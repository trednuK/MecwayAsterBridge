# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of bridge_section_stress and of its call in
# aster_results_export, without Code-Aster. Reruns itself with a Python that has
# numpy and scipy (Code-Aster's). The real runs: TestFiles/Verificatie
# (tests_balk_spanning.py).
#
#   python tests/test_bridge_section_stress.py

from __future__ import print_function

import glob
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
sys.dont_write_bytecode = True
try:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
except ImportError:
    pats = glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""),
                                  "code_aster", "*", "*", "Python*",
                                  "python.exe"))
    if not pats:
        print("no Python with numpy and scipy found")
        sys.exit(2)
    sys.exit(subprocess.call([sorted(pats)[-1], os.path.abspath(__file__)]))

import numpy as np  # noqa: E402
import aster_results_export as are  # noqa: E402
import bridge_section_stress as bss  # noqa: E402
import section_profiles  # noqa: E402
import section_stress as ss  # noqa: E402

TMP = tempfile.mkdtemp(prefix="section_stress_")
FAILED = []
COUNT = [0]


def check(name, ok, detail=""):
    print(("OK   " if ok else "FOUT ") + name +
          (" ({0})".format(detail) if detail != "" else ""))
    COUNT[0] += 1
    if not ok:
        FAILED.append(name)


def near(a, b, tol):
    return abs(a - b) <= tol * max(abs(b), 1e-300)


# ==========================================
# THE COPIES
# ==========================================
def source_folder():
    """Scripts of MecwayAdvancedBeamAnalysis next to this repository (a folder
    above it holds that repository), or None. Elsewhere there is nothing to
    compare with: the bridge itself never needs it."""
    env = os.environ.get("BEAM_ANALYSIS_SCRIPTS")
    if env:
        return env
    here = os.path.abspath(_HERE)
    while True:
        up = os.path.dirname(here)
        if up == here:
            return None
        here = up
        path = os.path.join(here, "MecwayAdvancedBeamAnalysis", "Scripts")
        if os.path.isdir(path):
            return path


def test_copies():
    print("-- copies against their source")
    source = source_folder()
    if source is None:
        print("     source not present, copies not compared")
        return
    for name in ("section_stress.py", "section_fem.py", "section_mesh.py",
                 "section_profiles.py"):
        with io.open(os.path.join(source, name), encoding="utf-8") as f:
            theirs = f.read()
        with io.open(os.path.join(_HERE, "..", "Scripts", name),
                     encoding="utf-8") as f:
            ours = f.read()
        check(name + " is an unchanged copy", theirs == ours)


# ==========================================
# MODELS
# ==========================================
# T: flange 100 x 8, web 6 wide, in principal axes about the centroid
T_DRAWING = [(-0.05, 0.0), (0.05, 0.0), (0.05, 0.008), (0.003, 0.008),
             (0.003, 0.1), (-0.003, 0.1), (-0.003, 0.008), (-0.05, 0.008)]


def centred(points):
    field = ss.SectionField([points], nu=0.3, n_target=800)
    c = field.centroid
    return [(p[0] - c[0], p[1] - c[1]) for p in points], field.mesh_props


T_LOOP, T_PROPS = centred(T_DRAWING)
GENERAL = (u'<geometric type="UniformGeneralSection" area="{A!r} m²" '
           u'iyy="{ivv!r} m⁴" izz="{iww!r} m⁴" torsionconstant="1e-08 m⁴" '
           u'perimeter="0.3 m" />').format(**T_PROPS)
