# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Offline test van Scripts/bridge_convergence.py (Python 2.7 en 3).
#
#   python tests/test_bridge_convergence.py [extra .mess-bestanden ...]
#
# De teksten hieronder zijn ingekorte stukken echte Code-Aster 17.4-uitvoer
# (study.mess / console van testmodellen: impliciete dynamica met contact,
# een pivot nul op LAGS_C, ENERGIE zonder contact, Python-fouten in
# study.comm). Extra .mess-bestanden op de opdrachtregel worden alleen
# samengevat (en mogen niet tot een fout leiden).

from __future__ import print_function

import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(globals().get("__file__",
                                                     sys.argv[0])))
sys.path.insert(0, os.path.join(_HERE, "..", "Scripts"))
import bridge_utils  # noqa: E402
# De verwachte teksten hieronder zijn Nederlands; de standaardtaal is Engels.
bridge_utils.CONFIG_BRIDGE["language"] = "nl"
import bridge_convergence as bc  # noqa: E402

SEP = u"-" * 137
HEAD = (u"|     CONTACT    |     NEWTON     |     RESIDU     |     RESIDU     |"
        u"     OPTION     |     CONTACT    |     CONTACT    |     CONTACT    |\n"
        u"|    BCL. GEOM.  |    ITERATION   |     RELATIF    |     ABSOLU     |"
        u"   ASSEMBLAGE   |   NEWTON GENE  |    PRESSURE    |     CRITERE    |\n"
        u"|    ITERATION   |                | RESI_GLOB_RELA | RESI_GLOB_MAXI |"
        u"(+ TYPE MATRICE)|   VARI. CONT.  |    ERROR       |    VALEUR      |\n")

MESS_CONTACT = u"\n".join([
    u"res = DYNA_NON_LINE(AFFICHAGE=_F(INFO_RESIDU='NON',",
    u"                                   ITER_GLOB_MAXI=20,",
    u"                                   RESI_GLOB_RELA=1e-06,",
    u"Il y a 0 points initialement en contact et 0 points exclus.",
    SEP,
    u"Instant de calcul:  5.000000000000e-03 - Niveau de d\u00e9coupe: 1",
    u"",
    SEP,
    HEAD + SEP,
    u"|     1        X |     0        X | 2.86516E-09    | 1.73583E-10    |TANGENTE   (SYM)|     1        X | 0.00000E+00    |                |",
    u"|     1        X |     1        X | 3.44757E-01  X | 3.22920E-01    |TANGENTE   (SYM)|   296        X | 4.19905E+02    |                |",
    u"|     1        X |     2        E | 1.94931E+00  X | 5.80928E+03    |TANGENTE (NOSYM)|     0          | 7.40079E-03    |                |",
    SEP,
    u"<Erreur> Le nombre maximum d'it\u00e9rations de Newton est atteint",
    u"",
    u"<Action> On essaie de d\u00e9couper le pas de temps.",
    u"On utilise la d\u00e9coupe manuelle.",
    u"D\u00e9coupe uniforme \u00e0 partir de l'instant  0.000000000000e+00 en 4 pas de temps.",
    u"<Action> On d\u00e9coupe le pas de temps.",
    u"Temps CPU consomm\u00e9 dans ce pas de temps    : 2.000 s",
    u"* Nombre d'it\u00e9rations de Newton                     : 3",
    u"* Nombre de liaisons de contact                     : 0",
    SEP,
    u"Instant de calcul:  1.250000000000e-03 - Niveau de d\u00e9coupe: 2",
    u"",
    SEP,
    HEAD + SEP,
    u"|     1        X |     0        X | 3.37162E-10    | 8.17067E-11    |TANGENTE   (SYM)|     1        X | 4.03280E-02    |                |",
    u"|     1        X |     1          | 2.99987E-09    | 2.36352E-06    |TANGENTE (NOSYM)|     0          | 6.50648E-03    | 1.00000E-01    |",
    SEP,
    u"|     2        X |     0        X | 1.00086E+00  X | 1.72407E+03    |TANGENTE (NOSYM)|    44        X | 2.69431E+06    |                |",
    u"|     2          |     1          | 1.12645E-12    | 8.84000E-10    |TANGENTE (NOSYM)|     0          | 2.19978E-06    | 5.08896E-03    |",
    SEP,
    u"Crit\u00e8re(s) de convergence atteint(s)",
    u"",
    u"Le r\u00e9sidu de type <RESI_GLOB_RELA> vaut  1.126447219273e-12 au noeud et degr\u00e9 de libert\u00e9 <298    ",
    u"DY>",
    u"Temps CPU consomm\u00e9 dans ce pas de temps    : 2.000 s",
    u"* Nombre d'it\u00e9rations de Newton                     : 4",
    u"* Nombre de liaisons de contact                     : 8",
    u"* Nombre de cycles de type contact/pas contact      : 0",
    u"[  0%] Instant calcul\u00e9 : 1.25000e-03, seul l'instant initial a \u00e9t\u00e9 archiv\u00e9",
    u" \u2554\u2550\u2550\u2550\u2557",
    u" \u2551 <ConvergenceError> <MECANONLINE9_7>      \u2551",
    u" \u2551                                          \u2551",
    u" \u2551 Arr\u00eat pour cause d'absence de convergence \u2551",
    u" \u255a\u2550\u2550\u2550\u255d",
    u"BRIDGE_ONVOLLEDIG 0.11",
    u" <I> <FIN> ARRET NORMAL DANS \"FIN\" PAR APPEL A \"JEFINI\".",
    u"------------------------------------------------------------",
    u"--- DIAGNOSTIC JOB : <A>_ALARM",
    u"------------------------------------------------------------",
    u"",
])

