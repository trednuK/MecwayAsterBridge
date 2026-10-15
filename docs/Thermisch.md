# Thermische analyses (Mecway T30 / T31)

*English version: [Thermal.md](en/Thermal.md)*

Wat de bridge met een thermisch Mecway-model doet (`Scripts/bridge_thermal.py`,
template `Scripts/AsterTemplate_Thermique.comm`). Code-Aster 17.4.

## 1. Analyse en solver

| Mecway | Bridge (`active_analysis`) | Code-Aster |
|---|---|---|
| T30, thermisch stationair | `ther_3d` (ook via "auto") | `THER_LINEAIRE` `TYPE_CALCUL='STAT'` |
| T31, thermisch transient | `ther_3d` (ook via "auto") | `THER_LINEAIRE` `TYPE_CALCUL='TRAN'` |
| met straling, convectie/straling op een schaalvlak of een temperatuurafhankelijk materiaal | `ther_3d` | `THER_NON_LINE` (materiaal `THER_NL`) |
| T31 met een bewegende lasbron (`#ASTER-LASBRON`) | `ther_3d` | als hierboven, met een bron `AFFE_CHAR_THER_F` ([Lassen.md](Lassen.md)) |
| T31 met een *Thermal stress* (en mechanische opleggingen) | `ther_3d` | als hierboven, daarna `STAT_NON_LINE` met de temperatuur als `AFFE_VARC` (restspanning en vervorming, [Lassen.md](Lassen.md) §9) |

- **Celsius.** Code-Aster's `RAYONNEMENT` rekent met `T + 273,15` (U4.44.02), dus
  de hele berekening staat in °C. Mecway-waarden (K, °C of °F) worden omgerekend;
  het resultaat `temperature` gaat in Kelvin terug naar Mecway.
- **Tijdstappen (T31):** `<timesteps timeperiod stepsize>` (of
  `timepointsincrement`): vaste stap, elke stap wordt geschreven (ook t = 0, de
  begintoestand).
- **Begintemperatuur:** `<initialconditions><temperature2>`; knopen zonder
  begintemperatuur starten, zoals in Mecway, op 0 K (manual v33 §6.7.2). De
  bridge waarschuwt als er geen begintemperatuur is.
- **Resultaten:** alleen via `result_route = "liml"`: `temperature` (knopen) en
  de warmteflux `heatfluxx/y/z` + `heatfluxmag` (`FLUX_NOEU` = −λ grad T; knopen).

## 2. Instellingen (startscherm, pagina "Thermisch")

| Instelling (sleutel) | Standaard | Betekenis |
|---|---|---|
| *Tijdschema THETA (0 .. 1)* (`theta`) | 0,57 | `SCHEMA_TEMPS` THETA, alleen transient (0 = expliciet, 0,5 = Crank-Nicolson, 1 = impliciet Euler); Code-Aster-standaard 0,57 (catalogus `ther_lineaire.py`). Mecway rekent Crank-Nicolson met de belasting op het einde van de stap: 0,5 volgt Mecway exact bij constante belasting (§5). |
| *Max. Newton-iteraties*, *Convergentie RESI_GLOB_RELA*, *NEWTON REAC_ITER* (`newton_max_iter`, `convergence_resi_rela`, `newton_reac_iter`) | 20, 1e-6, 1 | `THER_NON_LINE` (`CONVERGENCE`, `NEWTON`) en de mechanische `STAT_NON_LINE` van de keten thermisch → mechanisch. |
| *COMPORTEMENT DEFORMATION*, *Rekdefinitie hardingscurve* (`deformation`, `plastic_strain_definition`) | PETIT, auto | alleen de keten thermisch → mechanisch (T31 met een Thermal stress, [Lassen.md](Lassen.md) §9.3). |
| *MUMPS NPREC* (`solver_nprec`) | 8 | MUMPS NPREC. |
| *Resultaatvelden naar Mecway* (`fields`) | temperature, heat_flux | welke velden naar Mecway gaan. |
| *Tijdslimiet* / *Geheugenlimiet run_aster* (`time_limit`, `memory_limit`) | 1800 s, 4096 MB | limieten van de Code-Aster-job. |

## 3. Vertaling van elementen en belastingen

