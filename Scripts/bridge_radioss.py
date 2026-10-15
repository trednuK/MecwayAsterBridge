# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_radioss.py
# Responsibility: read the OpenRadioss input from the .liml that Mecway
# stores for the OpenRadioss solver, as far as the bridge can translate it
# to Code-Aster:
#   - <radiossmodeldefinition>: /FUNCT/<id> (tables) and /BEGIN (only the
#     units, for a message); other cards are only listed
#     (message "not translated");
#   - <mat><openradioss type="Custom" law="PLAS_TAB">: /MAT/LAW36
#     (elastic-plastic with a table yield stress - plastic strain)
#     -> E, NU, RHO and a hardening curve; a /FAIL/JOHNSON with a fixed
#     failure strain in the same field -> eps_p_max (bridge_failure.py);
#   - law="VOID": material without stiffness (in Radioss used e.g. for rigid
#     bodies with /RBODY); cannot be translated.
#
# Card format (OpenRadioss/Altair Radioss Reference Guide, /MAT/LAW36,
# /FUNCT, /FAIL/JOHNSON, /BEGIN): fixed columns of 10 or 20 characters;
# lines starting with '#' are comments, a line starting with '/'
# starts a new card. The values are in the unit system of the
# Radioss model. Mecway computes in SI (the templates: RHO 7800, E 206E9,
# yield stress 228.03E6) and writes a /BEGIN itself on export ('kg' is
# next to the /BEGIN text in mecway.exe); the bridge converts nothing and
# reports values that point to another system (_check_units).
#
# Compatible with IronPython 2.7.9.

from bridge_utils import log, tr

# Radioss default for "not active" for failure strains (Eps_p_max, Eps_t,
# Eps_m, Eps_f: 1e20 to 3e20 according to the Reference Guide /MAT/LAW36); a
# value from this limit upwards counts as not filled in.
_RADIOSS_INFINITE = 1.0e19

# SI input units in /BEGIN (mass, length, time)
_SI_UNITS = ("kg", "m", "s")


def _data_lines(text):
    """Lines without comments (#), up to the first card line (/...)."""
    out = []
    for line in (text or "").splitlines():
        if line.startswith("#"):
            continue
        if line.startswith("/"):
            break
        out.append(line.rstrip("\r"))
    return out


def _field(line, start, width):
    """Field from a fixed column as float, or None if it is empty."""
    txt = line[start:start + width].strip() if line else ""
    if not txt:
        return None
    try:
        return float(txt.replace("d", "e").replace("D", "E"))
    except ValueError:
        return None


def _active(value):
    """True for a filled-in failure strain (> 0 and below the Radioss
    default 'infinite'); 0 or empty means the default value in Radioss."""
    return value is not None and 0.0 < value < _RADIOSS_INFINITE


def parse_cards(text):
    """
    [(card name, [data lines])] from a Radioss text, e.g.
    ("/FUNCT/99", ["TRUE_Stress_strain", "  0.0  228.03E6", ...]).
    Comment lines are dropped.
    """
    cards = []
    for line in (text or "").splitlines():
        line = line.rstrip("\r")
        if line.startswith("#"):
            continue
        if line.startswith("/"):
            cards.append((line.split()[0], []))
        elif cards:
            cards[-1][1].append(line)
    return cards


def _point(line):
    """
    (x, y) of a /FUNCT line, or None. First the fixed columns of the
    Reference Guide (X in columns 1-20, Y in 21-40): two full fields are
    then adjacent without a space ('-1.0000000000E+00-2.0E+00'), which
    split() cannot separate. If that fails (free format, e.g.
    '  0.0  228.03E6', which runs across the column-20 boundary), split().
    Free format that is readable in the fixed columns gives the same
    values: each field must then contain exactly one number.
    """
    x, y = _field(line, 0, 20), _field(line, 20, 20)
    if x is not None and y is not None:
        return (x, y)
    vals = line.split()
    if len(vals) < 2:
        return None
    try:
        return (float(vals[0].replace("d", "e").replace("D", "E")),
                float(vals[1].replace("d", "e").replace("D", "E")))
    except ValueError:
        return None


def parse_functions(text):
    """{id: [(x, y), ...]} of all /FUNCT/<id> cards."""
    funcs = {}
    for name, lines in parse_cards(text):
        parts = name.split("/")
        if len(parts) < 3 or parts[1] != "FUNCT":
            continue
        try:
            fid = int(parts[2])
        except ValueError:
            continue
        points = []
        for line in lines[1:]:          # first line = title
            point = _point(line)
            if point is None:
                if line.strip():
                    log(tr("WARNING: /FUNCT/{0}: regel '{1}' is geen punt "
                           "(X, Y) en wordt overgeslagen.",
                           "WARNING: /FUNCT/{0}: line '{1}' is not a point "
                           "(X, Y) and is skipped.").format(
                               fid, line.strip()))
                continue
            points.append(point)
        funcs[fid] = points
    return funcs


