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
dist = {}
tied, untied = bm.ccx_tied_nodes(tris, slaves, nodes, tolloc, 0.1,
                                 distances=dist)
check("distances: one per tied node ({0})".format(sorted(dist)),
      sorted(dist) == tied)
check("distances: normal distance to the master (103: {0:.6g})".format(
    dist.get(103, -1.0)), abs(dist.get(103, -1.0) - 2.0 * tolloc) < 1e-15
      and abs(dist.get(101, -1.0)) < 1e-15)
# KNOWN_BUGS 146: gap tolerance 0.1 x mean triangle height, at most the
# expected shell offset
check("gap tolerance = 12 tolloc for solids",
      abs(bm.bonded_gap_tolerance(tris, 0.0) - 12.0 * tolloc) < 1e-15)
check("gap tolerance capped at the expected offset",
      bm.bonded_gap_tolerance(tris, 1e-3) == 1e-3)
check("flat master: no sagitta",
      bm.master_sagitta(tris, nodes) == 0.0 and
      bm.bonded_gap_tolerance(tris, 0.0, nodes) ==
      bm.bonded_gap_tolerance(tris, 0.0))
# two unit triangles hinged on the edge (0,0,0)-(0,1,0), 0.2 rad apart:
# sagitta = longest edge (sqrt 2) x 0.2 / 8
import math as _m
hn = {1: (0.0, 0.0, 0.0), 2: (0.0, 1.0, 0.0),
      3: (-1.0, 0.0, 0.0),
      4: (_m.cos(0.2), 0.0, _m.sin(0.2))}
hinge = [((1, 2, 3), None, (0.0, 0.0, 1.0), 0.0, None),
         ((2, 1, 4), None, (-_m.sin(0.2), 0.0, _m.cos(0.2)), 0.0, None)]
check("curved master: sagitta L theta / 8",
      abs(bm.master_sagitta(hinge, hn) - 2 ** 0.5 * 0.2 / 8.0) < 1e-12)
# KNOWN_BUGS 147: master face nodes per tied node, weights, redundancy
masters = {}
bm.ccx_tied_nodes(tris, slaves, nodes, tolloc, 0.0, masters=masters)
face1 = tuple(faces[0]["nodes"])
check("masters: face nodes of the triangle ({0})".format(masters.get(101)),
      set(masters.get(101, ())) == set(face1))
# slave 107 on the shared edge x = 1: only the two edge nodes weigh
w107 = bm._tie_weight_nodes(masters[107], nodes, nodes[107])
check("weights: node on a face edge -> only the edge nodes ({0})".format(
    w107), sorted(nodes[n][0] for n in w107) == [1.0, 1.0])
edge = [n for n in face1 if nodes[n][0] == 0.0]
held = dict((n, {"DX": 0.0}) for n in edge)
nodes[108] = (0.0, 0.5, 0.0)
held[108] = {"DX": 0.0, "DZ": 0.0}
tie = {"raccord": "MASSIF", "selections": ("M", "S"),
       "tie_masters": {108: face1}}
red, warn = bm._tied_overlaps([tie], held, nodes)
check("slave on x = 0 held in DX like its edge masters: DX redundant; DZ "
      "held only on the slave is no double condition ({0}, {1})".format(
          red, dict(warn)), red == {108: set(["DX"])} and not warn)
for n in edge:
    held[n]["DZ"] = 1e-3
red, warn = bm._tied_overlaps([tie], held, nodes)
check("masters held in DZ with another value: WARNING",
      red == {108: set(["DX"])} and list(warn.values()) == [set([108])])
red, warn = bm._tied_overlaps([tie], {108: {"DX": 0.0}}, nodes,
                              dict((n, set(["DX"])) for n in edge))
check("masters time-dependent in DX: WARNING, nothing dropped",
      not red and list(warn.values()) == [set([108])])
for racc in ("COQUE", "MASSIF_COQUE"):
    tie["raccord"] = racc
    red, warn = bm._tied_overlaps([tie], held, nodes)
    check("raccord {0}: nothing dropped, WARNING".format(racc),
          not red and warn)
