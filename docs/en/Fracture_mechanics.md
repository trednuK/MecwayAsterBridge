# Fracture mechanics: K and G along a meshed crack or an XFEM crack

*Nederlandse versie: [Breukmechanica.md](../Breukmechanica.md)*

For a linear static analysis (Mecway *Static*, S30; bridge analysis `lin_static_3d`)
the bridge uses Code-Aster to compute the **stress intensity factors** K_I, K_II,
K_III and the **energy release rate** G along the front of a crack that you made in
the mesh. Mecway itself has no fracture mechanics (Mecway Ltd., 2026); the bridge
recognises the crack by three selections with a fixed name.

| What | Where you see it |
|---|---|
| K_I, K_II, K_III and G per node along the front | table `<model>_<run-id>_scheur.csv` in the work folder |
| range of K_I and G along the front, and messages | log and status box after the run |
| displacements, stresses (the usual results) | Mecway, as always |

K and G are **not a field in Mecway** (KNOWN_BUGS 63): the values belong to the front,
not to a node or element of the model. General working of the bridge:
[`UserGuide.md`](UserGuide.md).

A crack that is **not in the mesh** (running through the elements, with an
`#ASTER-XFEM` line): **XFEM**, §7. §1 to §6 are about the meshed crack.

## 1. Step-by-step workflow

### 1.1 In Mecway: the model

1. **Analysis type** *Static* (S30). For other analyses the bridge gives a WARNING and
   computes no K and G (§4).
2. **Geometry with the crack plane as an element boundary.** The crack is a plane in
   the mesh: element faces lie on the crack plane, the front is a line of element
   edges. A crack running through elements: XFEM (§7).
3. **Solid elements, preferably hex20 (or tet10/wedge15).** With hex20, K from
   `CALC_G` is accurate even on a coarse mesh (§3). hex8 also works but is less
   accurate; `LINE_QUAD` (Elements page) makes hex8 quadratic and then gives the same
   as hex20.
4. **Fine mesh around the front.** Element size at the front: about a/10 to a/20
   (a = crack length or depth) is enough for K within 1 % with hex20 (§3). Refine
   mainly perpendicular to the front; along the front at least 4 elements (5 nodes,
   §2.3).
5. **Material:** isotropic elastic (`E`, `ν`), preferably one material around the
   front (a crack on an interface between materials is NOT verified).
6. **Constraints and loads** as always. Do not put a constraint on the lips (that
   closes the crack).

### 1.2 Opening the crack

A crack has two lips that lie at the same place but are **not connected** to each
other: the lips have double nodes, the front and the region beyond it (the ligament)
have shared nodes. This is how to do it in Mecway (Mecway Ltd., 2026, §4.2.10 and
§4.2.11):

1. Select all elements on **one side** of the crack plane (e.g. all elements above
   the plane).
2. *Mesh tools > Disconnect elements*. Now the whole plane is disconnected, the
   ligament too (check: *View > Exploded view* or *View > Open cracks*).
3. Select the **nodes of the ligament and of the front** (the nodes in the plane that
   do *not* belong to the crack). A box selection takes both double nodes at the same
   place.
4. *Mesh tools > Merge nearby nodes* with a small distance (smaller than the smallest
   element). With a node selection Mecway merges only those nodes; the lips stay
   apart.

Other ways: (a) build the two halves as separate parts and merge only the ligament and
the front (steps 3-4); (b) **half model with symmetry**: model only the half above the
crack plane, put a *Symmetry* constraint on the ligament and leave the lip free; then
there is only one lip and nothing needs opening (§1.3).

If the crack is not open (the lips share nodes outside the front), the bridge stops
with an ERROR (§5).

### 1.3 Naming the selections

Create these selections with *Named selection* (names in upper or lower case; the
Dutch names work too):

| Selection | Kind | What | Dutch |
|---|---|---|---|
| `CRACK_FRONT` | node selection | all nodes along the front (corner and mid-side nodes; if a mid-side node is missing the bridge takes it from the element) | `SCHEUR_FRONT` |
| `CRACK_LIP_UPPER` | face selection | the element faces of one lip | `SCHEUR_LIP_BOVEN` |
| `CRACK_LIP_LOWER` | face selection | the element faces of the other lip; **leave out** for a half model with symmetry | `SCHEUR_LIP_ONDER` |

- Which lip is "upper" does not matter: swapping gave exactly the same K (measured).
- **Several cracks:** give each crack its own suffix after all three names, e.g.
  `CRACK_FRONT_A`, `CRACK_LIP_UPPER_A`, `CRACK_LIP_LOWER_A` and `CRACK_FRONT_B`, ...
  The table then has a column `crack` with `_A`, `_B`.
- A front is one line: open (e.g. through the thickness of a plate, or a quarter of a
  circle in a quarter model) or closed (a circle around a penny-shaped crack).

### 1.4 In the bridge main window

Page **Static**, heading *Fracture mechanics (CRACK_ selections)*. The settings only do
something when the model has `CRACK_` selections.

| Setting (label) | Key | Default | When to change |
|---|---|---|---|
| Crack: R_INF [m] (0 = automatic) | `fracture_r_inf` | 0 | rarely. Code-Aster chooses 2 x the element size at the front. If G or K depend on the choice (compare two values), or the mesh at the front is irregular: choose R_INF = 2 to 3 elements |
| Crack: R_SUP [m] (0 = automatic) | `fracture_r_sup` | 0 | Code-Aster chooses 4 x the element size. Choose smaller if the ring would then reach another crack, a constrained or loaded boundary or the model boundary; R_SUP > R_INF |
| Crack: smoothing along the front | `fracture_smoothing` | `LINEAIRE` | `LEGENDRE` with degree 0 for a short front with fewer than 5 nodes (the bridge then warns) or if you want one mean value |
| Crack: Legendre degree (0 .. 7) | `fracture_legendre_degree` | 5 | `LEGENDRE` only; below the number of nodes along the front |

