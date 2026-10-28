# Element failure

*Nederlandse versie: [Bezwijken.md](../Bezwijken.md)*

Code-Aster cannot delete elements. The bridge therefore uses an approach that is
common in implicit analyses. When an element reaches its failure limit, it gets a very
low stiffness and its stress goes to zero. The element stays in the mesh, but from
that moment it carries (almost) nothing. The load redistributes over the rest of the
model. Alomar et al. (2023) use the same approach: they added element deletion to
Code_Aster by replacing failed elements with a virtual material of very low
stiffness.

In the nonlinear analyses: **"Nonlinear static"**
(`STAT_NON_LINE`), **"Dynamic (implicit)"** and
**"Dynamic (explicit)"** (both `DYNA_NON_LINE`). Not in the
linear and thermal analyses.

## 1. Usage

Give each Mecway material a **failure limit**: the equivalent plastic strain at which
an element fails. The bridge uses the average over the element's integration points.
There are three ways; the first one that exists counts:

1. **An `#ASTER-BEZWIJKEN` line** in Mecway's custom model definition (with solver CCX:
   *Analysis* > *CCX* > *Custom model definition*; the bridge also reads the
   OpenRadioss and Mystran fields, see [`ASTER_lines_examples.md`](ASTER_lines_examples.md)):

   ```
   ** ASTER-BEZWIJKEN Kerfstaal = 0.05
   ```

   `Kerfstaal` is the Mecway name of the material; `*` means all plastic materials
   without their own line. `#ASTER-FAILURE` works as well.
2. **OpenRadioss `PLAS_TAB`**: the value `Eps_p_max` from the material card.
3. **The setting** "Failure limit all plastic mat. (0 = off)" on the *Nonlinear static*, *Dynamic (implicit)* or
   *Dynamic (explicit)* page: applies to every plastic material without its own limit.

Conditions:
- the material is plastic: isotropic (hardening curve, bilinear isotropic,
  Ramberg-Osgood or `PLAS_TAB`) or kinematic with linear hardening
  (BilinearKinematic or a linear kinematic curve) with a *tangent modulus* > 0;
- the elements are **solid elements** (hex, tet, wedge, pyr; also with the hex8
  choice `LINE_QUAD`) or **shells** (tri3/quad4 as DKT; quadratic or with linear
  shells = `COQUE_3D` as `COQUE_3D`); **no beams**;
- the model has no beams with large rotations (`elem_beam` = `POU_D_T_GD`): after a
  failed element the next step needs `RIGI_MECA`, which that element does not have
  (`CALCUL_37`); the bridge stops beforehand with an ERROR;
- `DEFORMATION`: solids `PETIT`, `PETIT_REAC` or large displacements (`GDEF_LOG`,
  also `SIMO_MIEHE`); DKT is always geometrically linear (`PETIT`/`GREEN_LAGRANGE`);
  `COQUE_3D` `PETIT` or `GROT_GDEP`.

**Shells.** The limit applies to the average over all integration points, for shells
also over the points through the thickness. In bending a shell element therefore only
fails when the strain averaged over the thickness reaches the limit (it is higher at
the surface).

**Kinematic hardening.** Code-Aster does not keep an accumulated plastic strain for
`VMIS_CINE_LINE`. The bridge computes the strain from the back stress: X = 2/3·H·εp,
with H Mecway's *tangent modulus* (the plastic modulus; Code-Aster gets
`D_SIGM_EPSI` = Et = E·H/(E+H), so H = E·Et/(E−Et)). That is the current plastic
strain. Under alternating load it is smaller than the accumulated one, so an element
fails later (WARNING).

Anything that does not meet these conditions does not fail. The bridge then writes a
WARNING to the log and reports it at the end of the run.

## 2. Settings ("Nonlinear static", "Dynamic (implicit)" and "Dynamic (explicit)" pages)

| Setting | Default | Meaning |
|---|---|---|
| "Element failure (plastic strain)" | on | off: failure limits in the model are ignored (WARNING) |
| "Failure limit all plastic mat. (0 = off)" | 0 | limit for plastic materials without their own limit |
| "Stiffness of failed element (x E)" | 1e-6 | E and the slope after yielding of a failed element, as a fraction of the original (1e-7 .. 0.1; a value outside is clipped, with a WARNING). The force a failed cross-section still transmits scales with this factor (§5) |

For a single model you can also use `#ASTER-OPTIE`, e.g.
`** ASTER-OPTIE failure_stiffness_factor = 1e-4`.

## 3. What happens

**Nonlinear static:** after **every solver step** of the time list (every interval
between the time points of the time-dependent loads, or 0 to the end time, divided
into "Substeps per time interval") the bridge does the
following inside the Code-Aster job:

1. Read the average plastic strain (`V1` = `EPSPEQ`) per element.
2. Elements above the limit get a **soft material**: E and the slope after yielding
   are multiplied by "Stiffness of failed element (x E)". The yield stress stays the same, so
   the soft element remains elastic.
3. **Stress to zero**: the stresses and internal variables of those elements are set
   to zero. Only the plastic strain is kept, because it records which elements have
   failed (isotropic; with kinematic hardening the back stresses are set to zero too). The released part of the load redistributes over the rest of the model in
   the next step.
4. The next step starts with an **elastic prediction**
   (`NEWTON PREDICTION='ELASTIQUE'`). Code-Aster subdivides the step if needed; the
   step after that starts with the normal tangent prediction (`TANGENTE`) again.

An element that has failed stays failed.

In **dynamic** analyses the bridge checks at the **output times** (Mecway's time
steps) instead of after every solver step; every output time is also a solver step.
In between, Code-Aster simply continues (implicit: "Solver steps per Mecway time step"; explicit: steps of at most
"Time step / critical time step" × the estimated
critical time step). After a failure event the velocity and acceleration are also
carried over to the next step. With implicit, that step starts with an elastic
prediction, as in static; with explicit it starts normally (`PREDICTION='TANGENTE'`:
Code-Aster allows nothing else with an explicit scheme).

## 4. Results in Mecway

- Every failure event is a WARNING in `<model>_<run-id>_bridge_log.txt`, with the
  time, the elset and the **Mecway element numbers**. At the end of the run the bridge
  reports in the status box of the main window how many elements failed.
- The convergence window shows each event as a message ("Failure at t = …").
- In the results, failed elements show a stress of about 0 in the element-node
  values, while their plastic strain is above the limit. With complete separation the
  reaction force goes to about 0.
- Nodal stresses (averaged over the elements around a node) mix failed and intact
  elements. Look at element values or at the plastic strain instead.

## 5. Test models

In `TestFiles/`. All numbers below come from runs with Code-Aster 17.4 and the default
settings unless stated otherwise (reaction force = sum over the pulled face).

| Model | What | Result |
|---|---|---|
| `BezwijkenTrekstaaf.liml` | Tensile bar 100 × 10 × 10 mm (hex8, 5 mm), a 10 mm middle slice of `Kerfstaal` (σy = 250 MPa, *tangent modulus* 0.5 GPa) between `Staal` (355 MPa, 1 GPa); displacement 0 → 6 mm in 1 s; `** ASTER-BEZWIJKEN Kerfstaal = 0.05` | at t = 0.6 s the 8 notch elements fail (Mecway 10, 11, 30, 31, 50, 51, 70, 71); the reaction force drops from 36.7 kN to 1.5–4 N (large displacements; with `PETIT` from 38.3 kN to 2–6 N) |
| `BezwijkenDeelsKerf.liml` | The same, but only the lower half of the middle slice is `Kerfstaal` | at t = 0.6 and 0.7 s 2 + 2 elements fail (11, 51 and 10, 50); each time the force drops (37.5 → 27.4 kN and 33.2 → 30.0 kN) and then rises again as the remaining part hardens |
| `BezwijkenTrekstaafDynamisch.liml` | The same bar, dynamic (Mecway D31): 6 mm in 1 ms, output every 0.05 ms. *auto* chooses "Dynamic (implicit)" | at t = 0.55 ms the 8 notch elements fail; the reaction force drops from 37 kN to ~1 kN (t = 0.6 ms) and then rings (up to ±12 kN, damped by HHT) |
| `BezwijkenTrekstaafExpliciet.liml` | The same, but with an initial velocity of 6 m/s on the pulled face and a prescribed displacement 0 there (constant velocity; the bridge also converts a prescribed displacement 0 → 6 mm in explicit, with the same result). Choose "Dynamic (explicit)" | at t = 0.55 ms the 8 notch elements fail; the reaction force then rings almost undamped around 0 (up to ±37 kN) |

Usage: open the model in Mecway, start the bridge and choose the analysis: with *auto*
the first three models get the right one (L30 → "Nonlinear static", D31 → "Dynamic (implicit)"); for `BezwijkenTrekstaafExpliciet.liml` choose
"Dynamic (explicit)" yourself (with *auto*, D31 always becomes implicit).

Variants (same models, one setting or material changed):

