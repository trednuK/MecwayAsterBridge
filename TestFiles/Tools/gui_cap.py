# Rendert het hoofdvenster offscreen (DrawToBitmap) per pagina van de
# navigatie naar PNG, zonder Mecway (test van bridge_gui.py).
# gebruik: powershell -File run_ipy.ps1 -Script gui_cap.py -ScriptArgs <repo>,<uitmap>,en
# (IronPython): gui_cap.py <repo> <uitmap> [nl|en] [status]
# omgeving: CAP_SMALL=1 (venster op MinimumSize), CAP_BIG=1, CAP_SCROLL=1,
#           CAP_KEYS=1 (toetsenbordtest), CAP_ACTIVE=1 (actieve analyse wisselen)
#           CAP_DOCS=1 (neutral work folder for screenshots in docs/img),
#           CAP_SET="key=value;..." (settings in memory for a screenshot),
#           CAP_SCROLL_PAGE=<n> (with CAP_SCROLL: the page that is scrolled
#           to the bottom, default 0)
import sys, os
repo, out = sys.argv[1], sys.argv[2]
lang = sys.argv[3] if len(sys.argv) > 3 else "nl"
status = sys.argv[4] if len(sys.argv) > 4 else u""
sys.path.insert(0, repo + "/Scripts")
import clr
from System import Environment


def _env(name):
    return Environment.GetEnvironmentVariable(name) or ""

clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")
from System.Windows.Forms import (Application, MethodInvoker, ListBox,
                                  ComboBox, SendKeys, TextBox)
from System.Drawing import Bitmap, Rectangle, Point, Size
from System.Drawing.Imaging import ImageFormat
from System.Threading import Thread, ThreadStart
Application.EnableVisualStyles()
import bridge_utils
bridge_utils.CONFIG_BRIDGE["language"] = lang
if _env("CAP_DOCS"):
    # screenshots for docs/img: neutral paths and defaults, no user name
    # or own folders in the image (the repo is public)
    bridge_utils.CONFIG_BRIDGE["work_dir"] = r"C:\FEA\WorkDir"
    bridge_utils.CONFIG_BRIDGE["ncpus"] = 1
# CAP_SET="key=value;key=value": settings in memory only, for a screenshot
# that shows a non-default choice (top level of CONFIG_BRIDGE, else every
# analysis that has the key)
for _pair in [p for p in _env("CAP_SET").split(";") if "=" in p]:
    _key, _val = [v.strip() for v in _pair.split("=", 1)]
    for _conv in (int, float):
        try:
            _val = _conv(_val)
            break
        except ValueError:
            pass
    if _key in bridge_utils.CONFIG_BRIDGE:
        bridge_utils.CONFIG_BRIDGE[_key] = _val
    for _ana in bridge_utils.CONFIG_BRIDGE.get("analyses", {}).values():
        if _key in _ana:
            _ana[_key] = _val
import bridge_gui
if not os.path.isdir(out):
    os.makedirs(out)
tag = lang + ("_small" if _env("CAP_SMALL") else "")


def find_name(ctrl, name):
    for c in ctrl.Controls:
        if c.Name == name:
            return c
        r = find_name(c, name)
        if r is not None:
            return r
    return None


def find_all(ctrl, typ, acc):
    for c in ctrl.Controls:
        if isinstance(c, typ):
            acc.append(c)
        find_all(c, typ, acc)
    return acc


