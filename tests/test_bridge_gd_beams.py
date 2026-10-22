# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of elem_beam = POU_D_T_GD (beams with large rotations,
# STAPPENPLAN S20; Python 2.7 and 3, without Mecway and Code-Aster): the
# generated .comm for nonlinear static (MODELISATION, RELATION
# ELAS_POUTRE_GR, DEFORMATION GROT_GDEP, section forces from SIEF_ELNO/
# SIEF_NOEU, no SIPM_ELNO/EFGE_ELNO, AY/AZ for a general section, line3
# split, centrifugal force as FORMULE instead of ROTATION, route 'tabel'),
# the fallback to POU_D_T in other analyses and with PETIT, the ERRORs for
# crit_stab and imperfection_amplitude and the WARNINGs (beam offset,
# imposed rotation). POU_D_E stays as it was. The results of a run:
# TestFiles/Verificatie (NL-80 ... NL-88). Route from the fork by MishalTPC
# (github.com/mishal0488/MecwayAsterBridge, commit dd4c958).
#
#   python tests/test_bridge_gd_beams.py

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
import bridge_to_aster  # noqa: E402
import bridge_offset  # noqa: E402
import bridge_failure  # noqa: E402
for _mod in (bridge_from_liml, bridge_mesh, bridge_to_aster, bridge_offset,
             bridge_failure):
    _mod.log = _log

FAILS = []
_CONFIG = copy.deepcopy(bridge_utils.CONFIG_BRIDGE)


def check(cond, text):
    if not cond:
        FAILS.append(text)


RECT = u'<geometric type="RectBar" recta="10 mm" rectb="20 mm" />'
IPROF = (u'<geometric type="I" ia="100 mm" ib="50 mm" ic="10 mm" '
         u'id="8 mm" />')


def _liml(analysis="L30", section=RECT, shape="line2", extra=u""):
    """Cantilever along X, 4 elements (line3: 2), root fixed, tip force."""
    out = [u'<liml version="33">', u'  <analysis type="%s" />' % analysis]
    for i in range(5):
        out.append(u'  <node nid="%d" x="%g" y="0" z="0" />' % (i + 1,
                                                               0.25 * i))
    out.append(u'  <elset name="Balk" material="Staal">')
    if shape == "line2":
        for i in range(4):
            out.append(u'    <elem eid="%d" shape="line2" nodes="%d %d" />'
                       % (i + 1, i + 1, i + 2))
        eids = range(1, 5)
    else:
        out.append(u'    <elem eid="1" shape="line3" nodes="1 2 3" />')
        out.append(u'    <elem eid="2" shape="line3" nodes="3 4 5" />')
        eids = range(1, 3)
    out.append(u'  </elset>')
    out.append(u'  <fixed selection="Root" />')
    out.append(u'  <force selection="Tip"><x>0 N</x><y time="0 s">0 N</y>'
               u'<y time="1 s">100 N</y><z>0 N</z></force>')
    out.append(extra)
    out.append(u'  <mat name="Staal">\n    %s\n'
               u'    <mechanical type="Isotropic" youngsmodulus="210000 MPa" '
               u'poissonratio="0.3" />\n'
               u'    <density type="Simple" density="7850 kg/m³" />\n'
               u'  </mat>' % section)
    out.append(u'  <nodeselection name="Root"><node nid="1" />'
               u'</nodeselection>')
    out.append(u'  <nodeselection name="Tip"><node nid="5" />'
               u'</nodeselection>')
    out.append(u'  <elementselection name="Alle">%s</elementselection>'
               % u"".join(u'<element eid="%d" />' % e for e in eids))
    out.append(u'</liml>')
    return u"\n".join(out) + u"\n"


