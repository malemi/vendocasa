"""Valuation arithmetic, no-data outcomes and comparables (app/services/valuation.py).

The database returns NUMERIC columns as Decimal; these tests feed Decimal rows
through the real valuation functions with a recording fake session.
tests/integration/test_valuation_postgis.py runs the same paths on real PostGIS,
through the API routes.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services import valuation
from app.services.coefficients import compare_with_benchmarks
from app.services.geocoder import GeoResult
from app.services.zone_lookup import ZoneResult

ZONE = ZoneResult(link_zona="MI00000290", zone_code="B01", fascia="B", municipality_name="MILANO",
                  zone_description="CENTRO", distance_m=None)


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return [type("Row", (), {"_mapping": r})() for r in self._rows]


class FakeSession:
    """Returns `quotations` for quotation queries and `transactions` for comparables."""

    def __init__(self, quotations, transactions=()):
        self.quotations = list(quotations)
        self.transactions = list(transactions)
        self.statements: list[tuple[str, dict]] = []

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params or {}))
        return _Rows(self.transactions if "omi.transactions" in sql else self.quotations)


@pytest.fixture
def located(monkeypatch):
    def _install(precision="exact", distance_m=None):
        zone = ZoneResult(**{**ZONE.__dict__, "distance_m": distance_m})
        coords = GeoResult(lat=45.46, lng=9.19, source="photon", precision=precision,
                           matched_address="Via Roma 1, Milano")

        async def _geocode_and_find_zone(address, semester, db):
            return coords, zone, semester or "2024_S2"

        monkeypatch.setattr(valuation, "geocode_and_find_zone", _geocode_and_find_zone)

    _install()
    return _install


def _quotation(price_min, price_max, state="NORMALE", prevalent=True):
    return {"property_type_desc": "Abitazioni civili", "conservation_state": state, "is_prevalent": prevalent,
            "price_min": price_min, "price_max": price_max, "surface_type_sale": "L",
            "rent_min": Decimal("14.00"), "rent_max": Decimal("21.00"), "surface_type_rent": "L"}


@pytest.mark.asyncio
async def test_a_basic_estimate_from_decimal_rows_is_exact(located):
    db = FakeSession([_quotation(Decimal("2100.00"), Decimal("2800.00"))])
    result = await valuation.valuate_address("Via Roma 1", 20, 85.0, None, db)
    # The methodology document's worked example: 2,100-2,800 EUR/m2 over 85 m2.
    assert result["estimate"] == {"min": 178500.0, "max": 238000.0, "mid": 208250.0,
                                  "eur_per_m2_range": [2100.0, 2800.0]}
    assert result["quotations"][0]["price_min"] == 2100.0  # JSON-friendly, not Decimal
    assert "no_data" not in result


@pytest.mark.asyncio
async def test_float_surfaces_do_not_introduce_binary_rounding(located):
    db = FakeSession([_quotation(Decimal("1000.10"), Decimal("1000.10"))])
    result = await valuation.valuate_address("Via Roma 1", 20, 0.1, None, db)
    assert result["estimate"]["min"] == 100.01


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("price_min", "price_max"),
    [
        (Decimal("0"), Decimal("2800.00")),
        (Decimal("-100.00"), Decimal("2800.00")),
        (Decimal("2800.00"), Decimal("2100.00")),  # reversed
        (Decimal("NaN"), Decimal("2800.00")),
        (None, Decimal("2800.00")),
    ],
)
async def test_an_unusable_range_is_an_explicit_no_data_result(located, price_min, price_max):
    db = FakeSession([_quotation(price_min, price_max)])
    basic = await valuation.valuate_address("Via Roma 1", 20, 85.0, None, db)
    assert basic["estimate"] is None
    assert basic["no_data"]["reason"] == "no_usable_quotation"

    enhanced = await valuation.enhanced_valuate_address("Via Roma 1", 20, 85.0, None, {}, db)
    assert enhanced["no_data"]["reason"] == "no_usable_quotation"
    assert "adjusted_estimate" not in enhanced


@pytest.mark.asyncio
async def test_no_quotations_at_all_is_also_no_data(located):
    enhanced = await valuation.enhanced_valuate_address("Via Roma 1", 20, 85.0, None, {}, FakeSession([]))
    assert enhanced["no_data"]["reason"] == "no_usable_quotation"


@pytest.mark.asyncio
async def test_an_enhanced_estimate_with_decimal_comparables_works(located):
    transactions = [
        {"transaction_date": None, "declared_price": Decimal("250000.00"), "cadastral_category": "A/2",
         "cadastral_vani": Decimal("5.0"), "cadastral_mq": None, "notes": None},
        {"transaction_date": None, "declared_price": Decimal("480000.00"), "cadastral_category": "A/2",
         "cadastral_vani": None, "cadastral_mq": Decimal("55.0"), "notes": None},
    ]
    db = FakeSession([_quotation(Decimal("6500.00"), Decimal("8900.00"), state="OTTIMO")], transactions)
    details = {"conservation_state": "OTTIMO", "renovation": "premium_post_2015", "floor": "third_fourth",
               "exposure": "south_dual", "noise": "very_silent", "common_areas": "needs_maintenance"}
    result = await valuation.enhanced_valuate_address("Via Sottocorno 17", 20, 62.0, None, details, db)
    adjusted = result["adjusted_estimate"]
    # The methodology document's worked example: +21%, about 9,317 EUR/m2.
    assert adjusted["total_coefficient"] == 0.21
    assert adjusted["adjusted_mid"] == 9317.0
    assert adjusted["benchmark_comparison"]["closest_eur_m2"] == 8727.27
    assert result["comparables"][0]["declared_price"] == 250000.0


def test_benchmarks_accept_decimal_floats_and_missing_values():
    comparables = [{"declared_price": Decimal("300000"), "cadastral_vani": Decimal("6"), "cadastral_mq": None},
                   {"declared_price": None, "cadastral_mq": Decimal("50")},
                   {"declared_price": Decimal("NaN"), "cadastral_mq": Decimal("50")}]
    result = compare_with_benchmarks(3000.0, comparables)
    assert result.closest_eur_m2 == 2941.18  # 300,000 / (6 * 17)
    assert result.confidence == "high"


@pytest.mark.asyncio
async def test_comparables_match_the_exact_zone_only(located):
    db = FakeSession([_quotation(Decimal("2100.00"), Decimal("2800.00"))])
    await valuation.valuate_address("Via Roma 1", 20, 85.0, None, db)
    sql, params = next((s, p) for s, p in db.statements if "omi.transactions" in s)
    assert "link_zona = :link_zona" in sql
    assert "omi_zone" not in sql  # zone codes such as B01 repeat across municipalities
    assert params["link_zona"] == "MI00000290"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("precision", "distance_m", "approximate"),
    [("exact", None, False), ("approximate", None, True), ("exact", 120.0, True)],
)
async def test_results_say_when_the_location_is_approximate(located, precision, distance_m, approximate):
    located(precision=precision, distance_m=distance_m)
    db = FakeSession([_quotation(Decimal("2100.00"), Decimal("2800.00"))])
    result = await valuation.valuate_address("Via Roma 1", 20, None, None, db)
    assert result["location"]["approximate"] is approximate
    assert result["location"]["matched_address"] == "Via Roma 1, Milano"
