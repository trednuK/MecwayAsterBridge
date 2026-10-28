# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test of Mecway's result formulas in the bridge (STAPPENPLAN S33,
# GitHub issue #8):
#   - bridge_formula: parser (Mecway's language), symbols, units (Mecway's
#     exponents, Btu/h/ft2, degF, ...), plan, result field groups;
#   - bridge_from_liml / bridge_to_aster: the plan in model_data, the
#     formulas= argument in study.comm, WARNING for an unsupported symbol
#     and for a result field that is not chosen;
#   - aster_results_export._formula_vars with stand-in variables (units,
#     nodes where all variables exist, non-finite nodes left out as Mecway
#     does, t only with times). Needs numpy (CPython 3, as in the job).
# Reference numbers measured in Mecway 34 (headless, see bridge_formula).
#
#   python tests/test_bridge_formula.py

from __future__ import print_function

import ast
import io
import math
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import numpy as np  # noqa: E402
import bridge_formula as bf  # noqa: E402
import bridge_utils as u  # noqa: E402

u.CONFIG_BRIDGE["language"] = "en"
_FAILED = []
_MODEL = os.path.join(_HERE, "..", "TestFiles", "Verificatie", "modellen",
                      "TH-01a.liml")


def check(cond, text):
    print(("OK   " if cond else "FAIL ") + text)
    if not cond:
        _FAILED.append(text)


def _ev(text, env=None):
    return bf.evaluate(bf.parse(text), env or {}, np)


def test_parser():
    check(abs(_ev("-2^2") + 4) < 1e-12 and abs(_ev("2^3^2") - 512) < 1e-9,
          "-2^2 = -4 and 2^3^2 = 512 (as Mecway)")
    check(abs(_ev("log(10)") - math.log(10)) < 1e-12 and
          _ev("heaviside(0)") == 0.5 and
          abs(_ev("unittriangle(2, 0.5)") - 0.5) < 1e-12 and
          abs(_ev("atan2(1, 1)") - math.pi / 4) < 1e-12 and
          _ev("max(1, 3) + min(1, 3)") == 4,
          "functions log, heaviside, unittriangle, atan2, max, min")
    check(bf.symbols(bf.parse("T + t*qf.z/3600/(12^2) + e.xx + pi"))
          == set(["T", "t", "qf.z", "e.xx"]),
          "symbols case sensitive (T, t), dotted names, constant pi")
    for text, part in (("GLe1 + 1", "not supported"),
                       ("youngsmodulus", "not supported"),
                       ("foo", "unknown name"),
                       ("2*(x", "missing"), ("sinh(x)", "unknown function"),
                       ("", "empty")):
        try:
            bf.parse(text)
            check(False, "error for '{0}'".format(text))
        except bf.FormulaError as e:
            check(part in str(e), "error for '{0}': {1}".format(text, e))
    v = _ev("sqrt(u.x^2+u.z^2)", {"u.x": np.array([3.0, 0.0]),
                                  "u.z": np.array([4.0, 2.0])})
    check(np.allclose(v, [5.0, 2.0]), "evaluation on arrays")


