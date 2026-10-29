# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_beams.py
# Beam sidecar <model>_<run_id>_beams.json (mwhubpost-beams/1,
# AdvancedToolsHub docs/design/CONTRACT_MWPOST.md §4) for MWHub Post
# (plugin AdvMWHub Beams: profile swept along each beam, stresses from the
# section forces). Written by bridge_to_aster.generate_AsterSolver_files
# with vtu_export or med_export, when the model has beams.
#
# Contents (interpretation of the concept in the contract, fixed here):
#   units      {"length": "m"}; all values SI.
#   sections   per beam elset (Code-Aster group name, model_data
#              ["beam_sections"], whose geometry keeps Mecway's dimensions
#              in "profile"):
#     shape        Mecway geometry type: I, T, L, C, RectBar, RectTube,
#                  CircularBar, UniformCircularTube, UniformGeneralSection
#     dims         Mecway's dimensions in m (I/T/L/C: a, b, c, d with the
#                  meaning of bridge_from_liml._profile_props; RectBar a, b;
#                  RectTube a, b, t; circles od, id)
#     polygons     DISJOINT parts whose union is the section, each a closed
#                  outline [[y, z], ...] (counter-clockwise, first point not
#                  repeated) in the local axes, centroid at (0, 0); I/T/C =
#                  3 or 2 rectangles (flanges, web), L = 2 legs in
#                  Mecway's principal axes, circle = 64-gon
#     holes        outlines to subtract (RectTube, tube); [] otherwise
#     A, Iy, Iz, J the values the bridge passes to Code-Aster (Iy = about
#                  local y; after #ASTER-SECTIE those values)
#     shear_areas  {"y", "z"}: A / AY and A / AZ (I/T/L/C as POU_D_T,
#                  bridge_from_liml._profile_shear_coefs; RectBar A / 1.2);
#                  null if unknown
#     offset       [0, 0]: section offsets are offset cells in the mesh
#                  (bridge_mesh), not a shift of the section
#     wall         I/T/L/C/RectTube/tube: wall thicknesses for thin-walled
#                  shear {"flange", "web"} or {"t"}; absent otherwise
#   elements   per beam element: id (Mecway eid), section, axes x (node 1
#              -> node 2), y (= Mecway's V = Code-Aster VECT_Y, made
#              perpendicular to x), z = x × y, nodes [n1, n2], length, and
#              stations [0, 1]: the section forces are given at the two
#              element ends, as cell arrays EFGE_<N|VY|VZ|MT|MFY|MFZ>_1/_2
#              in the VTU (aster_vtu), per time step.
#
# Local section coordinates: y = V, z = W as Mecway uses them
# (bridge_warping.mecway_frame, measured with Mecway 34: the drawing x runs
# along -W, so a C profile has its web at +W; L in Mecway's principal
# axes). The self-check (_check) compares A, Iy, Iz of
# the polygons with the values of the bridge and logs a WARNING above 1 %.
#
# Compatible with IronPython 2.7.9 (stdlib only).

import io
import json
import math
from datetime import datetime

from bridge_utils import log, tr, run_name
import bridge_warping

SCHEMA = "mwhubpost-beams/1"


def _rect(y0, y1, z0, z1):
    """Counter-clockwise rectangle in (y, z)."""
    return [[y0, z0], [y0, z1], [y1, z1], [y1, z0]][::-1]


def _rects_of(shape, d):
    """Rectangles (x0, x1, y0, y1) of the drawing (x horizontal = W,
    y vertical = V), as bridge_from_liml._profile_props."""
    a, b, c, w = d["a"], d["b"], d["c"], d["d"]
    if shape == "I":
        return [(0.0, b, 0.0, c), (0.0, b, a - c, a),
                ((b - w) / 2.0, (b + w) / 2.0, c, a - c)]
    if shape == "T":
        return [(0.0, a, w, w + c), ((a - b) / 2.0, (a + b) / 2.0, 0.0, w)]
    if shape == "C":
        return [(0.0, a, 0.0, c), (0.0, a, b - c, b), (0.0, w, c, b - c)]
    if shape == "L":
        return [(0.0, a, 0.0, c), (0.0, c, c, b)]
    return []


