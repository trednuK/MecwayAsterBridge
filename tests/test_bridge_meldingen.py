# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test van meldingen die de berekening niet stoppen (Python 2.7 en
# 3, zonder Mecway en Code-Aster):
#   - harmonisch (bridge_harmonic): dempingsverhouding xi >= 1 geeft een
#     WARNING, voor de run (modal_damping) en na de run (de regel
#     BRIDGE_HARM_WAARSCHUWING DEMPING die de .comm in de .mess print);
#   - akoestiek (bridge_acoustic._materials): twee media waarvan een zonder
#     dichtheid geeft een WARNING; verschillende dichtheden een ERROR;
#   - FACTOR_57 (bridge_run_aster._resi_advice, aster_mess_errors): a small
#     MUMPS error estimate gives the page and value for lin_solver_resi, a
#     large one the singular-matrix hint; the SOLVEUR line of the static
#     step of modal/buckling (bridge_to_aster._static_step_solveur);
#   - harmonic total stresses with the loss factor (KNOWN_BUGS 120): the
#     classes of solid groups per eta, only materials whose ELAS got
#     AMOR_HYST (bridge_harmonic._stress_classes, _stress_args).
#
#   python tests/test_bridge_meldingen.py

from __future__ import print_function

import io
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
bridge_utils.CONFIG_BRIDGE["language"] = "nl"

# Logregels opvangen (alleen in het geheugen; geen bridge_log.txt).
LOG = []


def _log(msg):
    LOG.append(msg)


bridge_utils.log = _log
import bridge_to_aster  # noqa: E402
import bridge_harmonic as bh  # noqa: E402
import bridge_acoustic as bac  # noqa: E402
for _mod in (bridge_to_aster, bh, bac):
    _mod.log = _log

FAILS = []


def check(cond, text):
    if not cond:
        FAILS.append(text)


def _warnings():
    return [m for m in LOG if m.startswith("WARNING:")]


def test_harm_check_model():
    for zeta, basis, n in ((1.5, "GENE", 1), (1.0, "GENE", 1),
                           (0.05, "GENE", 0), (0.0, "PHYS", 0)):
        del LOG[:]
        ok = bh._check_model({"bcs": []}, {"modal_damping": zeta}, basis)
        warns = [w for w in _warnings() if "dempingsverhouding >= 1" in w]
        check(ok, "_check_model modal_damping {0} {1}: gestopt: {2}".format(
            zeta, basis, LOG))
        check(len(warns) == n, "_check_model modal_damping {0} {1}: {2} "
              "WARNING(s) verwacht: {3}".format(zeta, basis, n, LOG))
        if n:
            check("modal_damping = %g" % zeta in warns[0],
                  "_check_model: waarde ontbreekt: {0}".format(warns[0]))


class _Modes(object):
    def __init__(self, freqs):
        self.freqs = freqs

    def getAccessParameters(self):
        return {"FREQ": self.freqs}


def _comm_damping(alpha, beta, zeta, freqs):
    """Voer het dempingsdeel van de .comm (_harm_block tot de
    frequentielijst) uit; returns de geprinte regels."""
    plan = {"start": 1.0, "end": 10.0, "count": 5, "spacing": "lin"}
    block = bh._harm_block({"harm_refine_points": 0}, plan, "GENE", [],
                           alpha, beta, zeta, False, "")
    code = block.split("# Frequencies:")[0]
    out = []
    ns = {"modes": _Modes(freqs), "print": lambda s: out.append(s)}
    exec(code, ns)
    return out


def test_harm_comm():
    # beta = 0,1 s: xi = 0,1 pi f -> f = 1 Hz 0,314, f = 5 Hz 1,57,
    # f = 10 Hz 3,14 (twee modes >= 1, de grootste mode 3).
    out = _comm_damping(0.0, 0.1, 0.0, [1.0, 5.0, 10.0])
    warn = [s for s in out if s.startswith("BRIDGE_HARM_WAARSCHUWING")]
    check(len(warn) == 1 and "DEMPING MODE=3" in warn[0] and "N=2" in
          warn[0], ".comm xi >= 1: {0}".format(out))
    out = _comm_damping(0.0, 0.001, 0.02, [1.0, 5.0, 10.0])
    check(not [s for s in out if "WAARSCHUWING" in s],
          ".comm xi < 1: onverwachte waarschuwing: {0}".format(out))


