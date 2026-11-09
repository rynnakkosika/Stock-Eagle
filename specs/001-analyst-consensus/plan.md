# Implementation Plan: Analyytikkosuositusten koontinäkymä

**Branch**: `001-analyst-consensus` | **Date**: 2026-11-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-analyst-consensus/spec.md`

## Summary

Paikallinen Streamlit-sovellus, joka hakee analyytikkosuositukset adapter-moduuleilla (Finnhub,
Inderes, demo), tallentaa ne SQLiteen snapshot-historiana, yhtenäistää ne asteikolle 1–5 ja laskee
osakkeittain konsensuksen, keskitavoitehinnan ja nousuvaran. Kolme näkymää: ranking, osake, muutokset.

## Technical Context

**Language/Version**: Python 3.11+ (kehitetty 3.13:lla uv:n kautta)
**Primary Dependencies**: streamlit, pandas, requests, python-dotenv
**Storage**: SQLite (`data/stock_eagle.db`), ohitettavissa `STOCK_EAGLE_DB`-muuttujalla
**Testing**: pytest (ei verkkokutsuja; adapterit testataan tallennetuilla vastauksilla/monkeypatchilla)
**Target Platform**: Windows 10/11 -työpöytä, selain localhost:8501
**Project Type**: Yksittäinen Python-projekti + Streamlit-käyttöliittymä
**Performance Goals**: Näkymät tallennetusta datasta < 2 s; täysi päivitys ~40 osakkeelle muutamassa
minuutissa (Finnhub 60 kutsua/min, Inderes 1 pyyntö / 1,5 s)
**Constraints**: Ei palvelinta, ei maksullisia palveluita, avaimet vain `.env`:ssä
**Scale/Scope**: Kymmeniä–satoja osakkeita, yksi käyttäjä

## Constitution Check

| Periaate | Toteutus | OK |
|---|---|---|
| I Laillinen data | Finnhub virallinen API; Inderes julkinen sivu, robots.txt `Allow: /`, käyttöehdot sallivat henkilökohtaisen katselun/latauksen; hidas tahti, tunnistettava User-Agent, ei kirjautumista | ✅ |
| II Jäljitettävyys | Jokaisella snapshotilla `source_id`, `url`, `fetched_at`, `last_seen_at` | ✅ |
| III Ei neuvontaa | Vastuuvapauslauseke sivupalkissa; järjestys on lajittelu | ✅ |
| IV Laajennettavuus | `stock_eagle/sources/` – automaattinen löytö `pkgutil`:lla, `SourceAdapter`-rajapinta | ✅ |
| V Paikallinen | SQLite + Streamlit localhost | ✅ |
| VI Salaisuudet | `.env` + `.gitignore`, avain HTTP-otsakkeessa (ei URL:ssa/lokeissa) | ✅ |
| VII Testit | `tests/` kattaa scale, consensus, changes, db, adapter-parsinnan | ✅ |

## Project Structure

### Documentation (this feature)

```text
specs/001-analyst-consensus/
├── plan.md  research.md  data-model.md  quickstart.md
├── contracts/source-adapter.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
app.py                      # Streamlit-käyttöliittymä
stock_eagle/
├── config.py               # .env, polut, seurantalista
├── models.py               # dataclassit
├── scale.py                # suositusasteikon yhtenäistys
├── consensus.py            # konsensus, nousuvara, järjestys, suodatus
├── changes.py              # nostojen/laskujen tunnistus
├── db.py                   # SQLite-repo
├── refresh.py              # päivitysajo kaikille adaptereille
└── sources/
    ├── __init__.py         # rekisteri (automaattinen löytö)
    ├── base.py             # SourceAdapter-rajapinta
    ├── finnhub.py
    ├── inderes.py
    └── demo.py
config/watchlist.toml       # seurattavat osakkeet + lähdetunnisteet
tests/
```

**Structure Decision**: Yksi Python-paketti; käyttöliittymä ohuena kerroksena `app.py`:ssä, jotta
logiikka on testattavissa ilman Streamlitiä.

## Complexity Tracking

Ei poikkeamia perustuslaista.
