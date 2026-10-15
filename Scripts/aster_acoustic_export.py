# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# aster_acoustic_export.py
#
# Responsibility: converts the harmonic acoustic result (DYNA_VIBRA
# TYPE_CALCUL='HARM' on PHENOMENE='ACOUSTIQUE', bridge_acoustic.
# build_acoustic_harm) to Mecway's result format, plus the frequency
# response at the microphone nodes (CSV and BRIDGE_MIC lines in the
# .mess). Runs INSIDE the Code-Aster job (CPython 3.11 with numpy, like
# aster_results_export.py), NOT in IronPython.
#
# Code-Aster 17.4 (seen in a run): DYNA_VIBRA returns a result of
# type ACOU_HARMO (FullHarmonicAcousticResult) with, per frequency
# (NUME_ORDRE, access parameter FREQ), the complex field PRES
# (FieldOnNodesComplex, component PRES). Keep the intermediate objects:
# res.getField(..).toSimpleFieldOnNodes().getValues() in one chain once
# gave an <EXCEPTION> DVP_2 (floating point exception), separately not.
#
# Output per frequency is a block
#     <mode id="k" frequency="f Hz">
# (aster_results_export._write_fragment, like the modes: Mecway shows them
# as a list with the frequency) with the node variables
#     pressure       Re(P)   [Pa]  (Mecway's name for the pressure; with
#     pressurei      Im(P)   [Pa]   pressurei like Mecway's complex modes)
#     pressuremag    |P|     [Pa]  amplitude
#     pressurephase  arg(P)  [degrees], -180..180
#     spl            20 log10(|P| / (sqrt(2) p_ref)) [dB], p_ref = 20 uPa
# with p(t) = Re(P e^(i w t)) (Code-Aster; same convention as Mecway's
# complex modes, manual v33 par. 6.9.2). The sound pressure level is based
# on the RMS value |P|/sqrt(2); Code-Aster's PRAC_ELNO DB (ahlv100a) uses
# |P| itself and is therefore 20 log10(sqrt(2)) = 3.0103 dB higher
# (checked: |P| 6.2426 Pa -> DB 109.886).
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

P_REF = 2.0e-5           # Pa, reference pressure in air (ISO 1683)
_SQRT2 = math.sqrt(2.0)
# Lower bound for the log in the sound pressure level (a pressure node has
# p = 0): -200 dB instead of -inf, so no inf/NaN ends up in the .liml.
_SPL_FLOOR = P_REF * 1.0e-10

_CSV_HEAD = {
    "nl": ("microfoon", "frequentie_Hz", "p_re_Pa", "p_im_Pa", "p_amp_Pa",
           "fase_graden", "spl_dB", "knopen"),
    "en": ("microphone", "frequency_Hz", "p_re_Pa", "p_im_Pa", "p_amp_Pa",
           "phase_deg", "spl_dB", "nodes"),
}


def spl(amplitude):
    """Sound pressure level [dB re 20 uPa] of an amplitude |P| (numpy or
    float): 20 log10(|P| / (sqrt(2) p_ref))."""
    a = np.maximum(np.asarray(amplitude, dtype=float) / _SQRT2, _SPL_FLOOR)
    return 20.0 * np.log10(a / P_REF)


class _Harm(object):
    """Complex pressure per frequency (row i = Mecway node i+1); same
    role as aster_results_export._Fields for _write_fragment."""

    def __init__(self, pressures):
        self.pressures = pressures
        self.index = None

    def set_index(self, index):
        self.index = index

    def current(self):
        return self.pressures[self.index]


def _getter(rows, fn):
    def getter(data):
        return fn(data.current()[rows])
    return getter


_VARIABLES = (
    ("pressure", lambda p: p.real),
    ("pressurei", lambda p: p.imag),
    ("pressuremag", lambda p: np.abs(p)),
    ("pressurephase", lambda p: np.degrees(np.angle(p))),
    ("spl", lambda p: spl(np.abs(p))),
)


def _pressures(res, n):
    """({index: complex pressure (n,)}, rows with a value, {index: f})."""
    indexes = list(res.getIndexes())
    acc = res.getAccessParameters()
    freqs = dict(zip(acc["NUME_ORDRE"], acc["FREQ"]))
    out = OrderedDict()
    rows = None
    for idx in indexes:
        fld = res.getField("PRES", idx)
        sf = fld.toSimpleFieldOnNodes()
        vals, mask = sf.getValues()
        col = list(sf.getComponents()).index("PRES")
        p = np.zeros(n, dtype=complex)
        m = np.asarray(mask)[:n, col]
        p[m] = np.asarray(vals)[:n, col][m]
        out[idx] = p
        if rows is None:
            rows = np.nonzero(m)[0]
    return out, rows, freqs


