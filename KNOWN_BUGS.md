# KNOWN_BUGS.md – bekende fouten in de code (develop)

Fouten die gevonden zijn maar nog niet opgelost. Een nieuwe fout krijgt een
genummerd punt onder de juiste kop (het volgende vrije nummer, geschreven als `52\.`
zodat Markdown het niet hernummert; binnen een kop op nummer): bestand en functie, wat
er misgaat, en de status. Nummers worden niet hergebruikt, zodat verwijzingen
("KNOWN_BUGS 43") in code en docs blijven kloppen. Is een fout opgelost, haal het punt
dan in dezelfde commit weg en pas de verwijzingen aan.
Status: **bevestigd** = nagelopen in de code of met een offline run;
**vermoedelijk** = volgt uit de code, maar is niet gereproduceerd;
**vraag** = hangt af van gedrag van Mecway of Code-Aster dat niet in de repo staat.

Vergelijken met Mecway: zet in het startscherm "Eerst Mecway-solve ter controle" aan.
De bridge schrijft dan `WorkDir/<model>_<run-id>_vergelijking.csv` (Mecway- en
Code-Aster-waarde per knoop) en logt per variabele het grootste verschil.

## Afwijkingen van Mecway (gemeten)

1\. **Hex8 is stijver dan in Mecway** (bevestigd, `bridge_from_liml.py`
   MODELISATION='3D'). Mecway rekent hex8 met incompatibele modes (C3D8I in de
   CCX-export, "Incompatible hex8 elements" in de analyse-instellingen); Code-Aster
   heeft die niet. Gemeten met Code-Aster 17.4:
   - uitkragende balk 100x10x10 mm, 10 hex8 (1 dik), 100 N: Mecway 0.1892 mm,
     Code-Aster 0.1234 mm (analytisch 0.1905);
   - staaf 11 mm met plasticiteit (250 MPa): Mecway 0.251 mm, Code-Aster 0.039 mm
     (handberekening 0.251).
   `3D_SI` gaf de juiste verplaatsingen, maar buigspanning ~0 en foute REAC_NODA
   (onderintegratie). Oplossing als keuze: `elem_hex8` = "LINE_QUAD" (pagina
   Elementen) laat Code-Aster alle lineaire volume-elementen kwadratisch maken
   (CREA_MAILLAGE LINE_QUAD); dezelfde balk geeft dan 0.1886 mm. Alleen als verder
   niets lineair blijft (alleen volume-elementen, eventueel schalen met COQUE_3D) en
   niet expliciet; met de standaard "3D" waarschuwt de bridge bij hex8
   (`bridge_to_aster._resolve_line_quad`).
   Met LINE_QUAD blijven knoopkrachten op de hoekknopen staan: op hex20 zijn dat
   puntlasten met lokale vervorming (gezien in een klein hex20-testmodel: +21% op de
   belaste knopen, met druk op hetzelfde vlak +0,04%); gebruik een vlakbelasting.

2\. **Schaalelementen ~0,7% anders dan Mecway** (bevestigd). Vlakke quad4-plaat
   100x20 mm, 1 mm, ingeklemd op een rand: verplaatsingen DKT (Code-Aster) en
   Mecway verschillen 0,66%, rotaties tot ~10%. Keuze `elem_shell` = "COQUE_3D"
   (lineaire schalen via LINE_QUAD naar QUAD9/TRIA7, met drilling-rotatie) geeft
   0,03% / 0,83% op de verplaatsingen, de rotaties wijken vergelijkbaar af; geen
   formulering volgt Mecway exact. Bij een grof mesh is het verschil groter: wand
   1x1 m, 20 mm, 2x2 quad4, druk: DKT 8% meer doorbuiging dan Mecway (headless). COQUE_3D valt terug op DKT als de schalen knopen
   delen met elementen die lineair blijven (`bridge_to_aster._resolve_line_quad`).

3\. **Knoopspanningen en von Mises anders dan Mecway** (bevestigd in Mecway; bewuste
   keuze). De bridge volgt de Code-Aster-standaard: SIGM_NOEU (extrapolatie van
   SIEF_ELGA naar de knopen, gemiddeld) en SIEQ_NOEU (von Mises per element, daarna
   gemiddeld). Hex20-balk 100x10x10 mm met torsie en buiging: verplaatsingen en
   reacties gelijk, knoopspanningen aan het oppervlak tot ~12% lager dan Mecway; in
   het torsiecentrum geeft SIEQ_NOEU 7,5 MPa, Mecway (von Mises uit de gemiddelde
   tensor) 0,09 MPa. Niet "repareren" naar Mecway (wens gebruiker).

7\. **Spanningen per element-knoop blijven van Mecway in de tabelroute** (bevestigd
   in Mecway). Alleen bij `result_route` "tabel": `solution.set_variable()` schrijft
   alleen knoopwaarden, de `<elementnodevariable>` (o.a. `stressxx`) van de laatste
   Mecway-solve blijft staan. De standaardroute "liml" schrijft SIGM_ELNO/SIEQ_ELNO
   van volume-elementen wel mee (`bridge_to_aster._build_calc_champ_block`).

46\. **Knik: negatieve kniklastfactoren en Mecway's shift** (bevestigd met runs,
   `bridge_to_aster._calc_modes_block`). De bridge zoekt de kleinste |CHAR_CRIT|
   (`PLUS_PETITE`) en toont ook negatieve factoren (knik bij de omgekeerde last;
   WARNING). Mecway zoekt alleen positieve factoren boven zijn *Shift point*: een
   kolom onder trek gaf in Mecway 8,5e13 (zinloos), in de bridge -10,36 / -23,32 /
   -93,27 (de drukknik met minteken). Mecway's shift is een instelling van zijn
   oplosser en wordt niet gebruikt (alleen gemeld); zoeken rond een kniklastfactor
   kan niet (`OPTION='CENTRE'` negeert Code-Aster 17.4 bij knik). Starre modes van een
   vrij model krijgen in de bridge een frequentie van ~1e-4 Hz, soms negatief
   (numeriek nul); Mecway schrijft 0 of een klein positief getal.

60\. **Isotroop materiaal zonder Young's modulus: bridge E = 210 GPa, Mecway E = 0**
   (vermoedelijk, `bridge_from_liml.py`, materiaalblok: `youngsmodulus` met standaard
   "210000000000"). Gezien met headless Mecway op een Frequency-model waarvan een
   materiaal alleen *Speed of sound* en *Density* had: modes van ~1e-7 Hz (E = 0). De
   bridge rekent zo'n materiaal stil als staal; alleen met een geluidssnelheid (een
   fluidum) geeft hij buiten `vibroacoustic_modes_3d` een WARNING
   (`bridge_vibroacoustic.parse_vibro`). Zonder geluidssnelheid NIET nagelopen.

62\. **Sterk gekromde hex20/wedge15: frequenties tot 0,8% hoger dan Mecway** (vraag,
   gemeten met Mecway's voorbeeld Impeller, 66 hex20 + 21 wedge15 met middenknopen tot
   18% van de ribbelengte buiten het midden). De sector als gewoon modaal model
   (`modal_3d`, zonder centrifugaalkracht en cyclische symmetrie) gaf +0,02 ... +0,79%
   t.o.v. Mecway (6 modes); de cyclische route (S10g) wijkt evenveel af (+0,01 ...
   +0,92%). Bij rechte hex20 is de bridge gelijk aan Mecway (MP-07, CY-01, CY-05).
   Vermoedelijk een andere integratie van vervormde kwadratische elementen in Mecway
   of Code-Aster (NIET nagegaan; welke dichter bij de werkelijkheid ligt, ook niet).

95\. **Thermische rek in schalen: Mecway zet minder uit dan de bridge** (vraag, gemeten
   met Mecway 34 headless en Code-Aster 17.4). Plaat 100 × 40 × 2 mm (4 × 2 elementen),
   `fixed` op de rand x = 0, α = 1,2e-5 1/K, uniform +100 K (`temperature2` op alle
   elementen of `temperature3` op alle knopen, in beide programma's hetzelfde): max u_x
   quad8 Mecway 6,68e-5 m, bridge (`COQUE_3D`) 1,224e-4 m; quad4 Mecway 9,37e-5 m,
   bridge (DKT) 1,236e-4 m. De vrije uitzetting is αΔT·L = 1,2e-4 m (de ingeklemde rand
   verhindert alleen de dwarsrek, wat u_x eerder vergroot). Een vrije quad8-plaat met
   ΔT = 1000 K/m · x gaf in Mecway u_x(L, 0) = 4,87e-5 m tegen exact αgL²/2 = 6,0e-5 m.
   Volumes kloppen wel (TH-03, LS-08). Waarom Mecway bij schalen minder uitzet, is NIET
   nagegaan (vlakspanning of de temperatuur over de dikte?).

## Vertaling die anders werkt dan Mecway

8\. **Dubbele randvoorwaarden** (bevestigd, deels afgevangen). Mecway reduceert
   overlappende voorwaarden zelf (manual v33 par. 9.6), Code-Aster niet. Opgelost:
   fixed naast schuine voorwaarden, displacement, node rotation of velocity
   (SANS_GROUP_*, `bridge_to_aster._build_charges`); contact-slaves
   (`_exclude_fixed_slaves`); een DDL_IMPO 0 die al onder een symmetry/frictionless 0
   in dezelfde globale richting valt (`bridge_mesh._drop_covered_ddl`). Twee DDL_IMPO
   in dezelfde last: Code-Aster neemt de laatste (alleen gemeld bij verschillende
   waarden). Gemeld met selecties en DOF's, niet opgelost (`_report_constraint_overlaps`,
   rangtest per knoop): constant naast tijdsafhankelijk op dezelfde DOF (ASSEMBLA_26),
   pinned support, koppelingen, frictionless/symmetry onderling met verschillende
   relaties en schuine overlap.

