# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test (Python 2.7 and 3, also IronPython via TestFiles/Tools/
# run_ipy.ps1) of the ** SECTIE-VORM lines (bridge_custom) and of
# bridge_section_view: parser, stale check, frames, sweep as plain data, caps,
# offset, the text for the model copy in <solution>, and the stress from the
# section forces and from the kinematics against Mecway's own stressptu on 7
# beams.
#
#   python tests/test_bridge_section_view.py
#   powershell -ExecutionPolicy Bypass -File TestFiles/Tools/run_ipy.ps1
#       -Script tests/test_bridge_section_view.py

from __future__ import print_function

import io
import math
import os
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"
TMP = tempfile.mkdtemp(prefix="section_view_")
bridge_utils.CONFIG_BRIDGE["work_dir"] = TMP      # in memory only
bridge_utils.CONFIG_BRIDGE["active_analysis"] = "lin_static_3d"
import bridge_custom  # noqa: E402
import bridge_from_liml  # noqa: E402
import bridge_mesh  # noqa: E402
import bridge_results_liml  # noqa: E402
import bridge_section_view as sv  # noqa: E402

LOG = []
sv.log = LOG.append
bridge_custom.log = LOG.append


def check(name, cond):
    print(("OK   " if cond else "FOUT ") + name)
    check.count += 1
    if not cond:
        check.failed = True


check.failed = False
check.count = 0


def close(a, b, tol=1e-12):
    return (len(a) == len(b) and
            all(abs(x - y) <= tol for x, y in zip(a, b)))


def logged(text):
    return any(text in line for line in LOG)


# ==========================================
# bridge_custom: the lines
# ==========================================
ASTER_TEXT = u"\n".join([
    u"#ASTER verb = AFFE_CHAR_MECA(MODELE=model)",
    u"$ ASTER-excit verb",
    u"#ASTER-OPTIE newton_max_iter = 40",
    u"** ASTER-SECTIE Sect: A=8e-4, IY=1e-6, IZ=2e-7, JX=1e-8, AY=1.2",
    u"** an ordinary comment",
])
SHAPE_TEXT = u"\n".join([
    u"** SECTIE-VORM Sect: N=4, A=0.0008",
    u"** SECTIE-VORM Sect: P=0.02 0.01 -0.02 0.01",
    u"** SECTIE-VORM Sect: P=-0.02 -0.01 0.02 -0.01",
])
del LOG[:]
plain = bridge_custom.parse([ASTER_TEXT])
log_plain = list(LOG)
del LOG[:]
mixed = bridge_custom.parse([SHAPE_TEXT + u"\r\n" + ASTER_TEXT, SHAPE_TEXT])
check("custom: bodies in order, over the fields", mixed["section_shapes"] == [
    u"Sect: N=4, A=0.0008", u"Sect: P=0.02 0.01 -0.02 0.01",
    u"Sect: P=-0.02 -0.01 0.02 -0.01"] * 2)
check("custom: empty() has the key",
      bridge_custom.empty()["section_shapes"] == [])
same = dict((k, v) for k, v in mixed.items() if k != "section_shapes")
base = dict((k, v) for k, v in plain.items() if k != "section_shapes")
check("custom: #ASTER output unchanged by shape lines", same == base)
check("custom: existing section line still in sections",
      mixed["sections"] == plain["sections"] and len(plain["sections"]) == 1)
check("custom: no ERROR for shape lines",
      not [m for m in LOG if m.startswith("ERROR")])
check("custom: #ASTER summary unchanged",
      [m for m in LOG if m.startswith("INFO: #ASTER lines")] ==
      [m for m in log_plain if m.startswith("INFO: #ASTER lines")])
del LOG[:]
only = bridge_custom.parse([SHAPE_TEXT])
check("custom: only shape lines -> no #ASTER summary",
      not logged("#ASTER lines") and len(only["section_shapes"]) == 3)
del LOG[:]
out = bridge_custom.parse([u"# SECTIE-VORM X: N=3, A=1\n"
                           u"$ SECTIE-VORM X: N=3, A=1\n"
                           u"  **  SECTIE-VORM  Y: N=3, A=1\n"
                           u"** SECTIE-VORMX Z: N=3, A=1"])
check("custom: prefix ** only, leading spaces allowed",
      out["section_shapes"] == [u"Y: N=3, A=1"])
check("custom: other prefixes are no errors",
      not [m for m in LOG if m.startswith("ERROR")])
out = bridge_custom.parse([u"**ASTER-SECTIE-VORM X: N=3, A=1"])
check("custom: a near-#ASTER line stays reported as one",
      out["section_shapes"] == [] and logged("looks like an #ASTER line"))


# ==========================================
# parse_shapes
# ==========================================
def parse(*bodies):
    del LOG[:]
    return sv.parse_shapes(list(bodies))


shapes = parse(u"M: N=3 4, A=0.5",
               u"M: P=0 0 1 0 1 1",
               u"M: P=0.2 0.2 0.4 0.2",
               u"M: P=0.4 0.4 0.2 0.4")
check("parse: loops and area", shapes[u"M"]["area"] == 0.5 and
      shapes[u"M"]["loops"] == [[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)],
                                [(0.2, 0.2), (0.4, 0.2), (0.4, 0.4),
                                 (0.2, 0.4)]])
check("parse: nothing logged for good data", LOG == [])
good = (u"M: N=3, A=1", u"M: P=0 0 1 0 1 1")
shapes = parse(u"M: N=4, A=2", u"M: P=9 9 8 8 7 7 6 6", *good)
check("parse: newest N= wins", shapes[u"M"]["area"] == 1.0 and
      shapes[u"M"]["loops"] == [[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]])
shapes = parse(u"A: B: N=3, A=1", u"A: B: P=0 0 1 0 1 1")
check("parse: name split on the last colon", list(shapes) == [u"A: B"])
shapes = parse(u" M : N=3, A=1", u"M:P=0 0 1 0 1 1")
check("parse: name stripped", list(shapes) == [u"M"])
check("parse: nothing at all", parse() == {} and LOG == [])