| Mecway | Code-Aster |
|---|---|
| volume-element | `MODELISATION='3D'`, `THER` (LAMBDA, RHO_CP = ρ·cp) |
| schalen in evenwijdige vlakken | `MODELISATION='PLAN'` met factor f = t / t_ref op LAMBDA, RHO_CP en alle belastingen (t_ref = 1 m met volumes, anders de meest gebruikte dikte); per dikte een eigen deelgroep; de flux rekent `CALC_CHAMP` met de echte λ. Liggen de schalen niet in Z = constant, dan draait de `.comm` het mesh (`MODI_MAILLAGE ROTATION`) en de flux terug naar de globale assen; alarm MODELE1_53 is dan normaal |
| balk / fin-element, schalen die niet allemaal evenwijdig zijn | **niet vertaald** (Code-Aster heeft geen thermisch 1D-element; de thermische `COQUE` heeft drie temperaturen door de dikte) |
| `temperature2` (knopen, vlakken, elementen) | `TEMP_IMPO` (tijdstabel: `AFFE_CHAR_THER_F`) |
| `nodetemperature` | `TEMP_IMPO` per knoopgroep |
| `heatflux` op vlakken | `FLUX_REP FLUN` (volume, schaalrand); schaalvlak: `SOURCE` q/t; vlak 5 én 6 van een schaal in één selectie: beide zijden (factor 2, zoals Mecway) |
| `heatflow` op vlakken / elementen | totaal ÷ oppervlak (schaalrand: lengte × dikte) of ÷ volume, dan als hierboven |
| `heatflow` op knopen | Q/N per knoop (manual §9.27) als bronveld M⁻¹F (`MASS_THER`, `RESOUDRE`, `SOURCE SOUR_CALCULEE`); tijdstabel via `FONC_MULT` |
| `heatgeneration` | `SOURCE` |
| formule als waarde (x, y, z, t; `temperature2`, `heatflux`, `heatgeneration`, `convectionbc`, `radiationbc` op volumevlakken en schaalranden, `heatflow` alleen in t) | `FORMULE` van X, Y, Z, INST in `AFFE_CHAR_THER_F`, met de eenheden uit de Mecway-attributen (`unit`, `positionunit`, `timeunit`); stationair: t = 1 s. Verificatie WE-03/WE-06 ([Verificatie.md](Verificatie.md) §8) |
| temperatuurafhankelijk materiaal (`TempDependent`: λ(T), c(T)) | `THER_NL` met `DEFI_FONCTION` van TEMP (PROL constant, zoals Mecway §8.6); ρc-tabel verlengd en om de 10 graden verfijnd ([Lassen.md](Lassen.md) §6) |
| bewegende lasbron | `#ASTER-LASBRON` ([Lassen.md](Lassen.md)) |
| `convectionbc` | `ECHANGE` (schaalvlak: `SOUR_NL`; met een tijdstabel een bron plus een put met `FONC_MULT`) |
| `radiationbc` | `RAYONNEMENT` σ = 5,670374419e-8 (schaalvlak: `SOUR_NL`, getabelleerd per 5 °C) |
| verlijmd contact (`contact2`) *Tie* / *Constraint equations* | `AFFE_CHAR_THER` `LIAISON_MAIL`: de temperatuur van elke slave-knoop is die in het geprojecteerde punt op het master-vlak (manual §9.9.1); ook niet-conforme meshes en schalen (`PLAN`) onderling |
| verlijmd contact *Elastic* (thermische weerstandslaag, *Thermal conductance per unit area* h) | `AFFE_CHAR_THER` `ECHANGE_PAROI` `COEF_H` = h tussen de vlakken van beide kanten (flux h·ΔT over de naad). Alleen volumevlakken die knoop op knoop tegenover elkaar liggen; anders (niet-conform, schalen, geen h) als ideaal verlijmd (`LIAISON_MAIL`) met een WARNING en in de lijst niet-vertaald |
| verlijmd contact in een model met volumes **en** schalen | **niet vertaald** (ERROR): Code-Aster kan dan geen `LIAISON_MAIL` (CHARGES7_6) of `ECHANGE_PAROI` (CHARGES6_2) leggen; gebruik gedeelde knopen (*Merge nearby nodes*) |
| `forcedconvection`, `massflowrate`, cavity-straling, formules voor convectie/straling op een schaalvlak, een formule in x, y, z voor een totale `heatflow` of als begintemperatuur, formules in materiaaleigenschappen | **niet vertaald** (gemeld) |

