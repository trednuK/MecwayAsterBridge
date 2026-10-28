# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Resultaatformules van Mecway (Solution > Formula, <formula> in de .liml;
STAPPENPLAN S33, GitHub-issue #8): de bridge rekent ze uit in de job
(bridge_formula, aster_results_export._formula_vars) en schrijft ze als
nodevariable onder de fieldscalar ("formula", "formula(2)", ...).
Referenties: de analytische oplossing (Incropera, Roark), omgerekend naar
de eenheden van de formule (exponents van Mecway). Mecway 34 zelf
(headless, mw_solve.py) gaf op FX-01 dezelfde waarden (zie
docs/Verificatie.md).
"""
from verif_lib import Case, Check, Model, hexmesh, box
import tests_thermisch as th
from tests_lineair_statisch import _steel

GROUP = "Resultaatformules"
BTU_H_FT2 = 1055.05585262 / 3600.0 / 0.3048 ** 2   # W/m2 per Btu/h/ft2


def _formula(name, fs, text, units):
    """<formula> zoals Mecway hem schrijft (units: (exponents, eenheid))."""
    return (u'<formula name="{0}" displayunit="" fieldscalar="{1}">\n'
            .format(name, fs) +
            u"".join(u'    <unit exponents="{0}">{1}</unit>\n'.format(*x)
                     for x in units) +
            u"    <formula>{0}</formula>\n  </formula>".format(text))


# FX-01: wand met warmteproductie (TH-01a), T in degF en de warmteflux in
# Btu/h/ft2, ook de formule van issue #8 (Btu/h/ft2 -> Btu/s/in2).
def build_fx01():
    m = th.build_th01(1, 8)()
    m.add(_formula("T_F", "formula", "T", [("+0+0+0+0+1", u"°F")]))
    m.add(_formula("qx_BTU", "formula(2)", "qf.x",
                   [("+0+1-3", u"Btu/h/ft²")]))
    m.add(_formula("q_issue8", "formula(3)", "qf.x/3600/(12^2)",
                   [("+0+1-3", u"Btu/h/ft²")]))
    m.add(_formula("q_x", "formula(4)", "sqrt(qf.x^2+qf.y^2)*x",
                   [("+0+1-3", u"W/m²"), ("+1", "mm")]))
    return m


def _q(x):
    """|flux| van TH-01a op x: q (L/2 - x), W/m2 (Incropera vgl. 3.39)."""
    return th.QG * (th.L1 / 2 - x)


_FX01_SRC = "TH-01a (Incropera vgl. 3.39/3.41) in de eenheid van de formule"

# FX-02: staaf op trek, traction P op het eindvlak, symmetrievlakken.
LX, BX, PX, EX = 1.0, 0.1, 1.0e6, 210.0e9


def build_fx02():
    m = Model("S30")
    m.elset("Staaf", "Staal")
    g = hexmesh(m, "Staaf", 4, 1, 1, box(0, LX, 0, BX, 0, BX), order=2)
    _steel(m)
    for name, side, ax in (("SymX", "u0", "x"), ("SymY", "v0", "y"),
                           ("SymZ", "w0", "z")):
        m.node_selection(name, sorted(g["nodes"][side]))
        d = dict((a, 1 if a == ax else 0) for a in "xyz")
        m.add('<displacement selection="{0}"><value>0 mm</value>'
              '<x>{x}</x><y>{y}</y><z>{z}</z></displacement>'.format(
                  name, **d))
    m.face_selection("Eindvlak", g["faces"]["u1"])
    m.add('<traction selection="Eindvlak"><x>%g Pa</x><y>0 Pa</y>'
          '<z>0 Pa</z></traction>' % PX)
    m.add(_formula("sxx", "formula", "s.xx", [("-1+1-2", "MPa")]))
    m.add(_formula("ux", "formula(2)", "u.x", [("+1", "mm")]))
    m.add(_formula("FRx", "formula(3)", "FR.x", [("+1+1-2", "kN")]))
    m.add(_formula("exx", "formula(4)", "e.xx*1e6", [("", "")]))
    m.add(_formula("xpos", "formula(5)", "x", [("+1", "mm")]))
    m.add(_formula("s1", "formula(6)", "s1", [("-1+1-2", "MPa")]))
    m.add(_formula("tr", "formula(7)", "tr", [("-1+1-2", "MPa")]))
    m.add(_formula("e1", "formula(8)", "e1*1e6", [("", "")]))
    return m


_FX02_FIELDS = ["displacements", "stresses", "vonmises", "reactions",
                "strain", "principal_stresses", "principal_strains"]
NUX = 0.3

# FX-03: half-oneindig lichaam (TH-02a), t in minuten per tijdstap.
def build_fx03():
    m = th.build_th02(100, 0.1, 40.0)()
    m.add(_formula("t_min", "formula", "t", [("+0+0+1", "min")]))
    m.add(_formula("dT_t", "formula(2)", "(T-300)/max(t,1)",
                   [("+0+0+0+0+1", "K"), ("+0+0+1", "s")]))
    return m


TESTS = [
    Case("FX-01", GROUP, "Formules op TH-01a: T in degF, flux in Btu/h/ft2 "
         "(ook issue #8), flux x positie",
         "ther_3d", build_fx01,
         [Check("T in degF (x = L/2)",
                lambda r: r.at("formula", (th.L1 / 2, 0, 0)),
                ref=(th.T0 + th._rise_gen(th.L1 / 2)) * 1.8 - 459.67,
                tol=1e-6, unit="degF", source=_FX01_SRC),
          Check("qf.x in Btu/h/ft2 (x = L/4)",
                lambda r: r.at("formula(2)", (th.L1 / 4, 0, 0)),
                ref=-_q(th.L1 / 4) / BTU_H_FT2, tol=1e-5, unit="Btu/h/ft2",
                source=_FX01_SRC),
          Check("qf.x/3600/(12^2) (x = L/4)",
                lambda r: r.at("formula(3)", (th.L1 / 4, 0, 0)),
                ref=-_q(th.L1 / 4) / BTU_H_FT2 / 3600.0 / 144.0, tol=1e-5,
                unit="Btu/s/in2", source=_FX01_SRC),
          Check("sqrt(qf.x^2+qf.y^2)*x (x = L/4)",
                lambda r: r.at("formula(4)", (th.L1 / 4, 0, 0)),
                ref=_q(th.L1 / 4) * th.L1 / 4 * 1000.0, tol=1e-5,
                unit="W/m2 mm", source=_FX01_SRC)],
         note="Mecway 34 headless op hetzelfde model: alle vier gelijk aan "
              "de bridge binnen 4e-14 relatief."),
    Case("FX-02", GROUP, "Formules op een staaf op trek: MPa, mm, kN, rek",
         "lin_static_3d", build_fx02,
         [Check("s.xx in MPa (x = L/2)",
                lambda r: r.at("formula", (LX / 2, BX / 2, BX / 2)),
                ref=PX / 1e6, tol=1e-6, unit="MPa",
                source="sigma = P (Roark tabel 2.1)"),
          Check("u.x in mm (x = L)",
                lambda r: r.at("formula(2)", (LX, 0, 0)),
                ref=PX * LX / EX * 1e3, tol=1e-6, unit="mm",
                source="u = P L / E"),
          Check("som FR.x in kN (SymX)",
                lambda r: r.total("formula(3)", "SymX"),
                ref=-PX * BX * BX / 1e3, tol=1e-6, unit="kN",
                source="evenwicht: reactie = -P A"),
          Check("e.xx * 1e6 (x = L/2)",
                lambda r: r.at("formula(4)", (LX / 2, BX / 2, BX / 2)),
                ref=PX / EX * 1e6, tol=1e-6, unit="microstrain",
                source="eps = P / E"),
          Check("x in mm (x = L)",
                lambda r: r.at("formula(5)", (LX, 0, 0)),
                ref=LX * 1e3, tol=1e-9, unit="mm",
                source="knooppositie"),
          Check("principal1 (x = L/2)",
                lambda r: r.at("principal1", (LX / 2, BX / 2, BX / 2)),
                ref=PX, tol=1e-6, unit="Pa",
                source="eenassig: sigma1 = P (S34)"),
          Check("principal3 (x = L/2)",
                lambda r: r.at("principal3", (LX / 2, BX / 2, BX / 2)),
                ref=0.0, tol_abs=1e-3, unit="Pa",
                source="eenassig: sigma3 = 0"),
          Check("tresca (x = L/2)",
                lambda r: r.at("tresca", (LX / 2, BX / 2, BX / 2)),
                ref=PX, tol=1e-6, unit="Pa",
                source="sigma1 - sigma3 = P"),
          Check("lprincipalstrain1 (x = L/2)",
                lambda r: r.at("lprincipalstrain1", (LX / 2, BX / 2, BX / 2)),
                ref=PX / EX, tol=1e-6, unit="-", source="eps1 = P / E"),
          Check("lprincipalstrain3 (x = L/2)",
                lambda r: r.at("lprincipalstrain3", (LX / 2, BX / 2, BX / 2)),
                ref=-NUX * PX / EX, tol=1e-6, unit="-",
                source="eps3 = -nu P / E"),
          Check("formule s1 in MPa", lambda r: r.at("formula(6)",
                                                    (LX / 2, BX / 2, BX / 2)),
                ref=PX / 1e6, tol=1e-6, unit="MPa", source="sigma1 = P"),
          Check("formule tr in MPa", lambda r: r.at("formula(7)",
                                                    (LX / 2, BX / 2, BX / 2)),
                ref=PX / 1e6, tol=1e-6, unit="MPa", source="Tresca = P"),
          Check("formule e1 * 1e6", lambda r: r.at("formula(8)",
                                                   (LX / 2, BX / 2, BX / 2)),
                ref=PX / EX * 1e6, tol=1e-6, unit="microstrain",
                source="eps1 = P / E")],
         settings={"fields": _FX02_FIELDS},
         note="Instelling fields met 'strain' (e.xx) en de hoofdwaarden "
              "(s1, tr, e1); zonder geeft de bridge een WARNING en laat "
              "de formule weg."),
    Case("FX-03", GROUP, "Formules in de tijd op TH-02a: t in min",
         "ther_3d", build_fx03,
         [Check("t in min (t = 10 s)",
                lambda r: r.at("formula", (0, 0, 0), time=10.0),
                ref=10.0 / 60.0, tol=1e-6, unit="min",
                source="tijd van de stap"),
          Check("t in min (t = 40 s)",
                lambda r: r.at("formula", (0, 0, 0), time=40.0),
                ref=40.0 / 60.0, tol=1e-6, unit="min",
                source="tijd van de stap"),
          Check("(T-300)/t op x = 0 (t = 40 s)",
                lambda r: r.at("formula(2)", (0, 0, 0), time=40.0),
                ref=(th.TS - 300.0) / 40.0, tol=1e-6, unit="K/s",
                source="T = Ts op het oppervlak")],
         settings={"theta": 0.57}),
]
