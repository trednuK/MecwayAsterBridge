# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of bridge_homard (adaptive refinement with HOMARD, step
# S35b): recognition of curved boundaries (cylinder, sphere, flat, cone
# rejected), patches with the crease angle, #ASTER-RAND, the scope check
# (node groups with more than one node, shells) and the loop that wrap()
# puts into a .comm (valid Python, markers). CPython and Mecway's
# IronPython 2.7.9:
#
#   python tests/test_bridge_homard.py
#   powershell -ExecutionPolicy Bypass -File TestFiles/Tools/run_ipy.ps1 -Script tests/test_bridge_homard.py

from __future__ import print_function

import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils as u  # noqa: E402
import bridge_custom  # noqa: E402
import bridge_homard as H  # noqa: E402

u.CONFIG_BRIDGE["language"] = "en"
u.set_run_log(None)
_FAILED = []


def check(cond, text):
    print(("OK   " if cond else "FAIL ") + text)
    if not cond:
        _FAILED.append(text)


def close(a, b, tol=1.0e-6):
    return abs(a - b) <= tol * max(1.0, abs(b))


# ---------------------------------------------------------------
# Surfaces as quad faces on a grid of (s, t) -> point
# ---------------------------------------------------------------
def grid_faces(fn, ns, nt, s0, s1, t0, t1, start=1):
    """Quad faces (ring of 4 corner nodes) on fn(s, t); returns (faces,
    coords)."""
    coords = {}
    ids = {}
    nid = start
    for i in range(ns + 1):
        for j in range(nt + 1):
            s = s0 + (s1 - s0) * i / float(ns)
            t = t0 + (t1 - t0) * j / float(nt)
            coords[nid] = fn(s, t)
            ids[(i, j)] = nid
            nid += 1
    faces = []
    for i in range(ns):
        for j in range(nt):
            ring = [ids[(i, j)], ids[(i + 1, j)], ids[(i + 1, j + 1)],
                    ids[(i, j + 1)]]
            faces.append((frozenset(ring), ring))
    return faces, coords


def cylinder(c, r, h):
    def fn(s, t):
        return (c[0] + r * math.cos(s), c[1] + r * math.sin(s), c[2] + t)
    return fn


def fit_of(faces, coords):
    groups, normals = H.patches(faces, coords)
    pts = list(coords.values())
    return groups, H.fit_surface(pts, [n for n in normals if n])


# cylinder r = 0.01 about z through (0.1, -0.2), quarter, 4 x 2 faces
faces, coords = grid_faces(cylinder((0.1, -0.2, 0.0), 0.01, 0.02), 4, 2,
                           0.0, math.pi / 2, 0.0, 0.02)
groups, fit = fit_of(faces, coords)
check(len(groups) == 1, "quarter cylinder (22.5 degrees per face) is one patch")
check(fit["shape"] == "CYLINDRE", "cylinder recognised: {0}".format(fit["shape"]))
if fit["shape"] == "CYLINDRE":
    p = fit["params"]
    check(close(p[6], 0.01) and close(abs(p[5]), 1.0),
          "radius 0.01 and axis z: {0}".format(p))
    # point on the axis: distance of (0.1, -0.2) to the axis line is zero
    check(math.hypot(p[0] - 0.1, p[1] + 0.2) < 1.0e-9,
          "axis through (0.1, -0.2)")

# tilted cylinder (axis (1, 1, 1)/sqrt 3)
ax = tuple(1.0 / math.sqrt(3.0) for _ in range(3))
e1 = H._unit(H._cross(ax, (1.0, 0.0, 0.0)))
e2 = H._cross(ax, e1)


def tilted(s, t):
    return tuple(0.05 * (math.cos(s) * e1[i] + math.sin(s) * e2[i]) +
                 t * ax[i] for i in range(3))


