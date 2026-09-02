# Arabic Style Guide — Octopath Traveler 0

> Foundation artifact #5 (per `LOCALIZATION_METHODOLOGY.md`). Instantiates the reusable style-guide template
> from that doc, calibrated with `arabic-culture-guide` + `arabic-brand-voice` skills and the confirmed
> register finding in `GAME_CONTEXT.md`. **Lock this in the pilot (~300 lines), then hold it game-wide.**

## Register decision (confirmed, not guessed)
Source English is **grounded, modern, natural** JRPG prose — reviewers explicitly call it "grittier" and "more
grounded" than typical high fantasy; our own corpus samples read as plain modern English
("Have you heard the rumors about Lady Herminia?"). Per the methodology's calibration rule, this takes
**فصحى ميسّرة — warm, natural, everyday MSA** (full MSA grammar, flowing modern vocabulary), **not** the
elevated/archaic literary MSA used for FFT: The Ivalice Chronicles' deliberately archaic script. Avoid both
street dialect and stiff bureaucratic/classical MSA.

## Target audience
Broad, multi-regional Arab gamers (per `arabic-culture-guide`: unclear/multi-regional audience → MSA, not a
regional dialect — matches our established cross-project default from Elliot/FFT).

## Voice dimensions (per `arabic-brand-voice`)
- **Register:** فصحى ميسّرة (warm everyday MSA) as the default; individual characters may shift within that
  band per their established personality (a king/queen/noble reads slightly more formal within MSA; a
  street-tough companion reads plainer) — but nobody breaks into dialect or classical سجع.
- **3 personality anchors for the narration/system voice itself** (not per-character, which is handled by
  the conversation-aware gender + character-voice pass): **صادق** (honest/grounded — matches the "grounded,
  gritty" source tone, avoid inflating drama with flowery language), **متدفق** (flowing/natural — full MSA
  grammar but reads like spoken narration, not a legal document), **مباشر** (direct — short declarative
  sentences over long subordinate clauses, matching the source's plain prose).
- **Never:** corporate/bureaucratic Arabic filler (إنّ الأمر يتطلّب منك أن... where يجب أن... works), classical
  رجزّ/سجع rhymed prose, third-person address of the player ("يستطيع اللاعب..."), mixed dialect.

## Address/gender
- The protagonist is **player-created and silent**. **CONFIRMED (Game8, verified 2026-07-06):**
  "主人公の見た目を男性・女性どちらかにしても、ストーリーに影響はしません" — choosing a male or female
  appearance has **zero effect on the story text**; there is **no gender-branching dialogue system** at all.
  **This is now a locked, permanent rule, not a to-verify item:** every line addressing the player character
  — in `GameTextEvent`, `GameTextNPC`, anywhere — must use **gender-neutral Arabic phrasing** (verbal nouns,
  avoiding a committed أنتَ/أنتِ split second-person verb where the addressee is the player), since a single
  fixed text serves both player genders with no branching mechanism to draw from. Do not "default to
  protagonist's gender" here as the general style-guide address rule suggests for other games — that default
  is explicitly overridden for this game's player character.
- **★ Refinement (found during batch 1 grammar QA, 2026-07-07): true neutrality is only achievable for
  PAST-TENSE 2nd-person verbs** — `استعددت` is spelled identically whether addressing م/ف (the gender marker
  is an unwritten short vowel), so past-tense is the first tool to reach for. **PRESENT-TENSE verbs and
  predicate adjectives visibly mark gender in the spelling itself** (`تثق` vs `تثقين`; `مأسور` vs `مأسورة`) —
  there is no spelling-identical neutral form for these. When a line can't be rephrased into past tense or
  restructured to avoid a gendered predicate on the player (e.g. recasting the sentence so something else
  becomes the grammatical subject instead of "you"), the practical fallback is the **standard Arabic generic
  masculine** default — defensible and conventional for an unspecified addressee, but be clear this is a
  fallback, not literal neutrality. Prefer rephrasing to avoid the gendered form first; only default-masculine
  when rephrasing would be too awkward.
- For all other (named, canon-gendered) characters: standard conversation-aware speaker+addressee gender
  pass per `LOCALIZATION_METHODOLOGY.md` — resolve **both** parties per scene before translating, using
  `GAME_CONTEXT.md`'s cast list + `corpus/GameTextCharacter.csv` as the canonical gender reference (most of
  these are public, well-documented characters — verify via the same character-guide sources cited in
  `GAME_CONTEXT.md` rather than guessing from JP grammar alone where a name is already public knowledge).

