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
import io
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
      summary[0].endswith(", 1 METALLURGIE, 1 XFEM, 0 CONSTANT, 0 HYST, 1 SECTIE."))
check("geen ERROR", not [l for l in LOG if l.startswith("ERROR")])

# Alleen XFEM: de samenvatting noemt de regel ook dan
del LOG[:]
bridge_custom.parse([u"** ASTER-XFEM vorm=CIRKEL, r=1"])
check("alleen XFEM in de samenvatting",
      [l for l in LOG if l.endswith(", 1 XFEM, 0 CONSTANT, 0 HYST, 0 SECTIE.")] != [])

# CONSTANT (lineaire knik met dode last, bridge_to_aster._dead_live_split)
del LOG[:]
out = bridge_custom.parse([u"** ASTER-CONSTANT KopD, gravity\n"
                           u"#ASTER-CONSTANT Rand"])
check("CONSTANT gelezen", out["constant"] == ["KopD", "gravity", "Rand"])
check("CONSTANT zonder ERROR", not [l for l in LOG if l.startswith("ERROR")])

# HYST (verliesfactor, bridge_harmonic._loss_factors): regel bewaard en geteld
del LOG[:]
out = bridge_custom.parse([u"** ASTER-HYST Staal = 0.02\n# ASTER-HYST * = 0.1"])
check("HYST gelezen", out["hyst"] == [u"Staal = 0.02", u"* = 0.1"])
check("HYST in de samenvatting",
      [l for l in LOG if l.endswith(", 0 XFEM, 0 CONSTANT, 2 HYST, 0 SECTIE.")] != [])

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

# Contact keyword lines: split, keys, ownership, catalogue (KNOWN user
# keys from the docs and verification as a regression)
check("split: commas inside (), quotes and <<..>> stay",
      bridge_custom.split_pieces(
          "SANS_GROUP_NO=('<<a, b>>', 'X'), CONTACT_INIT='OUI', D=1") ==
      ["SANS_GROUP_NO=('<<a, b>>', 'X')", "CONTACT_INIT='OUI'", "D=1"])
check("line keys, piece without '=' is None",
      bridge_custom.line_keys("algo_cont='PENALISATION', x") ==
      ["ALGO_CONT", None])
for kind, line in (("zone", "CONTACT_INIT='OUI'"),
                   ("zone", "ALGO_CONT='PENALISATION', COEF_PENA_CONT=1.0E14"),
                   ("zone", "INTEGRATION='NCOTES'"),
                   ("zone", "SANS_GROUP_NO='<<Vast>>'"),
                   ("contact", "ALGO_RESO_GEOM='NEWTON'"),
                   ("contact", "ALGO_RESO_CONT='POINT_FIXE', ITER_CONT_MAXI=50"),
                   ("contact", "LISSAGE='OUI'"),
                   ("bonded", "DISTANCE_MAX=0.001, DISTANCE_ALARME=0.002"),
                   ("bonded", "ELIM_MULT='NON'")):
    e, w = bridge_custom.check_lines(kind, [line])
    check("documented {0} line accepted: {1}".format(kind, line),
          not e and not w)
e, w = bridge_custom.check_lines("zone", ["GROUP_MA_ESCL='X'", "COULOMB=0.3"])
check("owned zone keys: two ERRORs", len(e) == 2 and not w)
e, w = bridge_custom.check_lines("zone", ["CONTACT_INIT='OUI'",
                                          "CONTACT_INIT='NON'"])
check("duplicate key over two lines: ERROR", len(e) == 1)
e, w = bridge_custom.check_lines("contact", ["ALGO_RESO_GOEM='NEWTON'"])
check("typo: WARNING, no ERROR", not e and len(w) == 1)
e, w = bridge_custom.check_lines("zone", ["CONTACT_INIT='OUI',,DIST_MAXI=1"])
check("empty piece: ERROR", len(e) == 1)
e, w = bridge_custom.check_lines("zone", ["'A=b'"])
check("quoted key: ERROR (not a keyword)", len(e) == 1)
check("stray ')' does not stop the split",
      bridge_custom.split_pieces("A=1), B=2") == ["A=1)", "B=2"])
e, w = bridge_custom.check_lines("bonded", ["TYPE_RACCORD='MASSIF'"])
check("bonded: TYPE_RACCORD is the bridge's", len(e) == 1)
del LOG[:]
out = bridge_custom.parse([u"#ASTER-BONDED DISTANCE_MAX=0.001"])
check("#ASTER-BONDED parsed", out["bonded"] == ["DISTANCE_MAX=0.001"] and
      not [l for l in LOG if l.startswith("ERROR")])
# the lists against the installed Code-Aster 17.4 catalogue (skip without it)
import re as _re
cata = os.path.join(os.environ.get("LOCALAPPDATA", ""), "code_aster", "v2025",
                    "17.4", "lib", "aster", "code_aster", "Cata", "Commands")
if os.path.isfile(os.path.join(cata, "defi_contact.py")):
    def _facts(text, name):
        out = []
        for m in _re.finditer(name + r"\s*=\s*FACT\(", text):
            i, depth = m.end(), 1
            while depth:
                depth += (text[i] == "(") - (text[i] == ")")
                i += 1
            out.append(text[m.end():i])
        return out
    simp = r"\b([A-Z][A-Z0-9_]*)\s*=\s*SIMP\("
    dc = io.open(os.path.join(cata, "defi_contact.py"), encoding="utf-8",
                 errors="replace").read()
    zone = set()
    for r in _facts(dc, "ZONE"):
        zone |= set(_re.findall(simp, r))
    check("zone keys = catalogue 17.4",
          zone == set(bridge_custom.CONTACT_ZONE_KEYS))
    check("global keys = catalogue 17.4", set(_re.findall(simp, dc)) - zone ==
          set(bridge_custom.CONTACT_GLOBAL_KEYS))
    acm = io.open(os.path.join(cata, "affe_char_meca.py"), encoding="utf-8",
                  errors="replace").read()
    check("LIAISON_MAIL keys = catalogue 17.4",
          set(_re.findall(simp, _facts(acm, "LIAISON_MAIL")[0])) ==
          set(bridge_custom.LIAISON_MAIL_KEYS))
else:
    print("SKIP: Code-Aster 17.4 catalogue not found")

if check.failed:
    sys.exit(1)
print("Alle tests geslaagd.")
