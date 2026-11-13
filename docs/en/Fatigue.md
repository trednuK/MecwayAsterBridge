# Fatigue: damage and life (Wöhler, rainflow, Miner, multiaxial, Manson-Coffin)

*Nederlandse versie: [Vermoeiing.md](../Vermoeiing.md)*

The bridge computes the **fatigue damage** D and the **life** at each node from a load
history, with a Wöhler curve (S-N curve) or a strain-life curve (Manson-Coffin) per
material and Miner's rule. For a multiaxial stress state a **critical-plane
criterion** (Dang Van, Matake, Crossland or your own formula) of Code-Aster can give
the equivalent stress. Mecway itself has no fatigue: the manual has no S-N curve,
fatigue or Wöhler input (Mecway Ltd., 2026; checked). The input therefore goes through
`#ASTER` lines in a free text field of Mecway
([`ASTER_lines_examples.md`](ASTER_lines_examples.md) §1).

| What | Where you see it |
|---|---|
| damage D per node (`damage`) | Mecway, field *damage* (with a time history the same value in every time step); for shells the larger of top and bottom |
| life per node (`life`): repetitions of the signal or block spectrum until D = 1 | Mecway, field *life* |
| shells: damage on the top and bottom side (`damage_top`, `damage_bottom`) | Mecway, fields *damage_top*, *damage_bottom* (§1.8) |
| multiaxial: equivalent stress of the criterion (`fatigue_eq`, Pa) and the criterion value (`fatigue_ratio`) | Mecway, fields *fatigue_eq*, *fatigue_ratio* (§1.7) |
| largest damage (node, location, material), life there, number of nodes with D ≥ 1 | log and status box after the run |
| cycles of the node with the largest damage (layer, min, max, amplitude, mean, count, N, damage) | table `<model>_<run-id>_vermoeiing.csv` in the work folder |

General operation of the bridge: [`UserGuide.md`](UserGuide.md).

## 1. Step by step

### 1.1 In Mecway: the model

1. **Solid elements** (hex, tet, wedge, pyramid) and/or **shells** (plate or shell
   elements, DKT/COQUE_3D). The damage of solids comes from the nodal stress
   `SIGM_NOEU` (or the strain `EPSI_NOEU` with a strain curve), that of shells from
   the stress on the top and bottom side (§1.8). Beams get no damage (WARNING, §4).
2. **An analysis with a load history**:
   - *Static* (S30, `lin_static_3d`): the static stress is the stress of "one unit
     load"; you give the history as **blocks** or a **signal** (§1.3);
   - *Nonlinear static* (L30, `nonlin_static_3d`) or *Dynamic response* without
     *Mode superposition* / D31 (`dyna_impl_3d`, `dyna_expl_3d`): the **time steps of
     the run** are the signal, per node. Give the loads a time table (e.g. back and
     forth), as for any nonlinear or dynamic analysis.
   Other analyses (modal, harmonic, spectrum, mode superposition, thermal): WARNING, no
   damage.
3. **Named materials**: the Wöhler curve belongs to a Mecway material (the name in the
   tree under *Materials*).

### 1.2 The Wöhler curve: `#ASTER-WOHLER`

One line per material (`*` = all materials without a line of their own):

```
#ASTER-WOHLER Steel: S = [160, 200, 280, 400] MPa, N = [2e6, 1e6, 1e5, 1e4]
#ASTER-WOHLER Alu: Sf = 900 MPa, b = -0.1, Se = 60 MPa
#ASTER-WOHLER *: S = 40 MPa, N = 2e6, m = 3
#ASTER-WOHLER CastSteel: Sf = 900 MPa, b = -0.09, ef = 0.3, c = -0.55
```

**S is the stress amplitude** σ_a = (σ_max − σ_min)/2, not the stress range Δσ; this
is how Code-Aster works (`DEFI_MATERIAU` `FATIGUE` `WOHLER`; measured with szlz100a:
the 600/−500 MPa cycle gives N(550 MPa)). A curve in Δσ (e.g. Eurocode 3 detail
categories) must therefore be divided by 2 first: Δσ_C = 80 MPa at 2·10⁶ becomes
`S = 40 MPa, N = 2e6, m = 3`.

Four forms:

| Form | Keys | N(S) |
|---|---|---|
| table | `S = [..] <unit>`, `N = [..]` (S increasing, N not increasing, at least 2 points) | interpolation between the points, log-log by default (`INTERPOL = LOG`, like `DEFI_FONCTION INTERPOL='LOG'`) or linear (`INTERPOL = LIN`) |
| power | `S`, `N`, `m` (numbers) | N = N_ref · (S_ref / S)^m |
| Basquin | `Sf`, `b` (b < 0) | S = Sf · (2N)^b, so N = ½ (S/Sf)^(1/b) |
| strain (Manson-Coffin) | `Sf`, `b`, `ef`, `c` (b, c < 0), optionally `E` | ε_a = Sf/E · (2N)^b + ef · (2N)^c, N solved per cycle (§1.9) |

