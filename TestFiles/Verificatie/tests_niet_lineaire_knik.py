# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Niet-lineaire knik (nonlin_static_3d): het stabiliteitscriterium CRIT_STAB
per stap (instelling crit_stab) en de knikvorm als imperfectie
(imperfection_amplitude/_mode/_unit). Toelichting: docs/Verificatie.md
hoofdstuk Niet-lineaire knik (NK), docs/Modaal_en_knik.md par. 5.

Model: ingeklemde kolom L = 1 m, doorsnede a x b = 0,02 x 0,03 m (a in Y,
de zwakke as), staal; drukkracht P(t) = t P_eind langs -X (tijdstabel 0 ->
P_eind op t = 0 -> 1). Euler (Timoshenko & Gere, 1961, par. 2.1):
Pcr = pi^2 E I / (2 L)^2 = 10363 N.

NK-01   20 balkelementen (POU_D_E, altijd PETIT): CRIT_STAB geeft de
        kritische lastfactor van de huidige last; lambda(t) P(t) = Pcr.
NK-02a  hex20 (50x2x3), standaard DEFORMATION (GREEN_LAGRANGE): CRIT_STAB
        geeft de kleinste eigenwaarde van K_T met omgekeerd teken; die gaat
        lineair naar 0 bij Pcr (knikpunt uit de laatste twee stappen).
NK-02b  idem met DEFORMATION = PETIT: lastfactor zoals NK-01.
NK-03   hex20, imperfectie knikvorm 1 met e0 = 0,001 L (eenheid L): de
        totale uitbuiging volgt e0 / (1 - P/Pcr) (Timoshenko & Gere hfdst.
        1, staaf met beginkromming; Southwell, 1932) en de lineaire
        knikfactor van de
        imperfectiestap is gelijk aan buckling_3d (BU-03).
NK-04   hex20, bilineair plastisch (fy zo dat Npl = 1,5 Pcr), imperfectie
        e0 = 5 mm: de draagkracht daalt van Pcr naar P_u tussen de eerste
        vloei volgens Ayrton-Perry en het plastisch scharnier op de
        elastische tweede-orde-uitbuiging; CRIT_STAB gaat bij P_u naar 0.

