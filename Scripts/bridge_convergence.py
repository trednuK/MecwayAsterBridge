# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# bridge_convergence.py
# Responsibility: read the convergence information of STAT_NON_LINE /
# DYNA_NON_LINE from the Code-Aster output (fort.6 during the run,
# study.mess afterwards). Used by the convergence window
# (aster_convergence_monitor.py); itself without GUI and without writing
# files.
#
# Pure Python, standard library only; runs in Python 2.7
# (IronPython 2.7.9, Mecway) and Python 3 (the CPython 3.11 of Code-Aster).
#
# What Code-Aster 17.4 writes per solver step (seen in study.mess of the
# test models, e.g. static and implicit dynamic with contact):
#
#   Instant de calcul:  1.250000000000e-03 - Niveau de découpe: 2
#   |     CONTACT    |     NEWTON     |     RESIDU     | ...   (header, 3 lines)
#   |     1        X |     0        X | 3.37162E-10    | ...   (one line per
#                                                               Newton iteration)
#   Critère(s) de convergence atteint(s)        or  <Erreur> ... / <Action> ...
#   Le résidu de type <RESI_GLOB_RELA> vaut ... au noeud et degré de liberté <298 DY>
#   Temps CPU consommé dans ce pas de temps    : 2.000 s
#   * Nombre d'itérations de Newton            : 32
#   * Nombre de liaisons de contact            : 8
#   [  0%] Instant calculé : 1.25000e-03, ...
#
# The columns differ per model (without contact: 4 columns; discrete
# contact, friction, RESI_REFE_RELA ...). The header is therefore read per
# table and mapped to fixed keys via _COLUMN_KEYS; unknown columns
# go under their header name in it["extra"]. An "X" after a value means
# that this criterion is not met yet, "E" that the iteration ends in error
# (NOT verified in the U-doc; derived from the output: "E" is on the
# last iteration before "<Erreur> Le nombre maximum d'itérations ...").

import io
import os
import re

try:
    from bridge_utils import tr
except ImportError:      # pragma: no cover - bridge_utils next to this file
    def tr(nl, en):
        return nl


# ==========================================
# LINE RECOGNITION
# ==========================================
_INSTANT_RE = re.compile(
    r"Instant de calcul:\s*([-+0-9.eEdD]+)\s*-\s*Niveau de d.coupe:\s*(\d+)")
_PROGRESS_RE = re.compile(
    r"^\[\s*(\d+)%\]\s*Instant calcul.\s*:\s*([-+0-9.eE]+)")
_CPU_RE = re.compile(r"Temps CPU consomm. dans ce pas de temps\s*:\s*([0-9.]+)")
_SUMMARY_RE = re.compile(r"^\*\s*(.+?)\s*:\s*([-+0-9.eE]+)")
_CONTACT_INIT_RE = re.compile(
    r"Il y a (\d+) points initialement en contact et (\d+) points exclus")
_RESI_LOC_RE = re.compile(
    r"Le r.sidu de type <(\w+)> vaut\s*([-+0-9.eE]+) au noeud et "
    r"degr. de libert. <\s*(\S+)\s+(\S+?)\s*>")
_PIVOT_RE = re.compile(
    r"associ\S* au noeud (\S+) et \S+ la composante (\S+?)\.?\s*$")
_BOX_CODE_RE = re.compile(
    r"<(EXCEPTION|F|S|E|A|[A-Za-z]+Error)>\s*<([A-Za-z0-9_]+)>")
_COMMAND_RE = re.compile(r"\b(STAT_NON_LINE|DYNA_NON_LINE|THER_NON_LINE)\s*\(")
_RESI_CRIT_RE = re.compile(r"\bRESI_GLOB_RELA\s*=\s*([-+0-9.eE]+)")
_ITER_MAX_RE = re.compile(r"\bITER_GLOB_MAXI\s*=\s*(\d+)")
_PARTIAL_RE = re.compile(r"BRIDGE_ONVOLLEDIG\s+(\S+)")
# Element failure (bridge_failure.py, print in the .comm)
_FAILURE_RE = re.compile(r"BRIDGE_BEZWIJKEN t=([-+0-9.eE]+) elset=(\S+) "
                         r"nieuw=(\d+) totaal=(\d+)")
# End time of the failure loop (bridge_failure.py): it solves with one
# solve call per time step, and '[ n%]' then applies per call.
_TEND_RE = re.compile(r"^BRIDGE_TEND\s+([-+0-9.eE]+)\s*$")
# Explicit scheme in the command echo (no Newton iterations).
_EXPLICIT_RE = re.compile(r"SCHEMA\s*=\s*'(DIFF_CENT|TCHAMWA)'")
_DIAG_MARK = "--- DIAGNOSTIC JOB :"
# Line that the bridge appends to the .mess when the run did not end by
# itself (bridge_run_aster.AsterJob: Stop button or Code-Aster window
# closed); the .mess is then the copy of the live fort.6. Reason: "user" or
# "window".
STOPPED_MARK = u"BRIDGE_GESTOPT"
_STOPPED_RE = re.compile(r"^BRIDGE_GESTOPT\s*(\w*)")
_BOX_TOP = u"╔"     # top edge of message box
_BOX_BOTTOM = u"╚"  # bottom edge of message box
_BOX_SIDE = u"║"    # side of message box
_CONVERGED = u"Critère(s) de convergence atteint(s)"
_NUM_CELL_RE = re.compile(r"^\s*([-+]?\d[\d.]*(?:[EeDd][-+]?\d+)?)\s*([A-Z]?)\s*$")

# Column header (merged over the three header lines) -> key. Order matters:
# the first matching rule wins.
_COLUMN_KEYS = [
    ("BCL. GEOM.", "geom"),
    ("BCL. CONT.", "cont_loop"),
    ("BCL. FROT.", "frot_loop"),
    ("NEWTON ITERATION", "newton"),
    ("RESI_GLOB_RELA", "resi_rela"),
    ("RESI_GLOB_MAXI", "resi_maxi"),
    ("RESI_REFE_RELA", "resi_refe"),
    ("RESI_GEOM", "resi_geom"),
    ("OPTION", "option"),
    ("VARI. CONT.", "cont_vari"),
    ("CRIT. GEOM.", "cont_crit_geom"),
    ("PRESSURE", "cont_press"),
    ("CRITERE VALEUR", "cont_crit"),
    ("PENETRATION", "cont_pen"),
    ("DISCRET", "cont_discrete_iter"),
]

# Summary after each step ("* Nombre de ... : n") -> key.
_SUMMARY_KEYS = [
    (u"Nombre d'it", "newton_count"),
    (u"Nombre de liaisons de contact", "contact_links"),
    (u"contact/pas contact", "cycles_contact"),
    (u"glissement/adh", "cycles_slip_stick"),
    (u"glissement avant/arri", "cycles_slip_dir"),
    (u"point fixe contact", "cycles_fixed_point"),
]

# Events in the convergence table (French in study.mess) with explanation
# (nl, en). Texts seen in the study.mess files of the test models.
EVENT_TEXTS = [
    (u"nombre maximum d'it", u"Maximaal aantal Newton-iteraties "
     u"(ITER_GLOB_MAXI) bereikt zonder convergentie.",
     u"Maximum number of Newton iterations (ITER_GLOB_MAXI) reached "
     u"without convergence."),
    (u"matrice du syst", u"De stijfheidsmatrix is singulier (pivot nul); "
     u"zie de pivot-melding (knoop en component).",
     u"The stiffness matrix is singular (zero pivot); see the pivot "
     u"message (node and component)."),
    (u"essaie de découper", u"Code-Aster probeert de tijdstap op te "
     u"delen.", u"Code-Aster tries to subdivide the time step."),
    (u"On découpe le pas", u"Tijdstap opgedeeld.",
     u"Time step subdivided."),
    (u"chec dans la tentative de découper", u"Opdelen lukt niet meer "
     u"(maximaal aantal opdelingsniveaus bereikt).",
     u"Subdividing no longer possible (maximum number of subdivision "
     u"levels reached)."),
    (u"On arrête le calcul", u"Code-Aster stopt de berekening.",
     u"Code-Aster stops the calculation."),
]

