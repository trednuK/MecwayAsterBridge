# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_hide_failed.py
# Setting hide_failed: after the results are in the .liml, hide the failed
# elements in Mecway's own result view with the core liml_failed.py (copy
# of AdvancedToolsHub's common/liml_failed.py, contract failed/1 in
# AGENTS.md). The core gives every failed element private node copies in
# the <solution> mesh and collapses them on the element's centroid from
# the step where the element variable "failed" becomes 1; the model part
# of the file stays byte for byte.
#
# Python 2.7 (IronPython 2.7.9) and 3, stdlib only, no mw: the caller
# (MecwayAsterBridgeMain._hide_failed) passes mw.open as open_fn to
# hide_and_open, which processes the file and opens it.
# Files:
#   <liml>.hide.tmp      written by the core; becomes <liml> on success
#   <liml>.unhidden.tmp  the unprocessed <liml>, kept until Mecway opened
#                        the processed file (finish), or put back when
#                        that fails (restore)
# The .bak of the splice (bridge_results_liml) is not touched.
#
# Test: python tests/test_bridge_hide_failed.py

import os
import re
import time
from xml.sax.saxutils import escape as _xml_escape

from bridge_utils import CONFIG_BRIDGE, log, tr
import liml_failed

TMP_SUFFIX = ".hide.tmp"
KEEP_SUFFIX = ".unhidden.tmp"
# Refusals that only mean "nothing to hide here": no message.
SILENT_CODES = ("no_timesteps", "modal_result", "no_flag_source")


def _core_text(pair):
    """The core's (en, nl) text in the language of the bridge."""
    return tr(pair[1], pair[0])


