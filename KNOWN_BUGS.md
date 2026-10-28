# KNOWN_BUGS.md – known bugs in the code (develop)

Bugs that have been found but not yet fixed. A new bug gets a numbered item under the
right heading (the next free number, written as `52\.` so that Markdown does not
renumber it; ordered by number within a heading): file and function, what goes wrong,
and the status. Numbers are not reused, so that references ("KNOWN_BUGS 43") in code
and docs stay correct. Once a bug is fixed, remove the item in the same commit and
update the references.
Status: **confirmed** = checked in the code or with an offline run;
**suspected** = follows from the code, but has not been reproduced;
**question** = depends on behaviour of Mecway or Code-Aster that is not in the repo.

Comparing with Mecway: turn on "Mecway solve first as a check" on the start screen.
The bridge then writes `WorkDir/<model>_<run-id>_vergelijking.csv` (Mecway and
Code-Aster value per node) and logs the largest difference per variable.

## Deviations from Mecway (measured)

1\. **Hex8 is stiffer than in Mecway** (confirmed, `bridge_from_liml.py`
   MODELISATION='3D'). Mecway computes hex8 with incompatible modes (C3D8I in the
   CCX export, "Incompatible hex8 elements" in the analysis settings); Code-Aster
   does not have those. Measured with Code-Aster 17.4:
   - cantilever beam 100x10x10 mm, 10 hex8 (1 thick), 100 N: Mecway 0.1892 mm,
     Code-Aster 0.1234 mm (analytical 0.1905);
   - bar 11 mm with plasticity (250 MPa): Mecway 0.251 mm, Code-Aster 0.039 mm
     (hand calculation 0.251).
   `3D_SI` gave the correct displacements, but bending stress ~0 and wrong REAC_NODA
   (under-integration). Solution as an option: `elem_hex8` = "LINE_QUAD" (page
   Elements) lets Code-Aster make all linear solid elements quadratic
   (CREA_MAILLAGE LINE_QUAD); the same beam then gives 0.1886 mm. Only if nothing
   else stays linear (only solid elements, possibly shells with COQUE_3D) and not
   explicitly; with the default "3D" the bridge warns for hex8
   (`bridge_to_aster._resolve_line_quad`).
   With LINE_QUAD, nodal forces stay on the corner nodes: on hex20 these are
   point loads with local deformation (seen in a small hex20 test model: +21% at the
   loaded nodes, with pressure on the same face +0.04%); use a surface load.
   Hyperelastic material (GitHub issue #5): fully integrated hex8 locks
   volumetrically. Bonded rubber cylinder (684 hex8, Neo Hooke, K/G = 575), force
   at 3 mm: `3D` 368.5 N (= CCX C3D8), `LINE_QUAD` 132.3 N (= CCX C3D20),
   reference ~124 N (CCX C3D20R/C3D8I, mesh refined 2x); CCX C3D8R 181.8 N.
   `bridge_to_aster._resolve_line_quad` gives its own WARNING for hyperelastic
   hex8 with `3D`; `3D_SI` is not possible with `ELAS_HYPER` (`ELEMENTSSI_1`), so
   such an elset gets `3D` (`_hyper_hex8`).

2\. **Shell elements ~0.7% different from Mecway** (confirmed). Flat quad4 plate
   100x20 mm, 1 mm, fixed on one edge: displacements DKT (Code-Aster) and
   Mecway differ by 0.66%, rotations up to ~10%. Option `elem_shell` = "COQUE_3D"
   (linear shells via LINE_QUAD to QUAD9/TRIA7, with drilling rotation) gives
   0.03% / 0.83% on the displacements, the rotations deviate similarly; no
   formulation follows Mecway exactly. With a coarse mesh the difference is larger: wall
   1x1 m, 20 mm, 2x2 quad4, pressure: DKT 8% more deflection than Mecway (headless). COQUE_3D falls back to DKT if the shells share nodes
   with elements that stay linear (`bridge_to_aster._resolve_line_quad`).

3\. **Nodal stresses and von Mises different from Mecway** (confirmed in Mecway; deliberate
   choice). The bridge follows the Code-Aster standard: SIGM_NOEU (extrapolation of
   SIEF_ELGA to the nodes, averaged) and SIEQ_NOEU (von Mises per element, then
   averaged). Hex20 beam 100x10x10 mm with torsion and bending: displacements and
   reactions equal, nodal stresses at the surface up to ~12% lower than Mecway; at
   the torsion centre SIEQ_NOEU gives 7.5 MPa, Mecway (von Mises from the averaged
   tensor) 0.09 MPa. Do not "fix" towards Mecway (user's wish).

7\. **Stresses per element node stay from Mecway in the table route** (confirmed
   in Mecway). Only with `result_route` "tabel": `solution.set_variable()` writes
   only nodal values, the `<elementnodevariable>` (e.g. `stressxx`) of the last
   Mecway solve remains. The default route "liml" does write SIGM_ELNO/SIEQ_ELNO
   of solid elements (`bridge_to_aster._build_calc_champ_block`).

46\. **Buckling: negative buckling load factors and Mecway's shift** (confirmed with runs,
   `bridge_to_aster._calc_modes_block`). The bridge searches for the smallest |CHAR_CRIT|
   (`PLUS_PETITE`) and also shows negative factors (buckling under the reversed load;
   WARNING). Mecway only searches for positive factors above its *Shift point*: a
   column in tension gave 8.5e13 in Mecway (meaningless), in the bridge -10.36 / -23.32 /
   -93.27 (the compression buckling with a minus sign). Mecway's shift is a setting of its
   solver and is not used (only reported); searching around a buckling load factor
   is not possible (Code-Aster 17.4 ignores `OPTION='CENTRE'` for buckling). Rigid-body
   modes of a free model get a frequency of ~1e-4 Hz in the bridge, sometimes negative
   (numerically zero); Mecway writes 0 or a small positive number.

60\. **Isotropic material without Young's modulus: bridge E = 210 GPa, Mecway E = 0**
   (suspected, `bridge_from_liml.py`, material block: `youngsmodulus` with default
   "210000000000"). Seen with headless Mecway on a Frequency model in which one
   material had only *Speed of sound* and *Density*: modes of ~1e-7 Hz (E = 0). The
   bridge silently computes such a material as steel; only with a speed of sound (a
   fluid) does it give a WARNING outside `vibroacoustic_modes_3d`
   (`bridge_vibroacoustic.parse_vibro`). Without a speed of sound NOT checked.

62\. **Strongly curved hex20/wedge15: frequencies up to 0.8% higher than Mecway** (question,
   measured with Mecway's example Impeller, 66 hex20 + 21 wedge15 with midside nodes up to
   18% of the edge length off-centre). The sector as a plain modal model
   (`modal_3d`, without centrifugal force and cyclic symmetry) gave +0.02 ... +0.79%
   relative to Mecway (6 modes); the cyclic route (S10g) deviates by the same amount (+0.01 ...
   +0.92%). With straight hex20 the bridge equals Mecway (MP-07, CY-01, CY-05).
   Suspected: a different integration of distorted quadratic elements in Mecway
   or Code-Aster (NOT checked; which one is closer to reality, also not).

95\. **Thermal strain in shells: Mecway expands less than the bridge** (question, measured
   with Mecway 34 headless and Code-Aster 17.4). Plate 100 × 40 × 2 mm (4 × 2 elements),
   `fixed` on the edge x = 0, α = 1.2e-5 1/K, uniform +100 K (`temperature2` on all
   elements or `temperature3` on all nodes, the same in both programs): max u_x
   quad8 Mecway 6.68e-5 m, bridge (`COQUE_3D`) 1.224e-4 m; quad4 Mecway 9.37e-5 m,
   bridge (DKT) 1.236e-4 m. The free expansion is αΔT·L = 1.2e-4 m (the fixed edge
   only restrains the transverse strain, which if anything increases u_x). A free quad8 plate with
   ΔT = 1000 K/m · x gave u_x(L, 0) = 4.87e-5 m in Mecway versus exactly αgL²/2 = 6.0e-5 m.
   Solids do agree (TH-03, LS-08). Why Mecway expands less with shells has NOT been
   checked (plane stress, or the temperature through the thickness?). User docs: the bridge
   follows the theory, do not compare with Mecway here (Mecway_functionaliteit §2,
   Standaardinstellingen §4.4).

112\. **Buckling: Mecway's beam has no torsional buckling; the bridge is right** (confirmed,
   Mecway 34 headless and Code-Aster 17.4, `buckling_3d`, `POU_D_E`; verification BU-30/31).
   Fixed column L = 1 m, I 100/50/10/8 mm, 20 elements, 1000 N: bridge 109.72 / 987.46 /
   1230.44 / 2413.87, Mecway 109.72 / 987.46 / 1230.44 / 2743.03. Mecway's 2743.03 is not a
   torsional mode but the third flexural mode (25 × 109.72, the bridge's mode 6); Mecway's
   own beam gives no torsional buckling at all (doubling J or A changes nothing). The bridge's
   2413.87 = G·J·A/I_p (torsional buckling without warping, Timoshenko & Gere, 1961, sec. 5.3;
   `RIGI_GEOM` of `POU_D_E` has the term N·(I_y + I_z)/A, R3.08.01 sec. 6). Independent:
   the same column in hex20 (3000 elements) gives 2384.28 in Code-Aster, Mecway's own solver
   and CCX alike (2367.7 with 12000 elements): −1.2% from the bridge, because the exact J
   is 1.7% below Mecway's formula and the web distorts; with warping (`POU_D_TG`,
   C_w = 4.22e-10 m⁶) 2552.5 would be too high. Without warping the factor does not
   depend on the length, so it is a multiple eigenvalue (one per element; Sturm alarm
   `ALGELINE5_23`, the INFO line of `bridge_to_aster._buckling_beam_notes` explains it).
   Nothing to fix in the bridge; open sections with eccentric shear centre: item 115.

113\. **Buckling of frames with bending moments: Mecway's beam is too low, the bridge is right**
   (confirmed, Mecway 34 headless and Code-Aster 17.4; verification BU-32 … BU-34). L-frame
   (column along Z 1 m, girder along X 1 m, RectBar 40 × 10 mm, 100 N downwards at the end of
   the girder): bridge 17.27 / 44.53 / 122.44 / 151.95 / 155.45 (and −53.04 / −124.28 /
   −159.97 under the reversed load), Mecway 17.27 / 19.71 / 127.30 / 155.45 / 173.90. The
   same frame in hex20 gives 17.31 / 44.86 / 124.12 / 151.78 / 154.69 (Mecway's own solver,
   200 × 8 × 4 elements per member; on a 100 × 4 × 2 mesh Code-Aster, Mecway and CCX agree
   to 5 digits, also the negative −53.54): the out-of-plane mode of Mecway's beam is 56%
   too low. Code-Aster test case ssll105 (right-angle frame of Argyris, `POU_D_E`): bridge
   0.6813 / −1.0901 = the test (reference 0.68 / −1.088), Mecway's beam 0.4226 (F_X = −1)
   and 0.5525 (F_X = +1, instead of 1.088); a DKT shell model of that frame gives 0.703 in
   Code-Aster, Mecway and CCX. Cause: `RIGI_GEOM` of `POU_D_E` adds at each node the terms
   of moderate rotations (±M/2 between the twist and the bending rotations, R3.08.01
   sec. 6), so that a moment passes correctly through a joint where members meet at an
   angle; Mecway's beam lacks those terms. An own beam code reproduces both: without the
   terms 19.71 / 0.4225 / 0.5526 (Mecway), with them 44.53 / 0.6813 / 1.0901 (Code-Aster).
   A straight member (a cantilever under a transverse force) does not need them, hence
   the agreement there (127.9955). CCX's B32R (direct run of the L-frame) also gives a low
   20.90 (its rigid knot at the joint is linear); Mecway with solver CCX gives no buckling
   solution for beams headless. Nothing to fix in the bridge.

