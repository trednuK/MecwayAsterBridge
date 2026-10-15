# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# aster_spectrum.py
#
# Responsibility: the steps of the response spectrum analysis
# (bridge_spectrum.py) that run INSIDE the Code-Aster job (CPython 3.11
# with numpy, like aster_results_export.py; NOT in IronPython):
#   table()     spectrum value from a Mecway table (linear, constant
#               outside the table), used in the FORMULE per direction;
#   report()    BRIDGE_SPECTRUM_* lines in the .mess: spectral value per
#               mode, effective mass per direction and the combined
#               total reaction force (base shear);
#   maxima()    the maxima of COMB_SISM_MODAL as a result with one
#               index (CREA_RESU DYNA_TRANS: DEPL, ACCE, REAC_NODA,
#               SIGM_ELNO), optionally with the direction combination
#               100-30-30;
#   von_mises() von Mises per node, computed per mode and combined
#               (see there), as extra field SIEQ_NOEU for
#               aster_results_export.
#
# The combination rules are Code-Aster's own: CombModalResponse and
# BaseRunner._comb_directions from code_aster/MacroCommands/
# comb_sism_modal_ops.py (17.4), so the total reaction and von Mises are
# combined with the same formulas as the fields of COMB_SISM_MODAL.
#
# Do not use f-strings: same style as the rest of the bridge.

import math

import numpy as np

from aster_results_export import tr   # language of the messages

# Components of SIGM_NOEU (order for von Mises).
_SIG = ("SIXX", "SIYY", "SIZZ", "SIXY", "SIXZ", "SIYZ")
# COMB_SISM_MODAL OPTION -> NOM_CHAM in the result for Mecway.
_FIELDS = (("DEPL", "DEPL"), ("ACCE_ABSOLU", "ACCE"),
           ("REAC_NODA", "REAC_NODA"), ("SIGM_ELNO", "SIGM_ELNO"))


def table(x, xs, ys):
    """Value of a Mecway table at x: linear between the points, constant
    outside the table (Mecway manual v33 chapter 9, tables)."""
    return float(np.interp(x, xs, ys))


# ==========================================
# MODAL QUANTITIES
# ==========================================
def _modal(modes, amors):
    """(frequencies, {direction: participation factors}, {direction:
    effective mass fraction}) in the order of NUME_ORDRE (CALC_MODES
    PLUS_PETITE: ascending, as COMB_SISM_MODAL sorts them)."""
    para = modes.LIST_PARA()
    freqs = np.array(para["FREQ"], dtype=float)
    gam, frac = {}, {}
    for d in "XYZ":
        gam[d] = np.array(para["FACT_PARTICI_D" + d], dtype=float)
        key = "MASS_EFFE_UN_D" + d
        frac[d] = np.array(para[key], dtype=float) if key in para else None
    return freqs, gam, frac


def _spectral(spec, amors, freqs):
    """(S, w_r) per mode as in BaseRunner.compute (MONO_APPUI): the
    spectrum value times ECHELLE, with CORR_FREQ and NATURE converted to
    an acceleration, and the (possibly damped) angular frequency."""
    s = np.array([spec["spec"](a, f) * spec["scale"]
                  for a, f in zip(amors, freqs)], dtype=float)
    w = 2.0 * np.pi * freqs
    if spec.get("corr_freq") == "OUI":
        c = np.sqrt(1.0 - amors ** 2)
        w = w * c
        s = s * c
    if spec.get("nature") == "DEPL":
        s = (2.0 * np.pi * freqs) ** 2 * s
    elif spec.get("nature") == "VITE":
        s = 2.0 * np.pi * freqs * s
    return s, w


def _s_cut(spec, amor, f_cut):
    """Spectrum value at the cut-off frequency (BaseRunner._s_r_freq_cut)."""
    s = spec["spec"](amor, f_cut) * spec["scale"]
    if spec.get("corr_freq") == "OUI":
        s = s * math.sqrt(1.0 - amor ** 2)
    if spec.get("nature") == "DEPL":
        s = (2.0 * math.pi * f_cut) ** 2 * s
    elif spec.get("nature") == "VITE":
        s = 2.0 * math.pi * f_cut * s
    return s


def _comb_modes(rule, amors, freqs):
    from code_aster.MacroCommands.comb_sism_modal_ops import (
        CombModalResponse)
    return CombModalResponse({"TYPE": rule}, "MONO_APPUI", np.asarray(amors),
                             np.asarray(freqs))


def comb_directions(rule, arrays):
    """Direction combination of the maxima per direction (arrays >= 0):
    'QUAD' (SRSS), 'ABS', 'NEWMARK' (100-40-40, Code-Aster) as in
    BaseRunner._comb_directions, or '100-30-30' (EN 1998-1 par.
    4.3.3.5.2 (4): E_a + 0.30 E_b + 0.30 E_c, the largest over the
    directions a)."""
    arrays = [np.asarray(a, dtype=float) for a in arrays]
    if len(arrays) == 1:
        return arrays[0]
    if rule == "100-30-30":
        total = sum(arrays)
        return np.max([a + 0.3 * (total - a) for a in arrays], axis=0)
    from code_aster.MacroCommands.comb_sism_modal_ops import BaseRunner
    return BaseRunner._comb_directions(rule, arrays)[0]