Extra keys (upper or lower case):

| Key | Default | Meaning | When to change |
|---|---|---|---|
| `PROL_GAUCHE` (table) | `EXCLU` | below the first S of the table: `EXCLU` no damage (fatigue limit; Code-Aster's default, measured), `CONSTANT` N of the first point, `LINEAIRE` the first segment extended (log-log with `LOG`) | `LINEAIRE` when the curve has no fatigue limit (e.g. welds, corrosion, "elementary" Miner) |
| `PROL_DROITE` (table) | `LINEAIRE` | above the last S: the last segment extended (with a WARNING), or `CONSTANT` (N of the last point) | rather extend the table to higher stresses |
| `Se` (power, Basquin) | none | no damage below this amplitude (fatigue limit) | when the curve has a knee to infinite life |
| `correctie` (`correction`) | `GEEN` (`NONE`) | mean stress correction: `GOODMAN` S_eq = S_a / (1 − S_m/S_u), `GERBER` S_eq = S_a / (1 − (S_m/S_u)²) | when the curve was measured at R = −1 (zero mean) and the load has a mean (not with a strain curve or a multiaxial criterion: ERROR) |
| `Su` | – | tensile strength (needed with `GOODMAN`/`GERBER`) | – |
| `E` (strain curve) | E of the Mecway material | Young's modulus in Sf/E | only when the curve was measured at another E, or with `*` for materials with different E (then required) |

Stresses (`S`, `Sf`, `Se`, `Su`, `E`) need a unit: Pa, kPa, MPa, GPa, N/mm2, psi or
ksi. N, m, b, ef and c are dimensionless.

### 1.3 The load history

**(a) Blocks (linear static):** per line n cycles with an amplitude and a mean as a
**factor on the static stress**:

```
#ASTER-BLOCK 1.0, 0.0, 1e5
#ASTER-BLOCK 0.5, 0.5, 2e6
```

Here: 10⁵ fully reversed cycles (±1 × the static load) and 2·10⁶ cycles between 0 and
1 × the static load (amplitude 0.5, mean 0.5). Per node with equivalent stress σ_eq
(§1.4): S_a = |a·σ_eq|, S_m = m·σ_eq. All blocks together are one repetition of the
spectrum (with Miner the order does not matter). Also `#ASTER-BLOK`. With a multiaxial
criterion each block is a cycle between (m − a) and (m + a) × the static stress tensor
(§1.7).

**(b) Signal (linear static):** a sequence of load factors; the bridge counts the
cycles with rainflow on signal × σ_eq. Several lines are joined in order.

```
#ASTER-SIGNAL 0, 1, -0.5, 0.8, -1, 0
```

Also `#ASTER-SIGNAAL`. Intermediate points on a straight line are not needed: only the
reversals count.

**(c) The time steps of the run (nonlinear static, dynamic):** without blocks or a
signal, the stress history per node over all archived time steps is the signal (in
dynamics the output times of Mecway's *timesteps*; choose them fine enough to catch
the peaks). The initial state (t = 0) counts. `#ASTER-BLOCK`/`-SIGNAL` are ignored
there (WARNING).

### 1.4 Options: `#ASTER-FATIGUE`

```
#ASTER-FATIGUE stress = VMIS_SG, counting = RAINFLOW, repeats = 1e4
```

| Key (also NL) | Default | Choices | When to change |
|---|---|---|---|
| `stress` (`spanning`) | `VMIS_SG` | `VMIS_SG`: von Mises with the sign of the trace (as `CALC_FATIGUE CUMUL_DOMMAGE`); `PRIN`: the principal stress with the largest absolute value, with sign | `PRIN` for a (nearly) uniaxial alternating stress where von Mises follows the compression/tension phase poorly, or for cracking normal to the largest principal stress (brittle, welds) |
| `strain` (`rek`) | `PRIN` | equivalent strain with a strain curve: `PRIN` the principal strain with the largest absolute value (in a bar the axial strain, as in a strain-controlled test); `VMIS_SG`: √(2/3 e:e) of the strain deviator, with the sign of the trace | `VMIS_SG` for a clearly multiaxial strain; note: for elastic uniaxial strain it is 2/3 (1 + ν) × the axial strain (0.87 at ν = 0.3) |
| `counting` (`telling`) | `RAINFLOW` | `RAINFLOW`: the signal is repeated (starts at the largest absolute value, closed cycles only; `POST_FATIGUE COMPTAGE='RAINFLOW'`); `ASTM`: one pass according to ASTM E1049 §5.4.4, the residue counts as half cycles | `ASTM` when the signal occurs once (a single event); for repeated operation `RAINFLOW` is correct |
| `repeats` (`herhalingen`) | 1 | number of times the signal/spectrum occurs: D = repeats × D per repetition | the design life, e.g. number of trips or years × spectra per year |
| `criterion` (`criterium`) | `GEEN` (`NONE`) | `DANG_VAN`, `MATAKE`, `CROSSLAND`, `FORMULE` (§1.7) | for a multiaxial, especially non-proportional load |
| `a`, `b`, `c` | – | constants of the criterion (§1.7); `b` with a stress unit | – |
| `formula` (`formule`) | – | own equivalent stress with `criterion = FORMULE` (§1.7) | – |
| `loading` (`belasting`) | `PERIODIC` | `PERIODIC` (`PERIODIEK`) or `NON_PERIODIC` (`NIET_PERIODIEK`), only with a criterion | `NON_PERIODIC` when the history has more than one cycle (variable amplitude) |
| `projection` (`projectie`) | `UN_AXE` | `UN_AXE` or `DEUX_AXES`: projection of the shear stress on the critical plane with `NON_PERIODIC` (Code-Aster `PROJECTION`) | `DEUX_AXES` for a strongly non-proportional shear stress (measured on sslv135a: equal) |

Also `#ASTER-VERMOEIING`.

### 1.5 Running and results

Start the bridge as usual. After the run:

- **Mecway:** the fields `damage` (D) and `life` (life in repetitions until D = 1,
  capped at 10¹²; also when D = 0); for shells also `damage_top`/`damage_bottom`, with
  a criterion also `fatigue_eq`/`fatigue_ratio`. With a time history they have the
  same value in every time step (the damage of the whole history). Mecway's API reads
  them (checked headless, static and dynamic); the display in the GUI has NOT been
  checked.
- **Status box and log:** largest damage with node, location and material, the life
  there, the number of cycles per repetition, the number of nodes with D ≥ 1 (WARNING),
  with a criterion the equivalent stress and the largest criterion value, and messages
  (§5).
- **Cycle table** `<model>_<run-id>_vermoeiing.csv`: per cycle of the critical node
  `node`, `material`, `layer` (volume, top, bottom), `cycle`, `s_min`, `s_max`, `amplitude`, `mean`, `count`,
  `s_eq` (after the correction), `n_failure` and `damage` (in Pa, with a strain curve
  as strain; `inf` = below the fatigue limit). With a criterion every row is a result
  (the history, or a block) with `s_eq` = SIGEQ; `s_min`/`s_max`/`mean` are then
  `nan`.

### 1.6 Interpretation

- **Miner:** D = Σ nᵢ/Nᵢ; at D = 1 the rule predicts failure. Miner ignores the load
  sequence and is an average: in practice parts fail between D ≈ 0.3 and 3. Codes
  therefore often require D ≤ 0.5 or a safety factor on the stress or on N.
- **Life** = 1 / (D per repetition): the number of repetitions of the signal or
  spectrum. With a single block of n cycles, n × life is the number of cycles to
  failure.
- **Wöhler curve and stress:** the curve belongs to the stress the bridge uses: the
  nominal nodal stress of the mesh (`SIGM_NOEU`, averaged per node). In a notch the
  mesh already includes the stress concentration; then use a curve of smooth material
  (not a curve that already contains the notch). A fine mesh in the notch is needed:
  the damage goes with the stress to the power m (often 3 to 10), so a 5 % stress
  error gives a 15 to 60 % damage error.
- **Mean stress:** without a correction only the amplitude counts. Goodman is
  conservative for most metals, Gerber less so. Code-Aster (and therefore the bridge)
  keeps the sign of the mean: a mean **compression** lowers the equivalent amplitude
  with Goodman (measured). If you do not want that benefit, switch the correction off.
- **Multiaxial:** `VMIS_SG` and `PRIN` turn a stress tensor into one number per time
  step. That is fine for proportional loading (the principal directions stay the
  same). For non-proportional loading (e.g. bending and torsion out of phase), or when
  the mean stress must count through the critical plane: a criterion (§1.7).
- **Plasticity:** the stress route is high-cycle. With plastic strain per cycle
  (low-cycle, N < ~10⁴) the strain route (Manson-Coffin, §1.9) is better: under
  yielding the strain stays sensitive to the load, the stress does not.

### 1.7 Multiaxial: `criterion` (Dang Van, Matake, Crossland, formula)

```
#ASTER-WOHLER Steel: S = [138, 200, 295, 430] MPa, N = [1e6, 5e4, 1.2e4, 2e3]
#ASTER-FATIGUE criterion = DANG_VAN, a = 0.3, b = 110 MPa, c = 1.5
```

Code-Aster searches the **critical plane** at each node (`CALC_FATIGUE TYPE_CALCUL=
'FATIGUE_MULTI'`, `OPTION='DOMA_NOEUD'`) and gives an equivalent stress SIGEQ, which
the bridge puts as the amplitude on the Wöhler curve of the material (measured in
Code-Aster 17.4, sslv135a and VM-09):

| Criterion | Code-Aster | SIGEQ |
|---|---|---|
| `DANG_VAN` | `DANG_VAN_MODI_AC` (periodic), `DANG_VAN_MODI_AV` (non-periodic), `CISA_PLAN_CRIT` `D_VAN_A` = a, `COEF_CISA_TRAC` = c | c · (Δτ/2 + a · max(P_max, 0)): Δτ/2 the shear amplitude on the critical plane, P_max the largest hydrostatic stress |
| `MATAKE` | `MATAKE_MODI_AC`/`_AV`, `MATAKE_A` = a, `COEF_FLEX_TORS` = c | c · (Δτ/2 + a · max(N_max, 0)): N_max the largest normal stress on that plane |
| `CROSSLAND` | `FORMULE_CRITERE` with `AMPCIS` (as in szlz107a), periodic only | c · (√J₂,a + a · max(P_max, 0)): √J₂,a = √J₂ of the amplitude tensor (`AMPCIS`, measured) |
| `FORMULE` | `FORMULE_CRITERE`, `FORMULE_GRDEQ` | your own formula, e.g. `formula = '1.5*(DTAUMA + max(PHYDRM,0))'` (Code-Aster parameters: `DTAUMA`, `PHYDRM`, `NORMAX`, `NORMOY`, `AMPCIS`, `RAYSPH`, `DSIGEQ`, `EPNMAX`, ...; the bridge checks the names) |

**Choosing the constants** from the fatigue limits σ₋₁ (alternating tension-compression)
and τ₋₁ (alternating torsion) of the material (the classic calibration: pure torsion
at τ₋₁ and tension-compression at σ₋₁ then both lie exactly on the limit):

| Criterion | b | a | c |
|---|---|---|---|
| Dang Van | τ₋₁ | 3 (τ₋₁/σ₋₁ − ½) | σ₋₁/τ₋₁ |
| Matake | τ₋₁ | 2 τ₋₁/σ₋₁ − 1 | σ₋₁/τ₋₁ |
| Crossland | τ₋₁ | 3 τ₋₁/σ₋₁ − √3 (szlz107a) | σ₋₁/τ₋₁ |

With this c SIGEQ is a "tension-equivalent" amplitude: for pure alternating tension
or torsion at the limit SIGEQ = σ₋₁, so the usual (tension) Wöhler curve applies.
Code-Aster allows 1 ≤ c ≤ 1.7321 for Dang Van and Matake (catalogue
`defi_materiau.py`; outside that range ERROR). a and c are required; b is optional and
gives the field `fatigue_ratio` = SIGEQ / (c b) = (τ_a + a P)/b (with `FORMULE`:
SIGEQ / b): **> 1 means above the fatigue limit of the criterion** (finite life), ≤ 1
infinite life according to the criterion. Code-Aster's `D_VAN_B`/`MATAKE_B` do not
enter SIGEQ (measured: b = 2 and b = 100 give the same SIGEQ).

**Periodic or not** (`loading`):

- `PERIODIC` (default): the whole history (signal, time steps or one block) is **one
  cycle**: Code-Aster takes the largest shear range over all time steps
  (`METHODE='CERCLE_EXACT'`). D per repetition = Σ_blocks n / N(SIGEQ). Two identical
  periods in the history give the same damage as one (measured), hence a WARNING for
  a signal with more cycles.
- `NON_PERIODIC`: Code-Aster counts with rainflow on the critical plane and gives the
  damage (`ENDO1`, with the Wöhler function the bridge makes from the curve); two
  periods give twice the damage (measured). No `fatigue_eq`. Blocks are not possible
  here (ERROR), Crossland neither. Note: `MATAKE_MODI_AV` picks a different critical
  plane than `MATAKE_MODI_AC` (measured on sslv135a: damage 3.5·10⁻⁴ instead of
  9.1·10⁻⁵); `DANG_VAN_MODI_AV` gave the same damage as periodic for one proportional
  cycle.

**In linear static** the bridge builds a result with time steps from the static stress
and strain (`CREA_RESU`): the signal × the static state, or per block the two states
(m − a) and (m + a). **In a nonlinear/dynamic run** it copies the result with all time
steps, because `CALC_FATIGUE FATIGUE_MULTI` otherwise skips the initial state
(`NUME_ORDRE` 0; alarm `PREPOST4_27`; measured: a ramp 0 → 1 gave half the amplitude,
VM-08d).

**Interpretation:** the critical plane follows the direction of the shear stress, so a
rotating principal stress (non-proportional) also counts correctly; the term a · P_max
(or N_max) brings in the mean stress (tension unfavourable, compression does not
count, max(·, 0)). Dang Van and Crossland use the hydrostatic stress (independent of
the plane), Matake the normal stress on the plane. A mean-stress correction
(`correction`) on top is therefore not possible (ERROR).

### 1.8 Shells: top and bottom side

Plate and shell elements get damage on the **top side** (`damage_top`, the side of the
positive element normal, Code-Aster `NIVE_COUCHE='SUP'`, in Mecway the same side as
*vonmisesu1*) and the **bottom side** (`damage_bottom`, `'INF'`, *vonmisesb*).
`damage` and `life` are the larger damage of the two. The bridge takes the stress of
`POST_CHAMP EXTR_COQUE` (as for von Mises) as `SIEQ_NOEU`: `stress = VMIS_SG` uses the
component `VMIS_SG`, `PRIN` the `PRIN_i` with the largest absolute value. These are
invariants, so the local coordinate system of the shell plays no role. In bending, top
and bottom have the same range but an opposite mean: with Goodman the damage differs
(VM-10).

Not for shells: a strain curve and a multiaxial criterion (WARNING, shells skipped).
Beams: no damage.

### 1.9 Strain life: Manson-Coffin

```
#ASTER-WOHLER Steel: Sf = 900 MPa, b = -0.09, ef = 0.3, c = -0.55
#ASTER-FATIGUE strain = PRIN
```

The curve ε_a = Sf/E · (2N)^b + ef · (2N)^c (Basquin + Coffin-Manson, with E of the
material; Sf = σ'f, ef = ε'f) applies to the **total strain amplitude** ε_a = Δε/2.
The bridge reads the strain `EPSI_NOEU` per node and time step (in a nonlinear run the
plastic strain is part of the total strain), makes one equivalent strain per time step
(`strain`), counts the cycles with rainflow and solves N per cycle (bisection in
ln 2N, relative < 10⁻¹³). In linear static, blocks and a signal work on the static
strain, as with stress.

Use the strain route for low-cycle fatigue with plasticity (Mecway: *Nonlinear static*
with a plastic material and a back-and-forth load or imposed displacement).
`EPSI_NOEU` is the linear (engineering) strain from the displacement also with large
deformation, not the logarithmic one (measured with `GDEF_LOG`: 0.0060000 at u/L =
0.006, ln 1.006 = 0.005982); for strains of a few percent the difference is small.
For back-and-forth plasticity `deformation = PETIT` (setting *Deformation*) gives
exactly ε = u/L; the default (plastic solid → `GDEF_LOG`) also runs the reverse loading
of the bar of VM-11a through (13 Nov 2026, stresses within 0.1%). No mean-stress correction
(Morrow, Smith-Watson-Topper) and no `Se`: ERROR.

## 2. Overview of the keywords

| Line | Where | Example |
|---|---|---|
| `#ASTER-WOHLER material: K=V, ...` | every supported analysis (§1.1) | `#ASTER-WOHLER Steel: Sf = 900 MPa, b = -0.1, Su = 600 MPa, correction = GOODMAN` |
| `#ASTER-FATIGUE K=V, ...` (`#ASTER-VERMOEIING`) | idem | `#ASTER-FATIGUE repeats = 5`; `#ASTER-FATIGUE criterion = MATAKE, a = 0.4, c = 1.6, loading = NON_PERIODIC` |
| `#ASTER-BLOCK a, m, n` (`#ASTER-BLOK`) | linear static only | `#ASTER-BLOCK 1.5, 0.5, 1e4` |
| `#ASTER-SIGNAL f1, f2, ...` (`#ASTER-SIGNAAL`) | linear static only | `#ASTER-SIGNAL -2, 1, -3, 5, -1, 3, -4, 4, -2` |

Blocks and a signal together: ERROR (choose one). There are no settings in the main
window: the data belong to the model (like `#ASTER-LASBRON`). Examples 19, 20, 35 and
36 in [`ASTER_lines_examples.md`](ASTER_lines_examples.md).

## 3. How the bridge translates

1. `bridge_fatigue.py` reads the lines (IronPython) and puts a call of
   `aster_fatigue.compute` (or, with a criterion, `CALC_FATIGUE` +
   `aster_fatigue.compute_multi`) after `CALC_CHAMP` in the `.comm` (Python 3 with
   numpy in the Code-Aster job).
2. Uniaxial, per time step: `SIGM_NOEU` of the solid element sets (strain curve:
   `EPSI_NOEU`, an extra `CALC_CHAMP DEFORMATION`) and `SIEQ_NOEU` of
   `res_sup`/`res_inf` for shells → equivalent stress or strain per node (§1.4).
3. Per node: cycles (rainflow on the history; with blocks or a signal on factor ×
   σ_eq), then N per cycle from the curve of the material, with the correction, and
   D = repeats × Σ n/N. A node on the boundary of two materials with a curve gets the
   larger damage of the two; for shells the larger of top and bottom.
4. Multiaxial: per material its own `DEFI_MATERIAU` (`ELAS`, `FATIGUE=_F(WOHLER=)`,
   `CISA_PLAN_CRIT`) and `AFFE_MATERIAU` (only for `CALC_FATIGUE`), `CALC_CHAMP
   EPSI_NOEU` (`DOMA_NOEUD` needs `SIGM_NOEU` and `EPSI_NOEU`: without strain
   `<EXCEPTION> CALCULEL_29`, measured), the result (`CREA_RESU`, §1.7) and
   `CALC_FATIGUE TYPE_CALCUL='FATIGUE_MULTI' OPTION='DOMA_NOEUD'` per result.
   Periodic: N from max(`SIGEQ1`, `SIGEQ2`) with the bridge's curve (Code-Aster's
   `NBRUP1` is rounded to an integer, measured 10946.0 for N = 10946.1); non-periodic:
   D = Code-Aster's `ENDO1`. The Wöhler function for Code-Aster (`DEFI_FONCTION`) gets
   the log-log extension as extra points (down to N = 10¹² on the left and N = 1 on the
   right), because Code-Aster's `PROL 'LINEAIRE'` extends linearly in (S, N); below
   the table with `EXCLU` Code-Aster gives `NBRUP1` = 0 and `ENDO1` ≈ 10⁻³⁰⁸
   (measured), which the bridge reads as D = 0.
