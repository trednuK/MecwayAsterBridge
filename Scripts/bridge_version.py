# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_version.py
# Versiecontrole van Mecway en Code-Aster: alleen een waarschuwing, de run
# gaat altijd door. Compatibel met IronPython 2.7.9 en Python 3 (offline
# test: python tests/test_bridge_version.py).
#
#   Mecway     : attribuut version van de <liml>-root (Mecway 33 schrijft
#                version="33", Mecway 34 version="34"; gezien in de
#                testmodellen in TestFiles).
#   Code-Aster : voor de run uit het pad van de launcher
#                (...\<versie>\bin\run_aster.bat, de map van het Windows-
#                pakket); na de run uit de kop van de .mess, de regel
#                "Version 17.4.0 modifiée le 22/01/2026" (gezien in de
#                .mess van Code-Aster 17.4 voor Windows; de kop is Frans,
#                ook als de meldingen in een andere taal zijn).
#   Getest     : TESTED_MECWAY_VERSIONS en TESTED_ASTER_VERSIONS in
#                bridge_utils.py (buiten CONFIG_BRIDGE).
#
# Elke functie vangt zelf fouten af: een vreemd bestand of pad geeft None
# (onbekende versie, INFO in de log), nooit een exceptie.

import re

from bridge_utils import (log, tr, TESTED_MECWAY_VERSIONS,
                          TESTED_ASTER_VERSIONS)

# Alleen het begin van een bestand lezen: de <liml>-root staat bovenaan,
# de versie van Code-Aster in de kop van de .mess.
_LIML_HEAD_BYTES = 8192
_MESS_HEAD_BYTES = 65536

_LIML_ROOT_RE = re.compile(r"<liml\b([^>]*)>")
_VERSION_ATTR_RE = re.compile(
    r"(?:^|\s)version\s*=\s*(?:\"([^\"]*)\"|'([^']*)')")
# "Version 17.4.0 modifiée le ..." (niet "Version de Python : 3.11.9" en
# niet "Créée avec la version : 17.04.00": daar volgt geen getal direct
# op het woord Version).
_MESS_VERSION_RE = re.compile(
    r"^[ \t]*Version[ \t]+(\d+\.\d+(?:\.\d+)*)\b", re.M)
_DOTTED_RE = re.compile(r"^\d+\.\d+(?:\.\d+)*$")


def _read_head(path, nbytes):
    """Begin van een bestand als tekst (UTF-8, onleesbare tekens
    vervangen), of None als het niet te lezen is."""
    try:
        f = open(path, "rb")
        try:
            data = f.read(nbytes)
        finally:
            f.close()
        return data.decode("utf-8", "replace")
    except Exception:
        return None


def mecway_version_from_text(text):
    """Waarde van version in de <liml>-root, of None (geen root, geen of
    leeg attribuut)."""
    try:
        m = _LIML_ROOT_RE.search(text or u"")
        if not m:
            return None
        a = _VERSION_ATTR_RE.search(m.group(1))
        if not a:
            return None
        value = (a.group(1) if a.group(1) is not None
                 else a.group(2)).strip()
        return value or None
    except Exception:
        return None


def mecway_version_from_liml(path):
    """Mecway-versie die de .liml het laatst opsloeg, of None."""
    return mecway_version_from_text(_read_head(path, _LIML_HEAD_BYTES))


def aster_version_from_mess_text(text):
    """Code-Aster-versie uit de kop van een .mess ('17.4.0'), of None."""
    try:
        m = _MESS_VERSION_RE.search(text or u"")
        return m.group(1) if m else None
    except Exception:
        return None


def aster_version_from_mess(path):
    """Code-Aster-versie die de .mess schreef, of None."""
    return aster_version_from_mess_text(_read_head(path, _MESS_HEAD_BYTES))


