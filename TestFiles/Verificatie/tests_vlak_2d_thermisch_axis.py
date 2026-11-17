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


# ------------------------------------------------------------------
# PL-56 / PL-57 solid cylinder with internal heat (the revolved volume)
# ------------------------------------------------------------------
# A solid cylinder R0, surface at T_s, uniform heat q (W/m3): T(0) - T(R) =
# q R^2 / (4 k) (Incropera eq. 3.58). PL-56 as Internal heat generation
# (per volume, no factor), PL-57 as a total Heat flow on the elements
# (W, 360 degrees: Q = q pi R^2 h, spread over the revolved volume).
Q56 = 1.0e6


def build_pl56(total=False):
    def build():
        m = Model("T30")
        m.elset("Cilinder", "Staal")
        q = quadmesh(m, "Cilinder", 10, 1, rect(0.0, R0, 0.0, 0.005),
                     order=2)
        _mat(m)
        m.face_selection("Oppervlak", q["edges"]["u1"])
        m.element_selection("Alles", sorted(q["elems"].values()))
        m.add(_temp("Oppervlak", TS53))
        if total:
            m.add('<heatflow selection="Alles"><value>%.12g W</value>'
                  '</heatflow>' % (Q56 * math.pi * R0 ** 2 * 0.005))
        else:
            m.add('<heatgeneration selection="Alles"><value>%g W/m³'
                  '</value></heatgeneration>' % Q56)
        _switch(m)
        return m
    return build


_D56 = Q56 * R0 ** 2 / (4.0 * K)
TESTS += [
    Case("PL-56", GROUP, "Volle cilinder met warmteproductie (T30 + "
         "**ASTER-PLANE AXIS)", "ther_3d", build_pl56(),
         [Check("T(0) - T(R)", lambda r: r.at("temperature", (0, 0, 0)) -
                TS53, ref=_D56, tol=1e-3, unit="K",
                source="q R^2 / (4 k) (Incropera vgl. 3.58)")],
         note="R = 50 mm, quad8 10x1, internal heat generation 1e6 W/m3."),
    Case("PL-57", GROUP, "Volle cilinder met een totale warmtestroom op de "
         "elementen (T30 + **ASTER-PLANE AXIS)", "ther_3d",
         build_pl56(total=True),
         [Check("T(0) - T(R)", lambda r: r.at("temperature", (0, 0, 0)) -
                TS53, ref=_D56, tol=1e-3, unit="K",
                source="q R^2 / (4 k) met q = Q / (pi R^2 h)")],
         note="Als PL-56 met heat flow Q = q pi R^2 h (360 graden) op de "
              "elementen: verdeeld over het omwentelingsvolume."),
]


# ------------------------------------------------------------------
# PL-58 thermal -> mechanical chain in AXIS (S44d piece 2)
# ------------------------------------------------------------------
# The tube of PL-24 (tests_vlak_2d_thermisch) as T31: the inner edge at 393
# K, the outer at 293 K, start 293 K, Thermal stress with reference 293 K,
# both ends held axially (plane strain); ten steps of 2000 s with theta = 1
# (steady after about 2.5 diffusion times R^2/alpha), so the last state is
# the steady ln profile. Checks against the closed form with the
# tolerances of PL-24 (the FE temperatures at the nodes are not the exact
# ln values that PL-24 puts in, so not "= PL-24 within 1e-6").
import tests_vlak_2d_thermisch as p2t


def build_pl58():
    m = Model("T31", timesteps={"timeperiod": "20000 s",
                                "stepsize": "2000 s"})
    m.elset("Buis", "Staal")
    q = quadmesh(m, "Buis", p2t.NR, 1, rect(RA, RB, 0.0, H), order=2)
    m.mat("Staal", '<geometric type="Plate" thickness="10 mm" />',
          p2t.STEEL, '<density type="Simple" density="%g kg/m³" />' % RHO,
          '<thermal type="Isotropic" thermalconductivity="%g W/m/K" '
          'specificheat="%g J/kg/K" />' % (K, CP))
    e = q["edges"]
    m.face_selection("Binnen", e["u0"])
    m.face_selection("Buiten", e["u1"])
    m.face_selection("Onder", e["v0"])
    m.face_selection("Boven", e["v1"])
    m.node_selection("Ondern", sorted(q["nodes"]["v0"]))
    m.node_selection("Alle", list(range(1, len(m.nodes) + 1)))
    for sel in ("Onder", "Boven"):
        m.add('<displacement selection="%s"><value>0 m</value><x>0</x>'
              '<y>1</y><z>0</z></displacement>' % sel)
    m.add(_temp("Binnen", TA))
    m.add(_temp("Buiten", TB))
    m.add(u"<initialconditions>\n    " + _temp("Alle", TB) +
          u"\n  </initialconditions>")
    m.add('<thermalstress><referencetemperature>%g K</referencetemperature>'
          '</thermalstress>' % TB)
    for fv in ("displacement", "stress", "reaction force"):
        m.add('<fieldvariable name="%s" />' % fv)
    _switch(m)
    return m


T58 = 20000.0


