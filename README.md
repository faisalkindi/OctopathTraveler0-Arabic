<p align="center"><a href="https://ko-fi.com/kindiboy"><img src="https://img.shields.io/badge/Ko--fi-Support%20me%20on%20Ko--fi-ff5f5f?style=for-the-badge&logo=kofi&logoColor=white" alt="Support on Ko-fi"></a></p>

<h1 align="center">OCTOPATH TRAVELER 0 — التعريب الكامل</h1>
<p align="center">Complete Arabic localization for <b>OCTOPATH TRAVELER 0</b> (Steam) · تعريب كامل للعبة</p>

<p align="center">
  <a href="https://github.com/faisalkindi/OctopathTraveler0-Arabic/releases/latest/download/OctopathTraveler0_Arabic_Installer.zip"><b>⬇ تحميل المثبّت / Download installer</b></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/faisalkindi/OctopathTraveler0-Arabic/releases/latest/download/OctopathTraveler0_Arabic_Manual.zip">ملفات التثبيت اليدوي / Manual files</a>
  &nbsp;·&nbsp;
  <a href="https://github.com/faisalkindi/OctopathTraveler0-Arabic/releases">كل الإصدارات / All releases</a>
  &nbsp;·&nbsp;
  <a href="https://ko-fi.com/kindiboy">☕ Ko-fi</a>
</p>

---

## العربية

**ماذا يعرّب؟** يحوّل اللعبة بالكامل إلى العربية: نحو 50,000 سطرٍ مترجمة عن النصّ الياباني الأصلي (وليست نقلًا عن الإنجليزية)، مع واجهةٍ تراعي الاتجاه من اليمين إلى اليسار في القوائم والحوارات، وخطٍّ عربيٍّ واضح، وحتى شعار اللعبة في الشاشة الرئيسية بالعربية.

**المميزات**
- ترجمة كاملة بالعربية الفصحى الحديثة عن النصّ الياباني الأصلي حفاظًا على روح القصة.
- محاذاة يمين حقيقية في القوائم والحوارات — ليست مجرد نصٍّ عربيٍّ ملصوقٍ في واجهةٍ إنجليزية.
- خطٌّ عربيٌّ واضح في كل مكان: الحوار، القوائم، أسماء العناصر والمهارات والشخصيات.
- شعار اللعبة بالعربية في الشاشة الرئيسية.
- مسرد مصطلحات موحّد (الشخصيات، الأماكن، مصطلحات القتال) مطبَّق باتّساق عبر اللعبة كلها.
- آمن: ملفات منفصلة تُضاف إلى مجلد اللعبة، لا يُعدَّل أي ملف أصلي. الإزالة بنقرة واحدة.

**التثبيت (المثبّت)**
1. أغلق اللعبة تمامًا.
2. حمّل `OctopathTraveler0_Arabic_Installer.zip` من الرابط أعلاه وفكّ الضغط.
3. شغّل `Octopath Traveler 0 Arabic Installer.exe` — يكتشف مجلد اللعبة من Steam تلقائيًا (أو حدّده يدويًا) — ثم اضغط «تثبيت اللغة العربية».
4. داخل اللعبة: الإعدادات ← اللغة ← اختر «English» (تظهر العربية مكان النص الإنجليزي).

**التثبيت اليدوي**: فكّ `OctopathTraveler0_Arabic_Manual.zip` ثم:
- انسخ ملفَّي `.pak` إلى `...\steamapps\common\OCTOPATH TRAVELER 0\Octopath_Traveler0\Content\Paks\~mods\ZZZZZZ-Arabic Localization-1-0-0\`
- انسخ `OctopathArabicRTL.asi` إلى مجلد `Octopath_Traveler0\Binaries\Win64\` (يتطلب مُحمِّل ASI مثبَّتًا مسبقًا لتفعيل محاذاة اليمين؛ بدونه تعمل الترجمة والخط والشعار لكن دون محاذاة يمين).

**الإزالة**: المثبّت ← «إزالة اللغة العربية»، أو احذف الملفات المذكورة أعلاه.

## English

**What it covers.** A full Arabic conversion of the game: ~50,000 lines translated from the original Japanese script (not relayed through English), true right-to-left menu and dialogue alignment, a clean Arabic font, and an Arabic game logo on the title screen.

**Features**
- Complete Modern Standard Arabic translation from the Japanese original.
- Real RTL alignment in menus and dialogue — not Arabic text pasted into an English layout.
- Clear Arabic font everywhere: dialogue, menus, item/skill/character names.
- Arabic title-screen logo.
- Consistent, hand-reviewed glossary (characters, places, battle terms) across the whole game.
- Safe: separate add-on files only; no original game file is modified. One-click uninstall.

**Install (installer)**
1. Close the game completely.
2. Download `OctopathTraveler0_Arabic_Installer.zip` above and unzip it.
3. Run `Octopath Traveler 0 Arabic Installer.exe`; it finds the Steam install automatically (or pick the folder), then click the install button.
4. In game: Settings → Language → «English» (Arabic replaces the English slot).

**Manual install**: unzip `OctopathTraveler0_Arabic_Manual.zip`, then:
- copy the two `.pak` files into `...\steamapps\common\OCTOPATH TRAVELER 0\Octopath_Traveler0\Content\Paks\~mods\ZZZZZZ-Arabic Localization-1-0-0\`
- copy `OctopathArabicRTL.asi` into `Octopath_Traveler0\Binaries\Win64\` (needs an ASI loader already present; without one the translation, font and logo still work, only RTL alignment is off).

**Uninstall**: installer → uninstall button, or delete those files.

## Notes

- The Arabic occupies the game's English language slot — select «English» in the language menu.
- Some battle-system terms (e.g. "Shield Guard") are still under terminology review for future updates.
- A rare crash tied to the RTL alignment feature has been observed in very long sessions; report it in [Issues](https://github.com/faisalkindi/OctopathTraveler0-Arabic/issues) with what you were doing.
- Open-source tools that made this possible: repak, CUE4Parse, UAssetAPI, safetyhook, zydis.
- Contributors: see [`PIPELINE.md`](PIPELINE.md).

<p align="center">تعريب وإعداد: <b>Kindiboy</b></p>
