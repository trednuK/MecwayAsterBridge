# AGENTS.md

Mecway → Code-Aster bridge: `.liml` → mesh (ASTER-formaat) + `study.comm`/`.export` → Code-Aster →
resultaten terug in Mecway (standaard in de `.liml` zelf, `aster_results_export.py`). Entry point, architectuur en werkvolgorde staan in
`Scripts/MecwayAsterBridgeMain.py`. De code is leidend; gebruikersdocs in `docs/` bijhouden.

Bekende fouten staan in `KNOWN_BUGS.md`. Vind je een fout die niet bij je huidige taak hoort, los hem dan
niet op, maar zet hem daar (in het formaat bovenin dat bestand). Los je er een op, haal hem er dan uit.
Geplande uitbreidingen en de werkwijze daarvoor staan in `STAPPENPLAN.md` (uitvoeren met `/stappenplan`).

## Runtime

- Draait in **IronPython 2.7.9** (Mecway). Schrijf Python 2.7-code: geen f-strings,
  type hints of `pathlib`, en gebruik `"{0}".format(x)`.
- Alleen de standaardbibliotheek, plus `clr`/WinForms in `bridge_gui.py`. Geen pip-pakketten.
- Uitzonderingen (Python 3 van Code-Aster): `aster_results_export.py` en
  `aster_spectrum.py`, `aster_acoustic_export.py`, `aster_acoustic_complex.py` (ook scipy uit de
  Code-Aster-installatie), `aster_cyclic.py`, `aster_fatigue.py` (in de job) en
  het convergentiescherm `aster_convergence_monitor.py` (apart proces, tkinter). De
  parser `bridge_convergence.py` is gedeeld en moet in 2.7 en 3 werken
  (test: `python tests/test_bridge_convergence.py`).
- `mw` en `solution` bestaan alleen in het hoofdscript; geef ze als parameter door aan de `bridge_*`-modules.
- Mecway-API: alleen wat in Mecway's scripting-documentatie staat (Mecway-handleiding;
  lokaal eventueel `API_reference Mecway.txt`, auteursrecht Mecway Ltd, niet in de repo). Er is geen API om
  loads/constraints te lezen, dus haal BC's, materialen en selecties uit de
  `.liml`-XML (`bridge_from_liml.py`). Code-Aster: v17.4.

## Branches en bestanden

- Werk op `develop`. `main` werkt de gebruiker zelf bij vanuit `develop` (release); push `main` niet zelf.
- Mecway draait de scripts uit de hoofdcheckout (de map van deze repo waaruit Mecway
  `MecwayAsterBridgeMain.py` start). Wissel daar niet van branch.
- `WorkDir/` is gegenereerde output (gitignored); test in een tijdelijke map.
  `TestFiles/*.liml` zijn testmodellen.
- Deze repo is openbaar: inhoud, commitboodschap en tijdstip van elke commit zijn publiek. Commit geen
  persoonsgegevens of eigen paden (ook niet via een door het startscherm opgeslagen `bridge_utils.py`, zie
  hieronder) en wis de auteursnaam in de metadata van Office- en pdf-bestanden.
- Afspraken en paden die alleen voor één pc gelden horen in `CLAUDE.local.md` (gitignored, door Claude Code
  naast `CLAUDE.md` gelezen), niet in dit bestand.

## `bridge_utils.py` / `CONFIG_BRIDGE`

Het startscherm (`bridge_gui.save_to_bridge_utils`) herschrijft dit blok regel voor regel
met een regex. Een diff hier kan dus een opgeslagen instelling zijn; `.bak` is normaal.

- Eén sleutel per regel: `"sleutel":   waarde,`. Alleen lijsten mogen over meerdere
  regels lopen. Zet in dit blok geen expressies of variabelen.
- Een nieuwe instelling: sleutel in `CONFIG_BRIDGE` + entry in `GENERAL_SPECS`/`ANALYSIS_SPECS` (`bridge_gui.py`)
  + uitleg (tooltip) in `bridge_glossary.SETTING_HELP`; een nieuwe keuzewaarde of code in `GLOSSARY`.
- Een nieuw document in `docs/` (en `docs/en/`) ook in `bridge_docs.DOCS` (pagina Documentatie).
- Paden zonder persoonsgegevens: `exe_aster` standaard `%LOCALAPPDATA%\code_aster\...`, `work_dir`
  standaard `""` (= `WorkDir` naast `Scripts/`). Lees ze altijd via `bridge_utils.exe_aster_path()` en
  `work_dir_path()` (omgevingsvariabelen ingevuld, standaardwerkmap), nooit rechtstreeks uit `CONFIG_BRIDGE`.
- `BRIDGE_VERSION` (buiten `CONFIG_BRIDGE`) is de versie op het startscherm en in het log; bij een
  release ook `CHANGELOG.md` bijwerken.

## Uitbreiden

