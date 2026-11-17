# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Heat transfer in 2D and axisymmetric (STAPPENPLAN S44d; Scripts/
bridge_plane._apply_thermal, bridge_thermal with thermal_axis): Mecway
Thermal Steady State (T30) and Transient (T31) with plane shell elements and
the line '**ASTER-PLANE AXIS' -> THERMIQUE 'AXIS' about Y; without the line
the plane shells are 'PLAN' (existing route, PL-55). Explanation:
docs/Verificatie.md chapter 2D and axisymmetric (PL).

PL-50  tube a .. b, T_a and T_b on the walls: T(r) logarithmic, radial heat
       flux k (T_a - T_b) / (r ln(b/a)).
PL-51  the same tube with T_b fixed and a total heat flow Q (W, 360 degrees)
       on the inner edge: T_a - T_b = Q ln(b/a) / (2 pi k h) (the revolved
       area of a total heat flow).
PL-52  T_a fixed, convection on the outer edge.
PL-53  transient cooling of a long solid cylinder (T31), surface temperature
       prescribed: the Bessel series at r = 0, 0.5 R, 0.8 R.
PL-54  T_a fixed, radiation on the outer edge: conduction = radiation.
PL-55  plane wall with convection (T30 shells, PLAN, no line).
"""
import math

from verif_lib import Case, Check, Model, quadmesh, rect

GROUP = "2D en axisymmetrisch"
RA, RB, H = 0.1, 0.2, 0.01
K, RHO, CP = 50.0, 7800.0, 500.0
TA, TB = 393.0, 293.0
NR = 10                     # quad8 through the wall


def _mat(m, name="Staal", plate=0.01):
    m.mat(name, '<geometric type="Plate" thickness="%g m" />' % plate,
          '<density type="Simple" density="%g kg/m³" />' % RHO,
          '<thermal type="Isotropic" thermalconductivity="%g W/m/K" '
          'specificheat="%g J/kg/K" />' % (K, CP))


def _temp(sel, value):
    return ('<temperature2 selection="%s"><value>%.12g K</value>'
            '<starttime>0 s</starttime><endtime>0 s</endtime></temperature2>'
            % (sel, value))


def _switch(m):
    m.add(u"<ccxmodeldefinition>**ASTER-PLANE AXIS</ccxmodeldefinition>")


def _tube(outer):
    """Tube slice a .. b, height H; outer(m, edges): the load of the outer
    edge; the inner edge at T_a unless outer sets it."""
    def build():
        m = Model("T30")
        m.elset("Buis", "Staal")
        q = quadmesh(m, "Buis", NR, 1, rect(RA, RB, 0.0, H), order=2)
        _mat(m)
        e = q["edges"]
        m.face_selection("Binnen", e["u0"])
        m.face_selection("Buiten", e["u1"])
        outer(m)
        _switch(m)
        return m
    return build


def _ln_profile(r):
    return TA + (TB - TA) * math.log(r / RA) / math.log(RB / RA)


RM = 0.5 * (RA + RB)


def _pl50(m):
    m.add(_temp("Binnen", TA))
    m.add(_temp("Buiten", TB))


Q51 = 500.0                 # W over 360 degrees


def _pl51(m):
    m.add(_temp("Buiten", TB))
    m.add('<heatflow selection="Binnen"><value>%g W</value></heatflow>'
          % Q51)


HC, TINF = 100.0, 293.0


def _pl52(m):
    m.add(_temp("Binnen", TA))
    m.add('<convectionbc selection="Buiten"><ambienttemp>%g K</ambienttemp>'
          '<coefficient>%g W/m²/K</coefficient></convectionbc>' % (TINF, HC))


def _t52(r):
    return TA - (TA - TINF) * math.log(r / RA) / (
        math.log(RB / RA) + K / (HC * RB))


EPS, SIGMA = 0.8, 5.670374419e-8
TA54 = 1000.0               # hot inner wall: radiation matters


def _pl54(m):
    m.add(_temp("Binnen", TA54))
    m.add('<radiationbc selection="Buiten"><ambienttemp>%g K</ambienttemp>'
          '<emissivity>%g</emissivity></radiationbc>' % (TINF, EPS))


def _tb54():
    """Outer temperature from conduction = radiation (bisection)."""
    def f(tb):
        cond = K * (TA54 - tb) / (RB * math.log(RB / RA))
        return cond - EPS * SIGMA * (tb ** 4 - TINF ** 4)
    lo, hi = TINF, TA54
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ------------------------------------------------------------------
# PL-53 transient cooling of a long solid cylinder (Bessel series)
# ------------------------------------------------------------------
R0, TI53, TS53 = 0.05, 393.0, 293.0
ALPHA53 = K / (RHO * CP)
FOS = (0.05, 0.2, 0.5)
LAMBDAS = (2.404825557695773, 5.520078110286311, 8.653727912911013,
           11.791534439014281, 14.930917708487787, 18.071063967910924)
DT53 = 1.0e-3 * R0 ** 2 / ALPHA53          # Fourier number 1e-3 per step


def _bessel(n, x, m=2000):
    """J_n(x) = (1/pi) int_0^pi cos(n tau - x sin tau) d tau (Simpson)."""
    h = math.pi / m
    s = 0.0
    for i in range(m + 1):
        tau = i * h
        w = 1 if i in (0, m) else (4 if i % 2 else 2)
        s += w * math.cos(n * tau - x * math.sin(tau))
    return s * h / 3.0 / math.pi


def theta53(r, fo):
    """(T - Ts) / (Ti - Ts), Carslaw & Jaeger par. 7.4 (6 terms)."""
    return sum(2.0 / (l * _bessel(1, l)) * _bessel(0, l * r / R0) *
               math.exp(-l * l * fo) for l in LAMBDAS)


def build_pl53():
    tend = FOS[-1] * R0 ** 2 / ALPHA53
    m = Model("T31", timesteps={"timeperiod": "%.12g s" % tend,
                                "stepsize": "%.12g s" % DT53})
    m.elset("Cilinder", "Staal")
    q = quadmesh(m, "Cilinder", 20, 1, rect(0.0, R0, 0.0, 0.005), order=2)
    _mat(m)
    m.face_selection("Oppervlak", q["edges"]["u1"])
    m.node_selection("Alle", list(range(1, len(m.nodes) + 1)))
    m.add(_temp("Oppervlak", TS53))
    m.add(u"<initialconditions>\n    " + _temp("Alle", TI53) +
          u"\n  </initialconditions>")
    _switch(m)
    return m


def _checks53():
    out = []
    for fo in FOS:
        t = fo * R0 ** 2 / ALPHA53
        for rr in (0.0, 0.5, 0.8):
            out.append(Check(
                "theta r = %g R Fo = %g" % (rr, fo),
                (lambda rr_, t_: lambda r: (
                    r.at("temperature", (rr_ * R0, 0.0, 0.0), time=t_) -
                    TS53) / (TI53 - TS53))(rr, t),
                ref=theta53(rr * R0, fo), tol_abs=0.01, unit="-",
                source="Bessel-reeks, 6 termen (Carslaw & Jaeger par. 7.4); "
                       "1% van het beginverschil"))
    return out


# ------------------------------------------------------------------
# PL-55 plane wall with convection (PLAN, no line)
# ------------------------------------------------------------------
L55, H55 = 0.1, 250.0
Q55 = (TA - TB) / (L55 / K + 1.0 / H55)


def build_pl55():
    m = Model("T30")
    m.elset("Wand", "Staal")
    q = quadmesh(m, "Wand", 5, 2, rect(0.0, L55, 0.0, 0.02), order=1)
    _mat(m)
    m.face_selection("Links", q["edges"]["u0"])
    m.face_selection("Rechts", q["edges"]["u1"])
    m.add(_temp("Links", TA))
    m.add('<convectionbc selection="Rechts"><ambienttemp>%g K</ambienttemp>'
          '<coefficient>%g W/m²/K</coefficient></convectionbc>' % (TB, H55))
    return m


TESTS = [
    Case("PL-50", GROUP, "Radiale geleiding in een buis, thermisch "
         "axisymmetrisch (T30 + **ASTER-PLANE AXIS)", "ther_3d",
         _tube(_pl50),
         [Check("T(r) midden", lambda r: r.at("temperature", (RM, 0, 0)),
                ref=_ln_profile(RM), tol_abs=1e-3 * (TA - TB), unit="K",
                source="T_a + (T_b - T_a) ln(r/a) / ln(b/a)"),
          Check("q_r midden", lambda r: r.at("heatfluxx", (RM, 0, 0)),
                ref=K * (TA - TB) / (RM * math.log(RB / RA)), tol=0.005,
                unit="W/m²", source="k (T_a - T_b) / (r ln(b/a))")],
         note="Ring r = 0,1..0,2 m, h = 10 mm, quad8 10x1, k = 50 W/m/K."),
    Case("PL-51", GROUP, "Buis met een totale warmtestroom op de binnenrand "
         "(T30 + **ASTER-PLANE AXIS)", "ther_3d", _tube(_pl51),
         [Check("T_a - T_b", lambda r: r.at("temperature", (RA, 0, 0)) - TB,
                ref=Q51 * math.log(RB / RA) / (2 * math.pi * K * H),
                tol=0.005, unit="K",
                source="Q ln(b/a) / (2 pi k h): de warmtestroom verdeeld "
                       "over het omwentelingsoppervlak 2 pi a h")],
         note="Als PL-50, T_b vast, heat flow 500 W (360 graden) binnen."),
    Case("PL-52", GROUP, "Buis met convectie op de buitenrand (T30 + "
         "**ASTER-PLANE AXIS)", "ther_3d", _tube(_pl52),
         [Check("T(b)", lambda r: r.at("temperature", (RB, 0, 0)),
                ref=_t52(RB), tol_abs=1e-3 * (TA - TINF), unit="K",
                source="T_a - (T_a - T_inf) ln(r/a) / (ln(b/a) + k/(h b))")],
         note="T_a vast, convectie h = 100 W/m2/K naar 293 K buiten."),
    Case("PL-53", GROUP, "Afkoelende volle cilinder, transient (T31 + "
         "**ASTER-PLANE AXIS)", "ther_3d", build_pl53, _checks53(),
         timeout=3600,
         note="R = 50 mm, quad8 20x1, oppervlak 293 K, begin 393 K, stap "
              "Fo = 1e-3, theta 0,57 (standaard)."),
    Case("PL-54", GROUP, "Buis met straling op de buitenrand (T30 + "
         "**ASTER-PLANE AXIS)", "ther_3d", _tube(_pl54),
         [Check("T(b)", lambda r: r.at("temperature", (RB, 0, 0)),
                ref=_tb54(), tol_abs=1e-3 * (TA54 - TINF), unit="K",
                source="k (T_a - T_b)/(b ln(b/a)) = eps sigma (T_b^4 - "
                       "T_inf^4)")],
         note="T_a = 1000 K vast, straling eps = 0,8 naar 293 K."),
    Case("PL-55", GROUP, "Vlakke wand met convectie (T30-schalen, PLAN, "
         "zonder regel)", "ther_3d", build_pl55,
         [Check("T rechts", lambda r: r.at("temperature", (L55, 0, 0)),
                ref=TB + Q55 / H55, tol=1e-6, unit="K",
                source="serieschakeling geleiding-convectie"),
          Check("q_x", lambda r: r.at("heatfluxx", (L55 / 2, 0, 0)),
                ref=Q55, tol=1e-6, unit="W/m²",
                source="(T_a - T_inf) / (L/k + 1/h)")],
         note="Wand 100 x 20 mm, schaal t = 10 mm, quad4 5x2."),
]
