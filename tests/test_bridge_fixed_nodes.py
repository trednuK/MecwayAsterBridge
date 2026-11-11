# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of the WARNING for a Fixed support on a node selection with
# nodes that Mecway's own solver leaves free (KNOWN_BUGS 135,
# bridge_from_liml._warn_fixed_on_free_nodes; CPython 3, without Mecway and
# Code-Aster): shell edge nodes and a spring-only node warn, with the count;
# a beam end node, the shared node of a beam and a shell, a coupling
# reference node and a face selection do not. The bridge keeps clamping
# (BLOCAGE), and warn_supports=False (section view) is silent.
#
#   python tests/test_bridge_fixed_nodes.py

from __future__ import print_function

import os
import sys
import shutil
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
_REPO = os.path.join(_HERE, "..")
sys.path.insert(0, os.path.join(_REPO, "Scripts"))
sys.path.insert(0, os.path.join(_REPO, "TestFiles", "Verificatie"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"
LOG = []


def _log(msg):
    LOG.append(msg)


import bridge_from_liml  # noqa: E402
bridge_from_liml.log = _log
from verif_lib import Model, quadmesh, linemesh, rect  # noqa: E402

FAILS = []


def check(cond, text):
    if not cond:
        FAILS.append(text)


STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
PLATE = '<geometric type="Plate" thickness="2 mm" />'
BAR = '<geometric type="RectBar" recta="10 mm" rectb="10 mm" />'


def plate(m):
    """Plate 100 x 40 mm, 4 x 2 quad4 (3 nodes on the edge x = 0)."""
    m.elset("Plaat", "Plaat")
    m.mat("Plaat", PLATE, STEEL)
    return quadmesh(m, "Plaat", 4, 2, rect(0, 0.1, 0, 0.04))


def warnings():
    return [l for l in LOG if "KNOWN_BUGS 135" in l]


work = tempfile.mkdtemp(prefix="mab_fixed_nodes_")
try:
    bridge_utils.CONFIG_BRIDGE["work_dir"] = work
    bridge_utils.CONFIG_BRIDGE["active_analysis"] = "lin_static_3d"

    def run(model, **kw):
        del LOG[:]
        path = model.write(os.path.join(work, "model.liml"))
        md = bridge_from_liml.extract_aster_data_from_liml(path, **kw)
        check(md is not None, "model read: {0}".format(LOG[-3:]))
        return md

    # 1. Shell edge nodes: WARNING with the count; the bridge still clamps,
    #    twice the same selection warns once
    m = Model("S30")
    q = plate(m)
    m.node_selection("Rand", sorted(q["nodes"]["u0"]))
    m.add('<fixed selection="Rand" />')
    m.add('<fixed selection="Rand" />')
    md = run(m)
    w = warnings()
    check(len(w) == 1 and "'Rand': 3 of the 3 nodes" in w[0] and
          w[0].startswith("WARNING: Fixed support"), "shell edge: {0}".format(w))
    check(all(bc["aster_dict"] == {"BLOCAGE": ("DEPLACEMENT", "ROTATION")}
              for bc in md["bcs"] if bc["type"] == "fixed"),
          "still clamped: {0}".format([bc["aster_dict"] for bc in md["bcs"]]))
    run(m, warn_supports=False)
    check(not warnings(), "warn_supports=False is silent: {0}".format(
        warnings()))

    # 1b. Dutch text with the same numbers
    bridge_utils.CONFIG_BRIDGE["language"] = "nl"
    run(m)
    w = warnings()
    check(len(w) == 1 and "'Rand': 3 van de 3 knopen" in w[0],
          "Dutch text: {0}".format(w))
    bridge_utils.CONFIG_BRIDGE["language"] = "en"

    # 2. Beam end node: no WARNING
    m = Model("S30")
    m.elset("Balk", "Balk")
    m.mat("Balk", BAR, STEEL)
    _e, nids = linemesh(m, "Balk", 4, (0, 0, 0), (1.0, 0, 0))
    m.node_selection("Eind", [nids[0]])
    m.add('<fixed selection="Eind" />')
    run(m)
    check(not warnings(), "beam end node: {0}".format(warnings()))

    # 3. Shell edge faces: no WARNING (Mecway holds those)
    m = Model("S30")
    q = plate(m)
    m.face_selection("Randvlak", q["edges"]["u0"])
    m.add('<fixed selection="Randvlak" />')
    run(m)
    check(not warnings(), "edge faces: {0}".format(warnings()))

    # 4. Shell with a beam along y = 0.02 (as LS-62): the shared edge node
    #    is a beam node, the other two are counted
    m = Model("S30")
    q = plate(m)
    m.elset("Balk", "Balk")
    m.mat("Balk", BAR, STEEL)
    linemesh(m, "Balk", 4, (0, 0.02, 0), (0.1, 0.02, 0))
    m.node_selection("Rand", sorted(q["nodes"]["u0"]))
    m.add('<fixed selection="Rand" />')
    run(m)
    w = warnings()
    check(len(w) == 1 and "'Rand': 2 of the 3 nodes" in w[0],
          "shell + beam: {0}".format(w))

    # 5. Spring-only node: WARNING
    m = Model("S30")
    m.elset("Veer", "Veer")
    m.mat("Veer", '<mechanical type="Spring" springconstant="1000 N/m" />')
    _e, nids = linemesh(m, "Veer", 1, (0, 0, 0), (1.0, 0, 0))
    m.node_selection("Grond", [nids[0]])
    m.add('<fixed selection="Grond" />')
    run(m)
    w = warnings()
    check(len(w) == 1 and "'Grond': 1 of the 1 nodes" in w[0],
          "spring-only node: {0}".format(w))

    # 6. Reference node of a coupling that is also a shell node: no WARNING;
    #    a shell node next to it in the same selection is counted
    m = Model("S30")
    q = plate(m)
    edge = sorted(q["nodes"]["u0"])
    tip = sorted(q["nodes"]["u1"])
    m.node_selection("Ref", [edge[0]])
    m.node_selection("Kop", tip)
    m.node_selection("RefPlus", [edge[0], edge[1]])
    m.add('<nodesurfacecoupling type="rigidbody" selectionsurface="Kop" '
          'selectionnode="Ref" />')
    m.add('<fixed selection="Ref" />')
    run(m)
    check(not warnings(), "coupling reference node: {0}".format(warnings()))
    m.add('<fixed selection="RefPlus" />')
    run(m)
    w = warnings()
    check(len(w) == 1 and "'RefPlus': 1 of the 2 nodes" in w[0],
          "reference node + shell node: {0}".format(w))
finally:
    shutil.rmtree(work, ignore_errors=True)

if FAILS:
    print("FAILED ({0}):".format(len(FAILS)))
    for f in FAILS:
        print("  " + f)
    sys.exit(1)
print("OK: Fixed support on nodes that Mecway leaves free (KNOWN_BUGS 135)")