def _checks58():
    src = "Timoshenko & Goodier par. 150, vlakke rek (als PL-24)"
    at = lambda var, pt: lambda r: r.at(var, pt, time=T58)
    return [
        Check("u_r binnenwand", at("displx", (RA, 0, 0)),
              ref=p2t.u_r(RA, False), tol=1e-3, unit="m", source=src),
        Check("u_r buitenwand", at("displx", (RB, 0, 0)),
              ref=p2t.u_r(RB, False), tol=1e-3, unit="m", source=src),
        Check("sigma_r midden", at("stressxx", (p2t.RM, 0, 0)),
              ref=p2t.sig_r(p2t.RM), tol=0.012, unit="Pa", source=src),
        Check("sigma_theta binnenwand", at("stresszz", (RA, 0, 0)),
              ref=p2t.sig_t(RA), tol=0.01, unit="Pa", source=src),
        Check("sigma_theta buitenwand", at("stresszz", (RB, 0, 0)),
              ref=p2t.sig_t(RB), tol=0.01, unit="Pa", source=src),
        Check("sigma_z binnenwand", at("stressyy", (RA, 0, 0)),
              ref=p2t.sig_z(RA, False), tol=0.01, unit="Pa", source=src),
        Check("sigma_z buitenwand", at("stressyy", (RB, 0, 0)),
              ref=p2t.sig_z(RB, False), tol=0.01, unit="Pa", source=src),
        Check("T(r) midden (thermisch deel)", at("temperature",
                                                 (p2t.RM, 0, 0)),
              ref=_ln_profile(p2t.RM), tol_abs=1e-3 * (TA - TB), unit="K",
              source="T_a + (T_b - T_a) ln(r/a) / ln(b/a) (stationair)"),
        Check("som R_y onder (360 graden)",
              lambda r: r.total("reactionforcey", "Ondern", time=T58),
              ref=2.0 * math.pi * p2t.ALPHA * p2t.E * p2t._IB, tol=1e-3,
              unit="N", in_series=False,
              source="2 pi alpha E int theta r dr (de factor 2 pi in de "
                     "keten)")] + [
        Check("%s = PL-24 (knooptemperaturen)" % name,
              fn, ref=ref, tol=1e-4, unit=unit, in_series=False,
              source="PL-24 (MECA_STATIQUE met de exacte ln-temperatuur "
                     "in de knopen, = Mecway SA0); 1e-4: de FE-temperaturen "
                     "van de keten zijn niet de exacte ln-waarden")
        for name, fn, ref, unit in (
            ("u_r binnenwand", at("displx", (RA, 0, 0)), p2t.MW["PL-24"][0],
             "m"),
            ("u_r buitenwand", at("displx", (RB, 0, 0)), p2t.MW["PL-24"][1],
             "m"),
            ("som R_y onder", lambda r: r.total("reactionforcey", "Ondern",
                                                time=T58),
             p2t.MW["PL-24"][2], "N"))]


TESTS.append(Case(
    "PL-58", GROUP, "Thermomechanische keten, dikwandige buis (T31 + "
    "Thermal stress + **ASTER-PLANE AXIS)", "ther_3d", build_pl58,
    _checks58(), settings={"theta": 1.0}, timeout=3600,
    note="De buis van PL-24 als T31: binnen 393 K, buiten 293 K, 10 stappen "
         "van 2000 s, theta 1, Thermal stress 293 K, einden axiaal vast."))


# PL-59: PL-58 with an internal pressure P59 on the inner edge (edge loads
# in the chain): the plane-strain Lame solution superposed on the thermal
# one (linear elastic): u_r(a) and the axial reaction.
P59 = 50.0e6
_A59 = P59 * RA ** 2 / (RB ** 2 - RA ** 2)
_B59 = P59 * RA ** 2 * RB ** 2 / (RB ** 2 - RA ** 2)
_UR59 = (1.0 + p2t.NU) / p2t.E * ((1.0 - 2.0 * p2t.NU) * _A59 * RA +
                                  _B59 / RA)


def build_pl59():
    m = build_pl58()
    m.add('<surfacepressure selection="Binnen"><normal>%g Pa</normal>'
          '</surfacepressure>' % P59)
    return m


TESTS.append(Case(
    "PL-59", GROUP, "Thermomechanische keten met inwendige druk (T31 + "
    "Thermal stress + **ASTER-PLANE AXIS)", "ther_3d", build_pl59,
    [Check("u_r binnenwand", lambda r: r.at("displx", (RA, 0, 0), time=T58),
           ref=p2t.u_r(RA, False) + _UR59, tol=1e-3, unit="m",
           source="thermisch (Timoshenko & Goodier par. 150) + Lame, vlakke "
                  "rek"),
     Check("som R_y onder (360 graden)",
           lambda r: r.total("reactionforcey", "Ondern", time=T58),
           ref=2.0 * math.pi * p2t.ALPHA * p2t.E * p2t._IB -
           2.0 * p2t.NU * _A59 * math.pi * (RB ** 2 - RA ** 2), tol=1e-3,
           unit="N", in_series=False,
           source="thermisch 2 pi alpha E int theta r dr min Lame sigma_z "
                  "pi (b^2 - a^2), sigma_z = 2 nu A")],
    settings={"theta": 1.0}, timeout=3600,
    note="Als PL-58 met 50 MPa inwendige druk op de binnenrand."))
