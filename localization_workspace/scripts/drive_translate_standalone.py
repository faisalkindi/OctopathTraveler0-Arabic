"""
Phase-1b driver: translate all non-dialogue tables (UI/Item/Skill/Quest/Enemy/
Character/etc.) through vllm_translate_standalone.py, one table at a time.
No speaker-ID stage (not dialogue) and no per-chunk background generation (these
are standalone terms, not story-arc scenes) -- uses a short static background
per table instead.

Excludes the 5 tables already confirmed leftover-mobile-game/dev-test data
(GameTextQuestJP, GameTextStoryBook, GameTextSupport, GameTextLifepath,
GameTextPartVoice -- see PROJECT_STATE.md) and GameTextGraphic (EN-sourced,
handled separately since it has no Japanese source).

Usage: py -3.13 drive_translate_standalone.py
"""
import csv
import os
import subprocess
import sys
import time

WS = os.path.join(os.path.dirname(__file__), "..")
CORPUS = os.path.join(WS, "corpus")
OUT_DIR = os.path.join(WS, "standalone_translated")
SCRIPTS = os.path.dirname(__file__)
PY = sys.executable

SKIP_TABLES = {"GameTextQuestJP", "GameTextStoryBook", "GameTextSupport",
               "GameTextLifepath", "GameTextPartVoice", "GameTextGraphic",
               "GameTextEvent", "GameTextNPC"}

TABLE_BLURBS = {
    "GameTextCharacter": "Character names, titles, and short bios/descriptions for the player party and NPCs.",
    "GameTextCharacterCreate": "Player-created-protagonist character creation flow: job, appearance, and name options.",
    "GameTextEnding": "Ending-sequence narration and epilogue text.",
    "GameTextEnemy": "Enemy monster names and combat-encounter flavor text.",
    "GameTextFC": "Field-command/travel-banter conversations between party members (short, casual dialogue-like lines).",
    "GameTextItem": "Item names and item flavor-text descriptions (weapons, armor, consumables, key items).",
    "GameTextMap": "Map/location/region names shown on the world map and travel UI.",
    "GameTextPC": "Player-character-related short system strings.",
    "GameTextQuest": "Quest titles, quest log objectives, and quest completion text.",
    "GameTextScenarioReplay": "Story/side-story replay menu entries (chapter/scene titles and summaries).",
    "GameTextSkill": "Battle skill/ability names and their short effect descriptions.",
    "GameTextUI": "User-interface labels: menus, buttons, system messages, tooltips.",
    "GameTextVillage": "Village/settlement names and descriptions.",
}


def run(cmd, log_path, retries=2):
    for attempt in range(retries):
        with open(log_path, "w", encoding="utf-8") as logf:
            result = subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
        if result.returncode == 0:
            return 0
        print(f"  step failed (rc={result.returncode}), attempt {attempt+1}/{retries}")
        time.sleep(10)
    return result.returncode


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    with open(os.path.join(WS, "GAME_CONTEXT.md"), encoding="utf-8") as f:
        game_context_summary = f.read()[:1500]  # condensed excerpt, not the full doc (token budget)

    tables = []
    for fname in sorted(os.listdir(CORPUS)):
        if not fname.endswith(".csv"):
            continue
        table = fname[:-4]
        if table in SKIP_TABLES:
            continue
        path = os.path.join(CORPUS, fname)
        with open(path, encoding="utf-8-sig") as f:
            rows = [r for r in csv.DictReader(f) if r.get("ja_text") and r["ja_text"] != "no data."]
        if rows:
            tables.append((table, rows))

    total = sum(len(rows) for _, rows in tables)
    print(f"{len(tables)} tables, {total} rows total")

    for table, rows in tables:
        out_csv = os.path.join(OUT_DIR, f"{table}.csv")
        if os.path.exists(out_csv):
            print(f"{table}: already done, skipping")
            continue

        t0 = time.time()
        print(f"=== {table}: {len(rows)} rows ===")

        input_csv = os.path.join(OUT_DIR, f"{table}_input.csv")
        with open(input_csv, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "voice_id", "ja_text", "en_text"])
            for r in rows:
                w.writerow([r["id"], r.get("voice_id", ""), r["ja_text"], r["en_text"]])

        blurb = TABLE_BLURBS.get(table, f"{table} game data.")
        background_txt = os.path.join(OUT_DIR, f"{table}_background.txt")
        with open(background_txt, "w", encoding="utf-8") as f:
            f.write(f"{blurb}\n\n{game_context_summary}")

        rc = run([PY, os.path.join(SCRIPTS, "vllm_translate_standalone.py"), input_csv, out_csv, background_txt],
                  os.path.join(OUT_DIR, f"{table}_translate.log"))
        if rc != 0:
            print(f"{table}: vLLM translate FAILED (rc={rc}), see log. Stopping.")
            return
        print(f"{table}: DONE in {time.time()-t0:.0f}s")

    print("All tables translated.")


if __name__ == "__main__":
    main()