def _moments(polys, holes=()):
    """A, centroid (y, z), Iy (= int z^2), Iz (= int y^2), Iyz about the
    centroid of outlines (shoelace formulas)."""
    tot = [0.0] * 6     # A, Sy (int y), Sz (int z), int y^2, int z^2, int yz
    for sign, group in ((1.0, polys), (-1.0, holes)):
        for p in group:
            for i in range(len(p)):
                y0, z0 = p[i]
                y1, z1 = p[(i + 1) % len(p)]
                cr = y0 * z1 - y1 * z0
                tot[0] += sign * cr / 2.0
                tot[1] += sign * cr * (y0 + y1) / 6.0
                tot[2] += sign * cr * (z0 + z1) / 6.0
                tot[3] += sign * cr * (y0 * y0 + y0 * y1 + y1 * y1) / 12.0
                tot[4] += sign * cr * (z0 * z0 + z0 * z1 + z1 * z1) / 12.0
                tot[5] += sign * cr * (y0 * z1 + 2 * y0 * z0 + 2 * y1 * z1 +
                                       y1 * z0) / 24.0
    A = tot[0]
    if abs(A) < 1e-30:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    cy, cz = tot[1] / A, tot[2] / A
    iz = tot[3] - A * cy * cy
    iy = tot[4] - A * cz * cz
    iyz = tot[5] - A * cy * cz
    return A, cy, cz, iy, iz, iyz


def _shift_rotate(polys, cy, cz, angle):
    co, s = math.cos(angle), math.sin(angle)
    out = []
    for p in polys:
        q = []
        for y, z in p:
            y, z = y - cy, z - cz
            q.append([co * y + s * z, -s * y + co * z])
        out.append(q)
    return out


def _circle(r, n=64):
    return [[r * math.cos(2 * math.pi * k / n),
             r * math.sin(2 * math.pi * k / n)] for k in range(n)]


def section_geometry(profile):
    """(polygons, holes, wall) of a Mecway profile in local (y, z) with
    the centroid at the origin; I/T/L/C in Mecway's axes
    (bridge_warping.mecway_frame; L in its principal axes)."""
    shape = profile.get("shape")
    if shape in ("I", "T", "L", "C"):
        frame = bridge_warping.mecway_frame(shape, profile["a"],
                                            profile["b"], profile["c"],
                                            profile["d"])
        if frame is None:
            return [], [], None
        to_local = frame[1]
        # The map mirrors the drawing (x -> -W): these corners, counter-
        # clockwise in the drawing, stay counter-clockwise in (y, z)
        polys = [[list(to_local(x, y)) for x, y in
                  ((x1, y0), (x1, y1), (x0, y1), (x0, y0))]
                 for x0, x1, y0, y1 in _rects_of(shape, profile)]
        wall = ({"t": profile["c"]} if shape == "L" else
                {"flange": profile["c"],
                 "web": profile["b"] if shape == "T" else profile["d"]})
        return polys, [], wall
    elif shape == "RectBar":
        polys = [_rect(0.0, profile["a"], 0.0, profile["b"])]
        return _centred(polys, []) + (None,)
    elif shape == "RectTube":
        a, b, t = profile["a"], profile["b"], profile["t"]
        polys, holes = [_rect(0.0, a, 0.0, b)], [_rect(t, a - t, t, b - t)]
        return _centred(polys, holes) + ({"t": t},)
    elif shape == "CircularBar":
        return [_circle(profile["od"] / 2.0)], [], None
    elif shape == "UniformCircularTube":
        od, rid = profile["od"], profile["id"]
        return ([_circle(od / 2.0)], [_circle(rid / 2.0)][:1 if rid > 0
                                                              else 0],
                {"t": (od - rid) / 2.0})
    else:
        return [], [], None
    return _centred(polys, []) + (wall,)


def _centred(polys, holes):
    A, cy, cz = _moments(polys, holes)[:3]
    return _shift_rotate(polys, cy, cz, 0.0), _shift_rotate(holes, cy, cz,
                                                            0.0)


def _unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return [c / n for c in v] if n > 0 else [0.0, 0.0, 0.0]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def _axes(p1, p2, v):
    """x along the element, y = V made perpendicular to x, z = x × y."""
    x = _unit([p2[i] - p1[i] for i in range(3)])
    dot = sum(v[i] * x[i] for i in range(3))
    y = _unit([v[i] - dot * x[i] for i in range(3)])
    return x, y, _cross(x, y)


