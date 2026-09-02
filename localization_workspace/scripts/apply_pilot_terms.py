"""Fold the pilot's locked term decisions back into GLOSSARY.csv (methodology step:
'Get it reviewed, fold decisions into the glossary/style guide, THEN go wide.')
"""
import csv
import os

GLOSSARY = os.path.join(os.path.dirname(__file__), "..", "GLOSSARY.csv")

DECISIONS = {
    "Lady Herminia": "السيدة هيرمينيا",
    "Herminia": "هيرمينيا",
    "Auguste": "أوغست",
    "Auguste the Playwright": "أوغست الكاتب المسرحي",
    "Pierro Della": "بييرو ديلا",
    "Bargello": "بارجيلو",
    "Alaune": "ألاون",
    "Oskha the Have-Not": "أوسكا، المعدم",
    "Wordsworth the Wealthy": "وردزورث الثري",
    "Pharamea": "فارميا",
    "Orsterra": "أورستيرا",
    "Wishvale": "ويشفيل",
    "Cragspear": "كراغسبير",
    "Frostlands Region": "إقليم الأراضي الجليدية",
    "Frostlands": "الأراضي الجليدية",
    "Riven": "ريفن",
    "Edoras": "إيدوراس",
    "Castle Edoras": "قلعة إيدوراس",
    "Altinia": "ألتينيا",
    "Auguste's Journal": "مذكرات أوغست",
}

CATEGORY_ADD = [
    # term_en, term_ar, category, should_translate, notes
    ("Bestower of All", "واهب كل شيء", "system_term", "translate", "arc-title pattern: Bestower of Wealth/Fame/Power/All"),
    ("It's go time.", "...حان وقت العمل.", "system_term", "translate", "recurring fixed battle-start phrase (JA: クールだ)"),
    ("leaves (currency)", "أوراق", "system_term", "translate", "in-game currency, official EN name is lowercase 'leaves'"),
    ("BP", "نقاط الطاقة", "system_term", "translate", "Boost Point combat resource"),
    ("SP", "نقاط المهارة", "system_term", "translate", "Support Point combat resource"),
    ("Hell (辺獄 realm prefix)", "الجحيم", "system_term", "translate", "TENTATIVE - realm/area name prefix, verify if proper noun or literal"),
    ("Octopuff", "أوكتوبَف", "creature_name", "transliterate", "franchise mascot creature"),
]


def main():
    with open(GLOSSARY, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
        fieldnames = f
    with open(GLOSSARY, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    updated = 0
    for r in rows:
        if r["term_en"] in DECISIONS and not r["term_ar"]:
            r["term_ar"] = DECISIONS[r["term_en"]]
            updated += 1

    for term_en, term_ar, category, should_translate, notes in CATEGORY_ADD:
        rows.append({
            "term_ja": "", "term_en": term_en, "term_ar": term_ar,
            "category": category, "should_translate": should_translate, "notes": notes
        })

    with open(GLOSSARY, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"Filled {updated} existing rows, added {len(CATEGORY_ADD)} new system-term rows.")
    print(f"Total glossary rows now: {len(rows)}")


if __name__ == "__main__":
    main()
