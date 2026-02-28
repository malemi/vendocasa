# VendoCasa Documentation

Italian Real Estate Valuation Tool powered by OMI data, PostGIS spatial queries, and an AI conversational agent.

## Documentation Overview

### Core

- **[Architecture](architecture.md)** - System architecture, tech stack, database schema, request flow
- **[Valuation Methodology](valuation-methodology.md)** - Geocoding, zone lookup, OMI quotations, correction coefficients, Freakonomics agent incentives
- **[API Reference](api.md)** - All REST endpoints, request/response schemas, SSE streaming chat

### Data

- **[Data Sources](data-sources.md)** - OMI data ecosystem: CSV column schemas, KML structure, LinkZona join key, download procedures
- **[Data Pipeline](data-pipeline.md)** - Import scripts: zip scanning, CSV parsing, KML-to-PostGIS ingestion, semester detection

### Operations

- **[Deployment](deployment.md)** - Railway (backend) + Vercel (frontend) + Supabase (PostGIS), environment variables, CI/CD
- **[Legal](legal.md)** - OMI data licensing, declared transaction values, personal use scope

## Quick Navigation

### For Users

1. Open the app and type an address in the chat (e.g. "Via Sottocorno 17, Milano, 62mq")
2. The AI agent asks about your property details conversationally
3. View the valuation inline with zone map overlay
4. Learn about agent incentive misalignment (Freakonomics)

### For Developers

1. Review **[Architecture](architecture.md)** for system design and database schema
2. Check **[API Reference](api.md)** for all endpoints including SSE streaming
3. Follow **[Deployment](deployment.md)** for local dev setup and production deployment
4. Read **[Data Pipeline](data-pipeline.md)** before running imports

### For Data Analysts

1. Start with **[Data Sources](data-sources.md)** to understand OMI CSV/KML formats
2. Review **[Valuation Methodology](valuation-methodology.md)** for the calculation pipeline
3. Check **[Legal](legal.md)** for data licensing constraints

## Architecture

```
Vercel                         Railway                        Supabase
(React + Vite + Leaflet)  -->  (FastAPI + GDAL)          --> (PostgreSQL + PostGIS)
                               |                              |
                               +-- AI Chat Agent              +-- omi.zones (polygons)
                               |   (Claude Sonnet 4, SSE)     +-- omi.quotations (EUR/m2)
                               +-- Geocoding                  +-- omi.transactions
                               |   (Nominatim + Google)       +-- omi.geocode_cache
                               +-- Spatial Queries
                                   (ST_Intersects)
```

### Key Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frontend | React, Vite, Leaflet, TypeScript | Chat UI + interactive zone map |
| Backend | FastAPI, Python 3.12+, GDAL | REST API, geocoding, spatial queries, AI agent |
| Database | PostgreSQL + PostGIS (Supabase) | Zone polygons, quotation prices, transactions |
| AI Agent | Anthropic Claude Sonnet 4, SSE streaming | Conversational property valuation |
| Geocoding | Nominatim (primary) + Google (fallback) | Address to lat/lng conversion |

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL with PostGIS (or `docker compose up -d db`)
- OMI zip files from Agenzia delle Entrate (SPID required for download)

### Local Development

```bash
# 1. Database (PostGIS via Docker)
docker compose up -d db

# 2. Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your DATABASE_URL
uvicorn app.main:app --reload

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev

# 4. Import OMI data
cd backend
python -m scripts.import_omi /path/to/omi/zips
```

The app runs at http://localhost:5173 with API proxy to http://localhost:8000.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | yes | PostgreSQL+PostGIS connection string |
| `ANTHROPIC_API_KEY` | for chat | Anthropic API key for AI agent |
| `GOOGLE_GEOCODING_API_KEY` | no | Google Maps fallback geocoder |
| `CORS_ORIGINS` | production | Comma-separated allowed origins |
| `DATA_DIR` | for import | Path to OMI zip files |

## Data Source

All property valuation data comes from the **Osservatorio del Mercato Immobiliare (OMI)**, part of the Agenzia delle Entrate. OMI publishes semiannual expert-assessed EUR/m2 price ranges for ~8,000 micro-zones covering all of Italy.

Each semester provides:
- **~158,000 quotation rows** (price ranges by zone, property type, conservation state)
- **~8,000 KML polygons** (zone boundaries for PostGIS spatial queries)
- **~27,000 zone descriptions** (municipality, fascia, zone code)

