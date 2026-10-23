# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# section_analysis.py
# Cross-section properties of a beam section (mesher + FEM), run with the
# Python that ships with Code-Aster (CPython 3, numpy + scipy); NOT in
# IronPython.
#
#   python section_analysis.py <in.json> <out.json>
#
# Input (all lengths in metres):
#   {"loops": [[[x, y], ...], ...],   closed loops (last point not repeated),
#                                     even-odd domain
#    "step": {"file", "normal", "offset", "u", "v", "points", "tol"},
#                                     alternative to "loops" (section_step)
#    "mesh_size": null,               maximum element area in m^2 (null = auto)
#    "nu": 0.0}                       Poisson ratio for the shear functions
# Output: flat keys in SI (see run_analysis), "loops" (the cleaned loops that
# were meshed) and an "aster" block for AFFE_CARA_ELEM POUTRE
# SECTION='GENERALE'. out.json is always written ("success" false + "error" +
# "traceback" on failure).

import json
import math
import os
import sys
import time
import traceback

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import section_fem  # noqa: E402
import section_mesh  # noqa: E402


def _loops_from_step(step):
    import section_step   # written separately; imported only when needed
    path = step["file"]
    face_ids = section_step.find_faces(path, step.get("normal"), step.get("offset"),
                                       step.get("points"), step.get("tol"))
    # 1 degree per chord: ~5e-5 relative area error on circles (3 deg: ~5e-4)
    info = {}
    try:
        loops = section_step.face_loops_2d(path, face_ids, step.get("u"), step.get("v"),
                                           chord_rel=1e-6, max_angle_deg=1.0, info=info)
    except TypeError:
        # older section_step without the info argument
        loops = section_step.face_loops_2d(path, face_ids, step.get("u"), step.get("v"),
                                           chord_rel=1e-6, max_angle_deg=1.0)
    return loops, list(face_ids), info.get("gaps_closed", [])


def aster_block(res, nodes, elements):
    """Characteristics for AFFE_CARA_ELEM POUTRE SECTION='GENERALE'
    (U4.42.01 par. 9.4.3), in the frame local y = principal axis 1 (angle
    phi from +x), local z = axis 1 rotated +90 deg, origin at the centroid.

    Conventions, checked against MACR_CARA_POUTRE of Code-Aster 17.4 on the
    same tri6 mesh (tests/section_aster_check.py; channel, unequal angle, Z,
    rectangle), after mapping Code-Aster's principal frame (angle ALPHA,
    which may be ours rotated by a multiple of 90 deg) onto ours:
      IY = int z^2 dA = I11, IZ = int y^2 dA = I22;
      AY, AZ = A / shear area for a shear force along y, z (nu = 0 gives
        Code-Aster's values; rectangle 1.2);
      EY, EZ = components of the vector FROM the shear centre TO the centroid
        (Code-Aster: "excentrement du centre de torsion, composante de CG",
        macr_cara_poutre_ops.py: (PCTY, PCTZ) = CG);
      JX = J, JG = warping constant about the shear centre;
      RY, RZ = max |y|, |z| of the nodes;
      RT = J max|tau| / T on the boundary (Code-Aster takes the extreme normal
        flux along GROUP_MA_BORD; equal for smooth sections, mesh dependent at
        re-entrant corners);
      IYR2 = int z (y^2 + z^2) dA, IZR2 = int y (y^2 + z^2) dA, about the
        centroid (the IYR2/IZR2 columns of MACR_CARA_POUTRE with
        TABLE_CARA='OUI', i.e. what AFFE_CARA_ELEM TABLE_CARA reads)."""
    p = math.radians(res["phi_deg"])
    c, s = math.cos(p), math.sin(p)
    G = np.array(res["centroid"])
    rel = nodes - G
    yl = c * rel[:, 0] + s * rel[:, 1]
    zl = -s * rel[:, 0] + c * rel[:, 1]
    w, Ns, B, x, y = section_fem._element_data(nodes, elements, res["centroid"])
    yg = c * x + s * y
    zg = -s * x + c * y
    r2 = yg ** 2 + zg ** 2
    out = {
        "A": res["area"],
        "IY": res["i11_c"],
        "IZ": res["i22_c"],
        "RY": float(np.abs(yl).max()),
        "RZ": float(np.abs(zl).max()),
        "IYR2": float(np.sum(w * zg * r2)),
        "IZR2": float(np.sum(w * yg * r2)),
    }
    if res.get("warping_computed"):
        cg = G - np.array(res["shear_centre"])
        out.update({
            "AY": res["area"] / res["a_s11"],
            "AZ": res["area"] / res["a_s22"],
            "EY": float(c * cg[0] + s * cg[1]),
            "EZ": float(-s * cg[0] + c * cg[1]),
            "JX": res["j"],
            "JG": res["gamma"],
            "RT": res["rt"],
        })
    return out


def run_analysis(data):
    t0 = time.time()
    res = {}
    if data.get("loops"):
        loops = data["loops"]
        if "heal" in data:
            res["heal"] = data["heal"]      # passed through unchanged
    elif data.get("step"):
        loops, face_ids, gaps = _loops_from_step(data["step"])
        res["face_ids"] = face_ids
        res["gaps_closed"] = gaps
    else:
        raise ValueError("input needs 'loops' or 'step'")
    nu = float(data.get("nu") or 0.0)
    mesh = section_mesh.mesh_section(loops, max_area=data.get("mesh_size") or None)
    nodes, elements, boundary = mesh["nodes"], mesh["elements"], mesh["boundary"]
    t_mesh = time.time() - t0

    geo = section_fem.geometric_properties(nodes, elements)
    res.update(geo)
    res["perimeter"] = section_fem.outer_perimeter(mesh["loops"])
    n_parts, _ = section_mesh.element_parts(elements)
    res["n_parts"] = int(n_parts)
    res["n_elements"] = int(len(elements))
    res["n_nodes"] = int(len(nodes))
    res["mesh_info"] = mesh["info"]

    try:
        res.update(section_fem.plastic_properties(nodes, elements, geo["phi_deg"]))
        res["plastic_computed"] = True
    except Exception as exc:
        res["plastic_computed"] = False
        res["plastic_note"] = str(exc)

    res["warping_computed"] = False
    res["warping_note"] = ""
    if n_parts > 1:
        res["warping_note"] = ("section consists of {0} separate parts: torsion and shear "
                               "properties are not meaningful".format(n_parts))
    else:
        try:
            wp = section_fem.warping_properties(nodes, elements, geo, nu=nu, boundary=boundary)
            wp.pop("_omega", None)
            wp.pop("delta_s", None)
            res.update(wp)
            res["warping_computed"] = True
        except Exception as exc:
            res["warping_note"] = "warping analysis failed: {0}".format(exc)
    res["nu"] = nu
    res["aster"] = aster_block(res, nodes, elements)
    res["loops"] = [np.asarray(l).tolist() for l in mesh["loops"]]
    res["time_mesh_s"] = t_mesh
    res["time_total_s"] = time.time() - t0
    return res


def _jsonable(o):
    if isinstance(o, dict):
        return dict((k, _jsonable(v)) for k, v in o.items())
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return _jsonable(o.tolist())
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("Usage: python section_analysis.py <in.json> <out.json>")
        return 2
    in_path, out_path = argv
    try:
        with open(in_path, "r") as f:
            data = json.load(f)
        results = run_analysis(data)
        results["success"] = True
    except Exception as exc:
        results = {"success": False, "error": str(exc),
                   "traceback": traceback.format_exc()}
    with open(out_path, "w") as f:
        json.dump(_jsonable(results), f, indent=1)
    return 0 if results["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