R_INF and R_SUP are the inner and outer radius of the ring around the front over
which `CALC_G` integrates (theta method). For one model it also works with
`#ASTER-OPTIE` in Mecway's custom input, e.g. `#ASTER-OPTIE fracture_r_inf = 0.002`
and `#ASTER-OPTIE fracture_r_sup = 0.004`
([`ASTER_lines_examples.md`](ASTER_lines_examples.md) example 16).

### 1.5 Running and results

Click *Start*. Afterwards the log and the status box show for example (verification
BR-01, in English):

```
Fracture mechanics, crack 1: 5 points along the front. K_I 46.97 MPa.m^0.5 (CALC_G),
45.38 MPa.m^0.5 (POST_K1_K2_K3); G 9539 J/m2. K_II up to 2.42e-13, K_III up to
6.78e-14 MPa.m^0.5. Table: BR-01_verif_scheur.csv
```

If the value varies along the front, a range is shown (`1.568 .. 1.611`). The table
`<model>_<run-id>_scheur.csv` (commas, point as decimal separator; opens in a
spreadsheet) has per node along the front, in SI units:

| Column | Meaning | Unit |
|---|---|---|
| `crack` | suffix of the crack (`1` without a suffix) | - |
| `point`, `node` | number along the front and the number of the Mecway node | - |
| `x`, `y`, `z`, `s` | position and arc length along the front | m |
| `G` | energy release rate from `CALC_G` (theta method) | J/m² (= N/m) |
| `K1`, `K2`, `K3` | K_I, K_II, K_III from `CALC_G` (interaction integral) | Pa·√m |
| `G_IRWIN` | G from K1..K3 of `CALC_G`: (K1² + K2²)(1 − ν²)/E + K3²(1 + ν)/E | J/m² |
| `K1_POST_K`, `K2_POST_K`, `K3_POST_K`, `G_POST_K` | the same quantities from `POST_K1_K2_K3` (check; with quadratic elements only at the corner nodes, the mid-side nodes are empty) | Pa·√m, J/m² |

The tables are also in the `.mess` (`IMPR_TABLE`).

### 1.6 Interpretation

- **Which value:** K1/K2/K3 and G from `CALC_G` are the result; they are accurate
  even on a coarse mesh (§3). `POST_K1_K2_K3` is an independent check that comes out
  a few percent low without quarter-point elements. If they differ by more than 5 %
  inside the front, the bridge warns (mesh too coarse, or R_INF/R_SUP).
- **G and K:** in plane strain (the interior of a thick plate) G = K_I²/E' with
  E' = E/(1 − ν²); in plane stress (thin plate) E' = E. `G` and `G_IRWIN` should be
  equal in plane strain (verification: 0.2 %).
- **Checking against the fracture toughness:** the crack grows (brittle, linear
  elastic) when K_I ≥ K_IC. K_IC is a plane-strain material property (e.g.
  structural steel ~ 50–200 MPa·√m, aluminium ~ 20–40 MPa·√m; Anderson, 2005). Use
  K_IC for thick parts; a thin plate (plane stress) has a higher apparent toughness
  K_C. With plasticity around the front (a large plastic zone compared with the
  dimensions) linear elastic fracture mechanics no longer applies.
- **Mixed mode:** K_II (in-plane shear, perpendicular to the front) and K_III (shear
  along the front) are ~0 under a symmetric tensile load. You choose a criterion for
  mixed loading yourself (e.g. G ≥ G_C with G = the sum).
- **Edge effect at a free surface:** where the front meets a free surface the stress
  state is no longer plane strain and the singularity is no longer 1/√r. In the middle
  of a thick plate K_I equals the 2D plane-strain value (BR-03: +0.7 %); towards the
  surface K_I changes (BR-03: up to +6 %), and the value at the surface node itself is
  not a reliable K. Judge K in the interior of the front.
- **K_I < 0:** the lips overlap (compression on the crack). The bridge has no contact
  on the lips, so the value is physically meaningless (WARNING); the crack is then
  closed and does not grow in mode I.

## 2. How the bridge translates

### 2.1 Code-Aster commands

1. Mesh (`bridge_mesh.write_mesh`): the edges of the solid elements whose two end
   nodes are in `CRACK_FRONT` become SEG2/SEG3 cells in group `BRSCHEUR<n>`
   (`DEFI_FOND_FISS` only knows the front as cells or as ordered nodes; Mecway has no
   edges). The bridge checks that they form one line and that the lips share no nodes
   outside the front.
2. After `MECA_STATIQUE` and the export of the usual results (so an error in the
   fracture mechanics does not keep the results from Mecway):

```
fieldmat_fiss = AFFE_MATERIAU(... TOUT='OUI' with the material at the front, then the
                              material per elset ...)
res_fiss = CREA_RESU(OPERATION='AFFE', TYPE_RESU='EVOL_ELAS', AFFE=_F(NOM_CHAM='DEPL',
                     CHAM_GD=<displacement of res>, CHAM_MATER=fieldmat_fiss, ...),
                     EXCIT=<the loads of MECA_STATIQUE>)
res_fiss = CALC_CHAMP(reuse=res_fiss, RESULTAT=res_fiss, CONTRAINTE=('SIEF_ELGA',))
fond_1 = DEFI_FOND_FISS(MAILLAGE=mesh, FOND_FISS=_F(GROUP_MA='BRSCHEUR1'),
                        SYME='NON', LEVRE_SUP=_F(GROUP_MA='CRACK_LIP_UPPER'),
                        LEVRE_INF=_F(GROUP_MA='CRACK_LIP_LOWER'), CONFIG_INIT='COLLEE')
scheur_g_1 = CALC_G(RESULTAT=res_fiss, OPTION=('G', 'K'), THETA=_F(FISSURE=fond_1))
scheur_pk_1 = POST_K1_K2_K3(RESULTAT=res_fiss, FOND_FISS=fond_1)
```

