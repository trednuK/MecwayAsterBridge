# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_metallurgy.py
# Responsibility: metallurgy of steel in welding (step S5): the
# phase transformations (ferrite, pearlite, bainite, martensite; austenite
# on heating) from the temperature history of a transient thermal
# analysis (Mecway T31 -> ther_3d, bridge_thermal.py), the hardness, and
# optionally their influence on the residual stress in the chain
# thermal -> mechanical (bridge_thermomech.py).
#
# Input: Mecway has no metallurgy. A line in a free text field
# (bridge_custom.py), per Mecway material, like #ASTER-MATERIAAL:
#   #ASTER-METALLURGIE Staal: staal=16MND5
#   #ASTER-METALLURGIE Staal: staal=16MND5, begin=bainiet, mechanica=ja,
#   #ASTER-METALLURGIE     ALPHA_A=2.35e-5, DEPS=1.0e-2
#   #ASTER-METALLURGIE Staal: trc=MIJN_TRC, AR3=830, MS0=415, ...
# (a line that starts with '<material>:' starts a material; also
# #ASTER-METALLURGY). 'staal' picks a standard data set (DATASETS: CCT
# diagram and META_ACIER from a Code-Aster test case); 'trc' a DEFI_TRC
# that the user writes in #ASTER code. See docs/Lassen.md par. 10.
#
# Code-Aster 17.4 (catalogues calc_meta.py, defi_trc.py, defi_materiau.py
# META_ACIER / DURT_META / ELAS_META_FO / META_ECRO_LINE; syntax source
# test cases hsnv101a, mtlp100b, mtlp103a):
#   - META_ACIER (and DURT_META) in the thermal DEFI_MATERIAU (like
#     hsnv101a: THER + META_ACIER in one material; a separate CHAM_MATER
#     for CALC_META gave alarm RESULT1_39 at every step);
#   - CALC_META reuse=res, ETAT_INIT META_INIT_ELNO (CART_VAR2_R V1..V7 =
#     ferrite, pearlite, bainite, martensite, austenite, sum of cold
#     phases, grain size), COMPORTEMENT RELATION='ACIER' (Waeckel), OPTION
#     META_ELNO/META_NOEU and DURT_ELNO/DURT_NOEU;
#   - META_NOEU has V1..V9: the five phases, V6 sum of cold phases, V7
#     grain size, V8 temperature, V9 Ms (seen in a run, MT-01);
#   - mechanical (mechanica=ja): AFFE_VARC NOM_VARC='M_ACIER' (EVOL =
#     thermal result, NOM_CHAM='META_ELNO'), ELAS_META_FO +
#     META_ECRO_LINE, COMPORTEMENT RELATION='META_P_IL' RELATION_KIT=
#     ('ACIER',) (hsnv101a); internal variables V1..V5 hardening per
#     phase, V6 sum of cold phases, V7 EPSPEQ, V8 INDIPLAS (seen in the
#     .mess of hsnv101a).
# Temperatures in the .comm are in degrees Celsius (bridge_thermal), as
# are AR3/MS0/AC1/AC3 and the CCT diagrams.
#
#   parse_specs(bodies)             - read #ASTER-METALLURGIE lines
#   apply(tb, model_data, analysis) - (block for the materials, block after
#                                     the thermal solve); sets tb.meta_kw
#   mech_material(...)              - DEFI_MATERIAU with ELAS_META_FO for
#                                     the chain (bridge_thermomech._materials)
#   patch_comportement / varc_entries - chain: RELATION and AFFE_VARC
#   report_lines(mess_path)         - summary after the run (status box)
#
# Compatible with IronPython 2.7.9 (standard library only).

import re
from collections import OrderedDict

from bridge_utils import log, tr

KELVIN = 273.15

# Phases in the order of Code-Aster (Behaviours/acier.py nom_vari:
# FERRITE, PERLITE, BAINITE, MARTENSITE, AUSTENITE) with the Mecway names
# of the bridge (aster_results_export FIELD_TABLE, group "metallurgy").
PHASES = ("ferrite", "pearlite", "bainite", "martensite", "austenite")
FIELD_GROUP = "metallurgy"

