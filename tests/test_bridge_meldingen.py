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
#     dichtheid geeft een WARNING; verschillende dichtheden een ERROR.
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


def main():
    for test in (test_harm_check_model, test_harm_comm, test_harm_report,
                 test_acoustic_density):
        test()
    if FAILS:
        for f in FAILS:
            print(u"FOUT: {0}".format(f).encode("ascii", "replace").decode(
                "ascii"))
        return 1
    print("OK: meldingen (harmonisch xi >= 1, akoestiek medium zonder "
          "dichtheid)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
