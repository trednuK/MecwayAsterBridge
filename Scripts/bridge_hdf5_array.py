# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# The slice of NumPy that the vendored HDF5 reader (bridge_hdf5_low.py)
# uses. IronPython 2.7 has no NumPy; this stays inside the bridge.
from __future__ import division

import math
import struct


class DType(object):
    """A little- or big-endian numeric dtype, or a fixed byte string."""

    def __init__(self, spec):
        if isinstance(spec, DType):
            spec = spec.spec
        self.spec = spec
        if spec[0:1] == "S" or spec[0:2] == "|S":
            self.kind = "S"
            self.itemsize = int(spec[1:] if spec[0] == "S" else spec[2:])
            self._code = None
            return
        order = spec[0] if spec[0] in "<>=" else "<"
        body = spec[1:] if spec[0] in "<>=" else spec
        # NumPy codes (f8 = 8-byte float). struct uses f/d and i/q.
        numpy_to_struct = {
            "f4": "f", "f8": "d",
            "i1": "b", "i2": "h", "i4": "i", "i8": "q",
            "u1": "B", "u2": "H", "u4": "I", "u8": "Q",
        }
        code = numpy_to_struct.get(body, body)
        self.kind = "n"
        self._code = order + code
        self.itemsize = struct.calcsize(self._code)

    def __repr__(self):
        return "DType(%r)" % (self.spec,)


class Array(object):
    """C-order numeric array backed by a bytearray."""

    def __init__(self, raw, dtype, shape):
        self.dtype = dtype if isinstance(dtype, DType) else DType(dtype)
        self.shape = tuple(int(x) for x in shape)
        need = self.dtype.itemsize * _prod(self.shape)
        if isinstance(raw, Array):
            raw = raw._b
        buf = bytearray(raw)
        if len(buf) < need:
            buf.extend(b"\x00" * (need - len(buf)))
        self._b = buf[:need]

    def __len__(self):
        return self.shape[0] if self.shape else 1

    def reshape(self, shape):
        if isinstance(shape, int):
            shape = (shape,)
        if _prod(shape) != _prod(self.shape):
            raise ValueError("cannot reshape %s into %s" % (self.shape, shape))
        return Array(self._b, self.dtype, shape)

    def __getitem__(self, key):
        if key is Ellipsis or key == slice(None):
            return self._flat_list() if self.dtype.kind == "n" else self._bytes_list()
        if isinstance(key, int):
            return self._at(_offset_of((key,), self.shape))
        if isinstance(key, slice) and len(self.shape) == 1:
            return self._slice1(key)
        if isinstance(key, tuple):
            return self._tuple_get(key)
        raise TypeError("unsupported index %r" % (key,))

    def __setitem__(self, key, value):
        if isinstance(key, tuple):
            self._tuple_set(key, value)
            return
        raise TypeError("unsupported index %r" % (key,))

    def _flat_list(self):
        n = _prod(self.shape)
        out = []
        size = self.dtype.itemsize
        code = self.dtype._code
        for i in range(n):
            out.append(struct.unpack_from(code, self._b, i * size)[0])
        return out

    def _bytes_list(self):
        n = _prod(self.shape)
        size = self.dtype.itemsize
        return [bytes(self._b[i * size:(i + 1) * size]) for i in range(n)]

    def _at(self, index):
        size = self.dtype.itemsize
        raw = self._b[index * size:(index + 1) * size]
        if self.dtype.kind == "S":
            return bytes(raw)
        return struct.unpack(self.dtype._code, raw)[0]

    def _slice1(self, key):
        start, stop, step = key.indices(self.shape[0])
        if step != 1:
            return [self._at(i) for i in range(start, stop, step)]
        view = Array(self._b[start * self.dtype.itemsize:
                              stop * self.dtype.itemsize],
                     self.dtype, (stop - start,))
        return view._flat_list() if self.dtype.kind == "n" else view._bytes_list()

    def _tuple_get(self, key):
        # Only a full slice per axis (the reader's padding trim).
        ranges = []
        for i, part in enumerate(key):
            n = self.shape[i]
            if isinstance(part, slice):
                a, b, s = part.indices(n)
                if s != 1:
                    raise TypeError("only step-1 slices")
                ranges.append(range(a, b))
            else:
                ranges.append((int(part),))
        out_shape = tuple(len(r) for r in ranges)
        out = zeros(out_shape, self.dtype)
        for idx in _product(ranges):
            out._store(_offset_of(idx, out_shape), self._at(_offset_of(idx, self.shape)))
        return out

    def _tuple_set(self, key, value):
        ranges = []
        for i, part in enumerate(key):
            n = self.shape[i]
            if not isinstance(part, slice):
                raise TypeError("only slices in assignment")
            a, b, s = part.indices(n)
            if s != 1:
                raise TypeError("only step-1 slices")
            ranges.append(range(a, b))
        src = value if isinstance(value, Array) else Array(
            _pack(value, self.dtype), self.dtype,
            tuple(len(r) for r in ranges))
        src_ranges = [range(n) for n in src.shape]
        for dst_idx, src_idx in zip(_product(ranges), _product(src_ranges)):
            self._store(_offset_of(dst_idx, self.shape),
                        src._at(_offset_of(src_idx, src.shape)))

    def _store(self, index, number):
        size = self.dtype.itemsize
        if self.dtype.kind == "S":
            raw = number if isinstance(number, (bytes, bytearray)) else bytes(number)
            raw = raw[:size].ljust(size, b"\x00")
        else:
            raw = struct.pack(self.dtype._code, number)
        self._b[index * size:(index + 1) * size] = raw


