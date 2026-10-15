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
"""
import os
import sys
import math
from verif_lib import Case, Check, Model, linemesh, hexmesh, box, SCRIPTS

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
]
