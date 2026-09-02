import csv
import re
import os

PATH = os.path.join(os.path.dirname(__file__), "..", "batch1_translated.csv")
TAG_RE = re.compile(r"\{[0-9]+\}|<[^>]+>")


def main():
    with open(PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    issues = []
    empty_ar_nonempty_ja = 0
    for r in rows:
        ja, en, ar = r["ja_text"], r["en_text"], r["ar_text"]
        if ja and ja != "no data." and not ar:
            empty_ar_nonempty_ja += 1
            issues.append(f"id={r['id']}: EMPTY ar_text but ja_text present: {ja!r}")
            continue

        en_tags = sorted(TAG_RE.findall(en))
        ar_tags = sorted(TAG_RE.findall(ar))
        ja_tags = sorted(TAG_RE.findall(ja))
        # compare against ja tags primarily (source of truth), en as fallback reference
        if ja_tags and ja_tags != ar_tags:
            issues.append(f"id={r['id']}: TAG MISMATCH ja={ja_tags} ar={ar_tags}")

        ja_nl = ja.count("\n")
        en_nl = en.count("\n")
        ar_nl = ar.count("\n")
        if en_nl != ar_nl:
            issues.append(f"id={r['id']}: NEWLINE MISMATCH (vs EN) ja_nl={ja_nl} en_nl={en_nl} ar_nl={ar_nl}")

        for ch in [",", ";", "?"]:
            if ch in ar:
                issues.append(f"id={r['id']}: ASCII '{ch}' in ar_text: {ar!r}")

    print(f"Checked {len(rows)} rows, {len(issues)} issues found ({empty_ar_nonempty_ja} empty-ar rows):")
    for i in issues[:200]:
        print(" -", i)
    if len(issues) > 200:
        print(f" ... and {len(issues) - 200} more")


if __name__ == "__main__":
    main()
