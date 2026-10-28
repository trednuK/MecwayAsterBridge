# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Orthotropic and matrix materials on solids (step S13a): Mecway's
Orthotropic / Stiffness matrix / Compliance matrix -> ELAS_ORTH, material
axes from the element orientation -> AFFE_CARA_ELEM MASSIF ANGL_REP
(bridge_orthotropic).

References: Hooke's law in the material axes transformed to the global axes
(tensor rotation of the compliance, exact for a homogeneous stress state)
and beam theory (Timoshenko) for the cantilever; Mecway 34 headless with its
internal solver (TestFiles/Tools/mw_solve.py, the same .liml; numbers in
MW below). Explanation: docs/Verificatie.md (OR-01 .. ).
"""
import math

from verif_lib import Case, Check, Model, hexmesh, box

GROUP = "Orthotroop"

# Material in the axes U, V, W (major Poisson ratios, Mecway manual v34
# par. 8.5): E_U, E_V, E_W, nu_UV, nu_VW, nu_WU, G_UV, G_VW, G_WU
EU, EV, EW = 100e9, 20e9, 10e9
NUV, NVW, NWU = 0.3, 0.2, 0.05
GUV, GVW, GWU = 7e9, 4e9, 5e9
ORTHO = ('<mechanical type="Orthotropic" youngsmodulusu="100 GPa" '
         'youngsmodulusv="20 GPa" youngsmodulusw="10 GPa" '
         'poissonratiouv="0.3" poissonratiovw="0.2" poissonratiowu="0.05" '
         'shearmodulusuv="7 GPa" shearmodulusvw="4 GPa" '
         'shearmoduluswu="5 GPa" />')


def _compliance():
    """6x6 compliance in the material axes, order UU VV WW UV VW WU
    (engineering shear)."""
    s = [[0.0] * 6 for _i in range(6)]
    s[0][0], s[1][1], s[2][2] = 1 / EU, 1 / EV, 1 / EW
    s[0][1] = s[1][0] = -NUV / EU
    s[1][2] = s[2][1] = -NVW / EV
    s[0][2] = s[2][0] = -NWU / EW
    s[3][3], s[4][4], s[5][5] = 1 / GUV, 1 / GVW, 1 / GWU
    return s


def _inv(a):
    """Gauss-Jordan inverse of a square matrix."""
    n = len(a)
    m = [list(r) + [1.0 if i == j else 0.0 for j in range(n)]
         for i, r in enumerate(a)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        piv = m[c][c]
        m[c] = [x / piv for x in m[c]]
        for r in range(n):
            if r != c:
                f = m[r][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return [r[n:] for r in m]


_PAIRS = ((0, 0), (1, 1), (2, 2), (0, 1), (1, 2), (2, 0))


def _unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v]


def frame(u, v, angle=0.0):
    """Rows U, V, W (unit vectors): V projected perpendicular to U, then
    rotated about U by angle (Mecway manual v34 par. 7.4.2 / 8.5)."""
    u = _unit(u)
    d = sum(a * b for a, b in zip(u, v))
    v = _unit([b - d * a for a, b in zip(u, v)])
    w = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2],
         u[0] * v[1] - u[1] * v[0]]
    if angle:
        c, s = math.cos(angle), math.sin(angle)
        v, w = ([c * a + s * b for a, b in zip(v, w)],
                [-s * a + c * b for a, b in zip(v, w)])
    return [u, v, w]


def global_strain(rows, stress_dir, sigma):
    """Global strains (xx, yy, zz, gxy, gyz, gzx) of a uniaxial stress
    sigma along the global axis stress_dir (0, 1, 2) for the material with
    axes rows: eps_g = R^T S_l R : sigma_g, as tensors."""
    s6 = _compliance()
    st = {}
    for a, (i, j) in enumerate(_PAIRS):
        for b, (k, l) in enumerate(_PAIRS):
            f = (0.5 if a >= 3 else 1.0) * (0.5 if b >= 3 else 1.0)
            for p, q in {(i, j), (j, i)}:
                for r, t in {(k, l), (l, k)}:
                    st[(p, q, r, t)] = s6[a][b] * f
    # local stress tensor = R sigma_g R^T
    sg = [[0.0] * 3 for _i in range(3)]
    sg[stress_dir][stress_dir] = sigma
    R = rows
    sl = [[sum(R[i][p] * sg[p][q] * R[j][q] for p in range(3)
               for q in range(3)) for j in range(3)] for i in range(3)]
    el = [[sum(st.get((i, j, k, l), 0.0) * sl[k][l] for k in range(3)
               for l in range(3)) for j in range(3)] for i in range(3)]
    eg = [[sum(R[i][p] * el[i][j] * R[j][q] for i in range(3)
               for j in range(3)) for q in range(3)] for p in range(3)]
    return [eg[0][0], eg[1][1], eg[2][2], 2 * eg[0][1], 2 * eg[1][2],
            2 * eg[2][0]]


# ------------------------------------------------------------------
# OR-01 .. OR-03: cube 10 mm (hex20 2x2x2) under a uniaxial stress of
# 10 MPa (equal and opposite forces on two faces), held statically
# determinate (3-2-1 on corner nodes): homogeneous stress, so every element
# type is exact and the corner displacements give all six strains:
#   A (0,0,0) fixed; B (L,0,0) uy = uz = 0; C (0,L,0) uz = 0;
#   D (0,0,L) free. Then eps_xx = ux_B / L, eps_yy = uy_C / L,
#   eps_zz = uz_D / L, g_xy = ux_C / L, g_yz = uy_D / L, g_zx = ux_D / L
#   (the rigid rotation is removed by the constraints on B and C).
# ------------------------------------------------------------------
L = 0.01
SIG = 10e6
F = SIG * L * L
_FACES = {0: ("u0", "u1"), 1: ("v0", "v1"), 2: ("w0", "w1")}
_PTS = {"A": (0, 0, 0), "B": (L, 0, 0), "C": (0, L, 0), "D": (0, 0, L)}


def _cube(mat_lines, stress_dir, attrs=None, card=None, heat=None):
    m = Model("S30")
    m.elset("Blok", "Ortho")
    h = hexmesh(m, "Blok", 2, 2, 2, box(0, L, 0, L, 0, L), order=2)
    if attrs:
        es = m._elset["Blok"][2]
        for k in range(len(es)):
            es[k] = es[k][:3] + (attrs,)
    if card:
        m.element_selection("Alles", sorted(h["elems"].values()))
        m.add(card.replace("SEL", "Alles"))
    m.mat("Ortho", *mat_lines)
    lo, hi = _FACES[stress_dir]
    m.face_selection("Min", h["faces"][lo])
    m.face_selection("Max", h["faces"][hi])
    comp = ["x", "y", "z"]

    def force(sign):
        return "".join("<{0}>{1!r} N</{0}>".format(
            c, sign * F if k == stress_dir else 0.0)
            for k, c in enumerate(comp))
    if heat is None:
        m.add('<force selection="Max">%s</force>' % force(1.0))
        m.add('<force selection="Min">%s</force>' % force(-1.0))
    else:
        # uniform temperature rise heat [K] above the reference on all nodes
        m.node_selection("Alle", list(range(1, len(m.nodes) + 1)))
        m.add('<thermalstress><referencetemperature>%r K'
              '</referencetemperature></thermalstress>' % TREF)
        m.add('<temperature2 selection="Alle"><value>%r K</value>'
              '<starttime>0 s</starttime><endtime>0 s</endtime>'
              '</temperature2>' % (TREF + heat))
    for name, p in _PTS.items():
        m.node_selection(name, [m.node(*p)])
    for name, dofs in (("A", "xyz"), ("B", "yz"), ("C", "z")):
        for c in dofs:
            m.add('<displacement selection="%s"><value>0 m</value>'
                  '<x>%d</x><y>%d</y><z>%d</z></displacement>' % (
                      name, c == "x", c == "y", c == "z"))
    m.add('<fieldvariable name="stress" displayunit="Pa" expanded="true" />')
    return m


def _strain(r, k):
    """Global strain k (xx, yy, zz, gxy, gyz, gzx) from the corner
    displacements (see above)."""
    point, var = [("B", "displx"), ("C", "disply"), ("D", "displz"),
                  ("C", "displx"), ("D", "disply"), ("D", "displx")][k]
    return r.at(var, _PTS[point]) / L


_NAMES = ["eps_xx", "eps_yy", "eps_zz", "gamma_xy", "gamma_yz",
          "gamma_zx"]


def _cube_checks(rows, stress_dir, mw):
    eps = global_strain(rows, stress_dir, SIG)
    big = max(abs(e) for e in eps)
    out = []
    for k in range(6):
        out.append(Check(
            _NAMES[k], lambda r, k=k: _strain(r, k), ref=eps[k],
            tol_abs=1e-6 * big, unit="-",
            source="Hooke in U,V,W, compliance rotated to X,Y,Z"))
    comp = ["xx", "yy", "zz"][stress_dir]
    out.append(Check(
        "stress" + comp, lambda r: r.at("stress" + comp, (L / 2, L / 2,
                                                          L / 2)),
        ref=SIG, tol=1e-6, unit="Pa", source="F / A"))
    out.append(Check(
        "stressxy (0)", lambda r: r.at("stressxy", (L / 2, L / 2, L / 2)),
        ref=0.0, tol_abs=1e-6 * SIG, unit="Pa",
        source="uniaxial stress state"))
    for k, val in enumerate(mw or []):
        out.append(Check(
            _NAMES[k] + " = Mecway", lambda r, k=k: _strain(r, k), ref=val,
            tol_abs=1e-6 * big, unit="-",
            source="Mecway 34 headless (internal solver)", in_series=False))
    return out


# U, V of the element attributes (OR-01) and of the card (OR-02)
U1, V1 = (1.0, 1.0, 0.0), (-1.0, 1.0, 1.0)
ATTRS1 = ('orientationux="1" orientationuy="1" orientationuz="0" '
          'orientationvx="-1" orientationvy="1" orientationvz="1"')
U2, V2, ANG2 = (0.0, 0.6, 0.8), (1.0, 0.0, 0.0), math.radians(30.0)
CARD2 = ('<orientation selection="SEL"><ux>0</ux><uy>0.6</uy><uz>0.8</uz>'
         '<vx>1</vx><vy>0</vy><vz>0</vz><angleu>30 °</angleu>'
         '</orientation>')

# Mecway 34 headless (mw_solve.py, internal solver, 28 Oct 2026) on
# modellen/OR-*.liml: strains from the same corner displacements (equal to
# the analytical values within 1e-8), tip deflection of the cantilevers.
MW = {
    "OR-01": [0.00062253968, -0.00018698413, -0.00016055556, -0.00037222222,
              -2.5873016e-05, 0.00021634921],
    "OR-02": [0.000775, -0.0001726, -0.0001124, -0.00031176915, 0.0002064,
              0.00023382686],
    "OR-03": [-0.00018698413, 0.00062253968, -0.00016055556, -0.00037222222,
              -0.00021634921, 2.5873016e-05],
    "OR-04": [-0.0001124, -0.00019294971, 0.00058094971, 6.7658853e-05,
              -0.000530304, 9.7717358e-05],
    "OR-09": [0.00225, 0.00212, 0.00163, -0.00069282032, -0.00168,
              0.00051961524],
    "OR-05": 0.0032424784,
    "OR-06": 0.016041192,
}


# Mecway's matrix rows 1..6 = UU, VV, WW, VW, WU, UV (measured with
# headless Mecway 34 solves, STAPPENPLAN S13 findings): row k of Mecway's
# matrix is row _MW[k] of _compliance() (order UU VV WW UV VW WU).
_MW = (0, 1, 2, 4, 5, 3)


def _matrix_mat(kind):
    """Orthotropic stiffness (GPa) or compliance (m2/N) matrix in Mecway's
    order for the same material."""
    s = _compliance()
    if kind == "StiffnessMatrix":
        mat, pre, unit, scale = _inv(s), "c", "GPa", 1e-9
    else:
        mat, pre, unit, scale = s, "s", u"m²/N", 1.0
    return '<mechanical type="%s" %s />' % (kind, " ".join(
        '%s%d%d="%r %s"' % (pre, i + 1, j + 1,
                            mat[_MW[i]][_MW[j]] * scale, unit)
        for i in range(6) for j in range(i, 6)))


def build_or01():
    return _cube([ORTHO], 0, attrs=ATTRS1)


def build_or02():
    return _cube([ORTHO], 0, card=CARD2)


def build_or03():
    return _cube([_matrix_mat("StiffnessMatrix")], 1, attrs=ATTRS1)


def build_or04():
    return _cube([_matrix_mat("ComplianceMatrix")], 2, card=CARD2)


# OR-09: the cube heated by DT = 100 K without load, alpha = 1e-5, 2e-5,
# 3e-5 1/K in U, V, W, axes of the card of OR-02: free thermal strain
# eps_g = R^T diag(alpha DT) R, no stress.
TREF, DT = 293.15, 100.0
ALPHA = (1e-5, 2e-5, 3e-5)
ORTHO_T = ORTHO.replace(' />', ' thermalexpansionu="1E-05 1/K" '
                        'thermalexpansionv="2E-05 1/K" '
                        'thermalexpansionw="3E-05 1/K" />')


def thermal_strain(rows):
    eg = [[sum(rows[i][p] * ALPHA[i] * DT * rows[i][q] for i in range(3))
           for q in range(3)] for p in range(3)]
    return [eg[0][0], eg[1][1], eg[2][2], 2 * eg[0][1], 2 * eg[1][2],
            2 * eg[2][0]]


def build_or09():
    return _cube([ORTHO_T], 0, card=CARD2, heat=DT)


def _thermal_checks(rows, mw):
    eps = thermal_strain(rows)
    big = max(abs(e) for e in eps)
    out = [Check(_NAMES[k], lambda r, k=k: _strain(r, k), ref=eps[k],
                 tol_abs=1e-6 * big, unit="-",
                 source="alpha_i DT in U,V,W rotated to X,Y,Z")
           for k in range(6)]
    out.append(Check("von Mises (0)", lambda r: r.extreme("vonmises"),
                     ref=0.0, tol_abs=1e-3 * 100e9 * big, unit="Pa",
                     source="free expansion: no stress"))
    for k, val in enumerate(mw or []):
        out.append(Check(
            _NAMES[k] + " = Mecway", lambda r, k=k: _strain(r, k), ref=val,
            tol_abs=1e-6 * big, unit="-",
            source="Mecway 34 headless (internal solver)", in_series=False))
    return out


TESTS = [
    Case("OR-01", GROUP, "Orthotroop blok, trek X, assen per element "
         "(U, V)", "lin_static_3d", build_or01,
         _cube_checks(frame(U1, V1), 0, MW.get("OR-01")),
         note="Element attributes orientationux..vz; U = (1, 1, 0), "
              "V = (-1, 1, 1) (projected)."),
    Case("OR-02", GROUP, "Orthotroop blok, trek X, Element orientation-"
         "kaart met hoek", "lin_static_3d", build_or02,
         _cube_checks(frame(U2, V2, ANG2), 0, MW.get("OR-02")),
         note="Card on an element selection: U = (0, 0.6, 0.8), "
              "V = (1, 0, 0), angle 30 degrees."),
    Case("OR-03", GROUP, "Stijfheidsmatrix (orthotroop), trek Y, assen per "
         "element", "lin_static_3d", build_or03,
         _cube_checks(frame(U1, V1), 1, MW.get("OR-03")),
         note="StiffnessMatrix c11..c66 of the same material."),
    Case("OR-04", GROUP, "Compliantiematrix (orthotroop), trek Z, kaart met "
         "hoek", "lin_static_3d", build_or04,
         _cube_checks(frame(U2, V2, ANG2), 2, MW.get("OR-04")),
         note="ComplianceMatrix s11..s66 of the same material."),
    Case("OR-09", GROUP, "Orthotroop blok, vrije thermische uitzetting, "
         "kaart met hoek", "lin_static_3d", build_or09,
         _thermal_checks(frame(U2, V2, ANG2), MW.get("OR-09")),
         note="Thermal stress, uniform +100 K; alpha 1e-5/2e-5/3e-5 in "
              "U/V/W."),
]


# ------------------------------------------------------------------
# OR-05, OR-06: cantilever 200 x 10 x 10 mm (hex20 20 x 2 x 2), clamped at
# x = 0, traction in -Z on the end face. OR-05: U along the beam (E_U
# bends, G_WU shears); OR-06: material turned 90 degrees about Z (U = Y,
# V = -X), so V lies along the beam (E_V bends, G_VW shears).
# Timoshenko: w = P L^3 / (3 E I) + P L / (k G A), k = 5/6.
# ------------------------------------------------------------------
LB, BB = 0.2, 0.01
AB, IB, PB = BB * BB, BB ** 4 / 12.0, 100.0


def _cantilever(attrs):
    m = Model("S30")
    m.elset("Balk", "Ortho")
    h = hexmesh(m, "Balk", 20, 2, 2, box(0, LB, 0, BB, 0, BB), order=2)
    if attrs:
        es = m._elset["Balk"][2]
        for k in range(len(es)):
            es[k] = es[k][:3] + (attrs,)
    m.mat("Ortho", ORTHO)
    m.face_selection("Inklemming", h["faces"]["u0"])
    m.face_selection("Eindvlak", h["faces"]["u1"])
    m.node_selection("TipKnopen", sorted(h["nodes"]["u1"]))
    m.add('<fixed selection="Inklemming" />')
    m.add('<traction selection="Eindvlak"><x>0 Pa</x><y>0 Pa</y>'
          '<z>-%r Pa</z></traction>' % (PB / AB))
    return m


def _tip(r):
    nids = r.model.nodesel["TipKnopen"]
    d = r.step()["displz"]
    return -sum(d[n] for n in nids) / float(len(nids))


def _timoshenko(e, g):
    return PB * LB ** 3 / (3 * e * IB) + PB * LB / (5.0 / 6.0 * g * AB)


def build_or05():
    return _cantilever(None)


def build_or06():
    return _cantilever('orientationux="0" orientationuy="1" '
                       'orientationuz="0" orientationvx="-1" '
                       'orientationvy="0" orientationvz="0"')


def _beam_checks(e, g, mw):
    out = [Check("doorbuiging tip (gem.)", _tip, ref=_timoshenko(e, g),
                 tol=0.01, unit="m",
                 source="Timoshenko PL^3/3EI + PL/kGA, k = 5/6")]
    if mw is not None:
        out.append(Check("doorbuiging tip = Mecway", _tip, ref=mw,
                         tol=2e-3, unit="m",
                         source="Mecway 34 headless (internal solver)",
                         in_series=False))
    return out


TESTS += [
    Case("OR-05", GROUP, "Orthotrope ingeklemde balk, E_U langs de balk",
         "lin_static_3d", build_or05,
         _beam_checks(EU, GWU, MW.get("OR-05")),
         note="Default material axes (U = X, V = Y, W = Z)."),
    Case("OR-06", GROUP, "Orthotrope ingeklemde balk, E_V langs de balk "
         "(assen 90 graden gedraaid)", "lin_static_3d", build_or06,
         _beam_checks(EV, GVW, MW.get("OR-06")),
         note="U = Y, V = -X per element: E_V = 20 GPa bends."),
]


# ------------------------------------------------------------------
# OR-07, OR-08: the cantilever of OR-05/OR-06 in Frequency (V30), density
# 1500 kg/m3: first two bending frequencies (in Z and in Y).
# Euler-Bernoulli: f1 = 1.8751^2 / (2 pi) sqrt(E I / (rho A L^4)); the
# shear flexibility (E/G up to 20) lowers it by about 1% (tolerance 3%);
# the second reference is Mecway 34 headless.
# ------------------------------------------------------------------
RHO = 1500.0
DENS = u'<density type="Simple" density="1500 kg/m³" />'


def _modal(attrs):
    m = _cantilever(attrs)
    m.analysis = "V30"
    m.attrs = {"maxmode": 4}
    m.items = [i for i in m.items if "traction" not in i]
    m.mats = []
    m.mat("Ortho", ORTHO, DENS)
    return m


def _euler_f1(e):
    return 1.87510407 ** 2 / (2 * math.pi) * math.sqrt(
        e * IB / (RHO * AB * LB ** 4))


def build_or07():
    return _modal(None)


def build_or08():
    return _modal('orientationux="0" orientationuy="1" orientationuz="0" '
                  'orientationvx="-1" orientationvy="0" orientationvz="0"')


def _modal_checks(e, mw):
    out = [Check("f1 (Euler-Bernoulli)", lambda r: r.mode(1),
                 ref=_euler_f1(e), tol=0.03, unit="Hz",
                 source="1.8751^2/(2 pi) sqrt(EI/(rho A L^4))")]
    for k, val in enumerate(mw or []):
        out.append(Check("f%d = Mecway" % (k + 1),
                         lambda r, k=k: r.mode(k + 1), ref=val, tol=2e-3,
                         unit="Hz", source="Mecway 34 headless (internal "
                         "solver)", in_series=False))
    return out
