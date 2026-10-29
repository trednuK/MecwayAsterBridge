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
| S13 | Orthotropic and anisotropic materials, with *Element orientation* as material direction | split | – | chosen by the user 15 Oct (C1); split into S13a .. S13d (28 Oct 2026, see §S13) |
| S13a | Orthotropic / stiffness matrix / compliance matrix on solids in linear and nonlinear static, modal, buckling and implicit dynamics, material axes from the element orientation (`ELAS_ORTH` + `MASSIF` `ANGL_REP`) | done | – | branch worktree-agent-a36c7764124e6a606 on nacht-int3 (28 Oct 2026): `bridge_orthotropic.py`; OR-01 .. OR-10 OK (strains equal to Hooke rotated and to Mecway headless within 1e-7, cantilever −0.17/−0.12% vs Timoshenko, modes and buckling = Mecway within 1e-9, L30/D31 OR-12..14 = Mecway CCX within 5e-4, hex8 LINE_QUAD OR-15, formula card OR-17); LS, MO-20..31, BU-20..25, TH-03 unchanged; not yet tested in the Mecway GUI (see §S13) |
| S13b | Orthotropic material on linear shells (DKT/DST) in linear static (`DEFI_COMPOSITE` with one layer, `ORIENTATION` = angle of Mecway's U, default U = edge 1-2) | done | S13a | same branch as S13a (28 Oct 2026): `bridge_orthotropic._prepare_shells`, `composite_block`; OR-20/21 membrane exact and = Mecway headless, OR-22 bending −0.48% / +0.46% against Mecway (DKT vs MITC4); isotropic shells unchanged; not yet tested in the Mecway GUI |
| S13e | Orthotropic shells continued: quadratic shells (COQUE_3D), shells in other analyses, element offset, membranes, and Mecway's *Composite* laminates (several `DEFI_COMPOSITE` layers, per-ply results) | open | S13b | split off from S13b (29 Oct 2026); see §S13 |
| S13c | Orthotropic solids in the other mechanical analyses (explicit dynamics: critical time step from the orthotropic wave speed; mode superposition, harmonic incl. `AMOR_HYST`, spectrum, thermal → mechanical chain) and orthotropic thermal conductivity (`THER_ORTH`, Mecway `ORTHOTROPICLOCAL`) | open | S13a | split off from S13 (28 Oct 2026); see §S13 |
| S13d | Result field *stress in element coordinates* (`lamuu` .. `lamwu`) for solids | done | S13a | same branch as S13a (28 Oct 2026): `aster_results_export._element_coord_vars` with the field *stresses* in linear static of models with orthotropic solids; Mecway's rule measured (R σ Rᵀ, element-node mean at nodes of two frames); OR-01..04 (lam = R σ Rᵀ exact), OR-11 (rule within 1e-9 Pa); Mecway 34 reads the bridge's `lamuu` (headless `solution.node_value`); GUI not checked |
| S14 | Hyperelastic material (Neo-Hooke, Mooney-Rivlin) | done | – | V2026.4 (NL-50..53, issue #5); hyperfoam waits for a Windows Code-Aster with MFront (see §S14) |
| S15 | Pre-tension section (bolt prestress) | done | – | branch worktree-agent-a58def16c170e1c4c (28 Oct 2026): `bridge_pretension` (cut + LIAISON_DDL to a reference node), force and length adjustment in linear/nonlinear static; PT-01 .. PT-05 OK (exact / joint diagram 0.1%, Mecway CCX headless within 0.01%); not yet tested in the Mecway GUI (see §S15) |
| S15b | Pre-tension section in dynamic response (D30/D31) and the spring element variant (internal solver) | done | S15 | branch worktree-agent-a08bcf96702c925db on nacht-int2 (28 Oct 2026): prism variant in `dyna_impl_3d` (step from t = 0 like Mecway), spring variant in linear static as two nodal forces; PT-06 .. PT-10 OK (Mecway headless CCX within 0.06%, internal solver exact); spring variant in Frequency/Buckling ERROR (geometric stiffness, see §S15b); not yet tested in the Mecway GUI |
| S15c | Geometric stiffness of (pretensioned) springs in Buckling and Frequency with prestress, as Mecway does (now an ERROR for the spring pretension variant) | later | S15b | split off from S15b (29 Oct 2026); KNOWN_BUGS 47, 124 (b); see §S15b |
| S16a | 2D and axisymmetric static (S20 `C_PLAN`/`D_PLAN`, SA0 `AXIS`) | done | – | branch worktree-agent-ae20772a64706e75c (28 Oct 2026): `bridge_plane.py`; PL-01 .. PL-06 OK (Kt, Lamé, reaction sums exact, displacements = Mecway headless ≤ 1e-11); LS, FX unchanged; not yet tested in the Mecway GUI |
| S16b | 2D dynamic response (Mecway D20, DA0) | done | S16a | same branch (28 Oct 2026): `dyna_impl_3d`; PL-10 .. PL-12 OK (bar wave period −0.06%, damped ring −0.05%, histories = Mecway headless ≤ 4e-8); step size with *every n time steps* fixed later (former KNOWN_BUGS 127, MD-08); Mecway 34 has no 2D frequency/buckling type (V20 -> V30, B20 -> S30) |
| S16c | Thermal 2D / axisymmetric | dropped | – | Mecway has no thermal 2D type ("All thermal analysis types are 3D", manual v34 §6.7; "Axisymmetric heat transfer is not supported" in mecway.exe); thermal in a plane = shells, already translated (`bridge_thermal`, `PLAN`) |
| S16d | Acoustic Resonance 2D (Mecway A20; `ACOUSTIQUE` `PLAN`, not `2D_FLUIDE`) | done | S16a | branch worktree-agent-ad04139279cf151f2 (28 Oct 2026): `bridge_plane._apply_acoustic` + the A30 route; AK-10 .. AK-15 OK (quads = Mecway headless ≤ 1e-6, rectangle ≤ 0.05% of f_mn); triangles slightly higher (KNOWN_BUGS 130); identical via a .liml saved by Mecway (126 checks); no axisymmetric acoustic type in Mecway; not yet tested in the Mecway GUI |
| S16e | 2D extensions: beams/trusses/springs in S20, several thicknesses, moment, line pressure, frictionless, elastic support, oblique directions, constraint equations, error estimator | open | S16a | split off from S16 (28 Oct 2026); KNOWN_BUGS 126 |
| S17 | Loads on beam faces; hydrostatic pressure on shell edges (KNOWN_BUGS 5) | done | – | branch worktree-agent-afd8b7790c08d6a3d on nacht-int3 (28 Oct 2026): traction on beam side faces = `FORCE_POUTRE` traction x perimeter (`_beam_side_loads`), pressure there no load, hydrostatic pressure on shell edges as nodal forces; LS-92a..h, LS-93a..c OK (equal to Mecway headless, formula +0.06%); not yet tested in the Mecway GUI (see §S17) |
| S18 | Test new Code-Aster version (18) | later | Code-Aster 18 for Windows available | version warning and procedure done (`bridge_version.py`, docs/Na_een_update.md) |
| S19 | Beam element with warping (`POU_D_TG`) as element choice: flexural-torsional buckling of open sections (KNOWN_BUGS 115) | done | after the release of 16 Oct 2026 | branch worktree-agent-af7ab132aad22bc7d (28 Oct 2026): `elem_beam` = `POU_D_TG`, setting `beam_warping`, `bridge_warping.py`; BU-38 .. BU-42, LS-90, LS-91 OK (C column 384.98, theory 386.1, hex20 393.0; ssll103a = `VALE_CALC`); not yet tested in the Mecway GUI |
| S20 | Geometrically nonlinear beams (`POU_D_T_GD`, large rotations) as element choice for nonlinear static (KNOWN_BUGS 11) | done | after the release of 16 Oct 2026 | b366f94 (review fixes: s20-fix); idea and benchmarks from the fork by MishalTPC; NL-80 .. NL-89 OK (<= 0.04 %), existing beam cases bit-identical; not yet tested in the Mecway GUI |
| S21 | Selective flexible joint on `POU_D_T_GD` beams via a short GD stub element (KNOWN_BUGS 106b) | dropped | S20 | prototype 22 Oct 2026: benchmark B1 (objectivity) failed already for the plain GD beam without stub, B2 (hinged elastica) passed; ERROR kept (see §S21) |
| S22 | Hide failed or eroded elements in post-processing (ParaView Threshold) | open | – | requested 22 Oct 2026; branch b-mwpost (24 Oct): (a) field `failed` written (VTU `BEZWEKEN`), Mecway display not yet checked; (b) moves to AdvancedToolsHub (MWHub Post erosion filter, ParaView button → hub); (c) settings docs only |
| S23 | Linear buckling with a constant (dead) plus a variable (live) load | done | – | branch w-q, 23 Oct 2026: `#ASTER-CONSTANT` (BU-40) |
| S24 | Adaptive time stepping (`DEFI_LIST_INST METHODE='AUTO'`) from Mecway's automatic time stepping | done | – | branch w-p1; static only, setting `auto_time_stepping`; NL-21a/b; NL/NK families unchanged |
| S25 | Optional exact section properties with `MACR_CARA_POUTRE` | dropped | – | covered by MecwaySectionProps (own repository): exact A, I, J, `JG`, `EY`/`EZ`, `AY`/`AZ` via `#ASTER-SECTIE`, already read by the bridge (user, 28 Oct 2026) |
| S26 | Hysteretic damping (`AMOR_HYST`, `RIGI_MECA_HYST`) in harmonic analysis | done | S10h | branch w-s (23 Oct 2026): setting `loss_factor` + `#ASTER-HYST`; GENE and PHYS; HR-06a..d OK, HR-01..05 unchanged (see §S26) |
| S27 | Optional line search (`RECH_LINEAIRE`) in nonlinear static | done | – | branch w-p2; `line_search` auto (cables only)/on/off; SaggingCable *Tension only* 9 -> 7 iterations; `on` breaks `POU_D_T_GD` (see §S27) |
| S28 | Optional contact normal smoothing (`LISSAGE='OUI'`) | done | – | branch w-p2; `contact_smoothing` (default off); NL-03a..f and PipeClip unchanged with it on (see §S28) |
| S29 | Penetration check for penalty contact (`EVENEMENT='INTERPENETRATION'`) | done (other route) | – | branch w-p1; WARNING after the run from study.mess, setting `contact_pene_maxi`; `INTERPENETRATION` crashes 17.4 (JEVEUX_26); NL-03p |
| S30 | Redo the Code-Aster forum research | later | forum online again (offline until about 30 Oct 2026) | planned 23 Oct 2026 |
| S31 | LAC (mortar) contact as an option | later | – | long-term option, planned 23 Oct 2026 |
| S32 | Extra Newton iterations before step cutting (`ACTION='ITER_SUPPL'`) | dropped | – | tried 23 Oct 2026: NL-90 fails (FACTOR_11), see §S32 |
| S33 | Evaluate Mecway result formulas in the bridge (KNOWN_BUGS 121) | done | – | branch stap-S33 (28 Oct 2026): `bridge_formula` + `_formula_vars`; FX-01 .. FX-03 OK, equal to Mecway's own solve within 1e-13; checked in the Mecway GUI (formulas valid, contour) |
| S34 | Principal stresses, Tresca and principal strains as result fields (formulas `s1`, `tr`, `e1`); acceleration under Mecway's names | done | S33 | branch stap-S34 (28 Oct 2026): `_principal_vars`, groups `principal_stresses` / `principal_strains`; `accx/y/z`; FX-02 extended; Mecway recognises the fields (headless + GUI); regression 2376/2382 |
| S34b | Principal values of shells (top/middle/bottom) and Green-Lagrange principal strains (`GLe1`) under Mecway's names | done | S34 | branch of S34b (28 Oct 2026): `_shell_principal_vars`, `greenlagrangeprincipalstrain1..3`, `GLe1..3`, e/g/e1 alias for Green-Lagrange; FX-04, FX-05 OK; rule equal to Mecway's own solve within 3e-13; Mecway recognises the fields (headless); GUI not checked |
| S35a | HOMARD adaptive refinement inside the job: research and prototype (thermal, nonlinear static with plasticity) | done | S7 | 28 Oct 2026: route works (own ZZ indicator, CART_NEUT_R + `MACR_ADAP_MAIL`, restart per loop, `FRONTIERE_ANALYTIQUE`, `PROJ_CHAMP` back + `export_results` unchanged); 2.3 x (thermal) and 3.2 x (plasticity) fewer cells than uniform at equal accuracy; prototype `TestFiles/Tools/homard_s35` (see §S35) |
| S35b | HOMARD adaptive refinement inside the job: build into the bridge (settings Thermal/Nonlinear, curved boundaries automatic + `#ASTER-RAND`, verification AD-10 .. AD-12) | done | S35a | branch s35b (28/29 Oct 2026): `bridge_homard.py` + `aster_adapt.py`, settings `adapt_homard*`; AD-10/10b/11/12 OK (thermal −0.87%, plasticity +0.9% against uniform n32; 0.43 / 0.71 x the cells of uniform n8); first version solids + face selections only; not tested in the Mecway GUI (see §S35) |
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
bridge verification is 3D**, except the 2D analyses (S16a/b, family PL; A20, S16d: AK-10 .. AK-15).
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
   **Bar**: baseline 2356 of 2362 checks OK (439 test cases), 6 BEKEND (KNOWN_BUGS
   43: 3 in NL-03a; 83: 1 in BR-10; 108: 1 in LS-67; 115: 1 in BU-35), 0 NOK/FOUT
   (full regression on bridge f14f6c7, 2026-10-23, after V2026.4; since 29 Oct (373d13a + new S19 cases on 35c7564): 2957 of 2963, 544 test cases:
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
`orientationux`…`vz`, `angle`, or the Loads & Constraints card read by `bridge_orientation`)
as the material direction; also in shells.
**Code-Aster:** `DEFI_MATERIAU` `ELAS_ORTH` (and `ELAS_ISTR`), anisotropic via `ELAS_ORTH` if that
suffices, otherwise report it as NOT possible; direction with `AFFE_CARA_ELEM` `MASSIF` `ANGL_REP`/`ANGL_EULER`
per element (group), shells `COQUE` `ANGL_REP`/`VECTEUR`; composite `DEFI_COMPOSITE`.
**Research:** Mecway's XML of Orthotropic/StiffnessMatrix/ComplianceMatrix (Samples, mecway.exe),
the definition of U/V and `angle` (manual §7), how Mecway shows stresses in local axes; grouping
elements with the same orientation; thermal orthotropy (`THER_ORTH`).
**Done when:** an orthotropic beam in two orientations (analytical, bending with E_L and E_T) and a
rotated block under tension (Hooke in local axes) within 1%, and equal to Mecway headless; regression D.5.
**Findings (28 Oct 2026, S13a):**
- *Mecway's XML* (attribute names from `mecway.exe`, semantics measured with headless Mecway 34
  solves of single hex8 cubes under an imposed homogeneous strain, all nodes prescribed, so the
  nodal stress is C·ε exactly): `<mechanical type="Orthotropic" youngsmodulusu/v/w
  poissonratiouv/vw/wu shearmodulusuv/vw/wu thermalexpansionu/v/w>`, major Poisson ratios
  (ν31 = −ε_U/ε_W under stress in W, so `NU_LN` = ν31·E_U/E_W); `type="StiffnessMatrix"` with
  `c11` .. `c66` and `type="ComplianceMatrix"` with `s11` .. `s66` (upper triangle, compliance in
  m²/N), rows 1..6 = **UU, VV, WW, VW, WU, UV** with engineering shear (c14 couples ε_UU with γ_VW,
  c16 with γ_UV; not the UV, VW, WU of the Orthotropic tab labels). Material axes = element axes:
  global by default; attributes `orientationux..vz`, `orientationvx..vz`, `angle` and the
  *Element orientation* card give V projected perpendicular to U and turned about U by the angle
  (within 1e-15 of the rotated Hooke matrix). Only a U or only a V vector, or U parallel to V:
  Mecway gives no solution; an angle alone: global axes. Stresses are reported in global axes; the
  field *stress in element coordinates* stores `lamuu`, `lamvv`, `lamww`, `lamuv`, `lamvw`,
  `lamwu` = R σ Rᵀ (S13d). Mecway's thermal expansion of matrix types: none (message in
  `mecwayf.dll`).