def _node_values(field, comps):
    """(values n x k, mask n) of a node field for the components
    comps (missing components 0)."""
    sf = field.toSimpleFieldOnNodes()
    vals, mask = sf.getValues()
    names = list(sf.getComponents())
    out = np.zeros((vals.shape[0], len(comps)))
    have = np.zeros(vals.shape[0], dtype=bool)
    for k, c in enumerate(comps):
        if c in names:
            j = names.index(c)
            out[:, k] = np.where(mask[:, j], vals[:, j], 0.0)
            have |= mask[:, j]
    return out, have


def _pseudo_index(psmod, d):
    """NUME_ORDRE of the pseudo-mode of direction d (NOEUD_CMP 'ACCE    X',
    as in BaseRunner._corr_pseudo_mode)."""
    acc = psmod.getAccessParameters()
    for nr, nc in zip(acc["NUME_MODE"], acc["NOEUD_CMP"]):
        if str(nc).split() == ["ACCE", d]:
            return nr
    return None


# ==========================================
# SUMMARY IN THE .MESS
# ==========================================
def report(modes, specs, amors, comb_mode, comb_dir, psmod=None,
           f_cut=None):
    """
    BRIDGE_SPECTRUM lines (read by bridge_spectrum.report_summary):
      BRIDGE_SPECTRUM_MODE <nr> FREQ=.. XI=.. SA_X=.. [SA_Y=..]
      BRIDGE_SPECTRUM_MASSA X=<sum of fractions> ..
      BRIDGE_SPECTRUM_CUT FREQ=.. SA_X=..      (missing mass)
      BRIDGE_SPECTRUM_REACTIE FX=.. FY=.. FZ=..
    The total reaction is the sum of REAC_NODA over all nodes, summed per
    mode (and for the pseudo-mode) and then combined the way
    COMB_SISM_MODAL combines a node field; the sum of the combined
    nodal reactions themselves is larger (maxima without sign).
    """
    try:
        amors = np.asarray(amors, dtype=float)
        freqs, gam, frac = _modal(modes, amors)
        sa = dict((s["dir"], _spectral(s, amors, freqs)) for s in specs)
        for i, f in enumerate(freqs):
            parts = ["BRIDGE_SPECTRUM_MODE {0} FREQ={1:.6g} XI={2:.6g}".format(
                i + 1, f, amors[i])]
            parts += ["SA_{0}={1:.6g}".format(d, sa[d][0][i]) for d in sa]
            print(" ".join(parts))
        print("BRIDGE_SPECTRUM_MASSA " + " ".join(
            "{0}={1:.6g}".format(d, float(np.sum(frac[d])))
            for d in sa if frac[d] is not None))
        if psmod is not None and f_cut is not None:
            print("BRIDGE_SPECTRUM_CUT FREQ={0:.6g} ".format(f_cut) + " ".join(
                "SA_{0}={1:.6g}".format(s["dir"], _s_cut(s, amors[-1], f_cut))
                for s in specs))
        # Total reaction per mode: sum of REAC_NODA over the nodes
        idx = list(modes.getIndexes())
        r_modes = np.array([_node_values(modes.getField("REAC_NODA", k),
                                         ("DX", "DY", "DZ"))[0].sum(axis=0)
                            for k in idx])
        comb = _comb_modes(comb_mode, amors, freqs)
        per_dir = []
        for s in specs:
            d = s["dir"]
            S, w = sa[d]
            r_mi = (S * gam[d] / w ** 2)[:, None] * r_modes
            r_m2, _qs = comb.get(r_mi)
            r_c = np.zeros(3)
            if psmod is not None and f_cut is not None:
                k = _pseudo_index(psmod, d)
                if k is not None:
                    r_ps = _node_values(psmod.getField("REAC_NODA", k),
                                        ("DX", "DY", "DZ"))[0].sum(axis=0)
                    pr = np.sum((gam[d] / (2.0 * np.pi * freqs) ** 2)[:, None]
                                * r_modes, axis=0)
                    r_c = (r_ps - pr) * _s_cut(s, amors[-1], f_cut)
            per_dir.append(np.sqrt(r_m2 + r_c ** 2))
        total = comb_directions(comb_dir, per_dir)
        print("BRIDGE_SPECTRUM_REACTIE FX={0:.6g} FY={1:.6g} FZ={2:.6g}"
              .format(*[float(v) for v in total]))
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(tr("aster_spectrum: WAARSCHUWING: overzicht niet volledig: "
                 "{0}",
                 "aster_spectrum: WARNING: summary not complete: {0}").format(
            e))