def _translate(analysis_key, liml_text, general=None, settings=None):
    """(comm text or None, model_data, log text) of one translation."""
    bridge_utils.CONFIG_BRIDGE.clear()
    bridge_utils.CONFIG_BRIDGE.update(copy.deepcopy(_CONFIG))
    cfg = bridge_utils.CONFIG_BRIDGE
    cfg["language"] = "en"
    cfg["elem_beam"] = "POU_D_T_GD"
    cfg.update(general or {})
    cfg["active_analysis"] = analysis_key
    cfg["analyses"][analysis_key].update(settings or {})
    del LOG[:]
    tmp = tempfile.mkdtemp(prefix="gdtest")
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
                exp = bridge_to_aster.generate_AsterSolver_files(
                    tmp, md, mail, "test.resu")
                cpath = os.path.join(tmp, bridge_utils.run_name(".comm"))
                if exp and os.path.isfile(cpath):
                    with io.open(cpath, encoding="utf-8") as f:
                        comm = f.read()
                if os.path.isfile(mail):
                    with io.open(mail, encoding="utf-8",
                                 errors="replace") as f:
                        md["_mail_text"] = f.read()
        return comm, md, u"\n".join(u"%s" % l for l in LOG)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_nonlinear_static():
    comm, md, log = _translate("nonlin_static_3d", _liml())
    check(comm is not None, "GD: no .comm\n" + log)
    if comm is None:
        return
    check("MODELISATION='POU_D_T_GD'" in comm, "GD: MODELISATION")
    check("RELATION='ELAS_POUTRE_GR', DEFORMATION='GROT_GDEP'" in comm,
          "GD: RELATION/DEFORMATION")
    check("CONTRAINTE=('SIEF_ELNO', 'SIEF_NOEU', )" in comm,
          "GD: beam_forces from SIEF_ELNO/SIEF_NOEU")
    check("SIPM_ELNO" not in comm, "GD: no SIPM_ELNO")
    check("EFGE_ELNO" not in comm, "GD: no EFGE_ELNO (DVP_1)")
    check("VECT_Y" in comm, "GD: explicit VECT_Y")
    check("POU_D_T_GD (large rotations" not in log,
          "GD: no fallback in nonlinear static")
    check("are computed with large rotations (POU_D_T_GD" in log,
          "GD: WARNING with the limits")
    check("stay geometrically linear" not in log,
          "GD: no KNOWN_BUGS-11 warning for GD beams")
    check(md["elset_modelisations"].get("Balk") == "POU_D_T_GD",
          "GD: model_data modelisation")
    check(md.get("has_rot_dofs", True), "GD: rotation DOFs")
    # The generated file must at least be valid Python (CPython 3 and
    # IronPython 2.7 both parse the .comm syntax used here).
    try:
        compile(comm, "study.comm", "exec")
    except SyntaxError as e:
        check(False, "GD: .comm does not compile: %s" % e)


def test_general_section_shear():
    comm, _md, log = _translate("nonlin_static_3d", _liml(section=IPROF))
    check(comm is not None, "GD I profile: no .comm\n" + log)
    if comm:
        check(re.search(r"CARA=\([^)]*'AY', 'AZ'", comm) is not None,
              "GD I profile: AY/AZ for SECTION='GENERALE'")
        check("(I, POU_D_T_GD): AY=" in log, "GD I profile: INFO AY/AZ")


def test_line3_split():
    comm, md, log = _translate("nonlin_static_3d", _liml(shape="line3"))
    check(comm is not None, "GD line3: no .comm\n" + log)
    mail = md.get("_mail_text", "") if md else ""
    check(re.search(r"^\s*M1 ", mail, re.M) and
          re.search(r"^\s*H1 ", mail, re.M),
          "GD line3: split into SEG2 cells M1/H1")
    check("are not translated" not in log and "NOT translated" not in log,
          "GD line3: nothing left out")


def test_fallback_other_analyses():
    for key, analysis in (("lin_static_3d", "S30"), ("modal_3d", "F30"),
                          ("dyna_impl_3d", "D31")):
        comm, md, log = _translate(key, _liml(analysis))
        check(md is not None and
              md["elset_modelisations"].get("Balk") == "POU_D_T",
              "fallback %s: POU_D_T" % key)
        check("elem_beam = POU_D_T_GD (large rotations) only works" in log,
              "fallback %s: WARNING" % key)
        if comm:
            check("POU_D_T_GD" not in comm, "fallback %s: no GD" % key)
    comm, md, log = _translate("nonlin_static_3d", _liml(),
                               settings={"deformation": "PETIT"})
    check(md is not None and
          md["elset_modelisations"].get("Balk") == "POU_D_T",
          "fallback PETIT: POU_D_T")
    check("STAT_NON_LINE, deformation PETIT" in log,
          "fallback PETIT: WARNING names the deformation")