def microphone_rows(pressures, freqs, microphones):
    """
    [(name, f, P, number of nodes)] per microphone and frequency. P is the
    complex pressure of a node; for several nodes the mean of P with the
    root mean square |P| as amplitude (sqrt(mean |P|^2), the energy over
    the nodes; this way a selection at a location with opposite phases
    does not give an apparent silence).
    """
    out = []
    for name, nids in (microphones or {}).items():
        rows = [int(k) - 1 for k in nids]
        for idx, p in pressures.items():
            vals = p[rows]
            mean = complex(vals.mean())
            amp = float(np.sqrt(np.mean(np.abs(vals) ** 2)))
            if abs(mean) > 0.0:
                value = mean / abs(mean) * amp
            else:
                value = complex(amp, 0.0)
            out.append((name, float(freqs.get(idx, idx)), value, len(rows)))
    return out


def export_harmonic(res, out_path, liml_path, microphones=None,
                    csv_path=None, language="en", precision="double"):
    """
    Write the harmonic pressure field as a Mecway <results> fragment (one
    <mode> per frequency) and the microphone response.

    microphones : {name: [Mecway node numbers]} (bridge_acoustic,
                  selections MICROFOON_...), or None.
    csv_path    : CSV with the microphone response (commas, point as
                  decimal separator, like _vergelijking.csv), or None.
    Returns dict with statistics, or None on an error (message in the
    .mess).
    """
    t0 = time.time()
    try:
        return _export(res, out_path, liml_path, microphones, csv_path,
                       language, precision, t0)
    except Exception as e:
        traceback.print_exc()
        print(are.tr("aster_acoustic_export: FOUT: {0}",
                     "aster_acoustic_export: ERROR: {0}").format(e))
        return None


def _export(res, out_path, liml_path, microphones, csv_path, language,
            precision, t0):
    model = are.read_liml_model(liml_path)
    n = model["coords"].shape[0]
    err = are._check_node_order(res.getMesh(), model["coords"])
    if err:
        print(are.tr("aster_acoustic_export: FOUT: {0}",
                     "aster_acoustic_export: ERROR: {0}").format(err))
        return None
    pressures, rows, freqs = _pressures(res, n)
    if not pressures or rows is None or not len(rows):
        print(are.tr("aster_acoustic_export: FOUT: geen drukveld in het "
                     "resultaat.",
                     "aster_acoustic_export: ERROR: no pressure field in the "
                     "result."))
        return None
    ids = (rows + 1).astype("<i4")
    variables = [are._Var(name, False, ids, _getter(rows, fn))
                 for name, fn in _VARIABLES]
    elset_nodes, free_nodes = are._group_nodes(model, n)
    for var in variables:
        are._assign_groups(var, model, elset_nodes, free_nodes)
    data = _Harm(pressures)
    indexes = list(pressures.keys())
    tmp = out_path + ".tmp"
    with open(tmp, "wb") as f:
        are._write_fragment(f, variables, data, indexes, None, precision,
                            model, ("frequency", freqs))
        size = f.tell()
    os.replace(tmp, out_path)
    mic = microphone_rows(pressures, freqs, microphones)
    _print_microphones(mic)
    if csv_path and mic:
        _write_csv(csv_path, mic, language)
    print("BRIDGE_HARM FREQS={0} FMIN={1} FMAX={2} MICROFOONS={3}".format(
        len(indexes), are._num(min(freqs.values())),
        are._num(max(freqs.values())), len(microphones or {})))
    print("aster_acoustic_export: {0} geschreven: {1} frequentie(s), "
          "{2:.1f} MB in {3:.2f} s.".format(out_path, len(indexes),
                                            size / 1.0e6, time.time() - t0))
    return {"stappen": len(indexes), "bytes": size}


def _print_microphones(mic):
    """BRIDGE_MIC lines in the .mess (name last: may contain
    spaces)."""
    for name, f, p, count in mic:
        print("BRIDGE_MIC F={0} RE={1} IM={2} AMP={3} FASE={4} SPL={5} "
              "N={6} NAAM={7}".format(
                  are._num(f), are._num(p.real), are._num(p.imag),
                  are._num(abs(p)), "%.6f" % math.degrees(math.atan2(
                      p.imag, p.real)), "%.6f" % float(spl(abs(p))), count,
                  name))


def _write_csv(path, mic, language):
    head = _CSV_HEAD.get(language, _CSV_HEAD["en"])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(head)
        for name, freq, p, count in mic:
            w.writerow([name, are._num(freq), are._num(p.real),
                        are._num(p.imag), are._num(abs(p)),
                        "%.6f" % math.degrees(math.atan2(p.imag, p.real)),
                        "%.6f" % float(spl(abs(p))), count])
