# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# aster_harmonic_export.py
#
# Responsibility: converts the harmonic response of a structure
# (DYNA_VIBRA TYPE_CALCUL='HARM', bridge_harmonic.build_harmonic) to
# Mecway's result format, plus the frequency response at the probes
# (CSV and BRIDGE_PROBE lines in the .mess). Runs INSIDE the Code-Aster job
# (CPython 3.11 with numpy, like aster_results_export.py), NOT in
# IronPython.
#
# Code-Aster 17.4 (seen in a run): REST_GENE_PHYS on a HARM_GENE and
# DYNA_VIBRA HARM PHYS give a DYNA_HARMO with, per frequency (NUME_ORDRE,
# access parameter FREQ), the complex DEPL (components DX DY DZ, and DRX
# DRY DRZ for beams/shells); CALC_CHAMP SIGM_NOEU on it is complex
# (SIXX SIYY SIZZ SIXY SIXZ SIYZ). The time function is u(t) = Re(U e^(i w t))
# (bridge_harmonic, header). Keep the intermediate objects: a chain
# res.getField(..).toSimpleFieldOnNodes().getValues() gave NaN (seen).
#
# Output per frequency is a block <mode id="k" frequency="f Hz">
# (aster_results_export._write_fragment, like S3a) with the node variables
#   displmag            sqrt(|Ux|^2 + |Uy|^2 + |Uz|^2)       [m]
#   displx/y/z          Re(U): the displacement at phase 0   [m]
#   displix/y/z         Im(U)  (like Mecway's pressurei)     [m]
#   displampx/y/z       |U|  (amplitude per direction)       [m]
#   displphasex/y/z     arg(U) [degrees], -180..180; relative to the load
#                       with phase 0; negative = lagging
#   rotx/y/z, rotampx/y/z      beam/shell nodes: Re and amplitude [rad]
#   velmag, velampx/y/z        w |U|        (velocities)
#   accelmag, accelampx/y/z    w^2 |U|      (accelerations)
#   stressxx..zx               Re(S) (phase 0)                [Pa]
#   stressampxx..zx            |S_ij|                         [Pa]
#   vonmises                   largest von Mises stress over a period
# With pressure=True (vibro-acoustics, bridge_vibroacoustic_harm: DEPL also
# has the component PRES on the fluid nodes, U_P_PHI) additionally the
# fields of the harmonic acoustics (aster_acoustic_export, S3a):
#   pressure, pressurei        Re(P), Im(P)                   [Pa]
#   pressuremag, pressurephase |P|, arg(P) [degrees]
#   spl                        20 log10(|P| / (sqrt(2) 20 uPa)) [dB]
# and the microphones (CSV and BRIDGE_MIC lines like aster_acoustic_export).
# Largest von Mises over a period: sigma(theta) = Re(S e^(i theta)) =
# R cos(theta) - I sin(theta) and q = sigma_vm^2 is a quadratic form,
# so q(theta) = (q_RR + q_II)/2 + (q_RR - q_II)/2 cos 2 theta - q_RI
# sin 2 theta, with maximum (q_RR + q_II)/2 + sqrt(((q_RR - q_II)/2)^2 +
# q_RI^2) (exact; R and I in phase: the von Mises of |S|). Based on the
# node-averaged stress SIGM_NOEU (Code-Aster's SIEQ_NOEU averages the von
# Mises per element; equal for a fine mesh).
#
# Do not use f-strings: same style as the rest of the bridge.

import csv
import math
import os
import time
import traceback
from collections import OrderedDict

import numpy as np

import aster_results_export as are

_XYZ = ("x", "y", "z")
_DISP = ("DX", "DY", "DZ")
_ROT = ("DRX", "DRY", "DRZ")
_SIG = (("SIXX", "xx"), ("SIYY", "yy"), ("SIZZ", "zz"),
        ("SIXY", "xy"), ("SIYZ", "yz"), ("SIXZ", "zx"))

_CSV_HEAD = {
    "nl": ("meetpunt", "frequentie_Hz", "u_amp_m", "a_amp_m_s2",
           "ux_re_m", "ux_im_m", "uy_re_m", "uy_im_m", "uz_re_m", "uz_im_m",
           "ux_amp_m", "uy_amp_m", "uz_amp_m", "ux_fase_graden",
           "uy_fase_graden", "uz_fase_graden", "knopen"),
    "en": ("probe", "frequency_Hz", "u_amp_m", "a_amp_m_s2",
           "ux_re_m", "ux_im_m", "uy_re_m", "uy_im_m", "uz_re_m", "uz_im_m",
           "ux_amp_m", "uy_amp_m", "uz_amp_m", "ux_phase_deg",
           "uy_phase_deg", "uz_phase_deg", "nodes"),
}


