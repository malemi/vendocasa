# System Architecture

## High-Level Topology

```
+-------------------+     +------------------------+     +------------------+
|  React Frontend   |---->|  FastAPI Backend        |---->|  PostgreSQL +    |
|  (Vite + Leaflet) |     |  (Python 3.12+)        |     |  PostGIS         |
|  on Vercel/       |     |  on Railway             |     |  on Railway      |
|  Railway static   |     |                         |     |  (PostGIS tmpl)  |
+-------------------+     +------------------------+     +------------------+
```

Three services:
1. **React frontend** -- single-page app with map + search + valuation display
2. **FastAPI backend** -- REST API handling geocoding, spatial queries, and CRUD
3. **PostgreSQL + PostGIS** -- stores OMI zones (polygons), quotations (price data), and manually entered transactions

## Tech Stack Rationale

| Choice | Why |
|--------|-----|
| **FastAPI** | Async, automatic OpenAPI docs, Pydantic validation, excellent for REST APIs |
| **PostGIS** (not plain Postgres) | OMI zones are polygons; need `ST_Intersects` and `ST_DWithin` for spatial point-in-polygon queries. Plain Postgres cannot do this |
| **React-Leaflet** (not Mapbox) | Free, no API key required, OpenStreetMap tiles, good enough for zone overlay display |
| **SQLAlchemy + GeoAlchemy2** | Industry-standard ORM with PostGIS geometry type support |
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
    CONSTRAINT fk_zone FOREIGN KEY (link_zona, semester)
        REFERENCES omi.zones(link_zona, semester)
);
```

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

## Request Flow: Address Valuation

```
User enters address
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

## Directory Structure

```
vendocasa/
+-- README.md
+-- docs/                          # Project documentation
+-- data/                          # OMI zip files (not in git)
+-- backend/
|   +-- app/
|   |   +-- main.py                # FastAPI app
|   |   +-- config.py              # Settings
|   |   +-- database.py            # SQLAlchemy engine
|   |   +-- models/                # ORM models
|   |   +-- schemas/               # Pydantic schemas
|   |   +-- api/                   # Route handlers
|   |   +-- services/              # Business logic
|   +-- scripts/                   # Import scripts
|   +-- alembic/                   # DB migrations
|   +-- Dockerfile
|   +-- pyproject.toml
+-- frontend/
|   +-- src/
|   |   +-- components/            # React components
|   |   +-- hooks/                 # Custom hooks
|   |   +-- api/                   # API client
|   |   +-- types/                 # TypeScript types
|   +-- package.json
+-- docker-compose.yml             # Local dev (PostGIS)
```
