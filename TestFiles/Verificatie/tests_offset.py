# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Element offset (Mecway Loads & Constraints > Element offset, bridge_offset):
schalen met EXCENTREMENT (DKT) of op eigen knopen met starre armen
(COQUE_3D), balken met starre armen. Referenties: balktheorie (Steiner,
parallelle-assenstelling) en Mecway 34 (eigen solver, headless met
TestFiles/Tools/mw_solve.py op hetzelfde model). Toelichting:
docs/Verificatie.md (LS-60 .. LS-63).
"""
from verif_lib import Case, Check, Model, linemesh, quadmesh, rect

GROUP = "Lineair statisch"
E, NU = 210e9, 0.3
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')


def _mean(r, var, sel):
    d = r.step()[var]
    nids = r.model.nodesel[sel]
    return sum(d[n] for n in nids) / float(len(nids))


def _total(r, var, sel):
    d = r.step()[var]
    return sum(d.get(n, 0.0) for n in r.model.nodesel[sel])


def _moment_x(r, sel):
    """Moment van de reacties om de X-as (momenten en krachten)."""
    d = r.step()
    out = 0.0
    for n in r.model.nodesel[sel]:
        x, y, z = r.model.nodes[n - 1]
        out += (d["reactionmomx"].get(n, 0.0) +
                y * d["reactionforcez"].get(n, 0.0) -
                z * d["reactionforcey"].get(n, 0.0))
    return out


def _offset_w(sel, w):
    return ('<offset selection="{0}"><u>0 m</u><v>0 m</v><w>{1!r} m</w>'
            '</offset>'.format(sel, w))


def _offset_xyz(sel, xyz):
    return ('<offset selection="{0}"><x>{1!r} m</x><y>{2!r} m</y>'
            '<z>{3!r} m</z></offset>'.format(sel, *xyz))


# ------------------------------------------------------------------
# LS-60 Plaatstrook met offset w, trekkracht in de knopen
# ------------------------------------------------------------------
# Ingeklemde strook L x B x T in het XY-vlak (normaal +Z), offset w = e
# (middenvlak op z = e). P (+X) op de knopen van de vrije rand: in de
# strook een normaalkracht P en een moment P e (arm van de knoop naar het
# middenvlak), dus een uniforme kromming P e/(E I): tip w = P e L^2/(2EI)
# naar +W, rotatie om Y -P e L/(EI). Buigspanning 6 P e/(B T^2) bovenop
# P/(B T): onder (-W, kant van de knopen) trek 77,5 MPa, boven 72,5 MPa
# druk. (a) quad4 -> DKT met EXCENTREMENT, (b) quad8 -> COQUE_3D op eigen
# knopen met starre armen.
L0, B0, T0, E0, P0 = 0.2, 0.02, 0.002, 0.01, 100.0
I0 = B0 * T0 ** 3 / 12.0
W0 = P0 * E0 * L0 ** 2 / (2 * E * I0)
R0 = P0 * E0 * L0 / (E * I0)
SB0 = P0 / (B0 * T0) + 6 * P0 * E0 / (B0 * T0 ** 2)
ST0 = 6 * P0 * E0 / (B0 * T0 ** 2) - P0 / (B0 * T0)


def build_ls60(order):
    def build():
        m = Model("S30")
        m.mat("Plaat2", '<geometric type="Plate" thickness="2 mm" />',
              STEEL)
        m.elset("Plaat", "Plaat2")
        q = quadmesh(m, "Plaat", 20, 4, rect(0, L0, 0, B0), order=order)
        m.face_selection("Inklemming", q["edges"]["u0"])
        m.node_selection("Inklemming_knopen", sorted(q["nodes"]["u0"]))
        m.node_selection("Tip", sorted(q["nodes"]["u1"]))
        mid = [m.node(L0 / 2, y, 0.0) for y in (0.0, B0 / 2, B0)]
        m.node_selection("Midden", mid)
        m.add('<fixed selection="Inklemming" />')
        m.add('<force selection="Tip"><x>%g N</x><y>0 N</y><z>0 N</z>'
              '</force>' % P0)
        m.element_selection("Verschoven", list(q["elems"].values()))
        m.add(_offset_w("Verschoven", E0))
        return m
    return build


def _ls60_checks(mw_w, mw_rot):
    return [
        Check("doorbuiging tip (+W)", lambda r: _mean(r, "displz", "Tip"),
              ref=W0, tol=0.02, unit="m",
              source="P e L^2/(2EI) (Euler; inklemming -0,7 %)"),
        Check("doorbuiging tip t.o.v. Mecway",
              lambda r: _mean(r, "displz", "Tip"), ref=mw_w, tol=0.005,
              unit="m", source="Mecway 34, zelfde model", in_series=False),
        Check("rotatie tip om Y", lambda r: -_mean(r, "roty", "Tip"),
              ref=mw_rot, tol=0.005, unit="rad",
              source="Mecway 34, zelfde model (analytisch P e L/(EI) = "
                     "%.4g)" % R0, in_series=False),
        Check("reactie X inklemming", lambda r: -_total(
            r, "reactionforcex", "Inklemming_knopen"), ref=P0, tol=1e-3,
              unit="N", source="evenwicht"),
        Check("reactiemoment Y inklemming", lambda r: _total(
            r, "reactionmomy", "Inklemming_knopen"), ref=0.0, tol_abs=1e-3,
              unit="N m", source="evenwicht (last op de knooplijn)"),
        Check("von Mises onderkant, x = L/2", lambda r: _mean(
            r, "vonmisesb", "Midden"), ref=SB0, tol=0.02, unit="Pa",
              source="P/(BT) + 6 P e/(B T^2)"),
        Check("von Mises bovenkant, x = L/2", lambda r: _mean(
            r, "vonmisesu1", "Midden"), ref=ST0, tol=0.02, unit="Pa",
              source="6 P e/(B T^2) - P/(BT)")]


TESTS = [
    Case("LS-60a", GROUP, "Plaatstrook met element offset, trek in de "
         "knopen (DKT, EXCENTREMENT)", "lin_static_3d", build_ls60(1),
         _ls60_checks(7.09010e-3, 7.12691e-2),
         note="Element offset w op quad4 -> AFFE_CARA_ELEM COQUE "
              "EXCENTREMENT + INER_ROTA."),
    Case("LS-60b", GROUP, "Plaatstrook met element offset, trek in de "
         "knopen (COQUE_3D, starre armen)", "lin_static_3d", build_ls60(2),
         _ls60_checks(7.09558e-3, 7.12627e-2),
         note="quad8 -> COQUE_3D kent geen excentrement (CALCULEL2_31): "
              "element op eigen knopen, LIAISON_DDL per arm."),
]


# ------------------------------------------------------------------
# LS-61 Sandwich: twee lagen op een knoopnet, offset +e en -e
# ------------------------------------------------------------------
# Twee DKT-lagen (T = 2 mm) delen de knopen; laag A ligt op +e, laag B op
# -e (EXCENTREMENT). De starre armen koppelen de lagen tot een doorsnede
# met I = 2 (B T^3/12 + B T e^2) (Steiner). Eindlast P (-Z): tip
# P L^3/(3 E I) (Euler; de kern zelf vervormt niet, dus geen afschuiving).
E1, P1 = 0.01, 100.0
I1 = 2 * (B0 * T0 ** 3 / 12.0 + B0 * T0 * E1 ** 2)
W1 = P1 * L0 ** 3 / (3 * E * I1)


def build_ls61():
    m = Model("S30")
    m.mat("Plaat2", '<geometric type="Plate" thickness="2 mm" />', STEEL)
    m.elset("Laag_A", "Plaat2")
    a = quadmesh(m, "Laag_A", 20, 4, rect(0, L0, 0, B0))
    m.elset("Laag_B", "Plaat2")
    b = quadmesh(m, "Laag_B", 20, 4, rect(0, L0, 0, B0))
    m.face_selection("Inklemming", a["edges"]["u0"])
    m.node_selection("Inklemming_knopen", sorted(a["nodes"]["u0"]))
    m.node_selection("Tip", sorted(a["nodes"]["u1"]))
    m.add('<fixed selection="Inklemming" />')
    m.add('<force selection="Tip"><x>0 N</x><y>0 N</y><z>-%g N</z>'
          '</force>' % P1)
    m.element_selection("Boven", list(a["elems"].values()))
    m.element_selection("Onder", list(b["elems"].values()))
    m.add(_offset_w("Boven", E1))
    m.add(_offset_w("Onder", -E1))
    return m


TESTS += [
    Case("LS-61", GROUP, "Sandwich: twee schaallagen met offset +e en -e "
         "(Steiner)", "lin_static_3d", build_ls61,
         [Check("doorbuiging tip", lambda r: -_mean(r, "displz", "Tip"),
                ref=W1, tol=0.03, unit="m",
                source="P L^3/(3EI), I = 2(BT^3/12 + BTe^2)"),
          Check("doorbuiging tip t.o.v. Mecway", lambda r: -_mean(
              r, "displz", "Tip"), ref=1.60897e-4, tol=0.03, unit="m",
                source="Mecway 34, zelfde model (+1,7 % t.o.v. Steiner)",
                in_series=False),
          Check("reactie Z inklemming", lambda r: _total(
              r, "reactionforcez", "Inklemming_knopen"), ref=P1, tol=1e-3,
                unit="N", source="evenwicht"),
          Check("reactiemoment Y inklemming", lambda r: -_total(
              r, "reactionmomy", "Inklemming_knopen"), ref=P1 * L0,
                tol=1e-3, unit="N m", source="evenwicht P L")],
         note="Zonder offset zou I = 2 B T^3/12 zijn (300x slapper)."),
]


# ------------------------------------------------------------------
# LS-62 T-balk: plaat (flens) + balk (lijf) met offset
# ------------------------------------------------------------------
# Flens: DKT-strook 1 m x 50 mm x 5 mm in het XY-vlak; lijf: balk RectBar
# 5 mm (V = Y) x 100 mm (W = Z) op de middellijn van de flens, offset
# z = -(h/2 + t/2) (globale coordinaten, zoals Mecway voor balken). De
# balk krijgt eigen knopen op de verschoven as met starre armen. Eindlast
# P (-Z) op de tip van de middellijn: T-doorsnede met zwaartepunt en I
# volgens Steiner. Doorbuiging P L^3/(3 E I).
L2, BF, TF, TW, HW, P2 = 1.0, 0.05, 0.005, 0.005, 0.1, 100.0
ZW = -(HW / 2 + TF / 2)
AF, AW = BF * TF, TW * HW
ZC = AW * ZW / (AF + AW)
I2 = (BF * TF ** 3 / 12 + AF * ZC ** 2 + TW * HW ** 3 / 12 +
      AW * (ZW - ZC) ** 2)
W2 = P2 * L2 ** 3 / (3 * E * I2)


def build_ls62():
    m = Model("S30")
    m.mat("Plaat5", '<geometric type="Plate" thickness="5 mm" />', STEEL)
    m.mat("Lijf", '<geometric type="RectBar" recta="5 mm" rectb="100 mm" />',
          STEEL)
    m.elset("Flens", "Plaat5")
    q = quadmesh(m, "Flens", 20, 2, rect(0, L2, -BF / 2, BF / 2))
    m.elset("Lijf", "Lijf")
    eids, nids = linemesh(m, "Lijf", 20, (0, 0, 0), (L2, 0, 0))
    m.face_selection("Inklemming_flens", q["edges"]["u0"])
    m.node_selection("Inklemming_knopen", sorted(q["nodes"]["u0"]))
    m.node_selection("Tip", [nids[-1]])
    m.add('<fixed selection="Inklemming_knopen" />')
    m.add('<force selection="Tip"><x>0 N</x><y>0 N</y><z>-%g N</z>'
          '</force>' % P2)
    m.element_selection("Lijf_offset", eids)
    m.add(_offset_xyz("Lijf_offset", (0.0, 0.0, ZW)))
    return m


TESTS += [
    Case("LS-62", GROUP, "T-balk: plaat als flens, balk als lijf met "
         "offset (starre armen)", "lin_static_3d", build_ls62,
         [Check("doorbuiging tip", lambda r: -r.node(
             "displz", r.model.nodesel["Tip"][0]), ref=W2, tol=0.03,
                unit="m", source="P L^3/(3EI), T-doorsnede (Steiner)"),
          Check("doorbuiging tip t.o.v. Mecway", lambda r: -r.node(
              "displz", r.model.nodesel["Tip"][0]), ref=1.84904e-4,
                tol=0.03, unit="m", source="Mecway 34, zelfde model "
                "(+2,1 % t.o.v. Steiner)",
                in_series=False),
          Check("reactie Z inklemming", lambda r: _total(
              r, "reactionforcez", "Inklemming_knopen"), ref=P2, tol=1e-3,
                unit="N", source="evenwicht"),
          Check("reactiemoment Y inklemming", lambda r: -_total(
              r, "reactionmomy", "Inklemming_knopen"), ref=P2 * L2,
                tol=1e-3, unit="N m", source="evenwicht P L")],
         note="Balk-offset in globale x/y/z (Mecway: 'Global coordinates "
              "(beams)'); zonder offset I = 4,2e-7 + 5,2e-10 m4."),
]


# ------------------------------------------------------------------
# LS-63 Samengestelde balk (als Mecway-voorbeeld CompositeBeam)
# ------------------------------------------------------------------
# Lijf: balk RectBar 0,2 m (V = Y) x 0,01 m langs X, E = 5,2 GPa; flens:
# quad8-schalen 0,2 m breed (XZ-vlak, normaal +Y), t = 0,01 m, E = 2,6
# GPa, offset w = 0,105 m (aan de rand van het lijf, T-doorsnede).
# Torsiemoment 6 N m om X aan de tip, inklemming bij x = 0. Mecway-manual
# par. 11.2: hoek = M L / (J (G_flens + G_lijf)) = 0,108 rad met J =
# B t^3/3 (Mecway 0,109). De doorsnede draait om het dwarskrachtcentrum
# (snijpunt van lijf en flens), dus de knooplijn beweegt opzij (Z) met
# ongeveer hoek x 0,105 m.
L3, BW3, H3, T3, W3, M3 = 3.6, 0.01, 0.2, 0.01, 0.105, 6.0
EW3, EF3 = 5.2e9, 2.6e9
J3 = H3 * T3 ** 3 / 3.0
PHI3 = M3 * L3 / (J3 * (EF3 / 2.6 + EW3 / 2.6))


def build_ls63():
    m = Model("S30")
    m.mat("Lijf", '<geometric type="RectBar" recta="0.2 m" rectb="0.01 m" '
          '/>', '<mechanical type="Isotropic" youngsmodulus="5200000000 Pa" '
          'poissonratio="0.3" />')
    m.mat("Flens", '<geometric type="Plate" thickness="0.01 m" />',
          '<mechanical type="Isotropic" youngsmodulus="2600000000 Pa" '
          'poissonratio="0.3" />')
    m.elset("Flens", "Flens")
    q = quadmesh(m, "Flens", 6, 2,
                 lambda u, v: (u * L3, 0.0, 0.1 - 0.2 * v), order=2)
    m.elset("Lijf", "Lijf")
    eids, nids = linemesh(m, "Lijf", 12, (0, 0, 0), (L3, 0, 0))
    m.face_selection("Inklemming_flens", q["edges"]["u0"])
    m.node_selection("Inklemming_knopen", sorted(q["nodes"]["u0"]))
    m.node_selection("Lijf_begin", [nids[0]])
    m.node_selection("Tip", [nids[-1]])
    # Inklemming op de rand van de flens (vlakken) en het begin van het
    # lijf, zoals in het voorbeeld
    m.add('<fixed selection="Inklemming_flens" />')
    m.add('<fixed selection="Lijf_begin" />')
    m.add('<moment selection="Tip"><x>%g N.m</x><y>0 N.m</y><z>0 N.m</z>'
          '</moment>' % M3)
    m.element_selection("Flens_offset", list(q["elems"].values()))
    m.add(_offset_w("Flens_offset", W3))
    return m


TESTS += [
    Case("LS-63", GROUP, "Samengestelde balk: lijf (balk) + flens (quad8 "
         "met offset), torsie (CompositeBeam)", "lin_static_3d", build_ls63,
         [Check("torsiehoek tip", lambda r: r.node(
             "rotx", r.model.nodesel["Tip"][0]), ref=PHI3, tol=0.03,
                unit="rad", source="Mecway-manual par. 11.2: M L/(J (G_f "
                "+ G_w))"),
          Check("torsiehoek tip t.o.v. Mecway", lambda r: r.node(
              "rotx", r.model.nodesel["Tip"][0]), ref=0.109132, tol=0.005,
                unit="rad", source="Mecway 34, zelfde model",
                in_series=False),
          Check("zijverplaatsing knooplijn tip t.o.v. Mecway", lambda r: -r.node(
              "displz", r.model.nodesel["Tip"][0]), ref=1.14047e-2,
                tol=0.005, unit="m", source="Mecway 34, zelfde model "
                "(draaiing om het dwarskrachtcentrum)", in_series=False),
          Check("reactiemoment om de X-as, inklemming",
                lambda r: -_moment_x(r, "Inklemming_knopen"), ref=M3,
                tol=1e-3, unit="N m", source="evenwicht")],
         note="Flens quad8 -> COQUE_3D op eigen knopen met starre armen "
              "naar de knopen van het lijf."),
]
