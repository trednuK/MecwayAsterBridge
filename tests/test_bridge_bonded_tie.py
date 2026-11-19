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
