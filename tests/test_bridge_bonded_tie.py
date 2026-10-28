# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of CCX's tie rule for bonded contact in bridge_mesh
# (_ccx_triangles, ccx_tie_tolloc, ccx_tied_nodes; KNOWN_BUGS 128), Python
# 2.7 and 3, without Mecway and Code-Aster. A slave node is tied only if a
# master triangle lies opposite it (in-face tolerance tolloc) and its
# distance to that triangle is within the position tolerance (Mecway 0 =
# tolloc). The complete check against CCX's own list of untied nodes
# (mw_in_WarnNodeMissTiedContact.nam of Mecway 34, Samples/BoltedJoint with
# bonded contacts: the same 58 nodes) and the runs: TestFiles/Verificatie
# LS-07l/m.
#
#   python tests/test_bridge_bonded_tie.py

from __future__ import print_function

import os
import sys

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"
import bridge_mesh as bm  # noqa: E402

FAILS = []


def check(name, cond):
    print("{0:4s} {1}".format("OK" if cond else "FAIL", name))
    if not cond:
        FAILS.append(name)


# Master: top faces (z = 0) of a 2 x 1 row of hex8, x = 0 .. 2, y = 0 .. 1.
nodes = {}
conn = {}
grid = {}
nid = 0
for k, z in enumerate((-1.0, 0.0)):
    for j in range(2):
        for i in range(3):
            nid += 1
            nodes[nid] = (float(i), float(j), z)
            grid[(i, j, k)] = nid
faces = []
for e, i in enumerate((0, 1)):
    c = [grid[(i, 0, 0)], grid[(i + 1, 0, 0)], grid[(i + 1, 1, 0)],
         grid[(i, 1, 0)], grid[(i, 0, 1)], grid[(i + 1, 0, 1)],
         grid[(i + 1, 1, 1)], grid[(i, 1, 1)]]
    conn[e + 1] = ("HEXA8", c)
    # Mecway/CCX face 2 = nodes 5, 6, 7, 8 (top)
    faces.append({"kind": "solid", "stype": "QUAD4", "nodes": c[4:],
                  "eid": e + 1, "fid": 2})

tris = bm._ccx_triangles(faces, nodes, conn)
check("4 triangles (2 per quad4 face)", len(tris) == 4)
check("CCX face order: first triangle (5, 6, 8) of element 1",
      tris[0][0] == (conn[1][1][4], conn[1][1][5], conn[1][1][7]))
tolloc = bm.ccx_tie_tolloc(tris)
# triangle (1,2,4): corner 1 to the diagonal 2-4 = 1/sqrt(2); triangle
# (2,3,4): corner 2 to edge 3-4 = 1; tolloc = 0.025 * mean(h / 3)
ref = 0.025 * (1.0 / 2 ** 0.5 + 1.0) / 2.0 / 3.0
check("tolloc = 2.5 % of a third of the mean height ({0:.6g})".format(
    tolloc), abs(tolloc - ref) < 1e-12)

slaves = {101: (0.5, 0.5, 0.0),          # on the master
          102: (1.5, 0.2, 0.3 * tolloc),  # small gap within tolloc
          103: (1.5, 0.5, 2.0 * tolloc),  # gap beyond tolloc
          104: (2.5, 0.5, 0.0),          # overhang: no master face
          105: (2.0 + 0.5 * tolloc, 0.5, 0.0),  # just outside, in-face tol
          106: (2.0 + 2.0 * tolloc, 0.5, 0.0),  # beyond the in-face tol
          107: (1.0, 0.5, 0.0)}          # on the shared edge
nodes.update(slaves)
tied, untied = bm.ccx_tied_nodes(tris, slaves, nodes, tolloc, 0.0)
check("tolerance 0: tied {0}".format(tied), tied == [101, 102, 105, 107])
check("tolerance 0: untied {0}".format(untied), untied == [103, 104, 106])
tied, untied = bm.ccx_tied_nodes(tris, slaves, nodes, tolloc, 0.1)
check("tolerance 0.1: the gap is tied, the overhang is not ({0})".format(
    untied), untied == [104, 106])
tied, untied = bm.ccx_tied_nodes(tris, slaves, nodes, tolloc, 10.0)
check("large tolerance: the overhang still stays free (in-face tolloc)",
      untied == [104, 106])
tied, untied = bm.ccx_tied_nodes([], slaves, nodes, tolloc, 0.0)
check("no master triangles: nothing tied", tied == [] and
      len(untied) == len(slaves))

if FAILS:
    print("\n{0} FAILED".format(len(FAILS)))
    sys.exit(1)
print("\nall OK")
