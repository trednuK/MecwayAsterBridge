# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Loads on the side face of beams (LS-92a .. LS-92h) and hydrostatic
pressure on shell edges (LS-93a .. LS-93c), S17 / KNOWN_BUGS 5.
Explanation: docs/Verificatie.md (LS-92, LS-93).

Mecway rule (measured headless, Mecway 34 internal solver, S17): a beam has
three faces, 1 = the side face (the whole element), 2/3 = the ends.
Traction T on the side face = distributed load T x perimeter per length
(global direction, any section, independent of the orientation); a formula
is evaluated at the beam axis, one point per element. Pressure on the side
face has zero resultant and Mecway applies nothing. The bridge: FORCE_POUTRE
FX/FY/FZ = T x perimeter (bridge_mesh._beam_side_loads); pressure: no load.

References: Euler-Bernoulli (cantilever with uniform load w = qL^4/(8EI),
linearly increasing load w = 11 q0 L^4/(120 EI), tip force PL^3/(3EI)) and
Mecway 34 headless on the same .liml (TestFiles/Tools/mw_solve.py, 28 Oct
2026). Mecway takes a formula at one point per element (manual v34
par. 9.14), Code-Aster at the integration points; hence LS-92c is closer
to the exact value than Mecway.
"""
import math
from verif_lib import Case, Check, Model, linemesh, quadmesh
from tests_balken import line3mesh

E = 210e9
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
DENS = '<density type="Simple" density="7850 kg/m³" />'
RECT = '<geometric type="RectBar" recta="20 mm" rectb="10 mm" />'
CIRC = '<geometric type="CircularBar" roundod="20 mm" />'
IPROF = '<geometric type="I" ia="100 mm" ib="50 mm" ic="5 mm" id="4 mm" />'
L, N = 1.0, 10
T = 1000.0                      # traction 1 kPa
PER_RECT = 2 * (0.020 + 0.010)  # perimeter, Mecway: 0.06 m
PER_CIRC = math.pi * 0.020
PER_I = 2 * 0.100 + 4 * 0.050 - 2 * 0.004   # 0.392 m
I_V = 0.020 * 0.010 ** 3 / 12.0           # RectBar, deflection along W (Z)
Q = T * PER_RECT                           # 60 N/m
W_UNIF = Q * L ** 4 / (8 * E * I_V)
W_LIN = 11 * Q * L ** 4 / (120 * E * I_V)
P_TIP = 10.0
W_TIP = P_TIP * L ** 3 / (3 * E * I_V)
G_ACC = 9.81
Q_GRAV = 7850.0 * 0.020 * 0.010 * G_ACC    # rho A g
FORM = 'unit="kPa" timeunit="s" positionunit="m"'
TZ = ('<traction selection="Zijvlak"><x>0 Pa</x><y>0 Pa</y><z>1 kPa</z>'
      '</traction>')
TY = ('<traction selection="Zijvlak"><x>0 Pa</x><y>1 kPa</y><z>0 Pa</z>'
      '</traction>')

# Mecway 34 headless (internal solver) on the same .liml (28 Oct 2026)
MW_92A = 0.0214285714           # = W_UNIF
MW_92B = 0.00017004737
MW_92C = 0.0157047619
MW_92D = 0.00952380952            # = W_TIP; the pressure adds nothing
MW_92F = 0.0211875775
MW_92H = 0.0159279643
MW_93A = -4.55039911e-08        # Mecway: Pressure formula, not hydrostatic
MW_93A5 = -2.29205919e-08
MW_93B = -2.16271702e-08
MW_93C = -4.63808675e-08


def _beam(sec=RECT, load=TZ, line3=False, second=None, extra="",
          analysis="S30", dens=False):
    def build():
        m = Model(analysis, timesteps=({"timeperiod": "1 s",
                                        "stepsize": "1 s"}
                                       if analysis == "L30" else None))
        m.elset("Balk", "Staaf")
        if line3:
            eids, nids = line3mesh(m, "Balk", 4, (0, 0, 0), (L, 0, 0))
        elif second:
            m.elset("Balk2", "Staaf2")
            e1, n1 = linemesh(m, "Balk", N // 2, (0, 0, 0), (L / 2, 0, 0))
            e2, n2 = linemesh(m, "Balk2", N // 2, (L / 2, 0, 0), (L, 0, 0))
            eids, nids = e1 + e2, n1 + n2[1:]
            m.mat("Staaf2", second, STEEL)
        else:
            eids, nids = linemesh(m, "Balk", N, (0, 0, 0), (L, 0, 0))
        m.mat("Staaf", sec, STEEL, *([DENS] if dens else []))
        m.node_selection("Inklemming", [nids[0]])
        m.node_selection("Tip", [nids[-1]])
        m.add('<fixed selection="Inklemming" />')
        m.face_selection("Zijvlak", [(e, 1) for e in eids])
        m.add(load)
        if extra:
            m.add(extra)
        return m
    return build


def _tip(var, name, ref, tol, source, sign=1.0):
    return Check(name, lambda r: sign * r.at(var, (L, 0, 0)), ref=ref,
                 tol=tol, unit="m", source=source)


def _reaction(var, ref, source):
    return Check("reaction sum %s" % var[-1].upper(),
                 lambda r: r.total(var, "Inklemming"), ref=ref, tol=1e-6,
                 unit="N", source=source)


RHO_W, T_PL = 1000.0, 0.010


def _wall(zfree=1.0, order=1, formula=False):
    """Vertical plate 1 x 1 m in the XZ plane, t = 10 mm, quad4 4 x 10 (or
    quad8), edge x = 0 clamped, hydrostatic pressure (water, free surface
    at z = zfree, gravity -Z) on the edge x = 1 (faceid 2 of the edge
    elements). The plate material has no density: only the pressure
    loads it. formula: instead the same load as a Pressure with the formula
    rho g (h - z) (the Mecway reference: Mecway 34 does not apply a
    hydrostatic pressure to shell edges, but does apply this formula)."""
    def build():
        m = Model("S30")
        m.elset("Wand", "Plaat")
        q = quadmesh(m, "Wand", 4, 10, lambda u, v: (u, 0.0, v),
                     order=order)
        m.mat("Plaat", '<geometric type="Plate" thickness="10 mm" />', STEEL)
        m.node_selection("Inklemming", sorted(q["nodes"]["u0"]))
        m.node_selection("Rand", sorted(q["nodes"]["u1"]))
        # displacement + node rotation instead of fixed: with fixed on a
        # node selection of shells Mecway 34 headless computes a mechanism
        # (as in tests_formules)
        for ax in ("1</x><y>0</y><z>0", "0</x><y>1</y><z>0",
                   "0</x><y>0</y><z>1"):
            m.add('<displacement selection="Inklemming"><value>0 m</value>'
                  '<x>%s</z></displacement>' % ax)
            m.add('<noderotation selection="Inklemming"><value>0 rad'
                  '</value><x>%s</z></noderotation>' % ax)
        m.face_selection("Schaalrand", q["edges"]["u1"])
        m.add('<gravity><x>0 m/s²</x><y>0 m/s²</y><z>-%g m/s²</z>'
              '</gravity>' % G_ACC)
        if formula:
            m.add('<surfacepressure selection="Schaalrand"><normal '
                  'unit="kPa" timeunit="s" positionunit="m">max(0,9.81*(%g-z))'
                  '</normal></surfacepressure>' % zfree)
        else:
            m.add('<hydrostaticpressure selection="Schaalrand"><fluiddensity>'
                  '1000 kg/m³</fluiddensity><x>0 m</x><y>0 m</y><z>%g m</z>'
                  '</hydrostaticpressure>' % zfree)
        return m
    return build


def _hyd_force(h):
    """Resultant of the hydrostatic pressure on the edge, rho g t H^2/2."""
    return RHO_W * G_ACC * T_PL * h * h / 2.0


def _hyd_reaction(h, tol=1e-6):
    return Check("reaction sum X", lambda r: r.total("reactionforcex",
                                                     "Inklemming"),
                 ref=_hyd_force(h), tol=tol, unit="N",
                 source="rho g t H^2/2 (H = %g m)" % h)


def _edge_dx(z, ref, tol):
    return Check("edge displacement X at z = %g vs Mecway 34" % z,
                 lambda r: r.at("displx", (1.0, 0.0, z)), ref=ref, tol=tol,
                 unit="m", source="Mecway 34 headless: Pressure max(0, "
                 "rho g (h - z)) on the same edge (internal solver)")


SRC_U = "Euler: w = qL^4/(8EI), q = T x perimeter"
GROUP = "Lineair statisch"
TESTS = [
    Case("LS-92a", GROUP, "Traction on the side face of a beam (RectBar)",
         "lin_static_3d", _beam(),
         checks=[_tip("displz", "tip deflection", W_UNIF, 1e-3, SRC_U),
                 _tip("displz", "tip deflection vs Mecway 34", MW_92A, 1e-3,
                      "Mecway 34 headless (internal solver)"),
                 _reaction("reactionforcez", -Q, "T x perimeter x L = 60 N")],
         note="q = 1 kPa x 0.06 m; equal to a line pressure of 60 N/m."),
    Case("LS-92b", GROUP, "Traction on the side face of an I-profile beam "
         "(transverse, Y)", "lin_static_3d", _beam(sec=IPROF, load=TY),
         checks=[_tip("disply", "tip deflection vs Mecway 34", MW_92B, 1e-3,
                      "Mecway 34 headless (internal solver)"),
                 _reaction("reactionforcey", -T * PER_I * L,
                           "T x perimeter x L = 392 N (perimeter 0.392 m)")]),
    Case("LS-92c", GROUP, "Traction as a formula z = x kPa on a beam side "
         "face", "lin_static_3d",
         _beam(load='<traction selection="Zijvlak"><x>0 Pa</x><y>0 Pa</y>'
                    '<z %s>x</z></traction>' % FORM),
         checks=[_tip("displz", "tip deflection", W_LIN, 1e-3,
                      "Euler: w = 11 q0 L^4/(120 EI)"),
                 _tip("displz", "tip deflection vs Mecway 34", MW_92C, 2e-3,
                      "Mecway 34 headless (one point per element)"),
                 _reaction("reactionforcez", -Q * L / 2,
                           "integral of T(x) x perimeter = 30 N")]),
    Case("LS-92d", GROUP, "Pressure on the side face of a beam: no load",
         "lin_static_3d",
         _beam(load='<surfacepressure selection="Zijvlak"><normal>1 MPa'
                    '</normal></surfacepressure>',
               extra='<force selection="Tip"><x>0 N</x><y>0 N</y><z>%g N'
                     '</z></force>' % P_TIP),
         checks=[_tip("displz", "tip deflection (tip force only)", W_TIP,
                      1e-6, "Euler: PL^3/(3EI); pressure resultant 0"),
                 _tip("displz", "tip deflection vs Mecway 34", MW_92D, 1e-5,
                      "Mecway 34 headless (internal solver)"),
                 _reaction("reactionforcez", -P_TIP, "tip force only")]),
    Case("LS-92e", GROUP, "Traction on the side face of line3 beams",
         "lin_static_3d", _beam(line3=True),
         checks=[_tip("displz", "tip deflection", W_UNIF, 1e-3, SRC_U),
                 _reaction("reactionforcez", -Q, "60 N")],
         note="Mecway solves line3 beams only with CCX (expanded to solid "
              "elements); analytic reference only."),
    Case("LS-92f", GROUP, "Traction on side faces of two sections "
         "(RectBar + CircularBar)", "lin_static_3d",
         _beam(second=CIRC),
         checks=[_reaction("reactionforcez",
                           -T * L / 2 * (PER_RECT + PER_CIRC),
                           "T x (0.06 + pi 0.02) m x L/2"),
                 _tip("displz", "tip deflection vs Mecway 34", MW_92F, 1e-3,
                      "Mecway 34 headless (internal solver)")]),
    Case("LS-92g", "Niet-lineair statisch", "Traction on a beam side face "
         "in nonlinear static", "nonlin_static_3d",
         _beam(analysis="L30"),
         checks=[_tip("displz", "tip deflection", W_UNIF, 1e-3, SRC_U),
                 _reaction("reactionforcez", -Q, "60 N")]),
    Case("LS-92h", GROUP, "Traction on a beam side face together with "
         "gravity (one distributed load per beam)", "lin_static_3d",
         _beam(dens=True, extra='<gravity><x>0 m/s²</x><y>0 m/s²</y>'
                                '<z>-%g m/s²</z></gravity>' % G_ACC),
         checks=[_tip("displz", "tip deflection",
                      (Q - Q_GRAV) * L ** 4 / (8 * E * I_V), 1e-3,
                      "Euler with q = T x perimeter - rho A g"),
                 _tip("displz", "tip deflection vs Mecway 34", MW_92H, 1e-3,
                      "Mecway 34 headless (internal solver)"),
                 _reaction("reactionforcez", -(Q - Q_GRAV) * L,
                           "(60 - rho A g) N")]),
    Case("LS-93a", GROUP, "Hydrostatic pressure on a shell edge (quad4)",
         "lin_static_3d", _wall(),
         checks=[_hyd_reaction(1.0),
                 _edge_dx(0.0, MW_93A, 1e-3),
                 _edge_dx(0.5, MW_93A5, 2e-3)]),
    Case("LS-93b", GROUP, "Hydrostatic pressure on a shell edge, free "
         "surface inside an element", "lin_static_3d", _wall(zfree=0.55),
         checks=[_hyd_reaction(0.55, 1e-4),
                 _edge_dx(0.0, MW_93B, 5e-3)]),
    Case("LS-93c", GROUP, "Hydrostatic pressure on a shell edge (quad8)",
         "lin_static_3d", _wall(order=2),
         checks=[_hyd_reaction(1.0),
                 _edge_dx(0.0, MW_93C, 1e-3)]),
]
