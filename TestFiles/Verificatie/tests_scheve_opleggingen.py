# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Skew supports that overlap with imposed displacements (GitHub issue #9,
Dlubal verification example 0109 "Natural Vibrations of Circular Plate").
The rim of a round plate gets a frictionless support on the shell edges
(normal = radial, plus the rotation about the edge) and displacement
X = Y = Z = 0 on the same nodes. Mecway reduces that to a minimum set
(manual par. 9.6); in Code-Aster the dualised conditions were linearly
dependent (CALC_MODES <EXCEPTION> ALGELINE3_81). The bridge now reduces the
relation where the DDL_IMPO already covers it
(bridge_mesh._trim_covered_relations). Explanation: docs/en/Verification.md
(MO-09, LS-83).

Plate: radius a = 0.5 m, t = 1 mm, steel (E = 210 GPa, nu = 0.3,
rho = 7850 kg/m3), quad8 O-grid (verif_lib.diskmesh), so clamped
(Kirchhoff): f = lambda^2 / (2 pi a^2) sqrt(D / (rho t)).
"""
import math
from verif_lib import Case, Check, Model, diskmesh, quadmesh, rect

E, NU, RHO = 210e9, 0.3, 7850.0
A9, T9 = 0.5, 0.001
D9 = E * T9 ** 3 / (12 * (1 - NU ** 2))
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
DENS = '<density type="Simple" density="7850 kg/m³" />'
N9, NR9 = 8, 6

# Dlubal verification example 0109 (analytical solution, the values of the
# issue); f1 = 10.2158 / (2 pi a^2) sqrt(D / (rho t)) = 10.179 Hz (Leissa,
# Vibration of Plates, NASA SP-160, 1969, clamped circular plate).
F_REF = (10.179, 21.184, 34.752, 39.629, 50.847, 60.611)
# mode numbers of the six distinct frequencies (pairs with 1, 2 and 3
# nodal diameters are double)
MODE_OF = (1, 2, 4, 6, 7, 9)
# Mecway 34 (internal solver, headless mw_solve.py) on modellen/MO-09.liml
MW_MO09 = (10.17924, 21.18543, 34.75986, 39.63872, 50.87891, 60.65048)

P9 = 10.0                                   # Pa
W9 = P9 * A9 ** 4 / (64 * D9)               # clamped, centre (Timoshenko)
# Mecway 34 on modellen/LS-83.liml: |w| at the centre
MW_LS83 = 5.078427e-4


def _plate(analysis, attrs=None):
    m = Model(analysis, attrs=attrs)
    m.elset("Plaat", "Plaat1")
    mesh = diskmesh(m, "Plaat", A9, N9, NR9)
    m.mat("Plaat1", '<geometric type="Plate" thickness="%g m" />' % T9,
          STEEL, DENS)
    m.face_selection("RandRanden", mesh["rim_edges"])
    m.node_selection("RandKnopen", sorted(mesh["rim_nodes"]))
    # as in the model of issue #9 (reconstructed from its CCX export):
    # frictionless on the rim edges plus X, Y, Z on the rim nodes
    m.add('<frictionless selection="RandRanden" />')
    for d in ("<x>1</x><y>0</y><z>0</z>", "<x>0</x><y>1</y><z>0</z>",
              "<x>0</x><y>0</y><z>1</z>"):
        m.add('<displacement selection="RandKnopen"><value>0 m</value>%s'
              '</displacement>' % d)
    return m, mesh


def build_mo09():
    return _plate("V30", {"maxmode": 10})[0]


def build_ls83():
    m, mesh = _plate("S30")
    m.face_selection("Vlak", mesh["faces"])
    m.add('<surfacepressure selection="Vlak"><normal>%g Pa</normal>'
          '</surfacepressure>' % P9)
    return m


def _mo09_checks():
    out = []
    for i, (k, f) in enumerate(zip(MODE_OF, F_REF)):
        out.append(Check("f%d (mode %d)" % (i + 1, k),
                         lambda r, k=k: r.mode(k), ref=f, tol=0.005,
                         unit="Hz", source="Dlubal 0109, analytical "
                         "(clamped Kirchhoff plate)"))
        if MW_MO09[i]:
            out.append(Check("f%d t.o.v. Mecway" % (i + 1),
                             lambda r, k=k: r.mode(k), ref=MW_MO09[i],
                             tol=0.003, unit="Hz", in_series=False,
                             source="Mecway 34 headless, same .liml"))
    return out


def _ls83_checks():
    out = [Check("w midden", lambda r: abs(r.at("displz", (0, 0, 0))),
                 ref=W9, tol=0.01, unit="m",
                 source="p a^4 / (64 D), clamped (Timoshenko, Theory of "
                 "Plates and Shells, par. 62)"),
           Check("reactie Z", lambda r: abs(r.total("reactionforcez",
                                                    "RandKnopen")),
                 ref=P9 * math.pi * A9 ** 2, tol=0.005, unit="N",
                 source="p pi a^2")]
    if MW_LS83:
        out.append(Check("w midden t.o.v. Mecway",
                         lambda r: abs(r.at("displz", (0, 0, 0))),
                         ref=MW_LS83, tol=0.005, unit="m", in_series=False,
                         source="Mecway 34 headless, same .liml"))
    return out


# LS-84: frictionless on a straight shell edge alone (no displacement on the
# same rotations). Strip 1 x 0.2 m, t = 10 mm, quad8 10 x 2; edge x = 0:
# frictionless + Z = 0, node (0, 0, 0) Y = 0; far corners: 10 N in Z at
# (1, 0.2) (bending + twist), 100 N in Y at (1, 0) (in-plane bending).
# Mecway 34 (internal solver, headless) fixes on the edge nodes UX, the
# rotation about the edge (RY) and the drilling rotation about the shell
# normal (RZ, exactly 0), not the rotation about the in-plane edge normal
# (RX). The bridge fixes UX and RY only; the free drilling DOF changes no
# displacement (Mecway with RZ free via an ordinary displacement gives the
# same UY to 5 digits). Mecway values at (1, 0.2, 0) on modellen/LS-84.liml:
MW_LS84 = {"displz": 9.4979e-4, "disply": 2.4443e-5, "roty": -1.4291e-03}


def build_ls84():
    m = Model("S30")
    m.elset("Strook", "Strook1")
    me = quadmesh(m, "Strook", 10, 2, rect(0, 1.0, 0, 0.2), order=2)
    m.mat("Strook1", '<geometric type="Plate" thickness="0.01 m" />', STEEL)
    m.face_selection("Rand", me["edges"]["u0"])
    m.node_selection("RandKnopen", sorted(me["nodes"]["u0"]))
    m.node_selection("O", [m.node(0, 0, 0)])
    m.node_selection("Hoek", [m.node(1.0, 0.2, 0)])
    m.node_selection("Hoek2", [m.node(1.0, 0.0, 0)])
    m.add('<frictionless selection="Rand" />')
    m.add('<displacement selection="RandKnopen"><value>0 m</value><x>0</x>'
          '<y>0</y><z>1</z></displacement>')
    m.add('<displacement selection="O"><value>0 m</value><x>0</x><y>1</y>'
          '<z>0</z></displacement>')
    m.add('<force selection="Hoek"><x>0 N</x><y>0 N</y><z>10 N</z></force>')
    m.add('<force selection="Hoek2"><x>0 N</x><y>100 N</y><z>0 N</z>'
          '</force>')
    return m


def _ls84_checks():
    return [Check("%s hoek t.o.v. Mecway" % v,
                  lambda r, v=v: r.at(v, (1.0, 0.2, 0)), ref=ref, tol=0.01,
                  unit="rad" if v.startswith("rot") else "m",
                  source="Mecway 34 headless, same .liml")
            for v, ref in sorted(MW_LS84.items())]


TESTS = [
    Case("MO-09", "Modaal", "Ronde plaat ingeklemd via frictionless + "
         "displacement op de rand (issue #9)", "modal_3d", build_mo09,
         _mo09_checks(),
         note="quad8 O-grid; frictionless op de randen en X/Y/Z 0 op "
              "dezelfde knopen: de bridge reduceert de dubbele voorwaarde."),
    Case("LS-83", "Lineair statisch", "Ronde plaat onder druk, oplegging "
         "als MO-09", "lin_static_3d", build_ls83, _ls83_checks(),
         note="Zelfde oplegging als MO-09; doorbuiging en reactie."),
    Case("LS-84", "Lineair statisch", "Schaalstrook met frictionless op een "
         "rechte rand (rotatievoorwaarden t.o.v. Mecway)", "lin_static_3d",
         build_ls84, _ls84_checks(),
         note="Mecway zet op de rand ook de draairotatie (RZ) vast, de "
              "bridge niet; geen invloed op de verplaatsingen."),
]
