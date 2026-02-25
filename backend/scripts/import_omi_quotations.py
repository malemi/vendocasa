"""Import OMI quotation CSVs (VALORI files) into PostgreSQL.

Reads semicolon-delimited CSVs with Italian decimal separators (comma),
maps columns to the omi.quotations table schema, and bulk-inserts.

The CSV has a descriptive title on line 1 and column headers on line 2.
"""

import logging
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


def parse_semester_from_filename(filename: str) -> str | None:
    """Extract semester from OMI CSV filename.

    Pattern: QI_[YYYY][S]_VALORI.csv or QI_[YYYY][S]_ZONE.csv
    where YYYY is 4-digit year and S is 1 or 2.
    Example: QI_20242_VALORI.csv -> "2024_S2"
    """
    match = re.search(r"(\d{4})([12])_(?:VALORI|ZONE)", filename, re.IGNORECASE)
    if match:
        return f"{match.group(1)}_S{match.group(2)}"
    return None


def import_quotations(csv_path: str, semester: str, db_url: str) -> int:
    """Import a single OMI quotation CSV into the database.

    Args:
        csv_path: Path to the semicolon-delimited CSV file.
        semester: Semester string, e.g. "2024_S2".
        db_url: PostgreSQL connection string.

    Returns:
        Number of rows imported.
    """
    logger.info(f"Reading {csv_path} for semester {semester}")

    # Read CSV: skip line 1 (descriptive title), use line 2 as headers
    df = pd.read_csv(
        csv_path,
        sep=";",
        encoding="utf-8",
        dtype=str,
        skiprows=1,  # skip the descriptive title line
        on_bad_lines="warn",
    )

    if df.empty:
        logger.warning(f"Empty CSV: {csv_path}")
        return 0

    # Strip whitespace from column names and all string values
    df.columns = df.columns.str.strip()
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].str.strip()

    # Drop the trailing empty column from the trailing semicolon
    if df.columns[-1] == "" or df.columns[-1].startswith("Unnamed"):
        df = df.iloc[:, :-1]

    # Numeric conversions: replace comma decimal separator with period
    numeric_cols = ["Compr_min", "Compr_max", "Loc_min", "Loc_max"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .str.replace(",", ".", regex=False)
                .apply(pd.to_numeric, errors="coerce")
            )

    # Property type code
    if "Cod_Tip" in df.columns:
        df["Cod_Tip"] = pd.to_numeric(df["Cod_Tip"], errors="coerce")

    # Prevalent state: "P" -> True, anything else -> False
    if "Stato_prev" in df.columns:
        df["is_prevalent"] = df["Stato_prev"].str.strip().str.upper() == "P"
    else:
        df["is_prevalent"] = False

    df["semester"] = semester

    # Validate LinkZona format: 2 uppercase letters + 8 digits
    if "LinkZona" in df.columns:
        valid_lz = df["LinkZona"].str.match(r"^[A-Z]{2}\d{8}$", na=False)
        invalid_count = (~valid_lz).sum()
        if invalid_count > 0:
            bad_samples = df.loc[~valid_lz, "LinkZona"].dropna().unique()[:5]
            logger.warning(
                f"{invalid_count} rows with invalid LinkZona in {csv_path}: {bad_samples}"
            )
            # Keep only valid rows
            df = df[valid_lz]

    # Rename columns to match database schema
    result = df.rename(
        columns={
            "Prov": "province_code",
            "Comune_ISTAT": "municipality_istat",
            "Comune_descrizione": "municipality_name",
            "Fascia": "fascia",
            "Zona": "zone_code",
            "LinkZona": "link_zona",
            "Cod_Tip": "property_type_code",
            "Descr_Tipologia": "property_type_desc",
            "Stato": "conservation_state",
            "Compr_min": "price_min",
            "Compr_max": "price_max",
            "Sup_NL_compr": "surface_type_sale",
            "Loc_min": "rent_min",
            "Loc_max": "rent_max",
            "Sup_NL_loc": "surface_type_rent",
        }
    )

    # Select only the columns we need for the quotations table
    db_cols = [
        "link_zona",
        "semester",
        "property_type_code",
        "property_type_desc",
        "conservation_state",
        "is_prevalent",
        "price_min",
        "price_max",
        "surface_type_sale",
        "rent_min",
        "rent_max",
        "surface_type_rent",
    ]

    output = result[db_cols].copy()

    engine = create_engine(db_url)

    # Use a chunked insert to handle large files
    chunk_size = 10000
    total = 0
    for i in range(0, len(output), chunk_size):
        chunk = output.iloc[i : i + chunk_size]
        try:
            chunk.to_sql(
                "quotations",
                engine,
                schema="omi",
                if_exists="append",
                index=False,
                method="multi",
            )
            total += len(chunk)
        except Exception as e:
            if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
                logger.info(f"Skipping duplicate chunk at row {i} for {semester}")
            else:
                raise

    logger.info(f"Imported {total} quotation rows for {semester}")
    return total


def import_zone_descriptions(csv_path: str, semester: str, db_url: str) -> dict:
    """Import ZONE CSV and return a lookup dict: (belfiore_code, zone_code) -> {link_zona, ...}.

    This is used by the KML importer to resolve LinkZona from CODCOM + CODZONA.

    Returns:
        Dict mapping (comune_amm, zona) -> row dict with link_zona and other fields.
    """
    logger.info(f"Reading zone descriptions from {csv_path} for semester {semester}")

    df = pd.read_csv(
        csv_path,
        sep=";",
        encoding="utf-8",
        dtype=str,
        skiprows=1,
        on_bad_lines="warn",
    )

    if df.empty:
        return {}

    df.columns = df.columns.str.strip()
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].str.strip()

    # Drop trailing empty column
    if df.columns[-1] == "" or df.columns[-1].startswith("Unnamed"):
        df = df.iloc[:, :-1]

    # Clean Zona_Descr: strip spurious single quotes
    if "Zona_Descr" in df.columns:
        df["Zona_Descr"] = df["Zona_Descr"].str.strip("'").str.strip()

    # Build lookup: (Comune_amm, Zona) -> row data
    lookup = {}
    for _, row in df.iterrows():
        key = (row.get("Comune_amm", ""), row.get("Zona", ""))
        lookup[key] = {
            "link_zona": row.get("LinkZona", ""),
            "province_code": row.get("Prov", ""),
            "municipality_istat": row.get("Comune_ISTAT", ""),
            "municipality_name": row.get("Comune_descrizione", ""),
            "fascia": row.get("Fascia", ""),
            "zone_code": row.get("Zona", ""),
            "zone_description": row.get("Zona_Descr", ""),
        }

    logger.info(f"Built zone lookup with {len(lookup)} entries for {semester}")
    return lookup
