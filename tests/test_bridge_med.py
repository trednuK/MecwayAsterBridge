# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Host-side MED reader (CAVE): a small .rmed written like libmed, then
# the <results> fragment. Needs h5py only to BUILD the fixture; the
# reader itself does not.
#   python tests/test_bridge_med.py
from __future__ import print_function

import base64
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Scripts"))

import bridge_med
from bridge_utils import CONFIG_BRIDGE, host_med_results


def _fortran(rows):
    """rows: list of component lists. Column-major flat, as MED."""
    ncol = len(rows[0])
    nrow = len(rows)
    flat = []
    for c in range(ncol):
        for i in range(nrow):
            flat.append(rows[i][c])
    return flat


def _make(path):
    import h5py
    import numpy as np
    step = "-0000000000000000001-0000000000000000001"
    profile = "MED_NO_PROFILE_INTERNAL"
    with h5py.File(path, "w") as f:
        body = f.create_group("ENS_MAA/MAIL/" + step)
        # two nodes, (0,0,0) and (1,0,0), numbers 1 and 2
        coo = body.create_dataset(
            "NOE/COO", data=np.array(_fortran([[0, 0, 0], [1, 0, 0]]),
                                     dtype="<f8"))
        coo.attrs["NBR"] = np.int64(2)
        num = body.create_dataset("NOE/NUM", data=np.array([1, 2], dtype="<i4"))
        num.attrs["NBR"] = np.int64(2)
        # one tetra, nodes 1 2 3 4 would need 4 nodes; two-node line instead
        nod = body.create_dataset(
            "MAI/SE2/NOD", data=np.array(_fortran([[1, 2]]), dtype="<i4"))
        nod.attrs["NBR"] = np.int64(1)
        depl = f.create_group("CHA/DEPL")
        depl.attrs["NOM"] = np.bytes_("DX              DY              DZ              ")
        dest = depl.create_group(step + "/NOE/" + profile)
        co = dest.create_dataset(
            "CO", data=np.array(_fortran([[0.1, 0.2, 0.3], [0.4, 0.0, 0.0]]),
                                dtype="<f8"))
        co.attrs["NBR"] = np.int64(2)
        co.attrs["NGA"] = np.int64(1)
        f[step and "CHA/DEPL/" + step + "/NOE"].attrs["PFL"] = np.bytes_(profile)
        sieq = f.create_group("CHA/SIEQ_NOEU")
        sieq.attrs["NOM"] = np.bytes_("VMIS            ")
        sdest = sieq.create_group(step + "/NOE/" + profile)
        sv = sdest.create_dataset(
            "CO", data=np.array([10.0, 20.0], dtype="<f8"))
        sv.attrs["NBR"] = np.int64(2)
        sv.attrs["NGA"] = np.int64(1)
        f["CHA/SIEQ_NOEU/" + step + "/NOE"].attrs["PFL"] = np.bytes_(profile)
        # element-node, one value per end, MED order 1 then 2
        elno = f.create_group("CHA/SIGM_ELNO")
        elno.attrs["NOM"] = np.bytes_("SIXX            ")
        edest = elno.create_group(step + "/NOE.SE2/" + profile)
        ev = edest.create_dataset(
            "CO", data=np.array(_fortran([[3.0], [7.0]]), dtype="<f8"))
        ev.attrs["NBR"] = np.int64(1)
        ev.attrs["NGA"] = np.int64(2)
        f["CHA/SIGM_ELNO/" + step + "/NOE.SE2"].attrs["PFL"] = np.bytes_(profile)
        f["CHA/DEPL/" + step].attrs["PDT"] = np.float64(0.0)
        f["CHA/SIEQ_NOEU/" + step].attrs["PDT"] = np.float64(0.0)
        f["CHA/SIGM_ELNO/" + step].attrs["PDT"] = np.float64(0.0)


def _values(xml, name):
    marker = 'variable name="{0}"'.format(name)
    start = xml.index(marker)
    chunk = xml[start:xml.index("</valuesdouble>", start)]
    b64 = "".join(chunk.split("<valuesdouble>", 1)[1].split())
    raw = base64.b64decode(b64)
    return [struct.unpack_from("<d", raw, i)[0]
            for i in range(0, len(raw), 8)]


def _rust_exe():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.join(here, "..", "rust", "aster_fast", "target", "release")
    for name in ("aster_fast", "aster_fast.exe"):
        path = os.path.join(root, name)
        if os.path.isfile(path):
            return path
    return None


