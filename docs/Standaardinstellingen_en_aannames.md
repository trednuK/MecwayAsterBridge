# Standaardinstellingen en aannames

*English version: [Default_settings_and_assumptions.md](en/Default_settings_and_assumptions.md)*

Dit document legt per instelling van de bridge vast welke standaardwaarde hij heeft,
wat hij in Code-Aster doet, waarom deze waarde gekozen is en waarmee dat is
aangetoond. Daarna volgen de aannames die de vertaling Mecway → Code-Aster maakt.
Bron van de waarden: `CONFIG_BRIDGE` in `Scripts/bridge_utils.py` (zoals de repository
hem levert; het startscherm kan ze lokaal veranderen). Bij twijfel is de code leidend.
Code-Aster-versie: 17.4.

Uitleg per onderwerp staat in de andere documenten:
[Handleiding](Handleiding.md) (startscherm),
[Instellingen contact en niet-lineair](Instellingen_contact_en_nietlineair.md),
[Thermisch](Thermisch.md), [Modaal en knik](Modaal_en_knik.md), [Akoestiek](Akoestiek.md),
[Bezwijken](Bezwijken.md) en [Verificatie](Verificatie.md).

---

## 1. Leeswijzer

**Herkomst van een waarde** (kolom *Waarom*):

| Code | Betekenis |
|---|---|
| CA | Standaardwaarde van Code-Aster 17.4: wat Code-Aster doet als het sleutelwoord ontbreekt (catalogus `code_aster/Cata` in de installatie, §6) |
| Gemeten | Gekozen op grond van een run; het bewijs staat erbij |
| Keuze | Ontwerpkeuze van de bridge; de reden staat erbij |
| NIET geverifieerd | Niet met een run of bron onderbouwd |

**Bewijs** (kolom *Bewijs*):

- `LS-02`, `NL-01b`, `DY-03a`, ...: verificatietest uit [Verificatie.md](Verificatie.md),
  uitkomsten in `TestFiles/Verificatie/resultaten/resultaten.md`.
- `R-...`: controlerun bij deze review (oktober 2026): een verificatiecase met één
  andere instelling, met dezelfde keten gerekend (`TestFiles/Verificatie/_run_one.py`
  met een instellingenbestand). De uitkomst staat in de tekst; §5 geeft het overzicht.
- `KNOWN_BUGS n`: punt *n* in [`KNOWN_BUGS.md`](../KNOWN_BUGS.md).

Code-Aster-documenten staan in de tekst als (EDF R&D, U4.51.03 §3); de volledige
gegevens in §6. Andere literatuur als auteur (jaar).

---

## 2. Algemene instellingen

Pagina's *Algemeen* en *Elementen* van het startscherm. Ze gelden voor alle analyses.

