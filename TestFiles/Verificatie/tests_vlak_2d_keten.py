# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
The thermal -> mechanical chain (Mecway Thermal Transient T31 with Thermal
stress) in 2D and with plasticity in AXIS (Scripts/bridge_plane.
_apply_thermal and _plane_chain, bridge_thermomech). Explanation:
docs/Verificatie.md chapter 2D and axisymmetric (PL).

PL-75  C_PLAN: a strip L x W (thickness 1 mm), T = 393 K on the bottom
       edge, 293 K on the top edge, start and reference 293 K; both ends
       held along x (u_y free). Steady state: T linear in y and the exact
       field sigma_xx = -E alpha dT(y), sigma_yy = 0, eps_yy = (1 + nu)
       alpha dT, so u_y(W) = (1 + nu) alpha W dT_mean; the reaction of an end
       E alpha t int dT dy.
PL-76  the same strip in D_PLAN (eps_zz = 0): sigma_xx = sigma_zz = -E alpha
       dT / (1 - nu), eps_yy = alpha dT (1 + nu) / (1 - nu).
PL-77  PL-75 with a pressure on the top edge and the bottom edge held in
       y (edge loads in the plane chain).
PL-78  AXIS with plasticity: a ring a .. b, both ends held axially, heated
       uniformly by 200 K (every node on the inner or outer edge, so the
       temperature is uniform from the first step). Uniaxial axial stress
       (a uniform radial expansion leaves sigma_r = sigma_theta = 0);
       bilinear isotropic with Mecway's tangent modulus as the plastic
       modulus H: sigma = -(sigma_y + H p), p = (E alpha dT - sigma_y) /
       (E + H).
PL-79  the plastic case of PL-78 in C_PLAN (a strip of one row of quad4,
       ends held along x).
PL-80  D_PLAN, thickness 2 mm: a total heat flow Q (W) on the bottom edge,
       T0 on the top edge (the heat flow per length x thickness, bridge_
       thermal), and a total force F (N) on the top edge (/ t in the 2D
       load translation), bottom held in y, ends held in x.
