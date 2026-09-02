# Pipeline notes (for contributors)

Working files, not needed to play. Everything player-facing is in the README and the Releases page.

## Layout

| Path | What |
|---|---|
| `localization_workspace/PROJECT_STATE.md` | Running log: recon, decisions, every stage with dates |
| `localization_workspace/phase1_FINAL_v2.csv` | Final dialogue corpus (id, ja, en, ar) |
| `localization_workspace/phase1b_FINAL_v2.csv` | Final second-phase corpus |
| `localization_workspace/gapfill_FINAL.csv` | Final gap-fill rows |
| `localization_workspace/batch2_final.csv`, `batch1_*.csv` | Named-entity / early batches |
| `localization_workspace/scripts/` | Extraction, translation drivers, proofread, inject, msgpack codec |
| `localization_workspace/installer/` | .NET WinForms installer source (`Program.cs`, ui assets) |
| `nexus_description_ar.txt` | Nexus page text |

## Facts (verified in PROJECT_STATE.md / installer source)

- Game: OCTOPATH TRAVELER 0, Steam AppID **3014320**, Square Enix **Kingship** engine (UE5.4 fork).
- Text lives in msgpack-encoded `m_gametext` tables under `Content/Local/DataBase/GameText/Localize/<culture>/` (`kingship_msgpack.py` is the codec).
- Delivery = language-slot hijack: Arabic overwrites the **EN-US** rows; player selects «English».
- ~49,600 translated rows across the three FINAL CSVs; source of truth is the Japanese column.
- Mod files installed to `Octopath_Traveler0\Content\Paks\~mods\ZZZZZZ-Arabic Localization-1-0-0\` (`OctopathArabic_StatFix_P.pak` + `OctopathArabic_Logo_P.pak`) plus `OctopathArabicRTL.asi` in `Binaries\Win64\` (RTL UI alignment; requires an ASI loader).
- Uninstall = delete those files; nothing original is touched.

## Stages

1. `extract_corpus.py` — dump ja/en text tables to CSV.
2. Translation drivers (`drive_translate_all.py`, `gemini_translate.py`) — MSA draft from the Japanese source.
3. `gemini_proofread.py` + verify passes (`verify_part*.csv`) — proofread and diff-verify chunks.
4. `postprocess_mechanical.py` — deterministic sweep (punctuation, digits, placeholders).
5. `inject_table.py` + `kingship_msgpack.py` — write Arabic back into the EN-US tables.
6. repak — pack the modified tables + fonts + logo into `_P` paks.
7. `installer/` — .NET single-file installer; payload = the two paks + the RTL asi.

## Rebuilding

Needs the game installed (Steam), Python 3, repak, and the scripts above. Game files, extracted assets, built paks and installer binaries are not committed.

Installer: `cd localization_workspace/installer && dotnet publish -c Release -r win-x64 --self-contained -p:PublishSingleFile=true -o publish` after regenerating `payload.zip`.
