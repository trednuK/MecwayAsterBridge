# Changelog

## Unreleased

- **Nonlinear static without *Quasi-static*: load tables up to t = 1 s, like Mecway
  (results change).** Without `<timesteps>` Mecway computes one step and takes every table
  (force, imposed displacement, temperature) at t = 1 s, also when the table runs further
  (Mecway 36 with CCX, measured headless). The bridge computed up to the last table point;
  it now stops at t = 1 s with a WARNING, and a constant temperature ramps up to 1 s too.
  Turn on *Quasi-static* to follow the whole table. Verification NL-75b..d.
- **Nonlinear static with CCX *time points* (no step size, no automatic time stepping):
  up to the period, like Mecway (results change).** Mecway computes up to the *Time period*
  and takes the load tables there, also when a table runs further, and holds a table that
  ends earlier (Mecway 36 with CCX, measured headless). The bridge computed up to the last
  table point; it now ends at the period (INFO), and like Mecway only the end state goes to
  Mecway (with t = 0; every step when the run stops earlier, with the failure loop and with
  fatigue). Verification NL-75e/f/g.
- **Result route `tabel` removed.** The results now always go through the `.liml`:
  Code-Aster writes Mecway's own results and the bridge puts them into the model (all time
  steps or modes, values per element, every analysis type). The old table route (POST_RELEVE_T
  tables in a `.resu`, node values of the last time only, loaded into Mecway's own solution)
  needed a Mecway solve first, worked only for static analyses and showed Mecway's own values
  per element node and beam forces next to Code-Aster's node values (KNOWN_BUGS 7 and 148,
  now gone). The setting *Results to Mecway* is gone from the start screen; a `bridge_utils.py`
  kept from an older bridge with `"result_route": "tabel"` gives one WARNING and the run goes
  through the `.liml` (remove that line). Results stay storable apart from the model:
  *Results...* takes them out of the `.liml` and loads any run again later. The generated
  `.comm` of a run is unchanged. Code-Aster's alarm `POSTRELE_70` now explains a user's own
  `POST_RELEVE_T` (`#ASTER-POST`) on beam or shell fields; write own tables with `UNITE=6`.

- **Mecway 36: a run and *Show section* read the open model without saving it first.**
  With Mecway's new `mw.liml_text()` the bridge reads a copy of the open model
  (`<model>_<run-id>_model.liml` in the work folder, which the Code-Aster job reads too, e.g.
  for fatigue) and saves the `.liml` only right before the results go into it, so a run that
  ends without results (an error, Stop) leaves the file as it was, unless *Summary also as
  Saved monitor in the .liml* (`save_monitor_liml`) is on: then the model is saved (with the
  run's monitor text when it has no results yet). A model that was never saved is still
  saved first. A read-only model or a folder that is gone still stops the run
  before Code-Aster. The copy is removed after a run without errors whose results were
  loaded, and stays otherwise (the `.comm` reads it when run again by hand). Unsaved changes
  stay unsaved during the run: save the model yourself before a long run. After a run that
  left the file as it was, Mecway asks "Save changes?" when another model is opened (Mecway
  does that after every script); "No" is safe if you edited nothing. *Show section* no
  longer saves either. Older Mecway versions (no `mw.liml_text()`) behave as before.
  Verified in the Mecway 36 window (36.0.9815).

- **Start screen: the mouse wheel over a closed choice list scrolls the page** and no longer
  changes the setting (it did when the pointer was over a list while scrolling the page, e.g.
  *Active analysis*; KNOWN_BUGS 152). An open list scrolls as before; the arrow keys still
  change the focused list.

- **CCX keyword modifications** (Mecway's *CCX keyword*, e.g. `ADJUST` on `*CONTACT PAIR`)
  are CalculiX input: the bridge now reports them, a WARNING per active modification and one
  line in the list of items not translated (KNOWN_BUGS 4), also for harmless ones such as
  a solver choice. Before they were skipped without a message.
- **Bonded contact across a gap**: a WARNING when tied slave nodes lie farther from the
  master than half the shell thickness on each shell side (0 for solids) plus a small
  tolerance (a tenth of the master element size, and the sagitta of a curved master); not
  checked with an *Element offset* or a shell without a thickness (INFO). CCX first moves them onto the
  master, Code-Aster ties them where they are, so the gap stays (KNOWN_BUGS 146); close the
  gap in the mesh. Code-Aster's alarm `CALCULEL5_48` now has an explanation in the log.
  The generated `.comm` is unchanged.
- **Bonded contact with supports on slave nodes** (KNOWN_BUGS 147): a symmetry plane as
  *Displacement* 0 through both bonded parts (or another constant support that holds the
  tied slave nodes and their master nodes the same way) no longer stops Code-Aster with a
  singular matrix: the bridge leaves the support out on those slave nodes, which follow
  the master (INFO). Such models stopped before with `FACTOR_11` (linear) or computed no
  time step (nonlinear); now they give Mecway's result (verification LS-07n). Their `.comm`
  changes: the support goes to a node group without those nodes. Double conditions it
  cannot resolve get a WARNING.
- **Bonded contact with a symmetry or frictionless support on slave and master nodes, and
  on the bridge's own shell ties** (rest of KNOWN_BUGS 147): a *Symmetry* or *Frictionless
  support* on a plane perpendicular to a global axis, without a prescribed normal
  displacement, on the faces of both bonded solids no longer
  stops Code-Aster with `FACTOR_11` (linear) or `MECANONLINE9_4` (nonlinear): the tied
  slave nodes leave the relation there and follow the master (INFO; verification LS-07p/q
  and in Nonlinear Static LS-07t/u, equal to Mecway; modal LS-07v without the singular
  matrix ALARM; implicit dynamics LS-07w, buckling LS-07y and XFEM LS-07z, which previously
  stopped with `MECANONLINE9_4` or `FACTOR_11`). For shell on shell with a quadratic or an oblique/curved master (the
  bridge's own `LIAISON_DDL`) a tie relation in a translation whose nodes are all held the
  same way is left out (INFO; LS-07r/s, which previously stopped with `FACTOR_57` or
  `FACTOR_11`; in implicit dynamics LS-07x). The `.comm` of
  such models changes (node groups without those nodes, `SANS_GROUP_NO` on `FACE_IMPO`,
  fewer `LIAISON_DDL` rows). What stays double gets a WARNING, which with NPREC = -1 now
  says that MUMPS does not check for a singular matrix (`FACTOR_57` or an unreliable
  result). Also measured in implicit dynamics, buckling and XFEM (LS-07w..z); HOMARD refuses
  bonded contact before the run; explicit dynamics, harmonic and the other analyses NOT verified
  (side findings: KNOWN_BUGS 156, 157).
- **Behaviour change: contact method `auto` is the new default in Nonlinear Static**
  (`contact_algo`, page Contact). Every unilateral contact with Mecway's *normal stiffness*
  in a 3D Nonlinear Static analysis is now computed with penalty (`PENALISATION`), as Mecway
  does; before it was Lagrange (`STANDARD`) unless you chose otherwise. 2D models keep
  `STANDARD` (not measured with penalty; implicit dynamics and explicit dynamics: see below). Your own `ALGO_CONT`, `COEF_PENA_*` or
  `ALGO_FROT` in `#ASTER-ZONE` now take precedence over the bridge's (before: `SyntaxError`
  with *Contact method* = PENALISATION). Measured against Mecway 36 with CCX: the contact patch tests now agree to
  2e-5 (before 50 %, no penetration p/kn), Voorbeeld_C 3.2 % (before 7.0 %), and line contact
  between beams runs where `STANDARD` stopped. Results of contact models change by the
  penetration p/kn. If you keep your own `Scripts/bridge_utils.py` from an older version
  (saved start-screen settings), it still says `STANDARD`: choose `auto` once on the page
  Contact. Hard contact without penetration: choose `STANDARD`.
- **Option: close bonded gaps like CCX** (*Bonded contact: close gaps like CCX*, page
  General, off by default). On: the tied slave nodes of a solid-on-solid bonded contact are
  moved onto the master in the mesh for Code-Aster, as CCX does; the `.liml` stays as it is.
  Only with a flat master face and a move up to 0.1 × the shortest distance to another node
  of an element at the node, in linear and nonlinear static, modal and buckling analyses, not for nodes in another
  contact, coupling, equation, support or load. LS-07o (0.2 mm gap) now equals Mecway.
- **`#ASTER` contact lines are checked, and `#ASTER-BONDED` is new.** `#ASTER-ZONE`,
  `#ASTER-CONTACT` and the new `#ASTER-BONDED` (extra keywords for the `LIAISON_MAIL` of
  bonded contact, e.g. `DISTANCE_MAX`, `DISTANCE_ALARME`) are checked against the Code-Aster
  17.4 catalogue: a keyword the bridge writes itself, a keyword twice or a piece without
  `key=value` stops the run with an ERROR; an unknown keyword gives a WARNING.
- **Friction with parts held only by contact** no longer stops in the first step: zones
  with friction get `SEUIL_INIT` (initial friction threshold; the result does not depend
  on its value).
- **Friction: `COEF_PENA_FROT` no longer equals Mecway's kt** (behaviour change, Nonlinear
  static 3D). Code-Aster's `COEF_PENA_FROT` is in 1/m and acts on the slip of each time step
  (Code-Aster 17.4 source), so it cannot model Mecway's elastic slip τ/kt. The bridge now
  lets friction contact stick rigidly with `COEF_PENA_FROT` = 1/(1e-8 × the size of the
  contact faces) and gives a WARNING that kt is not used (KNOWN_BUGS 149). Results stay the
  same (it already stuck almost rigidly), but convergence is much better: NL-03h 10 steps
  instead of 754, and Tutorials/AssemblyWithContact *Friction* and *Quadratic_ramp* now
  complete (they stopped). Your own `#ASTER-ZONE COEF_PENA_FROT=...` still wins.
- **Contact in implicit dynamics: default contact method `auto`** (behaviour change).
  Like Nonlinear static since V2026.15: penalty contact with Mecway's normal stiffness, and
  friction sticks rigidly (also when you chose `PENALISATION`: kt is no longer written as
  `COEF_PENA_FROT` there). Measured against Mecway 36 with CCX: a force pulse with release
  within 4.7 % of the largest displacement (Lagrange: 59 % too stiff, then it stopped), an impact across a gap completes
  where Lagrange and CCX stopped (verification NL-03j/k/l/m). Explicit dynamics has no
  contact in Code-Aster (below). A saved start screen keeps its `STANDARD` for dynamics: choose `auto` once.
- **Contact in explicit dynamics stops with a clear ERROR before the run**: Code-Aster
  cannot compute it (`MECANONLINE5_22`, KNOWN_BUGS 154); choose an implicit scheme.
- **Friction with tangential stiffness 0** now sticks rigidly like kt > 0 (KNOWN_BUGS 150;
  Lagrange friction stopped AssemblyWithContact *Friction*; Mecway/CCX gives no usable
  result with kt = 0; verification NL-03n).
- **Nonlinear dynamics (D31) with a *Time step size*: the bridge now uses it** (bug fix,
  changes results). Before, a D31 model in the form Mecway writes for CCX (`stepsize`) got only
  the points of its load tables as time steps (a 200 µs pulse: 4 steps instead of 100); now
  the solver step and the output step are Mecway's step, as for D30 (verification NL-03j,
  equal to Mecway 36 with CCX). With *Time point increment* nothing changes. Explicit dynamics
  writes its output per step too, and a run with element failure restarts per step (more
  restarts than before).
- **Thermal bonded contact with the same temperature on both sides of the bond** no longer
  stops with `FACTOR_11`: slave nodes whose temperature is imposed with the same value as
  their master nodes leave the thermal tie (KNOWN_BUGS 147, verification TH-04e/f/g); another
  or a time-dependent value, or a gap, gives a WARNING.