def _check(name, sec):
    """WARNING if A, Iy or Iz of the polygons differs > 1 % from the
    values of the bridge (e.g. after #ASTER-SECTIE)."""
    if not sec["polygons"] or not sec.get("A"):
        return
    A, _cy, _cz, iy, iz, _iyz = _moments(sec["polygons"], sec["holes"])
    ok = all(abs(got - want) <= 0.01 * abs(want) + 1e-20
             for got, want in ((A, sec["A"]), (iy, sec["Iy"]),
                               (iz, sec["Iz"])) if want)
    if not ok:
        log(tr("WARNING: Balk-sidecar: doorsnede '{0}' wijkt af van de "
               "doorgegeven waarden (A {1:.4g}/{2:.4g}, Iy {3:.4g}/{4:.4g}, "
               "Iz {5:.4g}/{6:.4g}); de vorm is alleen ter illustratie.",
               "WARNING: Beam sidecar: section '{0}' differs from the "
               "values passed on (A {1:.4g}/{2:.4g}, Iy {3:.4g}/{4:.4g}, "
               "Iz {5:.4g}/{6:.4g}); the shape is for illustration "
               "only.").format(name, A, sec["A"], iy, sec["Iy"], iz,
                               sec["Iz"]))


def _section(name, profile, geom):
    cara = dict(zip(geom.get("cara", ()), geom.get("vale", ())))
    polys, holes, wall = section_geometry(profile)
    A = cara.get("A")
    iy, iz, j = cara.get("IY"), cara.get("IZ"), cara.get("JX")
    if A is None and profile.get("shape") in ("CircularBar",
                                              "UniformCircularTube"):
        # CERCLE: exact values (the 64-gon is about 0.2 % smaller)
        r, ri = profile["od"] / 2.0, profile.get("id", 0.0) / 2.0
        A = math.pi * (r * r - ri * ri)
        iy = iz = math.pi * (r ** 4 - ri ** 4) / 4.0
        j = 2.0 * iy
    elif A is None and polys:
        # RECTANGLE: Code-Aster computes them; take the polygons
        A, _cy, _cz, iy, iz, _iyz = _moments(polys, holes)
        j = None
    shear = None
    coefs = geom.get("shear_coefs")
    if coefs and A:
        shear = {"y": A / coefs[0], "z": A / coefs[1]}
    elif profile.get("shape") == "RectBar" and A:
        shear = {"y": A / 1.2, "z": A / 1.2}
    dims = dict((k, v) for k, v in profile.items() if k != "shape")
    sec = {"shape": profile.get("shape"), "dims": dims, "polygons": polys,
           "holes": holes, "A": A, "Iy": iy, "Iz": iz, "J": j,
           "shear_areas": shear, "offset": [0.0, 0.0]}
    if wall:
        sec["wall"] = wall
    _check(name, sec)
    return sec


def build(model_data):
    """The sidecar as a dict, or None without beam elements."""
    axes = model_data.get("beam_axes") or {}
    if not axes:
        return None
    xyz = model_data.get("beam_node_xyz") or {}
    # per elset (Code-Aster name, renamed by bridge_mesh like beam_axes):
    # the geometry of _parse_geometric_props with "profile" (Mecway's
    # dimensions), or {"truss": True, "area": ..} for trusses
    secs = model_data.get("beam_sections", {})
    sections, elements = {}, []
    for eid, (es, n1, n2, v) in axes.items():
        geom = secs.get(es)
        name = es if geom is not None else None
        if geom is not None and es not in sections:
            sections[es] = _section(es, geom.get("profile") or {
                "shape": geom.get("geom_type", "")}, geom)
        p1, p2 = xyz[n1], xyz[n2]
        x, y, z = _axes(p1, p2, v)
        elements.append({
            "id": int(eid), "section": name, "nodes": [int(n1), int(n2)],
            "length": math.sqrt(sum((p2[i] - p1[i]) ** 2
                                    for i in range(3))),
            "axes": {"x": x, "y": y, "z": z}, "stations": [0.0, 1.0]})
    return {"schema": SCHEMA,
            "created": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "units": {"length": "m"}, "sections": sections,
            "elements": elements}


def write_sidecar(work_dir, model_data):
    """Write <model>_<run_id>_beams.json; returns the path or None. An
    error only costs the sidecar (WARNING), not the run."""
    try:
        data = build(model_data)
        if data is None:
            return None
        import os
        path = os.path.join(work_dir, run_name("_beams.json"))
        text = json.dumps(data, ensure_ascii=False, indent=1,
                          sort_keys=True)
        if not isinstance(text, type(u"")):
            text = text.decode("utf-8")
        f = io.open(path, "w", encoding="utf-8")
        try:
            f.write(text)
        finally:
            f.close()
        log("INFO: Balk-sidecar geschreven: {0} ({1} elementen, {2} "
            "doorsneden).".format(path, len(data["elements"]),
                                  len(data["sections"])))
        return path
    except Exception as e:
        log(tr("WARNING: Balk-sidecar niet geschreven: {0}",
               "WARNING: Beam sidecar not written: {0}").format(e))
        return None
