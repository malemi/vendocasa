"""Valuation service: combines geocoding, zone lookup, and quotation retrieval.

Money arithmetic is exact (app/services/numbers.py). A quotation range that is
missing, non-positive or reversed is unusable; when a zone has no usable range
the result carries an explicit `no_data` entry instead of failing. Every result
says whether the location is approximate (geocoding or zone fallback).
"""

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.coefficients import (
    compute_adjusted_estimate,
    compare_with_benchmarks,
)
from app.services.geocoder import GeoResult, geocoder
from app.services.numbers import jsonable_rows, money, to_decimal, usable_range
from app.services.zone_lookup import ZoneResult, find_zone, get_latest_semester, semester_is_complete


# ---------------------------------------------------------------------------
# Reusable pipeline steps
# ---------------------------------------------------------------------------

async def geocode_and_find_zone(
    address: str,
    semester: str | None,
    db: AsyncSession,
) -> tuple[GeoResult, ZoneResult, str]:
    """Geocode an address and find its OMI zone.

    Returns (coords, zone, semester).
    Raises ValueError if address or zone not found.
    """
    coords = await geocoder.geocode(address)
    if not coords:
        raise ValueError(f"Address not found: {address}")

    if not semester:
        semester = await get_latest_semester(db)
        if not semester:
            raise ValueError("No data available in the database")
    elif not await semester_is_complete(semester, db):
        raise ValueError(f"Semester {semester} is not available")

    zone = await find_zone(coords.lat, coords.lng, semester, db)
    if not zone:
        raise ValueError(f"No OMI zone found for coordinates ({coords.lat}, {coords.lng})")

    return coords, zone, semester


async def get_quotations(
    link_zona: str,
    semester: str,
    property_type: int,
    db: AsyncSession,
) -> list[dict]:
    """Fetch quotations for a zone, semester, and property type."""
    result = await db.execute(
        text("""
            SELECT property_type_desc, conservation_state, is_prevalent,
                   price_min, price_max, surface_type_sale,
                   rent_min, rent_max, surface_type_rent
            FROM omi.quotations
            WHERE link_zona = :link_zona
              AND semester = :semester
              AND property_type_code = :ptype
            ORDER BY is_prevalent DESC, conservation_state
        """),
        {"link_zona": link_zona, "semester": semester, "ptype": property_type},
    )
    return [dict(row._mapping) for row in result.all()]


async def get_comparables(
    link_zona: str,
    db: AsyncSession,
    limit: int = 20,
) -> list[dict]:
    """Fetch comparable transactions for a zone, by its exact link_zona.

    Zone codes such as "B01" repeat across municipalities, so matching on the
    code would mix in sales from other cities; rows without a link_zona are
    therefore not comparables.
    """
    result = await db.execute(
        text("""
            SELECT transaction_date, declared_price, cadastral_category,
                   cadastral_vani, cadastral_mq, notes
            FROM omi.transactions
            WHERE link_zona = :link_zona
            ORDER BY transaction_date DESC NULLS LAST, id DESC
            LIMIT :limit
        """),
        {"link_zona": link_zona, "limit": limit},
    )
    return [dict(row._mapping) for row in result.all()]


NO_DATA = {
    "reason": "no_usable_quotation",
    "message": "Nessuna quotazione OMI utilizzabile per questa zona, tipologia e semestre.",
}


def _zone_info(zone: ZoneResult) -> dict:
    return {
        "link_zona": zone.link_zona,
        "zone_code": zone.zone_code,
        "fascia": zone.fascia,
        "municipality": zone.municipality_name,
        "description": zone.zone_description,
        "distance_m": zone.distance_m,
    }


def _location(coords: GeoResult, zone: ZoneResult) -> dict:
    """Where the estimate is placed, and whether that place is approximate."""
    outside_zone = bool(zone.distance_m and zone.distance_m > 0)
    return {
        "precision": coords.precision,
        "source": coords.source,
        "matched_address": coords.matched_address,
        "zone_distance_m": zone.distance_m,
        "approximate": coords.precision != "exact" or outside_zone,
    }


# ---------------------------------------------------------------------------
# Basic valuation (original endpoint)
# ---------------------------------------------------------------------------

async def valuate_address(
    address: str,
    property_type: int,
    surface_m2: float | None,
    semester: str | None,
    db: AsyncSession,
) -> dict:
    """Full valuation pipeline for an address.

    Returns a dict with coordinates, zone info, quotations, estimate, and comparables.
    Raises ValueError if address or zone not found.
    """
    coords, zone, semester = await geocode_and_find_zone(address, semester, db)

    quotations = await get_quotations(zone.link_zona, semester, property_type, db)
    comparables = await get_comparables(zone.link_zona, db)

    # The prevalent quotation's range, or the first usable one.
    ranges = [
        (bool(q.get("is_prevalent")), usable_range(q.get("price_min"), q.get("price_max")))
        for q in quotations
    ]
    usable = [(prevalent, r) for prevalent, r in ranges if r is not None]
    chosen = next((r for prevalent, r in usable if prevalent), usable[0][1] if usable else None)

    estimate = None
    surface = to_decimal(surface_m2)
    if chosen and surface is not None and surface > 0:
        p_min, p_max = chosen
        estimate = {
            "min": money(p_min * surface),
            "max": money(p_max * surface),
            "mid": money((p_min + p_max) / 2 * surface),
            "eur_per_m2_range": [money(p_min), money(p_max)],
        }

    result = {
        "address": address,
        "coordinates": {"lat": coords.lat, "lng": coords.lng},
        "location": _location(coords, zone),
        "zone": _zone_info(zone),
        "semester": semester,
        "quotations": jsonable_rows(quotations),
        "estimate": estimate,
        "comparables": jsonable_rows(comparables),
    }
    if chosen is None:
        result["no_data"] = NO_DATA
    return result


