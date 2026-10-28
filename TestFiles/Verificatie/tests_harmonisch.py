# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Harmonische respons in het frequentiedomein (bridge-analyse harmonic_3d,
Scripts/bridge_harmonic.py: CALC_MODES -> DYNA_VIBRA TYPE_CALCUL='HARM'
BASE_CALCUL='GENE' -> REST_GENE_PHYS, of direct BASE_CALCUL='PHYS').
Mecway heeft geen harmonische analyse (manual v33 hoofdstuk 6); de modellen
zijn Frequency-analyses (V30). Toelichting: docs/Verificatie.md par. 7 (HR).

Referenties:
  - analytisch, 1 vrijheidsgraad (veer k, massa m, demping zeta) onder F0
    e^(i w t): U = u_st / ((1 - r^2) + i 2 zeta r), r = f / f_n, dus |U| =
    u_st / sqrt((1 - r^2)^2 + (2 zeta r)^2) en arg U = -atan2(2 zeta r,
    1 - r^2) (Clough & Penzien, Dynamics of Structures, 2e druk 1993,
    hoofdstuk 3); piek u_st / (2 zeta sqrt(1 - zeta^2)) bij f_n sqrt(1 -
    2 zeta^2);
  - analytisch, uitkragende Euler-Bernoulli-balk met een harmonische
    tipkracht: receptantie van de tip w(L)/F = (sin bL cosh bL - cos bL
    sinh bL) / (E I b^3 (1 + cos bL cosh bL)), b^4 = rho A w^2 / (E I)
    (Bishop & Johnson, The Mechanics of Vibration, 1960, receptantietabellen;
    niet lokaal ingezien: hier afgeleid en nagerekend, statische limiet
    L^3 / 3EI, polen bij 1 + cos bL cosh bL = 0 = de eigenfrequenties,
    Blevins 1979 tabel 8-1); met massaproportionele demping C = alpha M
    (Rayleigh alpha) wordt b^4 = rho A (w^2 - i alpha w) / (E I);
  - de directe berekening (PHYS) op hetzelfde model als referentie voor de
    modale (GENE): waarden in PHYS_REF hieronder (Code-Aster 17.4, deze
    bridge, harm_basis PHYS, gelijk gecontroleerd met de PHYS-cases).
