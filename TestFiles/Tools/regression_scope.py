# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Which verification cases does a change touch? (CPython 3, STAPPENPLAN D.5)

Generates the .comm of every case in TestFiles/Verificatie with the Scripts
of this checkout and with those of a git ref, without Code-Aster, and compares
them. An identical .comm means Code-Aster computes the same. It does not show
what happens after the run (bridge_from_aster, bridge_results_liml, the aster_*
job scripts), so the fastest case of every group is run as well.

    python TestFiles/Tools/regression_scope.py [--base develop] [--also NK NL-8]
                                               [--jobs 8]

Prints the ids to pass to run_verificatie.py. Cases that run a solver while
they are being built cannot be compared (NOT_COMPARED): they are reported and
go into the list. Nothing in the checkout is written: models and .comm files
go to a temporary folder (VERIF_WORK if set).
"""
import argparse
import concurrent.futures
import glob
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
VERIF = os.path.join(REPO, "TestFiles", "Verificatie")
SCRIPTS = os.path.join(REPO, "Scripts")
RESULTS = os.path.join(VERIF, "resultaten", "resultaten.json")

# adapt_loop (tests_adaptief): build() runs the refinement loop with Mecway and
# Code-Aster and saves modellen/AD-02-L<k>.liml with the installed Mecway.
NOT_COMPARED = ("AD-02",)

# One case in its own process, as _run_one.py up to the Code-Aster run
_GENERATE = r'''
import io, json, os, shutil, sys
scripts, work, liml, analysis, cfg_path = sys.argv[1:6]
sys.path.insert(0, scripts)
cfg = json.load(io.open(cfg_path, encoding="utf-8"))
os.makedirs(work)
model = os.path.join(work, "model.liml")
shutil.copy(liml, model)
import bridge_utils as u
u.CONFIG_BRIDGE["work_dir"] = work
u.CONFIG_BRIDGE["language"] = "en"
u.CONFIG_BRIDGE["ncpus"] = 1
u.CONFIG_BRIDGE.update(cfg.get("general", {}))
u.CONFIG_BRIDGE["analyses"][analysis].update(cfg.get("settings", {}))
u.CONFIG_BRIDGE["active_analysis"] = analysis
u.set_run_log("verif", model)
from bridge_from_liml import extract_aster_data_from_liml
from bridge_mesh import write_mesh
from bridge_to_aster import generate_AsterSolver_files
md = extract_aster_data_from_liml(model)
mail = os.path.join(work, u.run_name(".mail"))
if md and write_mesh(mail, md):
    generate_AsterSolver_files(work, md, mail, u.run_name(".resu"))
'''


def base_scripts(ref, root):
    """Scripts of git ref in root/base-src (git archive: no checkout)."""
    target = os.path.join(root, "base-src")
    os.makedirs(target)
    tar = os.path.join(root, "base.tar")
    subprocess.check_call(["git", "-C", REPO, "archive", "-o", tar, ref,
                           "Scripts"])
    with tarfile.open(tar) as f:
        f.extractall(target, filter="data")
    return os.path.join(target, "Scripts")


def load_cases():
    sys.path.insert(0, VERIF)
    import run_verificatie
    return run_verificatie.load_cases()


def write_models(cases, root):
    """[(id, liml, analysis, cfg)] of the cases that can be compared."""
    folder = os.path.join(root, "models")
    os.makedirs(folder)
    out = []
    for case in cases:
        if case.id in NOT_COMPARED:
            continue
        liml = case.build().write(os.path.join(folder, case.id + ".liml"))
        cfg = os.path.join(folder, case.id + ".json")
        with open(cfg, "w") as f:
            json.dump({"general": case.general, "settings": case.settings}, f)
        out.append((case.id, liml, case.analysis, cfg))
    return out


def _spellings(path):
    """A path as it can appear in a .comm (slashes, escaped backslashes)."""
    back = path.replace("/", "\\")
    return (path, path.replace("\\", "/"), back, back.replace("\\", "\\\\"))


def generate(job):
    """(case id, tag, .comm text with neutral paths, or None)."""
    scripts, root, tag, cid, liml, analysis, cfg = job
    work = os.path.join(root, tag, cid)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
               PYTHONIOENCODING="utf-8")
    try:
        subprocess.run([sys.executable, "-c", _GENERATE, scripts, work, liml,
                        analysis, cfg], env=env, timeout=300,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return cid, tag, None
    found = glob.glob(os.path.join(work, "*.comm"))
    if not found:
        return cid, tag, None
    text = io.open(found[0], encoding="utf-8", errors="replace").read()
    for path in (work, scripts):
        for spelled in _spellings(path):
            text = text.replace(spelled, "<PATH>")
    return cid, tag, text


def fastest_per_group(cases, seconds):
    """The fastest case of every group (run time of the last regression)."""
    best = {}
    for case in cases:
        if case.id in NOT_COMPARED or case.id not in seconds:
            continue
        old = best.get(case.group)
        if old is None or seconds[case.id] < seconds[old]:
            best[case.group] = case.id
    return sorted(best.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base", default="develop",
                        help="git ref to compare with")
    parser.add_argument("--also", nargs="*", default=[],
                        help="ids or prefixes of the topic, always run")
    parser.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args()
    root = tempfile.mkdtemp(prefix="regression_scope_",
                            dir=os.environ.get("VERIF_WORK") or None)
    try:
        old = base_scripts(args.base, root)
        os.chdir(VERIF)
        cases = load_cases()
        models = write_models(cases, root)
        jobs = [(scripts, root, tag) + m for m in models
                for scripts, tag in ((old, "base"), (SCRIPTS, "new"))]
        texts = {}
        with concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:
            for cid, tag, text in pool.map(generate, jobs):
                texts.setdefault(cid, {})[tag] = text
    finally:
        os.chdir(REPO)
        shutil.rmtree(root, ignore_errors=True)
    changed = sorted(c for c, t in texts.items()
                     if t.get("base") != t.get("new"))
    neither = sorted(c for c, t in texts.items()
                     if t.get("base") is None and t.get("new") is None)
    seconds = {}
    if os.path.isfile(RESULTS):
        rows = json.load(io.open(RESULTS, encoding="utf-8"))
        seconds = dict((k, v.get("seconds") or 0.0) for k, v in rows.items())
    smoke = fastest_per_group(cases, seconds)
    ids = sorted(set(changed) | set(smoke) | set(args.also) |
                 set(NOT_COMPARED))
    print("cases %d, compared %d, identical .comm %d, different %d" % (
        len(cases), len(texts), len(texts) - len(changed), len(changed)))
    print("different: " + (" ".join(changed) or "-"))
    print("no .comm with either code: " + (" ".join(neither) or "-"))
    print("not compared: " + " ".join(NOT_COMPARED))
    print("fastest per group: " + " ".join(smoke))
    print("\npython run_verificatie.py " + " ".join(ids))
    return 0


if __name__ == "__main__":
    sys.exit(main())