tie["raccord"] = "MASSIF"
tie["tie_gap"], tie["tie_tolloc"] = {108: 0.01}, 1e-4
red, warn = bm._tied_overlaps([tie], held, nodes)
check("slave across a gap: nothing dropped, WARNING", not red and warn)
tie["tie_gap"] = {108: 0.0}
red, warn = bm._tied_overlaps([tie], held, nodes, None, set([108] + edge))
check("symmetry relation on slave and masters: WARNING",
      red == {108: set(["DX"])} and list(warn.values()) == [set([108])])
# two pairs tying each other (slave 120 on a face with corner 121 at the
# same point, slave 121 on a face with corner 120): neither support may go
cn = {120: (5.0, 5.0, 5.0), 121: (5.0, 5.0, 5.0), 122: (6.0, 5.0, 5.0),
      123: (6.0, 6.0, 5.0), 124: (5.0, 6.0, 5.0)}
nodes.update(cn)
cyc = [{"raccord": "MASSIF", "selections": ("A", "B"),
        "tie_masters": {120: (121, 122, 123, 124)}},
       {"raccord": "MASSIF", "selections": ("B", "A"),
        "tie_masters": {121: (120, 122, 123, 124)}}]
red, warn = bm._tied_overlaps(cyc, {120: {"DX": 0.0}, 121: {"DX": 0.0}},
                              nodes)
check("cyclic ties: neither support dropped ({0}, {1})".format(
    red, dict(warn)), not red and sum(len(v) for v in warn.values()) == 2)
for n in cn:
    del nodes[n]

# KNOWN_BUGS 147, thermal: slave 108 and its weighted edge masters with the
# same constant temperature -> 108 leaves the thermal tie; other value,
# time-dependent, gap -> WARNING; a free master -> nothing
tt = {"tie_masters": {108: face1}, "tie_gap": {108: 0.0}, "tie_tolloc": 1e-4}
fx = dict((n, 350.0) for n in edge)
fx[108] = 350.0
check("thermal: same temperature on slave and masters -> dropped",
      bm._tied_fixed_temp(tt, fx, set(), nodes) == (set([108]), set()))
fx2 = dict(fx)
fx2[edge[0]] = 360.0
check("thermal: another value on a master -> WARNING",
      bm._tied_fixed_temp(tt, fx2, set(), nodes) == (set(), set([108])))
check("thermal: master time-dependent -> WARNING",
      bm._tied_fixed_temp(tt, dict((k, v) for k, v in fx.items()
                                   if k != edge[0]), set([edge[0]]),
                          nodes) == (set(), set([108])))
check("thermal: a master free -> no double condition",
      bm._tied_fixed_temp(tt, dict((k, v) for k, v in fx.items()
                                   if k != edge[0]), set(),
                          nodes) == (set(), set()))
tt["tie_gap"] = {108: 0.01}
check("thermal: across a gap -> WARNING",
      bm._tied_fixed_temp(tt, fx, set(), nodes) == (set(), set([108])))
# two pairs tying each other: both rows go (every node keeps its TEMP_IMPO)
nodes.update(cn)
both = dict((n, 300.0) for n in cn)
d1 = bm._tied_fixed_temp(cyc[0], both, set(), nodes)
d2 = bm._tied_fixed_temp(cyc[1], both, set(), nodes)
check("thermal: cyclic ties both dropped ({0}, {1})".format(d1, d2),
      d1 == (set([120]), set()) and d2 == (set([121]), set()))
for n in cn:
    del nodes[n]

# _drop_bonded_redundant on a small model_data: node selection 'Sym' (DX
# 0) on slave 108 and the master edge, 'Pin' (DX, DZ 0) on 108 only:
# 'Sym' loses 108, 'Pin' is split into DZ on 108 and the rest
from collections import OrderedDict as _OD
md = {"bonded": [{"raccord": "MASSIF", "selections": ("M", "S"),
                  "tie_masters": {108: face1}, "tie_gap": {108: 0.0},
                  "tie_tolloc": 1e-4}],
      "node_groups": {"Sym": ["N%d" % n for n in edge + [108]],
                      "Pin": ["N108", "N%d" % edge[0]]},
      "extra_node_groups": _OD(), "group_face_list": {},
      "mesh_nodes": dict(list(nodes.items()) + [(108, (0.0, 0.5, 0.0))]),
      "_conn": dict(conn),
      "bcs": [{"type": "displacement", "selection": "Sym",
               "aster_keyword": "DDL_IMPO", "aster_dict": {"DX": 0.0}},
              {"type": "displacement", "selection": "Pin",
               "aster_keyword": "DDL_IMPO",
               "aster_dict": {"DX": 0.0, "DZ": 0.0}}]}
