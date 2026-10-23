# Mode superposition (Mecway Dynamic Response with Mode superposition)

*Nederlandse versie: [Respons_op_modale_basis.md](../Respons_op_modale_basis.md)*

Mecway's *Dynamic Response 3D* (analysis type D30) computes the linear response in
time to a load that changes with time. With the option *Mode superposition*, Mecway
first computes the eigenmodes and then, per mode, a simple single-degree-of-freedom
equation (Mecway Ltd., 2026, §6.4). The bridge does the same with Code-Aster:

| Mecway | Bridge analysis (page) | Code-Aster | Result in Mecway |
|---|---|---|---|
| Dynamic Response 3D, *Mode superposition* on | `dyna_modal_3d` (Mode superposition) | `CALC_MODES` → `PROJ_BASE` → `DYNA_VIBRA` `BASE_CALCUL='GENE'`, `TYPE_CALCUL='TRAN'` → `REST_GENE_PHYS` | time steps with displacement, rotation, velocity, angular velocity and stresses |
| Dynamic Response 3D, *Mode superposition* off (Newmark on the whole model) | `dyna_impl_3d` (Dynamic (implicit)) | `DYNA_NON_LINE` | see [Settings_contact_and_nonlinear.md](Settings_contact_and_nonlinear.md) |
| *Frequency 3D* or *Dynamic Response 3D*, load as a sine (Mecway cannot do this) | `harmonic_3d` (Harmonic response), choose it yourself | `CALC_MODES` → `DYNA_VIBRA` `TYPE_CALCUL='HARM'` (`GENE` or `PHYS`) | per frequency amplitude, phase, Re/Im, acceleration, stress (§7) |

When to use it: a linear model (no contact, plasticity, gaps) under a shock, an
impulse or a vibration, with many time steps. The computation per step is cheap (only
the modes); the expensive step is the modal analysis. For natural frequencies only:
[Modal_and_buckling.md](Modal_and_buckling.md).

## 1. Step by step

### 1.1 In Mecway: the model

1. **Analysis type.** *Dynamic Response 3D*. In the analysis settings, set the solver
   to *Mode superposition* and choose the **number of modes** (*Number of modes*).
   Usually the first modes are enough; a shock may need many more (Mecway Ltd., 2026,
   §6.4; see §3 for the check).
2. **Time.** *Time period* (end time) and *Time step*: Mecway and the bridge give a
   solution at t = 0 and after every time step, or every n-th step with *Generate
   solution at: Every n time steps* (in the `.liml` `keepeverynthtimestep`). The end
   time must be a multiple of the time step (§4). The bridge integrates internally
   with a smaller step (§2.4); Mecway's time step therefore only sets when you see
   results and how finely a load table is followed.
3. **Material** with a **density**: no mass, no vibration. Point masses (*Mass*,
   *Rotational inertia*) count.
4. **Supports.** The model must be fully constrained: rigid body motion is not
   possible (not in Mecway either, Mecway Ltd., 2026, §6.4). An imposed displacement
   or rotation must be 0 (§4).
5. **Loads** with a time table (*force*, *pressure*, *gravity*, ...): the load follows
   the table, linearly between the points. A load without a table acts from t = 0
   with its full value (a step load; initial displacement and velocity are 0). A
   formula in t becomes a table ([UserGuide.md](UserGuide.md) §4).
6. **Damping.** *Rayleigh damping* on the whole model (no selection): per mode the
   damping ratio ξ_i = (α/ω_i + β·ω_i)/2 (Mecway Ltd., 2026, §9.26), and ξ_i < 1 for
   every mode. α mainly damps the low modes, β the high ones. For ξ = ζ at one
   frequency ω: α = 2ζω (and β = 0), or β = 2ζ/ω (and α = 0). Dampers (*Damper*)
   cannot be used with mode superposition (Mecway Ltd., 2026, §6.4).

### 1.2 In the bridge main window

1. **Active analysis** `auto`: D30 with *Mode superposition* → `dyna_modal_3d`; D30
   without → `dyna_impl_3d` (§2.6). Or choose the analysis yourself.
2. **Results to Mecway** must be `liml` (General page).
3. Page **Mode superposition**:

| Setting (label) | Default | When to change |
|---|---|---|
| Result fields to Mecway | `displacements`, `velocities`, `stresses`, `vonmises` | switch fields off for a smaller `.liml` with many time steps (stresses cost most). `reactions` and plastic strain do not belong to this analysis (INFO) |
| Number of modes (without maxmode in Mecway) | 10 | only if the Mecway model has no *Number of modes* |
| Mode check (VERI_MODE SEUIL) | 1e-6 | as for modal ([Modal_and_buckling.md](Modal_and_buckling.md) §1.2) |
| Solver steps per period of the highest mode | 50 | lower (e.g. 20) only if the run takes too long: the period error of the highest mode then becomes 0.8%; higher is rarely needed (§2.4) |
| Extra modal damping (fraction of critical) | 0 | > 0 (e.g. 0.02) for a damping ratio on all modes, e.g. from a code, without Rayleigh; adds to Mecway's Rayleigh damping. Mecway has no such input |
| Static correction truncated modes (MACRO_ELAS_MULT) | off | on when you compute few modes and want the quasi-static contribution of the higher modes (displacements and especially stresses under a slowly varying load, §3). Off = as Mecway |
| Time limit / Memory limit run_aster, MUMPS NPREC | 1800 s, 2048 MB, 8 | large models |