| Variant | Result |
|---|---|
| hardening curve (σy, σy + H at plastic strain 1) instead of bilinear | equal to bilinear (36.7 kN, t = 0.6 s): the *tangent modulus* is translated as the plastic modulus H |
| hex8 as `LINE_QUAD` (hex20) | failure at t = 0.2 s (29.6 kN → 1–5 N): the strain localizes more strongly with quadratic elements (see §6, volumetric locking) |
| general limit 0.05 ("Failure limit all plastic mat. (0 = off)") | besides the 8 notch elements, 4 steel elements right next to the notch fail (12, 32, 52, 72) |
| `DEFORMATION` = `SIMO_MIEHE` | all four models fail at the same moments as with `GDEF_LOG` (tensile bar 36.7 kN → 1.5–4 N) |
| `BezwijkenDeelsKerf` with BilinearKinematic | 2 + 2 elements at t = 0.6 / 0.7 s (37.5 → 27.2 kN and 32.9 → 29.8 kN); WARNING about the current plastic strain |
| `BezwijkenDeelsKerf` with 20 instead of 10 substeps | the second pair fails at t = 0.65 s instead of 0.7 s (smaller step, detected earlier) |
| "Stiffness of failed element (x E)" 1e-7 / 1e-4 / 1e-3 (tensile bar) | residual force at t = 1 s 0.4 N / 0.39 kN / 3.9 kN (default 1e-6: 4 N); all runs converge |
| shell strip 100 × 20 × 2 mm (quad4 5 mm, notch as the middle slice), tension 6 mm | DKT: 8 elements at t = 0.2 s, 13.0 kN → 1–4 N; `COQUE_3D`: 13.8 kN → 1–10 N |

Tested earlier with the same approach (not rerun): the shell strip also dynamic
implicit and explicit (failure at 0.15 ms) and DKT bending with a notch at the clamped
end (2 + 2 elements, 44 → 22 → 0 N).

## 6. Messages and solutions

| Message | Cause | Solution in the model |
|---|---|---|
| WARNING about kinematic hardening and the current plastic strain | `VMIS_CINE_LINE` keeps no accumulated strain; the bridge uses the current one | Expected. Under alternating load: choose isotropic hardening |
| WARNING `… kinematic hardening without a slope after yield (tangent modulus 0)` | no hardening: the back stress stays 0, so no strain to see | Give a *tangent modulus* > 0, or choose isotropic hardening |
| WARNING `… the material is not plastic` | limit on an elastic material | Give the material plasticity, or remove the limit |
| WARNING about beams (`POU_D_E`) | Code-Aster only has plasticity in multifibre beams | Model the failure region with solid elements or shells |
| ERROR `Element failure (…) does not work in a model with POU_D_T_GD beams` | after the first failed element the loop restarts with `PREDICTION='ELASTIQUE'`, and `POU_D_T_GD` cannot compute `RIGI_MECA` (`CALCUL_37`); with `TANGENTE` or `EXTRAPOLE` the step after the failure did not converge (run, Code-Aster 17.4) | Switch *Element failure* off, or choose *Beams* = `POU_D_E`/`POU_D_T` |
| WARNING `… DEFORMATION … not supported` | strain measure that does not fit the element (e.g. `PETIT_REAC` on shells) | Choose `PETIT` or large displacements |
| WARNING `The bridge supports element failure only in nonlinear analyses` | linear analysis (Static) | Choose Nonlinear static or a dynamic analysis |
| WARNING about hex8 with '3D' and plasticity | fully integrated hex8 "locks" in plastic flow (volumetric locking): the plastic strain comes too late; in the tensile bar the notch failed at t = 0.6 s instead of 0.2 s with `LINE_QUAD` | Choose *Hex8* = `LINE_QUAD` on the Elements page, or use quadratic elements in Mecway |
| WARNING about "Stiffness of failed element (x E)" out of range (ERROR `#ASTER-OPTIE ...: not a valid value` if it is not a number) | value via `#ASTER-OPTIE` outside 1e-7 .. 0.1 or not a number | The bridge uses the limit or the default 1e-6; adjust the value |
| Alarm `MECANONLINE4_50` (implicit dynamic, after a failure event) | Code-Aster advises against an initial stress with HHT/NEWMARK | Expected; the bridge passes the acceleration too. Check the response (force drop, ringing) for plausibility |
| WARNING `… 'Element failure' is off` | setting off | Switch the setting on |
| ERROR `#ASTER-BEZWIJKEN: material 'X' does not exist` | typo in the material name | Use the name as in Mecway (case-sensitive) |
| ERROR `'#ASTER-BEZWIJKEN …': expected 'material = strain'` | line without `=` or with a strain ≤ 0 | Write `** ASTER-BEZWIJKEN Name = 0.2` |
| `MECANONLINE9_7` (Newton does not converge) shortly after a failure event | too many elements at once, or the rest cannot carry the load | More "Substeps per time interval" (smaller steps, so fewer elements per step; dynamic: more output times in Mecway); more "Max. Newton iterations (ITER_GLOB_MAXI)"; larger "Stiffness of failed element (x E)" (1e-4 … 1e-3; the failed cross-section then carries more, 0.4 kN resp. 3.9 kN in the tensile bar, §5). The results up to the last converged step are loaded |
| `MECANONLINE9_3` (`IntegrationError`) after failure | very large deformation of soft elements (large displacements) | Smaller steps; larger "Stiffness of failed element (x E)"; if the strains are small, `DEFORMATION = PETIT` |
| Singular matrix (`FACTOR_…`, `MECANONLINE9_4`) after failure | part of the model hangs only on failed elements and is not held anywhere else | Hold that part, or drive with a prescribed displacement (tested) instead of a force. With a force and complete separation the rest cannot carry the load; that is physical failure (expected, NOT checked with a run) |