STEEL = (u'<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         u'poissonratio="0.3" />')
PROFILE = u'<geometric type="I" ia="100 mm" ib="50 mm" ic="10 mm" id="8 mm" />'
RECT = u'<geometric type="RectBar" recta="40 mm" rectb="10 mm" />'


def shape_lines(name, loop, area, extra=u""):
    flat = u" ".join(u"%r" % c for p in loop for c in p)
    return (u"** SECTIE-VORM {0}: N={1}, A={2!r}\n** SECTIE-VORM {0}: P={3}\n"
            .format(name, len(loop), area, flat)) + extra


def write_model(name, mats, elsets, custom=u""):
    """mats: {material: inner xml}; elsets: [(material, [eid, ...])]. Every
    element is a line2 from node 1 to node 2; the numbers do not matter here."""
    lines = [u'<liml version="35">', u'  <analysis type="S30" />',
             u'  <node nid="1" x="0" y="0" z="0" />',
             u'  <node nid="2" x="1" y="0" z="0" />']
    for k, (material, eids) in enumerate(elsets):
        lines.append(u'  <elset name="E{0}" material="{1}">'.format(k, material))
        lines += [u'    <elem eid="%d" shape="line2" nodes="1 2" />' % e
                  for e in eids]
        lines.append(u"  </elset>")
    for mat, inner in mats.items():
        lines.append(u'  <mat name="{0}">{1}</mat>'.format(mat, inner))
    if custom:
        lines.append(u"  <ccxmodeldefinition>{0}</ccxmodeldefinition>"
                     .format(custom))
    # a solution that is not read: bad on purpose after <solution>
    lines += [u"  <solution>", u"  </solution>", u"</liml>"]
    path = os.path.join(TMP, name + ".liml")
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(u"\n".join(lines))
    return path


def run_plan(liml, eids, forces=bss.FORCE_NAMES, shape="line2"):
    size = 2 if shape == "line2" else 3
    elements = dict((e, (shape, list(range(1, size + 1)))) for e in eids)
    out = os.path.join(TMP, os.path.basename(liml)[:-5] + "_1_results.xml")
    ids = dict((name, np.array(sorted(eids), dtype="<i4")) for name in forces)
    plan, notes = bss.plan(liml, out, elements, ids)
    return plan, notes, out[:-len("_results.xml")] + "_section.json", elements


def extremes(field, forces, name):
    return abs(field.extremes(ss.measures(field.stress(forces))[name])
               ["outside"]["value"])


# ==========================================
# THE MAXIMA
# ==========================================
def test_maxima_against_the_field():
    print("-- maxima against SectionField on element nodes")
    path = write_model("t1", {"T": GENERAL + STEEL}, [("T", [1, 2])],
                       shape_lines("T", T_LOOP, T_PROPS["A"]))
    plan, notes, _sidecar, elements = run_plan(path, [1, 2])
    check("no warnings", notes == [], notes)
    field = ss.SectionField([T_LOOP], nu=0.3, props=dict(T_PROPS, ivw=0.0))
    rng = np.random.RandomState(1)
    raw = rng.normal(size=(4, 6)) * [2e3, 1e3, 1e3, 30.0, 300.0, 300.0]
    # flat arrays per force: eid 1 end 1, end 2, eid 2 end 1, end 2
    got = plan.values([raw[:, k] for k in range(6)])
    worst = 0.0
    names = ("N", "Vv", "Vw", "T", "Mv", "Mw")
    for i in range(4):
        forces = dict(zip(names, raw[i]))
        for var, measure in ((bss.VON_MISES, "vonmises"), (bss.SIGMA, "sigma"),
                             (bss.TAU, "tau")):
            worst = max(worst, abs(got[var][i] - extremes(field, forces, measure))
                        / extremes(field, forces, measure))
    check("within 0.5 % of the element-node maximum", worst < 0.005, worst)
    forces = {"N": 1000.0}
    got = plan.values([np.full(4, 1000.0)] + [np.zeros(4)] * 5)
    check("pure N: N/A", near(got[bss.SIGMA][0], 1000.0 / T_PROPS["A"], 1e-12))
    check("pure N: von Mises = sigma",
          near(got[bss.VON_MISES][0], 1000.0 / T_PROPS["A"], 1e-12))
    check("pure N: no shear", got[bss.TAU][0] == 0.0)
    moment = np.zeros(4)
    moment[1] = 100.0
    got = plan.values([np.zeros(4), np.zeros(4), np.zeros(4), np.zeros(4),
                       moment, np.zeros(4)])
    wmax = max(abs(p[1]) for p in T_LOOP)
    check("pure Mv at one end: M c / I there, zero at the others",
          near(got[bss.SIGMA][1], 100.0 * wmax / T_PROPS["ivv"], 1e-12) and
          got[bss.SIGMA][0] == 0.0 and got[bss.SIGMA][2] == 0.0)


def test_torque_term():
    print("-- T_S: the same stress for V at S and for V at G plus the torque")
    path = write_model("u1", {"U": GENERAL + STEEL}, [("U", [1])],
                       shape_lines("U", T_LOOP, T_PROPS["A"]))
    plan, _n, _s, _e = run_plan(path, [1])
    section = plan.groups[0][0]
    ey, ez = section.field.offset
    v = 500.0
    # The T is symmetric about W with S in the flange, so EZ != 0 and EY = 0:
    # the term of Vv is -EZ Vv, and a torque of EZ Vv takes it away.
    with_term = np.zeros((1, 6))
    with_term[0, 1] = v
    cancelled = with_term.copy()
    cancelled[0, 3] = ez * v
    shear = section.shear_forces(cancelled)
    check("the term is -EZ Vv and a torque can cancel it",
          abs(ez) > 1e-3 and near(shear[0, 2] + 1.0, 1.0, 1e-12))
    pure = np.array([[0.0, v, 0.0, 0.0, 0.0, 0.0]])
    check("with T_S = 0 the shear is that of the unit field alone",
          near(section.maxima(cancelled)[2][0],
               v * np.hypot(section.tau_v[0], section.tau_w[0]).max(), 1e-12))
    check("without the torque it differs",
          not near(section.maxima(pure)[2][0], section.maxima(cancelled)[2][0],
                   0.05))
    extra = u"** ASTER-SECTIE U: A={A!r}, IY={ivv!r}, IZ={iww!r}, JX=1e-08, " \
            u"AY=1, AZ=1, EY=0.02, EZ=-0.03, JG=1e-10, IYR2=0, IZR2=0\n" \
        .format(**T_PROPS)
    path = write_model("u2", {"U": GENERAL + STEEL}, [("U", [1])],
                       shape_lines("U", T_LOOP, T_PROPS["A"], extra))
    plan, notes, sidecar, _e = run_plan(path, [1])
    section = plan.groups[0][0]
    check("#ASTER-SECTIE counts", tuple(section.field.offset) == (0.02, -0.03),
          section.field.offset)
    with open(sidecar) as f:
        entry = json.load(f)["sections"][0]
    check("and goes to the table", entry["EY"] == 0.02 and entry["EZ"] == -0.03)
    shear = section.shear_forces(np.array([[0.0, 2.0, 3.0, 5.0, 0.0, 0.0]]))
    check("T_S = T + EY Vw - EZ Vv",
          near(shear[0, 2], 5.0 + 0.02 * 3.0 + 0.03 * 2.0, 1e-12))


# ==========================================
# THE TABLE OF THE SHELLS
# ==========================================
def test_table():
    print("-- the table for the shells")
    path = write_model("t2", {"T": GENERAL + STEEL}, [("T", [1])],
                       shape_lines("T", T_LOOP, T_PROPS["A"]))
    plan, _notes, sidecar, _e = run_plan(path, [1])
    section = plan.groups[0][0]
    with open(sidecar) as f:
        data = json.load(f)
    check("sidecar: version and one section",
          data["version"] == 1 and len(data["sections"]) == 1)
    entry = data["sections"][0]
    rows = entry["points"]
    check("every outline point has a row", all(
        any(abs(r[0] - p[0]) + abs(r[1] - p[1]) < 1e-12 for r in rows)
        for p in T_LOOP))
    check("the loops are what it was made for", [tuple(p) for p in
                                                 entry["loops"][0]] == T_LOOP)
    field = section.field
    inner = [r for r in rows if len(r) == 14]
    check("two exits at the two re-entrant corners, none elsewhere",
          len(field.corners) == 2 and len(inner) >= 2 and
          set(len(r) for r in rows) == set((8, 14)), len(inner))
    plain = [r for r in rows if len(r) == 8][0]
    nodes = field.nodes
    node = int(np.argmin(np.hypot(nodes[:, 0] - plain[0],
                                  nodes[:, 1] - plain[1])))
    check("a row is the nodal average of the unit fields",
          plain[2] == field.nodal(field.fields["vv"][:, :, 0])[node] and
          plain[7] == field.nodal(field.fields["t"][:, :, 1])[node])
    corner = field.corners[0]
    point = corner[0] + field.centroid
    row = [r for r in inner if abs(r[0] - point[0]) < 1e-9 and
           abs(r[1] - point[1]) < 1e-9]
    check("the corner vertex is one of them", len(row) == 1)
    # both exits are about one thickness from the corner
    walk = bss._Boundary(field.elements)
    start = walk.nodes[int(np.argmin(np.hypot(
        nodes[walk.nodes, 0] - point[0], nodes[walk.nodes, 1] - point[1])))]
    exits = walk.exits(int(start), section.outside)
    gaps = [float(np.hypot(*(nodes[n] - point))) for n in exits]
    check("two exits, just outside r = 1 t", len(exits) == 2 and
          all(corner[1] < g < 1.5 * corner[1] for g in gaps), gaps)


# ==========================================
# WHAT IS SKIPPED, AND WHAT THEN STILL WORKS
# ==========================================
def test_paths():
    print("-- paths without a result")
    path = write_model("no_shape", {"G": GENERAL + STEEL}, [("G", [1])])
    plan, notes, sidecar, _e = run_plan(path, [1])
    check("general section without a shape: WARNING, no plan",
          plan is None and len(notes) == 1 and "WARNING" in notes[0] and
          "'G'" in notes[0], notes)
    with open(sidecar) as f:
        check("and the warning is in the sidecar for the log",
              json.load(f)["warnings"] == notes)

    path = write_model("stale", {"G": GENERAL + STEEL}, [("G", [1])],
                       shape_lines("G", T_LOOP, T_PROPS["A"] * 1.1))
    plan, notes, _s, _e = run_plan(path, [1])
    check("stale shape: the same", plan is None and len(notes) == 1, notes)

    plastic = STEEL[:-3] + (u'><plastic type="Isotropic" /></mechanical>')
    path = write_model("plastic", {"G": GENERAL + plastic}, [("G", [1])],
                       shape_lines("G", T_LOOP, T_PROPS["A"]))
    plan, notes, _s, _e = run_plan(path, [1])
    check("plastic: WARNING, no plan", plan is None and len(notes) == 1 and
          "elastic" in notes[0], notes)

    path = write_model("rect", {"R": RECT + STEEL}, [("R", [1])])
    plan, notes, sidecar, _e = run_plan(path, [1])
    check("rectangle: nothing, not even a file (beamsixxmin/max stay)",
          plan is None and notes == [] and not os.path.exists(sidecar))

    no_nu = u'<mechanical type="Isotropic" youngsmodulus="210000 MPa" />'
    path = write_model("no_nu", {"G": GENERAL + no_nu}, [("G", [1])],
                       shape_lines("G", T_LOOP, T_PROPS["A"]))
    plan, notes, _s, _e = run_plan(path, [1])
    check("no poissonratio: nu = 0, as the bridge gives Code-Aster",
          plan is not None and notes == [] and
          plan.groups[0][0].field.nu == 0.0, notes)

    path = write_model("no_force", {"G": GENERAL + STEEL}, [("G", [1])],
                       shape_lines("G", T_LOOP, T_PROPS["A"]))
    plan, notes, _s, _e = run_plan(path, [1], forces=bss.FORCE_NAMES[:3])
    check("no beam_forces: WARNING that names it", plan is None and
          "beam_forces" in notes[0], notes)

    two = T_LOOP + []
    other = [(p[0] + 1.0, p[1]) for p in T_LOOP]
    flat = u" ".join(u"%r" % c for p in two + other for c in p)
    area = 2.0 * T_PROPS["A"]
    custom = (u"** SECTIE-VORM G: N={0} {0}, A={1!r}\n** SECTIE-VORM G: P={2}\n"
              .format(len(two), area, flat))
    geo = GENERAL.replace(u"%r m²" % T_PROPS["A"], u"%r m²" % area)
    path = write_model("parts", {"G": geo + STEEL}, [("G", [1])], custom)
    plan, notes, _s, _e = run_plan(path, [1])
    check("several parts: sigma only, with a WARNING",
          plan is not None and
          [v[0] for v in plan.variables] == [bss.SIGMA] and len(notes) == 1,
          notes)
    got = plan.values([np.ones(2)] + [np.zeros(2)] * 5)
    check("and values", near(got[bss.SIGMA][0], 1.0 / area, 1e-9))

    saved = sys.modules.pop("section_stress")
    sys.modules["section_stress"] = None
    try:
        path = write_model("no_scipy", {"G": GENERAL + STEEL}, [("G", [1])],
                           shape_lines("G", T_LOOP, T_PROPS["A"]))
        plan, notes, sidecar, _e = run_plan(path, [1])
    finally:
        sys.modules["section_stress"] = saved
    check("no scipy: WARNING, no plan, the run goes on", plan is None and
          "numpy/scipy" in notes[0], notes)
    check("and the sidecar says so", os.path.exists(sidecar))

    path = write_model("mixed", {"G": GENERAL + STEEL, "R": RECT + STEEL},
                       [("G", [1, 3]), ("R", [2])],
                       shape_lines("G", T_LOOP, T_PROPS["A"]))
    plan, notes, _s, elements = run_plan(path, [1, 2, 3])
    check("a beam without a section stays out of the ids",
          [list(v[1]) for v in plan.variables] == [[1, 3]] * 3, plan.variables)
    forces = [np.zeros(6) for _ in range(6)]
    forces[0][:] = [1.0, 1.0, 9.0, 9.0, 1.0, 1.0]
    got = plan.values(forces)
    check("and its forces do not count",
          len(got[bss.SIGMA]) == 4 and
          near(got[bss.SIGMA][3], 1.0 / T_PROPS["A"], 1e-12))


def test_shapes_and_layout():
    print("-- line3, partial forces, order")
    path = write_model("l3", {"G": GENERAL + STEEL}, [("G", [1, 2])],
                       shape_lines("G", T_LOOP, T_PROPS["A"]))
    plan, _n, _s, _e = run_plan(path, [1, 2], shape="line3")
    size = plan.sizes[bss.SIGMA]
    normal = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    got = plan.values([normal] + [np.zeros(6)] * 5)
    check("line3: a value per node, in order", size == 6 and all(
        near(got[bss.SIGMA][k], normal[k] / T_PROPS["A"], 1e-12)
        for k in range(6)))
    head = bss.read_head(path)
    check("reading stops at <solution>, elsets and materials are there",
          head["elsets"] == [("G", [1, 2])] and len(head["mats"]) == 1 and
          len(head["texts"]) == 1)
    elements = {1: ("line2", [1, 2]), 2: ("line2", [1, 2])}
    ids = dict((name, np.array([1, 2], dtype="<i4"))
               for name in bss.FORCE_NAMES)
    ids["torsion"] = np.array([2], dtype="<i4")
    out = os.path.join(TMP, "l3_2_results.xml")
    plan, _n = bss.plan(path, out, elements, ids)
    check("a beam that lacks one force is left out",
          [list(v[1]) for v in plan.variables] == [[2]] * 3)
    arrays = [np.array([9.0, 9.0, 1.0, 1.0])] + \
        [np.zeros(4) for _ in range(5)]
    arrays[3] = np.zeros(2)         # torsion only on element 2
    got = plan.values(arrays)
    check("and the other forces are taken at the right place",
          near(got[bss.SIGMA][0], 1.0 / T_PROPS["A"], 1e-12))


def test_mixed_sections():
    print("-- different sections, partial forces, line3 together")
    two = T_LOOP + [(p[0] + 1.0, p[1]) for p in T_LOOP]
    flat = u" ".join(u"%r" % c for p in two for c in p)
    area = 2.0 * T_PROPS["A"]
    custom = shape_lines("T", T_LOOP, T_PROPS["A"]) + (
        u"** SECTIE-VORM P: N={0} {0}, A={1!r}\n** SECTIE-VORM P: P={2}\n"
        .format(len(T_LOOP), area, flat))
    parts = GENERAL.replace(u"%r m²" % T_PROPS["A"], u"%r m²" % area)
    path = write_model("mix", {"T": GENERAL + STEEL, "P": parts + STEEL,
                               "I": PROFILE + STEEL, "R": RECT + STEEL},
                       [("T", [1, 5]), ("P", [2]), ("I", [3]), ("R", [4]),
                        ("T", [6])], custom)
    elements = {1: ("line2", [1, 2]), 2: ("line2", [1, 2]),
                3: ("line3", [1, 3, 2]), 4: ("line2", [1, 2]),
                5: ("line2", [1, 2]), 6: ("line2", [1, 2])}
    ids = dict((name, np.array([1, 2, 3, 4, 5, 6], dtype="<i4"))
               for name in bss.FORCE_NAMES)
    ids["torsion"] = np.array([1, 2, 3, 4, 6], dtype="<i4")     # not on 5
    out = os.path.join(TMP, "mix_1_results.xml")
    plan, notes = bss.plan(path, out, elements, ids)
    names = dict((n, list(e)) for n, e in plan.variables)
    check("sigma on all with a section and all forces",
          names[bss.SIGMA] == [1, 2, 3, 6], names)
    check("shear not on the section of two parts",
          names[bss.TAU] == [1, 3, 6] and names[bss.VON_MISES] == [1, 3, 6],
          names)
    check("one warning, of the two parts", len(notes) == 1 and "'P'" in notes[0],
          notes)
    # flat: eid 1, 2, 4, 5, 6 two values, eid 3 three; torsion not on 5
    arrays = [np.arange(1.0, 14.0)] + [np.zeros(13) for _ in range(5)]
    arrays[3] = np.zeros(11)
    got = plan.values(arrays)
    from bridge_from_liml import _profile_props
    area_i = _profile_props("I", 0.1, 0.05, 0.01, 0.008)[0]
    want = [1.0 / T_PROPS["A"], 2.0 / T_PROPS["A"], 3.0 / area, 4.0 / area,
            5.0 / area_i, 6.0 / area_i, 7.0 / area_i, 12.0 / T_PROPS["A"],
            13.0 / T_PROPS["A"]]
    check("every value at its place, N/A", len(got[bss.SIGMA]) == len(want) and
          all(near(a, b, 1e-9) for a, b in zip(got[bss.SIGMA], want)),
          list(got[bss.SIGMA]))
    check("the shear variables have their own layout",
          len(got[bss.TAU]) == 7 and len(got[bss.VON_MISES]) == 7)


def test_profiles():
    print("-- I, T, L, C of the bridge against the outline of the copy")
    from bridge_from_liml import _profile_props
    cases = [("I", (0.1, 0.05, 0.01, 0.008)), ("T", (0.1, 0.01, 0.01, 0.09)),
             ("C", (0.05, 0.1, 0.006, 0.006)), ("L", (0.08, 0.05, 0.008, 0.0))]
    for kind, dims in cases:
        p = kind.lower()
        attrs = dict((p + k, repr(v)) for k, v in zip("abcd", dims) if v)
        attrs["type"] = kind
        area, iy, iz, _j = _profile_props(kind, *dims)
        field = ss.SectionField(section_profiles.loops_for(attrs)["loops"],
                                nu=0.3, n_target=800)
        got = field.mesh_props
        check(kind + ": A, Iy, Iz agree", near(got["A"], area, 1e-9) and
              near(got["ivv"], iy, 1e-6) and near(got["iww"], iz, 1e-6),
              (got["ivv"], iy, got["iww"], iz))
        check(kind + ": axes are principal axes", abs(got["ivw"]) < 1e-6 * iy,
              got["ivw"])


def test_cost():
    print("-- cost on a chain of thousands of beams")
    count = [0]
    real = ss.SectionField

    class Counted(real):
        def __init__(self, *a, **k):
            count[0] += 1
            real.__init__(self, *a, **k)

    ss.SectionField = Counted
    try:
        n = 5000
        eids = list(range(1, n + 1))
        mats = dict(("M%d" % k, GENERAL + STEEL) for k in range(3))
        custom = u"".join(shape_lines("M%d" % k, T_LOOP, T_PROPS["A"])
                          for k in range(3))
        path = write_model("chain", mats, [("M0", eids[:1000]),
                                           ("M1", eids[1000:2000]),
                                           ("M2", eids[2000:])], custom)
        t0 = time.time()
        plan, notes, _s, _e = run_plan(path, eids)
        built = time.time() - t0
    finally:
        ss.SectionField = real
    check("one SectionField for 5000 beams and three equal materials",
          count[0] == 1 and len(plan.groups) == 1, count[0])
    rng = np.random.RandomState(2)
    arrays = [rng.normal(size=2 * n) * s
              for s in (1e3, 1e3, 1e3, 30.0, 300.0, 300.0)]
    t0 = time.time()
    plan.values(arrays)
    used = time.time() - t0
    print("     plan {0:.2f} s, one step of 10,000 ends {1:.2f} s".format(
        built, used))
    check("one step of 5000 beams stays below 5 s", used < 5.0, used)


# ==========================================
# THE CALL IN aster_results_export
# ==========================================
class FakeFields(object):
    """What the getters need of aster_results_export._Fields."""

    def __init__(self):
        self.data = {}


def make_var(name, element, ids, values):
    calls = []

    def getter(_fields):
        calls.append(1)
        return values
    var = are._Var(name, element, np.array(ids, dtype="<i4"), getter)
    var.calls = calls
    return var


def test_call():
    print("-- _section_stress_vars")
    path = write_model("call", {"G": GENERAL + STEEL}, [("G", [1])],
                       shape_lines("G", T_LOOP, T_PROPS["A"]))
    model = {"elements": {1: ("line2", [1, 2])}}
    out = os.path.join(TMP, "call_1_results.xml")
    # a nodal tensileforce with the same name comes first in the list
    variables = [make_var("tensileforce", False, [1, 2],
                          np.array([7.0, 7.0]))]
    variables += [make_var("displx", False, [1, 2], np.zeros(2))]
    variables += [make_var(n, True, [1], np.array([1.0, 2.0]) if k == 0
                           else np.zeros(2))
                  for k, n in enumerate(bss.FORCE_NAMES)]
    new = are._section_stress_vars(variables, model, path, out)
    check("three variables", [v.name for v in new] ==
          ["beamvonmisesmax", "beamsixxabsmax", "beamtaumax"] and
          all(v.element for v in new))
    fields = FakeFields()
    got = [v.getter(fields) for v in new]
    check("from the element values, not the nodal ones",
          near(got[1][1], 2.0 / T_PROPS["A"], 1e-12))
    check("computed once per step", variables[2].calls == [1])
    fields.data.clear()
    new[0].getter(fields)
    check("and again in the next step", variables[2].calls == [1, 1])

    missing = [make_var("displx", False, [1, 2], np.zeros(2))]
    missing += [make_var(n, True, [1], np.zeros(2)) for n in bss.FORCE_NAMES]
    missing[3].getter = lambda f: None
    new = are._section_stress_vars(missing, model, path, out)
    check("a force missing in a step: None, as other variables",
          new[0].getter(FakeFields()) is None)
    check("no displacement (thermal): nothing, no warning",
          are._section_stress_vars(variables[2:], model, path, out) == [])

    model = {"elements": {1: ("hex8", list(range(1, 9)))}}
    check("no beams: nothing", are._section_stress_vars(
        [], model, "does not exist", out) == [])
    model = {"elements": {1: ("line2", [1, 2])}}
    new = are._section_stress_vars(variables, model, os.path.join(
        TMP, "does_not_exist.liml"), out)
    check("an error costs these variables only", new == [])


def main():
    test_copies()
    test_maxima_against_the_field()
    test_torque_term()
    test_table()
    test_paths()
    test_shapes_and_layout()
    test_mixed_sections()
    test_profiles()
    test_cost()
    test_call()
    shutil.rmtree(TMP, ignore_errors=True)
    print("{0} checks".format(COUNT[0]))
    if FAILED:
        print("FOUT: " + "; ".join(FAILED))
        sys.exit(1)
    print("Alle controles OK")


if __name__ == "__main__":
    main()
