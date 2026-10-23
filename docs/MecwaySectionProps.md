# MecwaySectionProps: doorsnede-eigenschappen van een vlak in Mecway

*English version: [MecwaySectionProps.md](en/MecwaySectionProps.md)*

MecwaySectionProps berekent de doorsnede-eigenschappen van een vlakke doorsnede die je in
Mecway selecteert: oppervlakte, zwaartepunt, traagheidsmomenten (ook om de hoofdassen),
weerstandsmomenten (elastisch en plastisch), torsieconstante J, welvingsconstante Iw,
dwarskrachtcentrum en afschuifoppervlakken. Met één knop maak je er een Mecway-materiaal
met een *General section* van, en de kenmerken waar Mecway geen veld voor heeft
(afschuifcoëfficiënten, excentriciteit van het dwarskrachtcentrum, welving, ...) bewaart
het in het model, zodat de bridge er in Code-Aster mee rekent zonder schatting achteraf.

Het is de Mecway-versie van AreaPropsForAlibre (hetzelfde venster en dezelfde grootheden),
maar zonder extra Python-pakketten: de berekening draait in de Python die met Code-Aster
wordt meegeleverd (numpy en scipy).

| Wat | Waar |
|---|---|
| tabel met alle grootheden, in mm of m | het venster (knop *Kopiëren*: plakbaar in Excel) |
| tekening: doorsnede, zwaartepunt, x/y-assen, hoofdassen 1 (V) en 2 (W) met hoek φ, dwarskrachtcentrum | het venster, rechts |
| Mecway-materiaal met *General section* (area, Iyy, Izz, torsion constant, perimeter, stress recovery point) | Mecway, na *General section maken* |
| extra Code-Aster-kenmerken (`AY`, `AZ`, `EY`, `EZ`, `RY`, `RZ`, `RT`, `JG`, `IYR2`, `IZR2`) | één `#ASTER-SECTIE`-regel per materiaal in de custom model definition (§5) |
| invoer en resultaat van de laatste berekening | `section_props\section_input.json` en `section_results.json` in de werkmap van de bridge |

## 1. Installeren

1. Installeer de bridge en Code-Aster zoals in [`Handleiding.md`](Handleiding.md) §1.
   MecwaySectionProps gebruikt de Python van Code-Aster
   (`<Code-Aster>\Python311\python.exe`, gevonden via de instelling `exe_aster` van de
   bridge); andere installaties zijn niet nodig.
2. Voeg het script toe aan Mecway: *Tools* > *Scripts...* > *New*, en kies
   `Scripts\MecwaySectionProps.py` (dezelfde map als `MecwayAsterBridgeMain.py`). Het
   script staat daarna als item in het menu *Tools*.

## 2. Gebruik

1. Selecteer in Mecway, in de **vlakselectie** (*Select faces*), de vlakken van de
   doorsnede: bijvoorbeeld de eindvlakken van een geëxtrudeerd profiel of het
   snijvlak van een volume. Alle vlakken moeten in één plat vlak liggen.
2. Start *Tools* > `MecwaySectionProps`. Het venster blijft open naast Mecway: je kunt
   een andere selectie maken en opnieuw op **Berekenen** klikken. Een tweede start van
   het script haalt het open venster naar voren.
3. Kies de invoer:
   - **Mesh-vlakken (selectie)**: de rand van de geselecteerde mesh-vlakken. Randen die
     twee geselecteerde vlakken delen vallen weg; wat overblijft is de buitenrand en de
     rand van gaten. Bij kwadratische elementen (tet10, hex20, ...) volgt de rand de
     parabool door de middenknoop (gebogen randen). Werkt voor elk model, ook zonder
     CAD.
   - **CAD-vlak (exacte STEP-rand)**: alleen voor een component die Mecway uit een
     STEP-geometrie heeft gemesht (*Geometry* in het model). De tool zoekt in het
     STEP-bestand het vlakke CAD-vlak waar de geselecteerde mesh-vlakken op liggen en
     rekent met de **exacte** rand (lijnen, cirkels, ellipsen, B-splines), los van de
     meshfijnheid. Selecteer één of meer mesh-vlakken op het CAD-vlak; het hele CAD-vlak
     telt mee. Meerdere aangrenzende CAD-vlakken in hetzelfde vlak worden samengevoegd.
     Het model moet opgeslagen zijn (de koppeling component → STEP-bestand staat in de
     `.liml`).