MESS_PIVOT = u"\n".join([
    u"res = STAT_NON_LINE(CONVERGENCE=_F(RESI_GLOB_RELA=1e-06,",
    u"Il y a 2102 points initialement en contact et 8298 points exclus.",
    SEP,
    u"Instant de calcul:  5.000000000000e-01 - Niveau de d\u00e9coupe: 1",
    SEP,
    HEAD + SEP,
    u"Degr\u00e9 de libert\u00e9 physique associ\u00e9 au noeud 15405 et \u00e0 la composante LAGS_C.",
    u"",
    u"|     1        X |     0        E |                |                |TANGENTE   (SYM)|                |                |                |",
    SEP,
    u"<Erreur> La matrice du syst\u00e8me est singuli\u00e8re",
    u"<Action><\u00c9chec> \u00c9chec dans la tentative de d\u00e9couper le pas de temps.",
    u"<Action> On arr\u00eate le calcul.",
    u"",
])

MESS_ENERGY = u"\n".join([
    u"Instant de calcul:  5.000000000000e-03 - Niveau de d\u00e9coupe: 1",
    u"-" * 69,
    u"|     NEWTON     |     RESIDU     |     RESIDU     |     OPTION     |",
    u"|    ITERATION   |     RELATIF    |     ABSOLU     |   ASSEMBLAGE   |",
    u"|                | RESI_GLOB_RELA | RESI_GLOB_MAXI |(+ TYPE MATRICE)|",
    u"-" * 69,
    u"|     0          | 5.05448E-09    | 3.06222E-10    |TANGENTE   (SYM)|",
    u"-" * 69,
    u"| BILAN D'ENERGIE |  TRAV_EXT   |  ENER_TOT   |  ENER_CIN   |  TRAV_AMOR  |  DISS_SCH   |",
    u"|   PAS COURANT   |  2.9729E-14 |  1.0255E-29 |  1.0768E-20 |  0.0000E+00 |  2.9729E-14 |",
    u"|      TOTAL      |  2.9729E-14 |  1.0255E-29 |  1.0768E-20 |  0.0000E+00 |  2.9729E-14 |",
    u"Crit\u00e8re(s) de convergence atteint(s)",
    u"",
])

