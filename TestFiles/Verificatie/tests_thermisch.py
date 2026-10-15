# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Thermisch (Mecway T30 -> THER_LINEAIRE STAT, T31 -> THER_LINEAIRE TRAN;
schaalvlak-convectie -> THER_NON_LINE) en thermische spanning (Mecway S30
met <thermalstress> -> MECA_STATIQUE met AFFE_VARC TEMP).

Referenties:
  Incropera, DeWitt, Bergman, Lavine, Fundamentals of Heat and Mass
  Transfer, 6e druk (2007): par. 3.1 (vlakke wand, thermische weerstand in
  serie), par. 3.5 (wand met warmteproductie, vgl. 3.39-3.42), par. 3.6.2
  (vin met geisoleerd uiteinde, tabel 3.4 geval B), par. 5.7 (half-
  oneindig lichaam, vgl. 5.57).
  Carslaw & Jaeger, Conduction of Heat in Solids, 2e druk (1959), par. 2.4.
  Timoshenko & Goodier, Theory of Elasticity, 3e druk, par. 150
  (thermische rek: eps = alpha dT, vrij uitzetten spanningsloos).

Discretisatie: een temperatuurveld dat alleen van x afhangt is in een
gestructureerd hex8-blok de 1D-lineaire-elementoplossing (tensorproduct).
Voor -k T'' = q met lineaire elementen zijn de knoopwaarden dan exact
(Galerkin-oplossing = interpolant in 1D, Strang & Fix par. 1.2); hex20 is
exact voor kwadratische T. Daar is de tolerantie alleen afronding.
Transient (TH-02): de theta-methode met een sprong in de randtemperatuur op
t = 0 heeft een tijdfout van orde dt (de sprong wordt over de eerste stap
uitgesmeerd). Daarnaast vergelijkt TH-02 met een 1D-replica van hetzelfde
discrete schema (lineaire elementen, consistente massa, theta-methode,
_fe1d_theta hieronder): die controleert of theta, dt, rho*cp, lambda,
begin- en randvoorwaarde exact zo in Code-Aster terechtkomen.
"""
import math
from verif_lib import Case, Check, Model, hexmesh, box, quadmesh, rect

GROUP = "Thermisch"
GROUP_TS = "Thermische spanning"


def _mat_th(m, name, k, rho=None, cp=None, plate=None):
    lines = []
    if plate:
        lines.append('<geometric type="Plate" thickness="%g m" />' % plate)
    if rho is not None:
        lines.append('<density type="Simple" density="%g kg/m³" />' % rho)
    th = '<thermal type="Isotropic" thermalconductivity="%g W/m/K"' % k
    if cp is not None:
        th += ' specificheat="%g J/kg/K"' % cp
    lines.append(th + " />")
    m.mat(name, *lines)


def _temp(sel, value):
    return ('<temperature2 selection="%s"><value>%.12g K</value>'
            '<starttime>0 s</starttime><endtime>0 s</endtime></temperature2>'
            % (sel, value))


def _all_elems(m, name="Alles"):
    m.element_selection(name, [e for _n, _m, els in m.elsets
                               for e, _s, _ns, _a in els])


# ==================================================================
# TH-01 STATIONAIR
# ==================================================================
L1, B1, K1, QG, T0 = 0.1, 0.01, 50.0, 1.0e6, 300.0


def build_th01(order, n):
    """Staaf (wand) met warmteproductie, beide uiteinden T0, zijkanten
    geisoleerd. T(x) = T0 + q x (L - x) / (2k)."""
    def build():
        m = Model("T30")
        m.elset("Wand", "Staal")
        g = hexmesh(m, "Wand", n, 1, 1, box(0, L1, 0, B1, 0, B1), order=order)
        _mat_th(m, "Staal", K1)
        m.node_selection("Links", sorted(g["nodes"]["u0"]))
        m.node_selection("Rechts", sorted(g["nodes"]["u1"]))
        _all_elems(m)
        m.add(_temp("Links", T0))
        m.add(_temp("Rechts", T0))
        m.add('<heatgeneration selection="Alles"><value>%g W/m³</value>'
              '</heatgeneration>' % QG)
        return m
    return build


def _rise_gen(x):
    return QG * x * (L1 - x) / (2 * K1)


# Wand met vaste T links en convectie rechts (serieschakeling).
L2, K2, H2, TA2, TB2 = 0.1, 50.0, 250.0, 400.0, 300.0
Q2 = (TA2 - TB2) / (L2 / K2 + 1.0 / H2)          # W/m2
TL2 = TB2 + Q2 / H2


def build_th01c():
    m = Model("T30")
    m.elset("Wand", "Staal")
    g = hexmesh(m, "Wand", 5, 1, 1, box(0, L2, 0, B1, 0, B1))
    _mat_th(m, "Staal", K2)
    m.node_selection("Links", sorted(g["nodes"]["u0"]))
    m.face_selection("Rechts", g["faces"]["u1"])
    m.add(_temp("Links", TA2))
    m.add('<convectionbc selection="Rechts"><ambienttemp>%g K</ambienttemp>'
          '<coefficient>%g W/m²/K</coefficient></convectionbc>' % (TB2, H2))
    return m


# Wand met warmteproductie, x = 0 geisoleerd (symmetrievlak), x = L
# convectie: Ts = Tinf + q L / h, T(x) = Ts + q (L^2 - x^2) / (2k)
# (Incropera vgl. 3.42 en 3.46 met L = halve wanddikte).
L3, K3, H3, TB3 = 0.05, 50.0, 500.0, 300.0
TS3 = TB3 + QG * L3 / H3


def build_th01d():
    m = Model("T30")
    m.elset("Wand", "Staal")
    g = hexmesh(m, "Wand", 10, 1, 1, box(0, L3, 0, B1, 0, B1))
    _mat_th(m, "Staal", K3)
    m.face_selection("Rechts", g["faces"]["u1"])
    _all_elems(m)
    m.add('<heatgeneration selection="Alles"><value>%g W/m³</value>'
          '</heatgeneration>' % QG)
    m.add('<convectionbc selection="Rechts"><ambienttemp>%g K</ambienttemp>'
          '<coefficient>%g W/m²/K</coefficient></convectionbc>' % (TB3, H3))
    return m


# Vin als schaal (PLAN met diktefactor; convectie op het schaalvlak ->
# SOUR_NL, THER_NON_LINE): T(L) - Tinf = (T0 - Tinf) / cosh(mL),
# m = sqrt(h / (k t)) bij convectie op een zijde (Incropera tabel 3.4 B).
LF, WF, TF, KF, HF, TBF, T0F = 0.1, 0.01, 0.002, 50.0, 25.0, 300.0, 400.0
MF = math.sqrt(HF / (KF * TF))


def build_th01e():
    m = Model("T30")
    m.elset("Vin", "Plaat")
    g = quadmesh(m, "Vin", 10, 1, rect(0, LF, 0, WF), order=2)
    _mat_th(m, "Plaat", KF, plate=TF)
    m.node_selection("Voet", sorted(g["nodes"]["u0"]))
    m.face_selection("Vlak", g["faces"])
    m.add(_temp("Voet", T0F))
    m.add('<convectionbc selection="Vlak"><ambienttemp>%g K</ambienttemp>'
          '<coefficient>%g W/m²/K</coefficient></convectionbc>' % (TBF, HF))
    return m


_EXACT = ("knoopwaarden exact (1D-Galerkin, lineaire elementen); tolerantie "
          "= afronding")

TESTS = [
    Case("TH-01a", GROUP, "Wand met warmteproductie, T vast (hex8, 8 el.)",
         "ther_3d", build_th01(1, 8),
         [Check("T_max - T0 (x = L/2)",
                lambda r: r.at("temperature", (L1 / 2, 0, 0)) - T0,
                ref=_rise_gen(L1 / 2), tol=1e-5, unit="K",
                source="q L^2/(8k) (Incropera vgl. 3.41)"),
          Check("T - T0 (x = L/4)",
                lambda r: r.at("temperature", (L1 / 4, 0, 0)) - T0,
                ref=_rise_gen(L1 / 4), tol=1e-5, unit="K",
                source="q x(L-x)/(2k) (Incropera vgl. 3.39)"),
          Check("flux x (x = L/4)",
                lambda r: r.at("heatfluxx", (L1 / 4, 0, 0)),
                ref=-QG * (L1 / 2 - L1 / 4), tol=1e-5, unit="W/m²",
                source="-k dT/dx; knoopgemiddelde van twee elementen = "
                       "centraal verschil, exact voor kwadratische T")],
         note=_EXACT),
    Case("TH-01b", GROUP, "Wand met warmteproductie, T vast (hex20, 2 el.)",
         "ther_3d", build_th01(2, 2),
         [Check("T_max - T0 (x = L/2)",
                lambda r: r.at("temperature", (L1 / 2, 0, 0)) - T0,
                ref=_rise_gen(L1 / 2), tol=1e-5, unit="K",
                source="q L^2/(8k) (Incropera vgl. 3.41)"),
          Check("T - T0 (x = L/4, middenknoop)",
                lambda r: r.at("temperature", (L1 / 4, 0, 0)) - T0,
                ref=_rise_gen(L1 / 4), tol=1e-5, unit="K",
                source="q x(L-x)/(2k); hex20 exact voor kwadratische T"),
          Check("flux x (x = 0)",
                lambda r: r.at("heatfluxx", (0, 0, 0)),
                ref=-QG * L1 / 2, tol=1e-5, unit="W/m²",
                source="-k dT/dx = -q L/2; gradient lineair in hex20 = exact")],
         note="kwadratisch element: exact voor kwadratische T"),
    Case("TH-01c", GROUP, "Wand, T vast links, convectie rechts (Bi = 0,5)",
         "ther_3d", build_th01c,
         [Check("T(L) - Tinf",
                lambda r: r.at("temperature", (L2, 0, 0)) - TB2,
                ref=TL2 - TB2, tol=1e-5, unit="K",
                source="serieschakeling R = L/k + 1/h (Incropera vgl. 3.19)"),
          Check("flux x",
                lambda r: r.at("heatfluxx", (L2 / 2, 0, 0)),
                ref=Q2, tol=1e-5, unit="W/m²",
                source="q = dT / (L/k + 1/h); T lineair -> exact")],
         note="h L/k = 0,5; T lineair, exact met hex8"),
    Case("TH-01d", GROUP, "Wand met warmteproductie, geisoleerd + convectie",
         "ther_3d", build_th01d,
         [Check("Ts - Tinf (x = L)",
                lambda r: r.at("temperature", (L3, 0, 0)) - TB3,
                ref=QG * L3 / H3, tol=1e-5, unit="K",
                source="Ts = Tinf + q L/h (Incropera vgl. 3.46)"),
          Check("T(0) - Ts",
                lambda r: r.at("temperature", (0, 0, 0))
                - r.at("temperature", (L3, 0, 0)),
                ref=QG * L3 ** 2 / (2 * K3), tol=1e-5, unit="K",
                source="q L^2/(2k) (Incropera vgl. 3.42)"),
          Check("T(L/2) - Tinf",
                lambda r: r.at("temperature", (L3 / 2, 0, 0)) - TB3,
                ref=TS3 - TB3 + QG * (L3 ** 2 - (L3 / 2) ** 2) / (2 * K3),
                tol=1e-5, unit="K", source="Incropera vgl. 3.42")],
         note="Bi = hL/k = 0,5; " + _EXACT),
    Case("TH-01e", GROUP, "Vin als schaal (quad8, convectie op het vlak)",
         "ther_3d", build_th01e,
         [Check("T(L) - Tinf (uiteinde)",
                lambda r: r.at("temperature", (LF, 0, 0)) - TBF,
                ref=(T0F - TBF) / math.cosh(MF * LF), tol=1e-3, unit="K",
                source="(T0-Tinf)/cosh(mL), m = sqrt(h/(k t)) (Incropera "
                       "tabel 3.4 geval B)"),
          Check("T(L/2) - Tinf",
                lambda r: r.at("temperature", (LF / 2, 0, 0)) - TBF,
                ref=(T0F - TBF) * math.cosh(MF * LF / 2) / math.cosh(MF * LF),
                tol=1e-3, unit="K", source="Incropera tabel 3.4 geval B")],
         note="schaal 2 mm als PLAN met diktefactor, convectie op vlak 5 als "
              "SOUR_NL; mL = 1,58, quad8 met 10 elementen: "
              "discretisatiefout ~(mh)^4 < 1e-4"),
]


# ==================================================================
# TH-02 TRANSIENT: HALF-ONEINDIG LICHAAM
# ==================================================================
# Staaf 0,1 m (zijkanten en eind geisoleerd), begin 300 K, x = 0 vanaf
# t = 0 op 400 K. alpha = k/(rho cp) = 1e-5 m2/s; tot t = 40 s is de
# indringdiepte 2 sqrt(alpha t) = 0,04 m, de invloed van het geisoleerde
# eind (spiegelterm erfc((2L - x)/(2 sqrt(alpha t)))) < 1e-9.
LT, KT, RHOT, CPT, TI, TS = 0.1, 10.0, 1000.0, 1000.0, 300.0, 400.0
ALPHA = KT / (RHOT * CPT)
XS = (0.004, 0.008, 0.016)


def _erf_ref(x, t):
    return TS + (TI - TS) * math.erf(x / (2.0 * math.sqrt(ALPHA * t)))


def _fe1d_theta(n, dt, theta, tend, x):
    """
    1D-replica van het discrete probleem: n lineaire elementen op [0, LT],
    consistente massa, theta-methode, T(0) = TS vanaf de eerste stap,
    begin TI. Geeft T(x, tend). Thomas-algoritme (tridiagonaal).
    """
    h = LT / n
    N = n + 1
    a = ALPHA
    # (M/dt + theta K) T1 = (M/dt - (1-theta) K) T0, M en K per lengte.
    md, mo = 2.0 * h / 6.0, h / 6.0
    kd, ko = a / h, -a / h

    def diag(i):
        return 1.0 if i in (0, N - 1) else 2.0

    T = [TI] * N
    for _s in range(int(round(tend / dt))):
        lo, di, up, rhs = [0.0] * N, [0.0] * N, [0.0] * N, [0.0] * N
        for i in range(N):
            f = diag(i)
            di[i] = f * md / dt + theta * f * kd
            r = (f * md / dt - (1 - theta) * f * kd) * T[i]
            if i > 0:
                lo[i] = mo / dt + theta * ko
                r += (mo / dt - (1 - theta) * ko) * T[i - 1]
            if i < N - 1:
                up[i] = mo / dt + theta * ko
                r += (mo / dt - (1 - theta) * ko) * T[i + 1]
            rhs[i] = r
        di[0], up[0], rhs[0] = 1.0, 0.0, TS
        for i in range(1, N):
            w = lo[i] / di[i - 1]
            di[i] -= w * up[i - 1]
            rhs[i] -= w * rhs[i - 1]
        T[N - 1] = rhs[N - 1] / di[N - 1]
        for i in range(N - 2, -1, -1):
            T[i] = (rhs[i] - up[i] * T[i + 1]) / di[i]
    return T[int(round(x / h))]


def build_th02(n, dt, tend):
    def build():
        m = Model("T31", timesteps={"timeperiod": "%g s" % tend,
                                    "stepsize": "%g s" % dt})
        m.elset("Staaf", "Mat")
        g = hexmesh(m, "Staaf", n, 1, 1, box(0, LT, 0, 0.002, 0, 0.002))
        _mat_th(m, "Mat", KT, rho=RHOT, cp=CPT)
        m.node_selection("Oppervlak", sorted(g["nodes"]["u0"]))
        m.node_selection("Alle", list(range(1, len(m.nodes) + 1)))
        m.add(_temp("Oppervlak", TS))
        m.add(u"<initialconditions>\n    " + _temp("Alle", TI)
              + u"\n  </initialconditions>")
        return m
    return build


def _th02_checks(n, dt, theta, times, tol_erf, replica=True, xs=XS):
    out = []
    for t in times:
        for x in xs:
            out.append(Check(
                "T-Ti x=%g mm t=%g s" % (x * 1e3, t),
                (lambda x_, t_: lambda r: r.at("temperature", (x_, 0, 0),
                                               time=t_) - TI)(x, t),
                ref=_erf_ref(x, t) - TI, tol_abs=tol_erf, unit="K",
                source="Ts + (Ti-Ts) erf(x/(2 sqrt(alpha t))) (Carslaw & "
                       "Jaeger par. 2.4; Incropera vgl. 5.57)"))
    if replica:
        t, x = times[0], xs[1]
        out.append(Check(
            "zelfde schema 1D x=%g mm t=%g s" % (x * 1e3, t),
            (lambda x_, t_: lambda r: r.at("temperature", (x_, 0, 0),
                                           time=t_) - TI)(x, t),
            ref=_fe1d_theta(n, dt, theta, t, x) - TI, tol_abs=1e-4,
            in_series=False,
            unit="K", source="1D-replica van het discrete schema "
                             "(_fe1d_theta, theta = %g); tolerantie 1e-4 K: "
                             "transient schrijft de bridge float32 "
                             "(bridge_thermal: precision 'single'), ulp bij "
                             "380 K = 3e-5 K" % theta))
    return out


_ERF_TOL = 0.5
_ERF_NOTE = ("tolerantie 0,5 K = 0,5 % van de sprong: geschatte tijdfout "
             "(orde dt door de sprong op t = 0) <= 0,25 K bij dt = 0,1 s, "
             "ruimtefout < 0,02 K bij h = 1 mm")

TESTS += [
    Case("TH-02a", GROUP, "Half-oneindig lichaam, theta 0,57 (standaard)",
         "ther_3d", build_th02(100, 0.1, 40.0),
         _th02_checks(100, 0.1, 0.57, (10.0, 40.0), _ERF_TOL),
         settings={"theta": 0.57}, note=_ERF_NOTE),
    Case("TH-02b", GROUP, "Half-oneindig lichaam, theta 0,5 (Crank-Nicolson)",
         "ther_3d", build_th02(100, 0.1, 40.0),
         _th02_checks(100, 0.1, 0.5, (10.0, 40.0), _ERF_TOL),
         settings={"theta": 0.5}, series="TH-02 tijdstap (theta 0,5)",
         h=0.1, note=_ERF_NOTE),
    Case("TH-02c", GROUP, "Half-oneindig lichaam, theta 1,0 (Euler impliciet)",
         "ther_3d", build_th02(100, 0.1, 40.0),
         _th02_checks(100, 0.1, 1.0, (10.0, 40.0), _ERF_TOL),
         settings={"theta": 1.0}, series="TH-02 tijdstap (theta 1,0)",
         h=0.1, note=_ERF_NOTE),
]
# Tijdstapconvergentie (h = 1 mm vast; de reeks gebruikt h = dt).
for _dt, _sfx in ((0.4, "d"), (0.2, "e"), (0.05, "f")):
    for _th, _nm in ((0.5, "theta 0,5"), (1.0, "theta 1,0")):
        _id = "TH-02%s%s" % (_sfx, "1" if _th == 0.5 else "2")
        TESTS.append(Case(
            _id, GROUP, "Half-oneindig lichaam, dt = %g s, %s" % (_dt, _nm),
            "ther_3d", build_th02(100, _dt, 10.0),
            _th02_checks(100, _dt, _th, (10.0,), 1.0),
            settings={"theta": _th}, series="TH-02 tijdstap (%s)" % _nm,
            h=_dt, note="tijdstapreeks; tolerantie 1 K (grootste stap 0,4 s: "
                        "geschatte fout 0,5 K)"))
# Grove tijdstap: dt alpha / h^2 = 10. Crank-Nicolson schiet bij het
# oppervlak over (geen discreet maximumprincipe), theta 1 niet.
for _th, _sfx in ((0.5, "g"), (0.57, "h"), (1.0, "i")):
    TESTS.append(Case(
        "TH-02" + _sfx, GROUP,
        "Half-oneindig lichaam, grove stap dt = 1 s, theta %g" % _th,
        "ther_3d", build_th02(100, 1.0, 4.0),
        _th02_checks(100, 1.0, _th, (4.0,), 5.0, xs=(0.001, 0.008, 0.016)),
        settings={"theta": _th},
        note="grove stap: schemafout tot ~3 K (1D-schatting), tolerantie "
             "5 K; het doel is de vergelijking met hetzelfde schema in 1D "
             "en het verschil tussen de theta's"))


# ==================================================================
# TH-03 THERMISCHE SPANNING (mechanisch lineair statisch)
# ==================================================================
LB, BB = 1.0, 0.1
E, NU, ALPHA_T = 210e9, 0.3, 1.2e-5
TREF, TNEW = 293.15, 393.15
DT = TNEW - TREF


def build_th03(clamped):
    def build():
        m = Model("S30")
        m.elset("Staaf", "Staal")
        g = hexmesh(m, "Staaf", 4, 1, 1, box(0, LB, 0, BB, 0, BB))
        m.mat("Staal", '<mechanical type="Isotropic" youngsmodulus="210000 '
              'MPa" poissonratio="0.3" thermalexpansion="%g 1/K" />'
              % ALPHA_T)
        m.node_selection("Alle", list(range(1, len(m.nodes) + 1)))
        m.face_selection("X0", g["faces"]["u0"])
        m.face_selection("Y0", g["faces"]["v0"])
        m.face_selection("Z0", g["faces"]["w0"])
        m.node_selection("XL", sorted(g["nodes"]["u1"]))
        faces = [("X0", "1", "0", "0"), ("Y0", "0", "1", "0"),
                 ("Z0", "0", "0", "1")]
        if clamped:
            m.face_selection("XLv", g["faces"]["u1"])
            faces.append(("XLv", "1", "0", "0"))
        for sel, x, y, z in faces:
            m.add('<displacement selection="%s"><value>0 m</value><x>%s</x>'
                  '<y>%s</y><z>%s</z></displacement>' % (sel, x, y, z))
        m.add('<thermalstress><referencetemperature>%g K'
              '</referencetemperature></thermalstress>' % TREF)
        m.add(_temp("Alle", TNEW))
        return m
    return build


TESTS += [
    Case("TH-03a", GROUP_TS, "Vrije thermische uitzetting (hex8)",
         "lin_static_3d", build_th03(False),
         [Check("u_x eind", lambda r: r.at("displx", (LB, 0, 0)),
                ref=ALPHA_T * DT * LB, tol=1e-6, unit="m",
                source="alpha dT L (Timoshenko & Goodier par. 150)"),
          Check("u_y zijkant", lambda r: r.at("disply", (LB, BB, 0)),
                ref=ALPHA_T * DT * BB, tol=1e-6, unit="m",
                source="alpha dT b"),
          Check("max |sigma_xx|",
                lambda r: max(abs(v) for v in r.step()["stressxx"].values()),
                ref=0.0, tol_abs=1e-6 * E * ALPHA_T * DT, unit="Pa",
                source="vrij uitzetten: spanningsloos (tolerantie 1e-6 "
                       "E alpha dT)")],
         note="statisch bepaald opgelegd (drie symmetrievlakken); uniforme "
              "rek is exact met hex8"),
    Case("TH-03b", GROUP_TS, "Staaf ingeklemd in x, uniforme opwarming",
         "lin_static_3d", build_th03(True),
         [Check("sigma_xx", lambda r: r.at("stressxx", (LB / 2, BB / 2, BB)),
                ref=-E * ALPHA_T * DT, tol=1e-6, unit="Pa",
                source="-E alpha dT (verhinderde uitzetting, dwarsrichting "
                       "vrij)"),
          Check("max |sigma_yy|",
                lambda r: max(abs(v) for v in r.step()["stressyy"].values()),
                ref=0.0, tol_abs=1e-6 * E * ALPHA_T * DT, unit="Pa",
                source="dwarsrichting vrij"),
          Check("u_y zijkant", lambda r: r.at("disply", (LB / 2, BB, 0)),
                ref=(1 + NU) * ALPHA_T * DT * BB, tol=1e-6, unit="m",
                source="eps_y = alpha dT - nu sigma_xx/E = (1+nu) alpha dT"),
          Check("|reactie x| op x = L",
                lambda r: abs(r.total("reactionforcex", "XL")),
                ref=E * ALPHA_T * DT * BB * BB, tol=1e-6, unit="N",
                source="E alpha dT A")],
         note="uniforme spanningstoestand: exact met hex8"),
]


# ==================================================================
# TH-04 VERLIJMD CONTACT (contact2 bonded) IN EEN THERMISCHE ANALYSE
# ==================================================================
# Twee blokken met eigen knopen, x = 0..L/2 (A) en L/2..L (B), verlijmd op
# x = L/2; T vast links (TA4) en rechts (TB4), zijkanten geisoleerd.
# Tie / constraint equations: T lineair, op de naad (TA4 + TB4) / 2.
# Elastic (weerstandslaag, Mecway manual v33 par. 9.9.1): drie weerstanden
# in serie, q = dT / (L/(2k) + 1/h + L/(2k)) (Incropera par. 3.1, vgl.
# 3.19); sprong over de naad q / h.
L4, B4, K4, TA4, TB4, H4 = 0.1, 0.01, 50.0, 300.0, 400.0, 2000.0
Q4 = (TB4 - TA4) / (L4 / K4 + 1.0 / H4)
BOND4 = ('<contact2 selectionmaster="Lijm_A" selectionslave="Lijm_B" '
         'type="{0}"><tolerance>0 m</tolerance><normalstiffness>{1} Pa/m'
         '</normalstiffness><tangentialstiffness>{1} Pa/m'
         '</tangentialstiffness><frictioncoefficient>0'
         '</frictioncoefficient>{2}</contact2>')


def build_th04(kind, na, nb, order=1):
    """kind: bondedtie / bondedce / bondedelastic; na, nb: (nx, ny) per
    blok (ny = nz)."""
    def build():
        m = Model("T30")
        _mat_th(m, "Staal", K4)
        m.elset("Blok_A", "Staal")
        a = hexmesh(m, "Blok_A", na[0], na[1], na[1],
                    box(0, L4 / 2, 0, B4, 0, B4), order=order)
        m._index = {}                    # B: eigen knopen
        m.elset("Blok_B", "Staal")
        b = hexmesh(m, "Blok_B", nb[0], nb[1], nb[1],
                    box(L4 / 2, L4, 0, B4, 0, B4), order=order)
        m.node_selection("Links", sorted(a["nodes"]["u0"]))
        m.node_selection("Rechts", sorted(b["nodes"]["u1"]))
        m.node_selection("Naad_A", sorted(a["nodes"]["u1"]))
        m.node_selection("Naad_B", sorted(b["nodes"]["u0"]))
        m.face_selection("Lijm_A", a["faces"]["u1"])
        m.face_selection("Lijm_B", b["faces"]["u0"])
        m.add(_temp("Links", TA4))
        m.add(_temp("Rechts", TB4))
        elastic = kind == "bondedelastic"
        m.add(BOND4.format(
            kind, "1e+12" if elastic else "0",
            "<conductanceperarea>%g W/m²/K</conductanceperarea>" % H4
            if elastic else ""))
        return m
    return build


def build_th04d():
    """Twee schaalstroken (quad4, 2 mm, PLAN) in een vlak met eigen
    knopen: rand van B (4 knopen) op de laatste kolom van A (3 knopen op
    de naad), constraint equations."""
    m = Model("T30")
    _mat_th(m, "Plaat", K4, plate=0.002)
    m.elset("Deel_A", "Plaat")
    a = quadmesh(m, "Deel_A", 5, 2, rect(0, L4 / 2, 0, B4))
    m._index = {}
    m.elset("Deel_B", "Plaat")
    b = quadmesh(m, "Deel_B", 5, 3, rect(L4 / 2, L4, 0, B4))
    m.face_selection("Lijm_A", [(a["elems"][(4, j)], 5) for j in range(2)])
    m.face_selection("Lijm_B", b["edges"]["u0"])
    m.node_selection("Links", sorted(a["nodes"]["u0"]))
    m.node_selection("Rechts", sorted(b["nodes"]["u1"]))
    m.node_selection("Naad_A", sorted(a["nodes"]["u1"]))
    m.node_selection("Naad_B", sorted(b["nodes"]["u0"]))
    m.add(_temp("Links", TA4))
    m.add(_temp("Rechts", TB4))
    m.add(BOND4.format("bondedce", "0", ""))
    return m


def _th04_tie_checks(tol=1e-6, tol_q=1e-5, src=""):
    lin = "T lineair over de hele staaf (vlakke wand, Incropera par. 3.1)"
    return [
        Check("T naad (kant A)", lambda r: r.mean("temperature", "Naad_A"),
              ref=(TA4 + TB4) / 2, tol=tol, unit="K", source=lin + src),
        Check("T naad (kant B)", lambda r: r.mean("temperature", "Naad_B"),
              ref=(TA4 + TB4) / 2, tol=tol, unit="K",
              source="verlijmd: gelijk aan kant A" + src),
        Check("T (x = L/5)", lambda r: r.at("temperature", (L4 / 5, 0, 0)),
              ref=TA4 + (TB4 - TA4) / 5, tol=tol, unit="K", source=lin),
        Check("flux x (x = 3L/4)",
              lambda r: r.at("heatfluxx", (3 * L4 / 4, 0, 0)),
              ref=-K4 * (TB4 - TA4) / L4, tol=tol_q, unit="W/m²",
              source="-k dT/dx (Fourier)")]


TESTS += [
    Case("TH-04a", GROUP, "Verlijmd contact (tie), twee blokken, conform",
         "ther_3d", build_th04("bondedtie", (5, 1), (5, 1)),
         _th04_tie_checks(),
         note="eigen knopen aan beide kanten, AFFE_CHAR_THER LIAISON_MAIL; "
              "T lineair -> exact. Mecway 34 met CCX: 350 K op de naad"),
    Case("TH-04b", GROUP, "Verlijmd contact (constraint eq.), niet-conform",
         "ther_3d", build_th04("bondedce", (5, 2), (4, 3)),
         _th04_tie_checks(1e-3, 5e-3, "; Mecway 34 (intern): 350,0668 K"),
         note="naad 2x2 (master) tegen 3x3 (slave): knoop-op-vlak-koppeling "
              "is niet conform (tussen de slave-knopen een kleine sprong), "
              "dus niet exact: naad 350,067 K, flux +0,17 %; Mecway 34 "
              "(interne solver) zelfde koppeling, verschil per knoop "
              "< 0,003 K. Tolerantie 0,1 % (T) en 0,5 % (flux)"),
    Case("TH-04c", GROUP, "Verlijmd contact elastic: thermische weerstand",
         "ther_3d", build_th04("bondedelastic", (5, 1), (5, 1)),
         [Check("T naad (kant A)", lambda r: r.mean("temperature", "Naad_A"),
                ref=TA4 + Q4 * L4 / (2 * K4), tol=1e-6, unit="K",
                source="weerstanden in serie L/(2k) + 1/h + L/(2k) "
                       "(Incropera par. 3.1, vgl. 3.19)"),
          Check("T naad (kant B)", lambda r: r.mean("temperature", "Naad_B"),
                ref=TB4 - Q4 * L4 / (2 * K4), tol=1e-6, unit="K",
                source="idem"),
          Check("flux x (x = L/4)",
                lambda r: r.at("heatfluxx", (L4 / 4, 0, 0)),
                ref=-Q4, tol=1e-5, unit="W/m²",
                source="q = dT / (L/k + 1/h)")],
         note="h = 2000 W/m²K (Mecway 'Thermal conductance per unit "
              "area', <conductanceperarea>), ECHANGE_PAROI; sprong q/h = "
              "20 K; T lineair per blok -> exact. Mecway 34 met CCX: 340 / "
              "360 K"),
    Case("TH-04d", GROUP, "Verlijmd contact, schaalrand op schaalvlak (PLAN)",
         "ther_3d", build_th04d,
         _th04_tie_checks(1e-3, 5e-3, "; Mecway 34 (intern): 350,0366 K"),
         note="schalen als PLAN met diktefactor; naad 3 tegen 4 knopen, "
              "dus niet conform (zie TH-04b): naad 350,036 K; Mecway 34 "
              "(interne solver) verschil per knoop < 0,006 K. Tolerantie "
              "0,1 % (T) en 0,5 % (flux)"),
]