def von_mises_max(s):
    """Largest von Mises stress over a period of the complex
    stress s (..., 6) in the order xx yy zz xy yz zx (see header)."""
    r, i = s.real, s.imag

    def q(a, b):
        return (0.5 * ((a[..., 0] - a[..., 1]) * (b[..., 0] - b[..., 1]) +
                       (a[..., 1] - a[..., 2]) * (b[..., 1] - b[..., 2]) +
                       (a[..., 2] - a[..., 0]) * (b[..., 2] - b[..., 0])) +
                3.0 * (a[..., 3] * b[..., 3] + a[..., 4] * b[..., 4] +
                       a[..., 5] * b[..., 5]))
    qrr, qii, qri = q(r, r), q(i, i), q(r, i)
    top = 0.5 * (qrr + qii) + np.sqrt((0.5 * (qrr - qii)) ** 2 + qri ** 2)
    return np.sqrt(np.maximum(top, 0.0))


class _HarmFields(object):
    """Complex DEPL and SIGM_NOEU per frequency (row i = Mecway node
    i+1); the role of aster_results_export._Fields for _write_fragment."""

    def __init__(self, res, n, freqs):
        self.res = res
        self.n = n
        self.freqs = freqs
        self.index = None
        self.cache = {}

    def set_index(self, index):
        self.index = index
        self.cache = {}

    def omega(self):
        return 2.0 * math.pi * float(self.freqs.get(self.index, 0.0))

    def field(self, name):
        """(components, complex values (n, ncmp), mask) or None."""
        if name not in self.cache:
            self.cache[name] = None
            try:
                fld = self.res.getField(name, self.index)
            except Exception:
                return None
            sf = fld.toSimpleFieldOnNodes()
            vals, mask = sf.getValues()
            vals = np.array(vals, dtype=complex)[:self.n]
            mask = np.array(mask, dtype=bool)[:self.n]
            self.cache[name] = (list(sf.getComponents()), vals, mask)
        return self.cache[name]

    def column(self, name, cmp_):
        d = self.field(name)
        if d is None or cmp_ not in d[0]:
            return None
        return d[1][:, d[0].index(cmp_)]


def _rows(data, name, cmps):
    """Rows (node index) where all components cmps have a value."""
    d = data.field(name)
    if d is None or not all(c in d[0] for c in cmps):
        return None
    ok = np.ones(data.n, dtype=bool)
    for c in cmps:
        ok &= d[2][:, d[0].index(c)]
    rows = np.nonzero(ok)[0]
    return rows if len(rows) else None


def _var(name, rows, fn):
    def getter(data):
        return fn(data, rows)
    return are._Var(name, False, (rows + 1).astype("<i4"), getter)


def _cmp_fn(field, cmp_, part):
    def fn(data, rows):
        col = data.column(field, cmp_)
        if col is None:
            return None
        v = col[rows]
        if part == "re":
            return v.real
        if part == "im":
            return v.imag
        if part == "amp":
            return np.abs(v)
        if part == "phase":
            return np.degrees(np.angle(v))
        if part == "vel":
            return data.omega() * np.abs(v)
        return data.omega() ** 2 * np.abs(v)        # "acc"
    return fn


def _mag_fn(field, cmps, power):
    def fn(data, rows):
        cols = [data.column(field, c) for c in cmps]
        if any(c is None for c in cols):
            return None
        amp = np.sqrt(sum(np.abs(c[rows]) ** 2 for c in cols))
        return data.omega() ** power * amp
    return fn


def _vm_fn():
    def fn(data, rows):
        cols = [data.column("SIGM_NOEU", c) for c, _s in _SIG]
        if any(c is None for c in cols):
            return None
        return von_mises_max(np.stack([c[rows] for c in cols], axis=-1))
    return fn


def _pres_fn(part):
    def fn(data, rows):
        col = data.column("DEPL", "PRES")
        if col is None:
            return None
        v = col[rows]
        if part == "re":
            return v.real
        if part == "im":
            return v.imag
        if part == "amp":
            return np.abs(v)
        if part == "phase":
            return np.degrees(np.angle(v))
        import aster_acoustic_export
        return aster_acoustic_export.spl(np.abs(v))      # "spl"
    return fn


