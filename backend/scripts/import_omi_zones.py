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
from sqlalchemy import text

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

    Handles 3 KML formats:
    - 2010_S2, 2013_S2: LINKZONA populated, no CODCOM/CODZONA
    - 2014_S1: LINKZONA empty, no CODCOM/CODZONA — extract from filename + <name>
    - 2014_S2+: CODCOM + CODZONA present, LINKZONA empty

    Returns a list of dicts with keys:
        codcom, codzona, link_zona, geometry (Shapely MultiPolygon)
    """
    # Belfiore code from filename (e.g., A181.kml -> A181)
    filename_codcom = Path(kml_path).stem

    # Read as bytes and handle encoding issues (some KMLs have non-UTF-8 chars)
    raw = Path(kml_path).read_bytes()
    try:
        tree = etree.fromstring(raw)
    except etree.XMLSyntaxError:
        # Fallback: decode with replacement, then re-parse
        decoded = raw.decode("utf-8", errors="replace").encode("utf-8")
        try:
            tree = etree.fromstring(decoded)
        except etree.XMLSyntaxError as e:
            logger.warning(f"Cannot parse KML {kml_path}: {e}")
            return []
    root = tree

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
        link_zona = data.get("LINKZONA", "")

        # Three KML formats:
        # 1. LINKZONA populated directly (2010, 2013)
        # 2. CODCOM + CODZONA (2014_S2+)
        # 3. Neither — extract codcom from filename, codzona from <name> tag (2014_S1)
        if not codcom and not codzona and not link_zona:
            # Try to extract zone code from <name>: "CITY - Zona OMI R1"
            name_el = pm.find("{http://www.opengis.net/kml/2.2}name")
            if name_el is not None and name_el.text:
                zone_match = re.search(r"Zona\s+OMI\s+(\S+)", name_el.text)
                if zone_match:
                    codcom = filename_codcom
                    codzona = zone_match.group(1)
                else:
                    continue
            else:
                continue

        # Each <Polygon> (direct, or one of several in a MultiGeometry) has one
        # outer boundary and any number of inner boundaries, which are holes.
        polygons = [poly for poly_el in pm.iter(f"{KML_NS}Polygon")
                    if (poly := _parse_polygon(poly_el)) is not None]

        if not polygons:
            continue

        geom = MultiPolygon(polygons)

        zones.append({
            "codcom": codcom,
            "codzona": codzona,
            "link_zona": link_zona,
            "geometry": geom,
        })

    return zones


KML_NS = "{http://www.opengis.net/kml/2.2}"


def _ring_text(boundary_el) -> str | None:
    coords_el = boundary_el.find(f"{KML_NS}LinearRing/{KML_NS}coordinates")
    return coords_el.text.strip() if coords_el is not None and coords_el.text else None


def _parse_ring(coord_text: str) -> list[tuple[float, float]] | None:
    """Parse "lng,lat,alt lng,lat,alt ..." into a closed ring, or None."""
    points = []
    for triplet in coord_text.split():
        parts = triplet.split(",")
        if len(parts) >= 2:
            try:
                points.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue
    if len(points) < 3:
        return None
    if points[0] != points[-1]:
        points.append(points[0])
    return points


def _parse_polygon(polygon_el) -> Polygon | None:
    """A KML <Polygon>: its outerBoundaryIs is the shell, each innerBoundaryIs a hole."""
    outer = polygon_el.find(f"{KML_NS}outerBoundaryIs")
    shell_text = _ring_text(outer) if outer is not None else None
    shell = _parse_ring(shell_text) if shell_text else None
    if shell is None:
        return None
    holes = []
    for inner in polygon_el.findall(f"{KML_NS}innerBoundaryIs"):
        hole_text = _ring_text(inner)
        hole = _parse_ring(hole_text) if hole_text else None
        if hole is not None:
            holes.append(hole)
    try:
        return Polygon(shell, holes)
    except Exception:
        return None


def collect_zone_rows(kml_dir: str, semester: str, zone_lookup: dict) -> tuple[list[dict], int]:
    """Parse every KML file in `kml_dir` into zone rows ready to insert.

    Returns (rows, skipped). A row's `source_file` names its KML file, so a
    rejected row can be reported with its origin. Placemarks with no matching
    ZONE CSV entry are skipped and counted; they are not errors.
    """
    kml_files = sorted(Path(kml_dir).glob("*.kml"))
    logger.info(f"Found {len(kml_files)} KML files in {kml_dir}")

    rows: list[dict] = []
    skipped = 0
    # Build reverse index: link_zona -> zone_info (for older KMLs with direct LINKZONA)
    lz_reverse = {v["link_zona"]: v for v in zone_lookup.values() if v.get("link_zona")}

    for kml_path in kml_files:
        for pm in parse_kml_placemarks(str(kml_path)):
            # Older KMLs have LINKZONA directly; newer ones need lookup via CODCOM+CODZONA
            direct_lz = pm.get("link_zona", "")
            if direct_lz and re.match(r"^[A-Z]{2}\d{8}$", direct_lz):
                link_zona = direct_lz
                zone_info = lz_reverse.get(direct_lz, {})
            else:
                zone_info = zone_lookup.get((pm["codcom"], pm["codzona"]))
                if zone_info is None:
                    skipped += 1
                    continue
                link_zona = zone_info["link_zona"]
                if not link_zona or not re.match(r"^[A-Z]{2}\d{8}$", link_zona):
                    skipped += 1
                    continue

            rows.append({
                "link_zona": link_zona,
                "zone_code": zone_info.get("zone_code", ""),
                "fascia": zone_info.get("fascia", ""),
                "municipality_istat": zone_info.get("municipality_istat", ""),
                "municipality_name": zone_info.get("municipality_name", ""),
                "province_code": zone_info.get("province_code", ""),
                "zone_description": zone_info.get("zone_description", ""),
                "semester": semester,
                "wkt": pm["geometry"].wkt,
                "source_file": kml_path.name,
            })

    if skipped:
        logger.warning(f"Skipped {skipped} KML placemarks with no matching ZONE CSV entry")
    return rows, skipped


def insert_zone_rows(conn, rows: list[dict]) -> tuple[int, list[dict]]:
    """Insert zone rows on `conn` inside its current transaction.

    Each row runs in a savepoint, so one bad geometry does not hide the others:
    every rejected row is collected with its file, zone and error. The caller
    decides what a rejection means; the importer rolls the semester back.
    Returns (inserted, rejected).
    """
    inserted = 0
    rejected: list[dict] = []
    for row in rows:
        params = {k: v for k, v in row.items() if k != "source_file"}
        savepoint = conn.begin_nested()
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
                         :semester, ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_GeomFromText(:wkt, 4326)), 3)))
                    ON CONFLICT (link_zona, semester) DO NOTHING
                """),
                params,
            )
            savepoint.commit()
            inserted += result.rowcount
        except Exception as exc:
            savepoint.rollback()
            rejected.append({"file": row.get("source_file"), "link_zona": row["link_zona"],
                             "error": str(exc).splitlines()[0][:300]})
    return inserted, rejected