faces, coords = grid_faces(tilted, 6, 3, 0.0, math.pi, 0.0, 0.1)
groups, fit = fit_of(faces, coords)
check(fit["shape"] == "CYLINDRE" and close(fit["params"][6], 0.05) and
      close(abs(H._dot(fit["params"][3:6], ax)), 1.0),
      "tilted cylinder: axis and radius")


# sphere r = 0.2 around (1, 2, 3), octant
def sphere(s, t):
    return (1.0 + 0.2 * math.cos(s) * math.cos(t),
            2.0 + 0.2 * math.sin(s) * math.cos(t), 3.0 + 0.2 * math.sin(t))


faces, coords = grid_faces(sphere, 4, 4, 0.0, math.pi / 2, 0.0, 1.2)
groups, fit = fit_of(faces, coords)
check(fit["shape"] == "SPHERE" and close(fit["params"][3], 0.2) and
      close(fit["params"][0], 1.0) and close(fit["params"][2], 3.0),
      "sphere recognised: {0}".format(fit))

# flat face: PLAN (no boundary following)
faces, coords = grid_faces(lambda s, t: (s, t, 0.3 * s), 3, 3, 0.0, 1.0,
                           0.0, 1.0)
groups, fit = fit_of(faces, coords)
check(fit["shape"] == "PLAN", "flat face -> PLAN")


# cone: not recognised (no cone fit), deviation reported
def cone(s, t):
    r = 0.01 + 0.5 * t
    return (r * math.cos(s), r * math.sin(s), t)


faces, coords = grid_faces(cone, 4, 3, 0.0, math.pi / 2, 0.0, 0.02)
groups, fit = fit_of(faces, coords)
check(fit["shape"] is None and fit["dev"] > H.FIT_TOL,
      "cone rejected (deviation {0})".format(fit["dev"]))

# crease: a cylinder face and a flat face at 90 degrees are two patches
faces1, coords1 = grid_faces(cylinder((0.0, 0.0, 0.0), 0.01, 0.01), 4, 1,
                             0.0, math.pi / 2, 0.0, 0.01)
# flat ring face in z = 0 sharing the bottom edge of the cylinder
ring_nodes = sorted((n for n, p in coords1.items() if abs(p[2]) < 1e-12),
                    key=lambda n: math.atan2(coords1[n][1], coords1[n][0]))
coords2 = dict(coords1)
outer = []
nid = max(coords1) + 1
for n in ring_nodes:
    x, y, _z = coords1[n]
    coords2[nid] = (2 * x, 2 * y, 0.0)
    outer.append(nid)
    nid += 1
flat = []
for k in range(len(ring_nodes) - 1):
    ring = [ring_nodes[k], outer[k], outer[k + 1], ring_nodes[k + 1]]
    flat.append((frozenset(ring), ring))
groups, _n = H.patches(faces1 + flat, coords2)
check(len(groups) == 2, "cylinder and flat face at 90 degrees: 2 patches "
      "({0})".format(len(groups)))
out = H.recognise(faces1 + flat, coords2)
check(len(out) == 1 and out[0][0] == "CYLINDRE" and len(out[0][2]) == 4,
      "recognise: only the cylinder ({0})".format([o[0] for o in out]))

# #ASTER-RAND: override and NONE
spec = H.parse_boundaries(["Gat = CILINDER 0, 0, 0, 0, 0, 2, 10 mm",
                           "Bol = SPHERE 1, 2, 3, 0.5",
                           "Vlak = GEEN", "Fout = CILINDER 1, 2"])
check(spec.get("Gat") == ("CYLINDRE", [0.0, 0.0, 0.0, 0.0, 0.0, 2.0, 0.01]),
      "#ASTER-RAND cylinder with mm: {0}".format(spec.get("Gat")))
check(spec.get("Bol") == ("SPHERE", [1.0, 2.0, 3.0, 0.5]), "#ASTER-RAND sphere")
check(spec.get("Vlak") == ("NONE", []), "#ASTER-RAND GEEN")
check("Fout" not in spec, "#ASTER-RAND with too few numbers skipped")
keys = [k for k, _r in faces1]
out = H.recognise(faces1 + flat, coords2,
                  [("Gat", ("CYLINDRE", [0, 0, 0, 0, 0, 2.0, 0.01]), keys)])
