import csv
import os

WS = os.path.join(os.path.dirname(__file__), "..")
SRC = os.path.join(WS, "batch1_dialogue.csv")
N_PARTS = 3

with open(SRC, encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

chunk_size = (len(rows) + N_PARTS - 1) // N_PARTS
for i in range(N_PARTS):
    part = rows[i * chunk_size: (i + 1) * chunk_size]
    if not part:
        continue
    out = os.path.join(WS, f"batch1_part{i+1}.csv")
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "voice_id", "ja_text", "en_text"])
        for r in part:
            w.writerow([r["id"], r["voice_id"], r["ja_text"], r["en_text"]])
    print(f"part{i+1}: {len(part)} rows, ids {part[0]['id']}..{part[-1]['id']} -> {out}")
