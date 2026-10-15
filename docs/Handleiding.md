# Handleiding MecwayAsterBridge

*English version: [UserGuide.md](en/UserGuide.md)*

De bridge rekent een Mecway-model door met Code-Aster 17.4 en zet de resultaten terug in
Mecway. Je bouwt het model in Mecway (mesh, materialen, belastingen, selecties) en
start de bridge als script; de bridge vertaalt de `.liml` naar een Code-Aster-mesh
en een `.comm`, start Code-Aster en laadt de resultaten.

Verwante documenten:

| Onderwerp | Document |
|---|---|
| Installatie (Code-Aster, scripts, menu-item) | [`README.md`](../README.md) |
| Welke Mecway-functionaliteit wel en niet vertaald wordt (Ja/Deels/Nee per onderdeel) | [`Mecway_functionaliteit.md`](Mecway_functionaliteit.md) |
| Standaardinstellingen en aannames (waarom elke standaardwaarde) | [`Standaardinstellingen_en_aannames.md`](Standaardinstellingen_en_aannames.md) |
| Instellingen voor contact en niet-lineaire analyses, convergentiescherm | [`Instellingen_contact_en_nietlineair.md`](Instellingen_contact_en_nietlineair.md) |
| Thermische analyses | [`Thermisch.md`](Thermisch.md) |
| Lassen: bewegende warmtebron (lasrups, transient thermisch), restspanning, vervorming en metallurgie (fasen, hardheid) | [`Lassen.md`](Lassen.md) |
| Modale analyse (ook cyclische symmetrie), lineaire en niet-lineaire knik (CRIT_STAB, imperfectie) | [`Modaal_en_knik.md`](Modaal_en_knik.md) |
| Respons op modale basis (Dynamic Response met Mode superposition) en harmonische respons per frequentie (`harmonic_3d`) | [`Respons_op_modale_basis.md`](Respons_op_modale_basis.md) |
| Akoestiek: holtemodes en harmonisch drukveld met bron, absorberende randen en microfoons (Acoustic Resonance 3D); vibro-akoestiek: gekoppelde modes van constructie + lucht/vloeistof (Frequency met een fluïdum-onderdeel) en hun respons per frequentie (bron, absorberende randen, microfoons) | [`Akoestiek.md`](Akoestiek.md) |
| Responsspectrum (aardbeving, schok) | [`Spectrumanalyse.md`](Spectrumanalyse.md) |
| Foutschatter: discretisatiefout per element (lineair statisch) | [`Foutschatter.md`](Foutschatter.md) |
| Breukmechanica: K en G langs een gemeshte scheur (lineair statisch, `SCHEUR_`-selecties) of een XFEM-scheur zonder mesh (`#ASTER-XFEM`, §7) | [`Breukmechanica.md`](Breukmechanica.md) |
| Adaptieve verfijning: de mesh in Mecway verfijnen waar de fout groot is (lineair statisch) | [`Foutschatter.md`](Foutschatter.md) §6 |
| Bezwijken van elementen | [`Bezwijken.md`](Bezwijken.md) |
| Vermoeiing: schade en levensduur per knoop (Wöhler-curve, rainflow, Miner, kritiekvlakcriteria, Manson-Coffin; `#ASTER-WOHLER`) | [`Vermoeiing.md`](Vermoeiing.md) |
| Eigen Code-Aster-invoer (`#ASTER`-regels) | [`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md) |
| Meldingen van Code-Aster, oorzaak en oplossing | [`Foutmeldingen_CodeAster.md`](Foutmeldingen_CodeAster.md) |
| Verificatie tegen analytische oplossingen | [`Verificatie.md`](Verificatie.md) |
| Na een update van Mecway of Code-Aster: versiewaarschuwing, nieuwe versie controleren | [`Na_een_update.md`](Na_een_update.md) |
| Bekende afwijkingen en beperkingen (ontwikkelbestand, Nederlands) | [`KNOWN_BUGS.md`](../KNOWN_BUGS.md) |

## 1. Benodigd

- **Mecway 33.** De bridge draait in Mecway's IronPython 2.7-scriptomgeving
  (Mecway Ltd., 2026, §16.2) en is getest met `.liml`-bestanden van versie 33. Andere
  versies zijn niet getest (aanname: het `.liml`-formaat is gelijk).
- **Code-Aster 17.4 voor Windows**; het pad naar `run_aster.bat` staat in
  `CONFIG_BRIDGE["exe_aster"]` (`Scripts/bridge_utils.py`; standaard
  `%LOCALAPPDATA%\code_aster\v2025\17.4\bin\run_aster.bat`, de plek van het
  Windows-pakket) en is in te stellen in het hoofdvenster. Installatie: zie [`README.md`](../README.md).
- De map `Scripts/` van deze repository op een vaste plek. Mecway draait
  `Scripts/MecwayAsterBridgeMain.py`; Code-Aster laadt tijdens de run
  `Scripts/aster_results_export.py` vanaf die plek. Ook de `.comm`-templates
  (`AsterTemplate_*.comm`) staan in `Scripts/`; ze hoeven niet ingesteld te worden.
- Een werkmap met een kort pad: werkmap plus bestandsnaam mogen samen niet langer zijn
  dan 259 tekens (Windows). Is het pad te lang, dan kort de bridge de modelnaam in de
  bestandsnamen in (WARNING); past het ook dan niet, dan start Code-Aster niet.

## 2. Werkwijze

1. Bouw het model in Mecway. Ondersteunde analysetypen: statisch 3D, niet-lineair
   statisch 3D, dynamisch 3D (lineair, ook met mode superposition, en niet-lineair),
   thermisch stationair en transient, frequentie (modaal), knik en akoestische holtemodes (§4; modaal en knik:
   [`Modaal_en_knik.md`](Modaal_en_knik.md); mode superposition:
   [`Respons_op_modale_basis.md`](Respons_op_modale_basis.md); akoestiek: [`Akoestiek.md`](Akoestiek.md)). Een responsspectrum
   (aardbeving, schok) rekent de bridge op een frequentiemodel met een Gravity-tabel als
   spectrum ([`Spectrumanalyse.md`](Spectrumanalyse.md)). Geef elke elset een materiaal: zonder
   materialen stopt de bridge.
2. Start de bridge: *Tools* > het menu-item van `MecwayAsterBridgeMain.py` (zie
   [`README.md`](../README.md)).
3. Het **hoofdvenster** verschijnt (§3). Controleer de instellingen en klik
   *Starten* (*Sluiten* stopt de bridge zonder run).
4. De bridge slaat het model op (`mw.save()`), leest de `.liml`, schrijft het mesh,
   `<model>_<run-id>.comm` en `.export` in de werkmap (§5) en start Code-Aster in een
   **apart venster**. Met route `tabel` controleert hij eerst of de Mecway-solution
   bij het mesh past; zo niet, dan stopt hij met een melding.
5. Mecway toont "Code_Aster is gestart in een apart venster. Klik op OK zodra de
   berekening klaar is." (met het convergentiescherm aan staat daartussen "Het
   convergentiescherm toont de voortgang."). Wacht tot in het Code-Aster-venster `DIAGNOSTIC JOB` staat en
   klik dan pas op OK. Klik je te vroeg, dan vraagt de bridge het nog een keer.
6. De resultaten komen in Mecway:
   - route `liml` (standaard): de bridge zet de resultaten in de `.liml` (de vorige
     versie blijft als `<model>.liml.bak`) en opent het model opnieuw; de resultaten
     blijven ook los bewaard en zijn later opnieuw in te laden (§5.1);
   - route `tabel`: de bridge schrijft knoopwaarden in de bestaande Mecway-solution
     (alleen statisch en niet-lineair statisch, §3).
7. Daarna komt het hoofdvenster terug. Het statusvak meldt de uitkomst, wat niet
   vertaald is ("Let op: deze belastingen/randvoorwaarden zijn NIET naar Code-Aster
   vertaald ...") en welke fouten Code-Aster gaf (§6). Bij modaal en knik staan daar
   ook de frequenties of kniklastfactoren.

## 3. Het hoofdvenster

Het venster blijft open tot je op **Sluiten** klikt. Na een run komt het terug, met
de uitkomst en eventuele meldingen in het **statusvak** onderaan. Het venster is
niet-modaal: Mecway blijft bruikbaar terwijl het open is (NIET in Mecway geverifieerd
voor alle handelingen, KNOWN_BUGS 38). De kop toont het model en de actieve analyse.

Links staat een **navigatielijst** met de pagina's van het venster, in groepen:
*Instellingen* (Algemeen, Elementen), *Analyses* (een pagina per analyse) en *Hulp*
(Documentatie). De gekozen pagina is gemarkeerd (vet, met een blauwe streep); rechts
staan haar titel en haar instellingen, in groepen. Klik op een pagina, of gebruik de
pijltjestoetsen (en Home/End) in de lijst; Ctrl+Tab en Ctrl+PageDown gaan vanuit het
hele venster naar de volgende pagina, Ctrl+Shift+Tab en Ctrl+PageUp naar de vorige.
Het venster mag groter gesleept worden (padvelden groeien mee); in een klein venster
schuiven de lijst en de pagina. *Starten* en *Sluiten* staan rechtsonder, de andere
knoppen links.

| Knop | Wat het doet |
|---|---|
| Starten | Slaat de instellingen op, slaat het model op en start Code-Aster (§2). Daarna komt het venster terug |
| Resultaten... | Slaat de instellingen op; daarna een eerdere run inladen, of de resultaten uit het model halen (kleine `.liml`; §5.1). Daarna komt het venster terug |
| Convergentiescherm | Opent het convergentie- en meldingenscherm als apart venster (blijft open naast Mecway) voor de nieuwste run van het open model in de map uit het veld *Werkmap*; is er geen run van dit model, dan de nieuwste `.mess` in die map. Zonder run meldt het statusvak dat er niets te tonen is |
| Uitleg... | Opent op de pagina Documentatie de woordenlijst met codes en namen (D31, `GDEF_LOG`, `MUMPS`, ...) |
| Sluiten | Sluit de bridge. Instellingen die je na de laatste *Starten* of *Resultaten...* hebt gewijzigd, worden niet opgeslagen |

- **Tooltips:** ga met de muis over een instelling voor uitleg; bij een keuzelijst
  staat ook de betekenis van elke optie erbij.
- **Pagina Documentatie:** de woordenlijst en de documenten uit `docs/` (in de
  gekozen taal), met opmaak; links naar andere documenten en naar koppen werken,
  webadressen openen in de standaardbrowser.
- **Opslaan:** instellingen gelden voor de run en worden bij *Starten* en
  *Resultaten...* opgeslagen in `Scripts/bridge_utils.py` (vorige versie:
  `bridge_utils.py.bak`). Lukt het venster niet (Windows Forms niet beschikbaar), dan
  vraagt de bridge de instellingen met tekstvragen (`mw.input`) en doet hij één run.

De kolom *Standaard* hieronder geeft de waarde zoals de repository die levert. Waarom
elke waarde zo gekozen is: [`Standaardinstellingen_en_aannames.md`](Standaardinstellingen_en_aannames.md).

**Pagina Algemeen**

| Instelling (label) | Standaard | Betekenis |
|---|---|---|
| Taal / Language | `en` | `nl` (Nederlands) of `en` (Engels): hoofdvenster, meldingen, WARNING/ERROR-regels in de log en het convergentiescherm, en de WAARSCHUWING/FOUT-regels (en: WARNING/ERROR) die de bridge-scripts in de Code-Aster-job naar de `.mess` schrijven. Geldt direct voor de run; het hoofdvenster wisselt van taal als het terugkomt. INFO/SUCCESS-regels en het commentaar in de `.comm` blijven Nederlands |
| Code-Aster launcher (run_aster.bat) | `%LOCALAPPDATA%\code_aster\v2025\17.4\bin\run_aster.bat` | pad naar `run_aster.bat`; omgevingsvariabelen zoals `%LOCALAPPDATA%` mogen. Bestaat het bestand niet, dan zegt het statusvak dat bij de start; kies het met *Bladeren...* |
| Werkmap | leeg = `WorkDir` naast de map `Scripts` (het venster toont dat pad) | map voor mesh, `<model>_<run-id>.*`, log en resultaten (§5); wordt aangemaakt als hij niet bestaat |
| Aantal CPU-kernen (ncpus) | 1 | `ncpus` (threads) in de `.export`; de bridge rekent zonder MPI (`mpi_nbcpu 1`) |
| Actieve analyse (auto = volgens Mecway) | `auto` | `auto` volgt het Mecway-analysetype: S30 → Statisch, L30 → Niet-lineair statisch, D30 met *Mode superposition* → Respons op modale basis, D30 zonder en D31 → Dynamisch (impliciet), T30/T31 → Thermisch, V30 → Modaal (met een fluïdum-onderdeel: Vibro-akoestiek (modes)), B30 → Knik, A30 → Akoestiek (holtemodes; met een bron, `BRON_`-selectie, Akoestiek (harmonisch)); geldt alleen voor die run. Of kies zelf een analyse (Dynamisch (expliciet) kies je altijd zelf). Een ander Mecway-type (2D, ...) met `auto`: de bridge stopt met een melding |
| Configuratie (auto = volgens de regel) | `auto` | welke configuratie de bridge rekent en in welke solution de resultaten komen; de lijst toont de configuraties van het open model (laatst opgeslagen versie). `auto`: de enige configuratie, anders de enige zonder onderdrukte items, anders de eerste (WARNING). Een naam die niet in het model staat: WARNING en `auto` (§4) |
| Eerst Mecway-solve ter controle | uit | lost eerst in Mecway op en stopt bij een fout. Schrijft `<model>_<run-id>_vergelijking.csv` (Mecway- en Code-Aster-waarde per knoop) en logt per variabele het grootste verschil; bij modaal en knik vergelijkt de log de frequentie of factor per mode |
| Resultaten naar Mecway | `liml` | `liml`: alle tijdstappen of modes, ook element-knoopwaarden; het model wordt heropend. `tabel`: alleen knoopwaarden van het laatste tijdstip, in de bestaande Mecway-solution; vraagt een solution die bij het mesh past; alleen voor Statisch en Niet-lineair statisch (niet voor dynamisch, thermisch, modaal en knik) |
| Convergentie- en meldingenscherm | aan | opent bij elke run een apart venster: bij een niet-lineaire analyse residuen, voortgang en contact; bij de statische analyse de lineaire oplosser (tijd per fase, foutgrens, conditiegetal; bij GCPC het residu per iteratie); bij modaal en knik de eerste modes; bij elke analyse de meldingen (fouten en alarmen met uitleg) en de diagnose. Achteraf: knop *Convergentiescherm*. Zie [Instellingen §4.4](Instellingen_contact_en_nietlineair.md#44-convergentiescherm) |
| MED-bestand voor ParaView | uit | schrijft ook `<model>_<run-id>.rmed` (ParaView/Salome); Mecway gebruikt het niet en het kan honderden MB worden |

Onder de instellingen staan de koppeling van `auto` aan de Mecway-analysetypen, een
opmerking over de taal en het pad van `bridge_utils.py`.

Mecway's lineaire *Dynamic Response* (D30): met de optie *Mode superposition* kiest
`auto` *Respons op modale basis* (`dyna_modal_3d`,
[`Respons_op_modale_basis.md`](Respons_op_modale_basis.md)); zonder kiest `auto`
*Dynamisch (impliciet)*. Zet daar *Tijdschema* `NEWMARK` en *COMPORTEMENT
DEFORMATION* `PETIT` voor hetzelfde schema als Mecway (verificatie MD-07: gelijk aan
Mecway); met andere waarden geeft de bridge een WARNING. De stationaire respons op een
sinusvormige last per frequentie (amplitude, fase) heeft geen Mecway-analysetype: kies
zelf *Harmonische respons* (`harmonic_3d`) voor een *Frequency*- of
*Dynamic Response*-model ([`Respons_op_modale_basis.md`](Respons_op_modale_basis.md) §7).

**Pagina Elementen** (alle mechanische analyses)

| Instelling (label) | Standaard | Keuzes |
|---|---|---|
| Hex8-volume-elementen | `3D` | `3D`: volledig geïntegreerd; stijver dan Mecway's hex8 met incompatibele modes (KNOWN_BUGS 1; de bridge geeft een WARNING). `3D_SI`: onderintegratie, alleen voor elsets met uitsluitend hex8 en niet expliciet; met één element over de dikte ~0 buigspanning. `LINE_QUAD`: Code-Aster maakt alle lineaire volume-elementen kwadratisch (hex8 → hex20, tet4 → tet10, ~3x zoveel knopen); alleen als verder niets lineair blijft (geen balken, veren, DKT-schalen), het model geen kwadratische volume-elementen heeft en niet expliciet; anders blijft het `3D` met een WARNING. Resultaten op de hoekknopen |
| Lineaire schalen (tri3/quad4) | `DKT` | `DKT` (Kirchhoff, dun), `DST` (met dwarskrachtvervorming; alleen in de statische analyse, anders DKT met een WARNING) of `COQUE_3D`: de schalen worden eerst kwadratisch (quad9/tria7, met rotatie om de normaal); delen ze knopen met elementen die lineair blijven, of zijn ze master van verlijmd contact, dan DKT (KNOWN_BUGS 2). Kwadratische schalen (tri6/quad8) zijn altijd `COQUE_3D` |
| Balken (line2/line3) | `POU_D_E` | `POU_D_E` (Euler-Bernoulli, zoals Mecway) of `POU_D_T` (Timoshenko, met afschuifvervorming). Een line3-balk wordt in de middenknoop in twee SEG2-cellen gesplitst (Code-Aster heeft geen kwadratische balk); de resultaten komen op alle drie de knopen terug |

**Een pagina per analyse**: Statisch, Niet-lineair statisch, Dynamisch (impliciet),
Dynamisch (expliciet), Thermisch, Modaal, Respons op modale basis, Harmonische
respons, Responsspectrum, Knik, Akoestiek (holtemodes), Akoestiek (harmonisch),
Vibro-akoestiek (modes) en Vibro-akoestiek (harmonisch). De pagina
van de actieve analyse heet "... (actief)". Bovenaan elke pagina staan het Code-Aster-commando, de gebruikte
`.comm`-template en de Mecway-typen die bij `auto` naar deze analyse leiden. Een
pagina toont alleen de instellingen die bij die analyse horen:

| Instelling (label) | Analyses | Standaard |
|---|---|---|
| Resultaatvelden naar Mecway | alle | zie §4.1 |
| Tijdslimiet run_aster [s] | alle | 600 (statisch), 1800 (niet-lineair statisch, thermisch, respons op modale basis, harmonische respons, responsspectrum, vibro-akoestiek (harmonisch)), 7200 (dynamisch), 900 (modaal, knik, akoestiek, vibro-akoestiek (modes)) |
| Geheugenlimiet run_aster [MB] | alle | 4096 (niet-lineair statisch, dynamisch, thermisch), 2048 (overige) |
| MUMPS NPREC (-1 = controle uit) | alle | 8 |
| Lineaire oplosser (MUMPS / GCPC) | statisch | `MUMPS` |
| Nauwkeurigheid oplosser (RESI_RELA) | statisch | 1e-6 |
| Foutschatter (CALC_ERREUR, alleen volumes) | statisch | aan ([`Foutschatter.md`](Foutschatter.md)) |
| Scheur: R_INF / R_SUP [m] (0 = automatisch), gladmaken langs het front, Legendre-graad | statisch (alleen met `SCHEUR_`-selecties of `#ASTER-XFEM`; gladmaken en graad niet voor XFEM) | 0 / 0, `LINEAIRE`, 5 ([`Breukmechanica.md`](Breukmechanica.md)) |
| Adaptieve verfijning (Mecway refine_x2) | statisch | uit ([`Foutschatter.md`](Foutschatter.md) §6) |
| Substappen per tijdsinterval | niet-lineair statisch | 10 |
| Max. Newton-iteraties (ITER_GLOB_MAXI) | niet-lineair statisch, dynamisch impliciet, thermisch (alleen `THER_NON_LINE`) | 20 |
| NEWTON REAC_ITER | niet-lineair statisch, dynamisch impliciet, thermisch (alleen `THER_NON_LINE`) | 1 (minimaal 1) |
| Eindtijd zonder tijdsbelasting [s] | niet-lineair statisch, dynamisch | 1.0 |
| Convergentiecriterium (RELA / MAXI / RELA of MAXI) | niet-lineair statisch, dynamisch impliciet | `RELA` (keuze `RELA`, `MAXI`, `RELA_OF_MAXI`) |
| Convergentie RESI_GLOB_RELA | niet-lineair statisch, dynamisch impliciet, thermisch (alleen `THER_NON_LINE`) | 1e-5 (niet-lineair statisch, dynamisch impliciet; Code-Aster-standaard 1e-6), 1e-6 (thermisch) |
| Convergentie RESI_GLOB_MAXI [N] | niet-lineair statisch, dynamisch impliciet (bij `MAXI` en `RELA_OF_MAXI`) | 1e-3 |
| Contactmethode (STANDARD / PENALISATION) | niet-lineair statisch, dynamisch | `STANDARD` |
| Rekdefinitie hardingscurve | niet-lineair statisch, dynamisch | `auto` |
| COMPORTEMENT DEFORMATION | niet-lineair statisch, dynamisch | `GROT_GDEP` |
| Tijdschema (SCHEMA_TEMPS) | dynamisch | `HHT` (impliciet; keuze `HHT`/`NEWMARK`), `DIFF_CENT` (expliciet; keuze `DIFF_CENT`/`TCHAMWA`) |
| HHT ALPHA (-0.3 .. 0) | dynamisch impliciet | -0.1 |
| Rekenstappen per uitvoerinterval | dynamisch impliciet | 1 |
| Energiebalans (ENERGIE; niet met contact) | dynamisch impliciet | uit |
| Tijdstap / kritieke tijdstap | dynamisch expliciet | 0.5 |
| Tijdschema THETA (0 .. 1) | thermisch | 0.57 |
| Bezwijken van elementen (plastische rek) | niet-lineair statisch, dynamisch | aan |
| Bezwijkgrens alle plastische mat. (0 = uit) | niet-lineair statisch, dynamisch | 0 |
| Stijfheid bezweken element (x E) | niet-lineair statisch, dynamisch | 1e-6 |
| Aantal modes (zonder maxmode in Mecway) | modaal, knik, respons op modale basis, harmonische respons, responsspectrum, akoestiek (holtemodes), vibro-akoestiek (modes) | 10, behalve 4 (knik) en 20 (responsspectrum) |
| Zoekfrequentie [Hz] (0 = laagste modes) | modaal, akoestiek (holtemodes) | 0 |
| Normering trillings-/knikvormen (NORM_MODE) | modaal, knik | `MASS_GENE` (modaal), `RIGI_GENE` (knik) |
| Controle modes (VERI_MODE SEUIL) | modaal, knik, respons op modale basis, harmonische respons, responsspectrum, akoestiek (holtemodes), vibro-akoestiek (modes) | 1e-6 |
| Rekenstappen per periode van de hoogste mode | respons op modale basis | 50 |
| Extra modale demping (fractie van kritisch) | respons op modale basis, harmonische respons | 0 |
| Statische correctie weggelaten modes (MACRO_ELAS_MULT) | respons op modale basis, harmonische respons | uit (respons op modale basis), aan (harmonische respons) |
| Spectrumtabel: kolom 'time' is | responsspectrum | `period` |
| Modale demping (fractie van kritisch) | responsspectrum | 0.05 |
| Combinatie modes / richtingen | responsspectrum | `CQC` / `SRSS` |
| Missing mass (pseudo-modes, MODE_CORR) | responsspectrum | aan |

De frequenties, bronnen en overige instellingen van de harmonische respons, de
akoestiek en de vibro-akoestiek staan in
[`Respons_op_modale_basis.md`](Respons_op_modale_basis.md) §7 en
[`Akoestiek.md`](Akoestiek.md).

Uitleg per instelling: [`Instellingen_contact_en_nietlineair.md`](Instellingen_contact_en_nietlineair.md)
§2 (mechanisch), [`Thermisch.md`](Thermisch.md) §2, [`Modaal_en_knik.md`](Modaal_en_knik.md)
§1.2, [`Respons_op_modale_basis.md`](Respons_op_modale_basis.md) §1.2,
[`Spectrumanalyse.md`](Spectrumanalyse.md) §1.2,
[`Foutschatter.md`](Foutschatter.md) §1.2 en [`Bezwijken.md`](Bezwijken.md). Knik zoekt altijd de kleinste
kniklastfactoren, zoals Mecway (geen instelling, zie
[`Modaal_en_knik.md`](Modaal_en_knik.md) §1.2). Voor één model kun je een instelling ook in
het model zetten met `#ASTER-OPTIE` (zie
[`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md)); die geldt alleen
voor die run en wordt niet opgeslagen.

### 3.1 Grote verplaatsingen (DEFORMATION)

`DEFORMATION` kiest de bridge per elementtype (`bridge_to_aster._deformation_for`):
kies je `GROT_GDEP`, `GREEN_LAGRANGE`, `GDEF_LOG` of `SIMO_MIEHE`, dan krijgen volumes
`GREEN_LAGRANGE` (elastisch) of `GDEF_LOG`/`SIMO_MIEHE` (plastisch), DKT/DST
`GREEN_LAGRANGE`, `COQUE_3D` `GROT_GDEP`, kabels altijd `GROT_GDEP` en balken
`PETIT` (WARNING; KNOWN_BUGS 11). Details:
[`Instellingen_contact_en_nietlineair.md`](Instellingen_contact_en_nietlineair.md) §2.3.

## 4. Wat wordt vertaald

Per onderdeel van Mecway (analysetypen, belastingen, randvoorwaarden, koppelingen en
contact, elementen, materialen en doorsneden, resultaten, instellingen) staat in
[`Mecway_functionaliteit.md`](Mecway_functionaliteit.md) of het vertaald wordt (Ja,
Deels of Nee), met de beperking en wat je anders kunt doen. Daarnaast doet de bridge:

| Onderdeel | Ondersteund |
|---|---|
| Mecway-invoer | [`Mecway_functionaliteit.md`](Mecway_functionaliteit.md) |
| Lassen | bewegende warmtebron (Goldak dubbel-ellipsoïde) in een transiente thermische analyse via `#ASTER-LASBRON`, of als Mecway-formule in x, y, z, t (heat generation, heat flux); temperatuurafhankelijke geleidbaarheid en soortelijke warmte; met een Thermal stress daarna restspanning en vervorming (`STAT_NON_LINE`, temperatuurafhankelijke E, vloeigrens en α via `#ASTER-MATERIAAL`); fase-omzettingen in staal en hardheid (`CALC_META`, TRC-diagram) via `#ASTER-METALLURGIE`, als optie met transformatierek in de restspanning: [`Lassen.md`](Lassen.md) |
| Bezwijken | elementen met een plastische rek boven een grens krijgen een zeer lage stijfheid en spanning nul (niet-lineair statisch en dynamisch, volume-elementen en schalen, niet balken; grens via `#ASTER-BEZWIJKEN`, `PLAS_TAB` Eps_p_max of een instelling): [`Bezwijken.md`](Bezwijken.md) |
| Vermoeiing | schade D en levensduur per knoop van volume-elementen en schalen (boven- en onderzijde) met een Wöhler- of rekcurve (Manson-Coffin) per materiaal (`#ASTER-WOHLER`), rainflow en Miner, of een kritiekvlakcriterium (Dang Van, Matake, Crossland; `#ASTER-VERMOEIING criterium`); belastingsverloop als blokken of signaal op een statische run (`#ASTER-BLOK`, `#ASTER-SIGNAAL`) of de tijdstappen van een niet-lineaire/dynamische run: [`Vermoeiing.md`](Vermoeiing.md) |
| Resultaten | zie §4.1 |

Wat niet vertaald wordt, meldt de bridge aan het eind van de run. Wat Mecway niet kan
invoeren maar Code-Aster wel kent, voeg je toe met `#ASTER`-regels.

**Eenheden.** De bridge rekent alle Mecway-waarden met een eenheid om naar SI.
Een eenheid die hij niet kent, gebruikt hij ongewijzigd met een WARNING in de log;
controleer dan de invoer.

**Configuraties.** De actieve configuratie is via de Mecway-API niet te lezen; kies
daarom op het startscherm (Algemeen) bij *Configuratie* welke de bridge rekent. De
lijst toont de configuraties van het open model (de laatst opgeslagen versie: sla
een nieuwe configuratie eerst op). Met `auto` rekent de bridge de enige
configuratie, anders de configuratie waarin niets onderdrukt is; zijn er geen of
meerdere, dan de eerste, met een WARNING. Items die in de gerekende configuratie of
via een onderdrukte groep onderdrukt zijn, laat hij weg. De resultaten komen in de
solution van die configuratie; de solutions van de andere configuraties blijven
staan, en de bridge maakt de configuratie actief in Mecway
(`mw.set_active_configuration`). De instelling geldt ook voor *Resultaten...*: zet
haar op de configuratie van de run voordat je die resultaten inlaadt.

**Lastgevallen en combinaties.** Mecway kent geen load cases meer (ze worden bij het
openen omgezet naar configuraties) en een configuratie heeft geen factor: ze zet
alleen lastitems aan of uit (manual §2.8; in de `.liml` een `<configuration
name=".."/>` en per item `<suppressed configuration=".."/>`). Een combinatie als
1,2 G + 1,5 Q met factoren en een omhullende over lastgevallen zijn daarom niet in
Mecway in te stellen, en de bridge vertaalt ze niet (`MACRO_ELAS_MULT` is niet
gebouwd). Zo doe je het wel:
1. Maak per lastgeval en per combinatie een configuratie (Edit → New
   configuration). Geef een combinatie eigen lastitems met de gefactoreerde waarde
   (bijv. een tweede gravity met 1,2 × 9,81 m/s² en een tweede druk met 1,5 × q) en
   onderdruk in elke configuratie de items die er niet bij horen. Lineair statisch is
   dat gelijk aan de superpositie (Mecway headless: 1,2 G + 1,5 Q op 3e-15 relatief).
2. De bridge rekent per run één configuratie: kies haar op het startscherm
   (*Configuratie*) en start; herhaal dat per lastgeval of combinatie. Elke run zet
   zijn resultaten in de solution van zijn configuratie, zodat je in Mecway tussen de
   configuraties kunt wisselen. Verificatie LS-20: G, Q en ULS met de instelling
   gekozen, ULS = 1,2 G + 1,5 Q op 5e-16 relatief.
3. Mecway's eigen solver rekent alle configuraties (Solve all configurations;
   headless `mecway <model> solve` doet dat ook); daarmee kun je een bridge-run per
   configuratie controleren.

**Formules.** Een waarde als formule (Mecway: Formula) wordt vertaald als ze alleen
van de tijd t afhangt. De bridge bemonstert de formule zoals Mecway voor CCX doet:
10001 tijden van 0 tot de Time period, daarna alleen de punten waarmee de lijn
hoogstens 0,01% van het bereik afwijkt; het resultaat is een `DEFI_FONCTION`. De
eenheden uit Mecway (waarde, tijd in s of min) worden toegepast; een formule zonder t
is een gewone waarde. Formules in x, y of z (plaatsafhankelijk) en formules die de
bridge niet kan lezen, worden gemeld (ERROR) en niet meegenomen. Toegestaan:
`+ - * / ^`, haakjes, `pi`, `e`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`,
`log` (natuurlijk), `abs`, `sqrt`, `heaviside`, `unittriangle`, `max`, `min`. In een
lineair statische, modale of knikanalyse geldt de waarde op de eindtijd. Een gekromde
formule (bijv. een sinus) geeft veel tijdspunten en dus veel rekenstappen
(KNOWN_BUGS 45).

### 4.1 Resultaatvelden

Met *Resultaatvelden naar Mecway* kies je per analyse welke velden de bridge
teruggeeft; minder velden geeft een kleinere `.liml`. Namen in Mecway zijn dezelfde
als die van Mecway's eigen oplossing waar Mecway ze kent.

| Veld | Mecway-variabelen | Code-Aster-veld | Standaard aan bij |
|---|---|---|---|
| `displacements` | `displx/y/z`, `displmag` (niet bij modaal, zoals Mecway); `rotx/y/z` op knopen van balken en schalen | `DEPL` | alle mechanische analyses |
| `stresses` | `stressxx` .. `stresszx` (volume-elementen, knoopwaarden en per element-knoop); `beamsixxmin`/`beamsixxmax` (balken met rechthoekige of ronde doorsnede: kleinste/grootste axiale spanning uit N en M, zonder afschuiving en torsie) | `SIGM_NOEU`, `SIGM_ELNO`, `SIPM_ELNO` | statisch, niet-lineair, dynamisch, respons op modale basis, harmonische respons, responsspectrum, vibro-akoestiek (harmonisch) |
| `vonmises` | `vonmises` (volume); `vonmisesu1`/`vonmisesm`/`vonmisesb` (schaal boven/midden/onder) | `SIEQ_NOEU`, `SIEQ_ELNO` | als `stresses` |
| `reactions` | `reactionforcex/y/z/mag`, `reactionmomx/y/z/mag` | `REAC_NODA` | statisch, niet-lineair, dynamisch, responsspectrum |
| `velocities` | `velx/y/z`, `velmag`; `angularvelx/y/z`, `angularvelmag` op knopen van balken en schalen | `VITE` | dynamisch, respons op modale basis |
| `accelerations` | `accelx/y/z`, `accelmag` (harmonisch: `accelampx/y/z`, ω²\|U\|) | `ACCE` (responsspectrum: `ACCE_ABSOLU`) | harmonische respons, responsspectrum, vibro-akoestiek (harmonisch) |
| `plastic_strain` | `plasticstrainxx` .. `plasticstrainzx` (namen van de bridge) | `EPSP_NOEU` | niet-lineair statisch |
| `plastic_strain_eq` | `equivalentplasticstrain` | `VARI_NOEU` V1 | niet-lineair, dynamisch |
| `temperature` | `temperature` (K) | `TEMP` | thermisch |
| `heat_flux` | `heatfluxx/y/z/mag` | `FLUX_NOEU` | thermisch |
| foutschatter (instelling *Foutschatter*, niet in deze keuzelijst) | `errorestimate`, `errorestimaterel` (volume-elementen, knoopwaarden en per element; namen van de bridge) | `ERME_NOEU`, `ERME_ELNO` | statisch ([`Foutschatter.md`](Foutschatter.md)) |
| vermoeiing (`#ASTER-WOHLER`, niet in deze keuzelijst) | `damage` (schade D), `life` (herhalingen tot D = 1); schalen ook `damage_top`/`damage_bottom`, met een criterium `fatigue_eq`/`fatigue_ratio`; knoopwaarden, namen van de bridge | uit `SIGM_NOEU`/`EPSI_NOEU`/`SIEQ_NOEU` (rainflow, Miner; `aster_fatigue.py`) of `CALC_FATIGUE FATIGUE_MULTI` | statisch, niet-lineair, dynamisch ([`Vermoeiing.md`](Vermoeiing.md)) |
| `metallurgy` | `ferrite`, `pearlite`, `bainite`, `martensite`, `austenite` (fasefracties), `hardness` (als de dataset hardheid heeft); namen van de bridge | `META_NOEU`, `DURT_NOEU` | thermisch transient: met `#ASTER-METALLURGIE` altijd mee, alleen route `liml` ([`Lassen.md`](Lassen.md) §10) |
| druk (akoestiek, niet in deze keuzelijst) | `pressure` per mode (Mecway's naam); harmonisch per frequentie ook `pressurei`, `pressuremag`, `pressurephase`, `spl` | `PRES` (vibro-akoestiek: `DEPL` component `PRES`) | akoestiek, altijd ([`Akoestiek.md`](Akoestiek.md)) |

Bij modaal en knik geeft de bridge alleen de vormen (`displacements`), zoals Mecway;
andere gekozen velden worden genegeerd (INFO in de log). Knoopspanningen volgen de
Code-Aster-standaard (extrapolatie en middeling per knoop) en wijken daardoor af van
Mecway (KNOWN_BUGS 3). Schaalspanningstensoren (lokaal assenstelsel) worden niet
geladen.

## 5. Bestanden in de werkmap

Alle bestanden van een run heten `<model>_<run-id>...`: `<model>` is de naam van het
Mecway-bestand (tekens buiten A-Z, a-z, 0-9, `-` en `_` worden `_`, zonder dubbele of afsluitende
`_`, bijv. `Mijn Model (v2).liml` → `Mijn_Model_v2`; bij een te lang
pad ingekort, §1), `<run-id>` de datum en tijd van de start, bijv.
`ProfielBuigen_20261006_101500.mess`. Zo staan ze bij elkaar en overschrijft een
volgende run niets. In meldingen staat de echte naam.

| Bestand | Inhoud |
|---|---|
| `<model>_<run-id>_bridge_log.txt` | log van de bridge (INFO/WARNING/ERROR per stap); `bridge_log.txt`: alleen meldingen buiten een run (bijv. *Resultaten...*) |
| `<model>_<run-id>.mail` | het mesh (ASTER-formaat) |
| `<model>_<run-id>.comm`, `<model>_<run-id>.export` | Code-Aster-invoer; met `run_aster.bat <model>_<run-id>.export` opnieuw te draaien |
| `<model>_<run-id>.mess` | berichten van Code-Aster (fouten, alarmen, tabellen met `UNITE=6`) |
| `<model>_<run-id>_console.txt` | volledige console-uitvoer van Code-Aster (ook Python-fouten) |
| `<model>_<run-id>_results.xml` | **de resultaten** in Mecway's eigen formaat (route `liml`); de bridge zet ze in de `.liml` en laat het bestand staan, zodat je ze later opnieuw kunt inladen (§5.1) |
| `<model>.liml.bak` | de `.liml` van vóór het inlezen of verwijderen van resultaten |
| `<model>_<run-id>.resu` | resultaattabellen, alleen bij route `tabel` |
| `<model>_<run-id>.rmed` | resultaten in MED (ParaView/Salome), alleen met *MED-bestand voor ParaView* |
| `<model>_<run-id>_vergelijking.csv` | vergelijking met de Mecway-solve (alleen met *Eerst Mecway-solve ter controle*) |
| `<model>_<run-id>_monitor_log.txt` | log van het convergentie- en meldingenscherm |

Bestanden zonder tijdstempel van oudere bridge-versies (`study.mess`,
`model_mesh.mail`, `study_results.xml`, ...) ruimt de bridge bij de start van een run
op. Bestanden met een tijdstempel blijven staan; gooi oude runs zelf weg als je ze
niet meer nodig hebt (`_results.xml` en `.rmed` kunnen groot zijn).

### 5.1 Resultaten later opnieuw inladen (kleine .liml)

Mecway toont alleen resultaten die in de `.liml` staan; die wordt daardoor groot
(ongeveer zo groot als `<model>_<run-id>_results.xml`). Met de knop **Resultaten...**
in het hoofdvenster kies je:

- **Uit model verwijderen**: haalt alle resultaten uit de open `.liml` (vorige versie:
  `.bak`). Het model zelf blijft gelijk en de `.liml` is weer klein; de
  resultaatbestanden in de werkmap blijven staan.
- **Inladen**: kies een run uit de lijst (nieuwste eerst, met datum, model en grootte),
  of een `_results.xml` elders met *Ander bestand...*. De bridge controleert eerst of
  het mesh gelijk is: knoop- en elementnummers, en de knoopcoördinaten via
  `<model>_<run-id>.mail` van dezelfde run (bewaar dat bestand dus bij de
  resultaten). Is het mesh gewijzigd, dan worden de resultaten niet ingeladen.

Beide slaan het model eerst op en openen het daarna opnieuw. De resultaten zijn die
van de run: wijzig je daarna belastingen of materialen, dan horen ze daar niet meer
bij (alleen het mesh wordt gecontroleerd).

## 6. Fouten lezen

- **Melding vóór Code-Aster** ("Schrijven van het mesh mislukt", "Genereren
  solver-bestanden mislukt", "Geen materialen gevonden in het model", "De werkmap is
  te lang", analysetype niet ondersteund): zie de ERROR-regels in
  `<model>_<run-id>_bridge_log.txt`.
- **"Code-Aster meldt fouten in `<model>_<run-id>.mess`"**: de bridge zoekt
  `<EXCEPTION>`, `<F>`, `<S>`, `<E>` en `<...Error>` in de `.mess` en toont de eerste
  vijf meldingen. Bij een bekende code geeft hij uitleg:
  - `FACTOR_10/11/42/57` en `MECANONLINE9_4`: singuliere stijfheidsmatrix; meestal
    kan een deel vrij bewegen of staan er dubbele opleggingen;
  - `MECANONLINE9_7`: Newton convergeert niet; de resultaten tot het laatst
    bereikte tijdstip zijn geladen. Zie
    [`Instellingen_contact_en_nietlineair.md`](Instellingen_contact_en_nietlineair.md) §4;
  - `ALGELINE3_81` (modaal): singuliere stijfheid door een mechanisme;
    `ALGELINE5_49` / `ALGELINE3_78`: te weinig modes rond de zoekfrequentie. Zie
    [`Modaal_en_knik.md`](Modaal_en_knik.md) §4;
  - `ALGORITH16_52`, `ALGORITH16_58`, `ALGORITH14_94` (cyclische symmetrie): de
    snijvlakken herhalen niet om de as. Zie [`Modaal_en_knik.md`](Modaal_en_knik.md) §7.

  Alarmen (`<A>`) staan als WARNING in de log, bij bekende codes met uitleg:
  modecontrole `ALGELINE5_23`, `ALGELINE2_74`; `ALGELINE3_82` (ondergrens van de
  Sturm-band op een starre mode, meestal onschuldig); `MODELISA4_8`/`MODELISA8_13`
  (dubbele cellen, normaal bij vibro-akoestiek); bij complexe modes `ALGELINE5_79`
  (minder modes dan gevraagd) en `FACTOR_11` (vrij-vrij model). Alle eerder geziene codes, met oorzaak
  en oplossingen: [`Foutmeldingen_CodeAster.md`](Foutmeldingen_CodeAster.md).
- **"Code-Aster schreef geen .mess voor deze run"** of **alleen "DIAGNOSTIC JOB :
  <F>_ABNORMAL_ABORT"** zonder melding: de oorzaak staat in het Code-Aster-venster
  (dat blijft dan open).
- **"Python-fout in `<model>_<run-id>.comm`"**: de `.comm` is niet (helemaal)
  uitgevoerd, meestal door een tikfout in `#ASTER`-regels. De melding noemt de
  foutregel; de volledige uitvoer staat in `<model>_<run-id>_console.txt`.
- **Resultaten wijken af van Mecway**: zie `KNOWN_BUGS.md` (o.a. hex8 stijver,
  knoopspanningen volgens de Code-Aster-standaard).

## 7. Aannames

De belangrijkste aannames voor het gebruik; de volledige lijst, met de onderbouwing
van de standaardwaarden, staat in
[`Standaardinstellingen_en_aannames.md`](Standaardinstellingen_en_aannames.md).

- **Aanname:** het `.liml`-formaat van Mecway 33 (getest); andere versies zijn niet
  getest.
- **Aanname:** met *Configuratie* = `auto` is de enige configuratie of die zonder
  onderdrukte items de bedoelde (§4); de API kan de actieve configuratie niet lezen.
- **Aanname:** de bovenkant van een schaal in Code-Aster (`SUP`, kant van de positieve
  elementnormaal) is Mecway's `vonmisesu1`; NIET geverifieerd.
- **Aanname:** een formule in t wordt bemonsterd zoals Mecway dat voor CCX doet (§4).
- Het niet-modale hoofdvenster en de knoppen zijn NIET voor alle handelingen in Mecway
  geverifieerd (KNOWN_BUGS 38).
- De bridge benadert Mecway niet exact waar Code-Aster een eigen standaard heeft
  (bijv. knoopspanningen, hex8): de keuze volgt Code-Aster, met opties waar mogelijk.

## 8. Bronnen

- EDF R&D (2019). *Code_Aster, documentation U4.51.01: Opérateur MECA_STATIQUE*. Versie
  "default", 10-12-2019 (lokale kopie; de bridge gebruikt Code-Aster 17.4).
- EDF R&D (2020). *Code_Aster, documentation U4.51.03: Opérateur STAT_NON_LINE*.
  Versie "default", 30-04-2020.
- EDF R&D (2021). *Code_Aster, documentation U4.50.01: Mot clé SOLVEUR*. Versie
  "default", 04-11-2021.
- EDF R&D (2016). *Code_Aster, documentation U3.14.01: Modélisations 3D et 3D_SI
  mécaniques*. Versie "default", 21-12-2016.
- EDF R&D (2018). *Code_Aster, documentation R3.07.03: Éléments de plaque :
  modélisations DKT, DST, DKTG et Q4G*. Versie "default", 28-06-2018.
- EDF R&D (2025). *code_aster 17.4, commandocatalogus* (`lib/aster/code_aster/Cata/Commands/*.py`
  van de Windows-installatie): standaardwaarden en toegestane keuzes van de
  sleutelwoorden.
- Mecway Ltd. (2026). *Mecway Finite Element Analysis, Manual, Version 33*
  (`C:\Program Files\Mecway\manual.pdf`): §2.8 Configurations, §6 Analysis types,
  §16.2 Scripts.

De Code-Aster-documenten hierboven zijn de lokale (Engelse, machinaal vertaalde)
kopieën in de map met Code-Aster-documentatie; hun inhoud kan op details afwijken van
versie 17.4. Waar het gedrag van 17.4 telt, is het nagelopen in de catalogus of met een
run (zie [`Verificatie.md`](Verificatie.md)).

## Merken

Mecway is een product van Mecway Ltd. Code_Aster is een handelsmerk van EDF. Dit project is niet verbonden aan en niet goedgekeurd door Mecway Ltd of EDF.
