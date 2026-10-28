# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of elem_beam = POU_D_TG (beams with warping, STAPPENPLAN S19;
# Python 2.7 and 3, without Mecway and Code-Aster): the section properties
# of bridge_warping.section_props against closed forms and Code-Aster test
# case ssll103a, the generated .comm (MODELISATION, EY/EZ/JG/IYR2/IZR2,
# DDL_IMPO GRX), the warping rule at supports (beam_warping auto/free/
# blocked: Fixed support, fork support, Node rotation across the beam),
# the #ASTER-SECTIE route and POU_D_E unchanged. The results of a run:
# TestFiles/Verificatie (BU-38 ... BU-42, LS-90, LS-91).
#
#   python tests/test_bridge_warping.py

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
import bridge_warping  # noqa: E402
for _mod in (bridge_from_liml, bridge_mesh, bridge_to_aster, bridge_warping):
    _mod.log = _log

FAILS = []
_CONFIG = copy.deepcopy(bridge_utils.CONFIG_BRIDGE)


def check(cond, text):
    if not cond:
        FAILS.append(text)


def close(a, b, rel):
    return abs(a - b) <= rel * max(abs(b), 1e-300)


IPROF = (u'<geometric type="I" ia="100 mm" ib="50 mm" ic="10 mm" '
         u'id="8 mm" />')
CPROF = u'<geometric type="C" ca="50 mm" cb="100 mm" cc="6 mm" cd="6 mm" />'
RECT = u'<geometric type="RectBar" recta="10 mm" rectb="20 mm" />'
UGS = (u'<geometric type="UniformGeneralSection" area="1856 mm²" '
       u'iyy="4167339 mm⁴" izz="1045547 mm⁴" torsionconstant="39595 mm⁴" />')


def test_section_props():
    # I 100/50/10/8 mm: S in the centroid, primary C_w = t_f b^3 h^2/24
    # (+ thickness warping, about 1 %)
    p = bridge_warping.section_props("I", 0.1, 0.05, 0.01, 0.008)
    cw = 0.01 * 0.05 ** 3 * 0.09 ** 2 / 24.0
    check(p["EY"] == 0.0 and p["EZ"] == 0.0, "I: shear centre %r" % p)
    check(cw < p["JG"] < 1.02 * cw, "I: JG %r vs %r" % (p["JG"], cw))
    check(p["IYR2"] == 0.0 and p["IZR2"] == 0.0, "I: Wagner terms %r" % p)
    # C 100 x 50 x 6: shear centre on the axis of symmetry (z = W), 29.33 mm
    # from the centroid (centre line e + x_c = 29.375); primary C_w closed
    # form t b^3 h^2/12 (3b + 2h)/(6b + h) with b = 47, h = 94 mm
    p = bridge_warping.section_props("C", 0.05, 0.1, 0.006, 0.006)
    b, h, t = 0.047, 0.094, 0.006
    cw = t * b ** 3 * h ** 2 / 12.0 * (3 * b + 2 * h) / (6 * b + h)
    check(p["EY"] == 0.0 and close(p["EZ"], 0.029375, 0.005),
          "C: shear centre %r" % p)
    check(cw < p["JG"] < 1.02 * cw, "C: JG %r vs %r" % (p["JG"], cw))
    # L 120 x 120 x 8: Code-Aster test case ssll103a (EY 41.012 mm, JG
    # 44398819 mm^6, IYR2 84948392 mm^5 in its axes, y along the axis of
    # symmetry); here z is that axis (Mecway's V is the minor axis)
    p = bridge_warping.section_props("L", 0.12, 0.12, 0.008, 0.0)
    check(close(p["EZ"], 0.041012, 0.002) and abs(p["EY"]) < 1e-9,
          "L: shear centre %r" % p)
    check(close(p["JG"], 4.4398819e-11, 1e-6), "L: JG %r" % p["JG"])
    check(close(p["IZR2"], 8.4948392e-8, 0.002) and p["IYR2"] == 0.0,
          "L: Wagner %r" % p)
    # T: shear centre at the flange/web junction, on V above the centroid:
    # EY = (centroid - S) < 0
    p = bridge_warping.section_props("T", 0.1, 0.01, 0.01, 0.09)
    check(p["EY"] < 0.0 and close(-p["EY"], 0.0236842, 1e-4) and
          p["EZ"] == 0.0, "T: shear centre %r" % p)
    check(bridge_warping.section_props("X", 1, 1, 1, 1) is None,
          "unknown kind -> None")


