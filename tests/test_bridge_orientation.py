# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of the Element orientation card (bridge_orientation; Python
# 2.7 and 3, without Mecway and Code-Aster): the card as Mecway 34 writes
# it, beams/shells/gaps/solids, formulas of the element centre, overlap
# with attributes and a second card (the card wins, the last one of two),
# unusable cards (no selection, U on a beam, V on a shell, time formula)
# and the U axes for aster_results_export (bridge_to_aster._card_u_axes).
# The results of a run: TestFiles/Verificatie (MO-31, LS-79 ... LS-82,
# BU-25, LS-31d).
#
#   python tests/test_bridge_orientation.py

from __future__ import print_function

import math
import os
import sys
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"

LOG = []


def _log(msg):
    LOG.append(msg)


bridge_utils.log = _log
import bridge_orientation as bo  # noqa: E402
bo.log = _log

FAILS = []


def check(cond, text):
    if not cond:
        FAILS.append(text)


def close(a, b):
    return all(abs(x - y) <= 1e-12 for x, y in zip(a, b))


def _card(sel, u=(0, 0, 0), v=(0, 0, 0), angle="0 rad", extra=""):
    return ET.fromstring(
        (u'<orientation selection="{0}"><ux>{1}</ux><uy>{2}</uy><uz>{3}</uz>'
         u'<vx>{4}</vx><vy>{5}</vy><vz>{6}</vz><angleu>{7}</angleu>{8}'
         u'</orientation>').format(sel, u[0], u[1], u[2], v[0], v[1], v[2],
                                    angle, extra).encode("utf-8"))


def _model():
    """Beams 1-4 along X (elset Balk, POU_D_E), truss 5, gap 6, quad4 7,
    hex8 8."""
    nodes = dict((i + 1, (0.25 * i, 0.0, 0.0)) for i in range(5))
    nodes.update({6: (0, 1, 0), 7: (1, 1, 0), 8: (0, 0, 1), 9: (1, 0, 1),
                  10: (1, 1, 1), 11: (0, 1, 1)})
    elems = [(i + 1, "line2", [i + 1, i + 2], "Balk") for i in range(4)]
    elems += [(5, "line2", [1, 6], "Staaf_TRUSS"),
              (6, "line2", [6, 7], "Gap"),
              (7, "quad4", [1, 5, 7, 6], "Plaat"),
              (8, "hex8", [1, 5, 7, 6, 8, 9, 10, 11], "Blok")]
    return {"mesh_nodes": nodes, "mesh_elements": elems,
            "elset_modelisations": {"Balk": "POU_D_E", "Staaf_TRUSS": "BARRE",
                                    "Gap": "DIS_T", "Plaat": "DKT",
                                    "Blok": "3D"},
            "discrete_sections": {"Gap": {"kind": "gap"}},
            "element_selections": {"All": list(range(1, 9)),
                                   "Half": [1, 2], "Plate": [7]},
            "beam_orientations": {}, "skipped_loads": []}


def _run(md, *cards):
    del LOG[:]
    for c in cards:
        bo.parse(c, md)
    bo.apply(md)
    return md


def test_beam_card():
    md = _run(_model(), _card("All", v=(0, 0, 1), angle=u"30 °"))
    for eid in range(1, 5):
        o = md["beam_orientations"].get(eid)
        check(o is not None and close(o["vec"], (0, 0, 1)) and
              abs(o["angle"] - math.radians(30)) < 1e-12,
              "beam {0}: {1}".format(eid, o))
    check(5 not in md["beam_orientations"] and
          6 not in md["beam_orientations"], "truss/gap got an orientation")
    check(not md["skipped_loads"], "skipped: {0}".format(md["skipped_loads"]))
    check(any("no effect on 3 element(s) (5, 6, 8)" in l for l in LOG),
          "INFO no effect: {0}".format(LOG))
    # an angle without unit is in rad (Mecway writes "30 rad")
    md = _run(_model(), _card("Half", v=(0, 1, 0), angle="30"))
    check(abs(md["beam_orientations"][1]["angle"] - 30.0) < 1e-12,
          "angle without unit: {0}".format(md["beam_orientations"]))