CONSOLE = u"\n".join([
    u"Het systeem kan het opgegeven station niet vinden.",
    # logging zonder console (job zonder venster): geen fout in study.comm
    u"--- Logging error ---",
    u"Traceback (most recent call last):",
    u'  File "C:\\code_aster\\Lib\\logging\\__init__.py", line 1113, in emit',
    u"    stream.write(msg + self.terminator)",
    u"    ^^^^^^^^^^^^",
    u"AttributeError: 'NoneType' object has no attribute 'write'",
    u"Call stack:",
    u'  File "C:\\Temp\\run_aster_x\\study.comm.changed.py", line 389',
    u"    INCREMENT=_F(LIST_INST=listinst),",
    u"    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
    u"SyntaxError: keyword argument repeated: INCREMENT",
    u"Traceback (most recent call last):",
    u'  File "C:\\Temp\\run_aster_y\\study.comm.changed.py", line 39, in <module>',
    u"    x = onbekende_naam + 1",
    u"        ^^^^^^^^^^^^^^",
    u"NameError: name 'onbekende_naam' is not defined",
    u"Traceback (most recent call last):",
    u'  File "C:\\Temp\\run_aster_z\\study.comm.changed.py", line 50, in <module>',
    u"    res = STAT_NON_LINE(",
    u'  File "C:\\code_aster\\Supervis\\ExecuteCommand.py", line 282, in _call_oper',
    u"    return libaster.call_oper(syntax, 0)",
    u"libaster.AsterError: ",
    u" \u2551 <ConvergenceError> <MECANONLINE9_7>  \u2551",
    u"ValueError: geen traceback ervoor, telt niet",
    u"",
])


# MECA_STATIQUE met INFO=2 en MUMPS (blok van 268 569 vergelijkingen, ingekort;
# Code-Aster breekt de zinnen over de matrix af).
MESS_LIN_MUMPS = u"\n".join([
    u"res = MECA_STATIQUE(CHAM_MATER=fieldmat,",
    u"                    INFO=2,",
    u"                    SOLVEUR=_F(ACCELERATION='AUTO',",
    u"                               METHODE='MUMPS',",
    u"                               NPREC=-1,",
    u"                               POSTTRAITEMENTS='AUTO',",
    u"                               RESI_RELA=1e-06,",
    u"                               TYPE_RESOL='AUTO'))",
    u"",
    u"Le système linéaire à résoudre a 268569 degrés de liberté:",
    u"   - 265923 sont des degrés de liberté",
    u"physiques",
    u"     (ils sont portés par 88641 noeuds du maillage)",
    u"   - 2646 sont les couples de",
    u"paramètres de Lagrange associés",
    u"     aux 1323 relations linéaires dualisées.",
    u"La matrice est de taille 268569 équations.",
    u"  Elle contient 10208313 termes non nuls si elle est",
    u"symétrique et 20148057 termes non nuls si elle n'est pas symétrique.",
    u"  Soit un taux de remplissage",
    u"de   0.028 %.",
    u"Attention, le critère de détection de singularité (paramètre "
    u"SOLVEUR/NPREC) est trop relâché:",
    u"    * RESI_RELA du bloc",
    u"TEMPS CPU/SYS/ELAPSED ASSEMBLAGE M        :  0.2690D+00 0.0000D+00 "
    u"0.0000D+00",
    u"Entering DMUMPS 5.6.2 with JOB, N, NNZ =   1      268569       10174999",
    u" Ordering based on METIS",
    u" -- (20) Number of entries in factors (estim.)  =       245230632",
    u" RINFOG(1) Operations during elimination (estim)= 4.308D+11",
    u"    Total space in MBytes, IC factorization      (INFOG(17)):        6502",
    u" Elapsed time in analysis driver=       0.9160",
    u"Entering DMUMPS 5.6.2 with JOB, N, NNZ =   2      268569       10174999",
    u" Start factorization with total estimated flops (RINFOG(1))"
    u"                         =  4.308D+11",
    u"  --- (12) Number of negative pivots           =            2646",
    u" ** Memory allocated, total in Mbytes           (INFOG(19)):        6501",
    u" ** Memory effectively used, total in Mbytes    (INFOG(22)):        2272",
    u" INFOG (11) Maximum front size                      =            3969",
    u" INFOG (29) Number of entries in factors            =       244308006",
    u" INFOG (12) Number of negative pivots               =            2646",
    u" INFOG (13) Number of delayed pivots                =               0",
    u" Elapsed time in factorization driver               =     15.1360",
    u"TEMPS CPU/SYS/ELAPSED ASSEMBLAGE V        :  0.2000D-02 0.0000D+00 "
    u"0.0000D+00",
    u"Entering DMUMPS 5.6.2 with JOB, N, NNZ =   3      268569       10174999",
    u"  --- (20)                                     =           0",
    u" ERROR ANALYSIS BEFORE ITERATIVE REFINEMENT",
    u" RESIDUAL IS ............ (MAX-NORM)        = 3.62D-10",
    u" RINFOG(6):SCALED RESIDUAL ...... (MAX-NORM)= 2.45D-16",
    u" RINFOG(7):COMPONENTWISE SCALED RESIDUAL(W1)= 6.74D-16",
    u" ------(8):---------------------------- (W2)= 2.00D-19",
    u" STATISTICS AFTER ITERATIVE REFINEMENT ",
    u" NUMBER OF STEPS OF ITERATIVE REFINEMENTS PERFORMED     0",
    u" RESIDUAL IS ............ (MAX-NORM)        = 3.62D-10",
    u" RINFOG(6):SCALED RESIDUAL ...... (MAX-NORM)= 2.45D-16",
    u" RINFOG(7):COMPONENTWISE SCALED RESIDUAL(W1)= 6.74D-16",
    u" ------(8):---------------------------- (W2)= 2.00D-19",
    u" ------(9):Upper bound ERROR ...............= 1.42D-08",
    u" -----(10):CONDITION NUMBER (1) ............= 2.11D+07",
    u" -----(11):CONDITION NUMBER (2) ............= 3.78D+01",
    u" END   ITERATIVE REFINEMENT ",
    u" Elapsed time in solve driver=       5.6130",
    u"Champ stocké <DEPL> à l'instant  0.000000000000e+00 pour le "
    u"numéro d'ordre 1",
    u"Entering DMUMPS 5.6.2 with JOB =  -2",
    u"Statistics:",
    u"- _computeMatrix called 1 times in 1.176901 s",
    u"- DiscreteComputation.",
    u"  - getLinearStiffnessMatrix called 1 times in 0.900000 s",
    u"- MumpsSolver.",
    u"  - factorize called 1 times in 16.100000 s",
    u"  - solve called 1 times in 5.613000 s",
    u"- _computeRhs called 1 times in 0.010192 s",
    u"- StorageManager.",
    u"  - storeState called 1 times in 0.002000 s",
    u"- _computeStress called 1 times in 0.631859 s",
    u"# Résultat commande #0011 (MECA_STATIQUE): res ('<00000009>') de "
    u"type <ElasticResult>",
    u"# Fin commande #0011   user+syst:       20.66s (syst:        1.94s, "
    u"elaps:        0.00s)",
    # CALC_CHAMP REAC_NODA schrijft ook een stelsel; hoort er niet bij.
    u"Le système linéaire à résoudre a 999 degrés de "
    u"liberté:",
    u"--- DIAGNOSTIC JOB : OK",
    u"",
])

