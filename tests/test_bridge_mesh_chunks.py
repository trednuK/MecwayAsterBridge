# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of the faster .mail writing in Scripts/bridge_mesh.py
# (very large models): the result must stay byte-identical.
#   - _MailWriter: the pieces written are "\n".join(lines) + "\n", for every
#     chunk size, also when one line is longer than a chunk or ends exactly
#     on it; no lines writes nothing;
#   - _wrap: its fast path gives the same lines as the old loop (kept here
#     as _wrap_ref), for random items and the 79/80-character edges;
#   - _free_faces: the same faces in the same order as the old version with
#     an OrderedDict (kept here as _free_faces_ref), on the test models and
#     on degenerate elements (a collapsed hex, a shell on a solid face, a
#     wedge and a pyramid);
#   - write_mesh: the file equals the old join of the same lines, a tiny
#     chunk size gives the same bytes, a failure keeps an existing .mail
#     and leaves no .tmp.
# Python 2.7 (IronPython) and 3; under CPython it also runs once in
# Mecway's IronPython 2.7.9 (TestFiles/Tools/run_ipy.ps1) when Mecway is
# installed.
#
#   python tests/test_bridge_mesh_chunks.py

from __future__ import print_function

import io
import os
import random
import shutil
import subprocess
import sys
import tempfile
from collections import OrderedDict

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_REPO, "Scripts"))

import bridge_utils                                    # noqa: E402
import bridge_mesh                                     # noqa: E402
from bridge_from_liml import extract_aster_data_from_liml  # noqa: E402

IRONPYTHON = sys.platform == "cli"
FAILED = []
MODELS = [os.path.join(_REPO, "TestFiles", p) for p in (
    os.path.join("Voorbeelden", "Voorbeeld_A.liml"),
    os.path.join("Voorbeelden", "Voorbeeld_C.liml"),
    os.path.join("Voorbeelden", "Voorbeeld_S.liml"),
    os.path.join("Voorbeelden", "Voorbeeld_T.liml"),
    "BezwijkenTrekstaaf.liml", "TieContact_Plates.liml",
    "Foutschatter_Balk.liml")]


def check(name, cond, detail=""):
    print(("OK   " if cond else "FAIL ") + name +
          (" ({0})".format(detail) if detail != "" and not cond else ""))
    if not cond:
        FAILED.append(name)


def read(path):
    with open(path, "rb") as f:
        return f.read()


# --- the versions before the change (19 Nov 2026), as references ---
def _wrap_ref(items, width=79):
    lines = []
    cur = ""
    for it in items:
        if cur and len(cur) + 1 + len(it) > width:
            lines.append(cur)
            cur = ""
        cur += " " + it
    if cur:
        lines.append(cur)
    return lines


def _free_faces_ref(model_data, conn):
    bm = bridge_mesh
    shapes = model_data.get("elem_shapes", {})
    counts = OrderedDict()
    for eid in sorted(conn):
        if shapes.get(eid) not in bm._SOLID_SHAPES:
            continue
        atype, cn = conn[eid]
        for prefix, table in bm._FACE_CORNERS.items():
            if atype.startswith(prefix):
                for fid in sorted(table):
                    corners = [cn[i] for i in table[fid]]
                    key = frozenset(corners)
                    if key in counts:
                        counts[key][0] += 1
                    else:
                        counts[key] = [1, eid, corners]
                break
    taken = set()
    for eid, (atype, cn) in conn.items():
        if shapes.get(eid) in bm._SHELL_SHAPES:
            taken.add(frozenset(cn[:bm._N_CORNERS[atype]]))
    used = bm._referenced_names(model_data)
    for fname, faces in model_data.get("face_selection_faces", {}).items():
        if fname not in used:
            continue
        for eid, fid in faces:
            if eid in conn:
                taken.add(frozenset(bm._face_from_table(
                    conn[eid][0], conn[eid][1], fid) or []))
    fixed = set()
    for bc in model_data.get("bcs", []):
        if bc.get("type") not in bm._DIRICHLET_BCS or not bc.get("selection"):
            continue
        for i in model_data.get("node_groups", {}).get(bc["selection"], []):
            fixed.add(int(str(i).lstrip("N")))
    out = []
    for key, (n, eid, corners) in counts.items():
        if n != 1 or key in taken or key <= fixed:
            continue
        atype, cn = conn[eid]
        out.append(bm._skin_element(atype, cn, corners))
    return out