for label, bodies in [
        ("P before N", (u"M: P=0 0 1 0 1 1",)),
        ("too few points", (u"M: N=4, A=1", u"M: P=0 0 1 0 1 1")),
        ("too many points", (u"M: N=3, A=1", u"M: P=0 0 1 0 1 1 2 2")),
        ("odd number of values", (u"M: N=3, A=1", u"M: P=0 0 1 0 1")),
        ("no P at all", (u"M: N=3, A=1",)),
        ("text in P", (u"M: N=3, A=1", u"M: P=0 0 1 x 1 1")),
        ("nan in P", (u"M: N=3, A=1", u"M: P=0 0 1 nan 1 1")),
        ("inf in P", (u"M: N=3, A=1", u"M: P=0 0 1 inf 1 1")),
        ("text in N", (u"M: N=x, A=1", u"M: P=0 0 1 0 1 1")),
        ("fraction in N", (u"M: N=3.5, A=1", u"M: P=0 0 1 0 1 1")),
        ("two points in a loop", (u"M: N=2, A=1", u"M: P=0 0 1 0")),
        ("no area", (u"M: N=3", u"M: P=0 0 1 0 1 1")),
        ("area 0", (u"M: N=3, A=0", u"M: P=0 0 1 0 1 1")),
        ("area nan", (u"M: N=3, A=nan", u"M: P=0 0 1 0 1 1")),
        ("comma list of the old plan", (u"M: N=3,3, A=1",
                                        u"M: P=0 0 1 0 1 1 0 0 1 0 1 1")),
        ("unknown key", (u"M: N=3, A=1, Q=2", u"M: P=0 0 1 0 1 1")),
        ("unknown line", (u"M: N=3, A=1", u"M: X=1", u"M: P=0 0 1 0 1 1")),
        ("loop collapses", (u"M: N=3, A=1", u"M: P=0 0 0 0 1 1"))]:
    shapes = parse(*bodies)
    check("parse: bad data skipped with a log line: " + label,
          shapes == {} and logged("SECTIE-VORM of material 'M' is skipped"))
shapes = parse(u"no colon here", u": N=3, A=1", u"")
check("parse: no material -> line skipped, logged",
      shapes == {} and len(LOG) == 3)
shapes = parse(u"X: N=4, A=1", u"Y: N=3, A=1", u"Y: P=0 0 1 0 1 1")
check("parse: only the bad material is skipped",
      list(shapes) == [u"Y"] and logged("'X'"))
shapes = parse(u"M: P=0 0 1 0 1 1", *good)
check("parse: a later N= replaces an earlier error",
      list(shapes) == [u"M"] and LOG == [])
shapes = parse(u"M: N=3, A=1", u"M: P=0 0 1 0 1 1", u"M: N=bad, A=1")
check("parse: a bad newest N= does not bring the old outline back",
      shapes == {} and len(LOG) == 1)
shapes = parse(u"M: N=5, A=1", u"M: P=0 0 1 0 1 0 1 1 0 0")
check("parse: repeated points dropped (rounded in the file)",
      shapes[u"M"]["loops"] == [[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]])


# ==========================================
# Small models
# ==========================================
# An asymmetric L: every wrong sign or swapped axis moves a point.
L_LOOP = [(-0.01, -0.02), (0.05, -0.02), (0.05, -0.01), (0.0, -0.01),
          (0.0, 0.07), (-0.01, 0.07)]
L_SHAPE = {"M": {"loops": [L_LOOP], "area": 1.3e-3}}
RECT = {"M": {"loops": [[(-0.02, -0.01), (0.02, -0.01), (0.02, 0.01),
                         (-0.02, 0.01)]], "area": 8e-4}}


def model(nodes, elements, orient=None, mod="POU_D_E", **extra):
    """model_data with the keys bridge_section_view reads."""
    md = {"mesh_nodes": nodes,
          "mesh_elements": elements,
          "elem_shapes": dict((e[0], e[1]) for e in elements),
          "elsets": {"B": "M"},
          "elset_modelisations": {"B": mod},
          "beam_orientations": orient or {},
          "materials": {"M": {"E": 2.0e11}}}
    md.update(extra)
    return md


def one_beam(direction, orient=None, **extra):
    return model({1: (0.0, 0.0, 0.0), 2: direction},
                 [(1, "line2", [1, 2], "B")],
                 {1: orient} if orient else None, **extra)


def build(md, shapes_=L_SHAPE, **kw):
    del LOG[:]
    return sv.build_view(md, shapes_, **kw)


def point(view, beam, end, v, w):
    """Position of section point (v, w) of a ring; the first match."""
    for xyz, origin in zip(view["xyz"], view["origin"]):
        if origin == (beam, end, v, w):
            return xyz
    return None


# ==========================================
# Frames
# ==========================================
for label, p2, orient in [
        ("default", (2.0, 0.5, 0.3), None),
        ("along Z", (0.0, 0.0, 3.0), None),
        ("vector", (1.0, 1.0, 0.0), {"vec": (0.0, 0.0, 1.0), "angle": 0.0}),
        ("vector and angle", (1.0, -2.0, 0.5),
         {"vec": (0.2, 1.0, 0.0), "angle": 0.7})]:
    p1 = (0.1, 0.2, 0.3)
    u, v, w = sv.beam_frame(p1, p2, orient)
    ref = bridge_mesh._mecway_v_axis(p1, p2, orient)
    n = math.sqrt(sum((p2[i] - p1[i]) ** 2 for i in range(3)))
    check("frame: U along the beam, V from _mecway_v_axis, W = U x V: " +
          label, close(v, ref) and
          close(u, [(p2[i] - p1[i]) / n for i in range(3)]) and
          close(w, (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2],
                    u[0] * v[1] - u[1] * v[0])) and
          abs(sum(a * b for a, b in zip(u, v))) < 1e-12)


# ==========================================
# Sweep: L section on known beams
# ==========================================
view = build(one_beam((2.0, 0.0, 0.0)))
n_pts = len(L_LOOP)
check("beam: line2 ends are k = 1 and 2",
      view["beams"][0]["element_nodes"] == (1, 2))
check("sweep: one closed ring per end, in outline order",
      view["origin"][:n_pts] == [(0, 0) + p for p in L_LOOP] and
      view["origin"][n_pts:2 * n_pts] == [(0, 1) + p for p in L_LOOP])
first_ring = view["nids"][:n_pts]
second_ring = view["nids"][n_pts:2 * n_pts]
check("sweep: every segment once, end 0 to end 1, closing the ring",
      sorted(e[2] for e in view["elements"][:n_pts]) == sorted(
          (first_ring[i - 1], first_ring[i], second_ring[i],
           second_ring[i - 1]) for i in range(n_pts)))
sides = [e for e in view["elements"] if e[0] <= 1 + n_pts]
check("sweep: one quad4 per outline segment",
      len(sides) == n_pts and all(e[1] == "quad4" for e in sides))
check("sweep: ids above the model, ascending from the first free id",
      view["nids"][0] == 3 and view["elements"][0][0] == 2 and
      view["nids"] == sorted(view["nids"]))
check("handedness: +X beam, V = +Y, W = +Z",
      close(point(view, 0, 0, 0.05, -0.02), (0.0, 0.05, -0.02)) and
      close(point(view, 0, 1, -0.01, 0.07), (2.0, -0.01, 0.07)))