# MECA_STATIQUE met GCPC (blok van 37 389 vergelijkingen, ingekort).
MESS_LIN_GCPC = u"\n".join([
    u"res = MECA_STATIQUE(CHAM_MATER=fieldmat,",
    u"                    SOLVEUR=_F(METHODE='GCPC',",
    u"                               NIVE_REMPLISSAGE=0,",
    u"                               NMAX_ITER=0,",
    u"                               PRE_COND='LDLT_INC',",
    u"                               RESI_RELA=1e-06))",
    u"Le système linéaire à résoudre a 37389 degrés de liberté:",
    u"La matrice est de taille 37389 équations.",
    u"TEMPS CPU/SYS/ELAPSED ASSEMBLAGE M        :  0.3500D-01 0.0000D+00 "
    u"0.0000D+00",
    u" --- RENUMEROTATION DES NOEUDS DU MODELE (RCMK) :",
    u"    --- NOMBRE DE COMPOSANTES CONNEXES DU MODELE :                    1",
    u"Le système linéaire à résoudre a 37389 degrés de liberté:",
    u"TEMPS CPU/SYS/ELAPSED ASSEMBLAGE V        :  0.0000D+00 0.0000D+00 "
    u"0.0000D+00",
    u"",
    u"   * GCPC   NORME DU RESIDU = 0.9500D+02  (INITIALISATION PAR X = ZERO)",
    u"   *        NORME DU RESIDU A ATTEINDRE EN ABS/RELA= 0.9500D-04 "
    u"0.1000D-05",
    u"",
    u"   * ITERATION  229 NORME DU RESIDU EN ABS/RELA = 0.6611D+01 0.6959D-01",
    u"   * ITERATION  252 NORME DU RESIDU EN ABS/RELA = 0.8404D-01 0.8847D-03",
    u"   * ITERATION  279 NORME DU RESIDU EN ABS/RELA = 0.4335D-03 0.4563D-05",
    u"   * NORME DU RESIDU INITIAL/FINAL/RELATIF= 0.9500D+02 0.8098D-04 "
    u"0.8524D-06",
    u"",
    u"  ********************************",
    u"  * CONVERGENCE EN  292 ITERATIONS",
    u"  ********************************",
    u"Champ stocké <DEPL> à l'instant  0.000000000000e+00 pour le "
    u"numéro d'ordre 1",
    u"Statistics:",
    u"- _computeMatrix called 1 times in 0.154187 s",
    u"- GcpcSolver.",
    u"  - factorize called 1 times in 0.154071 s",
    u"  - solve called 1 times in 1.066494 s",
    u"- _computeRhs called 1 times in 0.002268 s",
    u"- _computeStress called 1 times in 0.084780 s",
    u"# Fin commande #0011   user+syst:        1.44s (syst:        0.02s, "
    u"elaps:        0.00s)",
    u"",
])

