"""
Phase 2 extraction: build the source corpus for every GameText table.

For each table, reads the base (Japanese source) .uexp and the EN-US .uexp (when present),
matches rows by m_id, and writes one CSV per table:
    id, voice_id, category, ja_text, en_text

Run with: py -3.13 extract_corpus.py
"""
import csv
import os
from kingship_msgpack import read_uexp

EXTRACT_ROOT = r"H:\_octo_pak\extract_full\Octopath_Traveler0\Content\Local\DataBase\GameText"
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "corpus")

TABLES = [
    ("SystemText", "GameTextCharacter"),
    ("SystemText", "GameTextCharacterCreate"),
    ("SystemText", "GameTextEnding"),
    ("SystemText", "GameTextEnemy"),
    ("SystemText", "GameTextFC"),
    ("SystemText", "GameTextGraphic"),        # EN-US only (no base found)
    ("SystemText", "GameTextItem"),
    ("SystemText", "GameTextLifepath"),       # base only (no EN-US found)
    ("SystemText", "GameTextMap"),
    ("SystemText", "GameTextPC"),
    ("SystemText", "GameTextPartVoice"),      # EN-US only (no base found)
    ("SystemText", "GameTextQuest"),
    ("SystemText", "GameTextQuestJP"),        # base only (no EN-US found)
    ("SystemText", "GameTextScenarioReplay"),
    ("SystemText", "GameTextSkill"),
    ("SystemText", "GameTextStoryBook"),       # base only (no EN-US found)
    ("SystemText", "GameTextSupport"),         # base only (no EN-US found)
    ("SystemText", "GameTextUI"),
    ("SystemText", "GameTextVillage"),
    ("TalkText", "GameTextEvent"),
    ("TalkText", "GameTextNPC"),
]


def base_path(subdir, name):
    return os.path.join(EXTRACT_ROOT, subdir, name + ".uexp")


def enus_path(subdir, name):
    return os.path.join(EXTRACT_ROOT, "Localize", "EN-US", subdir, name + ".uexp")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    summary = []

    for subdir, name in TABLES:
        bpath = base_path(subdir, name)
        epath = enus_path(subdir, name)

        base_rows = {}
        if os.path.exists(bpath):
            obj = read_uexp(bpath)
            for row in obj["m_DataList"]:
                base_rows[row["m_id"]] = row

        en_rows = {}
        if os.path.exists(epath):
            obj = read_uexp(epath)
            for row in obj["m_DataList"]:
                en_rows[row["m_id"]] = row

        all_ids = sorted(set(base_rows.keys()) | set(en_rows.keys()))
        out_path = os.path.join(OUT_DIR, f"{name}.csv")
        with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "voice_id", "category", "ja_text", "en_text"])
            for rid in all_ids:
                brow = base_rows.get(rid)
                erow = en_rows.get(rid)
                voice_id = (brow or erow).get("m_voiceId", "")
                ja_text = brow["m_gametext"][0] if brow else ""
                en_text = erow["m_gametext"][0] if erow else ""
                w.writerow([rid, voice_id, name, ja_text, en_text])

        summary.append((name, len(base_rows), len(en_rows), len(all_ids),
                         os.path.exists(bpath), os.path.exists(epath)))
        print(f"{name}: base={len(base_rows)} en={len(en_rows)} merged={len(all_ids)} "
              f"(base_file={'Y' if os.path.exists(bpath) else 'N'}, en_file={'Y' if os.path.exists(epath) else 'N'})")

    total_rows = sum(s[3] for s in summary)
    print(f"\nTOTAL rows across all tables: {total_rows}")


if __name__ == "__main__":
    main()