- Without `CRACK_LIP_LOWER`: `SYME='OUI'` (half model; Code-Aster computes K and G for
  the whole crack, BR-02 equal to BR-01).
- A closed front: `TYPE_FOND='FERME'`.
- A front that is a circle with the lip inside it (penny-shaped crack):
  `FORM_FISS='CERCLE', RAYON=<radius>` (curvature correction of the interaction
  integral; forma07a without it: K_I +5.6 %, with it: +0.1 %).
- `R_INF`/`R_SUP` and `DISCRETISATION`/`DEGRE` from the settings (§1.4).

Why a material field and result of their own: `CALC_G` also works on the boundary
cells (the lips, loaded faces) in the ring and needs a material there (`<EXCEPTION>
CALCUL_20`, "Le matériau est nécessaire sur la maille", option `CALC_K_G`, seen during
the build), while the bridge assigns the material per elset. Option `G` reads
`SIEF_ELGA` (`<EXCEPTION> RUPTURE0_94` without it).

### 2.2 Automatic R_INF and R_SUP

Without `R_INF`/`R_SUP` Code-Aster chooses them itself and reports it in the `.mess`
("Le paramètre R_INF automatiquement choisi vaut ..."). Measured: R_INF = 2 h and
R_SUP = 4 h, with h the element size at the front (BR-01, h = 1.25 mm: 2.5 and 5 mm).

### 2.3 Number of nodes along the front

With `DISCRETISATION='LINEAIRE'` (default) and only 3 nodes along the front (2
elements) G and K oscillated from node to node (measured: 11,739 / 4,696 / 25,826 J/m²
where 9,391 was expected; hex8 and hex20 alike). With 5 nodes or more they did not.
With fewer than 5 nodes the bridge gives a WARNING; then choose a finer mesh along the
front or `LEGENDRE` with degree 0 (a constant, correct in plane strain). Legendre with
too high a degree (5 with 3 nodes) gave −8 to −22 %.

## 3. Accuracy and mesh advice

Centre crack in a plate (plane strain, a/b = 0.5, BR-01), deviation of K_I and G in
the middle of the front from Tada (2000), with the default settings:

| Mesh at the front (h) | hex20: K_I / G (`CALC_G`) | hex20: K_I (`POST_K1_K2_K3`) | hex8: K_I / G (`CALC_G`) | hex8: K_I (`POST_K1_K2_K3`) |
|---|---|---|---|---|
| h ≈ a/12 (coarse) | −0.45 % / −1.6 % | −3.3 % | −1.3 % / −4.3 % | −8.7 % |
| h = a/20 | −0.24 % / −0.9 % | −2.9 % | −0.9 % / −2.8 % | −11 % |
| h = a/40 | −0.10 % / −0.4 % | −3.5 % | −0.7 % / −2.0 % | −10 % |
| h = a/40, quarter-point nodes | +0.02 % / +0.02 % | −0.1 % | - | - |

(hex8 with 8 elements through the thickness; with 2 see §2.3.) Advice:

- **hex20** (or `LINE_QUAD`) with h ≈ a/10 … a/20 at the front: K from `CALC_G`
  within 1 %, G within 2 %.
- **hex8**: K within 2 % from h ≈ a/12, G needs h ≈ a/40 for 2 %; `POST_K1_K2_K3` is
  ~10 % low with hex8, use `CALC_G`.
- **Quarter-point nodes** (the mid-side nodes of the edges from the front at 1/4 of
  the edge) make `POST_K1_K2_K3` exact. The bridge does not place them itself
  (KNOWN_BUGS 63) and Mecway cannot make them; `CALC_G` does not need them.
- `R_INF`/`R_SUP` (automatic, 2 × /4 ×, 4 × /8 ×, 8 × /16 × h) gave the same values;
  R_INF = 0 gave G −1.3 %.

## 4. What is not possible

- **Analyses other than linear static** (nonlinear, dynamics, modal, thermal):
  WARNING, no K and G.
- **Contact on the lips** and plasticity (J integral in a nonlinear analysis): not
  built.
- **K and G as a field in Mecway:** no; only the table and the log.
- **Quarter-point nodes** by the bridge: no (the result export checks the node
  coordinates against the `.liml`). If they are already in the `.liml` (e.g. a mesh
  from another program), it works (BR-04).
- **A crack without meshing it**: XFEM, §7.
- **NOT verified:** a crack on an interface between materials (WARNING), thermal
  strain, pressure on the lips, tet10 meshes around the front (forma07a has wedge15 at
  the front: BR-04), a closed front, shells in the model.

## 5. Messages and solutions