def aster_version_from_launcher(path):
    """
    Code-Aster-versie uit het launcherpad, of None. Alleen de map direct
    boven 'bin' telt (Windows-pakket: ...\\v2025\\17.4\\bin\\run_aster.bat);
    een ander pad (eigen build, snelkoppeling) geeft None, geen gok.
    """
    try:
        parts = [p for p in re.split(r"[\\/]+", path or u"") if p]
        for i in range(len(parts) - 1, 0, -1):
            if parts[i].lower() == "bin":
                cand = parts[i - 1].strip()
                return cand if _DOTTED_RE.match(cand) else None
        return None
    except Exception:
        return None


def major_minor(version):
    """'17.4.0' -> '17.4', '17.04.00' -> '17.4'; None als het geen
    versienummer is."""
    try:
        m = re.match(r"\s*(\d+)\.(\d+)", version or u"")
        if not m:
            return None
        return "{0}.{1}".format(int(m.group(1)), int(m.group(2)))
    except Exception:
        return None


def mecway_tested(version):
    """True/False voor een bekende versie (vergelijkt het hoofdnummer:
    '34' en '34.0' zijn beide 34), None als het geen getal is."""
    try:
        m = re.match(r"\s*(\d+)", version or u"")
        if not m:
            return None
        major = str(int(m.group(1)))
        return major in [str(v).strip() for v in TESTED_MECWAY_VERSIONS]
    except Exception:
        return None


def aster_tested(version):
    """True/False (major.minor in TESTED_ASTER_VERSIONS), None als
    onbekend."""
    mm = major_minor(version)
    if mm is None:
        return None
    return mm in [major_minor(v) for v in TESTED_ASTER_VERSIONS]


def check_mecway(liml_path):
    """
    Logt de Mecway-versie van de opgeslagen .liml (INFO) en een WARNING als
    die niet getest is. Returns (versie of None, melding voor de gebruiker
    of None).
    """
    version = mecway_version_from_liml(liml_path)
    if version is None:
        log(u"INFO: Mecway-versie onbekend (geen attribuut version in "
            "<liml>); geen versiecontrole.")
        return None, None
    tested = mecway_tested(version)
    if tested is None:
        log(u"INFO: Mecway-versie '{0}' is geen versienummer; geen "
            "versiecontrole.".format(version))
        return version, None
    if tested:
        log(u"INFO: Mecway-versie {0} (getest).".format(version))
        return version, None
    note = tr(u"Mecway {0} is niet getest met deze bridge (getest: {1}). "
              u"De run gaat door; controleer de resultaten. Zie "
              u"'Na een update van Mecway of Code-Aster' (Documentatie).",
              u"Mecway {0} has not been tested with this bridge (tested: "
              u"{1}). The run continues; check the results. See 'After an "
              u"update of Mecway or Code-Aster' (Documentation).").format(
                  version, u", ".join(TESTED_MECWAY_VERSIONS))
    log(u"WARNING: " + note)
    return version, note


def check_aster(version, source):
    """
    Logt de Code-Aster-versie (source: 'launcher-pad' of '.mess') en een
    WARNING als major.minor niet getest is. Returns de melding voor de
    gebruiker of None.
    """
    tested = aster_tested(version)
    if tested is None:
        log(u"INFO: Code-Aster-versie niet te bepalen uit {0}; geen "
            "versiecontrole.".format(source))
        return None
    if tested:
        log(u"INFO: Code-Aster-versie {0} volgens {1} (getest).".format(
            version, source))
        return None
    note = tr(u"Code-Aster {0} is niet getest met deze bridge (getest: {1}). "
              u"De run gaat door; controleer de resultaten en meldingen. "
              u"Zie 'Na een update van Mecway of Code-Aster' "
              u"(Documentatie).",
              u"Code-Aster {0} has not been tested with this bridge "
              u"(tested: {1}). The run continues; check the results and "
              u"messages. See 'After an update of Mecway or Code-Aster' "
              u"(Documentation).").format(
                  version, u", ".join(TESTED_ASTER_VERSIONS))
    log(u"WARNING: " + note)
    return note
