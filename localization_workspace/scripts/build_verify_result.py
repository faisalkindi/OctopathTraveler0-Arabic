import csv, sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\faisa\Ai\Mods Dev\OctopathTraveler0\localization_workspace\verify_part06.csv', encoding='utf-8') as f:
    r = list(csv.DictReader(f))

# regressions: id -> (final_ar_text, notes)
regressions = {
 '413743': (
   'سيد فين……!!',
   'JA "フェンさん……！！" has BOTH ellipsis (……) AND exclamation marks (！！). Gemini\'s reason falsely claims JA has no ellipsis, only "!!" -- untrue, JA clearly contains both. Gemini dropped the ellipsis entirely. Restored before\'s version which correctly preserved both.'
 ),
 '414153': (
   'إذا عشنا وفقًا لتعاليم الشعلة المقدسة\nهل تعتقدين أن الخطايا ستُغفر……؟',
   'Context (rows 414150/414156) confirms addressee is Laurana (named female character), not the silent protagonist. Gemini wrongly reclassified this as ambiguous player-address and replaced correct feminine تعتقدين with masculine ترى, citing "neutrality" -- false-neutrality violation (error class 2): ترى is itself gendered (masc), not neutral, and Laurana\'s gender is already known. Also wrongly cut ellipsis from 2 chars to 1 though JA has 2. Restored before\'s feminine verb + correct ellipsis count.'
 ),
 '414368': (
   'أنا آسفة، يا جدتي',
   'JA "ごめんなさい、おばあさま" contains ZERO ellipsis characters. Gemini\'s reason falsely claims "JA source has three ASCII dots" -- factually untrue (verified programmatically: count is 0). Gemini invented an ellipsis based on EN\'s "Grandma..." rather than JA. Restored before\'s version (no ellipsis).'
 ),
 '414371': (
   'رغمَ أنه يجبُ عليَّ\nتوبيخُكِ لأنكِ سرقتِ الزهور',
   'JA "お前が花を盗んだことを叱らなければいけないのに" has ZERO ellipsis characters. Gemini\'s reason falsely claims "JA source has four ASCII dots" -- untrue (verified: count is 0). Gemini invented "……" based on EN\'s trailing dots rather than JA. Restored before\'s version (no ellipsis).'
 ),
 '414884': (
   'لا…… هذا……',
   'JA "いや……だ……" = "No... it is..." -- だ ("da") is literal JA content, not "extraneous" as Gemini\'s reason claims. Gemini dropped this content word and reduced ellipsis count from JA\'s 4 chars to 2. Restored before\'s version which correctly preserved both content and ellipsis count.'
 ),
 '415459': (
   '……ألا يمكنكم\nأن تجعلوني رفيقاً في الرحلة؟',
   'JA "あの……僕を旅の仲間にしてもらえませんか？" opens with hesitation particle あの followed by one ellipsis (2 chars). Before mistranslated あの as demonstrative "ذلك" -- an error Gemini was right to remove -- but Gemini over-corrected by also deleting the ellipsis entirely, losing the required hesitation pause. Kept Gemini\'s removal of the wrong word but restored the JA-mandated ellipsis.'
 ),
 '414303': (
   'هل أصابتكِ أي جروح؟!',
   'Gemini\'s reason claims the addressee "Mamot" is male, but context (rows 414295-414306) shows マモット refers to the ANIMAL "marmot" that startled the old woman named Margot (female, per en_text row 414306). The line asks the startled Margot if she is hurt. Gemini misread the animal reference as a male character name and wrongly changed the correct feminine pronoun to masculine. Restored before\'s feminine form.'
 ),
 '415199': (
   '……بالفعل، ستذهب',
   'JA "……やっぱり、行くんだね" / EN "So you\'re leaving after all" express a present/near-future observation, not a completed past action. Gemini rephrased to past tense "لقد ذهبت" ("you have already left") to chase gender-neutrality, but this changes the actual meaning/tense (implies departure already happened, contradicting the scene where the addressee is still present). Restored before\'s tense-correct masculine-fallback phrasing.'
 ),
 '415738': (
   'ألم تكن تكره الأحاديث الفارغة\nيا حارس اللهب المقدس؟',
   'JA "守指長殿" = "Flameguard, sir" (聖火守指長, glossary row 505), a DIFFERENT title from "聖火騎士"/Knight Ardante (glossary row 501, فارس اللهب المقدس). Gemini\'s reason incorrectly claims فارس اللهب المقدس is "the glossary-consistent term" for Flameguard, but that term is reserved for Knight Ardante elsewhere in this same batch (rows 414135/414508/414511) -- conflates two distinct in-game titles, and is inconsistent with Gemini\'s own other renderings of Flameguard in this batch (حارس النار المقدسة in 414511, حارس الشعلة المقدسة in 415718). Corrected using the حارس root (guardian) to distinguish from فارس (knight), keeping اللهب for base-term consistency.'
 ),
 '414834': (
   '"كاتينا"',
   'JA "カッティーナ" is a standalone quoted katakana term/name (likely a rallying word or in-fiction proper noun), not a literal sentence. Gemini invented the explicit meaning "For the family!" based solely on EN\'s creative localization choice, with no JA support for that specific phrase (error class 4: inventing explicit content beyond ja_text). Per style guide default (transliterate proper-noun-like terms), restored before\'s transliteration.'
 ),
 '414830': (
   '……هذا رائع',
   'JA "……クールだ" literally means "...(that\'s) cool," a calm/composed exclamation. Gemini replaced this with "……حان وقت العمل" ("...It\'s go time"), following EN\'s free localization rather than the literal JA meaning -- EN may hint at subtext but should not justify swapping in an unrelated explicit meaning absent from ja_text. Restored before\'s literal, JA-faithful rendering.'
 ),
 '413936': (
   'بازيل……',
   'Name-consistency violation (error class 7): this row spells "Basil" as "باسيل" while immediately surrounding rows in this same batch (413868, 413870, 413872, 413957) all correctly use "بازيل" per Gemini\'s own glossary-compliance fixes. Standardized to "بازيل" as used elsewhere in the batch.'
 ),
}

