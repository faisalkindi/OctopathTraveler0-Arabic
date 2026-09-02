"""
Stage 3 of 3: Gemini proofreading pass on vLLM/Gemma4-12B's translation output.

CONCURRENT version (2026-07-07): chunks are independent, so they run concurrently
via asyncio.gather (same pattern as vllm_translate.py / gemini_speaker_id.py),
capped lower (6) than the other stages since this prompt is large (full game
context + style guide + glossary each call) and thinking is left ON (see note
below), making each call heavier.

Checks (in order, per arabic-ui-review's rule categories + this project's own
found error classes): mistranslation/false-friend errors against JA source
(e.g. パーティ = ball/banquet vs "party" as adventuring group), subject-verb/
gender/number agreement, hamza correctness, glossary consistency, register
consistency, and placeholder/line-break integrity.

Usage: py -3.13 gemini_proofread.py <input_csv> <output_csv>
  input_csv columns: id, ja_text, en_text, ar_text (vLLM's draft)
  output_csv: same columns, ar_text corrected where needed, plus a `changed` column
"""
import asyncio
import csv
import json
import os
import sys
import time

import httpx
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

# Retryable transient errors: SDK-level (APIError covers ServerError and other HTTP
# status errors) plus raw network exceptions from the underlying httpx client, which
# the SDK does NOT wrap -- confirmed 2026-07-07 (httpx.ReadError crashed 2 chunks
# because only genai_errors.ServerError was being caught).
RETRYABLE_ERRORS = (genai_errors.APIError, ValueError, json.JSONDecodeError,
                    httpx.HTTPError, httpx.TransportError)

API_KEY = "AIzaSyDYQLWqc7NlwVydFcDJG1Y-9_eFKh8M6hI"
MODEL = "gemini-2.5-flash"
WS = os.path.join(os.path.dirname(__file__), "..")
CHUNK_SIZE = 25
CONCURRENCY = 48


def load_context():
    with open(os.path.join(WS, "GAME_CONTEXT.md"), encoding="utf-8") as f:
        context = f.read()
    with open(os.path.join(WS, "STYLE_GUIDE.md"), encoding="utf-8") as f:
        style = f.read()
    with open(os.path.join(WS, "GLOSSARY.csv"), encoding="utf-8-sig") as f:
        glossary_rows = [r for r in csv.DictReader(f) if r["term_ar"]]
    glossary_text = "\n".join(f"{r['term_en']} = {r['term_ar']}" for r in glossary_rows)
    return context, style, glossary_text


