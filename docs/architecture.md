# System Architecture

## High-Level Topology

```
+-------------------+     +------------------------+     +------------------+
|  React Frontend   |---->|  FastAPI Backend        |---->|  PostgreSQL +    |
|  (Vite + Tailwind)|     |  (Python 3.12+)        |     |  PostGIS         |
|  on Vercel        |     |  on Railway             |     |  on Supabase     |
+---------+---------+     +-------+----------------+     +------------------+
          |                        |
          v                        v
+-------------------+     +----------------+
|  Supabase Auth    |     |  Anthropic API |
|  (sign-in links)  |     |  (Claude       |
+-------------------+     |   Sonnet 5.5)  |
                          +----------------+
```

Five services:
1. **React frontend** (Vercel): a dark-themed landing page, and a chat overlay opened after signing in.
2. **Supabase Auth**: registration and sign-in through emailed links. The frontend sends the session's access token to the backend.
3. **FastAPI backend** (Railway): it verifies the token on every API request, and runs the REST API, geocoding, spatial queries, the AI agent and the spending ledger.
4. **PostgreSQL + PostGIS** (Supabase): OMI zones, quotations and transactions in schema `omi`, and application state in schema `app`. Clients have no privileges on either schema.
5. **Anthropic Claude**: the conversational agent, with server-side tool calls.

## Tech Stack Rationale

| Choice | Why |
|--------|-----|
| **FastAPI** | Async, automatic OpenAPI docs, Pydantic validation, SSE streaming support |
| **PostGIS** (not plain Postgres) | OMI zones are polygons; need `ST_Intersects` and `ST_DWithin` for spatial point-in-polygon queries. Plain Postgres cannot do this |
| **Supabase** (not Railway Postgres) | Managed PostgreSQL with PostGIS enabled by default, free tier, connection pooling via Supavisor |
| **Tailwind CSS v4** | Utility-first CSS with `@tailwindcss/vite` plugin, `@theme` directive for dark palette, zero custom CSS files |
| **React-Leaflet** (not Mapbox) | Free, no API key required, OpenStreetMap tiles. Currently unused in the UI but available for future map features |
| **SQLAlchemy + GeoAlchemy2** | Industry-standard async ORM with PostGIS geometry type support |
| **Anthropic Claude Sonnet 5.5** | Tool calling for the conversational valuation flow, SSE streaming, prompt caching |
| **Supabase Auth** | Managed email sign-in links in the project that already hosts the database; no passwords stored by VendoCasa |
| **Photon** (primary geocoder), **Nominatim** | Free, no API key |
| **Google Geocoding** (optional last fallback) | Paid per request, charged to the requesting account |

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

**omi.semester_import**: one row per semester whose import is complete (migration 0005). Readers select only these semesters; see [the data pipeline](data-pipeline.md).

### Schema: `app`

Application state, never exposed to clients:
- `app.spend_month`: spent and reserved micro-dollars per scope and calendar month. A scope is an account ID, `global`, or `external` for spend recorded by `scripts/record_external_spend.py`.
- `app.spend_reservation`: one row per paid call, open or settled.
- `app.service_flag`: holds `paid_calls_enabled`.
- `app.disposable_email_domains`: the refused registration domains.
- `app.alembic_version`: the migration state.

The schema is managed by Alembic (`backend/migrations/`); migration 0001 is the baseline of the OMI schema.

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

The frontend presents a conversational chat interface inside a centered overlay panel (desktop) or fullscreen sheet (mobile). The panel stays mounted to keep the conversation. While closed it is `inert`, so neither the keyboard nor assistive technology reaches its controls. When it opens, focus moves inside and Tab and Shift+Tab stay there. Escape closes it and returns focus to the control that opened it. The backend orchestrates an AI agent that gathers property details through natural conversation and calls valuation tools programmatically.

### Agent Architecture

```
User message
     |
     v
POST /api/chat (SSE stream)
     |
     v
Claude Sonnet 5.5 (system prompt + 4 tools; arguments validated before each tool runs)
     |
     +---> tool_use: valuate_property -----> valuation service ---> DB
     +---> tool_use: enhanced_valuate_property -> coefficient service --> DB
     +---> tool_use: get_coefficient_info -> coefficient options
     +---> tool_use: get_zone_quotations --> quotation service ---> DB
     |
     v
SSE events streamed to frontend:
  - text_delta: token-by-token text
  - tool_result: structured valuation data (rendered as inline cards)
  - error: an Italian refusal or failure message
  - done: stream complete
```

### Tool Definitions