def other_cards(text):
    """Names of cards that the bridge does not translate (everything except
    /FUNCT)."""
    return [name for name, _ in parse_cards(text)
            if not name.startswith("/FUNCT/")]


def begin_units(text):
    """
    Input units (mass, length, time) from a /BEGIN card, or None.
    /BEGIN (Reference Guide): title, Invers/Irun, input units (3 fields
    of 20 characters), work units.
    """
    for name, lines in parse_cards(text):
        if name != "/BEGIN" or len(lines) < 3:
            continue
        units = tuple(lines[2][20 * k:20 * k + 20].strip()
                      for k in range(3))
        if all(units):
            return units
    return None


def _check_units(mat_name, e_mod, rho, units, notes):
    """
    Report a probably non-SI unit system (the values are used
    unchanged). Limits: E of solids lies in SI between
    ~1e6 Pa (rubber) and ~1e12 Pa (diamond), densities between ~1 and
    ~25000 kg/m3; N-mm-t gives E ~2e5 and RHO ~8e-9.
    """
    reasons = []
    if units is not None and tuple(u.lower() for u in units) != _SI_UNITS:
        reasons.append("/BEGIN {0} {1} {2}".format(*units))
    if e_mod < 1.0e6 or e_mod > 1.0e13:
        reasons.append("E=%.4g" % e_mod)
    if rho and (rho < 1.0 or rho > 1.0e5):
        reasons.append("RHO=%.4g" % rho)
    if not reasons:
        return
    log(tr("WARNING: PLAS_TAB van materiaal '{0}': de waarden lijken niet "
           "in SI (kg, m, s) te staan ({1}). De bridge rekent niet om; "
           "Mecway rekent in SI. Zet E, RHO en de /FUNCT-spanningen in Pa "
           "en kg/m3.",
           "WARNING: PLAS_TAB of material '{0}': the values do not seem to "
           "be in SI (kg, m, s) ({1}). The bridge does not convert; Mecway "
           "works in SI. Give E, RHO and the /FUNCT stresses in Pa and "
           "kg/m3.").format(mat_name, ", ".join(reasons)))
    notes.append(tr("PLAS_TAB van '{0}': waarschijnlijk geen SI-eenheden "
                    "({1}), niet omgerekend",
                    "PLAS_TAB of '{0}': probably no SI units ({1}), not "
                    "converted").format(mat_name, ", ".join(reasons)))


def _ignored_fields(mat_name, lines, n_funct, notes):
    """
    Report fields of /MAT/LAW36 that the bridge does not translate
    (Reference Guide /MAT/LAW36; defaults in brackets):
      Eps_t, Eps_m (1e20, 2e20): stress decreases from principal strain
          Eps_t and is zero at Eps_m;
      Eps_f (3e20): element deleted at tensile strain Eps_f;
      C_hard (0 = isotropic, 1 = kinematic Prager-Ziegler, in between
          mixed);
      fct_IDp (0): yield stress depending on pressure;
      Fct_IDE (0), EInf, CE: E decreases with plastic strain;
      F_smooth, F_cut, VP: strain rate only.
    What changes the calculation also goes into notes (skipped_loads).
    """
    eps_t = _field(lines[1], 60, 20)
    eps_m = _field(lines[1], 80, 20)
    f_smooth = _field(lines[2], 10, 10)
    c_hard = _field(lines[2], 20, 20)
    f_cut = _field(lines[2], 40, 20)
    eps_f = _field(lines[2], 60, 20)
    vp = _field(lines[2], 80, 20)
    fct_idp = _field(lines[3], 0, 10)
    fct_ide = _field(lines[3], 30, 10)
    e_inf = _field(lines[3], 40, 20)
    ce = _field(lines[3], 60, 20)

    changed = []          # (field, Dutch explanation, English explanation)
    if _active(eps_t) or _active(eps_m):
        changed.append(("Eps_t/Eps_m",
                        "afname van de spanning bij een grote hoofdrek",
                        "stress reduction at a large principal strain"))
    if _active(eps_f):
        changed.append(("Eps_f", "element weg bij trekrek Eps_f",
                        "element deletion at tensile strain Eps_f"))
    if c_hard:
        changed.append(("C_hard=%g" % c_hard,
                        "kinematische/gemengde versteviging; isotroop "
                        "gerekend (gelijk bij monotone belasting, anders bij "
                        "ontlasten of wisselbelasting)",
                        "kinematic/mixed hardening; computed as isotropic "
                        "(equal under monotonic loading, different on "
                        "unloading or load reversal)"))
    if fct_idp:
        changed.append(("fct_IDp", "drukafhankelijke vloeigrens",
                        "pressure-dependent yield stress"))
    if fct_ide or (ce and e_inf):
        changed.append(("Fct_IDE/EInf/CE",
                        "E afhankelijk van de plastische rek",
                        "E depending on the plastic strain"))
    for field, nl, en in changed:
        log(tr("WARNING: PLAS_TAB van materiaal '{0}': {1} ({2}) wordt niet "
               "vertaald.",
               "WARNING: PLAS_TAB of material '{0}': {1} ({2}) is not "
               "translated.").format(mat_name, field, tr(nl, en)))
        notes.append(tr("PLAS_TAB van '{0}': {1} ({2}) niet vertaald",
                        "PLAS_TAB of '{0}': {1} ({2}) not translated").format(
                            mat_name, field, tr(nl, en)))
    rate = [n for n, v in (("F_smooth", f_smooth), ("F_cut", f_cut),
                           ("VP", vp)) if v]
    if rate:
        log("INFO: PLAS_TAB '{0}': {1} (strain rate) not used; "
            "Code-Aster computes with one curve ({2} function(s)).".format(
                mat_name, ", ".join(rate), n_funct))