The element choices on the **Elements** page apply here too (hex8 with `3D` is too
stiff in bending, KNOWN_BUGS 1; shells differ slightly from Mecway, KNOWN_BUGS 2).

### 1.3 Running and monitoring

- **Log and status box** afterwards: "Modal basis of the response (n modes)" with
  per mode the frequency and the effective mass (as for modal,
  [Modal_and_buckling.md](Modal_and_buckling.md) §1.3) and the sum over the modes.
  This shows whether the modes carry the load (§3).
- **study.mess** (`<model>_<run-id>.mess`): the damping ratio per mode
  (`BRIDGE_DEMPING mode 1: 5.6494 Hz, xi = 0.05`, verification MD-04) and the solver
  step (`BRIDGE_DYNA_MODAL rekenstap 3.53357e-05 s (283 per uitvoerinterval), 28300
  stappen`, verification MD-01).
- **Convergence window:** the messages and the diagnosis; there are no Newton
  iterations.

### 1.4 Results in Mecway

Under *Solution* are the time steps (t = 0, Mecway's time step, ...), as in Mecway's
own solution. Fields: `displx/y/z`, `displmag`, `rotx/y/z` (beams, shells),
`velx/y/z`, `velmag`, `angularvelx/y/z`, `angularvelmag` (beams, shells),
`stressxx` ... and `vonmises` (solid elements), `vonmisesu1/m/b` (shells),
`beamsixxmin/max` (beams). No accelerations and no reactions (Mecway gives no
accelerations with mode superposition either, Mecway Ltd., 2026, §6.4). A Mecway
*Table* (time against a node value) shows the history at a node.

## 2. How the bridge translates

### 2.1 Modes

`ASSEMBLAGE` (`RIGI_MECA`, `MASS_MECA` with the supports as `CHARGE`) and `CALC_MODES`
`PLUS_PETITE` with `NMAX_FREQ` = the number of modes and `NORM_MODE='MASS_GENE'`, as in
the modal analysis ([Modal_and_buckling.md](Modal_and_buckling.md) §2.1). The mode
overview (frequency, effective mass) goes to the `.mess` and the log. Unlike the modal
analysis, the loads give **no prestress** (stress stiffening): neither does Mecway
(measured headless: a tensile force of 10 kN at the tip of MD-01, which with prestress
would raise the frequency ~1.4 times, left the period unchanged; the bridge gave the
same response, 1.4e-5).

### 2.2 Loads

`DYNA_VIBRA` on a modal basis needs a vector with a time function per load:
F(t) = Σ_j V_j·f_j(t) (catalogue `dyna_vibra.py`, `EXCIT` with `VECT_ASSE_GENE` and
`FONC_MULT`). The bridge builds the loads as for the other analyses and splits them:

- a load without a time table becomes a vector with f = 1 (from t = 0);
- a load with table(s): per time function a copy of the load with that function set
  to 1 and the others to 0, with the table as `FONC_MULT` (the load is linear in the
  values; this also covers two components with their own tables);
- vectors with `CALC_VECT_ELEM` (`CHAR_MECA`) and `ASSE_VECTEUR`, projected on the
  modes with `PROJ_BASE` (`STOCKAGE='DIAG'`): generalised mass, stiffness and forces
  (syntax as Code-Aster test case forma12d).

Loads from `#ASTER-EXCIT` only count as supports or couplings (in `ASSEMBLAGE`), as
for modal; a force in them does not take part.

### 2.3 Damping

The modal damping ratio per mode, computed in the job after `CALC_MODES`:
ξ_i = α/(2ω_i) + β·ω_i/2 + ζ (Mecway's Rayleigh damping, Mecway Ltd., 2026, §9.26,
plus the setting *Extra modal damping*) as `AMOR_MODAL=_F(AMOR_REDUIT=...)` in
`DYNA_VIBRA`. If a ξ_i ≥ 1, or a frequency ≤ 0 (rigid body motion), the job stops
with a message (§5). The modal analysis with *Complex modes with damping* gives the
same ξ_i (without the extra modal damping) per mode, together with the damped
frequency ([Modal_and_buckling.md](Modal_and_buckling.md) §6; verification MC-04):
so you can check α and β with a modal analysis first.

### 2.4 Time integration

Mecway integrates the modal equations exactly: measured with Mecway 33 (headless), a
mass on a beam under a step load gave the same response with time step 0.02 s
(ω·Δt = 0.71) and 0.001 s, within 1e-4 of u_st(1 − cos ωt). The bridge uses `NEWMARK`
(average acceleration, β = 1/4, γ = 1/2) with a small constant step: n steps per
period of the highest mode in the basis (setting, default 50), rounded to a whole
number per output interval. Newmark's period error is (ω·Δt)²/12 (Hughes, 2000,
§9.3): 0.13% for the highest mode, less for the lower ones. Only the output times are
archived. With 50 steps per period a model with a high first axial mode needs many
steps (e.g. 28,300 for MD-01: axial mode 565 Hz × 1 s × 50), but a step on a modal
basis is cheap (seconds).

### 2.5 Back to the nodes, stresses, static correction

`REST_GENE_PHYS` puts `DEPL`, `VITE` (and `ACCE`, needed for the beam stresses
`SIPM_ELNO`; seen: alarm `CALCULEL3_1` without accelerations) back on the nodes;
`CALC_CHAMP` computes the stresses as in the static analysis, with `MODELE`/
`CHAM_MATER` given explicitly. With *Static correction* on: `MACRO_ELAS_MULT` gives
the static response to each load vector (`MODE_CORR`), `DYNA_VIBRA` and
`REST_GENE_PHYS` get `CORR_STAT='OUI'` with the first and second derivative of the
time function (`CALC_FONCTION DERIVE`); route of test case forma12d. Measured
(MD-06b): with 1 mode the final displacement of a damped cantilever is exactly the
static one (< 1e-6), without correction 0.97069 of it.

