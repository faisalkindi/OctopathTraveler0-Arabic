"""
Lighter translation pipeline for non-dialogue tables (UI, Item, Skill, Quest, Enemy,
Character, etc.) -- no speaker-ID needed since these are standalone strings, not
scene dialogue. Same vLLM backend/glossary/standing-rules as vllm_translate.py, but
a simpler "id: text" batch format instead of the "Speaker: line" scene format.

Usage: py -3.13 vllm_translate_standalone.py <input_csv> <output_csv> <background_txt>
  input_csv columns: id, voice_id, category, ja_text, en_text
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
BATCH_SIZE = 20  # short standalone strings -- can batch more per call than dialogue scenes
CONCURRENCY = 24


def load_glossary():
    with open(os.path.join(WS, "GLOSSARY.csv"), encoding="utf-8-sig") as f:
        return [(r["term_en"], r["term_ar"]) for r in csv.DictReader(f) if r["term_ar"]]


def build_prompt(rows, background, glossary_pairs):
    lines = [f"{r['id']}: {r['ja_text']}" for r in rows]
    text = "\n".join(lines)

    rules = list(STANDING_RULES_GENERAL) + list(STANDING_RULES_ARABIC)
    rules.append(
        "These are STANDALONE UI/system/item/skill/quest/character strings, NOT dialogue -- "
        "no speaker context applies. Keep translations concise and consistent with how the "
        "same term is translated elsewhere (e.g. an item name must always render the same way)."
    )
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
        "Preserve any placeholder tags exactly (e.g. <chara_name>, {0}, {1}) and line breaks (\\n)."
    )
    rules.append(
        "Output format: one line per input, `id: translation`, same ids, same order, no extra commentary."
    )

    head = "Translate the following Japanese game strings into Arabic."
    parts = [head, "Requirements:\n" + "\n".join(f"{i + 1}. {r}" for i, r in enumerate(rules)),
             f"Text:\n{text}"]
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


def parse_output(text: str, expected_ids: list) -> dict | None:
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        id_part, _, rest = line.partition(":")
        id_part = id_part.strip()
        if id_part in expected_ids:
            result[id_part] = rest.strip()
    if len(result) != len(expected_ids):
        return None
    return result


def translate_one_fallback_sync(row: dict, background: str, glossary_pairs: list) -> str:
    prompt = build_prompt([row], background, glossary_pairs)
    try:
        out = vllm_call_sync(prompt, max_tokens=300)
    except Exception as e:
        print(f"  per-line fallback failed for id={row['id']} ({e}) -- leaving untranslated")
        return f"UNTRANSLATED: {row['ja_text']}"
    for line in out.splitlines():
        line = line.strip()
        if line.startswith(f"{row['id']}:"):
            return line.partition(":")[2].strip()
    return out.strip()


async def translate_chunk(sem, chunk, background, glossary_pairs, chunk_index):
    ids = [r["id"] for r in chunk]
    prompt = build_prompt(chunk, background, glossary_pairs)
    max_out = min(1500, 60 * len(chunk))

    async with sem:
        parsed = None
        for attempt in range(2):
            try:
                out = await asyncio.to_thread(vllm_call_sync, prompt, max_out)
            except Exception as e:
                print(f"chunk {chunk_index}: scene call error ({e}), falling back to per-line calls")
                break
            parsed = parse_output(out, ids)
            if parsed is not None:
                break

        mismatch = parsed is None
        if mismatch:
            print(f"chunk {chunk_index}: MISMATCH, falling back to per-line calls")
            translated = await asyncio.gather(*[
                asyncio.to_thread(translate_one_fallback_sync, r, background, glossary_pairs)
                for r in chunk
            ])
            parsed = dict(zip(ids, translated))

    return chunk_index, chunk, parsed, mismatch


async def run_all(rows, background, glossary_pairs):
    sem = asyncio.Semaphore(CONCURRENCY)
    chunks = [rows[i:i + BATCH_SIZE] for i in range(0, len(rows), BATCH_SIZE)]
    tasks = [translate_chunk(sem, chunk, background, glossary_pairs, i) for i, chunk in enumerate(chunks)]

    results = []
    n_mismatch = 0
    n_done = 0
    for coro in asyncio.as_completed(tasks):
        chunk_index, chunk, parsed, mismatch = await coro
        n_mismatch += int(mismatch)
        for r in chunk:
            results.append({"id": r["id"], "ja_text": r["ja_text"], "en_text": r["en_text"],
                             "ar_text": parsed.get(r["id"], f"UNTRANSLATED: {r['ja_text']}")})
        n_done += len(chunk)
        print(f"translated {n_done}/{len(rows)} (chunks done, mismatches so far: {n_mismatch})")

    id_order = {r["id"]: i for i, r in enumerate(rows)}
    results.sort(key=lambda r: id_order[r["id"]])
    return results, n_mismatch


def main():
    if len(sys.argv) != 4:
        print("Usage: vllm_translate_standalone.py <input_csv> <output_csv> <background_txt>")
        sys.exit(1)
    input_csv, output_csv, background_txt = sys.argv[1], sys.argv[2], sys.argv[3]

    with open(input_csv, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    with open(background_txt, encoding="utf-8") as f:
        background = f.read()
    glossary_pairs = load_glossary()

    t0 = time.time()
    results, n_mismatch = asyncio.run(run_all(rows, background, glossary_pairs))
    wall = time.time() - t0

    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "ja_text", "en_text", "ar_text"])
        w.writeheader()
        w.writerows(results)

    print(f"Done in {wall:.1f}s ({wall/max(1,len(rows)):.3f} s/row). Wrote {len(results)} rows to {output_csv}. "
          f"Total chunk mismatches: {n_mismatch}")


if __name__ == "__main__":
    main()