# ==========================================
# STANDARD DATA SETS
# ==========================================
# CCT diagram (DEFI_TRC HIST_EXP: per cooling history the cooling rate
# at 700 degrees C [C/s], the grain size, six coefficients and then
# groups of four (Z_ferrite, Z_pearlite, Z_bainite, T [C])), TEMP_MS, and
# META_ACIER/DURT_META as in the test case.
#
# 16MND5 (A508 cl. 3, pressure vessel steel): test case mtlp103a
# (V4.61.103, "trempe d'un barreau cylindrique en 16MND5"), 29 cooling
# histories from 0.05 to 400 C/s, GRAIN_AUST DREF = 11, hardness per
# phase (HV).
_TRC_16MND5 = (
    (
        -0.05, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 758.5,
        0.01, 0, 0, 755, 0.79, 0, 0, 620, 0.8, 0, 0, 616.5, 0.8, 0, 0,
        510, 0.8, 0, 0.01, 495, 0.8, 0, 0.19, 360, 0.8, 0, 0.2, 345),
    (
        -0.1, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 759.1, 0.01,
        0, 0, 755, 0.67, 0, 0, 620, 0.68, 0, 0, 615.9, 0.68, 0, 0,
        524.7, 0.68, 0, 0.01, 515, 0.68, 0, 0.31, 370, 0.68, 0, 0.32,
        360.3),
    (
        -0.15, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 759.5,
        0.01, 0, 0, 755, 0.61, 0, 0, 620, 0.62, 0, 0, 615.5, 0.62, 0,
        0, 538.6, 0.62, 0, 0.01, 530, 0.62, 0, 0.37, 375, 0.62, 0,
        0.38, 366.4),
    (
        -0.2, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 759.9, 0.01,
        0, 0, 755, 0.56, 0, 0, 620, 0.57, 0, 0, 615.1, 0.57, 0, 0,
        547.8, 0.57, 0, 0.01, 540, 0.57, 0, 0.42, 380, 0.57, 0, 0.43,
        372.2),
    (
        -0.3, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 760.6, 0.01,
        0, 0, 755, 0.49, 0, 0, 620, 0.5, 0, 0, 614.4, 0.5, 0, 0, 556.9,
        0.5, 0, 0.01, 550, 0.5, 0, 0.49, 385, 0.5, 0, 0.5, 378.1),
    (
        -0.5, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 761.8, 0.01,
        0, 0, 755, 0.41, 0, 0, 620, 0.42, 0, 0, 613.2, 0.42, 0, 0,
        571.2, 0.42, 0, 0.01, 565, 0.42, 0, 0.57, 390, 0.42, 0, 0.58,
        383.8),
    (
        -1, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 758.6, 0.01,
        0, 0, 750, 0.29, 0, 0, 630, 0.3, 0, 0, 621.4, 0.3, 0, 0, 585.3,
        0.3, 0, 0.01, 580, 0.3, 0, 0.69, 400, 0.3, 0, 0.7, 394.7),
    (
        -1.5, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 755, 0.01,
        0, 0, 745, 0.22, 0, 0, 640, 0.23, 0, 0, 630, 0.23, 0, 0, 595.1,
        0.23, 0, 0.01, 590, 0.23, 0, 0.76, 400, 0.23, 0, 0.77, 394.9),
    (
        -2, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 745.6, 0.01,
        0, 0, 735, 0.17, 0, 0, 650, 0.18, 0, 0, 639.4, 0.18, 0, 0,
        599.9, 0.18, 0, 0.01, 595, 0.18, 0, 0.81, 400, 0.18, 0, 0.82,
        395.1),
    (
        -3, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 730, 0.01, 0,
        0, 720, 0.11, 0, 0, 670, 0.12, 0, 0, 660, 0.12, 0, 0, 604.7,
        0.12, 0, 0.01, 600, 0.12, 0, 0.87, 400, 0.12, 0, 0.88, 395.3),
    (
        -4, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 722, 0.01, 0,
        0, 710, 0.06, 0, 0, 680, 0.07, 0, 0, 668, 0.07, 0, 0, 604.4,
        0.07, 0, 0.01, 600, 0.07, 0, 0.92, 400, 0.07, 0, 0.93, 395.6),
    (
        -5, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 720, 0.01, 0,
        0, 700, 0.02, 0, 0, 690, 0.03, 0, 0, 670, 0.03, 0, 0, 604.2,
        0.03, 0, 0.01, 600, 0.03, 0, 0.96, 400, 0.03, 0, 0.97, 395.8),
    (
        -6, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 604.1, 0, 0,
        0.01, 600, 0, 0, 0.99, 400, 0, 0, 1, 395.9),
    (
        -7, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 604.1, 0, 0,
        0.01, 600, 0, 0, 0.99, 400, 0, 0, 1, 395.9),
    (
        -8, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 604.1, 0, 0,
        0.01, 600, 0, 0, 0.99, 400, 0, 0, 1, 395.9),
    (
        -9, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 604.3, 0, 0,
        0.01, 600, 0, 0, 0.94, 400, 0, 0, 0.95, 395.7),
    (
        -10, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 599.4, 0, 0,
        0.01, 595, 0, 0, 0.9, 400, 0, 0, 0.91, 395.6),
    (
        -12, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 594.6, 0, 0,
        0.01, 590, 0, 0, 0.83, 400, 0, 0, 0.84, 395.4),
    (
        -15, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 584.9, 0, 0,
        0.01, 580, 0, 0, 0.74, 400, 0, 0, 0.75, 395.1),
    (
        -18, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 580.2, 0, 0,
        0.01, 575, 0, 0, 0.67, 404, 0, 0, 0.68, 398.8),
    (
        -20, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 575.3, 0, 0,
        0.01, 570, 0, 0, 0.63, 406, 0, 0, 0.64, 400.7),
    (
        -25, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 565.7, 0, 0,
        0.01, 560, 0, 0, 0.54, 410, 0, 0, 0.55, 404.3),
    (
        -30, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 555.9, 0, 0,
        0.01, 550, 0, 0, 0.47, 415, 0, 0, 0.48, 409.1),
    (
        -40, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 536.8, 0, 0,
        0.01, 530, 0, 0, 0.35, 415, 0, 0, 0.36, 408.2),
    (
        -50, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 523, 0, 0,
        0.01, 515, 0, 0, 0.26, 415, 0, 0, 0.27, 407),
    (
        -60, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 509.4, 0, 0,
        0.01, 500, 0, 0, 0.19, 415, 0, 0, 0.2, 405.6),
    (
        -80, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830, 0, 0, 0, 492.1, 0, 0,
        0.01, 475, 0, 0, 0.08, 415, 0, 0, 0.09, 397.9),
    (
        -100, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830),
    (
        -400, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 830),
)

# HSNV101A: test case hsnv101a (bar, cooling 900 -> 0 degrees C in 180 s,
# transformation to bainite between 600 and 345 degrees C). Fictitious data
# of the test case (verification MT-01), not a real steel; with the
# mechanical data of the test case (ELAS_META_FO, META_ECRO_LINE).
_TRC_HSNV101A = (
    (
        -1106, 11, 8.563, -0.0276, 0.000122, -2.955e-07, 3.402e-10,
        -1.517e-13, 0, 0, 0, 836, 0, 0, 0, 600.1, 0, 0, 1, 345),
    (
        -2206, 11, 8.563, -0.0276, 0.000122, -2.955e-07, 3.402e-10,
        -1.517e-13, 0, 0, 0, 836, 0, 0, 0, 600.1, 0, 0, 1, 345),
)
# hsnv101a FBM1 / AUS1: D_SIGM_EPSI [Pa] of the cold phases / austenite,
# FBM2 / AUS2: yield stress [Pa], as (T [C], value) pairs.
_FBM1 = (
    0, 4.35314e+09, 20, 4.2574e+09, 40, 4.16157e+09, 60, 4.06564e+09, 80,
    3.96962e+09, 100, 3.8735e+09, 120, 3.77729e+09, 140, 3.68098e+09, 160,
    3.58458e+09, 180, 3.48809e+09, 200, 3.3915e+09, 220, 3.29481e+09, 240,
    3.19803e+09, 260, 3.10116e+09, 280, 3.00419e+09, 300, 2.90712e+09, 320,
    2.80996e+09, 340, 2.7127e+09, 360, 2.61535e+09, 380, 2.5179e+09, 400,
    2.42035e+09, 420, 2.32271e+09, 440, 2.22497e+09, 460, 2.12713e+09, 480,
    2.0292e+09, 500, 1.93117e+09, 520, 1.83304e+09, 540, 1.73482e+09, 560,
    1.6365e+09, 580, 1.53808e+09, 600, 1.43956e+09, 620, 1.34095e+09, 640,
    1.24224e+09, 660, 1.14342e+09, 680, 1.04452e+09, 700, 9.4551e+08, 720,
    8.464e+08, 740, 7.472e+08, 760, 6.4789e+08, 780, 5.4849e+08, 800,
    4.4899e+08, 820, 3.4939e+08, 840, 2.4969e+08, 860, 1.4989e+08, 880,
    4.999e+07, 900, -5.001e+07)
_AUS1 = (
    0, 5.58931e+09, 20, 5.49477e+09, 40, 5.40014e+09, 60, 5.30543e+09, 80,
    5.21062e+09, 100, 5.11571e+09, 120, 5.02072e+09, 140, 4.92563e+09, 160,
    4.83045e+09, 180, 4.73517e+09, 200, 4.6398e+09, 220, 4.54434e+09, 240,
    4.44879e+09, 260, 4.35314e+09, 280, 4.2574e+09, 300, 4.16157e+09, 320,
    4.06564e+09, 340, 3.96962e+09, 360, 3.8735e+09, 380, 3.77729e+09, 400,
    3.68098e+09, 420, 3.58458e+09, 440, 3.48809e+09, 460, 3.3915e+09, 480,
    3.29481e+09, 500, 3.19803e+09, 520, 3.10116e+09, 540, 3.00419e+09, 560,
    2.90712e+09, 580, 2.80996e+09, 600, 2.7127e+09, 620, 2.61535e+09, 640,
    2.5179e+09, 660, 2.42035e+09, 680, 2.32271e+09, 700, 2.22497e+09, 720,
    2.12713e+09, 740, 2.0292e+09, 760, 1.93117e+09, 780, 1.83304e+09, 800,
    1.73482e+09, 820, 1.6365e+09, 840, 1.53808e+09, 860, 1.43956e+09, 880,
    1.34095e+09, 900, 1.24224e+09)
_FBM2 = (0, 8e+07, 900, 5.3e+08)
_AUS2 = (0, -5e+07, 900, 4e+08)


