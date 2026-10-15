# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_fatigue.py
# Fatigue (STAPPENPLAN S8): damage D and life per node from a
# load history, with a Wohler curve per material and Miner's
# rule. User doc: docs/Vermoeiing.md (EN: docs/en/Fatigue.md).
# Compatible with IronPython 2.7.9 (Mecway); the calculation itself runs in
# the Code-Aster job (aster_fatigue.py, Python 3 + numpy).
#
# Input (Mecway has no fatigue: manual v33 and mecway.exe know
# no fatigue/S-N/Wohler), as #ASTER lines (bridge_custom):
#   #ASTER-WOHLER material: K=V, ...       Wohler curve of a Mecway
#                                          material ('*' = the rest)
#       table   S = [s1, s2, ..] MPa, N = [n1, n2, ..]   (S = amplitude)
#       power   S = 80 MPa, N = 2e6, m = 3               (N = N (S/s)^m)
#       Basquin Sf = 900 MPa, b = -0.09                  (S = Sf (2N)^b)
#       further: Se (no damage below this amplitude; power/Basquin),
#       INTERPOL = LOG|LIN, PROL_GAUCHE = EXCLU|CONSTANT|LINEAIRE,
#       PROL_DROITE = LINEAIRE|CONSTANT (table), correctie = GEEN|GOODMAN|
#       GERBER with Su (tensile strength)
#       strain-life (Manson-Coffin, S8b): Sf, b, ef, c (and E; default
#       the E of the material): Δε/2 = Sf/E (2N)^b + ef (2N)^c
#   #ASTER-VERMOEIING K=V, ...             (also #ASTER-FATIGUE)
#       spanning = VMIS_SG|PRIN, telling = RAINFLOW|ASTM, herhalingen = h,
#       rek = PRIN|VMIS_SG (strain curve),
#       multiaxial (S8b): criterium = DANG_VAN|MATAKE|CROSSLAND|FORMULE
#       with a, b (stress), c, formule = '...', belasting = PERIODIEK|
#       NIET_PERIODIEK, projectie = UN_AXE|DEUX_AXES
#   #ASTER-BLOK a, m, n                    (also #ASTER-BLOCK; linear
#                                          static: n cycles with amplitude
#                                          a x and mean m x the
#                                          static stress)
#   #ASTER-SIGNAAL f1, f2, ...             (also #ASTER-SIGNAL; linear
#                                          static: rainflow on f x the
#                                          static stress)
# Without BLOK/SIGNAAL in a nonlinear or dynamic analysis
# (STAT_NON_LINE, DYNA_NON_LINE) the time steps of the run are the
# signal per node.
#
# Translation: after CALC_CHAMP (SIGM_NOEU on the solid elsets) a call of
# aster_fatigue.compute in the .comm; the result goes as node_fields
# (damage, life) to aster_results_export. After the run: report() reads the
# lines BRIDGE_VERMOEIING_* from the .mess (log and status box). Why not
# CALC_FATIGUE for the field: see docs/Vermoeiing.md par. 4 (CUMUL_DOMMAGE
# only knows VMIS_SG on ELNO/ELGA, no mean stress correction and
# no blocks; the bridge computes the same, verification VM-04/VM-06).
# Shells (S8b): the same route on SIEQ_NOEU of res_sup/res_inf (POST_CHAMP
# EXTR_COQUE, _build_calc_champ_block), fields damage_top/damage_bottom.
# Strain curve (Manson-Coffin, S8b): the same route on EPSI_NOEU.
# Multiaxial (S8b, criterium = ...): CALC_FATIGUE TYPE_CALCUL=
# 'FATIGUE_MULTI' OPTION='DOMA_NOEUD' (critical plane, Code-Aster) on res
# (time steps) or on a result built from the static stress
# (CREA_RESU, signal or one result per block); periodic: the
# bridge computes N from SIGEQ with its own curve (aster_fatigue.compute_multi),
# non-periodic: it takes over ENDO1 from Code-Aster.

import io
import os
import re

from bridge_utils import (log, tr, run_name, CONFIG_BRIDGE, parse_and_convert,
                          _unit_key, work_dir_path)

CSV_SUFFIX = "_vermoeiing.csv"

# Kinds of solid elements (MODELISATION in bridge_to_aster)
_VOLUME = ("3D", "3D_SI")
# Shells (bridge_to_aster._SHELL_MODELISATIONS)
_SHELL = ("DKT", "DST", "COQUE_3D")

# Allowed stress units (bridge_utils.parse_and_convert 'pressure')
_STRESS_UNITS = ("pa", "kpa", "mpa", "gpa", "n/mm2", "n/m2", "kn/m2", "psi",
                 "ksi", "bar")

_CORRECTIONS = {"GEEN": "GEEN", "NONE": "GEEN", "GOODMAN": "GOODMAN",
                "GERBER": "GERBER"}
_STRESS_KINDS = ("VMIS_SG", "PRIN")
_COUNTINGS = ("RAINFLOW", "ASTM")
# Multiaxial criteria (#ASTER-VERMOEIING criterium = ...) -> Code-Aster
# CALC_FATIGUE CRITERE per TYPE_CHARGE (catalogue calc_fatigue.py v17.4:
# PERIODIQUE MATAKE_MODI_AC/DANG_VAN_MODI_AC/FORMULE_CRITERE, NON_PERIODIQUE
# MATAKE_MODI_AV/DANG_VAN_MODI_AV/FORMULE_CRITERE). CROSSLAND does not exist
# in CALC_FATIGUE as a name: FORMULE_CRITERE with AMPCIS (like szlz107a
# "POUR RETROUVER LE CRITERE CROSSLAND"), periodic only.
_CRITERIA = ("GEEN", "DANG_VAN", "MATAKE", "CROSSLAND", "FORMULE")
_LOADINGS = {"PERIODIEK": "PERIODIQUE", "PERIODIC": "PERIODIQUE",
             "PERIODIQUE": "PERIODIQUE", "NIET_PERIODIEK": "NON_PERIODIQUE",
             "NON_PERIODIC": "NON_PERIODIQUE",
             "NON_PERIODIQUE": "NON_PERIODIQUE"}
_PROJECTIONS = ("UN_AXE", "DEUX_AXES")
# Parameters of FORMULE_GRDEQ: the name list in libbibfor.a of Code-Aster
# 17.4 (test cases sslv135a, szlz107a use DTAUMA, PHYDRM, NORMAX,
# NORMOY, EPNMAX, EPNMOY, RAYSPH, AMPCIS, DSIGEQ); U4.83.02 NOT consulted
FORMULA_PARAMS = ("DTAUMA", "PHYDRM", "NORMAX", "NORMOY", "EPNMAX",
                  "EPNMOY", "DEPSPE", "EPSPR1", "SIGNM1", "DENDIS", "DENDIE",
                  "APHYDR", "MPHYDR", "DSIGEQ", "SIGPR1", "EPSNM1", "INVA2S",
                  "DSITRE", "DEPTRE", "EPSPAC", "RAYSPH", "AMPCIS", "DEPSEE",
                  "DTAUCR", "DGAMCR", "DSINCR", "DEPNCR", "MTAUCR", "MGAMCR",
                  "MSINCR", "MEPNCR", "DGAMPC", "DEPNPC", "MGAMPC", "MEPNPC")

# Keys of #ASTER-VERMOEIING (NL and EN) -> internal name
_OPTION_KEYS = {"spanning": "stress", "stress": "stress",
                "telling": "counting", "counting": "counting",
                "herhalingen": "repeats", "repeats": "repeats",
                "rek": "strain", "strain": "strain",
                "criterium": "criterion", "criterion": "criterion",
                "a": "a", "b": "b", "c": "c",
                "formule": "formula", "formula": "formula",
                "belasting": "loading", "loading": "loading",
                "projectie": "projection", "projection": "projection"}
# Keys of #ASTER-WOHLER -> internal name
_CURVE_KEYS = {"s": "S", "n": "N", "m": "m", "sf": "Sf", "b": "b",
               "se": "Se", "su": "Su", "correctie": "correction",
               "correction": "correction", "interpol": "interpol",
               "prol_gauche": "prol_gauche", "prol_droite": "prol_droite",
               "ef": "ef", "c": "c", "e": "E"}


# ==========================================
# READING
# ==========================================
def is_requested(model_data):
    """True if the model has #ASTER-WOHLER lines."""
    fat = model_data.get("aster_custom", {}).get("fatigue") or []
    return any(kind == "wohler" for kind, _b in fat)