## Harakat (تشكيل) — light, targeted, NOT full vocalization (per user directive 2026-07-07)
Per `LOCALIZATION_METHODOLOGY.md`'s general policy (render, but light — shadda always for
gemination, a single short vowel only where a word would otherwise be misread, otherwise bare),
**this project's specific target: roughly 10% of the corpus's lines should carry any diacritics
at all** — most lines stay completely bare. Prioritize:
- **Shadda (ّ)** on genuinely gemination-critical words where its absence changes meaning or
  reads oddly (e.g. distinguishing a doubled-consonant verb form) — this is the highest-priority
  mark, apply it whenever it's meaning-bearing, regardless of the 10% budget.
- **Fatha/kasra** short vowels only on words that would otherwise be genuinely ambiguous or
  misread out of context (e.g. disambiguating two words with identical bare spelling but
  different meaning/vowel pattern) — a handful of marks per *sentence* at most, never full
  word-by-word tashkeel.
- Never diacritize an entire line/sentence fully — that reads as over-marked per the established
  cross-project preference (a prior project measured ~5.7% character-level density as "a touch
  heavy"; stay lighter than that in per-character terms, while still hitting roughly 1-in-10
  *lines* carrying at least one meaningful mark).

## UI commands (freeze in the glossary, reuse identically — carried over from the established cross-project
defaults, unless this game's specific menu structure needs a different verb)
ابدأ/لعبة جديدة · متابعة (Continue) · رجوع (Back) · تأكيد/موافق (Confirm/OK) · إلغاء (Cancel) · نعم/لا ·
حفظ/تحميل (Save/Load) · الإعدادات (Settings) · إغلاق/خروج (Quit) · تجهيز (Equip) · استخدام (Use) ·
الخريطة (Map) · الحقيبة/العناصر (Inventory).

## RPG stat terms (one per concept, game-wide — HP/MP/Lv are known short-token risk, see Layout below)
HP→نقاط الصحة (short slot: صحة) · MP→نقاط السحر (short slot: سحر) · ATK→الهجوم · DEF→الدفاع · SPD→السرعة ·
EXP→الخبرة · Level/Lv→المستوى (short slot: مستوى) · **BP→نقاط التعزيز** (official JP: ブーストポイント
"Boost" Point, `GameTextGraphic` id=8 — REVISED 2026-07-09 from usage-based نقاط الطاقة to match the literal
name, user decision) · **SP→نقاط خاصة** (official EN: "Special Points" not "Support", id=9 — REVISED
2026-07-09 from usage-based نقاط المهارة, user decision) ·
Skill→مهارة · Ability→قدرة · **Break→كسر التوازن** (the stagger/weakness-break mechanic, `GameTextGraphic`
id=10) · **Critical→ضربة حرجة** · **Overkill→قتل مفرط** (id=6) · **Shield Guard→درع الحماية** (id=7 — ⚠️
every external JP/EN source incl. the official SE site calls this mechanic "Shield Point", not "Shield Guard";
unresolved whether it's the same mechanic, user chose to keep this rendering as-is 2026-07-09, revisit if
in-game confirms otherwise) · **Elemental Attack→هجوم العناصر, Elemental Defense→دفاع العناصر** (JP 属性,
idafa/noun form — LOCKED 2026-07-09 after user rejected the adjective عنصري despite it being real,
precedent-backed Arabic RPG convention [Genshin Impact, Ragnarok Online]; possessive/target contexts use
بالعناصر instead, see `GLOSSARY.csv`; Non-Elemental→بلا عنصر).
*(These 8 bolded terms are this game's own combat-system vocabulary, not carried from the cross-project
default list.)*

