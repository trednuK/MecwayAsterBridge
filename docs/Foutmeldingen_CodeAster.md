# Foutmeldingen van Code-Aster: oorzaak en oplossing

*English version: [CodeAster_error_messages.md](en/CodeAster_error_messages.md)*

Naslag van de Code-Aster-meldingen (fouten en alarmen) die bij het bouwen, testen en
verifiëren van de bridge zijn voorgekomen. Per code: de betekenis, de gebruikelijke
oorzaak in een Mecway-model, waar de melding gezien is, de oplossing en de status.
Code-Aster-versie: 17.4.0 (Windows-build, gewijzigd 22-01-2026, zie de kop van elke
`.mess`).

De meldingsteksten komen uit de berichtencatalogus van de installatie (EDF R&D, 2026a):
`FACTOR_57` staat in `Messages/factor.py` onder nummer 57, `MECANONLINE9_7` in
`Messages/mecanonline9.py` onder 7, enzovoort. "Gezien" betekent: in een echte run
(Mecway, Code-Aster rechtstreeks of het verificatiekader `TestFiles/Verificatie`).
"Afgeleid uit de code" betekent: de bridge vermijdt de melding op grond van een eerdere
run, beschreven in het commentaar van de genoemde functie. Commitnummers verwijzen naar
de Git-geschiedenis van de bridge.

**Status** per melding:

- **opgelost in de bridge**: de bridge voorkomt de melding, of meldt de oorzaak vooraf;
- **model**: de oorzaak zit in het Mecway-model; pas het model aan;
- **beperking**: Code-Aster kan het niet; er is een omweg of niets aan te doen;
- **onschuldig**: verwacht alarm; de resultaten kloppen;
- **eigen invoer**: de oorzaak zit in eigen `#ASTER`-regels of een aangepaste `.comm`;
- **oorzaak niet vastgesteld**: gezien, maar niet uitgezocht.

Fouten in de bridge zelf staan in `KNOWN_BUGS.md`; hier staat alleen de verwijzing.

---

## Inhoud