def worker():
    try:
        f = None
        while f is None:
            if Application.OpenForms.Count > 0:
                f = Application.OpenForms[0]
            else:
                Thread.Sleep(2)

        def hide():
            f.Opacity = 0.0
            f.Location = Point(-5000, -5000)
            if _env("CAP_BIG"):
                f.Size = Size(1300, 860)
            if _env("CAP_SMALL"):
                f.Size = f.MinimumSize
        f.Invoke(MethodInvoker(hide))
        Thread.Sleep(800)

        def snap(name):
            def fn():
                bmp = Bitmap(f.Width, f.Height)
                f.DrawToBitmap(bmp, Rectangle(0, 0, f.Width, f.Height))
                bmp.Save(os.path.join(out, name + ".png"), ImageFormat.Png)
            f.Invoke(MethodInvoker(fn))

        nav = find_name(f, "nav")
        host = find_name(f, "pages")
        info = []
        f.Invoke(MethodInvoker(lambda: info.append(
            (nav.Items.Count, f.ActiveControl is nav, nav.SelectedIndex,
             f.ClientSize.Width, f.ClientSize.Height))))
        print("pagina's, focus op nav, gekozen, client:", info[0])
        n = info[0][0]
        for i in range(n):
            def sel(i=i):
                nav.SelectedIndex = i
            f.Invoke(MethodInvoker(sel))
            Thread.Sleep(600 if i < n - 1 else 2500)
            vis = []
            f.Invoke(MethodInvoker(lambda: vis.append(
                [k for k in range(host.Controls.Count)
                 if host.Controls[k].Visible])))
            if len(vis[0]) != 1:
                print("FOUT: zichtbare pagina's", vis[0])
            snap("%02d_%s" % (i, tag))
            if _env("CAP_SCROLL") and i == int(_env("CAP_SCROLL_PAGE") or 0):
                def scr():
                    for c in host.Controls:
                        if c.Visible:
                            c.AutoScrollPosition = Point(0, 2000)
                f.Invoke(MethodInvoker(scr))
                Thread.Sleep(400)
                snap("%02d_%s_scroll" % (i, tag))
        if _env("CAP_KEYS"):
            res = []

            def keys():
                f.Activate()
                nav.SelectedIndex = 0
                nav.Focus()
                SendKeys.SendWait("{DOWN}")
                res.append(("DOWN", nav.SelectedIndex))
                SendKeys.SendWait("{END}")
                res.append(("END", nav.SelectedIndex))
                SendKeys.SendWait("^{TAB}")
                res.append(("Ctrl+Tab", nav.SelectedIndex))
                SendKeys.SendWait("^+{TAB}")
                res.append(("Ctrl+Shift+Tab", nav.SelectedIndex))
                SendKeys.SendWait("^{PGUP}")
                res.append(("Ctrl+PgUp", nav.SelectedIndex))
                # vanuit een tekstveld op de pagina
                boxes = [c for c in find_all(host, TextBox, [])
                         if c.Visible]
                if boxes:
                    boxes[0].Focus()
                    SendKeys.SendWait("^{PGDN}")
                    res.append(("Ctrl+PgDn vanuit veld", nav.SelectedIndex))
            f.Invoke(MethodInvoker(keys))
            print("toetsen:", res)

            def explain():
                from System.Windows.Forms import Button
                nav.SelectedIndex = 0
                for b in find_all(f, Button, []):
                    if b.Text in ("Uitleg...", "Explanation..."):
                        b.PerformClick()
                res.append(("Uitleg-knop", nav.SelectedIndex,
                            nav.Items.Count - 1))
            f.Invoke(MethodInvoker(explain))
            print("uitleg:", res[-1])
        if _env("CAP_ACTIVE"):
            def act():
                for c in find_all(f, ComboBox, []):
                    items = ["%s" % x for x in c.Items]
                    if "auto" in items and "lin_static_3d" in items:
                        c.SelectedItem = "nonlin_static_3d"
                nav.SelectedIndex = 3
            f.Invoke(MethodInvoker(act))
            Thread.Sleep(500)
            snap("active_%s" % tag)
        if _env("CAP_START"):
            from System.Windows.Forms import Button
            def click():
                for x in find_all(f, Button, []):
                    if x.Text in ("Starten", "Start"):
                        x.PerformClick()
                        return
            f.Invoke(MethodInvoker(click))
        else:
            f.Invoke(MethodInvoker(lambda: f.Close()))
    except Exception as e:
        print("worker-fout: %r" % e)
        try:
            f.Invoke(MethodInvoker(lambda: f.Close()))
        except Exception:
            pass


t = Thread(ThreadStart(worker))
t.IsBackground = True
t.Start()
cur = bridge_gui._collect_current()
res = bridge_gui._show_winforms_dialog(cur, status)
print("klaar", res["action"], sorted((res.get("values") or {}).get("general", {}).keys()))