- **Clearer message when nothing resists yet.** If no step converges while Code-Aster's
  absolute residual stays about 0 (e.g. an imposed displacement before the contact closes,
  as in Mecway's sample PipeClip), the message now says that the relative criterion cannot
  converge and advises *Convergence criterion* = RELA_OF_MAXI (PipeClip then completes).

## V2026.14 – 18 November 2026

Mecway 36 is a tested version: verified headless and with ten checks in the Mecway 36 window
(release candidate 36.0.9815). Axisymmetric models get shells (`COQUE_AXIS`), and 2D and
axisymmetric models get heat transfer and the thermal -> mechanical chain (`AXIS`, `C_PLAN`,
`D_PLAN`), element failure and readable results under physical names (STAPPENPLAN S44d/e and
the failure loop of S44a). The S46 review of the
KNOWN_BUGS items goes on: gaps with their own direction, total harmonic stresses with
hysteretic damping, and a clear stop when route `tabel` has no Mecway solution.
Behaviour changes:
- a 2D or axisymmetric model with `**ASTER-PLANE` in Nonlinear Static and a failure limit now
  really fails;
- a closed gap that does not lie along global X no longer has lateral stiffness, so such
  models give different, correct results;
- harmonic stresses with hysteretic damping are the total stresses.

Measured with Code-Aster 17.4, Mecway 35 and 36 headless and offline tests; element failure in
2D and the `C_PLAN`/`D_PLAN` chain NOT checked in the Mecway window. Full regression on
02905aa: 3447 of 3455 checks OK (670 test cases), 8 BEKEND (KNOWN_BUGS 43, 83, 108, 115 as
before, and 144 in PL-70/PL-70r), 0 NOK/FOUT, no status change.

- **Mecway 36** (36.0.9815) is a tested version: a model saved by Mecway 36 no longer gives
  the "not tested" WARNING. Verified headless: the full verification, also on models saved
  by Mecway 36, the references of Mecway's own solver and of CCX measured again, and results
  opened by Mecway 36 ([`docs/en/After_an_update.md`](docs/en/After_an_update.md) §6). In
  the Mecway 36 window (18 November 2026) ten checks: start screen, linear static with route
  `liml`, configurations, Saved monitor, hiding failed elements, the section view, the status
  and convergence windows, the ParaView and AsterStudy buttons, `mw.face_nodes` and route
  `tabel`, all as expected. Mecway 35 is not in the list of tested versions. Beams with CCX in
  Mecway 36 agree with Mecway 34 within 1e-4 (displacements of NL-82, NL-83 and LS-50).
  Measured on the release candidate 36.0.9815; the check covers every 36.x build (it
  compares the major version); run §2 of After_an_update.md again on the final build.

- **Element failure in 2D and axisymmetric.** `#ASTER-BEZWIJKEN` (and the other failure
  limits) now works with `**ASTER-PLANE C_PLAN|D_PLAN|AXIS` in *Nonlinear Static* (L30), as
  in 3D; before, the elements could not fail (WARNING). A model with a failure limit, or the
  setting "Failure limit all plastic mat." above 0, therefore now fails in route A. Verified
  headless with Code-Aster 17.4 against closed forms (PL-70 … PL-74, also kinematic hardening
  and two strips side by side). Not together with contact and not in Mecway's 2D types
  (D20/DA0): a WARNING, the elements do not fail. `C_PLAN` with large strains gives forces
  about √(1 + ε) too high, because the thickness does not follow the strain (KNOWN_BUGS 144;
  a WARNING for a failure limit above 0.05).

- **The thermal -> mechanical chain in plane stress and plane strain.** A *Thermal
  Transient* model (T31) with *Thermal stress* and `**ASTER-PLANE C_PLAN` or `D_PLAN` is now
  computed (thermal `PLAN`, mechanical `C_PLAN`/`D_PLAN` with the shell thickness; one
  thickness per model); before it was an ERROR. Plasticity in the chain is verified in `AXIS`
  and `C_PLAN` (PL-75 … PL-80, headless, Code-Aster 17.4, all within 1e-6 of the closed form).
  A failure limit in the chain (in 3D too) now gives a WARNING: the chain has no failure
  loop; before it was ignored without a message. Bonded contact in 2D stays an ERROR.

- **Gaps with their own direction, and no lateral stiffness** (KNOWN_BUGS 23). A gap whose
  *Element orientation* card gives a U that is not along node 1 -> 2 is now translated: a U
  oblique to the element, a ground node offset to the side, and a gap between coincident
  nodes (also a tension gap there). The result equals Mecway 35 (NL-92e .. NL-92l; NL-92m
  against the hand calculation). Fix: a
  closed gap that does not lie along global X had lateral stiffness (up to its closed
  stiffness k) and carried forces across its axis; Mecway's gap does not (NL-92l). Models with
  such gaps give different, correct results now. Still refused (ERROR, with the reason): a
  tension gap on separate nodes, a clearance on coincident nodes, coincident nodes without a
  card.

- **Fix: clear message when route `tabel` has no Mecway solution.** Route `tabel` writes the
  results into Mecway's own solution. On a model that Mecway's own solver cannot solve (for
  example contact on shell edges) Mecway leaves a solution without nodes. The bridge then said
  "The solution has 0 nodes, the model 86. The solution predates the last change to the
  model." It now says that there is no Mecway solution of the model (the Mecway solve failed
  or was not run, or ran without an error but left none) and advises route `liml`. As before
  it stops before Code-Aster starts. With route `liml` and *Mecway solve first* on, such a
  solve now gives a WARNING that the comparison with Mecway is lost; the run goes on.

- **Readable 2D and axisymmetric results** (after a test in the Mecway 35 window):
  - the stresses of an axisymmetric model also under their physical names `radialstress`,
    `axialstress`, `hoopstress`, `shearstressrz` (same values as `stressxx`, `stressyy`,
    `stresszz`, `stressxy`); axisymmetric shells per surface `meridionalstress…` and
    `hoopstress…` (with `shell_stresses`);
  - `contactpressure` and `contactstate` in a 2D model on every node, 0 outside the contact
    (3D unchanged: the slave nodes);
  - the ParaView button opens an axisymmetric result as a body of revolution (270 degrees about
    Y), with "VTU/PVD files for ParaView" on (`<model>_<run-id>_paraview_axis.py`);
  - docs: the axes, the variable names, "red in Mecway's tree is expected" and a worked check
    of `PL-62.liml` and worked example 8 (`PL-47.liml`) in
    [`docs/en/2D_and_axisymmetric.md`](docs/en/2D_and_axisymmetric.md) §1.3 and §1.5.

- **Error estimator on a model without solid elements**: an INFO instead of a WARNING (the
  setting is on by default, so every shell, beam or axisymmetric-shell model showed it); still
  a WARNING when the model asks for the estimate with `#ASTER-OPTIE error_estimator`.

- **Fix: example models that opened with a message in Mecway 35.** The 2D example and
  verification models `PL-30`, `PL-30p`, `PL-31`, `PL-32`, `PL-35` (`plastic strain`) and
  `PL-40` … `PL-46` (`contact`) asked Mecway for a result field it does not know, so Mecway 35
  showed "Invalid fieldvariable name" on opening. Those lines are gone; the bridge itself
  writes no field variables, and its results were not affected. All PL models and the other
  models the docs point to (MD-05, MT-06, MT-07, WE-02, WE-10, WE-13), 68 in all, now open
  without a message (checked in a hidden Mecway 35).

- **Axisymmetric shells** (STAPPENPLAN S44e): line3 elements in Static 3D (S30) or
  Nonlinear Static (L30) in the XY plane with the line `**ASTER-PLANE AXIS` are computed as
  Code-Aster `COQUE_AXIS` (SEG3). The thickness comes from the new line
  `**ASTER-SHELL <material>: EPAIS=<t>` (also `**ASTER-SCHAAL`, optionally `A_CIS`), or from
  the material's *Shell/membrane* thickness or a *RectBar*; the line wins. Supports hold X, Y
  and the rotation about Z (*Fixed*, *Symmetry*, *Node rotation* about Z); a pressure on the
  side of the line elements (faceid 1) pushes along n = Z × U, exactly as Mecway draws the
  arrows (seen in Mecway 35; a WARNING when such elements have an orientation, where Mecway's
  side is not verified); forces and moments on nodes
  are for 360 degrees; gravity along Y. Results: displacements, `rotz` and the reactions
  (`reactionmomz` too) for 360 degrees; von Mises on the top, middle and bottom surface
  (`vonmisesu1/m/b`); with the result fields `shell_stresses`, `shell_forces` and
  `principal_stresses` the stress tensor per surface in global axes (`stresszz…` = hoop
  stress), the normal forces and bending moments per length along the meridian and the hoop
  direction (`forceperlengthu/v`, `momentu/v`; S30 only) and the principal stresses. Top
  (`u1`) is the face the pressure acts on, where Mecway draws the arrows. The transverse shear is left out (Code-Aster's SIXZ
  of `COQUE_AXIS` is not the physical shear, measured). Verification PL-60 … PL-68: thin
  cylinder and sphere (hoop stress p R / t, p R / (2t)), a clamped circular plate, the clamp
  moment and the clamp stress of a long cylinder (−0.94%, −1.1%), Code-Aster test case
  ssls114i (exact), a pressure time table in L30, a nodal force, a ring moment and gravity.
  Not: line2, plasticity, mixing with plane elements, temperatures, contact, centrifugal
  force, traction (ERROR); strain and factor of safety (INFO, WARNING).

- **Heat transfer axisymmetric** (STAPPENPLAN S44d, piece 1): Thermal Steady State (T30) or
  Transient (T31) with plane shell elements in the XY plane and the line
  `**ASTER-PLANE AXIS` is computed as Code-Aster `THERMIQUE` `AXIS` about Y (no shell
  thickness; a total heat flow spread over the revolved area or volume). Verification
  PL-50 … PL-57: radial conduction, a total heat flow, convection and radiation in a tube,
  heat generation in a solid cylinder (as *Internal heat generation* and as a total heat
  flow on the elements), the transient cooling of a cylinder against the Bessel series
  (within 0.0025 of the initial difference), and the plane wall with convection (`PLAN`,
  exact). Piece 2: the thermal → mechanical chain on an axisymmetric model (T31 with a
  *Thermal stress* and `**ASTER-PLANE AXIS`: first `THERMIQUE` `AXIS`, then `STAT_NON_LINE`
  `AXIS` with the temperature field; reactions for 360 degrees, `stresszz` = hoop stress).
  Verification PL-58: the thick tube of PL-24 as T31 (10 steps, steady) equals PL-24 within
  1.0e-6 and the closed form (u_r 1.5e-5; stresses within 1.2%), the axial reaction
  2π α E ∫ θ r dr within 9e-7; PL-59 adds an internal pressure of 50 MPa (an edge load in the
  chain, within 7e-6). The result route `tabel`, contact, node-surface couplings, bonded
  contact and an initial velocity in the `AXIS` chain give an ERROR (welding and metallurgy in
  `AXIS` too).

- **Harmonic stresses with hysteretic damping are now the total stresses** (KNOWN_BUGS 120): E
  (1 + i eta) eps per material instead of Code-Aster's E eps, which was up to 11 % too low in
  amplitude at eta = 0.5 and wrong in phase; with different loss factors per material exact
  also at the nodes between them (HR-06e .. HR-06g, `PHYS` and `GENE`). Viscous damping stress
  (Rayleigh, modal damping) is not included. The WARNING about it is gone; a new WARNING when a
  material without `ELAS` cannot get its loss factor.

- **Element orientation card on shells and gaps compared with Mecway 35** (KNOWN_BUGS 116,
  removed): with an oblique U axis and a flipped normal the shell forces per length are equal
  to Mecway's (quad4 at every node, quad8 at mid-length) and the moments at the centre within
  1.4 % (LS-31f .. LS-31h); a formula is evaluated at the mean of all element nodes, as in
  Mecway (LS-31i, quad8 with moved midside nodes); a gap card along the gap equals no card
  (NL-92d). Mecway also computes a tension gap, a lateral offset and coincident nodes, which
  the bridge still refuses (KNOWN_BUGS 23); the transverse shear of DKT shells is 11 % low on a
  coarse mesh (KNOWN_BUGS 2).

- **S46 review continued** (KNOWN_BUGS): the harmonic WARNING about stresses without the loss
  factor (item 120) now only counts materials of solid elements, the only ones with stresses
  in that analysis (shell-only models no longer get it); a new WARNING when `#ASTER-HYST` is
  used in harmonic vibro-acoustics, where it has no effect (item 59); a new WARNING when a
  Wohler curve also applies to beams, trusses, cables or discrete elements, which get no
  damage (item 66); a WARNING when the constant of a constraint equation is written as an
  element `<constant>`, which Mecway 35 ignores (item 27); the curved-front WARNING of
  `#ASTER-XFEM` gives the measured +5.3 % at h = a/20 (item 83). New verification MO-11
  (modal mechanism in a supported model, item 48), NL-91 (results up to the last step
  after a real floating point exception `DVP_2`, item 118 removed) and NL-92 .. NL-92c (a
  closed gap equal to Mecway 35; open and with clearance against a hand calculation, item
  23). Items 5, 9, 10, 22, 23, 27, 34, 38, 46, 54, 55, 58, 63, 64, 65, 106, 107, 116, 121,
  123, 124, 131 and 135 corrected after a desk review against the code, headless runs or
  GUI tests in Mecway 35; item 37 (a second run in one session, also a table run after a
  liml run) removed after GUI tests. The WARNING for the Code-Aster alarm `POSTRELE_70`
  (route `tabel` with beams) now explains that it is harmless and when it matters.

## V2026.13 – 17 November 2026

2D and axisymmetric models get much further: nonlinear static (plasticity, large deformations)
and contact between edges of plane elements (also friction), through the line
`**ASTER-PLANE` in an L30/S30 model (contact in L30 only), and *Thermal stress* in Static 2D and Static
Axisymmetric (STAPPENPLAN S44a-c), with a rewritten 2D guide: a decision table of the two
input routes, worked examples on the repo's model files, figures and the exact messages.
Linear static and thermal runs keep their results after Code-Aster's time limit (S45 phase
1). The S46 review of all KNOWN_BUGS items (real bug or test setting, re-measured with
Mecway 35 and Code-Aster 17.4) brings new WARNINGs (an isotropic material without Young's
modulus, bonded shell faces, linear buckling with DKT shells or an eccentric general section,
harmonic stresses with hysteretic damping, friction on held slave nodes), several items
re-measured, corrected or removed, and the default `lin_solver_resi` 1e-5 instead of 1e-6.
Behaviour changes: the linear solves stop with `FACTOR_57` only above an estimated error of
1e-5 (KNOWN_BUGS 138), a pinned support on several nodes in 2D holds the mean displacement as
in Mecway (KNOWN_BUGS 134), an element offset is an ERROR in every 2D analysis (also S20/SA0),
and `MECA_STATIQUE` runs with `OPTION='SANS'` followed by the same
`CALC_CHAMP` of the stresses. Measured with Code-Aster 17.4 and Mecway 35 headless and offline
tests; NOT checked in the Mecway window. Full regression on c5c459f: 3168 of 3174 checks OK
(607 test cases), 6 BEKEND (KNOWN_BUGS 43, 83, 108, 115, as before), 0 NOK/FOUT, no status
change.

