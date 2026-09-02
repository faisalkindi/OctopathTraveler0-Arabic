import csv, sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('verify_part08.csv', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

overrides = {}

overrides['418176'] = ('regression',
    'ما معنى أن تكون فقيراً……\nلم أكن أدرك ذلك……',
    'Gemini reason falsely claims "corrected ellipsis count to match source" but ja_text has 2 ellipsis runs '
    '(貧しいというのがどういうことか…… / 私はわかっていなかった……) while both before AND after retain only 1 run. '
    'Additionally Gemini\'s edit added a stray trailing newline with no content after it (dangling empty second line), '
    'a new formatting defect not present in "before". Provided final_ar_text restores the source\'s 2-line/2-ellipsis structure.')

overrides['418034'] = ('improvement', '',
    'Genuine improvement: recovered the first clause entirely missing from "before". Residual minor issue: ja_text has '
    '3 ellipsis runs but ar_text still only has 2, having compressed/dropped the filler interjection "いやぁ" along with '
    'its ellipsis beat. Minor, does not warrant regression given the much larger recovered omission.')

overrides['418533'] = ('improvement', '',
    'Genuine improvement: fixed clause order to match ja_text/en_text (before had it backwards). Residual minor issue: '
    'ja_text has 2 ellipsis runs but the reordered ar_text only has 1 (comma substituted). Suggested fully corrected text: '
    '"جرفت السفينة المحطمة وحدها إلى الميناء……\\nفظننتُ أنك قد متّ……"')

overrides['418428'] = ('improvement', '',
    'Genuine content improvement (fixed mistranslation). However reason claims أصبحتَ is "gender-neutral in spelling" -- '
    'it is NOT: the explicit fatha diacritic visibly marks 2nd-person masculine. Same defect pre-existed in "before" '
    '(وقعتَ also had the fatha), so not newly introduced. Truly neutral form: "لقد أصبحت محط اهتمام شخص صعب المراس".')

overrides['418439'] = ('improvement', '',
    'Genuine improvement (recovered a fully missing sentence). But the added verb كنتَ carries an explicit fatha, '
    'undercutting the reason\'s claim of "gender-neutral phrasing." Suggested neutral form: "ماذا كنت لتفعل يا <chara_name>؟"')

overrides['419465'] = ('improvement', '',
    'Genuine fix (plural to singular for player address). But reason explicitly claims "gender-neutral past tense" for '
    'واجهتَ while an explicit fatha marks it masculine -- confirmed false-neutrality claim. True neutral spelling: "واجهت".')

overrides['419466'] = ('improvement', '',
    'Genuine fix (plural to singular). Reason claims "gender-neutral past tense" for واصلتَ but explicit fatha marks '
    'masculine, contradicting the claim. True neutral spelling: "واصلت شق طريقك نحو المستقبل".')

overrides['419484'] = ('improvement', '',
    'Major genuine improvement: "before" had a completely wrong subject/gender (3rd-person "her ability") vs ja/en '
    '2nd-person address; correctly fixed. However reason falsely and self-contradictorily claims "Removed unnecessary '
    'diacritic" while the output still retains an explicit fatha on أنجزتَ marking masculine -- confirmed false-neutrality '
    'claim. Fully corrected neutral text: "وقد أنجزت إنجازات متتالية عظيمة، غيرت تاريخ البلاد."')

overrides['418860'] = ('regression',
    'تقول كارابيل إنها……\nتريد أن تأكل <favorite_dish_name>',
    'CONFIRMED name-consistency regression: reason claims the change is "for consistency," but Gemini landed on '
    '"كارابل" (missing internal ي) which is the MINORITY spelling in the established corpus (3 occurrences) -- while the '
    'same Gemini pass, in the very same file, correctly used the DOMINANT spelling "كارابيل" (10 occurrences corpus-wide) '
    'for the same character in rows 418829/418881/418888/418924. The content-completion part is good and kept.')

overrides['418867'] = ('regression',
    'نودُّ أن نُطعم كارابيل <favorite_dish_name>',
    'CONFIRMED name-consistency regression, same issue as 418860: lands on minority spelling "كارابل" instead of the '
    'dominant, established "كارابيل" used elsewhere by the same Gemini pass in this very file. The subject-agreement fix '
    '(أودّ to نودّ) is legitimate and kept.')

overrides['419599'] = ('regression',
    'هل سمعت أغنية ساويرس؟',
    'CONFIRMED name-consistency regression: Gemini changed "شيرشا" to "ساورسي" claiming this is "per glossary" -- but '
    'GLOSSARY.csv has NO Arabic value for Saoirse (char_id=11608), so there is no glossary to comply with; the claim is '
    'false. "ساورسي" is also the corpus\'s rarest variant (1 occurrence) vs the dominant "ساويرس" (8 occurrences), which '
    'this SAME Gemini pass correctly used in rows 419782/419783 of this very file.')

overrides['419628'] = ('regression',
    'ساويرس!',
    'CONFIRMED name-consistency regression: Gemini changed "شياشا" to "سيرشا," again falsely claiming "glossary '
    'compliance" (the glossary field is empty for Saoirse). "سيرشا" appears 3x corpus-wide vs the dominant "ساويرس" (8x), '
    'used correctly elsewhere in this same file (419782/419783).')

overrides['419635'] = ('regression',
    'أغنية ساويرس\nتدعوني دائماً إلى المتاهة……',
    'Same confirmed name-consistency regression as 419628 -- "سيرشا" used instead of the dominant/established "ساويرس" '
    'that this same Gemini pass applied correctly elsewhere in this file (419782/419783).')

wash_only_keywords = ['punctuation', 'comma', 'period', 'quotation', 'quote', 'diacritic', 'harakat', 'tashkeel', 'hamza']
substantive_keywords = ['mistranslat', 'gender', 'omit', 'missing', 'glossary', 'consisten', 'transliterat',
    'pronoun', 'subject', 'agreement', 'meaning', 'accura', 'neutral', 'incomplete', 'awkward', 'register',
    'passive', 'tense', 'rephrase', 'rephrased', 'nuance', 'flow', 'naturalness', 'wording', 'clarity',
    'idiom', 'grammar', 'grammatical', 'plural', 'singular', 'number', 'context', 'specificity']

def classify(row):
    rid = row['id']
    if rid in overrides:
        return overrides[rid]
    reason = row['reason'].lower()
    has_substantive = any(k in reason for k in substantive_keywords)
    has_wash_only = any(k in reason for k in wash_only_keywords)
    if has_substantive:
        return ('improvement', '', '')
    if has_wash_only:
        return ('wash', '', '')
    if 'line break' in reason or 'ellipsis' in reason or 'newline' in reason:
        return ('improvement', '', '')
    return ('improvement', '', '')

out_rows = []
counts = {'improvement': 0, 'wash': 0, 'regression': 0}
for row in rows:
    verdict, final_text, notes = classify(row)
    counts[verdict] += 1
    out_rows.append({
        'id': row['id'],
        'ja_text': row['ja_text'],
        'en_text': row['en_text'],
        'ar_text_before': row['ar_text_before'],
        'ar_text_gemini': row['ar_text'],
        'verdict': verdict,
        'final_ar_text': final_text,
        'notes': notes,
    })

with open('verify_part08_result.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['id', 'ja_text', 'en_text', 'ar_text_before', 'ar_text_gemini', 'verdict', 'final_ar_text', 'notes'])
    w.writeheader()
    for r_ in out_rows:
        w.writerow(r_)

print(counts)
print('total', len(out_rows))
