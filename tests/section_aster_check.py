# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Optional check (not part of the normal tests): compare the "aster" block of
# Scripts/section_analysis.py with Code-Aster's MACR_CARA_POUTRE on the same
# tri6 mesh. Needs Code-Aster 17.4; run with the Code-Aster Python:
#
#   python tests/section_aster_check.py [run_aster.bat]
#
# Works in WorkDir/section_aster_check (removed afterwards).

from __future__ import print_function

import json
import os
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "Scripts"))
import section_analysis  # noqa: E402
import section_mesh  # noqa: E402

COMM = u"""DEBUT(LANG='EN')
MA = LIRE_MAILLAGE(FORMAT='ASTER', UNITE=20)
T = MACR_CARA_POUTRE(MAILLAGE=MA, GROUP_MA_BORD='BORD', GROUP_NO='N1', TABLE_CARA='OUI',
                     NOM='SEC')
IMPR_TABLE(TABLE=T)
import json
v = T.EXTR_TABLE().values()
with open(r'{out}', 'w') as f:
    json.dump(dict((k, [x if isinstance(x, (int, float)) else str(x) for x in l])
                   for k, l in v.items()), f)
FIN()
"""

EXPORT = u"""P time_limit 300
P memory_limit 2048
P ncpus 1
P mpi_nbcpu 1
P mpi_nbnoeud 1
F comm {comm} D 1
F mail {mail} D 20
F mess {mess} R 6
"""


def write_mail(path, nodes, elements, boundary):
    lines = [" TITRE", " section_aster_check", " FINSF", " %", " COOR_2D"]
    for i, (x, y) in enumerate(nodes):
        lines.append(" N{0} {1:.17e} {2:.17e}".format(i + 1, x, y))
    lines += [" FINSF", " %", " TRIA6"]
    for k, e in enumerate(elements):
        lines.append(" M{0} ".format(k + 1) + " ".join("N{0}".format(i + 1) for i in e))
    lines += [" FINSF", " %", " SEG3"]
    for k, b in enumerate(boundary):
        lines.append(" B{0} N{1} N{2} N{3}".format(k + 1, b[0] + 1, b[1] + 1, b[2] + 1))
    lines += [" FINSF", " %", " GROUP_MA", " BORD"]
    lines += [" B{0}".format(k + 1) for k in range(len(boundary))]
    lines += [" FINSF", " %", " GROUP_NO", " N1", " N1", " FINSF", " %", " FIN", ""]
    with open(path, "w") as f:
        f.write("\n".join(lines))


SHAPES = {
    "rect": [[[0, 0], [0.1, 0], [0.1, 0.2], [0, 0.2]]],
    "channel": [[[0, 0], [0.075, 0], [0.075, 0.0115], [0.0085, 0.0115], [0.0085, 0.1885],
                 [0.075, 0.1885], [0.075, 0.2], [0, 0.2]]],
    "angle": [[[0, 0], [0.09, 0], [0.09, 0.01], [0.01, 0.01], [0.01, 0.15], [0, 0.15]]],
    "zed": [[[0, 0], [0.08, 0], [0.08, 0.01], [0.008, 0.01], [0.008, 0.2], [-0.072, 0.2],
             [-0.072, 0.19], [0, 0.19]]],
}

KEYS = ("A", "IY", "IZ", "AY", "AZ", "EY", "EZ", "JX", "JG", "RY", "RZ", "RT", "IYR2", "IZR2")


def run_one(name, loops, run_aster, work):
    mesh = section_mesh.mesh_section(loops)
    res = section_analysis.run_analysis({"loops": loops})
    d = os.path.join(work, name)
    os.makedirs(d)
    mail = os.path.join(d, "sec.mail")
    write_mail(mail, mesh["nodes"], mesh["elements"], mesh["boundary"])
    out = os.path.join(d, "table.json")
    comm = os.path.join(d, "sec.comm")
    with open(comm, "w") as f:
        f.write(COMM.format(out=out))
    exp = os.path.join(d, "sec.export")
    with open(exp, "w") as f:
        f.write(EXPORT.format(comm=comm, mail=mail, mess=os.path.join(d, "sec.mess")))
    subprocess.call([run_aster, exp], cwd=d, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL)
    if not os.path.exists(out):
        print("FOUT {0}: Code-Aster gave no table (see {1})".format(name, d))
        return None
    with open(out) as f:
        tab = json.load(f)
    row = dict((k, v[-1]) for k, v in tab.items())
    return res, row


def to_aster_frame(a, k):
    """Our aster block expressed in Code-Aster's principal frame, which is
    ours rotated by k * 90 deg (k = round((ALPHA - phi) / 90) mod 4), using
    the same relations as TraiteQuadrant in macr_cara_poutre_ops.py."""
    b = dict(a)
    for _ in range(k % 4):
        # rotate the frame by +90 deg: y' = z, z' = -y
        b = {"A": b["A"], "IY": b["IZ"], "IZ": b["IY"], "AY": b["AZ"], "AZ": b["AY"],
             "EY": b["EZ"], "EZ": -b["EY"], "RY": b["RZ"], "RZ": b["RY"],
             "IYR2": -b["IZR2"], "IZR2": b["IYR2"],
             "JX": b["JX"], "JG": b["JG"], "RT": b["RT"]}
    return b


# relative tolerance; for EY/EZ/IYR2/IZR2 relative to a scale of the section
TOL = {"A": 1e-9, "IY": 1e-9, "IZ": 1e-9, "RY": 1e-9, "RZ": 1e-9, "JG": 1e-4,
       "AY": 1e-4, "AZ": 1e-4, "JX": 2e-3, "EY": 1e-4, "EZ": 1e-4,
       "IYR2": 1e-6, "IZR2": 1e-6, "RT": None}


def main():
    run_aster = (sys.argv[1] if len(sys.argv) > 1 else
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "code_aster", "v2025", "17.4", "bin", "run_aster.bat"))
    work = os.path.join(_ROOT, "WorkDir", "section_aster_check")
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)
    failed = False
    keep = False
    for name, loops in sorted(SHAPES.items()):
        r = run_one(name, loops, run_aster, work)
        if r is None:
            keep = failed = True
            continue
        res, row = r
        k = int(round((row["ALPHA"] - res["phi_deg"]) / 90.0)) % 4
        a = to_aster_frame(res["aster"], k)
        print("== {0}: ALPHA = {1:.4f}, phi = {2:.4f}, frame offset {3} x 90 deg".format(
            name, row["ALPHA"], res["phi_deg"], k))
        scale = {"EY": max(a["RY"], a["RZ"]), "EZ": max(a["RY"], a["RZ"]),
                 "IYR2": max(a["IY"], a["IZ"]) * max(a["RY"], a["RZ"]),
                 "IZR2": max(a["IY"], a["IZ"]) * max(a["RY"], a["RZ"])}
        for key in KEYS:
            ca, us = row.get(key), a.get(key)
            dev = abs(us - ca) / max(scale.get(key, abs(ca)), 1e-300)
            tol = TOL[key]
            tag = "INFO" if tol is None else ("OK  " if dev <= tol else "FOUT")
            if tag == "FOUT":
                failed = True
            print("{0} {1:5s} ours {2: .6e}  Code-Aster {3: .6e}  dev {4:.1e}".format(
                tag, key, us, ca, dev))
    if not keep:
        shutil.rmtree(work)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