NK-05 .. NK-10: slanke kolom met grote-rotatiebalken (elem_beam =
POU_D_T_GD; GitHub issue #10): de imperfectie via het hulpmodel met POU_D_T
(bridge_to_aster._imperfection_aux_model), de stapbewaking gd_step_limit
(_gd_step_guard, _guarded_solve) en de sprongcontrole (print_jump_check),
gelezen met bridge_results_liml.read_step_guard. Model: scharnierende kolom
L = 2,5 m langs X, RectTube 48,96 x 48,96 x 3,85 mm, E = 200 GPa, nu = 0,25,
20 line3, torsie vast aan een eind; drukkracht 0 -> 100 kN op t = 0 -> 1,
stepsize 0,01 s (P/Pcr = 1,34 op t = 1).

NK-05   e0 = 0,25 mm (sinus) in de mesh, standaard stapbewaking: de kolom
        volgt de elastica; geen sprong en geen einde van de bewaking.
        (Met gd_step_limit = 0,05 blijft dit zo met 20 line3, maar springt
        de kolom met 10 line3 bij stepsize 0,01 s.)
NK-05b  idem met gd_step_limit = 0: de sprong naar de instabiele tak aan de
        overkant op t = 0,75 .. 0,76, gemeld door de sprongcontrole; op
        t = 1 de totale uitbuiging e0 / (P/Pcr - 1).
NK-06   rechte mesh, imperfection_amplitude = 0,25 mm: elastica op
        sqrt(dy^2 + dz^2) (dubbele eigenwaarde, richting willekeurig);
        lineaire knikfactor van de imperfectiestap (hulpmodel) = Pcr.
NK-07   NK-05 met een losse uitkraging met constante eindkracht 10 kN in
        dezelfde elset: de eerste stap overschrijdt de grens, die laat zich
        niet verkleinen, de bewaking eindigt op t = 0 en de kolom springt
        alsnog. De grens van de bewaking; de sprongcontrole meldt het.
NK-08   constante last, eerste stap boven de grens: bewaking eindigt op
        t = 0, resultaat gelijk aan een run met gd_step_limit = 0.
NK-09   doorslag van een ondiepe boog (echt grenspunt), gd_step_limit =
        0,005 (10 mm): de bewaking raakt uitgeput bij t = 0,196 en de run
        gaat door; eindresultaat gelijk aan gd_step_limit = 0.
NK-10   gemengd model door het hulpmodel: kolom POU_D_T_GD, losse schaal op
        trek, puntmassa en een #ASTER-regel, imperfectie 2,5 mm, P = 0,5 Pcr:
        kniklast, versterking 1 / (1 - P/Pcr) en rek van de schaal.
"""
import os
import sys
import math
from verif_lib import (Case, Check, Model, linemesh, hexmesh, quadmesh, box,
                       rect, SCRIPTS)

GROUP = "Niet-lineaire knik"
E = 210e9
L, A, B = 1.0, 0.02, 0.03
IZ = B * A ** 3 / 12.0
PCR = math.pi ** 2 * E * IZ / (2.0 * L) ** 2
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
TS = {"timeperiod": "1 s", "stepsize": "0.1 s"}
TIP = (L, 0.0, 0.0)
EULER = "Euler, Pcr = pi^2 EI/(2L)^2 (Timoshenko & Gere 2.1)"


def _history(tag, pts, unit):
    return "".join('<{0} time="{1:g} s">{2:.12g} {3}</{0}>'.format(
        tag, t, v, unit) for t, v in pts)


def build_beam(p_end):
    def build():
        m = Model("L30", timesteps=TS)
        m.elset("Kolom", "Staal")
        _e, nids = linemesh(m, "Kolom", 20, (0, 0, 0), (L, 0, 0))
        m.mat("Staal", '<geometric type="RectBar" recta="%g m" rectb="%g m" '
              '/>' % (A, B), STEEL)
        m.node_selection("Voet", [nids[0]])
        m.node_selection("Kop", [nids[-1]])
        m.add('<fixed selection="Voet" />')
        m.add('<force selection="Kop">%s<y>0 N</y><z>0 N</z></force>'
              % _history("x", [(0, 0), (1, -p_end)], "N"))
        return m
    return build


def build_solid(p_end, plastic=None, step=None):
    """step: Mecway's Time step size in s (standaard die van TS); de
    bridge rekent Mecway's stappen."""
    def build():
        ts = dict(TS)
        if step:
            ts["stepsize"] = "%g s" % step
        m = Model("L30", timesteps=ts)
        m.elset("Kolom", "Staal")
        g = hexmesh(m, "Kolom", 50, 2, 3,
                    box(0, L, -A / 2, A / 2, -B / 2, B / 2), order=2)
        if plastic:
            m.mat("Staal", STEEL, '<plastic type="BilinearIsotropic" '
                  'yieldstrength="%g Pa" tangentmodulus="%g Pa" />' % plastic)
        else:
            m.mat("Staal", STEEL)
        m.face_selection("Voet", g["faces"]["u0"])
        m.face_selection("Kop", g["faces"]["u1"])
        m.add('<fixed selection="Voet" />')
        m.add('<traction selection="Kop">%s<y>0 Pa</y><z>0 Pa</z>'
              '</traction>' % _history("x", [(0, 0), (1, -p_end / (A * B))],
                                       "Pa"))
        return m
    return build


# ------------------------------------------------------------------
# Uitlezen van de .mess (BRIDGE_CRIT_STAB / BRIDGE_IMPERFECTIE-regels,
# bridge_results_liml zoals de bridge zelf)
# ------------------------------------------------------------------
def _brl():
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)
    import bridge_results_liml
    return bridge_results_liml


def _crit(r, kind):
    cs = _brl().read_crit_stab(getattr(r, "mess", None))
    if not cs or not cs["rows"]:
        raise ValueError("geen CRIT_STAB in de .mess")
    if cs["kind"] != kind:
        raise ValueError("CRIT_STAB-soort %s, verwacht %s" % (cs["kind"],
                                                              kind))
    return cs["rows"]


def _factor_at(r, t):
    rows = _crit(r, "factor")
    tt, lam = min(rows, key=lambda x: abs(x[0] - t))
    if abs(tt - t) > 1e-6:
        raise ValueError("geen CRIT_STAB op t = %g" % t)
    return lam


def _eigen_estimate(r):
    est = _brl().crit_stab_estimate(_crit(r, "eigen"))
    if not est:
        raise ValueError("geen schatting van het knikpunt")
    return est[1]


def _imperfection_factor(r):
    imp = _brl().read_imperfection(getattr(r, "mess", None))
    if not imp or imp["mode"] not in imp["factors"]:
        raise ValueError("geen imperfectie in de .mess")
    return imp["factors"][imp["mode"]]


