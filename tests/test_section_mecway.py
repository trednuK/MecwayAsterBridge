# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of Scripts/section_mecway.py (Python 2.7 and 3): plane and
# boundary of selected faces, quadratic faces, holes, the #ASTER-SECTIE line
# in the .liml text, and the check in bridge_from_liml._section_extras.
#
#   python tests/test_section_mecway.py

from __future__ import print_function

import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"
import section_mecway as smw  # noqa: E402
import bridge_from_liml  # noqa: E402

LOG = []
smw.log = LOG.append
bridge_from_liml.log = LOG.append


def check(name, cond):
    print(("OK   " if cond else "FOUT ") + name)
    if not cond:
        check.failed = True


check.failed = False


def area(loop):
    a = 0.0
    for i in range(len(loop)):
        x0, y0 = loop[i]
        x1, y1 = loop[(i + 1) % len(loop)]
        a += x0 * y1 - x1 * y0
    return 0.5 * a


def even_odd_area(loops):
    """Area of nested loops: the absolute areas with sign by depth."""
    return sum(abs(area(lp)) * (1 if _depth(lp, loops) % 2 == 0 else -1)
               for lp in loops)


def _inside(pt, loop):
    x, y = pt
    c = False
    for i in range(len(loop)):
        x0, y0 = loop[i]
        x1, y1 = loop[(i + 1) % len(loop)]
        if (y0 > y) != (y1 > y) and \
                x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def _depth(lp, loops):
    return sum(1 for other in loops if other is not lp and
               _inside(lp[0], other))


def grid_faces(nx, ny, w, h, z, skip=(), below=True):
    """quad4 faces of a grid in the plane z (element centres below)."""
    nid = {}

    def node(i, j):
        key = (i, j)
        if key not in nid:
            nid[key] = len(nid) + 1
        return nid[key]
    faces = []
    for i in range(nx):
        for j in range(ny):
            if (i, j) in skip:
                continue
            corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            nodes = [node(a, b) for a, b in corners]
            coords = [(a * w / nx, b * h / ny, z) for a, b in corners]
            cx = (i + 0.5) * w / nx
            cy = (j + 0.5) * h / ny
            faces.append({"eid": len(faces) + 1, "face": 1, "nodes": nodes,
                          "coords": coords,
                          "centre": (cx, cy, z - 0.01 if below else z + 0.01)})
    return faces


# --- rectangle of 2 x 2 quad4 faces at z = 0.2 ---------------------------
faces = grid_faces(2, 2, 0.1, 0.05, 0.2)
plane = smw.selection_plane(faces)
check("normal +z (outward from the elements)",
      max(abs(a - b) for a, b in zip(plane["normal"], (0, 0, 1))) < 1e-12)
check("offset 0.2", abs(plane["offset"] - 0.2) < 1e-12)
check("u = X, v = Y", smw.axis_name(plane["u"]) == "X" and
      smw.axis_name(plane["v"]) == "Y")
loops, heal = smw.boundary_loops(faces, plane)
check("one loop of 8 corner points", len(loops) == 1 and len(loops[0]) == 8)
check("area 0.005", abs(abs(area(loops[0])) - 0.005) < 1e-15)
# elements above the face: normal -z, mirrored view (u = -X)
plane2 = smw.selection_plane(grid_faces(2, 2, 0.1, 0.05, 0.2, below=False))
check("normal -z when the elements are above", plane2["normal"][2] < -0.999
      and smw.axis_name(plane2["u"]) == u"−X")

# --- hole: 3 x 3 grid without the centre face ------------------------------
faces = grid_faces(3, 3, 0.03, 0.03, 0.0, skip=[(1, 1)])
loops, heal = smw.boundary_loops(faces, smw.selection_plane(faces))
check("hole: two loops", len(loops) == 2)
check("hole: even-odd area 8e-4", abs(even_odd_area(loops) - 8e-4) < 1e-15)

# --- quadratic face (quad8, alternating corner/mid), curved edge ------------
r = 0.01
c45 = r * math.cos(math.radians(45.0))
# quarter disc between 0 and 90 degrees: corners (0,0), (r,0), (0,r) +
# a 4th corner on the arc at 45 deg; midside nodes on the arcs
corner = [(0.0, 0.0), (r, 0.0), (c45, c45), (0.0, r)]


