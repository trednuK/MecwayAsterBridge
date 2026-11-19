# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_fast.py
# Optional Rust helper (rust/aster_fast) for the two slow steps on a
# large mesh under IronPython 2.7:
#   aster_fast prep  streams the .liml into a slim XML plus mesh.bin
#   aster_fast mail  writes the ASTER .mail (same bytes as the Python writer)
# Without the executable the pure Python path is used. ASTER_FAST=0
# switches the helper off; ASTER_FAST=/path/to/aster_fast picks one.
# Build: cargo build --release --manifest-path rust/aster_fast/Cargo.toml
# Copy target/release/aster_fast (or aster_fast.exe) next to this file
# if Mecway does not see the build directory.
# Compatible with IronPython 2.7.9.

import array
import os
import struct
import subprocess
import sys
import tempfile

from bridge_utils import log


def find_exe():
    """Path of aster_fast, or None when the fast path is off or absent."""
    chosen = os.environ.get("ASTER_FAST")
    if chosen == "0":
        return None
    if chosen and os.path.isfile(chosen):
        return chosen
    here = os.path.dirname(os.path.abspath(__file__))
    names = ("aster_fast.exe", "aster_fast")
    rel = os.path.join(here, "..", "rust", "aster_fast", "target", "release")
    for name in names:
        for folder in (here, rel):
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                return path
    path_env = os.environ.get("PATH", "")
    for folder in path_env.split(os.pathsep):
        if not folder:
            continue
        for name in names:
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                return path
    return None