def _rust_same(rmed, xml, model):
    """The Rust reader writes the same fragment. Skipped without a build."""
    import subprocess
    exe = _rust_exe()
    if not exe:
        print("SKIP aster_fast med (binary not built)")
        return
    liml = os.path.join(os.path.dirname(rmed), "model.liml")
    # one line, Mecway node order 2 then 1, elset Arm
    open(liml, "w").write(
        '<liml><elset name="Arm">'
        '<elem eid="1" shape="line2" nodes="2 1"/>'
        '</elset></liml>')
    out = os.path.join(os.path.dirname(rmed), "rust.xml")
    proc = subprocess.Popen([exe, "med", rmed, out, liml],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _stdout, err = proc.communicate()
    assert proc.returncode == 0, err
    got = open(out, "rb").read()
    want = open(xml, "rb").read()
    assert got == want, "aster_fast med differs from bridge_med"
    # gzip + shuffle, the way a large Code-Aster .rmed is stored
    import h5py
    import numpy as np
    import shutil
    packed = rmed + ".gz.h5"
    shutil.copy(rmed, packed)
    # rewrite the displacement values compressed; the mesh stays
    with h5py.File(rmed, "r") as src, h5py.File(packed, "w") as dst:
        def copy(name, obj):
            if isinstance(obj, h5py.Dataset):
                kw = {}
                if obj.dtype.kind == "f":
                    kw["compression"] = "gzip"
                    kw["shuffle"] = True
                d = dst.create_dataset(name, data=obj[()], **kw)
                for k, v in obj.attrs.items():
                    d.attrs[k] = v
            elif isinstance(obj, h5py.Group):
                g = dst.create_group(name)
                for k, v in obj.attrs.items():
                    g.attrs[k] = v
        src.visititems(copy)
    py2 = out + ".py"
    bridge_med.write_fragment(packed, py2, model)
    proc = subprocess.Popen([exe, "med", packed, out, liml],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _stdout, err = proc.communicate()
    assert proc.returncode == 0, err
    assert open(out, "rb").read() == open(py2, "rb").read()


def main():
    try:
        import h5py  # noqa: F401
    except ImportError:
        print("SKIP h5py (fixture only); reader is not skipped in the bridge")
        return 0
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "study.rmed")
    out = os.path.join(tmp, "out.xml")
    _make(path)
    model = {"elements": {1: ("line", [2, 1])},
             "elsets": {"Arm": [1]}}
    n = bridge_med.write_fragment(path, out, model)
    xml = open(out, "r").read()
    assert n >= 4, n
    assert "<results" in xml
    assert "<timestep" not in xml
    dx, dy = _values(xml, "displx"), _values(xml, "disply")
    assert abs(dx[0] - 0.1) < 1e-12 and abs(dx[1] - 0.4) < 1e-12, dx
    assert abs(dy[0] - 0.2) < 1e-12, dy
    mag = _values(xml, "displmag")
    assert abs(mag[0] - (0.1 ** 2 + 0.2 ** 2 + 0.3 ** 2) ** 0.5) < 1e-12
    vm = _values(xml, "vonmises")
    assert vm == [10.0, 20.0] or (abs(vm[0] - 10) < 1e-12 and abs(vm[1] - 20) < 1e-12)
    # Mecway node order of the line is 2, 1, so the element-node stress flips
    stress = _values(xml, "stressxx")
    # nodal SIGM is absent; the element-node block is the second stressxx
    # (only ELNO was written). One element, nodes 2 then 1 -> 7 then 3.
    assert abs(stress[0] - 7.0) < 1e-12 and abs(stress[1] - 3.0) < 1e-12, stress
    _rust_same(path, out, model)
    saved = CONFIG_BRIDGE.get("results_from_med"), CONFIG_BRIDGE.get("exe_aster")
    try:
        CONFIG_BRIDGE["results_from_med"] = False
        CONFIG_BRIDGE["exe_aster"] = r"C:\code_aster\bin\as_run.bat"
        assert host_med_results() is False
        CONFIG_BRIDGE["results_from_med"] = True
        assert host_med_results() is True
    finally:
        CONFIG_BRIDGE["results_from_med"], CONFIG_BRIDGE["exe_aster"] = saved
    print("OK: MED results on the host")
    return 0


if __name__ == "__main__":
    sys.exit(main())
