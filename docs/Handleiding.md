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
| Boutvoorspanning (*Pre-tension section*) | [`Boutvoorspanning.md`](Boutvoorspanning.md) |
| Vermoeiing: schade en levensduur per knoop (Wöhler-curve, rainflow, Miner, kritiekvlakcriteria, Manson-Coffin; `#ASTER-WOHLER`) | [`Vermoeiing.md`](Vermoeiing.md) |
| Eigen Code-Aster-invoer (`#ASTER`-regels) | [`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md) |
| Meldingen van Code-Aster, oorzaak en oplossing | [`Foutmeldingen_CodeAster.md`](Foutmeldingen_CodeAster.md) |
| Verificatie tegen analytische oplossingen | [`Verificatie.md`](Verificatie.md) |
| Na een update van Mecway of Code-Aster: versiewaarschuwing, nieuwe versie controleren | [`Na_een_update.md`](Na_een_update.md) |
| Bekende afwijkingen en beperkingen (ontwikkelbestand, Engels) | [`KNOWN_BUGS.md`](../KNOWN_BUGS.md) |

## 1. Benodigd

- **Mecway 33 of 34.** De bridge draait in Mecway's IronPython 2.7-scriptomgeving
  (Mecway Ltd., 2026, §16.2) en is getest met `.liml`-bestanden van versie 33 en 34:
  ontwikkeld en geverifieerd met Mecway 34; Mecway 33 is voor het laatst volledig
  geverifieerd met V2026.2 (welke functies per versie geverifieerd zijn:
  [`Na_een_update.md`](Na_een_update.md) §6). Andere versies zijn niet getest
  (aanname: het `.liml`-formaat is gelijk); de bridge waarschuwt dan.
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
5. Het **statusvenster** "Code-Aster-run" verschijnt (instelling *Wachten op Code-Aster* =
   `auto`, standaard). Het toont de verstreken tijd (met de tijdslimiet van de `.export`),
   wat Code-Aster op dat moment doet (niet-lineair: bereikt tijdstip, poging, niveau en
   Newton-iteratie; statisch: de fase van de lineaire oplosser; modaal: de gevonden modes;
   anders de laatste regel van de uitvoer) en het aantal fouten en alarmen tot nu toe. Het
   venster is modaal: Mecway is geblokkeerd tot de run klaar is, want daarna opent de bridge
   het model opnieuw met de resultaten. Het staat tijdens de run altijd bovenop (ook boven
   het Code-Aster-venster, dat zonder focus opent en leesbaar blijft; op Windows 11 kan
   Windows Terminal de focus toch nemen, het statusvenster blijft dan zichtbaar en
   klikbaar). Tot Code-Aster aan het eerste commando begint staat er "Code-Aster wordt
   gestart...". Het sluit vanzelf zodra Code-Aster klaar is
   (`run_aster` is teruggekeerd); de bridge herkent dat aan een eindmarkering die het
   Code-Aster-venster schrijft (`<model>_<run-id>_done.txt`, met de exitcode van
   `run_aster`; wordt na de run verwijderd), en anders aan `DIAGNOSTIC JOB` aan het einde van
   de `.mess`.
   - **Stoppen...** (of het sluitkruis, Esc) vraagt eerst om bevestiging en beëindigt dan
     alleen de processen van deze run (het Code-Aster-venster en alles wat daaruit gestart
     is). De uitvoer tot dat moment komt in de `.mess` met de regel `BRIDGE_GESTOPT`; het
     statusvak en het convergentiescherm melden "Run gestopt door de gebruiker." Code-Aster
     schrijft de resultaten pas aan het einde van de run, dus een gestopte run heeft meestal
     geen resultaten. Een adaptieve verfijning (§4) stopt dan ook.
   - Sluit je het Code-Aster-venster zelf tijdens de run, dan meldt de bridge "Run
     afgebroken: het Code-Aster-venster is gesloten." en gaat verder zoals na Stoppen.
   - Eindigt `run_aster` met een exitcode ongelijk aan 0, dan meldt het statusvak die code
     met het pad van de `.mess`; het Code-Aster-venster blijft dan open (net als bij een
     fout in de `.mess`).
   - Duurt de run langer dan de tijdslimiet (met 2 minuten marge), dan waarschuwt het
     venster; Code-Aster stopt normaal zelf bij de limiet.

   Met *Wachten op Code-Aster* = `confirm` (of als het statusvenster niet getoond kan
   worden) werkt het zoals voorheen: Mecway toont "Code_Aster is gestart in een apart venster.
   Klik op OK zodra de berekening klaar is." (met het convergentiescherm aan staat daartussen
   "Het convergentiescherm toont de voortgang."). Wacht tot in het Code-Aster-venster
   `DIAGNOSTIC JOB` staat en klik dan pas op OK. Klik je te vroeg, dan vraagt de bridge het
   nog een keer.
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
de uitkomst en eventuele meldingen in het **statusvak** onderaan; bij een melding wordt
het vak hoger, en met de bovenrand sleep je het groter of kleiner. Het venster is
niet-modaal: Mecway blijft bruikbaar terwijl het open is (NIET in Mecway gecontroleerd
voor alle handelingen, KNOWN_BUGS 38). De bridge draait maar één keer tegelijk per
Mecway: start je hem opnieuw (*Tools*) terwijl het venster open is of een run loopt, dan
meldt hij dat het venster al open is en opent hij geen tweede venster. De kop toont het
model en de actieve analyse.

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
| Resultaten... | Slaat de instellingen op; daarna een eerdere run inladen, of de resultaten uit het model halen (kleine `.liml`; §5.1); met AdvancedToolsHub ook *In MWHub Post* (de gekozen run in ParaView, met `.rmed` of `.pvd`). Daarna komt het venster terug |
| Convergentiescherm | Opent het convergentie- en meldingenscherm als apart venster (blijft open naast Mecway) voor de nieuwste run van het open model in de werkmap die het venster toont (veld *Werkmap*, of met *Werkmap naast het model* de map naast het model); is er geen run van dit model, dan de nieuwste `.mess` in die map. Zonder run meldt het statusvak dat er niets te tonen is |
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
| Taal / Language | `en` | `nl` (Nederlands) of `en` (Engels): hoofdvenster, meldingen, WARNING/ERROR-regels in de log en het convergentiescherm, en de WAARSCHUWING/FOUT-regels (en: WARNING/ERROR) die de bridge-scripts in de Code-Aster-job naar de `.mess` schrijven. Geldt direct voor de run; het hoofdvenster wisselt van taal als het terugkomt. INFO/SUCCESS-regels en het commentaar in de `.comm` zijn altijd Engels |
| Code-Aster launcher (run_aster.bat) | `%LOCALAPPDATA%\code_aster\v2025\17.4\bin\run_aster.bat` | pad naar `run_aster.bat`; omgevingsvariabelen zoals `%LOCALAPPDATA%` mogen. Bestaat het bestand niet, dan zegt het statusvak dat bij de start; kies het met *Bladeren...* |
| Werkmap | leeg = `WorkDir` naast de map `Scripts` (het venster toont dat pad) | map voor mesh, `<model>_<run-id>.*`, log en resultaten (§5); wordt aangemaakt als hij niet bestaat |
| Werkmap naast het model (<model>_aster) | uit | aan: de bestanden van een run gaan naar de submap `<model>_aster` naast het open `.liml`-bestand (bijv. `C:\Projecten\Ligger.liml` → `C:\Projecten\Ligger_aster`), ook voor *Resultaten...*, het convergentiescherm en adaptieve verfijning; naast het vinkje staat de map die gebruikt wordt. Een model dat nog niet is opgeslagen gebruikt de *Werkmap* |
| Aantal CPU-kernen (ncpus) | 1 | `ncpus` (threads) in de `.export`; de bridge rekent zonder MPI (`mpi_nbcpu 1`) |
| Actieve analyse (auto = volgens Mecway) | `auto` | `auto` volgt het Mecway-analysetype: S30 → Statisch, L30 → Niet-lineair statisch, D30 met *Mode superposition* → Respons op modale basis, D30 zonder en D31 → Dynamisch (impliciet), T30/T31 → Thermisch, V30 → Modaal (met een fluïdum-onderdeel: Vibro-akoestiek (modes)), B30 → Knik, A30 → Akoestiek (holtemodes; met een bron, `BRON_`-selectie, Akoestiek (harmonisch)); geldt alleen voor die run. Of kies zelf een analyse (Dynamisch (expliciet) kies je altijd zelf). Een ander Mecway-type (2D, ...) met `auto`: de bridge stopt met een melding |
| Configuratie (auto = volgens de regel) | `auto` | welke configuratie de bridge rekent en in welke solution de resultaten komen; de lijst toont de configuraties van het open model (laatst opgeslagen versie). `auto`: de enige configuratie, anders de enige zonder onderdrukte items, anders de eerste (WARNING). Een naam die niet in het model staat: WARNING en `auto` (§4) |
| Eerst Mecway-solve ter controle | uit | lost eerst in Mecway op en stopt bij een fout. Schrijft `<model>_<run-id>_vergelijking.csv` (Mecway- en Code-Aster-waarde per knoop) en logt per variabele het grootste verschil; bij modaal en knik vergelijkt de log de frequentie of factor per mode |
| Resultaten naar Mecway | `liml` | `liml`: alle tijdstappen of modes, ook element-knoopwaarden; het model wordt heropend. `tabel`: alleen knoopwaarden van het laatste tijdstip, in de bestaande Mecway-solution; vraagt een solution die bij het mesh past; alleen voor Statisch en Niet-lineair statisch (niet voor dynamisch, thermisch, modaal en knik) |
| Convergentie- en meldingenscherm | aan | opent bij elke run een apart venster: bij een niet-lineaire analyse residuen, voortgang en contact; bij de statische analyse de lineaire oplosser (tijd per fase, foutgrens, conditiegetal; bij GCPC het residu per iteratie); bij modaal en knik de eerste modes; bij elke analyse de meldingen (fouten en alarmen met uitleg) en de diagnose. Achteraf: knop *Convergentiescherm*. Zie [Instellingen §4.4](Instellingen_contact_en_nietlineair.md#44-convergentiescherm) |
| Wachten op Code-Aster | `auto` | `auto`: een modaal statusvenster met de voortgang en *Stoppen...*; de bridge herkent zelf het einde van de run en laadt dan de resultaten (§2 stap 5). `confirm`: je klikt op OK in Mecway als het Code-Aster-venster `DIAGNOSTIC JOB` toont (het eerdere gedrag) |
| MED-bestand voor ParaView | uit | schrijft ook `<model>_<run-id>.rmed` (ParaView/Salome); Mecway gebruikt het niet en het kan honderden MB worden |
| Code-Aster-uitvoer als Saved monitor in de .liml | `summary` | na de run zet de bridge de uitvoer van Code-Aster in de `.liml` als Mecway's item *Saved monitor* onder *Solution*, zodat je die in Mecway terugleest als de Code-Aster-vensters dicht zijn (§5.2). `summary`: fouten en alarmen, stappen, tijden en het pad van de volledige `.mess`; `full`: de hele `.mess` (boven 4 miljoen tekens het begin en het einde); `off`: niets. Alleen route `liml` |
| VTU/PVD-bestanden voor ParaView | uit | schrijft ook `<model>_<run-id>.pvd` met een `.vtu` per tijdstap (elke ParaView leest het, ook zonder MED-lezer), met dezelfde velden als Mecway krijgt, en `<model>_<run-id>_knopen.csv` (per benoemde knoopselectie van max. 100 knopen de knoopvelden over de tijd) |
| AdvancedToolsHub-map (leeg = automatisch) | leeg | map van AdvancedToolsHub; gevonden = de knop *ParaView* opent de run in MWHub Post (Mecway-weergave, eenheden, bezweken elementen verbergen); leeg = `%ADVANCEDTOOLSHUB_DIR%`, anders de map `AdvancedToolsHub` naast deze repository; niet gevonden = de `.rmed` rechtstreeks in ParaView |
| ParaView (leeg = automatisch zoeken) | leeg | `paraview.exe` voor de knop *ParaView* van het convergentiescherm; leeg = automatisch: eerst de officiele ParaView 6.x (`%ProgramFiles%\ParaView 6*\bin\paraview.exe`, nieuwste eerst), die zelf een `.rmed` leest; dan als terugval de ParaView van Salome-Meca (`C:\Salome_meca\*\*\ParaView\bin\paraview.exe`, `%ProgramFiles%\SALOME*`, gestart via `run_paraview.bat`); als laatste een oudere ParaView. ParaView 5.10 van paraview.org kan een `.rmed` **niet** openen. Omgevingsvariabelen mogen |

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
| Hex8-volume-elementen | `3D` | `3D`: volledig geïntegreerd; stijver dan Mecway's hex8 met incompatibele modes (KNOWN_BUGS 1; de bridge geeft een WARNING); met hyperelastisch materiaal (rubber) ~3x te stijf door volumetrische locking: kies dan `LINE_QUAD`. `3D_SI`: onderintegratie, alleen voor elsets met uitsluitend hex8, niet expliciet en niet hyperelastisch; met één element over de dikte ~0 buigspanning. `LINE_QUAD`: Code-Aster maakt alle lineaire volume-elementen kwadratisch (hex8 → hex20, tet4 → tet10, ~3x zoveel knopen); alleen als verder niets lineair blijft (geen balken, veren, DKT-schalen), het model geen kwadratische volume-elementen heeft en niet expliciet; anders blijft het `3D` met een WARNING. Resultaten op de hoekknopen |
| Lineaire schalen (tri3/quad4) | `DKT` | `DKT` (Kirchhoff, dun), `DST` (met dwarskrachtvervorming; alleen in de statische analyse, anders DKT met een WARNING) of `COQUE_3D`: de schalen worden eerst kwadratisch (quad9/tria7, met rotatie om de normaal); delen ze knopen met elementen die lineair blijven, of zijn ze master van verlijmd contact, dan DKT (KNOWN_BUGS 2). Kwadratische schalen (tri6/quad8) zijn altijd `COQUE_3D` |
| Balken (line2/line3) | `POU_D_E` | `POU_D_E` (Euler-Bernoulli, zoals Mecway), `POU_D_T` (Timoshenko, met afschuifvervorming) of `POU_D_T_GD` (Timoshenko met grote verplaatsingen en rotaties; alleen niet-lineair statisch met grote verplaatsingen, elders `POU_D_T`; geen balkspanningen, [Instellingen §2.9](Instellingen_contact_en_nietlineair.md#29-balken-met-grote-rotaties-elem_beam--pou_d_t_gd)) of `POU_D_TG` (Timoshenko met welving en dwarskrachtcentrum: buig-torsieknik en kip van open profielen, [Modaal en knik §3.5.1](Modaal_en_knik.md#351-balk-met-welving-elem_beam--pou_d_tg)). Een line3-balk wordt in de middenknoop in twee SEG2-cellen gesplitst (Code-Aster heeft geen kwadratische balk); de resultaten komen op alle drie de knopen terug |
| Welving POU_D_TG-balken bij opleggingen | `auto` | Alleen bij `POU_D_TG`. `auto`: welving vast waar een buigrotatie vastligt (*Fixed support*, inklemming), vrij bij een vorkoplegging (alleen verplaatsingen en de rotatie om de balkas vast) en elders; `free`: overal vrij; `blocked`: vast in elke opgelegde knoop ([Modaal en knik §3.5.1](Modaal_en_knik.md#351-balk-met-welving-elem_beam--pou_d_tg)) |

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
`PETIT` (WARNING; KNOWN_BUGS 11), behalve met `elem_beam` = `POU_D_T_GD` (`GROT_GDEP`,
grote rotaties). Details:
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

**Formules.** Een waarde als formule (Mecway: Formula) die alleen van de tijd t
afhangt, bemonstert de bridge zoals Mecway voor CCX doet: 10001 tijden van 0 tot de
Time period, daarna alleen de punten waarmee de lijn hoogstens 0,01% van het bereik
afwijkt; het resultaat is een `DEFI_FONCTION`. De eenheden uit Mecway (waarde, tijd in
s of min) worden toegepast; een formule zonder t is een gewone waarde. Formules die de
bridge niet kan lezen, worden gemeld (ERROR) en niet meegenomen. Toegestaan:
`+ - * / ^`, haakjes, `pi`, `e`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`,
`log` (natuurlijk), `abs`, `sqrt`, `heaviside`, `unittriangle`, `max`, `min`. In een
lineair statische, modale of knikanalyse geldt de waarde op de eindtijd. Een gekromde
formule (bijv. een sinus) geeft veel tijdspunten en dus veel rekenstappen
(KNOWN_BUGS 104).

*Formules in x, y, z* (plaatsafhankelijk, eventueel ook met t) worden een `FORMULE` van
X, Y, Z (en `INST`) in `AFFE_CHAR_MECA_F`, met x, y, z in de *Position unit* van de
formule (de beginpositie, ook bij grote verplaatsingen). Dat werkt voor:
- **Pressure** en **Traction** op vlakken van volumes en op schaalvlakken. Mecway rekent
  deze formules ook (per vlak 1, 7 of 9 punten); voorbeeld: druk `3*y^2` met
  positie in m en druk in kPa op een vlak van 1 × 2 m geeft 8 kN, in Mecway en in de
  bridge (verificatie LS-40, LS-41). Op DKT/DST-schalen neemt Code-Aster de formule
  in de knopen (kleine afwijking op een grof mesh, LS-44a); `COQUE_3D` is exact.
- **Force**: de formule is, zoals een getal, de totale kracht: per oppervlak f/A op
  vlakken, per knoop f/n op knopen, geëvalueerd op de plaats zelf.
- **Line pressure** op balken (`FORCE_POUTRE`) en schaalranden (`FORCE_ARETE`), bijv. een
  driehoekslast `-1000*x` N/m (LS-43).
- **Displacement** en **Node rotation**: de waarde als formule (in elke knoop), met
  een vaste richting (LS-42).

Mecway 34 zelf legt kracht, line pressure en opgelegde verplaatsing/rotatie met x, y
of z in de formule **niet** op (gemeten: reacties 0); de bridge wel en meldt dat met een
WARNING. Formules in x, y, z werken in statisch, niet-lineair statisch, impliciete
dynamica, modaal en knik; elders, en bij gravity, moment, centrifugaalkracht,
snelheid, frictionless, een richting als formule of druk op schaalranden en
balkuiteinden, meldt de bridge ze (ERROR) en neemt ze niet mee (KNOWN_BUGS 104).

### 4.1 Resultaatvelden

Met *Resultaatvelden naar Mecway* kies je per analyse welke velden de bridge
teruggeeft; minder velden geeft een kleinere `.liml`. Namen in Mecway zijn dezelfde
als die van Mecway's eigen oplossing waar Mecway ze kent.

| Veld | Mecway-variabelen | Code-Aster-veld | Standaard aan bij |
|---|---|---|---|
| `displacements` | `displx/y/z`, `displmag` (ook per mode); `rotx/y/z` op knopen van balken en schalen | `DEPL` | alle mechanische analyses |
| `stresses` | `stressxx` .. `stresszx` (volume-elementen, knoopwaarden en per element-knoop); `beamsixxmin`/`beamsixxmax` (balken met rechthoekige of ronde doorsnede: kleinste/grootste axiale spanning uit N en M, zonder afschuiving en torsie) | `SIGM_NOEU`, `SIGM_ELNO`, `SIPM_ELNO` | statisch, niet-lineair, dynamisch, respons op modale basis, harmonische respons, responsspectrum, vibro-akoestiek (harmonisch) |
| `vonmises` | `vonmises` (volume); `vonmisesu1`/`vonmisesm`/`vonmisesb` (schaal boven/midden/onder) | `SIEQ_NOEU`, `SIEQ_ELNO` | als `stresses` |
| `reactions` | `reactionforcex/y/z/mag`, `reactionmomx/y/z/mag` | `REAC_NODA` | statisch, niet-lineair, dynamisch, responsspectrum |
| `velocities` | `velx/y/z`, `velmag`; `angularvelx/y/z`, `angularvelmag` op knopen van balken en schalen | `VITE` | dynamisch, respons op modale basis |
| `accelerations` | `accx/y/z`, `accmag` (harmonisch: `accampx/y/z`, ω²\|U\|) | `ACCE` (responsspectrum: `ACCE_ABSOLU`) | harmonische respons, responsspectrum, vibro-akoestiek (harmonisch) |
| `plastic_strain` | `plasticstrainxx` .. `plasticstrainzx` (namen van de bridge) | `EPSP_NOEU` | niet-lineair statisch |
| `plastic_strain_eq` | `equivalentplasticstrain` | `VARI_NOEU` V1 | niet-lineair, dynamisch |
| `temperature` | `temperature` (K) | `TEMP` | thermisch |
| `heat_flux` | `heatfluxx/y/z/mag` (knoopwaarden en per elementknoop) | `FLUX_NOEU`, `FLUX_ELNO` | thermisch |
| foutschatter (instelling *Foutschatter*, niet in deze keuzelijst) | `errorestimate`, `errorestimaterel` (volume-elementen, knoopwaarden en per element; namen van de bridge) | `ERME_NOEU`, `ERME_ELNO` | statisch ([`Foutschatter.md`](Foutschatter.md)) |
| vermoeiing (`#ASTER-WOHLER`, niet in deze keuzelijst) | `damage` (schade D), `life` (herhalingen tot D = 1); schalen ook `damage_top`/`damage_bottom`, met een criterium `fatigue_eq`/`fatigue_ratio`; knoopwaarden, namen van de bridge | uit `SIGM_NOEU`/`EPSI_NOEU`/`SIEQ_NOEU` (rainflow, Miner; `aster_fatigue.py`) of `CALC_FATIGUE FATIGUE_MULTI` | statisch, niet-lineair, dynamisch ([`Vermoeiing.md`](Vermoeiing.md)) |
| `strain` | volumes: `lstrainxx` .. `lstrainzx` (lineair), `greenlagrangestrainxx` .. (niet-lineair met grote verplaatsingen, zoals Mecway's L30/D31); schalen: `lstrainxxu`/`m`/`b` .. (boven/midden/onder, globale assen); knoop- en elementknoopwaarden; schuif als hoekverdraaiing γ = 2ε (zoals Mecway) | `EPSI_NOEU`/`EPSI_ELNO` (`EPSG_*`), schalen `EPSI_ELNO` + `EXTR_COQUE` | uit (grotere `.liml`) |
| `beam_forces` | `tensileforce` (N), `sheary`, `shearz` (V langs Mecway's V en W), `torsion`, `bendingmomv`, `bendingmomw`; lokale assen en tekens zoals Mecway; knoop- en elementknoopwaarden | `EFGE_NOEU`, `EFGE_ELNO` | statisch, niet-lineair, dynamisch |
| `shell_stresses` | `stressxxu1` .. `stresszxu1`, idem `m1` (midden) en `b1` (onder): spanningstensor van schalen in globale assen, zoals Mecway | `SIGM_ELNO` na `EXTR_COQUE`, in de job van het lokale schaalassenstelsel naar globaal gedraaid | uit (18 variabelen) |
| `shell_forces` | `forceperlengthu`/`v`/`uv` (N/m), `momentu`/`v`/`uv` (N·m/m; `momentu` > 0 geeft trek boven), `shearuw`/`shearvw` (dwarskracht per lengte) in Mecway's U,V-assen (U = `orientationu*`, een *Element orientation*-kaart of de rand knoop 1→2) | `EFGE_ELNO`, in de job naar Mecway's U,V gedraaid | statisch, niet-lineair |
| `safety_factor` | `factorofsafety` (Mecway toont het item *failure*): tensile strength / von Mises van materialen met Mecway's von Mises-faalcriterium; schalen de kleinste van boven en onder; onbelast 1e6 | uit `SIEQ_NOEU`/`SIEQ_ELNO` (in de job) | statisch, niet-lineair, dynamisch |
| `principal_stresses` | `principal1` >= `principal2` >= `principal3` en `tresca` (= principal1 − principal3), volume-elementen, per elementknoop en als knoopgemiddelde, zoals Mecway ze berekent (Mecway's velden *principal stress* en *Tresca stress*); schalen: `principal1u1` .. `principal3u1`, `trescau1`, idem `m1` (midden) en `b1` (onder), uit de globale spanningstensor van dat vlak (de normaalspanning 0 telt mee, dus één waarde is ongeveer 0) | uit `SIGM_ELNO` (schalen na `EXTR_COQUE`; in de job) | uit |
| `principal_strains` | volumes: `lprincipalstrain1..3`, bij Green-Lagrange (niet-lineair met grote verplaatsingen) `greenlagrangeprincipalstrain1..3`, zoals Mecway; schalen: `lprincipalstrain1u1` .. `lprincipalstrain3b1` (boven/midden/onder); per elementknoop en knoopgemiddelde | uit `EPSI_ELNO`/`EPSG_ELNO`, schalen `EPSI_ELNO` + `EXTR_COQUE` (ook zonder `strain`; in de job) | uit |
| `contact` | `contactpressure` (Pa, positief bij druk; negatief wordt 0), `contactstate` (0 open, 1 gesloten, 2 glijdend) op de slave-knopen | `-LAGS_C` (`DEPL`); status uit `CONT_NOEU` (alleen lineaire contactvlakken) of uit de druk (> 1% van de grootste) | niet-lineair, dynamisch |
| `metallurgy` | `ferrite`, `pearlite`, `bainite`, `martensite`, `austenite` (fasefracties), `hardness` (als de dataset hardheid heeft); namen van de bridge | `META_NOEU`, `DURT_NOEU` | thermisch transient: met `#ASTER-METALLURGIE` altijd mee, alleen route `liml` ([`Lassen.md`](Lassen.md) §10) |
| druk (akoestiek, niet in deze keuzelijst) | `pressure` per mode (Mecway's naam); harmonisch per frequentie ook `pressurei`, `pressuremag`, `pressurephase`, `spl` | `PRES` (vibro-akoestiek: `DEPL` component `PRES`) | akoestiek, altijd ([`Akoestiek.md`](Akoestiek.md)) |

**`shell_forces` staat standaard aan** (statisch en niet-lineair). Heeft het model
schalen, dan meldt de bridge dat eenmaal per run met een WARNING. Het veld voegt 8
variabelen per knoop en per element-knoop toe; de andere resultaten veranderen niet.
Gemeten op een vlakke plaat (lineair statisch, de standaardvelden met en zonder
`shell_forces`):

| Model | Resultaten | `.liml` totaal | Code-Aster-job |
|---|---|---|---|
| 3500 quad4 (DKT) | 1,1 → 3,0 MB | 1,6 → 3,5 MB | 1,3 → 1,6 s |
| 2000 quad8 (`COQUE_3D`) | 1,8 → 4,2 MB | 2,4 → 4,7 MB | 3,2 → 3,6 s |
| 12000 quad4 (DKT) | 3,6 → 10,0 MB | 5,5 → 11,9 MB | 2,9 → 3,8 s |

De hele run (7 tot 10 s, vooral het opstarten van Code-Aster) verschilde niet meetbaar;
het openen van een grotere `.liml` in Mecway duurt langer (niet gemeten). Niet nodig?
Vink `shell_forces` uit op de pagina van de analyse, *Resultaatvelden naar Mecway*.

Bij modaal en knik geeft de bridge alleen de vormen (`displacements`), zoals Mecway;
bij modaal kunnen `stresses`, `vonmises`, `strain`, `beam_forces`, `shell_stresses` en
`shell_forces` per mode mee; andere gekozen velden worden genegeerd (INFO in de log).
Knoopspanningen volgen de Code-Aster-standaard (extrapolatie en middeling per knoop)
en wijken daardoor af van Mecway (KNOWN_BUGS 3).

De extra velden (`strain` .. `contact`) gaan alleen mee als ze gekozen zijn en het
model er iets voor heeft (anders een INFO). Via route `tabel` alleen `strain` (volumes)
en `beam_forces` (knoopwaarden); de rest alleen via route `liml`. Niet in respons op
modale basis, harmonisch, spectrum en de keten thermisch → mechanisch. Mecway's namen,
assen en tekens zijn headless nagelopen in Mecway 34; met Mecway's eigen oplossing
vergeleken in [`Verificatie.md`](Verificatie.md) (LS-30 .. LS-32, NL-30). Grenzen:

- schalen: de assen van Code-Aster (projectie van X of de `VECTEUR` van de groep) en
  van Mecway (rand 1→2, *Element properties* → `orientationu*` of een *Element
  orientation*-kaart in Loads & Constraints, LS-31d) worden per element uit de
  hoekknopen bepaald. Sterk gekromde kwadratische schalen:
  NIET geverifieerd;
- `contactstate` 2 (glijden) komt alleen uit `CONT_NOEU` met wrijving: NIET
  geverifieerd; met hex20/tet10-contactvlakken (integratie niet in de knopen) is er
  geen `CONT_NOEU` en volgt de status uit de druk;
- `factorofsafety`: Mecway rekent hem zelf pas bij het tonen (niet in een headless
  oplossing), dus alleen tegen de definitie (manual v34 par. 8.7) gecontroleerd;
  alleen het von Mises-criterium (Tsai-Wu e.a.: WARNING).

**Controle van massa en reacties** (lineair en niet-lineair statisch). Na de run staat
in de log (INFO) en het statusvak een regel als

```
Controle: massa 78.5 kg, zwaartepunt (0.5, 0.05, 0.05) m; som reactiekrachten FX -770.085, FY 0, FZ 0 N (vergelijk zelf met tekening en belastingen).
```

De massa en het zwaartepunt komen uit `POST_ELEM MASS_INER` over het hele model (met
de doorsneden en schaaldiktes van `CARA_ELEM`), de reacties zijn de som van
`REAC_NODA` over alle knopen in de laatste opgeslagen stap (niet-lineair: de laatste
geconvergeerde tijd). De som van de reacties is gelijk aan **min** de resultante van
de aangebrachte belastingen (in het voorbeeld eigen gewicht +X, reactie −X). Aubry
(2019, §4.13–4.14) noemt de massacontrole de eerste toets van een model: een fout in
dichtheid, dikte of eenheden valt hier direct op. De bridge vergelijkt niet zelf met
de belastingen (drukken op gekromde vlakken en formules maken dat onbetrouwbaar); het
is een getal voor je eigen controle. Krachten tussen onderdelen (contact, koppelingen)
vallen in de som tegen elkaar weg; met een elastische oplegging telt de veerkracht als
reactie (§4.1, `reactions`). Niet bij dynamische, modale en thermische analyses. In
de `.mess`: regels `BRIDGE_STATCHECK` en `BRIDGE_STATREAC`.

### 4.2 Resultaatformules (Solution > Formula)

Een formule die je in Mecway onder *Solution > Formula* toevoegt (bijvoorbeeld
`qf.z/3600/(12^2)` of `sqrt(u.x^2+u.y^2)`), rekent de bridge uit de resultaten van
Code-Aster uit en geeft hem onder de naam van de formule terug, zoals Mecway dat bij zijn
eigen solve doet. Na het laden is hij geldig (niet rood) en toont hij een contour zoals elk
ander veld. De formule moet **voor** de run in het model staan; een formule die je daarna
toevoegt, rekent Mecway zelf uit de geladen resultaten.

Hoe de bridge rekent (zoals gemeten in Mecway 34):

- elk symbool wordt eerst omgerekend naar de eenheid uit het formulevenster (*Units*, de
  `<unit>`-regels in de `.liml`), bijv. `x` in mm, `T` in °F (met verschuiving), `qf.x`
  in Btu/h/ft²; daarna wordt de formule uitgerekend en het getal zo bewaard;
- per knoop, met de knoopwaarden (dezelfde waarden die Mecway voor het veld toont), op de
  knopen waar alle symbolen een waarde hebben (`FR.x`: de reactieknopen); een knoop waar de
  uitkomst niet eindig is (bijv. `1/x` op x = 0), valt weg, zoals in Mecway;
- in elke tijdstap (`t` is de tijd van de stap); een formule met `t` wordt in een statische
  of stationaire oplossing en bij modes niet uitgerekend (Mecway doet dat ook niet);
- de taal is die van Mecway: `+ - * / ^ ( )`, `pi`, `e`, `sin`, `cos`, `tan`, `asin`,
  `acos`, `atan`, `atan2(y,x)`, `log` (natuurlijk), `abs`, `sqrt`, `heaviside(x)`,
  `unittriangle(w,x)`, `max(x,y)`, `min(x,y)`; symbolen zijn hoofdlettergevoelig (`T` =
  temperatuur, `t` = tijd).

| Symbolen | Veld (instelling *Resultaatvelden naar Mecway*) |
|---|---|
| `x`, `y`, `z`, `t` | knooppositie (onvervormd), tijd |
| `u.x`, `r.x`, `v.x`, `av.x`, `a.x` (en y, z) | `displacements`, `velocities`, `accelerations` |
| `FR.x`, `MR.x` | `reactions` |
| `s.xx` .. `s.zx`, `vm` | `stresses`, `vonmises` |
| `e.xx`, `g.xy` .. (lineair), `GLe.xx`, `GLg.xy` .. (Green-Lagrange) | `strain` (standaard uit) |
| `peeq` | `plastic_strain_eq` |
| `T`, `qf.x`, `qf.y`, `qf.z` | `temperature`, `heat_flux` |
| `FI.u`, `FI.v`, `FI.w`, `MI.u`, `MI.v`, `MI.w` | `beam_forces` |
| `cstr.P`, `fos`, `P` | `contact`, `safety_factor`, akoestische druk |
| `s1`, `s2`, `s3`, `tr`; `e1`, `e2`, `e3`; `GLe1`, `GLe2`, `GLe3` (Green-Lagrange) | `principal_stresses`; `principal_strains` (standaard uit) |

Met Green-Lagrange-rek in de oplossing (niet-lineair met grote verplaatsingen) herschrijft
Mecway `e`, `g`, `e1`..`e3` in een formule naar `GLe`, `GLg`, `GLe1`..`GLe3`; de bridge
leest daarvoor dan ook de Green-Lagrange-waarden. Schalen: de spannings- en reksymbolen
(`s.xx`, `s1`, `tr`, `e1`, ...) lezen de velden van volume-elementen; Mecway heeft geen
symbolen voor de schaalvlakken en rekent zo'n formule op schalen ook niet uit.
Niet mogelijk: spanningen in elementcoordinaten (`s.uu`..), schaalkrachten (`ML`, `FL`), Zienkiewicz-Zhu-spanningen,
uitwendige kracht `FE`, rekenergie, elektrische velden en materiaaleigenschappen
(`youngsmodulus` enz.). Zo'n formule blijft in Mecway ongeldig; maak hem na het laden
opnieuw (Mecway rekent hem dan uit). Verificatie FX-01 .. FX-05
([`Verificatie.md`](Verificatie.md)).

| Melding | Oorzaak | Oplossing |
|---|---|---|
| INFO: Formula 'F' (...) -> computed by the bridge as 'formula(2)' | normaal | – |
| WARNING: Formule 'F' (...) kan de bridge niet uitrekenen (symbol 's1' is not supported ...) | symbool van een veld dat de bridge niet schrijft, of een syntaxfout | na het laden: formule verwijderen en opnieuw maken (*Solution > Formula*) |
| WARNING: Formule 'F' (...) heeft het resultaatveld strain nodig, dat ... niet gekozen is | het veld van een symbool staat niet in *Resultaatvelden naar Mecway* | het veld aanvinken op de pagina van de analyse |
| WARNING: Formule 'F' (...): unit '...' of '...' not known: SI used | eenheid die de bridge niet kent (Mecway rekent dan ook in SI) | een andere eenheid kiezen in het formulevenster |
| `.mess`: aster_results_export: WAARSCHUWING: formule ... overgeslagen: ... niet in de resultaten | het veld ontbreekt in deze analyse (bijv. spanningen bij modaal zonder *stresses*) | als hierboven |

## 5. Bestanden in de werkmap

Alle bestanden van een run heten `<model>_<run-id>...`: `<model>` is de naam van het
Mecway-bestand (tekens buiten A-Z, a-z, 0-9, `-` en `_` worden `_`, zonder dubbele of afsluitende
`_`, bijv. `Mijn Model (v2).liml` → `Mijn_Model_v2`; bij een te lang
pad ingekort, §1), `<run-id>` de datum en tijd van de start, bijv.
`ProfielBuigen_20261006_101500.mess`. Zo staan ze bij elkaar en overschrijft een
volgende run niets. In meldingen staat de echte naam. De werkmap is de map uit het veld *Werkmap*, of met *Werkmap naast het model* de submap `<model>_aster` naast het open model (§3).

| Bestand | Inhoud |
|---|---|
| `<model>_<run-id>_bridge_log.txt` | log van de bridge (INFO/WARNING/ERROR per stap); `bridge_log.txt`: alleen meldingen buiten een run (bijv. *Resultaten...*) |
| `<model>_<run-id>.mail` | het mesh (ASTER-formaat) |
| `<model>_<run-id>.comm`, `<model>_<run-id>.export` | Code-Aster-invoer; met `run_aster.bat <model>_<run-id>.export` opnieuw te draaien |
| `<model>_<run-id>.mess` | berichten van Code-Aster (fouten, alarmen, tabellen met `UNITE=6`) |
| `<model>_<run-id>_console.txt` | volledige console-uitvoer van Code-Aster (ook Python-fouten) |
| `<model>_<run-id>_done.txt` | eindmarkering met de exitcode van `run_aster` (§2 stap 5); bestaat alleen kort, de bridge verwijdert hem na de run |
| `<model>_<run-id>_results.xml` | **de resultaten** in Mecway's eigen formaat (route `liml`); de bridge zet ze in de `.liml` en laat het bestand staan, zodat je ze later opnieuw kunt inladen (§5.1) |
| `<model>.liml.bak` | de `.liml` van vóór het inlezen of verwijderen van resultaten |
| `<model>_<run-id>.resu` | resultaattabellen, alleen bij route `tabel` |
| `<model>_<run-id>.rmed` | resultaten in MED (ParaView/Salome), alleen met *MED-bestand voor ParaView*; de knop *ParaView* van het convergentiescherm opent hem (met AdvancedToolsHub in MWHub Post) |
| `<model>_<run-id>.pvd`, `_<k>.vtu` | resultaten in VTK (ParaView), alleen met *VTU/PVD-bestanden voor ParaView*; met bezwijken ook de celvelden `BEZWEKEN` (0 intact, 1 bezweken) en `T_BEZWIJK` |
| `<model>_<run-id>_beams.json` | balkdoorsneden en lokale assen voor MWHub Post (`mwhubpost-beams/1`, beschrijving bovenin `Scripts/bridge_beams.py`), met *VTU/PVD-* of *MED-bestand voor ParaView* en balken in het model; de snedekrachten per element-uiteinde staan als `EFGE_<N/VY/VZ/MT/MFY/MFZ>_1/_2` in de VTU |
| `<model>_<run-id>_knopen.csv` | knoopvelden over de tijd per benoemde knoopselectie (met de VTU-export) |
| `<model>_<run-id>_job.json` | opdracht voor MWHub Post (`mwhubpost-job/1`), geschreven door de knop *ParaView* als AdvancedToolsHub gevonden is |
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
bij (alleen het mesh wordt gecontroleerd). *Inladen* zet ook de Saved monitor van die run
in het model (§5.2), als de `.mess` ervan nog in de werkmap staat.

### 5.2 Code-Aster-uitvoer in Mecway (Saved monitor)

Met route `liml` zet de bridge de uitvoer van de Code-Aster-run in de `.liml` als Mecway's
eigen item *Saved monitor* (boom, onder *Solution*; Mecway-handleiding §10.3), hetzelfde item
dat Mecway gebruikt voor de voortgangsmeldingen van zijn eigen solver. Het blijft in het model
als je de Code-Aster-vensters sluit, het model opslaat of aan iemand anders geeft. Instelling
*Code-Aster-uitvoer als Saved monitor in de .liml* (`save_monitor`, pagina Algemeen):

- `summary` (standaard): het model, de run, het pad en de grootte van de volledige
  `<model>_<run-id>.mess`, de Code-Aster-versie en de regel `DIAGNOSTIC JOB`; elk meldingskader
  met een fout of alarm (`<EXCEPTION>`, `<F>`, `<S>`, `<E>`, `<A>`) één keer, met het aantal
  keren dat het voorkwam; de lijst met alarmen die Code-Aster aan het einde geeft;
  Python-fouten uit `<model>_<run-id>_console.txt`; bij een niet-lineaire analyse elke
  tijdstap met niveau, Newton-iteraties en geconvergeerd/mislukt (de eerste en laatste 25, plus
  elke mislukte), anders de voortgangsregels; de eigen regels van de bridge (massacontrole,
  modes, resultaatbestand); de tijd per commando en het geheugen; het einde van de `.mess`.
  Hoogstens 400 000 tekens.
- `full`: de hele `.mess`; boven 4 miljoen tekens het eerste miljoen en de laatste drie
  miljoen, met een opmerking ertussen (de `.mess` van een lange niet-lineaire run kan tientallen
  MB zijn, en de `.liml` moet snel open gaan).
- `off`: geen Saved monitor.

De meldingen zijn die van Code-Aster zelf (Frans). Een run zonder resultaten (fout, gestopt)
krijgt de Saved monitor alleen als het model nog geen resultaten heeft: de bridge schrijft dan
een solution met alleen de monitor (Mecway toont een solution zonder resultaatvelden) en opent
het model opnieuw. Heeft het model al resultaten (van een eerdere run of van Mecway's eigen
solve), dan laat de bridge het model ongemoeid, zodat die resultaten niet door een lege solution
worden vervangen; de log noemt de `.mess` van de mislukte run, en de meldingen staan zoals
voorheen in het statusvak en het convergentiescherm. Een solution met alleen de monitor van een
eerdere mislukte run telt niet als resultaten. Met route `tabel` is er geen Saved monitor
(KNOWN_BUGS 122) (die route
vult Mecway's bestaande solution via de API, die het item niet kan toevoegen); de `.mess` blijft
in de werkmap staan. Reken je het model daarna met Mecway's eigen solver, dan vervangt Mecway de
tekst door zijn eigen voortgangsmeldingen. *Uit model verwijderen* (§5.1) haalt de tekst ook
weg; het item zelf blijft (leeg).

## 6. Fouten lezen

- **Melding vóór Code-Aster** ("Schrijven van het mesh mislukt", "Genereren
  solver-bestanden mislukt", "Geen materialen gevonden in het model", "De werkmap is
  te lang", analysetype niet ondersteund): zie de ERROR-regels in
  `<model>_<run-id>_bridge_log.txt`.
- **Start lijkt niets te doen**: het startscherm komt terug met de reden in het
  statusvak onderaan. "De map van het open model bestaat niet meer": het
  model is geopend uit een map die sindsdien verplaatst of verwijderd is, zodat Mecway
  het niet kan opslaan; sla het op met *File > Save As...* in een bestaande map en
  klik opnieuw op Start.
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
- **Na het sluiten van de vensters**: de meldingen van de laatste run staan in het model
  als item *Saved monitor* onder *Solution* (§5.2), met het pad van de volledige `.mess`.
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

- **Aanname:** het `.liml`-formaat van Mecway 33 en 34 (getest); andere versies zijn
  niet getest (WARNING, [`Na_een_update.md`](Na_een_update.md)).
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

- Aubry, J.-P. (2019). *Beginning with code_aster*, versie van 29 januari 2019,
  §4.13–4.14: de massa (`POST_ELEM MASS_INER`) en de som van de reacties
  (`REAC_NODA`, `POST_RELEVE_T RESULTANTE`) als eerste controle van een model (§4.1).
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