PROMPT_TEMPLATE = """You are proofreading Arabic translations (drafted by a smaller local model) of
Japanese JRPG dialogue for Octopath Traveler 0. This is a QUALITY-ASSURANCE pass, not a
re-translation from scratch -- most lines are already correct; fix only genuine errors.

GAME CONTEXT:
{context}

STYLE GUIDE:
{style}

GLOSSARY (frozen spellings, must be used exactly):
{glossary}

Check EVERY line for, in this priority order:
1. **Mistranslation / false-friend errors against the JAPANESE source** (ja_text is the source
   of truth; en_text is a meaning cross-reference only). Known error class already found in this
   pipeline: パーティ can mean "ball/banquet" (a social event) OR "adventuring party" (a group) --
   context must disambiguate; a scene set at a mansion banquet means "ball", not "group". Watch for
   similar homonym/false-friend confusions.
2. **Subject-verb / gender / number agreement**: does the Arabic verb/adjective genuinely agree
   with its ACTUAL grammatical subject (not just superficially plausible)? Known bug class: a
   sentence like "your blood stained my dress" needs the verb to agree with "blood" (masc.), not
   with "you".
3. **Hamza correctness**, dual (مثنى) vs plural where the source implies exactly two people.
4. **Glossary compliance**: every name/term must match the glossary exactly.
5. **Register**: warm everyday MSA per the style guide -- flag anything too flat/generic that
   loses a character's established tone (e.g. a noblewoman's curt dismissiveness), anything that
   slips into archaic MSA or real-world dialect, and awkward/unnatural word collocations even if
   not strictly ungrammatical.
6. **Player-address gender-neutrality**: any line where the addressee is the silent, gender-
   customizable protagonist must use neutral phrasing (past-tense 2nd-person forms are spelled
   identically for both genders; if a present-tense verb/adjective is unavoidable, generic
   masculine is an acceptable fallback -- but flag it if a rephrase would avoid the issue entirely).
   **Do NOT claim a present-tense verb (e.g. تفعل/تشعر/ترغب) or a predicate adjective is
   "gender-neutral" or "a verbal noun" when it is not** -- present-tense 2nd-person verbs visibly
   mark gender in the spelling (تفعل=masc. vs تفعلين=fem.), so replacing one masculine form with
   another masculine form is NOT a neutrality improvement, just a reword; don't report it as
   "changed: true" with a false neutrality justification unless the wording ACTUALLY changed
   something real (meaning, register, grammar, glossary compliance) -- a cosmetic swap between two
   equally-masculine-default options is not a fix.
7. **Placeholder tags and line breaks**: must be preserved exactly (do not touch tags like
   <chara_name>, <skl_user_name>, {{0}}, {{1}}, etc., or add/remove \\n).
8. **Harakat (تشكيل)**: this project targets roughly 1-in-10 lines carrying any diacritic at all --
   most lines should be completely bare. If ar_text is fully vocalized (diacritics on nearly every
   word), strip it down to bare except: keep a shadda (ّ) wherever it's genuinely gemination-
   meaning-bearing, and keep at most one or two short-vowel marks (fatha/kasra) only where the
   word would otherwise be genuinely misread. Do not ADD diacritics to a bare line just because
   you can -- the absence of diacritics is the default, correct state for ~90% of lines.
9. **Ellipsis count**: COUNT the exact number of consecutive ellipsis-like characters in ja_text
   (Japanese "……" runs use U+2026 HORIZONTAL ELLIPSIS, sometimes repeated -- e.g. "…………" is
   FOUR separate U+2026 characters, not two, not six). The Arabic ar_text must use that SAME exact
   count of the single Unicode "…" character (U+2026) -- never substitute ASCII dots ("......"),
   never a different count than the source. Before claiming an ellipsis fix, literally count the
   characters in ja_text yourself; do not estimate or pattern-match.

Rows (JSON array, each with id/ja_text/en_text/ar_text -- ar_text is the DRAFT to check):
{rows}

Return ONLY a JSON array, one object per input row, same order:
[{{"id": "<id>", "ar_text": "<corrected or unchanged translation>", "changed": true|false, "reason": "<brief reason if changed, else empty>"}}]
No markdown fences, no commentary.
"""


