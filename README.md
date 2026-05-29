# Breathe ESG — Data Ingestion Platform

Django REST + React prototype for ingesting, normalizing, and reviewing emissions data from SAP, utility portals, and corporate travel platforms.

## Quick Start (Local)

### Backend
```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python setup_demo.py        # seeds demo tenant + user
python manage.py runserver
```

### Frontend
```bash
cd frontend
cp .env.example .env        # set REACT_APP_API_URL=http://localhost:8000
npm install
npm start
```

**Demo credentials:** `analyst` / `demo1234`

## Architecture

- **Django REST Framework** — API, auth (token), ingestion endpoints
- **SQLite (dev) / PostgreSQL (prod)** — auto-selected via `DATABASE_URL` env var
- **React** — SPA with recharts for visualization

## Deployment (Railway)

1. Create Railway project
2. Add PostgreSQL plugin → copy `DATABASE_URL`
3. Deploy backend: set env vars `DATABASE_URL`, `SECRET_KEY`, `DEBUG=False`
4. Deploy frontend: set `REACT_APP_API_URL` to backend URL

See docs/ for full data model and decision documentation.

## Sample Data Files

Upload these from `sample_data/` via the Ingest page:
- `sap_fuel_export.csv` — SAP fuel & procurement (Scope 1/3)
- `utility_electricity.csv` — Utility portal CSV (Scope 2)
- `corporate_travel.json` — Navan/Concur-shaped travel data (Scope 3)

## Documentation
- `docs/MODEL.md` — Data model design and rationale
- `docs/DECISIONS.md` — Every ambiguity resolved
- `docs/TRADEOFFS.md` — Three things deliberately not built
- `docs/SOURCES.md` — Research on each data source format