def _pairs(flat):
    """(T [C], v, T, v, ...) -> [(T [K], v)]."""
    return [(flat[i] + KELVIN, float(flat[i + 1]))
            for i in range(0, len(flat), 2)]


DATASETS = OrderedDict([
    ("16MND5", {
        "source": "Code-Aster-testcase mtlp103a (V4.61.103, 16MND5)",
        "trc": _TRC_16MND5,
        "temp_ms": (0.38, -30.791, 11.698, -1.0),
        "grain_aust": {"DREF": 11.0},
        "meta": OrderedDict([("AR3", 830.0), ("ALPHA", -0.0249),
                             ("MS0", 415.0), ("AC1", 724.0),
                             ("AC3", 846.0), ("TAUX_1", 0.34),
                             ("TAUX_3", 0.34)]),
        "hv": (184.0, 184.0, 309.0, 450.0, 100.0),
        "grain": 11.0,
        "mech": None,
    }),
    ("HSNV101A", {
        "source": "Code-Aster-testcase hsnv101a (fictief staal van de "
                  "testcase)",
        "trc": _TRC_HSNV101A,
        "temp_ms": (0.45, -31.25, 14.06, -3497.0),
        "grain_aust": None,
        "meta": OrderedDict([("AR3", 830.0), ("ALPHA", -0.03),
                             ("MS0", 200.0), ("AC1", 724.0),
                             ("AC3", 846.0), ("TAUX_1", 0.34),
                             ("TAUX_3", 0.34)]),
        "hv": None,
        "grain": 10.0,
        "mech": {"ALPHA_F": [(None, 15.0e-6)],
                 "ALPHA_A": [(None, 23.5e-6)],
                 "DEPS": 2.52e-3, "REF": "CHAUD",
                 "SY_F": _pairs(_FBM2), "SY_P": _pairs(_FBM2),
                 "SY_B": _pairs(_FBM2), "SY_M": _pairs(_FBM2),
                 "SY_A": _pairs(_AUS2),
                 "ET_F": _pairs(_FBM1), "ET_P": _pairs(_FBM1),
                 "ET_B": _pairs(_FBM1), "ET_M": _pairs(_FBM1),
                 "ET_A": _pairs(_AUS1)},
    }),
])

# ==========================================
# KEYS
# ==========================================
_META_KEYS = ("AR3", "ALPHA", "MS0", "AC1", "AC3", "TAUX_1", "TAUX_3")
_META_OPT = ("LAMBDA0", "QSR_K", "D10", "WSR_K")
_PH = ("F", "P", "B", "M", "A")         # phase suffixes
_KEYS = OrderedDict(
    [("STAAL", ("staal", "steel", "dataset")),
     ("TRC", ("trc",)),
     ("HV", ("hv", "hardheid", "hardness")),
     ("BEGIN", ("begin", "initial", "start")),
     ("KORREL", ("korrel", "grain")),
     ("MECH", ("mechanica", "mechanics")),
     ("T", ("t", "temp")),
     ("TC", ("tc", "temp_c")),
     ("ALPHA_F", ("alpha_f",)),
     ("ALPHA_A", ("alpha_a", "alpha_c")),
     ("DEPS", ("deps", "epsf_epsc_tref")),
     ("REF", ("ref", "phase_refe")),
     ("SY", ("sy",)),
     ("ET", ("et",)),
     ("H", ("h",))] +
    [(k, (k.lower(),)) for k in _META_KEYS + _META_OPT] +
    [("{0}_{1}".format(q, p), ("{0}_{1}".format(q, p).lower(),))
     for q in ("SY", "ET", "H") for p in _PH])
_ALIAS = dict((a, k) for k, names in _KEYS.items() for a in names)
# Lists (over T/TC) or constants in the mechanical data
_TABLE_KEYS = (("ALPHA_F", "ALPHA_A", "SY", "ET", "H") +
               tuple("{0}_{1}".format(q, p) for q in ("SY", "ET", "H")
                     for p in _PH))
_BEGIN = OrderedDict([
    ("ferriet", (1.0, 0.0, 0.0, 0.0, 0.0)),
    ("ferrite", (1.0, 0.0, 0.0, 0.0, 0.0)),
    ("perliet", (0.0, 1.0, 0.0, 0.0, 0.0)),
    ("pearlite", (0.0, 1.0, 0.0, 0.0, 0.0)),
    ("bainiet", (0.0, 0.0, 1.0, 0.0, 0.0)),
    ("bainite", (0.0, 0.0, 1.0, 0.0, 0.0)),
    ("martensiet", (0.0, 0.0, 0.0, 1.0, 0.0)),
    ("martensite", (0.0, 0.0, 0.0, 1.0, 0.0)),
    ("austeniet", (0.0, 0.0, 0.0, 0.0, 1.0)),
    ("austenite", (0.0, 0.0, 0.0, 0.0, 1.0)),
])
_YES = ("ja", "yes", "oui", "1", "true", "meta", "iso")
_NO = ("nee", "no", "non", "0", "false")


def enabled(model_data):
    """True if the model has #ASTER-METALLURGIE lines."""
    return bool(model_data.get("aster_custom", {}).get("metallurgy"))


def _err(label, nl, en, *args):
    log(tr("ERROR: {0}: " + nl, "ERROR: {0}: " + en).format(label, *args))


def parse_specs(bodies):
    """
    {Mecway material: spec} from the #ASTER-METALLURGIE lines, or None
    (ERROR in the log). spec: "dataset" (name from DATASETS or None), "trc"
    (DEFI_TRC concept of the user or None), "meta" (META_ACIER
    values), "hv" (5 values or None), "begin" (5 fractions), "grain",
    "mech" (bool) and the mechanical data ("T", lists like
    #ASTER-MATERIAAL).
    """
    import bridge_thermomech as btm
    grouped = btm._group(bodies)
    if grouped is None:
        return None
    specs = OrderedDict()
    for name, text in grouped:
        label = "#ASTER-METALLURGIE {0}".format(name)
        raw = OrderedDict()
        for part in btm._split(text):
            key, sep, val = part.partition("=")
            k = _ALIAS.get(key.strip().lower())
            if not sep or k is None:
                _err(label, "onbekend of onvolledig '{1}'. Bekend: {2}.",
                     "unknown or incomplete '{1}'. Known: {2}.", part,
                     ", ".join(_KEYS[k][0] for k in _KEYS))
                return None
            raw[k] = val.strip()
        spec = _make_spec(raw, label)
        if spec is None:
            return None
        if name in specs:
            _err(label, "materiaal staat er twee keer in.",
                 "material appears twice.")
            return None
        specs[name] = spec
    return specs


def _bad(label, key):
    _err(label, "'{1}' heeft geen geldige waarde (zie docs/Lassen.md par. "
         "10.2).", "'{1}' has no valid value (see docs/en/Welding.md sec. "
         "10.2).", key)


