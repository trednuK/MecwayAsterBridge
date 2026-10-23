# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test van Scripts/bridge_custom.py (Python 2.7 en 3): het lezen van
# #ASTER-regels en de INFO-samenvatting in de log.
#
#   python tests/test_bridge_custom.py

from __future__ import print_function

import os
import sys

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "nl"
import bridge_custom  # noqa: E402

LOG = []
bridge_custom.log = LOG.append      # logregels opvangen, niets schrijven


def check(name, cond):
    print(("OK   " if cond else "FOUT ") + name)
    if not cond:
        check.failed = True


check.failed = False

# Alle soorten uit de tabel van docs/ASTER_regels_voorbeelden.md par. 2, met
# de drie voorvoegsels en een kleine-lettersoort.
TEXT = u"\n".join([
    u"#ASTER verb = AFFE_CHAR_MECA(MODELE=model,",
    u"#ASTER     LIAISON_ELEM=_F(OPTION='3D_POU', GROUP_MA_1='<<Tip>>',",
    u"#ASTER                     GROUP_NO_2='<<BalkStart>>'))",
    u"$ ASTER-excit verb",
    u"** ASTER-ZONE CONTACT_INIT='OUI'",
    u"#ASTER-CONTACT ALGO_RESO_GEOM='NEWTON'",
    u"#ASTER-OPTIE newton_max_iter = 40",
    u"#ASTER-POST IMPR_TABLE(TABLE=reac, UNITE=6)",
    u"#ASTER-BEZWIJKEN Staal = 0.2",
    u"#ASTER-SPECTRE X, Y = spec, ECHELLE=9.81",
    u"#ASTER-BRON Luidspreker = 2 mm/s, 90",
    u"#ASTER-LASBRON Q=1250, v=0.005",
    u"#ASTER-FASE Last2 = 180",
    u"#ASTER-MATERIAAL Staal: TC=(20, 600), E=(210e9, 120e9)",
    u"#ASTER-WOHLER Staal: Sf = 900 MPa, b = -0.1",
    u"#ASTER-METALLURGIE Staal: staal=16MND5",
    u"#ASTER-XFEM vorm=CIRKEL, centrum=(0, 0, 0), r=20 mm, normaal=(0, 0, 1)",
    u"** ASTER-SECTIE Profiel: A=1e-3, IY=1e-6, IZ=2e-7, JX=1e-8, AY=1.2",
    u"$ Mystran-commentaar wordt overgeslagen",
])
out = bridge_custom.parse([TEXT])
check("drie regels code", len(out["code"]) == 3)
check("EXCIT met kleine letters", out["excit"] == ["verb"])
check("OPTIE", out["options"] == {"newton_max_iter": "40"})
check("SPECTRE X en Y", sorted(out["spectrum"]) == ["X", "Y"])
check("XFEM gelezen", len(out["xfem"]) == 1)
check("SECTIE gelezen", out["sections"] == [
    u"Profiel: A=1e-3, IY=1e-6, IZ=2e-7, JX=1e-8, AY=1.2"])
summary = [l for l in LOG if l.startswith("INFO: #ASTER lines:")]
check("een INFO-samenvatting", len(summary) == 1)
check("samenvatting telt XFEM en SECTIE", bool(summary) and
      summary[0].endswith(", 1 METALLURGIE, 1 XFEM, 1 SECTIE."))
check("geen ERROR", not [l for l in LOG if l.startswith("ERROR")])

# Alleen XFEM: de samenvatting noemt de regel ook dan
del LOG[:]
bridge_custom.parse([u"** ASTER-XFEM vorm=CIRKEL, r=1"])
check("alleen XFEM in de samenvatting",
      [l for l in LOG if l.endswith(", 1 XFEM, 0 SECTIE.")] != [])

# Foute regels: ERROR en overgeslagen
del LOG[:]
out = bridge_custom.parse([u"#ASTER-FOO bla\n#ASTER_EXCIT verb\n"
                           u"#ASTER-OPTIE zonder_is\n#ASTER-SPECTRE Q = x"])
errors = [l for l in LOG if l.startswith("ERROR")]
check("vier ERROR-regels", len(errors) == 4)
check("onbekende soort", any("Onbekende regel '#ASTER-FOO'" in l
                             for l in errors))
check("niets overgenomen", not out["excit"] and not out["options"]
      and not out["spectrum"])

if check.failed:
    sys.exit(1)
print("Alle tests geslaagd.")