def _prod(shape):
    n = 1
    for x in shape:
        n *= int(x)
    return n


def _offset_of(idx, shape):
    off = 0
    stride = 1
    for i in range(len(shape) - 1, -1, -1):
        off += idx[i] * stride
        stride *= shape[i]
    return off


def _product(ranges):
    if not ranges:
        yield ()
        return
    for head in ranges[0]:
        for tail in _product(ranges[1:]):
            yield (head,) + tail


def _pack(seq, dtype):
    flat = list(seq) if not isinstance(seq, Array) else seq._flat_list()
    return b"".join(struct.pack(dtype._code, x) for x in flat)


def dtype(spec):
    return DType(spec)


def prod(shape):
    if isinstance(shape, int):
        return shape
    return _prod(shape)


def zeros(shape, dtype):
    if isinstance(shape, int):
        shape = (shape,)
    dt = DType(dtype)
    return Array(bytearray(_prod(shape) * dt.itemsize), dt, shape)


def empty(count, dtype=None):
    return [None] * int(count)


def frombuffer(buf, dtype, count=None, offset=0):
    dt = DType(dtype)
    if isinstance(buf, Array):
        buf = buf._b
    raw = buf[offset:]
    if count is not None:
        raw = raw[:int(count) * dt.itemsize]
    n = len(raw) // dt.itemsize
    return Array(raw, dt, (n,))


def fromstring(buf, dtype, count=None):
    return frombuffer(buf, dtype, count=count, offset=0)


def memmap(fh, dtype, mode="c", offset=0, shape=(), order="C"):
    dt = DType(dtype)
    n = _prod(shape)
    fh.seek(offset)
    raw = fh.read(n * dt.itemsize)
    return Array(raw, dt, shape)


def ceil(x):
    return math.ceil(x)


def array(seq):
    return list(seq)


def vectorize(func):
    def run(data):
        return [func(x) for x in data._flat_list()]
    return run


class np(object):
    """Namespace so the vendored reader can say np.zeros."""
    dtype = staticmethod(dtype)
    prod = staticmethod(prod)
    zeros = staticmethod(zeros)
    empty = staticmethod(empty)
    frombuffer = staticmethod(frombuffer)
    fromstring = staticmethod(fromstring)
    memmap = staticmethod(memmap)
    ceil = staticmethod(ceil)
    array = staticmethod(array)
    vectorize = staticmethod(vectorize)
    object = object
