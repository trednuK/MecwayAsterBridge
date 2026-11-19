# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of shells in DYNA_NON_LINE (Python 2.7 and 3, without Mecway
# and Code-Aster):
# - KNOWN_BUGS 156: DKT in implicit dynamics gets a zero initial
#   acceleration (ETAT_INIT ACCE) and an extra small first solver step,
#   decided by one predicate (_zero_initial_acceleration) for both; the
#   initial velocity field stays byte-identical without it; explicit and
#   models without DKT unchanged; the failure loop passes ETAT_INIT only to
#   its first call;
# - COQUE_3D is PETIT in DYNA_NON_LINE (ELEMENTS3_91), without follower
#   pressure there; no small step when an imposed displacement jumps at
#   t = 0.
# The results of runs: TestFiles/Verificatie (LS-07b/a/f dynamic).
#
#   python tests/test_bridge_shell_dynamics.py

from __future__ import print_function

import copy
import io
import os
import re
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"

LOG = []


def _log(msg):
    LOG.append(msg)


bridge_utils.log = _log
import bridge_from_liml  # noqa: E402
import bridge_mesh  # noqa: E402
import bridge_to_aster as bta  # noqa: E402
import bridge_failure  # noqa: E402
for _mod in (bridge_from_liml, bridge_mesh, bta, bridge_failure):
    _mod.log = _log

FAILS = []
_CONFIG = copy.deepcopy(bridge_utils.CONFIG_BRIDGE)


def check(cond, text):
    if not cond:
        FAILS.append(text)


L, B = 0.2, 0.02
STEEL = (u'    <mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         u'poissonratio="0.3" />\n'
         u'    <density type="Simple" density="7850 kg/m³" />\n')
PLASTIC = (u'    <plastic type="BilinearIsotropic" yieldstrength="355 MPa" '
           u'tangentmodulus="1000 MPa" />\n')
TS = (u'  <timesteps timeperiod="0.002 s" automatictimestepping="false" '
      u'outputtimes="regular" timepointsstart="0 s" '
      u'timepointsincrement="0.0005 s" />')