def _split_top(text):
    """Split on commas outside [ ], ( ) and quotes (a formula
    like 'max(PHYDRM,0)' stays whole)."""
    out, depth, cur, quote = [], 0, [], None
    for ch in text:
        if quote:
            if ch == quote:
                quote = None
            cur.append(ch)
            continue
        if ch in "'\"":
            quote = ch
        elif ch in "[(":
            depth += 1
        elif ch in "])":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return [p.strip() for p in out if p.strip()]


_LIST_RE = re.compile(r"^\[(.*)\]\s*(.*)$")
_NUM_RE = re.compile(r"^\s*([-+]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][-+]?"
                     r"[0-9]+)?)\s*(.*?)\s*$")


def _numbers(text):
    """'[1e4, 2e5] MPa' -> ([1e4, 2e5], 'MPa'); '80 MPa' -> ([80.0],
    'MPa', scalar). Returns (numbers, unit, list?) or None."""
    m = _LIST_RE.match(text.strip())
    if m:
        try:
            vals = [float(v) for v in m.group(1).split(",") if v.strip()]
        except ValueError:
            return None
        return vals, m.group(2).strip(), True
    m = _NUM_RE.match(text)
    if not m:
        return None
    return [float(m.group(1))], m.group(2), False


def _stress(vals, unit, what, line):
    """Stresses to Pa; ERROR (None) without a unit or with an unknown
    unit."""
    key = _unit_key(unit or u"")
    if key not in _STRESS_UNITS:
        log(tr(u"ERROR: #ASTER-WOHLER {0}: {1} heeft een spanningseenheid "
               u"nodig (Pa, kPa, MPa, GPa, N/mm2, psi, ksi), gevonden: "
               u"'{2}'. Voorbeeld: S = [200, 280, 400] MPa.",
               u"ERROR: #ASTER-WOHLER {0}: {1} needs a stress unit (Pa, "
               u"kPa, MPa, GPa, N/mm2, psi, ksi), found: '{2}'. Example: "
               u"S = [200, 280, 400] MPa.").format(line, what, unit or u"-"))
        return None
    return [parse_and_convert(u"{0!r} {1}".format(v, unit), "pressure")
            for v in vals]


def _bad_curve(line, why_nl, why_en):
    log(tr(u"ERROR: #ASTER-WOHLER {0}: {1}",
           u"ERROR: #ASTER-WOHLER {0}: {1}").format(
               line, tr(why_nl, why_en)))
    return None


def _parse_curve(body, materials):
    """An #ASTER-WOHLER line -> dict for aster_fatigue.Curve, or None
    (ERROR)."""
    line = body.strip()
    name, sep, rest = line.partition(":")
    name = name.strip()
    if not sep or not name:
        return _bad_curve(line, u"verwacht 'materiaal: K=V, ...' (bijv. "
                          u"'#ASTER-WOHLER Staal: S = [200, 400] MPa, N = "
                          u"[1e6, 1e4]').",
                          u"expected 'material: K=V, ...' (e.g. "
                          u"'#ASTER-WOHLER Steel: S = [200, 400] MPa, N = "
                          u"[1e6, 1e4]').")
    if name != "*" and name not in materials:
        return _bad_curve(line, u"materiaal '{0}' bestaat niet in het model "
                          u"(bekend: {1}; '*' = alle overige).".format(
                              name, u", ".join(sorted(materials))),
                          u"material '{0}' does not exist in the model "
                          u"(known: {1}; '*' = all others).".format(
                              name, u", ".join(sorted(materials))))
    raw = {}
    for part in _split_top(rest):
        key, eq, value = part.partition("=")
        k = _CURVE_KEYS.get(key.strip().lower())
        if not eq or k is None:
            return _bad_curve(line, u"onbekend of onvolledig: '{0}' "
                              u"(sleutels: {1}).".format(
                                  part, u", ".join(sorted(set(
                                      _CURVE_KEYS)))),
                              u"unknown or incomplete: '{0}' (keys: "
                              u"{1}).".format(part, u", ".join(sorted(set(
                                  _CURVE_KEYS)))))
        raw[k] = value.strip()
    d = {"material": name}
    for k in ("correction", "interpol", "prol_gauche", "prol_droite"):
        if k in raw:
            raw[k] = raw[k].strip("'\"").upper()
    nums = {}
    for k in ("S", "N", "m", "Sf", "b", "Se", "Su", "ef", "c", "E"):
        if k in raw:
            got = _numbers(raw[k])
            if got is None:
                return _bad_curve(line, u"geen getal(len) in {0} = {1}."
                                  .format(k, raw[k]),
                                  u"no number(s) in {0} = {1}.".format(
                                      k, raw[k]))
            nums[k] = got
    for k in ("S", "Sf", "Se", "Su", "E"):
        if k in nums:
            vals = _stress(nums[k][0], nums[k][1], k, line)
            if vals is None:
                return None
            nums[k] = (vals, "Pa", nums[k][2])
    for k in ("N", "m", "b", "ef", "c"):
        if k in nums and nums[k][1]:
            return _bad_curve(line, u"{0} is dimensieloos (eenheid '{1}')."
                              .format(k, nums[k][1]),
                              u"{0} is dimensionless (unit '{1}')."
                              .format(k, nums[k][1]))
    is_list = lambda k: k in nums and nums[k][2]
    scalar = lambda k: nums[k][0][0]
    if is_list("S") or is_list("N"):
        if not (is_list("S") and is_list("N")) or \
                len(nums["S"][0]) != len(nums["N"][0]) or \
                len(nums["S"][0]) < 2:
            return _bad_curve(line, u"een tabel heeft S en N als lijsten "
                              u"van gelijke lengte (minstens 2 punten).",
                              u"a table has S and N as lists of equal "
                              u"length (at least 2 points).")
        s, n = nums["S"][0], nums["N"][0]
        interpol = raw.get("interpol", "LOG")
        if interpol not in ("LOG", "LIN"):
            return _bad_curve(line, u"INTERPOL = LOG of LIN.",
                              u"INTERPOL = LOG or LIN.")
        if any(b <= a for a, b in zip(s[:-1], s[1:])) or \
                any(b > a for a, b in zip(n[:-1], n[1:])):
            # The examples in the messages must themselves be valid
            # (tests/test_bridge_fatigue_examples.py).
            return _bad_curve(line, u"S moet oplopen en N mag niet stijgen "
                              u"(S is de spanningsamplitude, N het aantal "
                              u"cycli tot breuk); begin bij de laagste S, "
                              u"bijv. S = [200, 400] MPa, N = [1e6, 1e4].",
                              u"S must increase and N must not increase (S "
                              u"is the stress amplitude, N the number of "
                              u"cycles to failure); start at the lowest S, "
                              u"e.g. S = [200, 400] MPa, N = [1e6, 1e4].")
        if interpol == "LOG" and (min(s) <= 0.0 or min(n) <= 0.0):
            return _bad_curve(line, u"INTERPOL = LOG vraagt S > 0 en N > 0 "
                              u"(of kies INTERPOL = LIN).",
                              u"INTERPOL = LOG needs S > 0 and N > 0 (or "
                              u"choose INTERPOL = LIN).")
        if min(s) < 0.0 or min(n) < 0.0:
            return _bad_curve(line, u"S en N mogen niet negatief zijn.",
                              u"S and N must not be negative.")
        left = raw.get("prol_gauche", "EXCLU")
        right = raw.get("prol_droite", "LINEAIRE")
        if left not in ("EXCLU", "CONSTANT", "LINEAIRE") or \
                right not in ("LINEAIRE", "CONSTANT"):
            return _bad_curve(line, u"PROL_GAUCHE = EXCLU, CONSTANT of "
                              u"LINEAIRE; PROL_DROITE = LINEAIRE of "
                              u"CONSTANT.",
                              u"PROL_GAUCHE = EXCLU, CONSTANT or LINEAIRE; "
                              u"PROL_DROITE = LINEAIRE or CONSTANT.")
        d.update({"form": "table", "S": s, "N": n, "interpol": interpol,
                  "prol_gauche": left, "prol_droite": right})
    elif "m" in nums and "S" in nums and "N" in nums:
        if scalar("m") <= 0.0 or scalar("S") <= 0.0 or scalar("N") <= 0.0:
            return _bad_curve(line, u"m, S en N moeten > 0 zijn.",
                              u"m, S and N must be > 0.")
        d.update({"form": "power", "S": scalar("S"), "N": scalar("N"),
                  "m": scalar("m")})
    elif "ef" in nums or "c" in nums:
        # Strain-life (Manson-Coffin-Basquin): Δε/2 = Sf/E (2N)^b +
        # ef (2N)^c (Manson 1953, Coffin 1954, Morrow 1965)
        if not ("Sf" in nums and "b" in nums and "ef" in nums and
                "c" in nums):
            return _bad_curve(line, u"Manson-Coffin vraagt Sf, b, ef en c "
                              u"(Δε/2 = Sf/E (2N)^b + ef (2N)^c), bijv. "
                              u"'Sf = 900 MPa, b = -0.09, ef = 0.3, c = "
                              u"-0.55'.",
                              u"Manson-Coffin needs Sf, b, ef and c (Δε/2 = "
                              u"Sf/E (2N)^b + ef (2N)^c), e.g. 'Sf = 900 "
                              u"MPa, b = -0.09, ef = 0.3, c = -0.55'.")
        if scalar("b") >= 0.0 or scalar("c") >= 0.0 or \
                scalar("Sf") <= 0.0 or scalar("ef") <= 0.0:
            return _bad_curve(line, u"Manson-Coffin: Sf > 0, ef > 0, b < 0 "
                              u"en c < 0.",
                              u"Manson-Coffin: Sf > 0, ef > 0, b < 0 and "
                              u"c < 0.")
        d.update({"form": "strain", "Sf": scalar("Sf"), "b": scalar("b"),
                  "ef": scalar("ef"), "c": scalar("c")})
        if "E" in nums:
            if scalar("E") <= 0.0:
                return _bad_curve(line, u"E moet > 0 zijn.",
                                  u"E must be > 0.")
            d["E"] = scalar("E")
        for k in ("Se", "correction", "Su"):
            if k in nums or (k == "correction" and raw.get(k, "GEEN")
                             not in ("GEEN", "NONE")):
                return _bad_curve(line, u"{0} kan niet bij een rekcurve "
                                  u"(Manson-Coffin); de bridge kent hier "
                                  u"geen gemiddelde-spanningscorrectie "
                                  u"(Morrow, SWT) en geen vermoeiingsgrens."
                                  u" Laat {0} weg.".format(k),
                                  u"{0} is not possible with a strain curve "
                                  u"(Manson-Coffin); the bridge has no "
                                  u"mean-stress correction (Morrow, SWT) and "
                                  u"no fatigue limit here. Remove {0}."
                                  .format(k))
        d["correction"] = "GEEN"
        return d
    elif "Sf" in nums and "b" in nums:
        if scalar("b") >= 0.0 or scalar("Sf") <= 0.0:
            return _bad_curve(line, u"Basquin: Sf > 0 en b < 0 (S = Sf "
                              u"(2N)^b).",
                              u"Basquin: Sf > 0 and b < 0 (S = Sf "
                              u"(2N)^b).")
        d.update({"form": "basquin", "Sf": scalar("Sf"), "b": scalar("b")})
    else:
        return _bad_curve(line, u"geef een tabel (S = [..] MPa, N = [..]), "
                          u"een machtsvorm (S, N, m) of Basquin (Sf, b).",
                          u"give a table (S = [..] MPa, N = [..]), a power "
                          u"form (S, N, m) or Basquin (Sf, b).")
    if "E" in nums:
        return _bad_curve(line, u"E geldt alleen voor een rekcurve "
                          u"(Manson-Coffin: Sf, b, ef, c).",
                          u"E only applies to a strain curve (Manson-Coffin:"
                          u" Sf, b, ef, c).")
    if "Se" in nums:
        if d["form"] == "table":
            return _bad_curve(line, u"Se geldt voor de macht- en "
                              u"Basquin-vorm; bij een tabel bepaalt "
                              u"PROL_GAUCHE wat er onder de tabel gebeurt.",
                              u"Se applies to the power and Basquin forms; "
                              u"for a table PROL_GAUCHE decides what happens "
                              u"below the table.")
        d["Se"] = scalar("Se")
    corr = _CORRECTIONS.get(raw.get("correction", "GEEN"))
    if corr is None:
        return _bad_curve(line, u"correctie = GEEN, GOODMAN of GERBER.",
                          u"correction = NONE, GOODMAN or GERBER.")
    d["correction"] = corr
    if "Su" in nums:
        d["Su"] = scalar("Su")
    if corr != "GEEN" and not d.get("Su", 0.0) > 0.0:
        return _bad_curve(line, u"correctie {0} vraagt de treksterkte Su "
                          u"(bijv. Su = 500 MPa).".format(corr),
                          u"correction {0} needs the tensile strength Su "
                          u"(e.g. Su = 500 MPa).".format(corr))
    return d


