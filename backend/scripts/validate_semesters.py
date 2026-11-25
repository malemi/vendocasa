"""Validate the OMI semesters loaded in a database, read-only.

For each semester present in omi.zones or omi.quotations, reports the zone
count, invalid geometries, quotation count and quotations whose zone has no
polygon, and whether it passes. A semester passes when it has zones and
quotations and every geometry is valid; quotations without a polygon are
legitimate (some OMI zones have no perimeter) and are only counted. When
omi.semester_import exists, the report also says which semesters are recorded
complete. Nothing is written.

Usage (from backend/, with DATABASE_URL set or in .env):
    python -m scripts.validate_semesters
Exit status: 0 if the latest loaded semester passes, 1 otherwise.
"""

from __future__ import annotations

import sys

from sqlalchemy import create_engine, text

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


def validate(database_url: str) -> list[dict]:
    from app.db_url import sync_database_url

    engine = create_engine(sync_database_url(database_url))
    try:
        with engine.connect() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            rows = conn.execute(text(VALIDATION_SQL)).all()
            recorded = set()
            has_records = conn.execute(text("SELECT to_regclass('omi.semester_import')")).scalar()
            if has_records:
                recorded = {r[0] for r in conn.execute(
                    text("SELECT semester FROM omi.semester_import WHERE status = 'complete'"))}
    finally:
        engine.dispose()
    return [
        {"semester": s, "zones": z, "invalid_geometries": i, "quotations": q,
         "quotations_without_zone": w, "passes": z > 0 and q > 0 and i == 0,
         "recorded_complete": s in recorded}
        for s, z, i, q, w in rows
    ]


def main() -> int:
    from app.config import settings

    report = validate(settings.database_url)
    if not report:
        print("No semesters loaded.")
        return 1
    for r in report:
        verdict = "passes" if r["passes"] else "FAILS"
        print(f"{r['semester']}: zones={r['zones']} invalid_geometries={r['invalid_geometries']} "
              f"quotations={r['quotations']} quotations_without_zone={r['quotations_without_zone']} "
              f"recorded_complete={r['recorded_complete']} -> {verdict}")
    print("Note: for semesters loaded by the old importer, quotations_without_zone counts both zones "
          "that truly have no perimeter and zone rows that the old importer lost after an insert "
          "error; the two cannot be told apart from the database. A re-import from the archive tells.")
    latest = report[-1]
    print(f"Latest loaded semester {latest['semester']} {'passes' if latest['passes'] else 'FAILS'}.")
    return 0 if latest["passes"] else 1


if __name__ == "__main__":
    sys.exit(main())
