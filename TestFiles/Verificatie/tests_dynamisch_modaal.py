# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Respons op modale basis (Mecway Dynamic Response D30 met Mode
superposition -> CALC_MODES + PROJ_BASE + DYNA_VIBRA GENE + REST_GENE_PHYS,
bridge-analyse dyna_modal_3d; Scripts/bridge_dyna_modal.py). Toelichting:
docs/Verificatie.md par. 7 (MD).

Referenties:
  - analytisch: 1-vrijheidsgraadsysteem (massa op het uiteinde van een
    ingeklemde balk met verwaarloosbare eigen massa, k = 3 E I / L^3) onder
    een staplast en een harmonische last, met en zonder demping: de exacte
    oplossing (Duhamel-integraal in gesloten vorm; Clough & Penzien,
    Dynamics of Structures, 2e druk 1993, hoofdstuk 3 en 4); de
    Euler-Bernoulli-console met de modale bijdrage 12 / lambda_i^4 van mode
    i aan de statische tipverplaatsing (modes genormeerd op int phi^2 dx = L,
    phi_i(L) = 2; Blevins 1979, tabel 8-1; zelfde reeks als DY-02);
  - Mecway 33 headless (TestFiles/Tools/mw_solve.py, interne solver, Mode
    superposition) op dezelfde .liml (modellen/MD-*.liml): waarden in
    MECWAY hieronder (elke n-de uitvoertijd).