def _plan(data, fields, pressure=False):
    """List of _Var in Mecway order (size for the components)."""
    out = []
    rows = _rows(data, "DEPL", _DISP)
    if rows is not None:
        out.append(_var("displmag", rows, _mag_fn("DEPL", _DISP, 0)))
        for part, prefix in (("re", "displ"), ("im", "displi"),
                             ("amp", "displamp"), ("phase", "displphase")):
            out += [_var(prefix + s, rows, _cmp_fn("DEPL", c, part))
                    for c, s in zip(_DISP, _XYZ)]
        if "velocities" in fields:
            out.append(_var("velmag", rows, _mag_fn("DEPL", _DISP, 1)))
            out += [_var("velamp" + s, rows, _cmp_fn("DEPL", c, "vel"))
                    for c, s in zip(_DISP, _XYZ)]
        if "accelerations" in fields:
            out.append(_var("accelmag", rows, _mag_fn("DEPL", _DISP, 2)))
            out += [_var("accelamp" + s, rows, _cmp_fn("DEPL", c, "acc"))
                    for c, s in zip(_DISP, _XYZ)]
    rrows = _rows(data, "DEPL", _ROT)
    if rrows is not None:
        out += [_var("rot" + s, rrows, _cmp_fn("DEPL", c, "re"))
                for c, s in zip(_ROT, _XYZ)]
        out += [_var("rotamp" + s, rrows, _cmp_fn("DEPL", c, "amp"))
                for c, s in zip(_ROT, _XYZ)]
    srows = _rows(data, "SIGM_NOEU", [c for c, _s in _SIG])
    if srows is not None:
        if "stresses" in fields:
            out += [_var("stress" + s, srows, _cmp_fn("SIGM_NOEU", c, "re"))
                    for c, s in _SIG]
            out += [_var("stressamp" + s, srows,
                         _cmp_fn("SIGM_NOEU", c, "amp")) for c, s in _SIG]
        if "vonmises" in fields:
            out.append(_var("vonmises", srows, _vm_fn()))
    elif any(f in fields for f in ("stresses", "vonmises")):
        print(are.tr("aster_harmonic_export: geen SIGM_NOEU in het "
                     "resultaat; geen spanningen.",
                     "aster_harmonic_export: no SIGM_NOEU in the result; no "
                     "stresses."))
    prows = _rows(data, "DEPL", ("PRES",)) if pressure else None
    if prows is not None:
        out += [_var(name, prows, _pres_fn(part)) for name, part in (
            ("pressure", "re"), ("pressurei", "im"), ("pressuremag", "amp"),
            ("pressurephase", "phase"), ("spl", "spl"))]
    elif pressure:
        print(are.tr("aster_harmonic_export: geen PRES in DEPL; geen druk.",
                     "aster_harmonic_export: no PRES in DEPL; no "
                     "pressure."))
    return out


def _pressures(data, indexes):
    """{index: complex pressure (n,)} (0 where no PRES) for the microphones
    (aster_acoustic_export.microphone_rows)."""
    out = OrderedDict()
    for idx in indexes:
        data.set_index(idx)
        d = data.field("DEPL")
        p = np.zeros(data.n, dtype=complex)
        if d is not None and "PRES" in d[0]:
            k = d[0].index("PRES")
            m = d[2][:, k]
            p[m] = d[1][m, k]
        out[idx] = p
    return out


def probe_rows(data, indexes, probes):
    """
    [(name, f, [Ux, Uy, Uz] complex, number of nodes)] per probe and
    frequency. For several nodes, per component the mean of U with the
    root mean square |U| as amplitude (sqrt(mean |U|^2), like
    the microphones of aster_acoustic_export).
    """
    out = []
    for idx in indexes:
        data.set_index(idx)
        f = float(data.freqs.get(idx, idx))
        cols = [data.column("DEPL", c) for c in _DISP]
        if any(c is None for c in cols):
            continue
        for name, nids in (probes or {}).items():
            rows = [int(k) - 1 for k in nids if 0 < int(k) <= data.n]
            if not rows:
                continue
            vals = []
            for c in cols:
                v = c[rows]
                mean = complex(v.mean())
                amp = float(np.sqrt(np.mean(np.abs(v) ** 2)))
                vals.append(mean / abs(mean) * amp if abs(mean) > 0.0
                            else complex(amp, 0.0))
            out.append((name, f, vals, len(rows)))
    return out


def export_harmonic(res, out_path, liml_path, fields=None, probes=None,
                    csv_path=None, language="en", basis="GENE",
                    precision="single", pressure=False, microphones=None,
                    mic_csv_path=None):
    """
    Write the harmonic response as a Mecway <results> fragment (one
    <mode> per frequency) and the probes.

    fields   : groups ("displacements", "velocities", "accelerations",
               "stresses", "vonmises"); None = all.
    probes   : {name: [Mecway node numbers]} (bridge_harmonic, selections
               MEETPUNT_... / PROBE_...), or None.
    csv_path : CSV with the frequency response per probe, or None.
    pressure : also the pressure (component PRES of DEPL, vibro-acoustics).
    microphones, mic_csv_path : {name: [node numbers]} and the CSV of the
               microphones (like aster_acoustic_export), or None.
    Returns dict with statistics, or None on an error (message in the
    .mess).
    """
    t0 = time.time()
    try:
        return _export(res, out_path, liml_path, fields, probes, csv_path,
                       language, basis, precision, t0, pressure,
                       microphones, mic_csv_path)
    except Exception as e:
        traceback.print_exc()
        print(are.tr("aster_results_export: FOUT: aster_harmonic_export: "
                     "{0}",
                     "aster_results_export: ERROR: aster_harmonic_export: "
                     "{0}").format(e))
        return None


