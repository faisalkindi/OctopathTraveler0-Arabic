"""Lock Arabic transliterations for every named character found in batch1_dialogue.csv
before translating (per user's explicit requirement: glossary must cover every named
character first).
"""
import csv
import os

GLOSSARY = os.path.join(os.path.dirname(__file__), "..", "GLOSSARY.csv")

NEW_NAMES = [
    # term_en, term_ar, category, should_translate, notes
    ("Ludo", "لودو", "character_name", "transliterate", "char_id=10302"),
    ("Tiziano", "تيزيانو", "character_name", "transliterate", "char_id=28569, Bargello gang member"),
    ("Fra", "فرا", "character_name", "transliterate", "char_id=28571, Bargello gang member"),
    ("Sonia", "سونيا", "character_name", "transliterate", "char_id=28574"),
    ("Lord Taviani", "اللورد تافياني", "character_name", "transliterate", "char_id=28575, JA=ドン・タヴィアーニ"),
    ("Rosso", "روسو", "character_name", "transliterate", "char_id=28588"),
    ("Tomazzo", "توماتزو", "character_name", "transliterate", "char_id=28589"),
    ("Gastone", "غاستوني", "character_name", "transliterate", "char_id=28590"),
    ("Francesca the Actress", "الممثلة الكبرى فرانشيسكا", "character_name", "transliterate", "char_id=28971"),
    ("Francesca", "فرانشيسكا", "character_name", "transliterate", "char_id=117854"),
    ("Margretta", "مارغريتا", "character_name", "transliterate", "char_id=28972"),
    ("Velnorte", "فيلنورت", "character_name", "transliterate", "char_id=28994, already used consistently in pilot GameTextQuest"),
    ("Jurgen", "يورغن", "character_name", "transliterate", "char_id=28995"),
    ("Rinyuu", "رينيو", "character_name", "transliterate", "char_id=28996, uncertain reading - phonetic"),
    ("Phina", "فينا", "character_name", "transliterate", "char_id=28998, already used consistently in pilot GameTextNPC"),
    ("Knight Ardante", "فارس اللهب المقدس", "job_class", "translate", "char_id=29006, recurring title (Sacred Flame Knight)"),
    ("King of Hornburg", "ملك هورنبورغ", "character_name", "transliterate", "char_id=116369, Hornburg already locked as place name"),
    ("Tytos", "تايتوس", "character_name", "transliterate", "char_id=117735, main Power-arc villain"),
    ("Gabriella", "غابرييلا", "character_name", "transliterate", "char_id=117851"),
    ("Anita", "أنيتا", "character_name", "transliterate", "char_id=117852"),
]


def main():
    with open(GLOSSARY, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    by_en = {r["term_en"]: r for r in rows}
    added = 0
    filled = 0
    for term_en, term_ar, category, should_translate, notes in NEW_NAMES:
        if term_en in by_en:
            if not by_en[term_en]["term_ar"]:
                by_en[term_en]["term_ar"] = term_ar
                filled += 1
            continue
        rows.append({"term_ja": "", "term_en": term_en, "term_ar": term_ar,
                     "category": category, "should_translate": should_translate, "notes": notes})
        added += 1

    with open(GLOSSARY, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"Filled {filled} existing empty rows, added {added} new rows. Total glossary rows: {len(rows)}")


if __name__ == "__main__":
    main()
