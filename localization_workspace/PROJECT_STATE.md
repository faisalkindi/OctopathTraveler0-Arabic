# PROJECT_STATE.md — Octopath Traveler 0 Arabic Localization

> Recon per `GAME_TRANSLATION_PLAYBOOK.md` Phase 1. Translation craft follows `LOCALIZATION_METHODOLOGY.md`.
> Prior art studied: `Elliot/localization_workspace/REFERENCE_octopath0_method.md` (reverse-engineered from a
> third-party Arabic mod for this same game). We reuse its **delivery pipeline** only — translation is done
> fresh, from-scratch, to our own quality bar.

## Install
- `H:\Steam\steamapps\common\Octopath_Traveler0\`
- Exe: `Octopath_Traveler0\Binaries\Win64\Octopath_Traveler0-Win64-Shipping.exe`
- Already has **UE4SS v3.0.1 Beta** installed + a couple of gameplay mods (100% Path Actions, Quick Study) +
  a Vortex-managed mod (`Octopath0Fix`) — mod manager in play, be mindful of load order.

## Engine
- **Unreal Engine 5.4** (confirmed via UE4SS log: `Found EngineVersion: 5.4`).

## Pak format
- **Single legacy `.pak`**, NOT IoStore — no `.ucas`/`.utoc` anywhere in the install.
  `Octopath_Traveler0\Content\Paks\pakchunk0-Windows.pak` (1.92 GB, 169,605 file entries).
- repak info: `version: V11`, `version major: Fnv64BugFix`, `encrypted index: true`, `compression: Oodle`,
  `path hash seed: 911B56BB`, mount point `../../../`.
- **AES key (confirmed working via `repak info`):**
  `0x14A2B6A734EE06B2B011E847AFFCD1DB9CB46C049B1AA5E3F44CCFE332EF6CDA`
  (AESDumpster returned 3 candidates; this is the one with successful `repak info` parse — highest entropy, 3.825).
- **This means the simpler Octopath-0-mod delivery applies, not the Elliot IoStore-triple path:** a loose
  legacy `.pak` placed in `Content\Paks\` with a filename that sorts alphanumerically last (e.g.
  `ZZZ_Arabic_999_P.pak`) overrides the base pak's DataTables/fonts directly. **No `retoc to-zen` / IoStore
  repacking needed** — confirmed by the existing third-party mod using exactly this method successfully.

## Text location — GameText DataTables (not `.locres`)
Same family as documented in `REFERENCE_octopath0_method.md`: `m_id → m_gametext` row-based DataTables under
`Octopath_Traveler0/Content/Local/DataBase/GameText/`.

- **Base folder (no locale prefix) = the default/dev language** — same pattern FFT/FF16 uses for Japanese.
  `GameText/SystemText/GameTextScenarioReplay.uasset` + `GameText/TalkText/GameTextEvent.uasset` (no
  `Localize/<culture>/` prefix). **Needs confirmation it's actually Japanese** (see To-verify below) —
  if so, this is Rule 0's "translate from the original" source.
- **Exported locales under `Localize/`:** `EN-US`, `KO-KR`, `ZH-CN`, `ZH-TW`. **No `JA-JP` folder exists** —
  consistent with JA being the unsuffixed base, not a separate locale export.
- **SystemText tables** (under `GameText/Localize/EN-US/SystemText/`, 15 tables): GameTextCharacter,
  GameTextCharacterCreate, GameTextEnding, GameTextEnemy, GameTextFC, GameTextGraphic, GameTextItem, GameTextMap,
  GameTextPC, GameTextPartVoice, GameTextQuest, GameTextScenarioReplay, GameTextSkill, GameTextUI, GameTextVillage.
- **TalkText table** (dialogue): `GameText/Localize/EN-US/TalkText/GameTextEvent.uasset` — this is almost
  certainly the big one (story dialogue), analogous to Elliot's largest batch.
- **Hijack plan (mirrors the third-party mod, verified approach):** overwrite the **EN-US** `m_gametext` rows
  with Arabic (player selects English in-game → sees Arabic) — same as the existing mod. Translate from the
  **base/JA source** per Rule 0, using EN-US as the QA cross-reference AND as the injection target.

## Fonts
- UI fonts are standard UE **`.ufont`** FontFace assets (not glyph-atlas — this is the "GENERAL" UE track, not
  the FF7R/FF16 special tracks) — confirmed 23 `.ufont` files under `Octopath_Traveler0/Content/UI/Font/`
  (e.g. `9PCS_CinemaLetter_Std_L`, `9PCS_ClearTone_Default`, `9PCS_Franco_B/Default`, `9PCS_KR_ShinGoHang_DB/R`,
  `9PCS_Now_Std_GB`, `9PCS_Rocio_Default`, …).
- Reuse the pipeline in `LOCALIZATION_METHODOLOGY.md`/`GAME_TRANSLATION_PLAYBOOK.md` §Fonts: default font
  **SST Arabic Medium** (`_shared\fonts\SST-Arabic-Medium_sanitized.ttf`), replace every `.ufont`, watch for
  the exit-crash table-stripping gotcha (already handled in the sanitized file), audit **per-field font
  binding** (a screen can use more than one font asset for different text fields — verify each).
  Third-party mod used **Bahij TheSansArabic** (OFL) instead — an option, but SST is our verified default.

## Reference material already extracted locally (third-party mod, for pipeline study only)
- `C:\Users\faisa\Ai\Mods Dev\Elliot\_reference\OCTOPATH TRAVELER 0_arabic.exe_extracted\` — the PyInstaller
  installer, unpacked. Its actual mod pak: `mom\mohammad\Octopath_Traveler0\...`.
- `H:\_octo_pak\Octopath_Traveler0\Content\Local\DataBase\` + `H:\_octo_pak\...\Content\UI\Font\` — that mod's
  pak already extracted to disk (confirms the DataTable/font paths above independent of our own pak listing).
- `H:\_octo_work\octo.exe_extracted\` — same installer, extracted again (Python runtime dump, not useful beyond
  `installer.pyc`/`mom\` already covered above).

## ★★★ SOLVED — the Kingship `BinaryData` blob is plain MessagePack (verified byte-for-byte)
Reverse-engineered directly from raw bytes, confirmed on two tables (`GameTextEvent`, `GameTextUI`):
- **Structure:** `[10-byte header][MessagePack object][8-byte trailer]`.
  - Header (10 bytes): starts `00 00 00 00 00`, then 3 bytes that vary per file (looks like a size/count field —
    not yet decoded precisely, but **irrelevant for round-trip**: on rebuild just re-derive from the actual
    msgpack byte length, don't hand-craft it).
  - Trailer (8 bytes): **constant across every file checked** — `00 00 00 00 c1 83 2a 9e`.
  - MessagePack payload: `{"m_DataList": [ {...row...}, ... ]}`. Row schema varies slightly by table:
    - `GameTextEvent` (dialogue): `{m_id: int, m_voiceId: int, m_gametext: [12 strings]}`
    - `GameTextUI`: `{m_id: int, m_gametext: [12 strings]}` (no voice — makes sense, UI has no VO)
  - `m_gametext` is a **fixed 12-element array**, one slot per language. **Each per-locale `.uexp` file only
    populates slot 0** with its own language's text; the other 11 slots are empty strings in every file checked
    (base=JA in slot 0, EN-US=English in slot 0). This matches the `LANG_INDEX` column in the third-party mod's
    export (`LANG_INDEX` was always `0` in every row of their EN-US dumps).
- **Verified against the third-party mod's Arabic export, exact match:** base JA row `m_id=413302` →
  `"あんたも"魔女"に\n歯向かおうってクチかい？"` corresponds to their Arabic `413302 || 0 || "أنت تخطط لمواجهة<NL>الساحرة أيضا?"`
  — same ID, same line-break position (`\n` ↔ `<NL>`). **Confirms Rule 0: the base/unsuffixed tables ARE the
  Japanese source**, and the injection target is EN-US slot 0, exactly as planned.
- **Tooling:** any standard **MessagePack** library works (`pip install msgpack`; verified with `msgpack` 1.2.1
  on Python 3.13, matching the game's bundled Python — decode via `msgpack.Unpacker` in streaming mode, since
  `unpackb` errors on the trailing 8 bytes). No custom parser, no FF16Tools-style bespoke tool needed — this is
  simpler than every other engine track in the methodology docs.
- Row counts confirmed: `GameTextEvent` (dialogue) = **21,656** rows; `GameTextUI` = **2,665** rows (both tables
  same count in base vs EN-US, as expected — same schema, different populated language slot).

## ★★★★★ SOURCE CORPUS EXTRACTED — Phase 2 done (2026-07-06)
`scripts/kingship_msgpack.py` (reusable read/write module) + `scripts/extract_corpus.py` (walks all 21 tables,
matches base-JA rows to EN-US rows by `m_id`) produced one CSV per table in `corpus/`
(`id, voice_id, category, ja_text, en_text`). **60,843 total rows.**

| Table | Rows | Base(JA) file? | EN-US file? |
|---|---|---|---|
| GameTextCharacter | 491 | Y | Y |
| GameTextCharacterCreate | 101 | Y | Y |
| GameTextEnding | 2,958 | Y | Y |
| GameTextEnemy | 999 | Y | Y |
| GameTextFC | 5,412 | Y | Y |
| GameTextGraphic | 27 | **N** | Y |
| GameTextItem | 3,332 | Y | Y |
| GameTextLifepath | 87 | Y | **N** |
| GameTextMap | 390 | Y | Y |
| GameTextPC | 21 | Y | Y |
| GameTextPartVoice | 7,749 | **N** | Y |
| GameTextQuest | 1,185 | Y | Y |
| GameTextQuestJP | 2,220 | Y | **N** |
| GameTextScenarioReplay | 565 | Y | Y |
| GameTextSkill | 5,227 | Y | Y |
| GameTextStoryBook | 379 | Y | **N** |
| GameTextSupport | 61 | Y | **N** |
| GameTextUI | 2,665 | Y | Y |
| GameTextVillage | 523 | Y | Y |
| **GameTextEvent** (dialogue) | **21,656** | Y | Y |
| **GameTextNPC** (NPC barks) | **4,795** | Y | Y |

## ★★★★★★ RESOLVED — the 6 base-only/EN-only tables (2026-07-06)
**Context that explains all of them:** Octopath Traveler 0 is a console remake of the 2020 Japan-only mobile
gacha game *Octopath Traveler: Champions of the Continent* — Square Enix explicitly stripped out gacha and
other mobile-only mechanics for the console port (confirmed via Wikipedia / Kotaku / HandWiki, 2026-07-06).
That maps directly onto the file evidence:

| Table | Verdict | Evidence |
|---|---|---|
| `GameTextQuestJP` (2,220 rows) | **SKIP** — leftover mobile-game system | Row content is quest-condition templates referencing "Clan influence" (`クランの影響力`) — a guild/clan mechanic explicitly removed for the console port |
| `GameTextStoryBook` (379 rows) | **SKIP** — leftover mobile-game replay menu | Story/side-story index (`学者猫と追憶の書` etc.) superseded by `GameTextScenarioReplay`, which **is** fully localized (565 rows, real EN-US content) |
| `GameTextSupport` (61 rows) | **SKIP** — dev/test data | Literally named `チュートリアルテスト` ("Tutorial Test") / `ヘルプテスト` ("Help Test"), almost entirely empty rows |
| `GameTextLifepath` (87 rows) | **SKIP** — leftover mobile-game backstory system | Character-origin flavor text, superseded by `GameTextCharacterCreate`, which **is** fully localized and confirmed real (skill/job/appearance/name creation flow) |
| `GameTextGraphic` (27 rows) | **★ TRANSLATE** (EN→AR, Rule 0 Case B — no JA source exists) | Verified genuinely distinct per-language content — pulled KO-KR and ZH-CN versions of the same rows and confirmed **real, different Korean/Chinese text** (not copies), incl. the wealth/fame/power prologue narration cards and combat HUD terms (Critical/Miss/BP/SP/BREAK). Added fresh for the international port — the JP release likely bakes this into video/texture instead. |
| `GameTextPartVoice` (7,749 rows) | **SKIP** — not real translated content | Verified **identical untranslated Japanese** text in the EN-US, KO-KR, **and** ZH-CN slots (pulled and compared first 10 rows of each) — never actually localized in any shipped language; almost certainly internal voice-bark reference/caption data, not player-facing text |

**Net effect on translation scope:** drop the 5 SKIP tables (10,496 rows) from the corpus entirely; keep
`GameTextGraphic` (27 rows, EN→AR) as a small Rule-0-Case-B exception alongside the 15 JA-sourced tables.
**Revised real corpus size: 60,843 − 10,496 = 50,347 rows** (this still includes `GameTextGraphic`'s 27 EN-only
rows counted normally). Caveat: this is a well-evidenced inference (file content + public facts about the game's
mobile-game origin), not a 100%-certain in-game confirmation — worth a final sanity check once we're deep enough
into a table's context to notice if any of these IDs turn out to be referenced live (e.g. a quest that reads a
`GameTextQuestJP` ID at runtime).

## ★★★★ VERIFIED END-TO-END IN-GAME — full round-trip pipeline confirmed (2026-07-06)
Built a test mod that wraps every `GameTextUI` EN-US string in `★...★` markers and deployed it as a loose pak.
**Confirmed working in-game** (player saw the star-wrapped text in the Options → language selector) after one
false start that revealed a critical extra step:

1. **First attempt crashed on launch.** UE crash report (`Saved/Crashes/UECC-Windows-.../CrashContext.runtime-xml`)
   gave the exact cause, no guessing needed:
   `BinaryAsset .../GameTextUI.GameTextUI: Serial size mismatch: Got 185109, Expected 170867`
   — a `LowLevelFatalError` in `AsyncLoading.cpp`.
2. **Root cause:** the `.uasset`'s export table stores a fixed `SerialSize` for its `.uexp` payload
   (standard UE `FObjectExport` field). We'd copied the `.uasset` unchanged but grew the `.uexp` (Arabic/marked
   text is virtually always a different byte length than the source) — size mismatch → hard crash. **This will
   happen on every single table we translate unless patched every time.**
3. **The fix — patch `SerialSize` in the `.uasset` after every `.uexp` rebuild:**
   - `SerialSize` (`int64` LE) and `SerialOffset` (`int64` LE, immediately following) live in the `.uasset`'s
     export table at a **fixed byte offset for this asset** (found empirically per-table via
     `UAssetGUI tojson` on the tiny ~700-byte `.uasset`, then `struct.pack('<q', old_value)` to locate the exact
     offset in the raw bytes — confirmed at offset **633** for `GameTextUI.uasset`, will differ per table/NameMap
     size so **re-derive per table**, don't hardcode 633 globally).
   - **The formula:** `SerialSize = new_uexp_file_total_size - 4` (verified: original EN-US GameTextUI.uexp was
     170871 bytes, original SerialSize was 170867 = size−4; after patching, new uexp was 185113 bytes → set
     SerialSize=185109 = size−4 — crash log's "Got 185109" was literally telling us the expected value ahead of
     time). The trailing 4 bytes (half of the constant 8-byte trailer) are excluded from SerialSize.
   - `SerialOffset` does **not** need to change (it's the `.uasset`'s own size / bookkeeping offset, unaffected
     by `.uexp` content).
4. **Delivery confirmed too:** a loose **V3, unencrypted, uncompressed** pak (matching the format of existing
   working community mods, NOT the base game's V11/Oodle/encrypted format) dropped in
   `Content\Paks\~mods\<AnyFolderName>\<Name>_P.pak` loads correctly — no IoStore repacking, no encryption
   needed for our own mod pak.

**This is now a fully proven, reusable recipe** for injecting any GameText table:
`decode MessagePack → edit m_gametext[0] strings → re-encode → rebuild [header(len)+payload+trailer] →
patch .uasset SerialSize (size-4) at its located offset → pack loose V3 → drop in ~mods/<folder>/<name>_P.pak`.

**Test mod cleanup:** the `★`-marker test pak should be removed before real work
(`Content\Paks\~mods\ZZZZZZ-Arabic-Test-999-1-0-0\`) — it corrupts every UI string in the game.

## ★ Format discovery — GameText tables are a custom binary blob, NOT a plain UAsset DataTable
Confirmed via `UAssetGUI tojson` on `GameTextEvent.uasset` (base): the asset class is **`BinaryAsset`** in
package **`/Script/Kingship`** (Square Enix's internal engine/tooling name for this title) — the actual
`m_id`/`m_gametext` rows are **not** exposed as UAsset tagged properties. They're packed into a single opaque
`BinaryData` `ByteProperty` array inside the uasset's one export. Tojson-ing it byte-by-byte produced a
**1 GB JSON** of individual byte entries — confirms UAssetGUI/UnrealLocres can't read the rows directly; a
**dedicated binary parser for the Kingship format** is required (same shape as FF16Tools' `.nxd`/`.pzd` handling
for other SE titles, or the third-party mod author's own tool).

**★★ The third-party mod's extracted files already include a working export** — every `.uexp` under
`H:\_octo_pak\Octopath_Traveler0\Content\Local\DataBase\GameText\Localize\EN-US\...` has a sibling
`<name>.uexp_export.txt` in a simple `ID || LANG_INDEX || TEXT` format (`=====` separator line, `<NL>` as the
line-break token). **This confirms the record structure** (id, lang_index, text) and, as a side effect, hands
us the **mod's complete existing Arabic translation**:
- `GameTextEvent.uexp_export.txt` — **21,656 lines** (dialogue — the big one)
- `GameTextNPC.uexp_export.txt` — **4,797 lines** (NPC barks)
- `GameTextUI.uexp_export.txt` — **2,687 lines** (UI)
- (presumably all 15 SystemText tables + TalkText have one each — same pattern, not all inspected yet)
- No tool/script that produced these was found alongside them in `_octo_pak`/`_octo_work` — likely came bundled
  from the modder's own build process. **`installer.pyc`** (PyInstaller bytecode, in
  `Elliot/_reference/OCTOPATH TRAVELER 0_arabic.exe_extracted/`) may contain the actual read/patch logic in
  Python — not yet decompiled/inspected.
- **Per the user's decision to reuse the pipeline only and redo translation fresh:** this existing Arabic text
  is NOT our translation source, but it is a **useful reference/QA aid** (e.g. spot-checking our own gender/term
  decisions against a shipped precedent) and a candidate (pending quality review) for a Lara-shift-style TM
  seed if it holds up.

## To-verify (next recon steps, not yet done)
1. **Confirm the base/unsuffixed GameText tables are actually Japanese** (open one with UAssetGUI `tojson`
   after generating a `.usmap` — see below — and read a few `m_gametext` values).
2. **Generate the `.usmap`** for UE 5.4 via `jmap` against this game (needed for UAssetGUI to parse UE5
   unversioned properties in the DataTables) — copy to `%LOCALAPPDATA%\UAssetGUI\Mappings\Octopath0.usmap`,
   set `PreferredMappings="Octopath0"`, `PreferredVersion="VER_UE5_4"`.
2b. Confirm `EnExtract`/`UAssetGUI` can open `GameTextEvent.uasset` (TalkText/dialogue) — this is a DataTable,
    not a `.locres`, so `UnrealLocres` does NOT apply here; use `UAssetGUI tojson` (or EnExtract dump) instead,
    same as the Octopath-0-mod / Elliot's "DataTable style" note.
3. **Row count per table** (esp. `GameTextEvent` = dialogue) to estimate corpus size and Lara/Gemini budget.
4. **Speaker/gender metadata** — check whether `GameTextEvent` rows carry a speaker/character ID column (needed
   for the conversation-aware gender pass — methodology's biggest quality lever).
5. **RTL widget behavior** — untested; Octopath 0 (like Elliot) is UE5, standard `Slate.DefaultTextFlowDirection`
   + per-widget `Justification`/`FlowDirectionPreference` levers from the playbook should apply, but verify
   in-engine once first Arabic text is injected.
6. Check `DefaultEngine.ini` location for the RTL flag injection point (likely inside this same base pak).

## ★★★★★★★ Foundation artifacts #3-5 done (2026-07-06)
Built using `arabic-culture-guide` + `arabic-brand-voice` skills, Exa research (verified via Wikipedia/
Destructoid/Kotaku/Inverse/RPGSite/Polygon/Pocket Tactics, all dated around the 2025-12-04 release), and our
own corpus data (`GameTextCharacter.csv`, `GameTextPC.csv`, `GameTextMap.csv`, `GameTextGraphic.csv`):
- **`GAME_CONTEXT.md`** — confirmed: player-created silent protagonist (franchise first), Wishvale
  origin/revenge plot, 3 villain-centric arcs (Wealth/Herminia, Fame/Auguste, Power/Tytos) + town-building,
  returning original-Octopath cast as companions, 28+ new companions, full character-ID→name table.
- **`STYLE_GUIDE.md`** — **register confirmed as warm everyday MSA (فصحى ميسّرة)**, the OPPOSITE calibration
  from FFT: The Ivalice Chronicles (elevated/archaic) — this game's English is explicitly "grittier/grounded"
  per multiple reviews, and our own corpus samples read as plain modern prose. Locked this game's own combat
  vocabulary (BP/SP/Break/Overkill/Shield Guard) as TBD-in-pilot terms, flagged the open question of whether
  NPC dialogue branches by player-selected gender (to-verify before the pilot).
- **`GLOSSARY.csv`** — 724-row skeleton auto-generated from corpus (character names, job classes, place
  names), Arabic column intentionally empty per methodology (terms locked during the pilot, not before).
- **Reusable script:** `scripts/build_glossary.py`.

**Not yet done:** the mandatory ~300-line pilot batch (methodology step 6) — translate a mixed sample, get it
reviewed, lock the glossary/style-guide decisions, THEN scale to the full ~50k-row corpus.

## ★★★★★★★★ Pilot batch translated + QA'd (2026-07-06) — methodology step 6 done
`scripts/select_pilot.py` selected **301 rows**: stratified sample across UI (50)/Item (40)/Skill (40)/
Quest (30)/NPC (20)/Character (10)/Map (10)/Village (10), plus **one contiguous in-context dialogue scene**
from `GameTextEvent` ids 1-100 (the Bargello-gang/Herminia-rumor opening scene in Valore) — translated
scene-by-scene per the methodology's rule, not as isolated rows.

Translated directly (not via Lara/Gemini — this is the human/Claude-judgment pilot pass) into
**`pilot_translated.csv`**, register = warm everyday MSA per `STYLE_GUIDE.md`.

**QA passed clean:** `scripts/qa_pilot.py` (mechanical placeholder/tag parity + newline-count check) — 0
issues after fixing 3 minor line-break mismatches. `arabic-ui-review` skill was invoked per instructions but
requires an external Fanar/OpenAI API key (`~/.arabic-review/.env`) not configured in this environment —
did the linguistic quality pass manually instead (إملاء/قواعد/صياغة/ترقيم categories from that skill's own
rule reference), applied directly rather than blocking on interactive `npx` setup.

**Term decisions locked and folded into `GLOSSARY.csv`** (now 731 rows, `scripts/apply_pilot_terms.py`):
- Character names: Herminia→هيرمينيا، Auguste→أوغست، Pierro Della→بييرو ديلا، Bargello→بارجيلو،
  Alaune→ألاون، Oskha→أوسكا، Wordsworth the Wealthy→وردزورث الثري، Pharamea→فارميا.
- World names: Orsterra→أورستيرا، Wishvale→ويشفيل، Cragspear→كراغسبير، Riven→ريفن، Edoras→إيدوراس،
  Altinia→ألتينيا، Frostlands→الأراضي الجليدية (translated, not transliterated — descriptive region name).
- System terms: **"leaves"** (currency) → أوراق · **BP→نقاط التعزيز, SP→نقاط خاصة** (REVISED 2026-07-09,
  see `STYLE_GUIDE.md` — originally usage-based نقاط الطاقة/نقاط المهارة, switched to match the literal
  official JP/EN names after user review) · **"It's go time." (recurring JA クールだ) → "...حان وقت العمل."**
  (fixed phrase, reuse identically everywhere) · **"Bestower of X" arc titles → واهب [الثروة/الشهرة/السلطة/كل
  شيء]** (Power corrected from القوة to السلطة 2026-07-09 — this note had the wrong word; the actually-shipped
  translation was already correct) · Octopuff (franchise mascot) → أوكتوبَف.

### ✅ Arbitration items — RESOLVED via Japanese authoritative sources (2026-07-06, Exa research)
All 5 open items from the pilot were verified against Japanese strategy/official sites (Game8, Square Enix
JP official site, GameWith, Nintendo JP, appmedia, gamecap) rather than left as guesses:

1. **"Hell" (辺獄) — CONFIRMED, locks in as الجحيم.** Verified via Game8/GameWith/monogamer: 辺獄 is a
   genuine proper-noun realm in the plot — a realm of the dead reached only in the endgame "Bestower/Master
   of All" chapter, where you can travel back and forth between "現世" (the present world) and "辺獄", and
   which contains "亡者となったかつての英雄たち" (former heroes turned into the restless dead). The EN
   localizers' choice of "Hell" is a deliberate, well-grounded translation of a real realm-of-the-dead
   concept, not a mistranslation — **الجحيم confirmed correct, not tentative.**
2. **碩学王アレファン vs Aelferic — CONFIRMED as two different gods, no conflict.** Verified via a detailed
   JP lore site (lushgreengame.com, "十二天の書"): Orsterra has **12 named gods (十二神)** —
   **アレファン (Alephan)**, the "Erudite King" god of knowledge/wisdom (source of "Alephan's Wisdom"), is
   entirely separate from **エルフリック (Elfrick)**, the "聖火神" (Sacred Flame God) who guides hearts with
   sacred fire — **Elfrick, not Alephan, is who English review coverage called "Aelferic."** My أليفان
   transliteration for Alephan was correct and unrelated.
3. **Player-address gender — CONFIRMED, neutral phrasing is the PERMANENT policy, not a stopgap.** Verified
   directly via Game8 (a major JP strategy site): **"主人公の見た目を男性・女性どちらかにしても、ストーリーに
   影響はしません"** ("Whether you make the protagonist's appearance male or female has no effect on the
   story") — there is **no dialogue branching by player gender** at all. This means every line addressing
   the player must already work for either gender in a single fixed text — my pilot's neutral-phrasing
   approach (e.g. avoiding gendered second-person verbs) is the **correct, permanent rule** for all
   player-addressed lines game-wide, not a fallback to revisit.
4. **Mikhail (ミハエル)** — not independently re-verified (low-impact, common name); ميخائيل stands unless
   an official transliteration surfaces later.
5. **"Invite" (招く) — CONFIRMED as a standard, unquoted Field Command, not special ironic quoting.**
   Verified via Game8/gamecap/appmedia/bozumemo: 招く is one of the game's official named **Field Commands**
   (フィールドコマンド) alongside 雇う(Hire)/勝ち取る(Win Over)/ねだる(Beg)/引き入れる(Recruit)/勧誘(Persuade)/
   買取る(Buy)/聞き出す(Ask About) — the mechanic that recruits NPCs to move into/reside in Wishvale. The
   quote-marks in that one quest line (`リラとジャスパーを"招く"`) are just that line's own stylistic quoting,
   not a general rule. **Revised glossary term: 招く/Invite → استضافة** (a clean Field Command noun matching
   our other short command terms), dropping the quote-styling from the pilot's `"ادعُ"` rendering — apply
   this revision the next time that quest line/table is touched.

## Toolbox
Reuse `C:\Users\faisa\Ai\Mods Dev\Elliot\localization_workspace\scripts\_tools\` as-is (repak, AESDumpster,
UAssetGUI, jmap, EnExtract, FModel, UnrealLocres — though UnrealLocres likely unused here since text is
DataTables not `.locres`).
