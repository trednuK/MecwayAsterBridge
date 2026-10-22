# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of a contact whose face selections are empty in the .liml
# (Mecway 34 replaces spaces in selection names by underscores when it
# opens an older model and then writes selectionmaster=""; seen 22 Oct
# 2026 with Voorbeeld_C.liml). Nonlinear static: ERROR before Code-Aster;
# linear static: WARNING and the run goes on (Mecway ignores the contact
# there too). Works in a temporary folder; bridge_utils.py is not written.
#
#   python tests/test_bridge_lost_contact.py

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
_MODEL = os.path.join(_HERE, "..", "TestFiles", "Voorbeelden",
                      "Voorbeeld_C.liml")


def check(cond, text):
    print(("OK   " if cond else "FAIL ") + text)
    if not cond:
        _FAILED.append(text)


def _run(tmp, liml_text, analysis):
    work = tempfile.mkdtemp(dir=tmp)
    liml = os.path.join(work, "model.liml")
    with io.open(liml, "w", encoding="utf-8") as f:
        f.write(liml_text)
    u.CONFIG_BRIDGE["work_dir"] = work
    u.CONFIG_BRIDGE["active_analysis"] = analysis
    md = extract_aster_data_from_liml(liml)
    ok = (md is not None and write_mesh(os.path.join(work, "m.mail"), md)
          and generate_AsterSolver_files(work, md, os.path.join(work, "m.mail"),
                                         "test.resu"))
    log = io.open(os.path.join(work, "bridge_log.txt"), encoding="utf-8").read()
    return bool(ok), log


def main():
    saved = dict(u.CONFIG_BRIDGE)
    tmp = tempfile.mkdtemp(prefix="bridge_lost_contact_")
    try:
        text = io.open(_MODEL, encoding="utf-8").read()
        lost = text.replace('selectionmaster="01_Contact_onder"',
                            'selectionmaster=""').replace(
            'selectionslave="02_Contact_boven"', 'selectionslave=""')
        check(lost != text, "model with emptied contact selections")
        ok, log = _run(tmp, text, "nonlin_static_3d")
        check(ok and "no master or slave selection" not in log,
              "intact contact: no lost-contact message")
        ok, log = _run(tmp, lost, "nonlin_static_3d")
        check(not ok and "ERROR: A contact in Loads & Constraints has no "
              "master or slave selection" in log,
              "nonlinear static: ERROR before Code-Aster")
        check("Self-contact" not in log,
              "no misleading self-contact message")
        ok, log = _run(tmp, lost, "lin_static_3d")
        check(ok and "WARNING: A contact in Loads & Constraints" in log,
              "linear static: WARNING, run goes on (Mecway ignores it)")
    finally:
        u.CONFIG_BRIDGE.clear()
        u.CONFIG_BRIDGE.update(saved)
        shutil.rmtree(tmp, ignore_errors=True)
    print("{0} failure(s)".format(len(_FAILED)))
    return 1 if _FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
