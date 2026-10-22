# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Modale analyse (Mecway V30 -> CALC_MODES, bridge-analyse modal_3d).
Referenties: Euler-Bernoulli-balk (Blevins, Formulas for Natural Frequency
and Mode Shape, 1979, tabel 8-1; Roark's Formulas for Stress and Strain,
7e druk, tabel 16.1) en de vrij opgelegde Kirchhoff-plaat (Leissa,
Vibration of Plates, NASA SP-160, 1969, par. 4.1). Toelichting:
doc_modaal.md.

Frequenties komen uit Results.modes (verif_lib, <mode frequency=..>); de
trillingsvormen zijn genormeerd op gegeneraliseerde massa 1 (MASS_GENE,
zoals Mecway), wat MO-01 controleert met de tipuitwijking.

Tolerantie in een mesh-convergentiereeks: zoals tests_lineair_statisch
(fijnste mesh tol_f, grovere meshes tol_f (h / h_f)^p, begrensd op 50%).
"""
import math
from verif_lib import Case, Check, Model, linemesh, hexmesh, quadmesh, box, \
    rect

GROUP = "Modaal"
E, NU, RHO = 210e9, 0.3, 7850.0
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
DENS = '<density type="Simple" density="7850 kg/m³" />'

# Euler-Bernoulli, ingeklemd-vrij: lambda_i L (Blevins tabel 8-1)
LAMBDA_CF = (1.87510407, 4.69409113, 7.85475744)


def _tol(tol_f, h, h_f, p):
    return max(tol_f, min(0.5, tol_f * (float(h) / h_f) ** p))


# ------------------------------------------------------------------
# MO-01 / MO-02 Ingeklemde balk: L = 1 m, doorsnede a x b = 0,02 x 0,03 m
# (a in Y = Mecway recta, b in Z = rectb). Buiging in Y heeft I_z = b a^3/12,
# in Z I_y = a b^3/12 = 2,25 I_z, dus f_Z = 1,5 f_Y. Torsie (~680 Hz) en
# langs (~1290 Hz) liggen boven de eerste 6 buigmodes.
# ------------------------------------------------------------------
L1, A1, B1 = 1.0, 0.02, 0.03
AREA1 = A1 * B1
IZ1 = B1 * A1 ** 3 / 12.0          # buiging in Y
IY1 = A1 * B1 ** 3 / 12.0          # buiging in Z
MASS1 = RHO * AREA1 * L1


def f_cf(lam, inertia):
    """f = lambda^2 / (2 pi L^2) sqrt(E I / (rho A))."""
    return lam ** 2 / (2 * math.pi * L1 ** 2) * math.sqrt(
        E * inertia / (RHO * AREA1))


# de 6 laagste buigmodes: (frequentie, vlak)
MODES1 = sorted([(f_cf(l, IZ1), "Y%d" % (i + 1)) for i, l in
                 enumerate(LAMBDA_CF)] +
                [(f_cf(l, IY1), "Z%d" % (i + 1)) for i, l in
                 enumerate(LAMBDA_CF)])


def build_mo01():
    m = Model("V30", attrs={"maxmode": 6})
    m.elset("Balk", "Staal")
    _eids, nids = linemesh(m, "Balk", 20, (0, 0, 0), (L1, 0, 0))
    m.mat("Staal", '<geometric type="RectBar" recta="%g m" rectb="%g m" />'
          % (A1, B1), STEEL, DENS)
    m.node_selection("Inklemming", [nids[0]])
    m.add('<fixed selection="Inklemming" />')
    return m


def _mode_check(k, ref, tol, source, name=None):
    return Check(name or "f%d" % k, lambda r, k=k: r.mode(k), ref=ref,
                 tol=tol, unit="Hz", source=source)


def _tip_check():
    # Massa-genormeerde eerste vorm: phi(L) = 2 / sqrt(m) voor de
    # uniforme ingeklemde balk (genormeerd met int phi^2 dx = L heeft
    # phi(L) = 2, Blevins tabel 8-1).
    return Check("tip Y mode 1 (MASS_GENE)",
                 lambda r: abs(r.at("disply", (L1, 0, 0), time=1)),
                 ref=2.0 / math.sqrt(MASS1), tol=0.002, unit="m",
                 source="2/sqrt(rho A L): normering MASS_GENE zoals Mecway")


# ------------------------------------------------------------------
# Effectieve massa (S10b). Euler-Bernoulli ingeklemd-vrij, genormeerde
# vorm W_i (int_0^L W^2 dx = L; Blevins tabel 8-1): de fractie van mode i
# voor een starre beweging R(x) is (int W_i R dx)^2 / (L int R^2 dx).
# Translatie R = 1: 0,6131 / 0,1883 / 0,0647; rotatie om de inklemming
# R = x: 0,97069 / 0,02472 / 0,00315 (beide hieronder numeriek uit W_i,
# eigen berekening; Mecway 33 headless op MO-01: 0,97071 rotatie). Som van
# de rotatiefracties over 3 modes: 0,99856.
# ------------------------------------------------------------------
def _cf_shape(lam):
    s = (math.cosh(lam) + math.cos(lam)) / (math.sinh(lam) + math.sin(lam))
    return lambda u: (math.cosh(lam * u) - math.cos(lam * u) -
                      s * (math.sinh(lam * u) - math.sin(lam * u)))


def _cf_fraction(lam, rigid, n=4000):
    """(int_0^1 W R du)^2 / int_0^1 R^2 du, middelpuntregel (u = x/L)."""
    w = _cf_shape(lam)
    us = [(i + 0.5) / n for i in range(n)]
    num = sum(w(u) * rigid(u) for u in us) / n
    den = sum(rigid(u) ** 2 for u in us) / n
    return num ** 2 / den


FRAC_T = [_cf_fraction(l, lambda u: 1.0) for l in LAMBDA_CF]
FRAC_R = [_cf_fraction(l, lambda u: u) for l in LAMBDA_CF]


def _effmass_check(name, k, key, ref, tol, source, known=None):
    return Check(name, lambda r, k=k, key=key: r.mode_param(k, key),
                 ref=ref, tol=tol, source=source, known=known)


def _effmass_sum_check(name, key, jkey, ref, tol, source, modes=None):
    """Som over de modes van fractie x noemer (kg.m2) tegen ref."""
    return Check(name, lambda r: r.mode_sum(key, modes) * r.mass_param(jkey),
                 ref=ref, tol=tol, unit="kg.m2", source=source)


# MO-01: modes Y1, Z1, Y2, Z2, Y3, Z3 (MODES1). Buiging in Y (Y1) is rotatie
# om Z door de inklemming (R = (-y, x, 0)), buiging in Z om Y.
_MO01_EFF = [
    _effmass_check("eff. massa Y mode 1 (Code-Aster)", 1, "MASS_EFFE_UN_DY",
                   FRAC_T[0], 0.002, "Euler-Bernoulli: (int W1 dx)^2/L^2 = "
                   "0,6131 (vorm uit Blevins 8-1)"),
    _effmass_check("eff. massa RZ mode 1", 1, "MASS_EFFE_UN_DRZ", FRAC_R[0],
                   0.002, "Euler-Bernoulli: 3 (int W1 x dx)^2/L^4 = 0,97069 "
                   "(rotatie om de inklemming = oorsprong)"),
    _effmass_check("eff. massa RY mode 2", 2, "MASS_EFFE_UN_DRY", FRAC_R[0],
                   0.002, "idem, buiging in Z"),
    _effmass_sum_check("som eff. massa RZ (6 modes)", "MASS_EFFE_UN_DRZ", "JZ",
                       MASS1 * L1 ** 2 / 3.0, 0.01,
                       "I_z om de inklemming = m L^2/3 (balkas; som van 3 "
                       "Y-modes analytisch 0,99856 I_z)"),
]


# S12: dezelfde effectieve massa als Mecway-variabelen in het
# resultaatbestand (<globalvariable> per <mode>, zoals Mecway's eigen
# modale oplossing): gelijk aan de waarden in de .mess (BRIDGE_MODE, 6
# cijfers) en aan de analytische waarden.
def _global_check(name, k, var, ref, tol, unit, source):
    return Check(name, lambda r, k=k, var=var: r.mode_global(k, var),
                 ref=ref, tol=tol, unit=unit, source=source)


def _global_vs_mess(name, k, var, key):
    """Mecway-variabele / .mess-waarde - 1 (de .mess heeft 6 cijfers)."""
    return Check(name, lambda r, k=k, var=var, key=key:
                 r.mode_global(k, var) / r.mode_param(k, key) - 1.0,
                 ref=0.0, tol_abs=2e-6, in_series=False,
                 source="zelfde waarde als BRIDGE_MODE in de .mess")


_MO01_EFF += [
    _global_check("Mecway: modaleffectivemassfractionty mode 1", 1,
                  "modaleffectivemassfractionty", FRAC_T[0], 0.002, "",
                  "Euler-Bernoulli 0,6131 (als MASS_EFFE_UN_DY)"),
    _global_vs_mess("Mecway = .mess: fractie ty mode 1", 1,
                    "modaleffectivemassfractionty", "MASS_EFFE_UN_DY"),
    _global_vs_mess("Mecway = .mess: fractie rz mode 1", 1,
                    "modaleffectivemassfractionrz", "MASS_EFFE_UN_DRZ"),
    _global_check("Mecway: modaleffectivemassty mode 1", 1,
                  "modaleffectivemassty", FRAC_T[0] * MASS1, 0.002, "kg",
                  "0,6131 m (m = rho A L = 4,71 kg)"),
    _global_check("Mecway: modaleffectivemassrz mode 1", 1,
                  "modaleffectivemassrz", FRAC_R[0] * MASS1 * L1 ** 2 / 3.0,
                  0.003, "kg.m2", "0,97069 m L^2/3 (rotatie om de "
                  "inklemming; doorsnede-traagheid ~1e-4 extra)"),
    _global_check("Mecway: cumulatief rz t/m mode 6", 6,
                  "cumulativeeffectivemassfractionrz", sum(FRAC_R), 0.003, "",
                  "som van de 3 Y-modes 0,99856 (Euler-Bernoulli)"),
    Check("Mecway = .mess: cumulatief rz t/m mode 6",
          lambda r: r.mode_global(6, "cumulativeeffectivemassfractionrz") /
          r.mode_sum("MASS_EFFE_UN_DRZ") - 1.0, ref=0.0, tol_abs=1e-5,
          in_series=False, source="som van MASS_EFFE_UN_DRZ in de .mess"),
]


TESTS = [
    Case("MO-01", GROUP, "Ingeklemde balk, 6 modes (20 balkelementen)",
         "modal_3d", build_mo01,
         [_mode_check(k + 1, f, 0.002,
                      "Euler-Bernoulli %s, lambda L = %.4f (Blevins 8-1)"
                      % (plane, LAMBDA_CF[int(plane[1]) - 1]))
          for k, (f, plane) in enumerate(MODES1)] + [_tip_check()] +
         _MO01_EFF,
         note="POU_D_E met consistente massa; 20 elementen."),
]


def build_mo02(n):
    def build():
        m = Model("V30", attrs={"maxmode": 3})
        m.elset("Balk", "Staal")
        mesh = hexmesh(m, "Balk", 25 * n, n, 3 * n // 2,
                       box(0, L1, -A1 / 2, A1 / 2, -B1 / 2, B1 / 2), order=2)
        m.mat("Staal", STEEL, DENS)
        m.face_selection("Inklemming", mesh["faces"]["u0"])
        m.add('<fixed selection="Inklemming" />')
        return m
    return build


def _mo02_cases():
    out = []
    # Modelfout 3D t.o.v. Euler-Bernoulli bij L/h = 33..50: afschuiving en
    # rotatietraagheid (Timoshenko) ~ -0,1% voor mode 1; inklemming met
    # dwarscontractie ~ +0,1%: tol_f 0,5%. Orde p = 2 (hex20, frequentie).
    ns = (2, 4)
    hf = A1 / ns[-1]
    for n in ns:
        h = A1 / n
        out.append(Case(
            "MO-02-h20-n%d" % n, GROUP,
            "Ingeklemde balk, hex20 %dx%dx%d" % (25 * n, n, 3 * n // 2),
            "modal_3d", build_mo02(n),
            [_mode_check(k + 1, f, _tol(0.005, h, hf, 2),
                         "Euler-Bernoulli %s (Blevins 8-1)" % plane)
             for k, (f, plane) in enumerate(MODES1[:3])],
            series="MO-02 hex20", h=h,
            note="Volume-elementen, mesh-convergentie."))
    return out


TESTS += _mo02_cases()


# ------------------------------------------------------------------
# MO-03 Vrij opgelegde rechthoekige plaat a x b = 0,6 x 0,4 m, t = 4 mm
# Kirchhoff (Leissa par. 4.1): f_mn = pi/2 (m^2/a^2 + n^2/b^2) sqrt(D/(rho t))
# ------------------------------------------------------------------
A3, B3, T3 = 0.6, 0.4, 0.004
D3 = E * T3 ** 3 / (12 * (1 - NU ** 2))


def f_ss(mm, nn):
    return math.pi / 2 * (mm ** 2 / A3 ** 2 + nn ** 2 / B3 ** 2) * math.sqrt(
        D3 / (RHO * T3))


MODES3 = sorted((f_ss(mm, nn), "(%d,%d)" % (mm, nn))
                for mm in range(1, 5) for nn in range(1, 4))[:4]


def build_mo03(k):
    def build():
        m = Model("V30", attrs={"maxmode": 4})
        m.elset("Plaat", "Plaat4")
        mesh = quadmesh(m, "Plaat", 3 * k, 2 * k, rect(0, A3, 0, B3))
        m.mat("Plaat4", '<geometric type="Plate" thickness="%g m" />' % T3,
              STEEL, DENS)
        rand = set()
        for s in ("u0", "u1", "v0", "v1"):
            rand |= mesh["nodes"][s]
        m.node_selection("Rand", sorted(rand))
        # vrij opgelegd zoals LS-03: randen DX = DY = DZ = 0 en de
        # rotatie om de normaal op de rand nul ("hard"); de plaatbuiging
        # (Kirchhoff) hangt alleen af van DZ = 0.
        for d in ("<x>1</x><y>0</y><z>0</z>", "<x>0</x><y>1</y><z>0</z>",
                  "<x>0</x><y>0</y><z>1</z>"):
            m.add('<displacement selection="Rand"><value>0 m</value>%s'
                  '</displacement>' % d)
        m.node_selection("RandX", sorted(mesh["nodes"]["u0"] |
                                         mesh["nodes"]["u1"]))
        m.node_selection("RandY", sorted(mesh["nodes"]["v0"] |
                                         mesh["nodes"]["v1"]))
        m.add('<noderotation selection="RandX"><value>0 rad</value>'
              '<x>1</x><y>0</y><z>0</z></noderotation>')
        m.add('<noderotation selection="RandY"><value>0 rad</value>'
              '<x>0</x><y>1</y><z>0</z></noderotation>')
        return m
    return build


def _mo03_cases():
    out = []
    # DKT: frequentie O(h^2); rotatietraagheid van de schaal ~ (t/b)^2
    # ~ 1e-4. tol_f 0,5% (discretisatie van mode 4 met 3 halve golven bij
    # 48 x 32 elementen).
    ks = (4, 8, 16)
    hf = B3 / (2 * ks[-1])
    for k in ks:
        h = B3 / (2 * k)
        out.append(Case(
            "MO-03-dkt-k%d" % k, GROUP,
            "Vrij opgelegde plaat, DKT %dx%d" % (3 * k, 2 * k),
            "modal_3d", build_mo03(k),
            [_mode_check(i + 1, f, _tol(0.005, h, hf, 2),
                         "Kirchhoff f%s = pi/2 (m^2/a^2+n^2/b^2) "
                         "sqrt(D/rho t) (Leissa par. 4.1)" % mn)
             for i, (f, mn) in enumerate(MODES3)],
            series="MO-03 DKT", h=h,
            note="quad4 DKT, vrij opgelegd (hard)."))
    return out


TESTS += _mo03_cases()


# ------------------------------------------------------------------
# MO-04 Vrije vierkante plaat (geen opleggingen): 6 starre modes ~0 Hz,
# dan de elastische. Controle van de vrij-vrij-route (CENTRE onder 0 Hz).
# Referentie mode 7: Leissa tabel 4.43 (vrije vierkante plaat, nu = 0,3),
# omega a^2 sqrt(rho t / D) = 13,468; tolerantie 1% (afronding van de
# tabel en DKT 24 x 24).
# ------------------------------------------------------------------
A4, T4 = 0.4, 0.004
D4 = E * T4 ** 3 / (12 * (1 - NU ** 2))
F4 = 13.468 / (2 * math.pi * A4 ** 2) * math.sqrt(D4 / (RHO * T4))


def build_mo04():
    m = Model("V30", attrs={"maxmode": 7})
    m.elset("Plaat", "Plaat4")
    quadmesh(m, "Plaat", 24, 24, rect(0, A4, 0, A4))
    m.mat("Plaat4", '<geometric type="Plate" thickness="%g m" />' % T4,
          STEEL, DENS)
    return m


TESTS.append(Case(
    "MO-04", GROUP, "Vrije vierkante plaat (vrij-vrij), DKT 24x24",
    "modal_3d", build_mo04,
    [Check("f1 (star)", lambda r: r.mode(1), ref=0.0, tol_abs=0.5,
           unit="Hz", source="starre-lichaamsbeweging"),
     Check("f6 (star)", lambda r: r.mode(6), ref=0.0, tol_abs=0.5,
           unit="Hz", source="starre-lichaamsbeweging"),
     _mode_check(7, F4, 0.01, "Leissa tabel 4.43: omega a^2 sqrt(rho t/D) "
                 "= 13,468 (vrije vierkante plaat, nu = 0,3)", "f7")] +
    # Vrij lichaam: de 6 starre modes bevatten elke starre beweging, dus
    # de som van de effectieve massa is precies R^T M R (ook voor de
    # rotatievrijheidsgraden van de schaal, DRX/DRY/DRZ = 1 in R).
    [Check("som eff. massa %s (7 modes)" % d,
           lambda r, d=d: r.mode_sum("MASS_EFFE_UN_D" + d), ref=1.0,
           tol=0.001, source="vrij lichaam: starre modes volledig")
     for d in ("X", "Z", "RX", "RZ")] +
    [Check("J_Z om de oorsprong", lambda r: r.mass_param("JZ"),
           ref=RHO * T4 * A4 ** 2 * 2 * A4 ** 2 / 3.0, tol=0.001,
           unit="kg.m2", source="int rho t (x^2 + y^2) dA = m 2a^2/3 "
           "(plaat [0,a]^2 in z = 0)")],
    note="Geen opleggingen: zoekfrequentie onder 0 Hz (CENTRE)."))


# ------------------------------------------------------------------
# MO-06 Vrij blok (geen opleggingen) buiten de oorsprong: hex20 10 x 2 x 2,
# 1 x 0,1 x 0,05 m vanaf (1, 2, 3). Effectieve massa voor de rotaties om de
# globale assen door de oorsprong (zoals Mecway): de som over de modes is
# het traagheidsmoment om die as, I = m (b^2 + h^2)/12 + m d^2
# (traagheidsmoment van een homogeen blok en de verschuivingsstelling van
# Steiner; standaardformules uit de mechanica).
# ------------------------------------------------------------------
X6, Y6, Z6 = 1.0, 2.0, 3.0
L6, B6, H6 = 1.0, 0.1, 0.05
MASS6 = RHO * L6 * B6 * H6
CG6 = (X6 + L6 / 2, Y6 + B6 / 2, Z6 + H6 / 2)
J6_CG = (MASS6 * (B6 ** 2 + H6 ** 2) / 12.0,
         MASS6 * (L6 ** 2 + H6 ** 2) / 12.0,
         MASS6 * (L6 ** 2 + B6 ** 2) / 12.0)
J6 = tuple(J6_CG[k] + MASS6 * sum(CG6[j] ** 2 for j in range(3) if j != k)
           for k in range(3))


def build_mo06():
    m = Model("V30", attrs={"maxmode": 12})
    m.elset("Blok", "Staal")
    hexmesh(m, "Blok", 10, 2, 2, box(X6, X6 + L6, Y6, Y6 + B6, Z6, Z6 + H6),
            order=2)
    m.mat("Staal", STEEL, DENS)
    return m


TESTS.append(Case(
    "MO-06", GROUP, "Vrij blok buiten de oorsprong: effectieve rotatiemassa",
    "modal_3d", build_mo06,
    [_effmass_sum_check("som eff. massa R%s (12 modes)" % "XYZ"[k],
                        "MASS_EFFE_UN_DR" + "XYZ"[k], "J" + "XYZ"[k], J6[k],
                        0.01, "I = m (b^2+h^2)/12 + m d^2 om de as door de "
                        "oorsprong (Steiner)") for k in range(3)] +
    [Check("J_%s zwaartepunt" % "XYZ"[k],
           lambda r, k=k: r.mass_param("JZ" + "XYZ"[k]), ref=J6_CG[k],
           tol=0.001, unit="kg.m2", source="m (b^2 + h^2)/12 (homogeen blok)")
     for k in range(3)] +
    [Check("som eff. massa X (Code-Aster)",
           lambda r: r.mode_sum("MASS_EFFE_UN_DX"), ref=1.0, tol=0.001,
           source="vrij lichaam: starre modes volledig")] +
    [_global_check("Mecway: cumulatief %s t/m mode 12" % d, 12,
                   "cumulativeeffectivemassfraction" + d, 1.0, 0.001, "",
                   "vrij lichaam: som van alle fracties 1")
     for d in ("tx", "ty", "tz")],
    note="6 starre modes + 6 elastische; rotaties om de oorsprong."))


# ------------------------------------------------------------------
# MO-07 Ingeklemde volumebalk (als MO-02, hex20 50 x 2 x 3) met spanningen
# per mode (fields displacements + stresses + vonmises). Referenties:
#   - effectieve massa: Euler-Bernoulli (zie FRAC_R; rotatie om de
#     inklemming, die in de oorsprong ligt);
#   - buigspanning van mode 1 (buiging in Y) halverwege, buitenvezel
#     y = a/2: sigma_xx = E (a/2) W1''(L/2) / sqrt(m) met de massa-
#     genormeerde vorm W1/sqrt(rho A L) (MASS_GENE, Blevins 8-1);
#   - Mecway 33 headless (mw_solve.py) op modellen/MO-07.liml met de
#     fieldvariables 'stress' en 'modal effective mass (fraction)'.
# ------------------------------------------------------------------
def _cf_curv(lam, u):
    s = (math.cosh(lam) + math.cos(lam)) / (math.sinh(lam) + math.sin(lam))
    return lam ** 2 * (math.cosh(lam * u) + math.cos(lam * u) -
                       s * (math.sinh(lam * u) + math.sin(lam * u)))


SIG7 = E * (A1 / 2) * _cf_curv(LAMBDA_CF[0], 0.5) / L1 ** 2 / math.sqrt(MASS1)
# Mecway 33 headless (mw_solve.py), 6 okt 2026: |stressxx| in (0,5; 0,01;
# 0) mode 1, modaleffectivemassfractionrz mode 1 en ry mode 2.
MECWAY7 = {"sxx1": 2320136514.52861, "rz1": 0.97042805, "ry2": 0.97050862}


def build_mo07():
    m = Model("V30", attrs={"maxmode": 6})
    m.elset("Balk", "Staal")
    mesh = hexmesh(m, "Balk", 50, 2, 3,
                   box(0, L1, -A1 / 2, A1 / 2, -B1 / 2, B1 / 2), order=2)
    m.mat("Staal", STEEL, DENS)
    m.face_selection("Inklemming", mesh["faces"]["u0"])
    m.add('<fixed selection="Inklemming" />')
    return m


def _mo07_checks():
    out = [
        _effmass_check("eff. massa RZ mode 1", 1, "MASS_EFFE_UN_DRZ",
                       FRAC_R[0], 0.01, "Euler-Bernoulli 0,97069 (zie MO-01)"),
        _effmass_check("eff. massa RY mode 2", 2, "MASS_EFFE_UN_DRY",
                       FRAC_R[0], 0.01, "idem, buiging in Z"),
        _effmass_sum_check("som eff. massa RZ (6 modes)", "MASS_EFFE_UN_DRZ",
                           "JZ", MASS1 * (L1 ** 2 / 3 + A1 ** 2 / 12), 0.01,
                           "I_z om de inklemming = m (L^2/3 + a^2/12)"),
        _effmass_sum_check("som eff. massa RY (6 modes)", "MASS_EFFE_UN_DRY",
                           "JY", MASS1 * (L1 ** 2 / 3 + B1 ** 2 / 12), 0.01,
                           "I_y om de inklemming = m (L^2/3 + b^2/12)"),
        Check("stressxx mode 1 halverwege", lambda r: abs(
            r.at("stressxx", (L1 / 2, A1 / 2, 0), time=1)), ref=SIG7,
            tol=0.02, unit="Pa/sqrt(kg)",
            source="E (a/2) W1''(L/2)/sqrt(rho A L), MASS_GENE (Blevins 8-1)"),
    ]
    if MECWAY7["sxx1"]:
        out += [
            Check("stressxx mode 1 t.o.v. Mecway", lambda r: abs(
                r.at("stressxx", (L1 / 2, A1 / 2, 0), time=1)),
                ref=MECWAY7["sxx1"], tol=0.01, unit="Pa/sqrt(kg)",
                in_series=False, source="Mecway 33 headless, zelfde .liml"),
            _effmass_check("eff. massa RZ mode 1 t.o.v. Mecway", 1,
                           "MASS_EFFE_UN_DRZ", MECWAY7["rz1"], 0.005,
                           "Mecway 33 headless (deelt door de vrije massa)"),
            _effmass_check("eff. massa RY mode 2 t.o.v. Mecway", 2,
                           "MASS_EFFE_UN_DRY", MECWAY7["ry2"], 0.005,
                           "Mecway 33 headless (deelt door de vrije massa)"),
        ]
    return out


TESTS.append(Case(
    "MO-07", GROUP, "Ingeklemde balk hex20: rotatiemassa en spanningen per "
    "mode", "modal_3d", build_mo07, _mo07_checks(),
    settings={"fields": ["displacements", "stresses", "vonmises"]},
    note="Spanningen per mode (fields) en effectieve massa rotaties."))


# ------------------------------------------------------------------
# MO-05 Massa-veerketen grond - k - m - k - m langs X (Mecway Spring en
# mass2 -> DIS_T K_T_D_L en POI1 M_T_D_N): omega^2 = k/m (3 -+ sqrt 5)/2
# (Thomson, Theory of Vibration, par. 5.1).
# ------------------------------------------------------------------
K5, M5 = 1000.0, 2.0
F5 = [math.sqrt(K5 / M5 * (3 + s * math.sqrt(5)) / 2) / (2 * math.pi)
      for s in (-1, 1)]


def build_mo05():
    m = Model("V30", attrs={"maxmode": 2})
    m.elset("Veer", "Veer")
    _e, nids = linemesh(m, "Veer", 2, (0, 0, 0), (2.0, 0, 0))
    m.mat("Veer", '<mechanical type="Spring" springconstant="%r N/m" />'
          % K5)
    m.node_selection("Grond", [nids[0]])
    m.node_selection("Massa", nids[1:])
    m.add('<fixed selection="Grond" />')
    for d in ((0, 1, 0), (0, 0, 1)):
        m.add('<displacement selection="Massa"><value>0 m</value>'
              '<x>%d</x><y>%d</y><z>%d</z></displacement>' % d)
    for n in nids[1:]:
        m.node_selection("M%d" % n, [n])
        m.add('<mass2 selection="M%d"><value>%r kg</value></mass2>'
              % (n, M5))
    return m


TESTS.append(Case(
    "MO-05", GROUP, "Massa-veerketen, 2 vrijheidsgraden (veer + mass2)",
    "modal_3d", build_mo05,
    [_mode_check(k + 1, f, 1e-4, "omega^2 = k/m (3 %s sqrt 5)/2 (Thomson "
                 "par. 5.1)" % ("-+"[k])) for k, f in enumerate(F5)],
    note="Discrete elementen: veer DIS_T en knoopmassa POI1."))


# ------------------------------------------------------------------
# MO-08 NAFEMS Challenge Problem 5: twee kwadratische truss-elementen
# (line3, truss="true"; GitHub issue #6)
# ------------------------------------------------------------------
# Knopen (m): 1 (0,1,0), 2 (1,1,0), 3 (0,0,0), 4 (0.5,0.5,0), 5 (1,1,0)
# (samenvallend met 2), 6 (0.5,1,0); elementen 1-6-2 en 3-4-5. Staal
# E = 210 GPa, nu = 0,3, rho = 7800 kg/m3, ronde staaf D = 10 mm. Knopen 1
# en 3 vast, uz = 0 op alle knopen, knoop 5 aan knoop 2 met constraint
# equations u5x = u2x en u5y = u2y (een scharnier). De bridge koppelt elke
# middenknoop dwars op de koorde aan de eindknopen
# (bridge_mesh._line3_truss_links); de richting z valt weg (uz = 0 overal).
# Referentie NAFEMS CP5: 451,1 en 1049,9 Hz. Mecway 34 zelf: 450 en
# 1030 Hz (issue #6).
RHO8 = '<density type="Simple" density="7800 kg/m³" />'
F8 = (451.1, 1049.9)


def build_mo08():
    m = Model("V30", attrs={"maxmode": 2})
    m.elset("Staaf", "Staal")
    for p in ((0, 1, 0), (1, 1, 0), (0, 0, 0), (0.5, 0.5, 0), (1, 1, 0),
              (0.5, 1, 0)):
        # zonder samenvoegen: knoop 5 valt samen met knoop 2
        m.nodes.append(tuple(float(c) for c in p))
    m.elem("Staaf", "line3", [1, 6, 2], 'truss="true"')
    m.elem("Staaf", "line3", [3, 4, 5], 'truss="true"')
    m.mat("Staal", '<geometric type="CircularBar" roundod="10 mm" />',
          STEEL, RHO8)
    m.node_selection("Vast", [1, 3])
    m.node_selection("Alle", range(1, 7))
    m.add('<fixed selection="Vast" />')
    m.add('<displacement selection="Alle"><value>0 mm</value>'
          '<x>0</x><y>0</y><z>1</z></displacement>')
    for dof in ("ux", "uy"):
        m.add('<constraintequation><term coefficient="1 1/m" nid="5" '
              'dof="%s" /><term coefficient="-1 1/m" nid="2" dof="%s" />'
              '<constant>0</constant></constraintequation>' % (dof, dof))
    return m


TESTS.append(Case(
    "MO-08", GROUP, "NAFEMS CP5: twee line3-truss-elementen, 2 modes",
    "modal_3d", build_mo08,
    [_mode_check(k + 1, f, 0.002, "NAFEMS Challenge Problem 5")
     for k, f in enumerate(F8)],
    note="Line3-truss als twee SEG2-cellen (BARRE), middenknoop dwars "
         "gekoppeld (GitHub issue #6). Mecway 34 zelf: 450 en 1030 Hz."))
