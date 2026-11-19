# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of '#ASTER-ELEMENT <component>: <MODELISATION>' (Code-Aster
# element per Mecway component; Python 2.7 and 3, without Mecway and
# Code-Aster): the parser (bridge_custom.parse_elements), the per-elset
# choice and its checks in bridge_from_liml (_element_override,
# _check_element_requests), the names after bridge_mesh renames them and
# AFFE_MODELE in the generated .comm, the COQUE_3D fall-back on a
# shared clamp (bridge_to_aster._resolve_line_quad). Runs:
# TestFiles/Verificatie (LS-98).
#
#   python tests/test_element_override.py

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
from verif_lib import Model, quadmesh, hexmesh, linemesh, rect  # noqa: E402

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


def model(lines, analysis="S30", quad8=False):
    """Two disjoint strips (Plaat_A, Plaat_B; quad4 or quad8 for A), a beam
    (Balk) and a hex8 block (Blok), all clamped at x = 0, tip force."""
    m = Model(analysis)
    m.mat("Plaat2", '<geometric type="Plate" thickness="2 mm" />', STEEL)
    m.mat("Staaf", '<geometric type="CircularBar" roundod="10 mm" />',
          STEEL)
    m.mat("Vol", STEEL)
    m.elset("Plaat_A", "Plaat2")
    a = quadmesh(m, "Plaat_A", 4, 2, rect(0, 0.2, 0, 0.02),
                 order=2 if quad8 else 1)
    m.elset("Plaat_B", "Plaat2")
    b = quadmesh(m, "Plaat_B", 4, 2, rect(0, 0.2, 0.1, 0.12))
    m.elset("Balk", "Staaf")
    eids, nids = linemesh(m, "Balk", 4, (0, 0.3, 0), (0.2, 0.3, 0))
    m.elset("Blok", "Vol")
    h = hexmesh(m, "Blok", 4, 1, 1,
                lambda u, v, w: (0.2 * u, 0.5 + 0.02 * v, 0.02 * w))
    m.face_selection("Klem", a["edges"]["u0"] + b["edges"]["u0"] +
                     h["faces"]["u0"])
    m.node_selection("Klem_balk", [nids[0]])
    m.face_selection("Eind", a["edges"]["u1"] + b["edges"]["u1"])
    m.add('<fixed selection="Klem" />')
    m.add('<fixed selection="Klem_balk" />')
    m.add('<force selection="Eind"><x>0 N</x><y>0 N</y><z>-1 N</z>'
          '</force>')
    if lines:
        m.add(u"<ccxmodeldefinition>{0}</ccxmodeldefinition>".format(
            u"\n".join(lines)))
    return m


def run(lines, analysis="lin_static_3d", mecway="S30", quad8=False,
        generate=False, **config):
    bridge_utils.CONFIG_BRIDGE.clear()
    bridge_utils.CONFIG_BRIDGE.update(copy.deepcopy(_CONFIG))
    bridge_utils.CONFIG_BRIDGE["language"] = "en"
    bridge_utils.CONFIG_BRIDGE["active_analysis"] = analysis
    bridge_utils.CONFIG_BRIDGE.update(config)
    del LOG[:]
    tmp = tempfile.mkdtemp()
    try:
        bridge_utils.CONFIG_BRIDGE["work_dir"] = tmp
        # Model.write leaves its file open (IronPython reads it empty)
        path = os.path.join(tmp, "model.liml")
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(model(lines, mecway, quad8).xml())
        md = bridge_from_liml.extract_aster_data_from_liml(path)
        comm = None
        if md is not None and generate:
            mesh = os.path.join(tmp, "model_mesh.mail")
            assert bridge_mesh.write_mesh(mesh, md)
            assert bridge_to_aster.generate_AsterSolver_files(
                tmp, md, mesh, "test.resu")
            comm = io.open(os.path.join(tmp, "study.comm"),
                           encoding="utf-8").read()
        return md, comm
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --- parser ---
got, ok = bridge_custom.parse_elements(
    [u"Plaat_A: dst", u"Deel: met: dubbele punt : POU_D_T",
     u"Plaat_A: DST"])
