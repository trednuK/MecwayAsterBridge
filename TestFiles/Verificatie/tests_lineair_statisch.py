# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Lineair statisch (Mecway S30 -> MECA_STATIQUE). Referenties: balktheorie,
Roark's Formulas for Stress and Strain (Young & Budynas, 7e druk),
Timoshenko & Woinowsky-Krieger (Theory of Plates and Shells, 2e druk),
Timoshenko & Goodier (Theory of Elasticity, 3e druk) en NAFEMS LE1.
Toelichting per test: doc_lineair_statisch.md.

Tolerantie in een mesh-convergentiereeks: het fijnste mesh krijgt tol_f =
modelfout van de analytische theorie (bijv. 3D-inklemming t.o.v. de
balktheorie) + onzekerheid van de referentie (afronding) + ruim de
discretisatiefout van dat mesh (Richardson uit de reeks); zie de doc.
Een grover mesh krijgt tol_f * (h / h_f)^p, met p de verwachte
convergentie-orde van de grootheid, begrensd op 50% (een grof mesh is
dan alleen een orde-van-grootte-controle). Zo controleert elk mesh dat
de fout past bij convergentie naar de referentie.
"""
import math
from verif_lib import Case, Check, Model, linemesh, hexmesh, quadmesh, box, \
    rect

GROUP = "Lineair statisch"
E, NU = 210e9, 0.3
G = E / (2 * (1 + NU))
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')


def _steel(m, name="Staal", extra=()):
    m.mat(name, STEEL, *extra)


def _mean(r, var, sel):
    """Gemiddelde van var over een knoopselectie."""
    d = r.step()[var]
    nids = r.model.nodesel[sel]
    return sum(d[n] for n in nids) / float(len(nids))


def _tol(tol_f, h, h_f, p):
    """Tolerantie van een mesh met elementgrootte h in een reeks met
    fijnste elementgrootte h_f (zie de kop van deze module)."""
    return max(tol_f, min(0.5, tol_f * (float(h) / h_f) ** p))


# ------------------------------------------------------------------
# LS-01 Ingeklemde balk, eindlast (POU_D_E)
# ------------------------------------------------------------------
L1, D1, P1, N1 = 1.0, 0.020, 100.0, 10
I1 = math.pi * D1 ** 4 / 64.0


def build_ls01():
    m = Model("S30")
    m.elset("Balk", "Rond20")
    _eids, nids = linemesh(m, "Balk", N1, (0, 0, 0), (L1, 0, 0))
    m.mat("Rond20", '<geometric type="CircularBar" roundod="20 mm" />',
          STEEL)
    m.node_selection("Inklemming", [nids[0]])
    m.node_selection("Tip", [nids[-1]])
    m.add('<fixed selection="Inklemming" />')
    m.add('<force selection="Tip"><x>0 N</x><y>0 N</y><z>-%g N</z></force>'
          % P1)
    return m


TESTS = [
    Case("LS-01", GROUP, "Ingeklemde balk, eindlast (balkelementen)",
         "lin_static_3d", build_ls01,
         [Check("doorbuiging tip", lambda r: -r.at("displz", (L1, 0, 0)),
                ref=P1 * L1 ** 3 / (3 * E * I1), tol=1e-3, unit="m",
                source="PL^3/3EI (Roark tabel 8.1 geval 1a)"),
          Check("rotatie tip", lambda r: abs(r.at("roty", (L1, 0, 0))),
                ref=P1 * L1 ** 2 / (2 * E * I1), tol=1e-3, unit="rad",
                source="PL^2/2EI (Roark tabel 8.1 geval 1a)"),
          Check("reactiekracht Z", lambda r: r.total("reactionforcez",
                                                       "Inklemming"),
                ref=P1, tol=1e-6, unit="N", source="evenwicht")],
         note="Euler-Bernoulli-balk is exact voor een eindlast."),
]


# ------------------------------------------------------------------
# LS-02 Ingeklemde balk met volume-elementen, eindlast als traction
# ------------------------------------------------------------------
# 1 x 0,1 x 0,1 m, x = as, belasting -Z. Doorsnede n x n elementen,
# lengte 10 n (kubusvormige elementen).
L2, B2, H2, P2 = 1.0, 0.1, 0.1, 10.0e3
A2 = B2 * H2
I2 = B2 * H2 ** 3 / 12.0
K2 = 5.0 / 6.0
W_BEND2 = P2 * L2 ** 3 / (3 * E * I2)
W_SHEAR2 = P2 * L2 / (K2 * G * A2)
W2 = W_BEND2 + W_SHEAR2                       # Timoshenko-balk
X2S = 0.2                                     # 2h van de inklemming
SIG2 = P2 * (L2 - X2S) * (H2 / 2.0) / I2      # Mc/I


def build_ls02(n, order):
    def build():
        m = Model("S30")
        m.elset("Balk", "Staal")
        mesh = hexmesh(m, "Balk", 10 * n, n, n, box(0, L2, 0, B2, 0, H2),
                       order=order)
        _steel(m)
        m.face_selection("Inklemming", mesh["faces"]["u0"])
        m.face_selection("Eindvlak", mesh["faces"]["u1"])
        m.node_selection("InklemKnopen", sorted(mesh["nodes"]["u0"]))
        m.node_selection("TipKnopen", sorted(mesh["nodes"]["u1"]))
        m.add('<fixed selection="Inklemming" />')
        m.add('<traction selection="Eindvlak"><x>0 Pa</x><y>0 Pa</y>'
              '<z>-%g Pa</z></traction>' % (P2 / A2))
        return m
    return build


def _ls02_cases():
    out = []
    # (label, order, general, n-reeks, (tol_w, tol_sig) fijnste, p_w, p_sig)
    # Doorbuiging: modelfout 3D-inklemming t.o.v. Timoshenko ~ de
    # afschuifterm (0,8%), dus tol_w 1% voor kwadratische elementen en 2%
    # voor hex8 3D (+ ~1% discretisatie bij n = 16). p_w = 2: de
    # singuliere randen van de inklemming beperken de orde.
    # Spanning op x = 0,2 m: geen modelfout (Saint-Venant); hex8: nodale
    # (geextrapoleerde) spanning convergeert met O(h).
    series = [
        ("hex8 3D", 1, {"elem_hex8": "3D"}, (1, 2, 4, 8, 16), (0.02, 0.03),
         2, 1),
        ("hex8 LINE_QUAD", 1, {"elem_hex8": "LINE_QUAD"}, (1, 2, 4),
         (0.01, 0.005), 2, 2),
        ("hex20", 2, {}, (1, 2, 4), (0.01, 0.005), 2, 2),
    ]
    for label, order, general, ns, (tw, ts), pw, ps in series:
        nf = ns[-1]
        hf = H2 / nf
        for n in ns:
            h = H2 / n
            key = {"hex8 3D": "h8", "hex8 LINE_QUAD": "lq",
                   "hex20": "h20"}[label]
            out.append(Case(
                "LS-02-%s-n%d" % (key, n), GROUP,
                "Ingeklemde balk volume, %s, %dx%dx%d" % (label, 10 * n, n,
                                                           n),
                "lin_static_3d", build_ls02(n, order),
                [Check("doorbuiging tip (gem.)",
                       lambda r: -_mean(r, "displz", "TipKnopen"),
                       ref=W2, tol=_tol(tw, h, hf, pw), unit="m",
                       source="Timoshenko-balk PL^3/3EI + PL/kGA, k=5/6"),
                 Check("sigma_xx x=0,2 m boven",
                       lambda r: r.at("stressxx", (X2S, B2 / 2, H2)),
                       ref=SIG2, tol=_tol(ts, h, hf, ps), unit="Pa",
                       source="M c / I, M = P (L - x)"),
                 Check("reactiekracht Z",
                       lambda r: r.total("reactionforcez", "InklemKnopen"),
                       ref=P2, tol=1e-6, unit="N", source="evenwicht")],
                general=general, series="LS-02 " + label, h=h,
                note="Traction %g Pa op het eindvlak; inklemming: alle "
                     "knopen van het vlak vast." % (P2 / A2)))
    return out


TESTS += _ls02_cases()


# ------------------------------------------------------------------
# LS-03 Vierkante plaat, vrij opgelegd rondom, gelijkmatige druk
# ------------------------------------------------------------------
A3, T3, Q3 = 1.0, 0.01, 10.0e3
D3 = E * T3 ** 3 / (12 * (1 - NU ** 2))


def _navier(nmax=401):
    """Navier-reeks (Timoshenko & Woinowsky-Krieger par. 30): w en Mx in
    het midden van een vrij opgelegde vierkante plaat a x a."""
    sw = sm = 0.0
    for mm in range(1, nmax + 1, 2):
        for nn in range(1, nmax + 1, 2):
            s = (-1) ** ((mm + nn) // 2 - 1)
            den = mm * nn * (mm ** 2 + nn ** 2) ** 2
            sw += s / den
            sm += s * (mm ** 2 + NU * nn ** 2) / den
    alpha = 16.0 / math.pi ** 6 * sw
    beta = 16.0 / math.pi ** 4 * sm
    return alpha, beta


ALPHA3, BETA3 = _navier()
W3 = ALPHA3 * Q3 * A3 ** 4 / D3
SIG3 = 6 * BETA3 * Q3 * A3 ** 2 / T3 ** 2


def build_ls03(n, order, hard=True):
    def build():
        m = Model("S30")
        m.elset("Plaat", "Plaat10")
        mesh = quadmesh(m, "Plaat", n, n, rect(0, A3, 0, A3), order=order)
        m.mat("Plaat10", '<geometric type="Plate" thickness="%g m" />' % T3,
              STEEL)
        rand = set()
        for s in ("u0", "u1", "v0", "v1"):
            rand |= mesh["nodes"][s]
        m.node_selection("Rand", sorted(rand))
        m.face_selection("Bovenvlak", mesh["faces"])
        # vrij opgelegd ("hard", zoals Navier/Kirchhoff): alle randknopen
        # DX = DY = DZ = 0 en de rotatie om de normaal op de rand nul
        # (randen x = 0, a: DRX = 0; randen y = 0, a: DRY = 0); de rotatie
        # om de rand zelf is vrij. Mecway's pinned support is "gemiddelde
        # verplaatsing nul", daarom displacement per richting.
        for d in ("<x>1</x><y>0</y><z>0</z>", "<x>0</x><y>1</y><z>0</z>",
                  "<x>0</x><y>0</y><z>1</z>"):
            m.add('<displacement selection="Rand"><value>0 m</value>%s'
                  '</displacement>' % d)
        if hard:
            m.node_selection("RandX", sorted(mesh["nodes"]["u0"] |
                                             mesh["nodes"]["u1"]))
            m.node_selection("RandY", sorted(mesh["nodes"]["v0"] |
                                             mesh["nodes"]["v1"]))
            m.add('<noderotation selection="RandX"><value>0 rad</value>'
                  '<x>1</x><y>0</y><z>0</z></noderotation>')
            m.add('<noderotation selection="RandY"><value>0 rad</value>'
                  '<x>0</x><y>1</y><z>0</z></noderotation>')
        m.add('<surfacepressure selection="Bovenvlak"><normal>%g Pa</normal>'
              '</surfacepressure>' % Q3)
        return m
    return build


def _ls03_cases():
    out = []
    # (label, key, orde, n-reeks, tol_w, tol_sig fijnste, p_w, p_sig).
    # Referentie exact (Navier-reeks); COQUE_3D (Mindlin) heeft +0,06%
    # afschuifdoorbuiging t.o.v. Kirchhoff.
    series = [("DKT quad4", "dkt", 1, (4, 8, 16, 32), 0.002, 0.005, 2, 2),
              ("COQUE_3D quad8", "cq3", 2, (2, 4, 8, 16), 0.002, 0.01, 2,
               2)]
    for label, key, order, ns, tw, ts, pw, ps in series:
        hf = A3 / ns[-1]
        for n in ns:
            h = A3 / n
            mid = (A3 / 2, A3 / 2, 0)
            out.append(Case(
                "LS-03-%s-n%d" % (key, n), GROUP,
                "Vrij opgelegde plaat, druk, %s %dx%d" % (label, n, n),
                "lin_static_3d", build_ls03(n, order),
                [Check("doorbuiging midden",
                       lambda r: -r.at("displz", mid), ref=W3,
                       tol=_tol(tw, h, hf, pw), unit="m",
                       source="alpha q a^4/D, alpha = %.5f (Navier; TWK "
                              "tabel 8: 0,00406)" % ALPHA3),
                 Check("sigma midden bovenvlak (VM)",
                       lambda r: r.at("vonmisesu1", mid), ref=SIG3,
                       tol=_tol(ts, h, hf, ps), unit="Pa",
                       source="6 beta q a^2/t^2, beta = %.4f (Navier; TWK "
                              "tabel 8: 0,0479)" % BETA3),
                 Check("sigma midden ondervlak (VM)",
                       lambda r: r.at("vonmisesb", mid), ref=SIG3,
                       tol=_tol(ts, h, hf, ps), unit="Pa",
                       source="idem")],
                series="LS-03 " + label, h=h,
                note="Randknopen DX = DY = DZ = 0, rotatie om de randnormaal 0 "
                     "(hard vrij opgelegd); in het midden "
                     "is sigma_x = sigma_y en tau_xy = 0, dus von Mises = "
                     "|sigma_x|."))
    return out


TESTS += _ls03_cases()


# ------------------------------------------------------------------
# LS-04 Dikwandige cilinder, inwendige druk (Lame), vlakke rek
# ------------------------------------------------------------------
RA4, RB4, P4, LZ4 = 0.1, 0.2, 100.0e6, 0.01
A4 = P4 * RA4 ** 2 / (RB4 ** 2 - RA4 ** 2)
B4 = P4 * RA4 ** 2 * RB4 ** 2 / (RB4 ** 2 - RA4 ** 2)
SIGT4 = A4 + B4 / RA4 ** 2                    # sigma_theta binnenwand
SIGZ4 = 2 * NU * A4                           # vlakke rek
UR4 = (1 + NU) / E * ((1 - 2 * NU) * A4 * RA4 + B4 / RA4)


def _cyl(u, v, w):
    r = RA4 + u * (RB4 - RA4)
    t = v * math.pi / 2
    return (r * math.cos(t), r * math.sin(t), w * LZ4)


def build_ls04(nr, nt):
    def build():
        m = Model("S30")
        m.elset("Cilinder", "Staal")
        mesh = hexmesh(m, "Cilinder", nr, nt, 1, _cyl, order=2)
        _steel(m)
        f = mesh["faces"]
        m.face_selection("Binnenwand", f["u0"])
        m.face_selection("SymY0", f["v0"])          # vlak y = 0
        m.face_selection("SymX0", f["v1"])          # vlak x = 0
        m.face_selection("Einden", f["w0"] + f["w1"])
        m.add('<surfacepressure selection="Binnenwand"><normal>%g Pa'
              '</normal></surfacepressure>' % P4)
        m.add('<symmetry selection="SymY0"><x>0</x><y>1</y><z>0</z>'
              '</symmetry>')
        m.add('<symmetry selection="SymX0"><x>1</x><y>0</y><z>0</z>'
              '</symmetry>')
        m.add('<frictionless selection="Einden"><displacement>0 m'
              '</displacement></frictionless>')
        return m
    return build


def _ls04_cases():
    out = []
    ns = (1, 2, 4, 8)
    hf = (RB4 - RA4) / ns[-1]
    for n in ns:
        h = (RB4 - RA4) / n
        pin = (RA4, 0, 0)
        out.append(Case(
            "LS-04-h20-n%d" % n, GROUP,
            "Dikwandige cilinder, inwendige druk, hex20 %dx%dx1" % (n, 2 * n),
            "lin_static_3d", build_ls04(n, 2 * n),
            [Check("u_r binnenwand", lambda r: r.at("displx", pin), ref=UR4,
                   tol=_tol(0.001, h, hf, 3), unit="m",
                   source="Lame, vlakke rek (Timoshenko & Goodier par. 28)"),
             Check("sigma_theta binnenwand", lambda r: r.at("stressyy", pin),
                   ref=SIGT4, tol=_tol(0.005, h, hf, 1), unit="Pa",
                   source="p (b^2+a^2)/(b^2-a^2) (Lame)"),
             Check("sigma_zz binnenwand", lambda r: r.at("stresszz", pin),
                   ref=SIGZ4, tol=_tol(0.01, h, hf, 2), unit="Pa",
                   source="2 nu p a^2/(b^2-a^2) (vlakke rek)")],
            series="LS-04 hex20", h=h,
            note="Kwartmodel: symmetry op x = 0 en y = 0, frictionless op "
                 "beide eindvlakken (vlakke rek)."))
    return out


TESTS += _ls04_cases()


# ------------------------------------------------------------------
# LS-05 NAFEMS LE1, elliptisch membraan
# ------------------------------------------------------------------
# Binnenellips (x/2)^2 + y^2 = 1, buitenellips (x/3,25)^2 + (y/2,75)^2 = 1,
# dikte 0,1 m, trekdruk 10 MPa op de buitenrand, kwartmodel. Punt D = (2, 0).
T5, P5 = 0.1, 10.0e6
SIG5 = 92.7e6
PT_D = (2.0, 0.0, 0.0)


GU5, GV5 = 2.0, 1.5     # verdichting naar D (radiaal u^2, hoek v^1,5)


def _graded(n, g):
    """Stuksgewijs lineaire verdichting: knoop i/n -> (i/n)^g, daartussen
    lineair. Zo liggen middenknopen midden tussen de hoekknopen (een
    gladde afbeelding als u^2 zou ze naar het kwartpunt schuiven: een
    singulier element in D)."""
    def f(x):
        k = min(int(x * n), n - 1)
        a, b = (k / float(n)) ** g, ((k + 1) / float(n)) ** g
        return a + (b - a) * (x * n - k)
    return f


def _le1_map(nu, nv):
    """Afbeelding (u, v[, w]) -> (x, y, z): u van binnen- naar
    buitenellips, v de hoek 0..90 graden; beide verdicht naar punt D
    (u = v = 0), waar de spanning steil afneemt. nu, nv: aantal
    elementen in u en v."""
    gu, gv = _graded(nu, GU5), _graded(nv, GV5)

    def f(u, v, w=0.0):
        s = gu(u)
        t = gv(v) * math.pi / 2
        return ((2.0 + 1.25 * s) * math.cos(t),
                (1.0 + 1.75 * s) * math.sin(t), w * T5)
    return f


def build_ls05_shell(n):
    def build():
        m = Model("S30")
        m.elset("Membraan", "Plaat")
        le1 = _le1_map(n, 2 * n)
        mesh = quadmesh(m, "Membraan", n, 2 * n, lambda u, v: le1(u, v),
                        order=2)
        m.mat("Plaat", '<geometric type="Plate" thickness="%g m" />' % T5,
              STEEL)
        e = mesh["edges"]
        m.face_selection("Buitenrand", e["u1"])
        m.face_selection("SymY0", e["v0"])
        m.face_selection("SymX0", e["v1"])
        m.node_selection("Alle", range(1, len(m.nodes) + 1))
        m.add('<surfacepressure selection="Buitenrand"><normal>-%g Pa'
              '</normal></surfacepressure>' % P5)
        m.add('<symmetry selection="SymY0"><x>0</x><y>1</y><z>0</z>'
              '</symmetry>')
        m.add('<symmetry selection="SymX0"><x>1</x><y>0</y><z>0</z>'
              '</symmetry>')
        # membraan: uit het vlak vast (anders vrije DZ-starre beweging)
        m.add('<displacement selection="Alle"><value>0 m</value><x>0</x>'
              '<y>0</y><z>1</z></displacement>')
        return m
    return build


def build_ls05_solid(n):
    def build():
        m = Model("S30")
        m.elset("Membraan", "Staal")
        mesh = hexmesh(m, "Membraan", n, 2 * n, 1, _le1_map(n, 2 * n),
                       order=2)
        _steel(m)
        f = mesh["faces"]
        m.face_selection("Buitenrand", f["u1"])
        m.face_selection("SymY0", f["v0"])
        m.face_selection("SymX0", f["v1"])
        m.node_selection("Zvast", [m.node(*PT_D)])
        m.add('<surfacepressure selection="Buitenrand"><normal>-%g Pa'
              '</normal></surfacepressure>' % P5)
        m.add('<symmetry selection="SymY0"><x>0</x><y>1</y><z>0</z>'
              '</symmetry>')
        m.add('<symmetry selection="SymX0"><x>1</x><y>0</y><z>0</z>'
              '</symmetry>')
        m.add('<displacement selection="Zvast"><value>0 m</value><x>0</x>'
              '<y>0</y><z>1</z></displacement>')
        return m
    return build


def _ls05_cases():
    out = []
    ns = (2, 4, 8, 16)
    hf = 1.25 / ns[-1]
    for n in ns:
        h = 1.25 / n
        out.append(Case(
            "LS-05-cq3-n%d" % n, GROUP,
            "NAFEMS LE1, COQUE_3D quad8 %dx%d" % (n, 2 * n),
            "lin_static_3d", build_ls05_shell(n),
            [Check("sigma_yy in D (VM midden)",
                   lambda r: r.at("vonmisesm", PT_D), ref=SIG5,
                   tol=_tol(0.005, h, hf, 2), unit="Pa",
                   source="NAFEMS LE1: 92,7 MPa")],
            series="LS-05 COQUE_3D quad8", h=h,
            note="In D is sigma_xx = tau_xy = 0 (vrije rand, symmetrie), "
                 "dus von Mises = sigma_yy."))
    for n in ns:
        h = 1.25 / n
        out.append(Case(
            "LS-05-h20-n%d" % n, GROUP,
            "NAFEMS LE1, hex20 %dx%dx1" % (n, 2 * n),
            "lin_static_3d", build_ls05_solid(n),
            [Check("sigma_yy in D",
                   lambda r: r.at("stressyy", PT_D), ref=SIG5,
                   tol=_tol(0.005, h, hf, 2), unit="Pa",
                   source="NAFEMS LE1: 92,7 MPa (vlakke spanning)")],
            series="LS-05 hex20", h=h,
            note="Volumemodel, 1 element over de dikte, vlakken z vrij "
                 "(sigma_yy over de dikte constant: vlakke spanning)."))
    return out


TESTS += _ls05_cases()


# ------------------------------------------------------------------
# LS-06 Ingeklemde balk met een veer aan de tip (veerrichting)
# ------------------------------------------------------------------
# Balk als LS-01 (Euler, exact), zijlast P in Y aan de tip; een veer
# (Mecway Spring, line2) van de tip naar een vast punt. Langs Y:
# delta = P / (3EI/L^3 + k). Onder 45 graden in het XY-vlak: de tip
# beweegt (axiaal vrijwel star, EA/L = 6,6e7 N/m) alleen in Y, de veer
# rekt delta/sqrt(2) en levert in Y k delta / 2: delta = P/(3EI/L^3 + k/2).
K6, P6 = 1000.0, 10.0
KB6 = 3 * E * I1 / L1 ** 3


def build_ls06(angle_deg):
    def build():
        m = Model("S30")
        m.elset("Balk", "Rond20")
        _eids, nids = linemesh(m, "Balk", N1, (0, 0, 0), (L1, 0, 0))
        m.mat("Rond20", '<geometric type="CircularBar" roundod="20 mm" />',
              STEEL)
        a = math.radians(angle_deg)
        ground = m.node(L1 + 0.5 * math.sin(a), 0.5 * math.cos(a), 0.0)
        m.elset("Veer", "Veer1000")
        m.elem("Veer", "line2", [nids[-1], ground])
        m.mat("Veer1000", '<mechanical type="Spring" springconstant="%g N/m" />'
              % K6)
        m.node_selection("Inklemming", [nids[0]])
        m.node_selection("Grond", [ground])
        m.node_selection("Tip", [nids[-1]])
        m.add('<fixed selection="Inklemming" />')
        m.add('<fixed selection="Grond" />')
        m.add('<force selection="Tip"><x>0 N</x><y>%g N</y><z>0 N</z></force>'
              % P6)
        return m
    return build


TESTS += [
    Case("LS-06a", GROUP, "Ingeklemde balk met veer langs Y aan de tip",
         "lin_static_3d", build_ls06(0.0),
         [Check("doorbuiging tip Y", lambda r: r.at("disply", (L1, 0, 0)),
                ref=P6 / (KB6 + K6), tol=1e-3, unit="m",
                source="P / (3EI/L^3 + k), balk en veer parallel"),
          Check("veerkracht (reactie grond Y)", lambda r: -r.total(
              "reactionforcey", "Grond"),
                ref=K6 * P6 / (KB6 + K6), tol=1e-3, unit="N",
                source="k delta")],
         note="Veer langs de globale Y-as (KNOWN_BUGS 47: werkte voorheen "
              "alleen in globaal X)."),
    Case("LS-06b", GROUP, "Ingeklemde balk met veer onder 45 graden",
         "lin_static_3d", build_ls06(45.0),
         [Check("doorbuiging tip Y", lambda r: r.at("disply", (L1, 0, 0)),
                ref=P6 / (KB6 + K6 / 2.0), tol=2e-3, unit="m",
                source="P / (3EI/L^3 + k/2) (axiaal star, kleine "
                       "verplaatsing)")],
         note="Veer schuin in het XY-vlak: werkt langs de eigen as."),
]


# ------------------------------------------------------------------
# LS-07 Verlijmd contact tussen schalen (Mecway bonded contact, type
# bondedtie -> LIAISON_MAIL TYPE_RACCORD='COQUE', bridge_mesh._bonded)
# ------------------------------------------------------------------
# (a, b) Ingeklemde plaatstrook L x B x T (DKT quad4), eindlast P (-Z) op
# de vrije rand. (a): twee delen met eigen knopen, A (x = 0 .. L/2, 10 x 4)
# en B (x = L/2 .. L, 10 x 7), verlijmd langs de naad x = L/2 (slave =
# rand van B, master = de laatste rij schaalvlakken van A); (b): één mesh
# 20 x 4. Referentie: Euler-balk P L^3/(3EI) met E (niet E/(1-nu^2)): bij
# lineaire plaattheorie met vrije zijranden is M_y = 0, dus kromming
# kappa_y = -nu kappa_x en buigstijfheid per breedte E T^3/12 (balk); alleen
# de inklemming verhindert de anticlastische kromming over een strook ~B
# (B/L = 0,1), daardoor is de plaat iets stijver (FE: -1,0 %). Daarnaast
# Mecway 34 (eigen solver) op model (b): -9,41484e-4 m, rotatie
# 7,09010e-3 rad. Mecway zelf rekent model (a) niet bruikbaar: de eigen
# solver koppelt bij verlijmd contact met een schaalrand geen rotaties
# (tip 3,7e6 m, een mechanisme).
# (c, d, e) T-stuk: plaat AX x AY (XY-vlak, lange randen y = 0 en y = AY
# ingeklemd) met een rib (vlak y = AY/2, x = 0,02 .. 0,08, hoogte BZ),
# zijlast P (+Y) op de bovenrand van de rib. De rib buigt uit zijn vlak;
# het moment aan de voet moet in de plaat (als scharnier: mechanisme).
# (c): rib met eigen knopen (13 x 8 tegen 20 langs x in de plaat),
# voetlijn op een meshlijn van de plaat (10 elementen over AY); (d):
# voetlijn midden in de plaatelementen (15 over AY); (e): gedeelde knopen.
# Referentie: (e) (zelfde schema, in_series False) en Mecway 34 op (e):
# 2,93195e-6 m.
L7, B7, T7, P7 = 0.2, 0.02, 0.002, 1.0
I7 = B7 * T7 ** 3 / 12.0
AX7, AY7, BZ7, BX07, BX17 = 0.1, 0.06, 0.04, 0.02, 0.08
W7 = P7 * L7 ** 3 / (3 * E * I7)
R7 = P7 * L7 ** 2 / (2 * E * I7)
R7H = P7 * (L7 * L7 / 2 - L7 ** 2 / 8) / (E * I7)     # rotatie in x = L/2
BOND = ('<contact2 selectionmaster="{0}" selectionslave="{1}" '
        'type="bondedtie"><tolerance>0 m</tolerance><normalstiffness>0 Pa/m'
        '</normalstiffness><tangentialstiffness>0 Pa/m</tangentialstiffness>'
        '<frictioncoefficient>0</frictioncoefficient></contact2>')
PLATE2 = '<geometric type="Plate" thickness="2 mm" />'


def build_ls07_strip(glued):
    def build():
        m = Model("S30")
        m.mat("Plaat2", PLATE2, STEEL)
        if glued:
            m.elset("Deel_A", "Plaat2")
            a = quadmesh(m, "Deel_A", 10, 4, rect(0, L7 / 2, 0, B7))
            m._index = {}                    # B: eigen knopen
            m.elset("Deel_B", "Plaat2")
            b = quadmesh(m, "Deel_B", 10, 7, rect(L7 / 2, L7, 0, B7))
            m.face_selection("Lijm_A", [(a["elems"][(9, j)], 5)
                                        for j in range(4)])
            m.face_selection("Lijm_B", b["edges"]["u0"])
            m.node_selection("Naad_A", sorted(a["nodes"]["u1"]))
            m.node_selection("Naad_B", sorted(b["nodes"]["u0"]))
            m.add(BOND.format("Lijm_A", "Lijm_B"))
            root, tip = a, b
        else:
            m.elset("Plaat", "Plaat2")
            root = tip = quadmesh(m, "Plaat", 20, 4, rect(0, L7, 0, B7))
        m.face_selection("Inklemming", root["edges"]["u0"])
        m.face_selection("Vrij_eind", tip["edges"]["u1"])
        m.node_selection("Tip", sorted(tip["nodes"]["u1"]))
        m.add('<fixed selection="Inklemming" />')
        m.add('<force selection="Vrij_eind"><x>0 N</x><y>0 N</y><z>-%g N</z>'
              '</force>' % P7)
        return m
    return build


def build_ls07_tee(mode):
    """mode: "rand" (voetlijn op een meshlijn), "midden" (in de
    elementen) of "doorlopend" (gedeelde knopen)."""
    def build():
        m = Model("S30")
        m.mat("Plaat2", PLATE2, STEEL)
        m.elset("Plaat", "Plaat2")
        nay = {"rand": 10, "midden": 15, "doorlopend": 10}[mode]
        a = quadmesh(m, "Plaat", 20, nay, rect(0, AX7, 0, AY7))
        if mode != "doorlopend":
            m._index = {}
        m.elset("Rib", "Plaat2")
        b = quadmesh(m, "Rib", 12 if mode == "doorlopend" else 13, 8,
                     lambda u, v: (BX07 + u * (BX17 - BX07), AY7 / 2,
                                   v * BZ7))
        m.face_selection("Inklemming", a["edges"]["v0"] + a["edges"]["v1"])
        m.face_selection("Ribtop", b["edges"]["v1"])
        m.node_selection("Ribtop_knopen", sorted(b["nodes"]["v1"]))
        if mode != "doorlopend":
            m.face_selection("Lijm_plaat", a["faces"])
            m.face_selection("Lijm_rib", b["edges"]["v0"])
            m.add(BOND.format("Lijm_plaat", "Lijm_rib"))
        m.add('<fixed selection="Inklemming" />')
        m.add('<force selection="Ribtop"><x>0 N</x><y>%g N</y><z>0 N</z>'
              '</force>' % P7)
        return m
    return build


def _ls07_strip_checks():
    return [
        Check("doorbuiging tip", lambda r: -_mean(r, "displz", "Tip"),
              ref=W7, tol=0.02, unit="m",
              source="P L^3/(3EI) (Euler, E; inklemming -1 %)"),
        Check("doorbuiging tip t.o.v. Mecway", lambda r: -_mean(
            r, "displz", "Tip"), ref=9.41484e-4, tol=0.005, unit="m",
              source="Mecway 34, doorlopende strook (LS-07b)",
              in_series=False),
        Check("rotatie tip", lambda r: _mean(r, "roty", "Tip"), ref=R7,
              tol=0.02, unit="rad", source="P L^2/(2EI)"),
        Check("rotatie tip t.o.v. Mecway", lambda r: _mean(r, "roty", "Tip"),
              ref=7.09010e-3, tol=0.005, unit="rad",
              source="Mecway 34, doorlopende strook (LS-07b)",
              in_series=False)]


TESTS += [
    Case("LS-07a", GROUP, "Plaatstrook uit twee verlijmde delen (schaal "
         "op schaal, eigen meshes)", "lin_static_3d",
         build_ls07_strip(True), _ls07_strip_checks() + [
             Check("rotatie naad, deel B", lambda r: _mean(
                 r, "roty", "Naad_B"), ref=R7H, tol=0.02, unit="rad",
                   source="P (L x - x^2/2)/(EI), x = L/2"),
             Check("rotatie naad B / A (geen scharnier)", lambda r: _mean(
                 r, "roty", "Naad_B") / _mean(r, "roty", "Naad_A"), ref=1.0,
                   tol=0.005, unit="-", source="doorlopende rotatie",
                   in_series=False)],
         note="Mecway bonded contact (bondedtie), slave = rand van deel B "
              "(7 elementen breed), master = schaalvlakken van deel A (4 "
              "breed) -> LIAISON_MAIL COQUE zonder DRZ (drilling)."),
    Case("LS-07b", GROUP, "Plaatstrook uit één mesh (referentie LS-07a)",
         "lin_static_3d", build_ls07_strip(False), _ls07_strip_checks()),
    Case("LS-07c", GROUP, "T-stuk: rib met de rand verlijmd op een plaat, "
         "voetlijn op een meshlijn", "lin_static_3d", build_ls07_tee("rand"),
         [Check("zijdelingse verplaatsing ribtop",
                lambda r: _mean(r, "disply", "Ribtop_knopen"),
                ref=2.947048e-6, tol=0.005, unit="m",
                source="LS-07e (gedeelde knopen, Code-Aster)",
                in_series=False),
          Check("idem t.o.v. Mecway",
                lambda r: _mean(r, "disply", "Ribtop_knopen"),
                ref=2.93195e-6, tol=0.01, unit="m",
                source="Mecway 34 op LS-07e", in_series=False)],
         note="Rib 13 elementen lang tegen 20 in de plaat (knopen vallen "
              "niet samen); het moment gaat via de rotaties in de lijm."),
    Case("LS-07d", GROUP, "T-stuk: voetlijn midden in de plaatelementen",
         "lin_static_3d", build_ls07_tee("midden"),
         [Check("zijdelingse verplaatsing ribtop",
                lambda r: _mean(r, "disply", "Ribtop_knopen"),
                ref=2.947048e-6, tol=0.07, unit="m",
                source="LS-07e (gedeelde knopen, Code-Aster)",
                in_series=False)],
         note="De rotatie van de plaat heeft een knik onder de rib; "
              "LIAISON_MAIL interpoleert ze lineair tussen de knopen (4 mm "
              "elementen: -5 %, 12 mm: -11 %, 1,3 mm: -2 %). Leg de "
              "voetlijn op een meshlijn (LS-07c)."),
    Case("LS-07e", GROUP, "T-stuk met gedeelde knopen (referentie)",
         "lin_static_3d", build_ls07_tee("doorlopend"),
         [Check("zijdelingse verplaatsing ribtop t.o.v. Mecway",
                lambda r: _mean(r, "disply", "Ribtop_knopen"),
                ref=2.93195e-6, tol=0.01, unit="m",
                source="Mecway 34 (eigen solver)", in_series=False)]),
]


# ------------------------------------------------------------------
# LS-08 Node temperature (Mecway temperature3) voor thermische spanning
# ------------------------------------------------------------------
# Mecway Node temperature (manual v34 par. 9.24): een temperatuur per
# knoop, bijv. overgenomen uit een thermische analyse ("Transfer
# temperatures from solution"). Knopen zonder temperatuur staan op de
# referentietemperatuur van de Thermal stress (par. 9.25). De bridge zet de
# waarden in het knoopveld TEMP (AFFE_VARC), net als temperature2.
ALPHA8, TREF8, DT8 = 1.2e-5, 293.15, 100.0
STEEL_T = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
           'poissonratio="0.3" thermalexpansion="%g 1/K" />' % ALPHA8)
# Mecway 34 headless (TestFiles/Tools/mw_solve.py) op modellen/LS-08*.liml
# (eigen solver). LS-08d in Mecway (hex8, incompatibele modes):
# u_z(L, 0, 0) = -6,2815e-4 m (+4,7 %); niet als controle, de bridge rekent
# met LINE_QUAD.
MW_LS08A = 2520000.0
MW_LS08B = -5.99999999987e-4
MW_LS08C = 4.5e-5


def _node_temps(pairs):
    """<temperature3> met (nid, K) per knoop."""
    return ("<temperature3>" + "".join(
        '<nodetemperature nid="%d" value="%.12g K" />' % p for p in pairs)
        + "</temperature3>")


def _tref8(m):
    m.add('<thermalstress><referencetemperature>%g K'
          '</referencetemperature></thermalstress>' % TREF8)


def _roll(m, sel, x, y, z):
    m.add('<displacement selection="%s"><value>0 m</value><x>%d</x>'
          '<y>%d</y><z>%d</z></displacement>' % (sel, x, y, z))


L8A, B8A = 1.0, 0.1


def build_ls08a():
    """Staaf als TH-03b (ingeklemd in x, dwarsrichting vrij), maar met
    Node temperature Tref + 100 K op alle knopen."""
    m = Model("S30")
    m.elset("Staaf", "Staal")
    g = hexmesh(m, "Staaf", 4, 1, 1, box(0, L8A, 0, B8A, 0, B8A))
    m.mat("Staal", STEEL_T)
    m.face_selection("X0", g["faces"]["u0"])
    m.face_selection("Y0", g["faces"]["v0"])
    m.face_selection("Z0", g["faces"]["w0"])
    m.face_selection("XLv", g["faces"]["u1"])
    m.node_selection("XL", sorted(g["nodes"]["u1"]))
    for sel, x, y, z in (("X0", 1, 0, 0), ("Y0", 0, 1, 0), ("Z0", 0, 0, 1),
                         ("XLv", 1, 0, 0)):
        _roll(m, sel, x, y, z)
    _tref8(m)
    m.add(_node_temps([(n, TREF8 + DT8)
                       for n in range(1, len(m.nodes) + 1)]))
    return m


# LS-08b/d: vrije balk met een lineair temperatuurverloop over de dikte,
# T = Tref + DT z / h. Exacte oplossing (Timoshenko & Goodier par. 150,
# lineaire temperatuur: spanningsloos): eps = alpha g z in alle richtingen
# (g = DT / h), u_x = alpha g x z, u_y = alpha g y z,
# u_z = -alpha g (x^2 + y^2 - z^2) / 2. Opgelegd zoals die oplossing het
# toelaat: u_x = 0 op x = 0, u_y = 0 op y = 0, u_z = 0 in (0, 0, 0).
# Doorbuiging op (L, 0, 0): -alpha g L^2 / 2.
L8B, B8B, H8B = 0.1, 0.01, 0.01
G8B = DT8 / H8B
W8B = -ALPHA8 * G8B * L8B ** 2 / 2.0


def build_ls08_bend(order, nx):
    def build():
        m = Model("S30")
        m.elset("Balk", "Staal")
        g = hexmesh(m, "Balk", nx, 1, 4, box(0, L8B, 0, B8B, 0, H8B),
                    order=order)
        m.mat("Staal", STEEL_T)
        m.face_selection("X0", g["faces"]["u0"])
        m.face_selection("Y0", g["faces"]["v0"])
        m.node_selection("O", [m.node(0, 0, 0)])
        _roll(m, "X0", 1, 0, 0)
        _roll(m, "Y0", 0, 1, 0)
        _roll(m, "O", 0, 0, 1)
        _tref8(m)
        m.add(_node_temps([(i + 1, TREF8 + G8B * p[2])
                           for i, p in enumerate(m.nodes)]))
        return m
    return build


def _ls08_bend_checks(mecway=None):
    checks = [
        Check("u_z op (L, 0, 0)", lambda r: r.at("displz", (L8B, 0, 0)),
              ref=W8B, tol=1e-4, unit="m",
              source="-alpha g L^2/2 (Timoshenko & Goodier par. 150)"),
        Check("u_z op (L, 0, h)", lambda r: r.at("displz", (L8B, 0, H8B)),
              ref=W8B + ALPHA8 * G8B * H8B ** 2 / 2.0, tol=1e-4, unit="m",
              source="-alpha g (L^2 - h^2)/2"),
        Check("max |sigma_xx|",
              lambda r: max(abs(v) for v in r.step()["stressxx"].values()),
              ref=0.0, tol_abs=1e-4 * E * ALPHA8 * DT8, unit="Pa",
              source="lineaire temperatuur, vrij: spanningsloos "
                     "(tolerantie 1e-4 E alpha dT)")]
    if mecway is not None:
        checks.append(Check(
            "u_z op (L, 0, 0) t.o.v. Mecway", lambda r: r.at(
                "displz", (L8B, 0, 0)), ref=mecway, tol=1e-4, unit="m",
            source="Mecway 34 (eigen solver; interpoleert de "
                   "knooptemperatuur in het element)", in_series=False))
    return checks


# LS-08c: vrije staaf (4 hex8 langs x), temperature2 op de knopen in
# x = 0 (+100 K) en Node temperature op de knopen in x = L (+200 K); de
# knopen ertussen staan op de referentie. Per element is de gemiddelde
# temperatuur +50 K (eerste) en +100 K (laatste): u_x(L) = alpha (50 +
# 100) K L/4 (Mecway en een lineair knoopveld geven hetzelfde).
U8C = ALPHA8 * (50.0 + 100.0) * (0.1 / 4)


def build_ls08c():
    m = Model("S30")
    m.elset("Staaf", "Staal")
    g = hexmesh(m, "Staaf", 4, 1, 1, box(0, 0.1, 0, 0.01, 0, 0.01))
    m.mat("Staal", STEEL_T)
    m.face_selection("X0", g["faces"]["u0"])
    m.face_selection("Y0", g["faces"]["v0"])
    m.face_selection("Z0", g["faces"]["w0"])
    for sel, x, y, z in (("X0", 1, 0, 0), ("Y0", 0, 1, 0), ("Z0", 0, 0, 1)):
        _roll(m, sel, x, y, z)
    m.node_selection("X0N", sorted(g["nodes"]["u0"]))
    m.node_selection("XL", sorted(g["nodes"]["u1"]))
    _tref8(m)
    m.add('<temperature2 selection="X0N"><value>%.12g K</value>'
          '<starttime>0 s</starttime><endtime>0 s</endtime></temperature2>'
          % (TREF8 + DT8))
    m.add(_node_temps([(n, TREF8 + 2 * DT8) for n in sorted(
        g["nodes"]["u1"])]))
    return m


TESTS += [
    Case("LS-08a", GROUP, "Staaf ingeklemd in x, Node temperature op alle "
         "knopen", "lin_static_3d", build_ls08a,
         [Check("sigma_xx", lambda r: r.at("stressxx", (L8A / 2, B8A / 2,
                                                        B8A)),
                ref=-E * ALPHA8 * DT8, tol=1e-6, unit="Pa",
                source="-E alpha dT (verhinderde uitzetting, dwarsrichting "
                       "vrij)"),
          Check("u_y zijkant", lambda r: r.at("disply", (L8A / 2, B8A, 0)),
                ref=(1 + NU) * ALPHA8 * DT8 * B8A, tol=1e-6, unit="m",
                source="(1+nu) alpha dT b"),
          Check("|reactie x| op x = L",
                lambda r: abs(r.total("reactionforcex", "XL")),
                ref=E * ALPHA8 * DT8 * B8A * B8A, tol=1e-6, unit="N",
                source="E alpha dT A"),
          Check("|reactie x| op x = L t.o.v. Mecway",
                lambda r: abs(r.total("reactionforcex", "XL")),
                ref=MW_LS08A, tol=1e-6, unit="N",
                source="Mecway 34 (eigen solver)", in_series=False)],
         note="als TH-03b, met temperature3 i.p.v. temperature2"),
    Case("LS-08b", GROUP, "Vrije balk, lineaire temperatuur over de dikte "
         "(Node temperature, hex20)", "lin_static_3d",
         build_ls08_bend(2, 10), _ls08_bend_checks(MW_LS08B),
         note="hex20 beschrijft de exacte (kwadratische) verplaatsing; "
              "Mecway geeft hetzelfde"),
    Case("LS-08c", GROUP, "Vrije staaf: temperature2 en Node temperature "
         "op verschillende knopen, overige op de referentie",
         "lin_static_3d", build_ls08c,
         [Check("gemiddelde u_x op x = L", lambda r: r.mean("displx", "XL"),
                ref=U8C, tol=0.01, unit="m",
                source="alpha (50 + 100) K L/4 (elementgemiddelden)"),
          Check("gemiddelde u_x op x = L t.o.v. Mecway",
                lambda r: r.mean("displx", "XL"), ref=MW_LS08C, tol=0.01,
                unit="m", source="Mecway 34 (eigen solver)",
                in_series=False)]),
    Case("LS-08d", GROUP, "Als LS-08b met hex8 en LINE_QUAD (middenknopen "
         "krijgen de geinterpoleerde temperatuur)", "lin_static_3d",
         build_ls08_bend(1, 10), _ls08_bend_checks(),
         general={"elem_hex8": "LINE_QUAD"}),
]