view = build(one_beam((0.0, 0.0, 2.0)))
check("handedness: +Z beam, V = +Y, W = -X",
      close(point(view, 0, 1, 0.05, -0.02), (0.02, 0.05, 2.0)))
view = build(one_beam((2.0, 0.0, 0.0), {"vec": (0.0, 0.0, 1.0),
                                        "angle": math.radians(-90.0)}))
check("handedness: vector Z, angle -90 deg: V = +Y (bridge_mesh)",
      close(point(view, 0, 0, 0.05, -0.02), (0.0, 0.05, -0.02)))
view = build(one_beam((2.0, 0.0, 0.0), {"vec": (0.0, 0.0, 1.0),
                                        "angle": 0.0}))
check("handedness: vector Z: V = +Z, W = -Y",
      close(point(view, 0, 0, 0.05, -0.02), (0.0, 0.02, 0.05)))
view = build(one_beam((0.0, -2.0, 0.0)))
check("handedness: -Y beam, V = +X, W = +Z",
      close(point(view, 0, 0, 0.05, -0.02), (0.05, 0.0, -0.02)))


# ==========================================
# Displacement: torsion and rigid rotation
# ==========================================
view = build(one_beam((2.0, 0.0, 0.0)))
theta = 0.01
values = sv.shell_values(view, {1: (0.0, 0.0, 0.0), 2: (0.0, 0.0, 0.0)},
                         {1: (0.0, 0.0, 0.0), 2: (theta, 0.0, 0.0)},
                         one_beam((2.0, 0.0, 0.0)))
where = view["origin"].index((0, 1, 0.05, -0.02))
check("torsion: theta x r = (0, -t w, t v) at end 1",
      close((values["displx"][where], values["disply"][where],
             values["displz"][where]),
            (0.0, theta * 0.02, theta * 0.05)))
where = view["origin"].index((0, 0, 0.05, -0.02))
check("torsion: nothing at the fixed end",
      close((values["disply"][where], values["displz"][where]), (0.0, 0.0)))
check("displmag is the length",
      all(abs(m - math.sqrt(x * x + y * y + z * z)) < 1e-15 for m, x, y, z in
          zip(values["displmag"], values["displx"], values["disply"],
              values["displz"])))
check("values per shell node, in order of nids",
      all(len(values[k]) == len(view["nids"]) for k in
          ("displx", "disply", "displz", "displmag", "sectionsigma")) and
      values["nids"] == view["nids"])
check("torsion: no longitudinal stress",
      max(abs(s) for s in values["sectionsigma"]) < 1e-3)
values = sv.shell_values(
    view, {1: (0.0, 0.0, 0.0), 2: (0.0, 0.2, 0.0)},
    {1: (0.0, 0.0, 0.1), 2: (0.0, 0.0, 0.1)}, one_beam((2.0, 0.0, 0.0)))
check("rigid rotation: no stress",
      max(abs(s) for s in values["sectionsigma"]) < 1e-1)


# ==========================================
# Stress by hand: axial and bending, offset
# ==========================================
beam = view["beams"][0]
E = 2.0e11
zero = (0.0, 0.0, 0.0)
check("stress: axial E strain",
      abs(sv.stress_from_kinematics(E, beam, zero, zero, (0.002, 0.0, 0.0),
                                    zero, 0.0, 0.03, 0.01) - 2.0e8) < 1e-3)
# Constant curvature about W: v'' = k with theta.W = k s, v = k s^2 / 2.
k = 0.004
d2 = (0.0, 0.5 * k * 4.0, 0.0)
t2 = (0.0, 0.0, 2.0 * k)
for s in (0.0, 2.0):
    check("stress: bending in the V direction, fibre at +v in compression",
          abs(sv.stress_from_kinematics(E, beam, zero, zero, d2, t2, s, 0.03,
                                        0.5) - (-E * k * 0.03)) < 1e-2)
# Constant curvature in the W direction: w' = -theta.V
d2 = (0.0, 0.0, 0.5 * k * 4.0)
t2 = (0.0, -2.0 * k, 0.0)
check("stress: bending in the W direction",
      abs(sv.stress_from_kinematics(E, beam, zero, zero, d2, t2, 2.0, 0.5,
                                    0.03) - (-E * k * 0.03)) < 1e-2)
section = {"A": 8e-4, "iyy": 2.667e-8, "izz": 1.067e-7}
check("forces: N / A", abs(sv.stress_from_forces(
    100.0, 0.0, 0.0, section, 0.3, 0.4) - 125000.0) < 1e-6)
check("forces: +Mv in tension on the +w side", sv.stress_from_forces(
    0.0, 1.0, 0.0, section, 0.0, 0.01) > 0.0)
check("forces: +Mw in compression on the +v side", sv.stress_from_forces(
    0.0, 0.0, 1.0, section, 0.02, 0.0) < 0.0)
# Cantilever with a line pressure, 1 element, root end: Mecway 35 gave
# N 100, Mv 416.667, Mw -250 and stressptu 203215827.3 Pa at (0.02, 0.01)
check("forces: measured line load, one element",
      abs(sv.stress_from_forces(100.0, 1250.0 / 3.0, -250.0, section, 0.02,
                                0.01) - 203215827.3) < 0.1)

off = (0.0, 0.0, 0.1)
md = one_beam((2.0, 0.0, 0.0),
              element_offsets=[{"selection": "S", "uvw": None,
                                "xyz": (0.0, 0.0, 0.0)},
                               {"selection": "S", "uvw": None, "xyz": off},
                               {"selection": "S", "uvw": None,
                                "xyz": (9.0, 9.0, 9.0)}],
              element_selections={"S": [1]})
view = build(md)
check("offset: the first non-zero one applies, as bridge_offset",
      view["beams"][0]["offset"] == off)
check("offset: the ring centre shifts",
      close(point(view, 0, 1, 0.05, -0.02), (2.0, 0.05, 0.08)))
theta2 = (0.0, 0.01, 0.0)
values = sv.shell_values(view, {1: zero, 2: zero}, {1: zero, 2: theta2}, md)
where = view["origin"].index((0, 1, 0.05, -0.02))
check("offset: displacement theta x (r + offset)",
      close((values["displx"][where], values["disply"][where],
             values["displz"][where]),
            (0.01 * (0.1 - 0.02), 0.0, 0.0)))
got = values["sectionsigma"][where]
plain_beam = dict(view["beams"][0], offset=zero)
check("offset: stress from the shifted element ends",
      abs(got - sv.stress_from_kinematics(
          E, plain_beam, zero, zero, (0.01 * 0.1, 0.0, 0.0), theta2, 2.0,
          0.05, -0.02)) < 1e-3 and abs(got) > 1.0)
