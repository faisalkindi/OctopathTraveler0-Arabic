using System;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Text;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Win32;

namespace OctopathArabic
{
    static class Program
    {
        const string AppId = "3014320"; // verified: H:\Steam\steamapps\appmanifest_3014320.acf
        const string ModFolderName = "ZZZZZZ-Arabic Localization-1-0-0";
        static readonly string[] PakFiles = { "OctopathArabic_StatFix_P.pak", "OctopathArabic_Logo_P.pak" };
        const string AsiFile = "OctopathArabicRTL.asi";
        // ASI loaders this game/community is known to ship under (Ultimate ASI Loader proxy names).
        // We don't bundle one ourselves -- Octopath0Fix (a popular existing community fix) already
        // ships one, and redistributing someone else's loader isn't ours to do.
        static readonly string[] KnownAsiLoaderNames = { "dsound.dll", "dinput8.dll", "xinput1_4.dll", "winmm.dll", "version.dll" };

        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(true);
            Application.Run(new MainForm());
        }

        // ---- Steam game-folder detection -------------------------------------

        public static string DetectGamePath()
        {
            try
            {
                string steam = GetSteamPath();
                if (steam == null) return null;
                string vdf = Path.Combine(steam, "steamapps", "libraryfolders.vdf");
                var libs = new System.Collections.Generic.List<string>();
                libs.Add(steam);
                if (File.Exists(vdf))
                {
                    foreach (Match m in Regex.Matches(File.ReadAllText(vdf), "\"path\"\\s*\"([^\"]+)\""))
                        libs.Add(m.Groups[1].Value.Replace("\\\\", "\\"));
                }
                foreach (string lib in libs)
                {
                    string acf = Path.Combine(lib, "steamapps", "appmanifest_" + AppId + ".acf");
                    if (!File.Exists(acf)) continue;
                    var im = Regex.Match(File.ReadAllText(acf), "\"installdir\"\\s*\"([^\"]+)\"");
                    if (!im.Success) continue;
                    string game = Path.Combine(lib, "steamapps", "common", im.Groups[1].Value);
                    if (IsValidGameFolder(game)) return game;
                }
            }
            catch { }
            return null;
        }

        static string GetSteamPath()
        {
            try
            {
                object p = Registry.GetValue(@"HKEY_CURRENT_USER\Software\Valve\Steam", "SteamPath", null);
                if (p is string s1 && Directory.Exists(s1)) return s1.Replace('/', '\\');
            }
            catch { }
            try
            {
                object p = Registry.GetValue(@"HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath", null);
                if (p is string s2 && Directory.Exists(s2)) return s2;
            }
            catch { }
            return null;
        }

        // ---- path helpers -----------------------------------------------------
        // Verified layout: <install>\Octopath_Traveler0\Octopath_Traveler0\{Content\Paks, Binaries\Win64}
        // (the folder name repeats, same pattern as Elliot's own install tree).

        public static string InnerRoot(string gameRoot) => Path.Combine(gameRoot, "Octopath_Traveler0");
        public static string PaksDir(string gameRoot) => Path.Combine(InnerRoot(gameRoot), "Content", "Paks");
        public static string ModsDir(string gameRoot) => Path.Combine(PaksDir(gameRoot), "~mods", ModFolderName);
        public static string BinDir(string gameRoot) => Path.Combine(InnerRoot(gameRoot), "Binaries", "Win64");
        public static string BasePak(string gameRoot) => Path.Combine(PaksDir(gameRoot), "pakchunk0-Windows.pak");
        public static string ExePath(string gameRoot) => Path.Combine(BinDir(gameRoot), "Octopath_Traveler0-Win64-Shipping.exe");

        public static bool IsValidGameFolder(string folder)
        {
            if (string.IsNullOrEmpty(folder)) return false;
            return File.Exists(BasePak(folder));
        }

        public static bool IsInstalled(string gameRoot) =>
            File.Exists(Path.Combine(ModsDir(gameRoot), PakFiles[0]));

