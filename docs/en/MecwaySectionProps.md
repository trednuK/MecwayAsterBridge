# MecwaySectionProps: section properties of a face in Mecway

*Nederlandse versie: [MecwaySectionProps.md](../MecwaySectionProps.md)*

MecwaySectionProps computes the properties of a flat cross-section that you select in
Mecway: area, centroid, second moments of area (also about the principal axes), section
moduli (elastic and plastic), torsion constant J, warping constant Iw, shear centre and
shear areas. With one button it turns them into a Mecway material with a *General
section*, and it stores the characteristics Mecway has no field for (shear coefficients,
eccentricity of the shear centre, warping, ...) in the model, so that the bridge uses
them in Code-Aster without estimating them afterwards.

It is the Mecway version of AreaPropsForAlibre (the same window and quantities), but
without extra Python packages: the analysis runs in the Python that comes with Code-Aster
(numpy and scipy).

| What | Where |
|---|---|
| table with all quantities, in mm or m | the window (button *Copy*: pastes into Excel) |
| drawing: section, centroid, x/y axes, principal axes 1 (V) and 2 (W) with angle φ, shear centre | the window, on the right |
| Mecway material with a *General section* (area, Iyy, Izz, torsion constant, perimeter, stress recovery point) | Mecway, after *Create general section* |
| extra Code-Aster characteristics (`AY`, `AZ`, `EY`, `EZ`, `RY`, `RZ`, `RT`, `JG`, `IYR2`, `IZR2`) | one `#ASTER-SECTIE` line per material in the custom model definition (§5) |
| input and result of the last analysis | `section_props\section_input.json` and `section_results.json` in the bridge's work folder |

## 1. Installation

1. Install the bridge and Code-Aster as described in [`UserGuide.md`](UserGuide.md) §1.
   MecwaySectionProps uses Code-Aster's Python (`<Code-Aster>\Python311\python.exe`,
   found through the bridge setting `exe_aster`); nothing else needs to be installed.
2. Add the script to Mecway: *Tools* > *Scripts...* > *New*, and choose
   `Scripts\MecwaySectionProps.py` (the same folder as `MecwayAsterBridgeMain.py`). The
   script then appears as an item in the *Tools* menu.

## 2. Use

1. In Mecway, in **face selection** (*Select faces*), select the faces of the
   cross-section: for example the end faces of an extruded profile or the cut face of a
   solid. All faces must lie in one flat plane.
2. Start *Tools* > `MecwaySectionProps`. The window stays open next to Mecway: you can
   make another selection and click **Calculate** again. Starting the script a second
   time brings the open window to the front.
3. Choose the input:
   - **Mesh faces (selection)**: the boundary of the selected mesh faces. Edges shared
     by two selected faces drop out; what remains is the outer boundary and the boundary
     of holes. With quadratic elements (tet10, hex20, ...) the boundary follows the
     parabola through the midside node (curved edges). Works for any model, also without
     CAD.
   - **CAD face (exact STEP boundary)**: only for a component Mecway meshed from a STEP
     geometry (*Geometry* in the model). The tool looks up, in the STEP file, the flat
     CAD face that the selected mesh faces lie on and uses its **exact** boundary (lines,
     circles, ellipses, B-splines), independent of the mesh density. Select one or more
     mesh faces on the CAD face; the whole CAD face counts. Several adjacent CAD faces in
     the same plane are merged. The model must be saved (the link component → STEP file
     is in the `.liml`).
4. Click **Calculate**. The analysis (a mesh of about 3000 quadratic triangles and the
   finite element analysis for torsion and shear) takes a few seconds; the status line
   counts along.
