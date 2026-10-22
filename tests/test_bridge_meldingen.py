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
#     step of modal/buckling (bridge_to_aster._static_step_solveur).
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
--- DIAGNOSTIC JOB : <F>_ERROR
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
    check(line == "SOLVEUR=_F(METHODE='MUMPS', NPREC=8, RESI_RELA=1e-06),",
          "_static_step_solveur default: {0}".format(line))
    for name in ("lin_static_3d", "nonlin_static_3d", "modal_3d",
                 "buckling_3d"):
        check(cfg["analyses"][name].get("lin_solver_resi") == 1.0e-6,
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


def main():
    for test in (test_harm_check_model, test_harm_comm, test_harm_report,
                 test_acoustic_density, test_factor57, test_log_errors):
        test()
    if FAILS:
        for f in FAILS:
            print(u"FOUT: {0}".format(f).encode("ascii", "replace").decode(
                "ascii"))
        return 1
    print("OK: meldingen (harmonisch xi >= 1, akoestiek medium zonder "
          "dichtheid, FACTOR_57)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