bm._drop_bonded_redundant(md)
groups = md["extra_node_groups"]
sym, pin = md["bcs"][0], md["bcs"][1]
check("drop: 'Sym' without the slave ({0})".format(
    groups.get(sym["selection"])),
      sym["aster_target"] == "GROUP_NO" and
      sorted(groups[sym["selection"]]) == sorted(edge))
copies = md["bcs"][2:]
check("drop: 'Pin' split, DZ kept on the slave ({0})".format(
    [(c["aster_dict"], groups.get(c["selection"])) for c in copies]),
      len(copies) == 1 and copies[0]["aster_dict"] == {"DZ": 0.0} and
      groups[copies[0]["selection"]] == [108] and
      groups[pin["selection"]] == [edge[0]])

# KNOWN_BUGS 147, relations: a symmetry/frictionless relation 0 along a
# global axis (rel_held) counts as a support 0 in the master test
tie = {"raccord": "MASSIF", "selections": ("M", "S"),
       "tie_masters": {108: face1}, "tie_gap": {108: 0.0}, "tie_tolloc": 1e-4}
rel = dict((n, {"DX": 0.0}) for n in edge + [108])
red, warn = bm._tied_overlaps([tie], {}, nodes, None, None, rel)
check("relation on slave and masters: DX redundant ({0}, {1})".format(
    red, dict(warn)), red == {108: set(["DX"])} and not warn)
red, warn = bm._tied_overlaps([tie], dict((n, {"DX": 0.0}) for n in edge),
                              nodes, None, None, {108: {"DX": 0.0}})
check("relation on the slave, masters by DDL_IMPO: DX redundant",
      red == {108: set(["DX"])} and not warn)
red, warn = bm._tied_overlaps([tie], {108: {"DX": 0.0}}, nodes, None, None,
                              dict((n, {"DX": 0.0}) for n in edge))
check("DDL_IMPO on the slave, masters by a relation: DX redundant",
      red == {108: set(["DX"])} and not warn)
red, warn = bm._tied_overlaps([tie], {108: {"DX": 1e-3}}, nodes, None, None,
                              dict((n, {"DX": 0.0}) for n in edge))
check("slave DX 1 mm, masters in a relation 0: WARNING, nothing dropped",
      not red and list(warn.values()) == [set([108])])
corner = [n for n in face1 if nodes[n][0] == 0.0 and nodes[n][1] == 0.0]
nodes[109] = (0.0, 0.0, 0.0)
tie2 = dict(tie, tie_masters={109: face1}, tie_gap={109: 0.0})
red, warn = bm._tied_overlaps(
    [tie2], {}, nodes, None, None,
    dict((n, {"DX": 0.0, "DY": 0.0}) for n in corner + [109]))
check("corner node in two planes: DX and DY redundant ({0})".format(red),
      red == {109: set(["DX", "DY"])} and not warn)
red, warn = bm._tied_overlaps([tie], {}, nodes, None, set(edge + [108]))
check("oblique plane (relation not along an axis): WARNING only",
      not red and list(warn.values()) == [set([108])])
red, warn = bm._tied_overlaps([tie], {}, nodes, None, set([108]),
                              dict((n, {"DX": 0.0}) for n in edge))
check("oblique relation on the slave, masters in an axis plane: WARNING",
      not red and list(warn.values()) == [set([108])])
fixed_m = dict((n, dict((d, 0.0) for d in bm._ALL_DOFS)) for n in edge)
red, warn = bm._tied_overlaps([tie], fixed_m, nodes, None, set([108]))
check("oblique relation on the slave, masters fixed: WARNING",
      not red and list(warn.values()) == [set([108])])