# Explanation for a zero pivot, per kind of degree of freedom. The advice
# follows the text Code-Aster itself gives with the pivot message (study.mess:
# "Si vous faites du contact, il ne faut pas que la structure ne 'tienne'
# que par le contact" and "exclure certains noeuds des conditions de contact
# (mots clés SANS_NOEUD et SANS_GROUP_NO)").
_PIVOT_HINT_CONTACT = (u"Contact-Lagrange (LAGS_C/LAGS_F): de contactvoorwaarde "
                       u"is overbepaald (knoop zit ook in een oplegging of in "
                       u"twee contactparen) of het deel hangt alleen aan "
                       u"contact. Sluit zulke knopen uit (SANS_GROUP_NO) of "
                       u"geef het deel een oplegging.",
                       u"Contact Lagrange (LAGS_C/LAGS_F): the contact "
                       u"condition is overdetermined (the node is also in a "
                       u"support or in two contact pairs) or the part hangs "
                       u"on contact only. Exclude such nodes (SANS_GROUP_NO) "
                       u"or give the part a support.")
_PIVOT_HINT_PHYS = (u"Fysieke vrijheidsgraad: waarschijnlijk een niet "
                    u"vastgehouden starre-lichaamsbeweging (te weinig "
                    u"opleggingen, of een deel dat alleen via contact op "
                    u"zijn plaats blijft).",
                    u"Physical degree of freedom: probably an unrestrained "
                    u"rigid-body motion (too few supports, or a part held "
                    u"in place only by contact).")
_PIVOT_HINT_LAGR = (u"Lagrange-vrijheidsgraad: waarschijnlijk een dubbele of "
                    u"tegenstrijdige randvoorwaarde.",
                    u"Lagrange degree of freedom: probably a duplicated or "
                    u"conflicting constraint.")


def _to_float(text):
    try:
        return float(text.replace("D", "E").replace("d", "e"))
    except (ValueError, AttributeError):
        return None


# ==========================================
# LINEAR SOLVER (MECA_STATIQUE with INFO=2)
#
# What Code-Aster 17.4 writes within "res = MECA_STATIQUE(...)" up to
# "# Fin commande" (seen in the .mess of a small 3D test model and a
# block of 37 389 equations; MUMPS 5.6.2 with ICNTL(4)=2):
#
#   Le système linéaire à résoudre a 252 degrés de liberté:
#      - 228 sont des degrés de liberté physiques (... 76 noeuds ...)
#      - 24 sont les couples de paramètres de Lagrange ... 12 relations
#   La matrice est de taille 252 équations.
#     Elle contient 4182 termes non nuls si elle est symétrique ...
#     Soit un taux de remplissage de  12.774 %.
#   TEMPS CPU/SYS/ELAPSED ASSEMBLAGE M        :  0.1000D-02 0.0000D+00 ...
#   Entering DMUMPS 5.6.2 with JOB, N, NNZ =   1 ...   (1 analysis, 2
#   ... Elapsed time in analysis driver=  0.0010      factorisation,
#   ... INFOG (12) Number of negative pivots = 24    3 solve)
#   ERROR ANALYSIS BEFORE ITERATIVE REFINEMENT / STATISTICS AFTER ...
#      RINFOG(6):SCALED RESIDUAL, (7)/(8) backward errors W1/W2,
#      (9) Upper bound ERROR, (10)/(11) CONDITION NUMBER (1)/(2)
#   Champ stocké <DEPL> ...                            (solution ready)
#   Statistics:  - _computeMatrix called 1 times in 0.002843 s  ...
#   # Fin commande #0011   user+syst: 0.06s (syst: 0.00s, elaps: 0.00s)
#
# GCPC (gcpc.F90): "* GCPC NORME DU RESIDU = ...", per iteration
# "* ITERATION n NORME DU RESIDU EN ABS/RELA = a r" (with INFO=2 only if
# the residual has dropped by a factor 10: paraaf = 0.1d0), then
# "* NORME DU RESIDU INITIAL/FINAL/RELATIF=" and "* CONVERGENCE EN n
# ITERATIONS".
#
# Meaning (U2.08.03 par. 7.2.1): the error bound RINFOG(9) is roughly
# condition number x 'backward error' and is compared by Code-Aster with
# SOLVEUR/RESI_RELA (U4.50.01 par. 3.5.3).
# ==========================================
_LIN_CMD_RE = re.compile(r"^\s*(?:[A-Za-z_]\w*\s*=\s*)?MECA_STATIQUE\s*\(")
# Modal/buckling (bridge_to_aster._build_modal): the echo of CALC_MODES and
# the lines that aster_results_export.print_modes prints after the solve:
#   BRIDGE_MODE 1 FREQ=7.0737 MASS_EFFE_UN_DX=.. MASS_EFFE_UN_DY=.. ..
#   BRIDGE_MODE 1 CHAR_CRIT=41124.7
_MODES_CMD_RE = re.compile(r"^\s*(?:[A-Za-z_]\w*\s*=\s*)?CALC_MODES\s*\(")
_MODE_LINE_RE = re.compile(r"^BRIDGE_MODE\s+(\d+)\s+(.*)$")
_LIN_END = u"# Fin commande"
_LIN_TXT_KW_RE = re.compile(r"\b(METHODE|PRE_COND|POSTTRAITEMENTS)\s*=\s*"
                            r"'(\w+)'")
_LIN_NUM_KW_RE = re.compile(r"\b(RESI_RELA|NPREC|NMAX_ITER|NIVE_REMPLISSAGE)"
                            r"\s*=\s*([-+0-9.eE]+)")
_LIN_DOF_RE = re.compile(u"système linéaire à résoudre a "
                         r"(\d+) degr")
_LIN_PHYS_RE = re.compile(r"^-\s*(\d+) sont des degr")
_LIN_NODES_RE = re.compile(r"port\S* par (\d+) noeuds")
_LIN_LAGR_RE = re.compile(r"^-\s*(\d+) sont les couples")
_LIN_REL_RE = re.compile(r"aux (\d+) relations lin")
_LIN_EQ_RE = re.compile(r"La matrice est de taille (\d+)")
_LIN_NNZ_RE = re.compile(r"contient (\d+) termes non nuls")
_LIN_FILL_RE = re.compile(r"taux de remplissage de\s*([0-9.]+)\s*%")
_LIN_ASSEMB_RE = re.compile(r"TEMPS CPU/SYS/ELAPSED ASSEMBLAGE ([MV])\s*:"
                            r"\s*(\S+)\s+(\S+)\s+(\S+)")
_LIN_JOB_RE = re.compile(r"Entering [SDCZ]MUMPS (\S+) with JOB\S*\s*"
                         r"(?:,\s*N,\s*NNZ\s*)?=\s*(-?\d+)")
_LIN_DRIVER_RE = re.compile(r"Elapsed time in (analysis|factorization|solve)"
                            r" driver\s*=\s*([0-9.eEdD+-]+)")
_LIN_ORDER_RE = re.compile(r"Ordering based on (\S+)")
_LIN_FLOPS_RE = re.compile(r"RINFOG\(1\)\)?\s*=\s*([-+0-9.eEdD]+)")
_LIN_INFOG_RE = re.compile(r"(?<![RA-Z])INFOG\s*\(\s*(\d+)\s*\)[^=]*="
                           r"\s*([-+0-9.eEdD]+)")
_LIN_MEM_RE = re.compile(r"\(INFOG\((17|19|22)\)\):\s*(\d+)")
# Estimates from the analysis phase (known during the factorisation)
_LIN_FLOPS_EST_RE = re.compile(r"RINFOG\(1\) Operations during elimination "
                               r"\(estim\)\s*=\s*(\S+)")
_LIN_ENTRIES_EST_RE = re.compile(r"\(20\) Number of entries in factors "
                                 r"\(estim\.\)\s*=\s*(\d+)")