check(ok and got == {u"Plaat_A": u"DST",
                     u"Deel: met: dubbele punt": u"POU_D_T"},
      "parse_elements: last colon, upper case, repeated equal line")
del LOG[:]
got, ok = bridge_custom.parse_elements([u"Plaat_A: DKT", u"Plaat_A: DST"])
check(ok and got[u"Plaat_A"] == u"DST" and logged("last one counts"),
      "parse_elements: differing lines -> last counts, WARNING")
for bad in (u"Plaat_A DKT", u": DKT", u"Plaat_A: Q4", u"Blok: LINE_QUAD"):
    del LOG[:]
    got, ok = bridge_custom.parse_elements([bad])
    check(not ok and logged("ERROR: '#ASTER-ELEMENT"),
          "parse_elements: bad line '{0}' -> ERROR".format(bad))
check(logged("LINE_QUAD makes the whole mesh"), "LINE_QUAD: own message")
out = bridge_custom.parse([u"#ASTER-ELEMENT Balk: POU_D_T",
                           u"**ASTER-ELEMENT Blok: 3D_SI"])
check(out["elements"] == [u"Balk: POU_D_T", u"Blok: 3D_SI"],
      "parse: #ASTER-ELEMENT and **ASTER-ELEMENT collected")

# --- per component, linear static, with the .comm ---
md, comm = run([u"**ASTER-ELEMENT Plaat_A: DST",
                u"**ASTER-ELEMENT Balk: POU_D_T",
                u"**ASTER-ELEMENT Blok: 3D_SI"], generate=True)
check(md is not None, "S30 with overrides: extract OK")
if md is not None:
    mods = md["elset_modelisations"]
    check(sorted(mods.values()) == ["3D_SI", "DKT", "DST", "POU_D_T"],
          "modelisations after write_mesh: {0}".format(sorted(mods.items())))
    check(comm is not None and re.search(r"MODELISATION='DST'", comm) and
          re.search(r"MODELISATION='DKT'", comm) and
          re.search(r"MODELISATION='POU_D_T'", comm) and
          re.search(r"MODELISATION='3D_SI'", comm),
          "AFFE_MODELE has DST, DKT, POU_D_T and 3D_SI")
    check(logged("Elset 'Plaat_A': element DST (#ASTER-ELEMENT)"),
          "INFO line per override")

# --- defaults unchanged without lines ---
md, _ = run([])
check(md is not None and sorted(md["elset_modelisations"].values()) ==
      ["3D", "DKT", "DKT", "POU_D_E"], "no lines: general defaults")

# --- general shell COQUE_3D, one component back to DKT ---
md, _ = run([u"**ASTER-ELEMENT Plaat_B: DKT"], elem_shell="COQUE_3D")
check(md is not None and md["elset_modelisations"]["Plaat_A"] == "COQUE_3D"
      and md["elset_modelisations"]["Plaat_B"] == "DKT" and
      "Plaat_B" not in md["shell_upgrades"] and
      md["shell_upgrades"]["Plaat_A"][0] == "LINE_QUAD",
      "elem_shell COQUE_3D + DKT for one component")

# --- COQUE_3D per component on a clamp shared with other elements ---
md, comm = run([u"**ASTER-ELEMENT Plaat_A: COQUE_3D"], generate=True)
check(md is not None and md["elset_modelisations"]["Plaat_A"] == "DKT" and
      md.get("_coque3d_fallback") and
      logged("COQUE_3D not applied to shells Plaat_A") and
      comm is not None and "LINE_QUAD=_F" not in comm,
      "COQUE_3D on a shared clamp: DKT with a WARNING, no LINE_QUAD")

# --- 3D_SI on a component that is not hex8 only (pure function) ---
del LOG[:]
got = bridge_from_liml._element_override(
    "Blok", "3D_SI", set(["hex8", "wedge6"]),
    {"solver_command": "MECA_STATIQUE"}, False, "3D")
check(got is None and logged("3D_SI only for a component with hex8 only"),
      "ERROR: 3D_SI on hex8 + wedge6")