# ==========================================
# MAXIMA AS A RESULT
# ==========================================
def maxima(sism, options, comb_dir, dirs, **affe):
    """
    CREA_RESU (TYPE_RESU 'DYNA_TRANS', one index) with the combined
    maxima of COMB_SISM_MODAL (NOM_CAS 'TOTA'); for comb_dir '100-30-30'
    this function combines the directions itself from NOM_CAS 'DIRE_X' ..
    (TYPE_RESU VALE_DIRE). ACCE_ABSOLU is called ACCE in the result. affe:
    MODELE, CHAM_MATER, CARA_ELEM for AFFE.
    """
    from code_aster.Commands import CREA_RESU
    acc = sism.getAccessParameters()
    cases = dict(zip(acc["NOM_CAS"], acc["NUME_ORDRE"]))
    res = None
    for opt, cham in _FIELDS:
        if opt not in options:
            continue
        fld = sism.getField(opt, cases["TOTA"]).copy()
        if comb_dir == "100-30-30" and len(dirs) > 1:
            parts = [np.asarray(sism.getField(opt, cases["DIRE_" + d])
                                .getValues()) for d in dirs]
            fld.setValues(comb_directions("100-30-30", parts))
        kw = dict(OPERATION="AFFE", TYPE_RESU="DYNA_TRANS", NOM_CHAM=cham,
                  AFFE=dict(CHAM_GD=fld, INST=0.0, **affe))
        if res is None:
            res = CREA_RESU(**kw)
        else:
            res = CREA_RESU(reuse=res, RESULTAT=res, **kw)
    return res


class _NodeValues(object):
    """Minimal node field for aster_results_export (_Fields.get):
    toSimpleFieldOnNodes().getValues() / getComponents()."""

    def __init__(self, comps, vals, mask):
        self.comps, self.vals, self.mask = list(comps), vals, mask

    def toSimpleFieldOnNodes(self):
        return self

    def getValues(self):
        return self.vals, self.mask

    def getComponents(self):
        return self.comps


class Result(object):
    """Result for aster_results_export: res (CREA_RESU) plus own
    fields (e.g. von Mises) as extra NOM_CHAM."""

    def __init__(self, res, extra):
        self._res, self._extra = res, dict(extra)

    def getField(self, name, index):
        if name in self._extra:
            return self._extra[name]
        return self._res.getField(name, index)

    def getFieldsNames(self):
        return list(self._res.getFieldsNames()) + list(self._extra)

    def __getattr__(self, name):
        return getattr(self._res, name)


def _vm(sig):
    """von Mises from SIXX SIYY SIZZ SIXY SIXZ SIYZ (rows)."""
    sxx, syy, szz, sxy, sxz, syz = [sig[:, k] for k in range(6)]
    return np.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 +
                          (szz - sxx) ** 2) +
                   3.0 * (sxy ** 2 + sxz ** 2 + syz ** 2))


def von_mises(modes, specs, amors, comb_mode, comb_dir, psmod=None,
              f_cut=None):
    """
    von Mises per node (field SIEQ_NOEU, component VMIS) from SIGM_NOEU of
    the modes (and the pseudo-modes), or None. Per direction: the modal
    contributions R_i = |S_i Gamma_i / w_i^2| VM(sigma_i) combined with the
    modal rule, plus the missing mass VM((sigma_ps - sum Gamma_i/w_i^2
    sigma_i) S_cut) in quadrature (as COMB_SISM_MODAL R_x = sqrt(R_m^2 +
    R_c^2)); then the direction rule. With SRSS this is the expected value
    of sigma^T P sigma (von Mises is a quadratic form, modes
    uncorrelated); with CQC an upper bound (|sigma_i^T P sigma_j| <=
    VM_i VM_j, rho_ij >= 0). Von Mises from the combined components
    (maxima without sign, each at a different moment) is not.
    """
    try:
        amors = np.asarray(amors, dtype=float)
        freqs, gam, _frac = _modal(modes, amors)
        idx = list(modes.getIndexes())
        sig, have = [], None
        for k in idx:
            v, h = _node_values(modes.getField("SIGM_NOEU", k), _SIG)
            sig.append(v)
            have = h if have is None else (have | h)
        vm_modes = np.array([_vm(s) for s in sig])
        comb = _comb_modes(comb_mode, amors, freqs)
        per_dir = []
        for s in specs:
            d = s["dir"]
            S, w = _spectral(s, amors, freqs)
            r_mi = np.abs(S * gam[d] / w ** 2)[:, None] * vm_modes
            r_m2, _qs = comb.get(r_mi)
            r_c2 = 0.0
            if psmod is not None and f_cut is not None:
                k = _pseudo_index(psmod, d)
                if k is not None:
                    resid = _node_values(psmod.getField("SIGM_NOEU", k),
                                         _SIG)[0]
                    for i, si in enumerate(sig):
                        resid = resid - gam[d][i] / (
                            2.0 * np.pi * freqs[i]) ** 2 * si
                    r_c2 = (_vm(resid) * _s_cut(s, amors[-1], f_cut)) ** 2
            per_dir.append(np.sqrt(r_m2 + r_c2))
        total = comb_directions(comb_dir, per_dir)
        return _NodeValues(["VMIS"], total[:, None], have[:, None])
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(tr("aster_spectrum: WAARSCHUWING: von Mises niet berekend: "
                 "{0}",
                 "aster_spectrum: WARNING: von Mises not computed: {0}")
              .format(e))
        return None