_LIN_REFINE_STEPS_RE = re.compile(r"NUMBER OF STEPS OF ITERATIVE REFINEMENTS"
                                  r" PERFORMED\s+(\d+)")
_LIN_RESID_RE = re.compile(r"^RESIDUAL IS \.+ \(MAX-NORM\)\s*=\s*(\S+)")
_LIN_RINFOG_RE = re.compile(r"^(?:RINFOG|-+)\(\s*(\d+)\)\s*:.*=\s*(\S+)\s*$")
_LIN_GCPC_INIT_RE = re.compile(r"^\*\s*GCPC\s+NORME DU RESIDU =\s*(\S+)")
_LIN_GCPC_TARGET_RE = re.compile(r"NORME DU RESIDU A ATTEINDRE EN ABS/RELA="
                                 r"\s*(\S+)\s+(\S+)")
_LIN_GCPC_ITER_RE = re.compile(r"^\*\s*ITERATION\s+(\d+) NORME DU RESIDU EN "
                               r"ABS/RELA =\s*(\S+)\s+(\S+)")
_LIN_GCPC_FINAL_RE = re.compile(r"NORME DU RESIDU INITIAL/FINAL/RELATIF=\s*"
                                r"(\S+)\s+(\S+)\s+(\S+)")
_LIN_GCPC_CONV_RE = re.compile(r"^\*\s*CONVERGENCE EN\s+(\d+) ITERATIONS")
_LIN_STAT_GROUP_RE = re.compile(r"^- (\w+)\.\s*$")
_LIN_STAT_RE = re.compile(r"^(\s*)- (\w+) called (\d+) times in "
                          r"([-+0-9.eE]+) s")
_LIN_FIN_RE = re.compile(r"user\+syst:\s*([0-9.]+)s.*elaps:\s*([0-9.]+)s")

# Phases of a linear solve, in order (key, nl, en).
LIN_PHASES = [
    ("matrix", u"Stijfheidsmatrix (elementen + assemblage)",
     u"Stiffness matrix (elements + assembly)"),
    ("analysis", u"Analyse (ordening, symbolisch)",
     u"Analysis (ordering, symbolic)"),
    ("factor", u"Factorisatie", u"Factorization"),
    ("rhs", u"Belastingsvector", u"Load vector"),
    ("solve", u"Oplossen", u"Solve"),
    ("post", u"Spanningen + opslag", u"Stresses + storage"),
]
_LIN_PHASE_KEYS = [p[0] for p in LIN_PHASES]


def lin_phase_title(key, method="MUMPS"):
    """Title of a phase in the chosen language; with GCPC 'factor' is the
    preconditioning (incomplete factorisation)."""
    if key == "factor" and method == "GCPC":
        return tr(u"Voorconditionering (LDLT_INC)",
                  u"Preconditioner (LDLT_INC)")
    if key == "solve" and method == "GCPC":
        return tr(u"Oplossen (GCPC-iteraties)", u"Solve (GCPC iterations)")
    for k, nl, en in LIN_PHASES:
        if k == key:
            return tr(nl, en)
    return key


class LinearSolve(object):
    """One MECA_STATIQUE call: matrix, solver, phases and quality."""

    def __init__(self, seen_at=None):
        self.command = "MECA_STATIQUE"
        self.started_at = seen_at     # wall clock time (live), else None
        self.status = "bezig"         # bezig / klaar / mislukt
        self.solver = {}              # METHODE, PRE_COND, RESI_RELA, NPREC ..
        self.dofs = None              # total degrees of freedom
        self.dofs_phys = None
        self.nodes = None
        self.lagr_pairs = None        # Lagrange parameters ("couples de
        #                               paramètres de Lagrange", 2 per relation)
        self.relations = None         # dualised linear relations
        self.equations = None
        self.nnz = None               # nonzero terms (symmetric)
        self.fill_pct = None          # fill ratio [%]
        self.mumps = {}               # version, ordering, flops, entries,
        #                               neg_pivots, delayed, front, mem_*
        self.refine_before = {}       # residual and quality before refinement
        self.refine_after = {}        # ... after refinement
        self.refine_steps = None
        self.gcpc_init = None         # initial residual (absolute)
        self.gcpc_target = None       # (absolute, relative)
        self.gcpc_iters = []          # (iteration, absolute, relative)
        self.gcpc_final = None        # (initial, final, relative)
        self.gcpc_converged = None    # number of iterations at convergence
        self.phases = {}              # key -> {start, end, seconds}
        self.current = None           # current phase
        self.stats = {}               # "MumpsSolver.factorize" -> s
        self.cpu_total = None
        self.elapsed_total = None
        self.detailed = False         # INFO=2 output seen (ASSEMBLAGE ..)

    # ---------- phases ----------
    def method(self):
        return self.solver.get("METHODE", u"MUMPS")

    def phase_keys(self):
        """The phases that belong to this solver (order of
        LIN_PHASES)."""
        keys = list(_LIN_PHASE_KEYS)
        if self.method() != "MUMPS":
            keys.remove("analysis")
        return keys

    def phase_seconds(self, key, now=None):
        """Duration of a phase [s]: the value from the output, else the
        wall clock (start..end, or start..now if the phase is running); None
        if unknown."""
        ph = self.phases.get(key)
        if not ph:
            return None
        if ph.get("seconds") is not None:
            return ph["seconds"]
        if ph.get("start") is not None:
            end = ph.get("end")
            if end is None and key == self.current and now is not None:
                end = now
            if end is not None:
                return max(0.0, end - ph["start"])
        return None

    def finished(self):
        return self.status != "bezig"

    def forward_error(self):
        """Estimated relative error of the solution (MUMPS RINFOG(9) after
        refinement), or None."""
        return self.refine_after.get(9)

    def condition(self):
        return self.refine_after.get(10)


def _e(value, digits):
    """Number in e-notation with a point (%-formatting: in IronPython
    str.format gives the decimal comma of the locale); '-' for None."""
    if value is None:
        return u"-"
    return u"%.*e" % (digits, value)