def _johnson_strain(mat_name, lines):
    """
    Fixed failure strain from /FAIL/JOHNSON, or None. Reference Guide
    /FAIL/JOHNSON: line 1 D1..D5 (20 characters each);
    eps_f = [D1 + D2 exp(D3 s*)] [1 + D4 ln(eps_dot*)] [1 + D5 T*] and
    damage D = sum(d eps_p / eps_f), failure at D >= 1. With D4 = D5 = 0
    and D2 = 0 or D3 = 0, eps_f is constant (D1 + D2) and D >= 1 is the
    same as eps_p >= eps_f: exactly the criterion of bridge_failure.py
    (equivalent plastic strain). Otherwise eps_f depends on the
    triaxiality, strain rate or temperature: not translated.
    """
    if not lines:
        return None
    d = [_field(lines[0], 20 * k, 20) or 0.0 for k in range(5)]
    if d[3] != 0.0 or d[4] != 0.0 or (d[1] != 0.0 and d[2] != 0.0):
        return None
    eps_f = d[0] + (d[1] if d[2] == 0.0 else 0.0)
    if eps_f <= 0.0:
        return None
    log("INFO: PLAS_TAB '{0}': /FAIL/JOHNSON with fixed failure strain {1} "
        "(D1={2}, D2={3}, D3=D4=D5=0) -> failure limit plastic strain."
        .format(mat_name, eps_f, d[0], d[1]))
    return eps_f


def _failure_cards(mat_name, fieldcontents, notes):
    """
    Cards after the LAW36 data in the same <fieldcontents> (the Mecway
    template has a commented-out /FAIL/BIQUAD there).
    Returns the failure strain of a translatable /FAIL/JOHNSON or None; the
    rest is reported (ERROR + notes).
    """
    eps = None
    for name, lines in parse_cards(fieldcontents):
        value = None
        if name.startswith("/FAIL/JOHNSON"):
            value = _johnson_strain(mat_name, lines)
        if value is not None:
            eps = value if eps is None else min(eps, value)
            continue
        if name.startswith("/FAIL/JOHNSON"):
            why = tr("breukrek hangt af van triaxialiteit, reksnelheid of "
                     "temperatuur (D2*D3, D4 of D5 niet 0)",
                     "failure strain depends on triaxiality, strain rate "
                     "or temperature (D2*D3, D4 or D5 not 0)")
        elif name.startswith("/FAIL/"):
            why = tr("alleen /FAIL/JOHNSON met een vaste breukrek wordt "
                     "vertaald", "only /FAIL/JOHNSON with a constant "
                     "failure strain is translated")
        else:
            why = tr("kaart in het materiaalveld", "card in the material "
                     "field")
        log(tr("ERROR: PLAS_TAB van materiaal '{0}': {1} wordt niet "
               "vertaald ({2}).",
               "ERROR: PLAS_TAB of material '{0}': {1} is not translated "
               "({2}).").format(mat_name, name, why))
        notes.append(tr("PLAS_TAB van '{0}': {1} niet vertaald ({2})",
                        "PLAS_TAB of '{0}': {1} not translated ({2})"
                        ).format(mat_name, name, why))
    return eps