def _export(res, out_path, liml_path, fields, probes, csv_path, language,
            basis, precision, t0, pressure=False, microphones=None,
            mic_csv_path=None):
    model = are.read_liml_model(liml_path)
    n = model["coords"].shape[0]
    err = are._check_node_order(res.getMesh(), model["coords"])
    if err:
        print(are.tr("aster_results_export: FOUT: {0}",
                     "aster_results_export: ERROR: {0}").format(err))
        return None
    if fields is None:
        fields = ["displacements", "velocities", "accelerations",
                  "stresses", "vonmises"]
    acc = res.getAccessParameters()
    freqs = dict(zip(acc["NUME_ORDRE"], acc["FREQ"]))
    indexes = list(res.getIndexes())
    if not indexes:
        print(are.tr("aster_results_export: FOUT: geen frequenties in het "
                     "resultaat.",
                     "aster_results_export: ERROR: no frequencies in the "
                     "result."))
        return None
    data = _HarmFields(res, n, freqs)
    data.set_index(indexes[0])
    variables = _plan(data, fields, pressure)
    if not variables:
        print(are.tr("aster_results_export: FOUT: geen verplaatsingsveld in "
                     "het resultaat.",
                     "aster_results_export: ERROR: no displacement field in "
                     "the result."))
        return None
    elset_nodes, free_nodes = are._group_nodes(model, n)
    for var in variables:
        are._assign_groups(var, model, elset_nodes, free_nodes)
    tmp = out_path + ".tmp"
    with open(tmp, "wb") as f:
        are._write_fragment(f, variables, data, indexes, None, precision,
                            model, ("frequency", freqs))
        size = f.tell()
    os.replace(tmp, out_path)
    rows = probe_rows(data, indexes, probes)
    _print_probes(rows)
    if csv_path and rows:
        _write_csv(csv_path, rows, language)
    if microphones:
        import aster_acoustic_export as aae
        mic = aae.microphone_rows(_pressures(data, indexes), freqs,
                                  microphones)
        aae._print_microphones(mic)
        if mic_csv_path and mic:
            aae._write_csv(mic_csv_path, mic, language)
    print("BRIDGE_HARM FREQS={0} FMIN={1} FMAX={2} MEETPUNTEN={3} "
          "BASIS={4}".format(len(indexes), are._num(min(freqs.values())),
                             are._num(max(freqs.values())),
                             len(probes or {}), basis))
    print("aster_harmonic_export: {0} geschreven: {1} frequentie(s), {2} "
          "variabelen ({3}), {4:.1f} MB in {5:.2f} s.".format(
              out_path, len(indexes), len(variables),
              ", ".join(v.name for v in variables), size / 1.0e6,
              time.time() - t0))
    return {"stappen": len(indexes), "bytes": size,
            "variabelen": [v.name for v in variables]}


def _amp(vals):
    return math.sqrt(sum(abs(v) ** 2 for v in vals))


def _print_probes(rows):
    """BRIDGE_PROBE lines in the .mess (name last: may contain
    spaces)."""
    for name, f, vals, count in rows:
        w = 2.0 * math.pi * f
        print("BRIDGE_PROBE F={0} UAMP={1} AAMP={2} {3} N={4} NAAM={5}"
              .format(are._num(f), are._num(_amp(vals)),
                      are._num(w * w * _amp(vals)),
                      " ".join("U{0}={1},{2}".format(
                          s.upper(), are._num(v.real), are._num(v.imag))
                          for s, v in zip(_XYZ, vals)), count, name))


def _write_csv(path, rows, language):
    head = _CSV_HEAD.get(language, _CSV_HEAD["en"])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(head)
        for name, freq, vals, count in rows:
            om = 2.0 * math.pi * freq
            row = [name, are._num(freq), are._num(_amp(vals)),
                   are._num(om * om * _amp(vals))]
            for v in vals:
                row += [are._num(v.real), are._num(v.imag)]
            row += [are._num(abs(v)) for v in vals]
            row += ["%.6f" % math.degrees(math.atan2(v.imag, v.real))
                    for v in vals]
            row.append(count)
            w.writerow(row)
