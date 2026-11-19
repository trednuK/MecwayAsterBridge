# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_liml_text.py
# The open model as .liml text through mw.liml_text() (Mecway 36 and later),
# so that the bridge can read the model without saving the user's file.
# Compatible with IronPython 2.7.9 and Python 3 (no mw import: mw is passed
# in; test: python tests/test_bridge_liml_text.py, also under run_ipy.ps1).
#
# mw.liml_text(solution=True) returns what saving as .liml would write,
# with LF line endings (Mecway's scripting documentation). Measured in a
# hidden Mecway 36.0.9815 (script mode, 18 Nov 2026): equal to the bytes of
# mw.save_as after CRLF -> LF, no XML declaration and no BOM (save_as
# writes none either), non-ASCII text (kg/m3 with a superscript) correct;
# liml_text(False) is the same text without the <solution> block; the call
# does not change file_name() or the model, and shows unsaved edits made in
# memory; 0.09 s for a 1 MB model.
#
# Feature detection (AGENTS.md, Mecway versions): hasattr(mw, "liml_text").
# Without it, or when the call fails, every function returns None and the
# caller saves the model as before (Mecway 33-35).
#
# Users: MecwayAsterBridgeMain (a run: the snapshot is the model the run
# reads, also model_data["liml_path"] for the job; route 'liml' saves the
# user's file only right before the results go into it; Show section: a
# temporary snapshot). The decisions of a run are the pure functions
# saved_path, wants_snapshot, save_problem, same_text and clean_end.

import os
import tempfile

from bridge_utils import log, tr

# '<solution' as an element: followed by one of these (the rule of
# bridge_from_liml._model_bytes).
_SOLUTION = u"<solution"
_FOLLOW = u">/ \t\r\n"


def available(mw):
    """True if this Mecway has mw.liml_text() (Mecway 36 and later)."""
    try:
        return hasattr(mw, "liml_text")
    except Exception:
        return False


def saved_path(file_name):
    """
    The path of the open model (mw.file_name()), or None for a model that
    was never saved: empty, None, or a bare name without a folder (the rule
    of bridge_utils.set_model_path).
    """
    if not file_name or not os.path.dirname(u"{0}".format(file_name)):
        return None
    return file_name


def wants_snapshot(has_api, route, file_name):
    """
    True if a run reads a model-only copy instead of saving the user's
    file first: with mw.liml_text() (has_api), route 'tabel' always (it
    writes into Mecway's own solution, never into the file; also an
    untitled model) and route 'liml' for a saved model (it saves only
    right before the results go into the file). Otherwise the model is
    saved first, as before.
    """
    if not has_api:
        return False
    if route == "tabel":
        return True
    return route == "liml" and saved_path(file_name) is not None


def save_problem(path):
    """
    Why mw.save() would fail for path, checked without saving (route
    'liml' with a snapshot saves at the end of the run, so this keeps
    the stop before Code-Aster): "folder" (the folder no longer exists),
    "readonly" (the file is read-only), or None.
    """
    folder = os.path.dirname(path or "")
    if folder and not os.path.isdir(folder):
        return "folder"
    if path and os.path.exists(path) and not os.access(path, os.W_OK):
        return "readonly"
    return None


def same_text(model, snapshot_path):
    """
    True if model (model_text of the open model, LF) equals the snapshot
    file (CRLF, write_snapshot): the model did not change during the run.
    False when it differs or the file cannot be read; None when model is
    None (no text to compare).
    """
    if model is None:
        return None
    try:
        f = open(snapshot_path, "rb")
        try:
            data = f.read()
        finally:
            f.close()
        return data.decode("utf-8").replace(u"\r\n", u"\n") == model
    except Exception:
        return False


def clean_end(state, exit_code, mess_errors, mess_done):
    """
    True if the Code-Aster job ran to its end without errors, so that the
    snapshot (the .comm's liml_path) may be removed: state "finished", or
    "confirmed" (wait_for_aster confirm) with a finished .mess (mess_done),
    exit code 0 and no errors in the .mess. Otherwise the snapshot stays
    for a run of the .export by hand (docs: Code-Aster error messages).
    """
    if exit_code or mess_errors:
        return False
    if state == "finished":
        return True
    return state == "confirmed" and bool(mess_done)


def _solution_start(text):
    """Index of the first <solution element in text, or None."""
    start = 0
    while True:
        i = text.find(_SOLUTION, start)
        if i < 0 or i + len(_SOLUTION) >= len(text):
            return None
        if text[i + len(_SOLUTION)] in _FOLLOW:
            return i
        start = i + 1


def model_text(mw):
    """
    The model of the open Mecway file as .liml text without results
    (mw.liml_text(False)), with LF line endings; None without the API or
    when it fails (WARNING in the log). A <solution> block, which
    liml_text(False) does not write, is cut off as bridge_from_liml does.
    """
    if not available(mw):
        return None
    try:
        text = mw.liml_text(False)
    except Exception as e:
        log(tr(u"WARNING: mw.liml_text() mislukt ({0}); de bridge slaat "
               u"het model op zoals eerder.",
               u"WARNING: mw.liml_text() failed ({0}); the bridge saves "
               u"the model as before.").format(e))
        return None
    if text is None:
        text = u""
    if not isinstance(text, type(u"")):
        try:
            text = text.decode("utf-8")
        except Exception:
            text = u"{0}".format(text)
    if not text.lstrip(u"\ufeff \t\r\n").startswith(u"<liml"):
        log(tr(u"WARNING: mw.liml_text() gaf geen .liml-tekst; de bridge "
               u"slaat het model op zoals eerder.",
               u"WARNING: mw.liml_text() returned no .liml text; the bridge "
               u"saves the model as before."))
        return None
    text = text.replace(u"\r\n", u"\n")
    cut = _solution_start(text)
    if cut is not None:
        text = text[:cut] + u"</liml>"
    return text


def write_snapshot(mw, path):
    """
    Write the model text (model_text) to path as Mecway saves a .liml:
    CRLF line endings, UTF-8 without BOM or declaration. Returns path, or
    None without the API or when writing fails (WARNING in the log; a
    partial file is removed).
    """
    text = model_text(mw)
    if text is None:
        return None
    try:
        data = text.replace(u"\n", u"\r\n").encode("utf-8")
        f = open(path, "wb")
        try:
            f.write(data)
        finally:
            f.close()
        return path
    except Exception as e:
        remove(path)
        log(tr(u"WARNING: Kopie van het model niet geschreven ({0}): {1}; "
               u"de bridge slaat het model op zoals eerder.",
               u"WARNING: Copy of the model not written ({0}): {1}; the "
               u"bridge saves the model as before.").format(path, e))
        return None


def temp_snapshot(mw):
    """
    write_snapshot into a new temporary file (%TEMP%); returns its path or
    None (no API, or it failed: nothing left behind). The caller removes it
    with remove() in a finally.
    """
    if not available(mw):
        return None
    try:
        handle, path = tempfile.mkstemp(prefix="mab_model_", suffix=".liml")
        os.close(handle)
    except Exception as e:
        log(tr(u"WARNING: Tijdelijk bestand niet gemaakt: {0}; de bridge "
               u"slaat het model op zoals eerder.",
               u"WARNING: Temporary file not made: {0}; the bridge saves "
               u"the model as before.").format(e))
        return None
    if write_snapshot(mw, path) is None:
        remove(path)
        return None
    return path


def remove(path):
    """Remove path if it exists (no error when it does not)."""
    if not path:
        return
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        log(u"INFO: Temporary model copy {0} not removed: {1}".format(
            path, e))