def _bad_option(body, why_nl, why_en):
    log(tr(u"ERROR: #ASTER-VERMOEIING {0}: {1}",
           u"ERROR: #ASTER-FATIGUE {0}: {1}").format(
               body.strip(), tr(why_nl, why_en)))
    return None


def _parse_options(bodies):
    """#ASTER-VERMOEIING lines -> dict, or None (ERROR)."""
    out = {"stress": "VMIS_SG", "counting": "RAINFLOW", "repeats": 1.0,
           "strain": "PRIN", "criterion": "GEEN", "loading": "PERIODIQUE",
           "projection": "UN_AXE"}
    for body in bodies:
        for part in _split_top(body):
            key, eq, value = part.partition("=")
            k = _OPTION_KEYS.get(key.strip().lower())
            value = value.strip().strip("'\"")
            if not eq or k is None:
                log(tr(u"ERROR: #ASTER-VERMOEIING {0}: onbekend: '{1}' "
                       u"(sleutels: spanning, telling, herhalingen, rek, "
                       u"criterium, a, b, c, formule, belasting, "
                       u"projectie).",
                       u"ERROR: #ASTER-FATIGUE {0}: unknown: '{1}' (keys: "
                       u"stress, counting, repeats, strain, criterion, a, b, "
                       u"c, formula, loading, projection).").format(
                           body, part))
                return None
            if k == "formula":
                if not value.strip():
                    return _bad_option(body, u"formule is leeg.",
                                       u"formula is empty.")
                out[k] = value.strip()
                continue
            if k in ("a", "c"):
                got = _numbers(value)
                if got is None or got[2] or got[1]:
                    return _bad_option(body, u"{0} = {1}: verwacht een getal "
                                       u"zonder eenheid.".format(k, value),
                                       u"{0} = {1}: expected a number "
                                       u"without unit.".format(k, value))
                out[k] = got[0][0]
                continue
            if k == "b":
                got = _numbers(value)
                if got is None or got[2] or \
                        _unit_key(got[1] or u"") not in _STRESS_UNITS:
                    return _bad_option(body, u"b = {0}: verwacht een "
                                       u"spanning met eenheid (de "
                                       u"vermoeiingsgrens van het criterium, "
                                       u"bijv. b = 120 MPa).".format(value),
                                       u"b = {0}: expected a stress with "
                                       u"unit (the fatigue limit of the "
                                       u"criterion, e.g. b = 120 MPa)."
                                       .format(value))
                out[k] = parse_and_convert(u"{0!r} {1}".format(
                    got[0][0], got[1]), "pressure")
                continue
            if k == "repeats":
                try:
                    out[k] = float(value)
                except ValueError:
                    out[k] = -1.0
                if out[k] < 0.0:
                    log(tr(u"ERROR: #ASTER-VERMOEIING herhalingen = {0}: "
                           u"verwacht een getal >= 0.",
                           u"ERROR: #ASTER-FATIGUE repeats = {0}: expected "
                           u"a number >= 0.").format(value))
                    return None
                continue
            value = value.upper().replace(" ", "_").replace("-", "_")
            if k == "loading":
                if value not in _LOADINGS:
                    log(tr(u"ERROR: #ASTER-VERMOEIING {0} = {1}: kies "
                           u"PERIODIEK / NIET_PERIODIEK.",
                           u"ERROR: #ASTER-FATIGUE {0} = {1}: choose "
                           u"PERIODIC / NON_PERIODIC.").format(
                               key.strip(), value))
                    return None
                out[k] = _LOADINGS[value]
                continue
            if k == "criterion" and value in ("NONE", "DANGVAN"):
                value = {"NONE": "GEEN", "DANGVAN": "DANG_VAN"}[value]
            allowed = {"stress": _STRESS_KINDS, "strain": _STRESS_KINDS,
                       "counting": _COUNTINGS, "criterion": _CRITERIA,
                       "projection": _PROJECTIONS}[k]
            if value not in allowed:
                log(tr(u"ERROR: #ASTER-VERMOEIING {0} = {1}: kies {2}.",
                       u"ERROR: #ASTER-FATIGUE {0} = {1}: choose {2}.")
                    .format(key.strip(), value, u" / ".join(allowed)))
                return None
            out[k] = value
    return _check_criterion(out, u", ".join(b.strip() for b in bodies))