5. `damage`, `life` (and the extra fields) go along as nodal fields in the result
   export (`aster_results_export`, `node_fields`); the bridge reads the cycle table and
   the `BRIDGE_VERMOEIING_*` lines in the `.mess` after the run (log, status box).

**Why not `CALC_FATIGUE` for the uniaxial field?** Code-Aster's `CALC_FATIGUE`
`TYPE_CALCUL='CUMUL_DOMMAGE'` computes the same (rainflow on `VMIS_SG`, Wöhler, Miner)
but only on a result with time steps, per element node (`DOMA_ELNO_SIGM`), without a
mean stress correction, without blocks and with a single material (`MATER`). The
bridge computes it itself and equals Code-Aster: `CALC_FATIGUE` on the same result
gives the same damage (VM-04 and VM-06: difference < 10⁻⁶) and so does `POST_FATIGUE`
on the same signal (VM-03b, VM-05). The critical plane (multiaxial) does come from
Code-Aster.

**Measured differences with Code-Aster's fatigue routines** (Code-Aster 17.4, checked
with `POST_FATIGUE` during the build):

- `PROL_GAUCHE`/`PROL_DROITE='LINEAIRE'` extends the curve **linearly in (S, N)** in
  `POST_FATIGUE`/`CALC_FATIGUE`, also with `INTERPOL='LOG'`: N(50 MPa) = 1.8·10⁷ for a
  table starting at (100 MPa, 10⁷), and above the table even a **negative** damage
  (−8.6·10⁻⁶ at 500 MPa). The function itself (`WH(50e6)` in Python) does give log-log
  (1.57·10⁸). With `LOG` the bridge extends log-log (a straight line in the S-N
  diagram).