9\. **Bezwijken niet voor balken; kinematische versteviging met de huidige plastische
   rek** (bevestigd; `bridge_failure.py`, `docs/Bezwijken.md`). Code-Aster verwijdert
   geen elementen; de bridge geeft bezweken elementen (plastische rek boven
   `#ASTER-BEZWIJKEN`, PLAS_TAB Eps_p_max of `failure_plastic_strain`) een zeer lage
   stijfheid en spanning nul, in STAT_NON_LINE en DYNA_NON_LINE. Dat werkt voor
   volume-elementen (PETIT, GDEF_LOG, SIMO_MIEHE) en schalen (DKT: PETIT/GREEN_LAGRANGE;
   COQUE_3D: PETIT/GROT_GDEP), met als criterium het gemiddelde over alle
   integratiepunten, bij schalen ook over de subpunten in de dikte. Niet gedaan
   (melding + skipped_loads): balken (Code-Aster kent plasticiteit alleen in
   multivezelbalken, POUTRE0_61). Bij `VMIS_CINE_LINE` komt de rek uit de terugspanning
   (X = 2/3 H εp, H = Mecway's tangent modulus): dat is de huidige, niet de opgetelde
   plastische rek (WARNING), en zonder versteviging (tangent modulus 0) bezwijkt er
   niets. OpenRadioss `/FAIL`: alleen
   /FAIL/JOHNSON met een vaste breukrek (D4=D5=0, D2·D3=0) in het materiaalveld wordt
   Eps_p_max; andere /FAIL-kaarten en /FAIL in de model definition worden gemeld.
   Dynamisch alleen gecontroleerd op de uitvoertijden; impliciet geeft het alarm
   MECANONLINE4_50.

10\. **Contactparen met gedeelde slave-knopen worden samengevoegd** (bevestigd,
   `bridge_mesh._merge_contact_zones`). Code-Aster verbiedt gedeelde slave-knopen
   tussen zones (CONTACT2_16); de bridge maakt er een zone van (master = unie,
   slave = unie, grootste wrijvingscoefficient) en logt dat.

11\. **Grote rotaties: balken, opgelegde rotaties en starre koppelingen** (bevestigd).
   Met `deformation` = GROT_GDEP kiest de bridge per elementtype een vorm voor grote
   verplaatsingen (`_deformation_for`). Niet: balken (POU_D_E blijft PETIT; POU_D_T_GD
   met ELAS_POUTRE_GR convergeerde al slecht bij een starre draaiing), DDL_IMPO op
   DRX/DRY/DRZ en LIAISON_SOLIDE (met TYPE_CHARGE='SUIV' niet als een knoop rotatie-
   vrijheidsgraden heeft, CHARGES_36). Werkt wel: een star deel aandrijven met de
   exacte starre beweging via #ASTER (FORMULE, docs/ASTER_regels_voorbeelden.md
   voorbeeld 9). Een buigmodel (profiel om een mal, met een rol) is zo impliciet tot 90 graden gerekend; het
   contact rol/profiel convergeert daar nog moeizaam (rol grof als slave: WARNING).

14\. **Thermisch: transient schema anders dan Mecway** (bevestigd, `bridge_thermal`,
   `theta`). Mecway 33 rekent Crank-Nicolson met de belasting op het einde van de
   stap (headless gemeten: `mecway.exe model.liml solve` met `<solutionfile>`);
   Code-Aster neemt het θ-gewogen gemiddelde (standaard 0,57). Bij constante
   belasting geeft θ = 0,5 Mecway tot 1,5e-5 K; met een tijdstabel blijft een
   O(Δt)-verschil (OscillatingHeatFlow max 1,4 K bij θ 0,57, RMS 0,13 K). Stationair
   met een tijdstabel: Mecway's interne solver telt de tabel als 0, CCX neemt t = 1 s;
   de bridge neemt t = 1 s en waarschuwt bij de interne solver. Met een bewegende bron
   (formule in x, y, z, t) loopt Mecway's bron daardoor v·Δt/2 voor: naast de bron
   +4,6%, op de lasas erachter −2,1% t.o.v. de bridge bij Δt = 0,05 s (WE-03; de
   bridge ligt binnen 1% van de analytische oplossing).

15\. **Thermische schalen als PLAN met een diktefactor** (bevestigd, keuze).
   Code-Aster's thermische `COQUE` heeft drie temperaturen door de dikte en
   randbelastingen alleen op TRIA; de bridge rekent schalen als `PLAN` (diepte 1)
   met f = t / t_ref op λ, ρc en de belastingen, per dikte een eigen deelgroep.
   Schalen in evenwijdige vlakken buiten Z = constant: de .comm draait het mesh
   (MODI_MAILLAGE ROTATION) en de flux terug; alarm MODELE1_53 blijft en is
   onschuldig. Schalen die niet allemaal evenwijdig zijn: niet vertaald (punt 16).

17\. **Thermische rek: temperatuur in het element en in de tijd** (bevestigd, bewuste keuze,
   `bridge_to_aster._build_temperature_field`). Volgens de manual (v33 par. 9.25) rekent
   Mecway per element met de gemiddelde knooptemperatuur; Mecway 34 (eigen solver,
   headless) interpoleert de knooptemperatuur echter in het element, net als
   Code-Aster: een lineair temperatuurverloop over de dikte van een vrije balk (één
   laag hex20) geeft in beide de exacte doorbuiging (zie LS-08b), met `temperature2` op
   knoopselecties en met `temperature3`. Het verloop in de tijd (L30, D31: `EVOL_THER`
   vanaf de referentie, constant vanaf de eerste stap of oplopend zonder Quasi-static,
   een tijdstabel gevolgd) staat in docs/Thermisch.md par. 3.1 (NL-70..75, DY-70..72).
   Statisch, modaal en knik: een tijdshistorie valt weg, net als in Mecway's eigen
   solver (Mecway 34 headless); Mecway met CCX neemt in S30 de waarde op t = 1 s.

19\. **Centrifugaalkracht** (bevestigd). Alleen een constante hoeksnelheid (een
   tijdshistorie wordt gemeld), geen tweede centrifugaalkracht (gyroscopisch effect).
   Spin softening (Mecway: automatisch in Nonlinear Static): ROTATION met
   TYPE_CHARGE='SUIV' in STAT_NON_LINE bij grote vervormingen, alleen als ROTATION
   alleen op volumes staat (getest: staaf 0,1 m, extra reactie = ρAω²∫u). Met schalen
   (formules van de beginpositie) en in dynamica blijft de last vast. Zonder schalen
   ROTATION op de elsets, in een model met schalen formules per elset
   (FORCE_INTERNE/FORCE_COQUE/FORCE_POUTRE); knoopmassa's krijgen FORCE_NODALE m w^2 r
   (`bridge_to_aster._centrifugal_loads`). Kabels (tension only) krijgen nooit
   centrifugaalkracht (CALCUL_37 "MECABL2", geen FORCE_POUTRE voor kabels): ERROR en
   gemeld. In een model met schalen krijgen andere elementen met dichtheid (geen
   volume, schaal of balk) hem ook niet (gemeld).

20\. **Meerdere verdeelde lasten op een balk** (bevestigd,
   `bridge_to_aster._prepare_beam_loads`). Code-Aster telt lasten met een verdeelde
   balklast (CALCULEL2_92, ook in CALC_CHAMP SIPM_ELNO). De bridge verdeelt de balken
   in disjuncte groepen (BRLP) met de som; met een tijdsafhankelijke line pressure
   alles in één AFFE_CHAR_MECA_F (gravity op balken als ρAg, elders als kracht). Nog
   niet: lokale en globale line pressure op dezelfde balk en centrifugaal met een
   tijdsafhankelijke line pressure (ERROR), gravity met historie samen met line
   pressures op balken (WARNING). FORCE_INTERNE/FORCE_COQUE in dat pad zijn niet met
   een run nagelopen.

