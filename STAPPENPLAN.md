# STAPPENPLAN.md – extensions with Code-Aster

The user's wish list (6 Oct 2026) as an executable plan, revised after a
crit-review. To run: type **`/stappenplan`** in Claude Code (the first open step in
table order whose prerequisite holds; then continue with the next one) or
**`/stappenplan S4a`** (a specific step; `S10` = the first open S10 sub-step). The
command lives in `.claude/commands/stappenplan.md` and follows the procedure below.

Commit hashes in the Result column of steps up to and including V2026.1 refer to the
development history before the first public version; they are not in this repo.

## Status

**The table order is the build order** (user's choice: S1, S10, S2, S3, S4, S6,
S7, S8, S5, S9).

| Id | Step | Status | Prerequisite | Result |
|---|---|---|---|---|
| S0 | Main window: navigation list on the left instead of tabs | done | – | 1741e04 (merge b0afe8e); tested in Mecway 6 Oct (navigation, Documentation, run with results) |
| S1 | Error estimator (discretisation error) | done | – | 7a0cda0 (merge e15b36b); tested in Mecway: fields visible, contour per element |
| S10a | Modal with prestress (KNOWN_BUGS 49) | done | – | aa19b0c; tested in Mecway (MP-04: per mode −0.52/0/−0.09/0% relative to Mecway) |
| S10b | Stresses per mode; effective mass for rotations | done | – | 2c8b7cd; tested via a .liml saved by Mecway (S11, identical) |
| S10c | Nonlinear buckling (`CRIT_STAB`), buckling shape as imperfection | done | – | 4d831b4; tested via a .liml saved by Mecway (S11, identical) |
| S10d | Response on a modal basis (Mecway D30 *mode superposition*) | done | – | e10121a; transient, harmonic split off as S10h; tested via a .liml saved by Mecway (S11, identical) |
| S10e | Spectrum analysis (earthquake, shock) | done | S10d | be706a0; tested via a .liml saved by Mecway (S11, identical) |
| S10f | Damping: complex modes | done | – | 6038d88; tested via a .liml saved by Mecway (S11, identical) |
| S10g | Cyclic symmetry (`MODE_ITER_CYCL`) | done | – | c668f42; tested in Mecway 7 Oct (CY-01: whole wheel, 25.74..333.1 Hz = verification) |
| S10i | Cyclic symmetry: the whole wheel in Mecway (expand shapes to N sectors in `<solution>`, like Mecway) | done | S10g | b030096; setting `cyclic_full_wheel` (on by default); tested in Mecway 7 Oct (CY-01: 12 sectors, 960 nodes in Mecway) |
| S10h | Harmonic response in the frequency domain (`DYNA_VIBRA` `HARM`, on a modal basis) | done | S10d | 5ce93a2; own analysis harmonic_3d; tested via a .liml saved by Mecway (S11, identical) |
| S2 | Acoustics: cavity modes (`PHENOMENE='ACOUSTIQUE'`) | done | – | 7c360ec; tested via a .liml saved by Mecway (S11, identical) |
| S2b | Acoustics: impedance boundaries (complex modes, KNOWN_BUGS 55) | done | S2 | stap-S2b; Code-Aster matrices + scipy in the job (`aster_acoustic_complex.py`); tested via a .liml saved by Mecway (S11, identical) |
| S3a | Acoustics: harmonic pressure field (`ACOUSTIQUE`, `DYNA_VIBRA`) | done | S2 | 1072641; tested in Mecway 7 Oct (AH-08: microphone 89.2029 dB = verification, pressure phase field) |
| S3b | Vibro-acoustics (`MECANIQUE`, `3D_FLUIDE` + `FLUI_STRU`, `U_P_PHI`) | done | – | b6cfd07; coupled modes, harmonic split off as S3c; tested via a .liml saved by Mecway (S11, identical) |
| S3c | Vibro-acoustics harmonic (`DYNA_VIBRA` `HARM`, `3D_FLUI_ABSO`, ahlv101a) | done | S3b | a70dd4c; own analysis vibroacoustic_harm_3d (select manually); tested via a .liml saved by Mecway (S11, identical) |
| S4a | Welding: transient thermal with moving source | done | – | 75ae3f2; `#ASTER-LASBRON` + Mecway formulas + temperature-dependent λ/c; tested in Mecway 7 Oct (WE-02: 100.0% of 500 W, temperature and heat flux) |
| S4b | Welding: chain thermal → mechanical (residual stress, distortion) | done | S4a | 3a7a941; Thermal stress in T31 + `#ASTER-MATERIAAL`; tested via a .liml saved by Mecway (S11, identical) |
| S4c | Welding: filler material | done | S4b | 7f2551a; `geboorte=` in `#ASTER-LASBRON` (quiet element), thermal + mechanical; tested via a .liml saved by Mecway (S11, identical) |
| S6a | Fracture mechanics: meshed crack (`CALC_G`, `POST_K1_K2_K3`) | done | – | 5c33ac7; tested via a .liml saved by Mecway (S11, identical) |
| S6b | Fracture mechanics: XFEM | done | S6a | 2740a4c; `#ASTER-XFEM` (CIRKEL/ELLIPSE/RECHTHOEK/HALFVLAK), fields via POST_CHAM_XFEM + PROJ_CHAMP; tested via a .liml saved by Mecway (S11, identical) |
| S7 | Adaptive refinement (Mecway `refine_x2` or HOMARD) | done | S1 | cac0922; Mecway route (`bridge_adapt.py`), HOMARD not built; tested via a .liml saved by Mecway (S11, identical) |
| S8 | Fatigue | done | – | 0a889dd; `#ASTER-WOHLER`, rainflow + Miner, fields damage/life; tested in Mecway 7 Oct (VM-02b: damage 0.004329 = reference) |
| S8b | Fatigue: multiaxial (`CALC_FATIGUE FATIGUE_MULTI`, Dang Van/Matake/Crossland), shells, strain-based (Manson-Coffin) | done | S8 | 04367b8; `#ASTER-VERMOEIING criterium`, shells top/bottom, Manson-Coffin in `#ASTER-WOHLER`; VM-08..11; tested via a .liml saved by Mecway (S11, identical) |
| S5 | Welding: metallurgy | done | S4b | d8d8f31; `#ASTER-METALLURGIE` (datasets 16MND5/mtlp103a, HSNV101A), CALC_META, option META_P_IL in the chain; tested via a .liml saved by Mecway (S11, identical) |
| S5b | Welding: metallurgy continued (tempering, TRIP, kinematic hardening) | open | S5 | not built; question to the user whether this is wanted (see §S5) |
| S9 | Load case combinations via Mecway configurations (go/no-go) | dropped | – | no-go: a Mecway configuration only switches loads on/off, no factor; combinations cannot be set in Mecway; procedure per configuration in Handleiding §4 |
| S11 | Wrap-up: crit-review of verification, check docs against the bridge, integral check, push to `main` | done | all other steps done and on `develop` | 7 Oct: crit-review on Fable (gate processed: 8742df0), settings/tooltips/assumptions (feabce4), docs checked against the bridge (345c400, 088244e, 3c336e4), KB 74/84/85/86 solved, all 270 cases identical via a .liml saved by Mecway (f1539a2), GUI spot checks VM-02b/CY-01/AH-08/WE-02, final regression see Verificatie.md §3 |
| S13 | Orthotropic and anisotropic materials, with *Element orientation* as material direction | open | – | chosen by the user 15 Oct (C1) |
| S14 | Hyperelastic material (Neo-Hooke, Mooney-Rivlin) | open | – | chosen by the user 15 Oct (C7) |
| S15 | Pre-tension section (bolt prestress) | open | – | chosen by the user 15 Oct (C8) |
| S16 | 2D and axisymmetric analyses (S20, D20, SA0, also thermal and acoustics 2D) | open | – | chosen by the user 15 Oct (C9) |
| S17 | Loads on beam faces; hydrostatic pressure on shell edges (KNOWN_BUGS 5) | open | – | chosen by the user 15 Oct (C10) |
| S18 | Test new Code-Aster version (18) | later | Code-Aster 18 for Windows available | version warning and procedure done (`bridge_version.py`, docs/Na_een_update.md) |
| – | Rotordynamics | later | – | |
| – | Soil-structure interaction (MISS3D) | not planned | – | |
| – | Hex block mesher as Tools script | not planned | – | |
| – | Topology optimisation | not planned | – | |

Status: **open**, **done** (with commit), **dropped** (with reason), **later** /
**not planned** (skipped by `/stappenplan`, unless you name the step). A step is
*in progress* if a branch `stap-<id>` exists (see A.4).

## Procedure per step

### A. Prepare
1. `git fetch`; create a worktree on a new branch `stap-<id>` from `develop`
   (`git worktree add … -b stap-<id> develop`, or EnterWorktree). No edits are made in the
   main checkout (the folder from which Mecway starts the scripts): Mecway runs
   there (and a hook blocks edits).
2. **Then** read, **from disk in the worktree** (not from the loaded context, which may
   be from an old commit): `AGENTS.md`, `KNOWN_BUGS.md`, this file, and the docs of
   the topic.
3. Check the prerequisite. If it does not hold: (without argument) take the next open
   step and report which step was skipped and why.
4. If `stap-<id>` already exists: if it is ahead of `develop`, rebase and continue; if it
   has already been merged, delete it and start over.
5. Other sessions (`git worktree list`, branches ahead of `develop`, uncommitted
   changes): a **conflict** is the same topic, or uncommitted changes in
   the same functions (look at the diff). Only the same shared files
   (`bridge_utils.py`, `bridge_gui.py`, `bridge_docs.py`, `KNOWN_BUGS.md`, docs) is
   **not** a reason to stop: rebase and resolve conflicts.

### B. Research
Do not put the input route to the user: research, choose, build and document.
Order for the input:
1. **Mecway itself**: make a small test model (in Mecway or with
   `TestFiles/Verificatie/verif_lib.py`) and read the tags in the `.liml`. Sources:
   `C:\Program Files\Mecway\Samples` and `Tutorials`, `manual.pdf` (with `pdftotext`),
   the tag names in `mecway.exe` (UTF-16), the API in
   `<hoofdcheckout>\API_reference Mecway.txt`
   (gitignored; not present in a worktree).
2. **Special group names**: a Mecway selection, elset or part with a fixed
   prefix (e.g. `LUCHT_`, `KOPPEL_`, `LASNAAD_`, `SCHEUR_`) designates elements or
   faces. Recognise them by the **original** Mecway name
   (`bridge_mesh._aster_names` renames for Code-Aster).
3. **Own `#ASTER-...` keyword** in `bridge_custom.py`: new kind in `_KINDS`,
   `empty()` and `parse()`; example in `docs/ASTER_regels_voorbeelden.md`.

Code-Aster: the catalogue (`…\17.4\lib\aster\code_aster\Cata\Commands\*.py`), the U-docs
(v17.4 site; locally only v14/v15 as background) and the test cases in
`%LOCALAPPDATA%\code_aster\v2025\17.4\share\aster\tests` (run:
`run_aster.bat --ctest <naam>.export`). **Test cases are a syntax source; the
bridge verification is always 3D** (the bridge has no 2D/AXIS, `MECWAY_ANALYSIS_TYPES`).
Back up behaviour in comments with a source, otherwise "NOT verified" (AGENTS.md).

### C. Build
- Extension table in `AGENTS.md`: analysis = template + builder +
  `SOLVER_BUILDERS_ASTER` + `CONFIG_BRIDGE["analyses"]` + `MECWAY_ANALYSIS_TYPES`; field =
  `RESULT_FIELD_SPECS` + `FIELD_TABLE` in `aster_results_export.py`; setting =
  `CONFIG_BRIDGE` + `GENERAL_SPECS`/`ANALYSIS_SPECS` + explanation in `bridge_glossary.py`.
- `SOLVER_BUILDERS_ASTER` has the Code-Aster command as key (`CALC_MODES` is
  taken by `_build_modal`). A **variant of an existing command**: dispatch inside
  the builder on an analysis key (like `type_resu` for modal/buckling), no second
  entry. A **chain** (static → modes, thermal → mechanical): one own template with
  both solves; `export_results` gets the main result as `res`, the rest via
  `extra_results`.
- A new page in the main window automatically appears in the navigation list
  (`new_page(titel, groep)` in `bridge_gui.py`).
- IronPython 2.7 in `Scripts/` (except what runs in the Code-Aster job), texts via
  `tr()` in NL and EN (default language English).
- Clear messages over automatic straightening: if the input says something impossible,
  give an ERROR with the solution.

### D. Verify
NAFEMS style: **few cases, but conclusive**, each with a number and a tolerance.
1. Syntax check and smoke test from `AGENTS.md`; Python 2.7 check with Mecway's
   IronPython: `powershell -ExecutionPolicy Bypass -File TestFiles/Tools/run_ipy.ps1
   -Script <script.py>`.
2. A real Code-Aster run per new route (diagnosis OK, or an explained alarm).
3. References: (a) an **analytical check** (Roark's Formulas for Stress and
   Strain, handbook formulas) on a simple 3D model; (b) where possible **Mecway's
   own solution**, headless: `python TestFiles/Tools/mw_solve.py <in.liml> <uit>`;
   (c) where useful a **Code-Aster test case**: the TEST_RESU values reproduced on a
   3D model. The done criterion of the step states the tolerance.
4. New cases: `TestFiles/Verificatie/tests_<groep>.py` and a section in
   `docs/Verificatie.md` + `docs/en/Verification.md` (layout like the existing ones: model,
   reference with source, result, difference). There are no `doc_*.md` files left in
   `TestFiles/Verificatie`.
5. Regression: set `VERIF_WORK=<eigen scratchmap>` (the default folder is wiped by other
   sessions) and run `python TestFiles/Verificatie/run_verificatie.py` in full.
   **Bar**: baseline 2145 of 2152 checks OK (394 test cases), 7 BEKEND (KNOWN_BUGS
   43: 3 in NL-03a; 83: 1 in BR-10; 108: 2 in LS-52a/LS-67; 115: 1 in BU-35), 0 NOK/FOUT
   (full regression on bridge 24258f9, 2026-10-16, after the extensions of 15 October:
   `TestFiles/Verificatie/resultaten/resultaten.md`). After the step: 0 NOK/FOUT and no previously OK check that is now
   BEKEND/NOK. Commit changed `modellen/` and `resultaten/` along with it; update the summary
   in `docs/Verificatie.md` §3 and the EN version.
6. GUI: offscreen with `TestFiles/Tools/gui_cap.py` (via `run_ipy.ps1`). A test in
   the Mecway GUI itself is only possible **after F.2** (Mecway runs the main checkout), only if the
   screen is free (use the open Mecway instance, do not start a second one). If it fails: a
   fix commit on `develop` and the status back to open.

