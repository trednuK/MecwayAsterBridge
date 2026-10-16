# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Beams with large displacements and rotations: elem_beam = POU_D_T_GD
(STAPPENPLAN S20) in nonlinear static (Mecway L30 -> STAT_NON_LINE,
MODELISATION POU_D_T_GD, RELATION ELAS_POUTRE_GR, DEFORMATION GROT_GDEP).

NL-80 .. NL-82 rebuild the benchmarks GB-01 .. GB-03 of the fork by
MishalTPC (github.com/mishal0488/MecwayAsterBridge, branch dev, commit
dd4c958, MPL-2.0), here as Mecway models through the whole bridge:

  NL-80   small tip force on a cantilever: Timoshenko F L^3/(3EI) +
          F L/(k G A), k = 5/6 (GB-01); NL-80b the same model in linear
          static: elem_beam POU_D_T_GD falls back to POU_D_T; NL-80c a
          constant (not time-dependent) tip force and moment
  NL-81   cantilever bent through 90 degrees by an end moment
          M = (pi/2) EI/L: a circular arc, tip x = L sin(t)/t,
          y = L (1 - cos t)/t (GB-02); section forces M constant, N = 0
  NL-82   initially curved column (first cantilever mode in the mesh,
          e0 = 1e-4 L), axial load 0.5 P_cr: amplification 1/(1 - P/P_cr)
          (GB-03)
  NL-83   elastica: tip force of fixed direction, PL^2/EI = 1, 2, 3
          (Mattiasson 1981; Reissner beam solved by shooting below);
          section forces against statics in the deformed state; Mecway 34
          with CCX (B31) on the same model
  NL-84   NL-81 with line3 elements (split into two SEG2 cells)
  NL-85   NL-81 about the weak axis set by an Element orientation card
  NL-86   centrifugal force on a radial bar (FORMULE route, fixed load);
          NL-86b plus a radial truss (BARRE, FORCE_POUTRE as well)
  NL-87   line pressure plus gravity (one FORCE_POUTRE + PESANTEUR load),
          configuration GQ; NL-87b configuration G (gravity only)
  NL-88   free thermal expansion (Thermal stress, temperature2)
  NL-89   line pressure as a formula in x and t