### 2.6 D30 without Mode superposition

Mecway then computes Newmark (average acceleration) on the whole model. `auto` picks
`dyna_impl_3d` (`DYNA_NON_LINE`); the output times come from Mecway's time step. With
*Time scheme* `NEWMARK` and *COMPORTEMENT DEFORMATION* `PETIT` (page Dynamic
(implicit)) it is the same scheme: verification MD-07 equal to Mecway to 3e-8. With
the default `HHT` (numerical damping) and `GROT_GDEP` the bridge logs a WARNING.

## 3. Interpretation

- **Modal truncation.** Only the computed modes move. A load that excites higher
  modes misses their contribution, including the static part. Measured on a
  cantilever with a point load at the tip (Euler-Bernoulli): with 1 mode the
  displacement reaches 97.07% of the static one (12/λ₁⁴, Blevins, 1979, table 8-1),
  with the 3 modes in that plane 99.86%, and Mecway gives exactly the same (MD-06a;
  Mecway applies no static correction). Stresses converge more slowly than
  displacements.
- **Enough modes?** Look at the sum of the effective mass in the load direction (log,
  §1.3). Rule of thumb: at least 90% (Aubry, 2023, sec. 3.3 and 11.3; see also
  [Modal_and_buckling.md](Modal_and_buckling.md) §1.5). If the sum stays below that
  in a loaded direction, the bridge gives a WARNING (§5, also harmonic §7.7). The
  loaded directions follow from the resultant of the load vectors (gravity as a base
  acceleration too): every direction with at least 1% of the largest component. If the
  resultant is nearly 0 (a pressure on a closed surface), every direction in which the
  load has components. The sum counts only the real modes, not the pseudo-modes of the
  *Static correction* (which does cover the quasi-static part of the missing modes,
  not their dynamics). Safer: compute again with
  more modes, or with *Static correction*; if the response hardly changes, the modes
  are enough. A load at one spot (point load, shock) needs more modes than a
  distributed load.
- **Frequencies above the highest mode** in the load are not followed: choose the
  number of modes so that the highest frequency is well above the frequencies in the
  load.
- **Mecway's time step** sets the output and how a table is sampled, not the accuracy
  of the integration (§2.4). A peak between two output times is not seen: choose the
  time step small compared to the shortest period you want to see (Mecway Ltd., 2026,
  §6.4: start from the period of the highest mode of interest). A step load gives,
  without damping, a maximum of 2 × the static displacement (DAF 2; MD-01).
- **High modes and the output step.** A mode with a period shorter than two output
  steps cannot be followed in the results (the values at the output times jump); the
  computation itself is accurate (§2.4). Seen with an axial mode of 565 Hz and an
  output step of 5 ms: the same peak as Mecway, but different values per output
  time.
- **Damping per mode** is in the `.mess`. With β only, the high modes are strongly
  damped (ξ ∝ ω), with α only the low ones.
- **Hand check** (formulas from the verification): single degree of freedom k, m:
  ω = √(k/m); step load u_max = u_st(1 + e^(−πζ/√(1−ζ²))); harmonic load F₀ sin Ωt
  steady state u = u_st / √((1 − r²)² + (2ζr)²), r = Ω/ω (Clough & Penzien, 1993,
  chapter 3).

## 4. Not possible

- Rigid body motion (free model, mechanism): ERROR or message in the job (§5); not in
  Mecway either.
- An imposed displacement or rotation ≠ 0, also with a time table (the modes have
  those degrees of freedom fixed; static modes would be needed, not built): ERROR,
  use `dyna_impl_3d`.
- Dampers, initial velocity, thermal strain (*Thermal stress*), contact, gaps,
  tension/compression only: ERROR; use `dyna_impl_3d`.
- Rayleigh damping on a selection (whole model only, also in Mecway).
- Output times that are not on a regular grid from 0 (end time not a multiple of the
  time step): ERROR.
- Accelerations and reactions to Mecway.
- The steady-state response per frequency (harmonic analysis in the frequency
  domain): not with `dyna_modal_3d`, but with the separate analysis `harmonic_3d`
  (§7). A sinusoidal load in time does work here (MD-03).

## 5. Messages and solutions

