"""
Auto-generate a per-batch condensed background for vllm_translate.py, since the
local model's 4096-token context window can't fit the full GAME_CONTEXT.md +
STYLE_GUIDE.md (measured 2026-07-07: caused a 400 context-overflow error), and a
single hardcoded background is wrong for batches from a different story arc.

Usage: py -3.13 gemini_batch_background.py <input_csv> <output_txt>
  input_csv columns: id, voice_id, ja_text, en_text (or any subset with ja_text)
"""
import csv
import os
import sys

import time

from google import genai
from google.genai import types
from google.genai import errors as genai_errors

API_KEY = "AIzaSyDYQLWqc7NlwVydFcDJG1Y-9_eFKh8M6hI"
MODEL = "gemini-2.5-flash"
WS = os.path.join(os.path.dirname(__file__), "..")
SAMPLE_LINES = 40  # enough lines to identify the arc/characters/setting without huge cost


PROMPT_TEMPLATE = """You are writing a CONDENSED background document for a small local translation
model (4096-token context window, so this must be SHORT -- target 1000-1500 characters, hard
cap ~1800) to use while translating Japanese Octopath Traveler 0 dialogue into Arabic.

FULL GAME CONTEXT (read fully, then compress):
{game_context}

FULL STYLE GUIDE (read fully, then compress):
{style_guide}

SAMPLE OF THE ACTUAL BATCH TO BE TRANSLATED (identify which story arc/characters/setting this is):
{sample}

Write a condensed background (1000-1500 chars) covering ONLY what's relevant to THIS SPECIFIC
batch's content -- do not try to summarize the whole game. Include:
1. Which story arc/characters/setting this batch is from (identify from the sample), with just
   enough plot/character context to translate it correctly (who's who, their relationships, tone).
2. The register rule: warm, natural, everyday MSA throughout -- NOT archaic, NOT dialect. Name which
   characters in THIS batch speak in a more refined/courtly register vs a blunt/rough one, if
   identifiable from the sample.
3. The player-character rule: silent, gender-customizable protagonist, NO gender branching --
   any line addressing "player" needs gender-neutral Arabic phrasing.
4. The harakat rule: ~1-in-10 lines get any diacritic; shadda when gemination-meaning-bearing,
   rare short vowel only to disambiguate; otherwise bare -- never fully vocalize a line.

Output ONLY the condensed background text, no headers, no commentary, no markdown formatting.
"""


def main():
    if len(sys.argv) != 3:
        print("Usage: gemini_batch_background.py <input_csv> <output_txt>")
        sys.exit(1)
    input_csv, output_txt = sys.argv[1], sys.argv[2]

    with open(os.path.join(WS, "GAME_CONTEXT.md"), encoding="utf-8") as f:
        game_context = f.read()
    with open(os.path.join(WS, "STYLE_GUIDE.md"), encoding="utf-8") as f:
        style_guide = f.read()

    with open(input_csv, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r.get("ja_text") and r["ja_text"] != "no data."]
    sample_rows = rows[:SAMPLE_LINES]
    sample = "\n".join(r["ja_text"].replace("\n", " / ") for r in sample_rows)

    client = genai.Client(api_key=API_KEY)
    prompt = PROMPT_TEMPLATE.format(game_context=game_context, style_guide=style_guide, sample=sample)
    background = None
    for attempt in range(5):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.3),
            )
            if resp.text is None:
                finish_reason = None
                try:
                    finish_reason = resp.candidates[0].finish_reason
                except Exception:
                    pass
                raise ValueError(f"empty response text (finish_reason={finish_reason})")
            background = resp.text.strip()
            break
        except (genai_errors.ServerError, ValueError) as e:
            wait = min(60, 5 * (2 ** attempt))
            print(f"  error ({e}), retrying in {wait}s")
            time.sleep(wait)
    if background is None:
        raise RuntimeError("gemini_batch_background: exhausted retries")

    with open(output_txt, "w", encoding="utf-8") as f:
        f.write(background)
    print(f"Wrote {len(background)} chars to {output_txt}")
    print("--- preview ---")
    print(background[:300])


if __name__ == "__main__":
    main()
