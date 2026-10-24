# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_mwpost.py
# A run in MWHub Post (AdvancedToolsHub, ParaView): write a job
# (mwhubpost-job/1, AdvancedToolsHub docs/design/CONTRACT_MWPOST.md §2)
# next to the result files and hand it to the hub's launcher
# (launcher/mwhubpost_launch.py: validate_job, write_job, launch).
#
# Used by the ParaView button of the convergence window
# (aster_convergence_monitor.open_paraview, CPython 3). Without the hub
# (bridge_utils.advancedtoolshub_dir_path() == "") open_run returns None
# and the caller keeps its old behaviour (.rmed directly in ParaView).
#
# Job contents (contract example A):
#   results  : <run>.rmed (MED, if med_export) and <run>.pvd (VTU, if
#              vtu_export); MED first, except when the VTU has the failure
#              field BEZWEKEN (aster_vtu): the MED file has no such field,
#              so the PVD comes first for the filter "hide failed".
#   fields   : deformation DEPL; erosion BEZWEKEN (intact = 0) when present;
#              a list with labels for the hub's panel.
#   sidecars : <run>_beams.json and <run>_knopen.csv when they exist.
#   style    : Mecway's user.config (mecway_user_config), display units of
#              Mecway; ParaView exe = setting paraview_exe.
#
# Compatible with IronPython 2.7.9 and CPython 3 (stdlib only; the
# launcher is loaded from its file, it has no package).

import os
import re
from datetime import datetime

import bridge_utils
from bridge_utils import tr

# <model>_<run_id>: run_id = time stamp of the run (bridge_utils.run_name)
_RUN_ID_RE = re.compile(r"^(.*)_(\d{8}_\d{6})$")

_LAUNCHER = {}


def load_launcher(hub_dir):
    """The module mwhubpost_launch from <hub_dir>/launcher (cached)."""
    path = os.path.join(hub_dir, "launcher", "mwhubpost_launch.py")
    if path not in _LAUNCHER:
        try:
            import importlib.util as iu      # CPython 3 (imp is gone in 3.12)
        except ImportError:
            iu = None
        if iu is None:
            import imp                       # IronPython 2.7
            _LAUNCHER[path] = imp.load_source("mwhubpost_launch", path)
        else:
            spec = iu.spec_from_file_location("mwhubpost_launch", path)
            module = iu.module_from_spec(spec)
            spec.loader.exec_module(module)
            _LAUNCHER[path] = module
    return _LAUNCHER[path]


def _has_vtu_field(pvd, name):
    """True if the first .vtu of the .pvd has an array name (the header
    is text before the appended data, aster_vtu)."""
    first = os.path.splitext(pvd)[0] + "_0.vtu"
    try:
        f = open(first, "rb")
        try:
            head = f.read(65536)
        finally:
            f.close()
    except (IOError, OSError):
        return False
    return ('Name="{0}"'.format(name)).encode("ascii") in head


def _label(nl, en):
    return {"en": en, "nl": nl}