def test_errors():
    comm, _md, log = _translate("nonlin_static_3d", _liml(),
                                settings={"crit_stab": True})
    check(comm is None and "ALGELINE4_41" in log,
          "crit_stab with GD: ERROR\n" + log)
    comm, _md, log = _translate("nonlin_static_3d", _liml(),
                                settings={"imperfection_amplitude": 0.001})
    check(comm is None and "RIGI_MECA" in log,
          "imperfection with GD: ERROR\n" + log)


# A plastic hex8 block beside the beam (nodes 6..13): element failure
HEX = (u'  <node nid="6" x="0" y="1" z="0" />\n'
       u'  <node nid="7" x="0.1" y="1" z="0" />\n'
       u'  <node nid="8" x="0.1" y="1.1" z="0" />\n'
       u'  <node nid="9" x="0" y="1.1" z="0" />\n'
       u'  <node nid="10" x="0" y="1" z="0.1" />\n'
       u'  <node nid="11" x="0.1" y="1" z="0.1" />\n'
       u'  <node nid="12" x="0.1" y="1.1" z="0.1" />\n'
       u'  <node nid="13" x="0" y="1.1" z="0.1" />\n'
       u'  <elset name="Blok" material="Kerf">\n'
       u'    <elem eid="10" shape="hex8" nodes="6 7 8 9 10 11 12 13" />\n'
       u'  </elset>\n'
       u'  <mat name="Kerf">\n'
       u'    <mechanical type="Isotropic" youngsmodulus="210000 MPa" '
       u'poissonratio="0.3" />\n'
       u'    <plastic type="BilinearIsotropic" yieldstrength="250 MPa" '
       u'tangentmodulus="500 MPa" />\n'
       u'  </mat>\n'
       u'  <nodeselection name="BlokVast"><node nid="6" /><node nid="9" />'
       u'<node nid="10" /><node nid="13" /></nodeselection>\n'
       u'  <fixed selection="BlokVast" />')


def test_element_failure():
    # After the first failure the loop restarts with PREDICTION='ELASTIQUE'
    # (RIGI_MECA, CALCUL_37 with POU_D_T_GD; TANGENTE/EXTRAPOLE did not
    # converge, Code-Aster 17.4 runs): ERROR beforehand.
    fail = {"deformation": "GDEF_LOG", "failure_plastic_strain": 0.05}
    comm, _md, log = _translate("nonlin_static_3d", _liml(extra=HEX),
                                settings=fail)
    check(comm is None and "Element failure (Blok) does not work" in log,
          "GD + element failure: ERROR\n" + log)
    comm, _md, log = _translate("nonlin_static_3d", _liml(extra=HEX),
                                settings=dict(fail, element_failure=False))
    check(comm is not None and "does not work in a model" not in log,
          "GD + element failure off: runs\n" + log)
    comm, _md, log = _translate("nonlin_static_3d", _liml(extra=HEX),
                                settings={"deformation": "GDEF_LOG"})
    check(comm is not None and "does not work in a model" not in log,
          "GD + plastic block without a failure limit: runs\n" + log)
    comm, _md, log = _translate("nonlin_static_3d", _liml(extra=HEX),
                                settings=fail,
                                general={"elem_beam": "POU_D_T"})
    check(comm is not None and "_bz_pred = 'ELASTIQUE'" in comm,
          "POU_D_T + element failure: failure loop\n" + log)