def test_harm_report():
    tmp = tempfile.mkdtemp()
    try:
        f = io.open(os.path.join(tmp, "study.mess"), "w", encoding="utf-8")
        f.write(u"BRIDGE_DEMPING mode 1: 5 Hz, xi = 1.5\n"
                u"BRIDGE_HARM_WAARSCHUWING DEMPING MODE=1 XI=1.5 N=1\n"
                u"BRIDGE_HARM_LIJST N=3 FMIN=1 FMAX=10 VERFIJND=0 "
                u"BASIS=GENE\n")
        f.close()
        mess = bh.read_mess_summary(os.path.join(tmp, "study.mess"))
        check(mess["warn_xi"] == {"MODE": 1.0, "XI": 1.5, "N": 1.0},
              "read_mess_summary warn_xi: {0}".format(mess["warn_xi"]))
        del LOG[:]
        bh.report_harmonic(tmp, [(1, "frequency", 1.0),
                                 (2, "frequency", 10.0)])
        warns = [w for w in _warnings() if "dempingsverhouding >= 1" in w]
        check(len(warns) == 1 and "mode 1, xi = 1.5" in warns[0],
              "report_harmonic: WARNING verwacht: {0}".format(LOG))
    finally:
        shutil.rmtree(tmp)
    bridge_utils.CONFIG_BRIDGE["language"] = "en"
    text = bh.damping_warning(2, 1.25, 3)
    bridge_utils.CONFIG_BRIDGE["language"] = "nl"
    check(text.startswith("WARNING: Harmonic: damping ratio >= 1 (mode 2, "
                          "xi = 1.25; 3 mode(s) with xi >= 1)"),
          "damping_warning EN: {0}".format(text))


def test_acoustic_density():
    elsets = [("E1", "Lucht"), ("E2", "Gas")]

    def run(rho_a, rho_b):
        ac = {"materials": {"Lucht": {"c": 343.0, "rho": rho_a},
                            "Gas": {"c": 600.0, "rho": rho_b}}}
        del LOG[:]
        return bac._materials(elsets, ac)

    mats = run(1.2, None)
    warns = [w for w in _warnings() if "geen dichtheid" in w]
    check(mats is not None and mats["Gas"] == (600.0, 1.0) and
          mats["Lucht"] == (343.0, 1.2),
          "_materials 1,2 / geen: {0}".format(mats))
    check(len(warns) == 1 and "'Gas'" in warns[0] and "'Lucht'" in warns[0]
          and "1.2 kg/m3" in warns[0],
          "_materials 1,2 / geen: WARNING verwacht: {0}".format(LOG))
    for rho_a, rho_b in ((1.2, 1.2), (None, None)):
        mats = run(rho_a, rho_b)
        check(mats is not None and not _warnings(),
              "_materials {0} / {1}: {2} {3}".format(rho_a, rho_b, mats,
                                                     LOG))
    mats = run(1.2, 12.0)
    check(mats is None and any(m.startswith("ERROR:") for m in LOG),
          "_materials 1,2 / 12: ERROR verwacht: {0} {1}".format(mats, LOG))


# FACTOR_57 box as Code-Aster 17.4 writes it (hex20 cantilever 1000 x 40 x
# 10 mm, lin_static_3d; the error value is replaced per case).
_BOX_57 = u"""\
 \u2554\u2550\u2550\u2550\u2557
 \u2551 <EXCEPTION> <FACTOR_57>                  \u2551
 \u2551                                          \u2551
 \u2551 Solveur MUMPS :                          \u2551
 \u2551   La solution du syst\u00e8me lin\u00e9aire est trop impr\u00e9cise :  \u2551
 \u2551   Erreur calcul\u00e9e   :                   \u2551
 \u2551 {err}                                     \u2551
 \u2551   Erreur acceptable : 1e-06   (RESI_RELA) \u2551
 \u2551                                          \u2551
 \u2551 Conseils :                               \u2551
 \u2551   On peut augmenter la                   \u2551
 \u2551 valeur du mot cl\u00e9 SOLVEUR/RESI_RELA.     \u2551
 \u255a\u2550\u2550\u2550\u255d
--- DIAGNOSTIC JOB : OK
"""