def _liml(analysis="S30", section=IPROF, bcs=u"", extra=u"", n=4,
          axis=(1.0, 0.0, 0.0)):
    """Beam along axis, n elements of 0.25 m; Root = node 1, Tip = last."""
    out = [u'<liml version="33">', u'  <analysis type="%s" />' % analysis]
    for i in range(n + 1):
        out.append(u'  <node nid="%d" x="%g" y="%g" z="%g" />' % (
            (i + 1,) + tuple(0.25 * i * a for a in axis)))
    out.append(u'  <elset name="Balk" material="Staal">')
    for i in range(n):
        out.append(u'    <elem eid="%d" shape="line2" nodes="%d %d" />'
                   % (i + 1, i + 1, i + 2))
    out.append(u'  </elset>')
    out.append(bcs or u'  <fixed selection="Root" />')
    out.append(u'  <force selection="Tip"><x>0 N</x><y>0 N</y><z>-100 N</z>'
               u'</force>')
    out.append(extra)
    out.append(u'  <mat name="Staal">\n    %s\n'
               u'    <mechanical type="Isotropic" youngsmodulus="210000 MPa" '
               u'poissonratio="0.3" />\n'
               u'    <density type="Simple" density="7850 kg/m³" />\n'
               u'  </mat>' % section)
    out.append(u'  <nodeselection name="Root"><node nid="1" />'
               u'</nodeselection>')
    out.append(u'  <nodeselection name="Tip"><node nid="%d" />'
               u'</nodeselection>' % (n + 1))
    out.append(u'</liml>')
    return u"\n".join(out) + u"\n"


FORK = (u'  <pinnedsupport selection="Root" />\n'
        u'  <noderotation selection="Root"><value>0 rad</value><x>1</x>'
        u'<y>0</y><z>0</z></noderotation>\n'
        u'  <displacement selection="Tip"><value>0 mm</value><x>0</x>'
        u'<y>1</y><z>0</z></displacement>\n'
        u'  <noderotation selection="Tip"><value>0 rad</value><x>1</x>'
        u'<y>0</y><z>0</z></noderotation>')


def _translate(analysis_key, liml_text, general=None):
    """(comm text or None, model_data, log text, mesh text)."""
    bridge_utils.CONFIG_BRIDGE.clear()
    bridge_utils.CONFIG_BRIDGE.update(copy.deepcopy(_CONFIG))
    cfg = bridge_utils.CONFIG_BRIDGE
    cfg["language"] = "en"
    cfg["elem_beam"] = "POU_D_TG"
    cfg.update(general or {})
    cfg["active_analysis"] = analysis_key
    del LOG[:]
    tmp = tempfile.mkdtemp(prefix="tgtest")
    mail_text = u""
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
                with io.open(mail, encoding="utf-8", errors="replace") as f:
                    mail_text = f.read()
                exp = bridge_to_aster.generate_AsterSolver_files(
                    tmp, md, mail, "test.resu")
                cpath = os.path.join(tmp, bridge_utils.run_name(".comm"))
                if exp and os.path.isfile(cpath):
                    with io.open(cpath, encoding="utf-8") as f:
                        comm = f.read()
        return comm, md, u"\n".join(u"%s" % l for l in LOG), mail_text
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _grx_nodes(mail):
    m = re.search(r"GROUP_NO\s+BRGRX\s+(.*?)\s+FINSF", mail, re.S)
    return set(m.group(1).split()) if m else set()


def test_comm_clamp():
    comm, md, log, mail = _translate("lin_static_3d", _liml())
    check(comm is not None, "TG clamp: no .comm\n" + log)
    if comm is None:
        return
    check("MODELISATION='POU_D_TG'" in comm, "TG: MODELISATION")
    check(re.search(r"CARA=\([^)]*'AY', 'AZ', 'EY', 'EZ', 'JG', 'IYR2', "
                    r"'IZR2'", comm) is not None, "TG: EY/EZ/JG/IYR2/IZR2")
    check("_F(GROUP_NO='BRGRX', GRX=0.0)" in comm, "TG: DDL_IMPO GRX")
    check(_grx_nodes(mail) == set(["N1"]), "TG clamp: GRX = 0 at N1 only %r"
          % _grx_nodes(mail))
    check(md.get("has_rot_dofs"), "TG: rotation DOFs")
    check("(I, POU_D_TG): EY=" in log, "TG: INFO with the section values")
    try:
        compile(comm, "study.comm", "exec")
    except SyntaxError as e:
        check(False, "TG: .comm does not compile: %s" % e)