# ------------------------------------------------------------------
# NK-01 / NK-02: CRIT_STAB op de perfecte kolom, P_eind = 0,9 Pcr
# ------------------------------------------------------------------
P_END = 0.9 * PCR


def _factor_checks(tol, src_extra=""):
    out = []
    for t in (0.5, 1.0):
        out.append(Check("lambda P(t) t=%g" % t,
                         (lambda tt: lambda r: _factor_at(r, tt) * tt *
                          P_END)(t),
                         ref=PCR, tol=tol, unit="N",
                         source=EULER + src_extra))
    return out


# ------------------------------------------------------------------
# NK-03: imperfectie e0 = 0,001 L in knikvorm 1, P_eind = 0,9 Pcr
# ------------------------------------------------------------------
E0 = 0.001 * L
P_REF_BUCKLING = 1000.0      # last van BU-03 (kniklastfactor x 1000 N)


def _w_total(r, t):
    """Totale uitbuiging van de kop: e0 + |DY| (DY t.o.v. de imperfecte
    vorm; de knikvorm heeft zijn grootste verplaatsing in de kop)."""
    for tt, w in r.history("disply", TIP):
        if abs(tt - t) < 1e-6:
            return E0 + abs(w)
    raise ValueError("tijdstip %g niet bereikt" % t)


def _southwell(r, alpha_max=0.7):
    """Southwell (1932): delta = Pcr (delta / P) - e0 (delta = extra
    uitbuiging); helling van de kleinste-kwadratenlijn door de stappen met
    P <= alpha_max Pcr."""
    pts = []
    for t, w in r.history("disply", TIP):
        p = t * P_END
        if t > 0 and p <= alpha_max * PCR + 1e-9:
            d = abs(w)
            pts.append((d / p, d))
    n = float(len(pts))
    sx = sum(x for x, _ in pts)
    sy = sum(y for _, y in pts)
    sxx = sum(x * x for x, _ in pts)
    sxy = sum(x * y for x, y in pts)
    return (n * sxy - sx * sy) / (n * sxx - sx * sx)


def _nk03_checks():
    out = [Check("lineaire knik imperfectiestap x P_eind",
                 lambda r: _imperfection_factor(r) * P_END, ref=PCR,
                 tol=0.005, unit="N",
                 source=EULER + "; BU-03-h20-n2 (zelfde mesh): +0,2%"),
           Check("CRIT_STAB knikpunt x P_eind",
                 lambda r: _eigen_estimate(r) * P_END, ref=PCR, tol=0.02,
                 unit="N", source=EULER)]
    for alpha in (0.3, 0.5, 0.7):
        t = math.floor(alpha / 0.9 / 0.05 + 1e-9) * 0.05   # P <= alpha Pcr
        a = t * P_END / PCR
        out.append(Check("w/e0 P=%.3f Pcr" % a,
                         (lambda tt: lambda r: _w_total(r, tt) / E0)(t),
                         ref=1.0 / (1.0 - a), tol=0.05, unit="-",
                         source="versterkingsfactor 1/(1 - P/Pcr), Euler-"
                         "Pcr (Timoshenko & Gere hfdst. 1)"))
    out.append(Check("Southwell Pcr (P <= 0,7 Pcr)", _southwell, ref=PCR,
                     tol=0.02, unit="N",
                     source="Southwell (1932): helling delta tegen "
                     "delta/P; " + EULER))
    return out


# ------------------------------------------------------------------
# NK-04: elastisch-plastisch, e0 = 5 mm, P_eind = 0,8 Pcr
# ------------------------------------------------------------------
E0_P = 0.005
FY = 1.5 * PCR / (A * B)          # Npl = 1,5 Pcr
H_P = 210e6                        # Mecway tangentmodulus (= E / 1000)
P_END_P = 0.8 * PCR


def _bisect(f, lo, hi):
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


# Eerste vloei aan de voet (Ayrton-Perry): P/A + P e0/(1 - a) / W = fy,
# W = b a^2/6. Plastisch scharnier: (P/Npl)^2 + P e0/(1 - a) / Mpl = 1,
# Mpl = fy b a^2/4 (volledig plastische rechthoek; de interactie volgt uit
# het spanningsblok). De echte bezwijklast ligt ertussen: boven de eerste
# vloei, en onder het scharnier met de elastische uitbuiging (de
# werkelijke uitbuiging is door het vloeien groter). De versteviging
# (H = E/1000) is verwaarloosd.
_W = B * A ** 2 / 6.0
_MPL = FY * B * A ** 2 / 4.0
_NPL = FY * A * B
ALPHA_Y = _bisect(lambda a: a * PCR / (A * B) + a * PCR * E0_P /
                  ((1 - a) * _W) - FY, 1e-6, 0.999)