def _check_criterion(out, body):
    """Consistency of the multiaxial keys; dict or None (ERROR)."""
    crit = out["criterion"]
    given = [k for k in ("a", "b", "c", "formula") if k in out]
    if crit == "GEEN":
        if given:
            return _bad_option(body, u"{0} geldt alleen met een multiaxiaal "
                               u"criterium (criterium = DANG_VAN, MATAKE, "
                               u"CROSSLAND of FORMULE).".format(
                                   u", ".join(given)),
                               u"{0} only applies with a multiaxial "
                               u"criterion (criterion = DANG_VAN, MATAKE, "
                               u"CROSSLAND or FORMULE).".format(
                                   u", ".join(given)))
        return out
    if crit == "FORMULE":
        if "formula" not in out:
            return _bad_option(body, u"criterium = FORMULE vraagt formule = "
                               u"'...' (bijv. formule = '1.5*(DTAUMA + "
                               u"max(PHYDRM,0))').",
                               u"criterion = FORMULE needs formula = '...' "
                               u"(e.g. formula = '1.5*(DTAUMA + "
                               u"max(PHYDRM,0))').")
        # names (not the exponent of a number such as 1e5)
        names = sorted(set(re.findall(r"(?<![0-9.A-Za-z_])[A-Za-z_]\w*",
                                      out["formula"])))
        params = [n for n in names if n in FORMULA_PARAMS]
        other = [n for n in names if n not in FORMULA_PARAMS and n not in
                 ("max", "min", "abs", "sqrt", "exp", "log", "pi")]
        if not params or other:
            return _bad_option(body, u"formule '{0}': {1}; bekende "
                               u"parameters: {2}.".format(
                                   out["formula"],
                                   u"onbekende naam {0}".format(
                                       u", ".join(other)) if other else
                                   u"geen parameter van Code-Aster",
                                   u", ".join(FORMULA_PARAMS)),
                               u"formula '{0}': {1}; known parameters: {2}."
                               .format(out["formula"],
                                       u"unknown name {0}".format(
                                           u", ".join(other)) if other else
                                       u"no Code-Aster parameter",
                                       u", ".join(FORMULA_PARAMS)))
        out["formula_params"] = params
        for k in ("a", "c"):
            if k in out:
                return _bad_option(body, u"{0} geldt niet bij FORMULE (zet "
                                   u"de constanten in de formule).".format(k),
                                   u"{0} does not apply to FORMULE (put the "
                                   u"constants in the formula).".format(k))
        return out
    if "formula" in out:
        return _bad_option(body, u"formule geldt alleen bij criterium = "
                           u"FORMULE.",
                           u"formula only applies to criterion = FORMULE.")
    missing = [k for k in ("a", "c") if k not in out]
    if missing:
        return _bad_option(body, u"criterium {0} vraagt a en c (ontbreekt: "
                           u"{1}); zie docs/Vermoeiing.md par. 1.7.".format(
                               crit, u", ".join(missing)),
                           u"criterion {0} needs a and c (missing: {1}); see "
                           u"docs/en/Fatigue.md section 1.7.".format(
                               crit, u", ".join(missing)))
    if crit in ("DANG_VAN", "MATAKE") and not 1.0 <= out["c"] <= 1.7321:
        # catalogue defi_materiau.py v17.4: COEF_CISA_TRAC/COEF_FLEX_TORS
        # val_min=1.0, val_max=1.7321
        return _bad_option(body, u"c = {0}: Code-Aster staat voor {1} 1 <= c "
                           u"<= 1,7321 toe (COEF_CISA_TRAC / "
                           u"COEF_FLEX_TORS).".format(out["c"], crit),
                           u"c = {0}: Code-Aster allows 1 <= c <= 1.7321 for "
                           u"{1} (COEF_CISA_TRAC / COEF_FLEX_TORS).".format(
                               out["c"], crit))
    if crit == "CROSSLAND" and out["loading"] != "PERIODIQUE":
        return _bad_option(body, u"CROSSLAND kan alleen periodiek (AMPCIS); "
                           u"kies belasting = PERIODIEK of DANG_VAN/MATAKE.",
                           u"CROSSLAND is only possible periodic (AMPCIS); "
                           u"choose loading = PERIODIC or DANG_VAN/MATAKE.")
    if "b" in out and out["b"] <= 0.0:
        return _bad_option(body, u"b moet > 0 zijn.", u"b must be > 0.")
    return out


def _parse_numbers(body, kind):
    """Numbers of an #ASTER-BLOK/-SIGNAAL line, or None (ERROR)."""
    try:
        return [float(v) for v in body.replace(";", ",").split(",")
                if v.strip()]
    except ValueError:
        log(tr(u"ERROR: #ASTER-{0} {1}: alleen getallen, gescheiden door "
               u"komma's (decimale punt).",
               u"ERROR: #ASTER-{0} {1}: numbers only, separated by commas "
               u"(decimal point).").format(kind, body.strip()))
        return None


def parse(model_data):
    """
    Plan from the #ASTER lines: {"curves": [dict], "options": dict,
    "blocks": [(a, m, n)] or None, "signal": [f] or None}; {} without
    #ASTER-WOHLER; None on an error (ERROR in the log).
    """
    fat = model_data.get("aster_custom", {}).get("fatigue") or []
    if not fat:
        return {}
    if not is_requested(model_data):
        log(tr(u"WARNING: Vermoeiing: #ASTER-VERMOEIING/-BLOK/-SIGNAAL zonder "
               u"#ASTER-WOHLER; geen vermoeiingsberekening.",
               u"WARNING: Fatigue: #ASTER-FATIGUE/-BLOCK/-SIGNAL without "
               u"#ASTER-WOHLER; no fatigue analysis."))
        return {}
    materials = model_data.get("materials", {})
    curves = []
    for kind, body in fat:
        if kind != "wohler":
            continue
        c = _parse_curve(body, materials)
        if c is None:
            return None
        if any(o["material"] == c["material"] for o in curves):
            log(tr(u"ERROR: #ASTER-WOHLER: twee curves voor materiaal "
                   u"'{0}'.", u"ERROR: #ASTER-WOHLER: two curves for "
                   u"material '{0}'.").format(c["material"]))
            return None
        curves.append(c)
    options = _parse_options([b for k, b in fat if k == "options"])
    if options is None:
        return None
    blocks = []
    for kind, body in fat:
        if kind != "block":
            continue
        vals = _parse_numbers(body, "BLOK")
        if vals is None:
            return None
        if len(vals) != 3 or vals[0] < 0.0 or vals[2] <= 0.0:
            log(tr(u"ERROR: #ASTER-BLOK {0}: verwacht 'amplitude, "
                   u"gemiddelde, aantal' (factoren op de statische last; "
                   u"amplitude >= 0, aantal > 0), bijv. '#ASTER-BLOK 1.0, "
                   u"0.0, 1e5'.",
                   u"ERROR: #ASTER-BLOCK {0}: expected 'amplitude, mean, "
                   u"count' (factors on the static load; amplitude >= 0, "
                   u"count > 0), e.g. '#ASTER-BLOCK 1.0, 0.0, 1e5'.")
                .format(body.strip()))
            return None
        blocks.append(tuple(vals))
    signal = []
    for kind, body in fat:
        if kind == "signal":
            vals = _parse_numbers(body, "SIGNAAL")
            if vals is None:
                return None
            signal += vals
    if signal and len(signal) < 2:
        log(tr(u"ERROR: #ASTER-SIGNAAL: minstens twee waarden.",
               u"ERROR: #ASTER-SIGNAL: at least two values."))
        return None
    if blocks and signal:
        log(tr(u"ERROR: Vermoeiing: #ASTER-BLOK en #ASTER-SIGNAAL samen; "
               u"kies een van beide.",
               u"ERROR: Fatigue: #ASTER-BLOCK and #ASTER-SIGNAL together; "
               u"choose one."))
        return None
    crit = options["criterion"]
    if crit != "GEEN":
        bad = [c["material"] for c in curves if c["form"] == "strain"]
        if bad:
            log(tr(u"ERROR: Vermoeiing: criterium = {0} rekent met "
                   u"spanningen (kritiek vlak); de rekcurve (Manson-Coffin) "
                   u"van {1} past daar niet bij. Gebruik een Wohler-curve "
                   u"(tabel, macht of Basquin) of laat criterium weg.",
                   u"ERROR: Fatigue: criterion = {0} works with stresses "
                   u"(critical plane); the strain curve (Manson-Coffin) of "
                   u"{1} does not fit. Use a Wohler curve (table, power or "
                   u"Basquin) or remove criterion.").format(
                       crit, u", ".join(bad)))
            return None
        bad = [c["material"] for c in curves if c["correction"] != "GEEN"]
        if bad:
            log(tr(u"ERROR: Vermoeiing: criterium = {0} heeft zijn eigen "
                   u"term voor de gemiddelde spanning (a x P_max of "
                   u"N_max); correctie {1} bij {2} kan daar niet bij. "
                   u"Verwijder correctie.",
                   u"ERROR: Fatigue: criterion = {0} has its own mean-stress "
                   u"term (a x P_max or N_max); correction {1} for {2} "
                   u"cannot be combined. Remove correction.").format(
                       crit, curves[0]["correction"], u", ".join(bad)))
            return None
        if blocks and options["loading"] != "PERIODIQUE":
            log(tr(u"ERROR: Vermoeiing: #ASTER-BLOK met belasting = "
                   u"NIET_PERIODIEK kan niet: een blok is een periodieke "
                   u"cyclus. Kies belasting = PERIODIEK of een "
                   u"#ASTER-SIGNAAL.",
                   u"ERROR: Fatigue: #ASTER-BLOCK with loading = "
                   u"NON_PERIODIC is not possible: a block is a periodic "
                   u"cycle. Choose loading = PERIODIC or an "
                   u"#ASTER-SIGNAL."))
            return None
    return {"curves": curves, "options": options,
            "blocks": blocks or None, "signal": signal or None}