def _remove(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def _progress():
    """Progress callback of the core: an INFO line per 25 %."""
    state = {"next": 0.25}

    def progress(fraction, phase):
        if fraction >= state["next"] and fraction < 1.0:
            log("INFO: Hiding failed elements: {0} % ({1}).".format(
                int(100 * fraction), phase))
            while state["next"] <= fraction:
                state["next"] += 0.25
    return progress


def _warning(nl, en, *args):
    """Log a WARNING and return ("warning", text without the prefix)."""
    text = tr(nl, en).format(*args)
    log(u"WARNING: " + text)
    return "warning", text


def _not_hidden(reason):
    return _warning(u"Bezweken elementen niet verborgen: {0} Het model is "
                    u"ongewijzigd.",
                    u"Failed elements not hidden: {0} The model is "
                    u"unchanged.", reason)


def _missing(liml):
    """WARNING text: liml is gone, the unprocessed file is liml +
    KEEP_SUFFIX."""
    return _warning(u"Bezweken elementen niet verborgen en het model {0} "
                    u"ontbreekt: de resultaten zonder verbergen staan in "
                    u"{1}. Hernoem dat bestand naar {0}.",
                    u"Failed elements not hidden and the model {0} is "
                    u"missing: the results without hiding are in {1}. "
                    u"Rename that file to {0}.", liml, liml + KEEP_SUFFIX)[1]


_ELEM = re.compile(br'<elem\s+eid="(\d+)"[^>]*?\snodes="([^"]*)"')
_NID = re.compile(br'<node\s+nid="(\d+)"')


def _model_max_eid(liml):
    """The highest element number of the model part (before the first
    <solution>); 0 without elements."""
    top = 0
    with open(liml, "rb") as f:
        for raw in f:
            s = raw.lstrip()
            if s.startswith(b"<solution"):
                break
            m = _ELEM.match(s)
            if m:
                top = max(top, int(m.group(1)))
    return top


def apply(liml, configuration=None, expected=None, state=None):
    """
    Hide the failed elements in liml (the .liml with the results of this
    bridge). configuration: name of the configuration whose solution to
    process (bridge_results_liml.pick_configuration), None for a model
    without configurations. expected: the element numbers (text) that
    failed in the run (bridge_failure.failed_elements), or None (Results...
    > Load: no .mess of a run); those that are not hidden give a note.
    state: a dict or None; "renamed" is True while liml is no longer the
    unprocessed file (that one is liml + KEEP_SUFFIX), so that a caller
    that gets an exception knows whether to restore().

    Returns (status, text):
      ("skip", text)      nothing hidden (static, modal, no variable
                          'failed', nothing failed); the file is unchanged;
                          text "" or the note on elements that stay visible;
      ("done", text)      liml is the processed file and the unprocessed
                          one is liml + KEEP_SUFFIX: the caller opens liml
                          and then calls finish(liml), or restore(liml)
                          when Mecway does not open it;
      ("warning", text)   refused or failed (WARNING logged); the file is
                          unchanged (or, when liml is missing, the text
                          names the file to rename back).
    """
    state = {} if state is None else state
    state["renamed"] = False
    tmp = liml + TMP_SUFFIX
    keep = liml + KEEP_SUFFIX
    _remove(tmp)
    if not os.path.isfile(liml):
        if os.path.isfile(keep):
            return "warning", _missing(liml)
        return _not_hidden(tr(u"bestand niet gevonden ({0}).",
                              u"file not found ({0}).").format(liml))
    try:
        processed = is_processed(liml, configuration)
        marker = (liml_failed.processed_marker(liml, configuration)
                  if processed else None)
    except (IOError, OSError) as e:
        return _not_hidden(u"{0}".format(e))
    if processed:
        return _warning(u"De resultaten in {0} hebben de bezweken elementen "
                        u"al verborgen ({1}); niet opnieuw bewerkt. "
                        u"Resultaten... > Inladen geeft de oorspronkelijke "
                        u"resultaten terug.",
                        u"The results in {0} already have the failed "
                        u"elements hidden ({1}); not processed "
                        u"again. Results... > Load gives back the original "
                        u"results.", os.path.basename(liml),
                        tr(u"versie {0}", u"version {0}").format(marker)
                        if marker else
                        tr(u"kenmerk verloren, bijvoorbeeld door opslaan in "
                           u"Mecway", u"marker lost, for example by a save "
                           u"in Mecway"))
    t0 = time.time()
    try:
        rep = liml_failed.process(liml, tmp, solver="aster", others="zero",
                                  configuration=configuration,
                                  progress=_progress())
    except liml_failed.LimlFailedError as e:
        _remove(tmp)
        if e.code in SILENT_CODES:
            log(u"INFO: Hide failed elements: not applied ({0}: {1})".format(
                e.code, e.text[0]))
            return "skip", u""
        return _not_hidden(_core_text(e.text))
    except Exception as e:
        _remove(tmp)
        return _not_hidden(u"{0}".format(e))
    seconds = time.time() - t0
    # Only model elements count: the shells of a section view
    # (bridge_section_view.build_view) are numbered above every element of
    # the model and copy the 'failed' of their beam, so they are hidden
    # with it.
    failed = rep.get("failed", {})
    top = _model_max_eid(liml) if failed else 0
    hidden = set(e for e in failed if e <= top)
    shells = len(failed) - len(hidden)
    stay = sorted(set(expected) - set(u"{0}".format(e) for e in hidden),
                  key=lambda x: (len(x), x)) if expected else []
    stay_note = u""
    if stay:
        log(u"INFO: {0} failed element(s) of the run stay visible: they "
            u"failed at the last stored step (failed is 1 only from the "
            u"step after the failure) or the results do not mark them: "
            u"{1}".format(len(stay), u", ".join(stay[:20]) +
                          (u", ..." if len(stay) > 20 else u"")))
        stay_note = tr(u"{0} bezweken element(en) van de run blijven "
                       u"zichtbaar: ze bezweken bij de laatste opgeslagen "
                       u"stap, of de resultaten markeren ze niet (zie het "
                       u"log).",
                       u"{0} failed element(s) of the run stay visible: "
                       u"they failed at the last stored step, or the results "
                       u"do not mark them (see the log).").format(len(stay))
    if not rep.get("written"):
        _remove(tmp)
        log("INFO: Hide failed elements: no failed element in the results "
            "({0:.1f} s).".format(seconds))
        return "skip", stay_note
    if os.path.exists(keep):
        # Left by an earlier session; liml has just been written by the
        # splice and is not processed, so the old file is not the current
        # model.
        log(tr(u"WARNING: Een eerder achtergebleven {0} is verwijderd: het "
               u"hoort niet bij de resultaten die nu in het model staan.",
               u"WARNING: An earlier {0} that was left behind has been "
               u"removed: it does not belong to the results now in the "
               u"model.").format(keep))
        _remove(keep)
    try:
        os.rename(liml, keep)
    except OSError as e:
        _remove(tmp)
        return _not_hidden(u"{0}".format(e))
    state["renamed"] = True
    try:
        os.rename(tmp, liml)
    except OSError as e:
        try:
            os.rename(keep, liml)
            state["renamed"] = False
        except OSError:
            pass
        if not os.path.isfile(liml):
            return "warning", _missing(liml)
        _remove(tmp)
        return _not_hidden(u"{0}".format(e))
    log(u"INFO: Hide failed elements: {0} element(s) hidden in '{1}' "
        u"({2:.1f} s, {3} node copies, {4} section-view shell(s) with "
        u"them).".format(len(hidden), liml, seconds, rep.get("copies", 0),
                         shells))
    for _code, pair in rep.get("messages", [])[1:]:
        log(u"WARNING: " + _core_text(pair))
    lines = [tr(u"{0} bezweken element(en) verborgen in de resultaten in "
                u"Mecway, elk vanaf de stap na het bezwijken ({1:.1f} s). "
                u"Resultaten... > Inladen met de optie 'Bezweken elementen "
                u"verbergen' uit toont ze weer.",
                u"{0} failed element(s) hidden in the results in Mecway, "
                u"each from the step after its failure ({1:.1f} s). "
                u"Results... > Load with the option 'Hide failed elements' "
                u"off shows them again.").format(len(hidden), seconds)]
    if shells:
        lines.append(tr(u"De doorsnede van die balken is mee verborgen.",
                        u"The section view of those beams is hidden with "
                        u"them."))
    if stay_note:
        lines.append(stay_note)
    lines += [_core_text(pair) for _code, pair in
              rep.get("messages", [])[1:]]
    return "done", u"\n".join(lines)


def finish(liml):
    """Mecway opened the processed liml: drop the unprocessed copy."""
    _remove(liml + KEEP_SUFFIX)


def restore(liml):
    """Put the unprocessed liml back (Mecway did not open the processed
    one). True when that worked; the processed file is moved aside first,
    so liml is never missing when the swap fails."""
    keep = liml + KEEP_SUFFIX
    aside = liml + TMP_SUFFIX
    if not os.path.exists(keep):
        return False
    try:
        _remove(aside)
        if os.path.exists(liml):
            os.rename(liml, aside)
        try:
            os.rename(keep, liml)
        except OSError:
            if os.path.exists(aside) and not os.path.exists(liml):
                os.rename(aside, liml)
            return False
    except OSError:
        return False
    _remove(aside)
    return True


def hide_and_open(liml, configuration=None, expected=None, open_fn=None,
                  activate_fn=None):
    """
    Setting hide_failed after results were written into liml: apply(), then
    open the processed file with open_fn(liml) (mw.open) and make the
    configuration active with activate_fn(configuration). When Mecway does
    not open it, the unprocessed file is put back and opened. An open
    failure is only seen as an exception of open_fn (NOT verified that
    mw.open raises rather than shows a message).

    Returns (opened, ok, text for the status box): opened True when this
    function opened liml (or tried to, or liml is missing): the caller
    does not open it again; ok False when Mecway does not show the results
    of liml (the caller does not report them as loaded).
    """
    if not enabled():
        return False, True, u""
    state = {}
    try:
        status, text = apply(liml, configuration, expected, state)
    except Exception as e:
        restored = state.get("renamed") and restore(liml)
        if not state.get("renamed"):
            _remove(liml + TMP_SUFFIX)      # the core's output, unused
        log(tr(u"WARNING: Bezweken elementen niet verborgen: {0}",
               u"WARNING: Failed elements not hidden: {0}").format(e))
        if not os.path.isfile(liml):
            return True, False, _missing(liml)
        if state.get("renamed") and not restored:
            # liml is the processed file (the core wrote it completely)
            return False, True, tr(
                u"Bezweken elementen verborgen, maar daarna ging iets mis "
                u"({0}); de resultaten zonder verbergen staan in {1}.",
                u"Failed elements hidden, but something went wrong "
                u"afterwards ({0}); the results without hiding are in "
                u"{1}.").format(e, liml + KEEP_SUFFIX)
        return False, True, tr(
            u"Bezweken elementen niet verborgen: {0} Het model is "
            u"ongewijzigd.",
            u"Failed elements not hidden: {0} The model is "
            u"unchanged.").format(e)
    if status != "done":
        if status == "warning" and not os.path.isfile(liml):
            return True, False, text
        return False, True, text
    try:
        open_fn(liml)
    except Exception as e:
        log(tr(u"ERROR: Mecway opent het model met verborgen bezweken "
               u"elementen niet: {0}",
               u"ERROR: Mecway does not open the model with hidden failed "
               u"elements: {0}").format(e))
        if not restore(liml):
            return True, False, tr(
                u"Mecway opent het model met verborgen bezweken elementen "
                u"niet; de resultaten zonder verbergen staan in {0}.",
                u"Mecway does not open the model with hidden failed "
                u"elements; the results without hiding are in {0}.").format(
                    liml + KEEP_SUFFIX)
        try:
            open_fn(liml)
        except Exception as e2:
            log(tr(u"ERROR: Mecway opent ook het teruggezette model niet: "
                   u"{0}",
                   u"ERROR: Mecway does not open the restored model either: "
                   u"{0}").format(e2))
            return True, False, tr(
                u"Mecway opent het model niet ({0}); de resultaten zonder "
                u"verbergen staan weer in {1}.",
                u"Mecway does not open the model ({0}); the results without "
                u"hiding are back in {1}.").format(e2, liml)
        if configuration and activate_fn is not None:
            activate_fn(configuration)
        return True, True, tr(
            u"Mecway opent het model met verborgen bezweken elementen niet; "
            u"de resultaten zonder verbergen zijn teruggezet.",
            u"Mecway does not open the model with hidden failed elements; "
            u"the results without hiding were put back.")
    finish(liml)
    if configuration and activate_fn is not None:
        activate_fn(configuration)
    return True, True, text


def leftover_text(liml):
    """Status text when liml + KEEP_SUFFIX was left by an earlier session
    (a crash between hiding and opening), else u""."""
    if not liml:
        return u""
    keep = liml + KEEP_SUFFIX
    if not os.path.isfile(keep):
        return u""
    text = tr(u"{0} is achtergebleven uit een eerdere sessie: het bevat de "
              u"resultaten zonder verborgen bezweken elementen. Hernoem het "
              u"naar {1} als dat model beschadigd is of ontbreekt; anders "
              u"mag het weg (de volgende keer verbergen verwijdert het).",
              u"{0} was left by an earlier session: it holds the results "
              u"without hidden failed elements. Rename it to {1} when that "
              u"model is damaged or missing; otherwise it can go (the next "
              u"hiding removes it).").format(keep, os.path.basename(liml))
    log(u"WARNING: " + text)
    return text


def is_processed(liml, configuration=None):
    """
    True when the solution of liml (of that configuration; None = the
    first) has its failed elements hidden: the core's marker on <results>,
    or (Mecway 35 drops that marker when it saves the file, but keeps the
    copies) an element of the model whose nodes in the solution mesh
    include a node numbered above every node of the model: the core's node
    copies. The shells of a section view (bridge_section_view.build_view)
    have node and element numbers above those of the model, so they do not
    count. Not for cyclic symmetry, whose whole-wheel solution numbers its
    extra sectors that way. Limit: the core makes no copy of a node that
    only failed elements share (the last to fail keeps it), so a file whose
    failed elements are all of that kind is not recognised without the
    marker.
    """
    try:
        if liml_failed.processed_marker(liml, configuration):
            return True
        # the attribute as it stands in the XML (escaped, as Mecway writes
        # it; liml_failed.processed_marker unescapes it)
        conf = (None if configuration is None else
                b'configuration="' + _xml_escape(
                    u"{0}".format(configuration),
                    {u'"': u"&quot;"}).encode("utf-8") + b'"')
        model_nid = 0
        model_eid = 0
        target = False
        in_solution = False
        with open(liml, "rb") as f:
            for raw in f:
                s = raw.lstrip()
                if not in_solution:
                    if s.startswith(b"<cyclicsymmetry"):
                        return False
                    if s.startswith(b"<solution"):
                        in_solution = True
                        target = conf is None or conf in s
                        continue
                    m = _NID.match(s)
                    if m:
                        model_nid = max(model_nid, int(m.group(1)))
                        continue
                    m = _ELEM.match(s)
                    if m:
                        model_eid = max(model_eid, int(m.group(1)))
                    continue
                if s.startswith(b"</solution"):
                    if target and conf is None:
                        return False
                    in_solution = False
                    continue
                if target:
                    if s.startswith(b"<results"):
                        return False
                    m = _ELEM.match(s)
                    if m and int(m.group(1)) <= model_eid and any(
                            int(n) > model_nid for n in m.group(2).split()):
                        return True
    except (IOError, OSError):
        return False
    return False


def enabled():
    """Setting hide_failed (route liml only)."""
    return bool(CONFIG_BRIDGE.get("hide_failed", False))
