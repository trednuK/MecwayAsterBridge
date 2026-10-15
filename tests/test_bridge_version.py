# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test van de versiecontrole (bridge_version.py), Python 2.7 en 3,
# zonder Mecway en Code-Aster:
#   - Mecway-versie uit door Mecway opgeslagen .liml-bestanden (33 en 34) en
#     uit vreemde invoer (geen root, leeg attribuut, binair, ontbrekend);
#   - Code-Aster-versie uit de kop van een .mess (fragment van Code-Aster
#     17.4 voor Windows, zonder machinenaam) en uit het launcherpad;
#   - WARNING bij een niet-geteste versie, INFO bij onbekend.
#
#   python tests/test_bridge_version.py

from __future__ import print_function

import io
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
_REPO = os.path.join(_HERE, "..")
sys.path.insert(0, os.path.join(_REPO, "Scripts"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "nl"

LOG = []


def _log(msg):
    LOG.append(msg)


bridge_utils.log = _log
import bridge_version as bv  # noqa: E402
bv.log = _log

FAILS = []


def check(cond, text):
    if not cond:
        FAILS.append(text)


# Kop van een .mess van Code-Aster 17.4 voor Windows (machinenaam en paden
# weggelaten). De regels "Version de Python" en "Créée avec la version"
# mogen niet als Code-Aster-versie tellen.
MESS_17_4 = u"""<INFO> Démarrage de l'exécution.

                  -- CODE_ASTER -- VERSION : DÉVELOPPEMENT STABILISÉE (testing) --
                               Version 17.4.0 modifiée le 22/01/2026
                          révision 03b95c288047 - branche 'windows-draft'
                                   Copyright EDF R&D 1991 - 2026
                                     Version de Python : 3.11.9
                                     Version de NumPy : 1.26.4
     Créée avec la version                   :
17.04.00
"""


def _warnings():
    return [m for m in LOG if m.startswith("WARNING:")]


def _infos():
    return [m for m in LOG if m.startswith("INFO:")]


def test_liml_files():
    # Door Mecway opgeslagen testmodellen
    for rel, want in ((("TestFiles", "Voorbeelden", "Voorbeeld_A.liml"), "33"),
                      (("TestFiles", "TieContact_Plates.liml"), "34")):
        path = os.path.join(_REPO, *rel)
        got = bv.mecway_version_from_liml(path)
        check(got == want, "{0}: {1!r} != {2!r}".format(rel[-1], got, want))
        del LOG[:]
        version, note = bv.check_mecway(path)
        check(version == want and note is None and not _warnings(),
              "{0}: geteste versie gaf een WARNING".format(rel[-1]))


def test_liml_text():
    cases = [
        (u'<?xml version="1.0"?>\n<liml version="34">', "34"),
        (u"<liml version='35' >", "35"),
        (u'<liml  other="1"  version = "33.1">', "33.1"),
        (u'<liml subversion="9">', None),
        (u'<liml version="">', None),
        (u"<liml>", None),
        (u'<other version="33"/>', None),
        (u"", None),
        (None, None),
        (u"\x00\xff garbage", None),
    ]
    for text, want in cases:
        got = bv.mecway_version_from_text(text)
        check(got == want, "liml-tekst {0!r}: {1!r} != {2!r}".format(
            text, got, want))
    check(bv.mecway_version_from_liml(os.path.join(_REPO, "bestaat_niet.liml"))
          is None, "ontbrekend bestand gaf geen None")


def test_mecway_check(tmp):
    def write(name, text):
        path = os.path.join(tmp, name)
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    del LOG[:]
    version, note = bv.check_mecway(write("v35.liml",
                                          u'<liml version="35">\n</liml>'))
    check(version == "35" and note and len(_warnings()) == 1
          and "35" in _warnings()[0],
          "version 35 gaf geen WARNING: {0}".format(LOG))
    del LOG[:]
    version, note = bv.check_mecway(write("geen.liml", u"<liml>\n</liml>"))
    check(version is None and note is None and not _warnings()
          and len(_infos()) == 1, "zonder version: alleen INFO verwacht")
    del LOG[:]
    version, note = bv.check_mecway(write("raar.liml",
                                          u'<liml version="nieuw">'))
    check(note is None and not _warnings(), "niet-numeriek: geen WARNING")
    # Engels: zelfde voorvoegsel
    bridge_utils.CONFIG_BRIDGE["language"] = "en"
    del LOG[:]
    bv.check_mecway(os.path.join(tmp, "v35.liml"))
    check(_warnings() and "not been tested" in _warnings()[0],
          "Engelse WARNING ontbreekt")
    bridge_utils.CONFIG_BRIDGE["language"] = "nl"


def test_mess(tmp):
    check(bv.aster_version_from_mess_text(MESS_17_4) == "17.4.0",
          "mess-kop: {0!r}".format(bv.aster_version_from_mess_text(MESS_17_4)))
    check(bv.aster_version_from_mess_text(
        u"Version de Python : 3.11.9\n") is None, "Python-versie geteld")
    check(bv.aster_version_from_mess_text(u"") is None, "lege mess")
    check(bv.aster_version_from_mess_text(None) is None, "None-mess")
    path = os.path.join(tmp, "x.mess")
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(MESS_17_4)
    check(bv.aster_version_from_mess(path) == "17.4.0", "mess-bestand")
    path = os.path.join(tmp, "bin.mess")
    with open(path, "wb") as f:
        f.write(b"\xff\xfe\x00\x81\n   Version 18.0.1 x\n")
    check(bv.aster_version_from_mess(path) == "18.0.1", "binaire mess")
    check(bv.aster_version_from_mess(os.path.join(tmp, "nee.mess")) is None,
          "ontbrekende mess")


def test_launcher():
    cases = [
        (r"C:\Users\x\AppData\Local\code_aster\v2025\17.4\bin\run_aster.bat",
         "17.4"),
        (r"%LOCALAPPDATA%\code_aster\v2025\18.0\bin\run_aster.bat", "18.0"),
        ("D:/code_aster/17.4.2/bin/run_aster.bat", "17.4.2"),
        (r"C:\eigen\build\bin\run_aster.bat", None),
        (r"C:\run_aster.bat", None),
        ("", None),
        (None, None),
    ]
    for path, want in cases:
        got = bv.aster_version_from_launcher(path)
        check(got == want, "launcher {0!r}: {1!r} != {2!r}".format(
            path, got, want))


def test_aster_check():
    check(bv.major_minor("17.04.00") == "17.4", "17.04.00")
    check(bv.major_minor("17.4.0") == "17.4", "17.4.0")
    check(bv.major_minor("x") is None, "geen versie")
    for version, warn in (("17.4.0", False), ("17.4", False),
                          ("17.04.00", False), ("18.0.1", True),
                          ("17.3", True)):
        del LOG[:]
        note = bv.check_aster(version, ".mess")
        check(bool(note) == warn and len(_warnings()) == int(warn),
              "check_aster {0}: {1}".format(version, LOG))
    for version in (None, "", "onbekend"):
        del LOG[:]
        note = bv.check_aster(version, "launcher-pad")
        check(note is None and not _warnings() and len(_infos()) == 1,
              "check_aster onbekend {0!r}: {1}".format(version, LOG))


def main():
    tmp = tempfile.mkdtemp(prefix="mab_versie_")
    try:
        test_liml_files()
        test_liml_text()
        test_mecway_check(tmp)
        test_mess(tmp)
        test_launcher()
        test_aster_check()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if FAILS:
        for f in FAILS:
            print("FOUT: " + f)
        sys.exit(1)
    print("OK: versiecontrole (bridge_version)")


if __name__ == "__main__":
    main()