# Mechanisme (alleen DX vastgehouden), NPREC=-1: FACTOR_57.
MESS_LIN_FAIL = u"\n".join([
    u"res = MECA_STATIQUE(SOLVEUR=_F(METHODE='MUMPS', NPREC=-1, "
    u"RESI_RELA=1e-06))",
    u"Le système linéaire à résoudre a 236 degrés de liberté:",
    u"   - 228 sont des degrés de liberté physiques",
    u"   - 8 sont les couples de paramètres de Lagrange associés",
    u"Entering DMUMPS 5.6.2 with JOB, N, NNZ =   2         236           3953",
    u" INFOG (12) Number of negative pivots               =              10",
    u" Elapsed time in factorization driver               =      0.0010",
    u"Entering DMUMPS 5.6.2 with JOB, N, NNZ =   3         236           3953",
    u" STATISTICS AFTER ITERATIVE REFINEMENT ",
    u" ------(9):Upper bound ERROR ...............= 5.85D+00",
    u" -----(10):CONDITION NUMBER (1) ............= 2.38D+16",
    u" END   ITERATIVE REFINEMENT ",
    u" Elapsed time in solve driver=       0.0020",
    u" ╔═══╗",
    u" ║ <EXCEPTION> <FACTOR_57>                  ║",
    u" ║ Solveur MUMPS :                          ║",
    u" ║   La solution du système linéaire est trop imprécise : ║",
    u" ╚═══╝",
    u"# Fin commande #0011   user+syst:        0.05s (syst:        0.00s, "
    u"elaps:        0.00s)",
    u"",
])


# Modaal (CALC_MODES + aster_results_export.print_modes), ingekort uit een
# run van Mecway's VibratingCantileverBeam.
MESS_MODES = u"\n".join([
    u"res = CALC_MODES(CALC_FREQ=_F(NMAX_FREQ=5),",
    u"                 MATR_MASS=masse,",
    u"BRIDGE_MODE 1 FREQ=7.07368492128143 MASS_EFFE_UN_DX=5.195e-49 "
    u"MASS_EFFE_UN_DY=0.613074 MASS_EFFE_UN_DZ=7.24243e-37",
    u"BRIDGE_MODE 2 FREQ=14.1473698425628 MASS_EFFE_UN_DX=4.48405e-43 "
    u"MASS_EFFE_UN_DY=3.22388e-34 MASS_EFFE_UN_DZ=0.613074",
    u"BRIDGE_MODE 3 CHAR_CRIT=41124.699122467",
    u"",
])


def check(cond, text):
    if not cond:
        raise AssertionError(text)