md["elem_shapes"][1] = "line3"
md["mesh_elements"] = [(1, "line3", [1, 2, 2], "B")]
check("offset: not on a line3, as bridge_offset", sv.beam_offsets(md) == {})


# ==========================================
# Caps
# ==========================================
def even_odd_inside(loops, v, w):
    inside = False
    for loop in loops:
        for i in range(len(loop)):
            a, b = loop[i - 1], loop[i]
            if (a[1] > w) != (b[1] > w) and \
                    v < a[0] + (b[0] - a[0]) * (w - a[1]) / (b[1] - a[1]):
                inside = not inside
    return inside


def in_piece(piece, v, w):
    n = len(piece)
    return all((piece[(i + 1) % n][0] - piece[i][0]) * (w - piece[i][1]) -
               (piece[(i + 1) % n][1] - piece[i][1]) * (v - piece[i][0]) > 0.0
               for i in range(n))


def cap_case(label, loops, area):
    pieces = sv.cap_pieces(loops)
    total = sum(sv.polygon_area(p) for p in pieces)
    check("cap area equals the even-odd area: " + label,
          abs(total - area) < 1e-12 * max(area, 1.0))
    check("cap pieces anticlockwise, 3 or 4 points: " + label,
          all(sv.polygon_area(p) > 0.0 and len(p) in (3, 4) for p in pieces))
    # 37 x 41: no grid point lies on a level or an edge of these loops
    pts = [p for loop in loops for p in loop]
    v0 = min(p[0] for p in pts)
    w0 = min(p[1] for p in pts)
    dv = (max(p[0] for p in pts) - v0) / 37.0
    dw = (max(p[1] for p in pts) - w0) / 41.0
    wrong = 0
    for i in range(37):
        for j in range(41):
            v, w = v0 + (i + 0.5) * dv * 0.9973, w0 + (j + 0.5) * dw * 0.9971
            hit = len([p for p in pieces if in_piece(p, v, w)])
            if hit != (1 if even_odd_inside(loops, v, w) else 0):
                wrong += 1
    check("cap covers the even-odd interior once: " + label, wrong == 0)


cap_case("L", [L_LOOP], abs(sv.polygon_area(L_LOOP)))
outer = [(0.0, 0.0), (10.0, 0.0), (10.0, 6.0), (0.0, 6.0)]
hole = [(2.0, 2.0), (2.0, 4.0), (5.0, 4.0), (5.0, 2.0)]     # clockwise
cap_case("rectangle with a hole", [outer, hole], 60.0 - 6.0)
notched = [(0.0, 0.0), (10.0, 0.0), (10.0, 4.0), (8.0, 4.0), (8.0, 6.0),
           (0.0, 6.0)]
cap_case("hole edge on a W level of the outer loop", [notched, hole],
         56.0 - 6.0)
diamond = [(4.0, 1.0), (6.0, 2.0), (4.0, 4.0), (2.0, 2.0)]
cap_case("hole vertices on the levels", [notched, diamond],
         56.0 - abs(sv.polygon_area(diamond)))
touch = [(3.0, 0.0), (5.0, 2.0), (3.0, 4.0), (1.0, 2.0)]
cap_case("hole vertex touching the outer loop", [notched, touch],
         56.0 - 8.0)
two = [outer, [(1.0, 1.0), (3.0, 1.0), (3.0, 5.0), (1.0, 5.0)],
       [(6.0, 1.0), (8.0, 1.0), (8.0, 5.0), (6.0, 5.0)]]
cap_case("two holes side by side", two, 60.0 - 8.0 - 8.0)

pieces = sv.cap_pieces([[(0.0, -1.0), (1.0, 0.0), (0.0, 1.0), (-1.0, 0.0)]])
check("degenerate side: diamond gives two tri3 pieces",
      sorted(len(p) for p in pieces) == [3, 3])
pieces = sv.cap_pieces([[(0.0, 0.0), (2.0, 0.0), (1.0, 3.0)]])
check("degenerate side: triangle gives one tri3 piece",
      len(pieces) == 1 and len(pieces[0]) == 3 and
      abs(sv.polygon_area(pieces[0]) - 3.0) < 1e-12)
check("zero-area pieces dropped: a flat loop gives nothing",
      sv.cap_pieces([[(0.0, 0.0), (0.0, 1.0), (0.0, 2.0)]]) == [] and
      sv.cap_pieces([[(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)]]) == [])
view = build(one_beam((2.0, 0.0, 0.0)), {"M": {"loops": [
    [(0.0, -1.0), (1.0, 0.0), (0.0, 1.0), (-1.0, 0.0)]], "area": 2.0}})
check("view: tri3 in the cap, two caps", view["tris"] == 4 and
      view["quads"] == 4 and
      all(e[1] == "tri3" for e in view["elements"][4:]))

nodes = {1: (0.0, 0.0, 0.0), 2: (1.0, 0.0, 0.0), 3: (2.0, 0.0, 0.0),
         4: (2.0, 1.0, 0.0)}
elements = [(1, "line2", [1, 2], "B"), (2, "line2", [2, 3], "B"),
            (3, "line2", [3, 4], "B")]
view = build(model(nodes, elements), RECT)
check("caps at free ends only: a chain of 3 has 2",
      len(view["elements"]) == 3 * 4 + 2)
ends = [view["elements"][4], view["elements"][-1]]      # after their sides
pos = dict(zip(view["nids"], view["xyz"]))
check("caps: all nodes in the plane of the beam end",
      all(pos[n][0] == 0.0 for n in ends[0][2]) and
      all(pos[n][1] == 1.0 for n in ends[1][2]))


def normal(nids):
    a, b, c = [pos[n] for n in nids[:3]]
    e = [b[i] - a[i] for i in range(3)]
    f = [c[i] - a[i] for i in range(3)]
    return (e[1] * f[2] - e[2] * f[1], e[2] * f[0] - e[0] * f[2],
            e[0] * f[1] - e[1] * f[0])


check("caps: normal out of the beam",
      normal(ends[0][2])[0] < 0.0 and normal(ends[1][2])[1] > 0.0)
closed = model({1: (0.0, 0.0, 0.0), 2: (1.0, 0.0, 0.0), 3: (0.0, 1.0, 0.0)},
               [(1, "line2", [1, 2], "B"), (2, "line2", [2, 3], "B"),
                (3, "line2", [3, 1], "B")])
view = build(closed, RECT)
check("no cap on a closed loop of beams", len(view["elements"]) == 12)
view = build(model(nodes, elements[:2] + [(3, "line2", [3, 4], "O")],
                   elsets={"B": "M", "O": "Other"},
                   elset_modelisations={"B": "POU_D_E", "O": "POU_D_E"}),
             RECT)
