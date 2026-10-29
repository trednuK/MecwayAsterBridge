# Mecway-functionaliteit in de bridge

*English version: [Mecway_features.md](en/Mecway_features.md)*

Welke Mecway-invoer de bridge naar Code-Aster vertaalt. Per regel staat de status:
**Ja** (vertaald), **Deels** (vertaald met een beperking) of **Nee** (niet vertaald).
De opmerking noemt de beperking, het nummer in [`KNOWN_BUGS.md`](../KNOWN_BUGS.md) (KB)
en, bij Deels en Nee, wat je in plaats daarvan kunt doen. Een `#ASTER`-regel is eigen
Code-Aster-invoer in Mecway's *Custom model definition*
([`ASTER_regels_voorbeelden.md`](ASTER_regels_voorbeelden.md), "voorbeeld n").

Wat de bridge niet vertaalt, meldt hij met een ERROR in de log en in de lijst
overgeslagen onderdelen aan het eind van de run. Uitzonderingen staan in de tabel
("zonder melding"). Mechanische lasten in een thermische analyse en omgekeerd
negeert de bridge met alleen een INFO, net als Mecway zelf.

## 1. Analysetypen

| Mecway | Status | Bridge (Code-Aster) | Opmerking |
|---|---|---|---|
| S30 Static 3D | Ja | `lin_static_3d` (`MECA_STATIQUE`) | Gap, tension only, compression only en contact vragen `nonlin_static_3d`: de bridge stopt met een ERROR. |
| L30 Nonlinear Static 3D | Ja | `nonlin_static_3d` (`STAT_NON_LINE`) | Rekenstappen = Mecway's *Time step size* plus de knikken van de lasttabellen. Contact: KB43. |
| D30 Dynamic Response 3D | Ja | `dyna_impl_3d` (`DYNA_NON_LINE`) | Gelijk aan Mecway (Newmark) met schema NEWMARK en deformation PETIT; anders een WARNING. |
| D30 met *Mode superposition* | Ja | `dyna_modal_3d` (`CALC_MODES` + `DYNA_VIBRA` `GENE`) | Geen opgelegde verplaatsing ≠ 0, beginsnelheid of dempers (KB54); kies dan `dyna_impl_3d`. |
| D31 Nonlinear Dynamic Response 3D | Ja | `dyna_impl_3d`; expliciet: `dyna_expl_3d` (zelf kiezen) | |
| V30 Frequency | Ja | `modal_3d` (`CALC_MODES`) | Voorspanning door lasten zoals Mecway; demping standaard niet, als optie complexe modes (KB49); cyclische symmetrie ([`Modaal_en_knik.md`](Modaal_en_knik.md) §2.5, §6, §7). Met een fluïdum-onderdeel: `vibroacoustic_modes_3d` / `vibroacoustic_harm_3d` ([`Akoestiek.md`](Akoestiek.md) §6, §7; KB59). |
| B30 Buckling | Ja | `buckling_3d` (`CALC_MODES` `MODE_FLAMB`) | Mecway's *Shift point* wordt niet gebruikt; ook negatieve kniklastfactoren (KB46). Zie [`Modaal_en_knik.md`](Modaal_en_knik.md). |
| T30 / T31 Thermal | Ja | `ther_3d` (`THER_LINEAIRE` / `THER_NON_LINE`) | Zie [`Thermisch.md`](Thermisch.md). Transient schema KB14. |
| A30 Acoustic Resonance 3D | Ja | `acoustic_modes_3d`; met een bron `acoustic_harm_3d` | KB55, KB57; [`Akoestiek.md`](Akoestiek.md). |
| S20 Static 2D (vlakke spanning, vlakke rek) | Deels | `lin_static_3d` (`MECA_STATIQUE`, `C_PLAN`/`D_PLAN`) | Alleen vlakke elementen, een dikte en type per model; belastingen en voorwaarden: [`2D_en_axisymmetrisch.md`](2D_en_axisymmetrisch.md) §1.1, §3 (KB126). Verificatie PL-01 … PL-03, PL-05. |
| SA0 Static Axisymmetric | Deels | `lin_static_3d` (`MECA_STATIQUE`, `AXIS`) | Als S20; Y = as, `stresszz` = tangentiële spanning, reacties voor 360 graden (KB126). Verificatie PL-04, PL-06. |
| D20, DA0 Dynamic Response 2D / Axisymmetric | Deels | `dyna_impl_3d` (`DYNA_NON_LINE`, `C_PLAN`/`D_PLAN`/`AXIS`) | Als S20/SA0; gelijk aan Mecway met NEWMARK, PETIT en een rekenstap per Mecway-stap (ook bij *every n time steps*); geen expliciet, mode superposition of beginsnelheid (KB126). Verificatie PL-10 … PL-12. |
| A20 Acoustic Resonance 2D | Ja | `acoustic_modes_3d` (`PHENOMENE='ACOUSTIQUE'`, `PLAN`) | Holtemodes, ook met impedantie; een dikte telt niet (zoals in Mecway); driehoeken iets hoger dan Mecway (KB130); geen harmonisch drukveld in 2D (KB126). [`Akoestiek.md`](Akoestiek.md) §3.5. Verificatie AK-10 … AK-15. |
| E30 DC Current Flow | Nee | – | De run stopt. |
| Elektrostatica en piëzo-elektriciteit (in S30) | Nee | – | Elektrische lasten worden overgeslagen; een piëzo- of matrixmateriaal stopt de run (§5). |
| geen Mecway-type | – | `harmonic_3d`, `spectrum_3d` (zelf kiezen) | Extra analyses van de bridge: [`Respons_op_modale_basis.md`](Respons_op_modale_basis.md), [`Spectrumanalyse.md`](Spectrumanalyse.md). |

