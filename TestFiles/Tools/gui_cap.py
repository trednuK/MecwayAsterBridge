# Rendert het hoofdvenster offscreen (DrawToBitmap) per pagina van de
# navigatie naar PNG, zonder Mecway (test van bridge_gui.py).
# gebruik: powershell -File run_ipy.ps1 -Script gui_cap.py -ScriptArgs <repo>,<uitmap>,en
# (IronPython): gui_cap.py <repo> <uitmap> [nl|en] [status]
# omgeving: CAP_SMALL=1 (venster op MinimumSize), CAP_BIG=1, CAP_SCROLL=1,
#           CAP_KEYS=1 (test of the navigation scrollbar with keys, wheel
#           and drag, the Section menu and the status box; window messages
#           only, safe on a hidden desktop; with CAP_SMALL=1; exit code 1 on
#           a failure), CAP_SENDKEYS=1 (Ctrl+Tab etc. with real keyboard
#           input; only on the input desktop), CAP_SHOWN=1 (the section
#           shape counts as shown), CAP_SECTION=show|hide|results (choose
#           that item of the Section menu instead of closing),
#           CAP_MENU=1 (image with the Section menu open, menu_<tag>.png),
#           CAP_ACTIVE=1 (actieve analyse wisselen),
#           CAP_PAGES=0,2 (only these pages of the navigation)
#           CAP_DOCS=1 (neutral work folder for screenshots in docs/img),
#           CAP_SET="key=value;..." (settings in memory for a screenshot),
#           CAP_RESULTS=1 (only the Results window, example runs)
#           CAP_SCROLL_PAGE=<n> (with CAP_SCROLL: the page that is scrolled
#           to the bottom, default 0)
#           CAP_SCALE=<f> (e.g. 1.25: all fonts of the windows f times
#           larger, like Windows display scale 125 % in Mecway, where the
#           fonts grow but fixed pixel sizes do not)
#           CAP_STATUS=1 (only the status window of a run, dummy job)
#           CAP_MODEL=<name> (model name in the header of the main
#           window)
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
                                  ComboBox, SendKeys, TextBox, Button,
                                  TextRenderer)
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
if _env("CAP_SCALE"):
    _scale = float(_env("CAP_SCALE"))
    _look_init = bridge_gui._Look.__init__

    def _scaled_init(self):
        from System.Drawing import Font
        _look_init(self)
        for _name, _font in list(vars(self).items()):
            if isinstance(_font, Font):
                setattr(self, _name, Font(_font.FontFamily,
                                          _font.Size * _scale, _font.Style))
    bridge_gui._Look.__init__ = _scaled_init
if not os.path.isdir(out):
    os.makedirs(out)
if _env("CAP_SHOWN"):
    bridge_gui._MODEL_INFO["section_shown"] = True
tag = lang + ("_small" if _env("CAP_SMALL") else "") + (
    "_x" + _env("CAP_SCALE") if _env("CAP_SCALE") else "")


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


FAILS = []


def fail(text):
    print("FOUT: " + text)
    FAILS.append(text)


def check(cond, text):
    print(("OK   " if cond else "FOUT ") + text)
    if not cond:
        FAILS.append(text)


# Window messages for the keyboard and mouse tests: sent straight to the
# window of a control (SendMessage, on its own thread through Invoke), so
# that nothing goes through the input of the screen (SendKeys/SendInput
# would type into the active window of the user's desktop).
import ctypes
_user32 = ctypes.windll.user32
WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101
WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP = 0x0200, 0x0201, 0x0202
WM_MOUSEWHEEL = 0x020A
VK = {"PRIOR": 0x21, "NEXT": 0x22, "END": 0x23, "HOME": 0x24,
      "UP": 0x26, "DOWN": 0x28}


def _send(ctrl, msg, wparam, lparam):
    _user32.SendMessageW(ctypes.c_void_p(ctrl.Handle.ToInt64()),
                         ctypes.c_uint(msg),
                         ctypes.c_size_t(wparam & 0xFFFFFFFF),
                         ctypes.c_ssize_t(lparam))


def _xy(x, y):
    return ((y & 0xFFFF) << 16) | (x & 0xFFFF)


def key(ctrl, name):
    _send(ctrl, WM_KEYDOWN, VK[name], 1)
    _send(ctrl, WM_KEYUP, VK[name], 1 | (3 << 30))