5. Read the table and the drawing; *Copy* puts the table on the clipboard
   (tab-separated, Windows decimal separator). *NL*/*EN* at the top right switches the
   language, *Unit* between mm and m.

**Small gaps in the boundary** are repaired automatically so that the analysis can
still run; every repair is listed as a note under the table:

- *Mesh faces*: nodes at (almost) the same place (within 1e-4 of the size, e.g. an
  imported mesh with duplicate nodes) become one node; an edge with a node of another
  face on it (T-joint of a non-conformal mesh) is split there; free ends of the boundary
  are joined to the nearest free end with a straight line.
- *CAD face*: edges whose end points do not exactly meet are joined with a straight
  line.
- A gap is only closed up to 2% of the size of the section; a larger one stops the
  analysis with the location of the gap. A real slot (with its own edges) has no free
  ends and therefore stays open.

## 3. What the window shows

**Axes.** The section is seen from outside the solid (as in AreaPropsForAlibre): the
normal n points out of the elements, y is the global Y axis projected onto the plane (or
−Z/+Z for a face normal to Y) and x = y × n. The origin is the model origin, so the
centroid is in model coordinates; below it also globally (X; Y; Z).

| Group | Quantities |
|---|---|
| Geometry | A, perimeter of the outer boundary, centroid |
| Second moments | Ixx, Iyy, Ixy about the centroid; principal moments I11 ≥ I22; angle φ from +x to principal axis 1 (counter-clockwise); radii of gyration |
| Section moduli | elastic Wx (top/bottom), Wy (right/left), W1, W2 (smallest about the principal axes); plastic Wpl,x, Wpl,y, Wpl,1, Wpl,2 |
| Torsion, warping, shear | J (Saint-Venant), Iw (about the shear centre), shear centre (x; y), shear areas As,1 and As,2 (along the principal axes) |
| Mecway general section | the values *Create general section* fills in, and the directions U, V, W (§4) |
| Code-Aster GENERALE | `AY`, `AZ`, `EY`, `EZ`, `RY`, `RZ`, `RT`, `JG`, `IYR2`, `IZR2` (§5) |

Torsion, warping and shear exist only for a connected section; when the selection
consists of separate parts, the reason is shown under the table and no *General section*
can be created from it.

## 4. Creating the general section

At the bottom of the window:

- **Material name**: the name of the new Mecway material (if it exists already, Mecway
  makes it `name(2)`).
- **Assign to**: a beam component (line2/line3) that gets the material, or none.
- **Copy E, ν, ρ**: copies the isotropic elastic data (E, ν, α) and the density from the
  component's current material, so that only the section changes.
- **Store extra Code-Aster properties**: puts the `#ASTER-SECTIE` line in the model
  (§5), as an extra *custom model definition* under *CCX* in the tree (the tool imports a
  small `.liml` file for it; there is no Mecway API for that text field). The model is not
  saved or reopened; save it yourself, or let the bridge do it at the next run. Click once
  in the tree if the new material (under *Unused Materials*) or the *custom model
  definition* is not shown yet.

The material gets a *General section* with:

| Mecway | Value |
|---|---|
| Area | A |
| Iyy (about V) | I11 |
| Izz (about W) | I22 |
| Torsion constant | J |
| Perimeter | perimeter of the outer boundary |
| Stress recovery point (V; W) | the boundary point farthest from the centroid, in principal axes |

**Beam orientation.** Mecway's *General section* only has principal moments, so the beam
must be turned such that its V axis lies along principal axis 1. In Mecway
(*Loads & Constraints* > *Element orientation*, or *Element properties*) enter the
direction from the table (*V vector (axis 1)*) as the V vector. Mecway's U axis runs
along the beam (node 1 → 2) and W = U × V; that is the same as x, y, z in Code-Aster.
`EY`, `EZ` (and `IZR2`) apply to a beam that runs in the direction of the normal n
(*Beam axis U = normal n* in the table). A beam running the other way sees the section
mirrored; for a section that is symmetric about a principal axis that makes no
difference.

## 5. Extra properties for Code-Aster (`#ASTER-SECTIE`)

Code-Aster's `AFFE_CARA_ELEM` (`SECTION='GENERALE'`) has more characteristics than
Mecway's *General section* (EDF R&D, 2021a §9.4.3). The tool writes them into the custom
model definition (*CCX* > *Custom model definition*; CCX reads `**` lines as comments):

```
** ASTER-SECTIE Profile: A=0.0018, IY=5.4e-07, IZ=1.35e-07, JX=..., AY=1.2, AZ=1.2, EY=0, EZ=-0.004, RY=0.03, RZ=0.015, RT=..., JG=..., IYR2=..., IZR2=...
```

All values in SI (m, m², m⁴, m⁶), local y = V (principal axis 1), z = W (principal
axis 2):

| Key | Meaning | Use by the bridge |
|---|---|---|
| `A`, `IY`, `IZ`, `JX` | copy of the *General section* | check: if the material differs (changed in Mecway later), the bridge ignores the line with a WARNING |
| `AY`, `AZ` | shear coefficient A / A' in y and z (rectangle 1.2) | Timoshenko beams only (`POU_D_T`, `POU_D_T_GD`), instead of the estimate or 1.0 |
| `EY`, `EZ` | vector from the shear centre C to the centroid G in y and z (CG, as `MACR_CARA_POUTRE`; checked with Code-Aster 17.4) | every beam (`POU_D_E`, `POU_D_T`, `POU_D_T_GD`): coupling of bending and torsion (EDF R&D, 2019 §5.1) |
| `RY`, `RZ` | largest distance from the centroid in y and z | every beam; stresses only (EDF R&D, 2021a §9.3) |
| `RT` | torsion radius: J · τmax / Mt | every beam; stresses only |
| `JG` | warping constant | stored; only `POU_D_TG`/`POU_D_TGM` use it, which the bridge does not offer |
| `IYR2`, `IZR2` | ∫ z(y² + z²) dA and ∫ y(y² + z²) dA about the centroid (equal to `MACR_CARA_POUTRE`) | stored; only for the geometric stiffness of `POU_D_TG`/`POU_D_TGM` (EDF R&D, 2020) |

- Each *Create general section* adds a *custom model definition* with one line. The
  bridge reads all of them, in order; when a material has several lines, the last one
  counts. You may delete old ones (right-click the item in the tree).
- If you rename the material in Mecway, change the name in the line too (otherwise:
  WARNING "no material with this name").
- The log of a bridge run shows what was taken over:
  `INFO: Material 'Profile': #ASTER-SECTIE adds EY=..., EZ=..., ...`.
- Mecway itself only uses the *General section* and ignores the shear centre (Mecway
  manual §7.5, Mecway Ltd., 2026); for an unsymmetric section the Code-Aster results
  therefore deliberately differ from Mecway's.

## 6. Accuracy and verification

The section is meshed again with quadratic triangles (tri6, about 3000 by default; in
thin walls fine enough for at least three elements across the thickness). Area, centroid,
second moments and section moduli follow exactly from the triangles; torsion, warping and
shear from a finite element analysis (Pilkey, 2002), the same formulation as the Python
package sectionproperties that AreaPropsForAlibre uses. Shear with ν = 0, as
`MACR_CARA_POUTRE` (rectangle: AY = 1.2).

Compared (`tests/test_section_analysis.py`, 23 Oct 2026) with sectionproperties for 13
sections (rectangle, circle, tube, I with and without root fillets, channel, unequal
angle, T, Z, plate with holes, thin box, thin open channel with t = 1/100, two separate
parts) and with `MACR_CARA_POUTRE` of Code-Aster 17.4 on the same mesh (rectangle,
channel, angle, Z):

| Quantity | Largest difference |
|---|---|
| A, centroid, Ixx, Iyy, Ixy, I11, I22, φ, elastic W | ≤ 1e-12 |
| plastic W | ≤ 1e-8 |
| J, Iw, shear areas | ≤ 1.6e-4 (sectionproperties); J ≤ 6.8e-4 (Code-Aster) |
| shear centre | ≤ 6e-6 × size |
| `AY`, `AZ`, `EY`, `EZ`, `JG`, `IYR2`, `IZR2`, `RY`, `RZ` against Code-Aster | ≤ 1e-6 |
| `RT` against Code-Aster | rectangle 4e-5; at re-entrant corners −3% to +17% (the stress is singular there; both depend on the mesh) |

Run time: 0.1–0.5 s for the analysis itself, plus starting Python (a few seconds). The
mesh of the *Mesh faces* route is made from the boundary of the selection, not from the
Mecway elements; a coarse Mecway mesh therefore only affects the shape of curved
boundaries.

## 7. Limitations

- **Flat** sections only: the selected faces must lie in one plane (deviation at most
  1e-5 of the size).
- *Mesh faces*: the boundary is as accurate as the mesh. A circle with linear elements is
  a polygon; quadratic elements follow an arc through the midside node (a coarse arc of
  45° per element misses 0.2% of the area). For curved boundaries prefer *CAD face* or a
  finer mesh.
- *CAD face*: only flat STEP faces with lines, circles, ellipses, polylines and
  (rational) B-splines; no assembly placements (one STEP geometry per component, as
  Mecway reads it).
- Separate parts: no J, Iw, shear centre or shear, and no *General section*.
- The window only works in Mecway with Windows Forms and a Code-Aster installation.

## 8. References

- EDF R&D (2019). *Éléments « exacts » de poutres (droites et courbes)*. Code_Aster
  documentation R3.08.01.
- EDF R&D (2020). *Macro-commande MACR_CARA_POUTRE*. Code_Aster documentation U4.42.02.
- EDF R&D (2021a). *Opérateur AFFE_CARA_ELEM*. Code_Aster documentation U4.42.01.
- Mecway Ltd. (2026). *Mecway manual*, §7.5 Beam, §16.2 Scripts (installed with Mecway
  as `manual.pdf`).
- Pilkey, W. D. (2002). *Analysis and Design of Elastic Beams: Computational Methods*.
  Wiley.
