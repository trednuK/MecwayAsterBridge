# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Mechanische lasten en voorwaarden met een Mecway-formule in x, y, z
(voorheen KNOWN_BUGS 45; grenzen: KNOWN_BUGS 104): bridge_bcs.PositionFormula
-> FORMULE in AFFE_CHAR_MECA_F.
Referenties: integralen van de formule (resultante en moment), balktheorie
(Roark) en de formule zelf in de knopen. Toelichting: docs/Verificatie.md
(LS-40 .. LS-44, NL-40).

Mecway 34 (headless, TestFiles/Tools/mw_solve.py) op dezelfde modellen:
druk en traction gelijk aan de integraal (zoals de bridge); kracht,
opgelegde verplaatsing/rotatie en line pressure met x, y, z in de formule
legt Mecway niet op (reacties 0), zie de kop van Scripts/bridge_bcs.py.
"""
import math
from verif_lib import Case, Check, Model, hexmesh, box, linemesh, \
    quadmesh, rect

GROUP_LS = "Lineair statisch"
GROUP_NL = "Niet-lineair statisch"
E, NU = 210e9, 0.3
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')


def _f(unit, pos="m"):
    """Attributen van een Mecway-formule (eenheden als attributen)."""
    return 'unit="%s" timeunit="s" positionunit="%s"' % (unit, pos)


def _moment(r, axis, sel="BodemN", time=None):
    """Moment van de reactiekrachten om de X-as (sum y Rz - z Ry) of de
    Y-as (sum z Rx - x Rz) door de oorsprong."""
    st = r.step(time)
    nodes = r.model.nodes
    rz = st["reactionforcez"]
    out = 0.0
    for n in r.model.nodesel[sel]:
        x, y, z = nodes[n - 1]
        if axis == "x":
            out += y * rz.get(n, 0.0) - z * st["reactionforcey"].get(n, 0.0)
        else:
            out += z * st["reactionforcex"].get(n, 0.0) - x * rz.get(n, 0.0)
    return out


# ------------------------------------------------------------------
# Blok 1 x 2 x 0,1 m (hex8 4 x 8 x 1), onderkant vast, last op de bovenkant
# ------------------------------------------------------------------
def _block(loads, analysis="S30", timesteps=None):
    m = Model(analysis, timesteps=timesteps)
    m.elset("Blok", "Staal")
    h = hexmesh(m, "Blok", 4, 8, 1, box(0, 1, 0, 2, 0, 0.1))
    m.mat("Staal", STEEL)
    m.face_selection("Top", h["faces"]["w1"])
    # de bovenkant in twee helften (y < 1 en y > 1)
    m.face_selection("Top1", [(h["elems"][(i, j, 0)], 2)
                              for i in range(4) for j in range(4)])
    m.face_selection("Top2", [(h["elems"][(i, j, 0)], 2)
                              for i in range(4) for j in range(4, 8)])
    m.face_selection("Bodem", h["faces"]["w0"])
    m.node_selection("BodemN", sorted(h["nodes"]["w0"]))
    m.node_selection("TopN", sorted(h["nodes"]["w1"]))
    m.add('<fixed selection="Bodem" />')
    for load in loads:
        m.add(load)
    return m


def build_ls40a():
    return _block(['<surfacepressure selection="Top"><normal %s>3*y^2'
                   '</normal></surfacepressure>' % _f("kPa")])


def build_ls40b():
    # zelfde druk met x, y, z in mm
    return _block(['<surfacepressure selection="Top"><normal %s>3e-6*y^2'
                   '</normal></surfacepressure>' % _f("kPa", "mm")])


def _ls40_checks():
    return [
        Check("reactie Z", lambda r: r.total("reactionforcez", "BodemN"),
              ref=8000.0, tol=1e-6, unit="N",
              source="int 3 y^2 dA = 8 kN (Mecway 34: 8000)"),
        Check("moment om X", lambda r: _moment(r, "x"), ref=12000.0,
              tol=1e-6, unit="N.m",
              source="int 3 y^3 dA = 12 kN.m (Mecway 34: 12000)"),
        Check("moment om Y", lambda r: _moment(r, "y"), ref=-4000.0,
              tol=1e-6, unit="N.m", source="-int 3 x y^2 dA = -4 kN.m")]


def build_ls41():
    return _block([
        '<surfacepressure selection="Top1"><normal %s>3*y^2</normal>'
        '</surfacepressure>' % _f("kPa"),
        '<surfacepressure selection="Top2"><normal %s>10*x</normal>'
        '</surfacepressure>' % _f("kPa"),
        '<traction selection="Top"><x %s>2*x+1</x><y>0 Pa</y>'
        '<z>0 Pa</z></traction>' % _f("kPa")])


def _ls42_build(direction, formula):
    def build():
        return _block(['<displacement selection="TopN"><value %s>%s</value>'
                       '%s</displacement>' % (_f("mm"), formula, direction)])
    return build


def _along(r, point, d):
    """Verplaatsing in point langs richting d (genormaliseerd)."""
    n = math.sqrt(sum(c * c for c in d))
    return sum(r.at(v, point) * c / n
               for v, c in zip(("displx", "disply", "displz"), d))


# ------------------------------------------------------------------
# Ingeklemde balk (10 line2, Ø 20 mm, L = 1 m) met q(x) = -1000 x N/m
# ------------------------------------------------------------------
L3, D3, Q3 = 1.0, 0.020, 1000.0
I3 = math.pi * D3 ** 4 / 64.0
A3 = math.pi * D3 ** 2 / 4.0
RHO3, G3 = 7850.0, 9.81


def _beam(gravity):
    def build():
        m = Model("S30")
        m.elset("Balk", "Rond20")
        eids, nids = linemesh(m, "Balk", 10, (0, 0, 0), (L3, 0, 0))
        mat = ['<geometric type="CircularBar" roundod="20 mm" />', STEEL]
        if gravity:
            mat.append('<density type="Simple" density="%g kg/m³" />' % RHO3)
        m.mat("Rond20", *mat)
        m.node_selection("In", [nids[0]])
        m.node_selection("Tip", [nids[-1]])
        m.element_selection("Alle", eids)
        m.add('<fixed selection="In" />')
        m.add('<linepressure selection="Alle"><x>0 N/m</x><y>0 N/m</y>'
              '<z %s>-1000*x</z></linepressure>' % _f("N/m"))
        if gravity:
            m.add('<gravity><x>0 m/s²</x><y>0 m/s²</y><z>-%g m/s²</z>'
                  '</gravity>' % G3)
        return m
    return build


def build_ls42c():
    m = Model("S30")
    m.elset("Balk", "Rond20")
    _eids, nids = linemesh(m, "Balk", 10, (0, 0, 0), (L3, 0, 0))
    m.mat("Rond20", '<geometric type="CircularBar" roundod="20 mm" />', STEEL)
    m.node_selection("In", [nids[0]])
    m.node_selection("Tip", [nids[-1]])
    m.add('<fixed selection="In" />')
    m.add('<noderotation selection="Tip"><value %s>0.001*(1+x)</value>'
          '<x>0</x><y>1</y><z>0</z></noderotation>' % _f("rad"))
    return m


def _beam_checks(gravity):
    w = RHO3 * A3 * G3 if gravity else 0.0
    return [
        Check("reactie Z", lambda r: r.total("reactionforcez", "In"),
              ref=Q3 * L3 / 2.0 + w * L3, tol=1e-6, unit="N",
              source="int q dx (+ rho A g L)"),
        Check("doorbuiging tip", lambda r: -r.at("displz", (L3, 0, 0)),
              ref=11.0 * Q3 * L3 ** 4 / (120.0 * E * I3)
              + w * L3 ** 4 / (8.0 * E * I3), tol=1e-4, unit="m",
              source="11 q0 L^4/(120 EI) (+ w L^4/(8 EI)), Roark tabel 8.1")]


# ------------------------------------------------------------------
# Plaat 1 x 2 m, t = 10 mm (quad4 4 x 8), rand y = 0 ingeklemd,
# druk 3 y^2 Pa op de schaalvlakken
# ------------------------------------------------------------------
def build_ls44():
    m = Model("S30")
    m.elset("Plaat", "Schaal")
    q = quadmesh(m, "Plaat", 4, 8, rect(0, 1, 0, 2))
    m.mat("Schaal", '<geometric type="Plate" thickness="10 mm" />', STEEL)
    m.node_selection("Rand", sorted(q["nodes"]["v0"]))
    m.node_selection("Tip", sorted(q["nodes"]["v1"]))
    m.face_selection("Vlak", q["faces"])
    # displacement + noderotation i.p.v. fixed: met fixed op een
    # knoopselectie van schalen rekent Mecway 34 headless een mechanisme
    for ax in ("1</x><y>0</y><z>0", "0</x><y>1</y><z>0",
               "0</x><y>0</y><z>1"):
        m.add('<displacement selection="Rand"><value>0 m</value><x>%s</z>'
              '</displacement>' % ax)
        m.add('<noderotation selection="Rand"><value>0 rad</value><x>%s</z>'
              '</noderotation>' % ax)
    m.add('<surfacepressure selection="Vlak"><normal %s>3*y^2</normal>'
          '</surfacepressure>' % _f("Pa"))
    return m


def _ls44_checks(tol_r, tol_mw, known=None):
    return [
        Check("reactie Z", lambda r: r.total("reactionforcez", "Rand"),
              ref=8.0, tol=tol_r, unit="N", source="int 3 y^2 dA = 8 N",
              known=known),
        Check("doorbuiging rand y = 2 m t.o.v. Mecway",
              lambda r: -r.mean("displz", "Tip"), ref=7.51970e-4,
              tol=tol_mw, unit="m", source="Mecway 34 (eigen solver)",
              in_series=False)]


TESTS = [
    Case("LS-40a", GROUP_LS, "Druk als formule 3*y^2 (kPa, x/y/z in m) op "
         "een blok", "lin_static_3d", build_ls40a, _ls40_checks(),
         note="PRES_REP met een FORMULE van Y (AFFE_CHAR_MECA_F)."),
    Case("LS-40b", GROUP_LS, "Idem met positionunit mm (3e-6*y^2)",
         "lin_static_3d", build_ls40b, _ls40_checks()),
    Case("LS-41", GROUP_LS, "Twee drukken en een traction als formule in "
         "één run", "lin_static_3d", build_ls41, [
             Check("reactie Z", lambda r: r.total("reactionforcez",
                                                  "BodemN"),
                   ref=6000.0, tol=1e-6, unit="N",
                   source="int 3 y^2 (y<1) + int 10 x (y>1) = 1 + 5 kN "
                          "(Mecway 34: 6000)"),
             Check("moment om X", lambda r: _moment(r, "x"), ref=8250.0,
                   tol=1e-6, unit="N.m", source="0,75 + 7,5 kN.m "
                   "(Mecway 34: 8250)"),
             Check("reactie X", lambda r: r.total("reactionforcex",
                                                  "BodemN"),
                   ref=-4000.0, tol=1e-6, unit="N",
                   source="-int (2 x + 1) dA = -4 kN"),
         ], note="Drie lasten AFFE_CHAR_MECA_F met elk een eigen FORMULE in "
                 "één EXCIT: elke last rekent met zijn eigen functie (geen "
                 "KNOWN_BUGS 70)."),
    Case("LS-42a", GROUP_LS, "Opgelegde verplaatsing Z = 0,001 x + 0,002 y "
         "mm", "lin_static_3d",
         _ls42_build("<x>0</x><y>0</y><z>1</z>", "0.001*x+0.002*y"), [
             Check("DZ in (1, 2, 0,1)", lambda r: r.at(
                 "displz", (1.0, 2.0, 0.1)), ref=5e-6, tol=1e-9, unit="m",
                 source="formule in de knoop"),
             Check("DZ in (0,5, 0,75, 0,1)", lambda r: r.at(
                 "displz", (0.5, 0.75, 0.1)), ref=2e-6, tol=1e-9, unit="m",
                 source="formule in de knoop")],
         note="DDL_IMPO DZ met een FORMULE (in de knopen). Mecway 34 legt "
              "deze verplaatsing niet op (0)."),
    Case("LS-42b", GROUP_LS, "Opgelegde verplaatsing schuin (1, 1, 0) = "
         "0,001 (1 + x) mm", "lin_static_3d",
         _ls42_build("<x>1</x><y>1</y><z>0</z>", "0.001*(1+x)"), [
             Check("verplaatsing langs (1,1,0) in (1, 2, 0,1)",
                   lambda r: _along(r, (1.0, 2.0, 0.1), (1, 1, 0)),
                   ref=2e-6, tol=1e-9, unit="m", source="formule in de knoop"),
             Check("idem in (0, 0, 0,1)",
                   lambda r: _along(r, (0.0, 0.0, 0.1), (1, 1, 0)),
                   ref=1e-6, tol=1e-9, unit="m", source="formule in de knoop")],
         note="LIAISON_OBLIQUE DX met een FORMULE."),
    Case("LS-42c", GROUP_LS, "Opgelegde rotatie om Y = 0,001 (1 + x) rad aan "
         "de tip van een ingeklemde balk", "lin_static_3d", build_ls42c, [
             Check("rotatie tip", lambda r: r.at("roty", (L3, 0, 0)),
                   ref=2e-3, tol=1e-9, unit="rad",
                   source="formule in de knoop (x = 1 m)"),
             Check("doorbuiging tip", lambda r: -r.at("displz", (L3, 0, 0)),
                   ref=1e-3, tol=1e-6, unit="m",
                   source="zuiver moment: w = theta L / 2")],
         note="DDL_IMPO DRY met een FORMULE. Mecway 34 legt deze rotatie "
              "niet op (0)."),
    Case("LS-43a", GROUP_LS, "Ingeklemde balk, driehoekslast q = 1000 x N/m "
         "(line pressure als formule)", "lin_static_3d", _beam(False),
         _beam_checks(False), note="FORCE_POUTRE FZ met een FORMULE van X. "
         "Mecway 34 legt deze line pressure niet op (0)."),
    Case("LS-43b", GROUP_LS, "Idem met gravity op de balk", "lin_static_3d",
         _beam(True), _beam_checks(True),
         note="Een verdeelde last per balk (CALCULEL2_92): gravity wordt "
              "FORCE_POUTRE rho A g in dezelfde AFFE_CHAR_MECA_F."),
    Case("LS-44a", GROUP_LS, "Plaat (DKT), druk 3*y^2 Pa als formule",
         "lin_static_3d", build_ls44, _ls44_checks(0.01, 0.02),
         note="FORCE_COQUE PRES met een FORMULE (PRES_REP met een functie "
              "geeft op schalen ELEMENTS4_92). DKT neemt de functie in de "
              "knopen: +0,78 % op dit mesh (KNOWN_BUGS 104)."),
    Case("LS-44b", GROUP_LS, "Idem met COQUE_3D", "lin_static_3d",
         build_ls44, _ls44_checks(1e-6, 0.01),
         general={"elem_shell": "COQUE_3D"}),
]


def build_nl40():
    return _block([
        '<surfacepressure selection="Top"><normal %s>3*y^2*t</normal>'
        '</surfacepressure>' % _f("kPa"),
        '<force selection="Top"><x>0 N</x><y>0 N</y><z time="0 s">0 N</z>'
        '<z time="2 s">-2000 N</z></force>'],
        analysis="L30", timesteps={"timeperiod": "2 s", "stepsize": "0.5 s"})


TESTS += [
    Case("NL-40", GROUP_NL, "Druk als formule in y en t naast een "
         "krachttabel", "nonlin_static_3d", build_nl40, [
             Check("reactie Z bij t = 1 s", lambda r: r.total(
                 "reactionforcez", "BodemN", 1.0), ref=9000.0, tol=1e-6,
                 unit="N", source="8 kN x t + 1 kN"),
             Check("reactie Z bij t = 2 s", lambda r: r.total(
                 "reactionforcez", "BodemN", 2.0), ref=18000.0, tol=1e-6,
                 unit="N", source="8 kN x t + 2 kN"),
             Check("moment om X bij t = 2 s", lambda r: _moment(
                 r, "x", time=2.0), ref=26000.0, tol=1e-6, unit="N.m",
                 source="12 kN.m x t + 2 kN x 1 m")],
         note="FORMULE van Y en INST; de krachttabel blijft een "
              "DEFI_FONCTION (FONC_MULT)."),
]