def assess_linear(lin):
    """
    Assessment of a linear solve: list (level, text) with
    level "ok", "info", "let_op" or "fout", in the chosen language.

    Sources: U4.50.01 par. 3.5.3 (RESI_RELA: error bound of MUMPS; larger
    = Code-Aster stops), U2.08.03 par. 7.2.1 (condition number 1e4 = well
    conditioned, up to 1e20 = very poor; 'backward error' for a
    good solution in the order of the machine precision 1e-15) and par. 7.1
    (condition number > 1e12 reveals a singularity, measured without
    preprocessing). The limit 1e-12 for the 'backward error' is a
    choice of the bridge (NOT verified in the U-doc).
    """
    out = []
    resi = lin.solver.get("RESI_RELA")
    method = lin.method()
    nprec = lin.solver.get("NPREC")
    if method == "MUMPS":
        if nprec is not None and nprec < 0:
            if resi is not None and resi < 0:
                out.append(("fout", tr(
                    u"NPREC < 0 en RESI_RELA < 0: geen enkele controle op de "
                    u"oplossing (singuliere matrix wordt niet gemeld).",
                    u"NPREC < 0 and RESI_RELA < 0: no check of the solution "
                    u"at all (a singular matrix is not reported).")))
            else:
                out.append(("info", tr(
                    u"NPREC = {0}: detectie van een singuliere matrix staat "
                    u"uit; de foutgrens (RESI_RELA) is de controle.",
                    u"NPREC = {0}: detection of a singular matrix is off; "
                    u"the error bound (RESI_RELA) is the check.").format(
                        int(nprec))))
        err = lin.forward_error()
        if err is not None and resi is not None and resi > 0:
            if err > resi:
                out.append(("fout", tr(
                    u"Geschatte fout op de oplossing {0} > RESI_RELA "
                    u"{1}: de oplossing is onnauwkeurig (Code-Aster "
                    u"stopt). Controleer opleggingen en materiaal.",
                    u"Estimated error of the solution {0} > RESI_RELA "
                    u"{1}: the solution is inaccurate (Code-Aster "
                    u"stops). Check supports and material.").format(
                        _e(err, 2), _e(resi, 0))))
            else:
                out.append(("ok", tr(
                    u"Geschatte fout op de oplossing {0} <= RESI_RELA "
                    u"{1}.",
                    u"Estimated error of the solution {0} <= RESI_RELA "
                    u"{1}.").format(_e(err, 2), _e(resi, 0))))
        cond = lin.condition()
        if cond is not None:
            if cond > 1e12:
                out.append(("let_op", tr(
                    u"Conditiegetal {0} > 1e12: wijst op een (bijna) "
                    u"singuliere matrix, bijv. een deel dat niet of "
                    u"nauwelijks is vastgehouden, of zeer grote "
                    u"stijfheidsverschillen.",
                    u"Condition number {0} > 1e12: indicates a "
                    u"(nearly) singular matrix, e.g. a part that is not or "
                    u"barely held, or very large stiffness "
                    u"differences.").format(_e(cond, 1))))
            elif cond > 1e4:
                out.append(("info", tr(
                    u"Conditiegetal {0}: gebruikelijk voor een "
                    u"FE-model (1e4 = goed, 1e12 en hoger = verdacht).",
                    u"Condition number {0}: usual for an FE model (1e4 "
                    u"= good, 1e12 and above = suspicious).").format(
                        _e(cond, 1))))
            else:
                out.append(("ok", tr(
                    u"Conditiegetal {0}: goed geconditioneerd.",
                    u"Condition number {0}: well conditioned.").format(
                        _e(cond, 1))))
        bw = lin.refine_after.get(7)
        if bw is not None and bw > 1e-12:
            out.append(("let_op", tr(
                u"'Backward error' {0} is groot (normaal ~1e-15): de "
                u"factorisatie had numerieke moeite.",
                u"Backward error {0} is large (normally ~1e-15): the "
                u"factorization had numerical difficulty.").format(
                    _e(bw, 1))))
        # Negative pivots: a system with Lagrange multipliers is
        # not positive definite; in the test runs the number of negative
        # pivots equalled the number of Lagrange parameters (252 and 268 569
        # equations); with a mechanism (only DX held,
        # FACTOR_57) 10 for 8. More negative pivots point to a non-positive
        # definite stiffness (Sylvester's law of inertia; NOT
        # verified in the U-doc).
        neg = lin.mumps.get("neg_pivots")
        if (neg is not None and lin.lagr_pairs is not None and
                neg > lin.lagr_pairs):
            out.append(("let_op", tr(
                u"{0} negatieve pivots, meer dan de {1} Lagrange-parameters: "
                u"de stijfheidsmatrix is niet positief definiet (negatieve "
                u"stijfheid, of een mechanisme dat alleen numeriek "
                u"vastzit).",
                u"{0} negative pivots, more than the {1} Lagrange "
                u"parameters: the stiffness matrix is not positive definite "
                u"(negative stiffness, or a mechanism held only "
                u"numerically).").format(int(neg), lin.lagr_pairs)))
        delayed = lin.mumps.get("delayed")
        if delayed:
            out.append(("info", tr(
                u"{0} uitgestelde pivots (numeriek pivoteren nodig).",
                u"{0} delayed pivots (numerical pivoting needed).").format(
                    int(delayed))))
    elif method == "GCPC":
        rel = lin.gcpc_final[2] if lin.gcpc_final else None
        if lin.gcpc_converged is not None:
            out.append(("ok", tr(
                u"GCPC geconvergeerd in {0} iteraties (residu {1}, "
                u"criterium {2}).",
                u"GCPC converged in {0} iterations (residual {1}, "
                u"criterion {2}).").format(
                    lin.gcpc_converged, _e(rel, 2), _e(resi, 0))))
            # Limit 20 % of the equations: choice of the bridge (NOT
            # verified in the U-doc; NMAX_ITER 0 = 50 %).
            if lin.equations and lin.gcpc_converged > 0.2 * lin.equations:
                out.append(("let_op", tr(
                    u"Veel iteraties ({0} bij {1} vergelijkingen): trage "
                    u"convergentie (slecht geconditioneerd); MUMPS is dan "
                    u"meestal sneller.",
                    u"Many iterations ({0} for {1} equations): slow "
                    u"convergence (poorly conditioned); MUMPS is then "
                    u"usually faster.").format(lin.gcpc_converged,
                                               lin.equations)))
        elif lin.status == "mislukt":
            out.append(("fout", tr(
                u"GCPC niet geconvergeerd (maximaal aantal iteraties, "
                u"NMAX_ITER = 0: vergelijkingen / 2). Gebruik MUMPS.",
                u"GCPC did not converge (maximum number of iterations, "
                u"NMAX_ITER = 0: equations / 2). Use MUMPS.")))
    if lin.status == "mislukt" and not [o for o in out if o[0] == "fout"]:
        out.append(("fout", tr(
            u"MECA_STATIQUE is mislukt; zie de meldingen hieronder.",
            u"MECA_STATIQUE failed; see the messages below.")))
    return out


def _column_key(name):
    for pattern, key in _COLUMN_KEYS:
        if pattern in name:
            return key
    return None


def event_hint(text):
    """Explanation (chosen language) for an <Erreur>/<Action> text, or u''."""
    for pattern, nl, en in EVENT_TEXTS:
        if pattern in text:
            return tr(nl, en)
    return u""


def pivot_hint(component):
    """Explanation for a zero pivot on this component (e.g. 'LAGS_C', 'DZ')."""
    comp = component.upper()
    if comp.startswith("LAGS_") or comp.startswith("LAG_C"):
        return tr(*_PIVOT_HINT_CONTACT)
    if comp.startswith("LAGR") or comp.startswith("LAG"):
        return tr(*_PIVOT_HINT_LAGR)
    return tr(*_PIVOT_HINT_PHYS)


# ==========================================
# DATA STRUCTURES
# ==========================================
class Step(object):
    """One solve attempt ("Instant de calcul"); a split step gives
    several attempts with a higher level."""

    def __init__(self, index, instant, level, seen_at=None):
        self.index = index            # sequence number of the attempt (0, 1, ...)
        self.instant = instant        # target time of the attempt
        self.level = level            # Niveau de découpe (1 = not split)
        self.seen_at = seen_at        # wall clock time (live), else None
        self.iterations = []          # dicts per Newton iteration
        self.status = "bezig"         # bezig / geconvergeerd / mislukt
        self.error = u""              # <Erreur> text (French)
        self.actions = []             # <Action> texts (French)
        self.cpu = None               # CPU time of the attempt [s]
        self.summary = {}             # newton_count, contact_links, cycles_*
        self.resi_location = u""      # e.g. "node 298 DY"
        self.contact_initial = None   # (in contact, excluded)
        self.energy = {}              # TOTAL line of BILAN D'ENERGIE

    def newton_count(self):
        """Number of Newton iterations (summary, else table rows)."""
        n = self.summary.get("newton_count")
        if n is not None:
            return int(n)
        return len(self.iterations)

    def geom_loops(self):
        """Number of geometric contact loops (BCL. GEOM.), or None."""
        vals = [it["geom"] for it in self.iterations
                if it.get("geom") is not None]
        return int(max(vals)) if vals else None

    def status_changes(self):
        """Sum of the contact status changes (VARI. CONT.), or None."""
        vals = [it["cont_vari"] for it in self.iterations
                if it.get("cont_vari") is not None]
        return int(sum(vals)) if vals else None