## 2. Belastingen

| Mecway | Status | Opmerking |
|---|---|---|
| Force (knopen, vlakken, elementen) | Ja | Op knopen gelijk verdeeld, op vlakken als kracht per oppervlak. |
| Pressure | Ja | Meebewegend in niet-lineaire analyses (een formule in x, y, z blijft vast). Op schaalranden (lengte × dikte) en balkuiteinden (oppervlak) als knoopkrachten; op het zijvlak van een balk geen last (zie onder). |
| Traction | Ja | Op een schaalvlak met het moment van de halve dikte, zoals Mecway. |
| Line pressure | Ja | Globaal of lokaal (U, V, W). Combinaties op één balk worden opgeteld; lokaal en globaal op dezelfde balk: Nee (ERROR, KB20). |
| Hydrostatic pressure | Ja | Ook op schaalranden (lengte × dikte, consistente knoopkrachten, LS-93); Mecway's eigen solver negeert hem daar (WARNING), vergelijk met een Pressure-formule ρ g (h − z). [`Handleiding.md`](Handleiding.md) §4. |
| Moment | Ja | Op één knoop met rotaties of als krachten over vlakken. |
| Gravity | Ja | Met een tijdstabel alleen bij een vaste richting. |
| Centrifugal force | Deels | Alleen een constante hoeksnelheid, één per model (geen gyroscopisch effect); spin softening alleen op volumes (KB19). |
| Mass, Rotational inertia | Ja | Alleen op knopen; rotatietraagheid op één knoop. |
| Temperature (`temperature2`) + Thermal stress | Ja | Constante temperatuur; een tijdstabel of formule in t in L30 en D31 (`EVOL_THER`, NL-70..75, DY-70..72). Statisch/modaal/knik: een tijdshistorie valt weg, zoals bij Mecway's eigen solver. D30 negeert hem zoals Mecway. Schalen: Mecway zet minder uit dan de bridge; de bridge geeft de theoretische vrije uitzetting αΔT·L (gemeten op een plaat: bridge +3% (quad4) en +2% (quad8), Mecway −22% en −44%; volumes gelijk aan Mecway). Vergelijk bij schalen met thermische rek dus niet met Mecway (KB95). |
| Node temperature (`temperature3`) in een mechanische analyse | Ja | Ook na *Transfer temperatures from solution*. Statisch, niet-lineair statisch, modaal (voorspanning) en knik, zoals Temperature; knopen zonder temperatuur op de referentie van de Thermal stress (LS-08). D30 negeert hem zoals Mecway; D31 gemeld (niet in Mecway's lijst). |
| Rayleigh damping | Deels | Alleen op het hele model, niet op een selectie (KB27). |
| Initial velocity | Ja | Alleen in dynamica; niet bij mode superposition (KB54). |
| Initial displacement | Nee | Gemeld. |
| Waarde als tabel of formule in t | Ja | 10001 monsters zoals Mecway voor CCX. Lineair statisch, modaal en knik: de waarde op de eindtijd. Veel punten = veel stappen (KB104). |
| Formule in x, y, z (mechanisch) | Ja | Druk, traction, kracht, line pressure, opgelegde verplaatsing/rotatie: `FORMULE` van X, Y, Z (ook met t) in `AFFE_CHAR_MECA_F` (LS-40..44, NL-40). Kracht, line pressure en verplaatsing/rotatie met x, y, z legt Mecway 34 zelf niet op (WARNING). Niet: gravity, moment, centrifugaal, richting als formule, druk op schaalranden; niet in expliciet, harmonisch, spectrum (KB104). DKT/DST-schalen nemen de formule in de knopen (+0,8% op een grof mesh, LS-44a). Druk als formule blijft bij grote verplaatsingen een vaste last. De foutschatter rekent een vlak met een formulelast als onbelast (te grote fout daar). |
| Last op het zijvlak van een balk | Ja | Traction: een verdeelde last traction × omtrek van de doorsnede (`FORCE_POUTRE`, globale richting, ook met een formule in x, y, z), zoals Mecway (LS-92). Pressure: resultante nul, geen last (WARNING), zoals Mecway's eigen solver. [`Handleiding.md`](Handleiding.md) §4. |
| Pre-tension section | Deels | Prisma van volume-elementen (Mecway's CCX-variant), kracht of lengteverandering, in statisch, niet-lineair statisch en impliciete dynamische respons (D30/D31, `dyna_impl_3d`, staplast vanaf t = 0 zoals Mecway): snede met `LIAISON_DDL` naar een referentieknooppunt (PT-01..08, [`Boutvoorspanning.md`](Boutvoorspanning.md)); de variant met één veerelement (interne solver) in lineair statisch als twee knoopkrachten (PT-09, PT-10). Niet: expliciete dynamica, de veervariant in Frequency/Buckling (geometrische stijfheid van de veer, KB124). |
| Electric potential, Charge, Current, Robin | Nee | Geen elektrische analyses (§1). |
| Thermische lasten (temperature, heat flow, heat flux, heat generation, convection, radiation) | Ja | In T30/T31; formules in x, y, z, t ook. Details: [`Thermisch.md`](Thermisch.md). |
| Forced convection, Mass flow rate, cavity-straling | Nee | KB16. |
| Fluid pressure, Impedance (akoestiek) | Deels | Fluid pressure alleen 0; impedantie zonder frequentieafhankelijkheid, harmonisch alleen reëel (KB55, KB57). |
| OpenRadioss-kaarten in de model definition | Nee | Alleen `/FUNCT` (voor `PLAS_TAB`) wordt gelezen; de rest gemeld (KB4). |

## 3. Randvoorwaarden, koppelingen en contact

| Mecway | Status | Opmerking |
|---|---|---|
| Fixed support | Ja | Overlap met andere voorwaarden: Code-Aster ruimt dubbele voorwaarden niet op zoals Mecway; de bekende gevallen vangt de bridge af, de rest meldt hij (WARNING, KB8). |
| Pinned support | Ja | Knopen en vlakken van volume-elementen, zoals Mecway. |
| Frictionless support | Deels | Niet op balken; normaalverplaatsing ≠ 0 niet op gekromde schalen en schaalranden (KB5). Naast een displacement/node rotation 0 op dezelfde knopen (bijv. frictionless op de randen van een ronde plaat plus X, Y, Z = 0, GitHub issue #9) laat de bridge het deel van de relatie weg dat al vastligt, zoals Mecway het reduceert (MO-09, LS-83). |
| Elastic support | Ja | Vlakken van volumes en schaalvlakken. |
| Compression only support | Deels | Alleen in niet-lineaire analyses, niet samen met contact; op schalen blijven de rotaties vrij (KB22). |
| Displacement, Node rotation | Ja | Waarde als formule in x, y, z: Ja; richting als formule: Nee (KB104). Opgelegde rotaties bij grote rotaties: KB11. |
| Velocity | Ja | Dynamica. |
| Symmetry | Ja | Vlakken van volumes, schaalranden en balkuiteinden. |
| Cyclic symmetry | Deels | Alleen in Frequency (V30) en alleen volume-elementen; in statisch en thermisch gemeld en als losse sector gerekend (KB61). |
| Constraint equation | Ja | KB27. Expliciet: een constante ≠ 0 wordt een opgelegde beweging (DY-20b; Mecway zelf staat haar dan niet toe). |
| Node-surface coupling, Rigid (RBE2) | Ja | `LIAISON_SOLIDE`; grote rotaties: KB11. Niet in thermisch (gemeld). |
| Node-surface coupling, Distributing (RBE3) | Ja | `LIAISON_RBE3`. Niet in thermisch (gemeld). |
| Flexible joint on beam | Ja | Vrije rotatie om U, V en/of W (lokale balkassen zoals Mecway) aan een balkuiteinde: het element krijgt daar een eigen knoop, met `LIAISON_DDL` gekoppeld (translaties en de niet-vrije rotaties). Mecway kent geen stijfheid in de joint, alleen vrij of vast. Ook op line3-balken en in Frequency, dynamica, knik en niet-lineair statisch (dat laatste kent Mecway niet). Met `POU_D_T_GD` (grote rotaties) alleen een joint met U, V en W vrij (exact, NL-90); een joint met een deel van de rotaties vrij stopt dan vooraf met een ERROR (KB106). Verificatie LS-51 (gelijk aan Mecway); snedekrachten per element ook naast de joint en op line3 (LS-53). Een voorwaarde op een *elementselectie* of component met het element met de joint werkt op de eigen knoop van de joint in plaats van op de knopen van het element zoals in Mecway: het resultaat kan afwijken en Code-Aster kan stoppen met `FACTOR_11` (WARNING). Zet hem op knopen of vlakken (KB106). Met een element offset op hetzelfde element (lineair statisch en modaal, line2): de joint zit aan het eind van de starre arm, tussen het offsetpunt en het element, zoals Mecway 34 (Mecway-knoop → arm → joint → element; LS-52a/b/c gelijk aan Mecway in doorbuiging en rotaties); elders WARNING en geen joint (KB108). Niet in de keten thermisch → mechanisch (WARNING). |
| Contact, Unilateral (vlakken van volumes en schaalvlakken) | Ja | Alleen niet-lineair, zoals in Mecway. Formulering en wrijving: KB43; paren met gedeelde slave-knopen worden één zone (gemeld, KB10). |
| Contact, Unilateral, *Self contact* | Nee | Gemeld. Maak twee aparte vlakselecties. |
| Contact, Unilateral, op schaalranden of balken | Nee | Gemeld. |
| Contact, Bonded *Tie* / *Constraint equations* | Ja | `LIAISON_MAIL` (star), zie de tabel hieronder. Werkt ook in lineaire analyses. Alleen de slave-knopen die Mecway (CCX `*TIE`) koppelt: met een mastervlak tegenover zich (tolerantie in het vlak 2,5% van een typische elementgrootte) en, volume op volume, binnen de *Tolerance* ervan (0 = diezelfde CCX-standaard; met schalen begrenst Mecway de afstand niet); de andere blijven vrij, zoals in Mecway (WARNING met de knopen). Volume op volume gemeten gelijk aan Mecway 34 (Samples/BoltedJoint met verlijmde contacten: dezelfde 58 vrije knopen als CCX, verplaatsingen gelijk; LS-07l/m); met schalen dezelfde vrije knopen, maar andere verplaatsingen (KB128). |
| Contact, Bonded *Elastic* | Deels | Star verlijmd; de stijfheid wordt niet vertaald (gemeld, KB21). |
| Bonded contact in T30/T31 | Ja | *Tie* / *Constraint equations*: `AFFE_CHAR_THER` `LIAISON_MAIL` (ook niet-conform en schaal op schaal). *Elastic*: thermische weerstand (*Thermal conductance per unit area*) als `ECHANGE_PAROI` bij volumevlakken die knoop op knoop tegenover elkaar liggen, anders ideaal verlijmd (gemeld). Niet in een model met volumes én schalen (ERROR; gedeelde knopen). [Thermisch.md](Thermisch.md) §3, verificatie TH-04. |
| Bonded contact in de akoestiek | Nee | Gemeld (KB55). |

Verlijmd contact per combinatie (slave op master):

| Slave → master | Status | Code-Aster | Opmerking |
|---|---|---|---|
| volume → volume | Ja | `MASSIF` | Alleen de slave-knopen die CCX koppelt (rij hierboven); een slave-vlak dat voorbij de master uitsteekt, is daar vrij, zoals in Mecway (LS-07l). |
| schaal → schaal | Ja | `COQUE` (of `LIAISON_DDL`) | Ook een schaalrand op een schaalvlak (naad in het vlak, T-stuk): stijf, de rotaties gaan mee (geen scharnier; Mecway's eigen solver doet dat niet). Lineaire schalen als master blijven DKT, ook bij de keuze COQUE_3D. Een kwadratische master (tri6/quad8) en een scheve of gekromde master: de bridge schrijft de koppeling (deels) zelf als `LIAISON_DDL`; scheef of gekromd zet `solver_nprec` voor die run op −1 (WARNING). Geverifieerd in LS-07a..k, voorbeeld `Voorbeeld_T.liml` ([contact §3.10](Instellingen_contact_en_nietlineair.md#310-voorbeeld-platen-verlijmen-bonded-contact-tussen-schalen)). |
| schaalvlak → volume | Ja | `MASSIF` | Alleen de verplaatsingen; gemeten gelijk aan gedeelde knopen (KB21). |
| schaalrand → volume | Deels | `COQUE_MASSIF` of `MASSIF` | Stijf als alle randen bij één component met een dikte horen; anders werkt de rand als scharnier (WARNING, KB21). Maak één verlijmd contact per component (voorbeeld 2). |
| volume → schaal | Ja | `MASSIF_COQUE` | Ook op een kwadratische schaal (quad8 met een hex20-blok, knopen midden in de plaatelementen: gemeten gelijk aan zelf geschreven relaties). |
| balk → volume | Nee | – | Gemeld en overgeslagen. Alternatief: Node-surface coupling met het balkuiteinde als referentieknoop, of `#ASTER` `LIAISON_ELEM` `3D_POU` (voorbeeld 1). |
| balk → schaal | Nee | – | Gemeld en overgeslagen. Alternatief: Node-surface coupling met het balkuiteinde als referentieknoop. |
| balk → balk | Nee | – | Kan in Mecway ook niet (de master moet een vlak zijn). Verbind met een gedeelde knoop of constraint equations. |

## 4. Elementen

| Mecway | Status | Code-Aster | Opmerking |
|---|---|---|---|
| hex8 | Deels | `3D` | Stijver dan Mecway (geen incompatibele modes, KB1); met rubber (hyperelastisch) ~3x te stijf. Beter: *Elementen* > hex8 `LINE_QUAD`. |
| tet4, tet10, pyr5, pyr13, wedge6, wedge15, hex20 | Ja | `3D` | Piramides niet in de akoestiek (KB55). Sterk gekromde hex20/wedge15: eigenfrequenties tot 0,8% hoger dan Mecway (KB62). |
| tri3, quad4 (schaal) | Ja | `DKT` (of `DST`/`COQUE_3D` als keuze) | ~0,7% anders dan Mecway (KB2). |
| tri6, quad8 (schaal) | Ja | `COQUE_3D` | Als master van verlijmd contact: translaties met `LIAISON_DDL`, rotaties met `LIAISON_MAIL` (LS-07i..k). |
| lineaire en kwadratische schalen in één component | Deels | – | De kwadratische worden niet gemodelleerd (ERROR). Splits de component. |
| beam line2 | Ja | `POU_D_E` (of `POU_D_T`, `POU_D_T_GD`, `POU_D_TG`) | Oriëntatie uit *Element properties* of een *Element orientation*-kaart (zie Element orientation hieronder). Geen plasticiteit (KB6). Grote rotaties alleen met `elem_beam` = `POU_D_T_GD` in niet-lineair statisch met grote verplaatsingen ([Instellingen §2.9](Instellingen_contact_en_nietlineair.md#29-balken-met-grote-rotaties-elem_beam--pou_d_t_gd); elders `POU_D_T`, WARNING; verificatie NL-80–89); met `POU_D_E`/`POU_D_T` blijven balken geometrisch lineair (KB11). Buig-torsieknik en kip van open profielen (T, C, L, I) met `elem_beam` = `POU_D_TG`: welving en dwarskrachtcentrum, welving bij opleggingen volgens `beam_warping` ([Modaal en knik §3.5.1](Modaal_en_knik.md#351-balk-met-welving-elem_beam--pou_d_tg); verificatie BU-38 … BU-42, LS-90 … LS-95b); Mecway's eigen balk heeft geen welving. |
| beam line3 | Ja | `POU_D_E` (of `POU_D_T`, `POU_D_T_GD`, `POU_D_TG`) | Elk element wordt in de middenknoop in twee SEG2-cellen gesplitst (Code-Aster heeft geen kwadratische balk); resultaten op alle drie de knopen. Mecway rekent line3-balken zelf alleen met CCX. Een gekromd element (middenknoop naast de koorde) wordt zo twee rechte stukken met een knik, Mecway rekent de kromme vorm (WARNING; verfijn de kromming, KB107). Verificatie LS-50. Veer, gap en demper op line3: Nee (ERROR; in Mecway alleen line2); de bridge stopt dan voor Code-Aster, net als bij elke elset die niet vertaald kan worden. |
| truss line2 | Ja | `BARRE` | Kleine verplaatsingen (KB40). Geen lineaire knik (geen `RIGI_GEOM`, ERROR; [`Modaal_en_knik.md`](Modaal_en_knik.md) §3.3). Balken en trusses in één component worden twee groepen (`<naam>_TRUSS`). |
| truss line3 | Ja | `BARRE` | Elk element wordt in de middenknoop in twee SEG2-cellen gesplitst (`BARRE` bestaat alleen op SEG2). De middenknoop volgt dwars op de koorde het gemiddelde van de eindknopen (`LIAISON_DDL`, zoals Mecway); een richting die op alle drie de knopen al vastligt (bijv. uz = 0 in een vlak model) vervalt. Gekromd element: twee rechte stukken (WARNING, KB107). De middenknoopvoorwaarde houdt ook de losse middenknoop-modes tegen die CalculiX zonder zo'n voorwaarde geeft. Geen lineaire knik (zoals line2). Verificatie LS-54 (staaf), MO-08 (NAFEMS CP5: 451,15 / 1049,9 Hz, referentie 451,1 / 1049,9; Mecway 34 zelf 450 / 1030). |
| spring, damper, gap (line2) | Ja | `DIS_T` (gap: `DIS_CHOC`) | Langs de eigen as. Gap alleen niet-lineair (KB23); veren/dempers niet tegen Mecway vergeleken (KB47). |
| tension only (line2, line3) | Deels | `CABLE` | Alleen niet-lineair; drukstijfheid 1e-4 E (KB23). Line3 gesplitst in twee SEG2-cellen zoals truss line3 (LS-54b, LS-54c; Mecway 34 gaf headless geen oplossing voor tension only). |
| elementen van verschillende dimensie in één component | Deels | – | Alleen de hoogste dimensie wordt gemodelleerd (ERROR). Splits de component. |
| plane, axisymmetric (2D): tri3, tri6, quad4, quad8 | Ja | `C_PLAN`, `D_PLAN`, `AXIS` | Alleen in S20 en SA0 (§1); verplaatsingen gelijk aan Mecway, ook quad4 (geen incompatibele modes in Mecway's 2D). [`2D_en_axisymmetrisch.md`](2D_en_axisymmetrisch.md). |
| schalen in een thermische analyse | Deels | `PLAN` met een diktefactor | Alleen schalen in evenwijdige vlakken (KB15); andere: Nee (KB16). |
| fin, fluid network element, resistor | Nee | – | Thermisch 1D en DC-stroom: KB16. |
| Element offset (schaal, balk) | Ja | DKT/DST: `COQUE` `EXCENTREMENT` (+ `INER_ROTA`); COQUE_3D en balken: element op eigen knopen + starre arm (`LIAISON_DDL`) | Schaal: *Element coordinates*, alleen W telt (zoals Mecway; u/v hebben ook daar geen effect). Balk: *Global coordinates* x/y/z (u/v/w op een balk: geen effect in Mecway, WARNING). Verplaatsing, rotatie en reactie op de Mecway-knopen; spanningen van het verschoven element op die knopen getoond, ook als elementwaarden (LS-65). In alle mechanische analyses (Mecway: alleen statisch), niet in de keten thermisch → mechanisch (WARNING, KB64). Starre arm: kleine rotaties, ook met `GROT_GDEP` (WARNING bij verschoven schalen, KB108). Een knoop met een eigen waarde (ander element) houdt die; de spanning van het verschoven element telt daar niet mee (KB108). Een last op een vlakselectie op randen van verschoven schalen zet de bridge op de knopen, Mecway op de verschoven rand (WARNING, KB108). Een flexible joint op een verschoven balkelement: in lineair statisch en modaal aan het eind van de arm, tussen het offsetpunt en het element, zoals Mecway (LS-52); elders niet vertaald (WARNING, KB108); verlijmd contact op verschoven schalen: WARNING (KB108). Verificatie LS-60–67, LS-52. |
| Element orientation (lokale U/V-assen) | Ja | balken: `AFFE_CARA_ELEM` `ORIENTATION` `CARA='VECT_Y'` | Mecway slaat de oriëntatie op twee manieren op: per element (*Element properties*: attributen `orientationux`…`vz`, `angle`) en als item in Loads & Constraints (*Element orientation* op een elementselectie: `<orientation selection="…">` met `ux`…`vz` en `angleu`, ook als formule van het elementmiddelpunt x, y, z; Mecway 34 houdt de kaart zo bij opslaan). De bridge leest beide op dezelfde manier. Balken: V-as en hoek; elke balk krijgt Mecway's V-as expliciet als `VECT_Y`, ook zonder oriëntatie (standaard V = Z × U, langs Z V = Y). Gaps: U = richting. Schalen: U-as van het resultaatveld `shell_forces` (§6). Volumes: U, V en hoek zijn de materiaalassen van orthotroop materiaal (§5, `MASSIF` `ANGL_REP`); met isotroop materiaal geen effect. Trusses, kabels, veren en dempers: geen effect (INFO). Een element met een oriëntatie uit zowel een kaart als de attributen, of uit twee kaarten: Mecway rekent dan niet (*already has its orientation defined elsewhere*), de bridge geeft een WARNING en gebruikt de kaart (van twee kaarten de laatste in het bestand). Een U-as op balken, een V-as of hoek op schalen (Mecway rekent dan ook niet) en een balkkaart zonder V-vector (Mecway: singulier): WARNING, genegeerd. Een kaart op een componentnaam zonder elementselectie met die naam heeft in Mecway geen effect: ERROR. Verificatie MO-31, LS-79–82, BU-25, LS-31d. |

## 5. Materialen en doorsneden

| Mecway | Status | Opmerking |
|---|---|---|
| Isotropic (E, ν, ρ, α) | Ja | Zonder E rekent de bridge met 210 GPa, Mecway met 0 (KB60). |
| Plastic, isotrope hardingscurve | Ja | `VMIS_ISOT_TRAC`. E = helling van het eerste stuk van de curve, zoals Mecway (WARNING als *Young's modulus* anders is; [`Instellingen_contact_en_nietlineair.md`](Instellingen_contact_en_nietlineair.md) §2.4). Niet op balken (elastisch, WARNING; KB6). |
| Plastic, Bilinear isotropic / kinematic | Ja | `ECRO_LINE`; Mecway's *tangent modulus* is de plastische modulus H, `D_SIGM_EPSI` = E·H/(E+H); ideaal plastisch met tangent modulus 0. |
| Plastic, Kinematic (curve) | Deels | Alleen een curve met lineaire versteviging (`VMIS_CINE_LINE`); een niet-lineaire curve wordt elastisch gerekend (gemeld). Geen equivalentplasticstrain (KB6). |
| Plastic, Ramberg-Osgood | Ja | Bemonsterde curve (KB6). |
| Spring, Damper, Gap, Tension only | Ja | Alleen op line2 (§4); tension only ook op line3 (LS-54b). Gap: *force of open gap* niet gebruikt (KB23). |
| Neo Hooke, Mooney-Rivlin (hyperelastisch) | Ja | `ELAS_HYPER` (C10, C01, K = 2/D1) met `GREEN_LAGRANGE`, in niet-lineair statisch en dynamisch (impliciet en expliciet), alleen volume-elementen (zoals Mecway). D1 = 0, schalen/balken en lineaire analyses: ERROR; thermische uitzetting genegeerd (WARNING). [`Instellingen_contact_en_nietlineair.md`](Instellingen_contact_en_nietlineair.md) §2.4, verificatie NL-50..53. |
| Orthotropic, Stiffness matrix, Compliance matrix | Deels | Op volume-elementen in Lineair en Niet-lineair statisch, Modaal, Knik en impliciete Dynamica: `ELAS_ORTH` met de elementassen U, V, W (attributen, *Element orientation*-kaart of standaard globaal) als `AFFE_CARA_ELEM` `MASSIF` `ANGL_REP`; een matrix alleen als hij orthotroop is in de elementassen (koppeltermen nul), anders ERROR (Code-Aster heeft geen algemene 3D-anisotropie). Lineaire schalen (DKT/DST) in Lineair statisch: `DEFI_COMPOSITE` met één laag, U standaard langs de rand van knoop 1 naar 2. Kwadratische schalen, membranen, *Composite* en de overige analyses: ERROR (KB131). [`Orthotroop_materiaal.md`](Orthotroop_materiaal.md), verificatie OR-01..22. |
| Composite, piëzo | Nee | WARNING en daarna stopt de run ("elset zonder bruikbaar materiaal"). Geen alternatief in de bridge. Hyperfoam: ERROR (niet mogelijk met Code-Aster 17.4 op Windows: geen MFront-ondersteuning; zie [Instellingen contact en niet-lineair](Instellingen_contact_en_nietlineair.md), hyperelastisch materiaal). |
| Failure criterion (factor of safety) | Deels | Von Mises (*tensile strength*): `factorofsafety` naar Mecway (resultaatveld `safety_factor`, §6). Tsai-Wu en andere criteria: WARNING, geen factor of safety. Voor plastisch bezwijken: [`Bezwijken.md`](Bezwijken.md). |
| Thermisch: geleiding, soortelijke warmte, ook *Temperature dependent* | Ja | [`Thermisch.md`](Thermisch.md). Formules in materiaaleigenschappen: Nee (KB16). |
| Speed of sound (akoestiek) | Ja | Media met verschillende dichtheid: Nee (KB55, KB59). |
| OpenRadioss law `PLAS_TAB` | Deels | Niet vertaalde velden: KB34. Law `VOID`: elementen weggelaten (gemeld); andere laws: Nee. |
| Doorsnede rond en rechthoekig (massief en hol), General section, I, T, L, C | Ja | Mecway's *Stress recovery point* wordt niet gebruikt. Andere geometrietypen: Nee (WARNING). |
| Plaatdikte (Plate) | Ja | Schalen; in S20 de dikte van de vlakke elementen, met *plane strain* `D_PLAN`. |

## 6. Resultaten terug in Mecway

| Mecway-veld | Status | Opmerking |
|---|---|---|
| Verplaatsing, rotatie | Ja | Modaal en knik: de vormen. |
| Spanningstensor volume-elementen (knoop en element-knoop) | Ja | Code-Aster-middeling, anders dan Mecway (KB3). Route `tabel`: KB7. |
| von Mises (volumes; schalen boven/midden/onder) | Ja | KB3. |
| Spanningstensor schalen (globaal, boven/midden/onder), krachten en momenten per lengte | Ja | Velden `shell_stresses` (standaard uit) en `shell_forces`; alleen route `liml`. `shell_forces` staat aan bij statisch en niet-lineair en maakt de resultaten bij schalen ca. 2,5 keer zo groot (WARNING; uitvinken op de pagina van de analyse). Mecway's *stress in element coordinates* van schalen niet (van volume-elementen met orthotroop materiaal wel: `lamuu` .., [`Orthotroop_materiaal.md`](Orthotroop_materiaal.md) §4). U-as uit *Element properties* of een *Element orientation*-kaart ([`Handleiding.md`](Handleiding.md) §4.1). |
| Balkspanning | Deels | Alleen kleinste/grootste axiale spanning bij rechthoekige en ronde doorsneden (`beamsixxmin/max`); niet met `POU_D_T_GD` (WARNING). |
| Snedekrachten en -momenten van balken | Ja | Veld `beam_forces` (`tensileforce`, `sheary`, `shearz`, `torsion`, `bendingmomv/w`), ook per mode. Met `POU_D_T_GD` uit `SIEF_ELNO`, één waarde per element in de meedraaiende assen (NL-81, NL-83). |
| Reactiekrachten en -momenten | Ja | Niet bij mode superposition, harmonisch en vibro-akoestiek (KB54, KB59). |
| Snelheid, versnelling | Ja | Dynamica; versnelling niet bij mode superposition (KB54). |
| Plastische rek, equivalente plastische rek | Deels | Equivalente plastische rek niet bij kinematische versteviging (KB6). |
| Totale rek | Ja | Veld `strain` (standaard uit): `lstrain*`, niet-lineair `greenlagrangestrain*`; schalen boven/midden/onder. Geen logaritmische rek en geen hoofdrekken. |
| Contactdruk, contactstatus | Deels | Veld `contact`: `contactpressure`, `contactstate` (0/1/2). Geen contactschuifspanning en -verplaatsing; glijden (2) NIET geverifieerd. |
| Factor of safety | Ja | Veld `safety_factor` (von Mises, §5). |
| Principal stress, Tresca stress, principal strain | Ja | Velden `principal_stresses` en `principal_strains` (standaard uit): `principal1..3`, `tresca`, `lprincipalstrain1..3` (niet-lineair met grote verplaatsingen, Green-Lagrange-rek: `greenlagrangeprincipalstrain1..3`) van volume-elementen en `principal1u1`, `trescau1`, `lprincipalstrain1u1` .. (boven/midden/onder) van schalen, berekend zoals Mecway (eigenwaarden per elementknoop, knoop = gemiddelde). Verificatie FX-02, FX-04, FX-05. |
| Temperatuur, warmteflux | Ja | Thermisch. |
| Eigenfrequenties, kniklastfactoren, effectieve massa | Ja | Fractie van de effectieve massa anders dan Mecway (KB49). |
| Akoestische druk | Ja | [`Akoestiek.md`](Akoestiek.md). |
| *Saved monitor* (Solution) | Optie | De samenvatting van de Code-Aster-run in plaats van de solvermeldingen van Mecway, alleen met de instelling `save_monitor_liml` (standaard uit; route `liml`). De samenvatting staat altijd in `<model>_<run-id>_aster_summary.txt` ([`Handleiding.md`](Handleiding.md) §5.2). |

Extra velden van de bridge (foutschatter, vermoeiing, metallurgie) en welk Code-Aster-veld
bij welke Mecway-naam hoort: [`Handleiding.md`](Handleiding.md) §4.1.

## 7. Analyse- en solverinstellingen van Mecway

| Mecway | Status | Opmerking |
|---|---|---|
| Analysetype | Ja | Kiest de analyse bij `auto` (§1). |
| Solver (Internal, CCX, OpenRadioss) | Nee | De bridge rekent altijd met Code-Aster; alleen voor meldingen gelezen. |
| Number of modes | Ja | Modaal, knik, mode superposition, akoestiek. |
| Shift point (knik) | Nee | Alleen INFO (KB46). |
| Mode superposition (D30) | Ja | §1. |
| Time period | Ja | |
| Time step size | Ja | D30, D20, DA0 (rekenstap = Mecway's stap, ook bij *every n time steps*; met mode superposition hoogstens Mecway's stap), T31 en L30 (L30: Mecway's stappen tot de periode plus de knikken van de lasttabellen; zonder stapgrootte `substeps_per_interval`). Met *Automatic time stepping* zie de regel hieronder. |
| Uitvoertijden, *Generate solution every n time steps* | Ja | |
| Automatic time stepping | Ja | L30 (niet-lineair statisch): `DEFI_LIST_INST METHODE='AUTO'` tussen Mecway's uitvoertijden, `ARCHIVAGE` op die tijden; instelling `auto_time_stepping`. Dynamisch niet: vaste stappen, knippen bij divergentie. |
| Incompatible hex8 | Nee | KB1. |
| Solution > Formula (resultaatformules, bijv. `qf.z/3600/(12^2)`) | Deels | De bridge rekent ze uit de resultaten uit, in de eenheden van de formule, per knoop en tijdstap, zoals Mecway bij zijn eigen solve (FX-01 .. FX-03); `s1`, `tr`, `e1`, `GLe1` met de velden `principal_stresses` / `principal_strains`. Niet: elementcoordinaten, schaalkrachten, materiaalsymbolen (WARNING; formule na het laden opnieuw maken, KB121). [`Handleiding.md`](Handleiding.md) §4.2. |
| CCX > custom element type (bijv. Hex8 → C3D8R) | Nee | Alleen CalculiX: WARNING, Code-Aster gebruikt de pagina *Elementen* (hex8 `3D` = C3D8, `LINE_QUAD` = C3D20; C3D8R/C3D8I hebben geen gelijke). [`Instellingen_contact_en_nietlineair.md`](Instellingen_contact_en_nietlineair.md), hyperelastisch materiaal. |
| Configuraties | Ja | Eén per run, te kiezen op het startscherm (*Configuratie*); resultaten in de solution van die configuratie ([`Handleiding.md`](Handleiding.md) §4, LS-20). |
| Custom model definition (CCX, OpenRadioss, Nastran) | Deels | Alleen `#ASTER`-regels; gewone CCX-kaarten zonder melding genegeerd. |