| Instelling (label) | Standaard | Wat het doet | Waarom | Aanpassen als | Bewijs |
|---|---|---|---|---|---|
| `language` (Taal / Language) | `en` | taal van startscherm, meldingen, WARNING/ERROR-regels en convergentiescherm | Keuze (projecttaal) | Nederlandstalige gebruiker: `nl` | - |
| `exe_aster` (Code-Aster launcher) | `%LOCALAPPDATA%\code_aster\v2025\17.4\bin\run_aster.bat` | `run_aster.bat` van de installatie | plek waar het Windows-pakket (MSI) van Code-Aster 17.4 installeert; omgevingsvariabelen worden ingevuld | andere installatie | - |
| `work_dir` (Werkmap) | leeg (`WorkDir` naast `Scripts/`) | map voor mesh, `.comm`, `.export`, `.mess`, log en resultaten | werkt zonder instellen; in de repo gitignored | korter pad nodig (259 tekens) | - |
| `work_dir_beside_model` (Werkmap naast het model) | uit | runbestanden in `<model>_aster` naast het open `.liml`-bestand i.p.v. de werkmap (niet opgeslagen model: de werkmap) | Keuze: één vaste werkmap houdt de modelmap schoon | resultaten per project bij het model | - |
| `ncpus` (Aantal CPU-kernen) | 1 | `P ncpus` in de `.export` (threads); altijd `mpi_nbcpu 1` | Keuze: de Windows-build rekent sequentieel (geen MPI, geen PETSc, `FERMETUR_10`) | grote modellen: meer threads; het effect op de rekentijd is NIET gemeten | - |
| `active_analysis` (Actieve analyse) | `auto` | volgt het Mecway-analysetype (S30, S20/SA0 → `lin_static_3d`, L30, D30, D20/DA0 → `dyna_impl_3d` (met *Mode superposition* `dyna_modal_3d`), D31, T30/T31, V30, B30) | Keuze: geen dubbele invoer | expliciete dynamica (`dyna_expl_3d`) kies je altijd zelf | - |
| `configuration` (Configuratie) | `auto` | welke configuratie gerekend wordt en de resultaten krijgt; `auto`: de enige, anders de enige zonder onderdrukte items, anders de eerste (WARNING) | Keuze: de API kan de actieve configuratie niet lezen | lastgevallen als configuraties | LS-20 |
| `mecway_solve_first` (Eerst Mecway-solve) | uit | eerst `mw.solve()`; vergelijkings-CSV per knoop | Keuze: sneller; Mecway's solve kan lang duren | vergelijken met Mecway | - |
| `result_route` (Resultaten naar Mecway) | `liml` | `liml`: alle tijdstappen/modes, ook element-knoopwaarden; `tabel`: knoopwaarden van het laatste tijdstip via `set_variable()` | Keuze: volledig en klein bestand | alleen als de `.liml`-route niet kan | KNOWN_BUGS 7 |
| `convergence_monitor` | aan | apart venster met residuen, oplosser en meldingen | Keuze | - | - |
| `wait_for_aster` (Wachten op Code-Aster) | `auto` | modaal statusvenster met voortgang en *Stoppen...*; einde van de run via de eindmarkering `<model>_<run-id>_done.txt` (exitcode van `run_aster`), anders `DIAGNOSTIC JOB` in de `.mess`; daarna worden de resultaten vanzelf ingeladen | Keuze: geen handwerk, Mecway kan tijdens de run niet gewijzigd worden | `confirm`: zelf OK klikken (het eerdere gedrag), bijv. als het statusvenster niet werkt | `tests/test_bridge_wait.py` |
| `med_export` | uit | ook een `.rmed` voor ParaView/Salome: `DEPL`, `REAC_NODA`, volumes `SIGM_NOEU`/`SIEQ_NOEU`, schalen `SIGM_ELNO` per laag en de Von Mises van boven-/midden-/onderzijde (`res_sup`/`res_moy`/`res_inf`), balken `SIPM_ELNO` en met `beam_forces` de snedekrachten; met `CARA_ELEM` | Keuze: Mecway gebruikt het niet, het kan honderden MB worden | nabewerking buiten Mecway | - |
| `aster_summary` (Samenvatting Code-Aster-run) | `summary` | na elke run (beide routes, ook mislukt of gestopt) `<model>_<run-id>_aster_summary.txt` in de werkmap: fouten en alarmen (elke code één keer, met het aantal), stappen, regels van de bridge, tijden, het einde van de `.mess` en het pad van de volledige `.mess`, hoogstens 400 000 tekens | Keuze: leesbaar na het sluiten van de Code-Aster-vensters zonder een `.mess` van vele MB te openen; het bestand raakt het model niet | `full`: een kopie van de hele `.mess` (boven 4 miljoen tekens het begin en het einde); `off`: geen bestand (de knoppen maken het op verzoek) | `tests/test_bridge_monitor.py` |
| `save_monitor_liml` (Samenvatting ook als Saved monitor in de .liml) | uit | dezelfde tekst in de `.liml` als Mecway's item *Saved monitor* (route `liml`); een run zonder resultaten alleen als het model nog geen resultaten heeft | Keuze (gebruiker, 28 okt 2026): het modelbestand blijft zoals het was; het samenvattingsbestand is genoeg | de uitvoer moet met het model meereizen | `tests/test_bridge_monitor.py`; formaat gemeten in Mecway 34 ([Handleiding §5.2](Handleiding.md#52-samenvatting-van-de-code-aster-run)) |
| `vtu_export` (VTU/PVD-bestanden voor ParaView) | uit | ook `<model>_<run-id>.pvd` met een `.vtu` per tijdstap (VTK, leest elke ParaView): dezelfde velden als Mecway krijgt, knoopvelden als puntdata plus de vector `DEPL`, velden per element als celgemiddelde; met bezwijken ook `BEZWEKEN` (0 intact, 1 bezweken) en `T_BEZWIJK`; plus `<model>_<run-id>_knopen.csv`: per benoemde knoopselectie (max. 100 knopen) alle knoopvelden over de tijd; alleen route `liml`, niet bij de hele schijf van cyclische symmetrie | Keuze: celgemiddelde is genoeg voor kleuren en het verbergen van bezweken elementen; de hoekwaarden staan in de `.liml` en de MED | nabewerking in ParaView zonder MED-lezer of in MWHub Post | - |
| `paraview_exe` (ParaView) | leeg (automatisch) | `paraview.exe` voor de knop *ParaView* van het convergentiescherm; leeg: eerst de officiele ParaView 6.x (`%ProgramFiles%\ParaView 6*`, leest zelf een `.rmed`), dan Salome-Meca's ParaView (gestart via zijn `run_paraview.bat`, die de Salome-omgeving zet), als laatste een oudere ParaView | werkt zonder instellen als ParaView 6.x of Salome-Meca er staat; ParaView 5.10 van paraview.org kan geen `.rmed` openen | andere ParaView-installatie | - |
| `advancedtoolshub_dir` (AdvancedToolsHub-map) | leeg (automatisch) | map van AdvancedToolsHub; gevonden = de knop *ParaView* opent de run in MWHub Post (job `<model>_<run-id>_job.json`: MED eerst, de PVD eerst als die `BEZWEKEN` heeft); leeg: `%ADVANCEDTOOLSHUB_DIR%`, anders de map `AdvancedToolsHub` naast de repository | niet gevonden = het oude gedrag (`.rmed` rechtstreeks in ParaView) | hub op een andere plek | - |
| `elem_hex8` (Hex8-volume-elementen) | `3D` | `MODELISATION='3D'` (volledig geïntegreerd) | CA-standaardelement; `LINE_QUAD` werkt alleen bij een model met uitsluitend volume-elementen en niet expliciet, en geeft ~3x zoveel knopen | buiging met weinig hex8 over de dikte: `LINE_QUAD` (of hex20 in Mecway) | LS-02: hex8 `3D` −35,7 / −13,1 / −4,3 / −1,7 / −0,9 % (n = 1…16), `LINE_QUAD` = hex20; KNOWN_BUGS 1 |
| `elem_shell` (Lineaire schalen) | `DKT` | tri3/quad4 → `DKT` (Kirchhoff) | Keuze: dunne platen, lineair en niet-lineair bruikbaar (`DST` alleen lineair) | grote rotaties of dikke schalen: `COQUE_3D` | LS-03-dkt (Navier, −0,003 %), NL-02b (`COQUE_3D`), KNOWN_BUGS 2 |
| `elem_beam` (Balken) | `POU_D_E` | Euler-Bernoulli-balk | Mecway-balk is ook Euler-Bernoulli | korte, dikke balken: `POU_D_T`; grote rotaties in niet-lineair statisch met grote verplaatsingen: `POU_D_T_GD` (elders `POU_D_T`, WARNING; [Instellingen §2.9](Instellingen_contact_en_nietlineair.md#29-balken-met-grote-rotaties-elem_beam--pou_d_t_gd)); buig-torsieknik en kip van open profielen (T, C, L, I): `POU_D_TG` (welving en dwarskrachtcentrum, [Modaal en knik §3.5.1](Modaal_en_knik.md#351-balk-met-welving-elem_beam--pou_d_tg)) | LS-01 (0,00 %), MO-01, BU-01, DY-02; `POU_D_T_GD`: NL-80–89 (≤ 0,04 %); `POU_D_TG`: BU-38 … BU-42, LS-90, LS-91 |
| `beam_warping` (Welving POU_D_TG-balken bij opleggingen) | `auto` | `GRX` = 0 (`DDL_IMPO`, knoopgroep `BRGRX`) waar een buigrotatie van een `POU_D_TG`-balk vastligt (*Fixed support*, *Node rotation* dwars op de balk, starre koppeling); vrij bij een vorkoplegging en elders | Mecway kent geen welving; een inklemming verhindert de welving van de flenzen, een vorkoplegging niet (Timoshenko & Gere 1961 §5.4, §6.2; besluit gebruiker 16 okt 2026). `BLOCAGE` van *Fixed support* houdt `GRX` niet vast | `free`: welving overal vrij; `blocked`: vast in elke opgelegde knoop (kopplaten) | LS-90 (inklemming, −0,09 %), LS-90b (`free` = T L/(G J)), LS-91 en BU-39 (vork, vrij) |
| `cable_n_init_factor` (Voorspanning kabels) | 1e-6 | tension only (`CABLE`): `N_INIT` = factor × E × A [N] per kabelgroep (`AFFE_CARA_ELEM CABLE`, INFO in de log) | zonder voorspanning is een rechte kabel singulier (geen dwarsstijfheid; KNOWN_BUGS 23); Aubry (2019, §10.1) gebruikt 10 N alleen om de oplossing mogelijk te maken | 0 = geen voorspanning (gedrag tot V2026.4) | LS-54b/c (ongewijzigd, < 1e-12 relatief); SaggingCable met *Tension only*: 3,06798 m (Mecway truss 3,0680 m), met 0 singulier |

---

## 3. Instellingen per analyse

### 3.1 Gemeenschappelijk

| Instelling | Standaard | Wat het doet | Waarom | Aanpassen als | Bewijs |
|---|---|---|---|---|---|
| `fields` (Resultaatvelden) | per analyse, zie onder | welke velden naar Mecway gaan | Keuze: wat Mecway zelf ook toont | minder velden = kleiner bestand | - |
| `time_limit` [s] | 600 (statisch), 1800 (niet-lineair statisch, thermisch), 7200 (dynamisch), 900 (modaal, knik) | `P time_limit` in de `.export`; `run_aster` stopt daarna | Keuze, NIET gemeten | lange runs; een afgebroken run levert geen volledige resultaten | - |
| `memory_limit` [MB] | 2048 (statisch, modaal, knik), 4096 (overige) | `P memory_limit` in de `.export` | Keuze, NIET gemeten | `.mess` of convergentiescherm toont geheugentekort | - |
| `solver_nprec` (MUMPS NPREC) | 8 | `SOLVEUR=_F(METHODE='MUMPS', NPREC=...)`: aantal decimalen dat bij de factorisatie verloren mag gaan voor de matrix singulier heet | 8 = CA (`c_solveur.py`), in alle analyses | zie §3.2 | R-FREE (§5) |

Resultaatvelden per analyse: statisch `displacements`, `stresses`, `vonmises`,
`reactions`, `beam_forces`, `shell_forces`, `safety_factor`; niet-lineair statisch
daarnaast `plastic_strain`, `plastic_strain_eq` en `contact`; dynamisch
`displacements`, `stresses`, `vonmises`, `velocities`, `reactions`,
`plastic_strain_eq`, `beam_forces`, `safety_factor`, `contact`; thermisch
`temperature`, `heat_flux`; modaal en knik alleen `displacements` (de vormen, zoals
Mecway). De extra velden (`beam_forces`, `shell_forces`, `safety_factor`, `contact`)
doen alleen iets als het model balken, schalen, een von Mises-faalcriterium of
contact heeft; ze kosten dan weinig rekentijd. `strain`, `shell_stresses`,
`principal_stresses` en `principal_strains` staan standaard uit: ze maken de `.liml` duidelijk groter (6 resp. 18 variabelen per knoop
en per element-knoop; hoofdwaarden van schalen 12 resp. 9); `shell_forces` (8 variabelen) maakt de resultaten bij schalen
ca. 2,5 keer zo groot (3500 quad4-schalen: `.liml` 1,6 → 3,5 MB, Code-Aster-job
+0,3 s; WARNING in de log) en staat bij dynamica uit (per tijdstap). Zie
[`Handleiding.md`](Handleiding.md) §4.1.

Niet instelbaar per analyse (vast in `CONFIG_BRIDGE`, niet op het startscherm):
`template` (de `.comm`-template in `Scripts/`), `solver_command` en bij modaal/knik
`type_resu` (`DYNAMIQUE` of `MODE_FLAMB`); verder de vlaggen die een analyse naar
zijn bouwer sturen: `phenomene` (`ACOUSTIQUE` bij akoestiek), `vibroacoustic`
(vibro-akoestiek) en `type_calcul` (`HARM`). Ze horen bij de analyse zelf (een
andere waarde maakt er een andere analyse van); de pagina van een analyse toont
Code-Aster-commando en template bovenaan.

### 3.2 Statisch (`lin_static_3d`, `MECA_STATIQUE`)

| Instelling | Standaard | Wat het doet | Waarom | Aanpassen als | Bewijs |
|---|---|---|---|---|---|
| `solver_nprec` | 8 | singulariteitscontrole van MUMPS (CA-standaard); daarnaast controleert de foutgrens (`RESI_RELA`) | CA-standaard (tot 8 okt 2026 stond hier -1, zonder vastgelegde reden). Een vrij bewegend deel stopt met `FACTOR_11`, met -1 met `FACTOR_57` (foutgrens > `RESI_RELA`); beide stoppen de run | -1 alleen als je de singulariteitscontrole bewust uit wilt | R-FREE: blok alleen in X vast, -1 → `FACTOR_57` (foutgrens 12,6, conditiegetal 5,8e16), 8 → `FACTOR_11` |
| `lin_solver` | `MUMPS` | directe oplosser (`METHODE='MUMPS'`) | CA-standaard voor `MECA_STATIQUE`; robuust | weinig geheugen, goed geconditioneerd model: `GCPC` (`PRE_COND='LDLT_INC'`) | R-GCPC: LS-02 hex8 n = 8 / 16 met GCPC binnen de tolerantie, 232 / 499 iteraties bij 20 169 / 141 321 vergelijkingen |
| `lin_solver_resi` | 1e-6 | `RESI_RELA`: MUMPS = grens op de geschatte relatieve fout; GCPC = ‖r‖/‖f‖ | CA (`c_solveur.py`, type `LIN`) | `FACTOR_57` met een kleine *Erreur calculée* (< 1e-3, geen mechanisme; slank volumemodel op buiging): de waarde uit de melding (macht van tien ≥ 10 × de fout). Niet hoger dan nodig: dat verbergt een slecht model (EDF R&D, U2.08.03 §7.2.1) | hex20-uitkragende balk 1000 × 40 × 10 mm: 7,0e-6 (1e-4: doorbuiging −0,4% t.o.v. PL³/3EI); mechanisme: `FACTOR_11`, met `solver_nprec` -1 fout 13 / 64 ([Foutmeldingen](Foutmeldingen_CodeAster.md), `FACTOR_57`) |
| `error_estimator` | aan | foutschatter: `CALC_ERREUR` `ERME` (residu-schatter) op de volume-elementen, veld `errorestimate`/`errorestimaterel` en de globale relatieve fout in de log ([Foutschatter.md](Foutschatter.md)) | Keuze: kost alleen elementberekeningen (FS-01 n = 16: 1,8 s van 17,6 s) en toont altijd de mesh-kwaliteit | uit bij een zeer groot model of als de extra velden de `.liml` te groot maken | FS-01, FS-02, FS-03 (sslv153a) |
| `fracture_r_inf`, `fracture_r_sup` | 0, 0 (automatisch) | binnen- en buitenstraal van het theta-veld van `CALC_G` rond het scheurfront (alleen met `SCHEUR_`-selecties of `#ASTER-XFEM`, [Breukmechanica.md](Breukmechanica.md)) | CA kiest zelf 2 × en 4 × de elementgrootte aan het front (gemeten: "R_INF automatiquement choisi"); G en K hingen er in de verificatie niet van af (2h/4h, 4h/8h, 8h/16h gelijk) | R_SUP komt over een andere scheur, een belaste rand of de rand van het model; R_INF = 0 gaf −1,3 % op G | BR-01 (h = a/40: K −0,1 %, G −0,4 %) |
| `fracture_smoothing` | `LINEAIRE` | gladmaken langs het front (`DISCRETISATION`): een waarde per knoop | CA-standaard (`calc_g.py`); volgt K(s) langs het front | minder dan 5 knopen langs het front (oscillatie, WARNING): `LEGENDRE` met graad 0 | BR-05; gemeten met 3 knopen: 11739 / 4696 / 25826 J/m² (verwacht 9391) |
| `fracture_legendre_degree` | 5 | graad van het Legendre-polynoom (alleen `LEGENDRE`) | CA-standaard `DEGRE` 5 | kleiner dan het aantal knopen langs het front (WARNING) | gemeten: graad 5 bij 3 knopen −8 tot −22 % |
| `adapt_refine` | uit | adaptieve verfijning: na de run de elementen met de grootste fout in Mecway verfijnen (`mw.refine_x2`) en opnieuw rekenen ([Foutschatter.md](Foutschatter.md) §6) | Keuze: elke lus is een extra run en het model wordt verfijnd opgeslagen | aan als je de mesh automatisch wilt laten verfijnen | AD-02, AD-03 |
| `adapt_target_error` | 2 % | doel van de lus: globale relatieve fout (energienorm) | Keuze: voldoende voor verplaatsingen en gemiddelde spanningen | 1 tot 1,5 voor een piekspanning (AD-02: Kt binnen 2% bij 1,1%) | AD-02 (met 1,5) |
| `adapt_max_loops` | 5 | maximaal aantal verfijningen | Keuze: 2⁵ per richting op de kritieke plek | hoger bij een klein model dat het doel nog niet haalt | AD-02 (met 6) |
| `adapt_select` / `adapt_fraction` | `dorfler` / 0,5 | keuze van de elementen: Dörfler (de grootste fouten tot de helft van Σ η²), `fraction` (fractie van de elementen) of `factor` (fout > factor x gemiddelde) | Keuze: Dörfler 0,5 is de gangbare bulk-keuze (Dörfler 1996) | kleiner = minder elementen per lus, meer lussen | AD-02 |
| `adapt_neighbours` | uit | ook de elementen verfijnen die een knoop met de keuze delen | Gemeten: bij een dikke plaat alleen extra elementen (Kt binnen 2% bij 22 956 i.p.v. 15 810), bij een dunne plaat later slechte overgangen | aan bij dunne elementen | buiten de regressie ([Foutschatter.md](Foutschatter.md) §6.5) |
| `adapt_max_elements` | 200000 | niet verfijnen als het model daarna meer elementen (alle, ook schalen en balken) zou hebben (schatting met de groei van de vorige lus) | Keuze: rekent op een gewone pc | naar het geheugen; ook `memory_limit` | – |

De bridge zet in `MECA_STATIQUE` altijd `INFO=2` (statistiek van de oplosser voor het
convergentiescherm, ongeveer 15 kB tekst; Keuze).

### 3.3 Niet-lineair statisch (`nonlin_static_3d`, `STAT_NON_LINE`)

| Instelling | Standaard | Wat het doet | Waarom | Aanpassen als | Bewijs |
|---|---|---|---|---|---|
| `substeps_per_interval` | 10 | alleen zonder Mecway's *Time step size*: rekenstappen per interval tussen de tijdspunten van de lasttabellen (`DEFI_LIST_REEL` `NOMBRE`); met een stapgrootte Mecway's stappen plus de knikken van de lasttabellen | Keuze: een fijner lastpad voor plasticiteit en contact; met een stapgrootte Mecway's stappen als uitvoertijden (NL-20) | stap waar de berekening steeds vastloopt; zie de kanttekening bij `convergence_resi_rela` | R-SUB1: NL-02a met 1 substap dezelfde uitkomst (tot 1e-7) in 3 stappen |
| `newton_max_iter` | 20 | `CONVERGENCE/ITER_GLOB_MAXI` | Gemeten/Keuze: CA-standaard is 10; contact vraagt vaak meer (EDF R&D, U4.51.03) | contact dat langzaam convergeert | R-SUB1: stap 2 van NL-02a had 11 iteraties nodig |
| `newton_reac_iter` | 1 | `NEWTON/REAC_ITER`: tangentmatrix elke iteratie opnieuw | CA; aanbevolen (EDF R&D, U2.04.01; U2.04.04 §4.5.2) | niet verlagen; het startscherm accepteert minimaal 1 | R-REAC0: NL-02a met 0 stopt in de eerste stap met `DVP_2` (geen resultaten) |
| `default_time_end` [s] | 1,0 | eindtijd zonder lasttabel | Keuze (pseudotijd) | - | - |
| `convergence_criterion` | `RELA` | `RELA` = `RESI_GLOB_RELA`; `MAXI` = `RESI_GLOB_MAXI`; `RELA_OF_MAXI` = beide met `VERIF='AU_MOINS_UN'`: geconvergeerd als een van beide gehaald is (catalogus `c_convergence.py`; EDF R&D, U4.51.03), zoals CCX: relatief met een absolute ondergrens | CA-criterium | opgelegde beweging zonder weerstand: `MAXI`; relatieve rest die stagneert: `RELA_OF_MAXI` (zie onder) | R-RIGID: starre translatie, `RELA` stopt in stap 1, `MAXI` exact; R-MAXI: NL-01 met `MAXI` 1e-2 N exact tot t = 3; NL-01b: 1e-6 met `RELA_OF_MAXI` 0,05 N exact tot t = 3 (R-ROM: met 1e-3 N niet) |
| `convergence_resi_rela` | 1e-5 | `RESI_GLOB_RELA`: grootste restkracht / (opgelegde last + reacties) | Gemeten: de CA-standaard 1e-6 (EDF R&D, U4.51.03) stagneert bij ontlasten van een plastisch volume met `GDEF_LOG` (zie onder); CCX en Abaqus gebruiken 5e-3 | strenger: 1e-6 (CA-standaard), bij stagnatie met `RELA_OF_MAXI` | NL-01 (1e-5) exact tot t = 3; met 1e-6 stop op t = 2,92; R-1E5; R-SUB40 en R-CURVE (zie onder) |
| `convergence_resi_maxi` [N] | 1e-3 | `RESI_GLOB_MAXI` bij `MAXI` en `RELA_OF_MAXI` | Keuze: klein ten opzichte van de krachten in de testmodellen | `MAXI`: klein ten opzichte van de verwachte krachten; `RELA_OF_MAXI`: boven de absolute rest waarop het residu stagneert (kolom `RESI_GLOB_MAXI` in de `.mess`) | R-RIGID, R-MAXI, NL-01b, R-ROM |
| `line_search` | `auto` | `RECH_LINEAIRE` (`CORDE`, `ITER_LINE_MAXI=3`) alleen bij kabels (`CABLE`) zonder contact; `on` altijd, `off` nooit | Keuze: Aubry (2019) §10.2 en U2.04.01 raden lijnzoeken aan bij kabels; CA-standaard: geen | Newton springt heen en weer of stappen worden opgedeeld: `on`; niet met contact `CONTINUE` (`MECANONLINE3_91`, weggelaten met een WARNING) of bij `POU_D_T_GD`-balken | LS-54b/c gelijk; SaggingCable (*Tension only*) 7 in plaats van 9 iteraties; met `on`: NL-01, NL-02a, NL-04 binnen 4e-6, NL-81 en NL-90 (`POU_D_T_GD`) geen convergentie (S27) |
| `contact_algo` | `STANDARD` | `DEFI_CONTACT` `CONTINUE` met `ALGO_CONT='STANDARD'` (Lagrange) of `'PENALISATION'` met Mecway's stijfheid | CA; geen stijfheid nodig, geen penetratie | lijncontact, contact dat verloren gaat, `MECANONLINE9_4` met `LAGS_C`: `PENALISATION` | NL-03a (STANDARD faalt), NL-03b/d/f (PENALISATION exact); KNOWN_BUGS 43 |
| `contact_smoothing` | uit | `DEFI_CONTACT` `LISSAGE='OUI'` (normalen gemiddeld in de knopen) | CA-standaard `NON`; fout over scherpe randen | gebogen contactvlakken (cilinder, bol) met weinig facetten; niet bij scherpe randen of hoeken | NL-03a..f met `on`: zelfde resultaten (binnen 6e-8); Samples/PipeClip (tet10): zelfde totale contactdruk (S28) |
| `auto_time_stepping` | aan | Alleen met Mecway's *Automatic time stepping*: `DEFI_LIST_INST METHODE='AUTO'` (`PAS_MAXI` = Mecway's stap, `PAS_MINI` = 1e-6 daarvan) tussen Mecway's uitvoertijden en de knikken; `ARCHIVAGE` op de uitvoertijden | Mecway-invoer volgen (EDF R&D, U4.34.03; Aubry, 2019, §14.1) | uit = vaste stappen | NL-21a/b |
| `contact_pene_maxi` | `0.05` | Alleen `PENALISATION`: WARNING na de run als de grootste penetratie (study.mess, `CONTACT PENETRATION`) groter is dan deze fractie van de kortste rand van de slave-vlakken; 0 = uit | Keuze: 5 % van een element is zichtbaar in de vervorming; de resultaten veranderen niet | lager voor nauwkeurig contact, 0 = uit | NL-03p (WARNING), NL-03b/d/f (geen) |
| `plastic_strain_definition` | `auto` | omrekening van Mecway's hardingscurve naar `TRACTION` (totale rek) | Keuze, zie §4.2 | een curve die met (0, σ > 0) begint maar totale rek bedoelt: `total` | R-CURVE (§4.2) |
| `deformation` | `GROT_GDEP` | `COMPORTEMENT/DEFORMATION`, per elset vertaald | Gemeten: Mecway's niet-lineaire analyse (CCX) rekent geometrisch niet-lineair | kleine vervormingen en vergelijking met lineaire theorie: `PETIT` | NL-02a/b; DY-03 (verschil 1,4e-4…6,9e-4 met `GREEN_LAGRANGE`) |
| `element_failure` | aan | bezwijken van elementen boven een plastische rek | Keuze | uitzetten negeert bezwijkgrenzen | [Bezwijken.md](Bezwijken.md) |
| `failure_plastic_strain` | 0 (uit) | grens voor alle plastische materialen zonder eigen grens | Keuze | - | [Bezwijken.md](Bezwijken.md) |
| `failure_stiffness_factor` | 1e-6 | E van een bezweken element × factor | Gemeten: 1e-9 maakte de matrix singulier; begrensd 1e-7…0,1 | - | [Bezwijken.md](Bezwijken.md) §7 |
| `crit_stab` | uit | `CRIT_STAB` in `STAT_NON_LINE`: na elke stap de kleinste kritische waarde (lastfactor bij kleine verplaatsingen, eigenwaarde van K_T bij grote) | Keuze: kost per stap een eigenwaardeberekening; alleen nuttig bij een knikvraag | knik of grenspunt zoeken: aan | NK-01, NK-02a/b, NK-04 ([Modaal_en_knik.md](Modaal_en_knik.md) §5) |
| `imperfection_amplitude` | 0 (geen) | grootste verplaatsingscomponent van de knikvorm waarmee het mesh vooraf vervormd wordt | Keuze: zonder opgave rekent de bridge de geometrie van Mecway | draagkracht of gedrag na knik: L/1000 tot L/300 of de waarde uit de norm | NK-03, NK-04 |
| `imperfection_mode` | 1 | welke knikvorm (1 = kleinste kniklastfactor) | Keuze: de maatgevende vorm | twee vormen met bijna dezelfde factor | NK-03 |
| `imperfection_unit` | `m` | `m`: amplitude in m; `L`: fractie van de grootste afmeting van het model | Keuze | amplitude als L/x opgeven: `L` | NK-03 (`L`) |
| `lin_solver_resi` | 1e-6 | `RESI_RELA` van de `MECA_STATIQUE` van de imperfectie (lineaire knik vooraf); `STAT_NON_LINE` zelf controleert het niet (CA-standaard -1) | als §3.2 | als §3.2 | - |

**Waarom 1e-5 en niet de Code-Aster-standaard 1e-6.** In de trekstaaf van NL-01
(plastische volumes, dus `GDEF_LOG`) blijft de restkracht steken: bij een kleine last
op ongeveer 5e-4 N, bij het ontlasten op ~1e-2 N bij 12 kN (`RESI_GLOB_RELA`
~1,5…2,3e-6). Dat is meer dan 1e-6 van de reactie: Newton haalt het criterium niet,
de stap wordt geknipt, de last wordt nog kleiner en de run stopt (`MECANONLINE9_7`).
Gemeten met 1e-6: NL-01 stopt op t = 2,92; met 40 in plaats van 10 substappen al op
t = 0,013 (R-SUB40); een hardingscurve met totale rek stopte ook op t = 0,013
(R-CURVE). Met 1e-5, `MAXI` 1e-2 N of `RELA_OF_MAXI` (1e-6 en 0,05 N) rekenen ze
door en zijn ze exact (NL-01, NL-01b, R-SUB40-1E5, R-CURVE, R-MAXI). Met `PETIT`
speelt het niet (R-SUB40-PETIT). Kleinere stappen helpen hier dus niet, ze maken het
erger. De overstap van 1e-6 naar 1e-5 veranderde de resultaten van alle NL- en
DY-verificatiecases hooguit 3,75e-6 relatief (R-1E5); CCX en Abaqus rekenen met 5e-3.
Wie de Code-Aster-standaard wil, zet 1e-6 en bij stagnatie `RELA_OF_MAXI` met een
`RESI_GLOB_MAXI` boven de absolute rest waarop het stagneert (kolom `RESI_GLOB_MAXI`
in de `.mess`; met 1e-3 N bleef NL-01 hangen, R-ROM). Thermisch (`ther_3d`) blijft
1e-6 (§3.6).

### 3.4 Dynamisch impliciet (`dyna_impl_3d`, `DYNA_NON_LINE`)

Dezelfde instellingen als §3.3 voor Newton, convergentie, contact, materiaal en
bezwijken (zonder `substeps_per_interval`), plus:

| Instelling | Standaard | Wat het doet | Waarom | Aanpassen als | Bewijs |
|---|---|---|---|---|---|
| `schema` | `HHT` | `SCHEMA_TEMPS` `HHT` (`MODI_EQUI='OUI'`, CA) of `NEWMARK` (β = 1/4, γ = 1/2) | Keuze: HHT dempt hoge frequenties (EDF R&D, U2.06.13) | geen numerieke demping gewenst: `NEWMARK` | DY-01a (HHT), DY-01b/c/d (NEWMARK, orde 1,98/1,99) |
| `hht_alpha` | -0,1 | `ALPHA` van HHT | CA (`dyna_non_line.py`); U2.06.13: begin bij -0,1, -0,3 is een bovengrens | hoogfrequente ruis: negatiever, tot -0,3 | DY-01a, DY-02, DY-03c; R-ALPHA: DY-01 met -0,3 volgt het schema op 4,7e-8 (periode +1,21 %, piek −0,87 %, zoals voorspeld) |
| `substeps_per_output` | 1 | rekenstappen per uitvoerinterval van Mecway's `<timesteps>` | Keuze: rekenstap = uitvoerinterval | grote uitvoerintervallen ten opzichte van de eerste periode | DY-01, DY-02, DY-03c |
| `energy_balance` | uit | `ENERGIE=_F()`: energiebalans per stap in de `.mess` | Keuze: alleen ter controle; niet met contact (`MECANONLINE5_15`, de bridge laat het dan weg) | controle van de energie | R-ENERGY: DY-01a met energiebalans, zelfde uitkomst, 101 balansregels |
| `time_limit` | 7200 | zie §3.1 | | | |

### 3.5 Dynamisch expliciet (`dyna_expl_3d`, `DYNA_NON_LINE`)

| Instelling | Standaard | Wat het doet | Waarom | Aanpassen als | Bewijs |
|---|---|---|---|---|---|
| `schema` | `DIFF_CENT` | centrale differenties, `MASS_DIAG='OUI'`, `FORMULATION='ACCELERATION'` | Keuze; diagonale massa aanbevolen (EDF R&D, U4.53.01) | hoge frequenties dempen: `TCHAMWA` (`PHI` = 1,05, CA) | DY-03a/b; R-TCHAMWA: DY-03a met TCHAMWA binnen de tolerantie |
| `explicit_dt_factor` | 0,5 | stap ≤ factor × geschatte kritieke stap (kleinste ribbe / drukgolfsnelheid), per uitvoerinterval gelijk verdeeld | Gemeten, zie onder | `DYNAMIQUE_2` (stap te groot): verlagen | DY-03a; R-DT |

**`explicit_dt_factor` ten opzichte van de CFL-grens van Code-Aster.** De factor geldt
voor de schatting van de bridge, niet voor de grens die Code-Aster zelf berekent. In
DY-03a (hex8-kubussen van 10 mm, ν = 0) schat de bridge 1,933e-6 s; Code-Aster meldt
een maximale stap van 9,667e-7 s, de helft (R-DT). De standaard 0,5 valt dus op de
grens van Code-Aster; door de gelijke verdeling per uitvoerinterval werd de stap
8,33e-7 s (0,86 × de CFL-grens). Met 0,7 en hoger weigert Code-Aster de run
(`DYNAMIQUE_2`, `STOP_CFL='OUI'`); er ontstaat dus geen stille instabiliteit. EDF R&D
(U2.06.13) raadt 0,5…0,7 × de CFL-grens aan; dat is in dit voorbeeld een factor
0,25…0,35. Met 0,3 bleef DY-03a binnen de tolerantie (R-DT, 9 in plaats van 6 stappen
per uitvoerinterval). Voor andere elementvormen is de verhouding NIET gemeten.

### 3.6 Thermisch (`ther_3d`, `THER_LINEAIRE` / `THER_NON_LINE`)

| Instelling | Standaard | Wat het doet | Waarom | Aanpassen als | Bewijs |
|---|---|---|---|---|---|
| `theta` | 0,57 | `SCHEMA_TEMPS` `THETA` (0 expliciet, 0,5 Crank-Nicolson, 1 impliciet Euler) | CA (`ther_lineaire.py`) | Mecway exact volgen: 0,5 | TH-02 (θ 0,5 / 0,57 / 1,0); KNOWN_BUGS 14 |
| `newton_max_iter`, `convergence_resi_rela`, `newton_reac_iter` | 20, 1e-6, 1 | `THER_NON_LINE` (straling, convectie op schaalvlakken, temperatuurafhankelijk materiaal) en de mechanische `STAT_NON_LINE` van de keten thermisch → mechanisch | als §3.3 | keten niet geconvergeerd (`BRIDGE_ONVOLLEDIG`): eerst `TC_CUT` en E/SY bij hoge temperatuur ([Lassen.md](Lassen.md) §9.8) | TH-01e; WE-07..10 |
| `deformation` | PETIT | alleen de keten thermisch → mechanisch (T31 met Thermal stress): `COMPORTEMENT DEFORMATION` | lassen: kleine rekken en rotaties | grote vervorming (dunne plaat die knikt): `GDEF_LOG` (NIET geverifieerd in de keten) | WE-07..10 |
| `plastic_strain_definition` | auto | idem, rekdefinitie van een Mecway-hardingscurve | als §3.3 | als §3.3 | - |
| `solver_nprec`, `time_limit`, `memory_limit` | 8, 1800, 4096 | zie §3.1 | | | |

### 3.7 Modaal (`modal_3d`, `CALC_MODES` `DYNAMIQUE`)

| Instelling | Standaard | Wat het doet | Waarom | Aanpassen als | Bewijs |
|---|---|---|---|---|---|
| `modal_modes` | 10 | `NMAX_FREQ` als het Mecway-model geen `maxmode` heeft | Keuze | - | - |
| `modal_shift_hz` | 0 | 0: `OPTION='PLUS_PETITE'` (zonder opleggingen in Mecway: automatisch `'CENTRE'` rond −f_s, §4.8); > 0: `'CENTRE'` rond deze frequentie; < 0: de laagste modes met een verschoven, regelmatige K − σM (mechanismen) | CA-optie `PLUS_PETITE` = de laagste modes, zoals Mecway | modes rond een excitatiefrequentie; een mechanisme (`ALGELINE3_81`): negatief | R-SHIFT: MO-01 met 600 Hz gaf de 6 modes het dichtst bij 600 Hz gemeten in ω² (eigenwaarde), niet in Hz; KNOWN_BUGS 48 |
| `modal_norm` | `MASS_GENE` | `NORM_MODE`: φᵀMφ = 1 | Gemeten: zo normeert Mecway | vormen vergelijken: `TRAN`/`TRAN_ROTA` (CA-standaard) | MO-01 (tip 2/√m exact); R-NORM: `TRAN_ROTA` maakt de grootste component 1 (hier de tiprotatie) |
| `modal_tolerance` | 1e-6 | `VERI_MODE SEUIL` (de bridge zet `STOP_ERREUR='NON'`) | CA (`calc_modes.py`) | `ALGELINE5_15` bij een grof model: groter | [Modaal_en_knik.md](Modaal_en_knik.md) §2.4 |
| `modal_prestress` | aan (`True`) | met belastingen of thermische rek: eerst `MECA_STATIQUE`, dan de modes met K + K_g (`RIGI_GEOM`; bij centrifugaalkracht ook `RIGI_ROTA`); uit: belastingen genegeerd (WARNING) | Mecway rekent zo zodra er belastingen zijn (manual §6.3) | de onbelaste frequenties willen zien; een opgelegde verplaatsing ≠ 0 die alleen als oplegging moet tellen | MP-01..07 (Mecway en analytisch, [Verificatie.md](Verificatie.md) §7); MP-06 (uit) |
| `lin_solver_resi` | 1e-6 | `RESI_RELA` van de `MECA_STATIQUE` voor de voorspanning (ook bij cyclische symmetrie); `CALC_MODES` controleert het niet (CA-standaard -1) | als §3.2 | als §3.2 | hex20-uitkragende balk met 100 N dwars: 7,0e-6, met 1e-4 f₁ = 8,3765 Hz (zonder voorspanning gelijk, analytisch 8,355) |
| `modal_complex` | uit (`False`) | aan + Rayleigh-demping en/of dempers in het model: complexe modes, `CALC_MODES` met `MATR_AMOR` (C = αM + βK + C_dempers); per mode de gedempte frequentie f_d (in Mecway's `<mode>`), ζ en f_n in log en statusvak; vorm = reëel deel (φᵀMφ = 1), `decayrate` = ζ·2πf_n; geen spanningen per mode. Uit: de demping telt niet mee (INFO) | Mecway's Frequency-analyse negeert Rayleigh-demping en rekent niet met een Damper (headless gemeten); complexe modes zijn de Code-Aster-route (testcase sdld21c) | de gedempte frequenties en de dempingsverhouding per mode willen zien, bijv. om Rayleigh-coëfficiënten te controleren of het effect van dempers te zien | MC-01..05 ([Verificatie.md](Verificatie.md) §7): ζ en f_d ≤ 1e-6 analytisch, f_n gelijk aan Mecway |
| `cyclic_base_modes` | 0 (= max(20, 4 × modes per ND)) | alleen met Mecway's *Cyclic symmetry*: aantal modes van de sector met vaste snijvlakken in de basis van `MODE_ITER_CYCL` (`CALC_MODES NMAX_FREQ`, `DEFI_BASE_MODALE NMAX_MODE`, `NB_MODE`) | Keuze: met 20 waren de modes van de ring en de schijf gelijk aan het volledige model (≤ 0,001%); de basis bepaalt de nauwkeurigheid van de hoogste modes per ND | hoge modes per ND; ter controle verdubbelen (de frequenties moeten gelijk blijven) | CY-01..05 ([Verificatie.md](Verificatie.md) §7); [Modaal_en_knik.md](Modaal_en_knik.md) §7 |
| `cyclic_full_wheel` | aan | alleen met Mecway's *Cyclic symmetry*: de modes op het **hele wiel** naar Mecway (alle N sectoren met hun fase: `DEFI_SQUELETTE CYCLIQUE` + `REST_SOUS_STRUC SQUELETTE`), met dezelfde knoop- en elementnummers als Mecway's eigen cyclische oplossing (knoop i van sector j = i + j·n, element e + j·ne); uit = alleen de sector | Mecway: de eigen oplossing toont het hele wiel (headless gemeten) | uit bij een groot model als het resultaatbestand te groot wordt (N keer zo groot) | CY-01..06 ([Verificatie.md](Verificatie.md) §7); [Modaal_en_knik.md](Modaal_en_knik.md) §7 |
| `fields` | `["displacements"]` | met `stresses`/`vonmises` (ook `strain`, `beam_forces`, `shell_stresses`, `shell_forces`): waarden per mode (`CALC_CHAMP` op de modes, zonder `REAC_NODA`); andere velden genegeerd (INFO) | Mecway's standaardoplossing van een mode heeft alleen de vorm; spanningen zijn bij genormeerde vormen alleen relatief betekenisvol | waar een mode de grootste spanning geeft | MO-07 (σ_xx mode 1 +0,43% Euler-Bernoulli, +0,01% Mecway) |
| (vast) effectieve massa rotaties | om de globale assen door de oorsprong | RX/RY/RZ per mode in log en statusvak (eigen berekening, Γ = φᵀMR); fractie van RᵀMR inclusief opgelegde knopen, zoals Code-Aster's translaties | zoals Mecway (manual §6.3, headless nagelopen); Code-Aster kent geen `MASS_EFFE_UN_DRX` | ander rotatiepunt: oorsprong in Mecway verleggen | MO-01, MO-04, MO-06, MO-07 ([Modaal_en_knik.md](Modaal_en_knik.md) §1.5) |
| `solver_nprec`, `time_limit`, `memory_limit` | 8, 900, 2048 | zie §3.1 | | | |

### 3.8 Knik (`buckling_3d`, `CALC_MODES` `MODE_FLAMB`)

| Instelling | Standaard | Wat het doet | Waarom | Aanpassen als | Bewijs |
|---|---|---|---|---|---|
| `modal_modes` | 4 | `NMAX_CHAR_CRIT` zonder `maxmode` | Keuze | - | - |
| `modal_norm` | `RIGI_GENE` | φᵀKφ = 1 (de bridge normeert zelf: Code-Aster kent het niet voor knik, `ALGELINE4_77`) | Gemeten: zo normeert Mecway | - | BU-01 (tip exact) |
| `modal_tolerance` | 1e-6 | als §3.7 | CA | | |
| `lin_solver_resi` | 1e-6 | `RESI_RELA` van de statische stap (spanningstoestand) | als §3.2 | als §3.2 | BU-37 (hex20-L-raamwerk: fout 5,0e-5, met 1e-3 gelijk aan `RESI_RELA` -1 en Mecway +0,4%) |

**Geen zoekcentrum bij knik.** Knik zoekt altijd de kleinste ∣kniklastfactoren∣
(`OPTION='PLUS_PETITE'`), zoals Mecway; er is geen instelling voor een zoekcentrum.
`OPTION='CENTRE'` negeert `CHAR_CRIT` bij `TYPE_RESU='MODE_FLAMB'` in Code-Aster 17.4:
met `CHAR_CRIT` 90, 95, 150, 200 en −200 gaf BU-01 steeds de kleinste factoren (10,36 / 23,32 / 93,27) en
meldt de `.mess` "La valeur de décalage en charge critique est : 0.00000E+00"
(R-BSHIFT). `OPTION='BANDE'` werkt wel (`CHAR_CRIT=(100, 300)` gaf 209,853 en
259,086), maar de bridge biedt het niet aan. Mecway's *Shift point* bij knik is een
instelling van Mecway's eigen oplosser, geen zoekcentrum (BucklingPlate met shift
1000 gaf factoren 7…12); de bridge meldt hem alleen in de log.

### 3.9 Vaste keuzes zonder instelling

| Wat | Waarde in de bridge | Code-Aster-standaard | Waarom / bewijs |
|---|---|---|---|
| Stapverkleining (`DEFI_LIST_INST` `ECHEC`) | `EVENEMENT='ERREUR'`, `ACTION='DECOUPE'`, `SUBD_PAS=4`, `SUBD_NIVEAU=6` | `SUBD_PAS=4`, `SUBD_NIVEAU=3` (catalogus) | Keuze: meer niveaus (tot 1/4096 van de stap); met alleen `DEFI_LIST_REEL` knipt `STAT_NON_LINE` niet (EDF R&D, U4.51.03; melding `SUBDIVISE_3`) |
| `NEWTON/PREDICTION` | niet gezet (behalve bij bezwijken en in de keten thermisch → mechanisch met toevoegmateriaal, §3.17) | geen catalogus-standaard; volgt `MATRICE` (NIET geverifieerd) | EDF R&D (U2.04.01) raadt `ELASTIQUE` aan bij problemen |
| Contact `INTEGRATION` | `'NCOTES'` op kwadratische slave-vlakken, anders `'AUTO'` | `'AUTO'` | Gemeten: `AUTO` haalde de contact-patchtest op hex20 niet (1,5…4,6 %), `NCOTES` exact (NL-03c…f) |
| Contact `CONTACT_INIT`, `ADAPTATION`, `VERI_NORM` | niet gezet | `'INTERPENETRE'`, `'CYCLAGE'`, `'OUI'` | CA (`defi_contact.py`) |
| HHT `MODI_EQUI` | niet gezet | `'OUI'` (volledig HHT, tweede orde) | CA; aanbevolen in EDF R&D (U2.06.13) |
| Expliciet `STOP_CFL` | niet gezet (`'NON'` als er geen element met materiaal is) | `'OUI'` | CA; zonder materiaal kan Code-Aster de grens niet bepalen (`DYNAMIQUE_4`) |
| `ARCHIVAGE` | dynamisch: de uitvoertijden; statisch: niet gezet (elke stap) | elke stap | Keuze |
| MUMPS `RESI_RELA` niet-lineair | niet gezet | -1 (geen controle op de foutgrens; type `NL` in `c_solveur.py`) | CA; Newton controleert het evenwicht. Met `solver_nprec` -1 is er dan geen enkele singulariteitscontrole (R-NPREC-CONTACT) |
| `MECA_STATIQUE` `INFO` | 2 | 1 | Keuze: statistiek van de oplosser voor het convergentiescherm |
| Foutschatter: druk op de vrije vlakken | `PRES_REP` 1e-14 Pa (groep `BRERRVRIJ`) | een vlak zonder last telt als opgelegd (geen randterm) | Gemeten: met 0 bleef de randterm gelijk aan die zonder de vlakken; 1e-14 zoals testcase sslv153a ([Foutschatter.md](Foutschatter.md) §2.2) |
| Foutschatter: teken van `FORCE_FACE` | omgekeerd in de last van de schatter | `ERME` rekent de randterm van `FORCE_FACE` als σ·n + g | Gemeten: blok onder uniforme trek 15% met het teken van de oplossing, 0,000% omgekeerd; `PRES_REP` 0,000% ([Foutschatter.md](Foutschatter.md) §2.3) |
| `CALC_MODES` `VERI_MODE STOP_ERREUR` | `'NON'` | `'OUI'` | Keuze: Sturm-test faalt bij meervoudige modes op de grens ([Modaal_en_knik.md](Modaal_en_knik.md) §3.1) |
| Precisie van de resultaten | statisch en modaal float64; dynamisch en thermisch transient float32 | - | Keuze (zoals Mecway's eigen resultaten); float32: ulp ~3e-5 K bij 380 K (TH-02) |
| Lasbron: tijdstapmelding (`bridge_welding.MAX_JUMP`) | WARNING als v·Δt > 0,5 × (af + ar) | - | Gemeten (temperatuur, geen energieverlies): op de grens naast de bron −2,2%, op de lasas −2,9% t.o.v. de analytische oplossing van dezelfde bron (t.o.v. de run met v·Δt = (af + ar)/6: −0,8% en −2,7%, zoals in het commentaar bij `MAX_JUMP`); bij 1 × (af + ar) −26% (WE-01/WE-01b, [Lassen.md](Lassen.md) §4.1) |
| Lasbron: meshmelding (`MAX_H`) | WARNING als een element langs de baan in een richting > 0,8 × de halve as | - | Berekend: integratiefout 2 Gauss-punten per richting 0,3% bij 0,8·a, 1,8% bij 1,0·a ([Lassen.md](Lassen.md) §4.2) |
| Lasbron: automatische brongroep (`CUTOFF`) | volume-elementen binnen 3 × de grootste halve as van de baan | - | q < 2·10⁻¹² van de piek daarbuiten; WE-01/02: energie ≤ 0,06% |
| Lasbron: energiecontrole (`POWER_TOL`) | WARNING als het opgenomen vermogen > 2% van η·Q afwijkt (vijf tijdstippen) | - | Keuze (tolerantie van de energiebalans); WE-01: +0,09% |
| Metallurgie: TAUX van de dataset | 16MND5: 0,34 s (zoals mtlp103a) | - | Bron getrouw overgenomen; bij lassen kleiner zetten (`TAUX_1=TAUX_3=0.001`): gemeten loopt de austenitisering bij snel opwarmen met grote stappen achter ([Lassen.md](Lassen.md) §10.5) |
| Metallurgie: melding achterlopende austenitisering | WARNING als knopen > Ac3 + 50 °C kwamen maar < 90% austeniet werden | - | Keuze; MT-06 met TAUX 0,34 s: lasas 6% austeniet |
| Toevoegmateriaal: stil materiaal (`bridge_welding.QUIET`) | voor de geboorte ρ·c × 10⁻⁴, λ × 10⁻⁸, E (en de versteviging) × 10⁻⁴ | - | Gemeten (prototype, rups in een keer geboren na 2 s): λ en ρ·c allebei × 10⁻³ gaf +21% energie bij de geboorte (de rups was door geleiding al warm), λ × 10⁻⁶ nog +3,3%; WE-11: +1,2..1,6%, WE-12: spanning vóór de geboorte 1,8·10⁻⁴ × E·α·ΔT ([Lassen.md](Lassen.md) §11) |
| Toevoegmateriaal: voorloop (`LEAD_AF`) | 2 × af | - | Berekend: buiten de voorloop ligt erfc(√3·voorloop/af) van het voorste deel van de bron (1 × af: 1,4%, 2 × af: 4·10⁻⁷) |
| Toevoegmateriaal: geboortemoment | levend vanaf de eerste staptijd na tb (tb = t0: vanaf t0); mechanisch spanningsvrij in de toestand van het begin van de geboortestap | - | Keuze (resolutie Δt); WE-12: krimpspanning t.o.v. de geboortetemperatuur −0,01% |
| Toevoegmateriaal: warmtecapaciteit | `3D_DIAG` (diagonaal) in het toevoegmateriaal | `3D` (consistent) | Gemeten: consistent warmde een stil knooppunt via de massakoppeling op (WE-13: +138 K voor de geboorte) |

### 3.10 Respons op modale basis (`dyna_modal_3d`, `DYNA_VIBRA` `GENE`)

| Instelling | Standaard | Wat het doet | Waarom | Aanpassen als | Bewijs |
|---|---|---|---|---|---|
| `modal_modes` | 10 | `NMAX_FREQ` als het Mecway-model geen `maxmode` heeft | Keuze, als modaal | - | - |
| `steps_per_period` | 50 | rekenstap `NEWMARK` = periode van de hoogste mode / 50, geheel aantal per uitvoerinterval | Mecway integreert exact (gemeten); periodefout (ω·Δt)²/12 = 0,13% voor de hoogste mode (Hughes, 2000, §9.3) | lager alleen als de run te lang duurt | MD-01 (Δt Mecway 0,01 s): u(t) binnen 1,2e-4 van exact, 1,4e-5 van Mecway |
| `modal_damping` | 0 | extra ζ op alle modes in `AMOR_REDUIT` (bovenop Rayleigh) | Keuze: Mecway kent alleen Rayleigh | een dempingsverhouding uit een norm | MD-04 (piek ζ = 0,05 −0,00%) |
| `static_correction` | uit | `MACRO_ELAS_MULT` als `MODE_CORR`, `CORR_STAT='OUI'` (testcase forma12d) | Gemeten: Mecway doet geen statische correctie (1 mode: 0,9707 × statisch) | weinig modes, spanningen bij een langzame last | MD-06a/b (zonder 0,97069, met 1,00000 × statisch) |
| `fields` | `displacements`, `velocities`, `stresses`, `vonmises` | `REST_GENE_PHYS` `DEPL`/`VITE` (+ `ACCE` voor balkspanningen) en `CALC_CHAMP` | zoals Mecway's D30-uitvoer (verplaatsing, snelheid, hoeksnelheid, von Mises) | kleinere `.liml` | MD-05 (σ_xx 4e-4 t.o.v. Mecway) |
| `modal_tolerance`, `solver_nprec`, `time_limit`, `memory_limit` | 1e-6, 8, 1800, 2048 | als §3.7 en §3.1 | | | |

### 3.11 Akoestiek (`acoustic_modes_3d`, `ACOUSTIQUE` + `CALC_MODES`)

| Instelling | Standaard | Wat het doet | Waarom | Aanpassen als | Bewijs |
|---|---|---|---|---|---|
| `modal_modes` | 10 | `NMAX_FREQ` als het Mecway-model geen `maxmode` heeft | Keuze (als modaal) | - | - |
| `modal_shift_hz` | 0 | 0: `OPTION='PLUS_PETITE'`; zonder drukknoop (harde wanden) automatisch `'CENTRE'` rond −0,1·c_min/(2D) (D = diagonaal van het omhullende blok); > 0: `'CENTRE'` rond deze frequentie | CA; `PLUS_PETITE` stopt bij harde wanden met `ALGELINE3_81` (de 0-Hz-mode, gezien) | modes rond een bromtoon of excitatiefrequentie; een los deel zonder drukknoop: negatief | AK-01, AK-04, AK-05 (harde wanden; frequenties gelijk aan Mecway) |
| `modal_tolerance` | 1e-6 | als §3.7 | CA | | |
| `solver_nprec`, `time_limit`, `memory_limit` | 8, 900, 2048 | zie §3.1 | | | |
| (vast) normering | pᵀMp = 1, M = ∫NᵀN/c² dV | `aster_results_export` schaalt met 1/√`MASS_GENE` (`NORM_MODE` werkt niet voor `MODE_ACOU`, gezien) | zoals Mecway (headless nagelopen) | - | AK-01…04: max ∣p∣ gelijk aan Mecway (< 1e-9) |
| (vast) dichtheid | `RHO` uit het materiaal, anders 1 kg/m³ | `DEFI_MATERIAU FLUIDE` vraagt `RHO`; de akoestische matrices bevatten hem niet (gemeten) | - | - | [Akoestiek.md](Akoestiek.md) §3.2; media met verschillende dichtheid: ERROR |
| (vast) met *Impedance*: complexe modes | `RIGI_ACOU`, `MASS_ACOU` en per rand `AMOR_ACOU` (`CELE_R = 1`); (K + λC + λ²M)P = 0 met C = Σ ρ/Z ∫NNᵀdA in de job (scipy: linearisering, shift-invert ARPACK; dicht als 2n ≤ 300, n = vrije drukvrijheidsgraden) | `CALC_MODES` neemt `MATR_AMOR` niet voor drukmatrices; zelfde probleem als Mecway (manual §6.9.2) | - | - | AI-01…10: gelijk aan Mecway ≤ 1e-8, analytisch ≤ 0,15% (hex20, tot 935 Hz) |
| (vast) modes met impedantie | de 2·n eigenwaarden met de kleinste \|λ\|, daarvan die met f ≥ 0 (n = maxmode of `modal_modes`); met `modal_shift_hz` > 0 de n met f ≥ 0 het dichtst bij i·2π·f | zoals Mecway (headless nagegaan); 0-Hz-modes altijd één keer (Mecway: willekeurig) | - | zoekfrequentie > 0: modes rond een frequentie | AI-01…10 (zelfde lijst als Mecway, op de 0-Hz-modes na) |
| (vast) normering met impedantie | fase zo dat PᵀMP reëel is, dan PᴴMP = 1, grootste Re P positief | Mecway schaalt willekeurig (Euclidisch, willekeurige fase, gemeten); zo is Z → ∞ precies de reële mode | - | - | AI-03; P(L)/P(0) gelijk aan Mecway (AI) |
| `modal_tolerance` met impedantie | 1e-6 | grens voor het residu ‖Q(λ)P‖/((‖K‖+\|λ\|‖C‖+\|λ\|²‖M‖)‖P‖): WARNING erboven | Keuze (zelfde instelling als `VERI_MODE`) | groter bij een WARNING en een goed mesh | AI: residu ≤ 1e-10 |

### 3.12 Responsspectrum (`spectrum_3d`, `COMB_SISM_MODAL`)

| Instelling | Standaard | Wat het doet | Waarom | Aanpassen als | Bewijs |
|---|---|---|---|---|---|
| `modal_modes` | 20 | `NMAX_FREQ` als het Mecway-model geen `maxmode` heeft | Keuze: meer dan modaal, een spectrum vraagt ~90% effectieve massa | - | - |
| `spectrum_abscissa` | `period` | kolom *time* van de gravity-tabel = periode [s] of frequentie [Hz] | normen geven spectra in T (EN 1998-1 §3.2.2.2) | spectrum in Hz | SP-02..06 (periode), formule in de `.comm` |
| `spectrum_damping` | 0.05 | ξ van elke mode in `AMOR_REDUIT` (plus Mecway's Rayleigh) | de gebruikelijke demping van ontwerpspectra (EN 1998-1: η = 1 bij 5%) | spectrum voor een andere demping; 0 met Rayleigh in Mecway | SP-01 (Rayleigh, 0), SP-02..07 |
| `modal_combination` | `CQC` | `COMB_MODE TYPE` | Code-Aster-standaard; juist ook bij dicht bij elkaar liggende modes | SRSS of ABS als de norm het vraagt | SP-02 (SRSS), SP-03 (CQC) exact |
| `direction_combination` | `SRSS` | `COMB_DIRECTION` `QUAD`; `100-30-30` rekent de bridge uit `VALE_DIRE`; `100-40-40` = `NEWMARK` | Keuze: SRSS is de neutrale regel (EN 1998-1 §4.3.3.5.2 (2)); Code-Aster-standaard is `NEWMARK` | de norm vraagt 100-30-30 of 100-40-40 | SP-06a/b/c exact |
| `missing_mass` | aan | `MODE_STATIQUE PSEUDO_MODE` + `MODE_CORR='OUI'`, `FREQ_COUP` = hoogste gerekende frequentie | Keuze (Code-Aster-standaard `NON`): reacties en spanningen zijn compleet, ook met weinig modes | alleen de modes tellen (norm met ≥ 90% massa) | SP-04 (aan), SP-05 (uit) exact |
| `fields` | `displacements`, `accelerations`, `stresses`, `vonmises`, `reactions` | `OPTION` `DEPL`, `ACCE_ABSOLU`, `SIGM_ELNO`, `REAC_NODA`; von Mises per mode gecombineerd | de maxima die een gebruiker nodig heeft | kleinere `.liml` | SP-01, SP-07 |
| `modal_tolerance`, `solver_nprec`, `time_limit`, `memory_limit` | 1e-6, 8, 1800, 2048 | als §3.7 en §3.1 | | | |

### 3.13 Akoestiek harmonisch (`acoustic_harm_3d`, `ACOUSTIQUE` + `DYNA_VIBRA` `HARM`)

| Instelling | Standaard | Wat het doet | Waarom | Aanpassen als | Bewijs |
|---|---|---|---|---|---|
| `harm_freq_start`, `harm_freq_end` | 50, 1000 Hz | bereik van de frequenties (`DEFI_LIST_REEL` → `LIST_FREQ`) | Keuze: een gangbaar bereik voor ruimtes en kanalen | het bereik van de vraag; de eindfrequentie bepaalt de mesh-fijnheid (≥ 10 lineaire / 5 kwadratische elementen per golflengte, anders WARNING) | AH-01, AH-01b, AH-02a/b |
| `harm_freq_count` | 20 | aantal frequenties van start tot eind (1 = alleen de start) | Keuze: rekentijd lineair in het aantal | pieken zoeken: stap kleiner dan een piekbreedte | - |
| `harm_freq_spacing` | `lin` | `lin` gelijke stappen, `log` gelijke verhoudingen | Keuze | breed bereik (octaven): `log` | - |
| `harm_freq_list` | `0` | eigen lijst (tekst, komma's); `0` = het bereik | Keuze | vaste frequenties (tertsbanden, toerentallen) | AH-01…07 (lijst), AH-08 (`#ASTER-OPTIE`) |
| `source_velocity` | 0,001 m/s | normaalsnelheid van de `BRON_`-vlakken, de fluid in, fase 0 (`VITE_FACE VNOR`) | Keuze: 1 mm/s geeft in lucht 0,41 Pa (83 dB), een realistische orde; alles is lineair in v | de werkelijke amplitude; per vlak: `#ASTER-BRON` | AH-01 (\|p\| = ρcv0), AH-04 |
| `#ASTER-BRON selectie = v [, fase]` | - | normaalsnelheid per vlakselectie: zonder eenheid m/s, verder mm/s, mm/ms, in/s, ft/s; fase in graden (standaard 0) | een druk-eenheid (Pa, kPa, bar, ...), een andere eenheid of tekst zonder getal geeft een ERROR (tot oktober 2026 werd `2 Pa` stil 2 m/s en `abc` 0 m/s); een opgelegde druk is Mecway's *fluid pressure* ≠ 0 | - | §4.14 |
| `solver_nprec`, `time_limit`, `memory_limit` | 8, 900, 2048 | zie §3.1 | | | |
| (vast) richting en fase | v > 0 de fluid in; p(t) = Re(P e^{iωt}) | `EXCIT` `COEF_MULT=+1`, `PUIS_PULS=1`, `PHAS_DEG=90` | gemeten: dan p = +ρcv op de bron (ahlv100a: −1, v naar buiten) | - | AH-01, AH-04 (−P = ahlv100a) |
| (vast) SPL | 20·log10(\|P\|/(√2·20 µPa)), drukknoop −200 dB | `aster_acoustic_export` | effectieve waarde, zoals een geluidsmeter; Code-Aster's DB is 3,01 dB hoger | - | AH-01, AH-04 |

### 3.14 Vibro-akoestiek (`vibroacoustic_modes_3d`, `3D_FLUIDE` + `FLUI_STRU` + `CALC_MODES` `BANDE`)

| Instelling | Standaard | Wat het doet | Waarom | Aanpassen als | Bewijs |
|---|---|---|---|---|---|
| `modal_modes` | 10 | aantal modes als het Mecway-model geen `maxmode` heeft | Keuze (als modaal) | - | - |
| `vibro_freq_min` | 0,1 Hz | ondergrens van de band: de eerste modes erboven (`INFO_MODE` zoekt de bovengrens, `CALC_MODES OPTION='BANDE'`) | `U_P_PHI` geeft een valse mode bij 0 Hz per vrijheidsgraad φ (gemeten); `PLUS_PETITE` stopt met `ALGELINE3_81`. 0,1 Hz ligt ruim boven de numerieke nul (~1e-5 Hz) en onder gewone constructiemodes | modes vanaf een frequentie (bromtoon, toerental); heel slappe constructie: lager (> 0) | VA-01…05 (alle gevraagde modes, in volgorde); VA-05c (100 Hz) |
| `modal_tolerance` | 1e-6 | `VERI_MODE SEUIL` | als §3.7 | `ALGELINE5_15` (gezien met hex8-lucht, fout net boven 1e-6): 1e-5 | VA-03 |
| `solver_nprec`, `time_limit`, `memory_limit` | 8, 900, 2048 | zie §3.1 | | | |
| (vast) formulering | `FORMULATION='U_P_PHI'` | onbekenden u, p, φ; symmetrische matrices | CA-standaard (catalogus `affe_modele.py`); `U_P` gaf een verkeerde reeks / `JEVEUX_26`, `U_PSI` kent `DDL_IMPO PRES` niet (gemeten) | - | VA-01…05 |
| (vast) normering | gegeneraliseerde massa 1 (`NORM_MODE MASS_GENE` na het filteren) | modes met f < `vibro_freq_min` of massa ≤ 0 vallen weg (INFO) | een valse mode met massa < 0 gaf bij normeren `DVP_2` (gemeten) | - | VA-01: p/u op de zuiger analytisch op 2e-6 |
| (vast) fluïdum | onderdeel met *Speed of sound* zonder Young's modulus, of naam `LUCHT_`/`VLOEISTOF_`/`FLUID_` | `3D_FLUIDE`, materiaal `FLUIDE` (`RHO`, `CELE_R`) | Mecway's akoestische materiaal (A30) | - | VA-01…05 |
| (vast) koppelvlak | automatisch (gedeelde vlakken met volume- of schaalelementen van de constructie); `KOPPEL_`/`COUPLING_`-vlakselecties: alleen die | `FLUI_STRU`, normaal uit het fluïdum (`ORIE_PEAU`) | testcases adlv100a/b | - | VA-01 (automatisch), VA-01k (`KOPPEL_`), VA-03/05 (schaal) |
| (vast) p = 0 | `OPEN_`-selecties (knopen of vlakken) en *fluid pressure* = 0 | `DDL_IMPO PRES=0, PHI=0` | adlv100a/adlv100p | - | VA-01 |

### 3.15 Harmonische respons (`harmonic_3d`, `DYNA_VIBRA` `HARM`)

| Instelling | Standaard | Wat het doet | Waarom | Aanpassen als | Bewijs |
|---|---|---|---|---|---|
| `harm_basis` | `GENE` | `GENE`: `CALC_MODES` → `PROJ_BASE` → `DYNA_VIBRA` `BASE_CALCUL='GENE'` → `REST_GENE_PHYS`; `PHYS`: `DYNA_VIBRA` `BASE_CALCUL='PHYS'` op het hele model | Keuze: modaal is snel en kent modale demping; `PHYS` als controle of met dempers | controle van GENE, een model met dempers, of veel frequenties boven de modes | HR-01a/b (GENE), HR-01c/d, HR-02b, HR-03b (PHYS) |
| `harm_freq_start`, `harm_freq_end` | 1, 100 Hz | bereik van de frequenties | Keuze: een gangbaar bereik voor constructies | het bereik van de vraag; de hoogste gerekende mode hoort er ruim boven te liggen (WARNING als hij eronder ligt) | HR-01, HR-02, HR-03 |
| `harm_freq_count` | 100 | aantal frequenties van start tot eind | Keuze: rekentijd lineair in het aantal (GENE goedkoop) | fijner of grover verloop tussen de pieken | - |
| `harm_freq_spacing` | `lin` | `lin` gelijke stappen, `log` gelijke verhoudingen | Keuze | breed bereik: `log` | - |
| `harm_freq_list` | `0` | eigen lijst (tekst, komma's, ≥ 0 Hz); `0` = het bereik; geen verfijning | Keuze | vaste frequenties (toerentallen) | HR-01d, HR-04 (`#ASTER-OPTIE`) |
| `harm_refine_points` | 5 | per mode in het bereik zoveel extra frequenties over de halfwaardebreedte 2ξf rond de piek f√(1−2ξ²) (`DEFI_LIST_FREQ` `RAFFINEMENT` `CRITERE='LARGEUR_3DB'`); alleen modes met 0 < ξ < 0,5 | CA: `NB_POINTS` standaard 5 (catalogus `defi_list_freq.py`); zonder verfijning valt een smalle piek tussen twee punten | 0 = alleen het bereik; meer punten voor een gladde piek | HR-01a (piek −0,00%, piekfrequentie exact) |
| `modal_damping` | 0 | extra ζ op alle modes in `AMOR_REDUIT` (alleen GENE; PHYS: ERROR) | Keuze: Mecway kent alleen Rayleigh | een dempingsverhouding uit een norm | HR-01a, HR-04 |
| `loss_factor` | 0 | verliesfactor η van alle materialen: `AMOR_HYST`, stijfheid `RIGI_MECA_HYST` = K(1 + iη) (GENE en PHYS); per materiaal `#ASTER-HYST` | Keuze: Mecway kent geen verliesfactor | structurele demping (staal 0,001–0,01, rubber 0,1–0,5) | HR-06a..d (piek u_st/η exact) |
| `static_correction` | aan | statische verrijking van de basis: `MACRO_ELAS_MULT` per last + `DEFI_BASE_MODALE` `RITZ` (`ORTHO`), eigenprobleem op die basis (`CALC_MODES` QZ) | CA: `DYNA_LINE` `ENRI_STAT='OUI'` is de standaard (catalogus `dyna_line.py`, `dyna_line_ops.py`); gemeten: zonder verrijking mist 6,2e-4 × u_st en wordt de fout groot waar de respons klein is | uit om de modale truncatie te zien | HR-02a (met: 6,6e-4 t.o.v. Euler-Bernoulli), HR-02c (zonder: statisch deel 6,22e-4 = 1 − Σ12/λ⁴) |
| `fields` | `displacements`, `accelerations`, `stresses`, `vonmises` | per frequentie Re, Im, amplitude, fase; ω²\|U\|; complexe `SIGM_NOEU` (volumes) | de grootheden van een frequentierespons | kleinere `.liml`; `velocities` voor ω\|U\| | HR-01a (versnelling), HR-03 (spanning) |
| `modal_modes`, `modal_tolerance`, `solver_nprec`, `time_limit`, `memory_limit` | 10, 1e-6, 8, 1800, 2048 | als §3.7 en §3.1 | | | |
| (vast) tijdsafhankelijkheid | last F·e^{iφ}·e^{iωt}, u(t) = Re(U e^{iωt}); fase = arg U, negatief = naijlen | `EXCIT` `COEF_MULT=1`, `PHAS_DEG` = `#ASTER-FASE` | gemeten (prototype, HR-01): U = F/(k − mω² + iωc) | - | HR-01, HR-04 |
| (vast) Mecway-tabel van een last | kolom *time* = frequentie [Hz], waarde = amplitude | `DEFI_FONCTION` `NOM_PARA='FREQ'` als `FONC_MULT` | Keuze: Mecway kent geen frequentietabel | - | HR-04 |
| (vast) von Mises | grootste waarde over een periode | uit de complexe knoopspanning, exact (`aster_harmonic_export`) | Keuze: de von Mises van Re of \|σ_ij\| is niet het maximum in de tijd | - | HR-03a (GENE = PHYS 4e-5) |

### 3.16 Vibro-akoestiek harmonisch (`vibroacoustic_harm_3d`, `3D_FLUIDE` + `FLUI_STRU` + `3D_FLUI_ABSO` + `DYNA_VIBRA` `HARM` `PHYS`)

| Instelling | Standaard | Wat het doet | Waarom | Aanpassen als | Bewijs |
|---|---|---|---|---|---|
| `harm_freq_start`, `harm_freq_end` | 20, 500 Hz | bereik van de frequenties (`DEFI_LIST_REEL` → `LIST_FREQ`) | Keuze: het gebied waar constructies geluid afstralen; de eindfrequentie bepaalt de mesh-fijnheid van het fluïdum (WARNING onder 10 lineaire / 5 kwadratische elementen per golflengte) | het bereik van de vraag | VH-02…06 |
| `harm_freq_count` | 50 | aantal frequenties van start tot eind | Keuze: één factorisatie per frequentie (direct), rekentijd lineair in het aantal | resonantiepieken: stap kleiner dan de piekbreedte (§7.4 van [Akoestiek.md](Akoestiek.md)) | - |
| `harm_freq_spacing` | `lin` | `lin` gelijke stappen, `log` gelijke verhoudingen | Keuze | breed bereik: `log` | - |
| `harm_freq_list` | `0` | eigen lijst (tekst, komma's, > 0 Hz); `0` = het bereik | Keuze | vaste frequenties; fijn rond een gekoppelde mode (`vibroacoustic_modes_3d`) | VH-01…08 (lijst), VH-07 (`#ASTER-OPTIE`) |
| `source_velocity` | 0,001 m/s | normaalsnelheid van de `BRON_`-vlakken, de fluid in, fase 0 (`VITE_FACE VNOR`, `EXCIT COEF_MULT=−1`) | Keuze, als §3.13; gemeten: met `COEF_MULT=+1` geeft `VITE_FACE` in `U_P_PHI` p = −ρcv (ahlv100b: `VNOR` naar buiten) | de werkelijke amplitude; per vlak: `#ASTER-BRON` | VH-01b (ahlv100b ≤ 2,3e-7), VH-07 |
| `incident_pressure` | 1 Pa | amplitude van de vlakke golf die door de `INVALLEND_`-vlakken het fluïdum in loopt (`ONDE_FLUI PRES` = 2 × de waarde) | Keuze: 1 Pa (91 dB) als eenheid, alles is lineair; gemeten: `ONDE_FLUI` met `PRES` geeft een binnenlopende golf `PRES`/2 en laat teruggekaatste golven door | de werkelijke amplitude; per vlak: `#ASTER-BRON selectie = p Pa [, fase]` | VH-01 (ahlv101a ≤ 1,3e-7), VH-05, VH-05b, VH-08 |
| `fields` | `displacements`, `accelerations`, `stresses`, `vonmises` | als §3.15 voor de constructie; de druk (`pressure`, `pressurei`, `pressuremag`, `pressurephase`, `spl`) gaat altijd mee | de grootheden van een frequentierespons | kleinere `.liml` | VH-02 (spanning op de zuiger) |
| `solver_nprec`, `time_limit`, `memory_limit` | 8, 1800, 2048 | zie §3.1 | | | |
| (vast) berekening | direct: `DYNA_VIBRA` `BASE_CALCUL='PHYS'` met `MATR_IMPE_PHI` | geen modale basis | `U_P_PHI` heeft valse modes bij 0 Hz (§3.14) en de absorptie is niet proportioneel; ahlv101a/ahlv100b rekenen zo | - | VH-01…08 |
| (vast) absorberende rand | `ABSORBEREND_`: `3D_FLUI_ABSO` met ρc van het fluïdum; Mecway *impedance* (reëel): eigen materiaal `CELE_R = Z/ρ` (`IMPE_MECA`) | | gemeten: Z = ρ·c_vlak | - | VH-01/02 (ρc), VH-03 (Z = 2ρc ≤ 1,2e-4) |
| (vast) demping van de constructie | Mecway *Rayleigh damping*: C = α·M_s + β·K_s met de matrices van alleen de constructie-groepen; dempers `AMOR_MECA` (`AMOR_FLUI='NON'`); `DYNA_VIBRA AMOR_FLUI='NON'` | | Keuze: het fluïdum dempt via de randen, niet via Rayleigh; `AMOR_FLUI='NON'` zoals `DYNA_LINE` | - | VH-04 (α), VH-04b (β), VH-04c (demper) |
| (vast) bronnen | `EXCIT` `PUIS_PULS=1`, `PHAS_DEG` = 90 + fase (iω × de vector); belastingen op de constructie als §3.15 | | ahlv101a, ahlv100b | - | VH-01…08 |
| (vast) SPL, microfoons, meetpunten | als §3.13 (SPL op de effectieve waarde) en §3.15 (meetpunten) | `aster_harmonic_export` met `pressure=True` | | - | VH-01, VH-02 |

### 3.17 Vaste waarden in de modules (zonder instelling)

Aanvulling op §3.9: waarden die in de code vastliggen en de uitkomst of de meldingen
bepalen. Bron is de code (module tussen haakjes); waar niets staat bij *Waarom* is het
een Keuze van de bridge die niet apart gemeten is.

| Onderwerp | Waarde in de bridge | Effect | Waarom / bewijs |
|---|---|---|---|
| Oudere `bridge_utils.py` zonder een sleutel | de modules vallen terug op `harm_freq_start`/`_end`/`_count` = 0 / 0 / 1 (akoestiek en harmonisch: ERROR over het bereik), `fields` = alleen `displacements` (harmonisch, respons op modale basis, spectrum, vibro-akoestiek), `error_estimator` uit (`bridge_adapt`) | alleen als de sleutel in `CONFIG_BRIDGE` ontbreekt | zet de sleutel terug (het startscherm toont hem dan weer) |
| Adaptief: groei vooraf (`bridge_adapt._GROWTH`) | 40 nieuwe elementen per verfijnd element in de eerste lus, daarna de gemeten groei van de vorige lus | schatting voor `adapt_max_elements` (telt alle elementen van het model, ook schalen en balken) | gemeten (headless Mecway 33): 19 per element bij hex8, 38 tot 70 bij hex20 |
| Adaptief: slecht element (`BAD_ELEMENT`) | WARNING bij een geschaalde Jacobiaan < 0,1 (alleen hex) | melding, geen ingreep | grof plaatmodel 0,71, slechte overgangen 0,002 tot 0,02 |
| Adaptief: stoppen | doel gehaald (`rel ≤ adapt_target_error`), de globale fout daalt niet meer (geen tolerantie; WARNING), of `adapt_max_loops` verfijningen (5 = 5 verfijningen, 6 runs) | einde van de lus | - |
| Adaptief: keuze bij gelijke fout | lager elementnummer eerst; `fraction`: ⌈f·n⌉ elementen (minstens 1); `factor`: η > factor × gemiddelde (strikt) | welke elementen verfijnd worden | - |
| `#ASTER-LASBRON` zonder sleutel (`bridge_welding`) | `eta` 1; `diepte` (0, 0, −1) (de warmte gaat in −Z); `t0` 0 s; `ff` = 2·af/(af+ar), `fr` = 2·ar/(af+ar) (WARNING als ff + fr ≠ 2); baan zonder `lengte`: v × (`t1` of de eindtijd − `t0`); `groep`: de `LASNAAD_`-selecties, anders automatisch (`CUTOFF`); `geboorte` uit; `voorloop` 2 × af | vermogen, richting en plaats van de bron | Goldak (dubbel-ellipsoïde, continu op het grensvlak bij deze ff/fr); [Lassen.md](Lassen.md) |
| Keten thermisch → mechanisch: lijnzoeken (`bridge_thermomech`) | `RECH_LINEAIRE ITER_LINE_MAXI=5` als er plasticiteit is | convergentie | gemeten: WE-10b (hex20, `LINE_QUAD`) divergeerde zonder; met 9 tot 10 iteraties per stap |
| Keten met toevoegmateriaal: `NEWTON PREDICTION` | `'TANGENTE'`; in de stap direct na een geboorte `'ELASTIQUE'` (spanning en interne variabelen van de nieuwe elementen op 0) | convergentie bij de geboorte | Keuze (zoals na bezwijken) |
| Keten met `LINE_QUAD` | temperatuur naar het kwadratische mesh met `PROJ_CHAMP METHODE='COLLOCATION'` (middenknopen lineair tussen de hoekknopen) | thermische rek op de middenknopen | zoals het lineaire element |
| Keten: bilineair materiaal | ET uit Mecway's tangentmodulus via H = E·ET/(E − ET) met E bij de eerste tabeltemperatuur, dan ET(T) = E(T)·H/(E(T) + H); zonder *Thermal expansion* α = 0 (WARNING) | versteviging en thermische rek bij temperatuurafhankelijke E | - |
| Metallurgie: dataset 16MND5 (`bridge_metallurgy.DATASETS`) | AR3 830, MS0 415, AC1 724, AC3 846 °C; ALPHA −0,0249; TAUX_1 = TAUX_3 = 0,34 s; `TEMP_MS` (0,38; −30,791; 11,698; −1,0); hardheid F/P/B/M/A 184/184/309/450/100 HV; korrel 11 (`DREF` 11) | fasen en hardheid | testcase mtlp103a, getrouw overgenomen |
| Metallurgie: dataset HSNV101A | AR3 830, MS0 200, AC1 724, AC3 846 °C; ALPHA −0,03; TAUX 0,34 s; korrel 10; met `mechanica=ja` ALPHA_F 15·10⁻⁶, ALPHA_A 23,5·10⁻⁶ /K, DEPS 2,52·10⁻³, REF `CHAUD` en de vloeigrenzen van de testcase | fictief staal van testcase hsnv101a | MT-01 |
| Metallurgie: zonder opgave | eigen `trc=` zonder `korrel`: korrel 0; `REF` zonder opgave of dataset: `CHAUD` als `begin` > 50 % austeniet, anders `FROID`; helling per fase zonder `ET_`/`H_`, dataset of Mecway-helling: 0 (ideaal plastisch) | fasen, transformatierek, versteviging | - |
| Metallurgie: meldingen | WTZ = knopen met > 1 % austeniet, volledig = > 99 %; WARNING als op de laatste tijd nog > 1 % austeniet is | alleen het verslag | - |
| Breukmechanica: vorm van het front (`bridge_fracture.front_shape`) | recht of cirkel als alle punten binnen 1 % van de grootste afmeting van het front liggen; `FORM_FISS='CERCLE'` alleen als de meerderheid van de lipknopen binnen de cirkel ligt (< 0,999 R) | krommingscorrectie van K | forma07a (zie §4.12) |
| Breukmechanica en XFEM: controle | WARNING als K_I van `CALC_G` en `POST_K1_K2_K3` op de binnenpunten van het front meer dan 5 % verschillen (t.o.v. de grootste \|K_I\|: `CALC_G` bij een gemeshte scheur, `POST_K1_K2_K3` bij XFEM) | melding | - |
| XFEM: mesh | WARNING als de elementen aan het front groter zijn dan de scheurmaat / 10 (kleinste halve as of straal) | melding | BR-08 ([Breukmechanica.md](Breukmechanica.md) §7.4) |
| XFEM: `POST_K1_K2_K3` | `ABSC_CURV_MAXI` = R_SUP als `fracture_r_sup` (of `rsup=`) gegeven is | bereik langs de lippen | testcase forma07b |
| Harmonisch: tabel van een last | lineair tussen de punten (Hz), buiten de tabel constant (`PROL_GAUCHE`/`PROL_DROITE='CONSTANT'`) | amplitude buiten het tabelbereik | - |
| Harmonisch: fase | `#ASTER-FASE` in graden; zonder: 0 | fase van de last | - |
| Harmonisch (GENE): pseudo-modes | de vectoren van de statische verrijking krijgen dezelfde demping ξ = ½(α/ω + β·ω) + ζ op hun frequentie | demping van het quasi-statische deel | - |
| Harmonisch: overkritische demping | geen controle op ξ ≥ 1 (in het frequentiedomein rekenbaar); respons op modale basis en spectrum stoppen dan met een ERROR | - | - |
| Harmonisch: grootheden per knoop | `displmag` = √(\|Ux\|² + \|Uy\|² + \|Uz\|²): een bovengrens van max \|u(t)\| (gelijk als de componenten in fase zijn); een meetpunt of microfoon met meer knopen: amplitude = RMS van \|U\| over de knopen, fase = arg van het gemiddelde | interpretatie | - |
| Harmonisch: precisie | float32 in de `.liml` (zoals dynamica, §3.9) | afronding ≤ 6·10⁻⁸ relatief (2⁻²⁴) | - |
| Respons op modale basis | `steps_per_period` minimaal 4 (ook op het startscherm); `NEWMARK` met de Code-Aster-standaard β = 1/4, γ = 1/2 (gemiddelde versnelling); ERROR bij ξ ≥ 1 of een mode met f ≤ 0; uitvoertijden moeten veelvouden van Mecway's tijdstap zijn (tolerantie 10⁻⁶ × stap), anders ERROR | - | MD-01 |
| Spectrum: invoer | ordinaten zonder teken (\|S_a\|), een getal = een vlak spectrum; meer gravities per richting opgeteld op alle abscissen samen (lineair, buiten de tabel constant) | spectrumwaarde | zoals Mecway een tabel en een getal optelt |
| Spectrum: missing mass in de eigen reactie en von Mises | spectrumwaarde bij `FREQ_COUP` met de demping van de hoogste gerekende mode | reactie en von Mises van de pseudo-mode | - |
| Spectrum: uitvoer | `REAC_NODA` zonder de veren van *elastic support* (`BRES*`, zoals statisch: de veerkracht is de reactie); spanningen alleen op volume-elementen; WARNING als de effectieve massa < 90 % is zonder missing mass | - | - |
| Complexe modes: zoekfrequentie (`bridge_modal_damping`) | `modal_shift_hz` ≠ 0, ook negatief: `OPTION='CENTRE'` rond die frequentie (anders dan bij reële modes, §3.7) | welke modes gevonden worden | NIET geverifieerd met een negatieve waarde |
| Akoestiek: zoekfrequentie zonder drukknoop | −0,1·c_min/(2D) (§3.11); is D = 0: −1 Hz | rekenbaar bij harde wanden | - |
| Akoestiek: complexe modes (`aster_acoustic_complex`) | dicht opgelost (`scipy.linalg.eig`) als 2n ≤ 300 (n = vrije drukvrijheidsgraden), anders shift-invert ARPACK; 2·maxmode + 8 kandidaten, tot 3 keer verdubbeld | - | AI-01…10 |
| Akoestiek: microfoon met meer knopen | amplitude = RMS van \|P\| over de knopen, fase = arg van het gemiddelde | CSV en log | - |
| Akoestiek: gelijke dichtheid | relatieve tolerantie 10⁻⁶; daarboven verschillende media (ERROR) | - | - |
| Akoestiek: bron op een selectie | `#ASTER-BRON` op een `BRON_`-selectie vervangt de standaardsnelheid | - | - |
| Fluïdum buiten een vibro-akoestische analyse | rekent als vaste stof met E = 210 GPa (WARNING; Mecway rekent met E = 0) | - | - |
| Vibro-akoestiek modes: band | `INFO_MODE` vanaf `vibro_freq_min`: bovengrens max(10·f_min, 1 Hz), × 4 tot er genoeg modes zijn (tot 10⁷ Hz), dan twee keer geometrisch gehalveerd; `CALC_MODES` `BANDE` met `COEF_DIM_ESPACE=4` | welke band gerekend wordt | VA-01…05 |
| Cyclisch: knoopparen (`bridge_cyclic`) | master- en slaveknoop gekoppeld binnen 10⁻⁵ × de grootste coördinaat, anders ERROR | - | CY-01..06 |
| Cyclisch: hele wiel (`aster_cyclic`) | knopen gekoppeld binnen 10⁻⁶ × de grootste coördinaat; de frequenties op het skelet moeten binnen 10⁻⁹ (relatief) gelijk zijn aan die van de sector, anders gaat alleen de sector naar Mecway | - | CY-01..06 |
| Cyclisch: zoekfrequentie en normering | negatief: genegeerd (INFO; de sector met vaste snijvlakken heeft geen starre modes); `modal_norm` anders dan `MASS_GENE` geldt alleen voor de sectorbasis (INFO) | - | - |

---

## 4. Aannames van de vertaling

Status: **geverifieerd** (met test of bron), **bron** (alleen documentatie), **NIET
geverifieerd**, of **afwijking** (bewust anders dan Mecway).

### 4.1 Eenheden en invoer

| Aanname | Wat de bridge doet | Status |
|---|---|---|
| Alles in SI | elke Mecway-waarde met eenheid (`"210 GPa"`, `"10000 mm⁴"`) wordt omgerekend (`parse_and_convert`); een onbekende eenheid komt ongewijzigd terug met een WARNING | geverifieerd: alle verificatiemodellen gebruiken eenheden als MPa en mm (Verificatie, alle groepen) |
| Formules in t | bemonsterd tot een tijdstabel (zoals Mecway voor CCX) | bron: Mecway-handleiding (Mecway, 2026) hoofdstuk 9; KNOWN_BUGS 104 |
| Formules in x, y, z (mechanisch) | `FORMULE` van X, Y, Z (en `INST`) in `AFFE_CHAR_MECA_F` voor druk, traction, kracht, line pressure en opgelegde verplaatsing/rotatie; x, y, z in de positionunit, beginpositie | geverifieerd: LS-40..44, NL-40; druk en traction gelijk aan Mecway 34; afwijking: kracht, line pressure en verplaatsing/rotatie met x, y, z legt Mecway 34 niet op (KNOWN_BUGS 104) |
| Tijdsafhankelijke last in lineair statisch | waarde op de eindtijd (ook t in een formule in x, y, z) | afwijking: Mecway intern negeert t, CCX neemt f(0) (KNOWN_BUGS 104) |
| Niet-lineair statisch: Mecway's `stepsize` | rekenstappen dt, 2 dt, ... tot de periode plus de knikken van de lasttabellen; met *Automatic time stepping* `METHODE='AUTO'` tussen die punten (`auto_time_stepping`) | uitvoertijden = Mecway's stappen (NL-20), plus een tijdstip op een knik tussen twee stappen |

### 4.2 Materiaal

| Aanname | Wat de bridge doet | Status |
|---|---|---|
| Bilineaire plasticiteit: Mecway's *tangent modulus* = plastische modulus H | `ECRO_LINE D_SIGM_EPSI` = E·H/(E+H) (helling in totale rek) | geverifieerd: NL-01 exact; Mecway/CCX headless 434,0 MPa (referentie 433,5) |
| Hardingscurve: de rek is de **totale** rek | `auto`: eerste punt (0, 0) of eerste rek > 0 → totale rek (zoals Mecway; (0, 0) vervalt); eerste punt (0, σ > 0) → plastische rek, met een WARNING dat Mecway dezelfde curve als totale rek leest | geverifieerd bij deze review (Mecway/CCX headless, staaf van NL-01, R-CURVE): curve (0, 0), (σy/E, σy), (0,1, …) gaf 430,6 MPa en p = 0,00792 op t = 2 (referentie 433,5 MPa / 0,00788), dus totale rek. Een curve die met (0, σy) begint, gaf in Mecway een onfysische uitkomst (13,5 MPa bij 0,1 % rek); de bridge leest die als plastische rek. Bridge met `auto`: curve met of zonder (0, 0) en curve (0, 355 MPa) als plastische rek alle drie exact tot t = 3 (R-CURVE) |
| Hardingscurve in totale rek: E = helling van het eerste stuk (Mecway: de eerste twee punten bepalen het elastische gebied) | E = helling oorsprong → eerste punt, ook als *Young's modulus* op het tabblad *Elastic* anders is (WARNING met beide waarden), voor isotroop en kinematisch en in alle analyses van het model; niet bij een curve als plastische rek of OpenRadioss `PLAS_TAB`. Wijkt de helling tot het eerste `TRACTION`-punt daarna nog > 1 % af van E, dan ERROR (Code-Aster stopt anders met `MATERIAL1_5`) | gemeten (Mecway/CCX headless): E-tabblad 200 GPa, curve met helling 210 GPa gaf 104,97 MPa bij rek 5·10⁻⁴ (niet-lineair) en 105,00 MPa (lineair, CCX), dus 210 GPa; geverifieerd: NL-04, NL-04b exact. Curve zonder (0, 0), (0,001; 210 MPa), (0,011; 310 MPa): 104,98 MPa (niet-lineair) en 105,00 MPa (lineair, CCX), dus ook de helling oorsprong → eerste punt (NL-04c exact) |
| Hyperelastisch (Neo Hooke, Mooney-Rivlin) | `ELAS_HYPER` (C10, C01, K = 2/D1, RHO), `GREEN_LAGRANGE`; alleen volume-elementen in niet-lineair statisch en dynamisch; D1 = 0 en lineaire analyses: ERROR; thermische uitzetting genegeerd (WARNING) | geverifieerd: NL-50..53 (kubus trek/druk, binnen 0,11 %; expliciet 0,7 %), gelijk aan Mecway/CCX headless |
| Plasticiteit | von Mises: `VMIS_ISOT_TRAC`/`_LINE`, `VMIS_CINE_LINE`; Ramberg-Osgood bemonsterd | geverifieerd (NL-01, officiële tests ssnp15a, hsnv100g); KNOWN_BUGS 6, 34 |
| Plasticiteit op balken | elastisch gerekend (WARNING) | afwijking: Code-Aster alleen in multivezelbalken (`POUTRE0_61`) |
| Thermische rek | knoopveld `TEMP` (`AFFE_VARC`), in het element geïnterpoleerd; *Temperature* per selectie en *Node temperature* (`temperature3`, ook na *Transfer temperatures from solution*) per knoop; knopen zonder temperatuur op de referentie van de *Thermal stress*; knopen die de bridge toevoegt (`LINE_QUAD`, middenknoop `COQUE_3D`) krijgen de geïnterpoleerde temperatuur | geverifieerd: TH-03 en LS-08a/c exact, LS-08b/d (lineair over de dikte) exact en gelijk aan Mecway 34, dat ook interpoleert (de manual noemt het elementgemiddelde, KNOWN_BUGS 17); L30/D31: `EVOL_THER` vanaf de referentie, tijdstabel gevolgd (NL-70..75, DY-70..72); D30 negeert temperaturen zoals Mecway |

### 4.3 Randvoorwaarden en lasten

| Aanname | Wat de bridge doet | Status |
|---|---|---|
| Pinned support = gemiddelde verplaatsing nul | `LIAISON_DDL` Σ wᵢuᵢ = 0 per richting (gewicht per knoop of per vlakoppervlak) | bron: Mecway (2026) §9.3; NIET in een verificatietest (LS-03 gebruikt `displacement`) |
| Druk positief naar het element toe | `PRES_REP` met `PRES` > 0 = drukkend | bron: Mecway (2026) §9.14; geverifieerd: LS-03, LS-04, LS-05 |
| Uniforme druk is meebewegend bij grote verplaatsingen | `TYPE_CHARGE='SUIV'` op volumes en `COQUE_3D`; op DKT vast (WARNING, `CALCUL_42`) | bron: Mecway (2026) §9.14; Code-Aster-test ssnv122a (Verificatie, officiële tests) |
| Overlappende randvoorwaarden | deels opgelost (`SANS_GROUP_*`; een scheve relatie of DDL_IMPO 0 die de ander al dekt wordt gereduceerd), anders gemeld | afwijking: Mecway reduceert zelf (KNOWN_BUGS 8) |
| Voorwaarde op een elementselectie of component met een flexible joint | werkt op de cellen (`GROUP_MA`), dus op de eigen knoop van de joint; een dubbele voorwaarde kan `FACTOR_11` geven (WARNING) | afwijking: Mecway legt hem op de knopen van het element; zet hem op knopen of vlakken (KNOWN_BUGS 106) |
| Veren en dempers langs hun eigen as | `DISCRET` met `REPERE='LOCAL'` | bron: Mecway (2026) §7.7 ("stiffness only in the direction of its length"); geverifieerd: LS-06 exact; vergelijking met een Mecway-oplossing ontbreekt (KNOWN_BUGS 47) |
| Compression only | `LIAISON_UNIL` (hard) | KNOWN_BUGS 22 |
| Rayleigh-demping | alleen op het hele model (`AMOR_ALPHA`/`AMOR_BETA` per materiaal) | KNOWN_BUGS 27 |

### 4.4 Elementen

| Aanname | Wat de bridge doet | Status |
|---|---|---|
| Hex8 | `3D` zonder incompatibele modes; Mecway gebruikt die wel (Mecway, 2026, §7.3) | afwijking, gemeten: LS-02 (te stijf bij weinig elementen); KNOWN_BUGS 1 |
| `LINE_QUAD` | Code-Aster maakt hex8 → hex20; resultaten alleen op de hoekknopen; knoopkrachten blijven op de hoekknopen | geverifieerd: LS-02-lq = hex20; puntlasten geven lokale vervorming (KNOWN_BUGS 1) |
| Schalen | DKT ~0,7 % anders dan Mecway, `COQUE_3D` via QUAD9/TRIA7 | gemeten (KNOWN_BUGS 2); LS-03, LS-05 |
| Thermische schalen | `PLAN` (diepte 1) met factor f = t / t_ref op λ, ρc en de belastingen | geverifieerd: TH-01e (6e-7); KNOWN_BUGS 15 |
| Trusses | `BARRE`, geometrisch lineair (ook met `GROT_GDEP`) | gemeten (KNOWN_BUGS 40) |
| Line3-balken | twee rechte `SEG2`-cellen per element; gekromd (middenknoop naast de koorde): een knik in de middenknoop (WARNING) | recht exact (LS-50); gekromd afwijking: Mecway (CCX) rekent de kromme vorm (KNOWN_BUGS 107) |
| Thermische rek in schalen | vrije uitzetting αΔT·L zoals de theorie | gemeten op een plaat: bridge +3% (DKT) en +2% (`COQUE_3D`), Mecway −22% (quad4) en −44% (quad8); de bridge volgt de theorie, waarom Mecway minder uitzet is NIET nagegaan (KNOWN_BUGS 95) |
| Expliciet met DKT-schalen | geen `INER_ROTA` in `AFFE_CARA_ELEM` | gemeten bij deze review (R-STRIP): uitkragende strook DKT, expliciet en impliciet gelijk, periode +0,6 % / +0,3 %, piek 1,957 × statisch (verwacht ~1,966) |

### 4.5 Kinematica (`deformation`)

| Aanname | Wat de bridge doet | Status |
|---|---|---|
| Mecway's niet-lineaire analyse is geometrisch niet-lineair | standaard `GROT_GDEP` | bron: Mecway (2026) §6.2.1 (alleen CCX); gemeten: een plastische staaf was met `PETIT` 14 % te stijf, met grote verplaatsingen +1 % t.o.v. Mecway (eerdere run, model niet in de repository) |
| Vorm per element | volume elastisch `GREEN_LAGRANGE` (of `GDEF_LOG`), volume plastisch `GDEF_LOG` (of `SIMO_MIEHE`, niet met `VMIS_CINE_LINE`), DKT/DST `GREEN_LAGRANGE` (gaf dezelfde uitkomst als `PETIT`; met `VMIS_CINE_LINE` `PETIT`), `COQUE_3D` `GROT_GDEP`, balken `PETIT` (`POU_D_T_GD`: `GROT_GDEP` met `ELAS_POUTRE_GR`), kabels `GROT_GDEP`, discreten `PETIT` | gemeten met runs op een gemengd model (`bridge_to_aster._deformation_for`); NL-02a (volume) en NL-02b (`COQUE_3D`) exact; grote verplaatsingen van DKT en van balken `POU_D_E`/`POU_D_T`: NIET mogelijk (KNOWN_BUGS 11), balken `POU_D_T_GD`: NL-80–89; discreten met grote verplaatsingen: NIET geverifieerd |
| Dynamica volgt de statische keuze | `GROT_GDEP` ook in `dyna_*` | Keuze, NIET tegen Mecway geverifieerd; DY-03: verschil met lineaire theorie 1,4e-4…6,9e-4 (fysisch) |
| Opgelegde rotaties en starre koppelingen | blijven kleine rotaties; WARNING boven ~6° (op knopen van `POU_D_T_GD`: de totale rotatievector, WARNING over de convergentie) | KNOWN_BUGS 11 |
| Starre arm van een element offset | `LIAISON_DDL` in de onvervormde assen: kleine rotaties, ook met `GROT_GDEP` (WARNING bij verschoven schalen) | KNOWN_BUGS 108 |

### 4.6 Contact

| Aanname | Wat de bridge doet | Status |
|---|---|---|
| Mecway-contact is penalty met een normaalstijfheid per oppervlak | standaard Lagrange (`STANDARD`, geen penetratie); `PENALISATION` gebruikt Mecway's stijfheid als `COEF_PENA_CONT` | afwijking bij `STANDARD` (KNOWN_BUGS 43); `PENALISATION` geverifieerd: penetratie p/kn exact (NL-03d/f), lijncontact exact (NL-03b) |
| Lijncontact met `STANDARD` | faalt op hex20 (`MECANONLINE9_4`, `LAGS_C`) | NL-03a; met `solver_nprec` -1 rekent het door, maar contactkracht −1,6 % en tip +2,8 % (R-NPREC-CONTACT): gebruik `PENALISATION` |
| Vastgezette slave-knopen | uitgesloten met `SANS_GROUP_NO` | bron: EDF R&D (U4.44.11, U2.04.04 §2.3.4) |
| Zones met gedeelde slave-knopen | samengevoegd, grootste wrijvingscoëfficiënt | KNOWN_BUGS 10 |
| Verlijmd contact | star (`LIAISON_MAIL`); de stijfheid van `bondedelastic` vervalt | KNOWN_BUGS 21 |

### 4.7 Dynamica

| Aanname | Wat de bridge doet | Status |
|---|---|---|
| Beginversnelling | Code-Aster rekent a₀ = M⁻¹F(0) | gemeten (Verificatie, DY) |
| HHT, eerste stap | Code-Aster gebruikt F₀ = 0 in de term −αF₀ | gemeten: DY-01a piek −0,44 % (Verificatie, DY) |
| Opgelegde beweging expliciet | omgezet naar de versnelling die het schema oplegt (`FORMULATION='ACCELERATION'`) | geverifieerd: DY-03b exact; frictionless (`FACE_IMPO` DY-20a, `LIAISON_OBLIQUE` DY-20c) en constraint equation met constante ≠ 0 (DY-20b, C in de eerste rekenstap) ook omgezet; TCHAMWA met een variabele stap: KNOWN_BUGS 41 |
| Massa | impliciet consistent, expliciet diagonaal (`MASS_DIAG='OUI'`) | DY-02, DY-03 |
| Kritieke stap | schatting kleinste ribbe / c; Code-Aster controleert zelf | gemeten (§3.5, R-DT) |
| Respons op modale basis (D30) | Rayleigh als modale ξ_i = α/(2ω_i) + β·ω_i/2; geen voorspanning door de belastingen; geen statische correctie (standaard); last zonder tabel = staplast vanaf t = 0 | geverifieerd tegen Mecway headless en analytisch: MD-01..07 ([Respons_op_modale_basis.md](Respons_op_modale_basis.md)) |
| Harmonische respons (`harmonic_3d`) | Rayleigh als modale ξ_i (GENE) of C = αM + βK (PHYS); de belastingen zijn de amplitude (geen voorspanning); statische verrijking van de basis (standaard); opgelegde beweging ≠ 0 niet | geverifieerd: HR-01..04 analytisch (1 vrijheidsgraad, Euler-Bernoulli-console) en GENE = PHYS ([Respons_op_modale_basis.md](Respons_op_modale_basis.md) §7); Mecway heeft geen harmonische analyse; Mecway-GUI NIET geverifieerd |
| D30 zonder mode superposition | `dyna_impl_3d`; uitvoertijden = Mecway's tijdstap × *keepeverynthtimestep* | geverifieerd: MD-07 (NEWMARK + PETIT gelijk aan Mecway) |
| Responsspectrum | gravity met tabel = spectrum per richting (geen last, lineair in T, constant buiten de tabel); `MONO_APPUI`; modes zonder voorspanning; maxima zonder teken als één stap; von Mises per mode gecombineerd; totale reactie per mode opgeteld en dan gecombineerd | geverifieerd: SP-01 (sdld25a) en SP-02..07 analytisch ([Spectrumanalyse.md](Spectrumanalyse.md)); Mecway-GUI NIET geverifieerd |

### 4.8 Modaal en knik

| Aanname | Wat de bridge doet | Status |
|---|---|---|
| Normering zoals Mecway | trillingsvormen φᵀMφ = 1, knikvormen φᵀKφ = 1 | geverifieerd: MO-01, BU-01, Mecway-voorbeelden ([Verificatie.md](Verificatie.md)) |
| Kniklastfactor = `CHAR_CRIT` | ook negatieve factoren (knik bij omgekeerde last) | geverifieerd: BucklingBeam gelijk aan Mecway; afwijking bij negatieve factoren (KNOWN_BUGS 46) |
| Modaal met belastingen | spanningsverstijving zoals Mecway (K + K_g, centrifugaal ook spin softening `RIGI_ROTA`) | geverifieerd: MP-01..07; afwijkingen balk-`RIGI_ROTA` en schalen met centrifugaalkracht (KNOWN_BUGS 49) |
| Vrij-vrij | `CENTRE` rond −f_s met (2πf_s)² = 1e-8 · max(diag K / diag M); ook met alleen verbindingen (verlijmd contact, koppelingen) | geverifieerd: MO-04, MO-10, VibratingFreePlate |
| Complexe modes (`modal_complex`) | C = αM + βK (het hele model, ook knoopmassa's en veren; K = de stijfheid van het eigenwaardeprobleem, met voorspanning K + K_g) + `AMOR_MECA` van de dempers; zonder zoekfrequentie `PLUS_PETITE` met `TRI_DIAG` (`SORENSEN` kan niet, `ALGELINE2_71`), anders `CENTRE` met `SORENSEN`; FREQ van Code-Aster = gedempte frequentie, `AMOR_REDUIT` = ζ; overkritisch gedempte en starre modes komen niet mee | geverifieerd: MC-01..05 (analytisch en Mecway); `TRI_DIAG` en `QZ` gaven dezelfde waarden (1e-9, gemeten) |
| Cyclische symmetrie (Mecway *Cyclic symmetry*, V30) | `MODE_ITER_CYCL` op de sector (Craig-Bampton: sectormodes met vaste snijvlakken + statische modes van de snijvlakken; testcases sdlv134a, sdls04a); per ND 0 .. N/2 `maxmode` modes, van een paar het eerste lid, in Mecway's volgorde, op het hele wiel (`cyclic_full_wheel`, Mecway's nummering) of de sector; X- of Y-as: het model wordt vooraf naar de Z-as gedraaid (MODE_ITER_CYCL eist Z) en terug; voorspanning met de relaties van ND 0 (u_slave = R u_master); knopen op de as als interface `AXE`; volledig vaste knopen op een snijvlak vallen uit de interfaces | geverifieerd: CY-01..06 (volledig model ≤ 0,0012%, Mecway ≤ 0,03%, Blevins/Leissa ≤ 1,2%; vormen op het hele wiel 1 − MAC ≤ 5,2e-7 t.o.v. het volledige model); grenzen KNOWN_BUGS 61 |
| Betekenis van `CRIT_STAB` | kleine verplaatsingen: kritische lastfactor van de huidige last; grote verplaatsingen (één elset is genoeg): −(kleinste eigenwaarde van K_T), knik bij 0; de bridge schat het nulpunt lineair uit de laatste twee stappen | gemeten ("produits B*X" in de `.mess`): NK-01, NK-02a/b, NK-04; SIMO_MIEHE NIET geverifieerd (KNOWN_BUGS 53) |
| Imperfectie | lineaire knikvorm onder de lasten op de eindtijd, `NORM_MODE` `TRAN`, `MODI_MAILLAGE DEFORME`; na de berekening mesh terug; verplaatsingen t.o.v. de imperfecte vorm | geverifieerd: NK-03 (versterking ≤ 0,5 %), NK-04 |

### 4.9 Thermisch

| Aanname | Wat de bridge doet | Status |
|---|---|---|
| Tijdschema | θ-methode met θ-gewogen belasting; Mecway: Crank-Nicolson met de belasting op het einde van de stap | afwijking: θ = 0,5 volgt Mecway bij constante belasting (KNOWN_BUGS 14, TH-02) |
| Stationair met tijdstabel | t = 1 s | KNOWN_BUGS 14 |
| Formule als waarde (x, y, z, t) | `FORMULE` in de Gauss-punten, θ-gewogen; stationair t = 1 s | geverifieerd: WE-06 gelijk aan Mecway (7e-12 K), WE-03 energie gelijk aan Mecway; temperatuurverschil met Mecway door het tijdschema (KNOWN_BUGS 14) |
| Temperatuurafhankelijk materiaal | `THER_NL`, tabellen constant verlengd, ρc om de 10 graden verfijnd | geverifieerd: WE-04a exact (Kirchhoff), WE-04b energie 0,01%, Mecway ≤ 0,15% |
| Lasbron (`#ASTER-LASBRON`) | Goldak dubbel-ellipsoïde, alleen op volume-elementen | geverifieerd: WE-01 (Rosenthal ≤ 1%), WE-02 (≤ 1,2%), energie ≤ 0,06% |
| Toevoegmateriaal (`geboorte=`) | "quiet element": stil tot de geboorte (booglengte langs de baan), daarna het gewone materiaal; mechanisch spanningsvrij bij de geboorte; meer bronnen (ook Mecway-formule-/tabelbronnen) in één last | geverifieerd: WE-11/11b energie ≤ 0,8%, WE-12/12b krimpspanning ≤ 0,04%; WE-13 kwalitatief; KNOWN_BUGS 71 |
| Keten thermisch → mechanisch | aan bij een Thermal stress in een T31-model; `STAT_NON_LINE` op de thermische tijden, `AFFE_VARC` `TEMP` met `EVOL` = het thermische resultaat, `VALE_REF` = referentietemperatuur van de Thermal stress | geverifieerd: WE-07..09 ≤ 4·10⁻⁸ t.o.v. de handberekening; KNOWN_BUGS 64 |
| Temperatuurafhankelijke E, ν, α, SY, H (`#ASTER-MATERIAAL`) | `ELAS_FO` / `ECRO_LINE_FO`, lineair tussen de tabelpunten, daarbuiten constant; α = secans t.o.v. `T_ALPHA` (standaard de referentietemperatuur); ET = E·H/(E + H) per tabelpunt | geverifieerd: WE-09 (elastisch, plastisch, omgekeerd vloeien) |
| Thermische rek boven `T_CUT` | constant (α = ε_cut/(T − T_ALPHA) in punten met 2% groei, tot T_CUT + 10 000 K) | keuze (smelten, Lindgren 2001); zonder `T_CUT` loopt de rek door ([Lassen.md](Lassen.md) §9.2) |
| Metallurgie (`#ASTER-METALLURGIE`) | `CALC_META` `RELATION='ACIER'` (Waeckel) op het thermische resultaat, `META_ACIER`/`DURT_META` in het thermische materiaal; standaard-datasets 16MND5 (testcase mtlp103a) en HSNV101A (hsnv101a); `begin` standaard ferriet; fasen en hardheid als knoopvelden | geverifieerd: MT-01 (hsnv101a in 3D ≤ 1,3·10⁻⁶), MT-02/MT-08 (Koistinen-Marburger ≤ 4·10⁻⁸), MT-03 (austenitiseren ≤ 2·10⁻⁸); gemeten grenzen KNOWN_BUGS 72 |
| Metallurgische wet (`mechanica=ja`) | `ELAS_META_FO` + `META_ECRO_LINE`, `RELATION='META_P_IL'` met `AFFE_VARC` `M_ACIER`; `PHASE_REFE` volgt `begin`, `TEMP_DEF_ALPHA` = referentietemperatuur; mengregel vloeigrens lineair; ALPHA_A en DEPS verplicht (behalve HSNV101A) | geverifieerd: MT-01 (TEST_RESU hsnv101a ≤ 5·10⁻⁵), MT-04/MT-05 (transformatierek en spanning ≤ 6·10⁻⁶) |

### 4.10 Resultaten

| Aanname | Wat de bridge doet | Status |
|---|---|---|
| Knoopspanningen | `SIGM_NOEU` en `SIEQ_NOEU` (Code-Aster-werkwijze), niet Mecway's gemiddelde tensor | afwijking, bewuste keuze (KNOWN_BUGS 3) |
| Schaalspanningen | alleen von Mises (boven-, midden-, ondervlak) | LS-03, LS-05 |
| Niet geconvergeerd | resultaten tot het laatst bereikte tijdstip (`BRIDGE_ONVOLLEDIG`) | NL-01 met `convergence_resi_rela` 1e-6 (stopt op t = 2,92) |

### 4.11 Akoestiek

| Aanname | Wat de bridge doet | Status |
|---|---|---|
| Vlak zonder voorwaarde = harde wand | geen rand-element (∂p/∂n = 0, natuurlijke randvoorwaarde) | bron: Mecway (2026) §6.9.1; geverifieerd: AK-01, AK-04 |
| *Fluid pressure* = 0 = drukknoop | `AFFE_CHAR_ACOU PRES_IMPO PRES=0j` op de knopen of vlakken; ≠ 0: ERROR bij de holtemodes (ook Mecway weigert), opgelegde druk (bron) in de harmonische analyse | bron: Mecway (2026) §9.34; geverifieerd: AK-02 (knopen), AK-03 (vlakken), AH-07 (2 Pa) |
| Meer media | gekoppeld met druk en ∂p/∂n continu: alleen juist bij gelijke dichtheid; verschillende dichtheid: ERROR | gemeten (AK-05 en een buis met ρ 1,2/12, [Akoestiek.md](Akoestiek.md) §3.2); Mecway zelf: één materiaal |
| Impedantie | Z = *specificimpedancer* + i·*specificimpedancei* (Pa·s/m), randterm ρ/Z ∫NNᵀdA; holtemodes: complexe modes (frequentie, decay rate, `pressure` + `pressurei`), zonder dichtheid ERROR (Mecway rekent dan met ρ = 0, een harde wand); harmonisch: reële Z als `3D_ABSO` met `CELE_R = Z/ρ`, complexe Z: ERROR | bron: Mecway (2026) §6.9.2, §9.35; geverifieerd: AI-01…10 (≤ 1e-8 t.o.v. Mecway, analytisch ≤ 0,15%), AH-06 (Z = 2ρc, ≤ 7e-6); KNOWN_BUGS 55, 57 |
| Harmonisch: bron, absorberende rand, microfoon | speciale selectienamen `BRON_`/`SOURCE_` (vlakken, `VITE_FACE`), `ABSORBEREND_`/`ABSORBING_` (vlakken, `3D_ABSO` met ρc van het medium), `MICROFOON_`/`MICROPHONE_` (knopen); `#ASTER-BRON selectie = v [, fase]` | geverifieerd: AH-01…08; Mecway kent deze invoer niet (geen harmonische analyse, Mecway (2026) hoofdstuk 6) |
| Harmonisch: `auto` | A30 met een bron (`BRON_`, `#ASTER-BRON`, *fluid pressure* ≠ 0) → `acoustic_harm_3d`, anders `acoustic_modes_3d` | keuze; INFO in de log |
| Vibro-akoestiek: `auto` | V30 met een fluïdum-onderdeel → `vibroacoustic_modes_3d`; een fluïdum in een andere analyse wordt als vaste stof gerekend (WARNING) | keuze; INFO in de log |
| Vibro-akoestiek: dichtheid | zit in de matrices (anders dan bij de holtemodes); twee fluïda met gedeelde knopen alleen bij gelijke dichtheid (anders ERROR) | gemeten: VA-04 (gelijke dichtheid, exact) en een buis met ρ 1,2/12 (188,23 i.p.v. 306,47 Hz) |
| Vibro-akoestiek harmonisch: invoer | hetzelfde V30-model als de modes; bronnen `BRON_` (snelheid), `INVALLEND_` (invallende golf), `#ASTER-BRON` (snelheid of druk), randen `ABSORBEREND_` en Mecway *impedance* (reëel), `MICROFOON_`, `MEETPUNT_`; analyse zelf kiezen (`auto` blijft de modes) | keuze; geverifieerd: VH-01…08; Mecway kent deze analyse niet (Mecway (2026) hoofdstuk 6) |
| Vibro-akoestiek harmonisch: Rayleigh-demping | alleen op de constructie (α·M_s + β·K_s), niet op het fluïdum | keuze (Mecway rekent geen fluïdum in V30); geverifieerd: VH-04, VH-04b |

### 4.12 Breukmechanica

| Aanname | Wat de bridge doet | Status |
|---|---|---|
| Invoer | speciale selectienamen: knoopselectie `SCHEUR_FRONT`/`CRACK_FRONT`, vlakselecties `SCHEUR_LIP_BOVEN`/`CRACK_LIP_UPPER` en `SCHEUR_LIP_ONDER`/`CRACK_LIP_LOWER`; zonder onderlip een half model (`SYME='OUI'`); meer scheuren met een achtervoegsel | Mecway kent geen breukmechanica (Mecway (2026)); geverifieerd: BR-01…06 (BR-06: twee scheuren) |
| Front | de ribben van de volume-elementen met beide eindknopen in `SCHEUR_FRONT` worden SEG2/SEG3-cellen (`BRSCHEUR<n>`) | geverifieerd: BR-01 (recht), BR-04 (kwartcirkel) |
| Open scheur | de lippen mogen buiten het front geen knopen delen (anders ERROR); `CONFIG_INIT='COLLEE'` | geverifieerd: BR-01 (dubbele knopen), BR-02 (half model) |
| Materiaal en resultaat | `CALC_G` en `POST_K1_K2_K3` rekenen op een eigen resultaat met een materiaal op alle cellen (ook randcellen) en dezelfde lasten | bron: `<EXCEPTION> CALCUL_20` zonder materiaal op de lippen, `RUPTURE0_94` zonder `SIEF_ELGA` (gezien bij de bouw) |
| Methode | `CALC_G` `OPTION=('G', 'K')`: G (theta-methode) en K (interactie-integraal) is het resultaat; `POST_K1_K2_K3` is een controle | geverifieerd: BR-01 (K −0,1 %, G −0,4 %; POST_K −3,5 % met hex20 zonder kwartpunten) |
| Gekromd front | cirkelvormig front rond de lip: `FORM_FISS='CERCLE'`, `RAYON` uit de geometrie; ander krom front: geen correctie (WARNING) | gemeten forma07a: zonder correctie K +5,6 %, met +0,1 % |
| Lineair, geen contact | K en G van één lineair statische oplossing; druk op een scheur (lippen over elkaar) wordt niet tegengehouden: WARNING bij K_I < 0 | keuze; niet-lineair en contact op de lippen: niet gebouwd (KNOWN_BUGS 63) |
| XFEM: invoer | `#ASTER-XFEM vorm=CIRKEL/ELLIPSE/RECHTHOEK/HALFVLAK` met de maten in m (of met eenheid), of een vlakselectie `XFEM_<naam>` op een knooplaag; geen scheur in het mesh; alleen volume-elementen met `3D` (anders ERROR) | keuze ([Breukmechanica.md](Breukmechanica.md) §7); geverifieerd: BR-07..13 |
| XFEM: gladmaken | `CALC_G_XFEM` `LISSAGE`: recht front (HALFVLAK, RECHTHOEK) `LAGRANGE`, gekromd (CIRKEL, ELLIPSE) `LEGENDRE` met graad `fracture_legendre_degree` (5); per scheur `glad=`/`graad=`; R_INF/R_SUP uit `fracture_r_inf`/`_sup` of per scheur | gemeten: LAGRANGE op een gekromd front oscilleerde (−0,1 tot 2 × K), LEGENDRE ≥ 2 op een recht front ±3 tot ±25 % |
| XFEM: symmetrie | *Symmetry* langs een globale as wordt `DDL_IMPO` i.p.v. `LIAISON_OBLIQUE` (legt ook de XFEM-vrijheidsgraden vast); schuin op knopen van gesneden elementen: WARNING | gemeten forma07b (BR-11): LIAISON_OBLIQUE K1 aan het symmetrievlak +3,8 %, DDL_IMPO exact |
| XFEM: velden naar Mecway | `POST_MAIL_XFEM` + `POST_CHAM_XFEM` + `PROJ_CHAMP` `COLLOCATION`: DEPL, SIGM_NOEU, SIEQ_NOEU op de Mecway-knopen (fysisch, per kant van de scheur); REAC_NODA uit het XFEM-resultaat; geen SIGM_ELNO, geen foutschatter en geen vermoeiing | geverifieerd: BR-07 (lippen symmetrisch), BR-10 (opening +3,3 %); REAC_NODA op gesneden elementen NIET geverifieerd |
| XFEM: K bij een gekromd front | `CALC_G_XFEM` heeft geen krommingscorrectie: WARNING, gebruik `POST_K1_K2_K3` of G | gemeten BR-10: K_I `CALC_G_XFEM` +5,3 %, `POST_K1_K2_K3` +1,6 %, uit G +1,0 % |

### 4.13 Vermoeiing

Invoer met `#ASTER`-regels, geen instellingen in het hoofdvenster
([`Vermoeiing.md`](Vermoeiing.md)); hieronder de standaard van elke sleutel.

| Aanname / standaard | Wat de bridge doet | Status |
|---|---|---|
| Invoer | Mecway kent geen vermoeiing (manual, `mecway.exe`): `#ASTER-WOHLER` per materiaal, `#ASTER-VERMOEIING`, `#ASTER-BLOK`/`#ASTER-SIGNAAL` | keuze (zoals `#ASTER-LASBRON`: modelgegevens) |
| S = amplitude | de Wöhler-S is σ_a = Δσ/2, zoals `DEFI_MATERIAU FATIGUE WOHLER` | gemeten: szlz100a (cyclus 600/−500 → N(550)), VM-05 |
| `INTERPOL = LOG` | log-log tussen de tabelpunten (zoals szlz100a/sslv135a) | geverifieerd: VM-01a, VM-02a (≤ 10⁻⁶) |
| `PROL_GAUCHE = EXCLU` | onder de tabel geen schade | gelijk aan `POST_FATIGUE`/`CALC_FATIGUE` (gemeten D = 0, VM-06) |
| `PROL_DROITE = LINEAIRE` | boven de tabel log-log doorgetrokken + WARNING | keuze: Code-Aster stopt met `EXCLU` en trekt met `LINEAIRE` lineair in (S, N) door (negatieve schade gemeten) |
| `spanning = VMIS_SG` | von Mises met het teken van het spoor, uit `SIGM_NOEU` | zoals `CALC_FATIGUE CUMUL_DOMMAGE` (`EQUI_GD` standaard); VM-04, VM-06, VM-07a |
| `telling = RAINFLOW` | periodiek: begin bij de grootste absolute waarde, alleen gesloten cycli | gelijk aan `POST_FATIGUE RAINFLOW` (VM-03b) en `CALC_FATIGUE` (VM-04, VM-06) |
| `correctie = GEEN` | geen gemiddelde-spanningscorrectie; Goodman/Gerber met het teken van S_m | formules gelijk aan `POST_FATIGUE CORR_SIGM_MOYE` (gemeten, VM-05b/c) |
| `herhalingen = 1` | D = herhalingen × D per herhaling; `life` = 1/(D per herhaling), max. 10¹² | keuze |
| Knoopspanning | `SIGM_NOEU` (gemiddeld per knoop) van de volume-elementen; een knoop van twee materialen met een curve krijgt de grootste schade | keuze (Code-Aster-standaard voor knoopvelden, KNOWN_BUGS 3); balken: niet gebouwd (KNOWN_BUGS 66) |
| Schalen | uniaxiale route op de boven- en onderzijde: `SIEQ_NOEU` (`VMIS_SG` of de `PRIN_i` met de grootste absolute waarde) van `POST_CHAMP EXTR_COQUE` `SUP`/`INF`; velden `damage_top`/`damage_bottom`, `damage` = de grootste | geverifieerd: VM-10 (zuivere buiging, ≤ 10⁻¹¹); geen rekcurve of criterium op schalen (WARNING) |
| `rek = PRIN` (rekcurve) | hoofdrek met de grootste absolute waarde uit `EPSI_NOEU` (bij een staaf de lengterek, zoals een rekgestuurde proef); `VMIS_SG` = √(2/3 e:e) van de deviator met het teken van het spoor | keuze; geverifieerd VM-11a (PRIN, 2·10⁻⁹), VM-11b (VMIS_SG, exact) |
| E van een rekcurve | E van het Mecway-materiaal (bij `*` moeten alle materialen dezelfde E hebben, anders `E = ...` verplicht) | keuze |
| `criterium = GEEN` | geen multiaxiaal criterium: equivalente spanning per tijdstap (`spanning`) | keuze; met `DANG_VAN`/`MATAKE`/`CROSSLAND`/`FORMULE` het kritieke vlak van Code-Aster (`CALC_FATIGUE FATIGUE_MULTI DOMA_NOEUD`) |
| a, c verplicht; b optioneel | geen standaard voor de constanten van het criterium: ze horen bij het materiaal (kalibratie uit σ₋₁ en τ₋₁, Vermoeiing.md §1.7); b alleen voor `fatigue_ratio`; Code-Aster's `D_VAN_B`/`MATAKE_B` (niet in SIGEQ, gemeten) krijgt b of 1 | keuze; 1 ≤ c ≤ 1,7321 zoals de catalogus |
| `belasting = PERIODIEK` | het verloop (of elk blok) is één cyclus, N uit SIGEQ met de curve van de bridge | geverifieerd: sslv135a (VM-08a/b, `VALE_REFE`), VM-09 met de hand |
| `projectie = UN_AXE` | alleen bij `NIET_PERIODIEK` (Code-Aster `PROJECTION`) | Code-Aster heeft geen standaard (verplicht); gemeten op sslv135a: `UN_AXE` = `DEUX_AXES` |
| Begintoestand in het multiaxiale verloop | de bridge kopieert het niet-lineaire/dynamische resultaat (`CREA_RESU`), zodat t = 0 meetelt | `CALC_FATIGUE FATIGUE_MULTI` slaat `NUME_ORDRE` 0 over (alarm `PREPOST4_27`, gemeten: de halve amplitude bij een ramp); VM-08d |
| Levensduur per cyclus begrensd | N < 1 wordt 1; met Goodman/Gerber en \|S_m\| ≥ S_u (Gerber) of S_m ≥ S_u (Goodman) N = 1; rekcurve: N met bisectie (tolerantie 10⁻¹³), boven 10³⁰ cycli geen schade | keuze (`aster_fatigue`) |
| `telling = ASTM` | restbereiken aan het begin en eind tellen als halve cycli (ASTM E1049 §5.4.4, een doorgang) | keuze; niet in een verificatietest |
| Multiaxiaal `NIET_PERIODIEK` | de Wöhler-curve gaat naar Code-Aster doorgetrokken tot N = 10¹², daaronder geen schade (`EXCLU`) | keuze (zelfde grens als `life`) |
| Kritiek vlak periodiek | `CALC_FATIGUE` `METHODE='CERCLE_EXACT'` (niet met een formule) | keuze; VM-08a/b |
| Basis van `#ASTER-BLOK`/`#ASTER-SIGNAAL` | het eerste opgeslagen resultaat (statisch: de enige stap), geschaald per blok of signaalwaarde; een blok = de reeks [m − a, m + a], één cyclus | keuze |
| Melding | WARNING als de schade D ≥ 1 | - |

### 4.14 `#ASTER`-invoer: eenheden en standaardwaarden

Hoe de bridge de waarden in de `#ASTER`-regels leest (`bridge_custom` en de module
erachter). Punt als decimaalteken; de komma scheidt waarden.

| Regel | Zonder eenheid | Eenheden | Status |
|---|---|---|---|
| `#ASTER`, `-POST`, `-EXCIT`, `-CONTACT`, `-ZONE` | tekst, ongewijzigd naar de `.comm` (SI-eenheden van het model in Code-Aster) | geen controle | keuze |
| `-OPTIE sleutel = waarde` | het type van de bestaande instelling (getal, tekst, ja/nee) | ja/nee: `ja`/`nee`, `aan`/`uit`, `yes`/`no`, `on`/`off`, `true`/`false`, `1`/`0`, `oui`/`non` (ook `waar`/`onwaar`, `vrai`/`faux`); een ander woord geeft een WARNING en de instelling blijft (tot oktober 2026 stil uit); een geheel getal met decimalen (`5.0`) is een ERROR | keuze |
| `-BEZWIJKEN materiaal = rek` | rek (dimensieloos); decimale komma toegestaan | een eenheid of `%` is een ERROR | keuze |
| `-SPECTRE` extra `K=V` | ongewijzigd naar `COMB_SISM_MODAL` (bijv. `ECHELLE`) | geen controle; de laatste regel per richting telt | keuze |
| `-WOHLER` S, Sf, Se, Su, E | geen standaard: ERROR | een spanningseenheid is verplicht (Pa, kPa, MPa, GPa, N/mm2, psi, ksi); N, m, b, ef, c zijn dimensieloos (eenheid: ERROR) | keuze |
| `-VERMOEIING` | a, c, `herhalingen` dimensieloos; b met een spanningseenheid | als `-WOHLER` | keuze |
| `-BLOK`/`-SIGNAAL` | factoren op de statische last | alleen getallen (komma's tussen de waarden) | keuze |
| `-BRON` (`acoustic_harm_3d`) | snelheid in m/s; fase in graden, standaard 0 | m/s, mm/s, mm/ms, in/s, ft/s; een druk-eenheid of een andere eenheid en tekst zonder getal geven een ERROR | keuze; een opgelegde druk: Mecway's *fluid pressure* ≠ 0 |
| `-BRON` (`vibroacoustic_harm_3d`) | snelheid in m/s; fase standaard 0 | Pa, N/m2, kPa, kN/m2, MPa, N/mm2, GPa, bar, mbar, psi = invallende golf (een keer naar Pa); m/s, mm/s, mm/ms, in/s, ft/s of geen eenheid = snelheid; een andere eenheid of tekst zonder getal is een ERROR (tot oktober 2026 werd die stil een snelheid in m/s en `1 bar` 1e10 Pa) | keuze |
| `-FASE selectie = fase` | graden | een eenheid is een ERROR; zonder regel: fase 0 | keuze |
| `-LASBRON`, `-MATERIAAL`, `-METALLURGIE` | SI (W, m, m/s, s, Pa, 1/K); temperaturen in °C (`TC`, en `AR3`, `MS0`, `AC1`, `AC3` zoals `META_ACIER`) | een eenheid is een ERROR | keuze ([Lassen.md](Lassen.md)) |
| `-XFEM` | lengte in m | eenheden worden omgerekend; een onbekende eenheid geeft een WARNING en de waarde telt als m | keuze |

**Let op m en M.** Overal waar een eenheid mag, maakt de hoofdletter het verschil:
`MPa` = 10⁶ Pa, `mPa` (en `mpa`) = 10⁻³ Pa (`parse_and_convert`, zoals Mecway's
eigen eenheden). `S = [400, 200] mpa` is dus een factor 10⁹ te klein.

---

## 5. Controleruns bij deze review

Alle runs: offline, bridge in deze werkmap, Code-Aster 17.4, oktober 2026. Basis =
de genoemde verificatiecase, één instelling anders. De niet-lineaire runs zijn gedaan
met `convergence_resi_rela` 1e-6 (de standaard tot oktober 2026, nu 1e-5, §3.3),
tenzij anders vermeld.

| Id | Basis en wijziging | Uitkomst |
|---|---|---|
| R-SUB1 | NL-02a, `substeps_per_interval` 1 | 3 stappen (9, 11 en 9 iteraties), uitkomst gelijk aan 10 substappen tot 1e-7, alle controles OK |
| R-REAC0 | NL-02a, `newton_reac_iter` 0 | stopt in stap 1 met `DVP_2`, geen resultaten |
| R-RIGID | blok 2×1×1 hex20, alleen een opgelegde verplaatsing (starre translatie) | `RELA`: `MECANONLINE9_7` in stap 1 (geen omschakeling naar `MAXI` in de eerste stap, EDF R&D, U4.51.03); `MAXI` 1e-3 N: 1 iteratie per stap, exact |
| R-MAXI | NL-01, `MAXI` 1e-2 N | tot t = 3, alle controles exact |
| R-SUB40 | NL-01, 40 substappen | stopt op t = 0,013 (restkracht ~5e-4 N) |
| R-SUB40-1E5 / R-SUB40-PETIT | idem met 1e-5 / met `PETIT` | tot t = 3; met 1e-5 alle controles exact |
| R-CURVE | NL-01 met hardingscurve (0, 0), (σy/E, σy), (0,1, …) | Mecway/CCX: 430,6 MPa op t = 2; bridge `auto` (totale rek): met 1e-6 stop op t = 0,013, met 1e-5 exact tot t = 3; zonder (0, 0) met `auto` (totale rek): exact tot t = 3 (σ op t = 2: 433,49 MPa, analytisch); curve (0, 355 MPa) als plastische rek: exact, WARNING in de log |
| R-ROM | NL-01, 1e-6 met `RELA_OF_MAXI`, `RESI_GLOB_MAXI` 0,05 N / 1e-3 N | 0,05 N: exact tot t = 3 (= NL-01b); 1e-3 N: stopt, de absolute rest stagneert op ~1e-2 N |
| R-1E5 | alle NL- en DY-cases, `convergence_resi_rela` 1e-6 → 1e-5 | grootste relatieve verandering van de resultaten 3,75e-6 |
| R-ALPHA | DY-01, HHT α = −0,3 | periode +1,21 %, piek −0,87 %, gelijk aan het schema (4,7e-8) |
| R-ENERGY | DY-01a, `energy_balance` aan | uitkomst gelijk, 101 balansregels in de `.mess` |
| R-DT | DY-03a, `explicit_dt_factor` 0,7 / 1,0 / 1,5 en 0,3 | 0,7…1,5: `DYNAMIQUE_2`; Code-Aster-grens 9,667e-7 s tegen schatting 1,933e-6 s; 0,3: binnen de tolerantie |
| R-TCHAMWA | DY-03a, `schema` TCHAMWA | binnen de tolerantie (alleen de vergelijking met de DIFF_CENT-keten wijkt af, 0,4 %) |
| R-STRIP | uitkragende strook 0,2 × 0,01 m, t = 5 mm, 10 DKT, staplast, expliciet en impliciet | periode 9,63 / 9,60 ms (Euler-Bernoulli 9,57 ms), piek 1,957 × statisch |
| R-GCPC | LS-02 hex8 n = 8 en 16, `lin_solver` GCPC | binnen de tolerantie; 232 / 499 iteraties |
| R-FREE | blok alleen in X vast, `solver_nprec` -1 / 8 | `FACTOR_57` / `FACTOR_11` |
| R-NPREC-CONTACT | NL-03a (STANDARD), `solver_nprec` -1 | rekent door; contactkracht −1,6 %, tip boven +2,8 % (tolerantie 0,5 %) |
| R-NORM | MO-01, `modal_norm` TRAN_ROTA | frequenties gelijk; tiprotatie `rotz` = 1,000, grootste verplaatsing 0,726 |
| R-SHIFT | MO-01, `modal_shift_hz` 100 / 400 / 600 | bij 600 Hz: 104,7…681,7 Hz, de 6 modes het dichtst bij in ω² |
| R-BSHIFT | BU-01, `OPTION='CENTRE'` met `CHAR_CRIT` 90 / 95 / 150 / 200 / −200; `OPTION='BANDE'` met `CHAR_CRIT=(100, 300)` | `CENTRE`: steeds de 3 kleinste factoren, "décalage … 0.00000E+00"; `BANDE`: 209,853 en 259,086 |

---

## 6. Bronnen

**Code-Aster-documentatie** (EDF R&D, versie "default"). *Lokaal*: Engelse
machinevertaling in een lokale map met Code-Aster-documentatie.
*Online*: DocAster, `https://docaster-en-codeaster-doc-4113bb35b8213385c636b94f1536856d7f617.gitlab.io/manuals/man_u/`
(geraadpleegd 5 oktober 2026) en `https://code-aster.org/doc/default/fr/man_u/`.

- EDF R&D (2018). *Notice de calcul au flambage*, U2.08.04, 12-01-2018. Lokaal.
- EDF R&D (2018). *Opérateur THER_LINEAIRE*, U4.54.01, 06-04-2018. Lokaal.
- EDF R&D (2020). *Notice d'utilisation des solveurs linéaires*, U2.08.03, 05-05-2020 (lokaal); versie 11-01-2024 online (Frans).
- EDF R&D (2020). *Opérateur STAT_NON_LINE*, U4.51.03, 30-04-2020. Lokaal; online §"Convergence settings".
- EDF R&D (2020). *Opérateur THER_NON_LINE*, U4.54.02, 05-05-2020. Lokaal.
- EDF R&D (2021). *Mot clé SOLVEUR*, U4.50.01, 04-11-2021 (lokaal); versie 11-01-2024 online (Frans).
- EDF R&D (2021). *Opérateur DEFI_CONTACT*, U4.44.11, 04-11-2021. Lokaal en online.
- EDF R&D (2021). *Opérateur DEFI_MATERIAU*, U4.43.01, 03-11-2021. Lokaal.
- EDF R&D (z.j.). *Instructions for using contact in code_aster*, U2.04.04. Online.
- EDF R&D (z.j.). *Tips for using STAT_NON_LINE*, U2.04.01. Online.
- EDF R&D (z.j.). *General tips for using DYNA_NON_LINE*, U2.06.13. Online.
- EDF R&D (z.j.). *Operator DEFI_LIST_INST*, U4.34.03. Online.
- EDF R&D (z.j.). *Operator DYNA_NON_LINE*, U4.53.01. Online.

**Code-Aster-installatie** (EDF R&D, code_aster 17.4, Windows-build v2025):
`%LOCALAPPDATA%\code_aster\v2025\17.4\lib\aster\code_aster\`; standaardwaarden
uit `Cata/Commands/` (`calc_modes.py`, `defi_contact.py`, `defi_list_inst.py`,
`dyna_non_line.py`, `ther_lineaire.py`) en `Cata/Commons/` (`c_convergence.py`,
`c_newton.py`, `c_solveur.py`); meldingen uit `Messages/`.

**Mecway**: Mecway (2026). *Mecway Finite Element Analysis, Manual, version 33*
(PDF van 09-03-2026), `C:\Program Files\Mecway\manual.pdf`: §6.2 (niet-lineair
statisch), §7.3 (hex8 met incompatibele modes), §7.7 (veer), §9.3 (pinned support),
§9.14 (druk).

**Literatuur**

- Belytschko, T., Liu, W.K. en Moran, B. (2000). *Nonlinear Finite Elements for Continua and Structures*. Chichester: Wiley. Stabiele stap met demping (geciteerd in `bridge_to_aster._damped_step_factor`; paragraaf NIET in het boek gecontroleerd).
- Hilber, H.M., Hughes, T.J.R. en Taylor, R.L. (1977). Improved numerical dissipation for time integration algorithms in structural dynamics. *Earthquake Engineering and Structural Dynamics*, 5, 283–292.
- Hughes, T.J.R. (2000). *The Finite Element Method: Linear Static and Dynamic Finite Element Analysis*. Mineola: Dover. Hoofdstuk 9.

Overige literatuur van de verificatietests: [Verificatie.md](Verificatie.md).