21\. **Verlijmd contact (LIAISON_MAIL)** (bevestigd, `bridge_mesh._bonded`).
   `bondedelastic` wordt star verlijmd (stijfheid niet vertaald, gemeld). Schaalvlak
   (slave) op volume (master): alleen de verplaatsingen worden gekoppeld (MASSIF;
   gemeten gelijk aan gedeelde knopen). Mecway wijkt hier zelf af (headless gemeten,
   balk 1x0,1x0,1 m met een plaat van 10 mm erop verlijmd, eindlast): de interne
   solver verbindt de plaat niet (plaat in rust, doorbuiging gelijk aan zonder
   plaat); met CCX daalt de doorbuiging tot 0,869 van die zonder plaat, Code-Aster
   (LINE_QUAD + COQUE_3D) 0,788, balktheorie 0,785. Schaalranden van één component op een
   volume: COQUE_MASSIF (stijf, ook de rotaties); randen van meerdere componenten of
   gemengd met vlakken: MASSIF, de rand werkt dan als scharnier (WARNING). Of Mecway
   een schaalrand op een volume ook stijf verbindt is NIET geverifieerd. Balkuiteinden als slave:
   gemeld en overgeslagen. Lineaire schalen die master zijn, blijven DKT, ook met
   elem_shell = COQUE_3D (LIAISON_MAIL trekt anders de DX van de QUAD9-middenknoop
   erbij, CHARGES2_31, en de middenknopen van LINE_QUAD kent de bridge niet; WARNING).
   Een automatische
   tolerantie van Mecway (0) wordt geen DISTANCE_MAX: Code-Aster koppelt alle
   slave-knopen, ook ver van het master-vlak. Schaal op schaal (`COQUE`, ook een
   schaalrand op een schaalvlak) koppelt de rotaties wel (stijf, LS-07); Mecway's eigen
   solver doet dat bij een schaalrand als slave niet (headless gemeten, Mecway 34:
   verlijmde strook en T-stuk van LS-07 worden een mechanisme, tip 3,7e6 m). Een
   kwadratische schaal (tri6/quad8) als master of een scheve/gekromde master schrijft
   de bridge zelf als `LIAISON_DDL` per slave-knoop (`_bonded_relations`; LS-07f..k);
   bij een scheve of gekromde master zet de bridge `NPREC` voor die run op −1 (WARNING),
   omdat MUMPS anders ten onrechte `FACTOR_11` meldt (fictieve drilling-stijfheid).
   Die relaties projecteren elke slave-knoop op de master-elementen (voorselectie met
   omhullende dozen; 500 slave-knopen op 3600 elementen: 1,3 s in CPython, in
   IronPython enkele keren trager): bij heel grote lijmvlakken merkbaar.

22\. **Compression only** (bevestigd). Hard (LIAISON_UNIL, zoals de interne solver),
   alleen in niet-lineaire analyses (MECA_STATIQUE stopt met een ERROR), niet in een
   model met contact2 (een DEFI_CONTACT per berekening; gemeld). Op schaalvlakken
   alleen de normaalverplaatsing, de rotaties blijven vrij.

23\. **Gap- en tension-only-elementen** (bevestigd). Gap (DIS_CHOC): geen trek-gap
   (U tegen knoop 1 -> 2 in), schuine U of samenvallende knopen (gemeld, element
   zonder stijfheid); de 'force of open gap' van CCX wordt niet gebruikt. Tension
   only (CABLE, GROT_GDEP): drukstijfheid 1e-4 E (Code-Aster EC_SUR_E), een kabel
   zonder voorspanning heeft geen dwarsstijfheid. Beide alleen niet-lineair.

34\. **PLAS_TAB: niet vertaalde velden** (bevestigd, `bridge_radioss.parse_plas_tab`).
   Kinematische/gemengde versteviging (C_hard > 0; 0 is isotroop, Altair /MAT/LAW36),
   Eps_t/Eps_m/Eps_f, fct_IDp en de E-evolutie (Fct_IDE/EInf/CE) worden gemeld
   (WARNING) en isotroop gerekend; F_smooth/F_cut/VP (reksnelheid) alleen INFO. Een
   ander eenhedenstelsel (`/BEGIN`, of E/RHO buiten het SI-bereik) wordt gemeld, niet
   omgerekend. Kinematisch met een curve: VMIS_ECMI_TRAC is alleen exact bij een
   bilineaire curve, dus niet ingebouwd.

40\. **Trusses bij grote verplaatsingen** (bevestigd met runs, `bridge_from_liml`
   `_split_trusses`). BARRE is in Code-Aster 17.4 geometrisch lineair: GROT_GDEP wordt
   stil genegeerd (een staaf die star 30° draait, geeft dezelfde normaalkracht als met
   PETIT); de bridge waarschuwt. Samples/SaggingCable.liml (rechte kabel onder dwarse
   gravity) is daardoor een mechanisme: de run stopt (singulier, BRIDGE_ONVOLLEDIG). CABLE met EC_SUR_E=1.0 is wel een geometrisch
   niet-lineaire staaf (gemeten: starre rotatie N=0), maar zonder voorspanning blijft
   een rechte kabel singulier; met N_INIT=2000 N gaf SaggingCable 3,06797 m (Mecway
   3,0680 m). Niet ingebouwd.

43\. **Contact: harde en zachte formulering verschillen van Mecway** (bevestigd).
   `contact_algo` = STANDARD (Lagrange, standaard) laat geen penetratie toe; Mecway
   rekent penalty. Samples/PipeClip verliest met STANDARD het contact (1,1 mm penetratie
   op t = 0,8), AssemblyWithContact (Fixed_support) stopt met MECANONLINE9_4 (pivot op
   LAGS_C); met PENALISATION (Mecway's stijfheid) volgen beide Mecway (2..8% en −1,1%,
   headless). Configuratie Quadratic_ramp van AssemblyWithContact (wrijving 0,5 +
   elastic support) convergeert ook met penalty niet in stap 1 (onverklaard).
   Lijncontact tussen hex20-volumes (verificatie NL-03a: twee balken met de tips
   op elkaar) lukt met STANDARD niet: met de standaard INTEGRATION='NCOTES' (bridge,
   kwadratisch slave-vlak) dringt de rand tussen de integratiepunten door (contactkracht
   ~0) en stopt de run bij t = 0,028 met MECANONLINE9_4; met AUTO een pivot op LAGS_C
   van een hoekknoop in de eerste stap, ook met master/slave omgedraaid. PENALISATION is
   exact (NL-03b).

48\. **Modaal: mechanisme in een opgelegd model** (bevestigd met runs,
   `bridge_to_aster._calc_modes_block`). Is K singulier terwijl er wel opleggingen
   zijn (bijv. een balk die alleen scharnierend vastzit), dan stopt Code-Aster met
   `<EXCEPTION> ALGELINE3_81`; Mecway geeft de starre modes met 0 Hz (zelfde model:
   Mecway 0 / 0 / 0,0007 / 73,277 / 109,916 / 237,467 Hz). De bridge gebruikt de
   verschoven zoekfrequentie alleen zonder enige oplegging (vrij-vrij); met een
   negatieve `modal_shift_hz` (bijv. -500 Hz) geeft de bridge dezelfde waarden als
   Mecway. Altijd verschuiven werkt niet: een vaste factor ver boven de eerste mode
   gaf bij een fijn hex20-mesh geen enkele mode (ALGELINE5_49/3_78).

53\. **Niet-lineaire knik: grenzen van CRIT_STAB en de imperfectie** (bevestigd met
   runs, `bridge_to_aster._crit_stab_kind`, `_imperfection_blocks`;
   docs/Modaal_en_knik.md par. 5). Mecway kent geen van beide (eigen invoer).
   (a) Met grote verplaatsingen (de standaard voor volumes en COQUE_3D; één elset is
   genoeg) is `CHAR_CRIT` van CRIT_STAB geen lastfactor maar −(kleinste eigenwaarde
   van K_T); de bridge schat het knikpunt lineair uit de laatste twee stappen (NK-02a,
   laatste stap op 0,9 Pcr: +0,4 %; dezelfde kolom met de laatste stap op 0,27 Pcr:
   +4,7 %, de reeks is licht gekromd). SIMO_MIEHE NIET
   geverifieerd. (b) De imperfectie is altijd de lineaire knikvorm onder de lasten op
   de eindtijd (meebewegende druk daar als vaste last); niet met contact, compression
   only, gaps of tension only (ERROR), niet in dynamica. (c) Balken en DKT/DST blijven
   geometrisch lineair: daar versterkt de imperfectie niet (WARNING). (d) De
   verplaatsingen in Mecway zijn t.o.v. de imperfecte vorm; de imperfectie zelf gaat
   niet als veld naar Mecway, de knikvorm van CRIT_STAB (`MODE_FLAMB`) ook niet.
   (e) Geen boogslengtemethode (`PILOTAGE`): met een last als tijdstabel stopt de run
   op het grenspunt (`MECANONLINE9_7`, NK-04).

70\. **Twee thermische functielasten met SOURCE rekenen als de eerste** (bevestigd met
   een Code-Aster-run, Code-Aster 17.4; `bridge_thermal.add_charge`). Staan twee
   lasten `AFFE_CHAR_THER_F` met `SOURCE` (een `FORMULE` of `DEFI_FONCTION`) in één
   lijst (`EXCIT` van `THER_LINEAIRE`/`THER_NON_LINE`, ook `CALC_VECT_ELEM`), dan rekent
   Code-Aster beide met de functie van de **eerste** last: twee constante `FORMULE`s
   (1e9 en 2e9 W/m³) op verschillende groepen gaven 2 × 960 W in plaats van 960 + 135 W;
   omgekeerd 2 × 135 W. Een `AFFE_CHAR_THER` met constante `SOURCE`, een constante
   naast een functie, of één last met twee `SOURCE`-regels rekent wel goed. Gevolg:
   twee Mecway-*Internal heat generation*s met een formule of tijdstabel (route B van
   docs/Lassen.md) geven de verkeerde warmte. `#ASTER-LASBRON` met meer bronnen had
   hetzelfde (de tweede bron werkte als een kopie van de eerste) en zet sinds stap S4c
   alle bronnen in één last (`bridge_welding._merged_load`); naast een lasbron geeft een
   Mecway-formulebron een WARNING. Open: de Mecway-formulebronnen ook samenvoegen
   (per deel van het mesh de som); of `FLUX_REP`, `ECHANGE` en `AFFE_CHAR_MECA_F` het
   ook hebben, is NIET nagegaan.

