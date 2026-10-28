# Bezwijken van elementen

*English version: [Failure.md](en/Failure.md)*

Code-Aster kan geen elementen verwijderen. De bridge gebruikt daarom een
gangbare aanpak voor impliciete berekeningen. Haalt een element de bezwijkgrens,
dan krijgt het een zeer lage stijfheid en gaat zijn spanning naar nul. Het
element blijft in het mesh, maar draagt vanaf dat moment (vrijwel) niets meer. De
belasting verdeelt zich over de rest. Zo werken ook Alomar e.a. (2023), die
elementverwijdering in Code_Aster inbouwden door bezweken elementen te vervangen
door een virtueel materiaal met een zeer lage stijfheid.

In de niet-lineaire analyses: **Niet-lineair statisch** (`STAT_NON_LINE`),
**Dynamisch (impliciet)** en **Dynamisch (expliciet)** (beide `DYNA_NON_LINE`). Niet
in de lineaire en thermische analyses.

## 1. Gebruiken

Geef per Mecway-materiaal een **bezwijkgrens**: de vergelijkingsplastische rek
(equivalent plastic strain) waarbij een element bezwijkt. De bridge kijkt naar het
gemiddelde over de integratiepunten van het element. Drie manieren, de eerste die
bestaat telt:

1. **`#ASTER-BEZWIJKEN`-regel** in Mecway's custom model definition (bij solver CCX:
   *Analysis* > *CCX* > *Custom model definition*; de bridge leest ook de velden van
   OpenRadioss en Mystran, zie [`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md)):

   ```
   ** ASTER-BEZWIJKEN Kerfstaal = 0.05
   ```

   `Kerfstaal` is de Mecway-naam van het materiaal; `*` betekent alle plastische
   materialen zonder eigen regel. `#ASTER-FAILURE` werkt ook.
2. **OpenRadioss `PLAS_TAB`**: de waarde `Eps_p_max` uit de materiaalkaart.
3. **Instelling** *Bezwijkgrens alle plastische mat. (0 = uit)* op de pagina
   *Niet-lineair statisch*, *Dynamisch (impliciet)* of *Dynamisch (expliciet)*: geldt
   voor elk plastisch materiaal zonder eigen grens.

Voorwaarden:
- het materiaal is plastisch: isotroop (hardingscurve, bilineair isotroop,
  Ramberg-Osgood of `PLAS_TAB`) of kinematisch met lineaire versteviging
  (BilinearKinematic of een lineaire kinematische curve) met een *tangent modulus* > 0;
- de elementen zijn **volume-elementen** (hex, tet, wedge, pyr; ook met de
  hex8-keuze `LINE_QUAD`) of **schalen** (tri3/quad4 als DKT; kwadratisch of met
  *Lineaire schalen* = `COQUE_3D` als `COQUE_3D`); **geen balken**;
- het model heeft geen balken met grote rotaties (`elem_beam` = `POU_D_T_GD`): na een
  bezweken element vraagt de volgende stap `RIGI_MECA`, die dat element niet heeft
  (`CALCUL_37`); de bridge stopt vooraf met een ERROR;
- `DEFORMATION`: volumes `PETIT`, `PETIT_REAC` of grote verplaatsingen (`GDEF_LOG`,
  ook `SIMO_MIEHE`); DKT rekent altijd geometrisch lineair (`PETIT`/`GREEN_LAGRANGE`);
  `COQUE_3D` `PETIT` of `GROT_GDEP`.

**Schalen.** De grens geldt voor het gemiddelde over alle integratiepunten, bij
schalen ook over de punten in de dikte. Bij buiging bezwijkt een schaalelement dus
pas als de rek gemiddeld over de dikte de grens haalt (aan het oppervlak is hij
hoger).

**Kinematische versteviging.** Code-Aster houdt bij `VMIS_CINE_LINE` geen opgetelde
plastische rek bij. De bridge rekent de rek uit de terugspanning: X = 2/3·H·εp, met H
de *tangent modulus* van Mecway (de plastische modulus; Code-Aster krijgt
`D_SIGM_EPSI` = Et = E·H/(E+H), dus H = E·Et/(E−Et)). Dat is de huidige plastische rek.
Bij wisselende belasting is die kleiner dan de opgetelde, dus bezwijkt een element
later (WARNING).

Wat niet aan de voorwaarden voldoet, bezwijkt niet. De bridge zet dan een WARNING in
de log en meldt het aan het eind van de run.

## 2. Instellingen (pagina's Niet-lineair statisch, Dynamisch (impliciet) en Dynamisch (expliciet))

| Instelling | Standaard | Betekenis |
|---|---|---|
| Bezwijken van elementen (plastische rek) | aan | uit: bezwijkgrenzen in het model worden genegeerd (WARNING) |
| Bezwijkgrens alle plastische mat. (0 = uit) | 0 | grens voor plastische materialen zonder eigen grens |
| Stijfheid bezweken element (x E) | 1e-6 | de E en de helling na vloeien van een bezweken element, als fractie van het origineel (1e-7 .. 0,1; een waarde daarbuiten wordt begrensd, met een WARNING). De kracht die een bezweken doorsnede nog doorgeeft, schaalt met deze factor (§5) |

Per model kan het ook met `#ASTER-OPTIE`, bijvoorbeeld
`** ASTER-OPTIE failure_stiffness_factor = 1e-4`.

## 3. Wat er gebeurt

**Niet-lineair statisch:** na **elke rekenstap** van de tijdlijst (elk interval tussen
de tijdspunten van de tijdsafhankelijke lasten, of 0 tot de eindtijd, gedeeld in
*Substappen per tijdsinterval*) doet de bridge in de Code-Aster-job het volgende:

1. Per element de gemiddelde plastische rek (`V1` = `EPSPEQ`) uitlezen.
2. Elementen boven de grens krijgen een **slap materiaal**: E en de helling na
   vloeien worden met *Stijfheid bezweken element* vermenigvuldigd. De vloeigrens
   blijft gelijk, zodat het slappe element elastisch blijft.
3. **Spanning naar nul**: de spanningen en interne variabelen van die elementen
   worden nul. Alleen de plastische rek blijft staan, want die bepaalt welke
   elementen bezweken zijn (isotroop; bij kinematische versteviging worden ook de
   terugspanningen nul). Het vrijgekomen deel van de belasting verdeelt zich in
   de volgende stap over de rest van het model.
4. De volgende stap start met een **elastische voorspelling**
   (`NEWTON PREDICTION='ELASTIQUE'`). Code-Aster deelt de stap zo nodig op; de stap
   daarna start weer met de gewone raaklijnvoorspelling (`TANGENTE`).

Een element dat bezweken is, blijft bezweken.

**Dynamisch** controleert de bridge op de **uitvoertijden** (de tijdstappen van
Mecway) in plaats van na elke rekenstap; elke uitvoertijd is ook een rekenstap.
Daartussen rekent Code-Aster gewoon door (impliciet: *Rekenstappen per
Mecway-tijdstap*; expliciet: stappen van ten hoogste *Tijdstap / kritieke tijdstap* ×
de geschatte kritieke tijdstap). Na een
bezwijkmoment gaan ook snelheid en versnelling mee naar de volgende stap. Impliciet
start die stap net als statisch met een elastische voorspelling; expliciet start hij
gewoon (`PREDICTION='TANGENTE'`: Code-Aster staat bij een expliciet schema niets anders
toe).

## 4. Resultaten in Mecway

- Elke bezwijkgebeurtenis staat als WARNING in `<model>_<run-id>_bridge_log.txt`,
  met het tijdstip, de elset en de **Mecway-elementnummers**. Aan het eind van de run
  meldt de bridge in het statusvak van het hoofdvenster hoeveel elementen bezweken zijn.
- Het convergentiescherm toont elke gebeurtenis als melding ("Bezwijken bij t = …").
- In de resultaten zijn bezweken elementen te herkennen aan een spanning van ongeveer
  0 in de elementknoopwaarden, terwijl de plastische rek boven de grens ligt. Bij
  volledige doorbraak gaat de reactiekracht naar ongeveer 0.
- De knoopspanningen (gemiddeld over de elementen rond een knoop) mengen bezweken en
  intacte elementen. Kijk daarom naar elementwaarden of naar de plastische rek.

## 5. Testmodellen

In `TestFiles/`. Alle getallen hieronder komen uit runs met Code-Aster 17.4 en de
standaardinstellingen, tenzij anders vermeld (reactiekracht = som over het trekvlak).

| Model | Wat | Resultaat |
|---|---|---|
| `BezwijkenTrekstaaf.liml` | Trekstaaf 100 × 10 × 10 mm (hex8 5 mm), middenplak 10 mm van `Kerfstaal` (σy = 250 MPa, *tangent modulus* 0,5 GPa) tussen `Staal` (355 MPa, 1 GPa); verplaatsing 0 → 6 mm in 1 s; `** ASTER-BEZWIJKEN Kerfstaal = 0.05` | bij t = 0,6 s bezwijken de 8 kerfelementen (Mecway 10, 11, 30, 31, 50, 51, 70, 71); de reactiekracht zakt van 36,7 kN naar 1,5 à 4 N (grote verplaatsingen; met `PETIT` van 38,3 kN naar 2 à 6 N) |
| `BezwijkenDeelsKerf.liml` | Idem, maar alleen de onderste helft van de middenplak is `Kerfstaal` | bij t = 0,6 en 0,7 s bezwijken 2 + 2 elementen (11, 51 en 10, 50); de kracht valt telkens terug (37,5 → 27,4 kN en 33,2 → 30,0 kN) en loopt daarna weer op door de versteviging van het overgebleven deel |
| `BezwijkenTrekstaafDynamisch.liml` | Dezelfde staaf, dynamisch (Mecway D31): 6 mm in 1 ms, uitvoer elke 0,05 ms. *auto* kiest *Dynamisch (impliciet)* | bij t = 0,55 ms bezwijken de 8 kerfelementen; de reactiekracht valt van 37 kN naar ~1 kN (t = 0,6 ms) en slingert daarna na (tot ±12 kN, gedempt door HHT) |
| `BezwijkenTrekstaafExpliciet.liml` | Idem, maar met een beginsnelheid van 6 m/s op het trekvlak en daar een opgelegde verplaatsing 0 (constante snelheid; een opgelegde verplaatsing 0 → 6 mm zet de bridge in expliciet ook om, met hetzelfde resultaat). Kies *Dynamisch (expliciet)* | bij t = 0,55 ms bezwijken de 8 kerfelementen; de reactiekracht slingert daarna vrijwel ongedempt rond 0 (tot ±37 kN) |

Gebruik: open het model in Mecway, start de bridge en kies de analyse: met *auto*
wordt het voor de eerste drie modellen de juiste (L30 → *Niet-lineair statisch*, D31 →
*Dynamisch (impliciet)*); voor `BezwijkenTrekstaafExpliciet.liml` kies je zelf
*Dynamisch (expliciet)* (D31 wordt bij *auto* altijd impliciet).

Varianten (zelfde modellen, één instelling of materiaal anders):

| Variant | Resultaat |
|---|---|
| hardingscurve (σy, σy + H bij plastische rek 1) i.p.v. bilineair | gelijk aan bilineair (36,7 kN, t = 0,6 s): de *tangent modulus* wordt als plastische modulus H vertaald |
| hex8 als `LINE_QUAD` (hex20) | bezwijken bij t = 0,2 s (29,6 kN → 1 à 5 N): de rek lokaliseert sterker met kwadratische elementen (zie §6, volumetrische locking) |
| algemene grens 0,05 (*Bezwijkgrens alle plastische mat.*) | naast de 8 kerfelementen bezwijken 4 staalelementen direct naast de kerf (12, 32, 52, 72) |
| `DEFORMATION` = `SIMO_MIEHE` | alle vier modellen bezwijken op dezelfde momenten als met `GDEF_LOG` (trekstaaf 36,7 kN → 1,5 à 4 N) |
| `BezwijkenDeelsKerf` met BilinearKinematic | 2 + 2 elementen bij t = 0,6 / 0,7 s (37,5 → 27,2 kN en 32,9 → 29,8 kN); WARNING over de huidige plastische rek |
| `BezwijkenDeelsKerf` met 20 i.p.v. 10 substappen | het tweede paar bezwijkt bij t = 0,65 s i.p.v. 0,7 s (kleinere stap, eerder gezien) |
| *Stijfheid bezweken element* 1e-7 / 1e-4 / 1e-3 (trekstaaf) | restkracht op t = 1 s 0,4 N / 0,39 kN / 3,9 kN (standaard 1e-6: 4 N); alle runs convergeren |
| schaalstrip 100 × 20 × 2 mm (quad4 5 mm, kerf als middenplak), trek 6 mm | DKT: 8 elementen bij t = 0,2 s, 13,0 kN → 1 à 4 N; `COQUE_3D`: 13,8 kN → 1 à 10 N |

Eerder, met dezelfde aanpak getest (niet opnieuw gedraaid): de schaalstrip ook
dynamisch impliciet en expliciet (bezwijken bij 0,15 ms) en DKT-buiging met een kerf
bij de inklemming (2 + 2 elementen, 44 → 22 → 0 N).

## 6. Meldingen en oplossingen

| Melding | Oorzaak | Oplossing in het model |
|---|---|---|
| WARNING over kinematische versteviging en de huidige plastische rek | `VMIS_CINE_LINE` houdt geen opgetelde rek bij; de bridge rekent met de huidige | Verwacht. Bij wisselende belasting: kies isotrope versteviging |
| WARNING `… kinematische versteviging zonder helling na vloeien (tangent modulus 0)` | geen versteviging: de terugspanning blijft 0, dus geen rek te zien | Geef een *tangent modulus* > 0, of kies isotrope versteviging |
| WARNING `… het materiaal is niet plastisch` | grens op een elastisch materiaal | Geef het materiaal plasticiteit, of verwijder de grens |
| WARNING over balken (`POU_D_E`) | Code-Aster kent plasticiteit alleen in multivezelbalken | Modelleer het bezwijkgebied met volume-elementen of schalen |
| ERROR `Bezwijken van elementen (…) werkt niet in een model met balken POU_D_T_GD` | na het eerste bezweken element herstart de lus met `PREDICTION='ELASTIQUE'`, en `POU_D_T_GD` kan `RIGI_MECA` niet (`CALCUL_37`); met `TANGENTE` of `EXTRAPOLE` convergeerde de stap na het bezwijken niet (run, Code-Aster 17.4) | Zet *Bezwijken van elementen* uit, of kies *Balken* = `POU_D_E`/`POU_D_T` |
| WARNING `… DEFORMATION … niet ondersteund` | rekmaat die niet bij het element past (bijv. `PETIT_REAC` op schalen) | Kies `PETIT` of grote verplaatsingen |
| WARNING `Bezwijken van elementen kan de bridge alleen in niet-lineaire analyses` | lineaire analyse (*Statisch*) | Kies *Niet-lineair statisch* of een dynamische analyse |
| WARNING over hex8 met '3D' en plasticiteit | volledig geïntegreerde hex8 "sluit" bij plastisch vloeien (volumetrische locking): de plastische rek komt te laat; in de trekstaaf bezweek de kerf bij t = 0,6 s i.p.v. 0,2 s met `LINE_QUAD` | Kies op de pagina Elementen *Hex8* = `LINE_QUAD`, of gebruik kwadratische elementen in Mecway |
| WARNING over *Stijfheid bezweken element* buiten het bereik (ERROR `#ASTER-OPTIE ...: geen geldige waarde` als het geen getal is) | waarde via `#ASTER-OPTIE` buiten 1e-7 .. 0,1 of geen getal | De bridge gebruikt de grens of de standaard 1e-6; pas de waarde aan |
| Alarm `MECANONLINE4_50` (impliciet dynamisch, na een bezwijkmoment) | Code-Aster raadt een beginspanning bij HHT/NEWMARK af | Verwacht; de bridge geeft de versnelling mee. Controleer het verloop (krachtval, naslingering) op plausibiliteit |
| WARNING `… 'Bezwijken van elementen' staat uit` | instelling uit | Zet de instelling aan |
| ERROR `#ASTER-BEZWIJKEN: materiaal 'X' bestaat niet` | tikfout in de materiaalnaam | Gebruik de naam zoals in Mecway (hoofdletters tellen) |
| ERROR `'#ASTER-BEZWIJKEN …': verwacht 'materiaal = rek'` | regel zonder `=` of met een rek ≤ 0 | Schrijf `** ASTER-BEZWIJKEN Naam = 0.2` |
| `MECANONLINE9_7` (Newton convergeert niet) kort na een bezwijkmoment | te veel elementen tegelijk, of de rest kan de belasting niet dragen | Meer *Substappen per tijdsinterval* (kleinere stappen, dus minder elementen per stap; dynamisch: meer uitvoertijden in Mecway); meer *Max. Newton-iteraties*; *Stijfheid bezweken element* groter (1e-4 … 1e-3; de bezweken doorsnede draagt dan wel meer, in de trekstaaf 0,4 kN resp. 3,9 kN, §5). De resultaten tot de laatst geconvergeerde stap worden geladen |
| `MECANONLINE9_3` (`IntegrationError`) na bezwijken | zeer grote vervorming in slappe elementen (grote verplaatsingen) | Kleinere stappen; *Stijfheid bezweken element* groter; zijn de rekken klein, dan `DEFORMATION = PETIT` |
| Singuliere matrix (`FACTOR_…`, `MECANONLINE9_4`) na bezwijken | een deel van het model hangt alleen nog aan bezweken elementen en ligt nergens anders vast | Houd dat deel vast of stuur met een opgelegde verplaatsing (getest) in plaats van een kracht. Bij een kracht en volledige doorbraak kan de rest de last niet dragen; dat is fysisch bezwijken (verwacht, NIET met een run nagelopen) |

Algemeen:
- **Mesh-afhankelijk.** De grens geldt per element (gemiddelde over de
  integratiepunten). Een fijner mesh of kwadratische elementen lokaliseren sterker
  en bezwijken eerder (zie §5, `LINE_QUAD`). Stem de grens af op een proef of
  referentie met een vergelijkbare elementgrootte.
- **Stapgrootte.** Bezwijken wordt na elke rekenstap gecontroleerd (dynamisch: op elke
  uitvoertijd). In één grote stap kunnen veel elementen tegelijk over de grens gaan;
  kleinere stappen (dynamisch: meer uitvoertijden) geven een geleidelijker verloop.
- **Rekentijd.** Elke rekenstap is een eigen `STAT_NON_LINE`-aanroep (dynamisch: een
  `DYNA_NON_LINE`-aanroep per uitvoertijd), met wat extra tijd per aanroep. De
  resultaten vormen één doorlopend resultaat.

## 7. Aannames

- **Criterium**: de vergelijkingsplastische rek, gemiddeld over alle integratiepunten
  van een element (bij schalen ook over de subpunten in de dikte). Geen
  schadeverloop: een element bezwijkt in één keer en blijft bezweken.
- **Bezweken element**: E en de helling na vloeien × *Stijfheid bezweken element*
  (standaard 1e-6), de vloeigrens ongewijzigd, zodat het slappe element elastisch
  blijft; spanning en interne variabelen nul, behalve de plastische rek (isotroop).
  Ondergrens 1e-7: met 1e-9 werd de matrix in een testrun na het bezwijken singulier
  (`bridge_to_aster._FAILURE_FACTOR_RANGE`).
- **Moment van controleren**: statisch na elke rekenstap, dynamisch op de
  uitvoertijden. Het bezwijken valt dus op het einde van een stap; de grootte van de
  stap bepaalt hoe nauwkeurig het moment is (§5, 20 substappen).
- **Kinematische versteviging**: de huidige plastische rek uit de terugspanning
  (§1), niet de opgetelde.
- **Mesh-afhankelijkheid**: de grens is niet gecorrigeerd voor de elementgrootte
  (geen regularisatie); zie §6.

## 8. Bronnen en onderbouwing

Code-Aster-gedrag (Code-Aster 17.4; catalogus = `code_aster/Behaviours/*.py` in de
installatie):

- Interne variabelen `EPSPEQ`, `INDIPLAS` (`VMIS_ISOT_LINE`/`_TRAC`) en geen `EPSPEQ` bij
  `VMIS_CINE_LINE`: catalogus `vmis_*.py`.
- `VMIS_CINE_LINE`: terugspanning `XCINXX..XCINYZ` (catalogus `vmis_cine_line.py`);
  X = c·εp met c = 2/3·E·Et/(E−Et) = 2/3·H, nagelopen tegen `EPSP_ELGA` (testrun).
- `ECRO_LINE D_SIGM_EPSI` is de helling van de trekkromme in totale rek (EDF R&D,
  U4.43.01); Mecway's *tangent modulus* is de plastische modulus H (headless gemeten
  met CCX, zie [Verificatie.md](Verificatie.md), NL-01).