check(len(out) == 1 and out[0][3] == "Gat" and out[0][1][5] == 1.0,
      "override: the selection with a unit axis")
out = H.recognise(faces1 + flat, coords2, [("Gat", ("NONE", []), keys)])
check(out == [], "override GEEN: no boundary following")
parsed = bridge_custom.parse(["#ASTER-RAND Gat = BOL 0, 0, 0, 1",
                              "#ASTER-BOUNDARY Hole = NONE"])
check(parsed["boundaries"] == ["Gat = BOL 0, 0, 0, 1", "Hole = NONE"],
      "bridge_custom: -RAND and -BOUNDARY")

# scope: node groups with more than one node, shells
md = {"node_groups": {"Knoop": ["N1"], "Rand": ["N1", "N2"]},
      "extra_node_groups": {"BRSY1": [1, 2, 3]},
      "elem_shapes": {1: "hex20", 2: "quad8"}}
text = ("load = AFFE_CHAR_MECA(DDL_IMPO=(_F(GROUP_NO='Knoop', DX=0.0),\n"
        "    _F(GROUP_NO=('Rand', 'BRSY1'), DY=0.0)))\n")
check(H.multi_node_groups(md, text) == ["BRSY1", "Rand"],
      "multi-node groups found: {0}".format(H.multi_node_groups(md, text)))
check(not H.check_scope(md, {}, text), "scope: quad8 shells -> ERROR")
md["elem_shapes"] = {1: "hex20"}
md["node_groups"] = {"Knoop": ["N1"]}
check(H.check_scope(md, {}, "DDL_IMPO=_F(GROUP_NO='Knoop', DX=0.0)"),
      "scope: solids and a one-node group are fine")
check(not H.check_scope(dict(md, contacts=[{"x": 1}]), {}),
      "scope: contact -> ERROR")

# wrap: valid Python with the loop, markers replaced
comm = ("DEBUT()\nmesh = LIRE_MAILLAGE(UNITE=20)\n"
        "# ---- BRIDGE_ADAPT_BEGIN ----\n"
        "model = AFFE_MODELE(MAILLAGE=mesh)\n"
        "res = THER_LINEAIRE(MODELE=model)\n"
        "# ---- BRIDGE_ADAPT_END ----\n"
        "aster_results_export.export_results(res)\nFIN()\n")
plan = {"target": 1.0, "max_loops": 5, "max_elements": 1000,
        "kind": "thermal", "solids": ["Plaat"], "skin": ["Warm"],
        "boundaries": [("BRRAND1", "CYLINDRE", [0, 0, 0, 0, 0, 1, 0.01]),
                       ("BRRAND2", "SPHERE", [1, 1, 1, 0.5])],
        "ignore_pyra": True, "scripts": "C:\\x\\Scripts",
        "refined_med": None}
new = H.wrap(comm, plan, {"elem_shapes": {1: "hex20"}})
ok = new is not None
try:
    compile(new, "study.comm", "exec")
except SyntaxError as e:
    ok = False
    print(e)
check(ok, "wrap: valid Python")
check(new is not None and "    res = THER_LINEAIRE(MODELE=model)" in new and
      "TYPE='CYLINDRE'" in new and "TYPE='SPHERE'" in new and
      "IGNORE_PYRA" in new and "PROJ_CHAMP" in new and
      "('res', 'res_flux')" in new,
      "wrap: indented body, boundaries, pyramids, projection")
check(H.wrap(comm.replace("BRIDGE_ADAPT_END", "X"), plan, {}) is None,
      "wrap: missing marker -> None")

print("{0} failure(s)".format(len(_FAILED)))
sys.exit(1 if _FAILED else 0)
