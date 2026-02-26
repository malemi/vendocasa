"""Unified OMI data importer.

Scans a directory of zip files from the Agenzia delle Entrate,
extracts CSVs and KMLs, and imports everything into the PostGIS database.

Usage (from backend/):
    # Reads DATABASE_URL and DATA_DIR from .env
    python -m scripts.import_omi

    # Reset database (drop and recreate all OMI tables)
    python -m scripts.import_omi --reset

    # Override via CLI args
    python -m scripts.import_omi [data_dir] [database_url]

Each zip contains:
    - 2 CSVs: QI_[YYYY][S]_VALORI.csv (quotations) + QI_[YYYY][S]_ZONE.csv (zone descriptions)
    - ~7,900 KML files (one per municipality, named by Belfiore code)
"""

import argparse
import logging
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

from sqlalchemy import create_engine, text

from scripts.import_omi_quotations import (
    import_quotations,
    import_zone_descriptions,
    parse_semester_from_filename,
)
from scripts.import_omi_zones import import_kml_zones_batch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def init_schema(db_url: str):
    """Create the OMI schema and tables if they don't exist."""
    schema_sql = (Path(__file__).parent.parent / "sql" / "001_schema.sql").read_text()
    # Strip SQL comments (lines starting with --) to avoid splitting issues
    lines = []
    for line in schema_sql.splitlines():
        # Remove inline comments but keep the rest of the line
        comment_pos = line.find("--")
        if comment_pos >= 0:
            line = line[:comment_pos]
        lines.append(line)
    cleaned_sql = "\n".join(lines)

    engine = create_engine(db_url)
    with engine.begin() as conn:
        for statement in cleaned_sql.split(";"):
            stmt = statement.strip()
            if not stmt:
                continue
            try:
                conn.execute(text(stmt))
            except Exception as e:
                err_msg = str(e).lower()
                if "already exists" in err_msg or "duplicate" in err_msg:
                    pass
                else:
                    raise
    logger.info("Database schema initialized")


def reset_schema(db_url: str):
    """Drop all OMI tables and recreate them from scratch."""
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS omi.quotations CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS omi.zones CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS omi.transactions CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS omi.geocode_cache CASCADE"))
        conn.execute(text("DROP SCHEMA IF EXISTS omi CASCADE"))
    logger.info("Dropped all OMI tables and schema")
    init_schema(db_url)


def get_existing_semesters(db_url: str) -> set[str]:
    """Return the set of semesters already imported into omi.zones."""
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT DISTINCT semester FROM omi.zones"))
            return {row[0] for row in result}
    except Exception:
        return set()


def discover_and_import_all(data_dir: str, db_url: str):
    """Scan data_dir for all OMI zip files, extract, and import everything.

    This is the main entry point.
    """
    data_path = Path(data_dir)
    zip_files = sorted(data_path.glob("*.zip"))
    logger.info(f"Found {len(zip_files)} zip files in {data_dir}")

    if not zip_files:
        logger.error(f"No zip files found in {data_dir}")
        sys.exit(1)

    # Initialize schema
    init_schema(db_url)

    # Check what's already imported
    existing = get_existing_semesters(db_url)
    if existing:
        logger.info(f"Already imported semesters: {sorted(existing)}")

    # Group zips by semester (detect from CSV filenames inside)
    semester_zips: dict[str, list[Path]] = {}

    for zf in zip_files:
        with ZipFile(zf, "r") as z:
            names = z.namelist()
            # Find a VALORI or ZONE CSV to determine semester
            for name in names:
                sem = parse_semester_from_filename(name)
                if sem:
                    semester_zips.setdefault(sem, []).append(zf)
                    break
            else:
                logger.warning(f"Could not determine semester for {zf.name} -- skipping")

    logger.info(f"Detected semesters: {sorted(semester_zips.keys())}")

    # Import each semester
    for semester in sorted(semester_zips.keys()):
        if semester in existing:
            logger.info(f"Semester {semester} already imported -- skipping")
            continue

        zips = semester_zips[semester]
        # Use the first zip that contains this semester (duplicates have same data)
        zip_path = zips[0]
        if len(zips) > 1:
            logger.info(
                f"Semester {semester} found in {len(zips)} zips, using {zip_path.name}"
            )

        logger.info(f"\n{'='*60}")
        logger.info(f"IMPORTING SEMESTER {semester} from {zip_path.name}")
        logger.info(f"{'='*60}")

        with tempfile.TemporaryDirectory() as tmpdir:
            logger.info(f"Extracting {zip_path.name} to temp directory...")
            with ZipFile(zip_path, "r") as z:
                z.extractall(tmpdir)

            tmppath = Path(tmpdir)

            # 1. Find and parse ZONE CSV (needed for KML lookup)
            zone_csvs = list(tmppath.glob("*ZONE*.csv")) + list(tmppath.glob("*zone*.csv"))
            # Exclude VALORI files
            zone_csvs = [f for f in zone_csvs if "VALORI" not in f.name.upper()]

            zone_lookup = {}
            if zone_csvs:
                zone_csv = zone_csvs[0]
                logger.info(f"Parsing zone descriptions from {zone_csv.name}")
                zone_lookup = import_zone_descriptions(str(zone_csv), semester, db_url)
            else:
                logger.warning(f"No ZONE CSV found for {semester}")

            # 2. Import KML polygons (zones must exist before quotations due to FK)
            kml_files = list(tmppath.glob("*.kml"))
            if kml_files:
                logger.info(f"Importing {len(kml_files)} KML zone perimeters...")
                import_kml_zones_batch(tmpdir, semester, zone_lookup, db_url)
            else:
                logger.warning(f"No KML files found for {semester}")

            # 3. Import quotation CSV
            valori_csvs = list(tmppath.glob("*VALORI*.csv")) + list(
                tmppath.glob("*valori*.csv")
            )
            if valori_csvs:
                valori_csv = valori_csvs[0]
                logger.info(f"Importing quotations from {valori_csv.name}")
                import_quotations(str(valori_csv), semester, db_url)
            else:
                logger.warning(f"No VALORI CSV found for {semester}")

    # Post-import maintenance
    logger.info("\nRunning VACUUM ANALYZE...")
    engine = create_engine(db_url)
    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.execute(text("VACUUM ANALYZE omi.zones"))
        conn.execute(text("VACUUM ANALYZE omi.quotations"))

    logger.info("\nImport complete!")


def main():
    from app.config import settings

    parser = argparse.ArgumentParser(description="Import OMI data into PostGIS")
    parser.add_argument("data_dir", nargs="?", default=settings.data_dir, help="Directory containing OMI zip files")
    parser.add_argument("database_url", nargs="?", default=settings.database_url, help="PostgreSQL connection string")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all OMI tables before importing")
    args = parser.parse_args()

    if args.reset:
        logger.info("Resetting database (dropping all OMI tables)...")
        reset_schema(args.database_url)

    discover_and_import_all(args.data_dir, args.database_url)


if __name__ == "__main__":
    main()
