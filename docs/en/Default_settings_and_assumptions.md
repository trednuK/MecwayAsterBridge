# Default settings and assumptions

*Nederlandse versie: [Standaardinstellingen_en_aannames.md](../Standaardinstellingen_en_aannames.md)*

This document records, for each setting of the bridge, its default value, what it does
in Code-Aster, why this value was chosen and what demonstrates it. It then lists the
assumptions made by the translation Mecway → Code-Aster. Source of the values:
`CONFIG_BRIDGE` in `Scripts/bridge_utils.py` (as shipped in the repository; the start
screen can change them locally). In case of doubt the code is authoritative.
Code-Aster version: 17.4.

Explanations per topic are in the other documents:
[User guide](UserGuide.md) (start screen),
[Settings contact and nonlinear](Settings_contact_and_nonlinear.md),
[Thermal](Thermal.md), [Modal and buckling](Modal_and_buckling.md), [Acoustics](Acoustics.md),
[Failure](Failure.md) and [Verification](Verification.md).

---

## 1. How to read this document

**Origin of a value** (column *Why*):

| Code | Meaning |
|---|---|
| CA | Code-Aster 17.4 default: what Code-Aster does when the keyword is absent (catalogue `code_aster/Cata` in the installation, §6) |
| Measured | Chosen on the basis of a run; the evidence is given |
| Choice | Design choice of the bridge; the reason is given |
| NOT verified | Not supported by a run or a source |

**Evidence** (column *Evidence*):

- `LS-02`, `NL-01b`, `DY-03a`, ...: verification test from [Verification.md](Verification.md),
  results in `TestFiles/Verificatie/resultaten/resultaten.md`.
- `R-...`: check run made for this review (October 2026): a verification case with one
  setting changed, computed with the same chain (`TestFiles/Verificatie/_run_one.py`
  with a settings file). The outcome is given in the text; §5 gives the overview.
- `KNOWN_BUGS n`: item *n* in [`KNOWN_BUGS.md`](../../KNOWN_BUGS.md) (Dutch).

Code-Aster documents are cited in the text as (EDF R&D, U4.51.03 §3); full details in
§6. Other literature as author (year).

---

## 2. General settings

Pages *General* and *Elements* of the start screen. They apply to all analyses.

| Setting (label) | Default | What it does | Why | Change when | Evidence |
|---|---|---|---|---|---|
| `language` (Taal / Language) | `en` | language of start screen, messages, WARNING/ERROR lines and convergence window | Choice (project language) | Dutch-speaking user: `nl` | - |
| `exe_aster` (Code-Aster launcher) | `%LOCALAPPDATA%\code_aster\v2025\17.4\bin\run_aster.bat` | `run_aster.bat` of the installation | location where the Windows package (MSI) of Code-Aster 17.4 installs; environment variables are expanded | other installation | - |
| `work_dir` (Work folder) | empty (`WorkDir` next to `Scripts/`) | folder for mesh, `.comm`, `.export`, `.mess`, log and results | works without configuration; gitignored in the repository | shorter path needed (259 characters) | - |
| `ncpus` (Number of CPU cores) | 1 | `P ncpus` in the `.export` (threads); always `mpi_nbcpu 1` | Choice: the Windows build is sequential (no MPI, no PETSc, `FERMETUR_10`) | large models: more threads; the effect on run time is NOT measured | - |
| `active_analysis` (Active analysis) | `auto` | follows the Mecway analysis type (S30, L30, D30 (with *Mode superposition* `dyna_modal_3d`), D31, T30/T31, V30, B30) | Choice: no double input | explicit dynamics (`dyna_expl_3d`) is always chosen by hand | - |
| `configuration` (Configuration) | `auto` | which configuration is solved and receives the results; `auto`: the only one, else the only one without suppressed items, else the first (WARNING) | Choice: the API cannot read the active configuration | load cases as configurations | LS-20 |
| `mecway_solve_first` (Mecway solve first) | off | first `mw.solve()`; comparison CSV per node | Choice: faster; Mecway's solve can take long | comparing with Mecway | - |
| `result_route` (Results to Mecway) | `liml` | `liml`: all time steps/modes, also element-node values; `tabel`: node values of the last time via `set_variable()` | Choice: complete and small file | only if the `.liml` route is not possible | KNOWN_BUGS 7 |
| `convergence_monitor` | on | separate window with residuals, solver and messages | Choice | - | - |
| `med_export` | off | also a `.rmed` for ParaView/Salome | Choice: Mecway does not use it, it can reach hundreds of MB | post-processing outside Mecway | - |
| `elem_hex8` (Hex8 solid elements) | `3D` | `MODELISATION='3D'` (fully integrated) | CA standard element; `LINE_QUAD` only works for a model with solid elements only and not explicit, and gives ~3x as many nodes | bending with few hex8 through the thickness: `LINE_QUAD` (or hex20 in Mecway) | LS-02: hex8 `3D` −35.7 / −13.1 / −4.3 / −1.7 / −0.9 % (n = 1…16), `LINE_QUAD` = hex20; KNOWN_BUGS 1 |
| `elem_shell` (Linear shells) | `DKT` | tri3/quad4 → `DKT` (Kirchhoff) | Choice: thin plates, usable linear and nonlinear (`DST` linear only) | large rotations or thick shells: `COQUE_3D` | LS-03-dkt (Navier, −0.003 %), NL-02b (`COQUE_3D`), KNOWN_BUGS 2 |
| `elem_beam` (Beams) | `POU_D_E` | Euler-Bernoulli beam | Mecway's beam is also Euler-Bernoulli | short, thick beams: `POU_D_T` | LS-01 (0.00 %), MO-01, BU-01, DY-02 |

---

## 3. Settings per analysis

### 3.1 Common

| Setting | Default | What it does | Why | Change when | Evidence |
|---|---|---|---|---|---|
| `fields` (Result fields) | per analysis, see below | which fields go to Mecway | Choice: what Mecway itself shows | fewer fields = smaller file | - |
| `time_limit` [s] | 600 (static), 1800 (nonlinear static, thermal), 7200 (dynamic), 900 (modal, buckling) | `P time_limit` in the `.export`; `run_aster` stops afterwards | Choice, NOT measured | long runs; an aborted run gives no complete results | - |
| `memory_limit` [MB] | 2048 (static, modal, buckling), 4096 (others) | `P memory_limit` in the `.export` | Choice, NOT measured | `.mess` or convergence window shows a memory shortage | - |
| `solver_nprec` (MUMPS NPREC) | 8 | `SOLVEUR=_F(METHODE='MUMPS', NPREC=...)`: number of digits that may be lost in the factorisation before the matrix is called singular | 8 = CA (`c_solveur.py`), in all analyses | see §3.2 | R-FREE (§5) |

Result fields per analysis: static `displacements`, `stresses`, `vonmises`,
`reactions`, `beam_forces`, `shell_forces`, `safety_factor`; nonlinear static also
`plastic_strain`, `plastic_strain_eq` and `contact`; dynamic `displacements`,
`stresses`, `vonmises`, `velocities`, `reactions`, `plastic_strain_eq`,
`beam_forces`, `safety_factor`, `contact`; thermal `temperature`, `heat_flux`; modal
and buckling only `displacements` (the shapes, as in Mecway). The extra fields
(`beam_forces`, `shell_forces`, `safety_factor`, `contact`) only do something when
the model has beams, shells, a von Mises failure criterion or contact; they then
cost little computing time. `strain` and `shell_stresses` are off by default: they
make the `.liml` clearly larger (6 and 18 variables per node and per element node);
`shell_forces` is off for dynamics (per time step). See
[`UserGuide.md`](UserGuide.md) §4.1.

Not settable per analysis (fixed in `CONFIG_BRIDGE`, not on the start screen):
`template` (the `.comm` template in `Scripts/`), `solver_command` and for modal/buckling
`type_resu` (`DYNAMIQUE` or `MODE_FLAMB`); also the flags that route an analysis to
its builder: `phenomene` (`ACOUSTIQUE` for acoustics), `vibroacoustic`
(vibroacoustics) and `type_calcul` (`HARM`). They belong to the analysis itself (a
different value makes it a different analysis); the page of an analysis shows the
Code-Aster command and the template at the top.

### 3.2 Static (`lin_static_3d`, `MECA_STATIQUE`)

| Setting | Default | What it does | Why | Change when | Evidence |
|---|---|---|---|---|---|
| `solver_nprec` | 8 | MUMPS singularity check (CA default); the error bound (`RESI_RELA`) checks as well | CA default (until 8 Oct 2026 this was -1, with no recorded reason). A part that can move freely stops with `FACTOR_11`, with -1 with `FACTOR_57` (error bound > `RESI_RELA`); both stop the run | -1 only if you deliberately want the singularity check off | R-FREE: block held in X only, -1 → `FACTOR_57` (error bound 12.6, condition number 5.8e16), 8 → `FACTOR_11` |
| `lin_solver` | `MUMPS` | direct solver (`METHODE='MUMPS'`) | CA default for `MECA_STATIQUE`; robust | little memory, well-conditioned model: `GCPC` (`PRE_COND='LDLT_INC'`) | R-GCPC: LS-02 hex8 n = 8 / 16 with GCPC within tolerance, 232 / 499 iterations for 20,169 / 141,321 equations |
| `lin_solver_resi` | 1e-6 | `RESI_RELA`: MUMPS = bound on the estimated relative error; GCPC = ‖r‖/‖f‖ | CA (`c_solveur.py`, type `LIN`) | rarely; raising it hides a bad model (EDF R&D, U2.08.03 §7.2.1) | - |
| `error_estimator` | on | error estimator: `CALC_ERREUR` `ERME` (residual estimator) on the solid elements, field `errorestimate`/`errorestimaterel` and the global relative error in the log ([Error_estimator.md](Error_estimator.md)) | Choice: costs only element computations (FS-01 n = 16: 1.8 s of 17.6 s) and always shows the mesh quality | off for a very large model or when the extra fields make the `.liml` too large | FS-01, FS-02, FS-03 (sslv153a) |
| `fracture_r_inf`, `fracture_r_sup` | 0, 0 (automatic) | inner and outer radius of the `CALC_G` theta field around the crack front (only with `CRACK_` selections or `#ASTER-XFEM`, [Fracture_mechanics.md](Fracture_mechanics.md)) | CA chooses 2 × and 4 × the element size at the front itself (measured: "R_INF automatiquement choisi"); G and K did not depend on it in the verification (2h/4h, 4h/8h, 8h/16h equal) | R_SUP reaches another crack, a loaded boundary or the model boundary; R_INF = 0 gave −1.3 % on G | BR-01 (h = a/40: K −0.1 %, G −0.4 %) |
| `fracture_smoothing` | `LINEAIRE` | smoothing along the front (`DISCRETISATION`): one value per node | CA default (`calc_g.py`); follows K(s) along the front | fewer than 5 nodes along the front (oscillation, WARNING): `LEGENDRE` with degree 0 | BR-05; measured with 3 nodes: 11739 / 4696 / 25826 J/m² (expected 9391) |
| `fracture_legendre_degree` | 5 | degree of the Legendre polynomial (`LEGENDRE` only) | CA default `DEGRE` 5 | below the number of nodes along the front (WARNING) | measured: degree 5 with 3 nodes −8 to −22 % |
| `adapt_refine` | off | adaptive refinement: after the run, refine the elements with the largest error in Mecway (`mw.refine_x2`) and run again ([Error_estimator.md](Error_estimator.md) §6) | Choice: each loop is an extra run with an OK click and the model is saved refined | on if you want the mesh refined automatically | AD-02, AD-03 |
| `adapt_target_error` | 2 % | target of the loop: global relative error (energy norm) | Choice: sufficient for displacements and average stresses | 1 to 1.5 for a peak stress (AD-02: Kt within 2% at 1.1%) | AD-02 (with 1.5) |
| `adapt_max_loops` | 5 | maximum number of refinements | Choice: 2⁵ per direction at the critical spot | higher for a small model that does not reach the target yet | AD-02 (with 6) |
| `adapt_select` / `adapt_fraction` | `dorfler` / 0.5 | selection of the elements: Dörfler (the largest errors up to half of Σ η²), `fraction` (fraction of the elements) or `factor` (error > factor x mean) | Choice: Dörfler 0.5 is the usual bulk choice (Dörfler 1996) | smaller = fewer elements per loop, more loops | AD-02 |
| `adapt_neighbours` | off | also refine the elements that share a node with the selection | Measured: with a thick plate only extra elements (Kt within 2% at 22 956 instead of 15 810), with a thin plate poor transitions later | on for thin elements | outside the regression ([Error_estimator.md](Error_estimator.md) §6.5) |
| `adapt_max_elements` | 200000 | do not refine if the model would then have more elements (all, also shells and beams) (estimate with the growth of the previous loop) | Choice: solves on an ordinary PC | according to the memory; also `memory_limit` | – |

In `MECA_STATIQUE` the bridge always sets `INFO=2` (solver statistics for the
convergence window, about 15 kB of text; Choice).

### 3.3 Nonlinear static (`nonlin_static_3d`, `STAT_NON_LINE`)