def test_factor57():
    import bridge_run_aster as bra
    bra.log = _log
    cfg = bridge_utils.CONFIG_BRIDGE
    old = cfg.get("active_analysis"), cfg.get("work_dir")
    tmp = tempfile.mkdtemp()
    try:
        cfg["work_dir"] = tmp
        for name, err, expect in (
                ("buckling_3d", u"4.98968e-05", (u"Knik", u"op 1e-3")),
                ("modal_3d", u"7.04369e-06", (u"Modaal", u"op 1e-4")),
                ("lin_static_3d", u"1.09913e-06", (u"Statisch", u"op 1e-4")),
                ("buckling_3d", u"13.4025", (u"singulier",)),
                ("ther_3d", u"7.04369e-06", (u"geen instelling",))):
            cfg["active_analysis"] = name
            path = os.path.join(tmp, bridge_utils.run_name(".mess"))
            with io.open(path, "w", encoding="utf-8") as f:
                f.write(_BOX_57.format(err=err))
            del LOG[:]
            msgs = bra.aster_mess_errors(tmp)
            check(len(msgs) == 1 and all(e in msgs[0] for e in expect),
                  "FACTOR_57 {0} {1}: {2}".format(name, err, msgs))
    finally:
        cfg["active_analysis"], cfg["work_dir"] = old
        shutil.rmtree(tmp, ignore_errors=True)
    line = bridge_to_aster._static_step_solveur(
        {"solver_nprec": 8, "lin_solver_resi": 1.0e-4})
    check(line == "SOLVEUR=_F(METHODE='MUMPS', NPREC=8, RESI_RELA=0.0001),",
          "_static_step_solveur: {0}".format(line))
    line = bridge_to_aster._static_step_solveur({})
    check(line == "SOLVEUR=_F(METHODE='MUMPS', NPREC=8, RESI_RELA=1e-05),",
          "_static_step_solveur default: {0}".format(line))
    for name in ("lin_static_3d", "nonlin_static_3d", "modal_3d",
                 "buckling_3d"):
        check(cfg["analyses"][name].get("lin_solver_resi") == 1.0e-5,
              "lin_solver_resi default in {0}".format(name))


def test_log_errors():
    """bridge_utils.log_errors: the first ERROR lines after a mark, for the
    message when the preparation stops before Code-Aster
    (MecwayAsterBridgeMain._prep_failed)."""
    cfg = bridge_utils.CONFIG_BRIDGE
    old = cfg.get("work_dir")
    tmp = tempfile.mkdtemp(prefix="logerr")
    try:
        cfg["work_dir"] = tmp
        path = os.path.join(tmp, bridge_utils.log_file_name())
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(u"[2026-10-22 10:00:00] ERROR: oude fout\n")
        mark = bridge_utils.log_size()
        check(mark > 0, "log_size after a line")
        with io.open(path, "a", encoding="utf-8") as f:
            f.write(u"[2026-10-22 10:00:01] INFO: mesh\n"
                    u"[2026-10-22 10:00:02] ERROR: eerste fout é\n"
                    u"[2026-10-22 10:00:03] WARNING: iets\n"
                    u"[2026-10-22 10:00:04] ERROR: tweede\n"
                    u"[2026-10-22 10:00:05] ERROR: derde\n"
                    u"[2026-10-22 10:00:06] ERROR: vierde\n")
        got = bridge_utils.log_errors(mark)
        check(got == [u"ERROR: eerste fout é", u"ERROR: tweede",
                      u"ERROR: derde"], "log_errors: {0!r}".format(got))
        check(bridge_utils.log_errors(0, limit=1) == [u"ERROR: oude fout"],
              "log_errors from the start, limit 1")
        cfg["work_dir"] = os.path.join(tmp, "bestaat_niet")
        check(bridge_utils.log_errors(0) == [] and
              bridge_utils.log_size() == 0, "log_errors without a log")
    finally:
        cfg["work_dir"] = old
        shutil.rmtree(tmp, ignore_errors=True)


