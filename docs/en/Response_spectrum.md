# Response spectrum analysis (earthquake, shock)

*Nederlandse versie: [Spectrumanalyse.md](../Spectrumanalyse.md)*

A response spectrum gives, per natural frequency (or period), the largest
acceleration of a single-degree-of-freedom system under a ground motion, such as an
earthquake or a shock. The response spectrum analysis uses it to compute the largest
response of the structure without an analysis in time: per mode the response to the
spectrum, then a combination over the modes and the directions. Mecway has no
response spectrum analysis (Mecway Ltd., 2026, chapter 6); the bridge computes it
with Code-Aster:

| Mecway | Bridge analysis (page) | Code-Aster | Result in Mecway |
|---|---|---|---|
| *Frequency* (V30) with a *Gravity* with a table as the spectrum | `spectrum_3d` (Response spectrum) | `CALC_MODES` → `COMB_SISM_MODAL` (`MONO_APPUI`), with missing mass `MODE_STATIQUE` | one step with the maxima: displacement, absolute acceleration, stresses, von Mises, reactions |

When to use: a linear model under an earthquake spectrum from a design code or a shock
spectrum (e.g. a design spectrum for transport or an impact). For the response in
time to a known time history: [Mode_superposition.md](Mode_superposition.md). For the
natural frequencies only: [Modal_and_buckling.md](Modal_and_buckling.md).

## 1. Step-by-step procedure

### 1.1 In Mecway: the model

1. **Analysis type** *Frequency* (V30) with the **number of modes** (*Number of
   modes*). Take enough modes to carry ~90% of the mass in every direction of the
   spectrum (§3), or keep the missing mass on (default, §1.2). The log gives the
   effective mass per direction (§1.3).
2. **Material** with a **density**; point masses (*Mass*) are included.
3. **Supports** (*Fixed*, *Displacement* = 0, ...): the ground moves all supports
   together (one spectrum for all supports). An imposed displacement ≠ 0 or with a
   table is not possible (§4).
4. **The spectrum** is a **Gravity** with a **table** per direction:
   - Add a *Gravity* and give the X, Y and/or Z component a **table** (*Table*). The
     *time* column holds the **period T in s** (default; or the frequency in Hz,
     setting *Spectrum table: column 'time' is*), the value is the **spectral
     acceleration** in m/s². You can paste a table from a spreadsheet.
   - Between the points the bridge interpolates linearly (in T); outside the table the
     first or last value applies, as for every Mecway table (Mecway Ltd., 2026,
     chapter 9).
   - A component **without a table** with a value ≠ 0 is a **flat spectrum** (that
     acceleration everywhere). A component 0 has no spectrum: that direction is not
     included.
   - Every direction with a spectrum is computed separately and then combined with the
     direction combination (§1.2). The sign of a value does not matter.
   - In this analysis the gravity is **not a load**: there is no self-weight. Other
     loads (forces, pressure, ...) are not included (WARNING).
5. **Damping**: the damping ratio of the modes is a setting (default 5%, §1.2);
   *Rayleigh damping* in Mecway is added per mode. The spectrum must belong to that
   damping.

Example: elastic spectrum EN 1998-1 type 1, ground type B (S = 1.2; T_B = 0.15 s,
T_C = 0.5 s, T_D = 2.0 s; EN 1998-1, §3.2.2.2, table 3.2), 5% damping (η = 1),
a_g = 1 m/s². Table of the Y component (period in s, acceleration in m/s²):

| T [s] | 0 | 0.15 | 0.5 | 0.6 | 0.8 | 1.0 | 1.5 | 2.0 | 3.0 | 4.0 |
|---|---|---|---|---|---|---|---|---|---|---|
| S_e [m/s²] | 1.2 | 3.0 | 3.0 | 2.5 | 1.875 | 1.5 | 1.0 | 0.75 | 0.333 | 0.1875 |

Between T_C and T_D the spectrum falls with 1/T: linear interpolation between the
points lies slightly above the curve there (on the safe side); use more points for a
more accurate spectrum. Check the values for your country (national annex) and
multiply by a_g. This is an illustration, not a design spectrum.

### 1.2 In the bridge main window