def test_contact():
    p = bc.ConvergenceParser(hints={"MECANONLINE9_7": u"uitleg"})
    # In kleine stukken voeren, zoals live uit fort.6.
    for i in range(0, len(MESS_CONTACT), 37):
        p.feed(MESS_CONTACT[i:i + 37])
    p.close()
    d = p.data
    check(d.command == "DYNA_NON_LINE", d.command)
    check(d.resi_crit == 1e-6 and d.iter_max == 20, (d.resi_crit, d.iter_max))
    check(len(d.steps) == 2, len(d.steps))
    s0, s1 = d.steps
    check(s0.status == "mislukt" and s0.level == 1, s0.status)
    check(abs(s0.instant - 5e-3) < 1e-12, s0.instant)
    check(len(s0.iterations) == 3, len(s0.iterations))
    it = s0.iterations[1]
    check(it["resi_rela"] == 0.344757 and it["flags"]["resi_rela"] == "X", it)
    check(it["cont_vari"] == 296 and it["cont_press"] == 419.905, it)
    check(s0.iterations[2]["flags"]["newton"] == "E", s0.iterations[2])
    check(s0.newton_count() == 3 and s0.cpu == 2.0, s0.summary)
    check(s1.status == "geconvergeerd" and s1.level == 2, s1.status)
    check(s1.geom_loops() == 2 and s1.status_changes() == 45,
          (s1.geom_loops(), s1.status_changes()))
    check(s1.iterations[-1]["cont_crit"] == 5.08896e-3, s1.iterations[-1])
    check(s1.resi_location == u"knoop 298 DY", s1.resi_location)
    check(s1.summary["contact_links"] == 8, s1.summary)
    check(s0.contact_initial == (0, 0), s0.contact_initial)
    check(d.progress == [(0, 1.25e-3)], d.progress)
    check(d.partial_until == 0.11 and d.fin, (d.partial_until, d.fin))
    check(d.diagnostic == u"<A>_ALARM", d.diagnostic)
    codes = [m["code"] for m in d.messages]
    check(u"MECANONLINE9_7" in codes, codes)
    msg = [m for m in d.messages if m["code"] == u"MECANONLINE9_7"][0]
    check(msg["hint"] == u"uitleg" and msg["kind"] == "fout", msg)
    newton = [m for m in d.messages if u"maximum d'it" in m["text"]][0]
    check(newton["hint"].startswith(u"Maximaal"), newton)


def test_pivot():
    p = bc.ConvergenceParser()
    p.feed(MESS_PIVOT)
    p.close()
    d = p.data
    check(d.command == "STAT_NON_LINE", d.command)
    check(d.steps[0].status == "mislukt", d.steps[0].status)
    check(d.steps[0].contact_initial == (2102, 8298), d.steps[0].contact_initial)
    piv = [m for m in d.messages if m["code"] == u"PIVOT"][0]
    check(u"15405" in piv["text"] and u"LAGS_C" in piv["text"], piv)
    check(piv["hint"].startswith(u"Contact-Lagrange"), piv["hint"])
    kinds = [(m["kind"], m["hint"][:10]) for m in d.messages]
    check(("fout", u"Opdelen lu") in kinds, kinds)
    check(("fout", u"Code-Aster") in kinds, kinds)
    check(not d.fin, d.fin)


def test_energy():
    p = bc.ConvergenceParser()
    p.feed(MESS_ENERGY)
    p.close()
    s = p.data.steps[0]
    check(s.status == "geconvergeerd", s.status)
    check(len(s.iterations) == 1 and s.iterations[0]["resi_rela"] == 5.05448e-9,
          s.iterations)
    check(s.energy.get("TRAV_EXT") == 2.9729e-14 and len(s.energy) == 5,
          s.energy)


def test_python_errors():
    errs = bc.python_errors(CONSOLE)
    check(len(errs) == 2, errs)
    check(errs[0].startswith(u"SyntaxError: keyword argument repeated") and
          u"INCREMENT=_F(LIST_INST=listinst)," in errs[0], errs[0])
    check(errs[1].startswith(u"NameError") and u"onbekende_naam + 1" in
          errs[1], errs[1])


def test_failure():
    """BRIDGE_BEZWIJKEN-regels (bridge_failure.py) worden een melding."""
    p = bc.ConvergenceParser()
    p.feed(u"BRIDGE_BEZWIJKEN t=0.6 elset=Kerf nieuw=2 totaal=4 "
           u"cellen=76,78\n")
    p.close()
    msgs = [m for m in p.data.messages if m["code"] == u"BRIDGE_BEZWIJKEN"]
    check(len(msgs) == 1 and u"0.6" in msgs[0]["text"] and
          u"Kerf" in msgs[0]["text"], p.data.messages)
    # Bezwijklus: een solve per tijdstap, '[100%]' geldt per aanroep; de
    # voortgang van de run volgt uit BRIDGE_TEND.
    p = bc.ConvergenceParser()
    p.feed(u"BRIDGE_TEND 1.0\n"
           u"[100%] Instant calculé : 1.00000e-01, dernier instant "
           u"archivé : 1.00000e-01\n")
    p.close()
    check(p.data.overall_progress() == (10, 0.1), p.data.overall_progress())