red, warn = bm._tied_overlaps([tie], dict((n, {"DY": 0.0}) for n in edge),
                              nodes, None, set([108]))
check("oblique relation on the slave, masters held by DDL_IMPO: WARNING",
      not red and list(warn.values()) == [set([108])])
red, warn = bm._tied_overlaps([tie], {}, nodes,
                              dict((n, set(["DZ"])) for n in edge), set([108]))
check("oblique relation on the slave, masters time-dependent: WARNING",
      not red and list(warn.values()) == [set([108])])
red, warn = bm._tied_overlaps([tie], {edge[0]: {"DX": 0.0}}, nodes, None,
                              set([108]))
check("oblique relation on the slave, a master free: nothing",
      not red and not warn)
# end to end: oblique symmetry on the slave, Fixed on the masters only
md = {"bonded": [dict(tie)], "node_groups": {"Vast": ["N%d" % n
                                                      for n in edge]},
      "extra_node_groups": _OD([("BRSY1", [108])]), "group_face_list": {},
      "mesh_nodes": dict(nodes), "_conn": dict(conn),
      "bcs": [{"type": "fixed", "selection": "Vast",
               "aster_dict": {"BLOCAGE": ("DEPLACEMENT",)}},
              {"type": "symmetry", "selection": "Sym", "aster_dict": {},
               "oblique": [("BRSY1", (30.0, 0.0, 0.0), ("DX",))]}]}
logged = []
_log = bm.log
bm.log = lambda msg: logged.append(msg)
try:
    bm._drop_bonded_redundant(md)
finally:
    bm.log = _log
check("end to end: oblique relation on the slave, fixed masters: WARNING",
      any(m.startswith("WARNING: Bonded contact") and "108" in m
          for m in logged))
nodes.update(cn)
red, warn = bm._tied_overlaps(cyc, {}, nodes, None, None,
                              {120: {"DX": 0.0}, 121: {"DX": 0.0}})
check("relation, two pairs tying each other: neither dropped",
      not red and sum(len(v) for v in warn.values()) == 2)
for n in cn:
    del nodes[n]
tie_ddl = dict(tie, relations=[([108], ["DX"], [1.0])])
red, warn = bm._tied_overlaps([tie_ddl], {}, nodes, None, None, rel)
check("a pair on the LIAISON_DDL route is left to _tied_rows",
      not red and not warn)

# _exact_relation_dofs: DNOR 0 on a flat face -> the normal DOF, DNOR != 0
# or an oblique ANGL_NAUT -> None (WARNING route)
fx_md = {"extra_node_groups": _OD([("G1", [1, 2])])}
fr = {"type": "frictionless", "selection": "F", "aster_keyword": "FACE_IMPO",
      "aster_dict": {"DNOR": -0.0}}
flat = {"normals": [(1.0, 0.0, 0.0), (-1.0, 0.0, 0.0)]}
nof = lambda sel: set([1, 2])
check("frictionless DNOR 0 on a flat face: DX",
      bm._exact_relation_dofs(fx_md, fr, nof, flat) ==
      {1: set(["DX"]), 2: set(["DX"])})
check("frictionless DNOR != 0: None",
      bm._exact_relation_dofs(fx_md, dict(fr, aster_dict={"DNOR": -1e-3}),
                              nof, flat) is None)
sy = {"type": "symmetry", "selection": "S", "oblique": [
    ("G1", (30.0, 0.0, 0.0), ("DX",))]}
check("symmetry in an oblique plane: None",
      bm._exact_relation_dofs(fx_md, sy, nof, None) is None)
sy["oblique"] = [("G1", (0.0, 0.0, 0.0), ("DX",), {"DX": 1e-3})]
check("relation with a non-zero value (4th element): None",
      bm._exact_relation_dofs(fx_md, sy, nof, None) is None)


def rel_md(bcs, groups):
    return {"bonded": [dict(tie)],
            "node_groups": {}, "extra_node_groups": _OD(groups),
            "group_face_list": {}, "mesh_nodes": dict(nodes),
            "_conn": dict(conn), "bcs": bcs}