1. **Active analysis**: choose **`spectrum_3d`** yourself. With *Frequency*, `auto`
   picks the modal analysis (`modal_3d`): the Mecway model does not say it is a
   spectrum.
2. **Results to Mecway** must be `liml` (General page).
3. Page **Response spectrum**:

| Setting (label) | Key | Default | When to change |
|---|---|---|---|
| Result fields to Mecway | `fields` | `displacements`, `accelerations`, `stresses`, `vonmises`, `reactions` | switch fields off for a smaller `.liml`. `velocities` and the plastic strain do not belong to this analysis (INFO) |
| Number of modes (without maxmode in Mecway) | `modal_modes` | 20 | only if the Mecway model has no *Number of modes* |
| Mode check (VERI_MODE SEUIL) | `modal_tolerance` | 1e-6 | as for modal ([Modal_and_buckling.md](Modal_and_buckling.md) §1.2) |
| Spectrum table: column 'time' is | `spectrum_abscissa` | `period` | `frequency` if your spectrum is given in Hz (the number in the *time* column is then the frequency) |
| Modal damping (fraction of critical) | `spectrum_damping` | 0.05 | the damping the spectrum belongs to (e.g. 0.02 for welded steel in some codes). With Rayleigh damping in Mecway: 0, otherwise they add up |
| Combination of modes | `modal_combination` | `CQC` | `SRSS` only if the frequencies are well separated (and the code asks for it); `ABS` as an upper bound |
| Combination of directions | `direction_combination` | `SRSS` | `100-30-30` (EN 1998-1 §4.3.3.5.2 (4)), `100-40-40` (Newmark, the Code-Aster default) or `ABS`; only with more than one spectrum direction |
| Missing mass (pseudo-modes, MODE_CORR) | `missing_mass` | on | off to count the modes only (as many codes do with ≥ 90% effective mass); then a WARNING below 90% |
| Time limit / Memory limit run_aster, MUMPS NPREC | | 1800 s, 2048 MB, 8 | large models |

The element choices on the **Elements** page also apply here (hex8 with `3D` is too
stiff in bending, KNOWN_BUGS 1).

A setting can also be set per model with `#ASTER-OPTIE` (e.g. `#ASTER-OPTIE
modal_combination = SRSS`; [ASTER_lines_examples.md](ASTER_lines_examples.md)). An
own Code-Aster spectrum per direction, for example spectra for several damping values
or in another quantity: `#ASTER-SPECTRE` (§2.2).

### 1.3 Starting and following the run

- **Log and status box** at the end: the modes with frequency and effective mass (as
  for modal), then per direction the **effective mass of the modes** (`Spectrum Y:
  effective mass of the modes 61.2%`), with missing mass the cut-off frequency and the
  spectrum there, and the **total reaction force** (*base shear*) per direction,
  correctly combined (§3).
