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
| 2D en axisymmetrisch (o.a. S20, SA0, D20, A20) | Nee | – | De run stopt ("analysetype wordt niet ondersteund"). Alternatief: modelleer in 3D, bijv. een plak met symmetry. |
| E30 DC Current Flow | Nee | – | De run stopt. |
| Elektrostatica en piëzo-elektriciteit (in S30) | Nee | – | Elektrische lasten worden overgeslagen; een piëzo- of matrixmateriaal stopt de run (§5). |
| geen Mecway-type | – | `harmonic_3d`, `spectrum_3d` (zelf kiezen) | Extra analyses van de bridge: [`Respons_op_modale_basis.md`](Respons_op_modale_basis.md), [`Spectrumanalyse.md`](Spectrumanalyse.md). |

## 2. Belastingen

| Mecway | Status | Opmerking |
|---|---|---|
| Force (knopen, vlakken, elementen) | Ja | Op knopen gelijk verdeeld, op vlakken als kracht per oppervlak. |
| Pressure | Ja | Meebewegend in niet-lineaire analyses. Op schaalranden en balkuiteinden als knoopkrachten (KB5). |
| Traction | Ja | Op een schaalvlak met het moment van de halve dikte, zoals Mecway. |
| Line pressure | Ja | Globaal of lokaal (U, V, W). Combinaties op één balk: KB20. |
| Hydrostatic pressure | Deels | Niet op schaalranden (KB5). |
| Moment | Ja | Op één knoop met rotaties of als krachten over vlakken. |
| Gravity | Ja | Met een tijdstabel alleen bij een vaste richting. |
| Centrifugal force | Deels | Alleen een constante hoeksnelheid, één per model (geen gyroscopisch effect); spin softening alleen op volumes (KB19). |
| Mass, Rotational inertia | Ja | Alleen op knopen; rotatietraagheid op één knoop. |
| Temperature (`temperature2`) + Thermal stress | Ja | Constante temperatuur; een tijdstabel of formule in t in L30 en D31 (`EVOL_THER`, NL-70..75, DY-70..72). Statisch/modaal/knik: een tijdshistorie valt weg, zoals bij Mecway's eigen solver. D30 negeert hem zoals Mecway. |
| Node temperature (`temperature3`) in een mechanische analyse | Ja | Ook na *Transfer temperatures from solution*. Statisch, niet-lineair statisch, modaal (voorspanning) en knik, zoals Temperature; knopen zonder temperatuur op de referentie van de Thermal stress (LS-08). D30 negeert hem zoals Mecway; D31 gemeld (niet in Mecway's lijst). |
| Rayleigh damping | Deels | Alleen op het hele model, niet op een selectie (KB27). |
| Initial velocity | Ja | Alleen in dynamica; niet bij mode superposition (KB54). |
| Initial displacement | Nee | Gemeld. |
| Waarde als tabel of formule in t | Ja | 10001 monsters zoals Mecway voor CCX. Lineair statisch, modaal en knik: de waarde op de eindtijd. Veel punten = veel stappen (KB45). |
| Formule in x, y, z (mechanisch) | Nee | KB45. Alternatief: eigen last in een `#ASTER`-regel (`AFFE_CHAR_MECA_F` met een `FORMULE` van X, Y, Z; opzet zoals voorbeeld 3), NIET geverifieerd. |
| Last op het zijvlak van een balk | Nee | KB5. Zet de last op een elementselectie van de balk. |
| Pre-tension section | Nee | Geen alternatief in de bridge. |
| Electric potential, Charge, Current, Robin | Nee | Geen elektrische analyses (§1). |
| Thermische lasten (temperature, heat flow, heat flux, heat generation, convection, radiation) | Ja | In T30/T31; formules in x, y, z, t ook. Details: [`Thermisch.md`](Thermisch.md). |
| Forced convection, Mass flow rate, cavity-straling | Nee | KB16. |
| Fluid pressure, Impedance (akoestiek) | Deels | Fluid pressure alleen 0; impedantie zonder frequentieafhankelijkheid, harmonisch alleen reëel (KB55, KB57). |
| OpenRadioss-kaarten in de model definition | Nee | Alleen `/FUNCT` (voor `PLAS_TAB`) wordt gelezen; de rest gemeld (KB4). |

## 3. Randvoorwaarden, koppelingen en contact

| Mecway | Status | Opmerking |
|---|---|---|
| Fixed support | Ja | Overlap met andere voorwaarden: KB8. |
| Pinned support | Ja | Knopen en vlakken van volume-elementen, zoals Mecway. |
| Frictionless support | Deels | Niet op balken; normaalverplaatsing ≠ 0 niet op gekromde schalen en schaalranden (KB5). |
| Elastic support | Ja | Vlakken van volumes en schaalvlakken. |
| Compression only support | Deels | Alleen in niet-lineaire analyses, niet samen met contact; op schalen blijven de rotaties vrij (KB22). |
| Displacement, Node rotation | Ja | Richting als formule in x, y, z: Nee (KB45). Opgelegde rotaties bij grote rotaties: KB11. |
| Velocity | Ja | Dynamica. |
| Symmetry | Ja | Vlakken van volumes, schaalranden en balkuiteinden. |
| Cyclic symmetry | Deels | Alleen in Frequency (V30) en alleen volume-elementen; in statisch en thermisch gemeld en als losse sector gerekend (KB61). |
| Constraint equation | Ja | KB27. Expliciet: een constante ≠ 0 wordt een opgelegde beweging (DY-20b; Mecway zelf staat haar dan niet toe). |
| Node-surface coupling, Rigid (RBE2) | Ja | `LIAISON_SOLIDE`; grote rotaties: KB11. Niet in thermisch (gemeld). |
| Node-surface coupling, Distributing (RBE3) | Ja | `LIAISON_RBE3`. Niet in thermisch (gemeld). |
| Flexible joint on beam | Ja | Vrije rotatie om U, V en/of W (lokale balkassen zoals Mecway) aan een balkuiteinde: het element krijgt daar een eigen knoop, met `LIAISON_DDL` gekoppeld (translaties en de niet-vrije rotaties). Mecway kent geen stijfheid in de joint, alleen vrij of vast. Ook op line3-balken en in Frequency, dynamica en knik. Verificatie LS-51 (gelijk aan Mecway). Een voorwaarde op een *elementselectie* met het element met de joint: zie KB106. |
| Contact, Unilateral (vlakken van volumes en schaalvlakken) | Ja | Alleen niet-lineair, zoals in Mecway. Formulering en wrijving: KB43; gedeelde slave-knopen: KB10. |
| Contact, Unilateral, *Self contact* | Nee | Gemeld. Maak twee aparte vlakselecties. |
| Contact, Unilateral, op schaalranden of balken | Nee | Gemeld. |
| Contact, Bonded *Tie* / *Constraint equations* | Ja | `LIAISON_MAIL` (star), zie de tabel hieronder. Werkt ook in lineaire analyses. Automatische tolerantie: alle slave-knopen worden gekoppeld (KB21). |
| Contact, Bonded *Elastic* | Deels | Star verlijmd; de stijfheid wordt niet vertaald (gemeld, KB21). |
| Bonded contact in T30/T31 | Ja | *Tie* / *Constraint equations*: `AFFE_CHAR_THER` `LIAISON_MAIL` (ook niet-conform en schaal op schaal). *Elastic*: thermische weerstand (*Thermal conductance per unit area*) als `ECHANGE_PAROI` bij volumevlakken die knoop op knoop tegenover elkaar liggen, anders ideaal verlijmd (gemeld). Niet in een model met volumes én schalen (ERROR; gedeelde knopen). [Thermisch.md](Thermisch.md) §3, verificatie TH-04. |
| Bonded contact in de akoestiek | Nee | Gemeld (KB55). |

Verlijmd contact per combinatie (slave op master):

| Slave → master | Status | Code-Aster | Opmerking |
|---|---|---|---|
| volume → volume | Ja | `MASSIF` | |
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
| hex8 | Deels | `3D` | Stijver dan Mecway (geen incompatibele modes, KB1). Beter: *Elementen* > hex8 `LINE_QUAD`. |
| tet4, tet10, pyr5, pyr13, wedge6, wedge15, hex20 | Ja | `3D` | Piramides niet in de akoestiek (KB55). Gekromde hex20/wedge15: KB62. |
| tri3, quad4 (schaal) | Ja | `DKT` (of `DST`/`COQUE_3D` als keuze) | ~0,7% anders dan Mecway (KB2). |
| tri6, quad8 (schaal) | Ja | `COQUE_3D` | Als master van verlijmd contact: translaties met `LIAISON_DDL`, rotaties met `LIAISON_MAIL` (LS-07i..k). |
| lineaire en kwadratische schalen in één component | Deels | – | De kwadratische worden niet gemodelleerd (ERROR). Splits de component. |
| beam line2 | Ja | `POU_D_E` (of `POU_D_T`) | Oriëntatie uit *Element properties*. Geen plasticiteit (KB6), geen grote rotaties (KB11). |
| beam line3 | Ja | `POU_D_E` (of `POU_D_T`) | Elk element wordt in de middenknoop in twee SEG2-cellen gesplitst (Code-Aster heeft geen kwadratische balk); resultaten op alle drie de knopen. Mecway rekent line3-balken zelf alleen met CCX. Verificatie LS-50. Truss, veer, gap, demper en tension-only op line3: Nee (ERROR; in Mecway alleen line2). |
| truss line2 | Ja | `BARRE` | Kleine verplaatsingen (KB40). Balken en trusses in één component worden twee groepen (`<naam>_TRUSS`). |
| spring, damper, gap (line2) | Ja | `DIS_T` (gap: `DIS_CHOC`) | Langs de eigen as. Gap alleen niet-lineair (KB23); veren/dempers niet tegen Mecway vergeleken (KB47). |
| tension only (line2, truss) | Deels | `CABLE` | Alleen niet-lineair; drukstijfheid 1e-4 E (KB23). |
| elementen van verschillende dimensie in één component | Deels | – | Alleen de hoogste dimensie wordt gemodelleerd (ERROR). Splits de component. |
| plane, axisymmetric (2D) | Nee | – | Alleen in 2D-analyses (§1). |
| schalen in een thermische analyse | Deels | `PLAN` met een diktefactor | Alleen schalen in evenwijdige vlakken (KB15); andere: Nee (KB16). |
| fin, fluid network element, resistor | Nee | – | Thermisch 1D en DC-stroom: KB16. |
| Element offset (schaal, balk) | Nee | – | Gemeld. Modelleer de excentriciteit met een Node-surface coupling (Rigid). |
| Element orientation (lokale U/V-assen per element) | Deels | – | Mecway slaat de oriëntatie per element op (`orientationux`…`vz`, `angle`). Gebruikt voor balken (doorsnede-oriëntatie) en gaps (richting). Bij volumes en schalen genegeerd zonder melding; met isotroop materiaal verandert dat de uitkomst niet. Pas nodig bij orthotrope materialen (§5, Nee). |

## 5. Materialen en doorsneden

| Mecway | Status | Opmerking |
|---|---|---|
| Isotropic (E, ν, ρ, α) | Ja | Zonder E rekent de bridge met 210 GPa, Mecway met 0 (KB60). |
| Plastic, isotrope hardingscurve | Ja | `VMIS_ISOT_TRAC`. Niet op balken (elastisch, WARNING; KB6). |
| Plastic, Bilinear isotropic / kinematic | Ja | `ECRO_LINE`; Mecway's *tangent modulus* is de plastische modulus H, `D_SIGM_EPSI` = E·H/(E+H); ideaal plastisch met tangent modulus 0. |
| Plastic, Kinematic (curve) | Deels | Alleen een curve met lineaire versteviging (`VMIS_CINE_LINE`); een niet-lineaire curve wordt elastisch gerekend (gemeld). Geen equivalentplasticstrain (KB6). |
| Plastic, Ramberg-Osgood | Ja | Bemonsterde curve (KB6). |
| Spring, Damper, Gap, Tension only | Ja | Alleen op line2 (§4). Gap: *force of open gap* niet gebruikt (KB23). |
| Orthotropic, Anisotropic (matrix), Composite, Neo Hooke, Mooney-Rivlin, piëzo | Nee | WARNING en daarna stopt de run ("elset zonder bruikbaar materiaal"). Geen alternatief in de bridge. |
| Failure criterion (factor of safety) | Deels | Von Mises (*tensile strength*): `factorofsafety` naar Mecway (resultaatveld `safety_factor`, §6). Tsai-Wu en andere criteria: WARNING, geen factor of safety. Voor plastisch bezwijken: [`Bezwijken.md`](Bezwijken.md). |
| Thermisch: geleiding, soortelijke warmte, ook *Temperature dependent* | Ja | [`Thermisch.md`](Thermisch.md). Formules in materiaaleigenschappen: Nee (KB16). |
| Speed of sound (akoestiek) | Ja | Media met verschillende dichtheid: Nee (KB55, KB59). |
| OpenRadioss law `PLAS_TAB` | Deels | Niet vertaalde velden: KB34. Law `VOID`: elementen weggelaten (gemeld); andere laws: Nee. |
| Doorsnede rond en rechthoekig (massief en hol), General section, I, T, L, C | Ja | Mecway's *Stress recovery point* wordt niet gebruikt. Andere geometrietypen: Nee (WARNING). |
| Plaatdikte (Plate) | Ja | |

## 6. Resultaten terug in Mecway

| Mecway-veld | Status | Opmerking |
|---|---|---|
| Verplaatsing, rotatie | Ja | Modaal en knik: de vormen. |
| Spanningstensor volume-elementen (knoop en element-knoop) | Ja | Code-Aster-middeling, anders dan Mecway (KB3). Route `tabel`: KB7. |
| von Mises (volumes; schalen boven/midden/onder) | Ja | KB3. |
| Spanningstensor schalen (globaal, boven/midden/onder), krachten en momenten per lengte | Ja | Velden `shell_stresses` (standaard uit) en `shell_forces`; alleen route `liml`. Mecway's *stress in element coordinates* (`stressuu` ..) niet. Element orientation als last: niet gelezen ([`Handleiding.md`](Handleiding.md) §4.1). |
| Balkspanning | Deels | Alleen kleinste/grootste axiale spanning bij rechthoekige en ronde doorsneden (`beamsixxmin/max`). |
| Snedekrachten en -momenten van balken | Ja | Veld `beam_forces` (`tensileforce`, `sheary`, `shearz`, `torsion`, `bendingmomv/w`), ook per mode. |
| Reactiekrachten en -momenten | Ja | Niet bij mode superposition, harmonisch en vibro-akoestiek (KB54, KB59). |
| Snelheid, versnelling | Ja | Dynamica; versnelling niet bij mode superposition (KB54). |
| Plastische rek, equivalente plastische rek | Deels | Equivalente plastische rek niet bij kinematische versteviging (KB6). |
| Totale rek | Ja | Veld `strain` (standaard uit): `lstrain*`, niet-lineair `greenlagrangestrain*`; schalen boven/midden/onder. Geen logaritmische rek en geen hoofdrekken. |
| Contactdruk, contactstatus | Deels | Veld `contact`: `contactpressure`, `contactstate` (0/1/2). Geen contactschuifspanning en -verplaatsing; glijden (2) NIET geverifieerd. |
| Factor of safety | Ja | Veld `safety_factor` (von Mises, §5). |
| Temperatuur, warmteflux | Ja | Thermisch. |
| Eigenfrequenties, kniklastfactoren, effectieve massa | Ja | Fractie van de effectieve massa anders dan Mecway (KB49). |
| Akoestische druk | Ja | [`Akoestiek.md`](Akoestiek.md). |

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
| Time step size | Ja | D30, T31 en L30 (L30: Mecway's stappen tot de periode plus de knikken van de lasttabellen; zonder stapgrootte `substeps_per_interval`). *Automatic time stepping* niet nagebootst: vaste stap, Code-Aster knipt alleen bij divergentie. |
| Uitvoertijden, *Generate solution every n time steps* | Ja | |
| Automatic time stepping | Nee | Zonder melding; de bridge halveert de stap zelf bij divergentie. |
| Incompatible hex8 | Nee | KB1. |
| Configuraties | Ja | Eén per run, te kiezen op het startscherm (*Configuratie*); resultaten in de solution van die configuratie ([`Handleiding.md`](Handleiding.md) §4, LS-20). |
| Custom model definition (CCX, OpenRadioss, Nastran) | Deels | Alleen `#ASTER`-regels; gewone CCX-kaarten zonder melding genegeerd. |