- **Default `lin_solver_resi` 1e-5** (was 1e-6, Code-Aster's default; KNOWN_BUGS 138, found and
  fixed in this release): a 160 x 32 quad4 plate and a 7281-node hex20 lap stopped with
  `FACTOR_57` at an estimated error of 1.7e-6 and 1.9e-6 although Mecway solves them; both
  compute now and the lap equals Mecway. A mechanism still gives an error of order 1. Applies
  to linear static, nonlinear static (imperfection), modal (prestress) and buckling (static
  step); the tooltip, Default settings and the error-message docs name the new value.
- **WARNING for an isotropic material without Young's modulus** (KNOWN_BUGS 60): the bridge
  computes it with E = 210 GPa, Mecway with E = 0. One WARNING per run lists the materials
  concerned; not for a hardening curve in total strain (which sets E), purely thermal or
  acoustic analyses, or parts named as a fluid.
- **WARNING for bonded shell faces** (KNOWN_BUGS 128): bonded contact ties the mid-surfaces of
  shells without the distance between them: a lap of two bonded 2 mm plates gives +13%
  deflection against a solid hex20 reference with a perfect bond (0.1498 mm in Code-Aster and
  Mecway; Mecway CCX -44%), plates bonded over their whole length up to 4x. The bridge warns
  for shell faces bonded face to face and for a shell face and a solid face bonded (either
  side), only for contacts that tie something. The coupling with the lever arm is step S47. The
  earlier "the bridge follows the theory" rested on a non-composite estimate and is corrected
  in the docs.
- **WARNING for linear buckling with DKT/DST shells** (KNOWN_BUGS 132): Code-Aster's DKT misses
  in-plane terms of the geometric stiffness and gives wrong factors for shell models of
  profiles (T beam of BU-43c: DKT only negative factors, `COQUE_3D` 26.64 / -19.91, Mecway on
  the same mesh 27.26 / 20.34). The WARNING names `COQUE_3D` (other advice when `COQUE_3D` fell
  back to DKT); DKT stays the default. Modal and buckling §3.5 and §4.
- **Buckling WARNING also for an eccentric general section** (KNOWN_BUGS 115): a General
  section whose `ASTER-SECTIE` line puts the shear centre off the centroid (distance above
  0.1 sqrt(A), as `bridge_custom`) gets the WARNING of T, C and L profiles with
  `POU_D_E`/`POU_D_T`: the geometric stiffness takes torsion about the centroid. The advice
  names `COQUE_3D` shells; the buckling factor of such a section is NOT measured.
- **KNOWN_BUGS re-measured and corrected**: item 1 (in Mecway 35, Mecway's hex8 is always
  incompatible-mode, whatever `<incompatiblehex8>` says; Mecway 35 values), item 2 (the shell
  difference is discretisation: Mecway and DKT/`COQUE_3D` approach each other within ~0.1%),
  item 135 (Mecway 35's GUI refuses a *Fixed support* on shell nodes (solid nodes and other
  versions not checked), so on shell nodes the case probably comes from generated or
  hand-edited `.liml` files or an older version; the WARNING stays as a safety net).
- **KNOWN_BUGS 82 removed**: reverse plasticity with the default deformation (`GDEF_LOG`)
  converges now (VM-11a to t = 3 s in 12 steps, within 0.1% of `PETIT`); Fatigue and
  Verification docs adjusted.
- **Thermal stress in 2D and axisymmetric** (STAPPENPLAN S44c): *Thermal stress* with
  *Temperature* (on nodes, edges or elements) or *Node temperature* in Static 2D (S20,
  `C_PLAN`/`D_PLAN`) and Static Axisymmetric (SA0, `AXIS`), as in 3D (`AFFE_VARC` `TEMP`, no
  thickness or 2π factor); still refused in D20/DA0. A tube with free plane ends via an `#ASTER`
  `LIAISON_UNIF` line. Verification PL-20 … PL-28: free expansion and held plates exact, a thick
  tube with a logarithmic temperature within 1% of Timoshenko & Goodier (σ_r 1.04%), and equal to
  Mecway 35's own S20/SA0 solution (headless, ≤ 1e-13). 2D docs §2.5.