check("cap where the next beam is not drawn",
      len(view["elements"]) == 2 * 4 + 2 and
      view["skipped"]["no_shape"] == 1 and logged("1 beams without"))


# ==========================================
# Elements: trusses, line3, limits
# ==========================================
md = model({1: (0.0, 0.0, 0.0), 2: (1.0, 0.0, 0.0), 3: (2.0, 0.0, 0.0)},
           [(1, "line2", [1, 2], "B"), (2, "line2", [2, 3], "T"),
            (3, "line2", [2, 3], "C"), (4, "quad4", [1, 2, 3, 3], "B")],
           elsets={"B": "M", "T": "M", "C": "M"},
           elset_modelisations={"B": "POU_D_T", "T": "BARRE", "C": "CABLE"})
view = build(md, RECT)
check("beams only: no truss, cable or shell",
      [b["eid"] for b in view["beams"]] == [1] and
      view["skipped"]["no_shape"] == 0)
check("truss on a node does not count for the free end",
      len(view["elements"]) == 4 + 2)

# A bent line3: c0 at the origin, midside out of the chord, c1 on +X
md = model({1: (0.0, 0.0, 0.0), 2: (1.0, 0.3, 0.0), 3: (2.0, 0.0, 0.0)},
           [(1, "line3", [1, 2, 3], "B")])
view = build(md, RECT)
beam = view["beams"][0]
check("line3: corners c0 and c1", beam["nodes"] == (1, 3))
check("line3: ends are k = 1 and 3 of <elem nodes>",
      beam["element_nodes"] == (1, 3))
check("line3: frame and length of the chord",
      close(beam["frame"][0], (1.0, 0.0, 0.0)) and beam["length"] == 2.0)
check("line3: one segment between the corners",
      len(view["elements"]) == 4 + 2 and
      close(point(view, 0, 1, 0.02, 0.01), (2.0, 0.02, 0.01)))
values = sv.shell_values(view, {1: zero, 3: (0.001, 0.0, 0.0)},
                         {1: zero, 3: zero}, md)
check("line3: results from the corners, not from the midside",
      values is not None and
      abs(values["sectionsigma"][0] - 2.0e11 * 0.0005) < 1e-3)

md = model({1: (0.0, 0.0, 0.0), 2: (0.0, 0.0, 0.0), 3: (1.0, 0.0, 0.0)},
           [(1, "line2", [1, 2], "B"), (2, "line2", [2, 3], "B"),
            (3, "line2", [3, 99], "B"), (4, "line2", [3], "B")])
view = build(md, RECT)
check("zero length, unknown node, too few nodes: skipped",
      [b["eid"] for b in view["beams"]] == [2] and
      view["skipped"]["invalid"] == 3)
view = build(model({1: (0.0, 0.0, 0.0), 2: (1.0, 0.0, 0.0)},
                   [(1, "line2", [1, 2], "Other")]), RECT)
check("nothing to draw -> None, logged", view is None and
      logged("no beam to draw"))
check("limit of 200 000 quads", sv.MAX_QUADS == 200000)
md = one_beam((2.0, 0.0, 0.0))
check("at the limit: built", build(md, RECT, max_quads=4) is not None)
check("above the limit: refused with the count",
      build(md, RECT, max_quads=3) is None and
      logged("ERROR: Section view: 4 quads") and logged("limit is 3"))
del LOG[:]
md = one_beam((2.0, 0.0, 0.0), elsets={"B": "M"})
view = build(md, RECT)
check("no result on a beam end -> None",
      sv.shell_values(view, {1: zero}, {1: zero, 2: zero}, md) is None and
      logged("ERROR: Section view: no result"))
check("None from node_value counts as no result, also in a component",
      sv.shell_values(view, {1: zero, 2: None}, {1: zero, 2: zero},
                      md) is None and
      sv.shell_values(view, {1: zero, 2: zero},
                      {1: zero, 2: (0.0, None, 0.0)}, md) is None)
del md["materials"]["M"]
values = sv.shell_values(view, {1: zero, 2: zero}, {1: zero, 2: zero}, md)
check("no E -> displacement only, logged",
      "sectionsigma" not in values and "displx" in values and
      "stress_routes" not in values and logged("no E for"))
md = model({5: (0.0, 0.0, 0.0), 9: (1.0, 0.0, 0.0)},
           [(70, "line2", [5, 9], "B"), (71, "tet4", [5, 9, 5, 9], "Doorsnede")])
view = build(md, RECT)
check("ids above the highest in the model, not next to the first",
      view["nids"][0] == 10 and view["elements"][0][0] == 72)
check("a component of the same name in the model stays apart",
      view["elset"] == "Doorsnede_1")


# ==========================================
# Stale check
# ==========================================
def geometric(area, kind=sv.GENERAL_SECTION):
    return {"geom_type": kind, "cara": ("A", "IY", "IZ", "JX", "EY"),
            "vale": (area, 1e-6, 1e-6, 1e-6, 0.0)}


def current(area, kind=sv.GENERAL_SECTION, name="M"):
    del LOG[:]
    return sv.current_shapes({"M": {"loops": [], "area": 8e-4}},
                             {"mat_geometrics": {name: geometric(area, kind)}
                              })


check("stale: same area counts", list(current(8e-4)) == ["M"] and LOG == [])
check("stale: within the tolerance of _SECTION_MATCH_TOL",
      list(current(8e-4 * (1.0 + 0.5e-6))) == ["M"])
check("stale: outside the tolerance is ignored, logged",
      current(8e-4 * (1.0 + 2e-6)) == {} and
      logged("the section was changed"))
check("stale: another section type is ignored",
      current(8e-4, "RectBar") == {} and logged("no material with a general"))
check("stale: a renamed material is ignored",
      current(8e-4, name="Other") == {} and
      logged("no material with a general"))
check("stale: %.10g of the writer stays within the tolerance",
      list(sv.current_shapes(
          {"M": {"loops": [], "area": float("%.10g" % 1.23456789012345e-3)}},
          {"mat_geometrics": {"M": geometric(1.23456789012345e-3)}})) == ["M"])