def arc_pt(a):
    return (r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
mids = [(r / 2, 0.0), arc_pt(22.5), arc_pt(67.5), (0.0, r / 2)]
for order in ("alternating", "grouped"):
    if order == "alternating":
        pts = [corner[0], mids[0], corner[1], mids[1], corner[2], mids[2],
               corner[3], mids[3]]
    else:
        pts = corner + mids
    face = {"eid": 1, "face": 1, "nodes": list(range(1, 9)),
            "coords": [(x, y, 0.0) for x, y in pts],
            "centre": (0.004, 0.004, -0.001)}
    lp, _ = smw.boundary_loops([face], smw.selection_plane([face]))
    exact = math.pi * r * r / 4
    a = abs(area(lp[0]))
    check("quad8 {0}: 32 boundary points".format(order), len(lp[0]) == 32)
    # coarse on purpose (two 45 degree arcs): 0.23% too small
    check("quad8 {0}: area of the quarter disc within 0.3% ({1:.5f})"
          .format(order, a / exact), abs(a / exact - 1) < 3e-3)

# --- repairs: duplicate nodes and a T-joint ----------------------------------
def quad(eid, ids, pts):
    cx = sum(p[0] for p in pts) / 4.0
    cy = sum(p[1] for p in pts) / 4.0
    return {"eid": eid, "face": 1, "nodes": ids,
            "coords": [(x, y, 0.0) for x, y in pts], "centre": (cx, cy, -0.1)}
# two unit squares; the right one has its own nodes on the shared edge, 1e-5
# (relative 5e-6 of the size) away from the left one's
d = 1e-5
faces = [quad(1, [1, 2, 3, 4], [(0, 0), (1, 0), (1, 1), (0, 1)]),
         quad(2, [12, 5, 6, 13], [(1 + d, 0), (2, 0), (2, 1), (1 + d, 1)])]
loops, heal = smw.boundary_loops(faces, smw.selection_plane(faces))
check("duplicate nodes welded: one loop, area 2", len(loops) == 1 and
      abs(abs(area(loops[0])) - 2.0) < 1e-4 and heal["welded"] == 2)
# T-joint: a tall square on the left, two squares on the right; node (1, 1)
# of the right ones lies on the left one's edge
faces = [quad(1, [1, 2, 3, 4], [(0, 0), (1, 0), (1, 2), (0, 2)]),
         quad(2, [2, 5, 6, 7], [(1, 0), (2, 0), (2, 1), (1, 1)]),
         quad(3, [7, 6, 8, 3], [(1, 1), (2, 1), (2, 2), (1, 2)])]
loops, heal = smw.boundary_loops(faces, smw.selection_plane(faces))
check("T-joint split: one loop, area 4", len(loops) == 1 and
      abs(abs(area(loops[0])) - 4.0) < 1e-12 and heal["split"] == 1)
check("nothing to repair in a proper mesh", heal["welded"] == 0 and
      heal["gaps_closed"] == [])
# a real slit (two squares 0.1 apart) stays: two loops, no gap closed
faces = [quad(1, [1, 2, 3, 4], [(0, 0), (1, 0), (1, 1), (0, 1)]),
         quad(2, [5, 6, 7, 8], [(1.1, 0), (2.1, 0), (2.1, 1), (1.1, 1)])]
loops, heal = smw.boundary_loops(faces, smw.selection_plane(faces))
check("a real slit is kept", len(loops) == 2 and heal["gaps_closed"] == [])

# --- not planar -------------------------------------------------------------
faces = grid_faces(2, 1, 0.1, 0.05, 0.0)
faces[1]["coords"][1] = (0.1, 0.0, 0.001)
try:
    smw.selection_plane(faces)
    check("not planar -> ValueError", False)
except ValueError:
    check("not planar -> ValueError", True)
try:
    smw.selection_plane([])
    check("no faces -> ValueError", False)
except ValueError:
    check("no faces -> ValueError", True)

# --- the #ASTER-SECTIE line -------------------------------------------------
res = {"area": 1.8e-05, "i11_c": 1.35e-09, "i22_c": 5.4e-13,
       "j": 2.16e-12, "perimeter": 0.0136, "centroid": [0.0, 0.0],
       "phi_deg": 0.0, "loops": [[[-0.0015, -0.003], [0.0015, -0.003],
                                  [0.0015, 0.003], [-0.0015, 0.003]]],
       "aster": {"A": 1.8e-05, "IY": 1.35e-09, "IZ": 5.4e-13,
                 "JX": 2.16e-12, "AY": 1.2, "AZ": 1.2, "EY": 0.0,
                 "EZ": 0.0, "RY": 0.003, "RZ": 0.0015, "RT": 0.0015,
                 "JG": 1e-18, "IYR2": 0.0, "IZR2": 0.0}}
line = smw.aster_line(u"Plat 3x6", res)
check("line starts with '** ASTER-SECTIE Plat 3x6: A='",
      line.startswith(u"** ASTER-SECTIE Plat 3x6: A=1.8e-05, IY="))
py, pz = smw.recovery_point(res)
check("stress recovery point at a corner",
      abs(abs(py) - 0.0015) < 1e-12 and abs(abs(pz) - 0.003) < 1e-12)
values = dict(smw.general_section_values(res))
check("iyy = I11, izz = I22", values["iyy"] == 1.35e-09 and
      values["izz"] == 5.4e-13)

snippet = smw.aster_line_liml(line.replace(u"Plat 3x6", u"A&B"))
check("import .liml: one custom model definition, name escaped",
      snippet.count(u"<ccxmodeldefinition>") == 1 and
      u"** ASTER-SECTIE A&amp;B: A=" in snippet)

# The bridge reads every <ccxmodeldefinition> (Mecway keeps an imported one
# next to an existing one); the later line of a material wins.
import xml.etree.ElementTree as ET  # noqa: E402
TWO = (u'<liml version="34"><ccxmodeldefinition>** own line\n'
       u'** ASTER-SECTIE M: A=1, IY=1, IZ=1, JX=1, AY=1.1</ccxmodeldefinition>'
       u'<ccxmodeldefinition>** ASTER-SECTIE M: A=1, IY=1, IZ=1, JX=1, '
       u'AY=1.3</ccxmodeldefinition></liml>')
root = ET.fromstring(TWO.encode("utf-8"))
import bridge_custom  # noqa: E402
bridge_custom.log = LOG.append
texts = [el.text for tag in bridge_custom.CUSTOM_TAGS
         for el in root.findall(tag)]
extras = bridge_from_liml._section_extras(bridge_custom.parse(texts)["sections"])
check("two custom model definitions: both read, the later line wins",
      len(texts) == 2 and extras["M"]["AY"] == 1.3)

# --- read back by the bridge (bridge_custom + _section_extras) -------------
custom = bridge_custom.parse([u"** own line\n" + line])
extras = bridge_from_liml._section_extras(custom["sections"])
check("bridge reads the line back", extras.get(u"Plat 3x6", {}).get("AY")
      == 1.2 and extras[u"Plat 3x6"]["IY"] == 1.35e-09)
geom = bridge_from_liml._parse_geometric_props(
    __import__("xml.etree.ElementTree", fromlist=["x"]).fromstring(
        (u'<geometric type="UniformGeneralSection" area="1.8e-05 m\xb2" '
         u'iyy="1.35e-09 m⁴" izz="5.4e-13 m⁴" '
         u'torsionconstant="2.16e-12 m⁴" />').encode("utf-8")))
new_geom = bridge_from_liml._apply_section_extras(u"Plat 3x6", geom,
                                                  extras[u"Plat 3x6"])
cara = dict(zip(new_geom["cara"], new_geom["vale"]))
check("EY, EZ, RY, RZ, RT added; AY/AZ as shear_coefs",
      all(k in cara for k in ("EY", "EZ", "RY", "RZ", "RT")) and
      new_geom.get("shear_coefs") == (1.2, 1.2))
changed = dict(extras[u"Plat 3x6"], IY=2e-9)
same = bridge_from_liml._apply_section_extras(u"Plat 3x6", geom, changed)
check("changed section -> extras ignored (WARNING)",
      same is geom and any("WARNING" in m for m in LOG))
bad = bridge_from_liml._section_extras([u"X: A=1, IY=1, IZ=1, JX=1, Q=2",
                                        u"no colon"])
check("unknown key and missing name -> skipped (ERROR)", bad == {} and
      sum(1 for m in LOG if m.startswith("ERROR")) >= 2)

if check.failed:
    print("FOUT: test_section_mecway")
    sys.exit(1)
print("Alle controles OK")