- **Nonlinear static in 2D and axisymmetric** (STAPPENPLAN S44a): a Nonlinear Static (L30) or
  Static 3D (S30) model of plane shell elements in the XY plane with the line
  `**ASTER-PLANE C_PLAN|D_PLAN|AXIS` in the custom model definition is computed as plane
  stress, plane strain or axisymmetric (`STAT_NON_LINE` / `MECA_STATIQUE`): plasticity, large
  deformations (`GDEF_LOG`), time steps, load tables and temperatures as in 3D, reactions for
  the thickness or 360 degrees in every step. Verification PL-30 … PL-36: Hill's thick cylinder
  (perfect plasticity) in plane strain and axisymmetric within 2%, first yield at a hole in
  plane stress +1.8%, the Code-Aster test case ssnp159b through the bridge equal to its values.
  Not yet: the failure loop in 2D (contact: see the next item); opening such a result in the
  Mecway window is NOT checked. A plastic material in S20/SA0 now gives a WARNING (Mecway's 2D types are linear).
  2D docs §1.4.
- **Contact in 2D and axisymmetric** (STAPPENPLAN S44b): with `**ASTER-PLANE` in Nonlinear
  Static (L30) a *Contact* between edges of the plane elements becomes `DEFI_CONTACT` on edge
  cells, with the contact settings of 3D. Verification PL-40/41: a shrink fit of two rings
  (axisymmetric and plane strain), contact pressure within 0.01% of Lamé; PL-42: the
  Code-Aster test case ssnp121a (two blocks, plane strain) through the bridge within 0.3%,
  PL-43 the same in plane stress, PL-45 Hertz line contact (half-width −0.01%, peak
  pressure +0.38%), PL-46 Coulomb friction (a sliding block, −0.14%). Bonded contact in 2D
  stays an ERROR.
- **Contact with `SANS_GROUP_NO` on a quadratic slave** keeps `INTEGRATION='AUTO'` (it stopped
  with `CONTACT_97`; seen in 2D, 3D NOT verified). New KNOWN_BUGS 141: with friction, slave nodes held in the
  tangential direction give a singular matrix; the bridge warns and names the workaround
  (`**ASTER-ZONE SANS_GROUP_NO`).
- **Results after a time limit in linear static and thermal analyses** (STAPPENPLAN S45 phase
  1, KNOWN_BUGS 137 narrowed): `MECA_STATIQUE`, `THER_LINEAIRE` and `THER_NON_LINE` compute
  on past *Time limit run_aster*, after which the next command stopped with `SUPERVIS_63` and
  nothing was loaded (for `MECA_STATIQUE` already its own `CALC_CHAMP` of the stresses). After
  the solve the bridge now always gives Code-Aster extra time for the post-processing, at
  least max(600 s, 0.9 x the limit) from the end of the solve, and `MECA_STATIQUE` runs with
  `OPTION='SANS'` followed by the same `CALC_CHAMP` `SIEF_ELGA` it made itself. A solve that
  ended after the limit gives a note in the convergence window, and a WARNING when the run
  then ends without errors. Caveat: with warping beams (`POU_D_TG`) and the field reaction
  forces, the separate solve of the reactions after the extra time gets no extension of its
  own. Measured headless with Code-Aster 17.4 and a delay past a 30 s limit: FX-04,
  TH-02a (401 steps) and WE-04b (101 steps) loaded, results byte-identical to runs without
  the delay; the 291 verification cases whose `.comm` changes (252 linear static, 39
  thermal): 1180 of 1182 checks OK, 2 BEKEND as before, 0 NOK/FOUT, every value unchanged.
  NOT checked in the Mecway window. Not yet: modal, harmonic and the other linear
  analyses, and the thermal solve with filler material, *Thermal stress* or adaptive
  refinement (STAPPENPLAN S45b, low priority). Error messages `SUPERVIS_63`, settings for
  contact and nonlinear §2.7.
- **Checks of the 2D input** (S44a): an *Element offset* is now an ERROR in every 2D analysis,
  also Static 2D/Axisymmetric (S20/SA0, which computed with it before; the offset arms would
  add nodes outside the XY plane). `**ASTER-PLANE` without a value, or written without the
  hyphen (`#ASTER PLANE ...`), stops the run with an ERROR.
- **KNOWN_BUGS 140 (new)**: with `DEFORMATION='GDEF_LOG'` the sum of `REAC_NODA` is about 2e-4
  off the applied force (Code-Aster's behaviour, measured on PL-32).
- **README and user guide**: the bridge is provided without warranty; check results
  independently.
- **KNOWN_BUGS 139 (new)**: Mecway with CCX gives exactly half the thermal expansion of a shell
  plate under a temperature (Mecway's internal solver and the bridge give α ΔT x).
- **Pinned support on several nodes in 2D holds the mean displacement** (KNOWN_BUGS 134):
  measured in Mecway 35 (Static 2D), its pinned support on nodes is the unweighted mean, as in
  3D; the bridge now writes `LIAISON_DDL` with equal weights on DX and DY instead of holding
  every node (verification PL-07, equal to Mecway). On edges Mecway holds nothing in 2D; the
  bridge keeps every node there with a WARNING. Behaviour change for 2D models with a pinned
  support on several nodes.
- **WARNING for harmonic stresses with hysteretic damping** (KNOWN_BUGS 120): Code-Aster's
  `CALC_CHAMP` computes the stresses of a harmonic result without the loss factor: the right
  complex stress is (1 + i eta) times the given one, so the amplitude is low by
  sqrt(1 + eta^2) (0.5% at eta = 0.1; measured on a bar in tension against F/A) and the
  phase is off by atan(eta). The bridge now says so, with the size, when stresses are requested;
  displacements are right.
- **Springs and dampers compared with Mecway** (KNOWN_BUGS 47): with the ground nodes held
  by *Displacement* Mecway 35 equals the bridge in a modal analysis and in a dynamic response
  with a damper (Newmark, to 1e-7; new verification DY-04a/b); earlier failures came from a
  *Fixed support* on spring-only nodes, which Mecway ignores.
- **KNOWN_BUGS 41 removed**: an imposed displacement from a time table with kinks off the
  explicit step (`TCHAMWA`, `DIFF_CENT`) follows the table: the kinks become `INTERVALLE`
  boundaries, the end face is within 4e-13 m, also with kinks 2 to 3 steps apart (new
  verification DY-20d/e).
- **2D/axisymmetric docs**: a decision table of the two input routes, step-by-step examples with
  the model files, new figures (route A/B, tube slice, plate with hole, contact edges) and the
  exact messages.
- **STAPPENPLAN**: user priorities of 11 Nov 2026 (S5b dropped, several steps later), the S46
  procedure with a progress table of all KNOWN_BUGS items, and the new step S47.

## V2026.12 – 11 November 2026

Results survive Code-Aster's time limit: a nonlinear static or nonlinear dynamic run (also
thermomechanical) that stops on *Time limit run_aster* now loads the steps computed so far; the
step loops of element failure and welding stop before the limit, mesh adaptation ends on it.
*Hide failed elements* gets the core `liml_failed.py` 1.0.5, and a *Fixed support* on shell,
solid or truss nodes, which Mecway's own solver leaves free, now gives a WARNING. Behaviour
changes: the other node values of a hidden element follow its original node instead of being 0,
a support node stays in place even when all its elements fail, and hidden results carry the
marker `failed_hidden` instead of the attribute `limlfailed`. Measured with Code-Aster 17.4
headless and offline tests; NOT checked in the Mecway window. The generated `.comm` of 121 of
the 578 comparable verification cases changes (every nonlinear case); those plus the fastest
case of every group (147 cases) gave 632 of 635 checks OK, 3 BEKEND (KNOWN_BUGS 43, as before);
a final run of 43 cases on the release code gave 280 of 280 OK. No status change.

- **Hide failed elements: core `liml_failed.py` 1.0.5** (copy of AdvancedToolsHub's, was
  1.0.0). Behaviour change: the other node variables of a collapsed node follow the node it
  copies, instead of being 0 from the failure on; only the displacement collapses, so the
  legends of the other variables stay as without hiding. A support node whose elements all fail
  no longer collapses: it stays in place with its real displacement and reaction; a reaction
  group that is only round-off (forces of a beam under a pure moment) marks no supports. An
  empty `<solution configuration=... />` is its own solution, so the core never reads into the
  next one.
- **WARNING for a Fixed support on nodes that Mecway leaves free** (KNOWN_BUGS 135): on a node
  selection Mecway's own solver holds only nodes with all rotational DOFs (beam nodes,
  reference nodes of couplings) and silently leaves shell, solid, 2D and spring-only nodes free
  (measured with Mecway 35 on quad and hex nodes; trusses, tension-only elements, gaps and
  dampers count by the manual's rule, NOT measured). The bridge keeps clamping them, as before,
  and now names per node selection how many nodes Mecway would leave free, with the advice to
  clamp on faces; truss models get this WARNING too. The generated `.comm` does not change.
  KNOWN_BUGS 95 (shells expanding less under a temperature) is withdrawn: it came from such a
  support.
- **New marker of hidden results**: the global variable `failed_hidden` (the number of hidden
  elements) as the first line in `<results>`, instead of the attribute `limlfailed`. A save in
  Mecway keeps it (Mecway 35), so hiding again and "Section in results" refuse a saved file by
  its marker; files of V2026.11 are still recognised, except when every failed element shares
  nodes only with other failed elements (see Failure §4). Where Mecway's result list shows the
  variable is NOT verified in the Mecway window.
- **Results after the time limit** (nonlinear static and dynamic, thermomechanical): when
  Code-Aster stops on *Time limit run_aster* (`MECANONLINE9_1`/`9_2`, `SUPERVIS_63`), the
  bridge now gives it extra time for the post-processing, so the steps computed so far are
  loaded; before, Code-Aster skipped the post-processing and nothing was loaded. The step
  loops of element failure and of filler material in welding stop themselves before the
  limit, the adaptive mesh loop (HOMARD) ends on a time stop, and a limit reached only in the
  post-processing gets the same extra time. The status box and the convergence window say so,
  and the status box advises raising the time limit; the tooltip of `time_limit` now says it
  is wall-clock time of which Code-Aster keeps 10 % to close. Linear and thermal analyses
  still lose the results (KNOWN_BUGS 137). Measured with Code-Aster 17.4 headless; NOT
  checked in the Mecway window.

## V2026.11 – 11 November 2026

Failed elements can disappear in Mecway's own result view: the new option *Hide failed
elements* hides each element from the first step after its failure. The element variable
`failed` changes with it: it is now 1 from that step on, no longer at the failure time itself.
The convergence window keeps a long file path readable and sits under Mecway's taskbar button.
Checked in the Mecway 35 window: the new option with `BezwijkenTrekstaaf`, the ParaView and
AsterStudy buttons of V2026.10, and the taskbar. The generated `.comm` of all 578 comparable
verification cases is unchanged; a limited regression of 45 cases gave 249 of 249 checks OK.

- **Convergence window**: a long path of the file shown wraps over several lines instead of
  running under the buttons; started from Mecway, the window sits on the taskbar under Mecway's
  button (Mecway in Program Files; verified with Mecway 35).
- **Hide failed elements in Mecway** (new setting `hide_failed`, "Hide failed elements", page
  General, off by default): after a run with the route `liml` and after Results... > Load,
  failed elements disappear in Mecway's own result view, each from the step after its failure
  (their nodes collapse onto the centroid; exact at deformation scale 1). The core
  `liml_failed.py` is a copy of AdvancedToolsHub's; contract `failed/1` in `AGENTS.md`.
  "Section in results" refuses results with hidden elements.
- **Behaviour change of the element variable `failed`** (and the VTU array of the same name):
  it is now 1 from the first stored step *after* the failure time, no longer at that time
  itself. The step at the failure time shows the computed state that made the element fail; its
  stress is about 0 from the next step on (measured with `BezwijkenTrekstaaf`). An element that
  fails at the last stored step keeps `failed` = 0.

## V2026.10 – 10 November 2026

The bridge opens its results outside Mecway itself: buttons *ParaView* and *AsterStudy* in the
Results dialog and in the convergence window, with one search for Salome-Meca (also
`C:\SALOME-MECA\<version>`). It no longer depends on AdvancedToolsHub (MWHub Post) and no longer
writes the files that existed only for it. Behaviour changes: the setting
`advancedtoolshub_dir` is gone, `salome_meca_dir` is new, and the VTU cell array of failed
elements is called `failed` instead of `BEZWEKEN`. The generated `.comm` of all 578 comparable
verification cases is identical to V2026.9; a limited regression of 56 cases gave 286 of 287
checks OK, 1 known limitation, 0 unexpected, no status change.

- **No coupling with AdvancedToolsHub any more**: the bridge no longer opens runs in MWHub Post.
  The button *In MWHub Post* of the Results dialog and the setting `advancedtoolshub_dir` are
  gone. An older `bridge_utils.py` that still has the setting keeps working (the line is
  ignored).
- **Buttons ParaView and AsterStudy** in the Results dialog (for the run chosen in the list; the
  dialog stays open) and in the convergence window (for the run shown). *ParaView* opens
  `_verfijnd.rmed` or `_xfem.rmed` when present, else the `.pvd` (`vtu_export`), else the
  `.rmed` (`med_export`), and names the other result files of the run; a `.rmed` opens in
  Salome-Meca's ParaView (the official ParaView 6.2.1 does not load its MEDReader plugin), a
  `.pvd` in the official ParaView 6.x, and `paraview_exe` still
  overrides the search. *AsterStudy* opens the MED file in Salome-Meca, AsterStudy, tab
  *Results*, through a session script `<file>_salome.py` next to it (a new Salome-Meca session
  per click; a second click within 60 s only gives a message). What the started program
  reports goes to `<run>_paraview_launch.log` or `<file>_salome_launch.log` and
  `<file>_salome_session.log`. New setting `salome_meca_dir`
  (empty = search `C:\SALOME-MECA`, `C:\Salome_meca` and `%ProgramFiles%\SALOME*`). Both buttons
  were started from a hidden Mecway 35 and from the convergence window's Python (ParaView 6.2.1,
  Salome-Meca 2025); clicking them in the Mecway window is NOT verified.
- **No beam sidecar and node series any more**: a run no longer writes
  `<model>_<run-id>_beams.json` (came with *VTU/PVD files for ParaView* or *MED file for
  ParaView*) and `<model>_<run-id>_knopen.csv` (came only with *VTU/PVD files for ParaView*);
  both existed only for MWHub Post. The `.pvd`/`.vtu` files are otherwise unchanged and keep the
  beam forces per element end (`EFGE_*`) for plain ParaView.
- **VTU array `failed`**: the cell array of failed elements in the `.vtu` files is now called
  `failed` (Mecway's own variable name) instead of `BEZWEKEN`; a ParaView state that thresholds
  on `BEZWEKEN` needs the new name.

## V2026.9 – 10 November 2026

Beams with a general section show the stress over their section in Mecway, and `POU_D_TG`
beams get the right stresses and reactions in buckling and modal with prestress, and the right
reactions in linear static. The main window and the convergence window fit a display scale of
125 %. Behaviour changes, among others: the `.comm` of models with `POU_D_TG` beams (an extra
elastic `STAT_NON_LINE` step), a force on shell faces selected on both sides (now the full
Mecway force, was half), and a pinned support in 2D. The full regression ran 579 cases: 3066
of 3072 checks OK, 6 known limitations, 0 unexpected, no status change against the previous
run. The verification model AD-02 and its load models AD-02-L1 .. L5 are now saved by Mecway 35.

- **Main window**: one button *Section ▾* with a menu (show, hide, in results) replaces the two
  section buttons; *Explanation...* is gone (the glossary is the first item of the page
  Documentation). The navigation list has a clear scrollbar of its own (mouse wheel, drag, click
  on the track, PageUp/PageDown) and is as wide as its longest page title needs. At a display
  scale of 125 % the label column, the info line of an analysis page, the document list and the
  status box grow with the text, and a small window no longer gets a horizontal scrollbar on
  General. *Hide section* only removes the shape; *Show section* on a shape that is already
  shown draws it anew. The save note shows `Scripts\bridge_utils.py` instead of the full path.
- **Convergence window**: the buttons and the top bar have the look of the main window (dark
  bar, flat white buttons with a hover colour, grey text when disabled; colours shared through
  `bridge_style.py`). At 125 % the legends, axis captions, rows and the cards of a linear
  analysis no longer run into each other. The messages box is six lines high and keeps that
  height in a low window; the plots shrink instead.
- **Stress over beam sections in Mecway**: after a Code-Aster run the beams with a general section
  with an outline, and Mecway's I, T, L and C, show per element end the largest von Mises,
  longitudinal and shear stress over the section outside the corner zones (`beamvonmisesmax`,
  `beamsixxabsmax`, `beamtaumax`). The shells of *Section in results* show von Mises and shear
  stress at the outline (`sectionvonmises`, `sectionshear`; `doorsnedevonmises`, `doorsnedeschuif` in
  Dutch) next to `longitudinalstress`. The calculation runs in the Code-Aster job from `beam_forces`
  with a copy of the section code of MecwayAdvancedBeamAnalysis; a new file
  `<model>_<run_id>_section.json` carries the table for the shells. The `.comm` does not change. A
  run without numpy or scipy, or without an outline, goes on with a WARNING. Verified by hand on T, U,
  I, C and L cantilevers (LS-97a..l). No warping stress.
- **Large-rotation beams, coarse steps**: two new verification cases with `POU_D_T_GD`: a
  cantilever rolled into a full circle in 8 steps (NL-81c) and the elastica in 6 steps (NL-83b);
  both pass with the bridge as it is. `PREDICTION='EXTRAPOLE'` was measured as an alternative
  Newton prediction and made these runs stop early (KNOWN_BUGS 11), so the bridge keeps
  Code-Aster's tangent prediction. No `.comm` of an existing case changes.
- **`POU_D_TG` beams: stresses and reactions from one elastic step**: outside `STAT_NON_LINE`
  Code-Aster 17.4 computes the stresses of `POU_D_TG` wrongly (`te0342.F90`: shear factor, no
  shift to the shear centre, no thermal strain); the reactions per node and the geometric
  stiffness inherit it, while the sum of the reactions stays right (KNOWN_BUGS 123). Buckling,
  modal with prestress, imperfection and dead loads now take the stress state from one
  elastic `STAT_NON_LINE` step, and linear static takes its reactions from it. Before, a C
  cantilever gave a buckling factor of 1.60 instead of 54.3. Only the `.comm` of models with `POU_D_TG`
  changes. The nodal reactions of a spectrum analysis stay wrong, with a WARNING; with `#ASTER-XFEM` the
  reactions stay those of `MECA_STATIQUE`, without a message; the cyclic route has not been run
  with `POU_D_TG`. New
  verification LS-96 .. LS-96g, BU-45 .. BU-45d, BU-46, MP-20, MP-20b.
- **Keep the Code-Aster base of a static run**: new settings `keep_base` and `keep_base_runs`,
  off by default. A kept base gets a manifest (schema 2: components, beam axes, offsets,
  connected nodes) after a run that ended well, for a follow-up run by MecwayFreebody. With the setting off, mesh and `.comm` stay the same.
- **Translation fixes**: a force on shell faces selected on both sides (faceid 5 and 6) gives
  the Mecway force (was half); an elastic support or compression only on such a selection
  gives an ERROR instead of stopping with a Python error; a pinned support in 2D on nodes or
  edges becomes `DX = DY = 0` (edges were refused, several nodes stopped Code-Aster);
  `#ASTER-XFEM groep=` is checked with the Code-Aster name of the selection; thermal face
  loads on faces of elements that are not modelled; the bonded relations of the bridge are
  written with a decimal point under a Dutch Windows locale; trusses take part in line loads
  and gravity; hydrostatic and formula pressures stay fixed next to a follower pressure on
  the same selection; the own nodes of flexible joints, offsets and pre-tension copies get the
  temperature of their Mecway node; prestress and buckling with only connections between
  parts stop with an ERROR before Code-Aster, and an `#ASTER-EXCIT` load counts as a support in
  modal and buckling (no false ERROR or free-free).
- **Section table of another version**: a `<model>_<run_id>_section.json` of another version
  gives a WARNING with both versions instead of being passed over, and its warnings are still
  logged; a file that cannot be read gives a WARNING.

## V2026.8 – 6 November 2026

Beams with a general section are easier to get right: the bridge warns when a beam does not
fit its section or needs warping, a run that stops with `FACTOR_57` says so, and the status
window no longer stays in front. The `.comm` of 550 regression cases is unchanged. The new
checks ran in tests and on Code-Aster runs outside Mecway, not yet in the Mecway window.

- **Check of the direction of a general section**: MecwaySectionProps can store the directions
  a section was made for as a `** SECTIE-RICHTING` line. For every beam of that material a
  WARNING goes to the log and the status box when its V axis is more than 1 degree off (the
  section is turned and the results are wrong), when it runs against the direction (the beam
  sees the section mirrored), or when it is more than 1 degree from parallel. On a run for all
  beams, with "Show section" and "Section in results" for the drawn beams. Mesh and results do
  not change; a model without the line gets no check and no message. User guide §4.3.
- **Beam without warping on an open section**: a WARNING when the shear centre of a general
  section lies more than 10% of the square root of the area from the centroid and the beam
  is not `POU_D_TG`. Measured against a solid model: `POU_D_TG` within 1.2%, `POU_D_E` 5.6
  times too much twist.
- **`FACTOR_57` is reported clearly**: Code-Aster writes `DIAGNOSTIC JOB : OK` after this stop.
  The convergence window and the summary now say the run stopped, the status box names the
  cause and not only the missing results, and the error size no longer reads "0" in Mecway.
- **Screens in the user guide**: numbered images of the main window, the section buttons and
  the status window, with every button explained, in Dutch and English.
- **User guide**: §4.3 now describes how to make a General section beam with
  MecwaySectionProps, step by step, and §1 names the tool.
- **Status window of a run**: on top only during the first 10 seconds, while the Code-Aster
  console opens. After that it is a normal window, so a window you click (the convergence
  window) comes in front. It now has a taskbar button, as the way back to Stop.

## V2026.7 – 6 November 2026

Buckling of slender columns with `POU_D_T_GD` beams (issue #10): the imperfection now works
with these beams, a new step guard keeps the column on the stable branch above the buckling
load, and a jump check warns when it left that branch. Two behaviour changes for models with
`POU_D_T_GD` beams in nonlinear static: steps can be cut (more archived steps in Mecway), and
every static run gets the jump check. Models without these beams compute as before. A
general section from MecwaySectionProps can now be shown with its real shape on the beams,
before a calculation and in the results. Tested with Code-Aster 17.4 and in the Mecway 35 GUI
(column of issue #10, T cantilever); Mecway 34 was not available for these two. The limited
regression ran 76 cases; the stored results stand at 551 cases, 2986 checks (2980 OK, 6 known
limitations, 0 unexpected).

- **`imperfection_amplitude` works with `POU_D_T_GD` beams**: the linear buckling beforehand
  runs on an auxiliary model with `POU_D_T` (`POU_D_T_GD` has no `RIGI_MECA`), the nonlinear
  run stays on `POU_D_T_GD`. It is an ERROR only together with `#ASTER-EXCIT`; `crit_stab`
  with `POU_D_T_GD` stays an ERROR. New verification NK-06 and NK-10.
- **New setting `gd_step_limit`** (page Nonlinear static, group Nonlinear buckling; default
  0.02, 0 = off; only with `POU_D_T_GD` beams): above the buckling load Newton with a coarse
  step lands on the unstable branch, the job ends OK and the column looks straight (column
  L = 2.5 m with 10, 20 and 40 line3 at dt = 0.01). A step is now cut (`DEFI_LIST_INST`
  `ECHEC` `DELTA_GRANDEUR`, `DECOUPE`) when a displacement component of these beams grows
  more than this fraction of their largest dimension; the column then gives 926.4 mm against
  926.7 mm for the exact elastica. **Behaviour change:** extra archived steps appear in Mecway
  (137 instead of 101 for that column), and the large-bending cases take about 5 s instead of
  about 3 s. With 0.05 the column with 10 line3 still jumped, hence 0.02. New verification
  NK-05 and NK-05b.
- **The run continues when cutting cannot help**: with a load present from the start or a
  real snap-through the job goes on from the last archived state without the guard
  (`BRIDGE_VANGNET` in the `.mess`), the status box says from which t, and the run is not
  reported as failed; the exception (`MECANONLINE9_50`, `MECANONLINE9_7`) stays visible in the
  `.mess`. New verification NK-07, NK-08 and NK-09. Limitation in KNOWN_BUGS 53 (f); arc length
  (`PILOTAGE`) is not built.
- **Jump check after every static run with `POU_D_T_GD` beams**, also with the guard off:
  when the displacement of a node falls below 50 % of the step before, a WARNING goes to the
  log and the status box. Nodes that moved less than 1 % of the size of the beams do not
  count, nor do intervals in which a load table falls; a formula in time is not looked at.
- **Clearer messages**: the status box now names `POU_D_T_GD` when beams stay geometrically
  linear in a nonlinear static analysis with large displacements, the imperfection WARNING
  names `POU_D_T_GD`, and "add an imperfection" appears only without an imperfection.

- **Shape of a general section on the beams**: MecwaySectionProps stores the outline of a
  section as `** SECTIE-VORM` lines in a custom model definition (with *Store extra Code-Aster
  properties and the shape*). The new button "Show section" shows it on general-section beams
  as temporary elements, before a calculation; they go on a second click, on closing the
  bridge, at the start of a run or Results... and at the next start after a crash. The new
  button "Section in results" puts the shells in the `<solution>` of the `.liml`, with their
  values, and reopens it; this happens automatically once at the end of a Code-Aster run when
  an outline exists. The model part stays unchanged and a `.bak` is kept. New variable
  `longitudinalstress` (`langsspanning` in Dutch): stress along the beam from normal force and
  bending, without shear from shear force or torsion and without warping bimoment. Every
  other result is on the shells as well, so that the shape does not turn black. In the results
  Mecway's rectangle becomes a thin bar (at most 2 mm, scaled on the section and its wall), in
  the solution only. The `.liml` grows: up to about 8 times for a model with only beams.
  Modal solutions show the shape without stress, plastic materials have no stress variable,
  cyclic models are refused. Verified on Mecway 35 only; Mecway 34 was not available. User
  guide §4.3.

## V2026.6 – 29 October 2026

Orthotropic material, bolt pretension (*Pre-tension section*), beams with warping
(`POU_D_TG`), 2D and axisymmetric analyses (static, dynamic, acoustic), adaptive refinement with
HOMARD, loads on beam side faces and hydrostatic pressure on shell edges, principal values of
shells and Green-Lagrange principal strains, a summary file of every Code-Aster run (issue #7)
and the fixes for issue #9 (frictionless next to a fixed displacement, free-free modal
analysis). Two behaviour changes: Green-Lagrange principal strains and the time step with
*Generate solution every n time steps*. Tested in Mecway 34 with Code-Aster 17.4; verification
544 test cases, 2963 checks (2957 OK, 6 known limitations, 0 unexpected).

- **Windows readable at a larger Windows display scale (e.g. 125 %)** (KNOWN_BUGS 129): the
  header of the main window, the Results window and the status window is sized from the
  title, so the subtitle (model, analysis, work folder) is no longer half hidden under it;
  buttons are as wide as their text ("Convergence window" was cut to "Convergence windo");
  the explanation in the Results window, the notes on the settings pages, the trademark
  notice and the texts of the status window get the height their text needs. At 100 % the
  windows look as before.
- **L profiles with the horizontal leg longer (a > b): bending axes as Mecway**: the bridge
  took the other principal axis as V for such an L, so `IY` and `IZ` were swapped (with every
  beam element; an L 120 × 80 × 8 cantilever bent about 5.6 times too much in one direction).
  Mecway wraps the principal angle into (−45°, 45°] (measured headless with Mecway 34 from its
  stress recovery points and tip rotations). New verification LS-95 (equal to Mecway).
- **POU_D_TG: shear centre of C and L profiles on the right side**: Mecway's W axis points
  from the flanges of a C profile to its web (measured headless from Mecway's stress recovery
  points), so the shear centre lies at +W and `EZ` < 0; the bridge had it at −W, so a
  transverse load through the centroid twisted the beam the wrong way (buckling under axial
  force was not affected). The beam sidecar for MWHub Post draws C and L profiles the same
  way. New verification LS-94/LS-94b (C, twist sign and size −0.4%), LS-95b (L, −0.005%) and
  LS-90d (bimoment at a clamp through `#ASTER-POST`, +0.5%).
- **Buckling with POU_D_TG beams**: the INFO line about torsional buckling without warping
  (`POU_D_E`/`POU_D_T`) is only logged when the model has beams without warping; with
  `elem_beam` = `POU_D_TG` only the line about warping beams remains.
- **Acoustic Resonance 2D (A20) with the harmonic analysis: clearer ERROR** (KNOWN_BUGS
  126): the message now says why the harmonic pressure field is not translated in 2D:
  Mecway has no 2D harmonic acoustic input (no frequency or source; an A20 model with a
  fluid pressure other than 0 gives no solution in Mecway 34). For a harmonic pressure
  field use a 3D model (A30) with `acoustic_harm_3d`. Documented in Acoustics §3.5.

- **Bonded contact between solids ties only the slave nodes Mecway ties** (KNOWN_BUGS 128):
  a slave node without a master face opposite it (for example where one plate overhangs the
  other) was tied to the nearest edge of the master, however far away, which made the joint
  much too stiff (Samples/BoltedJoint with bonded contacts: 0.096 mm against Mecway's
  1.90 mm). The bridge now applies CCX's `*TIE` rule, which Mecway uses: tied are the nodes
  with a master face opposite them (in-face tolerance 2.5% of a typical element size) and
  within the *Tolerance* of it (0 = that same default). The other nodes stay free, with a
  WARNING listing them. BoltedJoint (bonded) is now equal to Mecway; new verification
  LS-07l/m. With shells the same rule holds without a distance limit (Mecway ignores the
  tolerance there); the untied nodes equal CCX's, the displacements still differ from Mecway
  (KNOWN_BUGS 128).
- **Loads on the side face of a beam** (was not translated, KNOWN_BUGS 5): a *Traction* on
  the side face of beams or trusses becomes a distributed load traction × perimeter of the
  section (`FORCE_POUTRE`, global direction, also with a formula in x, y, z), as Mecway 34
  computes it (measured headless for all section types). A *Pressure* on the side face has
  zero resultant: Mecway's own solver applies nothing, the bridge neither (WARNING).
  Verification LS-92a .. LS-92h.
- **Hydrostatic pressure on shell edges** (was not translated, KNOWN_BUGS 5): consistent
  nodal forces of ρ g (h − z) × thickness on the edge, also when the free surface lies inside
  an element. Mecway's own solver applies no hydrostatic pressure on shell edges (manual
  §9.17); the bridge says so with a WARNING; compared with Mecway through the same load as a
  Pressure formula on the edge (equal within 0.01%). Verification LS-93a .. LS-93c.
- **Orthotropic and anisotropic material on solids** (STAPPENPLAN S13a): Mecway's
  *Orthotropic*, *Stiffness matrix* and *Compliance matrix* materials are translated in
  Linear and Nonlinear static, Modal, Buckling and implicit Dynamics to Code-Aster `ELAS_ORTH` (also thermal expansion in U, V, W), with Mecway's
  element axes U, V, W (*Element properties*, an *Element orientation* card with angle or
  formula, or the global axes by default) as `AFFE_CARA_ELEM` `MASSIF` `ANGL_REP`. A matrix is
  translated when it is orthotropic in the element axes; a truly anisotropic matrix (coupling
  terms) gives an ERROR, because Code-Aster has no general anisotropic elasticity for solids.
  *Orthotropic* on linear shells (DKT/DST) in Linear static: a one-layer `DEFI_COMPOSITE` with
  Mecway's U (default the edge from node 1 to 2). Quadratic shells, *Composite* laminates and
  the other analyses: clear ERROR (steps S13c, S13e). Cube in uniaxial tension and free
  thermal expansion with turned axes equal to Hooke's law and to Mecway's own solve; orthotropic
  cantilever in two orientations, also its frequencies, buckling load, large deflection and
  step response, shells (verification OR-01 .. OR-22; docs Orthotropic material). With the field *stresses*, linear static also
  writes Mecway's *stress in element coordinates* (`lamuu` .. `lamwu`) of the solids, with
  Mecway's averaging rule (S13d, OR-11).

- **Adaptive refinement with HOMARD for thermal and nonlinear static** (new setting
  `adapt_homard` on the pages Thermal and Nonlinear, with `adapt_homard_target` (default 0.3%),
  `adapt_homard_max_loops` and `adapt_homard_max_elements`): Code-Aster refines the mesh
  itself in one run (solve, ZZ error indicator, HOMARD `MACR_ADAP_MAIL`, solve again) and the
  result comes back onto the original Mecway mesh with `PROJ_CHAMP`; the Mecway model stays
  unchanged. Curved boundaries (cylinders, spheres) are recognised automatically for boundary
  following; `#ASTER-RAND` per face selection overrides. First version: solids with loads and
  constraints on face selections (clear ERROR otherwise). Plate with a hole: the peak heat
  flux and the plastic peak stress within 1% with 2.3 to 3.2 x fewer elements than uniform
  refinement (verification AD-10 .. AD-12; docs Error estimator §7).

- **Principal stresses, Tresca and principal strains of shells** (fields `principal_stresses`
  and `principal_strains`): on the top, middle and bottom surface under Mecway's names
  `principal1u1` .. `principal3b1`, `trescau1/m1/b1` and `lprincipalstrain1u1` ..
  `lprincipalstrain3b1`, computed as Mecway 34 does (eigenvalues of the global tensor of the
  surface per element node, node value = mean). Principal strains of shells no longer need the
  field `strain`. Verification FX-04.
- **Green-Lagrange principal strains under Mecway's names** (**behaviour change**, nonlinear
  analyses only): with large displacements (Green-Lagrange strain) the principal strains are
  now written as `greenlagrangeprincipalstrain1..3` (was
  `lprincipalstrain1..3`), as Mecway 34 itself does; the formula symbols `GLe1`..`GLe3` work,
  and `e`, `g`, `e1`..`e3` in a formula read the Green-Lagrange values there (Mecway rewrites
  them to `GLe`, ...). Linear analyses keep `lprincipalstrain1..3`; results loaded earlier
  keep the old name. Verification FX-05.
- **Summary of every Code-Aster run (GitHub issue #7)**: after every run (route `liml` and
  `tabel`, also a failed or stopped run) the bridge writes `<model>_<run-id>_aster_summary.txt`
  in the work folder: errors and alarms with their count, nonlinear steps, bridge lines,
  timings, the end of the `.mess` and the path of the full `.mess`, so it can be read after the
  Code-Aster windows have been closed. New button "Summary" in the Results window and in the
  convergence window (makes the file from the `.mess` when it is missing). Setting
  `aster_summary`: `summary` (default), `full` (a copy of the whole `.mess`, start and end above
  4 million characters) or `off`. Optionally (`save_monitor_liml`, off by default, route
  `liml`) the same text goes into the `.liml` as Mecway's own *Saved monitor* item under
  *Solution*; a run without results then only gets a solution with the monitor when the model
  has no results yet. Format measured headless in Mecway 34 (user guide §5.2).
- **Frictionless or symmetry next to a displacement 0 on the same nodes (GitHub issue #9)**:
  e.g. a round plate with *Frictionless support* on its rim edges and *Displacement* X, Y, Z = 0
  on the rim nodes stopped in Code-Aster with `ALGELINE3_81` (in a static analysis a singular
  matrix): the radial relation and DX = DY = 0 are linearly dependent. Mecway reduces such a
  set itself; the bridge now drops the part of the relation that the imposed displacement or
  rotation already fixes (INFO line in the log). Clamped circular plate (Dlubal 0109): all six
  frequencies within 0.25% of the analytical values and within 0.18% of Mecway (verification
  MO-09, LS-83). The explanation of `ALGELINE3_81` now also mentions duplicate constraints.
- **Modal analysis of an unsupported assembly** (remark in issue #9): a model whose only
  kinematic conditions are connections (bonded contact, rigid or distributing couplings) now
  takes the free-free route, so the rigid body modes come out with ~0 Hz instead of
  `ALGELINE3_81` (verification MO-10).
- **Beams with warping: `elem_beam` = `POU_D_TG`** (STAPPENPLAN S19, KNOWN_BUGS 115): a fourth
  beam choice on the Elements page (default stays `POU_D_E`). Code-Aster's Timoshenko beam with
  the warping degree of freedom `GRX`, the shear centre (`EY`, `EZ`), the warping constant `JG`
  and the Wagner terms (`IYR2`, `IZR2`) in `RIGI_GEOM`, so flexural-torsional and
  lateral-torsional buckling of open profiles (T, C, L, I) appear. The values come from an
  `#ASTER-SECTIE` line of MecwaySectionProps, or are computed for Mecway's I, T, C and L
  profiles with thin-walled formulas (`bridge_warping.py`; the angle of Code-Aster test case
  ssll103a within 0.12%); a general section without such a line gets `JG` = 0 with a WARNING.
  New setting `beam_warping` (`auto`/`free`/`blocked`): with `auto` the warping is fixed where
  a bending rotation is fixed (Fixed support, clamp, rigid coupling) and free at a fork support
  and elsewhere; Code-Aster's `BLOCAGE` alone does not fix `GRX`. Verification BU-38 .. BU-42,
  LS-90, LS-91: C column 384.98 (theory 386.1, hex20 393.0; `POU_D_E` 616), I beam
  lateral-torsional buckling −0.10% from Timoshenko & Gere, ssll103a equal to `VALE_CALC`,
  torsion with restrained warping −0.09%. Nodal reactions of `POU_D_TG` are off in Code-Aster
  17.4 (WARNING, KNOWN_BUGS 123). In explicit dynamics the beams become `POU_D_T` (WARNING; no
  mass for the warping degree of freedom). Not yet tested in the Mecway GUI.
- **Pre-tension section (bolt pretension, step S15)**: Mecway's *Pre-tension section* on a
  prism of solid elements is now translated in linear and nonlinear static analyses, with a
  force or a length adjustment (constant, table or formula in t). The bridge finds the prism
  and the section as Mecway does, cuts the mesh there and couples the two sides with
  `LIAISON_DDL` to a reference node whose DX is the shortening (the CCX formulation); the force
  stays applied during the whole analysis, the length adjustment locks the length, both as in
  Mecway. Verification PT-01 .. PT-05: exact against the hand calculation (bar, tet mesh with a
  zig-zag section) and the joint diagram within 0.1%, equal to Mecway 34's own CCX solve within
  0.01%. Not: dynamic response and Mecway's spring element variant (ERROR, KNOWN_BUGS 124).
  New document docs/Boutvoorspanning.md / docs/en/Bolt_pretension.md.
- **Pre-tension section in dynamics and on a spring (step S15b)**: the prism variant now also
  works in Dynamic response (D30/D31, implicit `dyna_impl_3d`). As in Mecway (CCX deck of a
  headless solve: one dynamic step, `AMPLITUDE=STEP`) a constant force or length adjustment
  acts as a step from t = 0, without a static preload step; a table or formula in t follows
  its time course. Mecway's spring element variant (internal solver: the face of one spring
  with a length adjustment) is translated in linear static as two nodal forces k × adjustment
  that pull the spring's nodes together; like Mecway, the bridge uses the length adjustment
  for a spring also when *Force* is chosen. Verification PT-06 .. PT-10: period and peak of
  the dynamic joint within 0.06% of Mecway 34 with CCX (hand calculation within 0.6%), the
  springs exact and equal to Mecway's internal solver. Not: explicit dynamics, and the spring
  variant in Frequency/Buckling, where Mecway also gives the tensioned spring a geometric
  stiffness (ERROR, KNOWN_BUGS 124). Mecway's dialog only allows *Length adjustment* for a
  spring (writes `adjustment="true"`). A model of springs only is no longer stopped with "No
  materials found" (checked in the Mecway GUI: PT-09 −0.25 mm, equal to Mecway).
- **Pre-tension section: reactions**: the reference node of the section was counted in the
  sum of reactions (status box: FX −10000 N for a self-equilibrated bolt) and, lying on a
  Mecway node, shown as a reaction there; it is now left out (PT-01/02/05 check the sums: 0).
- **Parts held only by contact** (KNOWN_BUGS 43): in nonlinear static the bridge now reports,
  before the run, every part that has no support, bonded contact, coupling or spring of its
  own and is held only by contact (also the side of a bolt behind a pre-tension section with a
  force), with its elements, contact selections and the remedies (weak Elastic support, a
  support, bonded contact, length adjustment). Code-Aster otherwise stops in the first step
  with `MECANONLINE9_4` (zero pivot); Mecway's penalty contact carries such parts. Found on
  Samples/BoltedJoint, where the friction contact itself still does not converge in
  Code-Aster even with the weak supports (without friction it runs). Docs: contact settings
  §3.11, error messages `MECANONLINE9_4`.
- **2D and axisymmetric static analyses (STAPPENPLAN S16a)**: Mecway's *Static 2D* (S20) and
  *Static Axisymmetric* (SA0) are now translated to Code-Aster `MECA_STATIQUE` with
  `C_PLAN` (plane stress, the material's *Shell/membrane* thickness), `D_PLAN` (with *plane
  strain*) or `AXIS` (Y = axis); `auto` chooses `lin_static_3d`. Loads: force on nodes and
  edges, pressure and traction on edges, gravity, centrifugal force; constraints: fixed,
  pinned, displacement along X/Y, symmetry with normal X/Y. Forces and reactions are for the
  whole thickness or 360 degrees, as in Mecway (Code-Aster computes per unit thickness and per
  radian). Results come back under Mecway's own names (`stresszz` = hoop stress in SA0), and
  Mecway recognises them. Displacements and reactions equal to Mecway's own solution
  (≤ 1e-11); Kt of a plate with a hole and Lamé within the tolerances of the 3D cases
  (verification PL-01 … PL-06). Beams in 2D and several thicknesses give an ERROR
  (KNOWN_BUGS 126). New document *2D: plane stress, plane strain, axisymmetric*.
- **2D and axisymmetric dynamic response (STAPPENPLAN S16b)**: Mecway's *Dynamic Response
  2D* (D20) and *Dynamic Response Axisymmetric* (DA0) go through `dyna_impl_3d` with the same
  2D translation; with schema NEWMARK, deformation PETIT and one solver step per Mecway step
  equal to Mecway's own solution (≤ 4e-8, verification PL-10 … PL-12: bar wave, damped ring,
  time-table force).
- **Dynamic Response with *Generate solution every n time steps* > 1 (D30, D20, DA0)**: the
  implicit solver step is now Mecway's *Time step size* (before: one step per output
  interval, n times Mecway's step; up to 100% off Mecway on a cantilever with n = 2, 86% with
  n = 5). Results are still written only at Mecway's output times. The setting
  `substeps_per_output` is now "Solver steps per Mecway time step" and multiplies on top of
  Mecway's step (default 1 = Mecway's step); models without *every n* (and D31) compute exactly
  as before. Mode superposition: the internal step is never larger than Mecway's step either.
  Verification MD-08a/b (Mecway 34 headless, n = 2 and 5: equal to Mecway within 3e-8);
  PL-11, PL-12 now without the workaround (KNOWN_BUGS 127 removed). **Behaviour change:**
  results of such models change (towards Mecway's) and the run takes up to n times as many
  solver steps.
- **Acoustic Resonance 2D (STAPPENPLAN S16d)**: Mecway's *Acoustic Resonance 2D* (A20) is now
  translated as the acoustic cavity modes (`acoustic_modes_3d`, chosen by `auto`) with
  `PHENOMENE='ACOUSTIQUE'`, `MODELISATION='PLAN'` on tri3/tri6/quad4/quad8 in the XY plane:
  hard walls, *Fluid pressure* = 0 on edges or nodes, *Impedance* on edges (complex modes,
  `PLAN_ABSO`). A thickness does not count, as in Mecway (measured: the model is per unit
  thickness). Frequencies, decay rates and the normalised pressure field equal to Mecway's own
  A20 solution for quads (≤ 1e-6), rectangle within 0.05% of f_mn = c/2·√((m/a)² + (n/b)²)
  (verification AK-10 … AK-15); with triangles the bridge is slightly higher (Code-Aster
  integrates their mass with fewer points, KNOWN_BUGS 130). No harmonic pressure field in 2D.
  Mecway has no axisymmetric acoustic type.

## V2026.5 – 28 October 2026

Result formulas computed by the bridge (issue #8), principal stresses and strains, acceleration
and heat flux as Mecway stores them, rubber on hex8 (issue #5), VTU export and MWHub Post, and
several options from Aubry's books (buckling with a constant load, hysteretic damping, line
search, automatic time stepping, mass and reaction check). Tested in Mecway 34 with Code-Aster
17.4; verification 442 test cases, 2382 checks (2376 OK, 6 known limitations, 0 unexpected).

- **Principal stresses, Tresca and principal strains** (new result fields `principal_stresses`
  and `principal_strains`, off by default): `principal1..3`, `tresca` and `lprincipalstrain1..3`
  of solid elements, computed as Mecway does (eigenvalues per element node, node value = mean of
  the element-node values; measured in Mecway 34). Mecway shows them as its own fields
  *principal stress*, *Tresca stress* and *principal strain*, and the formula symbols `s1`..`s3`,
  `tr`, `e1`..`e3` now work. Verification FX-02.
- **Acceleration under Mecway's names**: acceleration is now written as `accx/accy/accz/accmag`
  (harmonic: `accmag`, `accampx/y/z`), as Mecway 34 itself does. With the former names
  (`accelx`, ...) Mecway did not recognise the field "acceleration" (no vector and magnitude
  item, a formula with `a.x` made in Mecway had no data). Results loaded earlier keep the old
  names; own scripts that read `accelx` need the new names.
- **Result formulas computed by the bridge (GitHub issue #8)**: a formula from Mecway's
  *Solution > Formula* (e.g. `qf.z/3600/(12^2)`, `sqrt(u.x^2+u.y^2)`) is now computed from the
  Code-Aster results, per node and time step and in the units of the formula, and returned
  under its own name, as Mecway does in its own solve: after loading it is valid and shows a
  contour. Equal to Mecway's own solve within 1e-13 (verification FX-01 .. FX-03). Symbols of
  fields the bridge does not write (principal values `s1`, `e1`, `tr`, element coordinates,
  shell forces, material properties) give a WARNING with the workaround; a field a formula
  needs that is not chosen gives a WARNING too (user guide §4.2).
- **Heat flux per element node**: thermal results now also contain the heat flux of volume
  elements per element node (`FLUX_ELNO`, `heatfluxx/y/z/mag`), as Mecway itself stores it, so
  the contour per element is the same. Equal to Mecway's own solution within 1e-9 (also with a
  rotated mesh for shells outside Z = constant).
- **Rubber on hex8 (GitHub issue #5)**: with hyperelastic material on hex8 and *Hex8* = `3D`
  the bridge now warns about volumetric locking (measured ~3x too stiff on a bonded rubber
  block; `LINE_QUAD` was within ~6%) instead of giving the bending warning. *Hex8* = `3D_SI`
  cannot be used with hyperelastic material (Code-Aster `ELEMENTSSI_1`): that elset gets `3D`
  with a WARNING. Mecway's CCX *custom element type* (e.g. C3D8R) is no longer reported as an
  unsupported load (ERROR): it is a CalculiX setting, and the WARNING now says what
  Code-Aster uses instead.
- **Results... → In MWHub Post**: with AdvancedToolsHub found, the results window of the start screen
  has a button that opens the chosen run in MWHub Post (same job as the ParaView button).
- **Beam sidecar for MWHub Post**: with `vtu_export` or `med_export` a model with beams also gets
  `<model>_<run_id>_beams.json` (`mwhubpost-beams/1`): per beam elset the profile (Mecway's dimensions,
  the section as polygons in the local axes, A, Iy, Iz, J, shear areas) and per beam element its local
  axes. The VTU gets the section forces per element end as `EFGE_<N|VY|VZ|MT|MFY|MFZ>_1/_2` (with the
  result field *beam forces*). The format is described at the top of `Scripts/bridge_beams.py`.
- **VTU/PVD export** (setting `vtu_export`, off by default): next to the `.liml` results the job
  writes `<model>_<run_id>.pvd` with one `.vtu` per time step, with the same fields as Mecway gets
  (nodal fields as point data plus the vector `DEPL`, element fields as the cell average). Any
  ParaView reads it, also without a MED reader. With it comes `<model>_<run_id>_knopen.csv`: every
  nodal field over time for each named node selection (at most 100 nodes).
- **Failed elements as a field**: with element failure the results get the element field `failed`
  (0 intact, 1 failed from the failure time on), so Mecway can colour it; in the VTU it is called
  `BEZWEKEN`, with the failure time in `T_BEZWIJK`.
- **ParaView button opens MWHub Post** (AdvancedToolsHub) when the hub is found (setting
  `advancedtoolshub_dir`, default `%ADVANCEDTOOLSHUB_DIR%` or the folder next to the repository):
  the bridge writes `<model>_<run_id>_job.json` (`mwhubpost-job/1`) and calls the hub's launcher.
  Without the hub the button opens the `.rmed` as before.
- **ParaView button prefers ParaView 6.x**: with an empty `paraview_exe` the convergence window
  now starts the official ParaView 6.x (newest first), which reads a `.rmed` itself; Salome-Meca's
  ParaView (through `run_paraview.bat`) is the fallback, an older ParaView (5.10 cannot open a
  `.rmed`) the last resort. The `paraview_exe` setting still overrides the search.
- **Linear buckling with a constant plus a variable load** (Aubry, *Beginning with code_aster*,
  2019, §16.1–16.2): a line `#ASTER-CONSTANT name, ...` in the Custom model definition
  (selection names, or a load type such as `gravity`) keeps those loads constant: the bridge
  uses K + Kg(constant) as `MATR_RIGI` and Kg(variable) as `MATR_RIGI_GEOM`, so the buckling
  factor applies to the variable loads only. When the constant load alone is at or above
  critical (`INFO_MODE` Sturm count), the job stops with an ERROR. Without the line nothing
  changes. Verification BU-40.
- **Hysteretic (structural) damping in the harmonic response** (Aubry, *Beginning DYNAmics
  with code_aster*, 2023, §3.3.4 and §6): a loss factor η makes the stiffness K(1 + iη)
  (`AMOR_HYST` in `DEFI_MATERIAU` and for springs in `AFFE_CARA_ELEM`, `RIGI_MECA_HYST`),
  on the modal basis (complex generalised stiffness, `PROJ_MATR_BASE`) and direct
  (`PHYS`). Mecway has no loss factor: new setting *Loss factor eta* (`loss_factor`, all
  materials) and the line `#ASTER-HYST material = eta` per material. Verification HR-06a..d
  (mass on a spring: peak u_st/η exact; cantilever within 2.1e-4 of the exact
  receptance). Models without a loss factor are unchanged.
- **Optional line search** (`line_search`, nonlinear static and implicit dynamics; Aubry,
  *Beginning with code_aster*, 2019, §10.2): `RECH_LINEAIRE` (`CORDE`, `ITER_LINE_MAXI=3`) in
  `STAT_NON_LINE`/`DYNA_NON_LINE`. `auto` (default) only with cables (`CABLE`) without contact,
  `on` always (not with contact `CONTINUE`, which Code-Aster refuses: WARNING), `off` never.
  With `POU_D_T_GD` beams `on` converged poorly or not at all (WARNING). Cable cases LS-54b/c unchanged; SaggingCable with *Tension only* 7 instead of 9 Newton
  iterations with the same result.
- **Optional contact normal smoothing** (`contact_smoothing`, default off): `DEFI_CONTACT`
  `LISSAGE='OUI'` for curved contact surfaces meshed with few facets (cylinder, sphere); not
  for surfaces with sharp edges. Off: input unchanged.
- **Mecway's Automatic time stepping** (nonlinear static; U4.34.03; Aubry, *Beginning
  with code_aster*, 2019, §14.1): with `automatictimestepping="true"` in the `.liml`
  (internal solver or CCX time points) the bridge now uses `DEFI_LIST_INST
  METHODE='AUTO'` between Mecway's output times and the load-table kinks, with the
  existing step cutting as fallback, and archives only Mecway's output times. New
  setting `auto_time_stepping` (default on; off = fixed steps as before). Models without
  the flag are unchanged. The convergence window now also reads the step lines of
  `METHODE='AUTO'` (no "Niveau de découpe"). Verification NL-21a/b.
- **Penetration check for penalty contact**: with `contact_algo` = `PENALISATION` the
  bridge gives a WARNING after the run when the largest penetration (column `CONTACT
  PENETRATION` in study.mess) exceeds `contact_pene_maxi` (new setting, default 0.05) x
  the shortest edge of the slave faces, with the advice to raise the normal stiffness or
  use `STANDARD`. Results unchanged; 0 = off. (`DEFI_LIST_INST` `EVENEMENT=
  'INTERPENETRATION'` stops Code-Aster 17.4 with `JEVEUX_26` in the continuous
  formulation, so it is not used.) Verification NL-03p.
- **Mass and reaction check for static runs** (Aubry, *Beginning with code_aster*, 2019,
  §4.13–4.14): after a linear or nonlinear static run the log and the status box show the
  total mass and centre of gravity (`POST_ELEM MASS_INER`) and the sum of the reactions
  `REAC_NODA` per direction FX/FY/FZ (last stored step), for your own hand check. No
  automatic comparison with the loads. Both result routes. Verification LS-20a..e checks
  both numbers.
- **Warning for missing modal mass** (Aubry, *Beginning DYNAmics with code_aster*, 2023,
  §3.3/§11.3): a response on a modal basis (transient, harmonic `GENE`) gives a WARNING
  when the cumulative effective mass of the modes stays below 90% in a loaded direction
  (from the load resultant), with the advice to use more modes or physical coordinates.
  Results unchanged.
- **Docs:** nonlinear dynamics uses Code-Aster's default `AMOR_RAYL_RIGI='ELASTIQUE'`
  (Rayleigh damping with the elastic stiffness, catalogue `dyna_non_line.py`); documented,
  not changed.
- **Small cable pretension**: tension-only elements (`CABLE`) now get `N_INIT` =
  `cable_n_init_factor` x E x A (new setting on the page Elements, default 1e-6; INFO in
  the log). A straight cable without pretension was singular; now it solves (Samples/
  SaggingCable with *Tension only*: 3.06798 m, Mecway 3.0680 m). LS-54b/c unchanged.
- **MED export with shell and beam fields** (`med_export`): `IMPR_RESU` now passes
  `CARA_ELEM` and writes `SIGM_ELNO` (shell layers), the von Mises stress of the shell
  surfaces (`res_sup`/`res_moy`/`res_inf`), `SIPM_ELNO` and, with `beam_forces`, the
  section forces of beams.
- **`#ASTER-SECTIE`** (also `#ASTER-SECTION`): extra characteristics of a general beam
  section, written by MecwaySectionProps (section properties of a face in Mecway and a
  general section from them; its own repository, github.com/trednuK/MecwaySectionProps,
  after a few days in this one). The bridge passes `EY`, `EZ` (shear centre: bending-torsion coupling), `RY`,
  `RZ`, `RT` to `AFFE_CARA_ELEM` for every beam and `AY`, `AZ` to Timoshenko beams instead
  of the estimate; a line that no longer matches the material (A, IY, IZ, JX) is ignored
  with a WARNING. The bridge now reads every custom text field of a kind (Mecway keeps
  an imported custom model definition next to an existing one), not only the first.
- **Results after other errors in the step loop** (issue #5): when Code-Aster stops
  `STAT_NON_LINE`/`DYNA_NON_LINE` with another error than `MECANONLINE*` after some steps
  have converged (e.g. `DVP_2`, a floating point exception in a too distorted element),
  the bridge now loads the results up to the last converged time, as for a convergence
  failure. Mecway shows the error code, an explanation of `DVP_2` (smaller steps,
  quadratic elements, a smaller load) and the last time with results. An error before
  the first step still stops without results.
- **Buckling with trusses** (issue #6): linear buckling (and a buckling mode as
  imperfection) with trusses or cables now stops before Code-Aster with an ERROR that
  explains why (`BARRE`/`CABLE` have no geometric stiffness, `CALCUL_37` `RIGI_GEOM`) and
  advises beam elements. Docs: the midside condition of line3 trusses suppresses the
  isolated midside-node modes.

## V2026.4 – 22 October 2026

Quadratic trusses, hyperelastic materials, the elastic modulus from the plastic curve as
in Mecway, buttons in the convergence window, a work folder next to the model and better
flexible joints, most of them from GitHub issues (trednuK/MecwayAsterBridge). Tested in
Mecway 34 with Code-Aster 17.4; verification 431 test cases, 2318 checks (2312 OK, 6 known
limitations, 0 unexpected).

- **Line3 trusses** (issue #6): quadratic trusses and cables (line3, `truss="true"`) are
  now translated instead of stopping Code-Aster with `MODELE1_6`. Each element becomes two
  `BARRE`/`CABLE` cells; the midside node is tied to the end nodes. Verification MO-08
  (NAFEMS Challenge Problem 5: 451.1 / 1049.9 Hz, equal to the reference) and LS-54a (exact).
  An element set that cannot be translated as a whole now stops the bridge before
  Code-Aster with an error, instead of failing in Code-Aster.
- **Plastic curve** (issue #2): with a hardening curve in total strain, E is the slope of
  the first segment, as Mecway does, with a warning that gives both values. If the first
  slope still differs from E by more than 1 %, the bridge stops with an error before
  Code-Aster (before: a warning at 5 % and `MATERIAL1_5` in Code-Aster). Verification NL-04,
  NL-04b.
- **Hyperelastic materials** (issue #5): Mecway's *Neo Hooke* and *Mooney-Rivlin* become
  `ELAS_HYPER` (C10, C01, K = 2/D1) with `GREEN_LAGRANGE` in nonlinear static and dynamic
  analyses. Verification NL-50 to NL-53 (tension and compression, within 0.11 %, equal to
  Mecway with CCX). Hyperfoam is not possible: Code-Aster 17.4 on Windows has no MFront.
- **Convergence window** (issue #3): buttons *.comm*, *.mail*, *Folder* and *ParaView* for
  the run shown. New setting `paraview_exe` (empty = search automatically, Salome-Meca's
  ParaView with a MED reader first).
- **Work folder next to the model** (issue #4): new setting `work_dir_beside_model`; the
  files of a run go to `<model>_aster` next to the open `.liml`. The start screen shows the
  folder in use.
- **Mode shapes** now also get the displacement magnitude, as in Mecway 34.
- **Flexible joints**: a joint with U, V and W free is exact with `POU_D_T_GD` at any
  rotation and no longer gives a warning (NL-90, NL-90b). A joint with only some rotations
  free on `POU_D_T_GD` beams gives an error before the run. Joints on offset beams are
  translated in linear static and modal analyses, with the joint at the end of the rigid
  arm as in Mecway 34 (LS-52a/b/c equal to Mecway in deflection and rotations). Ideas and benchmarks from the fork by MishalTPC
  (github.com/mishal0488/MecwayAsterBridge).
- Docs: Mecway 33/34 compatibility table and version policy
  ([After an update](docs/en/After_an_update.md) §6, `AGENTS.md`).
- **Preparation errors** (reading the model, mesh, solver files) are shown directly in the
  status box instead of only "see the log".
- The ParaView button starts Salome-Meca's ParaView through its `run_paraview.bat` (sets
  the Salome environment; `paraview.exe` on its own stops with "Qt5Widgets.dll not
  found"), also when `paraview_exe` points to that `paraview.exe`.
- A contact whose face selections are empty (Mecway 34 replaces spaces in selection names
  by `_` when it opens an older model and then loses the reference) now stops before
  Code-Aster with a clear message instead of a non-converging run (nonlinear static and
  dynamics; bonded contact always); in linear and thermal analyses, where Mecway ignores
  unilateral contact, it is a warning. The example models
  `Voorbeeld_A` and `Voorbeeld_C` use selection names without spaces.
- Documented limitation: `POU_D_T_GD` under large rotations about a skew axis gives
  step-size dependent forces (STAPPENPLAN S21, KNOWN_BUGS 11).
- STAPPENPLAN: S14 (hyperelastic material) done, hyperfoam waiting for a Windows build with
  MFront; S21 (selective joint on `POU_D_T_GD` via a stub element) tried and documented.

## V2026.3 – 16 October 2026

Beams with large rotations (`POU_D_T_GD`) in nonlinear static, and Mecway 34's *Element
orientation* cards are read, so beams rotated with *Loads & Constraints > Element orientation*
get the right section axes. Both build on the fork by MishalTPC
(github.com/mishal0488/MecwayAsterBridge). Tested in Mecway 34; verification 415 test cases,
2267 checks (2260 OK, 7 known limitations, 0 unexpected).

- **Beams with large rotations** (`elem_beam` = `POU_D_T_GD` on the Elements page; default
  stays `POU_D_E`): in nonlinear static with large displacements, beams are computed as
  `POU_D_T_GD` (Timoshenko, `ELAS_POUTRE_GR`, `GROT_GDEP`). Elsewhere, including nonlinear
  static with `PETIT`/`PETIT_REAC`, they become `POU_D_T` with a warning. Supported: forces
  and moments (constant or as a time table), line pressure (also formulas in x, y, z, t),
  gravity, Thermal stress, configurations, line3, orientation cards, centrifugal force as a
  fixed load (trusses too) and section forces (`beam_forces`, one value per element). No beam
  stresses. `crit_stab`, `imperfection_amplitude` and element failure give an error
  beforehand. Offset arms, flexible joints and couplings stay linear relations (warning;
  couplings not verified). Idea, Code-Aster route and benchmarks from the fork by MishalTPC
  (github.com/mishal0488/MecwayAsterBridge). Verification NL-80 to NL-89 (14 cases, 55
  checks, ≤ 0.04 %; within 0.02 % of Mecway 34 with CCX).
- **Element orientation in Loads & Constraints** (`<orientation>` card on an element
  selection, also with formulas of the element centre) is now read instead of skipped, so
  beams no longer keep the default section orientation: V axis and angle for beams, U
  axis for gaps and for the shell result field `shell_forces`, exactly like the
  orientation in *Element properties*. Overlap with the element attributes or a second
  card (Mecway itself does not solve that) gives a warning; the card wins. In addition
  **every beam gets Mecway's V axis explicitly** as `ORIENTATION` `VECT_Y`, also without
  orientation, so the bridge no longer relies on Code-Aster's default. Both found in the
  fork by MishalTPC (github.com/mishal0488/MecwayAsterBridge). Verification MO-31,
  LS-79–82, BU-25, LS-31d: the same results as with the attributes and equal to Mecway 34;
  all existing beam cases unchanged.
- **Start screen**: the status box is higher when there is a message, uses a larger
  font, and can be made larger or smaller by dragging its upper edge. If the folder of the
  open model no longer exists (moved or deleted), Start and *Results...* say so and ask to
  save the model with *File > Save As...*; before, the status box only showed a bare
  Windows error. Start no longer rewrites `bridge_utils.py` when nothing was changed (the
  order of the result fields was saved again in another order on every Start). Starting
  the bridge again from *Tools* while its window is open or a run is going on now only
  says that the window is already open; before, Mecway opened a second window, so two
  runs on the same model were possible (KNOWN_BUGS 38).
- Fixes: the results export no longer reports the section-force source of the other beam
  formulation as missing; centrifugal force on trusses in models that use the formula route.
- STAPPENPLAN: S19 (beam element with warping, `POU_D_TG`, for flexural-torsional buckling)
  planned.
- README: acknowledgement of the fork by MishalTPC.

## V2026.2 – 16 October 2026

More of Mecway is translated (bonded contact for shells and in thermal analyses, element
offset, flexible joint, quadratic beams, formulas in x, y, z, node temperature and
temperature in time), more results come back into Mecway, the bridge waits for Code-Aster
by itself, and the configurations of a model can be chosen. Tested with Mecway 33 and 34 and
Code-Aster 17.4; verification 394 test cases, 2152 checks (2145 OK, 7 known limitations,
0 unexpected).

### Workflow
- **No more "click OK when Code-Aster has finished"**: the bridge now waits by itself. A
  modal status window shows the elapsed time, the current step (time, attempt, iteration or
  solver phase) and the messages so far, with a *Stop...* button that ends only this run's
  Code-Aster processes; when Code-Aster has finished the window closes and the results are
  loaded. The end is detected from an end marker with the exit code of `run_aster`
  (`Scripts/aster_launch.bat`), else from `DIAGNOSTIC JOB` in the `.mess`; a non-zero exit
  code, a closed Code-Aster window and a stop are reported in the status box and the
  convergence window. New setting *Waiting for Code-Aster* (`wait_for_aster`, General):
  `auto` (default) or `confirm` (the old OK dialog). The status window stays on top of the
  Code-Aster console (which opens without the focus). Test `tests/test_bridge_wait.py`;
  model for testing Stop: `TestFiles/Tools/StopTest_LongRun.liml` (~95 s).
- **Choose the configuration** (load case) on the start screen: new setting *Configuration*
  (`configuration`, General), `auto` = the previous rule; the results go into that
  configuration's solution. No more unjustified warning with a single configuration
  (was KNOWN_BUGS 68). Verification LS-20a–e.
- **Fix: results of a model with configurations** (e.g. load cases G, Q, ULS): Mecway 34 could
  not open the `.liml` after the bridge wrote the results into it ("Error opening file"). The
  model copy in `<solution configuration="X">` is now written as Mecway writes it: without the
  `<configuration>` definitions and `<suppressed configuration>` children, with
  `suppressed="true"` on the items suppressed in X. Test `tests/test_results_configuration.py`.
- **Version check** (warning only): the log shows the Mecway version (from the `.liml`) and the
  Code-Aster version (launcher path, then the `.mess`); an untested version gives a WARNING. New page
  *After an update of Mecway or Code-Aster* (`docs/en/After_an_update.md`).

### Mecway functionality now translated
- **Bonded (Tie) contact between shells** now works: a shell face or edge glued onto a
  shell face no longer stops with a singular matrix (`FACTOR_11`); the drilling rotation is
  left out of `LIAISON_MAIL`. Example `TestFiles/Voorbeelden/Voorbeeld_T.liml`, verification
  LS-07a–e, docs §3.10 of the contact settings. Also with a skewed or curved master and
  with a quadratic shell (tri6/quad8) as master: the bridge then writes the tie itself as
  `LIAISON_DDL` (skewed/curved: MUMPS `NPREC` −1 for that run, with a warning).
  Verification LS-07f–k (KNOWN_BUGS 90–92 solved).
- **Bonded contact in thermal analyses** (T30/T31) is now translated instead of silently
  dropped (KNOWN_BUGS 88): *Tie* / *Constraint equations* → `AFFE_CHAR_THER`
  `LIAISON_MAIL`, *Elastic* → thermal resistance `ECHANGE_PAROI` with Mecway's *Thermal
  conductance per unit area* (conforming solid faces; otherwise ideally bonded with a
  warning). Models with solids and shells together: ERROR (Code-Aster cannot couple
  them). Verification TH-04a–d.
- **Element offset** (Loads & Constraints) for shells and beams is now translated instead
  of skipped: linear shells (DKT/DST) with `EXCENTREMENT`, quadratic shells (COQUE_3D) and
  beams on their own nodes with rigid arms to the Mecway nodes. Results stay on the Mecway
  nodes (reactions include the arm). Verification LS-60–63 (incl. Mecway's CompositeBeam
  sample).
- **Quadratic beams (line3)** are now translated (were not modelled): each element is
  split at its midside node into two SEG2 beam cells; results on all three nodes.
  **Flexible joint on beam** is translated: an own node per beam end, coupled with
  `LIAISON_DDL` in Mecway's local axes. Verification LS-50 and LS-51 (equal to
  Mecway); limits KNOWN_BUGS 106–107.
- **Formulas in x, y, z for mechanical loads** (also combined with t) are now translated
  instead of skipped (KNOWN_BUGS 45): pressure, traction, force, line pressure and
  prescribed displacement/rotation become a `FORMULE` of X, Y, Z (INST) in
  `AFFE_CHAR_MECA_F`, e.g. a hydrostatic-like pressure `3*y^2`. Pressure and traction match
  Mecway 34 exactly; force, line pressure and displacement with x, y, z are not applied by
  Mecway 34 itself (warning). Verification LS-40–44, NL-40; limits KNOWN_BUGS 104.
- **Node temperature** (`temperature3`, also after *Transfer temperatures from solution*) now
  gives thermal strain in static, nonlinear static, modal and buckling analyses, like
  *Temperature*; nodes the bridge adds (`LINE_QUAD`, `COQUE_3D` centre node) get the
  interpolated temperature. Verification LS-08a–d. KNOWN_BUGS 89 fixed; 95 recorded
  (Mecway expands shells less).
- **Temperature in time** (`temperature2` with a time table or a formula in t) now gives
  thermal strain in nonlinear static (L30) and nonlinear dynamic response (D31): an
  `EVOL_THER` from the reference temperature, following the table like Mecway (with CCX).
  A constant temperature acts from the first step (Quasi-static, D31) or ramps up (L30
  without Quasi-static, up to t = 1 s like Mecway). Temperatures now give thermal stress in `DYNA_NON_LINE`
  (KNOWN_BUGS 94 fixed); D30 ignores them like Mecway. Verification NL-70..75, DY-70..73.
- **Mecway's time step size** in Nonlinear static is now used for the output times (load
  table kinks in between become extra steps); `substeps_per_interval` only applies without a
  step size (was KNOWN_BUGS 44). Verification NL-20.
- **Explicit dynamics**: a constraint equation with a constant ≠ 0 is now converted to an
  imposed acceleration (with a warning; was KNOWN_BUGS 41). Verification DY-20a–c.

### More results in Mecway
- New result fields: **contact pressure and contact status**, **beam section forces and
  moments** (N, V, T, M in Mecway's local axes), **shell stresses** (top/mid/bottom, off by
  default) and **forces and moments per unit length**, **total strain** (off by default) and
  the **factor of safety** of Mecway's *failure criterion*. `shell_forces` is on by default
  and gives a warning with its effect (about 2.5× larger results in the `.liml`).
  Verification LS-30–32, NL-30–32, MO-30, DY-30.

### Fixes
- **Several heat sources with a formula or time table** (*Internal heat generation*, heat
  flux on shell faces, `#ASTER-LASBRON`) now each give their own heat: Code-Aster 17.4
  computed two such loads both with the function of the first. All function sources are
  now in one load, overlapping sources summed per part of the mesh; a weld source next to
  a formula/table source no longer gives a warning (KNOWN_BUGS 70 solved). Verification
  TH-40–42.
- **`FACTOR_57` without a mechanism** (slender volume models in bending, MUMPS error estimate
  just above `RESI_RELA` 1e-6): the setting *Solver accuracy (RESI_RELA)* (`lin_solver_resi`,
  default 1e-6 as Code-Aster) is now also on the pages Modal (static step for the prestress,
  also cyclic), Buckling (static step) and Nonlinear static (static step of the imperfection).
  The error message reads the computed error from `study.mess`: below 1e-3 it names the page
  and the value to enter, above it the mechanism advice. Verification BU-37 (hex20 L frame).
  Was KNOWN_BUGS 114.
- **Cyclic symmetry about X or Y**: *Results...* reloads the results again (was KNOWN_BUGS 78).
- Final review fixes: two partly offset shell groups, offset and flexible joint on
  the same beam, element results of quad8 shells with offset, beam ends with a joint and
  line3 beams (they were silently missing), clear warnings in the thermal → mechanical
  chain and for offset combined with bonded contact.

### Verification, warnings and documentation
- **Beam orientation** verified for statics, natural frequencies and buckling against
  analytical values and Mecway 34 (MO-20–29, LS-70–78, BU-20–24): identical to Mecway.
- **Buckling of beams** investigated (BU-30–37): pure torsional buckling and frames with
  bending moments are right in the bridge (solid models and Code-Aster test ssll105 agree);
  Mecway's own beam element misses those terms. T, C and L sections cannot buckle
  flexural-torsionally with the beam elements (warning, KNOWN_BUGS 115; planned as STAPPENPLAN S19).
- Limits of the remaining open points are in the documentation and, where they can be
  detected, as warnings (curved line3 beams, joint on an element selection, offset shells
  with large rotations).
- **New overview** of which Mecway functionality the bridge does and does not translate
  (`docs/en/Mecway_features.md`, Dutch `docs/Mecway_functionaliteit.md`), also on the
  Documentation page of the start screen.
- Example `TestFiles/TieContact_Plates.liml` (bonded plates, with Code-Aster results).
- README: Mecway 34, acknowledgements.
- **Developer text in English**: code comments, docstrings, comments in the `.comm`
  templates (and the generated `study.comm`), INFO/SUCCESS log lines, `AGENTS.md`,
  `KNOWN_BUGS.md` and `STAPPENPLAN.md`. The user interface, messages, WARNING/ERROR lines,
  the convergence window and the user documentation (`docs/` Dutch, `docs/en/` English)
  stay bilingual.

## V2026.1 – first public release

First public version of the MecwayAsterBridge: a Mecway 33 model (`.liml`) is solved with
Code-Aster 17.4 for Windows and the results come back into Mecway. Standalone: only the
Python of Mecway and of Code-Aster, no `pip` packages.

- **Start screen** in English and Dutch, with settings per analysis, tooltips, a
  convergence and messages window, and the documentation built in.
- **Analyses**: linear and nonlinear static (contact, plasticity, large displacements,
  element failure), implicit and explicit nonlinear dynamics, mode superposition and
  harmonic response, thermal (steady state and transient) and thermo-mechanical, modal
  (also prestressed), linear and nonlinear buckling (CRIT_STAB, imperfection).
- **Acoustics**: cavity modes and harmonic pressure field (sources, absorbing boundaries,
  microphones); vibroacoustics, coupled modes and harmonic response.
- **Welding and metallurgy**: moving heat source along a weld bead, residual stress and
  distortion, filler material that is born, phases and hardness.
- **Fracture mechanics**: K and G along a meshed crack, and XFEM cracks without a mesh.
- **Fatigue**: damage and life per node (Wöhler curve, rainflow, Miner, critical-plane
  criteria, Manson-Coffin).
- **Cyclic symmetry** for modal analysis of a sector.
- **Response spectrum** (earthquake, shock) on a frequency model.
- **Error estimator** per element (linear static) and **adaptive refinement** of the
  mesh in Mecway.
- **`#ASTER` lines** in Mecway's *Custom model definition* for Code-Aster input that
  Mecway has no field for.
- **Verification set**: 272 test cases with 1629 checks against analytical solutions
  and benchmarks, plus 19 official Code-Aster validation tests
  ([`docs/en/Verification.md`](docs/en/Verification.md)).
