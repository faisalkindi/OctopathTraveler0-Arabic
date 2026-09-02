"""Build the initial glossary skeleton from corpus data (foundation artifact #4).
Arabic column starts EMPTY on purpose -- terms are agreed first, then applied identically everywhere.
"""
import csv
import os

CORPUS = os.path.join(os.path.dirname(__file__), "..", "corpus")
OUT = os.path.join(os.path.dirname(__file__), "..", "GLOSSARY.csv")


def load(table):
    path = os.path.join(CORPUS, table + ".csv")
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    rows_out = []

    # Characters (names) -- GameTextCharacter is JP name -> official EN name, keyed by character id
    for row in load("GameTextCharacter"):
        ja, en = row["ja_text"], row["en_text"]
        if not en or en in ("no data.", "???", "everyone", "Everyone"):
            continue
        rows_out.append({
            "term_ja": ja, "term_en": en, "term_ar": "", "category": "character_name",
            "should_translate": "transliterate", "notes": f"char_id={row['id']}"
        })

    # Job classes -- GameTextPC
    for row in load("GameTextPC"):
        ja, en = row["ja_text"], row["en_text"]
        if not en or en == "(Unlocalized)":
            continue
        rows_out.append({
            "term_ja": ja, "term_en": en, "term_ar": "", "category": "job_class",
            "should_translate": "translate", "notes": ""
        })

    # Regions + towns -- GameTextMap (dedupe, keep short place-name-looking entries)
    seen = set()
    for row in load("GameTextMap"):
        en = row["en_text"]
        if not en or en in seen:
            continue
        seen.add(en)
        rows_out.append({
            "term_ja": row["ja_text"], "term_en": en, "term_ar": "", "category": "place_name",
            "should_translate": "transliterate", "notes": f"map_id={row['id']}"
        })

    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["term_ja", "term_en", "term_ar", "category", "should_translate", "notes"])
        w.writeheader()
        w.writerows(rows_out)

    print(f"Wrote {len(rows_out)} glossary rows to {OUT}")


if __name__ == "__main__":
    main()
