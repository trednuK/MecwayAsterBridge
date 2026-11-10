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
# (MecwayAsterBridgeMain._hide_failed) opens the processed file in Mecway.
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


def apply(liml, configuration=None, expected=None):
    """
    Hide the failed elements in liml (the .liml with the results of this
    bridge). configuration: name of the configuration whose solution to
    process (bridge_results_liml.pick_configuration), None for a model
    without configurations. expected: number of failed elements of the run
    (bridge_failure.failed_elements) or None; more than were hidden gives
    a note that those failed at the last stored step and stay visible.

    Returns (status, text):
      ("skip", "")        nothing to hide (static, modal, no variable
                          'failed', nothing failed); the file is unchanged;
      ("done", text)      liml is the processed file and the unprocessed
                          one is liml + KEEP_SUFFIX: the caller opens liml
                          and then calls finish(liml), or restore(liml)
                          when Mecway does not open it;
      ("warning", text)   refused or failed (WARNING logged); the file is
                          unchanged.
    """
    tmp = liml + TMP_SUFFIX
    keep = liml + KEEP_SUFFIX
    _remove(tmp)
    if not os.path.isfile(liml):
        return _not_hidden(tr(u"bestand niet gevonden ({0}).",
                              u"file not found ({0}).").format(liml))
    try:
        marker = liml_failed.processed_marker(liml, configuration)
    except (IOError, OSError) as e:
        return _not_hidden(u"{0}".format(e))
    if marker:
        return _warning(u"De resultaten in {0} hebben de bezweken elementen "
                        u"al verborgen (versie {1}); niet opnieuw bewerkt. "
                        u"Resultaten... > Inladen geeft de oorspronkelijke "
                        u"resultaten terug.",
                        u"The results in {0} already have the failed "
                        u"elements hidden (version {1}); not processed "
                        u"again. Results... > Load gives back the original "
                        u"results.", os.path.basename(liml), marker)
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
    count = rep.get("failed_count", 0)
    stay = (expected - count) if expected and expected > count else 0
    if stay:
        log("INFO: {0} failed element(s) stay visible: they failed at the "
            "last stored step (failed is 1 only from the step after the "
            "failure).".format(stay))
    if not rep.get("written"):
        _remove(tmp)
        log("INFO: Hide failed elements: no failed element in the results "
            "({0:.1f} s).".format(seconds))
        return "skip", u""
    try:
        _remove(keep)
        os.rename(liml, keep)
    except OSError as e:
        _remove(tmp)
        return _not_hidden(u"{0}".format(e))
    try:
        os.rename(tmp, liml)
    except OSError as e:
        os.rename(keep, liml)
        _remove(tmp)
        return _not_hidden(u"{0}".format(e))
    log(u"INFO: Hide failed elements: {0} element(s) hidden in '{1}' "
        u"({2:.1f} s, {3} node copies).".format(count, liml, seconds,
                                               rep.get("copies", 0)))
    for _code, pair in rep.get("messages", [])[1:]:
        log(u"WARNING: " + _core_text(pair))
    lines = [tr(u"{0} bezweken element(en) verborgen in de resultaten in "
                u"Mecway, elk vanaf de stap na het bezwijken ({1:.1f} s). "
                u"Resultaten... > Inladen met de optie 'Bezweken elementen "
                u"verbergen' uit toont ze weer.",
                u"{0} failed element(s) hidden in the results in Mecway, "
                u"each from the step after its failure ({1:.1f} s). "
                u"Results... > Load with the option 'Hide failed elements' "
                u"off shows them again.").format(count, seconds)]
    if stay:
        lines.append(tr(u"{0} bezweken element(en) blijven zichtbaar: ze "
                        u"bezweken bij de laatste opgeslagen stap.",
                        u"{0} failed element(s) stay visible: they failed "
                        u"at the last stored step.").format(stay))
    lines += [_core_text(pair) for _code, pair in
              rep.get("messages", [])[1:]]
    return "done", u"\n".join(lines)


def finish(liml):
    """Mecway opened the processed liml: drop the unprocessed copy."""
    _remove(liml + KEEP_SUFFIX)


def restore(liml):
    """Put the unprocessed liml back (Mecway did not open the processed
    one). True when that worked."""
    keep = liml + KEEP_SUFFIX
    if not os.path.exists(keep):
        return False
    try:
        if os.path.exists(liml):
            os.remove(liml)
        os.rename(keep, liml)
    except OSError:
        return False
    return True


_NID = re.compile(br'<node\s+nid="(\d+)"')


def is_processed(liml, configuration=None):
    """
    True when the solution of liml (of that configuration; None = the
    first) has its failed elements hidden: the core's marker on <results>,
    or (in case a re-save in Mecway dropped the marker, NOT verified) a node
    in the solution mesh numbered above every node of the model. Not for
    cyclic symmetry, whose whole-wheel solution numbers its extra sectors
    that way.
    """
    try:
        if liml_failed.processed_marker(liml, configuration):
            return True
        conf = (None if configuration is None else
                b'configuration="' + u"{0}".format(configuration)
                .encode("utf-8") + b'"')
        model_max = 0
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
                        model_max = max(model_max, int(m.group(1)))
                    continue
                if s.startswith(b"</solution"):
                    in_solution = False
                    continue
                if target:
                    if s.startswith(b"<results"):
                        return False
                    m = _NID.match(s)
                    if m and int(m.group(1)) > model_max:
                        return True
    except (IOError, OSError):
        return False
    return False


def enabled():
    """Setting hide_failed (route liml only)."""
    return bool(CONFIG_BRIDGE.get("hide_failed", False))
