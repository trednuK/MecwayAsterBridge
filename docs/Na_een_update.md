# Na een update van Mecway of Code-Aster

De bridge is getest met bepaalde versies van Mecway en Code-Aster. Een nieuwere versie werkt
meestal ook, maar niet altijd. Deze pagina zegt wat de versiewaarschuwing betekent en hoe je een
nieuwe versie controleert.

## 1. De versiewaarschuwing

Bij elke run kijkt de bridge welke versies er draaien:

- **Mecway**: het attribuut `version` van `<liml>` in het opgeslagen model (Mecway 36 schrijft
  `<liml version="36">`).
- **Code-Aster**: vóór de run uit het pad van de launcher (`...\17.4\bin\run_aster.bat`), na de run
  uit de kop van de `.mess` (`Version 17.4.0 ...`). De versie uit de `.mess` telt; het is de versie
  die echt gerekend heeft. Vergeleken wordt alleen major.minor (17.4).

Beide versies staan bovenaan het log van de run (`<model>_<run_id>_bridge_log.txt`), bijvoorbeeld
`INFO: Mecway version 34 (tested).` en `INFO: Code-Aster version 17.4.0 according to .mess (tested).`

Is een versie niet getest, dan komt er een **WARNING** in het log en een melding in het statusvak
aan het eind van de run. De run gaat gewoon door: het is alleen een waarschuwing. Controleer de
resultaten dan extra (vergelijk bijvoorbeeld met Mecway's eigen solver) en voer bij gelegenheid de
controle van §2 uit. Is een versie niet te bepalen (oud model zonder `version`, eigen
Code-Aster-build op een ander pad), dan staat er alleen een INFO-regel in het log.

De geteste versies staan in `Scripts/bridge_utils.py`, buiten `CONFIG_BRIDGE`:

```python
TESTED_MECWAY_VERSIONS = ("33", "34", "36")
TESTED_ASTER_VERSIONS = ("17.4",)
```

## 2. Een nieuwe versie controleren

Nodig: CPython 3 en de repo (zie [`Verificatie.md`](Verificatie.md) §2).

| Nieuwe versie van | Uitvoeren (in `TestFiles/Verificatie`) |
|---|---|
| Code-Aster | `python run_verificatie.py` (ongeveer een uur) en `python code_aster_testcases/run_code_aster_tests.py` (officiële Code-Aster-tests) |
| Mecway | `python run_verificatie.py --mecway-opslaan`: Mecway opent en bewaart eerst elk testmodel, de bridge rekent daarna die door Mecway opgeslagen kopie |

Waar je naar kijkt:

- `resultaten/resultaten.md` (bij `--mecway-opslaan`: `resultaten/mecway/vergelijking.md`):
  **0 NOK en 0 FOUT**. BEKEND mag, als het dezelfde bekende beperkingen zijn als in de basislijn.
- Vergelijk de aantallen per groep met de basislijn in [`Verificatie.md`](Verificatie.md) §3.
- De officiële Code-Aster-tests: alle OK, geen NOOK.

Werk je daarna de documentatie bij (geteste versies, basislijn), draai dan vanuit de hoofdmap
`python TestFiles/Tools/check_docs.py`: het controleert links en ankers, verwijzingen naar
`KNOWN_BUGS.md` en verificatiecases, de standaardwaarden in
[`Standaardinstellingen_en_aannames.md`](Standaardinstellingen_en_aannames.md) en de tooltips
tegen `CONFIG_BRIDGE`, en of de Nederlandse en Engelse pagina's dezelfde opbouw hebben
(`--parity`: ook de getallen per sectie). Verwacht: `0 finding(s)`.

## 3. Wat er typisch breekt

**Mecway**

- Tag- en attribuutnamen in de `.liml` (belastingen, randvoorwaarden, materialen, selecties):
  een nieuwe naam wordt niet herkend en de belasting komt in de lijst "NIET vertaald" aan het
  eind van de run (`bridge_from_liml.py`, `bridge_bcs.py`).
- Het resultaatformaat in `<solution>`: resultaten laden niet of op de verkeerde plek
  (`aster_results_export.py`, `bridge_results_liml.py`).
- Eenheden die Mecway anders schrijft: een WARNING "Eenheid niet herkend" in het log. Andersom,
  een eenheid die Mecway niet meer accepteert: Mecway geeft een melding bij het openen van het
  model (Mecway 36 noemt `N/m³` bij een elastic support een onjuiste eenheid en leest het als `Pa/m`), en met
  `--mecway-opslaan` stopt de testcase.

**Code-Aster**

- Sleutelwoorden in de templates (`Scripts/AsterTemplate_*.comm`) en in de gegenereerde `.comm`:
  een hernoemd of verwijderd sleutelwoord geeft een syntaxfout in de `.mess`.
- De Python-API die de scripts in de job gebruiken: `aster_results_export.py`,
  `aster_spectrum.py`, `aster_acoustic_export.py`, `aster_acoustic_complex.py`, `aster_cyclic.py`,
  `aster_fatigue.py`. Een fout staat in de `.mess` of in `<model>_<run_id>_console.txt`.
- De tekst van de `.mess` die de bridge leest (convergentiescherm en meldingen,
  `bridge_convergence.py`, `bridge_run_aster.py`): andere opmaak geeft een leeg of onvolledig
  convergentiescherm, of een gemiste fout.

**Een nieuwere bridge**

- Een instelling in een ouder `Scripts/bridge_utils.py` die de nieuwe bridge niet meer kent,
  negeert hij; welke instellingen erbij kwamen of verdwenen, staat in `CHANGELOG.md`. Vanaf
  V2026.10: de instelling voor AdvancedToolsHub is weg, `salome_meca_dir` is nieuw (leeg = automatisch zoeken).
- Het celveld van bezweken elementen in de `.vtu`-bestanden (*VTU/PVD-bestanden voor
  ParaView*) heet nu `failed` in plaats van `BEZWEKEN`: pas een bewaarde ParaView-state die
  op `BEZWEKEN` filtert (*Threshold*) aan.
- Vanaf V2026.15 bestaat de resultaatroute `tabel` niet meer: de resultaten gaan altijd via
  de `.liml`. Een bewaard `bridge_utils.py` met `"result_route": "tabel"` geeft een
  WARNING en de run gaat via de `.liml`; haal die regel weg.

## 4. Een andere Code-Aster-versie kiezen

Elke Code-Aster-versie heeft een eigen map met een eigen `run_aster.bat`. Kies op de pagina
**Algemeen** van het startscherm bij *Code-Aster launcher (run_aster.bat)* met *Bladeren...* de
`run_aster.bat` van de gewenste versie, bijvoorbeeld
`%LOCALAPPDATA%\code_aster\v2025\17.4\bin\run_aster.bat`. De verificatie (§2) gebruikt dezelfde
instelling. Terug naar de vorige versie: het oude pad weer kiezen.

## 5. Na een geslaagde controle

Voeg de nieuwe versie toe aan `TESTED_MECWAY_VERSIONS` of `TESTED_ASTER_VERSIONS` in
`Scripts/bridge_utils.py` (met de hand; deze regels staan buiten `CONFIG_BRIDGE`, het startscherm
verandert ze niet) en werk de basislijn in [`Verificatie.md`](Verificatie.md) §3 bij. Daarna geeft
de bridge voor die versie geen waarschuwing meer. Voeg bij een nieuwe Mecway-versie ook een
kolom toe aan de tabel in §6 met wat daarin is nagelopen.

## 6. Mecway-versies / compatibiliteit

De bridge vertakt niet op de Mecway-versie: hij herkent functies aan wat in de `.liml` staat
(een tag of attribuut), of aan wat de scripting-API biedt (`mw.liml_text()` van Mecway 36). Een item dat een Mecway-versie niet schrijft ontbreekt gewoon, en de
bridge gedraagt zich dan als zonder dat item. Stand per onderdeel, met de release waarin het
het laatst is nagelopen:

| Onderdeel | Mecway 33 | Mecway 34 (35 waar genoemd) | Mecway 36 |
|---|---|---|---|
| Vertaling t/m V2026.2 (`.liml` lezen, mesh, belastingen, randvoorwaarden, materialen, analyses, resultaten terug in de `.liml`) | nagelopen (V2026.2) | nagelopen (V2026.4) | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Resultaten in een model met configuraties (V2026.2; Mecway 34 kon het eerdere formaat niet openen) | nagelopen (V2026.2) | nagelopen (V2026.4) | headless nagelopen (36.0.9815, 17 nov 2026: resultaten van LS-20a geopend; opslaan voegt een lege solution toe voor elke configuratie zonder resultaten); in het Mecway-venster (18 nov 2026): LS-20a, na heropenen staan de resultaten onder de juiste configuratie en blijven de andere leeg |
| Wachten op Code-Aster, convergentiescherm, versiecontrole (V2026.2) | nagelopen (V2026.2) | nagelopen (V2026.4) | versiecontrole headless nagelopen (36.0.9815, 17–18 nov 2026); wachten en convergentiescherm nagelopen in het Mecway-venster (18 nov 2026) |
| Balken met grote rotaties `POU_D_T_GD` (V2026.3) | NIET nagelopen | nagelopen (V2026.3) | headless nagelopen (36.0.9815, 17–18 nov 2026; de referenties van Mecway + CCX van NL-82/NL-83 op Mecway 36 opnieuw gemeten: gelijk binnen 1e-4) |
| *Element orientation*-kaarten in Loads & Constraints (V2026.3) | n.v.t. (Mecway 33 heeft die kaart niet) | nagelopen (V2026.3) | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Expliciete `ORIENTATION` `VECT_Y` voor elke balk (V2026.3) | NIET nagelopen | nagelopen (V2026.3) | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Startscherm: statusvak, ontbrekende modelmap, tweede venster (V2026.3) | NIET nagelopen | nagelopen (V2026.3) | deels in het Mecway-venster (18 nov 2026): het startscherm opent, de versieregel zonder WARNING "niet getest", een tweede start geeft de melding dat de bridge bezig is; statusvak en ontbrekende modelmap NIET nagelopen |
| Line3-trusses en -kabels (V2026.4) | NIET nagelopen (niet nagegaan of Mecway 33 ze heeft; geen effect op een model zonder) | nagelopen (V2026.4) | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Hyperelastisch Neo Hooke / Mooney-Rivlin (V2026.4) | NIET nagelopen (niet nagegaan of Mecway 33 ze heeft; geen effect op een model zonder) | nagelopen (V2026.4) | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| `#ASTER-SECTIE` (van MecwaySectionProps, eigen repository) en meerdere custom model definitions | NIET nagelopen (niet nagegaan of Mecway 33 een geïmporteerde custom model definition bewaart) | nagelopen (headless, 23 okt 2026) | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Plastische curve: E is de helling van het eerste segment (V2026.4) | NIET nagelopen (gemeten in Mecway 34 met CCX) | nagelopen (V2026.4) | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Eigenvormen met verplaatsingsgrootte (V2026.4) | NIET nagelopen; Mecway 33's eigen modale oplossing toont geen magnitude, dus één extra item (onschadelijk) | nagelopen (V2026.4) | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Flexible joints: `POU_D_T_GD` en balken met offset (V2026.4) | NIET nagelopen | nagelopen (V2026.4) | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Knoppen in het convergentiescherm, werkmap naast het model, voorbereidingsfouten in het statusvak (V2026.4) | NIET nagelopen | nagelopen (V2026.4) | deels in het Mecway-venster (18 nov 2026): werkmap naast het model (alle runs van de controles); knoppen van het convergentiescherm en voorbereidingsfouten NIET nagelopen |
| Resultaatformules berekend door de bridge, warmteflux per elementknoop (V2026.5) | NIET nagelopen | nagelopen (V2026.5) | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Hoofdspanningen/-rekken en versnelling onder Mecway's namen (V2026.5) | NIET nagelopen | nagelopen (V2026.5) | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Hoofdwaarden van schalen, Green-Lagrange-hoofdrekken en `GLe1` (V2026.6) | NIET nagelopen | nagelopen (headless) | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Rubber op hex8: locking-melding, geen `3D_SI` met `ELAS_HYPER`, kaart *Element type* (V2026.5) | NIET nagelopen | nagelopen (V2026.5) | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Code-Aster-samenvatting als *Saved monitor* (V2026.6, optie `save_monitor_liml`; `<savedmonitor>` in de `.liml`) | NIET nagelopen | formaat headless gemeten (34.0.9772, 28 okt 2026: geschreven door Mecway's eigen solve, behouden bij openen en `save_as`); het item in de boom NIET gecontroleerd in de GUI | formaat headless nagelopen (36.0.9815, 17 nov 2026: blijft bij openen en `save_as`); in het Mecway-venster (18 nov 2026): het item staat in de boom en blijft na opslaan en heropenen; dubbelklikken toont de samenvatting in Mecway's venster *Saved monitor*, zoals bij Mecway's eigen solver (het model is dan zwart, ook bij Mecway's eigen solver) |
| Verlijmd contact volume op volume: alleen de slave-knopen die CCX' `*TIE` koppelt (V2026.6, KNOWN_BUGS 128) | NIET nagelopen | headless nagelopen (Mecway 34 rekent met CCX; Samples/BoltedJoint met verlijmde contacten, LS-07l/m, 28 okt 2026); in de Mecway-GUI nagelopen op 29 okt 2026 (LS-07l) | headless nagelopen (36.0.9815, 17 nov 2026; de referentie van Mecway + CCX van LS-07l/m op Mecway 36 opnieuw gemeten: gelijk) |
| Frictionless/symmetry naast displacement 0 op dezelfde knopen gereduceerd; modaal met alleen verlijmd contact of koppelingen als vrij-vrij (V2026.6, GitHub issue #9) | NIET nagelopen | headless nagelopen (Mecway 34 rekent dezelfde modellen als referentie, 28 okt 2026); een run vanuit Mecway's GUI: NOG NIET | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Balk met welving `POU_D_TG`, instelling `beam_warping` (V2026.6) | NIET nagelopen | nagelopen in de Mecway-GUI (28/29 okt 2026: BU-38, LS-94, LS-95 = Mecway; Mecway schrijft hier niets nieuws in de `.liml`) | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Orthotroop / stijfheidsmatrix / compliantiematrix op volume-elementen met de elementoriëntatie als materiaalassen (V2026.6, S13a) | NIET nagelopen (niet nagegaan of Mecway 33 dezelfde attributen schrijft; geen effect op een model zonder) | headless nagelopen (34.0.9772, 28 okt 2026: OR-01..22 tegen Mecway's eigen oplossing van dezelfde `.liml`; attribuutnamen bevestigd door Mecway's oplossing (σ = C·ε)); nog niet in de Mecway-GUI | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| *Pre-tension section* (`force="true"` / `adjustment="true"`, V2026.6) | NIET nagelopen (Samples/BoltedJoint heeft dezelfde tag; niet nagegaan of Mecway 33 het attribuut `adjustment` schrijft) | headless nagelopen (28 okt 2026: PT-01..05 tegen Mecway's eigen CCX-solve, model opgeslagen door Mecway; dynamische respons PT-06..08 tegen CCX en de variant met een veerelement PT-09/10 tegen de interne solver, S15b, ook identiek via door Mecway opgeslagen modellen); in de Mecway-GUI nagelopen op 29 okt 2026 met de veervariant (PT-09), de prismavariant nog niet | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Static 2D (S20), Static Axisymmetric (SA0), Dynamic Response 2D/Axisymmetric (D20, DA0): `C_PLAN`/`D_PLAN`/`AXIS`, resultaten onder Mecway's namen (S16a, S16b, V2026.6) | NIET nagelopen | headless nagelopen (28 oktober 2026: Mecway's eigen oplossing, `mw.face_nodes`, de velden herkend na openen); een run in de Mecway-GUI moet nog | vertaling en resultaten headless nagelopen (36.0.9815, 17–18 nov 2026); in het Mecway-venster (18 nov 2026): PL-07 rekent zonder fout, waarden als in de regressie (`mw.face_nodes`) |
| Acoustic Resonance 2D (A20): `PHENOMENE='ACOUSTIQUE'`, `PLAN` / `PLAN_ABSO` (S16d, V2026.6) | NIET nagelopen | headless nagelopen (34.0.9772, 28 oktober 2026: Mecway's eigen A20-oplossing van AK-10 … AK-15 en van de orgelpijp-tutorial, bridge-resultaten geopend door Mecway met `solution.node_value`); een run in de Mecway-GUI moet nog | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Thermische spanning in S20/SA0 (S44c) en niet-lineair 2D met `**ASTER-PLANE` op S30/L30-shells (S44a, V2026.13) | NIET nagelopen | NIET nagelopen (gemeten met Mecway 35.0.9802 headless, 13 nov 2026: Mecway's eigen S20/SA0-oplossingen voor PL-20 … PL-28 en S30 voor PL-33; PL-30 … PL-32 en PL-34 … PL-36 tegen gesloten oplossingen en Code-Aster); een resultaat openen in de Mecway-GUI moet nog | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Axisymmetrisch warmtetransport met `**ASTER-PLANE AXIS` in T30/T31 en de thermomechanische keten (T31 met *Thermal stress*) (S44d, V2026.14) | NIET nagelopen | NIET nagelopen (Code-Aster 17.4 tegen gesloten vormen, PL-50 … PL-59; Mecway heeft geen axisymmetrisch thermisch type, dus geen Mecway-referentie; een resultaat openen in de Mecway-GUI moet nog) | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Axisymmetrische schalen: line3-elementen in S30/L30 met `**ASTER-PLANE AXIS` en `**ASTER-SHELL` (`COQUE_AXIS`, S44e, V2026.14; spanningen en snedekrachten per oppervlak) | NIET nagelopen | NIET nagelopen (Code-Aster 17.4 tegen gesloten vormen en ssls114i, PL-60 … PL-68). Mecway 35 (35.0.9802), in het Mecway-venster (17 nov 2026): accepteert een *Pressure* op de zijvlakken van line3 in S30 en tekent de pijlen op het vlak waar de bridge hem laat werken (PL-60); toont verplaatsing, rotatie Z en de reacties op de meridiaanlijn (PL-62); het component, de druk en de symmetrie staan rood in de boom. De spanningen op lijnelementen nog niet gezien in Mecway 35. | headless nagelopen (36.0.9815, 17–18 nov 2026); in het Mecway-venster (17 nov 2026, na de correctie van de drukkant): PL-60 en PL-62 opnieuw gerekend, alle waarden zoals verwacht (doorbuiging, reacties, `vonmises…`, `hoopstress…`, `meridionalstress…`, `momentu`) |
| Traction/druk op het zijvlak van een balk (faceid 1), hydrostatische druk op schaalranden (S17, V2026.6) | NIET geverifieerd | headless geverifieerd (28 oktober 2026: vlakken van een balk met `mw.face_nodes`, traction = T × omtrek en druk = geen last tegen de eigen solver, LS-92; Mecway zet geen hydrostatische druk op schaalranden, LS-93 tegen zijn Pressure-formule); nog niet in de Mecway-GUI | vertaling en resultaten headless nagelopen (36.0.9815, 17–18 nov 2026); in het Mecway-venster (18 nov 2026): LS-92a rekent zonder fout, waarden als in de regressie (`mw.face_nodes`) |
| Imperfectie, stapbewaking `gd_step_limit` en sprongcontrole met balken `POU_D_T_GD` (V2026.7, GitHub issue #10) | NIET nagelopen | NIET nagelopen (Mecway 34 was niet beschikbaar). Code-Aster-runs NK-05 tot NK-10; op Mecway 35 (35.0.9802) nagelopen in de GUI met de kolom van issue #10 (6 nov 2026) | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Vorm van een General section: `** SECTIE-VORM`, *Doorsnede tonen*, *Doorsnede in resultaten* (Handleiding §4.3) | NIET nagelopen | NIET nagelopen (Mecway 34 was niet beschikbaar). Alleen nagelopen op Mecway 35 (35.0.9802): headless, en beide weergaven bekeken in het Mecway-venster (6 nov 2026), ook de vorm die aan het eind van een run in de resultaten komt | in het Mecway-venster (18 nov 2026): LS-97a, de schalen zichtbaar met waarden, geen zwarte; *Hide* haalt ze weg vóór een run |
| Controle van de richting van een General section: `** SECTIE-RICHTING` (Handleiding §4.3) | NIET nagelopen | NIET nagelopen (Mecway 34 was niet beschikbaar). Op Mecway 35 zijn de regel en de oriëntatiekaart geschreven door MecwaySectionProps in een verborgen run, en gelezen door de bridge op een Code-Aster-run buiten Mecway (45 graden gemeld, niets bij de juiste V). Niet gecontroleerd in het Mecway-venster | NIET nagelopen (geen onderdeel van de headless controles) |
| Statusvenster na 10 s een gewoon venster, met taakbalkknop (V2026.8) | NIET nagelopen | NIET nagelopen: gecontroleerd met een nepberekening in Mecway's IronPython, niet op een echte run in Mecway | in het Mecway-venster (18 nov 2026): onder de taakbalkknop van Mecway 36 |
| `FACTOR_57` na `DIAGNOSTIC JOB : OK` in het convergentiescherm, de samenvatting en de statusbox (V2026.8) | NIET nagelopen | NIET nagelopen: gecontroleerd op de `.mess` van een echte run, niet in het Mecway-venster | NIET nagelopen (vraagt het Mecway-venster) |
| WARNING voor een balk zonder welving op een open General section (V2026.8) | NIET nagelopen | NIET nagelopen: offline tests; het verschil tussen `POU_D_E` en `POU_D_TG` is gemeten met Code-Aster 17.4 buiten Mecway | n.v.t. (hangt niet van Mecway af) |
| Selectienamen met spaties (modellen uit Mecway 33) | toegestaan | Mecway 34 vervangt de spaties door `_` bij het openen van zo'n model en verliest dan de verwijzing in een contact (`selectionmaster=""`, gezien 22 oktober 2026); de bridge stopt vóór Code-Aster met een ERROR die dat zegt waar het contact meetelt (niet-lineair statisch en dynamica; bonded contact in elke analyse), elders geeft hij een WARNING (Mecway negeert unilateraal contact daar ook). Kies de contactvlakken opnieuw. De voorbeeldmodellen gebruiken namen zonder spaties. | NIET nagelopen (niet gemeten op Mecway 36) |
| Spanning over balkdoorsneden, S41 (`beamvonmisesmax`, `doorsnedeschuif` ...) (V2026.9) | NIET nagelopen | NIET nagelopen (Mecway 34 was niet beschikbaar). Op Mecway 35 (35.0.9802) nagelopen in het Mecway-venster (10 nov 2026) | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| Hoofdvenster: menu *Doorsnede ▾*, schuifbalk van de navigatie, indeling bij een weergaveschaal van 125 % (V2026.9) | NIET nagelopen | NIET nagelopen (Mecway 34 was niet beschikbaar). Op Mecway 35 (35.0.9802) nagelopen in het Mecway-venster (10 nov 2026) | NIET nagelopen (vraagt het Mecway-venster) |
| Convergentiescherm: uiterlijk van het hoofdvenster, leesbaar bij 125 % (V2026.9) | NIET nagelopen | NIET nagelopen (Mecway 34 was niet beschikbaar). Op Mecway 35 (35.0.9802) nagelopen in het Mecway-venster (10 nov 2026) | in het Mecway-venster (18 nov 2026): leesbaar bij 125 % |
| Spanningen en reacties van `POU_D_TG` uit één elastische stap `STAT_NON_LINE` (V2026.9, KNOWN_BUGS 123) | NIET nagelopen | NIET nagelopen (Mecway 34 was niet beschikbaar). Op Mecway 35 (35.0.9802) nagelopen in het Mecway-venster (10 nov 2026) | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| De Code-Aster-base bewaren met een manifest, `keep_base` (V2026.9) | NIET nagelopen | NIET nagelopen: offline tests; met de instelling uit (standaard) blijven mesh en `.comm` gelijk | n.v.t. (hangt niet van Mecway af) |
| Knoppen *ParaView* en *AsterStudy* in het resultatenscherm en het convergentiescherm, instelling `salome_meca_dir` (V2026.10) | NIET nagelopen | Mecway 35 (35.0.9802): nagelopen in het Mecway-venster (11 nov 2026); ook vanuit een verborgen Mecway gestart (10 nov 2026: ParaView 6.2.1 met een `.pvd`, AsterStudy *Results* met een `.rmed`); vanuit de Python van het convergentiescherm: `.rmed`, `_xfem.rmed`, `_verfijnd.rmed` | in het Mecway-venster (18 nov 2026): beide knoppen in het resultatenscherm openen hun bestand; in het convergentiescherm NIET nagelopen |
| Bezweken elementen verbergen, `hide_failed`; `failed` 1 vanaf de stap na het bezwijken (V2026.11) | NIET nagelopen | Mecway 35 (35.0.9802): nagelopen in het Mecway-venster met `BezwijkenTrekstaaf` (11 nov 2026); bestanden ook offline gecontroleerd en met `BezwijkenTrekstaaf` (Code-Aster 17.4, invoegen onder IronPython 2.7.9) | bestanden headless nagelopen (36.0.9815, 17 nov 2026: `BezwijkenTrekstaaf`, het verwerkte bestand door Mecway 36 geopend); in het Mecway-venster (18 nov 2026): de bezweken elementen zijn weg vanaf de stap na het bezwijken, ook na opslaan in Mecway 36 en heropenen |
| Convergentiescherm op de taakbalk bij de knop van Mecway; lang pad over meerdere regels (V2026.11) | NIET nagelopen | Mecway 35 in Program Files: een testvenster met dezelfde taakbalk-ID stond bij Mecway's knop, en het convergentiescherm zelf na een run (11 nov 2026) | in het Mecway-venster (18 nov 2026): onder de taakbalkknop van Mecway 36; lang pad NIET nagelopen |
| WARNING voor *Fixed support* op een knoopselectie met schaal- of volumeknopen, KNOWN_BUGS 135 (V2026.12) | NIET nagelopen | NIET nagelopen in het Mecway-venster: offline tests; dat Mecway 35 (35.0.9802) zulke knopen vrijlaat, is headless gemeten met Mecway's eigen solver op quad- en hex-knopen (11 nov 2026; vakwerkstaven volgens de handleiding, NIET gemeten); de `.comm` van alle 578 vergelijkbare verificatiecases is gelijk | NIET nagelopen (Mecway's eigen gedrag niet op Mecway 36 opnieuw gemeten) |
| Resultaten na de tijdslimiet van Code-Aster: extra tijd na een `TimeLimitError`, tijdbewaking van de staplussen (V2026.12) | NIET nagelopen | NIET nagelopen in het Mecway-venster: headless gemeten met Code-Aster 17.4 (`StopTest_LongRun`, WE-12, 11 nov 2026); lineair statisch en thermisch sinds S45 fase 1 (headless, FX-04, TH-02a, WE-04b, 13 nov 2026); andere lineaire analyses en de thermische ketens verliezen de resultaten nog (KNOWN_BUGS 137) | n.v.t. (hangt niet van Mecway af) |
| Bezweken elementen verbergen met kern `liml_failed.py` 1.0.5: andere knoopwaarden volgen het origineel, kenmerk `failed_hidden`, steunpunten blijven staan (V2026.12) | NIET nagelopen | NIET nagelopen in het Mecway-venster: offline tests (CPython en IronPython 2.7.9) en de kopietest tegen AdvancedToolsHub; dat Mecway 35 het kenmerk bij opslaan houdt, is buiten de bridge gemeten | headless nagelopen (36.0.9815, 17–18 nov 2026): de markering `failed_hidden` blijft bij opslaan door Mecway 36 |
| WARNING voor een isotroop materiaal zonder elasticiteitsmodulus, KNOWN_BUGS 60 (V2026.13) | NIET nagelopen | NIET nagelopen in het Mecway-venster: offline tests; dat Mecway zo'n materiaal met E = 0 rekent, is headless gezien in een Frequency-model (13 nov 2026) | n.v.t. (hangt niet van Mecway af) |
| Pinned support op meerdere knopen in 2D als gemiddelde verplaatsing, KNOWN_BUGS 134 (V2026.13) | NIET nagelopen | NIET nagelopen in het Mecway-venster: headless gemeten met Mecway 35.0.9802 (17 nov 2026): S20 vlakke spanning (PL-07), vlakke rek en SA0 gelijk aan Mecway's eigen oplossing; D20/DA0 niet gemeten | headless nagelopen (36.0.9815, 17–18 nov 2026) |
| WARNING voor verlijmde schaalvlakken (vlak op vlak, schaal op volume), KNOWN_BUGS 128 (V2026.13) | NIET nagelopen | NIET nagelopen in het Mecway-venster: offline tests; de overlapverbinding van twee verlijmde platen headless gemeten met Code-Aster 17.4 en Mecway's eigen solver tegen een volumemodel met hex20 (13 nov 2026) | n.v.t. (hangt niet van Mecway af) |
| WARNING voor lineaire knik met DKT/DST-schalen, met `COQUE_3D` als advies, KNOWN_BUGS 132 (V2026.13) | NIET nagelopen | NIET nagelopen in het Mecway-venster: offline tests; de T-ligger van BU-43c headless gemeten met Code-Aster 17.4 (DKT en `COQUE_3D`) en Mecway's eigen solver op hetzelfde net (13 nov 2026) | n.v.t. (hangt niet van Mecway af) |
| Standaard `lin_solver_resi` 1e-5 in plaats van 1e-6 in lineair statisch, niet-lineair statisch, modaal en knik, KNOWN_BUGS 138, gevonden en opgelost in deze release (V2026.13) | NIET nagelopen | NIET nagelopen in het Mecway-venster: headless gemeten met Code-Aster 17.4 (plaat 160 x 32 quad4 en overlapverbinding hex20 rekenen, de overlap is gelijk aan Mecway; plaat 40 x 8 bitgelijk aan 1e-6, 13 nov 2026); de 293 verificatiecases waarvan de `.comm` verandert plus de snelste van elke groep: geen statuswijziging | n.v.t. (hangt niet van Mecway af) |
| Contact in 2D en axisymmetrisch met `**ASTER-PLANE` (randen van vlakke elementen, ook wrijving), WARNING voor KNOWN_BUGS 141 (S44b, V2026.13) | NIET nagelopen | NIET nagelopen in het Mecway-venster: headless gemeten met Code-Aster 17.4 (PL-40 … PL-46 tegen Lamé, Hertz, Coulomb en de Code-Aster-test ssnp121a); Mecway 35 (35.0.9802), in het Mecway-venster (17 nov 2026): PL-40 opent zonder melding na de correctie van de voorbeeldmodellen (V2026.14); de analyse, de componenten en het contact staan rood in de boom; het resultaat toont de strook plat in 3D met de spanningstensor onder Mecway's namen. | headless nagelopen (36.0.9815, 17–18 nov 2026); in het Mecway-venster (17 nov 2026): PL-47 toont `radialstress`, `axialstress`, `hoopstress`, `shearstressrz` en de contactdruk (als *contact stress pressure*) met de waarden van [`2D_en_axisymmetrisch.md`](2D_en_axisymmetrisch.md) §1.5 voorbeeld 8 (V2026.14) |
| Resultaten na de tijdslimiet van Code-Aster in lineair statisch en thermisch: extra tijd na de solve, `MECA_STATIQUE` met `OPTION='SANS'` (S45 fase 1, V2026.13) | NIET nagelopen | NIET nagelopen in het Mecway-venster: headless gemeten met Code-Aster 17.4 (FX-04, TH-02a, WE-04b met een vertraging voorbij de limiet, resultaten bitgelijk; 291 verificatiecases waarvan de `.comm` verandert: geen statuswijziging) | n.v.t. (hangt niet van Mecway af) |
| Totale harmonische spanningen met hysteretische demping, E(1 + iη)ε per materiaal, KNOWN_BUGS 120 (V2026.14; V2026.13 gaf alleen een WARNING) | NIET nagelopen | NIET nagelopen in het Mecway-venster: headless gemeten met Code-Aster 17.4 (HR-06e … HR-06g, staaf op trek, `PHYS` en `GENE`, twee materialen in serie) | n.v.t. (hangt niet van Mecway af) |
| WARNING voor lineaire knik met een excentrische algemene doorsnede (`ASTER-SECTIE` met afschuifmiddelpunt naast het zwaartepunt), KNOWN_BUGS 115 (V2026.13) | NIET nagelopen | NIET nagelopen in het Mecway-venster: offline tests; de knikfactor van zo'n doorsnede is niet gemeten | n.v.t. (hangt niet van Mecway af) |
| Bezwijken van elementen (`#ASTER-BEZWIJKEN`) in 2D en axisymmetrisch met `**ASTER-PLANE` in L30, WARNING voor KNOWN_BUGS 144 (V2026.14) | NIET nagelopen | NIET nagelopen in het Mecway-venster: headless gemeten met Code-Aster 17.4 (PL-70 … PL-74 tegen gesloten oplossingen) | NIET nagelopen in het Mecway-venster (headless runs hangen niet af van de Mecway-versie) |
| De thermomechanische keten (T31 met *Thermal stress*) met `**ASTER-PLANE C_PLAN` of `D_PLAN`, en met plasticiteit in `AXIS` (V2026.14) | NIET nagelopen | NIET nagelopen in het Mecway-venster: headless gemeten met Code-Aster 17.4 (PL-75 … PL-80 tegen gesloten oplossingen) | NIET nagelopen in het Mecway-venster (headless runs hangen niet af van de Mecway-versie) |
| Gaps met een eigen U-as (*Element orientation*-kaart), geen zijdelingse stijfheid van een gesloten gap, KNOWN_BUGS 23 (V2026.14) | NIET nagelopen | Mecway 35 (35.0.9802) headless: NL-92e … NL-92l gelijk aan Mecway's eigen oplossing; NL-92m tegen de handberekening | NIET nagelopen (Mecway's eigen gap niet op Mecway 36 opnieuw gemeten) |
| Het model als tekst via `mw.liml_text()`: een run en *Doorsnede tonen* lezen een kopie van het open model; het model wordt pas opgeslagen als de resultaten (of de Saved monitor) erin gaan (V2026.15) | n.v.t. (geen `mw.liml_text()`: het model wordt opgeslagen zoals eerder) | n.v.t. (geen `mw.liml_text()`: het model wordt opgeslagen zoals eerder) | headless nagelopen (36.0.9815, 18 nov 2026: de toenmalige route `tabel` en *Doorsnede tonen* in een verborgen Mecway, het modelbestand ongewijzigd, dezelfde `.comm`, hetzelfde mesh en dezelfde vermoeiingsuitkomst als met opslaan; 19 nov 2026: een run op VM-01a en LS-20a, dezelfde resultaten en hetzelfde modelbestand als met opslaan vooraf, een mislukte run laat het bestand ongewijzigd); nagelopen in het Mecway-venster (36.0.9815, 19 nov 2026, bridge a434d50: een niet-opgeslagen wijziging in VM-01a wordt één keer opgeslagen, vlak voor de resultaten, de kopie is weg; een mislukte run laat bestand en wijziging zoals ze waren met *Samenvatting ook als Saved monitor in de .liml* uit, en slaat op met de monitor aan; LS-20a met drie configuraties, het statusvenster modaal, *Resultaten...* > *Inladen*; een alleen-lezen model stopt vóór Code-Aster; een nooit opgeslagen model stopt met een melding; *Doorsnede tonen* slaat niets op; *Resultaten...* > *Uit model verwijderen* en *Inladen*; geen routekeuze op het startscherm en de WARNING voor een bewaarde regel `result_route`). Na een run die het bestand liet zoals het was, vraagt Mecway "Save changes?" als een ander model wordt geopend: dat doet Mecway na elk script, ook na een script dat niets verandert (36.0.9815, 19 nov 2026, een script `x = 1`; handleiding §2) |
| Contact (V2026.15): contactmethode `auto` (ook impliciete dynamica), D31 *Time step size*, `SEUIL_INIT` bij wrijving, dubbele opleggingen op verlijmde slave-knopen (KNOWN_BUGS 147), `bonded_close_gap`, star plakken bij wrijving (KNOWN_BUGS 149) | NIET nagelopen | NIET nagelopen | headless nagelopen (36.0.9815, 18-19 nov 2026: NL-03g/h/i/j/k/l/m en LS-07n/p/q tegen de eigen CCX-solve van Mecway 36, LS-07o tegen de Mecway 34-referentie van LS-07m); nagelopen in het Mecway-venster (36.0.9815, 19 nov 2026, bridge a434d50: NL-03g met `auto` = penalty, w 1,952e-6 m; de controles van `#ASTER-ZONE`/`#ASTER-BONDED`; NL-03h met de kt-WARNING, `SEUIL_INIT` en 10 stappen; LS-07n zonder `FACTOR_11`; spleet-WARNING en `bonded_close_gap` op LS-07 met een spleet van 1,5 mm en 0,2 mm; de WARNING voor een CCX-keyword, en geen als het item onderdrukt is; PipeClip met het advies RELA_OF_MAXI en AssemblyWithContact *Friction* die afloopt) |
| Lasttabellen in niet-lineair statisch zonder *Quasi-static* (tot t = 1 s) en met CCX-*time points* zonder *Automatic time stepping* (tot de periode) (V2026.15) | NIET geverifieerd | temperatuurtabel op t = 1 s geverifieerd (Mecway 34 met CCX, NL-75); de rest NIET geverifieerd | headless geverifieerd (36.0.9815, 19 nov 2026: kracht-, verplaatsings- en temperatuurtabellen, NL-75b..f; alleen de eindtoestand bij time points, NL-75e..g) |

"Nagelopen" betekent de verificatie van §2 en een run in Mecway met die versie. Vergelijkingen
met Mecway's eigen solver in de andere documenten noemen de Mecway-versie waarmee ze gemeten
zijn; dat is de versie van de referentie, geen beperking van de bridge.

*Headless nagelopen* in de kolom Mecway 36: de verificatie van §2 met die versie en de
controles hieronder, zonder het Mecway-venster. Mecway 36 staat op die grond in
`TESTED_MECWAY_VERSIONS` (§5).

Mecway 36 (36.0.9815, een release candidate) is op 17 en 18 november 2026 headless
nagelopen, met Code-Aster 17.4:

- de verificatie van §2 op bridge d9780c5: 631 testcases, 3267 controles, 3261 OK, 6 BEKEND,
  0 NOK/FOUT; met `--mecway-opslaan` op door Mecway 36 opgeslagen modellen 3262 controles
  identiek aan de gewone run, 1 alleen anders in de afronding (LS-97c), en LS-20e niet
  mogelijk (een bewust inconsistent model; [`Verificatie.md`](Verificatie.md) §1). Deze run is
  niet de stand van [`Verificatie.md`](Verificatie.md) §3, die bij de release uit één revisie
  komt;
- op bridge 4cdb284 (V2026.14 in ontwikkeling, na de wijzigingen aan gaps, 2D-resultaten en
  axisymmetrische schalen): met `--mecway-opslaan` 122 testcases: die welke de wijzigingen raken
  (`TestFiles/Tools/regression_scope.py`), alle PL-cases en de snelste case van elke groep; alle
  controles identiek aan de gewone run, of OK waar de gewone run nog geen waarde heeft (PL-47);
- de referenties die uit Mecway kwamen (eigen solver en CCX), opnieuw gemeten met Mecway 36:
  557 van de 589 vergelijkbare controles kloppen binnen 1e-4 relatief; de rest komt van een
  ander referentiemodel of van afronding van de vastgelegde waarde;
- Mecway 36 met CCX geeft een balk terug als de volume-elementen waarin CCX hem uitzet (hex8
  bij line2, hex20 bij line3), met eigen knoopnummers: per knoop van de balk 4 of 8 knopen
  rond de doorsnede. Hun gemiddelde is de verplaatsing van de balkknoop; zo gemeten geven
  NL-82, NL-83 en LS-50 de referenties van Mecway 34 met CCX terug binnen 1e-4. Alleen
  verplaatsingen zijn vergeleken; rotaties, balkkrachten en schalen met CCX zijn op Mecway 36
  NIET nagelopen; CCX op volume-elementen is ongewijzigd;
- resultaten van de bridge geopend door Mecway 36 (`node_value`, `element_node_value`): 4826
  waarden gelijk aan wat de bridge schreef; opslaan in Mecway 36 houdt de Saved monitor en
  `failed_hidden`, laat de lege staarten `<nodes />`/`<values />` vallen (zoals Mecway 35)
  en voegt een lege oplossing toe voor elke configuratie zonder resultaten;
- de bridge start in Mecway 36 (`mw.version()` geeft 36) en vertaalt `Voorbeeld_A.liml`
  (lineair en niet-lineair statisch).

In het Mecway 36-venster: PL-47, PL-60 en PL-62 (17 november 2026), en tien controles
(18 november 2026, bridge d86a39b): het startscherm met de versieregel en een tweede start; lineair statisch met
route `liml` (`Voorbeeld_A.liml` met de regels van voorbeeld 1 van
[`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md); contour per element zonder
zwarte vlakken); configuraties (LS-20a); de Saved monitor; bezweken elementen verbergen
(`BezwijkenTrekstaaf`); de doorsnede tonen en verbergen (LS-97a); het statusvenster en het
convergentiescherm; de knoppen ParaView en AsterStudy; `mw.face_nodes` (PL-07, LS-92a); route
`tabel` (een uitkragende balk, tipverplaatsing −35,3 mm; die route bestaat sinds V2026.15 niet meer). Alle tien zoals verwacht (zie de tabel, waar een rij bestaat). De
versiecontrole vergelijkt alleen het hoofdnummer, dus 36 dekt ook de definitieve build van
Mecway 36: draai §2 met `--mecway-opslaan` opnieuw op die build.