General:
- **Mesh dependence.** The limit applies per element (average over the integration
  points). A finer mesh or quadratic elements localize more strongly and fail earlier
  (see §5, `LINE_QUAD`). Calibrate the limit on a test or reference with a similar
  element size.
- **Step size.** Failure is checked after every solver step (dynamic: at every output
  time). In one large step many elements can cross the limit at once; smaller steps
  (dynamic: more output times) give a more gradual result.
- **Run time.** Every solver step is a separate `STAT_NON_LINE` call (dynamic: one
  `DYNA_NON_LINE` call per output time), with some extra time per call. The results
  form one continuous result.

## 7. Assumptions

- **Criterion**: the equivalent plastic strain, averaged over all integration points
  of an element (for shells also over the sub-points through the thickness). No damage
  evolution: an element fails at once and stays failed.
- **Failed element**: E and the slope after yielding × "Stiffness of failed element (x E)"
  (default 1e-6), yield stress unchanged, so the soft element stays elastic; stress and
  internal variables zero, except the plastic strain (isotropic). Lower bound 1e-7: with
  1e-9 the matrix became singular after failure in a test run
  (`bridge_to_aster._FAILURE_FACTOR_RANGE`).
- **When it is checked**: static after every solver step, dynamic at the output
  times. Failure therefore happens at the end of a step; the step size determines how
  accurate the moment is (§5, 20 substeps).
- **Kinematic hardening**: the current plastic strain from the back stress (§1), not
  the accumulated one.
- **Mesh dependence**: the limit is not corrected for the element size (no
  regularisation); see §6.

## 8. Sources and justification

Code-Aster behaviour (Code-Aster 17.4; catalogue = `code_aster/Behaviours/*.py` in the
installation):

- Internal variables `EPSPEQ`, `INDIPLAS` (`VMIS_ISOT_LINE`/`_TRAC`) and no `EPSPEQ` for
  `VMIS_CINE_LINE`: catalogue `vmis_*.py`.
- `VMIS_CINE_LINE`: back stress `XCINXX..XCINYZ` (catalogue `vmis_cine_line.py`);
  X = c·εp with c = 2/3·E·Et/(E−Et) = 2/3·H, checked against `EPSP_ELGA` (test run).
- `ECRO_LINE D_SIGM_EPSI` is the slope of the tensile curve in total strain (EDF R&D,
  U4.43.01); Mecway's *tangent modulus* is the plastic modulus H (measured headless with
  CCX, see [Verification.md](Verification.md), NL-01).
- `SIMO_MIEHE`: internal variables `SM1..SM6` (catalogue `simo_miehe.py`); setting
  them to zero gives a stress-free initial state (test run).
- Shells: sub-points through the thickness and `CREA_CHAMP ASSE` per sub-point: test
  runs. Beams: `<EXCEPTION>` `POUTRE0_61` (plasticity only in multifibre beams).
- Stress in `V3..V8` (`TXX..TYZ`) with `GDEF_LOG`: seen in the `.mess`
  ("Nombre total de variables internes : 8").
- `PREDICTION='ELASTIQUE'` after failure, a soft material that stays elastic, and
  zeroing `V3..V8`: chosen after test runs in which the other variants did not converge
  (see the header of `Scripts/bridge_failure.py`).
- Explicit only `PREDICTION='TANGENTE'`: `<EXCEPTION>` `MECANONLINE5_1` with 17.4.
- Implicit dynamic: alarm `MECANONLINE4_50` with an initial stress; whether passing the
  acceleration avoids the recomputation is NOT verified (the force response in the
  test run was plausible).

Literature:

- Alomar, Z., Maccioni, L. & Concli, F. (2023). Development and implementation of
  element deletion algorithm into an open-source software based on the fracture locus
  of materials. *Materials*, 16(1), 187. https://doi.org/10.3390/ma16010187
- EDF R&D (n.d.). *Code_Aster documentation, version 17.4*: U4.43.01 (`DEFI_MATERIAU`),
  U4.51.03 (`STAT_NON_LINE`), U4.53.01 (`DYNA_NON_LINE`). https://www.code-aster.org
