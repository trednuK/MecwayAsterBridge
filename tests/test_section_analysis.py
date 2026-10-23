# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Test of Scripts/section_mesh.py, section_fem.py and section_analysis.py
# (cross-section properties). Run with the Python that ships with Code-Aster
# (numpy + scipy):
#
#   python tests/test_section_analysis.py
#
# Reference values: analytic, sectionproperties 3.x (same polygons, about
# 4700 tri6 elements; recorded during development, not needed here) and
# Code-Aster 17.4 MACR_CARA_POUTRE on our mesh (tests/section_aster_check.py).

from __future__ import print_function

import json
import math
import os
import shutil
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__", sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import numpy as np  # noqa: E402
import section_analysis as sa  # noqa: E402
import section_mesh as sm  # noqa: E402


def check(name, cond, detail=""):
    print(("OK   " if cond else "FOUT ") + name + ("" if cond else "  " + str(detail)))
    if not cond:
        check.failed = True


check.failed = False


def rel(a, b):
    return abs(a - b) / max(abs(b), 1e-300)


# --- shapes (metres) -------------------------------------------------------
def rect(b, h, x0=0.0, y0=0.0):
    return [[x0, y0], [x0 + b, y0], [x0 + b, y0 + h], [x0, y0 + h]]


def circle(r, n, cx=0.0, cy=0.0):
    return [[cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)]
            for k in range(n)]


def arc(cx, cy, r, a0, a1, n):
    return [[cx + r * math.cos(a0 + (a1 - a0) * k / n), cy + r * math.sin(a0 + (a1 - a0) * k / n)]
            for k in range(n + 1)]


def ibeam_fillet(d, b, tf, tw, r, nr):
    x1, y1 = tw / 2.0, d / 2.0 - tf
    pts = [[-b / 2, -d / 2], [b / 2, -d / 2], [b / 2, -y1]]
    pts += arc(x1 + r, -y1 + r, r, -math.pi / 2, -math.pi, nr)
    pts += arc(x1 + r, y1 - r, r, math.pi, math.pi / 2, nr)
    pts += [[b / 2, y1], [b / 2, d / 2], [-b / 2, d / 2], [-b / 2, y1]]
    pts += arc(-x1 - r, y1 - r, r, math.pi / 2, 0.0, nr)
    pts += arc(-x1 - r, -y1 + r, r, 0.0, -math.pi / 2, nr)
    pts += [[-b / 2, -y1]]
    return pts


def channel(d, b, tf, tw):
    return [[0, 0], [b, 0], [b, tf], [tw, tf], [tw, d - tf], [b, d - tf], [b, d], [0, d]]


SHAPES = {
    "channel": [channel(0.2, 0.075, 0.0115, 0.0085)],
    "angle": [[[0, 0], [0.09, 0], [0.09, 0.01], [0.01, 0.01], [0.01, 0.15], [0, 0.15]]],
    "ibeam_fillet": [ibeam_fillet(0.2, 0.1, 0.0085, 0.0056, 0.012, 8)],
    "tube": [circle(0.05, 64), circle(0.04, 64)],
    "box_thin": [rect(0.2, 0.1), rect(0.196, 0.096, 0.002, 0.002)],
    "thin_open": [channel(0.1, 0.05, 0.001, 0.001)],
    "zed": [[[0, 0], [0.08, 0], [0.08, 0.01], [0.008, 0.01], [0.008, 0.2], [-0.072, 0.2],
             [-0.072, 0.19], [0, 0.19]]],
    "plate2holes": [rect(0.3, 0.1), circle(0.02, 48, 0.08, 0.05), circle(0.025, 48, 0.21, 0.05)],
}