Explanation, sources and results: docs/Verificatie.md (sec. NL-80 .. NL-89).
POU_D_T_GD is a linear element (one integration point): 40 elements per
member here, as in the fork.
"""
import math
from verif_lib import Case, Check, Model, linemesh

GROUP = "Niet-lineair statisch"
GD = {"elem_beam": "POU_D_T_GD"}

E, NU, RHO = 210e9, 0.3, 7850.0
G = E / (2.0 * (1.0 + NU))
ALPHA_T = 1.2e-5
L = 1.0
N_EL = 40
# RectBar recta x rectb = 10 x 20 mm: recta along Mecway's V (= global Y for
# a beam along X without orientation), rectb along W (= Z).
RA, RB = 0.010, 0.020
AREA = RA * RB
I_W = RB * RA ** 3 / 12.0           # bending in the XY plane (about W = Z)
I_V = RA * RB ** 3 / 12.0           # bending in the XZ plane (about V = Y)
K_SHEAR = 5.0 / 6.0                 # RECTANGLE: AY = AZ = 1.2 (Code-Aster)
SECTION = ('<geometric type="RectBar" recta="10 mm" rectb="20 mm" />')
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" thermalexpansion="%g 1/K" />' % ALPHA_T)
DENS = '<density type="Simple" density="7850 kg/m³" />'
TS = {"timeperiod": "1 s", "stepsize": "0.05 s"}
THETA = math.pi / 2.0


def _beam(analysis="L30", timesteps=None, shape="line2", attrs=""):
    """Cantilever along X, N_EL elements (line3: N_EL/2 elements with
    Mecway's node order end, middle, end); Root and Tip selections."""
    m = Model(analysis, timesteps=timesteps)
    m.elset("Balk", "Staal")
    if shape == "line2":
        eids, nids = linemesh(m, "Balk", N_EL, (0, 0, 0), (L, 0, 0))
    else:
        nids = [m.node(L * i / float(N_EL), 0, 0) for i in range(N_EL + 1)]
        eids = [m.elem("Balk", "line3", nids[2 * i:2 * i + 3], attrs)
                for i in range(N_EL // 2)]
    m.mat("Staal", SECTION, STEEL, DENS)
    m.node_selection("Inklemming", [nids[0]])
    m.node_selection("Tip", [nids[-1]])
    m.element_selection("Alle", eids)
    m.add('<fixed selection="Inklemming" />')
    return m, nids, eids


def _tip(var, time=None):
    return lambda r: r.at(var, (L, 0, 0), time)


def _tip_at(var, y, time=None):
    return lambda r: r.at(var, (L, y, 0), time)


def _ramp(tag, value, unit):
    return '<{0} time="0 s">0 {2}</{0}><{0} time="1 s">{1:.12g} {2}</{0}>'.format(
        tag, value, unit)


# ------------------------------------------------------------------
# NL-80 Small tip force (GB-01)
# ------------------------------------------------------------------
F80 = 1.0
REF80 = F80 * L ** 3 / (3.0 * E * I_W) + F80 * L / (K_SHEAR * G * AREA)


def build_nl80(analysis="L30"):
    def build():
        m, _n, _e = _beam(analysis)
        if analysis == "L30":
            m.add('<force selection="Tip"><x>0 N</x>%s<z>0 N</z></force>'
                  % _ramp("y", F80, "N"))
        else:
            m.add('<force selection="Tip"><x>0 N</x><y>%g N</y><z>0 N</z>'
                  '</force>' % F80)
        return m
    return build


def _nl80_checks():
    return [Check("doorbuiging tip", _tip("disply"), ref=REF80, tol=1e-3,
                  unit="m", source="Timoshenko: F L^3/(3EI) + F L/(kGA), "
                  "k = 5/6 (fork MishalTPC, GB-01)")]


# NL-80c: constant tip force F80 (Y) and moment M80C (about Z), no time
# table: small rotations, superposition of the linear solutions.
M80C = 0.5


def build_nl80c():
    m, _n, _e = _beam()
    m.add('<force selection="Tip"><x>0 N</x><y>%g N</y><z>0 N</z></force>'
          % F80)
    m.add('<moment selection="Tip"><x>0 N.m</x><y>0 N.m</y><z>%g N.m</z>'
          '</moment>' % M80C)
    return m


def _nl80c_checks():
    ei = E * I_W
    return [Check("doorbuiging tip", _tip("disply"),
                  ref=REF80 + M80C * L ** 2 / (2.0 * ei), tol=1e-3,
                  unit="m", source="Timoshenko: F L^3/(3EI) + F L/(kGA) + "
                  "M L^2/(2EI)"),
            Check("tiprotatie", _tip("rotz"),
                  ref=F80 * L ** 2 / (2.0 * ei) + M80C * L / ei, tol=1e-3,
                  unit="rad", source="F L^2/(2EI) + M L/(EI)")]


# ------------------------------------------------------------------
# NL-81, NL-84, NL-85 Cantilever bent through 90 degrees by an end moment
# ------------------------------------------------------------------
M81 = THETA * E * I_W / L
ARC_X = L * (math.sin(THETA) / THETA - 1.0)       # tip displacement along U
ARC_Y = L * (1.0 - math.cos(THETA)) / THETA       # tip displacement across
# Orientation card V = Z: recta (10 mm) along Z, rectb along W = X x Z = -Y.
# A moment about global Y bends about W with I = rectb recta^3/12 = I_W
# (without the card V = Y and the same moment would see I_V = 4 I_W).
CARD85 = ('<orientation selection="Alle"><ux>0</ux><uy>0</uy><uz>0</uz>'
          '<vx>0</vx><vy>0</vy><vz>1</vz><angleu>0 rad</angleu>'
          '</orientation>')


def build_nl81(shape="line2", card=False):
    def build():
        m, _n, _e = _beam(timesteps=TS, shape=shape)
        if card:
            m.add(CARD85)
            m.add('<moment selection="Tip"><x>0 N.m</x>%s<z>0 N.m</z>'
                  '</moment>' % _ramp("y", M81, "N.m"))
        else:
            m.add('<moment selection="Tip"><x>0 N.m</x><y>0 N.m</y>%s'
                  '</moment>' % _ramp("z", M81, "N.m"))
        return m
    return build


def _elems(r, var):
    return [v for _eid, vals in sorted(r.elem(var).items()) for v in vals]


def _nl81_checks(card=False):
    # Card: the moment about +Y turns the axis X towards -Z (rotation +t
    # about Y) and is a moment about -W (W = X x Z = -Y): bendingmomw = -M.
    across, sign = ("displz", -1.0) if card else ("disply", 1.0)
    rot = "roty" if card else "rotz"
    return [
        Check("tip verplaatsing langs de as", _tip("displx"), ref=ARC_X,
              tol=1e-3, unit="m", source="cirkelboog: L (sin t / t - 1), "
              "t = pi/2 (fork MishalTPC, GB-02)"),
        Check("tip verplaatsing dwars", _tip(across), ref=sign * ARC_Y,
              tol=1e-3, unit="m", source="cirkelboog: L (1 - cos t) / t"),
        Check("tiprotatie", _tip(rot), ref=THETA, tol=1e-3,
              unit="rad", source="t = M L / (EI) = pi/2"),
        Check("bendingmomw (min. over de elementen)",
              lambda r: min(_elems(r, "bendingmomw"), key=abs),
              ref=sign * M81, tol=1e-4, unit="N.m",
              source="zuivere buiging: M constant over de balk"),
        Check("bendingmomw (max. over de elementen)",
              lambda r: max(_elems(r, "bendingmomw"), key=abs),
              ref=sign * M81, tol=1e-4, unit="N.m",
              source="zuivere buiging: M constant over de balk"),
        Check("tensileforce (grootste |N|)",
              lambda r: max(_elems(r, "tensileforce"), key=abs),
              ref=0.0, tol_abs=0.05, unit="N",
              source="zuivere buiging: N = 0 (|N| < 0,05 N bij M = 550 Nm)"),
    ]


# ------------------------------------------------------------------
# NL-82 Initially curved column: second-order amplification (GB-03)
# ------------------------------------------------------------------
E0 = 1e-4 * L
ALPHA82 = 0.5
PCR = math.pi ** 2 * E * I_W / (4.0 * L ** 2)
# Mecway 34 + CCX 2.23 headless on modellen/NL-82.liml (solver="ccx"):
# u_y at the tip (mean of the section nodes) 9.9948003e-05 m.
MW82_CCX = 1.0 + 9.9948003e-05 / E0


def build_nl82():
    m, nids, _e = _beam()
    # First cantilever buckling mode in the mesh: zero deflection and slope
    # at the root (no buckling pre-solve: imperfection_amplitude needs
    # RIGI_MECA, which POU_D_T_GD does not have).
    m.nodes = [(x, E0 * (1.0 - math.cos(math.pi * x / (2.0 * L))), z)
               for x, y, z in m.nodes]
    m.add('<force selection="Tip">%s<y>0 N</y><z>0 N</z></force>'
          % _ramp("x", -ALPHA82 * PCR, "N"))
    return m


# ------------------------------------------------------------------
# NL-83 Elastica: tip force of fixed direction (Mattiasson 1981)
# ------------------------------------------------------------------
ALPHAS = (1.0, 2.0, 3.0)                  # P L^2 / EI at t = 1, 2, 3 s
TS83 = {"timeperiod": "3 s", "stepsize": "0.1 s"}
EI = E * I_W
# Mecway 34 (headless, TestFiles/Tools/mw_solve.py, 16 Oct 2026) with CCX
# 2.23 (solver="ccx", B31 expanded to solids) on modellen/NL-83.liml; the
# mean of the section nodes at x = L, per t: (u_x, u_y). Mecway's own
# solver gave no solution for Nonlinear static with beams (no solution
# file); CCX did not get NL-81 (end moment) beyond t = 0.55 s.
MW83_CCX = {1.0: (-0.0564209, 0.30168), 2.0: (-0.160607, 0.4933935),
            3.0: (-0.254362, 0.60317302)}


def reissner(alpha, n=4000):
    """
    Cantilever Reissner beam (extensible, shear deformable: what POU_D_T_GD
    models) with a tip force P of fixed direction perpendicular to the
    undeformed axis, alpha = P L^2 / EI, for the section of this module.
    With theta the rotation of the section and the internal force (0, P):
      N = P sin(theta), V = P cos(theta), eps = N/(EA), gam = V/(kGA),
      x' = (1+eps) cos(theta) - gam sin(theta),
      y' = (1+eps) sin(theta) + gam cos(theta),
      theta' = M/(EI), M' = -P x', theta(0) = 0, M(L) = 0.
    Shooting on M(0) (bisection) with RK4. Returns (u_x, u_y, theta) at the
    tip. Without eps and gam this is the elastica of tests_niet_lineair
    (Mattiasson 1981: alpha = 2: u_y/L 0.49346, -u_x/L 0.16064).
    """
    p = alpha * EI / L ** 2
    ea, kga = E * AREA, K_SHEAR * G * AREA

    def f(y):
        th, mom = y[0], y[1]
        n_, v_ = p * math.sin(th), p * math.cos(th)
        xp = (1 + n_ / ea) * math.cos(th) - v_ / kga * math.sin(th)
        yp = (1 + n_ / ea) * math.sin(th) + v_ / kga * math.cos(th)
        return [mom / EI, -p * xp, xp, yp]

    def run(m0):
        h = L / n
        y = [0.0, m0, 0.0, 0.0]
        for _ in range(n):
            k1 = f(y)
            k2 = f([y[i] + 0.5 * h * k1[i] for i in range(4)])
            k3 = f([y[i] + 0.5 * h * k2[i] for i in range(4)])
            k4 = f([y[i] + h * k3[i] for i in range(4)])
            y = [y[i] + h / 6.0 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i])
                 for i in range(4)]
        return y
    lo, hi = 0.0, 1.2 * p * L
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if run(mid)[1] < 0.0:
            lo = mid
        else:
            hi = mid
    y = run(0.5 * (lo + hi))
    return y[2] - L, y[3], y[0]


REF83 = dict((float(i + 1), reissner(a)) for i, a in enumerate(ALPHAS))


def build_nl83():
    m, _n, _e = _beam(timesteps=TS83)
    pts = "".join('<y time="%g s">%.12g N</y>' % (t, a * EI / L ** 2)
                  for t, a in [(0.0, 0.0)] + [(i + 1.0, a) for i, a in
                                              enumerate(ALPHAS)])
    m.add('<force selection="Tip"><x>0 N</x>%s<z>0 N</z></force>' % pts)
    return m


def _deformed(r, nid, t):
    x0, y0, _z0 = r.model.nodes[nid - 1]
    return (x0 + r.node("displx", nid, t), y0 + r.node("disply", nid, t))


def _root_moment_statics(r, t=3.0):
    """Statics in the deformed state (FEM coordinates): the section force
    of POU_D_T_GD is constant per element (one integration point, at the
    middle); the moment there is P (x_tip - x_mid) about Z."""
    p = ALPHAS[-1] * EI / L ** 2
    x_tip = _deformed(r, N_EL + 1, t)[0]
    x_mid = 0.5 * (_deformed(r, 1, t)[0] + _deformed(r, 2, t)[0])
    return p * (x_tip - x_mid)


def _tip_element_angle(r, t=3.0):
    a, b = _deformed(r, N_EL, t), _deformed(r, N_EL + 1, t)
    return math.atan2(b[1] - a[1], b[0] - a[0])


def _elem_value(var, eid, t=3.0):
    return lambda r: r.elem(var, t)[eid][0]


def _nl83_checks():
    out = []
    for t in sorted(REF83):
        ux, uy, th = REF83[t]
        out += [
            Check("tip u_y t=%g" % t, _tip("disply", t), ref=uy, tol=1e-3,
                  unit="m", source="Reissner-balk, schieten (RK4); "
                  "onrekbaar: Mattiasson 1981"),
            Check("tip u_x t=%g" % t, _tip("displx", t), ref=ux, tol=1e-3,
                  unit="m", source="Reissner-balk, schieten (RK4)"),
            Check("tiprotatie t=%g" % t, _tip("rotz", t), ref=th, tol=1e-3,
                  unit="rad", source="Reissner-balk, schieten (RK4)")]
    p = ALPHAS[-1] * EI / L ** 2
    out += [
        Check("bendingmomw element 1 t=3 (statica vervormd)",
              _elem_value("bendingmomw", 1),
              ref=None, tol=1e-3, unit="N.m",
              source="P (x_tip - x_midden element 1), vervormde FEM-"
              "coordinaten", in_series=False),
        Check("sheary laatste element t=3 (statica vervormd)",
              _elem_value("sheary", N_EL),
              ref=None, tol=1e-3, unit="N",
              source="P cos(phi), phi = hoek van de koorde van het element",
              in_series=False),
        Check("tensileforce laatste element t=3 (statica vervormd)",
              _elem_value("tensileforce", N_EL),
              ref=None, tol=1e-3, unit="N",
              source="P sin(phi)", in_series=False),
        Check("reactiekracht Y", lambda r: r.total("reactionforcey",
                                                     "Inklemming", 3.0),
              ref=-p, tol=1e-6, unit="N", source="evenwicht: -P"),
    ]
    for t, (mx, my) in sorted(MW83_CCX.items()):
        if mx is None:
            continue
        out += [
            Check("tip u_y t=%g t.o.v. Mecway 34 + CCX" % t,
                  _tip("disply", t), ref=my, tol=1e-3, unit="m",
                  source="Mecway 34 headless, CCX (B31), zelfde model",
                  in_series=False),
            Check("tip u_x t=%g t.o.v. Mecway 34 + CCX" % t,
                  _tip("displx", t), ref=mx, tol=1e-3, unit="m",
                  source="Mecway 34 headless, CCX (B31), zelfde model",
                  in_series=False)]
    return out


# ------------------------------------------------------------------
# NL-86 Centrifugal force on a radial bar (FORMULE route)
# ------------------------------------------------------------------
RPM86 = 300.0
W86 = RPM86 * 2.0 * math.pi / 60.0


def build_nl86():
    m, _n, _e = _beam()
    m.add('<centrifugal><x>0 r/min</x><y>0 r/min</y>'
          '<z>%r r/min</z></centrifugal>' % RPM86)
    return m


# NL-86b: NL-86 plus a radial truss (40 line2, truss="true": BARRE) at
# y = 0.5 m; the truss nodes are held in Y and Z (a bar has no bending
# stiffness), so it only stretches along X.
Y86B = 0.5


def build_nl86b():
    m = build_nl86()
    m.elset("Staaf", "Staal")
    tn = [m.node(L * i / float(N_EL), Y86B, 0) for i in range(N_EL + 1)]
    for i in range(N_EL):
        m.elem("Staaf", "line2", tn[i:i + 2], 'truss="true"')
    m.node_selection("StaafRoot", [tn[0]])
    m.node_selection("StaafAlle", tn)
    m.add('<fixed selection="StaafRoot" />')
    for d in ("<x>0</x><y>1</y><z>0</z>", "<x>0</x><y>0</y><z>1</z>"):
        m.add('<displacement selection="StaafAlle"><value>0 mm</value>%s'
              '</displacement>' % d)
    return m


# ------------------------------------------------------------------
# NL-87 Line pressure plus gravity (bending about V), two configurations
# ------------------------------------------------------------------
# Configuration G: gravity only (line pressure suppressed); GQ: both. The
# setting "configuration" chooses (as LS-20).
Q87, G87 = 20.0, 9.81
W87G = RHO * AREA * G87
W87 = Q87 + W87G


def build_nl87():
    m, _n, _e = _beam()
    for c in ("G", "GQ"):
        m.add('<configuration name="%s" />' % c)
    m.add('<linepressure selection="Alle"><x>0 N/m</x><y>0 N/m</y>'
          '<z>-%g N/m</z><suppressed configuration="G" /></linepressure>'
          % Q87)
    m.add('<gravity><x>0 m/s²</x><y>0 m/s²</y><z>-%g m/s²</z></gravity>'
          % G87)
    return m


def _nl87_checks(w):
    return [Check("doorbuiging tip", _tip("displz"),
                  ref=-(w * L ** 4 / (8.0 * E * I_V) +
                        w * L ** 2 / (2.0 * K_SHEAR * G * AREA)),
                  tol=1e-3, unit="m",
                  source="w L^4/(8 E I) + w L^2/(2 k G A), w = q + rho A g "
                  "(configuratie G: w = rho A g)"),
            Check("reactiekracht Z", lambda r: r.total("reactionforcez",
                                                       "Inklemming"),
                  ref=w * L, tol=1e-6, unit="N", source="w L")]


# ------------------------------------------------------------------
# NL-88 Free thermal expansion
# ------------------------------------------------------------------
TREF88, DT88 = 293.15, 100.0


def build_nl88():
    m, _n, _e = _beam()
    m.node_selection("AlleKnopen", list(range(1, len(m.nodes) + 1)))
    m.add('<thermalstress><referencetemperature>%g K</referencetemperature>'
          '</thermalstress>' % TREF88)
    m.add('<temperature2 selection="AlleKnopen"><value>%g K</value>'
          '<starttime>0 s</starttime><endtime>0 s</endtime></temperature2>'
          % (TREF88 + DT88))
    return m


# ------------------------------------------------------------------
# NL-89 Line pressure as a formula in x and t (triangular, growing in time)
# ------------------------------------------------------------------
Q89 = 30.0                          # q(x, t) = Q89 x/L t in -Z, t = 0 .. 1 s
TS89 = {"timeperiod": "1 s", "stepsize": "0.5 s"}


def build_nl89():
    m, _n, _e = _beam(timesteps=TS89)
    m.add('<linepressure selection="Alle"><x>0 N/m</x><y>0 N/m</y>'
          '<z unit="N/m" timeunit="s" positionunit="m">-%g*x*t</z>'
          '</linepressure>' % (Q89 / L))
    return m


# Absolute residual: with a small load RESI_GLOB_RELA 1e-5 stagnates at
# round-off (note of the fork, GB-01).
SMALL = {"convergence_criterion": "RELA_OF_MAXI",
         "convergence_resi_maxi": 1e-6}

TESTS = [
    Case("NL-80", GROUP, "POU_D_T_GD: ingeklemde balk, kleine eindkracht "
         "(Timoshenko)", "nonlin_static_3d", build_nl80(), _nl80_checks(),
         settings=SMALL, general=GD,
         note="Benchmark GB-01 van de fork van MishalTPC; 40 line2."),
    Case("NL-80b", GROUP, "POU_D_T_GD in lineair statisch: wordt POU_D_T",
         "lin_static_3d", build_nl80("S30"), _nl80_checks(), general=GD,
         note="elem_beam POU_D_T_GD buiten niet-lineair statisch: POU_D_T "
              "met een WARNING."),
    Case("NL-80c", GROUP, "POU_D_T_GD: constante eindkracht en "
         "eindmoment (geen tijdtabel)", "nonlin_static_3d", build_nl80c,
         _nl80c_checks(), settings=SMALL, general=GD,
         note="Kracht en moment zonder tijdtabel; kleine lasten: "
              "superpositie van de lineaire oplossingen."),
    Case("NL-81", GROUP, "POU_D_T_GD: zuivere buiging tot 90 graden",
         "nonlin_static_3d", build_nl81(), _nl81_checks(), general=GD,
         note="Benchmark GB-02 van de fork van MishalTPC; eindmoment "
              "M = (pi/2) EI/L in 20 stappen (Mecway-stap 0,05 s)."),
    Case("NL-82", GROUP, "POU_D_T_GD: kolom met beginkromming, "
         "tweede-orde-versterking", "nonlin_static_3d", build_nl82,
         [Check("totale tipuitwijking / e0",
                lambda r: 1.0 + r.at("disply", (L, E0, 0)) / E0,
                ref=1.0 / (1.0 - ALPHA82), tol=1e-3, unit="-",
                source="1/(1 - P/Pcr), P = 0,5 Pcr, Pcr = pi^2 EI/(4L^2) "
                "(fork MishalTPC, GB-03)"),
          Check("totale tipuitwijking / e0 t.o.v. Mecway 34 + CCX",
                lambda r: 1.0 + r.at("disply", (L, E0, 0)) / E0,
                ref=MW82_CCX, tol=1e-3, unit="-",
                source="Mecway 34 headless, CCX (B31), zelfde model",
                in_series=False)],
         settings={"substeps_per_interval": 40}, general=GD,
         note="Benchmark GB-03 van de fork van MishalTPC; de "
              "beginkromming staat in de mesh."),
    Case("NL-83", GROUP, "POU_D_T_GD: elastica, eindkracht van vaste "
         "richting (PL^2/EI = 1, 2, 3)", "nonlin_static_3d", build_nl83,
         _nl83_checks(), general=GD,
         note="Snedekrachten (beam_forces) tegen de statica in de vervormde "
              "stand; Mecway 34 rekent dit model met CCX."),
    Case("NL-84", GROUP, "POU_D_T_GD: zuivere buiging tot 90 graden, line3",
         "nonlin_static_3d", build_nl81("line3"), _nl81_checks(),
         general=GD, note="20 line3, elk gesplitst in twee SEG2-cellen."),
    Case("NL-85", GROUP, "POU_D_T_GD: zuivere buiging tot 90 graden om de "
         "zwakke as uit een orientatiekaart", "nonlin_static_3d",
         build_nl81(card=True), _nl81_checks(card=True), general=GD,
         note="Element orientation V = Z; moment om globaal Y."),
    Case("NL-86", GROUP, "POU_D_T_GD: centrifugaalkracht op een radiale "
         "staaf", "nonlin_static_3d", build_nl86,
         [Check("tipverlenging", _tip("displx"),
                ref=RHO * W86 ** 2 * L ** 3 / (3.0 * E), tol=1e-3, unit="m",
                source="u(L) = rho w^2 L^3 / (3E)"),
          Check("reactiekracht X", lambda r: r.total("reactionforcex",
                                                     "Inklemming"),
                ref=-RHO * AREA * W86 ** 2 * L ** 2 / 2.0, tol=1e-3,
                unit="N", source="-rho A w^2 L^2 / 2")],
         settings=SMALL, general=GD,
         note="ROTATION kan niet op POU_D_T_GD (CHAR_MECA_ROTA_R); "
              "FORCE_POUTRE als FORMULE van de beginpositie."),
    Case("NL-86b", GROUP, "POU_D_T_GD: centrifugaalkracht op een balk en "
         "een truss (BARRE)", "nonlin_static_3d", build_nl86b,
         [Check("tipverlenging truss", _tip_at("displx", Y86B),
                ref=RHO * W86 ** 2 * L ** 3 / (3.0 * E), tol=1e-3, unit="m",
                source="u(L) = rho w^2 L^3 / (3E)"),
          Check("reactiekracht X truss", lambda r: r.total(
              "reactionforcex", "StaafRoot"),
                ref=-RHO * AREA * W86 ** 2 * L ** 2 / 2.0, tol=1e-3,
                unit="N", source="-rho A w^2 L^2 / 2")],
         settings=SMALL, general=GD,
         note="Zelfde FORMULE-route; de truss (BARRE) krijgt ook "
              "FORCE_POUTRE."),
    Case("NL-87", GROUP, "POU_D_T_GD: line pressure en zwaartekracht "
         "(configuratie GQ)", "nonlin_static_3d", build_nl87,
         _nl87_checks(W87), settings=SMALL,
         general=dict(GD, configuration="GQ"),
         note="FORCE_POUTRE en PESANTEUR in een last (CALCULEL2_92)."),
    Case("NL-87b", GROUP, "POU_D_T_GD: zwaartekracht (configuratie G, "
         "line pressure onderdrukt)", "nonlin_static_3d", build_nl87,
         _nl87_checks(W87G), settings=SMALL,
         general=dict(GD, configuration="G"),
         note="Zelfde model als NL-87; de instelling configuration kiest."),
    Case("NL-89", GROUP, "POU_D_T_GD: line pressure als formule in x en t",
         "nonlin_static_3d", build_nl89,
         [Check("doorbuiging tip t=1", _tip("displz", 1.0),
                ref=-(11.0 * Q89 * L ** 4 / (120.0 * E * I_V) +
                      Q89 * L ** 2 / (3.0 * K_SHEAR * G * AREA)),
                tol=1e-3, unit="m", source="11 q0 L^4/(120 EI) (Roark) + "
                "q0 L^2/(3 k G A), q = q0 x/L"),
          Check("doorbuiging tip t=0,5", _tip("displz", 0.5),
                ref=-0.5 * (11.0 * Q89 * L ** 4 / (120.0 * E * I_V) +
                            Q89 * L ** 2 / (3.0 * K_SHEAR * G * AREA)),
                tol=1e-3, unit="m", source="evenredig met t"),
          Check("reactiekracht Z t=1", lambda r: r.total(
              "reactionforcez", "Inklemming", 1.0), ref=Q89 * L / 2.0,
                tol=1e-6, unit="N", source="q0 L / 2")],
         settings=SMALL, general=GD,
         note="FORCE_POUTRE als FORMULE van X en INST (AFFE_CHAR_MECA_F)."),
    Case("NL-88", GROUP, "POU_D_T_GD: vrije thermische uitzetting",
         "nonlin_static_3d", build_nl88,
         [Check("tipverlenging", _tip("displx"), ref=ALPHA_T * DT88 * L,
                tol=1e-6, unit="m", source="alpha dT L")],
         settings=SMALL, general=GD,
         note="Thermal stress met temperature2 (AFFE_VARC TEMP)."),
]


def _fill_statics(checks):
    """The statics checks of NL-83 have a reference from the FEM geometry
    itself; Check.evaluate needs a number, so wrap value and reference."""
    out = []
    for c in checks:
        if c.ref is not None:
            out.append(c)
            continue
        out.append(_StaticsCheck(c))
    return out


class _StaticsCheck(Check):
    """Check whose reference comes from the same result (statics in the
    deformed state): evaluate() fills ref first."""

    def __init__(self, c):
        Check.__init__(self, c.name, c.value, 0.0, tol=c.tol, unit=c.unit,
                       source=c.source, in_series=c.in_series)

    def evaluate(self, r):
        p = ALPHAS[-1] * EI / L ** 2
        if self.name.startswith("bendingmomw"):
            self.ref = _root_moment_statics(r)
        elif self.name.startswith("sheary"):
            self.ref = p * math.cos(_tip_element_angle(r))
        else:
            self.ref = p * math.sin(_tip_element_angle(r))
        return Check.evaluate(self, r)


for _case in TESTS:
    _case.checks = _fill_statics(_case.checks)