| Tool | Backend Service | Purpose |
|------|----------------|---------|
| `valuate_property` | `valuate_address()` | Geocode + zone lookup + basic OMI estimate |
| `enhanced_valuate_property` | `enhanced_valuate_address()` | Apply correction coefficients for adjusted estimate |
| `get_coefficient_info` | `get_coefficient_options()` | List available coefficient factors and options |
| `get_zone_quotations` | `get_quotations()` | Deep dive on zone price data |

The agent loop runs up to `AGENT_MAX_TOOL_ROUNDS` (default 3) model rounds per request. Before each round the backend counts the input tokens and reserves the call's maximum cost against the account's and the service's monthly caps (`backend/app/services/spending.py`); afterwards the actual cost from the usage report settles it. The fixed system prompt and tools carry a prompt-cache breakpoint. Tool arguments are validated (`backend/app/services/tool_inputs.py`); an invalid call or a failing tool becomes a tool error, not a broken stream. Tool execution is server-side; the frontend receives streamed text and structured results.

### System Prompt

The agent operates as an Italian-speaking real estate consultant:
1. Asks for address and surface area
2. Calls `valuate_property` for initial OMI lookup
3. Gathers property details conversationally (2-3 questions at a time, not all at once)
4. Calls `enhanced_valuate_property` with collected details
5. Explains the importance of realistic pricing (avoid both underpricing and overpricing)
6. Highlights the value of a good agent and provides practical advice (get 3 valuations, set realistic goals, verify track record)

## Request Flow: Address Valuation

### Via REST API (direct)

```
GET /api/valuate?address=...&surface_m2=...
         |
         v
[1] Geocode address --> lat/lng, precision (exact or approximate)
    - Try Photon, then Nominatim
    - Last fallback: Google Geocoding, if configured (charged to the account)
         |
         v
[2] Spatial lookup: ST_Intersects(zone.geom, point)
    - Find which OMI zone polygon contains the point
    - If no exact match, fallback to ST_DWithin(200m)
         |
         v
[3] Fetch quotations for zone + latest complete semester
    - JOIN omi.quotations ON link_zona + semester
    - Filter by property_type_code
    - Sort by is_prevalent DESC
         |
         v
[4] Fetch comparable transactions
    - SELECT from omi.transactions WHERE link_zona matches exactly
         |
         v
[5] Compute estimate (Decimal arithmetic, rounded to cents)
    - Midpoint of prevalent price_min/price_max * surface_m2
    - No usable range: explicit no_data instead of an estimate
    - Return range (min, mid, max), location precision and comparables
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
Streams text explanation + inline valuation cards
```

## Directory Structure

