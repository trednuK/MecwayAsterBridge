# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
KNOWN_BUGS 66: a Wohler curve whose material also sits on beams, trusses or
springs gives a WARNING that those elements get no damage
(bridge_fatigue._check_routes); without such elements no WARNING.

Usage: python tests/test_bridge_fatigue_routes.py (CPython 3 or 2.7).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "Scripts"))

import bridge_utils  # noqa: E402
import bridge_fatigue  # noqa: E402

bridge_utils.CONFIG_BRIDGE["language"] = "en"
_LOG = []
bridge_fatigue.log = _LOG.append


def _model(beam_material):
    elsets = {"Blok": "Staal", "Plaat": "Alu"}
    mods = {"Blok": "3D", "Plaat": "DKT"}
    if beam_material:
        elsets["Balk"] = beam_material
        mods["Balk"] = "POU_D_E"
    return {"elsets": elsets, "elset_modelisations": mods}


def main():
    failed = 0
    for beam, material, want in (("Staal", "Staal", ["'Staal'"]),
                                 ("Ligger", "*", ["'Ligger'"]),
                                 ("Ligger", "Staal", []),
                                 (None, "*", []),
                                 ("Staal", "Alu", [])):
        del _LOG[:]
        plan = {"options": {"criterion": "GEEN"},
                "curves": [{"material": material, "form": "stress"}]}
        curves = bridge_fatigue._check_routes(_model(beam), plan, {})
        warns = [m for m in _LOG if "beams, trusses, cables" in m]
        ok = (bool(curves) and len(warns) == len(want) and
              all(w in warns[0] for w in want))
        print("{0} beam {1}, curve '{2}': {3}".format(
            "OK  " if ok else "FAIL", beam, material, warns))
        failed += not ok
    print("{0} failure(s)".format(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