125\. **2D: pressure on curved quadratic edges, Mecway's resultant too large; the bridge is
   right** (confirmed, Mecway 34 headless and Code-Aster 17.4; `bridge_plane.py`, verification
   PL-03). Quarter ring a = 0.1 m, b = 0.2 m in Static 2D, plane strain, t = 10 mm, quad8 4 × 8
   with the midside nodes on the arcs, pressure 100 MPa on the inner arc. The resultant of a
   uniform pressure between (a, 0) and (0, a) is p·a·t = 100000 N per direction, whatever the
   shape of the edge: the bridge (`PRES_REP` on `SEG3`) gives exactly that, Mecway's reactions
   add up to 100161 N (+0.16%); u_r at the inner wall bridge −0.005%, Mecway −0.18% against
   Lamé. With straight edges (axisymmetric ring PL-04, plate PL-01 with traction on a straight
   edge) the bridge equals Mecway (≤ 1e-11). Mecway's example PressureVesselAxiSymmetric
   (curved head) differs by up to 0.9% in displacement for the same reason (suspected). Nothing
   to fix in the bridge; do not compare such models with Mecway.

## Translation that works differently from Mecway

8\. **Duplicate boundary conditions** (confirmed, partly caught). Mecway reduces
   overlapping conditions itself (manual v33 sec. 9.6), Code-Aster does not. Fixed:
   fixed next to skewed conditions, displacement, node rotation or velocity
   (SANS_GROUP_*, `bridge_to_aster._build_charges`); contact slaves
   (`_exclude_fixed_slaves`); a DDL_IMPO 0 that already falls under a symmetry/frictionless 0
   in the same global direction (`bridge_mesh._drop_covered_ddl`), and conversely the part of
   a symmetry/frictionless 0 that DDL_IMPO 0 on the same node already spans, also skew
   (`bridge_mesh._trim_covered_relations`; GitHub issue #9, MO-09). Two DDL_IMPO
   in the same load: Code-Aster takes the last one (only reported for different
   values). Reported with selections and DOFs, not fixed (`_report_constraint_overlaps`,
   rank test per node): constant next to time-dependent on the same DOF (ASSEMBLA_26),
   pinned support, couplings, frictionless/symmetry among each other with different
   relations, and skewed overlap.

9\. **Failure not for beams; kinematic hardening with the current plastic
   strain** (confirmed; `bridge_failure.py`, `docs/Bezwijken.md`). Code-Aster does not remove
   elements; the bridge gives failed elements (plastic strain above
   `#ASTER-BEZWIJKEN`, PLAS_TAB Eps_p_max or `failure_plastic_strain`) a very low
   stiffness and zero stress, in STAT_NON_LINE and DYNA_NON_LINE. That works for
   solid elements (PETIT, GDEF_LOG, SIMO_MIEHE) and shells (DKT: PETIT/GREEN_LAGRANGE;
   COQUE_3D: PETIT/GROT_GDEP), with as criterion the average over all
   integration points, for shells also over the sub-points through the thickness. Not done
   (message + skipped_loads): beams (Code-Aster only supports plasticity in
   multifibre beams, POUTRE0_61). With `VMIS_CINE_LINE` the strain comes from the back stress
   (X = 2/3 H εp, H = Mecway's tangent modulus): that is the current, not the accumulated
   plastic strain (WARNING), and without hardening (tangent modulus 0) nothing
   fails. OpenRadioss `/FAIL`: only
   /FAIL/JOHNSON with a fixed failure strain (D4=D5=0, D2·D3=0) in the material field becomes
   Eps_p_max; other /FAIL cards and /FAIL in the model definition are reported.
   Dynamic: only checked at the output times; implicit gives the alarm
   MECANONLINE4_50.

10\. **Contact pairs with shared slave nodes are merged** (confirmed,
   `bridge_mesh._merge_contact_zones`). Code-Aster forbids shared slave nodes
   between zones (CONTACT2_16); the bridge makes one zone of them (master = union,
   slave = union, largest friction coefficient) and logs that.

11\. **Large rotations: beams, prescribed rotations and rigid couplings** (confirmed).
   With `deformation` = GROT_GDEP the bridge chooses a large-displacement formulation per
   element type (`_deformation_for`). Beams `POU_D_E`/`POU_D_T` stay PETIT (WARNING;
   GROT_GDEP on POU_D_E did not converge); with `elem_beam` = `POU_D_T_GD` (STAPPENPLAN
   S20, only nonlinear static with large displacements, elsewhere POU_D_T) beams do compute large rotations
   (ELAS_POUTRE_GR; verification NL-80 .. NL-89). Not, or only partly: DDL_IMPO on
   DRX/DRY/DRZ (on nodes of POU_D_T_GD beams the total rotation vector, Code-Aster test
   case zzzz364a: a stocky beam 100 x 100 mm rotated rigidly through 90 degrees exactly,
   but a slender beam 10 x 20 mm, L = 1 m, stopped converging at 0.41 rad (rigid rotation)
   and 0.58 rad (end rotation), also with 5x smaller steps, while an end moment reached
   90 degrees: WARNING in `_warn_large_rotations`), LIAISON_SOLIDE (with
   TYPE_CHARGE='SUIV' not if a node has rotational degrees of freedom, CHARGES_36), and
   with POU_D_T_GD the rigid arms of an element offset and couplings (linear relations in
   the undeformed axes, KNOWN_BUGS 108; WARNING in `_warn_gd_linear_links`; with small loads
   offset equal to POU_D_T, couplings NOT verified); a flexible joint with only some
   rotations free stops with an ERROR (KNOWN_BUGS 106b), one with U, V and W free is exact
   (NL-90). Element failure in a model with POU_D_T_GD stops beforehand with an ERROR
   (`_check_gd_beams`): after the first failure the loop restarts with
   PREDICTION='ELASTIQUE' (CALCUL_37, no RIGI_MECA); with TANGENTE or EXTRAPOLE that step
   did not converge (MECANONLINE9_3, run 17.4). Not objective about a skew axis (runs 17.4,
   STAPPENPLAN S21): a frame of POU_D_T_GD beams with all translations imposed as an exact rigid
   rotation is exact about a global axis, but about the axis (1,1,0) it gets spurious section forces
   that depend on the step size (at 10 degrees max |M| = 6.0e-2 .. 6.4e-4 EI/L with 2 .. 16 steps)
   and about (1,2,3) it stops converging at about 60 degrees; the Newton residual of equal rotation
   steps grows with the accumulated rotation (incremental, path-dependent strain update; Fortran
   NOT verified). Force-driven cases with rotations about one global axis (NL-80 .. NL-90) are not
   affected; 3D large rotations with coarse steps can carry spurious forces. What does work: driving a rigid part with the
   exact rigid motion via #ASTER (FORMULE, docs/ASTER_regels_voorbeelden.md
   example 9). A bending model (profile around a die, with a roller) has been computed implicitly up to 90 degrees this way; the
   roller/profile contact still converges with difficulty there (roller coarse as slave: WARNING).

14\. **Thermal: transient scheme different from Mecway** (confirmed, `bridge_thermal`,
   `theta`). Mecway 33 computes Crank-Nicolson with the load at the end of the
   step (measured headless: `mecway.exe model.liml solve` with `<solutionfile>`);
   Code-Aster takes the θ-weighted average (default 0.57). With constant
   load, θ = 0.5 gives Mecway to within 1.5e-5 K; with a time table an
   O(Δt) difference remains (OscillatingHeatFlow max 1.4 K at θ 0.57, RMS 0.13 K). Steady state
   with a time table: Mecway's internal solver counts the table as 0, CCX takes t = 1 s;
   the bridge takes t = 1 s and warns with the internal solver. With a moving source
   (formula in x, y, z, t), Mecway's source therefore runs v·Δt/2 ahead: next to the source
   +4.6%, on the weld axis behind it −2.1% relative to the bridge at Δt = 0.05 s (WE-03; the
   bridge is within 1% of the analytical solution).

15\. **Thermal shells as PLAN with a thickness factor** (confirmed, choice).
   Code-Aster's thermal `COQUE` has three temperatures through the thickness and
   edge loads only on TRIA; the bridge computes shells as `PLAN` (depth 1)
   with f = t / t_ref on λ, ρc and the loads, with a separate sub-group per thickness.
   Shells in parallel planes other than Z = constant: the .comm rotates the mesh
   (MODI_MAILLAGE ROTATION) and the flux back; alarm MODELE1_53 remains and is
   harmless. Shells that are not all parallel: not translated (item 16).

17\. **Thermal strain: temperature within the element and in time** (confirmed, deliberate choice,
   `bridge_to_aster._build_temperature_field`). According to the manual (v33 sec. 9.25) Mecway
   computes per element with the average nodal temperature; Mecway 34 (own solver,
   headless) however interpolates the nodal temperature within the element, just like
   Code-Aster: a linear temperature distribution through the thickness of a free beam (one
   layer of hex20) gives the exact deflection in both (see LS-08b), with `temperature2` on
   node selections and with `temperature3`. The variation in time (L30, D31: `EVOL_THER`
   from the reference, constant from the first step or ramped without Quasi-static,
   a time table followed) is described in docs/Thermisch.md sec. 3.1 (NL-70..75, DY-70..72).
   Static, modal and buckling: a time history is dropped, just as in Mecway's own
   solver (Mecway 34 headless); Mecway with CCX takes the value at t = 1 s in S30.

19\. **Centrifugal force** (confirmed). Only a constant angular velocity (a
   time history is reported), no second centrifugal force (gyroscopic effect).
   Spin softening (Mecway: automatic in Nonlinear Static): ROTATION with
   TYPE_CHARGE='SUIV' in STAT_NON_LINE with large deformations, only if ROTATION
   is on solids only (tested: bar 0.1 m, extra reaction = ρAω²∫u). With shells
   (formulas of the initial position) and in dynamics the load stays fixed. Without shells
   ROTATION on the elsets, in a model with shells formulas per elset
   (FORCE_INTERNE/FORCE_COQUE/FORCE_POUTRE); nodal masses get FORCE_NODALE m w^2 r
   (`bridge_to_aster._centrifugal_loads`). Cables (tension only) never get
   centrifugal force (CALCUL_37 "MECABL2", no FORCE_POUTRE for cables): ERROR and
   reported. In a model with shells or POU_D_T_GD beams (formula route), trusses
   (BARRE) get FORCE_POUTRE as well (run with POU_D_T_GD: NL-86b; beside shells NOT
   verified); other elements with density (not solid, shell, beam or truss) do not get
   it (reported).

20\. **Multiple distributed loads on a beam** (confirmed,
   `bridge_to_aster._prepare_beam_loads`). Code-Aster sums loads with a distributed
   beam load (CALCULEL2_92, also in CALC_CHAMP SIPM_ELNO). The bridge divides the beams
   into disjoint groups (BRLP) with the sum; with a time-dependent line pressure
   everything in one AFFE_CHAR_MECA_F (gravity on beams as ρAg, elsewhere as force). Not
   yet: local and global line pressure on the same beam, and centrifugal with a
   time-dependent line pressure (ERROR), gravity with a history together with line
   pressures on beams (WARNING). FORCE_INTERNE/FORCE_COQUE in that path have not been
   checked with a run.

21\. **Bonded contact (LIAISON_MAIL)** (confirmed, `bridge_mesh._bonded`).
   `bondedelastic` becomes rigidly bonded (stiffness not translated, reported). Shell face
   (slave) on solid (master): only the displacements are coupled (MASSIF;
   measured equal to shared nodes). Mecway itself deviates here (measured headless,
   beam 1x0.1x0.1 m with a 10 mm plate bonded on top, end load): the internal
   solver does not connect the plate (plate at rest, deflection equal to without
   plate); with CCX the deflection drops to 0.869 of that without plate, Code-Aster
   (LINE_QUAD + COQUE_3D) 0.788, beam theory 0.785. Shell edges of one component on a
   solid: COQUE_MASSIF (rigid, also the rotations); edges of several components or
   mixed with faces: MASSIF, the edge then acts as a hinge (WARNING). Whether Mecway
   also connects a shell edge on a solid rigidly has NOT been verified. Beam ends as slave:
   reported and skipped. Linear shells that are master stay DKT, also with
   elem_shell = COQUE_3D (LIAISON_MAIL would otherwise drag in the DX of the QUAD9 centre node,
   CHARGES2_31, and the bridge does not know the midside nodes of LINE_QUAD; WARNING).
   An automatic
   tolerance of Mecway (0) does not become DISTANCE_MAX: Code-Aster couples all
   slave nodes, also far from the master face. Shell on shell (`COQUE`, also a
   shell edge on a shell face) does couple the rotations (rigid, LS-07); Mecway's own
   solver does not do that with a shell edge as slave (measured headless, Mecway 34:
   bonded strip and T-piece of LS-07 become a mechanism, tip 3.7e6 m). A
   quadratic shell (tri6/quad8) as master or a skewed/curved master is written
   by the bridge itself as `LIAISON_DDL` per slave node (`_bonded_relations`; LS-07f..k);
   with a skewed or curved master the bridge sets `NPREC` to −1 for that run (WARNING),
   because MUMPS otherwise wrongly reports `FACTOR_11` (fictitious drilling stiffness).
   Those relations project each slave node onto the master elements (preselection with
   bounding boxes; 500 slave nodes on 3600 elements: 1.3 s in CPython, in
   IronPython several times slower): noticeable for very large bonded faces.

22\. **Compression only** (confirmed). Hard (LIAISON_UNIL, like the internal solver),
   only in nonlinear analyses (MECA_STATIQUE stops with an ERROR), not in a
   model with contact2 (one DEFI_CONTACT per calculation; reported). On shell faces
   only the normal displacement, the rotations stay free.

23\. **Gap and tension-only elements** (confirmed). Gap (DIS_CHOC): no tension gap
   (U against node 1 -> 2), skewed U or coincident nodes (reported, element
   without stiffness); the 'force of open gap' of CCX is not used. Tension
   only (CABLE, GROT_GDEP): compressive stiffness 1e-4 E (Code-Aster EC_SUR_E). A
   straight cable without prestress has no transverse stiffness; the bridge therefore
   writes a small `N_INIT` = `cable_n_init_factor` x E x A (default 1e-6, INFO in the
   log), with which a straight cable under transverse load solves (Samples/SaggingCable
   with *Tension only*: 3.06798 m, Mecway truss 3.0680 m; with 0 singular, MECANONLINE9_4)
   and LS-54b/c do not change (< 1e-12 relative). Both only nonlinear.

34\. **PLAS_TAB: untranslated fields** (confirmed, `bridge_radioss.parse_plas_tab`).
   Kinematic/mixed hardening (C_hard > 0; 0 is isotropic, Altair /MAT/LAW36),
   Eps_t/Eps_m/Eps_f, fct_IDp and the E evolution (Fct_IDE/EInf/CE) are reported
   (WARNING) and computed as isotropic; F_smooth/F_cut/VP (strain rate) only INFO. A
   different unit system (`/BEGIN`, or E/RHO outside the SI range) is reported, not
   converted. Kinematic with a curve: VMIS_ECMI_TRAC is only exact for a
   bilinear curve, so not built in.

40\. **Trusses with large displacements** (confirmed with runs, `bridge_from_liml`
   `_split_trusses`). BARRE is geometrically linear in Code-Aster 17.4: GROT_GDEP is
   silently ignored (a bar that rotates rigidly by 30° gives the same normal force as with
   PETIT); the bridge warns. Samples/SaggingCable.liml (straight cable under transverse
   gravity) is therefore a mechanism: the run stops (singular, BRIDGE_ONVOLLEDIG). CABLE with EC_SUR_E=1.0 is a geometrically
   nonlinear bar (measured: rigid rotation N=0), but without prestress a
   straight cable stays singular; with N_INIT=2000 N SaggingCable gave 3.06797 m (Mecway
   3.0680 m). Not built in for trusses (EC_SUR_E=1.0 changes the material); for the
   same model with *Tension only* the bridge's default pretension (KNOWN_BUGS 23) gives
   3.06798 m.

43\. **Contact: hard and soft formulation differ from Mecway** (confirmed).
   `contact_algo` = STANDARD (Lagrange, default) allows no penetration; Mecway
   computes penalty. Samples/PipeClip loses contact with STANDARD (1.1 mm penetration
   at t = 0.8), AssemblyWithContact (Fixed_support) stops with MECANONLINE9_4 (pivot on
   LAGS_C); with PENALISATION (Mecway's stiffness) both follow Mecway (2..8% and −1.1%,
   headless). Configuration Quadratic_ramp of AssemblyWithContact (friction 0.5 +
   elastic support) does not converge in step 1 with penalty either (unexplained).
   Line contact between hex20 solids (verification NL-03a: two beams with their tips
   on each other) does not work with STANDARD: with the default INTEGRATION='NCOTES' (bridge,
   quadratic slave face) the edge penetrates between the integration points (contact force
   ~0) and the run stops at t = 0.028 with MECANONLINE9_4; with AUTO a pivot on LAGS_C
   of a corner node in the first step, also with master/slave swapped. PENALISATION is
   exact (NL-03b).
   Samples/BoltedJoint (S15, 28 Oct 2026): plate B is held only by friction contact and the
   bolt nut by frictionless contact; Code-Aster stops in the first step with MECANONLINE9_4
   (zero pivot on DZ of a plate-B node) with STANDARD and with PENALISATION, also with
   `SEUIL_INIT`, with `FORMULATION='DISCRETE'` and without the pre-tension section; Mecway/CCX
   solves it (penalty contact is active at zero gap). The same model with bonded contact
   instead of contact runs, but Mecway's displacements are then ~10x larger than the
   bridge's even without the pre-tension section (external force only); Mecway writes
   `*TIE ... POSITION TOLERANCE=0` there, possibly few tied nodes (question, NOT verified).

48\. **Modal: mechanism in a supported model** (confirmed with runs,
   `bridge_to_aster._calc_modes_block`). If K is singular while there are
   supports (e.g. a beam that is only held by a hinge), Code-Aster stops with
   `<EXCEPTION> ALGELINE3_81`; Mecway gives the rigid-body modes at 0 Hz (same model:
   Mecway 0 / 0 / 0.0007 / 73.277 / 109.916 / 237.467 Hz). The bridge uses the
   shifted search frequency only without any support (free-free); with a
   negative `modal_shift_hz` (e.g. -500 Hz) the bridge gives the same values as
   Mecway. Always shifting does not work: a fixed factor far above the first mode
   gave not a single mode with a fine hex20 mesh (ALGELINE5_49/3_78).

53\. **Nonlinear buckling: limits of CRIT_STAB and the imperfection** (confirmed with
   runs, `bridge_to_aster._crit_stab_kind`, `_imperfection_blocks`;
   docs/Modaal_en_knik.md sec. 5). Mecway has neither (own input).
   (a) With large displacements (the default for solids and COQUE_3D; one elset is
   enough) `CHAR_CRIT` of CRIT_STAB is not a load factor but −(smallest eigenvalue
   of K_T); the bridge estimates the buckling point linearly from the last two steps (NK-02a,
   last step at 0.9 Pcr: +0.4 %; the same column with the last step at 0.27 Pcr:
   +4.7 %, the series is slightly curved). SIMO_MIEHE NOT
   verified. (b) The imperfection is always the linear buckling mode under the loads at
   the end time (follower pressure there as a fixed load); not with contact, compression
   only, gaps or tension only (ERROR), not in dynamics. (c) Beams and DKT/DST stay
   geometrically linear: there the imperfection does not amplify (WARNING). (d) The
   displacements in Mecway are relative to the imperfect shape; the imperfection itself is
   not sent to Mecway as a field, nor is the buckling mode of CRIT_STAB (`MODE_FLAMB`).
   (e) No arc-length method (`PILOTAGE`): with a load as a time table the run stops
   at the limit point (`MECANONLINE9_7`, NK-04).

82\. **Nonlinear: back-and-forth plasticity with the default deformation does not converge
   on reloading in reverse** (confirmed with an offline run, `bridge_to_aster.
   _deformation_for`; found in S8b). Bar 0.1 × 0.01 × 0.01 m, 2 hex8, bilinear
   plastic (yield stress 250 MPa, tangent modulus 10 GPa), prescribed elongation 0 →
   +0.6 → −0.6 → 0 mm (t = 0..3 s, step 0.25 s), symmetry planes (model of VM-11a
   without `deformation = PETIT`): with the default `GROT_GDEP` (plastic solid →
   `GDEF_LOG`) `STAT_NON_LINE` stops at t = 2.29 s (`MECANONLINE9_7` after halving 7
   times, `BRIDGE_ONVOLLEDIG`); with `PETIT` the same bar runs through (VM-11a).
   Cause not investigated (GDEF_LOG when the strain reverses, or the Newton settings).
   Advice in docs/Vermoeiing.md §1.9: `deformation = PETIT` for back-and-forth plasticity.

83\. **XFEM: K_I from `CALC_G_XFEM` on a curved front a few percent too high**
   (confirmed with runs, Code-Aster 17.4; `bridge_xfem._warn_curved`; verification BR-10).
   Circular crack (penny crack, a = 20 mm) in a block under tension, hex8, front
   running obliquely through the elements: K_I of `CALC_G_XFEM` (`OPTION='CALC_K_G'`) at the middle
   of the front +5.3 % relative to 2σ√(a/π) at h = a/20, +10 % at a/10 and +15 % at a/5;
   on the same mesh K_I of `POST_K1_K2_K3` +1.6 % and K from G +1.0 %
   (docs/Breukmechanica.md §7.4). On a straight front (BR-07..09, BR-12)
   `CALC_G_XFEM` is within 0.3 %. Cause suspected to be the missing curvature correction
   of the interaction integral (the meshed crack has it with `FORM_FISS='CERCLE'`:
   forma07a +5.6 % → +0.1 %); that `CALC_G_XFEM` has no curvature correction has NOT
   been checked in the U-doc. With CIRKEL/ELLIPSE the bridge gives a WARNING and advises
   `K1_POST_K` or K from G. In the verification BR-10 tests this K_I with the same 5 % as
   the other XFEM checks; the deviation counts as BEKEND.


106\. **Flexible joint: constraint on an element selection, large rotations**
   (confirmed resp. suspected, `bridge_mesh._flexible_joints`). The beam end with
   a joint gets its own node at the same location, coupled to the Mecway node with
   `LIAISON_DDL` (verification LS-51, equal to Mecway). (a) A fixed
   constraint (fixed, displacement, ...) on an *element selection* or component that contains the
   element with the joint also fixes that own node in Code-Aster (`GROUP_MA`);
   together with the coupling that is double and Code-Aster stops with `FACTOR_11` (seen in
   a run: fixed on the end elements, joint on an end face). Put the constraint on
   nodes or faces (then only on the Mecway node, like Mecway); WARNING before the run
   (`bridge_mesh._warn_joint_element_constraints`). Not always fatal: two offline runs of
   LS-51a variants (fixed on elements 6+7 with the joint at N7; fixed on element 10 with the
   joint at its end N10) ran without FACTOR_11; in the second the Mecway node N10 kept its free
   rotation about Z (only the own node is in the `GROUP_MA`), whereas Mecway fixes the nodes
   of the element. Solution (NOT
   verified): the own nodes as `SANS_GROUP_NO` for constraints on `GROUP_MA`.
   (b) The coupling of the rotations is fixed in the local axes of the undeformed
   element: with large rotations (`GROT_GDEP`) the axes do not rotate along. A fixed-axis
   tie of two rotation vectors is not a hinge at finite rotation: a rigid rotation of
   1.1 rad plus an allowed hinge rotation of 0.6 rad gives 0.33 rad on a retained
   component, for every one of U, V, W, UV, UW and VW (kinematic counterexample of the fork
   by MishalTPC, `check_selective_release_objectivity.py`, recomputed). Mecway does not
   support the joint in Nonlinear Static (manual v33 sec. 9.12). Only relevant with
   `elem_beam` = `POU_D_T_GD` (other beams stay PETIT). A joint with U, V and W free only
   ties DX, DY, DZ and is exact (NL-90, NL-90b, after the fork's
   `check_nonlinear_releases.py`); a joint with only some rotations free on a POU_D_T_GD
   beam stops before the run with an ERROR (`bridge_to_aster._check_gd_joints`, choice of
   the user). Solution (open, NOT verified): a hinge in the co-rotating frame, as the fork's
   commit fa91375 tries for V/W. Tried 22 Oct 2026 (STAPPENPLAN S21): a short `POU_D_T_GD`
   stub per joint with near-zero IY/IZ/JX in the released directions works as a hinge in
   plane (hinged elastica up to 2 P_cr within 0.23 % of the ideal hinge and the elastica),
   but the objectivity benchmark (rigid rotation about a skew axis) already fails for
   `POU_D_T_GD` without stub (KNOWN_BUGS 11), so the ERROR stays.
   Status: (a) confirmed, open; (b) refused with an ERROR.

107\. **Line3 beams and trusses: two straight SEG2 cells** (confirmed, choice;
   `bridge_mesh.write_mesh`). Code-Aster has no quadratic beam element; each
   line3 element is split at the midside node. A curved line3 element (midside node
   not on the chord) thus becomes a kink of two straight pieces, each half with its own
   orientation; Mecway (only with CCX, B32R) computes the curved shape (WARNING when the
   midside node is more than 0.1% of the length off the chord, `bridge_mesh._line3_bow`).
   Exact for a straight
   beam (verification LS-50). Mecway's CCX result itself is 2–3 % below
   Euler theory (B32R expanded as one C3D20R over the cross-section; the same beam with line2
   in Mecway's own solver is exact); a round bar (SECTION=PIPE with inner radius 0)
   is not computed by CCX there ("nonpositive jacobian").
   A line3 truss (`BARRE`) is split the same way; its midside node is tied across the
   chord to the mean of the end nodes (`bridge_mesh._line3_truss_links`; verification
   LS-54, MO-08). A direction that a fixed support, pinned support or displacement fixes
   on all three nodes is skipped (else the matrix is singular). A *symmetry* or
   *frictionless* condition counts only with explicit global DX/DY/DZ: its per-node
   directions are made later in `write_mesh`, so a plane line3 truss held out of plane
   only by symmetry or frictionless may still stop with a singular matrix (zero pivot)
   (suspected, not reproduced). Solution: hold it with a displacement uz = 0 instead.

108\. **Element offset: small rotations, values at the nodes and combinations**
   (confirmed, `bridge_offset.py`). Beams and COQUE_3D shells (tri6/quad8 or the option
   COQUE_3D) with an element offset lie on their own nodes, with a rigid
   arm per node as `LIAISON_DDL` (linear). (a) With `DEFORMATION` = `GROT_GDEP` the arm stays
   linear (small rotations, like LIAISON_SOLIDE in KNOWN_BUGS 11; WARNING for shell arms,
   `bridge_to_aster._warn_linear_couplings`, and for beam arms with `POU_D_T_GD`,
   `_warn_gd_linear_links`); DKT/DST with
   `EXCENTREMENT` not. (b) Stresses of the offset element are placed on the
   Mecway node in Mecway; if that node already has a value itself (other element), that value stays
   (`aster_results_export._offset_values`). (c) Mecway 34 itself gives a different result with a *Fixed
   support* on a node selection than on the faces of the same
   model (LS-63 model with 24 beam and 12 x 2 quad8 elements: twist angle 0.1117 versus
   0.1046 rad, lateral displacement +1.6 versus −10.9 mm; the bridge gives 0.1092 rad
   and −11.4 mm in both); checked with the example itself and LS-63 (faces, equal to Mecway).
   (d) A beam element with both an offset and a flexible joint: in linear static and modal
   the joint sits at the end of the rigid arm, between the offset node and the element, as in
   Mecway 34 (Mecway node -> arm -> joint -> element; LS-52a/b/c equal to Mecway in deflection
   and rotations). In other analyses
   and on a line3 element the joint is not translated (WARNING in
   `bridge_mesh._flexible_joints`), the element is rigidly attached to the arm. The joint's own
   node lies in a BROFL node group with the Mecway node, so its values go to that node like those
   of the other offset nodes (element values at the jointed end NOT compared with Mecway). An offset beam
   and a beam with a joint at the same node do work (LS-52b, equal to Mecway). (e) Bonded contact on shells with an offset: the
   slave nodes (always the Mecway nodes) are coupled to the nodes of the master
   (EXCENTREMENT, or the own relations for quad8/tri6), but with `LIAISON_MAIL` on a
   master on its own nodes (solid on a quad8 shell, `MASSIF_COQUE`) to the
   offset face (WARNING with the face used, `bridge_mesh._bonded`). What Mecway
   does has not been checked. Shell on shell with an offset on own nodes: NPREC = -1
   (otherwise wrongly FACTOR_11; LS-66). (f) A load on edges of offset shells
   (face selection) is applied by Mecway on the offset edge (measured: tension on the edge does not bend the
   strip), by the bridge on the nodes (`FORCE_ARETE` on the edge cell, also with
   EXCENTREMENT): an extra moment w x F per length (LS-67, WARNING in
   `bridge_offset._report_edge_loads`). A load on a node selection acts on
   the nodes in both (LS-60).
   Status: (a) and (b) left as is; (c) and (e) **question** (behaviour of Mecway); (d) outside
   linear static/modal and line3, and (f) confirmed, open.

115\. **Buckling of T, C and L beams misses flexural-torsional buckling** (confirmed,
   Code-Aster 17.4, `POU_D_E`/`POU_D_T` with `SECTION='GENERALE'` from
   `bridge_from_liml._profile_props`; verification BU-35/36). The beam takes torsion about
   the centroid and without warping (no `EY`/`EZ`, no `JG`). Fixed column L = 1 m, C
   100 × 50 × 6 mm, 1000 N: bridge 136.02 / 616.43 (G·J·A/I_p, multiple) / 864.25; hex20
   (3600 elements, Code-Aster = Mecway's own solver = CCX) 135.41 / 393.03 / 1090.36;
   thin-walled theory with shear centre and warping (Timoshenko & Gere 1961 sec. 5.3)
   386.1. The coupled mode is 57% too high, so the beam is unsafe here. Mecway's own beam
   with a C profile gives no solution headless. The bridge warns in buckling for T, C and
   L elsets with `POU_D_E`/`POU_D_T` (`bridge_to_aster._buckling_beam_notes`) and names
   the option: `elem_beam` = `POU_D_TG` (STAPPENPLAN S19, `bridge_warping.py`) has the
   shear centre (`EY`, `EZ`), `JG` (C_w), the Wagner terms and the warping DOF `GRX` at
   supports (setting `beam_warping`): the same column 384.98 (BU-38, −0.29% from the
   theory, −2.0% from hex20), ssll103a equal to `VALE_CALC` (BU-41). Status: open for the
   default `POU_D_E` (kept like Mecway's Euler beam); solved with the option. A *General
   section* without an `#ASTER-SECTIE` line has no shear centre or C_w even with
   `POU_D_TG` (WARNING).

119\. **Mass check without the mass for `POU_D_T_GD` beams** (confirmed, Code-Aster 17.4,
   `bridge_to_aster._static_check_block`). `MECA_POU_D_T_GD` cannot compute `POST_ELEM
   MASS_INER` (`CALCUL_37`), and Code-Aster writes that exception into the .mess before
   Python catches it, so the bridge would report the run as failed. For models with
   POU_D_T_GD beams the mass part is therefore skipped (INFO); the sum of the reactions
   is still reported. Possible improvement: mass per group without the GD beams (their
   mass from rho·A·L).

123\. **Nodal reactions of `POU_D_TG` beams are off** (confirmed, Code-Aster 17.4,
   `CALC_CHAMP FORCE='REAC_NODA'` on `MECA_POU_D_TG`; WARNING in
   `bridge_warping.note_reactions`). Cantilever L = 1 m, 10 elements, `CERCLE` R = 10 mm,
   100 N at the tip: `POU_D_TG` gives 103.01 N at the clamp, −3.01 N at the loaded tip and
   −0.301 N·m reaction moment at every free node (sum of all reactions 100 N, so
   `BRIDGE_STATREAC` is right); `POU_D_T` on the same model gives 100.000 exactly, and
   `POU_D_TG` with `AY` = `AZ` = 1e-6 too (runs 28 Oct 2026). The error grows with the
   shear flexibility of the element (RectBar 10 × 20 mm, LS-50a: 104.9 N; LS-62 with short
   offset beams: 140 N). Displacements, section forces (`EFGE_ELNO`, LS-30/NL-32 exact)
   and buckling factors are right. Cause inside Code-Aster (`FORC_NODA` of
   `MECA_POU_D_TG`) NOT verified. Workaround: reactions with `elem_beam` = `POU_D_T`.

## Open questions (Mecway behaviour not checked)

27\. **Not verified in a .liml** (question). Constraint equation: `constant`
   (element or attribute; the bridge reads both) and the DOF names rx/ry/rz (derived
   from the string order in mecway.exe); rotational inertia: axis 1/2 = X/Y (only 3 = Z
   seen); more than one node gives an ERROR (mecway.exe: "can only be applied to a
   single node"). Rayleigh damping only on the whole model and not on discrete
   elements (Mecway: α on every node with mass, manual par. 9.26). Confirmed: the
   Rayleigh XML (DampedVibratingStrip) and the gap attributes
   `initialclearance`/`openforce` (mecway.exe).

37\. **Second run in the same session: `solution` after `mw.open`** (question,
   `MecwayAsterBridgeMain`). The main window stays open, so a second run uses
   the `solution` that Mecway gave at the start of the script, while run 1 reopened the
   model with `mw.open`. Only relevant for route `tabel` and "Mecway solve first as a
   check" (comparison). Whether Mecway carries that object along is not stated
   in the API documentation; if in doubt, restart the bridge.

38\. **Main window non-modal: other Mecway actions not checked** (question,
   `bridge_gui.run_settings_dialog`). The window uses `Show()` with its own message
   loop (`Application.DoEvents`), so Mecway stays usable while it is open. A second
   start of the bridge is refused (`bridge_gui.claim_instance`, named semaphore per
   Mecway process; checked in Mecway 34 on 16 October 2026). Whether Mecway allows
   everything else during the loop (e.g. opening another model) has not been tested.

41\. **Explicit: TCHAMWA with a variable step not checked** (question,
   `bridge_to_aster._explicit_accelerations`). In explicit dynamics (only
   `FORMULATION='ACCELERATION'`) the bridge converts imposed displacements, rotations,
   velocities, frictionless (`FACE_IMPO`, `LIAISON_OBLIQUE`) and the constant of a
   constraint equation into the acceleration imposed by the scheme (DIFF_CENT:
   DY-03b, DY-20a-c). The TCHAMWA series is derived for a fixed step; with
   different steps per interval (kinks that are not a multiple of the step) it
   has NOT been checked with a run.

47\. **Springs and dampers: not compared against a Mecway solution** (question). The bridge
   applies k and c along the element's own axis (DISCRET `REPERE='LOCAL'`; previously
   they acted in global X, even along Y: verification LS-06, now exact). This follows
   Mecway's CCX export (`*ELEMENT,TYPE=SPRINGA` = axial spring, string in mecway.exe).
   Headless, Mecway could not solve a hand-written spring (line2 + Spring material):
   the internal solver ignored it (deflection equal to that without the spring; a
   separate spring gave a singular system) and CCX gave no solution. To be checked
   with a spring created in the Mecway GUI. Update 28 Oct 2026 (S15b): two hand-written
   springs in series solve in Mecway 34's internal solver and equal the bridge exactly,
   along X and inclined (PT-09/10, static), when the end nodes are held with
   *Displacement* in X, Y and Z; with `<fixed>` on the node selection Mecway did not hold
   those spring-only nodes (singular, displacements ~1e10 m), which may be the singular
   system above. Springs in Buckling: Mecway gives a tensioned spring a geometric
   stiffness, DIS_T does not (measured with a pretensioned spring, KNOWN_BUGS 124);
   suspected for any spring with an axial force in Buckling and modal with prestress.

116\. **Element orientation card: parts not compared with Mecway** (question,
   `bridge_orientation`). Measured headless with Mecway 34 on hand-written cards (Mecway
   writes them back unchanged in its solution file): beams with vector, angle, formulas,
   a card on part of the elements, overlap and the refusals (MO-31, LS-79–82, BU-25).
   NOT compared: a card created in the Mecway GUI (the XML form is the same as Mecway
   writes it), the U axis of a card on shells against Mecway's own `forceperlength*`/
   `moment*` (Mecway headless only wrote displacements; LS-31d checks it against the
   attribute variant and theory), a card on gaps, and the "element centre" of a formula
   for quadratic elements and shells (the bridge takes the mean of all element nodes;
   for line2 that is Mecway's result, LS-81).

118\. **Results after `DVP_2` not seen in a real DVP_2 run** (question,
   `bridge_failure.PARTIAL_EXCEPT`, GitHub issue #5). The job now keeps the archived
   steps after any Code-Aster error in the step loop. Checked with Code-Aster 17.4 on an
   `<F>` error from the element computation (`FONCT0_9`, step 12 of 20: `res` held
   t = 0..0.5, post-processing and results file complete) and in the source
   (`ExecuteCommand.exec_` publishes the result on every `AsterError`). A real `DVP_2`
   could not be provoked offline: a Neo Hooke cube (hex8, 1 or 27 elements) converged in
   20 steps to λ = 0.02, through inversion (λ = -0.5) and at 300 shear strain. Whether the
   structure is still complete after a floating point exception (signal, not `utmess`)
   is therefore NOT verified.

120\. **Hysteretic damping: not on all discrete elements, stresses not checked** (question,
   `bridge_harmonic`, S26). The loss factor eta (`loss_factor`, `#ASTER-HYST`) is applied
   to materials and springs, not to elastic supports, dampers or point masses. Whether
   `CALC_CHAMP` includes eta in the stresses of a harmonic result is NOT verified; if not,
   the stress amplitude is low by a factor sqrt(1 + eta^2) (0.5 % at eta = 0.1).
   Displacements are verified (HR-06a..d).

## Not translated (the bridge reports it at the end of the run)

4\. **Loads and boundary conditions the bridge does not know** (confirmed). Supported
   are fixed, pinnedsupport, frictionless, displacement, noderotation, velocity
   (dynamics), force, moment, surfacepressure, gravity, traction, linepressure,
   hydrostaticpressure, elasticsupport, compressiononly, symmetry, centrifugal,
   mass2, rotationalinertia, constraintequation, flexiblejoint, offset (element
   offset), rayleighdamping, temperature2 and temperature3 with
   thermalstress, nodesurfacecoupling (rbe3/rigidbody), contact2 (unilateral and
   bonded, no self-contact), materials Gap/Damper/TensionOnly and an
   initial velocity; OpenRadioss material PLAS_TAB (`bridge_radioss.py`); in
   acoustics fluidpressure 0 (`bridge_acoustic.py`, item 55). Other tags
   with a selection (self-contact, cyclic symmetry outside a modal analysis (item
   61), pre-tension, ...),
   OpenRadioss cards except /FUNCT (e.g. /RBODY, /BCS, /IMPDISP), other
   OpenRadioss laws and VOID materials end up in `model_data["skipped_loads"]`.
   Via `#ASTER` lines the user can add Code-Aster commands themselves.

5\. **Loads on beam side faces and frictionless with displacement on curved
   shells** (confirmed). Pressure and traction on shell edges (length × thickness, in the
   shell plane) and beam ends (cross-section A) become nodal forces; frictionless on
   curved shell faces and shell edges becomes LIAISON_OBLIQUE per nodal normal
   (`bridge_mesh._edge_loads`, `_frictionless_per_node`). Headless against Mecway:
   pressure on a shell edge exactly equal, traction across the edge 0.5% (DKT, item 2);
   frictionless per nodal normal not computed against Mecway. Not yet: loads on the side face of a beam (use
   an element selection), frictionless with normal displacement ≠ 0 on curved
   shells/shell edges, hydrostatic pressure on shell edges. With LINE_QUAD,
   new midside nodes get no frictionless.

6\. **Kinematic hardening: no equivalentplasticstrain; non-linear
   kinematic curve** (confirmed). Translated: isotropic hardening curve
   (VMIS_ISOT_TRAC), BilinearIsotropic/-Kinematic (ECRO_LINE with
   D_SIGM_EPSI = E H/(E+H), H = Mecway's tangent modulus as plastic modulus;
   VMIS_ISOT_LINE/VMIS_CINE_LINE, perfectly plastic with tangent modulus 0),
   RambergOsgood (sampled curve, VMIS_ISOT_TRAC; incremental, on unloading
   different from CCX) and a Kinematic curve with linear hardening (VMIS_CINE_LINE,
   `bridge_from_liml._kinematic_curve`). A non-linear Kinematic curve is
   reported and computed elastically. With kinematic hardening no
   equivalentplasticstrain goes to Mecway (VARI V1 is the back stress there), but
   EPSP_NOEU does. Plasticity on beams is computed elastically (WARNING; Code-Aster knows
   plasticity only in multifibre beams). ('Simple' is not a plasticity type but
   the type of `<density>`.)

16\. **Thermal: not translated** (confirmed, `bridge_thermal.py`). Beams /
   fin elements (Code-Aster has no thermal 1D element; FinConvection.liml
   therefore does not run), shells that are not all parallel, fluid network
   (`forcedconvection`, `massflowrate`; CoolantChannel.liml stops with "temperature
   undetermined"), cavity radiation, formulas for convection/radiation on a shell face,
   a formula in x, y, z for a total `heatflow` or as initial temperature, formulas
   in material properties, unilateral contact and couplings (node-surface coupling)
   in a thermal analysis (bonded contact is supported: docs/Thermisch.md par. 3; not in
   a model with solids and shells together). A
   `temperature2` with `starttime`/`endtime` is imposed for the whole analysis. (Formulas
   in the other thermal loads and temperature-dependent λ/c are translated,
   docs/Thermisch.md par. 3.)

49\. **Modal: limits of the prestress and of the complex modes** (confirmed
   with runs, `bridge_to_aster._prestress_plan`). Prestress from loads
   (stress stiffening, `modal_prestress`) works like Mecway (verification MP-01..07).
   Deviations: (a) a rotating **beam** (`POU_D_E`, centrifugal) gives in the
   plane of rotation up to 0.5% lower frequencies than Mecway (MP-04: 20.795 vs 20.903 Hz;
   an independent FE calculation with consistent Hermite matrices gave 20.918 Hz), out of
   plane equal, with hex20 also equal in plane (MP-07): suspected Code-Aster's
   `RIGI_ROTA` of beams (NOT verified in the source code). (b) Centrifugal force
   with **shells** (formula load, no `ROTATION`) or on **nodal masses**: no spin
   softening (WARNING). (c) A **membrane with artificially small E** (Mecway's
   VibratingMembrane: E = 0.001 Pa, tri6 → `COQUE_3D`): the rotational degrees of freedom
   without stiffness give spurious modes (0.33 and 2.04 Hz, effective mass 0) and
   Sorensen finds no mode with `PLUS_PETITE` (`ALGELINE5_49`); with search frequency
   2 Hz the drum mode comes out at 2.00746 Hz (Mecway 2.00746), with the spurious modes in between.
   Damping: not by default (like Mecway, measured headless: V30 ignores Rayleigh and
   gives no solution with a Damper); with `modal_complex` complex modes
   (`bridge_modal_damping.py`, verification MC-01..05). Their limits: only the shape
   (real part) goes to Mecway, no stresses per mode; overcritically damped and rigid
   modes are missing (ALGELINE5_79); with dampers (non-proportional) the effective
   mass from the real part is an approximation (MC-03: sum 107%); no hysteretic
   damping; the `decayrate` and f_d in the Mecway GUI NOT checked (the API reads f_d and the shape).
   Cyclic symmetry: item 61. The effective
   mass for the rotations is computed by the bridge itself (about the origin, like Mecway; fraction
   of the total inertia incl. constrained nodes, Mecway divides by the free ones); in
   Mecway (*modal effective mass (fraction)*, S12) therefore Code-Aster's fraction is shown,
   not Mecway's; Mecway 34's GUI shows the bridge's own variable
   `cumulativeeffectivemassfraction*` as 6 red items per mode with truncated names (seen
   22 Oct 2026; Mecway stores it); stresses per mode
   only for modal (`fields`), not per buckling shape.

51\. **Error estimator: only linear static and solid elements** (confirmed,
   `bridge_to_aster._error_estimator_block`, `bridge_mesh._free_faces`,
   docs/Foutschatter.md). `CALC_ERREUR` ERME only with `MECA_STATIQUE` and only on
   solid elements; not with non-linear, dynamics, modal, buckling and thermal (ERTH),
   not on shells and beams. Missing in the estimator: point loads (`FORCE_NODALE`, also
   a moment on faces), loads on shells/beams/shell edges and hydrostatic pressure
   (formula); there and at a transition solid → shell/beam the boundary is
   stress-free for the estimator (estimated error too large). Faces with symmetry, frictionless or
   elastic support have no boundary term (like a constrained boundary). Two face loads of
   the same kind on one face: the estimator takes one of them into account (WARNING). A face counts as
   constrained if all its corner nodes lie in a node selection of an imposed displacement,
   even if that fixes only one direction. For an (almost) stress-free
   model the global relative error is meaningless (TH-03a: 64%). `FORCE_FACE` counts
   in `ERME` with the opposite sign (measured); the bridge reverses it in the load of
   the estimator (`_erme_force_face`), only the normal component counts in the boundary term.
   The adaptive refinement inherits these limits (item 65).

54\. **Response on modal basis and harmonic response: limits** (confirmed,
   `bridge_dyna_modal.py`, `bridge_harmonic.py`, docs/Respons_op_modale_basis.md).
   Mecway D30 with Mode superposition becomes `CALC_MODES` + `DYNA_VIBRA` GENE
   (verification MD-01..07, equal to Mecway). Not translated (ERROR with the solution
   `dyna_impl_3d`): an imposed displacement or rotation <> 0, also with a
   time table (requires static modes / `MULT_APPUI`), an initial velocity
   (`ETAT_INIT` on modal basis), thermal strain, dampers (Mecway neither) and
   output times that do not lie on a regular grid from 0. Accelerations and
   reactions do not go to Mecway. Loads from `#ASTER-EXCIT` count only as
   constraint (in `ASSEMBLAGE`). The static correction (`static_correction`) is exact with
   a constant load (MD-06b) and with a table measured only outside the regression
   (console, 1 mode, sine at 0.5 f1: 0.13% relative to 12 modes, without
   correction 2.0%).
   Harmonic response (`harmonic_3d`, own analysis: Mecway has no harmonic
   analysis type; verification HR-01..06): not translated (ERROR) an imposed
   (base) motion <> 0, dampers on modal basis (supported with `harm_basis` PHYS),
   `modal_damping` with PHYS, thermal strain and non-linear parts; not
   built: a loss factor on discrete elements other than Mecway springs
   (the loss factor itself is built, HR-06), stresses in
   shells and beams (only displacements/rotations), reactions and element
   nodal stresses. Without damping and with a list, a frequency may fall on
   an (infinite) resonance; the bridge only warns that there is no damping.
   A uniform base acceleration as gravity (relative motion) is theory, NOT
   checked with a test case. Mecway GUI: the frequencies come as `<mode
   frequency>` with e.g. `displx`/`displix`/`displamp*`/`displphase*`; Mecway's API
   reads them (headless script on HR-02a), the display in the GUI (list *Mode 1..n*,
   contour, animation without decay rate) has NOT been checked (question).

55\. **Acoustics: 2D, acoustic displacement and media with different density not
   translated; limits of the impedance** (confirmed, `bridge_acoustic.py`,
   `aster_acoustic_complex.py`, docs/Akoestiek.md §3). Cavity modes with rigid walls and
   pressure nodes (*fluid pressure* 0) are equal to Mecway (verification AK). *Impedance*
   (S2b): complex modes with frequency, *decay rate* and `pressure`/`pressurei` (the
   quadratic eigenvalue problem with scipy in the job, because `CALC_MODES` takes `MATR_AMOR`
   only as `matr_asse_depl_r`/`gene_r`); equal to Mecway ≤ 1e-8 and to the
   analytical tube (verification AI). Limits: a frequency-dependent Z not (nor
   Mecway); the list of modes may differ from Mecway in the 0 Hz modes (Mecway drops
   them randomly due to round-off noise, the bridge always gives them once); the scaling
   of P differs (Mecway arbitrary, the bridge P^H M P = 1); no Code-Aster result
   (no MED export, `#ASTER-POST` has no `res`); the factorisation (scipy `splu`) has been
   measured up to 13,000 nodes (14 s), larger models NOT verified (memory).
   Mecway's API reads the modes (headless script: `modes()`, `frequency`, `node_value`
   of `pressure`/`pressurei`; the decay rate has no API). The
   display of the complex modes in the Mecway GUI (decay rate under *Solution*,
   animation of `pressure` + `pressurei`) has NOT been checked (question). Also not:
   Acoustic Resonance 2D (A20, ERROR), Mecway's *acoustic displacement* as a field, contact,
   couplings and constraint equations in acoustics (ERROR, skipped_loads), pyramids.
   Code-Aster's `RIGI_ACOU`/`MASS_ACOU` do not contain the density (measured): at an
   interface dp/dn is continuous, correct only for equal density; media with
   different density: ERROR. Mecway GUI: the field `pressure` per mode has been compared headless
   with Mecway's own solution, NOT checked in the GUI.

56\. **Response spectrum: limits** (confirmed, `bridge_spectrum.py`,
   `aster_spectrum.py`, docs/Spectrumanalyse.md). Mecway has no spectrum analysis;
   the bridge computes it on a Frequency model with a Gravity table as spectrum
   (analysis `spectrum_3d`, choose it yourself: `auto` picks `modal_3d` for V30). Not
   translated: a spectrum per support (`MULT_APPUI`, `ENVELOPPE`), imposed
   displacements <> 0 or with a table (ERROR), loads (dropped, WARNING),
   velocities, stresses on shells and beams (only solid elements; INFO), and a
   spectrum that varies with damping from a gravity table (then `#ASTER-SPECTRE` with
   a `DEFI_NAPPE`). von Mises is computed per mode from `SIGM_NOEU` and combined
   (an upper bound with CQC), only per node (no element-nodal value). The
   result step is stored as a static result under a V30 analysis: Mecway's API reads
   the values (checked headless: `node_value`, `modes()` empty); the display in the
   Mecway GUI is NOT verified (question).

57\. **Harmonic acoustics: limits** (confirmed, `bridge_acoustic.py`
   `build_acoustic_harm`, `aster_acoustic_export.py`, docs/Akoestiek.md par. 5.6).
   Built and verified (AH-01..08): velocity source (`BRON_`, `#ASTER-BRON`),
   imposed pressure, pressure nodes, rho-c boundary (`ABSORBEREND_`) and a real impedance
   (Mecway *impedance*, `3D_ABSO` with `CELE_R = Z / rho`). Not: a **complex
   impedance** (Im Z != 0; `CELE_I` on the `3D_ABSO` face gave for c = 340(1 + i) a
   standing-wave ratio of 2.19 where Z = rho c (1 + i) gives 2.62, and -340 gave 2.29: the
   meaning of `CELE_I` in `AMOR_ACOU` has NOT been investigated) and a
   frequency-dependent impedance: ERROR. Possible route (NOT investigated): per
   frequency do `COMB_MATR_ASSE` (K - w^2 M + i w (rho/Z) A) and `RESOUDRE` yourself, like
   the "calcul decompose" of ahlv100a, or like the complex cavity modes (S2b,
   `aster_acoustic_complex.py`: A = int N N dA with `AMOR_ACOU` and `CELE_R = 1`, then
   scipy in the job; Z may then also differ per frequency). Also not: volume damping / complex
   speed of sound, a point source, microphones on face or element selections (WARNING),
   `#ASTER-EXCIT` (WARNING), coupling with a structure (for that
   `vibroacoustic_modes_3d` and `vibroacoustic_harm_3d`, item 59). A **resonance**
   without an absorbing boundary gives an (almost) singular matrix; the bridge only warns
   that there is no absorption, not which frequency falls on a cavity mode.
   Mecway GUI: the frequencies come as `<mode frequency>` with the fields `pressure`,
   `pressurei`, `pressuremag`, `pressurephase`, `spl`; Mecway's API reads them (headless
   script, `solution.modes()`, `node_value(.., mode=m)`), but the display in the GUI
   (list *Mode 1..n*, contour, animation of a complex "mode" without decay rate) has
   NOT been checked (question).

59\. **Vibro-acoustics: coupled modes and harmonic response; limits** (confirmed,
   `bridge_vibroacoustic.py`, `bridge_vibroacoustic_harm.py`, docs/Akoestiek.md §6.6 and
   §7.6). Built and verified: (a) coupled modes (VA-01..05c) of a
   structure (solids, shells) and a fluid (`3D_FLUIDE` + `FLUI_STRU`, `U_P_PHI`)
   on a Mecway Frequency model, coupling faces automatic or with `KOPPEL_`, p = 0 with
   `OPEN_`; (b) the harmonic response (`vibroacoustic_harm_3d`, VH-01..08:
   `DYNA_VIBRA` `HARM` `PHYS` with `MATR_IMPE_PHI`) with loads on the structure,
   velocity sources (`BRON_`, `VITE_FACE`), an incident wave (`INVALLEND_`,
   `ONDE_FLUI`), `#ASTER-BRON` (velocity or pressure), absorbing boundaries (`ABSORBEREND_`,
   real Mecway impedance, `3D_FLUI_ABSO`), Rayleigh damping (structure only)
   and dampers, microphones and measuring points. Not: two fluids with shared nodes and a
   **different density** (measured error: 188.23 instead of 306.47 Hz; ERROR); a
   shell with fluid on both sides (ERROR); impedance and *fluid pressure* != 0 in
   the modes (ERROR); in the harmonic response a **complex or
   frequency-dependent impedance** and *fluid pressure* != 0 (ERROR), volume damping,
   `AMOR_HYST`, `modal_damping`, a base motion (ERROR), stresses in shells and
   beams, reactions; prestress, gravity on a free surface (sloshing);
   effective mass per mode; modes below `vibro_freq_min` (including rigid modes).
   `ONDE_FLUI` and `3D_FLUI_ABSO` are exact for normal incidence (oblique: partial
   reflection, NOT measured). NOT verified: `elem_hex8` = `LINE_QUAD` with a
   fluid, bonded contact between fluid and structure, wedge/tet/pyramid fluid
   (only hex8/hex20 tested), quadratic shells (`COQUE_3D`, QUAD9) on a
   hex20 fluid face (the midside node of the shell then does not take part in the coupling),
   several sources with different phase at the same time (each separately is: VH-02t, VH-07, VH-08).
   Mecway GUI: the fields per mode (`displ`, `pressure`, headless script on VA-01) and per frequency
   (`displx`/`displix`, `pressure`/`pressurei`/`spl`, headless script on VH-02) are read by
   Mecway's API; the display in the GUI (contour, animation, list *Mode 1..n* of a
   harmonic response) has NOT been checked (question). A mechanism in the structure
   (e.g. a shell with only one rotation fixed) can make `CALC_MODES BANDE` find fewer modes
   than the Sturm count (WARNING with the number).

58\. **Welding heat source: limits** (confirmed, `bridge_welding.py`, docs/Lassen.md).
   `#ASTER-LASBRON` (Goldak double ellipsoid, verification WE-01..05) works only in
   a transient thermal analysis (T31) and only on solid elements; a path is
   straight or piecewise straight through the nodes of `pad` (the chain is built
   by distance: a path that runs back close along itself may be ordered wrongly,
   NOT tested), at constant speed. Without `geboorte=` the bead is present from t = 0;
   filler material that is born has its own limits (item 71). Several
   sources are in one load, together with Mecway sources as a formula or time table (two
   function loads with SOURCE are computed by Code-Aster 17.4 as the first). No latent heat
   (via c(T)); the
   mechanical chain has its own limits (item 64). The formula is evaluated per Gauss point in Python:
   with a large source group (route B on the whole model) that takes long (WE-02: 9,700
   elements in the source group, 60 steps, ~2 min; with THER_NON_LINE, WE-05, ~9 min).
   The energy check computes at five instants, not per step.

61\. **Cyclic symmetry: limits** (confirmed with runs, `bridge_cyclic.py`,
   `aster_cyclic.py`, docs/Modaal_en_knik.md par. 7). Translated: Mecway *Cyclic
   symmetry* in a *Frequency* analysis (V30) with `MODE_ITER_CYCL` (verification
   CY-01..06: full model and Mecway <= 0.03%). Not:
   (a) cyclic symmetry in static, non-linear static and thermal: ERROR and
   skipped_loads, the model is computed as a separate sector (Mecway can do it; for the
   prestress the bridge already builds the relations of ND 0, `_relations`);
   (b) shells, beams, springs and `LINE_QUAD` (ERROR; Mecway does not allow shells and beams
   in a Frequency analysis either);
   (c) a partial constraint or relation on a cut-face node (ERROR; Mecway
   allows axial displacement and a radial 0): the interfaces of
   `MODE_ITER_CYCL` have the same degrees of freedom per node;
   (d) 8 segments with nodes on the axis: Code-Aster 17.4 stops with `ALGORITH14_95`
   (`bibfor/algorith/ctetax.F90` rotates the vector (1, 1, 1) of active
   degrees of freedom by 45 degrees: cos - sin = 0, so DX is "missing"); the bridge
   gives an ERROR (solution: small hole on the axis);
   (e) a double eigenvalue within ND 0 (ring mode with n = N waves): the second
   +1.3% (CY-01 with 3-4 modes per ND, also with 80 sector modes); in ND N/2 it went
   fine. NOT investigated why (inverse iteration of MODE_ITER_CYCL);
   (f) with an X or Y axis: loads with a function or formula, `LIAISON_OBLIQUE` and
   `ANGL_NAUT` (ERROR); `#ASTER` code computes in the rotated frame (WARNING);
   (g) to Mecway the whole wheel like Mecway's own solution (S10i, setting
   `cyclic_full_wheel`, on by default; same node and element numbers, checked
   headless), but of a pair only the first member (which standing wave, i.e. the position
   of the nodal lines, is arbitrary and may differ from Mecway's choice) and only
   displacements (no stresses per mode, no complex modes, no effective mass,
   which Mecway does not give either). If Code-Aster's skeleton fails, only the
   sector goes to Mecway (WARNING in the `.mess`; NOT encountered in CY-01..06).
   The scaling of the shapes is that of `REST_SOUS_STRUC` (`modal_norm` does not apply; Mecway
   normalises differently). The display in the Mecway GUI has NOT been checked (the API reads the
   wheel, the modes and the values, headless). The highest modes per ND depend on
   `cyclic_base_modes`.

63\. **Fracture mechanics: only linear static, no field, no quarter points** (confirmed,
   `bridge_fracture.py`, docs/Breukmechanica.md). Built and verified (BR-01..06):
   K_I/K_II/K_III and G along a meshed crack (`SCHEUR_` selections) with `CALC_G`
   and `POST_K1_K2_K3` after `MECA_STATIQUE`, in the log, the status box and
   `<model>_<run>_scheur.csv`. Not: (a) non-linear static, dynamics and
   thermal models (WARNING, no K/G); (b) contact on the crack lips (a crack under
   compression gives overlapping lips and K_I < 0: WARNING); (c) K/G as a field in Mecway
   (only the table); (d) quarter-point nodes (`MODI_MAILLAGE NOEUD_QUART`): the bridge
   does not move nodes, because the result export checks the coordinates against
   the `.liml` (`aster_results_export._check_node_order`); with quarter points in the
   `.liml` itself it does work (BR-04), but Mecway cannot create them. Without
   quarter points `POST_K1_K2_K3` is 3-5 % too low with hex20 and 9-14 % with hex8
   (`CALC_G` < 1 % resp. 2 % on K); (e) XFEM (`#ASTER-XFEM`, `bridge_xfem.py`,
   S6b, BR-07..12; docs/Breukmechanica.md §7): only linear static and only
   solid elements with MODELISATION `3D` (ERROR otherwise); no contact on the lips,
   no crack growth (`PROPA_FISS`); K from `CALC_G_XFEM` has no curvature correction
   on a curved front (BR-10: +5 %; WARNING, use `POST_K1_K2_K3` or G);
   only nodal fields go to Mecway (displacement and stress via `POST_CHAM_XFEM`
   + `PROJ_CHAMP`, no `SIGM_ELNO`); a node exactly on the crack plane gets the
   value of one lip; `REAC_NODA` on nodes of cut elements is only the
   classical part (NOT verified); error estimator and fatigue not together with XFEM
   (WARNING); tet10/wedge15/pyr13 and `groep=` (`GROUP_MA_ENRI`) NOT verified,
   `LINE_QUAD` only outside the regression (BR-07 with LINE_QUAD: K_I 0.0 %), `result_route`
   `tabel` NOT verified; a crack from an `XFEM_` face selection (BR-13) always lies
   on a node layer; a curved crack plane or front, tet and quadratic
   elements from a selection NOT verified; (f) a crack on
   an interface between materials, thermal strain and pressure on the lips in `CALC_G`:
   NOT verified; (g) a curved front that is not a circle: K from `CALC_G` without
   curvature correction (WARNING; forma07a without correction +5.6 %). In the Mecway GUI
   NOT checked: opening a crack with *Disconnect elements* and *Merge
   nearby nodes* with a node selection (manual v33 par. 4.2.10/4.2.11) and the text in
   the status box.

64\. **Welding: limits of the thermal → mechanical chain** (confirmed,
   `bridge_thermomech.py`, docs/Lassen.md §9). Only in a transient thermal
   analysis (T31 with a Thermal stress) and only with solid elements (ERROR with
   shells, beams, springs); the chain does not compute contact and couplings, nor element
   offset, flexible joint and constraint equation (WARNING). The
   mechanical steps are the thermal ones (one Mecway *Time step*, also for
   cooling). Without `geboorte=` the bead is present from t = 0 and carries load
   (filler material that is born: item 71); metallurgy only
   with `#ASTER-METALLURGIE` (item 72), no recovery of the hardening above the
   melting temperature; the hardening curve
   (`TRACTION`) is not temperature-dependent, only bilinear via `#ASTER-MATERIAAL`.
   Linear hex8 ('3D') 'lock' under plastic yielding: WE-10 gave σxx in the weld
   1.3–2.6 × SY (top–bottom) and σzz 190 MPa in the middle of a 5 mm plate (WARNING, advice
   LINE_QUAD). With LINE_QUAD and plasticity Newton converged only with
   line search (`RECH_LINEAIRE`, now always with plasticity) and a step takes ~35 s
   CPU on 2,000 hex20 (WE-10b, ~1 hour; not in the standard regression). `GDEF_LOG`
   in the chain and kinematic hardening with temperature-dependent ET: NOT
   verified. Whether Mecway's GUI lets you add or shows Thermal stress, Fixed support and Displacement in a
   T31 model: NOT checked (headless, Mecway 33 stores and ignores
   them, WE-08).

65\. **Adaptive refinement: limits** (confirmed, `bridge_adapt.py`,
   docs/Foutschatter.md §6). Only linear static and only solid elements (the
   error estimator, item 51). Mecway's `refine_x2` creates poor transition elements
   after a few loops: with thin elements (thickness 1/40 of the width) in loop 2, with
   tet10 already in loop 1; the global estimate then rises and the loop stops (WARNING). Also in
   AD-02 the worst hex20 drops to 0.04 (WARNING) without the error rising.
   Node selections with a condition are not refined along by Mecway: ERROR before
   refining (AD-03). HOMARD (`MACR_ADAP_MAIL`, needed for thermal and nonlinear
   static) is not built yet: researched in STAPPENPLAN S35a (loop in one job, result
   projected back onto the Mecway mesh; prototype `TestFiles/Tools/homard_s35`), build =
   S35b. Each loop waits for Code-Aster (status window or OK click,
   setting `wait_for_aster`). The loop in the
   Mecway GUI has NOT been checked, only headless (`mecway.exe <model> script`).

66\. **Fatigue: limits (solids and shells, Miner, critical plane only on
   solids)** (confirmed, `bridge_fatigue.py`, `aster_fatigue.py`, docs/Vermoeiing.md).
   Built and verified (VM-01..11): damage and life per node with
   `#ASTER-WOHLER` (table, power law, Basquin, Manson-Coffin), rainflow (periodic
   like `POST_FATIGUE`, or ASTM E1049) and Miner, on blocks or a signal for linear
   static or the time steps of `STAT_NON_LINE`/`DYNA_NON_LINE`; shells on the top
   and bottom surface (`SIEQ_NOEU` of `POST_CHAMP EXTR_COQUE`); multiaxial with
   `CALC_FATIGUE FATIGUE_MULTI DOMA_NOEUD` (Dang Van, Matake, Crossland, own formula;
   sslv135a). Not: (a) beams (WARNING); shells with a strain curve or a criterion
   (WARNING, shells skipped); (b) multiaxial per Gauss point (`DOMA_ELGA`),
   Papadopoulos (only via `criterium = FORMULE` with `RAYSPH`), Fatemi-Socie
   (`FATESOCI_MODI_AV`), `COEF_PREECROU`, `INST_INIT_CYCL`, constants a/b/c per
   material (now equal for all materials); strain: no Morrow/SWT correction and no
   fatigue limit, Taheri, Lemaitre; vibration fatigue (`FATIGUE_VIBR`) and random
   (`POST_FATI_ALEA`); in response on modal basis, harmonic and spectrum only a
   WARNING; (c) damage per element node (only node-averaged stress; at a boundary
   between two materials the larger of the two curves); (d) a filter on small cycles
   (`DELTA_OSCI`); (e) Code-Aster searches the critical plane on a grid of normals:
   for Matake SIGEQ +0.06 % relative to the hand calculation (VM-09c), for Dang Van −2·10⁻⁶;
   for multiaxial the bridge copies the whole non-linear/dynamic result
   (`CREA_RESU`, so that t = 0 counts), for a large model with many time steps
   double the memory for `SIGM_NOEU`/`EPSI_NOEU` (NOT measured);
   (f) `PROL_GAUCHE`/`PROL_DROITE` `LINEAIRE` is extended log-log by the bridge, but linearly in (S, N)
   by Code-Aster's `POST_FATIGUE`/`CALC_FATIGUE` (measured; above the table there even
   negative damage), so outside the table the bridge deliberately deviates from Code-Aster.
   With a time history `damage`/`life` are in every time step with the same value
   (Mecway's API reads them, headless); the display in the Mecway GUI has NOT been checked
   (question). The history is held in memory as nodes × time steps (float64);
   the rainflow per node is Python (measured outside Code-Aster: 20,000 nodes × 200
   steps with noise, 1.26 million cycles, 3.3 s); a large dynamic model in a real
   run has NOT been measured.

72\. **Welding: limits of the metallurgy** (confirmed with runs, `bridge_metallurgy.py`,
   docs/Lassen.md §10). `#ASTER-METALLURGIE` works only in a transient
   thermal analysis (T31) and only on solid elements; only the steel model
   `ACIER` (no tempering `ACIER_REVENU`); mechanically only `META_P_IL` (no
   kinematic hardening, viscoplasticity or transformation plasticity
   `META_PT`) and not with `elem_hex8 = LINE_QUAD` (ERROR). Measured behaviour of
   `CALC_META` (Code-Aster 17.4), cause not investigated: (a) with fast heating and
   a large temperature step per time step the austenitisation lags behind the
   time constant (1000 °C/s: 4 °C per step exact, 40 °C per step ~8× slower; the
   bridge reports nodes that went well above Ac3 but became < 90% austenite; advice
   for welding `TAUX_1=TAUX_3=0.001`); (b) martensite formation stops at ~0.4–0.7%
   austenite, even where Koistinen-Marburger continues (MT-02); (c) 16MND5 still forms
   3% bainite at 200 °C/s, although the fastest CCT history with transformation is
   80 °C/s. Dataset 16MND5 (mtlp103a) has no mechanical data per phase:
   `ALPHA_A`, `DEPS` and the yield stress per phase are given by the user (MT-07 computes with
   illustrative values). Whether Mecway shows the fields `ferrite` .. `hardness` per time step:
   NOT checked in the Mecway GUI.

71\. **Welding: filler material that is born, limits** (confirmed, `bridge_welding.
   _births`, `birth_materials`, `ther_loop`, `bridge_thermomech._birth_solve`;
   docs/Lassen.md §11). `geboorte=` in `#ASTER-LASBRON` is the "quiet element" method
   (Code-Aster 17.4 has no element birth): quiet = ρ·c × 1e-4, λ × 1e-8, E × 1e-4
   (fixed factors), the source not in quiet material; verification WE-11..13. Limits:
   (a) the birth follows the arc length along the path (not the distance to the arc) and
   is per element and per time step: stress-free at the temperature at the start of the
   birth step; (b) at birth an element takes over the temperature of its nodes;
   those on the interface are already hot: +1.2..1.6% energy in WE-11; (c) the
   filler material is computed thermally with a diagonal heat capacity (`3D_DIAG`;
   with the consistent capacity a quiet node followed its hot neighbours via the mass
   coupling, WE-13 +138 K); (d) with λ(T)/c(T) or radiation (`THER_NON_LINE`) and in the
   chain one solve per birth step (longer computing time); (e) the plastic strain and
   hardening of the quiet element are reset to zero at birth; (f) only
   solid elements, each element with at most one source; (g) `GDEF_LOG` and
   kinematic hardening with birth: NOT verified; (h) Mecway's own solver
   has no birth (no comparison with Mecway); the display of quiet elements
   in the Mecway GUI has NOT been checked.

104\. **Formulas: limits** (confirmed with runs, `bridge_bcs.PositionFormula`,
   `_formula_value`, `bridge_from_liml._check_position_formulas`; verification
   LS-40..44, NL-40). A formula in x, y, z (also with t) becomes in the mechanical
   analyses a `FORMULE` of X, Y, Z (INST) in `AFFE_CHAR_MECA_F` for pressure, traction,
   force, line pressure and imposed displacement/rotation (value, fixed direction).
   Limits: (a) **not translated** (ERROR): a formula in x, y, z for gravity,
   centrifugal force, moment, velocity, frictionless, hydrostatic pressure, elastic
   support, the direction vector of displacement/node rotation (Mecway: "can be
   functions of position"; Mecway 34 headless did not solve such a model), pressure or
   traction on shell edges and beam ends (fixed nodal forces,
   `bridge_mesh._edge_loads`), in explicit dynamics, harmonic, modal response,
   spectrum and the thermal → mechanical chain; a line pressure as a formula next to
   a time-dependent line pressure on the same beams (`_prepare_beam_loads`).
   (b) **Mecway 34 computes differently**: force, imposed displacement/rotation and line
   pressure with x, y or z in the formula are not applied by Mecway (reactions 0; internal
   solver and CCX); the bridge does apply them (WARNING). Force on faces/nodes: the formula is
   the total, like a number, so per area f/A or per node f/n, at the location
   of the integration point or the node. (c) DKT/DST shells take a function at the
   nodes (`FORCE_COQUE`, pressure 3y² on a 4 × 8 plate +0.78%, LS-44a; `COQUE_3D`
   exact). Pressure with a formula on shells goes via `FORCE_COQUE PRES` (`PRES_REP`
   with a function: `<EXCEPTION> ELEMENTS4_92` on DKT and COQUE_3D) and remains a fixed load
   at large displacements (Mecway: only uniform pressure follows the deformation).
   (d) Linear static, modal and buckling take f(end time) (formula in t and x, y, z:
   t = end time); Mecway internal ignores a load in t, CCX takes f(0). (e) Each point
   of a time function becomes a computation step in STAT_NON_LINE (with Mecway's
   step size) or an interval with `substeps_per_interval` steps (without
   step size; `_build_listinst_block`): a sine gives hundreds of points and thus
   hundreds to thousands of steps. (f) Values that `bridge_from_liml` reads with
   `parse_and_convert(findtext(...))` (e.g. `referencetemperature`) would
   read a constant formula (number with unit attribute) as SI, if Mecway ever
   writes a formula there (NOT seen). (g) The error estimator (`CALC_ERREUR`, load
   `load_err`) only takes constant loads into account: a face with a formula load is
   a stress-free boundary for the estimator (INFO), so a too-large local error there.

121\. **Result formulas: not every Mecway symbol** (confirmed, Mecway 34, GitHub issue #8;
   S33). The bridge evaluates Mecway's result formulas (*Solution > Formula*) in the job
   (`bridge_formula`, `aster_results_export._formula_vars`), but only with symbols of fields it
   writes. Not: Green-Lagrange principal values `GLe1`.. (`e1` works: in a nonlinear analysis
   it is the Green-Lagrange principal strain; `s1`..`s3`, `tr`, `e1`..`e3` need the fields
   `principal_stresses` / `principal_strains`, S34), stresses in element coordinates
   (`s.uu`..), shell forces `ML`/`FL`, Zienkiewicz-Zhu stresses, `FE`, `Ue`/`UE`, electric
   symbols and material properties (`youngsmodulus`, ...). Such a formula keeps no values and is
   invalid (red) after loading; `bridge_from_liml._plan_result_formula` gives a WARNING and lists
   it in `skipped_loads`, with the workaround: delete the formula and create it again after
   loading, Mecway then computes it from the bridge results (checked in the GUI). Also: units
   are taken from the bridge's own unit table (`bridge_formula._ATOMS`, composite units with `/`
   and `.`); a unit Mecway does not know counts as SI in Mecway, the bridge may know it (e.g.
   `W/mm2`: Mecway SI, the bridge 1e-6). Mecway writes only units from its own list, so this
   only matters for hand-edited files.

122\. **Route `tabel`: no Saved monitor** (confirmed, `MecwayAsterBridgeMain._run`, GitHub
   issue #7). With `result_route` "tabel" the bridge fills Mecway's existing solution through
   `solution.set_variable()` and does not rewrite the `.liml`; the API cannot add the *Saved
   monitor* item, so the Code-Aster output is not stored in the model (an INFO line in the log
   says so). The `.mess` stays in the work folder. The default route "liml" writes the monitor
   (`bridge_monitor.py`, `bridge_results_liml.splice_results`).
124\. **Pre-tension section: limits** (confirmed with runs, `bridge_pretension.py`; S15,
   S15b, docs/Boutvoorspanning.md par. 7). (a) The prism variant in linear and nonlinear
   static and implicit dynamics (`MECA_STATIQUE`, `STAT_NON_LINE`, `DYNA_NON_LINE` with
   HHT/NEWMARK; PT-06 .. PT-08 equal to Mecway's CCX within 0.06%); not in explicit
   dynamics (`DIFF_CENT`: the reference node has no mass; Lagrange relations there NOT
   verified) or on a modal basis (ERROR). (b) Mecway's spring element variant only in
   linear static (two nodal forces k d, PT-09/10 exact against Mecway's internal solver).
   Mecway also allows it in Frequency and Buckling, but gives the tensioned spring a
   geometric stiffness there (cantilever with a pretensioned spring from base to tip:
   buckling factor 6.991 in Mecway, 1.748 with the nodal forces in Code-Aster, measured 28
   Oct 2026); DIS_T has none, so the bridge gives an ERROR. A fix would need the spring's
   geometric stiffness N/L across its axis (e.g. an extra element), NOT built. (c) Loads, supports and contact on faces that touch the section: the boundary
   cells of the elements below the section get the copies of the section nodes, except
   cells that only carry supports (those stay on the Mecway node: a support on both the node
   and its copy repeats the tie, `FACTOR_11`, seen in PT-01); node-based quantities that
   `bridge_mesh` derives from the face lists (pinned support weights, per-node normals of
   frictionless/compression only) use the Mecway node. The difference is at most the
   shortening, comparable to Mecway's inserted layer that carries no loads. (d) `LINE_QUAD`
   (quadratic Code-Aster cells from hex8) is not applied with a section (WARNING): the new
   mid-side nodes on both sides of the section would stay apart. (e) The section lies at the
   middle of the axial extent by element centroids; where Mecway puts it in an irregular
   mesh is NOT verified (BoltedJoint: the element boundary in the middle, as the bridge).
   (f) Which side keeps the Mecway nodes (results at the section) follows the axis sign
   (largest component positive, side above keeps them); Mecway's rule is NOT verified beyond
   BoltedJoint.
126\. **2D analyses: limits** (confirmed, `bridge_plane.py`, STAPPENPLAN S16a, S16b).
   Translated: Static 2D (S20, `C_PLAN`/`D_PLAN`) and Static Axisymmetric (SA0, `AXIS`) in
   linear static (`lin_static_3d`), Dynamic Response 2D/Axisymmetric (D20, DA0) in
   `dyna_impl_3d` (implicit, Rayleigh damping, time tables; no explicit scheme, mode
   superposition or initial velocity), plane elements only, one thickness and one type per
   model; fixed, pinned,
   displacement along X/Y, symmetry with normal X/Y, force (nodes, edges), pressure and
   traction on edges, gravity in the plane (SA0 along Y), centrifugal about Z (S20) / Y (SA0)
   ([`docs/en/2D_and_axisymmetric.md`](docs/en/2D_and_axisymmetric.md)). Not: Acoustic
   Resonance 2D (A20) (ERROR, step S16d), beams/trusses/springs in S20, several thicknesses, other loads and constraints
   (moment, line pressure, hydrostatic, frictionless, elastic support, oblique directions,
   constraint equations, couplings, contact, point masses, temperatures), the error estimator
   (INFO) and the result route `tabel` (ERROR) (step S16e). Mecway itself has no thermal,
   frequency, buckling or nonlinear 2D type (Mecway 34 converts V20 to V30 and B20/T20/L20 to
   S30; thermal 2D is made of shells, `bridge_thermal`).
