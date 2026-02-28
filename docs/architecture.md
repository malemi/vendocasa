# System Architecture

## High-Level Topology

```
+-------------------+     +------------------------+     +------------------+
|  React Frontend   |---->|  FastAPI Backend        |---->|  PostgreSQL +    |
|  (Vite + Leaflet) |     |  (Python 3.12+)        |     |  PostGIS         |
|  on Vercel        |     |  on Railway             |     |  on Supabase     |
+-------------------+     +-------+----------------+     +------------------+
                                  |
                                  v
                          +----------------+
                          |  Anthropic API |
                          |  (Claude       |
                          |   Sonnet 4)    |
                          +----------------+
```

Four services:
1. **React frontend** (Vercel) -- chat interface + interactive Leaflet map with zone overlay
2. **FastAPI backend** (Railway) -- REST API, geocoding, spatial queries, AI agent orchestration
3. **PostgreSQL + PostGIS** (Supabase) -- OMI zones (polygons), quotations (price data), transactions
4. **Anthropic Claude** (external API) -- conversational AI agent with programmatic tool calling

## Tech Stack Rationale

| Choice | Why |
|--------|-----|
| **FastAPI** | Async, automatic OpenAPI docs, Pydantic validation, SSE streaming support |
| **PostGIS** (not plain Postgres) | OMI zones are polygons; need `ST_Intersects` and `ST_DWithin` for spatial point-in-polygon queries. Plain Postgres cannot do this |
| **Supabase** (not Railway Postgres) | Managed PostgreSQL with PostGIS enabled by default, free tier, connection pooling via Supavisor |
| **React-Leaflet** (not Mapbox) | Free, no API key required, OpenStreetMap tiles, good enough for zone overlay display |
| **SQLAlchemy + GeoAlchemy2** | Industry-standard async ORM with PostGIS geometry type support |
| **Anthropic Claude Sonnet 4** | Programmatic tool calling for conversational valuation flow, SSE streaming |
| **Nominatim** (primary geocoder) | Free, no API key, cacheable permanently under ODbL license |
| **Google Geocoding** (fallback) | Better address parsing for Italian addresses when Nominatim fails |

## Database Schema

### Schema: `omi`

**omi.zones** -- Zone polygons (one row per zone per semester)
```sql
CREATE TABLE omi.zones (
    id                  SERIAL PRIMARY KEY,
    link_zona           VARCHAR(12) NOT NULL,   -- e.g. "AG00000027" (join key)
    zone_code           VARCHAR(10) NOT NULL,   -- e.g. "B01"
    fascia              VARCHAR(5),             -- B/C/D/E/R
    municipality_istat  VARCHAR(10) NOT NULL,   -- ISTAT code
    municipality_name   TEXT,
    province_code       VARCHAR(3),
    zone_description    TEXT,
    semester            VARCHAR(7) NOT NULL,    -- e.g. "2025_S1"
    geom                GEOMETRY(MultiPolygon, 4326) NOT NULL,
    UNIQUE(link_zona, semester)
);
```

**omi.quotations** -- Price data (multiple rows per zone per semester)
```sql
CREATE TABLE omi.quotations (
    id                  SERIAL PRIMARY KEY,
    link_zona           VARCHAR(12) NOT NULL,
    semester            VARCHAR(7) NOT NULL,
    property_type_code  INTEGER,
    property_type_desc  VARCHAR(60),
    conservation_state  VARCHAR(30),
    is_prevalent        BOOLEAN DEFAULT FALSE,
    price_min           NUMERIC(10,2),
    price_max           NUMERIC(10,2),
    surface_type_sale   CHAR(1),
    rent_min            NUMERIC(10,2),
    rent_max            NUMERIC(10,2),
    surface_type_rent   CHAR(1),
    UNIQUE(link_zona, semester, property_type_code, conservation_state)
);
```

Note: there is **no foreign key** from `quotations` to `zones`. Not every `link_zona` in the quotation CSVs has a corresponding KML polygon (some zones lack geographic perimeters). The join is done at query time via the shared `link_zona` + `semester` columns.

