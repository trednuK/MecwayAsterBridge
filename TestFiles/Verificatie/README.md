# Verificatietests MecwayAsterBridge

Tests die FEM-resultaten van de bridge (Mecway .liml → Code-Aster 17.4) vergelijken met
analytische oplossingen en benchmarks. Toelichting, bronnen en resultaten:
[`docs/Verificatie.md`](../../docs/Verificatie.md) (English: `docs/en/Verification.md`).

- `run_verificatie.py` – draait de tests (`python run_verificatie.py [ids]`); welke ids een
  wijziging raakt: `TestFiles/Tools/regression_scope.py` (`STAPPENPLAN.md` D.5)
- `verif_lib.py`, `_run_one.py` – kader (modelbouw, run, resultaten, vergelijking)
- `tests_*.py` – de testcases per groep
- `modellen/` – de gegenereerde Mecway-modellen
- `resultaten/` – rapport (`resultaten.md`), `.csv`, `.json` en de `.comm` per test;
  `resultaten/mecway/vergelijking.md`: dezelfde tests met door Mecway opgeslagen modellen
  (`--mecway-opslaan`)
- `code_aster_testcases/` – officiële Code-Aster-validatietests uit de installatie
