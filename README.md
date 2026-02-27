# Italian Real Estate Valuation Tool

Personal, non-commercial tool for property valuation across Italian cities and regions. Aggregates official data from the Agenzia delle Entrate's Osservatorio del Mercato Immobiliare (OMI) to provide EUR/m2 valuations, zone mapping, and comparable transaction tracking.

## Features

- **Address-to-valuation lookup** -- enter an Italian address, get the OMI zone and EUR/m2 price range
- **Interactive map** -- browse OMI zones with color-coded price heatmap (React-Leaflet + OpenStreetMap)
- **Multi-semester trends** -- compare valuations across semesters to see price evolution
- **Manual transaction log** -- record declared transaction values from the Agenzia's web viewer for comparables
- **Multi-city support** -- national coverage (entire Italian territory)

## Tech Stack

- **Backend:** Python 3.12+ / FastAPI / SQLAlchemy + psycopg3
- **Frontend:** React (Vite) + TypeScript + React-Leaflet
- **Database:** PostgreSQL + PostGIS
- **Geocoding:** Nominatim (primary) + Google Geocoding API (fallback)

## Quick Start

```bash
# 1. Start the database (local dev -- uses imresamu/postgis for Apple Silicon support)
docker compose up -d db

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your database credentials and data directory

# 3. Install Python dependencies
cd backend
pip install -e ".[dev]"

# 4. Import OMI data (reads DATA_DIR and DATABASE_URL from .env)
python -m scripts.import_omi

# To reset and re-import everything:
python -m scripts.import_omi --reset

# 5. Start the backend
uvicorn app.main:app --reload

# 6. Start the frontend (from project root)
cd ../frontend && npm install && npm run dev
```

## Data

OMI data files (zip) are stored outside the repo (configured via `DATA_DIR` in `.env`) and downloaded manually from the Agenzia delle Entrate portal (requires SPID authentication). See [docs/data-sources.md](docs/data-sources.md) for details.

**Current dataset:** 25 zip files covering 23 semesters from 2010_S2 to 2025_S1 (~2.4 GB). Full import produces:
- ~620,000 zone polygons (with PostGIS geometries)
- ~3,750,000 quotation rows (EUR/m2 price ranges)

## Import Script

```bash
cd backend

# Normal import (skips already-imported semesters)
python -m scripts.import_omi

# Reset database and re-import everything
python -m scripts.import_omi --reset

# Override data directory or database URL
python -m scripts.import_omi /path/to/data postgresql+psycopg://user:pass@host/db
```

The script handles:
- 3 different KML formats across semesters (2010-2013: direct LINKZONA, 2014_S1: filename+name extraction, 2014_S2+: CODCOM/CODZONA)
- UTF-8 and Latin-1 encoded CSVs (auto-fallback)
- Invalid geometries (ST_MakeValid + ST_CollectionExtract)
- Duplicate detection and safe re-imports
- PostgreSQL COPY protocol for fast bulk loading

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
| [docs/deployment.md](docs/deployment.md) | Docker setup, environment variables, deployment configuration |

## License

Personal use only. OMI data source: Agenzia delle Entrate -- OMI.
