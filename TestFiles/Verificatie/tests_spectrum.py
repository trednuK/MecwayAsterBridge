# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Responsspectrumanalyse (bridge-analyse spectrum_3d: Mecway Frequency-model
met een Gravity-tabel als spectrum -> CALC_MODES + COMB_SISM_MODAL;
Scripts/bridge_spectrum.py). Toelichting: docs/Verificatie.md par. 8 (SP).

Referenties:
  - Code-Aster-testcase sdld25a (17.4, share/aster/tests): 8 massa's van
    10 kg tussen 9 veren van 1e5 N/m met proportionele demping (dempers
    50 N s/m = beta k, beta = 5e-4 s), spectrum DEFI_NAPPE voor 0,5% en 5%
    demping (LOG in de frequentie, LIN in de demping), SRSS, ACCE_ABSOLU;
    de waarden van TEST_RESU (VALE_CALC; VALE_REFE uit de "fiche de
    validation" en POUX staan in de bron van de check);
  - handberekening van het 2-vrijheidsgradensysteem grond - k1 - m1 - k2 -
    m2 (eigenwaarden van de 2x2-matrices; participatie Gamma_i = phi_i^T M
    1, respons Gamma_i S_i / w_i^2 phi_i; SRSS; CQC met de correlatie van
    Der Kiureghian (1981) voor gelijke demping, Chopra (2012) vgl. 13.7.10;
    missing mass met de pseudo-mode psi = K^-1 M 1; richtingscombinatie
    SRSS, 100-30-30 (EN 1998-1 par. 4.3.3.5.2) en 100-40-40);
  - Euler-Bernoulli-console (Blevins 1979, tabel 8-1): Gamma_1 phi_1(L) =
    1,5660 en effectieve massa 0,6131 m van mode 1.
Alle spectra hier zijn Mecway-gravities met een tabel (periode -> m/s2),
behalve SP-01 (sdld25a: DEFI_NAPPE via #ASTER-SPECTRE).
"""
import math
from verif_lib import Case, Check, Model, linemesh, hexmesh, box

GROUP = "Responsspectrum"


# ------------------------------------------------------------------
# Hulpfuncties (handberekening)
# ------------------------------------------------------------------
def table(x, pts):
    """Mecway-tabel: lineair, constant buiten de tabel."""
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def rho_cqc(wi, wj, xi):
    """CQC-correlatie voor gelijke demping (Der Kiureghian 1981; Chopra
    vgl. 13.7.10)."""
    r = wi / wj
    return (8 * xi ** 2 * (1 + r) * r ** 1.5 /
            ((1 - r * r) ** 2 + 4 * xi ** 2 * r * (1 + r) ** 2))


def eig2(K, M):
    """Eigenwaarden en massa-genormeerde vectoren van 2x2 K, M (M
    diagonaal): [(w, (phi1, phi2))] oplopend."""
    m1, m2 = M[0][0], M[1][1]
    a = m1 * m2
    b = -(K[0][0] * m2 + K[1][1] * m1)
    c = K[0][0] * K[1][1] - K[0][1] * K[1][0]
    out = []
    for s in (-1, 1):
        lam = (-b + s * math.sqrt(b * b - 4 * a * c)) / (2 * a)
        # (K - lam M) phi = 0: phi = (K01, lam m1 - K00)
        v = (-K[0][1], K[0][0] - lam * m1)
        n = math.sqrt(m1 * v[0] ** 2 + m2 * v[1] ** 2)
        out.append((math.sqrt(lam), (v[0] / n, v[1] / n)))
    return out


def _comb(vals, ws, xi, rule):
    """Modale combinatie van de bijdragen vals[i] (met teken)."""
    if rule == "SRSS":
        return math.sqrt(sum(v * v for v in vals))
    return math.sqrt(sum(rho_cqc(ws[i], ws[j], xi) * vals[i] * vals[j]
                         for i in range(len(vals))
                         for j in range(len(vals))))


def _summary(r):
    """BRIDGE_SPECTRUM-regels uit de .mess (bridge_spectrum.read_summary)."""
    import sys
    from verif_lib import SCRIPTS
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)
    import bridge_spectrum
    return bridge_spectrum.read_summary(r.mess)


def _springs(m, mat, k):
    m.mat(mat, '<mechanical type="Spring" springconstant="%r N/m" />' % k)


def _gravity(tables):
    """Gravity met per as een tabel {as: [(T, a)]} (periode -> m/s2)."""
    parts = []
    for ax in "xyz":
        pts = tables.get(ax)
        if not pts:
            parts.append("<%s>0 m/s²</%s>" % (ax, ax))
            continue
        parts += ['<%s time="%r s">%r m/s²</%s>' % (ax, t, a, ax)
                  for t, a in pts]
    return '<gravity>%s</gravity>' % "".join(parts)


# ------------------------------------------------------------------
# SP-01 sdld25a: 8 massa's tussen 9 veren, spectrum DEFI_NAPPE (#ASTER)
# ------------------------------------------------------------------
K25, M25, BETA25 = 1.0e5, 10.0, 5.0e-4
SDLD25A_CODE = [
    "A_0_5 = DEFI_FONCTION(NOM_PARA='FREQ', INTERPOL='LOG',",
    "    VALE=(1.0, 1.0, 3.0, 25.0, 13.0, 25.0, 33.0, 1.0))",
    "A_5_0 = DEFI_FONCTION(NOM_PARA='FREQ', INTERPOL='LOG',",
    "    VALE=(1.0, 1.0, 3.0, 10.0, 13.0, 10.0, 33.0, 1.0))",
    "SPECT = DEFI_NAPPE(NOM_PARA='AMOR', INTERPOL=('LIN', 'LOG'),",
    "    PARA=(0.005, 0.05), FONCTION=(A_0_5, A_5_0))",
]
# TEST_RESU van sdld25a: (punt, VALE_CALC, VALE_REFE fiche, VALE_REFE POUX)
SDLD25A_ACCE = [("A", 0.0, 1.1363736792287, 1.0, 1.0),
                ("P1", 1.0, 10.449843284531, 10.45, 10.45),
                ("P2", 2.0, 19.029947319229, 19.03, 19.03),
                ("P3", 3.0, 25.317694891527, 25.31, 25.32),
                ("P4", 4.0, 28.945354190646, 28.94, 28.95)]
SDLD25A_FREQ = [5.5273931669183, 10.886839289456, 15.91549430919,
                20.460565087967, 24.383951950093, 27.56644477109,
                29.911345117011, 31.347404377423]


def build_sp01():
    m = Model("V30", attrs={"maxmode": 8})
    m.elset("Veer", "Veer")
    _e, nids = linemesh(m, "Veer", 9, (0, 0, 0), (9.0, 0, 0))
    _springs(m, "Veer", K25)
    m.node_selection("A_en_B", [nids[0], nids[-1]])
    m.node_selection("Massa", nids[1:-1])
    m.add('<fixed selection="A_en_B" />')
    for d in ((0, 1, 0), (0, 0, 1)):
        m.add('<displacement selection="Massa"><value>0 m</value>'
              '<x>%d</x><y>%d</y><z>%d</z></displacement>' % d)
    for n in nids[1:-1]:
        m.node_selection("M%d" % n, [n])
        m.add('<mass2 selection="M%d"><value>%r kg</value></mass2>'
              % (n, M25))
    # Dempers 50 N s/m = beta k (sdld25a): Rayleigh beta = 5e-4 s geeft de
    # AMOR_REDUIT van de testcase (xi_1 = beta w_1 / 2 = 0,008682).
    m.add('<rayleighdamping selection=""><alpha>0 rad/s</alpha>'
          '<beta>%r s</beta></rayleighdamping>' % BETA25)
    lines = (["** ASTER " + l for l in SDLD25A_CODE] +
             ["** ASTER-SPECTRE X = SPECT",
              "** ASTER-OPTIE spectrum_damping = 0",
              "** ASTER-OPTIE modal_combination = SRSS",
              "** ASTER-OPTIE missing_mass = false"])
    m.add("<ccxmodeldefinition>%s</ccxmodeldefinition>" % "\n".join(lines))
    return m


def _sp01_checks():
    out = [Check("f%d" % (k + 1), lambda r, k=k: r.mode_param(k + 1, "FREQ"),
                 ref=f, tol=1e-4, unit="Hz", source="sdld25a VALE_CALC")
           for k, f in enumerate(SDLD25A_FREQ)]
    out += [Check("ACCE_ABSOLU DX %s" % name, lambda r, x=x: r.at(
        "accx", (x, 0, 0)), ref=calc, tol=0.01, unit="m/s2",
        source="sdld25a VALE_CALC (VALE_REFE fiche %g, POUX %g)" % (fiche,
                                                                    poux))
        for name, x, calc, fiche, poux in SDLD25A_ACCE]
    return out


TESTS = [Case(
    "SP-01", GROUP, "sdld25a: 8 massa's en veren, spectrum DEFI_NAPPE, SRSS",
    "spectrum_3d", build_sp01, _sp01_checks(),
    settings={"fields": ["displacements", "accelerations", "reactions"]},
    note="Mecway Spring + mass2, Rayleigh beta = 5e-4 s; spectrum via "
         "#ASTER-code + #ASTER-SPECTRE X (LOG in f, LIN in xi); ACCE_ABSOLU "
         "met de automatische correctie van Code-Aster.")]


# ------------------------------------------------------------------
# SP-02..04 Twee massa's: grond - k1 - m1 - k2 - m2 langs X (een kleine
# massa afgestemd op de grote: twee modes dicht bij elkaar, w2/w1 ~ 1,25,
# zodat CQC duidelijk van SRSS verschilt). Spectrum als Mecway-tabel in de
# periode, beide perioden op een schuin deel van de tabel.
# ------------------------------------------------------------------
K1, M1 = 1.0e5, 100.0
M2 = 5.0
K2 = M2 * K1 / M1 / (1 + M2 / M1) ** 2      # afstemming 1 / (1 + mu)
XI2 = 0.05
SPEC2 = [(0.0, 2.0), (0.1, 8.0), (0.3, 5.0), (2.0, 1.0)]
MODES2 = eig2([[K1 + K2, -K2], [-K2, K2]], [[M1, 0], [0, M2]])
W2 = [w for w, _p in MODES2]
GAM2 = [M1 * p[0] + M2 * p[1] for _w, p in MODES2]
SA2 = [table(2 * math.pi / w, SPEC2) for w in W2]


def _sp2_disp(j, rule, n=2):
    vals = [GAM2[i] * SA2[i] / W2[i] ** 2 * MODES2[i][1][j] for i in range(n)]
    return _comb(vals, W2, XI2, rule)


def _sp2_base(rule, n=2):
    vals = [GAM2[i] ** 2 * SA2[i] for i in range(n)]
    return _comb(vals, W2, XI2, rule)


def _sp2_acc(j, rule, n=2):
    vals = [GAM2[i] * SA2[i] * MODES2[i][1][j] for i in range(n)]
    return _comb(vals, W2, XI2, rule)


# Missing mass met alleen mode 1: pseudo-mode psi = K^-1 M 1 (statische
# verplaatsing onder een eenheidsversnelling): psi_1 = (M1 + M2) / K1,
# psi_2 = psi_1 + M2 / K2. Rest = (psi - Gamma_1 phi_1 / w_1^2) S(f_1).
PSI2 = [(M1 + M2) / K1, (M1 + M2) / K1 + M2 / K2]


def _sp4_disp(j):
    d1 = GAM2[0] * SA2[0] / W2[0] ** 2 * MODES2[0][1][j]
    rest = (PSI2[j] - GAM2[0] * MODES2[0][1][j] / W2[0] ** 2) * SA2[0]
    return math.hypot(d1, rest)


def build_sp2(maxmode):
    def build():
        m = Model("V30", attrs={"maxmode": maxmode})
        m.elset("Veer1", "Veer1")
        m.elset("Veer2", "Veer2")
        n0, n1, n2 = (m.node(0, 0, 0), m.node(1, 0, 0), m.node(2, 0, 0))
        m.elem("Veer1", "line2", [n0, n1])
        m.elem("Veer2", "line2", [n1, n2])
        _springs(m, "Veer1", K1)
        _springs(m, "Veer2", K2)
        m.node_selection("Grond", [n0])
        m.node_selection("Massa", [n1, n2])
        m.node_selection("M1", [n1])
        m.node_selection("M2", [n2])
        m.add('<fixed selection="Grond" />')
        for d in ((0, 1, 0), (0, 0, 1)):
            m.add('<displacement selection="Massa"><value>0 m</value>'
                  '<x>%d</x><y>%d</y><z>%d</z></displacement>' % d)
        m.add('<mass2 selection="M1"><value>%r kg</value></mass2>' % M1)
        m.add('<mass2 selection="M2"><value>%r kg</value></mass2>' % M2)
        m.add(_gravity({"x": SPEC2}))
        return m
    return build


def _sp2_checks(rule):
    src = ("handberekening 2 vrijheidsgraden, %s (%s)" % (
        rule, "Der Kiureghian rho" if rule == "CQC" else "wortel som "
        "kwadraten"))
    return [
        Check("u m1", lambda r: r.at("displx", (1, 0, 0)),
              ref=_sp2_disp(0, rule), tol=0.005, unit="m", source=src),
        Check("u m2", lambda r: r.at("displx", (2, 0, 0)),
              ref=_sp2_disp(1, rule), tol=0.005, unit="m", source=src),
        Check("reactie grond", lambda r: r.at("reactionforcex", (0, 0, 0)),
              ref=_sp2_base(rule), tol=0.005, unit="N",
              source=src + "; Gamma_i^2 S_i"),
        Check("totale reactie (log)", lambda r: _summary(r)["reactie"]["FX"],
              ref=_sp2_base(rule), tol=0.005, unit="N",
              source=src + "; BRIDGE_SPECTRUM_REACTIE"),
        Check("abs. versnelling m2", lambda r: r.at("accx", (2, 0, 0)),
              ref=_sp2_acc(1, rule), tol=0.005, unit="m/s2",
              source=src + "; Gamma_i S_i phi_i"),
    ]


TESTS += [
    Case("SP-02", GROUP, "Twee massa's, spectrumtabel (periode), SRSS",
         "spectrum_3d", build_sp2(2), _sp2_checks("SRSS"),
         settings={"modal_combination": "SRSS"},
         note="f1/f2 = %.3f/%.3f Hz, Sa = %.4f/%.4f m/s2 (lineair in T)."
         % (W2[0] / 2 / math.pi, W2[1] / 2 / math.pi, SA2[0], SA2[1])),
    Case("SP-03", GROUP, "Twee massa's, spectrumtabel (periode), CQC",
         "spectrum_3d", build_sp2(2), _sp2_checks("CQC"),
         settings={"modal_combination": "CQC"},
         note="rho_12 = %.4f (xi = %g); CQC t.o.v. SRSS u m2 %+.1f%%."
         % (rho_cqc(W2[0], W2[1], XI2), XI2,
            100 * (_sp2_disp(1, "CQC") / _sp2_disp(1, "SRSS") - 1))),
    Case("SP-04", GROUP, "Twee massa's, 1 mode met missing mass",
         "spectrum_3d", build_sp2(1), [
             Check("u m1", lambda r: r.at("displx", (1, 0, 0)),
                   ref=_sp4_disp(0), tol=0.005, unit="m",
                   source="mode 1 + (psi - Gamma_1 phi_1 / w_1^2) S(f_1), "
                          "psi = K^-1 M 1"),
             Check("u m2", lambda r: r.at("displx", (2, 0, 0)),
                   ref=_sp4_disp(1), tol=0.005, unit="m",
                   source="idem"),
             Check("reactie grond", lambda r: r.at(
                 "reactionforcex", (0, 0, 0)),
                 ref=math.hypot(GAM2[0] ** 2 * SA2[0],
                                (M1 + M2 - GAM2[0] ** 2) * SA2[0]),
                 tol=0.005, unit="N",
                 source="sqrt((M_eff,1 S_1)^2 + ((M - M_eff,1) S_1)^2)"),
             Check("abs. versnelling m2", lambda r: r.at(
                 "accx", (2, 0, 0)),
                 ref=math.hypot(GAM2[0] * SA2[0] * MODES2[0][1][1],
                                (1 - GAM2[0] * MODES2[0][1][1]) * SA2[0]),
                 tol=0.005, unit="m/s2",
                 source="Gamma_1 S_1 phi_1 en (1 - Gamma_1 phi_1) S(f_1)"),
         ],
         settings={"modal_combination": "SRSS", "missing_mass": True},
         note="Missing mass: pseudo-mode (MODE_STATIQUE) met het spectrum op "
              "de hoogste gerekende frequentie (hier f1)."),
    Case("SP-05", GROUP, "Twee massa's, 1 mode zonder missing mass",
         "spectrum_3d", build_sp2(1), [
             Check("u m2", lambda r: r.at("displx", (2, 0, 0)),
                   ref=_sp2_disp(1, "SRSS", 1), tol=0.005, unit="m",
                   source="alleen mode 1: Gamma_1 S_1 / w_1^2 phi_1"),
             Check("reactie grond", lambda r: r.at(
                 "reactionforcex", (0, 0, 0)),
                 ref=_sp2_base("SRSS", 1), tol=0.005, unit="N",
                 source="M_eff,1 S_1 (de rest van de massa ontbreekt)"),
         ],
         settings={"modal_combination": "SRSS", "missing_mass": False},
         note="Zonder missing mass draagt mode 1 %.0f%% van de massa: de "
              "reactie is te laag (WARNING)." % (
                  100 * GAM2[0] ** 2 / (M1 + M2))),
]


# ------------------------------------------------------------------
# SP-06 Richtingscombinatie: een massa aan twee schuine veren in het
# XY-vlak (30 en 120 graden, verschillende stijfheid). Beide modes
# bewegen in X en Y, dus spectra in X en Y geven elk een bijdrage aan
# displx en disply; de richtingen worden met SRSS, 100-30-30 of 100-40-40
# gecombineerd.
# ------------------------------------------------------------------
KA, KB, M6 = 2.0e5, 5.0e4, 50.0
SPEC6X = [(0.0, 3.0), (0.05, 6.0), (0.5, 6.0), (2.0, 1.5)]
SPEC6Y = [(0.0, 1.5), (0.1, 3.0), (1.0, 2.0)]
# Veerrichtingen (loodrecht op elkaar): de eigenvormen liggen langs de
# veren, w^2 = k / m.
DIR6A = (math.cos(math.radians(30)), math.sin(math.radians(30)))
DIR6B = (math.cos(math.radians(120)), math.sin(math.radians(120)))
MODES6 = sorted([(math.sqrt(KB / M6), DIR6B), (math.sqrt(KA / M6), DIR6A)])


def _sp6_dir(j, spec):
    """Respons in component j (0 = x, 1 = y) op het spectrum in richting
    d, SRSS over de 2 modes (ver uit elkaar). Gamma = m phi_d / sqrt(m)
    met de massa-genormeerde vorm phi / sqrt(m)."""
    d = 0 if spec is SPEC6X else 1
    vals = []
    for w, v in MODES6:
        gam = math.sqrt(M6) * v[d]
        phi_j = v[j] / math.sqrt(M6)
        vals.append(gam * table(2 * math.pi / w, spec) / w ** 2 * phi_j)
    return math.sqrt(sum(x * x for x in vals))


def _sp6(j, rule):
    a, b = _sp6_dir(j, SPEC6X), _sp6_dir(j, SPEC6Y)
    if rule == "SRSS":
        return math.hypot(a, b)
    c = 0.3 if rule == "100-30-30" else 0.4
    return max(a + c * b, b + c * a)


def build_sp06():
    m = Model("V30", attrs={"maxmode": 2})
    m.elset("VeerA", "VeerA")
    m.elset("VeerB", "VeerB")
    n0 = m.node(0, 0, 0)
    na = m.node(-DIR6A[0], -DIR6A[1], 0)
    nb = m.node(-DIR6B[0], -DIR6B[1], 0)
    m.elem("VeerA", "line2", [na, n0])
    m.elem("VeerB", "line2", [nb, n0])
    _springs(m, "VeerA", KA)
    _springs(m, "VeerB", KB)
    m.node_selection("Grond", [na, nb])
    m.node_selection("Massa", [n0])
    m.add('<fixed selection="Grond" />')
    m.add('<displacement selection="Massa"><value>0 m</value>'
          '<x>0</x><y>0</y><z>1</z></displacement>')
    m.add('<mass2 selection="Massa"><value>%r kg</value></mass2>' % M6)
    m.add(_gravity({"x": SPEC6X, "y": SPEC6Y}))
    return m


def _sp6_checks(rule):
    src = "handberekening, modes SRSS, richtingen %s" % rule
    return [Check("u x", lambda r: r.at("displx", (0, 0, 0)),
                  ref=_sp6(0, rule), tol=0.005, unit="m", source=src),
            Check("u y", lambda r: r.at("disply", (0, 0, 0)),
                  ref=_sp6(1, rule), tol=0.005, unit="m", source=src)]


TESTS += [
    Case("SP-06%s" % s, GROUP, "Massa aan schuine veren, spectra X en Y, "
         "richtingen %s" % rule, "spectrum_3d", build_sp06,
         _sp6_checks(rule),
         settings={"modal_combination": "SRSS",
                   "direction_combination": rule},
         note="Twee spectrumtabellen (gravity x en y); 100-30-30 rekent de "
              "bridge zelf uit VALE_DIRE.")
    for s, rule in (("a", "SRSS"), ("b", "100-30-30"), ("c", "100-40-40"))]


# ------------------------------------------------------------------
# SP-07 Ingeklemde volumebalk (hex20 50 x 2 x 3, als MO-07), vlak spectrum
# S = 1 m/s2 in Y (gravity zonder tabel), alleen mode 1 (buiging in Y),
# zonder missing mass. Euler-Bernoulli (Blevins tabel 8-1): Gamma_1
# phi_1(L) = 1,5660; M_eff,1 = 0,6131 m; buigspanning halverwege uit de
# genormeerde vorm (MO-07). De frequentie komt uit de run (eigen controle
# in MO-07), zodat deze case de spectrale stap meet.
# ------------------------------------------------------------------
L7, A7, B7 = 1.0, 0.02, 0.03
E7, RHO7 = 210e9, 7850.0
MASS7 = RHO7 * A7 * B7 * L7
LAM1 = 1.87510407
S7 = 1.0


def _cf_mode(u):
    s = (math.cosh(LAM1) + math.cos(LAM1)) / (math.sinh(LAM1) + math.sin(LAM1))
    return (math.cosh(LAM1 * u) - math.cos(LAM1 * u) -
            s * (math.sinh(LAM1 * u) - math.sin(LAM1 * u)))


def _cf_curv(u):
    s = (math.cosh(LAM1) + math.cos(LAM1)) / (math.sinh(LAM1) + math.sin(LAM1))
    return LAM1 ** 2 * (math.cosh(LAM1 * u) + math.cos(LAM1 * u) -
                        s * (math.sinh(LAM1 * u) + math.sin(LAM1 * u)))


_N = 4000
_INT_W = sum(_cf_mode((i + 0.5) / _N) for i in range(_N)) / _N   # 0,7830
_INT_W2 = sum(_cf_mode((i + 0.5) / _N) ** 2 for i in range(_N)) / _N  # 1
GAM7 = math.sqrt(MASS7) * _INT_W / math.sqrt(_INT_W2)   # massa-genormeerd
PHI_TIP7 = _cf_mode(1.0) / math.sqrt(MASS7 * _INT_W2)
SIG7 = E7 * (A7 / 2) * _cf_curv(0.5) / L7 ** 2 / math.sqrt(MASS7 * _INT_W2)


def _w1(r):
    return 2 * math.pi * r.mode_param(1, "FREQ")


def build_sp07():
    m = Model("V30", attrs={"maxmode": 1})
    m.elset("Balk", "Staal")
    mesh = hexmesh(m, "Balk", 50, 2, 3,
                   box(0, L7, -A7 / 2, A7 / 2, -B7 / 2, B7 / 2), order=2)
    m.mat("Staal", '<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
          'poissonratio="0.3" />',
          u'<density type="Simple" density="7850 kg/m³" />')
    m.face_selection("Inklemming", mesh["faces"]["u0"])
    m.add('<fixed selection="Inklemming" />')
    m.add('<gravity><x>0 m/s²</x><y>%r m/s²</y><z>0 m/s²</z>'
          '</gravity>' % S7)
    return m


TESTS += [Case(
    "SP-07", GROUP, "Ingeklemde volumebalk hex20, vlak spectrum, mode 1",
    "spectrum_3d", build_sp07, [
        Check("f1", lambda r: r.mode_param(1, "FREQ"),
              ref=LAM1 ** 2 / (2 * math.pi * L7 ** 2) * math.sqrt(
                  E7 * B7 * A7 ** 3 / 12 / (RHO7 * A7 * B7)),
              tol=0.005, unit="Hz", source="Euler-Bernoulli (Blevins 8-1)"),
        Check("u tip", lambda r: r.at("disply", (L7, 0, 0)) * _w1(r) ** 2,
              ref=GAM7 * PHI_TIP7 * S7, tol=0.005, unit="m/s2",
              source="u w1^2 = Gamma_1 phi_1(L) S = 1,5660 S (Euler-"
                     "Bernoulli)"),
        Check("stressxx halverwege", lambda r: r.at(
            "stressxx", (L7 / 2, A7 / 2, 0)) * _w1(r) ** 2,
            ref=GAM7 * S7 * SIG7, tol=0.02, unit="Pa/s2",
            source="Gamma_1 S sigma(phi_1), buitenvezel (zoals MO-07)"),
        Check("vonmises halverwege", lambda r: r.at(
            "vonmises", (L7 / 2, A7 / 2, 0)) * _w1(r) ** 2,
            ref=GAM7 * S7 * SIG7, tol=0.02, unit="Pa/s2",
            source="eenassig: von Mises = |sigma_xx|"),
        Check("totale reactie Y", lambda r: _summary(r)["reactie"]["FY"],
              ref=GAM7 ** 2 * S7, tol=0.01, unit="N",
              source="M_eff,1 S = 0,6131 m S (Euler-Bernoulli)"),
        Check("abs. versnelling tip", lambda r: r.at("accy", (L7, 0, 0)),
              ref=S7 * math.hypot(GAM7 * PHI_TIP7, 1 - GAM7 * PHI_TIP7),
              tol=0.005, unit="m/s2",
              source="Gamma_1 phi_1(L) S en de rest (1 - Gamma_1 phi_1) S"),
    ],
    settings={"missing_mass": False,
              "fields": ["displacements", "accelerations", "stresses",
                         "vonmises", "reactions"]},
    note="Spanningen en von Mises (per mode berekend en gecombineerd) op "
         "volume-elementen.")]
