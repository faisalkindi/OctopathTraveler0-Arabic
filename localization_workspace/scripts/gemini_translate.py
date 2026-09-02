"""
Gemini-based bulk translation for Octopath Traveler 0 (replaces Claude subagents per
user directive 2026-07-07 -- do not use Claude for translation or grammar QA on this
project going forward).

Model choice per LOCALIZATION_METHODOLOGY.md's verified bake-off: gemini-2.5-flash,
thinking OFF (thinking_budget=0) -- Flash holds Pro-level quality for in-character MSA
transcreation while being far cheaper; Flash-Lite is explicitly NOT safe for this (loses
quality, breaks JSON schema).

Usage:
    py -3.13 gemini_translate.py <input_csv> <output_csv>
    input_csv columns: id, voice_id, ja_text, en_text
    output_csv columns: id, ja_text, en_text, ar_text
"""
import csv
import json
import os
import sys
import time

from google import genai
from google.genai import types

API_KEY = os.environ["GEMINI_API_KEY"]  # set your own key
MODEL = "gemini-2.5-flash"
BATCH_SIZE = 40
WS = os.path.join(os.path.dirname(__file__), "..")


def load_context():
    with open(os.path.join(WS, "STYLE_GUIDE.md"), encoding="utf-8") as f:
        style = f.read()
    with open(os.path.join(WS, "GAME_CONTEXT.md"), encoding="utf-8") as f:
        context = f.read()
    with open(os.path.join(WS, "GLOSSARY.csv"), encoding="utf-8-sig") as f:
        glossary_rows = [r for r in csv.DictReader(f) if r["term_ar"]]
    glossary_text = "\n".join(f"{r['term_en']} = {r['term_ar']}" for r in glossary_rows)
    return style, context, glossary_text


RULES_CARD = """You are translating Japanese JRPG dialogue/text to Arabic for Octopath Traveler 0.

STYLE GUIDE (must follow exactly):
{style}

GAME CONTEXT:
{context}

FROZEN GLOSSARY (use these exact Arabic spellings whenever these terms appear -- never
re-derive your own transliteration for a name/term already listed here):
{glossary}

RULES:
- Register: warm, everyday Modern Standard Arabic (فصحى ميسّرة) -- natural, NOT archaic, NOT dialect, NOT bureaucratic.
- Translate from ja_text (source of truth). Use en_text only as a meaning/gender cross-reference.
- PRESERVE placeholder tags byte-for-byte: <chara_name>, <skl_user_name>, <Param_State>, <item_skill_explanation>, <icon_area_map>, {{0}}, {{1}}, etc.
- PRESERVE line breaks (\\n) in a sensible position matching the source.
- Arabic punctuation: ، ؛ ؟ not ASCII , ; ? -- except inside placeholders.
- Single ellipsis character … not multiple dots.
- CRITICAL grammar check before finalizing each line: verify the verb/adjective genuinely agrees in gender/number/person with its ACTUAL grammatical subject in your Arabic sentence -- not just superficially plausible. (Known failure mode: a sentence like "your blood stained my dress" needs the verb to agree with "blood" [masc. 3rd person], not with "you" -- check this class of error on every single line.)
- Any line addressing the player character (protagonist) must use GENDER-NEUTRAL phrasing (avoid committing to a single gendered 2nd-person verb/adjective form) -- this game has NO gender branching, a single fixed text serves both player genders.
- Empty ja_text or "no data." rows: output empty or "no data." respectively.

Return ONLY a JSON array, one object per input row, in the same order:
[{{"id": "<id>", "ar_text": "<arabic translation>"}}, ...]
No markdown fences, no commentary -- raw JSON array only.
"""


def translate_batch(client, style, context, glossary, rows):
    prompt = RULES_CARD.format(style=style, context=context, glossary=glossary)
    prompt += "\n\nROWS TO TRANSLATE:\n"
    prompt += json.dumps(
        [{"id": r["id"], "ja_text": r["ja_text"], "en_text": r["en_text"]} for r in rows],
        ensure_ascii=False, indent=None
    )

    resp = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            temperature=0.3,
            response_mime_type="application/json",
        ),
    )
    data = json.loads(resp.text)
    by_id = {str(d["id"]): d["ar_text"] for d in data}
    return by_id


def main():
    if len(sys.argv) != 3:
        print("Usage: gemini_translate.py <input_csv> <output_csv>")
        sys.exit(1)
    input_csv, output_csv = sys.argv[1], sys.argv[2]

    style, context, glossary = load_context()
    client = genai.Client(api_key=API_KEY)

    with open(input_csv, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    results = []
    for i in range(0, len(rows), BATCH_SIZE):
        chunk = rows[i:i + BATCH_SIZE]
        for attempt in range(3):
            try:
                translations = translate_batch(client, style, context, glossary, chunk)
                break
            except Exception as e:
                print(f"batch {i}: attempt {attempt+1} failed: {e}")
                time.sleep(5)
        else:
            raise RuntimeError(f"batch starting at row {i} failed after 3 attempts")

        for r in chunk:
            ar = translations.get(str(r["id"]), "")
            results.append({"id": r["id"], "ja_text": r["ja_text"], "en_text": r["en_text"], "ar_text": ar})
        print(f"translated {min(i+BATCH_SIZE, len(rows))}/{len(rows)}")

    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "ja_text", "en_text", "ar_text"])
        w.writeheader()
        w.writerows(results)

    print(f"Done. Wrote {len(results)} rows to {output_csv}")


if __name__ == "__main__":
    main()
