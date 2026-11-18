# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Element failure in 2D and axisymmetric (route A: Nonlinear Static L30 with
'#ASTER-PLANE C_PLAN|D_PLAN|AXIS' and '#ASTER-BEZWIJKEN'; Scripts/
bridge_failure.py). Explanation: docs/Verificatie.md chapter 2D and
axisymmetric (PL).

A strip of five quad4 elements in uniaxial tension under an imposed
elongation u(t) = U t (lateral contraction free), perfectly plastic,
sigma_y = 250 MPa. All elements have the same properties, but only the
middle one has the material 'Bros' with a failure limit; the others have
'Taai' (same values, no limit). The field stays uniform up to the failure,
so the failure time has a closed form:

  GDEF_LOG (the default for plastic material, bridge_to_aster
  _deformation_for; SIMO_MIEHE the same for this stretch): additive
  logarithmic strain e = ln(1 + u/L) and the dual stress T (Kirchhoff tau
  for a stretch without rotation). Uniaxial stress, perfectly plastic:
  tau = sigma_y, p = e - sigma_y / E. PETIT: e = u/L. Plane strain (D_PLAN,
  eps_zz = 0, sigma_yy = 0): the same law integrated numerically
  (_plane_strain, radial return).

The element fails at the first stored step with mean p >= limit; its
fields are zero from the next step on, and the element variable 'failed'
is 1 from that next step (AGENTS.md, contract with AdvancedToolsHub).

PL-70  C_PLAN (thickness 1 mm), GDEF_LOG. The reaction before failure is
       about sqrt(1 + u/L) too high (KNOWN_BUGS 144); PL-70p (PETIT) exact,
       PL-70r (PETIT_REAC) the same deviation as GDEF_LOG.
PL-71  D_PLAN; PL-71s with SIMO_MIEHE, PL-71p PETIT, PL-71r PETIT_REAC.
PL-72  AXIS: a tube r = 0.10 .. 0.11 m, pulled along the axis Y (uniform
       too: u_r = eps_lat r gives the same radial and hoop strain);
       PL-72s SIMO_MIEHE, PL-72p PETIT, PL-72r PETIT_REAC, PL-72c a
       hardening curve (VMIS_ISOT_TRAC), PL-72k kinematic hardening
       (VMIS_CINE_LINE, GDEF_LOG; monotonic: tau = sigma_y + H p).
PL-73  kinematic hardening (VMIS_CINE_LINE, the measure from the back
       stress incl. the shear component): simple shear of a strip of one row
       (every node prescribed, so the field is uniform), PETIT.
PL-74  parallel: two concentric rings in AXIS, the inner one 'Bros'; after
       the failure the outer ring carries the load alone.