class _Sink(object):
    """File-like object that keeps every write."""

    def __init__(self):
        self.parts = []

    def write(self, text):
        self.parts.append(text)


def test_writer():
    rnd = random.Random(7)
    cases = [[], ["FIN"], ["a" * 50], ["", "", "x", ""],
             ["b" * 200, "c"], ["d" * 63, "e" * 63, "f"]]
    for _ in range(20):
        cases.append(["x" * rnd.randint(0, 90)
                      for _k in range(rnd.randint(1, 60))])
    ok = True
    for lines in cases:
        for chunk in (1, 7, 64, 65, None):
            sink = _Sink()
            w = bridge_mesh._MailWriter(sink, chunk)
            for line in lines:
                w.append(line)
            w.flush()
            got = "".join(sink.parts)
            want = "\n".join(lines) + "\n" if lines else ""
            if got != want or "" in sink.parts:
                ok = False
    check("_MailWriter: pieces equal the old join for every chunk size", ok)
    sink = _Sink()
    w = bridge_mesh._MailWriter(sink, 10)
    w.extend(["123456789"])          # 10 characters with the newline
    check("_MailWriter: a full chunk is written at once",
          sink.parts == ["123456789\n"], sink.parts)
    w.flush()
    check("_MailWriter: a flush without lines writes nothing",
          sink.parts == ["123456789\n"], sink.parts)


def test_wrap():
    rnd = random.Random(11)
    cases = [[], ["M1"], ["x" * 78], ["x" * 79], ["x" * 80],
             ["a" * 39, "b" * 38], ["a" * 39, "b" * 39], ["a" * 39, "b" * 40],
             ["M123456"] + ["N{0}".format(n) for n in range(100000, 100027)]]
    for _ in range(300):
        cases.append(["N{0}".format(rnd.randint(1, 10 ** rnd.randint(1, 7)))
                      for _k in range(rnd.randint(1, 30))])
    bad = [c for c in cases if bridge_mesh._wrap(c) != _wrap_ref(c)]
    check("_wrap: fast path gives the same lines", not bad, bad[:1])
    bad = [c for c in cases
           if bridge_mesh._wrap(c, 40) != _wrap_ref(c, 40)]
    check("_wrap: same lines with another width", not bad, bad[:1])


def test_free_faces_degenerate():
    # hex 1 with its top face collapsed (nodes 5..8 -> 5), hex 2 on its
    # bottom face, a shell on a face of hex 2, a wedge and a pyramid
    conn = OrderedDict()
    conn[1] = ("HEXA8", [1, 2, 3, 4, 5, 5, 5, 5])
    conn[2] = ("HEXA8", [5, 6, 7, 8, 9, 10, 11, 12])
    conn[3] = ("QUAD4", [9, 10, 11, 12])
    conn[4] = ("PENTA6", [20, 21, 22, 23, 24, 25])
    conn[5] = ("PYRAM5", [23, 24, 25, 26, 27])
    conn[6] = ("TETRA4", [1, 2, 3, 30])
    md = {"elem_shapes": {1: "hex8", 2: "hex8", 3: "quad4", 4: "wedge6",
                          5: "pyr5", 6: "tet4"},
          "bcs": [{"type": "fixed", "selection": "Vast"}],
          "node_groups": {"Vast": ["N20", "N21", "N22"]},
          "face_selection_faces": {}}
    if "wedge6" not in bridge_mesh._SOLID_SHAPES:
        md["elem_shapes"][4] = [s for s in bridge_mesh._SOLID_SHAPES
                                if s.startswith("wedge") or
                                s.startswith("penta")][0]
    got = bridge_mesh._free_faces(md, conn)
    want = _free_faces_ref(md, conn)
    check("_free_faces: degenerate elements as before", got == want,
          (got, want))
    check("_free_faces: the fixture has free faces", len(got) > 5, got)


def _write(model, mail, analysis="lin_static_3d"):
    bridge_utils.CONFIG_BRIDGE["active_analysis"] = analysis
    md = extract_aster_data_from_liml(model)
    return md is not None and bridge_mesh.write_mesh(mail, md)


