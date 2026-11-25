"""Unified OMI data importer.

Scans a directory of zip files from the Agenzia delle Entrate,
extracts CSVs and KMLs, and imports everything into the PostGIS database.

Usage (from backend/):
    # Reads DATABASE_URL and DATA_DIR from .env
    python -m scripts.import_omi

    # Empty the OMI zone and quotation data (and their completion records)
    # before importing; transactions and application data are never touched
    python -m scripts.import_omi --reset

    # Override via CLI args
    python -m scripts.import_omi [data_dir] [database_url]

Each zip contains:
    - 2 CSVs: QI_[YYYY][S]_VALORI.csv (quotations) + QI_[YYYY][S]_ZONE.csv (zone descriptions)
    - ~7,900 KML files (one per municipality, named by Belfiore code)

Each semester is imported in ONE transaction: its existing zones and
quotations are replaced, and its completion record (omi.semester_import) is
written, or nothing changes. A semester is complete only when every step
succeeds and no zone row is rejected; readers select complete semesters only.
A failed semester therefore leaves the previous data current.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

from sqlalchemy import create_engine, text

from scripts.import_omi_quotations import (
    copy_quotations,
    import_zone_descriptions,
    parse_semester_from_filename,
    prepare_quotations,
)
from scripts.import_omi_zones import collect_zone_rows, insert_zone_rows

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[1]


class SemesterImportFailed(Exception):
    """The semester was rolled back; `rejected` lists rejected zone rows, if any."""

    def __init__(self, semester: str, reason: str, rejected: list[dict] | None = None) -> None:
        super().__init__(f"{semester}: {reason}")
        self.semester = semester
        self.reason = reason
        self.rejected = rejected or []


def _sync_url(db_url: str) -> str:
    from app.db_url import sync_database_url

    return sync_database_url(db_url)


def init_schema(db_url: str) -> None:
    """Bring the database schema up to date with the Alembic migrations."""
    from alembic import command
    from alembic.config import Config

    from app.config import settings

    original = settings.database_url
    settings.database_url = db_url
    try:
        command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")
    finally:
        settings.database_url = original
    logger.info("Database schema is at the latest migration")


def reset_schema(db_url: str) -> None:
    """Empty OMI zones, quotations and their completion records, in one transaction.

    The schema, omi.transactions and everything in the app schema (accounts'
    spending, the disposable-domain list) are never dropped or emptied.
    """
    engine = create_engine(_sync_url(db_url))
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE omi.quotations, omi.zones, omi.semester_import"))
    engine.dispose()
    logger.info("Emptied omi.zones, omi.quotations and omi.semester_import")


def get_complete_semesters(db_url: str) -> set[str]:
    """Semesters whose import is recorded complete."""
    engine = create_engine(_sync_url(db_url))
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT semester FROM omi.semester_import WHERE status = 'complete'"))
            return {row[0] for row in rows}
    finally:
        engine.dispose()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def import_semester(engine, semester: str, zip_path: Path) -> dict:
    """Import one semester from its zip in a single transaction.

    Returns the counts written to the completion record. Raises
    SemesterImportFailed, after rolling everything back, when a step fails,
    a zone row is rejected, or the semester has no zones or no quotations.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info(f"Extracting {zip_path.name} to a temporary directory...")
        with ZipFile(zip_path, "r") as z:
            z.extractall(tmpdir)
        tmppath = Path(tmpdir)

        zone_csvs = [f for f in list(tmppath.glob("*ZONE*.csv")) + list(tmppath.glob("*zone*.csv"))
                     if "VALORI" not in f.name.upper()]
        valori_csvs = list(tmppath.glob("*VALORI*.csv")) + list(tmppath.glob("*valori*.csv"))
        if not zone_csvs:
            raise SemesterImportFailed(semester, "no ZONE CSV in the archive")
        if not valori_csvs:
            raise SemesterImportFailed(semester, "no VALORI CSV in the archive")
        if not list(tmppath.glob("*.kml")):
            raise SemesterImportFailed(semester, "no KML files in the archive")

        # Parse everything before opening the transaction.
        zone_lookup = import_zone_descriptions(str(zone_csvs[0]), semester)
        zone_rows, skipped = collect_zone_rows(tmpdir, semester, zone_lookup)
        quotations_text, quotations_count = prepare_quotations(str(valori_csvs[0]), semester)

    source = f"{zip_path.name} sha256={_file_sha256(zip_path)}"
    try:
        with engine.begin() as conn:
            # One importer per semester at a time.
            conn.execute(text("SELECT pg_advisory_xact_lock(hashtext(:s))"), {"s": f"omi-import:{semester}"})
            conn.execute(text("DELETE FROM omi.semester_import WHERE semester = :s"), {"s": semester})
            conn.execute(text("DELETE FROM omi.quotations WHERE semester = :s"), {"s": semester})
            conn.execute(text("DELETE FROM omi.zones WHERE semester = :s"), {"s": semester})

            inserted, rejected = insert_zone_rows(conn, zone_rows)
            if rejected:
                raise SemesterImportFailed(semester, f"{len(rejected)} zone rows rejected", rejected)
            if inserted == 0:
                raise SemesterImportFailed(semester, "no zone polygons imported")
            if quotations_count == 0:
                raise SemesterImportFailed(semester, "no quotation rows in the VALORI CSV")
            copy_quotations(conn, quotations_text)

            without_zone = conn.execute(
                text("SELECT count(*) FROM omi.quotations q WHERE q.semester = :s AND NOT EXISTS "
                     "(SELECT 1 FROM omi.zones z WHERE z.link_zona = q.link_zona AND z.semester = q.semester)"),
                {"s": semester},
            ).scalar()
            counts = {"zones_count": inserted, "quotations_count": quotations_count,
                      "quotations_without_zone": without_zone, "placemarks_skipped": skipped}
            conn.execute(
                text("INSERT INTO omi.semester_import (semester, status, zones_count, quotations_count, "
                     "quotations_without_zone, source) VALUES (:s, 'complete', :z, :q, :w, :src)"),
                {"s": semester, "z": inserted, "q": quotations_count, "w": without_zone, "src": source},
            )
    except SemesterImportFailed:
        raise
    except Exception as exc:
        raise SemesterImportFailed(semester, f"{type(exc).__name__}: {str(exc).splitlines()[0][:300]}") from exc
    return counts


