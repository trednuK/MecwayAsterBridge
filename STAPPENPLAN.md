# STAPPENPLAN.md – uitbreidingen met Code-Aster

Wensenlijst van de gebruiker (6 okt 2026) als uitvoerbaar plan, herzien na een
crit-review. Uitvoeren: typ in Claude Code **`/stappenplan`** (de eerste open stap in
tabelvolgorde waarvan de voorwaarde klopt; daarna door met de volgende) of
**`/stappenplan S4a`** (een bepaalde stap; `S10` = de eerste open S10-deelstap). Het
commando staat in `.claude/commands/stappenplan.md` en volgt de werkwijze hieronder.

Commit-hashes in de kolom Resultaat van stappen tot en met V2026.1 verwijzen naar de
ontwikkelgeschiedenis vóór de eerste openbare versie; die staan niet in deze repo.

## Status

**De tabelvolgorde is de bouwvolgorde** (keuze gebruiker: S1, S10, S2, S3, S4, S6,
S7, S8, S5, S9).

| Id | Stap | Status | Voorwaarde | Resultaat |
|---|---|---|---|---|
| S0 | Hoofdvenster: navigatielijst links i.p.v. tabbladen | klaar | – | 1741e04 (merge b0afe8e); in Mecway getest 6 okt (navigatie, Documentatie, run met resultaten) |
| S1 | Foutschatter (discretisatiefout) | klaar | – | 7a0cda0 (merge e15b36b); in Mecway getest: velden zichtbaar, contour per element |
| S10a | Modaal met voorspanning (KNOWN_BUGS 49) | klaar | – | aa19b0c; in Mecway getest (MP-04: per mode −0,52/0/−0,09/0% t.o.v. Mecway) |
| S10b | Spanningen per mode; effectieve massa voor rotaties | klaar | – | 2c8b7cd; via door Mecway opgeslagen .liml getest (S11, identiek) |
| S10c | Niet-lineaire knik (`CRIT_STAB`), knikvorm als imperfectie | klaar | – | 4d831b4; via door Mecway opgeslagen .liml getest (S11, identiek) |
| S10d | Respons op modale basis (Mecway D30 *mode superposition*) | klaar | – | e10121a; transiënt, harmonisch afgesplitst als S10h; via door Mecway opgeslagen .liml getest (S11, identiek) |
| S10e | Spectrumanalyse (aardbeving, schok) | klaar | S10d | be706a0; via door Mecway opgeslagen .liml getest (S11, identiek) |
| S10f | Demping: complexe modes | klaar | – | 6038d88; via door Mecway opgeslagen .liml getest (S11, identiek) |
| S10g | Cyclische symmetrie (`MODE_ITER_CYCL`) | klaar | – | c668f42; in Mecway getest 7 okt (CY-01: hele wiel, 25,74..333,1 Hz = verificatie) |
| S10i | Cyclische symmetrie: het hele wiel in Mecway (vormen uitbreiden naar N sectoren in `<solution>`, zoals Mecway) | klaar | S10g | b030096; instelling `cyclic_full_wheel` (standaard aan); in Mecway getest 7 okt (CY-01: 12 sectoren, 960 knopen in Mecway) |
| S10h | Harmonische respons in het frequentiedomein (`DYNA_VIBRA` `HARM`, op modale basis) | klaar | S10d | 5ce93a2; eigen analyse harmonic_3d; via door Mecway opgeslagen .liml getest (S11, identiek) |
| S2 | Akoestiek: holtemodes (`PHENOMENE='ACOUSTIQUE'`) | klaar | – | 7c360ec; via door Mecway opgeslagen .liml getest (S11, identiek) |
| S2b | Akoestiek: impedantieranden (complexe modes, KNOWN_BUGS 55) | klaar | S2 | stap-S2b; Code-Aster-matrices + scipy in de job (`aster_acoustic_complex.py`); via door Mecway opgeslagen .liml getest (S11, identiek) |
| S3a | Akoestiek: harmonisch drukveld (`ACOUSTIQUE`, `DYNA_VIBRA`) | klaar | S2 | 1072641; in Mecway getest 7 okt (AH-08: microfoon 89,2029 dB = verificatie, drukfaseveld) |
| S3b | Vibro-akoestiek (`MECANIQUE`, `3D_FLUIDE` + `FLUI_STRU`, `U_P_PHI`) | klaar | – | b6cfd07; gekoppelde modes, harmonisch afgesplitst als S3c; via door Mecway opgeslagen .liml getest (S11, identiek) |
| S3c | Vibro-akoestiek harmonisch (`DYNA_VIBRA` `HARM`, `3D_FLUI_ABSO`, ahlv101a) | klaar | S3b | a70dd4c; eigen analyse vibroacoustic_harm_3d (zelf kiezen); via door Mecway opgeslagen .liml getest (S11, identiek) |
| S4a | Lassen: transiënt thermisch met bewegende bron | klaar | – | 75ae3f2; `#ASTER-LASBRON` + Mecway-formules + temperatuurafhankelijke λ/c; in Mecway getest 7 okt (WE-02: 100,0% van 500 W, temperatuur en warmtestroom) |
| S4b | Lassen: keten thermisch → mechanisch (restspanning, vervorming) | klaar | S4a | 3a7a941; Thermal stress in T31 + `#ASTER-MATERIAAL`; via door Mecway opgeslagen .liml getest (S11, identiek) |
| S4c | Lassen: toevoegmateriaal | klaar | S4b | 7f2551a; `geboorte=` in `#ASTER-LASBRON` (quiet element), thermisch + mechanisch; via door Mecway opgeslagen .liml getest (S11, identiek) |
| S6a | Breukmechanica: gemeshte scheur (`CALC_G`, `POST_K1_K2_K3`) | klaar | – | 5c33ac7; via door Mecway opgeslagen .liml getest (S11, identiek) |
| S6b | Breukmechanica: XFEM | klaar | S6a | 2740a4c; `#ASTER-XFEM` (CIRKEL/ELLIPSE/RECHTHOEK/HALFVLAK), velden via POST_CHAM_XFEM + PROJ_CHAMP; via door Mecway opgeslagen .liml getest (S11, identiek) |
| S7 | Adaptieve verfijning (Mecway `refine_x2` of HOMARD) | klaar | S1 | cac0922; Mecway-route (`bridge_adapt.py`), HOMARD niet gebouwd; via door Mecway opgeslagen .liml getest (S11, identiek) |
| S8 | Vermoeiing | klaar | – | 0a889dd; `#ASTER-WOHLER`, rainflow + Miner, velden damage/life; in Mecway getest 7 okt (VM-02b: damage 0,004329 = referentie) |
| S8b | Vermoeiing: multiaxiaal (`CALC_FATIGUE FATIGUE_MULTI`, Dang Van/Matake/Crossland), schalen, rek-gebaseerd (Manson-Coffin) | klaar | S8 | 04367b8; `#ASTER-VERMOEIING criterium`, schalen boven/onder, Manson-Coffin in `#ASTER-WOHLER`; VM-08..11; via door Mecway opgeslagen .liml getest (S11, identiek) |
| S5 | Lassen: metallurgie | klaar | S4b | d8d8f31; `#ASTER-METALLURGIE` (datasets 16MND5/mtlp103a, HSNV101A), CALC_META, optie META_P_IL in de keten; via door Mecway opgeslagen .liml getest (S11, identiek) |
| S5b | Lassen: metallurgie vervolg (ontlaten, TRIP, kinematische versteviging) | open | S5 | niet gebouwd; vraag aan de gebruiker of dit gewenst is (zie §S5) |
| S9 | Loadcase-combinaties via Mecway-configuraties (go/no-go) | vervallen | – | no-go: een Mecway-configuratie zet lasten alleen aan/uit, geen factor; combinaties niet in Mecway in te stellen; werkwijze per configuratie in Handleiding §4 |
| S11 | Afsluiting: crit-review verificatie, docs nalopen met de bridge, integrale controle, push naar `main` | klaar | alle andere stappen klaar en op `develop` | 7 okt: crit-review op Fable (gate verwerkt: 8742df0), instellingen/tooltips/aannames (feabce4), docs met de bridge nagelopen (345c400, 088244e, 3c336e4), KB 74/84/85/86 opgelost, alle 270 cases via door Mecway opgeslagen .liml identiek (f1539a2), GUI-steekproeven VM-02b/CY-01/AH-08/WE-02, eindregressie zie Verificatie.md §3 |
| S13 | Orthotrope en anisotrope materialen, met *Element orientation* als materiaalrichting | open | – | gekozen door de gebruiker 15 okt (C1) |
| S14 | Hyperelastisch materiaal (Neo-Hooke, Mooney-Rivlin) | open | – | gekozen door de gebruiker 15 okt (C7) |
| S15 | Pre-tension section (boutvoorspanning) | open | – | gekozen door de gebruiker 15 okt (C8) |
| S16 | 2D- en axisymmetrische analyses (S20, D20, SA0, ook thermisch en akoestiek 2D) | open | – | gekozen door de gebruiker 15 okt (C9) |
| S17 | Lasten op balkzijvlakken; hydrostatische druk op schaalranden (KNOWN_BUGS 5) | open | – | gekozen door de gebruiker 15 okt (C10) |
| S18 | Nieuwe Code-Aster-versie (18) testen | later | Code-Aster 18 voor Windows beschikbaar | versiewaarschuwing en werkwijze klaar (`bridge_version.py`, docs/Na_een_update.md) |
| – | Rotordynamica | later | – | |
| – | Grond-constructie-interactie (MISS3D) | niet gepland | – | |
| – | Hex-blokmesher als Tools-script | niet gepland | – | |
| – | Topologie-optimalisatie | niet gepland | – | |

Status: **open**, **klaar** (met commit), **vervallen** (met reden), **later** /
**niet gepland** (slaat `/stappenplan` over, behalve als je de stap noemt). Een stap is
*bezig* als er een branch `stap-<id>` bestaat (zie A.4).

## Werkwijze per stap

### A. Voorbereiden
1. `git fetch`; maak een worktree op een nieuwe branch `stap-<id>` vanaf `develop`
   (`git worktree add … -b stap-<id> develop`, of EnterWorktree). In de hoofdcheckout
   (de map waaruit Mecway de scripts start) wordt niet bewerkt: daar draait
   Mecway (en een hook blokkeert edits).
2. Lees **daarna, vanaf schijf in de worktree** (niet uit de geladen context, die kan
   van een oude commit zijn): `AGENTS.md`, `KNOWN_BUGS.md`, dit bestand, en de docs van
   het onderwerp.
3. Controleer de voorwaarde. Klopt die niet: neem (zonder argument) de volgende open
   stap en meld welke stap is overgeslagen en waarom.
4. Bestaat `stap-<id>` al: loopt hij voor op `develop`, rebase en ga verder; is hij al
   gemerged, verwijder hem en begin opnieuw.
5. Andere sessies (`git worktree list`, branches voor op `develop`, ongecommitte
   wijzigingen): een **conflict** is hetzelfde onderwerp, of ongecommitte wijzigingen in
   dezelfde functies (bekijk de diff). Alleen dezelfde gedeelde bestanden
   (`bridge_utils.py`, `bridge_gui.py`, `bridge_docs.py`, `KNOWN_BUGS.md`, docs) is
   **geen** stopreden: rebase en los conflicten op.

### B. Uitzoeken
Leg de invoerroute niet aan de gebruiker voor: zoek uit, kies, bouw en documenteer.
Volgorde voor de invoer:
1. **Mecway zelf**: maak een klein testmodel (in Mecway of met
   `TestFiles/Verificatie/verif_lib.py`) en lees de tags in de `.liml`. Bronnen:
   `C:\Program Files\Mecway\Samples` en `Tutorials`, `manual.pdf` (met `pdftotext`),
   de tagnamen in `mecway.exe` (UTF-16), de API in
   `<hoofdcheckout>\API_reference Mecway.txt`
   (gitignored; staat niet in een worktree).
2. **Speciale groepsnamen**: een Mecway-selectie, -elset of -onderdeel met een vast
   voorvoegsel (bijv. `LUCHT_`, `KOPPEL_`, `LASNAAD_`, `SCHEUR_`) wijst elementen of
   vlakken aan. Herken op de **oorspronkelijke** Mecway-naam
   (`bridge_mesh._aster_names` hernoemt voor Code-Aster).
3. **Eigen `#ASTER-...`-sleutelwoord** in `bridge_custom.py`: nieuwe soort in `_KINDS`,
   `empty()` en `parse()`; voorbeeld in `docs/ASTER_regels_voorbeelden.md`.

Code-Aster: de catalogus (`…\17.4\lib\aster\code_aster\Cata\Commands\*.py`), de U-docs
(v17.4-site; lokaal alleen v14/v15 als achtergrond) en de testcases in
`%LOCALAPPDATA%\code_aster\v2025\17.4\share\aster\tests` (draaien:
`run_aster.bat --ctest <naam>.export`). **Testcases zijn een syntaxbron; de
bridge-verificatie is altijd 3D** (de bridge kent geen 2D/AXIS, `MECWAY_ANALYSIS_TYPES`).
Onderbouw gedrag in commentaar met een bron, anders "NIET geverifieerd" (AGENTS.md).

### C. Bouwen
- Uitbreidingstabel in `AGENTS.md`: analyse = template + builder +
  `SOLVER_BUILDERS_ASTER` + `CONFIG_BRIDGE["analyses"]` + `MECWAY_ANALYSIS_TYPES`; veld =
  `RESULT_FIELD_SPECS` + `FIELD_TABLE` in `aster_results_export.py`; instelling =
  `CONFIG_BRIDGE` + `GENERAL_SPECS`/`ANALYSIS_SPECS` + uitleg in `bridge_glossary.py`.
- `SOLVER_BUILDERS_ASTER` heeft het Code-Aster-commando als sleutel (`CALC_MODES` is
  bezet door `_build_modal`). Een **variant op een bestaand commando**: dispatch binnen
  de builder op een analysesleutel (zoals `type_resu` bij modaal/knik), geen tweede
  entry. Een **keten** (statisch → modes, thermisch → mechanisch): één eigen template met
  beide solves; `export_results` krijgt het hoofdresultaat als `res`, de rest via
  `extra_results`.
- Een nieuwe pagina in het hoofdvenster komt vanzelf in de navigatielijst
  (`new_page(titel, groep)` in `bridge_gui.py`).
- IronPython 2.7 in `Scripts/` (behalve wat in de Code-Aster-job draait), teksten via
  `tr()` in NL en EN (standaardtaal Engels).
- Duidelijke meldingen boven automatisch rechttrekken: zegt de invoer iets onmogelijks,
  geef een ERROR met de oplossing.

### D. Verifiëren
NAFEMS-stijl: **weinig cases, maar bewijzend**, elk met een getal en een tolerantie.
1. Syntaxcheck en rooktest uit `AGENTS.md`; Python 2.7-controle met Mecway's
   IronPython: `powershell -ExecutionPolicy Bypass -File TestFiles/Tools/run_ipy.ps1
   -Script <script.py>`.
2. Een echte Code-Aster-run per nieuwe route (diagnose OK, of een verklaard alarm).
3. Referenties: (a) een **analytische controle** (Roark's Formulas for Stress and
   Strain, handboekformules) op een eenvoudig 3D-model; (b) waar het kan **Mecway's
   eigen oplossing**, headless: `python TestFiles/Tools/mw_solve.py <in.liml> <uit>`;
   (c) waar nuttig een **Code-Aster-testcase**: de TEST_RESU-waarden nagebootst op een
   3D-model. Het klaar-criterium van de stap noemt de tolerantie.
4. Nieuwe cases: `TestFiles/Verificatie/tests_<groep>.py` en een sectie in
   `docs/Verificatie.md` + `docs/en/Verification.md` (opzet zoals de bestaande: model,
   referentie met bron, resultaat, verschil). Er staan geen `doc_*.md` meer in
   `TestFiles/Verificatie`.
5. Regressie: `VERIF_WORK=<eigen scratchmap>` zetten (de standaardmap wordt door andere
   sessies gewist) en `python TestFiles/Verificatie/run_verificatie.py` volledig draaien.
   **Lat**: basislijn 1639 van 1643 controles OK (277 testcases), 4 BEKEND (KNOWN_BUGS
   43: 3 in NL-03a; KNOWN_BUGS 83: 1 in BR-10), 0 NOK/FOUT (volledige regressie op
   bridge 71ecf2f, 2026-10-15, na verlijmd contact tussen schalen LS-07:
   `TestFiles/Verificatie/resultaten/resultaten.md`). Na de stap: 0 NOK/FOUT en geen eerder OK-controle die nu
   BEKEND/NOK is. Gewijzigde `modellen/` en `resultaten/` meecommitten; de samenvatting
   in `docs/Verificatie.md` §3 en de EN-versie bijwerken.