### E. Document
- User doc `docs/<Onderwerp>.md` + `docs/en/<Topic>.md`, included in `DOCS` of
  `bridge_docs.py` and referenced from `Handleiding.md`/`UserGuide.md`. Structure like
  `docs/Modaal_en_knik.md`: procedure in Mecway step by step, settings with
  default and **when to change**, how the bridge translates, interpretation, what is not
  possible, and a table **messages → cause → solution** so the user can solve errors
  themselves. The correct settings found during verification belong here.
- Settings in `docs/Standaardinstellingen_en_aannames.md` (+EN); special
  group names and `#ASTER` keywords with examples in
  `docs/ASTER_regels_voorbeelden.md` (+EN); new Code-Aster messages in
  `docs/Foutmeldingen_CodeAster.md` (+EN); limitations in `KNOWN_BUGS.md`.

### F. Finish
1. Update the status line (done + commit, or dropped + reason) and fill in the
   **Findings** of the step (chosen input route, measured differences, open
   questions for the user).
2. Commit (in Dutch), rebase on `develop`, and fast-forward `develop` in the
   main checkout:
   - `git -C <hoofd> status --porcelain`. Only `Scripts/bridge_utils.py` changed
     (a setting saved by the user): save the diff
     (`git -C <hoofd> diff Scripts/bridge_utils.py > <scratch>/settings.patch`), then
     `git -C <hoofd> checkout -- Scripts/bridge_utils.py`, `merge --ff-only stap-<id>`,
     and afterwards restore the setting values **by hand** in the
     `CONFIG_BRIDGE` block (line by line; no `git apply` if the step changed that
     block). Leave the restored setting uncommitted.
   - Other changes in the main checkout: do not merge, stop and report.
   - Push **only `develop`**, never `main`.
3. Clean up: `git worktree remove <pad>` and `git branch -d stap-<id>`.
4. Do the Mecway GUI test if it is needed (D.6).
5. No reason to stop: start the next open step directly in the same session. Collect
   questions for the user in Findings and in the final report, not in between.

**Stop and report** if a prerequisite does not hold, another session is working on the same
topic, the main checkout has changes other than `bridge_utils.py`, or the
verification fails and cannot be fixed. If a step is larger than one run: build a
usable, verified part and split the rest off as new rows in the status table.

### S11 – Wrap-up (user's instruction, 7 Oct 2026)
Only when all other steps are done and pushed to `develop`, in this order:
1. One crit-review focused on the verification (see below) and process the findings;
   then check all documentation by running the described settings with the bridge.
2. **Integral check** of all functionality: everything works; all assumptions and hidden
   settings are in the documentation and where possible in the tooltips of the input fields;
   the documentation is consistent; all test cases work from models **built
   in Mecway** and computed in Code-Aster via the bridge (GUI route). Fix errors found.
   Keep questions until nothing more can be done without breaking something.
