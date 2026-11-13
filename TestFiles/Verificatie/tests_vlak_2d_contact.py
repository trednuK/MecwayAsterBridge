# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Contact in 2D and axisymmetric (STAPPENPLAN S44b, route A; Scripts/
bridge_plane.py, bridge_mesh.py): Mecway Nonlinear Static (L30) with plane
shell elements, '**ASTER-PLANE' and a Contact between face selections of
shell edges -> DEFI_CONTACT on SEG boundary cells of C_PLAN/D_PLAN/AXIS.
Explanation: docs/Verificatie.md chapter 2D and axisymmetric (PL).

PL-40  shrink fit of two rings (AXIS): inner ring a .. b + delta, outer ring
       b .. c, both ends of both rings held axially (plane strain),
       frictionless: the contact pressure against Lame (plane strain,
       p = delta / (f_i + f_o)).
PL-41  the same in plane strain (D_PLAN, quarter rings, symmetry x = 0 and
       y = 0).
"""
import math

from verif_lib import Case, Check, Model, quadmesh, rect

GROUP = "2D en axisymmetrisch"
E, NU = 210e9, 0.3
RA, RB, RC, H = 0.10, 0.15, 0.20, 0.01
DELTA = 5.0e-5              # radial interference
NR = 8                      # quad8 through each wall
STEEL = ('<geometric type="Plate" thickness="10 mm" />',
         '<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
TS = {"timeperiod": "1 s", "stepsize": "1 s"}


def _u_per_p(r, a, b, inner):
    """Radial displacement at r of a ring a .. b per unit pressure on its
    inner (inner=True) or outer wall; Lame, plane strain."""
    pi, po = (1.0, 0.0) if inner else (0.0, 1.0)
    A = (pi * a ** 2 - po * b ** 2) / (b ** 2 - a ** 2)
    B = (pi - po) * a ** 2 * b ** 2 / (b ** 2 - a ** 2)
    return (1.0 + NU) / E * ((1.0 - 2.0 * NU) * A * r + B / r)


# inner ring: outer pressure p shrinks it; outer ring: inner pressure p
P_FIT = DELTA / (-_u_per_p(RB, RA, RB, False) + _u_per_p(RB, RB, RC, True))


def _contact(m):
    m.add('<contact2 selectionmaster="Buitenring_binnen" selectionslave='
          '"Binnenring_buiten" type="unilateralelastic"><tolerance>0 m'
          '</tolerance><normalstiffness>1000 GPa/m</normalstiffness>'
          '<tangentialstiffness>0 GPa/m</tangentialstiffness>'
          '<frictioncoefficient>0</frictioncoefficient></contact2>')


def _finish(m, mod):
    m.add(u"<ccxmodeldefinition>**ASTER-PLANE %s</ccxmodeldefinition>" % mod)
    for fv in ("displacement", "stress", "von Mises stress",
               "reaction force", "contact"):
        m.add('<fieldvariable name="%s" />' % fv)


def build_pl40():
    m = Model("L30", timesteps=TS)
    m.elset("Binnen", "Staal")
    m.elset("Buiten", "Staal")
    qi = quadmesh(m, "Binnen", NR, 1, rect(RA, RB + DELTA, 0.0, H), order=2)
    qo = quadmesh(m, "Buiten", NR, 1, rect(RB, RC, 0.0, H), order=2)
    m.mat("Staal", *STEEL)
    m.face_selection("Binnenring_buiten", qi["edges"]["u1"])
    m.face_selection("Buitenring_binnen", qo["edges"]["u0"])
    m.node_selection("Slave", sorted(qi["nodes"]["u1"]))
    m.face_selection("Einden", qi["edges"]["v0"] + qi["edges"]["v1"] +
                     qo["edges"]["v0"] + qo["edges"]["v1"])
    m.add('<displacement selection="Einden"><value>0 m</value><x>0</x>'
          '<y>1</y><z>0</z></displacement>')
    _contact(m)
    _finish(m, "AXIS")
    return m


def _ring(r0, r1):
    def f(u, v):
        r = r0 + u * (r1 - r0)
        t = v * math.pi / 2
        return (r * math.cos(t), r * math.sin(t), 0.0)
    return f


def build_pl41():
    m = Model("L30", timesteps=TS)
    m.elset("Binnen", "Staal")
    m.elset("Buiten", "Staal")
    qi = quadmesh(m, "Binnen", NR, 8, _ring(RA, RB + DELTA), order=2)
    qo = quadmesh(m, "Buiten", NR, 8, _ring(RB, RC), order=2)
    m.mat("Staal", *STEEL)
    m.face_selection("Binnenring_buiten", qi["edges"]["u1"])
    m.face_selection("Buitenring_binnen", qo["edges"]["u0"])
    m.node_selection("Slave", sorted(qi["nodes"]["u1"]))
    m.face_selection("SymY0", qi["edges"]["v0"] + qo["edges"]["v0"])
    m.face_selection("SymX0", qi["edges"]["v1"] + qo["edges"]["v1"])
    m.add('<symmetry selection="SymY0"><x>0</x><y>1</y><z>0</z>'
          '</symmetry>')
    m.add('<symmetry selection="SymX0"><x>1</x><y>0</y><z>0</z>'
          '</symmetry>')
    _contact(m)
    _finish(m, "D_PLAN")
    return m


def _checks(plane=False):
    """plane: D_PLAN quarter rings; their nodal sigma_r at the contact wall
    is +2.4% (also at 45 degrees: the extrapolation in elements with an
    aspect ratio of about 5, as PL-03 has no sigma_r check), so only the
    contact pressure and u_r there."""
    src = "Lame, vlakke rek: p = delta / (f_binnen + f_buiten)"
    sr = [] if plane else [
        Check("-sigma_r buitenring binnenwand",
              lambda r: -r.at("stressxx", (RB, 0.0, 0.0), time=1.0),
              ref=P_FIT, tol=0.01, unit="Pa", source=src)]
    return [
        Check("contactdruk (gemiddeld, slave)",
              lambda r: r.mean("contactpressure", "Slave", time=1.0),
              ref=P_FIT, tol=0.01, unit="Pa", source=src)] + sr + [
        Check("u_r buitenring binnenwand",
              lambda r: r.at("displx", (RB, 0.0, 0.0), time=1.0),
              ref=P_FIT * _u_per_p(RB, RB, RC, True), tol=0.01, unit="m",
              source=src)]


TESTS = [
    Case("PL-40", GROUP, "Krimpverbinding twee ringen, axisymmetrisch "
         "(L30 + **ASTER-PLANE AXIS, contact)", "nonlin_static_3d",
         build_pl40, _checks(),
         note="a = 0,1, b = 0,15, c = 0,2 m, overmaat 0,05 mm, quad8 8x1 "
              "per ring, einden axiaal vast, wrijvingsloos."),
    Case("PL-41", GROUP, "Krimpverbinding twee ringen, vlakke rek "
         "(L30 + **ASTER-PLANE D_PLAN, contact)", "nonlin_static_3d",
         build_pl41, _checks(plane=True),
         note="Als PL-40 als kwart ringen quad8 8x8, symmetrie x = 0 en "
              "y = 0."),
]
