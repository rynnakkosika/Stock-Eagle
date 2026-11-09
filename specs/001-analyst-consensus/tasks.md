# Tasks: Analyytikkosuositusten koontinäkymä

**Input**: plan.md, spec.md, data-model.md, contracts/source-adapter.md, research.md

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [X] T001 Luo projektirakenne (`stock_eagle/`, `stock_eagle/sources/`, `tests/`, `config/`, `data/`)
- [X] T002 [P] `requirements.txt`, `.env.example`, `.gitignore`, `pytest.ini`
- [X] T003 [P] `setup.bat` ja `run.bat` Windowsille

## Phase 2: Foundational

- [X] T004 `stock_eagle/models.py` – dataclassit (Stock, Recommendation, Quote, StockInfo, SourceResult)
- [X] T005 `stock_eagle/config.py` – .env-lataus, Settings, seurantalistan luku
- [X] T006 `config/watchlist.toml` – oletusseurantalista (Helsinki)
- [X] T007 `stock_eagle/scale.py` + `tests/test_scale.py`
- [X] T008 `stock_eagle/db.py` + `tests/test_db.py`
- [X] T009 `stock_eagle/sources/base.py` + rekisteri `sources/__init__.py` + `tests/test_registry.py`
- [X] T010 `stock_eagle/refresh.py` + `tests/test_refresh.py`

## Phase 3: US1+US2 – Ranking ja päivitys (P1) 🎯 MVP

- [X] T011 [US1] `stock_eagle/consensus.py` + `tests/test_consensus.py` (konsensus, nousuvara, järjestys, suodatus)
- [X] T012 [US1] `stock_eagle/sources/finnhub.py` + `tests/test_finnhub.py` (vastaukset mockattuina)
- [X] T013 [US1] `stock_eagle/sources/demo.py` (aktiivinen vain ilman Finnhub-avainta)
- [X] T014 [US1/US2] `app.py` – ranking-välilehti, suodattimet, Päivitä-nappi, lähteiden hakuajat, vastuuvapaus

## Phase 4: Inderes-lähde

- [X] T015 `stock_eagle/sources/inderes.py` + `tests/test_inderes.py` (tallennettu HTML-fixture)

## Phase 5: US3+US4 – Osakenäkymä ja muutokset (P2/P3)

- [X] T016 [US3/US4] `stock_eagle/changes.py` + `tests/test_changes.py`
- [X] T017 [US3] `app.py` – osakenäkymä (lähteittäin, linkit, historia)
- [X] T018 [US4] `app.py` – muutosnäkymä (aikaikkuna)

## Phase 6: Polish

- [X] T019 README (Windows-ohjeet, yhteenveto, keskeneräiset)
- [X] T020 Aja pytest, korjaa virheet, varmista Streamlitin käynnistys
- [X] T021 Päivitä DECISIONS.md

## Dependencies

Phase 1 → 2 → 3 → 4 → 5 → 6. Testit kirjoitetaan samassa tehtävässä kuin moduuli.
