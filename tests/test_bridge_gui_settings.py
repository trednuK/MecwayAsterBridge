# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of the start screen logic without Windows Forms
# (bridge_gui): the order of result fields is kept when the selection does
# not change (otherwise every Start rewrote bridge_utils.py), and the height
# of the status box. Only CONFIG_BRIDGE in memory; bridge_utils.py itself is
# not written.
#
#   python tests/test_bridge_gui_settings.py

from __future__ import print_function

import copy
import os
import sys

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
    check(g._status_height(u"") == 96, "welcome text: small status box")
    short = u"run: stopped.\n\nThe folder of the open model no longer exists:"
    check(g._status_height(short) == 150, "short message: at least 150")
    long_text = u"\n".join([u"line"] * 40)
    check(g._status_height(long_text) == 260, "long message: at most 260")
    lines = u"\n".join([u"line"] * 6)
    check(g._status_height(u"x" * 600) == g._status_height(lines) > 150,
          "line of 600 characters counts as 6 lines")


def main():
    test_keep_order()
    test_apply_values_no_change()
    test_status_height()
    print("{0} failure(s)".format(len(_FAILED)))
    return 1 if _FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