# Symmetry as LIAISON_OBLIQUE groups: a solid group (DX) and a group of the
# same nodes with DX, DRY and a 4th element: the slave leaves DX only
md = rel_md([{"type": "symmetry", "selection": "Sym", "aster_dict": {},
              "oblique": [("BRSY1", (0.0, 0.0, 0.0), ("DX",)),
                          ("BRSY2", (0.0, 0.0, 0.0), ("DX", "DRY"),
                           {"DX": 0.0})]}],
            [("BRSY1", sorted(edge + [108])), ("BRSY2", sorted(edge + [108]))])
bm._drop_bonded_redundant(md)
ob = md["bcs"][0]["oblique"]
g = md["extra_node_groups"]
check("symmetry: slave out of the DX group, group reused ({0})".format(ob),
      ob[0][0] == "BRSY1" and sorted(g["BRSY1"]) == sorted(edge))
check("symmetry: the other ddls and the 4th element stay on the slave",
      ob[1][0] == "BRSY2" and sorted(g["BRSY2"]) == sorted(edge) and
      ob[2][1:] == ((0.0, 0.0, 0.0), ("DRY",), {"DX": 0.0}) and
      g[ob[2][0]] == [108])
# Frictionless FACE_IMPO DNOR 0 on a flat face (group_faces normals):
# SANS_GROUP_NO with the slave; a face with only tied slave nodes skipped
face_list = {"Fr": [{"kind": "solid", "nodes": edge + [108]}],
             "Fr2": [{"kind": "solid", "nodes": [108]}]}
md = rel_md([{"type": "frictionless", "selection": "Fr",
              "aster_keyword": "FACE_IMPO", "aster_target": "GROUP_MA",
              "aster_dict": {"DNOR": -0.0}}], [])
md["group_face_list"] = face_list
gf = {"Fr": {"normals": [(-1.0, 0.0, 0.0)]}}
bm._drop_bonded_redundant(md, None, gf)
fb = md["bcs"][0]
check("frictionless: SANS_GROUP_NO with the slave ({0})".format(
    fb.get("sans_group_no")), len(fb.get("sans_group_no", [])) == 1 and
      md["extra_node_groups"][fb["sans_group_no"][0]] == [108]
      and not fb.get("skip"))
md = rel_md([{"type": "frictionless", "selection": "Fr",
              "aster_keyword": "FACE_IMPO", "aster_target": "GROUP_MA",
              "aster_dict": {"DNOR": -0.0}},
             {"type": "frictionless", "selection": "Fr2",
              "aster_keyword": "FACE_IMPO", "aster_target": "GROUP_MA",
              "aster_dict": {"DNOR": -0.0}}], [])
md["group_face_list"] = face_list
gf["Fr2"] = {"normals": [(-1.0, 0.0, 0.0)]}
bm._drop_bonded_redundant(md, None, gf)
check("frictionless on only the slave node: skipped, never emptied",
      md["bcs"][1].get("skip") and not md["bcs"][1].get("sans_group_no"))
# Fixed support on the masters (SANS_*: the relation does not hold them,
# the fixed support does) and a relation on the slave: slave out
md = rel_md([{"type": "fixed", "selection": "Vast", "aster_dict":
              {"BLOCAGE": ("DEPLACEMENT",)}},
             {"type": "symmetry", "selection": "Sym", "aster_dict": {},
              "oblique": [("BRSY1", (0.0, 0.0, 0.0), ("DX",))]}],
            [("BRSY1", sorted(edge + [108]))])
md["node_groups"] = {"Vast": ["N%d" % n for n in edge]}
bm._drop_bonded_redundant(md)
check("fixed masters, relation on the slave: slave out of the relation",
      sorted(md["extra_node_groups"]["BRSY1"]) == sorted(edge))