def test_harm_stress_eta():
    """KNOWN_BUGS 120: the stress correction (1 + i eta) uses the loss
    factor per solid group, only of materials whose ELAS got AMOR_HYST;
    one class -> stress_eta, several -> stress_classes."""
    md = {"elsets": {"Blok": "Staal", "Blok2": "Rubber", "Plaat": "Alu",
                     "Veer": "V"}}
    for etas, patched, g3d, want in (
            ({"Staal": 0.1}, {"Staal"}, ["Blok"], [(0.1, ["Blok"])]),
            ({"Alu": 0.5}, {"Alu"}, ["Blok"], [(0.0, ["Blok"])]),
            ({"Staal": 0.1}, set(), ["Blok"], [(0.0, ["Blok"])]),
            ({"Staal": 0.02, "Rubber": 0.5}, {"Staal", "Rubber"},
             ["Blok", "Blok2"], [(0.02, ["Blok"]), (0.5, ["Blok2"])]),
            ({"Rubber": 0.5}, {"Rubber"}, ["Blok", "Blok2"],
             [(0.0, ["Blok"]), (0.5, ["Blok2"])]),
            ({"Staal": 0.3, "Rubber": 0.3}, {"Staal", "Rubber"},
             ["Blok", "Blok2"], [(0.3, ["Blok", "Blok2"])])):
        got = list(bh._stress_classes(md, etas, patched, g3d).items())
        check(got == want, "harmonic stress classes {0} on {1}: {2} (want "
              "{3})".format(sorted(etas.items()), g3d, got, want))
    one = bh._stress_args({0.3: ["A", "B"]}, 0.3)
    check(one == ",\n    stress_eta=0.3", "stress_eta argument: " + one)
    two = bh._stress_args({0.0: ["A"], 0.1: ["B", "C"]}, None)
    check(two == ",\n    stress_classes=[(0, bridge_sig1, ['A']), "
          "(0.1, bridge_sig2, ['B', 'C'])]", "stress_classes argument: " +
          two)
    import tempfile
    path = os.path.join(tempfile.mkdtemp(), "x.mess")
    f = open(path, "w")
    f.write("BRIDGE_HARM_HYST_STRESS CLASSES=0,0.5 UNMATCHED=3\n")
    f.close()
    hyst = bh.read_mess_summary(path)["hyst"]
    check(hyst == {"CLASSES": "0,0.5", "UNMATCHED": 3.0},
          "BRIDGE_HARM_HYST_STRESS read: {0}".format(hyst))
    check(bh._stress_args({0.0: ["A"]}, None) == "", "no correction")


_CE_LIML = u"""<liml version="33">
  <analysis type="S30" />
  <node nid="1" x="0" y="0" z="0" />
  <node nid="2" x="1" y="0" z="0" />
  <elset name="Balk" material="Staal">
    <elem eid="1" shape="line2" nodes="1 2" />
  </elset>
  <fixed selection="Vast" />
  {ce}
  <mat name="Staal">
    <geometric type="RectBar" recta="0.02 m" rectb="0.03 m" />
    <mechanical type="Isotropic" youngsmodulus="210000 MPa" poissonratio="0.3" />
  </mat>
  <nodeselection name="Vast"><node nid="1" /></nodeselection>
</liml>
"""