82\. **Niet-lineair: heen-en-weer-plasticiteit met de standaardvervorming convergeert
   niet bij het terugbelasten** (bevestigd met een offline run, `bridge_to_aster.
   _deformation_for`; gevonden bij S8b). Staaf 0,1 × 0,01 × 0,01 m, 2 hex8, bilineair
   plastisch (vloeigrens 250 MPa, tangentmodulus 10 GPa), opgelegde verlenging 0 →
   +0,6 → −0,6 → 0 mm (t = 0..3 s, stap 0,25 s), symmetrievlakken (model van VM-11a
   zonder `deformation = PETIT`): met de standaard `GROT_GDEP` (plastisch volume →
   `GDEF_LOG`) stopt `STAT_NON_LINE` op t = 2,29 s (`MECANONLINE9_7` na 7 keer
   halveren, `BRIDGE_ONVOLLEDIG`); met `PETIT` rekent dezelfde staaf door (VM-11a).
   Oorzaak niet gezocht (GDEF_LOG bij het omkeren van de rek, of de Newton-instellingen).
   Advies in docs/Vermoeiing.md §1.9: `deformation = PETIT` bij heen-en-weer-plasticiteit.

83\. **XFEM: K_I uit `CALC_G_XFEM` op een gekromd front een paar procent te hoog**
   (bevestigd met runs, Code-Aster 17.4; `bridge_xfem._warn_curved`; verificatie BR-10).
   Cirkelvormige scheur (penny crack, a = 20 mm) in een blok onder trek, hex8, front
   schuin door de elementen: K_I van `CALC_G_XFEM` (`OPTION='CALC_K_G'`) in het midden
   van het front +5,3 % t.o.v. 2σ√(a/π) bij h = a/20, +10 % bij a/10 en +15 % bij a/5;
   op hetzelfde mesh K_I van `POST_K1_K2_K3` +1,6 % en K uit G +1,0 %
   (docs/Breukmechanica.md §7.4). Op een recht front (BR-07..09, BR-12) ligt
   `CALC_G_XFEM` binnen 0,3 %. Oorzaak vermoedelijk de ontbrekende krommingscorrectie
   van de interactie-integraal (de gemeshte scheur heeft die met `FORM_FISS='CERCLE'`:
   forma07a +5,6 % → +0,1 %); dat `CALC_G_XFEM` geen krommingscorrectie kent, is NIET
   in de U-doc nagegaan. De bridge geeft bij CIRKEL/ELLIPSE een WARNING en adviseert
   `K1_POST_K` of K uit G. In de verificatie toetst BR-10 deze K_I met dezelfde 5 % als
   de andere XFEM-controles; de afwijking telt als BEKEND.


106\. **Flexible joint: voorwaarde op een elementselectie, grote rotaties**
   (bevestigd resp. vermoedelijk, `bridge_mesh._flexible_joints`). Het balkuiteinde met
   een joint krijgt een eigen knoop op dezelfde plaats, met `LIAISON_DDL` aan de
   Mecway-knoop gekoppeld (verificatie LS-51, gelijk aan Mecway). (a) Een vaste
   voorwaarde (fixed, displacement, ...) op een *elementselectie* of component die het
   element met de joint bevat, legt in Code-Aster (`GROUP_MA`) ook die eigen knoop vast;
   samen met de koppeling is dat dubbel en Code-Aster stopt met `FACTOR_11` (gezien in
   een run: fixed op de eindelementen, joint op een eindvlak). Leg de voorwaarde op
   knopen of vlakken (dan alleen op de Mecway-knoop, zoals Mecway). Oplossing (NIET
   geverifieerd): de eigen knopen als `SANS_GROUP_NO` bij voorwaarden op `GROUP_MA`.
   (b) De koppeling van de rotaties ligt vast in de lokale assen van het onvervormde
   element: bij grote rotaties (`GROT_GDEP`) draaien de assen niet mee (niet
   gereproduceerd; Mecway kent de joint niet in Nonlinear Static, manual v33 par. 9.12).

