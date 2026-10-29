# Acoustics: cavity modes, harmonic pressure field and vibroacoustics

*Nederlandse versie: [Akoestiek.md](../Akoestiek.md)*

The bridge computes Mecway's *Acoustic Resonance 3D* (analysis type A30) and
*Acoustic Resonance 2D* (A20, §3.5) with Code-Aster: the eigenmodes (resonances) of an air or fluid volume, such as the standing
waves in a pipe, a room or a car cabin, and (§5) the pressure field per frequency from
a source, with absorbing boundaries and microphones (harmonic response; Mecway itself
does not have that analysis). §6 (vibroacoustics) couples the fluid to a structure:
the coupled modes of e.g. a panel on an air cavity, a piston in a liquid column or a
tank with water (Mecway cannot do that itself either). §7 computes the same coupled
model **per frequency**: a vibrating panel radiating sound, a piston on an air column
with an absorbing end, a loudspeaker in a box (displacement of the structure and
pressure/SPL in the fluid).

| Mecway analysis | Bridge analysis (page) | What Code-Aster computes | Result in Mecway |
|---|---|---|---|
| Acoustic Resonance 3D (A30) | `acoustic_modes_3d` (Acoustics (cavity modes)) | `PHENOMENE='ACOUSTIQUE'`, matrices `RIGI_ACOU` and `MASS_ACOU` (`ASSEMBLAGE`), `CALC_MODES` | per mode the frequency (Hz) and the pressure field `pressure` |
| Acoustic Resonance 3D (A30) with *Impedance* (§3.3) | `acoustic_modes_3d` (Acoustics (cavity modes)) | the same matrices + `AMOR_ACOU` per impedance boundary; the bridge solves the quadratic eigenvalue problem in the job with scipy (`aster_acoustic_complex.py`) | per mode the frequency, the *decay rate* and the complex pressure field `pressure` + `pressurei`, like Mecway |
| Acoustic Resonance 2D (A20, §3.5), also with *Impedance* | `acoustic_modes_3d` (Acoustics (cavity modes)) | as A30 with `MODELISATION='PLAN'` (impedance edges `PLAN_ABSO`) | as A30 |
| Acoustic Resonance 3D (A30) with a source (`SOURCE_` selection, §5) | `acoustic_harm_3d` (Acoustics (harmonic)) | `PHENOMENE='ACOUSTIQUE'`, `RIGI_ACOU`, `MASS_ACOU`, `AMOR_ACOU`, `DYNA_VIBRA` `HARM` | per frequency the complex pressure (`pressure`, `pressurei`), amplitude, phase and sound pressure level; microphone response in the log and a CSV |
| Frequency 3D (V30) with a fluid part (§6) | `vibroacoustic_modes_3d` (Vibroacoustics (modes)) | `PHENOMENE='MECANIQUE'`: `3D_FLUIDE` + `FLUI_STRU` + the structure, `FORMULATION='U_P_PHI'`, `CALC_MODES` `BANDE` | per mode the frequency, the displacement of the structure (`displ`) and the pressure in the fluid (`pressure`) |
| the same model with a source (§7) | `vibroacoustic_harm_3d` (Vibroacoustics (harmonic)); choose it yourself | as above + `3D_FLUI_ABSO`, `DYNA_VIBRA` `HARM` `PHYS` with `MATR_IMPE_PHI` | per frequency the complex displacement of the structure and the complex pressure, amplitude, phase and SPL in the fluid; microphones and probes in the log and CSV files |

The problem is the Helmholtz equation ∇²p + (ω/c)²p = 0 for the acoustic pressure p
(Mecway Ltd., 2026, §6.9.1). The results appear in Mecway as with Mecway's own
solution: under *Solution* a list *Mode 1, Mode 2, ...* with the frequency. General
operation of the bridge: [`UserGuide.md`](UserGuide.md); modal analysis of
structures: [`Modal_and_buckling.md`](Modal_and_buckling.md).

## 1. Step-by-step procedure

### 1.1 In Mecway: the model