| Message | Cause | Solution |
|---|---|---|
| ERROR: Mode superposition analysis without supports | rigid body motion | constrain the model in Mecway |
| ERROR: Imposed displacement or rotation <> 0 on ... | the modes have those degrees of freedom fixed | value 0, or `dyna_impl_3d` |
| ERROR: A time-dependent imposed displacement is not possible ... | same | `dyna_impl_3d` |
| ERROR: Dampers (...) cannot be used in a mode superposition analysis | not in Mecway either | Rayleigh damping, or `dyna_impl_3d` (Mecway: Mode superposition off) |
| ERROR: An initial velocity is not translated ... | not built | `dyna_impl_3d` |
| ERROR: Thermal strain ... is not translated ... | not built | `dyna_impl_3d` |
| ERROR: The output times ... are not on a regular grid | end time not a multiple of the time step | adjust *Time period* or *Time step* |
| ERROR: ... is not possible in a mode superposition analysis (linear) | contact, gap, tension/compression only | remove or suppress it, or `dyna_impl_3d` |
| ERROR: The result route 'tabel' does not work ... | modes and time steps only via `liml` | *Results to Mecway* = `liml` |
| WARNING: The Mecway model computes Dynamic Response without Mode superposition ... | `dyna_modal_3d` chosen by hand for a D30 without mode superposition | intended? Otherwise `auto` or `dyna_impl_3d` |
| WARNING: Mecway Dynamic Response (D30) computes linearly with Newmark ... | D30 without mode superposition, `dyna_impl_3d` with HHT or large displacements | schema `NEWMARK` and deformation `PETIT` for the same scheme as Mecway (§2.6) |
| WARNING: No loads: the response is zero everywhere | no load | apply the load |
| WARNING: Modal basis: effective mass (sum over ... modes) below 90% in the loaded direction(s): ... | too few modes in the load direction (§3) | more modes (*Number of modes* in Mecway, or `modal_modes`), or direct time integration (Mecway: Mode superposition off, `dyna_impl_3d`) |
| WARNING: Modal: elset(s) ... have no density | no mass | give the material a density |
| Code-Aster reports: Mode superposition: damping ratio >= 1 (mode=..) | overdamped mode (often a high mode with β, or a low one with α) | lower α/β or *Extra modal damping*, or fewer modes; ξ per mode in the `.mess` (`BRIDGE_DEMPING`) |
| Code-Aster reports: Mode superposition: a mode with frequency <= 0 | mechanism or loose part | constrain the model fully |
| `ALGELINE3_81`, `ALGELINE5_*` and other `CALC_MODES` messages | as in the modal analysis | [Modal_and_buckling.md](Modal_and_buckling.md) §4 |

## 6. Verification

[Verification.md](Verification.md) §7 (MD-01 … MD-07): mass on a beam under a step
load and a harmonic load, with and without damping, within 0.17% of the exact
solution and within 1.4e-5 of headless Mecway; a hex20 cantilever equal to Mecway
(displacement 4e-5, velocity 1.4e-4, stress 4e-4); modal truncation and static
correction exact; D30 direct via `dyna_impl_3d` equal to Mecway. Mecway sample
DampedVibratingStrip (quad8 shells, 10 modes, Rayleigh): displacement at the table
node max. 1.9% difference over 10 s, peak −0.6%, largest von Mises +0.9%; the shell
frequencies differ 0.3–0.6% from Mecway (`COQUE_3D`, KNOWN_BUGS 2), so the phase
drifts slowly.

## 7. Harmonic response (`harmonic_3d`)

The **steady-state** response to a sinusoidal load F·cos(ωt + φ), per frequency:
amplitude, phase, stress and acceleration, as in a vibration measurement or a shaker
test. Examples: a machine with unbalance on a frame, a pump on a floor, checking that
an operating frequency is far enough from a natural frequency. Mecway has no harmonic
analysis (Mecway Ltd., 2026, chapter 6; *Dynamic Response* computes in time). The
bridge therefore computes a Mecway *Frequency* or *Dynamic Response* model in the
frequency domain with Code-Aster `DYNA_VIBRA` `TYPE_CALCUL='HARM'`:

| Bridge analysis (page) | Code-Aster | Result in Mecway |
|---|---|---|
| `harmonic_3d` (Harmonic response), basis `GENE` (default) | `CALC_MODES` → static enrichment → `PROJ_BASE` → `DYNA_VIBRA` `HARM` `BASE_CALCUL='GENE'` → `REST_GENE_PHYS` → `CALC_CHAMP` | per frequency a "mode" with amplitude, phase, Re/Im, acceleration, stress |
| same, basis `PHYS` (check, dampers) | `DYNA_VIBRA` `HARM` `BASE_CALCUL='PHYS'` on the whole model | same |

A sinusoidal load that is **switched on** (with the transient build-up) is a
transient analysis: §1 with a table (MD-03). The harmonic analysis gives only the
steady state, but for many frequencies at once.

### 7.1 Step by step in Mecway

1. **Analysis type.** *Frequency 3D* with *Number of modes*, or *Dynamic Response 3D*
   with *Mode superposition* and *Number of modes*. The number of modes is the modal
   basis: choose it so that the highest mode is well above the highest frequency of
   interest (§7.5). Mecway's own *Solve* then gives the natural frequencies: useful to
   choose the frequency range.
2. **Material with a density**; point masses (*Mass*) count.
3. **Supports.** The model must be fully constrained; an imposed displacement or
   rotation must be 0 (§7.6).
4. **Loads** (*Force*, *Pressure*, *Gravity*, *Moment*, ...): the value is the
   **amplitude** (peak value) of the sine, at phase 0. A **different phase** per load:
   put `** ASTER-FASE <selection> = <degrees>` in a free text field (e.g. *CCX >
   Custom model definition*) ([ASTER_lines_examples.md](ASTER_lines_examples.md),
   example 15). An **amplitude that changes with frequency** (e.g. an unbalance force
   m·e·ω²): give the load a table; the *time* column is then the frequency in Hz
   (linear in between, constant outside).
5. **Damping.** *Rayleigh damping* on the whole model: per mode ξ_i = α/(2ω_i) +
   β·ω_i/2, or the setting *Extra modal damping* (§7.2). Without damping the response
   at a natural frequency is infinite (WARNING). Dampers (*Damper*) only with basis
   `PHYS`. A mode with ξ ≥ 1 (overdamped) gives a WARNING, but the computation
   continues (unlike the response in time, §5).
