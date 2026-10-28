# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
S35a: research and prototype of adaptive refinement with HOMARD inside the
Code-Aster job (STAPPENPLAN.md §S35). Not part of the bridge and not part of
the regression; reproduces the numbers in the S35 findings.

usage (CPython 3, Code-Aster 17.4 installed):
    python run_s35.py research   [work]   checks: indicators, groups, MAJ_CHAM,
                                          PROJ_CHAMP, mixed meshes, ERTH
    python run_s35.py prototype  [work]   adaptive loops (thermal without and
                                          with boundary following, nonlinear)
    python run_s35.py references [work]   uniform meshes through the bridge
work: work folder (default %TEMP%/mab_s35_proto). The lines 'S35 ...' of
each job are printed; the .mess files stay in the work folder.

Models: the quarter plate with a hole of tests_adaptief.py (d/W = 0.2, hex20,
slab with symmetry on both z faces), thermal (T = 0 / 100 degrees C on the
faces x = 0 / x = L, insulated hole) and nonlinear (bilinear plasticity,
yield 250 MPa, traction ramp to 150 MPa). Quantity: heat flux qx and stress
sxx in the node (0, R) at the hole edge.
"""
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCRIPTS = os.path.join(REPO, "Scripts")
VERIF = os.path.join(REPO, "TestFiles", "Verificatie")
sys.path.insert(0, VERIF)
import tests_adaptief as A                      # noqa: E402
from verif_lib import Model, Results, hexmesh, box  # noqa: E402

SIG = 150.0e6


def plate(n, analysis, timesteps=None, nz=None):
    nz = n if nz is None else nz
    block_a, block_b = A._blocks(A.TZ_STRAIN)
    m = Model(analysis, timesteps=timesteps)
    m.elset("Plaat", "Staal")
    a = hexmesh(m, "Plaat", 2 * n, 2 * n, nz, block_a, order=2)
    b = hexmesh(m, "Plaat", 2 * n, 2 * n, nz, block_b, order=2)
    c = hexmesh(m, "Plaat", 2 * n, 2 * n, nz,
                box(A.WH, A.LH, 0, A.WH, 0, A.TZ_STRAIN), order=2)
    # face selection on the hole (group 'Gat' for FRONTIERE_ANALYTIQUE);
    # the dummy load makes the bridge write its face cells
    m.face_selection("Gat", a["faces"]["u0"] + b["faces"]["u0"])
    return m, a, b, c


def thermal(n, nz=None):
    m, a, b, c = plate(n, "T30", nz=nz)
    m.mat("Staal", '<thermal type="Isotropic" thermalconductivity="50 W/m/K" />')
    m.face_selection("Koud", b["faces"]["v1"])
    m.face_selection("Warm", c["faces"]["u1"])
    m.add(u'<heatflux selection="Gat"><value>0 W/m²</value></heatflux>')
    for sel, t in (("Koud", 273.15), ("Warm", 373.15)):
        m.add('<temperature2 selection="%s"><value>%.12g K</value><starttime>0 s'
              '</starttime><endtime>0 s</endtime></temperature2>' % (sel, t))
    return m


def nonlin(n, nz=None):
    m, a, b, c = plate(n, "L30", {"timeperiod": "1 s", "stepsize": "0.25 s"}, nz=nz)
    m.mat("Staal", '<mechanical type="Isotropic" youngsmodulus="210000 MPa" '
          'poissonratio="0.3" />', '<plastic type="BilinearIsotropic" '
          'yieldstrength="250 MPa" tangentmodulus="2000 MPa" />')
    m.face_selection("SymX", b["faces"]["v1"])
    m.face_selection("SymY", a["faces"]["v0"] + c["faces"]["v0"])
    m.face_selection("SymZ", [f for blk in (a, b, c) for w in ("w0", "w1")
                              for f in blk["faces"][w]])
    m.face_selection("Trek", c["faces"]["u1"])
    # not translated by the bridge (skipped load), only for the face cells
    m.add('<pressure selection="Gat"><value>0 Pa</value></pressure>')
    for s, (x, y, z) in (("SymX", (1, 0, 0)), ("SymY", (0, 1, 0)), ("SymZ", (0, 0, 1))):
        m.add('<symmetry selection="%s"><x>%d</x><y>%d</y><z>%d</z></symmetry>'
              % (s, x, y, z))
    m.add('<traction selection="Trek"><x time="0 s">0 Pa</x><x time="1 s">%g Pa</x>'
          '<y>0 Pa</y><z>0 Pa</z></traction>' % SIG)
    return m


def bridge(work, name, model, analysis):
    """Model through the bridge and Code-Aster (_run_one.py). Returns
    (liml, run.json dict)."""
    liml = model.write(os.path.join(work, name + ".liml"))
    run = os.path.join(work, "run_" + name)
    cfg = run + ".json"
    json.dump({"settings": {}, "general": {}, "timeout": 3600}, open(cfg, "w"))
    subprocess.call([sys.executable, os.path.join(VERIF, "_run_one.py"), run,
                     liml, analysis, cfg])
    return liml, json.load(open(os.path.join(run, "run.json")))


def aster(work, comm_name, mail, tokens):
    """Run one of the .comm files of this folder (tokens filled in)."""
    exe = os.path.expandvars(r"%LOCALAPPDATA%\code_aster\v2025\17.4\bin\run_aster.bat")
    text = io.open(os.path.join(HERE, comm_name), encoding="utf-8").read()
    for k, v in tokens.items():
        text = text.replace("@@%s@@" % k, v)
    base = os.path.join(work, os.path.splitext(comm_name)[0] + tokens.get("TAG", ""))
    io.open(base + ".comm", "w", encoding="utf-8").write(text)
    lines = ["P actions make_etude", "P time_limit 7200", "P memory_limit 4096",
             "P mpi_nbcpu 1", "P ncpus 4", "F comm %s.comm D 1" % base,
             "F mail %s D 20" % mail, "F mess %s.mess R 6" % base,
             "F rmed %s.rmed R 80" % base]
    io.open(base + ".export", "w").write("\n".join(lines) + "\n")
    with open(base + "_console.txt", "w") as f:
        subprocess.call([exe, base + ".export"], stdout=f, stderr=subprocess.STDOUT)
    mess = io.open(base + ".mess", encoding="utf-8", errors="replace").read()
    for line in mess.splitlines():
        if line.startswith("S35 "):
            print(line[:400])
    m = re.search(r"--- DIAGNOSTIC JOB : (\S+)", mess)
    print("%s: DIAGNOSTIC %s" % (os.path.basename(base), m.group(1) if m else "?"))


def mail_of(run):
    return run["export"].replace(".export", ".mail")


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "prototype"
    work = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.environ.get("TEMP", "."), "mab_s35_proto"))
    if not os.path.isdir(work):
        os.makedirs(work)
    if what == "references":
        for name, build, analysis, var in (
                ("th", thermal, "ther_3d", "heatfluxx"),
                ("nl", nonlin, "nonlin_static_3d", "stressxx")):
            for n, nz in ((1, None), (2, None), (4, None), (8, None), (16, 1), (32, 1)):
                tag = "%s_n%d%s" % (name, n, "" if nz is None else "z1")
                liml, run = bridge(work, tag, build(n, nz), analysis)
                lm = A.LimlModel(liml)
                r = Results(run["results"], lm)
                t = r.times()[-1] if r.times() else None
                print("S35 REF %-10s elements %6d  %s(0, R) = %.6g" % (
                    tag, lm.n_elem, var, r.at(var, (0.0, A.R, 0.0), time=t)))
        return
    th_liml, th_run = bridge(work, "th_n1", thermal(1), "ther_3d")
    nl_liml, nl_run = bridge(work, "nl_n1", nonlin(1), "nonlin_static_3d")
    if what == "research":
        aster(work, "research_fields.comm", mail_of(nl_run), {})
        aster(work, "research_erth.comm", mail_of(th_run), {})
        aster(work, "research_mixed.comm", os.path.join(HERE, "mixed.mail"), {})
        return
    common = {"LIB": HERE, "SCRIPTS": SCRIPTS}
    for tag, front in (("_polygon", False), ("_front", True)):
        opts = json.dumps({"nloop": 9, "theta": 0.5, "target": 0.0, "front": front})
        aster(work, "proto_thermal.comm", mail_of(th_run), dict(
            common, OPTS=opts, TAG=tag, LIML=th_liml,
            OUT=os.path.join(work, "proto_thermal%s_results.xml" % tag)))
    opts = json.dumps({"nloop": 9, "theta": 0.5, "target": 0.0, "front": True})
    aster(work, "proto_nonlin.comm", mail_of(nl_run), dict(
        common, OPTS=opts, TAG="_front", LIML=nl_liml, SIG=repr(SIG),
        OUT=os.path.join(work, "proto_nonlin_results.xml")))


if __name__ == "__main__":
    main()
