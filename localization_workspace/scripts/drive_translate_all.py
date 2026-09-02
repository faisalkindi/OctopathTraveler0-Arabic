"""
Phase-1 driver: translate ALL remaining dialogue (GameTextEvent + GameTextNPC)
through speaker-ID + background-gen + vLLM translate, chunk by chunk, with NO
pause for proofread/postprocess/verify -- those run as phase 2 afterward, per
user directive 2026-07-07.

Writes per-chunk outputs to translated_chunks/chunk_NNN.csv and a manifest.
Resumable: skips chunks whose output file already exists.

Usage: py -3.13 drive_translate_all.py
"""
import csv
import json
import os
import subprocess
import sys
import time

WS = os.path.join(os.path.dirname(__file__), "..")
CORPUS = os.path.join(WS, "corpus")
OUT_DIR = os.path.join(WS, "translated_chunks")
CHUNK_SIZE = 1200
DONE_EVENT_IDS = set(range(0, 3344))  # pilot(1-100) + batch1(101-2064) + batch2(2065-3343)

PY = sys.executable
SCRIPTS = os.path.dirname(__file__)


def load(table):
    path = os.path.join(CORPUS, table + ".csv")
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def build_source_list():
    event = [r for r in load("GameTextEvent") if r["id"].isdigit()
             and r["ja_text"] and r["ja_text"] != "no data."
             and int(r["id"]) not in DONE_EVENT_IDS]
    event.sort(key=lambda r: int(r["id"]))
    for r in event:
        r["_table"] = "GameTextEvent"

    npc = [r for r in load("GameTextNPC") if r["id"].isdigit()
           and r["ja_text"] and r["ja_text"] != "no data."]
    npc.sort(key=lambda r: int(r["id"]))
    for r in npc:
        r["_table"] = "GameTextNPC"

    return event + npc  # GameTextEvent (main story) first, then GameTextNPC barks


def run(cmd, log_path, retries=3):
    for attempt in range(retries):
        with open(log_path, "w", encoding="utf-8") as logf:
            result = subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
        if result.returncode == 0:
            return 0
        print(f"  step failed (rc={result.returncode}), attempt {attempt+1}/{retries}")
        time.sleep(10)
    return result.returncode


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = build_source_list()
    print(f"Total rows to translate: {len(rows)}")

    chunks = [rows[i:i + CHUNK_SIZE] for i in range(0, len(rows), CHUNK_SIZE)]
    print(f"{len(chunks)} chunks of up to {CHUNK_SIZE} rows each")

    for ci, chunk in enumerate(chunks):
        tag = f"chunk_{ci:03d}"
        out_csv = os.path.join(OUT_DIR, f"{tag}.csv")
        if os.path.exists(out_csv):
            print(f"{tag}: already done, skipping")
            continue

        t0 = time.time()
        print(f"=== {tag}: {len(chunk)} rows (tables: {sorted(set(r['_table'] for r in chunk))}) ===")

        input_csv = os.path.join(OUT_DIR, f"{tag}_input.csv")
        with open(input_csv, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "voice_id", "ja_text", "en_text"])
            for r in chunk:
                w.writerow([r["id"], r.get("voice_id", ""), r["ja_text"], r["en_text"]])

        bg_txt = os.path.join(OUT_DIR, f"{tag}_background.txt")
        rc = run([PY, os.path.join(SCRIPTS, "gemini_batch_background.py"), input_csv, bg_txt],
                 os.path.join(OUT_DIR, f"{tag}_bg.log"))
        if rc != 0:
            print(f"{tag}: background-gen FAILED (rc={rc}), see log. Stopping.")
            return
        print(f"{tag}: background generated ({time.time()-t0:.0f}s elapsed)")

        speakers_json = os.path.join(OUT_DIR, f"{tag}_speakers.json")
        rc = run([PY, os.path.join(SCRIPTS, "gemini_speaker_id.py"), input_csv, speakers_json],
                  os.path.join(OUT_DIR, f"{tag}_speakerid.log"))
        if rc != 0:
            print(f"{tag}: speaker-ID FAILED (rc={rc}), see log. Stopping.")
            return
        print(f"{tag}: speaker-ID done ({time.time()-t0:.0f}s elapsed)")

        rc = run([PY, os.path.join(SCRIPTS, "vllm_translate.py"), input_csv, speakers_json, out_csv, bg_txt],
                  os.path.join(OUT_DIR, f"{tag}_translate.log"))
        if rc != 0:
            print(f"{tag}: vLLM translate FAILED (rc={rc}), see log. Stopping.")
            return
        print(f"{tag}: DONE in {time.time()-t0:.0f}s total")

    print("All chunks translated.")


if __name__ == "__main__":
    main()