6. **Probes** (optional): a node selection named `PROBE_...` (or `MEETPUNT_...`),
   e.g. `PROBE_Bearing`. Per probe the frequency response goes to the log and a CSV
   (§7.3).
7. Save.

### 7.2 In the bridge main window

1. **Active analysis:** choose *Harmonic response* (`harmonic_3d`) yourself; `auto`
   picks the modal analysis for V30 and the transient one for D30.
2. **Results to Mecway** must be `liml`.
3. Page **Harmonic response**:

| Setting (label) | Default | When to change |
|---|---|---|
| Result fields to Mecway | `displacements`, `accelerations`, `stresses`, `vonmises` | switch fields off for a smaller `.liml` (stresses cost most); `velocities` for ω\|U\| |
| Number of modes (without maxmode in Mecway) | 10 | only if the Mecway model has no *Number of modes* |
| Extra modal damping (fraction of critical) | 0 | > 0 (e.g. 0.02) for a damping ratio on all modes from a code or a measurement; adds to Rayleigh; basis `GENE` only |
| Static correction truncated modes | on | off only to see the modal truncation (§7.5) |
| Start frequency / End frequency [Hz] | 1 / 100 | the range of interest, e.g. 0.5–2× the operating frequency; the highest mode of the basis should be well above it |
| Number of frequencies | 100 | more for a smoother curve between the peaks; the refinement catches the peaks themselves |
| Spacing (lin / log) | lin | `log` over several decades |
| Frequency list [Hz] (0 = range above) | 0 | fixed frequencies, e.g. rotational speeds `25, 50, 100`; then exactly these frequencies, without refinement |
| Basis (GENE modal / PHYS direct) | GENE | `PHYS` to check the modal basis, with dampers, or if the load has frequencies above the modes; one solution of the whole model per frequency (more expensive) |
| Loss factor eta (hysteretic damping, 0 = none) | 0 | > 0 for structural damping of all materials (§7.4 item 4), e.g. 0.02 for a steel structure, 0.1–0.5 for rubber; per material with `#ASTER-HYST` |
| Extra frequencies per resonance (0 = none) | 5 | more (7–11) for a smooth peak; 0 = the range only |
| Time limit / Memory limit run_aster, MUMPS NPREC | 1800 s, 2048 MB, 8 | large models or many frequencies (PHYS) |

Per model with `#ASTER-OPTIE`, e.g. `** ASTER-OPTIE harm_freq_list = 25, 50` or
`** ASTER-OPTIE harm_basis = PHYS`.

**Hysteretic (structural) damping.** Mecway has no loss factor (only *Rayleigh
damping* and the *Damper* material). Give it with the setting *Loss factor eta*
(`loss_factor`, all materials) or per material in the *custom model definition* (like
`#ASTER-FASE`):

```
** ASTER-HYST Rubber = 0.3
** ASTER-HYST * = 0.02
```

`material = eta` with the Mecway name of the material (also a *Spring* material),
`*` = all materials; the line wins over the setting, the last line per material
counts. The stiffness becomes K(1 + iη); at a resonance η acts like a viscous ξ = η/2
(Aubry, 2023, §3.3.4). Unlike viscous damping, hysteretic damping does not depend on
the frequency: the phase below the resonance is −atan η, not 0.

### 7.3 Results in Mecway

Under *Solution* there is one entry per frequency (*Mode 1 ... n* with the frequency
in Hz; these are **not** eigenmodes but the response at that frequency, as in
harmonic acoustics). Fields per frequency (nodal values):

| Field | Meaning | Unit |
|---|---|---|
| `displx/y/z` | Re(U): the displacement at the moment the load (phase 0) is at its maximum; Mecway's deformed shape and animation use these | m |
| `displix/y/z` | Im(U) | m |
| `displampx/y/z` | amplitude \|U\| per direction | m |
| `displmag` | √(\|Ux\|² + \|Uy\|² + \|Uz\|²) | m |
| `displphasex/y/z` | phase arg U relative to the load with phase 0, −180…180; negative = lagging | degrees |
| `rotx/y/z`, `rotampx/y/z` | beam and shell nodes: Re and amplitude of the rotation | rad |
| `velmag`, `velampx/y/z` | ω\|U\| (field `velocities`) | m/s |
| `accelmag`, `accelampx/y/z` | ω²\|U\| (field `accelerations`) | m/s² |
| `stressxx` … `stresszx` | Re of the stress (phase 0), solid elements | Pa |
| `stressampxx` … | amplitude per component | Pa |
| `vonmises` | largest von Mises stress **over a period** (§7.4) | Pa |

The displacement in time is u(t) = Re(U·e^{iωt}) = \|U\|·cos(ωt + phase). In the
**log** and the status box: the number of frequencies, the modes in the range with
their damping, per probe the largest amplitude and its frequency, and a WARNING if the
highest frequency is above the highest mode of the basis. Per probe and frequency
|u|, |a|, Re/Im and phase per direction are in `<model>_<run-id>_meetpunten.csv`
(columns `probe, frequency_Hz, u_amp_m, a_amp_m_s2, ux_re_m, ux_im_m, ...,
ux_phase_deg, ..., nodes` in English; Dutch column names with language Dutch); a
spreadsheet turns that into a frequency response plot directly. A probe with several
nodes: per direction the mean of U with the root-mean-square \|U\| as amplitude (like
the microphones, [Acoustics.md](Acoustics.md) §5.3).

### 7.4 How the bridge translates

`bridge_harmonic.build_harmonic` (template `AsterTemplate_Harmonisch.comm`; syntax
from the Code-Aster test cases sdld313d and sdld21b):