class ConvergenceData(object):
    """Everything read from the output so far."""

    def __init__(self):
        self.steps = []
        self.messages = []        # dicts: kind, code, text, hint, step
        self.progress = []        # (percent, instant)
        self.command = None       # STAT_NON_LINE / DYNA_NON_LINE
        self.resi_crit = None     # RESI_GLOB_RELA from the command
        self.iter_max = None      # ITER_GLOB_MAXI from the command
        self.diagnostic = u""     # DIAGNOSTIC JOB, empty while running
        self.partial_until = None  # BRIDGE_ONVOLLEDIG time
        self.t_end = None          # BRIDGE_TEND (failure loop), else None
        self.explicit = False      # explicit scheme seen
        self.fin = False           # "<I> <FIN>" seen (study.comm up to FIN)
        self.stopped = None        # BRIDGE_GESTOPT reason ("user"/"window")
        self.linear = []           # LinearSolve per MECA_STATIQUE
        self.modes = []            # (nr, {FREQ/CHAR_CRIT/MASS_EFFE_UN_..})
        self.lines = 0

    def finished(self):
        return bool(self.diagnostic)

    def last_linear(self):
        return self.linear[-1] if self.linear else None

    def overall_progress(self):
        """(percent, time) of the whole run, or None. With BRIDGE_TEND
        (failure loop, one solve per time step) from time / end time; else
        the last '[ n%]' of Code-Aster."""
        if not self.progress:
            return None
        pct, inst = self.progress[-1]
        if self.t_end and inst is not None and self.t_end > 0.0:
            pct = int(min(100.0, max(0.0, 100.0 * inst / self.t_end)))
        return pct, inst

    def last_converged(self):
        for step in reversed(self.steps):
            if step.status == "geconvergeerd":
                return step
        return None