def test_write_mesh(tmp):
    recorded = []
    orig_writer = bridge_mesh._MailWriter

    class Recorder(orig_writer):
        def append(self, line):
            recorded.append(line)
            orig_writer.append(self, line)

    orig_free = bridge_mesh._free_faces
    compared = []

    def free_both(model_data, conn):
        got = orig_free(model_data, conn)
        compared.append(got == _free_faces_ref(model_data, conn))
        return got

    for model in MODELS:
        if not os.path.exists(model):
            check("model present: " + os.path.basename(model), False)
            continue
        name = os.path.splitext(os.path.basename(model))[0]
        del recorded[:]
        del compared[:]
        mail = os.path.join(tmp, name + ".mail")
        bridge_mesh._MailWriter = Recorder
        bridge_mesh._free_faces = free_both
        try:
            ok = _write(model, mail)
        finally:
            bridge_mesh._MailWriter = orig_writer
            bridge_mesh._free_faces = orig_free
        if not ok:
            check(name + ": write_mesh", False)
            continue
        ref = os.path.join(tmp, name + "_ref.mail")
        f = open(ref, "w")             # the old way: one join, text mode
        try:
            f.write("\n".join(recorded) + "\n")
        finally:
            f.close()
        check(name + ": file equals the old join of its lines",
              read(mail) == read(ref))
        check(name + ": _free_faces as before",
              compared and all(compared), compared)
        small = os.path.join(tmp, name + "_small.mail")
        saved = bridge_mesh._MAIL_CHUNK
        bridge_mesh._MAIL_CHUNK = 64
        try:
            _write(model, small)
        finally:
            bridge_mesh._MAIL_CHUNK = saved
        check(name + ": chunk size 64 gives the same bytes",
              read(small) == read(mail))
        check(name + ": no .tmp left", not os.path.exists(mail + ".tmp"))


def test_write_failure(tmp):
    model = MODELS[0]
    mail = os.path.join(tmp, "fail.mail")
    with open(mail, "wb") as f:
        f.write(b"OLD")

    orig = bridge_mesh._MailWriter

    class Broken(orig):
        def append(self, line):
            if line == "FINSF":
                raise IOError("disk full (test)")
            orig.append(self, line)

    bridge_mesh._MailWriter = Broken
    try:
        ok = _write(model, mail)
    finally:
        bridge_mesh._MailWriter = orig
    check("failure: write_mesh returns False", ok is False, ok)
    check("failure: the existing .mail is unchanged", read(mail) == b"OLD")
    check("failure: no .tmp left", not os.path.exists(mail + ".tmp"))
    os.remove(mail)
    check("success after a failure: new .mail written",
          _write(model, mail) and read(mail).startswith(b"TITRE"))


def run_in_ironpython():
    ps = os.path.join(_HERE, "..", "TestFiles", "Tools", "run_ipy.ps1")
    if not (sys.platform == "win32" and os.path.isdir(
            r"C:\Program Files\Mecway") and os.path.exists(ps)):
        print("SKIP IronPython run (needs Mecway's IronPython)")
        return
    tmp = tempfile.mkdtemp(prefix="mesh_chunks_ipy_")
    try:
        wrapper = os.path.join(tmp, "run_mesh_chunks.py")
        with io.open(wrapper, "w", encoding="utf-8") as f:
            f.write(u"import sys\nsys.path.insert(0, {0!r})\n"
                    u"import test_bridge_mesh_chunks as t\n"
                    u"sys.exit(t.main())\n".format(os.path.abspath(_HERE)))
        proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", os.path.abspath(ps), "-Script", wrapper],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = proc.communicate()[0].decode("utf-8", "replace")
        print("--- IronPython 2.7.9 ---")
        print(out.strip())
        check("IronPython run without failures", proc.returncode == 0 and
              "FAIL" not in out and "All tests passed." in out)
    finally:
        shutil.rmtree(tmp, True)


def main():
    tmp = tempfile.mkdtemp(prefix="mesh_chunks_")
    config = bridge_utils.CONFIG_BRIDGE
    saved = (config.get("work_dir", ""), config.get("active_analysis"))
    config["work_dir"] = tmp           # in memory only: log goes here
    try:
        test_writer()
        test_wrap()
        test_free_faces_degenerate()
        test_write_mesh(tmp)
        test_write_failure(tmp)
    finally:
        config["work_dir"], config["active_analysis"] = saved
        shutil.rmtree(tmp, True)
    if not IRONPYTHON:
        run_in_ironpython()
    if FAILED:
        print("{0} failure(s): {1}".format(len(FAILED), ", ".join(FAILED)))
        return 1
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