def test_warping_rule():
    # fork supports (translations + rotation about the beam axis): free
    comm, _md, log, mail = _translate("lin_static_3d", _liml(bcs=FORK))
    check(comm is not None and not _grx_nodes(mail) and
          "BRGRX" not in (comm or ""), "fork: warping free\n" + log)
    check("free at 2 supported node(s)" in log, "fork: INFO free nodes")
    # beam_warping = blocked: GRX = 0 at both fork nodes
    comm, _md, log, mail = _translate("lin_static_3d", _liml(bcs=FORK),
                                      {"beam_warping": "blocked"})
    check(_grx_nodes(mail) == set(["N1", "N5"]),
          "blocked: GRX at N1, N5 %r" % _grx_nodes(mail))
    # beam_warping = free: no GRX even at the Fixed support
    comm, _md, log, mail = _translate("lin_static_3d", _liml(),
                                      {"beam_warping": "free"})
    check(comm is not None and "GRX" not in comm, "free: no GRX")
    # Node rotation about Y (across a beam along X) at the root: blocked
    bcs = (u'  <pinnedsupport selection="Root" />\n'
           u'  <noderotation selection="Root"><value>0 rad</value><x>0</x>'
           u'<y>1</y><z>0</z></noderotation>\n'
           u'  <noderotation selection="Root"><value>0 rad</value><x>1</x>'
           u'<y>0</y><z>0</z></noderotation>')
    comm, _md, log, mail = _translate("lin_static_3d", _liml(bcs=bcs))
    check(_grx_nodes(mail) == set(["N1"]), "bending rotation: GRX at N1")
    # the same fork on a beam along Z (rotation about Z = twist): free
    bcs_z = FORK.replace(u"<x>1</x><y>0</y><z>0</z></noderotation>",
                         u"<x>0</x><y>0</y><z>1</z></noderotation>").replace(
        u"<x>0</x><y>1</y><z>0</z></displacement>",
        u"<x>1</x><y>0</y><z>0</z></displacement>")
    comm, _md, log, mail = _translate("lin_static_3d",
                                      _liml(bcs=bcs_z, axis=(0, 0, 1)))
    check(comm is not None and not _grx_nodes(mail),
          "fork along Z: warping free\n" + log)
    # unknown value -> auto with a WARNING
    comm, _md, log, mail = _translate("lin_static_3d", _liml(),
                                      {"beam_warping": "maybe"})
    check(_grx_nodes(mail) == set(["N1"]) and "is unknown" in log,
          "unknown beam_warping -> auto")


def test_general_section():
    # without #ASTER-SECTIE: JG = 0 with a WARNING
    comm, _md, log, _mail = _translate("lin_static_3d", _liml(section=UGS))
    check(comm is not None, "UGS: no .comm\n" + log)
    check("no warping constant and no shear centre known" in log,
          "UGS: WARNING without #ASTER-SECTIE")
    check(comm is None or "'JG'" not in comm, "UGS: no JG")
    # with #ASTER-SECTIE: JG, EY, IYR2 of the line
    line = (u"  <ccxmodeldefinition>#ASTER-SECTIE Staal: A=1.856e-3, "
            u"IY=4.167339e-6, IZ=1.045547e-6, JX=3.9595e-8, AY=1, AZ=1, "
            u"EY=0.041012, EZ=0, JG=4.4398819e-11, IYR2=8.4948392e-8, "
            u"IZR2=0</ccxmodeldefinition>")
    comm, _md, log, _mail = _translate("lin_static_3d",
                                       _liml(section=UGS, extra=line))
    check(comm is not None and "'JG', 'IYR2', 'IZR2'" in comm and
          "4.4398819e-11" in comm, "UGS + #ASTER-SECTIE: JG/IYR2\n" + log)
    check("#ASTER-SECTIE (MecwaySectionProps)" in log,
          "UGS + #ASTER-SECTIE: INFO source")
    # POU_D_E with #ASTER-SECTIE: no JG (only POU_D_TG uses it)
    comm, _md, log, _mail = _translate("lin_static_3d",
                                       _liml(section=UGS, extra=line),
                                       {"elem_beam": "POU_D_E"})
    check(comm is not None and "'JG'" not in comm and "GRX" not in comm,
          "POU_D_E: no JG/GRX")


def test_rect_and_buckling():
    comm, _md, log, _mail = _translate("buckling_3d",
                                       _liml("B30", section=RECT))
    check(comm is not None and "SECTION='RECTANGLE'" in comm and
          "MODELISATION='POU_D_TG'" in comm, "RECTANGLE with POU_D_TG")
    check("JG = 0" in log, "RECTANGLE: INFO JG = 0")
    comm, _md, log, _mail = _translate("buckling_3d",
                                       _liml("B30", section=CPROF))
    check("Buckling with T, C or L profiles" not in log,
          "C with POU_D_TG: no KNOWN_BUGS-115 WARNING")
    check("with warping (POU_D_TG)" in log, "C with POU_D_TG: INFO")
    comm, _md, log, _mail = _translate("buckling_3d",
                                       _liml("B30", section=CPROF),
                                       {"elem_beam": "POU_D_E"})
    check("Choose elem_beam = POU_D_TG" in log,
          "C with POU_D_E: WARNING names POU_D_TG")


def test_explicit_fallback():
    comm, md, log, _mail = _translate("dyna_expl_3d", _liml("D32"))
    check(md is not None and
          md["elset_modelisations"].get("Balk") == "POU_D_T",
          "explicit: POU_D_T")
    check("does not work in explicit dynamics" in log, "explicit: WARNING")
    check(comm is None or "GRX" not in comm, "explicit: no GRX")


def test_reactions_warning():
    comm, _md, log, _mail = _translate("lin_static_3d", _liml())
    fields = bridge_utils.CONFIG_BRIDGE["analyses"]["lin_static_3d"].get(
        "fields") or []
    if "reactions" in fields:
        check("KNOWN_BUGS 123" in log, "TG: reactions WARNING")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    if FAILS:
        print("FAILED ({0}):".format(len(FAILS)))
        for f in FAILS:
            print(" - " + f)
        sys.exit(1)
    print("OK: test_bridge_warping")
