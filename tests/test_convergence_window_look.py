# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of the look of the convergence window
# (aster_convergence_monitor, Python 3 with tkinter): the colours come from
# bridge_style as in the Windows Forms windows (bridge_gui), the flat
# buttons react to the mouse only when enabled, the buttons of the files of
# a run follow those files, and pixel distances follow the display scale.
# The window is created hidden (withdraw before anything is drawn): nothing
# appears on the screen and nothing takes the focus. Without tkinter (or
# without a display) the tkinter part is skipped.
#
#   python tests/test_convergence_window_look.py

from __future__ import print_function

import argparse
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_style  # noqa: E402
import bridge_gui  # noqa: E402
import aster_convergence_monitor as m  # noqa: E402

_FAILED = []


def check(cond, text):
    print(("OK   " if cond else "FAIL ") + text)
    if not cond:
        _FAILED.append(text)


def col(key):
    return bridge_style.hex_colour(key)


def test_colours():
    for key, rgb in bridge_style.COLOURS.items():
        check(bridge_gui._STYLE[key] == rgb,
              "bridge_gui uses the shared colour " + key)
    check(bridge_gui._STYLE["font"] == bridge_style.FONT,
          "bridge_gui uses the shared font")
    check(col("accent") == "#1f6fb2", "hex colour of the accent")
    check(m._BAR_BG == col("header_bg") and m._BG == col("window_bg"),
          "top bar and window background as the bridge windows")


def test_button_colours():
    bc = m._button_colours
    check(bc("normal") == (col("button_bg"), m._C_TEXT),
          "button: white at rest")
    check(bc("normal", hover=True)[0] == col("status_bg"),
          "button: light grey under the mouse")
    check(bc("disabled", hover=True)[0] == col("button_bg"),
          "disabled button: no hover")
    check(bc("normal", True) == (col("accent"), col("header_fg")),
          "primary button: accent with white text")
    check(bc("normal", True, True)[0] == col("accent_hover"),
          "primary button: darker under the mouse")
    check(bc("disabled", True, True)[0] == col("accent"),
          "disabled primary button: no hover")


def _tk_root():
    if m.tk is None:
        return None
    try:
        root = m.tk.Tk()
    except Exception as e:     # no display
        print("SKIP tkinter part: {0}".format(e))
        return None
    root.withdraw()            # before anything is drawn: never shown
    return root


def test_buttons_tk(root):
    btn = m._flat_button(root, u"Map", lambda: None)
    check(btn.cget("relief") == "flat" and
          int(str(btn.cget("borderwidth"))) == 0, "flat, no 3D border")
    check(str(btn.cget("background")) == col("button_bg"),
          "rest colour white")
    check(str(btn.cget("highlightbackground")) == col("line"),
          "1 px border in the line colour")
    check(str(btn.cget("highlightcolor")) == col("accent"),
          "keyboard focus in the accent colour")
    check(str(btn.cget("disabledforeground")) == col("scroll_thumb"),
          "disabled text grey")
    m._button_hover(btn, True)
    check(str(btn.cget("background")) == col("status_bg"), "hover")
    m._set_button_state(btn, "disabled")
    check(str(btn.cget("state")) == "disabled" and
          str(btn.cget("background")) == col("button_bg"),
          "disabled: state and rest colour (no hover left behind)")
    m._button_hover(btn, True)
    check(str(btn.cget("background")) == col("button_bg"),
          "disabled: no hover colour")
    m._set_button_state(btn, "normal")
    m._button_hover(btn, True)
    check(str(btn.cget("background")) == col("status_bg"),
          "enabled again: hover works")
    m._button_hover(btn, False)
    check(str(btn.cget("background")) == col("button_bg"), "leave: rest")
    prim = m._flat_button(root, u"Start", lambda: None, primary=True)
    check(str(prim.cget("background")) == col("accent") and
          str(prim.cget("foreground")) == col("header_fg"),
          "primary: accent and white")
    btn.destroy()
    prim.destroy()


def test_file_buttons(root):
    """The buttons of the files of the run shown: disabled while the file
    is missing, enabled once it is there (_update_buttons)."""
    tmp = tempfile.mkdtemp(prefix="mab_convlook_")
    try:
        mess = os.path.join(tmp, "Model_20260101_120000.mess")
        open(mess, "w").close()
        args = argparse.Namespace(
            mess=mess, since=0.0, resi=None, iter_max=None, log=None,
            console=None, exit_after_finish=None, lang="en", paraview=None,
            scale=None)
        top = m.tk.Toplevel(root)
        top.withdraw()
        mon = m.Monitor(top, args)
        b = mon.btn_files
        state = dict((k, str(b[k].cget("state"))) for k in b)
        check(state["comm"] == "disabled" and state["mail"] == "disabled",
              "no .comm/.mail: their buttons disabled")
        check(state["summary"] == "normal" and state["folder"] == "normal"
              and state["rmed"] == "normal",
              "Summary (from the .mess), Folder and ParaView enabled")
        check(str(b["comm"].cget("background")) == col("button_bg"),
              "disabled button in the rest colour")
        check(str(mon.top.cget("background")) == col("header_bg"),
              "top bar dark as the header of the bridge windows")
        open(os.path.join(tmp, "Model_20260101_120000.comm"), "w").close()
        mon._update_buttons()
        check(str(b["comm"].cget("state")) == "normal",
              ".comm appears: its button enabled")
        top.destroy()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_scale(root):
    for scale, want in ((1.0, 1.0), (1.25, 1.25)):
        root.tk.call("tk", "scaling", scale * 96 / 72.0)
        m.Plot.fit_fonts(root)
        check(abs(m._K - want) < 1e-6 and m._px(10) == int(round(10 * want)),
              "display scale {0}: _K {1:.3f}, _px(10) = {2}".format(
                  scale, m._K, m._px(10)))
    check(m._ROW_DY >= 19, "row distance at least 19 px")


def main():
    test_colours()
    test_button_colours()
    root = _tk_root()
    if root is not None:
        try:
            # 100 % first: the Monitor below is built at that scale
            root.tk.call("tk", "scaling", 96 / 72.0)
            test_buttons_tk(root)
            test_file_buttons(root)
            test_scale(root)
        finally:
            root.destroy()
    print("{0} failure(s)".format(len(_FAILED)))
    return 1 if _FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