- *Code-Aster*: `ELAS_ORTH` (no general 3D anisotropy in `DEFI_MATERIAU`, only `ELAS_ORTH`,
  `ELAS_ISTR`; `ELAS_COQUE` is for shells), so a matrix is translated only if all coupling terms
  are zero, else ERROR. `MASSIF` `ANGL_REP` nautical angles (U4.42.01 §13.3/13.6, the example
  (0, 0, −90) → (L, T, N) = (X, −Z, Y) fixes the signs; same formulas as `anglnaut` in
  `observation_ops.py`), one group `BRORI<n>` per distinct frame. Orthotropic shells need
  `DEFI_COMPOSITE` (U4.43.01 §3.5.2; the DKT test cases ssls111/117 have `ELAS_ORTH` commented
  out): S13b.
- *Built* (`bridge_orthotropic.py`): parse, `ELAS_ORTH` (+ `ALPHA_L/T/N` with thermal stress),
  frame → `ANGL_REP`, grouping, scope check (solids; linear and nonlinear static, modal and
  buckling of the structure, implicit dynamics; elsewhere ERROR). Cards on solids now fill `solid_orientations`
  (`bridge_orientation`).
- *Verification*: OR-01 .. OR-04, OR-09 (cube, tension and free thermal expansion with turned
  axes, attributes and card with angle, stiffness and compliance matrix): all six global strains
  within 5e-8 of Hooke's law rotated and of Mecway's own solve; OR-05/06 cantilever with E_U and
  E_V along the beam −0.17% / −0.12% against Timoshenko, equal to Mecway (1e-8); OR-07/08
  (frequencies, −1.1% / −0.26% against Euler-Bernoulli = the shear effect) and OR-10 (buckling
  factor −0.28%) equal to Mecway within 1e-9. Regression: LS (all), MO-20 .. MO-31,
  BU-20 .. BU-25, TH-03: 136 cases, FEM values bit-identical to the baseline.
- *Nonlinear static and implicit dynamics* (same branch, part of S13c): RELATION `ELAS` with
  `ELAS_ORTH`; large displacements on solids = `GREEN_LAGRANGE` (as for isotropic); Rayleigh
  damping as `AMOR_ALPHA`/`AMOR_BETA` in `ELAS_ORTH` (not verified). Mecway's internal solver
  gives no solution for L30/D31 (also isotropic, these models), so CCX is the reference: OR-12
  (cube, L30) within 2e-6, OR-13 (cantilever 300 N, 23% of L) 1e-7, OR-14 (step response,
  period) +0.05%. Explicit dynamics stays an ERROR: `_critical_time_step` estimates the wave
  speed from one E and NU.
- *S13d* (same branch): Mecway's *stress in element coordinates* = node variables `lamuu`,
  `lamvv`, `lamww`, `lamuv`, `lamvw`, `lamwu` = R σ Rᵀ; at a node of elements with different
  axes Mecway takes the mean of the element-node values (measured: at the interface of two
  frames Mecway's value differs from the rotated nodal mean, at single-frame nodes it equals
  it within 1e-15). The bridge does the same from `SIGM_ELNO` (`_element_coord_vars`), for all
  solids of a model with orthotropic material, with the field *stresses* (no new setting).
  OR-11 (two frames): the rule within 1e-9 Pa; against Mecway's own values the difference is
  that of the global nodal stresses of the two solvers on this coarse mesh (up to 2 MPa of
  80 MPa at the interface node, KB3). Mecway 34 reads the bridge's `lamuu` (headless).
- *S13b* (same branch): Mecway's shell: W = normal, U = edge from node 1 to 2 by default
  (measured on quad4 squares under imposed membrane strain; the manual says node 3 for
  quadratic elements, not measured), otherwise the projected U axis; plane stress with E_U,
  E_V, ν_UV, G_UV; stresses in global axes. Code-Aster: orthotropic shells only via
  `DEFI_COMPOSITE` (U4.43.01 §3.5.2); one layer per group `BRSHO<n>` of equal angle from the
  local x (projection of the group's `VECTEUR`, as `_shell_ref_vector`) to U, folded into
  [−90°, 90°] (catalogue range; an orthotropic layer is symmetric under U → −U). `SIGM_ELNO`
  of the composite stays in the shell's user axes, so the existing transformation to global
  works (OR-20: σyy = σxy = 0 with U at 30°). Seen on the way: Mecway 34's *Fixed* on a node
  selection of shell nodes left the rotations free (singular result, OR-22 first try); on the
  edge (face selection) it clamps. NOT checked how the bridge translates the node-selection
  variant (it may clamp the rotations where Mecway does not).
- *Open*: GUI check in Mecway (open a result, item *stress in element coordinates*);
  quadratic and composite shells (S13e); explicit dynamics, modal-basis analyses and
  orthotropic conductivity (S13c).

### S14 – Hyperelastic material
**Goal:** translate Mecway *Neo Hooke* and *Mooney-Rivlin* (now: WARNING and the run stops).
**Code-Aster:** `ELAS_HYPER` (C01, C10, C20, K) with `RELATION='ELAS_HYPER'`, `DEFORMATION='GDEF_LOG'`
or `'GREEN_LAGRANGE'` in `STAT_NON_LINE`; test cases `ssnv187a`, `ssnp154`.
**Research:** Mecway's parameters and units (XML), near-incompressibility (`INCO_UPG`?),
which analyses (nonlinear only).
**Done when:** uniaxial tension up to 100% strain equal to the analytical Neo-Hooke/Mooney-Rivlin curve
(≤ 1%) and to Mecway headless; regression D.5.
**Status:** Neo Hooke and Mooney-Rivlin done for V2026.4 (NL-50..53, issue #5).
**Still open – hyperfoam:** only when a Windows build of Code-Aster with MFront support (MGIS) is
available. Checked 22 Oct 2026: neither the Simulease build nor the open-simulation-center
`code_aster-17.4.0-win64.msi` can run `HYPER_HILL` (ssnv520a: `MGISBehaviour` not available; see
docs/en/Settings_contact_and_nonlinear.md). Mecway has no hyperfoam material, so the input would be an
`#ASTER` keyword (bridge_custom.py). Then: `HYPER_HILL` (ALPHA, BETA, MU) with GREEN_LAGRANGE, check
against ssnv520a and a uniaxial foam case.

### S15 – Pre-tension section (bolt prestress)
**Goal:** translate Mecway's *Pre-tension section* (`pretensionsection`, Samples/BoltedJoint).
**Code-Aster:** prestress via an imposed shortening across a cut (`LIAISON_DDL` between the
two sides of the cut, or cutting the bolt with `CREA_MAILLAGE` and `DDL_IMPO`), in two phases:
first force, then locked (`STAT_NON_LINE` with two loads/`ETAT_INIT`); alternatively thermal
shrinkage. Check the Code-Aster documentation on bolt prestress (U2 doc).
**Research:** Mecway's XML (cut plane, force or shortening, phases), behaviour in linear static.
**Done when:** BoltedJoint: bolt force after prestressing = specified force (≤ 1%), results equal to
Mecway headless within the known contact differences (KNOWN_BUGS 43); regression D.5.
**Findings (28 Oct 2026):**
- *Mecway's semantics* (manual v34 §9.11 and the CCX decks read during headless Mecway 34 solves of
  BoltedJoint and test models): the selected faces define the prism (axis = median of the pairwise
  cross products of the normals, extent of the faces); Mecway cuts in the middle (BoltedJoint: the
  element boundary between the two selected elements), inserts a 0.25 mm element layer and writes
  `*PRE-TENSION SECTION` with a reference node; force = `*CLOAD` on DOF 1 of that node in the
  (single) step, so the force stays applied (no locking); length adjustment = `*BOUNDARY`. Mode
  attribute: `adjustment="true"` (found by trial, confirmed by a model re-saved by Mecway);
  `force="true"`, `force="false"` and no attribute all give the force. With *Quasi-static* time
  steps a constant pretension acts in full from the first step (`AMPLITUDE=STEP`).
- *Route*: CCX's own formulation (`pretensionsections.f` of the ccx 2.23 source shipped with
  Mecway: per node pair two tangential MPCs and one normal MPC with the reference DOF), in Code-Aster
  as LIAISON_DDL per pair u_above − u_below + δ n = 0 with δ = DX of a POI1 `DIS_T` reference node;
  FORCE_NODALE FX = F or DDL_IMPO DX = δ. One step, no `ETAT_INIT` phases (Mecway has none).
  Thermal shrinkage was not chosen: it is not force-controlled and depends on the element layer.
  ssnv106a tightens a bolt the same way (relative displacement between doubled nodes).
- *Verification*: PT-01/02/05 exact (bar, hex20 and tet4 with a zig-zag section), PT-03 joint
  diagram −0.10% (plate flexibility), PT-04 force constant under an external load 1000.00 N;
  Mecway CCX headless −0.004 .. +0.007%. Bolt force after prestressing = F by construction (PT-01
  reaction exact).
- *BoltedJoint itself*: does not solve with Code-Aster (plate B only held by friction contact,
  `MECANONLINE9_4` in step 1, also without the section and with penalty, `SEUIL_INIT` or
  DISCRETE); recorded in KNOWN_BUGS 43. A bonded-contact variant runs, but Mecway's displacements
  are ~10x larger even without the section (CCX `*TIE` with `POSITION TOLERANCE=0`, question).
  So the BoltedJoint criterion is replaced by PT-03/04 (same physics, contact-free).
- *Irregular mesh* (29 Oct 2026): PT-11 .. PT-13, the bar as a jittered tet10/tet4 mesh (section
  through tetrahedra of varying size at a random height): stress N/A exact in all nodes in force and
  adjustment mode, node pairs and element counts equal to an own count, Mecway CCX −0.001%. Fixed:
  the logged section area used abs() of the projected faces and counted folds of the zig-zag surface
  twice (1.0641e-4 instead of 1e-4 m2); now a signed projection (log only, no effect on results).
- *Open*: dynamics and the spring element variant (S15b); a GUI check in Mecway (load PT-01 results,
  Pre-tension section dialog with Length adjustment saves `adjustment="true"`).

