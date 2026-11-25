"""Baseline: the OMI schema as the importer created it before migrations existed.

Every statement is idempotent, so this migration is a no-op on a database
that the importer already initialized (production) and creates the same
objects on an empty database.

Revision ID: 0001
Revises:
Create Date: 2026-11-25
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE SCHEMA IF NOT EXISTS omi")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS omi.zones (
            id                  SERIAL PRIMARY KEY,
            link_zona           VARCHAR(12) NOT NULL,
            zone_code           VARCHAR(10) NOT NULL,
            fascia              VARCHAR(5),
            municipality_istat  VARCHAR(10) NOT NULL,
            municipality_name   TEXT,
            province_code       VARCHAR(3),
            zone_description    TEXT,
            semester            VARCHAR(7) NOT NULL,
            geom                GEOMETRY(MultiPolygon, 4326) NOT NULL,
            UNIQUE (link_zona, semester)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_zones_geom ON omi.zones USING GIST (geom)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_zones_link ON omi.zones (link_zona)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_zones_semester ON omi.zones (semester)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS omi.quotations (
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
            UNIQUE (link_zona, semester, property_type_code, conservation_state)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_quot_lookup ON omi.quotations (link_zona, semester)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_quot_type ON omi.quotations (property_type_code)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS omi.transactions (
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
        )
        """
    )


def downgrade() -> None:
    # The baseline describes data that predates migrations, including the
    # manually entered transaction records. It is never dropped automatically.
    raise RuntimeError("The baseline migration cannot be downgraded.")