- **study.mess** (`<model>_<run-id>.mess`): per mode the frequency, the damping and
  the spectral acceleration per direction (`BRIDGE_SPECTRUM_MODE 1 FREQ=4.39309
  XI=0.05 SA_X=6.08555`), and the table of `COMB_SISM_MODAL` itself ("VALEURS DU
  SPECTRE").
- **WARNING** if the modes carry less than 90% of the mass in a spectrum direction
  and the missing mass is off.

### 1.4 Results in Mecway

Under *Solution* there is **one step** (no time steps, no modes) with the maxima:

| Mecway variable | Meaning |
|---|---|
| `displx/y/z`, `displmag` | largest displacement relative to the ground (rotations `rotx/y/z` for beams and shells) |
| `accx/y/z`, `accmag` | largest **absolute** acceleration (ground + structure), own names of the bridge (Mecway has no acceleration field) |
| `stressxx` ... `stresszx` | largest stress component (solid elements; per node and per element node) |
| `vonmises` | von Mises per node, computed per mode and combined (§3) |
| `reactionforcex/y/z`, `reactionforcemag` | largest reaction per node |

## 2. How the bridge translates

### 2.1 Chain

1. `ASSEMBLAGE` (`RIGI_MECA`, `MASS_MECA` with the supports) and `CALC_MODES`
   `PLUS_PETITE` with `NORM_MODE='MASS_GENE'`, as in the modal analysis
   ([Modal_and_buckling.md](Modal_and_buckling.md) §2.1), without prestress. On the
   modes `CALC_CHAMP` with `REAC_NODA` and, for stresses, `SIGM_ELNO`/`SIGM_NOEU` on
   the solid elements (as in test case sdlx02a).
2. Per direction the spectrum as a `FORMULE` in `AMOR` and `FREQ` (the table, linear
   in the period or frequency, constant outside the table), or the own `DEFI_NAPPE`
   of `#ASTER-SPECTRE`.
3. Damping ratio per mode ξ_i = α/(2ω_i) + β·ω_i/2 + `spectrum_damping` (Mecway's
   Rayleigh damping, Mecway Ltd., 2026, §9.26) as `AMOR_REDUIT`. ξ_i ≥ 1 or a mode
   with f ≤ 0 stops the job with a message (§5).
4. Missing mass (default): `MODE_STATIQUE` `PSEUDO_MODE` per spectrum direction (the
   static response ψ to a unit acceleration) with the same `CALC_CHAMP`.
5. `COMB_SISM_MODAL` `TYPE_ANALYSE='MONO_APPUI'` with `OPTION` `DEPL`, `ACCE_ABSOLU`,
   `REAC_NODA`, `SIGM_ELNO`, `COMB_MODE` and `COMB_DIRECTION` from the settings, and
   with missing mass `MODE_CORR='OUI'` with `FREQ_COUP` = the highest computed
   frequency. With `100-30-30` the bridge asks for the response per direction
   (`TYPE_RESU` `VALE_DIRE`) and combines it itself.
6. `aster_spectrum.maxima`: the maxima as a result with one index (`CREA_RESU`),
   `CALC_CHAMP` `SIGM_NOEU`, von Mises (§3), and `aster_results_export` writes one step
   to the `.liml`.

### 2.2 What Code-Aster computes per mode

From the macro `comb_sism_modal_ops.py` (Code-Aster 17.4), per direction d and mode i,
with Γ_i,d the participation factor (`FACT_PARTICI_D*`), φ_i the mass-normalised shape
and S_i = S_d(ξ_i, f_i):

- displacement, stress, reaction: R_i = S_i·Γ_i,d/ω_i² · (φ_i, σ_i, r_i);
- absolute acceleration: R_i = S_i·Γ_i,d·φ_i, plus always the rest
  (1 − Σ Γ_i,d·φ_i)·S(f_c) (the structure moves with the ground for the high modes);
- modal combination: SRSS √(Σ R_i²); CQC √(Σ_i Σ_j ρ_ij R_i R_j) with the correlation
  of Der Kiureghian (1981): ρ_ij = 8√(ξ_iξ_j)(ξ_i ω_i + ξ_j ω_j)ω_iω_j·√(ω_iω_j) /
  ((ω_i² − ω_j²)² + 4ξ_iξ_jω_iω_j(ω_i² + ω_j²) + 4(ξ_i² + ξ_j²)ω_i²ω_j²); ABS Σ|R_i|;
- missing mass: R_c = (ψ_d − Σ Γ_i,d/ω_i² · φ_i)·S(f_c), added in quadrature:
  √(R_m² + R_c²), with f_c the cut-off frequency;
- directions: SRSS √(R_X² + R_Y² + R_Z²); 100-40-40 (`NEWMARK`): the largest of
  R_a + 0.4 R_b + 0.4 R_c; 100-30-30 (bridge): the largest of R_a + 0.3 R_b + 0.3 R_c.

`CORR_FREQ` is off (the spectra are pseudo-accelerations at the undamped frequency),
`NATURE` is `ACCE`. With `#ASTER-SPECTRE` you can set both differently per direction.

**Own spectrum (`#ASTER-SPECTRE`).** In Mecway's custom model definition field
([ASTER_lines_examples.md](ASTER_lines_examples.md) §2): `#ASTER` code with a
`DEFI_NAPPE` (parameter `AMOR`, functions of `FREQ`) or a `FORMULE` in `AMOR` and
`FREQ`, and `#ASTER-SPECTRE X, Y = name` for the directions; extra keywords for
`SPECTRE` after a comma (`ECHELLE=9.81`, `NATURE='DEPL'`, `CORR_FREQ='OUI'`). Such a
direction needs no gravity table; a gravity in the same direction is then ignored
(INFO). A `DEFI_FONCTION` in `FREQ` only is not possible (`COMB_SISM_MODAL` needs a
nappe or formula). Verification SP-01 (test case sdld25a).

## 3. Interpretation

- **Maxima without sign.** Every value is the largest expected (absolute) maximum at
  that place, and every component separately. The maxima do not occur at the same
  time: a displacement field of maxima is not an equilibrium state, `displmag` and
  `accmag` are an upper bound (√ of the sum of the squares of the maxima), and stress
  components must not be combined into a principal stress.
- **Do not add up the total reaction.** The sum of the reactions per node is larger
  than the real total reaction: so do not sum `reactionforce*` in Mecway. The log gives
  the **total reaction force per direction** (`Total reaction force (combined)`): per
  mode the sum over all nodes, then combined like the fields (verification SP-02 …
  SP-04, SP-07).
- **von Mises** is computed per mode (VM_i from the stresses of mode i) and combined
  with the same rule, plus the missing mass. With SRSS that is exactly the expected
  value of the quadratic form σᵀPσ (independent modes); with CQC an upper bound
  (|σ_iᵀPσ_j| ≤ VM_i·VM_j). Von Mises from the combined components (as some programs
  do) can be too low, e.g. in shear.
- **Enough modes?** Look at the effective mass per direction in the log. Many codes
  ask for ~90% (e.g. EN 1998-1 §4.3.3.3.1: modes up to 90% of the mass and all modes
  with more than 5%). With missing mass (default) the rest is included
  quasi-statically with the spectrum at the highest computed frequency; that is
  correct if the spectrum has reached its final value there (the peak ground
  acceleration, *ZPA*). If the highest frequency is still on the plateau, compute more
  modes.
- **CQC or SRSS.** For modes with close frequencies (within ~10%, or a small mass on a
  large one) SRSS gives a wrong value (too high or too low); CQC accounts for the
  correlation (SP-03: ρ = 0.17 at f₂/f₁ = 1.25 and 5% damping; displacement m2 −6.5%
  relative to SRSS, total reaction +7.9%).
- **Absolute acceleration** (`accel*`) is the acceleration of the mass itself (for
  equipment on the structure); at a supported node it is the ground acceleration at
  the cut-off frequency.
- **Hand check** (single degree of freedom, mass m, ω = √(k/m)): displacement
  S(T)/ω², reaction m·S(T), absolute acceleration S(T). Clamped beam, mode 1: tip
  displacement 1.566·S/ω₁², total reaction 0.613·m·S (Euler-Bernoulli, from the shape
  of Blevins, 1979, table 8-1; verification SP-07).

## 4. What is not possible

- A spectrum per support (`MULT_APPUI`, different ground motions) and `ENVELOPPE`:
  the ground moves the same everywhere (`MONO_APPUI`).
- Imposed displacements ≠ 0 or with a table (ERROR); loads are not included.
- Contact, gaps, tension/compression only (ERROR: linear).
- Stresses on shells and beams (only displacements and reactions; INFO), and
  velocities (pseudo-velocity).
- A spectrum that varies with damping from a gravity table (one spectrum for all
  modes); for that use `#ASTER-SPECTRE` with a `DEFI_NAPPE`. Mecway's Rayleigh damping
  makes ξ differ per mode (WARNING with a table).
- The sign of the response, and combinations with other load cases (such as
  self-weight): compute those separately and combine according to the code.
- `auto` does not pick this analysis; comparing with Mecway's own solution is not
  possible (Mecway has no response spectrum analysis; *Mecway solve first* skips the
  comparison).
- See KNOWN_BUGS 56.

## 5. Messages and solutions

| Message | Cause | Solution |
|---|---|---|
| ERROR: Response spectrum analysis without a spectrum | no gravity with a value and no `#ASTER-SPECTRE` | add a Gravity with a table (§1.1) |
| ERROR: Spectrum X: negative period/frequency in the table | table starts below 0 | check the *time* column |
| ERROR: Response spectrum analysis without supports | no supports: the ground cannot move the structure | constrain the model |
| ERROR: Imposed displacement or rotation <> 0 / with a time table | only fixed supports | set the value to 0, remove the table |
| ERROR: ... is not possible in a response spectrum analysis (linear) | contact, gap, tension/compression only | remove or suppress it |
| ERROR: Setting ... is unknown / spectrum_damping | choice or value outside the list | see §1.2 |
| ERROR: The result route 'tabel' does not work | maxima only via `liml` | *Results to Mecway* = `liml` |
| ERROR: '#ASTER-SPECTRE ...': expected 'X, Y = name' | syntax | `#ASTER-SPECTRE X = spec, ECHELLE=9.81` |
| WARNING: Response spectrum analysis: loads (...) are not included | forces, pressure, ... in the model | intended (the load is the spectrum); compute self-weight separately |
| WARNING: The Mecway model is not a Frequency analysis | other analysis type | choose *Frequency* in Mecway (Number of modes) |
| WARNING: The damping differs per mode (Rayleigh) ... | gravity table with Rayleigh damping | intended? Otherwise `#ASTER-SPECTRE` with a `DEFI_NAPPE` per damping |
| WARNING: Spectrum X: the modes carry ...% of the mass (< 90%) | too few modes, missing mass off | more modes, or *Missing mass* on |
| WARNING: Modal: elset(s) ... have no density | no mass | give the material a density |
| Code-Aster reports: Response spectrum analysis: damping ratio >= 1 | overdamped mode (often a high mode with Rayleigh β) | lower β or `spectrum_damping`, or fewer modes |
| Code-Aster reports: Response spectrum analysis: a mode with frequency <= 0 | mechanism or loose part | constrain the model fully |
| `SEISME_*` in the `.mess` | message of `COMB_SISM_MODAL` (e.g. an `#ASTER-SPECTRE` name that is not a nappe or formula) | read the text; check the `#ASTER` code |
| `ALGELINE*` and other `CALC_MODES` messages | as for modal | [Modal_and_buckling.md](Modal_and_buckling.md) §4 |

## 6. Verification

[Verification.md](Verification.md) §7, *Response spectrum (SP)*: Code-Aster test case
sdld25a rebuilt with Mecway springs and masses and the spectrum via `#ASTER-SPECTRE`:
frequencies and absolute accelerations equal to the TEST_RESU values (≤ 1e-6
relative); two masses with a table as the spectrum: SRSS, CQC, missing mass and the
total reaction equal to the hand calculation (≤ 1e-6); direction combination SRSS,
100-30-30 and 100-40-40 exact; clamped hex20 beam: tip displacement −0.02%, stress and
von Mises +0.4%, total reaction −0.1% relative to Euler-Bernoulli. Mecway reads the
result (one step under a *Frequency* analysis) through its API (checked headless);
the display in the Mecway GUI is NOT verified.

## 7. References

- Blevins, R.D. (1979). *Formulas for Natural Frequency and Mode Shape*. New York: Van
  Nostrand Reinhold, table 8-1. Not consulted locally; recomputed in the verification.
- CEN (2004). *EN 1998-1: Eurocode 8: Design of structures for earthquake resistance
  – Part 1*. §3.2.2.2 (elastic spectrum), §4.3.3.3.1 (number of modes), §4.3.3.5.2
  (combination of the directions). Not consulted locally; values from memory, check
  the code and the national annex.
- Chopra, A.K. (2012). *Dynamics of Structures* (4th ed.). Upper Saddle River:
  Prentice Hall, chapter 13. Not consulted locally; the formulas are recomputed in the
  verification (SP-02 … SP-07).
- Der Kiureghian, A. (1981). A response spectrum method for random vibration analysis
  of MDF systems. *Earthquake Engineering and Structural Dynamics*, 9, 419–435. Not
  consulted locally; the formula is the one of Code-Aster (`comb_sism_modal_ops.py`,
  `cqc_array`).
- EDF R&D (2025). *code_aster 17.4*: catalogue `comb_sism_modal.py`, macro
  `MacroCommands/comb_sism_modal_ops.py`, test cases sdld25a and sdlx02a
  (`share/aster/tests`).
- Mecway Ltd. (2026). *Mecway Finite Element Analysis, Manual, Version 33*: chapter 6
  (analysis types), chapter 9 (tables), §9.26 Rayleigh damping.