# ==========================================
# The measured chain: real .liml, real extraction, Mecway's stressptu
# ==========================================
# The chain of 7 beams in +X, inclined, +Z, -Y, -X, -Z and inclined
# directions, with default orientation, V vector + angle and an <orientation>
# card, solved by Mecway 35.0.9802 (500, -100, 50 N on the tip). Section
# rectangle 40 x 20 mm: the recovery point (pointy, pointz) = (0.02, 0.01) is
# a corner of the outline.
CHAIN = u"""<liml version="35">
  <analysis type="S30" />
  <node nid="1" x="0.0" y="0.0" z="0.0" />
  <node nid="2" x="1.0" y="0.0" z="0.0" />
  <node nid="3" x="1.6" y="0.5" z="0.3" />
  <node nid="4" x="1.6" y="0.5" z="1.3" />
  <node nid="5" x="1.6" y="-0.5" z="1.3" />
  <node nid="6" x="0.6" y="-0.5" z="1.3" />
  <node nid="7" x="0.6" y="-0.5" z="0.3" />
  <node nid="8" x="0.2" y="-0.9" z="-0.1" />
  <elset name="Beam" colorrgb="DADADA" material="Sect">
    <elem eid="1" shape="line2" nodes="1 2" />
    <elem eid="2" shape="line2" nodes="2 3" orientationvz="1" angle="30 \xb0" />
    <elem eid="3" shape="line2" nodes="3 4" />
    <elem eid="4" shape="line2" nodes="4 5" />
    <elem eid="5" shape="line2" nodes="5 6" orientationvx="0.2" orientationvy="1" />
    <elem eid="6" shape="line2" nodes="6 7" />
    <elem eid="7" shape="line2" nodes="7 8" />
  </elset>
  <mat name="Sect">
    <geometric type="UniformGeneralSection" area="0.0008 m\xb2" iyy="2.667e-08 m⁴" izz="1.067e-07 m⁴" torsionconstant="7.3e-08 m⁴" perimeter="0.12 m" pointy="0.02 m" pointz="0.01 m" />
    <mechanical type="Isotropic" youngsmodulus="210000000000 Pa" poissonratio="0.3" />
  </mat>
  <nodeselection name="Clamp">
    <node nid="1" />
  </nodeselection>
  <nodeselection name="Tip"><node nid="8" /></nodeselection>
  <elementselection name="Card"><element eid="6" /></elementselection>
  <fixed selection="Clamp" />
  <force selection="Tip"><x>500 N</x><y>-100 N</y><z>50 N</z></force>
  <orientation selection="Card"><ux>0</ux><uy>0</uy><uz>0</uz><vx>1</vx><vy>0.5</vy><vz>0</vz><angleu>-20 \xb0</angleu></orientation>
  <ccxmodeldefinition>** SECTIE-VORM Sect: N=4, A=0.0008
** SECTIE-VORM Sect: P=-0.02 -0.01 0.02 -0.01 0.02 0.01 -0.02 0.01</ccxmodeldefinition>
</liml>
"""
# {node: (dx, dy, dz, rx, ry, rz)} solved by Mecway 35 (solution.node_value)
MEASURED_DOFS = {
    1: (0.0, 0.0, 0.0,
        0.0, -0.0, 0.0),
    2: (2.9761904761901523e-06, 0.01033903095755111, 0.003868564048270168,
        -0.009328114807430293, -0.006249218847135576, 0.02142187709191771),
    3: (-0.03613604837188648, 0.04730652270053657, 0.01453852603998464,
        0.0038063392789621474, -0.03822017892177527, 0.10567061478188726),
    4: (-0.1008410119335307, 0.04669858868182288, 0.014538823659032255,
        -0.0033342864183483548, -0.10606884069588435, 0.24813636820661963),
    5: (0.16232042284456197, 0.04669799344372763, 0.03513285737091602,
        -0.036365871756002546, -0.2129181557640259, 0.2744674254655462),
    6: (0.16232339903503815, -0.23461253164844104, -0.235516177271138,
        -0.06350220574181686, -0.3298678227694989, 0.2874098095419795),
    7: (0.5260053182928492, -0.3221112643385258, -0.23551587965209037,
        -0.1041246967059356, -0.3867779072885719, 0.32811431052048373),
    8: (0.8144365948028791, -0.4955007802040357, -0.3505557845278878,
        -0.10226881212118429, -0.3923441698250095, 0.33182468847217084),
}
# (N, Mv, Mw) at (end 0, end 1) per element: tensileforce, bendingmomv,
# bendingmomw of the same solve, element values
MEASURED_FORCES = {
    1: ((499.9999999999456, -59.99999999657591,
         429.9999999978862),
        (499.9999999999456, -9.999999997728537,
         529.999999999314)),
    2: ((316.7355814720504, 429.8164949860493,
         -279.94118373480455),
        (316.7355814720504, 745.8964537722404,
         -396.6393399096396)),
    3: ((49.99999999953434, -129.99999999857891,
         109.99999999904978),
        (49.99999999953434, -629.9999999979266,
         210.00000000022243)),
    4: ((100.00000000186265, -210.00000000022294,
         840.0000000004438),
        (100.00000000186265, -160.0000000009768,
         340.0000000010914)),
    5: ((-499.9999999962747, -629.9999999979264,
         -340.00000000109685),
        (-499.9999999962747, -679.9999999971787,
         -240.00000000018554)),
    6: ((-50.0, -603.79058524117,
         351.33592069500264),
        (-50.0, -171.95981209112415,
         80.18617727296805)),
    7: ((-259.8076211595908, 84.85281374237911,
         293.9387691344964),
        (-259.8076211595908, -1.2732925824820995e-11,
         -1.4551915228366852e-11)),
}
# stressptu of a second solve of the same model, with the recovery point at
# (-0.015, 0.03); its forces differ from these only in the last digits
MEASURED_OTHER_POINT = {
    1: (-6416704.132069841, 63884372.33724337),
    2: (444524610.24285024, 783664569.2112592),
    3: (-130705303.507633, -679076892.9530865),
    4: (-118007374.97159041, -132054939.55161019),
    5: (-757083980.582129, -799268843.3683425),
    6: (-629850831.8531836, -182220451.30305287),
    7: (136444951.21200815, -324759.52646585694),
}
# Mecway's stressptu at (end 0, end 1) per element, Pa
MEASURED_STRESS = {
    1: (-102472000.40841399, -102468486.32166433),
    2: (214029534.23736358, 354418773.0222494),
    3: (-69299963.7119441, -275520671.5967233),
    4: (-236065954.10653377, -123597585.28659238),
    5: (-173115388.09131607, -210607187.0896214),
    6: (-292310575.7915017, -79569581.22308187),
    7: (-23605232.970041484, -324759.5264515351),
}


def chain_model(text, name="chain.liml"):
    """model_data of the text, through the real reader."""
    path = os.path.join(TMP, name)
    f = io.open(path, "w", encoding="utf-8", newline="")
    try:
        f.write(text)
    finally:
        f.close()
    return bridge_from_liml.extract_aster_data_from_liml(path)


