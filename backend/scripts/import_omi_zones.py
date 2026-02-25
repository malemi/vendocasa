"""Import OMI zone perimeters from KML files into PostGIS.

Each KML file represents one municipality (named by Belfiore code, e.g. A089.kml).
Each Placemark is one OMI zone polygon with ExtendedData containing CODCOM and CODZONA.

LINKZONA is empty in the KMLs, so we construct it by looking up the ZONE CSV
via (CODCOM, CODZONA) -> LinkZona.
"""

import logging
import re
from pathlib import Path

from lxml import etree
from shapely.geometry import MultiPolygon, Polygon
from shapely import wkt
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}


def parse_semester_from_kml(kml_path: str) -> str | None:
    """Extract semester from KML Document name element.

    Pattern: "AGRIGENTO (AG) Anno/Semestre 2025/1 generato il ..."
    Returns: "2025_S1" or None.
    """
    try:
        # Only parse the first few KB to find the Document name
        with open(kml_path, "rb") as f:
            # Read enough to get the Document name
            header = f.read(2048)

        match = re.search(rb"Anno/Semestre\s+(\d{4})/(\d)", header)
        if match:
            year = match.group(1).decode()
            sem = match.group(2).decode()
            return f"{year}_S{sem}"
    except Exception as e:
        logger.warning(f"Could not parse semester from {kml_path}: {e}")

    return None


def parse_kml_placemarks(kml_path: str) -> list[dict]:
    """Parse a KML file and extract zone data + geometry for each Placemark.

    Returns a list of dicts with keys:
        codcom, codzona, geometry (Shapely MultiPolygon)
    """
    tree = etree.parse(kml_path)
    root = tree.getroot()

    zones = []
    for pm in root.iter("{http://www.opengis.net/kml/2.2}Placemark"):
        data = {}

        # Extract ExtendedData fields
        for data_el in pm.iter("{http://www.opengis.net/kml/2.2}Data"):
            name = data_el.get("name", "")
            value_el = data_el.find("{http://www.opengis.net/kml/2.2}value")
            if value_el is not None and value_el.text:
                data[name] = value_el.text.strip()

        codcom = data.get("CODCOM", "")
        codzona = data.get("CODZONA", "")

        if not codcom or not codzona:
            continue

        # Parse all polygons (may be inside MultiGeometry or direct)
        polygons = []
        for coords_el in pm.iter("{http://www.opengis.net/kml/2.2}coordinates"):
            if coords_el.text:
                poly = _parse_coordinates(coords_el.text.strip())
                if poly is not None:
                    polygons.append(poly)

        if not polygons:
            continue

        geom = MultiPolygon(polygons)

        zones.append({
            "codcom": codcom,
            "codzona": codzona,
            "geometry": geom,
        })

    return zones


def _parse_coordinates(coord_text: str) -> Polygon | None:
    """Parse KML coordinate string into a Shapely Polygon.

    Format: "lng,lat,alt lng,lat,alt ..."
    """
    points = []
    for triplet in coord_text.split():
        parts = triplet.split(",")
        if len(parts) >= 2:
            try:
                lng = float(parts[0])
                lat = float(parts[1])
                points.append((lng, lat))
            except ValueError:
                continue

    if len(points) >= 3:
        # Ensure ring is closed
        if points[0] != points[-1]:
            points.append(points[0])
        try:
            return Polygon(points)
        except Exception:
            return None
    return None