# ==========================================
# PARSER (incremental)
# ==========================================
class ConvergenceParser(object):
    """
    Reads the output line by line; feed() may be called with chunks of text
    that end in the middle of a line (live fort.6).

    hints : dict code -> explanation in the chosen language (e.g.
            bridge_run_aster.mess_hints()); optioneel.
    clock : function that returns the wall clock time (live), or None.
    """

    def __init__(self, hints=None, clock=None):
        self.data = ConvergenceData()
        self._hints = hints or {}
        self._clock = clock
        self._partial = u""
        self._columns = None       # keys of the current table
        self._names = None         # header names of the current table
        self._header = []          # header lines being built
        self._energy_cols = None
        self._box = None           # [kind, code, lines] being built
        self._pending = u""        # line that continues on the next one
        self._msg_seen = {}
        self._lin = None           # LinearSolve within MECA_STATIQUE
        self._lin_refine = None    # "before" / "after" (MUMPS refinement)
        self._lin_group = u""      # group in the Statistics block
        self._lin_prev = u""       # previous line within MECA_STATIQUE

    # ---------- input ----------
    def feed(self, text):
        """Process a chunk of text (unicode); an incomplete last line
        is kept until the next chunk."""
        text = self._partial + text
        lines = text.split(u"\n")
        self._partial = lines.pop()
        for line in lines:
            self.feed_line(line.rstrip(u"\r"))

    def close(self):
        """Process a possibly incomplete last line."""
        if self._partial:
            self.feed_line(self._partial.rstrip(u"\r"))
            self._partial = u""
        if self._pending:
            line, self._pending = self._pending, u""
            self._handle(line)

    def feed_line(self, line):
        self.data.lines += 1
        if self._pending:
            # Continuation line (residual location or "au numéro d'ordre :").
            line = self._pending.rstrip() + u" " + line.strip()
            self._pending = u""
        elif (u"au noeud et degr" in line and u">" not in
              line.split(u"libert", 1)[-1]):
            self._pending = line
            return
        self._handle(line)

    # ---------- processing ----------
    def _current(self):
        return self.data.steps[-1] if self.data.steps else None

    def _add_message(self, kind, code, text, hint=u""):
        """Add a message; a repeated message adds up (count) and
        gets the latest attempt/time and a new sequence number (seq)."""
        step = self._current()
        self._seq += 1
        key = (kind, code, text[:80])
        msg = self._msg_seen.get(key)
        if msg is None:
            msg = {"kind": kind, "code": code, "text": text, "hint": hint,
                   "count": 0}
            self._msg_seen[key] = msg
            self.data.messages.append(msg)
        msg["count"] += 1
        msg["seq"] = self._seq
        msg["step"] = step.index if step else None
        msg["instant"] = step.instant if step else None

    _seq = 0

    def _handle(self, line):
        data = self.data
        stripped = line.strip()
        if stripped.startswith(u"<I> <FIN>"):
            data.fin = True
            return
        m = _STOPPED_RE.match(stripped)
        if m:
            # Appended by the bridge after a stop: an open message box of
            # the truncated output ends here.
            self._box = None
            data.stopped = m.group(1) or u"user"
            self._add_message("fout", STOPPED_MARK, stopped_text(
                data.stopped))
            return

        # --- message box ---
        if self._box is not None:
            if _BOX_BOTTOM in line:
                kind, code, body = self._box
                self._box = None
                text = u" ".join(body)
                if len(text) > 400:
                    text = text[:400] + u" ..."
                if kind is None:
                    return   # <I> box (e.g. list of alarms)
                self._add_message(kind, code, text, self._hints.get(code, u""))
                if kind == "fout":
                    step = self._current()
                    if step is not None and step.status == "bezig":
                        step.status = "mislukt"
                    if self._lin is not None:
                        self._lin.status = "mislukt"
                return
            part = stripped.strip(_BOX_SIDE).strip()
            m = _BOX_CODE_RE.search(part)
            if m and not self._box[1]:
                self._box[0] = self._kind(m.group(1))
                self._box[1] = m.group(2)
            elif part:
                self._box[2].append(part)
            return
        if _BOX_TOP in line:
            self._box = [None, u"", []]
            return
        m = _BOX_CODE_RE.search(line)
        if m and _BOX_SIDE in line:
            # Box without a recognised top edge (truncated file).
            self._box = [self._kind(m.group(1)), m.group(2), []]
            return

        # --- linear solver (MECA_STATIQUE) ---
        if self._lin is not None:
            if self._lin_line(line, stripped):
                return
        elif _LIN_CMD_RE.match(line):
            self._lin_start()
            self._lin_line(line, stripped)
            return

        # --- modal / buckling ---
        if _MODES_CMD_RE.match(line):
            data.command = u"CALC_MODES"
            return
        m = _MODE_LINE_RE.match(stripped)
        if m:
            values = {}
            for part in m.group(2).split():
                key, _sep, val = part.partition(u"=")
                if _sep:
                    values[key] = _to_float(val)
            data.modes.append((int(m.group(1)), values))
            return

        # --- convergence table ---
        if stripped.startswith(u"|"):
            self._table_line(stripped)
            return
        if stripped.startswith(u"---"):
            if self._header:
                self._finish_header()
            if _DIAG_MARK in stripped:
                data.diagnostic = stripped.split(u":", 1)[1].strip()
            return

        m = _INSTANT_RE.search(line)
        if m:
            step = Step(len(data.steps), _to_float(m.group(1)),
                        int(m.group(2)),
                        self._clock() if self._clock else None)
            if self._contact_init is not None:
                step.contact_initial = self._contact_init
                self._contact_init = None
            data.steps.append(step)
            self._columns = None
            return

        step = self._current()
        if stripped.startswith(u"<Erreur>"):
            text = stripped[len(u"<Erreur>"):].strip()
            if step is not None:
                step.error = text
                step.status = "mislukt"
            # A failed integration of the material law is solved by Code-Aster
            # by splitting the step (e.g. after every failure moment); only if
            # the run stops is it an error, and that comes separately as a box.
            kind = "alarm" if u"intégration" in text else "fout"
            self._add_message(kind, u"", text, event_hint(text))
            return
        if stripped.startswith(u"<Action>"):
            text = stripped[len(u"<Action>"):].strip()
            text = text.replace(u"<Échec>", u"").strip()
            if step is not None:
                step.actions.append(text)
            kind = "fout" if (u"chec" in text or u"arrête" in text) \
                else "actie"
            self._add_message(kind, u"", text, event_hint(text))
            return
        if stripped.startswith(_CONVERGED):
            if step is not None:
                step.status = "geconvergeerd"
            return
        if stripped.startswith(u"Découpe uniforme") and step is not None:
            step.actions.append(stripped)
            return

        m = _RESI_LOC_RE.search(line)
        if m and step is not None:
            step.resi_location = tr(u"knoop {0} {1}",
                                    u"node {0} {1}").format(m.group(3),
                                                            m.group(4))
            return
        m = _PIVOT_RE.search(stripped)
        if m:
            text = tr(u"Pivot nul bij knoop {0}, component {1}.",
                      u"Zero pivot at node {0}, component {1}.").format(
                m.group(1), m.group(2))
            self._add_message("fout", u"PIVOT", text, pivot_hint(m.group(2)))
            return
        m = _CPU_RE.search(line)
        if m and step is not None:
            step.cpu = _to_float(m.group(1))
            return
        if stripped.startswith(u"*"):
            m = _SUMMARY_RE.match(stripped)
            if m and step is not None:
                for pattern, key in _SUMMARY_KEYS:
                    if pattern in m.group(1):
                        step.summary[key] = _to_float(m.group(2))
                        break
            return
        m = _PROGRESS_RE.match(stripped)
        if m:
            data.progress.append((int(m.group(1)), _to_float(m.group(2))))
            return
        m = _TEND_RE.match(stripped)
        if m:
            data.t_end = _to_float(m.group(1))
            return
        if not data.explicit and _EXPLICIT_RE.search(line):
            data.explicit = True
        m = _CONTACT_INIT_RE.search(line)
        if m:
            self._contact_init = (int(m.group(1)), int(m.group(2)))
            return
        if data.command is None or not data.steps:
            m = _COMMAND_RE.search(line)
            if m and data.command in (None, "MECA_STATIQUE"):
                data.command = m.group(1)
            if data.command is not None and not data.steps:
                m = _RESI_CRIT_RE.search(line)
                if m:
                    data.resi_crit = _to_float(m.group(1))
                m = _ITER_MAX_RE.search(line)
                if m:
                    data.iter_max = int(m.group(1))
        m = _PARTIAL_RE.search(line)
        if m:
            data.partial_until = _to_float(m.group(1))
            self._add_message("fout", u"BRIDGE_ONVOLLEDIG",
                              tr(u"Niet geconvergeerd; resultaten tot "
                                 u"t = {0} s.",
                                 u"Not converged; results up to "
                                 u"t = {0} s.").format(m.group(1)))
            return
        m = _FAILURE_RE.search(line)
        if m:
            self._add_message("alarm", u"BRIDGE_BEZWIJKEN", tr(
                u"Bezwijken bij t = {0} s: {1} element(en) van elset {2} "
                u"(totaal {3}).",
                u"Failure at t = {0} s: {1} element(s) of elset {2} "
                u"(total {3}).").format(m.group(1), m.group(3), m.group(2),
                                        m.group(4)), tr(
                u"Hun stijfheid is verlaagd en hun spanning is nul; de "
                u"volgende stap begint met een elastische voorspelling en "
                u"wordt zo nodig opgedeeld.",
                u"Their stiffness has been reduced and their stress is "
                u"zero; the next step starts with an elastic prediction "
                u"and is subdivided if needed."))
            return
        if _DIAG_MARK in line:
            data.diagnostic = line.split(u":", 1)[1].strip()

    _contact_init = None

    @staticmethod
    def _kind(tag):
        return "alarm" if tag == "A" else "fout"

    # ---------- linear solver ----------
    def _now(self):
        return self._clock() if self._clock else None

    def _lin_start(self):
        lin = LinearSolve(self._now())
        self.data.linear.append(lin)
        if self.data.command is None:
            self.data.command = "MECA_STATIQUE"
        self._lin = lin
        self._lin_refine = None
        self._lin_group = u""
        self._lin_phase("matrix")

    def _lin_phase(self, key):
        """Phase 'key' starts (the current phase ends)."""
        lin = self._lin
        now = self._now()
        if lin.current is not None and lin.current != key:
            ph = lin.phases.get(lin.current)
            if ph is not None and ph.get("end") is None:
                ph["end"] = now
        ph = lin.phases.setdefault(key, {"start": now, "end": None,
                                         "seconds": None})
        if ph.get("start") is None:
            ph["start"] = now
        ph["end"] = None
        lin.current = key

    def _lin_phase_end(self, key, seconds=None):
        lin = self._lin
        ph = lin.phases.setdefault(key, {"start": None, "end": None,
                                         "seconds": None})
        ph["end"] = self._now()
        if seconds is not None:
            ph["seconds"] = seconds
        if lin.current == key:
            lin.current = None

    def _lin_finish(self, stripped):
        lin = self._lin
        m = _LIN_FIN_RE.search(stripped)
        if m:
            lin.cpu_total = _to_float(m.group(1))
            lin.elapsed_total = _to_float(m.group(2))
        if lin.current is not None:
            self._lin_phase_end(lin.current)
        # Times from the Statistics block (Python timers of Code-Aster,
        # wall clock) take precedence over the clock of the window; the MUMPS
        # phases keep the 'Elapsed time in ... driver' of MUMPS itself.
        st = lin.stats
        solver = u"GcpcSolver" if lin.method() == "GCPC" else u"MumpsSolver"

        def put(key, value):
            if value is not None:
                ph = lin.phases.setdefault(key, {"start": None, "end": None,
                                                 "seconds": None})
                ph["seconds"] = value
        put("matrix", st.get(u"_computeMatrix"))
        put("rhs", st.get(u"_computeRhs"))
        post = [st[k] for k in (u"_computeStress",
                                u"StorageManager.storeState") if k in st]
        if post:
            put("post", sum(post))
        if lin.method() == "GCPC":
            put("factor", st.get(solver + u".factorize"))
            put("solve", st.get(solver + u".solve"))
        else:
            fac = lin.phases.get("factor", {})
            if fac.get("seconds") is None and solver + u".factorize" in st:
                ana = lin.phases.get("analysis", {}).get("seconds") or 0.0
                put("factor", max(0.0, st[solver + u".factorize"] - ana))
            if lin.phases.get("solve", {}).get("seconds") is None:
                put("solve", st.get(solver + u".solve"))
        if lin.status == "bezig":
            lin.status = "klaar"
        self._lin = None
        self._lin_refine = None

    def _lin_line(self, line, stripped):
        """Line within MECA_STATIQUE; True if it was processed."""
        lin = self._lin
        # Code-Aster breaks long sentences ("taux de remplissage" /
        # "de   0.028 %."): the previous line is included for _LIN_FILL_RE.
        joined = self._lin_prev + u" " + stripped
        self._lin_prev = stripped
        if stripped.startswith(_LIN_END):
            self._lin_finish(stripped)
            return True
        if lin.dofs is None:
            # Command echo: the values of SOLVEUR (incl. the defaults).
            for m in _LIN_TXT_KW_RE.finditer(line):
                lin.solver.setdefault(m.group(1), m.group(2))
            for m in _LIN_NUM_KW_RE.finditer(line):
                value = _to_float(m.group(2))
                if value is not None:
                    if m.group(1) in ("NPREC", "NMAX_ITER",
                                      "NIVE_REMPLISSAGE"):
                        value = int(value)
                    lin.solver.setdefault(m.group(1), value)
            m = _LIN_DOF_RE.search(line)
            if m:
                lin.dofs = int(m.group(1))
                return True
            return False
        # --- matrix (first time; GCPC repeats this after RCMK) ---
        if stripped.startswith(u"-"):
            m = _LIN_PHYS_RE.match(stripped)
            if m and lin.dofs_phys is None:
                lin.dofs_phys = int(m.group(1))
                return True
            m = _LIN_LAGR_RE.match(stripped)
            if m and lin.lagr_pairs is None:
                lin.lagr_pairs = int(m.group(1))
                return True
        for rx, attr, conv in ((_LIN_NODES_RE, "nodes", int),
                               (_LIN_REL_RE, "relations", int),
                               (_LIN_EQ_RE, "equations", int),
                               (_LIN_NNZ_RE, "nnz", int),
                               (_LIN_FILL_RE, "fill_pct", float)):
            m = rx.search(joined if attr == "fill_pct" else line)
            if m:
                if getattr(lin, attr) is None:
                    setattr(lin, attr, conv(m.group(1)))
                return True
        m = _LIN_ASSEMB_RE.search(line)
        if m:
            lin.detailed = True
            if m.group(1) == "M":
                self._lin_phase_end("matrix")
            elif lin.current != "rhs":
                self._lin_phase("rhs")
            return True
        if u"RENUMEROTATION DES NOEUDS" in line:
            self._lin_phase("factor")      # GCPC: RCMK + LDLT_INC
            return True
        m = _LIN_JOB_RE.search(line)
        if m:
            lin.detailed = True
            lin.mumps.setdefault("version", m.group(1))
            job = int(m.group(2))
            key = {1: "analysis", 4: "analysis", 6: "analysis",
                   2: "factor", 5: "factor", 3: "solve"}.get(job)
            if key is not None:
                self._lin_phase(key)
            return True
        m = _LIN_DRIVER_RE.search(line)
        if m:
            key = {"analysis": "analysis", "factorization": "factor",
                   "solve": "solve"}[m.group(1)]
            self._lin_phase_end(key, _to_float(m.group(2)))
            return True
        m = _LIN_ORDER_RE.search(line)
        if m:
            lin.mumps["ordering"] = m.group(1)
            return True
        if u"Start factorization" in line:
            m = _LIN_FLOPS_RE.search(line)
            if m:
                lin.mumps["flops"] = _to_float(m.group(1))
            return True
        m = _LIN_MEM_RE.search(line)
        if m:
            key = {"17": "mem_est", "19": "mem_alloc",
                   "22": "mem_used"}[m.group(1)]
            lin.mumps[key] = int(m.group(2))
            return True
        m = _LIN_FLOPS_EST_RE.search(line)
        if m:
            lin.mumps.setdefault("flops", _to_float(m.group(1)))
            return True
        m = _LIN_ENTRIES_EST_RE.search(line)
        if m:
            lin.mumps["entries_est"] = int(m.group(1))
            return True
        m = _LIN_INFOG_RE.search(line)
        if m:
            key = {"1": "infog1", "11": "front", "12": "neg_pivots",
                   "13": "delayed", "29": "entries"}.get(m.group(1))
            if key is not None:
                lin.mumps[key] = _to_float(m.group(2))
            return True
        if u"ERROR ANALYSIS BEFORE ITERATIVE REFINEMENT" in line:
            self._lin_refine = "before"
            return True
        if u"STATISTICS AFTER ITERATIVE REFINEMENT" in line:
            self._lin_refine = "after"
            return True
        if u"END   ITERATIVE REFINEMENT" in line or \
                u"END ITERATIVE REFINEMENT" in line:
            self._lin_refine = None
            return True
        m = _LIN_REFINE_STEPS_RE.search(line)
        if m:
            lin.refine_steps = int(m.group(1))
            return True
        if self._lin_refine is not None:
            target = (lin.refine_before if self._lin_refine == "before"
                      else lin.refine_after)
            m = _LIN_RESID_RE.match(stripped)
            if m:
                target["resid"] = _to_float(m.group(1))
                return True
            m = _LIN_RINFOG_RE.match(stripped)
            if m:
                target[int(m.group(1))] = _to_float(m.group(2))
                return True
        # --- GCPC ---
        m = _LIN_GCPC_INIT_RE.match(stripped)
        if m:
            lin.detailed = True
            lin.gcpc_init = _to_float(m.group(1))
            self._lin_phase("solve")
            return True
        m = _LIN_GCPC_TARGET_RE.search(stripped)
        if m:
            lin.gcpc_target = (_to_float(m.group(1)), _to_float(m.group(2)))
            return True
        m = _LIN_GCPC_ITER_RE.match(stripped)
        if m:
            lin.gcpc_iters.append((int(m.group(1)), _to_float(m.group(2)),
                                   _to_float(m.group(3))))
            return True
        m = _LIN_GCPC_FINAL_RE.search(stripped)
        if m:
            lin.gcpc_final = tuple(_to_float(m.group(i)) for i in (1, 2, 3))
            return True
        m = _LIN_GCPC_CONV_RE.match(stripped)
        if m:
            lin.gcpc_converged = int(m.group(1))
            self._lin_phase_end("solve")
            return True
        # --- after the solve ---
        if stripped.startswith(u"Champ stock"):
            self._lin_phase("post")
            return True
        m = _LIN_STAT_GROUP_RE.match(line)
        if m:
            self._lin_group = m.group(1)
            return True
        m = _LIN_STAT_RE.match(line)
        if m:
            name = m.group(2)
            if m.group(1):
                name = u"{0}.{1}".format(self._lin_group, name)
            else:
                self._lin_group = u""
            lin.stats[name] = _to_float(m.group(4))
            return True
        return False

    # ---------- tables ----------
    def _cells(self, line):
        return line.strip().strip(u"|").split(u"|")

    def _table_line(self, line):
        cells = self._cells(line)
        first = cells[0].strip() if cells else u""
        if first.startswith(u"BILAN D'ENERGIE"):
            self._energy_cols = [c.strip() for c in cells[1:]]
            return
        if first in (u"PAS COURANT", u"TOTAL"):
            step = self._current()
            if first == u"TOTAL" and step is not None and self._energy_cols:
                for name, cell in zip(self._energy_cols, cells[1:]):
                    step.energy[name] = _to_float(cell.strip())
            return
        if not _NUM_CELL_RE.match(cells[0]):
            if self._header and len(cells) != len(self._header[0]):
                self._header = []
            self._header.append(cells)
            return
        if self._header:
            self._finish_header()
        if not self._columns or len(cells) != len(self._columns):
            return
        step = self._current()
        if step is None:
            return
        it = {"extra": {}, "flags": {}}
        for key, name, cell in zip(self._columns, self._names, cells):
            m = _NUM_CELL_RE.match(cell)
            if key == "option":
                it["option"] = cell.strip()
                continue
            value = None
            if m:
                value = _to_float(m.group(1))
                if m.group(2):
                    it["flags"][key or name] = m.group(2)
            if key is None:
                if value is not None:
                    it["extra"][name] = value
            else:
                it[key] = value
        if it.get("newton") is None:
            return
        step.iterations.append(it)

    def _finish_header(self):
        rows = self._header
        self._header = []
        if not rows:
            return
        n = len(rows[0])
        names = []
        for i in range(n):
            parts = [r[i].strip() for r in rows if i < len(r) and r[i].strip()]
            names.append(u" ".join(parts))
        self._names = names
        self._columns = [_column_key(nm) for nm in names]


