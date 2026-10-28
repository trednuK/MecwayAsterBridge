# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of the 2D analyses (bridge_plane, STAPPENPLAN S16a; Python
# 2.7 and 3, without Mecway and Code-Aster):
#   - S20 -> C_PLAN (thickness) / D_PLAN (planestrain="1"), SA0 -> AXIS;
#   - D20 -> C_PLAN with dyna_impl_3d (S16b);
#   - ERROR (model_data None) for: S20 without thickness, Z != 0, SA0 with
#     X < 0, a beam in 2D, A20 with a static analysis, D20 with a static
#     analysis, route 'tabel';
#   - A20 (S16d) -> PHENOMENE ACOUSTIQUE, MODELISATION PLAN (+ PLAN_ABSO for
#     an impedance) in the .comm; ERROR for Z != 0, a beam, the harmonic
#     analysis;
#   - finish_bcs: DZ dropped, FORCE_NODALE / thickness or / 2 pi, gravity
#     out of the plane skipped;
#   - _edge_measure: revolved area 2 pi int(r dl) and length x t.
#
#   python tests/test_bridge_plane.py

from __future__ import print_function

import math
import os
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
import bridge_plane  # noqa: E402
import bridge_from_liml as bfl  # noqa: E402
for _mod in (bridge_plane, bfl):
    _mod.log = _log

FAILS = []


def check(cond, text):
    if not cond:
        FAILS.append(text)


STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')


def _liml(atype, geo, x0=0.0, z=0.0, extra_elem="", loads=""):
    """Two quad4 in the XY plane (x0 .. x0+2, 0 .. 1), fixed edge, force."""
    nodes = [(x0, 0), (x0 + 1, 0), (x0 + 2, 0), (x0, 1), (x0 + 1, 1),
             (x0 + 2, 1)]
    lines = ['<liml version="34">', '  <analysis type="%s" />' % atype]
    for i, (x, y) in enumerate(nodes):
        lines.append('  <node nid="%d" x="%r" y="%r" z="%r" />' % (
            i + 1, x, y, z))
    lines += ['  <node nid="7" x="%r" y="0" z="1" />' % x0,
              '  <elset name="P" material="M">',
              '    <elem eid="1" shape="quad4" nodes="1 2 5 4" />',
              '    <elem eid="2" shape="quad4" nodes="2 3 6 5" />',
              extra_elem, '  </elset>',
              '  <fixed selection="Links" />', loads,
              '  <mat name="M">', geo, STEEL, '  </mat>',
              '  <faceselection name="Links"><face eid="1" faceid="4" />'
              '</faceselection>',
              '  <nodeselection name="Tip"><node nid="3" /><node nid="6" />'
              '</nodeselection>', '</liml>']
    return "\n".join(l for l in lines if l)


PS = '<geometric type="Plate" thickness="10 mm" />'
PE = '<geometric type="Plate" thickness="10 mm" planestrain="1" />'


def _extract(text, analysis="lin_static_3d", route="liml"):
    tmp = tempfile.mkdtemp(prefix="mab_s16_unit")
    try:
        path = os.path.join(tmp, "m.liml")
        with open(path, "w") as f:
            f.write(text)
        bridge_utils.CONFIG_BRIDGE["active_analysis"] = analysis
        bridge_utils.CONFIG_BRIDGE["result_route"] = route
        del LOG[:]
        return bfl.extract_aster_data_from_liml(path)
    finally:
        bridge_utils.CONFIG_BRIDGE["result_route"] = "liml"
        shutil.rmtree(tmp, ignore_errors=True)


def _errors():
    return [m for m in LOG if m.startswith("ERROR")]


def test_modelisations():
    md = _extract(_liml("S20", PS))
    check(md is not None and md["elset_modelisations"].get("P") == "C_PLAN",
          "S20 plane stress -> C_PLAN: {0}".format(_errors()))
    check(md and abs(md["plane"]["factor"] - 0.01) < 1e-15,
          "factor = thickness: {0}".format(md and md.get("plane")))
    md = _extract(_liml("S20", PE))
    check(md is not None and md["elset_modelisations"].get("P") == "D_PLAN",
          "S20 planestrain -> D_PLAN")
    md = _extract(_liml("SA0", ""))
    check(md is not None and md["elset_modelisations"].get("P") == "AXIS" and
          abs(md["plane"]["factor"] - 2 * math.pi) < 1e-15,
          "SA0 -> AXIS, factor 2 pi")
    md = _extract(_liml("S30", PS))
    check(md is not None and "plane" not in md and
          md["elset_modelisations"].get("P") == "DKT",
          "S30 unchanged (shells)")