def import_kml_zones(
    kml_dir: str,
    semester: str,
    zone_lookup: dict,
    db_url: str,
) -> int:
    """Import all KML files from a directory into PostGIS.

    Args:
        kml_dir: Directory containing KML files.
        semester: Semester string, e.g. "2025_S1".
        zone_lookup: Dict from import_zone_descriptions: (belfiore_code, zone_code) -> row data.
        db_url: PostgreSQL connection string.

    Returns:
        Number of zones imported.
    """
    kml_files = sorted(Path(kml_dir).glob("*.kml"))
    logger.info(f"Found {len(kml_files)} KML files in {kml_dir}")

    engine = create_engine(db_url)
    total = 0
    skipped_no_lookup = 0

    for kml_path in kml_files:
        placemarks = parse_kml_placemarks(str(kml_path))
        if not placemarks:
            continue

        for pm in placemarks:
            codcom = pm["codcom"]
            codzona = pm["codzona"]
            geom = pm["geometry"]

            # Look up zone metadata from ZONE CSV
            key = (codcom, codzona)
            zone_info = zone_lookup.get(key)

            if zone_info is None:
                skipped_no_lookup += 1
                continue

            link_zona = zone_info["link_zona"]
            if not link_zona or not re.match(r"^[A-Z]{2}\d{8}$", link_zona):
                skipped_no_lookup += 1
                continue

            wkt_geom = geom.wkt

            try:
                with engine.begin() as conn:
                    conn.execute(
                        text("""
                            INSERT INTO omi.zones
                                (link_zona, zone_code, fascia, municipality_istat,
                                 municipality_name, province_code, zone_description,
                                 semester, geom)
                            VALUES
                                (:link_zona, :zone_code, :fascia, :municipality_istat,
                                 :municipality_name, :province_code, :zone_description,
                                 :semester, ST_GeomFromText(:wkt, 4326))
                            ON CONFLICT (link_zona, semester) DO NOTHING
                        """),
                        {
                            "link_zona": link_zona,
                            "zone_code": zone_info["zone_code"],
                            "fascia": zone_info["fascia"],
                            "municipality_istat": zone_info["municipality_istat"],
                            "municipality_name": zone_info["municipality_name"],
                            "province_code": zone_info["province_code"],
                            "zone_description": zone_info["zone_description"],
                            "semester": semester,
                            "wkt": wkt_geom,
                        },
                    )
                total += 1
            except Exception as e:
                if "duplicate" in str(e).lower():
                    pass  # Already exists
                else:
                    logger.error(f"Error importing zone {link_zona} from {kml_path.name}: {e}")

    if skipped_no_lookup > 0:
        logger.warning(
            f"Skipped {skipped_no_lookup} KML placemarks with no matching ZONE CSV entry"
        )
    logger.info(f"Imported {total} zone polygons for {semester}")
    return total


def import_kml_zones_batch(
    kml_dir: str,
    semester: str,
    zone_lookup: dict,
    db_url: str,
    batch_size: int = 500,
) -> int:
    """Batch version of KML import for better performance.

    Collects zones into batches and inserts them in bulk.
    """
    kml_files = sorted(Path(kml_dir).glob("*.kml"))
    logger.info(f"Found {len(kml_files)} KML files in {kml_dir}")

    engine = create_engine(db_url)
    total = 0
    skipped = 0
    batch = []

    for kml_path in kml_files:
        placemarks = parse_kml_placemarks(str(kml_path))
        for pm in placemarks:
            key = (pm["codcom"], pm["codzona"])
            zone_info = zone_lookup.get(key)

            if zone_info is None:
                skipped += 1
                continue

            link_zona = zone_info["link_zona"]
            if not link_zona or not re.match(r"^[A-Z]{2}\d{8}$", link_zona):
                skipped += 1
                continue

            batch.append({
                "link_zona": link_zona,
                "zone_code": zone_info["zone_code"],
                "fascia": zone_info["fascia"],
                "municipality_istat": zone_info["municipality_istat"],
                "municipality_name": zone_info["municipality_name"],
                "province_code": zone_info["province_code"],
                "zone_description": zone_info["zone_description"],
                "semester": semester,
                "wkt": pm["geometry"].wkt,
            })

            if len(batch) >= batch_size:
                total += _insert_batch(engine, batch)
                batch = []

    # Flush remaining
    if batch:
        total += _insert_batch(engine, batch)

    if skipped > 0:
        logger.warning(f"Skipped {skipped} KML placemarks with no matching ZONE CSV entry")
    logger.info(f"Imported {total} zone polygons for {semester}")
    return total


def _insert_batch(engine, batch: list[dict]) -> int:
    """Insert a batch of zone records."""
    inserted = 0
    with engine.begin() as conn:
        for row in batch:
            try:
                result = conn.execute(
                    text("""
                        INSERT INTO omi.zones
                            (link_zona, zone_code, fascia, municipality_istat,
                             municipality_name, province_code, zone_description,
                             semester, geom)
                        VALUES
                            (:link_zona, :zone_code, :fascia, :municipality_istat,
                             :municipality_name, :province_code, :zone_description,
                             :semester, ST_GeomFromText(:wkt, 4326))
                        ON CONFLICT (link_zona, semester) DO NOTHING
                    """),
                    row,
                )
                if result.rowcount > 0:
                    inserted += 1
            except Exception as e:
                logger.error(f"Error inserting zone {row['link_zona']}: {e}")
    return inserted