# ==========================================
# .COMM
# ==========================================
def csv_path(work_dir=None):
    """Cycle table of this run (<model>_<run_id>_vermoeiing.csv)."""
    return os.path.join(work_dir or work_dir_path(),
                        run_name(CSV_SUFFIX))


def _py(text):
    return "r'{0}'".format(text) if "'" not in text else repr(text)


def _materials_of(model_data, modelisations):
    """Materials with at least one elset with one of these MODELISATIONs."""
    mods = model_data.get("elset_modelisations", {})
    elsets = model_data.get("elsets", {})
    return set(elsets.get(g) for g, mod in mods.items()
               if mod in modelisations)


def _volume_materials(model_data):
    """Materials with at least one solid elset."""
    return _materials_of(model_data, _VOLUME)


def _groups_of(model_data, mats, modelisations):
    """Code-Aster group names (bridge_mesh) of the elsets with these
    materials and MODELISATIONs, in order."""
    mods = model_data.get("elset_modelisations", {})
    elsets = model_data.get("elsets", {})
    return sorted(g for g, mod in mods.items()
                  if mod in modelisations and elsets.get(g) in mats)


def _curve_materials(model_data, curve, pool):
    """Materials (from pool) to which this curve applies; '*' = all
    materials without a curve of their own."""
    if curve["material"] != "*":
        return set([curve["material"]]) & pool
    named = set(c["material"] for c in model_data.get("_fat_curves", []))
    return set(m for m in pool if m not in named)


def _resolve_strain_E(model_data, curve, mats):
    """E for a strain curve: own E, else that of the material (with '*'
    the materials must have the same E). True or False (ERROR)."""
    if "E" in curve:
        return True
    props = model_data.get("materials", {})
    values = sorted(set(float(props.get(m, {}).get("E") or 0.0)
                        for m in mats))
    if len(values) != 1 or values[0] <= 0.0:
        log(tr(u"ERROR: #ASTER-WOHLER {0}: de rekcurve (Manson-Coffin) "
               u"vraagt E; de materialen {1} hebben {2}. Geef E = ... GPa "
               u"in de regel.",
               u"ERROR: #ASTER-WOHLER {0}: the strain curve (Manson-Coffin) "
               u"needs E; the materials {1} have {2}. Give E = ... GPa in "
               u"the line.").format(
                   curve["material"], u", ".join(sorted(mats)),
                   u", ".join("%g Pa" % v for v in values) or u"-"))
        return False
    curve["E"] = values[0]
    return True


def wohler_points(curve, life_max=1.0e12):
    """
    Wohler curve as points for DEFI_FONCTION (Code-Aster: FATIGUE WOHLER
    in DEFI_MATERIAU, needed for CALC_FATIGUE FATIGUE_MULTI). Returns
    (S [Pa], N, INTERPOL, PROL_GAUCHE, PROL_DROITE).
    In the fatigue routines Code-Aster extends PROL 'LINEAIRE' linearly in
    (S, N), also with INTERPOL='LOG' (measured, S8; docs/Vermoeiing.md
    par. 3). Therefore the bridge puts a log-log extension as extra points
    in the table (up to N = life_max on the left and N = 1 on the right)
    and lets Code-Aster use EXCLU beyond that (no damage, measured:
    NBRUP = 0 and ENDO ~ 1e-308) or CONSTANT. Power and Basquin are
    straight lines in log-log: two points are exact.
    """
    import math
    form = curve["form"]
    if form == "table":
        s, n = list(curve["S"]), list(curve["N"])
        if curve.get("interpol", "LOG") != "LOG":
            return (s, n, "LIN", curve.get("prol_gauche", "EXCLU"),
                    curve.get("prol_droite", "LINEAIRE"))
        left = curve.get("prol_gauche", "EXCLU")
        right = curve.get("prol_droite", "LINEAIRE")
        if left == "LINEAIRE" and n[0] < life_max:
            k0 = (math.log(n[1]) - math.log(n[0])) / (math.log(s[1]) -
                                                      math.log(s[0]))
            if k0 < 0.0:
                s.insert(0, math.exp(math.log(s[0]) + (math.log(life_max) -
                                                       math.log(n[0])) / k0))
                n.insert(0, life_max)
            left = "EXCLU"
        if right == "LINEAIRE" and n[-1] > 1.0:
            k1 = (math.log(n[-1]) - math.log(n[-2])) / (math.log(s[-1]) -
                                                        math.log(s[-2]))
            if k1 < 0.0:
                s.append(math.exp(math.log(s[-1]) - math.log(n[-1]) / k1))
                n.append(1.0)
            right = "CONSTANT"
        elif right == "LINEAIRE":
            right = "CONSTANT"
        return s, n, "LOG", left, right
    if form == "power":
        def s_of(nn):
            return curve["S"] * (curve["N"] / nn) ** (1.0 / curve["m"])
    else:
        def s_of(nn):
            return curve["Sf"] * (2.0 * nn) ** curve["b"]
    lo_n = life_max
    se = curve.get("Se")
    if se is not None and se > s_of(life_max):
        if form == "power":
            lo_n = curve["N"] * (curve["S"] / se) ** curve["m"]
        else:
            lo_n = 0.5 * (se / curve["Sf"]) ** (1.0 / curve["b"])
    return [s_of(lo_n), s_of(1.0)], [lo_n, 1.0], "LOG", "EXCLU", "CONSTANT"