def prepare(liml_path):
    """(slim path, bin path) or None. Caller deletes both."""
    exe = find_exe()
    if not exe:
        return None
    slim = bin_path = None
    try:
        fd, slim = tempfile.mkstemp(prefix="mwfast_", suffix=".liml")
        os.close(fd)
        fd, bin_path = tempfile.mkstemp(prefix="mwfast_", suffix=".bin")
        os.close(fd)
        proc = subprocess.Popen(
            [exe, "prep", liml_path, slim, bin_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _out, err = proc.communicate()
        if proc.returncode != 0:
            log("WARNING: aster_fast prep failed ({0}); reading the .liml "
                "in Python. {1}".format(proc.returncode, _err_text(err)))
            cleanup(slim, bin_path)
            return None
        return slim, bin_path
    except Exception as exc:
        log("WARNING: aster_fast prep could not start ({0}); reading the "
            ".liml in Python.".format(exc))
        cleanup(slim, bin_path)
        return None


def cleanup(slim, bin_path):
    for path in (slim, bin_path):
        if path and os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass


def load_mesh(bin_path, model_data):
    """Fill mesh fields from mesh.bin. Returns the elset tables the
    Python loop used to build, for _split_trusses."""
    from bridge_from_liml import (_DIM_1D_SHAPES, _DIM_3D_SHAPES,
                                  _parse_beam_orientation, parse_and_convert)
    if (sys.byteorder != "little" or array.array("I").itemsize != 4 or
            array.array("d").itemsize != 8):
        raise ValueError("mesh.bin needs a little-endian runtime")
    data = open(bin_path, "rb").read()
    r = _Reader(data)
    magic = r.raw(7)
    if magic != b"MWFAST1":
        raise ValueError("bad mesh.bin")
    elset_shapes_map = {}
    truss_eids = {}
    line_eids = {}
    n_nodes = r.u32()
    nids = _array(r, "I", n_nodes)
    xyz = _array(r, "d", n_nodes * 3)
    mesh_nodes = model_data["mesh_nodes"]
    for i in range(n_nodes):
        mesh_nodes[nids[i]] = (xyz[i * 3], xyz[i * 3 + 1], xyz[i * 3 + 2])
    n_elsets = r.u32()
    for _e in range(n_elsets):
        ename = r.text()
        shapes = set()
        n_elems = r.u32()
        for _j in range(n_elems):
            eid = r.u32()
            shape = r.text()
            n_conn = r.u32()
            enodes = [r.u32() for _k in range(n_conn)]
            flags = r.u8()
            attrs = {}
            for bit, key in ((1, "orientationux"), (2, "orientationuy"),
                             (3, "orientationuz"), (4, "orientationvx"),
                             (5, "orientationvy"), (6, "orientationvz")):
                if flags & (1 << bit):
                    attrs[key] = r.text()
            angle = r.text() if flags & (1 << 7) else None
            if angle is not None:
                attrs["angle"] = angle
            truss = bool(flags & 1)
            if shape:
                shapes.add(shape)
                if shape in _DIM_1D_SHAPES:
                    line_eids.setdefault(ename, set()).add(eid)
                    if truss:
                        truss_eids.setdefault(ename, set()).add(eid)
                model_data["elem_shapes"][eid] = shape
                model_data["mesh_elements"].append(
                    (eid, shape, enodes, ename))
                if any(k in attrs for k in (
                        "orientationux", "orientationuy", "orientationuz")):
                    model_data.setdefault("elem_u_axes", {})[eid] = tuple(
                        float(attrs.get(k, "0")) for k in (
                            "orientationux", "orientationuy", "orientationuz"))
                if shape in _DIM_3D_SHAPES:
                    if any(k in attrs for k in (
                            "orientationvx", "orientationvy",
                            "orientationvz")):
                        model_data.setdefault("elem_v_axes", {})[eid] = tuple(
                            float(attrs.get(k, "0")) for k in (
                                "orientationvx", "orientationvy",
                                "orientationvz"))
                    if "angle" in attrs:
                        model_data.setdefault("elem_angles", {})[eid] = \
                            parse_and_convert(attrs["angle"], "angle")
                if shape in _DIM_1D_SHAPES and not truss:
                    orient = _parse_beam_orientation(_Attr(eid, attrs))
                    if orient is not None:
                        model_data["beam_orientations"][eid] = orient
        n_extra = r.u32()
        for _k in range(n_extra):
            shapes.add(r.text())
        elset_shapes_map[ename] = shapes
    _read_faces(r, model_data)
    _read_id_sel(r, model_data, "element_selections", False)
    _read_node_groups(r, model_data)
    log("INFO: Mesh read with aster_fast: {0} nodes, {1} elements.".format(
        len(model_data["mesh_nodes"]), len(model_data["mesh_elements"])))
    model_data["_fast_mesh"] = True
    return elset_shapes_map, truss_eids, line_eids


def write_mail(mail_path, nids, nodes, extra_nodes, by_type, group_ma,
               group_no):
    """Write the ASTER mesh with aster_fast. False: caller uses Python."""
    exe = find_exe()
    if not exe:
        return False
    if array.array("I").itemsize != 4 or array.array("d").itemsize != 8:
        return False
    if sys.byteorder != "little":
        return False
    try:
        proc = subprocess.Popen(
            [exe, "mail", mail_path],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        stdin = proc.stdin
        # communicate() flushes stdin; closing it first breaks on CPython 3.
        proc.stdin = None
        _write_job(stdin, nids, nodes, extra_nodes, by_type,
                   group_ma, group_no)
        stdin.close()
        _out, err = proc.communicate()
        if proc.returncode != 0:
            log("WARNING: aster_fast mail failed ({0}); writing the mesh "
                "in Python. {1}".format(proc.returncode, _err_text(err)))
            return False
        return True
    except Exception as exc:
        log("WARNING: aster_fast mail could not start ({0}); writing the "
            "mesh in Python.".format(exc))
        return False


def _array(r, typecode, n_items):
    """Native array of n_items. mesh.bin is little-endian, same as Mecway."""
    arr = array.array(typecode)
    raw = r.raw(n_items * arr.itemsize)
    if sys.version_info[0] >= 3:
        arr.frombytes(raw)
    else:
        arr.fromstring(raw)
    return arr


class _Attr(object):
    """elem.get() for _parse_beam_orientation."""

    def __init__(self, eid, attrs):
        self._eid = eid
        self._a = attrs

    def get(self, key, default=None):
        if key == "eid":
            return str(self._eid)
        if key in self._a:
            return self._a[key]
        return default


class _Reader(object):

    def __init__(self, data):
        self.d = data
        self.i = 0

    def raw(self, n):
        b = self.d[self.i:self.i + n]
        self.i += n
        return b

    def u32(self):
        v = struct.unpack_from("<I", self.d, self.i)[0]
        self.i += 4
        return v

    def u8(self):
        v = self.d[self.i]
        self.i += 1
        if not isinstance(v, int):
            v = ord(v)
        return v

    def f64(self):
        v = struct.unpack_from("<d", self.d, self.i)[0]
        self.i += 8
        return v

    def text(self):
        n = self.u32()
        b = self.raw(n)
        if not isinstance(b, str):
            return b.decode("utf-8")
        try:
            return b.decode("utf-8")
        except AttributeError:
            return b


def _read_faces(r, model_data):
    n = r.u32()
    for _i in range(n):
        name = r.text()
        n_faces = r.u32()
        faces = []
        eids = []
        for _k in range(n_faces):
            eid = r.u32()
            faceid = r.u32()
            eids.append(eid)
            faces.append((eid, faceid))
        if name:
            model_data["face_selections"][name] = eids
            model_data["face_selection_faces"][name] = faces


def _read_id_sel(r, model_data, key, _unused):
    n = r.u32()
    for _i in range(n):
        name = r.text()
        n_ids = r.u32()
        ids = [r.u32() for _k in range(n_ids)]
        if name:
            model_data[key][name] = ids


def _read_node_groups(r, model_data):
    n = r.u32()
    for _i in range(n):
        name = r.text()
        n_ids = r.u32()
        ids = [r.text() for _k in range(n_ids)]
        if name and ids:
            model_data["node_groups"][name] = [
                "N{0}".format(i) for i in ids]
            log("INFO: NodeGroup '{0}' -> {1} nodes".format(name, len(ids)))


def _write_job(out, nids, nodes, extra_nodes, by_type, group_ma, group_no):
    _write_coords(out, [(nid, nodes[nid]) for nid in nids])
    _write_coords(out, extra_nodes)
    _pack(out, "<I", len(by_type))
    for atype, items in by_type.items():
        _write_str(out, atype)
        _pack(out, "<I", len(items))
        for name, cn in items:
            _write_str(out, name)
            _pack(out, "<I", len(cn))
            if cn:
                arr = array.array("I", [int(n) for n in cn])
                if sys.version_info[0] >= 3:
                    out.write(arr.tobytes())
                else:
                    out.write(arr.tostring())
    _pack(out, "<I", 2)
    for kind, groups in (("GROUP_MA", group_ma), ("GROUP_NO", group_no)):
        _write_str(out, kind)
        _pack(out, "<I", len(groups))
        for name, members in groups.items():
            _write_str(out, name)
            _pack(out, "<I", len(members))
            for member in members:
                _write_str(out, member)


def _write_coords(out, pairs):
    nids = array.array("I")
    xyz = array.array("d")
    for nid, coords in pairs:
        nids.append(int(nid))
        xyz.append(float(coords[0]))
        xyz.append(float(coords[1]))
        xyz.append(float(coords[2]))
    _pack(out, "<I", len(nids))
    if sys.version_info[0] >= 3:
        out.write(nids.tobytes())
        out.write(xyz.tobytes())
    else:
        out.write(nids.tostring())
        out.write(xyz.tostring())


def _write_str(out, text):
    if not isinstance(text, bytes):
        text = text.encode("utf-8")
    _pack(out, "<I", len(text))
    out.write(text)


def _pack(out, fmt, value):
    out.write(struct.pack(fmt, value))


def _err_text(err):
    if not err:
        return ""
    if not isinstance(err, str):
        err = err.decode("utf-8", "replace")
    err = err.strip()
    if len(err) > 400:
        err = err[:400]
    return err