def _strip(order=1, analysis="D31", solid=False, extra=u"", plastic=False,
           timesteps=TS, load=True):
    """Cantilever strip L x B in the XY plane (4 x 2 quad4, order 2:
    quad8), clamped at x = 0, 1 N -Z on the tip edge; solid: also a
    separate hex8 bar (own nodes) with its own clamp."""
    nodes, index = [], {}

    def node(x, y, z=0.0):
        key = (round(x * 1e9), round(y * 1e9), round(z * 1e9))
        if key not in index:
            nodes.append((x, y, z))
            index[key] = len(nodes)
        return index[key]

    nx, ny = 4, 2
    elems, clamp_faces, tip_faces = [], [], []
    for i in range(nx):
        for j in range(ny):
            x0, x1 = L * i / nx, L * (i + 1) / nx
            y0, y1 = B * j / ny, B * (j + 1) / ny
            c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            if order == 1:
                ids = [node(*p) for p in c]
            else:
                ids = []
                for k in range(4):
                    a, b = c[k], c[(k + 1) % 4]
                    ids += [node(*a), node(0.5 * (a[0] + b[0]),
                                           0.5 * (a[1] + b[1]))]
            elems.append(ids)
            eid = len(elems)
            # shell edge faces: 1 = edge n1-n2 (y = y0), 2 = n2-n3 (x1),
            # 3 = n3-n4 (y1), 4 = n4-n1 (x0); bridge_mesh._SHELL_EDGES
            if i == 0:
                clamp_faces.append((eid, 4))
            if i == nx - 1:
                tip_faces.append((eid, 2))
    shape = "quad4" if order == 1 else "quad8"
    out = [u'<liml version="33">', u'  <analysis type="%s" />' % analysis]
    if timesteps and analysis.startswith("D"):
        out.append(timesteps)
    hexes = []
    if solid:
        for i in range(nx):
            x0, x1 = L * i / nx, L * (i + 1) / nx
            y0, y1, z0, z1 = 0.05, 0.07, -0.001, 0.001
            hexes.append([node(x0, y0, z0), node(x1, y0, z0),
                          node(x1, y1, z0), node(x0, y1, z0),
                          node(x0, y0, z1), node(x1, y0, z1),
                          node(x1, y1, z1), node(x0, y1, z1)])
    for k, (x, y, z) in enumerate(nodes):
        out.append(u'  <node nid="%d" x="%r" y="%r" z="%r" />' % (k + 1, x, y,
                                                                  z))
    out.append(u'  <elset name="Plaat" material="Plaat2">')
    for k, ids in enumerate(elems):
        out.append(u'    <elem eid="%d" shape="%s" nodes="%s" />' % (
            k + 1, shape, u" ".join(u"%d" % n for n in ids)))
    out.append(u'  </elset>')
    if solid:
        out.append(u'  <elset name="Blok" material="Vol">')
        for k, ids in enumerate(hexes):
            out.append(u'    <elem eid="%d" shape="hex8" nodes="%s" />' % (
                len(elems) + k + 1, u" ".join(u"%d" % n for n in ids)))
        out.append(u'  </elset>')
    out.append(u'  <fixed selection="Klem" />')
    if solid:
        out.append(u'  <fixed selection="KlemBlok" />')
    if load:
        out.append(u'  <force selection="Eind"><x>0 N</x><y>0 N</y>'
                   u'<z>-1 N</z></force>')
    out.append(extra)
    out.append(u'  <mat name="Plaat2">\n    <geometric type="Plate" '
               u'thickness="2 mm" />\n' + STEEL +
               (PLASTIC if plastic else u"") + u'  </mat>')
    if solid:
        out.append(u'  <mat name="Vol">\n' + STEEL + u'  </mat>')
    out.append(u'  <faceselection name="Klem">%s</faceselection>' % u"".join(
        u'<face eid="%d" faceid="%d" />' % f for f in clamp_faces))
    out.append(u'  <faceselection name="Eind">%s</faceselection>' % u"".join(
        u'<face eid="%d" faceid="%d" />' % f for f in tip_faces))
    out.append(u'  <faceselection name="Vlak">%s</faceselection>' % u"".join(
        u'<face eid="%d" faceid="5" />' % (k + 1) for k in range(len(elems))))
    out.append(u'  <elementselection name="Alles">%s</elementselection>'
               % u"".join(u'<element eid="%d" />' % (k + 1)
                          for k in range(len(elems))))
    if solid:
        # hex8 face 6 = x0 side (bridge_mesh._FACE_CORNERS)
        out.append(u'  <faceselection name="KlemBlok"><face eid="%d" '
                   u'faceid="6" /></faceselection>' % (len(elems) + 1))
    out.append(u'</liml>')
    return u"\n".join(out) + u"\n"


def _translate(analysis_key, liml_text, general=None, settings=None):
    """(comm text or None, model_data, log text) of one translation."""
    bridge_utils.CONFIG_BRIDGE.clear()
    bridge_utils.CONFIG_BRIDGE.update(copy.deepcopy(_CONFIG))
    cfg = bridge_utils.CONFIG_BRIDGE
    cfg["language"] = "en"
    cfg.update(general or {})
    cfg["active_analysis"] = analysis_key
    cfg["analyses"][analysis_key].update(settings or {})
    del LOG[:]
    bta._COQUE3D_DYNA_WARNED.clear()
    tmp = tempfile.mkdtemp(prefix="shdyn")
    try:
        cfg["work_dir"] = tmp
        path = os.path.join(tmp, "model.liml")
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(liml_text)
        md = bridge_from_liml.extract_aster_data_from_liml(path)
        comm = None
        if md is not None:
            mail = os.path.join(tmp, "model_mesh.mail")
            if bridge_mesh.write_mesh(mail, md):
                exp = bridge_to_aster_generate(tmp, md, mail)
                cpath = os.path.join(tmp, bridge_utils.run_name(".comm"))
                if exp and os.path.isfile(cpath):
                    with io.open(cpath, encoding="utf-8") as f:
                        comm = f.read()
        return comm, md, u"\n".join(u"%s" % l for l in LOG)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def bridge_to_aster_generate(tmp, md, mail):
    return bta.generate_AsterSolver_files(tmp, md, mail, "test.resu")


def _times_block(comm):
    m = re.search(r"times = DEFI_LIST_REEL\((.*?)\n\)\n", comm, re.S)
    return m.group(1) if m else ""


def _intervals(comm):
    """[(JUSQU_A, NOMBRE)] of the implicit time list (floats: IronPython
    writes repr with 17 digits)."""
    return [(float(t), int(n)) for t, n in re.findall(
        r"_F\(JUSQU_A=([^,]+), NOMBRE=(\d+)\)", _times_block(comm))]