## Path Actions / arc-title vocabulary (this game's own system)
- **Path Actions** (the Wealth/Fame/Power interaction system — steal, duel, recruit-via-charm, etc.; JP:
  フィールドコマンド "Field Command", no direct JP phrase for the "Path Actions" umbrella label itself — this
  is an EN-only coined term for the international release) → **LOCKED 2026-07-09: تفاعلات مميزة** (system/menu
  label, plural) **/ تفاعل مميز** (a single action, singular). Not a literal translation of "path" — "path"
  dropped per user direction; instead echoes the phrasing Arabic gaming press itself already uses to describe
  this exact mechanic ("...بطريقة مميزة" — Blue Gaming's review of this game, bluegamingsa.com). Checked for
  an existing Arabic-press term for "Path Actions" itself first (2 reviews of this game + 1 of the original
  2018 game all keep it untranslated in Latin script) — user rejected keeping it untranslated, wanted a real
  Arabic phrase instead.
- **Wealth / Fame / Power** (the 3 arc names, also in-fiction "virtues" characters are judged by; JP 富/名声/
  権力) → **الثروة / الشهرة / السلطة** (Power revised from القوة to السلطة 2026-07-09: 権力 = political
  authority, not physical strength; confirmed already correctly shipped as السلطة in GameTextUI ids
  27808/31003, user confirmed).
  but must read naturally in arc titles like "Bestower of Wealth," "Master of Power."
- **Ringbearer**, **Aelferic** (the god), the finger-named Rings (**Pathos of the Thumb**, **Apatheia of the
  Ring Finger** — confirmed via `corpus/GameTextCharacter.csv` ids 116343-116344) — proper nouns, transliterate
  + translate the epithet the same way names are handled below.
- **Wishvale** (home village), **Master of All** (endgame title) — proper nouns / fixed title, lock spelling.

## Names — transliterate by default, one spelling per name, frozen in the glossary
`GLOSSARY.csv` (724 rows, auto-generated from `corpus/GameTextCharacter.csv` + `GameTextPC.csv` +
`GameTextMap.csv`) is the starting skeleton — **Arabic column is intentionally empty**, to be filled during
the pilot and then frozen. Verify tricky readings against the official English spelling already captured in
that CSV (e.g. `H'aanit`, `Tytos`/`Sazantos` distinct spellings, `Alaune` vs `Alauné`-style temptation) —
don't re-derive transliteration from the Japanese kana alone when an official EN spelling already exists.

## Arabic punctuation
`،` `؛` `؟` (not ASCII `,` `;` `?`). No space before punctuation, one space after, no double spaces. Dialogue
quotes «…». Ellipsis `…` (single char), preserve count for pacing. Never touch punctuation inside a
placeholder/tag (`{0}`, `{1}`, `<NL>`/`\n`).

## Numbers
Western digits 0–9 for gameplay. Never localize digits inside `{0}`/`{1}` placeholders.

## Layout
Respect the source's line breaks (`\n` inside `m_gametext` strings) — for the base game's UE-native rendering
these control text-box pacing, don't add/remove arbitrarily. **UI micro-slots**: watch for the same "HP/MP/Lv"
overflow risk documented in `LOCALIZATION_METHODOLOGY.md` (short English token → long Arabic term breaks a
fixed-width slot) — use the short variants noted above only where the *source string itself* is the terse
token (exact match), keep the full term elsewhere.

## Placeholders / tags — non-negotiable, every batch prompt must state these
1. **Preserve every placeholder byte-for-byte, same count:** `{0}`, `{1}`, etc. (confirmed present in
   `GameTextQuestJP`-style templates and item/skill descriptions), and the literal `\n` line breaks inside
   `m_gametext` strings (confirmed present in dialogue, e.g. `"あんたも"魔女"に\n歯向かおうってクチかい？"`).
2. Never translate the `m_id`/re-injection key.
3. **Skip** the tables flagged SKIP in `PROJECT_STATE.md` (`GameTextQuestJP`, `GameTextStoryBook`,
   `GameTextSupport`, `GameTextLifepath`, `GameTextPartVoice`) — leftover mobile-game/dev-test content, not
   shipped to players. Flag, don't translate, any row that looks like debug/test data if found elsewhere.

## Forbidden patterns
❌ literal calques that break Arabic syntax · ❌ altering/translating/reordering/spacing any `{n}` placeholder
or `\n` · ❌ mixing dialects in MSA · ❌ inconsistent term/name spellings (check `GLOSSARY.csv` first) ·
❌ over-formal filler · ❌ ASCII `?,;` inside Arabic · ❌ translating the leftover mobile-game tables above ·
❌ elevated/archaic MSA (that's FFT's register, not this game's).
