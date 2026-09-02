"""Mechanical QA pass on the pilot translation: placeholder/tag parity, newline count,
ASCII punctuation leaks, per LOCALIZATION_METHODOLOGY.md's QA validator artifact.
"""
import csv
import re
import os

PATH = os.path.join(os.path.dirname(__file__), "..", "pilot_translated.csv")

TAG_RE = re.compile(r"\{[0-9]+\}|<[^>]+>")


def main():
    with open(PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    issues = []
    for r in rows:
        en, ar = r["en_text"], r["ar_text"]
        en_tags = sorted(TAG_RE.findall(en))
        ar_tags = sorted(TAG_RE.findall(ar))
        if en_tags != ar_tags:
            issues.append(f"{r['table']} id={r['id']}: TAG MISMATCH en={en_tags} ar={ar_tags}")

        en_nl = en.count("\n")
        ar_nl = ar.count("\n")
        if en_nl != ar_nl:
            issues.append(f"{r['table']} id={r['id']}: NEWLINE COUNT MISMATCH en={en_nl} ar={ar_nl}")

        for ch in [",", ";", "?"]:
            if ch in ar and ar != "(Unlocalized)":
                issues.append(f"{r['table']} id={r['id']}: ASCII '{ch}' found in ar_text: {ar!r}")

    print(f"Checked {len(rows)} rows, {len(issues)} issues found:")
    for i in issues:
        print(" -", i)


if __name__ == "__main__":
    main()