def discover_and_import_all(data_dir: str, db_url: str) -> int:
    """Scan data_dir for OMI zip files and import every semester not yet complete.

    Returns the number of semesters that failed (each one rolled back).
    """
    data_path = Path(data_dir)
    zip_files = sorted(data_path.glob("*.zip"))
    logger.info(f"Found {len(zip_files)} zip files in {data_dir}")

    if not zip_files:
        logger.error(f"No zip files found in {data_dir}")
        return 1

    init_schema(db_url)
    complete = get_complete_semesters(db_url)
    if complete:
        logger.info(f"Semesters already complete: {sorted(complete)}")

    # Group zips by semester (detected from the CSV filenames inside)
    semester_zips: dict[str, list[Path]] = {}
    for zf in zip_files:
        with ZipFile(zf, "r") as z:
            for name in z.namelist():
                sem = parse_semester_from_filename(name)
                if sem:
                    semester_zips.setdefault(sem, []).append(zf)
                    break
            else:
                logger.warning(f"Could not determine semester for {zf.name} -- skipping")

    logger.info(f"Detected semesters: {sorted(semester_zips.keys())}")
    engine = create_engine(_sync_url(db_url))
    failures = 0
    try:
        for semester in sorted(semester_zips):
            if semester in complete:
                logger.info(f"Semester {semester} already complete -- skipping")
                continue
            zips = semester_zips[semester]
            hashes = {_file_sha256(z) for z in zips}
            if len(hashes) > 1:
                logger.error(f"Semester {semester} is in {len(zips)} different archives "
                             f"({', '.join(z.name for z in zips)}); not importing it")
                failures += 1
                continue
            logger.info(f"{'=' * 60}\nIMPORTING SEMESTER {semester} from {zips[0].name}\n{'=' * 60}")
            try:
                counts = import_semester(engine, semester, zips[0])
            except SemesterImportFailed as failed:
                failures += 1
                logger.error(f"Semester {semester} rolled back, previous data unchanged: {failed.reason}")
                for row in failed.rejected:
                    logger.error(f"  rejected zone {row['link_zona']} in {row['file']}: {row['error']}")
                continue
            logger.info(f"Semester {semester} complete: {counts}")

        with engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT")
            conn.execute(text("VACUUM ANALYZE omi.zones"))
            conn.execute(text("VACUUM ANALYZE omi.quotations"))
    finally:
        engine.dispose()

    logger.info(f"Import finished with {failures} failed semesters")
    return failures


def main() -> int:
    from app.config import settings

    parser = argparse.ArgumentParser(description="Import OMI data into PostGIS")
    parser.add_argument("data_dir", nargs="?", default=settings.data_dir, help="Directory containing OMI zip files")
    parser.add_argument("database_url", nargs="?", default=settings.database_url, help="PostgreSQL connection string")
    parser.add_argument("--reset", action="store_true",
                        help="Empty OMI zones, quotations and completion records before importing")
    args = parser.parse_args()

    if args.reset:
        init_schema(args.database_url)
        reset_schema(args.database_url)

    return 1 if discover_and_import_all(args.data_dir, args.database_url) else 0


if __name__ == "__main__":
    sys.exit(main())
