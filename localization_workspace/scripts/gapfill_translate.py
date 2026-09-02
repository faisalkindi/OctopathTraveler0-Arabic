"""
Gap-fill pass: re-translate rows that ended up with empty ar_text somewhere in the
main pipeline (batch-mode mismatch/fallback failures). Translated ONE ROW AT A TIME
via vLLM (these already failed batch-mode once; per-row calls maximize success and
avoid the same class of chunk-parse failure recurring).

Usage: py -3.13 gapfill_translate.py <input_csv> <output_csv>
  input_csv columns: id, ja_text, en_text, source
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
CONCURRENCY = 24


def load_glossary():
    with open(os.path.join(WS, "GLOSSARY.csv"), encoding="utf-8-sig") as f:
        return [(r["term_en"], r["term_ar"]) for r in csv.DictReader(f) if r["term_ar"]]


def load_bg():
    with open(os.path.join(WS, "GAME_CONTEXT.md"), encoding="utf-8") as f:
        return f.read()[:2000]


def build_prompt(row, background, glossary_pairs):
    rules = list(STANDING_RULES_GENERAL) + list(STANDING_RULES_ARABIC)
    rules.append(
        "Ellipsis: match the source's U+2026 count exactly, never ASCII dots."
    )
    rules.append(
        "Adhere to this background document (context, characters, facts):\n"
        f"---\n{background}\n---"
    )
    if glossary_pairs:
        ref = "\n".join(f"- {a} → {b}" for a, b in glossary_pairs)
        rules.append(f"Use this glossary for the given terms:\n{ref}")
    rules.append("Output ONLY the Arabic translation, nothing else -- no commentary, no id prefix.")

    head = "Translate the following single Japanese game-text string into Arabic."
    parts = [head, "Requirements:\n" + "\n".join(f"{i + 1}. {r}" for i, r in enumerate(rules)),
             f"Text:\n{row['ja_text']}"]
    return "\n\n".join(parts)


def vllm_call_sync(prompt: str, max_tokens: int = 600, retries: int = 4) -> str:
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
            time.sleep(3 * (attempt + 1))
    raise last_err


async def translate_row(sem, row, background, glossary_pairs):
    prompt = build_prompt(row, background, glossary_pairs)
    async with sem:
        try:
            out = await asyncio.to_thread(vllm_call_sync, prompt)
            return row["id"], out.strip()
        except Exception as e:
            print(f"  id={row['id']}: failed even per-row ({e})")
            return row["id"], ""


async def run_all(rows, background, glossary_pairs):
    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [translate_row(sem, r, background, glossary_pairs) for r in rows]
    results = {}
    n_done = 0
    for coro in asyncio.as_completed(tasks):
        rid, ar = await coro
        results[rid] = ar
        n_done += 1
        if n_done % 100 == 0:
            print(f"gapfilled {n_done}/{len(rows)}")
    return results


def main():
    if len(sys.argv) != 3:
        print("Usage: gapfill_translate.py <input_csv> <output_csv>")
        sys.exit(1)
    input_csv, output_csv = sys.argv[1], sys.argv[2]

    with open(input_csv, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    background = load_bg()
    glossary_pairs = load_glossary()

    t0 = time.time()
    results = asyncio.run(run_all(rows, background, glossary_pairs))
    wall = time.time() - t0

    n_still_empty = sum(1 for r in rows if not results.get(r["id"], "").strip())
    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "ja_text", "en_text", "ar_text"])
        w.writeheader()
        for r in rows:
            w.writerow({"id": r["id"], "ja_text": r["ja_text"], "en_text": r["en_text"],
                        "ar_text": results.get(r["id"], "")})

    print(f"Done in {wall:.1f}s. {len(rows)-n_still_empty}/{len(rows)} filled, {n_still_empty} still empty.")


if __name__ == "__main__":
    main()