del LOG[:]
md = chain_model(CHAIN)
check("chain: the reader gives a model", md is not None and
      len(md["mesh_elements"]) == 7)
bodies = md["aster_custom"]["section_shapes"]
check("chain: outline lines read from the .liml, not as #ASTER lines",
      len(bodies) == 2 and md["aster_custom"]["sections"] == [] and
      not [m for m in LOG if m.startswith("ERROR")])
shapes = sv.current_shapes(sv.parse_shapes(bodies), md)
check("chain: shape matches the material", list(shapes) == ["Sect"])
check("chain: orientation card in beam_orientations",
      close(md["beam_orientations"][6]["vec"], (1.0, 0.5, 0.0)))
view = build(md, shapes)
check("chain: 7 beams, 2 free ends", len(view["beams"]) == 7 and
      len(view["elements"]) == 7 * 4 + 2 and view["quads"] == 30 and
      view["tris"] == 0)
displacements = dict((n, v[:3]) for n, v in MEASURED_DOFS.items())
rotations = dict((n, v[3:]) for n, v in MEASURED_DOFS.items())
values = sv.shell_values(view, displacements, rotations, md)
worst = 0.0
for index, beam in enumerate(view["beams"]):
    for end in (0, 1):
        where = view["origin"].index((index, end, 0.02, 0.01))
        ref = MEASURED_STRESS[beam["eid"]][end]
        worst = max(worst, abs(values["sectionsigma"][where] - ref))
check("chain: kinematics, 14 element ends against Mecway's stressptu, "
      "worst %.3g Pa" % worst, worst < 1e-3)
check("chain: without forces the kinematic route is used",
      values["stress_routes"] == {"forces": 0, "kinematics": 7})
kinematic = values["sectionsigma"]
values = sv.shell_values(view, displacements, rotations, md, MEASURED_FORCES)
check("chain: with forces the force route is used",
      values["stress_routes"] == {"forces": 7, "kinematics": 0})
worst = 0.0
for index, beam in enumerate(view["beams"]):
    for end in (0, 1):
        where = view["origin"].index((index, end, 0.02, 0.01))
        ref = MEASURED_STRESS[beam["eid"]][end]
        worst = max(worst, abs(values["sectionsigma"][where] - ref))
check("chain: forces, 14 element ends against Mecway's stressptu, "
      "worst %.3g Pa" % worst, worst < 1e-3)
gap = max(abs(a - b) for a, b in zip(values["sectionsigma"], kinematic))
check("chain: the two routes agree on every shell node, gap %.3g Pa" % gap,
      gap < 1e-3)
section = sv.section_values(md, "Sect")
check("chain: section values from the material",
      close((section["A"], section["iyy"], section["izz"]),
            (8e-4, 2.667e-8, 1.067e-7), 1e-20))
worst = 0.0
for eid, ends in MEASURED_FORCES.items():
    for end in (0, 1):
        got = sv.stress_from_forces(ends[end][0], ends[end][1], ends[end][2],
                                    section, -0.015, 0.03)
        worst = max(worst, abs(got - MEASURED_OTHER_POINT[eid][end]))
check("chain: forces at a second recovery point (-0.015, 0.03), worst %.3g "
      "Pa" % worst, worst < 0.01)
partial = dict(MEASURED_FORCES)
partial[3] = (partial[3][0], (None, 0.0, 0.0))
del partial[5]
values = sv.shell_values(view, displacements, rotations, md, partial)
gap = max(abs(a - b) for a, b in zip(values["sectionsigma"], kinematic))
check("chain: beams without complete forces fall back, per beam",
      values["stress_routes"] == {"forces": 5, "kinematics": 2} and
      gap < 1e-3)
index = [b["eid"] for b in view["beams"]].index(1)
where = view["origin"].index((index, 0, 0.02, 0.01))
check("chain: clamped end moves nothing",
      values["displmag"][where] == 0.0)