# ---------------------------------------------------------------------------
# Enhanced valuation (with correction coefficients)
# ---------------------------------------------------------------------------

async def enhanced_valuate_address(
    address: str,
    property_type: int,
    surface_m2: float,
    semester: str | None,
    property_details: dict[str, str],
    db: AsyncSession,
) -> dict:
    """Enhanced valuation with correction coefficients applied.

    Like valuate_address but:
    1. Groups quotations by conservation state so the user can see all ranges
    2. Uses the user-selected conservation_state as the base
    3. Applies correction coefficients from property_details
    4. Compares with real transaction benchmarks

    Returns a dict with enhanced valuation data.
    Raises ValueError if address or zone not found, or no quotation data.
    """
    coords, zone, semester = await geocode_and_find_zone(address, semester, db)

    quotations = await get_quotations(zone.link_zona, semester, property_type, db)
    comparables = await get_comparables(zone.link_zona, db)

    # Group usable quotations by conservation state (exact Decimal ranges).
    ranges_by_state: dict[str, tuple[Decimal, Decimal]] = {}
    quotations_by_state: dict[str, dict] = {}
    for q in quotations:
        state = q.get("conservation_state") or "SCONOSCIUTO"
        usable = usable_range(q.get("price_min"), q.get("price_max"))
        if usable is None:
            continue
        ranges_by_state[state] = usable
        quotations_by_state[state] = {
            "price_min": money(usable[0]),
            "price_max": money(usable[1]),
            "is_prevalent": bool(q.get("is_prevalent")),
            "surface_type_sale": q.get("surface_type_sale"),
        }

    if not ranges_by_state:
        return {
            "address": address,
            "coordinates": {"lat": coords.lat, "lng": coords.lng},
            "location": _location(coords, zone),
            "zone": _zone_info(zone),
            "semester": semester,
            "no_data": NO_DATA,
            "comparables": jsonable_rows(comparables),
        }

    # Select the base OMI range for the user-chosen conservation state,
    # falling back to the prevalent state, then to the first usable one.
    selected_state = property_details.get("conservation_state", "NORMALE")
    if selected_state not in ranges_by_state:
        prevalent_state = next(
            (s for s, v in quotations_by_state.items() if v.get("is_prevalent")),
            None,
        )
        selected_state = prevalent_state or next(iter(ranges_by_state))
    base_min, base_max = ranges_by_state[selected_state]

    # Apply correction coefficients
    details_for_engine = {k: v for k, v in property_details.items() if k != "conservation_state"}
    adjusted = compute_adjusted_estimate(
        omi_price_min=base_min,
        omi_price_max=base_max,
        surface_m2=surface_m2,
        property_details=details_for_engine,
    )
    adjusted.base_conservation_state = selected_state

    # Compare with benchmarks
    benchmark = compare_with_benchmarks(adjusted.adjusted_mid, comparables)
    adjusted.benchmark_comparison = benchmark

    return {
        "address": address,
        "coordinates": {"lat": coords.lat, "lng": coords.lng},
        "location": _location(coords, zone),
        "zone": _zone_info(zone),
        "semester": semester,
        "quotations_by_state": quotations_by_state,
        "adjusted_estimate": {
            "base_price_min": adjusted.base_price_min,
            "base_price_max": adjusted.base_price_max,
            "base_conservation_state": adjusted.base_conservation_state,
            "total_coefficient": adjusted.total_coefficient,
            "adjusted_price_min": adjusted.adjusted_price_min,
            "adjusted_price_max": adjusted.adjusted_price_max,
            "adjusted_mid": adjusted.adjusted_mid,
            "total_min": adjusted.total_min,
            "total_max": adjusted.total_max,
            "total_mid": adjusted.total_mid,
            "surface_m2": adjusted.surface_m2,
            "breakdown": [
                {
                    "factor": b.factor,
                    "factor_label": b.factor_label,
                    "selected_key": b.selected_key,
                    "selected_label": b.selected_label,
                    "coefficient": b.coefficient,
                    "impact_eur_m2": b.impact_eur_m2,
                }
                for b in adjusted.breakdown
            ],
            "benchmark_comparison": {
                "has_comparables": benchmark.has_comparables,
                "closest_eur_m2": benchmark.closest_eur_m2,
                "difference_pct": benchmark.difference_pct,
                "confidence": benchmark.confidence,
                "note": benchmark.note,
            } if benchmark else None,
        },
        "comparables": jsonable_rows(comparables),
    }
