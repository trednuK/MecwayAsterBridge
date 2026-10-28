# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Akoestische holtemodes met impedantieranden: complexe modes (Mecway A30
met <impedance> -> Code-Aster-matrices + kwadratisch eigenwaardeprobleem
in de job, Scripts/aster_acoustic_complex.py; bridge-analyse
acoustic_modes_3d). Toelichting: docs/Verificatie.md par. 7 (AI) en
docs/Akoestiek.md par. 3.3.

Grootheden per mode: frequentie f = Im(lambda) / 2 pi (<mode frequency>),
decay rate sigma = -Re(lambda) (<mode decayrate>, ook DECAY in de
BRIDGE_MODE-regel van de .mess) en de complexe druk P = pressure + i
pressurei; p(t) = Re(P e^(lambda t)) (Mecway manual v33 par. 6.9.2).

Referenties:
  - buis met lengte L langs x, harde wand op x = 0 en een impedantie Z op
    x = L (vlakke golven, zelf afgeleid): p = cosh(s x / c), de rand
    dp/dx = -rho s p / Z (rho dv/dt = -dp/dx, v = p / Z naar buiten) geeft
    tanh(s L / c) = -rho c / Z, dus
        s_n = (c / L) (-artanh(rho c / Z) + i pi n),  n geheel,
    met f = Im(s) / 2 pi >= 0. Reele Z > rho c: f_n = n c / (2L), sigma =
    (c / L) artanh(rho c / Z) (n = 0: niet-oscillerend, f = 0); Z < rho c:
    f_n = (2n - 1) c / (4L), sigma = (c / L) artanh(Z / (rho c)); Z ->
    oneindig: de harde wand (sigma -> 0); Z = rho c: geen wortel (geen
    reflectie, geen resonantie). Drukknoop (p = 0) op x = 0: p = sinh(s x /
    c), tanh(s L / c) = -Z / (rho c);
  - vorm: P(L) / P(0) = cosh(s L / c) = (-1)^n / sqrt(1 - (rho c / Z)^2);
  - Mecway 33 headless (TestFiles/Tools/mw_solve.py, interne solver) op
    dezelfde .liml (modellen/AI-*.liml): (f, sigma) van elke mode en P(L) /
    P(0) (schaal-onafhankelijk: Mecway schaalt de vorm willekeurig); waarden
    hieronder in MECWAY.
