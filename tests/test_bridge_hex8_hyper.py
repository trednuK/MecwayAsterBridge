# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test (CPython) of the follow-up on GitHub issue #5 (bonded rubber
# block, Code-Aster about 3x stiffer than CCX with C3D8R):
#   - <elementtype> (CCX > custom element type) is a WARNING, not an
#     unsupported load (bridge_from_liml, step 2d-ter);
#   - hex8 '3D_SI' with hyperelastic material becomes '3D' with a WARNING
#     (ELEMENTSSI_1, bridge_to_aster._hyper_hex8);
#   - hex8 '3D' with hyperelastic material: volumetric locking WARNING
#     instead of the bending warning (bridge_to_aster._resolve_line_quad).
# Model: TestFiles/Verificatie/modellen/NL-50.liml (one hex8, Neo Hooke).
#
#   python tests/test_bridge_hex8_hyper.py

from __future__ import print_function

import io
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils as u  # noqa: E402
from bridge_from_liml import extract_aster_data_from_liml  # noqa: E402
from bridge_mesh import write_mesh  # noqa: E402
from bridge_to_aster import generate_AsterSolver_files  # noqa: E402

u.CONFIG_BRIDGE["language"] = "en"
_FAILED = []
_MODEL = os.path.join(_HERE, "..", "TestFiles", "Verificatie", "modellen",
                      "NL-50.liml")
_ELEMENTTYPE = '  <elementtype selection="" shape="hex8" type="C3D8R" />\n'
_ISOTROPIC = ('<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
              'poissonratio="0.3" />')
_LOCKING = "the fully integrated hex8 locks"
_BENDING = "WARNING: Hex8 is stiffer in Code-Aster than in Mecway"


def check(cond, text):
    print(("OK   " if cond else "FAIL ") + text)
    if not cond:
        _FAILED.append(text)


def _run(tmp, hex8, elementtype=False, isotropic=False):
    """Smoke test; returns (model_data, log text, study.comm text)."""
    work = tempfile.mkdtemp(dir=tmp)
    with io.open(_MODEL, encoding="utf-8") as f:
        text = f.read()
    if elementtype:
        text = text.replace("  <mat ", _ELEMENTTYPE + "  <mat ", 1)
    if isotropic:
        start = text.index("<mechanical ")
        text = text[:start] + _ISOTROPIC + text[text.index("/>", start) + 2:]
    liml = os.path.join(work, "model.liml")
    with io.open(liml, "w", encoding="utf-8") as f:
        f.write(text)
    u.CONFIG_BRIDGE["work_dir"] = work
    u.CONFIG_BRIDGE["active_analysis"] = "nonlin_static_3d"
    u.CONFIG_BRIDGE["elem_hex8"] = hex8
    md = extract_aster_data_from_liml(liml)
    mail = os.path.join(work, "m.mail")
    ok = (md is not None and write_mesh(mail, md) and
          generate_AsterSolver_files(work, md, mail, "test.resu"))
    check(bool(ok), "{0}: files generated".format(hex8))
    log = io.open(os.path.join(work, "bridge_log.txt"),
                  encoding="utf-8").read()
    comm = ""
    if ok:
        comm = io.open(os.path.join(work, "study.comm"),
                       encoding="utf-8").read()
    return md, log, comm


def test_elementtype(tmp):
    md, log, _ = _run(tmp, "3D", elementtype=True)
    check("WARNING: Custom CCX element type C3D8R for hex8 (all elements)"
          in log and "(hex8: 3D)" in log,
          "elementtype: WARNING with the CCX type and the hex8 choice")
    check("ERROR: Load/boundary condition 'elementtype'" not in log and
          not any("elementtype" in s for s in md.get("skipped_loads", [])),
          "elementtype: no 'unsupported load' ERROR, not in skipped_loads")


def test_hyper_3d(tmp):
    _, log, comm = _run(tmp, "3D")
    check(_LOCKING in log and "K/G = 1000" in log,
          "hyperelastic hex8 '3D': locking WARNING with K/G")
    check(_BENDING not in log,
          "hyperelastic hex8 '3D': no bending warning on top")
    check("MODELISATION='3D')" in comm, "hyperelastic hex8 '3D': 3D")


def test_hyper_3d_si(tmp):
    _, log, comm = _run(tmp, "3D_SI")
    check("WARNING: Hex8 '3D_SI' (under-integration) does not work with "
          "hyperelastic material (elset Kubus)" in log,
          "hyperelastic hex8 '3D_SI': fallback WARNING")
    check("MODELISATION='3D')" in comm and "3D_SI" not in comm.split(
        "AFFE_MODELE")[1].split(")")[0] if "AFFE_MODELE" in comm else False,
          "hyperelastic hex8 '3D_SI': AFFE_MODELE with '3D'")
    check(_LOCKING in log, "hyperelastic hex8 '3D_SI': locking WARNING")


def test_hyper_line_quad(tmp):
    _, log, comm = _run(tmp, "LINE_QUAD")
    check(_LOCKING not in log and "LINE_QUAD=_F(TOUT='OUI')" in comm,
          "hyperelastic hex8 'LINE_QUAD': quadratic, no locking WARNING")


def test_isotropic_3d(tmp):
    _, log, _ = _run(tmp, "3D", isotropic=True)
    check(_BENDING in log and _LOCKING not in log,
          "isotropic hex8 '3D': bending warning as before")
    _, log, comm = _run(tmp, "3D_SI", isotropic=True)
    check("MODELISATION='3D_SI'" in comm,
          "isotropic hex8 '3D_SI': stays 3D_SI")


def main():
    saved = dict(u.CONFIG_BRIDGE)
    tmp = tempfile.mkdtemp(prefix="bridge_hex8_hyper_")
    try:
        test_elementtype(tmp)
        test_hyper_3d(tmp)
        test_hyper_3d_si(tmp)
        test_hyper_line_quad(tmp)
        test_isotropic_3d(tmp)
    finally:
        u.CONFIG_BRIDGE.clear()
        u.CONFIG_BRIDGE.update(saved)
        shutil.rmtree(tmp, ignore_errors=True)
    print("{0} failure(s)".format(len(_FAILED)))
    return 1 if _FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