- Above the table with the default `PROL_DROITE='EXCLU'`, `POST_FATIGUE` stops with an
  error; the bridge extends by default, with a WARNING.
- Below the table with `EXCLU`, `POST_FATIGUE` gives zero damage (measured); so does
  the bridge.
- Multiaxial: Code-Aster searches the normal of the critical plane on a grid; with
  Matake (N_max depends linearly on the direction) that gave SIGEQ +0.06 % compared to
  the hand calculation (VM-09c), with Dang Van −2·10⁻⁶.

## 4. What is not possible

- **Beams:** no damage; WARNING.
- **Shells with a strain curve or a multiaxial criterion:** not built (WARNING, shells
  skipped); shells work uniaxially (§1.8).
- **Multiaxial per Gauss point** (`DOMA_ELGA`), **Papadopoulos** (`RAYSPH`, only via
  `criterion = FORMULE`), **Fatemi-Socie** (`FATESOCI_MODI_AV`), `VMIS_TRESCA`,
  `COEF_PREECROU`, `INST_INIT_CYCL` and constants per material (a, b, c apply to all
  materials): not built.
- **Strain based:** no mean-stress correction (Morrow, SWT), no fatigue limit, no
  Taheri and Lemaitre damage; the strain is `EPSI_NOEU` (also with large deformation
  the linear strain, measured).