107\. **Line3-balken: twee rechte SEG2-cellen** (bevestigd, keuze;
   `bridge_mesh.write_mesh`). Code-Aster heeft geen kwadratisch balkelement; elk
   line3-element wordt in de middenknoop gesplitst. Een gekromd line3-element (middenknoop
   niet op de koorde) wordt zo een knik van twee rechte stukken, met per helft een eigen
   oriëntatie; Mecway (alleen met CCX, B32R) rekent de gekromde vorm. Voor een rechte
   balk exact (verificatie LS-50). Mecway's CCX-uitkomst zelf ligt 2–3 % onder de
   Euler-theorie (B32R uitgezet als één C3D20R over de doorsnede; dezelfde balk met line2
   in Mecway's eigen solver is exact); een ronde staaf (SECTION=PIPE met binnenstraal 0)
   rekent CCX daar niet ("nonpositive jacobian").

## Open vragen (gedrag van Mecway niet nagegaan)

27\. **Niet geverifieerd in een .liml** (vraag). Constraint equation: `constant`
   (element of attribuut; de bridge leest beide) en de DOF-namen rx/ry/rz (afgeleid
   uit de stringvolgorde in mecway.exe); rotational inertia: as 1/2 = X/Y (alleen 3 = Z
   gezien); meer dan één knoop geeft een ERROR (mecway.exe: "can only be applied to a
   single node"). Rayleigh-demping alleen op het hele model en niet op discrete
   elementen (Mecway: α op elke knoop met massa, manual par. 9.26). Bevestigd: de
   Rayleigh-XML (DampedVibratingStrip) en de gap-attributen
   `initialclearance`/`openforce` (mecway.exe).

37\. **Tweede run in dezelfde sessie: `solution` na `mw.open`** (vraag,
   `MecwayAsterBridgeMain`). Het hoofdvenster blijft open, dus een tweede run gebruikt
   de `solution` die Mecway bij de start van het script gaf, terwijl run 1 het model
   met `mw.open` opnieuw opende. Alleen van belang voor route `tabel` en "Eerst
   Mecway-solve ter controle" (vergelijking). Of Mecway dat object meeverhuist staat
   niet in de API-documentatie; bij twijfel de bridge opnieuw starten.

38\. **Hoofdvenster niet-modaal: NIET in Mecway geverifieerd** (vraag, `bridge_gui`).
   Het venster gebruikt `Show()` met een eigen berichtenlus (`Application.DoEvents`),
   zodat Mecway bruikbaar blijft terwijl het open is. Op welke thread Mecway scripts
   draait en of Mecway tijdens die lus alles toestaat (bijv. een ander model openen,
   het script nog eens starten: de bridge weigert een tweede venster) is niet getest.

41\. **Expliciet: TCHAMWA met een variabele stap niet nagelopen** (vraag,
   `bridge_to_aster._explicit_accelerations`). In expliciete dynamica (alleen
   `FORMULATION='ACCELERATION'`) zet de bridge opgelegde verplaatsingen, rotaties,
   snelheden, frictionless (`FACE_IMPO`, `LIAISON_OBLIQUE`) en de constante van een
   constraint equation om naar de versnelling die het schema oplegt (DIFF_CENT:
   DY-03b, DY-20a-c). De TCHAMWA-reeks is afgeleid voor een vaste stap; met
   verschillende stappen per interval (knikken die geen veelvoud van de stap zijn) is
   ze NIET met een run nagelopen.

47\. **Veren en dempers: niet tegen een Mecway-oplossing vergeleken** (vraag). De bridge
   zet k en c langs de eigen as van het element (DISCRET `REPERE='LOCAL'`; voorheen
   werkten ze in globaal X, ook langs Y: verificatie LS-06, nu exact). Dat volgt
   Mecway's CCX-export (`*ELEMENT,TYPE=SPRINGA` = axiale veer, string in mecway.exe).
   Headless kon Mecway een met de hand geschreven veer (line2 + Spring-materiaal) niet
   rekenen: de interne solver negeerde hem (doorbuiging gelijk aan zonder veer; een
   losse veer gaf een singulier stelsel) en CCX gaf geen oplossing. Te controleren
   met een veer die in de Mecway-GUI is gemaakt.

## Niet vertaald (de bridge meldt het aan het eind van de run)

4\. **Belastingen en randvoorwaarden die de bridge niet kent** (bevestigd). Ondersteund
   zijn fixed, pinnedsupport, frictionless, displacement, noderotation, velocity
   (dynamica), force, moment, surfacepressure, gravity, traction, linepressure,
   hydrostaticpressure, elasticsupport, compressiononly, symmetry, centrifugal,
   mass2, rotationalinertia, constraintequation, flexiblejoint, rayleighdamping,
   temperature2 met
   thermalstress, nodesurfacecoupling (rbe3/rigidbody), contact2 (unilateraal en
   verlijmd, geen self-contact), materialen Gap/Damper/TensionOnly en een
   beginsnelheid; OpenRadioss-materiaal PLAS_TAB (`bridge_radioss.py`); in de
   akoestiek fluidpressure 0 (`bridge_acoustic.py`, punt 55). Andere tags
   met een selectie (self-contact, cyclic symmetry buiten een modale analyse (punt
   61), pre-tension, ...),
   OpenRadioss-kaarten behalve /FUNCT (o.a. /RBODY, /BCS, /IMPDISP), andere
   OpenRadioss-wetten en VOID-materialen komen in `model_data["skipped_loads"]`.
   Via `#ASTER`-regels kan de gebruiker zelf Code-Aster-commando's toevoegen.

5\. **Belastingen op balkzijvlakken en frictionless met verplaatsing op gekromde
   schalen** (bevestigd). Druk en traction op schaalranden (lengte × dikte, in het
   schaalvlak) en balkuiteinden (doorsnede A) worden knoopkrachten; frictionless op
   gekromde schaalvlakken en schaalranden wordt LIAISON_OBLIQUE per knoopnormaal
   (`bridge_mesh._edge_loads`, `_frictionless_per_node`). Headless tegen Mecway:
   druk op een schaalrand exact gelijk, traction dwars op de rand 0,5% (DKT, punt 2);
   frictionless per knoopnormaal niet tegen Mecway gerekend. Nog niet: lasten op het zijvlak van een balk (gebruik
   een elementselectie), frictionless met normaalverplaatsing ≠ 0 op gekromde
   schalen/schaalranden, hydrostatische druk op schaalranden. Met LINE_QUAD krijgen
   nieuwe middenknopen geen frictionless.

6\. **Kinematische versteviging: geen equivalentplasticstrain; niet-lineaire
   kinematische curve** (bevestigd). Vertaald: isotrope hardingscurve
   (VMIS_ISOT_TRAC), BilinearIsotropic/-Kinematic (ECRO_LINE met
   D_SIGM_EPSI = E H/(E+H), H = Mecway's tangent modulus als plastische modulus;
   VMIS_ISOT_LINE/VMIS_CINE_LINE, ideaal plastisch met tangent modulus 0),
   RambergOsgood (bemonsterde curve, VMIS_ISOT_TRAC; incrementeel, bij ontlasten
   anders dan CCX) en een Kinematic-curve met lineaire versteviging (VMIS_CINE_LINE,
   `bridge_from_liml._kinematic_curve`). Een niet-lineaire Kinematic-curve wordt
   gemeld en elastisch gerekend. Bij kinematische versteviging gaat geen
   equivalentplasticstrain naar Mecway (VARI V1 is daar de terugspanning), wel
   EPSP_NOEU. Plasticiteit op balken wordt elastisch gerekend (WARNING; Code-Aster kent
   plasticiteit alleen in multivezelbalken). ('Simple' is geen plasticiteitstype maar
   het type van `<density>`.)

16\. **Thermisch: niet vertaald** (bevestigd, `bridge_thermal.py`). Balken /
   fin-elementen (Code-Aster heeft geen thermisch 1D-element; FinConvection.liml
   draait daarom niet), schalen die niet allemaal evenwijdig zijn, vloeistofnetwerk
   (`forcedconvection`, `massflowrate`; CoolantChannel.liml stopt met "temperatuur
   onbepaald"), cavity-straling, formules voor convectie/straling op een schaalvlak,
   een formule in x, y, z voor een totale `heatflow` of als begintemperatuur, formules
   in materiaaleigenschappen, contact en koppelingen in een thermische analyse. Een
   `temperature2` met `starttime`/`endtime` wordt de hele analyse opgelegd. (Formules
   in de overige thermische lasten en temperatuurafhankelijke λ/c worden wel vertaald,
   docs/Thermisch.md par. 3.)

45\. **Formules in x, y, z bij mechanische lasten** (bevestigd,
   `bridge_bcs._formula_value`). Thermisch opgelost: daar wordt elke formule een
   `FORMULE` van X, Y, Z, INST (`bridge_thermal.Formula`, `bridge_bcs.aster_expression`;
   WE-06 gelijk aan Mecway, WE-03 bewegende bron). Mechanisch: een waarde als
   formule in t wordt een tijdshistorie (zoals Mecway voor CCX: 10001 monsters, punten
   met <= 0,01% afwijking); plaatsafhankelijke formules (bijv. druk `3*y^2`) worden
   gemeld (ERROR) en niet meegenomen. Mogelijk: AFFE_CHAR_MECA_F met FORMULE(X,Y,Z)
   (dezelfde vertaling als thermisch).
   Lineair statisch neemt de bridge f(eindtijd); Mecway intern negeert een last in t,
   CCX neemt f(0). Elk functiepunt wordt in STAT_NON_LINE een rekenstap (met Mecway's
   stapgrootte) of een interval met substeps_per_interval stappen (zonder stapgrootte;
   `bridge_to_aster._build_listinst_block`): een sinus geeft honderden punten en dus
   honderden tot duizenden stappen. Waarden die `bridge_from_liml` met
   `parse_and_convert(findtext(...))` leest (bijv. `referencetemperature`) zouden een
   constante formule (getal met unit-attribuut) als SI lezen, als Mecway daar ooit een
   formule schrijft (NIET gezien).

49\. **Modaal: grenzen van de voorspanning en van de complexe modes** (bevestigd
   met runs, `bridge_to_aster._prestress_plan`). Voorspanning door belastingen
   (stress stiffening, `modal_prestress`) werkt zoals Mecway (verificatie MP-01..07).
   Afwijkingen: (a) een draaiende **balk** (`POU_D_E`, centrifugal) geeft in het
   rotatievlak tot 0,5% lagere frequenties dan Mecway (MP-04: 20,795 tegen 20,903 Hz;
   een eigen FE-berekening met consistente Hermite-matrices gaf 20,918 Hz), uit het
   vlak gelijk, met hex20 ook in het vlak gelijk (MP-07): vermoedelijk Code-Aster's
   `RIGI_ROTA` van balken (NIET geverifieerd in de broncode). (b) Centrifugaalkracht
   met **schalen** (formule-last, geen `ROTATION`) of op **knoopmassa's**: geen spin
   softening (WARNING). (c) Een **membraan met kunstmatig kleine E** (Mecway's
   VibratingMembrane: E = 0,001 Pa, tri6 → `COQUE_3D`): de rotatievrijheidsgraden
   zonder stijfheid geven valse modes (0,33 en 2,04 Hz, effectieve massa 0) en
   Sorensen vindt met `PLUS_PETITE` geen mode (`ALGELINE5_49`); met zoekfrequentie
   2 Hz komt de trommelmode 2,00746 Hz (Mecway 2,00746), met de valse modes ertussen.
   Demping: standaard niet (zoals Mecway, headless gemeten: V30 negeert Rayleigh en
   geeft met een Damper geen oplossing); met `modal_complex` complexe modes
   (`bridge_modal_damping.py`, verificatie MC-01..05). Grenzen daarvan: alleen de vorm
   (reëel deel) naar Mecway, geen spanningen per mode; overkritisch gedempte en starre
   modes ontbreken (ALGELINE5_79); bij dempers (niet-proportioneel) is de effectieve
   massa uit het reële deel een benadering (MC-03: som 107%); geen hysteretische
   demping; de `decayrate` en f_d in de Mecway-GUI NIET bekeken (de API leest f_d en de vorm).
   Cyclische symmetrie: punt 61. De effectieve
   massa voor de rotaties rekent de bridge zelf (om de oorsprong, zoals Mecway; fractie
   van de totale traagheid incl. opgelegde knopen, Mecway deelt door de vrije); in
   Mecway (*modal effective mass (fraction)*, S12) staat daarom Code-Aster's fractie,
   niet Mecway's; of de GUI de eigen variabele `cumulativeeffectivemassfraction*`
   toont, is NIET geverifieerd (Mecway bewaart hem wel); spanningen per mode
   alleen bij modaal (`fields`), niet per knikvorm.

51\. **Foutschatter: alleen lineair statisch en volume-elementen** (bevestigd,
   `bridge_to_aster._error_estimator_block`, `bridge_mesh._free_faces`,
   docs/Foutschatter.md). `CALC_ERREUR` ERME alleen bij `MECA_STATIQUE` en alleen op
   volume-elementen; niet bij niet-lineair, dynamica, modaal, knik en thermisch (ERTH),
   niet op schalen en balken. In de schatter ontbreken: puntlasten (`FORCE_NODALE`, ook
   een moment op vlakken), lasten op schalen/balken/schaalranden en hydrostatische druk
   (formule); daar en op een overgang volume → schaal/balk is de rand voor de schatter
   spanningsvrij (geschatte fout te groot). Vlakken met symmetry, frictionless of
   elastic support hebben geen randterm (zoals een opgelegde rand). Twee vlaklasten van
   dezelfde soort op een vlak: de schatter neemt er een mee (WARNING). Een vlak telt als
   opgelegd als al zijn hoekknopen in een knoopselectie van een opgelegde verplaatsing
   liggen, ook als die maar een richting vastlegt. Bij een (vrijwel) spanningsloos
   model is de globale relatieve fout betekenisloos (TH-03a: 64%). `FORCE_FACE` telt
   in `ERME` met het omgekeerde teken (gemeten); de bridge keert het om in de last van
   de schatter (`_erme_force_face`), alleen de normaalcomponent telt in de randterm.
   De adaptieve verfijning erft deze grenzen (punt 65).

54\. **Respons op modale basis en harmonische respons: grenzen** (bevestigd,
   `bridge_dyna_modal.py`, `bridge_harmonic.py`, docs/Respons_op_modale_basis.md).
   Mecway D30 met Mode superposition wordt `CALC_MODES` + `DYNA_VIBRA` GENE
   (verificatie MD-01..07, gelijk aan Mecway). Niet vertaald (ERROR met de oplossing
   `dyna_impl_3d`): een opgelegde verplaatsing of rotatie <> 0, ook met een
   tijdstabel (vraagt statische modes / `MULT_APPUI`), een beginsnelheid
   (`ETAT_INIT` op modale basis), thermische rek, dempers (Mecway ook niet) en
   uitvoertijden die niet op een regelmatig raster vanaf 0 liggen. Versnellingen en
   reacties gaan niet naar Mecway. Lasten uit `#ASTER-EXCIT` tellen alleen als
   oplegging (in `ASSEMBLAGE`). De statische correctie (`static_correction`) is met
   een constante last exact (MD-06b) en met een tabel alleen buiten de regressie
   gemeten (console, 1 mode, sinus op 0,5 f1: 0,13% t.o.v. 12 modes, zonder
   correctie 2,0%).
   Harmonische respons (`harmonic_3d`, eigen analyse: Mecway heeft geen harmonisch
   analysetype; verificatie HR-01..05): niet vertaald (ERROR) een opgelegde
   (basis)beweging <> 0, dempers op modale basis (wel met `harm_basis` PHYS),
   `modal_damping` met PHYS, thermische rek en niet-lineaire onderdelen; niet
   gebouwd: hysteretische demping (`AMOR_HYST`, verliesfactor), spanningen in
   schalen en balken (alleen verplaatsingen/rotaties), reacties en element-
   knoopspanningen. Zonder demping en met een lijst valt een frequentie mogelijk op
   een (oneindige) resonantie; de bridge waarschuwt alleen dat er geen demping is.
   Een gelijkmatige basisversnelling als gravity (relatieve beweging) is theorie, NIET
   met een testcase nagelopen. Mecway-GUI: de frequenties komen als `<mode
   frequency>` met o.a. `displx`/`displix`/`displamp*`/`displphase*`; Mecway's API
   leest ze (headless script op HR-02a), de weergave in de GUI (lijst *Mode 1..n*,
   contour, animatie zonder decay rate) is NIET bekeken (vraag).

55\. **Akoestiek: 2D, acoustic displacement en media met verschillende dichtheid niet
   vertaald; grenzen van de impedantie** (bevestigd, `bridge_acoustic.py`,
   `aster_acoustic_complex.py`, docs/Akoestiek.md §3). Holtemodes met harde wanden en
   drukknopen (*fluid pressure* 0) zijn gelijk aan Mecway (verificatie AK). *Impedance*
   (S2b): complexe modes met frequentie, *decay rate* en `pressure`/`pressurei` (het
   kwadratische eigenwaardeprobleem met scipy in de job, omdat `CALC_MODES` `MATR_AMOR`
   alleen als `matr_asse_depl_r`/`gene_r` neemt); gelijk aan Mecway ≤ 1e-8 en aan de
   analytische buis (verificatie AI). Grenzen: een frequentieafhankelijke Z niet (ook
   Mecway niet); de lijst modes kan op de 0-Hz-modes van Mecway verschillen (Mecway laat
   ze door afrondingsruis willekeurig weg, de bridge geeft ze altijd een keer); de schaal
   van P is anders (Mecway willekeurig, de bridge P^H M P = 1); geen Code-Aster-resultaat
   (geen MED-export, `#ASTER-POST` heeft geen `res`); de factorisatie (scipy `splu`) is
   gemeten tot 13 000 knopen (14 s), grotere modellen NIET geverifieerd (geheugen).
   Mecway's API leest de modes (headless script: `modes()`, `frequency`, `node_value`
   van `pressure`/`pressurei`; de decay rate heeft geen API). De
   weergave van de complexe modes in de Mecway-GUI (decay rate onder *Solution*,
   animatie van `pressure` + `pressurei`) is NIET bekeken (vraag). Ook niet:
   Acoustic Resonance 2D (A20, ERROR), Mecway's *acoustic displacement* als veld, contact,
   koppelingen en constraint equations in de akoestiek (ERROR, skipped_loads), piramides.
   Code-Aster's `RIGI_ACOU`/`MASS_ACOU` bevatten de dichtheid niet (gemeten): op een
   grensvlak is dp/dn continu, juist alleen bij gelijke dichtheid; media met
   verschillende dichtheid: ERROR. Mecway-GUI: het veld `pressure` per mode is headless
   met Mecway's eigen oplossing vergeleken, NIET in de GUI bekeken.

56\. **Responsspectrum: grenzen** (bevestigd, `bridge_spectrum.py`,
   `aster_spectrum.py`, docs/Spectrumanalyse.md). Mecway heeft geen spectrumanalyse;
   de bridge rekent hem op een Frequency-model met een Gravity-tabel als spectrum
   (analyse `spectrum_3d`, zelf kiezen: `auto` kiest bij V30 `modal_3d`). Niet
   vertaald: een spectrum per steunpunt (`MULT_APPUI`, `ENVELOPPE`), opgelegde
   verplaatsingen <> 0 of met een tabel (ERROR), belastingen (vervallen, WARNING),
   snelheden, spanningen op schalen en balken (alleen volume-elementen; INFO), en een
   spectrum dat met de demping varieert uit een gravity-tabel (dan `#ASTER-SPECTRE` met
   een `DEFI_NAPPE`). von Mises is per mode berekend uit `SIGM_NOEU` en gecombineerd
   (bij CQC een bovengrens), alleen per knoop (geen element-knoopwaarde). De
   resultaatstap staat als statisch resultaat onder een V30-analyse: Mecway's API leest
   de waarden (headless nagelopen: `node_value`, `modes()` leeg); de weergave in de
   Mecway-GUI is NIET geverifieerd (vraag).

57\. **Akoestiek harmonisch: grenzen** (bevestigd, `bridge_acoustic.py`
   `build_acoustic_harm`, `aster_acoustic_export.py`, docs/Akoestiek.md par. 5.6).
   Gebouwd en geverifieerd (AH-01..08): snelheidsbron (`BRON_`, `#ASTER-BRON`),
   opgelegde druk, drukknopen, rho-c-rand (`ABSORBEREND_`) en een reele impedantie
   (Mecway *impedance*, `3D_ABSO` met `CELE_R = Z / rho`). Niet: een **complexe
   impedantie** (Im Z != 0; `CELE_I` op het `3D_ABSO`-vlak gaf voor c = 340(1 + i) een
   staande-golfverhouding 2,19 waar Z = rho c (1 + i) 2,62 geeft, en -340 gaf 2,29: de
   betekenis van `CELE_I` in `AMOR_ACOU` is NIET uitgezocht) en een
   frequentieafhankelijke impedantie: ERROR. Mogelijke route (NIET uitgezocht): per
   frequentie zelf `COMB_MATR_ASSE` (K - w^2 M + i w (rho/Z) A) en `RESOUDRE`, zoals
   het "calcul decompose" van ahlv100a, of zoals de complexe holtemodes (S2b,
   `aster_acoustic_complex.py`: A = int N N dA met `AMOR_ACOU` en `CELE_R = 1`, dan
   scipy in de job; Z mag dan ook per frequentie verschillen). Ook niet: volumedemping / complexe
   geluidssnelheid, een puntbron, microfoons op vlak- of elementselecties (WARNING),
   `#ASTER-EXCIT` (WARNING), koppeling met een constructie (daarvoor
   `vibroacoustic_modes_3d` en `vibroacoustic_harm_3d`, punt 59). Een **resonantie**
   zonder absorberende rand geeft een (bijna) singuliere matrix; de bridge waarschuwt
   alleen dat er geen absorptie is, niet welke frequentie op een holtemode valt.
   Mecway-GUI: de frequenties komen als `<mode frequency>` met de velden `pressure`,
   `pressurei`, `pressuremag`, `pressurephase`, `spl`; Mecway's API leest ze (headless
   script, `solution.modes()`, `node_value(.., mode=m)`), maar de weergave in de GUI
   (lijst *Mode 1..n*, contour, animatie van een complexe "mode" zonder decay rate) is
   NIET bekeken (vraag).

59\. **Vibro-akoestiek: gekoppelde modes en harmonische respons; grenzen** (bevestigd,
   `bridge_vibroacoustic.py`, `bridge_vibroacoustic_harm.py`, docs/Akoestiek.md §6.6 en
   §7.6). Gebouwd en geverifieerd: (a) gekoppelde modes (VA-01..05c) van een
   constructie (volumes, schalen) en een fluidum (`3D_FLUIDE` + `FLUI_STRU`, `U_P_PHI`)
   op een Mecway Frequency-model, koppelvlakken automatisch of met `KOPPEL_`, p = 0 met
   `OPEN_`; (b) de harmonische respons (`vibroacoustic_harm_3d`, VH-01..08:
   `DYNA_VIBRA` `HARM` `PHYS` met `MATR_IMPE_PHI`) met belastingen op de constructie,
   snelheidsbronnen (`BRON_`, `VITE_FACE`), een invallende golf (`INVALLEND_`,
   `ONDE_FLUI`), `#ASTER-BRON` (snelheid of druk), absorberende randen (`ABSORBEREND_`,
   reele Mecway-impedantie, `3D_FLUI_ABSO`), Rayleigh-demping (alleen de constructie)
   en dempers, microfoons en meetpunten. Niet: twee fluida met gedeelde knopen en een
   **verschillende dichtheid** (gemeten fout: 188,23 i.p.v. 306,47 Hz; ERROR); een
   schaal met fluidum aan beide kanten (ERROR); impedantie en *fluid pressure* != 0 in
   de modes (ERROR); in de harmonische respons een **complexe of
   frequentieafhankelijke impedantie** en *fluid pressure* != 0 (ERROR), volumedemping,
   `AMOR_HYST`, `modal_damping`, een basisbeweging (ERROR), spanningen in schalen en
   balken, reacties; voorspanning, zwaartekracht op een vrij oppervlak (klotsen);
   effectieve massa per mode; modes onder `vibro_freq_min` (ook starre modes).
   `ONDE_FLUI` en `3D_FLUI_ABSO` zijn exact voor loodrechte inval (schuin: deels
   reflectie, NIET gemeten). NIET geverifieerd: `elem_hex8` = `LINE_QUAD` met een
   fluidum, bonded contact tussen fluidum en constructie, wedge/tet/piramide-fluidum
   (alleen hex8/hex20 getest), kwadratische schalen (`COQUE_3D`, QUAD9) op een
   hex20-fluidumvlak (de middenknoop van de schaal doet dan niet mee in de koppeling),
   meer bronnen met verschillende fase tegelijk (elk apart wel: VH-02t, VH-07, VH-08).
   Mecway-GUI: de velden per mode (`displ`, `pressure`, headless script op VA-01) en per frequentie
   (`displx`/`displix`, `pressure`/`pressurei`/`spl`, headless script op VH-02) leest
   Mecway's API; de weergave in de GUI (contour, animatie, lijst *Mode 1..n* van een
   harmonische respons) is NIET bekeken (vraag). Een mechanisme in de constructie
   (bijv. een schaal met maar een rotatie vast) kan `CALC_MODES BANDE` minder modes
   laten vinden dan de Sturm-telling (WARNING met het aantal).