6. GUI: offscreen met `TestFiles/Tools/gui_cap.py` (via `run_ipy.ps1`). Een test in
   de Mecway-GUI zelf kan pas **na F.2** (Mecway draait de hoofdcheckout), alleen als het
   scherm vrij is (open Mecway-instantie gebruiken, geen tweede starten). Faalt hij: een
   herstel-commit op `develop` en de status terug naar open.

### E. Documenteren
- Gebruikersdoc `docs/<Onderwerp>.md` + `docs/en/<Topic>.md`, opgenomen in `DOCS` van
  `bridge_docs.py` en verwezen vanuit `Handleiding.md`/`UserGuide.md`. Opbouw zoals
  `docs/Modaal_en_knik.md`: werkwijze in Mecway stap voor stap, instellingen met
  standaard en **wanneer aanpassen**, hoe de bridge vertaalt, interpretatie, wat niet
  kan, en een tabel **meldingen → oorzaak → oplossing** zodat de gebruiker fouten zelf
  kan oplossen. De juiste instellingen die bij het verifiëren gevonden zijn, horen hier.
- Instellingen in `docs/Standaardinstellingen_en_aannames.md` (+EN); speciale
  groepsnamen en `#ASTER`-sleutelwoorden met voorbeelden in
  `docs/ASTER_regels_voorbeelden.md` (+EN); nieuwe Code-Aster-meldingen in
  `docs/Foutmeldingen_CodeAster.md` (+EN); beperkingen in `KNOWN_BUGS.md`.

### F. Afronden
1. Werk de statusregel bij (klaar + commit, of vervallen + reden) en vul
   **Bevindingen** van de stap aan (gekozen invoerroute, gemeten verschillen, open
   vragen voor de gebruiker).
2. Commit (Nederlands), rebase op `develop`, en fast-forward `develop` in de
   hoofdcheckout:
   - `git -C <hoofd> status --porcelain`. Alleen `Scripts/bridge_utils.py` gewijzigd
     (een opgeslagen instelling van de gebruiker): bewaar de diff
     (`git -C <hoofd> diff Scripts/bridge_utils.py > <scratch>/settings.patch`), dan
     `git -C <hoofd> checkout -- Scripts/bridge_utils.py`, `merge --ff-only stap-<id>`,
     en zet de instellingswaarden daarna **met de hand** terug in het
     `CONFIG_BRIDGE`-blok (regel voor regel; geen `git apply` als de stap dat blok
     wijzigde). Laat de teruggezette instelling ongecommit.
   - Andere wijzigingen in de hoofdcheckout: niet mergen, stoppen en melden.
   - Push **alleen `develop`**, nooit `main`.
3. Opruimen: `git worktree remove <pad>` en `git branch -d stap-<id>`.
4. Doe de Mecway-GUI-test als die nodig is (D.6).
5. Geen stopreden: begin direct aan de volgende open stap in dezelfde sessie. Vragen
   voor de gebruiker verzamel je in Bevindingen en in het eindrapport, niet tussendoor.

**Stoppen en melden** als een voorwaarde niet klopt, een andere sessie aan hetzelfde
onderwerp werkt, de hoofdcheckout andere wijzigingen dan `bridge_utils.py` heeft, of de
verificatie faalt en niet op te lossen is. Is een stap groter dan één run: bouw een
bruikbaar, geverifieerd deel en splits de rest als nieuwe regels in de statustabel.

### S11 – Afsluiting (opdracht gebruiker, 7 okt 2026)
Pas als alle andere stappen klaar en op `develop` gepusht zijn, in deze volgorde:
1. Eén crit-review gericht op de verificatie (zie hieronder) en de bevindingen verwerken;
   daarna alle documentatie nalopen door de beschreven instellingen met de bridge uit te voeren.
2. **Integrale controle** van alle functionaliteit: alles werkt; alle aannames en verborgen
   instellingen staan in de documentatie en waar mogelijk in de tooltips bij de invoervelden;
   de documentatie is consistent; alle testcases werken vanuit modellen die **in Mecway zijn
   opgebouwd** en via de bridge in Code-Aster gerekend (GUI-route). Gevonden fouten oplossen.
   Vragen bewaren tot er niets meer kan zonder iets te breken.
3. Daarna (en alleen dan) mag `develop` naar `main` gepusht worden (toestemming gebruiker).

**Aan het eind van een reeks stappen** (opdracht gebruiker): één crit-review gericht
op de verificatie (genoeg Code-Aster-testcases en analytische controles om de werking
te bewijzen, vastgelegd in `docs/Verificatie.md`), de bevindingen verwerken, en daarna
**alle documentatie nalopen door de beschreven instellingen met de bridge zelf uit te
voeren**.

## Stappen

### S0 – Hoofdvenster: navigatielijst links
Klaar (1741e04): de TabControl is vervangen door een getekende navigatielijst links
(groepen Instellingen / Analyses / Hulp) met de pagina rechts; `new_page(titel, groep)`
is het enige registratiepunt. Offscreen getest in NL en EN, opslaan byte-voor-byte gelijk
aan de oude versie. **Open:** test in de Mecway-GUI (modeless gedrag, muis).
**Bevindingen:** het dubbele kopje "Algemeen" onder de paginatitel heet nu "Taal en
installatie". Mecway-GUI-test op 6 okt niet gedaan: toegang tot Mecway geweigerd
(gebruiker afwezig).

### S1 – Foutschatter
**Doel:** de geschatte discretisatiefout als veld in Mecway en de globale relatieve fout
in de log, zodat je ziet waar de mesh te grof is.
**Code-Aster:** `CALC_ERREUR`: `ERME_ELEM`/`ERME_ELNO`/`ERME_NOEU` (residu; componenten
`ERREST`, `NUEST`), `ERZ1_ELEM`/`ERZ2_ELEM` (Zienkiewicz-Zhu), `QIRE_*` (doelgericht;
vraagt een duaal probleem `RESU_DUAL`, niet standaard), `ERTH_*` (thermisch). 3D-testcases:
`sslv07a`, `sslv111f` (ERZ1), `sslv153a` (ERME_NOEU, QIRE), `ssnv301a`. (`forma01b`,
`forma20a` zijn C_PLAN: alleen syntax.)
**Route:** `ERME_NOEU` → `nodevariable` (KNOOP in `FIELD_TABLE`); `ERME_ELNO` →
`elementnodevariable` (ELEMKNOOP, alleen volume-elementen). Globale relatieve fout uit
de .mess ("ESTIMATEUR D'ERREUR EN RESIDU EXPLICITE … RELATIVE").
**Uitzoeken:** welke elementen/analyses (schalen, balken, `LINE_QUAD`, niet-lineair,
thermisch); of Mecway een eigen variabelenaam toont (Mecway-GUI na F.2).
**Klaar als:** op de reeks `LS-02-h8-n1…n16` (TestFiles/Verificatie) daalt de globale
relatieve fout monotoon met orde ≈ 1 (±0,2); de fout is het grootst bij de inklemming;
regressie volgens D.5.
**Bevindingen:** Invoerroute: geen invoer nodig, instelling `error_estimator`
(lin_static_3d, standaard aan; ook `#ASTER-OPTIE`). Alleen `ERME` op volume-elementen bij
`MECA_STATIQUE`; de bridge zet de vrije vlakken zelf als randelementen met druk 1e-14
(Code-Aster ziet een onbelast vlak als opgelegd; 0 werkt niet) en rekent de schatter in
een eigen model/last/resultaat (balken: CALCUL_37; meerdere drukken: INDICATEUR_7/8;
puntlasten: INDICATEUR_6/8; reuse met andere EXCIT: CALCULEL_39). Velden
`errorestimate`/`errorestimaterel` (knoop en per element), globale fout uit de `.mess`
in log en statusvak. FS-01 (hex8): orde 0,88/0,96/0,96, effectiviteit 1,3-2,2; FS-02
(hex20): orde ~1,9; FS-03 = sslv153a exact. Niet: niet-lineair, thermisch (ERTH),
schalen/balken, ZZ en QIRE (KNOWN_BUGS 51).

### S10 – Modaal en knik uitbreiden
Lees eerst `docs/Modaal_en_knik.md` en KNOWN_BUGS 46-49. Bestaande route:
`_build_modal` (één builder voor modaal en knik, dispatch op `type_resu`),
`AsterTemplate_CalcModes.comm`.

- **S10a – Modaal met voorspanning.** Mecway rekent een frequentieanalyse mét
  belastingen als voorgespannen (*stress stiffening*); de bridge negeert de lasten nu
  (WARNING). Keten: `MECA_STATIQUE` → `SIEF_ELGA` → `RIGI_GEOM` → `CALC_MODES` met
  K + Kg (dezelfde stappen als de knikroute, dispatch in `_build_modal`).
  **Klaar als:** frequenties binnen 1% van headless Mecway met belasting
  (`mw_solve.py`), plus een analytische controle: snaar/balk onder trek
  (f = f0·sqrt(1 + P/Pcr) of een snaarformule, Roark/Blevins), ≤ 1%.
- **S10b – Spanningen per mode; effectieve massa voor rotaties.** Code-Aster heeft
  alleen `MASS_EFFE_UN_DX/DY/DZ`; rotaties zelf berekenen (participatie met starre
  rotatievectoren om het zwaartepunt) of documenteren dat het niet kan. Spanningen per
  mode: `CALC_CHAMP` op het modale resultaat; toon ze alleen als Mecway ze kan tonen.
  **Klaar als:** de som van de effectieve rotatiemassa over alle modes nadert het
  massatraagheidsmoment (≤ 1% bij voldoende modes) op een balkmodel.
- **S10c – Niet-lineaire knik.** `CRIT_STAB` in `STAT_NON_LINE` (testcases `ssll105d`,
  `ssll105e`, `ssll105f`) en een knikvorm als imperfectie (`MODI_MAILLAGE`
  `DEFORME`, schaalbare amplitude) vóór een niet-lineaire analyse. Invoer zoeken in
  Mecway/`#ASTER-OPTIE`. **Klaar als:** `CRIT_STAB` op een Euler-kolom binnen 2% van
  de lineaire knikroute en van pi²EI/(kL)²; met imperfectie daalt de draagkracht
  (Southwell/Ayrton-Perry als controle).
- **S10d – Respons op modale basis.** Mecway *Dynamic Response* (D30) heeft een optie
  *mode superposition* (manual §6.4); D30 staat nog niet in `MECWAY_ANALYSIS_TYPES`.
  Code-Aster `DYNA_VIBRA` `BASE_CALCUL='GENE'`, harmonisch en transiënt (testcase
  `forma12d`: `MACRO_ELAS_MULT` als statische correctie). Tags van D30 eerst in een
  Mecway-model lezen. **Klaar als:** 1-vrijheidsgraad-achtig model (massa op veer/balk)
  binnen 1% van de analytische respons (dynamische vergrotingsfactor), en gelijk aan
  headless Mecway D30 (≤ 2%).
- **S10e – Spectrumanalyse.** `COMB_SISM_MODAL` (testcase `sdld25a`); invoer van het
  spectrum uitzoeken (Mecway-tabel of `#ASTER`). **Klaar als:** `sdld25a`-waarden binnen
  1% op een 3D-nabouw, en SRSS/CQC met de hand nagerekend op een 2-modesysteem.
- **S10f – Demping: complexe modes.** Rayleigh/modale demping in `CALC_MODES` (complexe
  modes) of als modale dempingsfactor in S10d. **Klaar als:** dempingsverhouding van
  een 1-vrijheidsgraadsysteem binnen 1% van de opgegeven waarde.
- **S10g – Cyclische symmetrie.** Mecway heeft een *Cyclic symmetry*-constraint
  (manual §9.41). Code-Aster `MODE_ITER_CYCL` vraagt `BASE_MODALE`, `NB_SECTEUR` en
  `LIAISON` links/rechts (substructurering): grote vertaalklus. **Klaar als:** sector
  van een ring/schijf geeft dezelfde frequenties als het volledige model (≤ 1%).
**Bevindingen:**
- *S10a (klaar):* Mecway rekent altijd voorgespannen zodra er een belasting is
  (manual §6.3), ook thermische rek (voorbeeld VibratingMembrane) en centrifugaal
  met spin softening (Impeller). Gebouwd: instelling `modal_prestress` (standaard
  aan = Mecway; pagina Modaal), dispatch in `_build_modal` via `_prestress_plan`:
  `MECA_STATIQUE` → `SIEF_ELGA` → `RIGI_GEOM` (+ `RIGI_ROTA` bij `ROTATION`) →
  `COMB_MATR_ASSE` (COEF_R 1, testcases sdll101a/sdll133a). Opgelegde verplaatsing
  ≠ 0 met voorspanning: ERROR (Mecway geeft dan headless geen oplossing); zonder
  opleggingen: ERROR; contact bleef al ERROR. Negatieve frequentie (druk > kniklast):
  WARNING (Mecway geeft 0 Hz). Verificatie MP-01..07 (`tests_modaal_voorspanning.py`):
  balk trek/druk analytisch ≤ 0,001% en gelijk aan Mecway; hex20 −0,05/−0,11%
  analytisch, gelijk aan Mecway; plaat met thermische druk analytisch ≤ 0,05%, Mecway
  −0,25%; draaiende hex20-balk gelijk aan Mecway; draaiende `POU_D_E`-balk −0,52% in
  het rotatievlak (KNOWN_BUGS 49). Open: Mecway-GUI-test; VibratingMembrane (E =
  0,001 Pa) vindt met de laagste modes niets (valse `COQUE_3D`-rotatiemodes; met
  zoekfrequentie wel, KNOWN_BUGS 49). Vraag gebruiker: valse modes zonder effectieve
  massa automatisch weglaten, of zo laten (nu: zo laten, melding)?
- *S10b (klaar):* Mecway (headless, fieldvariables `modal effective mass (fraction)`
  en `stress` vóór het oplossen) geeft per mode `<globalvariable>`
  `modaleffectivemass{tx..rz}` en `...fraction..`, rotatie om de **oorsprong**
  (nagerekend: J_X = 524,15 kg·m² van een blok op (1, 2, 3) m), fractie van de *vrije*
  massa; en ook spanningen per mode (`stressxx`.., `vonmises`; docs §1.4 zei ten
  onrechte van niet). Gebouwd: effectieve massa voor de rotaties in de job
  (`aster_results_export._effective_masses`, Γ = φᵀMR met de massamatrix `masse`,
  `getNodeAndComponentFromDOF`), om de oorsprong zoals Mecway, fractie van RᵀMR
  inclusief opgelegde knopen zoals Code-Aster's translaties; controle per run: eigen
  translaties = `MASS_EFFE_UN_D*` (≤ 1e-4), anders geen rotaties. Log/statusvak
  RX/RY/RZ + som, regel `BRIDGE_MASSA` (massa, zwaartepunt, J om oorsprong en
  zwaartepunt). Spanningen per mode als optie via de bestaande instelling `fields`
  van `modal_3d` (`stresses`/`vonmises`, standaard uit; geen nieuwe instelling;
  `CALC_CHAMP` zonder `REAC_NODA`, ook schalen en balken). Verificatie: MO-06 (vrij
  blok, som = Steiner exact), MO-07 (hex20: rotatie mode 1 −0,03% t.o.v. Euler 0,97069,
  som 6 modes −0,15%, σ_xx mode 1 +0,43% analytisch / +0,01% Mecway), MO-01/MO-04
  extra controles; Mecway's API leest de spanningen per mode uit de bridge-`.liml`.
  Open: Mecway-GUI-test (spanningen per mode tonen);  Vragen gebruiker:
  de effectieve massa ook als Mecway-veld (`<globalvariable>`, met de bridge-fractie
  i.p.v. Mecway's vrije massa) schrijven? (Besluit: ja, gebouwd in S12: altijd bij
  modaal en complexe modes, Mecway's eigen namen + `cumulativeeffectivemassfraction*`;
  verificatie MO-01/MO-06; open: Mecway-GUI-test van de cumulatieve variabele.)
  Rotatie om het zwaartepunt als optie (nu:
  oorsprong verleggen)? Spanningen per knikvorm?
