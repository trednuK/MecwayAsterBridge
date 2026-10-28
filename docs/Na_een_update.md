# Na een update van Mecway of Code-Aster

De bridge is getest met bepaalde versies van Mecway en Code-Aster. Een nieuwere versie werkt
meestal ook, maar niet altijd. Deze pagina zegt wat de versiewaarschuwing betekent en hoe je een
nieuwe versie controleert.

## 1. De versiewaarschuwing

Bij elke run kijkt de bridge welke versies er draaien:

- **Mecway**: het attribuut `version` van `<liml>` in het opgeslagen model (Mecway 34 schrijft
  `<liml version="34">`).
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
TESTED_MECWAY_VERSIONS = ("33", "34")
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
- Eenheden die Mecway anders schrijft: een WARNING "Eenheid niet herkend" in het log.

**Code-Aster**

- Sleutelwoorden in de templates (`Scripts/AsterTemplate_*.comm`) en in de gegenereerde `.comm`:
  een hernoemd of verwijderd sleutelwoord geeft een syntaxfout in de `.mess`.
- De Python-API die de scripts in de job gebruiken: `aster_results_export.py`,
  `aster_spectrum.py`, `aster_acoustic_export.py`, `aster_acoustic_complex.py`, `aster_cyclic.py`,
  `aster_fatigue.py`. Een fout staat in de `.mess` of in `<model>_<run_id>_console.txt`.
- De tekst van de `.mess` die de bridge leest (convergentiescherm en meldingen,
  `bridge_convergence.py`, `bridge_run_aster.py`): andere opmaak geeft een leeg of onvolledig
  convergentiescherm, of een gemiste fout.

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
(een tag of attribuut). Een item dat een Mecway-versie niet schrijft ontbreekt gewoon, en de
bridge gedraagt zich dan als zonder dat item. Stand per onderdeel, met de release waarin het
het laatst is nagelopen:

| Onderdeel | Mecway 33 | Mecway 34 |
|---|---|---|
| Vertaling t/m V2026.2 (`.liml` lezen, mesh, belastingen, randvoorwaarden, materialen, analyses, resultaten terug in de `.liml`) | nagelopen (V2026.2) | nagelopen (V2026.4) |
| Resultaten in een model met configuraties (V2026.2; Mecway 34 kon het eerdere formaat niet openen) | nagelopen (V2026.2) | nagelopen (V2026.4) |
| Wachten op Code-Aster, convergentiescherm, versiecontrole (V2026.2) | nagelopen (V2026.2) | nagelopen (V2026.4) |
| Balken met grote rotaties `POU_D_T_GD` (V2026.3) | NIET nagelopen | nagelopen (V2026.3) |
| *Element orientation*-kaarten in Loads & Constraints (V2026.3) | n.v.t. (Mecway 33 heeft die kaart niet) | nagelopen (V2026.3) |
| Expliciete `ORIENTATION` `VECT_Y` voor elke balk (V2026.3) | NIET nagelopen | nagelopen (V2026.3) |
| Startscherm: statusvak, ontbrekende modelmap, tweede venster (V2026.3) | NIET nagelopen | nagelopen (V2026.3) |
| Line3-trusses en -kabels (V2026.4) | NIET nagelopen (niet nagegaan of Mecway 33 ze heeft; geen effect op een model zonder) | nagelopen (V2026.4) |
| Hyperelastisch Neo Hooke / Mooney-Rivlin (V2026.4) | NIET nagelopen (niet nagegaan of Mecway 33 ze heeft; geen effect op een model zonder) | nagelopen (V2026.4) |
| `#ASTER-SECTIE` (van MecwaySectionProps, eigen repository) en meerdere custom model definitions | NIET nagelopen (niet nagegaan of Mecway 33 een geïmporteerde custom model definition bewaart) | nagelopen (headless, 23 okt 2026) |
| Plastische curve: E is de helling van het eerste segment (V2026.4) | NIET nagelopen (gemeten in Mecway 34 met CCX) | nagelopen (V2026.4) |
| Eigenvormen met verplaatsingsgrootte (V2026.4) | NIET nagelopen; Mecway 33's eigen modale oplossing toont geen magnitude, dus één extra item (onschadelijk) | nagelopen (V2026.4) |
| Flexible joints: `POU_D_T_GD` en balken met offset (V2026.4) | NIET nagelopen | nagelopen (V2026.4) |
| Knoppen in het convergentiescherm, werkmap naast het model, voorbereidingsfouten in het statusvak (V2026.4) | NIET nagelopen | nagelopen (V2026.4) |
| Resultaatformules berekend door de bridge, warmteflux per elementknoop (V2026.5) | NIET nagelopen | nagelopen (V2026.5) |
| Hoofdspanningen/-rekken en versnelling onder Mecway's namen (V2026.5) | NIET nagelopen | nagelopen (V2026.5) |
| Hoofdwaarden van schalen, Green-Lagrange-hoofdrekken en `GLe1` (niet uitgebracht) | NIET nagelopen | nagelopen (headless) |
| Rubber op hex8: locking-melding, geen `3D_SI` met `ELAS_HYPER`, kaart *Element type* (V2026.5) | NIET nagelopen | nagelopen (V2026.5) |
| Code-Aster-samenvatting als *Saved monitor* (Unreleased, optie `save_monitor_liml`; `<savedmonitor>` in de `.liml`) | NIET nagelopen | formaat headless gemeten (34.0.9772, 28 okt 2026: geschreven door Mecway's eigen solve, behouden bij openen en `save_as`); het item in de boom NIET gecontroleerd in de GUI |
| Frictionless/symmetry naast displacement 0 op dezelfde knopen gereduceerd; modaal met alleen verlijmd contact of koppelingen als vrij-vrij (Unreleased, GitHub issue #9) | NIET nagelopen | headless nagelopen (Mecway 34 rekent dezelfde modellen als referentie, 28 okt 2026); een run vanuit Mecway's GUI: NOG NIET |
| Balk met welving `POU_D_TG`, instelling `beam_warping` (nog niet uitgebracht) | NIET nagelopen | NIET nagelopen in de Mecway-GUI (alleen verificatie via de bridge, 28 okt 2026; Mecway schrijft hier niets nieuws in de `.liml`) |
| Orthotroop / stijfheidsmatrix / compliantiematrix op volume-elementen met de elementoriëntatie als materiaalassen (nog niet uitgebracht, S13a) | NIET nagelopen (niet nagegaan of Mecway 33 dezelfde attributen schrijft; geen effect op een model zonder) | headless nagelopen (34.0.9772, 28 okt 2026: OR-01..11 tegen Mecway's eigen oplossing van dezelfde `.liml`; attribuutnamen uit `mecway.exe`); nog niet in de Mecway-GUI |
| *Pre-tension section* (`force="true"` / `adjustment="true"`, nog niet uitgebracht) | NIET nagelopen (Samples/BoltedJoint heeft dezelfde tag; niet nagegaan of Mecway 33 het attribuut `adjustment` schrijft) | headless nagelopen (28 okt 2026: PT-01..05 tegen Mecway's eigen CCX-solve, model opgeslagen door Mecway; dynamische respons PT-06..08 tegen CCX en de variant met een veerelement PT-09/10 tegen de interne solver, S15b, ook identiek via door Mecway opgeslagen modellen); nog niet in de Mecway-GUI |
| Static 2D (S20), Static Axisymmetric (SA0), Dynamic Response 2D/Axisymmetric (D20, DA0): `C_PLAN`/`D_PLAN`/`AXIS`, resultaten onder Mecway's namen (S16a, S16b, nog niet uitgebracht) | NIET nagelopen | headless nagelopen (28 oktober 2026: Mecway's eigen oplossing, `mw.face_nodes`, de velden herkend na openen); een run in de Mecway-GUI moet nog |
| Acoustic Resonance 2D (A20): `PHENOMENE='ACOUSTIQUE'`, `PLAN` / `PLAN_ABSO` (S16d, nog niet uitgebracht) | NIET nagelopen | headless nagelopen (34.0.9772, 28 oktober 2026: Mecway's eigen A20-oplossing van AK-10 … AK-15 en van de orgelpijp-tutorial, bridge-resultaten geopend door Mecway met `solution.node_value`); een run in de Mecway-GUI moet nog |
| Selectienamen met spaties (modellen uit Mecway 33) | toegestaan | Mecway 34 vervangt de spaties door `_` bij het openen van zo'n model en verliest dan de verwijzing in een contact (`selectionmaster=""`, gezien 22 oktober 2026); de bridge stopt vóór Code-Aster met een ERROR die dat zegt waar het contact meetelt (niet-lineair statisch en dynamica; bonded contact in elke analyse), elders geeft hij een WARNING (Mecway negeert unilateraal contact daar ook). Kies de contactvlakken opnieuw. De voorbeeldmodellen gebruiken namen zonder spaties. |

"Nagelopen" betekent de verificatie van §2 en een run in Mecway met die versie. Vergelijkingen
met Mecway's eigen solver in de andere documenten noemen de Mecway-versie waarmee ze gemeten
zijn; dat is de versie van de referentie, geen beperking van de bridge.