3. After that (and only then) `develop` may be pushed to `main` (user's permission).

**At the end of a series of steps** (user's instruction): one crit-review focused
on the verification (enough Code-Aster test cases and analytical checks to prove that it
works, recorded in `docs/Verificatie.md`), process the findings, and then
**check all documentation by running the described settings with the bridge
itself**.

## Steps

### S0 – Main window: navigation list on the left
Done (1741e04): the TabControl has been replaced by a drawn navigation list on the left
(groups Settings / Analyses / Help) with the page on the right; `new_page(titel, groep)`
is the only registration point. Tested offscreen in NL and EN, saving byte-for-byte identical
to the old version. **Open:** test in the Mecway GUI (modeless behaviour, mouse).
**Findings:** the duplicate heading "General" under the page title is now called "Language and
installation". Mecway GUI test on 6 Oct not done: access to Mecway refused
(user absent).

### S1 – Error estimator
**Goal:** the estimated discretisation error as a field in Mecway and the global relative error
in the log, so you can see where the mesh is too coarse.
**Code-Aster:** `CALC_ERREUR`: `ERME_ELEM`/`ERME_ELNO`/`ERME_NOEU` (residual; components
`ERREST`, `NUEST`), `ERZ1_ELEM`/`ERZ2_ELEM` (Zienkiewicz-Zhu), `QIRE_*` (goal-oriented;
requires a dual problem `RESU_DUAL`, not standard), `ERTH_*` (thermal). 3D test cases:
`sslv07a`, `sslv111f` (ERZ1), `sslv153a` (ERME_NOEU, QIRE), `ssnv301a`. (`forma01b`,
`forma20a` are C_PLAN: syntax only.)
**Route:** `ERME_NOEU` → `nodevariable` (KNOOP in `FIELD_TABLE`); `ERME_ELNO` →
`elementnodevariable` (ELEMKNOOP, solid elements only). Global relative error from
the .mess ("ESTIMATEUR D'ERREUR EN RESIDU EXPLICITE … RELATIVE").
**Research:** which elements/analyses (shells, beams, `LINE_QUAD`, nonlinear,
thermal); whether Mecway shows its own variable name (Mecway GUI after F.2).
**Done when:** on the series `LS-02-h8-n1…n16` (TestFiles/Verificatie) the global
relative error decreases monotonically with order ≈ 1 (±0.2); the error is largest at the fixed support;
regression according to D.5.
**Findings:** Input route: no input needed, setting `error_estimator`
(lin_static_3d, on by default; also `#ASTER-OPTIE`). Only `ERME` on solid elements with
`MECA_STATIQUE`; the bridge itself sets the free faces as boundary elements with pressure 1e-14
(Code-Aster treats an unloaded face as supported; 0 does not work) and computes the estimator in
a separate model/load/result (beams: CALCUL_37; multiple pressures: INDICATEUR_7/8;
point loads: INDICATEUR_6/8; reuse with different EXCIT: CALCULEL_39). Fields
`errorestimate`/`errorestimaterel` (node and per element), global error from the `.mess`
in log and status box. FS-01 (hex8): order 0.88/0.96/0.96, effectivity 1.3-2.2; FS-02
(hex20): order ~1.9; FS-03 = sslv153a exact. Not: nonlinear, thermal (ERTH),
shells/beams, ZZ and QIRE (KNOWN_BUGS 51).

### S10 – Extend modal and buckling
First read `docs/Modaal_en_knik.md` and KNOWN_BUGS 46-49. Existing route:
`_build_modal` (one builder for modal and buckling, dispatch on `type_resu`),
`AsterTemplate_CalcModes.comm`.

- **S10a – Modal with prestress.** Mecway computes a frequency analysis with
  loads as prestressed (*stress stiffening*); the bridge currently ignores the loads
  (WARNING). Chain: `MECA_STATIQUE` → `SIEF_ELGA` → `RIGI_GEOM` → `CALC_MODES` with
  K + Kg (the same steps as the buckling route, dispatch in `_build_modal`).
  **Done when:** frequencies within 1% of headless Mecway with load
  (`mw_solve.py`), plus an analytical check: string/beam under tension
  (f = f0·sqrt(1 + P/Pcr) or a string formula, Roark/Blevins), ≤ 1%.
- **S10b – Stresses per mode; effective mass for rotations.** Code-Aster only has
  `MASS_EFFE_UN_DX/DY/DZ`; compute rotations ourselves (participation with rigid
  rotation vectors about the centre of gravity) or document that it is not possible. Stresses per
  mode: `CALC_CHAMP` on the modal result; only show them if Mecway can show them.
  **Done when:** the sum of the effective rotational mass over all modes approaches the
  mass moment of inertia (≤ 1% with enough modes) on a beam model.
- **S10c – Nonlinear buckling.** `CRIT_STAB` in `STAT_NON_LINE` (test cases `ssll105d`,
  `ssll105e`, `ssll105f`) and a buckling shape as imperfection (`MODI_MAILLAGE`
  `DEFORME`, scalable amplitude) before a nonlinear analysis. Find the input in
  Mecway/`#ASTER-OPTIE`. **Done when:** `CRIT_STAB` on an Euler column within 2% of
  the linear buckling route and of pi²EI/(kL)²; with imperfection the load capacity drops
  (Southwell/Ayrton-Perry as check).
- **S10d – Response on a modal basis.** Mecway *Dynamic Response* (D30) has an option
  *mode superposition* (manual §6.4); D30 is not yet in `MECWAY_ANALYSIS_TYPES`.
  Code-Aster `DYNA_VIBRA` `BASE_CALCUL='GENE'`, harmonic and transient (test case
  `forma12d`: `MACRO_ELAS_MULT` as static correction). Read the D30 tags in a
  Mecway model first. **Done when:** single-degree-of-freedom-like model (mass on spring/beam)
  within 1% of the analytical response (dynamic amplification factor), and equal to
  headless Mecway D30 (≤ 2%).
- **S10e – Spectrum analysis.** `COMB_SISM_MODAL` (test case `sdld25a`); research the input of the
  spectrum (Mecway table or `#ASTER`). **Done when:** `sdld25a` values within
  1% on a 3D replica, and SRSS/CQC recalculated by hand on a 2-mode system.
- **S10f – Damping: complex modes.** Rayleigh/modal damping in `CALC_MODES` (complex
  modes) or as modal damping ratio in S10d. **Done when:** damping ratio of
  a single-degree-of-freedom system within 1% of the specified value.
- **S10g – Cyclic symmetry.** Mecway has a *Cyclic symmetry* constraint
  (manual §9.41). Code-Aster `MODE_ITER_CYCL` requires `BASE_MODALE`, `NB_SECTEUR` and
  `LIAISON` left/right (substructuring): a big translation job. **Done when:** a sector
  of a ring/disc gives the same frequencies as the full model (≤ 1%).
**Findings:**
- *S10a (done):* Mecway always computes prestressed as soon as there is a load
  (manual §6.3), also thermal strain (example VibratingMembrane) and centrifugal
  with spin softening (Impeller). Built: setting `modal_prestress` (on by default
  = Mecway; page Modal), dispatch in `_build_modal` via `_prestress_plan`:
  `MECA_STATIQUE` → `SIEF_ELGA` → `RIGI_GEOM` (+ `RIGI_ROTA` with `ROTATION`) →
  `COMB_MATR_ASSE` (COEF_R 1, test cases sdll101a/sdll133a). Prescribed displacement
  ≠ 0 with prestress: ERROR (Mecway then gives no solution headless); without
  supports: ERROR; contact was already ERROR. Negative frequency (compression > buckling load):
  WARNING (Mecway gives 0 Hz). Verification MP-01..07 (`tests_modaal_voorspanning.py`):
  beam tension/compression analytical ≤ 0.001% and equal to Mecway; hex20 −0.05/−0.11%
  analytical, equal to Mecway; plate with thermal compression analytical ≤ 0.05%, Mecway
  −0.25%; rotating hex20 beam equal to Mecway; rotating `POU_D_E` beam −0.52% in
  the plane of rotation (KNOWN_BUGS 49). Open: Mecway GUI test; VibratingMembrane (E =
  0.001 Pa) finds nothing with the lowest modes (spurious `COQUE_3D` rotation modes; with
  a search frequency it does, KNOWN_BUGS 49). Question to user: omit spurious modes without effective
  mass automatically, or leave as is (now: leave as is, message)?
- *S10b (done):* Mecway (headless, fieldvariables `modal effective mass (fraction)`
  and `stress` before solving) gives per mode `<globalvariable>`
  `modaleffectivemass{tx..rz}` and `...fraction..`, rotation about the **origin**
  (recalculated: J_X = 524.15 kg·m² of a block at (1, 2, 3) m), fraction of the *free*
  mass; and also stresses per mode (`stressxx`.., `vonmises`; docs §1.4 wrongly said
  it did not). Built: effective mass for the rotations in the job
  (`aster_results_export._effective_masses`, Γ = φᵀMR with the mass matrix `masse`,
  `getNodeAndComponentFromDOF`), about the origin like Mecway, fraction of RᵀMR
  including supported nodes like Code-Aster's translations; check per run: own
  translations = `MASS_EFFE_UN_D*` (≤ 1e-4), otherwise no rotations. Log/status box
  RX/RY/RZ + sum, line `BRIDGE_MASSA` (mass, centre of gravity, J about origin and
  centre of gravity). Stresses per mode as an option via the existing setting `fields`
  of `modal_3d` (`stresses`/`vonmises`, off by default; no new setting;
  `CALC_CHAMP` without `REAC_NODA`, also shells and beams). Verification: MO-06 (free
  block, sum = Steiner exact), MO-07 (hex20: rotation mode 1 −0.03% relative to Euler 0.97069,
  sum of 6 modes −0.15%, σ_xx mode 1 +0.43% analytical / +0.01% Mecway), MO-01/MO-04
  extra checks; Mecway's API reads the stresses per mode from the bridge `.liml`.
  Open: Mecway GUI test (show stresses per mode);  Questions to user:
  also write the effective mass as a Mecway field (`<globalvariable>`, with the bridge fraction
  instead of Mecway's free mass)? (Decision: yes, built in S12: always for
  modal and complex modes, Mecway's own names + `cumulativeeffectivemassfraction*`;
  verification MO-01/MO-06; open: Mecway GUI test of the cumulative variable.)
  Rotation about the centre of gravity as an option (now:
  move the origin)? Stresses per buckling shape?
- *S10c (done):* Mecway has no input for nonlinear buckling (manual §6.2, §6.6;
  example BucklingPlateNonlinear uses a small perturbation force). Input route:
  settings on the page Nonlinear static (`crit_stab`, off by default;
  `imperfection_amplitude` 0 = none, `imperfection_mode` 1, `imperfection_unit` m or
  L = fraction of the largest model dimension), also per model with `#ASTER-OPTIE`. Built
  (`bridge_to_aster._crit_stab_*`, `_imperfection_*`): `CRIT_STAB` PLUS_PETITE 1 mode
  in `STAT_NON_LINE`, table `ANALYSE_MODALE` as `BRIDGE_CRIT_STAB` in the `.mess`, log
  and status box with message "buckling reached"; imperfection = linear buckling (like
  `buckling_3d`, loads at the end time, `NORM_MODE` TRAN) → `MODI_MAILLAGE DEFORME`
  (+ `AFFE_CARA_ELEM` again) → `STAT_NON_LINE` → `CALC_CHAMP` → mesh back with
  −e0·φ, so that `_check_node_order` holds (displacements relative to the imperfect shape).
  Measured: with small displacements CRIT_STAB is a load factor (det(K_T + λK_g)), with
  large ones (default for solids, one elset is enough) −(smallest eigenvalue of K_T)
  (det(K_T + λI), "produits B*X = 0"); the bridge then estimates the zero crossing. Verification
  NK-01..04 (`tests_niet_lineaire_knik.py`): beam λP = Pcr < 0.001%; hex20 buckling point
  +0.38% (large) and +0.20% (PETIT, = BU-03); imperfection L/1000: amplification
  e0/(1 − P/Pcr) up to 0.675 Pcr ≤ 0.44%, Southwell Pcr +0.20%; plastic with e0 = L/200:
  load capacity 0.488 Pcr between Ayrton-Perry 0.419 and hinge 0.563, CRIT_STAB → 0.
  Limitations: KNOWN_BUGS 53. Open: Mecway GUI test (status box, fields after
  imperfection). Questions to user: (1) also send the imperfection as a field to Mecway, or show the
  displacements including imperfection (now relative to the imperfect shape)? (2)
  CRIT_STAB in dynamics too (`DYNA_NON_LINE`)? (3) arc-length method (`PILOTAGE`)
  to compute beyond the limit point (new step)?
- *S10d (done, transient):* Mecway input `<analysis type="D30"
  modesuperposition="true" maxmode="n" />` with `<timesteps timeperiod stepsize
  [keepeverynthtimestep]>` (DampedVibratingStrip, strings in mecway.exe). Measured
  headless: Mecway integrates the modal equations **exactly** (step 0.02 and 0.001 s
  equal, 1e-4 of u_st(1 − cos ωt)), without static correction (1 mode: 0.9707 ×
  static = 12/λ₁⁴) and without prestress from the loads; output at t = 0 and every
  n-th step; fields displ/rot/vel/angularvel/von Mises. Built: analysis
  `dyna_modal_3d` (`bridge_dyna_modal.py`, `AsterTemplate_DynaVibra.comm`,
  `SOLVER_BUILDERS_ASTER["DYNA_VIBRA"]`), `auto`: D30 + mode superposition →
  `dyna_modal_3d`, D30 without → `dyna_impl_3d` (output times from `stepsize`; WARNING
  unless NEWMARK + PETIT, then equal to Mecway). Chain `CALC_MODES` → loads split per
  time function (variant of each `AFFE_CHAR_MECA_F` with that function at 1,
  the rest 0) → `CALC_VECT_ELEM`/`ASSE_VECTEUR` → `PROJ_BASE` → `DYNA_VIBRA` GENE
  (NEWMARK, `steps_per_period` 50 of the highest mode; Rayleigh as `AMOR_REDUIT`
  ξ = α/2ω + βω/2 + `modal_damping`) → `REST_GENE_PHYS` (`DEPL`, `VITE`, `ACCE` for
  `SIPM_ELNO`) → `CALC_CHAMP` with `MODELE`/`CHAM_MATER`. Option `static_correction`
  (`MACRO_ELAS_MULT` + `CORR_STAT`, forma12d). Angular velocity `angularvel*` now also in
  `FIELD_TABLE`. Verification MD-01..07 (`tests_dynamisch_modaal.py`, 21 checks):
  SDOF step/damped/harmonic analytical ≤ 0.17% (time history), peak 0.00–0.17%; relative to
  headless Mecway ≤ 1.4e-5 (SDOF), hex20 4e-5 / 1.4e-4 / 4e-4 (u / v / σ_xx), cantilever
  1 mode 3.4e-3; static correction exact; D30 direct 3e-8. DampedVibratingStrip
  (shells): 1.9% (frequencies shells −0.6/+0.3%, KNOWN_BUGS 2). Regression 390/393
  OK, 3 BEKEND (KNOWN_BUGS 43), 0 NOK. Limitations: KNOWN_BUGS 54. Harmonic in the
  frequency domain split off as **S10h** (Mecway has no analysis type; research input
  frequency list + load, `DYNA_VIBRA TYPE_CALCUL='HARM'`
  `BASE_CALCUL='GENE'`, test cases sdld21b and sdld313d (`HARM` + `GENE`) as syntax source; done when: DAF
  1/√((1−r²)² + (2ζr)²) ≤ 1% on the SDOF model of MD). Open: Mecway GUI test.
  Questions to user: compute D30 without mode superposition automatically with NEWMARK + PETIT
  (now: `dyna_impl_3d` with its own settings + WARNING)? Build an initial velocity
  and prescribed motions on a modal basis (static modes)?
- *S10e (done):* Mecway has no spectrum analysis (manual chapter 6; no
  "spectrum"/"seism" in mecway.exe). Input route: Mecway *Frequency* (V30, Number of
  modes) with a **Gravity with a table per direction** (column *time* = period [s],
  setting `spectrum_abscissa` also frequency; value = spectral acceleration; without
  table = flat spectrum; the gravity is not a load), analysis `spectrum_3d` selected manually
  (`auto` remains `modal_3d`). Own spectrum (`DEFI_NAPPE`/`FORMULE` in AMOR and FREQ,
  e.g. multiple damping values) with the new `#ASTER-SPECTRE X, Y = naam [, K=V]`.
  Built: `bridge_spectrum.py`, `AsterTemplate_Spectre.comm`, job module
  `aster_spectrum.py`; chain `CALC_MODES` → `CALC_CHAMP` (REAC_NODA, SIGM) →
  `MODE_STATIQUE PSEUDO_MODE` → `COMB_SISM_MODAL MONO_APPUI` → maxima as a
  static step (`CREA_RESU`); settings `spectrum_damping` (0.05 + Rayleigh),
  `modal_combination` (CQC), `direction_combination` (SRSS; 100-30-30 is computed by the bridge
  from `VALE_DIRE`; 100-40-40 = `NEWMARK`), `missing_mass` (on, `FREQ_COUP` = highest
  mode). Fields: displacement, absolute acceleration (new `accelx/y/z`), stress
  (solids), von Mises (computed per mode and combined: SRSS = expected value
  of σᵀPσ, CQC upper bound), reactions; log: effective mass per direction (WARNING
  < 90% without missing mass), cut-off frequency, combined total reaction (the sum
  of nodal maxima is too large). Verification SP-01..07 (9 cases, 41 checks):
  sdld25a (8 masses/springs, Rayleigh β, DEFI_NAPPE via #ASTER-SPECTRE) frequencies ≤
  3e-14, ACCE_ABSOLU ≤ 3.5e-8 (done criterion 1%); two masses SRSS, CQC (ρ = 0.17),
  missing mass with 1 mode and the total reaction ≤ 1e-6 of the hand calculation
  (criterion 0.5%); directions SRSS/100-30-30/100-40-40 ≤ 4e-8; hex20 cantilever relative to
  Euler-Bernoulli u −0.02%, σ/von Mises +0.38%, reaction −0.12%. Mecway reads the step
  under V30 via the API (headless script: `node_value`, `modes()` empty); GUI display
  NOT verified. Regression 444/447 OK, 3 BEKEND (KNOWN_BUGS 43), 0 NOK. Limitations:
  KNOWN_BUGS 56. Open: Mecway GUI test (step under a Frequency analysis, `accel*`).
  Questions to user: (1) `auto` with V30 + gravity with table to `spectrum_3d` (now select
  manually)? (2) missing mass on by default (now) or off (Code-Aster default)?
  (3) direction combination default SRSS (now), 100-30-30 (EC8) or 100-40-40
  (Code-Aster)? (4) spectrum per support (`MULT_APPUI`) needed? (5) have an EC8 spectrum
  generated from a_g and ground type instead of a table?
- *S10f (done):* Mecway (measured headless) has no damped modes: V30 ignores
  Rayleigh damping (same frequencies, no decay rate; according to manual
  §9.26 Rayleigh belongs to D30/D31) and gives no solution with a Damper element (D30 ignored the
  hand-written damper too, cf. KNOWN_BUGS 47). Mecway only knows complex modes
  acoustically (`<mode frequency=".. Hz" decayrate=".. 1/s">`, seen headless). Built
  as an option: setting `modal_complex` (page Modal, off by default = real modes
  like Mecway, INFO when there is damping in the model), `bridge_modal_damping.py`: C = αM + βK
  (`COMB_MATR_ASSE` on the matrices of the eigenvalue problem, so also nodal masses and
  springs, with prestress K + K_g) + `AMOR_MECA` of the dampers (other discrete elements
  `A_*` 0 against `DISCRETS_28`); `CALC_MODES` with `MATR_AMOR`, `PLUS_PETITE` +
  `TRI_DIAG` (Sorensen is not possible: `ALGELINE2_71`), with search frequency or free-free
  `CENTRE` + Sorensen. Measured: Code-Aster's `FREQ` = damped frequency,
  `AMOR_REDUIT` = ζ; overcritical and rigid modes drop out (`ALGELINE5_79`, hint in
  bridge_run_aster). Export: `<mode frequency="f_d Hz" decayrate="ζ·2πf_n 1/s">`, shape
  = real part after phase rotation (½·arg φᵀMφ), φᵀMφ = 1 (with Rayleigh equal to the
  real mode, 2e-9); log/status box per mode f_d, ζ, f_n and effective mass; Mecway
  comparison on f_n. Mecway's API reads the modes (headless script, `frequency` = f_d);
  GUI NOT inspected. Verification MC-01..05 (`tests_modaal_demping.py`): mass-spring-
  damper ζ = 0.1/0.5 and Rayleigh α/β (ζ = 0.2): ζ, f_d and f_n ≤ 1.3e-15 analytical
  (criterion 1%); 2 masses with damper (non-proportional) ≤ 1.1e-14 relative to
  det(s²M + sC + K) = 0; hex20 cantilever α = 20, β = 1e-4: ζ_n = α/2ω_n + βω_n/2 ≤ 2e-11
  per mode (6 modes), f_n equal to Mecway (≤ 8.4e-11); free-free: 6 rigid modes removed,
  elastic ones equal to Mecway (≤ 3e-11). Regression 569/572 OK, 3 BEKEND (NL-03a,
  KNOWN_BUGS 43), 0 NOK/FOUT. dyna_modal_3d: the same ξ_i (docs). Limits: KNOWN_BUGS 49. Open:
  Mecway GUI test (f_d and decay rate under *Solution*). Questions to user: (1) the
  frequency in Mecway damped (now, like Mecway's acoustics) or undamped? (2) also send the
  imaginary part of the shape to Mecway (field name unknown)? (3) hysteretic
  damping (`AMOR_HYST`) or `modal_damping` as ζ per mode also needed in modal?
- *S10h (done):* Mecway has no harmonic analysis (manual chapter 6; D30 is
  transient). Input route: own analysis `harmonic_3d` (page *Harmonic response*,
  select manually; `auto` remains V30 → modal) on a V30 or D30 model; the loads
  are the amplitude, phase per selection with the new `#ASTER-FASE selectie = graden`
  (`PHAS_DEG`), a Mecway table of a load = amplitude versus frequency (column
  *time* = Hz, `DEFI_FONCTION NOM_PARA='FREQ'` as `FONC_MULT`), measurement points with
  node selections `MEETPUNT_`/`PROBE_` (log, status box, `_meetpunten.csv`). Frequencies
  with the keys of S3a (`harm_freq_start/_end/_count/_spacing/_list`) plus
  `harm_refine_points` (5 points per mode over 2ξf around the peak: `DEFI_LIST_FREQ`
  `RAFFINEMENT` `LARGEUR_3DB`, sdld21b), `harm_basis` GENE (default) / PHYS (direct,
  C = αM + βK + dampers), `modal_damping`, `static_correction` (on by default:
  static enrichment of the basis like `DYNA_LINE` `ENRI_STAT`: `MACRO_ELAS_MULT` +
  `DEFI_BASE_MODALE RITZ ORTHO` + `CALC_MODES QZ` + `REST_GENE_PHYS`). Built:
  `bridge_harmonic.py` (dispatch in `_build_dyna_modal` on `type_calcul` 'HARM'),
  `AsterTemplate_Harmonisch.comm`, job module `aster_harmonic_export.py` (per
  frequency `<mode frequency>` with `displx/y/z` = Re, `displix/y/z` = Im,
  `displamp*`, `displphase*`, `displmag`, `rot*`/`rotamp*`, `velamp*`/`accelamp*`,
  `stressxx..` = Re, `stressamp..`, `vonmises` = maximum over the period, exact from the
  complex `SIGM_NOEU`). Measured: U = F·e^{iφ}/(k − mω² + iωc) (`PHAS_DEG` +,
  lagging negative); `FONC_MULT` as a function of `FREQ` works in GENE and PHYS; a
  chain `getField(..).toSimpleFieldOnNodes().getValues()` gave NaN (keep intermediate objects
  alive). Verification HR-01..05 (`tests_harmonisch.py`, 11 cases, 40 checks):
  (a) 1 degree of freedom (spring + mass) with modal damping, Rayleigh α (GENE and PHYS) and
  a damper ζ = 0.2: |U| ≤ 5.5e-8 and phase ≤ 7.5e-6° over the whole range
  (criterion 1% and 1°), peak and peak frequency exact; (b) Euler-Bernoulli cantilever
  (exact receptance, Rayleigh α): GENE with enrichment and PHYS 6.6e-4 over 1–200 Hz,
  GENE = PHYS 1.9e-5 (criterion 1%); without enrichment the static part of the
  omitted modes 6.22e-4 = 1 − Σ12/λ⁴ and 64% error in the antiresonance; hex20 cantilever
  GENE = PHYS (tip 4.3e-6, von Mises 4.3e-5, |σ_xx| 2.3e-3); phase, table, antiphase and
  measurement point CSV exact. Mecway's API reads the result (headless `mecway.exe <model>
  script <script.py>`: 120 frequencies and the fields). Regression (`VERIF_WORK` own
  folder): 712/715 OK (162 cases), 3 BEKEND (NL-03a, KNOWN_BUGS 43), 0 NOK/FOUT, no
  previously OK check worse. Limitations: KNOWN_BUGS 54. Open: Mecway GUI test (list
  per frequency, contour of `displamp*`, animation). Questions to user: (1)
  `static_correction` on by default (now, Code-Aster `DYNA_LINE`) or off? (2)
  hysteretic damping (loss factor η, `AMOR_HYST`) needed? (3) build base motion
  (prescribed acceleration/displacement, `MULT_APPUI`/static modes)? (4)
  the frequency response also as a Mecway graph (e.g. `<globalvariable>`) instead of CSV?
  (5) set `harm_freq_end` automatically to the highest mode?
- *S10g (done):* Mecway input (measured headless, Samples/Impeller.liml and own
  ring sectors): `<cyclicsymmetry axis segments selectionmaster selectionslave>`,
  `axis` 1/2/3 = X/Y/Z through the origin, master/slave node or face selections, slave at
  ±360°/N. Mecway computes *Number of modes* modes per ND 0 … N/2 (a pair of standing
  waves once), in order of ND, and puts the whole wheel (own nodes and
  elements) in `<solution>`. Chosen route: Code-Aster `MODE_ITER_CYCL` (no
  full model): `bridge_cyclic.py` (pairs at ±360°/N, GAUCHE = +360°/N, nodes on the
  axis → `AXE`, fully fixed cut-face nodes from the interfaces, X/Y axis → exact
  swap of the coordinates and the load directions, prestress with the relations
  of ND 0), template `AsterTemplate_ModeIterCycl.comm` (Craig-Bampton basis:
  `CALC_MODES` with fixed cut faces, `DEFI_INTERF_DYNA`, `DEFI_BASE_MODALE`,
  `MODE_ITER_CYCL` `NB_DIAM` 0 … N/2, `REST_SOUS_STRUC SECTEUR=1 NOM_CHAM='DEPL'`),
  job module `aster_cyclic.py` (Mecway's order, `BRIDGE_MODE .. ND=..`; the result
  of REST_SOUS_STRUC only got fields after `setMesh`/`setDOFNumbering`/`build`); log and
  status box with ND; setting `cyclic_base_modes` (0 = max(20, 4 × modes per ND)).
  Code-Aster pitfalls found: noise around 0 in the axial coordinate →
  `ALGORITH16_52` (the bridge sets < 1e-12 × model size to 0, MODI_MAILLAGE rotation
  avoided), `TOUT_DIAM` computes one ND too many for odd N, `REST_SOUS_STRUC`
  `NOM_CHAM` defaults to `'ACCE'`, 8 segments with nodes on the axis → `ALGORITH14_95`
  (bug in `ctetax.F90`, ERROR). Verification CY-01..06 (`tests_cyclisch.py`, 134
  checks): ring (12 segments, Z and X) and rotating disc (Y, 3000 rpm,
  prestress) relative to the full model ≤ 0.0012% (criterion 1%), relative to Mecway's
  cyclic solution ≤ 0.03% (criterion 1%), ring relative to Blevins +0.59 … +1.18% and
  clamped plate (6 segments, nodes on the axis) relative to Leissa +0.58 … +0.66%
  (criterion 2%). Mecway's Impeller (Y, 100,000 rpm): 27 modes +0.01 … +0.92% relative to
  Mecway, the sector without cyclic symmetry deviates by the same amount (KNOWN_BUGS 62).
  Mecway's API reads the modes from the bridge (headless script); GUI NOT inspected.
  Limits: KNOWN_BUGS 61 (among others double eigenvalue in ND 0 +1.3%, modal only,
  solid elements only, only the sector to Mecway). Split off: **S10i** (the
  whole wheel in Mecway). Open: Mecway GUI test (sector solution of a cyclic
  model in the GUI, list *Mode 1..n*, animation). Questions to user: (1) show the whole wheel
  (S10i) or is the sector enough? (2) cyclic symmetry also in static and
  thermal (Mecway can do it; now ERROR and a separate sector)? (3) a partial
  support on a cut face (axially free) needed? (4) with a double eigenvalue in
  ND 0, rather the full model as an option (`cyclic_method`)?
- *S10i (done):* Mecway's format (headless `mw_solve.py` on CY-01, CY-04, CY-05,
  Impeller and variants: two elsets, loose node, master/slave swapped): the
  model copy in `<solution>` has N copies; node i of sector j = i + j·n, rotated
  by +j·360°/N (clockwise-positive, independent of master/slave), element e + j·ne
  (ne = highest eid), per elset the sectors one after another, all nodes copied (also
  cut faces and axis). Code-Aster: `DEFI_SQUELETTE` (`CYCLIQUE`, `SECTEUR TOUT='OUI'`) +
  `REST_SOUS_STRUC SQUELETTE NOM_CHAM='DEPL'` gives exactly that structure (N·n nodes,
  block j = sector rotated by +j·360°/N, with the phase; block j = `SECTEUR=j+1` rotated; seen
  with CY-01), also about X/Y (skeleton rotated back) and with nodes on the axis; the result
  got fields without `setMesh`. Built: `aster_cyclic.collect` (wheel or fallback to
  the sector with WARNING, `BRIDGE_CYCL ... WIEL=0|1`), `wheel_model`/`node_rows`
  (matching on coordinate), `aster_results_export(cyclic=...)`,
  `bridge_results_liml.splice_results`/`check_results_fit` (nodes and elements of
  the wheel in the model copy), setting `cyclic_full_wheel` (on by default). Measured:
  model copy equal to Mecway's own (ids, order, elements; coordinates ≤ 1.1e-15
  m), Mecway's API reads the bridge's wheel like its own (CY-01, Impeller);
  shapes relative to the full model 1 − MAC ≤ 5.1e-7 (CY-01) and ≤ 2.1e-8 (CY-05),
  criterion 1e-3; cut faces continuous ≤ 1.3e-14; on the axis (CY-04, ND 1) 6.2e-4,
  Mecway's own solution 9.4e-4; relative to Mecway's wheel ND 0 MAC 1.000000 (CY-05),
  Impeller 0.9996 … 0.99994. 37 new checks in `tests_cyclisch.py` (CY 171/171).
  Regression (`VERIF_WORK` own folder): 1055/1058 OK (216 cases), 3 BEKEND (NL-03a, KNOWN_BUGS 43), 0 NOK/FOUT, no previously OK check worse. Found: KNOWN_BUGS 78 (Resultaten... with X/Y axis; solved 15 Oct, `check_results_fit` rotates the frame back).
  Open: Mecway GUI test (show wheel, animation per mode). Questions to user: (1) make the
  scale of the shapes equal to Mecway (mass normalisation over the whole wheel; now
  that of REST_SOUS_STRUC)? (2) for a pair, also show the second member as an extra mode?

### S2 – Acoustics: cavity modes
**Goal:** Mecway *Acoustic Resonance* (manual §6.9, §9.34) via Code-Aster: eigenmodes
of an air or liquid volume with pressure nodes (p = 0) and impedance boundaries.
**Code-Aster:** `PHENOMENE='ACOUSTIQUE'`, `MODELISATION='3D'` (boundary: `3D_ABSO`), a
pressure formulation without coupling to the structure; `CALC_MODES` on the acoustic
matrices. Test cases: search for `ACOUSTIQUE` (e.g. `ahlv100a` for syntax). First read
the analysis type and the tags in Mecway (probably A30; not confirmed), plus the name
of the pressure field in Mecway's solution; modes as a list in the `.liml`
(reuse of the modal result route).
**Done when:** 3D tube with hard walls and open/closed ends: f_n = n·c/(2L) within
0.5%, and equal to headless Mecway for the same model (≤ 1%). The organ-pipe tutorial
(2D) only as an illustration.
**Findings:** Input route: Mecway itself (established headless with `mw_solve.py`):
`<analysis type="A30" maxmode="..">`, material `<mechanical type="Isotropic"
speedofsound="340 m/s" />` (density optional, Mecway solves without it),
`<fluidpressure selection=".."><value>0 Pa</value>` on nodes or faces (≠ 0 is rejected
by Mecway), `<impedance selection=".."><specificimpedancer>408</..><specificimpedancei>0</..>`
(number without unit; "Pa*s/m" is rejected by Mecway). Mecway's solution: per mode
`<mode frequency>` with the node variable `pressure`, normalised pᵀMp = 1 with
M = ∫NᵀN/c²; with impedance complex modes (`decayrate`, `pressure` + `pressurei`).
Mecway solves acoustics with **one** material (two: no solution). Built:
`bridge_acoustic.py` (parse + builder, dispatch in `_build_modal` on
`analysis["phenomene"]`), `AsterTemplate_Akoestiek.comm`, analysis `acoustic_modes_3d`
(A30), `PRES` → `pressure` in `aster_results_export`. Code-Aster: `NORM_MODE` does not work
for `MODE_ACOU` (the bridge scales with 1/√`MASS_GENE`, then equal to Mecway); hard
walls without a pressure node give `ALGELINE3_81` with `PLUS_PETITE` (bridge: `CENTRE` around
−0.1·c/(2D), alarm `ALGELINE3_82` harmless); `RIGI_ACOU`/`MASS_ACOU` do not contain ρ
(measured), so media with different densities give an ERROR. Verification AK-01..07
(`tests_akoestiek.py`, 78 checks OK): hex20 tube closed-closed and open-closed
≤ 0.017%, 3D room ≤ 0.026%, hex8/wedge6/tet4 ≤ 0.36% (Δf/f ≈ (kh)²/24), two media
≤ 0.024%; vs. headless Mecway < 4e-10 (frequencies and ∣p∣). Regression 447/450 OK,
3 BEKEND, 0 NOK/FOUT. **S2b (split off):** impedance not built (ERROR): `CALC_MODES`
does not take `MATR_AMOR` for pressure matrices, `AFFE_CHAR_ACOU` has no impedance,
`3D_ABSO` only ρc; route still to be researched (own quadratic eigenvalue problem in the
job, or projection onto real modes). Check case: tube hard/Z (real, Z > ρc) has
f_n = n·c/(2L) and decay rate (c/L)·artanh(ρc/Z). Open: Mecway GUI test (field `pressure`
per mode). Questions for the user: build impedance (S2b), and via which route? *Acoustic
displacement* wanted as a field? Media with different densities needed (then a different
formulation)?
**S2b (done):** Input route: Mecway's own *Impedance* (no new input). Mecway
(manual §6.9.2, checked headless) solves (K + λC + λ²M)P = 0 with C = ∫ρ/Z NNᵀdA,
Z = `specificimpedancer` + i·`specificimpedancei`, λ = iω − σ; without density ρ = 0
(impedance does not work: bridge ERROR); the 2 × maxmode smallest |λ|, of those f ≥ 0 (so
not always maxmode modes; 0 Hz modes random due to noise); shape scaled to
Euclidean norm 1 with a random phase. Route: (2) own quadratic problem in the
job, with scipy (included in Code-Aster's Python311, 1.16.2) instead of numpy only: Code-Aster
builds `RIGI_ACOU`/`MASS_ACOU` (= Mecway's K, M) and per boundary `AMOR_ACOU` with
`CELE_R = 1` (= ∫NNᵀdA, measured; other boundaries in that matrix `CELE_R` 1e30), the job
(`aster_acoustic_complex.py`) reads them with `getValuesWithDescription`, eliminates the
pressure nodes, linearises (2n) and solves shift-invert with ARPACK/`splu` (< 300
degrees of freedom dense). Route (1) projection onto real modes was dropped (truncation error,
complex C does not fit in `gene_r`), route (3) `3D_FLUIDE` too (spurious φ modes, no complex C).
Built: `bridge_acoustic._impedance_inputs`/`_complex_modes_comm`/`_write_modes_files`
(branch in `build_acoustic_modes`), `aster_acoustic_complex.py`, report per mode (decay
rate, T60, Q, residual WARNING) in `MecwayAsterBridgeMain._report_modes`, comparison with
Mecway at the nearest frequency (`bridge_from_aster`). Normalisation: phase with
PᵀMP real, PᴴMP = 1 (Z → ∞ = the real mode). Verification AI-01..10
(`tests_akoestiek_impedantie.py`, 227 checks OK): tube hard/Z real (Z = 2000, 200,
1e9, ρc), complex (2000 − 1000i, 1000 + 3000i, 1000i), pressure node/Z, hex8 (dense path),
room with two impedances; analytical (tanh(λL/c) = −ρc/Z) hex20 f ≤ 0.037%,
σ ≤ 0.14%, P(L)/P(0) ≤ 2e-8 (criterion 1%); vs. headless Mecway ≤ 1e-8 (f, σ and
P ratio/phase; criterion 1%); Z = ρc: all modes σ ≥ 1588 1/s (no resonance);
hex8: σ more sensitive to the mesh than f (+1.7% vs +0.41% at 340 Hz). Mecway's API reads
the modes (headless script: `modes()`, `frequency`, `node_value` of `pressure`/
`pressurei`). Run time 13,000 nodes/20 modes 14 s. Regression (`VERIF_WORK` own
folder): 1245 of 1248 checks OK (226 cases), 3 BEKEND (NL-03a), 0 NOK/FOUT, no
previously OK check worse; in `resultaten.*` only the AI cases. Limits: KNOWN_BUGS
55 (also: no MED/`res`, large model NOT verified). Open: Mecway GUI test (decay
rate under *Solution*, animation of a complex mode). Questions for the user: (1) always show 0 Hz
modes (constant pressure, non-oscillating) (now) or omit them? (2) number of modes
like Mecway (≈ maxmode, now) or exactly maxmode? (3) complex Z also in the harmonic
analysis (KNOWN_BUGS 57; now feasible with the same scipy route)?

### S3a – Acoustics: harmonic pressure field
**Goal:** pressure field per frequency for a source or imposed velocity, with absorbing
boundaries. **Code-Aster:** `ACOUSTIQUE` + `DYNA_VIBRA` (harmonic); test case `ahlv100a`
(runs: diagnosis OK).
**Input:** Mecway has no harmonic analysis (manual chapter 6): frequency range
on a page *Acoustics* in the main window + `#ASTER-OPTIE`; source/velocity via
Mecway boundary conditions or `#ASTER`; sound level in dB at "microphone" nodes via
`#ASTER-POST`. Results per frequency as steps (amplitude, phase, dB).
**Done when:** plane wave in a tube with an absorbing end: |p| constant and phase
linear, within 1% of the analytical solution; `ahlv100a` values on a 3D rebuild ≤ 1%.
**Findings:** Input route: the A30 model itself (Mecway has no harmonic
analysis, manual chapter 6) with its own analysis `acoustic_harm_3d` (page
*Acoustics (harmonic)*; `auto` picks it for A30 with a source) and special
selection names: face selection `BRON_`/`SOURCE_` (normal velocity `source_velocity`,
default 1 mm/s, into the fluid), `ABSORBEREND_`/`ABSORBING_` (rho-c boundary),
node selection `MICROFOON_`/`MICROPHONE_`; keyword `#ASTER-BRON selectie = v [,
fase]` (bridge_custom); Mecway's *fluid pressure* != 0 = imposed pressure, *impedance*
with real Z = absorbing boundary. Frequencies: `harm_freq_start/_end/_count/_spacing`
or `harm_freq_list` (also `#ASTER-OPTIE`). Built: `bridge_acoustic.build_acoustic_harm`
(dispatch in `bridge_to_aster._build_dyna_modal` on `phenomene`),
`AsterTemplate_AkoestiekHarm.comm`, `aster_acoustic_export.py` (in the job: per
frequency a `<mode frequency>` with `pressure`, `pressurei`, `pressuremag`,
`pressurephase`, `spl`; microphone CSV and `BRIDGE_MIC`), report in the log/status box
(`report_harmonic`). Code-Aster (route ahlv100a, measured): `VITE_FACE` requires the
source faces in the model with a material (`CALCUL_20`); `EXCIT` `COEF_MULT=+1`,
`PUIS_PULS=1`, `PHAS_DEG=90` gives p = +rho c v (v into the fluid; ahlv100a -1);
`3D_ABSO` damping = (1/c) int NN dA without rho, so Z becomes `CELE_R = Z/rho` (Z = 2 rho c:
reflection 1/3 measured); `CELE_I` does not give the reflection of a complex Z (ERROR,
KNOWN_BUGS 57); imposed pressure as a separate load vector without `PUIS_PULS`; a chain
`getField().toSimpleFieldOnNodes()` once gave `DVP_2` (FPE), separately not. SPL on the
effective (RMS) value (Code-Aster's `PRAC_ELNO` DB is 3.01 dB higher). Verification AH-01..08
(`tests_akoestiek_harmonisch.py`, 10 cases, 103 checks OK): (a) plane wave hex20 10
per wavelength |p| -0.018%, phase -0.011% (5 per wavelength -0.25% / -0.16%; hex8 10 per
wavelength +1.7% / -1.6%, 20 per wavelength +0.41% / -0.41%); (b) hard wall: |P - P_exact|
<= 1.2e-4 of max|P| (100/250/420 Hz); (c) ahlv100a 500 Hz: Re/Im within the
TEST_RESU precision of VALE_REFE (Im in NO751 +0.33%, Code-Aster itself too) and equal to
VALE_CALC (<= 1e-6), DB 109.887; CALC_MODES part of ahlv100a (8 modes) equal to
VALE_CALC; impedance Z = 2 rho c <= 7e-6; imposed pressure 2 Pa exact; `#ASTER-BRON` with 90
degrees and microphones (SPL 89.20 dB, phase 90 - kL within 0.02 degrees). Mecway's API reads the
frequencies and the five fields (headless script). Regression (`VERIF_WORK` own folder): 584 of 587 checks OK (135 cases), 3 BEKEND
(NL-03a, KNOWN_BUGS 43), 0 NOK/FOUT; in `resultaten.json` only the AH cases
updated. Open:
Mecway GUI test (list per frequency, contour of `spl`/`pressuremag`, animation of
`pressure` + `pressurei` without decay rate). Questions for the user: (1) build complex or
frequency-dependent impedance (own frequency loop with `COMB_MATR_ASSE` +
`RESOUDRE`)? (2) volume damping / porous materials needed? (3) SPL on the effective
value (now) or on the amplitude like Code-Aster? (4) frequency response also as a Mecway
graph (e.g. `<globalvariable>` per frequency) instead of CSV only?

### S3b – Vibroacoustics
**Goal:** structure and air/liquid coupled (vibrating panel in a room, tank
with liquid). **Code-Aster:** `PHENOMENE='MECANIQUE'`, `3D_FLUIDE`, `FLUI_STRU`
(coupling surface; there is no `3D_FLUI_STRU`), `3D_FLUI_ABSO`,
`FORMULATION='U_P_PHI'`. Test cases `adlv100a` (piston + liquid column, coupled
modes, analytical 13.8285 Hz) and `ahlv101a` (harmonic with absorption).
**Input (proposal):** air = part with Mecway's acoustic material or group name
`LUCHT_`; coupling surfaces automatic (faces shared by air and structure), `KOPPEL_`
as a manual choice.
**Done when:** `adlv100a` on a 3D rebuild within 0.5% of 13.8285 Hz; harmonic
coupling according to `ahlv101a` ≤ 1%.
**Findings:** Input route: a Mecway *Frequency* model (V30; Mecway has no
coupled analysis and solves acoustics with one material) with the fluid as its own
part: material with *Speed of sound* + *Density* without Young's modulus (Mecway's
acoustic material), or a part name `LUCHT_`/`VLOEISTOF_`/`FLUID_`;
coupling surfaces automatic (fluid faces that coincide with a face of a
structural solid element or with a shell), `KOPPEL_`/`COUPLING_` face selections as
a manual choice; p = 0 with node/face selections `OPEN_` (Mecway's *fluid pressure*
only exists for A30; if it is in the `.liml`, 0 counts). Analysis
`vibroacoustic_modes_3d` (page *Vibroacoustics (modes)*, `auto` picks it for V30 with
a fluid; elsewhere a WARNING), setting `vibro_freq_min` (0.1 Hz). Built:
`bridge_vibroacoustic.py` (parse, coupling surfaces, builder, report),
`AsterTemplate_VibroAkoestiek.comm`, step 2c in `bridge_mesh.write_mesh` (boundary elements
`BRFSI<k>`), dispatch in `_build_modal` (analysis `"vibroacoustic"`), `FIELD_TABLE`
`pressure` from `DEPL`/`PRES`. Code-Aster (measured): `FORMULATION='U_P_PHI'`
(default, symmetric); every φ degree of freedom gives a spurious mode at 0 Hz
(`PLUS_PETITE`: `ALGELINE3_81`; `CENTRE`: the spurious modes first), so `INFO_MODE`
(Sturm count is correct) searches a band from `vibro_freq_min`, `CALC_MODES BANDE`
(`COEF_DIM_ESPACE` 4), filter on f and `MASS_GENE` > 0 (a spurious mode with
`MASS_GENE` < 0 gave `DVP_2` during normalisation), `EXTR_MODE`, `NORM_MODE MASS_GENE`; `U_P`
gave a wrong series / `JEVEUX_26`, `U_PSI` does not know `DDL_IMPO PRES`. The density
is in the matrices (unlike `ACOUSTIQUE`, KNOWN_BUGS 55): bar + water with ρ 1000
and 1 each gave their own analytical frequencies; two fluids with shared nodes and a
different density gave 188.23 instead of 306.47 Hz (φ continuous): ERROR. Coupling surfaces
`ORIE_PEAU` with `GROUP_MA_INTERNE` = fluid; shell + coupling surface give the alarm
`MODELISA4_8`/`8_13` (duplicate cells, harmless; explanation in `bridge_run_aster`).
Verification VA (`tests_vibroakoestiek.py`, 8 cases, 29 checks OK): (a) adlv100a 3D
(hex20) 13.82767 Hz: −6.0e-5 vs. VALE_REFE 13.8285 (= the low-frequency approximation),
−9.8e-7 vs. the exact root, mode 2 +5.1e-5, p/u on both piston faces 2e-6, also
with `KOPPEL_` (VA-01k); (b) elastic bar + water column (Zs·cot + Zf·cot = 0) 4 modes
≤ 2.4e-5 (criterion 1%); shell piston (DKT) on an air column ≤ 6.6e-4; tube of two
media (equal ρ) ≤ 8.6e-5; panel on an air cavity with 1000× lighter air = separate plate
and cavity modes ≤ 0.61% (DKT discretisation), with ordinary air pumping mode +8.8% (−0.48%
vs. the one-mode approximation); `#ASTER-OPTIE vibro_freq_min` (example 14). Official
test cases adlv100a and ahlv101a run (ctest, no NOOK). Mecway's API reads frequencies,
`displ` and `pressure` per mode (headless script on VA-01). Regression (`VERIF_WORK`
own folder): 651 of 654 checks OK (151 cases), 3 BEKEND (NL-03a), 0 NOK/FOUT, no
previously OK check worse; then VA-05c added (657/654). (c) Harmonic not built:
**split off as S3c** (`DYNA_VIBRA HARM` on the coupled matrices, `3D_FLUI_ABSO` with
`IMPE_MECA`/`ONDE_FLUI` → `MATR_IMPE_PHI`, source as a force on the structure, `VITE_FACE`
or incident wave; done when: ahlv101a on a 3D rebuild ≤ 1% and a harmonically
driven piston + column ≤ 1%). Limitations: KNOWN_BUGS 59; a material without E
is computed by the bridge as steel, by Mecway as E = 0 (KNOWN_BUGS 60). Open: Mecway GUI test
(modes with `displ` and `pressure`, contour and animation). Questions for the user: (1) is the
input via the material (Speed of sound without E) + `OPEN_` workable, or rather an
`#ASTER` keyword? (2) air above water (two densities) needed? Then build a
coupling surface between the fluids; (3) sloshing (gravity on the free surface)
wanted? (4) S3c (harmonic) as the next step?

### S3c – Vibroacoustics harmonic
**Goal:** harmonic response of a coupled structure-fluid model (vibrating
panel radiating sound, piston on an air column with an absorbing end): per
frequency displacements in the structure and pressure/SPL in the fluid, with
absorbing boundaries (`3D_FLUI_ABSO`), sources and microphones. **Code-Aster:**
`DYNA_VIBRA` `HARM` on the coupled `U_P_PHI` matrices with `MATR_IMPE_PHI`; test case
ahlv101a.
**Done when:** ahlv101a (TEST_RESU) within 1% on a 3D rebuild; piston (mass-spring) on
an air column with a ρc end: u = F/(k − mω² + iωρcA) and the pressure within 1%; regression
according to D.5.
**Findings:** Input route: the same Mecway *Frequency* model as S3b (fluid
part, coupling surfaces automatic/`KOPPEL_`, `OPEN_`) with its own analysis
`vibroacoustic_harm_3d` (page *Vibroacoustics (harmonic)*, chosen by the user; `auto`
stays with the modes of S3b). Sources: Mecway loads on the structure (amplitude,
`#ASTER-FASE`, table = amplitude versus frequency, as in S10h), face selections
`BRON_`/`SOURCE_` (velocity into the fluid, `source_velocity`) and new
`INVALLEND_`/`INCIDENT_` (incident wave, new setting `incident_pressure`, 1 Pa),
`#ASTER-BRON` with a velocity or (new) a pressure unit = incident wave; boundaries
`ABSORBEREND_` (ρc) and Mecway's *impedance* (real, `CELE_R = Z/ρ`); `MICROFOON_`
(pressure/SPL, CSV as in S3a), `MEETPUNT_` (displacement, CSV as in S10h); frequencies
`harm_freq_*` (20–500 Hz, 50). Built: `bridge_vibroacoustic_harm.py` (builder and
report; dispatch in `_build_dyna_modal` on `vibroacoustic` + `type_calcul` HARM),
`AsterTemplate_VibroAkoestiekHarm.comm`, `aster_harmonic_export` extended with
`pressure=True` (fields `pressure`, `pressurei`, `pressuremag`, `pressurephase`, `spl`
from component `PRES` of `DEPL`) and microphones (route of `aster_acoustic_export`);
`parse_vibro` keeps the roles of the special selections and the impedance values.
Chosen route: direct (`BASE_CALCUL='PHYS'`): `U_P_PHI` has spurious modes at 0 Hz, the
absorption is not proportional, and ahlv101a/ahlv100b compute this way. Code-Aster (measured):
`ONDE_FLUI` with `PRES` gives an incoming wave `PRES`/2 and lets the reflected
wave through (the bridge writes 2 × `incident_pressure`); `VITE_FACE` in `U_P_PHI` gives with
`COEF_MULT=+1` p = −ρcv (the bridge: −1, v into the fluid); `IMPE_MECA` rejects `CARA_ELEM`
(`SUPERVIS_4`: own `ASSEMBLAGE`), `AMOR_MECA` with `GROUP_MA` gave `DVP_1` (so on the whole
model with `AMOR_FLUI='NON'`); Rayleigh only on the structure (`RIGI_MECA`/`MASS_MECA`
with `GROUP_MA`); `DYNA_VIBRA AMOR_FLUI='NON'` with `MATR_AMOR` + `MATR_IMPE_PHI` (as in
`DYNA_LINE`). Verification VH (`tests_vibroakoestiek_harmonisch.py`, 13 cases, 175
checks): (a) ahlv101a 3D (incident wave + absorbing outlet): VALE_REFE
≤ 8.0e-4 (PRECISION 1e-3), VALE_CALC ≤ 1.3e-7; ahlv100b (velocity source) VALE_REFE ≤
8.9e-4, VALE_CALC ≤ 2.3e-7; `#ASTER-BRON` with phase (×i, ×e^{−i30°}) ≤ 2.3e-7; (b) piston
(m 0.05 kg, k 3000 N/m, ζ_radiation 0.17) on an air column with a ρc end: U ≤ 1.3e-4,
phase ≤ 7e-4°, pressure ≤ 2.9e-5 of the hand formula over 5–200 Hz (criterion 1%); with Z =
2ρc ≤ 1.2e-4, with Rayleigh α/β and a damper ≤ 1.3e-4, with a force table + phase ≤
1.3e-4, shell piston (DKT, hex8 air) U ≤ 2.5e-4, p ≤ 3.3e-3; incident wave on a
hard wall / `OPEN_` ≤ 1.2e-4. Mecway's API reads the result (headless script on
VH-02: 8 frequencies, `displx`/`displix`, `pressure`/`pressurei`/`spl`). Regression (`VERIF_WORK`
own folder, groups after Welding in parallel): 1193 of 1196 checks OK (229 cases), 3 BEKEND
(NL-03a, KNOWN_BUGS 43), 0 NOK/FOUT, no previously OK check worse; in
`resultaten.json` only the VH cases updated. Found (KNOWN_BUGS 74, not fixed): in
`acoustic_harm_3d` `#ASTER-BRON .. = 2 Pa` silently becomes 2 m/s and text without a number 0 m/s.
Limitations: KNOWN_BUGS 59. Open: Mecway GUI test (list per frequency with
displacement and pressure, contour of `spl`, animation). Questions for the user: (1) `auto` for
V30 + fluid + source (`BRON_`/`INVALLEND_`/`ABSORBEREND_`) to the harmonic analysis
(now: modes, chosen by the user)? (2) build complex or frequency-dependent impedance
(own frequency loop with `COMB_MATR_ASSE` + `RESOUDRE`)? (3) Rayleigh damping also on the
fluid (now only the structure)? (4) the radiated power or the intensity on a
surface (`CALC_CHAMP` `INTE_ELNO`) as a result? (5) a modal basis (GENE) for large
models with many frequencies (requires the `BANDE` search of S3b and static
enrichment)?

### S4a – Welding: transient thermal with a moving source
**Goal:** temperature field of a weld bead. Builds on `bridge_thermal.py` (T31).
**Research:** a moving source (Goldak double ellipsoid or a simpler
Gaussian source) as a Mecway formula in x, y, z, t first required KNOWN_BUGS 45 (x/y/z formulas
→ ERROR; fixed in the meantime); otherwise an `#ASTER` keyword (weld path, speed, power, dimensions).
Analysis choice: `auto` sends T31 to `ther_3d`; welding is chosen by the user on the page
or via `#ASTER-OPTIE`.
**Done when:** quasi-steady peak temperature outside the fusion zone within 5% of
Rosenthal (point source on a thick plate).
**Findings:** Input route (docs/Lassen.md): (A) `#ASTER-LASBRON` in Mecway's custom
model definition (`bridge_welding.py`): Goldak double ellipsoid (af, ar, b, c or r;
ff/fr continuous by default), Q, η, v, straight path (`start`, `richting`, `lengte`) or
`pad=<<knoopselectie>>` (piecewise straight), `diepte`, `t0`/`t1`, `groep` (default
selections/components with `LASNAAD_`, otherwise automatic within 3× the largest semi-
axis), `symmetrie`. In the .comm a Python function + `FORMULE(X, Y, Z, INST)` +
`AFFE_CHAR_THER_F SOURCE`; after the solve an energy check in the job (`CALC_VECT_ELEM`
`CHAR_THER`: absorbed power, line `BRIDGE_LASBRON`, status box). Messages:
v·Δt > ½(af + ar), element > 0.8× the semi-axis, absorbed power off by > 2%. (B)
Mecway formulas in x, y, z, t for all thermal loads (then KNOWN_BUGS 45, thermal
fixed, mechanical later too; Mecway's internal solver also solves such a model). No separate analysis: T31 →
`ther_3d` (also `auto`). Temperature-dependent λ/c were not translated: XML read
from a model saved with Mecway (script `mw.set_material_type(.., "TempDependent")`),
now `THER_NL` + `THER_NON_LINE`; found: Code-Aster interpolates the enthalpy
linearly between the `RHO_CP` table points (13% energy lost after the first step), the bridge
extends and refines the table. Verification WE-01..06 (`tests_lassen.py`, 53
checks): Rosenthal −0.94..+0.90% (tolerance 5%; with v·Δt at the message limit
3.6%), Goldak analytically folded ≤ 1.2%, energy balance ≤ 0.06% (tolerance 2%),
absorbed power ≤ 0.09%, λ(T) exact (Kirchhoff, Mecway too), energy with c(T)
0.003%, formulas in temperature/convection/flux equal to Mecway (5e-15). Mecway
headless with the source as a formula: energy equal (1e-9), temperatures −2.9/+1.6%
due to Mecway's load at the end of the step (KNOWN_BUGS 14). Regression 456/459 OK,
3 BEKEND (NL-03a, KNOWN_BUGS 43), 0 NOK. Limitations: KNOWN_BUGS 56. Open:
Mecway GUI test (text in Custom model definition, status box). Questions for the user: (1)
normalise the source to the absorbed power (now only reported)? (2) a dedicated
page in the main window for the welding source instead of `#ASTER`? (3) other source shapes
(conical, surface Gaussian) as a key? (4) a larger time step for the
cooling phase (now one fixed step)?

### S4b – Welding: thermal → mechanical chain
**Goal:** residual stress and distortion. One template with `THER_NON_LINE` and
`STAT_NON_LINE` (`AFFE_VARC` `TEMP` with `EVOL_THER`), equal time steps.
**Research:** temperature-dependent E, yield strength and α: Mecway supports
temperature dependence only for conductivity and specific heat (manual
§8.6), so via an `#ASTER` keyword or table (document it).
**Done when:** (1) freely expanding bar with uniform ΔT: strain α·ΔT exact (≤ 0.1%);
(2) fully restrained bar: σ = −E·α·ΔT up to the yield strength (≤ 1%); (3) weld bead on
a plate: residual stress pattern (tension in the weld, compression next to it) qualitatively, with the
measured values in the doc.
**Findings:** Input route (docs/Lassen.md §9): no separate analysis and no
setting: a *Thermal stress* in a T31 model switches the chain on (Mecway keeps
Thermal stress, Fixed support and Displacement in a thermal model too; checked headless
with Mecway 33: they remain in the saved `.liml` and the thermal part
solves without a message). `auto` → `ther_3d`; `bridge_from_liml` then reads the
mechanical conditions, `bridge_thermomech.py` builds after the thermal solve (own
template `AsterTemplate_ThermoMeca.comm`) `STAT_NON_LINE` with `AFFE_VARC` `TEMP`
(`EVOL` = thermal result, `VALE_REF` = reference temperature, in °C), at the
thermal times (`ARCHIVAGE` at the same times: temperature and stress per step in
Mecway). Temperature-dependent E, ν, α, SY and H/ET via `#ASTER-MATERIAAL <Mecway-
materiaal>: TC=(..), E=(..), ...` (`ELAS_FO`, `ECRO_LINE_FO`; α = secant relative to
`T_ALPHA`; `TC_CUT`: thermal strain constant above the melting temperature); without the line
the constant Mecway values incl. bilinear/hardening curve. New settings in
`ther_3d`: `deformation` (PETIT), `plastic_strain_definition`. Verification WE-07..10
(`tests_lassen_mech.py`): free expansion, uniaxially restrained with bilinear
hardening and residual stress after cooling back, E(T)/SY(T)/α(T) with reverse yielding:
all ≤ 4·10⁻⁸ vs. the hand calculation (tolerance 0.1% / 1%). Weld bead WE-10 (hex8):
equilibrium N 0.02% / M 1% of SY·A, yielding in the weld (von Mises = SY + H·p, 0.2%),
tension in the weld, compression next to it, angular distortion 8.9 mrad towards the weld side, longitudinal and
transverse shrinkage (0.077 mm, upper bound α·q/(v·ρ·c·t) = 0.103 mm). Found: linear hex8
locks with plasticity (σxx in the weld 1.3–2.6 × SY, triaxial; WARNING, advice
LINE_QUAD); with LINE_QUAD Newton diverged without line search (now `RECH_LINEAIRE`
with plasticity) and without capping the thermal strain above the melting temperature
(4.6% at 3400 K; now `TC_CUT`); WE-10b (LINE_QUAD, 53 min, only with
`VERIF_ZWAAR=1`): longitudinal stress in the weld 400–450 MPa = SY + H·p (1.13 × SY), σzz ≈ 0, equilibrium 0.05%, angular distortion 12.4 mrad. Mecway's *Displacement* is one direction (LIAISON_OBLIQUE for x and z):
a separate condition per direction (in the doc). Limitations: KNOWN_BUGS 64. Open:
Mecway GUI test (add and show Thermal stress/Fixed support in a T31 model,
results per step). Questions for the user: (1) a larger time step for cooling (one
Mecway *Time step* makes long cooling expensive); (2) temperature-dependent
hardening curve (`TRACTION` per temperature) needed?; (3) the list of `#ASTER-MATERIAAL`
rather as a dedicated page/table in the main window?; (4) LINE_QUAD by default in the chain
with plasticity (more accurate, ~5× slower)?

### S4c – Welding: filler material
Let elements be "born" (group name `LASNAAD_`) or simplify (present from the
start, soft above the melting temperature). Research what Code-Aster can do; choose
and document the limitation. **Done when:** a bead in two layers gives a
plausible temperature history and no stress in not-yet-"born" material.
**Findings:** Input route (docs/Lassen.md §10): key `geboorte=ja` or
`geboorte=<<selectie>>` (+ `voorloop`, default 2 × af) in `#ASTER-LASBRON`; the
filler material is the `LASNAAD_` selection/component (ja) or the named selection, the
source then automatically acts on all elements along the path. Code-Aster 17.4 has no
element birth (catalogue and test cases searched); chosen: the "quiet
element" method: before birth ρ·c × 1e-4, λ × 1e-8, E (and hardening) × 1e-4,
no source. Birth time per element from the arc length of its rearmost node along the
path (the same code in the .comm and the bridge, `exec`), quantised per time step.
Thermal: `THER_LINEAIRE` with `THER_FO` of `INST` and `NEUT1` (CART, test cases
ttnp201a/ssnp160a); with λ(T)/c(T) or radiation, `BETA`/`RHO_CP` of `THER_NL` may not be a
formula or nappe (`MODELISA6_31`/`58`): `THER_NON_LINE` per birth step with a
quiet `THER_NL` material (in a prototype equal to the first route to within 1e-6);
filler material with `3D_DIAG`. Mechanical: `STAT_NON_LINE` per birth step with a
new `AFFE_MATERIAU`, `ETAT_INIT` with stress and internal variables of the new
elements at zero, `PREDICTION='ELASTIQUE'`: stress-free in the deformed position at the
temperature at the start of the birth step (also LINE_QUAD, bilinear and
hardening curve). Found and fixed: (1) Code-Aster 17.4 computes two loads
`AFFE_CHAR_THER_F` with `SOURCE` in one list both with the function of the first (the
second `#ASTER-LASBRON` from S4a thus never worked): all welding sources now in one load
(KNOWN_BUGS 70; Mecway formula sources not yet at first, WARNING next to a welding source; later
fixed: all function sources in one load, TH-40..42, KNOWN_BUGS 70 removed); (2) with
the consistent heat capacity a quiet node followed its warm neighbours via the mass coupling
(+138 K): `3D_DIAG` in the filler material; (3) due to rounding the source was sometimes off at t_end:
margin 1e-9. Verification WE-11..13 (`tests_lassen_geboorte.py`,
37 checks): (a) bead in two pieces: energy of the living volume +1.2..1.6%
vs. the θ scheme (tolerance 2%; birth brings along the heat of the nodes on the
interface), in the unborn piece T0 + 0.5 K, also with c(T) (WE-11b); (b) bar
born halfway: stress in the unborn part 1.8e-4 × E·α·ΔT (tolerance 1e-3),
shrinkage stress relative to the birth temperature −0.01% (1%), bilinear and hardening curve
0.00%; (c) two layers (chain): layer 1 melts (2,690 K), cools down (530 K), is
reheated (1,750 K); layer 2 before birth 4.7e-4 × SY and T0 + 0.03 K;
residual stress in equilibrium (−0.25% SY·A), tension in the bead, compression next to it (5.5 min).
Regression 1018/1021 OK, 3 BEKEND (NL-03a, KNOWN_BUGS 43), 0 NOK/FOUT; no previously OK check changed (WE-01..10 equal). Limitations: KNOWN_BUGS 71 (58 and 64 updated). Open: Mecway GUI test (selection
`LASNAAD_`, line in Custom model definition, quiet elements in the results).
Questions for the user: (1) also merge the Mecway formula sources (*Internal heat generation* with a formula)
into one load (KNOWN_BUGS 70; done in the meantime)? (2) mechanically stress-free at the
solidus temperature (during cooling) instead of at the arrival of the source? (3)
the factors of the quiet material (1e-4) as a key? (4) let filler material beyond
the end of the path (now never born, WARNING) be born anyway?

### S6a – Fracture mechanics: meshed crack
**Code-Aster:** `DEFI_FOND_FISS`, `CALC_G`, `POST_K1_K2_K3`; 3D test case `forma07a`
(`forma05a` is D_PLAN: syntax only). **Input:** crack front and lips as
group names (`SCHEUR_FRONT`, `SCHEUR_LIP_BOVEN`/`_ONDER`). Output: K and G along the
front in the log and as a table.
**Done when:** thick plate with a through centre crack under tension: K_I within 3% of
σ·sqrt(πa)·F(a/W) (Tada/Roark), and G = K²/E' consistent.
**Findings:** Input route: Mecway has no fracture mechanics; the crack is opened
with *Disconnect elements* + *Merge nearby nodes* on ligament and front (manual
v33 §4.2.10/4.2.11) or as a half model with symmetry. Special selection names:
node selection `SCHEUR_FRONT`/`CRACK_FRONT`, face selections `SCHEUR_LIP_BOVEN`/`_ONDER`
(`CRACK_LIP_UPPER`/`_LOWER`); without a lower lip `SYME='OUI'`; more cracks with a
suffix. `bridge_fracture.py`: front as SEG2/SEG3 (`BRSCHEUR<n>`, edges with
both nodes in the selection, check for a single line and open lips), after the result
export `DEFI_FOND_FISS` + `CALC_G` `OPTION=('G','K')` + `POST_K1_K2_K3` on a separate
result (material on all cells: otherwise `CALCUL_20` on the lips; `SIEF_ELGA`:
otherwise `RUPTURE0_94`), `FORM_FISS='CERCLE'` for a circular front. Output:
`<model>_<run>_scheur.csv`, log and status box; no field. Settings
`fracture_r_inf`/`_r_sup` (0 = Code-Aster: 2h/4h), `fracture_smoothing`,
`fracture_legendre_degree`. Verification BR-01..06: K_I (`CALC_G`) −0.10 % vs. Tada
(plane strain, hex20, h = a/40), G −0.41 %, G/(K²/E') 0.998; half model equal;
thick plate mid-plane +0.7 %; forma07a K1 MAX exact (1,607,011.55), G +0.8 %; hex8
K −0.7 %, G −2.0 %; two cracks with suffix (_L/_R) per front as BR-01.
`POST_K1_K2_K3` without quarter points −3.5 % (hex20) / −10 % (hex8).
Regression (own VERIF_WORK): 727 of 730 checks OK (165 cases), 3 BEKEND
(NL-03a), 0 NOK/FOUT; no previously OK check changed. Not: nonlinear, contact
on the lips, K as a field,
quarter-point nodes by the bridge (the result export checks the coordinates),
XFEM (S6b); NOT verified: closed front, tet10, interface, thermal strain, pressure
on the lips, the GUI procedure (KNOWN_BUGS 63). **Open questions:** (1) K/G as a field on
the front nodes in Mecway wanted? (2) Quarter-point nodes as an option (requires an
exception in the node check of `aster_results_export`)? (3) Does *Disconnect
elements* + *Merge nearby nodes* with a node selection work in the GUI as the manual
says?

### S6b – Fracture mechanics: XFEM
Crack without remeshing via level sets (`DEFI_FISS_XFEM`), input via `#ASTER`.
**Done when:** same case as S6a within 5%.
**Findings:** Input route: Mecway has no crack input; a dedicated keyword
`#ASTER-XFEM vorm=CIRKEL|ELLIPSE|RECHTHOEK|HALFVLAK, ...` (`bridge_custom` kind
`-XFEM`, worked out in `bridge_xfem.py`; English keys work too; lengths in m or
with a unit; a line with `vorm=` starts a new crack; `groep=<<elementselectie>>`
→ `GROUP_MA_ENRI`). No group-name route: the shape needs dimensions, a selection does not
give them. Settings as in S6a (`fracture_r_inf`/`_sup`, per crack `r_inf=`/
`r_sup=`), plus per crack `glad`, `graad`, `punten` (NB_POINT_FOND). Translation: the
bridge's model is called `model_sain`, `DEFI_FISS_XFEM` + `MODI_MODELE_XFEM` → `model`
for loads and `MECA_STATIQUE`; then `POST_MAIL_XFEM` + `POST_CHAM_XFEM` and
`PROJ_CHAMP` `COLLOCATION` back to the Mecway nodes (DEPL, SIGM_NOEU, SIEQ_NOEU,
physical per side of the crack; REAC_NODA from the XFEM result), so that the normal
export to Mecway works; after the export per crack and per front (`NUME_FOND`,
`getCrackTipMultiplicity`) `CALC_G_XFEM` `CALC_K_G` and `POST_K1_K2_K3`, table
`<model>_<run>_xfem.csv`, log and status box. Checks up front: only solid elements
with `3D` (ERROR), the crack must cut elements and have a front in the model
(ERROR, often mm instead of m), mesh advice (WARNING above a/10). Found while
verifying: (1) *Symmetry* as `LIAISON_OBLIQUE` does not fix the XFEM degrees of freedom of
cut elements (forma07b K1 MAX +3.8 % at the symmetry plane): with XFEM
a symmetry along a global axis becomes `DDL_IMPO` (then exact), oblique on such
nodes a WARNING; (2) hex20 works (quadratic XFEM elements, alarm XFEM_63), no
ERROR needed; (3) `LAGRANGE` oscillates on a curved front (irregular intersection points),
`LEGENDRE` ≥ 2 on a short straight front: default per shape; (4) `CALC_G_XFEM` has no
curvature correction (penny +5.3 %): WARNING, use `POST_K1_K2_K3` or G. Verification
BR-07..12 (tests_breukmechanica_xfem.py): plate of BR-01 with HALFVLAK, hex8 h = a/20:
K_I −0.08 %, G −0.18 %, POST_K −0.24 % (done criterion 5 %); hex20 +0.10 %; crack plane
through nodes −0.06 %; two fronts (RECHTHOEK) −0.09 %; penny crack K_I POST_K +1.6 %,
from G +1.0 %, CALC_G_XFEM +5.3 %, opening +3.3 % (Sneddon); forma07b via the bridge K1
MAX CALC_G_XFEM and POST_K equal to the TEST_TABLE (< 1e-6). Regression (own VERIF_WORK on D:): 1047 of 1050 checks OK (222 cases), 3 BEKEND (NL-03a), 0 NOK/FOUT; no previously OK check changed. Not:
contact on the lips, crack growth (PROPA_FISS), FONC_LN/FONC_LT, shells/beams in the
model, error estimator and fatigue together with XFEM, SIGM_ELNO in Mecway; NOT
verified: tet10/wedge15/pyr13, `groep=`, ELLIPSE with a ≠ b, multiple XFEM cracks in
one model, REAC_NODA on cut elements (KNOWN_BUGS 63). **Open questions:** (1) A
MED file with the mesh of POST_MAIL_XFEM (the crack visible in ParaView) wanted as an
option? (2) Should `groep=` also pick up an `XFEM_` element selection automatically?
(3) Crack growth (`PROPA_FISS`, fatigue crack growth) as a follow-up step?

### S7 – Adaptive refinement
**Two routes, Mecway first:** (1) Mecway's own `mw.refine_x2(element_ids=…)` on the
elements with the largest error from S1: selections and boundary conditions stay intact,
loop from the main script; (2) HOMARD (`MACR_ADAP_MAIL`; works on this installation,
`forma01b` diagnosis OK) inside Code-Aster. A HOMARD mesh cannot come back via the current
result route (`export_results` checks the node order against the `.liml`):
then write a new model or choose route 1. 3D test cases `sslv110f`, `sslv319a`.
**Done when:** plate with a hole under tension (finite width): Kt within 2% of
Peterson/Heywood after the refinement loop, with fewer elements than uniform refinement.
**Findings:** Route (1) built, HOMARD not (docs/Foutschatter.md §6.6: works in
3D on this installation, sslv110f run, but the mesh cannot go back to Mecway
without a new `.liml` with all selections/loads). `Scripts/bridge_adapt.py`: after the
run `after_run` (error per element from the result file, `ERME_ELNO`; choice Dörfler
0.5 / fraction / factor; stop at target, max. loops, max. elements (growth of the
previous loop), rising error; ERROR if a node selection with a condition lies on an edge to be
refined; WARNING for flat hex), `refine_in_mecway` (`mw.refine_x2`); loop
in `MecwayAsterBridgeMain.main()` (`_adapt_step`, copy of the original model
`_voor_verfijning.liml`, each loop an OK click). Settings (page Static,
`#ASTER-OPTIE`): `adapt_refine` (off), `adapt_target_error` 2%, `adapt_max_loops` 5,
`adapt_select` dorfler, `adapt_fraction` 0.5, `adapt_neighbours` off,
`adapt_max_elements` 200000. Measured headless (`mecway.exe <model> script`): refine_x2
keeps the mesh conforming (transitions pyr/tet/wedge), face and element selections and
parts follow, node selections do not; hex20 follows a curved edge, hex8 does not;
pyr13 order of bridge_mesh confirmed. **S1 bug found and fixed:** `ERME`
computes `FORCE_FACE` with the opposite sign (uniform tension: 15% instead of 0); the bridge reverses
it in the load of the estimator (FS unchanged: tangential does not count). Verification
(`tests_adaptief.py`, AD): plate with hole d/W = 0.2, hex20, slice in plane strain; uniform
AD-01 n = 1…32 −27.2…−0.14% (Peterson 2.519); loop AD-02 (target 1.5%, headless Mecway): 5
loops, global error 4.57 → 1.11% decreasing every loop, Kt +0.82% with 15,810 elements, uniform
Refine x2 to 2%: 49,152 (factor 0.32), 98% of the refinement within 3r of the hole;
AD-03 node selection → ERROR. Outside the regression: thin plate (aspect 1:40) and tet10
give poor transition elements and a rising estimate after 1-2 loops (loop stops).
Limitations: KNOWN_BUGS 65 (and 51). `#ASTER-OPTIE` example 18. Regression (`VERIF_WORK` own folder): 767 of 770 checks OK
(175 cases), 3 BEKEND (NL-03a), 0 NOK/FOUT, no previously OK check worse (FS-01 different by ≤ 3e-4 due to the
sign correction); in `resultaten.json` only the AD cases updated. Open: Mecway GUI test (loop with OK clicks, status box).
Questions for the user: (1) each loop requires an OK click; automatic waiting for Code-Aster in
the loop wanted? (2) default target 2% (energy norm) or lower for peak stresses? (3) for
tet meshes rather re-automesh with Mecway's refinement points (`automesh_3d`
`refinements`) than `refine_x2`? (4) build the HOMARD route after all (write a new `.liml`)?

### S8 – Fatigue
**Code-Aster:** `POST_FATIGUE`, `CALC_FATIGUE` (rainflow, Wöhler, Miner; multiaxial).
Test cases `szlz100a`, `sslv135a` (runs: diagnosis OK).
**Research:** Wöhler curve (no Mecway input: `#ASTER` keyword or table);
load history (time steps of a nonlinear/dynamic run, or two
load states); damage/life as a field.
**Done when:** constant amplitude: damage exactly according to Miner (≤ 0.1%); a
two-level spectrum recalculated by hand (≤ 0.1%).
**Findings:** Mecway has no fatigue (manual and `mecway.exe`: no
fatigue/S-N/Wöhler). Input route: `#ASTER` lines (no settings in the
main window, model data like `#ASTER-LASBRON`): `#ASTER-WOHLER materiaal: K=V`
(table `S = [..] MPa, N = [..]` log-log or `INTERPOL = LIN`, power form `S, N, m`,
Basquin `Sf, b`; `Se`, `PROL_GAUCHE` EXCLU/CONSTANT/LINEAIRE, `PROL_DROITE`,
`correctie` GOODMAN/GERBER with `Su`; `*` = other materials), `#ASTER-VERMOEIING`
(`spanning` VMIS_SG/PRIN, `telling` RAINFLOW/ASTM, `herhalingen`), and for linear
static `#ASTER-BLOK a, m, n` (factors on the static stress) or `#ASTER-SIGNAAL
f1, f2, ...`; for `STAT_NON_LINE`/`DYNA_NON_LINE` the time steps are the signal.
Built: `bridge_fatigue.py` (parse, block in the `.comm`, report), job module
`aster_fatigue.py` (σ_eq from `SIGM_NOEU`, rainflow, Wöhler, Miner, cycle table
`<model>_<run>_vermoeiing.csv`, lines `BRIDGE_VERMOEIING_*`), `node_fields` in
`aster_results_export.export_results` (fields `damage`, `life` = repetitions until D = 1,
max. 10¹²; with a time history equal in every step), hook in `_build_lin_static` and
`_build_nonlin_static`, report in the status box (WARNING at D ≥ 1). Measured in
Code-Aster 17.4: S of `WOHLER` is the amplitude; `POST_FATIGUE`/`CALC_FATIGUE`
`RAINFLOW` counts periodically (ASTM signal → 4 closed cycles; szlz105a); Goodman/Gerber
take the sign of S_m into account; Basquin `A_BASQUIN`: 1/N = A·S^β; below the table with
`EXCLU` D = 0, above it an error; `PROL_*='LINEAIRE'` extrapolates linearly in (S, N) in the
fatigue routines, also with `INTERPOL='LOG'` (negative damage above the table),
while the function itself gives log-log: the bridge extrapolates log-log (documented
deviation). Own rainflow instead of `CALC_FATIGUE` because `CUMUL_DOMMAGE` has no blocks,
no mean-stress correction and only one material; equal to Code-Aster.
Verification VM-01..07 (`tests_vermoeiing.py`, 14 cases, 24 checks): (a) constant
amplitude table/Basquin/power form with Se ≤ 2·10⁻¹⁴ (criterion 0.1 %); (b)
two-level spectrum (table; Basquin + Goodman, 5 repetitions) ≤ 6·10⁻¹⁴; (c) ASTM
E1049: cycles exact (0.5/1.5/0.5/1/0.5), damage 1·10⁻¹⁴, periodic equal to
`POST_FATIGUE` 2·10⁻¹⁴; (d) szlz105a 3D (nonlinear static) 3·10⁻⁶ of `VALE_REFE`
and equal to `CALC_FATIGUE` (0), szlz100a 3D (no correction/Gerber/Goodman) ≤
5·10⁻⁸; sslv135a (`FATIGUE_MULTI`, critical plane) not rebuilt: multiaxial criteria
not built (split off as **S8b**); dynamic (`DYNA_NON_LINE`) equal to
`CALC_FATIGUE` 2·10⁻⁸; VMIS_SG/PRIN biaxial exact. Mecway's API reads `damage`/`life`
(headless script, static and 101 time steps). Regression (`VERIF_WORK` own folder on D:): 978 of 981 checks OK (204 cases), 3 BEKEND (NL-03a, KNOWN_BUGS 43), 0 NOK/FOUT, no previously OK check worse; in `resultaten.json` only the VM cases added. Limitations: KNOWN_BUGS
66. Open: Mecway GUI test (contour of `damage`/`life`, text in Custom model
definition, status box). Questions for the user: (1) `life` capped at 10¹² (now) or a
dedicated "infinite" value/log10 field? (2) count mean compression in Goodman as a benefit
(now, like Code-Aster) or set it to 0? (3) `PROL_DROITE` extrapolate by default
(now, with WARNING) or stop like Code-Aster? (4) S8b (multiaxial,
shells, Manson-Coffin) or vibration fatigue on a modal basis/harmonic needed?

**Findings S8b** (7 Oct 2026): input route an extension of the existing lines
(no settings in the main window): `#ASTER-VERMOEIING criterium = DANG_VAN|MATAKE|
CROSSLAND|FORMULE, a = .., b = .. MPa, c = .., formule = '..', belasting = PERIODIEK|
NIET_PERIODIEK, projectie = UN_AXE|DEUX_AXES`, `rek = PRIN|VMIS_SG`, and in
`#ASTER-WOHLER` the strain form `Sf, b, ef, c` (E of the material or `E = ..`). Built:
(1) multiaxial: per material a separate `DEFI_MATERIAU` (`ELAS`, `FATIGUE WOHLER`,
`CISA_PLAN_CRIT`) + `AFFE_MATERIAU`, `CALC_CHAMP EPSI_NOEU`, `CALC_FATIGUE
FATIGUE_MULTI DOMA_NOEUD`; for linear static a result from static stress/strain
× signal or per block (m ± a) via `CREA_RESU`, for nonlinear/dynamic a copy of
`res` (CALC_FATIGUE skips `NUME_ORDRE` 0, alarm PREPOST4_27: a ramp gave half the
amplitude); periodic N from max(SIGEQ1, SIGEQ2) with the bridge's curve, non-periodic
`ENDO1`; fields `fatigue_eq`, `fatigue_ratio` = SIGEQ/(c b) (`aster_fatigue.compute_multi`);
(2) shells: uniaxial route on `SIEQ_NOEU` of `res_sup`/`res_inf`, fields
`damage_top`/`damage_bottom`; (3) Manson-Coffin on `EPSI_NOEU` (bisection in ln 2N).
Measured in Code-Aster 17.4: SIGEQ = c (Δτ/2 + a max(P_max, 0)) (Dang Van) or with N_max
(Matake) respectively, `D_VAN_B`/`MATAKE_B` do not count; Crossland = `FORMULE_CRITERE` with `AMPCIS`
= √J₂ of the amplitude tensor (szlz107a); `DOMA_NOEUD` without `EPSI_NOEU`: CALCULEL_29;
below the Wöhler table with EXCLU NBRUP = 0, ENDO ≈ 1e-308; PROL LINEAIRE here too linear
in (S, N) (the bridge puts log-log points in the function); NBRUP1 rounded to an
integer, ENDO1 not; PERIODIQUE counts one cycle per history, NON_PERIODIQUE rainflow;
MATAKE_MODI_AV picks a different plane than _AC; `EPSI_NOEU` is the linear
strain even with GDEF_LOG. Verification (`tests_vermoeiing.py`, 11 new cases, 28 checks): (1) sslv135a in
3D: SIGEQ 300/275 MPa exact, NBRUP 1.2·10⁻⁵/1.5·10⁻⁵ (rounding), ENDO ≤ 1·10⁻¹⁴ vs.
`VALE_REFE` (tolerance 1 %); Dang Van non-periodic 4·10⁻¹⁵; ramp 0 → 1 exact (VM-08d);
tension + shear by hand (σ = 120, τ = 80 MPa): Dang Van SIGEQ −2.3·10⁻⁶, D −1·10⁻⁵,
two blocks −2.3·10⁻⁵; Crossland 3·10⁻¹⁵; Matake SIGEQ +5.8·10⁻⁴, D +2.6·10⁻³ (search grid
of the critical plane; within 1 %); (2) shell plate pure bending, σ = 6m/t² (7·10⁻¹³),
damage top/bottom with Goodman 8·10⁻¹² / 6·10⁻¹² (≤ 0.1 %); (3) Manson-Coffin with
imposed plastic strain: strain amplitude exact, D 1.6·10⁻⁹; elastic with `rek = VMIS_SG`
exact. Smoke tests (not in the regression): Dang Van in `dyna_impl_3d` and a model with
solid + shell, diagnosis OK. IronPython 2.7.9: parse, messages, .comm code and report.
Regression (`VERIF_WORK` on D:): 1046 of 1049 checks OK (227 cases), 3 BEKEND (NL-03a,
KNOWN_BUGS 43), 0 NOK/FOUT, no previously OK check worse; in `resultaten.json` only
the VM cases (VM-01..07 were missing from the baseline and are back). Found and not
fixed: KNOWN_BUGS 82 (reversed plasticity with the default deformation GDEF_LOG
does not converge on unloading). Limitations: KNOWN_BUGS 66. Open: Mecway GUI test
(fields `fatigue_eq`, `fatigue_ratio`, `damage_top/bottom` as a contour). Questions
for the user: (1) a, b, c per material (now one set for all materials) or rather
by default from σ₋₁/τ₋₁ (`#ASTER-WOHLER ... sigma_1 = .., tau_1 = ..`)? (2) multiaxial on
shells (top/bottom via `CALC_FATIGUE` on `res_sup`) and per Gauss point (`DOMA_ELGA`)
needed (as S8c)? (3) Morrow/SWT correction for the strain curve wanted? (4) with reversed
plasticity propose `PETIT` by default (WARNING) or research KNOWN_BUGS 82 first?

### S5 – Welding: metallurgy
**Code-Aster:** `CALC_META`, `DEFI_TRC`, `META_ACIER`. `hsnv101a`/`hsnv102a` are AXIS:
only a source for material and TRC syntax. **Research:** input of TRC data
(`#ASTER` keyword or data file); phase fields to Mecway.
**Done when:** 3D bar with imposed T(t): phase fractions within 1% of the
TEST_RESU values of `hsnv101a`.
**Findings:** Input route (docs/Lassen.md §10): `#ASTER-METALLURGIE <Mecway-
materiaal>: staal=16MND5 | trc=<DEFI_TRC uit #ASTER-code>, ...` (`bridge_metallurgy.py`;
form like `#ASTER-MATERIAAL`). Standard datasets with source: `16MND5` (test case
mtlp103a, V4.61.103: TRC with 29 histories, META_ACIER, DURT_META, GRAIN_AUST) and
`HSNV101A` (test case hsnv101a, incl. the mechanical data per phase). `META_ACIER` /
`DURT_META` in the thermal `DEFI_MATERIAU` (a separate CHAM_MATER gave
`RESULT1_39` per step; only needed for a custom `trc=`, because #ASTER code comes after the
materials), `CALC_META` (`ACIER`) after the thermal solve; fields `ferrite`,
`pearlite`, `bainite`, `martensite`, `austenite`, `hardness` per time step (group
`metallurgy`), summary with the HAZ in log/status box. Option `mechanica=ja` in the
chain S4b: `ELAS_META_FO` + `META_ECRO_LINE`, `META_P_IL`, `AFFE_VARC M_ACIER`
(`ALPHA_A`, `DEPS`, yield strength/slope per phase). Verification MT-01..08
(`tests_lassen_meta.py`, group "Metallurgie"): (a) hsnv101a in 3D: phases ≤ 1.3·10⁻⁶
vs. the test case itself (hsnv101a has no TEST_RESU on phases; AXIS run with
CREA_TABLE), and with the metallurgical law the TEST_RESU σ ≤ 5·10⁻⁷, ε ≤ 5·10⁻⁵ (tol.
1%); (b) Koistinen-Marburger (16MND5, 1000 °C/s; own TRC MT-08) ≤ 4·10⁻⁸ and
austenitisation on heating ≤ 2·10⁻⁸ between Ac1 and Ac3 (0.22% just above Ac3);
(c) transformation strain of a free bar and stress of a restrained bar ≤ 6·10⁻⁶ vs. the
hand calculation; weld bead MT-06 (HAZ, hardness) and MT-07 (residual stress with phases, 14 min)
qualitative: the martensite expansion lowers σxx in the weld from 466/641 to 176/4
MPa (top/middle, hex8). Measured behaviour (KNOWN_BUGS 72): austenitisation lags behind with
fast heating and large ΔT per step (dataset τ 0.34 s: weld axis 6% austenite;
advice and WARNING: `TAUX_1=TAUX_3=0.001`), martensite stops at ~0.7% austenite,
16MND5 still gives 3% bainite at 200 °C/s; with `META_P_IL` no
`equivalentplasticstrain` (V7 is a stress). Regression 1037/1040 OK, 3 BEKEND (NL-03a, KNOWN_BUGS 43), 0 NOK/FOUT; Lassen.md has been renumbered (§10 Metallurgy, §11 Verification, §12 Sources). Open: Mecway GUI test
(fields per time step, status box). Questions for the user: (1) set TAUX of 16MND5 by default to
0.001 s for welding (now faithful to mtlp103a 0.34 s, with WARNING)? (2)
include mechanical phase data for 16MND5 (or S355) from the literature as a
dataset? (3) a TRC diagram for structural steel (S355) needed? (4) tempering
(`ACIER_REVENU`) in multi-pass welding and transformation plasticity (`META_PT`) as a
follow-up step (split off as S5b)?

### S9 – Load case combinations (go/no-go)
Mecway no longer has load cases: they are converted into **configurations** (manual §2.8;
API `mw.set_active_configuration`). **First go/no-go:** can configurations with
factors properly express load cases that the bridge reads from the `.liml`? If not: set the step
to **dropped** with the reason, document it, build nothing.
**Code-Aster:** `MACRO_ELAS_MULT` (one factorisation, several `CAS_CHARGE`), combinations
and envelope via `CREA_CHAMP`/`CALC_CHAMP`. 3D test case `sdlv128a` (4 `NOM_CAS`); also
`ssll101c`, `ssll106a`.
**Done when:** the combination equals the linear superposition of separate runs
(≤ 1e-6 relative).
**Findings:** **No-go, dropped** (7 Oct 2026). (1) A configuration in the `.liml`
is only `<configuration name=".."/>` at the top plus, per load item/condition, a child
`<suppressed configuration=".."/>` (Samples/CylinderLifting, Tutorials/AssemblyWithContact,
own test model); there is no factor, no per-configuration value and no active
configuration in the file (mecway.exe: only "Suppress/Unsuppress in all
configurations", tab menu New/Delete/Rename, "Solve all configurations"; manual
§2.8: "suppress and unsuppress loads and constraints"; the old load cases become
configurations on opening). Solution formulas (manual §10.11) work on the active
solution. A combination 1.2 G + 1.5 Q can therefore only be entered by the user as a separate
configuration with duplicated load items factored by hand; the
factors are then stored nowhere, so the bridge cannot derive `MACRO_ELAS_MULT` + combination/
envelope. (2) Mecway headless (`mw_solve.py`) solves all configurations,
each a `<solution configuration="..">` with a model copy in which suppressed items are
`suppressed="true"`. Model beam hex20 with G (gravity), Q (pressure) and ULS (its own
gravity 1.2 g and pressure 1.5 q): Mecway ULS = 1.2 G + 1.5 Q to 3e-15 (displacement,
relative to max); bridge on a copy with only configuration ULS = Mecway ULS to
1.0e-9 (diagnosis OK). (3) The bridge solves one configuration per run (the only one without
suppressed items, otherwise the first) and cannot read the active one; procedure for
load cases (a copy per configuration) in `docs/Handleiding.md` §4 + EN; the unjustified
WARNING with one configuration as KNOWN_BUGS 68 (fixed 15 Oct: setting
Configuration on the start screen, verification LS-20). Nothing built. **Open questions:** (a)
A dedicated input for factors after all (e.g. `#ASTER-COMBINATIE ULS = 1.2*G + 1.5*Q`
on configuration names) with `MACRO_ELAS_MULT` and envelope, outside Mecway? (b) A
drop-down "Configuration" on the start screen (names from the `.liml`, then
`mw.set_active_configuration`) or all configurations in one run with `MACRO_ELAS_MULT`
(same boundary conditions), without factors?

### S13 – Orthotropic and anisotropic materials
**Goal:** translate the Mecway materials *Orthotropic* and *Anisotropic* (stiffness or compliance matrix)
instead of stopping the run, with Mecway's *Element orientation* (per element
`orientationux`…`vz`, `angle`) as the material direction; also in shells.
**Code-Aster:** `DEFI_MATERIAU` `ELAS_ORTH` (and `ELAS_ISTR`), anisotropic via `ELAS_ORTH` if that
suffices, otherwise report it as NOT possible; direction with `AFFE_CARA_ELEM` `MASSIF` `ANGL_REP`/`ANGL_EULER`
per element (group), shells `COQUE` `ANGL_REP`/`VECTEUR`; composite `DEFI_COMPOSITE`.
**Research:** Mecway's XML of Orthotropic/StiffnessMatrix/ComplianceMatrix (Samples, mecway.exe),
the definition of U/V and `angle` (manual §7), how Mecway shows stresses in local axes; grouping
elements with the same orientation; thermal orthotropy (`THER_ORTH`).
**Done when:** an orthotropic beam in two orientations (analytical, bending with E_L and E_T) and a
rotated block under tension (Hooke in local axes) within 1%, and equal to Mecway headless; regression D.5.

### S14 – Hyperelastic material
**Goal:** translate Mecway *Neo Hooke* and *Mooney-Rivlin* (now: WARNING and the run stops).
**Code-Aster:** `ELAS_HYPER` (C01, C10, C20, K) with `RELATION='ELAS_HYPER'`, `DEFORMATION='GDEF_LOG'`
or `'GREEN_LAGRANGE'` in `STAT_NON_LINE`; test cases `ssnv187a`, `ssnp154`.
**Research:** Mecway's parameters and units (XML), near-incompressibility (`INCO_UPG`?),
which analyses (nonlinear only).
**Done when:** uniaxial tension up to 100% strain equal to the analytical Neo-Hooke/Mooney-Rivlin curve
(≤ 1%) and to Mecway headless; regression D.5.

### S15 – Pre-tension section (bolt prestress)
**Goal:** translate Mecway's *Pre-tension section* (`pretensionsection`, Samples/BoltedJoint).
**Code-Aster:** prestress via an imposed shortening across a cut (`LIAISON_DDL` between the
two sides of the cut, or cutting the bolt with `CREA_MAILLAGE` and `DDL_IMPO`), in two phases:
first force, then locked (`STAT_NON_LINE` with two loads/`ETAT_INIT`); alternatively thermal
shrinkage. Check the Code-Aster documentation on bolt prestress (U2 doc).
**Research:** Mecway's XML (cut plane, force or shortening, phases), behaviour in linear static.
**Done when:** BoltedJoint: bolt force after prestressing = specified force (≤ 1%), results equal to
Mecway headless within the known contact differences (KNOWN_BUGS 43); regression D.5.

### S16 – 2D and axisymmetric analyses
**Goal:** translate Mecway's 2D analysis types (S20, D20, SA0, also A20 and thermal 2D); now the run stops.
**Code-Aster:** modelisations `C_PLAN`, `D_PLAN`, `AXIS` (thermal `PLAN`/`AXIS`, acoustics `2D_FLUIDE`);
mesh in the XY plane, thickness for plane stress; results back in Mecway's 2D fields.
**Research:** Mecway's 2D elements and thickness input, analysis codes (DA0, V20 appear in mecway.exe),
which loads/conditions exist in 2D, Mecway's field names for 2D/axisymmetric (hoop stress).
**Done when:** plate with a hole in plane stress (Kt), thick-walled cylinder axisymmetric (Lamé) and a
2D dynamic case within the tolerances of their 3D counterparts and equal to Mecway headless;
regression D.5. May be done in sub-steps (S16a static, S16b dynamic/thermal/acoustics).

### S17 – Loads on beam side faces and hydrostatic pressure on shell edges
**Goal:** the two open items of KNOWN_BUGS 5: pressure/traction on the side face of a beam (Mecway
computes them as a distributed beam load) and hydrostatic pressure on shell edges.
**Code-Aster:** `FORCE_POUTRE` (also as a function of X, Y, Z via `AFFE_CHAR_MECA_F`); shell edges via
`FORCE_ARETE` or nodal forces like `bridge_mesh._edge_loads`.
**Done when:** beam with pressure on a side face = beam with the equivalent line load (≤ 0.1%) and equal to
Mecway headless; hydrostatic pressure on a shell edge equal to the hand calculation; regression D.5.

### S18 – Testing the new Code-Aster version (18)
**Goal:** make the bridge work with Code-Aster 18 and record that version as tested; until then
a run with 18 only gives a WARNING (`bridge_version.py`, `TESTED_ASTER_VERSIONS` in `bridge_utils.py`).
**Prerequisite:** Code-Aster 18 for Windows (code-aster-windows.com) is available; until then status later.
**Code-Aster:** keywords in the templates (`AsterTemplate_*.comm`) and the generated `.comm`
against the catalogue of 18; the Python API in the job (`aster_results_export.py`, `aster_spectrum.py`,
`aster_acoustic_export.py`, `aster_acoustic_complex.py`, `aster_cyclic.py`, `aster_fatigue.py`);
the `.mess` text that `bridge_version.py`, `bridge_convergence.py` and `bridge_run_aster.py` read (version line,
convergence table, DIAGNOSTIC JOB).
**Research:** the release notes of 18 (removed/renamed keywords), the default path of the
launcher (`exe_aster`) and whether 17.4 and 18 can stay installed side by side.
**Done when:** full regression (`run_verificatie.py`) with 0 NOK/FOUT and the same BEKEND as the
baseline in docs/Verificatie.md §3, the official Code-Aster tests (`run_code_aster_tests.py`) all OK,
templates/API adapted where needed (17.4 keeps working or the decision to drop 17.4 is recorded in
CHANGELOG.md), `TESTED_ASTER_VERSIONS` updated and docs (Handleiding, Na_een_update, Verificatie) NL+EN
reviewed; regression D.5.
