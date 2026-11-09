# Quickstart (Windows)

1. Asenna Python 3.11+ (python.org) tai uv.
2. Projektikansiossa: `setup.bat` (luo `.venv` ja asentaa riippuvuudet).
3. (Valinnainen) kopioi `.env.example` → `.env` ja lisää `FINNHUB_API_KEY`.
4. `run.bat` → selain avautuu osoitteeseen http://localhost:8501.
5. Paina sivupalkista **Päivitä data**.

Validointi: `.venv\Scripts\python -m pytest` → kaikki testit läpi.
