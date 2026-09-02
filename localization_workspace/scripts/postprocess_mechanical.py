"""
Deterministic (ZERO model tokens) post-processor, run after gemini_proofread.py.
Fixes error classes the LLM proofreader proved unreliable at even when explicitly
instructed (measured 2026-07-07: still undercounted ellipsis ~14% of the time
despite an explicit rule to count exactly). Per LOCALIZATION_METHODOLOGY.md's own
principle: mechanical checks belong in code, not model judgment.

Usage: py -3.13 postprocess_mechanical.py <input_csv> <output_csv>
  input_csv columns: id, ja_text, en_text, ar_text
"""
import csv
import re
import sys
import os

WS = os.path.join(os.path.dirname(__file__), "..")


def load_glossary_bad_spellings():
    """Build a map of known-wrong -> correct spellings for names we've had to fix
    before (e.g. Erika-style transliteration vs the locked Elrica spelling)."""
    return {
        "إيريكا": "إلريكا",  # Elrica, not "Erika" -- confirmed via en_text 2026-07-07
    }


def fix_ellipsis(ja_text, ar_text):
    """Force ar_text's U+2026 run count to match ja_text's, preserving position
    (append/trim at the end of each run) rather than guessing new placement."""
    ja_count = ja_text.count("…")
    orig_ar_text = ar_text

    # ALWAYS strip/convert ASCII dot runs (2+ dots) first -- never allowed per style
    # guide, regardless of whether the (wrong) unicode count happened to match at 0.
    if re.search(r"\.{2,}", ar_text):
        ar_text = re.sub(r"\.{2,}", lambda m: "…" * ja_count if ja_count else "", ar_text)
        ar_text = ar_text.rstrip() if not ja_count else ar_text

    ar_count = ar_text.count("…")
    if ja_count == ar_count and ar_text == orig_ar_text:
        return ar_text, False
    if ar_count == ja_count:
        return ar_text, True

    if ar_count == 0 and ja_count > 0:
        # no ellipsis at all in ar_text but source has one -- append at the end
        # (best-effort; a human/LLM pass should still review these)
        return ar_text.rstrip() + "…" * ja_count, True

    if ja_count == 0 and ar_count > 0:
        # ar_text invented an ellipsis the source doesn't have -- strip it
        return re.sub(r"…+", "", ar_text).rstrip(), True

    # both present but count differs -- normalize the FIRST run found to the
    # correct count (covers the dominant single-run-undercount bug)
    def replace_first(m):
        return "…" * ja_count
    new_text, n_subs = re.subn(r"…+", replace_first, ar_text, count=1)
    return new_text, True


def fix_names(ar_text):
    changed = False
    for bad, good in load_glossary_bad_spellings().items():
        if bad in ar_text:
            ar_text = ar_text.replace(bad, good)
            changed = True
    return ar_text, changed


def check_newline_count(ja_text, en_text, ar_text):
    """Flag (don't auto-fix -- risk of breaking real content) if ar_text's
    newline count matches neither ja_text's nor en_text's."""
    ja_nl, en_nl, ar_nl = ja_text.count("\n"), en_text.count("\n"), ar_text.count("\n")
    return ar_nl not in (ja_nl, en_nl)


def main():
    if len(sys.argv) != 3:
        print("Usage: postprocess_mechanical.py <input_csv> <output_csv>")
        sys.exit(1)
    input_csv, output_csv = sys.argv[1], sys.argv[2]

    with open(input_csv, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    n_ellipsis_fixed = 0
    n_name_fixed = 0
    flagged_newline = []

    for r in rows:
        new_ar, changed = fix_ellipsis(r["ja_text"], r["ar_text"])
        if changed:
            n_ellipsis_fixed += 1
            r["ar_text"] = new_ar

        new_ar, changed = fix_names(r["ar_text"])
        if changed:
            n_name_fixed += 1
            r["ar_text"] = new_ar

        if check_newline_count(r["ja_text"], r.get("en_text", ""), r["ar_text"]):
            flagged_newline.append(r["id"])

    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "ja_text", "en_text", "ar_text"])
        w.writeheader()
        w.writerows([{"id": r["id"], "ja_text": r["ja_text"], "en_text": r["en_text"], "ar_text": r["ar_text"]}
                     for r in rows])

    print(f"Done. {n_ellipsis_fixed} ellipsis fixes, {n_name_fixed} name fixes, "
          f"{len(flagged_newline)} rows flagged for newline mismatch (not auto-fixed): {flagged_newline[:20]}")


if __name__ == "__main__":
    main()