Een stationaire analyse met een tijdstabel neemt de waarde op t = 1 s, zoals Mecway
met CCX (Mecway's interne solver telt een tabel als 0; de bridge waarschuwt dan). Een
`temperature2` met een tijdsinterval (`starttime`/`endtime` ≠ 0) wordt de hele
analyse opgelegd (gemeld).

**Meer warmtebronnen met een formule of tijdstabel.** Code-Aster 17.4 rekent twee
lasten `AFFE_CHAR_THER_F` met `SOURCE` in één analyse allebei met de functie van de
**eerste** last (gemeten: twee helften met 2e6·t W/m³ en een tijdstabel gaven twee keer
de eerste). De bridge zet daarom alle bronnen met een functie (`heatgeneration`,
`heatflow` op elementen, `heatflux` op een schaalvlak, de bron van schaalvlak-convectie
met een tijdstabel en `#ASTER-LASBRON`) in **één** last. Overlappen bronnen (bijv. een
bron op het hele model en een op een deel), dan krijgt elk deel van het mesh een eigen
`FORMULE` met de som, want in één last overschrijft een latere `SOURCE`-regel op
hetzelfde element de eerdere. Een bron die nergens overlapt houdt zijn eigen groep en
functie. Twee functielasten met `FLUX_REP`, `ECHANGE` of `SOUR_NL` rekent Code-Aster
wel goed (gemeten); die blijven apart. Verificatie TH-40 .. TH-42.

**Verlijmd contact.** In een T31 met *Thermal stress* (keten thermisch → mechanisch)
krijgt het thermische deel de thermische koppeling hierboven en het mechanische deel
de gewone mechanische `LIAISON_MAIL` (TYPE_RACCORD, [Mecway_functionaliteit.md](Mecway_functionaliteit.md));
bij *Elastic* is de mechanische laag star (gemeld), de thermische weerstand wel
vertaald. Mecway's interne solver (Mecway 34, zonder GUI) rekende *Tie* en *Elastic*
in een T30 zonder koppeling (300 / 400 K aan beide kanten); met de CCX-solver wel
(350 K, en 340 / 360 K met h = 2000 W/m²K), gelijk aan de bridge (TH-04a/c).
### 3.1 Temperaturen in een mechanische analyse (thermische spanning)

In een statische, niet-lineair statische, modale of knikanalyse en in een niet-lineaire
dynamische respons geeft een *Thermal stress* (referentietemperatuur) samen met
temperaturen thermische rek (manual §9.23–9.25):

| Mecway | Code-Aster |
|---|---|
| *Thermal stress* | `VALE_REF` van `AFFE_VARC` `NOM_VARC='TEMP'` en `ALPHA` in `ELAS` |
| *Temperature* (`temperature2`) op knopen, vlakken of elementen | knoopveld `TEMP` (`CREA_CHAMP` `NOEU_TEMP_R` `AFFE`) |
| *Node temperature* (`temperature3`), ook het resultaat van *Transfer temperatures from solution* (manual §17.10) | dezelfde waarde per knoop in dat veld |

- Knopen zonder temperatuur staan op de referentietemperatuur, ook naast knopen met een
  temperatuur (zoals Mecway; Temperature en Node temperature op verschillende knopen
  tellen samen, LS-08c).
- De temperatuur wordt in het element geïnterpoleerd; een lineair verloop over de dikte
  geeft de exacte kromming (LS-08b, gelijk aan Mecway 34). Knopen die de bridge in de
  job toevoegt (`LINE_QUAD`, de middenknoop van `COQUE_3D`) krijgen de geïnterpoleerde
  temperatuur van de Mecway-knopen (LS-08d).
- Twee verschillende temperaturen op één knoop: Mecway rekent dan niet ("Conflicting
  temperatures on node"); de bridge geeft een WARNING en gebruikt de Node temperature
  (of bij twee Node temperatures de laatste).
- Modaal en knik: de voorspanning door de thermische rek telt mee (`modal_prestress`).
- Niet-lineair statisch (L30) en niet-lineaire dynamische respons (D31): het veld is een
  `EVOL_THER` (`CREA_RESU`) met de referentie op het eerste tijdstip, zodat de thermische
  rek vanaf de eerste stap spanning geeft (een veld dat al op t = 0 afwijkt, neemt
  Code-Aster als spanningsloze begintoestand, alarm `MECANONLINE2_97`). Daarna, zoals
  Mecway 34 met CCX in L30 (headless gezien):

  | Temperature | Met *Quasi-static* (`<timesteps>`) en in D31 | L30 zonder *Quasi-static* |
  |---|---|---|
  | constant (ook Node temperature) | volle waarde vanaf de eerste stap | lineair oplopend tot de eindtijd (Mecway toont alleen de eindtoestand) |
  | tijdstabel of formule in t | volgt de tabel: lineair tussen de punten, constant buiten het bereik; de knikpunten worden rekentijden | volgt de tabel tot t = 1 s en neemt daar de tabelwaarde (Mecway's staptijd) |

  Een formule in t wordt bemonsterd over de *Time period* (zoals Mecway, 10001 punten,
  0,01 %). Verificatie NL-70..75 en DY-70..72. In D31 is een plotselinge temperatuur een
  staplast (de staaf slingert om de nieuwe lengte, DY-72); laat de temperatuur met een
  tabel oplopen voor een quasi-statische opwarming (DY-71). Mecway rekent D31 headless
  niet (eigen solver en CCX); het gedrag in D31 is daarom niet tegen Mecway vergeleken.
- Statisch, modaal en knik met een tijdshistorie van een Temperature: weggelaten
  (WARNING), zoals Mecway's eigen solver (Mecway 34 headless: geen uitzetting, dezelfde
  frequentie en knikfactor als zonder temperatuur). Met CCX neemt Mecway in S30 de
  tabelwaarde op t = 1 s; gebruik daar een constante temperatuur.
- Dynamic Response (D30): Mecway negeert de temperaturen (headless gezien, ook met een
  tijdstabel); Temperature en Node temperature vallen ook in de bridge weg (INFO, DY-73).
  Nonlinear Dynamic Response (D31): Node temperature staat niet bij Mecway's
  analysetypen (manual §9.24) en wordt gemeld (ERROR, niet vertaald).

## 4. Aanvullende controles (Code-Aster 17.4, offline)

De reproduceerbare tests met tolerantie en bronnen staan in
[Verificatie.md](Verificatie.md) §8 (TH-01 .. TH-04, TH-40 .. TH-42). Daarnaast is de vertaling met de
hand gecontroleerd op deze modellen (analytische waarden volgens Incropera e.a.
(2007), hfdst. 3; ConductionConvectionRadiation volgens de Mecway-handleiding §11.13):

| Model | Verwacht | Code-Aster via de bridge |
|---|---|---|
| ConductionConvectionRadiation (schaal + volume; fin weggelaten) | T rechts 380,2783 K, q = 3591,65 W/m² (manual §11.13) | 380,278 K, 3591,65 W/m² in schaal en volume |
| staaf 0,1 m, 400/300 K, k = 50 | lineair, q = 50 000 W/m² | exact |
| idem, 1e6 W/m³ (`heatgeneration` en `heatflow` 10 W op de elementen), uiteinden 300 K | T_max = 325 K | 325,000 K |
| staaf als fin, h = 25 op zijkanten en eind | T(L) = 344,51 K, T(L/2) = 357,32 K | 344,47 / 357,28 K |
| schaal 2 mm, 1e6 W/m³ / 1000 W/m² op het vlak | 325 K / 312,5 K | 325,000 / 312,500 K |
| schaal, convectie h = 25 op één vlak | T(L) = 300 + 100/cosh(mL) = 339,48 K (fin, m = √(h/(k·t)), geïsoleerd uiteinde) | 339,42 K |
| schaal, convectie op de rand x = L | q = 2380,95 W/m², T(L) = 395,238 K | exact |
| schaal + volume (f = 0,01) in serie | zelfde warmtestroom in beide | 4,71 W in beide |
| staaf, `heatflow` 100 W 10 s, geïsoleerd | gemiddelde stijging 27,87 K | 27,87 K |
| staaf, convectie h = 1000 met tijdstabel T∞ | geconcentreerde capaciteit: ≈ 382,8 K na 20 s | 381,7–384,8 K |
| OscillatingHeatFlow (quad8-schaal, `heatflow`-tabel) | gemiddelde stijging Q/(ρcV) = 18,009 K | 17,998 K (t = 40 en 80 s) |

## 5. Vergelijking met Mecway's eigen thermische solver

Mecway rekent zonder GUI: `mecway.exe model.liml solve`, met
`<solutionfile filename="...\x_sol.liml" />` in de `.liml` (de oplossing bevat alleen
`temperature`, geen warmteflux). Gemeten met Mecway 33 (KNOWN_BUGS 14):

| Geval | Max. verschil bridge – Mecway |
|---|---|
| stationair: convectie, flux, heatflow, bron, randlasten, schaal + volume, ook één selectie over twee diktes en lasten op beide zijden | ≤ 1e-11 K |
| straling (tabel per 5 °C) | 1e-3 K |
| ConductionConvectionRadiation | 1,8e-6 K |
| `heatflow` op knopen (volume, twee diktes, gemengd) | ≤ 2e-12 K |
| schalen in het XZ-vlak en in een schuin vlak | ≤ 3e-12 K |
| stationair met tijdstabel, Mecway met CCX | 4e-4 K |
| transient, constante belasting, `theta` = 0,5 | 1,5e-5 K |
| OscillatingHeatFlow (1601 stappen), `theta` 0,57 / 0,5 / 1,0 | max 1,40 / 1,49 / 2,61 K (RMS 0,13 / 0,14 / 0,06 K) |
| tijdsafhankelijke convectie/straling op een schaalvlak, `theta` 0,5 | 0,10–0,21 K |
| verlijmd contact *Constraint equations*, niet-conform (volumes TH-04b, schalen TH-04d; Mecway 34) | 0,0024 / 0,0056 K |
| verlijmd contact *Tie* en *Elastic* (TH-04a/c), Mecway 34 met CCX | < 0,002 K |
| drie overlappende bronnen als formule, stationair (TH-40, Mecway 34) | 2e-12 K |
| twee bronnen in de tijd (formule + tabel, TH-41) en drie schaalvlak-fluxen (formule, tabel, overlappend), `theta` 0,5, Mecway 34 | 0,2 / 0,1 K: Mecway neemt de last op het einde van de stap; de gemiddelde stijging van Mecway is precies die van dat schema (2,875 / 2,075 K tegen exact 2,75 / 2,0 K) |

Mecway rekent transient Crank-Nicolson (θ = 0,5) met de belasting op het einde van
de stap; Code-Aster neemt het θ-gewogen gemiddelde. Bij een tijdstabel blijft
daardoor een verschil van de orde van de stap (met de tabel een halve stap verschoven
daalt OscillatingHeatFlow naar RMS 0,007 K). De standaard 0,57 blijft (gedempt;
Crank-Nicolson gaf in Mecway niet-monotone eerste stappen).

## 6. Aannames

- De berekening staat in °C (vanwege `RAYONNEMENT`); temperaturen gaan in K terug naar
  Mecway.
- Een schaal is een `PLAN`-laag met factor f = t / t_ref op λ, ρ·cp en de belastingen;
  er is geen temperatuurverloop door de dikte (zoals Mecway, manual §7.4).
- Stationair met een tijdstabel: de waarde op t = 1 s (zoals Mecway met CCX). Een
  `temperature2` met een tijdsinterval geldt de hele analyse.
- Knopen zonder begintemperatuur starten op 0 K (zoals Mecway).
- Een formule als waarde wordt in de Gauss-punten per stap uitgerekend (θ-gewogen); stationair met t = 1 s. Mecway's interne solver rekent de last op het einde van de stap (KNOWN_BUGS 14; [Lassen.md](Lassen.md) §5).
- Temperatuurafhankelijk materiaal: λ(T) en ρc(T) lineair tussen de tabelpunten, daarbuiten constant (zoals Mecway); de ρc-tabel wordt verfijnd zodat de enthalpie van `THER_NON_LINE` klopt ([Lassen.md](Lassen.md) §6).
- `heatflow` op knopen: Q/N per knoop (manual §9.27), verdeeld als bronveld.
- Straling op een schaalvlak is als functie van T getabelleerd per 5 °C (lineair
  geïnterpoleerd; verschil met Mecway ~1e-3 K, §5); convectie op een schaalvlak is
  exact (lineair in T).
- Transiente resultaten worden in enkele precisie geschreven (~3e-5 K bij 380 K).
- `theta` = 0,57 is een bewuste keuze (gedempt, geen overschieten bij een grove stap,
  [Verificatie.md](Verificatie.md) TH-02); 0,5 als Mecway exact gevolgd moet worden.

## 7. Bronnen

- EDF R&D (z.j.). *Code_Aster, documentatie versie 17.4*: U4.43.01 (`DEFI_MATERIAU`
  `THER`/`THER_NL`), U4.44.02 (`AFFE_CHAR_THER`), U4.54.01 (`THER_LINEAIRE`), U4.54.02
  (`THER_NON_LINE`). https://www.code-aster.org
- Incropera, F.P., DeWitt, D.P., Bergman, T.L. & Lavine, A.S. (2007). *Fundamentals of
  Heat and Mass Transfer* (6th ed.). Hoboken: Wiley.
- Mecway (2026). *Mecway-handleiding*, versie 33 (`manual.pdf` in de
  installatiemap). Verwezen als "manual §…".
