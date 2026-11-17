# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Contact in 2D and axisymmetric (STAPPENPLAN S44b, route A; Scripts/
bridge_plane.py, bridge_mesh.py): Mecway Nonlinear Static (L30) with plane
shell elements, '**ASTER-PLANE' and a Contact between face selections of
shell edges -> DEFI_CONTACT on SEG boundary cells of C_PLAN/D_PLAN/AXIS.
Explanation: docs/Verificatie.md chapter 2D and axisymmetric (PL).

PL-40  shrink fit of two rings (AXIS): inner ring a .. b + delta, outer ring
       b .. c, both ends of both rings held axially (plane strain),
       frictionless: the contact pressure against Lame (plane strain,
       p = delta / (f_i + f_o)).
PL-41  the same in plane strain (D_PLAN, quarter rings, symmetry x = 0 and
       y = 0).
PL-42  Code-Aster test case ssnp121a (two blocks, D_PLAN, non-matching).
PL-43  the same in C_PLAN (nu = 0: the same state).
PL-45  Hertz line contact of a cylinder on a block (D_PLAN).
PL-46  Coulomb friction: a block sliding over a block (D_PLAN).
"""
import math

from verif_lib import Case, Check, Model, quadmesh, rect

GROUP = "2D en axisymmetrisch"
E, NU = 210e9, 0.3
RA, RB, RC, H = 0.10, 0.15, 0.20, 0.01
DELTA = 5.0e-5              # radial interference
NR = 8                      # quad8 through each wall
STEEL = ('<geometric type="Plate" thickness="10 mm" />',
         '<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
TS = {"timeperiod": "1 s", "stepsize": "1 s"}


def _u_per_p(r, a, b, inner):
    """Radial displacement at r of a ring a .. b per unit pressure on its
    inner (inner=True) or outer wall; Lame, plane strain."""
    pi, po = (1.0, 0.0) if inner else (0.0, 1.0)
    A = (pi * a ** 2 - po * b ** 2) / (b ** 2 - a ** 2)
    B = (pi - po) * a ** 2 * b ** 2 / (b ** 2 - a ** 2)
    return (1.0 + NU) / E * ((1.0 - 2.0 * NU) * A * r + B / r)


# inner ring: outer pressure p shrinks it; outer ring: inner pressure p
P_FIT = DELTA / (-_u_per_p(RB, RA, RB, False) + _u_per_p(RB, RB, RC, True))


def _contact(m):
    m.add('<contact2 selectionmaster="Buitenring_binnen" selectionslave='
          '"Binnenring_buiten" type="unilateralelastic"><tolerance>0 m'
          '</tolerance><normalstiffness>1000 GPa/m</normalstiffness>'
          '<tangentialstiffness>0 GPa/m</tangentialstiffness>'
          '<frictioncoefficient>0</frictioncoefficient></contact2>')


def _finish(m, mod):
    m.add(u"<ccxmodeldefinition>**ASTER-PLANE %s</ccxmodeldefinition>" % mod)
    # Mecway's own outline names only: an unknown name ("contact") gives
    # the box 'Invalid fieldvariable name' when the model is opened in
    # Mecway 35 (user, 17 Nov 2026). The bridge writes contactpressure
    # without a fieldvariable; Mecway adds it when it saves the result.
    for fv in ("displacement", "stress", "von Mises stress",
               "reaction force"):
        m.add('<fieldvariable name="%s" />' % fv)


def build_pl40(delta=DELTA):
    m = Model("L30", timesteps=TS)
    m.elset("Binnen", "Staal")
    m.elset("Buiten", "Staal")
    qi = quadmesh(m, "Binnen", NR, 1, rect(RA, RB + delta, 0.0, H), order=2)
    qo = quadmesh(m, "Buiten", NR, 1, rect(RB, RC, 0.0, H), order=2)
    m.mat("Staal", *STEEL)
    m.face_selection("Binnenring_buiten", qi["edges"]["u1"])
    m.face_selection("Buitenring_binnen", qo["edges"]["u0"])
    m.node_selection("Slave", sorted(qi["nodes"]["u1"]))
    m.face_selection("Einden", qi["edges"]["v0"] + qi["edges"]["v1"] +
                     qo["edges"]["v0"] + qo["edges"]["v1"])
    m.add('<displacement selection="Einden"><value>0 m</value><x>0</x>'
          '<y>1</y><z>0</z></displacement>')
    _contact(m)
    _finish(m, "AXIS")
    return m


# PL-47: the worked example of the docs (2D_en_axisymmetrisch sec. 1.5,
# example 8): PL-40 with a four times larger interference, 0.2 mm, so that
# the result is visible in Mecway (deformation scale) and every value is
# four times PL-40's (Lame is linear). The checks use the physical names.
DELTA47 = 2.0e-4
P47 = P_FIT * DELTA47 / DELTA


def build_pl47():
    return build_pl40(DELTA47)


def _checks47():
    src = "Lame, overmaat 0,2 mm: p = delta / (f_binnen + f_buiten)"
    t = 1.0
    return [
        Check("contactdruk (gemiddeld, slave)",
              lambda r: r.mean("contactpressure", "Slave", time=t),
              ref=P47, tol=0.01, unit="Pa", source=src),
        Check("hoopstress buitenring binnenwand",
              lambda r: r.at("hoopstress", (RB, 0.0, 0.0), time=t),
              ref=P47 * (RC ** 2 + RB ** 2) / (RC ** 2 - RB ** 2), tol=0.02,
              unit="Pa", source="Lame: p (c^2 + b^2) / (c^2 - b^2)"),
        Check("hoopstress binnenring buitenwand",
              lambda r: r.at("hoopstress", (RB + DELTA47, 0.0, 0.0),
                             time=t),
              ref=-P47 * (RB ** 2 + RA ** 2) / (RB ** 2 - RA ** 2),
              tol=0.02, unit="Pa",
              source="Lame: -p (b^2 + a^2) / (b^2 - a^2)"),
        Check("hoopstress binnenring binnenwand (minimum)",
              lambda r: r.at("hoopstress", (RA, 0.0, 0.0), time=t),
              ref=-2.0 * P47 * RB ** 2 / (RB ** 2 - RA ** 2), tol=0.02,
              unit="Pa", source="Lame: -2 p b^2 / (b^2 - a^2)"),
        Check("radialstress buitenring binnenwand",
              lambda r: r.at("radialstress", (RB, 0.0, 0.0), time=t),
              ref=-P47, tol=0.01, unit="Pa", source="Lame: -p"),
        Check("u_r buitenring binnenwand",
              lambda r: r.at("displx", (RB, 0.0, 0.0), time=t),
              ref=P47 * _u_per_p(RB, RB, RC, True), tol=0.01, unit="m",
              source=src),
        Check("u_r binnenring buitenwand",
              lambda r: r.at("displx", (RB + DELTA47, 0.0, 0.0), time=t),
              ref=P47 * _u_per_p(RB, RA, RB, False), tol=0.01, unit="m",
              source=src)]


def _ring(r0, r1):
    def f(u, v):
        r = r0 + u * (r1 - r0)
        t = v * math.pi / 2
        return (r * math.cos(t), r * math.sin(t), 0.0)
    return f


def build_pl41():
    m = Model("L30", timesteps=TS)
    m.elset("Binnen", "Staal")
    m.elset("Buiten", "Staal")
    qi = quadmesh(m, "Binnen", NR, 8, _ring(RA, RB + DELTA), order=2)
    qo = quadmesh(m, "Buiten", NR, 8, _ring(RB, RC), order=2)
    m.mat("Staal", *STEEL)
    m.face_selection("Binnenring_buiten", qi["edges"]["u1"])
    m.face_selection("Buitenring_binnen", qo["edges"]["u0"])
    m.node_selection("Slave", sorted(qi["nodes"]["u1"]))
    m.face_selection("SymY0", qi["edges"]["v0"] + qo["edges"]["v0"])
    m.face_selection("SymX0", qi["edges"]["v1"] + qo["edges"]["v1"])
    m.add('<symmetry selection="SymY0"><x>0</x><y>1</y><z>0</z>'
          '</symmetry>')
    m.add('<symmetry selection="SymX0"><x>1</x><y>0</y><z>0</z>'
          '</symmetry>')
    _contact(m)
    _finish(m, "D_PLAN")
    return m


def _checks(plane=False):
    """plane: D_PLAN quarter rings; their nodal sigma_r at the contact wall
    is +2.4% (also at 45 degrees: the extrapolation in elements with an
    aspect ratio of about 5, as PL-03 has no sigma_r check), so only the
    contact pressure and u_r there."""
    src = "Lame, vlakke rek: p = delta / (f_binnen + f_buiten)"
    sr = [] if plane else [
        Check("-sigma_r buitenring binnenwand",
              lambda r: -r.at("stressxx", (RB, 0.0, 0.0), time=1.0),
              ref=P_FIT, tol=0.01, unit="Pa", source=src)]
    # 2D: contactpressure on every node, 0 outside the contact (S44,
    # readable 2D results); the hoop stress under its own name (AXIS)
    extra = [
        Check("contactdruk buiten het contact (binnenwand binnenring)",
              lambda r: r.at("contactpressure", (RA, 0.0, 0.0), time=1.0),
              ref=0.0, tol_abs=1e-6 * P_FIT, unit="Pa", in_series=False,
              source="geen contact: 0 (elke knoop heeft een waarde)"),
        Check("contactstatus buiten het contact",
              lambda r: r.at("contactstate", (RA, 0.0, 0.0), time=1.0),
              ref=0.0, tol_abs=1e-9, unit="-", in_series=False,
              source="geen contact: 0")]
    if not plane:
        extra.append(Check(
            "hoopstress buitenring binnenwand",
            lambda r: r.at("hoopstress", (RB, 0.0, 0.0), time=1.0),
            ref=P_FIT * (RC ** 2 + RB ** 2) / (RC ** 2 - RB ** 2), tol=0.02,
            unit="Pa", source="Lame: p (c^2 + b^2) / (c^2 - b^2)"))
    return [
        Check("contactdruk (gemiddeld, slave)",
              lambda r: r.mean("contactpressure", "Slave", time=1.0),
              ref=P_FIT, tol=0.01, unit="Pa", source=src)] + sr + extra + [
        Check("u_r buitenring binnenwand",
              lambda r: r.at("displx", (RB, 0.0, 0.0), time=1.0),
              ref=P_FIT * _u_per_p(RB, RB, RC, True), tol=0.01, unit="m",
              source=src)]


TESTS = [
    Case("PL-40", GROUP, "Krimpverbinding twee ringen, axisymmetrisch "
         "(L30 + **ASTER-PLANE AXIS, contact)", "nonlin_static_3d",
         build_pl40, _checks(),
         note="a = 0,1, b = 0,15, c = 0,2 m, overmaat 0,05 mm, quad8 8x1 "
              "per ring, einden axiaal vast, wrijvingsloos."),
    Case("PL-47", GROUP, "Krimpverbinding twee ringen, overmaat 0,2 mm "
         "(voorbeeld in de documentatie, AXIS)", "nonlin_static_3d",
         build_pl47, _checks47(),
         note="PL-40 met overmaat 0,2 mm: het voorbeeld van de "
              "documentatie, met de fysische namen."),
    Case("PL-41", GROUP, "Krimpverbinding twee ringen, vlakke rek "
         "(L30 + **ASTER-PLANE D_PLAN, contact)", "nonlin_static_3d",
         build_pl41, _checks(plane=True),
         note="Als PL-40 als kwart ringen quad8 8x8, symmetrie x = 0 en "
              "y = 0."),
]


# ------------------------------------------------------------------
# PL-42 Code-Aster test case ssnp121a (D_PLAN, "ecrasement de deux blocs")
# ------------------------------------------------------------------
# Two blocks 2 x 1 m on top of each other (ssnp121a.datg): the upper one
# 12 x 12 quad4 (slave edge AB at y = 0), the lower one 11 x 11 (master EF
# at y = 0), non-matching on the interface; E = 2e6 Pa, nu = 0; the top
# edge CD DX = 0, DY = -0.1 m, the bottom edge GH DX = DY = 0. TEST_RESU
# (VALE_REFE, ANALYTIQUE, PRECISION 1%): LAGS_C = -1e5 (contactpressure
# +1e5 Pa), DY = -0.05 m on the interface. Node sets per block apart: the
# corners of the two blocks coincide and must not be merged.
def build_pl42():
    m = Model("L30", timesteps=TS)
    m.elset("Boven", "Mat")
    m.elset("Onder", "Mat")
    up = quadmesh(m, "Boven", 12, 12, rect(-1.0, 1.0, 0.0, 1.0), order=1)
    base = Model.node
    # own merge key for the lower block (verif_lib merges by coordinate)
    m.node = lambda x, y, z, tol=1.0000001e-9: base(m, x, y, z, tol)
    lo = quadmesh(m, "Onder", 11, 11, rect(-1.0, 1.0, -1.0, 0.0), order=1)
    del m.node
    assert len(m.nodes) == 13 * 13 + 12 * 12, len(m.nodes)
    m.mat("Mat", '<geometric type="Plate" thickness="1 m" />',
          '<mechanical type="Isotropic" youngsmodulus="2e6 Pa" '
          'poissonratio="0" />')
    m.face_selection("AB", up["edges"]["v0"])
    m.face_selection("EF", lo["edges"]["v1"])
    m.node_selection("ABn", sorted(up["nodes"]["v0"]))
    m.face_selection("CD", up["edges"]["v1"])
    m.face_selection("GH", lo["edges"]["v0"])
    m.add('<displacement selection="CD"><value time="0 s">0 m</value>'
          '<value time="1 s">-0.1 m</value><x>0</x><y>1</y><z>0</z>'
          '</displacement>')
    m.add('<displacement selection="CD"><value>0 m</value><x>1</x><y>0</y>'
          '<z>0</z></displacement>')
    m.add('<fixed selection="GH" />')
    m.add('<contact2 selectionmaster="EF" selectionslave="AB" '
          'type="unilateralelastic"><tolerance>0 m</tolerance>'
          '<normalstiffness>1000 GPa/m</normalstiffness>'
          '<tangentialstiffness>0 GPa/m</tangentialstiffness>'
          '<frictioncoefficient>0</frictioncoefficient></contact2>')
    _finish(m, "D_PLAN")
    return m


TESTS.append(Case(
    "PL-42", GROUP, "ssnp121a: twee blokken in contact, vlakke rek "
    "(L30 + **ASTER-PLANE D_PLAN)", "nonlin_static_3d", build_pl42,
    [Check("contactdruk (gemiddeld, slave AB)",
           lambda r: r.mean("contactpressure", "ABn", time=1.0), ref=1.0e5,
           tol=0.01, unit="Pa",
           source="ssnp121a TEST_RESU LAGS_C (VALE_REFE -1e5, 1%)"),
     Check("contactdruk laagste knoop (hoeken A, B)",
           lambda r: min(r.step(1.0)["contactpressure"][n]
                         for n in r.model.nodesel["ABn"]), ref=1.0e5,
           tol=0.05, unit="Pa",
           source="ssnp121a TEST_RESU LAGS_C in A en B (VALE_REFE -1e5); "
                  "-3,0% met de standaardintegratie van de bridge (de test "
                  "met SIMPSON orde 4: +0,08%), daarom 5%"),
     Check("DY slave AB (gemiddeld)",
           lambda r: r.mean("disply", "ABn", time=1.0), ref=-0.05,
           tol=0.01, unit="m",
           source="ssnp121a TEST_RESU DY (VALE_REFE -0.05, 1%)")],
    settings={"deformation": "PETIT"},
    note="Geometrie en belasting van ssnp121a (Code-Aster 17.4), quad4 "
         "12x12 op 11x11, niet-passende randen; deformation PETIT zoals de "
         "test (met de standaard GROT_GDEP -> GREEN_LAGRANGE is de druk bij "
         "5% rek 7,6% lager: geometrisch niet-lineair)."))


# ------------------------------------------------------------------
# PL-43 the blocks of PL-42 in plane stress
# ------------------------------------------------------------------
# With nu = 0, C_PLAN and D_PLAN give the same uniform state, so the
# references of ssnp121a hold (contact in C_PLAN). Friction: PL-46.
def build_pl43():
    m = build_pl42()
    m.items = [it.replace("**ASTER-PLANE D_PLAN", "**ASTER-PLANE C_PLAN")
               for it in m.items]
    return m


_PL42 = [c for c in TESTS if c.id == "PL-42"][0]
TESTS.append(Case(
    "PL-43", GROUP, "ssnp121a in vlakke spanning (L30 + **ASTER-PLANE "
    "C_PLAN)", "nonlin_static_3d", build_pl43, _PL42.checks,
    settings={"deformation": "PETIT"},
    note="Als PL-42 met C_PLAN; met nu = 0 dezelfde oplossing."))


# ------------------------------------------------------------------
# PL-45 Hertz line contact: a cylinder on a block (D_PLAN)
# ------------------------------------------------------------------
# A quarter of a cylinder R (x >= 0, below its centre line y = R) on a
# block 4R x 4R (y <= 0), symmetry x = 0, the block's bottom fixed, the
# cylinder's flat top edge (y = R) pushed down by DELTA45 (displacement
# control: the cylinder is never held by the contact alone). Equal steel,
# plane strain, frictionless. Hertz (Johnson, Contact Mechanics, 1985,
# par. 4.2): with the force per unit length F' (from the reactions, x 2 for
# the half model, / t) b = sqrt(4 F' R / (pi E*)), E* = E / (2 (1 - nu^2)),
# p0 = 2 F' / (pi b). The half-width from the second moment of the contact
# pressure, b = 2 sqrt(int p x^2 dx / int p dx) (exact for the elliptic
# Hertz pressure), so it does not depend on where the nodes fall. Graded
# quad8 meshes: about 10 elements over b on the cylinder (slave).
R45, T45, DELTA45 = 0.05, 0.01, 2.6e-4
N45 = 44                    # quad8 along the contact arc (0 .. 45 degrees)
ESTAR = E / (2.0 * (1.0 - NU ** 2))


def _graded(u, a):
    """Parameter grading: a share linear, the rest cubic (fine at 0)."""
    return a * u + (1.0 - a) * u ** 3


def _coons(c1, e_bottom, e_right, e_top, e_left):
    """Transfinite (Coons) map of the unit square from its four edges:
    bottom and top as functions of u (from u = 0), left and right of v
    (from v = 0); c1 is the corner u = v = 0."""
    def f(u, v):
        out = []
        b, r, t, l = e_bottom(u), e_right(v), e_top(u), e_left(v)
        c2, c3, c4 = e_bottom(1.0), e_top(1.0), e_top(0.0)
        for k in range(2):
            out.append((1 - v) * b[k] + v * t[k] + (1 - u) * l[k] + u * r[k]
                       - ((1 - u) * (1 - v) * c1[k] + u * (1 - v) * c2[k] +
                          u * v * c3[k] + (1 - u) * v * c4[k]))
        return (out[0], out[1], 0.0)
    return f


def _cylinder_map(a=0.2):
    """Quarter disk below the centre (0, R): bottom edge = the arc from the
    contact point (0, 0) to 45 degrees (graded), right edge = the arc on to
    (R, R), top edge = the centre line y = R, left edge = x = 0."""
    def arc(theta):
        return (R45 * math.sin(theta), R45 - R45 * math.cos(theta))
    return _coons(
        (0.0, 0.0),
        lambda u: arc(_graded(u, a) * math.pi / 4),
        lambda v: arc(math.pi / 4 + v * math.pi / 4),
        lambda u: (u * R45, R45),
        lambda v: (0.0, _graded(v, a) * R45))


def _own_index(m, tol=1e-9):
    """Node function with its own merge index: a second body gets its own
    nodes where it touches the first (verif_lib merges by coordinate)."""
    index = {}

    def node(x, y, z, tol=tol):
        key = (round(x / tol), round(y / tol), round(z / tol))
        nid = index.get(key)
        if nid is None:
            m.nodes.append((float(x), float(y), float(z)))
            nid = len(m.nodes)
            index[key] = nid
        return nid
    return node


def build_pl45():
    m = Model("L30", timesteps={"timeperiod": "1 s", "stepsize": "0.25 s"})
    m.elset("Cilinder", "Staal")
    m.elset("Blok", "Staal")
    cyl = quadmesh(m, "Cilinder", N45, 30, _cylinder_map(), order=2)
    m.node = _own_index(m)      # the contact point (0, 0) twice
    blk = quadmesh(m, "Blok", 40, 40, lambda u, v: (
        4 * R45 * _graded(u, 0.05), -4 * R45 * _graded(v, 0.05), 0.0),
        order=2)
    del m.node
    m.mat("Staal", '<geometric type="Plate" thickness="%g mm" />' % (
        T45 * 1000), STEEL[1])
    m.face_selection("Cilinder_rand", cyl["edges"]["v0"])
    m.face_selection("Blok_boven", blk["edges"]["v0"])
    m.node_selection("Slave45", sorted(cyl["nodes"]["v0"]))
    m.face_selection("Sym", cyl["edges"]["u0"] + blk["edges"]["u0"])
    m.face_selection("Boven", cyl["edges"]["v1"])
    m.node_selection("Bovenn", sorted(cyl["nodes"]["v1"]))
    m.face_selection("Bodem", blk["edges"]["v1"])
    m.add('<symmetry selection="Sym"><x>1</x><y>0</y><z>0</z></symmetry>')
    m.add('<fixed selection="Bodem" />')
    m.add('<displacement selection="Boven"><value time="0 s">0 m</value>'
          '<value time="1 s">%r m</value><x>0</x><y>1</y><z>0</z>'
          '</displacement>' % -DELTA45)
    m.add('<contact2 selectionmaster="Blok_boven" selectionslave='
          '"Cilinder_rand" type="unilateralelastic"><tolerance>0 m'
          '</tolerance><normalstiffness>1000 GPa/m</normalstiffness>'
          '<tangentialstiffness>0 GPa/m</tangentialstiffness>'
          '<frictioncoefficient>0</frictioncoefficient></contact2>')
    _finish(m, "D_PLAN")
    return m


def _force45(r):
    """F' (N/m, whole cylinder): 2 x the top reaction / t."""
    return -2.0 * r.total("reactionforcey", "Bovenn", time=1.0) / T45


