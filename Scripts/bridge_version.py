# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_version.py
# Version check of Mecway and Code-Aster: only a warning, the run always
# continues. Compatible with IronPython 2.7.9 and Python 3 (offline
# test: python tests/test_bridge_version.py).
#
#   Mecway     : attribute version of the <liml> root (Mecway 33 writes
#                version="33", Mecway 34 version="34"; seen in the
#                test models in TestFiles).
#   Code-Aster : before the run from the path of the launcher
#                (...\<version>\bin\run_aster.bat, the Windows package
#                folder); after the run from the .mess header, the line
#                "Version 17.4.0 modifiée le 22/01/2026" (seen in the
#                .mess of Code-Aster 17.4 for Windows; the header is French,
#                even when the messages are in another language).
#   Tested     : TESTED_MECWAY_VERSIONS and TESTED_ASTER_VERSIONS in
#                bridge_utils.py (outside CONFIG_BRIDGE).
#
# Every function catches its own errors: an odd file or path gives None
# (unknown version, INFO in the log), never an exception.

import re

from bridge_utils import (log, tr, TESTED_MECWAY_VERSIONS,
                          TESTED_ASTER_VERSIONS)

# Only read the start of a file: the <liml> root is at the top,
# the Code-Aster version in the header of the .mess.
_LIML_HEAD_BYTES = 8192
_MESS_HEAD_BYTES = 65536

_LIML_ROOT_RE = re.compile(r"<liml\b([^>]*)>")
_VERSION_ATTR_RE = re.compile(
    r"(?:^|\s)version\s*=\s*(?:\"([^\"]*)\"|'([^']*)')")
# "Version 17.4.0 modifiée le ..." (not "Version de Python : 3.11.9" and
# not "Créée avec la version : 17.04.00": there no number directly
# follows the word Version).
_MESS_VERSION_RE = re.compile(
    r"^[ \t]*Version[ \t]+(\d+\.\d+(?:\.\d+)*)\b", re.M)
_DOTTED_RE = re.compile(r"^\d+\.\d+(?:\.\d+)*$")


def _read_head(path, nbytes):
    """Start of a file as text (UTF-8, unreadable characters
    replaced), or None if it cannot be read."""
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
    """Value of version in the <liml> root, or None (no root, missing or
    empty attribute)."""
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
    """Mecway version that last saved the .liml, or None."""
    return mecway_version_from_text(_read_head(path, _LIML_HEAD_BYTES))


def aster_version_from_mess_text(text):
    """Code-Aster version from the header of a .mess ('17.4.0'), or None."""
    try:
        m = _MESS_VERSION_RE.search(text or u"")
        return m.group(1) if m else None
    except Exception:
        return None


def aster_version_from_mess(path):
    """Code-Aster version that wrote the .mess, or None."""
    return aster_version_from_mess_text(_read_head(path, _MESS_HEAD_BYTES))


def aster_version_from_launcher(path):
    """
    Code-Aster version from the launcher path, or None. Only the folder
    directly above 'bin' counts (Windows package:
    ...\\v2025\\17.4\\bin\\run_aster.bat); another path (own build,
    shortcut) gives None, no guess.
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
    """'17.4.0' -> '17.4', '17.04.00' -> '17.4'; None if it is not a
    version number."""
    try:
        m = re.match(r"\s*(\d+)\.(\d+)", version or u"")
        if not m:
            return None
        return "{0}.{1}".format(int(m.group(1)), int(m.group(2)))
    except Exception:
        return None


def mecway_tested(version):
    """True/False for a known version (compares the major number:
    '34' and '34.0' are both 34), None if it is not a number."""
    try:
        m = re.match(r"\s*(\d+)", version or u"")
        if not m:
            return None
        major = str(int(m.group(1)))
        return major in [str(v).strip() for v in TESTED_MECWAY_VERSIONS]
    except Exception:
        return None


def aster_tested(version):
    """True/False (major.minor in TESTED_ASTER_VERSIONS), None if
    unknown."""
    mm = major_minor(version)
    if mm is None:
        return None
    return mm in [major_minor(v) for v in TESTED_ASTER_VERSIONS]


def check_mecway(liml_path):
    """
    Logs the Mecway version of the saved .liml (INFO) and a WARNING if
    it is not tested. Returns (version or None, message for the user
    or None).
    """
    version = mecway_version_from_liml(liml_path)
    if version is None:
        log(u"INFO: Mecway version unknown (no attribute version in "
            "<liml>); no version check.")
        return None, None
    tested = mecway_tested(version)
    if tested is None:
        log(u"INFO: Mecway version '{0}' is not a version number; no "
            "version check.".format(version))
        return version, None
    if tested:
        log(u"INFO: Mecway version {0} (tested).".format(version))
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
    Logs the Code-Aster version (source: 'launcher-pad' or '.mess') and a
    WARNING if major.minor is not tested. Returns the message for the
    user or None.
    """
    tested = aster_tested(version)
    if tested is None:
        log(u"INFO: Code-Aster version cannot be determined from {0}; no "
            "version check.".format(source))
        return None
    if tested:
        log(u"INFO: Code-Aster version {0} according to {1} (tested).".format(
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
