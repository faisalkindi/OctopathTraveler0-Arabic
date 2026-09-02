# Game Context — Octopath Traveler 0

> Foundation artifact #3 (per `LOCALIZATION_METHODOLOGY.md`). Sourced from: our own extracted corpus
> (`corpus/GameTextCharacter.csv`, `GameTextMap.csv`, `GameTextGraphic.csv`) + verified web research
> (Wikipedia, Destructoid, Kotaku, Inverse, RPGSite, Polygon, Pocket Tactics — all 2025-12 release reviews).
> Read this fully before translating a single line.

## What the game is
Console remake (Switch/Switch 2/PS4/PS5/Xbox/PC, released 2025-12-04) of the 2020 Japan-only mobile gacha
title *Octopath Traveler: Champions of the Continent*. Square Enix stripped the gacha/mobile mechanics for
this release — it's a full premium HD-2D JRPG, ~100 hours, built on the same world (**Orsterra**) as the
original *Octopath Traveler* duology.

## Protagonist
**A player-created custom character** (a franchise first — no more 8 fixed protagonists). Silent/customizable:
player picks appearance, voice, job, a learned skill, a favorite dish, 3 starting belongings, and a name via
the `GameTextCharacterCreate` flow. Backstory: a resident of the small village of **Wishvale**, which is
burned to the ground by three villains hunting a legendary ring tied to the god **Aelferic**. The story is
one of vengeance and rebirth as the protagonist hunts those responsible and rebuilds Wishvale.

## Structure — 3 villain-centric arcs + 1 town-building arc, playable in any order
- **Bestower/Master of Wealth** — antagonist **Lady Herminia**, "the Covetous Witch" (狩王女ヘルミニア /
  大富豪ヘルミニア), ruler of **Valore**. Reviews describe her arc's tone as darker/crime-adjacent.
- **Bestower/Master of Fame** — antagonist **Auguste**, "the genius playwright" (劇作家アーギュスト), based in
  **Theatropolis**, "the city of the arts." Described by reviewers as JoJo's-Bizarre-Adventure-esque intrigue.
- **Bestower/Master of Power** — antagonist **Tytos** ("Tytos the Thunderblade" / commander of the **Scarlet
  Wings**), based in **Emberglow**. Reviewers compare this arc's tone to Fire Emblem-style warring nations.
- **Wishvale rebuilding** — town-management mode; recruit NPCs as Residents, raise Wishvale's Town Level.
- After all three arcs: **Master of All**, the endgame convergence.
- Each arc is villain-centric and largely self-contained ("its own separate credit roll" — RPGSite), so
  translate scene-by-scene in order per arc, not just by raw ID order.

## Tone (confirmed — this decides the Arabic register)
Reviewers consistently describe the writing as **"grounded," "grittier," "fantastically written," with complex,
morally-gray characters** — explicitly contrasted against lighter, more colorful high-fantasy JRPGs (Pocket
Tactics: "considerably grittier... a lot more grounded, despite the fantasy setting"). Our own extracted
dialogue confirms this in practice — plain, natural modern English, not archaic/purple prose:
> "Have you heard the rumors about Lady Herminia?" / "They say she'd happily slaughter her own child for coin!"

**This is the OPPOSITE calibration from FFT: The Ivalice Chronicles** (which used elevated literary MSA to
match its deliberately archaic "War of the Lions" script). Octopath Traveler 0's source register is modern,
grounded, natural — per `LOCALIZATION_METHODOLOGY.md`'s calibration rule ("source-localization register +
setting → target register"), this calls for **warm, natural MSA (فصحى ميسّرة)** — the methodology's
*adventure-default* register, not the elevated/archaic exception used for FFT.

## Returning cast from the original *Octopath Traveler* (recruitable companions, not protagonists here)
Olberic (Warrior), Tressa (Merchant), Therion (Thief), Alfyn (Apothecary), H'aanit (Hunter), Ophilia (Cleric),
Cyrus (Scholar), Primrose (Dancer) — the original 8 "octopaths," now supporting cast.

## New companions (partial list, 28+ more recruitable characters)
Viator, Reime, Ludo, Carinda, Celsus, Heidne, Esperre, Macy, Phenn, Delitia, Pius, Laurana, Xerc, Alexia,
Goodwin, Saoirse — plus royalty/nobility tied to the main plot: Bargello, Alaune, Richard, Solon, Eltrix,
Rondo, Tatloch, Stia, Sazantos, El, Isla.

## Nations/kingdoms referenced
**Riven**, **Edoras** (Castle Edoras appears repeatedly — royal seat), **Altinia** — soldiers/armies of each
appear in the corpus (`リーヴェン兵`=Riven Soldier, `エドラス兵`=Edoras Soldier, `アルティニア兵`=Altinian Soldier).

## World — 8 regions of Orsterra (confirmed via `GameTextMap.csv`)
Frostlands, Flatlands, Coastlands, Highlands, Sunlands, Riverlands, Cliftlands, Woodlands — each with its own
towns (e.g. Woodlands→Valore; Cragspear/Castle Edoras cluster; Rippletide/Isle of Orsa; Sunshade).

## Job classes (8 standard + special/unique)
Standard: Warrior (剣士), Apothecary (薬師), Thief (盗賊), Scholar (学者), Cleric (神官), Hunter (狩人),
Merchant (商人), Dancer (踊子). Special/plot-tied: Lord, Queen, King, Wise King, Captain, Knight Ardante,
Empress, Architect, Cait Scholar ("学者猫" — a talking scholar-cat, ties to `GameTextStoryBook`'s "学者猫と
追憶の書" title we found, though that specific table is flagged SKIP as legacy mobile-game content), Flameguard.

## Speaker/character ID table
`corpus/GameTextCharacter.csv` is the master speaker-name reference (JP name → official EN name, keyed by a
numeric character ID, e.g. `20101=Olberic`, `28572=Lady Herminia`, `116288=Commander Tytos`). **Use this as the
authoritative name-spelling source and as the speaker-ID key for the conversation-aware gender pass** — do not
re-derive spellings independently.

## Cross-reference note
No French/Spanish/Italian locale export was found in this pak (only EN-US/KO-KR/ZH-CN/ZH-TW) — the
Rule 0 Case B "check Romance-language gendered exports" trick from the methodology doesn't apply here.
Instead, gender for JA-ambiguous lines should be resolved from the JP source itself (JP marks speaker
gender via sentence-final particles/self-reference terms) plus the character-name table above (most named
character genders are already public knowledge, verifiable via the same character-guide sources cited here).