| Message | Cause | Solution |
|---|---|---|
| ERROR: Fracture mechanics: '...' must be a node selection/face selection | `CRACK_FRONT` as a face selection, or a lip as a node selection | make the selection again of the right kind (§1.3) |
| ERROR: ... crack '...' is incomplete | front or upper lip missing (e.g. a typo in the name) | all selections with the same name and the same suffix (§1.3) |
| ERROR: ... two selections for the same crack | two selections that end up with the same name (case does not count) | a suffix of its own per crack |
| ERROR: ... no edge of a solid element with both end nodes in '...' | the front nodes are not neighbours on an element edge, or the front lies on shells | select all nodes along the front; the front must be an edge of solid elements |
| ERROR: ... do not form a single line (branch / several pieces) | two fronts in one selection, or extra nodes | one selection per front, with a suffix |
| ERROR: ... upper and lower lip ... share ... nodes outside the front: the crack is not open | the crack was not disconnected | §1.2 (Disconnect elements, then Merge nearby nodes only for ligament and front) |
| ERROR: ... the lips ... must be faces of solid elements | a lip on shells | model the crack in solid elements |
| ERROR: ... fracture_r_inf and fracture_r_sup: need 0 <= R_INF < R_SUP | wrong settings | both 0 (automatic) or R_INF < R_SUP |
| WARNING: ... node(s) of '...' are not on an edge along the front | stray nodes in the front selection | harmless; they are ignored |
| WARNING: ... the lips ... share no front nodes | the front was disconnected too | merge the front nodes again (§1.2 steps 3-4) |
| WARNING: ... has only n nodes; ... oscillate | short front (< 5 nodes) | finer mesh along the front, or `LEGENDRE` degree 0 (§2.3) |
| WARNING: ... Legendre degree ... with n nodes | degree too high | degree below the number of nodes |
| WARNING: ... not a straight line nor a disc-shaped circle | curved front, or a circle with the lip outside it | use G or K from `POST_K1_K2_K3` |
| WARNING: ... different materials | front on an interface | NOT verified; check with a calculation of your own |
| WARNING: ... K_I is negative | compression on the crack (lips overlapping) | no mode I growth; meaningless without contact (§1.6) |
| WARNING: ... K_I from CALC_G and from POST_K1_K2_K3 differ by up to ...% | coarse mesh, unfavourable R_INF/R_SUP or a curved front | refine the mesh around the front (§3) |
| WARNING: ... POST_K1_K2_K3 gave no values | `POST_K1_K2_K3` failed (error in the `.mess` after `BRIDGE_SCHEUR_POSTK_FOUT`) | use `CALC_G`; see the `.mess` |
| WARNING: Fracture mechanics (CRACK_ selections) only works for linear static | another analysis | normal; no K and G |

## 6. Verification

[`Verification.md`](Verification.md) chapter Fracture mechanics (BR):