def _make_spec(raw, label):
    import bridge_thermomech as btm
    spec = {"dataset": None, "trc": None, "meta": OrderedDict(), "hv": None,
            "begin": _BEGIN["ferriet"], "begin_name": "ferriet",
            "grain": 0.0, "mech": False, "T": None, "label": label,
            "user_mech": {}}
    name = raw.get("STAAL")
    if name is not None:
        key = name.strip("'\"").upper()
        if key not in DATASETS:
            _err(label, "geen standaard-dataset '{1}'. Beschikbaar: {2} "
                 "(of trc=<DEFI_TRC uit #ASTER-code>).",
                 "no standard dataset '{1}'. Available: {2} (or "
                 "trc=<DEFI_TRC from #ASTER code>).", name,
                 ", ".join(DATASETS))
            return None
        ds = DATASETS[key]
        spec["dataset"] = key
        spec["meta"].update(ds["meta"])
        spec["hv"] = ds["hv"]
        spec["grain"] = ds["grain"]
    if raw.get("TRC") is not None:
        trc = raw["TRC"].strip("'\"")
        if not re.match(r"^[A-Za-z_]\w*$", trc):
            _bad(label, "trc")
            return None
        if spec["dataset"]:
            _err(label, "geef staal=... of trc=..., niet allebei.",
                 "give staal=... or trc=..., not both.")
            return None
        spec["trc"] = trc
    if not spec["dataset"] and not spec["trc"]:
        _err(label, "geef een standaard-dataset staal=<{1}> of een eigen "
             "TRC-diagram trc=<DEFI_TRC uit #ASTER-code> met AR3, ALPHA, "
             "MS0, AC1, AC3, TAUX_1, TAUX_3.",
             "give a standard dataset staal=<{1}> or an own TRC diagram "
             "trc=<DEFI_TRC from #ASTER code> with AR3, ALPHA, MS0, AC1, "
             "AC3, TAUX_1, TAUX_3.", "|".join(DATASETS))
        return None
    try:
        for k in _META_KEYS + _META_OPT:
            if k in raw:
                vals = btm._numbers(raw[k])
                if len(vals) != 1:
                    raise ValueError(k)
                spec["meta"][k] = vals[0]
    except ValueError:
        _bad(label, k)
        return None
    missing = [k for k in _META_KEYS if k not in spec["meta"]]
    if missing:
        _err(label, "met trc=... ontbreken: {1} (META_ACIER, graden C).",
             "with trc=... missing: {1} (META_ACIER, degrees C).",
             ", ".join(missing))
        return None
    m = spec["meta"]
    if m["ALPHA"] >= 0.0:
        _err(label, "ALPHA = {1}: Code-Aster schrijft de martensietvorming "
             "als Z_M = 1 - exp(ALPHA (Ms - T)), dus ALPHA < 0 (de "
             "Koistinen-Marburger-constante met een minteken, bijv. "
             "-0.011).", "ALPHA = {1}: Code-Aster writes martensite "
             "formation as Z_M = 1 - exp(ALPHA (Ms - T)), so ALPHA < 0 (the "
             "Koistinen-Marburger constant with a minus sign, e.g. "
             "-0.011).", m["ALPHA"])
        return None
    if not m["AC1"] < m["AC3"]:
        _err(label, "AC1 ({1}) moet onder AC3 ({2}) liggen.",
             "AC1 ({1}) must be below AC3 ({2}).", m["AC1"], m["AC3"])
        return None
    if m["TAUX_1"] <= 0.0 or m["TAUX_3"] <= 0.0:
        _err(label, "TAUX_1 en TAUX_3 (tijdconstanten [s]) moeten > 0 "
             "zijn.", "TAUX_1 and TAUX_3 (time constants [s]) must be > 0.")
        return None
    if "HV" in raw:
        try:
            hv = btm._numbers(raw["HV"])
        except ValueError:
            hv = []
        if len(hv) != 5 or min(hv) <= 0.0:
            _err(label, "HV vraagt vijf hardheden > 0: (ferriet, perliet, "
                 "bainiet, martensiet, austeniet).",
                 "HV needs five hardnesses > 0: (ferrite, pearlite, "
                 "bainite, martensite, austenite).")
            return None
        spec["hv"] = tuple(hv)
    if "BEGIN" in raw:
        txt = raw["BEGIN"].strip("'\"").lower()
        if txt in _BEGIN:
            spec["begin"], spec["begin_name"] = _BEGIN[txt], txt
        else:
            try:
                z = btm._numbers(raw["BEGIN"])
            except ValueError:
                z = []
            if (len(z) != 5 or min(z) < 0.0 or
                    abs(sum(z) - 1.0) > 1.0e-6):
                _err(label, "begin = {1}: een fase ({2}) of vijf fracties "
                     "(ferriet, perliet, bainiet, martensiet, austeniet) "
                     "met som 1.", "begin = {1}: a phase ({2}) or five "
                     "fractions (ferrite, pearlite, bainite, martensite, "
                     "austenite) summing to 1.", raw["BEGIN"],
                     ", ".join(_BEGIN))
                return None
            spec["begin"], spec["begin_name"] = tuple(z), raw["BEGIN"]
    if "KORREL" in raw:
        try:
            g = btm._numbers(raw["KORREL"])
            if len(g) != 1 or g[0] < 0.0:
                raise ValueError("korrel")
            spec["grain"] = g[0]
        except ValueError:
            _bad(label, "korrel")
            return None
    if "MECH" in raw:
        low = raw["MECH"].strip("'\"").lower()
        if low in _YES:
            spec["mech"] = True
        elif low not in _NO:
            _bad(label, "mechanica")
            return None
    # Mechanical data (only with mechanica=ja; like #ASTER-MATERIAAL)
    try:
        for k in ("T", "TC"):
            if k in raw:
                vals = btm._numbers(raw[k])
                spec["T"] = [v + (KELVIN if k == "TC" else 0.0)
                             for v in vals]
        for k in _TABLE_KEYS:
            if k in raw:
                spec["user_mech"][k] = btm._numbers(raw[k])
        if "DEPS" in raw:
            v = btm._numbers(raw["DEPS"])
            if len(v) != 1:
                raise ValueError("DEPS")
            spec["user_mech"]["DEPS"] = v[0]
        if "REF" in raw:
            low = raw["REF"].strip("'\"").lower()
            ref = {"koud": "FROID", "cold": "FROID", "froid": "FROID",
                   "warm": "CHAUD", "hot": "CHAUD", "chaud": "CHAUD"}.get(low)
            if ref is None:
                raise ValueError("REF")
            spec["user_mech"]["REF"] = ref
    except ValueError as e:
        _bad(label, str(e) if str(e).isupper() else "mechanica")
        return None
    if spec["user_mech"] and not spec["mech"]:
        log(tr("WARNING: {0}: mechanische gegevens zonder mechanica=ja; "
               "genegeerd (de fasen veranderen de spanning dan niet).",
               "WARNING: {0}: mechanical data without mechanica=ja; "
               "ignored (the phases then do not change the stress).")
            .format(label))
    lists = [k for k, v in spec["user_mech"].items()
             if isinstance(v, list) and len(v) > 1]
    if lists and spec["T"] is None:
        _err(label, "lijsten voor {1} vragen de temperaturen T=(..) [K] of "
             "TC=(..) [graden C].", "lists for {1} need the temperatures "
             "T=(..) [K] or TC=(..) [degrees C].", ", ".join(lists))
        return None
    for k in lists:
        if len(spec["user_mech"][k]) != len(spec["T"]):
            _err(label, "{1} heeft {2} waarden, T heeft er {3}.",
                 "{1} has {2} values, T has {3}.", k,
                 len(spec["user_mech"][k]), len(spec["T"]))
            return None
    if spec["T"] is not None and any(b <= a for a, b in
                                     zip(spec["T"], spec["T"][1:])):
        _err(label, "de temperaturen moeten oplopen.",
             "the temperatures must increase.")
        return None
    return spec


