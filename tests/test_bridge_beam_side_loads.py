# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of loads on the side face of beams (S17, KNOWN_BUGS 5;
# CPython 3, without Mecway and Code-Aster): the perimeter per section type
# (bridge_from_liml._section_perimeter, values measured in Mecway 34),
# traction on beam side faces -> FORCE_POUTRE = traction x perimeter on a
# BRSF group (constant, formula, two sections, line3, together with a beam
# end), pressure on beam side faces -> no load with a WARNING. The results
# of a run: TestFiles/Verificatie LS-92a .. LS-92h.
#
#   python tests/test_bridge_beam_side_loads.py

from __future__ import print_function

import math
import os
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
_REPO = os.path.join(_HERE, "..")
sys.path.insert(0, os.path.join(_REPO, "Scripts"))
sys.path.insert(0, os.path.join(_REPO, "TestFiles", "Verificatie"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"

LOG = []


def _log(msg):
    LOG.append(msg)


import bridge_from_liml as bfl  # noqa: E402
import bridge_mesh  # noqa: E402
import bridge_to_aster  # noqa: E402
for _mod in (bridge_utils, bfl, bridge_mesh, bridge_to_aster):
    _mod.log = _log
from verif_lib import Model  # noqa: E402

FAILS = []


def check(cond, text):
    if not cond:
        FAILS.append(text)


def close(a, b, rel=1e-9):
    return abs(a - b) <= rel * max(abs(a), abs(b), 1e-30)


# --- perimeter per section type (Mecway 34 headless, S17) ---
for xml, ref in (
        ('<geometric type="RectBar" recta="20 mm" rectb="10 mm" />', 0.06),
        ('<geometric type="CircularBar" roundod="20 mm" />', math.pi * 0.02),
        ('<geometric type="UniformCircularTube" roundod="20 mm" '
         'roundid="10 mm" />', math.pi * 0.03),
        ('<geometric type="RectTube" recta="20 mm" rectb="10 mm" '
         'rectthickness="2 mm" />', 0.104),
        ('<geometric type="I" ia="100 mm" ib="50 mm" ic="5 mm" id="4 mm" />',
         0.392),
        ('<geometric type="T" ta="100 mm" tb="4 mm" tc="5 mm" td="50 mm" />',
         0.310),
        ('<geometric type="L" la="50 mm" lb="80 mm" lc="5 mm" />', 0.260),
        ('<geometric type="C" ca="50 mm" cb="100 mm" cc="5 mm" cd="4 mm" />',
         0.392),
        ('<geometric type="UniformGeneralSection" area="100 mm²" '
         'iyy="1000 mm⁴" izz="2000 mm⁴" torsionconstant="500 mm⁴" '
         'perimeter="77 mm" />', 0.077)):
    g = bfl._parse_geometric_props(ET.fromstring(xml))
    check(g is not None and close(g.get("perimeter", -1.0), ref),
          "perimeter {0}: {1}".format(xml[:45], g and g.get("perimeter")))
g = bfl._parse_geometric_props(ET.fromstring(
    '<geometric type="Plate" thickness="10 mm" />'))
check("perimeter" not in g, "shell has no perimeter")

STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')
RECT = '<geometric type="RectBar" recta="20 mm" rectb="10 mm" />'
CIRC = '<geometric type="CircularBar" roundod="20 mm" />'
FORM = 'unit="kPa" timeunit="s" positionunit="m"'


def build(load, line3=False, second=False, end_too=False):
    """Cantilever along X (10 elements), side faces of all elements in
    selection F; second: the last 5 elements in an elset with a circular
    section."""
    m = Model("S30")
    m.elset("B1", "R")
    if second:
        m.elset("B2", "C")
    nids = [m.node(i / 10.0, 0, 0) for i in range(11)]
    eids = []
    for i in range(10):
        es = "B2" if second and i >= 5 else "B1"
        if line3:
            mid = m.node((i + 0.5) / 10.0, 0, 0)
            eids.append(m.elem(es, "line3", [nids[i], mid, nids[i + 1]]))
        else:
            eids.append(m.elem(es, "line2", [nids[i], nids[i + 1]]))
    m.mat("R", RECT, STEEL)
    if second:
        m.mat("C", CIRC, STEEL)
    m.node_selection("Fix", [nids[0]])
    m.add('<fixed selection="Fix" />')
    faces = [(e, 1) for e in eids]
    if end_too:
        faces.append((eids[-1], 3))
    m.face_selection("F", faces)
    m.add(load)
    return m


def translate(m, name):
    d = tempfile.mkdtemp(prefix="mab_s17_ut_")
    try:
        bridge_utils.CONFIG_BRIDGE["work_dir"] = d
        bridge_utils.CONFIG_BRIDGE["active_analysis"] = "lin_static_3d"
        path = m.write(os.path.join(d, "model.liml"))
        del LOG[:]
        md = bfl.extract_aster_data_from_liml(path)
        ok = bridge_mesh.write_mesh(os.path.join(d, "model_mesh.mail"), md)
        check(ok, name + ": write_mesh")
        ok = bridge_to_aster.generate_AsterSolver_files(
            d, md, os.path.join(d, "model_mesh.mail"), "test.resu")
        check(ok, name + ": generate_AsterSolver_files")
        comm = open(os.path.join(d, "study.comm")).read() if ok else ""
        return md, comm
    finally:
        shutil.rmtree(d, ignore_errors=True)


def side_bcs(md):
    return [b for b in md["bcs"] if b.get("_beam_side")]


# --- constant traction: FZ = 1 kPa x 0.06 m ---
md, comm = translate(build('<traction selection="F"><x>0 Pa</x><y>0 Pa</y>'
                           '<z>1 kPa</z></traction>'), "constant")
sb = side_bcs(md)
check(len(sb) == 1 and close(sb[0]["aster_dict"]["FZ"], 60.0),
      "constant: synthetic BC {0}".format(sb))
check(re.search(r"FORCE_POUTRE=_F\(GROUP_MA='BRSF1', FZ=60\.0\)", comm),
      "constant: FORCE_POUTRE in study.comm")
check(re.search(r"_F\(NOM='BRSF1', MAILLE=", comm), "constant: DEFI_GROUP")
orig = [b for b in md["bcs"] if b["type"] == "traction"]
check(not orig, "constant: original BC dropped (skip)")
check(not md.get("skipped_loads"), "constant: no skipped loads {0}".format(
    md.get("skipped_loads")))

# --- formula in x: FORMULE scaled by the perimeter ---
md, comm = translate(build(
    '<traction selection="F"><x>0 Pa</x><y>0 Pa</y><z %s>x</z></traction>'
    % FORM), "formula")
check(re.search(r"FORCE_POUTRE=_F\(GROUP_MA='BRSF1', FZ=FPOS1\)", comm),
      "formula: FORCE_POUTRE with FORMULE")
m_ = re.search(r"FPOS1 = FORMULE\(\s*VALE='([^']*)'", comm)
check(m_ and "0.05999999" in m_.group(1) and "1000.0" in m_.group(1),
      "formula: FORMULE {0}".format(m_ and m_.group(1)))

# --- two sections: one group per perimeter, added up per beam ---
md, comm = translate(build('<traction selection="F"><x>0 Pa</x>'
                           '<y>2 kPa</y><z>0 Pa</z></traction>',
                           second=True), "two sections")
sb = side_bcs(md)
fy = sorted(round(b["aster_dict"]["FY"], 9) for b in sb)
check(fy == sorted([120.0, round(2000.0 * math.pi * 0.02, 9)]),
      "two sections: FY {0}".format(fy))
check(len(md.get("extra_ma_groups", {}).get("BRSF1", ())) == 5 and
      len(md.get("extra_ma_groups", {}).get("BRSF2", ())) == 5,
      "two sections: groups {0}".format(md.get("extra_ma_groups")))

# --- line3: both halves of a split element in the group ---
md, comm = translate(build('<traction selection="F"><x>0 Pa</x><y>0 Pa</y>'
                           '<z>1 kPa</z></traction>', line3=True), "line3")
m_ = re.search(r"_F\(NOM='BRSF1', MAILLE=\(([^)]*)\)", comm)
check(m_ and len(re.findall(r"'M\d+'", m_.group(1))) == 20,
      "line3: 20 cells in BRSF1 ({0})".format(m_ and m_.group(1)))

# --- side faces together with a beam end: FORCE_POUTRE + nodal force ---
md, comm = translate(build('<traction selection="F"><x>0 Pa</x><y>0 Pa</y>'
                           '<z>1 kPa</z></traction>', end_too=True),
                     "side + end")
orig = [b for b in md["bcs"] if b["type"] == "traction"][0]
check(not orig.get("skip") and orig.get("node_loads"),
      "side + end: beam end as nodal force")
check(len(side_bcs(md)) == 1, "side + end: one synthetic BC")

# --- pressure: zero resultant, no load, WARNING ---
md, comm = translate(build('<surfacepressure selection="F"><normal>1 MPa'
                           '</normal></surfacepressure>'), "pressure")
check(not side_bcs(md), "pressure: no synthetic BC")
check(not [b for b in md["bcs"] if b["type"] == "surfacepressure"],
      "pressure: BC dropped (skip)")
check(any("WARNING: Pressure on the side face" in l for l in LOG),
      "pressure: WARNING")
check(not md.get("skipped_loads"), "pressure: not a skipped load")
check("FORCE_POUTRE" not in comm and "PRES_REP=" not in comm,
      "pressure: no load in study.comm")

if FAILS:
    print("FAILED ({0}):".format(len(FAILS)))
    for f in FAILS:
        print("  " + f)
    sys.exit(1)
print("OK: beam side loads")
