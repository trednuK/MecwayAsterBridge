# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Niet-lineair statisch (Mecway L30 -> STAT_NON_LINE, analyse nonlin_static_3d).

  NL-01  materiaal-niet-lineair: trekstaaf met bilineaire isotrope
         versteviging, opgelegde verlenging met ontlasten
  NL-02  geometrisch niet-lineair: ingeklemde slanke balk met een eindlast
         van vaste richting (elastica, Bisshopp & Drucker 1945), volume
         (hex20) en schaal (COQUE_3D)
  NL-03  contact: twee identieke uitkragende balken met de tips op elkaar
         (a/b) en een contact-patchtest met twee blokken (c-f), met
         contact_algo STANDARD en PENALISATION

Toelichting, bronnen en interpretatie: doc_niet_lineair.md.
"""
import math
from verif_lib import (Case, Check, Model, hexmesh, quadmesh, box,
                       rect, HEX_FACE)

GROUP = "Niet-lineair statisch"
# Zoals Mecway's samples (PipeClip): vaste stap 0,1 s. De bridge rekent
# statisch Mecway's stappen plus de knikken van de lasttabellen
# (bridge_to_aster._mecway_static_times); zie NL-20.
TS = {"timeperiod": "1 s", "stepsize": "0.1 s"}


def _timesteps(t_end):
    d = dict(TS)
    d["timeperiod"] = "%g s" % t_end
    return d


def _t(r, t):
    """t, als die tijdstap in de resultaten staat. Results.step() neemt de
    dichtstbijzijnde tijdstap; stopt Code-Aster eerder (BRIDGE_ONVOLLEDIG),
    dan zou een check stil een eerder tijdstip vergelijken."""
    near = min(r.times(), key=lambda x: abs(x - t))
    if abs(near - t) > 1e-6 * max(1.0, abs(t)):
        raise ValueError("tijdstip %g niet bereikt (laatste %g)"
                         % (t, r.times()[-1]))
    return t


def _history(tag, points, unit):
    """<tag time="t s">v unit</tag> voor elk (t, v)."""
    return "".join('<{0} time="{1:g} s">{2:.12g} {3}</{0}>'.format(
        tag, t, v, unit) for t, v in points)


# ------------------------------------------------------------------
# NL-01 Trekstaaf, bilineaire isotrope versteviging
# ------------------------------------------------------------------
# Homogene eenassige trek: symmetrievlakken x=0, y=0, z=0 (dwarscontractie
# vrij), opgelegde verlenging u(t) op x=L.
# ET1 is Mecway's tangentmodulus. Mecway (CCX, headless gemeten) rekent die
# als plastische hellingsmodulus H = d sigma / d eps_p, niet als helling in
# totale rek: bij tangentmodulus 100 GPa gaf CCX sigma = 915,8 MPa bij 1%
# rek (H-lezing 914,5, totale-rek-lezing 1181). De referentie volgt Mecway.
E1, SY1, ET1 = 210e9, 355e6, 10e9          # Pa
L1, A1 = 0.100, 0.010                       # m; doorsnede A1 x A1
U1 = [(0.0, 0.0), (1.0, 0.10e-3), (2.0, 1.00e-3), (3.0, 0.85e-3)]


def _u1(t):
    for (t0, u0), (t1, u1) in zip(U1, U1[1:]):
        if t0 <= t <= t1:
            return u0 + (u1 - u0) * (t - t0) / (t1 - t0)
    return U1[-1][1]


def _bar_state(t):
    """
    Analytische toestand van de staaf op tijd t (eenassig, homogeen).
    Code-Aster rekent plastische volumes met DEFORMATION='GDEF_LOG'
    (bridge_to_aster._deformation_for): additieve logaritmische rek en de
    daaraan duale spanning T; bij eenassige trek zonder rotatie is T de
    Kirchhoff-spanning tau = J sigma. Bilineair isotroop met Mecway's
    tangentmodulus als plastische modulus H: tau = SY + H p, p = eps_log -
    tau/E (helling in totale rek E H/(E + H)), elastisch ontlasten met
    helling E (in log-rek). Kracht:
    F = sigma A = tau A0 / lambda (A = A0 lambda_dwars^2, J = lambda
    lambda_dwars^2). Returns dict met eps (technisch), eps_log, tau, sigma
    (Cauchy), F, p (cumulatieve plastische rek) en F_klein (dezelfde wet
    met technische rek en F = sigma A0: kleine-rektheorie).
    """
    # tijdpunten: de knikken van de lasthistorie plus t (de spannings-
    # toestand hangt alleen af van het rekpad; per lineair stuk is een stap
    # exact bij eenassige lineaire versteviging)
    pts = [tt for tt, _u in U1 if tt < t] + [t]

    def integrate(measure):
        tau_y, p, tau, e_prev = SY1, 0.0, 0.0, 0.0
        H = ET1                          # Mecway: plastische modulus
        for ti in pts[1:]:
            e = measure(_u1(ti) / L1)
            trial = tau + E1 * (e - e_prev)
            if abs(trial) > tau_y:       # radial return
                dp = (abs(trial) - tau_y) / (E1 + H)
                p += dp
                tau_y += H * dp
                tau = math.copysign(tau_y, trial)
            else:
                tau = trial
            e_prev = e
        return tau, p, e_prev
    tau, p, e_log = integrate(lambda e: math.log(1.0 + e))
    s_small, _p, _e = integrate(lambda e: e)
    e = _u1(t) / L1
    nu = 0.3
    # J = exp(spoor log-rek): plastisch volumebehoudend, elastisch
    # (1 - 2 nu) tau / E bij eenassige spanning
    j = math.exp(tau * (1 - 2 * nu) / E1)
    A0 = A1 * A1
    return {"eps": e, "eps_log": e_log, "tau": tau, "sigma": tau / j,
            "F": tau * A0 / (1.0 + e), "p": p, "F_klein": s_small * A0}


def build_nl01():
    m = Model("L30", timesteps=_timesteps(3.0))
    m.elset("Staaf", "Staal")
    g = hexmesh(m, "Staaf", 2, 1, 1, box(0, L1, 0, A1, 0, A1), order=2)
    m.mat("Staal", '<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
          'poissonratio="0.3" />',
          '<plastic type="BilinearIsotropic" yieldstrength="%g Pa" '
          'tangentmodulus="%g Pa" />' % (SY1, ET1))
    for name, side, ax in (("SymX", "u0", "x"), ("SymY", "v0", "y"),
                           ("SymZ", "w0", "z")):
        m.node_selection(name, sorted(g["nodes"][side]))
        d = dict((a, 1 if a == ax else 0) for a in "xyz")
        m.add('<displacement selection="{0}"><value>0 mm</value><x>{x}</x>'
              '<y>{y}</y><z>{z}</z></displacement>'.format(name, **d))
    m.node_selection("Trek", sorted(g["nodes"]["u1"]))
    m.add('<displacement selection="Trek">{0}<x>1</x><y>0</y><z>0</z>'
          '</displacement>'.format(_history(
              "value", [(t, u * 1e3) for t, u in U1], "mm")))
    return m


MID1 = (L1 / 2, A1 / 2, A1 / 2)


# NL-20: dezelfde staaf met Mecway-stap 0,4 s over 3 s: de knikken van de
# lasttabel (t = 1 en 2) vallen tussen de stappen en worden extra rekenstappen
TIMES20 = [0.4, 0.8, 1.0, 1.2, 1.6, 2.0, 2.4, 2.8, 3.0]


def build_nl20():
    m = build_nl01()
    m.timesteps = {"timeperiod": "3 s", "stepsize": "0.4 s"}
    return m


def _times_dev(r, expected):
    """Grootste verschil tussen de uitvoertijden (zonder t = 0) en
    expected; 1e9 bij een ander aantal."""
    got = [t for t in r.times() if t > 0.0]
    if len(got) != len(expected):
        return 1.0e9
    return max(abs(a - b) for a, b in zip(got, expected))


def _nl01_checks(load=True, known=None):
    """Tolerantie 0,2%: homogene toestand (elk element exact, radial return
    exact bij eenassige lineaire versteviging); over blijven de
    Newton-tolerantie (RESI_GLOB_RELA 1e-5) en, voor sigma, J - 1 < 0,1%.
    load=False: alleen het ontlasten (t = 3)."""
    src_f = ("eenassig, log-rek: F = A0 tau/(1+e), tau = SY + H p, "
             "H = Mecway tangentmodulus (CCX-gedrag)")
    out = []
    steps = ((1.0, "elastisch"), (1.5, "plastisch"), (2.0, "plastisch"),
             (3.0, "ontlast")) if load else ((3.0, "ontlast"),)
    for t, what in steps:
        s = _bar_state(t)
        out.append(Check("F t=%g (%s)" % (t, what),
                         (lambda tt: lambda r: r.total(
                             "reactionforcex", "Trek", time=_t(r, tt)))(t),
                         ref=s["F"], tol=0.002, unit="N", source=src_f,
                         known=known if t == 3.0 else None))
    s2 = _bar_state(2.0)
    if load:
        out.append(Check("sigma_xx t=2", lambda r: r.at(
            "stressxx", MID1, time=_t(r, 2.0)),
            ref=s2["sigma"], tol=0.002, unit="Pa",
            source="sigma = tau/J (J = exp((1-2nu) tau/E))"))
        out.append(Check("p t=2", lambda r: r.at(
            "equivalentplasticstrain", MID1, time=_t(r, 2.0)),
            ref=s2["p"], tol=0.002, unit="-",
            source="p = eps_log - tau/E (V1 van VMIS_ISOT_LINE)"))
    s3 = _bar_state(3.0)
    out.append(Check("p t=3 (ontlast)", lambda r: r.at(
        "equivalentplasticstrain", MID1, time=_t(r, 3.0)),
        ref=s3["p"], tol=0.002, unit="-",
        source="p blijft gelijk bij elastisch ontlasten", known=known))
    return out


# ------------------------------------------------------------------
# NL-02 Ingeklemde balk, grote doorbuiging (elastica)
# ------------------------------------------------------------------
def elastica(alpha, n=4000):
    """
    Ingeklemde, onrekbare Euler-balk met een eindlast P loodrecht op de
    onvervormde as en van vaste richting; alpha = P L^2 / EI.
    theta'' = -alpha cos(theta), theta(0) = 0, theta'(1) = 0 (s = x/L).
    Schieten op theta'(0) (bisectie) met RK4. Returns (v/L, u/L, theta_tip):
    doorbuiging loodrecht op de as, verkorting langs de as, tiprotatie.
    Literatuur (Mattiasson 1981, tabel 1; Bisshopp & Drucker 1945):
    alpha=1: v/L 0.30172, u/L 0.05643; alpha=2: 0.49346, 0.16064;
    alpha=3: 0.60325, 0.25442.
    """
    def run(k0):
        h = 1.0 / n
        y = [0.0, k0, 0.0, 0.0]          # theta, theta', x, z

        def f(y):
            return [y[1], -alpha * math.cos(y[0]), math.cos(y[0]),
                    math.sin(y[0])]
        for _ in range(n):
            k1 = f(y)
            k2 = f([y[i] + 0.5 * h * k1[i] for i in range(4)])
            k3 = f([y[i] + 0.5 * h * k2[i] for i in range(4)])
            k4 = f([y[i] + h * k3[i] for i in range(4)])
            y = [y[i] + h / 6.0 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i])
                 for i in range(4)]
        return y
    lo, hi = 0.0, alpha
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if run(mid)[1] < 0.0:
            lo = mid
        else:
            hi = mid
    y = run(0.5 * (lo + hi))
    return y[3], 1.0 - y[2], y[0]


L2 = 1.0
ALPHAS = (1.0, 2.0, 3.0)                    # PL^2/EI op t = 1, 2, 3 s
# volume: b x h = 10 x 10 mm, nu = 0 (geen dwarscontractie-effecten bij de
# inklemming; de elastica hangt niet af van nu)
B2V, H2V = 0.010, 0.010
EI2V = E1 * B2V * H2V ** 3 / 12.0
# schaal: strook 50 mm breed, 10 mm dik
B2S, T2S = 0.050, 0.010
EI2S = E1 * B2S * T2S ** 3 / 12.0


def _elastic_mat(m, name, nu, extra=()):
    m.mat(name, '<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
          'poissonratio="%g" />' % nu, *extra)


def _tip_force(m, sel, ei):
    pts = [(0.0, 0.0)] + [(float(i + 1), -a * ei / L2 ** 2)
                          for i, a in enumerate(ALPHAS)]
    m.add('<force selection="{0}"><x>0 N</x><y>0 N</y>{1}</force>'.format(
        sel, _history("z", pts, "N")))


def build_nl02_volume():
    m = Model("L30", timesteps=_timesteps(3.0))
    m.elset("Balk", "Staal0")
    g = hexmesh(m, "Balk", 20, 1, 2,
                box(0, L2, 0, B2V, -H2V / 2, H2V / 2), order=2)
    _elastic_mat(m, "Staal0", 0.0)
    m.node_selection("Inklemming", sorted(g["nodes"]["u0"]))
    m.node_selection("Tip", sorted(g["nodes"]["u1"]))
    m.add('<fixed selection="Inklemming" />')
    _tip_force(m, "Tip", EI2V)
    return m


def build_nl02_shell():
    m = Model("L30", timesteps=_timesteps(3.0))
    m.elset("Strook", "Plaat10")
    g = quadmesh(m, "Strook", 20, 1, rect(0, L2, 0, B2S), order=2)
    _elastic_mat(m, "Plaat10", 0.0,
                 ('<geometric type="Plate" thickness="%g mm" />'
                  % (T2S * 1e3),))
    m.node_selection("Inklemming", sorted(g["nodes"]["u0"]))
    m.node_selection("Tip", sorted(g["nodes"]["u1"]))
    m.add('<fixed selection="Inklemming" />')
    _tip_force(m, "Tip", EI2S)
    return m


def _nl02_checks(b):
    src = ("elastica, Bisshopp & Drucker (1945) / Mattiasson (1981); "
           "numeriek (RK4 + schieten)")
    out = []
    tip = (L2, b / 2.0, 0.0)
    for i, a in enumerate(ALPHAS):
        v, u, _th = elastica(a)
        t = float(i + 1)
        out.append(Check("v/L PL2/EI=%g" % a,
                         (lambda tt: lambda r: -r.at(
                             "displz", tip, time=_t(r, tt)) / L2)(t),
                         ref=v, tol=0.01, unit="-", source=src))
        out.append(Check("u/L PL2/EI=%g" % a,
                         (lambda tt: lambda r: -r.at(
                             "displx", tip, time=_t(r, tt)) / L2)(t),
                         ref=u, tol=0.01, unit="-", source=src))
    return out


# ------------------------------------------------------------------
# NL-03 Contact: twee uitkragende balken met de tips op elkaar
# ------------------------------------------------------------------
# Bovenste balk x in [0, L], z in [0, h]; onderste balk x in [0, L + e],
# bovenvlak z = -g0 (1 - x/L): het raakt de bovenste balk alleen op x = L
# (geen spleet daar), naar de inklemming toe loopt een spleet op tot g0.
# Beide ingeklemd op x = 0, wrijvingsloos contact (bovenste balk slave,
# laatste 4 elementen; onderste master, x >= L - 30 mm .. L + e). Last P op
# het eindvlak van de bovenste balk. Zo is het contact een lijn op x = L
# en de status elders eenduidig open (bij twee balken die over de hele
# lengte zonder spleet op elkaar liggen is de contactdruk overal ~0 behalve
# aan de tip: dat gaf in Code-Aster een singuliere LAGS_C, zie de docs).
# nu = 0: geen dwarscontractie-effecten (plaatwerking b = 2h, inklemming),
# die balktheorie niet kent (met nu = 0,3 gaf het model 1,35% minder
# doorbuiging, met nu = 0 0,01%).
L3, B3, H3, P3 = 0.100, 0.010, 0.005, 10.0
N3, E3, GAP3 = 20, 0.010, 0.5e-3            # elementen op L, overstek, spleet
I3 = B3 * H3 ** 3 / 12.0
NU3 = 0.0
G3 = E1 / (2 * (1 + NU3))
KAPPA = 5.0 / 6.0
KN_STIF = 1.0e13                            # Pa/m (10000 GPa/m)


def _compliance():
    """Doorbuiging per newton op x = L van een ingeklemde balk
    (Timoshenko: L^3/3EI + L/kappa G A; Roark tabel 8.1 geval 1a)."""
    return L3 ** 3 / (3 * E1 * I3) + L3 / (KAPPA * G3 * B3 * H3)


def build_nl03(kn=KN_STIF, swap=False):
    m = Model("L30", timesteps=_timesteps(1.0))
    m.elset("Onder", "Staal")
    n_lo = N3 + int(round(E3 / (L3 / N3)))
    l_lo = L3 + E3

    def lower(u, v, w):
        x = u * l_lo
        return (x, v * B3, -GAP3 * (1.0 - x / L3) - (1.0 - w) * H3)
    lo = hexmesh(m, "Onder", n_lo, 1, 1, lower, order=2)
    m._index = {}          # bovenste balk: eigen knopen
    m.elset("Boven", "Staal")
    up = hexmesh(m, "Boven", N3, 1, 1, box(0, L3, 0, B3, 0, H3), order=2)
    _elastic_mat(m, "Staal", NU3)
    m.node_selection("InklemmingOnder", sorted(lo["nodes"]["u0"]))
    m.node_selection("InklemmingBoven", sorted(up["nodes"]["u0"]))
    m.node_selection("TipBoven", sorted(up["nodes"]["u1"]))
    m.face_selection("ContactOnder", [(lo["elems"][(i, 0, 0)], HEX_FACE["w1"])
                                      for i in range(N3 - 6, n_lo)])
    m.face_selection("ContactBoven", [(up["elems"][(i, 0, 0)], HEX_FACE["w0"])
                                      for i in range(N3 - 4, N3)])
    m.add('<fixed selection="InklemmingOnder" />')
    m.add('<fixed selection="InklemmingBoven" />')
    m.add('<force selection="TipBoven"><x>0 N</x><y>0 N</y>{0}</force>'
          .format(_history("z", [(0.0, 0.0), (1.0, -P3)], "N")))
    ms = ("ContactBoven", "ContactOnder")
    if not swap:
        ms = ms[::-1]
    m.add('<contact2 selectionmaster="%s" selectionslave="%s" '
          'type="unilateralelastic"><tolerance>0 m</tolerance>'
          '<normalstiffness>%g GPa/m</normalstiffness>'
          '<tangentialstiffness>0 GPa/m</tangentialstiffness>'
          '<frictioncoefficient>0</frictioncoefficient></contact2>'
          % (ms[0], ms[1], kn / 1e9))
    return m


TIP_UP = (L3, 0.0, H3 / 2.0)               # as van de bovenste balk, x = L
TIP_LO = (L3, 0.0, -H3 / 2.0)              # as van de onderste balk, x = L


def _nl03_checks(rigid=True, known=None):
    """Tolerantie 0,5%: balktheorie (Timoshenko, afschuiving 0,1%) tegen een
    3D-model met L/h = 20 en nu = 0, discretisatie 20 hex20 over de lengte
    en 1 over de dikte (lineaire buigspanning exact), lokale vervorming
    onder de contactlijn (< 1e-4 relatief)."""
    c = _compliance()
    out = [Check("tip gemiddeld", lambda r: -0.5 * (
        r.at("displz", TIP_UP) + r.at("displz", TIP_LO)),
        ref=P3 * c / 2.0, tol=0.005, unit="m", known=known,
        source="(w_b + w_o)/2 = P C/2, C = L^3/3EI + L/kGA; geldt voor "
               "elke contactwet (gelijke balken, inwendige contactkracht)")]
    if rigid:
        out += [Check("tip boven", lambda r: -r.at("displz", TIP_UP),
                      ref=P3 * c / 2.0, tol=0.005, unit="m", known=known,
                      source="(P - R) C met R = P/2"),
                Check("contactkracht", lambda r: r.total(
                    "reactionforcez", "InklemmingOnder"),
                      ref=P3 / 2.0, tol=0.005, unit="N", known=known,
                      source="R = P/2: gelijke stijfheid in het contactpunt "
                             "(reactie inklemming onderste balk)")]
    return out


# ------------------------------------------------------------------
# NL-03c..f Contact-patchtest: twee blokken onder gelijkmatige druk
# ------------------------------------------------------------------
# Onderblok 20 x 20 x 10 mm (2 x 2 x 1 hex20), bovenblok idem met 3 x 3 x 1
# hex20 (niet-passende meshes op het contactvlak). Symmetrievlakken x = 0
# en y = 0 voor beide blokken, onderblok z = 0 aan de onderkant; kracht F
# (gelijkmatig verdeeld) op de bovenkant. Eenassige druk p = F/A in beide
# blokken, contactdruk p overal.
A4, H4, F4 = 0.020, 0.010, 4000.0          # m, m, N  -> p = 10 MPa
P4 = F4 / A4 ** 2
KN4 = 1.0e13                                # Pa/m
NU4 = 0.3
# Contactintegratie via een #ASTER-ZONE-regel in Mecway's custom model
# definition (bridge_custom.py); zonder: INTEGRATION='AUTO'.
NCOTES = ("<ccxmodeldefinition>** ASTER-ZONE INTEGRATION='NCOTES'"
          "</ccxmodeldefinition>")


def build_nl03_patch(kn=KN4, n_lo=2, extra=None):
    m = Model("L30", timesteps=_timesteps(1.0))
    m.elset("Onderblok", "Staal")
    lo = hexmesh(m, "Onderblok", n_lo, n_lo, 1, box(0, A4, 0, A4, -H4, 0),
                 order=2)
    m._index = {}          # bovenblok: eigen knopen
    m.elset("Bovenblok", "Staal")
    up = hexmesh(m, "Bovenblok", 3, 3, 1, box(0, A4, 0, A4, 0, H4), order=2)
    _elastic_mat(m, "Staal", NU4)
    m.node_selection("SymX", sorted(lo["nodes"]["u0"] | up["nodes"]["u0"]))
    m.node_selection("SymY", sorted(lo["nodes"]["v0"] | up["nodes"]["v0"]))
    m.node_selection("Bodem", sorted(lo["nodes"]["w0"]))
    for name, ax in (("SymX", "x"), ("SymY", "y"), ("Bodem", "z")):
        d = dict((a, 1 if a == ax else 0) for a in "xyz")
        m.add('<displacement selection="{0}"><value>0 mm</value><x>{x}</x>'
              '<y>{y}</y><z>{z}</z></displacement>'.format(name, **d))
    m.face_selection("Bovenkant", up["faces"]["w1"])
    m.face_selection("ContactOnder", lo["faces"]["w1"])
    m.face_selection("ContactBoven", up["faces"]["w0"])
    m.add('<force selection="Bovenkant"><x>0 N</x><y>0 N</y>{0}</force>'
          .format(_history("z", [(0.0, 0.0), (1.0, -F4)], "N")))
    m.add('<contact2 selectionmaster="ContactOnder" selectionslave='
          '"ContactBoven" type="unilateralelastic"><tolerance>0 m</tolerance>'
          '<normalstiffness>%g GPa/m</normalstiffness>'
          '<tangentialstiffness>0 GPa/m</tangentialstiffness>'
          '<frictioncoefficient>0</frictioncoefficient></contact2>'
          % (kn / 1e9))
    if extra:
        m.add(extra)
    return m


def _at_body(r, var, pt, upper):
    """var in de knoop op pt van het onderste (eerst gemaakte) of het
    bovenste lichaam: op het contactvlak liggen twee knopen op dezelfde
    plaats, Results.at() kiest daar willekeurig."""
    nids = [i + 1 for i, q in enumerate(r.model.nodes)
            if sum((q[k] - pt[k]) ** 2 for k in range(3)) < 1e-20]
    return r.node(var, max(nids) if upper else min(nids))


def _nl03_patch_checks(penalty):
    """Tolerantie 0,5%: de toestand is homogeen en exact te representeren;
    een contactformulering die de patchtest haalt, geeft hem tot op de
    Newton-tolerantie. Bovenkant: hoek (A, A) en een punt dat niet op een
    knoop van het onderblok ligt."""
    el = P4 * H4 / E1                       # indrukking per blok
    pen = P4 / KN4 if penalty else 0.0
    src = "eenassige druk: p H / E per blok"
    out = [Check("w contactvlak onder", lambda r: -_at_body(
        r, "displz", (A4, A4, 0.0), False), ref=el, tol=0.005, unit="m",
        source=src)]
    for name, pt in (("w boven (A,A)", (A4, A4, H4)),
                     ("w boven (A/3,2A/3)", (A4 / 3, 2 * A4 / 3, H4))):
        out.append(Check(name, (lambda q: lambda r: -r.at("displz", q))(pt),
                         ref=2 * el + pen, tol=0.005, unit="m",
                         source=src + (" + p/kn (penalty)" if penalty
                                       else "")))
    if penalty:
        out.append(Check("penetratie", lambda r: (
            _at_body(r, "displz", (A4, A4, 0.0), False) -
            _at_body(r, "displz", (A4, A4, 0.0), True)),
            ref=pen, tol=0.005, unit="m",
            source="contactdruk = kn x penetratie (Mecway normalstiffness, "
                   "COEF_PENA_CONT)"))
    return out


TESTS = [
    Case("NL-01", GROUP, "Trekstaaf, bilineaire isotrope versteviging, "
         "ontlasten", "nonlin_static_3d", build_nl01,
         _nl01_checks(),
         note="Standaardinstellingen. Homogeen: elk element is exact."),
    Case("NL-01b", GROUP, "Trekstaaf, ontlasten (RELA 1e-6 of MAXI 0,05 N)",
         "nonlin_static_3d", build_nl01, _nl01_checks(load=False),
         settings={"convergence_resi_rela": 1e-6,
                   "convergence_criterion": "RELA_OF_MAXI",
                   "convergence_resi_maxi": 0.05},
         note="Als NL-01 met de Code-Aster-standaard RESI_GLOB_RELA 1e-6: "
              "alleen RELA stagneert bij het ontlasten (GDEF_LOG) op "
              "~2e-6 / ~1e-2 N; met RELA_OF_MAXI (VERIF='AU_MOINS_UN') "
              "rekent hij door."),
    Case("NL-20", GROUP, "Trekstaaf, Mecway-stap 0,4 s met knikken van de "
         "lasttabel ertussen", "nonlin_static_3d", build_nl20,
         [Check("uitvoertijden = Mecway-stappen + knikken",
                lambda r: _times_dev(r, TIMES20), ref=0.0, tol_abs=1e-9,
                unit="s", source="Mecway: stap 0,4 s tot 3 s; knikken "
                "t = 1, 2 als extra rekenstap")] +
         [c for c in _nl01_checks() if "t=1.5" not in c.name],
         note="Als NL-01 met <timesteps stepsize=\"0.4 s\">: rekenstappen "
              "0,4 .. 2,8, 3 plus de knikken 1 en 2; het lastpad blijft "
              "exact."),
    Case("NL-02a", GROUP, "Ingeklemde balk, grote doorbuiging (hex20)",
         "nonlin_static_3d", build_nl02_volume, _nl02_checks(B2V),
         note="Elastica; volume-elementen, GREEN_LAGRANGE."),
    Case("NL-02b", GROUP, "Ingeklemde balk, grote doorbuiging (COQUE_3D)",
         "nonlin_static_3d", build_nl02_shell, _nl02_checks(B2S),
         general={"elem_shell": "COQUE_3D"},
         note="Elastica; quad8 -> COQUE_3D (QUAD9), GROT_GDEP."),
    Case("NL-03a", GROUP, "Contact: twee balken, tips op elkaar (STANDARD)",
         "nonlin_static_3d", build_nl03, _nl03_checks(known="KNOWN_BUGS 43"),
         settings={"contact_algo": "STANDARD"},
         note="Lagrange-contact (standaard), wrijvingsloos. Lijncontact op "
              "hex20: Code-Aster stopt met MECANONLINE9_4 (pivot op LAGS_C); "
              "gebruik PENALISATION (NL-03b)."),
    Case("NL-03b", GROUP, "Contact: twee balken, tips op elkaar "
         "(PENALISATION, kn = 1e13 Pa/m)", "nonlin_static_3d", build_nl03,
         _nl03_checks(), settings={"contact_algo": "PENALISATION"},
         note="Penalty met een stijve normalstiffness."),
    Case("NL-03c", GROUP, "Contact-patchtest (STANDARD)",
         "nonlin_static_3d", build_nl03_patch, _nl03_patch_checks(False),
         settings={"contact_algo": "STANDARD"},
         note="Niet-passende hex20-meshes; de bridge zet bij een "
              "kwadratisch slave-vlak INTEGRATION='NCOTES' (met 'AUTO' "
              "1,5..4,6% fout)."),
    Case("NL-03d", GROUP, "Contact-patchtest (PENALISATION)",
         "nonlin_static_3d", build_nl03_patch, _nl03_patch_checks(True),
         settings={"contact_algo": "PENALISATION"},
         note="kn = 1e13 Pa/m: penetratie p/kn = 1 um, even groot als de "
              "elastische indrukking van een blok."),
    Case("NL-03e", GROUP, "Contact-patchtest (STANDARD, NCOTES)",
         "nonlin_static_3d", lambda: build_nl03_patch(extra=NCOTES),
         _nl03_patch_checks(False), settings={"contact_algo": "STANDARD"},
         note="Als NL-03c met #ASTER-ZONE INTEGRATION='NCOTES' (nu gelijk "
              "aan de standaard van de bridge)."),
    Case("NL-03f", GROUP, "Contact-patchtest (PENALISATION, NCOTES)",
         "nonlin_static_3d", lambda: build_nl03_patch(extra=NCOTES),
         _nl03_patch_checks(True), settings={"contact_algo": "PENALISATION"},
         note="Als NL-03d met #ASTER-ZONE INTEGRATION='NCOTES' (nu gelijk "
              "aan de standaard van de bridge)."),
]