class FakeClock(object):
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def test_linear_mumps():
    clock = FakeClock()
    p = bc.ConvergenceParser(clock=clock)
    text = MESS_LIN_MUMPS
    # Live: tot en met de start van de factorisatie, 10 s later de rest.
    cut = text.index(u"NNZ =   2")
    cut = text.index(u"\n", cut) + 1
    for i in range(0, cut, 41):
        p.feed(text[i:min(i + 41, cut)])
    d = p.data
    lin = d.last_linear()
    check(d.command == "MECA_STATIQUE" and not d.steps, d.command)
    check(lin.current == "factor" and not lin.finished(), lin.current)
    check(lin.mumps.get("flops") == 4.308e11 and
          lin.mumps.get("entries_est") == 245230632, lin.mumps)
    clock.t = 110.0
    check(abs(lin.phase_seconds("factor", clock.t) - 10.0) < 1e-9,
          lin.phase_seconds("factor", clock.t))
    p.feed(text[cut:])
    p.close()
    check(lin.finished() and lin.status == "klaar", lin.status)
    check(lin.solver == {"METHODE": "MUMPS", "NPREC": -1,
                         "POSTTRAITEMENTS": "AUTO", "RESI_RELA": 1e-6},
          lin.solver)
    check((lin.dofs, lin.dofs_phys, lin.nodes, lin.lagr_pairs, lin.relations,
           lin.equations, lin.nnz, lin.fill_pct) ==
          (268569, 265923, 88641, 2646, 1323, 268569, 10208313, 0.028),
          (lin.dofs, lin.nnz, lin.fill_pct))
    mu = lin.mumps
    check(mu["version"] == u"5.6.2" and mu["ordering"] == u"METIS", mu)
    check(mu["neg_pivots"] == 2646 and mu["delayed"] == 0 and
          mu["entries"] == 244308006 and mu["front"] == 3969, mu)
    check(mu["mem_alloc"] == 6501 and mu["mem_used"] == 2272 and
          mu["mem_est"] == 6502, mu)
    check(lin.refine_steps == 0 and lin.refine_before["resid"] == 3.62e-10,
          lin.refine_before)
    check(lin.forward_error() == 1.42e-8 and lin.condition() == 2.11e7 and
          lin.refine_after[7] == 6.74e-16 and lin.refine_after[11] == 37.8,
          lin.refine_after)
    # Fasen: MUMPS-tijden uit de drivers, de rest uit Statistics.
    secs = dict((k, lin.phase_seconds(k)) for k in lin.phase_keys())
    check(secs == {"matrix": 1.176901, "analysis": 0.916,
                   "factor": 15.136, "rhs": 0.010192, "solve": 5.613,
                   "post": 0.631859 + 0.002}, secs)
    check(lin.cpu_total == 20.66, lin.cpu_total)
    levels = [lv for lv, _t in bc.assess_linear(lin)]
    check(levels == ["info", "ok", "info"], levels)
    # De stelsel-regel van CALC_CHAMP na "# Fin commande" telt niet mee.
    check(len(d.linear) == 1 and lin.dofs == 268569, len(d.linear))
    check(u"lineair MECA_STATIQUE MUMPS" in bc.summarize(d), bc.summarize(d))


def test_linear_gcpc():
    p = bc.ConvergenceParser()
    p.feed(MESS_LIN_GCPC)
    p.close()
    lin = p.data.last_linear()
    check(lin.method() == "GCPC" and lin.solver["PRE_COND"] == "LDLT_INC" and
          lin.solver["NMAX_ITER"] == 0, lin.solver)
    check(lin.gcpc_init == 95.0 and lin.gcpc_target == (9.5e-5, 1e-6),
          (lin.gcpc_init, lin.gcpc_target))
    check([n for n, _a, _r in lin.gcpc_iters] == [229, 252, 279],
          lin.gcpc_iters)
    check(lin.gcpc_final == (95.0, 8.098e-5, 8.524e-7) and
          lin.gcpc_converged == 292, (lin.gcpc_final, lin.gcpc_converged))
    check(lin.phase_keys() == ["matrix", "factor", "rhs", "solve", "post"],
          lin.phase_keys())
    check(lin.phase_seconds("solve") == 1.066494 and
          lin.phase_seconds("factor") == 0.154071,
          (lin.phase_seconds("solve"), lin.phase_seconds("factor")))
    check([lv for lv, _t in bc.assess_linear(lin)] == ["ok"],
          bc.assess_linear(lin))