def test_errors():
    for text, what in (
            (_liml("S20", ""), "S20 without thickness"),
            (_liml("S20", PS, z=0.5), "Z != 0"),
            (_liml("SA0", "", x0=-0.5), "SA0 with X < 0"),
            (_liml("S20", PS, extra_elem='    <elem eid="3" shape="line2" '
                   'nodes="1 7" />'), "beam in 2D"),
            (_liml("A20", PS), "A20 with a static analysis"),
            (_liml("D20", PS), "D20 only with dyna_impl_3d")):
        md = _extract(text)
        check(md is None and _errors(), "{0}: ERROR and stop ({1})".format(
            what, LOG[-3:]))
    md = _extract(_liml("S20", PS), route="tabel")
    check(md is None, "route tabel: ERROR")
    md = _extract(_liml("S20", PS), analysis="nonlin_static_3d")
    check(md is None, "S20 with nonlin_static_3d: ERROR")
    md = _extract(_liml("D20", PS), analysis="dyna_impl_3d")
    check(md is not None and md["elset_modelisations"].get("P") == "C_PLAN",
          "D20 with dyna_impl_3d -> C_PLAN: {0}".format(_errors()))


def test_finish_bcs():
    md = {"plane": {"type": "SA0", "modelisation": "AXIS", "thickness": None,
                    "factor": 2 * math.pi},
          "bcs": [
              {"type": "fixed", "aster_keyword": "DDL_IMPO",
               "aster_dict": {"DX": 0.0, "DY": 0.0, "DZ": 0.0},
               "selection": "A"},
              {"type": "force", "aster_keyword": "FORCE_NODALE",
               "aster_dict": {"FX": 0.0, "FY": 2 * math.pi, "FZ": 0.0},
               "selection": "B"},
              {"type": "gravity", "aster_keyword": "PESANTEUR",
               "aster_dict": {"GRAVITE": 9.81, "DIRECTION": (1.0, 0.0, 0.0)},
               "selection": ""},
              {"type": "centrifugal", "aster_keyword": "ROTATION",
               "aster_dict": {"VITESSE": 10.0, "AXE": (0.0, 1.0, 0.0)},
               "selection": ""}]}
    del LOG[:]
    bridge_plane.finish_bcs(md)
    b = md["bcs"]
    check(dict(b[0]["aster_dict"]) == {"DX": 0.0, "DY": 0.0},
          "DZ dropped: {0}".format(b[0]["aster_dict"]))
    check(abs(b[1]["aster_dict"]["FY"] - 1.0) < 1e-12 and
          "FZ" not in b[1]["aster_dict"], "force per radian: {0}".format(
              b[1]["aster_dict"]))
    check(b[2].get("skip"), "AXIS gravity along X skipped")
    check(not b[3].get("skip"), "AXIS rotation about Y kept")


def test_edge_measure():
    # SEG3 from r = 1 to r = 2 at y = 0: 2 pi int r dr = 3 pi
    md = {"mesh_nodes": {1: (1.0, 0.0, 0.0), 2: (2.0, 0.0, 0.0),
                         3: (1.5, 0.0, 0.0)},
          "group_face_list": {"E": [{"nodes": [1, 2, 3]}]}}
    a = bridge_plane._edge_measure(md, "E", True, None)
    check(abs(a - 3 * math.pi) < 1e-12, "revolved area {0}".format(a))
    a = bridge_plane._edge_measure(md, "E", False, 0.01)
    check(abs(a - 0.01) < 1e-15, "length x t {0}".format(a))


AIR = ('<mechanical type="Isotropic" speedofsound="340 m/s" />'
       '<density type="Simple" density="1.2 kg/m&#179;" />')


def _acoustic_liml(z=0.0, extra_elem="", impedance=False):
    """Two quad4 of air (A20), p = 0 on the left edge, optionally an
    impedance on the right edge (face 2 of element 2)."""
    text = _liml("A20", AIR, z=z, extra_elem=extra_elem)
    text = text.replace('<analysis type="A20" />',
                        '<analysis type="A20" maxmode="3" />')
    text = text.replace('  <fixed selection="Links" />',
                        '  <fluidpressure selection="Links"><value>0 Pa'
                        '</value></fluidpressure>' + (
                            '\n  <impedance selection="Rechts">'
                            '<specificimpedancer>2000</specificimpedancer>'
                            '<specificimpedancei>0</specificimpedancei>'
                            '</impedance>' if impedance else ""))
    text = text.replace('</faceselection>', '</faceselection>\n'
                        '  <faceselection name="Rechts"><face eid="2" '
                        'faceid="2" /></faceselection>', 1)
    return text.replace(STEEL, "")