- `SIMO_MIEHE`: interne variabelen `SM1..SM6` (catalogus `simo_miehe.py`); op nul
  zetten geeft een spanningsloze begintoestand (testrun).
- Schalen: subpunten in de dikte en `CREA_CHAMP ASSE` per subpunt: testruns. Balken:
  `<EXCEPTION>` `POUTRE0_61` (plasticiteit alleen in multivezelbalken).
- Spanning in `V3..V8` (`TXX..TYZ`) bij `GDEF_LOG`: gezien in de `.mess`
  ("Nombre total de variables internes : 8").
- `PREDICTION='ELASTIQUE'` na het bezwijken, een slap materiaal dat elastisch blijft,
  en het op nul zetten van `V3..V8`: gekozen na testruns waarin de andere varianten
  niet convergeerden (zie de kop van `Scripts/bridge_failure.py`).
- Expliciet alleen `PREDICTION='TANGENTE'`: `<EXCEPTION>` `MECANONLINE5_1` met 17.4.
- Impliciet dynamisch: alarm `MECANONLINE4_50` bij een beginspanning; of het meegeven
  van de versnelling de herberekening voorkomt is NIET geverifieerd (het krachtverloop
  in de testrun was plausibel).

Literatuur:

- Alomar, Z., Maccioni, L. & Concli, F. (2023). Development and implementation of
  element deletion algorithm into an open-source software based on the fracture locus
  of materials. *Materials*, 16(1), 187. https://doi.org/10.3390/ma16010187
- EDF R&D (z.j.). *Code_Aster, documentatie versie 17.4*: U4.43.01 (`DEFI_MATERIAU`),
  U4.51.03 (`STAT_NON_LINE`), U4.53.01 (`DYNA_NON_LINE`). https://www.code-aster.org
