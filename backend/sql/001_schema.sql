-- OMI Real Estate Valuation Tool - Database Schema
-- Requires PostgreSQL with PostGIS extension

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS omi;

-- OMI zone polygons (one row per zone per semester)
CREATE TABLE omi.zones (
    id                  SERIAL PRIMARY KEY,
    link_zona           VARCHAR(12) NOT NULL,   -- e.g. "AG00000027" — JOIN KEY
    zone_code           VARCHAR(10) NOT NULL,   -- e.g. "B01"
    fascia              VARCHAR(5),             -- B=Centrale, C=Semicentrale, D=Periferica, E=Suburbana, R=Rurale
    municipality_istat  VARCHAR(10) NOT NULL,   -- ISTAT code
    municipality_name   TEXT,
    province_code       VARCHAR(3),             -- e.g. "MI"
    zone_description    TEXT,                   -- street-level description of zone boundaries
    semester            VARCHAR(7) NOT NULL,    -- e.g. "2025_S1"
    geom                GEOMETRY(MultiPolygon, 4326) NOT NULL,
    UNIQUE(link_zona, semester)
);
CREATE INDEX idx_zones_geom ON omi.zones USING GIST (geom);
CREATE INDEX idx_zones_link ON omi.zones (link_zona);
CREATE INDEX idx_zones_semester ON omi.zones (semester);

-- OMI quotations (multiple rows per zone: one per property type × conservation state × semester)
CREATE TABLE omi.quotations (
    id                  SERIAL PRIMARY KEY,
    link_zona           VARCHAR(12) NOT NULL,
    semester            VARCHAR(7) NOT NULL,
    property_type_code  INTEGER,                -- 20=Abitazioni civili, 21=Economico, 1=Ville, 2=Signorili, 13=Box, 11=Negozi, 6=Uffici
    property_type_desc  VARCHAR(60),
    conservation_state  VARCHAR(30),            -- OTTIMO / NORMALE / SCADENTE
    is_prevalent        BOOLEAN DEFAULT FALSE,  -- TRUE if this is the most common state in the zone
    price_min           NUMERIC(10,2),          -- EUR/m2 purchase min
    price_max           NUMERIC(10,2),          -- EUR/m2 purchase max
    surface_type_sale   CHAR(1),                -- L=Lorda (gross), N=Netta (net)
    rent_min            NUMERIC(10,2),          -- EUR/m2/month rent min
    rent_max            NUMERIC(10,2),          -- EUR/m2/month rent max
    surface_type_rent   CHAR(1),
    UNIQUE(link_zona, semester, property_type_code, conservation_state)
);
CREATE INDEX idx_quot_lookup ON omi.quotations (link_zona, semester);
CREATE INDEX idx_quot_type ON omi.quotations (property_type_code);

-- Manually entered transaction data (from the Agenzia's "Consultazione Valori Immobiliari Dichiarati")
CREATE TABLE omi.transactions (
    id                  SERIAL PRIMARY KEY,
    transaction_date    DATE,                   -- month/year of the deed
    transaction_type    VARCHAR(30),            -- Residenziale, Commerciale, Produttivo, etc.
    declared_price      NUMERIC(12,2),          -- total corrispettivo dichiarato (EUR)
    municipality        TEXT,
    omi_zone            VARCHAR(10),            -- OMI zone code (e.g. "B01")
    link_zona           VARCHAR(12),            -- if identifiable
    cadastral_category  VARCHAR(10),            -- e.g. A/2, A/3, C/6
    cadastral_vani      NUMERIC(6,1),           -- "consistenza" in vani (for cat. A)
    cadastral_mq        NUMERIC(8,1),           -- "consistenza" in m2 (for cat. C)
    cadastral_mc        NUMERIC(8,1),           -- "consistenza" in m3 (for cat. B)
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Geocoding cache
CREATE TABLE omi.geocode_cache (
    address             TEXT PRIMARY KEY,
    lat                 DOUBLE PRECISION,
    lng                 DOUBLE PRECISION,
    source              VARCHAR(30),            -- "nominatim" or "google"
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