**omi.transactions** -- Manually entered comparable sales
```sql
CREATE TABLE omi.transactions (
    id                  SERIAL PRIMARY KEY,
    transaction_date    DATE,
    transaction_type    VARCHAR(30),
    declared_price      NUMERIC(12,2),
    municipality        TEXT,
    omi_zone            VARCHAR(10),
    link_zona           VARCHAR(12),
    cadastral_category  VARCHAR(10),
    cadastral_vani      NUMERIC(6,1),
    cadastral_mq        NUMERIC(8,1),
    cadastral_mc        NUMERIC(8,1),
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

**omi.geocode_cache** -- Cached geocoding results
```sql
CREATE TABLE omi.geocode_cache (
    address             TEXT PRIMARY KEY,
    lat                 DOUBLE PRECISION,
    lng                 DOUBLE PRECISION,
    source              VARCHAR(30),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### Indexes

```sql
-- Spatial index for ST_Intersects / ST_DWithin queries
CREATE INDEX idx_zones_geom ON omi.zones USING GIST (geom);
-- Fast lookup by join key
CREATE INDEX idx_zones_link ON omi.zones (link_zona);
CREATE INDEX idx_zones_semester ON omi.zones (semester);
-- Quotation lookup
CREATE INDEX idx_quot_lookup ON omi.quotations (link_zona, semester);
CREATE INDEX idx_quot_type ON omi.quotations (property_type_code);
```

## AI Chat Agent

The frontend presents a conversational chat interface instead of a form-based wizard. The backend orchestrates an AI agent that gathers property details through natural conversation and calls valuation tools programmatically.

### Agent Architecture

```
User message
     |
     v
POST /api/chat (SSE stream)
     |
     v
Claude Sonnet 4 (with system prompt + 4 tools)
     |
     +---> tool_use: valuate_property -----> valuation service ---> DB
     +---> tool_use: enhanced_valuate -----> coefficient service --> DB
     +---> tool_use: get_coefficient_info -> coefficient options
     +---> tool_use: get_zone_quotations --> quotation service ---> DB
     |
     v
SSE events streamed to frontend:
  - text_delta: token-by-token text
  - tool_result: structured valuation data (rendered as inline cards)
  - map_update: coordinates for map flyTo
  - done: stream complete
```

### Tool Definitions

| Tool | Backend Service | Purpose |
|------|----------------|---------|
| `valuate_property` | `valuate_address()` | Geocode + zone lookup + basic OMI estimate |
| `enhanced_valuate_property` | `enhanced_valuate_address()` | Apply correction coefficients for adjusted estimate |
| `get_coefficient_info` | `get_coefficient_options()` | List available coefficient factors and options |
| `get_zone_quotations` | `get_quotations()` | Deep dive on zone price data |

The agent loop runs up to 5 tool rounds per request. Tool execution is entirely server-side; the frontend only receives streamed text and structured results.

### System Prompt

The agent operates as an Italian-speaking real estate consultant:
1. Asks for address and surface area
2. Calls `valuate_property` for initial OMI lookup
3. Gathers property details conversationally (2-3 questions at a time, not all at once)
4. Calls `enhanced_valuate_property` with collected details
5. Explains Freakonomics agent incentive misalignment using concrete numbers from the valuation
6. Provides practical advice (get 3 valuations, negotiate commission, verify track record)

## Request Flow: Address Valuation

### Via REST API (direct)

```
GET /api/valuate?address=...&surface_m2=...
        |
        v
[1] Geocode address --> lat/lng
    - Check omi.geocode_cache first
    - Try Nominatim (free, 1 req/sec)
    - Fallback to Google Geocoding API
    - Cache result in DB
        |
        v
[2] Spatial lookup: ST_Intersects(zone.geom, point)
    - Find which OMI zone polygon contains the point
    - If no exact match, fallback to ST_DWithin(200m)
        |
        v
[3] Fetch quotations for zone + semester
    - JOIN omi.quotations ON link_zona + semester
    - Filter by property_type_code
    - Sort by is_prevalent DESC
        |
        v
[4] Fetch comparable transactions
    - SELECT from omi.transactions WHERE link_zona or omi_zone matches
        |
        v
[5] Compute estimate
    - Midpoint of prevalent price_min/price_max * surface_m2
    - Return range (min, mid, max) + comparables
```

### Via AI Chat (conversational)

```
User types message in chat
        |
        v
POST /api/chat (SSE)
        |
        v
Claude orchestrates steps [1]-[5] via tool calls
        |
        v
Streams text explanation + inline valuation cards + map updates
```

## Directory Structure

```
vendocasa/
+-- README.md
+-- docs/                          # Project documentation
+-- data/                          # OMI zip files (not in git, ~2.4 GB)
+-- backend/
|   +-- app/
|   |   +-- main.py                # FastAPI app + CORS middleware
|   |   +-- config.py              # Settings (pydantic-settings, reads .env)
|   |   +-- database.py            # Async SQLAlchemy engine
|   |   +-- models/                # ORM models (Zone, Quotation, Transaction)
|   |   +-- schemas/               # Pydantic request/response schemas
|   |   +-- api/                   # Route handlers
|   |   |   +-- chat.py            # POST /api/chat (SSE streaming)
|   |   |   +-- valuations.py      # Valuation endpoints
|   |   |   +-- zones.py           # Zone GeoJSON endpoints
|   |   |   +-- semesters.py       # Available semesters
|   |   |   +-- transactions.py    # Transaction CRUD
|   |   +-- services/              # Business logic
|   |       +-- agent.py           # AI agent (Claude, tools, SSE loop)
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
|   +-- pyproject.toml
+-- frontend/
|   +-- src/
|   |   +-- components/
|   |   |   +-- Chat/              # AI chat interface
|   |   |   |   +-- ChatPanel.tsx  # Main chat UI
|   |   |   |   +-- ChatMessage.tsx # Message bubbles
|   |   |   |   +-- InlineToolResult.tsx # Valuation cards
|   |   |   +-- Map/               # Leaflet map + zone overlay
|   |   |   +-- Layout/            # Sidebar + responsive layout
|   |   +-- api/client.ts          # API client (axios + SSE streaming)
|   |   +-- types/index.ts         # TypeScript types
|   +-- package.json
+-- railway.toml                   # Railway deployment config
+-- vercel.json                    # Vercel deployment config
+-- docker-compose.yml             # Local dev (PostGIS container)
```
