"""Select the next contiguous dialogue chunk from GameTextEvent, continuing after the
pilot's already-translated ids (1-100), and report which named characters (from
GameTextCharacter.csv) actually appear in the chunk's text -- for glossary completeness
before translating.
"""
import csv
import os
import re

CORPUS = os.path.join(os.path.dirname(__file__), "..", "corpus")
OUT = os.path.join(os.path.dirname(__file__), "..", "batch1_dialogue.csv")
TARGET_ROWS = 1500


def load(table):
    path = os.path.join(CORPUS, table + ".csv")
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    event = load("GameTextEvent")
    by_id = [(int(r["id"]), r) for r in event if r["id"].isdigit()]
    by_id.sort(key=lambda t: t[0])

    already_done = set(range(0, 101))  # pilot covered ids 1-100 (plus 0="no data.")
    chunk = []
    for i, r in by_id:
        if i in already_done:
            continue
        if not r["ja_text"] or r["ja_text"] == "no data.":
            continue
        chunk.append(r)
        if len(chunk) >= TARGET_ROWS:
            break

    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "voice_id", "ja_text", "en_text"])
        for r in chunk:
            w.writerow([r["id"], r["voice_id"], r["ja_text"], r["en_text"]])

    print(f"Selected {len(chunk)} rows, id range {chunk[0]['id']}..{chunk[-1]['id']} -> {OUT}")

    # Character-name scan: which official character names (from GameTextCharacter.csv)
    # appear as a substring inside this chunk's ja_text?
    chars = load("GameTextCharacter")
    names = [(r["id"], r["ja_text"], r["en_text"]) for r in chars
             if r["ja_text"] and r["en_text"] and r["en_text"] not in ("no data.", "???", "Everyone")]

    full_text = "\n".join(r["ja_text"] for r in chunk)
    found = []
    for cid, ja, en in names:
        # strip quote marks some names carry, e.g. "フランソワ"
        bare_ja = ja.strip("“”\"")
        if bare_ja and len(bare_ja) >= 2 and bare_ja in full_text:
            found.append((cid, bare_ja, en))

    out2 = os.path.join(os.path.dirname(__file__), "..", "batch1_characters_found.csv")
    with open(out2, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["char_id", "ja_name", "en_name"])
        for cid, ja, en in found:
            w.writerow([cid, ja, en])

    print(f"Found {len(found)} distinct character names referenced in this chunk -> {out2}")


if __name__ == "__main__":
    main()