def test_linear_fail():
    p = bc.ConvergenceParser(hints={"FACTOR_57": u"singulier"})
    p.feed(MESS_LIN_FAIL)
    p.close()
    d = p.data
    lin = d.last_linear()
    check(lin.status == "mislukt", lin.status)
    check([m["code"] for m in d.messages] == [u"FACTOR_57"], d.messages)
    levels = [lv for lv, _t in bc.assess_linear(lin)]
    # NPREC-info, foutgrens > RESI_RELA, conditie > 1e12, 10 > 8 pivots
    check(levels == ["info", "fout", "let_op", "let_op"], levels)
    # Een niet-lineaire .mess heeft geen lineaire oplossing.
    q = bc.ConvergenceParser()
    q.feed(MESS_CONTACT)
    q.close()
    check(q.data.linear == [] and q.data.command == "DYNA_NON_LINE",
          q.data.linear)


def test_modes():
    p = bc.ConvergenceParser()
    p.feed(MESS_MODES)
    p.close()
    d = p.data
    check(d.command == u"CALC_MODES", d.command)
    check([nr for nr, _v in d.modes] == [1, 2, 3], d.modes)
    check(abs(d.modes[0][1]["MASS_EFFE_UN_DY"] - 0.613074) < 1e-12,
          d.modes[0])
    text = bc.modes_text(d)
    check(text == u"1: 7.074 Hz, 2: 14.15 Hz, 3: 4.112e+04", text)
    check(u"mode 1: FREQ=" in bc.summarize(d), bc.summarize(d))


def test_auto_steps():
    """METHODE='AUTO' (Automatic time stepping): no "Niveau de
    decoupe" after the time; level 1."""
    p = bc.ConvergenceParser()
    p.feed(u"Instant de calcul:  5.000000000000e-01\n"
           u"Instant de calcul:  1.000000000000e+00 - Niveau de "
           u"découpe: 2\n")
    p.close()
    steps = p.data.steps
    check([(s.instant, s.level) for s in steps] == [(0.5, 1), (1.0, 2)],
          [(s.instant, s.level) for s in steps])


def test_live_dir(tmp):
    """find_live_fort6 herkent de run aan 'F mess' in de .export-kopie."""
    run = os.path.join(tmp, "run_aster_test1")
    if not os.path.isdir(run):
        os.makedirs(run)
    mess = os.path.join(tmp, "werk", "study.mess")
    with io.open(os.path.join(run, "123.export"), "w") as f:
        f.write(u"P ncpus 1\nF comm {0} D 1\nF mess {1} R 6\n".format(
            os.path.join(tmp, "werk", "study.comm"),
            mess.replace(os.sep, "/")))
    with io.open(os.path.join(run, "fort.6"), "w") as f:
        f.write(u"x\n")
    fort6, created = bc.find_live_fort6([tmp], mess, 0.0)
    check(fort6 == os.path.join(run, "fort.6"), fort6)
    other, _c = bc.find_live_fort6([tmp], mess + "x", 0.0)
    check(other is None, other)
    later, _c = bc.find_live_fort6([tmp], mess, created + 100.0)
    check(later is None, later)


def main(argv):
    import shutil
    import tempfile
    test_contact()
    test_pivot()
    test_energy()
    test_python_errors()
    test_failure()
    test_linear_mumps()
    test_linear_gcpc()
    test_linear_fail()
    test_modes()
    test_auto_steps()
    tmp = tempfile.mkdtemp(prefix="convtest_")
    try:
        test_live_dir(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("OK: bridge_convergence (contact, pivot, energie, Python-fouten, "
          "bezwijken, lineair MUMPS/GCPC/fout, modes, live map)")
    for path in argv:
        d = bc.parse_file(path)
        print(u"== {0}\n{1}".format(path, bc.summarize(d)).encode(
            "ascii", "replace").decode("ascii"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