- [De melding vinden](#de-melding-vinden)
- [Een melding toevoegen](#een-melding-toevoegen)
- [1. Mesh en groepen](#1-mesh-en-groepen)
- [2. Model, elementen en belastingen](#2-model-elementen-en-belastingen)
- [3. Randvoorwaarden en singuliere matrix](#3-randvoorwaarden-en-singuliere-matrix)
- [4. Contact](#4-contact)
- [5. Niet-lineaire berekening en dynamica](#5-niet-lineaire-berekening-en-dynamica)
- [6. Grote rotaties](#6-grote-rotaties)
- [7. Nabewerking](#7-nabewerking)
- [8. Syntax en `#ASTER`-regels](#8-syntax-en-aster-regels)
- [9. Systeem, oplosser en vervolgfouten](#9-systeem-oplosser-en-vervolgfouten)
- [10. Modaal en knik](#10-modaal-en-knik)
- [11. Foutschatter](#11-foutschatter)
- [Codes op alfabet](#codes-op-alfabet)
- [Aannames](#aannames)
- [Bronnen](#bronnen)

---

## De melding vinden

Alle bestanden van een run heten `<model>_<run-id>.*` (zie
[Handleiding §5](Handleiding.md#5-bestanden-in-de-werkmap)); hieronder kort `.mess`,
`.comm` en `.export`. Meldingen van de bridge noemen de echte bestandsnaam.

1. **In Mecway.** Na de run toont de bridge de fouten uit de `.mess` in het statusvak
   van het hoofdvenster (zonder hoofdvenster: als Mecway-melding)
   (`bridge_run_aster.aster_mess_errors`): de code, de tekst uit het meldingskader en,
   bij een bekende code, uitleg in de gekozen taal (`_MESS_HINTS` in
   `Scripts/bridge_run_aster.py`):
   - `FACTOR_10`, `FACTOR_11`, `FACTOR_42`, `FACTOR_57`: singuliere stijfheidsmatrix;
   - `MECANONLINE9_4`: idem, met de aanvulling voor een pivot op `LAGS_C`
     (contact): *Contactmethode* = PENALISATION (niet `solver_nprec` = -1: dat rekent
     wel door, maar is onnauwkeurig, −1,6% / +2,8% in NL-03a, R-NPREC-CONTACT in
     [Standaardinstellingen §5](Standaardinstellingen_en_aannames.md#5-controleruns-bij-deze-review));
   - `MECANONLINE9_7`: Newton convergeert niet, met de vervolgstappen (zie
     [`MECANONLINE9_7`](#mecanonline9_7--newton-convergeert-niet)) en "Laatste tijdstip
     met resultaten: ... s" als de job `BRIDGE_ONVOLLEDIG <tijd>` schreef;
   - `ALGELINE3_81`, `ALGELINE5_49`, `ALGELINE3_78`: modaal en knik (§10);
   - `ALGORITH16_52`, `ALGORITH16_58`, `ALGORITH14_94`: cyclische symmetrie (§10).

   Alarmen (`<A>`) komen niet in die melding, maar als
   `WARNING: Code-Aster-alarm <CODE> in <model>_<run-id>.mess.` in
   `<model>_<run-id>_bridge_log.txt`; voor `ALGELINE5_23`, `ALGELINE3_82`,
   `ALGELINE2_74`, `MODELISA4_8`/`MODELISA8_13` (dubbele cellen) en, bij complexe modes,
   `ALGELINE5_79` en `FACTOR_11` met uitleg (`_ALARM_HINTS`):
   `WARNING: Code-Aster-alarm <CODE> in <model>_<run-id>.mess: <uitleg>`. Het convergentie- en meldingenscherm toont fouten en alarmen per
   run, met uitleg bij een pivot nul per soort vrijheidsgraad
   (`bridge_convergence.pivot_hint`; [Instellingen §4.4](Instellingen_contact_en_nietlineair.md#44-convergentiescherm)).
2. **De `.mess` in de werkmap** (`work_dir`). Zoek op:
   - `<EXCEPTION>`, `<F>`, `<S>`, `<E>`: fout; de job stopt of slaat de commando's
     erna over;
   - `<ConvergenceError>`, `<SolverError>`, `<IntegrationError>` en andere
     `<...Error>`: fout in `STAT_NON_LINE`/`DYNA_NON_LINE`; de bridge vangt die op en
     gaat door met de nabewerking (resultaten tot het laatst bereikte tijdstip);
   - `<A>`: alarm, de job gaat door;
   - `<I> <CATAMESS_89>` aan het eind: alle alarmen met hun aantal.

   Boven het kader staat het commando met `# Commande #00nn de ....comm.changed.py,
   ligne N`. `N` is het regelnummer in de door Code-Aster aangepaste kopie van de
   `.comm`; meestal gelijk aan de `.comm` zelf (NIET voor elk geval geverifieerd). De
   laatste regel `--- DIAGNOSTIC JOB : ...` zegt `OK`, `<A>_ALARM` of
   `<F>_ABNORMAL_ABORT`. Let op: ook na een `<EXCEPTION>` staat daar soms `OK` of
   `<A>_ALARM` (gezien: `FACTOR_42` met `DIAGNOSTIC JOB : OK`). Beoordeel een run dus
   op de meldingskaders, niet op die regel; de bridge doet dat ook.
3. **`<model>_<run-id>_bridge_log.txt`** in de werkmap: fouten vóór Code-Aster
   (ERROR/WARNING per stap), hernoemde groepen (`INFO: Group name 'x' -> 'y'`),
   samengevoegde contactzones, overgeslagen belastingen.
4. **Geen meldingskader.** Bij `<F>_ABNORMAL_ABORT` zonder kader staat de oorzaak
   alleen in het Code-Aster-venster (dat blijft dan open). Ontbreekt `<FIN>` in de
   `.mess`, dan is de `.comm` niet tot het eind uitgevoerd (Python-fout); de bridge
   meldt "Python-fout in `<model>_<run-id>.comm`" met de foutregel uit
   `<model>_<run-id>_console.txt` ([§8](#8-syntax-en-aster-regels)).
   Eindigt `run_aster` met een exitcode ongelijk aan 0, dan meldt het statusvak
   "run_aster eindigde met exitcode N (fout)" met het pad van de `.mess`; ook dan blijft het
   Code-Aster-venster open. Een run die met *Stoppen...* is gestopt (of waarvan het
   Code-Aster-venster is gesloten) heeft geen `DIAGNOSTIC JOB`: de `.mess` is de uitvoer tot
   dat moment met als laatste regel `BRIDGE_GESTOPT` ([Handleiding §2](Handleiding.md#2-werkwijze)
   stap 5).
5. **Opnieuw draaien zonder Mecway**: `run_aster.bat <model>_<run-id>.export` in de
   werkmap. Zo kun je de `.comm` van die run met de hand aanpassen en een oplossing
   proberen.

## Een melding toevoegen

Kopieer dit blok onder het juiste thema en vul elk veld in; onbekend:
"niet vastgesteld" of "NIET geverifieerd".

```markdown
### `CODE` – korte titel

- **Melding** (fout/alarm): Nederlandse samenvatting van de tekst.
- **Oorzaak in een Mecway-model**: ...
- **Gezien**: testmodel/situatie (en commit van de oplossing).
- **Oplossing**: in Mecway: ... / in de bridge: ... / met `#ASTER`-regels: ...
- **Status**: opgelost in de bridge | model | beperking | onschuldig | eigen invoer | oorzaak niet vastgesteld.
```

Zet de code ook in [Codes op alfabet](#codes-op-alfabet) en in de Engelse versie.
Geeft de bridge er uitleg bij, zet de code dan in `_MESS_HINTS` (fout) of
`_ALARM_HINTS` (alarm) in `Scripts/bridge_run_aster.py`.

---

## 1. Mesh en groepen

De bridge schrijft het mesh zelf in het ASTER-formaat (`Scripts/bridge_mesh.py`,
`LIRE_MAILLAGE FORMAT='ASTER'`). Meldingen in dit thema wijzen bijna altijd op een fout
in dat bestand, niet op het model.

### `MODELISA7_85` – getal verwacht in het mesh

- **Melding** (fout): "(LIGNE n) un nombre est attendu": op regel n staat geen getal
  dat Code-Aster kan lezen.
- **Oorzaak**: een coördinaat als `-1e-05` (zonder decimale punt) wordt niet als getal
  gelezen.
- **Gezien**: een knipmodel (dynamisch, contact).
- **Oplossing**: in de bridge: `bridge_mesh._real` schrijft altijd een decimale punt
  (`-1.0e-05`) (commit 117dba3).
- **Status**: opgelost in de bridge.

### `MODELISA7_66` – item verwacht aan het begin van de regel

- **Melding** (fout): "(LIGNE n) item attendu en début de ligne".
- **Oorzaak**: (a) een regel langer dan 80 tekens (HEXA20 met lange knoopnamen);
  (b) een getal met een komma (`0,25`): `"{0:.15g}".format()` volgt in Mecway's
  IronPython de Nederlandse landinstelling.
- **Gezien**: (a) hex20-balk met pinned support; (b) IronPython-testharness.
- **Oplossing**: in de bridge: regels afgebroken op 79 tekens (`bridge_mesh._wrap`,
  commit f9ac7f9) en `%`-opmaak in `_real` (commit 543fe80).
- **Status**: opgelost in de bridge.

### `MODELISA7_81` – geen geldige naam

- **Melding** (fout): "un identificateur est attendu : 'x' n'en est pas un".
- **Oorzaak**: een groepsnaam die met een cijfer begint (`02ContactProfiel`) of haakjes
  bevat (`Linear(2)`). Mecway staat zulke namen toe.
- **Gezien**: naamtest met namen als `02ContactProfielToRol`, `13FixZ`.
- **Oplossing**: in de bridge: `bridge_mesh._aster_names` hernoemt (bijv.
  `G02ContactProfiel`) en logt dat; gebruik in `#ASTER`-regels `<<Mecway-naam>>`
  (commit 93eaa5f).
- **Status**: opgelost in de bridge.

### `MODELISA5_7` – maille bestaat niet

- **Melding** (fout): "La maille b déclaré dans le GROUP_MA a n'existe pas dans les
  connectivités".
- **Oorzaak**: een groepsnaam met `.` of `-` (`a.b`, `Fix-Z`): de lezer splitst de naam.
- **Gezien**: naamtest (zie `MODELISA7_81`).
- **Oplossing**: als bij `MODELISA7_81`.
- **Status**: opgelost in de bridge.

### `MODELISA7_82` – interne fout bij lange groepsnaam

- **Melding** (fout): "message d'erreur développeur", zonder uitleg.
- **Oorzaak**: een groepsnaam van meer dan 24 tekens (24 gaat goed, 25 niet).
- **Gezien**: naamtest bij de overstap van Gmsh naar het ASTER-formaat.
- **Oplossing**: in de bridge: namen worden ingekort tot 24 tekens en uniek gemaakt
  (`ASTER_NAME_MAX`, `_aster_names`; commit 93eaa5f).
- **Status**: opgelost in de bridge.

### `MODELISA_1` – mesh niet te lezen

- **Melding** (fout): "Problème à la relecture du fichier de maillage".
- **Oorzaak**: vervolg op een eerdere meshmelding (`MODELISA7_66`, `_81`, `_85`).
- **Gezien**: samen met die meldingen.
- **Oplossing**: los de eerste melding op.
- **Status**: opgelost in de bridge (via de oorzaken hierboven).

### `MODELISA4_80` – groep leeg

- **Melding** (alarm): "le groupe X est vide. On l'ignore."
- **Oorzaak**: de vroegere Gmsh-route kapte groepsnamen af op 8 tekens; de groep onder
  de volledige naam bleef leeg.
- **Gezien**: naamtest met de Gmsh-route.
- **Oplossing**: in de bridge: geen Gmsh meer, het mesh komt rechtstreeks uit de
  `.liml` (commit 93eaa5f). Zie je dit alarm nu, dan is een selectie in Mecway
  waarschijnlijk echt leeg.
- **Status**: opgelost in de bridge.

### `MODELISA7_75`, `MODELISA7_77` – groep bestaat niet

- **Melding** (fout): "le GROUP_NO X ne fait pas partie du maillage" (`7_75`) of "le
  GROUP_MA X ne fait pas partie du maillage" (`7_77`).
- **Oorzaak**: (a) een `#ASTER`-regel noemt een selectie die niet bestaat (tikfout);
  (b) een randvoorwaarde, last of koppeling op een lege of ontbrekende selectie.
- **Gezien**: (a) tests van `ASTER_regels_voorbeelden.md`; (b) afgeleid uit de code
  (`bridge_mesh`, commentaar bij het overslaan van lege selecties).
- **Oplossing**: (a) de bridge logt eerst
  `ERROR: #ASTER: selectie 'X' bestaat niet in het mesh.` (nagelopen 06-10-2026);
  controleer de naam in Mecway, de hernoemde namen staan in de log. (b) in de bridge:
  zo'n voorwaarde of koppeling wordt overgeslagen en gemeld (`skipped_loads`).
- **Status**: eigen invoer (a) / opgelost in de bridge (b).

### `MODELISA6_10` – maille niet in het mesh

- **Melding** (fout): "la maille X ne fait pas partie du maillage Y".
- **Oorzaak**: een groep met mailles op naam (`M<eid>`) waar Code-Aster het
  volgnummer van de cel verwacht.
- **Gezien**: afgeleid uit de code (`bridge_thermal._list_group`; element-ID's +1000
  gaven deze fout).
- **Oplossing**: in de bridge: het Mecway-elementnummer wordt vertaald naar het
  celnummer in het mesh (`model_data["cell_names"]`).
- **Status**: opgelost in de bridge.

### `MODELISA5_8` – maille dubbel in een groep

- **Melding** (alarm): "La maille X est en double dans le GROUP_MA Y. On élimine les
  doublons."
- **Oorzaak**: een vlakselectie met vlak 5 én 6 van hetzelfde schaalelement.
- **Gezien**: afgeleid uit de code (`bridge_mesh`, `bridge_thermal`).
- **Oplossing**: in de bridge: elke cel één keer per groep; een thermische last op
  beide zijden van een schaal krijgt een eigen groep met factor 2.
- **Status**: opgelost in de bridge.

### `SOUSTRUC_37`, `SOUSTRUC_38` – knoopgroep bestaat al / is leeg

- **Melding**: `SOUSTRUC_37` (fout): de knoopgroep bestaat al; `SOUSTRUC_38` (alarm):
  de knoopgroep is leeg en wordt niet gemaakt.
- **Oorzaak**: het aanvullen van knoopgroepen na `CREA_MAILLAGE LINE_QUAD` en de groep
  met middenknopen van `COQUE_3D`-schalen.
- **Gezien**: afgeleid uit de code (`bridge_to_aster`, `_LQ_GROUPS` en de groep met
  QUAD9/TRIA7-middenknopen).
- **Oplossing**: in de bridge: een bestaande groep eerst verwijderen
  (`DETR_GROUP_NO`); schaalranden niet in de middenknoopgroep.
- **Status**: opgelost in de bridge.

### `UTILITAI5_1` – bestand bij een unit ontbreekt

- **Melding** (fout): "Le fichier de nom 'fort.19' associé à l'unité logique 19
  n'existe pas."
- **Oorzaak**: de `.export` noemt een meshbestand dat er niet is.
- **Gezien**: offline testharness met de vroegere Gmsh-route.
- **Oplossing**: controleer de regels `F ... D <unit>` in de `.export`; laat de bridge
  `work_dir` en de `.export` zelf maken.
- **Status**: oorzaak in de testopzet, niet in de bridge.

### `MODELISA4_6` / `MODELISA8_11` – weesknopen

- **Melding** (alarm): "présence de noeuds orphelins" / "Le noeud N est orphelin".
- **Oorzaak**: losse knopen in het Mecway-model (hulpknopen, knopen die na het
  verwijderen van elementen zijn blijven staan).
- **Gezien**: volumemodel R_Voorbeeld; test C6_elastic.
- **Oplossing**: onschuldig zolang er geen last of oplegging op die knoop staat; anders
  een singuliere matrix (`FACTOR_*`). In Mecway: losse knopen verwijderen of verbinden.
- **Status**: onschuldig (meestal).

### `MODELISA4_8` / `MODELISA8_13` – dubbele elementen

- **Melding** (alarm): "présence de mailles doubles" / "Les mailles A et B sont doubles".
- **Oorzaak**: (a) twee vlakselecties op dezelfde vlakken: elk vlak werd twee keer als
  randelement geschreven; (b) een veer en een demper tussen dezelfde knopen; (c)
  vibro-akoestiek: een schaal op een fluïdumvlak en zijn koppelvlak (`FLUI_STRU`) zijn
  aparte cellen op dezelfde knopen.
- **Gezien**: (a) een gemengd testmodel (RBE); (b) demper-test D18_damper; (c)
  verificatie VA-03, VA-05 (frequenties exact).
- **Oplossing**: in de bridge: (a) een vlakselectie met dezelfde vlakken als een eerdere
  groep wordt een kopie (`DEFI_GROUP CREA_GROUP_MA`, commit 631cc36); (b), (c) bedoeld
  (een cel kan maar één modellering hebben).
- **Status**: opgelost in de bridge (a) / onschuldig (b, c).

### `MODELISA8_14` – POI1 in een ander element

- **Melding** (alarm): "La maille POI1 N est incluse dans une autre."
- **Oorzaak**: een puntelement (puntmassa, veer naar de grond, RBE-masterknoop) op een
  knoop die ook bij een ander element hoort.
- **Gezien**: tests met puntmassa, centrifugaalbelasting, demper en gap-elementen; ook in
  de officiële testcases ssls114a en sdls115a (`Verificatie.md`).
- **Oplossing**: geen; bedoeld.
- **Status**: onschuldig.

### `MESH1_4` – LINE_QUAD op een deel van het mesh

- **Melding** (alarm): alleen een deel van de cellen wordt kwadratisch; dat kan een
  niet-conform mesh geven.
- **Oorzaak**: *Lineaire schalen* = `COQUE_3D` in een model met ook andere elementen:
  de bridge maakt alleen de schaalgroepen kwadratisch (`_resolve_line_quad`).
- **Gezien**: afgeleid uit de code en de catalogustekst (`mesh1.py`); NIET in een
  bewaarde `.mess` nagelopen.
- **Oplossing**: geen nodig als de bridge het koos: dat doet hij alleen als de schalen
  geen knopen delen met elementen die lineair blijven (anders DKT met een WARNING).
- **Status**: onschuldig.

---

## 2. Model, elementen en belastingen

### `MODELISA_78` – afschuifcoëfficiënt ontbreekt (balk)

- **Melding** (alarm): "section GENERALE élément poutre : il manque la caractéristique
  AY1" (of AZ1); daarna `DVP_2`.
- **Oorzaak**: `POU_D_T` met een algemene doorsnede (`SECTION='GENERALE'`) zonder AY/AZ.
- **Gezien**: testmodel met alle Mecway-profieltypen.
- **Oplossing**: in de bridge: standaard *Balken* = `POU_D_E` (Euler-Bernoulli, zoals
  Mecway; commit e772fab). Met `POU_D_T` berekent de bridge AY/AZ uit het profiel
  (`bridge_from_liml._profile_shear_coefs`); onbekend profiel: AY = AZ = 1 met een
  WARNING.
- **Status**: opgelost in de bridge.

### `DVP_2` – floating point exception

- **Melding** (fout): "Erreur numérique (floating point exception)".
- **Oorzaak**: (a) `POU_D_T` met `SECTION='GENERALE'` zonder AY/AZ (zie `MODELISA_78`);
  (b) `POU_D_T_GD` met `RELATION='ELAS'`; die balk vraagt `ELAS_POUTRE_GR` (testcase
  ssnl103a, EDF R&D, 2026c); (c) vibro-akoestiek: `NORM_MODE MASS_GENE` op een valse
  mode met negatieve gegeneraliseerde massa (gezien bij een schaal met maar één rotatie
  vast; de bridge filtert die modes nu eerst, [`Akoestiek.md`](Akoestiek.md) §6.5);
  (d) niet-lineair (`STAT_NON_LINE`, optie `FULL_MECA`, bijv. `MECA_HEXA8`): een element
  is zo sterk vervormd (bijna platgedrukt of binnenstebuiten) dat de integratie van de
  materiaalwet overloopt, bijv. hyperelastisch (`ELAS_HYPER`) met een grote opgelegde
  verplaatsing.
- **Gezien**: (a) profieltest; (b) proeven voor grote rotaties; (d) GitHub-issue #5
  (Neo Hooke, maille 495).
- **Oplossing**: (a) zie `MODELISA_78`; (b) met `elem_beam` = `POU_D_T_GD` zet de bridge
  zelf `ELAS_POUTRE_GR` ([Instellingen §2.9](Instellingen_contact_en_nietlineair.md#29-balken-met-grote-rotaties-elem_beam--pou_d_t_gd)); alleen eigen code met
  `POU_D_T_GD` en `ELAS` geeft deze fout; (d) de job houdt de stappen die vóór de fout
  geconvergeerd zijn: hij schrijft `BRIDGE_ONVOLLEDIG <tijd>`, laadt de resultaten tot
  dat tijdstip en Mecway toont `DVP_2` met "Laatste tijdstip met resultaten: ... s"
  ([Instellingen §4.1](Instellingen_contact_en_nietlineair.md#41-wat-de-bridge-dan-doet)).
  Kijk naar het laatste resultaat waar het net het sterkst vervormt, en maak de stappen
  kleiner (*Time step size* in Mecway), gebruik kwadratische elementen of een fijner net
  op die plek, of verklein de belasting.
- **Status**: opgelost in de bridge (a, b); (d) melding, resultaten tot de fout.

### `CALCUL_37` – element kan deze optie niet

- **Melding** (fout): "Le TYPE_ELEMENT X ne sait pas encore calculer l'option: Y".
- **Oorzaak**, zes gevallen:
  1. `MECA_HEXS8` (hex8 als `3D_SI`) kan `PAS_COURANT` niet (stabiele tijdstap bij
     expliciete dynamica);
  2. `MECA_POU_D_T_GD` kan `RIGI_MECA` niet (`PREDICTION='ELASTIQUE'` of
     `MATRICE='ELASTIQUE'` met een GD-balk; de bridge zet `PREDICTION='ELASTIQUE'` na
     een bezweken element, [`Bezwijken.md`](Bezwijken.md));
  3. `MEDKQU4` (DKT) en `MECA_DIS_T_N` (discreet element) kunnen `CHAR_MECA_ROTA_R`
     niet (centrifugaalbelasting met schalen of discrete elementen);
  4. formaten-testmodel F4_model (dynamica): element en optie niet nagelopen;
  5. `MECABL2` (kabel, tension only) kan `ROTATION` niet;
  6. `MECA_POU_D_T_GD` kan ook `RIGI_MECA` in een lineaire analyse, `SIPM_ELNO`
     (balkspanning) en `CHAR_MECA_ROTA_R` (centrifugaalkracht) niet;
  7. `MECA_BARRE` (truss, line2 en line3) en de kabel kunnen `RIGI_GEOM` niet
     (geometrische stijfheid van lineaire knik; GitHub-issue #6).
- **Gezien**: 1 expliciete dynamica met `3D_SI`; 2 balkproeven en een run met een
  bezwijkende hex8-staaf naast een GD-balk; 3 en 4 tests van de belastingen; 5
  code-review (commit 6ce5cba); 6 proeven met `POU_D_T_GD`.
- **Oplossing**: 1 de bridge kiest bij een expliciet schema altijd `3D` (WARNING);
  2 bezwijken van elementen in een model met `POU_D_T_GD`-balken geeft vooraf een ERROR
  (met `PREDICTION='TANGENTE'` of `'EXTRAPOLE'` convergeerde de stap na het bezwijken
  niet); in eigen code geen `PREDICTION`/`MATRICE='ELASTIQUE'` bij GD-balken;
  3 `ROTATION` alleen op elsets zonder discrete elementen, in een model met schalen als
  `FORMULE` van X, Y, Z per elset en `FORCE_NODALE` op knoopmassa's
  (`_centrifugal_loads`); 4 niet vastgesteld; 5 kabels krijgen geen centrifugaalkracht
  (ERROR; KNOWN_BUGS 19); 6 met `elem_beam` = `POU_D_T_GD` maakt de bridge in andere
  analyses dan niet-lineair statisch met grote verplaatsingen `POU_D_T` (WARNING),
  vraagt hij geen `SIPM_ELNO` en zet hij de centrifugaalkracht als `FORMULE`;
  `imperfection_amplitude` geeft vooraf een ERROR; 7 knik (en een knikvorm als
  imperfectie) met trusses of kabels geeft vooraf een ERROR: modelleer de staven als
  balken ([`Modaal_en_knik.md`](Modaal_en_knik.md)).
- **Status**: opgelost in de bridge (1, 3, 6, 7; 2 en 5 als melding) / eigen invoer (2, eigen
  code) / oorzaak niet vastgesteld (4).

### `CALCUL_42` – optie nog niet geprogrammeerd (meebewegende druk op DKT)

- **Melding** (fout): "Le TYPE_ELEMENT MEDKQU4 devrait calculer l'option :
  RIGI_MECA_PRSU_F, mais il ne le fait pas encore".
- **Oorzaak**: druk als meebewegende last (`TYPE_CHARGE='SUIV'`, grote verplaatsingen)
  op DKT/DST-schalen.
- **Gezien**: afgeleid uit de code (`bridge_to_aster`, docstring bij de meebewegende
  druk; testrun).
- **Oplossing**: in de bridge: meebewegende druk alleen op volumevlakken en
  `COQUE_3D`; op DKT/DST blijft de druk vast (WARNING). Kies *Lineaire schalen* =
  `COQUE_3D` voor meebewegende druk op schalen.
- **Status**: opgelost in de bridge (als melding).

### `CALCUL_20` – materiaal ontbreekt

- **Melding** (fout): "Le matériau est nécessaire sur la maille ...".
- **Oorzaak**: een elset in het model zonder vertaald materiaal.
- **Gezien**: afgeleid uit de code (`bridge_to_aster`, controle op materialen; QA-run).
- **Oplossing**: in de bridge: ERROR vóór Code-Aster met de naam van de elset; geef het
  onderdeel in Mecway een materiaal.
- **Ook gezien**: `CALC_G` (breukmechanica) op de randcellen van de lippen
  (`MECA_FACE8`, optie `CALC_K_G`): de bridge geeft het materiaal per elset, niet aan
  de randcellen. Opgelost in de bridge: `CALC_G` rekent op een eigen resultaat met een
  materiaal op alle cellen (`bridge_fracture._material_block`,
  [Breukmechanica.md](Breukmechanica.md) §2.1).
- **Status**: opgelost in de bridge (als melding).

### `CALCULEL2_92` – meer dan één verdeelde last op een balk

- **Melding** (fout): "votre chargement contient plus d'une charge répartie, le calcul
  n'est pas possible pour les modèles de poutre".
- **Oorzaak**: meer dan één last met een verdeelde balklast in een berekening (ook in
  `CALC_CHAMP` `SIPM_ELNO`): line pressure, gravity en centrifugaalkracht op balken.
- **Gezien**: `FORCE_POUTRE` en `PESANTEUR` in aparte lasten; twee line pressures op
  overlappende selecties.
- **Oplossing**: in de bridge (`_prepare_beam_loads`): de balken worden verdeeld in
  disjuncte groepen met per groep de som van de lasten, in één last; met een
  tijdsafhankelijke line pressure alles in één `AFFE_CHAR_MECA_F`. Nog niet: lokale
  en globale line pressure op dezelfde balk en centrifugaal met een tijdsafhankelijke
  line pressure (ERROR vooraf); gravity met een tijdshistorie samen met line pressures
  op balken (WARNING). Zie KNOWN_BUGS 20.
- **Status**: opgelost in de bridge, op de genoemde gevallen na.

### `MECANONLINE_3` (met alarm `CALCULEL_54`) – element niet voor niet-lineair

- **Melding** (fout): "les éléments ne sont pas programmés pour cela"; vooraf alarm
  `CALCULEL_54` over `PCOMPOR` van `FULL_MECA`.
- **Oorzaak**: schalen als `DST` in `STAT_NON_LINE`/`DYNA_NON_LINE`.
- **Gezien**: vlakke quad4-plaat, niet-lineair met DST.
- **Oplossing**: in de bridge: DST alleen bij `MECA_STATIQUE`, anders DKT met een
  WARNING (commit 9ba9857).
- **Status**: opgelost in de bridge.

### `COMPOR5_22` – GROT_GDEP niet op volume-elementen

- **Melding** (fout): "COMPORTEMENT affecte le modèle de déformation GROT_GDEP sur une
  modélisation MECA_HEXA8. Ce n'est pas possible."
- **Oorzaak**: `DEFORMATION='GROT_GDEP'` op volume-elementen.
- **Gezien**: een buigmodel (contact) en een `#ASTER-OPTIE`-test.
- **Oplossing**: in de bridge: `deformation` wordt per elementtype vertaald
  (`_deformation_for`): volumes `GREEN_LAGRANGE` (elastisch) of `GDEF_LOG`
  (plastisch), DKT/DST `GREEN_LAGRANGE`, `COQUE_3D` `GROT_GDEP`, balken `PETIT`
  ([Instellingen §2.3](Instellingen_contact_en_nietlineair.md#23-kinematica-deformation)).
  Zie je de melding toch, dan komt hij uit eigen `#ASTER`-code.
- **Status**: opgelost in de bridge.

### `COMPOR1_44`, `COMPOR1_99` – rekmaat past niet bij wet of element

- **Melding** (fout): `COMPOR1_44`: het type rek past niet bij de wet;
  `COMPOR1_99`: structuurelementen kunnen niet met `DEFORMATION='GDEF_LOG'`.
- **Oorzaak**: `COMPOR1_44`: `GREEN_LAGRANGE` met een Von Mises-wet (`VMIS_*`);
  `COMPOR1_99`: `GDEF_LOG` op schalen of balken.
- **Gezien**: gemengd model bij het uitzoeken van grote verplaatsingen (commit 1de4c87).
- **Oplossing**: in de bridge: zie `COMPOR5_22`.
- **Status**: opgelost in de bridge.

### `COMPOR1_47` – COQUE_3D met GROT_GDEP: rotaties onder 2π

- **Melding** (alarm): met `COQUE_3D` en `GROT_GDEP` moeten de rotaties kleiner blijven
  dan 2π.
- **Oorzaak**: grote verplaatsingen met `COQUE_3D`-schalen.
- **Gezien**: runs met grote verplaatsingen (commentaar bij `_deformation_for`).
- **Oplossing**: geen nodig zolang een schaal niet meer dan een volle slag draait.
- **Status**: onschuldig.

### `MODELE1_7` – 3D_SI alleen voor parallellepipeda

- **Melding** (alarm): "l'élément HEXA8 en 3D_SI ne fonctionne correctement que sur les
  parallélépipèdes".
- **Oorzaak**: *Hex8-volume-elementen* = `3D_SI`.
- **Gezien**: proeven met 3D_SI.
- **Oplossing**: de bridge gebruikt `3D_SI` alleen als een elset uitsluitend hex8 heeft.
  Liever `LINE_QUAD` (KNOWN_BUGS 1).
- **Status**: onschuldig (bewuste keuze); let op de spanningen.

### `PLATE1_40` – schaal niet te oriënteren

- **Melding** (fout): "L'élément de plaque ne peut pas être orienté".
- **Oorzaak**: een schaal in een vlak x = constant (normaal langs X).
- **Gezien**: plaat gekoppeld aan een blok, gedraaid naar x = constant.
- **Oplossing**: in de bridge: `_shell_ref_vector` zet dan `VECTEUR` in
  `AFFE_CARA_ELEM COQUE` (commit 354c7e9). Heeft één selectie normalen langs alle assen
  (gesloten doos), dan een WARNING: splits de selectie in Mecway per vlak.
- **Status**: opgelost in de bridge (behalve het doos-geval).

### `MODELISA4_50` / `MODELISA4_51` – maille zonder element

- **Melding**: `4_50` (alarm): "la maille N n'est pas affectée par un élément fini";
  `4_51` (fout): geen van de mailles heeft een element.
- **Oorzaak**: `#ASTER`-code (`LIAISON_ELEM` 3D_POU) noemt een vlakselectie van
  volume-elementen die niet in het model zat.
- **Gezien**: balk aan een volumevlak met `LIAISON_ELEM`.
- **Oplossing**: in de bridge: een volumevlak dat als `<<naam>>` in `#ASTER`-regels
  voorkomt, komt als randelement in het model (`bridge_mesh`, `skin_groups`).
- **Status**: opgelost in de bridge.

### `MODELISA6_96` / `PROJECTION4_55` – LIAISON_MAIL

- **Melding**: `MODELISA6_96` (fout): mailles in `LIAISON_MAIL` horen niet bij het
  model; `PROJECTION4_55` (fout): de master-mailles moeten dezelfde dimensie hebben als
  het model.
- **Oorzaak**: verlijmd contact of een kracht op schaalranden, vertaald met vlakken die
  niet in het model zaten, of met randvlakken als master.
- **Gezien**: tests C15_bondedtie en S4_edge.
- **Oplossing**: in de bridge (`bridge_mesh._bonded`): master = de volume-elementen naast
  het vlak, slave = de knopen van het vlak (`GROUP_NO_ESCL`).
- **Status**: opgelost in de bridge.

### `CHARGES2_31` – vrijheidsgraad bestaat niet op de knoop

- **Melding** (fout): een randvoorwaarde op vrijheidsgraad X van knoop N, terwijl die
  knoop X niet heeft.
- **Oorzaak**: de middenknoop van QUAD9/TRIA7 (`COQUE_3D`) heeft alleen rotaties;
  `LIAISON_OBLIQUE` of `LIAISON_MAIL` legt daar `DX` op.
- **Gezien**: afgeleid uit de code (`bridge_to_aster`, QA-model M15b_bonded_coque en
  frictionless op `COQUE_3D`).
- **Oplossing**: in de bridge: de middenknopen gaan in `SANS_GROUP_NO`; schalen die
  master zijn van verlijmd contact blijven DKT (WARNING; KNOWN_BUGS 21).
- **Status**: opgelost in de bridge.

### `ELEMENTS4_92` – druk als functie op een schaal

- **Melding** (fout): een drukbelasting als functie (`PRES_REP`) op een schaalelement;
  Code-Aster vraagt daar `FORCE_COQUE`.
- **Oorzaak**: druk met een tijdshistorie op schalen.
- **Gezien**: afgeleid uit de code (`bridge_to_aster`, `bridge_mesh`; testrun).
- **Oplossing**: in de bridge: `PRES = 1` met de historie als `FONC_MULT`, of
  `FORCE_COQUE PRES` met een functie.
- **Status**: opgelost in de bridge.

### `CHARGES2_89` – geen maille van het juiste type

- **Melding** (alarm): geen van de mailles in het sleutelwoord heeft het juiste type;
  alle worden genegeerd.
- **Oorzaak**: druk (`PRES_REP`) op een elementselectie van volume-elementen.
- **Gezien**: afgeleid uit de code (`bridge_mesh`, gemeld in een review; NIET met een
  run nagelopen).
- **Oplossing**: in de bridge: druk op een elementselectie alleen voor schalen; anders
  ERROR en niet vertaald. Kies in Mecway een vlakselectie.
- **Status**: opgelost in de bridge (als melding).

### `POUTRE0_61` – plasticiteit op een klassieke balk

- **Melding** (fout): de wet (bijv. `VMIS_ISOT_LINE`) bestaat niet voor klassieke
  balken; gebruik multivezelbalken.
- **Oorzaak**: een plastisch materiaal op balkelementen.
- **Gezien**: afgeleid uit de code (`bridge_to_aster`, testrun).
- **Oplossing**: in de bridge: de balk rekent elastisch (WARNING en `skipped_loads`).
- **Status**: beperking (gemeld).

### `DISCRETS_26` – discreet element zonder massa

- **Melding** (alarm): de massamatrix van een discreet element zonder `M_*`; de massa
  is nul.
- **Oorzaak**: veren en POI1-knopen (RBE-master) zonder massa in `AFFE_CARA_ELEM`.
- **Gezien**: een gemengd testmodel (RBE, veer).
- **Oplossing**: in de bridge: elk discreet element krijgt massa 0 (`M_T_D_N` enz.).
- **Status**: opgelost in de bridge.

### `DISCRETS_28` – discreet element zonder demping

- **Melding** (alarm): als `DISCRETS_26`, voor de dempingsmatrix.
- **Oorzaak**: een discreet element zonder `A_*` in een dynamische berekening met
  demping.
- **Gezien**: demper-test D18_damper (uitdemping 0,7303, theorie 0,7301) en F4_model.
- **Oplossing**: geen nodig zolang die elementen geen demping horen te hebben.
- **Status**: onschuldig.

### `ELEMENTS2_63` – THER_NL ontbreekt in het materiaal (thermisch)

- **Melding** (fout): "On ne trouve pas le comportement THER_NL dans le matériau fourni."
- **Oorzaak**: `THER_NON_LINE` met een materiaal als `THER`.
- **Gezien**: thermische proeven.
- **Oplossing**: in de bridge: bij `THER_NON_LINE` schrijft `bridge_thermal.py` `THER_NL`.
- **Status**: opgelost in de bridge.

### `MODELE1_3`, `MODELE1_14`, `MODELE1_53`, `CHARGES2_4` – thermische schalen als PLAN

- **Melding** (alarmen): `MODELE1_3`: een vlakke modelisatie vraagt een mesh in z = 0;
  `MODELE1_14` / `CHARGES2_4`: 2D- en 3D-elementen gemengd; `MODELE1_53`:
  2D-elementen in een 3D-mesh.
- **Oorzaak**: thermisch rekent de bridge vlakke schalen als `PLAN` met een diktefactor
  (KNOWN_BUGS 15, [`Thermisch.md`](Thermisch.md)).
- **Gezien**: alle thermische modellen met schalen.
- **Oplossing**: geen, zolang de schalen in evenwijdige vlakken liggen (de bridge
  controleert dat en draait het mesh zo nodig met `MODI_MAILLAGE ROTATION`). De
  resultaten kloppen (tegen Mecway ≤ 3e-12 K). `MODELE1_53` komt ook als de
  z-coördinaten niet exact gelijk zijn (~1e-18): ook dan onschuldig.
- **Status**: onschuldig (bewuste keuze).

### `MODELE1_63`, `MODELE1_64` – geen stijfheid

- **Melding** (alarmen): `MODELE1_63`: een randelement grenst aan geen element met
  stijfheid; `MODELE1_64`: het model heeft geen elementen met stijfheid.
- **Oorzaak**: proefmodel met alleen randelementen.
- **Gezien**: thermische proefjob, niet in een bridge-run.
- **Oplossing**: controleer `AFFE_MODELE`.
- **Status**: niet in de bridge gezien.

---

## 3. Randvoorwaarden en singuliere matrix

Een singuliere matrix betekent bijna altijd: een deel kan vrij bewegen (mechanisme), of
een vrijheidsgraad is dubbel vastgelegd. De code hangt af van *MUMPS NPREC*
(`solver_nprec`; `SOLVEUR NPREC`, EDF R&D, 2021d): met 8 (standaard in alle analyses) komen `FACTOR_10/11/42`. Bij -1 (controle uit)
geeft een bijna-mechanisme `FACTOR_57`; een volledig los deel geeft ook dan `FACTOR_42`
(MUMPS kan niet factoriseren). In
`STAT_NON_LINE`/`DYNA_NON_LINE` staat de pivot-tekst (knoop en component) zonder
kader in de convergentietabel en stopt de run met `MECANONLINE9_4` (gezien
06-10-2026). Code-Aster's eigen advies staat in de
catalogus bij `FACTOR_10/11` (EDF R&D, 2026a): een fysieke vrijheidsgraad wijst op een
slecht vastgehouden starre beweging, een Lagrange-vrijheidsgraad op een overbodige
voorwaarde, vaak door contact (`SANS_GROUP_NO`).

### `FACTOR_10` / `FACTOR_11` – (bijna) singuliere matrix

- **Melding** (fout): "la matrice est singulière ou presque singulière": pivot (bijna)
  nul; boven het kader staan knoop en component.
- **Oorzaak**: te weinig opleggingen; een pinned support (houdt in de bridge alleen de
  gemiddelde verplaatsing vast); een deel dat alleen via contact op zijn plaats blijft;
  een schaal die langs één lijn knopen aan een volume vastzit (scharnier).
- **Gezien**: `FACTOR_11` in een gemengd testmodel niet-lineair: de plaat
  kan draaien. `FACTOR_10` is niet in een bewaarde run gezien; volgens de catalogus
  dezelfde oorzaken, met het aantal verloren decimalen.
- **Oplossing**: in Mecway: genoeg opleggingen; een plaat over een vlak aan het volume
  verbinden in plaats van langs één lijn. Met `#ASTER`-regels: `LIAISON_MAIL
  TYPE_RACCORD='COQUE_MASSIF'` (doorgerekend, voorbeeld 2 in
  [`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md)) of `LIAISON_ELEM
  OPTION='COQ_3D'` (catalogus `affe_char_meca.py`, EDF R&D, 2026b; met `GROUP_MA_COQUE`,
  `GROUP_MA_MASSIF` en `CARA_ELEM`; niet doorgerekend).
- **Status**: model.

### `FACTOR_42` – MUMPS: matrix singulier

- **Melding** (fout): "La matrice est non factorisable. Elle est détectée comme étant
  singulière".
- **Oorzaak**: (a) dubbele voorwaarde: een knoop van een fixed support zit ook in een
  frictionless of schuine oplegging; (b) een `#ASTER`-last zonder `#ASTER-EXCIT`: het
  deel dat ermee verbonden zou zijn, hangt los.
- **Gezien**: (a) schuine plaat met frictionless naast een inklemming (test PL);
  (b) voorbeeld 1 van `ASTER_regels_voorbeelden.md` zonder `#ASTER-EXCIT`, opnieuw
  doorgerekend op 06-10-2026: *Statisch* (`solver_nprec` -1) `FACTOR_42` met
  `DIAGNOSTIC JOB : OK`; *Niet-lineair statisch* `MECANONLINE9_4`. Op 07-10-2026 gaf
  een ander model (losse buisbalk aan een hex20-blok) in *Statisch* `FACTOR_57`
  (foutgrens 9,4, nog met `solver_nprec` -1). Sinds 08-10-2026 staat `solver_nprec` ook bij
  *Statisch* op 8: voorbeeld 1 (model A) geeft dan `FACTOR_11`. Welke code komt, hangt van
  het model en NPREC af; de uitleg en de oplossing zijn gelijk.
- **Oplossing**: in de bridge: knopen van fixed supports worden uitgesloten bij
  `LIAISON_OBLIQUE`/`FACE_IMPO` en bij een opgelegde verplaatsing, rotatie of snelheid
  (`SANS_GROUP_*`, commit ef86c7b; zie `ASSEMBLA_26`). Andere overlappen meldt de bridge
  vooraf als WARNING met de selectienamen (`_report_constraint_overlaps`, KNOWN_BUGS
  8): haal de overlap in Mecway weg. Bij (b): `#ASTER-EXCIT naam` toevoegen.
- **Status**: deels opgelost in de bridge / model / eigen invoer.

### `FACTOR_57` – MUMPS: oplossing te onnauwkeurig

- **Melding** (fout): "La solution du système linéaire est trop imprécise: Erreur
  calculée ... Erreur acceptable 1e-06 (RESI_RELA)". MUMPS schat de relatieve fout van
  de oplossing (conditiegetal × 'backward error') en stopt als die boven `RESI_RELA`
  ligt (U4.50.01 §3.5.3). De grootte van de *Erreur calculée* zegt wat er aan de hand is.
- **Oorzaak**: (a) **fout van orde 1 of meer**: een mechanisme, als `FACTOR_10/11`, maar
  bij `solver_nprec` = -1 zoekt MUMPS geen singulariteit en blijkt de fout pas uit de
  onnauwkeurige oplossing (gemeten: 13 en 64). Met `solver_nprec` 8 geeft een mechanisme
  `FACTOR_11`. (b) **kleine fout (tot ca. 1e-4)**: geen mechanisme maar een slecht
  geconditioneerde matrix, typisch een slank volumemodel op buiging.
- **Gezien**: (a) een gemengd testmodel na de juiste vertaling van pinned support: de
  plaat kan vrij draaien. Mecway rekent het door, maar toont ±499 N "reactie" op knopen
  zonder oplegging. Ook test T1 (plaat langs één lijn aan het blok). (b) Code-Aster
  17.4, `solver_nprec` 8: hex20-uitkragende balk 1000 × 40 × 10 mm (100 × 4 × 2
  elementen, 100 N dwars) fout 7,0e-6 in *Statisch*, in de statische stap van *Knik* en
  van *Modaal* met voorspanning (conditiegetal 1,8e10); dezelfde balk axiaal gedrukt
  (knik) 1,1e-6; het hex20-L-raamwerk van BU-37 (knik) 5,0e-5. Met de verhoogde
  instelling rekenen ze door, met dezelfde resultaten als met `RESI_RELA=-1` en
  analytisch / Mecway binnen 0,4% ([Verificatie §7](Verificatie.md)).
- **Oplossing**: de bridge leest de *Erreur calculée* uit `study.mess`. (a) Boven 1e-3:
  de melding over een (bijna) singuliere matrix; in Mecway de plaat extra vastzetten of
  over een vlak verbinden (zie `FACTOR_10`). Tijdelijk `solver_nprec` = 8 geeft een
  `FACTOR_10/11` met knoop en component. (b) Onder 1e-3: de melding noemt de pagina en
  de waarde (de macht van tien die minstens 10 × de fout is) voor *Nauwkeurigheid
  oplosser (RESI_RELA)* (`lin_solver_resi`). Die instelling bestaat bij *Statisch* (de
  hele berekening), *Modaal* (de statische stap voor de voorspanning, ook bij
  cyclische symmetrie), *Knik* (de statische stap) en *Niet-lineair statisch* (de
  statische stap van de imperfectie). Verhoog hem niet blind tot boven 1e-3: dan zou
  een mechanisme met `solver_nprec` = -1 niet meer gemeld worden.
- **Status**: model (a) / instelling (b).

### `ASSEMBLA_26` – vrijheidsgraad meer keer geblokkeerd

- **Melding** (fout): "le noeud: N composante: DX est bloqué plusieurs fois".
- **Oorzaak**: een knoop met een fixed support zit ook in een tijdsafhankelijke
  opgelegde verplaatsing, rotatie of snelheid (`DDL_IMPO` in `AFFE_CHAR_MECA_F`). Een
  constante waarde gaf geen melding, maar won stil van de inklemming.
- **Gezien**: code-review (commit 6ce5cba; commentaar in `_build_charges`).
- **Oplossing**: in de bridge: `DDL_IMPO` krijgt `SANS_GROUP_NO`/`SANS_GROUP_MA` met de
  fixed-selecties: de inklemming wint. (Mecway brengt meerdere voorwaarden op een knoop
  terug tot een minimale set; Mecway, 2026: §9.6.) Twee andere voorwaarden op dezelfde
  knoop lost de bridge niet op (KNOWN_BUGS 8).
- **Status**: opgelost in de bridge (fixed) / model (overige overlap).

### `FACTOR_13` – probleem bij factoriseren

- **Melding** (fout): "Problème lors de la factorisation de la matrice."
- **Oorzaak**: niet vastgesteld; gezien in een thermische proefjob met `SOUR_NL` op een
  `PLAN`-schaal (route die de bridge niet gebruikt).
- **Gezien**: thermische proefjob.
- **Oplossing**: niet vastgesteld.
- **Status**: oorzaak niet vastgesteld.

### `MECANONLINE9_4` – matrix niet inverteerbaar (niet-lineair)

- **Melding** (fout, `<SolverError>`): "Arrêt pour cause de matrice non inversible";
  de opgeslagen stappen blijven bewaard. Erboven per poging de pivot-melding.
- **Oorzaak**:
  1. een contact-slaveknoop die ook volledig vastligt (pivot op `LAGS_C`);
     een buigmodel: knoop 15405 in slave `G03ContactProfielToMalUP` en in
     `G09FixYXZ`;
  2. Lagrange-contact (*Contactmethode* = STANDARD) bij lijncontact tussen
     kwadratische volumes: pivot op `LAGS_C` van een hoekknoop;
  3. een `#ASTER`-last zonder `#ASTER-EXCIT` (zie `FACTOR_42`);
  4. tension only (kabel) zonder drukstijfheid;
  5. formaten-testmodellen F2/F4: oorzaak niet vastgesteld;
  6. een deel dat alleen door contact op zijn plaats blijft (geen eigen oplegging,
     verlijmd contact, koppeling of veer; ook de kant van een bout achter een
     pre-tension section met een kracht): pivot op een fysieke vrijheidsgraad
     (DX/DY/DZ) van dat deel in de eerste stap.
- **Gezien**: 1 een buigmodel (contact); 2 verificatie NL-03a (twee balken, tips op
  elkaar) en Samples/AssemblyWithContact (KNOWN_BUGS 43); 3 opnieuw doorgerekend op
  06-10-2026; 4 test B17; 5 F2_model/F4_model; 6 Samples/BoltedJoint (pivot op DZ van een
  knoop van plaat B, 28-10-2026; de bridge waarschuwt vooraf: WARNING "wordt alleen door
  contact op zijn plaats gehouden").
- **Oplossing**: 1 in de bridge: slave-knopen in een fixed support worden per zone
  uitgesloten met `SANS_GROUP_NO` (`_exclude_fixed_slaves`, commit 7daa249; INFO in de
  log), zoals de catalogus bij `FACTOR_10/11` aanraadt; een andere voorwaarde op
  slave-knopen: in Mecway uit de slave-selectie halen of
  `#ASTER-ZONE SANS_GROUP_NO='<<selectie>>'` (geldt voor elke zone en vervangt de
  automatische). 2 *Contactmethode* = PENALISATION met Mecway's *normal stiffness*
  (NL-03b: tip −0,01%, contactkracht −0,07%). 3 `#ASTER-EXCIT` toevoegen. 4 in de
  bridge: `EC_SUR_E` = 1e-4 (standaard van de catalogus `defi_materiau.py`). 5 niet
  vastgesteld. 6 in Mecway: een zwakke *Elastic support* op een groot vlak van dat deel,
  een echte oplegging, of verlijmd contact
  ([Instellingen §3.11](Instellingen_contact_en_nietlineair.md#311-delen-die-alleen-door-contact-vastzitten)).
- **Status**: opgelost in de bridge (1 bij fixed, 4) / model (1 overig, 2, 6) / eigen
  invoer (3) / oorzaak niet vastgesteld (5).

### `CHARGES7_1` – verlijmen: relatie is een tautologie

- **Melding** (alarm): de relatie voor een slaveknoop is overbodig, want het
  master-element bevat die knoop zelf.
- **Oorzaak**: verlijmd contact (`LIAISON_MAIL`) waar slave- en mastervlak knopen delen.
- **Gezien**: bonded-test C15; reacties klopten.
- **Oplossing**: geen nodig.
- **Status**: onschuldig.

### `MECANONLINE2_97` – temperatuurrek in de begintoestand

- **Melding** (alarm): de temperatuur geeft in de begintoestand al een anelastische rek.
- **Oorzaak**: een constant temperatuurveld vanaf t = 0 dat afwijkt van de
  referentietemperatuur.
- **Gezien**: thermische-rektest C14_thermal (verplaatsing 6,0e-5 m, verwacht 6e-5).
- **Oplossing**: in de bridge (`_build_temperature_field`): in `STAT_NON_LINE` en
  `DYNA_NON_LINE` is het veld een `EVOL_THER` met de referentie op het eerste tijdstip;
  daarna de temperatuur vanaf de eerste stap, oplopend of volgens de tijdstabel
  ([Thermisch.md](Thermisch.md) §3.1). In `DYNA_NON_LINE` gaf het constante veld geen
  thermische spanning (verificatie DY-70).
- **Status**: opgelost in de bridge.

### `MECANONLINE_78` – massamatrix bijna singulier

- **Melding** (alarm): de massamatrix voor de beginversnelling is bijna singulier; de
  beginversnelling kan op enkele knopen te groot zijn.
- **Oorzaak**: vrijheidsgraden zonder massa: een materiaal zonder dichtheid, of
  rotaties zonder rotatietraagheid.
- **Gezien**: D12_rotinertia (maximale hoek 0,012611, gelijk aan de theorie), F4_model,
  en voorbeeld 1 van `ASTER_regels_voorbeelden.md` in *Dynamisch (impliciet)* (balk
  zonder dichtheid; 06-10-2026). De bridge waarschuwt vooraf bij een elset zonder
  dichtheid.
- **Oplossing**: geef het materiaal in Mecway een dichtheid; verder geen nodig als de
  resultaten kloppen.
- **Status**: onschuldig (in de geziene gevallen) / model (geen dichtheid).

---

## 4. Contact

Achtergrond en instellingen:
[Instellingen §3](Instellingen_contact_en_nietlineair.md#3-contact); `DEFI_CONTACT`:
EDF R&D (2021b) en de catalogus `defi_contact.py`. Zie ook `MECANONLINE9_4` (pivot op
`LAGS_C`).

### `CONTACT2_16` – zones delen slave-knopen

- **Melding** (fout): "Les zones de contact numéro 1 et numéro 2 ont N noeuds communs à
  leurs surfaces esclaves : c'est interdit."
- **Oorzaak**: in Mecway is hetzelfde vlak slave in meer contactparen. Mecway staat dat
  toe, Code-Aster niet.
- **Gezien**: een knipmodel (*Dynamisch (impliciet)*): 48 gedeelde knopen.
- **Wat niet werkte**: `SANS_GROUP_NO` (de controle gaat over de vlakken); master en
  slave wisselen (divergeerde in de eerste stap).
- **Oplossing**: in de bridge: zulke paren worden één zone (unie van masters en slaves,
  grootste wrijvingscoëfficiënt; `_merge_contact_zones`, KNOWN_BUGS 10, commit
  cdc0a74), met een WARNING. Verschillende wrijving per paar: laat de slave-selecties
  niet overlappen.
- **Status**: opgelost in de bridge.

### `APPARIEMENT_1` – geen knoop gekoppeld

- **Melding** (alarm): "Aucun noeud n'est apparié": geen slaveknoop vindt een
  master-element. Code-Aster noemt `CONTACT_INIT='OUI'`, `TOLE_PROJ_EXT` en
  `ALGO_RESO_GEOM='POINT_FIXE'`.
- **Oorzaak**: vermoedelijk lagen de vlakken van een zone (nog) te ver uit elkaar; NIET
  nagelopen.
- **Gezien**: een variant van een knipmodel (dynamisch); de run liep door.
- **Oplossing**: controleer master/slave en de beginspleet
  ([Instellingen §3.2-3.4](Instellingen_contact_en_nietlineair.md#32-master-en-slave));
  extra opties via `#ASTER-ZONE` / `#ASTER-CONTACT` (voorbeelden 5 en 6).
- **Status**: oorzaak niet vastgesteld (geen invloed gezien).

### `MECANONLINE5_15` – energie niet met continu contact

- **Melding** (fout): "Le calcul des énergies n'est pas disponible avec le contact en
  formulation continue ou XFEM."
- **Oorzaak**: `ENERGIE=_F()` in `DYNA_NON_LINE` met `FORMULATION='CONTINUE'`.
- **Gezien**: proef voor de energiebalans.
- **Oplossing**: in de bridge: met contact laat de bridge `ENERGIE` weg, ook als
  *Energiebalans* aan staat.
- **Status**: opgelost in de bridge (beperking van Code-Aster).

---

## 5. Niet-lineaire berekening en dynamica

Stappenplan en instellingen:
[Instellingen §2 en §4](Instellingen_contact_en_nietlineair.md#4-mijn-berekening-convergeert-niet);
`STAT_NON_LINE`: EDF R&D (2021c) en de catalogus `stat_non_line.py`.

### `MECANONLINE9_7` – Newton convergeert niet

- **Melding** (fout, `<ConvergenceError>`): "Arrêt pour cause d'absence de convergence
  avec le nombre d'itérations requis": geen convergentie binnen `ITER_GLOB_MAXI`, ook
  niet na het verkleinen van de stap (`SUBD_PAS` = 4, `SUBD_NIVEAU` = 6). De opgeslagen
  stappen blijven bewaard.
- **Wat de bridge doet**: de job vangt de fout op, schrijft `BRIDGE_ONVOLLEDIG <tijd>`
  en laadt de resultaten tot het laatst bereikte tijdstip; Mecway toont de uitleg
  (`_NEWTON_HINT`).
- **Oorzaak**; lees de convergentietabel in de `.mess` (kolommen `RESI_GLOB_RELA`,
  `RESI_GLOB_MAXI`, contact):
  1. **Relatief residu blijft hangen, absoluut residu is ~0.** Een buigmodel (profiel, rol en mal met contact):
     `RESI_GLOB_RELA` rond 0,1 bij `RESI_GLOB_MAXI` ~1e-11: een opgelegde beweging
     zonder weerstand, dus geen referentiekracht: kies `convergence_criterion` = MAXI.
  2. **Stagnatie net boven het criterium** (bijv. 1,4–2,8e-6 bij 1e-6), vooral bij
     ontlasten van een plastisch volume met `GDEF_LOG`; de absolute rest blijft dan
     steken (NL-01: ~1e-2 N bij 12 kN).
  3. **Doorsnijden of bezwijken.** Een knipmodel (dynamisch, contact) stopt bij t = 0,11 s als het
     profiel doorgesneden is; Code-Aster verwijdert geen elementen.
  4. **Te grote stappen** of veel niet-lineariteit tegelijk (contact, plasticiteit,
     grote vervorming).
  5. **Starre rotatie met een GD-balk** (`POU_D_T_GD`; zie §6).
  6. **Geen belasting**: alle lasten overgeslagen of nul (residu 0 in elke iteratie,
     `RESI_GLOB_RELA` = -1 in de tabel).
  7. **Knik of grenspunt bereikt** (draagkracht): met een imperfectie of plasticiteit
     heeft de last een maximum; een last als tijdstabel kan daar niet verder. Met
     *Stabiliteit per stap (CRIT_STAB)* gaat het criterium naar 0
     ([`Modaal_en_knik.md`](Modaal_en_knik.md) §5).
- **Gezien**: 1 een buigmodel (contact); 2 verificatie NL-01 met de Code-Aster-standaard
  1e-6 (stop op t = 2,92 s); 3 een knipmodel;
  4 algemeen; 5 proeven voor een buigmodel; 6 een klein hex8-testmodel (kracht op
  vlakken niet vertaald, opgelost in commit 8e86271) en een testmodel met een
  onderdrukte last (06-10-2026). Ook bij een tension-only kabel (test B17, oorzaak niet
  vastgesteld). 7 verificatie NK-04 (plastische kolom met imperfectie, stop op
  0,49 Pcr, verwacht).
- **Oplossing** (pagina van de analyse, of per model met `#ASTER-OPTIE`):
  1. *Convergentiecriterium* = MAXI (`convergence_criterion`; grens
     *Convergentie RESI_GLOB_MAXI [N]*, standaard 1e-3 N). De bridge schrijft dan
     `CONVERGENCE=_F(RESI_GLOB_MAXI=...)` (nagelopen in de `.comm`). Het effect is met de
     hand in de `.comm` van een buigmodel vastgesteld (stap 0 → 0,5 s
     convergeerde); de instelling zelf is niet op dat model opnieuw doorgerekend;
  2. *Convergentie RESI_GLOB_RELA* (`convergence_resi_rela`) op de standaard 1e-5
     laten (de Code-Aster-standaard 1e-6 stagneerde in NL-01; met 1e-5 rekent NL-01 exact
     door tot het eind). Wil je 1e-6 houden: *Convergentiecriterium* = RELA_OF_MAXI
     (`RESI_GLOB_RELA` en `RESI_GLOB_MAXI` met `VERIF='AU_MOINS_UN'`) met
     *Convergentie RESI_GLOB_MAXI* boven de absolute rest waarop het residu stagneert
     (kolom `RESI_GLOB_MAXI` in de `.mess`): NL-01b (1e-6 en 0,05 N) rekent exact door,
     met 1e-3 N niet (`TestFiles/Verificatie/resultaten/resultaten.md`;
     [Instellingen §2.2](Instellingen_contact_en_nietlineair.md#22-newton-en-convergentie));
  3. een bezwijkgrens ([`Bezwijken.md`](Bezwijken.md)); anders zijn de resultaten tot
     het bezwijken geladen;
  4. *Substappen per tijdsinterval* / *Rekenstappen per Mecway-tijdstap* en
     *Max. Newton-iteraties* verhogen, en de niet-lineariteiten één voor één aanzetten
     ([Instellingen §4.2](Instellingen_contact_en_nietlineair.md#42-stappenplan)); bij
     contact *Contactmethode* = PENALISATION;
  5. niet via de bridge;
  6. controleer in `<model>_<run-id>_bridge_log.txt` de overgeslagen belastingen;
  7. geen fout: de last op het laatste tijdstip is de draagkracht. Verder rekenen
     voorbij het grenspunt kan alleen met een opgelegde verplaatsing in plaats van een
     kracht (de boogslengtemethode `PILOTAGE` zit niet in de bridge).
- **Status**: model / beperking (per geval).

### `SUBDIVISE_3` – stap kan niet verkleind worden

- **Melding** (fout): de tijdstap kan niet gedeeld worden, want de functie staat niet
  aan; gebruik `DEFI_LIST_INST`.
- **Oorzaak**: `STAT_NON_LINE` met alleen een `DEFI_LIST_REEL`.
- **Gezien**: afgeleid uit de catalogustekst; niet als run-fout bewaard.
- **Oplossing**: in de bridge: `DEFI_LIST_INST` met
  `ECHEC=_F(EVENEMENT='ERREUR', ACTION='DECOUPE', SUBD_PAS=4, SUBD_NIVEAU=6)`
  (commit 57ffead; nagelopen in een `.comm` van 06-10-2026).
- **Status**: opgelost in de bridge.

### `DISCRETISATION_87` – tijdlijst niet strikt stijgend

- **Melding** (fout): "La liste d'instants n'est pas strictement croissante."
- **Oorzaak**: twee tijden die bijna samenvallen (bijv. 1e-20 s uit elkaar), uit
  verschillende lasthistories.
- **Gezien**: afgeleid uit de code (`_merge_times`; testrun).
- **Oplossing**: in de bridge: bijna-dubbele tijden (verschil ≤ 1e-9 × eindtijd) worden
  samengevoegd.
- **Status**: opgelost in de bridge.

### `MECANONLINE5_80` – beginsnelheid op ander model

- **Melding** (alarm): het veld in `ETAT_INIT` hoort bij een ander model dan de
  berekening; Code-Aster vult aan met nullen.
- **Oorzaak**: niet nagelopen (vermoedelijk de extra vrijheidsgraden van contact).
- **Gezien**: alle dynamische runs met een beginsnelheid (een knipmodel en
  varianten); de runs liepen door. Of de beginsnelheid overal goed is toegepast, is niet
  apart gecontroleerd.
- **Oplossing**: niet vastgesteld; controleer bij twijfel de snelheid op het eerste
  tijdstip in Mecway.
- **Status**: oorzaak niet vastgesteld.

### `DYNAMIQUE_4` – stabiliteitsgrens niet te berekenen (expliciet)

- **Melding** (fout bij `STOP_CFL='OUI'`): de stabiliteitsvoorwaarde kon voor geen
  enkel element worden berekend.
- **Oorzaak**: een expliciet model zonder elementen met materiaal (alleen veren,
  dempers en knoopmassa's).
- **Gezien**: afgeleid uit de code (`bridge_to_aster`, kritieke tijdstap; testrun met
  veer, demper en knoopmassa).
- **Oplossing**: in de bridge: dan `STOP_CFL='NON'` met een eigen schatting van de
  stabiele stap van de discrete elementen (`_discrete_time_step`; INFO in de log).
  Zie [Instellingen §2.1](Instellingen_contact_en_nietlineair.md#21-tijdstappen).
- **Status**: opgelost in de bridge.

### `MECANONLINE5_1` – expliciet alleen PREDICTION TANGENTE

- **Melding** (fout): bij een expliciet schema is alleen `PREDICTION='TANGENTE'`
  mogelijk.
- **Oorzaak**: de bezwijklus gebruikte na een bezwijkmoment `PREDICTION='ELASTIQUE'`.
- **Gezien**: afgeleid uit de code (`bridge_failure`).
- **Oplossing**: in de bridge: expliciet blijft `TANGENTE`.
- **Status**: opgelost in de bridge.

### `MATERIAL1_5` – helling van de hardingscurve past niet bij E

- **Melding** (fout, `<F>`): de helling tot het eerste punt van `TRACTION` wijkt meer dan
  1 % af van `ELAS` E (`DEFI_MATERIAU`, controle `check_young_consistency` in
  `defi_materiau_ops.py`).
- **Oorzaak in een Mecway-model**: *Young's modulus* op het tabblad *Elastic* past niet
  bij het eerste stuk van de hardingscurve, of een curve als plastische rek begint niet
  met plastische rek 0.
- **Gezien**: GitHub issue #2 (curve met een andere helling dan E).
- **Oplossing**: in de bridge: bij een curve in totale rek is E de helling van het eerste
  stuk, zoals Mecway (WARNING met beide waarden); wat dan nog meer dan 1 % afwijkt, stopt
  vóór Code-Aster met een ERROR met beide waarden
  ([`Instellingen_contact_en_nietlineair.md`](Instellingen_contact_en_nietlineair.md)
  §2.4). In het model: laat de curve met (0, 0) beginnen en de vloeigrens op de
  elastische lijn liggen, of (plastische rek) met plastische rek 0 bij de vloeigrens.
- **Status**: opgelost in de bridge (curve in totale rek) / model (overige).

### `MECANONLINE9_3` – integratie van de materiaalwet mislukt

- **Melding** (fout, `<IntegrationError>`): de integratie van de materiaalwet is
  mislukt; de opgeslagen stappen blijven bewaard.
- **Oorzaak**: zeer grote vervorming in slappe (bezweken) elementen; of alleen
  `SIEF_ELGA` op nul zetten zonder de interne variabelen.
- **Gezien**: bezwijkproeven (`bridge_failure`, [`Bezwijken.md`](Bezwijken.md) §6).
- **Oplossing**: in de bridge: bij bezwijken ook de interne variabelen op nul. In het
  model: kleinere stappen, of *Stijfheid bezweken element* groter.
- **Status**: opgelost in de bridge (oorzaak 2) / model (oorzaak 1).

### `MECANONLINE4_50` – beginspanning bij een meerstapsschema

- **Melding** (alarm): een beginspanning (`SIGM` in `ETAT_INIT`) bij HHT/NEWMARK wordt
  afgeraden: de beginversnelling wordt zonder die spanning berekend.
- **Oorzaak**: de bezwijklus in *Dynamisch (impliciet)* herstart na een bezwijkmoment met
  de spanning van de vorige stap.
- **Gezien**: bezwijkproeven (`bridge_failure`).
- **Oplossing**: in de bridge: ook de versnelling gaat mee in `ETAT_INIT`. Of dat de
  herberekening voorkomt, is NIET geverifieerd; controleer het verloop op
  plausibiliteit ([`Bezwijken.md`](Bezwijken.md) §6).
- **Status**: onschuldig (verwacht; NIET geverifieerd).

---

## 6. Grote rotaties

Met *COMPORTEMENT DEFORMATION* voor grote verplaatsingen kiest de bridge per
elementtype de vorm (`COMPOR5_22`, `COMPOR1_44/47/99`); balken `POU_D_E`/`POU_D_T`,
opgelegde rotaties (`DDL_IMPO` DR*) en starre koppelingen blijven kleine rotaties
(KNOWN_BUGS 11); balken met grote rotaties: `elem_beam` = `POU_D_T_GD` ([Instellingen §2.9](Instellingen_contact_en_nietlineair.md#29-balken-met-grote-rotaties-elem_beam--pou_d_t_gd)). De bridge
waarschuwt bij een opgelegde rotatie boven ~6° (`_warn_large_rotations`). Een star deel
over een grote hoek draaien gaat robuust met een opgelegde verplaatsing als `FORMULE`
(voorbeeld 9 van [`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md),
opnieuw doorgerekend op 06-10-2026).

### `CHARGES_36` – LIAISON_SOLIDE als volgende last met rotaties

- **Melding** (fout): `LIAISON_SOLIDE`-relaties worden met `TYPE_CHARGE='SUIV'`
  niet-lineair; dat kan niet als een knoop DRX, DRY en DRZ heeft.
- **Oorzaak**: een RBE2 bij grote rotaties met een balkknoop als master.
- **Gezien**: proef met een aangepaste `.comm` voor een buigmodel.
- **Oplossing**: de starre beweging opleggen als `DDL_IMPO` met een `FORMULE` op de
  slaveknopen (voorbeeld 9), of een masterknoop zonder rotatievrijheidsgraden. Alleen met
  eigen code.
- **Status**: beperking.

Verder bij grote rotaties: `COMPOR5_22`, `COMPOR1_44`, `COMPOR1_47`, `COMPOR1_99`,
`DVP_2` (`POU_D_T_GD` met `ELAS`), `CALCUL_37` (`POU_D_T_GD` met
`PREDICTION='ELASTIQUE'`), `MECANONLINE9_7` geval 5. Met `POU_D_T_GD` vangt de bridge
vooraf af: `ALGELINE4_41` (`crit_stab`: de tangentmatrix is niet symmetrisch; ERROR),
`CALCUL_37` (bezwijken van elementen; ERROR) en `DVP_1` (`EFGE_ELNO` op dit element,
`te0185.F90`; de bridge vraagt `SIEF_ELNO`).

---

## 7. Nabewerking

Fouten na de solve (`CALC_CHAMP`, `POST_CHAMP`, `POST_RELEVE_T`, `IMPR_RESU`, export):
de oplossing is berekend, maar de commando's erna worden overgeslagen.

### `CALCULEL_58` – component ontbreekt

- **Melding** (fout): "Il manque la composante : SIXX sur la maille : 8".
- **Oorzaak**: `CALC_CHAMP` op het resultaat van `POST_CHAMP EXTR_COQUE` zonder
  `GROUP_MA`.
- **Gezien**: een gemengd testmodel (volume, schaal, balk).
- **Oplossing**: in de bridge: `GROUP_MA` met de schaalgroepen (commit 631cc36).
- **Status**: opgelost in de bridge.

### `POSTRELE_40` – knoop niet verbonden met maille

- **Melding** (fout): "Le noeud numéro 1 n'est pas connecté à la maille de nom X".
- **Oorzaak**: `POST_RELEVE_T` met een balkgroep en `GROUP_NO='all_nodes'`.
- **Gezien**: een gemengd testmodel (balkspanning).
- **Oplossing**: in de bridge: een knopengroep uit dezelfde mailles (commit 65f8c7a).
- **Status**: opgelost in de bridge.

### `POSTRELE_70` – SIGM_NOEU in het lokale assenstelsel

- **Melding** (alarm): met structuurelementen heeft `SIGM_NOEU` alleen betekenis in het
  lokale assenstelsel; `REPERE` wordt genegeerd.
- **Oorzaak**: gemengde modellen. In de bridge bestaat `SIGM_NOEU` alleen op de
  3D-elementen en staat daar in het globale assenstelsel (`_build_postreleve_block`).
- **Gezien**: elk gemengd model.
- **Oplossing**: geen nodig.
- **Status**: onschuldig.

### `JEVEUX_10` – naam bestaat al

- **Melding** (fout): "Le nom demandé existe déjà dans la base &&SSCGNO.LITMP2".
- **Oorzaak**: `DEFI_GROUP CREA_GROUP_NO` met meerdere groepen in één `_F`.
- **Gezien**: model met 6 balkgroepen.
- **Oplossing**: in de bridge: één `_F` per groep (commit 18f308a).
- **Status**: opgelost in de bridge.

### `UTILITAI_3` – velden met sub-punten naar knopen

- **Melding** (alarm): een ELNO-veld met sub-punten (lagen van een schaal) kan geen
  NOEU-veld worden.
- **Oorzaak**: `SIGM_NOEU` op het hele model, ook op schalen.
- **Gezien**: een gemengd testmodel.
- **Oplossing**: in de bridge: `SIGM_NOEU`/`SIEQ_NOEU` alleen op 3D-groepen; schalen via
  `POST_CHAMP EXTR_COQUE` per laag.
- **Status**: opgelost in de bridge.

### `PREPOST2_57` – sub-punten in IMPR_RESU GMSH

- **Melding** (fout): "nombre de sous-points différent de 1".
- **Oorzaak**: `IMPR_RESU FORMAT='GMSH'` zonder `NOM_CHAM`.
- **Gezien**: vroege versie, gemengd model.
- **Oplossing**: in de bridge: geen GMSH-export meer (commit a27ddba); met
  *MED-bestand voor ParaView* alleen knoopvelden die in `res` bestaan.
- **Status**: opgelost in de bridge.

### `CALCULEL2_15` – EXTR_COQUE zonder sub-punten

- **Melding** (fout): extractie gevraagd voor velden zonder sub-punten.
- **Oorzaak**: `SIGM_ELNO` eerst alleen op de volumes; de latere `CALC_CHAMP` op de
  schalen vulde het veld niet aan.
- **Gezien**: gemengd model ME (route `liml`).
- **Oplossing**: in de bridge: `SIGM_ELNO` één keer over volumes en schalen samen
  (commit ed7971c).
- **Status**: opgelost in de bridge.

### `CALCCHAMP_1` – veld bestaat al

- **Melding** (alarm): het veld (bijv. `SIGM_ELNO`) staat al in het resultaat; er wordt
  niets opnieuw berekend.
- **Oorzaak**: `CALC_CHAMP` vraagt een veld dat de bridge al maakte, bijv. eigen
  `#ASTER-POST`-code met `SIGM_ELNO`/`SIEQ_ELNO`.
- **Gezien**: gemengd model ME; de vroegere vorm van voorbeeld 8 (06-10-2026).
- **Oplossing**: geen nodig; laat de dubbele `CALC_CHAMP` weg.
- **Status**: onschuldig.

### `ELEMENTS4_4`, `ELEMENTS4_64` – SIPM_ELNO niet mogelijk

- **Melding**: `ELEMENTS4_4`: `SIPM_ELNO` kan niet bij `SECTION='GENERALE'`;
  `ELEMENTS4_64` (fout): voor deze optie moet het materiaal alleen `ELAS` hebben.
- **Oorzaak**: balkspanning gevraagd voor een I/T/C/L- of algemeen profiel, of voor een
  balk met een plastisch materiaal.
- **Gezien**: afgeleid uit de code (`bridge_to_aster`, posigr.F90; testrun voor
  `ELEMENTS4_64`).
- **Oplossing**: in de bridge: `SIPM_ELNO` alleen voor `RECTANGLE` en `CERCLE`
  (`_SIPM_SECTIONS`) en alleen bij een elastisch materiaal; anders een INFO-melding.
- **Status**: opgelost in de bridge.

### `CALCULEL_33` / `RESULT1_39` – ander materiaal in CALC_CHAMP (thermisch)

- **Melding**: `CALCULEL_33` (fout): `CALC_CHAMP` met `reuse` en een andere
  `CHAM_MATER` mag niet; `RESULT1_39` (alarm): er wordt gerekend met het opgegeven
  materiaal.
- **Oorzaak**: thermische schalen rekenen met een geschaalde λ; de flux moet met de
  echte λ.
- **Gezien**: thermisch model ConductionConvectionRadiation; ook bij
  `#ASTER-METALLURGIE` met een eigen `trc=` (`CALC_META` met een eigen `CHAM_MATER`,
  verificatie MT-08; [Lassen.md](Lassen.md) §10.6).
- **Oplossing**: in de bridge: de flux in een nieuw resultaat (`res_flux`); het alarm
  `RESULT1_39` is dan bedoeld (`bridge_thermal.py`, `bridge_metallurgy.py`).
- **Status**: opgelost in de bridge (`CALCULEL_33`) / onschuldig (`RESULT1_39`).

### `ALGORITH2_12`, `CALCUL_5` – interne thermische nabewerking

- **Melding** (fout): `ALGORITH2_12`: `MODI_REPERE` mist een component;
  `CALCUL_5`: het veld heeft niet de grootheid die de optie verwacht.
- **Oorzaak**: `FLUZ` op `PLAN`-knopen bij het terugdraaien van de flux; een bronveld
  als `TEMP_R` in plaats van `SOUR_R`.
- **Gezien**: afgeleid uit de code (`bridge_thermal`).
- **Oplossing**: in de bridge opgelost (`FLUZ` alleen met volume-elementen; bron als
  `NOEU_SOUR_R`).
- **Status**: opgelost in de bridge.

### `RUPTURE0_94` – SIEF_ELGA ontbreekt voor CALC_G

- **Melding** (fout): "Accès impossible au champ SIEF_ELGA pour le numéro d'ordre : 1
  ... vous calculez l'option 'G'".
- **Oorzaak**: `CALC_G` `OPTION='G'` op een resultaat zonder `SIEF_ELGA` (bijv. uit
  `CREA_RESU`).
- **Gezien**: bij de bouw van de breukmechanica (stap S6a).
- **Oplossing**: in de bridge: `CALC_CHAMP CONTRAINTE=('SIEF_ELGA',)` vóór `CALC_G`
  ([Breukmechanica.md](Breukmechanica.md) §2.1); met eigen `#ASTER-POST`-code: idem, of
  `OPTION='G_EPSI'`.
- **Status**: opgelost in de bridge.

### `XFEM_63`, `QUALITY1_1`, `MODELE1_63` – XFEM-alarmen

- **Melding** (alarm): `XFEM_63` "Éléments XFEM quadratiques ... On a effectué un
  ajustement géométrique de la fissure" (aantal ajustementen); `QUALITY1_1` "La
  fonctionnalité XFEM n'est pas qualifiée pour les études de sûreté"; `MODELE1_63` "La
  maille ... porte un élément fini de bord, mais elle ne borde aucun élément ayant une
  rigidité".
- **Oorzaak**: `XFEM_63`: de levelset snijdt ribben meer dan eens of ligt vlak bij
  knopen (kwadratische elementen, scheurvlak door knopen) en wordt licht verschoven;
  `QUALITY1_1`: altijd bij XFEM; `MODELE1_63`: het hulpmodel op het mesh van
  `POST_MAIL_XFEM` met `TOUT='OUI'` kreeg ook de frontcellen (SEG2).
- **Gezien**: bij de bouw van XFEM (stap S6b; BR-08, BR-09).
- **Oplossing**: `XFEM_63` en `QUALITY1_1`: onschuldig (K binnen 0,2 %, BR-08/BR-09);
  `MODELE1_63`: in de bridge: het hulpmodel krijgt alleen de volume-elsets
  ([Breukmechanica.md](Breukmechanica.md) §7.3).
- **Status**: informatie (`XFEM_63`, `QUALITY1_1`); opgelost in de bridge (`MODELE1_63`).

---

## 8. Syntax en `#ASTER`-regels

Voorbeelden en valkuilen: [`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md).
Zie ook `MODELISA7_75` (onbekende selectie), `FACTOR_42`/`MECANONLINE9_4` (last zonder
`#ASTER-EXCIT`) en `CALCCHAMP_1`.

### `SUPERVIS_4` – syntaxfout in een commando

- **Melding** (fout): "Erreur de syntaxe dans <COMMANDO>" met de reden, bijv. "Keyword
  INCREMENT is mandatory". De job stopt (`<F>_ABNORMAL_ABORT`).
- **Oorzaak**: een sleutelwoord dat ontbreekt, niet bestaat of niet op die plek mag.
  Gezien: `GROUP_MA=` in `POST_RELEVE_T ACTION` (eigen `#ASTER-POST`-code);
  `THER_LINEAIRE` zonder `INCREMENT`; `AFFE_MATERIAU` zonder `AFFE` in een model met
  alleen discrete elementen.
- **Oplossing**: lees de reden in het kader; vergelijk met de catalogus
  (`Cata/Commands/<commando>.py`).
- **Status**: eigen invoer / opgelost in de bridge (per geval).

### Python-fout in de `.comm` (zonder code)

- **Melding**: geen meldingskader; in `<model>_<run-id>_console.txt` een traceback of
  `SyntaxError`, bijv. `SyntaxError: keyword argument repeated: FROTTEMENT`. De `.mess`
  eindigt zonder `<FIN>`, vaak met `DIAGNOSTIC JOB : OK`.
- **Oorzaak**: een tikfout in `#ASTER`-regels, of een sleutelwoord dat de bridge al
  schrijft: `FROTTEMENT` via `#ASTER-CONTACT`, of `ALGO_CONT` via `#ASTER-ZONE` terwijl
  *Contactmethode* = PENALISATION.
- **Gezien**: beide gevallen opnieuw doorgerekend op 06-10-2026; de bridge meldt
  "Python-fout in `<model>_<run-id>.comm`: SyntaxError: keyword argument repeated: ..."
  met de foutregel.
- **Oplossing**: herhaal niets wat de bridge al schrijft
  ([`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md) §4).
- **Status**: eigen invoer.

---

## 9. Systeem, oplosser en vervolgfouten

Geheugen- of tijdsgrensmeldingen zijn bij het testen niet voorgekomen. De grenzen staan
in de `.export` (*Tijdslimiet run_aster [s]*, *Geheugenlimiet run_aster [MB]*).

### `JEVEUX_26` – object bestaat niet

- **Melding** (fout): "Objet inexistant dans les bases ouvertes: ... .ORDR".
- **Oorzaak**: vervolgfout: een eerder commando faalde (bijv. `COMPOR5_22`,
  `MECANONLINE_3`, `MECANONLINE5_15`, `CALCULEL2_15`, `CALCUL_37`), het resultaat bestaat
  niet.
- **Gezien**: steeds samen met een van die fouten.
- **Oplossing**: los de eerste fout in de `.mess` op.
- **Status**: vervolgfout.

### `CATAMESS_6` – stop na een `<E>`-melding

- **Melding** (fout): "Fin à la suite de message(s) <E>".
- **Oorzaak**: na een `<E>`-melding stopt Code-Aster bij het volgende commando; een
  `try/except` in de `.comm` kan dat niet opvangen.
- **Gezien**: modecontrole van `CALC_MODES` (verificatie, `Verificatie.md`).
- **Oplossing**: in de bridge: `VERI_MODE STOP_ERREUR='NON'`: de controles worden
  alarmen (§10).
- **Status**: opgelost in de bridge.

### `FERMETUR_10` – PETSc niet geïnstalleerd

- **Melding** (fout): de oplosser PETSc zit niet in deze versie.
- **Oorzaak**: `METHODE='PETSC'`; de Windows-versie is sequentieel.
- **Gezien**: testrun (commentaar in `bridge_to_aster`).
- **Oplossing**: in de bridge: alleen MUMPS en GCPC (*Lineaire oplosser*).
- **Status**: beperking (niet aangeboden).

### `ALGELINE4_3` – GCPC convergeert niet

- **Melding** (fout): de iteratieve oplosser GCPC haalt het criterium niet binnen het
  toegestane aantal iteraties.
- **Oorzaak**: *Lineaire oplosser* = GCPC bij een slecht geconditioneerd model (bijv.
  slanke balken van volume-elementen).
- **Gezien**: NIET in een bewaarde run; genoemd in
  [Instellingen §2.6](Instellingen_contact_en_nietlineair.md#26-lineaire-solver-solver_nprec-lin_solver-lin_solver_resi).
- **Oplossing**: *Lineaire oplosser* = MUMPS.
- **Status**: model / instelling.

### `CATAMESS_41` – alarm niet meer getoond

- **Melding** (alarm): het alarm X is 5 keer gegeven en wordt niet meer getoond.
- **Status**: informatie; kijk naar alarm X.

### `CATAMESS_89` – lijst van alarmen

- **Melding** (`<I>`): aan het eind van de `.mess` alle alarmen met hun aantal.
- **Status**: informatie.

### Zonder code: crash, afgebroken job of loggingfout

- `Windows fatal exception: access violation` (`<F>_ABNORMAL_ABORT`, geen kader): gezien
  bij `DEFI_GROUP reuse=mesh` ná de solve; in de bridge opgelost door alle groepen vóór
  `AFFE_MODELE` te maken. De traceback staat alleen in het Code-Aster-venster.
- `Exception: Trying to close the database after an uncaught exception...`: een fout
  in een commando; de melding erboven is de oorzaak. Gezien na `FACTOR_42`
  (06-10-2026).
- `--- Logging error ---` met een traceback in de console-uitvoer: een logregel kon niet
  naar een console (job zonder venster); de job rekent door. De bridge negeert deze
  traceback (`bridge_convergence.python_errors`).
- Geen `<FIN>` in de `.mess`: de `.comm` is niet tot het eind uitgevoerd; zie
  [§8](#python-fout-in-de-comm-zonder-code).

---

## 10. Modaal en knik

`CALC_MODES` in *Modaal* en *Knik* (`bridge_to_aster._calc_modes_block`; achtergrond in
[`Modaal_en_knik.md`](Modaal_en_knik.md)). De modecontrole (`VERI_MODE`) staat op
`STOP_ERREUR='NON'`, zodat een mislukte controle een alarm geeft in plaats van een stop.

### `ALGELINE3_81` – zoekfrequentie valt samen met een eigenwaarde

- **Melding** (fout): de shift voor de dynamische matrix valt samen met een eigenwaarde;
  ondanks verschuiven blijft de matrix singulier.
- **Oorzaak**: een mechanisme of starre beweging in een model met opleggingen (balk
  alleen scharnierend vast, los onderdeel). Ook: een verbinding via `#ASTER`-code
  (`LIAISON_ELEM`, `LIAISON_MAIL`, ...) waarvan de last niet in `#ASTER-EXCIT` staat.
  Met `#ASTER-EXCIT` zet de bridge de last ook in `CHARGE` van `ASSEMBLAGE`, zodat de
  verbinding in de matrices van *Modaal* en *Knik* meetelt (zie
  [`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md) §2). Ook: een dubbele
  voorwaarde, twee opleggingen op dezelfde knopen in lineair afhankelijke richtingen (de
  gedualiseerde voorwaarden maken de matrix singulier, welke shift ook); de bridge meldt
  zo'n overlap vooraf met `WARNING: Voorwaarden ... delen ... knoop/knopen`.
- **Gezien**: balk die alleen scharnierend vastzit (KNOWN_BUGS 48); GitHub issue #9
  (ronde plaat met frictionless op de randen en displacement X, Y, Z = 0 op dezelfde
  knopen; die overlap reduceert de bridge nu zelf, MO-09); een samenstel met verlijmd
  contact en zonder oplegging (nu de vrij-vrij-route, MO-10); voorbeeld 1 van
  `ASTER_regels_voorbeelden.md` in *Modaal* en *Knik* toen `#ASTER-EXCIT` nog niet in
  de matrices kwam (06-10-2026: de balk hing los). Met de last in de matrices rekent
  voorbeeld 1 door (*Modaal* f1 = f2 = 841,8 Hz met het toenmalige testmodel; met model
  A uit `TestFiles/Voorbeelden/` 2855,4 Hz).
- **Oplossing**: leg het model beter vast (verbindingen uit `#ASTER`-code via
  `#ASTER-EXCIT`), of kies *Zoekfrequentie [Hz]* negatief (bijv. -10 × de verwachte
  eerste frequentie); de starre modes komen dan met ~0 Hz mee. Nagelopen op
  06-10-2026 (losse balk): met -1000 Hz zes modes van ~1e-3 Hz en daarna 841,8 Hz.
  Dat helpt alleen als het losse deel massa heeft (dichtheid of puntmassa): zelfde
  model zonder dichtheid gaf opnieuw `ALGELINE3_81`. De uitleg in de log zegt dit ook.
- **Akoestiek** (holtemodes, [`Akoestiek.md`](Akoestiek.md)): een volume met harde
  wanden zonder drukknoop heeft een mode met constante druk (0 Hz); met `PLUS_PETITE`
  gaf dat `ALGELINE3_81` (gezien, 07-10-2026). De bridge zoekt dan zelf rond een kleine
  negatieve frequentie. Blijft de melding (een los deel van het volume zonder
  drukknoop terwijl er elders wel drukknopen zijn): kies een negatieve zoekfrequentie
  op de pagina *Akoestiek (holtemodes)*.
- **Status**: model.

### `ALGELINE3_82` – bandgrens is een eigenwaarde

- **Melding** (alarm): de ondergrens van het zoekinterval (de Sturm-band) valt (bijna)
  op een eigenwaarde; de Sturm-telling kan fout zijn.
- **Oorzaak**: meestal een starre mode bij ~0 Hz, bij een negatieve zoekfrequentie.
- **Gezien**: run met *Zoekfrequentie* -1000 Hz (06-10-2026) en een vrij-vrij model met
  een negatieve zoekfrequentie; de Sturm-controle telde daarna wel het juiste aantal
  modes. Ook bij akoestische holtemodes met harde wanden (de 0-Hz-mode van de
  constante druk; verificatie AK-01 en AK-05, 07-10-2026): frequenties exact.
- **Wat de bridge doet**: WARNING in de log met uitleg (`_ALARM_HINTS`).
- **Oplossing**: meestal geen nodig. Controleer het aantal starre modes (zes per vrij
  deel), of verschuif de zoekfrequentie iets.
- **Status**: onschuldig (in de geziene gevallen).

### `ALGELINE5_49`, `ALGELINE3_78` – te weinig modes gevonden

- **Melding**: `ALGELINE5_49` (alarm): minder modes berekend dan gevraagd;
  `ALGELINE3_78` (fout): geen eigenwaarde met de gevraagde nauwkeurigheid.
- **Oorzaak**: een zoekfrequentie ver van de modes.
- **Gezien**: hex20-balk met een verschuiving ver boven de eerste mode (KNOWN_BUGS 48,
  `Verificatie.md`).
- **Oplossing**: zoekfrequentie dichter bij de verwachte frequenties (0 = de laagste), of
  minder modes.
- **Status**: model / instelling.

### `ALGELINE5_23`, `ALGELINE2_74`, `ALGELINE5_15` – modecontrole

- **Melding** (alarmen, door `STOP_ERREUR='NON'`): `ALGELINE5_23`: de Sturm-controle telt
  meer eigenwaarden dan berekend; `ALGELINE2_74`: de modecontrole is niet gehaald;
  `ALGELINE5_15`: de foutnorm van een mode is groter dan de grens.
- **Oorzaak**: `5_23` meestal een meervoudige mode (symmetrie) op de grens van het
  aantal modes, anders een gemiste mode; `5_15` een grof of slecht geconditioneerd
  model.
- **Gezien**: BucklingBeam met vierkante doorsnede (`5_23`; `Verificatie.md`).
- **Oplossing**: `5_23`: vraag een of twee modes meer en vergelijk; `5_15`: fijner mesh
  of *Controle modes (VERI_MODE SEUIL)* groter (bijv. 1e-4). De bridge logt `5_23` en
  `2_74` als WARNING met uitleg.
- **Status**: model / onschuldig (per geval).

### `ALGELINE4_77`, `UTILITAI3_5` – normering en modeparameters

- **Melding** (fout): `ALGELINE4_77`: de normering is niet geïmplementeerd;
  `UTILITAI3_5`: de parameter bestaat niet.
- **Oorzaak**: `NORM_MODE='RIGI_GENE'` bij `MODE_FLAMB`; een parameter als
  `MASS_EFFE_UN_DRX` opvragen.
- **Gezien**: tijdens de bouw van modaal en knik (`Verificatie.md`).
- **Oplossing**: in de bridge: knikvormen worden zelf genormeerd
  (phi^T K phi = 1, `aster_results_export.py`); alleen bestaande parameters worden
  gelezen.
- **Status**: opgelost in de bridge.

### `ALGORITH16_52`, `ALGORITH16_58`, `ALGORITH14_94`, `ALGORITH14_95` – cyclische symmetrie

- **Melding** (fout, `MODE_ITER_CYCL`): `ALGORITH16_52` "axe de symétrie cyclique
  différent de Oz" (een paar knopen ligt niet als rotatie om de Z-as);
  `ALGORITH16_58` "arrêt sur problème répétitivité cyclique" (met diagnose
  "INVERSION INTERFACE DROITE/GAUCHE" of geen diagnose); `ALGORITH14_94`/`_95`
  "erreur de répétitivité cyclique" / "il manque un ddl sur un noeud axe".
- **Oorzaak**: snijvlakken die niet als herhaling om de Z-as passen; DROITE en GAUCHE
  verwisseld; ruis rond 0 in de axiale coördinaat (Code-Aster vergelijkt relatief);
  8 segmenten met knopen op de as (`ctetax.F90`: cos 45° − sin 45° = 0).
- **Gezien**: tijdens de bouw van S10g (ringsector, Mecway's Impeller met y = 1,9e-20 /
  6,0e-20 m, plaat met 8 segmenten; `Verificatie.md` CY).
- **Oplossing**: in de bridge: de paren worden zelf gezocht en op volgorde gezet,
  GAUCHE is de kant op +360°/N, coördinaten < 1e-12 × de modelgrootte worden 0, bij een
  X/Y-as een exacte verwisseling van de coördinaten; 8 segmenten met knopen op de as
  geeft een ERROR. In Mecway: een klein gat op de as. Komt `ALGORITH16_52` toch: meld
  het model.
- **Status**: opgelost in de bridge (ruis, richting) / beperking (8 segmenten met
  knopen op de as, KNOWN_BUGS 61).

---

## 11. Foutschatter

`CALC_ERREUR` (residu-schatter `ERME`) in *Statisch* met de instelling
`error_estimator` (`bridge_to_aster._error_estimator_block`; achtergrond in
[`Foutschatter.md`](Foutschatter.md)). De bridge bouwt de schatter zo dat geen van
deze meldingen optreedt (eigen model, eigen last, eigen resultaat); ze verschijnen
alleen bij een eigen `CALC_ERREUR` in `#ASTER-POST`-code. Alle hieronder gezien met
Code-Aster 17.4 bij de bouw van de foutschatter (balk hex8 20x2x2, ook met puntlast,
twee drukken en balken in het model).

### `INDICATEUR_2`, `CALCUL_29` – spanningen niet op het hele model

- **Melding** (alarm, dan fout): "Le champ de contraintes n'a pas été calculé sur tout
  le modèle. On ne peut pas calculer l'option ERME_ELEM"; daarna `<EXCEPTION>
  CALCUL_29` (parameter `PERREUR` ontbreekt voor `ERME_ELNO`).
- **Oorzaak**: `SIGM_ELNO` alleen op een deel van het model (`GROUP_MA`), terwijl het
  model ook randelementen (drukvlakken) of andere elementen bevat. Een tweede
  `CALC_CHAMP` op het hele model vult het veld niet aan (alarm `CALCCHAMP_1`).
- **Oplossing**: in de bridge: `SIGM_ELNO` zonder `GROUP_MA` op een eigen model met
  alleen de volume-elementen en hun randvlakken.
- **Status**: opgelost in de bridge.

### `INDICATEUR_6`, `INDICATEUR_7`, `INDICATEUR_8` – lasten die de schatter niet kan

- **Melding**: `INDICATEUR_6` (alarm) "ne sait pas traiter les charges du type de
  <last>" bij `FORCE_NODALE`; `INDICATEUR_7` (alarm) "Le choix PRESS apparaît au moins
  dans 2 charges" bij twee lasten met `PRES_REP`; daarna `<EXCEPTION> INDICATEUR_8`
  ("Problème sur les charges").
- **Oorzaak**: de schatter kent per soort last maar één last en geen puntlasten. De
  bridge maakt elke belasting een eigen `AFFE_CHAR_MECA`.
- **Oplossing**: in de bridge: een eigen last `load_err` met alle lasten die de
  schatter kent samen (`PRES_REP`, `FORCE_FACE`, `PESANTEUR`, `ROTATION`), via `EXCIT`
  van `CALC_ERREUR`; puntlasten vallen weg (INFO).
- **Status**: opgelost in de bridge.

### `CALCULEL_39`, `RESULT1_40`, `RESULT1_65` – andere lasten dan in het resultaat

- **Melding**: `<EXCEPTION> CALCULEL_39` "Le chargement (mot clé: EXCIT) fourni par
  l'utilisateur est différent de celui présent dans la structure de données Résultat.
  Dans ce cas, le reuse est interdit"; zonder `reuse` de alarmen `RESULT1_65` ("Vous
  avez fourni 1 charges alors qu'il n'y a 2 ...") en `RESULT1_40` ("On poursuit les
  calculs avec le chargement fourni par l'utilisateur").
- **Oorzaak**: `CALC_ERREUR` met een `EXCIT` die afwijkt van de lasten van de
  oplossing. Zonder `reuse` komt `ERME_ELEM` in het nieuwe resultaat, maar zoeken
  `ERME_ELNO`/`ERME_NOEU` hun bronveld in het oude (`UTILITAI8_13`, `CALCUL_29`,
  `CALCUL_17`).
- **Oplossing**: in de bridge: een eigen resultaat (`CREA_RESU` met de verplaatsingen),
  daarop `SIGM_ELNO` en `CALC_ERREUR` met `reuse` en `EXCIT`: geen alarm.
- **Status**: opgelost in de bridge.

### `CALCUL_37` (`INIT_MAIL_VOIS`) – balk in het model van de schatter

- **Melding** (fout): "Le TYPE_ELEMENT MECA_POU_D_E ne sait pas encore calculer
  l'option: INIT_MAIL_VOIS".
- **Oorzaak**: `CALC_ERREUR` op een model met balken (de schatter zoekt de buren van
  elk element); `CALC_ERREUR` kent geen `GROUP_MA`.
- **Oplossing**: in de bridge: het model van de schatter heeft alleen de
  volume-elementen en hun randvlakken.
- **Status**: opgelost in de bridge.

---

## Codes op alfabet

| Code | Thema | Status |
|---|---|---|
| `ALGELINE2_74` | [10](#algeline5_23-algeline2_74-algeline5_15--modecontrole) | model / onschuldig (per geval) |
| `ALGELINE3_78` | [10](#algeline5_49-algeline3_78--te-weinig-modes-gevonden) | model / instelling |
| `ALGELINE3_81` | [10](#algeline3_81--zoekfrequentie-valt-samen-met-een-eigenwaarde) | model |
| `ALGELINE3_82` | [10](#algeline3_82--bandgrens-is-een-eigenwaarde) | onschuldig (in de geziene gevallen) |
| `ALGELINE4_3` | [9](#algeline4_3--gcpc-convergeert-niet) | model / instelling |
| `ALGELINE4_77` | [10](#algeline4_77-utilitai3_5--normering-en-modeparameters) | opgelost in de bridge |
| `ALGELINE5_15` | [10](#algeline5_23-algeline2_74-algeline5_15--modecontrole) | model / onschuldig (per geval) |
| `ALGELINE5_23` | [10](#algeline5_23-algeline2_74-algeline5_15--modecontrole) | model / onschuldig (per geval) |
| `ALGELINE5_49` | [10](#algeline5_49-algeline3_78--te-weinig-modes-gevonden) | model / instelling |
| `ALGORITH14_95` | [10](#algorith16_52-algorith16_58-algorith14_94-algorith14_95--cyclische-symmetrie) | beperking (8 segmenten met knopen op de as) |
| `ALGORITH16_52` | [10](#algorith16_52-algorith16_58-algorith14_94-algorith14_95--cyclische-symmetrie) | opgelost in de bridge |
| `ALGORITH16_58` | [10](#algorith16_52-algorith16_58-algorith14_94-algorith14_95--cyclische-symmetrie) | opgelost in de bridge |
| `ALGORITH2_12` | [7](#algorith2_12-calcul_5--interne-thermische-nabewerking) | opgelost in de bridge |
| `APPARIEMENT_1` | [4](#appariement_1--geen-knoop-gekoppeld) | oorzaak niet vastgesteld (geen invloed gezien) |
| `ASSEMBLA_26` | [3](#assembla_26--vrijheidsgraad-meer-keer-geblokkeerd) | opgelost in de bridge (fixed) / model (overige overlap) |
| `CALCCHAMP_1` | [7](#calcchamp_1--veld-bestaat-al) | onschuldig |
| `CALCULEL2_15` | [7](#calculel2_15--extr_coque-zonder-sub-punten) | opgelost in de bridge |
| `CALCULEL2_92` | [2](#calculel2_92--meer-dan-één-verdeelde-last-op-een-balk) | opgelost in de bridge, op de genoemde gevallen na |
| `CALCULEL_33` | [7](#calculel_33--result1_39--ander-materiaal-in-calc_champ-thermisch) | opgelost in de bridge (`CALCULEL_33`) / onschuldig (`RESULT1_39`) |
| `CALCULEL_39` | [11](#calculel_39-result1_40-result1_65--andere-lasten-dan-in-het-resultaat) | opgelost in de bridge |
| `CALCULEL_54` | [2](#mecanonline_3-met-alarm-calculel_54--element-niet-voor-niet-lineair) | opgelost in de bridge |
| `CALCULEL_58` | [7](#calculel_58--component-ontbreekt) | opgelost in de bridge |
| `CALCUL_20` | [2](#calcul_20--materiaal-ontbreekt) | opgelost in de bridge (als melding) |
| `CALCUL_29` | [11](#indicateur_2-calcul_29--spanningen-niet-op-het-hele-model) | opgelost in de bridge |
| `CALCUL_37` | [2](#calcul_37--element-kan-deze-optie-niet) | opgelost in de bridge (1, 3, 6, 7; 2 en 5 als melding) / eigen invoer (2, eigen code) / oorzaak niet vastgesteld (4) |
| `CALCUL_37` (`INIT_MAIL_VOIS`) | [11](#calcul_37-init_mail_vois--balk-in-het-model-van-de-schatter) | opgelost in de bridge |
| `CALCUL_42` | [2](#calcul_42--optie-nog-niet-geprogrammeerd-meebewegende-druk-op-dkt) | opgelost in de bridge (als melding) |
| `CALCUL_5` | [7](#algorith2_12-calcul_5--interne-thermische-nabewerking) | opgelost in de bridge |
| `CATAMESS_41` | [9](#catamess_41--alarm-niet-meer-getoond) | informatie; kijk naar alarm X |
| `CATAMESS_6` | [9](#catamess_6--stop-na-een-e-melding) | opgelost in de bridge |
| `CATAMESS_89` | [9](#catamess_89--lijst-van-alarmen) | informatie |
| `CHARGES2_31` | [2](#charges2_31--vrijheidsgraad-bestaat-niet-op-de-knoop) | opgelost in de bridge |
| `CHARGES2_4` | [2](#modele1_3-modele1_14-modele1_53-charges2_4--thermische-schalen-als-plan) | onschuldig (bewuste keuze) |
| `CHARGES2_89` | [2](#charges2_89--geen-maille-van-het-juiste-type) | opgelost in de bridge (als melding) |
| `CHARGES7_1` | [3](#charges7_1--verlijmen-relatie-is-een-tautologie) | onschuldig |
| `CHARGES_36` | [6](#charges_36--liaison_solide-als-volgende-last-met-rotaties) | beperking |
| `COMPOR1_44` | [2](#compor1_44-compor1_99--rekmaat-past-niet-bij-wet-of-element) | opgelost in de bridge |
| `COMPOR1_47` | [2](#compor1_47--coque_3d-met-grot_gdep-rotaties-onder-2π) | onschuldig |
| `COMPOR1_99` | [2](#compor1_44-compor1_99--rekmaat-past-niet-bij-wet-of-element) | opgelost in de bridge |
| `COMPOR5_22` | [2](#compor5_22--grot_gdep-niet-op-volume-elementen) | opgelost in de bridge |
| `CONTACT2_16` | [4](#contact2_16--zones-delen-slave-knopen) | opgelost in de bridge |
| `DISCRETISATION_87` | [5](#discretisation_87--tijdlijst-niet-strikt-stijgend) | opgelost in de bridge |
| `DISCRETS_26` | [2](#discrets_26--discreet-element-zonder-massa) | opgelost in de bridge |
| `DISCRETS_28` | [2](#discrets_28--discreet-element-zonder-demping) | onschuldig |
| `DVP_2` | [2](#dvp_2--floating-point-exception) | opgelost in de bridge (a, b); melding met resultaten tot de fout (d) |
| `DYNAMIQUE_4` | [5](#dynamique_4--stabiliteitsgrens-niet-te-berekenen-expliciet) | opgelost in de bridge |
| `ELEMENTS2_63` | [2](#elements2_63--ther_nl-ontbreekt-in-het-materiaal-thermisch) | opgelost in de bridge |
| `ELEMENTS4_4` | [7](#elements4_4-elements4_64--sipm_elno-niet-mogelijk) | opgelost in de bridge |
| `ELEMENTS4_64` | [7](#elements4_4-elements4_64--sipm_elno-niet-mogelijk) | opgelost in de bridge |
| `ELEMENTS4_92` | [2](#elements4_92--druk-als-functie-op-een-schaal) | opgelost in de bridge |
| `FACTOR_10` | [3](#factor_10--factor_11--bijna-singuliere-matrix) | model |
| `FACTOR_11` | [3](#factor_10--factor_11--bijna-singuliere-matrix) | model |
| `FACTOR_13` | [3](#factor_13--probleem-bij-factoriseren) | oorzaak niet vastgesteld |
| `FACTOR_42` | [3](#factor_42--mumps-matrix-singulier) | deels opgelost in de bridge / model / eigen invoer |
| `FACTOR_57` | [3](#factor_57--mumps-oplossing-te-onnauwkeurig) | model |
| `FERMETUR_10` | [9](#fermetur_10--petsc-niet-geïnstalleerd) | beperking (niet aangeboden) |
| `INDICATEUR_2` | [11](#indicateur_2-calcul_29--spanningen-niet-op-het-hele-model) | opgelost in de bridge |
| `INDICATEUR_6` | [11](#indicateur_6-indicateur_7-indicateur_8--lasten-die-de-schatter-niet-kan) | opgelost in de bridge |
| `INDICATEUR_7` | [11](#indicateur_6-indicateur_7-indicateur_8--lasten-die-de-schatter-niet-kan) | opgelost in de bridge |
| `INDICATEUR_8` | [11](#indicateur_6-indicateur_7-indicateur_8--lasten-die-de-schatter-niet-kan) | opgelost in de bridge |
| `JEVEUX_10` | [7](#jeveux_10--naam-bestaat-al) | opgelost in de bridge |
| `JEVEUX_26` | [9](#jeveux_26--object-bestaat-niet) | vervolgfout |
| `MATERIAL1_5` | [5](#material1_5--helling-van-de-hardingscurve-past-niet-bij-e) | opgelost in de bridge (curve in totale rek) / model (overige) |
| `MECANONLINE2_97` | [3](#mecanonline2_97--temperatuurrek-in-de-begintoestand) | opgelost in de bridge |
| `MECANONLINE4_50` | [5](#mecanonline4_50--beginspanning-bij-een-meerstapsschema) | onschuldig (verwacht; NIET geverifieerd) |
| `MECANONLINE5_1` | [5](#mecanonline5_1--expliciet-alleen-prediction-tangente) | opgelost in de bridge |
| `MECANONLINE5_15` | [4](#mecanonline5_15--energie-niet-met-continu-contact) | opgelost in de bridge (beperking van Code-Aster) |
| `MECANONLINE5_80` | [5](#mecanonline5_80--beginsnelheid-op-ander-model) | oorzaak niet vastgesteld |
| `MECANONLINE9_3` | [5](#mecanonline9_3--integratie-van-de-materiaalwet-mislukt) | opgelost in de bridge (oorzaak 2) / model (oorzaak 1) |
| `MECANONLINE9_4` | [3](#mecanonline9_4--matrix-niet-inverteerbaar-niet-lineair) | opgelost in de bridge (1 bij fixed, 4) / model (1 overig, 2) / eigen invoer (3) / oorzaak niet vastgesteld (5) |
| `MECANONLINE9_7` | [5](#mecanonline9_7--newton-convergeert-niet) | model / beperking (per geval) |
| `MECANONLINE_3` | [2](#mecanonline_3-met-alarm-calculel_54--element-niet-voor-niet-lineair) | opgelost in de bridge |
| `MECANONLINE_78` | [3](#mecanonline_78--massamatrix-bijna-singulier) | onschuldig (in de geziene gevallen) / model (geen dichtheid) |
| `MESH1_4` | [1](#mesh1_4--line_quad-op-een-deel-van-het-mesh) | onschuldig |
| `MODELE1_14` | [2](#modele1_3-modele1_14-modele1_53-charges2_4--thermische-schalen-als-plan) | onschuldig (bewuste keuze) |
| `MODELE1_3` | [2](#modele1_3-modele1_14-modele1_53-charges2_4--thermische-schalen-als-plan) | onschuldig (bewuste keuze) |
| `MODELE1_53` | [2](#modele1_3-modele1_14-modele1_53-charges2_4--thermische-schalen-als-plan) | onschuldig (bewuste keuze) |
| `MODELE1_63` | [2](#modele1_63-modele1_64--geen-stijfheid) | niet in de bridge gezien |
| `MODELE1_64` | [2](#modele1_63-modele1_64--geen-stijfheid) | niet in de bridge gezien |
| `MODELE1_7` | [2](#modele1_7--3d_si-alleen-voor-parallellepipeda) | onschuldig (bewuste keuze); let op de spanningen |
| `MODELISA4_50` | [2](#modelisa4_50--modelisa4_51--maille-zonder-element) | opgelost in de bridge |
| `MODELISA4_51` | [2](#modelisa4_50--modelisa4_51--maille-zonder-element) | opgelost in de bridge |
| `MODELISA4_6` | [1](#modelisa4_6--modelisa8_11--weesknopen) | onschuldig (meestal) |
| `MODELISA4_8` | [1](#modelisa4_8--modelisa8_13--dubbele-elementen) | opgelost in de bridge (a) / onschuldig (b) |
| `MODELISA4_80` | [1](#modelisa4_80--groep-leeg) | opgelost in de bridge |
| `MODELISA5_7` | [1](#modelisa5_7--maille-bestaat-niet) | opgelost in de bridge |
| `MODELISA5_8` | [1](#modelisa5_8--maille-dubbel-in-een-groep) | opgelost in de bridge |
| `MODELISA6_10` | [1](#modelisa6_10--maille-niet-in-het-mesh) | opgelost in de bridge |
| `MODELISA6_96` | [2](#modelisa6_96--projection4_55--liaison_mail) | opgelost in de bridge |
| `MODELISA7_66` | [1](#modelisa7_66--item-verwacht-aan-het-begin-van-de-regel) | opgelost in de bridge |
| `MODELISA7_75` | [1](#modelisa7_75-modelisa7_77--groep-bestaat-niet) | eigen invoer (a) / opgelost in de bridge (b) |
| `MODELISA7_77` | [1](#modelisa7_75-modelisa7_77--groep-bestaat-niet) | eigen invoer (a) / opgelost in de bridge (b) |
| `MODELISA7_81` | [1](#modelisa7_81--geen-geldige-naam) | opgelost in de bridge |
| `MODELISA7_82` | [1](#modelisa7_82--interne-fout-bij-lange-groepsnaam) | opgelost in de bridge |
| `MODELISA7_85` | [1](#modelisa7_85--getal-verwacht-in-het-mesh) | opgelost in de bridge |
| `MODELISA8_11` | [1](#modelisa4_6--modelisa8_11--weesknopen) | onschuldig (meestal) |
| `MODELISA8_13` | [1](#modelisa4_8--modelisa8_13--dubbele-elementen) | opgelost in de bridge (a) / onschuldig (b) |
| `MODELISA8_14` | [1](#modelisa8_14--poi1-in-een-ander-element) | onschuldig |
| `MODELISA_1` | [1](#modelisa_1--mesh-niet-te-lezen) | opgelost in de bridge (via de oorzaken hierboven) |
| `MODELISA_78` | [2](#modelisa_78--afschuifcoëfficiënt-ontbreekt-balk) | opgelost in de bridge |
| `PLATE1_40` | [2](#plate1_40--schaal-niet-te-oriënteren) | opgelost in de bridge (behalve het doos-geval) |
| `POSTRELE_40` | [7](#postrele_40--knoop-niet-verbonden-met-maille) | opgelost in de bridge |
| `POSTRELE_70` | [7](#postrele_70--sigm_noeu-in-het-lokale-assenstelsel) | onschuldig |
| `POUTRE0_61` | [2](#poutre0_61--plasticiteit-op-een-klassieke-balk) | beperking (gemeld) |
| `PREPOST2_57` | [7](#prepost2_57--sub-punten-in-impr_resu-gmsh) | opgelost in de bridge |
| `PROJECTION4_55` | [2](#modelisa6_96--projection4_55--liaison_mail) | opgelost in de bridge |
| `RESULT1_39` | [7](#calculel_33--result1_39--ander-materiaal-in-calc_champ-thermisch) | opgelost in de bridge (`CALCULEL_33`) / onschuldig (`RESULT1_39`) |
| `RESULT1_40` | [11](#calculel_39-result1_40-result1_65--andere-lasten-dan-in-het-resultaat) | opgelost in de bridge |
| `RESULT1_65` | [11](#calculel_39-result1_40-result1_65--andere-lasten-dan-in-het-resultaat) | opgelost in de bridge |
| `SOUSTRUC_37` | [1](#soustruc_37-soustruc_38--knoopgroep-bestaat-al--is-leeg) | opgelost in de bridge |
| `SOUSTRUC_38` | [1](#soustruc_37-soustruc_38--knoopgroep-bestaat-al--is-leeg) | opgelost in de bridge |
| `SUBDIVISE_3` | [5](#subdivise_3--stap-kan-niet-verkleind-worden) | opgelost in de bridge |
| `RUPTURE0_94` | [7](#rupture0_94--sief_elga-ontbreekt-voor-calc_g) | opgelost in de bridge |
| `XFEM_63`, `QUALITY1_1`, `MODELE1_63` | [7](#xfem_63-quality1_1-modele1_63--xfem-alarmen) | informatie / opgelost in de bridge |
| `SUPERVIS_4` | [8](#supervis_4--syntaxfout-in-een-commando) | eigen invoer / opgelost in de bridge (per geval) |
| `UTILITAI3_5` | [10](#algeline4_77-utilitai3_5--normering-en-modeparameters) | opgelost in de bridge |
| `UTILITAI5_1` | [1](#utilitai5_1--bestand-bij-een-unit-ontbreekt) | oorzaak in de testopzet, niet in de bridge |
| `UTILITAI_3` | [7](#utilitai_3--velden-met-sub-punten-naar-knopen) | opgelost in de bridge |

---

## Aannames

- De meldingsteksten en hun nummers gelden voor Code-Aster 17.4.0; in een andere versie
  kunnen nummer of tekst verschillen.
- Een melding die "afgeleid uit de code" is, is niet opnieuw met deze versie van de
  bridge gereproduceerd; de bridge vermijdt hem op grond van een eerdere run.
- "Onschuldig" betekent: in de geziene gevallen klopten de resultaten met een
  referentie; het is geen garantie voor elk model.

## Bronnen

- EDF R&D (2026a). *code_aster 17.4.0, berichtencatalogus*. Installatie
  `code_aster/v2025/17.4/lib/aster/code_aster/Messages/<module>.py` (bijv. `factor.py`,
  `mecanonline9.py`, `algeline3.py`).
- EDF R&D (2026b). *code_aster 17.4.0, commandocatalogus*. Installatie
  `code_aster/v2025/17.4/lib/aster/code_aster/Cata/Commands/<commando>.py` (bijv.
  `affe_char_meca.py`, `defi_contact.py`, `defi_materiau.py`, `dyna_non_line.py`).
- EDF R&D (2026c). *code_aster 17.4.0, testcases* ssnl103a. Installatie
  `code_aster/v2025/17.4/share/aster/tests/`.
- EDF R&D (2021a). *Opérateur AFFE_CHAR_MECA*. Code_Aster-documentatie U4.44.01. Lokale
  PDF in `Code_Aster_documentation/important documents/` (aangemaakt 17-12-2021; ouder
  dan 17.4).
- EDF R&D (2021b). *Opérateur DEFI_CONTACT*. Code_Aster-documentatie U4.44.11. Lokale
  PDF (aangemaakt 18-12-2021; ouder dan 17.4).
- EDF R&D (2021c). *Opérateur STAT_NON_LINE*. Code_Aster-documentatie U4.51.03. Lokale
  PDF (aangemaakt 17-12-2021; ouder dan 17.4).
- EDF R&D (2021d). *Mot-clé SOLVEUR*. Code_Aster-documentatie U4.50.01. Lokale PDF
  (aangemaakt 17-12-2021; ouder dan 17.4).
- Mecway (2026). *Mecway Finite Element Analysis – Manual*, versie 33.
  `C:\Program Files\Mecway\manual.pdf`.
- MecwayAsterBridge. `KNOWN_BUGS.md`, `docs/Verificatie.md` en
  `TestFiles/Verificatie/resultaten/resultaten.md` (verificatie-uitkomsten).