def _same(a, b):
    return abs(a - b) <= 1e-12 * max(abs(a), abs(b))


def _old_etat_init_block(model_data):
    """_build_etat_init_block of the bridge before the zero initial
    acceleration (byte identity of the velocity-only case)."""
    vels = model_data.get("initial_velocities", [])
    if not vels:
        return "", ""
    affe = ["_F(TOUT='OUI', NOM_CMP=('DX', 'DY', 'DZ'), "
            "VALE=(0.0, 0.0, 0.0))"]
    for sel, target, v in vels:
        affe.append("_F({0}='{1}', NOM_CMP=('DX', 'DY', 'DZ'), "
                    "VALE=({2!r}, {3!r}, {4!r}))".format(
                        target, sel, v[0], v[1], v[2]))
    block = (
        "vite0 = CREA_CHAMP(\n"
        "    TYPE_CHAM='NOEU_DEPL_R',\n"
        "    OPERATION='AFFE',\n"
        "    MODELE=model,\n"
        "    AFFE=(\n        {0},\n    ),\n"
        ")\n"
    ).format(",\n        ".join(affe))
    return block, "    ETAT_INIT=_F(VITE=vite0),\n"


# ------------------------------------------------------------------
# predicate and helpers
# ------------------------------------------------------------------
def test_predicate():
    hht = {"solver_command": "DYNA_NON_LINE", "schema": "HHT"}
    new = {"solver_command": "DYNA_NON_LINE", "schema": "NEWMARK"}
    dif = {"solver_command": "DYNA_NON_LINE", "schema": "DIFF_CENT"}
    tch = {"solver_command": "DYNA_NON_LINE", "schema": "TCHAMWA"}
    stat = {"solver_command": "STAT_NON_LINE"}
    dkt = {"elset_modelisations": {"P": "DKT", "S": "3D"}}
    c3d = {"elset_modelisations": {"P": "COQUE_3D", "S": "3D"}}
    dst = {"elset_modelisations": {"P": "DST"}}
    f = bta._zero_initial_acceleration
    check(f(dkt, hht) and f(dkt, new), "predicate: DKT implicit")
    check(f(dkt, {"solver_command": "DYNA_NON_LINE"}),
          "predicate: default schema HHT")
    check(not f(dkt, dif) and not f(dkt, tch), "predicate: explicit no")
    check(not f(dkt, stat), "predicate: static no")
    check(not f(c3d, hht), "predicate: COQUE_3D no")
    check(not f(dst, hht), "predicate: DST no (never in DYNA_NON_LINE)")
    check(not f({}, hht), "predicate: empty model no")


def test_rotation_groups_match_from_liml():
    want = set(bridge_from_liml._ROT_DOF_MODELISATIONS) - set(["COQUE_AXIS"])
    check(set(bta._ROT_DOF_3D_MODELISATIONS) == want,
          "rotation DOF modelisations differ from bridge_from_liml: %r" % (
              sorted(set(bta._ROT_DOF_3D_MODELISATIONS) ^ want)))
    md = {"elset_modelisations": {"P": "DKT", "S": "3D", "B": "POU_D_E",
                                  "V": "DIS_T"},
          "poi1_groups": {"M1": "DIS_TR", "M2": "DIS_T"},
          "discretes": {"D1": {"mod": "DIS_TR"}, "D2": {"mod": "DIS_T"}}}
    check(bta._rotation_dof_groups(md) == ["B", "D1", "M1", "P"],
          "rotation groups: %r" % bta._rotation_dof_groups(md))


def test_first_step():
    f = bta._zero_acce_first_step
    iv, tiny = f([(0.0005, 1), (0.001, 1)], 0.002)
    check(iv == [(5e-06, 1), (0.0005, 1), (0.001, 1)] and tiny == 5e-06,
          "first step NOMBRE 1: %r" % iv)
    iv, tiny = f([(0.0006, 3), (0.0012, 3)], 0.0012)
    check(iv == [(2e-06, 1), (0.0002, 1), (0.0006, 2), (0.0012, 3)],
          "first step NOMBRE 3: %r" % iv)
    check(sum(n for _t, n in iv) == 7, "first step: one solver step more")
    # lower bound 1e-8 t_end (above the 1e-9 t_end of _merge_times)
    iv, tiny = f([(1e-6, 1)], 1.0)
    check(tiny == 1e-8, "first step lower bound: %r" % tiny)
    # upper bound dt1 / 2
    iv, tiny = f([(1e-9, 1)], 1.0)
    check(tiny == 5e-10, "first step upper bound: %r" % tiny)


