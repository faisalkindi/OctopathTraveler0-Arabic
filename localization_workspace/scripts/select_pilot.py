"""Select the ~300-line pilot batch: stratified sample across categories, plus one
contiguous in-context dialogue scene (per methodology: dialogue must be scene-by-scene,
not randomly sampled rows).
"""
import csv
import os

CORPUS = os.path.join(os.path.dirname(__file__), "..", "corpus")
OUT = os.path.join(os.path.dirname(__file__), "..", "pilot_batch.csv")


def load(table):
    path = os.path.join(CORPUS, table + ".csv")
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def nonempty(rows, min_len=2):
    return [r for r in rows if r["ja_text"] and r["ja_text"] not in ("no data.",) and len(r["ja_text"]) >= min_len]


def main():
    picks = []

    # UI: 50 rows, spread across the table (every Nth row for variety of screens)
    ui = nonempty(load("GameTextUI"))
    step = max(1, len(ui) // 50)
    picks += [("GameTextUI", r) for r in ui[::step][:50]]

    # Item: 40 rows
    item = nonempty(load("GameTextItem"))
    step = max(1, len(item) // 40)
    picks += [("GameTextItem", r) for r in item[::step][:40]]

    # Skill: 40 rows
    skill = nonempty(load("GameTextSkill"))
    step = max(1, len(skill) // 40)
    picks += [("GameTextSkill", r) for r in skill[::step][:40]]

    # Quest: 30 rows
    quest = nonempty(load("GameTextQuest"))
    step = max(1, len(quest) // 30)
    picks += [("GameTextQuest", r) for r in quest[::step][:30]]

    # NPC barks: 20 rows
    npc = nonempty(load("GameTextNPC"))
    step = max(1, len(npc) // 20)
    picks += [("GameTextNPC", r) for r in npc[::step][:20]]

    # Character/Map/Village: 10 each
    for table, n in [("GameTextCharacter", 10), ("GameTextMap", 10), ("GameTextVillage", 10)]:
        rows = nonempty(load(table))
        step = max(1, len(rows) // n)
        picks += [(table, r) for r in rows[::step][:n]]

    # Dialogue: one CONTIGUOUS scene from GameTextEvent, in m_id order (already confirmed
    # ids 1-18ish are the opening Herminia-rumor scene from our earlier spot-check).
    event = load("GameTextEvent")
    by_id = {int(r["id"]): r for r in event if r["id"].isdigit()}
    scene_ids = sorted(i for i in by_id if 0 <= i <= 100)[:100]
    picks += [("GameTextEvent", by_id[i]) for i in scene_ids if by_id[i]["ja_text"] and by_id[i]["ja_text"] != "no data."]

    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["table", "id", "voice_id", "ja_text", "en_text"])
        for table, r in picks:
            w.writerow([table, r["id"], r.get("voice_id", ""), r["ja_text"], r["en_text"]])

    print(f"Selected {len(picks)} pilot rows -> {OUT}")


if __name__ == "__main__":
    main()
