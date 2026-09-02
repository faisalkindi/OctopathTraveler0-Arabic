"""
Production translation for Octopath Traveler 0 via local vLLM (Gemma 4 12B AWQ),
per C:\\Users\\faisa\\Ai\\Benchmarks\\flores-ja-ar\\CLAUDE.md's validated setup.

CONCURRENT version (2026-07-07) -- the whole point of using vLLM over Ollama is
continuous batching across concurrent requests (measured in the benchmark: 25
concurrent short lines in 0.49s, 50k lines in ~16min projected). The original
sequential version defeated this; this version uses asyncio.gather over
asyncio.to_thread, same pattern as vllm_multi_scene.py, capped by a semaphore
matching the server's --max-num-seqs 32 capacity.

Pipeline stage 2 of 3: speaker-tagged JSON (from gemini_speaker_id.py) + our
glossary/game-context/style-guide -> vLLM translation -> CSV, with a line-count
validator + per-line fallback (per batch_sweep.py's proven pattern).

Usage: py -3.13 vllm_translate.py <input_csv> <speaker_json> <output_csv> [background_txt]
  input_csv columns: id, voice_id, ja_text, en_text
  speaker_json: output of gemini_speaker_id.py
  background_txt: output of gemini_batch_background.py (per-batch, since a single fixed
    background is wrong for batches from a different story arc). Defaults to
    scripts/condensed_background.txt (the Bargello/Herminia test-scene background) if omitted
    -- ALWAYS pass a real per-batch background for actual production batches.
"""
import asyncio
import csv
import json
import sys
import os
import time
import urllib.request

sys.path.insert(0, r"C:\Users\faisa\Ai\Benchmarks\flores-ja-ar")
from translate import STANDING_RULES_GENERAL, STANDING_RULES_ARABIC  # noqa: E402

URL = "http://127.0.0.1:8000/v1/chat/completions"
MODEL = "gemma4-12b-awq"
WS = os.path.join(os.path.dirname(__file__), "..")
SCENE_CHUNK = 8  # lines per vLLM call -- per CLAUDE.md, 5-10 lines w/ shared speaker context tested well
CONCURRENCY = 24  # matches the benchmark's validated 24-way concurrency (zero 429s on this server config)


def load_background_and_glossary(background_path=None):
    background_path = background_path or os.path.join(WS, "scripts", "condensed_background.txt")
    with open(background_path, encoding="utf-8") as f:
        background = f.read()
    with open(os.path.join(WS, "GLOSSARY.csv"), encoding="utf-8-sig") as f:
        all_pairs = [(r["term_en"], r["term_ar"]) for r in csv.DictReader(f) if r["term_ar"]]
    return background, all_pairs


def build_scene_prompt(rows, speaker_by_id, background, glossary_pairs):
    lines = []
    for r in rows:
        tag = speaker_by_id.get(str(r["id"]), {})
        speaker = tag.get("speaker", "Unknown")
        lines.append(f"{speaker}: {r['ja_text']}")
    scene_text = "\n".join(lines)

    rules = list(STANDING_RULES_GENERAL) + list(STANDING_RULES_ARABIC)
    rules.append(
        "Adhere to this background document (context, characters, facts):\n"
        f"---\n{background}\n---"
    )
    if glossary_pairs:
        ref = "\n".join(f"- {a} → {b}" for a, b in glossary_pairs)
        rules.append(
            "Use this glossary for the given terms. Inflect the Arabic side as "
            f"grammar requires (number, case, gender):\n{ref}"
        )
    rules.append(
        "Ellipsis: the Japanese source uses U+2026 HORIZONTAL ELLIPSIS characters (……), never ASCII "
        "dots. Your Arabic output must use the SAME character, U+2026 (…), and the SAME count as the "
        "source -- never substitute ASCII dots ('...' or '......'). Count the source's ellipsis "
        "characters exactly and match that count."
    )
    rules.append(
        "The player-character (protagonist) is silent and player-created; the game has NO gender "
        "branching for them. Any line addressing 'player' as addressee must use gender-neutral Arabic "
        "phrasing (prefer past-tense 2nd-person forms, which are spelled identically for both genders; "
        "if a present-tense verb or predicate adjective is unavoidable, default to the generic masculine "
        "form rather than guessing a gender)."
    )

    head = (
        "Translate the following Japanese dialogue scene into Arabic. "
        "Each line has the format `Speaker: line`. Translate every line, "
        "keeping the same order and the same `Speaker: translation` format, "
        "one line per source line -- same speaker labels, same count, same order. "
        "Use the speaker information to get gender agreement, register, and who is "
        "being addressed right. Output ONLY the translated lines, nothing else."
    )
    parts = [head, "Requirements:\n" + "\n".join(f"{i + 1}. {r}" for i, r in enumerate(rules)),
             f"Text:\n{scene_text}"]
    return "\n\n".join(parts)


def vllm_call_sync(prompt: str, max_tokens: int = 1200, retries: int = 3) -> str:
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0, "max_tokens": max_tokens}
    req = urllib.request.Request(URL, data=json.dumps(payload).encode("utf-8"),
                                  headers={"Content-Type": "application/json"})
    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                d = json.load(resp)
            return d["choices"][0]["message"]["content"]
        except Exception as e:
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise last_err


