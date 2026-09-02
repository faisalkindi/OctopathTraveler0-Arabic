import csv
import os

WS = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(WS, "batch1_translated.csv")

all_rows = []
for i in [1, 2, 3]:
    path = os.path.join(WS, f"batch1_part{i}_translated.csv")
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    print(f"part{i}: {len(rows)} rows")
    all_rows.extend(rows)

with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["id", "ja_text", "en_text", "ar_text"])
    w.writeheader()
    w.writerows(all_rows)

print(f"Merged {len(all_rows)} rows -> {OUT}")