def _pressure45(r):
    """[(x, p)] along the slave edge, sorted by x (initial positions)."""
    d = r.step(1.0)["contactpressure"]
    pts = sorted((r.model.nodes[n - 1][0], d.get(n, 0.0))
                 for n in r.model.nodesel["Slave45"])
    return pts


def _b45(r):
    pts = _pressure45(r)
    m0 = m2 = 0.0
    for (x0, p0), (x1, p1) in zip(pts, pts[1:]):
        h = x1 - x0
        m0 += 0.5 * h * (p0 + p1)
        m2 += 0.5 * h * (p0 * x0 ** 2 + p1 * x1 ** 2)
    return 2.0 * math.sqrt(m2 / m0) if m0 > 0 else float("nan")


def _p0_fit(r):
    """Peak of the Hertz profile p0 sqrt(1 - x^2/b^2) fitted (least
    squares, b from _b45) to the nodal contact pressure up to 0.9 b: the
    nodal LAGS_C of quadratic edges with INTEGRATION='AUTO' alternate by
    about +-10% (corner and midside nodes), so one node is no peak."""
    b = _b45(r)
    num = den = 0.0
    for x, p in _pressure45(r):
        if x <= 0.9 * b:
            sh = math.sqrt(1.0 - (x / b) ** 2)
            num += p * sh
            den += sh * sh
    return num / den if den else float("nan")


