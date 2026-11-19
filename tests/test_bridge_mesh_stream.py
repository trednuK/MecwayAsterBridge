# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# The streamed ASTER mesh writer must emit the same bytes as the old
# "\\n".join(lines) writer, including the 79-character wrap and a flush
# in the middle of the file. No Mecway, no Code-Aster.
#
#   python tests/test_bridge_mesh_stream.py

from __future__ import print_function

import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_mesh as m  # noqa: E402

_FAILED = []


def check(cond, text):
    print(("OK   " if cond else "FAIL ") + text)
    if not cond:
        _FAILED.append(text)


def _reference(nids, nodes, extra, by_type, group_ma, group_no):
    """The writer this change replaced: one list, joined once."""
    out = ["TITRE", " Mecway-model via MecwayAsterBridge", "FINSF",
           "COOR_3D"]
    for nid in nids:
        out.append(" N{0} {1}".format(nid, " ".join(
            m._real(c) for c in nodes[nid])))
    for nid, xyz in extra:
        out.append(" N{0} {1}".format(nid, " ".join(
            m._real(c) for c in xyz)))
    out.append("FINSF")
    for atype, items in by_type.items():
        out.append(atype)
        for name, cn in items:
            out.extend(m._wrap([name] + ["N{0}".format(n) for n in cn]))
        out.append("FINSF")
    for kind, groups in (("GROUP_MA", group_ma), ("GROUP_NO", group_no)):
        for name, members in groups.items():
            out.append(kind)
            out.append(" {0}".format(name))
            out.extend(m._wrap(members))
            out.append("FINSF")
    out.append("FIN")
    return "\n".join(out) + "\n"


def _sample():
    nodes = {}
    nids = list(range(1, 401))
    for nid in nids:
        nodes[nid] = (nid * 1.0e-8, -nid * 0.25, float(nid))
    nodes[1] = (0.0, -1.0e-5, 1.25)
    extra = [(401, (1.0, 2.0, 3.0)), (402, (-0.0, 1.0e20, -3.5))]
    cn = list(range(1, 21))
    by_type = {
        "HEXA20": [("M{0}".format(i), cn) for i in range(1, 31)],
        "SEG2": [("M100", [1, 2])],
    }
    group_ma = {"ALL": ["M{0}".format(i) for i in range(1, 31)]}
    # One name longer than the line limit: _wrap keeps it on its own line.
    group_no = {"NODES": ["N{0}".format(n) for n in nids] + ["TOOLONGNAME"]}
    return nids, nodes, extra, by_type, group_ma, group_no


def _compare(chunk, label):
    nids, nodes, extra, by_type, group_ma, group_no = _sample()
    expect = _reference(nids, nodes, extra, by_type, group_ma, group_no)
    saved = m._MAIL_CHUNK
    m._MAIL_CHUNK = chunk
    fd, path = tempfile.mkstemp(suffix=".mail")
    os.close(fd)
    try:
        m._write_aster_mail_py(path, nids, nodes, extra, by_type,
                            group_ma, group_no)
        with open(path, "r") as f:
            got = f.read()
    finally:
        m._MAIL_CHUNK = saved
        os.remove(path)
    check(got == expect, label + ": {0} bytes".format(len(expect)))
    if got != expect:
        print("  first difference at {0}".format(
            next((i for i, (a, b) in enumerate(zip(got, expect)) if a != b),
                 min(len(got), len(expect)))))


def main():
    _compare(1 << 20, "default chunk")
    _compare(64, "flush every 64 characters")
    _compare(1, "flush every character")
    # Empty groups and no extra nodes still get the header and FIN.
    expect = _reference([1], {1: (0.0, 0.0, 0.0)}, [], {}, {}, {})
    fd, path = tempfile.mkstemp(suffix=".mail")
    os.close(fd)
    try:
        m._write_aster_mail_py(path, [1], {1: (0.0, 0.0, 0.0)}, [], {}, {}, {})
        with open(path, "r") as f:
            got = f.read()
    finally:
        os.remove(path)
    check(got == expect and got.endswith("FIN\n"), "header only")
    if _FAILED:
        print("{0} FAILED".format(len(_FAILED)))
        return 1
    print("ALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