def build_job(run_base, analysis="", language="en", mecway_version=None):
    """
    mwhubpost-job/1 for the result files <run_base>.rmed / .pvd (run_base =
    <work_dir>/<model>_<run_id>). None if neither exists.
    """
    rmed = run_base + ".rmed"
    pvd = run_base + ".pvd"
    has_med = os.path.isfile(rmed)
    has_pvd = os.path.isfile(pvd)
    if not (has_med or has_pvd):
        return None
    failed = has_pvd and _has_vtu_field(pvd, "BEZWEKEN")
    results = []
    if has_med:
        results.append({"kind": "med", "path": rmed.replace("\\", "/")})
    if has_pvd:
        item = {"kind": "pvd", "path": pvd.replace("\\", "/")}
        if failed:
            results.insert(0, item)
        else:
            results.append(item)
    results[0]["role"] = "primary"
    for item in results[1:]:
        item["role"] = "alternative"

    base = os.path.basename(run_base)
    m = _RUN_ID_RE.match(base)
    name, run_id = (m.group(1), m.group(2)) if m else (base, "")
    fields = {
        "deformation": {"name": "DEPL", "scale": "auto"},
        "list": [
            {"name": "DEPL", "label": _label("Verplaatsing", "Displacement"),
             "dimension": "L", "association": "points"},
            {"name": "SIEQ_NOEU", "alt_names": ["vonmises"],
             "label": _label("Von Mises-spanning", "Von Mises stress"),
             "dimension": "L-1 M T-2", "association": "points"},
        ],
    }
    if failed:
        fields["erosion"] = {"name": "BEZWEKEN", "association": "cells",
                             "active_value": 0}
        fields["list"].append(
            {"name": "BEZWEKEN", "label": _label("Bezweken", "Failed"),
             "dimension": "", "association": "cells"})
    job = {
        "schema": "mwhubpost-job/1",
        "created": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "caller": {"name": "MecwayAsterBridge",
                   "version": bridge_utils.BRIDGE_VERSION},
        "language": "nl" if language == "nl" else "en",
        "model": {"name": name, "run_id": run_id, "solver": "code_aster",
                  "analysis": analysis or "",
                  "units": {"length": "m", "mass": "kg", "time": "s",
                            "force": "N", "stress": "Pa"}},
        "results": results,
        "fields": fields,
        "style": {"source": "mecway_user_config"},
        "display_units": "mecway",
        "window": {"reuse": True},
    }
    if mecway_version:
        job["style"]["mecway_version"] = int(mecway_version)
    sidecars = {}
    for key, suffix in (("beams", "_beams.json"),
                        ("node_series", "_knopen.csv")):
        if os.path.isfile(run_base + suffix):
            sidecars[key] = (run_base + suffix).replace("\\", "/")
    if sidecars:
        job["sidecars"] = sidecars
    return job


def open_run(run_base, paraview=None, analysis="", mecway_version=None):
    """
    Open the run in MWHub Post. Returns None without the hub (the caller
    keeps its own route), else (ok, [message lines]) in the language of
    the bridge. paraview: paraview.exe / run_paraview.bat or None (= the
    setting paraview_exe; "" = the launcher's own search, ParaView 6.x
    first, then Salome-Meca's).
    """
    hub = bridge_utils.advancedtoolshub_dir_path()
    if not hub:
        return None
    lang = bridge_utils.CONFIG_BRIDGE.get("language", "en")
    job = build_job(run_base, analysis, lang, mecway_version)
    if job is None:
        return (False, [tr(
            u"Geen MED- of VTU-bestand voor deze run: {0}.rmed / .pvd. Zet "
            u"in het startscherm 'MED-bestand voor ParaView' (med_export) of "
            u"'VTU/PVD-bestanden voor ParaView' (vtu_export) aan en start de "
            u"run opnieuw.",
            u"No MED or VTU file for this run: {0}.rmed / .pvd. Turn on 'MED "
            u"file for ParaView' (med_export) or 'VTU/PVD files for "
            u"ParaView' (vtu_export) on the start screen and run "
            u"again.").format(run_base)])
    try:
        launcher = load_launcher(hub)
    except Exception as e:
        return (False, [tr(u"MWHub Post-launcher niet te laden ({0}): {1}",
                           u"Cannot load the MWHub Post launcher ({0}): {1}")
                        .format(hub, e)])
    if paraview is None:
        paraview = bridge_utils.CONFIG_BRIDGE.get("paraview_exe") or ""
    paraview = bridge_utils.expand_path(paraview)
    job_path = run_base + "_job.json"
    issues = launcher.validate_job(job)
    if launcher.has_errors(issues):
        return (False, launcher.format_issues(issues, lang))
    launcher.write_job(job, job_path)
    result = launcher.launch(job_path, setting=paraview or None)
    lines = launcher.format_issues(result.get("issues") or [], lang)
    return (bool(result.get("ok")), lines)