# sectionproperties (Pilkey formulation), nu = 0
SP = {
    'channel': dict(j=1.0762243393914184e-07, gamma=1.0681194298938471e-08, sc=[-0.02196956128951704, 0.09999991575571167], asp=[0.0008732746838269545, 0.001473275209893287], s=[0.00022915537500000014, 5.80445371360966e-05], sp=[0.00022915537500000014, 5.80445371360966e-05]),
    'angle': dict(j=7.53043262899205e-08, gamma=9.996386319745049e-11, sc=[0.004897103917935165, 0.006019954290130837], asp=[0.0007157398869764608, 0.0011788820777432854], s=[9.624999999742115e-05, 3.868333329485304e-05], sp=[0.00010277051338492495, 3.717746928185247e-05]),
    'ibeam_fillet': dict(j=6.884644195700524e-08, gamma=1.274296154148178e-08, sc=[8.603268509589565e-09, 3.6918229207971063e-09], asp=[0.001589902620338767, 0.0010971596766366145], s=[0.00022089143125416142, 4.463296073454845e-05], sp=[0.00022089143125416142, 4.463296073454845e-05]),
    'tube': dict(j=5.777186700586544e-06, gamma=1.1372949325583654e-16, sc=[-1.4942343213066875e-08, 1.1642943920044195e-08], asp=[0.0014402605263276506, 0.0014402605449061485], s=[8.113751221783076e-05, 8.113751221783078e-05], sp=[8.113751221783076e-05, 8.113751221783078e-05]),
    'box_thin': dict(j=5.1200762961943414e-06, gamma=1.0878240351202782e-09, sc=[0.09999961439948116, 0.05000011167293343], asp=[0.0002638141691785813, 0.0007280457846329428], s=[4.8416000000000134e-05, 7.801600000000029e-05], sp=[7.801600000000029e-05, 4.8416000000000134e-05]),
    'thin_open': dict(j=6.595048056991238e-11, gamma=8.672066181663134e-11, sc=[-0.018054765480327598, 0.04999999581756053], asp=[6.118841920389426e-05, 8.286691364911291e-05], s=[7.350999999750008e-06, 2.450989975114321e-06], sp=[7.350999999750008e-06, 2.450989975114321e-06]),
    'zed': dict(j=8.178877074342084e-08, gamma=1.651379725246336e-08, sc=[0.004000026500827935, 0.1000000514057824], asp=[0.0011421807059521132, 0.0014978811729211968], s=[0.00021680000000000012, 6.080000000000004e-05], sp=[0.00022405463638282806, 5.0942009653635585e-05]),
    'plate2holes': dict(j=7.673056243436338e-05, gamma=1.1607751217142048e-07, sc=[0.14953990194094607, 0.04999999946153627], asp=[0.018363255014349388, 0.019196026161320077], s=[0.0007186347433808635, 0.0020435708221734324], sp=[0.0020435708221734324, 0.0007186347433808635]),
}

# Code-Aster 17.4 MACR_CARA_POUTRE (TABLE_CARA='OUI') on our mesh, in its own
# principal frame (ALPHA); k = frame offset to ours in multiples of 90 deg.
ASTER = {
    "channel": (1, dict(A=3.229500e-03, IY=1.706095e-06, IZ=1.927017e-05, AY=2.192146,
                        AZ=3.698524, EY=1.213397e-07, EZ=-4.398013e-02, JX=1.075500e-07,
                        JG=1.068134e-08, RY=0.1, RZ=5.298990e-02, IYR2=-2.029667e-07,
                        IZR2=1.692385e-15)),
    "angle": (3, dict(A=2.3e-03, IY=8.931265e-07, IZ=5.978250e-06, AY=1.950922,
                      AZ=3.213341, EY=3.648071e-02, EZ=-3.015565e-02, JX=7.527615e-08,
                      JG=9.996308e-11, RY=1.003853e-01, RZ=5.111589e-02, IYR2=-7.733531e-08,
                      IZR2=8.707465e-08)),
}


def to_aster_frame(a, k):
    """Our aster block in a frame rotated by k * 90 deg (y' = z, z' = -y per
    step), as TraiteQuadrant in Code-Aster's macr_cara_poutre_ops.py."""
    b = dict(a)
    for _ in range(k % 4):
        b = {"A": b["A"], "IY": b["IZ"], "IZ": b["IY"], "AY": b["AZ"], "AZ": b["AY"],
             "EY": b["EZ"], "EZ": -b["EY"], "RY": b["RZ"], "RZ": b["RY"],
             "IYR2": -b["IZR2"], "IZR2": b["IYR2"], "JX": b["JX"], "JG": b["JG"]}
    return b


