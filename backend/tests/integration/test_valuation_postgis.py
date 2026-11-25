"""Valuations on real PostGIS, through the API routes (M4 check).

Runs only when TEST_DATABASE_URL points at a disposable PostGIS database. The
fixture runs every migration, imports the synthetic semester of
tests/omi_fixtures.py through the real importer, and adds four sales: two in
zone MI00000001 (MILANO, zone code B01) and two in another municipality whose
zone code is also B01. The routes read real NUMERIC values through a real
database session; only the geocoder is replaced, by fixed coordinates.
"""

from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db_url import async_database_url, sync_database_url
from app.services.geocoder import GeoResult
from tests.auth_helpers import auth_headers
from tests.omi_fixtures import SEMESTER, make_archive

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set")

BACKEND_DIR = Path(__file__).resolve().parents[2]
IN_B01 = "Via Esatta 1, Milano"      # zone MI00000001, outside its hole
IN_C01 = "Via Seconda 2, Milano"     # first part of zone MI00000002
POINTS = {
    IN_B01: GeoResult(lat=45.42, lng=9.12, source="test", precision="exact", matched_address=IN_B01),
    IN_C01: GeoResult(lat=45.415, lng=9.315, source="test", precision="exact", matched_address=IN_C01),
}
SALE_NOTE = "valuation test sale"
SALES = [
    (date(2024, 5, 10), Decimal("205000.00"), "MILANO", "B01", "MI00000001", Decimal("82.0")),
    (date(2024, 8, 21), Decimal("221500.50"), "MILANO", "B01", "MI00000001", Decimal("90.0")),
    (date(2024, 6, 1), Decimal("99000.00"), "TORINO", "B01", "TO00000099", Decimal("80.0")),
    (date(2024, 7, 2), Decimal("98000.00"), "TORINO", "B01", "TO00000099", Decimal("75.0")),
]
DETAILS = {"conservation_state": "NORMALE", "renovation": "none", "floor": "second", "exposure": "east_west",
           "noise": "normal", "common_areas": "good", "building_facade": "good_condition",
           "energy_class": "E", "elevator": "yes"}


@pytest.fixture(scope="module")
def seeded(tmp_path_factory):
    from scripts.import_omi import discover_and_import_all

    engine = create_engine(sync_database_url(TEST_DATABASE_URL))
    with engine.begin() as conn:
        for schema in ("app", "omi"):
            conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        conn.execute(text((BACKEND_DIR / "sql" / "client_roles.sql").read_text()))
    directory = tmp_path_factory.mktemp("omi")
    make_archive(directory)
    assert discover_and_import_all(str(directory), TEST_DATABASE_URL) == 0  # every migration, then the semester
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO omi.transactions (transaction_date, transaction_type, declared_price, municipality, "
                 "omi_zone, link_zona, cadastral_category, cadastral_mq, notes) "
                 "VALUES (:d, 'compravendita', :p, :m, :z, :l, 'A/2', :mq, :n)"),
            [{"d": d, "p": p, "m": m, "z": z, "l": lz, "mq": mq, "n": SALE_NOTE} for d, p, m, z, lz, mq in SALES],
        )
    yield engine
    engine.dispose()


@pytest.fixture
def api(seeded, monkeypatch):
    from fastapi.testclient import TestClient

    from app.database import get_db
    from app.main import app

    async def fixed_point(self, address):
        return POINTS.get(address)

    monkeypatch.setattr("app.services.geocoder.ItalianGeocoder.geocode", fixed_point)
    sessions = async_sessionmaker(create_async_engine(async_database_url(TEST_DATABASE_URL), poolclass=NullPool),
                                  expire_on_commit=False)

    async def real_db():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = real_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


def valuate(api, address, surface="80"):
    response = api.get("/api/valuate", params={"address": address, "surface_m2": surface}, headers=auth_headers())
    assert response.status_code == 200, response.text
    return response.json()


def test_a_valuation_computes_from_real_numeric_values(api):
    result = valuate(api, IN_B01)
    assert result["zone"]["link_zona"] == "MI00000001"
    assert result["semester"] == SEMESTER
    estimate = result["estimate"]
    # NORMALE, prevalent: 2100.00-2800.00 EUR/m2 (NUMERIC), times 80 m2.
    assert (estimate["min"], estimate["max"], estimate["mid"]) == (168000, 224000, 196000)
    assert "no_data" not in result


# Zero and negative ranges are value rules, covered by tests/test_valuation_numbers.py.
# Here: the reversed range, which the old code turned into an estimate, and the
# NULL range, which only the database driver produces.
@pytest.mark.parametrize(("price_min", "price_max"), [(2800, 2100), (None, None)], ids=["reversed", "missing"])
def test_an_unusable_range_gives_a_no_data_result(api, seeded, price_min, price_max):
    with seeded.begin() as conn:
        original = conn.execute(text("SELECT price_min, price_max FROM omi.quotations WHERE link_zona = 'MI00000002'")).one()
        conn.execute(text("UPDATE omi.quotations SET price_min = :a, price_max = :b WHERE link_zona = 'MI00000002'"),
                     {"a": price_min, "b": price_max})
    try:
        result = valuate(api, IN_C01)
    finally:
        with seeded.begin() as conn:
            conn.execute(text("UPDATE omi.quotations SET price_min = :a, price_max = :b WHERE link_zona = 'MI00000002'"),
                         {"a": original[0], "b": original[1]})
    assert result["zone"]["link_zona"] == "MI00000002"
    assert result["no_data"]["reason"] == "no_usable_quotation"
    assert result.get("estimate") is None


def test_comparables_are_the_zone_s_own_sales_only(api):
    comparables = valuate(api, IN_B01)["comparables"]
    # Same zone code B01 in TORINO: those sales are another municipality's.
    assert [(c["transaction_date"], c["declared_price"]) for c in comparables] == [
        ("2024-08-21", 221500.5), ("2024-05-10", 205000.0)]


def test_the_enhanced_valuation_compares_with_decimal_comparables(api):
    response = api.post("/api/valuate/enhanced", headers=auth_headers(),
                        json={"address": IN_B01, "surface_m2": 80, "details": DETAILS})
    assert response.status_code == 200, response.text
    result = response.json()
    benchmark = result["adjusted_estimate"]["benchmark_comparison"]
    assert benchmark["has_comparables"] is True
    # EUR/m2 of the zone's own sales: 205000.00 / 82.0 and 221500.50 / 90.0.
    assert benchmark["closest_eur_m2"] in (2500.0, 2461.12)
    assert benchmark["confidence"] in {"high", "medium", "low"}
    assert {c["declared_price"] for c in result["comparables"]} == {221500.5, 205000.0}


def test_transaction_pages_hold_on_real_rows(api, seeded):
    with seeded.begin() as conn:
        conn.execute(text("INSERT INTO omi.transactions (transaction_date, municipality, notes) "
                          "SELECT DATE '2023-01-01' + i, 'PAGINE', 'page test' FROM generate_series(1, 120) AS i"))
    try:
        first = api.get("/api/transactions", params={"municipality": "PAGINE", "limit": 100}, headers=auth_headers())
        rest = api.get("/api/transactions", params={"municipality": "PAGINE", "limit": 100, "offset": 100},
                       headers=auth_headers())
    finally:
        with seeded.begin() as conn:
            conn.execute(text("DELETE FROM omi.transactions WHERE notes = 'page test'"))
    assert first.status_code == rest.status_code == 200
    assert len(first.json()) == 100 and len(rest.json()) == 20
    assert {row["id"] for row in first.json()}.isdisjoint(row["id"] for row in rest.json())