def test_units():
    a, b = bf.unit_map(u"Btu/h/ft²", bf.HEAT_FLUX)
    check(abs(-37500.0 / a + 11887.4) < 0.1,
          "Btu/h/ft2: -37500 W/m2 -> -11887.4 (Mecway 34)")
    a, b = bf.unit_map(u"°F", bf.TEMPERATURE)
    check(abs((310.938 - b) / a - 100.018) < 1e-3,
          "degF: 310.938 K -> 100.018 (Mecway 34)")
    a, b = bf.unit_map(u"°C", bf.TEMPERATURE)
    check(abs((310.938 - b) / a - 37.7875) < 1e-3, "degC: 310.938 K -> 37.79")
    check(bf.unit_map("mm", bf.LENGTH) == (1.0e-3, 0.0) and
          bf.unit_map("in", bf.LENGTH)[0] == 0.0254 and
          bf.unit_map("MPa", bf.PRESSURE)[0] == 1.0e6 and
          abs(bf.unit_map("psi", bf.PRESSURE)[0] - 6894.757) < 1e-3 and
          bf.unit_map("N.mm", bf.MOMENT)[0] == 1.0e-3 and
          bf.unit_map("kN", bf.FORCE)[0] == 1.0e3 and
          bf.unit_map("", bf.NONE) == (1.0, 0.0),
          "mm, in, MPa, psi, N.mm, kN, dimensionless")
    check(bf.unit_map("mm", bf.PRESSURE) is None and
          bf.unit_map(u"BTU/(h·ft²)", bf.HEAT_FLUX) is None and
          bf.unit_map("furlong", bf.LENGTH) is None,
          "wrong dimension, parentheses, unknown unit -> None (SI)")
    check(bf.exponents("+0+1-3") == (0, 1, -3) and
          bf.exponents("+0+0+0+0+1") == bf.TEMPERATURE and
          bf.exponents("") == () and bf.exponents("+1+0") == (1,),
          "Mecway exponents")


def test_plan():
    p = bf.plan("F", "formula(2)", "qf.z/3600/(12^2) + T",
                [("+0+1-3", u"Btu/h/ft²"),
                 ("+0+0+0+0+1", u"°F")])
    check(p["symbols"]["qf.z"][0] == "heatfluxz" and
          abs(p["symbols"]["qf.z"][1] - 3.15459) < 1e-4 and
          p["symbols"]["T"][0] == "temperature" and not p["notes"],
          "plan: variables and unit factors")
    p = bf.plan("F", "formula", "s.xx + x", [("-1+1-2", "furlongs")])
    check(len(p["notes"]) == 2 and p["symbols"]["x"][1:] == [1.0, 0.0],
          "plan: unknown unit and missing unit line -> SI with notes")
    check(bf.groups(bf.plan("F", "formula", "e.xx + FR.z + T + x", []))
          == ["reactions", "strain", "temperature"],
          "result field groups of a formula")
    p2 = bf.plan("F", "formula", "s1 - s3 + tr + e1 + a.x", [])
    check(p2["symbols"]["s1"][0] == "principal1" and
          p2["symbols"]["tr"][0] == "tresca" and
          p2["symbols"]["e1"][0] == "lprincipalstrain1" and
          p2["symbols"]["a.x"][0] == "accx" and
          bf.groups(p2) == ["accelerations", "principal_strains",
                            "principal_stresses"],
          "s1, tr, e1 (principal fields, S34) and a.x (accx)")
    lit = ast.literal_eval(repr(p))
    check(lit == p, "plan is a plain literal (written into study.comm)")


class _V(object):
    def __init__(self, name, ids, vals):
        self.name = name
        self.element = False
        self.ids = np.array(ids, dtype="<i4")
        self.getter = lambda fields, v=np.array(vals, float): v


class _F(object):
    index = 7


def test_formula_vars():
    import aster_results_export as are
    model = {"coords": np.array([[0.0, 0, 0], [0.05, 0, 0], [0.1, 0, 0]])}
    stress = _V("stressxx", [1, 2, 3], [1.0e6, 2.0e6, 3.0e6])
    react = _V("reactionforcez", [1, 3], [10.0, 30.0])
    plans = [bf.plan("F1", "formula", "s.xx", [("-1+1-2", "MPa")]),
             bf.plan("F2", "formula(2)", "FR.z*x", [("+1+1-2", "kN"),
                                                    ("+1", "mm")]),
             bf.plan("F3", "formula(3)", "s.xx/x", [("-1+1-2", "MPa"),
                                                    ("+1", "mm")]),
             bf.plan("F4", "formula(4)", "t*s.xx", [("+0+0+1", "min"),
                                                    ("-1+1-2", "MPa")]),
             bf.plan("F5", "formula(5)", "e.xx", [("", "")])]
    out = are._formula_vars(plans, [stress, react], model, None, _F())
    got = dict((v.name, v) for v in out)
    check(sorted(got) == ["formula", "formula(2)", "formula(3)"],
          "static: t-formula and missing strain left out")
    check(np.allclose(got["formula"].getter(_F()), [1.0, 2.0, 3.0]),
          "s.xx in MPa")
    check(list(got["formula(2)"].ids) == [1, 3] and
          np.allclose(got["formula(2)"].getter(_F()), [0.0, 3.0]),
          "FR.z*x only on reaction nodes, kN and mm")
    check(list(got["formula(3)"].ids) == [2, 3] and
          np.allclose(got["formula(3)"].getter(_F()), [0.04, 0.03]),
          "s.xx/x: node at x = 0 (inf) left out, as Mecway")
    out = are._formula_vars(plans[3:4], [stress], model, {7: 120.0}, _F())
    check(len(out) == 1 and np.allclose(out[0].getter(_F()), [2, 4, 6]),
          "t in min from the step time (120 s)")