# ==========================================
# THERMAL PART: META_ACIER + CALC_META
# ==========================================
def _r(x):
    import bridge_mesh
    return bridge_mesh._real(float(x))


def _seq(vals, per_line=8, indent=12):
    rows = [", ".join(_r(v) for v in vals[i:i + per_line])
            for i in range(0, len(vals), per_line)]
    return (",\n" + " " * indent).join(rows)


def _trc_block(name, ds):
    hist = ",\n".join(
        "        _F(VALE=(\n            {0},\n        ))".format(_seq(h))
        for h in ds["trc"])
    seuil, akm, bkm, tplm = ds["temp_ms"]
    grain = ""
    if ds.get("grain_aust"):
        grain = "    GRAIN_AUST=_F({0}),\n".format(", ".join(
            "{0}={1}".format(k, _r(v)) for k, v in ds["grain_aust"].items()))
    return ("# TRC diagram {0} ({1})\n"
            "trc_{0} = DEFI_TRC(\n    HIST_EXP=(\n{2},\n    ),\n"
            "    TEMP_MS=_F(SEUIL={3}, AKM={4}, BKM={5}, TPLM={6}),\n"
            "{7})\n").format(name, ds["source"], hist, _r(seuil), _r(akm),
                             _r(bkm), _r(tplm), grain)


def _material_kw(spec):
    """', META_ACIER=_F(...), DURT_META=_F(...)' for the thermal
    DEFI_MATERIAU."""
    trc = spec["trc"] or "trc_{0}".format(spec["dataset"])
    parts = ["TRC={0}".format(trc)] + [
        "{0}={1}".format(k, _r(spec["meta"][k]))
        for k in _META_KEYS + _META_OPT if k in spec["meta"]]
    out = ", META_ACIER=_F({0})".format(", ".join(parts))
    if spec["hv"]:
        out += (", DURT_META=_F(F1_DURT={0}, F2_DURT={1}, F3_DURT={2}, "
                "F4_DURT={3}, C_DURT={4})").format(
                    *[_r(v) for v in spec["hv"]])
    return out


def _fmt_groups(groups):
    return "({0},)".format(", ".join("'{0}'".format(g) for g in groups))


# Summary in the job (after CALC_META): lines 'BRIDGE_META <key>
# <value>' in the .mess (report_lines). An error here must not stop the
# job.
_REPORT = '''# Metallurgy summary (bridge_metallurgy): phases at the last time,
# largest austenite fraction during the run (heat-affected zone),
# hardness. Lines BRIDGE_META in the .mess.
def _bridge_meta_report(res, n_nodes, with_hv, ac3):
    import numpy as np
    out = []
    try:
        acc = res.getAccessParameters()
        idx = acc['NUME_ORDRE']
        out.append(('t', acc['INST'][-1]))

        def vals(name, i):
            sf = res.getField(name, i).toSimpleFieldOnNodes()
            v, m = sf.getValues()
            return list(sf.getComponents()), v[:n_nodes], m[:n_nodes]
        c, v, m = vals('META_NOEU', idx[-1])
        ok = m[:, c.index('V5')]
        out.append(('n', int(ok.sum())))
        for k, name in enumerate(('ferrite', 'pearlite', 'bainite',
                                  'martensite', 'austenite')):
            col = v[ok, c.index('V%d' % (k + 1))]
            out += [(name + '_min', float(col.min())),
                    (name + '_max', float(col.max()))]
        zmax = np.zeros(int(ok.sum()))
        tmax = np.full(int(ok.sum()), -1.0e30)
        for i in idx:
            c, v, m = vals('META_NOEU', i)
            zmax = np.maximum(zmax, v[ok, c.index('V5')])
            tmax = np.maximum(tmax, v[ok, c.index('V8')])
        out += [('austenite_peak', float(zmax.max())),
                ('n_haz', int((zmax > 0.01).sum())),
                ('n_full', int((zmax > 0.99).sum())),
                ('T_peak', float(tmax.max()) + 273.15),
                # well above Ac3 but not (nearly) fully
                # austenite: the austenitisation lags behind
                ('n_lag', int(((tmax > ac3 + 50.0) & (zmax < 0.9)).sum()))]
        if with_hv:
            c, v, m = vals('DURT_NOEU', idx[-1])
            col = v[ok, c.index('HV')]
            out += [('HV_min', float(col.min())), ('HV_max', float(col.max()))]
    except Exception as exc:
        print('BRIDGE_META_FOUT', repr(exc))
    for key, value in out:
        print('BRIDGE_META %s %r' % (key, value))
_bridge_meta_report(res, {n_nodes}, {with_hv}, {ac3})
'''


