"""Completion records for OMI semesters, and their backfill.

A semester is selectable only when `omi.semester_import` records it complete.
New imports write the record in the same transaction that replaces the
semester's zones and quotations (scripts/import_omi.py).

Semesters loaded before this migration have no record. The backfill validates
each one: it passes when it has zones and quotations and every zone geometry
is valid. Quotations whose zone has no polygon are legitimate (some OMI zones
have no perimeter) and are counted, not failed. Each semester's result is
printed; a failing semester gets no record and stays unselectable.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

# Frozen copy of the validation in scripts/validate_semesters.py.
VALIDATION_SQL = """
    WITH semesters AS (
        SELECT semester FROM omi.zones
        UNION
        SELECT semester FROM omi.quotations
    )
    SELECT s.semester,
           (SELECT count(*) FROM omi.zones z WHERE z.semester = s.semester) AS zones,
           (SELECT count(*) FROM omi.zones z WHERE z.semester = s.semester
                AND NOT ST_IsValid(z.geom)) AS invalid_geometries,
           (SELECT count(*) FROM omi.quotations q WHERE q.semester = s.semester) AS quotations,
           (SELECT count(*) FROM omi.quotations q WHERE q.semester = s.semester
                AND NOT EXISTS (SELECT 1 FROM omi.zones z
                                WHERE z.link_zona = q.link_zona AND z.semester = q.semester))
               AS quotations_without_zone
    FROM semesters s
    ORDER BY s.semester
"""


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE omi.semester_import (
            semester                 VARCHAR(7)  PRIMARY KEY,
            status                   TEXT        NOT NULL CHECK (status IN ('complete')),
            zones_count              INTEGER     NOT NULL CHECK (zones_count > 0),
            quotations_count         INTEGER     NOT NULL CHECK (quotations_count > 0),
            quotations_without_zone  INTEGER     NOT NULL,
            source                   TEXT        NOT NULL,  -- archive and SHA-256, or 'backfill'
            completed_at             TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("REVOKE ALL ON omi.semester_import FROM PUBLIC, anon, authenticated")

    rows = op.get_bind().execute(sa.text(VALIDATION_SQL)).all()
    print("Backfill note: quotations_without_zone counts zones without a perimeter and zone rows the "
          "old importer lost after an insert error alike; a re-import from the archive tells them apart.")
    for semester, zones, invalid, quotations, without_zone in rows:
        passes = zones > 0 and quotations > 0 and invalid == 0
        print(
            f"semester {semester}: zones={zones} invalid_geometries={invalid} "
            f"quotations={quotations} quotations_without_zone={without_zone} -> "
            f"{'complete' if passes else 'NOT COMPLETE (stays unselectable)'}"
        )
        if passes:
            op.get_bind().execute(
                sa.text(
                    "INSERT INTO omi.semester_import (semester, status, zones_count, quotations_count, "
                    "quotations_without_zone, source) VALUES (:s, 'complete', :z, :q, :w, 'backfill')"
                ),
                {"s": semester, "z": zones, "q": quotations, "w": without_zone},
            )


def downgrade() -> None:
    # Only the records go; the zones and quotations they describe stay.
    op.execute("DROP TABLE IF EXISTS omi.semester_import")