58\. **Lasbron: grenzen** (bevestigd, `bridge_welding.py`, docs/Lassen.md).
   `#ASTER-LASBRON` (Goldak dubbel-ellipsoïde, verificatie WE-01..05) werkt alleen in
   een transiente thermische analyse (T31) en alleen op volume-elementen; een baan is
   recht of stuksgewijs recht door de knopen van `pad` (de keten wordt op afstand
   gebouwd: een pad dat dicht langs zichzelf terugloopt kan verkeerd geordend worden,
   NIET getest), met constante snelheid. Zonder `geboorte=` is de rups vanaf t = 0
   aanwezig; toevoegmateriaal dat geboren wordt heeft eigen grenzen (punt 71). Meer
   bronnen staan in een last (punt 70: twee functielasten met SOURCE rekent Code-Aster
   als de eerste). Geen latente warmte (via c(T)); de
   mechanische keten heeft eigen grenzen (punt 64). De formule wordt per Gauss-punt in Python uitgerekend:
   met een grote brongroep (route B op het hele model) duurt dat lang (WE-02: 9 700
   elementen in de brongroep, 60 stappen, ~2 min; met THER_NON_LINE, WE-05, ~9 min).
   De energiecontrole rekent op vijf tijdstippen, niet per stap.

61\. **Cyclische symmetrie: grenzen** (bevestigd met runs, `bridge_cyclic.py`,
   `aster_cyclic.py`, docs/Modaal_en_knik.md par. 7). Vertaald: Mecway *Cyclic
   symmetry* in een *Frequency*-analyse (V30) met `MODE_ITER_CYCL` (verificatie
   CY-01..06: volledig model en Mecway <= 0,03%). Niet:
   (a) cyclische symmetrie in statisch, niet-lineair statisch en thermisch: ERROR en
   skipped_loads, het model rekent als losse sector (Mecway kan het wel; voor de
   voorspanning bouwt de bridge de relaties van ND 0 al, `_relations`);
   (b) schalen, balken, veren en `LINE_QUAD` (ERROR; Mecway staat schalen en balken
   in een Frequency-analyse ook niet toe);
   (c) een gedeeltelijke oplegging of relatie op een snijvlakknoop (ERROR; Mecway
   staat axiaal verplaatsen en een radiale 0 toe): de interfaces van
   `MODE_ITER_CYCL` hebben per knoop dezelfde vrijheidsgraden;
   (d) 8 segmenten met knopen op de as: Code-Aster 17.4 stopt met `ALGORITH14_95`
   (`bibfor/algorith/ctetax.F90` draait de vector (1, 1, 1) van actieve
   vrijheidsgraden over 45 graden: cos - sin = 0, dus "ontbreekt" DX); de bridge
   geeft een ERROR (oplossing: klein gat op de as);
   (e) een dubbele eigenwaarde binnen ND 0 (ring-mode met n = N golven): de tweede
   +1,3% (CY-01 met 3-4 modes per ND, ook met 80 sectormodes); in ND N/2 ging het
   goed. NIET uitgezocht waarom (inverse iteratie van MODE_ITER_CYCL);
   (f) bij een X- of Y-as: lasten met een functie of formule, `LIAISON_OBLIQUE` en
   `ANGL_NAUT` (ERROR); `#ASTER`-code rekent in het gedraaide frame (WARNING);
   (g) naar Mecway het hele wiel zoals Mecway's eigen oplossing (S10i, instelling
   `cyclic_full_wheel`, standaard aan; zelfde knoop- en elementnummers, headless
   nagelopen), maar van een paar alleen het eerste lid (welke staande golf, dus de stand
   van de knooplijnen, is willekeurig en kan van Mecway's keuze verschillen) en alleen
   verplaatsingen (geen spanningen per mode, geen complexe modes, geen effectieve massa,
   die Mecway ook niet geeft). Lukt het skelet van Code-Aster niet, dan gaat alleen de
   sector naar Mecway (WARNING in de `.mess`; NIET voorgekomen in CY-01..06).
   De schaal van de vormen is die van `REST_SOUS_STRUC` (`modal_norm` geldt niet; Mecway
   normeert anders). De weergave in de Mecway-GUI is NIET bekeken (de API leest het
   wiel, de modes en de waarden, headless). De hoogste modes per ND hangen af van
   `cyclic_base_modes`.

63\. **Breukmechanica: alleen lineair statisch, geen veld, geen kwartpunten** (bevestigd,
   `bridge_fracture.py`, docs/Breukmechanica.md). Gebouwd en geverifieerd (BR-01..06):
   K_I/K_II/K_III en G langs een gemeshte scheur (`SCHEUR_`-selecties) met `CALC_G`
   en `POST_K1_K2_K3` na `MECA_STATIQUE`, in de log, het statusvak en
   `<model>_<run>_scheur.csv`. Niet: (a) niet-lineair statisch, dynamica en
   thermische modellen (WARNING, geen K/G); (b) contact op de lippen (een scheur onder
   druk geeft overlappende lippen en K_I < 0: WARNING); (c) K/G als veld in Mecway
   (alleen de tabel); (d) kwartpuntknopen (`MODI_MAILLAGE NOEUD_QUART`): de bridge
   verplaatst geen knopen, want de resultaatexport controleert de coördinaten tegen
   de `.liml` (`aster_results_export._check_node_order`); met kwartpunten in de
   `.liml` zelf werkt het wel (BR-04), maar Mecway kan ze niet maken. Zonder
   kwartpunten is `POST_K1_K2_K3` met hex20 3-5 % en met hex8 9-14 % te laag
   (`CALC_G` < 1 % resp. 2 % op K); (e) XFEM (`#ASTER-XFEM`, `bridge_xfem.py`,
   S6b, BR-07..12; docs/Breukmechanica.md §7): alleen lineair statisch en alleen
   volume-elementen met MODELISATION `3D` (ERROR anders); geen contact op de lippen,
   geen scheurgroei (`PROPA_FISS`); K uit `CALC_G_XFEM` heeft op een gekromd front
   geen krommingscorrectie (BR-10: +5 %; WARNING, gebruik `POST_K1_K2_K3` of G);
   naar Mecway gaan alleen knoopvelden (verplaatsing en spanning via `POST_CHAM_XFEM`
   + `PROJ_CHAMP`, geen `SIGM_ELNO`); een knoop precies op het scheurvlak krijgt de
   waarde van één lip; `REAC_NODA` op knopen van gesneden elementen is alleen het
   klassieke deel (NIET geverifieerd); foutschatter en vermoeiing niet samen met XFEM
   (WARNING); tet10/wedge15/pyr13 en `groep=` (`GROUP_MA_ENRI`) NIET geverifieerd,
   `LINE_QUAD` alleen buiten de regressie (BR-07 met LINE_QUAD: K_I 0,0 %), `result_route`
   `tabel` NIET geverifieerd; een scheur uit een `XFEM_`-vlakselectie (BR-13) ligt
   altijd op een knooplaag; een gekromd scheurvlak of front, tet- en kwadratische
   elementen uit een selectie NIET geverifieerd; (f) een scheur op
   een grensvlak tussen materialen, thermische rek en druk op de lippen in `CALC_G`:
   NIET geverifieerd; (g) een krom front dat geen cirkel is: K uit `CALC_G` zonder
   krommingscorrectie (WARNING; forma07a zonder correctie +5,6 %). In de Mecway-GUI
   NIET nagelopen: het openen van een scheur met *Disconnect elements* en *Merge
   nearby nodes* met een knoopselectie (manual v33 par. 4.2.10/4.2.11) en de tekst in
   het statusvak.

64\. **Lassen: grenzen van de keten thermisch → mechanisch** (bevestigd,
   `bridge_thermomech.py`, docs/Lassen.md §9). Alleen in een transiente thermische
   analyse (T31 met een Thermal stress) en alleen met volume-elementen (ERROR bij
   schalen, balken, veren); contact en koppelingen rekent de keten niet. De
   mechanische stappen zijn de thermische (één Mecway-*Time step*, ook voor het
   afkoelen). Zonder `geboorte=` is de rups vanaf t = 0 aanwezig en draagt mee
   (toevoegmateriaal dat geboren wordt: punt 71); metallurgie alleen
   met `#ASTER-METALLURGIE` (punt 72), geen herstel van de versteviging boven de
   smelttemperatuur; de hardingscurve
   (`TRACTION`) is niet temperatuurafhankelijk, alleen bilineair via `#ASTER-MATERIAAL`.
   Lineaire hex8 ('3D') 'locken' bij plastisch vloeien: WE-10 gaf σxx in de las
   1,3–2,6 × SY (boven–onder) en σzz 190 MPa midden in een plaat van 5 mm (WARNING, advies
   LINE_QUAD). Met LINE_QUAD en plasticiteit convergeerde Newton alleen met
   lijnzoeken (`RECH_LINEAIRE`, nu altijd bij plasticiteit) en duurt een stap ~35 s
   CPU op 2 000 hex20 (WE-10b, ~1 uur; niet in de standaardregressie). `GDEF_LOG`
   in de keten en kinematische versteviging met temperatuurafhankelijke ET: NIET
   geverifieerd. Of Mecway's GUI Thermal stress, Fixed support en Displacement in een
   T31-model laat toevoegen of tonen: NIET nagelopen (headless bewaart en negeert
   Mecway 33 ze, WE-08).

65\. **Adaptieve verfijning: grenzen** (bevestigd, `bridge_adapt.py`,
   docs/Foutschatter.md §6). Alleen lineair statisch en alleen volume-elementen (de
   foutschatter, punt 51). Mecway's `refine_x2` maakt na een paar lussen slechte
   overgangselementen: bij dunne elementen (dikte 1/40 van de breedte) in lus 2, bij
   tet10 al in lus 1; de globale schatting stijgt dan en de lus stopt (WARNING). Ook in
   AD-02 zakt de slechtste hex20 naar 0,04 (WARNING) zonder dat de fout stijgt.
   Knoopselecties met een voorwaarde verfijnt Mecway niet mee: ERROR vóór het
   verfijnen (AD-03). HOMARD (`MACR_ADAP_MAIL`) is niet gebouwd: het nieuwe mesh kan
   niet terug naar Mecway. Elke lus vraagt een OK-klik na Code-Aster. De lus in de
   Mecway-GUI is NIET nagelopen, alleen headless (`mecway.exe <model> script`).

66\. **Vermoeiing: grenzen (volumes en schalen, Miner, kritiek vlak alleen op
   volumes)** (bevestigd, `bridge_fatigue.py`, `aster_fatigue.py`, docs/Vermoeiing.md).
   Gebouwd en geverifieerd (VM-01..11): schade en levensduur per knoop met
   `#ASTER-WOHLER` (tabel, machtsvorm, Basquin, Manson-Coffin), rainflow (periodiek
   zoals `POST_FATIGUE`, of ASTM E1049) en Miner, op blokken of een signaal bij lineair
   statisch of de tijdstappen van `STAT_NON_LINE`/`DYNA_NON_LINE`; schalen op de boven-
   en onderzijde (`SIEQ_NOEU` van `POST_CHAMP EXTR_COQUE`); multiaxiaal met
   `CALC_FATIGUE FATIGUE_MULTI DOMA_NOEUD` (Dang Van, Matake, Crossland, eigen formule;
   sslv135a). Niet: (a) balken (WARNING); schalen met een rekcurve of een criterium
   (WARNING, schalen overgeslagen); (b) multiaxiaal per Gauss-punt (`DOMA_ELGA`),
   Papadopoulos (alleen via `criterium = FORMULE` met `RAYSPH`), Fatemi-Socie
   (`FATESOCI_MODI_AV`), `COEF_PREECROU`, `INST_INIT_CYCL`, constanten a/b/c per
   materiaal (nu voor alle materialen gelijk); rek: geen Morrow/SWT-correctie en geen
   vermoeiingsgrens, Taheri, Lemaitre; trillingsvermoeiing (`FATIGUE_VIBR`) en random
   (`POST_FATI_ALEA`); in respons op modale basis, harmonisch en spectrum alleen een
   WARNING; (c) schade per element-knoop (alleen knoopgemiddelde spanning; op een grens
   van twee materialen de grootste van de twee curves); (d) een filter op kleine cycli
   (`DELTA_OSCI`); (e) het kritieke vlak zoekt Code-Aster op een raster van normalen:
   bij Matake SIGEQ +0,06 % t.o.v. de handberekening (VM-09c), bij Dang Van −2·10⁻⁶;
   multiaxiaal kopieert de bridge het hele niet-lineaire/dynamische resultaat
   (`CREA_RESU`, zodat t = 0 meetelt), bij een groot model met veel tijdstappen het
   dubbele geheugen voor `SIGM_NOEU`/`EPSI_NOEU` (NIET gemeten);
   (f) `PROL_GAUCHE`/`PROL_DROITE` `LINEAIRE` trekt de bridge log-log door, Code-Aster's
   `POST_FATIGUE`/`CALC_FATIGUE` lineair in (S, N) (gemeten; boven de tabel daar zelfs
   negatieve schade), dus buiten de tabel wijkt de bridge bewust af van Code-Aster.
   Bij een tijdsverloop staan `damage`/`life` in elke tijdstap met dezelfde waarde
   (Mecway's API leest ze, headless); de weergave in de Mecway-GUI is NIET bekeken
   (vraag). De geschiedenis staat in het geheugen als knopen × tijdstappen (float64);
   de rainflow per knoop is Python (gemeten buiten Code-Aster: 20 000 knopen × 200
   stappen met ruis, 1,26 miljoen cycli, 3,3 s); een groot dynamisch model in een echte
   run is NIET gemeten.

72\. **Lassen: grenzen van de metallurgie** (bevestigd met runs, `bridge_metallurgy.py`,
   docs/Lassen.md §10). `#ASTER-METALLURGIE` werkt alleen in een transiente
   thermische analyse (T31) en alleen op volume-elementen; alleen het staalmodel
   `ACIER` (geen ontlaten `ACIER_REVENU`); mechanisch alleen `META_P_IL` (geen
   kinematische versteviging, viscoplasticiteit of transformatieplasticiteit
   `META_PT`) en niet met `elem_hex8 = LINE_QUAD` (ERROR). Gemeten gedrag van
   `CALC_META` (Code-Aster 17.4), oorzaak niet uitgezocht: (a) bij snel opwarmen met
   een grote temperatuurstap per tijdstap loopt de austenitisering achter op de
   tijdconstante (1000 °C/s: 4 °C per stap exact, 40 °C per stap ~8× trager; de
   bridge meldt knopen die ruim boven Ac3 kwamen maar < 90% austeniet werden; advies
   bij lassen `TAUX_1=TAUX_3=0.001`); (b) de martensietvorming stopt bij ~0,4–0,7%
   austeniet, ook waar Koistinen-Marburger verder gaat (MT-02); (c) 16MND5 vormt bij
   200 °C/s nog 3% bainiet, hoewel de snelste TRC-geschiedenis met omzetting
   80 °C/s is. Dataset 16MND5 (mtlp103a) heeft geen mechanische gegevens per fase:
   `ALPHA_A`, `DEPS` en de vloeigrens per fase geeft de gebruiker (MT-07 rekent met
   illustratieve waarden). Of Mecway de velden `ferrite` .. `hardness` per tijdstap
   toont: NIET in de Mecway-GUI nagelopen.

71\. **Lassen: toevoegmateriaal dat geboren wordt, grenzen** (bevestigd, `bridge_welding.
   _births`, `birth_materials`, `ther_loop`, `bridge_thermomech._birth_solve`;
   docs/Lassen.md §11). `geboorte=` in `#ASTER-LASBRON` is de "quiet element"-methode
   (Code-Aster 17.4 kent geen element birth): stil = ρ·c × 1e-4, λ × 1e-8, E × 1e-4
   (vaste factoren), de bron niet in stil materiaal; verificatie WE-11..13. Grenzen:
   (a) de geboorte volgt de booglengte langs de baan (niet de afstand tot de boog) en
   is per element en per tijdstap: spanningsvrij op de temperatuur van het begin van de
   geboortestap; (b) bij de geboorte neemt een element de temperatuur van zijn knopen
   over; die op het grensvlak zijn al warm: +1,2..1,6% energie in WE-11; (c) het
   toevoegmateriaal rekent thermisch met een diagonale warmtecapaciteit (`3D_DIAG`;
   met de consistente capaciteit volgde een stil knooppunt via de massakoppeling zijn
   warme buren, WE-13 +138 K); (d) met λ(T)/c(T) of straling (`THER_NON_LINE`) en in de
   keten een solve per geboortestap (langere rekentijd); (e) de plastische rek en
   versteviging van het stille element gaan bij de geboorte naar nul; (f) alleen
   volume-elementen, elk element bij hoogstens één bron; (g) `GDEF_LOG` en
   kinematische versteviging met geboorte: NIET geverifieerd; (h) Mecway's eigen solver
   kent geen geboorte (geen vergelijking met Mecway); de weergave van stille elementen
   in de Mecway-GUI is NIET nagelopen.