### S15b – Pre-tension section in dynamics and on a spring
**Goal:** the two parts of KNOWN_BUGS 124 a/b: the prism variant in Dynamic response (D30/D31) and
Mecway's spring element variant (internal solver).
**Findings (28 Oct 2026):**
- *Mecway's semantics in dynamics* (CCX decks caught from Mecway's temp folder during headless D30/D31
  solves of the joint of PT-03 with a heavy top plate): one `*STEP` (`NLGEOM=YES` for D31) with
  `AMPLITUDE=STEP` and `*DYNAMIC,DIRECT`, the `*CLOAD` (force) or `*BOUNDARY` (adjustment) on the
  pre-tension node; a formula in t becomes `*CLOAD,AMPLITUDE=...`. So a constant value acts as a step
  from t = 0, no static preload step; the top plate vibrates about the static state (Mecway: period
  +0.23% from 2π√(m/k), peak 2× static). D30 and D31 give the same history. Mecway's deck also uses the
  axis −Y where the bridge uses +Y (same physics). `<timesteps>` needs `stepsize` for CCX (without it
  the increment was 0 and CCX gave no solution).
- *Built*: `bridge_pretension` accepts `DYNA_NON_LINE` with an implicit scheme; the load on the
  reference node takes the same route as an ordinary force or displacement (time functions), so the
  semantics are Mecway's. Explicit (`DIFF_CENT`) stays an ERROR (massless reference node, NOT
  verified). PT-06 (force), PT-07 (adjustment), PT-08 (formula ramp, D30): hand calculation within
  0.26% (PT-08 0.57%, a sensitive sample of a small vibration), Mecway within 0.06%.
- *Spring variant* (Mecway 34 internal solver, headless): the XML is the same `<pretensionsection>` on a
  face selection of the line element; faceid 1, 2 and 3 give the same result; Mecway always uses the
  length adjustment (force="true" with force 0 and adjustment 1 mm shortens by 1 mm; force 5 N with
  adjustment 0 does nothing). Translated in linear static as two `FORCE_NODALE` k δ along the spring
  axis (exact, PT-09 along X with `force="true"`, PT-10 inclined). Mecway's `<fixed>` on a node selection
  of spring-only nodes did not hold them in Mecway (singular); the cases use displacement constraints.
- *Buckling/Frequency with the spring variant*: Mecway gives the tensioned spring a geometric
  stiffness (cantilever beam with a pretensioned spring from base to tip: 6.991 = the load directed
  through the base; the bridge with nodal forces 1.748 = Mecway with an ordinary tip force), DIS_T has
  none: ERROR, recorded in KNOWN_BUGS 124 (b) and 47.
- *Open*: GUI check in Mecway (a spring pretension made in the Mecway dialog: which faceid and mode
  attribute it writes); whether a geometric stiffness for springs is wanted in buckling/modal with
  prestress (would apply to all tensioned springs, KNOWN_BUGS 47). Decision (user, 29 Oct 2026): keep
  the ERROR for now; geometric stiffness of springs is step S15c.

### S16 – 2D and axisymmetric analyses
**Goal:** translate Mecway's 2D analysis types (S20, D20, SA0, also A20 and thermal 2D); now the run stops.
**Code-Aster:** modelisations `C_PLAN`, `D_PLAN`, `AXIS` (thermal `PLAN`/`AXIS`, acoustics `2D_FLUIDE`);
mesh in the XY plane, thickness for plane stress; results back in Mecway's 2D fields.
**Research:** Mecway's 2D elements and thickness input, analysis codes (DA0, V20 appear in mecway.exe),
which loads/conditions exist in 2D, Mecway's field names for 2D/axisymmetric (hoop stress).
**Done when:** plate with a hole in plane stress (Kt), thick-walled cylinder axisymmetric (Lamé) and a
2D dynamic case within the tolerances of their 3D counterparts and equal to Mecway headless;
regression D.5. May be done in sub-steps (S16a static, S16b dynamic/thermal/acoustics).
**Status:** S16a, S16b and S16d done (28 Oct 2026); split off: S16c (dropped, no thermal 2D in
Mecway), S16e (2D extensions).
**Findings S16a (Mecway 34, headless: `mw_solve.py`, a safe runner on own PIDs, `mw.save_as`;
no GUI):**
- Analysis codes: S20 = *Static 2D*, SA0 = *Static Axisymmetric*, D20 = *Dynamic Response 2D*
  (Samples/PandSWaves), DA0 = *Dynamic Response Axisymmetric* (solved headless with time
  steps), A20 = *Acoustic Resonance 2D*. V20 is legacy: Mecway 34 solves it as V30 (the
  solution file says V30); B20/T20/L20 become S30. No thermal, frequency, buckling or
  nonlinear 2D type.
- Elements: tri3/tri6/quad4/quad8 in the XY plane (Z ignored), same `<elem>` as shells;
  faceid 1..4 = the edges corner k -> k+1 (`mw.face_nodes` in S20/SA0 gives corner, mid,
  corner; 5/6 = the face). Thickness: the material's `<geometric type="Plate" thickness>`;
  plane strain adds `planestrain="1"` (seen by importing CPS4/CPE4 from a .inp). S20 without
  a thickness: no solution in Mecway; SA0 with a thickness: no solution either.
- Mecway's forces, gravity and reactions are for the whole thickness t (also in plane
  strain) and for 360 degrees in SA0 (measured with pressure, nodal force, edge force,
  traction, gravity, centrifugal). Code-Aster: per unit thickness (measured) and per radian
  (U4.44.01 §3.5): the bridge divides `FORCE_NODALE` by t or 2 pi, converts an edge force to
  `FORCE_CONTOUR` = F / (L t) or F / (2 pi int r dl), and multiplies `REAC_NODA` back
  (`aster_results_export`, `plane=`). `MASS_INER` of `AXIS` is already 360 degrees.