"""
import cmath
import csv
import io
import math
from verif_lib import Case, Check, Model, linemesh, hexmesh, box

GROUP = "Harmonische respons"


# ------------------------------------------------------------------
# HR-01 1 vrijheidsgraad: grond (0,0,0) - veer k - massa (1,0,0), de
# massaknoop alleen vrij in X (zoals MC-01, tests_modaal_demping), kracht
# F0 in X op de massa.
# ------------------------------------------------------------------
K1, M1 = 1000.0, 2.0
W1 = math.sqrt(K1 / M1)                 # 22,36 rad/s
FN1 = W1 / (2.0 * math.pi)              # 3,559 Hz
F0 = 10.0
U_ST = F0 / K1                          # 0,01 m
ZETA = 0.05
MASS_X = (1.0, 0.0, 0.0)


def sdof(f, zeta, ust=U_ST):
    """Complexe stationaire respons U (u(t) = Re(U e^(i w t)))."""
    r = f / FN1
    return ust / complex(1.0 - r * r, 2.0 * zeta * r)


def _spring(m, mat, k):
    m.mat(mat, '<mechanical type="Spring" springconstant="%r N/m" />' % k)


def _damper(m, mat, c):
    m.mat(mat, '<mechanical type="Damper" dampingcoefficient="%r N.s/m" />'
          % c)


def build_sdof(c=None, alpha=0.0, force=None, extra=()):
    def build():
        m = Model("V30", attrs={"maxmode": 1})
        m.elset("Veer", "Veer")
        a, n = m.node(0, 0, 0), m.node(1, 0, 0)
        m.elem("Veer", "line2", [a, n])
        _spring(m, "Veer", K1)
        ground = [a]
        if c:
            m.elset("Demper", "Demper")
            b = m.node(2, 0, 0)
            m.elem("Demper", "line2", [n, b])
            _damper(m, "Demper", c)
            ground.append(b)
        m.node_selection("Grond", ground)
        m.add('<fixed selection="Grond" />')
        m.node_selection("Massa", [n])
        for d in ((0, 1, 0), (0, 0, 1)):
            m.add('<displacement selection="Massa"><value>0 m</value>'
                  '<x>%d</x><y>%d</y><z>%d</z></displacement>' % d)
        m.add('<mass2 selection="Massa"><value>%r kg</value></mass2>' % M1)
        m.node_selection("Last", [n])
        m.add('<force selection="Last">%s<y>0 N</y><z>0 N</z></force>'
              % (force or "<x>%r N</x>" % F0))
        m.node_selection("MEETPUNT_Massa", [n])
        if alpha:
            m.add('<rayleighdamping selection=""><alpha>%r rad/s</alpha>'
                  '<beta>0 s</beta></rayleighdamping>' % alpha)
        for x in extra:
            m.add(x)
        return m
    return build


def _steps(r):
    """[(f, variabelen)] per frequentie."""
    return [(r.modes[int(k)], d) for k, d in r.steps]


def _node(r, point):
    return r.nearest(point)


def _max_amp_dev(r, exact, var="displampx", point=MASS_X):
    nid = _node(r, point)
    return max(abs(d[var][nid] - abs(exact(f))) / abs(exact(f))
               for f, d in _steps(r))


def _max_phase_dev(r, exact, var="displphasex", point=MASS_X):
    nid = _node(r, point)
    out = 0.0
    for f, d in _steps(r):
        dev = (d[var][nid] - math.degrees(cmath.phase(exact(f))) + 180.0) \
            % 360.0 - 180.0
        out = max(out, abs(dev))
    return out


def _max_complex_dev(r, exact, point=MASS_X):
    nid = _node(r, point)
    return max(abs(complex(d["displx"][nid], d["displix"][nid]) - exact(f))
               / abs(exact(f)) for f, d in _steps(r))


def _peak(r, var="displampx", point=MASS_X):
    nid = _node(r, point)
    return max((d[var][nid], f) for f, d in _steps(r))


def _sdof_checks(zeta, src, n_freq=None, peak=True):
    exact = lambda f: sdof(f, zeta)
    out = [
        Check("|U| over alle frequenties (max. rel. afwijking)",
              lambda r: _max_amp_dev(r, exact), ref=0.0, tol_abs=0.01,
              unit="-", source="|U| = u_st / sqrt((1 - r^2)^2 + (2 zeta "
              "r)^2), %s (Clough & Penzien hfst. 3)" % src),
        Check("fase over alle frequenties (max. afwijking)",
              lambda r: _max_phase_dev(r, exact), ref=0.0, tol_abs=1.0,
              unit="graden", source="arg U = -atan2(2 zeta r, 1 - r^2)"),
        Check("Re + i Im over alle frequenties (max. |U - U_exact| / "
              "|U_exact|)", lambda r: _max_complex_dev(r, exact), ref=0.0,
              tol_abs=0.01, unit="-", source="U = u_st / ((1 - r^2) + i 2 "
              "zeta r); displx = Re U, displix = Im U"),
    ]
    if peak:
        out += [
            Check("piekamplitude", lambda r: _peak(r)[0],
                  ref=U_ST / (2 * zeta * math.sqrt(1 - zeta ** 2)), tol=0.01,
                  unit="m", source="u_st / (2 zeta sqrt(1 - zeta^2)); de "
                  "verfijning LARGEUR_3DB legt een punt op de piek"),
            Check("frequentie van de piek", lambda r: _peak(r)[1],
                  ref=FN1 * math.sqrt(1 - 2 * zeta ** 2), tol=0.001,
                  unit="Hz", source="f_n sqrt(1 - 2 zeta^2)"),
            Check("versnellingsamplitude in de piek",
                  lambda r: max((d["displampx"][_node(r, MASS_X)], d[
                      "accampx"][_node(r, MASS_X)] / (2 * math.pi * f) ** 2
                      / d["displampx"][_node(r, MASS_X)])
                      for f, d in _steps(r))[1],
                  ref=1.0, tol=1e-5, unit="-",
                  source="|a| = w^2 |u| (accampx / (w^2 displampx))"),
        ]
    if n_freq:
        out.append(Check("aantal frequenties", lambda r: len(r.steps),
                         ref=float(n_freq), tol_abs=0.0, unit="-",
                         source="bereik + verfijning (DEFI_LIST_FREQ)"))
    return out


SDOF_RANGE = {"harm_freq_start": 0.5, "harm_freq_end": 7.0,
              "harm_freq_count": 27, "harm_refine_points": 5}
ALPHA1 = 2.0 * ZETA * W1                # Rayleigh alpha: zeta = alpha / 2w

TESTS = [
    Case("HR-01a", GROUP, "1 vrijheidsgraad, modale demping 0,05 (GENE)",
         "harmonic_3d", build_sdof(),
         _sdof_checks(ZETA, "zeta = 0,05 (modal_damping)", n_freq=32),
         settings=dict(SDOF_RANGE, modal_damping=ZETA,
                       fields=["displacements", "accelerations"]),
         timeout=300,
         note="Veer 1000 N/m, mass2 2 kg (f_n = 3,559 Hz), F0 = 10 N; 0,5 "
              ".. 7 Hz (27) + 5 rond de resonantie."),
    Case("HR-01b", GROUP, "1 vrijheidsgraad, Rayleigh alpha (GENE)",
         "harmonic_3d", build_sdof(alpha=ALPHA1),
         _sdof_checks(ZETA, "zeta = alpha / (2 w_n) = 0,05 (C = alpha M, "
                      "viskeus)"),
         settings=dict(SDOF_RANGE, fields=["displacements",
                                           "accelerations"]),
         timeout=300, note="Als HR-01a met Rayleigh alpha = 2,236 1/s."),
    Case("HR-01c", GROUP, "1 vrijheidsgraad, Rayleigh alpha (PHYS, direct)",
         "harmonic_3d", build_sdof(alpha=ALPHA1),
         _sdof_checks(ZETA, "zeta = alpha / (2 w_n) = 0,05 (C = alpha M)"),
         settings=dict(SDOF_RANGE, harm_basis="PHYS",
                       fields=["displacements", "accelerations"]),
         timeout=300, note="Als HR-01b, direct (harm_basis PHYS)."),
]

# Demper (Mecway Damper, line2) alleen direct; zeta = 0,2 en een lijst
# (geen verfijning: de demping van een demper is geen modale demping).
ZETA_D = 0.2
C_D = 2.0 * ZETA_D * math.sqrt(K1 * M1)
TESTS.append(Case(
    "HR-01d", GROUP, "1 vrijheidsgraad, demper zeta = 0,2 (PHYS)",
    "harmonic_3d", build_sdof(c=C_D),
    _sdof_checks(ZETA_D, "zeta = c / (2 sqrt(k m)) = 0,2 (Mecway Damper)",
                 peak=False),
    settings={"harm_basis": "PHYS", "fields": ["displacements"],
              "harm_freq_list": "0.5, 1, 2, 3, %r, 4, 5, 7" % FN1},
    timeout=300, note="Damper %.4g N.s/m (line2), frequentielijst met f_n."
                      % C_D))


# ------------------------------------------------------------------
# HR-04 Fase (#ASTER-FASE) en een amplitude die met de frequentie
# verandert (Mecway-tabel, kolom 'time' = Hz); meetpunt-CSV.
# ------------------------------------------------------------------
TAB = [(0.0, 10.0), (10.0, 30.0)]          # F(f) = 10 + 2 f [N]
PHASE = 90.0
HR04_F = (1.0, 2.0, 3.0, FN1, 5.0)


def _tab_force():
    return "".join('<x time="%r s">%r N</x>' % p for p in TAB)


def _hr04(f):
    fa = TAB[0][1] + (TAB[1][1] - TAB[0][1]) * f / TAB[1][0]
    return sdof(f, ZETA, fa / K1) * cmath.exp(1j * math.radians(PHASE))


def _probe(r, name, f, col):
    """Waarde uit de meetpunt-CSV (aster_harmonic_export) van deze run."""
    path = r.mess[:-len(".mess")] + "_meetpunten.csv"
    rows = list(csv.reader(io.open(path, encoding="utf-8")))
    head = rows[0]
    for row in rows[1:]:
        if row[0] == name and abs(float(row[1]) - f) < 1e-6 * max(f, 1.0):
            return float(row[head.index(col)])
    raise KeyError((name, f))


TESTS.append(Case(
    "HR-04", GROUP, "Fase 90 graden (#ASTER-FASE), amplitude uit een tabel, "
    "meetpunt", "harmonic_3d",
    build_sdof(force=_tab_force(), extra=(
        "<ccxmodeldefinition>** ASTER-FASE Last = 90\n"
        "** ASTER-OPTIE harm_freq_list = %s</ccxmodeldefinition>"
        % ", ".join("%r" % f for f in HR04_F),)),
    [Check("|U| (max. rel. afwijking)",
           lambda r: _max_amp_dev(r, _hr04), ref=0.0, tol_abs=0.01,
           unit="-", source="F(f) = 10 + 2 f N (tabel), |U| = F(f)/k / "
           "sqrt((1 - r^2)^2 + (2 zeta r)^2)"),
     Check("fase (max. afwijking)", lambda r: _max_phase_dev(r, _hr04),
           ref=0.0, tol_abs=1.0, unit="graden",
           source="arg U = 90 - atan2(2 zeta r, 1 - r^2)"),
     Check("meetpunt-CSV: |u| bij 3 Hz", lambda r: _probe(
         r, "MEETPUNT_Massa", 3.0, "u_amp_m"), ref=abs(_hr04(3.0)),
         tol=0.001, unit="m", source="CSV = knoopwaarde (1 knoop)"),
     Check("meetpunt-CSV: fase x bij 3 Hz", lambda r: _probe(
         r, "MEETPUNT_Massa", 3.0,
         "ux_fase_graden"), ref=math.degrees(cmath.phase(_hr04(3.0))),
         tol_abs=0.1, unit="graden", source="idem"),
     ],
    settings={"modal_damping": ZETA, "fields": ["displacements"]},
    timeout=300,
    note="Als HR-01a; last met tabel F(f) en #ASTER-FASE Last = 90; "
         "frequenties met #ASTER-OPTIE."))

# HR-05 Twee lasten in tegenfase op dezelfde knoop (10 N fase 0 en 4 N fase
# 180 graden): netto 6 N (superpositie van de excitaties met fase).
HR05_F = (1.0, 3.0, FN1, 5.0)
TESTS.append(Case(
    "HR-05", GROUP, "Twee lasten in tegenfase (#ASTER-FASE Last2 = 180)",
    "harmonic_3d",
    build_sdof(extra=(
        '<nodeselection name="Last2">\n    <node nid="2" />\n'
        '  </nodeselection>',
        '<force selection="Last2"><x>4 N</x><y>0 N</y><z>0 N</z></force>',
        "<ccxmodeldefinition>** ASTER-FASE Last2 = 180\n"
        "** ASTER-OPTIE harm_freq_list = %s</ccxmodeldefinition>"
        % ", ".join("%r" % f for f in HR05_F),)),
    [Check("|U| (max. rel. afwijking)", lambda r: _max_amp_dev(
        r, lambda f: sdof(f, ZETA, 6.0 / K1)), ref=0.0, tol_abs=0.01,
        unit="-", source="(10 - 4) N / k / sqrt((1 - r^2)^2 + (2 zeta "
        "r)^2)"),
     Check("fase (max. afwijking)", lambda r: _max_phase_dev(
         r, lambda f: sdof(f, ZETA, 6.0 / K1)), ref=0.0, tol_abs=1.0,
         unit="graden", source="arg U = -atan2(2 zeta r, 1 - r^2)")],
    settings={"modal_damping": ZETA, "fields": ["displacements"]},
    timeout=300, note="Als HR-01a met een tweede kracht 4 N op dezelfde "
                      "knoop, fase 180 graden."))


# ------------------------------------------------------------------
# HR-02 Uitkragende balk (20 x line2 POU_D_E, RectBar 20 x 30 mm, staal),
# harmonische tipkracht 100 N in Y, Rayleigh alpha (zeta = 0,02 in mode 1):
# GENE (8 modes, waarvan 4 in het Y-vlak) en PHYS tegen de exacte
# Euler-Bernoulli-receptantie; GENE tegen PHYS.
# ------------------------------------------------------------------
E = 210e9
RHO = 7850.0
L = 1.0
BH, BB = 0.02, 0.03                     # recta (Y), rectb (Z)
A_B = BH * BB
IZ = BB * BH ** 3 / 12.0                # buiging in Y
EI = E * IZ
RHOA = RHO * A_B
F_B = 100.0
LAMBDA = (1.87510407, 4.69409113, 7.85475744)
F_BEAM = [lam ** 2 / (2 * math.pi) * math.sqrt(EI / (RHOA * L ** 4))
          for lam in LAMBDA]
ALPHA_B = 2.0 * 0.02 * 2 * math.pi * F_BEAM[0]
TIP = (L, 0.0, 0.0)
U_ST_B = F_B * L ** 3 / (3.0 * EI)
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
DENS = u'<density type="Simple" density="7850 kg/m³" />'


def beam_tip(f, alpha=ALPHA_B, eta=0.0):
    """Exacte tipverplaatsing (complex) van de Euler-Bernoulli-console met
    C = alpha M en verliesfactor eta (E (1 + i eta)) onder F_B e^(i w t)
    aan de tip (zie de kop)."""
    w = 2 * math.pi * f
    b = (RHOA * complex(w * w, -alpha * w) / (EI * complex(1.0, eta))) \
        ** 0.25
    x = b * L
    num = cmath.sin(x) * cmath.cosh(x) - cmath.cos(x) * cmath.sinh(x)
    den = EI * complex(1.0, eta) * b ** 3 * (1.0 + cmath.cos(x) *
        cmath.cosh(x))
    return F_B * num / den


def build_beam(maxmode=8, alpha=ALPHA_B, extra=()):
    def build():
        m = Model("V30", attrs={"maxmode": maxmode})
        m.elset("Balk", "Staal")
        _e, nids = linemesh(m, "Balk", 20, (0, 0, 0), (L, 0, 0))
        m.mat("Staal", '<geometric type="RectBar" recta="%r m" rectb="%r m" '
              '/>' % (BH, BB), STEEL, DENS)
        m.node_selection("Inklemming", [nids[0]])
        m.node_selection("Tip", [nids[-1]])
        m.node_selection("PROBE_Tip", [nids[-1]])
        m.add('<fixed selection="Inklemming" />')
        m.add('<force selection="Tip"><x>0 N</x><y>%r N</y><z>0 N</z>'
              '</force>' % F_B)
        if alpha:
            m.add('<rayleighdamping selection=""><alpha>%r rad/s</alpha>'
                  '<beta>0 s</beta></rayleighdamping>' % alpha)
        for x in extra:
            m.add(x)
        return m
    return build


BEAM_RANGE = {"harm_freq_start": 1.0, "harm_freq_end": 200.0,
              "harm_freq_count": 100, "fields": ["displacements"]}


def tip_u(r, f_step, point=TIP, comp="y"):
    nid = r.nearest(point)
    return complex(f_step[1]["displ" + comp][nid],
                   f_step[1]["displi" + comp][nid])


def _beam_dev(r, ref, fmax=None):
    """max |U - U_ref| / |U_ref| in de tip over de frequenties <= fmax."""
    return max(abs(tip_u(r, s) - ref(s[0])) / abs(ref(s[0]))
               for s in _steps(r) if not fmax or s[0] <= fmax)


def _beam_phase(r, ref, fmax=None):
    """max |arg U - arg U_ref| [graden] in de tip."""
    out = 0.0
    for s in _steps(r):
        if fmax and s[0] > fmax:
            continue
        d = math.degrees(cmath.phase(tip_u(r, s)) - cmath.phase(ref(s[0])))
        out = max(out, abs((d + 180.0) % 360.0 - 180.0))
    return out


def _band_dev(r, ref, bands):
    """Als _beam_dev, alleen in de frequentiebanden [(f0, f1)]."""
    return max(abs(tip_u(r, s) - ref(s[0])) / abs(ref(s[0]))
               for s in _steps(r) if any(a <= s[0] <= b for a, b in bands))


# Directe berekening (PHYS) als referentie voor GENE: Code-Aster 17.4, deze
# bridge (HR-02b en HR-03b, 7 okt 2026); single precision (7 cijfers).
# HR-02: elke derde frequentie van HR-02b.
PHYS_REF = {
    # HR-02b: f -> tip disply + i displiy [m]
    'HR-02': [
        (1.0, 0.00796417, -1.858584e-05),
        (7.03030303030303, 0.009590369, -0.0001914145),
        (13.0606060606061, 0.01990704, -0.001580639),
        (16.5366108502673, 0.08012176, -0.1528783),
        (17.0377202435396, -0.09416672, -0.09730625),
        (21.1010101010101, -0.01262371, -0.001093221),
        (24.893969083313, -0.006058591, -0.0003083842),
        (25.2281163017603, -0.005763688, -0.0002839835),
        (29.1414141414141, -0.003520343, -0.0001292401),
        (35.1717171717172, -0.001986622, -5.563447e-05),
        (41.2020202020202, -0.001246993, -3.013594e-05),
        (47.2323232323232, -0.0008185097, -1.872591e-05),
        (53.2626262626263, -0.0005389148, -1.287569e-05),
        (59.2929292929293, -0.0003382571, -9.687383e-06),
        (65.3232323232323, -0.0001804038, -8.013137e-06),
        (71.3535353535353, -4.271133e-05, -7.419031e-06),
        (77.3838383838384, 9.377065e-05, -7.92117e-06),
        (83.4141414141414, 0.0002532844, -1.017132e-05),
        (89.4444444444444, 0.0004855304, -1.678961e-05),
        (95.4747474747475, 0.0009568469, -4.179155e-05),
        (101.505050505051, 0.003034486, -0.0003296467),
        (104.553913840087, 0.01220404, -0.0245562),
        (105.055218691661, -0.01547695, -0.01539234),
        (109.545454545455, -0.002213808, -0.000147912),
        (115.575757575758, -0.001021838, -3.004303e-05),
        (121.606060606061, -0.0006689309, -1.283622e-05),
        (127.636363636364, -0.0004955599, -7.228116e-06),
        (133.666666666667, -0.0003905534, -4.70124e-06),
        (139.69696969697, -0.0003191487, -3.339121e-06),
        (145.727272727273, -0.0002668949, -2.516213e-06),
        (151.757575757576, -0.0002266645, -1.978604e-06),
        (156.748206880513, -0.0001995947, -1.66244e-06),
        (157.249514568639, -0.0001971216, -1.635358e-06),
        (159.79797979798, -0.0001851469, -1.50847e-06),
        (165.828282828283, -0.0001602186, -1.266899e-06),
        (171.858585858586, -0.000139067, -1.086083e-06),
        (177.888888888889, -0.0001207698, -9.481424e-07),
        (183.919191919192, -0.0001046634, -8.417246e-07),
        (189.949494949495, -9.025063e-05, -7.594205e-07),
        (195.979797979798, -7.714346e-05, -6.963405e-07),
    ],
    # HR-03b: f -> tip displz, displiz [m], vonmises in HEX_ROOT,
    # stressampxx in HEX_MID [Pa]
    'HR-03': [
        (1.0, 0.001495854, -9.403838e-07, 2.306095e+07, 1.200405e+07),
        (6.06779661016949, 0.001525552, -5.93503e-06, 2.357633e+07, 1.219597e+07),
        (11.135593220339, 0.001603169, -1.203042e-05, 2.492371e+07, 1.269737e+07),
        (16.2033898305085, 0.001744729, -2.074481e-05, 2.738228e+07, 1.361112e+07),
        (21.271186440678, 0.001986363, -3.534704e-05, 3.158209e+07, 1.516933e+07),
        (26.3389830508475, 0.00241387, -6.482219e-05, 3.902076e+07, 1.792368e+07),
        (31.4067796610169, 0.003275515, -0.0001431358, 5.404272e+07, 2.347419e+07),
        (36.4745762711864, 0.00567224, -0.0005052482, 9.608049e+07, 3.897473e+07),
        (41.5423728813559, 0.02676766, -0.02015149, 5.806279e+08, 2.168463e+08),
        (41.7116300940163, 0.02772129, -0.02713436, 6.728723e+08, 2.505357e+08),
        (41.9923837878436, 0.02242853, -0.04346796, 8.498028e+08, 3.148129e+08),
        (42.273137481671, 0.0007706509, -0.05461964, 9.505592e+08, 3.503389e+08),
        (42.5538911754983, -0.02126442, -0.04393239, 8.507047e+08, 3.119178e+08),
        (42.8346448693256, -0.0269055, -0.02749735, 6.7162e+08, 2.449706e+08),
        (46.6101694915254, -0.006572002, -0.0009015205, 1.184834e+08, 4.006348e+07),
        (51.6779661016949, -0.002879475, -0.0001938174, 5.331316e+07, 1.599259e+07),
        (56.7457627118644, -0.001761364, -8.211728e-05, 3.380634e+07, 8766843),
        (61.8135593220339, -0.001228014, -4.539525e-05, 2.45378e+07, 5313526),
        (66.8813559322034, -0.0009185381, -2.907253e-05, 1.917983e+07, 3299168),
        (71.9491525423729, -0.0007179157, -2.051428e-05, 1.572298e+07, 1983874),
        (77.0169491525424, -0.0005781809, -1.554502e-05, 1.333062e+07, 1063361),
        (81.3904683897369, -0.0004881688, -1.280788e-05, 1.18017e+07, 486754.2),
        (82.0847457627119, -0.0004758106, -1.246247e-05, 1.159289e+07, 414701),
        (82.4887074733182, -0.0004688297, -1.227073e-05, 1.147508e+07, 376286.2),
        (83.5869465568995, -0.0004505879, -1.178143e-05, 1.116776e+07, 289640.3),
        (84.6851856404809, -0.0004333562, -1.133515e-05, 1.087822e+07, 242023.3),
        (85.7834247240622, -0.0004170559, -1.092765e-05, 1.06051e+07, 247333.8),
        (87.1525423728814, -0.0003979331, -1.046836e-05, 1.028576e+07, 312705.5),
        (92.2203389830509, -0.000336923, -9.148926e-06, 9276669, 684472.9),
        (97.2881355932203, -0.0002879822, -8.273128e-06, 8482390, 1034946),
        (102.35593220339, -0.0002479448, -7.704482e-06, 7848150, 1341294),
        (107.423728813559, -0.0002146396, -7.358924e-06, 7336557, 1612155),
        (112.491525423729, -0.0001865296, -7.183159e-06, 6921322, 1856264),
        (117.559322033898, -0.0001624968, -7.14292e-06, 6583512, 2080685),
        (122.627118644068, -0.0001417087, -7.216296e-06, 6309245, 2291036),
        (127.694915254237, -0.0001235328, -7.389815e-06, 6088204, 2491866),
        (132.762711864407, -0.000107479, -7.656127e-06, 5912662, 2686965),
        (137.830508474576, -9.316166e-05, -8.012624e-06, 5776824, 2879604),
        (142.898305084746, -8.027181e-05, -8.460685e-06, 5676377, 3072711),
        (147.966101694915, -6.855818e-05, -9.005349e-06, 5608188, 3269023),
        (153.033898305085, -5.781309e-05, -9.655323e-06, 5570086, 3471199),
        (158.101694915254, -4.786193e-05, -1.042328e-05, 5560725, 3681933),
        (163.169491525424, -3.855525e-05, -1.13265e-05, 5579502, 3904054),
        (168.237288135593, -2.976266e-05, -1.238777e-05, 5626512, 4140638),
        (173.305084745763, -2.136792e-05, -1.363691e-05, 5702550, 4395122),
        (178.372881355932, -1.326511e-05, -1.511269e-05, 5809148, 4671444),
        (183.440677966102, -5.355552e-06, -1.686573e-05, 5948651, 4974219),
        (188.508474576271, 2.45464e-06, -1.896255e-05, 6124344, 5308940),
        (193.576271186441, 1.025608e-05, -2.149127e-05, 6340630, 5682248),
        (198.64406779661, 1.813646e-05, -2.456988e-05, 6603270, 6102278),
        (203.71186440678, 2.617879e-05, -2.835802e-05, 6919708, 6579089),
        (208.779661016949, 3.445568e-05, -3.307414e-05, 7299472, 7125202),
        (213.847457627119, 4.301588e-05, -3.901999e-05, 7754640, 7756242),
        (218.915254237288, 5.185583e-05, -4.661498e-05, 8300296, 8491582),
        (223.983050847458, 6.086169e-05, -5.644122e-05, 8954723, 9354748),
        (229.050847457627, 6.969455e-05, -6.929274e-05, 9738681, 1.037282e+07),
        (234.118644067797, 7.757109e-05, -8.61972e-05, 1.067219e+07, 1.157298e+07),
        (239.186440677966, 8.287625e-05, -0.0001083061, 1.176527e+07, 1.297207e+07),
        (239.495567061719, 8.305893e-05, -0.0001098454, 1.18369e+07, 1.306375e+07),
        (244.254237288136, 8.260203e-05, -0.0001363839, 1.299612e+07, 1.45511e+07),
        (249.322033898305, 7.197933e-05, -0.0001693979, 1.426926e+07, 1.62051e+07),
        (250.274046571724, 6.836874e-05, -0.0001758158, 1.44976e+07, 1.650635e+07),
        (254.389830508475, 4.571043e-05, -0.0002020345, 1.536405e+07, 1.767865e+07),
        (259.457627118644, 2.831682e-06, -0.0002235244, 1.59442e+07, 1.856918e+07),
        (261.052526081728, -1.292988e-05, -0.0002260875, 1.596962e+07, 1.866585e+07),
        (264.525423728814, -4.759713e-05, -0.000223378, 1.573554e+07, 1.853098e+07),
        (269.593220338983, -9.044776e-05, -0.000201695, 1.476991e+07, 1.757213e+07),
        (271.831005591733, -0.0001042426, -0.0001878912, 1.418081e+07, 1.694273e+07),
        (274.661016949153, -0.0001168193, -0.0001690514, 1.336377e+07, 1.604838e+07),
        (279.728813559322, -0.0001277955, -0.0001361536, 1.185819e+07, 1.436222e+07),
        (282.609485101738, -0.0001291989, -0.0001195443, 1.104209e+07, 1.343406e+07),
        (284.796610169492, -0.0001286964, -0.000108232, 1.045768e+07, 1.276449e+07),
        (289.864406779661, -0.0001242733, -8.62755e-05, 9238469, 1.13557e+07),
        (294.932203389831, -0.0001175173, -6.950628e-05, 8207069, 1.015184e+07),
        (300.0, -0.0001100373, -5.677223e-05, 7342799, 9134228),
    ],
}


def _ref_fn(key, col):
    table = dict((row[0], row) for row in PHYS_REF[key])

    def fn(f):
        for fr, row in table.items():
            if abs(fr - f) <= 1e-6 * f:
                return row
        return None
    return fn


def _vs_phys(r, key, point, comp="y"):
    """max |U - U_PHYS| / |U_PHYS| (tip, complex) over de frequenties van
    PHYS_REF[key]; elke referentiefrequentie moet in de run zitten."""
    find = _ref_fn(key, 1)
    used, out = 0, 0.0
    for s in _steps(r):
        row = find(s[0])
        if row is None:
            continue
        used += 1
        ref = complex(row[1], row[2])
        out = max(out, abs(tip_u(r, s, point, comp) - ref) / abs(ref))
    if used != len(PHYS_REF[key]):
        raise ValueError("%d van %d referentiefrequenties gevonden" % (
            used, len(PHYS_REF[key])))
    return out


def _vs_phys_col(r, key, point, var, col):
    find = _ref_fn(key, col)
    nid = r.nearest(point)
    out = 0.0
    for f, d in _steps(r):
        row = find(f)
        if row is not None:
            out = max(out, abs(d[var][nid] - row[col]) / abs(row[col]))
    return out


# Statisch deel van de weggelaten modes (5, 6, ...) van de tip-
# verplaatsing van de console: 1 - som_{i=1..4} 12 / lambda_i^4 (bijdrage
# van mode i aan P L^3 / 3EI, Blevins tabel 8-1; zoals MD-06a).
LAMBDA4 = LAMBDA + (10.99554073,)
TRUNC4 = 1.0 - sum(12.0 / lam ** 4 for lam in LAMBDA4)

_EB_SRC = ("exacte Euler-Bernoulli-receptantie met C = alpha M (kop; "
           "Bishop & Johnson 1960)")
TESTS += [
    Case("HR-02a", GROUP, "Console (balk), harmonische tipkracht, GENE 8 "
         "modes + statische verrijking", "harmonic_3d", build_beam(),
         [Check("tip t.o.v. Euler-Bernoulli, 1 .. 200 Hz (max. |U - U_ex| "
                "/ |U_ex|)", lambda r: _beam_dev(r, beam_tip), ref=0.0,
                tol_abs=0.01, unit="-", source=_EB_SRC),
          Check("fase t.o.v. Euler-Bernoulli (max. afwijking)",
                lambda r: _beam_phase(r, beam_tip), ref=0.0, tol_abs=1.0,
                unit="graden", source=_EB_SRC),
          Check("GENE t.o.v. PHYS (HR-02b), tip complex", lambda r: _vs_phys(
              r, "HR-02", TIP), ref=0.0, tol_abs=0.01, unit="-",
              source="directe berekening op hetzelfde model (PHYS_REF)",
              in_series=False)],
         settings=BEAM_RANGE, timeout=300,
         note="20 x line2 POU_D_E, RectBar 20 x 30 mm, 100 N in Y op de "
              "tip, alpha = %.4g 1/s (zeta 0,02 in mode 1, %.4g Hz); 1 .. "
              "200 Hz (100) + 5 per mode; modes in Y: 16,7 / 104,7 / 293 / "
              "575 Hz." % (ALPHA_B, F_BEAM[0])),
    Case("HR-02b", GROUP, "Console (balk), harmonische tipkracht, PHYS "
         "(direct)", "harmonic_3d", build_beam(),
         [Check("tip t.o.v. Euler-Bernoulli, 1 .. 200 Hz (max. |U - U_ex| "
                "/ |U_ex|)", lambda r: _beam_dev(r, beam_tip), ref=0.0,
                tol_abs=0.01, unit="-", source=_EB_SRC),
          Check("fase t.o.v. Euler-Bernoulli (max. afwijking)",
                lambda r: _beam_phase(r, beam_tip), ref=0.0, tol_abs=1.0,
                unit="graden", source=_EB_SRC)],
         settings=dict(BEAM_RANGE, harm_basis="PHYS"), timeout=300,
         note="Als HR-02a, harm_basis PHYS (C = alpha M)."),
    Case("HR-02c", GROUP, "Console (balk), GENE 8 modes zonder statische "
         "verrijking (modale truncatie)", "harmonic_3d", build_beam(),
         [Check("statisch deel weggelaten modes bij 1 Hz: (|U_ex| - |U|) / "
                "u_st", lambda r: (abs(beam_tip(1.0)) - abs(tip_u(r, min(
                    _steps(r), key=lambda s: abs(s[0] - 1.0))))) / U_ST_B,
                ref=TRUNC4, tol=0.02, unit="-",
                source="1 - som_{i<=4} 12 / lambda_i^4 = %.4g (4 modes in "
                       "Y; Blevins tabel 8-1)" % TRUNC4),
          Check("tip t.o.v. Euler-Bernoulli, 1 .. 45 Hz", lambda r:
                _beam_dev(r, beam_tip, fmax=45.0), ref=0.0, tol_abs=0.01,
                unit="-", source=_EB_SRC + "; onder de antiresonantie "
                "(73 Hz)"),
          Check("tip t.o.v. Euler-Bernoulli rond mode 2 (95 .. 115 Hz)",
                lambda r: _band_dev(r, beam_tip, [(95.0, 115.0)]),
                ref=0.0, tol_abs=0.01, unit="-", source=_EB_SRC)],
         settings=dict(BEAM_RANGE, static_correction=False), timeout=300,
         note="Als HR-02a, static_correction uit: alleen de 8 modes."),
]


# ------------------------------------------------------------------
# HR-03 Hex20-console 1 x 0,1 x 0,05 m (10 x 2 x 1, zoals MD-05), kracht
# 1000 N in Z op het eindvlak, Rayleigh beta = 1e-4 s, 6 modes: GENE tegen
# PHYS (verplaatsing en spanning).
# ------------------------------------------------------------------
HEX_TIP = (L, 0.05, 0.025)
HEX_MID = (0.5, 0.05, 0.05)
HEX_ROOT = (0.1, 0.05, 0.05)
F1_HEX = 42.2805978697951               # CALC_MODES, mode 1 (= MD-05)
XI1_HEX = 1e-4 * 2 * math.pi * F1_HEX / 2.0


def build_hex():
    m = Model("V30", attrs={"maxmode": 6})
    m.elset("Balk", "Staal")
    msh = hexmesh(m, "Balk", 10, 2, 1, box(0, L, 0, 0.1, 0, 0.05), order=2)
    m.mat("Staal", STEEL, DENS)
    m.face_selection("Inklemming", msh["faces"]["u0"])
    m.face_selection("Eindvlak", msh["faces"]["u1"])
    m.add('<fixed selection="Inklemming" />')
    m.add('<force selection="Eindvlak"><x>0 N</x><y>0 N</y><z>1000 N</z>'
          '</force>')
    m.add('<rayleighdamping selection=""><alpha>0 rad/s</alpha>'
          '<beta>0.0001 s</beta></rayleighdamping>')
    return m


HEX_RANGE = {"harm_freq_start": 1.0, "harm_freq_end": 300.0,
             "harm_freq_count": 60,
             "fields": ["displacements", "stresses", "vonmises"]}


def _hex_peak(r):
    nid = r.nearest(HEX_TIP)
    return max((d["displampz"][nid], f) for f, d in _steps(r))[1]


TESTS += [
    Case("HR-03a", GROUP, "Hex20-console, GENE 6 modes + statische "
         "verrijking", "harmonic_3d", build_hex,
         [Check("GENE t.o.v. PHYS: tip U_z (complex)", lambda r: _vs_phys(
             r, "HR-03", HEX_TIP, "z"), ref=0.0, tol_abs=0.01, unit="-",
             source="directe berekening (HR-03b, PHYS_REF)", in_series=False),
          Check("GENE t.o.v. PHYS: von Mises (max. over de periode) bij de "
                "inklemming", lambda r: _vs_phys_col(
                    r, "HR-03", HEX_ROOT, "vonmises", 3), ref=0.0,
                tol_abs=0.01, unit="-", source="idem", in_series=False),
          Check("GENE t.o.v. PHYS: |sigma_xx| halverwege", lambda r:
                _vs_phys_col(r, "HR-03", HEX_MID, "stressampxx", 4),
                ref=0.0, tol_abs=0.01, unit="-", source="idem",
                in_series=False)],
         settings=HEX_RANGE, timeout=600,
         note="10 x 2 x 1 hex20, 1000 N in Z op het eindvlak, beta = 1e-4 "
              "s; 1 .. 300 Hz (60) + 5 per mode; modes in Z: 42,3 / 262,9 "
              "Hz."),
    Case("HR-03b", GROUP, "Hex20-console, PHYS (direct)", "harmonic_3d",
         build_hex,
         [Check("frequentie van de piek (mode 1)", _hex_peak,
                ref=F1_HEX * math.sqrt(1 - 2 * XI1_HEX ** 2), tol=0.001,
                unit="Hz", source="f_1 sqrt(1 - 2 xi_1^2), xi_1 = beta w_1 "
                "/ 2 = %.4g (f_1 uit CALC_MODES; verfijning LARGEUR_3DB)"
                % XI1_HEX)],
         settings=dict(HEX_RANGE, harm_basis="PHYS"), timeout=600,
         note="Als HR-03a, harm_basis PHYS (C = beta K)."),
]


# ------------------------------------------------------------------
# HR-06 Hysteretische (structurele) demping, verliesfactor eta (S26):
# stijfheid K (1 + i eta) via AMOR_HYST (DEFI_MATERIAU ELAS en
# AFFE_CARA_ELEM DISCRET) en RIGI_MECA_HYST.
#   1 vrijheidsgraad: U = u_st / ((1 - r^2) + i eta) (Aubry, Beginning
#   DYNAmics with code_aster, 2023, par. 3.3.4; Clough & Penzien 1993 par.
#   3-7), piek precies bij f_n: |U| = u_st / eta, fase -90 graden.
#   Console: de Euler-Bernoulli-receptantie met E (1 + i eta).
# ------------------------------------------------------------------
ETA = 0.04
ETA_B = 0.02


def sdof_hyst(f, eta=ETA, ust=U_ST):
    r = f / FN1
    return ust / complex(1.0 - r * r, eta)


def _hyst_checks(src, at_fn=False):
    out = [
        Check("|U| over alle frequenties (max. rel. afwijking)",
              lambda r: _max_amp_dev(r, sdof_hyst), ref=0.0, tol_abs=0.01,
              unit="-", source="|U| = u_st / sqrt((1 - r^2)^2 + eta^2), %s"
              % src),
        Check("fase over alle frequenties (max. afwijking)",
              lambda r: _max_phase_dev(r, sdof_hyst), ref=0.0, tol_abs=1.0,
              unit="graden", source="arg U = -atan2(eta, 1 - r^2)"),
        Check("piekamplitude", lambda r: _peak(r)[0], ref=U_ST / ETA,
              tol=0.02, unit="m", source="u_st / eta (piek bij f_n)"),
    ]
    if at_fn:
        out.append(Check(
            "|U(f_n)| = u_st / eta", lambda r: d_at(r, FN1, "displampx"),
            ref=U_ST / ETA, tol=0.001, unit="m",
            source="r = 1: U = u_st / (i eta)"))
        out.append(Check(
            "fase bij f_n", lambda r: d_at(r, FN1, "displphasex"),
            ref=-90.0, tol_abs=0.1, unit="graden", source="arg 1/(i eta)"))
    return out


def d_at(r, f0, var, point=MASS_X):
    nid = _node(r, point)
    f, d = min(_steps(r), key=lambda s: abs(s[0] - f0))
    return d[var][nid]


_HYST_LIST = "0.5, 1, 2, 3, 3.4, %r, 3.7, 4, 5, 7" % FN1
TESTS += [
    Case("HR-06a", GROUP, "1 vrijheidsgraad, verliesfactor eta = 0,04 "
         "(loss_factor, GENE)", "harmonic_3d", build_sdof(),
         _hyst_checks("eta = 0,04 (veer, AFFE_CARA_ELEM AMOR_HYST)"),
         settings=dict(SDOF_RANGE, loss_factor=ETA,
                       fields=["displacements"]),
         timeout=300, note="Als HR-01a zonder viskeuze demping, met "
         "loss_factor 0,04 (K (1 + i eta), RIGI_MECA_HYST); verfijning "
         "met xi = eta / 2."),
    Case("HR-06b", GROUP, "1 vrijheidsgraad, #ASTER-HYST Veer = 0,04 "
         "(PHYS, lijst met f_n)", "harmonic_3d", build_sdof(extra=(
             "<ccxmodeldefinition>** ASTER-HYST Veer = %r"
             "</ccxmodeldefinition>" % ETA,)),
         _hyst_checks("eta = 0,04 (#ASTER-HYST)", at_fn=True),
         settings={"harm_basis": "PHYS", "fields": ["displacements"],
                   "harm_freq_list": _HYST_LIST},
         timeout=300, note="Verliesfactor per materiaal (#ASTER-HYST), "
         "direct; frequentielijst met f_n."),
]
_EB_HYST = ("exacte Euler-Bernoulli-receptantie met E (1 + i eta), eta = "
            "0,02 (kop; Bishop & Johnson 1960)")
TESTS += [
    Case("HR-06c", GROUP, "Console (balk), verliesfactor eta = 0,02, GENE "
         "8 modes + statische verrijking", "harmonic_3d",
         build_beam(alpha=0.0),
         [Check("tip t.o.v. Euler-Bernoulli, 1 .. 200 Hz (max. |U - U_ex| "
                "/ |U_ex|)", lambda r: _beam_dev(
                    r, lambda f: beam_tip(f, 0.0, ETA_B)), ref=0.0,
                tol_abs=0.01, unit="-", source=_EB_HYST),
          Check("fase t.o.v. Euler-Bernoulli (max. afwijking)",
                lambda r: _beam_phase(r, lambda f: beam_tip(f, 0.0, ETA_B)),
                ref=0.0, tol_abs=1.0, unit="graden", source=_EB_HYST),
          Check("tip bij f_1: |U| eta / (12 / lambda_1^4 u_st)", lambda r:
                max(abs(tip_u(r, s)) for s in _steps(r)) * ETA_B /
                (12.0 / LAMBDA[0] ** 4 * U_ST_B), ref=1.0, tol=0.02,
                unit="-", source="mode 1 neemt 12 / lambda_1^4 = 0,971 van "
                "u_st; in resonantie die / eta (Blevins tabel 8-1)")],
         settings=dict(BEAM_RANGE, loss_factor=ETA_B), timeout=300,
         note="Als HR-02a zonder Rayleigh, loss_factor 0,02 (PROJ_BASE "
              "van RIGI_MECA_HYST, STOCKAGE PLEIN)."),
    Case("HR-06d", GROUP, "Console (balk), #ASTER-HYST Staal = 0,02, PHYS "
         "(direct)", "harmonic_3d", build_beam(alpha=0.0, extra=(
             "<ccxmodeldefinition>** ASTER-HYST Staal = %r"
             "</ccxmodeldefinition>" % ETA_B,)),
         [Check("tip t.o.v. Euler-Bernoulli, 1 .. 200 Hz (max. |U - U_ex| "
                "/ |U_ex|)", lambda r: _beam_dev(
                    r, lambda f: beam_tip(f, 0.0, ETA_B)), ref=0.0,
                tol_abs=0.01, unit="-", source=_EB_HYST),
          Check("fase t.o.v. Euler-Bernoulli (max. afwijking)",
                lambda r: _beam_phase(r, lambda f: beam_tip(f, 0.0, ETA_B)),
                ref=0.0, tol_abs=1.0, unit="graden", source=_EB_HYST)],
         settings=dict(BEAM_RANGE, harm_basis="PHYS"), timeout=300,
         note="Als HR-06c, verliesfactor per materiaal, harm_basis PHYS."),
]