1. **Mesh only the fluid.** Mesh the air or fluid volume, not the walls around it.
   Solid elements: hex8, hex20, wedge6, wedge15, tet4, tet10 (A20: plane elements
   tri3, tri6, quad4, quad8 in the XY plane, §3.5). Pyramids, shells and
   beams are not possible (Code-Aster has no acoustic element for them; ERROR, §4). An
   opening into a large space (like the organ pipe of Mecway's tutorial 17.13) is
   meshed together with a part of that space.
2. **Analysis type.** Choose *Acoustic Resonance 3D* and set *Number of modes*.
   For a cross-section: *Acoustic Resonance 2D* (A20, §3.5).
3. **Material.** *Isotropic* with *Speed of sound* (e.g. 340 m/s for air at 15 °C,
   ~1480 m/s for water). A density is not needed: the modes do not depend on it.
   Mecway computes acoustics with one material; the bridge can also handle several
   media (e.g. two gases with a different speed of sound), but only with **the same
   density** (§3.2).
4. **Boundaries.**
   - A face without a condition is a **hard wall** (∂p/∂n = 0, Mecway Ltd., 2026,
     §6.9.1). Without any other condition, mode 1 is the constant pressure at 0 Hz.
   - **Fluid pressure = 0** (on nodes or faces) creates a **pressure node**: a place
     where the pressure stays zero, e.g. the open end of a pipe (Mecway Ltd., 2026,
     §9.34). A value other than 0 is not possible (Mecway refuses it too).
   - **Impedance** (absorbing boundary, on faces) with *specific impedance* Z = R + iX
     in Pa·s/m (a number without unit; Mecway Ltd., 2026, §9.35): the modes become
     **complex**, with a frequency and a *decay rate*, as in Mecway (§3.3). The
     material then needs a **density** (the boundary term is ρ/Z).
5. **Other loads** (forces, supports, temperatures, ...) play no role in an acoustic
   analysis (INFO in the log). Contact (also *bonded*), *node-surface coupling* and
   *constraint equations* are not translated in acoustics: they are reported (ERROR,
   list at the end of the run) and left out. Mesh the volume as one continuous mesh.

### 1.2 In the bridge's main window

1. **Active analysis:** `auto` chooses `acoustic_modes_3d` for A30 and A20; or choose
   it yourself.
2. **Results to Mecway** must be `liml` (General page).
3. Page **Acoustics (cavity modes)** (change only when needed):

| Setting (label) | Default | When to change |
|---|---|---|
| Number of modes (without maxmode in Mecway) | 10 | only if the Mecway model has no *Number of modes* |
| Search frequency [Hz] (0 = lowest modes) | 0 | > 0: the modes closest to this frequency (`OPTION='CENTRE'`), e.g. around a hum or the blade-pass frequency of a fan. With 0 and hard walls without a pressure node the bridge picks a small negative search frequency itself (§2) |
| Mode check (VERI_MODE SEUIL) | 1e-6 | larger (e.g. 1e-4) if the log reports `ALGELINE5_15` |
| Time limit / Memory limit run_aster, MUMPS NPREC | 900 s, 2048 MB, 8 | large models |

The element choices on the **Elements** page (hex8 `3D`/`3D_SI`/`LINE_QUAD`) do not
apply here: the pressure is a scalar field and hex8 does not suffer from the excessive
bending stiffness of structures (KNOWN_BUGS 1); the bridge always uses the mesh elements
as they are.

### 1.3 Starting and following

Click *Start*. After the run the log and the status box list the frequency per mode
(`Mode 2: 170 Hz`; with impedance also the decay rate, reverberation time T60 and Q,
§3.3). With hard walls and no pressure node, mode 1 is the constant pressure at ~0 Hz
(INFO, not an error). With *Mecway solve first as a check*, the log compares the
frequency per mode from Mecway and Code-Aster (only with one material: with two Mecway
does not solve the model itself; with impedance against the Mecway mode with the
nearest frequency, because Mecway drops 0 Hz modes at random).

### 1.4 Viewing the results in Mecway

- Under *Solution* you find *Mode 1 ... Mode n* with the frequency. Click a mode and
  choose the field **pressure** (Mecway's own name): red and blue are pressure
  antinodes of opposite sign, the zero line is a pressure node.
- **The scale of the pressure field has no physical meaning** (Mecway Ltd., 2026,
  §6.9.1). The bridge normalises like Mecway (pᵀMp = 1 with M = ∫NᵀN/c² dV; e.g. the
  constant mode of a volume V has p = c/√V), so the numbers equal Mecway's
  (verification AK-01…04: difference < 1e-9). The sign is arbitrary.
- With impedance each mode also has a *decay rate*, and there are two fields:
  **pressure** (real part of P) and **pressurei** (imaginary part), as in Mecway's own
  solution (§3.3).
- The results are also kept separately (`<model>_<run-id>_results.xml`) and can be
  reloaded with *Results...* ([User guide §5.1](UserGuide.md#51-loading-results-again-later-small-liml)).

### 1.5 Interpretation and checks

- **Hand calculation** (plane waves in a pipe of length L, speed of sound c):
  - closed-closed (hard ends): f_n = n·c/(2L), n = 0, 1, 2, ... (n = 0 is the constant
    pressure);
  - open-closed (p = 0 at one end): f_n = (2n − 1)·c/(4L);
  - open-open: f_n = n·c/(2L), n = 1, 2, ...;
  - rectangular room with hard walls: f_lmn = c/2·√((l/Lx)² + (m/Ly)² + (n/Lz)²).
  A pipe behaves like this up to the first cross mode, f ≈ c/(2·width).
- **Open end:** p = 0 exactly at the end is an idealisation. A real open pipe radiates
  and is acoustically somewhat longer (end correction; Mecway's organ pipe tutorial,
  §17.13, adds the pipe width). To include it, mesh a part of the surroundings instead
  of imposing p = 0.
- **Mesh fineness:** the error grows with frequency. Measured
  ([`Verification.md`](Verification.md) §7, acoustics AK):
  - hex8: Δf/f ≈ (kh)²/24 with k = 2π/λ and h the element length (AK-03: 25 elements
    per wavelength gave +0.26%); 0.5% needs ~18 elements per wavelength;
  - hex20: much more accurate; 9 elements per wavelength gave +0.017% (AK-02, mode 5).
  When in doubt, compute a second time with a finer mesh.
- **Two media:** at the interface the pressure and ∂p/∂n are continuous (as with equal
  density); verification AK-05.

## 2. How the bridge translates

`bridge_acoustic.py` writes the `.comm` (template `AsterTemplate_Akoestiek.comm`);
syntax as in the Code-Aster test cases ahlv100a and adlv101f:

1. `AFFE_MODELE` with `PHENOMENE='ACOUSTIQUE'`, `MODELISATION='3D'` on the solids
   (A20: `'PLAN'` on the plane elements, §3.5).
2. `DEFI_MATERIAU(FLUIDE=_F(RHO=ρ, CELE_R=c))` per material (without density ρ = 1
   kg/m³: `RHO` is mandatory in Code-Aster but plays no role in the modes, §3.2).
3. Pressure nodes: `AFFE_CHAR_ACOU(PRES_IMPO=_F(GROUP_NO=... or GROUP_MA=..., PRES=0j))`.
4. `ASSEMBLAGE` with `RIGI_ACOU` and `MASS_ACOU` (complex matrices) and their real
   parts with `COMB_MATR_ASSE(PARTIE='REEL')`.
5. `CALC_MODES` with `OPTION='PLUS_PETITE'` (`NMAX_FREQ` = the number of modes), or
   `OPTION='CENTRE'` around the search frequency. Hard walls without a pressure node
   make the stiffness singular (the constant pressure): `PLUS_PETITE` then stops with
   `ALGELINE3_81`. The bridge then searches around −0.1·c_min/(2D), D being the
   diagonal of the bounding box of the volume (well below the first mode with a
   pressure variation); this is logged as INFO. `VERI_MODE` with `STOP_ERREUR='NON'`
   (as for modal).
6. `aster_results_export.py` writes per mode `<mode id="k" frequency="f Hz">` with the
   node variable `pressure`. `NORM_MODE` does not work for acoustic modes in
   Code-Aster 17.4 (the shape stayed at max |p| = 1); the bridge scales by
   1/√`MASS_GENE` itself (pᵀMp = 1, like Mecway).

With impedance (complex modes) steps 3–6 differ: see §3.3.

## 3. Particulars

### 3.1 Mode at 0 Hz

With hard walls and no pressure node, mode 1 is the constant pressure (a uniform
pressure rise in the whole volume, frequency 0). Mecway gives it too (|f| of order
1e-4…4e-3 Hz, numerically zero; the bridge ~1e-5 Hz). Count it in the number of modes.
It comes with the alarm `ALGELINE3_82` in the `.mess`: harmless (§4).

### 3.2 Density and several media

Code-Aster's `RIGI_ACOU` and `MASS_ACOU` do not contain the density (measured: ρ = 1.2
and ρ = 1 give the same frequencies and shapes; NOT checked in the source code). Mecway
computes without it as well (K = ∫∇Nᵀ∇N dV, Mecway Ltd., 2026, §6.9.1). For one medium
this makes no difference. At an interface between two media ∂p/∂n is therefore
continuous, which is only correct for **equal density** (physically (1/ρ)·∂p/∂n is
continuous): a pipe of two media with ρ = 1.2 and 12 kg/m³ gave 248.98 Hz where
306.47 Hz is correct. The bridge therefore stops with an ERROR if the materials have
different densities. Two media with different speeds of sound and equal density, or
both without a density, are computed (AK-05, ≤ 0.03%); Mecway itself gives no solution
with two materials. If one medium has a density and the other does not, the bridge
continues with a **WARNING**: the interface is then treated as if the densities are
equal, which is only correct if the medium without a density really has the same
density. Code-Aster gets ρ = 1 kg/m³ for that medium; that only matters for a velocity
source or impedance on that medium, and those require a density themselves (ERROR). So
fill in the density for every medium.

### 3.3 Impedance: complex modes

An *Impedance* boundary (Mecway Ltd., 2026, §9.35) is an absorber, or a boundary with
its own "spring" or "mass": Z = p/vₙ is the ratio of the pressure to the outward normal
velocity, the *specific acoustic impedance* in Pa·s/m. In Mecway *specific impedance
(real)* R and *(imaginary)* X, so Z = R + iX. Mecway then solves the **quadratic
eigenvalue problem** (Mecway Ltd., 2026, §6.9.2)

  (K + λC + λ²M)·P = 0,  K = ∫∇N·∇Nᵀ dV,  M = ∫NNᵀ/c² dV,  C = ∫(ρ/Z)·NNᵀ dA,

with λ = iω − σ and the pressure in time p(t) = Re(P·e^{λt}): every mode has a
**frequency** f = ω/2π and a **decay rate** σ (amplitude ∝ e^{−σt}). The bridge solves
exactly the same problem (verification AI: equal to Mecway to 1e-8).

**Procedure:** as in §1, with an *Impedance* on the absorbing faces. Give the material
a **density** (air 1.2 kg/m³): C contains ρ. Mecway itself computes without a density
with ρ = 0 (seen headless: the impedance then has no effect, a hard wall); the bridge
stops with an ERROR. Several impedance boundaries, each with its own Z, are possible
(AI-10); two impedances on the same faces add up (ρ/Z₁ + ρ/Z₂).

**Which value for Z** (ρc = 408 Pa·s/m for air at 15 °C, ≈ 1.48·10⁶ for water):

| Z | Meaning | Reflection factor (normal incidence) R = (Z − ρc)/(Z + ρc) |
|---|---|---|
| Z → ∞ | hard wall (as without impedance) | 1 |
| real, Z > ρc | partially absorbing wall | 0 < R < 1 |
| Z = ρc | fully absorbing for a normally incident plane wave ("infinitely long pipe"): no resonances | 0 |
| real, Z < ρc | "soft" boundary, towards an open end (p = 0) | −1 < R < 0 |
| Z = iX, X > 0 | mass-like boundary (with e^{iωt} a mass is Z = iωm), no damping; the frequencies go **up** compared with the hard wall (like a heavy free piston: the 0 Hz mode becomes a mass-spring oscillation) | \|R\| = 1 |
| Z = iX, X < 0 | spring-like boundary (Z = k/(iω)), no damping | \|R\| = 1 |
| Re Z < 0 | the boundary adds energy: modes grow (negative decay rate; WARNING) | \|R\| > 1 |

In reality Z depends on the frequency; Mecway and the bridge use one fixed Z per
boundary. Mecway's tip (§9.35): one configuration per Z, and per mode pick the
configuration whose Z belongs to that frequency.

**Results:** per mode `<mode frequency="f Hz" decayrate="σ 1/s">` with the fields
`pressure` = Re P and `pressurei` = Im P (Mecway's names and format). The log and the
status box list per mode f, σ, the **reverberation time T60 = 3·ln(10)/σ = 6.91/σ**
(the time in which the mode decays by 60 dB) and the **quality factor Q = |λ|/(2σ)**
(≈ π·f/σ; the half-power bandwidth of the resonance peak in a harmonic analysis is
Δf ≈ f/Q ≈ σ/π). The `.mess` also has ζ = σ/|λ| (line `BRIDGE_MODE ... ZETA`). A mode
with f = 0 and σ > 0 is **non-oscillating**: the pressure decays without oscillating
(for a pipe with Z > ρc the "n = 0" mode with σ = (c/L)·artanh(ρc/Z)). Mecway's API
reads the bridge's modes (headless script: `solution.modes()`, `frequency(m)`,
`node_value('pressure' / 'pressurei', .., mode=m)`); the display in the Mecway GUI has
not been checked yet (KNOWN_BUGS 55).

**Hand calculation** (pipe of length L, hard wall at x = 0, Z at x = L, plane waves;
[`Verification.md`](Verification.md) §7 AI): tanh(λL/c) = −ρc/Z, so
λₙ = (c/L)·(−artanh(ρc/Z) + iπn):
- real Z > ρc: fₙ = n·c/(2L) (as the hard wall) and for all modes
  σ = (c/L)·artanh(ρc/Z); e.g. Z = 2000 Pa·s/m, L = 1 m: σ = 70.35 1/s, T60 = 0.098 s;
- real Z < ρc: fₙ = (2n − 1)·c/(4L) (as an open end) and σ = (c/L)·artanh(Z/(ρc));
- complex Z: f shifts (X > 0 up, X < 0 down) and σ = (c/L)·Re(artanh(ρc/Z));
- with a pressure node at x = 0 instead of the hard wall: tanh(λL/c) = −Z/(ρc).
- The decay rate is more sensitive to the mesh than the frequency: hex8 with 20
  elements per metre gave at 340 Hz f +0.41% but σ +1.7% (AI-09); hex20 with 20 per
  metre ≤ 0.1% up to 850 Hz (AI-01). When in doubt, compute again with a finer mesh.

**Which modes:** like Mecway (checked headless): the 2 × *Number of modes* eigenvalues
with the smallest |λ| = |iω − σ|, and of those the ones with f ≥ 0, in ascending
frequency. The count is therefore not always exactly *Number of modes* (a room with
maxmode 8 gave 10 modes in Mecway and in the bridge). Strongly damped modes (large σ)
may be missing if you request too few modes (Mecway Ltd., 2026, §6.9.2). Mecway drops
or duplicates 0 Hz modes (the constant pressure without a pressure node,
non-oscillating modes) at random because of round-off; the bridge always gives them
once, with f = 0. An eigenvalue with a negative frequency is dropped (it belongs to the
conjugate impedance conj(Z)). With a **search frequency** > 0 (page Acoustics (cavity
modes)) the bridge gives the *Number of modes* modes with f ≥ 0 whose λ lies closest to
i·2π·f; a negative search frequency does not apply here (WARNING).

**Scale of P:** Mecway scales arbitrarily (measured: Euclidean norm 1 with an arbitrary
phase). The bridge normalises like the real modes: the phase such that PᵀMP is real,
then PᴴMP = 1 and the largest component of Re P positive. For Z → ∞ this is exactly the
real cavity mode (AI-03). Only ratios and phase differences between nodes have a
meaning (AI: P(L)/P(0) equal to Mecway to 1e-7 and to cosh(λL/c)).

**How the bridge translates** (`bridge_acoustic._complex_modes_comm`,
`aster_acoustic_complex.py`). Code-Aster's `CALC_MODES` cannot handle this problem
(`MATR_AMOR` only for displacement or generalised matrices, catalogue `calc_modes.py`;
`AFFE_CHAR_ACOU` has no impedance; a complex Z gives a complex C). Therefore:
1. `AFFE_MODELE`: the solids `3D` and the impedance faces `3D_ABSO`.
2. `ASSEMBLAGE` of `RIGI_ACOU` and `MASS_ACOU` without loads.
3. Per impedance boundary `CALC_MATR_ELEM(OPTION='AMOR_ACOU')` with its own
   `CHAM_MATER`: `CELE_R = 1` on that boundary (the `3D_ABSO` matrix is (1/c)·∫NNᵀdA,
   measured), so A = ∫NNᵀdA; `ASSE_MATRICE` with the same numbering.
4. In the job (Python 3 with numpy and scipy from the Code-Aster installation):
   C = Σ(ρ/Z)·A, the pressure nodes (*fluid pressure* 0) removed, linearisation (2n
   degrees of freedom), shift-invert with ARPACK (`scipy.sparse.linalg.eigs`,
   factorisation `splu`); small models dense (`scipy.linalg.eig`). Per mode the residual
   ‖Q(λ)P‖/((‖K‖ + |λ|‖C‖ + |λ|²‖M‖)·‖P‖); above *Mode check* a WARNING.
5. The job writes the modes directly in Mecway's format. There is no Code-Aster result:
   `med_export` and `#ASTER-POST` on `res` do not work here.
Computing time (measured): a room of 13,000 nodes (hex20) with 20 modes 14 s.

### 3.4 What is not possible

- A **frequency-dependent** impedance (Mecway cannot either, §9.35) and a complex
  impedance in the **harmonic** analysis (§5.6).
- Mecway's *acoustic displacement* as a result field, media with different density
  (§3.2), contact and couplings in acoustics, pyramid elements.
- In 2D (A20): the harmonic pressure field (§5), nodes with Z ≠ 0, beams or solids in
  the model (§3.5). Axisymmetric acoustics: Mecway has no such analysis type.
- Coupling with a structure: the coupled modes are in §6 (vibroacoustics). The
  pressure field at an excitation frequency (harmonic) is in §5.

### 3.5 Acoustic Resonance 2D (A20)

Mecway's *Acoustic Resonance 2D* computes the modes of a cross-section (e.g. the organ
pipe of Mecway's tutorial 17.13). The bridge translates it like A30, with plane
elements:

1. **Mesh** the air or fluid area with tri3, tri6, quad4 or quad8 in the XY plane, all
   nodes with Z = 0 (Code-Aster needs Z = 0 for a 2D mesh; Mecway ignores Z, the bridge
   stops). Beams, shells in another plane or solids in the model: ERROR.
2. **Material:** *Isotropic* with *Speed of sound* (and a density for an impedance), as
   for A30. A *Shell/membrane* thickness is not needed and does not count: measured in
   Mecway 34, 10 mm or no thickness gives the same frequencies and the same pressure
   field. The model is per unit thickness: the constant mode has p = c/√A (A = area).
3. **Boundaries** on edges (face selection of the edges) or nodes: an edge without a
   condition is a hard wall, *Fluid pressure* = 0 a pressure node, *Impedance* gives
   complex modes (§3.3), all as in 3D.
4. **Bridge:** `auto` (or `acoustic_modes_3d`), results route `liml`. Code-Aster:
   `PHENOMENE='ACOUSTIQUE'`, `MODELISATION='PLAN'` (impedance edges `PLAN_ABSO`, Code-Aster
   test case ahlv100f); the rest is the A30 route. The 2D analysis has no harmonic
   pressure field (`acoustic_harm_3d`: ERROR, and `auto` keeps the cavity modes with a
   `SOURCE_` selection), because Mecway has no 2D input for it: its analysis types are
   only *Acoustic Resonance 2D/3D*, its manual describes only real and complex modes (no
   frequency, no source; Mecway Ltd., 2026, §6.9, §9.34, §9.35), and an A20 model with a
   *Fluid pressure* of 1 Pa gives no solution in Mecway 34 (checked headless, 29 Oct
   2026). For a harmonic pressure field, model the cross-section as a thin 3D slab (A30)
   and use §5.

Results: equal to Mecway's own A20 solution (headless, verification AK-10 … AK-15):
quad4 and quad8 to 1e-6 relative (frequencies, decay rates and the normalised
pressure), rectangle 1.0 × 0.7 m with the analytical f_mn = c/2·√((m/a)² + (n/b)²)
within 0.05% (quad8 10 × 7). **Triangles** differ slightly: Code-Aster integrates the
mass of its plane acoustic elements with fewer points than Mecway (tri3 one point,
tri6 three), so the bridge is higher: tri6 ≤ 0.003% in frequency (0.02% in the
pressure), tri3 0.07% (mode 2) to 0.6% (mode 8) on a mesh of 20 × 14 × 2 (KNOWN_BUGS
130). Mesh with quads (or tri6) where possible. Mecway's organ pipe (497 elements, of which 48
tri3, 20 modes): the fundamental of the pipe, mode 4, 64.594 Hz (Mecway 64.592 Hz).

## 4. Messages and solutions

| Message | Cause | Solution |
|---|---|---|
| ERROR: Acoustics: material ... has no speed of sound | *Speed of sound* missing | fill in *Speed of sound* for the material (*Isotropic*) |
| ERROR: Acoustics: only solid elements (hex, wedge, tet; no pyramids, shells or beams) | the model contains pyramids, shells, beams or an elset without material | mesh only the fluid with hex/wedge/tet; give every elset a material |
| ERROR: Acoustics: the media have different densities | two materials with a different density (§3.2) | equal density (or none) if the difference is small, or compute the media separately |
| WARNING: Acoustics: medium '...' has no density, medium '...' has (...) | one medium with and one without *Density*; the interface is then computed as equal density (§3.2) | fill in the density for every medium; if it is equal, the result is correct |
| ERROR: Acoustics: fluid pressure on '...' is ...; only 0 is possible | *Fluid pressure* ≠ 0 for the cavity modes | set the value to 0 (pressure node), or compute harmonically (§5: it is then an imposed pressure) |
| ERROR: Acoustics: fluid pressure on '...': choose a node or face selection | *Fluid pressure* on an element selection | choose nodes or faces |
| ERROR: Acoustics: impedance on '...': material '...' has no density | impedance without a density (C = ρ/Z, §3.3) | fill in a density for the material (air 1.2 kg/m³) |
| ERROR: Acoustics: impedance on '...' is 0 | *specific impedance* R = X = 0 | an open end is *fluid pressure* = 0 (pressure node) |
| ERROR: Acoustics: impedance on '...': choose a face selection | impedance on nodes or elements | make a *Face selection* |
| ERROR: Acoustics: impedance on '...': Re Z and Im Z must be numbers | text or a unit in the field | only the number (Pa·s/m), without unit |
| ERROR: Acoustics: impedance '...' borders 2 media | the selection borders two materials | a separate selection per medium |
| WARNING: Acoustics: impedance on '...' has Re Z < 0 | negative resistance: the boundary adds energy | check the sign; Re Z ≥ 0 for an ordinary absorber |
| WARNING: Complex modes: residual ... > ... (Mode check) | a mode was solved inaccurately (e.g. nearly multiple or very strongly damped) | refine the mesh, request fewer modes, or relax *Mode check* |
| WARNING: Acoustics: no MED export for complex modes | `med_export` on | normal: the modes are in Mecway |
| WARNING: Acoustics: #ASTER-EXCIT ... is not used for complex modes | own loads in a model with impedance | normal; pressure nodes via *fluid pressure* = 0 |
| `aster_acoustic_complex: ERROR: ...` in the `.mess`, no results | e.g. ARPACK does not converge, or Q(σ) is singular | another search frequency or fewer modes; if it persists: report it (KNOWN_BUGS) |
| ERROR: Mecway analysis type A20 (Acoustic Resonance 2D) is only translated to the cavity modes 'acoustic_modes_3d' | another analysis chosen (e.g. the harmonic); Mecway has no 2D harmonic acoustic input (§3.5) | choose `auto` or `acoustic_modes_3d`; harmonic: a 3D model (A30) |
| ERROR: Elset '…' contains …; in Acoustic Resonance 2D (A20) the bridge only translates plane elements | beams, solids or springs in the A20 model | mesh only the air area with plane elements |
| ERROR: A 2D analysis (A20) needs all nodes in the XY plane (Z = 0) | mesh not in the XY plane | move the mesh to Z = 0 |
| ERROR: 'contact2' / 'nodesurfacecoupling' / 'constraintequation' on ... is not translated in an acoustic analysis | coupling in acoustics | use one continuous mesh |
| INFO: Load '...' on '...' does not count in an acoustic analysis | mechanical or thermal load in the model | normal |
| INFO: Mode 1 is at ~0 Hz: constant pressure | hard walls without a pressure node | normal (§3.1) |
| alarm `ALGELINE3_82` (la borne minimale ... est une valeur propre) | the lower bound of the Sturm check falls on the 0 Hz mode (hard walls) | harmless; the frequencies are correct (AK-01, AK-05) |
| `<EXCEPTION> <ALGELINE3_81>` | singular stiffness: a separate part of the volume without a pressure node while there are pressure nodes elsewhere, or only `#ASTER-EXCIT` loads | choose a small negative search frequency (e.g. −10 Hz); the 0 Hz mode is then included |
| alarm `ALGELINE5_15` / `ALGELINE5_23` | a mode misses the accuracy / multiple mode at the boundary (e.g. a square cross-section) | as for modal ([`Modal_and_buckling.md`](Modal_and_buckling.md) §4) |

More messages: [`CodeAster_error_messages.md`](CodeAster_error_messages.md).

## 5. Harmonic pressure field (`acoustic_harm_3d`)

Mecway has no harmonic analysis (Mecway Ltd., 2026, chapter 6). The bridge therefore
computes the **A30 model** (same mesh, material, *fluid pressure* and *impedance*) as a
**harmonic response**: the pressure field at each frequency of a list, driven by a
source (a vibrating face or an imposed pressure), with hard walls, pressure nodes and
absorbing boundaries. Examples: a loudspeaker in a box, an exhaust or duct, a room
with an absorbing ceiling.

| What | How in Mecway | Code-Aster |
|---|---|---|
| analysis | *Acoustic Resonance 3D* (A30); in the bridge `acoustic_harm_3d` (page *Acoustics (harmonic)*); `auto` chooses it when the model has a source | `PHENOMENE='ACOUSTIQUE'`, `DYNA_VIBRA` `TYPE_CALCUL='HARM'` |
| source: vibrating face | face selection **`SOURCE_...`** (or `BRON_...`): normal velocity = setting *Velocity SOURCE_ faces*; or **`#ASTER-BRON selection = velocity [, phase]`** | `AFFE_CHAR_ACOU` `VITE_FACE` |
| source: imposed pressure | *Fluid pressure* with a value ≠ 0 (nodes or faces) | `AFFE_CHAR_ACOU` `PRES_IMPO` |
| pressure node | *Fluid pressure* = 0 | `PRES_IMPO` 0 |
| absorbing boundary (ρc) | face selection **`ABSORBING_...`** (or `ABSORBEREND_...`) | `MODELISATION='3D_ABSO'` |
| impedance Z (real) | Mecway *Impedance* (*specific impedance*, Im = 0) | `3D_ABSO` with c = Z/ρ |
| hard wall | face without a condition | (nothing: ∂p/∂n = 0) |
| microphone | node selection **`MICROPHONE_...`** (or `MICROFOON_...`) | frequency response in the log and a CSV |

The prefixes apply to the name of the selection in Mecway; case does not matter
(`Source_speaker` works too).

### 5.1 Step-by-step procedure in Mecway

1. **Model as for the cavity modes** (§1.1): mesh only the fluid (hex, wedge, tet),
   analysis type *Acoustic Resonance 3D*, material *Isotropic* with *Speed of sound*
   **and a density** (e.g. 1.2 kg/m³ for air, 1000 kg/m³ for water): a velocity
   source gives p = ρ·c·v, so without a density the bridge stops (§5.7).
2. **Source.** Select the faces of the source (e.g. the cone of a loudspeaker, an
   inlet) as a *Face selection* and name it `SOURCE_Speaker`. The normal velocity is
   then the setting *Velocity SOURCE_ faces* (default 1 mm/s), directed **into the
   fluid** (a pushing piston), phase 0. A different velocity or phase per source: put
   the line `** ASTER-BRON Speaker = 2 mm/s, 90` in a free text field in Mecway (e.g.
   *CCX > Custom model definition*) (velocity in m/s or mm/s, phase in degrees; the
   selection then needs no prefix; `#ASTER-SOURCE` is the same keyword). Two
   loudspeakers in antiphase: two lines with phase 0 and 180. An **imposed pressure**
   as a source: *Fluid pressure* with a value (e.g. 2 Pa) on nodes or faces; Mecway
   itself refuses that for the cavity modes, the bridge uses it only here.
3. **Absorbing boundaries.** An open end into a large space, an anechoic termination or
   an "infinitely long" duct: face selection `ABSORBING_Outlet`. The bridge imposes the
   characteristic impedance ρc of the adjacent medium there: a plane wave hitting it
   perpendicularly is not reflected. An absorber with a different (real) impedance:
   Mecway's *Impedance* with *specific impedance* Z in Pa·s/m (Z = ρc = 408 for air;
   Z > ρc is harder, Z < ρc softer); the imaginary part must be 0 (§5.6).
4. **Microphones.** Node selection `MICROPHONE_Ear` with one node (or more, see §5.4).
5. **Mesh fineness.** Choose the element size for the highest frequency: λ = c/f_max,
   at least **10 linear** or **5 quadratic** elements per wavelength (§5.4); the bridge
   warns if the mesh is coarser.

### 5.2 In the bridge's main window

1. **Active analysis:** with A30 and a source (`SOURCE_` selection, `#ASTER-BRON` or
   *fluid pressure* ≠ 0) `auto` chooses `acoustic_harm_3d`, without a source
   `acoustic_modes_3d`. To get the cavity modes of a model with a source: choose
   `acoustic_modes_3d` yourself (the source and absorbing selections are then hard
   walls, INFO in the log).
2. **Results to Mecway** must be `liml`.
3. Page **Acoustics (harmonic)**:

| Setting (label) | Default | When to change |
|---|---|---|
| Start frequency / End frequency [Hz] | 50 / 1000 | the range of interest (e.g. 20–2000 Hz for hearing, or around a hum). The end frequency determines the mesh fineness (§5.4) |
| Number of frequencies | 20 | more to find resonance peaks: the step must be smaller than the width of a peak (§5.4); the run time grows linearly with the number |
| Spacing (lin / log) | lin | `log` over a wide range (equal ratios, like octave bands) |
| Frequency list [Hz] (0 = range above) | 0 | own frequencies, e.g. `100, 250, 500` (point as decimal separator); replaces the range |
| Velocity SOURCE_ faces [m/s] | 0.001 | the actual amplitude of the source; everything scales linearly (p ∝ v), so for a transfer function p/v any value is fine |
| Time limit / Memory limit run_aster, MUMPS NPREC | 900 s, 2048 MB, 8 | large models or many frequencies |

Per model with `#ASTER-OPTIE` (see [`ASTER_lines_examples.md`](ASTER_lines_examples.md)),
e.g. `** ASTER-OPTIE harm_freq_list = 125, 250, 500, 1000` or
`** ASTER-OPTIE harm_freq_count = 200`.

### 5.3 Results in Mecway

Under *Solution* there is one entry per frequency (*Mode 1 ... Mode n* with the
frequency in Hz; these are **not** eigenmodes but the response at that frequency).
Fields per frequency (nodal values):

| Field | Meaning | Unit |
|---|---|---|
| `pressure` | real part of the complex pressure P (the pressure at t = 0) | Pa |
| `pressurei` | imaginary part of P | Pa |
| `pressuremag` | amplitude \|P\| (peak value of the sine) | Pa |
| `pressurephase` | phase of P relative to the source, −180…180 | degrees |
| `spl` | sound pressure level 20·log10(\|P\| / (√2 · 20 µPa)) | dB |

The pressure in time is p(t) = Re(P·e^{iωt}) (the same convention as Mecway's complex
modes, Mecway Ltd., 2026, §6.9.2). Mecway's own API reads the frequencies and all five
fields per frequency (checked headless with a Mecway script); the display in the
Mecway GUI has not been inspected yet (KNOWN_BUGS 57).

The **log** and the status box show the number of frequencies and the highest level
per microphone; per microphone and frequency |p|, phase and SPL are in the log and in
`<model>_<run-id>_microfoons.csv` in the working folder (columns `microphone,
frequency_Hz, p_re_Pa, p_im_Pa, p_amp_Pa, phase_deg, spl_dB, nodes`; commas and a
point as decimal separator; with language Dutch Dutch column names). A spreadsheet
turns that directly into a frequency response (SPL against f).

### 5.4 Interpretation and checks

- **Plane wave (hand calculation):** in a duct with a source v at the start and an
  absorbing end, |p| = ρ·c·v everywhere and the phase decreases by k·x (k = 2πf/c).
  With a hard wall at the end (length L): |p(x)| = ρ c v |cos(k(L−x)) / sin(kL)|,
  infinite at the resonances f_n = n·c/(2L). A real impedance Z at the end reflects
  R = (Z − ρc)/(Z + ρc); the standing wave has max/min = (1+|R|)/(1−|R|).
- **SPL:** based on the rms value |P|/√2 (like a sound level meter). 1 Pa amplitude =
  91.0 dB. Code-Aster's own `PRAC_ELNO` DB (test case ahlv100a) uses |P| itself and is
  3.01 dB higher. A pressure node (p = 0) gets −200 dB.
- **Phase:** relative to the source (phase 0 = in phase with the velocity into the
  fluid). For a plane wave going into the fluid the pressure is in phase with the
  velocity.
- **Resonances:** without an absorbing boundary there is no damping and the response at
  a cavity mode is infinite (the bridge warns; Code-Aster then has a nearly singular
  matrix). First compute the cavity modes (`acoustic_modes_3d`) and choose the
  frequencies in between, or include an absorbing boundary. With absorption the peaks
  are finite; their width depends on the absorption: choose the frequency step at
  least 3–5 times smaller than the expected peak width, or run a second time with a
  finer list around the peak.
- **Elements per wavelength** (measured, [`Verification.md`](Verification.md) §7, AH):
  - hex20: 10 per wavelength gave |p| within 0.02% and the phase lag over 2
    wavelengths within 0.01% (AH-01); 5 per wavelength still ≤ 0.3% (AH-01b);
  - hex8: the phase lags by ≈ (kh)²/24 per wavelength: 10 per wavelength gave −1.6%
    phase and +1.7% |p| (AH-02a), 20 per wavelength −0.4% (AH-02b). For 1% phase
    about 13 linear elements per wavelength are needed.
  The bridge warns below 10 (linear) / 5 (quadratic) per wavelength at the highest
  frequency, measured with the **largest** element edge (also transverse). The error
  accumulates with distance: mesh finer in a long duct or a large room.
- **Absorbing boundary (ρc):** exact for a plane wave hitting it perpendicularly. An
  obliquely incident wave or a spherical wave close to the source is partly reflected;
  therefore place the boundary some distance from the source (rule of thumb: ≥ half a
  wavelength at the lowest frequency). Cross modes in a duct (above f ≈
  c/(2·width)) are also partly reflected.

### 5.5 How the bridge translates

`bridge_acoustic.build_acoustic_harm` writes the `.comm` (template
`AsterTemplate_AkoestiekHarm.comm`); route of test case ahlv100a:

1. `AFFE_MODELE` `PHENOMENE='ACOUSTIQUE'`: volumes and source faces
   `MODELISATION='3D'` (the source faces must be in the model and have a material),
   absorbing faces `'3D_ABSO'`.
2. `DEFI_MATERIAU(FLUIDE=_F(RHO, CELE_R))` per medium; per impedance a separate
   material with `CELE_R = Z/ρ` on that face. Measured: the `3D_ABSO` damping matrix is
   (1/c)∫NNᵀdA with the c of the face and without ρ (a different RHO on the face changed
   nothing; `CELE_R` 680 instead of 340 gave reflection 1/3, like Z = 2ρc), and
   Mecway's impedance term is (ρ/Z)∫NNᵀdA (Mecway Ltd., 2026, §6.9.2).
3. Source: `AFFE_CHAR_ACOU(VITE_FACE=_F(GROUP_MA, VNOR=v))`; imposed pressure and
   pressure nodes: `PRES_IMPO`.
4. `ASSEMBLAGE`: `RIGI_ACOU`, `MASS_ACOU`, `AMOR_ACOU` (only with absorbing boundaries)
   and the load vectors `CHAR_ACOU` (velocity and imposed pressure separately).
5. `DYNA_VIBRA(TYPE_CALCUL='HARM', BASE_CALCUL='PHYS', LIST_FREQ=...)` with the velocity
   source as `EXCIT` `PUIS_PULS=1, PHAS_DEG=90` (= iω·v) and the imposed pressure
   without a factor. Measured: `COEF_MULT=+1` gives p = +ρcv at the source with an
   absorbing end, so v into the fluid; ahlv100a uses −1 (v outward).
6. `aster_acoustic_export.py` (in the job) writes one `<mode>` per frequency with the
   five fields and the microphone response (CSV, lines `BRIDGE_MIC` in the `.mess`).

With `med_export` on, the bridge writes the real and imaginary parts as
`PRES_REEL`/`PRES_IMAG` to the `.rmed`. Own post-processing of the result `res` (type
`ACOU_HARMO`, complex field `PRES`) is possible with `#ASTER-POST`, e.g.
`CALC_CHAMP(... ACOUSTIQUE=('INTE_ELNO',))` for the intensity (ahlv100a).

### 5.6 What is not possible

- **Complex impedance** (Im Z ≠ 0) and frequency-dependent impedance: Code-Aster's
  `3D_ABSO` with a complex `CELE_I` did not give the reflection of a complex Z, and
  `DYNA_VIBRA` has no frequency-dependent term (KNOWN_BUGS 57): ERROR.
- **Volume damping** (air damping, porous materials) and a complex speed of sound: not
  translated.
- **Coupling with a structure** (vibrating panel): not in this analysis; see §6
  (coupled modes) and §7 (harmonic response of structure + fluid).
- A source at a node or inside the volume (point source, monopole): no; use a small
  source face or an imposed pressure.
- Microphones on face or element selections (only node selections count; WARNING).
- Comparison with a Mecway solve (*Mecway solve first as a check*): Mecway has no
  harmonic analysis (INFO).
- Furthermore everything that is not possible for the cavity modes (§3.4): 2D, media
  with different density, contact and couplings, pyramids.

### 5.7 Messages and solutions (harmonic)

| Message | Cause | Solution |
|---|---|---|
| ERROR: Acoustics harmonic: no source | no `SOURCE_` face selection, `#ASTER-BRON` or *fluid pressure* ≠ 0 | name the source faces `SOURCE_...` |
| ERROR: Acoustics harmonic: material ... has no density | velocity source without density (p = ρcv) | fill in a density for the material |
| ERROR: ... source '...' is a node selection; a source must be a face selection | `SOURCE_` on nodes or elements | make a *Face selection* |
| ERROR: ... '#ASTER-BRON ...': expected 'selection = velocity ...' | typing error in the line | e.g. `** ASTER-BRON Speaker = 2 mm/s, 90` (point as decimal separator) |
| ERROR: ... #ASTER-BRON: '...' is not a face selection | the name does not exist as a face selection | name exactly as in Mecway |
| ERROR: ... '...' borders 2 media; make a separate selection per medium | source or absorbing selection borders two materials | split the selection |
| ERROR: ... selection '...' is both source and absorbing | the same selection with two roles | separate selections |
| ERROR: ... impedance on '...' is complex (Im Z = ...) | *specific impedance (imaginary)* ≠ 0 | only a real Z (§5.6) |
| ERROR: ... impedance on '...': material '...' has no density | Z/ρ without ρ | fill in a density |
| ERROR: ... frequency list (harm_freq_list) '...' is invalid | no numbers, or ≤ 0 | e.g. `100, 250, 500`, or `0` for the range |
| ERROR: ... frequency range ... is invalid | start ≤ 0, end < start or count < 1 | settings on the page |
| WARNING: ... no absorbing boundary ...: the response at a cavity mode is infinite | only hard walls and pressure nodes | add an absorbing boundary or choose frequencies between the resonances |
| WARNING: ... fewer than 10 (linear) / 5 (quadratic) elements per wavelength | mesh too coarse for the highest frequency | refine the mesh or lower the end frequency (§5.4) |
| WARNING: ... microphone '...' is a face selection | microphone not a node selection | make a *Node selection* |
| ERROR: Acoustics: fluid pressure on '...' is ...; only 0 is possible (pressure node; as a source: ...) | cavity modes (`acoustic_modes_3d`) with *fluid pressure* ≠ 0 | set it to 0, or compute harmonically (`auto` does that by itself) |

## 6. Vibroacoustics: coupled modes (`vibroacoustic_modes_3d`)

A structure and an air or liquid volume in one model: the bridge computes the
**coupled eigenmodes**, in which the structure makes the fluid vibrate along and the
fluid pushes back. Examples: a panel on an air cavity (the "pumping mode" becomes
stiffer through the air spring), a piston or membrane in a liquid column, a tank or
pipe with water (the water adds **added mass**: the structure vibrates lower), a
loudspeaker box. Mecway has no coupled analysis (Mecway Ltd., 2026, chapter 6) and
computes acoustics with one material; the bridge therefore uses an ordinary
*Frequency* model (V30) in which the fluid is a part of its own.

| What | How in Mecway | Code-Aster |
|---|---|---|
| analysis | *Frequency 3D* (V30) with *Number of modes*; `auto` chooses `vibroacoustic_modes_3d` as soon as the model has a fluid | `PHENOMENE='MECANIQUE'`, `CALC_MODES` `OPTION='BANDE'` |
| fluid | a part (component) with an *Isotropic* material with **Speed of sound** and **Density**, without Young's modulus; or a part whose name starts with **`LUCHT_`**, **`VLOEISTOF_`** or **`FLUID_`** | `MODELISATION='3D_FLUIDE'`, `FORMULATION='U_P_PHI'`, `DEFI_MATERIAU(FLUIDE=_F(RHO, CELE_R))` |
| structure | the other parts, as in a modal analysis (solids, shells, beams, springs, supports) | the ordinary mechanical elements |
| coupling face | **automatic**: every face of a fluid element that coincides with a face of a structural solid element or with a shell element (shared nodes); manual: face selections **`KOPPEL_...`** (or `COUPLING_...`) | `MODELISATION='FLUI_STRU'` (skin elements, normal out of the fluid) |
| p = 0 (free surface, open end) | node or face selection **`OPEN_...`** (or Mecway's *fluid pressure* = 0, if it is in the model) | `DDL_IMPO` `PRES=0`, `PHI=0` |
| hard wall | face of the fluid without a condition and without structure | (nothing: ∂p/∂n = 0) |

The prefixes apply to the name in Mecway; upper/lower case does not matter.

### 6.1 Step-by-step procedure in Mecway

1. **Mesh the structure and the fluid as one continuous mesh**: on the interface they
   share the nodes (like two parts merged in Mecway). The fluid: hex, wedge, tet or
   pyramid (linear or quadratic); the structure: anything the modal analysis knows. A
   shell may lie on a fluid face (the shell shares its nodes with the fluid), but not
   with fluid on **both** sides: the two sides would then have the same pressure
   (ERROR; then make the panel from one layer of solid elements).
2. **Analysis type** *Frequency 3D* with *Number of modes*.
3. **Material of the fluid**: *Isotropic* with only *Speed of sound* (e.g. 340 m/s for
   air, 1480 m/s for water) and a *Density* (1.2 kg/m³ air, 1000 kg/m³ water). Leave
   *Young's modulus* empty: that is how the bridge recognises the fluid. The density is
   needed: the coupling and the added mass depend on it. Two fluids (e.g. water and
   air) must **not touch** if they have a different density (ERROR, §6.6); with the
   same density and a different speed of sound it is fine.
4. **Structure** as in a modal analysis: material with E, ν and density,
   section/thickness, supports (*fixed*, *displacement*, ...). Loads do not count
   (WARNING; there is no prestress in vibroacoustics).
5. **Boundaries of the fluid**:
   - a face against the structure: coupling face (automatic);
   - a face with nothing: hard wall (e.g. a stiff tank wall that you do not mesh);
   - a free water surface or an open end into a large space: p = 0 with a node or face
     selection `OPEN_Surface`. (Air above water is not meshed: different density, and
     for the water motion p = 0 is the usual approximation; sloshing due to gravity is
     not included by the bridge.)
6. **Mesh density**: as for the cavity modes (§1.5): choose the fluid mesh for the
   highest frequency you look for; ≥ 10 linear or ≥ 5 quadratic elements per
   wavelength c/f. The structure as in a modal analysis (shell: enough elements per
   half wave).

### 6.2 In the bridge's main window

1. **Active analysis:** `auto` chooses `vibroacoustic_modes_3d` for a Frequency model
   with a fluid (INFO in the log); or choose it yourself. If you choose `modal_3d` for
   such a model, the bridge computes the fluid as a solid (WARNING).
2. **Results to Mecway** must be `liml`.
3. **Mecway solve first as a check**: pointless (Mecway computes a material without
   Young's modulus as a solid with E = 0; the bridge then does not compare).
4. Page **Vibroacoustics (modes)**:

| Setting (label) | Default | When to change |
|---|---|---|
| Number of modes (without maxmode in Mecway) | 10 | only if the Mecway model has no *Number of modes* |
| Lower frequency bound [Hz] (`vibro_freq_min`) | 0.1 | the modes **above** this frequency. Higher: the modes from a frequency on (e.g. around a hum or a rotation speed). Below 0.1 Hz only for a very soft structure (modes expected below 0.1 Hz); > 0 is always needed (§6.5) |
| Mode check (VERI_MODE SEUIL) | 1e-6 | larger (e.g. 1e-5) if the log reports `ALGELINE5_15` (the error of a mode just above 1e-6, seen with hex8 air) |
| Time limit / Memory limit run_aster, MUMPS NPREC | 900 s, 2048 MB, 8 | large models |

Per model with `#ASTER-OPTIE`, e.g. `** ASTER-OPTIE vibro_freq_min = 100`
([`ASTER_lines_examples.md`](ASTER_lines_examples.md), example 14).

### 6.3 Results in Mecway

Under *Solution* there are *Mode 1 … Mode n* with the frequency, as for a modal
analysis. Per mode:

| Field | Where | Meaning |
|---|---|---|
| `displ` (`displx`, `disply`, `displz`; shells and beams also `rot*`) | nodes of the structure (including those on the coupling face) | mode shape of the structure |
| `pressure` | nodes of the fluid (including those on the coupling face) | acoustic pressure of the same mode |

The scale is arbitrary (like any mode shape), but **displacement and pressure belong
together**: the ratio p/u is physical (verification VA-01: on the piston within 2e-6
equal to the analytical ρω²·cot(kL)/k). The bridge normalises to generalised mass 1
(`NORM_MODE MASS_GENE` of the coupled mass matrix). Fluid nodes have no displacement,
structural nodes outside the coupling face no pressure. Mecway's API reads the
frequencies and both fields per mode (checked headless with a Mecway script on VA-01);
the display in the Mecway GUI has not been looked at yet (KNOWN_BUGS 59). In the log
and the status box: the frequencies and the band that was searched.

### 6.4 Interpretation and checks

- **Coupled mode**: structure and fluid vibrate together at one frequency. A heavy
  liquid on a light structure changes the frequencies a lot; air on a steel plate
  little, unless the air is enclosed and the plate acts on it like a piston.
- **Added mass** (liquid that has to move along) lowers the frequency; the **air
  spring** of an enclosed volume raises that of a mode that compresses the volume.
  Measured (VA-05b, steel plate 0.5 × 0.4 m, 2 mm, on a closed air cavity
  0.5 × 0.4 × 0.3 m): the pumping mode (1,1) goes from 50.52 to 54.96 Hz (+8.8%; a hand
  calculation with one mode and the air spring ρc²(∫φ dA)²/V gives 55.23 Hz); the other
  plate modes drop 0.2–0.5% (added mass); the first cavity mode drops 0.7% (the plate
  gives way).
- **Hand calculation for a column** (piston with mass m per area between a water
  column L1 with a free surface and a closed air column L2):
  m + ρ1·tan(k1L1)/k1 − ρ2·cot(k2L2)/k2 = 0; for low frequency
  f ≈ 1/(2π)·√(ρ2c2²/(L2(m + ρ1L1))) (mass plus the moving water column on the air
  spring). Test case adlv100a: 13.83 Hz (VA-01).
- **Check of the coupling**: temporarily make the density of the fluid 1000× smaller;
  the modes must then be the separate structural modes (*Modal*) and the cavity modes
  (*Acoustics (cavity modes)*, hard walls) (VA-05: ≤ 0.6%, the difference is the shell
  discretisation).
- **No modes at 0 Hz**: a rigid body motion or a constant pressure in a closed volume
  falls below the lower bound and is not given.

### 6.5 How the bridge translates

`bridge_vibroacoustic.py` writes the `.comm` (template
`AsterTemplate_VibroAkoestiek.comm`); syntax of the test cases adlv100a (piston +
liquid column), adlv100p and adlv312a:

1. `bridge_mesh` writes the coupling faces as skin elements (groups `BRFSI1`,
   `BRFSI2`, … per fluid part); `MODI_MAILLAGE ORIE_PEAU` with `GROUP_MA_INTERNE` = the
   fluid points their normal out of the fluid (adlv100b, adls102a).
2. `AFFE_MODELE`: the structure as in modal, the fluid `3D_FLUIDE` and the coupling
   faces `FLUI_STRU`, both `FORMULATION='U_P_PHI'` (the Code-Aster default; unknowns
   displacement, pressure p and displacement potential φ; symmetric matrices).
   Measured: `U_P` (non-symmetric) gave a wrong series with `PLUS_PETITE` and a
   `<F> JEVEUX_26` with `CENTRE`; `U_PSI` has no `DDL_IMPO PRES`.
3. `DEFI_MATERIAU(FLUIDE=_F(RHO, CELE_R))` on the fluid and its coupling faces. The
   density is in the matrices (measured: rod + water column with ρ 1000 and 1 each gave
   their own analytical frequencies), unlike for the cavity modes (§3.2).
4. Supports of the structure as in modal; p = 0 as `DDL_IMPO PRES=0, PHI=0`.
   `ASSEMBLAGE` `RIGI_MECA` and `MASS_MECA`.
5. **Searching the modes.** In `U_P_PHI` the stiffness has no term for φ: every φ
   degree of freedom gives a spurious mode at 0 Hz (measured: 40 on the small mesh of
   adlv100a, with negative generalised mass). `PLUS_PETITE` then stops with
   `ALGELINE3_81` and `CENTRE` first gives those spurious modes. The bridge therefore
   uses `INFO_MODE` (Sturm count) to find a band [`vibro_freq_min`, f_max] with at
   least the requested number of modes (×4 per step, then two halvings), computes
   `CALC_MODES OPTION='BANDE'` and keeps the first modes with f ≥ `vibro_freq_min` and
   a positive generalised mass (`EXTR_MODE`), normalised with `NORM_MODE`
   `MASS_GENE`. The Sturm count is right (rod + water column: 6 of 6 analytical modes).
6. `aster_results_export` writes `displ` (DX…) and `pressure` (component `PRES` of
   `DEPL`) per mode.

### 6.6 What is not possible

- **Harmonic response** of structure + fluid (force or source per frequency, absorbing
  boundaries): not in the modes, but in the analysis `vibroacoustic_harm_3d` on the
  same model (§7). For the pressure field without a structure: §5.
- **Two fluids touching each other with a different density** (e.g. air above water):
  on shared nodes φ is continuous, which with p = ρω²φ is only right for equal
  density (measured: pipe with ρ 1.2/12 gave 188.23 Hz, analytically 306.47 Hz):
  ERROR. Separated by a structure (as in adlv100a) is fine.
- A shell with fluid on both sides (shared nodes): ERROR (step 1 of §6.1).
- A non-continuous mesh (fluid and structure with their own nodes on the interface):
  no coupling face (WARNING). *Bonded contact* between fluid and structure: NOT
  verified (no coupling face; use shared nodes).
- Impedance, *fluid pressure* ≠ 0, source, absorbing and microphone selections: do not
  count in the modes (impedance and *fluid pressure* ≠ 0: ERROR; the selections: INFO).
- Prestress from loads, damping and complex modes, gravity on the free surface
  (sloshing, `2D_FLUI_PESA`), effective mass per mode (Code-Aster's value has no
  meaning for these modes), comparison with a Mecway solve.
- `elem_hex8` = `LINE_QUAD` with a fluid: NOT verified.

### 6.7 Messages and solutions

| Message | Cause | Solution |
|---|---|---|
| ERROR: Vibroacoustics: the model has no fluid | no part with a material with *Speed of sound* without Young's modulus, and no `LUCHT_`/`FLUID_` name | give the air/liquid volume a part and material of its own |
| ERROR: … part '…' is named a fluid, but material '…' has no speed of sound | name with `LUCHT_`/`FLUID_`, material without *Speed of sound* | fill in *Speed of sound*, or rename the part |
| ERROR: … fluid material '…' has no density | *Density* missing | fill in the density (1.2 air, 1000 water) |
| ERROR: … fluid '…' contains quad4 … only solid elements | shells or beams in a fluid part | mesh the fluid with solid elements; shells in a part of their own with a structural material |
| ERROR: … fluids '…' and '…' touch with a different density | two fluids with shared nodes (§6.6) | leave out one fluid (air above water: p = 0 with `OPEN_`), or equal density |
| ERROR: … shell element(s) … have fluid on both sides | shell between two fluid volumes with the same nodes | panel as one layer of solid elements, or fluid on one side |
| ERROR: … face(s) of COUPLING_ selections do not border exactly one fluid element | `KOPPEL_` face that is not a fluid face | choose faces on the fluid–structure interface |
| ERROR: … OPEN_ selection '…' is an element selection / COUPLING_ selection '…' is a … selection | wrong kind of selection | `OPEN_`: nodes or faces; `KOPPEL_`: faces |
| ERROR: … fluid pressure on '…' is …; in the modes only 0 / impedance on … | *fluid pressure* ≠ 0 or *impedance* in the model | set the value to 0 (or use `OPEN_`), suppress the impedance |
| WARNING: … no coupling face found | fluid and structure share no nodes | merge the nodes (one continuous mesh) |
| WARNING: … loads (…) do not count in the modes | forces/pressures in the model | normal; they have no influence on the modes |
| WARNING: … N of the M requested modes found | the solver did not find all modes in the band; usually a mechanism (e.g. a shell with only one rotation fixed, spurious modes at ~0 Hz) | check the supports; ask for fewer modes or raise `vibro_freq_min` |
| INFO: … spurious mode(s) … left out | Code-Aster returned a mode below the lower bound or with mass ≤ 0 (§6.5) | normal |
| WARNING: Part(s) … have a material with a speed of sound and without Young's modulus | a fluid in an analysis other than `vibroacoustic_modes_3d` | choose `vibroacoustic_modes_3d` (or `auto` with a Frequency model) |
| alarm `MODELISA4_8` / `MODELISA8_13` (mailles doubles) | a shell on a fluid face: shell and coupling face are separate cells with the same nodes | harmless (VA-03, VA-05) |
| alarm `ALGELINE5_15` | the error of a mode is just above *Mode check* | *Mode check* 1e-5 |

## 7. Vibroacoustics harmonic (`vibroacoustic_harm_3d`)

The same model as §6 (structure + fluid, one continuous mesh), but now excited **per
frequency**: the bridge computes the steady-state response to a harmonic force on the
structure, a vibrating face in the fluid or an incident sound wave, with absorbing
boundaries where the sound leaves the model. Examples: a machine cover or panel
radiating sound into a room (SPL at a microphone), a piston or membrane on a duct with
an anechoic end, a loudspeaker in a box, a tank wall excited by a pressure wave in the
water. Mecway has neither a harmonic nor a coupled analysis (Mecway Ltd., 2026, chapter
6); with such a model `auto` keeps choosing the coupled modes (§6), you choose this
analysis yourself.

| What | How in Mecway | Code-Aster |
|---|---|---|
| analysis | *Frequency 3D* (V30) with a fluid part (§6.1); in the bridge `vibroacoustic_harm_3d` (page *Vibroacoustics (harmonic)*) | `DYNA_VIBRA` `TYPE_CALCUL='HARM'`, `BASE_CALCUL='PHYS'` |
| force on the structure | Mecway loads (*force*, *pressure*, *gravity*, ...) = the amplitude; phase with `#ASTER-FASE selection = degrees`; a Mecway table = amplitude versus frequency (column *time* = Hz), as in the harmonic response ([`Mode_superposition.md`](Mode_superposition.md)) | `CALC_VECT_ELEM` → `EXCIT` (`PHAS_DEG`, `FONC_MULT`) |
| velocity source in the fluid | face selection **`SOURCE_...`** (or `BRON_...`) on a face of the fluid: normal velocity = *Velocity SOURCE_ faces*, into the fluid; or **`#ASTER-BRON selection = v [m/s, mm/s] [, phase]`** | `AFFE_CHAR_MECA` `VITE_FACE` |
| incident wave | face selection **`INCIDENT_...`** (or `INVALLEND_...`): a plane wave with amplitude *Amplitude incident wave* enters the fluid through this face; the face lets reflected waves pass unhindered; or **`#ASTER-BRON selection = p [Pa] [, phase]`** | `AFFE_CHAR_MECA` `ONDE_FLUI` + matrix `ONDE_FLUI` |
| absorbing boundary (ρc) | face selection **`ABSORBING_...`** (or `ABSORBEREND_...`) | `MODELISATION='3D_FLUI_ABSO'`, matrix `IMPE_MECA` |
| impedance Z (real) | Mecway *Impedance* (*specific impedance*, Im = 0) on a face of the fluid | `3D_FLUI_ABSO` with its own material c = Z/ρ |
| p = 0 | `OPEN_...` (nodes or faces), as in §6 | `DDL_IMPO PRES=0, PHI=0` |
| microphone | node selection **`MICROPHONE_...`** in the fluid: pressure, phase and SPL per frequency | log, CSV |
| probe | node selection **`PROBE_...`** (or `MEETPUNT_...`) on the structure: displacement per frequency | log, CSV |
| damping of the structure | Mecway *Rayleigh damping* (only on the structure) and *Damper* elements | `MATR_AMOR` = α·M_s + β·K_s + `AMOR_MECA` |

The prefixes apply to the name in Mecway; upper/lower case does not matter.

### 7.1 Step-by-step procedure in Mecway

1. **Model as for the coupled modes** (§6.1): structure and fluid as one continuous
   mesh, fluid material with *Speed of sound* and *Density* without Young's modulus,
   supports of the structure, `OPEN_` for p = 0. A panel radiating into a (half-)open
   space: mesh a piece of air in front of the panel and close it with an absorbing
   boundary (step 3).
2. **Source.** A force or pressure on the structure (e.g. a *force* at the mounting
   point of a motor): the value is the amplitude at every frequency; for a different
   phase per selection: `** ASTER-FASE Force2 = 90` in *CCX > Custom model definition*.
   Or a source in the fluid: face selection `SOURCE_Speaker` on a face of the fluid
   (velocity into the fluid) or `INCIDENT_Inlet` (an incoming wave, e.g. the inlet of a
   duct). Per selection its own value and phase: `** ASTER-BRON Inlet = 2 mm/s, 90`
   (velocity) or `** ASTER-BRON Inlet = 0.5 Pa, -30` (pressure: incident wave); the
   selection then needs no prefix.
3. **Absorbing boundaries** where the sound must leave the model: face selection
   `ABSORBING_Wall` (ρc of the fluid: a plane wave at normal incidence is not
   reflected), or Mecway's *Impedance* with a real Z for a partly absorbing wall
   (Z = ρc = 408 Pa·s/m for air; Z > ρc harder, Z < ρc softer). Put an absorbing
   boundary some distance from the source (≥ half a wavelength at the lowest
   frequency, §5.4).
4. **Microphones and probes:** node selection `MICROPHONE_Ear` in the fluid and
   `PROBE_Cover` on the structure (one node, or more: then the root mean square of the
   amplitude, as in §5.4).
5. **Mesh density:** the fluid as in §5.1 (≥ 10 linear or ≥ 5 quadratic elements per
   wavelength at the highest frequency; the bridge warns), the structure fine enough for
   the bending waves at the highest frequency.
6. **Analysis:** choose `vibroacoustic_harm_3d` in the main window (`auto` computes the
   modes, §6).

### 7.2 In the bridge's main window

Page **Vibroacoustics (harmonic)**:

| Setting (label) | Default | When to change |
|---|---|---|
| Result fields to Mecway | displacement, acceleration, stress, von Mises | the pressure is always included; fewer fields for a smaller `.liml`; stresses only on solid elements of the structure |
| Start frequency / End frequency [Hz] | 20 / 500 | the range of the question; the end frequency determines the mesh density of the fluid (§7.1) |
| Number of frequencies | 50 | more to catch resonance peaks (step smaller than the peak width, §7.4); the run time grows linearly (one factorisation per frequency) |
| Spacing (lin / log) | lin | `log` over a wide range |
| Frequency list [Hz] (0 = range above) | 0 | own frequencies, e.g. `100, 250, 500`; a fine list around a coupled mode from §6 |
| Velocity SOURCE_ faces [m/s] | 0.001 | the actual amplitude of the source (p ∝ v) |
| Amplitude incident wave INCIDENT_ [Pa] | 1 | the amplitude of the wave entering the model (everything is linear) |
| Time limit / Memory limit run_aster, MUMPS NPREC | 1800 s, 2048 MB, 8 | large models or many frequencies |

Per model with `#ASTER-OPTIE`, e.g. `** ASTER-OPTIE harm_freq_list = 125, 250, 500`
([`ASTER_lines_examples.md`](ASTER_lines_examples.md), example 27). *Mecway solve first
as a check* is pointless (INFO in the log).

### 7.3 Results in Mecway

Under *Solution* there is one line per frequency (*Mode 1 … Mode n* with the
frequency; not eigenmodes, but the response at that frequency). Fields per frequency
(nodal values):

| Field | Where | Meaning |
|---|---|---|
| `displx/y/z`, `displix/y/z` | structure (also the nodes on the coupling face) | real and imaginary part of the displacement U [m] |
| `displampx/y/z`, `displmag`, `displphasex/y/z` | structure | amplitude per direction, total amplitude, phase [degrees] |
| `rot*`, `rotamp*` | shells and beams | rotation (Re) and amplitude [rad] |
| `accamp*`, `accmag` (and `velamp*`, `velmag` with *velocities*) | structure | ω²·\|U\| (ω·\|U\|) |
| `stress..`, `stressamp..`, `vonmises` | solid elements of the structure | stress (Re), amplitude per component, largest von Mises over a period |
| `pressure`, `pressurei` | fluid (also the nodes on the coupling face) | real and imaginary part of the pressure P [Pa] |
| `pressuremag`, `pressurephase`, `spl` | fluid | \|P\|, phase [degrees], sound pressure level 20·log10(\|P\|/(√2·20 µPa)) [dB] |

The time function is u(t) = Re(U·e^{iωt}) and p(t) = Re(P·e^{iωt}) (as in §5.3 and the
harmonic response of structures). Mecway's API reads the frequencies and the fields
(checked headless with a Mecway script on VH-02: 8 frequencies, `displx`/`displix` on
the piston, `pressure`/`pressurei`/`spl` in the column); the display in the Mecway GUI
has not been checked yet (KNOWN_BUGS 59).

In the **log** and the status box: the number of frequencies, per microphone the
highest level and per probe the largest amplitude; per frequency in the log and in
`<model>_<run-id>_microfoons.csv` (columns as in §5.3) and
`<model>_<run-id>_meetpunten.csv` (columns as in the harmonic response:
`probe, frequency_Hz, u_amp_m, a_amp_m_s2, ux_re_m, ...`).

### 7.4 Interpretation and checks

- **Radiation damping:** a structure that radiates sound loses energy to the wave
  travelling away; that acts as a damper. A rigid piston with area A on a column with a
  ρc end feels a force −ρcA·v, so U = F / (k − mω² + iωρcA), ζ = ρcA/(2√(km)): the
  resonance peak stays finite without other damping (verification VH-02: ζ = 0.17, U
  and the pressure within 1.3e-4). With an impedance Z at the end the piston sees the
  input impedance Z_in = ρc(1 + R·e^{−2ikL})/(1 − R·e^{−2ikL}),
  R = (Z − ρc)/(Z + ρc) (VH-03). Air on a steel plate gives little radiation damping,
  water or a light structure a lot.
- **Enclosed fluid without absorption:** no radiation damping; at a coupled natural
  frequency (§6) the response is infinite (WARNING). Give the structure damping
  (Rayleigh, dampers) or an absorbing boundary, or choose frequencies between the
  modes.
- **Pressure and SPL:** a plane wave with velocity v has p = ρcv (air: 408 Pa per m/s);
  1 Pa amplitude is 91.0 dB. SPL on the effective value (\|P\|/√2), as in §5.4.
- **Incident wave:** the amplitude is that of the wave entering the model; with an
  absorbing end \|P\| equals that amplitude everywhere, with a hard wall at the end 2×
  at the wall, with p = 0 (`OPEN_`) 0 (VH-05, VH-05b). Code-Aster's `ONDE_FLUI` with
  `PRES` gives an incoming wave with amplitude `PRES`/2 (ahlv101a: `PRES` 1 → 0.5 Pa);
  the bridge writes `PRES` = 2× the setting.
- **Damping of the structure:** Mecway's *Rayleigh damping* C = αM + βK acts only on
  the structure (the mass and stiffness matrix of the structural elements), not on the
  fluid (VH-04: α, VH-04b: β); dampers as in a modal model (VH-04c).
- **Phase:** relative to the source (phase 0); lagging is negative. For a wave
  travelling away the source velocity and the pressure in front of it are in phase.
- **Own check:** the piston of the first item (rigid plate on a spring, column with an
  `ABSORBING_` end) is a simple test set-up next to your own model.

### 7.5 How the bridge translates

`bridge_vibroacoustic_harm.py` writes the `.comm` (template
`AsterTemplate_VibroAkoestiekHarm.comm`); route of the test cases ahlv101a (incident
wave: `ONDE_FLUI` + `IMPE_MECA` as `MATR_IMPE_PHI`), ahlv100b (`VITE_FACE` with
`3D_FLUI_ABSO`) and ahlv302a:

1. Mesh, model and materials as in §6.5 (coupling faces `FLUI_STRU`, `U_P_PHI`), plus
   the source and wave faces as `3D_FLUIDE` and the absorbing faces as `3D_FLUI_ABSO`,
   all boundary faces with the normal out of the fluid (`ORIE_PEAU`). An impedance gets
   its own material with `CELE_R = Z/ρ` (measured: VH-03 then agrees within 1.2e-4).
2. Loads on the structure as in the harmonic response (`CALC_VECT_ELEM` per load,
   phase `PHAS_DEG`, table `FONC_MULT` in the frequency); sources per face
   `AFFE_CHAR_MECA(VITE_FACE=...)` and `AFFE_CHAR_MECA(ONDE_FLUI=_F(PRES=2·p_in))`
   (both take only a real value; the phase is in `EXCIT`).
3. `ASSEMBLAGE` `RIGI_MECA`, `MASS_MECA` (Rayleigh: the same matrices on the structure
   groups only; dampers: `AMOR_MECA` with `AMOR_FLUI='NON'`), and separately
   `ONDE_FLUI` and `IMPE_MECA` on the same numbering (`IMPE_MECA` rejects `CARA_ELEM`:
   `SUPERVIS_4`; `AMOR_MECA` with `GROUP_MA` gave `DVP_1`).
4. `DYNA_VIBRA(TYPE_CALCUL='HARM', BASE_CALCUL='PHYS', MATR_IMPE_PHI=..., MATR_AMOR=...,
   AMOR_FLUI='NON')`: the sources as `EXCIT` with `PUIS_PULS=1, PHAS_DEG=90` (iω × the
   vector, as in ahlv101a/ahlv100b), `VITE_FACE` with `COEF_MULT=−1` (ahlv100b gives
   p = −ρcv with +1: `VNOR` outward; the bridge applies v into the fluid).
   `AMOR_FLUI='NON'` as `DYNA_LINE` does with `MATR_AMOR` and `MATR_IMPE_PHI` together.
5. `CALC_CHAMP SIGM_NOEU` on the solid elements of the structure;
   `aster_harmonic_export.py` writes one `<mode>` per frequency with the displacement
   (components DX…) and the pressure (component `PRES` of `DEPL`), plus the CSV files.

**Why direct (`PHYS`) and not on a modal basis** (as `harmonic_3d` by default): in
`U_P_PHI` every degree of freedom φ gives a spurious mode at 0 Hz (§6.5), so a modal
basis needs the `BANDE` search and misses the quasi-static contribution; the absorbing
boundary is not a proportional damping, so the real modes do not decouple (and the
radiation damping is exactly what you want to see); the test cases compute it this way
too. Drawback: one factorisation per frequency.

With `med_export` on, the bridge writes `DEPL_REEL`/`DEPL_IMAG` (with `PRES`) to the
`.rmed`. Own post-processing on `res` (type `DYNA_HARMO`) with `#ASTER-POST`; loads
from `#ASTER-EXCIT` only count as supports (as in the harmonic response).

### 7.6 What is not possible

- **Complex or frequency-dependent impedance** (Im Z ≠ 0): ERROR (KNOWN_BUGS 59; as in
  §5.6).
- **Imposed pressure ≠ 0** (*fluid pressure* with a value): ERROR; use `SOURCE_`,
  `INCIDENT_` or `#ASTER-BRON`. An imposed (base) motion of the structure ≠ 0: ERROR
  (as in the harmonic response).
- **Oblique incidence** or a spherical wave: `ONDE_FLUI` and `3D_FLUI_ABSO` are exact
  for a plane wave at normal incidence; oblique waves are partly reflected (as in
  §5.4).
- Volume damping in the fluid, porous materials, hysteretic damping of the structure
  (`AMOR_HYST`), extra modal damping (`modal_damping`; the computation is direct).
- A source on a node or in the volume (sources only on face selections, microphones
  only on node selections: WARNING).
- Everything that is not possible in the coupled modes (§6.6): two fluids with a
  different density touching each other, a shell with fluid on both sides, prestress,
  sloshing.
- Stresses in shells and beams (only displacements/rotations), reactions.
- Comparison with a Mecway solve (Mecway does not have this analysis).

### 7.7 Messages and solutions

| Message | Cause | Solution |
|---|---|---|
| ERROR: Vibroacoustics harmonic: the model has no fluid | no fluid part (§6.1) | fluid part with *Speed of sound* and *Density* without E, or choose `harmonic_3d` |
| ERROR: … no source: no load on the structure …, no SOURCE_ or INCIDENT_ face selection and no #ASTER-BRON | nothing drives the model | a force/pressure on the structure or a source face |
| ERROR: … source / incident wave / absorbing boundary '…' does not border exactly one fluid | the faces lie (partly) on the structure or on two fluids | choose faces of one fluid part (*Face selection* on the air) |
| ERROR: … '…' is a node/element selection; choose a face selection | `SOURCE_`/`INCIDENT_`/`ABSORBING_` on nodes | make a *Face selection* |
| ERROR: … selection '…' is both … and … | the same selection with two roles | separate selections |
| ERROR: … '#ASTER-BRON …': expected 'selection = velocity [m/s, mm/s, …] or pressure [Pa, N/m2, …] [, phase in degrees]' (possibly: unit '…' not recognised) | typing error or an unknown unit | e.g. `** ASTER-BRON Inlet = 2 mm/s, 90` (point as decimal separator) |
| ERROR: … impedance on '…' is complex / Re Z must be a number > 0 | *specific impedance* with Im ≠ 0 or Re ≤ 0 | only a real Z > 0 |
| ERROR: … fluid pressure on '…' is …; an imposed pressure != 0 … | *fluid pressure* with a value | `OPEN_` (p = 0) or a source |
| ERROR: … imposed displacement or rotation <> 0 | base motion | value 0; the load as a force or source |
| ERROR: … frequency list / frequency range … is invalid | settings | e.g. `100, 250, 500`, or `0` for the range |
| WARNING: … no absorbing boundary … and no damping … infinite | closed fluid without damping | absorbing boundary or Rayleigh/dampers, or frequencies between the modes (§6) |
| WARNING: … no coupling face found | fluid and structure share no nodes | one continuous mesh (§6.1) |
| WARNING: Acoustics harmonic: … fewer than 10 (linear) / 5 (quadratic) elements per wavelength | fluid mesh too coarse for the highest frequency | refine the mesh or lower the end frequency |
| WARNING: … microphone '…' is a face selection | microphone not a node selection | *Node selection* |
| alarm `MODELISA4_8` / `MODELISA8_13` | shell on a fluid face (coupling face and shell are separate cells), or two discrete elements on the same nodes | harmless (VH-06, VH-04c) |

## 8. Sources

- EDF R&D (2025). *code_aster 17.4, test cases* adlv100a (piston between a water column
  with a free surface and a closed air column: `3D_FLUIDE`, `FLUI_STRU`, `DDL_IMPO
  PRES`/`PHI`, `CALC_MODES`, VALE_REFE 13.8285 Hz), adlv100b/adls102a/fdlv112h
  (`ORIE_PEAU` with `GROUP_MA_INTERNE` = fluid), adlv100p, adlv312a (shell + fluid,
  `BANDE`, `COEF_DIM_ESPACE`), sdlv102a (`FORMULATION='U_P'`) and ahlv101a (`U_P_PHI`
  harmonic with `3D_FLUI_ABSO` and `ONDE_FLUI`: TEST_RESU reproduced in VH-01),
  ahlv100b (`VITE_FACE` with `3D_FLUI_ABSO`, `IMPE_MECA`: VH-01b) and ahlv302a
  (`DYNA_LINE` with `MATR_IMPE_PHI`), `share/aster/tests` of the installation; catalogue
  `affe_modele.py` (`FORMULATION` U_P_PHI/U_P/U_PSI, default U_P_PHI), `info_mode.py`,
  `extr_mode.py`, `norm_mode.py`, `dyna_vibra.py` (`MATR_IMPE_PHI`, `AMOR_FLUI`),
  `affe_char_meca.py` (`VITE_FACE`, `ONDE_FLUI`: real values only), `assemblage.py`
  (`IMPE_MECA`, `ONDE_FLUI`); `MacroCommands/dyna_line_ops.py` (`AMOR_FLUI='NON'` with
  `MATR_AMOR` and `MATR_IMPE_PHI`); elements `MEFL_*` (fluid, also pyramids) and
  `MEFS_FACE*` (coupling face) in `lib/aster/elem.1`.
- EDF R&D (2025). *code_aster 17.4, test cases* ahlv100a (wave guide, `RIGI_ACOU`,
  `MASS_ACOU`, `COMB_MATR_ASSE PARTIE='REEL'`, `CALC_MODES`; harmonic: `3D_ABSO`,
  `AMOR_ACOU`, `VITE_FACE`, `DYNA_VIBRA HARM`, `PRAC_ELNO`) and adlv101f
  (`AFFE_CHAR_ACOU PRES_IMPO`, `PRES=0j`), `share/aster/tests` of the installation.
- EDF R&D (2025). *code_aster 17.4, catalogue* `lib/aster/code_aster/Cata/Commands/`:
  `calc_modes.py` (`MATR_AMOR` only `matr_asse_depl_r`/`gene_r`), `dyna_vibra.py`
  (`HARM` `PHYS` with `matr_asse_pres_c`, `LIST_FREQ`, `EXCIT` `PUIS_PULS`/`PHAS_DEG`),
  `affe_char_acou.py`,
  `defi_materiau.py` (`FLUIDE`: `RHO`, `CELE_R`, `CELE_I`); elements `ACOU_HEXA8/20`, `ACOU_PENTA6/15`,
  `ACOU_TETRA4/10` in `lib/aster/elem.1`.
- Mecway Ltd. (2026). *Mecway Finite Element Analysis, Manual, Version 33*: chapter 6
  (analysis types, no harmonic acoustics), §6.9 Acoustic Resonance (§6.9.2 complex
  modes and the impedance term), §9.34 Fluid pressure, §9.35 Impedance, §17.13 Acoustic Analysis
  of an Organ Pipe.
- Kinsler, L.E., Frey, A.R., Coppens, A.B. & Sanders, J.V. *Fundamentals of
  Acoustics*. New York: Wiley. Not consulted locally; the formulas in §1.5 and §5.4 are
  checked in the verification (AK-01…05, AH-01…08); the column formulas of §6.4 in
  VA-01…04; the piston and wave formulas of §7.4 in VH-02…06.
