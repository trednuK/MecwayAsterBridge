# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test (CPython 3, Windows) of the dialog watchdog for a hidden
# Mecway in the verification tools (TestFiles/Verificatie/verif_lib.py,
# run_mecway; used by AD-02, --mecway-opslaan and TestFiles/Tools/
# mw_solve.py). Mecway itself is not started: a child Python stands in.
#   - a child that ends: "ok";
#   - a child that hangs: "timeout", the process is gone;
#   - a child that shows a window with an "OK" button: "dialog", killed at
#     once. The window is created off-screen (-32000) with
#     WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW, so it never appears on the
#     user's screen or takes the focus;
#   - the same window without a button is not a dialog: with other_grace
#     None it is left alone until the time limit.
#
#   python tests/test_verif_mecway_guard.py

from __future__ import print_function

import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "TestFiles", "Verificatie"))
import verif_lib as V  # noqa: E402

_FAILED = []

_WINDOW = r'''
import ctypes, time
from ctypes import wintypes as wt
u32 = ctypes.WinDLL("user32")
u32.CreateWindowExW.restype = wt.HWND
u32.CreateWindowExW.argtypes = (wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD,
                                ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, wt.HWND, wt.HMENU,
                                wt.HINSTANCE, wt.LPVOID)
WS_POPUP, WS_VISIBLE, WS_CHILD = 0x80000000, 0x10000000, 0x40000000
EX = 0x08000000 | 0x00000080          # WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
h = u32.CreateWindowExW(EX, "STATIC", "guard test", WS_POPUP | WS_VISIBLE,
                        -32000, -32000, 120, 60, None, None, None, None)
if BUTTON:
    u32.CreateWindowExW(0, "BUTTON", "OK", WS_CHILD | WS_VISIBLE, 5, 5, 50,
                        20, h, None, None, None)
time.sleep(30)
'''


def check(cond, what):
    print("{0}: {1}".format("OK  " if cond else "FAIL", what))
    if not cond:
        _FAILED.append(what)


def _child(code):
    return [sys.executable, "-c", code]


def main():
    if os.name != "nt":
        print("Windows only; skipped")
        return 0
    state, rc, _w = V.run_mecway(_child("pass"), timeout=20)
    check(state == "ok" and rc == 0, "a run that ends: ok")
    t0 = time.time()
    state, _rc, _w = V.run_mecway(_child("import time; time.sleep(30)"),
                                  timeout=1.0)
    check(state == "timeout" and time.time() - t0 < 10,
          "a run that hangs: timeout, stopped")
    t0 = time.time()
    state, _rc, wins = V.run_mecway(_child("BUTTON = True\n" + _WINDOW),
                                    timeout=20)
    check(state == "dialog" and time.time() - t0 < 10 and
          any("OK" in w[2] for w in wins),
          "a window with an OK button: dialog, killed ({0})".format(wins))
    t0 = time.time()
    state, _rc, wins = V.run_mecway(_child("BUTTON = False\n" + _WINDOW),
                                    timeout=3.0, other_grace=None)
    check(state == "timeout" and not any(V._is_dialog(w) for w in wins),
          "an off-screen window without a button: not a dialog ({0})".format(
              wins))
    print("{0} failure(s)".format(len(_FAILED)))
    return 1 if _FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
