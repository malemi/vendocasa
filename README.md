# Italian Real Estate Valuation Tool

Personal, non-commercial tool for property valuation across Italian cities and regions. Aggregates official data from the Agenzia delle Entrate's Osservatorio del Mercato Immobiliare (OMI) to provide EUR/m2 valuations, zone mapping, and comparable transaction tracking.

## Features

- **Address-to-valuation lookup** -- enter an Italian address, get the OMI zone and EUR/m2 price range
- **Interactive map** -- browse OMI zones with color-coded price heatmap (React-Leaflet + OpenStreetMap)
- **Multi-semester trends** -- compare valuations across semesters to see price evolution
- **Manual transaction log** -- record declared transaction values from the Agenzia's web viewer for comparables
- **Multi-city support** -- national coverage (entire Italian territory)

## Tech Stack

- **Backend:** Python 3.12+ / FastAPI / SQLAlchemy + GeoAlchemy2
- **Frontend:** React (Vite) + TypeScript + React-Leaflet
- **Database:** PostgreSQL + PostGIS
- **Geocoding:** Nominatim (primary) + Google Geocoding API (fallback)
- **Deployment:** Railway (~$5/month hobby plan)

## Quick Start

```bash
# 1. Start the database (local dev)
docker compose up -d db

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your database credentials and data directory

# 3. Import OMI data (reads DATA_DIR and DATABASE_URL from .env)
cd backend
python -m scripts.import_omi

# 4. Start the backend
uvicorn app.main:app --reload

# 5. Start the frontend (from project root)
cd ../frontend && npm run dev
```

## Data

OMI data files (zip) are stored in `./data/` and downloaded manually from the Agenzia delle Entrate portal (requires SPID authentication). See [docs/data-sources.md](docs/data-sources.md) for details on data formats, update procedures, and legal considerations.

## Documentation

See the `docs/` directory:

| File | Topic |
|------|-------|
| [docs/index.md](docs/index.md) | Documentation index |
| [docs/architecture.md](docs/architecture.md) | System architecture, tech stack, deployment |
| [docs/data-sources.md](docs/data-sources.md) | OMI data formats, CSV schemas, KML structure, download procedures |
| [docs/data-pipeline.md](docs/data-pipeline.md) | Import scripts, ETL process, semiannual update workflow |
| [docs/api.md](docs/api.md) | Backend API endpoints reference |
| [docs/valuation-methodology.md](docs/valuation-methodology.md) | How valuations are calculated, limitations, caveats |
| [docs/legal.md](docs/legal.md) | Data licensing, personal use scope, restrictions |
| [docs/deployment.md](docs/deployment.md) | Railway setup, environment variables, Docker configuration |

## License

Personal use only. OMI data source: Agenzia delle Entrate -- OMI.