# Fixed slave (solid) on an oblique plane, masters fixed: the fixed support
# stays (without it the oblique relation would hold the slave), WARNING
md = rel_md([{"type": "fixed", "selection": "Vast", "aster_dict":
              {"BLOCAGE": ("DEPLACEMENT",)}},
             {"type": "symmetry", "selection": "Sym", "aster_dict": {},
              "oblique": [("BRSY1", (30.0, 0.0, 0.0), ("DX",))]}],
            [("BRSY1", sorted(edge + [108]))])
md["node_groups"] = {"Vast": ["N%d" % n for n in edge + [108]]}
bm._drop_bonded_redundant(md)
check("fixed slave in an oblique relation: fixed support kept",
      md["bcs"][0]["selection"] == "Vast" and not md["bcs"][0].get("skip"))
# Fixed slave in an axis-aligned relation, masters fixed: the fixed support
# loses the slave and so does the relation
md = rel_md([{"type": "fixed", "selection": "Vast", "aster_dict":
              {"BLOCAGE": ("DEPLACEMENT",)}},
             {"type": "symmetry", "selection": "Sym", "aster_dict": {},
              "oblique": [("BRSY1", (0.0, 0.0, 0.0), ("DX",))]}],
            [("BRSY1", sorted(edge + [108]))])
md["node_groups"] = {"Vast": ["N%d" % n for n in edge + [108]]}
bm._drop_bonded_redundant(md)
check("fixed slave in an axis relation: out of both ({0})".format(
    md["extra_node_groups"]),
      sorted(md["extra_node_groups"][md["bcs"][0]["selection"]]) ==
      sorted(edge) and sorted(md["extra_node_groups"]["BRSY1"]) ==
      sorted(edge))

# KNOWN_BUGS 147, LIAISON_DDL route: _tied_rows. Slave 201 tied to 202, 203
# (weights 0.5); translation rows DX, DY and two rotation rows.
rows = [([201, 202, 203], ["DX"] * 3, [1.0, -0.5, -0.5]),
        ([201, 202, 203], ["DY"] * 3, [1.0, -0.5, -0.5]),
        ([201, 201, 202, 202, 203, 203], ["DRX", "DRY"] * 3,
         [0.6, 0.8, -0.3, -0.4, -0.3, -0.4])]
hx = dict((n, {"DX": 0.0}) for n in (201, 202, 203))
kept, removed, w = bm._tied_rows(rows, hx)
check("rows: DX row removed, others kept ({0}, {1})".format(removed, w),
      removed == 1 and kept == rows[1:] and not w)
kept, removed, w = bm._tied_rows(rows, dict(list(hx.items()) + [(203, {"DX": 1e-3})]))
check("rows: another value on a row node -> WARNING, row kept",
      removed == 0 and w == set([201]))
kept, removed, w = bm._tied_rows(rows, {201: {"DX": 0.0}},
                                 {202: set(["DX"]), 203: set(["DX"])})
check("rows: time-dependent on the row nodes -> WARNING",
      removed == 0 and w == set([201]))
kept, removed, w = bm._tied_rows(rows, {201: {"DX": 0.0}, 202: {"DX": 0.0}})
check("rows: a row node free -> nothing", removed == 0 and not w)
kept, removed, w = bm._tied_rows(rows, {}, None,
                                 dict((n, {"DX": 0.0}) for n in rows[0][0]))
check("rows: symmetry relation on all row nodes -> WARNING, row kept",
      removed == 0 and w == set([201]))
rot = dict((n, {"DRX": 0.0, "DRY": 0.0}) for n in (201, 202, 203))
kept, removed, w = bm._tied_rows(rows, rot)
check("rows: rotation row fully held -> WARNING kept, not removed",
      removed == 0 and kept == rows and w == set([201]))
kept, removed, w = bm._tied_rows(rows[:2], {201: {"DRX": 0.0},
                                            202: {"DRX": 0.0},
                                            203: {"DRX": 0.0}},
                                 rot_ddl=("DRX", "DRY"))
check("rows: LIAISON_MAIL rotation (quadratic master) held -> WARNING",
      removed == 0 and w == set([201]))
kept, removed, w = bm._tied_rows(rows, {}, None, None, set([201, 202, 203]))
check("rows: all row nodes in an oblique relation -> WARNING",
      w == set([201]))