# --- 1. rectangle: analytic ------------------------------------------------
t0 = time.time()
r = sa.run_analysis({"loops": [rect(0.1, 0.2)]})
check("rectangle: area", rel(r["area"], 0.02) < 1e-12, r["area"])
check("rectangle: centroid", np.allclose(r["centroid"], [0.05, 0.1], atol=1e-15), r["centroid"])
check("rectangle: Ixx, Iyy, Ixy", rel(r["ixx_c"], 0.1 * 0.2 ** 3 / 12) < 1e-12 and
      rel(r["iyy_c"], 0.2 * 0.1 ** 3 / 12) < 1e-12 and abs(r["ixy_c"]) < 1e-18)
check("rectangle: I11 = Ixx, phi = 0", r["i11_c"] == r["ixx_c"] and r["phi_deg"] == 0.0)
check("rectangle: perimeter", rel(r["perimeter"], 0.6) < 1e-12, r["perimeter"])
check("rectangle: Zxx+ = bh^2/6", rel(r["zxx_plus"], 0.1 * 0.04 / 6) < 1e-12)
check("rectangle: Sxx = bh^2/4, Syy = hb^2/4", rel(r["sxx"], 0.1 * 0.04 / 4) < 1e-9 and
      rel(r["syy"], 0.2 * 0.01 / 4) < 1e-9, (r["sxx"], r["syy"]))
# J = beta h b^3 with beta(h/b = 2) = 0.2287 (Timoshenko & Goodier, series)
beta = 1.0 / 3.0 * (1 - 192.0 / math.pi ** 5 * 0.5 *
                    sum(math.tanh((2 * n + 1) * math.pi) / (2 * n + 1) ** 5 for n in range(20)))
check("rectangle: J (series) 1e-4", rel(r["j"], beta * 0.2 * 0.1 ** 3) < 1e-4,
      (r["j"], beta * 0.2 * 0.1 ** 3))
check("rectangle: shear centre = centroid",
      np.allclose(r["shear_centre"], r["centroid"], atol=1e-8))
check("rectangle: AY = AZ = 1.2 (nu = 0)", abs(r["aster"]["AY"] - 1.2) < 1e-6 and
      abs(r["aster"]["AZ"] - 1.2) < 1e-6, (r["aster"]["AY"], r["aster"]["AZ"]))
check("rectangle: RT = Code-Aster 0.093005 (smooth boundary)",
      rel(r["aster"]["RT"], 0.09300503) < 1e-3, r["aster"]["RT"])
check("rectangle: tri6 count about 3000+", 2500 <= r["n_elements"] <= 6000, r["n_elements"])

# --- 2. circle with dense boundary: J = pi r^4 / 2 --------------------------
r = sa.run_analysis({"loops": [circle(0.05, 360)]})
ip = math.pi * 0.05 ** 4 / 2
check("circle 360 points: J = Ip (2e-4)", rel(r["j"], ip) < 2e-4, (r["j"], ip))
check("circle 360 points: element count not exploded", r["n_elements"] < 6000, r["n_elements"])
check("circle: warping constant ~ 0", abs(r["gamma"]) < 1e-12 * ip * 0.05 ** 2, r["gamma"])

# --- 3. against sectionproperties -------------------------------------------
for name, loops in sorted(SHAPES.items()):
    r = sa.run_analysis({"loops": loops})
    s = SP[name]
    size = r["mesh_info"]["diag"]
    check(name + ": J (0.5%)", rel(r["j"], s["j"]) < 5e-3, (r["j"], s["j"]))
    g_ok = (rel(r["gamma"], s["gamma"]) < 5e-3 if s["gamma"] > 1e-12 else
            abs(r["gamma"]) < 1e-10)
    check(name + ": warping constant (0.5%)", g_ok, (r["gamma"], s["gamma"]))
    check(name + ": shear centre (1e-4 size)",
          np.allclose(r["shear_centre"], s["sc"], atol=1e-4 * size), (r["shear_centre"], s["sc"]))
    check(name + ": Trefftz shear centre (1e-4 size)",
          np.allclose(r["shear_centre_trefftz"], s["sc"], atol=1e-4 * size))
    check(name + ": shear areas 11, 22 (0.5%)", rel(r["a_s11"], s["asp"][0]) < 5e-3 and
          rel(r["a_s22"], s["asp"][1]) < 5e-3, ([r["a_s11"], r["a_s22"]], s["asp"]))
    check(name + ": plastic moduli (0.1%)",
          all(rel(a, b) < 1e-3 for a, b in zip([r["sxx"], r["syy"], r["s11"], r["s22"]],
                                              s["s"] + s["sp"])),
          ([r["sxx"], r["syy"], r["s11"], r["s22"]], s["s"] + s["sp"]))