- *S10c (klaar):* Mecway heeft geen invoer voor niet-lineaire knik (manual §6.2, §6.6;
  voorbeeld BucklingPlateNonlinear gebruikt een kleine verstoringskracht). Invoerroute:
  instellingen op de pagina Niet-lineair statisch (`crit_stab`, standaard uit;
  `imperfection_amplitude` 0 = geen, `imperfection_mode` 1, `imperfection_unit` m of
  L = fractie van de grootste modelafmeting), ook per model met `#ASTER-OPTIE`. Gebouwd
  (`bridge_to_aster._crit_stab_*`, `_imperfection_*`): `CRIT_STAB` PLUS_PETITE 1 mode
  in `STAT_NON_LINE`, tabel `ANALYSE_MODALE` als `BRIDGE_CRIT_STAB` in de `.mess`, log
  en statusvak met melding "knik bereikt"; imperfectie = lineaire knik (zoals
  `buckling_3d`, lasten op de eindtijd, `NORM_MODE` TRAN) → `MODI_MAILLAGE DEFORME`
  (+ `AFFE_CARA_ELEM` opnieuw) → `STAT_NON_LINE` → `CALC_CHAMP` → mesh terug met
  −e0·φ, zodat `_check_node_order` klopt (verplaatsingen t.o.v. de imperfecte vorm).
  Gemeten: CRIT_STAB is bij kleine verplaatsingen een lastfactor (det(K_T + λK_g)), bij
  grote (standaard voor volumes, één elset is genoeg) −(kleinste eigenwaarde van K_T)
  (det(K_T + λI), "produits B*X = 0"); de bridge schat dan het nulpunt. Verificatie
  NK-01..04 (`tests_niet_lineaire_knik.py`): balk λP = Pcr < 0,001%; hex20 knikpunt
  +0,38% (groot) en +0,20% (PETIT, = BU-03); imperfectie L/1000: versterking
  e0/(1 − P/Pcr) tot 0,675 Pcr ≤ 0,44%, Southwell-Pcr +0,20%; plastisch met e0 = L/200:
  draagkracht 0,488 Pcr tussen Ayrton-Perry 0,419 en scharnier 0,563, CRIT_STAB → 0.
  Beperkingen: KNOWN_BUGS 53. Open: Mecway-GUI-test (statusvak, velden na
  imperfectie). Vragen gebruiker: (1) de imperfectie ook als veld naar Mecway, of de
  verplaatsingen inclusief imperfectie tonen (nu t.o.v. de imperfecte vorm)? (2)
  CRIT_STAB ook in dynamica (`DYNA_NON_LINE`)? (3) boogslengtemethode (`PILOTAGE`)
  om voorbij het grenspunt te rekenen (nieuwe stap)?
- *S10d (klaar, transiënt):* Mecway-invoer `<analysis type="D30"
  modesuperposition="true" maxmode="n" />` met `<timesteps timeperiod stepsize
  [keepeverynthtimestep]>` (DampedVibratingStrip, strings in mecway.exe). Headless
  gemeten: Mecway integreert de modale vergelijkingen **exact** (stap 0,02 en 0,001 s
  gelijk, 1e-4 van u_st(1 − cos ωt)), zonder statische correctie (1 mode: 0,9707 ×
  statisch = 12/λ₁⁴) en zonder voorspanning door de lasten; uitvoer op t = 0 en elke
  n-de stap; velden displ/rot/vel/angularvel/von Mises. Gebouwd: analyse
  `dyna_modal_3d` (`bridge_dyna_modal.py`, `AsterTemplate_DynaVibra.comm`,
  `SOLVER_BUILDERS_ASTER["DYNA_VIBRA"]`), `auto`: D30 + mode superposition →
  `dyna_modal_3d`, D30 zonder → `dyna_impl_3d` (uitvoertijden uit `stepsize`; WARNING
  tenzij NEWMARK + PETIT, dan gelijk aan Mecway). Keten `CALC_MODES` → lasten per
  tijdsfunctie gesplitst (variant van elke `AFFE_CHAR_MECA_F` met die functie op 1,
  de rest 0) → `CALC_VECT_ELEM`/`ASSE_VECTEUR` → `PROJ_BASE` → `DYNA_VIBRA` GENE
  (NEWMARK, `steps_per_period` 50 van de hoogste mode; Rayleigh als `AMOR_REDUIT`
  ξ = α/2ω + βω/2 + `modal_damping`) → `REST_GENE_PHYS` (`DEPL`, `VITE`, `ACCE` voor
  `SIPM_ELNO`) → `CALC_CHAMP` met `MODELE`/`CHAM_MATER`. Optie `static_correction`
  (`MACRO_ELAS_MULT` + `CORR_STAT`, forma12d). Hoeksnelheid `angularvel*` nu ook in
  `FIELD_TABLE`. Verificatie MD-01..07 (`tests_dynamisch_modaal.py`, 21 controles):
  SDOF stap/gedempt/harmonisch analytisch ≤ 0,17% (verloop), piek 0,00–0,17%; t.o.v.
  headless Mecway ≤ 1,4e-5 (SDOF), hex20 4e-5 / 1,4e-4 / 4e-4 (u / v / σ_xx), console
  1 mode 3,4e-3; statische correctie exact; D30 direct 3e-8. DampedVibratingStrip
  (schalen): 1,9% (frequenties schalen −0,6/+0,3%, KNOWN_BUGS 2). Regressie 390/393
  OK, 3 BEKEND (KNOWN_BUGS 43), 0 NOK. Beperkingen: KNOWN_BUGS 54. Harmonisch in het
  frequentiedomein afgesplitst als **S10h** (Mecway heeft geen analysetype; invoer
  frequentielijst + belasting uitzoeken, `DYNA_VIBRA TYPE_CALCUL='HARM'`
  `BASE_CALCUL='GENE'`, testcases sdld21b en sdld313d (`HARM` + `GENE`) als syntaxbron; klaar als: DAF
  1/√((1−r²)² + (2ζr)²) ≤ 1% op het SDOF-model van MD). Open: Mecway-GUI-test.
  Vragen gebruiker: D30 zonder mode superposition automatisch met NEWMARK + PETIT
  rekenen (nu: `dyna_impl_3d` met de eigen instellingen + WARNING)? Een beginsnelheid
  en opgelegde bewegingen op modale basis bouwen (statische modes)?