"""
import math

from verif_lib import Case, Check, Model, quadmesh, rect

GROUP = "2D en axisymmetrisch"
E, NU, ALPHA = 210e9, 0.3, 1.2e-5
K, RHO, CP = 50.0, 7800.0, 500.0
T0, T1 = 293.0, 393.0                # start/reference, hot edge [K]
L, W, T = 0.05, 0.01, 0.001          # strip [m]
RA, RB = 0.10, 0.11                  # ring [m]
SY, H = 250.0e6, 2.1e9               # yield stress, plastic modulus [Pa]
DT_P = 200.0                         # uniform heating of PL-75/76 [K]
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" thermalexpansion="1.2e-05 1/K" />')
THERMAL = ('<density type="Simple" density="%g kg/m³" />' % RHO,
           '<thermal type="Isotropic" thermalconductivity="%g W/m/K" '
           'specificheat="%g J/kg/K" />' % (K, CP))
PLASTIC = ('<plastic type="BilinearIsotropic" yieldstrength="%g Pa" '
           'tangentmodulus="%g Pa" />' % (SY, H))
TEND = 100.0


def _temp(sel, value):
    return ('<temperature2 selection="%s"><value>%.12g K</value>'
            '<starttime>0 s</starttime><endtime>0 s</endtime></temperature2>'
            % (sel, value))


def _hold(m, sel, axis):
    d = dict((a, 1 if a == axis else 0) for a in "xyz")
    m.add('<displacement selection="{0}"><value>0 m</value><x>{x}</x>'
          '<y>{y}</y><z>{z}</z></displacement>'.format(sel, **d))


def _finish(m, mod, hot_sels):
    m.node_selection("Alle", list(range(1, len(m.nodes) + 1)))
    for sel, value in hot_sels:
        m.add(_temp(sel, value))
    m.add(u"<initialconditions>\n    " + _temp("Alle", T0) +
          u"\n  </initialconditions>")
    m.add('<thermalstress><referencetemperature>%g K</referencetemperature>'
          '</thermalstress>' % T0)
    for fv in ("displacement", "stress", "reaction force"):
        m.add('<fieldvariable name="%s" />' % fv)
    m.add(u"<ccxmodeldefinition>**ASTER-PLANE %s</ccxmodeldefinition>" % mod)


def build_strip(mod, plastic=False):
    """plastic: one row of quad4 (all nodes on the top or bottom edge),
    both edges at T0 + DT_P; otherwise 10 x 4 quad8 with T1 at the bottom
    and T0 at the top."""
    def build():
        m = Model("T31", timesteps={"timeperiod": "%g s" % TEND,
                                    "stepsize": "%g s" % (TEND / 10)})
        m.elset("Strook", "Staal")
        if plastic:
            q = quadmesh(m, "Strook", 10, 1, rect(0.0, L, 0.0, W), order=1)
        else:
            q = quadmesh(m, "Strook", 10, 4, rect(0.0, L, 0.0, W), order=2)
        m.mat("Staal", '<geometric type="Plate" thickness="%g mm" />'
              % (T * 1000), STEEL, *(THERMAL + ((PLASTIC,) if plastic
                                                 else ())))
        e = q["edges"]
        m.face_selection("Onder", e["v0"])
        m.face_selection("Boven", e["v1"])
        m.node_selection("Links", sorted(q["nodes"]["u0"]))
        m.node_selection("Rechts", sorted(q["nodes"]["u1"]))
        m.node_selection("Punt", [m.node(0.0, 0.0, 0.0)])
        _hold(m, "Links", "x")
        _hold(m, "Rechts", "x")
        _hold(m, "Punt", "y")
        if plastic:
            _finish(m, mod, (("Onder", T0 + DT_P), ("Boven", T0 + DT_P)))
        else:
            _finish(m, mod, (("Onder", T1), ("Boven", T0)))
        return m
    return build


def build_ring():
    m = Model("T31", timesteps={"timeperiod": "%g s" % TEND,
                                "stepsize": "%g s" % (TEND / 10)})
    m.elset("Ring", "Staal")
    q = quadmesh(m, "Ring", 1, 4, rect(RA, RB, 0.0, 0.01), order=1)
    m.mat("Staal", '<geometric type="Plate" thickness="10 mm" />', STEEL,
          *(THERMAL + (PLASTIC,)))
    e = q["edges"]
    m.face_selection("Binnen", e["u0"])
    m.face_selection("Buiten", e["u1"])
    m.face_selection("Onder", e["v0"])
    m.face_selection("Boven", e["v1"])
    m.node_selection("Ondern", sorted(q["nodes"]["v0"]))
    _hold(m, "Onder", "y")
    _hold(m, "Boven", "y")
    _finish(m, "AXIS", (("Binnen", T0 + DT_P), ("Buiten", T0 + DT_P)))
    return m


# --- closed forms -------------------------------------------------------
def _k(mod):
    """Stress factor of a held end: 1 (C_PLAN) or 1 / (1 - nu) (D_PLAN)."""
    return 1.0 / (1.0 - NU) if mod == "D_PLAN" else 1.0


def _eyy(mod):
    """eps_yy / (alpha dT)."""
    return (1.0 + NU) / (1.0 - NU) if mod == "D_PLAN" else 1.0 + NU


def _checks_strip(mod):
    at = lambda var, pt: lambda r: r.at(var, pt, time=TEND)
    dt = T1 - T0
    src = "exact veld bij T lineair in y en u_x = 0 (%s)" % mod
    out = [
        Check("sigma_xx onderrand (heet)", at("stressxx", (L / 2, 0, 0)),
              ref=-E * ALPHA * dt * _k(mod), tol=2e-3, unit="Pa",
              source=src),
        Check("sigma_xx bovenrand (koud)", at("stressxx", (L / 2, W, 0)),
              ref=0.0, tol_abs=2e-3 * E * ALPHA * dt, unit="Pa",
              source=src),
        Check("sigma_yy onderrand", at("stressyy", (L / 2, 0, 0)),
              ref=0.0, tol_abs=2e-3 * E * ALPHA * dt, unit="Pa",
              source=src),
        Check("u_y bovenrand", at("disply", (L / 2, W, 0)),
              ref=_eyy(mod) * ALPHA * W * dt / 2.0, tol=2e-3, unit="m",
              source=src + ", T gemiddeld dT/2"),
        Check("som R_x links (dikte 1 mm)",
              lambda r: r.total("reactionforcex", "Links", time=TEND),
              ref=E * ALPHA * _k(mod) * T * W * dt / 2.0, tol=2e-3,
              unit="N", in_series=False,
              source="E alpha t int dT dy %s(factor t in de keten)" % (
                  "/ (1 - nu) " if mod == "D_PLAN" else "")),
        Check("T midden (thermisch deel, stationair)",
              at("temperature", (L / 2, W / 2, 0)), ref=(T0 + T1) / 2,
              tol_abs=1e-3 * dt, unit="K", source="lineair profiel")]
    if mod == "D_PLAN":
        out.insert(2, Check(
            "sigma_zz onderrand", at("stresszz", (L / 2, 0, 0)),
            ref=-E * ALPHA * dt / (1.0 - NU), tol=2e-3, unit="Pa",
            source=src))
    return out


_P = (E * ALPHA * DT_P - SY) / (E + H)
_SIG = SY + H * _P


def _checks_plastic(mod):
    at = lambda var, pt: lambda r: r.at(var, pt, time=TEND)
    src = ("eenassig, bilineair isotroop: sigma = sigma_y + H p, p = "
           "(E alpha dT - sigma_y) / (E + H)")
    lat = ALPHA * DT_P + NU * _SIG / E + 0.5 * _P
    if mod == "AXIS":
        mid, svar, area = (RB, 0.005, 0), "stressyy", math.pi * (
            RB ** 2 - RA ** 2)
        react = lambda r: r.total("reactionforcey", "Ondern", time=TEND)
        lat_chk = Check("u_r buitenwand", at("displx", (RB, 0.005, 0)),
                        ref=RB * lat, tol=5e-3, unit="m",
                        source="eps_theta = alpha dT + nu |sigma| / E + p / "
                               "2 (vrij radiaal)")
    else:
        mid, svar, area = (L / 2, 0, 0), "stressxx", W * T
        react = lambda r: r.total("reactionforcex", "Links", time=TEND)
        lat_chk = Check("u_y bovenrand", at("disply", (L / 2, W, 0)),
                        ref=W * lat, tol=5e-3, unit="m",
                        source="eps_yy = alpha dT + nu |sigma| / E + p / 2")
    return [
        Check("axiale spanning" if mod == "AXIS" else "sigma_xx",
              at(svar, mid), ref=-_SIG, tol=2e-3, unit="Pa", source=src),
        Check("equivalentplasticstrain", at("equivalentplasticstrain", mid),
              ref=_P, tol=5e-3, source=src),
        lat_chk,
        Check("som reactie (%s)" % ("360 graden" if mod == "AXIS" else
                                    "dikte 1 mm"),
              lambda r: abs(react(r)), ref=_SIG * area, tol=3e-3, unit="N",
              in_series=False, source="sigma A (A = pi (b^2 - a^2) of W t)")]


TESTS = []
for _id, _mod in (("PL-75", "C_PLAN"), ("PL-76", "D_PLAN")):
    TESTS.append(Case(
        _id, GROUP, "Thermomechanische keten in 2D, strook met lineaire "
        "temperatuur (T31 + Thermal stress + **ASTER-PLANE %s)" % _mod,
        "ther_3d", build_strip(_mod), _checks_strip(_mod),
        settings={"theta": 1.0},
        note="Strook 50 x 10 mm, quad8 10 x 4, onder 393 K, boven 293 K, "
             "einden vast in x; 10 stappen van 10 s (stationair)."))
TESTS.append(Case(
    "PL-78", GROUP, "Thermomechanische keten met plasticiteit, "
    "axisymmetrisch (T31 + Thermal stress + **ASTER-PLANE AXIS)", "ther_3d",
    build_ring, _checks_plastic("AXIS"), settings={"theta": 1.0},
    note="Ring 100 .. 110 mm, quad4 1 x 4, 200 K gelijkmatig verwarmd, "
         "einden axiaal vast; bilineair sigma_y = 250 MPa, H = 2,1 GPa."))
TESTS.append(Case(
    "PL-79", GROUP, "Thermomechanische keten met plasticiteit in vlakke "
    "spanning (T31 + Thermal stress + **ASTER-PLANE C_PLAN)", "ther_3d",
    build_strip("C_PLAN", plastic=True), _checks_plastic("C_PLAN"),
    settings={"theta": 1.0},
    note="Strook 50 x 10 mm, quad4 10 x 1, 200 K gelijkmatig verwarmd, "
         "einden vast in x; bilineair als PL-78."))


# PL-77: PL-75 with a pressure P77 on the top edge and the whole bottom
# edge held in y (edge loads in the plane chain, factor t): sigma_yy = -p,
# sigma_xx = nu sigma_yy - E alpha dT (u_x = 0), eps_yy gains
# -(1 - nu^2) p / E; the bottom reaction is p L t.
P77 = 50.0e6


def build_pl77():
    m = build_strip("C_PLAN")()
    m.items = [it for it in m.items if 'selection="Punt"' not in it]
    bottom = [i + 1 for i, p in enumerate(m.nodes) if abs(p[1]) < 1e-12]
    m.node_selection("Ondern", bottom)
    _hold(m, "Ondern", "y")
    m.add('<surfacepressure selection="Boven"><normal>%g Pa</normal>'
          '</surfacepressure>' % P77)
    return m


def _checks77():
    at = lambda var, pt: lambda r: r.at(var, pt, time=TEND)
    dt = T1 - T0
    src = "PL-75 + uniforme druk p op de bovenrand (vlakke spanning, u_x = 0)"
    return [
        Check("sigma_yy midden", at("stressyy", (L / 2, W / 2, 0)),
              ref=-P77, tol=2e-3, unit="Pa", source=src),
        Check("sigma_xx onderrand (heet)", at("stressxx", (L / 2, 0, 0)),
              ref=-E * ALPHA * dt - NU * P77, tol=2e-3, unit="Pa",
              source=src),
        Check("u_y bovenrand", at("disply", (L / 2, W, 0)),
              ref=(1 + NU) * ALPHA * W * dt / 2.0 -
              (1 - NU ** 2) * P77 * W / E, tol=2e-3, unit="m", source=src),
        Check("som R_y onder (dikte 1 mm)",
              lambda r: r.total("reactionforcey", "Ondern", time=TEND),
              ref=P77 * L * T, tol=2e-3, unit="N", in_series=False,
              source="evenwicht p L t (de druk per eenheid dikte, factor t)"),
        Check("som R_x links (dikte 1 mm)",
              lambda r: r.total("reactionforcex", "Links", time=TEND),
              ref=(E * ALPHA * dt / 2.0 + NU * P77) * W * T, tol=2e-3,
              unit="N", in_series=False,
              source="E alpha t int dT dy + nu p W t")]


TESTS.append(Case(
    "PL-77", GROUP, "Thermomechanische keten in 2D met druk op een rand (T31 "
    "+ Thermal stress + **ASTER-PLANE C_PLAN)", "ther_3d", build_pl77,
    _checks77(), settings={"theta": 1.0},
    note="Als PL-75 met 50 MPa druk op de bovenrand en de onderrand vast in "
         "y."))


# PL-80: D_PLAN, t = 2 mm, heat flow Q in W on the bottom edge (q = Q / (L t)
# in the thermal 'PLAN' part), T0 on the top edge; a force F in N on the top
# edge (sigma_yy = -F / (L t)); bottom held in y, both ends in x. Steady:
# dT(y) = q (W - y) / k, sigma_xx = sigma_zz = (nu sigma_yy - E alpha dT) /
# (1 - nu), eps_yy = (sigma_yy - 2 nu sigma_xx) / E + alpha dT.
T80 = 0.002
Q80 = 50.0                           # W, total over the edge
F80 = 2000.0                         # N, total over the edge
DT80 = Q80 * W / (K * L * T80)       # temperature rise of the bottom edge


def build_pl80():
    m = Model("T31", timesteps={"timeperiod": "%g s" % TEND,
                                "stepsize": "%g s" % (TEND / 10)})
    m.elset("Strook", "Staal")
    q = quadmesh(m, "Strook", 10, 4, rect(0.0, L, 0.0, W), order=2)
    m.mat("Staal", '<geometric type="Plate" thickness="%g mm" />'
          % (T80 * 1000), STEEL, *THERMAL)
    e = q["edges"]
    m.face_selection("Onder", e["v0"])
    m.face_selection("Boven", e["v1"])
    m.node_selection("Links", sorted(q["nodes"]["u0"]))
    m.node_selection("Rechts", sorted(q["nodes"]["u1"]))
    m.node_selection("Ondern", sorted(q["nodes"]["v0"]))
    _hold(m, "Links", "x")
    _hold(m, "Rechts", "x")
    _hold(m, "Ondern", "y")
    m.add('<heatflow selection="Onder"><value>%g W</value></heatflow>' % Q80)
    m.add('<force selection="Boven"><x>0 N</x><y>%g N</y><z>0 N</z>'
          '</force>' % -F80)
    _finish(m, "D_PLAN", (("Boven", T0),))
    return m


def _checks80():
    at = lambda var, pt: lambda r: r.at(var, pt, time=TEND)
    syy = -F80 / (L * T80)

    def sxx(dt):
        return (NU * syy - E * ALPHA * dt) / (1.0 - NU)
    # u_y(W) = int eps_yy dy, dT linear from DT80 to 0 (mean DT80 / 2)
    uy = W * ((syy - 2 * NU * sxx(DT80 / 2)) / E + ALPHA * DT80 / 2)
    src = ("D_PLAN, q = Q / (L t), sigma_yy = -F / (L t), eps_xx = "
           "eps_zz = 0")
    return [
        Check("T onderrand (warmtestroom in W)", at("temperature",
                                                    (L / 2, 0, 0)),
              ref=T0 + DT80, tol_abs=1e-3 * DT80, unit="K",
              source="T0 + Q W / (k L t): de stroom per lengte x dikte"),
        Check("warmteflux q_y", at("heatfluxy", (L / 2, W / 2, 0)),
              ref=Q80 / (L * T80), tol=2e-3, unit="W/m2",
              source="q = Q / (L t)"),
        Check("sigma_yy midden (kracht in N)", at("stressyy",
                                                  (L / 2, W / 2, 0)),
              ref=syy, tol=2e-3, unit="Pa", source="-F / (L t)"),
        Check("sigma_xx onderrand", at("stressxx", (L / 2, 0, 0)),
              ref=sxx(DT80), tol=2e-3, unit="Pa", source=src),
        Check("sigma_zz onderrand", at("stresszz", (L / 2, 0, 0)),
              ref=sxx(DT80), tol=2e-3, unit="Pa", source=src),
        Check("u_y bovenrand", at("disply", (L / 2, W, 0)), ref=uy,
              tol=2e-3, unit="m", source=src),
        Check("som R_y onder (dikte 2 mm)",
              lambda r: r.total("reactionforcey", "Ondern", time=TEND),
              ref=F80, tol=2e-3, unit="N", in_series=False,
              source="evenwicht: F (de kracht / t in Code-Aster, reactie "
                     "x t)"),
        Check("som R_x links (dikte 2 mm)",
              lambda r: r.total("reactionforcex", "Links", time=TEND),
              ref=-sxx(DT80 / 2) * W * T80, tol=2e-3, unit="N",
              in_series=False, source="-sigma_xx gemiddeld x W t")]


TESTS.append(Case(
    "PL-80", GROUP, "Thermomechanische keten in vlakke rek met warmtestroom "
    "en kracht (T31 + Thermal stress + **ASTER-PLANE D_PLAN)", "ther_3d",
    build_pl80, _checks80(), settings={"theta": 1.0},
    note="Strook 50 x 10 mm, dikte 2 mm, quad8 10 x 4: 50 W op de onderrand, "
         "293 K boven, 2000 N op de bovenrand; onderrand vast in y, einden in "
         "x."))
