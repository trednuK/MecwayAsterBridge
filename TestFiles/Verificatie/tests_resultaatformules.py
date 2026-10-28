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
import tests_resultaatvelden as rv

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


# FX-04: hoofdwaarden van schalen (S34b), schaalstrook LS-31 (quad4, scheef
# in de ruimte) met P = 10 N: op x = L/2 boven sigma_uu = N/t + 6M/t^2 =
# 52,5 MPa, onder -22,5 MPa, midden 15 MPa, sigma_vv ~ 0 (eenassig). Mecway
# (headless, Mecway 34): principal<k>u1/m1/b1, tresca<s>1 en
# lprincipalstrain<k><s>1 = eigenwaarden van de globale 3 x 3-tensor per
# elementknoop (de normaalspanning 0 hoort erbij), knoop = gemiddelde.
# Eenassig: boven p1 = sigma, p2 = p3 ~ 0; onder p3 = sigma; rek boven
# eps1 = sigma/E, eps3 = -nu sigma/E (eps_ww = 0, vlakspanning).
P34B = 10.0


def build_fx04():
    m = rv.build_ls31(1)()
    m.items = [i for i in m.items if not i.lstrip().startswith("<force")]
    fv = [rv.F31 * rv.E1_31[k] - P34B * rv.N_31[k] for k in range(3)]
    m.add('<force selection="Eind"><x>%r N</x><y>%r N</y><z>%r N</z>'
          '</force>' % tuple(fv))
    return m


_S04 = rv.F31 / (rv.B31 * rv.T31)
_B04 = 6 * P34B * (rv.L31 - rv.X31) / rv.B31 / rv.T31 ** 2
SIG04 = {"u": _S04 + _B04, "m": _S04, "b": _S04 - _B04}
_SRC04 = ("plaattheorie op x = L/2 (LS-31 met P = 10 N): sigma_uu = N/t "
          "+- 6M/t^2, eenassig")
_FX04_FIELDS = ["displacements", "stresses", "vonmises", "reactions",
                "shell_stresses", "principal_stresses", "principal_strains"]


def _c04(r, var):
    return rv._mean(r, var, rv._center31(r))


def _rule04(r, lvl, node=False):
    """Grootste relatieve afwijking van principal<k><lvl>1 van Mecway's
    regel, toegepast op de schaalspanningen van de bridge zelf
    (stress<ij><lvl>1): per elementknoop de eigenwaarden van de globale
    tensor (aflopend); node=True: knoopwaarde = gemiddelde van de
    elementknoopwaarden."""
    import numpy as np
    comps = ("xx", "yy", "zz", "xy", "yz", "zx")
    ed = dict((c, r.elem("stress%s%s1" % (c, lvl))) for c in comps)
    pd = [r.elem("principal%d%s1" % (k, lvl)) for k in (1, 2, 3)]
    eids = sorted(pd[0])
    t = [np.concatenate([ed[c][e] for e in eids]) for c in comps]
    xx, yy, zz, xy, yz, zx = t
    ev = np.linalg.eigvalsh(np.stack(
        [np.stack([xx, xy, zx], -1), np.stack([xy, yy, yz], -1),
         np.stack([zx, yz, zz], -1)], -2))[:, ::-1]
    p = np.column_stack([np.concatenate([d[e] for e in eids]) for d in pd])
    scale = np.abs(p).max()
    if not node:
        return float(np.abs(ev - p).max() / scale)
    acc = {}
    nodes = dict((e[0], e[2]) for e in r.model.elsets[0][2])
    for e in eids:
        for n, v in zip(nodes[e], pd[0][e]):
            acc.setdefault(n, []).append(v)
    nd = r.step()["principal1%s1" % lvl]
    return max(abs(nd[n] - sum(v) / len(v)) for n, v in acc.items()) / scale


