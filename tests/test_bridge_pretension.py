# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of the pre-tension section (bridge_bcs.PretensionSectionBC,
# bridge_pretension; CPython 3, without Mecway and Code-Aster): the XML as
# Mecway 34 writes it (force="true" / adjustment="true"), the prism axis,
# the cut through the bar of TestFiles/Verificatie PT-01 (node copies,
# LIAISON_DDL, reference node, BC on that node), implicit dynamics, the
# spring element variant (two nodal forces) and the rejections (explicit
# dynamics, spring variant outside linear static, two springs, all faces
# parallel). The results of a run: TestFiles/Verificatie (PT-01 ... PT-10).
#
#   python tests/test_bridge_pretension.py

from __future__ import print_function

import os
import sys
import shutil
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


bridge_utils.log = _log
import bridge_bcs  # noqa: E402
import bridge_pretension as bp  # noqa: E402
bp.log = _log
bridge_bcs.log = _log

FAILS = []


def check(cond, text):
    if not cond:
        FAILS.append(text)


# --- XML: mode attribute (Mecway 34) ---
bc = bridge_bcs.SUPPORTED_BCS["pretensionsection"]
for xml, mode, value in (
        ('<pretensionsection selection="s" force="true"><force>10 kN</force>'
         '<adjustment>0 m</adjustment></pretensionsection>', "force", 1e4),
        ('<pretensionsection selection="s" adjustment="true"><force>0 N'
         '</force><adjustment>0.01 mm</adjustment></pretensionsection>',
         "adjustment", 1e-5),
        # force="false" or no attribute: Mecway 34 still applies the force
        ('<pretensionsection selection="s" force="false"><force>2 kN'
         '</force><adjustment>1 mm</adjustment></pretensionsection>',
         "force", 2e3),
        ('<pretensionsection selection="s"><force>3 kN</force>'
         '</pretensionsection>', "force", 3e3)):
    p = bc.parse_xml(ET.fromstring(xml), ET.fromstring("<liml />"))
    check(p["mode"] == mode and abs(p["value"] - value) < 1e-9 * value,
          "parse_xml {0}: {1}".format(xml[:60], p))
    d = bc.to_aster_dict(p)
    key = "FX" if mode == "force" else "DX"
    check(list(d) == [key], "to_aster_dict {0}".format(d))
    check(bc.keyword(p) == ("FORCE_NODALE" if mode == "force"
                            else "DDL_IMPO"), "keyword {0}".format(mode))

# --- axis ---
ax = bp.prism_axis([(1.0, 0.0, 0.0), (0.0, 0.0, 1.0)])
check(ax == (0.0, 1.0, 0.0), "axis of two lateral faces: {0}".format(ax))
import math  # noqa: E402
ring = [(math.cos(a), 0.0, math.sin(a)) for a in
        [k * math.pi / 8 for k in range(16)]] + [(0.0, 1.0, 0.0),
                                                 (0.0, -1.0, 0.0)]
ax = bp.prism_axis(ring)
check(ax is not None and abs(ax[1] - 1.0) < 1e-12,
      "axis of a cylinder with end faces: {0}".format(ax))
check(bp.prism_axis([(1.0, 0.0, 0.0), (-1.0, 0.0, 0.0)]) is None,
      "parallel faces give no axis")

# --- cut through the bar of PT-01 ---
import tests_boutvoorspanning as T  # noqa: E402
from bridge_from_liml import extract_aster_data_from_liml  # noqa: E402
from bridge_mesh import write_mesh  # noqa: E402