VITE_TODAY = (
    "vite0 = CREA_CHAMP(\n"
    "    TYPE_CHAM='NOEU_DEPL_R',\n"
    "    OPERATION='AFFE',\n"
    "    MODELE=model,\n"
    "    AFFE=(\n"
    "        _F(TOUT='OUI', NOM_CMP=('DX', 'DY', 'DZ'), VALE=(0.0, 0.0, 0.0)),\n"
    "        _F(GROUP_MA='Alles', NOM_CMP=('DX', 'DY', 'DZ'), "
    "VALE=(0.0, 0.0, -0.1)),\n"
    "    ),\n"
    ")\n")


def test_etat_init_block():
    vel = [("Alles", "GROUP_MA", (0.0, 0.0, -0.1))]
    hht = {"solver_command": "DYNA_NON_LINE", "schema": "HHT"}
    dif = {"solver_command": "DYNA_NON_LINE", "schema": "DIFF_CENT"}
    solid = {"elset_modelisations": {"S": "3D"}, "initial_velocities": vel}
    blk, ref = bta._build_etat_init_block(solid, hht)
    check((blk, ref) == _old_etat_init_block(solid),
          "ETAT_INIT: VITE only must stay byte-identical:\n" + blk)
    if repr(0.1) == "0.1":     # CPython; IronPython writes 17 digits
        check(blk == VITE_TODAY and
              ref == "    ETAT_INIT=_F(VITE=vite0),\n",
              "ETAT_INIT: VITE only, text of the bridge before:\n" + blk)
    blk2, ref2 = bta._build_etat_init_block(solid)
    check((blk2, ref2) == (blk, ref), "ETAT_INIT: analysis optional")
    dkt_vel = {"elset_modelisations": {"P": "DKT", "S": "3D"},
               "initial_velocities": vel}
    blk, ref = bta._build_etat_init_block(dkt_vel, dif)
    check((blk, ref) == _old_etat_init_block(dkt_vel),
          "ETAT_INIT: explicit DKT unchanged")
    dkt = {"elset_modelisations": {"P": "DKT", "S": "3D", "B": "POU_D_E"}}
    blk, ref = bta._build_etat_init_block(dkt, hht)
    check(ref == "    ETAT_INIT=_F(ACCE=acce0),\n", "ETAT_INIT: ACCE ref")
    check("vite0" not in blk and "acce0 = CREA_CHAMP(" in blk,
          "ETAT_INIT: ACCE only")
    rot = ("_F(GROUP_MA=('B', 'P',), NOM_CMP=('DRX', 'DRY', 'DRZ'), "
           "VALE=(0.0, 0.0, 0.0))")
    check(rot in blk and "_F(TOUT='OUI', NOM_CMP=('DX', 'DY', 'DZ'), "
          "VALE=(0.0, 0.0, 0.0))" in blk, "ETAT_INIT: ACCE components")
    blk, ref = bta._build_etat_init_block(dkt_vel, hht)
    check(ref == "    ETAT_INIT=_F(VITE=vite0, ACCE=acce0),\n",
          "ETAT_INIT: both ref")
    check(blk.count(rot.replace("'B', 'P',", "'P',")) == 2,
          "ETAT_INIT: rotations in VITE and ACCE when ACCE is written")
    check(bta._build_etat_init_block({"elset_modelisations": {"P": "DKT"}},
                                     dif) == ("", ""),
          "ETAT_INIT: explicit DKT without velocity: none")


def test_deformation_for_solver():
    f = bta._deformation_for
    check(f("COQUE_3D", "ELAS", "GROT_GDEP", "P") == "GROT_GDEP",
          "COQUE_3D without solver")
    check(f("COQUE_3D", "ELAS", "GROT_GDEP", "P", "STAT_NON_LINE") ==
          "GROT_GDEP", "COQUE_3D STAT_NON_LINE")
    del LOG[:]
    check(f("COQUE_3D", "ELAS", "GROT_GDEP", "Pd", "DYNA_NON_LINE") ==
          "PETIT", "COQUE_3D DYNA_NON_LINE -> PETIT")
    check(any("ELEMENTS3_91" in l for l in LOG), "COQUE_3D dyna WARNING")
    del LOG[:]
    f("COQUE_3D", "ELAS", "GROT_GDEP", "Pd", "DYNA_NON_LINE")
    check(not LOG, "COQUE_3D dyna WARNING once per run and elset")
    check(f("COQUE_3D", "ELAS", "PETIT", "P", "DYNA_NON_LINE") == "PETIT",
          "COQUE_3D PETIT stays")
    check(f("DKT", "ELAS", "GROT_GDEP", "P", "DYNA_NON_LINE") ==
          "GREEN_LAGRANGE", "DKT unchanged in dynamics")
    check(f("3D", "ELAS", "GROT_GDEP", "S", "DYNA_NON_LINE") ==
          "GREEN_LAGRANGE", "3D unchanged in dynamics")
    g = bta._solver_deformation_for({"solver_command": "DYNA_NON_LINE"})
    check(g("COQUE_3D", "ELAS", "GROT_GDEP", "Pd") == "PETIT",
          "failure_plan deformation_for with the solver")