4. Klik op **Berekenen**. De berekening (mesh van ±3000 kwadratische driehoeken en de
   eindige-elementenberekening voor torsie en afschuiving) duurt enkele seconden; de
   statusregel telt mee.
5. Lees de tabel en de tekening; *Kopiëren* zet de tabel op het klembord
   (tab-gescheiden, decimaalteken van Windows). *NL*/*EN* rechtsboven wisselt de taal,
   *Eenheid* tussen mm en m.

**Kleine openingen in de rand** worden automatisch gerepareerd, zodat de berekening
toch kan; elke reparatie staat als opmerking onder de tabel:

- *Mesh-vlakken*: knopen op (vrijwel) dezelfde plek (binnen 1e-4 van de afmeting, bijv.
  een geïmporteerd mesh met dubbele knopen) worden één knoop; een rand waar een knoop
  van een ander vlak op ligt (T-aansluiting van een niet-conform mesh) wordt daar
  gesplitst; losse rand-einden worden met een rechte lijn verbonden met het dichtstbijzijnde
  losse einde.
- *CAD-vlak*: randen waarvan de eindpunten niet precies op elkaar aansluiten worden met
  een rechte lijn verbonden.
- Een opening wordt alleen gesloten tot 2 % van de afmeting van de doorsnede; is hij
  groter, dan stopt de berekening met de plaats van de opening. Een echte sleuf (met
  eigen randen) is geen losse rand en blijft dus open.

## 3. Wat het venster toont

**Assen.** De doorsnede wordt bekeken van buiten het volume (zoals AreaPropsForAlibre):
de normaal n wijst uit de elementen, y is de globale Y-as geprojecteerd op het vlak (of
−Z/+Z bij een vlak loodrecht op Y) en x = y × n. De oorsprong is die van het model, dus het
zwaartepunt staat in modelcoördinaten; daaronder ook globaal (X; Y; Z).

| Groep | Grootheden |
|---|---|
| Geometrie | A, omtrek van de buitenrand, zwaartepunt |
| Traagheid | Ixx, Iyy, Ixy om het zwaartepunt; hoofdtraagheden I11 ≥ I22; hoek φ van +x naar hoofdas 1 (tegen de klok in); traagheidsstralen |
| Weerstandsmomenten | elastisch Wx (boven/onder), Wy (rechts/links), W1, W2 (kleinste om de hoofdassen); plastisch Wpl,x, Wpl,y, Wpl,1, Wpl,2 |
| Torsie, welving, afschuiving | J (Saint-Venant), Iw (om het dwarskrachtcentrum), dwarskrachtcentrum (x; y), afschuifoppervlakken As,1 en As,2 (langs de hoofdassen) |
| Mecway General section | de waarden die *General section maken* invult, en de richtingen U, V, W (§4) |
| Code-Aster GENERALE | `AY`, `AZ`, `EY`, `EZ`, `RY`, `RZ`, `RT`, `JG`, `IYR2`, `IZR2` (§5) |

Torsie, welving en afschuiving bestaan alleen voor een samenhangende doorsnede; bestaat
de selectie uit losse delen, dan staat de reden onder de tabel en kan er geen *General
section* van worden gemaakt.

## 4. General section maken

Onderaan het venster:

- **Materiaalnaam**: de naam van het nieuwe Mecway-materiaal (bestaat hij al, dan maakt
  Mecway er `naam(2)` van).
- **Toewijzen aan**: een balkcomponent (line2/line3) die het materiaal krijgt, of geen.
- **E, ν, ρ overnemen**: neemt het isotrope elastische materiaal (E, ν, α) en de
  dichtheid over van het huidige materiaal van die component, zodat alleen de doorsnede
  verandert.
- **Extra Code-Aster-eigenschappen opslaan**: zet de `#ASTER-SECTIE`-regel in het model
  (§5). Daarvoor slaat de tool het model op, past de `.liml` aan en opent hem opnieuw in
  Mecway (er is geen Mecway-API voor dat tekstveld); de undo-geschiedenis van Mecway
  vervalt. Het venster vraagt eerst bevestiging. Het model moet een bestandsnaam hebben.

Het materiaal krijgt een *General section* met:

| Mecway | Waarde |
|---|---|
| Area | A |
| Iyy (om V) | I11 |
| Izz (om W) | I22 |
| Torsion constant | J |
| Perimeter | omtrek van de buitenrand |
| Stress recovery point (V; W) | het randpunt het verst van het zwaartepunt, in hoofdassen |

**Oriëntatie van de balk.** Mecway's *General section* kent alleen hoofdtraagheden; de
balk moet dus zo gedraaid zijn dat zijn V-as langs hoofdas 1 ligt. Geef in Mecway
(*Loads & Constraints* > *Element orientation*, of *Element properties*) als V-vector
de richting uit de tabel (*V-vector (as 1)*). Mecway's U-as loopt langs de balk (knoop
1 → 2) en W = U × V; dat is hetzelfde als x, y, z van Code-Aster.
`EY`, `EZ` (en `IZR2`) gelden voor een balk die in de richting van de normaal n loopt
(*Balkas U = normaal n* in de tabel). Loopt de balk de andere kant op, dan ziet hij de
doorsnede gespiegeld; voor een doorsnede die symmetrisch is om een hoofdas maakt dat
niet uit.

## 5. Extra eigenschappen voor Code-Aster (`#ASTER-SECTIE`)

Code-Aster's `AFFE_CARA_ELEM` (`SECTION='GENERALE'`) kent meer kenmerken dan Mecway's
*General section* (EDF R&D, 2021a §9.4.3). De tool schrijft ze in de custom model
definition (*CCX* > *Custom model definition*; CCX leest `**`-regels als commentaar):

```
** ASTER-SECTIE Profiel: A=0.0018, IY=5.4e-07, IZ=1.35e-07, JX=..., AY=1.2, AZ=1.2, EY=0, EZ=-0.004, RY=0.03, RZ=0.015, RT=..., JG=..., IYR2=..., IZR2=...
```

Alle waarden in SI (m, m², m⁴, m⁶), lokaal y = V (hoofdas 1), z = W (hoofdas 2):

| Sleutel | Betekenis | Gebruik door de bridge |
|---|---|---|
| `A`, `IY`, `IZ`, `JX` | kopie van de *General section* | controle: wijkt het materiaal af (later in Mecway aangepast), dan negeert de bridge de regel met een WARNING |
| `AY`, `AZ` | afschuifcoëfficiënt A / A' in y en z (rechthoek 1,2) | alleen bij Timoshenko-balken (`POU_D_T`, `POU_D_T_GD`), in plaats van de schatting of 1,0 |
| `EY`, `EZ` | vector van het dwarskrachtcentrum C naar het zwaartepunt G in y en z (CG, zoals `MACR_CARA_POUTRE`; nagelopen met Code-Aster 17.4) | elke balk (`POU_D_E`, `POU_D_T`, `POU_D_T_GD`): koppeling van buiging en torsie (EDF R&D, 2019 §5.1) |
| `RY`, `RZ` | grootste afstand tot het zwaartepunt in y en z | elke balk; alleen voor spanningen (EDF R&D, 2021a §9.3) |
| `RT` | torsiestraal: J · τmax / Mt | elke balk; alleen voor spanningen |
| `JG` | welvingsconstante | bewaard; alleen `POU_D_TG`/`POU_D_TGM` gebruiken hem, die de bridge niet aanbiedt |
| `IYR2`, `IZR2` | ∫ z(y² + z²) dA en ∫ y(y² + z²) dA om het zwaartepunt (gelijk aan `MACR_CARA_POUTRE`) | bewaard; alleen voor de geometrische stijfheid van `POU_D_TG`/`POU_D_TGM` (EDF R&D, 2020) |

- Eén regel per materiaal; *General section maken* vervangt een eerdere regel van
  hetzelfde materiaal.
- Hernoem je het materiaal in Mecway, pas dan de naam in de regel aan (anders: WARNING
  "geen materiaal met deze naam").
- De log van een bridge-run toont wat er is overgenomen:
  `INFO: Material 'Profiel': #ASTER-SECTIE adds EY=..., EZ=..., ...`.
- Mecway zelf gebruikt alleen de *General section* en houdt geen rekening met het
  dwarskrachtcentrum (Mecway-handleiding §7.5, Mecway Ltd., 2026); de resultaten van
  Code-Aster wijken bij een asymmetrische doorsnede dus bewust af van Mecway.

## 6. Nauwkeurigheid en verificatie

De doorsnede wordt opnieuw gemesht met kwadratische driehoeken (tri6, standaard ±3000;
in dunne wanden zo fijn dat er minstens drie elementen over de dikte komen). Oppervlakte,
zwaartepunt, traagheden en weerstandsmomenten volgen exact uit de driehoeken; torsie,
welving en afschuiving uit een eindige-elementenberekening (Pilkey, 2002), dezelfde
formulering als het Python-pakket sectionproperties dat AreaPropsForAlibre gebruikt.
Afschuiving met ν = 0, zoals `MACR_CARA_POUTRE` (rechthoek: AY = 1,2).

Vergeleken (`tests/test_section_analysis.py`, 23 okt 2026) met sectionproperties voor
13 doorsneden (rechthoek, cirkel, buis, I met en zonder afrondingen, U, ongelijkzijdige
hoek, T, Z, plaat met gaten, dunne koker, dunne open U met t = 1/100, twee losse delen) en
met `MACR_CARA_POUTRE` van Code-Aster 17.4 op hetzelfde mesh (rechthoek, U, hoek, Z):

| Grootheid | Grootste verschil |
|---|---|
| A, zwaartepunt, Ixx, Iyy, Ixy, I11, I22, φ, elastische W | ≤ 1e-12 |
| plastische W | ≤ 1e-8 |
| J, Iw, afschuifoppervlakken | ≤ 1,6e-4 (sectionproperties); J ≤ 6,8e-4 (Code-Aster) |
| dwarskrachtcentrum | ≤ 6e-6 × afmeting |
| `AY`, `AZ`, `EY`, `EZ`, `JG`, `IYR2`, `IZR2`, `RY`, `RZ` tegen Code-Aster | ≤ 1e-6 |
| `RT` tegen Code-Aster | rechthoek 4e-5; bij inspringende hoeken −3 % tot +17 % (de spanning is daar singulier; beide hangen van het mesh af) |

Rekentijd: 0,1–0,5 s voor de berekening zelf, plus het starten van Python (enkele
seconden). Het mesh van de *Mesh-vlakken*-route komt uit de rand van de selectie, niet uit
de Mecway-elementen; een grof Mecway-mesh beïnvloedt dus alleen de vorm van gebogen randen.

## 7. Beperkingen

- Alleen **vlakke** doorsneden: de geselecteerde vlakken moeten in één vlak liggen
  (afwijking hoogstens 1e-5 van de afmeting).
- *Mesh-vlakken*: de rand is zo nauwkeurig als het mesh. Een cirkel met lineaire
  elementen is een veelhoek; kwadratische elementen volgen een boog via de middenknoop
  (een grove boog van 45° per element mist 0,2 % van de oppervlakte). Gebruik voor
  gebogen randen liever *CAD-vlak* of een fijner mesh.
- *CAD-vlak*: alleen vlakke STEP-vlakken met lijnen, cirkels, ellipsen, polylijnen en
  (rationele) B-splines; geen plaatsingen van assemblies (één STEP-geometrie per
  component, zoals Mecway hem inleest).
- Losse delen: geen J, Iw, dwarskrachtcentrum of afschuiving, en geen *General section*.
- Het venster werkt alleen in Mecway met Windows Forms en een Code-Aster-installatie.

## 8. Bronnen

- EDF R&D (2019). *Éléments « exacts » de poutres (droites et courbes)*. Code_Aster
  documentatie R3.08.01.
- EDF R&D (2020). *Macro-commande MACR_CARA_POUTRE*. Code_Aster documentatie U4.42.02.
- EDF R&D (2021a). *Opérateur AFFE_CARA_ELEM*. Code_Aster documentatie U4.42.01.
- Mecway Ltd. (2026). *Mecway manual*, §7.5 Beam, §16.2 Scripts (met Mecway
  geïnstalleerd als `manual.pdf`).
- Pilkey, W. D. (2002). *Analysis and Design of Elastic Beams: Computational Methods*.
  Wiley.
