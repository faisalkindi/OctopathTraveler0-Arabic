"""
Injects our final Arabic translations into a GameText table's EN-US .uexp (slot 0
= EN-US per PROJECT_STATE.md's confirmed LANG_INDEX=0), re-encodes, and patches the
paired .uasset SerialSize -- the fully verified end-to-end recipe from the
2026-07-06 in-game test (see PROJECT_STATE.md "VERIFIED END-TO-END IN-GAME").

Usage: py -3.13 inject_table.py <table_name> <final_csv> <src_dir> <out_dir>
  final_csv columns: id, ja_text, en_text, ar_text
  src_dir: directory containing <table_name>.uexp and <table_name>.uasset (EN-US)
  out_dir: where to write the patched <table_name>.uexp / .uasset
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from kingship_msgpack import read_uexp, write_uexp, patch_uasset_serial_size


def main():
    if len(sys.argv) != 5:
        print("Usage: inject_table.py <table_name> <final_csv> <src_dir> <out_dir>")
        sys.exit(1)
    table, final_csv, src_dir, out_dir = sys.argv[1:5]

    with open(final_csv, encoding="utf-8-sig") as f:
        translations = {r["id"]: r["ar_text"] for r in csv.DictReader(f)}

    src_uexp = os.path.join(src_dir, f"{table}.uexp")
    src_uasset = os.path.join(src_dir, f"{table}.uasset")
    obj = read_uexp(src_uexp)

    n_injected = 0
    n_missing = 0
    for row in obj["m_DataList"]:
        rid = str(row["m_id"])
        if rid in translations and translations[rid]:
            row["m_gametext"][0] = translations[rid]
            n_injected += 1
        elif row.get("m_gametext", [None])[0] not in (None, "", "no data.", "No data."):
            n_missing += 1

    os.makedirs(out_dir, exist_ok=True)
    dst_uexp = os.path.join(out_dir, f"{table}.uexp")
    dst_uasset = os.path.join(out_dir, f"{table}.uasset")

    new_size = write_uexp(dst_uexp, obj)
    offset, new_serial = patch_uasset_serial_size(src_uasset, dst_uasset, new_size)

    print(f"{table}: injected {n_injected}, missing translation for {n_missing} non-empty rows. "
          f"New uexp size {new_size}, SerialSize patched to {new_serial} at uasset offset {offset}.")


if __name__ == "__main__":
    main()