kept, removed, w = bm._tied_rows(
    rows, dict((n, dict((d, 0.0) for d in bm._ALL_DOFS))
               for n in (202, 203)), None, None, set([201]))
check("rows: slave in a relation, row nodes fixed -> WARNING",
      removed == 0 and w == set([201]))
kept, removed, w = bm._tied_rows(rows, {202: {"DZ": 0.0}}, None, None,
                                 set([201, 203]))
check("rows: slave in a relation, row nodes in a relation or held -> WARNING",
      w == set([201]))
kept, removed, w = bm._tied_rows(rows, {202: {"DZ": 0.0}}, None, None,
                                 set([201]))
check("rows: slave in a relation, a row node free -> nothing", not w)
both = dict((n, {"DX": 0.0, "DY": 0.0}) for n in (201, 202, 203))
kept, removed, w = bm._tied_rows(rows[:2], both)
check("rows: every row removed -> empty list", removed == 2 and kept == [])
# _render_mpcs with an empty relations list: no LIAISON_DDL, no LIAISON_MAIL
import bridge_to_aster as bta
out = bta._render_mpcs({"bonded": [{"relations": [], "master": "M",
                                    "slave": "S", "raccord": "COQUE",
                                    "selections": ("A", "B")}]})
check("render_mpcs: empty relations -> nothing ({0})".format(dict(out)),
      not out.get("LIAISON_DDL") and not out.get("LIAISON_MAIL"))
out = bta._render_mpcs({"bonded": [{"relations": [], "master": "M",
                                    "slave": "S", "raccord": "COQUE",
                                    "ddl": ("DRX", "DRY"),
                                    "selections": ("A", "B")}]})
check("render_mpcs: empty relations with rotations -> LIAISON_MAIL only",
      not out.get("LIAISON_DDL") and len(out.get("LIAISON_MAIL", [])) == 1)
# _drop_bonded_redundant end to end on the route (no tie_masters needed)
md = {"bonded": [{"raccord": "COQUE", "selections": ("P", "R"),
                  "relations": list(rows)}],
      "node_groups": {"H": ["N201", "N202", "N203"]},
      "extra_node_groups": _OD(), "group_face_list": {},
      "mesh_nodes": {201: (0, 0, 0), 202: (0, 0, 0), 203: (1, 0, 0)},
      "_conn": {}, "_bonded_nprec_off": True,
      "bcs": [{"type": "displacement", "selection": "H",
               "aster_keyword": "DDL_IMPO", "aster_dict": {"DX": 0.0}}]}
bm._drop_bonded_redundant(md)
check("route: DX row removed, support kept",
      md["bonded"][0]["relations"] == rows[1:] and
      md["bcs"][0]["selection"] == "H")
# bonded_close_gap: moves onto the triangle plane, gate, busy, curved,
# all or nothing per face (_close_gap_moves); a flat master face z = 0
cg_nodes = {1: (0.0, 0.0, 0.0), 2: (1.0, 0.0, 0.0), 3: (1.0, 1.0, 0.0),
            4: (0.0, 1.0, 0.0),
            11: (0.2, 0.2, 0.05), 12: (0.8, 0.2, 0.05), 13: (0.8, 0.8, 0.05),
            14: (0.2, 0.8, 0.05)}
plane = ((0.0, 0.0, 1.0), 0.0)
sl = [11, 12, 13, 14]
face = [{"nodes": sl}]
masters_cg = dict((s, (1, 2, 3, 4)) for s in sl)
planes_cg = dict((s, plane) for s in sl)
dist = dict((s, 0.05) for s in sl)
mv, sk = bm._close_gap_moves(face, sl, dist, masters_cg, planes_cg, cg_nodes,
                             1e-4, set())
check("close gap: all four slave nodes onto z = 0 ({0})".format(mv),
      sorted(mv) == sl and all(abs(x[2]) < 1e-15 for x in mv.values())
      and abs(mv[11][0] - 0.2) < 1e-15)
mv, sk = bm._close_gap_moves(face, sl, dist, masters_cg, planes_cg, cg_nodes,
                             1e-4, set([12]))
