# Bolt pretension (Pre-tension section)

*Nederlandse versie: [Boutvoorspanning.md](../Boutvoorspanning.md)*

Mecway's *Pre-tension section* (manual v34 §9.11) pretensions a bolt or another
prismatic part: with a **force** (tension positive) or a **length adjustment** (the
free length changes, positive = shortening). The bridge translates the variant
with a prism of solid elements (in Mecway the CCX variant) in **Linear static**
(S30, `lin_static_3d`), **Nonlinear static** (L30, `nonlin_static_3d`) and
**Dynamic response** (D30/D31, implicit `dyna_impl_3d`), and the variant with one
**spring element** (in Mecway the internal-solver variant) in **Linear static**.

## 1. Usage

1. Model the bolt (or the part to be pretensioned) with solid elements: hex, wedge,
   tet or pyramid, linear or quadratic. The part where the section comes must be
   prismatic (the same cross-section along the axis).
2. *Loads and constraints* > *Pre-tension section*: select at least two **exterior
   faces of the shank at different angles**, e.g. the whole cylindrical surface
   of a piece of the shank. These faces define the axis (perpendicular to their
   normals) and the axial extent; the section comes in the **middle** of that
   extent. Select faces on both sides of the place where you want the section.
3. Choose *Force* (e.g. `10 kN`) or *Length adjustment* (e.g. `0.01 mm`). Both may
   be constant, a table in time or a formula in t.
4. Mecway itself only computes the section with CCX; for the bridge the solver
   choice in Mecway does not matter. Choose the analysis Static 3D, Nonlinear
   static 3D or (Nonlinear) Dynamic Response 3D and start the bridge as usual.
