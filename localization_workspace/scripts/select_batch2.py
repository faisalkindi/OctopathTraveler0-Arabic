import csv
import os

CORPUS = os.path.join(os.path.dirname(__file__), "..", "corpus")
OUT = os.path.join(os.path.dirname(__file__), "..", "batch2_dialogue.csv")
TARGET_ROWS = 1000  # smaller first real batch on the new pipeline, scale up once validated


def load(table):
    path = os.path.join(CORPUS, table + ".csv")
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    event = load("GameTextEvent")
    by_id = [(int(r["id"]), r) for r in event if r["id"].isdigit()]
    by_id.sort(key=lambda t: t[0])

    already_done = set(range(0, 2065))  # pilot (1-100) + batch1 (101-2064)
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


if __name__ == "__main__":
    main()