- *S10e (klaar):* Mecway heeft geen spectrumanalyse (manual hoofdstuk 6; geen
  "spectrum"/"seism" in mecway.exe). Invoerroute: Mecway *Frequency* (V30, Number of
  modes) met een **Gravity met per richting een tabel** (kolom *time* = periode [s],
  instelling `spectrum_abscissa` ook frequentie; waarde = spectrale versnelling; zonder
  tabel = vlak spectrum; de gravity is geen last), analyse `spectrum_3d` zelf kiezen
  (`auto` blijft `modal_3d`). Eigen spectrum (`DEFI_NAPPE`/`FORMULE` in AMOR en FREQ,
  bijv. meerdere dempingen) met het nieuwe `#ASTER-SPECTRE X, Y = naam [, K=V]`.
  Gebouwd: `bridge_spectrum.py`, `AsterTemplate_Spectre.comm`, job-module
  `aster_spectrum.py`; keten `CALC_MODES` → `CALC_CHAMP` (REAC_NODA, SIGM) →
  `MODE_STATIQUE PSEUDO_MODE` → `COMB_SISM_MODAL MONO_APPUI` → maxima als een
  statische stap (`CREA_RESU`); instellingen `spectrum_damping` (0,05 + Rayleigh),
  `modal_combination` (CQC), `direction_combination` (SRSS; 100-30-30 rekent de bridge
  uit `VALE_DIRE`; 100-40-40 = `NEWMARK`), `missing_mass` (aan, `FREQ_COUP` = hoogste
  mode). Velden: verplaatsing, absolute versnelling (nieuw `accelx/y/z`), spanning
  (volumes), von Mises (per mode berekend en gecombineerd: SRSS = verwachtingswaarde
  van σᵀPσ, CQC bovengrens), reacties; log: effectieve massa per richting (WARNING
  < 90% zonder missing mass), afsnijfrequentie, gecombineerde totale reactie (de som
  van knoopmaxima is te groot). Verificatie SP-01..07 (9 cases, 41 controles):
  sdld25a (8 massa's/veren, Rayleigh β, DEFI_NAPPE via #ASTER-SPECTRE) frequenties ≤
  3e-14, ACCE_ABSOLU ≤ 3,5e-8 (klaar-criterium 1%); twee massa's SRSS, CQC (ρ = 0,17),
  missing mass met 1 mode en de totale reactie ≤ 1e-6 van de handberekening
  (criterium 0,5%); richtingen SRSS/100-30-30/100-40-40 ≤ 4e-8; hex20-console t.o.v.
  Euler-Bernoulli u −0,02%, σ/von Mises +0,38%, reactie −0,12%. Mecway leest de stap
  onder V30 via de API (headless script: `node_value`, `modes()` leeg); GUI-weergave
  NIET geverifieerd. Regressie 444/447 OK, 3 BEKEND (KNOWN_BUGS 43), 0 NOK. Beperkingen:
  KNOWN_BUGS 56. Open: Mecway-GUI-test (stap onder een Frequency-analyse, `accel*`).
  Vragen gebruiker: (1) `auto` bij V30 + gravity met tabel naar `spectrum_3d` (nu zelf
  kiezen)? (2) missing mass standaard aan (nu) of uit (Code-Aster-standaard)?
  (3) richtingscombinatie standaard SRSS (nu), 100-30-30 (EC8) of 100-40-40
  (Code-Aster)? (4) spectrum per steunpunt (`MULT_APPUI`) nodig? (5) een EC8-spectrum
  uit a_g en grondtype laten maken i.p.v. een tabel?
- *S10f (klaar):* Mecway (headless gemeten) heeft geen gedempte modes: V30 negeert
  Rayleigh-demping (zelfde frequenties, geen decay rate; Rayleigh hoort volgens manual
  §9.26 bij D30/D31) en geeft met een Damper-element geen oplossing (D30 negeerde de
  hand-geschreven demper ook, vgl. KNOWN_BUGS 47). Complexe modes kent Mecway alleen
  akoestisch (`<mode frequency=".. Hz" decayrate=".. 1/s">`, headless gezien). Gebouwd
  als optie: instelling `modal_complex` (pagina Modaal, standaard uit = reële modes
  zoals Mecway, INFO bij demping in het model), `bridge_modal_damping.py`: C = αM + βK
  (`COMB_MATR_ASSE` op de matrices van het eigenwaardeprobleem, dus ook knoopmassa's en
  veren, met voorspanning K + K_g) + `AMOR_MECA` van de dempers (andere discreten
  `A_*` 0 tegen `DISCRETS_28`); `CALC_MODES` met `MATR_AMOR`, `PLUS_PETITE` +
  `TRI_DIAG` (Sorensen kan niet: `ALGELINE2_71`), met zoekfrequentie of vrij-vrij
  `CENTRE` + Sorensen. Gemeten: Code-Aster's `FREQ` = gedempte frequentie,
  `AMOR_REDUIT` = ζ; overkritische en starre modes vallen weg (`ALGELINE5_79`, hint in
  bridge_run_aster). Export: `<mode frequency="f_d Hz" decayrate="ζ·2πf_n 1/s">`, vorm
  = reëel deel na fasedraaiing (½·arg φᵀMφ), φᵀMφ = 1 (bij Rayleigh gelijk aan de
  reële mode, 2e-9); log/statusvak per mode f_d, ζ, f_n en effectieve massa; Mecway-
  vergelijking op f_n. Mecway's API leest de modes (headless script, `frequency` = f_d);
  GUI NIET bekeken. Verificatie MC-01..05 (`tests_modaal_demping.py`): massa-veer-
  demper ζ = 0,1/0,5 en Rayleigh α/β (ζ = 0,2): ζ, f_d en f_n ≤ 1,3e-15 analytisch
  (criterium 1%); 2 massa's met demper (niet-proportioneel) ≤ 1,1e-14 t.o.v.
  det(s²M + sC + K) = 0; hex20-console α = 20, β = 1e-4: ζ_n = α/2ω_n + βω_n/2 ≤ 2e-11
  per mode (6 modes), f_n gelijk aan Mecway (≤ 8,4e-11); vrij-vrij: 6 starre modes weg,
  elastische gelijk aan Mecway (≤ 3e-11). Regressie 569/572 OK, 3 BEKEND (NL-03a,
  KNOWN_BUGS 43), 0 NOK/FOUT. dyna_modal_3d: dezelfde ξ_i (docs). Grenzen: KNOWN_BUGS 49. Open:
  Mecway-GUI-test (f_d en decay rate onder *Solution*). Vragen gebruiker: (1) de
  frequentie in Mecway gedempt (nu, zoals Mecway's akoestiek) of ongedempt? (2) het
  imaginaire deel van de vorm ook naar Mecway (veldnaam onbekend)? (3) hysteretische
  demping (`AMOR_HYST`) of `modal_damping` als ζ per mode ook in modaal nodig?
- *S10h (klaar):* Mecway heeft geen harmonische analyse (manual hoofdstuk 6; D30 is
  transient). Invoerroute: eigen analyse `harmonic_3d` (pagina *Harmonische respons*,
  zelf kiezen; `auto` blijft V30 → modaal) op een V30- of D30-model; de belastingen
  zijn de amplitude, fase per selectie met het nieuwe `#ASTER-FASE selectie = graden`
  (`PHAS_DEG`), een Mecway-tabel van een last = amplitude tegen frequentie (kolom
  *time* = Hz, `DEFI_FONCTION NOM_PARA='FREQ'` als `FONC_MULT`), meetpunten met
  knoopselecties `MEETPUNT_`/`PROBE_` (log, statusvak, `_meetpunten.csv`). Frequenties
  met de sleutels van S3a (`harm_freq_start/_end/_count/_spacing/_list`) plus
  `harm_refine_points` (5 punten per mode over 2ξf rond de piek: `DEFI_LIST_FREQ`
  `RAFFINEMENT` `LARGEUR_3DB`, sdld21b), `harm_basis` GENE (standaard) / PHYS (direct,
  C = αM + βK + dempers), `modal_damping`, `static_correction` (standaard aan:
  statische verrijking van de basis zoals `DYNA_LINE` `ENRI_STAT`: `MACRO_ELAS_MULT` +
  `DEFI_BASE_MODALE RITZ ORTHO` + `CALC_MODES QZ` + `REST_GENE_PHYS`). Gebouwd:
  `bridge_harmonic.py` (dispatch in `_build_dyna_modal` op `type_calcul` 'HARM'),
  `AsterTemplate_Harmonisch.comm`, job-module `aster_harmonic_export.py` (per
  frequentie `<mode frequency>` met `displx/y/z` = Re, `displix/y/z` = Im,
  `displamp*`, `displphase*`, `displmag`, `rot*`/`rotamp*`, `velamp*`/`accelamp*`,
  `stressxx..` = Re, `stressamp..`, `vonmises` = maximum over de periode, exact uit de
  complexe `SIGM_NOEU`). Gemeten: U = F·e^{iφ}/(k − mω² + iωc) (`PHAS_DEG` +,
  naijlen negatief); `FONC_MULT` als functie van `FREQ` werkt in GENE en PHYS; een
  keten `getField(..).toSimpleFieldOnNodes().getValues()` gaf NaN (tussenobjecten
  vasthouden). Verificatie HR-01..05 (`tests_harmonisch.py`, 11 cases, 40 controles):
  (a) 1 vrijheidsgraad (veer + massa) met modale demping, Rayleigh α (GENE en PHYS) en
  een demper ζ = 0,2: |U| ≤ 5,5e-8 en fase ≤ 7,5e-6° over het hele bereik
  (criterium 1% en 1°), piek en piekfrequentie exact; (b) Euler-Bernoulli-console
  (exacte receptantie, Rayleigh α): GENE met verrijking en PHYS 6,6e-4 over 1–200 Hz,
  GENE = PHYS 1,9e-5 (criterium 1%); zonder verrijking het statische deel van de
  weggelaten modes 6,22e-4 = 1 − Σ12/λ⁴ en 64% fout in de antiresonantie; hex20-console
  GENE = PHYS (tip 4,3e-6, von Mises 4,3e-5, |σ_xx| 2,3e-3); fase, tabel, tegenfase en
  meetpunt-CSV exact. Mecway's API leest het resultaat (headless `mecway.exe <model>
  script <script.py>`: 120 frequenties en de velden). Regressie (`VERIF_WORK` eigen
  map): 712/715 OK (162 cases), 3 BEKEND (NL-03a, KNOWN_BUGS 43), 0 NOK/FOUT, geen
  eerder OK-controle slechter. Beperkingen: KNOWN_BUGS 54. Open: Mecway-GUI-test (lijst
  per frequentie, contour van `displamp*`, animatie). Vragen gebruiker: (1)
  `static_correction` standaard aan (nu, Code-Aster `DYNA_LINE`) of uit? (2)
  hysteretische demping (verliesfactor η, `AMOR_HYST`) nodig? (3) basisbeweging
  (opgelegde versnelling/verplaatsing, `MULT_APPUI`/statische modes) bouwen? (4)
  de frequentierespons ook als Mecway-grafiek (bijv. `<globalvariable>`) i.p.v. CSV?
  (5) `harm_freq_end` automatisch op de hoogste mode zetten?
- *S10g (klaar):* Mecway-invoer (headless gemeten, Samples/Impeller.liml en eigen
  ringsectoren): `<cyclicsymmetry axis segments selectionmaster selectionslave>`,
  `axis` 1/2/3 = X/Y/Z door de oorsprong, master/slave knoop- of vlakselecties, slave op
  ±360°/N. Mecway rekent per ND 0 … N/2 *Number of modes* modes (een paar staande
  golven één keer), op volgorde van ND, en zet het hele wiel (eigen knopen en
  elementen) in `<solution>`. Gekozen route: Code-Aster `MODE_ITER_CYCL` (geen
  volledig model): `bridge_cyclic.py` (paren op ±360°/N, GAUCHE = +360°/N, knopen op de
  as → `AXE`, volledig vaste snijvlakknopen uit de interfaces, X/Y-as → exacte
  verwisseling van de coördinaten en de lastrichtingen, voorspanning met de relaties
  van ND 0), template `AsterTemplate_ModeIterCycl.comm` (Craig-Bampton-basis:
  `CALC_MODES` met vaste snijvlakken, `DEFI_INTERF_DYNA`, `DEFI_BASE_MODALE`,
  `MODE_ITER_CYCL` `NB_DIAM` 0 … N/2, `REST_SOUS_STRUC SECTEUR=1 NOM_CHAM='DEPL'`),
  job-module `aster_cyclic.py` (Mecway's volgorde, `BRIDGE_MODE .. ND=..`; het resultaat
  van REST_SOUS_STRUC kreeg pas velden na `setMesh`/`setDOFNumbering`/`build`); log en
  statusvak met ND; instelling `cyclic_base_modes` (0 = max(20, 4 × modes per ND)).
  Code-Aster-valkuilen gevonden: ruis rond 0 in de axiale coördinaat →
  `ALGORITH16_52` (de bridge zet < 1e-12 × modelgrootte op 0, MODI_MAILLAGE-rotatie
  vermeden), `TOUT_DIAM` rekent bij oneven N één ND te veel, `REST_SOUS_STRUC`
  `NOM_CHAM` is standaard `'ACCE'`, 8 segmenten met knopen op de as → `ALGORITH14_95`
  (fout in `ctetax.F90`, ERROR). Verificatie CY-01..06 (`tests_cyclisch.py`, 134
  controles): ring (12 segmenten, Z en X) en draaiende schijf (Y, 3000 r/min,
  voorspanning) t.o.v. het volledige model ≤ 0,0012% (criterium 1%), t.o.v. Mecway's
  cyclische oplossing ≤ 0,03% (criterium 1%), ring t.o.v. Blevins +0,59 … +1,18% en
  ingeklemde plaat (6 segmenten, knopen op de as) t.o.v. Leissa +0,58 … +0,66%
  (criterium 2%). Mecway's Impeller (Y, 100 000 r/min): 27 modes +0,01 … +0,92% t.o.v.
  Mecway, de sector zonder cyclische symmetrie wijkt evenveel af (KNOWN_BUGS 62).
  Mecway's API leest de modes van de bridge (headless script); GUI NIET bekeken.
  Grenzen: KNOWN_BUGS 61 (o.a. dubbele eigenwaarde in ND 0 +1,3%, alleen modaal,
  alleen volume-elementen, alleen de sector naar Mecway). Afgesplitst: **S10i** (het
  hele wiel in Mecway). Open: Mecway-GUI-test (sector-oplossing van een cyclisch
  model in de GUI, lijst *Mode 1..n*, animatie). Vragen gebruiker: (1) het hele wiel
  tonen (S10i) of is de sector genoeg? (2) cyclische symmetrie ook in statisch en
  thermisch (Mecway kan het; nu ERROR en losse sector)? (3) een gedeeltelijke
  oplegging op een snijvlak (axiaal vrij) nodig? (4) bij een dubbele eigenwaarde in
  ND 0 liever het volledige model als optie (`cyclic_method`)?
- *S10i (klaar):* Mecway's formaat (headless `mw_solve.py` op CY-01, CY-04, CY-05,
  Impeller en varianten: twee elsets, losse knoop, master/slave verwisseld): de
  modelkopie in `<solution>` heeft N kopieen; knoop i van sector j = i + j·n, gedraaid
  over +j·360°/N (rechtsom-positief, onafhankelijk van master/slave), element e + j·ne
  (ne = hoogste eid), per elset de sectoren achter elkaar, alle knopen gekopieerd (ook
  snijvlakken en as). Code-Aster: `DEFI_SQUELETTE` (`CYCLIQUE`, `SECTEUR TOUT='OUI'`) +
  `REST_SOUS_STRUC SQUELETTE NOM_CHAM='DEPL'` geeft precies die opbouw (N·n knopen,
  blok j = sector over +j·360°/N, met de fase; blok j = `SECTEUR=j+1` gedraaid; gezien
  met CY-01), ook om X/Y (skelet terug gedraaid) en met knopen op de as; het resultaat
  kreeg zonder `setMesh` velden. Gebouwd: `aster_cyclic.collect` (wiel of terugval naar
  de sector met WARNING, `BRIDGE_CYCL ... WIEL=0|1`), `wheel_model`/`node_rows`
  (koppeling op coordinaat), `aster_results_export(cyclic=...)`,
  `bridge_results_liml.splice_results`/`check_results_fit` (knopen en elementen van
  het wiel in de modelkopie), instelling `cyclic_full_wheel` (standaard aan). Gemeten:
  modelkopie gelijk aan Mecway's eigen (ids, volgorde, elementen; coordinaten ≤ 1,1e-15
  m), Mecway's API leest het wiel van de bridge zoals zijn eigen (CY-01, Impeller);
  vormen t.o.v. het volledige model 1 − MAC ≤ 5,1e-7 (CY-01) en ≤ 2,1e-8 (CY-05),
  criterium 1e-3; snijvlakken doorlopend ≤ 1,3e-14; op de as (CY-04, ND 1) 6,2e-4,
  Mecway's eigen oplossing 9,4e-4; t.o.v. Mecway's wiel ND 0 MAC 1,000000 (CY-05),
  Impeller 0,9996 … 0,99994. 37 nieuwe controles in `tests_cyclisch.py` (CY 171/171).
  Regressie (`VERIF_WORK` eigen map): 1055/1058 OK (216 cases), 3 BEKEND (NL-03a, KNOWN_BUGS 43), 0 NOK/FOUT, geen eerder OK-controle slechter. Gevonden, niet opgelost: KNOWN_BUGS 78 (Resultaten... bij X/Y-as).
  Open: Mecway-GUI-test (wiel tonen, animatie per mode). Vragen gebruiker: (1) de
  schaal van de vormen gelijk aan Mecway maken (massanormering over het hele wiel; nu
  die van REST_SOUS_STRUC)? (2) bij een paar ook het tweede lid als extra mode tonen?

### S2 – Akoestiek: holtemodes
**Doel:** Mecway *Acoustic Resonance* (manual §6.9, §9.34) via Code-Aster: eigenmodes
van een lucht- of vloeistofvolume met drukknopen (p = 0) en impedantieranden.
**Code-Aster:** `PHENOMENE='ACOUSTIQUE'`, `MODELISATION='3D'` (rand: `3D_ABSO`), een
drukformulering zonder koppeling met de constructie; `CALC_MODES` op de akoestische
matrices. Testcases: zoek op `ACOUSTIQUE` (o.a. `ahlv100a` voor syntax). Het
analysetype en de tags in Mecway eerst lezen (waarschijnlijk A30; niet bevestigd), plus
de naam van het drukveld in Mecway's oplossing; modes als lijst in de `.liml`
(hergebruik van de modale resultaatroute).
**Klaar als:** 3D-buis met harde wanden en open/gesloten einden: f_n = n·c/(2L) binnen
0,5%, en gelijk aan headless Mecway van hetzelfde model (≤ 1%). De orgelpijp-tutorial
(2D) alleen als illustratie.
**Bevindingen:** Invoerroute: Mecway zelf (headless vastgesteld met `mw_solve.py`):
`<analysis type="A30" maxmode="..">`, materiaal `<mechanical type="Isotropic"
speedofsound="340 m/s" />` (dichtheid optioneel, Mecway rekent zonder),
`<fluidpressure selection=".."><value>0 Pa</value>` op knopen of vlakken (≠ 0 weigert
Mecway), `<impedance selection=".."><specificimpedancer>408</..><specificimpedancei>0</..>`
(getal zonder eenheid; "Pa*s/m" weigert Mecway). Mecway's oplossing: per mode
`<mode frequency>` met de knoopvariabele `pressure`, genormeerd pᵀMp = 1 met
M = ∫NᵀN/c²; met impedantie complexe modes (`decayrate`, `pressure` + `pressurei`).
Mecway rekent akoestiek met **één** materiaal (twee: geen oplossing). Gebouwd:
`bridge_acoustic.py` (parse + builder, dispatch in `_build_modal` op
`analysis["phenomene"]`), `AsterTemplate_Akoestiek.comm`, analyse `acoustic_modes_3d`
(A30), `PRES` → `pressure` in `aster_results_export`. Code-Aster: `NORM_MODE` werkt niet
voor `MODE_ACOU` (de bridge schaalt met 1/√`MASS_GENE`, dan gelijk aan Mecway); harde
wanden zonder drukknoop geven met `PLUS_PETITE` `ALGELINE3_81` (bridge: `CENTRE` rond
−0,1·c/(2D), alarm `ALGELINE3_82` onschuldig); `RIGI_ACOU`/`MASS_ACOU` bevatten ρ niet
(gemeten), dus media met verschillende dichtheid geven een ERROR. Verificatie AK-01..07
(`tests_akoestiek.py`, 78 controles OK): hex20-buis gesloten-gesloten en open-gesloten
≤ 0,017%, ruimte 3D ≤ 0,026%, hex8/wedge6/tet4 ≤ 0,36% (Δf/f ≈ (kh)²/24), twee media
≤ 0,024%; t.o.v. headless Mecway < 4e-10 (frequenties én ∣p∣). Regressie 447/450 OK,
3 BEKEND, 0 NOK/FOUT. **S2b (afgesplitst):** impedantie niet gebouwd (ERROR): `CALC_MODES`
neemt `MATR_AMOR` niet voor drukmatrices, `AFFE_CHAR_ACOU` kent geen impedantie,
`3D_ABSO` alleen ρc; route nog uitzoeken (eigen kwadratisch eigenwaardeprobleem in de
job, of projectie op reële modes). Controlegeval: buis hard/Z (reëel, Z > ρc) heeft
f_n = n·c/(2L) en decay rate (c/L)·artanh(ρc/Z). Open: Mecway-GUI-test (veld `pressure`
per mode). Vragen gebruiker: impedantie (S2b) bouwen, en via welke route? *Acoustic
displacement* als veld gewenst? Media met verschillende dichtheid nodig (dan andere
formulering)?
**S2b (klaar):** Invoerroute: Mecway's eigen *Impedance* (geen nieuwe invoer). Mecway
(manual §6.9.2, headless nagegaan) rekent (K + λC + λ²M)P = 0 met C = ∫ρ/Z NNᵀdA,
Z = `specificimpedancer` + i·`specificimpedancei`, λ = iω − σ; zonder dichtheid ρ = 0
(impedantie werkt niet: bridge ERROR); de 2 × maxmode kleinste |λ|, daarvan f ≥ 0 (dus
niet altijd maxmode modes; 0-Hz-modes willekeurig door ruis); vorm geschaald op
Euclidische norm 1 met willekeurige fase. Route: (2) eigen kwadratisch probleem in de
job, met scipy (zit in Code-Aster's Python311, 1.16.2) i.p.v. alleen numpy: Code-Aster
maakt `RIGI_ACOU`/`MASS_ACOU` (= Mecway's K, M) en per rand `AMOR_ACOU` met
`CELE_R = 1` (= ∫NNᵀdA, gemeten; andere randen in die matrix `CELE_R` 1e30), de job
(`aster_acoustic_complex.py`) leest ze met `getValuesWithDescription`, elimineert de
drukknopen, lineariseert (2n) en lost shift-invert op met ARPACK/`splu` (< 300
vrijheidsgraden dicht). Route (1) projectie op reële modes viel af (afkapfout, complexe
C past niet in `gene_r`), route (3) `3D_FLUIDE` ook (valse φ-modes, geen complexe C).
Gebouwd: `bridge_acoustic._impedance_inputs`/`_complex_modes_comm`/`_write_modes_files`
(tak in `build_acoustic_modes`), `aster_acoustic_complex.py`, rapport per mode (decay
rate, T60, Q, residu-WARNING) in `MecwayAsterBridgeMain._report_modes`, vergelijking met
Mecway op de dichtstbijzijnde frequentie (`bridge_from_aster`). Normering: fase met
PᵀMP reëel, PᴴMP = 1 (Z → ∞ = de reële mode). Verificatie AI-01..10
(`tests_akoestiek_impedantie.py`, 227 controles OK): buis hard/Z reëel (Z = 2000, 200,
1e9, ρc), complex (2000 − 1000i, 1000 + 3000i, 1000i), drukknoop/Z, hex8 (dicht pad),
ruimte met twee impedanties; analytisch (tanh(λL/c) = −ρc/Z) hex20 f ≤ 0,037%,
σ ≤ 0,14%, P(L)/P(0) ≤ 2e-8 (criterium 1%); t.o.v. headless Mecway ≤ 1e-8 (f, σ en
P-verhouding/fase; criterium 1%); Z = ρc: alle modes σ ≥ 1588 1/s (geen resonantie);
hex8: σ gevoeliger voor de mesh dan f (+1,7% vs +0,41% bij 340 Hz). Mecway's API leest
de modes (headless script: `modes()`, `frequency`, `node_value` van `pressure`/
`pressurei`). Rekentijd 13 000 knopen/20 modes 14 s. Regressie (`VERIF_WORK` eigen
map): 1245 van 1248 controles OK (226 cases), 3 BEKEND (NL-03a), 0 NOK/FOUT, geen
eerder OK-controle slechter; in `resultaten.*` alleen de AI-cases. Grenzen: KNOWN_BUGS
55 (ook: geen MED/`res`, groot model NIET geverifieerd). Open: Mecway-GUI-test (decay
rate onder *Solution*, animatie van een complexe mode). Vragen gebruiker: (1) 0-Hz-
modes (constante druk, niet-oscillerend) altijd tonen (nu) of weglaten? (2) aantal modes
zoals Mecway (≈ maxmode, nu) of precies maxmode? (3) complexe Z ook in de harmonische
analyse (KNOWN_BUGS 57; nu met dezelfde scipy-route haalbaar)?

### S3a – Akoestiek: harmonisch drukveld
**Doel:** drukveld per frequentie bij een bron of opgelegde snelheid, met absorberende
randen. **Code-Aster:** `ACOUSTIQUE` + `DYNA_VIBRA` (harmonisch); testcase `ahlv100a`
(draait: diagnose OK).
**Invoer:** Mecway heeft geen harmonische analyse (manual hoofdstuk 6): frequentiebereik
op een pagina *Akoestiek* in het hoofdvenster + `#ASTER-OPTIE`; bron/snelheid via
Mecway-randvoorwaarden of `#ASTER`; geluidsniveau in dB op "microfoon"-knopen via
`#ASTER-POST`. Resultaten per frequentie als stappen (amplitude, fase, dB).
**Klaar als:** vlakke golf in een buis met absorberend einde: |p| constant en fase
lineair, binnen 1% van de analytische oplossing; `ahlv100a`-waarden op een 3D-nabouw ≤ 1%.
**Bevindingen:** Invoerroute: het A30-model zelf (Mecway heeft geen harmonische
analyse, manual hoofdstuk 6) met een eigen analyse `acoustic_harm_3d` (pagina
*Akoestiek (harmonisch)*; `auto` kiest hem bij A30 met een bron) en speciale
selectienamen: vlakselectie `BRON_`/`SOURCE_` (normaalsnelheid `source_velocity`,
standaard 1 mm/s, de fluid in), `ABSORBEREND_`/`ABSORBING_` (rho-c-rand),
knoopselectie `MICROFOON_`/`MICROPHONE_`; sleutelwoord `#ASTER-BRON selectie = v [,
fase]` (bridge_custom); Mecway's *fluid pressure* != 0 = opgelegde druk, *impedance*
met reele Z = absorberende rand. Frequenties: `harm_freq_start/_end/_count/_spacing`
of `harm_freq_list` (ook `#ASTER-OPTIE`). Gebouwd: `bridge_acoustic.build_acoustic_harm`
(dispatch in `bridge_to_aster._build_dyna_modal` op `phenomene`),
`AsterTemplate_AkoestiekHarm.comm`, `aster_acoustic_export.py` (in de job: per
frequentie een `<mode frequency>` met `pressure`, `pressurei`, `pressuremag`,
`pressurephase`, `spl`; microfoon-CSV en `BRIDGE_MIC`), rapport in de log/het statusvak
(`report_harmonic`). Code-Aster (route ahlv100a, gemeten): `VITE_FACE` vraagt de
bronvlakken in het model met een materiaal (`CALCUL_20`); `EXCIT` `COEF_MULT=+1`,
`PUIS_PULS=1`, `PHAS_DEG=90` geeft p = +rho c v (v de fluid in; ahlv100a -1);
`3D_ABSO`-demping = (1/c) int NN dA zonder rho, dus Z wordt `CELE_R = Z/rho` (Z = 2 rho c:
reflectie 1/3 gemeten); `CELE_I` geeft niet de reflectie van een complexe Z (ERROR,
KNOWN_BUGS 57); opgelegde druk als aparte lastvector zonder `PUIS_PULS`; een keten
`getField().toSimpleFieldOnNodes()` gaf een keer `DVP_2` (FPE), los niet. SPL op de
effectieve waarde (Code-Aster's `PRAC_ELNO` DB is 3,01 dB hoger). Verificatie AH-01..08
(`tests_akoestiek_harmonisch.py`, 10 cases, 103 controles OK): (a) vlakke golf hex20 10
per golflengte |p| -0,018%, fase -0,011% (5 per golflengte -0,25% / -0,16%; hex8 10 per
golflengte +1,7% / -1,6%, 20 per golflengte +0,41% / -0,41%); (b) harde wand: |P - P_exact|
<= 1,2e-4 van max|P| (100/250/420 Hz); (c) ahlv100a 500 Hz: Re/Im binnen de
TEST_RESU-precisie van VALE_REFE (Im in NO751 +0,33%, ook Code-Aster zelf) en gelijk aan
VALE_CALC (<= 1e-6), DB 109,887; CALC_MODES-deel van ahlv100a (8 modes) gelijk aan
VALE_CALC; impedantie Z = 2 rho c <= 7e-6; opgelegde druk 2 Pa exact; `#ASTER-BRON` met 90
graden en microfoons (SPL 89,20 dB, fase 90 - kL binnen 0,02 graden). Mecway's API leest de
frequenties en de vijf velden (headless script). Regressie (`VERIF_WORK` eigen map): 584 van 587 controles OK (135 cases), 3 BEKEND
(NL-03a, KNOWN_BUGS 43), 0 NOK/FOUT; in `resultaten.json` alleen de AH-cases
bijgewerkt. Open:
Mecway-GUI-test (lijst per frequentie, contour van `spl`/`pressuremag`, animatie van
`pressure` + `pressurei` zonder decay rate). Vragen gebruiker: (1) complexe of
frequentieafhankelijke impedantie bouwen (eigen frequentielus met `COMB_MATR_ASSE` +
`RESOUDRE`)? (2) volumedemping / poreuze materialen nodig? (3) SPL op de effectieve
waarde (nu) of op de amplitude zoals Code-Aster? (4) frequentierespons ook als Mecway-
grafiek (bijv. `<globalvariable>` per frequentie) in plaats van alleen CSV?

### S3b – Vibro-akoestiek
**Doel:** constructie en lucht/vloeistof gekoppeld (trillend paneel in een ruimte, tank
met vloeistof). **Code-Aster:** `PHENOMENE='MECANIQUE'`, `3D_FLUIDE`, `FLUI_STRU`
(koppelvlak; er bestaat geen `3D_FLUI_STRU`), `3D_FLUI_ABSO`,
`FORMULATION='U_P_PHI'`. Testcases `adlv100a` (zuiger + vloeistofkolom, gekoppelde
modes, analytisch 13,8285 Hz) en `ahlv101a` (harmonisch met absorptie).
**Invoer (voorstel):** lucht = onderdeel met Mecway's akoestische materiaal of groepsnaam
`LUCHT_`; koppelvlakken automatisch (vlakken die lucht en constructie delen), `KOPPEL_`
als handmatige keuze.
**Klaar als:** `adlv100a` op een 3D-nabouw binnen 0,5% van 13,8285 Hz; harmonische
koppeling volgens `ahlv101a` ≤ 1%.
**Bevindingen:** Invoerroute: een Mecway *Frequency*-model (V30; Mecway heeft geen
gekoppelde analyse en rekent akoestiek met één materiaal) met het fluïdum als eigen
onderdeel: materiaal met *Speed of sound* + *Density* zonder Young's modulus (Mecway's
akoestische materiaal), of een onderdeelnaam `LUCHT_`/`VLOEISTOF_`/`FLUID_`;
koppelvlakken automatisch (fluïdumvlakken die samenvallen met een vlak van een
constructie-volume-element of met een schaal), `KOPPEL_`/`COUPLING_`-vlakselecties als
handmatige keuze; p = 0 met knoop-/vlakselecties `OPEN_` (Mecway's *fluid pressure*
bestaat alleen bij A30; staat hij in de `.liml`, dan telt 0 mee). Analyse
`vibroacoustic_modes_3d` (pagina *Vibro-akoestiek (modes)*, `auto` kiest hem bij V30 met
een fluïdum; elders een WARNING), instelling `vibro_freq_min` (0,1 Hz). Gebouwd:
`bridge_vibroacoustic.py` (parse, koppelvlakken, builder, rapport),
`AsterTemplate_VibroAkoestiek.comm`, stap 2c in `bridge_mesh.write_mesh` (randelementen
`BRFSI<k>`), dispatch in `_build_modal` (analysis `"vibroacoustic"`), `FIELD_TABLE`
`pressure` uit `DEPL`/`PRES`. Code-Aster (gemeten): `FORMULATION='U_P_PHI'`
(standaard, symmetrisch); elke vrijheidsgraad φ geeft een valse mode bij 0 Hz
(`PLUS_PETITE`: `ALGELINE3_81`; `CENTRE`: eerst de valse modes), dus `INFO_MODE`
(Sturm-telling klopt) zoekt een band vanaf `vibro_freq_min`, `CALC_MODES BANDE`
(`COEF_DIM_ESPACE` 4), filteren op f en `MASS_GENE` > 0 (een valse mode met
`MASS_GENE` < 0 gaf bij normeren `DVP_2`), `EXTR_MODE`, `NORM_MODE MASS_GENE`; `U_P`
gaf een verkeerde reeks / `JEVEUX_26`, `U_PSI` kent `DDL_IMPO PRES` niet. De dichtheid
zit wel in de matrices (anders dan `ACOUSTIQUE`, KNOWN_BUGS 55): staaf + water met ρ 1000
en 1 gaven elk de eigen analytische frequenties; twee fluïda met gedeelde knopen en een
andere dichtheid gaven 188,23 i.p.v. 306,47 Hz (φ continu): ERROR. Koppelvlakken
`ORIE_PEAU` met `GROUP_MA_INTERNE` = fluïdum; schaal + koppelvlak geven het alarm
`MODELISA4_8`/`8_13` (dubbele cellen, onschuldig; uitleg in `bridge_run_aster`).
Verificatie VA (`tests_vibroakoestiek.py`, 8 cases, 29 controles OK): (a) adlv100a 3D
(hex20) 13,82767 Hz: −6,0e-5 t.o.v. VALE_REFE 13,8285 (= de lage-frequentiebenadering),
−9,8e-7 t.o.v. de exacte wortel, mode 2 +5,1e-5, p/u op beide zuigervlakken 2e-6, ook
met `KOPPEL_` (VA-01k); (b) elastische staaf + waterkolom (Zs·cot + Zf·cot = 0) 4 modes
≤ 2,4e-5 (criterium 1%); schaalzuiger (DKT) op een luchtkolom ≤ 6,6e-4; buis van twee
media (gelijke ρ) ≤ 8,6e-5; paneel op luchtholte met 1000× lichtere lucht = losse plaat-
en holtemodes ≤ 0,61% (DKT-discretisatie), met gewone lucht pompmode +8,8% (−0,48%
t.o.v. de een-mode-benadering); `#ASTER-OPTIE vibro_freq_min` (voorbeeld 14). Officiële
testcases adlv100a en ahlv101a draaien (ctest, geen NOOK). Mecway's API leest frequenties,
`displ` en `pressure` per mode (headless script op VA-01). Regressie (`VERIF_WORK`
eigen map): 651 van 654 controles OK (151 cases), 3 BEKEND (NL-03a), 0 NOK/FOUT, geen
eerder OK-controle slechter; daarna VA-05c erbij (657/654). (c) Harmonisch niet gebouwd:
**afgesplitst als S3c** (`DYNA_VIBRA HARM` op de gekoppelde matrices, `3D_FLUI_ABSO` met
`IMPE_MECA`/`ONDE_FLUI` → `MATR_IMPE_PHI`, bron als kracht op de constructie, `VITE_FACE`
of invallende golf; klaar als: ahlv101a op een 3D-nabouw ≤ 1% en een harmonisch
aangedreven zuiger + kolom ≤ 1%). Beperkingen: KNOWN_BUGS 59; een materiaal zonder E
rekent de bridge als staal, Mecway als E = 0 (KNOWN_BUGS 60). Open: Mecway-GUI-test
(modes met `displ` en `pressure`, contour en animatie). Vragen gebruiker: (1) is de
invoer via het materiaal (Speed of sound zonder E) + `OPEN_` werkbaar, of liever een
`#ASTER`-sleutelwoord? (2) lucht boven water (twee dichtheden) nodig? Dan een
koppelvlak tussen de fluïda bouwen; (3) klotsen (zwaartekracht op het vrije oppervlak)
gewenst? (4) S3c (harmonisch) als volgende stap?

### S3c – Vibro-akoestiek harmonisch
**Doel:** harmonische respons van een gekoppeld constructie-fluïdum-model (trillend
paneel dat geluid afstraalt, zuiger op een luchtkolom met absorberend einde): per
frequentie verplaatsingen in de constructie en druk/SPL in het fluïdum, met
absorberende randen (`3D_FLUI_ABSO`), bronnen en microfoons. **Code-Aster:**
`DYNA_VIBRA` `HARM` op de gekoppelde `U_P_PHI`-matrices met `MATR_IMPE_PHI`; testcase
ahlv101a.
**Klaar als:** ahlv101a (TEST_RESU) binnen 1% op een 3D-nabouw; zuiger (massa-veer) op
een luchtkolom met ρc-einde: u = F/(k − mω² + iωρcA) en de druk binnen 1%; regressie
volgens D.5.
**Bevindingen:** Invoerroute: hetzelfde Mecway *Frequency*-model als S3b (fluïdum-
onderdeel, koppelvlakken automatisch/`KOPPEL_`, `OPEN_`) met een eigen analyse
`vibroacoustic_harm_3d` (pagina *Vibro-akoestiek (harmonisch)*, zelf kiezen; `auto`
blijft de modes van S3b). Bronnen: Mecway-belastingen op de constructie (amplitude,
`#ASTER-FASE`, tabel = amplitude tegen de frequentie, zoals S10h), vlakselecties
`BRON_`/`SOURCE_` (snelheid de fluid in, `source_velocity`) en nieuw
`INVALLEND_`/`INCIDENT_` (invallende golf, nieuwe instelling `incident_pressure`, 1 Pa),
`#ASTER-BRON` met een snelheid of (nieuw) een druk-eenheid = invallende golf; randen
`ABSORBEREND_` (ρc) en Mecway's *impedance* (reëel, `CELE_R = Z/ρ`); `MICROFOON_`
(druk/SPL, CSV zoals S3a), `MEETPUNT_` (verplaatsing, CSV zoals S10h); frequenties
`harm_freq_*` (20–500 Hz, 50). Gebouwd: `bridge_vibroacoustic_harm.py` (builder en
rapport; dispatch in `_build_dyna_modal` op `vibroacoustic` + `type_calcul` HARM),
`AsterTemplate_VibroAkoestiekHarm.comm`, `aster_harmonic_export` uitgebreid met
`pressure=True` (velden `pressure`, `pressurei`, `pressuremag`, `pressurephase`, `spl`
uit component `PRES` van `DEPL`) en microfoons (route van `aster_acoustic_export`);
`parse_vibro` bewaart de rollen van de speciale selecties en de impedantiewaarden.
Gekozen route: direct (`BASE_CALCUL='PHYS'`): `U_P_PHI` heeft valse modes bij 0 Hz, de
absorptie is niet proportioneel en ahlv101a/ahlv100b rekenen zo. Code-Aster (gemeten):
`ONDE_FLUI` met `PRES` geeft een binnenlopende golf `PRES`/2 en laat de teruggekaatste
golf door (de bridge schrijft 2 × `incident_pressure`); `VITE_FACE` in `U_P_PHI` geeft met
`COEF_MULT=+1` p = −ρcv (de bridge: −1, v de fluid in); `IMPE_MECA` weigert `CARA_ELEM`
(`SUPERVIS_4`: eigen `ASSEMBLAGE`), `AMOR_MECA` met `GROUP_MA` gaf `DVP_1` (dus op het hele
model met `AMOR_FLUI='NON'`); Rayleigh alleen op de constructie (`RIGI_MECA`/`MASS_MECA`
met `GROUP_MA`); `DYNA_VIBRA AMOR_FLUI='NON'` met `MATR_AMOR` + `MATR_IMPE_PHI` (zoals
`DYNA_LINE`). Verificatie VH (`tests_vibroakoestiek_harmonisch.py`, 13 cases, 175
controles): (a) ahlv101a 3D (invallende golf + absorberende uitlaat): VALE_REFE
≤ 8,0e-4 (PRECISION 1e-3), VALE_CALC ≤ 1,3e-7; ahlv100b (snelheidsbron) VALE_REFE ≤
8,9e-4, VALE_CALC ≤ 2,3e-7; `#ASTER-BRON` met fase (×i, ×e^{−i30°}) ≤ 2,3e-7; (b) zuiger
(m 0,05 kg, k 3000 N/m, ζ_straling 0,17) op een luchtkolom met ρc-einde: U ≤ 1,3e-4,
fase ≤ 7e-4°, druk ≤ 2,9e-5 van de handformule over 5–200 Hz (criterium 1%); met Z =
2ρc ≤ 1,2e-4, met Rayleigh α/β en een demper ≤ 1,3e-4, met een krachttabel + fase ≤
1,3e-4, schaalzuiger (DKT, hex8-lucht) U ≤ 2,5e-4, p ≤ 3,3e-3; invallende golf op een
harde wand / `OPEN_` ≤ 1,2e-4. Mecway's API leest het resultaat (headless script op
VH-02: 8 frequenties, `displx`/`displix`, `pressure`/`pressurei`/`spl`). Regressie (`VERIF_WORK`
eigen map, groepen na Lassen parallel): 1193 van 1196 controles OK (229 cases), 3 BEKEND
(NL-03a, KNOWN_BUGS 43), 0 NOK/FOUT, geen eerder OK-controle slechter; in
`resultaten.json` alleen de VH-cases bijgewerkt. Gevonden (KNOWN_BUGS 74, niet opgelost): in
`acoustic_harm_3d` wordt `#ASTER-BRON .. = 2 Pa` stil 2 m/s en tekst zonder getal 0 m/s.
Beperkingen: KNOWN_BUGS 59. Open: Mecway-GUI-test (lijst per frequentie met
verplaatsing én druk, contour van `spl`, animatie). Vragen gebruiker: (1) `auto` bij
V30 + fluïdum + bron (`BRON_`/`INVALLEND_`/`ABSORBEREND_`) naar de harmonische analyse
(nu: modes, zelf kiezen)? (2) complexe of frequentieafhankelijke impedantie bouwen
(eigen frequentielus met `COMB_MATR_ASSE` + `RESOUDRE`)? (3) Rayleigh-demping ook op het
fluïdum (nu alleen de constructie)? (4) het stralingsvermogen of de intensiteit op een
vlak (`CALC_CHAMP` `INTE_ELNO`) als resultaat? (5) een modale basis (GENE) voor grote
modellen met veel frequenties (vraagt de `BANDE`-zoektocht van S3b en statische
verrijking)?

### S4a – Lassen: transiënt thermisch met bewegende bron
**Doel:** temperatuurveld van een lasrups. Bouwt op `bridge_thermal.py` (T31).
**Uitzoeken:** bewegende bron (Goldak dubbel-ellipsoïde of een eenvoudiger
Gauss-bron) als Mecway-formule in x, y, z, t vraagt eerst KNOWN_BUGS 45 (x/y/z-formules
→ ERROR); anders een `#ASTER`-sleutelwoord (lasbaan, snelheid, vermogen, afmetingen).
Analysekeuze: `auto` stuurt T31 naar `ther_3d`; lassen kiest de gebruiker op de pagina
of via `#ASTER-OPTIE`.
**Klaar als:** quasi-stationaire piektemperatuur buiten de smeltzone binnen 5% van
Rosenthal (puntbron op een dikke plaat).
**Bevindingen:** Invoerroute (docs/Lassen.md): (A) `#ASTER-LASBRON` in Mecway's custom
model definition (`bridge_welding.py`): Goldak dubbel-ellipsoïde (af, ar, b, c of r;
ff/fr standaard continu), Q, η, v, rechte baan (`start`, `richting`, `lengte`) of
`pad=<<knoopselectie>>` (stuksgewijs recht), `diepte`, `t0`/`t1`, `groep` (standaard
selecties/componenten met `LASNAAD_`, anders automatisch binnen 3× de grootste halve
as), `symmetrie`. In de .comm een Python-functie + `FORMULE(X, Y, Z, INST)` +
`AFFE_CHAR_THER_F SOURCE`; na de solve een energiecontrole in de job (`CALC_VECT_ELEM`
`CHAR_THER`: opgenomen vermogen, regel `BRIDGE_LASBRON`, statusvak). Meldingen:
v·Δt > ½(af + ar), element > 0,8× de halve as, opgenomen vermogen > 2% af. (B)
Mecway-formules in x, y, z, t voor alle thermische lasten (KNOWN_BUGS 45 thermisch
opgelost; Mecway's interne solver rekent zo'n model ook). Geen aparte analyse: T31 →
`ther_3d` (ook `auto`). Temperatuurafhankelijke λ/c werden niet vertaald: XML gelezen
uit een met Mecway (script `mw.set_material_type(.., "TempDependent")`) opgeslagen
model, nu `THER_NL` + `THER_NON_LINE`; gevonden: Code-Aster interpoleert de enthalpie
lineair tussen de `RHO_CP`-tabelpunten (13% energie weg na de eerste stap), de bridge
verlengt en verfijnt de tabel. Verificatie WE-01..06 (`tests_lassen.py`, 53
controles): Rosenthal −0,94..+0,90% (tolerantie 5%; met v·Δt op de meldingsgrens
3,6%), Goldak analytisch gevouwen ≤ 1,2%, energiebalans ≤ 0,06% (tolerantie 2%),
opgenomen vermogen ≤ 0,09%, λ(T) exact (Kirchhoff, ook Mecway), energie met c(T)
0,003%, formules in temperatuur/convectie/flux gelijk aan Mecway (5e-15). Mecway
headless met de bron als formule: energie gelijk (1e-9), temperaturen −2,9/+1,6%
door Mecway's last op het einde van de stap (KNOWN_BUGS 14). Regressie 456/459 OK,
3 BEKEND (NL-03a, KNOWN_BUGS 43), 0 NOK. Beperkingen: KNOWN_BUGS 56. Open:
Mecway-GUI-test (tekst in Custom model definition, statusvak). Vragen gebruiker: (1)
de bron normaliseren op het opgenomen vermogen (nu alleen melden)? (2) een eigen
pagina in het hoofdvenster voor de lasbron i.p.v. `#ASTER`? (3) andere bronvormen
(conisch, oppervlakte-Gauss) als sleutel? (4) een grotere tijdstap voor de
afkoelfase (nu één vaste stap)?

### S4b – Lassen: keten thermisch → mechanisch
**Doel:** restspanning en vervorming. Eén template met `THER_NON_LINE` en
`STAT_NON_LINE` (`AFFE_VARC` `TEMP` met `EVOL_THER`), tijdstappen gelijk.
**Uitzoeken:** temperatuurafhankelijke E, vloeigrens en α: Mecway kent
temperatuurafhankelijkheid alleen voor geleidbaarheid en soortelijke warmte (manual
§8.6), dus via een `#ASTER`-sleutelwoord of tabel (documenteren).
**Klaar als:** (1) vrij uitzettende staaf met uniforme ΔT: rek α·ΔT exact (≤ 0,1%);
(2) volledig ingeklemde staaf: σ = −E·α·ΔT tot de vloeigrens (≤ 1%); (3) lasrups op
een plaat: restspanningspatroon (trek in de las, druk ernaast) kwalitatief, met de
gemeten waarden in de doc.
**Bevindingen:** Invoerroute (docs/Lassen.md §9): geen aparte analyse en geen
instelling: een *Thermal stress* in een T31-model zet de keten aan (Mecway bewaart
Thermal stress, Fixed support en Displacement ook in een thermisch model; headless
nagelopen met Mecway 33: ze blijven in de opgeslagen `.liml` en het thermische deel
rekent zonder melding). `auto` → `ther_3d`; `bridge_from_liml` leest dan de
mechanische voorwaarden, `bridge_thermomech.py` bouwt na de thermische solve (eigen
template `AsterTemplate_ThermoMeca.comm`) `STAT_NON_LINE` met `AFFE_VARC` `TEMP`
(`EVOL` = thermisch resultaat, `VALE_REF` = referentietemperatuur, in °C), op de
thermische tijden (`ARCHIVAGE` op dezelfde tijden: temperatuur en spanning per stap in
Mecway). Temperatuurafhankelijke E, ν, α, SY en H/ET via `#ASTER-MATERIAAL <Mecway-
materiaal>: TC=(..), E=(..), ...` (`ELAS_FO`, `ECRO_LINE_FO`; α = secans t.o.v.
`T_ALPHA`; `TC_CUT`: thermische rek constant boven de smelttemperatuur); zonder de regel
de constante Mecway-waarden incl. bilineair/hardingscurve. Nieuwe instellingen in
`ther_3d`: `deformation` (PETIT), `plastic_strain_definition`. Verificatie WE-07..10
(`tests_lassen_mech.py`): vrij uitzetten, eenassig verhinderd met bilineaire
versteviging en restspanning na terugkoelen, E(T)/SY(T)/α(T) met omgekeerd vloeien:
alle ≤ 4·10⁻⁸ t.o.v. de handberekening (tolerantie 0,1% / 1%). Lasrups WE-10 (hex8):
evenwicht N 0,02% / M 1% van SY·A, vloeien in de las (von Mises = SY + H·p, 0,2%),
trek in de las, druk ernaast, hoekverdraaiing 8,9 mrad naar de laskant, langs- en
dwarskrimp (0,077 mm, bovengrens α·q/(v·ρ·c·t) = 0,103 mm). Gevonden: lineaire hex8
locken bij plasticiteit (σxx in de las 1,3–2,6 × SY, triaxiaal; WARNING, advies
LINE_QUAD); met LINE_QUAD divergeerde Newton zonder lijnzoeken (nu `RECH_LINEAIRE`
bij plasticiteit) en zonder afkap van de thermische rek boven de smelttemperatuur
(4,6% bij 3400 K; nu `TC_CUT`); WE-10b (LINE_QUAD, 53 min, alleen met
`VERIF_ZWAAR=1`): langsspanning in de las 400–450 MPa = SY + H·p (1,13 × SY), σzz ≈ 0, evenwicht 0,05%, hoekverdraaiing 12,4 mrad. Mecway's *Displacement* is één richting (LIAISON_OBLIQUE bij x én z):
per richting een eigen voorwaarde (in de doc). Beperkingen: KNOWN_BUGS 64. Open:
Mecway-GUI-test (Thermal stress/Fixed support in een T31-model toevoegen en tonen,
resultaten per stap). Vragen gebruiker: (1) een grotere tijdstap voor het afkoelen (één
Mecway-*Time step* maakt lange afkoeling duur); (2) temperatuurafhankelijke
hardingscurve (`TRACTION` per temperatuur) nodig?; (3) de lijst van `#ASTER-MATERIAAL`
liever als eigen pagina/tabel in het hoofdvenster?; (4) LINE_QUAD standaard in de keten
bij plasticiteit (nauwkeuriger, ~5× trager)?

### S4c – Lassen: toevoegmateriaal
Elementen "geboren" laten worden (groepsnaam `LASNAAD_`) of versimpelen (vanaf het
begin aanwezig, zacht boven de smelttemperatuur). Uitzoeken wat Code-Aster kan; kiezen
en de beperking documenteren. **Klaar als:** een rups in twee lagen geeft een
plausibele temperatuurgeschiedenis en geen spanning in nog niet "geboren" materiaal.
**Bevindingen:** Invoerroute (docs/Lassen.md §10): sleutel `geboorte=ja` of
`geboorte=<<selectie>>` (+ `voorloop`, standaard 2 × af) in `#ASTER-LASBRON`; het
toevoegmateriaal is de `LASNAAD_`-selectie/-component (ja) of de genoemde selectie, de
bron werkt dan automatisch op alle elementen bij de baan. Code-Aster 17.4 heeft geen
element birth (catalogus en testcases doorzocht); gekozen: de "quiet
element"-methode: vóór de geboorte ρ·c × 1e-4, λ × 1e-8, E (en versteviging) × 1e-4,
geen bron. Geboortetijd per element uit de booglengte van zijn achterste knoop langs de
baan (dezelfde code in de .comm en de bridge, `exec`), per tijdstap gekwantiseerd.
Thermisch: `THER_LINEAIRE` met `THER_FO` van `INST` en `NEUT1` (CART, testcases
ttnp201a/ssnp160a); met λ(T)/c(T) of straling mogen `BETA`/`RHO_CP` van `THER_NL` geen
formule of nappe zijn (`MODELISA6_31`/`58`): `THER_NON_LINE` per geboortestap met een
stil `THER_NL`-materiaal (in een prototype gelijk aan de eerste route tot 1e-6);
toevoegmateriaal met `3D_DIAG`. Mechanisch: `STAT_NON_LINE` per geboortestap met een
nieuw `AFFE_MATERIAU`, `ETAT_INIT` met spanning en interne variabelen van de nieuwe
elementen op nul, `PREDICTION='ELASTIQUE'`: spanningsvrij in de vervormde stand op de
temperatuur van het begin van de geboortestap (ook LINE_QUAD, bilineair en
hardingscurve). Gevonden en opgelost: (1) Code-Aster 17.4 rekent twee lasten
`AFFE_CHAR_THER_F` met `SOURCE` in één lijst allebei met de functie van de eerste (de
tweede `#ASTER-LASBRON` uit S4a werkte dus nooit): alle lasbronnen nu in één last
(KNOWN_BUGS 70; Mecway-formulebronnen nog niet, WARNING naast een lasbron); (2) met
de consistente warmtecapaciteit volgde een stil knooppunt via de massakoppeling zijn
warme buren (+138 K): `3D_DIAG` in het toevoegmateriaal; (3) de bron stond op t_eind
door afronding soms uit: marge 1e-9. Verificatie WE-11..13 (`tests_lassen_geboorte.py`,
37 controles): (a) rups in twee stukken: energie van het levende volume +1,2..1,6%
t.o.v. het θ-schema (tolerantie 2%; de geboorte brengt de warmte van de knopen op het
grensvlak mee), in het ongeboren stuk T0 + 0,5 K, ook met c(T) (WE-11b); (b) staaf
halverwege geboren: spanning in het ongeboren deel 1,8e-4 × E·α·ΔT (tolerantie 1e-3),
krimpspanning t.o.v. de geboortetemperatuur −0,01% (1%), bilineair en hardingscurve
0,00%; (c) twee lagen (keten): laag 1 smelt (2 690 K), koelt af (530 K), wordt
opnieuw opgewarmd (1 750 K); laag 2 vóór de geboorte 4,7e-4 × SY en T0 + 0,03 K;
restspanning in evenwicht (−0,25% SY·A), trek in de rups, druk ernaast (5,5 min).
Regressie 1018/1021 OK, 3 BEKEND (NL-03a, KNOWN_BUGS 43), 0 NOK/FOUT; geen eerder OK-controle veranderd (WE-01..10 gelijk). Beperkingen: KNOWN_BUGS 71 (58 en 64 bijgewerkt). Open: Mecway-GUI-test (selectie
`LASNAAD_`, regel in Custom model definition, stille elementen in de resultaten).
Vragen gebruiker: (1) de Mecway-formulebronnen (*Internal heat generation* met formule)
ook samenvoegen tot één last (KNOWN_BUGS 70)? (2) mechanisch spanningsvrij op de
solidustemperatuur (bij het afkoelen) in plaats van bij de aankomst van de bron? (3)
de factoren van het stille materiaal (1e-4) als sleutel? (4) toevoegmateriaal voorbij
het einde van de baan (nu nooit geboren, WARNING) toch laten geboren worden?

### S6a – Breukmechanica: gemeshte scheur
**Code-Aster:** `DEFI_FOND_FISS`, `CALC_G`, `POST_K1_K2_K3`; 3D-testcase `forma07a`
(`forma05a` is D_PLAN: alleen syntax). **Invoer:** scheurfront en lippen als
groepsnamen (`SCHEUR_FRONT`, `SCHEUR_LIP_BOVEN`/`_ONDER`). Uitvoer: K en G langs het
front in de log en als tabel.
**Klaar als:** dikke plaat met doorgaande middenscheur onder trek: K_I binnen 3% van
σ·sqrt(πa)·F(a/W) (Tada/Roark), en G = K²/E' consistent.
**Bevindingen:** Invoerroute: Mecway heeft geen breukmechanica; de scheur wordt open
gemaakt met *Disconnect elements* + *Merge nearby nodes* op ligament en front (manual
v33 §4.2.10/4.2.11) of als half model met symmetrie. Speciale selectienamen:
knoopselectie `SCHEUR_FRONT`/`CRACK_FRONT`, vlakselecties `SCHEUR_LIP_BOVEN`/`_ONDER`
(`CRACK_LIP_UPPER`/`_LOWER`); zonder onderlip `SYME='OUI'`; meer scheuren met een
achtervoegsel. `bridge_fracture.py`: front als SEG2/SEG3 (`BRSCHEUR<n>`, ribben met
beide knopen in de selectie, controle op één lijn en open lippen), na de resultaat-
export `DEFI_FOND_FISS` + `CALC_G` `OPTION=('G','K')` + `POST_K1_K2_K3` op een eigen
resultaat (materiaal op alle cellen: anders `CALCUL_20` op de lippen; `SIEF_ELGA`:
anders `RUPTURE0_94`), `FORM_FISS='CERCLE'` bij een cirkelvormig front. Uitvoer:
`<model>_<run>_scheur.csv`, log en statusvak; geen veld. Instellingen
`fracture_r_inf`/`_r_sup` (0 = Code-Aster: 2h/4h), `fracture_smoothing`,
`fracture_legendre_degree`. Verificatie BR-01..06: K_I (`CALC_G`) −0,10 % t.o.v. Tada
(vlakke rek, hex20, h = a/40), G −0,41 %, G/(K²/E') 0,998; half model gelijk;
dikke plaat middenvlak +0,7 %; forma07a K1 MAX exact (1 607 011,55), G +0,8 %; hex8
K −0,7 %, G −2,0 %; twee scheuren met achtervoegsel (_L/_R) per front als BR-01.
`POST_K1_K2_K3` zonder kwartpunten −3,5 % (hex20) / −10 % (hex8).
Regressie (eigen VERIF_WORK): 727 van 730 controles OK (165 cases), 3 BEKEND
(NL-03a), 0 NOK/FOUT; geen eerder OK-controle veranderd. Niet: niet-lineair, contact
op de lippen, K als veld,
kwartpuntknopen door de bridge (de resultaatexport controleert de coördinaten),
XFEM (S6b); NIET geverifieerd: gesloten front, tet10, grensvlak, thermische rek, druk
op de lippen, de GUI-werkwijze (KNOWN_BUGS 63). **Open vragen:** (1) K/G als veld op
de frontknopen in Mecway gewenst? (2) Kwartpuntknopen als optie (vraagt een
uitzondering in de knoopcontrole van `aster_results_export`)? (3) Werkt *Disconnect
elements* + *Merge nearby nodes* met een knoopselectie in de GUI zoals de manual
zegt?

### S6b – Breukmechanica: XFEM
Scheur zonder hermeshen via levelsets (`DEFI_FISS_XFEM`), invoer via `#ASTER`.
**Klaar als:** zelfde geval als S6a binnen 5%.
**Bevindingen:** Invoerroute: Mecway heeft geen scheur-invoer; een eigen sleutelwoord
`#ASTER-XFEM vorm=CIRKEL|ELLIPSE|RECHTHOEK|HALFVLAK, ...` (`bridge_custom` soort
`-XFEM`, uitgewerkt in `bridge_xfem.py`; Engelse sleutels werken ook; lengtes in m of
met eenheid; een regel met `vorm=` start een nieuwe scheur; `groep=<<elementselectie>>`
→ `GROUP_MA_ENRI`). Geen groepsnaam-route: de vorm heeft maten nodig, een selectie geeft
die niet. Instellingen zoals S6a (`fracture_r_inf`/`_sup`, per scheur `r_inf=`/
`r_sup=`), plus per scheur `glad`, `graad`, `punten` (NB_POINT_FOND). Vertaling: het
model van de bridge heet `model_sain`, `DEFI_FISS_XFEM` + `MODI_MODELE_XFEM` → `model`
voor lasten en `MECA_STATIQUE`; daarna `POST_MAIL_XFEM` + `POST_CHAM_XFEM` en
`PROJ_CHAMP` `COLLOCATION` terug naar de Mecway-knopen (DEPL, SIGM_NOEU, SIEQ_NOEU,
fysisch per kant van de scheur; REAC_NODA uit het XFEM-resultaat), zodat de gewone
export naar Mecway werkt; na de export per scheur en per front (`NUME_FOND`,
`getCrackTipMultiplicity`) `CALC_G_XFEM` `CALC_K_G` en `POST_K1_K2_K3`, tabel
`<model>_<run>_xfem.csv`, log en statusvak. Controles vooraf: alleen volume-elementen
met `3D` (ERROR), de scheur moet elementen snijden en een front in het model hebben
(ERROR, vaak mm i.p.v. m), mesh-advies (WARNING boven a/10). Gevonden bij het
verifiëren: (1) *Symmetry* als `LIAISON_OBLIQUE` legt de XFEM-vrijheidsgraden van
gesneden elementen niet vast (forma07b K1 MAX +3,8 % aan het symmetrievlak): bij XFEM
wordt een symmetrie langs een globale as `DDL_IMPO` (daarna exact), schuin op zulke
knopen een WARNING; (2) hex20 werkt (kwadratische XFEM-elementen, alarm XFEM_63), geen
ERROR nodig; (3) `LAGRANGE` oscilleert op een gekromd front (onregelmatige snijpunten),
`LEGENDRE` ≥ 2 op een kort recht front: standaard per vorm; (4) `CALC_G_XFEM` heeft geen
krommingscorrectie (penny +5,3 %): WARNING, `POST_K1_K2_K3` of G gebruiken. Verificatie
BR-07..12 (tests_breukmechanica_xfem.py): plaat van BR-01 met HALFVLAK, hex8 h = a/20:
K_I −0,08 %, G −0,18 %, POST_K −0,24 % (klaar-criterium 5 %); hex20 +0,10 %; scheurvlak
door knopen −0,06 %; twee fronten (RECHTHOEK) −0,09 %; penny crack K_I POST_K +1,6 %,
uit G +1,0 %, CALC_G_XFEM +5,3 %, opening +3,3 % (Sneddon); forma07b via de bridge K1
MAX CALC_G_XFEM en POST_K gelijk aan de TEST_TABLE (< 1e-6). Regressie (eigen VERIF_WORK op D:): 1047 van 1050 controles OK (222 cases), 3 BEKEND (NL-03a), 0 NOK/FOUT; geen eerder OK-controle veranderd. Niet:
contact op de lippen, scheurgroei (PROPA_FISS), FONC_LN/FONC_LT, schalen/balken in het
model, foutschatter en vermoeiing samen met XFEM, SIGM_ELNO in Mecway; NIET
geverifieerd: tet10/wedge15/pyr13, `groep=`, ELLIPSE met a ≠ b, meer XFEM-scheuren in
één model, REAC_NODA op gesneden elementen (KNOWN_BUGS 63). **Open vragen:** (1) Een
MED-bestand met het mesh van POST_MAIL_XFEM (de scheur zichtbaar in ParaView) als optie
gewenst? (2) Moet `groep=` ook een `XFEM_`-elementselectie automatisch oppakken?
(3) Scheurgroei (`PROPA_FISS`, vermoeiingsgroei) als vervolgstap?

### S7 – Adaptieve verfijning
**Twee routes, Mecway eerst:** (1) Mecway's eigen `mw.refine_x2(element_ids=…)` op de
elementen met de grootste fout uit S1: selecties en randvoorwaarden blijven intact,
lus vanuit het hoofdscript; (2) HOMARD (`MACR_ADAP_MAIL`; werkt op deze installatie,
`forma01b` diagnose OK) binnen Code-Aster. Een HOMARD-mesh kan niet via de huidige
resultaatroute terug (`export_results` controleert de knoopvolgorde tegen de `.liml`):
dan een nieuw model schrijven of route 1 kiezen. 3D-testcases `sslv110f`, `sslv319a`.
**Klaar als:** plaat met gat onder trek (eindige breedte): Kt binnen 2% van
Peterson/Heywood na de verfijningslus, met minder elementen dan uniform verfijnen.
**Bevindingen:** Route (1) gebouwd, HOMARD niet (docs/Foutschatter.md §6.6: werkt in
3D op deze installatie, sslv110f gedraaid, maar het mesh kan niet terug naar Mecway
zonder een nieuwe `.liml` met alle selecties/lasten). `Scripts/bridge_adapt.py`: na de
run `after_run` (fout per element uit het resultaatbestand, `ERME_ELNO`; keuze Dörfler
0,5 / fractie / factor; stoppen bij doel, max. lussen, max. elementen (groei van de
vorige lus), stijgende fout; ERROR als een knoopselectie met voorwaarde op een te
verfijnen ribbe ligt; WARNING bij platte hex), `refine_in_mecway` (`mw.refine_x2`); lus
in `MecwayAsterBridgeMain.main()` (`_adapt_step`, kopie van het oorspronkelijke model
`_voor_verfijning.liml`, elke lus een OK-klik). Instellingen (pagina Statisch,
`#ASTER-OPTIE`): `adapt_refine` (uit), `adapt_target_error` 2%, `adapt_max_loops` 5,
`adapt_select` dorfler, `adapt_fraction` 0,5, `adapt_neighbours` uit,
`adapt_max_elements` 200000. Headless gemeten (`mecway.exe <model> script`): refine_x2
houdt het mesh conform (overgangen pyr/tet/wedge), vlak- en elementselecties en
onderdelen gaan mee, knoopselecties niet; hex20 volgt een gebogen rand, hex8 niet;
pyr13-volgorde van bridge_mesh bevestigd. **S1-fout gevonden en opgelost:** `ERME`
rekent `FORCE_FACE` met omgekeerd teken (uniforme trek: 15% i.p.v. 0); de bridge keert
het om in de last van de schatter (FS ongewijzigd: tangentieel telt niet). Verificatie
(`tests_adaptief.py`, AD): plaat met gat d/W = 0,2, hex20, plak in vlakke rek; uniform
AD-01 n = 1…32 −27,2…−0,14% (Peterson 2,519); lus AD-02 (doel 1,5%, headless Mecway): 5
lussen, globale fout 4,57 → 1,11% elke lus dalend, Kt +0,82% met 15 810 elementen, uniform
Refine x2 tot 2%: 49 152 (factor 0,32), 98% van de verfijning binnen 3r van het gat;
AD-03 knoopselectie → ERROR. Buiten de regressie: dunne plaat (aspect 1:40) en tet10
geven na 1-2 lussen slechte overgangselementen en een stijgende schatting (lus stopt).
Beperkingen: KNOWN_BUGS 65 (en 51). `#ASTER-OPTIE`-voorbeeld 18. Regressie (`VERIF_WORK` eigen map): 767 van 770 controles OK
(175 cases), 3 BEKEND (NL-03a), 0 NOK/FOUT, geen eerder OK-controle slechter (FS-01 door de
tekencorrectie ≤ 3e-4 anders); in `resultaten.json` alleen de AD-cases bijgewerkt. Open: Mecway-GUI-test (lus met OK-klikken, statusvak).
Vragen gebruiker: (1) elke lus vraagt een OK-klik; automatisch wachten op Code-Aster in
de lus gewenst? (2) standaarddoel 2% (energienorm) of lager voor piekspanningen? (3) bij
tet-meshes liever opnieuw automeshen met Mecway's verfijningspunten (`automesh_3d`
`refinements`) dan `refine_x2`? (4) HOMARD-route alsnog bouwen (nieuwe `.liml` schrijven)?

### S8 – Vermoeiing
**Code-Aster:** `POST_FATIGUE`, `CALC_FATIGUE` (rainflow, Wöhler, Miner; multiaxiaal).
Testcases `szlz100a`, `sslv135a` (draait: diagnose OK).
**Uitzoeken:** Wöhler-curve (geen Mecway-invoer: `#ASTER`-sleutelwoord of tabel);
belastingsverloop (tijdstappen van een niet-lineaire/dynamische run, of twee
belastingstoestanden); schade/levensduur als veld.
**Klaar als:** constante amplitude: schade exact volgens Miner (≤ 0,1%); een
twee-niveau-spectrum met de hand nagerekend (≤ 0,1%).
**Bevindingen:** Mecway heeft geen vermoeiing (manual en `mecway.exe`: geen
fatigue/S-N/Wöhler). Invoerroute: `#ASTER`-regels (geen instellingen in het
hoofdvenster, modelgegevens zoals `#ASTER-LASBRON`): `#ASTER-WOHLER materiaal: K=V`
(tabel `S = [..] MPa, N = [..]` log-log of `INTERPOL = LIN`, machtsvorm `S, N, m`,
Basquin `Sf, b`; `Se`, `PROL_GAUCHE` EXCLU/CONSTANT/LINEAIRE, `PROL_DROITE`,
`correctie` GOODMAN/GERBER met `Su`; `*` = overige materialen), `#ASTER-VERMOEIING`
(`spanning` VMIS_SG/PRIN, `telling` RAINFLOW/ASTM, `herhalingen`), en bij lineair
statisch `#ASTER-BLOK a, m, n` (factoren op de statische spanning) of `#ASTER-SIGNAAL
f1, f2, ...`; bij `STAT_NON_LINE`/`DYNA_NON_LINE` zijn de tijdstappen het signaal.
Gebouwd: `bridge_fatigue.py` (parse, blok in de `.comm`, rapport), job-module
`aster_fatigue.py` (σ_eq uit `SIGM_NOEU`, rainflow, Wöhler, Miner, cyclustabel
`<model>_<run>_vermoeiing.csv`, regels `BRIDGE_VERMOEIING_*`), `node_fields` in
`aster_results_export.export_results` (velden `damage`, `life` = herhalingen tot D = 1,
max. 10¹²; bij een tijdsverloop in elke stap gelijk), haak in `_build_lin_static` en
`_build_nonlin_static`, rapport in het statusvak (WARNING bij D ≥ 1). Gemeten in
Code-Aster 17.4: S van `WOHLER` is de amplitude; `POST_FATIGUE`/`CALC_FATIGUE`
`RAINFLOW` telt periodiek (ASTM-signaal → 4 gesloten cycli; szlz105a); Goodman/Gerber
nemen het teken van S_m mee; Basquin `A_BASQUIN`: 1/N = A·S^β; onder de tabel met
`EXCLU` D = 0, erboven een fout; `PROL_*='LINEAIRE'` trekt in de vermoeiingsroutines
lineair in (S, N) door, ook bij `INTERPOL='LOG'` (boven de tabel negatieve schade),
terwijl de functie zelf log-log geeft: de bridge trekt log-log door (gedocumenteerde
afwijking). Eigen rainflow i.p.v. `CALC_FATIGUE` omdat `CUMUL_DOMMAGE` geen blokken,
geen gemiddelde-spanningscorrectie en één materiaal kent; gelijk aan Code-Aster.
Verificatie VM-01..07 (`tests_vermoeiing.py`, 14 cases, 24 controles): (a) constante
amplitude tabel/Basquin/machtsvorm met Se ≤ 2·10⁻¹⁴ (criterium 0,1 %); (b)
twee-niveau-spectrum (tabel; Basquin + Goodman, 5 herhalingen) ≤ 6·10⁻¹⁴; (c) ASTM
E1049: cycli exact (0,5/1,5/0,5/1/0,5), schade 1·10⁻¹⁴, periodiek gelijk aan
`POST_FATIGUE` 2·10⁻¹⁴; (d) szlz105a 3D (niet-lineair statisch) 3·10⁻⁶ van `VALE_REFE`
en gelijk aan `CALC_FATIGUE` (0), szlz100a 3D (geen correctie/Gerber/Goodman) ≤
5·10⁻⁸; sslv135a (`FATIGUE_MULTI`, kritiek vlak) niet nagebouwd: multiaxiale criteria
niet gebouwd (afgesplitst als **S8b**); dynamisch (`DYNA_NON_LINE`) gelijk aan
`CALC_FATIGUE` 2·10⁻⁸; VMIS_SG/PRIN tweeassig exact. Mecway's API leest `damage`/`life`
(headless script, statisch en 101 tijdstappen). Regressie (`VERIF_WORK` eigen map op D:): 978 van 981 controles OK (204 cases), 3 BEKEND (NL-03a, KNOWN_BUGS 43), 0 NOK/FOUT, geen eerder OK-controle slechter; in `resultaten.json` alleen de VM-cases toegevoegd. Beperkingen: KNOWN_BUGS
66. Open: Mecway-GUI-test (contour van `damage`/`life`, tekst in Custom model
definition, statusvak). Vragen gebruiker: (1) `life` begrensd op 10¹² (nu) of een
eigen "oneindig"-waarde/log10-veld? (2) gemiddelde druk bij Goodman als voordeel
meetellen (nu, zoals Code-Aster) of op 0 zetten? (3) `PROL_DROITE` standaard
doortrekken (nu, met WARNING) of stoppen zoals Code-Aster? (4) S8b (multiaxiaal,
schalen, Manson-Coffin) of trillingsvermoeiing op modale basis/harmonisch nodig?

**Bevindingen S8b** (7 okt 2026): invoerroute uitbreiding van de bestaande regels
(geen instellingen in het hoofdvenster): `#ASTER-VERMOEIING criterium = DANG_VAN|MATAKE|
CROSSLAND|FORMULE, a = .., b = .. MPa, c = .., formule = '..', belasting = PERIODIEK|
NIET_PERIODIEK, projectie = UN_AXE|DEUX_AXES`, `rek = PRIN|VMIS_SG`, en in
`#ASTER-WOHLER` de rekvorm `Sf, b, ef, c` (E van het materiaal of `E = ..`). Gebouwd:
(1) multiaxiaal: per materiaal een eigen `DEFI_MATERIAU` (`ELAS`, `FATIGUE WOHLER`,
`CISA_PLAN_CRIT`) + `AFFE_MATERIAU`, `CALC_CHAMP EPSI_NOEU`, `CALC_FATIGUE
FATIGUE_MULTI DOMA_NOEUD`; bij lineair statisch een resultaat uit statische spanning/rek
× signaal of per blok (m ± a) via `CREA_RESU`, bij niet-lineair/dynamisch een kopie van
`res` (CALC_FATIGUE slaat `NUME_ORDRE` 0 over, alarm PREPOST4_27: een ramp gaf de halve
amplitude); periodiek N uit max(SIGEQ1, SIGEQ2) met de curve van de bridge, niet-periodiek
`ENDO1`; velden `fatigue_eq`, `fatigue_ratio` = SIGEQ/(c b) (`aster_fatigue.compute_multi`);
(2) schalen: uniaxiale route op `SIEQ_NOEU` van `res_sup`/`res_inf`, velden
`damage_top`/`damage_bottom`; (3) Manson-Coffin op `EPSI_NOEU` (bisectie in ln 2N).
Gemeten in Code-Aster 17.4: SIGEQ = c (Δτ/2 + a max(P_max, 0)) (Dang Van) resp. met N_max
(Matake), `D_VAN_B`/`MATAKE_B` tellen niet mee; Crossland = `FORMULE_CRITERE` met `AMPCIS`
= √J₂ van de amplitudetensor (szlz107a); `DOMA_NOEUD` zonder `EPSI_NOEU`: CALCULEL_29;
onder de Wöhler-tabel met EXCLU NBRUP = 0, ENDO ≈ 1e-308; PROL LINEAIRE ook hier lineair
in (S, N) (de bridge zet log-log-punten in de functie); NBRUP1 afgerond op een geheel
getal, ENDO1 niet; PERIODIQUE telt één cyclus per verloop, NON_PERIODIQUE rainflow;
MATAKE_MODI_AV kiest een ander vlak dan _AC; `EPSI_NOEU` is ook met GDEF_LOG de lineaire
rek. Verificatie (`tests_vermoeiing.py`, 11 nieuwe cases, 28 controles): (1) sslv135a in
3D: SIGEQ 300/275 MPa exact, NBRUP 1,2·10⁻⁵/1,5·10⁻⁵ (afronding), ENDO ≤ 1·10⁻¹⁴ t.o.v.
`VALE_REFE` (tolerantie 1 %); Dang Van niet-periodiek 4·10⁻¹⁵; ramp 0 → 1 exact (VM-08d);
trek + afschuiving met de hand (σ = 120, τ = 80 MPa): Dang Van SIGEQ −2,3·10⁻⁶, D −1·10⁻⁵,
twee blokken −2,3·10⁻⁵; Crossland 3·10⁻¹⁵; Matake SIGEQ +5,8·10⁻⁴, D +2,6·10⁻³ (zoekraster
van het kritieke vlak; binnen 1 %); (2) schaalplaat zuivere buiging, σ = 6m/t² (7·10⁻¹³),
schade boven/onder met Goodman 8·10⁻¹² / 6·10⁻¹² (≤ 0,1 %); (3) Manson-Coffin met
opgelegde plastische rek: rekamplitude exact, D 1,6·10⁻⁹; elastisch met `rek = VMIS_SG`
exact. Rooktests (niet in de regressie): Dang Van in `dyna_impl_3d` en een model met
volume + schaal, diagnose OK. IronPython 2.7.9: parse, meldingen, .comm-code en report.
Regressie (`VERIF_WORK` op D:): 1046 van 1049 controles OK (227 cases), 3 BEKEND (NL-03a,
KNOWN_BUGS 43), 0 NOK/FOUT, geen eerder OK-controle slechter; in `resultaten.json` alleen
de VM-cases (VM-01..07 ontbraken in de basislijn en zijn er weer bij). Gevonden en niet
opgelost: KNOWN_BUGS 82 (heen-en-weer-plasticiteit met de standaardvervorming GDEF_LOG
convergeert niet bij het terugbelasten). Beperkingen: KNOWN_BUGS 66. Open: Mecway-GUI-test
(velden `fatigue_eq`, `fatigue_ratio`, `damage_top/bottom` als contour). Vragen
gebruiker: (1) a, b, c per materiaal (nu één set voor alle materialen) of liever
standaard uit σ₋₁/τ₋₁ (`#ASTER-WOHLER ... sigma_1 = .., tau_1 = ..`)? (2) multiaxiaal op
schalen (boven/onder via `CALC_FATIGUE` op `res_sup`) en per Gauss-punt (`DOMA_ELGA`)
nodig (als S8c)? (3) Morrow/SWT-correctie voor de rekcurve gewenst? (4) bij heen-en-weer-
plasticiteit standaard `PETIT` voorstellen (WARNING) of KNOWN_BUGS 82 eerst uitzoeken?

### S5 – Lassen: metallurgie
**Code-Aster:** `CALC_META`, `DEFI_TRC`, `META_ACIER`. `hsnv101a`/`hsnv102a` zijn AXIS:
alleen bron voor materiaal- en TRC-syntax. **Uitzoeken:** invoer van TRC-gegevens
(`#ASTER`-sleutelwoord of databestand); fasevelden naar Mecway.
**Klaar als:** 3D-staaf met opgelegde T(t): fasefracties binnen 1% van de
TEST_RESU-waarden van `hsnv101a`.
**Bevindingen:** Invoerroute (docs/Lassen.md §10): `#ASTER-METALLURGIE <Mecway-
materiaal>: staal=16MND5 | trc=<DEFI_TRC uit #ASTER-code>, ...` (`bridge_metallurgy.py`;
vorm zoals `#ASTER-MATERIAAL`). Standaard-datasets met bron: `16MND5` (testcase
mtlp103a, V4.61.103: TRC met 29 geschiedenissen, META_ACIER, DURT_META, GRAIN_AUST) en
`HSNV101A` (testcase hsnv101a, incl. de mechanische gegevens per fase). `META_ACIER` /
`DURT_META` in de thermische `DEFI_MATERIAU` (een aparte CHAM_MATER gaf per stap
`RESULT1_39`; alleen bij een eigen `trc=` nodig, want #ASTER-code staat na de
materialen), `CALC_META` (`ACIER`) na de thermische solve; velden `ferrite`,
`pearlite`, `bainite`, `martensite`, `austenite`, `hardness` per tijdstap (groep
`metallurgy`), samenvatting met de WBZ in log/statusvak. Optie `mechanica=ja` in de
keten S4b: `ELAS_META_FO` + `META_ECRO_LINE`, `META_P_IL`, `AFFE_VARC M_ACIER`
(`ALPHA_A`, `DEPS`, vloeigrens/helling per fase). Verificatie MT-01..08
(`tests_lassen_meta.py`, groep "Metallurgie"): (a) hsnv101a in 3D: fasen ≤ 1,3·10⁻⁶
t.o.v. de testcase zelf (hsnv101a heeft geen TEST_RESU op fasen; AXIS-run met
CREA_TABLE), en met de metallurgische wet de TEST_RESU σ ≤ 5·10⁻⁷, ε ≤ 5·10⁻⁵ (tol.
1%); (b) Koistinen-Marburger (16MND5, 1000 °C/s; eigen TRC MT-08) ≤ 4·10⁻⁸ en
austenitiseren bij opwarmen ≤ 2·10⁻⁸ tussen Ac1 en Ac3 (0,22% vlak boven Ac3);
(c) transformatierek vrije staaf en spanning ingeklemde staaf ≤ 6·10⁻⁶ t.o.v. de
hand; lasrups MT-06 (WBZ, hardheid) en MT-07 (restspanning met fasen, 14 min)
kwalitatief: de martensietuitzetting verlaagt σxx in de las van 466/641 naar 176/4
MPa (boven/midden, hex8). Gemeten gedrag (KNOWN_BUGS 72): austenitisering loopt bij
snel opwarmen met grote ΔT per stap achter (dataset-τ 0,34 s: lasas 6% austeniet;
advies en WARNING: `TAUX_1=TAUX_3=0.001`), martensiet stopt bij ~0,7% austeniet,
16MND5 geeft bij 200 °C/s nog 3% bainiet; bij `META_P_IL` geen
`equivalentplasticstrain` (V7 is een spanning). Regressie 1037/1040 OK, 3 BEKEND (NL-03a, KNOWN_BUGS 43), 0 NOK/FOUT; Lassen.md is hernummerd (§10 Metallurgie, §11 Verificatie, §12 Bronnen). Open: Mecway-GUI-test
(velden per tijdstap, statusvak). Vragen gebruiker: (1) TAUX van 16MND5 standaard op
0,001 s zetten voor lassen (nu getrouw aan mtlp103a 0,34 s, met WARNING)? (2)
mechanische fasegegevens voor 16MND5 (of S355) uit de literatuur als dataset
opnemen? (3) een TRC-diagram voor constructiestaal (S355) nodig? (4) ontlaten
(`ACIER_REVENU`) bij meerlaags lassen en transformatieplasticiteit (`META_PT`) als
vervolgstap (splitsen als S5b)?

### S9 – Loadcase-combinaties (go/no-go)
Mecway heeft geen load cases meer: ze worden omgezet naar **configuraties** (manual §2.8;
API `mw.set_active_configuration`). **Eerst go/no-go:** kunnen configuraties met
factoren goed lastgevallen uitdrukken die de bridge uit de `.liml` leest? Zo niet: stap
op **vervallen** met de reden, documenteren, niets bouwen.
**Code-Aster:** `MACRO_ELAS_MULT` (één factorisatie, meerdere `CAS_CHARGE`), combinaties
en omhullende via `CREA_CHAMP`/`CALC_CHAMP`. 3D-testcase `sdlv128a` (4 `NOM_CAS`); ook
`ssll101c`, `ssll106a`.
**Klaar als:** de combinatie is gelijk aan de lineaire superpositie van losse runs
(≤ 1e-6 relatief).
**Bevindingen:** **No-go, vervallen** (7 okt 2026). (1) Een configuratie in de `.liml`
is alleen `<configuration name=".."/>` bovenaan plus per lastitem/voorwaarde een kind
`<suppressed configuration=".."/>` (Samples/CylinderLifting, Tutorials/AssemblyWithContact,
eigen testmodel); er is geen factor, geen per-configuratie-waarde en geen actieve
configuratie in het bestand (mecway.exe: alleen "Suppress/Unsuppress in all
configurations", tabbladmenu New/Delete/Rename, "Solve all configurations"; manual
§2.8: "suppress and unsuppress loads and constraints"; de oude load cases worden bij
het openen configuraties). Solution-formules (manual §10.11) werken op de actieve
solution. Een combinatie 1,2 G + 1,5 Q kan de gebruiker dus alleen als eigen
configuratie met gedupliceerde, met de hand gefactoreerde lastitems invoeren; de
factoren staan dan nergens, dus de bridge kan geen `MACRO_ELAS_MULT` + combinatie/
omhullende afleiden. (2) Mecway headless (`mw_solve.py`) rekent alle configuraties,
elk een `<solution configuration="..">` met een modelkopie waarin onderdrukte items
`suppressed="true"` zijn. Model balk hex20 met G (gravity), Q (druk) en ULS (eigen
gravity 1,2 g en druk 1,5 q): Mecway ULS = 1,2 G + 1,5 Q op 3e-15 (verplaatsing,
relatief t.o.v. max); bridge op een kopie met alleen configuratie ULS = Mecway ULS op
1,0e-9 (diagnose OK). (3) De bridge rekent één configuratie per run (de enige zonder
onderdrukte items, anders de eerste) en kan de actieve niet lezen; werkwijze voor
lastgevallen (kopie per configuratie) in `docs/Handleiding.md` §4 + EN; de onterechte
WARNING bij één configuratie als KNOWN_BUGS 68 (opgelost 15 okt: instelling
Configuratie op het startscherm, verificatie LS-20). Niets gebouwd. **Open vragen:** (a)
Toch een eigen invoer voor factoren (bijv. `#ASTER-COMBINATIE ULS = 1.2*G + 1.5*Q`
op configuratienamen) met `MACRO_ELAS_MULT` en omhullende, buiten Mecway om? (b) Een
keuzelijst "Configuratie" op het startscherm (namen uit de `.liml`, daarna
`mw.set_active_configuration`) of alle configuraties in één run met `MACRO_ELAS_MULT`
(zelfde randvoorwaarden), zonder factoren?

### S13 – Orthotrope en anisotrope materialen
**Doel:** Mecway-materialen *Orthotropic* en *Anisotropic* (stijfheids- of compliantiematrix)
vertalen in plaats van de run te stoppen, met Mecway's *Element orientation* (per element
`orientationux`…`vz`, `angle`) als materiaalrichting; ook in schalen.
**Code-Aster:** `DEFI_MATERIAU` `ELAS_ORTH` (en `ELAS_ISTR`), anisotroop via `ELAS_ORTH` als dat
volstaat, anders NIET mogelijk melden; richting met `AFFE_CARA_ELEM` `MASSIF` `ANGL_REP`/`ANGL_EULER`
per element(groep), schalen `COQUE` `ANGL_REP`/`VECTEUR`; composiet `DEFI_COMPOSITE`.
**Uitzoeken:** Mecway's XML van Orthotropic/StiffnessMatrix/ComplianceMatrix (Samples, mecway.exe),
de definitie van U/V en `angle` (manual §7), hoe Mecway spanningen in lokale assen toont; groeperen
van elementen met dezelfde oriëntatie; thermische orthotropie (`THER_ORTH`).
**Klaar als:** een orthotrope balk in twee oriëntaties (analytisch, buiging met E_L en E_T) en een
geroteerd blok onder trek (Hooke in lokale assen) binnen 1%, en gelijk aan Mecway headless; regressie D.5.