- **BR-01** centre crack in a plate, plane strain, hex20, both lips (double nodes):
  K_I −0.10 % from Tada, G −0.41 %, G/(K_I²/E') = 0.998.
- **BR-02** the same as a half model (`SYME='OUI'`): equal to BR-01.
- **BR-03** thick plate (B = 4a) with free side faces: K_I at the mid-plane +0.7 %.
- **BR-04** Code-Aster test case forma07a through the bridge: K1 MAX of
  `POST_K1_K2_K3` 1,607,011.55 = the TEST_TABLE value; K_I from `CALC_G` −0.8 % and G
  +0.8 % from the analytical solution.
- **BR-05** as BR-01 with hex8: K_I −0.7 %, G −2.0 %.
- **BR-06** two fronts as two cracks (`_L`, `_R`): per front equal to BR-01.

XFEM (§7):

- **BR-07** the plate of BR-01 without a crack in the mesh, `HALF_PLANE`, hex8 h =
  a/20: K_I −0.08 %, G −0.18 %, `POST_K1_K2_K3` −0.24 %; the lips open equally in
  Mecway.
- **BR-08** idem with hex20: K_I +0.10 %, G +0.17 %.
- **BR-09** idem with the crack plane through nodes and the front on element
  boundaries: K_I −0.06 %, G −0.05 %.
- **BR-10** penny-shaped crack in a block, `CIRCLE`: K_I `POST_K1_K2_K3` +1.6 %, K from
  G +1.0 %, K_I `CALC_G_XFEM` +5.3 % (no curvature correction); crack opening +3.3 %
  (Sneddon).
- **BR-11** Code-Aster test case forma07b through the bridge: K1 MAX of `CALC_G_XFEM`
  and `POST_K1_K2_K3` equal to the TEST_TABLE values.
- **BR-12** centre crack over the full width as `RECTANGLE` (two fronts): per front as
  BR-07.
- **BR-13** the crack of BR-09 as face selection `XFEM_midden` (§7.8): K_I −0.06 %,
  G −0.05 %, `POST_K1_K2_K3` +1.1 %.
- **BR-14** BR-07 with `med_export`: `_xfem.rmed` with `DEPL`, `SIGM_NOEU` and
  `SIEQ_NOEU` on the mesh that follows the crack; opening 99.6 % (§7.9).

## 7. XFEM: a crack without meshing it

With XFEM (*extended finite element method*) the crack does not need to be in the
mesh: you describe it with a shape (circle, ellipse, rectangle or half plane) in an
`#ASTER-XFEM` line, or with a face selection `XFEM_<name>` in Mecway (a free shape on
a layer of nodes, §7.8), and Code-Aster lets it run through the elements as a *level
set* (`DEFI_FISS_XFEM`). This way you can put a crack at any place and in any orientation
in an existing, uncracked mesh, without *Disconnect elements* and without adapting the
mesh to the crack plane. You get the same output as for a meshed crack: K_I, K_II,
K_III and G along the front, and the usual results in Mecway (§7.5).

| What | Where you see it |
|---|---|
| K_I, K_II, K_III and G per point along the front | table `<model>_<run-id>_xfem.csv` in the work folder |
| range of K_I and G per front, and messages | log and status box after the run |
| displacements, stresses, reactions (with the crack) | Mecway, as always (§7.5) |
| the mesh that follows the crack, with displacement and stress (the opening is visible) | `<model>_<run-id>_xfem.rmed` in the work folder, only with the setting *MED file for ParaView* (§7.9) |

### 7.1 Step-by-step workflow

1. **Model in Mecway** as always: analysis type *Static* (S30), only solid elements
   (hex8, hex20, tet4, wedge, pyramid; no shells, beams, springs or loose nodes,
   §7.6), constraints and loads. Do **not** make a crack in the mesh.
2. **Fine mesh around the location of the front**: elements perpendicular to the
   front of about a/20 (a = radius or smallest semi-axis; for a through crack the half
   crack length), §7.4. The front and the crack plane may run through the elements and
   also through nodes or along element boundaries (BR-07, BR-09).
3. **Describe the crack** in a free text field of Mecway, e.g. *CCX > Custom model
   definition* (line with `**`), *OpenRadioss > Custom model definition* (`#`) or
   *Mystran > Custom bulk data* (`$`), see
   [`ASTER_lines_examples.md`](ASTER_lines_examples.md) example 29:

   ```
   ** ASTER-XFEM shape=CIRCLE, centre=(0, 0, 0), r=20 mm, normal=(0, 0, 1)
   ```

   A line starting with `shape=` (or `vorm=`) is a new crack; a following line without
   `shape=` belongs to the same crack (to split long lines). More cracks: more lines
   with `shape=` (each with its own `name=`). Or: a face selection `XFEM_<name>` with
   the faces in the crack plane, without an `#ASTER-XFEM` line (§7.8).
4. **Settings** (page *Static*, heading *Fracture mechanics*): `fracture_r_inf` /
   `fracture_r_sup` also apply to XFEM (§1.4); per crack `r_inf=`/`r_sup=` is possible.
5. *Start*. The log and the status box give per front the range of K_I from
   `CALC_G_XFEM` and from `POST_K1_K2_K3`, and G, for example (BR-10: the line above with `name=penny`):

   ```
   Fracture mechanics XFEM, crack penny: 38 points along the front. K_I 0.1648 ..
   0.1728 MPa.m^0.5 (CALC_G_XFEM), 0.1605 .. 0.1679 MPa.m^0.5 (POST_K1_K2_K3); G
   0.1102 .. 0.1165 J/m2. K_II up to 4.91e-05, K_III up to 0.00013 MPa.m^0.5. Table:
   BR-10_verif_xfem.csv
   ```

   The table has per point the same columns as for a meshed crack (§1.5), with a
   column `front` (1, 2, … per front of the crack) and without `node` (the points are
   intersections of the front with the elements, not nodes).

### 7.2 Keys of `#ASTER-XFEM`

Lengths and coordinates in m (like all `#ASTER` lines) or with a unit (`r=20 mm`,
`centre=(10, 0, 5) mm`). Directions need not be unit vectors. Case does not matter;
the Dutch names work as well.

| Key (Dutch) | With shape | Meaning | Default | When to change |
|---|---|---|---|---|
| `shape` (`vorm`) | – | `CIRCLE` (`CIRKEL`), `ELLIPSE`, `RECTANGLE` (`RECHTHOEK`) or `HALF_PLANE` (`HALFVLAK`, Code-Aster `DEMI_PLAN`) | required | – |
| `centre` (`centrum`) | CIRCLE, ELLIPSE, RECTANGLE | centre (x, y, z) | required | – |
| `r` (`radius`, `straal`) | CIRCLE | radius | required | – |
| `normal` (`normaal`) | CIRCLE, HALF_PLANE | normal to the crack plane | required | – |
| `a`, `b` | ELLIPSE, RECTANGLE | semi-axes along `vect_x` and `vect_y` | required | – |
| `vect_x`, `vect_y` | ELLIPSE, RECTANGLE | direction of the axes in the crack plane, perpendicular to each other | required | – |
| `fillet` (`afronding`) | RECTANGLE | radius of the rounded corners (`RAYON_CONGE`) | 0 | a rectangle whose corners lie in the material |
| `point` (`front`) | HALF_PLANE | a point on the (straight) front | required | – |
| `direction` (`richting`) | HALF_PLANE | growth direction of the front: in the crack plane, perpendicular to the front, from the crack into the uncracked material | required | – |
| `name` (`naam`) | all | name in the table and the log (letters, digits, `_`, max. 16) | 1, 2, … | more cracks |
| `group` (`groep`) | all | `<<element selection>>`: Code-Aster may enrich only there (`GROUP_MA_ENRI`) | the whole model | large models; NOT verified |
| `smoothing` (`glad`) | all | smoothing along the front in `CALC_G_XFEM`: `LAGRANGE` or `LEGENDRE` | straight front (HALF_PLANE, RECTANGLE): `LAGRANGE`; curved (CIRCLE, ELLIPSE): `LEGENDRE` | see §7.3 |
| `degree` (`graad`) | `LEGENDRE` | degree of the polynomial (0 .. 7) | `fracture_legendre_degree` (5) | short front: 0 or 1 (§7.3) |
| `points` (`punten`) | all | number of points along the front (`NB_POINT_FOND`, evenly spaced) for `CALC_G_XFEM` and `POST_K1_K2_K3` | the intersections of the front with the elements | a regular table; never more than the number of intersections |
| `r_inf`, `r_sup` | all | ring of the theta field (m) | `fracture_r_inf`/`_sup`, 0 = automatic (2h/4h) | as §1.4 |

A rectangle that sticks out of the model only gives fronts inside the model: a through
crack in a plate is a `RECTANGLE` spanning the thickness (two straight fronts, BR-12)
or a `HALF_PLANE` (one front, BR-07). A `HALF_PLANE` is cracked everywhere on one side
of the front: use it when the front is the only end of the crack in the model (e.g. an
edge crack, or a half model with the crack up to the symmetry plane).

### 7.3 How the bridge translates

1. The bridge's model is called `model_sain`; per crack `DEFI_FISS_XFEM` and then
   `model = MODI_MODELE_XFEM(MODELE_IN=model_sain, FISSURE=(...))`. Loads and
   `MECA_STATIQUE` use the XFEM model.
2. A *Symmetry* along a global axis becomes `DDL_IMPO` with XFEM (otherwise
   `LIAISON_OBLIQUE`): `DDL_IMPO` also fixes the XFEM degrees of freedom of the nodes of
   cut elements, `LIAISON_OBLIQUE` does not. Measured (BR-11, symmetry planes through
   the crack): with `LIAISON_OBLIQUE` K1 at the symmetry plane +3.8 %, with `DDL_IMPO`
   equal to the test case. An oblique constraint on such a node gives a WARNING.
3. Results for Mecway: the displacement of the XFEM model has extra degrees of freedom
   and is not the physical displacement at a node of a cut element. `POST_MAIL_XFEM` +
   `POST_CHAM_XFEM` give the displacement and the stress on a mesh that follows the
   crack; every Mecway node is a node of that mesh, so `PROJ_CHAMP` (`COLLOCATION`)
   puts `DEPL`, `SIGM_NOEU` and `SIEQ_NOEU` back on the Mecway nodes with the value on
   their own side of the crack. `REAC_NODA` comes from the XFEM result. That result
   goes to Mecway as always.
4. After the export, per crack and per front (`NUME_FOND`; a rectangle through a plate
   has two):

```
_tg = CALC_G_XFEM(RESULTAT=res_xfem, OPTION='CALC_K_G',
                  THETA=_F(FISSURE=fiss_1, NUME_FOND=_k[, R_INF=.., R_SUP=..][, NB_POINT_FOND=..]),
                  LISSAGE=_F(LISSAGE_G='LEGENDRE', LISSAGE_THETA='LEGENDRE', DEGRE=5))
_tp = POST_K1_K2_K3(RESULTAT=res_xfem, FISSURE=fiss_1, NUME_FOND=_k
                    [, ABSC_CURV_MAXI=R_SUP][, NB_POINT_FOND=..])
```

`ABSC_CURV_MAXI = R_SUP` only when R_SUP is given (like test case forma07b).

**Smoothing** (measured during the build, hex8): the front points are the
intersections of the front with the element faces. For a straight front through a
regular mesh they are regular and `LAGRANGE` is good (13 points: K_I within ±1 %);
`LEGENDRE` with degree 2 gave ±3 % there and degree 4-5 ±25 % (with 5 points only
degree 0-1 worked). For a curved front the intersections are irregular (sometimes
close together): `LAGRANGE` oscillated there from −0.1 to 2 × K (penny, 38 points),
`LEGENDRE` degree 5 was smooth. Hence the default per shape (§7.2). The table and the
WARNING for a difference with `POST_K1_K2_K3` (> 5 %) show whether it went well.

### 7.4 Accuracy and mesh advice

Measured with the bridge (verification BR-07..14, [`Verification.md`](Verification.md)):

| Case | Mesh at the front | K_I `CALC_G_XFEM` | G | K_I `POST_K1_K2_K3` |
|---|---|---|---|---|
| centre crack plate (Tada), HALF_PLANE, front through the elements (BR-07) | hex8, h = a/20 | −0.08 % | −0.18 % | −0.24 % |
| idem, hex20 (BR-08) | hex20, h = a/20 | +0.10 % | +0.17 % | −0.13 % |
| idem, crack plane through nodes, front on element boundaries (BR-09) | hex8, h = a/20 | −0.06 % | −0.05 % | +1.1 % |
| idem as RECTANGLE, two fronts (BR-12) | hex8, h = a/20 | −0.09 % | −0.19 % | −0.29 % |
| idem from a face selection `XFEM_` (mesh of BR-09, BR-13) | hex8, h = a/20 | −0.06 % | −0.05 % | +1.1 % |
| penny-shaped crack (2σ√(a/π)), CIRCLE (BR-10) | hex8, h = a/20 | +5.3 % (no curvature correction) | +1.9 % (K from G +1.0 %) | +1.6 % |

Mesh study penny-shaped crack (hex8, middle of the front, outside the regression):

| h at the front | K_I `CALC_G_XFEM` (`LEGENDRE` 5) | G | K_I `POST_K1_K2_K3` |
|---|---|---|---|
| a/20 | +5.3 % | +1.9 % | +1.6 % |
| a/10 | +10 % | +4.8 % | +3.2 % |
| a/5 | +15 % | +11 % | +1.5 % |

Advice:

- **Straight fronts**: hex8 with h ≈ a/20 gives K and G within 0.3 %; hex20 is not
  needed. The front and the crack plane may lie anywhere in the mesh.
- **Curved fronts** (CIRCLE, ELLIPSE): `CALC_G_XFEM` has no curvature correction (the
  meshed crack does, `FORM_FISS='CERCLE'`, §2.1): K from `CALC_G_XFEM` is 3 to 5 % too
  high at h = a/20 and more on a coarser mesh. Use **K from `POST_K1_K2_K3`** (column
  `K1_POST_K`, +1.6 %) or K from G: K = √(G E/(1 − ν²)) (plane strain, mode I;
  +1.0 %). The bridge gives a WARNING.
- **Mesh**: h ≤ a/20 perpendicular to the front; above a/10 the bridge gives a
  WARNING. Refine only around the front (a tube of a few elements); the rest may be
  coarse.
- R_INF/R_SUP automatic (2h/4h) was good in all cases; forma07b uses 2h/5h.

### 7.5 Interpretation

- **K and G**: as for a meshed crack (§1.6). At a free surface or a symmetry plane
  (the end points of the front) the methods differ; judge the interior of the front.
- **Fields in Mecway**: the displacement is the physical displacement of each node on
  its own side of the crack (BR-07: upper and lower lip open equally; BR-10: the
  opening of the penny crack +3.3 % from Sneddon, including the distance of the nodes
  to the crack plane). Stresses and von Mises are node fields from the mesh that
  follows the crack (no element-node values, `SIGM_ELNO`). A node exactly on the crack
  plane gets the value of one lip. Mecway does not draw the crack: the elements it cuts
  are interpolated across the crack.
- **Reactions**: from the XFEM result; on nodes of cut elements only the classical
  part (NOT verified). Constraints away from the crack are normal.

### 7.6 What is not possible

- Analyses other than linear static: WARNING, the crack is ignored.
- Shells, beams, springs and loose nodes in the model, or `elem_hex8` = `3D_SI`:
  ERROR. `LINE_QUAD` works (BR-07 with LINE_QUAD: K_I 0.0 %, outside the regression).
- Contact between the lips (a crack under compression: K_I < 0, WARNING), crack growth
  (`PROPA_FISS`), cohesive cracks and branched cracks (`JONCTION`).
- Error estimator and fatigue together with XFEM (INFO/WARNING; they are skipped).
- A shape from an own level set (`FONC_LN`/`FONC_LT`): not built; possible with own
  `#ASTER` code. A crack from a face selection always lies on a layer of nodes
  (§7.8); a free shape through the elements is not possible.
- **NOT verified**: tet10, wedge15, pyr13 (tet4 and pyram5 are, BR-11), `group=`,
  more than one XFEM crack in a model, an ELLIPSE with a ≠ b, `fillet`.

### 7.7 Messages and solutions

| Message | Cause | Solution |
|---|---|---|
| ERROR: #ASTER-XFEM: unknown or incomplete '...' | typo in a key, or no `=` | keys from §7.2 |
| ERROR: #ASTER-XFEM: '...' has no valid value | e.g. a vector with two numbers, or a group without `<<` `>>` | `(x, y, z)`, `<<selection>>`, number with or without a unit |
| ERROR: ... give the shape / missing for ... | `shape=` missing or a required key of that shape | §7.2 |
| ERROR: ... vect_x and vect_y are not perpendicular / direction must be perpendicular to the normal | wrong axes | axes in the crack plane, perpendicular |
| ERROR: ... the crack cuts no solid element | the crack lies outside the model; often mm instead of m | coordinates in m, or with a unit (`r=20 mm`) |
| ERROR: ... the front lies outside the model | the crack cuts all the way through the model (or a HALF_PLANE with the front outside the model) | smaller crack, another shape or reverse `direction` |
| ERROR: ... group '...' is not an element selection | name of `group=` | an existing element selection |
| ERROR: ... R_INF ... and R_SUP | R_INF ≥ R_SUP | both 0 or R_INF < R_SUP |
| ERROR: #ASTER-XFEM only works in a model with only solid elements / only knows MODELISATION '3D' | shells, beams, springs or `3D_SI` | §7.6, or a meshed crack (§1) |
| WARNING: ... the elements at the front ... are larger than 1/10 of the crack size | coarse mesh | refine around the front (§7.4) |
| WARNING: ... curved front; K from CALC_G_XFEM has no curvature correction | CIRCLE/ELLIPSE | use `K1_POST_K` or G (§7.4) |
| WARNING: ... the constraint on '...' is oblique (LIAISON_OBLIQUE) | oblique symmetry or imposed direction on nodes of cut elements | §7.3 item 2 |
| WARNING: Fracture mechanics XFEM ... K_I from CALC_G_XFEM and from POST_K1_K2_K3 differ by up to ...% | curved front, coarse mesh, or unfavourable `smoothing`/`degree` | §7.3, §7.4 |
| WARNING: Fracture mechanics XFEM ... K_I is negative | compression on the crack | see §1.6 |
| WARNING: Fracture mechanics XFEM ... POST_K1_K2_K3 gave no values | `POST_K1_K2_K3` failed (`BRIDGE_XFEM_POSTK_FOUT` in the `.mess`) | use `CALC_G_XFEM`; see the `.mess` |
| ERROR: XFEM crack '...': face ... is not a face of a solid element | the `XFEM_` selection contains a shell or beam face | only faces of solid elements (§7.8) |
| ERROR: XFEM crack '...': an edge belongs to more than two faces | branched crack surface (e.g. a T) | one `XFEM_` selection per branch |
| ERROR: XFEM crack '...': the face selection has no edge inside the solid | the surface runs all the way through the model, or the faces are outer faces | only the faces of the crack, not the ligament (§7.8) |
| ERROR: XFEM: two cracks named '...' | `name=` and `XFEM_<name>` equal | another name |
| WARNING: XFEM: '...' is a node selection / element selection | `XFEM_` on a selection of the wrong kind | a face selection (§7.8) |
| WARNING: XFEM (#ASTER-XFEM, XFEM_ selections) only works for linear static | another analysis | normal; the crack is ignored |
| `<A> <XFEM_63>` in the `.mess` (adjustment of the level set) | quadratic elements or a crack plane close to nodes | harmless (BR-08, BR-09) |
| `<A> <QUALITY1_1>` | Code-Aster: XFEM is not qualified for safety studies (*études de sûreté*) | for information |

### 7.8 Crack from a face selection (`XFEM_<name>`)

A crack with a shape that is not a circle, ellipse, rectangle or half plane (e.g. an
L shape or a crack along a weld) is given as a **face selection** in Mecway. The input
follows the rule of the bridge: first what Mecway itself knows (a face selection),
then a special name; no `#ASTER-XFEM` line is needed.

1. The mesh must have a **layer of nodes in the crack plane**: the crack surface
   consists of element faces and the front of element edges. The crack is **not**
   open in the mesh (no *Disconnect elements*); XFEM opens it.
2. Select the **faces in the crack plane** (only the crack, not the ligament). These
   faces lie inside the model: put Mecway in *Select faces*, move the *Cutting plane*
   until the elements on one side of the plane are hidden and pick the faces of the
   visible elements (Mecway Ltd., 2026, §9.12 and §17.2; NOT tried in the Mecway GUI
   with a crack plane in the model). It does not matter from which element (above or
   below) a face comes: the bridge aligns the normals itself (BR-13 picks them
   alternately).
3. Make it a *Named selection* named **`XFEM_<name>`**, e.g. `XFEM_A` (upper or lower
   case; XFEM is the same in Dutch and English). `<name>` is the name of the crack in
   the table and the log. More cracks: more selections (`XFEM_A`, `XFEM_B`); they may
   be combined with `#ASTER-XFEM` lines.
4. *Start*, otherwise as §7.1.

How the bridge translates it: the faces become separate cells (`QUAD4`/`TRIA3`, corner
nodes only, normals aligned) in group `BRXF<n>S`, the edge of the selection that lies
**inside the solid** becomes `SEG2` cells in `BRXF<n>F` (the front; an edge on an outer
face or a symmetry plane is the mouth of the crack, not a front). These cells are not
part of the model. The normal of the crack surface is a fixed choice: the largest
component of the mean normal positive (a crack in the plane y = 0 gets normal +y).
Why: with a crack plane on a layer of nodes the solution depends slightly on the
normal; with normal −y the upper lip in BR-13 opened 1.8 % further than the lower lip
(K equal within 0.05 %), with +y the result equals BR-09. Then

```
fiss_1 = DEFI_FISS_XFEM(MAILLAGE=mesh, TYPE_DISCONTINUITE='FISSURE',
                        DEFI_FISS=_F(GROUP_MA_FISS='BRXF1S', GROUP_MA_FOND='BRXF1F'))
```

(catalogue `defi_fiss_xfem.py`; likewise the Code-Aster test cases `sslv314b` and
`sslv320d`, where the crack surface is a separate mesh). Code-Aster computes the level
sets from these cells. Smoothing: `LAGRANGE` if every piece of the front is straight,
otherwise `LEGENDRE` (as for the shapes, §7.3); the settings `fracture_r_inf`/`_sup`
and `fracture_legendre_degree` apply. Keys per crack (`points=`, `smoothing=`,
`r_inf=`) do not exist for a selection.

Measured (BR-13, mesh of BR-09 with the crack as a selection): K_I −0.06 %, G −0.05 %,
`POST_K1_K2_K3` +1.1 % relative to Tada, as BR-09 with `HALF_PLANE` (§7.4). Because
the crack plane lies on a layer of nodes, the nodes in the plane get the value of one
lip in Mecway (§7.5); the node layers next to it open equally far (upper/lower −1.0004).

Not possible: a crack surface through the elements (use a shape), a branched crack
surface in one selection, faces of shells. NOT verified: a curved crack surface or
front from a selection, tet elements and quadratic elements (the cells only use the
corner nodes).

### 7.9 MED file for ParaView: seeing the crack open

Mecway does not draw the XFEM crack (§7.5). With the setting **MED file for ParaView**
(`med_export`) the bridge writes, next to the usual `<model>_<run-id>.rmed`, also
**`<model>_<run-id>_xfem.rmed`**: the mesh of `POST_MAIL_XFEM`, in which the elements
along the crack are subdivided and each lip has its own nodes, with the fields `DEPL`,
`SIGM_NOEU` and `SIEQ_NOEU` of `POST_CHAM_XFEM` (`IMPR_RESU`, UNITE 81 in the
`.export`). Open it with the "ParaView" or "AsterStudy" button in the Results window or the
convergence window ([User guide §5.1](UserGuide.md#51-loading-results-again-later-small-liml)):
both open the `_xfem.rmed` before the other result files of the run. With *Warp By Vector* on
`DEPL` you see the crack open. The groups of the model (element sets, selections) are in it; the fields
are called `res_xvisDEPL`, `res_xvisSIGM_NOEU` and `res_xvisSIEQ_NOEU`. The usual
`.rmed` has the fields on the original mesh (without opening).

Measured (BR-14, read back with the MEDCoupling of the Code-Aster installation): the
three fields and the group of the part are in it, and the opening between the lip
nodes in the middle of the crack is 99.6 % of the opening Mecway sees between the
nodes at ±h/2.

## 8. Sources

- EDF R&D. *code_aster 17.4*: catalogue `lib/aster/code_aster/Cata/Commands/`
  `defi_fond_fiss.py`, `calc_g.py`, `post_k1_k2_k3.py`, `crea_resu.py`; test case
  `forma07a` (`share/aster/tests`); XFEM: `defi_fiss_xfem.py`, `modi_modele_xfem.py`,
  `calc_g_xfem.py`, `post_mail_xfem.py`, `post_cham_xfem.py`, `proj_champ.py`,
  `MacroCommands/post_k1_k2_k3_ops.py` (several fronts: `getCrackTipMultiplicity`),
  test case `forma07b` (com1/com2, mesh `forma07b.41`); crack from a group of cells
  (`GROUP_MA_FISS`/`GROUP_MA_FOND`): test cases `sslv314b`, `sslv320d`. The U documents (U4.82.03 `CALC_G`, U4.82.05
  `POST_K1_K2_K3`, U2.05.01 fracture mechanics) are not available locally: NOT
  consulted.
- Mecway Ltd. (2026). *Mecway 33 manual*, §4.2.10 Disconnect elements, §4.2.11 Merge
  nearby nodes, §9.12 and §17.2 (*Select faces*, *Cutting plane*)
  (`C:\Program Files\Mecway\manual.pdf`).
- Tada, H., Paris, P.C. & Irwin, G.R. (2000). *The Stress Analysis of Cracks
  Handbook*, 3rd ed. New York: ASME Press, p. 2.2 (centre crack in a strip), p. 24.2
  (penny-shaped crack: K = 2σ√(a/π), opening 8(1 − ν²)σ√(a² − r²)/(πE)).
- Sneddon, I.N. (1946). The distribution of stress in the neighbourhood of a crack in
  an elastic solid. *Proc. R. Soc. Lond. A* 187, 229-260 (penny-shaped crack). Not
  consulted locally; via Tada p. 24.2.
- Anderson, T.L. (2005). *Fracture Mechanics: Fundamentals and Applications*, 3rd ed.
  Boca Raton: CRC Press (K_IC, plane strain, edge effect). Not consulted locally;
  general background.
