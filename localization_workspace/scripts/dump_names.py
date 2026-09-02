import csv
import os

CORPUS = os.path.join(os.path.dirname(__file__), "..", "corpus")

for table in ["GameTextPC", "GameTextMap", "GameTextVillage", "GameTextCharacter"]:
    path = os.path.join(CORPUS, table + ".csv")
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    out_path = rf"H:\_octo_pak\{table}_dump.txt"
    with open(out_path, "w", encoding="utf-8") as out:
        for row in rows:
            out.write(f"{row['id']} | {row['ja_text']} | {row['en_text']}\n")
    print(table, "rows:", len(rows), "->", out_path)