def test_formula():
    f = 'unit="" timeunit="s" positionunit="mm"'
    c = ET.fromstring(
        (u'<orientation selection="All"><vx>0</vx><vy {0}>x</vy>'
         u'<vz {0}>1000-x</vz><angleu unit="°" timeunit="s" '
         u'positionunit="m">30*x</angleu></orientation>').format(f)
        .encode("utf-8"))
    md = _run(_model(), c)
    o = md["beam_orientations"][2]          # centre x = 0.375 m = 375 mm
    check(close(o["vec"], (0, 375.0, 625.0)) and
          abs(o["angle"] - math.radians(30 * 0.375)) < 1e-12,
          "formula at the centre: {0}".format(o))
    bad = ET.fromstring(u'<orientation selection="All"><vz unit="" '
                        u'timeunit="s" positionunit="m">t</vz>'
                        u'</orientation>')
    md = _run(_model(), bad)
    check(md["skipped_loads"] and not md["beam_orientations"],
          "time formula not reported: {0}".format(md["skipped_loads"]))


def test_overlap():
    md = _model()
    md["beam_orientations"][1] = {"vec": (0, 1, 0), "angle": 0.0}
    _run(md, _card("All", v=(0, 0, 1)), _card("Half", v=(1, 1, 0)))
    check(close(md["beam_orientations"][1]["vec"], (1, 1, 0)) and
          close(md["beam_orientations"][3]["vec"], (0, 0, 1)),
          "overlap: {0}".format(md["beam_orientations"]))
    warns = [l for l in LOG if l.startswith("WARNING") and "already" in l]
    check(len(warns) == 2 and "1 element(s)" in warns[0] and
          "2 element(s)" in warns[1], "overlap warnings: {0}".format(warns))


def test_shell_gap_and_unusable():
    md = _run(_model(), _card("All", u=(0, 1, 0)))
    check(md["card_u_axes"] == {7: (0.0, 1.0, 0.0)} and
          md["elem_u_axes"].get(6) == (0.0, 1.0, 0.0),
          "U axis shell/gap: {0} {1}".format(md.get("card_u_axes"),
                                             md.get("elem_u_axes")))
    check(not md["beam_orientations"] and any(
        "U axis has no meaning for beams" in l for l in LOG) and any(
        "no V vector" in l for l in LOG), "U on beams: {0}".format(LOG))
    md = _run(_model(), _card("Plate", v=(0, 1, 0)))
    check(not md.get("card_u_axes") and any(
        "only apply to beams" in l for l in LOG),
        "V on a shell: {0}".format(LOG))
    md = _run(_model(), _card("Balk", v=(0, 0, 1)))
    check(md["skipped_loads"] and not md["beam_orientations"],
          "component name as selection: {0}".format(md["skipped_loads"]))


def test_u_axes_ranges():
    import bridge_to_aster
    md = {"card_u_axes": {3: (0, 1, 0), 4: (0, 1, 0), 5: (0, 1, 0),
                          9: (0, 1, 0), 7: (1, 0, 0)}}
    got = bridge_to_aster._card_u_axes(md)
    check(got == [((0.0, 1.0, 0.0), [(3, 5), (9, 9)]),
                  ((1.0, 0.0, 0.0), [(7, 7)])], "ranges: {0}".format(got))
    check(bridge_to_aster._card_u_axes({}) is None, "without cards")


def main():
    for test in (test_beam_card, test_formula, test_overlap,
                 test_shell_gap_and_unusable, test_u_axes_ranges):
        test()
    if FAILS:
        for f in FAILS:
            print(u"FAIL: {0}".format(f).encode("ascii", "replace").decode(
                "ascii"))
        return 1
    print("OK: Element orientation card (beams, formulas, overlap, shells, "
          "gaps, unusable cards, U axes for the export)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