### S14 – Hyperelastisch materiaal
**Doel:** Mecway *Neo Hooke* en *Mooney-Rivlin* vertalen (nu: WARNING en de run stopt).
**Code-Aster:** `ELAS_HYPER` (C01, C10, C20, K) met `RELATION='ELAS_HYPER'`, `DEFORMATION='GDEF_LOG'`
of `'GREEN_LAGRANGE'` in `STAT_NON_LINE`; testcases `ssnv187a`, `ssnp154`.
**Uitzoeken:** Mecway's parameters en eenheden (XML), bijna-onsamendrukbaarheid (`INCO_UPG`?),
welke analyses (alleen niet-lineair).
**Klaar als:** uniaxiale trek tot 100% rek gelijk aan de analytische Neo-Hooke-/Mooney-Rivlin-curve
(≤ 1%) en aan Mecway headless; regressie D.5.

### S15 – Pre-tension section (boutvoorspanning)
**Doel:** Mecway's *Pre-tension section* (`pretensionsection`, Samples/BoltedJoint) vertalen.
**Code-Aster:** voorspanning via een opgelegde verkorting over een snede (`LIAISON_DDL` tussen de
twee kanten van de snede, of de bout opknippen met `CREA_MAILLAGE` en `DDL_IMPO`), in twee fasen:
eerst kracht, dan vastgezet (`STAT_NON_LINE` met twee lasten/`ETAT_INIT`); alternatief thermische
krimp. Code-Aster-documentatie over boutvoorspanning nagaan (U2-doc).
**Uitzoeken:** Mecway's XML (snedevlak, kracht of verkorting, fasen), gedrag in lineair statisch.
**Klaar als:** BoltedJoint: boutkracht na voorspannen = opgegeven kracht (≤ 1%), resultaten gelijk aan
Mecway headless binnen de bekende contactverschillen (KNOWN_BUGS 43); regressie D.5.