| Wat | Waar |
|---|---|
| BC/belasting | subklasse van `BaseBC` in `bridge_bcs.py` (`parse_xml`, `to_aster_dict`) + `SUPPORTED_BCS` onder de `.liml`-tagnaam |
| Analysetype | `Scripts/AsterTemplate_<Naam>.comm` + builder in `bridge_to_aster.py` + `SOLVER_BUILDERS_ASTER` + entry in `CONFIG_BRIDGE["analyses"]` |
| Resultaatveld | groep in `RESULT_FIELD_SPECS` (`bridge_from_aster.py`; ook de keuzelijst op het startscherm) + `FIELD_TABLE` in `aster_results_export.py` (route `liml`, standaard) + voor route `tabel` POST_RELEVE_T met dezelfde INTITULE in `bridge_to_aster._result_tables` |
| Sectie-/materiaaltype | `_parse_geometric_props()` / materiaalblok in `bridge_from_liml.py`; OpenRadioss-kaarten (PLAS_TAB, /FUNCT) in `bridge_radioss.py` |
| Code-Aster-functie zonder Mecway-invoer | gebruiker: `#ASTER`-regels in Mecway's custom model definition (`bridge_custom.py`; voorbeelden in `docs/ASTER_regels_voorbeelden.md`) |

`model_data` (uit `extract_aster_data_from_liml`, aangevuld door `write_mesh`) is het
contract tussen de modules. Lees optionele sleutels met `.get()`.

## Valkuilen

- Mecway-waarden hebben eenheden (`"210 GPa"`, `"10000 mm⁴"`): altijd naar SI via
  `parse_and_convert(val, type)`. Een onbekende eenheid komt ongewijzigd terug
  (met een WARNING in de log); een nieuwe eenheid hoort in de tabellen daar.
- In de templates vult `str.format()` de placeholders `{naam}` in. Een letterlijke
  accolade schrijf je als `{{ }}`.
- `bridge_mesh.py` schrijft het mesh rechtstreeks uit de `.liml` (geen Gmsh: die kapte
  namen af op 8 tekens). Groepsnamen in Code-Aster: letter eerst, alleen letters/cijfers/_,
  max. 24 tekens; `bridge_mesh` hernoemt in `model_data`, dus gebruik groepsnamen uit
  `model_data`. `INTITULE` ≤ 16 tekens.
- Uitvoerbestanden van een run heten `<model>_<run_id><suffix>` (naam van het Mecway-bestand +
  tijdstempel): naam via `bridge_utils.run_name(suffix)`, nooit een vaste naam. Zonder
  `set_run_log()` (rooktest) is het `study<suffix>`.
- `solution.set_variable()` verwacht één waarde per knoop van de laatste Mecway-solve.
- `run_AsterSolver()` wacht niet op Code-Aster; de gebruiker bevestigt via `mw.message()`.

## Controleren

Een echte run kan alleen in Mecway. Hulpmiddelen zonder Mecway-GUI in `TestFiles/Tools/`: `run_ipy.ps1`
(script draaien met Mecway's IronPython 2.7.9), `gui_cap.py` (hoofdvenster offscreen naar PNG), `mw_solve.py`
(Mecway headless laten rekenen als referentie). Offline syntaxcheck (Python 3; Python 2.7-compatibiliteit zelf nalopen):

```bash
cd Scripts && for f in *.py; do python -c "import ast,io;ast.parse(io.open('$f',encoding='utf-8').read())" || echo "FOUT: $f"; done
```

Rooktest liml → mesh/`.comm`/`.export` (CPython, tijdelijke map `T` met `model.liml`, bijv. een
kopie van `TestFiles/Voorbeelden/Voorbeeld_A.liml` (statisch) of `TestFiles/BezwijkenTrekstaaf.liml`
(niet-lineair); de templates staan als bestandsnaam in `CONFIG_BRIDGE` en worden in de map van de
scripts gezocht, `bridge_utils.template_path`):

```python
import sys, shutil; sys.path.insert(0, "Scripts")
import bridge_utils as u; u.CONFIG_BRIDGE["work_dir"] = T   # alleen in geheugen
from bridge_from_liml import extract_aster_data_from_liml
from bridge_mesh import write_mesh
from bridge_to_aster import generate_AsterSolver_files
for name in ("lin_static_3d", "nonlin_static_3d"):
    u.CONFIG_BRIDGE["active_analysis"] = name
    md = extract_aster_data_from_liml(T + "/model.liml")
    assert write_mesh(T + "/model_mesh.mail", md)   # zonder Mecway: faceid-tabel
    assert generate_AsterSolver_files(T, md, T + "/model_mesh.mail", "test.resu")
```

Bekijk daarna `T/study.comm` en `T/bridge_log.txt`. Roep de opslagfuncties van
`bridge_gui` niet aan (die herschrijven `bridge_utils.py`).

## Conventies

- Licentie: MPL-2.0 (`LICENSE`). Een nieuw bronbestand (.py, .comm) krijgt bovenaan (na een
  eventuele coderingsregel) de kop uit `Scripts/bridge_utils.py` (Copyright + MPL-2.0-verwijzing).

- Nederlands in commentaar, logregels en commits. Log met `log("INFO|WARNING|ERROR|SUCCESS: ...")`.
- Tekst voor de gebruiker (startscherm, `mw.message()`, WARNING/ERROR-regels, `skipped_loads`,
  convergentiescherm) in beide talen (`CONFIG_BRIDGE["language"]`):
  `log(tr("WARNING: ... {0}", "WARNING: ... {0}").format(x))` met `tr` uit `bridge_utils`;
  zelfde voorvoegsel en placeholders. INFO/SUCCESS, commentaar en `study.comm` blijven Nederlands.
- Fatale fout in een module: `log("ERROR: ...")` en `None`/`False` teruggeven; `main()` stopt dan met `mw.message()`.
- Onderbouw Code-Aster-gedrag in commentaar met een bron (U-doc, catalogus, `.F90`), anders "NIET geverifieerd".