def parse_plas_tab(fieldcontents, functions, mat_name, units=None):
    """
    /MAT/LAW36 (PLAS_TAB) from <fieldcontents>.

    Columns (OpenRadioss Reference Guide, /MAT/LAW36):
      1: RHO_I(20)
      2: E(20) Nu(20) Eps_p_max(20) Eps_t(20) Eps_m(20)
      3: N_funct(10) F_smooth(10) C_hard(20) F_cut(20) Eps_f(20) VP(20)
      4: fct_IDp(10) Fscale(20) Fct_IDE(10) EInf(20) CE(20)
      5: func_ID1..5 (10 each)
      6: Fscale_1..5 (20 each)
      7: Eps_dot_1..5 (20 each)
    The functions give the yield stress as a function of the plastic
    strain, per strain rate Eps_dot_i. Code-Aster (VMIS_ISOT_TRAC) is
    strain-rate independent: the function with the lowest strain rate is
    used. Fields not translated: _ignored_fields; /FAIL cards in
    the same field: _failure_cards. units: input units from /BEGIN
    (begin_units) or None.

    Returns
    -------
    (props, notes)
        props : {"E", "NU", "rho", "plastic_curve", "curve_definition"} or
                None on an error
        notes : [str] - what is not translated (for skipped_loads)
    """
    notes = []
    lines = _data_lines(fieldcontents)
    if len(lines) < 7:
        log(tr("ERROR: PLAS_TAB van materiaal '{0}': {1} dataregels, "
               "verwacht minstens 7.",
               "ERROR: PLAS_TAB of material '{0}': {1} data lines, "
               "expected at least 7.").format(mat_name, len(lines)))
        return None, [tr("PLAS_TAB van '{0}' onleesbaar",
                         "PLAS_TAB of '{0}' unreadable").format(mat_name)]
    rho = _field(lines[0], 0, 20)
    e_mod = _field(lines[1], 0, 20)
    nu = _field(lines[1], 20, 20)
    eps_p_max = _field(lines[1], 40, 20)
    n_funct = int(_field(lines[2], 0, 10) or 0)
    if e_mod is None or nu is None or n_funct < 1:
        log(tr("ERROR: PLAS_TAB van materiaal '{0}': E, Nu of N_funct "
               "ontbreekt.",
               "ERROR: PLAS_TAB of material '{0}': E, Nu or N_funct "
               "is missing.").format(mat_name))
        return None, [tr("PLAS_TAB van '{0}' onvolledig",
                         "PLAS_TAB of '{0}' incomplete").format(mat_name)]
    _check_units(mat_name, e_mod, rho, units, notes)
    _ignored_fields(mat_name, lines, n_funct, notes)
    if n_funct > 5:
        notes.append(tr("PLAS_TAB van '{0}': alleen de eerste 5 van {1} "
                        "functies gelezen",
                        "PLAS_TAB of '{0}': only the first 5 of {1} "
                        "functions read").format(mat_name, n_funct))
        n_funct = 5
    ids = [_field(lines[4], 10 * k, 10) for k in range(n_funct)]
    scales = [_field(lines[5], 20 * k, 20) for k in range(n_funct)]
    rates = [_field(lines[6], 20 * k, 20) for k in range(n_funct)]
    choice = sorted(range(n_funct), key=lambda k: rates[k] or 0.0)[0]
    fid = int(ids[choice] or 0)
    scale = scales[choice] if scales[choice] else 1.0
    if fid not in functions:
        log(tr("ERROR: PLAS_TAB van materiaal '{0}': /FUNCT/{1} niet "
               "gevonden in <radiossmodeldefinition>.",
               "ERROR: PLAS_TAB of material '{0}': /FUNCT/{1} not found "
               "in <radiossmodeldefinition>.").format(mat_name, fid))
        return None, [tr("PLAS_TAB van '{0}': /FUNCT/{1} ontbreekt",
                         "PLAS_TAB of '{0}': /FUNCT/{1} is missing").format(
            mat_name, fid)]
    if n_funct > 1:
        notes.append(tr("reksnelheidsafhankelijkheid van '{0}' (alleen de "
                        "curve bij Eps_dot={1} gebruikt)",
                        "strain-rate dependence of '{0}' (only the curve "
                        "at Eps_dot={1} used)").format(
                         mat_name, rates[choice] or 0.0))
    eps_fail = _failure_cards(mat_name, fieldcontents, notes)
    if eps_fail is not None and (not eps_p_max or eps_fail < eps_p_max):
        eps_p_max = eps_fail
    curve = [(x, y * scale) for x, y in functions[fid]]
    props = {
        "E": e_mod,
        "NU": nu,
        "Texp": 0.0,
        "rho": rho or 0.0,
        "plastic_type": "Isotropic",
        "plastic_curve": sorted(curve),
        # Radioss LAW36: x = plastic strain (Reference Guide)
        "curve_definition": "plastic",
        # Failure limit (plastic strain); bridge_failure.py turns it into
        # failure of elements. 0 = no failure.
        "eps_p_max": eps_p_max or 0.0,
    }
    log("INFO: PLAS_TAB '{0}': E={1} Pa, NU={2}, rho={3}, /FUNCT/{4} with "
        "{5} points (scale {6}).".format(mat_name, e_mod, nu, rho, fid,
                                          len(curve), scale))
    return props, notes