```
vendocasa/
+-- README.md
+-- docs/                          # Project documentation
+-- backend/
|   +-- app/
|   |   +-- main.py                # FastAPI app, middleware, periodic sweeps
|   |   +-- auth.py                # Token verification, owner check
|   |   +-- middleware.py          # Request body limits
|   |   +-- refusals.py            # Refusal codes and Italian messages
|   |   +-- config.py              # Settings (pydantic-settings, reads .env)
|   |   +-- database.py            # Async SQLAlchemy engine
|   |   +-- db_url.py              # Database URL forms, sync and async drivers
|   |   +-- schemas/               # Pydantic request/response schemas
|   |   |   +-- enhanced_valuation.py
|   |   |   +-- transaction.py
|   |   +-- api/                   # Route handlers
|   |   |   +-- router.py          # Account requirement and quotas for every route
|   |   |   +-- chat.py            # POST /api/chat (SSE streaming)
|   |   |   +-- documents.py       # POST /api/documents/upload
|   |   |   +-- valuations.py      # Valuation endpoints
|   |   |   +-- zones.py           # Zone GeoJSON endpoints
|   |   |   +-- semesters.py       # Available semesters
|   |   |   +-- transactions.py    # Transaction CRUD (writes: owner only)
|   |   |   +-- admin.py           # Owner: spending, paid-call switch
|   |   |   +-- quotas.py          # Per-account request quotas
|   |   +-- services/              # Business logic
|   |       +-- agent.py           # AI agent (Claude, tools, SSE loop)
|   |       +-- valuation.py       # Geocoding + zone lookup + estimate
|   |       +-- coefficients.py    # Correction coefficient system
|   |       +-- zone_lookup.py     # PostGIS spatial queries
|   |       +-- geocoder.py        # Photon, then Nominatim, then optional Google geocoding
|   |       +-- document_store.py  # Owned in-memory uploads with byte caps
|   |       +-- rate_limit.py      # In-memory request limits per account and per IP
|   |       +-- disposable_domains.py # Cached list of refused email domains
|   |       +-- spending.py        # Monthly caps: reservations and settlement
|   |       +-- pricing.py         # Provider prices, call costs
|   |       +-- numbers.py         # Decimal money helpers
|   |       +-- tool_inputs.py     # Agent tool argument validation
|   +-- scripts/                   # Import and maintenance scripts
|   |   +-- import_omi.py          # Unified entry point
|   |   +-- import_omi_zones.py    # KML -> PostGIS importer
|   |   +-- import_omi_quotations.py # CSV -> COPY importer
|   |   +-- validate_semesters.py  # Read-only validation of loaded semesters
|   |   +-- refresh_disposable_domains.py # Refresh the refused-domain list
|   |   +-- record_external_spend.py # Record provider spend made outside the app
|   +-- data/                      # OMI zip files (DATA_DIR, not in git) and disposable_domains.txt
|   +-- migrations/                # Alembic migrations (schema source of truth)
|   +-- tests/                     # pytest: unit, integration/ (PostGIS), local_stack/ (Supabase),
|   |                              # e2e/ (backend for the browser journeys)
|   +-- sql/
|   |   +-- client_roles.sql       # Supabase client roles, for plain PostgreSQL
|   +-- .env.example               # Template (placeholder values)
|   +-- Dockerfile                 # Production container (GDAL + Python)
|   +-- pyproject.toml
|   +-- requirements.lock          # Hashed dependency lock (+ requirements-dev.lock)
+-- frontend/
|   +-- src/
|   |   +-- index.css              # Tailwind @import + @theme (dark palette)
|   |   +-- main.tsx               # Entry point (imports index.css)
|   |   +-- App.tsx                # Router + drawer state orchestrator
|   |   +-- components/
|   |   |   +-- ui/                # Design system primitives
|   |   |   |   +-- Button.tsx     # Primary/secondary/ghost/danger variants
|   |   |   |   +-- Logo.tsx       # VendoCasa wordmark SVG
|   |   |   |   +-- Badge.tsx
|   |   |   |   +-- Card.tsx
|   |   |   +-- Landing/           # Dark landing page sections
|   |   |   |   +-- LandingPage.tsx
|   |   |   |   +-- HeroSection.tsx
|   |   |   |   +-- HowItWorks.tsx
|   |   |   |   +-- FreakonomicsSection.tsx
|   |   |   |   +-- TrustSection.tsx
|   |   |   |   +-- CtaSection.tsx
|   |   |   |   +-- Footer.tsx
|   |   |   +-- AppDrawer/         # Centered overlay (desktop) / fullscreen (mobile)
|   |   |   |   +-- AppDrawer.tsx  # Modal panel with CSS animations
|   |   |   |   +-- DrawerHeader.tsx
|   |   |   +-- Auth/
|   |   |   |   +-- SignInPanel.tsx # Email sign-in link request
|   |   |   +-- Chat/              # AI chat interface
|   |   |   |   +-- ChatPanel.tsx  # Main chat UI (messages, input, uploads, reset at the limit)
|   |   |   |   +-- chatLogic.ts   # History limit, re-upload, card notices
|   |   |   |   +-- ChatMessage.tsx # Message bubbles (dark theme)
|   |   |   |   +-- InlineToolResult.tsx # Valuation cards in chat
|   |   |   +-- CookieBanner.tsx   # GDPR consent (gates drawer opening)
|   |   +-- api/client.ts          # API client (bearer token, axios + SSE streaming)
|   |   +-- api/sse.ts             # Chunk-boundary-safe SSE parser
|   |   +-- api/refusals.ts        # Refusal bodies to Italian messages
|   |   +-- auth/                  # Supabase client, sign-in error messages
|   |   +-- hooks/useSession.ts    # Session state, sign-out
|   |   +-- types/index.ts         # TypeScript types
|   |   +-- pages/                 # Privacy policy, terms of service
|   +-- e2e/                       # Playwright browser journeys on the local stack
|   +-- package.json
+-- railway.toml                   # Railway deployment config
+-- vercel.json                    # Vercel deployment config
+-- docker-compose.yml             # Local dev (PostGIS container)
+-- supabase/config.toml           # Local Supabase stack (auth rules, hook, local SMTP)
+-- supabase/seed.sql              # Creates the app and omi schemas for the local Data API
+-- .github/workflows/ci.yml       # Backend tests with PostGIS, frontend tests and build
```