- Result names (Mecway's own S20/SA0 solution): `displx/disply/displmag` (no `displz`),
  `reactionforcex/y/mag`, `stressxx..stresszx` (yz = zx = 0; `stresszz` = 0, nu (sxx + syy)
  or the hoop stress), `vonmises`, `principal1..3`, `tresca` (3D eigenvalues); node and element
  node; no strain field in 2D. The bridge writes the same; after opening a bridge result Mecway
  adds the items displacement, stress, von Mises stress, reaction force, principal stress, Tresca
  stress, and `solution.node_value` reads the values.
- Built: `Scripts/bridge_plane.py` (modelisations and checks, 2D loads and constraints,
  factors) with hooks in `bridge_from_liml` (before STEP 4, `planestrain`), `bridge_mesh`
  (`convert_bc`, `finish_bcs`), `bridge_to_aster` (skin modelisation, plane modelisations
  post-processed as volumes, `FORCE_CONTOUR` its own load, export/static-check arguments, no
  error estimator) and `aster_results_export` (`plane=`: plane cells as continuum elements,
  reactions x factor, stressyz/zx = 0, magnitudes without Z, principal values with the
  out-of-plane shears 0). S20/SA0 -> `lin_static_3d` in `MECWAY_ANALYSIS_TYPES`.
- Verification (family PL, `tests_vlak_2d.py`): PL-01 Kt in plane stress as AD-01 (n = 16
  −0.79%, tolerance 2%), PL-02 plane strain, PL-03 Lamé plane strain (n = 8 the same
  numbers as LS-04 hex20: u_r −0.001%, sigma_theta −0.18%, sigma_z +0.42%), PL-04 Lamé
  axisymmetric (sigma_r at the loaded wall converges slower: n = 8 −0.97%, tolerance 1.2%),
  PL-05/PL-06 every load type with the reaction sum and the mass exact; displacements equal to
  Mecway's own solution (≤ 1e-11) in PL-01, PL-02, PL-04 … PL-06. All four element shapes equal
  to Mecway (cantilever, ≤ 1e-11; Mecway's quad4 in 2D is a plain bilinear element).
- Found: Mecway's pressure on curved quadratic edges has a resultant 0.16% too large
  (KNOWN_BUGS 125, PL-03); nodal stresses differ from Mecway where the stress varies strongly
  (other extrapolation, KNOWN_BUGS 3). Two `FORCE_CONTOUR` on one edge in one
  `AFFE_CHAR_MECA` kept only the last (fixed: own load each).
- Open: GUI run in Mecway 34 (open a PL model, run with `auto`, look at the contour of
  `stresszz`); whether Mecway's *in-plane principal stress* option (`principal1plane` in
  mecway.exe) needs other fields.

**Findings S16b (D20/DA0):**
- Mecway's D20/DA0 solution has the same names plus `velx/vely/velmag` (no reaction forces
  in Mecway's own dynamic solution). The bridge routes D20/DA0 through `dyna_impl_3d`
  (`bridge_plane.EQUIVALENT_3D`: the D30 output times and Newmark warning); the mass per
  unit thickness / per radian matches the forces, no extra factor. Explicit, mode
  superposition and an initial velocity: ERROR (not verified).
- Equal to Mecway's own solution (≤ 4e-8) with NEWMARK, PETIT and `substeps_per_output` =
  *every n time steps*: cantilever step load and time table (D20), ring with Rayleigh damping
  (DA0). With `substeps_per_output` = 1 and n = 5 the bridge steps 5 times coarser than Mecway
  (22% difference on the cantilever): pre-existing for D30 too (former KNOWN_BUGS 127);
  fixed 28 Oct 2026: the solver step is now derived from `<timesteps stepsize>` (MD-08).

**Findings S16d (A20, Acoustic Resonance 2D; Mecway 34.0.9772 headless, `mw_solve.py`, no GUI):**
- Mecway: `<analysis type="A20" maxmode="n" />`, the same tags as A30 (`speedofsound`,
  `density`, `<fluidpressure>` = 0 on edges (face selection, faceid 1..4) or nodes,
  `<impedance>` on edges) on tri3/tri6/quad4/quad8. A `<geometric type="Plate" thickness>`
  changes nothing (10 mm or none: identical frequencies and shapes); Z of the nodes is ignored
  (Z = 0.05 identical). Normalisation p^T M p = 1 per unit thickness (constant mode c/sqrt(A),
  406.378 Pa for 1.0 x 0.7 m). Result names as A30: `pressure` (+ `pressurei` and the decay
  rate with an impedance). No axisymmetric acoustic type: the analysis codes in mecway.exe are
  S20, SA0, S30, V30, D20, DA0, D30, T30, T31, E30, A20, A30, B30.
- Code-Aster: for `PHENOMENE='ACOUSTIQUE'` the 2D modelisation is `PLAN` (impedance edges
  `PLAN_ABSO`; catalogue affe_modele.py v17.4, test case ahlv100f). `2D_FLUIDE` (in the plan
  text) is the `MECANIQUE` fluid element of fluid-structure coupling (U_P_PHI), not the
  counterpart of the A30 route (`ACOUSTIQUE` `3D`); not used. `MASS_ACOU` of `PLAN` is per
  unit thickness, so the MASS_GENE normalisation gives Mecway's amplitudes without a factor.
- Built: `bridge_plane._apply_acoustic` (A20 only with `acoustic_modes_3d`, plane elements,
  Z = 0; `elset_modelisations` = PLAN, `model_data["acoustic_2d"]`, no `plane` factor),
  `bridge_acoustic._modelisations` (PLAN/PLAN_ABSO in the real and complex routes),
  `resolve_auto` keeps the modes for A20; `MECWAY_ANALYSIS_TYPES["A20"]`; glossary entry A20.
- Verification (`tests_akoestiek_2d.py`): AK-10 rectangle 1.0 x 0.7 quad8 (analytical
  ≤ +0.05%, Mecway ≤ 1e-6, |p| constant mode = c/sqrt(A)), AK-11 p = 0 on an edge + thickness
  10 mm, AK-13 quad4 in two elsets with a node selection, AK-14 impedance Z = 2000 (complex
  modes; f and decay rate = Mecway ≤ 1e-6, tube roots within 0.04%) all equal to Mecway.
  Triangles: Code-Aster's plane acoustic elements have no MASS integration family in elem.1
  (the mass uses the RIGI rule: tri3 1 point, tri6 3 points; reproduced exactly with an own
  one-point tri3 calculation), so AK-12 tri6 ≤ 0.003% and AK-15 tri3 +0.07 .. +0.64% above
  Mecway (KNOWN_BUGS 130). Mecway's organ pipe tutorial as A20 (497 elements, 20 modes): mode 4
  64.594 Hz (Mecway 64.592, manual 64.59). Mecway opens the bridge's A20 results and reads
  `pressure`/`pressurei` per mode with `solution.node_value` (headless script).
- `run_verificatie.py --mecway-opslaan AK-1`: all 126 checks identical with the models as
  Mecway 34 saves them, the same `.comm`.
- Full regression on 4e52f98 (Code-Aster 17.4): 2642 of 2648 checks OK (486 test cases), the
  6 BEKEND of the baseline (KNOWN_BUGS 43 x3, 83, 108, 115), 0 NOK/FOUT; no status change
  against the committed `resultaten.json`; AK/AH unchanged bit for bit, AI ≤ 2e-6 (one decay
  rate of AI-06, the same `.comm` apart from comments: noise of the iterative solve in
  `aster_acoustic_complex`). `resultaten.*` not committed (integration branch).
- Open: a run from the Mecway GUI; the harmonic pressure field in 2D (`acoustic_harm_3d`
  with PLAN/PLAN_ABSO, not built: ERROR).

### S17 – Loads on beam side faces and hydrostatic pressure on shell edges
**Goal:** the two open items of KNOWN_BUGS 5: pressure/traction on the side face of a beam (Mecway
computes them as a distributed beam load) and hydrostatic pressure on shell edges.
**Code-Aster:** `FORCE_POUTRE` (also as a function of X, Y, Z via `AFFE_CHAR_MECA_F`); shell edges via
`FORCE_ARETE` or nodal forces like `bridge_mesh._edge_loads`.
**Done when:** beam with pressure on a side face = beam with the equivalent line load (≤ 0.1%) and equal to
Mecway headless; hydrostatic pressure on a shell edge equal to the hand calculation; regression D.5.
**Findings (28 Oct 2026, Mecway 34 headless, internal solver):**
- A line2/line3 beam has three faces (`mw.face_nodes`): 1 = side face (all nodes), 2/3 = ends.
- Traction on the side face = distributed load traction x perimeter per length, global direction,
  independent of the orientation: RectBar 20x10 mm reaction 0.06 m x T x L; CircularBar pi d; tube
  pi (D + d) and RectTube 2(a + b) + 2(a + b - 4t) (outer plus inner wall); I/T/L/C the full outline;
  UniformGeneralSection its `perimeter`. A formula is taken at the beam axis, one point per element
  (z = 1 + 100 y gave the same as 1; z = x gave a tip 0.06% below the exact load). The premise "Mecway
  computes pressure as a distributed beam load" did not hold: pressure on the side face has zero
  resultant and the internal solver applies nothing (also with a formula); CCX expands the beam and
  only squeezes the section. Mecway's CCX gave a very different deflection for traction on the side
  face (1.47 against 21.4 m for the same load; not investigated, internal solver is the reference).
- Hydrostatic pressure on shell edges: Mecway applies nothing (internal solver and CCX; manual v34
  §9.17 "locally 2-dimensional" faces only), but it does apply a Pressure with the formula
  rho g (h - z) on the same edge (resultant 49.05 N = hand). The bridge applies the hydrostatic
  pressure (consistent nodal forces, edge length x thickness, 8 sub-segments where the free surface
  crosses an edge) with a WARNING; equal to Mecway's formula within 0.01%. `FORCE_ARETE` was not
  used: a function of X, Y, Z would need the pressure direction per edge (normal in the shell plane).
- Mecway 34 headless with *Fixed* on a node selection of shells computes a mechanism (known from
  LS-44); LS-93 uses displacement + node rotation.
- Not done: pressure as a formula on shell edges and beam ends (KNOWN_BUGS 104), traction on an
  element selection of beams, a GUI check.

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

### S19 – Beam element with warping (`POU_D_TG`) as element choice
**Goal:** open thin-walled sections (C, Z, L, T, also I) can buckle flexural-torsionally; `POU_D_E`/`POU_D_T`
have no warping and no shear-centre offset, so the bridge is up to 57% unconservative there
(KNOWN_BUGS 115, BU-35). Add `POU_D_TG` as a third choice for beams on the Elements page (default stays
`POU_D_E`), and mention it in the KB 115 WARNING.
**Code-Aster:** `POU_D_TG` (7th DOF `GRX`), `AFFE_CARA_ELEM POUTRE` `SECTION='GENERALE'` with `JG` (warping
constant) and `EY`/`EZ` (shear centre relative to the centroid), `AY`/`AZ`; check in the 17.4 catalogue and
U-docs which RIGI_GEOM terms couple bending and torsion through `EY`/`EZ`; official test cases with `POU_D_TG`.
**Research:** I_w and the shear-centre position from Mecway's dimensions (I, T, L, C, box, tube; thin-walled
formulas, Roark/Trahair) and what *UniformGeneralSection* supplies; warping at supports (Mecway has no warping
DOF): user decision 16 Oct 2026: warping blocked (`GRX` = 0) at *Fixed* and at every node where a rotation is
fixed in at least one direction (e.g. *Node rotation*, *Displacement* with a fixed rotation component, rigid
couplings that fix rotations), free elsewhere, with a setting to override this; log per node which rule applied;
results: section forces as now, bimoment only in the log/.mess; how line3 split, offset, joint and beam
orientation combine with the 7th DOF.
**Done when:** C-column flexural-torsional buckling within 3% of hex20 (≈ 393, BU-36) and thin-walled theory,
lateral-torsional buckling of an I-beam against Timoshenko & Gere, a Code-Aster test case with `POU_D_TG` equal
to VALE_CALC, symmetric sections unchanged with respect to `POU_D_E`, the warping rule checked on a cantilever
(clamped: warping blocked) and a fork-supported beam (only translations and the rotation about the beam axis fixed); docs NL+EN (Modaal_en_knik §3.5,
Mecway_functionaliteit, Standaardinstellingen), tooltip, KNOWN_BUGS 115 updated; regression D.5.
**Findings** (28 Oct 2026, branch worktree-agent-af7ab132aad22bc7d): input route: the existing setting
`elem_beam` (Elements page), fourth value `POU_D_TG`, plus a new setting `beam_warping` (`auto`/`free`/`blocked`)
on the same page; Mecway has no warping or switch for it. New module `Scripts/bridge_warping.py`:
(1) `section_props`: `EY`, `EZ`, `JG`, `IYR2`, `IZR2` of Mecway's I, T, C and L profiles with thin-walled theory
(centre-line tree, sectorial coordinate from the centroid, shear centre as the pole with zero sectorial products,
primary C_w plus the thickness warping t^3/12 int (r.e)^2 ds of each plate; Wagner integrals exact over the
rectangles); checked against closed forms (I: t_f b^3 h^2/24; C: Timoshenko & Gere 5.3) and the angle of
Code-Aster test case ssll103a (EY 40.96 vs 41.012 mm, JG and IYR2 within 0.12%). A general section takes JG,
EY/EZ, IYR2/IZR2 from `#ASTER-SECTIE` (MecwaySectionProps; JG/IYR2/IZR2 are now passed for `POU_D_TG` only),
without such a line JG = 0 and EY = EZ = 0 with a bilingual WARNING. RECTANGLE/CERCLE stay as they are (Code-Aster
17.4 accepts them on `POU_D_TG`, LS-01/LS-30 runs). (2) `warping_nodes`: node group `BRGRX` with `DDL_IMPO GRX=0`
(`bridge_mesh.write_mesh` after offsets and joints, `bridge_to_aster._build_charges`). Measured: `BLOCAGE=
('DEPLACEMENT', 'ROTATION')` of a Fixed support does NOT fix GRX (C column 343.8 without, 385.0 with GRX = 0).
Sign convention EY/EZ = vector shear centre -> centroid (U4.42.01 par. 9.4.3 "composante de CG"; consistent with
ssll103a where positive EY goes with positive IYR2, and with MecwaySectionProps); for an axial load the sign does
not matter (checked: +-EZ give the same factors).
Deviation from the recorded user decision ("warping blocked where a rotation is fixed in at least one direction"):
`auto` blocks the warping only where a rotation ACROSS the beam (a bending rotation) is fixed, so that a fork
support (translations plus the rotation about the beam axis) keeps the warping free, as in the handbook cases
(Timoshenko & Gere 6.2) and as the done criterion of this step asks ("fork-supported beam: only translations and
the rotation about the beam axis fixed"); with the literal rule the fork would be clamped for warping and BU-39 /
LS-91 would come out too stiff. `blocked` gives the literal behaviour (every supported node), `free` none.
Rigid couplings (`rigidbody`) on a beam node block the warping; RBE3 does not. Flexible joints and offset beams
lie on own nodes without a support: the warping is free there (documented). Results: displacements/rotations as
before (GRX itself is not sent to Mecway), section forces from EFGE (BX bimoment not sent).
Verification (tests_balk_welving.py): BU-38 C column 384.98 (-0.29% from thin-walled theory, -2.0% from hex20
BU-36, criterion 3%), BU-39 I beam on forks M_cr -0.10% (Timoshenko & Gere 6.2), BU-41 ssll103a equal to
VALE_CALC (modes 1, 8, 19), BU-41b the same angle as Mecway L profile -2.2% (Mecway's J 1.9% below the test's,
AY/AZ 2.4 instead of 1; tolerance 3%), BU-42 T column -0.59%, LS-90 torsion with restrained warping -0.09%,
LS-90b free warping exact, LS-90c `POU_D_E` unchanged, LS-91 fork + midspan torque -0.22%. 20 existing beam
cases run with `POU_D_TG` (static, modal, buckling, nonlinear PETIT, harmonic, implicit dynamics, line3, joints,
offsets, shells): all diagnostics OK. Found: nodal reactions of `POU_D_TG` are off in Code-Aster 17.4 (support
103.0 N instead of 100 N in LS-01, sum right; vanishes with AY -> 0, not with POU_D_T): WARNING and KNOWN_BUGS
122. Explicit dynamics: `POU_D_TG` has no mass for GRX (MECANONLINE_78, then FACTOR_11 in DY-02 with DIFF_CENT),
so the beams become `POU_D_T` there with a WARNING (`bridge_from_liml._warp_beam_choice`; run OK after it).
Open: a GUI test in Mecway 34 (the Elements page renders the new choice and setting, offscreen gui_cap);
lateral-torsional buckling of mono-symmetric sections (T, C under bending) only checked through the shared
IYR2/EY convention of ssll103a, not against a shell model (done in the second follow-up below).
Follow-up (29 Oct 2026): Mecway's section axes measured headless (Mecway 34, own solver) from its stress
recovery points `stresspt1..4` under end moments about V and W (C, T and three L profiles, match within
1e-13): the drawing x of `_rects` runs along -W (C web at +W, so the shear centre at +W and EZ < 0; the bridge
had the opposite sign) and the L principal angle is wrapped into (-45, 45] degrees (for a > b the bridge had
swapped IY/IZ, also with POU_D_E). Fixed in `bridge_warping.mecway_frame`/`principal_angle` (used by
`_profile_props`, `_profile_shear_coefs`, `section_props` and the beam sidecar `bridge_beams`). New cases:
LS-94/LS-94b C cantilever, transverse tip load through the centroid, twist F e/(GJ)(L - tanh(kL)/k) -0.38%
(sign confirms Code-Aster's EY/EZ = shear centre -> centroid); LS-95 L 120 x 80 POU_D_E equal to Mecway;
LS-95b L twist -0.005%; LS-90d bimoment at the clamp (max |BX| of EFGE_ELNO printed to the .mess with
#ASTER-POST) +0.51% from T tanh(kL)/k. BX sign not compared.
Second follow-up (29 Oct 2026): lateral-torsional buckling of mono-symmetric sections and the sign of BX
verified; the bridge was right, nothing changed in `Scripts/`. BU-43/43b: T 100 x 10 x 10 x 90 mm, L = 2 m,
fork supports, uniform moment, both signs in one model: flange in compression 63.313 (formula 63.576,
-0.41%), stem in compression 35.366 (35.448, -0.23%); formula M_cr = P (beta/2 +- sqrt(beta^2/4 + I_w/I_z +
GJL^2/(pi^2 E I_z))) with beta = int y (x^2 + y^2) dA/I_y - 2 y0 (Trahair 1993 ch. 6, SSRC Guide ch. 5),
section values written out in the test independently of the bridge. BU-44/44b: C 100 x 50 x 6 mm bent about
the minor axis V (checks EZ with IZR2), L = 4 m: 7.6458 (7.6497, -0.05%) and 31.150 (31.265, -0.37%). BU-43c:
the T at L = 4 m against a shell model of quad4 plates in Mecway 34 headless (own solver, 400 x 20 elements):
27.459 / -20.438 against the shells 27.081 / 20.228 (+1.4% / +1.0%) and the formula 27.484 / -20.452. The
same shell model in Code-Aster (DKT) gives 18.76 / -7.77 with spurious in-plane modes: the DKT geometric
stiffness has only the out-of-plane terms of each plate (R3.07.03 par. 4.6), KNOWN_BUGS 132. BX: LS-90d now
compares the signed value (and GRX at the tip), LS-90e the reversed torque: Code-Aster's BX = +E I_w phi''
with GRX = phi' (the opposite of Vlasov's B = -E I_w phi''), +-15.333 against +-15.255 (+0.51%); the
installed U4.42.01/R3.08.01 do not define the sign. All S19 cases (BU-35 .. BU-44b, LS-90 .. LS-95b)
rerun: unchanged, all OK.


### S20 – Geometrically nonlinear beams (`POU_D_T_GD`) as element choice
**Goal:** beams with large displacements and rotations in nonlinear static (today beams stay geometrically linear,
`PETIT`, with a warning; KNOWN_BUGS 11). Add `POU_D_T_GD` as a choice for beams on the Elements page (default stays
`POU_D_E`).
**Credit:** idea, Code-Aster route and benchmarks come from the fork by MishalTPC
(https://github.com/mishal0488/MecwayAsterBridge, branch `dev`, commit dd4c958 "Add elastic geometric-nonlinear beam
support and benchmarks", MPL-2.0): `MODELISATION='POU_D_T_GD'`, `RELATION='ELAS_POUTRE_GR'`, `DEFORMATION='GROT_GDEP'`,
section forces from `SIEF_ELNO` (17.4 has no `SIPM_ELNO`, `RIGI_GEOM` or `CHAR_MECA_ROTA_R` for this element),
AY/AZ estimated for I/T/C/L sections, a clear ERROR for unsupported analyses (linear, modal, buckling, dynamics),
plastic beam material, non-SEG2 beams and centrifugal load. Their benchmarks GB-01 (small-load Timoshenko cantilever),
GB-02 (90-degree pure bending) and GB-03 (initially curved column amplification) agreed within 0.02%. Re-implement in
the current code (the fork is based on V2026.1) and credit the fork in CHANGELOG/README.
**Research:** combination with what was built after V2026.1: line3 split into SEG2 halves (allowed?), element offset
(rigid arms are linear `LIAISON_DDL`: KNOWN_BUGS 108a), flexible joint, beam orientation (explicit `VECT_Y`), result
field `beam_forces` (EFGE_* vs SIEF_ELNO for `POU_D_T_GD`), follower loads and imposed rotations, Mecway's own
large-deformation beam behaviour (compare with Mecway 34 / CCX where Mecway can solve it), and memory note: earlier a
rigid 90-degree rotation with `POU_D_T_GD` converged badly in the ProfielBuigen model.
**Done when:** GB-01..03 rebuilt as verification cases (NL-8x) within 0.1% of the analytical references, the
existing small-rotation beam cases unchanged, clear messages for unsupported combinations, docs NL+EN (Instellingen
contact en niet-lineair, Mecway_functionaliteit, Standaardinstellingen), tooltip, KNOWN_BUGS 11 updated;
regression D.5.
**Findings** (16 Oct 2026, b366f94): input route: the existing setting `elem_beam` (Elements page), third value
`POU_D_T_GD`; Mecway has no switch for it. Route as in the fork: `POU_D_T_GD` + `ELAS_POUTRE_GR` + `GROT_GDEP`,
AY/AZ as `POU_D_T` (`_profile_shear_coefs`, unchanged). Measured with Code-Aster 17.4 runs: `EFGE_ELNO` is in the
catalogue but stops with `DVP_1` (`te0185.F90`), so `beam_forces` comes from `SIEF_ELNO`/`SIEF_NOEU` (same component
names and signs as `EFGE_*` of `POU_D_T`, co-rotating axes, one value per element); `SIPM_ELNO`, `RIGI_MECA` and
`CHAR_MECA_ROTA_R` give `CALCUL_37`; `CRIT_STAB` gives `ALGELINE4_41` (non-symmetric tangent). Decisions: outside
`STAT_NON_LINE` with large displacements the beam becomes `POU_D_T` with a WARNING (like DST -> DKT); `crit_stab` and
`imperfection_amplitude`: ERROR; centrifugal force via the FORMULE route; plastic material elastic (WARNING, as the
other beams); line3, orientation card, offset and joint work (offset/joint/couplings stay linear relations: WARNING).
Imposed rotations: `DDL_IMPO` DR* is the total rotation vector (test case zzzz364a); a stocky beam rotated rigidly
through 90 degrees exactly, a slender one (10 x 20 mm, L = 1 m) stopped at 0.41 rad also with 5x smaller steps (this
explains the earlier ProfielBuigen observation): WARNING, KNOWN_BUGS 11. Mecway 34 computes nonlinear beams only
with CCX (its own solver gave no solution headless): NL-82/NL-83 within 0.016 % of Mecway/CCX, CCX did not get the
end moment of NL-81 past t = 0.55 s. Verification NL-80 .. NL-89 (12 cases, 51 checks: 41 in series, 10 with in_series=False) all OK, GB-01..03 equal to
the fork's numbers; NL, LS-3..LS-7, MO, BU, DY (134 cases) bit-identical. Open: a GUI test in Mecway 34, implicit
dynamics with `POU_D_T_GD` (sdnl103a exists, not built), finite-rotation offset arms/joints.
Follow-up after the documentation review (branch s20-fix): element failure in a model with `POU_D_T_GD` gives
CALCUL_37 at the first failure (the loop restarts with `PREDICTION='ELASTIQUE'`; `TANGENTE` and `EXTRAPOLE` did not
converge, runs 17.4): ERROR in `_check_gd_beams`. Trusses (`BARRE`) in the centrifugal FORMULE route get
`FORCE_POUTRE` (was an ERROR "not translated"). `aster_results_export._report_missing` no longer reports the
`beam_forces` source of the other beam formulation (EFGE_* vs SIEF_*). New cases NL-80c (constant force and
moment) and NL-86b (truss + GD beam, centrifugal): 14 cases, 55 checks (45 in series, 10 with in_series=False).

### S21 – Selective flexible joint on `POU_D_T_GD` beams (GD stub)
**Goal:** replace the ERROR of `bridge_to_aster._check_gd_joints` (a flexible joint with only some of U, V, W free
on a `POU_D_T_GD` beam, KNOWN_BUGS 106b) by a physically sound joint, but only if two benchmarks pass (user's
decision). Code-Aster 17.4 has no objective partial hinge: `LIAISON_DDL` on DR* is a relation in fixed axes,
`DIS_TR` does not co-rotate, `LIAISON_SOLIDE` is refused on nodes with DR*, and there is no hinge element.
**Method (prototype):** per selective joint a short connecting `POU_D_T_GD` element (stub) from the joint node A to a
new node C = A + L_h e1 on the side of the released element (that element reconnected to C), L_h = 1e-3 L_e, with
the beam's A, AY, AZ and JX and a near-zero IY and/or IZ in the released local directions,
EI_h = c EI L_h/L_e with c = 1e-5, `ORIENTATION VECT_Y` = the beam's y axis, in the same `STAT_NON_LINE`
(`ELAS_POUTRE_GR`, `GROT_GDEP`). Expected bounds: hinge position error L_h/(2 L), residual moment EI_h theta/L_h.
**Pass criteria (fixed before the runs):** B1 joint and member moments < 1e-6 M_ref (M_ref = EI/L x 1 rad) and
forces < 1e-6 EI/L^2 under a rigid rotation, also after a closed rotation path; B2 end rotation and shortening
within 0.5 % of the elastica at the default stub parameters.
**Results** (22 Oct 2026, hand-written .comm files, Code-Aster 17.4, ncpus 1; frame of two members of 1 m,
10 elements each, section 10 x 20 mm, joint at the corner; column of 1 m, 40 elements):
- B1, objectivity: **failed, and not because of the stub.** With all node translations imposed as an exact rigid
  rotation (FORMULE in INST, rotations free) the plain frame *without* stub is exact for a rotation about a global
  axis (X, Y or Z: moments < 3e-13 M_ref over 120 degrees), but about a skew axis (1,1,0) it builds up spurious
  section forces that depend on the step size: at 10 degrees max |M| = 6.0e-2, 2.6e-2, 4.6e-3, 6.4e-4 M_ref with
  2, 4, 8, 16 steps; over 120 degrees about (1,2,3) it reaches 4 M_ref at 60 degrees and stops converging
  (MECANONLINE9_7/9_4, also with 0.5-degree steps, `PREDICTION='EXTRAPOLE'` does not help, `ELASTIQUE` gives
  CALCUL_37). The Newton residual at the start of each equal rotation step grows with the accumulated rotation
  (1.6e3, 2.6e3, 3.7e3, ... 5.7e4 N), so the element does not respond objectively to a rigidly rotated increment:
  an incremental (path-dependent) update of the strains, the behaviour Crisfield & Jelenic (1999) describe for
  interpolated incremental rotations (the Fortran is not in the installation: NOT verified in the source). With the
  stub (W or VW released) the members show the same 6.4e-4 M_ref, the stub's retained moment 2.6e-6 M_ref and the
  forces 5e-2 F_ref (8x the frame without stub: the short stiff stub amplifies the spurious shear). The closed path
  (60 degrees about Y, then 60 about Z, back along the geodesic) did not get past 70 degrees (TimeLimitError after
  15 min, subdivision level 7), so no residual torsion moment could be measured. Driving only three nodes instead of
  all gives the same failures plus Newton divergence.
- B2, hinged elastica (in-plane, rotations about one global axis): **passed.** Load control up to 2 P_cr,
  imperfection 1e-3 L. Ideal hinge (free DRZ at the end nodes) against the elastica (Timoshenko & Gere): end rotation
  +0.26/-0.02/-0.05 %, shortening +0.89/+0.18/+0.04 %, midspan deflection +0.04/-0.20/-0.23 % at P/P_cr = 1.2/1.5/2.0
  (the 0.9 % at 1.2 is the imperfection close to bifurcation). Stub with the defaults: end rotation +0.20/-0.05/-0.07 %,
  shortening +0.77/+0.14/+0.02 %, mid -0.00/-0.20/-0.22 %; residual stub moment 1.1e-4 of P delta, equal to the bound
  EI_h alpha/L_h. Stub minus ideal hinge at 2 P_cr (end rotation): -0.015 % (defaults), -0.13 % (c = 1e-4),
  -0.004 % (c = 1e-6), -0.040 % (L_h = 1e-2 L_e): scales with c and L_h as the bounds predict. Conditioning: with
  `RESI_GLOB_RELA` = 1e-8 the stub run stalls at a residual of ~1e-6 (round-off), with 1e-5 (bridge default) it
  converges.
**Conclusion:** the stub works as a hinge in plane, but the objectivity benchmark fails for every `POU_D_T_GD`
model with rotations about a skew axis, so a stub cannot be shown to be objective in 3D. ERROR kept (user's rule);
the spurious forces under skew rigid rotation are recorded as a limitation of `POU_D_T_GD` in KNOWN_BUGS 11. Possible
follow-up (not planned): an in-plane-only stub (joint axis and all loads in one plane) with its own benchmark, or a
re-test with Code-Aster 18.

### S22 – Hide failed or eroded elements in post-processing (ParaView Threshold)
**Goal:** after a run with element failure, show the model without the failed (Code-Aster) or eroded
(OpenRadioss) elements. Code-Aster keeps failed elements as soft elements (`bridge_failure`,
`failure_stiffness_factor`), OpenRadioss really deletes them; Mecway 34 cannot hide elements by value.
**Parts:** (a) an element field "failed" (0/1 per step) written to Mecway, so the user can colour it with
the contour range; (b) a generated pvpython/ParaView script with a `Threshold` filter on that field, hooked
to the ParaView button of the convergence window: for Code-Aster the Salome-Meca ParaView with the MED reader
on the `.rmed`, for OpenRadioss `anim_to_vtk_win64.exe` with the `EROSION_STATUS` cell field; (c) docs NL+EN.
**Research:** how `bridge_failure` marks a failed element per step (internal variable or own field), the
field name and its route back (`FIELD_TABLE` in `aster_results_export.py`, `RESULT_FIELD_SPECS`), where the
Salome-Meca `pvpython` lives and how `aster_convergence_monitor.py` starts ParaView now.
**Done when:** a failure case (Code-Aster) and an erosion case (OpenRadioss) show the field "failed" in Mecway
(0/1 equal to the failed elements in the log) and the ParaView button opens the model with the failed
elements hidden per step; docs NL+EN and a verification case for the field; regression D.5.

### S23 – Linear buckling with a constant (dead) plus a variable (live) load
**Goal:** buckling factor of the live load only, with the dead load present: stiffness K + Kg(dead) and
`MATR_RIGI_GEOM` = Kg(live) in `CALC_MODES TYPE_RESU='MODE_FLAMB'`, so the critical load is
dead + lambda x live.
**Source:** J.-P. Aubry, *Beginning with code_aster* (2019), §16.1–16.2.
**Research:** input route for marking a load as constant (Mecway-native, e.g. a load table or a separate
load group, otherwise a `#ASTER` keyword, see the memory rule on input); how the bridge builds the buckling
matrices now (`bridge_to_aster`, buckling builder); a check that the dead load alone is below critical
(a negative or smallest factor of K + Kg(dead) alone), which must stop with an ERROR NL+EN instead of a
meaningless factor.
**Done when:** a column with an axial dead load of 0.5 P_cr plus a live load gives lambda = 0.5 P_cr/P_live
within 1 %; a dead load above P_cr stops with the ERROR; docs NL+EN (Modaal_en_knik/Modal_and_buckling) and a
verification case.

### S24 – Adaptive time stepping from Mecway's automatic time stepping
**Goal:** `DEFI_LIST_INST(METHODE='AUTO', PAS_MINI=..., PAS_MAXI=...)` when the `.liml` has Mecway's
`automatictimestepping`, while Mecway's output times stay in the results through `ARCHIVAGE`.
**Source:** J.-P. Aubry, *Beginning with code_aster* (2019), §14.1; U4.34.03 (DEFI_LIST_INST); catalogue `defi_list_inst.py` (17.4).
**Research:** the `.liml` attributes of automatic time stepping (minimum/maximum step, initial step) and their
meaning in Mecway's manual; how `METHODE='AUTO'` combines with the existing `ECHEC` subdivision and
`ADAPTATION`; `ARCHIVAGE LIST_INST`/`PRECISION` for the output times; whether `aster_results_export` copes with
archived times that differ from the computed ones.
**Done when:** a nonlinear case with automatic time stepping solves with fewer steps than the fixed list and
gives the same results at the output times (within the case tolerance); the NL families stay within tolerance;
docs NL+EN.
**Result** (23 Oct 2026, Code-Aster 17.4, ncpus 1): Mecway 34 keeps `automatictimestepping="true"` on save in
both formats (internal solver with `stepsize`, CCX with time points; no min/max step attributes exist, strings
of Mecway.exe). Seen with 17.4: with `METHODE='AUTO'` the times of `DEFI_LIST` are mandatory solver points,
`ARCHIVAGE LIST_INST` times are not (list 0, 0.1, 2, 3 gave 0.1, 0.2, 0.4, 0.6, 1.0, 1.4, 2.0, 2.4, 3.0; archive
times 0.5/1.5/2.5 skipped). So `_auto_listinst_block` puts Mecway's output times plus the load kinks in the list,
`PAS_MAXI` = Mecway's step/time-point interval, `PAS_MINI` = 1e-6 of it, the existing `ECHEC DECOUPE` kept,
and `ARCHIVAGE` on the output times (the failure loop archives every step). Dynamics: not changed. The
convergence parser now also reads step lines without "Niveau de découpe" (AUTO). NL-21a (stepsize 0.4 s): times
and values as NL-20; NL-21b (CCX time points 0.5 s): 6 instead of 30 steps, values within 0.2 % (exact). Temporary
flagged copies: NL-90 equal within 0.01 % (40 steps instead of 23: after a cut the step regrows gradually),
NK-04 P_u/Pcr 0.480 instead of 0.488 (within tolerance). All 58 NL/NK cases without the flag: identical to the
baseline (only NL-03a known, KNOWN_BUGS 43).

### S25 – Optional exact section properties with `MACR_CARA_POUTRE`
**Status:** dropped (28 Oct 2026): the user's tool MecwaySectionProps computes the exact section
properties and writes them as `#ASTER-SECTIE` lines, which the bridge reads (docs/ASTER_regels_voorbeelden.md);
a second route inside the bridge is not needed.
**Goal:** a setting (default off: Mecway's values, including J, stay the default) that computes A, IY, IZ, JX,
JG, AY/AZ and the shear centre of I/T/C/L and general sections with `MACR_CARA_POUTRE` on a 2D mesh of the
section, and uses them in `AFFE_CARA_ELEM`.
**Source:** J.-P. Aubry, *Beginning with code_aster* (2019), §17.1–17.2; U4.42.02 (MACR_CARA_POUTRE).
**Research:** making the 2D section mesh without Gmsh (the bridge writes meshes itself, `bridge_mesh`); which
outputs `MACR_CARA_POUTRE` gives in 17.4 (table names); a second Code-Aster job before the analysis or one job
with the table read in the `.comm`; the shear centre offset versus Mecway's beam axis.
**Done when:** for an I- and a C-section the computed properties match handbook values (A, I within 0.5 %, J
within 5 %); with the setting off the `.comm` is unchanged; docs NL+EN.

### S26 – Hysteretic damping in harmonic analysis
**Goal:** structural (hysteretic) damping eta via `AMOR_HYST` in `DEFI_MATERIAU` and `RIGI_MECA_HYST`
(complex stiffness) in the harmonic analysis.
**Source:** Aubry, *Beginning with code_aster DYNAmics*, §3.3.4 and §6.
**Research:** the input route: does Mecway have a structural damping factor in harmonic analysis (check the
manual and a saved `.liml`), otherwise a `#ASTER` keyword; whether `harmonic_3d` (on a modal basis,
`DYNA_VIBRA HARM`) can take a complex stiffness or needs a direct (`PHYS`) solve.
**Done when:** a single-DOF-like case (cantilever) gives the resonance amplitude 1/eta times the static one
within 2 %; docs NL+EN; a verification case.
**Result** (23 Oct 2026, Code-Aster 17.4, ncpus 1): Mecway has no loss factor (manual v34: only Rayleigh
damping and the Damper material), so the input is the setting `loss_factor` (all materials) and
`#ASTER-HYST material = eta` (per material, also springs via `AFFE_CARA_ELEM DISCRET AMOR_HYST`). PHYS:
`MATR_RIGI=rigi_hyst`. GENE: `PROJ_BASE` refuses a complex matrix (SUPERVIS_4), so `NUME_DDL_GENE` +
`PROJ_MATR_BASE`/`PROJ_VECT_BASE` in full storage (complex generalised stiffness, exact also for an eta
per material). HR-06a/b (spring-mass, eta 0.04): |U| within 4.3e-8, peak u_st/eta = 0.25 m (PHYS at f_n
exact, -90.00 deg); HR-06c/d (cantilever, eta 0.02): 2.1e-4 against Euler-Bernoulli with E(1 + i eta),
peak 0.99997 x (12/lambda_1^4) u_st/eta. Open: eta on other discrete elements; stresses use the real E
(NOT verified whether CALC_CHAMP includes the eta part).

### S27 – Optional line search (`RECH_LINEAIRE`)
**Goal:** a setting for `RECH_LINEAIRE` in `STAT_NON_LINE` (method and `ITER_LINE_MAXI`), optionally automatic
for models with `CABLE` or `GROT_GDEP`.
**Source:** J.-P. Aubry, *Beginning with code_aster* (2019), §10.2; U2.04.01 (nonlinear computations advice); U4.51.03.
**Research:** which methods 17.4 offers (`CORDE`, `MIXTE`, `PILOTAGE`) and which suit cables; whether line
search changes the converged result (it should not) and how much it costs per iteration.
**Done when:** a cable case (e.g. SaggingCable with *Tension only*) converges with fewer cuts or iterations; the
NL families stay within tolerance; docs NL+EN.
**Result** (23 Oct 2026, Code-Aster 17.4, ncpus 1): setting `line_search` (nonlinear static, implicit
dynamics): `auto` (default) = `RECH_LINEAIRE=_F(METHODE='CORDE', ITER_LINE_MAXI=3)` only with `CABLE` and without
contact, `on`, `off`; never explicit; with contact `CONTINUE` omitted with a WARNING (`MECANONLINE3_91`:
incompatible). `MIXTE`/`PILOTAGE` not offered (`PILOTAGE` needs a PILOTAGE keyword). LS-54b/c with `auto`: identical
(1.6e-14). SaggingCable with *Tension only*: 9 -> 7 Newton iterations, results within 8e-7. With `on`: NL-01, 01b,
02a, 02b, 04, 04b/c, 80c, 86, 86b, 87, 87b, 88, 90b within 6e-6; NL-03a..f unchanged (omitted); but `POU_D_T_GD`
NL-81/83/84/85/90 stop without convergence (`MECANONLINE9_7`), NL-82 7.6% off, NL-80/89 1000-2000 substeps and
0.6-0.7% off. Hence `auto` = cables only and a WARNING for `on` with `POU_D_T_GD`. The thermal-mechanical chain
keeps its own `RECH_LINEAIRE` (ITER_LINE_MAXI=5 with plasticity).

### S28 – Optional contact normal smoothing (`LISSAGE='OUI'`)
**Goal:** a setting for `LISSAGE='OUI'` in `DEFI_CONTACT` (normals smoothed over the master surface), for
contact on faceted curved surfaces.
**Source:** U4.44.11 (DEFI_CONTACT); catalogue `defi_contact.py` (17.4).
**Research:** which formulations accept `LISSAGE` (continue, penalty); effect on convergence and on the contact
pressure of a curved contact case (e.g. Samples/PipeClip).
**Done when:** a curved contact case gives a smoother contact pressure with the same total force (within 1 %);
the contact families stay within tolerance with the setting off and on; docs NL+EN.
**Result** (23 Oct 2026): setting `contact_smoothing` (bool, default off) writes global `LISSAGE='OUI'` in the
CONTINUE `DEFI_CONTACT` (bloc `b_contact_mail`, catalogue `defi_contact.py` 17.4; a user `#ASTER-CONTACT LISSAGE`
takes precedence). Off: NL-03a..f `.comm` identical to the baseline. On: NL-03a..f within 6e-8; Samples/PipeClip
(tet10, PENALISATION, MAXI) runs, total contact pressure equal (max 2913.7 vs 2913.8), so the fine mesh shows no
effect; a coarse faceted case was not built.

### S29 – Penetration check for penalty contact
**Goal:** with `contact_algo` = PENALISATION, report too much penetration with
`ECHEC=_F(EVENEMENT='INTERPENETRATION', PENE_MAXI=..., ACTION='ARRET')` or a WARNING NL+EN after the run, not
an automatic change of the penalty coefficient (`ACTION='ADAPT_COEF_PENA'`), in line with the rule "clear
messages over automatic fixes".
**Source:** U4.34.03 (DEFI_LIST_INST ECHEC); catalogue `defi_list_inst.py` (17.4: `INTERPENETRATION` with
`ARRET` or `ADAPT_COEF_PENA`).
**Research:** a sensible default for `PENE_MAXI` (relative to the element size or the contact face), and how
the bridge reports the stop (error code and explanation in `docs/Foutmeldingen_CodeAster.md`).
**Done when:** a penalty case with a too soft `normalstiffness` stops (or warns) with a clear message that names
the setting to change; the contact families with a normal stiffness stay unchanged; docs NL+EN.
**Result** (23 Oct 2026, Code-Aster 17.4): `ECHEC=_F(EVENEMENT='INTERPENETRATION', PENE_MAXI=1e-4,
ACTION='ARRET')` with `FORMULATION='CONTINUE'`, `ALGO_CONT='PENALISATION'` stopped in the first step with
`<EXCEPTION> JEVEUX_26` (`&&OP0070.RESOC.COCO` missing, a discrete-formulation object) and no results: not
usable. Built instead: the .comm prints `BRIDGE_PENE_MAXI <limit> <edge>`; after the run
`bridge_run_aster.penetration_report` takes the largest `CONTACT PENETRATION` (convergence table, last
iteration of each converged step; equals p/kn exactly in the patch test) and gives a bilingual WARNING (log and
message) above `contact_pene_maxi` (default 0.05) x the shortest slave edge. Results unchanged. NL-03p (kn 1e10,
1 mm = 15 %): WARNING; NL-03b/d/f and NL-30b/c: none, values identical.

### S30 – Redo the Code-Aster forum research
**Goal:** repeat the forum searches of earlier steps (e.g. KNOWN_BUGS items marked "NOT verified" and open
questions) once the code_aster forum is online again: it was offline until about 30 Oct 2026 because of a PHP
vulnerability.
**Research:** the list of open questions that waited for the forum (search KNOWN_BUGS and the docs for
"forum"); per item the thread or the answer.
**Done when:** each item has a forum source or is marked "no answer on the forum" with the date.

### S31 – LAC (mortar) contact as an option
**Goal:** long-term: `DEFI_CONTACT FORMULATION='CONTINUE', ALGO_CONT='LAC'` (mortar) as a choice besides
STANDARD and PENALISATION, for non-matching meshes and pressure-accurate contact.
**Source:** U4.44.11 (DEFI_CONTACT), R5.03.55 (LAC).
**Research:** the mesh requirements of LAC in 17.4 (`DECOUPE_LAC` of the slave surface, linear/quadratic faces),
which of Mecway's contact options carry over, and the convergence on the existing contact cases.
**Done when:** the contact families solve with LAC within tolerance where STANDARD does; limitations documented
NL+EN.

### S32 – Extra Newton iterations before step cutting (`ACTION='ITER_SUPPL'`)
**Goal:** in `_LISTINST_ECHEC` (`bridge_to_aster`) `ECHEC=_F(EVENEMENT='ERREUR', ACTION='ITER_SUPPL',
PCENT_ITER_PLUS=50, SUBD_METHODE='MANUEL', SUBD_PAS=4, SUBD_NIVEAU=6)` instead of `ACTION='DECOUPE'`, so that Newton
may continue while the residual still decreases before a step is cut.
**Source:** catalogue `defi_list_inst.py` (17.4): the `ITER_SUPPL` block contains `SUBD_METHODE` and the
`MANUEL`/`AUTO` subdivision keywords; the `.mess` of a run states "quand ce maximum sera atteint, on pourra
découper le pas de temps"; messages `ITERSUPP_6`/`MECANONLINE10_33`. So the step cutting stays as a fallback:
seen in NL-83 (one extra-iteration attempt succeeded, the next failed with `ITERSUPP_6` and the step was cut).
**Result** (23 Oct 2026, all 60 `nonlin_static_3d` cases, Code-Aster 17.4, ncpus 1): 58 cases unchanged
(within 1e-4); NL-03a (known failure, KNOWN_BUGS 43) stopped earlier, now without any results; ITER_SUPPL was tried 9 times (NK-04 7, NL-83 2) and avoided a cut only twice (NK-04 kept its
7 cuts and ran 72 s instead of 52 s). **NL-90 failed:** in the step to t = 0.1 the Newton iterations are identical in both runs (residual 2.8e1 .. 1.4e5, not converging) until the tangent matrix becomes singular at iteration 14. With `DECOUPE` that is caught as an `ERREUR` event ("La matrice du système est singulière", `MECANONLINE10_33`), the step is cut and the case solves (tip within 0.01 %); with `ITER_SUPPL` the same singular matrix is raised as `<EXCEPTION> FACTOR_11` and the run stops at t = 0.05 (tip u_y 0.033 instead of 0.493 m). So the fallback works for non-convergence but not for a singular matrix (NOT verified in the source; seen in the .mess). **Dropped**; `ACTION='DECOUPE'` kept.
**Possible follow-up (not planned):** only with a convergence criterion that stops the extra iterations when the
residual rises (`EVENEMENT='DIVE_RESI'` before `ERREUR`), with its own regression run.

### S33 – Evaluate Mecway result formulas in the bridge
**Goal:** a `<formula>` in the model (*Solution > Formula*) gets its values from the bridge, as
Mecway does during its own solve: nodevariable named after the `fieldscalar` (`formula`,
`formula(2)`, ...) in every time step (KNOWN_BUGS 121, GitHub issue #8).
**Research first:** Mecway's formula syntax (operators, functions, `^`), the full list of symbols
and which result variable each one reads (the list in Mecway's formula window: `u.x`, `s.xx`,
`qf.x`, `FR.x`, `x`, `t`, ...), node or element-node values, and the units: are the symbols SI and
what do the `<unit exponents=...>` lines change (measure with Mecway's own solve: a formula's
stored values against the variables it uses, as for `qf.x` on TH-01a). Symbols of fields the
bridge does not write: WARNING, formula left out.
**Build:** evaluator in `aster_results_export` (numpy, no `eval` of user text: own small parser),
after the other variables; WARNING in `bridge_from_liml` only for formulas it cannot evaluate.
**Verify:** formulas on TH-01a, a static and a nonlinear case against Mecway's own solve.
**Status:** done (28 Oct 2026, branch stap-S33).
**Findings:**
- Input route: Mecway itself, nothing new for the user. `<formula name fieldscalar>` with
  `<unit exponents="...">unit</unit>` lines and `<formula>text</formula>`; Mecway stores the
  values as nodevariable `<fieldscalar>`. Measured with Mecway 34 (headless `mw_solve.py`, and in
  the GUI with an own Mecway window and screenshots):
  - exponents are powers of (length, mass, time, current, temperature), trailing zeros left out
    (`+1` m, `-1+1-2` Pa, `+0+1-3` W/m2, `+0+0+1` s, `+0+0+0+0+1` K, `""` dimensionless);
  - each symbol is converted from SI to the unit of its dimension, then the formula is evaluated
    and stored without converting back (x in mm 50 for 0.05 m; T in degF 100.018 for 310.938 K,
    affine; qf.x in Btu/h/ft2 -11887.4 for -37500 W/m2); an unknown unit counts as SI;
  - the symbols read Mecway's node values; e.xx = lstrainxx, g.xy = lstrainxy (engineering);
    FR.x only on the reaction nodes; non-finite results (1/x at x = 0) are left out;
  - `t` is not computed in a steady/static solution; `s1`, `e1`, `tr` need Mecway's principal
    fields (not written by the bridge);
  - a formula needs a unit line for each dimension it uses, or Mecway's solve stops without a
    solution; an unknown symbol is skipped silently by Mecway.
- Build: `Scripts/bridge_formula.py` (parser of Mecway's language as in `bridge_bcs`, symbol
  table, unit parser, plan; Python 2.7 and 3), `bridge_from_liml._plan_result_formula`,
  `bridge_to_aster.formulas_arg` + `_check_formula_fields` (WARNING for a missing result field,
  no automatic change of the setting), `aster_results_export._formula_vars` (Code-Aster traps
  floating point exceptions: `libaster.matfpe(-1/1)` around the evaluation, otherwise x/0 stops
  the job with DVP_2).
- Verification: FX-01 (TH-01a, degF, Btu/h/ft2, the formula of issue #8), FX-02 (bar in tension:
  MPa, mm, kN, strain), FX-03 (TH-02a: t in min): 12 checks OK. Mecway's own solve on FX-01: equal
  within 4e-14 relative. GUI: the four formulas of FX-01 on the bridge result are valid (black)
  and show the contour (F3: +-0.02675, Mecway 0.0267528).
- Found on the way: Mecway 34 names acceleration `accx/y/z`, the bridge wrote `accelx/y/z`
  (fixed in S34).
- Open question for the user: should the bridge also write principal stresses/strains, so that
  `s1`..`s3`, `e1`..`e3` and `tr` work in formulas? (Mecway shows them as a field too.)

### S34 – Principal values as result fields; acceleration under Mecway's names
**Goal (user, 28 Oct 2026):** principal stresses/strains so that `s1`, `e1`, `tr` work in
formulas (if Mecway supports them), and check whether the acceleration names (`accelx` vs
Mecway's `accx`) are a problem; if so, fix it.
**Status:** done (28 Oct 2026, branch stap-S34).
**Findings (measured headless with Mecway 34, mw_solve.py and a safe runner; no GUI):**
- Mecway's fields: *principal stress* -> `principal1..3`, *Tresca stress* -> `tresca`,
  *principal strain* -> `lprincipalstrain1..3` (also in a nonlinear L30 with CCX, where they are
  the eigenvalues of the Green-Lagrange tensor), node and element-node variables. Per element
  node: eigenvalues of the tensor, descending; tresca = p1 - p3; strains with gamma/2. Node value
  = mean of the element-node values (within 1e-9), not the eigenvalues of the mean tensor.
- Built: `aster_results_export._principal_vars` (from SIGM_ELNO / EPSI_ELNO / EPSG_ELNO, the
  same rule), groups `principal_stresses` and `principal_strains` (opt-in, solids), the strain
  ELNO field for principal strains without the field `strain`, glossary tooltips, formula
  symbols `s1`..`s3`, `tr`, `e1`..`e3`. Shells (Mecway: `principal1u/m/b`) not built.
- Acceleration: Mecway 34's own D30 solution writes `accx/y/z/accmag`. With the bridge's former
  names Mecway did not recognise the field: after save_as of a bridge result without
  fieldvariables Mecway added no "acceleration" item, `solution.node_value("accx")` gave None;
  with `accx` it added "acceleration" and read the values. Effects of the old names: no vector/
  magnitude item in Mecway, a formula with `a.x` created in Mecway had no data, no comparison
  with Mecway (*Mecway solve first*). Renamed to `accx/y/z/accmag` (harmonic `accmag`,
  `accampx/y/z`, like `velmag`/`velampx`) in the liml route, route 'tabel' and the formula symbol.
  Not found anywhere else (AdvancedToolsHub reads no acceleration names).
- Verification: FX-02 +8 checks (principal values, Tresca, principal strains, formulas `s1`, `tr`,
  `e1`): OK; spectrum (SP) and harmonic (HR) with the new names: OK. Cantilever LS-02: bridge
  principal values follow Mecway's rule within 1e-16 relative.
- Full regression on 8b13519: 2376 of 2382 OK (442 test cases), 6 BEKEND, 0 NOK/FOUT, no
  status change. GUI (Mecway 34, computer use, 28 Oct): a bridge result shows *principal
  stress*, *principal strain* and *maximum shear stress x 2* in the tree, and *acceleration* as a
  vector item next to *velocity*.
- Open: principal values of shells (top/middle/bottom, Mecway `principal1u/m/b`), and `GLe1`.
  (S34b: the Green-Lagrange name above was wrong for Mecway 34, see §S34b.)

### S34b – Principal values of shells; Green-Lagrange principal strains
**Goal:** the open items of S34: principal stresses/strains and Tresca of shells as Mecway
shows them (top/middle/bottom), and `GLe1`..`GLe3` in formulas.
**Status:** done (28 Oct 2026). GUI check not done (no computer use in this session):
open a bridge result of FX-04 in Mecway and look at *principal stress* top/bottom.
**Findings (measured headless with Mecway 34, `mw_solve.py`, safe runner; no GUI):**
- Field names (from the strings in `mecway.exe` and Mecway's own solve of the LS-31 strip with
  an extra in-plane force, quad4 and quad8, internal solver): `principal1u1` ..
  `principal3u1`, `principal1m1` .., `principal1b1` .. (layer 1, like `stressxxu1`),
  `trescau1/m1/b1`, `lprincipalstrain1u1` .. `lprincipalstrain3b1`; node and element-node
  variables. Rule (same as solids): per element node the eigenvalues of the global 3 x 3
  tensor of that surface, descending (the zero normal stress is part of it: one value about
  0); tresca = p1 - p3; strains from `lstrain<ij><s>` with gamma/2 (within 2e-15); node value
  = mean of the element-node values (exact), not the eigenvalues of the node tensor (up to
  16% off).
- CCX: Mecway's shell result with CCX has the solid names (`principal1`, `stressxx`, ...,
  expanded shells); the bridge follows the internal solver.
- Formulas: no formula symbols for the shell surfaces in `mecway.exe` (only `s1`..`s3`, `tr`,
  `e1`..`e3`, `GLe1`..`GLe3`); on a shell-only model Mecway's solve stores no formula with
  `s.xx`, `s1`, `tr`, `e1` (it does with `u.x`, `x`). Nothing to build; the bridge also has no
  node variable for them and leaves such a formula out.
- Green-Lagrange: Mecway 34's L30 with CCX (NL-31 bar and a hex20 cantilever with shear)
  writes `greenlagrangestrain*` and `greenlagrangeprincipalstrain1..3`, also when only
  *principal strain* is requested (it renames the field to *Green-Lagrange principal strain*);
  values = eigenvalues of the Green-Lagrange node tensor with gamma/2 (within 3e-8, CCX node
  values). It rewrites `e1` in a formula to `GLe1` (stored formula text changed; a message in
  `mecway.exe` says the same for `e`, `g`, `e1..e3`). S34's statement that Mecway names them
  `lprincipalstrain1..3` was wrong for this model.
- Built: `aster_results_export._shell_principal_vars` (from `res_sup/moy/inf` SIGM_ELNO and
  `eps_sup/moy/inf` EPSI_ELNO, `_principal_columns`), `bridge_to_aster` requests
  `EPSI_ELNO` + `EXTR_COQUE` of the shells for `principal_strains` also without `strain`,
  principal groups apply to shells; EPSG principal strains renamed to
  `greenlagrangeprincipalstrain1..3`; formula symbols `GLe1..3`; `_gl_alias` in
  `_formula_vars` (e.xx, e1, ... read the Green-Lagrange variables when only those exist).
- Verification: FX-04 (shell strip: top/middle/bottom principal values and principal
  strains against plate theory within 0.22%, Mecway's rule on the bridge's own stresses within
  3e-16), FX-05 (GL principal strain, `GLe1`, `e1`, `e.xx` = 0.05125 exact). Mecway's own
  solve of FX-04: dominant principal values within 0.05% at x = L/2; tresca and the values
  near 0 up to 1% of the maximum apart (Mecway's MITC4 has transverse shear at the
  surfaces, DKT not). Spliced bridge result opened headless in Mecway:
  `solution.node_value("principal1u1")` and `element_node_value` read, Mecway adds the
  fields *principal stress*, *Tresca stress*, *principal strain* on save. FX family,
  LS-31..LS-31d, LS-32, LS-32b, NL-31: all OK.
- Open: whether Mecway, when opening a bridge result of a nonlinear model, also rewrites a
  formula `e1` to `GLe1` (the bridge writes the values under the fieldscalar either way); GUI
  check of the shell fields.

### S35 – HOMARD adaptive refinement inside the job (route a)
**Goal (user, 28 Oct 2026):** adaptive refinement for analyses the Mecway route of S7 cannot handle
(thermal, nonlinear static), with HOMARD inside the Code-Aster job. The loop runs in one job (no OK
click per loop, the Mecway model stays unchanged). Mecway gets the results projected onto its
original mesh; the full refined result goes to ParaView/MWHub Post. Linear static keeps the S7 route
(`refine_x2`); writing a new `.liml` with the refined mesh (route b) is not part of this step.
**Known:** HOMARD 11.10 is in the Code-Aster installation (`tools/ASTER_HOMARD`); `MACR_ADAP_MAIL`
works there in 3D (S7: sslv110f, HEXA8 1680 -> 1698 + 56 TETRA4, conforming, TEST_RESU OK). No
Salome needed (the SalomePlatform `homard` module is only a Salome GUI around the same program;
`mmgplugin` needs Salome too, so not used).
**Source:** U7.03.01 (`MACR_ADAP_MAIL`), U4.72.05 (`PROJ_CHAMP`), U4.81.06 (`CALC_ERREUR`, if that is
the right number: check), validation cases with HOMARD in the Code-Aster test base.
**Research first:**
- Indicator per analysis: thermal `ERTH_ELEM` (does it exist for `THER_LINEAIRE` and
  `THER_NON_LINE` in 17.4?); nonlinear static: `ERME` is only linear, so a field indicator
  (jump/value of `SIEQ`, `EPSP`/`VARI`, or `ERZ1`/`ERZ2`: which are allowed with plasticity?).
  Choose and document the default; options as settings or `#ASTER-OPTIE`.
- `MACR_ADAP_MAIL` with the bridge's meshes: hex20/tet10/wedge/pyramid (quadratic supported?),
  mixed solids with shells/beams (refine only the solid group, `GROUP_MA`), curved boundaries
  (`FRONTIERE_ANALYTIQUE` cylinder/sphere: worth it, or leave as is).
- Groups after refinement: do the bridge's `GROUP_MA`/`GROUP_NO` (loads, constraints, contact) stay
  complete on the new mesh, also node groups (the S7 limitation AD-03)?
- Nonlinear: refine between load steps with `MAJ_CHAM` (fields carried over) or restart the whole
  analysis on the new mesh per loop; which is reliable with plasticity and contact?
- Back to Mecway: `PROJ_CHAMP` of the final result onto the original mesh (nodes and element
  nodes), so `export_results` can keep checking the nodes against the `.liml`; what happens to
  `*_ELNO` fields and to `ERME`/indicator fields; time steps of a nonlinear run.
**Build (after the research):** setting(s) on the pages Thermal and Nonlinear (e.g.
`adapt_homard`, target, max. loops, max. elements; NL/EN tooltips), loop in the `.comm` templates
(Python loop around solve -> indicator -> `MACR_ADAP_MAIL`), `PROJ_CHAMP` back to the original mesh
before the export, refined mesh and result to VTU/MED (`vtu_export`/`med_export`), log per loop
(elements, global indicator). Clear ERROR/WARNING instead of silent fallback (memory:
messages above auto-fix).
**Verify:** thermal case with a known peak (e.g. heat flux around a hole or a re-entrant corner,
analytical or uniformly refined reference) and a nonlinear static case (plasticity at a notch,
against a uniformly refined reference): the result converges with fewer elements than uniform
refinement; projected values in Mecway equal the refined result at the original nodes; existing
TH/NL families unchanged with the setting off. GUI: the projected result in Mecway, the refined
result in MWHub Post.
**Done when:** both cases within tolerance, docs NL/EN (Foutschatter/Error_estimator §6, settings,
KNOWN_BUGS 65 updated), regression 0 NOK/FOUT.
**Status:** split (28 Oct 2026): **S35a** research + prototype done, **S35b** build open.
**Findings S35a** (Code-Aster 17.4 + HOMARD 11.10, real runs; reproduce with
`python TestFiles/Tools/homard_s35/run_s35.py research|prototype|references`; models: the
quarter plate with a hole of `tests_adaptief.py`, hex20, slab with symmetry in z, thermal
T = 0/100 °C on x = 0/x = L, and bilinear plasticity, yield 250 MPa, traction 150 MPa):
- *Indicator, thermal:* `ERTH_ELEM` works after `THER_LINEAIRE` on hex20 (also forma21a), but
  `CALCUL_37` "THER_PYRAM13 ne sait pas encore calculer l'option ERTH_ELEM" on the first refined
  mesh (HOMARD always makes PYRAM13/TETRA10 transitions in a hex mesh), and `DVP_1`
  (rsadpa.F90) after a stationary `THER_NON_LINE` already on pure hex20. Not usable.
- *Indicator, plasticity:* `ERZ1_ELEM` works on the coarse hex20 mesh (as ssnp158a,
  VMIS_ISOT_TRAC), but `DVP_2` (floating point exception in CALC_ESTI_ERRE) on a HOMARD TETRA10;
  `ERZ2_ELEM` `CALCUL_38` (CALC_NOEU_BORD) as soon as the model has face cells; `ERME_ELEM`
  needs SIGM_ELNO on the whole model including face cells (`INDICATEUR_2`) and EXCIT without
  reuse (`CALCULEL_39`), and is the linear residual (forma20c does use it with VMIS_ISOT_LINE).
  **Chosen:** own ZZ-type indicator in the job (`aster_adapt_proto.zz_indicator`): |SIGM_ELNO -
  SIGM_NOEU| (thermal: FLUX), volume-weighted, global relative L2 error; works on every 3D
  cell type and with plasticity. Selection Dörfler in Python; passed to HOMARD as a 0/1
  `CART_NEUT_R` field with `ADAPTATION='RAFFINEMENT'`, `CRIT_RAFF_ABS=0.5` (pattern of
  forma07b). `RAFFINEMENT_UNIFORME` with a `GROUP_MA` filter works once, then HOMARD makes no
  mesh (filter group with its own transition cells). The `CRIT_RAFF_*`/`USAGE_CHAMP` options on
  a native field are then not needed.
- *Meshes:* hex20 → hex20 + PYRAM13 + TETRA10 (conforming), quadratic and linear input, penta
  neighbours become pyramids/tets (`research_mixed.comm`). Pyramids in the input (Mecway
  pyr5/pyr13): default `ELEMENTS_ACCEPTES='HOMARD'` gives no mesh; `'IGNORE_PYRA'` works for
  field-driven refinement (the input pyramids stay as they are), `RAFFINEMENT_UNIFORME` fails
  with pyramids also with `IGNORE_PYRA`. Shells/beams: refining only the solid block also
  splits the attached shell quad (1 → 4) and a beam on a refined edge (2 → 3): conforming, a
  `GROUP_MA` filter does not prevent it (shell/beam results on such meshes NOT verified).
- *Groups:* all `GROUP_MA` (elsets, face groups) are refined along completely (SymZ 24 → 58).
  `GROUP_NO` keep only their old nodes (SymZno 106 → 106, NFACEX0 4 → 4) and HOMARD renumbers
  the nodes (old node i is not node i). So the bridge's node groups (Mecway node selections,
  BRSY/BRCO normal-zone groups as NOEUD lists, centre and LINE_QUAD node groups) are wrong on
  a refined mesh: in the loop everything must hang on cell groups (prototype: symmetry as
  `FACE_IMPO DNOR` on the face groups) or be rebuilt per mesh. A single-node group survives.
- *Boundary following is essential:* without `FRONTIERE_ANALYTIQUE` the hole stays the coarse
  polygon and its kinks act as re-entrant corners: qx at the hole -59.1k → -81.4k W/m² after 9
  loops (reference -67.5k, +21% and rising). With `TYPE='CYLINDRE'` on the face group of the
  hole it converges (-66.9k). Needs a face group on the curved boundary and its analytic shape
  (sphere, cylinder, cone, torus); `MAILLAGE_FRONTIERE` (discrete boundary) not tried.
- *Silent failures:* when HOMARD fails, `MACR_ADAP_MAIL` often raises nothing (the CO result
  does not exist, or LIRE_MAILLAGE "Mesh ... not found"); the job must check the new mesh after
  each call. `INFO=2` crashes the macro (LIRE_MAILLAGE `INFO_MED=2` not allowed). A `.comm` with
  a syntax error gives an empty `.mess` with "DIAGNOSTIC OK".
- *Nonlinear:* `MAJ_CHAM` works for `NOEU_DEPL_R`, but `ELGA_VARI_R`/`ELGA_SIEF_R` give no mesh
  on HOMARD's mixed meshes, so carrying the plastic state over between load steps is not
  reliable. **Chosen:** restart the whole load history on each new mesh (every loop is a full
  `STAT_NON_LINE`; the indicator at the last instant).
- *Back to Mecway:* `PROJ_CHAMP` with `MODELE_1`/`MODELE_2` (with only `MAILLAGE_1/2`: node
  fields; ELNO gives `SUPERVIS_4`), all instants (0 .. 1). Node fields at the original nodes
  equal the refined result (DEPL 4e-17 of 2.7e-4 m, SIGM_NOEU 0.002 Pa of 6e8, VARI 7e-16).
  ELNO fields: at a node shared by two coarse elements both get the value of one refined element
  (214.27 and 214.27 MPa; refined 214.27/236.12, nodal mean 225.2): the element-node jump is
  lost. `export_results` of the projected result against the original `.liml` works unchanged
  (5 steps, all variables, also heat flux via `extra_results`). Indicator fields are cell fields
  of other cells: report them per loop in the log, not to Mecway.
- *Prototype results* (quantity at the hole edge (0, R)): thermal, reference uniform n32
  (12 288 hex20 in the plane) qx = -67 465 W/m²; uniform 3D n4 (768 cells) -2.66%, n8 (6144)
  -0.87%; adaptive with boundary following loop 5 (667) -2.67%, loop 8 (2621) -0.87%: same
  accuracy with **2.3 x fewer cells**. Plasticity, reference n32 sxx = 291.0 MPa, p = 0.001507;
  uniform n4 (768) +22.5%, n8 (6144) +2.4% (p +0.8%); adaptive loop 8 (1932) +2.3% (p +0.8%),
  loop 9 (4364) +0.9% (p +1.5%): **3.2 x fewer cells**. The projected value on the original
  node equals the refined one (-66 878.5; 293.69 MPa). The global ZZ error does not decrease
  monotonically (1.92 → 1.71 → 0.83 → 1.24 → 0.62 %): the S7 rule "stop when the error rises"
  must not be copied; the peak improves late (plasticity loops 4-6 stay at +22% until the
  hole cells themselves are refined).
**Design proposal S35b:** (1) an adaptive variant of the thermal and nonlinear templates in
which the mesh-dependent part is a function `_solve(mesh)` called per loop, with all loads and
constraints on cell groups (face selections are `GROUP_MA` in the `.mail` already; symmetry and
frictionless as `FACE_IMPO DNOR`); in the first version an ERROR for what needs node lists or
node normals (node selections with more than one node, compression only, couplings, contact,
shells/beams, LINE_QUAD), cf. AD-03; (2) a job module `aster_adapt.py` (from
`aster_adapt_proto.py`): indicator, Dörfler, HOMARD call with the existence check,
`IGNORE_PYRA` if the input has pyramids, `FRONTIERE_ANALYTIQUE`, element limit, log per loop
(cells, global error), `PROJ_CHAMP` back and `export_results`, the refined result to MED/VTU;
(3) settings `adapt_homard` (+ target, max. loops, max. elements, Dörfler fraction) on the
pages Thermal and Nonlinear with NL/EN tooltips; (4) verification AD-10 (thermal) and AD-11
(plasticity) = these prototype cases with the references above, TH/NL families unchanged.
**Questions for the user:** (1) boundary following needs the shape of each curved boundary:
an `#ASTER` keyword per face selection (e.g. cylinder: centre, axis, radius) acceptable, or
refine without it and only WARN (the peak then converges to the wrong value)? (2) first
version restricted to solids with loads/constraints on face selections (ERROR otherwise)? (3)
after projection Mecway's element-node values lose the jump between coarse elements (node
values exact): acceptable, or write only node values? (4) stop criterion: the ZZ error is an L2
stress/flux norm, not the energy norm of S7; default target 1%?
**Answers of the user (28 Oct 2026, 21:10):** (1) recognise curved boundaries automatically
(cylinder, sphere; cone if cheap) with INFO/WARNING per surface, `#ASTER` keyword as override;
(2) first version: solids, loads and constraints on face selections, bilingual ERROR for the
rest; (3) node and element-node values after `PROJ_CHAMP`, ELNO limitation documented; (4)
target default 1% as a setting, plus max. loops and max. elements, no stop on a single
rising loop.
**Findings S35b (built, branch s35b on nacht-int2):**
- *Route:* `bridge_homard.wrap` puts the region between the markers `BRIDGE_ADAPT_BEGIN/END`
  of `AsterTemplate_Thermique.comm` / `AsterTemplate_StatNonLine.comm` (model .. CALC_CHAMP)
  indented into a Python loop in `study.comm`; after the loop `PROJ_CHAMP` (MODELE_1/2) of
  `res` (and `res_flux`) onto the original mesh, so `aster_results_export` and the MED/VTU
  blocks run unchanged on the projected result. Per loop: `aster_adapt.Loop.after_solve`
  (ZZ indicator from a separate `CALC_CHAMP` SIGM/FLUX ELNO+NOEU on the solid groups, Dörfler
  0.5, stop rules), `Mesh.setGroupOfCells('BRADAP<k>')`, `CART_NEUT_R` 0/1, `MACR_ADAP_MAIL
  RAFFINEMENT CRIT_RAFF_ABS=0.5`, existence check of the new mesh (HOMARD fails silently),
  `MODI_MAILLAGE ORIE_PEAU` of the skin groups on the new mesh. Nothing changes with the
  setting off (only two comment lines in the templates).
- *Symmetry* on solid faces becomes `FACE_IMPO DNOR = 0` on the face group in this mode
  (`bridge_mesh._apply_to_model_data`), like frictionless; LIAISON_OBLIQUE on node lists would
  miss the new nodes.
- *Curved boundaries:* `bridge_mesh._adapt_boundaries` + `bridge_homard.recognise`: free faces
  of the solids in patches (crease 50°), fit as sphere (only if the normals are not all
  perpendicular to one axis) or cylinder (axis = eigenvector of Σ n nᵀ with the smallest
  eigenvalue, Kasa circle in the plane), tolerance 1e-3 x radius; a recognised patch becomes a
  group `BRRAND<n>` of boundary elements with `FRONTIERE_ANALYTIQUE`. Cones are not
  recognised (WARNING, `#ASTER-RAND` as fallback): not cheap enough for this run. AD-10: the
  hole recognised with deviation 5e-13 x R. Pitfall found by the unit test: two circles of a
  one-layer cylinder also lie on a sphere, so the sphere is not tried when the normals have an
  exact zero eigenvalue.
- *`#ASTER-RAND` / `#ASTER-BOUNDARY`* `selection = CILINDER x, y, z, ax, ay, az, r` | `BOL x, y, z,
  r` | `GEEN` (English CYLINDER/SPHERE/NONE), lengths with unit; its faces leave the automatic
  recognition (AD-10b equal to AD-10 within 1e-4).
- *Scope:* `bridge_homard.check_scope` (before the builder, and on the loop text for
  GROUP_NO with more than one node): ERROR for non-solid elements, couplings, contact,
  bonded contact, constraint equations, point masses, pre-tension, flexible joints, springs,
  compression only, element failure, LINE_QUAD, route 'tabel', 2D (AD-12). Reactions are not
  projected (WARNING); pyramids in the input get `ELEMENTS_ACCEPTES='IGNORE_PYRA'`.
- *Verification:* AD-10 thermal qx −66 878 (−0.87%, tol. 1.5%) with 2621 cells after 8 loops;
  AD-11 plasticity sxx 293.69 MPa (+0.92%, tol. 3%), p +1.25%, 4364 cells after 9 loops, 5 time
  steps; AD-10b, AD-12 OK. Identical to the S35a prototype. Unit test
  `tests/test_bridge_homard.py` (CPython + IronPython 2.7.9); the generation pipeline with
  adapt_homard also run in Mecway's IronPython (AD-10b, AD-11). TH/NL families with the
  setting off (79 cases, 298 checks): all values identical to the baseline (relative
  difference < 1e-9), no status change (only NL-03a known, KNOWN_BUGS 43); the generated
  `.comm` differs only by the two marker comment lines. Refined result to
  `_verfijnd.rmed` checked with `med_export`/`vtu_export` (no MED alarm). Full regression:
  coordinator.
- *Open:* Mecway GUI check (status box lines, results of AD-10/AD-11 in Mecway, the refined
  `_verfijnd.rmed` in ParaView/MWHub Post); cones and free-form boundaries
  (`MAILLAGE_FRONTIERE` not tried); shells/beams/contact in the loop (needs node groups rebuilt
  per mesh); the default target 1% is much too coarse for a peak (AD-10 stops after 2 loops at
  −6%): document only, as the user chose 1%.