def apply(tb, model_data, analysis):
    """
    Metallurgy in the thermal builder tb (bridge_thermal._Thermal).
    Returns (block for the materials (DEFI_TRC), block after the thermal
    solve (CALC_META + summary)) or None (ERROR); ("", "") without
    #ASTER-METALLURGIE. Sets tb.meta_kw = {Mecway material: text for
    DEFI_MATERIAU} and model_data["metallurgy"] (for the chain and the
    export).
    """
    tb.meta_kw = {}
    bodies = model_data.get("aster_custom", {}).get("metallurgy", [])
    if not bodies:
        return "", ""
    specs = parse_specs(bodies)
    if specs is None:
        return None
    if not tb.transient:
        log(tr("ERROR: #ASTER-METALLURGIE vraagt een transiente thermische "
               "analyse (Mecway Thermal transient, T31): de fasen volgen uit "
               "het temperatuurverloop.",
               "ERROR: #ASTER-METALLURGY needs a transient thermal analysis "
               "(Mecway Thermal transient, T31): the phases follow from the "
               "temperature history."))
        return None
    mats = tb.th.get("materials", {})
    groups = OrderedDict()
    for name, spec in specs.items():
        if name not in mats:
            log(tr("ERROR: #ASTER-METALLURGIE '{0}': geen (thermisch) "
                   "materiaal met die naam in het model. Materialen: {1}.",
                   "ERROR: #ASTER-METALLURGY '{0}': no (thermal) material "
                   "with that name in the model. Materials: {1}.").format(
                       name, ", ".join(mats)))
            return None
        els = [e for e, i in tb.elsets.items() if i["mat"] == name]
        shells = [e for e in els if tb.elsets[e]["cls"] != "solid"]
        if shells:
            log(tr("ERROR: #ASTER-METALLURGIE '{0}': alleen volume-"
                   "elementen; de schaal-elsets {1} hebben dit materiaal "
                   "(CALC_META kent geen schalen). Geef de schalen een "
                   "ander materiaal.",
                   "ERROR: #ASTER-METALLURGY '{0}': solid elements only; "
                   "the shell elsets {1} have this material (CALC_META has "
                   "no shells). Give the shells another material.").format(
                       name, ", ".join(shells)))
            return None
        if not els:
            log(tr("WARNING: #ASTER-METALLURGIE '{0}': materiaal niet "
                   "gebruikt door een elset; genegeerd.",
                   "WARNING: #ASTER-METALLURGY '{0}': material not used by "
                   "an elset; ignored.").format(name))
            continue
        groups[name] = els
        tb.meta_kw[name] = _material_kw(spec)
        if spec["mech"] and not model_data.get("thermo_mech"):
            log(tr("WARNING: #ASTER-METALLURGIE '{0}': mechanica=ja zonder "
                   "Thermal stress: geen keten thermisch -> mechanisch, "
                   "alleen de fasen (docs/Lassen.md par. 10.4).",
                   "WARNING: #ASTER-METALLURGY '{0}': mechanica=ja without "
                   "Thermal stress: no thermal -> mechanical chain, only the "
                   "phases (docs/en/Welding.md sec. 10.4).").format(name))
    if not groups:
        return "", ""
    # CCT diagrams of the data sets used (once per data set)
    pre = []
    for ds_name in OrderedDict((specs[n]["dataset"], True) for n in groups
                               if specs[n]["dataset"]):
        pre.append(_trc_block(ds_name, DATASETS[ds_name]))
    users = [specs[n]["trc"] for n in groups if specs[n]["trc"]]
    sep = ""
    if users:
        # A user DEFI_TRC is in #ASTER code, which comes after the
        # materials in the .comm (bridge_thermal: loads_block). META_ACIER
        # then goes into its own material and CHAM_MATER for CALC_META
        # (alarm RESULT1_39 "materiau different" is then intended; seen in
        # a run, the phases are equal to those with META_ACIER in the
        # thermal material).
        log(tr("INFO: #ASTER-METALLURGIE: eigen TRC-diagram(men) {0} uit "
               "#ASTER-code; META_ACIER in een eigen CHAM_MATER (alarm "
               "RESULT1_39 is dan bedoeld).", "INFO: #ASTER-METALLURGY: own "
               "TRC diagram(s) {0} from #ASTER code; META_ACIER in its own "
               "CHAM_MATER (alarm RESULT1_39 is then intended).").format(
                   ", ".join(users)))
        affe_m = []
        for k, name in enumerate(groups):
            sep += "meta_mat{0} = DEFI_MATERIAU({1})\n".format(
                k + 1, tb.meta_kw[name].lstrip(", "))
            affe_m.append("_F(GROUP_MA={0}, MATER=meta_mat{1})".format(
                _fmt_groups(groups[name]), k + 1))
        sep += ("fieldmat_meta = AFFE_MATERIAU(\n    MAILLAGE=mesh,\n"
                "    MODELE=model,\n    AFFE=(\n        {0},\n    ),\n)\n"
                .format(",\n        ".join(affe_m)))
        tb.meta_kw = {}
    all_groups = [e for els in groups.values() for e in els]
    affe = []
    for name, els in groups.items():
        spec = specs[name]
        z = spec["begin"]
        affe.append("        _F(GROUP_MA={0}, NOM_CMP=('V1', 'V2', 'V3', "
                    "'V4', 'V5', 'V6', 'V7'),\n           VALE=({1}, {2}, "
                    "{3}, {4}, {5}, {6}, {7})),".format(
                        _fmt_groups(els), _r(z[0]), _r(z[1]), _r(z[2]),
                        _r(z[3]), _r(z[4]), _r(z[0] + z[1] + z[2] + z[3]),
                        _r(spec["grain"])))
        log("INFO: #ASTER-METALLURGIE '{0}': {1}, begin {2}, grain {3}, "
            "AR3/MS0/AC1/AC3 = {4}/{5}/{6}/{7} C, ALPHA {8}{9}{10}; elsets "
            "{11}.".format(
                name, "dataset {0} ({1})".format(
                    spec["dataset"], DATASETS[spec["dataset"]]["source"])
                if spec["dataset"] else "TRC '{0}'".format(spec["trc"]),
                spec["begin_name"], _r(spec["grain"]),
                *[_r(spec["meta"][k]) for k in ("AR3", "MS0", "AC1", "AC3",
                                                "ALPHA")] +
                [", hardness HV {0}".format("/".join(
                    "%g" % v for v in spec["hv"])) if spec["hv"] else "",
                 ", mechanics: META_P_IL" if spec["mech"] else "",
                 ", ".join(els)]))
    with_hv = all(specs[n]["hv"] for n in groups)
    if any(specs[n]["hv"] for n in groups) and not with_hv:
        log(tr("WARNING: #ASTER-METALLURGIE: niet alle materialen hebben "
               "HV; geen hardheid in Mecway.",
               "WARNING: #ASTER-METALLURGY: not all materials have HV; no "
               "hardness in Mecway."))
    cham = ("    MODELE=model,\n    CHAM_MATER=fieldmat_meta,\n" if sep
            else "")
    post = (
        "# --- Metallurgy (#ASTER-METALLURGIE, bridge_metallurgy.py) ---\n"
        "# Initial state: V1..V5 = ferrite, pearlite, bainite, martensite, "
        "austenite,\n# V6 = sum of the cold phases, V7 = grain size "
        "(hsnv101a, mtlp103a)\n"
        "{2}meta_init = CREA_CHAMP(\n    OPERATION='AFFE',\n"
        "    TYPE_CHAM='CART_VAR2_R',\n    MAILLAGE=mesh,\n    AFFE=(\n"
        "{0}\n    ),\n)\n"
        "res = CALC_META(\n    reuse=res,\n    RESULTAT=res,\n{3}"
        "    ETAT_INIT=_F(META_INIT_ELNO=meta_init),\n"
        "    COMPORTEMENT=_F(RELATION='ACIER', GROUP_MA={1}),\n"
        "    OPTION=('META_ELNO', 'META_NOEU'),\n)\n").format(
            "\n".join(affe), _fmt_groups(all_groups), sep, cham)
    if with_hv:
        post += ("res = CALC_META(\n    reuse=res,\n    RESULTAT=res,\n{1}"
                 "    GROUP_MA={0},\n    OPTION=('DURT_ELNO', 'DURT_NOEU'),"
                 "\n)\n").format(_fmt_groups(all_groups), cham)
    post += _REPORT.format(n_nodes=len(model_data.get("mesh_nodes", {})),
                           with_hv=with_hv, ac3=_r(max(
                               specs[n]["meta"]["AC3"] for n in groups)))
    post += "# --- end of metallurgy ---\n"
    model_data["metallurgy"] = {
        "specs": specs, "groups": groups, "with_hv": with_hv,
        "mech": OrderedDict((n, specs[n]) for n in groups
                            if specs[n]["mech"])}
    return "\n".join(pre), post


def fields(fields_in, model_data):
    """Fields for the export: with metallurgy also FIELD_GROUP."""
    out = list(fields_in or [])
    if model_data.get("metallurgy") and FIELD_GROUP not in out:
        out.append(FIELD_GROUP)
        log("INFO: Metallurgy: phases{0} to Mecway ({1}).".format(
            " and hardness" if model_data["metallurgy"]["with_hv"] else "",
            ", ".join(PHASES + (("hardness",) if model_data["metallurgy"]
                                ["with_hv"] else ()))))
    return out


# ==========================================
# MECHANICAL PART (chain thermal -> mechanical, mechanica=ja)
# ==========================================
def mech_specs(model_data):
    """{Mecway material: spec} with mechanica=ja (empty without)."""
    return (model_data.get("metallurgy") or {}).get("mech") or {}


def mech_fields(fields_in, model_data):
    """Fields of the chain without 'plastic_strain_eq' with the
    metallurgical law: with META_P_IL the internal variables V1..V5 are
    hardenings per phase and V7 a stress (seen in hsnv101a and MT-07), not
    a cumulative plastic strain; the plastic strain tensor (plastic_strain)
    stays."""
    out = list(fields_in or [])
    if mech_specs(model_data) and "plastic_strain_eq" in out:
        out.remove("plastic_strain_eq")
        log("INFO: Metallurgical law (META_P_IL): no "
            "equivalentplasticstrain (internal variables per phase); the "
            "plastic strain is in plasticstrain*.")
    return out