async def call_gemini_raw(sem, client, context, style, glossary, chunk, max_retries=9, label=""):
    """Returns (tags, blocked). blocked=True -> hard PROHIBITED_CONTENT safety block,
    caller should bisect (see gemini_speaker_id.py for the same pattern -- confirmed
    2026-07-07 on a violent battle/curse scene, not retryable)."""
    rows_json = json.dumps(
        [{"id": r["id"], "ja_text": r["ja_text"], "en_text": r["en_text"], "ar_text": r["ar_text"]} for r in chunk],
        ensure_ascii=False
    )
    prompt = PROMPT_TEMPLATE.format(context=context, style=style, glossary=glossary, rows=rows_json)
    async with sem:
        for attempt in range(max_retries):
            try:
                resp = await client.aio.models.generate_content(
                    model=MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json",
                        # thinking left at default (ON), NOT disabled: measured 2026-07-07 that
                        # thinking-off caused inconsistent misses on the exact ellipsis-count bug
                        # this prompt is designed to catch (ids 18/20/25 missed while identical
                        # ids 39/47 were caught, same input, same rule). Proofreading needs the
                        # careful counting/checking that speedy pattern-matching skips -- unlike
                        # bulk translation, where the benchmark validated no quality loss.
                    ),
                )
                if resp.text is None:
                    block_reason = getattr(getattr(resp, "prompt_feedback", None), "block_reason", None)
                    if block_reason is not None:
                        print(f"  {label}: SAFETY BLOCK ({block_reason}) on {len(chunk)} row(s) -- will bisect")
                        return None, True
                    finish_reason = None
                    try:
                        finish_reason = resp.candidates[0].finish_reason
                    except Exception:
                        pass
                    raise ValueError(f"empty response text (finish_reason={finish_reason})")
                return json.loads(resp.text), False
            except RETRYABLE_ERRORS as e:
                wait = min(90, 5 * (2 ** attempt))
                print(f"  {label}: error ({e}), retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                await asyncio.sleep(wait)
    raise RuntimeError(f"{label}: exhausted retries")


async def proofread_chunk(sem, client, context, style, glossary, chunk, chunk_index):
    proofed = await proofread_rows_with_bisection(sem, client, context, style, glossary, chunk, label=f"chunk {chunk_index}")
    return chunk_index, proofed


async def proofread_rows_with_bisection(sem, client, context, style, glossary, chunk, label):
    proofed, blocked = await call_gemini_raw(sem, client, context, style, glossary, chunk, label=label)
    if not blocked:
        return proofed

    if len(chunk) == 1:
        # blocked even alone -- fall back to "no change" (keep the vLLM draft as-is)
        # rather than losing the row entirely.
        r = chunk[0]
        print(f"  {label}: single row id={r['id']} still blocked -- keeping draft unchanged")
        return [{"id": r["id"], "ar_text": r["ar_text"], "changed": False,
                 "reason": "SKIPPED: Gemini safety block, draft kept as-is"}]

    mid = len(chunk) // 2
    left = await proofread_rows_with_bisection(sem, client, context, style, glossary, chunk[:mid], label=f"{label}L")
    right = await proofread_rows_with_bisection(sem, client, context, style, glossary, chunk[mid:], label=f"{label}R")
    return left + right


async def run_all(client, context, style, glossary, rows, checkpoint_path=None):
    chunks = [rows[i:i + CHUNK_SIZE] for i in range(0, len(rows), CHUNK_SIZE)]
    sem = asyncio.Semaphore(CONCURRENCY)

    # Resume support: a crash (e.g. a sustained Gemini 503 outage exhausting retries
    # on one chunk) used to lose ALL progress since output was only written at the
    # very end. Confirmed 2026-07-07 on the full-corpus run (~7000 rows lost). Now
    # checkpoint after every completed chunk and skip already-done chunks on restart.
    results_by_index = {}
    if checkpoint_path and os.path.exists(checkpoint_path):
        with open(checkpoint_path, encoding="utf-8") as f:
            saved = json.load(f)
        results_by_index = {int(k): v for k, v in saved.items()}
        print(f"Resuming from checkpoint: {len(results_by_index)}/{len(chunks)} chunks already done")

    todo_indices = [i for i in range(len(chunks)) if i not in results_by_index]
    tasks = [proofread_chunk(sem, client, context, style, glossary, chunks[i], i) for i in todo_indices]

    n_changed = sum(1 for res in results_by_index.values() for r in res if r.get("changed") is True)
    n_done = sum(len(res) for res in results_by_index.values())
    for coro in asyncio.as_completed(tasks):
        chunk_index, proofed = await coro
        chunk = chunks[chunk_index]
        by_id = {str(p["id"]): p for p in proofed}
        chunk_results = []
        for r in chunk:
            p = by_id.get(r["id"])
            if p is None:
                chunk_results.append({**r, "ar_text_before": r["ar_text"], "changed": "ERROR_NO_RESPONSE", "reason": ""})
                continue
            if p.get("changed"):
                n_changed += 1
                print(f"  id={r['id']}: CHANGED -- {p.get('reason', '')}")
            chunk_results.append({
                "id": r["id"], "ja_text": r["ja_text"], "en_text": r["en_text"],
                "ar_text_before": r["ar_text"], "ar_text": p["ar_text"],
                "changed": p.get("changed", False), "reason": p.get("reason", ""),
            })
        results_by_index[chunk_index] = chunk_results
        n_done += len(chunk)
        print(f"proofread {n_done}/{len(rows)} ({n_changed} changed so far)")

        if checkpoint_path:
            tmp = checkpoint_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({str(k): v for k, v in results_by_index.items()}, f, ensure_ascii=False)
            os.replace(tmp, checkpoint_path)

    results = []
    for i in range(len(chunks)):
        results.extend(results_by_index[i])
    return results, n_changed


def main():
    if len(sys.argv) != 3:
        print("Usage: gemini_proofread.py <input_csv> <output_csv>")
        sys.exit(1)
    input_csv, output_csv = sys.argv[1], sys.argv[2]

    context, style, glossary = load_context()
    client = genai.Client(api_key=API_KEY)

    with open(input_csv, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    checkpoint_path = output_csv + ".ckpt.json"
    t0 = time.time()
    results, n_changed = asyncio.run(run_all(client, context, style, glossary, rows, checkpoint_path))
    wall = time.time() - t0

    if os.path.exists(checkpoint_path):
        os.remove(checkpoint_path)

    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "ja_text", "en_text", "ar_text_before", "ar_text", "changed", "reason"])
        w.writeheader()
        w.writerows(results)
    print(f"Done in {wall:.1f}s ({wall/max(1,len(rows)):.3f} s/row). "
          f"Wrote {len(results)} rows to {output_csv}. Total changed: {n_changed}")


if __name__ == "__main__":
    main()