ALPHA_H = _bisect(lambda a: (a * PCR / _NPL) ** 2 + a * PCR * E0_P /
                  ((1 - a) * _MPL) - 1.0, 1e-6, 0.999)


def _capacity(r):
    return r.times()[-1] * P_END_P / PCR


def _crit_ratio(r):
    rows = _crit(r, "eigen")
    return rows[-1][1] / rows[0][1]


# ------------------------------------------------------------------
# NK-05 .. NK-10: scharnierende kolom met POU_D_T_GD (issue #10)
# ------------------------------------------------------------------
GD = {"elem_beam": "POU_D_T_GD"}
L_K = 2.5
A_K, T_K = 0.04895912993185, 0.003851935412259
E_K, NU_K = 200e9, 0.25
E0_K = 0.00025                      # imperfectie 0,25 mm
P_K = 100e3                         # eindlast
SEC_K = ('<geometric type="RectTube" recta="%.13g mm" rectb="%.13g mm" '
         'rectthickness="%.13g mm" />' % (A_K * 1e3, A_K * 1e3, T_K * 1e3))
MECH_K = ('<mechanical type="Isotropic" youngsmodulus="200000 MPa" '
          'poissonratio="0.25" />')
DENS_K = u'<density type="Simple" density="7850 kg/m\u00b3" />'
I_K = (A_K ** 4 - (A_K - 2 * T_K) ** 4) / 12.0
PE_K = math.pi ** 2 * E_K * I_K / L_K ** 2
# Dwarskracht: afschuifoppervlakte A/2 (de twee lijven), Pcr = PE / (1 + PE /
# (G A/2)) (Timoshenko & Gere hfdst. 2). De lineaire knik van Code-Aster geeft
# 0,06% minder (zijn afschuifoppervlakte van de koker: NIET geverifieerd).
AREA_K = A_K ** 2 - (A_K - 2 * T_K) ** 2
PCR_K = PE_K / (1.0 + PE_K / (E_K / (2 * (1 + NU_K)) * AREA_K / 2.0))
MID_K = (L_K / 2.0, 0.0, 0.0)
TIP_K = (L_K, 0.0, 0.0)


def _pinned(m, a, b):
    """Scharnier a (X, Y, Z en torsie vast), scharnier b (Y, Z vast)."""
    for sel, dirs in ((a, "xyz"), (b, "yz")):
        for d in dirs:
            m.add('<displacement selection="%s"><value>0 m</value>%s'
                  '</displacement>' % (sel, "".join(
                      "<%s>%d</%s>" % (c, c == d, c) for c in "xyz")))
    m.add('<noderotation selection="%s"><value>0 rad</value><x>1</x><y>0</y>'
          '<z>0</z></noderotation>' % a)


def _sine(x):
    return -E0_K * math.sin(math.pi * x / L_K)


