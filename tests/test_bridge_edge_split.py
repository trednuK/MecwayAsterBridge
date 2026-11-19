# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of a force on a shell-edge selection over several components
# (bridge_mesh._split_shell_edges, former KNOWN_BUGS 161; Python 2.7 and 3,
# without Mecway and Code-Aster): one BRED group per component when the
# element, LINE_QUAD or thickness differs, the force shared by length x
# thickness (one _F per part in FORCE_ARETE), an edge shared by two
# components in one part only, no split (and no BRED group) when everything
# is equal. Runs: TestFiles/Verificatie (LS-98c, LS-98d).
#
#   python tests/test_bridge_edge_split.py

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
sys.path.insert(0, os.path.join(_HERE, "..", "TestFiles", "Verificatie"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"

LOG = []


def _log(msg):
    LOG.append(msg)


bridge_utils.log = _log
import bridge_custom  # noqa: E402
import bridge_from_liml  # noqa: E402
import bridge_mesh  # noqa: E402
import bridge_to_aster  # noqa: E402
for _mod in (bridge_custom, bridge_from_liml, bridge_mesh, bridge_to_aster):
    _mod.log = _log
from verif_lib import Model, quadmesh, rect  # noqa: E402

FAILS = []
_CONFIG = copy.deepcopy(bridge_utils.CONFIG_BRIDGE)
STEEL = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
         'poissonratio="0.3" />')


def check(cond, text):
    print("{0:4s} {1}".format("OK" if cond else "FAIL", text))
    if not cond:
        FAILS.append(text)
        for m in LOG:
            if "ERROR" in m:
                print(u"     " + m)


def logged(fragment):
    return any(fragment in m for m in LOG)


def strips(thick=("2 mm", "2 mm"), lines=(), joined=False):
    """Two strips A, B (4 x 2 quad4); joined: B continues A (shared edge
    at x = 0.2, the force on that edge from both sides), else separate."""
    m = Model("S30")
    clamp, end = [], []
    for k, t in enumerate(thick):
        m.mat("P%d" % k, '<geometric type="Plate" thickness="%s" />' % t,
              STEEL)
        es = m.elset("S%d" % k, "P%d" % k)
        box = (rect(0.2 * k, 0.2 * (k + 1), 0, 0.02) if joined else
               rect(0, 0.2, 0.1 * k, 0.1 * k + 0.02))
        q = quadmesh(m, es, 4, 2, box)
        if joined:
            end += q["edges"]["u1" if k == 0 else "u0"]
            if k == 0:
                clamp += q["edges"]["u0"]
        else:
            clamp += q["edges"]["u0"]
            end += q["edges"]["u1"]
    m.face_selection("Klem", clamp)
    m.face_selection("Eind", end)
    m.add('<fixed selection="Klem" />')
    m.add('<force selection="Eind"><x>0 N</x><y>0 N</y><z>-2 N</z>'
          '</force>')
    if lines:
        m.add(u"<ccxmodeldefinition>{0}</ccxmodeldefinition>".format(
            u"\n".join(lines)))
    return m


def run(model):
    bridge_utils.CONFIG_BRIDGE.clear()
    bridge_utils.CONFIG_BRIDGE.update(copy.deepcopy(_CONFIG))
    bridge_utils.CONFIG_BRIDGE["language"] = "en"
    bridge_utils.CONFIG_BRIDGE["active_analysis"] = "lin_static_3d"
    del LOG[:]
    tmp = tempfile.mkdtemp()
    try:
        bridge_utils.CONFIG_BRIDGE["work_dir"] = tmp
        path = os.path.join(tmp, "model.liml")
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(model.xml())
        md = bridge_from_liml.extract_aster_data_from_liml(path)
        mesh = os.path.join(tmp, "model_mesh.mail")
        assert bridge_mesh.write_mesh(mesh, md)
        mail = io.open(mesh, encoding="utf-8").read()
        assert bridge_to_aster.generate_AsterSolver_files(
            tmp, md, mesh, "test.resu")
        comm = io.open(os.path.join(tmp, "study.comm"),
                       encoding="utf-8").read()
        return md, mail, comm
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def arete(comm):
    """[(group, FZ)] of the FORCE_ARETE entries (one _F or a tuple)."""
    i = comm.find("FORCE_ARETE=")
    if i < 0:
        return []
    block = comm[i:comm.find("\n)", i)]
    return [(g, float(v)) for g, v in re.findall(
        r"_F\(GROUP_MA='(\w+)', FZ=([-0-9.eE+]+)\)", block)]


def close(a, b):
    return abs(a - b) <= 1e-9 * max(1.0, abs(b))


# --- equal element and thickness: no split, unchanged ---
md, mail, comm = run(strips())
check("BRED" not in mail and not md.get("edge_splits") and
      len(arete(comm)) == 1 and arete(comm)[0][0] == "Eind" and
      close(arete(comm)[0][1], -2.0 / 0.04),
      "equal: one FORCE_ARETE on the selection, no BRED group")

# --- different thickness: shared by length x thickness ---
md, mail, comm = run(strips(("2 mm", "4 mm")))
parts = arete(comm)
check(len(parts) == 2 and all(g.startswith("BRED") for g, _v in parts),
      "thickness 2/4 mm: two parts {0}".format(parts))
if len(parts) == 2:
    # total = sum(q_k L_k), L = 0.02 each; strip 2 mm gets 2/3 N
    total = sum(v * 0.02 for _g, v in parts)
    check(abs(total + 2.0) < 1e-9 and
          abs(parts[0][1] * 0.02 + 2.0 / 3.0) < 1e-9,
          "thickness: total 2 N, 2 mm strip 2/3 N")
    check(all(re.search(r"GROUP_MA='{0}', PHENOMENE='MECANIQUE', "
                        r"MODELISATION='DKT'".format(g), comm)
              for g, _v in parts),
          "thickness: both parts in AFFE_MODELE with DKT")
    check(all(re.search(r"GROUP_MA\n {0}\n".format(g), mail)
              for g, _v in parts), "thickness: BRED groups in the mesh")

# --- different elements (DKT + DST), equal thickness ---
md, mail, comm = run(strips(lines=[u"**ASTER-ELEMENT S1: DST"]))
parts = arete(comm)
check(len(parts) == 2 and close(parts[0][1], parts[1][1]) and
      abs(sum(v * 0.02 for _g, v in parts) + 2.0) < 1e-9 and
      re.search(r"MODELISATION='DST'", comm),
      "DKT + DST: two parts with the same force per length")

# --- an edge shared by two components goes to one part only ---
md, mail, comm = run(strips(("2 mm", "4 mm"), joined=True))
parts = arete(comm)
check(len(parts) == 1 and abs(parts[0][1] * 0.02 + 2.0) < 1e-9,
      "shared edge: one part, the whole force once {0}".format(parts))

# --- only LINE_QUAD (general COQUE_3D, equal strips): split as well ---
_SAVED = _CONFIG.get("elem_shell")
_CONFIG["elem_shell"] = "COQUE_3D"
try:
    md, mail, comm = run(strips())
finally:
    _CONFIG["elem_shell"] = _SAVED
parts = arete(comm)
check(len(parts) == 2 and close(parts[0][1], parts[1][1]) and
      all(re.search(r"GROUP_MA='{0}', PHENOMENE='MECANIQUE', "
                    r"MODELISATION='COQUE_3D'".format(g), comm)
          for g, _v in parts),
      "LINE_QUAD only: two COQUE_3D parts {0}".format(parts))

bridge_utils.CONFIG_BRIDGE.clear()
bridge_utils.CONFIG_BRIDGE.update(_CONFIG)
print("")
print("{0} failure(s)".format(len(FAILS)))
sys.exit(1 if FAILS else 0)