def test_centrifugal_formula():
    extra = (u'  <centrifugal><x>0 r/min</x><y>0 r/min</y><z>300 r/min</z>'
             u'</centrifugal>')
    comm, _md, log = _translate("nonlin_static_3d", _liml(extra=extra))
    check(comm is not None, "GD centrifugal: no .comm\n" + log)
    if comm:
        check("ROTATION=" not in comm, "GD centrifugal: no ROTATION "
              "(CHAR_MECA_ROTA_R)")
        check("FCEN" in comm and "FORCE_POUTRE" in comm,
              "GD centrifugal: FORCE_POUTRE as FORMULE")
    # A truss (BARRE) in the FORMULE route gets FORCE_POUTRE as well
    # (verification NL-86b) instead of an ERROR "not translated".
    truss = (u'  <node nid="6" x="0" y="0.5" z="0" />\n'
             u'  <node nid="7" x="1" y="0.5" z="0" />\n'
             u'  <elset name="Staaf" material="Staal">\n'
             u'    <elem eid="20" shape="line2" nodes="6 7" '
             u'truss="true" />\n'
             u'  </elset>\n')
    comm, md, log = _translate("nonlin_static_3d",
                               _liml(extra=extra + u"\n" + truss))
    check(comm is not None, "GD centrifugal + truss: no .comm\n" + log)
    if comm:
        check(md["elset_modelisations"].get("Staaf") == "BARRE",
              "GD centrifugal + truss: BARRE")
        check(re.search(r"FORCE_POUTRE=_F\(GROUP_MA='Staaf', FX=FCEN", comm)
              is not None, "GD centrifugal + truss: FORCE_POUTRE on BARRE")
        check("not translated" not in log,
              "GD centrifugal + truss: no ERROR\n" + log)


def test_route_tabel():
    comm, _md, log = _translate("nonlin_static_3d", _liml(),
                                general={"result_route": "tabel"})
    check(comm is not None, "GD tabel: no .comm\n" + log)
    if comm:
        check(re.search(r"NOM_CHAM='SIEF_NOEU'", comm) is not None,
              "GD tabel: beam_forces table from SIEF_NOEU")


def test_warnings_links_and_rotation():
    extra = (u'  <offset selection="Alle"><x>0 m</x><y>0.01 m</y><z>0 m</z>'
             u'</offset>')
    comm, _md, log = _translate("nonlin_static_3d", _liml(extra=extra))
    check(comm is not None, "GD offset: no .comm\n" + log)
    check("rigid arms of an element offset" in log,
          "GD offset: WARNING linear arms")
    extra = (u'  <noderotation selection="Tip"><value time="0 s">0 rad'
             u'</value><value time="1 s">1 rad</value><x>0</x><y>0</y>'
             u'<z>1</z></noderotation>')
    comm, _md, log = _translate("nonlin_static_3d", _liml(extra=extra))
    check("is the total rotation vector" in log,
          "GD imposed rotation: WARNING")


def _joint(free, offset=False):
    """Flexible joint on the start of element 3 (node 3), free axes free;
    offset: element offset y = 10 mm on elements 3 and 4."""
    extra = (u'  <faceselection name="J"><face eid="3" faceid="2" />'
             u'</faceselection>\n'
             u'  <flexiblejoint selection="J">%s</flexiblejoint>'
             % u"".join(u"<rot%s />" % a for a in free))
    if offset:
        extra += (u'\n  <elementselection name="Rechts"><element eid="3" />'
                  u'<element eid="4" /></elementselection>\n'
                  u'  <offset selection="Rechts"><x>0 m</x><y>0.01 m</y>'
                  u'<z>0 m</z></offset>')
    return _liml(extra=extra)


def test_joints():
    # Selective joint on POU_D_T_GD: ERROR before the run (KNOWN_BUGS 106b)
    for free in ("w", "uv", "vw"):
        comm, _md, log = _translate("nonlin_static_3d", _joint(free))
        check(comm is None and "only some rotations free on POU_D_T_GD"
              in log, "GD selective joint %s: ERROR\n%s" % (free, log))
    # All rotations free: only DX/DY/DZ tied, exact; no linear-link WARNING
    comm, md, log = _translate("nonlin_static_3d", _joint("uvw"))
    check(comm is not None, "GD joint UVW: no .comm\n" + log)
    check("only some rotations free" not in log,
          "GD joint UVW: no ERROR/WARNING for selective joints\n" + log)
    check("POU_D_T_GD beams (large rotations), but" not in log,
          "GD joint UVW: no linear-relation WARNING\n" + log)
    # Small rotations stay as they were
    comm, _md, log = _translate("nonlin_static_3d", _joint("w"),
                                general={"elem_beam": "POU_D_T"})
    check(comm is not None, "POU_D_T selective joint: .comm\n" + log)
    comm, _md, log = _translate("lin_static_3d", _joint("w"))
    check(comm is not None, "lin static selective joint: .comm\n" + log)