work = tempfile.mkdtemp(prefix="mab_pretension_")
try:
    bridge_utils.CONFIG_BRIDGE["work_dir"] = work

    def run(model, analysis="lin_static_3d"):
        bridge_utils.CONFIG_BRIDGE["active_analysis"] = analysis
        path = model.write(os.path.join(work, "model.liml"))
        md = extract_aster_data_from_liml(path)
        ok = write_mesh(os.path.join(work, "model.mail"), md)
        return md, ok

    m = T.build_pt01()
    md, ok = run(m)
    check(ok, "write_mesh PT-01")
    sec = md.get("pretension_sections") or []
    check(len(sec) == 1, "one section: {0}".format(sec))
    if sec:
        s = sec[0]
        check(s["axis"] == (0.0, 1.0, 0.0) and abs(s["s_cut"] - 0.05) < 1e-12
              and (s["below"], s["above"]) == (4, 4) and s["pairs"] == 21,
              "section PT-01: {0}".format(s))
        check(abs(s["area"] - 1e-4) < 1e-12, "area {0}".format(s["area"]))
        eqs = [e for e in md["constraint_equations"]
               if e.get("source") == "pretension"]
        check(len(eqs) == 21 * 3 + 2, "relations: {0}".format(len(eqs)))
        ref = s["ref"]
        normal = [e for e in eqs if any(t[0] == ref and t[1] == "DX"
                                        for t in e["terms"])]
        check(len(normal) == 21 and all(
            len(e["terms"]) == 3 and e["terms"][0][1] == "DY"
            for e in normal), "normal relations along Y")
        pbc = [b for b in md["bcs"] if b["type"] == "pretensionsection"]
        check(len(pbc) == 1 and pbc[0]["selection"] == s["group"] and
              pbc[0]["aster_target"] == "GROUP_NO" and
              pbc[0]["aster_keyword"] == "FORCE_NODALE" and
              pbc[0]["aster_dict"] == {"FX": 1e4},
              "BC on the reference node: {0}".format(pbc))
        mail = open(os.path.join(work, "model.mail")).read()
        check("PT{0} N{0}".format(ref) in mail.replace("\n", " ") and
              "BRPRET" in mail and s["group"] in mail,
              "POI1 cell and groups in the mesh")
        check(md["poi1_groups"].get("BRPRET") == "DIS_T", "DIS_T group")

    # implicit dynamics (S15b): translated like in static
    del LOG[:]
    md, ok = run(T.build_pt06(), "dyna_impl_3d")
    sec = md.get("pretension_sections") or []
    check(ok and len(sec) == 1 and [b["aster_dict"] for b in md["bcs"]
                                    if b["type"] == "pretensionsection"]
          == [{"FX": 1000.0}], "implicit dynamics translated: {0}".format(
              sec))
    # explicit dynamics: rejected
    del LOG[:]
    md, ok = run(T.build_pt06(), "dyna_expl_3d")
    check(not md.get("pretension_sections") and any(
        "implicit dynamics" in l and "ERROR" in l for l in LOG),
        "explicit dynamics rejected")

    # spring element variant (S15b): two nodal forces k d along the axis;
    # force="true" still uses the adjustment (like Mecway)
    del LOG[:]
    md, ok = run(T.build_pt10())
    sp = [b for b in md["bcs"] if b["type"] == "pretensionsection"]
    e = T.E10
    want = [dict((c, s * 1000.0 * 2e-3 * e[i]) for i, c in
                 enumerate(("FX", "FY", "FZ"))) for s in (1.0, -1.0)]
    check(ok and len(sp) == 2 and not md.get("pretension_sections") and
          all(b["aster_keyword"] == "FORCE_NODALE" and
              b["aster_target"] == "GROUP_NO" for b in sp) and
          all(abs(sp[i]["aster_dict"][c] - want[i][c]) < 1e-12
              for i in range(2) for c in want[i]) and
          [b["selection"] for b in sp] == ["BRPS1A", "BRPS1B"],
          "spring variant PT-10: {0}".format(sp))
    mail = open(os.path.join(work, "model.mail")).read()
    check("BRPS1A" in mail and "BRPS1B" in mail, "spring node groups")
    md, ok = run(T.build_pt09())
    sp = [b for b in md["bcs"] if b["type"] == "pretensionsection"]
    check(len(sp) == 2 and abs(sp[0]["aster_dict"]["FX"] - 1.0) < 1e-12,
          "spring variant with force=\"true\": adjustment used: {0}".format(
              sp))
    # spring variant outside linear static: rejected (geometric stiffness)
    del LOG[:]
    md, ok = run(T.build_pt09(), "buckling_3d")
    check(not [b for b in md["bcs"] if b["type"] == "pretensionsection" and
               not b.get("skip")] and any(
        "only in linear static" in l for l in LOG),
        "spring variant in buckling rejected")
    # two springs in one selection: rejected
    m = T.build_pt09()
    m.selections = [s_ for s_ in m.selections if 'name="VeerVlak"' not in s_]
    m.face_selection("VeerVlak", [(1, 1), (2, 1)])
    del LOG[:]
    md, ok = run(m)
    check(any("exactly one spring" in l for l in LOG),
          "two springs rejected")
    # all selected faces parallel: no axis
    m = T.build_pt01()
    m.selections = [s_ for s_ in m.selections if 'name="Bout"' not in s_]
    els = [e for e in m.elsets[0][2]]
    m.face_selection("Bout", [(els[0][0], 4), (els[1][0], 4)])
    del LOG[:]
    md, ok = run(m)
    check(not md.get("pretension_sections") and any(
        "no axis" in l for l in LOG), "parallel faces rejected")
finally:
    shutil.rmtree(work, ignore_errors=True)

if FAILS:
    print("FAILED ({0}):".format(len(FAILS)))
    for f in FAILS:
        print("  " + f)
    sys.exit(1)
print("OK: pre-tension section")