### S16 – 2D- en axisymmetrische analyses
**Doel:** Mecway's 2D-analysetypen (S20, D20, SA0, ook A20 en thermisch 2D) vertalen; nu stopt de run.
**Code-Aster:** modelisaties `C_PLAN`, `D_PLAN`, `AXIS` (thermisch `PLAN`/`AXIS`, akoestiek `2D_FLUIDE`);
mesh in het XY-vlak, dikte bij vlakspanning; resultaten terug in Mecway's 2D-velden.
**Uitzoeken:** Mecway's 2D-elementen en dikte-invoer, analysecodes (DA0, V20 komen voor in mecway.exe),
welke lasten/voorwaarden in 2D bestaan, Mecway's veldnamen voor 2D/axisymmetrisch (hoepelspanning).
**Klaar als:** plaat met gat in vlakspanning (Kt), dikwandige cilinder axisymmetrisch (Lamé) en een
2D-dynamisch geval binnen de toleranties van de 3D-tegenhangers en gelijk aan Mecway headless;
regressie D.5. Mag in deelstappen (S16a statisch, S16b dynamisch/thermisch/akoestiek).

### S17 – Lasten op balkzijvlakken en hydrostatische druk op schaalranden
**Doel:** de twee open punten van KNOWN_BUGS 5: druk/traction op het zijvlak van een balk (Mecway
rekent ze als verdeelde balklast) en hydrostatische druk op schaalranden.
**Code-Aster:** `FORCE_POUTRE` (ook als functie van X, Y, Z via `AFFE_CHAR_MECA_F`); schaalranden via
`FORCE_ARETE` of knoopkrachten zoals `bridge_mesh._edge_loads`.
**Klaar als:** balk met druk op een zijvlak = balk met de equivalente lijnlast (≤ 0,1%) en gelijk aan
Mecway headless; hydrostatische druk op een schaalrand gelijk aan de handberekening; regressie D.5.