def test_acoustic():
    """A20 (S16d): PHENOMENE ACOUSTIQUE, MODELISATION PLAN; ERROR for Z != 0,
    a beam, the harmonic analysis or a static analysis; the .comm with PLAN
    and PLAN_ABSO."""
    import bridge_acoustic
    check(bridge_utils.resolve_auto_analysis("A20") == "acoustic_modes_3d",
          "auto: A20 -> acoustic_modes_3d")
    md = _extract(_acoustic_liml(), analysis="acoustic_modes_3d")
    check(md is not None and md.get("acoustic_2d") and
          md["elset_modelisations"].get("P") == "PLAN" and "plane" not in md,
          "A20 -> PLAN, acoustic_2d, no plane factor: {0}".format(_errors()))
    check(md and bridge_acoustic._modelisations(md) == ("PLAN", "PLAN_ABSO"),
          "acoustic modelisations of A20")
    check(bridge_acoustic._modelisations({}) == ("3D", "3D_ABSO"),
          "acoustic modelisations of A30 unchanged")
    check(bridge_acoustic.resolve_auto("acoustic_modes_3d", {
        "analysis_type": "A20",
        "acoustic_data": {"aster_sources": [("S", 1.0, 0.0)]}}) ==
        "acoustic_modes_3d", "A20 with a source stays acoustic_modes_3d")
    for text, analysis, what in (
            (_acoustic_liml(z=0.5), "acoustic_modes_3d", "A20 with Z != 0"),
            (_acoustic_liml(extra_elem='    <elem eid="3" shape="line2" '
                            'nodes="1 7" />'), "acoustic_modes_3d",
             "A20 with a beam"),
            (_acoustic_liml(), "acoustic_harm_3d", "A20 harmonic"),
            (_acoustic_liml(), "lin_static_3d", "A20 static")):
        md = _extract(text, analysis=analysis)
        check(md is None and _errors(), "{0}: ERROR and stop ({1})".format(
            what, LOG[-3:]))
    # .comm: AFFE_MODELE with PLAN (and PLAN_ABSO for the impedance edge)
    import bridge_mesh
    import bridge_to_aster
    for mod in (bridge_mesh, bridge_to_aster, bridge_acoustic):
        mod.log = _log
    for impedance in (False, True):
        tmp = tempfile.mkdtemp(prefix="mab_s16d_unit")
        work = bridge_utils.CONFIG_BRIDGE["work_dir"]
        try:
            bridge_utils.CONFIG_BRIDGE["work_dir"] = tmp
            path = os.path.join(tmp, "m.liml")
            with open(path, "w") as f:
                f.write(_acoustic_liml(impedance=impedance))
            bridge_utils.CONFIG_BRIDGE["active_analysis"] = \
                "acoustic_modes_3d"
            del LOG[:]
            md = bfl.extract_aster_data_from_liml(path)
            mail = os.path.join(tmp, "m.mail")
            ok = md is not None and bridge_mesh.write_mesh(mail, md)
            ok = ok and bridge_to_aster.generate_AsterSolver_files(
                tmp, md, mail, "test.resu")
            comm = ""
            if ok:
                with open(os.path.join(tmp, "study.comm")) as f:
                    comm = f.read()
            check("MODELISATION='PLAN'" in comm and
                  "PHENOMENE='ACOUSTIQUE'" in comm,
                  "A20 .comm with PLAN (impedance {0}): {1}".format(
                      impedance, _errors()))
            check(("MODELISATION='PLAN_ABSO'" in comm) == impedance,
                  "PLAN_ABSO only with an impedance ({0})".format(impedance))
        finally:
            bridge_utils.CONFIG_BRIDGE["work_dir"] = work
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_modelisations()
    test_errors()
    test_finish_bcs()
    test_edge_measure()
    test_acoustic()
    for f in FAILS:
        print("FAIL:", f)
    print("{0} failure(s)".format(len(FAILS)))
    sys.exit(1 if FAILS else 0)