# ==========================================
# HELPER FUNCTIONS
# ==========================================
def stopped_text(reason):
    """Text for a run that did not end by itself (BRIDGE_GESTOPT)."""
    if reason == "window":
        return tr(u"Run afgebroken: het Code-Aster-venster is gesloten.",
                  u"Run aborted: the Code-Aster window was closed.")
    return tr(u"Run gestopt door de gebruiker.", u"Run stopped by the user.")


def read_text(path):
    """Text of a .mess/fort.6 (UTF-8, unreadable characters replaced)."""
    f = io.open(path, "rb")
    try:
        return f.read().decode("utf-8", "replace")
    finally:
        f.close()


def parse_file(path, hints=None):
    """Read a complete .mess file. Returns ConvergenceData."""
    parser = ConvergenceParser(hints=hints)
    parser.feed(read_text(path))
    parser.close()
    return parser.data


def modes_text(data, limit=6):
    """Short text with the first modes ('1: 7.074 Hz, 2: ...' or
    buckling load factors), or '' without modes."""
    out = []
    for nr, values in data.modes[:limit]:
        if values.get("FREQ") is not None:
            # %-formatting: format() follows the locale in IronPython
            out.append(u"{0}: {1} Hz".format(nr, "%.4g" % values["FREQ"]))
        elif values.get("CHAR_CRIT") is not None:
            out.append(u"{0}: {1}".format(nr, "%.4g" % values["CHAR_CRIT"]))
    if len(data.modes) > limit:
        out.append(u"...")
    return u", ".join(out)