# --- 4. against Code-Aster MACR_CARA_POUTRE ---------------------------------
for name, (k, ca) in sorted(ASTER.items()):
    r = sa.run_analysis({"loops": SHAPES[name]})
    a = to_aster_frame(r["aster"], k)
    big = max(ca["RY"], ca["RZ"])
    for key, ref in sorted(ca.items()):
        if key in ("EY", "EZ"):
            ok = abs(a[key] - ref) < 1e-5 * big
        elif key in ("IYR2", "IZR2"):
            ok = abs(a[key] - ref) < 1e-5 * max(ca["IY"], ca["IZ"]) * big
        elif key == "JX":
            ok = rel(a[key], ref) < 2e-3
        else:
            ok = rel(a[key], ref) < 1e-5
        check("{0}: Code-Aster {1}".format(name, key), ok, (a[key], ref))

# --- 5. thin walls: elements across the wall ---------------------------------
def count_across(m, p0, p1, n=600):
    X = m["nodes"][m["elements"][:, :3]]
    hit = set()
    for t in np.linspace(0.002, 0.998, n):
        p = p0 + t * (p1 - p0)
        a, b, c = X[:, 0], X[:, 1], X[:, 2]

        def s(u, v):
            return (v[:, 0] - u[:, 0]) * (p[1] - u[:, 1]) - (v[:, 1] - u[:, 1]) * (p[0] - u[:, 0])
        hit.update(np.nonzero((s(a, b) >= 0) & (s(b, c) >= 0) & (s(c, a) >= 0))[0].tolist())
    return len(hit)


for t in (1e-3, 1e-4):
    m = sm.mesh_section([channel(0.1, 0.05, t, t)])
    n1 = count_across(m, np.array([0.025, 0.0]), np.array([0.025, t]))
    n2 = count_across(m, np.array([0.0, 0.05]), np.array([t, 0.05]))
    check("thin channel t = size/{0:g}: >= 4 elements across ({1}, {2})".format(0.1 / t, n1, n2),
          min(n1, n2) >= 4)
m = sm.mesh_section(SHAPES["box_thin"])
n1 = count_across(m, np.array([0.1, 0.0]), np.array([0.1, 0.002]))
check("thin box: >= 4 elements across ({0})".format(n1), n1 >= 4)

# --- 6. robustness -------------------------------------------------------------
rng = np.random.RandomState(1)
noisy = [(np.asarray(l) + rng.normal(0, 1e-9 * 0.2, np.asarray(l).shape)).tolist()
         for l in SHAPES["channel"]]
r = sa.run_analysis({"loops": noisy})
check("noisy loops (1e-9): area", rel(r["area"], 3.2295e-3) < 1e-6, r["area"])
check("noisy loops: J", rel(r["j"], SP["channel"]["j"]) < 5e-3, r["j"])

r = sa.run_analysis({"loops": [rect(0.1, 0.1), rect(0.1, 0.1, 0.1, 0.0)]})
check("two adjacent faces (shared edge cancels): one part", r["n_parts"] == 1 and
      rel(r["area"], 0.02) < 1e-12 and r["warping_computed"], (r["n_parts"], r["area"]))
check("two adjacent faces: same J as one rectangle",
      rel(r["j"], beta * 0.2 * 0.1 ** 3) < 1e-4, r["j"])
r = sa.run_analysis({"loops": [rect(0.2, 0.1), rect(0.1, 0.05, 0.0, 0.1),
                               rect(0.1, 0.05, 0.1, 0.1)]})
check("T-junction of three faces: one part, area", r["n_parts"] == 1 and
      rel(r["area"], 0.03) < 1e-12, (r["n_parts"], r["area"]))
r = sa.run_analysis({"loops": [rect(0.2, 0.2), rect(0.16, 0.16, 0.02, 0.02),
                               rect(0.08, 0.08, 0.06, 0.06)]})
