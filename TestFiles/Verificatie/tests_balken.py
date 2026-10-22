# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Balken: kwadratische balkelementen (line3, LS-50) en Mecway's *Flexible
joint on beam* (LS-51). Mecway S30 -> MECA_STATIQUE. Referenties: Euler-
balktheorie (Roark's Formulas for Stress and Strain, 7e druk, tabel 8.1) en
Mecway 34 (headless, TestFiles/Tools/mw_solve.py): line3 met CCX (Mecway's
eigen solver kent geen line3-balk, manual v33 par. 7.5), flexible joint met
de eigen solver (CCX kent hem niet, manual par. 9.12). Toelichting:
docs/Verificatie.md par. 4 (LS-50, LS-51).
"""
import math
from verif_lib import Case, Check, Model, linemesh

GROUP = "Lineair statisch"
E = 210e9
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
ROND = '<geometric type="CircularBar" roundod="20 mm" />'
# Mecway 34 headless (TestFiles/Tools/mw_solve.py), doorbuiging in m:
# - LS-50, eigen solver, hetzelfde model met 10 line2 op dezelfde knopen
#   (de eigen solver kent geen line3-balk): MW50x;
# - LS-50, CCX op het line3-model (B32R, als C3D20R uitgezet; gemiddelde
#   over de knopen van de doorsnede): MW50x_CCX;
# - LS-51, eigen solver op hetzelfde model: MW51x.
MW50A, MW50B, MW50C = 1.190476e-02, 4.464286e-03, 9.523810e-02
MW50A_CCX, MW50B_CCX, MW50C_CCX = 1.163280e-02, 4.329228e-03, 9.214860e-02
MW51A = MW51C = MW51F = 1.263134e-03
MW51B, MW51D = 3.157836e-04, 5.526213e-04
D = 0.020
I = math.pi * D ** 4 / 64.0
L = 1.0


def line3mesh(m, elset, n, p0, p1, attrs=""):
    """n line3-elementen van p0 naar p1 (Mecway-volgorde: eind, midden,
    eind; bridge_mesh._ASTER_TYPES). Returns (eids, nids) met nids langs
    de lijn (2n + 1)."""
    nids = [m.node(*[p0[d] + (p1[d] - p0[d]) * i / (2.0 * n)
                     for d in range(3)]) for i in range(2 * n + 1)]
    eids = [m.elem(elset, "line3", [nids[2 * i], nids[2 * i + 1],
                                    nids[2 * i + 2]], attrs)
            for i in range(n)]
    return eids, nids


# ------------------------------------------------------------------
# LS-50 Ingeklemde balk met line3-elementen
# ------------------------------------------------------------------
# 5 line3 (de bridge splitst elk in twee SEG2-cellen, POU_D_E), L = 1 m,
# rechthoekige staaf (RectBar) a x b: a langs V, b langs W (bridge_from_liml,
# profielen). (a, b) vierkant 20 x 20 mm: (a) eindlast P = 100 N in -Z;
# (b) gelijkmatige line pressure q = 100 N/m in -Z op alle elementen
# (elementselectie, FORCE_POUTRE). (c) 20 x 10 mm met orientatievector
# (0, 0, 1) per element (V = Z, a staat verticaal), eindlast P in -Y:
# buiging om V, I = a b^3/12 (zonder orientatie zou V = Y zijn en I vier
# keer zo groot).
# Euler: eindlast w(x) = P x^2 (3L - x) / (6EI), phi(L) = PL^2/(2EI);
# verdeeld w(L) = qL^4/(8EI), w(x) = q x^2 (6L^2 - 4Lx + x^2) / (24EI).
# Twee Euler-cellen per element zijn exact voor beide (de bridge zet een
# verdeelde last consistent op de knopen, met momenten).
# Mecway 34 rekent line3-balken alleen met CCX (B32R, als volume-elementen
# uitgezet; Timoshenko, afschuiving hier 0,03 %). Een ronde staaf kan daar
# niet: Mecway schrijft SECTION=PIPE met binnenstraal 0 en CCX stopt met
# "nonpositive jacobian" (CCX 2.23); daarom een rechthoek.
P50, Q50, N50 = 100.0, 100.0, 5
X50 = 0.1                      # middenknoop van het eerste element
A50, B50 = 0.020, 0.020
I50 = A50 * B50 ** 3 / 12.0
I50C = 0.020 * 0.010 ** 3 / 12.0


def build_ls50(load, solver=None):
    def build():
        m = Model("S30", solver=solver)
        m.elset("Balk", "Staaf")
        attrs = ('orientationvx="0" orientationvy="0" orientationvz="1"'
                 if load == "orient" else "")
        eids, nids = line3mesh(m, "Balk", N50, (0, 0, 0), (L, 0, 0), attrs)
        m.mat("Staaf", '<geometric type="RectBar" recta="20 mm" '
              'rectb="%g mm" />' % (10 if load == "orient" else 20), STEEL)
        m.node_selection("Inklemming", [nids[0]])
        m.node_selection("Tip", [nids[-1]])
        m.add('<fixed selection="Inklemming" />')
        if load == "tip":
            m.add('<force selection="Tip"><x>0 N</x><y>0 N</y>'
                  '<z>-%g N</z></force>' % P50)
        elif load == "orient":
            m.add('<force selection="Tip"><x>0 N</x><y>-%g N</y>'
                  '<z>0 N</z></force>' % P50)
        else:
            m.element_selection("Alle", eids)
            m.add('<linepressure selection="Alle"><x>0 N/m</x><y>0 N/m</y>'
                  '<z>-%g N/m</z></linepressure>' % Q50)
        return m
    return build


def _w_tip_load(x, inertia=I50):
    return P50 * x * x * (3 * L - x) / (6 * E * inertia)


def _w_uniform(x):
    return Q50 * x * x * (6 * L * L - 4 * L * x + x * x) / (24 * E * I50)


def _mw_line2(name, var, point, ref):
    """Vergelijking met Mecway 34 (eigen solver) op dezelfde balk met
    line2-elementen."""
    return Check("%s t.o.v. Mecway 34, line2" % name,
                 lambda r: -r.at(var, point), ref=ref, tol=1e-3, unit="m",
                 source="Mecway 34, eigen solver, 10 line2 (Euler)",
                 in_series=False)


def _mw_ccx(name, var, point, ref):
    """Vergelijking met Mecway 34 (CCX, B32R) op hetzelfde line3-model.
    Tolerantie 4 %: CCX zet de B32R uit in een C3D20R per element (een
    element over de doorsnede); dat is hier 2,3-3,2 % stijver dan de
    Euler-theorie, terwijl dezelfde balk met line2 in Mecway's eigen solver
    exact is. De afwijking is van CCX, niet van de bridge."""
    return Check("%s t.o.v. Mecway 34, CCX" % name,
                 lambda r: -r.at(var, point), ref=ref, tol=0.04, unit="m",
                 source="Mecway 34, solver CCX (line3 -> B32R)",
                 in_series=False)


TESTS = [
    Case("LS-50a", GROUP, "Ingeklemde balk, line3-elementen, eindlast",
         "lin_static_3d", build_ls50("tip"),
         [Check("doorbuiging tip", lambda r: -r.at("displz", (L, 0, 0)),
                ref=_w_tip_load(L), tol=1e-3, unit="m",
                source="PL^3/3EI (Roark tabel 8.1 geval 1a)"),
          Check("doorbuiging middenknoop x = 0,1 m",
                lambda r: -r.at("displz", (X50, 0, 0)),
                ref=_w_tip_load(X50), tol=1e-3, unit="m",
                source="P x^2 (3L - x)/6EI (Roark tabel 8.1 geval 1a)"),
          Check("rotatie tip", lambda r: abs(r.at("roty", (L, 0, 0))),
                ref=P50 * L ** 2 / (2 * E * I50), tol=1e-3, unit="rad",
                source="PL^2/2EI (Roark tabel 8.1 geval 1a)"),
          Check("reactiekracht Z", lambda r: r.total("reactionforcez",
                                                       "Inklemming"),
                ref=P50, tol=1e-6, unit="N", source="evenwicht"),
          _mw_line2("doorbuiging tip", "displz", (L, 0, 0), MW50A),
          _mw_ccx("doorbuiging tip", "displz", (L, 0, 0), MW50A_CCX)],
         note="line3-balk -> twee SEG2-cellen per element (C4)."),
    Case("LS-50b", GROUP, "Ingeklemde balk, line3-elementen, line pressure",
         "lin_static_3d", build_ls50("q"),
         [Check("doorbuiging tip", lambda r: -r.at("displz", (L, 0, 0)),
                ref=_w_uniform(L), tol=1e-3, unit="m",
                source="qL^4/8EI (Roark tabel 8.1 geval 2a)"),
          Check("doorbuiging middenknoop x = 0,1 m",
                lambda r: -r.at("displz", (X50, 0, 0)),
                ref=_w_uniform(X50), tol=1e-3, unit="m",
                source="q x^2 (6L^2 - 4Lx + x^2)/24EI (Roark tabel 8.1 "
                       "geval 2a)"),
          Check("reactiekracht Z", lambda r: r.total("reactionforcez",
                                                       "Inklemming"),
                ref=Q50 * L, tol=1e-6, unit="N", source="evenwicht"),
          _mw_line2("doorbuiging tip", "displz", (L, 0, 0), MW50B),
          _mw_ccx("doorbuiging tip", "displz", (L, 0, 0), MW50B_CCX)],
         note="Line pressure op een elementselectie met line3-balken."),
    Case("LS-50c", GROUP, "Line3-balk met orientatievector, eindlast",
         "lin_static_3d", build_ls50("orient"),
         [Check("doorbuiging tip", lambda r: -r.at("disply", (L, 0, 0)),
                ref=_w_tip_load(L, I50C), tol=1e-3, unit="m",
                source="PL^3/3EI met I = a b^3/12 (V = Z)"),
          _mw_line2("doorbuiging tip", "disply", (L, 0, 0), MW50C),
          _mw_ccx("doorbuiging tip", "disply", (L, 0, 0), MW50C_CCX)],
         note="Orientatie per helft van het gesplitste element."),
]


# ------------------------------------------------------------------
# LS-51 Flexible joint on beam (scharnier in een balk)
# ------------------------------------------------------------------
# Balk L = 1 m, 10 line2 (of 4 line3), Ø 20 mm, beide uiteinden
# ingeklemd, P = 100 N in het midden. Joint op het eindvlak van het
# element rechts van het midden (faceid 2 = eerste knoop).
# Lokale assen (Mecway, manual v33 par. 7.5): balk langs X -> U = X,
# V = Z x U = Y, W = Z; balk langs Z -> V = Y, W = U x V = -X.
# (a) langs X, last -Y, <rotw/>: scharnier om Z. Elke helft is een
#     ingeklemde balk L/2 met P/2 aan de tip: w = (P/2)(L/2)^3/(3EI) =
#     PL^3/(48EI); rotatie links van het scharnier (P/2)(L/2)^2/(2EI) =
#     PL^2/(16EI).
# (b) idem met <rotv/>: vrij om Y, maar buiging om Z -> geen effect,
#     w = PL^3/(192EI) (Roark tabel 8.1 geval 1d).
# (c) joint <rotw/> aan beide kanten van de middenknoop: zelfde als (a);
#     de middenknoop zelf heeft dan geen rotatiestijfheid (POI1 DIS_TR,
#     rotatie om Z op 0, zoals Mecway).
# (d) joint met alle drie de rotaties vrij op het eindvlak bij x = L:
#     inklemming wordt scharnier; ingeklemd-scharnierend met P in het
#     midden: w(L/2) = 7PL^3/(768EI) (Roark tabel 8.1 geval 1c).
# (e) als (a) met 4 line3-elementen (joint op een line3-uiteinde).
# (f) verticale balk (langs Z), last +X: buiging om Y = V; <rotv/> ->
#     scharnier, w = PL^3/(48EI).
P51 = 100.0
W48 = P51 * L ** 3 / (48 * E * I)


def build_ls51(free, faces="right", axis="x", shape="line2", end_joint=False):
    def build():
        m = Model("S30")
        m.elset("Balk", "Rond20")
        p1 = (L, 0, 0) if axis == "x" else (0, 0, L)
        if shape == "line3":
            eids, nids = line3mesh(m, "Balk", 4, (0, 0, 0), p1)
            mid_left, mid_right = eids[1], eids[2]
        else:
            eids, nids = linemesh(m, "Balk", 10, (0, 0, 0), p1)
            mid_left, mid_right = eids[4], eids[5]
        m.mat("Rond20", ROND, STEEL)
        m.node_selection("Inklemming", [nids[0], nids[-1]])
        m.node_selection("Midden", [nids[len(nids) // 2]])
        if end_joint:
            fj = [(eids[-1], 3)]
        elif faces == "both":
            fj = [(mid_left, 3), (mid_right, 2)]
        else:
            fj = [(mid_right, 2)]
        m.face_selection("Joint", fj)
        m.add('<fixed selection="Inklemming" />')
        if axis == "x":
            m.add('<force selection="Midden"><x>0 N</x><y>-%g N</y>'
                  '<z>0 N</z></force>' % P51)
        else:
            m.add('<force selection="Midden"><x>%g N</x><y>0 N</y>'
                  '<z>0 N</z></force>' % P51)
        m.add('<flexiblejoint selection="Joint">%s</flexiblejoint>'
              % "".join("<rot%s />" % a for a in free))
        return m
    return build


def _mw(name, var, point, ref, unit="m"):
    """Vergelijking met Mecway 34 (eigen solver) op hetzelfde model."""
    return Check("%s t.o.v. Mecway 34" % name,
                 lambda r: abs(r.at(var, point)), ref=ref, tol=1e-3,
                 unit=unit,
                 source="Mecway 34, eigen solver", in_series=False)


MID = (L / 2, 0, 0)
TESTS += [
    Case("LS-51a", GROUP, "Flexible joint: scharnier om W in het midden",
         "lin_static_3d", build_ls51("w"),
         [Check("doorbuiging midden", lambda r: -r.at("disply", MID),
                ref=W48, tol=1e-3, unit="m",
                source="twee ingeklemde balken L/2 met P/2: PL^3/48EI"),
          Check("rotatie links van het scharnier",
                lambda r: -r.at("rotz", MID),
                ref=P51 * L ** 2 / (16 * E * I), tol=1e-3, unit="rad",
                source="(P/2)(L/2)^2/2EI"),
          Check("reactiekracht Y", lambda r: r.total("reactionforcey",
                                                       "Inklemming"),
                ref=P51, tol=1e-6, unit="N", source="evenwicht"),
          _mw("doorbuiging midden", "disply", MID, MW51A)],
         note="<flexiblejoint><rotw/> -> eigen knoop + LIAISON_DDL (C6)."),
    Case("LS-51b", GROUP, "Flexible joint om V: geen effect bij buiging om W",
         "lin_static_3d", build_ls51("v"),
         [Check("doorbuiging midden", lambda r: -r.at("disply", MID),
                ref=W48 / 4.0, tol=1e-3, unit="m",
                source="PL^3/192EI (Roark tabel 8.1 geval 1d)"),
          _mw("doorbuiging midden", "disply", MID, MW51B)],
         note="Controleert de lokale assen: V = Y bij een balk langs X."),
    Case("LS-51c", GROUP, "Flexible joint aan beide kanten van de knoop",
         "lin_static_3d", build_ls51("w", faces="both"),
         [Check("doorbuiging midden", lambda r: -r.at("disply", MID),
                ref=W48, tol=1e-3, unit="m",
                source="twee ingeklemde balken L/2 met P/2: PL^3/48EI"),
          Check("rotatie middenknoop", lambda r: r.at("rotz", MID),
                ref=0.0, tol_abs=1e-12, unit="rad",
                source="Mecway 34: 0 (knoop zonder rotatiestijfheid)"),
          _mw("doorbuiging midden", "disply", MID, MW51C)],
         note="Knoop zonder ander element met rotaties: POI1 DIS_TR."),
    Case("LS-51d", GROUP, "Flexible joint als scharnieroplegging",
         "lin_static_3d", build_ls51("uvw", end_joint=True),
         [Check("doorbuiging midden", lambda r: -r.at("disply", MID),
                ref=7 * P51 * L ** 3 / (768 * E * I), tol=1e-3, unit="m",
                source="7PL^3/768EI (Roark tabel 8.1 geval 1c)"),
          Check("reactiemoment Z", lambda r: abs(r.total(
              "reactionmomz", "Inklemming")),
                ref=3 * P51 * L / 16.0, tol=1e-3, unit="N m",
                source="3PL/16 (Roark tabel 8.1 geval 1c)"),
          _mw("doorbuiging midden", "disply", MID, MW51D)],
         note="Joint met U, V en W vrij op het ingeklemde uiteinde."),
    Case("LS-51e", GROUP, "Flexible joint op een line3-balk",
         "lin_static_3d", build_ls51("w", shape="line3"),
         [Check("doorbuiging midden", lambda r: -r.at("disply", MID),
                ref=W48, tol=1e-3, unit="m",
                source="twee ingeklemde balken L/2 met P/2: PL^3/48EI")],
         note="C4 + C6: joint op het uiteinde van een gesplitst element. "
              "Mecway rekent dit niet (line3 alleen met CCX, joint niet "
              "met CCX)."),
    Case("LS-51f", GROUP, "Flexible joint om V op een verticale balk",
         "lin_static_3d", build_ls51("v", axis="z"),
         [Check("doorbuiging midden", lambda r: r.at("displx", (0, 0, L / 2)),
                ref=W48, tol=1e-3, unit="m",
                source="twee ingeklemde balken L/2 met P/2: PL^3/48EI"),
          _mw("doorbuiging midden", "displx", (0, 0, L / 2), MW51F)],
         note="Balk langs Z: Mecway V = Y; last in X buigt om V."),
]


# ------------------------------------------------------------------
# LS-52 Flexible joint en element offset samen (bridge_offset)
# ------------------------------------------------------------------
# Balk en last als LS-51a (scharnier om W op het eindvlak rechts van het
# midden), met een element offset z = e = 10 mm (globaal) op een helft.
# De offset staat loodrecht op het buigvlak (XY), dus geen koppeling met
# de buiging om Z; alleen een torsiemoment F e (verwaarloosbaar: extra
# doorbuiging e theta_x ~ 0,2 %).
# (a) offset op de rechterhelft, dus ook op het element met de joint: de
#     joint zit in de Mecway-knoop, voor de starre arm (zoals de fork van
#     MishalTPC, commit 773d59f): eigen knoop in de middenknoop, eigen arm
#     naar het element (KNOWN_BUGS 108d). Scharnier: w = PL^3/(48EI) zoals
#     LS-51a; Mecway 34 gaf hetzelfde (MW52).
# (b) offset op de linkerhelft: de verschoven balk en de balk met de
#     joint komen samen in de middenknoop N, die dan in geen enkele cel
#     meer zit (alleen in de arm en de joint): POI1 J<N> (DIS_TR). Het
#     scharnier werkt: w = PL^3/(48EI) zoals LS-51a.
# (c) als (a), maar de joint met U, V en W vrij (kogelscharnier). Waar de
#     joint zit blijkt uit de torsie: de rechterhelft (op z = e) krijgt
#     de kracht F2 via de arm vanaf de middenknoop, met de arm star aan de
#     balk: torsiemoment T = e F2 in de rechterhelft, de linkerhelft houdt
#     geen torsie (rotx in het midden 0). Zat de joint aan het eind van
#     de arm, dan was het omgekeerd. Verdeling van P: elke helft is een
#     ingeklemde balk L/2 met stijfheid k = 3EI/(L/2)^3 (POU_D_E); de
#     torsie van de rechterhelft (c = (L/2)/(GJ)) verschuift het
#     aangrijpingspunt met e theta_x: F1 = F2 (1 + a), a = e^2 c k.
# Mecway 34 (eigen solver, headless) geeft voor (a) en (b) dezelfde
# doorbuiging. (c) Mecway 34 (eigen solver, headless, 22 okt 2026, model
# modellen/LS-52c.liml): doorbuiging 1,264119 mm (gelijk aan W52C), maar
# de torsie zit in de linkerhelft: rotx in het midden -1,96895e-4 rad
# (= e F2 (L/2)/(GJ)), op x = 0,8 m 0. Mecway zet de joint dus aan het
# eind van de arm, de bridge in de Mecway-knoop (KNOWN_BUGS 117). De
# doorbuiging is door de symmetrie (beide helften dezelfde k en c) gelijk.
E52 = 0.01
MW52 = 1.263627e-03
MW52C, MW52C_ROT = 1.264119e-03, -1.968954e-04
# LS-52c: CircularBar (Code-Aster CERCLE): JX = pi D^4/32; elem_beam
# POU_D_E (default, Euler-Bernoulli): k = 3EI/(L/2)^3 without shear.
G52 = E / 2.6
J52 = math.pi * D ** 4 / 32.0
K52 = 3.0 * E * I / (L / 2) ** 3
C52 = (L / 2) / (G52 * J52)
A52C = E52 ** 2 * C52 * K52
F2_52C = P51 / (2.0 + A52C)
W52C = P51 * (1.0 + A52C) / (2.0 + A52C) / K52
ROT52C = E52 * F2_52C * (L - 0.8) / (G52 * J52)


def build_ls52(side, free="w"):
    def build():
        m = build_ls51(free)()
        eids = [e for e, _sh, _n, _a in m.elsets[0][2]]
        m.element_selection("Verschoven",
                            eids[5:] if side == "right" else eids[:5])
        m.add('<offset selection="Verschoven"><x>0 m</x><y>0 m</y>'
              '<z>%r m</z></offset>' % E52)
        return m
    return build


TESTS += [
    Case("LS-52a", GROUP, "Flexible joint op een balk met element offset",
         "lin_static_3d", build_ls52("right"),
         [Check("doorbuiging midden", lambda r: -r.at("disply", MID),
                ref=W48, tol=0.01, unit="m",
                source="twee ingeklemde balken L/2 met P/2: PL^3/48EI"),
          _mw("doorbuiging midden", "disply", MID, MW52),
          Check("reactiekracht Y", lambda r: r.total("reactionforcey",
                                                       "Inklemming"),
                ref=P51, tol=1e-6, unit="N", source="evenwicht")],
         note="Joint op het eindvlak van een verschoven element: in de "
              "Mecway-knoop, met een eigen starre arm (KNOWN_BUGS 108d "
              "opgelost)."),
    Case("LS-52b", GROUP, "Flexible joint naast een balk met element "
         "offset (zelfde knoop)", "lin_static_3d", build_ls52("left"),
         [Check("doorbuiging midden", lambda r: -r.at("disply", MID),
                ref=W48, tol=0.01, unit="m",
                source="twee ingeklemde balken L/2 met P/2: PL^3/48EI"),
          _mw("doorbuiging midden", "disply", MID, MW52),
          Check("reactiekracht Y", lambda r: r.total("reactionforcey",
                                                       "Inklemming"),
                ref=P51, tol=1e-6, unit="N", source="evenwicht")],
         note="Middenknoop alleen nog in de arm en de joint: POI1 DIS_TR "
              "(J<N>)."),
    Case("LS-52c", GROUP, "Flexible joint U, V en W vrij op een balk met "
         "element offset: torsie via de arm", "lin_static_3d",
         build_ls52("right", "uvw"),
         [Check("doorbuiging midden", lambda r: -r.at("disply", MID),
                ref=W52C, tol=1e-4, unit="m",
                source="F1/k, F1 = P (1 + a)/(2 + a), a = e^2 c k"),
          Check("rotx midden (linkerhelft zonder torsie)",
                lambda r: r.at("rotx", MID), ref=0.0, tol_abs=1e-9,
                unit="rad", source="joint in de Mecway-knoop: geen torsie "
                "naar links (fork MishalTPC, 773d59f)"),
          Check("|rotx| bij x = 0,8 (rechterhelft)",
                lambda r: abs(r.at("rotx", (0.8, 0, 0))), ref=ROT52C,
                tol=1e-3, unit="rad", source="T (L - x)/(GJ), T = e F2"),
          Check("reactiekracht Y", lambda r: r.total("reactionforcey",
                                                       "Inklemming"),
                ref=P51, tol=1e-6, unit="N", source="evenwicht"),
          _mw("doorbuiging midden", "disply", MID, MW52C),
          Check("rotx midden t.o.v. Mecway 34", lambda r: r.at("rotx", MID),
                ref=MW52C_ROT, tol=1e-3, unit="rad",
                source="Mecway 34, eigen solver: torsie links (joint aan "
                "het eind van de arm)", in_series=False,
                known="KNOWN_BUGS 117")],
         note="Kogelscharnier op het verschoven element: de arm draait "
              "met het element mee. Mecway 34: zelfde doorbuiging, torsie "
              "in de andere helft (KNOWN_BUGS 117)."),
]


# ------------------------------------------------------------------
# LS-53 Snedekrachten per element bij een flexible joint en line3
# ------------------------------------------------------------------
# LS-51a (line2) en LS-51e (line3) met beam_forces: Mecway's
# elementnodevariable bendingmomw/sheary per element. De cel van het
# element met de joint begint op een eigen knoop, een line3-balk bestaat
# uit twee SEG2-cellen (M<eid>, H<eid>); aster_results_export koppelt ze
# terug aan het Mecway-element. Elke helft is een ingeklemde balk L/2 met
# P/2 op het scharnier: M(x) = (P/2) |x - L/2|, V = P/2. Element rechts
# van het midden: M = 0 in het scharnier, (P/2) h aan het andere eind
# (h = 0,1 m line2; line3 0,25 m met middenknoop op h/2).
FIELDS53 = ["displacements", "stresses", "vonmises", "reactions",
            "beam_forces"]


def _elem_abs(var, eid, k):
    return lambda r: abs(r.elem(var)[eid][k])


TESTS += [
    Case("LS-53a", GROUP, "Snedekrachten per element naast een flexible "
         "joint (line2)", "lin_static_3d", build_ls51("w"),
         [Check("elementen met bendingmomw", lambda r: len(
             r.elem("bendingmomw")), ref=10, tol_abs=0, unit="",
                source="alle 10 balkelementen", in_series=False),
          Check("M in het scharnier (element 6, knoop 1)",
                _elem_abs("bendingmomw", 6, 0), ref=0.0, tol_abs=1e-6,
                unit="N m", source="scharnier: M = 0"),
          Check("M element 6, knoop 2 (x = 0,6 m)",
                _elem_abs("bendingmomw", 6, 1), ref=P51 / 2 * 0.1,
                tol=1e-3, unit="N m", source="(P/2) h"),
          Check("V element 6", _elem_abs("sheary", 6, 0), ref=P51 / 2,
                tol=1e-3, unit="N", source="P/2")],
         settings={"fields": FIELDS53},
         note="Cel van element 6 op de eigen knoop van de joint."),
    Case("LS-53b", GROUP, "Snedekrachten per element, line3-balk met "
         "flexible joint", "lin_static_3d", build_ls51("w", shape="line3"),
         [Check("elementen met bendingmomw", lambda r: len(
             r.elem("bendingmomw")), ref=4, tol_abs=0, unit="",
                source="alle 4 balkelementen", in_series=False),
          Check("M in het scharnier (element 3, knoop 1)",
                _elem_abs("bendingmomw", 3, 0), ref=0.0, tol_abs=1e-6,
                unit="N m", source="scharnier: M = 0"),
          Check("M element 3, middenknoop (x = 0,625 m)",
                _elem_abs("bendingmomw", 3, 1), ref=P51 / 2 * 0.125,
                tol=1e-3, unit="N m", source="(P/2) h/2"),
          Check("M element 3, knoop 3 (x = 0,75 m)",
                _elem_abs("bendingmomw", 3, 2), ref=P51 / 2 * 0.25,
                tol=1e-3, unit="N m", source="(P/2) h"),
          Check("V element 2, middenknoop", _elem_abs("sheary", 2, 1),
                ref=P51 / 2, tol=1e-3, unit="N", source="P/2")],
         settings={"fields": FIELDS53},
         note="Line3 als twee SEG2-cellen: waarden van beide helften op "
              "het Mecway-element."),
]


# ------------------------------------------------------------------
# LS-54 Staaf met een line3-truss-element (truss="true", GitHub issue #6)
# ------------------------------------------------------------------
# Een line3-element langs X, L = 1 m, ronde staaf D = 10 mm (A = pi D^2/4).
# Wortel ingeklemd, tip uy = uz = 0, trekkracht F = 1000 N langs X op de
# tip. De bridge splitst het element in twee SEG2-cellen (BARRE) en koppelt
# de middenknoop dwars op de koorde aan de eindknopen (LIAISON_DDL,
# bridge_mesh._line3_truss_links); zonder die koppeling is de middenknoop
# een mechanisme (ALGELINE3_81). Referentie u = F x / (E A).
F54, D54 = 1000.0, 0.010
A54 = math.pi * D54 ** 2 / 4.0


def build_ls54():
    m = Model("S30")
    m.elset("Staaf", "Staaf")
    _eids, nids = line3mesh(m, "Staaf", 1, (0, 0, 0), (L, 0, 0),
                            'truss="true"')
    m.mat("Staaf", '<geometric type="CircularBar" roundod="10 mm" />',
          STEEL)
    m.node_selection("Wortel", [nids[0]])
    m.node_selection("Tip", [nids[-1]])
    m.add('<fixed selection="Wortel" />')
    for d in ("<x>0</x><y>1</y><z>0</z>", "<x>0</x><y>0</y><z>1</z>"):
        m.add('<displacement selection="Tip"><value>0 mm</value>%s'
              '</displacement>' % d)
    m.add('<force selection="Tip"><x>%g N</x><y>0 N</y><z>0 N</z></force>'
          % F54)
    return m


TESTS += [
    Case("LS-54a", GROUP, "Staaf, een line3-truss-element, trekkracht",
         "lin_static_3d", build_ls54,
         [Check("verlenging tip", lambda r: r.at("displx", (L, 0, 0)),
                ref=F54 * L / (E * A54), tol=1e-6, unit="m",
                source="u = F L / (E A)"),
          Check("verplaatsing middenknoop", lambda r: r.at(
              "displx", (L / 2, 0, 0)), ref=F54 * L / (2 * E * A54),
                tol=1e-6, unit="m", source="u = F x / (E A), x = L/2"),
          Check("dwarsverplaatsing middenknoop", lambda r: max(
              abs(r.at("disply", (L / 2, 0, 0))),
              abs(r.at("displz", (L / 2, 0, 0)))), ref=0.0, tol_abs=1e-12,
                unit="m", source="midden volgt de eindknopen (0)",
                in_series=False)],
         note="Line3-truss als twee SEG2-cellen (BARRE) met de "
              "middenknoop dwars gekoppeld (GitHub issue #6)."),
]


# ------------------------------------------------------------------
# LS-54b/c Line3-kabel (Tension only, MODELISATION='CABLE')
# ------------------------------------------------------------------
# Als LS-54a, maar met materiaal TensionOnly (Mecway manual v33 par. 7.10):
# de bridge splitst ook een CABLE-line3 in twee SEG2-cellen met de
# middenknoop dwars gekoppeld (bridge_mesh._LINE3_SPLIT_MODS). CABLE kan
# alleen niet-lineair (RELATION='CABLE' met GROT_GDEP, U4.51.11).
# (b) een element, trekkracht F op de tip: u = F L / (E A).
# (c) twee elementen in serie, beide uiteinden vast (dwars vast op de
#     hoekknopen), F langs +X op de knoop ertussen: het linkerelement
#     krijgt trek, het rechter zou druk krijgen en draagt niets (Code-Aster:
#     drukstijfheid EC_SUR_E = 1e-4 E, bridge_to_aster._render_materials):
#     u = F L / (E A) / (1 + 1e-4), reactie links -F, rechts ~ 0.
# Tolerantie 2e-4: CABLE rekent met GROT_GDEP (Green-Lagrange-rek), dat
# wijkt O(eps) = 6e-5 af van de lineaire F L / (E A) (run: -7,5e-5).
# Mecway 34 headless (22 okt 2026) gaf voor TensionOnly geen oplossing,
# ook niet met line2 (eigen solver Static en Nonlinear static: lege
# <solution>; CCX: Mecway stopte met 0xC0000409); dezelfde line2-staaf
# als Isotropic truss wel (6,0630e-5 m). Alleen de handberekening dus.
TENSION = '<mechanical type="TensionOnly" youngsmodulus="210000 MPa" />'


def build_ls54_cable(two):
    def build():
        m = Model("L30", timesteps={"timeperiod": "1 s", "stepsize": "1 s"})
        m.elset("Kabel", "Kabel")
        _e, nids = line3mesh(m, "Kabel", 1, (0, 0, 0), (L, 0, 0))
        if two:
            _e, n2 = line3mesh(m, "Kabel", 1, (L, 0, 0), (2 * L, 0, 0))
            nids = nids + n2[1:]
        m.mat("Kabel", '<geometric type="CircularBar" roundod="10 mm" />',
              TENSION)
        ends = [nids[0]] + ([nids[4]] if two else [])
        m.node_selection("Wortel", ends)
        m.node_selection("Tip", [nids[2]])
        m.node_selection("Dwars", ends + [nids[2]])
        if two:
            m.node_selection("Links", [nids[0]])
            m.node_selection("Rechts", [nids[4]])
        m.add('<fixed selection="Wortel" />')
        for d in ("<x>0</x><y>1</y><z>0</z>", "<x>0</x><y>0</y><z>1</z>"):
            m.add('<displacement selection="Dwars"><value>0 mm</value>%s'
                  '</displacement>' % d)
        m.add('<force selection="Tip"><x>%g N</x><y>0 N</y><z>0 N</z>'
              '</force>' % F54)
        return m
    return build


U54 = F54 * L / (E * A54)
TESTS += [
    Case("LS-54b", GROUP, "Kabel (tension only), een line3-element, "
         "trekkracht", "nonlin_static_3d", build_ls54_cable(False),
         [Check("verlenging tip", lambda r: r.at("displx", (L, 0, 0)),
                ref=U54, tol=2e-4, unit="m", source="u = F L / (E A)"),
          Check("verplaatsing middenknoop", lambda r: r.at(
              "displx", (L / 2, 0, 0)), ref=U54 / 2, tol=2e-4, unit="m",
                source="u = F x / (E A), x = L/2"),
          Check("reactiekracht X", lambda r: r.total(
              "reactionforcex", "Wortel"), ref=-F54, tol=1e-6, unit="N",
                source="evenwicht")],
         note="Line3-kabel (CABLE) als twee SEG2-cellen met de middenknoop "
              "dwars gekoppeld (GitHub issue #6)."),
    Case("LS-54c", GROUP, "Twee line3-kabels in serie, een op druk: "
         "draagt niets", "nonlin_static_3d", build_ls54_cable(True),
         [Check("verplaatsing knoop ertussen", lambda r: r.at(
             "displx", (L, 0, 0)), ref=U54, tol=1e-3, unit="m",
                source="alleen de trekkabel: u = F L / (E A)"),
          Check("reactie links (trekkabel)", lambda r: r.total(
              "reactionforcex", "Links"), ref=-F54, tol=1e-3, unit="N",
                source="F gaat helemaal via de trekkabel"),
          Check("reactie rechts (drukkabel)", lambda r: r.total(
              "reactionforcex", "Rechts"), ref=0.0, tol_abs=1e-3 * F54,
                unit="N", source="drukkabel draagt niets (EC_SUR_E 1e-4 "
                "geeft 0,1 N)")],
         note="Rechterkabel op druk: Code-Aster houdt 1e-4 E als "
              "drukstijfheid (EC_SUR_E)."),
]
