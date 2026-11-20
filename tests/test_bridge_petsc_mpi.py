# -*- coding: utf-8 -*-
# Copyright (C) 2026 trednuK
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# PETSc and MPI solver options. Defaults keep the previous .export lines
# and do not add keywords to a MUMPS SOLVEUR.
#   python tests/test_bridge_petsc_mpi.py
from __future__ import print_function

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Scripts"))

import bridge_to_aster as a
import bridge_utils as u

_FAILED = []


def check(cond, text):
    print(("OK   " if cond else "FAIL ") + text)
    if not cond:
        _FAILED.append(text)


def _static():
    return {"lin_solver": "MUMPS", "solver_nprec": 8,
            "lin_solver_resi": 1.0e-5, "mumps_memory": "auto",
            "petsc_algo": "FGMRES", "petsc_precond": "LDLT_SP"}


def main():
    u.CONFIG_BRIDGE["mpi_nbcpu"] = 1
    u.CONFIG_BRIDGE["ncpus"] = 1
    u.CONFIG_BRIDGE["matr_distribuee"] = "auto"
    del u._MPI_LOGGED[:]
    del u._DIST_LOGGED[:]
    lines = u.export_parallel_lines()
    check(lines == ("P mpi_nbcpu 1", "P ncpus 1", "P no-mpi true"),
          "default export lines")
    check(u.distributed_matrix() == "", "auto, one rank: no keyword")
    line = a._build_lin_solveur_ref(_static())
    check("METHODE='MUMPS'" in line and "MATR_DISTRIBUEE" not in line
          and "PETSC" not in line, "default static solver is MUMPS")

    pet = _static()
    pet["lin_solver"] = "PETSC"
    line = a._build_lin_solveur_ref(pet)
    check("METHODE='PETSC'" in line and "ALGORITHME" not in line
          and "PRE_COND" not in line and "RESI_RELA=1e-05" in line
          and line.endswith("INFO=2,\n"),
          "PETSc defaults omit ALGORITHME and PRE_COND")
    pet["petsc_algo"] = "GMRES"
    pet["petsc_precond"] = "JACOBI"
    line = a._petsc_solveur(pet)
    check("ALGORITHME='GMRES'" in line and "PRE_COND='JACOBI'" in line,
          "PETSc algorithm and preconditioner")
    pet["petsc_algo"] = "NOPE"
    line = a._petsc_solveur(pet)
    check("ALGORITHME" not in line, "unknown PETSc algorithm falls back")

    nl = a._build_solveur_ref({"lin_solver": "PETSC", "solver_nprec": 8,
                               "lin_solver_resi": 1.0e-5})
    check("METHODE='PETSC'" in nl and "NPREC" not in nl,
          "nonlinear solve uses PETSc")
    ex = a._build_solveur_ref({"lin_solver": "PETSC", "solver_nprec": 8},
                              low_rank=False)
    check("METHODE='MUMPS'" in ex, "explicit dynamics stays MUMPS")

    u.CONFIG_BRIDGE["mpi_nbcpu"] = 4
    lines = u.export_parallel_lines()
    check(lines == ("P mpi_nbcpu 4", "P ncpus 1", "P no-mpi false"),
          "four MPI ranks turn no-mpi off")
    check(u.distributed_matrix() == ", MATR_DISTRIBUEE='OUI'",
          "auto distributes the matrix")
    mumps = a._build_lin_solveur_ref(_static())
    check("MATR_DISTRIBUEE='OUI'" in mumps, "MUMPS line carries it")
    gcpc = _static()
    gcpc["lin_solver"] = "GCPC"
    check("MATR_DISTRIBUEE" not in a._build_lin_solveur_ref(gcpc),
          "GCPC does not get MATR_DISTRIBUEE")
    u.CONFIG_BRIDGE["matr_distribuee"] = "non"
    check(u.distributed_matrix() == "", "non never writes the keyword")

    u.CONFIG_BRIDGE["mpi_nbcpu"] = 1
    u.CONFIG_BRIDGE["matr_distribuee"] = "auto"
    if _FAILED:
        print("{0} FAILED".format(len(_FAILED)))
        return 1
    print("ALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