"""
import cmath
import math
from verif_lib import Case, Check, Model, hexmesh, box

GROUP = "Akoestiek impedantie"
C_AIR, RHO = 340.0, 1.2
RHOC = RHO * C_AIR                       # 408 Pa.s/m
AIR = ['<mechanical type="Isotropic" speedofsound="340 m/s" />',
       u'<density type="Simple" density="1.2 kg/m³" />']
LT, WT = 1.0, 0.1

# Mecway 33 headless (mw_solve.py) op modellen/AI-*.liml, 7 okt 2026:
# per mode (f [Hz], decay rate [1/s]) en P(L)/P(0) als (|.|, fase in graden)
# van de mode het dichtst bij "shape_f".
_O, _X = (0.0, 0.0, 0.0), (1.0, 0.0, 0.0)
MECWAY = {
    "AI-01": {"modes": ((2.11916547499127e-11, 70.3469248029735),
                        (170.000069959995, 70.3470420865244),
                        (340.002273872688, 70.3487907776063),
                        (510.017218655038, 70.3562387374409),
                        (680.072011323684, 70.3757614796721),
                        (850.217444002739, 70.415448251298)),
              "shape": ((170.000069959995, 70.3470420865244),
                        1.0214808163349105, 179.99999972308603, (_O, _X))},
    "AI-02": {"modes": ((84.9999986672181, 182.348276739418),
                        (255.000440533216, 182.350585190946),
                        (425.006481145174, 182.366584203659),
                        (595.035843079628, 182.418735603913),
                        (765.126464751221, 182.54006984172)),
              "shape": ((84.9999986672181, 182.348276739418),
                        0.5624015944708521, -89.99999759407757, (_O, _X))},
    "AI-03": {"modes": ((1.96390943063226e-05, -3.20007957466645e-05),
                        (170.00007178014, 0.000138720205313803),
                        (340.002288125325, 0.000138723624928616),
                        (510.017264978263, 0.000138738570651591),
                        (680.072115195111, 0.00013877735824286),
                        (850.217631869642, 0.000138856259393968)),
              "shape": ((170.00007178014, 0.000138720205313803),
                        0.9999999999999758, -179.99999999997002, (_O, _X))},
    "AI-04": {"modes": ((1.53337076927303e-11, -1.75414426199336e-10),
                        (130.113278170427, 2105.09946321986),
                        (265.345370376628, 2006.12480053619),
                        (408.683321375361, 1870.52731550614),
                        (560.037313080293, 1725.64357884131),
                        (717.50756834993, 1588.07310582641)),
              "shape": ((130.113278170427, 2105.09946321986),
                        244.28561313688388, -137.7641414322169, (_O, _X))},
    "AI-05": {"modes": ((165.475064447011, 55.6015649490489),
                        (335.477163056367, 55.6029069033078),
                        (505.491648235591, 55.6087051572758),
                        (675.545222382136, 55.6240134994519),
                        (845.688161399208, 55.6552794593351)),
              "shape": ((165.475064447011, 55.6015649490489),
                        1.0099535702384521, -179.22162510212743, (_O, _X))},
    "AI-06": {"modes": ((6.60132914304731, 13.6742773526711),
                        (176.601412661843, 13.6743033833505),
                        (346.603798700806, 13.6746673595031),
                        (516.619491465112, 13.6761857946638),
                        (686.676210408221, 13.6801285164847),
                        (856.825517861473, 13.688102698432)),
              "shape": ((176.601412661843, 13.6743033833505),
                        0.9933830948935981, 179.71763925546793, (_O, _X))},
    "AI-07": {"modes": ((20.962378444258, -1.12855664891155e-09),
                        (190.962494000349, -5.26821580138274e-11),
                        (360.96529793554, -1.24359060269844e-11),
                        (530.982694808448, -6.35539719147654e-12),
                        (701.043794253084, -7.94758920634865e-11),
                        (871.201918051567, 5.54791768081486e-11)),
              "shape": ((190.962494000349, -5.26821580138274e-11),
                        0.9259006135634555, -179.99999999999923, (_O, _X))},
    "AI-08": {"modes": ((85.0000020169936, 70.346932057756),
                        (255.000538114545, 70.3475177605843),
                        (425.006935361747, 70.3514521057814),
                        (595.037091557959, 70.3640168528837),
                        (765.129124058686, 70.3925326860633),
                        (935.348011279515, 70.4456526311786)),
              "shape": ((255.000538114545, 70.3475177605843),
                        1.4293220916337175, -174.11453003558418,
                        ((0.5, 0.0, 0.0), _X))},
    "AI-09": {"modes": ((2.0630041157223e-11, 1.33010752913799e-10),
                        (170.170968782132, 70.6382567487224),
                        (341.391994451208, 71.5215389236653),
                        (514.718870611874, 73.018467535031)),
              "shape": ((170.170968782132, 70.6382567487224),
                        1.021526423394033, -179.99965992714644, (_O, _X))},
    "AI-10": {"modes": ((3.83391943100233e-12, 3.42190029470362e-11),
                        (139.306032282494, 401.528885808026),
                        (218.674021358579, 442.508291685081),
                        (276.488604851233, 466.373056202164),
                        (323.557984374279, 483.686017973576),
                        (376.848783715241, 828.951062213244),
                        (408.139555700674, 510.593954784725),
                        (411.818901951959, 838.108191061003),
                        (445.384839476029, 846.3174367457),
                        (482.972482784286, 528.988637820238)),
              "shape": ((139.306032282494, 401.528885808026),
                        1.2102016483808784, 177.94689953072447,
                        (_O, (1.0, 0.7, 0.4)))},
}


# ------------------------------------------------------------------
# Hulpfuncties
# ------------------------------------------------------------------
def _lam(f, decay):
    return complex(-decay, 2.0 * math.pi * f)


def _modes(r):
    """[(k, lambda)] van de bridge-modes (frequentie uit <mode>, decay rate
    uit de .mess)."""
    return [(k, _lam(f, r.mode_param(k, "DECAY"))) for k, f in
            sorted(r.modes.items())]


def _nearest(r, lam):
    """Mode-nummer met de eigenwaarde het dichtst bij lam."""
    return min(_modes(r), key=lambda t: abs(t[1] - lam))[0]


def _f(r, lam):
    return r.mode(_nearest(r, lam))


def _decay(r, lam):
    return r.mode_param(_nearest(r, lam), "DECAY")


def _P(r, k, point):
    return complex(r.at("pressure", point, float(k)),
                   r.at("pressurei", point, float(k)))


def _ratio(r, lam, a=(0.0, 0.0, 0.0), b=(LT, 0.0, 0.0)):
    """P(b) / P(a) van de mode het dichtst bij lam (schaal-onafhankelijk)."""
    k = _nearest(r, lam)
    return _P(r, k, b) / _P(r, k, a)


def _phase_deg(z):
    return math.degrees(cmath.phase(z))


def tube_roots(z, count, pnode=False, c=C_AIR, L=LT):
    """Analytische eigenwaarden s (f >= 0) van de buis, oplopend in f (zie
    de kop); [] bij Z = rho c (geen wortel)."""
    # complex / complex: Python 3.14 divides float / complex without
    # converting the float, which gives -0j for a real z, puts atanh on the
    # other side of its branch cut (imag -pi/2 instead of +pi/2) and shifts n
    zeta = complex(RHOC) / complex(z)
    arg = complex(1.0) / zeta if pnode else zeta
    if abs(arg - 1.0) < 1e-12:
        return []
    a = cmath.atanh(arg)
    out = []
    for n in range(-count - 2, count + 3):
        s = (c / L) * (-a + 1j * math.pi * n)
        if s.imag >= -1e-9:
            out.append((n, complex(s.real, max(s.imag, 0.0))))
    out.sort(key=lambda t: t[1].imag)
    return out[:count]


def _root_checks(roots, src, tol=0.01, skip_zero=False):
    out = []
    for n, s in roots:
        f = s.imag / (2.0 * math.pi)
        if skip_zero and f <= 1e-6:
            continue
        tag = "n=%d" % n
        if f > 1e-6:
            out.append(Check("f (%s)" % tag, lambda r, s=s: _f(r, s), ref=f,
                             tol=tol, unit="Hz", source=src))
        else:
            out.append(Check("f (%s, niet-oscillerend)" % tag,
                             lambda r, s=s: _f(r, s), ref=0.0, tol_abs=1e-6,
                             unit="Hz", source=src))
        if abs(s.real) > 1e-6:
            out.append(Check("decay rate (%s)" % tag,
                             lambda r, s=s: _decay(r, s), ref=-s.real,
                             tol=tol, unit="1/s", source=src))
        else:
            out.append(Check("decay rate (%s)" % tag,
                             lambda r, s=s: _decay(r, s), ref=0.0,
                             tol_abs=1e-6, unit="1/s", source=src))
    return out


def _shape_checks(z, src):
    """P(L)/P(0) van de laagste oscillerende mode (harde wand op x = 0)
    t.o.v. cosh(s L / c): grootte, en de fase van het quotient
    (bridge / analytisch, 0 = gelijk; zo geen sprong bij 180 graden)."""
    roots = [t for t in tube_roots(z, 6) if t[1].imag > 1e-6]
    if not roots:
        return []
    n, s = roots[0]
    ref = cmath.cosh(s * LT / C_AIR)
    f = s.imag / (2.0 * math.pi)
    text = "%s; mode n=%d (%.4g Hz): P(L)/P(0) = %.6g, fase %.4f graden" % (
        src, n, f, abs(ref), _phase_deg(ref))
    return [Check("|P(L)/P(0)| (%.4g Hz)" % f, lambda r: abs(_ratio(r, s)),
                  ref=abs(ref), tol=0.001, unit="-", in_series=False,
                  source=text),
            Check("fase P(L)/P(0) t.o.v. analytisch (%.4g Hz)" % f,
                  lambda r: _phase_deg(_ratio(r, s) / ref), ref=0.0,
                  tol_abs=0.05, unit="graden", in_series=False, source=text)]


def _mecway_checks(case_id, tol=0.01):
    ref = MECWAY.get(case_id)
    if not ref:
        return []
    src = "Mecway 33 headless (mw_solve.py), zelfde .liml"
    out = []
    for f, d in ref["modes"]:
        lam = _lam(f, d)
        if f <= 1e-3 and abs(d) < 1e-3:
            # numeriek nul (de constante druk, lambda = 0): Mecway's waarde
            # is afrondingsruis (1e-5 .. 1e-10), niet te vergelijken
            continue
        if f > 1e-3:
            out.append(Check("f %.6g Hz t.o.v. Mecway" % f,
                             lambda r, lam=lam: _f(r, lam), ref=f, tol=tol,
                             unit="Hz", in_series=False, source=src))
        if abs(d) > 1e-6:
            out.append(Check("decay %.6g 1/s t.o.v. Mecway" % d,
                             lambda r, lam=lam: _decay(r, lam), ref=d,
                             tol=tol, unit="1/s", in_series=False,
                             source=src))
        else:
            out.append(Check("decay (f %.6g Hz) t.o.v. Mecway (0)" % f,
                             lambda r, lam=lam: _decay(r, lam), ref=0.0,
                             tol_abs=1e-6, unit="1/s", in_series=False,
                             source=src))
    if "shape" in ref:
        (f, d), mag, ph, pts = ref["shape"]
        lam = _lam(f, d)
        mw = cmath.rect(mag, math.radians(ph))
        out.append(Check("|P(B)/P(A)| t.o.v. Mecway (%.6g Hz)" % f,
                         lambda r: abs(_ratio(r, lam, *pts)), ref=mag,
                         tol=1e-4, unit="-", in_series=False,
                         source=src + "; A = %s, B = %s" % pts))
        out.append(Check("fase P(B)/P(A) t.o.v. Mecway (%.6g Hz)" % f,
                         lambda r: _phase_deg(_ratio(r, lam, *pts) / mw),
                         ref=0.0, tol_abs=0.01, unit="graden",
                         in_series=False,
                         source=src + "; Mecway: fase %.4f graden" % ph))
    return out


# ------------------------------------------------------------------
# Buis L = 1 m, 0,1 x 0,1 m (eerste dwarsmode 1700 Hz): harde wand op
# x = 0 (of een drukknoop), impedantie op x = L.
# ------------------------------------------------------------------
def build_tube(zr, zi, order=2, n=20, maxmode=6, pnode=False):
    def build():
        m = Model("A30", attrs={"maxmode": maxmode})
        m.elset("Lucht", "Lucht")
        h = hexmesh(m, "Lucht", n, 1, 1, box(0, LT, 0, WT, 0, WT),
                    order=order)
        m.mat("Lucht", *AIR)
        m.face_selection("Absorbeerder", h["faces"]["u1"])
        m.add('<impedance selection="Absorbeerder"><specificimpedancer>%r'
              '</specificimpedancer><specificimpedancei>%r'
              '</specificimpedancei></impedance>' % (float(zr), float(zi)))
        if pnode:
            m.face_selection("Open", h["faces"]["u0"])
            m.add('<fluidpressure selection="Open"><value>0 Pa</value>'
                  '</fluidpressure>')
        return m
    return build


TUBE = ("buis L = 1 m, c = 340 m/s, rho = 1,2 kg/m3; tanh(s L/c) = "
        "-rho c / Z (vlakke golven, zie de kop)")
SHAPE = "P(L)/P(0) = cosh(s L/c) (vlakke golf, zie de kop)"
TESTS = []


def _tube_case(cid, title, zr, zi, count, note, extra=(), shape=True,
               pnode=False, order=2, n=20, maxmode=6, tol=0.01,
               skip_zero=False):
    z = complex(zr, zi)
    checks = _root_checks(tube_roots(z, count, pnode=pnode), TUBE if not pnode
                          else TUBE.replace("-rho c / Z", "-Z / (rho c) "
                                            "(drukknoop op x = 0)"), tol=tol,
                          skip_zero=skip_zero)
    if shape and not pnode:
        checks += _shape_checks(z, SHAPE)
    checks += list(extra) + _mecway_checks(cid)
    TESTS.append(Case(cid, GROUP, title, "acoustic_modes_3d",
                      build_tube(zr, zi, order=order, n=n, maxmode=maxmode,
                                 pnode=pnode), checks, note=note))


_tube_case("AI-01", "Buis hard / Z = 2000 Pa.s/m (reeel, Z > rho c), hex20 "
           "20x1x1", 2000.0, 0.0, 6,
           "f_n = n c / (2L), decay rate (c/L) artanh(rho c / Z) = 70,35 1/s; "
           "n = 0 is een niet-oscillerende mode (f = 0). De bridge geeft ook "
           "de constante druk (lambda = 0).")
_tube_case("AI-02", "Buis hard / Z = 200 Pa.s/m (reeel, Z < rho c), hex20 "
           "20x1x1", 200.0, 0.0, 5,
           "Zachte rand: f_n = (2n - 1) c / (4L), decay rate (c/L) "
           "artanh(Z / (rho c)) = 182,3 1/s.")
_tube_case("AI-03", "Buis hard / Z = 1e9 Pa.s/m (Z -> oneindig = harde "
           "wand), hex20 20x1x1", 1.0e9, 0.0, 5,
           "Moet gelijk zijn aan AK-01 (harde wanden): decay rate (c/L) rho c "
           "/ Z = 1,4e-4 1/s. De niet-oscillerende mode (n = 0, decay 1,4e-4) "
           "valt numeriek samen met de constante druk (lambda = 0) en wordt "
           "niet vergeleken.", skip_zero=True,
           extra=[Check("f2 = AK-01 (Mecway, harde wanden)",
                        lambda r: _f(r, _lam(170.0, 0.0)),
                        ref=170.0000717803, tol=1e-6, unit="Hz",
                        in_series=False,
                        source="Mecway 33 headless AK-01 (zelfde mesh, "
                               "zonder impedantie)")])


SIGMA_2000 = (C_AIR / LT) * math.atanh(RHOC / 2000.0)     # AI-01: 70,35


def _min_decay_ratio(r):
    """min(1, kleinste decay rate van de oscillerende modes / (10 x die
    bij Z = 2000)): 1 = elke mode dempt minstens 10x sneller uit dan de
    buis met Z = 2000."""
    d = min(r.mode_param(k, "DECAY") for k, l in _modes(r) if l.imag > 0.0)
    return min(1.0, d / (10.0 * SIGMA_2000))


TESTS.append(Case(
    "AI-04", GROUP, "Buis hard / Z = rho c = 408 Pa.s/m (geen reflectie), "
    "hex20 20x1x1", "acoustic_modes_3d", build_tube(RHOC, 0.0),
    [Check("decay rate >= 10 x die bij Z = 2000 (geen resonantie)",
           _min_decay_ratio, ref=1.0, tol_abs=1e-12, unit="-",
           in_series=False,
           source="Z = rho c: tanh(s L/c) = -1 heeft geen wortel (geen "
                  "reflectie); de eindige-elementenmodes dempen veel sneller "
                  "uit dan bij Z = 2000 (AI-01: (c/L) artanh(rho c/Z) = "
                  "70,35 1/s)")] +
    _mecway_checks("AI-04"),
    note="Z = rho c: een vlakke golf wordt niet teruggekaatst; de buis heeft "
         "geen resonanties. De gevonden modes zijn discretisatiemodes met "
         "hoge decay rate (gelijk aan Mecway)."))
_tube_case("AI-05", "Buis hard / Z = 2000 - 1000i Pa.s/m (complex), hex20 "
           "20x1x1", 2000.0, -1000.0, 5,
           "Complexe Z (Z = R + iX, Mecway's specificimpedancer/-i): f_n = "
           "170 n - 4,5 Hz, decay rate 55,6 1/s; de vorm is complex.")
_tube_case("AI-06", "Buis hard / Z = 1000 + 3000i Pa.s/m (complex), hex20 "
           "20x1x1", 1000.0, 3000.0, 6,
           "Reactantie X > 0 (massa-achtig bij e^(i w t)): de frequenties "
           "schuiven omhoog (6,6 Hz voor n = 0).")
_tube_case("AI-07", "Buis hard / Z = 1000i Pa.s/m (zuiver reactief), hex20 "
           "20x1x1", 0.0, 1000.0, 6,
           "Zuiver reactief: geen demping (decay rate 0), f_n = 170 n + 20,96 "
           "Hz (tan(kL) = rho c / X).")
_tube_case("AI-08", "Buis drukknoop (x = 0) / Z = 2000 Pa.s/m, hex20 20x1x1",
           2000.0, 0.0, 6,
           "p = 0 op x = 0 (fluid pressure 0, vlakselectie): f_n = (2n + 1) "
           "c / (4L), decay rate 70,35 1/s.", pnode=True)
_tube_case("AI-09", "Buis hard / Z = 2000 Pa.s/m, hex8 20x1x1 (dichte "
           "oplossing, < 300 vrijheidsgraden)", 2000.0, 0.0, 2,
           "hex8 (20 per meter): analytisch alleen n <= 1; gemeten f +0,10 / "
           "+0,41 / +0,93% en decay rate +0,41 / +1,67 / +3,8% voor n = 1 / 2 "
           "/ 3 (de decay rate is gevoeliger voor de mesh dan f), gelijk aan "
           "Mecway. 168 vrijheidsgraden in de gelineariseerde vorm: "
           "scipy.linalg.eig.",
           order=1, maxmode=4)


# ------------------------------------------------------------------
# AI-10 Rechthoekige ruimte 1,0 x 0,7 x 0,4 m (zoals AK-04), hex20
# 10 x 7 x 4, twee impedantieranden: vloer (z = 0) Z = 1000 Pa.s/m,
# plafond (z = 0,4) Z = 600 - 300i Pa.s/m. Alleen t.o.v. Mecway (3D, geen
# gesloten oplossing).
# ------------------------------------------------------------------
LX, LY, LZ = 1.0, 0.7, 0.4


def build_room():
    m = Model("A30", attrs={"maxmode": 8})
    m.elset("Lucht", "Lucht")
    h = hexmesh(m, "Lucht", 10, 7, 4, box(0, LX, 0, LY, 0, LZ), order=2)
    m.mat("Lucht", *AIR)
    m.face_selection("Vloer", h["faces"]["w0"])
    m.face_selection("Plafond", h["faces"]["w1"])
    m.add('<impedance selection="Vloer"><specificimpedancer>1000'
          '</specificimpedancer><specificimpedancei>0</specificimpedancei>'
          '</impedance>')
    m.add('<impedance selection="Plafond"><specificimpedancer>600'
          '</specificimpedancer><specificimpedancei>-300</specificimpedancei>'
          '</impedance>')
    return m


TESTS.append(Case(
    "AI-10", GROUP, "Ruimte 1,0 x 0,7 x 0,4 m, hex20 10x7x4, vloer Z = 1000 "
    "en plafond Z = 600 - 300i Pa.s/m", "acoustic_modes_3d", build_room,
    _mecway_checks("AI-10"),
    note="Twee impedantieranden (elk een eigen dempingsmatrix); 3D-modes "
         "(ook schuine) t.o.v. Mecway."))