def test_constraint_constant():
    """KNOWN_BUGS 27: Mecway 35 reads the constant of a constraint equation
    only as an attribute; a non-zero <constant> element gives a WARNING,
    the value is still used."""
    from bridge_from_liml import extract_aster_data_from_liml
    term = u'<term coefficient="1 1/m" nid="2" dof="ux" />'
    tmp = tempfile.mkdtemp(prefix="mab_ce_")
    try:
        for ce, value, warn in (
                (u'<constraintequation constant="0.001">' + term +
                 u'</constraintequation>', 0.001, False),
                (u'<constraintequation>' + term +
                 u'<constant>0.001</constant></constraintequation>', 0.001,
                 True),
                (u'<constraintequation>' + term +
                 u'<constant>0</constant></constraintequation>', 0.0, False),
                (u'<constraintequation constant="0.002">' + term +
                 u'<constant>0.001</constant></constraintequation>', 0.002,
                 False)):
            path = os.path.join(tmp, "m.liml")
            with io.open(path, "w", encoding="utf-8") as f:
                f.write(_CE_LIML.replace(u"{ce}", ce))
            bridge_utils.CONFIG_BRIDGE["work_dir"] = tmp
            bridge_utils.CONFIG_BRIDGE["active_analysis"] = "lin_static_3d"
            del LOG[:]
            md = extract_aster_data_from_liml(path)
            eqs = (md or {}).get("constraint_equations", [])
            got = [m for m in LOG if "WARNING" in m and "<constant>" in m]
            check(len(eqs) == 1 and abs(eqs[0]["constant"] - value) < 1e-15
                  and bool(got) == warn,
                  u"constraint equation {0}: C {1}, WARNING {2}".format(
                      ce[:40], eqs[0]["constant"] if eqs else None,
                      bool(got)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_bonded_offset():
    """KNOWN_BUGS 128: WARNING for bonded shell faces (face to face, shell
    face on a solid, solid face on a shell), none for shell edges."""
    import bridge_mesh
    saved = bridge_mesh.log
    bridge_mesh.log = _log
    try:
        for m_type, s_type, kinds, text in (
                ("COQUE", "COQUE", set(["shellface"]), "vlak op vlak"),
                ("MASSIF", "COQUE", set(["shellface"]), "volumevlak"),
                ("COQUE", "MASSIF", set(["solid"]), "volumevlak"),
                ("COQUE", "COQUE", set(["shelledge"]), None),
                ("MASSIF", "COQUE", set(["shelledge"]), None),
                ("MASSIF", "MASSIF", set(["solid"]), None)):
            del LOG[:]
            bridge_mesh._warn_bonded_offset("c", m_type, s_type, kinds)
            warn = _warnings()
            if text is None:
                check(not warn, "bonded {0}/{1} {2}: no WARNING, got {3}"
                      .format(m_type, s_type, sorted(kinds), warn))
            else:
                check(len(warn) == 1 and text in warn[0]
                      and "KNOWN_BUGS 128" in warn[0],
                      "bonded {0}/{1} {2}: WARNING with '{3}', got {4}"
                      .format(m_type, s_type, sorted(kinds), text, warn))
    finally:
        bridge_mesh.log = saved


def test_bonded_gap():
    """KNOWN_BUGS 146: WARNING for tied slave nodes farther from the master
    than the shell offset plus the tolerance; none within it. Cases:
    stacked plates at (t1 + t2)/2, a solid at t/2 and at 0 from a shell, a
    shell edge on a shell face (expected t_m/2, node at the mid-surface),
    solid on solid with a gap; skipped with an Element offset or a shell
    without a thickness."""
    import bridge_mesh as bm
    saved = bm.log
    bm.log = _log
    try:
        t1, t2, tol = 0.002, 0.004, 1e-4
        for name, dist, expected, warn in (
                ("plates stacked", 0.5 * (t1 + t2), 0.5 * (t1 + t2), False),
                ("solid on shell surface", 0.5 * t1, 0.5 * t1, False),
                ("solid on mid-surface", 0.0, 0.5 * t1, False),
                ("shell edge on face", 0.0, 0.5 * t1, False),
                ("solid on solid touching", 0.5 * tol, 0.0, False),
                ("solid on solid, gap", 0.002, 0.0, True),
                ("solid above shell, gap", 0.002, 0.5 * t1, True)):
            del LOG[:]
            got = bm._bonded_gap_warning("c", {1: 0.0, 2: dist}, expected,
                                         tol)
            warn_lines = _warnings()
            check(got == warn and len(warn_lines) == (1 if warn else 0),
                  "bonded gap '{0}': warned {1}, {2}".format(
                      name, got, warn_lines))
            if warn:
                check("1 van de 2" in warn_lines[0] and
                      "KNOWN_BUGS 146" in warn_lines[0] and
                      ("%.3g" % dist) in warn_lines[0],
                      "bonded gap text: {0}".format(warn_lines[0]))
        # expected offset from the shell sections; skip conditions
        md = {"shell_sections": {"P": {"thickness": t1}},
              "_elem_elset": {1: "P", 2: "Q"}}
        face = [{"kind": "shellface", "eid": 1}]
        check(bm._bonded_expected_offset(md, face, set(["shellface"]))
              == 0.5 * t1, "expected offset t/2")
        check(bm._bonded_expected_offset(md, [{"kind": "shellface",
                                               "eid": 2}],
                                         set(["shellface"])) is None,
              "no thickness: None")
        check(bm._bonded_expected_offset(md, face, set(["solid"])) == 0.0,
              "solid: 0")
        del LOG[:]
        check(not bm._check_bonded_gap(
            md, "c", {"M": [{"kind": "shellface", "eid": 2}]}, "M", "S",
            set(["shellface"]), set(["solid"]), [], {1: 1.0}, False) and
            not _warnings() and any("without a thickness" in m for m in LOG),
            "shell without a thickness: INFO, no WARNING")
        del LOG[:]
        bm._bonded_gap_warning("c", {1: 0.01}, 0.0, 1e-4, stiffer=False)
        check(_warnings() and "kan afwijken" in _warnings()[0],
              "shell on shell gap: 'can deviate'")
        del LOG[:]
        md["element_offsets"] = [{"selection": "x"}]
        check(not bm._check_bonded_gap(md, "c", {}, "M", "S",
                                       set(["solid"]), set(["solid"]), [],
                                       {1: 1.0}, False) and
              not _warnings() and any("Element offset" in m for m in LOG),
              "Element offset: INFO, no WARNING")
    finally:
        bm.log = saved


def test_alarm_hint():
    """CALCULEL5_48 has an explanation in both languages (KNOWN_BUGS 146)."""
    import bridge_run_aster as bra
    hint = bra._ALARM_HINTS.get("CALCULEL5_48")
    check(hint is not None and len(hint) == 2 and
          all("KNOWN_BUGS 146" in h for h in hint),
          "CALCULEL5_48 hint: {0!r}".format(hint))


def test_ccx_keywords():
    """KNOWN_BUGS 4: active CCX keyword modifications give a WARNING each
    and one combined skipped_loads entry; suppressed ones nothing."""
    import xml.etree.ElementTree as ET
    import bridge_from_liml as bfl
    saved = bfl.log
    bfl.log = _log
    try:
        root = ET.fromstring(
            '<liml><ccxmodifykeyword action="setparameter" keyword="STATIC" '
            'setparameter="SOLVER" value="PARDISO" omitparameter="" '
            'suppressed="true" />'
            '<ccxmodifykeyword action="setparameter" keyword="CONTACT PAIR" '
            'setparameter="ADJUST" value="0" omitparameter="" />'
            '<ccxmodifykeyword action="omitparameter" keyword="STEP" '
            'setparameter="" value="" omitparameter="NLGEOM" /></liml>')
        md = {"skipped_loads": []}
        del LOG[:]
        bfl._report_ccx_keywords(root, md)
        warn = _warnings()
        check(len(warn) == 2 and "*CONTACT PAIR: setparameter ADJUST=0"
              in warn[0] and "*STEP: omitparameter NLGEOM" in warn[1],
              "ccx keyword WARNINGs: {0}".format(warn))
        check(len(md["skipped_loads"]) == 1 and
              "(2," in md["skipped_loads"][0] and
              "PARDISO" not in md["skipped_loads"][0],
              "ccx keyword skipped_loads: {0}".format(md["skipped_loads"]))
        md = {"skipped_loads": []}
        bfl._report_ccx_keywords(ET.fromstring("<liml />"), md)
        check(md["skipped_loads"] == [], "no ccx keywords: nothing")
    finally:
        bfl.log = saved


def main():
    for test in (test_harm_check_model, test_harm_comm, test_harm_report,
                 test_acoustic_density, test_factor57, test_log_errors,
                 test_bonded_offset, test_harm_stress_eta,
                 test_constraint_constant, test_bonded_gap, test_alarm_hint,
                 test_ccx_keywords):
        test()
    if FAILS:
        for f in FAILS:
            print(u"FOUT: {0}".format(f).encode("ascii", "replace").decode(
                "ascii"))
        return 1
    print("OK: meldingen (harmonisch xi >= 1, akoestiek medium zonder "
          "dichtheid, FACTOR_57, verliesfactor spanningen)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