"""
import math
from verif_lib import Case, Check, Model, linemesh, hexmesh, box
from tests_dynamisch import period, peak, sdof_response

GROUP = "Respons op modale basis"

E = 210e9
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
RECT = '<geometric type="RectBar" recta="0.02 m" rectb="0.03 m" />'
L = 1.0
IZ = 0.03 * 0.02 ** 3 / 12.0           # buiging in Y (recta in Y)

# Massa op een balk: k = 3 E I / L^3, tipmassa 10 kg, balk 1 kg/m3
# (eigen massa 6e-4 kg: verwaarloosbaar)
K_TIP = 3.0 * E * IZ / L ** 3           # 12 600 N/m
M_TIP = 10.0
W_TIP = math.sqrt(K_TIP / M_TIP)        # 35,50 rad/s
T_TIP = 2.0 * math.pi / W_TIP           # 0,1770 s
F_TIP = 100.0
U_ST = F_TIP / K_TIP                    # 7,937 mm
TIP = (L, 0.0, 0.0)


def sdof_exact(t, zeta=0.0, om=None):
    """Exacte respons van u'' + 2 zeta w u' + w^2 u = w^2 U_ST g(t) uit
    rust: g = 1 (staplast) of g = sin(om t) (Clough & Penzien hfst. 3/4)."""
    w = W_TIP
    wd = w * math.sqrt(1.0 - zeta ** 2)
    if om is None:
        return U_ST * (1.0 - math.exp(-zeta * w * t) * (
            math.cos(wd * t) + zeta / math.sqrt(1.0 - zeta ** 2) *
            math.sin(wd * t)))
    r = om / w
    den = (1.0 - r * r) ** 2 + (2.0 * zeta * r) ** 2
    a = U_ST * (1.0 - r * r) / den
    b = -U_ST * 2.0 * zeta * r / den
    c = -b
    d = (zeta * w * c - a * om) / wd
    return (a * math.sin(om * t) + b * math.cos(om * t) +
            math.exp(-zeta * w * t) * (c * math.cos(wd * t) +
                                       d * math.sin(wd * t)))


def _ts(t_end, dt, keep=None):
    ts = {"timeperiod": "%r s" % t_end, "stepsize": "%r s" % dt}
    if keep:
        ts["keepeverynthtimestep"] = "%d" % keep
    return ts


def build_tipmass(t_end, dt, force, alpha=None, maxmode=3, direct=False,
                  keep=None):
    """Ingeklemde balk (10 x line2, RectBar 20 x 30 mm, 1 kg/m3) met 10 kg op
    de tip; last in Y op de tip."""
    def build():
        attrs = {"maxmode": maxmode}
        if not direct:
            attrs["modesuperposition"] = "true"
        m = Model("D30", timesteps=_ts(t_end, dt, keep), attrs=attrs)
        m.elset("Balk", "Staal")
        _e, nids = linemesh(m, "Balk", 10, (0, 0, 0), (L, 0, 0))
        m.mat("Staal", RECT, STEEL,
              u'<density type="Simple" density="1 kg/m³" />')
        m.node_selection("Inklemming", [nids[0]])
        m.node_selection("Tip", [nids[-1]])
        m.add('<fixed selection="Inklemming" />')
        m.add('<mass2 selection="Tip"><value>%r kg</value></mass2>' % M_TIP)
        m.add('<force selection="Tip"><x>0 N</x>%s<z>0 N</z></force>'
              % force)
        if alpha:
            m.add('<rayleighdamping selection=""><alpha>%r rad/s</alpha>'
                  '<beta>0 s</beta></rayleighdamping>' % alpha)
        return m
    return build


def _max_dev(hist, ref_fn, scale):
    """max |u(t) - ref(t)| / scale over alle uitvoertijden."""
    return max(abs(u - ref_fn(t)) for t, u in hist) / scale


def _mecway_dev(hist, ref):
    """max |u - u_Mecway| / max |u_Mecway| op de tijden van ref [(t, u)]."""
    out = 0.0
    scale = max(abs(u) for _t, u in ref)
    for t, u in ref:
        tb, ub = min(hist, key=lambda p: abs(p[0] - t))
        if abs(tb - t) > 1e-6 * max(1.0, abs(t)):
            raise ValueError("uitvoertijd %g ontbreekt" % t)
        out = max(out, abs(ub - u) / scale)
    return out


def _hist_check(name, var, point, ref_fn, scale, tol, source):
    return Check(name, lambda r: _max_dev(r.history(var, point), ref_fn,
                                          scale),
                 ref=0.0, tol_abs=tol, unit="-", source=source)


def _mecway_check(case_id, var, point, tol=0.02, name=None):
    return Check(name or "verloop t.o.v. Mecway (%s)" % var,
                 lambda r: _mecway_dev(r.history(var, point),
                                       MECWAY[case_id][var]),
                 ref=0.0, tol_abs=tol, unit="-",
                 source="max |u - u_Mecway| / max |u_Mecway| op %d "
                        "uitvoertijden; Mecway 33 headless (mw_solve.py), "
                        "zelfde .liml" % len(MECWAY.get(case_id, {}).get(
                            var, [])))


# Mecway 33 headless (mw_solve.py) op modellen/MD-*.liml, 7 okt 2026:
# [(t, waarde)] op elke n-de uitvoertijd en de laatste
# (verif_lib.Results(<model>_sol.liml).history(var, punt)[::n]).
MECWAY = {
    'MD-01': {
        'disply': [
            (0.0, 0.0), (0.04, 0.00674305665), (0.08, 0.0155140691),
            (0.12, 0.0114088704), (0.16, 0.0014032307), (0.2, 0.00249926067),
            (0.24, 0.0128345284), (0.28, 0.0148468019), (0.32, 0.00511671987),
            (0.36, 0.000178150913), (0.4, 0.00842297182),
            (0.44, 0.0158411481), (0.48, 0.00982732334),
            (0.52, 0.000600505784), (0.56, 0.00383939042),
            (0.6, 0.0140402937), (0.64, 0.0138693027), (0.68, 0.00361697442),
            (0.72, 0.000704605726), (0.76, 0.0100810471), (0.8, 0.0158133549),
            (0.84, 0.00816088931), (0.88, 0.000127123528),
            (0.92, 0.00536345604), (0.96, 0.0149720345), (1.0, 0.0126254556),
        ],
    },
    'MD-02': {
        'disply': [
            (0.0, 0.0), (0.04, 0.00644607973), (0.08, 0.0144000719),
            (0.12, 0.0110614543), (0.16, 0.0032141169), (0.2, 0.00388682292),
            (0.24, 0.0108860852), (0.28, 0.0122860628), (0.32, 0.00661003201),
            (0.36, 0.00378673771), (0.4, 0.0079113107), (0.44, 0.0115298282),
            (0.48, 0.00897672375), (0.52, 0.00511360919),
            (0.56, 0.00623393437), (0.6, 0.00990320989),
            (0.64, 0.00997107661), (0.68, 0.00680672423),
            (0.72, 0.0058510412), (0.76, 0.00832569199), (0.8, 0.00985620793),
            (0.84, 0.00814287698), (0.88, 0.00632938014),
            (0.92, 0.00730196573), (0.96, 0.00915105387),
            (1.0, 0.00883125056),
        ],
    },
    'MD-03': {
        'disply': [
            (0.0, 0.0), (0.04, 0.00246607282), (0.08, 0.010855105),
            (0.12, 0.00932388634), (0.16, -0.00986454474),
            (0.2, -0.0218752682), (0.24, -0.00381272635),
            (0.28, 0.0236882194), (0.32, 0.0210715704), (0.36, -0.0110584767),
            (0.4, -0.029498406), (0.44, -0.00909804204), (0.48, 0.0223904097),
            (0.52, 0.0240454422), (0.56, -0.00372392853), (0.6, -0.024234492),
            (0.64, -0.0144773036), (0.68, 0.0101057021), (0.72, 0.0205198894),
            (0.76, 0.00815864122), (0.8, -0.0112234743),
            (0.84, -0.0177742286), (0.88, -0.00589984281),
            (0.92, 0.0123317084), (0.96, 0.0180194819), (1.0, 0.00375095235),
            (1.04, -0.0161035869), (1.08, -0.0184530536),
            (1.12, 0.00131319521), (1.16, 0.0207572217), (1.2, 0.0158587143),
            (1.24, -0.00852334657), (1.28, -0.0230840665),
            (1.32, -0.00996074572), (1.36, 0.0150022758), (1.4, 0.0218511136),
            (1.44, 0.00292731096), (1.48, -0.0188694634),
            (1.52, -0.0182624403), (1.56, 0.00319395755), (1.6, 0.0203821336),
            (1.64, 0.0140677622), (1.68, -0.0080072727),
            (1.72, -0.0207427355), (1.76, -0.00990286655),
            (1.8, 0.0122130182), (1.84, 0.020515887), (1.88, 0.00532649078),
            (1.92, -0.016235236), (1.96, -0.0192844477),
            (2.0, 8.67610879e-05),
        ],
    },
    'MD-05': {
        'displz': [
            (0.0, 0.0), (0.002, 0.000269640421), (0.004, 0.000758898942),
            (0.006, 0.00152194301), (0.008, 0.0022084511),
            (0.01, 0.00273057146), (0.012, 0.00287806237),
            (0.014, 0.00266319446), (0.016, 0.00211885378),
            (0.018, 0.00141791253), (0.02, 0.000743503089),
            (0.022, 0.000285258043), (0.024, 0.000163883322),
            (0.026, 0.0004073705), (0.028, 0.000945720325),
            (0.03, 0.00162503704), (0.032, 0.00225990727),
            (0.034, 0.00267468476), (0.036, 0.00276111803),
            (0.038, 0.00249822458), (0.04, 0.0019644795),
            (0.042, 0.00130850498), (0.044, 0.000712636422),
            (0.046, 0.000338371163), (0.048, 0.000285671119),
            (0.05, 0.000564013025), (0.052, 0.00109287335),
            (0.054, 0.00172372552), (0.056, 0.00228257858),
            (0.058, 0.00261734007), (0.06, 0.00263956141),
            (0.062, 0.00234750466), (0.064, 0.00182555019),
            (0.066, 0.00121981532), (0.068, 0.00069730948),
            (0.07, 0.000399923397), (0.072, 0.000405911911),
            (0.074, 0.000709392005), (0.076, 0.0012230996),
            (0.078, 0.00180345328), (0.08, 0.00229062408),
            (0.082, 0.00255254618), (0.084, 0.0025206636),
            (0.086, 0.00220782629), (0.088, 0.00170361766),
            (0.09, 0.00114876351), (0.092, 0.000695879556),
            (0.094, 0.00046752773), (0.096, 0.000523078265),
            (0.098, 0.000843344038), (0.1, 0.00133693259),
        ],
        'velz': [
            (0.0, 0.0), (0.002, 0.188306991), (0.004, 0.342290197),
            (0.006, 0.365552347), (0.008, 0.33032252), (0.01, 0.162851861),
            (0.012, -0.00761421632), (0.014, -0.208147149),
            (0.016, -0.319630691), (0.018, -0.366062645),
            (0.02, -0.292418198), (0.022, -0.154739948),
            (0.024, 0.0348118627), (0.026, 0.203644836), (0.028, 0.320571935),
            (0.03, 0.343684011), (0.032, 0.275416881), (0.034, 0.130685597),
            (0.036, -0.0465195184), (0.038, -0.209257494),
            (0.04, -0.31203129), (0.042, -0.328092622), (0.044, -0.254097643),
            (0.046, -0.111492634), (0.048, 0.0595130636), (0.05, 0.21197002),
            (0.052, 0.304116812), (0.054, 0.311840881), (0.056, 0.233967678),
            (0.058, 0.0932264118), (0.06, -0.0711442665),
            (0.062, -0.213670719), (0.064, -0.295749887),
            (0.066, -0.295671413), (0.068, -0.214673134),
            (0.07, -0.0760170044), (0.072, 0.081493385), (0.074, 0.214494797),
            (0.076, 0.286901499), (0.078, 0.27974989), (0.08, 0.196106522),
            (0.082, 0.0599468673), (0.084, -0.0907170836),
            (0.086, -0.214432984), (0.088, -0.277707431),
            (0.09, -0.264065047), (0.092, -0.178317967),
            (0.094, -0.044953455), (0.096, 0.0988496116),
            (0.098, 0.213573889), (0.1, 0.268218537),
        ],
        'stressxx': [
            (0.0, 0.0), (0.002, -6742870.24), (0.004, -6079725.78),
            (0.006, -13773528.1), (0.008, -16156323.4), (0.01, -20915000.8),
            (0.012, -20903456.8), (0.014, -20148327.5), (0.016, -16277574.5),
            (0.018, -11999370.3), (0.02, -7575414.63), (0.022, -4666791.44),
            (0.024, -3904826.89), (0.026, -5424903.43), (0.028, -8927128.55),
            (0.03, -13226701.5), (0.032, -17347742.7), (0.034, -19959565.9),
            (0.036, -20553660.8), (0.038, -18835323.0), (0.04, -15441327.8),
            (0.042, -11215679.2), (0.044, -7412930.0), (0.046, -5001782.96),
            (0.048, -4673095.7), (0.05, -6450565.72), (0.052, -9844779.38),
            (0.054, -13885062.8), (0.056, -17468947.2), (0.058, -19613339.5),
            (0.06, -19756439.6), (0.062, -17884229.4), (0.064, -14538912.6),
            (0.066, -10656600.2), (0.068, -7307530.92), (0.07, -5401649.54),
            (0.072, -5439851.04), (0.074, -7385136.87), (0.076, -10677521.9),
            (0.078, -14397351.0), (0.08, -17519696.3), (0.082, -19198538.3),
            (0.084, -18994121.9), (0.086, -16989087.3), (0.088, -13757391.0),
            (0.09, -10201158.7), (0.092, -7298439.92), (0.094, -5834864.84),
            (0.096, -6190898.5), (0.098, -8243604.51), (0.1, -11407188.9),
        ],
    },
    'MD-06a': {
        'disply': [
            (0.0, 0.0), (0.1, 0.00940247172), (0.2, 0.00809976829),
            (0.3, 0.0073232654), (0.4, 0.00779520807), (0.5, 0.00772061176),
            (0.6, 0.0076851426), (0.7, 0.00770874242), (0.8, 0.0077045574),
            (0.9, 0.00770295689), (1.0, 0.00770413264), (1.1, 0.0077039016),
            (1.2, 0.00770383044), (1.3, 0.0077038888), (1.4, 0.00770387621),
            (1.5, 0.00770387311), (1.6, 0.007703876), (1.7, 0.00770387532),
            (1.8, 0.00770387518), (1.9, 0.00770387533), (2.0, 0.00770387529),
        ],
    },
    'MD-07': {
        'disply': [
            (0.0, 0.0), (0.04, 0.00630969604), (0.08, 0.0152060936),
            (0.12, 0.0125435344), (0.16, 0.00255560318), (0.2, 0.00112354403),
            (0.24, 0.0105243932), (0.28, 0.0158103925), (0.32, 0.00857657359),
            (0.36, 0.000325022533), (0.4, 0.00417606363),
            (0.44, 0.0140063744), (0.48, 0.014185334), (0.52, 0.00442838897),
            (0.56, 0.000249505319), (0.6, 0.00829328946),
            (0.64, 0.0157697755), (0.68, 0.0107910261), (0.72, 0.00127346894),
            (0.76, 0.00235043295), (0.8, 0.0123094986), (0.84, 0.0153153193),
            (0.88, 0.00658850963), (0.92, 5.07576875e-06),
            (0.96, 0.0060329633), (1.0, 0.0150875694),
        ],
    },
    # Mecway 34 headless (mw_solve.py), 28 Oct 2026: every output time;
    # equal to MD-07 at the same times (difference < 1e-14), so Mecway
    # steps with stepsize whatever keepeverynthtimestep is.
    'MD-08a': {
        'disply': [
            (0.0, 0.0), (0.04, 0.00630969604), (0.08, 0.0152060936),
            (0.12, 0.0125435344), (0.16, 0.00255560318), (0.2, 0.00112354403),
            (0.24, 0.0105243932), (0.28, 0.0158103925), (0.32, 0.00857657359),
            (0.36, 0.000325022533), (0.4, 0.00417606363),
            (0.44, 0.0140063744), (0.48, 0.014185334), (0.52, 0.00442838897),
            (0.56, 0.000249505319), (0.6, 0.00829328946),
            (0.64, 0.0157697755), (0.68, 0.0107910261), (0.72, 0.00127346894),
            (0.76, 0.00235043295), (0.8, 0.0123094986), (0.84, 0.0153153193),
            (0.88, 0.00658850963), (0.92, 5.07576875e-06),
            (0.96, 0.0060329633), (1.0, 0.0150875694),
        ],
    },
    'MD-08b': {
        'disply': [
            (0.0, 0.0), (0.1, 0.0155869753), (0.2, 0.00112354403),
            (0.3, 0.0134208748), (0.4, 0.00417606363), (0.5, 0.0097019685),
            (0.6, 0.00829328946), (0.7, 0.00548320193), (0.8, 0.0123094986),
            (0.9, 0.00195904748), (1.0, 0.0150875694),
        ],
    },
}


# ------------------------------------------------------------------
# MD-01 Staplast, ongedempt: u = u_st (1 - cos w t), DAF = 2. Mecway's
# stepsize 0,01 s (w dt = 0,355); Mecway integreert de modale vergelijkingen
# exact, de bridge met NEWMARK en een kleinere rekenstap.
# ------------------------------------------------------------------
STEP = "<y>%r N</y>" % F_TIP

TESTS = [Case(
    "MD-01", GROUP, "Massa op balk, staplast, ongedempt", "dyna_modal_3d",
    build_tipmass(1.0, 0.01, STEP),
    [Check("max. verplaatsing (DAF)", lambda r: peak(
        r.history("disply", TIP), t_max=T_TIP), ref=2.0 * U_ST, tol=0.01,
        unit="m", source="u_max = 2 F/k (Clough & Penzien par. 4-1)"),
     Check("periode", lambda r: period(r.history("disply", TIP), U_ST),
           ref=T_TIP, tol=0.005, unit="s", source="T = 2 pi sqrt(m/k), "
           "k = 3EI/L^3"),
     _hist_check("verloop t.o.v. u_st (1 - cos wt)", "disply", TIP,
                 sdof_exact, 2.0 * U_ST, 0.01,
                 "max |u - u_exact| / (2 u_st) op alle uitvoertijden"),
     _mecway_check("MD-01", "disply", TIP),
     ],
    timeout=600,
    note="10 x line2 (POU_D_E), tipmassa 10 kg (mass2), balk 1 kg/m3; "
         "3 modes; Mecway stepsize 0,01 s, 1 s.")]


# ------------------------------------------------------------------
# MD-02 Staplast met Rayleigh-demping alpha = 2 zeta w (zeta = 0,05):
# piek u_st (1 + exp(-pi zeta / sqrt(1 - zeta^2))).
# ------------------------------------------------------------------
ZETA = 0.05
ALPHA = 2.0 * ZETA * W_TIP
PEAK_D = U_ST * (1.0 + math.exp(-math.pi * ZETA / math.sqrt(1.0 - ZETA ** 2)))

TESTS.append(Case(
    "MD-02", GROUP, "Massa op balk, staplast, Rayleigh-demping",
    "dyna_modal_3d", build_tipmass(1.0, 0.01, STEP, alpha=ALPHA),
    [Check("max. verplaatsing", lambda r: peak(
        r.history("disply", TIP), t_max=T_TIP), ref=PEAK_D, tol=0.01,
        unit="m", source="u_max = u_st (1 + exp(-pi zeta / sqrt(1 - "
        "zeta^2))), zeta = alpha / (2 w) = 0,05 (Clough & Penzien hfst. 3; "
        "Mecway manual par. 9.26)"),
     _hist_check("verloop t.o.v. exact (gedempt)", "disply", TIP,
                 lambda t: sdof_exact(t, ZETA), PEAK_D, 0.01,
                 "max |u - u_exact| / u_max; u_exact gedempte staprespons"),
     _mecway_check("MD-02", "disply", TIP),
     ],
    timeout=600, note="Als MD-01, Rayleigh alpha = 2 zeta w = 3,550 1/s."))


# ------------------------------------------------------------------
# MD-03 Harmonische last F0 sin(Omega t), Omega = 0,8 w, zeta = 0,05:
# exacte respons uit rust (inschakelverschijnsel + stationair, DAF
# stationair 1 / sqrt((1 - r^2)^2 + (2 zeta r)^2) = 2,71). Mecway-tabel met
# 400 punten over 2 s (44 per lastperiode).
# ------------------------------------------------------------------
OM = 0.8 * W_TIP
T_HARM = 2.0
N_TAB = 400


def _sine_table():
    return "".join('<y time="%r s">%r N</y>' % (
        T_HARM * i / N_TAB, F_TIP * math.sin(OM * T_HARM * i / N_TAB))
        for i in range(N_TAB + 1))


def _harm_exact(t):
    return sdof_exact(t, ZETA, OM)


HARM_MAX = max(abs(_harm_exact(0.005 * i)) for i in range(401))

TESTS.append(Case(
    "MD-03", GROUP, "Massa op balk, harmonische last, gedempt",
    "dyna_modal_3d", build_tipmass(T_HARM, 0.005, _sine_table(),
                                   alpha=ALPHA),
    [_hist_check("verloop t.o.v. exact (harmonisch)", "disply", TIP,
                 _harm_exact, HARM_MAX, 0.01,
                 "max |u - u_exact| / max |u_exact|; u_exact: Duhamel in "
                 "gesloten vorm (Clough & Penzien hfst. 3), r = 0,8, zeta = "
                 "0,05; de tabel (lineair tussen 400 punten) wijkt ~0,2% af "
                 "van de sinus"),
     Check("max. verplaatsing", lambda r: max(
         abs(u) for _t, u in r.history("disply", TIP)), ref=HARM_MAX,
         tol=0.01, unit="m", source="max |u_exact| over 2 s (met "
         "inschakelverschijnsel)"),
     _mecway_check("MD-03", "disply", TIP),
     ],
    timeout=600, note="Als MD-02 met F = 100 sin(0,8 w t) N als tabel."))


# ------------------------------------------------------------------
# MD-04 Instelling modal_damping (extra modale demping, geen Mecway-
# invoer): zeta = 0,05 voor alle modes, zonder Rayleigh.
# ------------------------------------------------------------------
TESTS.append(Case(
    "MD-04", GROUP, "Massa op balk, staplast, modale demping (instelling)",
    "dyna_modal_3d", build_tipmass(1.0, 0.01, STEP),
    [Check("max. verplaatsing", lambda r: peak(
        r.history("disply", TIP), t_max=T_TIP), ref=PEAK_D, tol=0.01,
        unit="m", source="als MD-02, zeta = 0,05 (instelling modal_damping)"),
     _hist_check("verloop t.o.v. exact (gedempt)", "disply", TIP,
                 lambda t: sdof_exact(t, ZETA), PEAK_D, 0.01,
                 "max |u - u_exact| / u_max"),
     ],
    settings={"modal_damping": ZETA}, timeout=600,
    note="Als MD-01 met modal_damping = 0,05."))


# ------------------------------------------------------------------
# MD-05 Hex20-console 1 x 0,1 x 0,05 m (10 x 2 x 1), 6 modes, kracht
# 1000 N in Z op het eindvlak, Rayleigh beta = 1e-4 s: gelijk aan Mecway
# (verplaatsing, snelheid en spanning).
# ------------------------------------------------------------------
HEX_TIP = (L, 0.05, 0.025)
HEX_MID = (0.5, 0.05, 0.05)


def build_md05():
    m = Model("D30", timesteps=_ts(0.1, 0.0005),
              attrs={"maxmode": 6, "modesuperposition": "true"})
    m.elset("Balk", "Staal")
    msh = hexmesh(m, "Balk", 10, 2, 1, box(0, L, 0, 0.1, 0, 0.05), order=2)
    m.mat("Staal", STEEL, u'<density type="Simple" density="7850 kg/m³" />')
    m.face_selection("Inklemming", msh["faces"]["u0"])
    m.face_selection("Eindvlak", msh["faces"]["u1"])
    m.add('<fixed selection="Inklemming" />')
    m.add('<force selection="Eindvlak"><x>0 N</x><y>0 N</y><z>1000 N</z>'
          '</force>')
    m.add('<rayleighdamping selection=""><alpha>0 rad/s</alpha>'
          '<beta>0.0001 s</beta></rayleighdamping>')
    for fv in ("displacement", "velocity", "stress", "von Mises stress"):
        m.add('<fieldvariable name="%s" />' % fv)
    return m


TESTS.append(Case(
    "MD-05", GROUP, "Hex20-console, staplast, 6 modes", "dyna_modal_3d",
    build_md05,
    [_mecway_check("MD-05", "displz", HEX_TIP),
     _mecway_check("MD-05", "velz", HEX_TIP),
     _mecway_check("MD-05", "stressxx", HEX_MID),
     ],
    timeout=900, note="10 x 2 x 1 hex20, ingeklemd, 1000 N in Z op het "
                      "eindvlak; beta = 1e-4 s; stepsize 0,5 ms, 0,1 s."))


# ------------------------------------------------------------------
# MD-06 Modale truncatie: Euler-console (20 x line2, staal), puntlast op de
# tip, sterk gedempt (alpha = 20 1/s), 1 mode. Zonder statische correctie
# (zoals Mecway) eindigt de tip op 12 / lambda_1^4 = 0,97069 x de statische
# verplaatsing; met static_correction op de statische (P L^3 / 3EI).
# Mecway keepeverynthtimestep = 10 (201 uitvoertijden).
# ------------------------------------------------------------------
LAMBDA1 = 1.87510407
U_ST6 = F_TIP * L ** 3 / (3.0 * E * IZ)
FRAC1 = 12.0 / LAMBDA1 ** 4


def build_md06():
    m = Model("D30", timesteps=_ts(2.0, 0.001, keep=10),
              attrs={"maxmode": 1, "modesuperposition": "true"})
    m.elset("Balk", "Staal")
    _e, nids = linemesh(m, "Balk", 20, (0, 0, 0), (L, 0, 0))
    m.mat("Staal", RECT, STEEL,
          u'<density type="Simple" density="7850 kg/m³" />')
    m.node_selection("Inklemming", [nids[0]])
    m.node_selection("Tip", [nids[-1]])
    m.add('<fixed selection="Inklemming" />')
    m.add('<force selection="Tip"><x>0 N</x><y>%r N</y><z>0 N</z></force>'
          % F_TIP)
    m.add('<rayleighdamping selection=""><alpha>20 rad/s</alpha>'
          '<beta>0 s</beta></rayleighdamping>')
    return m


def _final(r):
    return r.history("disply", TIP)[-1][1]


TESTS.append(Case(
    "MD-06a", GROUP, "Console, 1 mode, zonder statische correctie",
    "dyna_modal_3d", build_md06,
    [Check("eindverplaatsing", _final, ref=FRAC1 * U_ST6, tol=0.002,
           unit="m", source="12 / lambda_1^4 x P L^3 / 3EI (bijdrage van "
           "mode 1 aan de statische tipverplaatsing, Euler-Bernoulli; "
           "Blevins tabel 8-1)"),
     Check("aantal uitvoertijden", lambda r: len(r.times()), ref=201.0,
           tol_abs=0.0, unit="-", source="t = 0 en elke 10e stap van "
           "0,001 s tot 2 s (Mecway keepeverynthtimestep)"),
     _mecway_check("MD-06a", "disply", TIP),
     ],
    timeout=600, note="20 x line2, staal 7850 kg/m3, alpha = 20 1/s, 2 s."))

TESTS.append(Case(
    "MD-06b", GROUP, "Console, 1 mode, met statische correctie",
    "dyna_modal_3d", build_md06,
    [Check("eindverplaatsing", _final, ref=U_ST6, tol=0.001, unit="m",
           source="P L^3 / 3EI (statische correctie: MACRO_ELAS_MULT, "
           "CORR_STAT; testcase forma12d)"),
     ],
    settings={"static_correction": True}, timeout=600,
    note="Als MD-06a met static_correction."))


# ------------------------------------------------------------------
# MD-07 D30 zonder Mode superposition (Mecway: Newmark op het hele model):
# met dyna_impl_3d, schema NEWMARK en deformation PETIT hetzelfde schema.
# Referentie: dezelfde Newmark-recursie in Python (sdof_response,
# tests_dynamisch) met Mecway's stepsize 0,02 s (w dt = 0,71: periodefout
# zichtbaar, +4%).
# ------------------------------------------------------------------
DT7 = 0.02
N7 = 50
REF7 = sdof_response(DT7, N7, "NEWMARK", 0.0, M_TIP, K_TIP, F_TIP)


def _dev7(r):
    h = r.history("disply", TIP)
    if len(h) != N7 + 1:
        raise ValueError("%d uitvoertijden, verwacht %d" % (len(h), N7 + 1))
    return max(abs(u - REF7[i]) for i, (_t, u) in enumerate(h)) / \
        max(abs(v) for v in REF7)


TESTS.append(Case(
    "MD-07", GROUP, "D30 direct via dyna_impl_3d (Newmark)", "dyna_impl_3d",
    build_tipmass(1.0, DT7, STEP, direct=True),
    [Check("verloop t.o.v. Newmark-schema", _dev7, ref=0.0, tol_abs=0.002,
           unit="-", source="max |u - u_Newmark| / max u_Newmark; "
           "sdof_response (tests_dynamisch), stap 0,02 s zoals Mecway's "
           "stepsize"),
     _mecway_check("MD-07", "disply", TIP),
     ],
    settings={"schema": "NEWMARK", "deformation": "PETIT"}, timeout=600,
    note="Model MD-01 zonder modesuperposition, stepsize 0,02 s."))

# ------------------------------------------------------------------
# MD-08 As MD-07 with "Generate solution every n time steps" (Mecway
# keepeverynthtimestep = 2 and 5): the bridge computes with Mecway's step
# 0,02 s and writes only every n-th step (before the fix,
# the step was n x 0,02 s). Reference: the Newmark recursion of MD-07 at
# every n-th step, and Mecway's own solution.
# ------------------------------------------------------------------
def _dev8(keep):
    ref = REF7[::keep]

    def dev(r):
        h = r.history("disply", TIP)
        if len(h) != len(ref):
            raise ValueError("%d uitvoertijden, verwacht %d" % (len(h),
                                                                 len(ref)))
        return max(abs(u - ref[i]) for i, (_t, u) in enumerate(h)) / \
            max(abs(v) for v in REF7)
    return dev


for _sfx, _keep in (("a", 2), ("b", 5)):
    TESTS.append(Case(
        "MD-08" + _sfx, GROUP, "D30 direct, uitvoer elke %de stap "
        "(keepeverynthtimestep)" % _keep, "dyna_impl_3d",
        build_tipmass(1.0, DT7, STEP, direct=True, keep=_keep),
        [Check("verloop t.o.v. Newmark-schema", _dev8(_keep), ref=0.0,
               tol_abs=0.002, unit="-",
               source="max |u - u_Newmark| / max u_Newmark op elke %de "
               "stap; sdof_response (tests_dynamisch), stap 0,02 s zoals "
               "Mecway's stepsize" % _keep),
         _mecway_check("MD-08" + _sfx, "disply", TIP),
         ],
        settings={"schema": "NEWMARK", "deformation": "PETIT"}, timeout=600,
        note="Model MD-07 met keepeverynthtimestep = %d; substeps_per_output "
             "= 1." % _keep))