- **Vibration fatigue** on a modal basis (`FATIGUE_VIBR`), random/spectral fatigue
  (`POST_FATI_ALEA`) and a harmonic analysis as the load: not built; in mode
  superposition, harmonic and spectrum analyses the bridge gives a WARNING.
- **A signal or blocks in a nonlinear/dynamic run:** there the history of the run is
  the signal.
- **Damage per element node** (`elementnodevariable`): per node only.
- **Sequence effects** (nonlinear damage accumulation, Marco-Starkey, ...): Miner
  only.
- **A filter on small cycles** (`DELTA_OSCI` of `POST_FATIGUE`): not built; with
  `PROL_GAUCHE = EXCLU` (default) cycles below the table do not count anyway.
- Result route `tabel`: the fields do not go to Mecway (INFO); the log and the cycle
  table do.

See also KNOWN_BUGS 66.

## 5. Messages and solutions

| Message | Cause | Solution |
|---|---|---|
| ERROR: #ASTER-WOHLER ...: expected 'material: K=V, ...' | colon after the material name forgotten | `#ASTER-WOHLER Steel: S = [..] MPa, N = [..]` |
| ERROR: ... material '...' does not exist in the model | typo or a different name than in Mecway | the name from the Mecway tree (*Materials*), or `*` |
| ERROR: ... needs a stress unit | `S`, `Sf`, `Se`, `Su` or `E` without a unit | e.g. `S = [200, 400] MPa` |
| ERROR: ... a table has S and N as lists of equal length | unequal lists or a single point | as many S as N values, at least 2 |
| ERROR: ... S must increase and N must not increase | points in the wrong order, or S and N swapped | S from low to high, N from high to low |
| ERROR: ... INTERPOL = LOG needs S > 0 and N > 0 | a point with S = 0 or N = 0 | `INTERPOL = LIN` or drop the point |
| ERROR: ... give a table, a power form or Basquin | missing keys | §1.2 |
| ERROR: ... Manson-Coffin needs Sf, b, ef and c | `ef` or `c` without the rest | all four, §1.9 |
| ERROR: ... Se / correction / Su is not possible with a strain curve | strain curve with a fatigue limit or correction | remove it (§1.9) |
| ERROR: ... E only applies to a strain curve | `E` with table/power/Basquin | remove `E` |
| ERROR: ... the strain curve (Manson-Coffin) needs E | `*` for materials with different E | `E = 210 GPa` in the line, or one line per material |
| ERROR: ... correction GOODMAN needs the tensile strength Su | `Su` missing | `Su = 500 MPa` |
| ERROR: #ASTER-FATIGUE ...: unknown / choose ... | unknown key or choice | §1.4 |
| ERROR: ... criterion ... needs a and c | constant missing | §1.7 (table with the calibration) |
| ERROR: ... Code-Aster allows 1 <= c <= 1.7321 for DANG_VAN/MATAKE | c outside the range of `COEF_CISA_TRAC`/`COEF_FLEX_TORS` | c = σ₋₁/τ₋₁ (usually 1.5–1.7) |
| ERROR: ... b = ...: expected a stress with unit | `b` without a unit | `b = 110 MPa` |
| ERROR: ... a, b, c only applies with a multiaxial criterion | constants without `criterion` | add `criterion = DANG_VAN`, or remove the constants |
| ERROR: ... formula '...': unknown name ... | a name Code-Aster does not know | the parameter names from the message (upper case) |
| ERROR: ... CROSSLAND is only possible periodic | `loading = NON_PERIODIC` with Crossland | `PERIODIC`, or Dang Van/Matake |
| ERROR: Fatigue: criterion = ... the strain curve ... does not fit | strain curve with a criterion | a Wöhler curve, or no criterion |
| ERROR: Fatigue: criterion = ... has its own mean-stress term | `correction` with a criterion | remove `correction` |
| ERROR: Fatigue: #ASTER-BLOCK with loading = NON_PERIODIC is not possible | blocks non-periodic | `PERIODIC`, or an `#ASTER-SIGNAL` |
| ERROR: #ASTER-BLOCK ...: expected 'amplitude, mean, count' | not three numbers, or count ≤ 0 | `#ASTER-BLOCK 1.0, 0.0, 1e5` (decimal point) |
| ERROR: Fatigue: #ASTER-BLOCK and #ASTER-SIGNAL together | both given | choose one |
| WARNING: ... a linear static analysis needs a load history | Wöhler curve without blocks or signal | add `#ASTER-BLOCK` or `#ASTER-SIGNAL` |
| WARNING: ... #ASTER-BLOCK/#ASTER-SIGNAL only apply to linear static | blocks in a nonlinear/dynamic run | normal: there the history of the run is the signal |
| WARNING: ... loading = PERIODIC counts one cycle per signal | signal with more cycles and a criterion | `loading = NON_PERIODIC` or blocks |
| WARNING: ... criterion = ... only works on solid elements | criterion on shells | no criterion for shells (§1.8) |
| WARNING: ... the strain curve ... only works on solid elements | strain curve on shells | a stress curve for the shells |
| WARNING: ... material '...' is not in solid or shell elements | curve on beams | solids and shells only (§4) |
| WARNING: Fatigue (#ASTER-WOHLER) only works for ... | other analysis | use linear static with blocks/signal or a nonlinear/dynamic run |
| WARNING: Fatigue: damage D = ... >= 1 | failure according to Miner | lower stress, fewer repetitions or another curve |
| WARNING: ... an amplitude exceeds the highest S of the Wohler table | stress outside the table | extend the table; N is now extrapolated (`PROL_DROITE`) |
| WARNING: ... the mean stress of a cycle is >= Su | static failure | check the stress or `Su`; such a cycle counts as N = 1 |
| WARNING: ... the Wohler curve gives N < 1 | far above the curve (extrapolated) | extend the table; N = 1 is used there |
| WARNING: ... the run stopped before the end time | nonlinear run did not converge | solve the convergence first ([Settings §4](Settings_contact_and_nonlinear.md#4-my-analysis-does-not-converge)) |
| WARNING: Fatigue failed in the Code-Aster job: ... | error in the job (e.g. no `SIGM_NOEU`) | see the traceback in the `.mess` |

## 6. Verification

[`Verification.md`](Verification.md) chapter Fatigue (VM), module
`tests_vermoeiing.py`: constant amplitude (table, Basquin, power form with Se) and a
two-level spectrum (with Goodman and repeats) exactly according to Miner (≤ 10⁻⁶ from
the hand calculation, tolerance 0.1 %); rainflow on the ASTM E1049 signal: the cycles
of the standard exactly and the damage ≤ 10⁻⁶; periodic rainflow equal to
`POST_FATIGUE`; szlz100a (Wöhler table, Goodman, Gerber) and szlz105a (`CALC_FATIGUE`,
Downing-Socie) in 3D within 10⁻⁶ of `VALE_REFE`; a dynamic run equal to
`CALC_FATIGUE` on the same result; `VMIS_SG` and `PRIN` under biaxial stress. S8b:
sslv135a in 3D (Matake and Dang Van, periodic and non-periodic) equal to `VALE_REFE`
(SIGEQ exact, `NBRUP1` 1.5·10⁻⁵ due to the rounding, damage ≤ 10⁻¹⁴); the initial
state counts (VM-08d); tension + shear by hand: Dang Van and Crossland ≤ 2·10⁻⁵, Matake
0.26 % (search grid of Code-Aster, tolerance 1 %), two blocks 2·10⁻⁵; shell plate in
pure bending: σ = 6m/t² and the top/bottom damage with Goodman ≤ 10⁻¹¹; Manson-Coffin
at imposed plastic strain 2·10⁻⁹ and elastic with `strain = VMIS_SG` exact.

## 7. References

- ASTM International (2017). *ASTM E1049-85 (Reapproved 2017): Standard Practices for
  Cycle Counting in Fatigue Analysis*, §5.4.4 and fig. 6 (rainflow). West
  Conshohocken: ASTM. Not consulted locally; the example and the table are well known
  and recomputed.
- Coffin, L.F. (1954). A study of the effects of cyclic thermal stresses on a ductile
  metal. *Transactions of the ASME*, 76, 931–950. Manson, S.S. (1953). *Behavior of
  materials under conditions of thermal stress* (NACA TN 2933). Not consulted; the
  form ε_a = σ'f/E (2N)^b + ε'f (2N)^c is the standard handbook form.
- Crossland, B. (1956). Effect of large hydrostatic pressures on the torsional fatigue
  strength of an alloy steel. *Proc. Int. Conf. on Fatigue of Metals*, 138–149. Dang
  Van, K. (1973/1989), Matake, T. (1977): the critical-plane criteria as Code-Aster
  implements them; NOT consulted, Code-Aster's behaviour was measured (§1.7).
- EDF R&D. *code_aster 17.4*: catalogue `lib/aster/code_aster/Cata/Commands/`
  `post_fatigue.py`, `calc_fatigue.py`, `defi_materiau.py` (`FATIGUE`,
  `CISA_PLAN_CRIT`); test cases `szlz100a`, `szlz105a`, `sslv135a`, `sslv135c`,
  `szlz107a` (`share/aster/tests`). The U documents (U4.83.01 `POST_FATIGUE`,
  U4.83.02 `CALC_FATIGUE`, R7.04.01 rainflow, R7.04.04 multiaxial criteria) are not
  available locally: NOT consulted; the behaviour was checked with runs (§1.7, §3).
- Miner, M.A. (1945). Cumulative damage in fatigue. *Journal of Applied Mechanics*,
  12, A159–A164.
- Mecway Ltd. (2026). *Mecway 33 manual* (`C:\Program Files\Mecway\manual.pdf`): no
  fatigue.