        public static bool HasAsiLoader(string gameRoot)
        {
            string bin = BinDir(gameRoot);
            return KnownAsiLoaderNames.Any(n => File.Exists(Path.Combine(bin, n)));
        }

        // ---- install / uninstall ---------------------------------------------
        // Much simpler than Elliot: these are standalone loose-pak overrides, not a base-pak
        // rebuild -- nothing in the player's own game files is ever modified or needs backing up.

        public static void Install(string gameRoot, Action<string> progress)
        {
            string paks = PaksDir(gameRoot);
            string mods = ModsDir(gameRoot);
            string bin = BinDir(gameRoot);
            if (!IsValidGameFolder(gameRoot))
                throw new Exception("لم يُعثر على ملف اللعبة الأساسي:\npakchunk0-Windows.pak");

            EnsureGameClosed(gameRoot);

            string work = Path.Combine(Path.GetTempPath(), "OctopathArabicInstall_tmp");
            SafeDeleteDir(work);
            Directory.CreateDirectory(work);
            try
            {
                progress("جارٍ تحضير ملفات التعريب…");
                ExtractPayload(work);

                progress("جارٍ تثبيت النصوص والخطوط والشعار…");
                Directory.CreateDirectory(mods);
                foreach (string pf in PakFiles)
                    File.Copy(Path.Combine(work, "mods", ModFolderName, pf), Path.Combine(mods, pf), true);

                progress("جارٍ تثبيت محاذاة النص لليمين…");
                Directory.CreateDirectory(bin);
                File.Copy(Path.Combine(work, "asi", AsiFile), Path.Combine(bin, AsiFile), true);

                progress("تم التثبيت بنجاح ✔");
            }
            finally
            {
                SafeDeleteDir(work);
            }
        }

        public static void Uninstall(string gameRoot, Action<string> progress)
        {
            string mods = ModsDir(gameRoot);
            string bin = BinDir(gameRoot);

            EnsureGameClosed(gameRoot);

            progress("جارٍ إزالة ملفات التعريب…");
            if (Directory.Exists(mods))
            {
                foreach (string pf in PakFiles)
                {
                    string f = Path.Combine(mods, pf);
                    if (File.Exists(f)) File.Delete(f);
                }
                if (!Directory.EnumerateFileSystemEntries(mods).Any())
                    Directory.Delete(mods);
            }
            string asi = Path.Combine(bin, AsiFile);
            if (File.Exists(asi)) File.Delete(asi);

            progress("تمت الإزالة ✔");
        }

        // ---- internals --------------------------------------------------------

        static void ExtractPayload(string destDir)
        {
            var asm = Assembly.GetExecutingAssembly();
            using (Stream s = asm.GetManifestResourceStream("payload.zip"))
            {
                if (s == null) throw new Exception("ملفات التعريب المضمّنة غير موجودة داخل المثبّت.");
                using (var z = new ZipArchive(s, ZipArchiveMode.Read))
                    z.ExtractToDirectory(destDir, true);
            }
        }

        static void SafeDeleteDir(string dir)
        {
            try { if (Directory.Exists(dir)) Directory.Delete(dir, true); } catch { }
        }