def _run(tmp, formula_xml, analysis="ther_3d"):
    work = tempfile.mkdtemp(dir=tmp)
    with io.open(_MODEL, encoding="utf-8") as f:
        s = f.read()
    s = s.replace("</liml>", formula_xml + "</liml>")
    liml = os.path.join(work, "model.liml")
    with io.open(liml, "w", encoding="utf-8") as f:
        f.write(s)
    u.CONFIG_BRIDGE["work_dir"] = work
    u.CONFIG_BRIDGE["active_analysis"] = analysis
    from bridge_from_liml import extract_aster_data_from_liml
    from bridge_mesh import write_mesh
    from bridge_to_aster import generate_AsterSolver_files
    md = extract_aster_data_from_liml(liml)
    mail = os.path.join(work, "m.mail")
    ok = (md is not None and write_mesh(mail, md) and
          generate_AsterSolver_files(work, md, mail, "test.resu"))
    log = io.open(os.path.join(work, "bridge_log.txt"),
                  encoding="utf-8").read()
    comm = io.open(os.path.join(work, "study.comm"),
                   encoding="utf-8").read() if ok else ""
    return md, log, comm


def _xml(name, fs, text, units):
    return (u'  <formula name="{0}" displayunit="" fieldscalar="{1}">\n'
            .format(name, fs) +
            u"".join(u'    <unit exponents="{0}">{1}</unit>\n'.format(*x)
                     for x in units) +
            u"    <formula>{0}</formula>\n  </formula>\n".format(text))


def test_bridge(tmp):
    md, log, comm = _run(tmp, _xml("Fq", "formula", "qf.z/3600/(12^2)",
                                   [("+0+1-3", u"Btu/h/ft²")]) +
                         _xml("Fs", "formula(2)", "youngsmodulus", []) +
                         _xml("Fe", "formula(3)", "e.xx", [("", "")]))
    plans = md.get("result_formulas", [])
    check([p["fieldscalar"] for p in plans] == ["formula", "formula(3)"],
          "bridge_from_liml plans the computable formulas")
    check("WARNING: Formula 'Fs' (youngsmodulus) cannot be computed by "
          "the bridge"
          in log and any("formula 'Fs'" in x for x in md["skipped_loads"]),
          "unsupported symbol: WARNING and skipped_loads")
    check("WARNING: Formula 'Fe' (e.xx) needs the result field strain"
          in log, "result field not chosen: WARNING")
    i = comm.find("formulas=")
    check(i > 0 and "'heatfluxz'" in comm[i:i + 600],
          "study.comm passes formulas= to export_results")


def main():
    saved = dict(u.CONFIG_BRIDGE)
    tmp = tempfile.mkdtemp(prefix="bridge_formula_")
    try:
        test_parser()
        test_units()
        test_plan()
        test_formula_vars()
        test_bridge(tmp)
    finally:
        u.CONFIG_BRIDGE.clear()
        u.CONFIG_BRIDGE.update(saved)
        shutil.rmtree(tmp, ignore_errors=True)
    print("{0} failure(s)".format(len(_FAILED)))
    return 1 if _FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