# ==========================================
# Plain data per beam (also for temporary elements through the API)
# ==========================================
def plain(value):
    """True for nested dict/list/tuple of numbers and strings without
    markup: nothing of the file format in the data."""
    if isinstance(value, dict):
        return all(plain(k) and plain(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return all(plain(v) for v in value)
    if isinstance(value, (int, float)):
        return True
    return "<" not in value and ">" not in value


check("data: no XML in the view", plain(view))
check("data: one part per beam, in beam order",
      [p["eid"] for p in view["parts"]] == [b["eid"] for b in view["beams"]])
first = max(md["mesh_nodes"]) + 1
check("data: shell ids contiguous from max(model node id) + 1",
      view["nids"] == list(range(first, first + len(view["nids"]))))
check("data: parts hold every node once, with its coordinates",
      [n for p in view["parts"] for n in p["nodes"]] ==
      list(zip(view["nids"], view["xyz"])))
check("data: parts hold every element once",
      [e for p in view["parts"] for e in p["elements"]] == view["elements"])
check("data: elements use nodes of their own part only",
      all(set(n for e in p["elements"] for n in e[2]) <=
          set(n[0] for n in p["nodes"]) for p in view["parts"]))
check("data: shapes for the API", set(
    e[1] for e in view["elements"]) == set(["quad4"]))
gap_model = model({5: (0.0, 0.0, 0.0), 9: (1.0, 0.0, 0.0)},
                  [(70, "line2", [5, 9], "B")])
gap_view = build(gap_model, RECT)
check("data: contiguous also when the model ids have gaps",
      gap_view["nids"] == list(range(10, 10 + 16)))


# ==========================================
# Text for the model copy in <solution>
# ==========================================
def split_copy(text, nl):
    """(head, lines of the model copy) as bridge_results_liml splits it."""
    head = text[:text.index(u"</liml>")]
    return head, bridge_results_liml._solution_copy(head, nl, None)


def spliced(head, lines, nl):
    """The file as splice_results would make it, with a dummy <results>."""
    return nl.join([head.rstrip(), u"  <solution>"] + lines +
                   [u'    <results precision="double" />', u"  </solution>",
                    u"</liml>", u""])


for label, nl in (("LF", u"\n"), ("CRLF", u"\r\n")):
    text = CHAIN.replace(u"\n", nl)
    head, copy_lines = split_copy(text, nl)
    new = sv.insert_into_copy(copy_lines, view)
    inserted = sv.solution_lines(view)
    at = new.index(inserted[0])
    check("copy lines unchanged and in order: " + label,
          new[:at] + new[at + len(inserted):] == copy_lines)
    check("inserted after the last top-level <node>: " + label,
          new[at - 1].startswith(u'    <node nid="8"') and
          new[at + len(inserted)].startswith(u"    <elset"))
    whole = spliced(head, new, nl)
    check("model part byte-identical: " + label,
          whole.startswith(head.rstrip()) and
          text.startswith(head.rstrip()))
    root = ET.fromstring(whole.encode("utf-8"))
    solution = root.find("solution")
    check("parsed back: model part without shells: " + label,
          len(root.findall("node")) == 8 and
          [e.get("name") for e in root.findall("elset")] == ["Beam"])
    check("parsed back: solution with model and shells: " + label,
          len(solution.findall("node")) == 8 + len(view["nids"]) and
          [e.get("name") for e in solution.findall("elset")] ==
          ["Doorsnede", "Beam"])
    nids = [int(n.get("nid")) for n in solution.findall("node")]
    check("parsed back: node ids unique, ascending: " + label,
          nids == sorted(set(nids)) and nids[8] == 9)
    shells = solution.find("elset")
    known = set(nids)
    eids = [int(e.get("eid")) for e in shells.findall("elem")]
    check("parsed back: shells on known nodes, ids above the model: " + label,
          min(eids) == 8 and len(set(eids)) == 30 and
          all(int(n) in known for e in shells.findall("elem")
              for n in e.get("nodes").split()) and
          set(e.get("shape") for e in shells.findall("elem")) == set(
              ["quad4"]))
    check("parsed back: no material on the shells: " + label,
          shells.get("material") is None)
    found = dict((int(n.get("nid")), (float(n.get("x")), float(n.get("y")),
                                      float(n.get("z"))))
                 for n in solution.findall("node"))
    check("parsed back: coordinates exact: " + label,
          all(found[n] == p for n, p in zip(view["nids"], view["xyz"])))

text = sv.solution_text(view, "\r\n")
lines = sv.solution_lines(view)
check("text: lines joined, every line ended", text.endswith("</elset>\r\n") and
      text.split("\r\n")[:-1] == lines)
check("text: LF on request", "\r" not in sv.solution_text(view, "\n"))
head, copy_lines = split_copy(CHAIN, u"\n")
model_node = [ln for ln in copy_lines if '<node nid="1"' in ln][0]
model_elem = [ln for ln in copy_lines if 'eid="1"' in ln][0]
model_end = [ln for ln in copy_lines if "</elset>" in ln][0]
indent = len(model_node) - len(model_node.lstrip())
check("text: indentation as the copy", indent == 4 and
      lines[0].startswith(" " * 4 + "<node") and
      [ln for ln in lines if "<elset" in ln][0].startswith(" " * 4 + "<") and
      [ln for ln in lines if "<elem" in ln][0].startswith(
          model_elem[:len(model_elem) - len(model_elem.lstrip())] + "<") and
      lines[-1] == model_end)
check("text: no comma as decimal separator, no fieldvariable",
      "," not in text and "fieldvariable" not in text)
check("text: no <results>, no model content",
      "<results" not in text and "<solution" not in text and
      'name="Beam"' not in text)
check("text: no material on the elset", "material" not in text)
del LOG[:]
md_cfg = chain_model(CHAIN.replace(u'  <analysis type="S30" />',
                                   u'  <analysis type="S30" />\n'
                                   u'  <configuration name="A" />'),
                     "chain_cfg.liml")
check("configurations: read", md_cfg is not None)
head, _ = split_copy(CHAIN.replace(u'  <analysis type="S30" />',
                                   u'  <analysis type="S30" />\n'
                                   u'  <configuration name="A" />'), u"\n")
cfg_lines = bridge_results_liml._solution_copy(head, u"\n", "A")
new = sv.insert_into_copy(cfg_lines, view)
check("configurations: inserted in that copy as well",
      len(new) == len(cfg_lines) + len(lines) and lines[0] in new)
# --- thin bar in the model copy -----------------------------------------
def rect(w, h):
    return [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)]


def same(a, b):
    return abs(a - b) < 1e-12


check("thin: at most 2 mm",
      sv.thin_size([rect(0.3, 0.2)], 0.06) == sv.THIN_MAX)
check("thin: 3% of the largest size for a small solid section",
      same(sv.thin_size([rect(0.01, 0.01)], 1e-4), 0.0003))
ell = [(0.0, 0.0), (0.06, 0.0), (0.06, 0.006), (0.006, 0.006), (0.006, 0.04),
       (0.0, 0.04)]
check("thin: a quarter of the wall of an L 60 x 40 x 6",
      same(sv.thin_size([ell], 5.64e-4), 0.25 * 2.0 * 5.64e-4 / 0.2))
tube = [rect(0.1, 0.1), [(0.001, 0.001), (0.001, 0.099), (0.099, 0.099),
                         (0.099, 0.001)]]
got = sv.thin_size(tube, 0.1 ** 2 - 0.098 ** 2)
check("thin: a tube with a 1 mm wall gets a bar of a quarter of that",
      abs(got - 0.00025) < 1e-5)
copy_lines = [u'    <elset name="Beam" colorrgb="DADADA" material="A&amp;B">',
              u'      <elem eid="1" shape="line2" nodes="1 2" />',
              u'    </elset>',
              u'    <elset name="Other" material="Staal">',
              u'    </elset>',
              u'    <mat name="A&amp;B">',
              u'      <geometric type="UniformGeneralSection" area="1 m" />',
              u'      <mechanical type="Isotropic" poissonratio="0.3" />',
              u'    </mat>',
              u'    <mat name="Staal">',
              u'      <geometric type="RectBar" recta="1 m" rectb="1 m" />',
              u'    </mat>']
one = {"thin": {u"A&B": 0.0014}}
thin = sv.thin_beam_lines(copy_lines, one)
text = u"\n".join(thin)
check("thin: material copied with a bar, the original stays",
      u'name="A&amp;B__doorsnede_lijn"' in text and
      u'<geometric type="RectBar" recta="0.0014 m" rectb="0.0014 m" />' in text
      and u'name="A&amp;B">' in text and u"UniformGeneralSection" in text)
check("thin: only the elsets of that material move",
      u'material="A&amp;B__doorsnede_lijn"' in thin[0] and
      u'material="Staal"' in thin[3])
check("thin: a second call gives the same text",
      sv.thin_beam_lines(thin, one) == thin)
check("thin: undone with nothing to draw",
      sv.thin_beam_lines(thin, {"thin": {}}) == copy_lines)
top = [u'  <mat name="A&amp;B">', u'  </mat>'] + copy_lines
check("thin: the top level of a file is not touched",
      sv.thin_beam_lines(top, one)[:2] == top[:2])
shutil.rmtree(TMP, ignore_errors=True)

print("{0} checks".format(check.count))
if check.failed:
    print("FOUT: test_bridge_section_view")
    sys.exit(1)
print("Alle controles OK")
