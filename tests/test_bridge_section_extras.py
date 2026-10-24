# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test (Python 2.7 and 3) of the #ASTER-SECTIE lines that
# MecwaySectionProps (github.com/trednuK/MecwaySectionProps) writes:
# bridge_custom reads them, bridge_from_liml._section_extras and
# _apply_section_extras add them to a general beam section.
#
#   python tests/test_bridge_section_extras.py

from __future__ import print_function

import os
import sys
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "en"
import bridge_custom  # noqa: E402
import bridge_from_liml  # noqa: E402

LOG = []
bridge_custom.log = LOG.append
bridge_from_liml.log = LOG.append


def check(name, cond):
    print(("OK   " if cond else "FOUT ") + name)
    if not cond:
        check.failed = True


check.failed = False

# A line as MecwaySectionProps writes it (section_mecway.aster_line there).
LINE = (u"** ASTER-SECTIE Plat 3x6: A=1.8e-05, IY=1.35e-09, IZ=5.4e-13, "
        u"JX=2.16e-12, AY=1.2, AZ=1.2, EY=0, EZ=0, RY=0.003, RZ=0.0015, "
        u"RT=0.0015, JG=1e-18, IYR2=0, IZR2=0")

custom = bridge_custom.parse([u"** own line\n" + LINE])
extras = bridge_from_liml._section_extras(custom["sections"])
check("bridge reads the line", extras.get(u"Plat 3x6", {}).get("AY") == 1.2
      and extras[u"Plat 3x6"]["IY"] == 1.35e-09)

geom = bridge_from_liml._parse_geometric_props(ET.fromstring(
    (u'<geometric type="UniformGeneralSection" area="1.8e-05 m\xb2" '
     u'iyy="1.35e-09 m⁴" izz="5.4e-13 m⁴" '
     u'torsionconstant="2.16e-12 m⁴" />').encode("utf-8")))
new_geom = bridge_from_liml._apply_section_extras(u"Plat 3x6", geom,
                                                  extras[u"Plat 3x6"])
cara = dict(zip(new_geom["cara"], new_geom["vale"]))
check("EY, EZ, RY, RZ, RT added; AY/AZ as shear_coefs",
      all(k in cara for k in ("EY", "EZ", "RY", "RZ", "RT")) and
      new_geom.get("shear_coefs") == (1.2, 1.2))
changed = dict(extras[u"Plat 3x6"], IY=2e-9)
same = bridge_from_liml._apply_section_extras(u"Plat 3x6", geom, changed)
check("changed section -> extras ignored (WARNING)",
      same is geom and any("WARNING" in m for m in LOG))
bad = bridge_from_liml._section_extras([u"X: A=1, IY=1, IZ=1, JX=1, Q=2",
                                        u"no colon"])
check("unknown key and missing name -> skipped (ERROR)", bad == {} and
      sum(1 for m in LOG if m.startswith("ERROR")) >= 2)

# Mecway keeps an imported custom model definition next to an existing one;
# every one is read in file order and the later line of a material wins.
TWO = (u'<liml version="34"><ccxmodeldefinition>** own line\n'
       u'** ASTER-SECTIE M: A=1, IY=1, IZ=1, JX=1, AY=1.1</ccxmodeldefinition>'
       u'<ccxmodeldefinition>** ASTER-SECTIE M: A=1, IY=1, IZ=1, JX=1, '
       u'AY=1.3</ccxmodeldefinition></liml>')
root = ET.fromstring(TWO.encode("utf-8"))
texts = [el.text for tag in bridge_custom.CUSTOM_TAGS
         for el in root.findall(tag)]
extras = bridge_from_liml._section_extras(
    bridge_custom.parse(texts)["sections"])
check("two custom model definitions: both read, the later line wins",
      len(texts) == 2 and extras["M"]["AY"] == 1.3)

if check.failed:
    print("FOUT: test_bridge_section_extras")
    sys.exit(1)
print("Alle controles OK")