| Setting | Default | What it does | Why | Change when | Evidence |
|---|---|---|---|---|---|
| `substeps_per_interval` | 10 | only without Mecway's *Time step size*: solver steps per interval between the time points of the load tables (`DEFI_LIST_REEL` `NOMBRE`); with a step size Mecway's steps plus the kinks of the load tables | Choice: a finer load path for plasticity and contact; with a step size Mecway's steps as output times (NL-20) | a step where the analysis keeps getting stuck; see the note on `convergence_resi_rela` | R-SUB1: NL-02a with 1 substep gives the same result (to 1e-7) in 3 steps |
| `newton_max_iter` | 20 | `CONVERGENCE/ITER_GLOB_MAXI` | Measured/Choice: CA default is 10; contact often needs more (EDF R&D, U4.51.03) | contact that converges slowly | R-SUB1: step 2 of NL-02a needed 11 iterations |
| `newton_reac_iter` | 1 | `NEWTON/REAC_ITER`: tangent matrix renewed every iteration | CA; recommended (EDF R&D, U2.04.01; U2.04.04 §4.5.2) | do not lower; the start screen accepts at least 1 | R-REAC0: NL-02a with 0 stops in the first step with `DVP_2` (no results) |
| `default_time_end` [s] | 1.0 | end time without a load table | Choice (pseudo time) | - | - |
| `convergence_criterion` | `RELA` | `RELA` = `RESI_GLOB_RELA`; `MAXI` = `RESI_GLOB_MAXI`; `RELA_OF_MAXI` = both with `VERIF='AU_MOINS_UN'`: converged when either one is met (catalogue `c_convergence.py`; EDF R&D, U4.51.03), like CCX: relative with an absolute floor | CA criterion | imposed motion without resistance: `MAXI`; relative residual that stalls: `RELA_OF_MAXI` (see below) | R-RIGID: rigid translation, `RELA` stops in step 1, `MAXI` exact; R-MAXI: NL-01 with `MAXI` 1e-2 N exact up to t = 3; NL-01b: 1e-6 with `RELA_OF_MAXI` 0.05 N exact up to t = 3 (R-ROM: not with 1e-3 N) |
| `convergence_resi_rela` | 1e-5 | `RESI_GLOB_RELA`: largest residual force / (imposed load + reactions) | Measured: the CA default 1e-6 (EDF R&D, U4.51.03) stalls when unloading a plastic solid with `GDEF_LOG` (see below); CCX and Abaqus use 5e-3 | stricter: 1e-6 (CA default), with stagnation combined with `RELA_OF_MAXI` | NL-01 (1e-5) exact up to t = 3; with 1e-6 stop at t = 2.92; R-1E5; R-SUB40 and R-CURVE (see below) |
| `convergence_resi_maxi` [N] | 1e-3 | `RESI_GLOB_MAXI` with `MAXI` and `RELA_OF_MAXI` | Choice: small compared with the forces in the test models | `MAXI`: small compared with the expected forces; `RELA_OF_MAXI`: above the absolute residual at which the residual stalls (column `RESI_GLOB_MAXI` in the `.mess`) | R-RIGID, R-MAXI, NL-01b, R-ROM |
| `contact_algo` | `STANDARD` | `DEFI_CONTACT` `CONTINUE` with `ALGO_CONT='STANDARD'` (Lagrange) or `'PENALISATION'` with Mecway's stiffness | CA; no stiffness needed, no penetration | line contact, contact that is lost, `MECANONLINE9_4` with `LAGS_C`: `PENALISATION` | NL-03a (STANDARD fails), NL-03b/d/f (PENALISATION exact); KNOWN_BUGS 43 |
| `plastic_strain_definition` | `auto` | conversion of Mecway's hardening curve to `TRACTION` (total strain) | Choice, see §4.2 | a curve that starts with (0, σ > 0) but means total strain: `total` | R-CURVE (§4.2) |
| `deformation` | `GROT_GDEP` | `COMPORTEMENT/DEFORMATION`, translated per elset | Measured: Mecway's nonlinear analysis (CCX) is geometrically nonlinear | small deformations and comparison with linear theory: `PETIT` | NL-02a/b; DY-03 (difference 1.4e-4…6.9e-4 with `GREEN_LAGRANGE`) |
| `element_failure` | on | element failure above a plastic strain | Choice | switching off ignores failure limits | [Failure.md](Failure.md) |
| `failure_plastic_strain` | 0 (off) | limit for all plastic materials without their own limit | Choice | - | [Failure.md](Failure.md) |
| `failure_stiffness_factor` | 1e-6 | E of a failed element × factor | Measured: 1e-9 made the matrix singular; bounded 1e-7…0.1 | - | [Failure.md](Failure.md) §7 |
| `crit_stab` | off | `CRIT_STAB` in `STAT_NON_LINE`: after each step the smallest critical value (load factor with small displacements, eigenvalue of K_T with large ones) | Choice: costs an eigenvalue solution per step; only useful for a buckling question | searching for buckling or a limit point: on | NK-01, NK-02a/b, NK-04 ([Modal_and_buckling.md](Modal_and_buckling.md) §5) |
| `imperfection_amplitude` | 0 (none) | largest displacement component of the buckling mode used to pre-deform the mesh | Choice: without input the bridge uses Mecway's geometry | load capacity or behaviour after buckling: L/1000 to L/300 or the value from the design code | NK-03, NK-04 |
| `imperfection_mode` | 1 | which buckling mode (1 = smallest buckling factor) | Choice: the governing shape | two shapes with almost the same factor | NK-03 |
| `imperfection_unit` | `m` | `m`: amplitude in m; `L`: fraction of the largest dimension of the model | Choice | amplitude given as L/x: `L` | NK-03 (`L`) |

**Why 1e-5 and not the Code-Aster default 1e-6.** In the tensile bar of NL-01 (plastic
solids, hence `GDEF_LOG`) the residual force gets stuck: at a small load at about
5e-4 N, when unloading at ~1e-2 N at 12 kN (`RESI_GLOB_RELA` ~1.5…2.3e-6). That is
more than 1e-6 of the reaction: Newton does not reach the criterion, the step is cut,
the load becomes even smaller and the run stops (`MECANONLINE9_7`). Measured with
1e-6: NL-01 stops at t = 2.92; with 40 instead of 10 substeps already at t = 0.013
(R-SUB40); a hardening curve in total strain also stopped at t = 0.013 (R-CURVE).
With 1e-5, `MAXI` 1e-2 N or `RELA_OF_MAXI` (1e-6 and 0.05 N) they run to the end and
are exact (NL-01, NL-01b, R-SUB40-1E5, R-CURVE, R-MAXI). With `PETIT` it does not
occur (R-SUB40-PETIT). Smaller steps therefore do not help here, they make it worse.
Changing from 1e-6 to 1e-5 changed the results of all NL and DY verification cases by
at most 3.75e-6 relative (R-1E5); CCX and Abaqus compute with 5e-3. If you want the
Code-Aster default, set 1e-6 and, on stagnation, `RELA_OF_MAXI` with a
`RESI_GLOB_MAXI` above the absolute residual at which it stalls (column
`RESI_GLOB_MAXI` in the `.mess`; with 1e-3 N NL-01 got stuck, R-ROM). Thermal
(`ther_3d`) stays at 1e-6 (§3.6).

### 3.4 Dynamic implicit (`dyna_impl_3d`, `DYNA_NON_LINE`)

The same settings as §3.3 for Newton, convergence, contact, material and failure
(without `substeps_per_interval`), plus:

| Setting | Default | What it does | Why | Change when | Evidence |
|---|---|---|---|---|---|
| `schema` | `HHT` | `SCHEMA_TEMPS` `HHT` (`MODI_EQUI='OUI'`, CA) or `NEWMARK` (β = 1/4, γ = 1/2) | Choice: HHT damps high frequencies (EDF R&D, U2.06.13) | no numerical damping wanted: `NEWMARK` | DY-01a (HHT), DY-01b/c/d (NEWMARK, order 1.98/1.99) |
| `hht_alpha` | -0.1 | `ALPHA` of HHT | CA (`dyna_non_line.py`); U2.06.13: start at -0.1, -0.3 is an upper limit | high-frequency noise: more negative, down to -0.3 | DY-01a, DY-02, DY-03c; R-ALPHA: DY-01 with -0.3 follows the scheme to 4.7e-8 (period +1.21 %, peak −0.87 %, as predicted) |
| `substeps_per_output` | 1 | solver steps per output interval of Mecway's `<timesteps>` | Choice: solver step = output interval | output intervals that are large compared with the first period | DY-01, DY-02, DY-03c |
| `energy_balance` | off | `ENERGIE=_F()`: energy balance per step in the `.mess` | Choice: for checking only; not with contact (`MECANONLINE5_15`, the bridge then omits it) | checking the energy | R-ENERGY: DY-01a with energy balance, same result, 101 balance lines |
| `time_limit` | 7200 | see §3.1 | | | |

### 3.5 Dynamic explicit (`dyna_expl_3d`, `DYNA_NON_LINE`)

| Setting | Default | What it does | Why | Change when | Evidence |
|---|---|---|---|---|---|
| `schema` | `DIFF_CENT` | central differences, `MASS_DIAG='OUI'`, `FORMULATION='ACCELERATION'` | Choice; lumped mass recommended (EDF R&D, U4.53.01) | damp high frequencies: `TCHAMWA` (`PHI` = 1.05, CA) | DY-03a/b; R-TCHAMWA: DY-03a with TCHAMWA within tolerance |
| `explicit_dt_factor` | 0.5 | step ≤ factor × estimated critical step (smallest edge / dilatational wave speed), divided evenly per output interval | Measured, see below | `DYNAMIQUE_2` (step too large): lower it | DY-03a; R-DT |

**`explicit_dt_factor` relative to Code-Aster's CFL limit.** The factor applies to the
bridge's estimate, not to the limit Code-Aster computes itself. In DY-03a (hex8 cubes of
10 mm, ν = 0) the bridge estimates 1.933e-6 s; Code-Aster reports a maximum step of
9.667e-7 s, half of it (R-DT). The default 0.5 therefore lands on Code-Aster's limit;
because of the even division per output interval the step became 8.33e-7 s (0.86 × the
CFL limit). With 0.7 and above Code-Aster refuses the run (`DYNAMIQUE_2`,
`STOP_CFL='OUI'`); so no silent instability arises. EDF R&D (U2.06.13) recommends
0.5…0.7 × the CFL limit; in this example that is a factor 0.25…0.35. With 0.3 DY-03a
stayed within tolerance (R-DT, 9 instead of 6 steps per output interval). For other
element shapes the ratio is NOT measured.

### 3.6 Thermal (`ther_3d`, `THER_LINEAIRE` / `THER_NON_LINE`)

| Setting | Default | What it does | Why | Change when | Evidence |
|---|---|---|---|---|---|
| `theta` | 0.57 | `SCHEMA_TEMPS` `THETA` (0 explicit, 0.5 Crank-Nicolson, 1 implicit Euler) | CA (`ther_lineaire.py`) | follow Mecway exactly: 0.5 | TH-02 (θ 0.5 / 0.57 / 1.0); KNOWN_BUGS 14 |
| `newton_max_iter`, `convergence_resi_rela`, `newton_reac_iter` | 20, 1e-6, 1 | `THER_NON_LINE` (radiation, convection on shell faces, temperature-dependent material) and the mechanical `STAT_NON_LINE` of the thermal → mechanical chain | as §3.3 | chain not converged (`BRIDGE_ONVOLLEDIG`): first `TC_CUT` and E/SY at high temperature ([Welding.md](Welding.md) §9.8) | TH-01e; WE-07..10 |
| `deformation` | PETIT | only the thermal → mechanical chain (T31 with Thermal stress): `COMPORTEMENT DEFORMATION` | welding: small strains and rotations | large distortion (thin plate that buckles): `GDEF_LOG` (NOT verified in the chain) | WE-07..10 |
| `plastic_strain_definition` | auto | same, strain definition of a Mecway hardening curve | as §3.3 | as §3.3 | - |
| `solver_nprec`, `time_limit`, `memory_limit` | 8, 1800, 4096 | see §3.1 | | | |

### 3.7 Modal (`modal_3d`, `CALC_MODES` `DYNAMIQUE`)