check("close gap: a busy node keeps its whole face in place ({0})".format(
    dict(sk)), not mv and sk.get("busy") == set([12]))
far = dict((s, 0.2) for s in sl)
mv, sk = bm._close_gap_moves(face, sl, far, masters_cg, planes_cg, cg_nodes,
                             1e-4, set())
check("close gap: move > 0.1 x shortest edge (0.06) not made",
      not mv and sk.get("large"))
bent = dict(cg_nodes)
bent[3] = (1.0, 1.0, 0.01)
mv, sk = bm._close_gap_moves(face, sl, dist, masters_cg, planes_cg, bent,
                             1e-4, set())
check("close gap: curved (warped) master face not used", not mv and
      sk.get("curved"))
# a thin element under the slave face (node 15 at 0.01 below node 11):
# the gate uses the shortest distance in the elements at the node
thin = dict(cg_nodes)
thin[15] = (0.2, 0.2, 0.04)
mv, sk = bm._close_gap_moves(face, sl, dist, masters_cg, planes_cg, thin,
                             1e-4, set(), {1: ("HEXA8", [11, 12, 13, 14,
                                                         15, 15, 15, 15])})
check("close gap: thin layer under the face -> move too large ({0})".format(
    dict(sk)), not mv and sk.get("large"))
mv, sk = bm._close_gap_moves(face, sl, dist, {}, planes_cg, cg_nodes, 1e-4,
                             set())
check("close gap: no master data -> not moved", not mv and sk.get("curved"))
# _close_bonded_gap end to end on a small model_data: moves in a static
# analysis, refuses (nothing moved) in an analysis whose export does not
# pass moved_nodes
cfg = bridge_utils.CONFIG_BRIDGE
saved_active = cfg.get("active_analysis")
try:
    for active, expect in (("lin_static_3d", True), ("dyna_impl_3d", False)):
        cfg["active_analysis"] = active
        md = {"mesh_nodes": dict(cg_nodes), "_conn": {}, "bcs": [],
              "group_face_list": {}}
        d2 = dict(dist)
        bm._close_bonded_gap(md, {"type": "bondedtie"}, "c",
                             ("MASSIF", "MASSIF"), face, sl, d2, masters_cg,
                             planes_cg, 1e-4)
        moved = sorted(md.get("_moved_nodes", {}))
        check("close gap end to end in {0}: moved {1}".format(active, moved),
              (moved == sl and md["mesh_nodes"][11][2] == 0.0 and
               md["_moved_from"][11] == cg_nodes[11] and d2[11] == 0.0)
              if expect else not moved)
finally:
    cfg["active_analysis"] = saved_active
# write_moved_nodes rewrites only the moved COOR_3D lines, plus the sidecar
import tempfile, shutil, json
tmpd = tempfile.mkdtemp(prefix="cgap")
try:
    mail = os.path.join(tmpd, "m_1.mail")
    with open(mail, "w") as f:
        f.write("TITRE\n x\nFINSF\nCOOR_3D\n N1 0.0 0.0 0.0\n"
                " N11 0.2 0.2 0.05\nFINSF\nFIN\n")
    ok = bm.write_moved_nodes(mail, {"_moved_nodes": {11: (0.2, 0.2, 0.0)}})
    text = open(mail).read()
    side = json.load(open(os.path.join(tmpd, "m_1_moved.json")))
    check("write_moved_nodes: line rewritten, sidecar ({0})".format(side),
          ok and " N11 0.2 0.2 0.0\n" in text and " N1 0.0 0.0 0.0" in text
          and side == {"moved_nodes": [11]})
    import bridge_results_liml as brl
    check("results check reads the sidecar",
          brl.moved_nodes(mail) == [11])
finally:
    shutil.rmtree(tmpd, ignore_errors=True)
tied, untied = bm.ccx_tied_nodes([], slaves, nodes, tolloc, 0.0)
check("no master triangles: nothing tied", tied == [] and
      len(untied) == len(slaves))

if FAILS:
    print("\n{0} FAILED".format(len(FAILS)))
    sys.exit(1)
print("\nall OK")