"""
import math

from verif_lib import Case, Check, Model, quadmesh, rect

GROUP = "2D en axisymmetrisch"
E, NU, SY = 210e9, 0.3, 250.0e6
G = E / (2.0 * (1.0 + NU))
L, W, T = 0.05, 0.01, 0.001          # strip length, width, thickness [m]
RA = 0.10                            # AXIS: inner radius [m]
U = 2.0e-3                           # elongation at t = 1 s [m]
STEP = 0.05
TS = {"timeperiod": "1 s", "stepsize": "%g s" % STEP}
NE = 5
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
PERFECT = ('<plastic type="BilinearIsotropic" yieldstrength="%g Pa" '
           'tangentmodulus="0 Pa" />' % SY)
# The same perfectly plastic law as a hardening curve in total strain (E =
# the slope of the first segment, bridge_from_liml _curve_young)
CURVE = ('<plastic type="Isotropic"><hardeningcurve strain="%.12g" '
         'stress="250 MPa" /><hardeningcurve strain="0.5" stress="250 MPa" '
         '/></plastic>' % (SY / E))
H73 = 2.1e9                          # kinematic: plastic modulus (Mecway)
KINEMATIC = ('<plastic type="BilinearKinematic" yieldstrength="%g Pa" '
             'tangentmodulus="%g Pa" />' % (SY, H73))
GAMMA = 0.08                         # PL-73: shear strain at t = 1 s


def _e(t, deformation="GDEF_LOG"):
    s = U * t / L
    return s if deformation == "PETIT" else math.log(1.0 + s)


def _uniaxial(deformation="GDEF_LOG"):
    def p(t):
        return max(0.0, _e(t, deformation) - SY / E)
    return p


def _plane_strain(t, n=4000, stress_xx=False, deformation="GDEF_LOG"):
    """Equivalent plastic strain p (or the stress T_xx) at time t for plane
    strain (eps_zz = 0) and sigma_yy = 0 under the log strain e(t) along x:
    J2, perfectly plastic, radial return with eps_yy solved per increment
    (secant)."""
    K = E / (3 * (1 - 2 * NU))
    ep = [0.0, 0.0, 0.0]            # plastic strain xx, yy, zz
    p, eyy = 0.0, 0.0

    def trial(exx, eyy_):
        el = [exx - ep[0], eyy_ - ep[1], -ep[2]]
        tr = sum(el)
        s = [2 * G * (x - tr / 3.0) + K * tr for x in el]
        sm = sum(s) / 3.0
        sd = [x - sm for x in s]
        q = math.sqrt(1.5 * sum(x * x for x in sd))
        if q <= SY:
            return s, 0.0, sd, q
        return [sm + SY / q * x for x in sd], (q - SY) / (3 * G), sd, q

    s = [0.0, 0.0, 0.0]
    for k in range(1, n + 1):
        exx = _e(t * k / float(n), deformation)
        a, b = eyy - 1e-3, eyy + 1e-3
        fa, fb = trial(exx, a)[0][1], trial(exx, b)[0][1]
        for _i in range(60):
            c = b - fb * (b - a) / (fb - fa) if fb != fa else b
            fc = trial(exx, c)[0][1]
            a, fa, b, fb = b, fb, c, fc
            if abs(fc) < 1e-3:
                break
        eyy = b
        s, dp, sd, q = trial(exx, eyy)
        if dp > 0.0:
            for i in range(3):
                ep[i] += 1.5 * dp * sd[i] / q
            p += dp
    return s[0] if stress_xx else p


def _shear(t):
    """PL-73: p and tau for simple shear gamma(t) = GAMMA t, PETIT, linear
    kinematic hardening (monotonic = isotropic): q = sqrt3 tau = sigma_y +
    H p, gamma = tau / G + sqrt3 p."""
    g = GAMMA * t
    gy = SY / (math.sqrt(3.0) * G)
    if g <= gy:
        return 0.0, G * g
    p = (g - gy) / (H73 / (math.sqrt(3.0) * G) + math.sqrt(3.0))
    return p, (SY + H73 * p) / math.sqrt(3.0)


def _kinematic_uniaxial(t):
    """PL-72k: uniaxial monotonic, linear kinematic hardening (= isotropic
    when monotonic), log strain: tau = sigma_y + H p, e = tau / E + p."""
    return max(0.0, (E * _e(t) - SY) / (E + H73))


def _fail_step(pfun, limit):
    """First stored step with p >= limit (the failure time)."""
    k = 1
    while k * STEP <= 1.0 + 1e-9:
        if pfun(k * STEP) >= limit:
            return k * STEP
        k += 1
    return None


def _limit_between(pfun):
    """A failure limit halfway (in p) between the steps around p = 0.02:
    robust against small differences in the strain measure."""
    k = 1
    while pfun(k * STEP) < 0.02:
        k += 1
    return round(0.5 * (pfun((k - 1) * STEP) + pfun(k * STEP)), 5)


def _custom(m, mod, limit):
    m.add(u"<ccxmodeldefinition>**ASTER-PLANE %s\n"
          u"** ASTER-BEZWIJKEN Bros = %g</ccxmodeldefinition>" % (mod, limit))
    for fv in ("displacement", "stress", "von Mises stress",
               "reaction force"):
        m.add('<fieldvariable name="%s" />' % fv)


def _mats(m, plastic):
    for name in ("Bros", "Taai"):
        m.mat(name, '<geometric type="Plate" thickness="%g mm" />'
              % (T * 1000), STEEL, plastic)


def _hold(m, sel, axis, value_mm=None):
    d = dict((a, 1 if a == axis else 0) for a in "xyz")
    if value_mm is None:
        val = "<value>0 mm</value>"
    else:
        val = ('<value time="0 s">0 mm</value><value time="1 s">%.12g mm'
               '</value>' % value_mm)
    m.add('<displacement selection="{0}">{1}<x>{x}</x><y>{y}</y><z>{z}</z>'
          '</displacement>'.format(sel, val, **d))


def build_strip(mod, limit, plastic=PERFECT):
    def build():
        m = Model("L30", timesteps=TS)
        axis = mod == "AXIS"
        m.elset("Taai", "Taai")
        m.elset("Bros", "Bros")
        for k in range(NE):
            elset = "Bros" if k == NE // 2 else "Taai"
            if axis:
                quadmesh(m, elset, 1, 1, rect(RA, RA + W, k * L / NE,
                                              (k + 1) * L / NE))
            else:
                quadmesh(m, elset, 1, 1, rect(k * L / NE, (k + 1) * L / NE,
                                              0.0, W))
        _mats(m, plastic)
        c = 1 if axis else 0
        m.node_selection("Vast", [i + 1 for i, p in enumerate(m.nodes)
                                  if p[c] < 1e-12])
        m.node_selection("Trek", [i + 1 for i, p in enumerate(m.nodes)
                                  if p[c] > L - 1e-12])
        ax = "y" if axis else "x"
        _hold(m, "Vast", ax)
        _hold(m, "Trek", ax, U * 1000)
        if not axis:
            m.node_selection("Punt", [m.node(0.0, 0.0, 0.0)])
            _hold(m, "Punt", "y")
        _custom(m, mod, limit)
        return m
    return build


def build_shear(limit):
    """PL-73: one row of five quad4 in C_PLAN, bottom held, top moved by
    GAMMA W t along x (every node prescribed: uniform simple shear)."""
    def build():
        m = Model("L30", timesteps=TS)
        m.elset("Taai", "Taai")
        m.elset("Bros", "Bros")
        for k in range(NE):
            quadmesh(m, "Bros" if k == NE // 2 else "Taai", 1, 1,
                     rect(k * L / NE, (k + 1) * L / NE, 0.0, W))
        _mats(m, KINEMATIC)
        m.node_selection("Onder", [i + 1 for i, p in enumerate(m.nodes)
                                   if p[1] < 1e-12])
        m.node_selection("Boven", [i + 1 for i, p in enumerate(m.nodes)
                                   if p[1] > W - 1e-12])
        m.add('<fixed selection="Onder" />')
        _hold(m, "Boven", "y")
        _hold(m, "Boven", "x", GAMMA * W * 1000)
        _custom(m, "C_PLAN", limit)
        return m
    return build


def build_parallel(limit):
    """PL-74: two concentric rings (AXIS) of five quad4 each, the inner one
    'Bros', pulled along Y."""
    def build():
        m = Model("L30", timesteps=TS)
        m.elset("Taai", "Taai")
        m.elset("Bros", "Bros")
        quadmesh(m, "Bros", 1, NE, rect(RA, RA + W / 2, 0.0, L))
        quadmesh(m, "Taai", 1, NE, rect(RA + W / 2, RA + W, 0.0, L))
        _mats(m, PERFECT)
        m.node_selection("Vast", [i + 1 for i, p in enumerate(m.nodes)
                                  if p[1] < 1e-12])
        m.node_selection("Trek", [i + 1 for i, p in enumerate(m.nodes)
                                  if p[1] > L - 1e-12])
        _hold(m, "Vast", "y")
        _hold(m, "Trek", "y", U * 1000)
        _custom(m, "AXIS", limit)
        return m
    return build


# --- result readers ----------------------------------------------------
def _bros_ids(r):
    return set(e[0] for es in r.model.elsets if es[0] == "Bros"
               for e in es[2])


def _n_failed(t):
    def f(r):
        v = r.elem("failed", time=t)
        return sum(1 for vals in v.values() if max(vals) > 0.5)
    return f


def _failed_is_bros(r):
    v = r.elem("failed", time=1.0)
    got = set(e for e, vals in v.items() if max(vals) > 0.5)
    n = sum(len(es[2]) for es in r.model.elsets)
    return 1.0 if got == _bros_ids(r) and len(v) == n else 0.0


def _first_failed_step(r):
    for t in r.times():
        v = r.elem("failed", time=t)
        if any(max(vals) > 0.5 for vals in v.values()):
            return t
    return float("nan")


def _reaction(var, sel, t):
    def f(r):
        return -r.total(var, sel, time=t)
    return f


def _area(mod):
    return math.pi * ((RA + W) ** 2 - RA ** 2) if mod == "AXIS" else W * T


def _common(tf):
    return [
        Check("bezwijkstap (eerste stap met p >= grens)",
              lambda r: _first_failed_step(r) - STEP, ref=tf, tol_abs=1e-6,
              unit="s", in_series=False,
              source="closed form p(t) bij een uniform veld"),
        Check("aantal bezweken op t = %g s" % tf, _n_failed(tf), ref=0.0,
              tol_abs=0.5, in_series=False,
              source="failed = 1 pas vanaf de stap na t_fail (contract)"),
        Check("bezweken = de elementen van 'Bros' (t = 1 s)",
              _failed_is_bros, ref=1.0, tol_abs=0.5, in_series=False,
              source="alleen 'Bros' heeft een grens")]


def _checks_strip(mod, pfun, limit, deformation="GDEF_LOG", known=None):
    tf = _fail_step(pfun, limit)
    a0 = _area(mod)
    if mod == "D_PLAN":
        tau = _plane_strain(tf, stress_xx=True, deformation=deformation)
    elif pfun is _kinematic_uniaxial:
        tau = SY + H73 * pfun(tf)
    else:
        tau = SY
    # Cauchy x current area: T A0 / (1 + u/L) (volume kept in plastic
    # flow, elastic change ~1e-3); PETIT: sigma A0
    f_pre = tau * a0 / (1.0 if deformation == "PETIT" else
                        1.0 + U * tf / L)
    var = "reactionforcey" if mod == "AXIS" else "reactionforcex"
    out = _common(tf)
    out += [
        Check("reactie t = %g s (voor bezwijken)" % tf,
              _reaction(var, "Vast", tf), ref=f_pre, tol=0.005, unit="N",
              in_series=False, known=known,
              source="F = T_xx A0 / (1 + u/L), T_xx = %s%s" % (
                  "J2 vlakke rek" if mod == "D_PLAN" else "sigma_y",
                  " (x 2 pi: hele ring)" if mod == "AXIS" else
                  " (dikte 1 mm)")),
        Check("reactie t = 1 s (na bezwijken)", _reaction(var, "Vast", 1.0),
              ref=0.0, tol_abs=0.01 * SY * a0, unit="N", in_series=False,
              source="zacht element in serie: ~0 (factor 1e-6)")]
    return out


def _ratio70(t):
    """KNOWN_BUGS 144: C_PLAN with GDEF_LOG, reaction / (sigma_y A0 /
    (1 + u/L)) at time t (pins the measured deviation)."""
    def f(r):
        return -r.total("reactionforcex", "Vast", time=t) / (
            SY * W * T / (1.0 + U * t / L))
    return f


def _checks70(limit, what="GDEF_LOG"):
    out = _checks_strip("C_PLAN", _uniaxial(), limit, known="KNOWN_BUGS 144")
    for t in (0.2, 0.4):
        out.append(Check(
            "C_PLAN %s: reactie / exact t = %g s (KNOWN_BUGS 144)" % (what, t),
            _ratio70(t), ref=math.sqrt(1.0 + U * t / L), tol=2e-3,
            in_series=False,
            source="gemeten afwijking ~ sqrt(1 + u/L): de dikte volgt de "
                   "grote rek niet (oorzaak NIET geverifieerd)"))
    return out


def _checks73(limit):
    tf = _fail_step(lambda t: _shear(t)[0], limit)
    out = _common(tf)
    out += [
        Check("schuifreactie t = %g s (voor bezwijken)" % tf,
              _reaction("reactionforcex", "Boven", tf),
              ref=-_shear(tf)[1] * L * T, tol=0.005, unit="N",
              in_series=False,
              source="tau = (sigma_y + H p) / sqrt3, gamma = tau / G + "
                     "sqrt3 p; F = tau L t"),
        Check("schuifreactie t = 1 s (na bezwijken: 4/5 van L)",
              _reaction("reactionforcex", "Boven", 1.0),
              ref=-_shear(1.0)[1] * L * T * (NE - 1) / NE, tol=0.005,
              unit="N", in_series=False,
              source="'Bros' zacht, de vier andere elementen dragen")]
    return out


def _checks74(limit):
    tf = _fail_step(_uniaxial(), limit)
    a_out = math.pi * ((RA + W) ** 2 - (RA + W / 2) ** 2)
    out = _common(tf)
    out += [
        Check("reactie t = %g s (voor bezwijken, beide ringen)" % tf,
              _reaction("reactionforcey", "Vast", tf),
              ref=SY * _area("AXIS") / (1.0 + U * tf / L), tol=0.005,
              unit="N", in_series=False,
              source="T = sigma_y, F = T A0 / (1 + u/L) (x 2 pi)"),
        Check("reactie t = 1 s (na bezwijken, alleen de buitenring)",
              _reaction("reactionforcey", "Vast", 1.0),
              ref=SY * a_out / (1.0 + U / L), tol=0.005, unit="N",
              in_series=False,
              source="de binnenring zacht: sigma_y x de buitenring")]
    return out


TESTS = []
_NOTE = ("Strook van 5 quad4 (L = 50 mm), ideaal plastisch sigma_y = 250 MPa, "
         "verlenging 2 mm in 20 stappen; alleen het middelste element heeft "
         "#ASTER-BEZWIJKEN = %g%s.")
for _id, _mod, _deform, _plastic, _p, _what in (
        ("PL-70", "C_PLAN", None, PERFECT, _uniaxial(), ""),
        ("PL-70p", "C_PLAN", "PETIT", PERFECT, _uniaxial("PETIT"), ", PETIT"),
        ("PL-70r", "C_PLAN", "PETIT_REAC", PERFECT, _uniaxial(),
         ", PETIT_REAC"),
        ("PL-71", "D_PLAN", None, PERFECT, _plane_strain, ""),
        ("PL-71s", "D_PLAN", "SIMO_MIEHE", PERFECT, _plane_strain,
         ", SIMO_MIEHE"),
        ("PL-71p", "D_PLAN", "PETIT", PERFECT,
         lambda t: _plane_strain(t, deformation="PETIT"), ", PETIT"),
        ("PL-71r", "D_PLAN", "PETIT_REAC", PERFECT, _plane_strain,
         ", PETIT_REAC"),
        ("PL-72", "AXIS", None, PERFECT, _uniaxial(), ""),
        ("PL-72s", "AXIS", "SIMO_MIEHE", PERFECT, _uniaxial(), ", SIMO_MIEHE"),
        ("PL-72p", "AXIS", "PETIT", PERFECT, _uniaxial("PETIT"), ", PETIT"),
        ("PL-72r", "AXIS", "PETIT_REAC", PERFECT, _uniaxial(),
         ", PETIT_REAC"),
        ("PL-72c", "AXIS", None, CURVE, _uniaxial(),
         ", verstevigingskromme (VMIS_ISOT_TRAC)"),
        ("PL-72k", "AXIS", None, KINEMATIC, _kinematic_uniaxial,
         ", kinematisch (VMIS_CINE_LINE)")):
    _lim = _limit_between(_p)
    if _id in ("PL-70", "PL-70r"):
        _checks = _checks70(_lim, _deform or "GDEF_LOG")
    else:
        # PETIT_REAC in C_PLAN: the same deviation as GDEF_LOG (the
        # width follows the strain, the thickness not)
        _checks = _checks_strip(_mod, _p, _lim,
                                deformation=_deform or "GDEF_LOG",
                                known="KNOWN_BUGS 144" if _id == "PL-70r"
                                else None)
    TESTS.append(Case(
        _id, GROUP, "Bezwijken van een element in 2D (L30 + #ASTER-PLANE "
        "%s + #ASTER-BEZWIJKEN%s)" % (_mod, _what), "nonlin_static_3d",
        build_strip(_mod, _lim, _plastic), _checks,
        settings={"deformation": _deform} if _deform else None,
        note=_NOTE % (_lim, _what)))
_LIM73 = _limit_between(lambda t: _shear(t)[0])
TESTS.append(Case(
    "PL-73", GROUP, "Bezwijken in 2D met kinematische versteviging, "
    "afschuiving (L30 + #ASTER-PLANE C_PLAN + #ASTER-BEZWIJKEN)",
    "nonlin_static_3d", build_shear(_LIM73), _checks73(_LIM73),
    settings={"deformation": "PETIT"},
    note="Rij van 5 quad4, onderrand vast, bovenrand verschoven tot gamma = "
         "0,08 (alle knopen opgelegd), BilinearKinematic sigma_y = 250 MPa, "
         "H = 2,1 GPa, PETIT; grens %g." % _LIM73))
_LIM74 = _limit_between(_uniaxial())
TESTS.append(Case(
    "PL-74", GROUP, "Bezwijken in 2D, parallel: twee ringen (L30 + "
    "#ASTER-PLANE AXIS + #ASTER-BEZWIJKEN)", "nonlin_static_3d",
    build_parallel(_LIM74), _checks74(_LIM74),
    note="Binnenring 100 .. 105 mm ('Bros'), buitenring 105 .. 110 mm, elk 5 "
         "quad4 over 50 mm, axiaal getrokken tot 2 mm; grens %g." % _LIM74))