def _user_table(spec, key):
    """[(T_K or None, v)] from the user values, or None."""
    vals = spec["user_mech"].get(key)
    if vals is None:
        return None
    if len(vals) == 1:
        return [(None, vals[0])]
    return list(zip(spec["T"], vals))


def _et_from_h(h, e_tab):
    """D_SIGM_EPSI(T) = E H / (E + H) from a plastic modulus H(T)
    (like bridge_thermomech._slope_table; Mecway's tangent modulus is
    H)."""
    import bridge_thermomech as btm
    temps = sorted(set(t for t, _v in list(h) + list(e_tab)
                       if t is not None))

    def at(t):
        e_t, h_t = btm._value_at(e_tab, t), btm._value_at(h, t)
        return e_t * h_t / (e_t + h_t) if h_t > 0.0 else 0.0
    if not temps:
        return [(None, at(0.0))]
    return [(t, at(t)) for t in temps]


def mech_material(concept, mat, spec, tab, tref, t_alpha, t_cut, label):
    """
    DEFI_MATERIAU (ELAS_META_FO + META_ECRO_LINE) for a material with
    mechanica=ja, or None (ERROR). tab: the tables of
    bridge_thermomech._materials ("E", "NU", "ALPHA" (secant relative to
    t_alpha, already cut off above t_cut) and "SY"/"ET" if the Mecway
    material or #ASTER-MATERIAAL is plastic); temperatures in K.

    Thermal and metallurgical strain (ELAS_META_FO), with DEPS =
    EPSF_EPSC_TREF (strain of the cold phases minus that of austenite at
    T_ref = TEMP_DEF_ALPHA = t_alpha) and Z_a the austenite fraction;
    'FROID' recomputed by hand in MT-04/MT-05, 'CHAUD' via hsnv101a
    (MT-01); the U-doc NOT read. PHASE_REFE='CHAUD' (austenite is the
    reference):
        eps = Z_a alpha_a (T - T_ref) + (1 - Z_a) (alpha_f (T - T_ref) + DEPS)
    'FROID' (cold phases the reference):
        eps = (1 - Z_a) alpha_f (T - T_ref) + Z_a (alpha_a (T - T_ref) - DEPS)
    """
    import bridge_thermomech as btm
    ds = DATASETS.get(spec["dataset"] or "", {})
    dmech = ds.get("mech") or {}
    alpha_f = _user_table(spec, "ALPHA_F") or dmech.get("ALPHA_F")
    alpha_a = _user_table(spec, "ALPHA_A") or dmech.get("ALPHA_A")
    deps = spec["user_mech"].get("DEPS", dmech.get("DEPS"))
    missing = [k for k, v in (("ALPHA_A", alpha_a), ("DEPS", deps))
               if v is None]
    if missing:
        log(tr("ERROR: {0}: mechanica=ja vraagt {1} (uitzetting van "
               "austeniet [1/K] en het rekverschil koude fasen - austeniet "
               "bij de referentietemperatuur, EPSF_EPSC_TREF); de dataset "
               "heeft ze niet. Zie docs/Lassen.md par. 10.4.",
               "ERROR: {0}: mechanica=ja needs {1} (expansion of austenite "
               "[1/K] and the strain difference cold phases - austenite at "
               "the reference temperature, EPSF_EPSC_TREF); the dataset has "
               "none. See docs/en/Welding.md sec. 10.4.").format(
                   label, ", ".join(missing)))
        return None
    if t_cut is not None:
        alpha_a = btm._cut_alpha(alpha_a, t_alpha, t_cut)
        if alpha_f is not None:
            alpha_f = btm._cut_alpha(alpha_f, t_alpha, t_cut)
    if alpha_f is None:
        alpha_f = tab["ALPHA"]       # Mecway / #ASTER-MATERIAAL (cut off)
    ref = spec["user_mech"].get("REF") or dmech.get("REF") or (
        "CHAUD" if spec["begin"][4] > 0.5 else "FROID")
    # Yield stress and slope per phase: own value (SY_F, ...), otherwise SY
    # for all phases, otherwise the data set, otherwise the Mecway material
    # / #ASTER-MATERIAAL (tab["SY"], tab["ET"]).
    sy, et = OrderedDict(), OrderedDict()
    for p in _PH:
        sy[p] = (_user_table(spec, "SY_" + p) or _user_table(spec, "SY") or
                 dmech.get("SY_" + p) or tab.get("SY"))
        h = _user_table(spec, "H_" + p) or _user_table(spec, "H")
        e_t = _user_table(spec, "ET_" + p) or _user_table(spec, "ET")
        if h is not None and e_t is not None:
            log(tr("ERROR: {0}: geef H of ET (per fase), niet allebei.",
                   "ERROR: {0}: give H or ET (per phase), not both.").format(
                       label))
            return None
        for t_k, v in (e_t or []):
            e_mod = btm._value_at(tab["E"], t_k if t_k is not None else tref)
            if v < 0.0 or v >= e_mod:
                log(tr("ERROR: {0}: ET_{1} = {2} moet tussen 0 en E liggen.",
                       "ERROR: {0}: ET_{1} = {2} must be between 0 and E.")
                    .format(label, p, v))
                return None
        if h is not None:
            if min(v for _t, v in h) < 0.0:
                log(tr("ERROR: {0}: H_{1} moet >= 0 zijn.",
                       "ERROR: {0}: H_{1} must be >= 0.").format(label, p))
                return None
            e_t = _et_from_h(h, tab["E"])
        et[p] = (e_t or dmech.get("ET_" + p) or tab.get("ET") or
                 [(None, 0.0)])
    if any(v is None for v in sy.values()):
        log(tr("ERROR: {0}: mechanica=ja vraagt een vloeigrens: SY_F, SY_P, "
               "SY_B, SY_M, SY_A (per fase) of SY (alle fasen) in "
               "#ASTER-METALLURGIE, of een plastisch Mecway-materiaal / SY "
               "in #ASTER-MATERIAAL.",
               "ERROR: {0}: mechanica=ja needs a yield strength: SY_F, "
               "SY_P, SY_B, SY_M, SY_A (per phase) or SY (all phases) in "
               "#ASTER-METALLURGY, or a plastic Mecway material / SY in "
               "#ASTER-MATERIAL.").format(label))
        return None
    lines = []

    def func(suffix, table_):
        name = "{0}_{1}".format(concept, suffix)
        lines.append(btm._func(name, table_))
        return name
    kw = ["E={0}".format(func("E", tab["E"])),
          "NU={0}".format(func("NU", tab["NU"])),
          "F_ALPHA={0}".format(func("AF", alpha_f)),
          "C_ALPHA={0}".format(func("AC", alpha_a)),
          "PHASE_REFE='{0}'".format(ref),
          "EPSF_EPSC_TREF={0}".format(_r(deps)),
          "TEMP_DEF_ALPHA={0}".format(_r(t_alpha - KELVIN))]
    names = (("F1", "F"), ("F2", "P"), ("F3", "B"), ("F4", "M"), ("C", "A"))
    for ca, p in names:
        kw.append("{0}_SY={1}".format(ca, func("SY" + p, sy[p])))
    lines.append("{0}_MEL = DEFI_FONCTION(NOM_PARA='META', VALE=(0.0, 0.0, "
                 "1.0, 1.0), PROL_GAUCHE='CONSTANT', PROL_DROITE='CONSTANT')"
                 .format(concept))
    kw.append("SY_MELANGE={0}_MEL".format(concept))
    ecro = ["{0}_D_SIGM_EPSI={1}".format(ca, func("ET" + p, et[p]))
            for ca, p in names]
    lines.append(
        "# Metallurgical law (#ASTER-METALLURGIE mechanica=ja; "
        "ELAS_META_FO + META_ECRO_LINE,\n# hsnv101a): per phase yield strength "
        "and slope, linear mixing rule (SY_MELANGE)\n"
        "{0} = DEFI_MATERIAU(\n    ELAS_META_FO=_F(\n        {1},\n    ),\n"
        "    META_ECRO_LINE=_F(\n        {2},\n    ),\n)".format(
            concept, ",\n        ".join(kw), ",\n        ".join(ecro)))
    log("INFO: Thermomechanical: material '{0}': ELAS_META_FO + "
        "META_ECRO_LINE (META_P_IL), PHASE_REFE {1}, DEPS {2}, T_ref = {3} "
        "K{4}.".format(mat, ref, _r(deps), "%.6g" % t_alpha,
                       ", dataset {0}".format(spec["dataset"])
                       if dmech else ""))
    return "\n".join(lines)