def _elements_over_b(r):
    """Number of slave quad8 edges over 0 .. b, counting the part of the
    last one (corner nodes = every second node of the slave edge)."""
    b = _b45(r)
    xs = [x for x, _p in _pressure45(r)][::2]
    return sum(min(1.0, max(0.0, (b - x0) / (x1 - x0)))
               for x0, x1 in zip(xs, xs[1:]))


def _b_hertz(r):
    return math.sqrt(4.0 * _force45(r) * R45 / (math.pi * ESTAR))


TESTS.append(Case(
    "PL-45", GROUP, "Hertz-lijncontact cilinder op blok, vlakke rek "
    "(L30 + **ASTER-PLANE D_PLAN)", "nonlin_static_3d", build_pl45,
    [Check("halve breedte b / b_Hertz",
           lambda r: _b45(r) / _b_hertz(r), ref=1.0, tol=0.03, unit="-",
           source="Hertz (Johnson 1985 par. 4.2): b = sqrt(4 F' R / "
                  "(pi E*)); b uit het tweede moment van de contactdruk"),
     Check("piekdruk p0 (Hertz-profiel gefit) / p0_Hertz",
           lambda r: _p0_fit(r) / (
               2.0 * _force45(r) / (math.pi * _b_hertz(r))),
           ref=1.0, tol=0.03, unit="-",
           source="Hertz: p0 = 2 F' / (pi b); p0 uit een kleinste-"
                  "kwadratenfit van p0 sqrt(1 - x^2/b^2) aan de knopen tot "
                  "0,9 b (de knoopwaarden van LAGS_C wisselen +-10%)"),
     Check("elementen over b (cilinder, minimaal 10)",
           lambda r: min(10.0, _elements_over_b(r)),
           ref=10.0, tol_abs=1e-9, unit="-",
           source="Done-when: 10 of meer quad8 over de halve breedte "
                  "(fractie per element tussen de hoekknopen)")],
    settings={"deformation": "PETIT"},
    note="Kwart cilinder R = 50 mm op een blok 200 x 200 mm, t = 10 mm, "
         "quad8 40x30 en 40x40 gegradeerd naar het contactpunt, bovenrand "
         "0,26 mm omlaag in 4 stappen, wrijvingsloos, deformation PETIT."))