def _signal_cycles(signal):
    """Number of turning points within the signal (periodically closed) / 2:
    more than 1 means more than one cycle per period."""
    r = []
    for v in signal:
        if r and v == r[-1]:
            continue
        if len(r) >= 2 and (r[-1] - r[-2]) * (v - r[-1]) > 0.0:
            r[-1] = v
        else:
            r.append(v)
    return max(1, (len(r) - 1) // 2)


def _check_routes(model_data, plan, analysis):
    """List of curves that take part (or None/[] with a message)."""
    multi = plan["options"]["criterion"] != "GEEN"
    vol = _volume_materials(model_data)
    shell = _materials_of(model_data, _SHELL)
    model_data["_fat_curves"] = plan["curves"]
    curves = []
    for c in plan["curves"]:
        on_vol = _curve_materials(model_data, c, vol)
        on_shell = _curve_materials(model_data, c, shell)
        if c["form"] == "strain" and on_shell:
            log(tr(u"WARNING: Vermoeiing: de rekcurve (Manson-Coffin) van "
                   u"'{0}' werkt alleen op volume-elementen; de schalen "
                   u"({1}) krijgen geen schade (geen rek per laag).",
                   u"WARNING: Fatigue: the strain curve (Manson-Coffin) of "
                   u"'{0}' only works on solid elements; the shells ({1}) "
                   u"get no damage (no strain per layer).").format(
                       c["material"], u", ".join(sorted(on_shell))))
            on_shell = set()
        if multi and on_shell:
            log(tr(u"WARNING: Vermoeiing: criterium = {0} werkt alleen op "
                   u"volume-elementen (CALC_FATIGUE op SIGM_NOEU); de "
                   u"schalen ({1}) krijgen geen schade. Laat criterium weg "
                   u"voor schalen (boven- en onderzijde, VMIS_SG/PRIN).",
                   u"WARNING: Fatigue: criterion = {0} only works on solid "
                   u"elements (CALC_FATIGUE on SIGM_NOEU); the shells ({1}) "
                   u"get no damage. Remove criterion for shells (top and "
                   u"bottom, VMIS_SG/PRIN).").format(
                       plan["options"]["criterion"],
                       u", ".join(sorted(on_shell))))
            on_shell = set()
        if not on_vol and not on_shell:
            log(tr(u"WARNING: Vermoeiing: materiaal '{0}' zit niet in "
                   u"volume- of schaalelementen; vermoeiing alleen op "
                   u"volume-elementen en schalen (balken niet).",
                   u"WARNING: Fatigue: material '{0}' is not in solid or "
                   u"shell elements; fatigue only on solid elements and "
                   u"shells (not beams).").format(c["material"]))
            continue
        if c["form"] == "strain" and not _resolve_strain_E(model_data, c,
                                                           on_vol):
            return None
        c = dict(c)
        c["_vol"] = sorted(on_vol)
        c["_shell"] = sorted(on_shell)
        curves.append(c)
    if not curves:
        log(tr(u"WARNING: Vermoeiing: geen volume- of schaalelementen met "
               u"een Wohler-curve; geen vermoeiingsberekening.",
               u"WARNING: Fatigue: no solid or shell elements with a Wohler "
               u"curve; no fatigue analysis."))
    return curves


def fatigue_block(model_data, analysis, work_dir):
    """
    .comm code after CALC_CHAMP (aster_fatigue.compute or, with criterium,
    CALC_FATIGUE FATIGUE_MULTI + aster_fatigue.compute_multi) and the extra
    argument for export_results. Returns (code, export_arg); ("", "")
    without fatigue (or skipped with a WARNING); None on an error.
    """
    plan = parse(model_data)
    if plan is None:
        return None
    if not plan:
        return "", ""
    solver = analysis.get("solver_command")
    static = solver == "MECA_STATIQUE"
    if static and not (plan["blocks"] or plan["signal"]):
        log(tr(u"WARNING: Vermoeiing: een lineair statische analyse heeft "
               u"een belastingsverloop nodig: #ASTER-BLOK (amplitude, "
               u"gemiddelde, aantal) of #ASTER-SIGNAAL (factoren op de "
               u"statische last). Geen vermoeiingsberekening.",
               u"WARNING: Fatigue: a linear static analysis needs a load "
               u"history: #ASTER-BLOCK (amplitude, mean, count) or "
               u"#ASTER-SIGNAL (factors on the static load). No fatigue "
               u"analysis."))
        return "", ""
    if not static and (plan["blocks"] or plan["signal"]):
        log(tr(u"WARNING: Vermoeiing: #ASTER-BLOK/#ASTER-SIGNAAL gelden "
               u"alleen bij lineair statisch; hier zijn de tijdstappen van "
               u"de run het signaal (regels genegeerd).",
               u"WARNING: Fatigue: #ASTER-BLOCK/#ASTER-SIGNAL only apply to "
               u"linear static; here the time steps of the run are the "
               u"signal (lines ignored)."))
        plan["blocks"] = plan["signal"] = None
    curves = _check_routes(model_data, plan, analysis)
    if curves is None:
        return None
    if not curves:
        return "", ""
    if CONFIG_BRIDGE.get("result_route", "liml") != "liml":
        log(tr(u"INFO: Vermoeiing: de velden damage/life gaan alleen via "
               u"result_route 'liml' naar Mecway; met 'tabel' alleen de log "
               u"en de cyclustabel.",
               u"INFO: Fatigue: the fields damage/life only go to Mecway "
               u"with result_route 'liml'; with 'tabel' only the log and "
               u"the cycle table."))
    opts = plan["options"]
    scripts = os.path.dirname(os.path.abspath(__file__))
    route = ("blocks" if plan["blocks"] else "signal" if plan["signal"]
             else "time steps of the run")
    log(u"INFO: Fatigue: {0} curve(s) ({1}), load history: {2}, "
        u"{3}, counting {4}, repeats {5}.".format(
            len(curves), u", ".join(c["material"] for c in curves), route,
            (u"criterion {0} ({1})".format(opts["criterion"],
                                           opts["loading"])
             if opts["criterion"] != "GEEN" else
             u"stress {0}".format(opts["stress"])),
            opts["counting"], opts["repeats"]))
    head = [
        "",
        "# " + "=" * 53,
        "# FATIGUE (bridge: #ASTER-WOHLER, bridge_fatigue.py,",
        "# docs/Vermoeiing.md): damage and life per node (Miner)",
        "# " + "=" * 53,
        "import sys",
        "sys.path.insert(0, {0})".format(_py(scripts)),
        "import aster_fatigue",
    ]
    vol_groups = _groups_of(model_data, set(m for c in curves
                                            for m in c["_vol"]), _VOLUME)
    if opts["criterion"] != "GEEN":
        body = _multi_code(model_data, plan, curves, vol_groups, work_dir,
                           static)
        if body is None:
            return None
        return "\n".join(head + body + [""]), \
            ", node_fields=globals().get('_bridge_vermoeiing')"
    body = []
    if any(c["form"] == "strain" for c in curves) and vol_groups:
        # Total strain per node (EPSI_NOEU; with DEFORMATION='PETIT' the
        # linear strain, catalogue calc_champ.py DEFORMATION)
        body += ["res = CALC_CHAMP(reuse=res, RESULTAT=res, GROUP_MA={0}, "
                 "DEFORMATION=('EPSI_NOEU', ))".format(_tuple(vol_groups))]
    shells = any(c["_shell"] for c in curves)
    for c in curves:
        c.pop("_vol", None)
        c.pop("_shell", None)
    body += [
        "_bridge_vermoeiing = aster_fatigue.compute(",
        "    res, {0}, {1},".format(
            _py(model_data.get("liml_path", "")), _py(csv_path(work_dir))),
        "    {0!r},".format(curves),
        "    {0!r},".format(opts),
        "    blocks={0!r}, signal={1!r},".format(plan["blocks"],
                                                  plan["signal"]),
        "    shells={0})".format(
            "dict((k, globals()[k]) for k in ('res_sup', 'res_inf') if k in "
            "globals())" if shells else "None"),
    ]
    return "\n".join(head + body + [""]), \
        ", node_fields=globals().get('_bridge_vermoeiing')"


def _tuple(names):
    return "(" + "".join("'{0}', ".format(n) for n in names) + ")"


def _num(v):
    return repr(float(v))


def _multi_code(model_data, plan, curves, vol_groups, work_dir, static):
    """
    .comm lines for CALC_FATIGUE TYPE_CALCUL='FATIGUE_MULTI' (catalogue
    calc_fatigue.py v17.4; test case sslv135a). Per material its own
    DEFI_MATERIAU (ELAS, FATIGUE WOHLER, CISA_PLAN_CRIT) and AFFE_MATERIAU,
    separate from fieldmat (only for CALC_FATIGUE). DOMA_NOEUD requires
    SIGM_NOEU and EPSI_NOEU in the result (measured: without EPSI_NOEU
    <EXCEPTION> CALCULEL_29).
    """
    opts = plan["options"]
    crit = opts["criterion"]
    periodic = opts["loading"] == "PERIODIQUE"
    props = model_data.get("materials", {})
    out = [
        "# Multiaxial: critical plane per node (CALC_FATIGUE FATIGUE_MULTI,",
        "# DOMA_NOEUD); requires SIGM_NOEU and EPSI_NOEU",
        "res = CALC_CHAMP(reuse=res, RESULTAT=res, GROUP_MA={0}, "
        "DEFORMATION=('EPSI_NOEU', ))".format(_tuple(vol_groups)),
    ]
    aster_crit = {("DANG_VAN", True): "DANG_VAN_MODI_AC",
                  ("DANG_VAN", False): "DANG_VAN_MODI_AV",
                  ("MATAKE", True): "MATAKE_MODI_AC",
                  ("MATAKE", False): "MATAKE_MODI_AV"}.get((crit, periodic),
                                                           "FORMULE_CRITERE")
    affe = []
    k = 0
    for c in curves:
        s, n, interp, left, right = wohler_points(c)
        for mat in c["_vol"]:
            k += 1
            groups = _groups_of(model_data, set([mat]), _VOLUME)
            p = props.get(mat, {})
            out += [
                "# material {0}".format(_ascii(mat)),
                "_FW{0} = DEFI_FONCTION(NOM_PARA='SIGM', INTERPOL='{1}', "
                "PROL_GAUCHE='{2}', PROL_DROITE='{3}', VALE=({4}))".format(
                    k, interp, left, right, ", ".join(
                        "{0}, {1}".format(_num(a), _num(b))
                        for a, b in zip(s, n))),
            ]
            cisa = ""
            if crit == "DANG_VAN":
                # D_VAN_B is required but does not count in SIGEQ (measured:
                # b = 2 and b = 100 give the same SIGEQ1, NBRUP1)
                cisa = (", CISA_PLAN_CRIT=_F(CRITERE='{0}', D_VAN_A={1}, "
                        "D_VAN_B={2}, COEF_CISA_TRAC={3})".format(
                            aster_crit, _num(opts["a"]),
                            _num(opts.get("b", 1.0)), _num(opts["c"])))
            elif crit == "MATAKE":
                cisa = (", CISA_PLAN_CRIT=_F(CRITERE='{0}', MATAKE_A={1}, "
                        "MATAKE_B={2}, COEF_FLEX_TORS={3})".format(
                            aster_crit, _num(opts["a"]),
                            _num(opts.get("b", 1.0)), _num(opts["c"])))
            out.append(
                "_FM{0} = DEFI_MATERIAU(ELAS=_F(E={1}, NU={2}), "
                "FATIGUE=_F(WOHLER=_FW{0}){3})".format(
                    k, _num(p.get("E") or 1.0), _num(p.get("NU") or 0.0),
                    cisa))
            affe.append("_F(GROUP_MA={0}, MATER=_FM{1})".format(
                _tuple(groups), k))
    out.append("_FCM = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=({0}, ))".format(
        ", ".join(affe)))
    extra = ""
    if crit in ("CROSSLAND", "FORMULE"):
        if crit == "CROSSLAND":
            # Crossland: sqrt(J2) of the amplitude (AMPCIS) + a P_max;
            # szlz107a: "POUR RETROUVER LE CRITERE CROSSLAND" AMPCIS +
            # a*max(PHYDRM,0); measured: AMPCIS = sqrt(J2(delta sigma / 2))
            expr = "{0}*(AMPCIS + {1}*max(PHYDRM, 0))".format(
                _num(opts["c"]), _num(opts["a"]))
            params = ["AMPCIS", "PHYDRM"]
        else:
            expr = opts["formula"]
            params = opts["formula_params"]
        out.append("_FCRIT = FORMULE(VALE={0}, NOM_PARA={1!r})".format(
            repr(str(expr)), [str(x) for x in params]))
        extra = ", FORMULE_GRDEQ=_FCRIT, COURBE_GRD_VIE='WOHLER'"
    if periodic and aster_crit != "FORMULE_CRITERE":
        extra += ", METHODE='CERCLE_EXACT'"
    if not periodic:
        extra += ", PROJECTION='{0}'".format(opts["projection"])
    if static:
        idx = "res.getIndexes()[0]"
        out += [
            "# Static stress and strain x the factors of the signal or",
            "# block as a result with time steps (CREA_RESU AFFE)",
            "_FS0 = CREA_CHAMP(TYPE_CHAM='NOEU_SIEF_R', OPERATION='EXTR', "
            "RESULTAT=res, NOM_CHAM='SIGM_NOEU', NUME_ORDRE={0})".format(idx),
            "_FE0 = CREA_CHAMP(TYPE_CHAM='NOEU_EPSI_R', OPERATION='EXTR', "
            "RESULTAT=res, NOM_CHAM='EPSI_NOEU', NUME_ORDRE={0})".format(idx),
            "def _fat_resu(factors):",
            "    _r = CREA_RESU(OPERATION='AFFE', TYPE_RESU='EVOL_ELAS', "
            "NOM_CHAM='SIGM_NOEU', AFFE=[_F(CHAM_GD=_FS0 * float(f), "
            "INST=float(i), MODELE=model, CHAM_MATER=fieldmat) for i, f in "
            "enumerate(factors)])",
            "    _r = CREA_RESU(reuse=_r, RESULTAT=_r, OPERATION='AFFE', "
            "TYPE_RESU='EVOL_ELAS', NOM_CHAM='EPSI_NOEU', AFFE=[_F("
            "CHAM_GD=_FE0 * float(f), INST=float(i), MODELE=model, "
            "CHAM_MATER=fieldmat) for i, f in enumerate(factors)])",
            "    return _r",
        ]
        if plan["blocks"]:
            out.append("_FRES = [(_fat_resu([m_ - a_, m_ + a_]), n_) for "
                       "a_, m_, n_ in {0!r}]".format(plan["blocks"]))
        else:
            out.append("_FRES = [(_fat_resu({0!r}), 1.0)]".format(
                plan["signal"]))
            if periodic and _signal_cycles(plan["signal"]) > 1:
                log(tr(u"WARNING: Vermoeiing: belasting = PERIODIEK telt "
                       u"een cyclus per signaal (het grootste bereik over "
                       u"het hele signaal, CALC_FATIGUE PERIODIQUE); dit "
                       u"signaal heeft er meer. Kies belasting = "
                       u"NIET_PERIODIEK (rainflow op het kritieke vlak) of "
                       u"geef blokken.",
                       u"WARNING: Fatigue: loading = PERIODIC counts one "
                       u"cycle per signal (the largest range over the whole "
                       u"signal, CALC_FATIGUE PERIODIQUE); this signal has "
                       u"more. Choose loading = NON_PERIODIC (rainflow on the "
                       u"critical plane) or give blocks."))
    else:
        out += [
            "# Copy as EVOL_ELAS with all time steps: CALC_FATIGUE",
            "# FATIGUE_MULTI skips NUME_ORDRE 0 (the initial state of",
            "# STAT_NON_LINE/DYNA_NON_LINE) (alarm PREPOST4_27; measured:",
            "# a ramp 0 -> 1 gave half the amplitude). After CREA_RESU the",
            "# numbering starts at 1 and the initial state counts, as in the",
            "# uniaxial route.",
            "def _fat_copy(r):",
            "    _i = list(r.getIndexes())",
            "    _c = CREA_RESU(OPERATION='AFFE', TYPE_RESU='EVOL_ELAS', "
            "NOM_CHAM='SIGM_NOEU', AFFE=[_F(CHAM_GD=r.getField('SIGM_NOEU', "
            "i), INST=r.getTime(i), MODELE=model, CHAM_MATER=fieldmat) for i "
            "in _i])",
            "    _c = CREA_RESU(reuse=_c, RESULTAT=_c, OPERATION='AFFE', "
            "TYPE_RESU='EVOL_ELAS', NOM_CHAM='EPSI_NOEU', AFFE=[_F("
            "CHAM_GD=r.getField('EPSI_NOEU', i), INST=r.getTime(i), "
            "MODELE=model, CHAM_MATER=fieldmat) for i in _i])",
            "    return _c",
            "_FRES = [(_fat_copy(res), 1.0)]",
        ]
    out += [
        "_FCHAM = [(CALC_FATIGUE(TYPE_CALCUL='FATIGUE_MULTI', "
        "OPTION='DOMA_NOEUD', TYPE_CHARGE='{0}', RESULTAT=r_, "
        "CHAM_MATER=_FCM, MAILLAGE=mesh, GROUP_MA={1}, CRITERE='{2}'{3}), "
        "n_) for r_, n_ in _FRES]".format(opts["loading"],
                                         _tuple(vol_groups), aster_crit,
                                         extra),
    ]
    for c in curves:
        c.pop("_vol", None)
        c.pop("_shell", None)
    out += [
        "_bridge_vermoeiing = aster_fatigue.compute_multi(",
        "    _FCHAM, {0}, {1},".format(
            _py(model_data.get("liml_path", "")), _py(csv_path(work_dir))),
        "    {0!r},".format(curves),
        "    {0!r})".format(dict(list(opts.items()) + [(
            "route", "blocks" if plan["blocks"] else "signal" if
            plan["signal"] else "history")])),
    ]
    return out


def _ascii(text):
    return u"".join(ch if ord(ch) < 128 else u"?" for ch in u"{0}".format(
        text)).replace("\n", " ")


def unsupported_warning(model_data, solver_cmd):
    """WARNING if there is a Wohler curve in an analysis without
    fatigue (only MECA_STATIQUE, STAT_NON_LINE, DYNA_NON_LINE)."""
    if is_requested(model_data) and solver_cmd not in (
            "MECA_STATIQUE", "STAT_NON_LINE", "DYNA_NON_LINE"):
        log(tr(u"WARNING: Vermoeiing (#ASTER-WOHLER) werkt alleen bij "
               u"lineair statisch (met #ASTER-BLOK/-SIGNAAL), niet-lineair "
               u"statisch en dynamisch (DYNA_NON_LINE), niet bij {0}; geen "
               u"schade.",
               u"WARNING: Fatigue (#ASTER-WOHLER) only works for linear "
               u"static (with #ASTER-BLOCK/-SIGNAL), nonlinear static and "
               u"dynamic (DYNA_NON_LINE), not for {0}; no damage.").format(
                   solver_cmd))


# ==========================================
# AFTER THE RUN
# ==========================================
_KV_RE = re.compile(r"(\w+)=(\S+)")


def read_summary(mess_path):
    """{"MAX": {...}, "INFO": {...}, "WARN": {...}, "FOUT": text} from the
    lines BRIDGE_VERMOEIING_* (aster_fatigue), or {}."""
    out = {}
    if not mess_path or not os.path.isfile(mess_path):
        return out
    with io.open(mess_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("BRIDGE_ONVOLLEDIG"):
                out["ONVOLLEDIG"] = line.split()[-1]
            if not line.startswith("BRIDGE_VERMOEIING_"):
                continue
            head, _sp, rest = line.strip().partition(" ")
            kind = head[len("BRIDGE_VERMOEIING_"):]
            if kind == "FOUT":
                out["FOUT"] = rest
            elif kind == "CSV":
                out["CSV"] = rest
            else:
                d = {}
                rest, _m, mat = rest.partition(" MATERIAL=")
                if _m:
                    d["MATERIAL"] = mat.strip()
                for k, v in _KV_RE.findall(rest):
                    try:
                        d[k] = float(v)
                    except ValueError:
                        d[k] = v
                out[kind] = d
    return out


def report(work_dir=None, mess_path=None):
    """Lines for log and status box (empty without fatigue). WARNING for
    D >= 1, cycles above the Wohler table and a mean >= Su."""
    s = read_summary(mess_path)
    if not [k for k in s if k != "ONVOLLEDIG"]:
        return []
    out = []
    if "FOUT" in s:
        text = tr(u"WARNING: Vermoeiing mislukt in de Code-Aster-job: {0}. "
                  u"Zie de .mess (traceback).",
                  u"WARNING: Fatigue failed in the Code-Aster job: {0}. See "
                  u"the .mess (traceback).").format(s["FOUT"])
        log(text)
        return [text[len("WARNING: "):]]
    mx, info = s.get("MAX", {}), s.get("INFO", {})
    if not mx:
        return []
    d = mx.get("D", 0.0)
    repeats = info.get("REPEATS", 1.0)
    life = mx.get("LIFE", 0.0)
    route = info.get("ROUTE", "")
    what = {"blocks": tr(u"het blokkenspectrum", u"the block spectrum"),
            "signal": tr(u"het signaal", u"the signal"),
            "history": tr(u"het verloop van de run (alle tijdstappen)",
                          u"the history of the run (all time steps)")}.get(
                              route, route)
    line = tr(u"Vermoeiing: grootste schade D = {0} in knoop {1} ({2}, {3}, "
              u"{4}) m, materiaal {5}, na {6} herhaling(en) van {7}; "
              u"levensduur daar {8} herhalingen ({9} cycli per herhaling, "
              u"telling {10}, spanning {11}). {12} knopen berekend, {13} met "
              u"D >= 1. Velden in Mecway: damage, life. Cyclustabel: {14}",
              u"Fatigue: largest damage D = {0} at node {1} ({2}, {3}, {4}) "
              u"m, material {5}, after {6} repetition(s) of {7}; life there "
              u"{8} repetitions ({9} cycles per repetition, counting {10}, "
              u"stress {11}). {12} nodes computed, {13} with D >= 1. Fields "
              u"in Mecway: damage, life. Cycle table: {14}").format(
                  "%.4g" % d, int(mx.get("NODE", 0)),
                  "%.4g" % mx.get("X", 0.0), "%.4g" % mx.get("Y", 0.0),
                  "%.4g" % mx.get("Z", 0.0),
                  u"{0}".format(mx.get("MATERIAL", "?")),
                  "%g" % repeats, what, "%.4g" % life,
                  "%g" % mx.get("CYCLES", 0.0), info.get("COUNTING", "?"),
                  info.get("STRESS", "?"), int(info.get("NODES", 0)),
                  int(info.get("FAILED", 0)),
                  os.path.basename(s.get("CSV", "") or csv_path(work_dir)))
    multi = s.get("MULTI", {})
    if multi:
        what = u"{0}".format(multi.get("CRIT", "?"))
        if "EQ" in multi:
            line += tr(u" Multiaxiaal ({0}): equivalente spanning daar {1} "
                       u"MPa (veld fatigue_eq)",
                       u" Multiaxial ({0}): equivalent stress there {1} MPa "
                       u"(field fatigue_eq)").format(
                           what, "%.4g" % (multi["EQ"] / 1.0e6))
            if "RATIO_MAX" in multi:
                line += tr(u", grootste criteriumwaarde (tau_a + a P)/b = "
                           u"{0} (veld fatigue_ratio; > 1: boven de "
                           u"vermoeiingsgrens van het criterium)",
                           u", largest criterion value (tau_a + a P)/b = {0} "
                           u"(field fatigue_ratio; > 1: above the fatigue "
                           u"limit of the criterion)").format(
                               "%.4g" % multi["RATIO_MAX"])
            line += u"."
        else:
            line += tr(u" Multiaxiaal ({0}, niet-periodiek): schade van "
                       u"Code-Aster (rainflow op het kritieke vlak).",
                       u" Multiaxial ({0}, non-periodic): damage from "
                       u"Code-Aster (rainflow on the critical plane).").format(
                           what)
    elif info.get("LAYER") in ("top", "bottom"):
        line += tr(u" De grootste schade zit in een schaal, {0} (velden "
                   u"damage_top en damage_bottom).",
                   u" The largest damage is in a shell, {0} (fields "
                   u"damage_top and damage_bottom).").format(
                       tr(u"bovenzijde", u"top side") if info["LAYER"] ==
                       "top" else tr(u"onderzijde", u"bottom side"))
    log(u"INFO: " + line)
    out.append(line)
    warns = []
    if d >= 1.0:
        warns.append(tr(u"WARNING: Vermoeiing: schade D = {0} >= 1 in {1} "
                        u"knoop/knopen: breuk volgens Miner binnen {2} "
                        u"herhaling(en). Verlaag de spanning of het aantal "
                        u"herhalingen, of controleer de Wohler-curve.",
                        u"WARNING: Fatigue: damage D = {0} >= 1 at {1} "
                        u"node(s): failure according to Miner within {2} "
                        u"repetition(s). Lower the stress or the number of "
                        u"repetitions, or check the Wohler curve.").format(
                            "%.4g" % d, int(info.get("FAILED", 0)),
                            "%g" % repeats))
    if "ONVOLLEDIG" in s and route == "history":
        warns.append(tr(u"WARNING: Vermoeiing: de run stopte voor de eindtijd "
                        u"(t = {0}); de schade geldt alleen voor het "
                        u"berekende deel van het verloop.",
                        u"WARNING: Fatigue: the run stopped before the end "
                        u"time (t = {0}); the damage only covers the computed "
                        u"part of the history.").format(s["ONVOLLEDIG"]))
    w = s.get("WARN", {})
    if w.get("ABOVE"):
        warns.append(tr(u"WARNING: Vermoeiing: in {0} knoop/knopen is een "
                        u"amplitude groter dan de hoogste S van de "
                        u"Wohler-tabel; N is daar doorgetrokken "
                        u"(PROL_DROITE). Breid de tabel uit naar hogere "
                        u"spanningen.",
                        u"WARNING: Fatigue: at {0} node(s) an amplitude "
                        u"exceeds the highest S of the Wohler table; N is "
                        u"extrapolated there (PROL_DROITE). Extend the "
                        u"table to higher stresses.").format(
                            int(w["ABOVE"])))
    if w.get("MEAN_SU"):
        warns.append(tr(u"WARNING: Vermoeiing: in {0} knoop/knopen is de "
                        u"gemiddelde spanning van een cyclus >= Su (statisch "
                        u"bezwijken); die cycli tellen als N = 1.",
                        u"WARNING: Fatigue: at {0} node(s) the mean stress "
                        u"of a cycle is >= Su (static failure); those "
                        u"cycles count as N = 1.").format(int(w["MEAN_SU"])))
    if w.get("N_BELOW_1"):
        warns.append(tr(u"WARNING: Vermoeiing: in {0} knoop/knopen geeft de "
                        u"Wohler-curve N < 1 (boven het bereik van de "
                        u"curve); daar geldt N = 1.",
                        u"WARNING: Fatigue: at {0} node(s) the Wohler curve "
                        u"gives N < 1 (above the range of the curve); N = 1 "
                        u"is used there.").format(int(w["N_BELOW_1"])))
    for text in warns:
        log(text)
        out.append(text[len("WARNING: "):])
    return out
