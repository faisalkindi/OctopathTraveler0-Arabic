"""
Speaker-ID pass (Gemini): reads a contiguous GameTextEvent scene and tags each
line with who's speaking and who's being addressed, since the corpus has no
speaker column and no reliable voice_id->character mapping was found.

CONCURRENT version (2026-07-07): chunks are independent (each is its own
contiguous scene-context call), so they run concurrently via asyncio.gather,
same pattern as vllm_translate.py, with retry-on-503 (transient Gemini overload,
confirmed 2026-07-07).

Output feeds into vllm_translate.py's Speaker: line scene format.

Usage: py -3.13 gemini_speaker_id.py <input_csv> <output_json>
  input_csv columns: id, voice_id, ja_text, en_text
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

# Retryable transient errors: SDK-level (APIError covers ServerError) plus raw
# network exceptions from the underlying httpx client, which the SDK does NOT wrap
# -- confirmed 2026-07-07 (httpx.ReadError crashed chunks in gemini_proofread.py
# because only genai_errors.ServerError was being caught there).
RETRYABLE_ERRORS = (genai_errors.APIError, ValueError, json.JSONDecodeError,
                    httpx.HTTPError, httpx.TransportError)

API_KEY = os.environ["GEMINI_API_KEY"]  # set your own key
MODEL = "gemini-2.5-flash"
WS = os.path.join(os.path.dirname(__file__), "..")
CHUNK_SIZE = 60  # rows per speaker-id call -- small enough to keep scene coherence
CONCURRENCY = 8  # moderate cap -- Gemini free/low tiers rate-limit harder than a local vLLM server


def load_cast():
    with open(os.path.join(WS, "GAME_CONTEXT.md"), encoding="utf-8") as f:
        context = f.read()
    with open(os.path.join(WS, "GLOSSARY.csv"), encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["category"] == "character_name"]
    cast = "\n".join(f"- {r['term_en']}" for r in rows if r["term_ar"])
    return context, cast


PROMPT_TEMPLATE = """You are identifying speakers in Japanese JRPG dialogue (Octopath Traveler 0) so a
translator downstream can get gender/register agreement right. You are NOT translating anything.

GAME CONTEXT:
{context}

KNOWN CAST (character names that may appear as speakers):
{cast}

TASK: For each numbered dialogue line below (in original scene order), determine:
- speaker: who is saying this line. Use a name from KNOWN CAST if it's clearly one of them.
  If it's an unnamed/generic NPC (e.g. a flower-selling child, a nameless thug), give a short
  descriptive label instead (e.g. "Flower Girl", "Gang Member 1") -- but keep the SAME label
  for the same recurring unnamed character across consecutive lines if it's clearly the same person.
- speaker_gender: male, female, or unknown (only if truly indeterminable from context/grammar)
- addressee: who the line is spoken TO, if identifiable from context (another character name/label,
  "player" if addressing the protagonist, or "none"/"self" for narration/monologue/reaction sounds)

Read the WHOLE scene as a continuing conversation, in order, before deciding -- pronouns, honorifics,
and JP sentence-final particles (わ/ですわ = feminine; だぜ/だろ = masculine informal, etc.) are your
main clues. A single speaker keeps talking across consecutive lines unless the content clearly shows
a new speaker responding.

Lines (id: japanese_text):
{lines}