check("island in a hole: area, 2 parts, warping skipped", rel(r["area"], 0.0208) < 1e-12 and
      r["n_parts"] == 2 and not r["warping_computed"] and "separate" in r["warping_note"])
check("island in a hole: perimeter = outer + island", rel(r["perimeter"], 0.8 + 0.32) < 1e-12,
      r["perimeter"])
r = sa.run_analysis({"loops": [[[0, 0], [0.1, 0], [0.1, 0.1 * math.tan(math.radians(5))]]]})
check("5 degree wedge: meshes, area", rel(r["area"], 0.5 * 0.01 * math.tan(math.radians(5))) < 1e-12)
r = sa.run_analysis({"loops": [rect(0.1, 0.2) + [[0.0, 0.0]]]})
check("closing point repeated", rel(r["area"], 0.02) < 1e-12)
m = sm.mesh_section([rect(0.1, 0.1)], max_area=1e-5)
X = m["nodes"][m["elements"][:, :3]]
ar = 0.5 * np.abs((X[:, 1, 0] - X[:, 0, 0]) * (X[:, 2, 1] - X[:, 0, 1]) -
                  (X[:, 2, 0] - X[:, 0, 0]) * (X[:, 1, 1] - X[:, 0, 1]))
check("mesh_size: every element area <= max area", ar.max() <= 1e-5 * (1 + 1e-9), ar.max())
r = sa.run_analysis({"loops": [rect(0.1, 0.1)], "mesh_size": 1e-5})
check("mesh_size passed through", r["n_elements"] == len(m["elements"]), r["n_elements"])

# --- 7. CLI: out.json always written ------------------------------------------
tmp = tempfile.mkdtemp()
try:
    inp = os.path.join(tmp, "in.json")
    out = os.path.join(tmp, "out.json")
    with open(inp, "w") as f:
        json.dump({"loops": [rect(0.1, 0.2)], "nu": 0.3, "heal": {"x": 1}}, f)
    rc = sa.main([inp, out])
    with open(out) as f:
        res = json.load(f)
    check("CLI: success, nu passed, heal copied", rc == 0 and res["success"] and
          res["nu"] == 0.3 and res["heal"] == {"x": 1} and "aster" in res and res["loops"])
    with open(inp, "w") as f:
        json.dump({"loops": [[[0, 0], [1, 0]]]}, f)
    rc = sa.main([inp, out])
    with open(out) as f:
        res = json.load(f)
    check("CLI: failure gives success false + error + traceback",
          rc != 0 and res["success"] is False and res["error"] and res["traceback"])
    # step route (needs Scripts/section_step.py and the test STEP file)
    step_file = os.path.join(_HERE, "data", "section_step", "tube.step")
    try:
        import section_step  # noqa: F401
        have_step = os.path.exists(step_file)
    except ImportError:
        have_step = False
    if have_step:
        with open(inp, "w") as f:
            json.dump({"step": {"file": step_file, "normal": [0, 0, 1], "offset": 0.0,
                                "u": [1, 0, 0], "v": [0, 1, 0], "points": [[0.0275, 0, 0]],
                                "tol": 1e-7}}, f)
        rc = sa.main([inp, out])
        with open(out) as f:
            res = json.load(f)
        ok = rc == 0 and res["success"]
        check("step route: tube.step", ok, res.get("error"))
        if ok:
            ja = math.pi / 2 * (0.03 ** 4 - 0.025 ** 4)
            check("step route: face_ids, gaps_closed", len(res["face_ids"]) == 1 and
                  res["gaps_closed"] == [])
            check("step route: J of the tube (1e-4)", rel(res["j"], ja) < 1e-4, (res["j"], ja))
            check("step route: dense arcs, element count < 8000", res["n_elements"] < 8000,
                  res["n_elements"])
    else:
        print("---  step route skipped (section_step or test data missing)")
finally:
    shutil.rmtree(tmp)

# --- 8. speed -------------------------------------------------------------------
t1 = time.time()
r = sa.run_analysis({"loops": SHAPES["ibeam_fillet"]})
dt = time.time() - t1
check("speed: I with fillets in < 3 s ({0:.2f} s)".format(dt), dt < 3.0)
print("total {0:.1f} s".format(time.time() - t0))

sys.exit(1 if check.failed else 0)
