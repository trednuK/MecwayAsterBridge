# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of bridge_floating (CPython 3, without Mecway and
# Code-Aster): a block resting on a fixed block with only contact between
# them is reported in nonlinear static (WARNING naming its component and the
# contact selection); not with a weak elastic support, with bonded contact,
# with a support of its own, or in linear static. Samples/BoltedJoint (plate
# B and the bolt side behind a pre-tension section with a force) is checked
# in docs/Instellingen_contact_en_nietlineair.md par. 3.11.
#
#   python tests/test_bridge_floating.py

from __future__ import print_function

import os
import sys
import shutil
import tempfile

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


import bridge_floating  # noqa: E402
bridge_floating.log = _log
from verif_lib import Model, hexmesh, box  # noqa: E402
from bridge_from_liml import extract_aster_data_from_liml  # noqa: E402
from bridge_mesh import write_mesh  # noqa: E402

FAILS = []


def check(cond, text):
    if not cond:
        FAILS.append(text)


STEEL = ('<mechanical type="Isotropic" youngsmodulus="200 GPa" '
         'poissonratio="0.3" />')
CONTACT = ('<contact2 selectionmaster="Top" selectionslave="Bottom" '
           'type="{0}"><tolerance>0 m</tolerance><normalstiffness>1e5 GPa/m'
           '</normalstiffness><tangentialstiffness>1e5 GPa/m'
           '</tangentialstiffness><frictioncoefficient>{1}'
           '</frictioncoefficient></contact2>')


def make(contact="unilateralelastic", friction="0.5", extra=(),
         analysis="L30", own_support=False):
    """Block B (own nodes, 0.1 um above A) on the fixed block A."""
    m = Model(analysis, timesteps={"timeperiod": "1 s", "stepsize": "0.5 s"}
              if analysis == "L30" else None)
    m.elset("A", "Steel")
    m.elset("B", "Steel")
    m.mat("Steel", STEEL)
    a = hexmesh(m, "A", 2, 1, 2, box(0, 0.02, 0, 0.01, 0, 0.02))
    b = hexmesh(m, "B", 2, 1, 2, box(0, 0.02, 0.0100001, 0.02, 0, 0.02))
    m.face_selection("Fix", a["faces"]["v0"])
    m.face_selection("Top", a["faces"]["v1"])
    m.face_selection("Bottom", b["faces"]["v0"])
    m.face_selection("Load", b["faces"]["v1"])
    m.face_selection("Side", b["faces"]["u0"])
    m.add('<fixed selection="Fix" />')
    m.add(CONTACT.format(contact, friction))
    m.add('<force selection="Load"><x>0 N</x><y>-100 N</y><z>0 N</z>'
          '</force>')
    if own_support:
        m.add('<frictionless selection="Side" />')
    for x in extra:
        m.add(x)
    return m


work = tempfile.mkdtemp(prefix="mab_floating_")
try:
    bridge_utils.CONFIG_BRIDGE["work_dir"] = work

    def run(model, analysis="nonlin_static_3d"):
        del LOG[:]
        bridge_utils.CONFIG_BRIDGE["active_analysis"] = analysis
        path = model.write(os.path.join(work, "model.liml"))
        md = extract_aster_data_from_liml(path)
        ok = write_mesh(os.path.join(work, "model.mail"), md)
        return md, ok

    md, ok = run(make())
    fp = md.get("floating_parts") or []
    check(ok and len(fp) == 1 and fp[0]["elsets"] == ["B"] and
          fp[0]["contacts"] == ["Bottom"] and fp[0]["friction"],
          "block on contact reported: {0}".format(fp))
    check(any("is held in place only by contact ('Bottom')" in l and
              "Elastic support" in l and "par. 3.11" in l for l in LOG),
          "WARNING text: {0}".format([l[:120] for l in LOG]))
    md, ok = run(make(extra=['<elasticsupport selection="Load"><modulus>'
                             '1e6 Pa/m</modulus><tangential>1e6 Pa/m'
                             '</tangential></elasticsupport>']))
    check(ok and not md.get("floating_parts"), "elastic support holds it")
    md, ok = run(make(contact="bondedtie"))
    check(ok and not md.get("floating_parts"), "bonded contact holds it")
    md, ok = run(make(own_support=True))
    check(ok and not md.get("floating_parts"),
          "a support of its own (frictionless) counts")
    md, ok = run(make(analysis="S30"), "lin_static_3d")
    check(ok and not md.get("floating_parts"), "not in linear static")
finally:
    shutil.rmtree(work, ignore_errors=True)

if FAILS:
    print("FAILED ({0}):".format(len(FAILS)))
    for f in FAILS:
        print("  " + f)
    sys.exit(1)
print("OK: parts held only by contact (bridge_floating)")