# ------------------------------------------------------------------
# generated .comm
# ------------------------------------------------------------------
def test_dkt_dynamics_comm():
    comm, md, log = _translate("dyna_impl_3d", _strip())
    check(comm is not None, "DKT dyna: no .comm\n" + log)
    if comm is None:
        return
    check("MODELISATION='DKT'" in comm, "DKT dyna: DKT")
    check("acce0 = CREA_CHAMP(" in comm and
          "ETAT_INIT=_F(ACCE=acce0)," in comm, "DKT dyna: ETAT_INIT ACCE")
    iv = _intervals(comm)
    check(len(iv) == 5 and _same(iv[0][0], 5e-06) and iv[0][1] == 1 and
          _same(iv[1][0], 0.0005) and iv[1][1] == 1,
          "DKT dyna: small first step %r" % iv)
    m = re.search(r"outlist = DEFI_LIST_REEL\(\n    VALE=\(([^,]+),", comm)
    check("ARCHIVAGE=_F(LIST_INST=outlist)" in comm and m is not None and
          _same(float(m.group(1)), 0.0005),
          "DKT dyna: outlist without the small step")
    check("zero initial acceleration" in log, "DKT dyna: INFO line")
    # NEWMARK the same
    comm, md, log = _translate("dyna_impl_3d", _strip(),
                               settings={"schema": "NEWMARK"})
    check(comm is not None and "ETAT_INIT=_F(ACCE=acce0)," in comm and
          _same(_intervals(comm)[0][0], 5e-06),
          "DKT NEWMARK: ACCE and small step")


def test_mecway_step_size():
    ts = u'  <timesteps timeperiod="0.002 s" stepsize="0.0002 s" />'
    comm, md, log = _translate("dyna_impl_3d", _strip(timesteps=ts))
    check(comm is not None, "step size: no .comm\n" + log)
    if comm is None:
        return
    first = _intervals(comm)
    check(_same(first[0][0], 2e-06) and first[0][1] == 1 and
          _same(first[1][0], 0.0002) and first[1][1] == 1,
          "step size: small step then the rest of the first step: %r"
          % first[:4])
    n_steps = sum(n for _t, n in first)
    m = re.search(r"Implicit dynamics: solver step = .*?; (\d+) steps", log)
    check(m and int(m.group(1)) == n_steps,
          "step size: INFO step count includes the small step (%s, %d)" % (
              m and m.group(1), n_steps))


def test_without_dkt_unchanged():
    # quadratic shells (COQUE_3D): no ACCE, no small step
    comm, md, log = _translate("dyna_impl_3d", _strip(order=2))
    check(comm is not None, "quad8 dyna: no .comm\n" + log)
    if comm is None:
        return
    check("MODELISATION='COQUE_3D'" in comm, "quad8 dyna: COQUE_3D")
    check("ETAT_INIT" not in comm.split("DYNA_NON_LINE(")[1].split(
        "ARCHIVAGE")[0] and "acce0" not in comm,
          "quad8 dyna: no ETAT_INIT")
    check(min(t for t, _n in _intervals(comm)) > 1e-4,
          "quad8 dyna: no small step")
    check("RELATION='ELAS', DEFORMATION='PETIT'" in comm,
          "quad8 dyna: COQUE_3D PETIT (ELEMENTS3_91)")
    check("ELEMENTS3_91" in log, "quad8 dyna: WARNING")
    # explicit DKT: unchanged (MASS_DIAG, no ACCE)
    comm, md, log = _translate("dyna_expl_3d", _strip())
    check(comm is not None and "acce0" not in comm and
          "MASS_DIAG='OUI'" in comm, "explicit DKT: no ACCE")


