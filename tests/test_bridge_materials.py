# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test van materiaalvertaling (Python 2.7 en 3, zonder Mecway en
# Code-Aster):
#   - hardingscurve in totale rek: E = helling van het eerste stuk
#     (bridge_from_liml._curve_young, GitHub issue #2), niet voor een curve
#     als plastische rek; een curve die daarna nog > 1% afwijkt geeft een
#     ValueError (MATERIAL1_5, bridge_to_aster._to_aster_traction_curve);
#   - hyperelastisch (bridge_from_liml._parse_hyperelastic, issue #5):
#     K = 2/D1, D1 = 0 is een ERROR; eenheid D1 (inverse_pressure).
#
#   python tests/test_bridge_materials.py

from __future__ import print_function

import os
import sys
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "nl"

LOG = []


def _log(msg):
    LOG.append(msg)


bridge_utils.log = _log
import bridge_from_liml as bfl  # noqa: E402
import bridge_to_aster as bta  # noqa: E402
for _mod in (bfl, bta):
    _mod.log = _log

FAILS = []


def check(cond, text):
    if not cond:
        FAILS.append(text)


CURVE = [(0.0, 0.0), (0.001, 210e6), (0.011, 310e6)]


def test_curve_young():
    del LOG[:]
    e = bfl._curve_young(CURVE, 200e9, "M", "auto")
    check(abs(e - 210e9) < 1.0, "E uit de curve: {0}".format(e))
    check(any(m.startswith("WARNING:") for m in LOG),
          "WARNING bij E_tab != helling: {0}".format(LOG))
    del LOG[:]
    check(bfl._curve_young(CURVE, 210e9, "M", "auto") == 210e9 and not LOG,
          "gelijke E: geen melding: {0}".format(LOG))
    plastic = [(0.0, 250e6), (1.0, 750e6)]
    check(bfl._curve_young(plastic, 200e9, "M", "auto") == 200e9,
          "curve als plastische rek: E ongewijzigd")
    check(bfl._curve_young(CURVE, 200e9, "M", "plastic") == 200e9,
          "definitie plastic: E ongewijzigd")
    # na de aanpassing past de curve; met de tabblad-E stopt de bridge
    bta._to_aster_traction_curve("M", CURVE, 210e9, "auto")
    try:
        bta._to_aster_traction_curve("M", CURVE, 200e9, "total")
        check(False, "helling 5% anders dan E: ValueError verwacht")
    except ValueError as exc:
        check("MATERIAL1_5" in str(exc), "melding noemt MATERIAL1_5: "
              "{0}".format(exc))
    try:
        bta._to_aster_traction_curve("M", [(0.001, 250e6), (1.0, 750e6)],
                                     200e9, "plastic")
        check(False, "eerste plastische rek 0,001: ValueError verwacht")
    except ValueError:
        pass


def _mech(xml):
    return ET.fromstring(xml)


def test_hyperelastic():
    del LOG[:]
    hyp = bfl._parse_hyperelastic(_mech(
        u'<mechanical type="MooneyRivlin" hyperelasticc10="0.8 MPa" '
        u'hyperelasticc01="0.2 MPa" d1="0.001 mm²/N" />'), None,
        "MooneyRivlin", "R")
    check(hyp is not None, "Mooney-Rivlin vertaald: {0}".format(LOG))
    if hyp:
        h = hyp["hyper"]
        check(abs(h["K"] - 2.0e9) < 1.0 and h["C10"] == 0.8e6 and
              h["C01"] == 0.2e6, "C10/C01/K: {0}".format(h))
        g = 2.0 * (h["C10"] + h["C01"])
        check(abs(hyp["E"] - 2.0 * g * (1.0 + hyp["NU"])) < 1e-6 * hyp["E"],
              "E = 2 G (1 + nu): {0}".format(hyp))
        md = {"materials": {"R": hyp}}
        check(bta._relation_for(md, "R") == "ELAS_HYPER", "RELATION")
        check(bta._deformation_for("3D", "ELAS_HYPER", "PETIT", "E") ==
              "GREEN_LAGRANGE", "DEFORMATION GREEN_LAGRANGE")
    del LOG[:]
    hyp = bfl._parse_hyperelastic(_mech(
        '<mechanical type="NeoHooke" hyperelasticc10="1 MPa" />'), None,
        "NeoHooke", "N")
    check(hyp is None and any(m.startswith("ERROR:") for m in LOG),
          "D1 = 0: ERROR: {0}".format(LOG))
    md = {"materials": {"N": {"E": 1.0, "NU": 0.3, "hyper": {"K": 1.0}}},
          "elsets": {"Kubus": "N"}, "elset_modelisations": {"Kubus": "3D"}}
    del LOG[:]
    check(not bta._check_hyperelastic(md, {"solver_command":
                                           "MECA_STATIQUE"}),
          "lineair statisch: ERROR")
    check(bta._check_hyperelastic(md, {"solver_command": "STAT_NON_LINE"}),
          "niet-lineair statisch: toegestaan: {0}".format(LOG))
    md["elset_modelisations"]["Kubus"] = "DKT"
    check(not bta._check_hyperelastic(md, {"solver_command":
                                           "STAT_NON_LINE"}),
          "schaal: ERROR")


def main():
    test_curve_young()
    test_hyperelastic()
    if FAILS:
        for f in FAILS:
            print("FOUT:", f)
        sys.exit(1)
    print("OK: test_bridge_materials")


if __name__ == "__main__":
    main()
