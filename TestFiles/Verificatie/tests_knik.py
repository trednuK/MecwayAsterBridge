# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Lineaire knik (Mecway B30 -> MECA_STATIQUE + RIGI_GEOM + CALC_MODES
MODE_FLAMB, bridge-analyse buckling_3d). Referenties: Euler-knik
(Timoshenko & Gere, Theory of Elastic Stability, 2e druk, 1961, par. 2.1
en 2.3) en de vrij opgelegde plaat onder eenzijdige druk (idem par. 9.2:
sigma_cr = k pi^2 D / (b^2 t), k = (m b/a + a/(m b))^2). Toelichting:
doc_modaal.md.

De kniklastfactor (Results.modes, <mode bucklingfactor=..>) is het veelvoud
van de aangebrachte last waarbij de constructie knikt.
"""
import math
from verif_lib import Case, Check, Model, linemesh, hexmesh, quadmesh, box, \
    rect

GROUP = "Knik"
E, NU = 210e9, 0.3
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')


def _tol(tol_f, h, h_f, p):
    return max(tol_f, min(0.5, tol_f * (float(h) / h_f) ** p))


def _factor(k, ref, tol, source, name=None):
    return Check(name or "factor %d" % k, lambda r, k=k: r.mode(k), ref=ref,
                 tol=tol, unit="-", source=source)


# ------------------------------------------------------------------
# Kolom L = 1 m langs X, doorsnede a x b = 0,02 x 0,03 m (a in Y = recta).
# I_z = b a^3/12 (knik in Y), I_y = 2,25 I_z (knik in Z). Drukkracht
# P = 1000 N op het vrije/rolende einde.
# ------------------------------------------------------------------
L1, A1, B1, P1 = 1.0, 0.02, 0.03, 1000.0
IZ1 = B1 * A1 ** 3 / 12.0
IY1 = A1 * B1 ** 3 / 12.0
EULER = math.pi ** 2 * E * IZ1 / L1 ** 2       # scharnierend, zwakke as


def _column(m, nids, pinned):
    m.node_selection("Voet", [nids[0]])
    m.node_selection("Kop", [nids[-1]])
    if pinned:
        # Voet: X, Y, Z en torsie vast; kop: Y en Z vast (rolt in X).
        m.add('<displacement selection="Voet"><value>0 m</value><x>1</x>'
              '<y>0</y><z>0</z></displacement>')
        for sel in ("Voet", "Kop"):
            for d in ("<x>0</x><y>1</y><z>0</z>", "<x>0</x><y>0</y><z>1</z>"):
                m.add('<displacement selection="%s"><value>0 m</value>%s'
                      '</displacement>' % (sel, d))
        m.add('<noderotation selection="Voet"><value>0 rad</value><x>1</x>'
              '<y>0</y><z>0</z></noderotation>')
    else:
        m.add('<fixed selection="Voet" />')
    m.add('<force selection="Kop"><x>-%g N</x><y>0 N</y><z>0 N</z></force>'
          % P1)


def build_bu(pinned):
    def build():
        m = Model("B30", attrs={"maxmode": 3, "shift": 1})
        m.elset("Kolom", "Staal")
        _eids, nids = linemesh(m, "Kolom", 20, (0, 0, 0), (L1, 0, 0))
        m.mat("Staal", '<geometric type="RectBar" recta="%g m" rectb="%g m" '
              '/>' % (A1, B1), STEEL)
        _column(m, nids, pinned)
        return m
    return build


# Ingeklemd-vrij: Pcr = (2i-1)^2 pi^2 EI / (4 L^2); scharnierend:
# i^2 pi^2 EI / L^2 (Timoshenko & Gere par. 2.1, 2.3).
CF = sorted([((2 * i - 1) ** 2 * EULER / 4 / P1, "Y%d" % i) for i in (1, 2)] +
            [((2 * i - 1) ** 2 * EULER * IY1 / IZ1 / 4 / P1, "Z%d" % i)
             for i in (1, 2)])[:3]
PP = sorted([(i ** 2 * EULER / P1, "Y%d" % i) for i in (1, 2)] +
            [(i ** 2 * EULER * IY1 / IZ1 / P1, "Z%d" % i)
             for i in (1, 2)])[:3]
# Knikvorm ingeklemd-vrij phi = c (1 - cos(pi x / 2L)), genormeerd op
# phi^T K phi = EI int phi''^2 dx = 1 (zoals Mecway):
# c = 1 / sqrt(EI (pi/2L)^4 L/2).
TIP_CF = 1.0 / math.sqrt(E * IZ1 * (math.pi / (2 * L1)) ** 4 * L1 / 2)

TESTS = [
    Case("BU-01", GROUP, "Ingeklemde kolom, Euler-knik (20 balkelementen)",
         "buckling_3d", build_bu(False),
         [_factor(k + 1, f, 0.002, "Pcr/P, Pcr = (2i-1)^2 pi^2 EI/(4L^2), "
                  "knik %s (Timoshenko & Gere 2.1)" % plane)
          for k, (f, plane) in enumerate(CF)] +
         [Check("tip Y mode 1 (phi^T K phi = 1)",
                lambda r: abs(r.at("disply", (L1, 0, 0), time=1)),
                ref=TIP_CF, tol=0.005, unit="m",
                source="1/sqrt(EI (pi/2L)^4 L/2): normering zoals Mecway")],
         note="POU_D_E; drukkracht 1000 N."),
    Case("BU-02", GROUP, "Scharnierende kolom, Euler-knik (20 balkelementen)",
         "buckling_3d", build_bu(True),
         [_factor(k + 1, f, 0.002, "Pcr/P, Pcr = i^2 pi^2 EI/L^2, knik %s "
                  "(Timoshenko & Gere 2.3)" % plane)
          for k, (f, plane) in enumerate(PP)],
         note="POU_D_E; drukkracht 1000 N."),
]


def build_bu03(n):
    def build():
        m = Model("B30", attrs={"maxmode": 2, "shift": 1})
        m.elset("Kolom", "Staal")
        mesh = hexmesh(m, "Kolom", 25 * n, n, 3 * n // 2,
                       box(0, L1, -A1 / 2, A1 / 2, -B1 / 2, B1 / 2), order=2)
        m.mat("Staal", STEEL)
        m.face_selection("Voet", mesh["faces"]["u0"])
        m.face_selection("Kop", mesh["faces"]["u1"])
        m.add('<fixed selection="Voet" />')
        m.add('<traction selection="Kop"><x>-%g Pa</x><y>0 Pa</y>'
              '<z>0 Pa</z></traction>' % (P1 / (A1 * B1)))
        return m
    return build


def _bu03_cases():
    out = []
    # 3D t.o.v. Euler: afschuiving Pcr/(k G A) ~ 2e-4 en de inklemming met
    # dwarscontractie; tol_f 0,5%, orde 2 (hex20).
    ns = (2, 4)
    hf = A1 / ns[-1]
    for n in ns:
        h = A1 / n
        out.append(Case(
            "BU-03-h20-n%d" % n, GROUP,
            "Ingeklemde kolom, hex20 %dx%dx%d" % (25 * n, n, 3 * n // 2),
            "buckling_3d", build_bu03(n),
            [_factor(k + 1, f, _tol(0.005, h, hf, 2),
                     "Euler %s, Pcr = (2i-1)^2 pi^2 EI/(4L^2)" % plane)
             for k, (f, plane) in enumerate(CF[:2])],
            series="BU-03 hex20", h=h,
            note="Volume-elementen; drukkracht als traction op de kop."))
    return out


TESTS += _bu03_cases()


# ------------------------------------------------------------------
# BU-04 Vrij opgelegde vierkante plaat a = b = 0,4 m, t = 4 mm, druk in X:
# lijnlast q = 1 N/m op rand x = a (rand x = 0: X vast). Kniklastfactor =
# N_cr / q met N_cr = sigma_cr t = k pi^2 D / b^2; k = 4 (m = 1) en
# k = 6,25 (m = 2) (Timoshenko & Gere par. 9.2).
# ------------------------------------------------------------------
A4, T4, Q4 = 0.4, 0.004, 1.0
D4 = E * T4 ** 3 / (12 * (1 - NU ** 2))


def k_plate(mm):
    return (mm * A4 / A4 + A4 / (mm * A4)) ** 2


def build_bu04(n):
    def build():
        m = Model("B30", attrs={"maxmode": 2, "shift": 1})
        m.elset("Plaat", "Plaat4")
        mesh = quadmesh(m, "Plaat", n, n, rect(0, A4, 0, A4))
        m.mat("Plaat4", '<geometric type="Plate" thickness="%g m" />' % T4,
              STEEL)
        rand = set()
        for s in ("u0", "u1", "v0", "v1"):
            rand |= mesh["nodes"][s]
        m.node_selection("Rand", sorted(rand))
        m.node_selection("RandX0", sorted(mesh["nodes"]["u0"]))
        m.node_selection("Hoek", sorted(mesh["nodes"]["u0"] &
                                        mesh["nodes"]["v0"]))
        m.face_selection("RandX1", mesh["edges"]["u1"])
        # Vrij opgelegd: DZ = 0 op alle randen, rotatie om de normaal op de
        # rand nul (zoals LS-03); in het vlak alleen X = 0 op x = 0 en Y = 0
        # in een hoek, zodat de plaat vrij dwars kan uitzetten (zuivere
        # eenassige druk).
        m.add('<displacement selection="Rand"><value>0 m</value><x>0</x>'
              '<y>0</y><z>1</z></displacement>')
        m.add('<displacement selection="RandX0"><value>0 m</value><x>1</x>'
              '<y>0</y><z>0</z></displacement>')
        m.add('<displacement selection="Hoek"><value>0 m</value><x>0</x>'
              '<y>1</y><z>0</z></displacement>')
        m.node_selection("RandX", sorted(mesh["nodes"]["u0"] |
                                         mesh["nodes"]["u1"]))
        m.node_selection("RandY", sorted(mesh["nodes"]["v0"] |
                                         mesh["nodes"]["v1"]))
        m.add('<noderotation selection="RandX"><value>0 rad</value>'
              '<x>1</x><y>0</y><z>0</z></noderotation>')
        m.add('<noderotation selection="RandY"><value>0 rad</value>'
              '<x>0</x><y>1</y><z>0</z></noderotation>')
        m.add('<linepressure selection="RandX1"><x>-%g N/m</x><y>0 N/m</y>'
              '<z>0 N/m</z></linepressure>' % Q4)
        return m
    return build


def _bu04_cases():
    out = []
    ns = (8, 16, 32)
    hf = A4 / ns[-1]
    for n in ns:
        h = A4 / n
        out.append(Case(
            "BU-04-dkt-n%d" % n, GROUP,
            "Vrij opgelegde plaat, eenzijdige druk, DKT %dx%d" % (n, n),
            "buckling_3d", build_bu04(n),
            [_factor(mm, k_plate(mm) * math.pi ** 2 * D4 / A4 ** 2 / Q4,
                     _tol(0.005, h, hf, 2),
                     "k pi^2 D/b^2 / q, k = %.2f (m = %d; Timoshenko & "
                     "Gere 9.2)" % (k_plate(mm), mm))
             for mm in (1, 2)],
            series="BU-04 DKT", h=h,
            note="quad4 DKT; lijnlast 1 N/m op de rand x = a."))
    return out


TESTS += _bu04_cases()


# ------------------------------------------------------------------
# BU-40 Constante (dode) plus variabele last (#ASTER-CONSTANT, STAPPENPLAN
# S23; Aubry, Beginning with code_aster, 2019, par. 16.1-16.2): kolom van
# BU-01 met een constante drukkracht P_d = 0,5 Pcr,1 op de kop (eigen
# selectie KopD met dezelfde knoop) en de variabele 1000 N. Voor een
# axiaal belaste kolom is Kg evenredig met de normaalkracht, dus
# lambda_k = (Pcr,k - P_d) / P (Timoshenko & Gere 2.1). De foutmelding bij
# P_d > Pcr,1 staat in doc Verificatie (handmatig gecontroleerd).
# ------------------------------------------------------------------
PD40 = 0.5 * CF[0][0] * P1


def build_bu40(pd):
    def build():
        m = build_bu(False)()
        m.node_selection("KopD", m.nodesel["Kop"])
        m.add('<force selection="KopD"><x>-%r N</x><y>0 N</y><z>0 N</z>'
              '</force>' % pd)
        m.add("<ccxmodeldefinition>** ASTER-CONSTANT KopD"
              "</ccxmodeldefinition>")
        return m
    return build


TESTS.append(Case(
    "BU-40", GROUP, "Ingeklemde kolom, constante last 0,5 Pcr plus variabele "
    "last (#ASTER-CONSTANT)", "buckling_3d", build_bu40(PD40),
    [_factor(k + 1, (f * P1 - PD40) / P1, 0.002,
             "(Pcr,k - P_d)/P, P_d = 0,5 Pcr,1, knik %s (Timoshenko & Gere "
             "2.1; Aubry 2019 par. 16.2)" % plane)
     for k, (f, plane) in enumerate(CF)],
    note="POU_D_E; constante 0,5 Pcr,1 op KopD, variabele 1000 N op Kop."))