1. Model, materials, supports and loads as in the other analyses; every load (per
   Mecway load, per table) becomes a load vector (`CALC_VECT_ELEM`, `ASSE_VECTEUR`),
   as in §2.2.
2. `ASSEMBLAGE` and `CALC_MODES` (the lowest modes, `MASS_GENE`), mode overview in
   the `.mess` and the log.
3. **Static enrichment** (setting *Static correction*, on by default): the static
   response to every load vector (`MACRO_ELAS_MULT`) is added to the modes
   (`DEFI_BASE_MODALE` `RITZ`, `ORTHO`), then the eigenproblem on that small basis
   (`CALC_MODES` `QZ`) and back (`REST_GENE_PHYS`). This is how Code-Aster's own
   `DYNA_LINE` works with `ENRI_STAT='OUI'` (its default;
   `MacroCommands/dyna_line_ops.py`). The extra vectors become "pseudo-modes" high
   above the real modes (in the `.mess`: `BRIDGE_HARM_VERRIJKING`); if the static
   shape already lies in the modes (single degree of freedom), it drops out.
4. **Damping:** per vector of the basis ξ_i = α/(2ω_i) + β·ω_i/2 + ζ as `AMOR_MODAL`
   (as §2.3; per mode in the `.mess`, `BRIDGE_DEMPING`). Basis `PHYS`: C = αM + βK
   (+ `AMOR_MECA` of the dampers) as `MATR_AMOR`; `modal_damping` does not exist
   there. If a ξ_i ≥ 1, the job prints `BRIDGE_HARM_WAARSCHUWING DEMPING` and the
   bridge gives a WARNING (also before the run if `modal_damping` ≥ 1); the steady-state
   response exists then as well, only without a resonance peak. **Loss factor** η
   (`loss_factor`, `#ASTER-HYST`): `AMOR_HYST` in `ELAS` of `DEFI_MATERIAU` and, for
   springs, in `AFFE_CARA_ELEM` `DISCRET`; with it `ASSEMBLAGE` builds the complex
   stiffness `RIGI_MECA_HYST` = K(1 + iη) (U2.06.03, Aubry, 2023, §6). Basis `PHYS`:
   `DYNA_VIBRA` with that matrix as `MATR_RIGI`. Basis `GENE`: the projection onto the
   modes with `PROJ_MATR_BASE` (`PROJ_BASE` only takes real matrices) in full storage,
   so a complex generalised stiffness, exact also when η differs per material (the modes
   then couple); the modes themselves come from the real K. For the refinement around
   the peaks ξ_i + η/2 counts (largest η). (HR-01a computed with
   ζ = 1.5: |U| within 4.4e-8 of the exact solution).
5. **Frequencies:** the range (lin/log) or the list; with the range, for every mode in
   the range with 0 < ξ < 0.5, *n* more frequencies over the half-power bandwidth 2ξf
   around the peak f·√(1−2ξ²) (`DEFI_LIST_FREQ` `RAFFINEMENT` `CRITERE='LARGEUR_3DB'`,
   `NB_POINTS` = *n*; with an odd *n* exactly on the peak).
6. `DYNA_VIBRA` `TYPE_CALCUL='HARM'` with `EXCIT` per load vector: `COEF_MULT=1` (or
   `FONC_MULT` = the table as a `DEFI_FONCTION` of `FREQ`) and `PHAS_DEG` from
   `#ASTER-FASE`. Measured: U = F·e^{iφ}/(k − mω² + iωc), so lagging is a negative
   phase (HR-01).
7. `REST_GENE_PHYS` (`DEPL`) and `CALC_CHAMP` `SIGM_NOEU` on the solid elements
   (complex). `aster_harmonic_export.py` writes one `<mode>` per frequency. The
   **von Mises over a period**: σ(t) = R·cos ωt − I·sin ωt, so σ_vm² is a quadratic
   form in cos 2ωt and sin 2ωt with maximum ½(q_RR + q_II) + √(¼(q_RR − q_II)² +
   q_RI²), computed exactly on the nodal stress.

### 7.5 Interpretation

- **Resonance.** For an isolated mode with damping ξ the peak is ≈ (static
  contribution of that mode)/(2ξ) at f_n·√(1−2ξ²), the half-power bandwidth 2ξ·f_n
  and the phase there −90°. Below the resonance the structure moves in phase with the
  load, far above it in antiphase (−180°). Small damping (ξ = 0.005: peak 100×) makes
  the peak result sensitive to the value of ξ: use a measured or code value.
- **Frequency step around resonances.** A peak is 2ξ·f_n wide; a regular step misses
  it. The refinement (*Extra frequencies per resonance*) puts points on every peak in
  the range (HR-01a: peak amplitude and frequency exact). With a frequency list or
  without damping there is no refinement: then choose frequencies around f_n yourself
  (the natural frequencies are in the log).
- **Number of modes and modal truncation.** Only the computed modes take part
  dynamically. With static enrichment (default) the quasi-static part of the higher
  modes is included, so the response below the highest mode is good (HR-02a: 6.6e-4
  from the exact solution, like the direct computation). Without enrichment a constant
  error is missing (HR-02c: 6.2e-4 × u_st), which becomes large where the response is
  small: at an **antiresonance** (with force and displacement at the same point, a
  frequency with almost no motion lies between two resonances) and above the last
  modes. Rule of thumb: highest mode ≥ 1.5–2× the highest frequency (NOT verified in a
  source); check doubts with basis `PHYS` or more modes. Above the highest mode of the
  basis the bridge gives a WARNING.