def wheel(ctrl, delta):
    p = ctrl.PointToScreen(Point(ctrl.Width // 2, 10))
    _send(ctrl, WM_MOUSEWHEEL, (delta & 0xFFFF) << 16, _xy(p.X, p.Y))


def keys_test(f, nav, host):
    """CAP_KEYS=1 (with CAP_SMALL=1, so that the navigation does not fit):
    the self-drawn scrollbar of the navigation with keys, wheel, drag and
    a click on the track; the Section menu; the status box shows its text
    without scrolling."""
    import bridge_gui as g
    bar = find_name(f, "nav_bar")
    clip = find_name(f, "nav_clip")

    def run():
        view = clip.ClientSize.Height
        total = nav.Height - 2
        track = bar.ClientSize.Height
        row_h = nav.GetItemRectangle(1).Height   # page without heading
        n = nav.Items.Count
        check(bar.Visible, "navigation scrollbar shown (%d > %d px)"
              % (total, view))
        if not bar.Visible:
            return

        def off():
            return -nav.Top

        def shown(k):
            r = nav.GetItemRectangle(k)
            return r.Top >= off() and r.Bottom <= off() + view

        nav.SelectedIndex = 0
        key(nav, "END")
        check(nav.SelectedIndex == n - 1 and shown(n - 1) and off() > 0,
              "End: last page chosen and in view (off %d)" % off())
        key(nav, "HOME")
        check(nav.SelectedIndex == 0 and off() == 0, "Home: back to top")
        key(nav, "NEXT")
        want = g._nav_page_index(0, n, max(1, view // row_h), True)
        check(nav.SelectedIndex == want and shown(want),
              "PageDown: page %d (want %d) in view" % (nav.SelectedIndex,
                                                       want))
        key(nav, "PRIOR")
        check(nav.SelectedIndex == 0 and off() == 0, "PageUp: back to top")
        for _i in range(n - 1):
            key(nav, "DOWN")
        check(nav.SelectedIndex == n - 1 and shown(n - 1),
              "Down arrows: the chosen page stays in view")
        key(nav, "HOME")
        room = total - view
        for ctrl, name in ((nav, "list"), (clip, "panel of the list"),
                           (bar, "scrollbar")):
            wheel(ctrl, -120)
            check(off() == min(room, 2 * row_h),
                  "wheel down over the %s: %d px" % (name, off()))
            wheel(ctrl, 120)
            check(off() == 0, "wheel up over the %s: back to 0" % name)
        top, h = g._nav_thumb(0, total, view, track)
        x = bar.ClientSize.Width // 2
        y0 = top + h // 2
        _send(bar, WM_LBUTTONDOWN, 1, _xy(x, y0))
        _send(bar, WM_MOUSEMOVE, 1, _xy(x, y0 + 30))
        want = g._nav_drag_off(0, 30, total, view, track, h)
        check(off() == want and off() > 0,
              "drag the thumb 30 px: off %d (want %d)" % (off(), want))
        _send(bar, WM_MOUSEMOVE, 1, _xy(x, y0 + 29))
        want = g._nav_drag_off(0, 29, total, view, track, h)
        check(off() == want, "drag 1 px back: off %d (want %d)"
              % (off(), want))
        _send(bar, WM_LBUTTONUP, 0, _xy(x, y0 + 29))
        before = off()
        _send(bar, WM_MOUSEMOVE, 0, _xy(x, y0 + 80))
        check(off() == before, "after release the thumb no longer follows")
        top, h = g._nav_thumb(before, total, view, track)
        if top > 0:
            _send(bar, WM_LBUTTONDOWN, 1, _xy(x, 0))
            _send(bar, WM_LBUTTONUP, 0, _xy(x, 0))
            check(off() == max(0, before - view),
                  "click on the track above the thumb: one view up (%d)"
                  % off())
        key(nav, "HOME")
        _send(bar, WM_LBUTTONDOWN, 1, _xy(x, track - 2))
        _send(bar, WM_LBUTTONUP, 0, _xy(x, track - 2))
        check(off() == min(room, view),
              "click on the track below the thumb: one view down (%d)"
              % off())
        key(nav, "HOME")

    def menu():
        btn = find_name(f, "section_btn")
        check(btn is not None and btn.ContextMenuStrip is not None,
              "Section button with its menu")
        if btn is None:
            return
        items = btn.ContextMenuStrip.Items
        shown = bool(_env("CAP_SHOWN"))
        states = dict((items[i].Name, items[i].Enabled)
                      for i in range(items.Count) if items[i].Name)
        check(states == {"section_show": not shown, "section_hide": shown,
                         "section_results": True},
              "menu items and enabled states %r" % states)
        check(all(items[i].ToolTipText for i in range(items.Count)
                  if items[i].Name), "every menu item has a tooltip")
        names = [b.Text for b in find_all(f, Button, [])]
        check(not [t for t in names if t in ("Uitleg...",
                                             "Explanation...")],
              "no Explanation button")

    def status():
        box = find_name(f, "status_box")
        lines = box.GetLineFromCharIndex(max(0, len(box.Text) - 1)) + 1
        line_h = TextRenderer.MeasureText(u"Ag", box.Font).Height
        check(lines * line_h <= box.ClientSize.Height,
              "status box shows its %d line(s) in %d px" %
              (lines, box.ClientSize.Height))

    for fn in (run, menu, status):
        f.Invoke(MethodInvoker(fn))


def _on_input_desktop():
    """True when this thread's desktop takes the keyboard input (then
    SendKeys types into the bridge window, not into another window)."""
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.GetThreadDesktop.restype = ctypes.c_void_p
    user32.OpenInputDesktop.restype = ctypes.c_void_p

    def name(h):
        buf = ctypes.create_unicode_buffer(256)
        need = ctypes.c_uint(0)
        user32.GetUserObjectInformationW(ctypes.c_void_p(h), 2, buf, 512,
                                         ctypes.byref(need))
        return buf.value
    mine = user32.GetThreadDesktop(kernel32.GetCurrentThreadId())
    inp = user32.OpenInputDesktop(0, False, 0x0001)
    if not inp or not mine:
        return False
    try:
        return name(mine) == name(inp)
    finally:
        user32.CloseDesktop(ctypes.c_void_p(inp))


def sendkeys_test(f, nav, host):
    """CAP_SENDKEYS=1: Ctrl+Tab and Ctrl+PageUp/PageDown through SendKeys
    (real keyboard input, with modifier keys). Only when the window is on
    the input desktop: on a hidden desktop the keys would go to the
    user's active window, so then it is skipped."""
    ok = []
    f.Invoke(MethodInvoker(lambda: ok.append(_on_input_desktop())))
    if not ok[0]:
        print("SendKeys test skipped: not on the input desktop")
        return
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
        boxes = [c for c in find_all(host, TextBox, []) if c.Visible]
        if boxes:
            boxes[0].Focus()
            SendKeys.SendWait("^{PGDN}")
            res.append(("Ctrl+PgDn vanuit veld", nav.SelectedIndex))
    f.Invoke(MethodInvoker(keys))
    print("toetsen:", res)


def menu_capture(f):
    """CAP_MENU=1: the window with the Section menu open, to
    menu_<tag>.png. Drawn in the same call as it opens (a drop-down closes
    when its window is not the active one, as on a hidden desktop)."""
    from System.Drawing import Graphics
    btn = find_name(f, "section_btn")
    btn.PerformClick()
    m = btn.ContextMenuStrip
    Application.DoEvents()
    bmp = Bitmap(f.Width, f.Height)
    f.DrawToBitmap(bmp, Rectangle(0, 0, f.Width, f.Height))
    mb = Bitmap(m.Width, m.Height)
    m.DrawToBitmap(mb, Rectangle(0, 0, m.Width, m.Height))
    # from client to window coordinates (border and title bar)
    org = f.PointToScreen(Point(0, 0))
    dx = org.X - f.Location.X
    dy = org.Y - f.Location.Y
    # The window is far off screen, where Windows moves a drop-down back
    # onto the screen: draw the menu where it opens, above the button
    # (bridge_gui: ToolStripDropDownDirection.AboveRight).
    b = f.PointToClient(btn.PointToScreen(Point(0, 0)))
    x, y = b.X + dx, b.Y + dy - m.Height
    gr = Graphics.FromImage(bmp)
    gr.DrawImage(mb, x, y)
    gr.Dispose()
    bmp.Save(os.path.join(out, "menu_%s.png" % tag), ImageFormat.Png)
    print("menu at %d,%d size %dx%d; button at %d,%d size %dx%d" % (
        x, y, m.Width, m.Height, b.X + dx, b.Y + dy, btn.Width, btn.Height))
    m.Close()


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
        # CAP_PAGES=0,2,16: capture only these pages (default: all)
        only = [int(x) for x in _env("CAP_PAGES").split(",") if x.strip()]
        for i in range(n):
            if only and i not in only:
                continue
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
            keys_test(f, nav, host)
        if _env("CAP_SENDKEYS"):
            sendkeys_test(f, nav, host)
        if _env("CAP_MENU"):
            f.Invoke(MethodInvoker(lambda: menu_capture(f)))
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
        elif _env("CAP_SECTION"):
            # CAP_SECTION=show|hide|results: choose that item of the
            # Section menu; the window closes with its action (printed
            # as "klaar <action>"; the dialog itself saves nothing)
            def choose():
                btn = find_name(f, "section_btn")
                items = btn.ContextMenuStrip.Items.Find(
                    "section_" + _env("CAP_SECTION"), False)
                if not items or not items[0].Enabled:
                    fail("menu item %s not available" % _env("CAP_SECTION"))
                    f.Close()
                    return
                items[0].PerformClick()
            f.Invoke(MethodInvoker(choose))
        else:
            f.Invoke(MethodInvoker(lambda: f.Close()))
    except Exception as e:
        fail("worker-fout: %r" % e)
        try:
            f.Invoke(MethodInvoker(lambda: f.Close()))
        except Exception:
            pass


def results_worker():
    """CAP_RESULTS=1: the Results window (results_dialog) with three example
    runs, hidden and offscreen like the main window, to results_<lang>.png."""
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
        f.Invoke(MethodInvoker(hide))
        Thread.Sleep(800)

        def fn():
            bmp = Bitmap(f.Width, f.Height)
            f.DrawToBitmap(bmp, Rectangle(0, 0, f.Width, f.Height))
            bmp.Save(os.path.join(out, "results_%s.png" % tag),
                     ImageFormat.Png)
            f.Close()
        f.Invoke(MethodInvoker(fn))
    except Exception as e:
        print("worker-fout: %r" % e)


class _DemoJob(object):
    """CAP_STATUS=1: stands in for bridge_run_aster.AsterJob."""
    done = False

    def status(self):
        # The texts of AsterJob.status for a nonlinear step past its time
        # limit, so that every line of the window is filled.
        tr = bridge_utils.tr
        return {"headline": tr(u"Code-Aster rekent...",
                               u"Code-Aster is running..."),
                "time": tr(u"Verstreken tijd: 32:41 (tijdslimiet 30:00)",
                           u"Elapsed time: 32:41 (time limit 30:00)"),
                "detail": tr(u"STAT_NON_LINE | bereikt t = 0.275 s | poging "
                             u"13: t = 0.3 s, niveau 0, iteratie 4",
                             u"STAT_NON_LINE | reached t = 0.275 s | attempt "
                             u"13: t = 0.3 s, level 0, iteration 4"),
                "messages": tr(u"Meldingen tot nu toe: 0 fout(en), 2 "
                               u"alarm(en).",
                               u"Messages so far: 0 error(s), 2 alarm(s)."),
                "warning": tr(u"De run duurt langer dan de tijdslimiet. "
                              u"Code-Aster stopt normaal zelf bij de limiet; "
                              u"reageert het Code-Aster-venster niet meer, "
                              u"gebruik dan Stoppen.",
                              u"The run takes longer than the time limit. "
                              u"Code-Aster normally stops by itself at the "
                              u"limit; if the Code-Aster window no longer "
                              u"responds, use Stop."),
                "percent": 30}

    def poll(self):
        return self.done

    def finished(self):
        return self.done

    def stop(self):
        self.done = True


def status_worker(job):
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
        f.Invoke(MethodInvoker(hide))
        Thread.Sleep(1200)

        def fn():
            bmp = Bitmap(f.Width, f.Height)
            f.DrawToBitmap(bmp, Rectangle(0, 0, f.Width, f.Height))
            bmp.Save(os.path.join(out, "status_%s.png" % tag),
                     ImageFormat.Png)
            job.done = True
        f.Invoke(MethodInvoker(fn))
    except Exception as e:
        print("worker-fout: %r" % e)
        job.done = True


if _env("CAP_STATUS"):
    bridge_gui._mecway_window = lambda: None
    bridge_utils.run_name = lambda suffix: u"Bracket_20261028_101500" + suffix
    job = _DemoJob()
    t = Thread(ThreadStart(lambda: status_worker(job)))
    t.IsBackground = True
    t.Start()
    print("klaar", bridge_gui.run_status_dialog(job))
    sys.exit(0)

if _env("CAP_RESULTS"):
    wd = bridge_utils.CONFIG_BRIDGE["work_dir"] or r"C:\FEA\WorkDir"
    demo = []
    for rid, size in (("20261028_101500", 4.2e6), ("20261027_163000", 3.9e6),
                      ("20261027_091000", 0.4e6)):
        stem = os.path.join(wd, "Bracket_" + rid)
        demo.append({"path": stem + "_results.xml", "size": size,
                     "run_id": rid, "comm": stem + ".comm", "mail": None,
                     "model": r"C:\FEA\Bracket.liml"})
    t = Thread(ThreadStart(results_worker))
    t.IsBackground = True
    t.Start()
    print("klaar", bridge_gui.results_dialog(demo, wd))
    sys.exit(0)

t = Thread(ThreadStart(worker))
t.IsBackground = True
t.Start()
cur = bridge_gui._collect_current()
res = bridge_gui._show_winforms_dialog(cur, status,
                                       _env("CAP_MODEL") or None)
print("klaar", res["action"], sorted((res.get("values") or {}).get("general", {}).keys()))
if FAILS:
    print("%d failure(s)" % len(FAILS))
    sys.exit(1)
