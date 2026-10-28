# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Een verificatiecase door de bridge en Code-Aster (CPython 3, eigen proces).
gebruik: python _run_one.py <werkmap> <model.liml> <analyse> <instellingen.json>
Schrijft <werkmap>/run.json met export/mess/results/diagnose.
De bridge draait zoals vanuit Mecway (bridge_from_liml -> bridge_mesh ->
bridge_to_aster/bridge_thermal), maar zonder Mecway-API (faceid-tabel van
bridge_mesh) en met run_aster.bat synchroon.
"""
import sys
import os
import io
import re
import json
import shutil
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(HERE)), "Scripts")
sys.path.insert(0, SCRIPTS)

work, liml, analysis, cfg_path = sys.argv[1:5]
cfg = json.load(io.open(cfg_path, encoding="utf-8"))
if os.path.isdir(work):
    shutil.rmtree(work)
os.makedirs(work)
model = os.path.join(work, os.path.basename(liml))
shutil.copy(liml, model)

import bridge_utils as u
u.CONFIG_BRIDGE["work_dir"] = work
u.CONFIG_BRIDGE["language"] = "nl"
for k, v in cfg.get("general", {}).items():
    u.CONFIG_BRIDGE[k] = v
for k, v in cfg.get("settings", {}).items():
    u.CONFIG_BRIDGE["analyses"][analysis][k] = v
u.CONFIG_BRIDGE["active_analysis"] = analysis
u.set_run_log("verif", model)

from bridge_from_liml import extract_aster_data_from_liml
from bridge_mesh import write_mesh
from bridge_to_aster import generate_AsterSolver_files

out = {"export": None, "mess": None, "results": None, "diagnostic": "",
       "errors": [], "seconds": None}
md = extract_aster_data_from_liml(model)
mail = os.path.join(work, u.run_name(".mail"))
exp = None
if md and write_mesh(mail, md):
    exp = generate_AsterSolver_files(work, md, mail, u.run_name(".resu"))
out["export"] = exp
out["skipped"] = list(md.get("skipped_loads", [])) if md else []
if exp:
    t0 = time.time()
    with open(os.path.join(work, u.run_name("_console.txt")), "w") as f:
        try:
            # CREATE_NO_WINDOW: without it Windows opens a console window
            # for run_aster.bat per case (the output goes to the file anyway)
            subprocess.call([u.exe_aster_path(), exp], stdout=f,
                            stderr=subprocess.STDOUT,
                            timeout=float(cfg.get("timeout", 1800)),
                            creationflags=getattr(subprocess,
                                                  "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired:
            out["errors"].append("TIMEOUT")
    out["seconds"] = time.time() - t0
    mess = os.path.join(work, u.run_name(".mess"))
    if os.path.isfile(mess):
        out["mess"] = mess
        text = io.open(mess, encoding="utf-8", errors="replace").read()
        m = re.search(r"--- DIAGNOSTIC JOB : (\S+)", text)
        out["diagnostic"] = m.group(1) if m else "?"
        out["errors"] += sorted(set(re.findall(
            r"<(?:EXCEPTION|F|[A-Za-z]+Error)>\s*<([A-Za-z0-9_]+)>", text)))
        if "BRIDGE_ONVOLLEDIG" in text:
            out["errors"].append("BRIDGE_ONVOLLEDIG")
    res = os.path.join(work, u.run_name("_results.xml"))
    if os.path.isfile(res):
        out["results"] = res
log = os.path.join(work, u.log_file_name())
if os.path.isfile(log):
    out["errors"] += [l[22:] for l in io.open(log, encoding="utf-8",
                                              errors="replace")
                      if "ERROR:" in l]
json.dump(out, io.open(os.path.join(work, "run.json"), "w", encoding="utf-8"),
          indent=1)