5. Spring element instead of a prism (Mecway's internal-solver variant): select the
   face of **one** spring element (line element with a *Spring* material) and give a
   *Length adjustment*. Mecway always uses the length adjustment for a spring, also
   when *Force* is chosen (the force is then ignored); the bridge does the same.
   Only in Static 3D.

There are no settings. The bridge reports the section in the log: axis, axial
extent, place of the section, section area with the nominal stress F/A, the
number of elements on both sides and the reference node.

## 2. Force or length adjustment

| Mecway | What stays fixed | Under an extra external load |
|---|---|---|
| Force | the force in the section, during the whole analysis | the bolt force stays F (the bolt lengthens); there is no "locking" after tightening |
| Length adjustment | the shortening | the bolt force changes with the stiffnesses (joint diagram: + P kb/(kb + kc)) |

![Bolt force against external load](../img/pretension_force_vs_adjustment.svg)

1. Force: the bolt force Fb stays equal to the specified force, whatever the external load P.
2. Length adjustment: the bolt force rises with P at the slope kb/(kb + kc) (kb bolt, kc clamped parts), as long as the parts stay clamped.
3. The pretension Fp at P = 0 (both modes; for the length adjustment Fp = kb kc/(kb + kc) × shortening).

That is how Mecway does it (CCX: the force stays a `*CLOAD` on the pre-tension node,
the adjustment is a `*BOUNDARY`) and how the bridge does it (verification PT-03 and
PT-04: equal to Mecway within 0.01%). Do you want a tightened and then locked bolt
under a later load? Use the length adjustment with the shortening that gives the
desired pretension (PT-03: Fp = kb kc/(kb + kc) × shortening; Mecway has no
two-step "force, then lock" either).

Time course: like an ordinary force or prescribed displacement. In Nonlinear
static with Mecway's *Quasi-static* time steps a constant value acts in full from
the first step (as in Mecway, BoltedJoint); without time steps the loads ramp up.

**Dynamic response** (D30/D31): Mecway (CCX) computes one dynamic step with the
force or the length adjustment on the pre-tension node, constant values as a step
from t = 0 (`AMPLITUDE=STEP`); there is no static preload step first. The bridge
does the same in `dyna_impl_3d`. A constant pretension therefore starts a vibration
about the static state; use a table or formula in t that rises slowly (compared with
the lowest natural period) if you want the bolt to be tightened quasi-statically.

![Displacement against time with a pretension in dynamics](../img/pretension_dynamic.svg)

1. Constant value: acts as a step from t = 0 and the structure vibrates (undamped
   between 0 and twice the static value).
2. The static value u_s: the displacement that Static 3D gives with the same
   pretension.
3. Twice the static value: the first peak of the step response.
4. Value as a slowly rising table or formula: follows the static value with a
   small vibration.

## 3. How the bridge translates

![Prism, section and node pair](../img/pretension_cut.svg)

1. The selected exterior faces of the shank (at least two at different angles).
2. The axis n, perpendicular to the normals of those faces.
3. The axial extent of the selected faces; the prism is the solid elements within it.
4. The section in the middle of the extent.
5. The side below (along n): its elements get copies of the section nodes.
6. The side above: keeps the Mecway nodes; Mecway shows these values.
7. A Mecway node on the section (side above).
8. Its copy (side below), at the same place; the two differ by the shortening δ along n and are equal across n.
9. The reference node: its DX is δ; it carries the force F or the prescribed δ.

- **Prism** (as Mecway, manual §9.11): the axis is the median of the cross products
  of the normals of every pair of selected faces (at most 1000 faces), the axial
  extent that of the selected faces; the prism holds all solid elements within that
  extent that are connected to the selected faces or to each other.
- **Section**: every prism element lies below or above the middle of the extent
  (its centroid along the axis). The nodes that both sides share are the section;
  in a structured mesh that is a layer of element faces, in a tet mesh a zig-zag
  surface over faces, edges and corner nodes (PT-05). Mecway inserts a thin
  layer of elements there for CCX; the bridge does not need that.
- **Cut**: the elements below (along the axis) get a copy of the section nodes
  (new nodes after the Mecway nodes). Per node pair three `LIAISON_DDL`:
  u(above) − u(below) + δ·n = 0, with n the axis and δ the shortening = `DX` of a
  **reference node** (POI1 with `DIS_T` stiffness 0, group `BRPRET`; `DY` = `DZ` = 0).
  The tangential components stay equal, the normal ones differ by δ; that is CCX's
  own formulation (`pretensionsections.f`) and the tightening of the official
  test case ssnv106a.
- **Load**: force → `FORCE_NODALE FX` = F on the reference node (the work conjugate
  of δ is the axial force, tension positive); length adjustment → `DDL_IMPO DX` = δ.
  The Mecway load points at the node group `BRPT<k>` of that node. In dynamics the
  same load follows the time course like an ordinary force or prescribed
  displacement; the reference node has no mass (it only carries the relations),
  which is why the explicit scheme is not supported.
- **Spring element variant**: the spring force is k (elongation + δ), so a spring
  shortened by δ is the same spring with two nodal forces k δ that pull its end
  nodes towards each other along its axis: `FORCE_NODALE` on node groups
  `BRPS<k>A` and `BRPS<k>B`. Exact in linear static (PT-09, PT-10: equal to
  Mecway's internal solver).

## 4. Results in Mecway

- The nodes on the section show the values of the side **above** (the higher side
  along the axis, the largest axis component positive). The jump δ across the section
  is not visible in Mecway (the copies are not Mecway nodes); in Mecway itself
  the nodes of the inserted layer are not visible either.
- The bolt force in force mode is exactly F. Check it with the nominal stress in the
  log, or with the stress in the shank (in a coarse mesh the nodal stress at the
  junction with the head deviates; take a node halfway along the shank).

## 5. Test models

PT-01 .. PT-05 in [`Verification.md`](Verification.md): bar with force and with
length adjustment (hand calculation exact, Mecway 34 −0.004%), bolt with sleeve
between rigid plates (joint diagram with length adjustment, and with force under an
increasing external load in Nonlinear static), and a bar in tet4 with a zig-zag
section. PT-06 .. PT-08: the joint with a heavy top plate in Dynamic response
(force and length adjustment as a step, force as a ramp in D30; period and peak
equal to the mass-spring hand calculation within 0.6% and to Mecway 34 with CCX
within 0.06%). PT-09, PT-10: the spring element variant (two springs in series,
along X and inclined; exact, equal to Mecway's internal solver).

## 6. Messages and solutions

| Message | Cause | Solution |
|---|---|---|
| ERROR: Pre-tension section on '...': only in linear and nonlinear static analyses and implicit dynamics | explicit dynamics (`dyna_expl_3d`), dynamics on a modal basis, modal, buckling, ... | use Static, Nonlinear static or `dyna_impl_3d` (KNOWN_BUGS 124) |
| ERROR: ... only faces of solid elements (prism, CCX variant) or the face of a single spring element | the selection holds shell/beam faces, or solid and spring faces together | select faces of solid elements only, or the face of one spring |
| ERROR: ... the spring element variant acts on the face of exactly one spring | faces of several springs in one selection | make one pre-tension section per spring |
| ERROR: ... the spring element variant only in linear static | the spring variant in another analysis (Frequency, Buckling, nonlinear, dynamics) | in Frequency and Buckling Mecway also gives the tensioned spring its geometric stiffness, Code-Aster's DIS_T does not; replace the spring by a short bar of solid elements (prism variant) (KNOWN_BUGS 124) |
| WARNING: Pre-tension section on spring '...': for a spring Mecway only uses the length adjustment | *Force* chosen on a spring | give the shortening as *Length adjustment* (the force does nothing, as in Mecway) |
| ERROR: ... no axis: select at least two faces at different angles | all selected faces parallel (e.g. only a flat side of a square bar) | also select a face at another angle (e.g. the adjacent side) |
| ERROR: ... no section through the prism found | one element along the axis, or the faces do not span the place of the section | select faces of at least two element layers, on both sides of the desired section |
| ERROR: ... the section touches elements outside the prism | elements around the section that reach beyond the axial extent (e.g. a nut or plate meshed together with the bolt) | select faces over a piece of the shank that only holds shank elements, or mesh the bolt as its own part (contact or bonded contact to the plates) |
| ERROR: ... the section passes through nodes of another pre-tension section | two sections at the same place | move one of them |
| WARNING: A part of ... element(s) ... is held in place only by contact (...) and by the force of a pre-tension section | the side of the bolt behind the section is only held by contact (nut) and the force; Code-Aster stops in step 1 with `MECANONLINE9_4` | a weak *Elastic support* on a face of that side, or *Length adjustment* ([Settings §3.11](Settings_contact_and_nonlinear.md#311-parts-held-only-by-contact)) |
| WARNING: Choice LINE_QUAD ... not applied: ... pre-tension section | hex8 with `elem_hex8` = LINE_QUAD | the mid-side nodes made by Code-Aster would stay apart at the section; use hex20 in Mecway |

## 7. What is not possible

See also KNOWN_BUGS 124.

- Explicit dynamics (`dyna_expl_3d`), dynamics on a modal basis and the other analyses
  (modal, buckling, ...): ERROR. Mecway allows the prism variant only in static and
  dynamic response.
- The spring element variant outside Static 3D: Mecway also allows Frequency and
  Buckling, but there it gives the tensioned spring a geometric stiffness (a cantilever
  with a pretensioned spring from its base to its tip: buckling factor 6.99 in Mecway,
  the load acting as if directed through the base; 1.75 with nodal forces), which the
  discrete element of Code-Aster does not have.
- Mecway's own solve of a spring model: *Fixed* on a node selection did not hold nodes
  that only have springs in Mecway 34 (singular model); use *Displacement* in X, Y
  and Z there. The bridge fixes them either way.
- A follower direction: the axis stays fixed at large rotations (also in Mecway).
- Loads, supports and contact on faces that touch the section: on the side
  below they act on the copy (load, contact) or on the Mecway node (support only);
  the difference is at most δ, as for Mecway's inserted layer.
- Samples/BoltedJoint itself does not run with Code-Aster: plate B is only held by
  contact, and with the force the upper part of the bolt is only held by the nut contact
  and the pretension force. The bridge reports both parts before the run (WARNING "held
  in place only by contact"); a weak *Elastic support* on each removes the zero pivots,
  but the friction contact itself still does not converge in Code-Aster; without friction
  it runs (KNOWN_BUGS 43,
  [Settings_contact_and_nonlinear.md §3.11](Settings_contact_and_nonlinear.md#311-parts-held-only-by-contact)).

## 8. Sources

- Mecway manual v34 §9.11 (prism, axis, extent, thin layer, limitations); XML and
  CCX deck of Samples/BoltedJoint.liml and test models read during headless Mecway 34
  solves (28 Oct 2026): `force="true"` = force, `adjustment="true"` = length
  adjustment, `*CLOAD` resp. `*BOUNDARY` on the pre-tension node; in D30/D31 one
  `*DYNAMIC` step with `AMPLITUDE=STEP` (no preload step), a formula in t as an
  `*AMPLITUDE`. Spring element variant: Mecway 34 internal solver, headless (the
  faceid of the line element does not matter; the length adjustment is used
  whatever the mode).
- CalculiX 2.23 source shipped with Mecway, `pretensionsections.f`: per node pair
  two tangential MPCs and one normal MPC with the DOF of the reference node.
- Code-Aster 17.4: `LIAISON_DDL` (catalogue `affe_char_meca.py`, U4.44.01); test
  case ssnv106a (tightening as a relative displacement between doubled nodes).