        static void EnsureGameClosed(string gameRoot)
        {
            string exe = ExePath(gameRoot);
            if (!File.Exists(exe)) return;
            try
            {
                using (var fs = new FileStream(exe, FileMode.Open, FileAccess.Read, FileShare.Read))
                { }
            }
            catch (IOException)
            {
                throw new Exception("اللعبة قيد التشغيل. الرجاء إغلاق اللعبة تمامًا ثم إعادة المحاولة.");
            }
            catch (UnauthorizedAccessException)
            {
                throw new Exception("تعذّر الوصول إلى ملفات اللعبة. شغّل المثبّت كمسؤول (Run as administrator).");
            }
        }
    }

    // ===================== modern UI (same visual language as the Elliot installer) =====================

    static class Ui
    {
        public static readonly Color Bg = Color.FromArgb(30, 26, 23);
        public static readonly Color Card = Color.FromArgb(44, 38, 33);
        public static readonly Color Gold = Color.FromArgb(206, 167, 92);
        public static readonly Color GoldHover = Color.FromArgb(224, 187, 112);
        public static readonly Color Red = Color.FromArgb(168, 70, 58);
        public static readonly Color RedHover = Color.FromArgb(192, 86, 72);
        public static readonly Color Ink = Color.FromArgb(34, 28, 23);
        public static readonly Color Text = Color.FromArgb(236, 228, 214);
        public static readonly Color Muted = Color.FromArgb(150, 140, 128);

        static PrivateFontCollection _pfc;
        public static FontFamily Family;

        public static void LoadFont()
        {
            try
            {
                var asm = Assembly.GetExecutingAssembly();
                using (Stream s = asm.GetManifestResourceStream("ui_font.ttf"))
                {
                    byte[] data = new byte[s.Length];
                    s.Read(data, 0, data.Length);
                    IntPtr ptr = Marshal.AllocCoTaskMem(data.Length);
                    Marshal.Copy(data, 0, ptr, data.Length);
                    _pfc = new PrivateFontCollection();
                    _pfc.AddMemoryFont(ptr, data.Length);
                    Marshal.FreeCoTaskMem(ptr);
                    Family = _pfc.Families[0];
                }
            }
            catch { Family = new FontFamily("Tahoma"); }
        }

        public static Font F(float size, FontStyle style = FontStyle.Regular)
            => new Font(Family, size, style, GraphicsUnit.Point);

        public static Image LoadLogo()
        {
            try
            {
                using (Stream s = Assembly.GetExecutingAssembly().GetManifestResourceStream("ui_logo.png"))
                using (var img = Image.FromStream(s))
                    return new Bitmap(img);
            }
            catch { return null; }
        }

        public static GraphicsPath Round(Rectangle r, int radius)
        {
            int d = radius * 2;
            var p = new GraphicsPath();
            p.AddArc(r.X, r.Y, d, d, 180, 90);
            p.AddArc(r.Right - d, r.Y, d, d, 270, 90);
            p.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
            p.AddArc(r.X, r.Bottom - d, d, d, 90, 90);
            p.CloseFigure();
            return p;
        }
    }

    public class RoundButton : Button
    {
        public Color Base = Ui.Gold;
        public Color Hover = Ui.GoldHover;
        public Color Fg = Ui.Ink;
        public int Radius = 14;
        bool _hover;

        public RoundButton()
        {
            SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint
                     | ControlStyles.OptimizedDoubleBuffer | ControlStyles.SupportsTransparentBackColor, true);
            FlatStyle = FlatStyle.Flat;
            FlatAppearance.BorderSize = 0;
            BackColor = Color.Transparent;
            Cursor = Cursors.Hand;
            MouseEnter += (s, e) => { _hover = true; Invalidate(); };
            MouseLeave += (s, e) => { _hover = false; Invalidate(); };
        }

        protected override void OnPaintBackground(PaintEventArgs e) { }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.TextRenderingHint = System.Drawing.Text.TextRenderingHint.ClearTypeGridFit;
            var rect = new Rectangle(0, 0, Width - 1, Height - 1);
            Color fill = !Enabled ? Color.FromArgb(70, 64, 58) : (_hover ? Hover : Base);
            using (var path = Ui.Round(rect, Radius))
            using (var b = new SolidBrush(fill))
                g.FillPath(b, path);
            var sf = new StringFormat(StringFormatFlags.DirectionRightToLeft)
            { Alignment = StringAlignment.Center, LineAlignment = StringAlignment.Center };
            using (var tb = new SolidBrush(Enabled ? Fg : Color.FromArgb(140, 130, 120)))
                g.DrawString(Text, Font, tb, rect, sf);
        }
    }

    public class MainForm : Form
    {
        string gamePath;
        Label lblStatus, lblPath;
        RoundButton btnInstall, btnUninstall;
        LinkLabel btnBrowse;
        bool busy;

        public MainForm()
        {
            Ui.LoadFont();

            FormBorderStyle = FormBorderStyle.None;
            StartPosition = FormStartPosition.CenterScreen;
            ClientSize = new Size(520, 716);
            BackColor = Ui.Bg;
            RightToLeft = RightToLeft.Yes;
            RightToLeftLayout = true;
            Font = Ui.F(11f);
            Region = new Region(Ui.Round(new Rectangle(0, 0, Width, Height), 18));

            MouseDown += DragStart;

            var close = new Label
            {
                Text = "✕",
                Font = new Font("Segoe UI", 12f, FontStyle.Bold),
                ForeColor = Ui.Muted,
                AutoSize = false,
                Size = new Size(34, 30),
                Location = new Point(12, 12),
                TextAlign = ContentAlignment.MiddleCenter,
                Cursor = Cursors.Hand
            };
            close.Click += (s, e) => Close();
            close.MouseEnter += (s, e) => { close.ForeColor = Ui.Red; };
            close.MouseLeave += (s, e) => { close.ForeColor = Ui.Muted; };
            Controls.Add(close);

            var logo = new PictureBox
            {
                Image = Ui.LoadLogo(),
                SizeMode = PictureBoxSizeMode.Zoom,
                BackColor = Color.Transparent,
                Size = new Size(420, 216),
                Location = new Point((ClientSize.Width - 420) / 2, 46)
            };
            logo.MouseDown += DragStart;
            Controls.Add(logo);

            var subtitle = new Label
            {
                Text = "التعريب العربي الكامل",
                Font = Ui.F(15f, FontStyle.Bold),
                ForeColor = Ui.Gold,
                AutoSize = false,
                UseCompatibleTextRendering = true,
                TextAlign = ContentAlignment.MiddleCenter,
                Size = new Size(ClientSize.Width, 34),
                Location = new Point(0, 270)
            };
            subtitle.MouseDown += DragStart;
            Controls.Add(subtitle);

            var card = new RoundPanel
            {
                Size = new Size(440, 78),
                Location = new Point((ClientSize.Width - 440) / 2, 322),
                Fill = Ui.Card
            };
            lblPath = new Label
            {
                AutoSize = false,
                Dock = DockStyle.Fill,
                Padding = new Padding(14, 8, 14, 8),
                ForeColor = Ui.Text,
                Font = Ui.F(9.5f),
                UseCompatibleTextRendering = true,
                TextAlign = ContentAlignment.MiddleCenter,
                BackColor = Color.Transparent
            };
            card.Controls.Add(lblPath);
            Controls.Add(card);

            btnInstall = new RoundButton
            {
                Text = "تثبيت اللغة العربية",
                Font = Ui.F(14f, FontStyle.Bold),
                Size = new Size(440, 62),
                Location = new Point((ClientSize.Width - 440) / 2, 420),
                Base = Ui.Gold,
                Hover = Ui.GoldHover,
                Fg = Ui.Ink
            };
            btnInstall.Click += OnInstall;
            Controls.Add(btnInstall);

            btnUninstall = new RoundButton
            {
                Text = "إزالة اللغة العربية",
                Font = Ui.F(12.5f, FontStyle.Bold),
                Size = new Size(440, 50),
                Location = new Point((ClientSize.Width - 440) / 2, 494),
                Base = Ui.Red,
                Hover = Ui.RedHover,
                Fg = Ui.Text
            };
            btnUninstall.Click += OnUninstall;
            Controls.Add(btnUninstall);

            lblStatus = new Label
            {
                AutoSize = false,
                Font = Ui.F(10f),
                UseCompatibleTextRendering = true,
                TextAlign = ContentAlignment.MiddleCenter,
                ForeColor = Ui.Muted,
                Size = new Size(ClientSize.Width, 30),
                Location = new Point(0, 602)
            };
            lblStatus.MouseDown += DragStart;
            Controls.Add(lblStatus);

            btnBrowse = new LinkLabel
            {
                Text = "تحديد مجلد اللعبة يدويًا",
                AutoSize = false,
                Font = Ui.F(9f),
                LinkColor = Ui.Muted,
                ActiveLinkColor = Ui.Gold,
                LinkBehavior = LinkBehavior.HoverUnderline,
                TextAlign = ContentAlignment.MiddleCenter,
                Size = new Size(ClientSize.Width, 24),
                Location = new Point(0, 642),
                BackColor = Color.Transparent
            };
            btnBrowse.Click += OnBrowse;
            Controls.Add(btnBrowse);

            var footer = new Label
            {
                Text = "تعريب وإعداد:  Kindiboy",
                Font = Ui.F(9.5f, FontStyle.Bold),
                ForeColor = Color.FromArgb(170, 140, 92),
                AutoSize = false,
                UseCompatibleTextRendering = true,
                TextAlign = ContentAlignment.MiddleCenter,
                Size = new Size(ClientSize.Width, 22),
                Location = new Point(0, 682)
            };
            footer.MouseDown += DragStart;
            Controls.Add(footer);

            gamePath = Program.DetectGamePath();
            RefreshState();
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            using (var pen = new Pen(Color.FromArgb(60, Ui.Gold), 1))
            using (var path = Ui.Round(new Rectangle(0, 0, Width - 1, Height - 1), 18))
            {
                e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
                e.Graphics.DrawPath(pen, path);
            }
        }

        [DllImport("user32.dll")] static extern bool ReleaseCapture();
        [DllImport("user32.dll")] static extern IntPtr SendMessage(IntPtr h, int msg, int wp, int lp);
        void DragStart(object sender, MouseEventArgs e)
        {
            if (e.Button == MouseButtons.Left)
            {
                ReleaseCapture();
                SendMessage(Handle, 0xA1, 0x2, 0);
            }
        }

        void RefreshState()
        {
            if (Program.IsValidGameFolder(gamePath))
            {
                bool installed = Program.IsInstalled(gamePath);
                lblPath.ForeColor = Ui.Text;
                lblPath.Text = "تم العثور على اللعبة" + Environment.NewLine + Trim(gamePath);
                btnInstall.Enabled = !busy;
                btnUninstall.Enabled = !busy && installed;
                if (installed) SetStatus("✔ اللغة العربية مُثبّتة حاليًا", Ui.Gold);
                else if (!Program.HasAsiLoader(gamePath))
                    SetStatus("تنبيه: لم يُعثر على محمّل ASI (يلزم لمحاذاة النص لليمين)", Ui.Red);
                else SetStatus("اللغة العربية غير مُثبّتة", Ui.Muted);
            }
            else
            {
                lblPath.ForeColor = Ui.Red;
                lblPath.Text = "لم يتم العثور على اللعبة" + Environment.NewLine + "الرجاء تحديد المجلد يدويًا";
                btnInstall.Enabled = false;
                btnUninstall.Enabled = false;
                SetStatus("في انتظار تحديد مجلد اللعبة", Ui.Muted);
            }
            btnInstall.Invalidate();
            btnUninstall.Invalidate();
        }

        static string Trim(string p)
        {
            if (p != null && p.Length > 52) return "…" + p.Substring(p.Length - 50);
            return p;
        }

        void SetStatus(string text, Color color)
        {
            lblStatus.Text = text;
            lblStatus.ForeColor = color;
        }

        void Progress(string text)
        {
            if (InvokeRequired) BeginInvoke(new Action(() => SetStatus(text, Color.FromArgb(120, 170, 220))));
            else SetStatus(text, Color.FromArgb(120, 170, 220));
        }

        void SetBusy(bool b)
        {
            busy = b;
            Cursor = b ? Cursors.WaitCursor : Cursors.Default;
            RefreshState();
        }

        void OnBrowse(object sender, EventArgs e)
        {
            if (busy) return;
            using (var dlg = new FolderBrowserDialog())
            {
                dlg.Description = "اختر مجلد اللعبة (المجلد الذي يحتوي على Octopath_Traveler0)";
                dlg.UseDescriptionForTitle = true;
                if (dlg.ShowDialog(this) == DialogResult.OK)
                {
                    string chosen = dlg.SelectedPath;
                    if (!Program.IsValidGameFolder(chosen))
                    {
                        string sub = Path.Combine(chosen, "Octopath_Traveler0");
                        if (Program.IsValidGameFolder(sub)) chosen = sub;
                    }
                    if (Program.IsValidGameFolder(chosen)) gamePath = chosen;
                    else MessageBox.Show(this, "هذا المجلد لا يحتوي على ملفات اللعبة (Octopath_Traveler0\\Content\\Paks).",
                        "مجلد غير صالح", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    RefreshState();
                }
            }
        }

        void OnInstall(object sender, EventArgs e)
        {
            if (busy) return;
            string warn = Program.HasAsiLoader(gamePath) ? "" :
                "\n\nتنبيه: لم يُعثر على محمّل ASI في مجلد اللعبة. محاذاة النص لليمين تحتاج إليه " +
                "(مثل الموجود مع تعديل Octopath0Fix الشائع) — بدونه سيعمل النص والخطوط والشعار " +
                "لكن محاذاة اليمين لن تعمل.";
            if (MessageBox.Show(this,
                    "سيتم نسخ ملفات تعريب مستقلة إلى مجلد اللعبة (لا يتم تعديل أي ملف أصلي)." +
                    warn + "\n\nالمتابعة؟",
                    "تثبيت", MessageBoxButtons.OKCancel, MessageBoxIcon.Question) != DialogResult.OK)
                return;

            SetBusy(true);
            string root = gamePath;
            var t = new Thread(() =>
            {
                try
                {
                    Program.Install(root, Progress);
                    BeginInvoke(new Action(() =>
                    {
                        SetBusy(false);
                        MessageBox.Show(this,
                            "تم تثبيت اللغة العربية بنجاح!\n\nشغّل اللعبة، ثم اذهب إلى:\nالإعدادات ← اللغة ← اختر «English»\n(العربية تظهر مكان النص الإنجليزي).",
                            "تم التثبيت", MessageBoxButtons.OK, MessageBoxIcon.Information);
                    }));
                }
                catch (Exception ex)
                {
                    BeginInvoke(new Action(() =>
                    {
                        SetBusy(false);
                        MessageBox.Show(this, ex.Message, "خطأ في التثبيت", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    }));
                }
            });
            t.IsBackground = true;
            t.Start();
        }

        void OnUninstall(object sender, EventArgs e)
        {
            if (busy) return;
            SetBusy(true);
            string root = gamePath;
            var t = new Thread(() =>
            {
                try
                {
                    Program.Uninstall(root, Progress);
                    BeginInvoke(new Action(() =>
                    {
                        SetBusy(false);
                        MessageBox.Show(this, "تمت إزالة اللغة العربية بنجاح.",
                            "تمت الإزالة", MessageBoxButtons.OK, MessageBoxIcon.Information);
                    }));
                }
                catch (Exception ex)
                {
                    BeginInvoke(new Action(() =>
                    {
                        SetBusy(false);
                        MessageBox.Show(this, ex.Message, "خطأ في الإزالة", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    }));
                }
            });
            t.IsBackground = true;
            t.Start();
        }
    }

    public class RoundPanel : Panel
    {
        public Color Fill = Ui.Card;
        public int Radius = 12;
        public RoundPanel()
        {
            SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint
                     | ControlStyles.OptimizedDoubleBuffer | ControlStyles.SupportsTransparentBackColor, true);
            BackColor = Color.Transparent;
        }
        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            var r = new Rectangle(0, 0, Width - 1, Height - 1);
            using (var path = Ui.Round(r, Radius))
            using (var b = new SolidBrush(Fill))
                g.FillPath(b, path);
        }
    }
}