def _column(z=None, section=SEC_K, step=0.01):
    """Kolom van 20 line3 met scharnieren; z(x) = vorm in de mesh."""
    m = Model("L30", timesteps={"timeperiod": "1 s",
                                "stepsize": "%g s" % step})
    m.elset("Beam", "S")
    nn = 40
    nids = [m.node(L_K * i / float(nn), 0,
                   z(L_K * i / float(nn)) if z else 0.0)
            for i in range(nn + 1)]
    for i in range(nn // 2):
        m.elem("Beam", "line3", nids[2 * i:2 * i + 3])
    m.mat("S", section, MECH_K, DENS_K)
    m.node_selection("PinA", [nids[0]])
    m.node_selection("PinB", [nids[-1]])
    _pinned(m, "PinA", "PinB")
    return m, nids


def _ramp(m, sel, p):
    m.add('<force selection="%s"><x time="0 s">0 N</x><x time="1 s">%r N</x>'
          '<y>0 N</y><z>0 N</z></force>' % (sel, p))


def build_col(z=None):
    def build():
        m = _column(z)[0]
        _ramp(m, "PinB", -P_K)
        return m
    return build


def build_stub():
    """NK-05 plus een losse uitkraging in dezelfde elset, constante
    eindkracht: die laat de stapbewaking al in de eerste stap eindigen."""
    m = build_col(_sine)()
    stub = [m.node(0.1 * i, 1.0, 0.0) for i in range(11)]
    for i in range(0, 10, 2):
        m.elem("Beam", "line3", stub[i:i + 3])
    m.node_selection("StubRoot", [stub[0]])
    m.node_selection("StubTip", [stub[-1]])
    m.add('<fixed selection="StubRoot" />')
    m.add('<force selection="StubTip"><x>0 N</x><y>0 N</y>'
          '<z>-10000 N</z></force>')
    return m


def build_const():
    """Constante dwarskracht 15 kN op het midden, 10 stappen."""
    m = _column(step=0.1)[0]
    m.node_selection("Mid", [m.node(L_K / 2.0, 0, 0)])
    m.add('<force selection="Mid"><x>0 N</x><y>0 N</y><z>-15000 N</z>'
          '</force>')
    return m


S_B, H_B = 2.0, 0.04                # boog: overspanning, pijl
MID_B = (S_B / 2.0, 0.0, H_B)


def build_arch():
    """Ondiepe scharnierende boog (sinus), 40 line2, puntlast 0 -> 60 kN."""
    n = 40
    m = Model("L30", timesteps={"timeperiod": "1 s", "stepsize": "0.02 s"})
    m.elset("Beam", "S")
    nids = [m.node(S_B * i / float(n), 0,
                   H_B * math.sin(math.pi * i / float(n)))
            for i in range(n + 1)]
    for i in range(n):
        m.elem("Beam", "line2", nids[i:i + 2])
    m.mat("S", SEC_K, MECH_K, DENS_K)
    m.node_selection("PinA", [nids[0]])
    m.node_selection("PinB", [nids[-1]])
    m.node_selection("Mid", [nids[n // 2]])
    for sel in ("PinA", "PinB"):
        for d in "xyz":
            m.add('<displacement selection="%s"><value>0 m</value>%s'
                  '</displacement>' % (sel, "".join(
                      "<%s>%d</%s>" % (c, c == d, c) for c in "xyz")))
    m.add('<noderotation selection="PinA"><value>0 rad</value><x>1</x><y>0'
          '</y><z>0</z></noderotation>')
    m.add('<force selection="Mid"><x>0 N</x><y>0 N</y><z time="0 s">0 N</z>'
          '<z time="1 s">-60000 N</z></force>')
    return m


# NK-10: massieve rechthoek (a in Y is de zwakke as): een enkele knikvorm, en
# de afschuifoppervlakte van de rechthoek is A / 1,2.
A_M, B_M = 0.03, 0.05
EI_M = E_K * B_M * A_M ** 3 / 12.0
PE_M = math.pi ** 2 * EI_M / L_K ** 2
GA_M = E_K / (2 * (1 + NU_K)) * A_M * B_M / 1.2
PCR_M = PE_M / (1.0 + PE_M / GA_M)
P_M = 0.5 * PCR_M
E0_M = 0.0025
F_PL, L_PL, B_PL, T_PL = 10e3, 0.5, 0.1, 0.005     # trekstrook (schaal)
ASTER_M = (u"<ccxmodeldefinition>** ASTER print('BRIDGE_NK10 ASTER=1')\n"
           u"</ccxmodeldefinition>")


def build_mixed():
    m, nids = _column(section='<geometric type="RectBar" recta="%g m" '
                      'rectb="%g m" />' % (A_M, B_M), step=0.1)
    _ramp(m, "PinB", -P_M)
    m.node_selection("Massa", [nids[len(nids) // 2]])
    m.add('<mass2 selection="Massa"><value>5 kg</value></mass2>')
    m.elset("Strook", "P")
    g = quadmesh(m, "Strook", 10, 2, rect(0, L_PL, 1.0, 1.0 + B_PL))
    m.mat("P", '<geometric type="Plate" thickness="%g m" />' % T_PL, MECH_K)
    m.node_selection("PlaatVast", sorted(g["nodes"]["u0"]))
    m.node_selection("PlaatAlles", sorted(n for s in g["nodes"].values()
                                          for n in s))
    m.node_selection("PlaatY", [m.node(0, 1.0, 0)])
    for sel, d in (("PlaatVast", "x"), ("PlaatY", "y"), ("PlaatAlles", "z")):
        m.add('<displacement selection="%s"><value>0 m</value>%s'
              '</displacement>' % (sel, "".join(
                  "<%s>%d</%s>" % (c, c == d, c) for c in "xyz")))
    m.face_selection("PlaatRand", g["edges"]["u1"])
    _ramp(m, "PlaatRand", F_PL)
    m.add(ASTER_M)
    return m


def _elastica(ratio):
    """
    Knik-elastica van de scharnierende staaf (Timoshenko & Gere, 1961,
    hfdst. 2): P/Pcr = (2 K(m) / pi)^2 met k^2 = m; grootste uitbuiging k L / K
    en verkorting L (2 - 2 E / K). K, E: volledige elliptische integralen
    (rekenkundig-meetkundig gemiddelde, Abramowitz & Stegun 17.6).
    """
    def ke(m):
        a, b, c = 1.0, math.sqrt(1.0 - m), math.sqrt(m)
        s, p = 0.5 * c * c, 1.0
        while abs(c) > 1e-14:
            a, b, c = (a + b) / 2.0, math.sqrt(a * b), (a - b) / 2.0
            p *= 2.0
            s += 0.5 * p * c * c
        k1 = math.pi / (2.0 * a)
        return k1, k1 * (1.0 - s)

    m = _bisect(lambda x: (2.0 * ke(x)[0] / math.pi) ** 2 - ratio, 1e-12,
                0.999)
    k1, e1 = ke(m)
    return math.sqrt(m) * L_K / k1, L_K * (2.0 - 2.0 * e1 / k1)


W_EL, U_EL = _elastica(P_K / PCR_K)
# Instabiele tak: totale uitbuiging e0 / (P/Pcr - 1) aan de overkant van de
# imperfectie, ten opzichte van de mesh dus plus e0.
W_TAK = E0_K / (P_K / PCR_K - 1.0) + E0_K
ELASTICA = "elastica (Timoshenko & Gere hfdst. 2), P/Pcr = %.4f" % (
    P_K / PCR_K)
TAK = ("instabiele tak e0/(P/Pcr - 1) + e0 (beginkromming, Timoshenko & "
       "Gere hfdst. 1, boven Pcr)")


def _guard(r):
    return _brl().read_step_guard(getattr(r, "mess", None))


def _end(r):
    """De laatste stap; die moet t = 1 zijn."""
    if abs(r.times()[-1] - 1.0) > 1e-6:
        raise ValueError("gestopt op t = %g" % r.times()[-1])
    return r.steps[-1][1]


def _transverse(r, point):
    d, n = _end(r), r.nearest(point)
    return math.hypot(d["disply"][n], d["displz"][n])


def _deflection(r):
    """Totale uitbuiging midden: e0 + verplaatsing t.o.v. de imperfecte
    vorm."""
    return _transverse(r, MID_K) + E0_K


def _shortening(r):
    return abs(_end(r)["displx"][r.nearest(TIP_K)])


def _dz(point):
    return lambda r: _end(r)["displz"][r.nearest(point)]


def _n_jumps(r):
    return len(_guard(r)["jumps"])


def _guard_ended(r):
    """Tijdstip waarop de stapbewaking eindigde, -1 als dat niet gebeurde."""
    t = _guard(r)["ended"]
    return -1.0 if t is None else t


def _jump_time(r):
    jumps = _guard(r)["jumps"]
    if not jumps:
        raise ValueError("geen BRIDGE_SPRONG in de .mess")
    return 0.5 * (jumps[0][0] + jumps[0][1])


def _t_end(r):
    return r.times()[-1]


# Referentie NK-08/NK-09: geen formule, maar een echte run van hetzelfde
# model met gd_step_limit = 0 (Code-Aster 17.4, 5 nov. 2026); de controle
# laat zien dat de bewaking na haar einde niets aan de oplossing verandert.
NK08_REF = -0.102471456
NK09_REF = -0.105194759
NK_REF_SRC = "run met gd_step_limit = 0, Code-Aster 17.4 (geen analytische " \
             "referentie)"


def _follows_elastica():
    return [Check("uitbuiging midden t=1", _deflection, ref=W_EL, tol=0.005,
                  unit="m", source=ELASTICA),
            Check("eindverkorting t=1", _shortening, ref=U_EL, tol=0.005,
                  unit="m", source=ELASTICA)]


def _no_jump():
    return [Check("aantal BRIDGE_SPRONG", _n_jumps, ref=0.0, tol_abs=0.5,
                  unit="-", source="de kolom blijft op de stabiele tak"),
            Check("BRIDGE_VANGNET (t, -1 = geen)", _guard_ended, ref=-1.0,
                  tol_abs=1e-9, unit="-", source="de bewaking eindigt niet")]


TESTS = [
    Case("NK-01", GROUP, "Ingeklemde kolom, CRIT_STAB, 20 balkelementen",
         "nonlin_static_3d", build_beam(P_END), _factor_checks(0.002),
         settings={"crit_stab": True},
         note="POU_D_E (PETIT): kritische lastfactor per stap; P tot "
              "0,9 Pcr in 10 stappen."),
    Case("NK-02a", GROUP, "Ingeklemde kolom, CRIT_STAB, hex20, grote "
         "verplaatsingen", "nonlin_static_3d", build_solid(P_END),
         [Check("knikpunt x P_eind", lambda r: _eigen_estimate(r) * P_END,
                ref=PCR, tol=0.02, unit="N",
                source=EULER + "; knikpunt = lambda lineair naar 0 uit de "
                "laatste twee stappen")],
         settings={"crit_stab": True},
         note="GREEN_LAGRANGE: lambda = -(kleinste eigenwaarde van K_T)."),
    Case("NK-02b", GROUP, "Ingeklemde kolom, CRIT_STAB, hex20, PETIT",
         "nonlin_static_3d", build_solid(P_END),
         _factor_checks(0.005, "; BU-03-h20-n2 (zelfde mesh): +0,2%"),
         settings={"crit_stab": True, "deformation": "PETIT"},
         note="Kleine verplaatsingen: kritische lastfactor per stap."),
    Case("NK-03", GROUP, "Ingeklemde kolom hex20 met imperfectie L/1000 "
         "(knikvorm 1)", "nonlin_static_3d", build_solid(P_END, step=0.05),
         _nk03_checks(),
         settings={"crit_stab": True, "imperfection_amplitude": 0.001,
                   "imperfection_unit": "L"},
         note="e0 = 0,001 L = 1 mm; P tot 0,9 Pcr in 20 stappen "
              "(stepsize 0,05 s)."),
    Case("NK-04", GROUP, "Ingeklemde kolom hex20, plastisch, imperfectie "
         "5 mm: draagkracht", "nonlin_static_3d",
         build_solid(P_END_P, plastic=(FY, H_P), step=0.025),
         [Check("P_u/Pcr (Ayrton-Perry %.3f .. scharnier %.3f)"
                % (ALPHA_Y, ALPHA_H), _capacity,
                ref=0.5 * (ALPHA_Y + ALPHA_H),
                tol_abs=0.5 * (ALPHA_H - ALPHA_Y), unit="-",
                source="eerste vloei P/A + P e0/((1-P/Pcr) W) = fy "
                "(Ayrton-Perry) <= P_u <= (P/Npl)^2 + M/Mpl = 1 met M = "
                "P e0/(1-P/Pcr)"),
          Check("CRIT_STAB bij P_u / begin", _crit_ratio, ref=0.0,
                tol_abs=0.05, unit="-",
                source="grenspunt: kleinste eigenwaarde van K_T naar 0")],
         settings={"crit_stab": True, "imperfection_amplitude": E0_P},
         note="fy = %.1f MPa (Npl = 1,5 Pcr), H = 210 MPa; P tot 0,8 Pcr: "
              "de run stopt op het grenspunt (BRIDGE_ONVOLLEDIG, "
              "verwacht)." % (FY / 1e6)),
    Case("NK-05", GROUP, "Kolom POU_D_T_GD boven de kniklast, imperfectie in "
         "de mesh, stapbewaking", "nonlin_static_3d", build_col(_sine),
         _follows_elastica() + _no_jump(), general=GD,
         note="e0 = 0,25 mm (sinus), 20 line3, 100 kN in 100 stappen, "
              "standaard gd_step_limit."),
    Case("NK-05b", GROUP, "NK-05 zonder stapbewaking: sprong naar de "
         "instabiele tak", "nonlin_static_3d", build_col(_sine),
         [Check("t sprong", _jump_time, ref=0.755, tol_abs=0.01, unit="s",
                source="stap 0,75 -> 0,76 bij deze stapgrootte"),
          Check("dz midden t=1", _dz(MID_K), ref=W_TAK, tol=0.02, unit="m",
                source=TAK)],
         settings={"gd_step_limit": 0.0}, general=GD,
         note="gd_step_limit = 0: Newton convergeert op de instabiele tak; "
              "alleen de sprongcontrole meldt het."),
    Case("NK-06", GROUP, "Kolom POU_D_T_GD, rechte mesh, imperfection_"
         "amplitude via het hulpmodel", "nonlin_static_3d", build_col(),
         _follows_elastica() + _no_jump() + [
             Check("lineaire knik imperfectiestap x P_eind",
                   lambda r: _imperfection_factor(r) * P_K, ref=PCR_K,
                   tol=0.005, unit="N", source="Pcr = PE / (1 + PE / (G A/2)) "
                   "(Timoshenko & Gere hfdst. 2)")],
         settings={"imperfection_amplitude": E0_K}, general=GD,
         note="Vierkante koker: dubbele eigenwaarde, de richting van de "
              "vorm is willekeurig, daarom sqrt(dy^2 + dz^2)."),
    Case("NK-07", GROUP, "Grens van de stapbewaking: constante last die de "
         "grens al in de eerste stap overschrijdt", "nonlin_static_3d",
         build_stub,
         [Check("BRIDGE_VANGNET t", _guard_ended, ref=0.0, tol_abs=1e-9,
                unit="s", source="eerste stap kan niet kleiner"),
          Check("t sprong", _jump_time, ref=0.755, tol_abs=0.01, unit="s",
                source="als NK-05b: de sprongcontrole meldt het"),
          Check("dz midden t=1", _dz(MID_K), ref=W_TAK, tol=0.02, unit="m",
                source=TAK)],
         general=GD,
         note="Losse uitkraging 1 m, 10 kN in dezelfde elset. Grens van de "
              "bewaking: daarna rekent de run als zonder bewaking."),
    Case("NK-08", GROUP, "Stapbewaking: constante last, eerste stap boven "
         "de grens", "nonlin_static_3d", build_const,
         [Check("BRIDGE_VANGNET t", _guard_ended, ref=0.0, tol_abs=1e-9,
                unit="s", source="eerste stap kan niet kleiner"),
          Check("dz midden t=1", _dz(MID_K), ref=NK08_REF, tol=1e-6, unit="m",
                source=NK_REF_SRC, in_series=False)],
         general=GD,
         note="Rechte kolom, 15 kN dwars op het midden vanaf t = 0, 10 "
              "stappen."),
    Case("NK-09", GROUP, "Stapbewaking: doorslag van een ondiepe boog",
         "nonlin_static_3d", build_arch,
         [Check("BRIDGE_VANGNET t", _guard_ended, ref=0.196, tol_abs=0.005,
                unit="s", source="stappen rond de doorslag"),
          Check("t einde", _t_end, ref=1.0, tol_abs=1e-9, unit="s",
                source="de run gaat door na de bewaking"),
          Check("dz midden t=1", _dz(MID_B), ref=NK09_REF, tol=1e-6, unit="m",
                source=NK_REF_SRC, in_series=False)],
         settings={"gd_step_limit": 0.005}, general=GD,
         note="Boog overspanning 2 m, pijl 40 mm, 40 line2, last 0 -> 60 kN "
              "op het midden, 50 stappen; grens 10 mm."),
    Case("NK-10", GROUP, "Gemengd model door het hulpmodel: POU_D_T_GD, "
         "schaal, puntmassa, #ASTER-regel", "nonlin_static_3d", build_mixed,
         [Check("lineaire knik imperfectiestap x P_eind",
                lambda r: _imperfection_factor(r) * P_M, ref=PCR_M,
                tol=0.005, unit="N", source="Pcr = PE / (1 + PE / (G A / "
                "1,2)), PE = pi^2 EI/L^2 (Timoshenko & Gere hfdst. 2)"),
          Check("w/e0 midden t=1",
                lambda r: 1.0 + _transverse(r, MID_K) / E0_M,
                ref=1.0 / (1.0 - P_M / PCR_M), tol=0.01, unit="-",
                source="versterking 1/(1 - P/Pcr) (Timoshenko & Gere "
                "hfdst. 1)"),
          Check("rek schaal", lambda r: _end(r)["displx"][
              r.nearest((L_PL, 1.0, 0.0))], ref=F_PL * L_PL /
                (E_K * T_PL * B_PL), tol=0.005, unit="m",
                source="F L / (E t b)"),
          Check("#ASTER-regel uitgevoerd", lambda r: _brl().read_tagged(
              r.mess, "BRIDGE_NK10")["ASTER"], ref=1.0, tol_abs=0.5, unit="-",
                source="print in de .mess")],
         settings={"imperfection_amplitude": E0_M}, general=GD,
         note="Kolom 30 x 50 mm, imperfectie 2,5 mm, P = 0,5 Pcr, 10 "
              "stappen; quad4-strook 500 x 100 x 5 mm op trek en 5 kg op "
              "het kolommidden."),
]
