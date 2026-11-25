"""OMI import publication on real PostGIS (scripts/import_omi.py, migration 0005).

Runs only when TEST_DATABASE_URL points at a disposable PostGIS database. The
fixture creates the client roles and runs every migration, which also covers
the M1 check that `alembic upgrade head` works on an empty database.
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set")

BACKEND_DIR = Path(__file__).resolve().parents[2]
SEMESTER = "2024_S2"

ZONE_CSV = (
    "Zone OMI semestre 2024/2\n"
    "Prov;Comune_ISTAT;Comune_amm;Comune_descrizione;Fascia;Zona;Zona_Descr;LinkZona\n"
    "MI;015146;F205;MILANO;B;B01;'CENTRO CON BUCO';MI00000001\n"
    "MI;015146;F205;MILANO;C;C01;'SEMICENTRO IN DUE PARTI';MI00000002\n"
    "MI;015146;F205;MILANO;D;D01;'ZONA SENZA PERIMETRO';MI00000003\n"
)


def valori_csv(price_scale: int = 1) -> str:
    rows = [
        ("MI", "MI00000001", "20", "Abitazioni civili", "NORMALE", "P", 2100, 2800),
        ("MI", "MI00000002", "20", "Abitazioni civili", "NORMALE", "P", 1500, 1900),
        ("MI", "MI00000003", "20", "Abitazioni civili", "NORMALE", "P", 900, 1200),
    ]
    lines = ["Valori OMI semestre 2024/2",
             "Prov;LinkZona;Cod_Tip;Descr_Tipologia;Stato;Stato_prev;Compr_min;Compr_max;Sup_NL_compr;Loc_min;Loc_max;Sup_NL_loc"]
    for prov, lz, tip, desc, stato, prev, low, high in rows:
        lines.append(f"{prov};{lz};{tip};{desc};{stato};{prev};{low * price_scale};{high * price_scale};L;7;10;L")
    return "\n".join(lines) + "\n"


def kml(extra_placemark: str = "") -> str:
    def placemark(link_zona, polygons):
        return (f"<Placemark><ExtendedData><Data name=\"LINKZONA\"><value>{link_zona}</value></Data>"
                f"</ExtendedData><MultiGeometry>{polygons}</MultiGeometry></Placemark>")

    def polygon(outer, inner=None):
        inner_xml = (f"<innerBoundaryIs><LinearRing><coordinates>{inner}</coordinates></LinearRing>"
                     f"</innerBoundaryIs>") if inner else ""
        return (f"<Polygon><outerBoundaryIs><LinearRing><coordinates>{outer}</coordinates></LinearRing>"
                f"</outerBoundaryIs>{inner_xml}</Polygon>")

    holed = placemark("MI00000001", polygon("9.10,45.40 9.20,45.40 9.20,45.50 9.10,45.50 9.10,45.40",
                                             "9.14,45.44 9.16,45.44 9.16,45.46 9.14,45.46 9.14,45.44"))
    two_parts = placemark("MI00000002", polygon("9.30,45.40 9.33,45.40 9.33,45.43 9.30,45.43 9.30,45.40")
                          + polygon("9.40,45.40 9.42,45.40 9.42,45.42 9.40,45.42 9.40,45.40"))
    return ('<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
            f"{holed}{two_parts}{extra_placemark}</Document></kml>")


def make_archive(directory: Path, name: str = "omi_2024_2.zip", valori: str | None = None,
                 kml_text: str | None = None) -> Path:
    path = directory / name
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("QI_20242_ZONE.csv", ZONE_CSV)
        z.writestr("QI_20242_VALORI.csv", valori if valori is not None else valori_csv())
        z.writestr("F205.kml", kml_text if kml_text is not None else kml())
    return path


@pytest.fixture(scope="module")
def db():
    from scripts.import_omi import init_schema

    engine = create_engine(TEST_DATABASE_URL.replace("+psycopg_async://", "+psycopg://"))
    with engine.begin() as conn:
        for schema in ("app", "omi"):
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        conn.execute(text((BACKEND_DIR / "sql" / "client_roles.sql").read_text()))
    init_schema(TEST_DATABASE_URL)  # every migration, on an empty database
    yield engine
    engine.dispose()


@pytest.fixture
def clean(db):
    from scripts.import_omi import reset_schema

    reset_schema(TEST_DATABASE_URL)
    with db.begin() as conn:
        conn.execute(text("DELETE FROM omi.transactions"))
    return db


def scalar(engine, sql, **params):
    with engine.connect() as conn:
        return conn.execute(text(sql), params).scalar()


def test_postgis_is_available(db):
    assert scalar(db, "SELECT PostGIS_Version()")


def test_an_import_publishes_holes_parts_and_its_completion_record(clean, tmp_path):
    from scripts.import_omi import import_semester

    counts = import_semester(clean, SEMESTER, make_archive(tmp_path))
    assert counts["zones_count"] == 2
    assert counts["quotations_count"] == 3
    assert counts["quotations_without_zone"] == 1  # MI00000003 has no perimeter: legitimate
    assert scalar(clean, "SELECT count(*) FROM omi.semester_import WHERE semester = :s AND status = 'complete'",
                  s=SEMESTER) == 1
    # The hole: outer 0.1 x 0.1 degrees minus inner 0.02 x 0.02.
    area = scalar(clean, "SELECT ST_Area(geom) FROM omi.zones WHERE link_zona = 'MI00000001'")
    assert abs(area - (0.01 - 0.0004)) < 1e-9
    in_hole = scalar(clean, "SELECT count(*) FROM omi.zones WHERE ST_Intersects(geom, "
                            "ST_SetSRID(ST_MakePoint(9.15, 45.45), 4326))")
    assert in_hole == 0
    parts = scalar(clean, "SELECT ST_NumGeometries(geom) FROM omi.zones WHERE link_zona = 'MI00000002'")
    assert parts == 2
    for lng, lat in ((9.31, 45.41), (9.41, 45.41)):
        assert scalar(clean, "SELECT count(*) FROM omi.zones WHERE link_zona = 'MI00000002' AND "
                             "ST_Intersects(geom, ST_SetSRID(ST_MakePoint(:x, :y), 4326))", x=lng, y=lat) == 1


def test_a_retry_replaces_and_does_not_duplicate(clean, tmp_path):
    from scripts.import_omi import import_semester

    import_semester(clean, SEMESTER, make_archive(tmp_path))
    import_semester(clean, SEMESTER, make_archive(tmp_path, "again.zip", valori=valori_csv(price_scale=2)))
    assert scalar(clean, "SELECT count(*) FROM omi.zones WHERE semester = :s", s=SEMESTER) == 2
    assert scalar(clean, "SELECT count(*) FROM omi.quotations WHERE semester = :s", s=SEMESTER) == 3
    assert scalar(clean, "SELECT price_min FROM omi.quotations WHERE link_zona = 'MI00000001'") == 4200


def test_a_failed_import_leaves_the_previous_data_current(clean, tmp_path):
    from scripts.import_omi import SemesterImportFailed, import_semester

    import_semester(clean, SEMESTER, make_archive(tmp_path))
    # A duplicate quotation key makes COPY fail after the old rows were deleted.
    broken = valori_csv() + valori_csv().splitlines()[2] + "\n"
    with pytest.raises(SemesterImportFailed):
        import_semester(clean, SEMESTER, make_archive(tmp_path, "broken.zip", valori=broken))
    assert scalar(clean, "SELECT count(*) FROM omi.quotations WHERE semester = :s", s=SEMESTER) == 3
    assert scalar(clean, "SELECT count(*) FROM omi.semester_import WHERE semester = :s", s=SEMESTER) == 1


def test_a_rejected_zone_row_rolls_the_semester_back_and_names_it(clean, tmp_path, monkeypatch):
    from scripts import import_omi_zones
    from scripts.import_omi import SemesterImportFailed, import_semester

    real_collect = import_omi_zones.collect_zone_rows

    def collect_with_a_bad_row(kml_dir, semester, zone_lookup):
        rows, skipped = real_collect(kml_dir, semester, zone_lookup)
        rows.append({**rows[0], "link_zona": "MI00000009", "wkt": "POLYGON((not a geometry))",
                     "source_file": "BAD.kml"})
        return rows, skipped

    monkeypatch.setattr("scripts.import_omi.collect_zone_rows", collect_with_a_bad_row)
    with pytest.raises(SemesterImportFailed) as info:
        import_semester(clean, SEMESTER, make_archive(tmp_path))
    assert [r["link_zona"] for r in info.value.rejected] == ["MI00000009"]
    assert info.value.rejected[0]["file"] == "BAD.kml"
    assert scalar(clean, "SELECT count(*) FROM omi.zones") == 0
    assert scalar(clean, "SELECT count(*) FROM omi.semester_import") == 0


def test_reset_keeps_transactions_and_app_tables_and_clears_completion(clean, tmp_path):
    from scripts.import_omi import import_semester, reset_schema

    import_semester(clean, SEMESTER, make_archive(tmp_path))
    with clean.begin() as conn:
        conn.execute(text("INSERT INTO omi.transactions (declared_price, link_zona, notes) "
                          "VALUES (250000, 'MI00000001', 'nota')"))
    fingerprint_sql = ("SELECT md5(string_agg(t::text, '|' ORDER BY t::text)) FROM ({}) t")
    before = {name: scalar(clean, fingerprint_sql.format(f"SELECT * FROM {name}"))
              for name in ("omi.transactions", "app.disposable_email_domains", "app.service_flag")}

    reset_schema(TEST_DATABASE_URL)

    after = {name: scalar(clean, fingerprint_sql.format(f"SELECT * FROM {name}")) for name in before}
    assert after == before
    assert scalar(clean, "SELECT count(*) FROM omi.semester_import") == 0  # nothing is complete

    import_semester(clean, SEMESTER, make_archive(tmp_path, "after-reset.zip"))
    assert scalar(clean, "SELECT count(*) FROM omi.semester_import WHERE status = 'complete'") == 1


def test_validation_passes_valid_semesters_and_reports_missing_perimeters(clean, tmp_path):
    from scripts.import_omi import import_semester
    from scripts.validate_semesters import validate

    import_semester(clean, SEMESTER, make_archive(tmp_path))
    with clean.begin() as conn:  # a legacy semester with quotations and no zones
        conn.execute(text("INSERT INTO omi.quotations (link_zona, semester, property_type_code, "
                          "conservation_state, price_min, price_max) VALUES ('MI00000001', '2023_S1', 20, "
                          "'NORMALE', 2000, 2600)"))
    report = {r["semester"]: r for r in validate(TEST_DATABASE_URL)}
    assert report[SEMESTER]["passes"] and report[SEMESTER]["quotations_without_zone"] == 1
    assert report[SEMESTER]["recorded_complete"]
    assert not report["2023_S1"]["passes"]  # no zones


def test_the_backfill_marks_valid_legacy_semesters_complete(clean, tmp_path):
    from alembic import command
    from alembic.config import Config

    from app.config import settings
    from scripts.import_omi import import_semester

    import_semester(clean, SEMESTER, make_archive(tmp_path))  # zones and quotations exist
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    original = settings.database_url
    settings.database_url = TEST_DATABASE_URL
    try:
        command.downgrade(cfg, "0004")  # as before this work: data, no records
        with clean.begin() as conn:
            conn.execute(text("INSERT INTO omi.quotations (link_zona, semester, property_type_code, "
                              "conservation_state, price_min, price_max) VALUES ('MI00000001', '2023_S1', 20, "
                              "'NORMALE', 2000, 2600)"))
        command.upgrade(cfg, "head")
    finally:
        settings.database_url = original
    complete = {row[0] for row in clean.connect().execute(text("SELECT semester FROM omi.semester_import"))}
    assert complete == {SEMESTER}  # 2023_S1 has no zones: not selectable
