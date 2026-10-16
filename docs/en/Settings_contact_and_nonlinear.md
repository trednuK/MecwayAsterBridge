# Settings for contact and nonlinear analyses

*Nederlandse versie: [Instellingen_contact_en_nietlineair.md](../Instellingen_contact_en_nietlineair.md)*

For readers who know Mecway and are new to Code-Aster. This document describes what
the bridge actually writes into the `.comm` of a run (`<model>_<run-id>.comm`, see
[User guide §5](UserGuide.md#5-files-in-the-working-directory)), and which
other Code-Aster options exist. When in doubt, the code is authoritative. Code-Aster
version: 17.4.

Why each default value was chosen, with the evidence per setting:
[`Default_settings_and_assumptions.md`](Default_settings_and_assumptions.md).
References such as (EDF R&D, U2.04.04 §4.1) are the document number and section of the
Code-Aster documentation; full details are in §5. "Catalogue" is the syntax definition
of the installed Code-Aster 17.4 (`code_aster/Cata`), the source for default values.
Test ids such as NL-01 refer to [Verification.md](Verification.md), R-... to the check
runs in [Default_settings_and_assumptions.md](Default_settings_and_assumptions.md) §5.

---

## 1. Overview

### Which analysis becomes which Code-Aster command

| Mecway analysis | Bridge analysis (`active_analysis`) | Code-Aster | Time integration |
|---|---|---|---|
| S30, linear static | `lin_static_3d` | `MECA_STATIQUE` | none |
| L30, nonlinear static | `nonlin_static_3d` | `STAT_NON_LINE` | pseudo-time, Newton per step |
| D31, dynamic, implicit | `dyna_impl_3d` | `DYNA_NON_LINE` | HHT (or NEWMARK), Newton per step |
| D31, dynamic, explicit | `dyna_expl_3d` | `DYNA_NON_LINE` | DIFF_CENT (or TCHAMWA), no iterations |
| D30, linear dynamic (without *Mode superposition*) | `dyna_impl_3d` | `DYNA_NON_LINE` | NEWMARK with `deformation` `PETIT` = Mecway's scheme (otherwise WARNING) |
| D30 with *Mode superposition* | `dyna_modal_3d` | `CALC_MODES` + `DYNA_VIBRA` `GENE` | NEWMARK per mode ([Mode_superposition.md](Mode_superposition.md)) |

With "Active analysis (auto = follow Mecway)" = `auto` (default) the bridge follows the analysis type in the
`.liml` (`bridge_utils.resolve_auto_analysis`): S30, L30, D30 and D31 as in the table
(D31 always becomes `dyna_impl_3d`), T30/T31 `ther_3d` ([Thermal.md](Thermal.md)), V30
`modal_3d` (with a fluid part `vibroacoustic_modes_3d`), B30 `buckling_3d`
([Modal_and_buckling.md](Modal_and_buckling.md)) and A30 `acoustic_modes_3d` (with a
source `acoustic_harm_3d`; [Acoustics.md](Acoustics.md)). Any other type stops the
bridge with a message. Explicit dynamics you select yourself on
the start screen.

What the nonlinear analyses support:

- material: `ELAS`; with plasticity `VMIS_ISOT_TRAC` (hardening curve,
  Ramberg-Osgood, OpenRadioss `PLAS_TAB`), `VMIS_ISOT_LINE` or `VMIS_CINE_LINE`
  (bilinear); tension only `CABLE`, gap `DIS_CHOC`; beams with large rotations
  `ELAS_POUTRE_GR` (`elem_beam` = `POU_D_T_GD`, §2.9);
- contact: Mecway `contact2` becomes `DEFI_CONTACT` (§3); compression only
  `DEFI_CONTACT FORMULATION='LIAISON_UNIL'`;
- dynamics: initial velocity (Mecway `initialconditions/velocity`) becomes
  `ETAT_INIT=_F(VITE=...)`;
- time-dependent loads via `DEFI_FONCTION`.

### Where to find the settings

- **Start screen**, one page per analysis. A field only appears if the key exists in
  that analysis (`CONFIG_BRIDGE["analyses"]` in `Scripts/bridge_utils.py`,
  `ANALYSIS_SPECS` in `bridge_gui.py`):

| Group (heading on the page) | Keys | Analyses |
|---|---|---|
| Code-Aster run | `time_limit`, `memory_limit` | all |
| Solver | `solver_nprec`; `lin_solver`, `lin_solver_resi` | all; `lin_solver` static only, `lin_solver_resi` static and the static step of modal, buckling and the imperfection |
| Steps and convergence | `substeps_per_interval` (static), `newton_max_iter`, `newton_reac_iter`, `default_time_end`, `convergence_criterion`, `convergence_resi_rela`, `convergence_resi_maxi` | nonlinear static, dynamic implicit; `default_time_end` also explicit |
| Contact | `contact_algo` | nonlinear static, dynamic |
| Material and kinematics | `plastic_strain_definition`, `deformation` | nonlinear static, dynamic |
| Time scheme | `schema`, `hht_alpha`, `substeps_per_output` (implicit), `explicit_dt_factor` (explicit) | dynamic |
| Failure | `element_failure`, `failure_plastic_strain`, `failure_stiffness_factor` | nonlinear static, dynamic ([Failure.md](Failure.md)) |
| Checks | `energy_balance`; `error_estimator` | dynamic implicit; static |
| Nonlinear buckling | `crit_stab`, `imperfection_amplitude`, `imperfection_mode`, `imperfection_unit` | nonlinear static ([Modal_and_buckling.md](Modal_and_buckling.md) §5) |

- **Per model**: `#ASTER-OPTIE key = value` (§3.9).

---

## 2. Settings

Legend: **Bridge** = default value in `bridge_utils.py`; **CA** = Code-Aster default
when you omit the keyword (catalogue 17.4).

### 2.1 Time steps

| Key (label) | Analysis | What it does | Bridge | CA |
|---|---|---|---|---|
| `substeps_per_interval` (Substeps per time interval) | static | Only for a model without Mecway's *Time step size*: solver steps per interval between the time points of the time-dependent loads (`DEFI_LIST_REEL`, `NOMBRE`); without a time load 0 to `default_time_end`. With a step size the bridge computes Mecway's steps plus the kinks of the load tables (§2.1). | 10 | - |
| `substeps_per_output` (Solver steps per output interval) | implicit | Solver steps per output interval of Mecway `<timesteps>`. Kinks of load functions are added as extra time points. | 1 | - |
| `default_time_end` (End time without time load) [s] | all | End time when the model has no time load (static) or no `<timesteps>` (dynamic). | 1.0 | - |
| `explicit_dt_factor` (Time step / critical time step) | explicit | Time step ≤ factor × the critical time step as estimated by the bridge, divided evenly per output interval (so every output time is a solver step). | 0.5 | - |

**Static (`STAT_NON_LINE`).** As for implicit dynamics the bridge creates a
`DEFI_LIST_INST` with automatic cutting (see below); with only a `DEFI_LIST_REEL`,
Code-Aster would not reduce the step (EDF R&D, U4.51.03; message `SUBDIVISE_3`). Sent to
Mecway (route `liml`): all archived solver steps up to the last time reached (the
bridge sets no `ARCHIVAGE`), or (route `tabel`) only that last time. The solver steps
are Mecway's (*Time step size*, `<timesteps stepsize>`: dt, 2 dt, ... up to the period),
plus the kinks of the load tables that fall in between; so Mecway shows the same times
as with Mecway's own solver. Load times after the period are dropped. Mecway's
*automatic time stepping* is not reproduced (fixed step; Code-Aster only cuts on
divergence). Only a model without a step size uses `substeps_per_interval`.

**Implicit dynamic.** The bridge creates a `DEFI_LIST_INST` with:

```
ECHEC=_F(EVENEMENT='ERREUR', ACTION='DECOUPE',
         SUBD_METHODE='MANUEL', SUBD_PAS=4, SUBD_NIVEAU=6)
```

- `EVENEMENT='ERREUR'` covers, among others, too many Newton iterations, failed
  integration of the constitutive law and a singular matrix (EDF R&D, U4.34.03, "Event
  ERREUR").
- `DECOUPE` with `SUBD_PAS=4`: the failed step is split into **4** equal steps
  (not halved). `SUBD_NIVEAU=6`: this can be nested 6 times, so down to 1/4096 of the
  original step.
- CA default according to the catalogue: `SUBD_PAS=4`, `SUBD_NIVEAU=3`. U4.34.03 gives
  `SUBD_NIVEAU=4` for the automatically added `ERREUR`; the catalogue says 3. Which of
  the two Code-Aster uses is NOT verified (the bridge sets it explicitly to 6 anyway).
- Results are archived only at the output times (`ARCHIVAGE`), and all output times
  are sent to Mecway.

**How many substeps.** Smaller steps usually make a nonlinear problem easier (EDF R&D,
U2.04.01), but not always: NL-02a (large deflection, elastic) gave the same result
with 1 substep per interval as with 10 (R-SUB1), and NL-01 (plastic solids) stopped
with 40 substeps and `RESI_GLOB_RELA` 1e-6 already at t = 0.013, because the residual
force of `GDEF_LOG` stays above 1e-6 of the reaction at a small load (R-SUB40; §2.2;
with the default 1e-5 it runs through).

**Explicit (`DIFF_CENT`).**

- Stability: the time step must stay below the Courant limit (CFL). For `DIFF_CENT`
  the critical step is 2/ω_max (EDF R&D, U2.06.13).
- The bridge estimates the critical step as smallest edge / dilatational wave speed
  `c = sqrt(E(1-ν)/(ρ(1+ν)(1-2ν)))` over all elements with a density. That is an
  estimate, not Code-Aster's value.
- Code-Aster computes the CFL limit itself and stops with `DYNAMIQUE_2` if a step is
  too large (`STOP_CFL='OUI'`, default; EDF R&D, U4.53.01). The bridge leaves that on.
- **Factor and CFL limit.** The factor applies to the bridge's estimate. In DY-03a
  (hex8 cubes of 10 mm, ν = 0) Code-Aster's limit was half of that estimate
  (9.667e-7 s vs 1.933e-6 s): the default 0.5 lands on the limit itself (0.86 × the
  limit after the even division per output interval), and with 0.7 or more Code-Aster
  refuses the run (R-DT). U2.06.13 recommends 0.5 to 0.7 × the CFL limit; here that is
  a factor of 0.25 to 0.35 (0.3 gave the same result within tolerance in DY-03a). For
  other element shapes the ratio is NOT measured.
- The CFL limit is computed only at the start (U2.06.13). Elements that shrink
  strongly, or penalty contact, can lower the limit: then lower the factor.
- The bridge sets `MASS_DIAG='OUI'` (lumped mass, recommended in U4.53.01).
- In explicit analysis the step is never reduced automatically (U2.06.13).
- **No mass scaling.** An option like `/DT/NODA/CST` in OpenRadioss (adding mass to
  enlarge the step) is not in U4.53.01 and U2.06.13 (NOT found). `COEF_MASS_SHIFT` is
  something else (M + coef·K, to make a singular mass matrix invertible). The step
  therefore follows from the smallest element. Above 2,000,000 steps the bridge writes
  a WARNING; then consider `dyna_impl_3d`.
- **Damping and discrete elements.** Rayleigh damping reduces the stable step:
  dt = (2/ω)(√(1+ξ²) − ξ) with ξ = α/(2ω) + βω/2 (Belytschko et al., 2000; factor
  < 0.1: WARNING, consider `dyna_impl_3d`). Loose springs, dampers and nodal masses
  count (ω² = Σk(1/m_i + 1/m_j) per node); without elements with a material Code-Aster
  cannot determine the CFL limit itself (`DYNAMIQUE_4`), and the bridge sets
  `STOP_CFL='NON'`.
- **Imposed displacement.** `DIFF_CENT`/`TCHAMWA` only support
  `FORMULATION='ACCELERATION'`: `DDL_IMPO` imposes an acceleration there. The bridge
  converts an imposed displacement, rotation or velocity ≠ 0 into the acceleration the
  scheme imposes; at every solver step u(t) is correct (DY-03b). Kinks in u(t) become
  solver times; a value without a time history is reached in the first step (impulse,
  WARNING). A displacement of 0 simply stays fixed.
- **Shells.** Explicit with DKT gave the same vibration as implicit (R-STRIP: period
  +0.6 % relative to Euler-Bernoulli); the bridge does not set `INER_ROTA`.

### 2.2 Newton and convergence

| Key (label) | Code-Aster | Bridge | CA | When to change |
|---|---|---|---|---|
| `newton_max_iter` (Max. Newton iterations) | `CONVERGENCE/ITER_GLOB_MAXI` | 20 | 10 | Increase with contact (`CONTINUE`): U4.51.03 says contact often needs more iterations. Very many iterations usually indicate a model error or too large a step (U4.51.03). With 1 substep NL-02a needed 11 iterations (R-SUB1). |
| `newton_reac_iter` (NEWTON REAC_ITER) | `NEWTON/REAC_ITER` | 1 | 1 | Keep 1: tangent matrix renewed every iteration (robust, recommended in EDF R&D, U2.04.01 and U2.04.04 §4.5.2). With 0, NL-02a stopped in the first step with `DVP_2` (R-REAC0); the start screen therefore accepts at least 1. |
| `convergence_criterion` (Convergence criterion) | `RESI_GLOB_RELA`, `RESI_GLOB_MAXI`, or both with `VERIF='AU_MOINS_UN'` | `RELA` | `RELA` | See below. |
| `convergence_resi_rela` (Convergence RESI_GLOB_RELA) | `CONVERGENCE/RESI_GLOB_RELA` | 1e-5 (thermal 1e-6) | 1e-6 | Relative to the imposed load plus reactions (U4.51.03). The bridge deviates from the CA default 1e-6 because the residual stalls on it with plastic solids (`GDEF_LOG`) (see below). 1e-6 is possible, if needed with `RELA_OF_MAXI`. Do not loosen it further: that hides problems. |
| `convergence_resi_maxi` (Convergence RESI_GLOB_MAXI) [N] | `CONVERGENCE/RESI_GLOB_MAXI` | 1e-3 | - | Only with `MAXI` and `RELA_OF_MAXI`. `MAXI`: choose it small compared with the expected forces. `RELA_OF_MAXI`: above the absolute residual at which the residual stalls (column `RESI_GLOB_MAXI` in the `.mess`). |

**`RELA` or `MAXI`.** `RELA` = `RESI_GLOB_RELA`: largest residual force divided by the
imposed load plus reactions. `MAXI` = `RESI_GLOB_MAXI`: largest residual force in N
(`convergence_resi_maxi`). If the reference of `RELA` becomes zero (e.g. complete
unloading), Code-Aster switches to an absolute criterion itself, but not in the first
step (U4.51.03, "Convergence settings"). So choose `MAXI` when the load and the
reactions are ~0 from the start (an imposed motion without resistance or contact
force): a rigid translation stopped with `RELA` in step 1 and was exact with `MAXI`
1e-3 N (R-RIGID). Samples/PipeClip stalled with `RELA` in step 1 (RESI_GLOB_RELA 1..13
at ~1e-12 N) and runs through with `MAXI` 1e-3 N.

**`RELA_OF_MAXI`.** The bridge then sets both criteria with `VERIF='AU_MOINS_UN'`:
converged when the relative **or** the absolute criterion is met (catalogue
`c_convergence.py` 17.4; U4.51.03). Without `VERIF` Code-Aster requires both
(`VERIF='TOUT'`). CCX works the same way: a relative criterion with an absolute floor
for small forces. U4.51.03 warns that `'AU_MOINS_UN'` may accept an inaccurate result;
so do not choose `convergence_resi_maxi` larger than needed: just above the absolute
residual at which the residual stalls (column `RESI_GLOB_MAXI` in the `.mess` or the
convergence screen, §4.4). Measured on NL-01 with `RESI_GLOB_RELA` 1e-6: with
`RESI_GLOB_MAXI` 0.05 N exact up to t = 3 (verification case NL-01b); with 1e-3 N
not, because the absolute residual stalls at ~1e-2 N (R-ROM).

**Stagnation with `GDEF_LOG`; why the default is 1e-5.** With plastic solids
(`GDEF_LOG`, §2.3) the residual force gets stuck: around 5e-4 N at a small load and
~1e-2 N when unloading (tensile bar of NL-01, 12 kN; `RESI_GLOB_RELA` ~1.5…2.3e-6).
With the CA default 1e-6 that is more than the criterion; the step is cut, the load
becomes even smaller, and the run stops with `MECANONLINE9_7`. Seen when unloading
(NL-01 stopped at t = 2.92), with 40 substeps (stop at t = 0.013) and with a hardening
curve (stop at t = 0.013). With 1e-5 (NL-01, R-SUB40-1E5, R-CURVE), `MAXI` 1e-2 N
(R-MAXI) or `RELA_OF_MAXI` (NL-01b) they run through and are exact. The bridge default
is therefore 1e-5 (`nonlin_static_3d`, `dyna_impl_3d`). Over all NL and DY
verification cases, 1e-6 → 1e-5 changed the results by at most 3.75e-6 relative
(R-1E5); CCX and Abaqus use 5e-3.

Not settable in the bridge: `NEWTON/PREDICTION`. Normally the bridge omits it; the
catalogue gives no default, and which prediction Code-Aster then uses is not stated
unambiguously in U4.51.03 (NOT verified). U2.04.01 and U2.04.04 §4.5.2 recommend
`PREDICTION='ELASTIQUE'` for convergence problems. Exception: with
[element failure](Failure.md) the bridge does set it: `'TANGENTE'`, and in the step
directly after a failure event `'ELASTIQUE'` (static and implicit dynamic). In
explicit analysis it always stays `'TANGENTE'` (Code-Aster allows nothing else with an
explicit scheme).

### 2.3 Kinematics: `deformation`

`COMPORTEMENT/DEFORMATION` (EDF R&D, U4.51.11, "Operand DEFORMATION"). Code-Aster:
`PETIT`; for the nonlinear analyses the bridge uses `GROT_GDEP` by default, because
Mecway's nonlinear analysis (CCX) is geometrically nonlinear (a plastic bar: 14 % too
stiff with `PETIT`, +1 % relative to Mecway with large displacements; earlier run,
model not in the repository). The value on the start screen is a choice for the whole
model; if you choose a large-displacement form (`GROT_GDEP`, `GREEN_LAGRANGE`,
`GDEF_LOG`, `SIMO_MIEHE`), the bridge sets per elset the form that Code-Aster 17.4
accepts for that element and constitutive law (`bridge_to_aster._deformation_for`,
checked with runs on a mixed model). One WARNING per run names the beam and DKT/DST
elsets that stay geometrically linear; the details per elset are INFO lines in the log.

| Elset | Large displacements chosen | Why |
|---|---|---|
| solid, elastic | `GREEN_LAGRANGE`, or `GDEF_LOG` if that was chosen | `GROT_GDEP` not allowed on 3D (`COMPOR5_22`) |
| solid, plastic | `GDEF_LOG`, or `SIMO_MIEHE` if that was chosen (with `VMIS_CINE_LINE` always `GDEF_LOG`) | `GREEN_LAGRANGE` with `VMIS_*` refused, `SIMO_MIEHE` with `VMIS_CINE_LINE` too (`COMPOR1_44`) |
| DKT/DST | `GREEN_LAGRANGE` (with `VMIS_CINE_LINE` `PETIT`) | `GROT_GDEP` did not converge, `GDEF_LOG` refused (`COMPOR1_99`); `GREEN_LAGRANGE` gave the same result as `PETIT`, so effectively geometrically linear. Large rotations of shells: `elem_shell` = `COQUE_3D` |
| `COQUE_3D` | `GROT_GDEP` | alarm `COMPOR1_47`: rotations < 2π; NL-02b exact |
| beam `POU_D_E`/`POU_D_T` | `PETIT` | `GROT_GDEP` on `POU_D_E` did not converge (KNOWN_BUGS 11); for large rotations `elem_beam` = `POU_D_T_GD` |
| beam `POU_D_T_GD` | `GROT_GDEP` with `ELAS_POUTRE_GR` | large rotations of beams (§2.9) |
| cable (tension only) | always `GROT_GDEP` | `RELATION='CABLE'` requires it |
| discrete (spring, nodal mass, elastic support) | `PETIT` (`PETIT_REAC` if chosen) | large displacements for discrete elements NOT verified |

`PETIT` and `PETIT_REAC` go unchanged to all elsets (except cables).

**Follower loads.** With a large-displacement form, uniform pressure is a follower
load (`TYPE_CHARGE='SUIV'`), as in Mecway (Mecway, 2026, §9.14), on solids and
`COQUE_3D`; on DKT/DST Code-Aster cannot do this (`CALCUL_42`), and the pressure stays
fixed there (WARNING). Hydrostatic pressure stays fixed. Centrifugal force uses the
deformed radius in `STAT_NON_LINE` (spin softening, as Mecway §9.20) when only solids
rotate. Plasticity on beams is computed elastically (WARNING).

| Value | What | When |
|---|---|---|
| `PETIT` | Small displacements, rotations and strains (below approx. 5 %). | Linear static; nonlinear only for truly small deformations or for comparison with linear theory (DY-03). |
| `PETIT_REAC` | Equilibrium on the updated geometry, law in small strains. Only good for small steps, small rotations, predominantly plastic strain, isotropic behaviour. Not recommended for shells and beams. | Rarely; prefer `GDEF_LOG`. |
| `GROT_GDEP` | Large displacements and rotations, **small strains**. Code-Aster: `COQUE_3D` (all laws), `DKT` (linear elastic only), multifibre beams. | Buckling, slender shells, large displacements in general (the bridge chooses per elset, see above). |
| `SIMO_MIEHE` | Large plastic strains (e.g. `VMIS_ISOT_TRAC`). 3D/2D solid elements only. Non-symmetric tangent matrix. | Large plastic deformation. |
| `GDEF_LOG` | Large strains with a logarithmic strain measure (e.g. `VMIS_ISOT_*`). 3D/2D only. The elastic strain must stay small. | Large plastic deformation (forming, cutting). First choice next to `SIMO_MIEHE`; note the stagnation in §2.2. |
| `GREEN_LAGRANGE` | Green-Lagrange strain. | Elastic solids with large displacements (NL-02a). |

Imposed rotations (`DDL_IMPO` DRX/DRY/DRZ) and rigid couplings (`LIAISON_SOLIDE`) stay
small rotations even with large displacements (on the nodes of `POU_D_T_GD` beams an
imposed rotation is the total rotation vector, §2.9); an imposed rotation above ~6° gives a
WARNING (`_warn_large_rotations`). A rigid part is rotated robustly via `#ASTER`
(`ASTER_lines_examples.md` example 9).

### 2.4 Plasticity: `plastic_strain_definition`

Code-Aster `TRACTION/SIGM` expects the stress as a function of the **total** strain.
The first point is the yield point; a point with zero strain is not allowed (EDF R&D,
U4.43.01 §5.1.1). The bridge converts Mecway's hardening curve (setting "Strain
definition hardening curve"):

| Value | Meaning of the Mecway strain | Conversion |
|---|---|---|
| `plastic` | plastic strain | strain_total = strain_plastic + σ/E |
| `total` | total strain | start point (0, 0) is dropped |
| `auto` (default) | derived from the first point | (0, 0) or first strain > 0: total (as Mecway); (0, σ>0): plastic, with a WARNING |

Mecway's hardening curve uses the **total** strain (measured with Mecway/CCX headless
on the bar of NL-01, R-CURVE): the curve (0, 0), (σy/E, σy), (0.1, …) gave the expected
stress and plastic strain; a curve starting with (0, σy) gave a non-physical result in
Mecway. `auto` therefore reads a curve with start point (0, 0), or a curve that starts
directly at the yield point (σy/E, σy), as total strain. If the first point with
strain > 0 is not on the elastic line (slope E), a WARNING about the slope follows. If
the curve starts with (0, σ > 0), `auto` reads it as plastic strain, with a WARNING that
Mecway reads the same curve as total strain (the Mecway solution may then differ);
choose `plastic` or `total` to avoid the message. Measured on NL-01 with `auto`: curve
with and without (0, 0) exact up to t = 3 (σ at t = 2: 433.49 MPa, analytical), curve
(0, 355 MPa) as plastic strain also exact (R-CURVE). When in doubt, check the yield
stress in the `.comm` (first point of the function). Bilinear plasticity:
Mecway's *tangent modulus* is the plastic modulus H; the bridge sets
`D_SIGM_EPSI` = E·H/(E+H) (NL-01).

### 2.5 Time scheme (dynamics): `schema`, `hht_alpha`

`DYNA_NON_LINE/SCHEMA_TEMPS` (EDF R&D, U4.53.01, U2.06.13).

| `schema` | Type | What the bridge sets | Remark |
|---|---|---|---|
| `HHT` (default `dyna_impl_3d`) | implicit | `ALPHA=hht_alpha`, `FORMULATION='DEPLACEMENT'` | Full HHT scheme (CA default `MODI_EQUI='OUI'`; Hilber et al., 1977). DY-01a, DY-02, DY-03c. |
| `NEWMARK` | implicit | `FORMULATION='DEPLACEMENT'`, no BETA/GAMMA | CA: β = 0.25, γ = 0.5 (trapezoidal rule). No numerical damping; can be unstable in nonlinear problems (U4.53.01). DY-01b/c/d (period error of order 2, Hughes, 2000). |
| `DIFF_CENT` (default `dyna_expl_3d`) | explicit | `MASS_DIAG='OUI'`, `FORMULATION='ACCELERATION'` | No numerical damping. DY-03a/b. |
| `TCHAMWA` | explicit | same | Damps high frequencies (CA: `PHI=1.05`). DY-03a with TCHAMWA within tolerance (R-TCHAMWA). |

`hht_alpha` (HHT ALPHA): bridge -0.1, CA -0.1. The more negative, the more numerical
damping. U2.06.13: start at -0.1; -0.3 is an upper limit that is still usable; carry
out a parameter study and choose the value closest to zero that still gives a good
solution. With -0.3, DY-01 followed the scheme exactly (period +1.21 %, peak −0.87 %,
R-ALPHA). With HHT a step load gets a slightly too small impulse in the first step
(Code-Aster uses F₀ = 0; DY-01a: peak −0.44 %).

**`MODI_EQUI`.** The bridge keeps the CA default `'OUI'`: the full HHT scheme, second
order, which mainly damps high frequencies and which U2.06.13 recommends (`'NON'` =
modified average acceleration, first order).

### 2.6 Linear solver: `solver_nprec`, `lin_solver`, `lin_solver_resi`

`SOLVEUR=_F(METHODE='MUMPS', NPREC=...)`. NPREC is the number of digits that may be
lost in the factorisation before Code-Aster calls the matrix singular.

| | `lin_static_3d` | nonlinear, modal, buckling, thermal | CA |
|---|---|---|---|
| `solver_nprec` (MUMPS NPREC) | 8 | 8 | 8 |

In nonlinear analysis a singular matrix counts as `ERREUR` and leads (implicit
dynamic) to step reduction (U4.34.03). A part that can move freely gives in
`MECA_STATIQUE` `FACTOR_57` with -1 (error bound too large) and `FACTOR_11` with 8
(R-FREE); both stop the run. In `STAT_NON_LINE`/`DYNA_NON_LINE` MUMPS does not check
the error bound by default (`RESI_RELA` = -1 for nonlinear commands, catalogue
`c_solveur.py`); NPREC is the only singularity check there. NL-03a (line contact,
`STANDARD`) ran through with -1, but 1.6 % off in the contact force (R-NPREC-CONTACT):
use `PENALISATION` there (§3.1).

**Static analysis (`lin_static_3d`): `lin_solver` and `lin_solver_resi`.**
`MECA_STATIQUE` solves one system Ku = F. The bridge always adds `INFO=2`, so that the
solver statistics end up in the `.mess` (convergence window, §4.4). That is about
15 kB of text, also with 270,000 equations (measured).

| Setting (label) | Values | Code-Aster |
|---|---|---|
| `lin_solver` (Linear solver) | `MUMPS` (default): direct solver, factorises the matrix | `SOLVEUR=_F(METHODE='MUMPS', NPREC=..., RESI_RELA=...)` |
| | `GCPC`: iterative, conjugate gradient with incomplete factorisation | `SOLVEUR=_F(METHODE='GCPC', PRE_COND='LDLT_INC', RESI_RELA=...)` |
| `lin_solver_resi` (Solver accuracy) | `RESI_RELA`, default 1e-6 (= CA default for `MECA_STATIQUE`) | |

- **MUMPS**: `RESI_RELA` is the bound on the *estimated relative error in the
  displacements*. MUMPS estimates it as condition number × 'backward error'; if it is
  larger than `RESI_RELA`, Code-Aster stops with `FACTOR_57` (EDF R&D, U4.50.01
  §3.5.3; U2.08.03 §7.2.1). With `solver_nprec` = -1 this is the only check for a
  singular matrix (U2.08.03 table 7.1-1, case 5). Choose MUMPS unless you have a
  reason: it is robust and usually the fastest. A slender volume model in bending can
  exceed 1e-6 without a mechanism (hex20 cantilever 1000 × 40 × 10 mm: 7.0e-6; a
  mechanism gives `FACTOR_11`, or with -1 an error of order 10); the bridge's message
  then gives the value for `lin_solver_resi`
  ([Error messages](CodeAster_error_messages.md), `FACTOR_57`).
- **Other analyses**: `lin_solver_resi` is also on the pages *Modal* (the
  `MECA_STATIQUE` for the prestress), *Buckling* (the static step) and *Nonlinear
  static* (the `MECA_STATIQUE` of the imperfection). There the solver is always MUMPS
  (`NPREC` = `solver_nprec`). `STAT_NON_LINE` and `CALC_MODES` do not check the error
  bound (`RESI_RELA` -1, catalogue `c_solveur.py`).
- **GCPC**: `RESI_RELA` is the convergence criterion ‖r‖/‖f‖ (residual force divided by
  the load). Maximum number of iterations: the number of equations / 2
  (`NMAX_ITER=0`; after that Code-Aster stops with `ALGELINE4_3`). GCPC uses less
  memory, but only converges well for a well-conditioned model (U2.08.03 §3: condition
  number < 1e4); for slender structures (beams made of solid elements) hundreds of
  iterations are normal: the beam of LS-02 (hex8) took 232 iterations with 20,169
  equations and 499 with 141,321, with the same result as MUMPS within tolerance
  (R-GCPC). If the convergence window shows a long flat line, use MUMPS.
- **PETSC** is in the catalogue, but the Windows version of Code-Aster is sequential
  and has no PETSc (`FERMETUR_10`, seen in a test run; U4.50.01 §3.7). The bridge
  therefore does not offer it.

### 2.7 Other

`time_limit` (Time limit run_aster) [s] and `memory_limit` (Memory limit run_aster)
[MB] go into the `.export` (limits of `run_aster`). A run aborted by the time limit
gives no complete results.

`energy_balance` (Energy balance; implicit dynamics only, default off): see §4.4.

`error_estimator` (Error estimator; static only, default on): estimated
discretisation error per element with `CALC_ERREUR` `ERME`, see
[Error_estimator.md](Error_estimator.md).

`crit_stab` (Stability per step, default off) and `imperfection_*` (buckling mode as
imperfection, default amplitude 0 = none; nonlinear static only): `CRIT_STAB` in
`STAT_NON_LINE` and a linear buckling mode as pre-deformation of the mesh, see
[Modal_and_buckling.md](Modal_and_buckling.md) §5. With the default `deformation`
(large displacements) `CRIT_STAB` is not a load factor but an eigenvalue that goes to 0.

### 2.8 Modal, buckling and thermal

The settings of modal and buckling (`modal_modes`, `modal_shift_hz`, `modal_norm`,
`modal_tolerance`) are in [Modal_and_buckling.md](Modal_and_buckling.md) §1.2, those
of thermal (`theta` and the Newton settings of `THER_NON_LINE`) in
[Thermal.md](Thermal.md) §2. Justification and check runs:
[Default_settings_and_assumptions.md](Default_settings_and_assumptions.md) §3.6 to
§3.8. Buckling always looks for the smallest buckling factors
(`OPTION='PLUS_PETITE'`), as Mecway does; a search centre (`OPTION='CENTRE'`) ignores
`CHAR_CRIT` in Code-Aster 17.4 (R-BSHIFT) and is therefore not a setting.

### 2.9 Beams with large rotations: `elem_beam` = `POU_D_T_GD`

By default beams are geometrically linear in the nonlinear analyses (`POU_D_E`/
`POU_D_T` with `PETIT`, §2.3; KNOWN_BUGS 11). For large displacements and rotations of
beams choose `elem_beam` = `POU_D_T_GD` on the **Elements** page. The bridge then writes:

```python
model = AFFE_MODELE(..., AFFE=_F(GROUP_MA=..., MODELISATION='POU_D_T_GD'))
res = STAT_NON_LINE(...,
    COMPORTEMENT=_F(GROUP_MA=..., RELATION='ELAS_POUTRE_GR', DEFORMATION='GROT_GDEP'))
```

An elastic Timoshenko beam (with shear deformation; `AY`/`AZ` as for `POU_D_T`) with
large displacements and rotations and small strains (EDF R&D, U4.51.11; Code-Aster test
case ssnl103a). The idea, the Code-Aster route, the first list of limitations and the
benchmarks NL-80 to NL-82 come from the fork by MishalTPC
(`github.com/mishal0488/MecwayAsterBridge`, MPL-2.0); the bridge rebuilt them for
element offset, flexible joint, line3, beam orientation and `beam_forces`.

| Combination | What the bridge does |
|---|---|
| nonlinear static with large displacements (`deformation` default `GROT_GDEP`) | `POU_D_T_GD`: force and moment (constant, NL-80c, or as a table in time), line pressure (constant or as a formula in x, y, z, t), gravity, Thermal stress, Mecway's *Time step size*, configurations (NL-80 to NL-89) |
| line3 beam | two SEG2 cells per element, as for `POU_D_E` (NL-84) |
| beam orientation (attributes and *Element orientation*) | explicit `VECT_Y` per cell (NL-85) |
| centrifugal force | `ROTATION` is not possible on this element (`CHAR_MECA_ROTA_R`, `CALCUL_37`); the bridge writes `FORCE_POUTRE` as a formula of the initial position: a fixed load, without spin softening (NL-86); trusses (`BARRE`) in such a model get `FORCE_POUTRE` as well (NL-86b) |
| plastic material | computed elastically (WARNING), as for the other beams |
| element failure ([`Failure.md`](Failure.md)) | ERROR: after the first failed element the next step needs `RIGI_MECA` (`CALCUL_37`); switch failure off or choose `POU_D_E`/`POU_D_T` |
| other analyses (static, modal, buckling, harmonic, spectrum, dynamics) and nonlinear with `PETIT`/`PETIT_REAC` | `POU_D_T` with a WARNING: the same beam at small displacements (NL-80b). The element has no `RIGI_MECA` (`CALCUL_37` in `MECA_STATIQUE`); dynamics (test case sdnl103a) is NOT verified in the bridge |
| `crit_stab` | ERROR: the tangent matrix is not symmetric (`ALGELINE4_41`) |
| `imperfection_amplitude` > 0 | ERROR: the linear buckling beforehand needs `RIGI_MECA`; put the initial curvature in the mesh (NL-82) |
| element offset, flexible joint, couplings | they compute (offset and joint equal to `POU_D_T` for small loads; couplings NOT verified), but stay linear relations in the undeformed axes: WARNING (KNOWN_BUGS 11, 106, 108) |
| imposed rotation (`noderotation`) | the total rotation vector (exact for a rotation about one fixed axis), but slender beams converge poorly: WARNING (KNOWN_BUGS 11) |

**Results.** Displacements, rotations and reactions as always. Section forces
(`beam_forces`: `tensileforce`, `sheary`, `shearz`, `torsion`, `bendingmomv`,
`bendingmomw`) come from `SIEF_ELNO`/`SIEF_NOEU` (`EFGE_ELNO` stops with `DVP_1` on this
element), in the co-rotating axes of the cross-section, with the same names and signs as
for `POU_D_E`. It is one value per element (one integration point, at the middle); the
nodal value is the mean of the adjacent elements, so at the clamped end half an element
away from the maximum. There are no beam stresses (`beamsixxmin`/`beamsixxmax`): the
element has no `SIPM_ELNO` (`CALCUL_37`). One WARNING per run says so.

**Hints.**

- `POU_D_T_GD` is a linear element: use 20 to 40 elements per member (with 40
  elements ≤ 0.03 % from the analytical solution, NL-81 and NL-83).
- Let the load increase (a table in time, Mecway's *Time step size*): NL-81 bends
  90 degrees in 20 steps.
- With a small load `RESI_GLOB_RELA` stagnates at round-off: choose
  `convergence_criterion` = `RELA_OF_MAXI` with an absolute limit (§2.2, NL-80).
- Forces keep their direction (fixed load, as in Mecway: NL-83 is within 0.02 % of
  Mecway 34 with CCX). A moment about a fixed axis (plane bending) is exact (NL-81); a
  moment in 3D is NOT verified.
- Mecway 34 computes nonlinear beams with CCX only (its own solver gave no solution);
  CCX did not get the end moment of NL-81 beyond t = 0.55 s.

---

## 3. Contact

### 3.1 What the bridge generates

Mecway `contact2` becomes:

```
contact = DEFI_CONTACT(
    MODELE=model,
    FORMULATION='CONTINUE',
    FROTTEMENT='SANS',          # 'COULOMB' if a pair has friction > 0
    ZONE=(_F(GROUP_MA_MAIT='<master>', GROUP_MA_ESCL='<slave>'),),  # + COULOMB=mu
)
```

- **Formulation (`contact_algo`, label "Contact method (STANDARD / PENALISATION)").** `CONTINUE` with per zone
  `ALGO_CONT`:
  - `STANDARD` (default, CA default): augmented Lagrangian (EDF R&D, U4.44.11), with
    the contact pressure as an extra unknown on the slave side; no stiffness needed, no
    penetration.
  - `PENALISATION`: contact pressure = `COEF_PENA_CONT` × penetration, with
    `COEF_PENA_CONT` = Mecway's *normal stiffness* (Pa/m); with friction
    `ALGO_FROT='PENALISATION'` with `COEF_PENA_FROT` = *tangential stiffness* (if that
    is 0, Lagrange friction). This is how Mecway itself computes (Mecway, 2026,
    §9.9.2). Choose this if `STANDARD` loses the contact or stops with
    `MECANONLINE9_4` with `LAGS_C` in the message (line contact). Verified: the
    penetration is exactly p/kn (NL-03d/f) and line contact between hex20 beams is
    exact (NL-03b), where `STANDARD` fails (NL-03a). Against Mecway (headless):
    Samples/PipeClip with `PENALISATION` + `MAXI` follows the clip displacement within
    2..8 % (with `STANDARD` the contact was lost); Tutorials/AssemblyWithContact
    (Fixed_support) 21.74 vs 21.97 µm (with `STANDARD`: `MECANONLINE9_4`).

  Difference from Mecway with `STANDARD`: Mecway "unilateral elastic" is a penalty
  method with a stiffness per area (Mecway, 2026, §9.9): Mecway allows some
  penetration, Code-Aster does not at the slave points (KNOWN_BUGS 43).
- **Integration.** On quadratic slave faces (tet10, hex20, quad8 ...) the bridge sets
  `INTEGRATION='NCOTES'`; linear faces keep the CA default `'AUTO'`. With `'AUTO'` the
  contact patch test on hex20 with non-matching meshes failed (1.5 to 4.6 % error),
  with `'NCOTES'` it is exact (NL-03c to f). Code-Aster then issues the harmless alarm
  `CONTACT3_16` (no `CONT_NOEU`). Your own `#ASTER-ZONE INTEGRATION=...` takes
  precedence.
- **Mecway contact type.** Mecway has `unilateralelastic` (contact) and
  `bondedelastic`, `bondedtie` and `bondedce` (bonded). Only `unilateralelastic`
  becomes `DEFI_CONTACT`. A bonded pair becomes `AFFE_CHAR_MECA/LIAISON_MAIL` (rigid;
  `bondedelastic` without its stiffness, reported): `TYPE_RACCORD='MASSIF'` (solid on
  solid, master = the solid elements behind the faces), `'COQUE'` (shell on shell, also a shell edge on a shell face; rigid, without
  the rotation about the normal, §3.10) or
  `'MASSIF_COQUE'` (solid slave on shell master). Shell slave on solid master: a shell
  face couples the displacements (`'MASSIF'` with the shell nodes); shell edges of a
  single component are connected rigidly (`'COQUE_MASSIF'` with the thickness and the
  normal field of the shell), otherwise the edge acts as a hinge (WARNING). Beam ends
  as slave are reported and skipped (KNOWN_BUGS 21).
- **Nonlinear only.** `contact2` only goes to `STAT_NON_LINE`/`DYNA_NON_LINE`; with
  `lin_static_3d` (also S30 via `auto`) the bridge stops with an ERROR. Choose
  `nonlin_static_3d` for contact. Bonded contact (`LIAISON_MAIL`) also works in a
  linear analysis.
- **Compression only support** (Mecway) becomes `DEFI_CONTACT
  FORMULATION='LIAISON_UNIL'` (U4.44.11 §3.8), only in a model without `contact2` (one
  `DEFI_CONTACT` per analysis; KNOWN_BUGS 22).
- **Friction.** If at least one pair has a friction coefficient > 0, then
  `FROTTEMENT='COULOMB'` for all zones, with `COULOMB=` per zone (0 for pairs without
  friction).
- **Adaptation.** CA default `ADAPTATION='CYCLAGE'`: if a contact point keeps
  switching status, Code-Aster switches there to penalty with a maximum penetration
  (U4.44.11, "Operand ADAPTATION"; U2.04.04 §4.1). Then check the penetration in the
  convergence table in the `.mess`.
- **Faces.** Only faces of solid elements and shell faces. Other pairs are reported
  (ERROR in `<model>_<run-id>_bridge_log.txt`) and skipped.
- A **suppressed** contact in Mecway (`suppressed`) is skipped. Useful to switch
  contact off temporarily (§4).
- **Fixed slave nodes.** Slave nodes that are also in a fixed support are excluded
  per zone with `SANS_GROUP_NO` (U4.44.11 §3.1.3; `bridge_mesh._exclude_fixed_slaves`,
  INFO in the log). Your own `#ASTER-ZONE SANS_GROUP_NO=...` takes precedence. Other
  constraints on slave nodes (symmetry, displacement, ...) are not excluded (§3.7).
- **Coarse slave.** If the slave side is clearly coarser than the master (element size
  more than 2× larger), the bridge issues a WARNING (`bridge_mesh._check_contact_sides`):
  the fine master can then penetrate the slave without contact force. The bridge does
  not swap the sides itself (§3.2).

### 3.2 Master and slave

The bridge takes master and slave as set in Mecway. Choose them well; Code-Aster only
prevents slave points from penetrating the master face, the other way round is
possible (EDF R&D, U2.04.04 §2.1).

| Master (`GROUP_MA_MAIT`) if the face... | Slave (`GROUP_MA_ESCL`) if the face... |
|---|---|
| is rigid | is curved |
| covers the other (is larger) | is smaller |
| has a much larger apparent stiffness (N/m) | has a small apparent stiffness |
| is meshed much more coarsely | is meshed much more finely |

(U2.04.04 §2.2.1 and §2.2.2.) In short: master = stiff tool / coarse face, slave = fine
or deforming face. A sharp corner you cannot avoid: the face with that corner becomes
slave (U2.04.04, "Sharp angles"). With convergence problems, especially with
plasticity, swapping the roles can help (U2.04.04 §2.2.3). Many master nodes inside
the slave face after the analysis: mesh too coarse or too large a difference in
fineness (U2.04.04 §2.2.5).

### 3.3 Normals

Contact faces must have an **outward** normal (U2.04.04, "Orientation of the normals";
U4.44.11).

- The bridge applies `MODI_MAILLAGE ORIE_PEAU` to the contact (and pressure) faces of
  solid elements.
- For shell faces the bridge does not set `ORIE_NORM_COQUE`.
- Code-Aster checks the orientation by default and stops on an error
  (`VERI_NORM='OUI'`, catalogue).

### 3.4 Initial gap and initial penetration

The bridge does not set `CONTACT_INIT`, so the CA default `'INTERPENETRE'` applies
(catalogue 17.4, U4.44.11): at the start, all points with zero gap or with penetration
are active. Tolerance: 1e-6 × the smallest edge (U2.04.04 §4.4.1).

- An initial penetration is pushed out and **produces forces**; it is not a geometric
  correction (U2.04.04 §4.4.1). So make sure the mesh in Mecway has no overlap.
- Other values (not via the bridge): `'OUI'` activates all points, also with a gap
  (useful if faces almost but not quite close); `'NON'` activates nothing.
- **Parts held in place only by contact.** In statics the matrix is then singular as
  long as there is no contact. Solutions (U2.04.04 §4.4, §4.1; Mecway, 2026, §6.2.3):
  initial contact (zero gap), weak springs (elastic support), or first a step with an
  imposed displacement until there is contact. In dynamics a rigid-body motion is
  allowed.

### 3.5 Zones sharing slave nodes

Code-Aster forbids nodes that lie in the slave faces of two zones (message
`CONTACT2_16`; U2.04.04 §2.1, U4.44.11). Mecway does allow it (for example a profile
that is slave against a blade and against a contour).

The bridge merges such pairs into one zone: master = union of the masters, slave =
union of the slaves (`DEFI_GROUP ... UNION`, groups `CMAIT<n>`/`CESCL<n>`). Friction:
the largest coefficient; a WARNING is written to `<model>_<run-id>_bridge_log.txt` if
they differed (KNOWN_BUGS 10). The solution suggested by `CONTACT2_16` itself (swapping
master and slave) is not used by the bridge: the stiff tool would then become slave.

Master and slave face of **one** zone may not share nodes either, otherwise Code-Aster
stops (U2.04.04 §2.3.4). The bridge does not exclude such nodes.

### 3.6 Self-contact

Not possible in Code-Aster, except when you know the contact area in advance and
specify it as two separate faces (U2.04.04 §2.2). The bridge reports a self-contact (or
master = slave) as an ERROR and skips it.

### 3.7 Contact and boundary conditions (symmetry)

If a slave node also lies on a symmetry plane or another boundary condition, the
friction condition can conflict with it; the matrix becomes singular as soon as there
is contact (U2.04.04 §4.7). Code-Aster solutions:

- `SANS_GROUP_NO`: no contact on those nodes, the boundary condition wins (U2.04.04
  §2.3.4). The bridge sets this itself for nodes of a **fixed support** (§3.1); for
  other conditions use `#ASTER-ZONE`;
- `SANS_GROUP_NO_FR` with `DIRE_EXCL_FROT`: excludes one friction direction (U2.04.04
  §4.7; not set by the bridge);
- `ALGO_CONT='LAC'` does not have this problem (U2.04.04 §3.1.4).

Conditions that share nodes (pinned, frictionless, symmetry, displacement, couplings)
are reported by the bridge beforehand with a WARNING listing the selection names
(`bridge_mesh._report_constraint_overlaps`); resolve them in Mecway. See also
KNOWN_BUGS 8 (duplicate boundary conditions).

### 3.8 Alternatives in Code-Aster

The bridge does not set these options itself (except `LIAISON_MAIL`). You can pass them
with `#ASTER` lines (§3.9), for example `#ASTER-ZONE ALGO_CONT='PENALISATION'`.

| Option | For | Source |
|---|---|---|
| `ALGO_CONT='PENALISATION'` with `ADAPTATION='ADAPT_COEF'` (CONTINUE) | Penalty without Mecway's stiffness: Code-Aster chooses the stiffness itself from `PENE_MAXI` (default 1e-2 × smallest edge). Penalty with Mecway's stiffness is the setting `contact_algo` (§3.1). | U4.44.11, U2.04.04 §4.12 |
| `FORMULATION='DISCRETE'` | Few contact degrees of freedom without friction (`CONTRAINTE`); `GCP` for many. Cannot handle parts held in place only by contact. With friction: prefer CONTINUE. | U2.04.04 §3.4, §4.4 |
| `ALGO_CONT='LAC'` | Strongly non-matching meshes, accurate contact pressure. Requires `CREA_MAILLAGE/DECOUPE_LAC`. According to U2.04.04 §3.1.4 still without friction; the 17.4 catalogue does accept LAC in the friction block (NOT verified whether that works). | U2.04.04 §2.1, §3.1.4 |
| `GLISSIERE='OUI'` | Permanent contact: faces stay together (bilateral), may slide. | U4.44.11, U2.04.04 §4.1 |
| `AFFE_CHAR_MECA/LIAISON_MAIL` | Bonding two faces, also with non-matching meshes (no contact). The bridge uses it for Mecway's bonded contact (§3.1); also usable for very local contact or as a pre-calculation. | U4.44.01 §5.13, U2.04.04 §4.1, §4.5.2 |
| Springs `DIS_T` + `DIS_CHOC` | Point contact in a fixed direction (penalty); not for large displacements. | U2.04.04 §4.10 |
| `CONTACT_INIT`, `SANS_GROUP_NO(_FR)` | See §3.4 and §3.7. | U4.44.11 |

### 3.9 Custom Code-Aster input: `#ASTER` lines

For what Mecway cannot enter, put `#ASTER` lines in a free text field of Mecway
(OpenRadioss: `#ASTER`, Mystran: `$ASTER`, CCX: `**ASTER`). Syntax, selection names
(`<<Mecway selection>>`), pitfalls and worked examples (including `#ASTER-CONTACT`,
`#ASTER-ZONE` and `#ASTER-OPTIE` for contact) are in
[`ASTER_lines_examples.md`](ASTER_lines_examples.md).

### 3.10 Example: bonding plates (bonded contact between shells)

You connect two plate parts that each have their own mesh with Mecway's bonded
contact; the meshes do not have to match. Example model:
[`TestFiles/Voorbeelden/Voorbeeld_T.liml`](../../TestFiles/Voorbeelden/Voorbeeld_T.liml)
(made with `maak_voorbeelden.py`, the same model as verification case LS-07a).

**Model.** Cantilever plate strip 200 × 20 mm, thickness 2 mm, steel, in two parts:
`Deel_A` (x = 0..100 mm, 10 × 4 quad4) and `Deel_B` (x = 100..200 mm, 10 × 7 quad4, own
nodes). Clamped at x = 0, 1 N in −Z on the free edge.

**Setting it up in Mecway:**
1. Mesh the two parts separately (own nodes, do not merge). Each part gets a material
   with a plate thickness (*Plate*).
2. Make two face selections: the **master** = shell faces of part A along the seam
   (here the last row of elements, `Lijm_A`; all faces of A is fine too), the **slave**
   = the edge of part B that lies on A (`Lijm_B`; shell edges are selected as faces of
   the elements). Use the finer side as slave.
3. Add a contact with master `Lijm_A`, slave `Lijm_B` and type bonded (*bonded*, in the
   `.liml` `type="bondedtie"`). Tolerance 0 (automatic) is fine: the bridge then ties
   all slave nodes (no `DISTANCE_MAX`). *Bonded elastic* is bonded rigidly (the
   stiffness is not translated, reported).
4. Analysis linear static (`lin_static_3d`): bonded contact is not `DEFI_CONTACT` and
   also works in a linear analysis.

**What the bridge makes of it:** `AFFE_CHAR_MECA` with `LIAISON_MAIL`
(`GROUP_MA_MAIT` = the shell elements of the master, `GROUP_NO_ESCL` = the nodes of the
slave edge, `TYPE_RACCORD='COQUE'`, `DDL=('DX','DY','DZ','DRX','DRY')`). The rotations in
the master plane are tied, so the seam carries a moment (no hinge). The bridge leaves
out the rotation about the plate normal (*drilling*, only a fictitious stiffness in
DKT): with that tie Code-Aster stops with `FACTOR_11` (singular matrix).

**Result (verified, [Verification.md](Verification.md) LS-07):**

| Quantity | Bonded (bridge) | One mesh (bridge) | Mecway, one mesh | Analytical |
|---|---|---|---|---|
| tip deflection | 0.94220 mm | 0.94257 mm | 0.94148 mm | 0.95238 mm |
| tip rotation | 7.0899 mrad | 7.0938 mrad | 7.0901 mrad | 7.1429 mrad |

Analytical is the Euler beam P L³/(3EI) and P L²/(2EI) with E (not E/(1−ν²)): with free
side edges the strip bends like a beam; the clamping makes it slightly stiffer
(−1.0 %). The bonded strip differs 0.04 % from one continuous mesh and 0.08 % from
Mecway; the rotation is equal on both sides of the seam (0.01 %).

**T-joint** (edge of a rib bonded onto the face of a plate, LS-07c..e): the rib passes
its moment through the bond into the plate. With the foot line on a mesh line of the
plate, the rib deflection is within 0.1 % of shared nodes (0.4 % of Mecway). With the
foot line in the middle of the plate elements, `LIAISON_MAIL` interpolates the plate
rotation linearly across the kink under the rib: 5 % too stiff with 4 mm elements, 11 %
with 12 mm. So put the foot line on a mesh line (or refine there).

**Skewed or curved master** (LS-07f, g): `DDL` of `LIAISON_MAIL` only knows global
components, so the rotation about the normal can only be left out there when the
master is normal to a global axis. Otherwise the bridge writes the tie itself, per
slave node as `LIAISON_DDL`: the three displacements and the two rotations in the
tangent plane of the master at the projected point (the same interpolation as
`LIAISON_MAIL`). MUMPS then still wrongly sees a nearly singular matrix (the drilling
rotation only has a fictitious stiffness); the bridge therefore sets `solver_nprec`
to −1 for that run (WARNING). In a linear static analysis `RESI_RELA` still checks
the solution: the same strip without clamping stops with `FACTOR_57`.

| Model | Bonded (bridge) | Reference |
|---|---|---|
| strip rotated 30° (LS-07f), tip deflection | 0.94220 mm | 0.94220 mm (LS-07a, in the XY plane) |
| tube R 20 mm, 16 and 24 elements around (LS-07g) | 2.7306e-4 mm | 2.7277e-4 mm (one mesh, 24 around); Mecway 2.7235e-4 mm; Timoshenko 2.7233e-4 mm |

**Quadratic shell (tri6/quad8, `COQUE_3D`) as master** (LS-07i..k): the centre node
that Code-Aster adds (QUAD9/TRIA7) only has rotations, and `LIAISON_MAIL` asks for a
displacement there (`CHARGES2_31`). The bridge therefore writes the displacements
itself (`LIAISON_DDL` with the quad8/tri6 shape functions) and leaves the rotations to
`LIAISON_MAIL` (`DDL` rotations only, the centre node then counts). With a skewed or
curved quadratic master these are all three rotations, with `solver_nprec` −1. Quad8
plate 10 × 4 with a rib in the middle of the elements, side load on the rib:
1.1342e-2 mm, shared nodes 1.1536e-2 mm (−1.7 %, the kink under the rib), rotated 30°
1.1336e-2 mm.

**Limitations:**
- A shell face on a solid only ties the displacements; beam ends as slave are not
  translated (KNOWN_BUGS 21).
- Mecway's own solver ties no rotations for a shell edge as slave: the bonded strip and
  the T-joint become a mechanism there (measured headless, Mecway 34). A comparison with
  Mecway is therefore only possible with a continuous mesh.
- Shells with an *Element offset* in the contact: the slave nodes (always the Mecway
  nodes) are tied to the master nodes; only with `LIAISON_MAIL` on a master on its own
  nodes (solid on a quad8 shell) to the offset surface. The bridge reports which
  surface (WARNING); what Mecway does has not been checked (KNOWN_BUGS 108). Shell on
  shell with an offset on own nodes (quad8/tri6): `solver_nprec` −1, otherwise a false
  `FACTOR_11` (LS-66: 0.94266 mm, Mecway continuous 0.94148 mm).

---

## 4. "My analysis does not converge"

### 4.1 What the bridge does then

- Code-Aster stops `STAT_NON_LINE`/`DYNA_NON_LINE` with a `ConvergenceError`, usually
  `MECANONLINE9_7` (too many Newton iterations). The stored steps are kept (EDF R&D,
  U4.51.03, "Shutdown management"; text of `MECANONLINE9_7` in 17.4).
- The bridge catches this error (`try/except` in the `.comm`), writes
  `BRIDGE_ONVOLLEDIG <time>` into the `.mess` and continues with the post-processing.
- Mecway shows the message with the error code, advice and "Last time with results:
  ... s".
- **Dynamic**: all output times up to that time go to Mecway.
- **Static**: route `liml` all archived steps up to that time, route `tabel` only the
  last time reached (§2.1).
- An error other than `MECANONLINE*` (e.g. `DVP_2`) stops the run without results.
- Other error codes, with causes and solutions:
  [`CodeAster_error_messages.md`](CodeAster_error_messages.md).

### 4.2 Step-by-step plan

Work from top to bottom. Source: EDF R&D, U2.04.04 §4.1 and §4.5, U2.04.01; Mecway
(2026) §6.2.3. According to U2.04.04 §4.1 contact problems "very often" have a physical
cause, not a numerical one.

1. **Read the message.** Look in `<model>_<run-id>_bridge_log.txt` (skipped contacts,
   WARNINGs) and the `.mess` (convergence table: residual, contact status,
   penetration).
2. **Check the model.**
   - master/slave choice (§3.2), normals (§3.3);
   - initial gaps and penetrations (§3.4);
   - parts held only by contact (§3.4);
   - boundary conditions on slave nodes (§3.7);
   - skipped contact pairs or self-contact (§3.6);
   - failed integration of the constitutive law can come from an element that is
     turned inside out by the contact (U2.04.04 §4.1, figure 4.1-1).
3. **Look at the residual** (convergence window, graph (a)):
   - `RESI_GLOB_RELA` stays high while `RESI_GLOB_MAXI` is very small (motion without
     resistance): `convergence_criterion` = `MAXI` (§2.2, R-RIGID);
   - `RESI_GLOB_RELA` stalls just above the criterion (plastic solids, `GDEF_LOG`;
     e.g. ~2e-6 at 1e-6): `convergence_resi_rela` = 1e-5 (the default), or
     `convergence_criterion` = `RELA_OF_MAXI` with `convergence_resi_maxi` above the
     absolute residual at which it stalls (§2.2, NL-01, NL-01b).
4. **Decouple the nonlinearities** (U2.04.04 §4.5.1). Do not switch them all on at
   once:
   1. contact only, linear elastic material, `deformation` = `PETIT` (remove the
      hardening curve in Mecway);
   2. plasticity without contact (suppress contact in Mecway);
   3. if needed large deformation without contact and without plasticity; if that
      fails, try another `deformation` (`SIMO_MIEHE`, `GDEF_LOG`, `PETIT_REAC`).
5. **Friction later.** Start without friction (coefficient 0 in Mecway) (U2.04.04
   §4.1).
6. **Contact method.** With line contact, contact that is lost or `MECANONLINE9_4`
   with `LAGS_C`: `contact_algo` = `PENALISATION` (§3.1, NL-03b).
7. **Smaller steps.** Reduce Mecway's *Time step size* (static; without a step size
   increase `substeps_per_interval`) or increase `substeps_per_output` (implicit). Code-Aster already cuts a failed step itself
   (`DECOUPE`, up to 6 levels, §2.1); smaller initial steps help when it keeps getting
   stuck at the same time. Not with a stalling residual (step 3): smaller steps make
   that worse (R-SUB40).
8. **Newton.** Keep `newton_reac_iter` = 1 (R-REAC0). Increase `newton_max_iter` with
   contact (U4.51.03). `PREDICTION='ELASTIQUE'` helps according to U2.04.04 §4.5.2, but
   is not settable in the bridge.
9. **Large strains.** Above approx. 5 % strain: `GDEF_LOG` or `SIMO_MIEHE` instead of
   `PETIT` (§2.3).
10. **Last resort for quasi-static:** compute slowly with dynamics (`dyna_impl_3d`)
    over a long time, with the real density and large steps. The mass stabilises;
    check that the inertia forces stay small (U2.04.04 §4.5.3).
11. **Converged is not the same as correct** (U2.04.04 §4.1). Check penetration,
    oscillations in the contact pressure and, if needed, a mesh convergence study.

Not as a setting, but with `#ASTER-CONTACT`/`#ASTER-ZONE` (§3.9), according to
U2.04.04: `ADAPTATION` (§4.12), `ALGO_RESO_FROT='POINT_FIXE'` with friction (§4.1),
`RESI_GEOM`, `ITER_GEOM_MAXI`, `LISSAGE='OUI'` for curved coarse faces (§2.4.3). Only by
hand in the `.comm`: a predictive analysis with `PREDICTION='DEPL_CALCULE'` (§4.1).

### 4.3 What Code-Aster cannot do

- **No element deletion.** Cutting through or failure in which elements disappear
  (erosion, as in explicit crash codes) is not in the Code-Aster documentation read
  (NOT found). Damage is modelled as an internal variable; the element stays in the
  mesh (e.g. `ENDO_HETEROGENE`: "broken" element = damage variable 1, EDF R&D,
  U4.51.11). An analysis that goes as far as cutting through therefore no longer
  converges or gives heavily distorted elements. The bridge can however imitate
  **element failure**: an element above a plastic strain limit gets a very low
  stiffness and zero stress (nonlinear static and dynamic; [`Failure.md`](Failure.md)).
- **Damage and fracture models do exist**, but the bridge does not support them (only
  `ELAS`, `VMIS_ISOT_*`/`VMIS_CINE_LINE`, `CABLE` and the discrete laws, §1):
  - `ROUSSELIER` (ductile fracture by void growth; with `SIMO_MIEHE`);
  - `ENDO_*` laws (e.g. `ENDO_ISOT_BETON`, `ENDO_SCALAIRE`, `ENDO_CARRE`);
  - cohesive zones `CZM_*` with joint elements, or in XFEM (`ALGO_CONT='CZM'`).
  (U4.51.11, U4.44.11.)
- **HOMARD** (`MACR_ADAP_MAIL`) is mesh adaptation: it refines or coarsens an
  existing mesh based on a field or a geometric rule, and can transfer fields (EDF R&D,
  U7.03.01). It is not automatic remeshing of distorted elements and not element
  deletion. Not supported by the bridge.

### 4.4 Convergence screen

For every analysis the bridge opens a separate window (start screen: "Convergence and
messages window", on by default). For a nonlinear analysis (`STAT_NON_LINE`,
`DYNA_NON_LINE`, `THER_NON_LINE`) it follows the convergence live; for a linear static
analysis (`MECA_STATIQUE`) it shows the linear solver (see *Linear analysis* below);
for `THER_LINEAIRE` the messages (errors and alarms with explanation in the chosen
language) and the diagnosis. Afterwards: the *Convergence window* button in the main
window of the bridge shows the last run in the working directory; with "Open .mess ..."
you choose another file. The window stays open next to Mecway and the main window. It
runs in Code-Aster's Python; closing it has no effect on the run or on Mecway.

| Graph | What you see | What to look for |
|---|---|---|
| (a) Residual | `RESI_GLOB_RELA` (left, red line = criterion) and `RESI_GLOB_MAXI` (right) per Newton iteration, for the last N attempts | Healthy: per attempt a quick drop below the red line. If the residual stays around 1 or jumps up and down, look at (d). If `RELA` stays high with a `MAXI` of ~0, or `RELA` stalls just above the line: §4.2 step 3. |
| (b) Progress | Time per attempt; red = failed (Code-Aster splits the step), grey staircase = subdivision level | Many red points at the same time: the analysis gets stuck there. See what happens physically then (first contact, cutting through, §4.3). |
| (c) Newton per attempt | Iterations per attempt with `ITER_GLOB_MAXI`; black points = geometric contact loops | Rising number of iterations before a failure: the step is too large or the contact changes strongly (§4.2 steps 7 and 8). |
| (d) Contact | Per Newton iteration: status changes (grey bars, column `VARI. CONT.`), `PRESSURE ERROR` and `CRITERE VALEUR` at the end of a geometric loop (G2, G3 ...) | If the status changes do not go to 0, points jump between contact and no contact: check master/slave, normals and initial gaps (§3.2-3.4). Without contact and with `energy_balance` on: the energy balance. |
| (e) Messages | Errors and alarms with the Code-Aster code and explanation | "Zero pivot at node ..., component LAGS_C" (Dutch: "Pivot nul bij knoop ..."): contact condition over-constrained or a part hangs only on contact (§3.4, §3.7). "Python error in `<model>_<run-id>.comm`": usually a typo in `#ASTER` lines. |

Below the graphs are the details of the selected attempt (slider "Attempt" or click in
(b)/(c)): number of contact links, status changes, the node with the largest residual
and the CPU time. The estimated remaining time follows from Code-Aster's percentage and
is rough. That `VARI. CONT.` is the number of status changes is the bridge's reading;
the U documentation does not say so (NOT verified).

`energy_balance` (Energy balance; implicit dynamics only, default off) sets
`ENERGIE=_F()` in `DYNA_NON_LINE` (EDF R&D, U4.53.01 §3.22); the result does not change
(R-ENERGY). With contact `CONTINUE` Code-Aster then stops with `MECANONLINE5_15`; the
bridge omits it in that case and reports it in the log.

#### Linear analysis (`MECA_STATIQUE`)

A linear analysis has no Newton iterations: Code-Aster builds the stiffness matrix and
solves Ku = F once. Like the solver monitor of common pre/post-processing software, the
window then shows four cards (the bridge sets `INFO=2` in `MECA_STATIQUE`, §2.6):

| Card | What you see | What to look for |
|---|---|---|
| (a) System and solver | Number of equations (physical degrees of freedom + Lagrange parameters of supports and couplings), nodes, non-zero terms and fill of the matrix; with MUMPS also the ordering (METIS, AMF ...), terms in the factors, the work in flop, the memory and the pivots; the criteria (`RESI_RELA`, `NPREC`) | Memory almost equal to `memory_limit`: raise it or use GCPC. Orange pivots: see (d). |
| (b) Time per phase | Stiffness matrix (elements + assembly), analysis (ordering), factorisation, load vector, solve, stresses + storage; during the run the active phase (blue) is shown live | For large models the factorisation dominates. MUMPS only reports at the end of a phase that it is done; the estimated work (flop) is in (a). |
| (c) Quality (MUMPS) | On a log scale: scaled residual, 'backward errors' ω₁/ω₂, the error bound (red dashed: `RESI_RELA`) and the condition numbers (green < 1e4, orange > 1e12) | The error bound must lie to the left of the red line. |
| (c) Residual (GCPC) | Relative residual ‖r‖/‖f‖ per iteration on a log scale, with `RESI_RELA` | A long flat staircase = slow convergence. |
| (d) Assessment | Green = fine, grey = information, orange = attention, red = error, with explanation | See the list below. |

What the numbers mean (EDF R&D, U2.08.03 §7.2.1; MUMPS manual: RINFOG(6)-(11)):

- **Error bound** (RINFOG(9)): upper bound for the relative error in the
  displacements, approximately condition number × backward error. Code-Aster compares
  it with `RESI_RELA`; larger = stop with `FACTOR_57`. In the test models (252 to
  268,569 equations): 1e-11 to 1e-8.
- **Backward error** ω₁, ω₂ (RINFOG(7)/(8)): how well the computed solution solves the
  system itself. For a healthy factorisation of the order of machine precision
  (~1e-15). Larger than 1e-12 (the bridge's limit) indicates numerical difficulty in
  the factorisation.
- **Condition number** (RINFOG(10)/(11)): sensitivity of the solution to rounding
  errors. According to U2.08.03 it lies between 1e4 (well conditioned) and 1e20 (very
  badly conditioned); in the test models 5e4 to 2e7. Above 1e12 it indicates a (nearly)
  singular matrix (U2.08.03 §7.1): a part that is not or hardly held, a mechanism, or
  extreme stiffness differences (e.g. a very stiff spring next to a soft part).
  Measured: 2e16 for a block held in X only (R-FREE: 5.8e16, error bound 12.6).
- **Residual before/after iterative refinement**: MUMPS improves the solution with a
  few extra steps if that helps (`POSTTRAITEMENTS='AUTO'`, at most 4, U4.50.01
  §3.5.3); 0 steps means the first solution was already good.
- **Negative pivots**: a system with Lagrange parameters is not positive definite; in
  the test runs the number of negative pivots equalled the number of Lagrange
  parameters. If there are more, the stiffness itself is not positive definite
  (mechanism or negative stiffness; measured: 10 with 8 Lagrange parameters with a
  freely moving block). This is a deduction of the bridge (NOT verified in the U
  documentation).
- **Delayed pivots** (INFOG(13)): MUMPS had to pivot numerically; a few are harmless,
  many indicate a badly scaled system.
- **GCPC**: Code-Aster writes an iteration only when the residual has dropped by a
  factor 10 (`gcpc.F90`, `paraaf = 0.1`; every iteration only with `INFO=3`, which
  `MECA_STATIQUE` does not allow). The graph is therefore a staircase. More than 20 % of
  the number of equations in iterations is marked as slow by the bridge (choice of the
  bridge).

With a `FACTOR_57` message (error bound > `RESI_RELA`) the cause is almost always the
input, not the solver: look for the part that can move freely (see
[`CodeAster_error_messages.md`](CodeAster_error_messages.md)). Raising `RESI_RELA` only
hides it (U2.08.03 §7.2.1: the tolerance must be taken seriously).

---

## 5. References

**Code-Aster documentation** (EDF R&D, version "default"; cited in the text as
"EDF R&D, U4.51.03" or, within a paragraph, just the document number). The default
values have been checked against the 17.4 catalogue.

- EDF R&D (2020). *Notice d'utilisation des solveurs linéaires*, U2.08.03. Read: version 11-01-2024, `https://code-aster.org/doc/default/fr/man_u/u2/u2.08.03.pdf` (§3 choice of solver, §7.1 singular matrix, §7.2.1 error bound and condition number). Local: version 05-05-2020.
- EDF R&D (2020). *Opérateur STAT_NON_LINE*, U4.51.03, 30-04-2020. Local; online "Calculation parametrization", "Nonlinear solver settings", "Convergence settings".
- EDF R&D (2021). *Mot clé SOLVEUR*, U4.50.01. Read: version 11-01-2024, `https://code-aster.org/doc/default/fr/man_u/u4/u4.50.01.pdf` (§3.5.3 `RESI_RELA`/`POSTTRAITEMENTS`, §3.6 GCPC, §3.7 PETSC). Local: version 04-11-2021.
- EDF R&D (2021). *Opérateur DEFI_CONTACT*, U4.44.11, 04-11-2021. Local and online (all operands).
- EDF R&D (2021). *Opérateur DEFI_MATERIAU*, U4.43.01, 03-11-2021. Local (`TRACTION` §5.1.1).
- EDF R&D (2021). *Opérateurs AFFE_CHAR_MECA*, U4.44.01, 04-11-2021. Local (`LIAISON_MAIL` §5.13).
- EDF R&D (n.d.). *Instructions for using contact in code_aster*, U2.04.04. Online, §1 to §4.
- EDF R&D (n.d.). *Tips for using STAT_NON_LINE*, U2.04.01. Online, "Introduction" and "Convergence tools".
- EDF R&D (n.d.). *General tips for using DYNA_NON_LINE*, U2.06.13. Online, "Discretization of the ongoing problem" and "Optimizing performance".
- EDF R&D (n.d.). *Operator DEFI_LIST_INST*, U4.34.03. Online, "DEFI_LIST" and "ECHEC".
- EDF R&D (n.d.). *Operator DYNA_NON_LINE*, U4.53.01. Online, "Operands" (`SCHEMA_TEMPS`, `MASS_DIAG`, `ENERGIE`).
- EDF R&D (n.d.). *Nonlinear behaviors, keyword COMPORTEMENT*, U4.51.11. Online, `DEFORMATION`, damage models.
- EDF R&D (n.d.). *Macro-command MACR_ADAP_MAIL*, U7.03.01. Online, purpose.

Local = English machine translation in a local folder with Code-Aster documentation.
Online = DocAster, `https://docaster-en-codeaster-doc-4113bb35b8213385c636b94f1536856d7f617.gitlab.io/manuals/man_u/`
(`u2/u2.04.04/index.html` etc.), consulted 5 October 2026; the site does not state a
version number.

**Code-Aster installation** (EDF R&D, code_aster 17.4, Windows build v2025):
`%LOCALAPPDATA%/code_aster/v2025/17.4/lib/aster/code_aster/`

- `Cata/Commands/defi_contact.py`, `stat_non_line.py`, `dyna_non_line.py`,
  `defi_list_inst.py`, `meca_statique.py` (`INFO` 1 or 2);
- `Cata/Commons/c_convergence.py`, `c_newton.py`, `c_comportement.py`,
  `c_solveur.py`;
- `Messages/contact2.py` (`CONTACT2_16`), `contact3.py` (`CONTACT3_16`),
  `mecanonline9.py` (`MECANONLINE9_7`), `subdivise.py` (`SUBDIVISE_3`).
- GCPC output: `bibfor/algeline/gcpc.F90` in `https://gitlab.com/codeaster/src` (which
  iterations are written with `INFO=2`).

**Mecway**: Mecway (2026). *Mecway Finite Element Analysis, Manual, version 33*,
`C:\Program Files\Mecway\manual.pdf`: §6.2 (nonlinear static, convergence), §9.9
(contact), §9.14 (pressure), §9.20 (centrifugal force).

**Literature**

- Belytschko, T., Liu, W.K. and Moran, B. (2000). *Nonlinear Finite Elements for Continua and Structures*. Chichester: Wiley. Stable step of central differences with damping (cited in `bridge_to_aster._damped_step_factor`; section NOT checked in the book).
- Hilber, H.M., Hughes, T.J.R. and Taylor, R.L. (1977). Improved numerical dissipation for time integration algorithms in structural dynamics. *Earthquake Engineering and Structural Dynamics*, 5, 283–292.
- Hughes, T.J.R. (2000). *The Finite Element Method: Linear Static and Dynamic Finite Element Analysis*. Mineola: Dover. Chapter 9.

**Bridge code**: `Scripts/bridge_utils.py` (`resolve_auto_analysis`),
`Scripts/bridge_to_aster.py` (`_build_nonlin_static`, `_build_listinst_block`,
`_build_contact_block`, `_build_dyna_listinst_block`, `_critical_time_step`,
`_build_etat_init_block`, `_build_comportement_block`, `_deformation_for`,
`_convergence_args`), `Scripts/bridge_mesh.py` (`_merge_contact_zones`,
`_exclude_fixed_slaves`, `_check_contact_sides`, `_report_constraint_overlaps`),
`Scripts/bridge_run_aster.py`, `Scripts/bridge_gui.py`.