See **[Data Sources](data-sources.md)** for full CSV/KML column schemas and **[Data Pipeline](data-pipeline.md)** for the import process.

## How Valuation Works

```
Address --> Geocode --> Zone Lookup --> OMI Quotations --> Basic Estimate
                                                              |
                                                              v
                                                    AI Agent asks about:
                                                    conservation, floor,
                                                    exposure, noise, etc.
                                                              |
                                                              v
                                                    Correction Coefficients
                                                    applied (+/- %)
                                                              |
                                                              v
                                                    Enhanced Estimate
```

1. **Geocoding**: Address to lat/lng (Nominatim, cached in DB)
2. **Zone lookup**: `ST_Intersects` finds which OMI polygon contains the point
3. **Quotation retrieval**: EUR/m2 min/max for zone + property type + conservation state
4. **Basic estimate**: Midpoint of price range * surface area
5. **Enhanced estimate**: AI agent collects property details conversationally, applies correction coefficients (Italian appraisal methodology)
6. **Agent incentives**: Freakonomics-based education on real estate agent behavior

See **[Valuation Methodology](valuation-methodology.md)** for the complete calculation pipeline and coefficient table.

## Repository Structure

```
vendocasa/
+-- docs/                          # Documentation (you are here)
+-- data/                          # OMI zip files (not in git, ~2.4 GB)
+-- backend/
|   +-- app/
|   |   +-- main.py                # FastAPI app + CORS middleware
|   |   +-- config.py              # Settings (reads .env via pydantic-settings)
|   |   +-- database.py            # Async SQLAlchemy engine
|   |   +-- models/                # ORM models (Zone, Quotation, Transaction)
|   |   +-- schemas/               # Pydantic request/response schemas
|   |   +-- api/                   # Route handlers
|   |   |   +-- chat.py            # POST /api/chat (SSE streaming)
|   |   |   +-- valuations.py      # GET /api/valuate, POST /api/valuate/enhanced
|   |   |   +-- zones.py           # GET /api/zones/geojson
|   |   |   +-- semesters.py       # GET /api/semesters
|   |   |   +-- transactions.py    # CRUD for manual transactions
|   |   +-- services/              # Business logic
|   |       +-- agent.py           # AI chat agent (Claude, tool calling, SSE)
|   |       +-- valuation.py       # Geocoding + zone lookup + estimate
|   |       +-- coefficients.py    # Correction coefficient system
|   +-- scripts/                   # Import scripts
|   |   +-- import_omi.py          # Unified entry point
|   |   +-- import_omi_zones.py    # KML -> PostGIS importer
|   |   +-- import_omi_quotations.py # CSV -> COPY importer
|   +-- sql/
|   |   +-- 001_schema.sql         # Database DDL
|   +-- .env.example               # Template (placeholder values)
|   +-- Dockerfile                 # Production container (GDAL + Python)
|   +-- pyproject.toml             # Dependencies
+-- frontend/
|   +-- src/
|   |   +-- components/
|   |   |   +-- Chat/              # AI chat interface
|   |   |   |   +-- ChatPanel.tsx  # Main chat UI (messages + input)
|   |   |   |   +-- ChatMessage.tsx # Message bubbles
|   |   |   |   +-- InlineToolResult.tsx # Valuation cards in chat
|   |   |   +-- Map/               # Leaflet map with zone overlay
|   |   |   +-- Layout/            # Sidebar + responsive layout
|   |   +-- api/client.ts          # API client (axios + SSE streaming)
|   |   +-- types/index.ts         # TypeScript types
|   +-- package.json
+-- railway.toml                   # Railway deployment config
+-- vercel.json                    # Vercel deployment config
+-- docker-compose.yml             # Local dev (PostGIS container)
```

## Deployment

```
Production:  Vercel (frontend) + Railway (backend) + Supabase (PostgreSQL + PostGIS)
Local dev:   Vite dev server + uvicorn --reload + Docker PostGIS
```

See **[Deployment](deployment.md)** for full setup instructions.

## Legal

OMI quotation data is freely downloadable from the Agenzia delle Entrate. Personal use is unrestricted. Declared transaction values (manual entries) cannot be redistributed commercially. See **[Legal](legal.md)** for details.

---

**Data source:** Agenzia delle Entrate -- Osservatorio del Mercato Immobiliare (OMI)