def varc_entries(model_data, evol):
    """AFFE_VARC M_ACIER (phases from the thermal result) for the
    elsets with mechanica=ja."""
    mm = model_data.get("metallurgy") or {}
    groups = [e for n in mech_specs(model_data) for e in mm["groups"][n]]
    if not groups:
        return []
    return ["_F(GROUP_MA={0}, NOM_VARC='M_ACIER', EVOL={1}, "
            "NOM_CHAM='META_ELNO')".format(_fmt_groups(groups), evol)]


def patch_comportement(text, model_data):
    """RELATION='META_P_IL', RELATION_KIT=('ACIER',) for the elsets with
    mechanica=ja (hsnv101a)."""
    mm = model_data.get("metallurgy") or {}
    for n in mech_specs(model_data):
        for e in mm["groups"][n]:
            text = re.sub(r"(_F\(GROUP_MA='{0}', RELATION=)'\w+'".format(
                re.escape(e)), r"\1'META_P_IL', RELATION_KIT=('ACIER',)",
                text)
    return text


def check_chain(model_data, projected):
    """False (ERROR) if the chain cannot compute the metallurgical law."""
    if mech_specs(model_data) and projected:
        log(tr("ERROR: #ASTER-METALLURGIE mechanica=ja werkt niet met "
               "elem_hex8 = LINE_QUAD (de fasen staan op het lineaire mesh). "
               "Gebruik kwadratische elementen (hex20) in Mecway of "
               "elem_hex8 = 3D.",
               "ERROR: #ASTER-METALLURGY mechanica=ja does not work with "
               "elem_hex8 = LINE_QUAD (the phases are on the linear mesh). "
               "Use quadratic elements (hex20) in Mecway or elem_hex8 = "
               "3D."))
        return False
    return True


# ==========================================
# AFTER THE RUN
# ==========================================
_ROW = re.compile(r"^BRIDGE_META\s+(\w+)\s+([-+0-9.eEinfa]+)\s*$")


def read_summary(mess_path):
    """{key: value} from the BRIDGE_META lines of the .mess."""
    import io
    import os
    out = OrderedDict()
    if not mess_path or not os.path.exists(mess_path):
        return out
    f = io.open(mess_path, "r", encoding="utf-8", errors="replace")
    try:
        for line in f:
            m = _ROW.match(line.strip())
            if m:
                try:
                    out[m.group(1)] = float(m.group(2))
                except ValueError:
                    pass
            elif line.startswith("BRIDGE_META_FOUT"):
                out["_fout"] = line.strip()
    finally:
        f.close()
    return out


def report_lines(mess_path):
    """Lines for log and status box: phases at the last time, the
    heat-affected zone and the hardness."""
    s = read_summary(mess_path)
    if not s:
        return []
    if "_fout" in s:
        log("INFO: Metallurgical summary incomplete: {0}".format(
            s["_fout"]))
    if "t" not in s or "austenite_max" not in s:
        return []

    def rng(k):
        return "{0}..{1}".format("%.3g" % s.get(k + "_min", 0.0),
                                 "%.3g" % s.get(k + "_max", 0.0))
    line = tr(
        u"Metallurgie, t = {0} s: ferriet {1}, perliet {2}, bainiet {3}, "
        u"martensiet {4}, austeniet {5}; austeniet tijdens de run max {6} "
        u"(piektemperatuur {7} K; {8} van {9} knopen boven 1% austeniet = "
        u"warmte-beinvloede zone, {10} volledig){11}.",
        u"Metallurgy, t = {0} s: ferrite {1}, pearlite {2}, bainite {3}, "
        u"martensite {4}, austenite {5}; austenite during the run max {6} "
        u"(peak temperature {7} K; {8} of {9} nodes above 1% austenite = "
        u"heat-affected zone, {10} fully){11}.").format(
            "%.6g" % s["t"], rng("ferrite"), rng("pearlite"), rng("bainite"),
            rng("martensite"), rng("austenite"),
            "%.3g" % s.get("austenite_peak", 0.0),
            "%.5g" % s.get("T_peak", 0.0), int(s.get("n_haz", 0)),
            int(s.get("n", 0)), int(s.get("n_full", 0)),
            tr(u"; hardheid {0} HV", u"; hardness {0} HV").format(
                rng("HV")) if "HV_max" in s else u"")
    log(u"INFO: " + line)
    if s.get("n_lag", 0.0) > 0:
        # Measured (Code-Aster 17.4, docs/Lassen.md par. 10.5): with fast
        # heating and a large temperature step per time step the
        # austenitization does not follow the time constant TAUX (40 C per
        # step: ~8 x slower; 4 C per step: exact).
        msg = tr(u"WARNING: Metallurgie: {0} knopen kwamen ruim boven Ac3 "
                 u"maar werden niet volledig austeniet (< 90%): de "
                 u"austenitisering loopt achter. Bij lassen (snel opwarmen) "
                 u"een kleine TAUX_1/TAUX_3 (bijv. 0.001 s) of een kleinere "
                 u"tijdstap; zie docs/Lassen.md par. 10.5.",
                 u"WARNING: Metallurgy: {0} nodes got well above Ac3 but did "
                 u"not become fully austenite (< 90%): the austenitisation "
                 u"lags behind. For welding (fast heating) a small TAUX_1/"
                 u"TAUX_3 (e.g. 0.001 s) or a smaller time step; see "
                 u"docs/en/Welding.md sec. 10.5.").format(int(s["n_lag"]))
        log(msg)
        line += u" " + msg[len(u"WARNING: "):]
    if s.get("austenite_max", 0.0) > 0.01:
        log(tr(u"WARNING: Metallurgie: op het laatste tijdstip is er nog "
               u"austeniet (tot {0}): het werkstuk is nog niet afgekoeld "
               u"tot onder Ms, of de afkoeling is te kort gerekend. Reken "
               u"langer door voor de eindtoestand.",
               u"WARNING: Metallurgy: at the last time there is still "
               u"austenite (up to {0}): the part has not yet cooled below "
               u"Ms, or the cooling was computed too short. Compute longer "
               u"for the final state.").format(
                   "%.3g" % s["austenite_max"]))
    return [line]
