# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Materialen in niet-lineaire analyses (Mecway L30/D31).

  NL-04  hardingscurve (totale rek) waarvan de helling van het eerste stuk
         (210 GPa) afwijkt van youngsmodulus op het tabblad Elastic
         (200 GPa): de bridge neemt E = helling van de curve, zoals Mecway
         (GitHub issue #2). b: dezelfde curve als Kinematic (lineair ->
         VMIS_CINE_LINE).
  NL-50  hyperelastisch (GitHub issue #5): kubus in eenassige trek
         (lambda = 1,5) en druk (lambda = 0,7), Neo Hooke en Mooney-Rivlin,
         nagenoeg onsamendrukbaar (K = 1000 G); NL-52: Neo Hooke in
         Dynamisch (impliciet), quasi-statisch.

Mecway-metingen (headless, Mecway 34 + CCX, 22 okt 2026), zie de toelichting
per case: NL-04 sigma 104,97 MPa bij rek 5e-4 (E = 210 GPa), NL-50/51
binnen 0,11% van de analytische waarde.
"""
import math
from verif_lib import Case, Check, Model, hexmesh, box

GROUP = "Niet-lineair statisch"

# ------------------------------------------------------------------
# NL-04 Trekstaaf, hardingscurve met E_tab != helling van de curve
# ------------------------------------------------------------------
E_TAB, E4 = 200e9, 210e9                    # Pa (tabblad / curve)
CURVE4 = [(0.0, 0.0), (0.001, 210e6), (0.011, 310e6)]
L4, A4 = 0.100, 0.010
U4 = [(0.0, 0.0), (1.0, 0.05e-3), (2.0, 0.5e-3)]   # m (rek 5e-4, 5e-3)
MID4 = (L4 / 2, A4 / 2, A4 / 2)


def build_nl04(kind):
    def build():
        m = Model("L30", timesteps={"timeperiod": "2 s",
                                    "stepsize": "0.1 s"})
        m.elset("Staaf", "Staal")
        g = hexmesh(m, "Staaf", 2, 1, 1, box(0, L4, 0, A4, 0, A4), order=2)
        m.mat("Staal", '<mechanical type="Isotropic" youngsmodulus='
              '"200000 MPa" poissonratio="0.3" />',
              '<plastic type="%s">%s</plastic>' % (kind, "".join(
                  '<hardeningcurve strain="%g" stress="%g MPa" />'
                  % (e, s / 1e6) for e, s in CURVE4)))
        for name, side, ax in (("SymX", "u0", "x"), ("SymY", "v0", "y"),
                               ("SymZ", "w0", "z")):
            m.node_selection(name, sorted(g["nodes"][side]))
            d = dict((a, 1 if a == ax else 0) for a in "xyz")
            m.add('<displacement selection="{0}"><value>0 mm</value>'
                  '<x>{x}</x><y>{y}</y><z>{z}</z></displacement>'.format(
                      name, **d))
        m.node_selection("Trek", sorted(g["nodes"]["u1"]))
        m.add('<displacement selection="Trek">%s<x>1</x><y>0</y><z>0</z>'
              '</displacement>' % "".join(
                  '<value time="%g s">%.12g mm</value>' % (t, u * 1e3)
                  for t, u in U4))
        return m
    return build


def _nl04_state(t):
    """Eenassig, GDEF_LOG: tau(eps_log) volgt de curve in totale rek met
    E = 210 GPa (elastisch tot 0,001, daarna helling 10 GPa; monotoon, dus
    isotroop = kinematisch). F = tau A0 / (1 + e), sigma = tau / J."""
    e = dict(U4)[t] / L4
    el = math.log(1.0 + e)
    if el <= CURVE4[1][0]:
        tau = E4 * el
    else:
        (e1, s1), (e2, s2) = CURVE4[1], CURVE4[2]
        tau = s1 + (s2 - s1) / (e2 - e1) * (el - e1)
    j = math.exp(tau * (1 - 2 * 0.3) / E4)
    return {"F": tau * A4 * A4 / (1.0 + e), "sigma": tau / j}


def _nl04_checks():
    src = ("eenassig, log-rek, curve in totale rek met E = helling eerste "
           "stuk (210 GPa)")
    out = []
    for t, what in ((1.0, "elastisch"), (2.0, "plastisch")):
        s = _nl04_state(t)
        out.append(Check("F t=%g (%s)" % (t, what),
                         (lambda tt: lambda r: r.total(
                             "reactionforcex", "Trek", time=tt))(t),
                         ref=s["F"], tol=0.002, unit="N", source=src))
    s = _nl04_state(1.0)
    out.append(Check("sigma_xx t=1 (E = 210 GPa)", lambda r: r.at(
        "stressxx", MID4, time=1.0), ref=s["sigma"], tol=0.002, unit="Pa",
        source="sigma = E eps_log / J; Mecway/CCX: 104,97 MPa"))
    return out


# ------------------------------------------------------------------
# NL-50..52 Hyperelastische kubus, eenassig
# ------------------------------------------------------------------
# Onsamendrukbaar, eenassig: nominale spanning
#   P = 2 (lambda - lambda^-2) (C10 + C01 / lambda),
# Cauchy sigma = lambda P (Treloar; Mooney-Rivlin W = C10 (I1 - 3) +
# C01 (I2 - 3)). K = 2/D1 = 1000 G: de samendrukbaarheid verandert P
# minder dan 0,1%.
H5 = 0.010                                  # m, ribbe van de kubus
D1 = 1.0e-9                                 # m2/N (K = 2 GPa)


def _hyper_mat(c10, c01):
    if c01:
        return ('<mechanical type="MooneyRivlin" hyperelasticc10="%g MPa" '
                'hyperelasticc01="%g MPa" d1="%g m²/N" />'
                % (c10 / 1e6, c01 / 1e6, D1))
    return ('<mechanical type="NeoHooke" hyperelasticc10="%g MPa" '
            'd1="%g m²/N" />' % (c10 / 1e6, D1))


def build_nl50(c10, c01, lam, dynamic=False, t_end=1.0):
    def build():
        if dynamic:
            m = Model("D31", timesteps={
                "timeperiod": "%r s" % t_end,
                "automatictimestepping": "false",
                "outputtimes": "regular", "timepointsstart": "0 s",
                "timepointsincrement": "%r s" % (t_end / 20)})
        else:
            m = Model("L30", timesteps={"timeperiod": "1 s",
                                        "stepsize": "0.05 s"})
        m.elset("Kubus", "Rubber")
        g = hexmesh(m, "Kubus", 1, 1, 1, box(0, H5, 0, H5, 0, H5), order=1)
        lines = [_hyper_mat(c10, c01)]
        if dynamic:
            lines.append('<density type="Simple" density="1000 kg/m³" />')
        m.mat("Rubber", *lines)
        for name, side, ax in (("SymX", "u0", "x"), ("SymY", "v0", "y"),
                               ("SymZ", "w0", "z")):
            m.node_selection(name, sorted(g["nodes"][side]))
            d = dict((a, 1 if a == ax else 0) for a in "xyz")
            m.add('<displacement selection="{0}"><value>0 mm</value>'
                  '<x>{x}</x><y>{y}</y><z>{z}</z></displacement>'.format(
                      name, **d))
        m.node_selection("Trek", sorted(g["nodes"]["u1"]))
        m.add('<displacement selection="Trek"><value time="0 s">0 mm</value>'
              '<value time="%r s">%.12g mm</value><x>1</x><y>0</y><z>0</z>'
              '</displacement>' % (t_end, (lam - 1.0) * H5 * 1e3))
        return m
    return build


def _nl50_checks(c10, c01, lam, mecway=None, t_end=1.0, tol=0.005):
    p = 2.0 * (lam - lam ** -2) * (c10 + c01 / lam)
    src = "P = 2 (l - l^-2) (C10 + C01/l), onsamendrukbaar"
    note = "" if mecway is None else "; Mecway/CCX sigma %s MPa" % mecway
    mid = (H5 / 2, H5 / 2, H5 / 2)
    return [
        Check("F (nominaal, l=%g)" % lam, lambda r: r.total(
            "reactionforcex", "Trek", time=t_end), ref=p * H5 * H5, tol=tol,
            unit="N", source=src),
        Check("sigma_xx Cauchy (l=%g)" % lam, lambda r: r.at(
            "stressxx", mid, time=t_end), ref=lam * p, tol=tol, unit="Pa",
            source="sigma = l P" + note),
    ]


C10N, C10M, C01M = 1.0e6, 0.8e6, 0.2e6

TESTS = [
    Case("NL-04", GROUP, "Trekstaaf, hardingscurve met E (tabblad) != "
         "helling van de curve", "nonlin_static_3d", build_nl04("Isotropic"),
         _nl04_checks(),
         note="youngsmodulus 200 GPa, curve (0,0), (0,001; 210 MPa), "
              "(0,011; 310 MPa): E = 210 GPa zoals Mecway (WARNING). "
              "Mecway/CCX: sigma 104,97 MPa bij t = 1, 248,1 MPa bij t = 2."),
    Case("NL-04b", GROUP, "Als NL-04 met een kinematische (lineaire) curve",
         "nonlin_static_3d", build_nl04("Kinematic"), _nl04_checks(),
         note="Kinematic, lineaire versteviging -> VMIS_CINE_LINE met "
              "E = 210 GPa; monotoon gelijk aan NL-04."),
    Case("NL-50", GROUP, "Hyperelastisch: kubus Neo Hooke, trek l = 1,5",
         "nonlin_static_3d", build_nl50(C10N, 0.0, 1.5),
         _nl50_checks(C10N, 0.0, 1.5, "3,163"),
         note="hex8, C10 = 1 MPa, D1 = 1e-9 m2/N (K = 2 GPa)."),
    Case("NL-50b", GROUP, "Hyperelastisch: kubus Neo Hooke, druk l = 0,7",
         "nonlin_static_3d", build_nl50(C10N, 0.0, 0.7),
         _nl50_checks(C10N, 0.0, 0.7, "-1,877")),
    Case("NL-51", GROUP, "Hyperelastisch: kubus Mooney-Rivlin, trek "
         "l = 1,5", "nonlin_static_3d", build_nl50(C10M, C01M, 1.5),
         _nl50_checks(C10M, C01M, 1.5, "2,952"),
         note="C10 = 0,8 MPa, C01 = 0,2 MPa."),
    Case("NL-51b", GROUP, "Hyperelastisch: kubus Mooney-Rivlin, druk "
         "l = 0,7", "nonlin_static_3d", build_nl50(C10M, C01M, 0.7),
         _nl50_checks(C10M, C01M, 0.7, "-2,038")),
    Case("NL-52", GROUP, "Hyperelastisch: Neo Hooke trek l = 1,5 in "
         "Dynamisch (impliciet), quasi-statisch", "dyna_impl_3d",
         build_nl50(C10N, 0.0, 1.5, dynamic=True),
         _nl50_checks(C10N, 0.0, 1.5),
         note="rho = 1000 kg/m3, 1 s: traagheid verwaarloosbaar."),
    Case("NL-53", GROUP, "Hyperelastisch: Neo Hooke trek l = 1,5 in "
         "Dynamisch (expliciet), 20 ms", "dyna_expl_3d",
         build_nl50(C10N, 0.0, 1.5, dynamic=True, t_end=0.02),
         _nl50_checks(C10N, 0.0, 1.5, t_end=0.02, tol=0.02),
         note="rho = 1000 kg/m3; 20 ms is ongeveer 20 x de eerste "
              "eigenperiode (traagheid < 1%). Tijdstap uit E en NU van "
              "de kleine rek (E = 2 G (1 + NU))."),
]