| Setting | Default | What it does | Why | Change when | Evidence |
|---|---|---|---|---|---|
| `modal_modes` | 10 | `NMAX_FREQ` when the Mecway model has no `maxmode` | Choice | - | - |
| `modal_shift_hz` | 0 | 0: `OPTION='PLUS_PETITE'` (without supports in Mecway: automatically `'CENTRE'` around −f_s, §4.8); > 0: `'CENTRE'` around this frequency; < 0: the lowest modes with a shifted, regular K − σM (mechanisms) | CA option `PLUS_PETITE` = the lowest modes, as in Mecway | modes around an excitation frequency; a mechanism (`ALGELINE3_81`): negative | R-SHIFT: MO-01 with 600 Hz gave the 6 modes closest to 600 Hz measured in ω² (eigenvalue), not in Hz; KNOWN_BUGS 48 |
| `modal_norm` | `MASS_GENE` | `NORM_MODE`: φᵀMφ = 1 | Measured: this is how Mecway normalises | comparing shapes: `TRAN`/`TRAN_ROTA` (CA default) | MO-01 (tip 2/√m exact); R-NORM: `TRAN_ROTA` makes the largest component 1 (here the tip rotation) |
| `modal_tolerance` | 1e-6 | `VERI_MODE SEUIL` (the bridge sets `STOP_ERREUR='NON'`) | CA (`calc_modes.py`) | `ALGELINE5_15` with a coarse model: larger | [Modal_and_buckling.md](Modal_and_buckling.md) §2.4 |
| `modal_prestress` | on (`True`) | with loads or thermal strain: first `MECA_STATIQUE`, then the modes with K + K_g (`RIGI_GEOM`; with centrifugal force also `RIGI_ROTA`); off: loads ignored (WARNING) | Mecway does this whenever loads are present (manual §6.3) | you want the unloaded frequencies; an imposed displacement ≠ 0 that should only count as a support | MP-01..07 (Mecway and analytical, [Verification.md](Verification.md) §7); MP-06 (off) |
| `modal_complex` | off (`False`) | on + Rayleigh damping and/or dampers in the model: complex modes, `CALC_MODES` with `MATR_AMOR` (C = αM + βK + C_dampers); per mode the damped frequency f_d (in Mecway's `<mode>`), ζ and f_n in the log and status box; shape = real part (φᵀMφ = 1), `decayrate` = ζ·2πf_n; no stresses per mode. Off: damping is not included (INFO) | Mecway's Frequency analysis ignores Rayleigh damping and does not solve with a Damper (measured headless); complex modes are the Code-Aster route (testcase sdld21c) | you want the damped frequencies and the damping ratio per mode, e.g. to check Rayleigh coefficients or to see the effect of dampers | MC-01..05 ([Verification.md](Verification.md) §7): ζ and f_d ≤ 1e-6 analytical, f_n equal to Mecway |
| `cyclic_base_modes` | 0 (= max(20, 4 × modes per ND)) | only with Mecway's *Cyclic symmetry*: number of modes of the sector with fixed cut faces in the basis of `MODE_ITER_CYCL` (`CALC_MODES NMAX_FREQ`, `DEFI_BASE_MODALE NMAX_MODE`, `NB_MODE`) | Choice: with 20 the modes of the ring and the disc equalled the full model (≤ 0.001%); the basis determines the accuracy of the highest modes per ND | high modes per ND; double it as a check (the frequencies should stay the same) | CY-01..05 ([Verification.md](Verification.md) §7); [Modal_and_buckling.md](Modal_and_buckling.md) §7 |
| `cyclic_full_wheel` | on | only with Mecway's *Cyclic symmetry*: the modes on the **whole wheel** to Mecway (all N sectors with their phase: `DEFI_SQUELETTE CYCLIQUE` + `REST_SOUS_STRUC SQUELETTE`), with the same node and element numbers as Mecway's own cyclic solution (node i of sector j = i + j·n, element e + j·ne); off = only the sector | Mecway: its own solution shows the whole wheel (measured headless) | off for a large model if the result file becomes too large (N times as large) | CY-01..06 ([Verification.md](Verification.md) §7); [Modal_and_buckling.md](Modal_and_buckling.md) §7 |
| `fields` | `["displacements"]` | with `stresses`/`vonmises` (also `strain`, `beam_forces`, `shell_stresses`, `shell_forces`): values per mode (`CALC_CHAMP` on the modes, without `REAC_NODA`); other fields ignored (INFO) | Mecway's default solution of a mode has only the shape; with normalised shapes stresses are only meaningful relative to each other | where a mode gives the largest stress | MO-07 (σ_xx mode 1 +0.43% Euler-Bernoulli, +0.01% Mecway) |
| (fixed) effective mass rotations | about the global axes through the origin | RX/RY/RZ per mode in log and status box (own computation, Γ = φᵀMR); fraction of RᵀMR including supported nodes, as Code-Aster's translations | as Mecway (manual §6.3, checked headless); Code-Aster has no `MASS_EFFE_UN_DRX` | other rotation point: move the origin in Mecway | MO-01, MO-04, MO-06, MO-07 ([Modal_and_buckling.md](Modal_and_buckling.md) §1.5) |
| `solver_nprec`, `time_limit`, `memory_limit` | 8, 900, 2048 | see §3.1 | | | |

### 3.8 Buckling (`buckling_3d`, `CALC_MODES` `MODE_FLAMB`)

| Setting | Default | What it does | Why | Change when | Evidence |
|---|---|---|---|---|---|
| `modal_modes` | 4 | `NMAX_CHAR_CRIT` without `maxmode` | Choice | - | - |
| `modal_norm` | `RIGI_GENE` | φᵀKφ = 1 (the bridge normalises itself: Code-Aster does not support it for buckling, `ALGELINE4_77`) | Measured: this is how Mecway normalises | - | BU-01 (tip exact) |
| `modal_tolerance` | 1e-6 | as §3.7 | CA | | |

**No search centre for buckling.** Buckling always looks for the smallest ∣buckling
factors∣ (`OPTION='PLUS_PETITE'`), as Mecway does; there is no setting for a search
centre. `OPTION='CENTRE'` ignores `CHAR_CRIT` with `TYPE_RESU='MODE_FLAMB'` in
Code-Aster 17.4: with `CHAR_CRIT` 90, 95, 150, 200 and −200, BU-01 always gave the
smallest factors (10.36 / 23.32 / 93.27) and the `.mess` reports "La valeur de décalage
en charge critique est : 0.00000E+00" (R-BSHIFT). `OPTION='BANDE'` does work
(`CHAR_CRIT=(100, 300)` gave 209.853 and 259.086), but the bridge does not offer it.
Mecway's *Shift point* for buckling is a setting of Mecway's own solver, not a search
centre (BucklingPlate with shift 1000 gave factors 7…12); the bridge only reports it in
the log.

### 3.9 Fixed choices without a setting

| What | Value in the bridge | Code-Aster default | Why / evidence |
|---|---|---|---|
| Step cutting (`DEFI_LIST_INST` `ECHEC`) | `EVENEMENT='ERREUR'`, `ACTION='DECOUPE'`, `SUBD_PAS=4`, `SUBD_NIVEAU=6` | `SUBD_PAS=4`, `SUBD_NIVEAU=3` (catalogue) | Choice: more levels (down to 1/4096 of the step); with only `DEFI_LIST_REEL`, `STAT_NON_LINE` does not cut (EDF R&D, U4.51.03; message `SUBDIVISE_3`) |
| `NEWTON/PREDICTION` | not set (except with failure and in the thermal → mechanical chain with filler material, §3.17) | no catalogue default; follows `MATRICE` (NOT verified) | EDF R&D (U2.04.01) recommends `ELASTIQUE` in case of problems |
| Contact `INTEGRATION` | `'NCOTES'` on quadratic slave faces, otherwise `'AUTO'` | `'AUTO'` | Measured: `AUTO` failed the contact patch test on hex20 (1.5…4.6 %), `NCOTES` exact (NL-03c…f) |
| Contact `CONTACT_INIT`, `ADAPTATION`, `VERI_NORM` | not set | `'INTERPENETRE'`, `'CYCLAGE'`, `'OUI'` | CA (`defi_contact.py`) |
| HHT `MODI_EQUI` | not set | `'OUI'` (full HHT, second order) | CA; recommended in EDF R&D (U2.06.13) |
| Explicit `STOP_CFL` | not set (`'NON'` when there is no element with material) | `'OUI'` | CA; without material Code-Aster cannot determine the limit (`DYNAMIQUE_4`) |
| `ARCHIVAGE` | dynamic: the output times; static: not set (every step) | every step | Choice |
| MUMPS `RESI_RELA` nonlinear | not set | -1 (no check of the error bound; type `NL` in `c_solveur.py`) | CA; Newton checks the equilibrium. With `solver_nprec` -1 there is then no singularity check at all (R-NPREC-CONTACT) |
| `MECA_STATIQUE` `INFO` | 2 | 1 | Choice: solver statistics for the convergence window |
| Error estimator: pressure on the free faces | `PRES_REP` 1e-14 Pa (group `BRERRVRIJ`) | a face without a load counts as constrained (no boundary term) | Measured: with 0 the boundary term stayed the same as without those faces; 1e-14 as in test case sslv153a ([Error_estimator.md](Error_estimator.md) §2.2) |
| Error estimator: sign of `FORCE_FACE` | reversed in the load of the estimator | `ERME` computes the boundary term of `FORCE_FACE` as σ·n + g | Measured: block under uniform tension 15% with the sign of the solution, 0.000% reversed; `PRES_REP` 0.000% ([Error_estimator.md](Error_estimator.md) §2.3) |
| `CALC_MODES` `VERI_MODE STOP_ERREUR` | `'NON'` | `'OUI'` | Choice: the Sturm test fails with multiple modes at the limit ([Modal_and_buckling.md](Modal_and_buckling.md) §3.1) |
| Precision of the results | static and modal float64; dynamic and thermal transient float32 | - | Choice (as Mecway's own results); float32: ulp ~3e-5 K at 380 K (TH-02) |
| Weld source: time step warning (`bridge_welding.MAX_JUMP`) | WARNING if v·Δt > 0.5 × (af + ar) | - | Measured (temperature, not an energy loss): at the limit −2.2% next to the source, −2.9% on the weld axis relative to the analytical solution for the same source (relative to the run with v·Δt = (af + ar)/6: −0.8% and −2.7%, as in the comment at `MAX_JUMP`); at 1 × (af + ar) −26% (WE-01/WE-01b, [Welding.md](Welding.md) §4.1) |
| Weld source: mesh warning (`MAX_H`) | WARNING if an element along the path is > 0.8 × the semi-axis in some direction | - | Computed: integration error with 2 Gauss points per direction 0.3% at 0.8·a, 1.8% at 1.0·a ([Welding.md](Welding.md) §4.2) |
| Weld source: automatic source group (`CUTOFF`) | solid elements within 3 × the largest semi-axis of the path | - | q < 2·10⁻¹² of the peak outside it; WE-01/02: energy ≤ 0.06% |
| Weld source: energy check (`POWER_TOL`) | WARNING if the absorbed power deviates > 2% from η·Q (five times) | - | Choice (tolerance of the energy balance); WE-01: +0.09% |
| Metallurgy: TAUX of the dataset | 16MND5: 0.34 s (as mtlp103a) | - | Taken faithfully from the source; set smaller for welding (`TAUX_1=TAUX_3=0.001`): measured, austenitisation lags behind with fast heating and large steps ([Welding.md](Welding.md) §10.5) |
| Metallurgy: warning for lagging austenitisation | WARNING when nodes got above Ac3 + 50 °C but became < 90% austenite | - | Choice; MT-06 with TAUX 0.34 s: weld axis 6% austenite |
| Filler material: quiet material (`bridge_welding.QUIET`) | before birth ρ·c × 10⁻⁴, λ × 10⁻⁸, E (and the hardening) × 10⁻⁴ | - | Measured (prototype, bead born at once after 2 s): λ and ρ·c both × 10⁻³ gave +21% energy at birth (the bead was already warm by conduction), λ × 10⁻⁶ still +3.3%; WE-11: +1.2..1.6%, WE-12: stress before birth 1.8·10⁻⁴ × E·α·ΔT ([Welding.md](Welding.md) §11) |
| Filler material: lead (`LEAD_AF`) | 2 × af | - | Computed: beyond the lead lies erfc(√3·lead/af) of the front part of the source (1 × af: 1.4%, 2 × af: 4·10⁻⁷) |
| Filler material: moment of birth | alive from the first time step after tb (tb = t0: from t0); mechanically stress-free in the state at the start of the birth step | - | Choice (resolution Δt); WE-12: shrinkage stress relative to the birth temperature −0.01% |
| Filler material: heat capacity | `3D_DIAG` (diagonal) in the filler | `3D` (consistent) | Measured: consistent capacity let a quiet node heat up through the mass coupling (WE-13: +138 K before birth) |

### 3.10 Mode superposition (`dyna_modal_3d`, `DYNA_VIBRA` `GENE`)

| Setting | Default | What it does | Why | Change when | Evidence |
|---|---|---|---|---|---|
| `modal_modes` | 10 | `NMAX_FREQ` if the Mecway model has no `maxmode` | Choice, as modal | - | - |
| `steps_per_period` | 50 | `NEWMARK` step = period of the highest mode / 50, a whole number per output interval | Mecway integrates exactly (measured); period error (ω·Δt)²/12 = 0.13% for the highest mode (Hughes, 2000, §9.3) | lower only if the run takes too long | MD-01 (Mecway Δt 0.01 s): u(t) within 1.2e-4 of exact, 1.4e-5 of Mecway |
| `modal_damping` | 0 | extra ζ on all modes in `AMOR_REDUIT` (on top of Rayleigh) | Choice: Mecway only has Rayleigh | a damping ratio from a code | MD-04 (peak ζ = 0.05 −0.00%) |
| `static_correction` | off | `MACRO_ELAS_MULT` as `MODE_CORR`, `CORR_STAT='OUI'` (test case forma12d) | Measured: Mecway applies no static correction (1 mode: 0.9707 × static) | few modes, stresses under a slow load | MD-06a/b (without 0.97069, with 1.00000 × static) |
| `fields` | `displacements`, `velocities`, `stresses`, `vonmises` | `REST_GENE_PHYS` `DEPL`/`VITE` (+ `ACCE` for beam stresses) and `CALC_CHAMP` | as Mecway's D30 output (displacement, velocity, angular velocity, von Mises) | smaller `.liml` | MD-05 (σ_xx 4e-4 against Mecway) |
| `modal_tolerance`, `solver_nprec`, `time_limit`, `memory_limit` | 1e-6, 8, 1800, 2048 | as §3.7 and §3.1 | | | |

### 3.11 Acoustics (`acoustic_modes_3d`, `ACOUSTIQUE` + `CALC_MODES`)

| Setting | Default | What it does | Why | Change when | Evidence |
|---|---|---|---|---|---|
| `modal_modes` | 10 | `NMAX_FREQ` if the Mecway model has no `maxmode` | Choice (as modal) | - | - |
| `modal_shift_hz` | 0 | 0: `OPTION='PLUS_PETITE'`; without a pressure node (hard walls) automatically `'CENTRE'` around −0.1·c_min/(2D) (D = diagonal of the bounding box); > 0: `'CENTRE'` around this frequency | CA; `PLUS_PETITE` stops with `ALGELINE3_81` for hard walls (the 0 Hz mode, seen) | modes around a hum or excitation frequency; a separate part without a pressure node: negative | AK-01, AK-04, AK-05 (hard walls; frequencies equal to Mecway) |
| `modal_tolerance` | 1e-6 | as §3.7 | CA | | |
| `solver_nprec`, `time_limit`, `memory_limit` | 8, 900, 2048 | see §3.1 | | | |
| (fixed) normalisation | pᵀMp = 1, M = ∫NᵀN/c² dV | `aster_results_export` scales by 1/√`MASS_GENE` (`NORM_MODE` does not work for `MODE_ACOU`, seen) | as Mecway (checked headless) | - | AK-01…04: max ∣p∣ equal to Mecway (< 1e-9) |
| (fixed) density | `RHO` from the material, otherwise 1 kg/m³ | `DEFI_MATERIAU FLUIDE` requires `RHO`; the acoustic matrices do not contain it (measured) | - | - | [Acoustics.md](Acoustics.md) §3.2; media with different density: ERROR |
| (fixed) with *Impedance*: complex modes | `RIGI_ACOU`, `MASS_ACOU` and per boundary `AMOR_ACOU` (`CELE_R = 1`); (K + λC + λ²M)P = 0 with C = Σ ρ/Z ∫NNᵀdA in the job (scipy: linearisation, shift-invert ARPACK; dense if 2n ≤ 300, n = free pressure degrees of freedom) | `CALC_MODES` does not accept `MATR_AMOR` for pressure matrices; same problem as Mecway (manual §6.9.2) | - | - | AI-01…10: equal to Mecway ≤ 1e-8, analytical ≤ 0.15% (hex20, up to 935 Hz) |
| (fixed) modes with impedance | the 2·n eigenvalues with the smallest \|λ\|, of those the ones with f ≥ 0 (n = maxmode or `modal_modes`); with `modal_shift_hz` > 0 the n with f ≥ 0 closest to i·2π·f | like Mecway (checked headless); 0 Hz modes always once (Mecway: at random) | - | search frequency > 0: modes around a frequency | AI-01…10 (same list as Mecway, apart from the 0 Hz modes) |
| (fixed) normalisation with impedance | phase such that PᵀMP is real, then PᴴMP = 1, largest Re P positive | Mecway scales arbitrarily (Euclidean, arbitrary phase, measured); this way Z → ∞ is exactly the real mode | - | - | AI-03; P(L)/P(0) equal to Mecway (AI) |
| `modal_tolerance` with impedance | 1e-6 | limit for the residual ‖Q(λ)P‖/((‖K‖+\|λ\|‖C‖+\|λ\|²‖M‖)‖P‖): WARNING above it | Choice (same setting as `VERI_MODE`) | larger after a WARNING with a good mesh | AI: residual ≤ 1e-10 |

### 3.12 Response spectrum (`spectrum_3d`, `COMB_SISM_MODAL`)

| Setting | Default | What it does | Why | Change when | Evidence |
|---|---|---|---|---|---|
| `modal_modes` | 20 | `NMAX_FREQ` if the Mecway model has no `maxmode` | Choice: more than modal, a spectrum needs ~90% effective mass | - | - |
| `spectrum_abscissa` | `period` | *time* column of the gravity table = period [s] or frequency [Hz] | codes give spectra in T (EN 1998-1 §3.2.2.2) | spectrum in Hz | SP-02..06 (period), formula in the `.comm` |
| `spectrum_damping` | 0.05 | ξ of every mode in `AMOR_REDUIT` (plus Mecway's Rayleigh) | the usual damping of design spectra (EN 1998-1: η = 1 at 5%) | spectrum for another damping; 0 with Rayleigh in Mecway | SP-01 (Rayleigh, 0), SP-02..07 |
| `modal_combination` | `CQC` | `COMB_MODE TYPE` | Code-Aster default; also correct for close modes | SRSS or ABS if the code asks for it | SP-02 (SRSS), SP-03 (CQC) exact |
| `direction_combination` | `SRSS` | `COMB_DIRECTION` `QUAD`; `100-30-30` computed by the bridge from `VALE_DIRE`; `100-40-40` = `NEWMARK` | Choice: SRSS is the neutral rule (EN 1998-1 §4.3.3.5.2 (2)); the Code-Aster default is `NEWMARK` | the code asks for 100-30-30 or 100-40-40 | SP-06a/b/c exact |
| `missing_mass` | on | `MODE_STATIQUE PSEUDO_MODE` + `MODE_CORR='OUI'`, `FREQ_COUP` = highest computed frequency | Choice (Code-Aster default `NON`): reactions and stresses are complete, also with few modes | count the modes only (code with ≥ 90% mass) | SP-04 (on), SP-05 (off) exact |
| `fields` | `displacements`, `accelerations`, `stresses`, `vonmises`, `reactions` | `OPTION` `DEPL`, `ACCE_ABSOLU`, `SIGM_ELNO`, `REAC_NODA`; von Mises combined per mode | the maxima a user needs | smaller `.liml` | SP-01, SP-07 |
| `modal_tolerance`, `solver_nprec`, `time_limit`, `memory_limit` | 1e-6, 8, 1800, 2048 | as §3.7 and §3.1 | | | |

### 3.13 Acoustics harmonic (`acoustic_harm_3d`, `ACOUSTIQUE` + `DYNA_VIBRA` `HARM`)

| Setting | Default | What it does | Why | Change when | Evidence |
|---|---|---|---|---|---|
| `harm_freq_start`, `harm_freq_end` | 50, 1000 Hz | range of the frequencies (`DEFI_LIST_REEL` → `LIST_FREQ`) | Choice: a common range for rooms and ducts | the range of interest; the end frequency determines the mesh fineness (≥ 10 linear / 5 quadratic elements per wavelength, otherwise WARNING) | AH-01, AH-01b, AH-02a/b |
| `harm_freq_count` | 20 | number of frequencies from start to end (1 = only the start) | Choice: run time linear in the number | looking for peaks: step smaller than a peak width | - |
| `harm_freq_spacing` | `lin` | `lin` equal steps, `log` equal ratios | Choice | wide range (octaves): `log` | - |
| `harm_freq_list` | `0` | own list (text, commas); `0` = the range | Choice | fixed frequencies (third-octave bands, speeds) | AH-01…07 (list), AH-08 (`#ASTER-OPTIE`) |
| `source_velocity` | 0.001 m/s | normal velocity of the `SOURCE_` faces, into the fluid, phase 0 (`VITE_FACE VNOR`) | Choice: 1 mm/s gives 0.41 Pa (83 dB) in air, a realistic order; everything is linear in v | the actual amplitude; per face: `#ASTER-BRON` | AH-01 (\|p\| = ρcv0), AH-04 |
| `#ASTER-BRON selection = v [, phase]` | - | normal velocity per face selection: without a unit m/s, otherwise mm/s, mm/ms, in/s, ft/s; phase in degrees (default 0) | a pressure unit (Pa, kPa, bar, ...), another unit or text without a number gives an ERROR (until October 2026 `2 Pa` silently became 2 m/s and `abc` 0 m/s); an imposed pressure is Mecway's *fluid pressure* ≠ 0 | - | §4.14 |
| `solver_nprec`, `time_limit`, `memory_limit` | 8, 900, 2048 | see §3.1 | | | |
| (fixed) direction and phase | v > 0 into the fluid; p(t) = Re(P e^{iωt}) | `EXCIT` `COEF_MULT=+1`, `PUIS_PULS=1`, `PHAS_DEG=90` | measured: then p = +ρcv at the source (ahlv100a: −1, v outward) | - | AH-01, AH-04 (−P = ahlv100a) |
| (fixed) SPL | 20·log10(\|P\|/(√2·20 µPa)), pressure node −200 dB | `aster_acoustic_export` | rms value, like a sound level meter; Code-Aster's DB is 3.01 dB higher | - | AH-01, AH-04 |

### 3.14 Vibroacoustics (`vibroacoustic_modes_3d`, `3D_FLUIDE` + `FLUI_STRU` + `CALC_MODES` `BANDE`)

| Setting | Default | What it does | Why | Change when | Evidence |
|---|---|---|---|---|---|
| `modal_modes` | 10 | number of modes if the Mecway model has no `maxmode` | Choice (as modal) | - | - |
| `vibro_freq_min` | 0.1 Hz | lower bound of the band: the first modes above it (`INFO_MODE` searches the upper bound, `CALC_MODES OPTION='BANDE'`) | `U_P_PHI` gives a spurious mode at 0 Hz per φ degree of freedom (measured); `PLUS_PETITE` stops with `ALGELINE3_81`. 0.1 Hz is well above the numerical zero (~1e-5 Hz) and below ordinary structural modes | modes from a frequency on (hum, rotation speed); very soft structure: lower (> 0) | VA-01…05 (all requested modes, in order); VA-05c (100 Hz) |
| `modal_tolerance` | 1e-6 | `VERI_MODE SEUIL` | as §3.7 | `ALGELINE5_15` (seen with hex8 air, error just above 1e-6): 1e-5 | VA-03 |
| `solver_nprec`, `time_limit`, `memory_limit` | 8, 900, 2048 | see §3.1 | | | |
| (fixed) formulation | `FORMULATION='U_P_PHI'` | unknowns u, p, φ; symmetric matrices | CA default (catalogue `affe_modele.py`); `U_P` gave a wrong series / `JEVEUX_26`, `U_PSI` has no `DDL_IMPO PRES` (measured) | - | VA-01…05 |
| (fixed) normalisation | generalised mass 1 (`NORM_MODE MASS_GENE` after filtering) | modes with f < `vibro_freq_min` or mass ≤ 0 are left out (INFO) | a spurious mode with mass < 0 gave `DVP_2` when normalising (measured) | - | VA-01: p/u on the piston analytical within 2e-6 |
| (fixed) fluid | part with *Speed of sound* without Young's modulus, or name `LUCHT_`/`VLOEISTOF_`/`FLUID_` | `3D_FLUIDE`, material `FLUIDE` (`RHO`, `CELE_R`) | Mecway's acoustic material (A30) | - | VA-01…05 |
| (fixed) coupling face | automatic (shared faces with solid or shell elements of the structure); `KOPPEL_`/`COUPLING_` face selections: only those | `FLUI_STRU`, normal out of the fluid (`ORIE_PEAU`) | test cases adlv100a/b | - | VA-01 (automatic), VA-01k (`KOPPEL_`), VA-03/05 (shell) |
| (fixed) p = 0 | `OPEN_` selections (nodes or faces) and *fluid pressure* = 0 | `DDL_IMPO PRES=0, PHI=0` | adlv100a/adlv100p | - | VA-01 |

### 3.15 Harmonic response (`harmonic_3d`, `DYNA_VIBRA` `HARM`)

| Setting | Default | What it does | Why | Change when | Evidence |
|---|---|---|---|---|---|
| `harm_basis` | `GENE` | `GENE`: `CALC_MODES` → `PROJ_BASE` → `DYNA_VIBRA` `BASE_CALCUL='GENE'` → `REST_GENE_PHYS`; `PHYS`: `DYNA_VIBRA` `BASE_CALCUL='PHYS'` on the whole model | Choice: modal is fast and supports modal damping; `PHYS` as a check or with dampers | checking GENE, a model with dampers, or many frequencies above the modes | HR-01a/b (GENE), HR-01c/d, HR-02b, HR-03b (PHYS) |
| `harm_freq_start`, `harm_freq_end` | 1, 100 Hz | frequency range | Choice: a common range for structures | the range of interest; the highest computed mode should be well above it (WARNING if it is below) | HR-01, HR-02, HR-03 |
| `harm_freq_count` | 100 | number of frequencies from start to end | Choice: run time linear in the count (GENE is cheap) | finer or coarser between the peaks | - |
| `harm_freq_spacing` | `lin` | `lin` equal steps, `log` equal ratios | Choice | wide range: `log` | - |
| `harm_freq_list` | `0` | own list (text, commas, ≥ 0 Hz); `0` = the range; no refinement | Choice | fixed frequencies (rotational speeds) | HR-01d, HR-04 (`#ASTER-OPTIE`) |
| `harm_refine_points` | 5 | per mode in the range this many extra frequencies over the half-power bandwidth 2ξf around the peak f√(1−2ξ²) (`DEFI_LIST_FREQ` `RAFFINEMENT` `CRITERE='LARGEUR_3DB'`); only modes with 0 < ξ < 0.5 | CA: `NB_POINTS` default 5 (catalogue `defi_list_freq.py`); without refinement a narrow peak falls between two points | 0 = the range only; more points for a smooth peak | HR-01a (peak −0.00%, peak frequency exact) |
| `modal_damping` | 0 | extra ζ on all modes in `AMOR_REDUIT` (GENE only; PHYS: ERROR) | Choice: Mecway only has Rayleigh | a damping ratio from a code | HR-01a, HR-04 |
| `static_correction` | on | static enrichment of the basis: `MACRO_ELAS_MULT` per load + `DEFI_BASE_MODALE` `RITZ` (`ORTHO`), eigenproblem on that basis (`CALC_MODES` QZ) | CA: `DYNA_LINE` `ENRI_STAT='OUI'` is the default (catalogue `dyna_line.py`, `dyna_line_ops.py`); measured: without enrichment 6.2e-4 × u_st is missing and the error becomes large where the response is small | off to see the modal truncation | HR-02a (with: 6.6e-4 vs Euler-Bernoulli), HR-02c (without: static part 6.22e-4 = 1 − Σ12/λ⁴) |
| `fields` | `displacements`, `accelerations`, `stresses`, `vonmises` | per frequency Re, Im, amplitude, phase; ω²\|U\|; complex `SIGM_NOEU` (solids) | the quantities of a frequency response | smaller `.liml`; `velocities` for ω\|U\| | HR-01a (acceleration), HR-03 (stress) |
| `modal_modes`, `modal_tolerance`, `solver_nprec`, `time_limit`, `memory_limit` | 10, 1e-6, 8, 1800, 2048 | as §3.7 and §3.1 | | | |
| (fixed) time dependence | load F·e^{iφ}·e^{iωt}, u(t) = Re(U e^{iωt}); phase = arg U, negative = lagging | `EXCIT` `COEF_MULT=1`, `PHAS_DEG` = `#ASTER-FASE` | measured (prototype, HR-01): U = F/(k − mω² + iωc) | - | HR-01, HR-04 |
| (fixed) Mecway table of a load | column *time* = frequency [Hz], value = amplitude | `DEFI_FONCTION` `NOM_PARA='FREQ'` as `FONC_MULT` | Choice: Mecway has no frequency table | - | HR-04 |
| (fixed) von Mises | largest value over a period | from the complex nodal stress, exact (`aster_harmonic_export`) | Choice: the von Mises of Re or of \|σ_ij\| is not the maximum in time | - | HR-03a (GENE = PHYS 4e-5) |

### 3.16 Vibroacoustics harmonic (`vibroacoustic_harm_3d`, `3D_FLUIDE` + `FLUI_STRU` + `3D_FLUI_ABSO` + `DYNA_VIBRA` `HARM` `PHYS`)

| Setting | Default | What it does | Why | Change if | Evidence |
|---|---|---|---|---|---|
| `harm_freq_start`, `harm_freq_end` | 20, 500 Hz | range of frequencies (`DEFI_LIST_REEL` → `LIST_FREQ`) | Choice: the range where structures radiate sound; the end frequency determines the mesh density of the fluid (WARNING below 10 linear / 5 quadratic elements per wavelength) | the range of the question | VH-02…06 |
| `harm_freq_count` | 50 | number of frequencies from start to end | Choice: one factorisation per frequency (direct), run time linear in the number | resonance peaks: step smaller than the peak width (§7.4 of [Acoustics.md](Acoustics.md)) | - |
| `harm_freq_spacing` | `lin` | `lin` equal steps, `log` equal ratios | Choice | wide range: `log` | - |
| `harm_freq_list` | `0` | own list (text, commas, > 0 Hz); `0` = the range | Choice | fixed frequencies; fine around a coupled mode (`vibroacoustic_modes_3d`) | VH-01…08 (list), VH-07 (`#ASTER-OPTIE`) |
| `source_velocity` | 0.001 m/s | normal velocity of the `SOURCE_` faces, into the fluid, phase 0 (`VITE_FACE VNOR`, `EXCIT COEF_MULT=−1`) | Choice, as §3.13; measured: with `COEF_MULT=+1` `VITE_FACE` in `U_P_PHI` gives p = −ρcv (ahlv100b: `VNOR` outward) | the actual amplitude; per face: `#ASTER-BRON` | VH-01b (ahlv100b ≤ 2.3e-7), VH-07 |
| `incident_pressure` | 1 Pa | amplitude of the plane wave that enters the fluid through the `INCIDENT_` faces (`ONDE_FLUI PRES` = 2 × the value) | Choice: 1 Pa (91 dB) as a unit, everything is linear; measured: `ONDE_FLUI` with `PRES` gives an incoming wave `PRES`/2 and lets reflected waves pass | the actual amplitude; per face: `#ASTER-BRON selection = p Pa [, phase]` | VH-01 (ahlv101a ≤ 1.3e-7), VH-05, VH-05b, VH-08 |
| `fields` | `displacements`, `accelerations`, `stresses`, `vonmises` | as §3.15 for the structure; the pressure (`pressure`, `pressurei`, `pressuremag`, `pressurephase`, `spl`) is always included | the quantities of a frequency response | smaller `.liml` | VH-02 (stress on the piston) |
| `solver_nprec`, `time_limit`, `memory_limit` | 8, 1800, 2048 | see §3.1 | | | |
| (fixed) computation | direct: `DYNA_VIBRA` `BASE_CALCUL='PHYS'` with `MATR_IMPE_PHI` | no modal basis | `U_P_PHI` has spurious modes at 0 Hz (§3.14) and the absorption is not proportional; ahlv101a/ahlv100b compute it this way | - | VH-01…08 |
| (fixed) absorbing boundary | `ABSORBING_`: `3D_FLUI_ABSO` with ρc of the fluid; Mecway *impedance* (real): own material `CELE_R = Z/ρ` (`IMPE_MECA`) | | measured: Z = ρ·c_face | - | VH-01/02 (ρc), VH-03 (Z = 2ρc ≤ 1.2e-4) |
| (fixed) damping of the structure | Mecway *Rayleigh damping*: C = α·M_s + β·K_s with the matrices of the structure groups only; dampers `AMOR_MECA` (`AMOR_FLUI='NON'`); `DYNA_VIBRA AMOR_FLUI='NON'` | | Choice: the fluid is damped by the boundaries, not by Rayleigh; `AMOR_FLUI='NON'` as in `DYNA_LINE` | - | VH-04 (α), VH-04b (β), VH-04c (damper) |
| (fixed) sources | `EXCIT` `PUIS_PULS=1`, `PHAS_DEG` = 90 + phase (iω × the vector); loads on the structure as §3.15 | | ahlv101a, ahlv100b | - | VH-01…08 |
| (fixed) SPL, microphones, probes | as §3.13 (SPL on the effective value) and §3.15 (probes) | `aster_harmonic_export` with `pressure=True` | | - | VH-01, VH-02 |

### 3.17 Fixed values in the modules (without a setting)

Supplement to §3.9: values fixed in the code that determine the result or the
messages. The source is the code (module in brackets); where *Why* is empty it is a
Choice of the bridge that has not been measured separately.

| Topic | Value in the bridge | Effect | Why / evidence |
|---|---|---|---|
| Older `bridge_utils.py` without a key | the modules fall back to `harm_freq_start`/`_end`/`_count` = 0 / 0 / 1 (acoustics and harmonic: ERROR about the range), `fields` = only `displacements` (harmonic, mode superposition, spectrum, vibroacoustics), `error_estimator` off (`bridge_adapt`) | only when the key is missing from `CONFIG_BRIDGE` | put the key back (the start screen then shows it again) |
| Adaptive: growth in advance (`bridge_adapt._GROWTH`) | 40 new elements per refined element in the first loop, then the measured growth of the previous loop | estimate for `adapt_max_elements` (counts all elements of the model, also shells and beams) | measured (headless Mecway 33): 19 per element with hex8, 38 to 70 with hex20 |
| Adaptive: bad element (`BAD_ELEMENT`) | WARNING with a scaled Jacobian < 0.1 (hex only) | message, no action | coarse plate model 0.71, bad transitions 0.002 to 0.02 |
| Adaptive: stopping | target reached (`rel ≤ adapt_target_error`), the global error no longer decreases (no tolerance; WARNING), or `adapt_max_loops` refinements (5 = 5 refinements, 6 runs) | end of the loop | - |
| Adaptive: choice with equal error | lower element number first; `fraction`: ⌈f·n⌉ elements (at least 1); `factor`: η > factor × mean (strict) | which elements are refined | - |
| `#ASTER-LASBRON` without a key (`bridge_welding`) | `eta` 1; `depth` (0, 0, −1) (the heat goes into −Z); `t0` 0 s; `ff` = 2·af/(af+ar), `fr` = 2·ar/(af+ar) (WARNING if ff + fr ≠ 2); path without `length`: v × (`t1` or the end time − `t0`); `group`: the `LASNAAD_` selections, otherwise automatic (`CUTOFF`); `birth` off; `lead` 2 × af | power, direction and position of the source | Goldak (double ellipsoid, continuous at the interface with this ff/fr); [Welding.md](Welding.md) |
| Thermal → mechanical chain: line search (`bridge_thermomech`) | `RECH_LINEAIRE ITER_LINE_MAXI=5` when there is plasticity | convergence | measured: WE-10b (hex20, `LINE_QUAD`) diverged without it; with it 9 to 10 iterations per step |
| Chain with filler material: `NEWTON PREDICTION` | `'TANGENTE'`; in the step right after a birth `'ELASTIQUE'` (stress and internal variables of the new elements set to 0) | convergence at the birth | Choice (as after failure) |
| Chain with `LINE_QUAD` | temperature to the quadratic mesh with `PROJ_CHAMP METHODE='COLLOCATION'` (midside nodes linear between the corner nodes) | thermal strain at the midside nodes | as in the linear element |
| Chain: bilinear material | ET from Mecway's tangent modulus via H = E·ET/(E − ET) with E at the first table temperature, then ET(T) = E(T)·H/(E(T) + H); without *Thermal expansion* α = 0 (WARNING) | hardening and thermal strain with temperature-dependent E | - |
| Metallurgy: dataset 16MND5 (`bridge_metallurgy.DATASETS`) | AR3 830, MS0 415, AC1 724, AC3 846 °C; ALPHA −0.0249; TAUX_1 = TAUX_3 = 0.34 s; `TEMP_MS` (0.38; −30.791; 11.698; −1.0); hardness F/P/B/M/A 184/184/309/450/100 HV; grain 11 (`DREF` 11) | phases and hardness | test case mtlp103a, copied as is |
| Metallurgy: dataset HSNV101A | AR3 830, MS0 200, AC1 724, AC3 846 °C; ALPHA −0.03; TAUX 0.34 s; grain 10; with `mechanica=ja` ALPHA_F 15·10⁻⁶, ALPHA_A 23.5·10⁻⁶ /K, DEPS 2.52·10⁻³, REF `CHAUD` and the yield stresses of the test case | fictitious steel of test case hsnv101a | MT-01 |
| Metallurgy: when not given | own `trc=` without `korrel`: grain 0; `REF` not given and no dataset: `CHAUD` if `begin` > 50 % austenite, otherwise `FROID`; slope per phase without `ET_`/`H_`, dataset or Mecway slope: 0 (perfectly plastic) | phases, transformation strain, hardening | - |
| Metallurgy: messages | HAZ = nodes with > 1 % austenite, full = > 99 %; WARNING if there is still > 1 % austenite at the last time | report only | - |
| Fracture mechanics: shape of the front (`bridge_fracture.front_shape`) | straight or circle if all points lie within 1 % of the largest dimension of the front; `FORM_FISS='CERCLE'` only if most lip nodes lie inside the circle (< 0.999 R) | curvature correction of K | forma07a (see §4.12) |
| Fracture mechanics and XFEM: check | WARNING if K_I of `CALC_G` and `POST_K1_K2_K3` differ by more than 5 % at the inner points of the front (relative to the largest \|K_I\|: `CALC_G` for a meshed crack, `POST_K1_K2_K3` for XFEM) | message | - |
| XFEM: mesh | WARNING if the elements at the front are larger than the crack size / 10 (smallest semi-axis or radius) | message | BR-08 ([Fracture_mechanics.md](Fracture_mechanics.md) §7.4) |
| XFEM: `POST_K1_K2_K3` | `ABSC_CURV_MAXI` = R_SUP when `fracture_r_sup` (or `rsup=`) is given | range along the lips | test case forma07b |
| Harmonic: table of a load | linear between the points (Hz), constant outside the table (`PROL_GAUCHE`/`PROL_DROITE='CONSTANT'`) | amplitude outside the table range | - |
| Harmonic: phase | `#ASTER-FASE` in degrees; without it: 0 | phase of the load | - |
| Harmonic (GENE): pseudo-modes | the vectors of the static enrichment get the same damping ξ = ½(α/ω + β·ω) + ζ at their frequency | damping of the quasi-static part | - |
| Harmonic: overcritical damping | no check for ξ ≥ 1 (solvable in the frequency domain); mode superposition and spectrum stop with an ERROR | - | - |
| Harmonic: quantities per node | `displmag` = √(\|Ux\|² + \|Uy\|² + \|Uz\|²): an upper bound of max \|u(t)\| (equal when the components are in phase); a probe or microphone with several nodes: amplitude = RMS of \|U\| over the nodes, phase = arg of the mean | interpretation | - |
| Harmonic: precision | float32 in the `.liml` (as dynamics, §3.9) | rounding ≤ 6·10⁻⁸ relative (2⁻²⁴) | - |
| Mode superposition | `steps_per_period` at least 4 (also on the start screen); `NEWMARK` with the Code-Aster default β = 1/4, γ = 1/2 (average acceleration); ERROR with ξ ≥ 1 or a mode with f ≤ 0; output times must be multiples of Mecway's time step (tolerance 10⁻⁶ × step), otherwise ERROR | - | MD-01 |
| Spectrum: input | ordinates without sign (\|S_a\|), a number = a flat spectrum; several gravities summed per direction on all abscissae together (linear, constant outside the table) | spectrum value | as Mecway adds a table and a number |
| Spectrum: missing mass in the bridge's own reaction and von Mises | spectrum value at `FREQ_COUP` with the damping of the highest computed mode | reaction and von Mises of the pseudo-mode | - |
| Spectrum: output | `REAC_NODA` without the springs of *elastic support* (`BRES*`, as in static: the spring force is the reaction); stresses on solid elements only; WARNING if the effective mass is < 90 % without missing mass | - | - |
| Complex modes: search frequency (`bridge_modal_damping`) | `modal_shift_hz` ≠ 0, also negative: `OPTION='CENTRE'` around that frequency (unlike real modes, §3.7) | which modes are found | NOT verified with a negative value |
| Acoustics: search frequency without a pressure node | −0.1·c_min/(2D) (§3.11); if D = 0: −1 Hz | solvable with hard walls | - |
| Acoustics: complex modes (`aster_acoustic_complex`) | solved dense (`scipy.linalg.eig`) if 2n ≤ 300 (n = free pressure degrees of freedom), otherwise shift-invert ARPACK; 2·maxmode + 8 candidates, doubled up to 3 times | - | AI-01…10 |
| Acoustics: microphone with several nodes | amplitude = RMS of \|P\| over the nodes, phase = arg of the mean | CSV and log | - |
| Acoustics: equal density | relative tolerance 10⁻⁶; above it different media (ERROR) | - | - |
| Acoustics: source on a selection | `#ASTER-BRON` on a `SOURCE_` selection replaces the default velocity | - | - |
| Fluid outside a vibroacoustic analysis | computed as a solid with E = 210 GPa (WARNING; Mecway uses E = 0) | - | - |
| Vibroacoustic modes: band | `INFO_MODE` from `vibro_freq_min`: upper bound max(10·f_min, 1 Hz), × 4 until there are enough modes (up to 10⁷ Hz), then halved geometrically twice; `CALC_MODES` `BANDE` with `COEF_DIM_ESPACE=4` | which band is computed | VA-01…05 |
| Cyclic: node pairs (`bridge_cyclic`) | master and slave node paired within 10⁻⁵ × the largest coordinate, otherwise ERROR | - | CY-01..06 |
| Cyclic: whole wheel (`aster_cyclic`) | nodes matched within 10⁻⁶ × the largest coordinate; the frequencies on the skeleton must equal those of the sector within 10⁻⁹ (relative), otherwise only the sector goes to Mecway | - | CY-01..06 |
| Cyclic: search frequency and normalisation | negative: ignored (INFO; the sector with fixed cut faces has no rigid-body modes); `modal_norm` other than `MASS_GENE` applies only to the sector basis (INFO) | - | - |

---

## 4. Assumptions of the translation

Status: **verified** (by test or source), **source** (documentation only), **NOT
verified**, or **deviation** (deliberately different from Mecway).

### 4.1 Units and input

| Assumption | What the bridge does | Status |
|---|---|---|
| Everything in SI | every Mecway value with a unit (`"210 GPa"`, `"10000 mm⁴"`) is converted (`parse_and_convert`); an unknown unit is returned unchanged with a WARNING | verified: all verification models use units such as MPa and mm (Verification, all groups) |
| Formulas in t | sampled to a time table (as Mecway does for CCX) | source: Mecway manual (Mecway, 2026) chapter 9; KNOWN_BUGS 104 |
| Formulas in x, y, z (mechanical) | `FORMULE` of X, Y, Z (and `INST`) in `AFFE_CHAR_MECA_F` for pressure, traction, force, line pressure and prescribed displacement/rotation; x, y, z in the position unit, initial position | verified: LS-40..44, NL-40; pressure and traction equal to Mecway 34; deviation: Mecway 34 does not apply force, line pressure and displacement/rotation with x, y, z (KNOWN_BUGS 104) |
| Time-dependent load in linear static | value at the end time (also t in a formula in x, y, z) | deviation: Mecway internal ignores t, CCX takes f(0) (KNOWN_BUGS 104) |
| Nonlinear static: Mecway's `stepsize` | solver steps dt, 2 dt, ... up to the period plus the kinks of the load tables; *automatic time stepping* not reproduced | output times = Mecway's steps (NL-20), plus a time at a kink between two steps |

### 4.2 Material

| Assumption | What the bridge does | Status |
|---|---|---|
| Bilinear plasticity: Mecway's *tangent modulus* = plastic modulus H | `ECRO_LINE D_SIGM_EPSI` = E·H/(E+H) (slope in total strain) | verified: NL-01 exact; Mecway/CCX headless 434.0 MPa (reference 433.5) |
| Hardening curve: the strain is the **total** strain | `auto`: first point (0, 0) or first strain > 0 → total strain (as Mecway; (0, 0) is dropped; if the first point is not on the elastic line, a WARNING about the slope follows); first point (0, σ > 0) → plastic strain, with a WARNING that Mecway reads the same curve as total strain | verified in this review (Mecway/CCX headless, bar of NL-01, R-CURVE): curve (0, 0), (σy/E, σy), (0.1, …) gave 430.6 MPa and p = 0.00792 at t = 2 (reference 433.5 MPa / 0.00788), hence total strain. A curve starting with (0, σy) gave a non-physical result in Mecway (13.5 MPa at 0.1 % strain); the bridge reads it as plastic strain. Bridge with `auto`: curve with or without (0, 0) and curve (0, 355 MPa) as plastic strain all three exact up to t = 3 (R-CURVE) |
| Plasticity | von Mises: `VMIS_ISOT_TRAC`/`_LINE`, `VMIS_CINE_LINE`; Ramberg-Osgood sampled | verified (NL-01, official tests ssnp15a, hsnv100g); KNOWN_BUGS 6, 34 |
| Plasticity on beams | computed elastically (WARNING) | deviation: Code-Aster only in multifibre beams (`POUTRE0_61`) |
| Thermal strain | nodal field `TEMP` (`AFFE_VARC`), interpolated inside the element; *Temperature* per selection and *Node temperature* (`temperature3`, also after *Transfer temperatures from solution*) per node; nodes without a temperature at the *Thermal stress* reference; nodes added by the bridge (`LINE_QUAD`, `COQUE_3D` centre node) get the interpolated temperature | verified: TH-03 and LS-08a/c exact, LS-08b/d (linear through the thickness) exact and equal to Mecway 34, which also interpolates (the manual mentions the element average, KNOWN_BUGS 17); L30/D31: `EVOL_THER` from the reference, time table followed (NL-70..75, DY-70..72); D30 ignores temperatures like Mecway |

### 4.3 Constraints and loads

| Assumption | What the bridge does | Status |
|---|---|---|
| Pinned support = mean displacement zero | `LIAISON_DDL` Σ wᵢuᵢ = 0 per direction (weight per node or per face area) | source: Mecway (2026) §9.3; NOT in a verification test (LS-03 uses `displacement`) |
| Pressure positive towards the element | `PRES_REP` with `PRES` > 0 = compressive | source: Mecway (2026) §9.14; verified: LS-03, LS-04, LS-05 |
| Uniform pressure follows large displacements | `TYPE_CHARGE='SUIV'` on solids and `COQUE_3D`; fixed on DKT (WARNING, `CALCUL_42`) | source: Mecway (2026) §9.14; Code-Aster test ssnv122a (Verification, official tests) |
| Overlapping constraints | partly resolved (`SANS_GROUP_*`), otherwise reported | deviation: Mecway reduces them itself (KNOWN_BUGS 8) |
| Springs and dampers along their own axis | `DISCRET` with `REPERE='LOCAL'` | source: Mecway (2026) §7.7 ("stiffness only in the direction of its length"); verified: LS-06 exact; a comparison with a Mecway solution is missing (KNOWN_BUGS 47) |
| Compression only | `LIAISON_UNIL` (hard) | KNOWN_BUGS 22 |
| Rayleigh damping | only on the whole model (`AMOR_ALPHA`/`AMOR_BETA` per material) | KNOWN_BUGS 27 |

### 4.4 Elements

| Assumption | What the bridge does | Status |
|---|---|---|
| Hex8 | `3D` without incompatible modes; Mecway does use them (Mecway, 2026, §7.3) | deviation, measured: LS-02 (too stiff with few elements); KNOWN_BUGS 1 |
| `LINE_QUAD` | Code-Aster turns hex8 → hex20; results on the corner nodes only; nodal forces stay on the corner nodes | verified: LS-02-lq = hex20; point loads give local deformation (KNOWN_BUGS 1) |
| Shells | DKT ~0.7 % different from Mecway, `COQUE_3D` via QUAD9/TRIA7 | measured (KNOWN_BUGS 2); LS-03, LS-05 |
| Thermal shells | `PLAN` (depth 1) with factor f = t / t_ref on λ, ρc and the loads | verified: TH-01e (6e-7); KNOWN_BUGS 15 |
| Trusses | `BARRE`, geometrically linear (also with `GROT_GDEP`) | measured (KNOWN_BUGS 40) |
| Explicit with DKT shells | no `INER_ROTA` in `AFFE_CARA_ELEM` | measured in this review (R-STRIP): cantilever strip DKT, explicit and implicit equal, period +0.6 % / +0.3 %, peak 1.957 × static (expected ~1.966) |

### 4.5 Kinematics (`deformation`)

| Assumption | What the bridge does | Status |
|---|---|---|
| Mecway's nonlinear analysis is geometrically nonlinear | default `GROT_GDEP` | source: Mecway (2026) §6.2.1 (CCX only); measured: a plastic bar was 14 % too stiff with `PETIT`, +1 % vs Mecway with large displacements (earlier run, model not in the repository) |
| Form per element | elastic solid `GREEN_LAGRANGE` (or `GDEF_LOG`), plastic solid `GDEF_LOG` (or `SIMO_MIEHE`, not with `VMIS_CINE_LINE`), DKT/DST `GREEN_LAGRANGE` (gave the same result as `PETIT`; with `VMIS_CINE_LINE` `PETIT`), `COQUE_3D` `GROT_GDEP`, beams `PETIT`, cables `GROT_GDEP`, discrete elements `PETIT` | measured with runs on a mixed model (`bridge_to_aster._deformation_for`); NL-02a (solid) and NL-02b (`COQUE_3D`) exact; large displacements of DKT and beams: NOT possible (KNOWN_BUGS 11); discrete elements with large displacements: NOT verified |
| Dynamics follows the static choice | `GROT_GDEP` also in `dyna_*` | Choice, NOT verified against Mecway; DY-03: difference with linear theory 1.4e-4…6.9e-4 (physical) |
| Imposed rotations and rigid couplings | stay small rotations; WARNING above ~6° | KNOWN_BUGS 11 |

### 4.6 Contact

| Assumption | What the bridge does | Status |
|---|---|---|
| Mecway contact is penalty with a normal stiffness per area | default Lagrange (`STANDARD`, no penetration); `PENALISATION` uses Mecway's stiffness as `COEF_PENA_CONT` | deviation with `STANDARD` (KNOWN_BUGS 43); `PENALISATION` verified: penetration p/kn exact (NL-03d/f), line contact exact (NL-03b) |
| Line contact with `STANDARD` | fails on hex20 (`MECANONLINE9_4`, `LAGS_C`) | NL-03a; with `solver_nprec` -1 it runs through, but contact force −1.6 % and tip +2.8 % (R-NPREC-CONTACT): use `PENALISATION` |
| Fixed slave nodes | excluded with `SANS_GROUP_NO` | source: EDF R&D (U4.44.11, U2.04.04 §2.3.4) |
| Zones sharing slave nodes | merged, largest friction coefficient | KNOWN_BUGS 10 |
| Bonded contact | rigid (`LIAISON_MAIL`); the stiffness of `bondedelastic` is dropped | KNOWN_BUGS 21 |

### 4.7 Dynamics

| Assumption | What the bridge does | Status |
|---|---|---|
| Initial acceleration | Code-Aster computes a₀ = M⁻¹F(0) | measured (Verification, DY) |
| HHT, first step | Code-Aster uses F₀ = 0 in the term −αF₀ | measured: DY-01a peak −0.44 % (Verification, DY) |
| Imposed motion explicit | converted to the acceleration imposed by the scheme (`FORMULATION='ACCELERATION'`) | verified: DY-03b exact; frictionless (`FACE_IMPO` DY-20a, `LIAISON_OBLIQUE` DY-20c) and constraint equation with constant ≠ 0 (DY-20b, C in the first solver step) converted too; TCHAMWA with a variable step: KNOWN_BUGS 41 |
| Mass | implicit consistent, explicit lumped (`MASS_DIAG='OUI'`) | DY-02, DY-03 |
| Critical step | estimate smallest edge / c; Code-Aster checks itself | measured (§3.5, R-DT) |
| Mode superposition (D30) | Rayleigh as modal ξ_i = α/(2ω_i) + β·ω_i/2; no prestress from the loads; no static correction (default); a load without a table = step load from t = 0 | verified against headless Mecway and analytically: MD-01..07 ([Mode_superposition.md](Mode_superposition.md)) |
| D30 without mode superposition | `dyna_impl_3d`; output times = Mecway's time step × *keepeverynthtimestep* | verified: MD-07 (NEWMARK + PETIT equal to Mecway) |
| Harmonic response (`harmonic_3d`) | Rayleigh as modal ξ_i (GENE) or C = αM + βK (PHYS); the loads are the amplitude (no prestress); static enrichment of the basis (default); imposed motion ≠ 0 not | verified: HR-01..04 analytically (single degree of freedom, Euler-Bernoulli cantilever) and GENE = PHYS ([Mode_superposition.md](Mode_superposition.md) §7); Mecway has no harmonic analysis; Mecway GUI NOT verified |
| Response spectrum | gravity with a table = spectrum per direction (not a load, linear in T, constant outside the table); `MONO_APPUI`; modes without prestress; maxima without sign as one step; von Mises combined per mode; total reaction summed per mode and then combined | verified: SP-01 (sdld25a) and SP-02..07 analytically ([Response_spectrum.md](Response_spectrum.md)); Mecway GUI NOT verified |

### 4.8 Modal and buckling

| Assumption | What the bridge does | Status |
|---|---|---|
| Normalisation as in Mecway | vibration shapes φᵀMφ = 1, buckling shapes φᵀKφ = 1 | verified: MO-01, BU-01, Mecway samples ([Verification.md](Verification.md)) |
| Buckling factor = `CHAR_CRIT` | negative factors too (buckling under the reversed load) | verified: BucklingBeam equal to Mecway; deviation for negative factors (KNOWN_BUGS 46) |
| Modal with loads | stress stiffening like Mecway (K + K_g, centrifugal also spin softening `RIGI_ROTA`) | verified: MP-01..07; deviations beam `RIGI_ROTA` and shells with centrifugal force (KNOWN_BUGS 49) |
| Free-free | `CENTRE` around −f_s with (2πf_s)² = 1e-8 · max(diag K / diag M) | verified: MO-04, VibratingFreePlate |
| Complex modes (`modal_complex`) | C = αM + βK (the whole model, including point masses and springs; K = the stiffness of the eigenvalue problem, with prestress K + K_g) + `AMOR_MECA` of the dampers; without a search frequency `PLUS_PETITE` with `TRI_DIAG` (`SORENSEN` is not possible, `ALGELINE2_71`), otherwise `CENTRE` with `SORENSEN`; Code-Aster's FREQ = damped frequency, `AMOR_REDUIT` = ζ; overdamped and rigid body modes are not included | verified: MC-01..05 (analytical and Mecway); `TRI_DIAG` and `QZ` gave the same values (1e-9, measured) |
| Cyclic symmetry (Mecway *Cyclic symmetry*, V30) | `MODE_ITER_CYCL` on the sector (Craig-Bampton: sector modes with fixed cut faces + static modes of the cut faces; testcases sdlv134a, sdls04a); per ND 0 .. N/2 `maxmode` modes, of a pair the first member, in Mecway's order, on the whole wheel (`cyclic_full_wheel`, Mecway's numbering) or the sector; X or Y axis: the model is rotated to the Z axis beforehand (MODE_ITER_CYCL requires Z) and back; prestress with the relations of ND 0 (u_slave = R u_master); nodes on the axis as interface `AXE`; fully fixed nodes on a cut face are left out of the interfaces | verified: CY-01..06 (full model ≤ 0.0012%, Mecway ≤ 0.03%, Blevins/Leissa ≤ 1.2%; shapes on the whole wheel 1 − MAC ≤ 5.2e-7 against the full model); limits KNOWN_BUGS 61 |
| Meaning of `CRIT_STAB` | small displacements: critical load factor of the current load; large displacements (one elset is enough): −(smallest eigenvalue of K_T), buckling at 0; the bridge estimates the zero linearly from the last two steps | measured ("produits B*X" in the `.mess`): NK-01, NK-02a/b, NK-04; SIMO_MIEHE NOT verified (KNOWN_BUGS 53) |
| Imperfection | linear buckling mode under the loads at the end time, `NORM_MODE` `TRAN`, `MODI_MAILLAGE DEFORME`; mesh restored after the analysis; displacements relative to the imperfect shape | verified: NK-03 (amplification ≤ 0.5 %), NK-04 |

### 4.9 Thermal

| Assumption | What the bridge does | Status |
|---|---|---|
| Time scheme | θ method with θ-weighted load; Mecway: Crank-Nicolson with the load at the end of the step | deviation: θ = 0.5 follows Mecway for a constant load (KNOWN_BUGS 14, TH-02) |
| Steady state with a time table | t = 1 s | KNOWN_BUGS 14 |
| Formula as a value (x, y, z, t) | `FORMULE` in the Gauss points, θ-weighted; steady state t = 1 s | verified: WE-06 equal to Mecway (7e-12 K), WE-03 energy equal to Mecway; temperature difference with Mecway due to the time scheme (KNOWN_BUGS 14) |
| Temperature-dependent material | `THER_NL`, tables extended as constants, ρc refined every 10 degrees | verified: WE-04a exact (Kirchhoff), WE-04b energy 0.01%, Mecway ≤ 0.15% |
| Weld source (`#ASTER-LASBRON`) | Goldak double ellipsoid, solid elements only | verified: WE-01 (Rosenthal ≤ 1%), WE-02 (≤ 1.2%), energy ≤ 0.06% |
| Filler material (`birth=`) | "quiet element": quiet until birth (arc length along the path), then the normal material; mechanically stress-free at birth; several sources (also Mecway formula/table sources) in one load | verified: WE-11/11b energy ≤ 0.8%, WE-12/12b shrinkage stress ≤ 0.04%; WE-13 qualitative; KNOWN_BUGS 71 |
| Thermal → mechanical chain | on with a Thermal stress in a T31 model; `STAT_NON_LINE` at the thermal times, `AFFE_VARC` `TEMP` with `EVOL` = the thermal result, `VALE_REF` = reference temperature of the Thermal stress | verified: WE-07..09 ≤ 4·10⁻⁸ against the hand calculation; KNOWN_BUGS 64 |
| Temperature-dependent E, ν, α, SY, H (`#ASTER-MATERIAL`) | `ELAS_FO` / `ECRO_LINE_FO`, linear between the table points, constant outside; α = secant relative to `T_ALPHA` (default the reference temperature); ET = E·H/(E + H) per table point | verified: WE-09 (elastic, plastic, reverse yielding) |
| Thermal strain above `T_CUT` | constant (α = ε_cut/(T − T_ALPHA) at points with 2% growth, up to T_CUT + 10 000 K) | choice (melting, Lindgren 2001); without `T_CUT` the strain keeps growing ([Welding.md](Welding.md) §9.2) |
| Metallurgy (`#ASTER-METALLURGIE`) | `CALC_META` `RELATION='ACIER'` (Waeckel) on the thermal result, `META_ACIER`/`DURT_META` in the thermal material; standard datasets 16MND5 (test case mtlp103a) and HSNV101A (hsnv101a); `begin` ferrite by default; phases and hardness as nodal fields | verified: MT-01 (hsnv101a in 3D ≤ 1.3·10⁻⁶), MT-02/MT-08 (Koistinen-Marburger ≤ 4·10⁻⁸), MT-03 (austenitisation ≤ 2·10⁻⁸); measured limits KNOWN_BUGS 72 |
| Metallurgical law (`mechanica=ja`) | `ELAS_META_FO` + `META_ECRO_LINE`, `RELATION='META_P_IL'` with `AFFE_VARC` `M_ACIER`; `PHASE_REFE` follows `begin`, `TEMP_DEF_ALPHA` = reference temperature; linear mixture of the yield strength; ALPHA_A and DEPS required (except HSNV101A) | verified: MT-01 (TEST_RESU hsnv101a ≤ 5·10⁻⁵), MT-04/MT-05 (transformation strain and stress ≤ 6·10⁻⁶) |

### 4.10 Results

| Assumption | What the bridge does | Status |
|---|---|---|
| Nodal stresses | `SIGM_NOEU` and `SIEQ_NOEU` (Code-Aster practice), not Mecway's averaged tensor | deviation, deliberate choice (KNOWN_BUGS 3) |
| Shell stresses | von Mises only (top, middle, bottom) | LS-03, LS-05 |
| Not converged | results up to the last time reached (`BRIDGE_ONVOLLEDIG`) | NL-01 with `convergence_resi_rela` 1e-6 (stops at t = 2.92) |

### 4.11 Acoustics

| Assumption | What the bridge does | Status |
|---|---|---|
| Face without a condition = hard wall | no boundary element (∂p/∂n = 0, natural boundary condition) | source: Mecway (2026) §6.9.1; verified: AK-01, AK-04 |
| *Fluid pressure* = 0 = pressure node | `AFFE_CHAR_ACOU PRES_IMPO PRES=0j` on the nodes or faces; ≠ 0: ERROR for the cavity modes (Mecway refuses it too), imposed pressure (source) in the harmonic analysis | source: Mecway (2026) §9.34; verified: AK-02 (nodes), AK-03 (faces), AH-07 (2 Pa) |
| Several media | coupled with pressure and ∂p/∂n continuous: only correct for equal density; different density: ERROR | measured (AK-05 and a pipe with ρ 1.2/12, [Acoustics.md](Acoustics.md) §3.2); Mecway itself: one material |
| Impedance | Z = *specificimpedancer* + i·*specificimpedancei* (Pa·s/m), boundary term ρ/Z ∫NNᵀdA; cavity modes: complex modes (frequency, decay rate, `pressure` + `pressurei`), without a density ERROR (Mecway then uses ρ = 0, a hard wall); harmonic: real Z as `3D_ABSO` with `CELE_R = Z/ρ`, complex Z: ERROR | source: Mecway (2026) §6.9.2, §9.35; verified: AI-01…10 (≤ 1e-8 against Mecway, analytical ≤ 0.15%), AH-06 (Z = 2ρc, ≤ 7e-6); KNOWN_BUGS 55, 57 |
| Harmonic: source, absorbing boundary, microphone | special selection names `SOURCE_`/`BRON_` (faces, `VITE_FACE`), `ABSORBING_`/`ABSORBEREND_` (faces, `3D_ABSO` with ρc of the medium), `MICROPHONE_`/`MICROFOON_` (nodes); `#ASTER-BRON selection = v [, phase]` | verified: AH-01…08; Mecway has no such input (no harmonic analysis, Mecway (2026) chapter 6) |
| Harmonic: `auto` | A30 with a source (`SOURCE_`, `#ASTER-BRON`, *fluid pressure* ≠ 0) → `acoustic_harm_3d`, otherwise `acoustic_modes_3d` | choice; INFO in the log |
| Vibroacoustics: `auto` | V30 with a fluid part → `vibroacoustic_modes_3d`; a fluid in another analysis is computed as a solid (WARNING) | choice; INFO in the log |
| Vibroacoustics: density | in the matrices (unlike the cavity modes); two fluids with shared nodes only with equal density (otherwise ERROR) | measured: VA-04 (equal density, exact) and a pipe with ρ 1.2/12 (188.23 instead of 306.47 Hz) |
| Vibroacoustics harmonic: input | the same V30 model as the modes; sources `SOURCE_` (velocity), `INCIDENT_` (incident wave), `#ASTER-BRON` (velocity or pressure), boundaries `ABSORBING_` and Mecway *impedance* (real), `MICROPHONE_`, `PROBE_`; choose the analysis yourself (`auto` stays with the modes) | choice; verified: VH-01…08; Mecway does not have this analysis (Mecway (2026) chapter 6) |
| Vibroacoustics harmonic: Rayleigh damping | only on the structure (α·M_s + β·K_s), not on the fluid | choice (Mecway computes no fluid in V30); verified: VH-04, VH-04b |

### 4.12 Fracture mechanics

| Assumption | What the bridge does | Status |
|---|---|---|
| Input | special selection names: node selection `CRACK_FRONT`/`SCHEUR_FRONT`, face selections `CRACK_LIP_UPPER`/`SCHEUR_LIP_BOVEN` and `CRACK_LIP_LOWER`/`SCHEUR_LIP_ONDER`; without a lower lip a half model (`SYME='OUI'`); several cracks with a suffix | Mecway has no fracture mechanics (Mecway (2026)); verified: BR-01…06 (BR-06: two cracks) |
| Front | the edges of the solid elements with both end nodes in `CRACK_FRONT` become SEG2/SEG3 cells (`BRSCHEUR<n>`) | verified: BR-01 (straight), BR-04 (quarter circle) |
| Open crack | the lips may share no nodes outside the front (otherwise ERROR); `CONFIG_INIT='COLLEE'` | verified: BR-01 (double nodes), BR-02 (half model) |
| Material and result | `CALC_G` and `POST_K1_K2_K3` work on a result of their own with a material on all cells (also boundary cells) and the same loads | source: `<EXCEPTION> CALCUL_20` without a material on the lips, `RUPTURE0_94` without `SIEF_ELGA` (seen during the build) |
| Method | `CALC_G` `OPTION=('G', 'K')`: G (theta method) and K (interaction integral) are the result; `POST_K1_K2_K3` is a check | verified: BR-01 (K −0.1 %, G −0.4 %; POST_K −3.5 % with hex20 without quarter points) |
| Curved front | circular front around the lip: `FORM_FISS='CERCLE'`, `RAYON` from the geometry; other curved front: no correction (WARNING) | measured forma07a: without correction K +5.6 %, with +0.1 % |
| Linear, no contact | K and G from one linear static solution; compression on a crack (lips overlapping) is not prevented: WARNING when K_I < 0 | choice; nonlinear and contact on the lips: not built (KNOWN_BUGS 63) |
| XFEM: input | `#ASTER-XFEM shape=CIRCLE/ELLIPSE/RECTANGLE/HALF_PLANE` with the dimensions in m (or with a unit), or a face selection `XFEM_<name>` on a layer of nodes; no crack in the mesh; only solid elements with `3D` (otherwise ERROR) | choice ([Fracture_mechanics.md](Fracture_mechanics.md) §7); verified: BR-07..13 |
| XFEM: smoothing | `CALC_G_XFEM` `LISSAGE`: straight front (HALF_PLANE, RECTANGLE) `LAGRANGE`, curved (CIRCLE, ELLIPSE) `LEGENDRE` with degree `fracture_legendre_degree` (5); per crack `smoothing=`/`degree=`; R_INF/R_SUP from `fracture_r_inf`/`_sup` or per crack | measured: LAGRANGE on a curved front oscillated (−0.1 to 2 × K), LEGENDRE ≥ 2 on a straight front ±3 to ±25 % |
| XFEM: symmetry | *Symmetry* along a global axis becomes `DDL_IMPO` instead of `LIAISON_OBLIQUE` (also fixes the XFEM degrees of freedom); oblique on nodes of cut elements: WARNING | measured forma07b (BR-11): LIAISON_OBLIQUE K1 at the symmetry plane +3.8 %, DDL_IMPO exact |
| XFEM: fields to Mecway | `POST_MAIL_XFEM` + `POST_CHAM_XFEM` + `PROJ_CHAMP` `COLLOCATION`: DEPL, SIGM_NOEU, SIEQ_NOEU on the Mecway nodes (physical, per side of the crack); REAC_NODA from the XFEM result; no SIGM_ELNO, no error estimator and no fatigue | verified: BR-07 (lips symmetric), BR-10 (opening +3.3 %); REAC_NODA on cut elements NOT verified |
| XFEM: K on a curved front | `CALC_G_XFEM` has no curvature correction: WARNING, use `POST_K1_K2_K3` or G | measured BR-10: K_I `CALC_G_XFEM` +5.3 %, `POST_K1_K2_K3` +1.6 %, from G +1.0 % |

### 4.13 Fatigue

Input through `#ASTER` lines, no settings in the main window
([`Fatigue.md`](Fatigue.md)); below the default of each key.

| Assumption / default | What the bridge does | Status |
|---|---|---|
| Input | Mecway has no fatigue (manual, `mecway.exe`): `#ASTER-WOHLER` per material, `#ASTER-FATIGUE`, `#ASTER-BLOCK`/`#ASTER-SIGNAL` | choice (like `#ASTER-LASBRON`: model data) |
| S = amplitude | the Wöhler S is σ_a = Δσ/2, as in `DEFI_MATERIAU FATIGUE WOHLER` | measured: szlz100a (cycle 600/−500 → N(550)), VM-05 |
| `INTERPOL = LOG` | log-log between the table points (as szlz100a/sslv135a) | verified: VM-01a, VM-02a (≤ 10⁻⁶) |
| `PROL_GAUCHE = EXCLU` | no damage below the table | equal to `POST_FATIGUE`/`CALC_FATIGUE` (measured D = 0, VM-06) |
| `PROL_DROITE = LINEAIRE` | above the table extended log-log + WARNING | choice: Code-Aster stops with `EXCLU` and with `LINEAIRE` extends linearly in (S, N) (negative damage measured) |
| `stress = VMIS_SG` | von Mises with the sign of the trace, from `SIGM_NOEU` | as `CALC_FATIGUE CUMUL_DOMMAGE` (`EQUI_GD` default); VM-04, VM-06, VM-07a |
| `counting = RAINFLOW` | periodic: start at the largest absolute value, closed cycles only | equal to `POST_FATIGUE RAINFLOW` (VM-03b) and `CALC_FATIGUE` (VM-04, VM-06) |
| `correction = NONE` | no mean stress correction; Goodman/Gerber with the sign of S_m | formulas equal to `POST_FATIGUE CORR_SIGM_MOYE` (measured, VM-05b/c) |
| `repeats = 1` | D = repeats × D per repetition; `life` = 1/(D per repetition), max. 10¹² | choice |
| Nodal stress | `SIGM_NOEU` (averaged per node) of solid elements; a node of two materials with a curve gets the larger damage | choice (Code-Aster standard for nodal fields, KNOWN_BUGS 3); beams: not built (KNOWN_BUGS 66) |
| Shells | uniaxial route on the top and bottom side: `SIEQ_NOEU` (`VMIS_SG` or the `PRIN_i` with the largest absolute value) of `POST_CHAMP EXTR_COQUE` `SUP`/`INF`; fields `damage_top`/`damage_bottom`, `damage` = the larger | verified: VM-10 (pure bending, ≤ 10⁻¹¹); no strain curve or criterion on shells (WARNING) |
| `strain = PRIN` (strain curve) | principal strain with the largest absolute value from `EPSI_NOEU` (in a bar the axial strain, as a strain-controlled test); `VMIS_SG` = √(2/3 e:e) of the deviator with the sign of the trace | choice; verified VM-11a (PRIN, 2·10⁻⁹), VM-11b (VMIS_SG, exact) |
| Strain curve E | E of the Mecway material (with `*` all materials must have the same E, otherwise `E = ...` required) | choice |
| `criterion = GEEN` | no multiaxial criterion: equivalent stress per time step (`stress`) | choice; with `DANG_VAN`/`MATAKE`/`CROSSLAND`/`FORMULE` Code-Aster's critical plane (`CALC_FATIGUE FATIGUE_MULTI DOMA_NOEUD`) |
| a, c required; b optional | no default for the constants of the criterion: they belong to the material (calibration from σ₋₁ and τ₋₁, Fatigue.md §1.7); b only for `fatigue_ratio`; Code-Aster's `D_VAN_B`/`MATAKE_B` (not in SIGEQ, measured) gets b or 1 | choice; 1 ≤ c ≤ 1.7321 as in the catalogue |
| `loading = PERIODIC` | the history (or each block) is one cycle, N from SIGEQ with the bridge's curve | verified: sslv135a (VM-08a/b, `VALE_REFE`), VM-09 by hand |
| `projection = UN_AXE` | only with `NON_PERIODIC` (Code-Aster `PROJECTION`) | Code-Aster has no default (required); measured on sslv135a: `UN_AXE` = `DEUX_AXES` |
| Initial state in the multiaxial history | the bridge copies the nonlinear/dynamic result (`CREA_RESU`), so that t = 0 counts | `CALC_FATIGUE FATIGUE_MULTI` skips `NUME_ORDRE` 0 (alarm `PREPOST4_27`, measured: half the amplitude on a ramp); VM-08d |
| Life per cycle bounded | N < 1 becomes 1; with Goodman/Gerber and \|S_m\| ≥ S_u (Gerber) or S_m ≥ S_u (Goodman) N = 1; strain curve: N by bisection (tolerance 10⁻¹³), above 10³⁰ cycles no damage | choice (`aster_fatigue`) |
| `counting = ASTM` | residual ranges at the start and end count as half cycles (ASTM E1049 §5.4.4, one pass) | choice; not in a verification test |
| Multiaxial `NON_PERIODIC` | the Wöhler curve goes to Code-Aster extended up to N = 10¹², below it no damage (`EXCLU`) | choice (same limit as `life`) |
| Critical plane, periodic | `CALC_FATIGUE` `METHODE='CERCLE_EXACT'` (not with a formula) | choice; VM-08a/b |
| Base of `#ASTER-BLOCK`/`#ASTER-SIGNAL` | the first stored result (static: the only step), scaled per block or signal value; a block = the history [m − a, m + a], one cycle | choice |
| Message | WARNING if the damage D ≥ 1 | - |

### 4.14 `#ASTER` input: units and defaults

How the bridge reads the values in the `#ASTER` lines (`bridge_custom` and the module
behind it). Point as decimal separator; the comma separates values.

| Line | Without a unit | Units | Status |
|---|---|---|---|
| `#ASTER`, `-POST`, `-EXCIT`, `-CONTACT`, `-ZONE` | text, unchanged into the `.comm` (SI units of the model in Code-Aster) | no check | choice |
| `-OPTIE key = value` | the type of the existing setting (number, text, yes/no) | yes/no: `yes`/`no`, `on`/`off`, `true`/`false`, `1`/`0`, `ja`/`nee`, `aan`/`uit`, `oui`/`non` (also `waar`/`onwaar`, `vrai`/`faux`); any other word gives a WARNING and the setting is kept (until October 2026 silently off); an integer with decimals (`5.0`) is an ERROR | choice |
| `-BEZWIJKEN material = strain` | strain (dimensionless); decimal comma allowed | a unit or `%` is an ERROR | choice |
| `-SPECTRE` extra `K=V` | unchanged into `COMB_SISM_MODAL` (e.g. `ECHELLE`) | no check; the last line per direction counts | choice |
| `-WOHLER` S, Sf, Se, Su, E | no default: ERROR | a stress unit is required (Pa, kPa, MPa, GPa, N/mm2, psi, ksi); N, m, b, ef, c are dimensionless (unit: ERROR) | choice |
| `-VERMOEIING` | a, c, `herhalingen` dimensionless; b with a stress unit | as `-WOHLER` | choice |
| `-BLOK`/`-SIGNAAL` | factors on the static load | numbers only (commas between the values) | choice |
| `-BRON` (`acoustic_harm_3d`) | velocity in m/s; phase in degrees, default 0 | m/s, mm/s, mm/ms, in/s, ft/s; a pressure unit or another unit and text without a number give an ERROR | choice; an imposed pressure: Mecway's *fluid pressure* ≠ 0 |
| `-BRON` (`vibroacoustic_harm_3d`) | velocity in m/s; phase default 0 | Pa, N/m2, kPa, kN/m2, MPa, N/mm2, GPa, bar, mbar, psi = incident wave (converted to Pa once); m/s, mm/s, mm/ms, in/s, ft/s or no unit = velocity; another unit or text without a number is an ERROR (until October 2026 it silently became a velocity in m/s and `1 bar` 1e10 Pa) | choice |
| `-FASE selection = phase` | degrees | a unit is an ERROR; without a line: phase 0 | choice |
| `-LASBRON`, `-MATERIAAL`, `-METALLURGIE` | SI (W, m, m/s, s, Pa, 1/K); temperatures in °C (`TC`, and `AR3`, `MS0`, `AC1`, `AC3` as in `META_ACIER`) | a unit is an ERROR | choice ([Welding.md](Welding.md)) |
| `-XFEM` | length in m | units are converted; an unknown unit gives a WARNING and the value counts as m | choice |

**Mind m and M.** Wherever a unit is allowed, the capital letter matters: `MPa` =
10⁶ Pa, `mPa` (and `mpa`) = 10⁻³ Pa (`parse_and_convert`, like Mecway's own units).
`S = [400, 200] mpa` is therefore a factor 10⁹ too small.

---

## 5. Check runs for this review

All runs: offline, bridge in this working copy, Code-Aster 17.4, October 2026. Base =
the named verification case, one setting changed. The nonlinear runs were done with
`convergence_resi_rela` 1e-6 (the default until October 2026, now 1e-5, §3.3), unless
stated otherwise.

| Id | Base and change | Outcome |
|---|---|---|
| R-SUB1 | NL-02a, `substeps_per_interval` 1 | 3 steps (9, 11 and 9 iterations), result equal to 10 substeps to 1e-7, all checks OK |
| R-REAC0 | NL-02a, `newton_reac_iter` 0 | stops in step 1 with `DVP_2`, no results |
| R-RIGID | block 2×1×1 hex20, only an imposed displacement (rigid translation) | `RELA`: `MECANONLINE9_7` in step 1 (no switch to `MAXI` in the first step, EDF R&D, U4.51.03); `MAXI` 1e-3 N: 1 iteration per step, exact |
| R-MAXI | NL-01, `MAXI` 1e-2 N | up to t = 3, all checks exact |
| R-SUB40 | NL-01, 40 substeps | stops at t = 0.013 (residual force ~5e-4 N) |
| R-SUB40-1E5 / R-SUB40-PETIT | same with 1e-5 / with `PETIT` | up to t = 3; with 1e-5 all checks exact |
| R-CURVE | NL-01 with hardening curve (0, 0), (σy/E, σy), (0.1, …) | Mecway/CCX: 430.6 MPa at t = 2; bridge `auto` (total strain): with 1e-6 stop at t = 0.013, with 1e-5 exact up to t = 3; without (0, 0) with `auto` (total strain): exact up to t = 3 (σ at t = 2: 433.49 MPa, analytical); curve (0, 355 MPa) as plastic strain: exact, WARNING in the log |
| R-ROM | NL-01, 1e-6 with `RELA_OF_MAXI`, `RESI_GLOB_MAXI` 0.05 N / 1e-3 N | 0.05 N: exact up to t = 3 (= NL-01b); 1e-3 N: stops, the absolute residual stalls at ~1e-2 N |
| R-1E5 | all NL and DY cases, `convergence_resi_rela` 1e-6 → 1e-5 | largest relative change of the results 3.75e-6 |
| R-ALPHA | DY-01, HHT α = −0.3 | period +1.21 %, peak −0.87 %, equal to the scheme (4.7e-8) |
| R-ENERGY | DY-01a, `energy_balance` on | result unchanged, 101 balance lines in the `.mess` |
| R-DT | DY-03a, `explicit_dt_factor` 0.7 / 1.0 / 1.5 and 0.3 | 0.7…1.5: `DYNAMIQUE_2`; Code-Aster limit 9.667e-7 s vs estimate 1.933e-6 s; 0.3: within tolerance |
| R-TCHAMWA | DY-03a, `schema` TCHAMWA | within tolerance (only the comparison with the DIFF_CENT chain differs, 0.4 %) |
| R-STRIP | cantilever strip 0.2 × 0.01 m, t = 5 mm, 10 DKT, step load, explicit and implicit | period 9.63 / 9.60 ms (Euler-Bernoulli 9.57 ms), peak 1.957 × static |
| R-GCPC | LS-02 hex8 n = 8 and 16, `lin_solver` GCPC | within tolerance; 232 / 499 iterations |
| R-FREE | block held in X only, `solver_nprec` -1 / 8 | `FACTOR_57` / `FACTOR_11` |
| R-NPREC-CONTACT | NL-03a (STANDARD), `solver_nprec` -1 | runs through; contact force −1.6 %, upper tip +2.8 % (tolerance 0.5 %) |
| R-NORM | MO-01, `modal_norm` TRAN_ROTA | frequencies equal; tip rotation `rotz` = 1.000, largest displacement 0.726 |
| R-SHIFT | MO-01, `modal_shift_hz` 100 / 400 / 600 | at 600 Hz: 104.7…681.7 Hz, the 6 modes closest in ω² |
| R-BSHIFT | BU-01, `OPTION='CENTRE'` with `CHAR_CRIT` 90 / 95 / 150 / 200 / −200; `OPTION='BANDE'` with `CHAR_CRIT=(100, 300)` | `CENTRE`: always the 3 smallest factors, "décalage … 0.00000E+00"; `BANDE`: 209.853 and 259.086 |

---

## 6. References

**Code-Aster documentation** (EDF R&D, version "default"). *Local*: English machine
translation in a local folder with Code-Aster documentation.
*Online*: DocAster, `https://docaster-en-codeaster-doc-4113bb35b8213385c636b94f1536856d7f617.gitlab.io/manuals/man_u/`
(consulted 5 October 2026) and `https://code-aster.org/doc/default/fr/man_u/`.

- EDF R&D (2018). *Notice de calcul au flambage*, U2.08.04, 12-01-2018. Local.
- EDF R&D (2018). *Opérateur THER_LINEAIRE*, U4.54.01, 06-04-2018. Local.
- EDF R&D (2020). *Notice d'utilisation des solveurs linéaires*, U2.08.03, 05-05-2020 (local); version 11-01-2024 online (French).
- EDF R&D (2020). *Opérateur STAT_NON_LINE*, U4.51.03, 30-04-2020. Local; online section "Convergence settings".
- EDF R&D (2020). *Opérateur THER_NON_LINE*, U4.54.02, 05-05-2020. Local.
- EDF R&D (2021). *Mot clé SOLVEUR*, U4.50.01, 04-11-2021 (local); version 11-01-2024 online (French).
- EDF R&D (2021). *Opérateur DEFI_CONTACT*, U4.44.11, 04-11-2021. Local and online.
- EDF R&D (2021). *Opérateur DEFI_MATERIAU*, U4.43.01, 03-11-2021. Local.
- EDF R&D (n.d.). *Instructions for using contact in code_aster*, U2.04.04. Online.
- EDF R&D (n.d.). *Tips for using STAT_NON_LINE*, U2.04.01. Online.
- EDF R&D (n.d.). *General tips for using DYNA_NON_LINE*, U2.06.13. Online.
- EDF R&D (n.d.). *Operator DEFI_LIST_INST*, U4.34.03. Online.
- EDF R&D (n.d.). *Operator DYNA_NON_LINE*, U4.53.01. Online.

**Code-Aster installation** (EDF R&D, code_aster 17.4, Windows build v2025):
`%LOCALAPPDATA%\code_aster\v2025\17.4\lib\aster\code_aster\`; defaults
from `Cata/Commands/` (`calc_modes.py`, `defi_contact.py`, `defi_list_inst.py`,
`dyna_non_line.py`, `ther_lineaire.py`) and `Cata/Commons/` (`c_convergence.py`,
`c_newton.py`, `c_solveur.py`); messages from `Messages/`.

**Mecway**: Mecway (2026). *Mecway Finite Element Analysis, Manual, version 33*
(PDF of 09-03-2026), `C:\Program Files\Mecway\manual.pdf`: §6.2 (nonlinear static),
§7.3 (hex8 with incompatible modes), §7.7 (spring), §9.3 (pinned support),
§9.14 (pressure).

**Literature**

- Belytschko, T., Liu, W.K. and Moran, B. (2000). *Nonlinear Finite Elements for Continua and Structures*. Chichester: Wiley. Stable step with damping (cited in `bridge_to_aster._damped_step_factor`; section NOT checked in the book).
- Hilber, H.M., Hughes, T.J.R. and Taylor, R.L. (1977). Improved numerical dissipation for time integration algorithms in structural dynamics. *Earthquake Engineering and Structural Dynamics*, 5, 283–292.
- Hughes, T.J.R. (2000). *The Finite Element Method: Linear Static and Dynamic Finite Element Analysis*. Mineola: Dover. Chapter 9.

Other literature of the verification tests: [Verification.md](Verification.md).