- **Phase.** Per direction relative to the load with phase 0. Two points with phase 0
  and ±180° move in antiphase. With several loads with different phases there is no
  single "shape": the deformed shape in Mecway (Re) is the moment ωt = 0.
- **Stresses.** `stressxx`… is the moment ωt = 0, `stressamp…` the amplitude per
  component (these do not occur at the same time), `vonmises` the maximum over the
  period (≥ the von Mises of `stressxx`…). On nodal-averaged stresses; with a coarse
  mesh lower than the stress in the element. Fatigue needs the amplitude per component
  or the principal stress amplitude (not as a field).
- **Damping.** α (mass) mainly damps the low, β (stiffness) the high modes; with only β,
  ξ ∝ f. Extra modal damping gives all modes the same ξ.
- **Hand check** (single degree of freedom k, m): \|U\| = u_st/√((1−r²)² + (2ξr)²),
  phase −atan2(2ξr, 1−r²), r = f/f_n, u_st = F/k (Clough & Penzien, 1993, chapter 3).
  With loss factor η: \|U\| = u_st/√((1−r²)² + η²), the peak exactly at f_n and equal
  to u_st/η, phase −90° there (Aubry, 2023, §3.3.4). For a beam or solid: (static
  contribution of the mode)/η.

### 7.6 Not possible

- **Imposed (base) motion** ≠ 0 (ERROR): the modes have those degrees of freedom
  fixed. A uniform acceleration of all supports (table, floor) is an inertia load in
  relative coordinates: a *Gravity* with the acceleration amplitude in the opposite
  direction gives the motion **relative to the supports** (theory, Clough & Penzien,
  1993; NOT verified separately).
- Frequency-dependent damping (also an η that changes with the frequency). Loss
  factor on discrete elements other than Mecway springs (*Elastic support*, dampers,
  point masses): not translated (η = 0 there).
- Stresses with a loss factor: `CALC_CHAMP` computes them from the displacement with
  the real E (NOT verified in the source code whether the η part counts); with the
  factor (1 + iη) the amplitude would be √(1 + η²) larger (0.5% at η = 0.1).
- Dampers on a modal basis (ERROR; basis `PHYS` works), `modal_damping` direct
  (ERROR).
- Prestress from the loads (Mecway's *Frequency* with loads computes prestressed
  modes; here the loads are the harmonic load).
- Thermal strain, contact, gaps, tension/compression only, plasticity (ERROR).
- Stresses in shells and beams (only displacements and rotations), reactions, element
  nodal stresses.
- Comparison with a Mecway solve: Mecway has no harmonic analysis (INFO).
- The display in the Mecway GUI (list per frequency, animation, contour) is NOT
  checked. Mecway's API does read the result (headless `mecway.exe <model> script
  <script.py>` on HR-02a: `solution.modes()` 120 frequencies, `frequency(m)` and
  `node_value` of `disply`, `displiy`, `displampy`, `displphasey`, `displmag`, `rotz`,
  `rotampz` equal to the bridge values).

### 7.7 Messages and solutions (harmonic)

| Message | Cause | Solution |
|---|---|---|
| ERROR: Harmonic analysis without supports | rigid body motion | constrain the model in Mecway |
| ERROR: Harmonic: no load ... | no force, pressure, gravity, ... | apply the harmonic load (value = amplitude) |
| ERROR: Imposed displacement or rotation <> 0 on ... | base motion not translated | value 0; a uniform base acceleration as gravity (§7.6) |
| ERROR: Harmonic: an imposed displacement with a table ... | same | remove the table or set the value to 0 |
| ERROR: Dampers (...) cannot be used in the harmonic analysis on a modal basis | non-proportional damping | basis `PHYS`, or Rayleigh damping |
| ERROR: Extra modal damping ... only exists on a modal basis | `modal_damping` > 0 with basis `PHYS` | basis `GENE` or `modal_damping` 0 |
| ERROR: Harmonic: frequency list (harm_freq_list) '...' is invalid | not numbers or < 0 | e.g. `5, 10, 20` (point as decimal separator), or `0` |
| ERROR: Harmonic: frequency range ... is invalid | start ≤ 0, end < start, count < 1 | settings on the page |
| ERROR: Harmonic: basis (harm_basis) '...' is unknown | typo in `#ASTER-OPTIE` | `GENE` or `PHYS` |
| ERROR: Harmonic: '#ASTER-FASE ...': expected 'selection = phase in degrees' | typo | e.g. `** ASTER-FASE Last2 = 180` |
| ERROR: Harmonic: #ASTER-FASE: '...' is not a selection with a load | unknown name or no load | the name of the selection of the load, exactly as in Mecway |
| ERROR: Harmonic: a load on ... has different phases | one load on several selections (e.g. merged beam loads) | give each selection its own load |
| ERROR: Thermal strain ... is not translated in the harmonic analysis | *Thermal stress* on | switch it off |
| ERROR: Loss factor (loss_factor) ... is invalid | negative or not a number | a number ≥ 0 |
| ERROR: '#ASTER-HYST ...': expected 'material = eta' ... / material '...' does not exist | typo or unknown name | e.g. `** ASTER-HYST Steel = 0.02`, the name as in Mecway (case does not matter) or `*` |
| WARNING: Loss factor of the hyperelastic material ... is ignored | `ELAS_HYPER` has no `AMOR_HYST` | no action (the harmonic analysis is linear) |
| WARNING: Harmonic: the model has no damping ... | no Rayleigh, `modal_damping`, `loss_factor` or dampers | specify damping or choose frequencies between the natural frequencies |
| WARNING: Harmonic: damping ratio >= 1 (...), overdamped ... The computation continues. | a mode with ξ ≥ 1: `modal_damping` ≥ 1, or Rayleigh α (low modes) or β (high modes) too large | check α/β and *Extra modal damping* (often a unit error); ξ per mode in the `.mess` (`BRIDGE_DEMPING`). Overdamped on purpose: no action needed |
| WARNING: Harmonic: the highest frequency (...) is above the highest mode ... | too few modes for the range | more modes (*Number of modes*), basis `PHYS`, or a lower end frequency |
| WARNING: Modal basis: effective mass (sum over ... modes) below 90% in the loaded direction(s): ... | basis `GENE` with too few modes in the load direction (§3) | more modes (*Number of modes*, or `modal_modes`), or basis `PHYS` (`harm_basis`) |
| WARNING: Harmonic: probe '...' is a face selection ... | `PROBE_` on a face or element | make a *Node selection* |
| Code-Aster reports: Mode superposition: a mode with frequency <= 0 | mechanism or loose part | constrain the model fully |