# ------------------------------------------------------------------
# PL-46 friction: the blocks of PL-42 pressed together, then the upper one
# pushed sideways until it slides (D_PLAN, Coulomb 0.3)
# ------------------------------------------------------------------
# 0 .. 1 s: the top edge CD DY 0 -> -0.01 m (normal force); 1 .. 2 s: CD
# DX 0 -> 0.05 m with DY held. Once the whole interface slides, the
# horizontal reaction of the fixed bottom GH is mu times its vertical
# reaction (Coulomb). The slave nodes are held by no support (KNOWN_BUGS
# 141 does not apply).
MU46 = 0.3


def build_pl46(n_lower=18):
    """The lower block is wider (x = -1.5 .. 1.5, 18 quad4: the same node
    spacing as the upper block, matching at the start), so the slave edge
    stays on the master while it slides 0.05 m (a slave node beyond the
    master end carries no friction: with blocks of the same width the
    ratio was 1.3% low)."""
    m = Model("L30", timesteps={"timeperiod": "2 s", "stepsize": "0.1 s"})
    m.elset("Boven", "Mat")
    m.elset("Onder", "Mat")
    up = quadmesh(m, "Boven", 12, 12, rect(-1.0, 1.0, 0.0, 1.0), order=1)
    m.node = _own_index(m)
    lo = quadmesh(m, "Onder", n_lower, 12, rect(-1.5, 1.5, -1.0, 0.0),
                  order=1)
    del m.node
    m.mat("Mat", '<geometric type="Plate" thickness="1 m" />',
          '<mechanical type="Isotropic" youngsmodulus="2e6 Pa" '
          'poissonratio="0" />')
    m.face_selection("AB", up["edges"]["v0"])
    m.face_selection("EF", lo["edges"]["v1"])
    m.face_selection("CD", up["edges"]["v1"])
    m.face_selection("GH", lo["edges"]["v0"])
    m.add('<fixed selection="GH" />')
    m.add('<contact2 selectionmaster="EF" selectionslave="AB" '
          'type="unilateralelastic"><tolerance>0 m</tolerance>'
          '<normalstiffness>1000 GPa/m</normalstiffness>'
          '<tangentialstiffness>0 GPa/m</tangentialstiffness>'
          '<frictioncoefficient>0</frictioncoefficient></contact2>')
    _finish(m, "D_PLAN")
    m.add('<displacement selection="CD"><value time="0 s">0 m</value>'
          '<value time="1 s">-0.01 m</value><value time="2 s">-0.01 m'
          '</value><x>0</x><y>1</y><z>0</z></displacement>')
    m.add('<displacement selection="CD"><value time="0 s">0 m</value>'
          '<value time="1 s">0 m</value><value time="2 s">0.05 m</value>'
          '<x>1</x><y>0</y><z>0</z></displacement>')
    m.items = [it.replace("<frictioncoefficient>0</frictioncoefficient>",
                          "<frictioncoefficient>%r</frictioncoefficient>"
                          % MU46) for it in m.items]
    m.node_selection("GHn", [i + 1 for i, p in enumerate(m.nodes)
                             if abs(p[1] + 1.0) < 1e-12])
    return m


def _mu46(r):
    rx = r.total("reactionforcex", "GHn", time=2.0)
    ry = r.total("reactionforcey", "GHn", time=2.0)
    return abs(rx / ry)


TESTS.append(Case(
    "PL-46", GROUP, "Wrijving: blok glijdt over blok, vlakke rek "
    "(L30 + **ASTER-PLANE D_PLAN, Coulomb 0,3)", "nonlin_static_3d",
    build_pl46,
    [Check("|R_x / R_y| onder bij glijden", _mu46, ref=MU46, tol=0.01,
           unit="-", source="Coulomb: tangentiele kracht = mu x normaalkracht "
                            "bij glijden")],
    settings={"deformation": "PETIT"},
    note="Blokken als PL-42 (onderblok 3 m breed, quad4 18x12 onder en "
         "12x12 boven, bij de start passend): eerst 0,01 m samengedrukt, dan "
         "de bovenrand 0,05 m zijwaarts; wrijvingscoefficient 0,3."))
