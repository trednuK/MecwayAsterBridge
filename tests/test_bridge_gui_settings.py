# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of the start screen logic without Windows Forms
# (bridge_gui): the order of result fields is kept when the selection does
# not change (otherwise every Start rewrote bridge_utils.py), the height
# of the status box, the scroll arithmetic of the navigation list, and a
# setting removed from the bridge (advancedtoolshub_dir, V2026.10) that is
# still in an older bridge_utils.py stays harmless when saving. Only
# CONFIG_BRIDGE in memory and a copy of bridge_utils.py in a temporary
# folder; bridge_utils.py itself is not written.
#
#   python tests/test_bridge_gui_settings.py

from __future__ import print_function

import codecs
import copy
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
import bridge_gui as g  # noqa: E402

bridge_utils.CONFIG_BRIDGE["language"] = "en"
_FAILED = []


def check(cond, text):
    print(("OK   " if cond else "FAIL ") + text)
    if not cond:
        _FAILED.append(text)


def test_keep_order():
    old = ["displacements", "velocities", "stresses", "vonmises"]
    gui = ["displacements", "stresses", "vonmises", "velocities"]
    check(g._keep_order(old, gui) == old, "same fields: saved order kept")
    check(g._keep_order(old, ["displacements", "stresses", "vonmises"]) ==
          ["displacements", "stresses", "vonmises"],
          "field removed: rest keeps its order")
    check(g._keep_order(old, ["displacements", "stresses", "vonmises",
                              "velocities", "reactions"]) ==
          old + ["reactions"], "field added: after the saved ones")
    check(g._keep_order(None, gui) == gui, "no saved list: selection as is")
    check(g._keep_order(old, ["stresses", "stresses"]) == ["stresses"],
          "field given twice: kept once")


def test_apply_values_no_change():
    """The selection list gives the fields in RESULT_FIELD_SPECS order; for
    analyses whose default has another order that must not count as a
    change (before, every Start rewrote bridge_utils.py; seen in Mecway 34)."""
    saved = copy.deepcopy(bridge_utils.CONFIG_BRIDGE)
    try:
        spec_order = list(g.RESULT_FIELD_SPECS.keys())
        values = {"general": {}, "analyses": {}}
        for name in g._analysis_names():
            fields = bridge_utils.CONFIG_BRIDGE["analyses"][name].get(
                "fields")
            if fields is None:
                continue
            values["analyses"][name] = {
                "fields": [f for f in spec_order if f in fields] +
                          [f for f in fields if f not in spec_order]}
        changes = g._apply_values(values)
        check(changes == [], "Start without changes: no SETTING changes "
              "({0})".format([c[0] for c in changes]))
        name = "harmonic_3d"
        fields = list(bridge_utils.CONFIG_BRIDGE["analyses"][name]["fields"])
        values = {"general": {}, "analyses": {name: {
            "fields": [f for f in spec_order
                       if f in fields + ["reactions"]]}}}
        changes = g._apply_values(values)
        check(len(changes) == 1 and changes[0][4] == fields + ["reactions"],
              "field added: one change, saved order + new field")
    finally:
        bridge_utils.CONFIG_BRIDGE.clear()
        bridge_utils.CONFIG_BRIDGE.update(saved)


def test_status_height():
    short = u"run: stopped.\n\nThe folder of the open model no longer exists:"
    check(g._status_height(short) == 150, "short message: at least 150")
    long_text = u"\n".join([u"line"] * 40)
    check(g._status_height(long_text) == 260, "long message: at most 260")
    lines = u"\n".join([u"line"] * 6)
    check(g._status_height(u"x" * 600) == g._status_height(lines) > 150,
          "line of 600 characters counts as 6 lines")
    # 125 %: line height 24 instead of 19, every bound grows along
    check(g._status_height(short, 24) == int(150 * 24 / 19.0),
          "125 %: minimum grows with the line height")
    check(g._status_height(long_text, 24) == int(260 * 24 / 19.0),
          "125 %: maximum grows with the line height")
    check(g._status_height(lines, 24) > g._status_height(lines),
          "125 %: six lines need more room")
    check(g._status_height(lines, 12) == 150,
          "a smaller line height keeps the bounds of 100 %")