def parse_scene_output(text: str, expected_n: int) -> list | None:
    """Return list of ar_text strings in order if exactly expected_n speaker-prefixed
    entries parse; else None. An entry may span multiple physical lines (the model
    preserves the source's own \\n breaks within one speaker's turn) -- any line that
    does NOT start a new recognized speaker label is treated as a continuation of the
    current entry, joined with \\n."""
    out_lines = [l for l in text.splitlines() if l.strip()]
    if not out_lines:
        return None

    entries = []
    current = None
    for line in out_lines:
        prefix, sep, rest = line.partition(":")
        looks_like_label = sep and 0 < len(prefix.strip()) <= 30
        if looks_like_label:
            if current is not None:
                entries.append(current)
            current = rest.strip()
        else:
            if current is None:
                return None
            current += "\n" + line.strip()
    if current is not None:
        entries.append(current)

    if len(entries) != expected_n:
        return None
    return entries


def translate_one_fallback_sync(ja_text: str, speaker: str, background: str, glossary_pairs: list) -> str:
    prompt = build_scene_prompt(
        [{"id": "0", "ja_text": ja_text}], {"0": {"speaker": speaker}}, background, glossary_pairs
    )
    try:
        out = vllm_call_sync(prompt, max_tokens=300)
    except Exception as e:
        print(f"  per-line fallback also failed ({e}) -- leaving row untranslated for manual pass")
        return f"UNTRANSLATED: {ja_text}"
    lines = [l for l in out.splitlines() if l.strip()]
    if lines and ":" in lines[0]:
        return lines[0].partition(":")[2].strip()
    return out.strip()


async def translate_chunk(sem, chunk, speaker_by_id, background, glossary_pairs, chunk_index):
    speakers = [speaker_by_id.get(r["id"], {}).get("speaker", "Unknown") for r in chunk]
    prompt = build_scene_prompt(chunk, speaker_by_id, background, glossary_pairs)
    max_out = min(1200, 120 * len(chunk))

    async with sem:
        parsed = None
        for attempt in range(2):
            try:
                out = await asyncio.to_thread(vllm_call_sync, prompt, max_out)
            except Exception as e:
                # e.g. HTTP 400 (context-length overflow on an unusually long scene) --
                # confirmed 2026-07-07. Don't crash the whole run; fall through to the
                # per-line fallback below, which uses much smaller prompts.
                print(f"chunk {chunk_index}: scene call error ({e}), will fall back to per-line calls")
                break
            parsed = parse_scene_output(out, len(chunk))
            if parsed is not None:
                break

        mismatch = parsed is None
        if mismatch:
            print(f"chunk {chunk_index}: MISMATCH, falling back to per-line calls")
            parsed = await asyncio.gather(*[
                asyncio.to_thread(translate_one_fallback_sync, r["ja_text"], sp, background, glossary_pairs)
                for r, sp in zip(chunk, speakers)
            ])

    return chunk_index, chunk, parsed, mismatch


async def run_all(rows, speaker_by_id, background, glossary_pairs):
    sem = asyncio.Semaphore(CONCURRENCY)
    chunks = [rows[i:i + SCENE_CHUNK] for i in range(0, len(rows), SCENE_CHUNK)]
    tasks = [translate_chunk(sem, chunk, speaker_by_id, background, glossary_pairs, i)
             for i, chunk in enumerate(chunks)]

    results_by_index = {}
    n_mismatch = 0
    n_done = 0
    for coro in asyncio.as_completed(tasks):
        chunk_index, chunk, parsed, mismatch = await coro
        results_by_index[chunk_index] = (chunk, parsed)
        n_mismatch += int(mismatch)
        n_done += len(chunk)
        print(f"translated {n_done}/{len(rows)} (chunks done, mismatches so far: {n_mismatch})")

    results = []
    for i in range(len(chunks)):
        chunk, parsed = results_by_index[i]
        for r, ar in zip(chunk, parsed):
            results.append({"id": r["id"], "ja_text": r["ja_text"], "en_text": r["en_text"], "ar_text": ar})
    return results, n_mismatch


def main():
    if len(sys.argv) not in (4, 5):
        print("Usage: vllm_translate.py <input_csv> <speaker_json> <output_csv> [background_txt]")
        sys.exit(1)
    input_csv, speaker_json, output_csv = sys.argv[1], sys.argv[2], sys.argv[3]
    background_path = sys.argv[4] if len(sys.argv) == 5 else None
    if background_path is None:
        print("WARNING: no per-batch background_txt given -- falling back to the Bargello/Herminia "
              "test-scene background. Pass one generated by gemini_batch_background.py for real batches.")

    background, glossary_pairs = load_background_and_glossary(background_path)

    with open(input_csv, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["ja_text"] and r["ja_text"] != "no data."]
    with open(speaker_json, encoding="utf-8") as f:
        speaker_tags = json.load(f)
    speaker_by_id = {t["id"]: t for t in speaker_tags}

    t0 = time.time()
    results, n_mismatch = asyncio.run(run_all(rows, speaker_by_id, background, glossary_pairs))
    wall = time.time() - t0

    # results come back in as-completed order (by chunk finish time) -- resort by original id order
    id_order = {r["id"]: i for i, r in enumerate(rows)}
    results.sort(key=lambda r: id_order[r["id"]])

    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "ja_text", "en_text", "ar_text"])
        w.writeheader()
        w.writerows(results)
    print(f"Done in {wall:.1f}s ({wall/max(1,len(rows)):.3f} s/row). "
          f"Wrote {len(results)} rows to {output_csv}. Total chunk mismatches: {n_mismatch}")


if __name__ == "__main__":
    main()