improved_overrides = {
 '413702': (
   'ما رأيك في الانضمام إليّ في رحلة البحث عن الكنوز المقدسة؟',
   'Gemini correctly fixed a major mistranslation ("الآلهة الثمانية"/eight gods -> "الكنوز المقدسة"/sacred treasures) and achieved gender neutrality -- a real improvement. However "الثمانية" (eight) is not supported by this specific ja_text/en_text line; recommend dropping it (this residual issue predates Gemini\'s edit, carried over from "before").'
 ),
 '413893': (
   'هل أنت من نفس موطن السيدة مارغو؟!',
   'Gemini correctly fixed the wrong subject (before wrongly said "هل هي"/is she, about a third party) to address "you" directly, matching en_text. However Gemini used plural أنتم when context (row 413890) and en_text both indicate a single addressee -- corrected to singular أنت.'
 ),
 '413730': (
   'بعد أن تعرضت ويشفيل للهجوم……صنعنا قبورًا للجميع.',
   'Gemini correctly fixed a real content-completeness bug (before only translated the first clause, dropping "we dug graves for everyone" entirely) -- a genuine improvement. However in merging the two JA display-lines Gemini also dropped the JA ellipsis (2 chars) for a comma. Recommended fix keeps the completed content and restores the ellipsis for pacing.'
 ),
 '413878': (
   '……أريد تناول خضروات\nالجدة مارغو……',
   'Gemini\'s only actual change here was harakat removal (a legitimate style-guide-aligned tweak), but neither before nor after fixed a pre-existing ellipsis-count bug: ja_text has exactly 2 ellipsis occurrences (4 chars total), while both before and gemini insert an extra middle ellipsis not present in ja_text (6 chars total). Wash on Gemini\'s own change; underlying defect persists uncorrected. Recommended final removes the spurious middle ellipsis to match ja_text exactly.'
 ),
}

wash_only = {
 '413895': 'Only change was harakat removal; text is otherwise identical/equivalent, no real translation difference.',
 '413958': 'ar_text_before and ar_text are byte-identical -- despite changed=True and a reason field, no actual change was made to this row. The reason text appears to be a copy/mismatch from a neighboring row (413957) and does not describe this row\'s (unchanged) content.',
 '415232': 'ar_text_before and ar_text are byte-identical -- despite changed=True and a reason field claiming a line-break preservation, no actual change was made to this row.',
}

out_rows = []
for x in r:
    rid = x['﻿id'] if '﻿id' in x else x['id']
    ja = x['ja_text']; en = x['en_text']; before = x['ar_text_before']; gem = x['ar_text']

    if rid in regressions:
        final, note = regressions[rid]
        verdict = 'regression'
    elif rid in wash_only:
        final = gem
        note = wash_only[rid]
        verdict = 'wash'
    elif rid in improved_overrides:
        final, note = improved_overrides[rid]
        verdict = 'improvement'
    else:
        final = gem
        verdict = 'improvement'
        note = ''

    out_rows.append({
        'id': rid, 'ja_text': ja, 'en_text': en, 'ar_text_before': before,
        'ar_text_gemini': gem, 'verdict': verdict, 'final_ar_text': final, 'notes': note
    })

out_path = r'C:\Users\faisa\Ai\Mods Dev\OctopathTraveler0\localization_workspace\verify_part06_result.csv'
with open(out_path, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['id','ja_text','en_text','ar_text_before','ar_text_gemini','verdict','final_ar_text','notes'])
    w.writeheader()
    w.writerows(out_rows)

c = Counter(x['verdict'] for x in out_rows)
print(c)
print(len(out_rows))