def summarize(data):
    """Short text summary (log, tests)."""
    steps = data.steps
    conv = [s for s in steps if s.status == "geconvergeerd"]
    fail = [s for s in steps if s.status == "mislukt"]
    its = sum(len(s.iterations) for s in steps)
    last = data.last_converged()
    lines = [
        u"commando={0} RESI_GLOB_RELA={1} ITER_GLOB_MAXI={2}".format(
            data.command, data.resi_crit, data.iter_max),
        u"pogingen={0} geconvergeerd={1} mislukt={2} iteraties={3} "
        u"max_niveau={4}".format(
            len(steps), len(conv), len(fail), its,
            max([s.level for s in steps] or [0])),
        u"laatste geconvergeerd t={0} voortgang={1} diagnose={2} "
        u"fin={3}".format(
            last.instant if last else None,
            data.overall_progress(),
            data.diagnostic or u"(bezig)", data.fin),
    ]
    for lin in data.linear:
        lines.append(
            u"lineair {0} {1}: vergelijkingen={2} nnz={3} status={4} "
            u"fout={5} cond={6} gcpc_iter={7} fasen={8}".format(
                lin.command, lin.method(), lin.equations, lin.nnz,
                lin.status, lin.forward_error(), lin.condition(),
                lin.gcpc_converged,
                u",".join(u"%s:%.3g" % (k, lin.phase_seconds(k))
                          for k in lin.phase_keys()
                          if lin.phase_seconds(k) is not None)))
    for nr, values in data.modes:
        lines.append(u"mode {0}: {1}".format(nr, u" ".join(
            u"{0}={1}".format(k, values[k]) for k in sorted(values))))
    codes = []
    for msg in data.messages:
        c = msg["code"] or msg["text"][:40]
        if c not in codes:
            codes.append(c)
    lines.append(u"meldingen: " + u"; ".join(codes))
    return u"\n".join(lines)


# ==========================================
# PYTHON ERRORS IN THE CONSOLE OUTPUT
#
# A Python error in study.comm (e.g. a typo in #ASTER lines) is
# not in fort.6/study.mess: run_aster only sends stdout of the job via
# "tee" to fort.6, the traceback goes to stderr (the Code-Aster window).
# Seen with Code-Aster 17.4: a SyntaxError then gives "DIAGNOSTIC JOB : OK"
# without <FIN>, a NameError "<F>_ABNORMAL_ABORT". The bridge captures the
# console output in study_console.txt (bridge_run_aster.py).
# ==========================================
_PY_ERR_RE = re.compile(
    r"^([A-Za-z_][\w.]*(?:Error|Exception|Interrupt|Exit)):\s*(.*)$")
_PY_FILE_RE = re.compile(r'^\s*File "([^"]+)", line (\d+)')


def python_errors(text, max_errors=5):
    """
    Python errors (traceback or SyntaxError) from console output.

    Only an error line ("NameError: ...") at the start of a line,
    after a traceback or after a 'File "...", line n' line counts; this way
    Code-Aster messages such as <ConvergenceError> give no false hits.

    Returns
    -------
    list of unicode - e.g. "SyntaxError: keyword argument repeated:
                      INCREMENT (line: 'INCREMENT=_F(...)')", unique, in
                      order of occurrence.
    """
    lines = text.splitlines()
    found = []
    for i, line in enumerate(lines):
        m = _PY_ERR_RE.match(line.rstrip())
        if not m or m.group(1).startswith(u"libaster."):
            # libaster.AsterError etc.: Code-Aster error with its own
            # message box in study.mess (seen with FACTOR_11, DVP_2).
            continue
        frame = None
        in_traceback = False
        for j in range(i - 1, max(-1, i - 60), -1):
            prev = lines[j]
            if prev.startswith(u"Traceback (most recent call last)"):
                in_traceback = True
                if j > 0 and lines[j - 1].strip() == u"--- Logging error ---":
                    # logging.Handler.handleError: a log line could not
                    # go to the console (no console, e.g. a job without
                    # window: "De ingang is ongeldig"); the job just
                    # keeps solving (DIAGNOSTIC JOB : OK, seen 17.4)
                    in_traceback = None
                break
            fm = _PY_FILE_RE.match(prev)
            if fm and (frame is None or u".comm" in fm.group(1)):
                frame = (fm.group(1), j)    # frame in study.comm wins
            if not fm and not prev.startswith(u" ") and prev.strip():
                break
        if in_traceback is None or (frame is None and not in_traceback):
            continue
        msg = u"{0}: {1}".format(m.group(1), m.group(2).strip())
        if frame is not None and frame[1] + 1 < i:
            code = lines[frame[1] + 1].strip()
            if (code and not code.startswith(u"^") and
                    not code.startswith(u"File ")):
                if len(code) > 120:
                    code = code[:120] + u"..."
                msg += tr(u" (regel: '{0}')", u" (line: '{0}')").format(code)
        if msg not in found:
            found.append(msg)
        if len(found) >= max_errors:
            break
    return found


# ==========================================
# LIVE fort.6 OF A RUNNING RUN
#
# run_aster (Code-Aster 17.4, lib/aster/run_aster/run.py) runs the job in
# a temporary folder (tempfile.mkdtemp(prefix="run_aster_"), in the folder
# "tmpdir" from share/aster/config.json, else %TEMP%) and writes the
# output live in that folder via "tee -a fort.6". Only at the end does it
# copy fort.6 to the .mess file from the .export and remove the
# folder. The folder holds a copy of the .export ("<pid>.export") with the
# line "F mess <path> R 6"; that is how we recognise the run.
# ==========================================
def _norm(path):
    return os.path.normcase(os.path.normpath(path.replace("/", os.sep)))


def aster_tmp_dirs(root):
    """Folders in which run_aster creates its run_aster_* folder: "tmpdir"
    from share/aster/config.json of the installation in root, else %TEMP%
    (run_aster uses tempfile.mkdtemp(dir=tmpdir); run_aster/run.py)."""
    import json
    import tempfile
    dirs = []
    cfg = os.path.join(root, "share", "aster", "config.json")
    try:
        f = io.open(cfg, encoding="utf-8")
        try:
            tmp = json.load(f).get("tmpdir")
        finally:
            f.close()
        if tmp:
            dirs.append(tmp)
    except Exception:
        pass
    for d in (tempfile.gettempdir(), os.environ.get("TEMP"),
              os.environ.get("TMP")):
        if d and d not in dirs:
            dirs.append(d)
    return dirs


def run_dir_mess(run_dir):
    """The .mess path from the .export in a run_aster folder, or None."""
    try:
        names = os.listdir(run_dir)
    except OSError:
        return None
    for name in names:
        if not name.endswith(".export"):
            continue
        try:
            text = read_text(os.path.join(run_dir, name))
        except (IOError, OSError):
            continue
        for line in text.splitlines():
            parts = line.split()
            if len(parts) >= 4 and parts[0] == "F" and parts[1] == "mess":
                return u" ".join(parts[2:-2])
    return None


def find_live_fort6(tmp_dirs, mess_path, since=0.0):
    """
    Find the fort.6 of the running run that writes to mess_path.

    tmp_dirs : list of folders in which run_aster creates its run_aster_* folder.
    since    : only folders created after this time (time.time())
               (2 s margin); 0 = all.

    Returns
    -------
    (path to fort.6, creation time of the folder) of the newest matching
    folder, or (None, None).
    """
    target = _norm(mess_path)
    best = (None, None)
    for tmp in tmp_dirs:
        try:
            names = os.listdir(tmp)
        except OSError:
            continue
        for name in names:
            if not name.startswith("run_aster_"):
                continue
            run_dir = os.path.join(tmp, name)
            fort6 = os.path.join(run_dir, "fort.6")
            try:
                created = os.path.getctime(run_dir)
            except OSError:
                continue
            if created < since - 2.0 or not os.path.isfile(fort6):
                continue
            mess = run_dir_mess(run_dir)
            if mess is None or _norm(mess) != target:
                continue
            if best[1] is None or created > best[1]:
                best = (fort6, created)
    return best