### 7.8 Verification

[Verification.md](Verification.md) §7 (HR-01 … HR-05): mass on a spring with modal
damping, Rayleigh α (GENE and PHYS) and a damper (ζ = 0.2): amplitude and phase over
the whole range within 6e-8 and 1e-5° of the exact solution (criterion 1% and 1°),
peak and peak frequency exact; cantilever beam (Euler-Bernoulli, Rayleigh α): GENE
with enrichment and PHYS within 6.6e-4 of the exact receptance over 1–200 Hz (two
resonances and an antiresonance), GENE = PHYS within 1.9e-5; without enrichment the
static part of the truncated modes 6.22e-4 = 1 − Σ12/λ_i⁴ (−0.06%); hex20 cantilever
GENE = PHYS: displacement 4e-6, von Mises 4e-5, σ_xx amplitude 2.3e-3; phase with
`#ASTER-FASE`, amplitude from a table, two loads in antiphase and the probe CSV exact.
Loss factor (HR-06): mass on a spring with η = 0.04 (GENE with `loss_factor`, PHYS with
`#ASTER-HYST`): amplitude and phase within 4.3e-8 and 7e-6°, the peak u_st/η = 0.25 m
(PHYS at f_n exact, phase −90.00°); beam with η = 0.02 (GENE and PHYS) within 2.1e-4
of the Euler-Bernoulli receptance with E(1 + iη) over 1–200 Hz, the peak at f₁ equal
to (12/λ₁⁴)·u_st/η (−0.003%).

## 8. Sources

- Aubry, J.-P. (2023). *Beginning DYNAmics with code_aster*, sec. 3.3 and 11.3: the
  cumulative effective mass of the modal basis (at least 90% in the loaded direction)
  as a check of a response on a modal basis; sec. 3.3.4, 6 and appendix sec. 2.3:
  hysteretic damping (`AMOR_HYST`, `RIGI_MECA_HYST`, η/2 as equivalent ξ).
- Code-Aster, U2.06.03 (damping in dynamic analyses) and U4.53.11 (`DYNA_VIBRA`
  harmonic); catalogues `defi_materiau.py`, `affe_cara_elem.py` (`AMOR_HYST`),
  `proj_base.py`/`proj_matr_base.py` and `MacroCommands/assemblage_ops.py`
  (`RIGI_MECA_HYST` from `RIGI_MECA`), version 17.4.
- Bishop, R.E.D. & Johnson, D.C. (1960). *The Mechanics of Vibration*. Cambridge:
  Cambridge University Press (receptances of beams). Not consulted locally; the
  receptance of the cantilever was derived and checked (static limit L³/3EI, poles at
  the natural frequencies; HR-02b within 6.6e-4).
- Blevins, R.D. (1979). *Formulas for Natural Frequency and Mode Shape*. New York: Van
  Nostrand Reinhold, table 8-1. Not consulted locally; checked in the verification.
- Clough, R.W. & Penzien, J. (1993). *Dynamics of Structures* (2nd ed.). New York:
  McGraw-Hill, chapters 3 and 4. Not consulted locally; the formulas are checked in
  the verification (MD-01 … MD-04).
- EDF R&D (2025). *code_aster 17.4, catalogues* `dyna_vibra.py`, `proj_base.py`,
  `rest_gene_phys.py`, `calc_vect_elem.py` (`lib/aster/code_aster/Cata/Commands`) and
  test case forma12d (`share/aster/tests`); for the harmonic response also
  `defi_list_freq.py`, `defi_base_modale.py`, `dyna_line.py`, the macros
  `MacroCommands/defi_list_freq_ops.py` and `dyna_line_ops.py` (static enrichment
  `ENRI_STAT`), and the test cases sdld21b (`DEFI_LIST_FREQ` `RAFFINEMENT`) and
  sdld313d (`DYNA_VIBRA` `HARM` `PHYS` and `GENE`).
- EDF R&D (2023). *Forma 12d – Calcul transitoire sur base généralisée avec
  correction statique a posteriori* (training presentation, local copy).
- Hughes, T.J.R. (2000). *The Finite Element Method: Linear Static and Dynamic Finite
  Element Analysis*. Mineola: Dover, §9.3.
- Mecway Ltd. (2026). *Mecway Finite Element Analysis, Manual, Version 33*: §6.4 Dynamic
  Response, §9.26 Rayleigh damping, §11.24 DampedVibratingStrip.