def test_nav_scroll():
    """Arithmetic of the self-drawn scrollbar of the navigation."""
    total, view, track = 600, 300, 300
    check(g._nav_clamp(-5, total, view) == 0 and
          g._nav_clamp(999, total, view) == 300 and
          g._nav_clamp(120, total, view) == 120, "offset within 0..room")
    check(g._nav_clamp(50, 200, 300) == 0, "list fits: no scrolling")
    check(g._nav_thumb(0, total, view, track) == (0, 150),
          "thumb: half the track when half is visible")
    check(g._nav_thumb(300, total, view, track) == (150, 150),
          "thumb at the bottom at the end")
    check(g._nav_thumb(0, 10000, view, track)[1] == 24,
          "thumb at least 24 px")
    check(g._nav_visible_off(320, 352, 0, view) == 52,
          "row below the view: scroll just enough")
    check(g._nav_visible_off(10, 42, 100, view) == 10,
          "row above the view: scroll up to it")
    check(g._nav_visible_off(110, 142, 100, view) == 100,
          "row in view: no scrolling")
    check(g._nav_wheel_off(0, -120, 32, total, view) == 64,
          "wheel one notch down: two rows")
    check(g._nav_wheel_off(64, 120, 32, total, view) == 0,
          "wheel one notch up: back")
    check(g._nav_wheel_off(290, -240, 32, total, view) == 300,
          "wheel stops at the end")
    check(g._nav_drag_off(0, 75, total, view, track, 150) == 150,
          "drag: the thumb follows the mouse")
    check(g._nav_drag_off(100, -1, total, view, track, 150) == 98,
          "drag 1 px up moves 2 px (no rounding towards -inf)")
    check(g._nav_drag_off(100, 1, total, view, track, 150) == 102,
          "drag 1 px down moves 2 px")
    check(g._nav_track_off(0, 280, 0, 150, total, view) == 300,
          "click below the thumb: one view down")
    check(g._nav_track_off(300, 10, 150, 150, total, view) == 0,
          "click above the thumb: one view up")
    check(g._nav_track_off(100, 120, 50, 150, total, view) == 100,
          "click on the thumb itself: no jump")
    check(g._nav_page_index(0, 17, 11, True) == 10, "PageDown: 10 pages")
    check(g._nav_page_index(15, 17, 11, True) == 16, "PageDown stops at end")
    check(g._nav_page_index(3, 17, 11, False) == 0, "PageUp stops at top")
    check(g._nav_page_index(5, 17, 1, True) == 6, "PageDown at least 1")


def test_removed_setting_tolerated():
    """A key the start screen no longer offers (advancedtoolshub_dir,
    removed with the AdvancedToolsHub coupling) may stay in an older
    bridge_utils.py: saving other settings works and leaves that line
    alone; the start screen never offers it again."""
    check("advancedtoolshub_dir" not in [s[0] for s in g.GENERAL_SPECS],
          "removed setting not offered by the start screen")
    check("advancedtoolshub_dir" not in bridge_utils.CONFIG_BRIDGE,
          "removed setting not in CONFIG_BRIDGE")
    tmp = tempfile.mkdtemp(prefix="mab_removed_")
    try:
        path = os.path.join(tmp, "bridge_utils.py")
        shutil.copy(bridge_utils.__file__.replace(".pyc", ".py"), path)
        f = codecs.open(path, "r", "utf-8")
        text = f.read()
        f.close()
        anchor = '    "paraview_exe":    "",'
        check(text.count(anchor) == 1, "anchor line found in the copy")
        text = text.replace(anchor, anchor + '\n    "advancedtoolshub_dir": '
                            '"%ADVANCEDTOOLSHUB_DIR%",')
        f = codecs.open(path, "w", "utf-8")
        f.write(text)
        f.close()
        errors = g.save_to_bridge_utils(
            [(None, "paraview_exe", "file", "", "C:\\PV\\paraview.exe")],
            path=path)
        f = codecs.open(path, "r", "utf-8")
        after = f.read()
        f.close()
        check(errors == [], "saving another setting: no error")
        check('"advancedtoolshub_dir": "%ADVANCEDTOOLSHUB_DIR%",' in after,
              "old line left alone")
        check("paraview.exe" in after, "the changed setting is saved")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    test_keep_order()
    test_apply_values_no_change()
    test_status_height()
    test_nav_scroll()
    test_removed_setting_tolerated()
    print("{0} failure(s)".format(len(_FAILED)))
    return 1 if _FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
