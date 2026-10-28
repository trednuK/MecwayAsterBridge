# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of bridge_mesh._trim_covered_relations (Python 2.7 and 3,
# without Mecway and Code-Aster): a skew relation (frictionless/symmetry,
# LIAISON_OBLIQUE per node group) that an imposed displacement/rotation 0
# along global axes already covers is reduced at those nodes (GitHub
# issue #9: frictionless on the rim of a round plate with displacement
# X = Y = Z = 0 on the same nodes gave ALGELINE3_81). The results of a run:
# TestFiles/Verificatie (MO-09, LS-83).
#
#   python tests/test_bridge_trim_relations.py

from __future__ import print_function

import os
import sys
from collections import OrderedDict

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"

LOG = []


def _log(msg):
    LOG.append(msg)


bridge_utils.log = _log
import bridge_mesh as bm  # noqa: E402
bm.log = _log

FAILS = []


def check(name, cond):
    print("{0:4s} {1}".format("OK" if cond else "FAIL", name))
    if not cond:
        FAILS.append(name)


def ddl(sel, axis, value=0.0, kind="displacement"):
    prefix = "DR" if kind == "noderotation" else "D"
    return {"type": kind, "selection": sel, "aster_keyword": "DDL_IMPO",
            "aster_dict": {prefix + axis: value}}


def model(extra, bcs, node_groups):
    md = {"extra_node_groups": OrderedDict(extra), "bcs": bcs,
          "node_groups": node_groups}

    def nodes_of(sel):
        if sel in node_groups:
            return set(node_groups[sel])
        return set(md["extra_node_groups"].get(sel, ()))
    return md, nodes_of


# Radial normal at 30 degrees (shell edge: local y = edge, DX = DRY = 0),
# nodes 1..4; displacement X and Y on nodes 1, 2; Z only on node 3.
ANGL = (30.0, 0.0, 0.0)
fr = {"type": "frictionless", "selection": "Rim", "aster_dict": {},
      "oblique": [("BRFR1", ANGL, ("DX", "DRY"))]}
md, nodes_of = model([("BRFR1", [1, 2, 3, 4])],
                     [fr, ddl("A", "X"), ddl("A", "Y"), ddl("B", "Z")],
                     {"A": [1, 2], "B": [3]})
bm._trim_covered_relations(md, nodes_of)
ob = dict((g, (a, d)) for g, a, d in fr["oblique"])
extra = md["extra_node_groups"]
check("nodes 3, 4 keep DX and DRY in the original group",
      extra["BRFR1"] == [3, 4] and ob["BRFR1"][1] == ("DX", "DRY"))
other = [g for g in ob if g != "BRFR1"]
check("nodes 1, 2 only keep the rotation DRY (new group)",
      len(other) == 1 and extra[other[0]] == [1, 2]
      and ob[other[0]] == (ANGL, ("DRY",)))
check("INFO line with the number of nodes",
      any("in 2 node(s) the relation" in m for m in LOG))
check("no double condition left (_dependent_dofs)",
      not bm._dependent_dofs(bm._unit_rows(("DX", "DY")),
                             bm._unit_rows(("DRY",), ANGL)))

# Only X imposed: the radial direction is not in its span -> unchanged.
LOG[:] = []
fr2 = {"type": "frictionless", "selection": "Rim", "aster_dict": {},
       "oblique": [("BRFR1", ANGL, ("DX", "DRY"))]}
md, nodes_of = model([("BRFR1", [1, 2])], [fr2, ddl("A", "X")],
                     {"A": [1, 2]})
bm._trim_covered_relations(md, nodes_of)
check("displacement X alone: relation unchanged",
      fr2["oblique"] == [("BRFR1", ANGL, ("DX", "DRY"))] and not LOG)

# A non-zero imposed value is not a support: unchanged.
fr3 = {"type": "frictionless", "selection": "Rim", "aster_dict": {},
       "oblique": [("BRFR1", ANGL, ("DX", "DRY"))]}
md, nodes_of = model([("BRFR1", [1])],
                     [fr3, ddl("A", "X", 0.001), ddl("A", "Y")], {"A": [1]})
bm._trim_covered_relations(md, nodes_of)
check("displacement X = 1 mm: relation unchanged",
      fr3["oblique"] == [("BRFR1", ANGL, ("DX", "DRY"))])

# Rotations too: node rotation X, Y and Z 0 cover DRY; displacements none.
fr4 = {"type": "symmetry", "selection": "S", "aster_dict": {},
       "oblique": [("BRSY1", ANGL, ("DX", "DRY"))]}
md, nodes_of = model([("BRSY1", [5])],
                     [fr4] + [ddl("R", a, kind="noderotation") for a in "XYZ"],
                     {"R": [5]})
bm._trim_covered_relations(md, nodes_of)
check("node rotations 0: only DX left",
      fr4["oblique"] == [("BRSY1", ANGL, ("DX",))])

# Everything covered: the bc is skipped, the group is left unused.
fr5 = {"type": "frictionless", "selection": "Rim", "aster_dict": {},
       "oblique": [("BRFR1", ANGL, ("DX",))]}
md, nodes_of = model([("BRFR1", [1, 2])], [fr5, ddl("A", "X"),
                                           ddl("A", "Y")], {"A": [1, 2]})
bm._trim_covered_relations(md, nodes_of)
check("fully covered: skipped, no empty node group",
      fr5.get("skip") and fr5["oblique"] == []
      and md["extra_node_groups"]["BRFR1"] == [1, 2])

print()
print("{0} failure(s)".format(len(FAILS)))
sys.exit(1 if FAILS else 0)