def test_joint_on_offset():
    # KNOWN_BUGS 108d: Mecway node -> rigid arm -> joint -> element (as
    # Mecway 34, LS-52c): the own node lies at the offset node O and
    # replaces O in the cell; the joint ties it to O
    comm, md, log = _translate("lin_static_3d", _joint("w", offset=True),
                               general={"elem_beam": "POU_D_T"})
    check(comm is not None, "joint on offset: no .comm\n" + log)
    check("at the end of the rigid arm" in log,
          "joint on offset: joint at the end of the arm\n" + log)
    check("the joint is not translated" not in log,
          "joint on offset: no longer refused\n" + log)
    if md:
        info = list((md.get("joint_free") or {}).values())
        check(len(info) == 1 and info[0]["offset"],
              "joint on offset: joint_free entry")
        mail = md.get("_mail_text", u"")
        dup = list(md["joint_free"])[0] if info else 0
        at_o = re.findall(r"(?m)^ N(\d+) 0\.5 0\.01 0\.0$", mail)
        check(str(dup) in at_o and len(at_o) == 2,
              "joint on offset: own node at the offset node")
        o_node = int([n for n in at_o if n != str(dup)][0]) \
            if len(at_o) == 2 else 0
        check(re.search(r"(?m)^ M3 N%d " % dup, mail) is not None,
              "joint on offset: element 3 starts at the own node")
        check(re.search(r"(?m)^ J%d N%d$" % (o_node, o_node), mail)
              is not None and re.search(r"(?m)^ J%d " % dup, mail) is None,
              "joint on offset: POI1 on O (in no cell), not on the own node")
        rel = [e for e in md.get("constraint_equations", [])
               if e["source"] == "flexiblejoint" and
               any(t[0] == dup for t in e["terms"])]
        check(len(rel) == 5 and all(
            set(t[0] for t in e["terms"]) == set([dup, o_node])
            for e in rel), "joint on offset: 5 joint relations to O")
        check(re.search(r"(?m)^ BROFL\d+\n N3 N%d$" % dup, mail)
              is not None, "joint on offset: BROFL group N3 + own node")
    # Joint with U, V and W free on an offset element at the beam end
    # (only that element at node 3 on the right side): solvable
    comm, md, log = _translate("lin_static_3d", _joint("uvw", offset=True),
                               general={"elem_beam": "POU_D_T"})
    check(comm is not None, "joint UVW on offset: .comm\n" + log)
    # Modal: translated as well; nonlinear static: as before (WARNING,
    # element rigid to the arm)
    comm, md, log = _translate("modal_3d", _joint("w", offset=True),
                               general={"elem_beam": "POU_D_T"})
    check(comm is not None and "at the end of the rigid arm" in log,
          "joint on offset, modal: translated\n" + log)
    comm, md, log = _translate("nonlin_static_3d", _joint("w", offset=True),
                               general={"elem_beam": "POU_D_T"})
    check(comm is not None and "the joint is not translated" in log and
          not (md or {}).get("joint_free"),
          "joint on offset, nonlinear: not translated (WARNING)\n" + log)


def test_pou_d_e_unchanged():
    comm, md, log = _translate("nonlin_static_3d", _liml(),
                               general={"elem_beam": "POU_D_E"})
    check(comm is not None, "POU_D_E: no .comm\n" + log)
    if comm:
        check("MODELISATION='POU_D_E'" in comm, "POU_D_E: MODELISATION")
        check("RELATION='ELAS', DEFORMATION='PETIT'" in comm,
              "POU_D_E: stays PETIT")
        check("CONTRAINTE=('EFGE_ELNO', 'EFGE_NOEU', )" in comm,
              "POU_D_E: EFGE_ELNO/EFGE_NOEU")
        check("SIEF_ELNO" not in comm, "POU_D_E: no SIEF_ELNO")
        check("SIPM_ELNO" in comm, "POU_D_E: SIPM_ELNO (RECTANGLE)")
        check("stay geometrically linear" in log,
              "POU_D_E: KNOWN_BUGS-11 warning")


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
    print("OK: test_bridge_gd_beams")
    return 0


if __name__ == "__main__":
    sys.exit(main())