del LOG[:]
got = bridge_from_liml._element_override(
    "Blok", "3D_SI", set(["hex8"]),
    {"solver_command": "DYNA_NON_LINE", "schema": "DIFF_CENT"}, False, "3D")
check(got == "3D" and logged("3D_SI does not work with an explicit"),
      "explicit: 3D_SI -> 3D with a WARNING")
del LOG[:]
got = bridge_from_liml._element_override(
    "Balk", "POU_D_TG", set(["line2"]),
    {"solver_command": "DYNA_NON_LINE", "schema": "DIFF_CENT"}, False, "3D")
check(got == "POU_D_T" and logged("is about the line '#ASTER-ELEMENT Balk"),
      "explicit: POU_D_TG -> POU_D_T, WARNING named")

# --- analysis guard: DST in nonlinear static -> DKT with a WARNING ---
md, _ = run([u"**ASTER-ELEMENT Plaat_A: DST"], analysis="nonlin_static_3d",
            mecway="L30")
check(md is not None and md["elset_modelisations"]["Plaat_A"] == "DKT" and
      logged("'#ASTER-ELEMENT Plaat_A: DST': DST only works linearly"),
      "nonlinear static: DST -> DKT with a WARNING naming the line")

# --- errors stop the run ---
for lines, quad8, text, what in (
        ([u"**ASTER-ELEMENT Plaat_A: DKT"], True, "allowed is COQUE_3D",
         "DKT on quad8"),
        ([u"**ASTER-ELEMENT Balk: 3D_SI"], False, "allowed is POU_D_E",
         "solid value on a beam"),
        ([u"**ASTER-ELEMENT Plaat_A: POU_D_E"], False, "allowed is COQUE_3D",
         "beam value on a shell"),
        ([u"**ASTER-ELEMENT Onbekend: DKT"], False,
         "no component with that name", "unknown component"),
        ([u"**ASTER-ELEMENT Plaat_A: Q4G"], False, "expected '<component>",
         "unknown value")):
    md, _ = run(lines, quad8=quad8)
    check(md is None and logged(text), "ERROR, run stops: " + what)
md, _ = run([u"**ASTER-ELEMENT Blok: 3D"], elem_hex8="LINE_QUAD")
check(md is None and logged("not together with the general setting"),
      "ERROR: solid override with elem_hex8 = LINE_QUAD")
# POU_D_T_GD next to another beam (large displacements)
cfg = copy.deepcopy(_CONFIG["analyses"])
cfg["nonlin_static_3d"]["deformation"] = "GROT_GDEP"
md, _ = run([u"**ASTER-ELEMENT Balk: POU_D_T_GD"], analysis="nonlin_static_3d",
            mecway="L30", analyses=cfg)
check(md is not None and md["elset_modelisations"]["Balk"] == "POU_D_T_GD",
      "POU_D_T_GD alone (all beams): OK")

# POU_D_T_GD mixed with another beam (pure check)
del LOG[:]
ok = bridge_from_liml._check_element_requests(
    {"elset_modelisations": {"B1": "POU_D_T_GD", "B2": "POU_D_E"}},
    {"B1": "POU_D_T_GD"}, {"B1": "POU_D_T_GD"}, ["B1", "B2"], False)
check(not ok and logged("together with other beams (POU_D_E)"),
      "ERROR: POU_D_T_GD mixed with POU_D_E")
del LOG[:]
ok = bridge_from_liml._check_element_requests(
    {"elset_modelisations": {"B1": "BARRE"}}, {"B1": "POU_D_T"},
    {"B1": "POU_D_T"}, ["B1"], False)
check(not ok and logged("follows from the Mecway element type (BARRE)"),
      "ERROR: override on a truss component")

# --- thermal: lines not used ---
md, _ = run([u"**ASTER-ELEMENT Plaat_A: DST"], analysis="ther_3d",
            mecway="T30")
check(logged("#ASTER-ELEMENT lines are not used in this analysis"),
      "thermal: WARNING, lines not used")

bridge_utils.CONFIG_BRIDGE.clear()
bridge_utils.CONFIG_BRIDGE.update(_CONFIG)
print("")
print("{0} failure(s)".format(len(FAILS)))
sys.exit(1 if FAILS else 0)