Return ONLY a JSON array, one object per input line, same order:
[{{"id": "<id>", "speaker": "<name or label>", "speaker_gender": "male|female|unknown", "addressee": "<name/label/player/none>"}}]
No markdown fences, no commentary.
"""


FALLBACK_TAG = {"speaker": "Unknown", "speaker_gender": "unknown", "addressee": "none"}


async def call_gemini_raw(sem, client, context, cast, rows, max_retries=5, label=""):
    """Single call attempt with retry-on-transient-error. Returns (tags, blocked)
    where blocked=True means a hard PROHIBITED_CONTENT safety block (not retryable --
    caller should bisect), tags=None in that case."""
    lines_text = "\n".join(f"{r['id']}: {r['ja_text']}" for r in rows)
    prompt = PROMPT_TEMPLATE.format(context=context, cast=cast, lines=lines_text)
    async with sem:
        for attempt in range(max_retries):
            try:
                resp = await client.aio.models.generate_content(
                    model=MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type="application/json",
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                    ),
                )
                if resp.text is None:
                    block_reason = getattr(getattr(resp, "prompt_feedback", None), "block_reason", None)
                    if block_reason is not None:
                        # Deterministic safety block (e.g. PROHIBITED_CONTENT) -- confirmed
                        # 2026-07-07 on a violent battle/curse scene. Retrying the SAME
                        # content will always fail identically; caller must bisect instead.
                        print(f"  {label}: SAFETY BLOCK ({block_reason}) on {len(rows)} row(s) -- will bisect")
                        return None, True
                    finish_reason = None
                    try:
                        finish_reason = resp.candidates[0].finish_reason
                    except Exception:
                        pass
                    raise ValueError(f"empty response text (finish_reason={finish_reason})")
                return json.loads(resp.text), False
            except RETRYABLE_ERRORS as e:
                wait = min(60, 5 * (2 ** attempt))
                print(f"  {label}: error ({e}), retrying in {wait}s (attempt {attempt+1}/{max_retries})")
                await asyncio.sleep(wait)
    raise RuntimeError(f"{label}: exhausted retries")


async def process_chunk(sem, client, context, cast, rows, chunk_index):
    tags = await process_rows_with_bisection(sem, client, context, cast, rows, label=f"chunk {chunk_index}")
    return chunk_index, tags


async def process_rows_with_bisection(sem, client, context, cast, rows, label):
    tags, blocked = await call_gemini_raw(sem, client, context, cast, rows, label=label)
    if not blocked:
        return tags

    if len(rows) == 1:
        # a single line still gets blocked even alone -- fall back to a safe generic
        # tag rather than failing the whole pipeline over one line's content.
        r = rows[0]
        print(f"  {label}: single row id={r['id']} still blocked -- using fallback tag")
        return [{"id": r["id"], **FALLBACK_TAG}]

    mid = len(rows) // 2
    left = await process_rows_with_bisection(sem, client, context, cast, rows[:mid], label=f"{label}L")
    right = await process_rows_with_bisection(sem, client, context, cast, rows[mid:], label=f"{label}R")
    return left + right


async def run_all(client, context, cast, rows):
    chunks = []
    for i in range(0, len(rows), CHUNK_SIZE):
        chunk = [r for r in rows[i:i + CHUNK_SIZE] if r["ja_text"] and r["ja_text"] != "no data."]
        if chunk:
            chunks.append(chunk)

    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [process_chunk(sem, client, context, cast, chunk, i) for i, chunk in enumerate(chunks)]

    results_by_index = {}
    n_done = 0
    for coro in asyncio.as_completed(tasks):
        chunk_index, tags = await coro
        results_by_index[chunk_index] = tags
        n_done += len(chunks[chunk_index])
        print(f"tagged {n_done}/{len(rows)} (chunks completed so far)")

    all_tags = []
    for i in range(len(chunks)):
        all_tags.extend(results_by_index[i])
    return all_tags


def main():
    if len(sys.argv) != 3:
        print("Usage: gemini_speaker_id.py <input_csv> <output_json>")
        sys.exit(1)
    input_csv, output_json = sys.argv[1], sys.argv[2]

    context, cast = load_cast()
    client = genai.Client(api_key=API_KEY)

    with open(input_csv, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    t0 = time.time()
    all_tags = asyncio.run(run_all(client, context, cast, rows))
    wall = time.time() - t0

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_tags, f, ensure_ascii=False, indent=2)
    print(f"Done in {wall:.1f}s ({wall/max(1,len(rows)):.3f} s/row). Wrote {len(all_tags)} speaker tags to {output_json}")


if __name__ == "__main__":
    main()