### S18 – Nieuwe Code-Aster-versie (18) testen
**Doel:** de bridge met Code-Aster 18 laten werken en die versie als getest opnemen; tot dan geeft
een run met 18 alleen een WARNING (`bridge_version.py`, `TESTED_ASTER_VERSIONS` in `bridge_utils.py`).
**Voorwaarde:** Code-Aster 18 voor Windows (code-aster-windows.com) is beschikbaar; tot dan status later.
**Code-Aster:** sleutelwoorden in de templates (`AsterTemplate_*.comm`) en de gegenereerde `.comm`
tegen de catalogus van 18; de Python-API in de job (`aster_results_export.py`, `aster_spectrum.py`,
`aster_acoustic_export.py`, `aster_acoustic_complex.py`, `aster_cyclic.py`, `aster_fatigue.py`);
de `.mess`-tekst die `bridge_version.py`, `bridge_convergence.py` en `bridge_run_aster.py` lezen (versieregel,
convergentietabel, DIAGNOSTIC JOB).
**Uitzoeken:** de release notes van 18 (vervallen/hernoemde sleutelwoorden), het standaardpad van de
launcher (`exe_aster`) en of 17.4 en 18 naast elkaar geïnstalleerd kunnen blijven.
**Klaar als:** volledige regressie (`run_verificatie.py`) met 0 NOK/FOUT en dezelfde BEKEND als de
basislijn in docs/Verificatie.md §3, de officiële Code-Aster-tests (`run_code_aster_tests.py`) alle OK,
templates/API aangepast waar nodig (17.4 blijft werken of het besluit om 17.4 te laten vallen staat in
CHANGELOG.md), `TESTED_ASTER_VERSIONS` bijgewerkt en docs (Handleiding, Na_een_update, Verificatie) NL+EN
nagelopen; regressie D.5.