def test_quad8_static_unchanged():
    comm, md, log = _translate("nonlin_static_3d", _strip(order=2,
                                                         analysis="L30"))
    check(comm is not None and "DEFORMATION='GROT_GDEP'" in comm,
          "quad8 static: COQUE_3D stays GROT_GDEP\n" + (log or ""))
    check("ELEMENTS3_91" not in log, "quad8 static: no WARNING")


def test_follower_pressure_dynamics():
    press = (u'  <surfacepressure selection="Vlak"><normal>1000 Pa</normal>'
             u'</surfacepressure>')
    liml = _strip(order=2, extra=press, load=False)
    comm, md, log = _translate("dyna_impl_3d", liml)
    check(comm is not None, "pressure dyna: no .comm\n" + log)
    if comm is None:
        return
    check("TYPE_CHARGE='SUIV'" not in comm, "pressure dyna: no SUIV")
    check("stays a fixed load in dynamics" in log,
          "pressure dyna: WARNING\n" + log)
    comm, md, log = _translate("nonlin_static_3d",
                               _strip(order=2, extra=press, load=False,
                                      analysis="L30"))
    check(comm is not None and "TYPE_CHARGE='SUIV'" in comm,
          "pressure static: SUIV stays")


def test_velocity_and_mixed():
    vel = (u'  <initialconditions><velocity selection="Alles"><value>0.1 m/s'
           u'</value><x>0</x><y>0</y><z>-1</z></velocity>'
           u'</initialconditions>')
    comm, md, log = _translate("dyna_impl_3d", _strip(solid=True, extra=vel))
    check(comm is not None, "mixed: no .comm\n" + log)
    if comm is None:
        return
    check("ETAT_INIT=_F(VITE=vite0, ACCE=acce0)," in comm,
          "mixed: VITE and ACCE")
    plate = [g for g, m in md["elset_modelisations"].items() if m == "DKT"]
    check(comm.count("_F(GROUP_MA=('%s',), NOM_CMP=('DRX', 'DRY', 'DRZ')"
                     % plate[0]) == 2, "mixed: rotations on the DKT group")


def test_failure_loop_first_call():
    disp = (u'  <displacement selection="Eind"><value time="0 s">0 mm'
            u'</value><value time="0.002 s">6 mm</value><x>1</x><y>0</y>'
            u'<z>0</z></displacement>')
    comm, md, log = _translate("dyna_impl_3d",
                               _strip(extra=disp, plastic=True, load=False),
                               settings={"failure_plastic_strain": 0.02,
                                         "deformation": "PETIT"})
    check(comm is not None, "failure: no .comm\n" + log)
    if comm is None:
        return
    check("_bz_extra = dict(ETAT_INIT=_F(ACCE=acce0))" in comm,
          "failure: ETAT_INIT in the first call")
    check(comm.count("ACCE=acce0") == 1, "failure: ACCE only once")


def test_imposed_jump_no_small_step():
    disp = (u'  <displacement selection="Eind"><value>-1 mm</value><x>0</x>'
            u'<y>0</y><z>1</z></displacement>')
    ramp = (u'  <displacement selection="Eind"><value time="0 s">0 mm</value>'
            u'<value time="0.002 s">-1 mm</value><x>0</x><y>0</y><z>1</z>'
            u'</displacement>')
    for name, extra, small in (("constant", disp, False),
                               ("ramp from 0", ramp, True)):
        comm, md, log = _translate("dyna_impl_3d", _strip(extra=extra,
                                                          load=False))
        check(comm is not None, "jump %s: no .comm " % name + log)
        if comm is None:
            continue
        check("ETAT_INIT=_F(ACCE=acce0)," in comm,
              "jump %s: zero initial acceleration" % name)
        has_small = min(t for t, _n in _intervals(comm)) < 1e-4
        check(has_small == small, "jump %s: small step %s, want %s" % (
            name, has_small, small))
        check(("no extra small first step" in log) == (not small),
              "jump %s: INFO line" % name)


def main():
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    bridge_utils.CONFIG_BRIDGE.clear()
    bridge_utils.CONFIG_BRIDGE.update(_CONFIG)
    if FAILS:
        print("FAILED (%d):" % len(FAILS))
        for f in FAILS:
            print("  - " + f)
        return 1
    print("OK: test_bridge_shell_dynamics")
    return 0


if __name__ == "__main__":
    sys.exit(main())