def _fx04_checks():
    out = []
    for name, lvl, ref in (("principal1u1", "u", SIG04["u"]),
                           ("principal1m1", "m", SIG04["m"]),
                           ("principal3b1", "b", SIG04["b"]),
                           ("trescau1", "u", SIG04["u"]),
                           ("trescab1", "b", -SIG04["b"])):
        out.append(Check(name, (lambda v: lambda r: _c04(r, v))(name),
                         ref=ref, tol=0.01, unit="Pa", source=_SRC04))
    out.append(Check("principal2u1", lambda r: _c04(r, "principal2u1"),
                     ref=0.0, tol_abs=0.01 * SIG04["u"], unit="Pa",
                     source="eenassig: sigma2 = 0"))
    for name, ref in (("lprincipalstrain1u1", SIG04["u"] / EX),
                      ("lprincipalstrain3u1", -NUX * SIG04["u"] / EX),
                      ("lprincipalstrain1b1", -NUX * SIG04["b"] / EX),
                      ("lprincipalstrain3b1", SIG04["b"] / EX)):
        out.append(Check(name, (lambda v: lambda r: _c04(r, v))(name),
                         ref=ref, tol=0.01, unit="-",
                         source="eps_uu = sigma/E, eps_vv = -nu sigma/E, "
                                "eps_ww = 0"))
    for lvl in "umb":
        out.append(Check(
            "regel Mecway %s: eigenwaarden per elementknoop" % lvl,
            (lambda l: lambda r: _rule04(r, l))(lvl), ref=0.0,
            tol_abs=1e-9, unit="rel.", in_series=False,
            source="Mecway 34 headless: principal = eigenwaarden van "
                   "stress<ij>" + lvl + "1 (binnen 3e-13)"))
    out.append(Check("regel Mecway u: knoop = gemiddelde", lambda r:
                     _rule04(r, "u", node=True), ref=0.0, tol_abs=1e-9,
                     unit="rel.", in_series=False,
                     source="Mecway 34 headless: knoopwaarde = gemiddelde "
                            "van de elementknoopwaarden"))
    return out


# FX-05: Green-Lagrange-hoofdrek en GLe1 (S34b) op de staaf van NL-31
# (hex20, 5% opgelegde rek, L30): E1 = (lambda^2 - 1)/2, E2 = E3 =
# ((lambda_t)^2 - 1)/2. Mecway 34 (CCX, headless) schrijft
# greenlagrangeprincipalstrain1..3 en herschrijft de formule e1 naar GLe1.
def build_fx05():
    m = rv.build_nl31()
    m.add(_formula("gl1", "formula", "GLe1", [("", "")]))
    m.add(_formula("e1", "formula(2)", "e1", [("", "")]))
    m.add(_formula("exx", "formula(3)", "e.xx", [("", "")]))
    return m


_GL05 = (rv.LAM31 ** 2 - 1) / 2


def _mid05():
    T = rv._nl()
    return (T.L1 / 2, T.A1 / 2, T.A1 / 2)


_FX05_FIELDS = ["displacements", "stresses", "vonmises", "reactions",
                "strain", "principal_strains"]


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
    Case("FX-04", GROUP, "Hoofdspanningen en -rekken van schalen boven/"
         "midden/onder (S34b): strook LS-31, buiging + trek",
         "lin_static_3d", build_fx04, _fx04_checks(),
         settings={"fields": _FX04_FIELDS},
         note="Zonder het veld strain: de bridge vraagt EPSI_ELNO van de "
              "schalen zelf aan voor de hoofdrekken. Mecway 34 headless op "
              "hetzelfde model (MITC4): op x = L/2 de dominante "
              "hoofdwaarden binnen 0,05% van de bridge (DKT); tresca en de "
              "waarden ~0 tot 1% van het maximum (dwarsschuif boven/onder "
              "bij MITC4, niet bij DKT)."),
    Case("FX-05", GROUP, "Green-Lagrange-hoofdrek en formules GLe1, e1, "
         "e.xx bij 5% rek (L30, S34b)",
         "nonlin_static_3d", build_fx05,
         [Check("greenlagrangeprincipalstrain1",
                lambda r: r.at("greenlagrangeprincipalstrain1", _mid05()),
                ref=_GL05, tol=1e-4, unit="-",
                source="E1 = (lambda^2 - 1)/2 (homogene rek)"),
          Check("formule GLe1", lambda r: r.at("formula", _mid05()),
                ref=_GL05, tol=1e-4, unit="-",
                source="E1 = (lambda^2 - 1)/2"),
          Check("formule e1 (Mecway: GLe1)",
                lambda r: r.at("formula(2)", _mid05()), ref=_GL05,
                tol=1e-4, unit="-",
                source="Mecway herschrijft e1 naar GLe1 (S34b)"),
          Check("formule e.xx (Mecway: GLe.xx)",
                lambda r: r.at("formula(3)", _mid05()), ref=_GL05,
                tol=1e-4, unit="-",
                source="Mecway herschrijft e.xx naar GLe.xx (S34b)")],
         settings={"fields": _FX05_FIELDS},
         note="Mecway 34 (CCX) op hetzelfde model: GLe1 = e1 = "
              "greenlagrangeprincipalstrain1 = 0,051248."),
]
