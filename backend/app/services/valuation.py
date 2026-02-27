"""Valuation service: combines geocoding, zone lookup, and quotation retrieval."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.coefficients import (
    compute_adjusted_estimate,
    compare_with_benchmarks,
)
from app.services.geocoder import GeoResult, geocoder
from app.services.zone_lookup import ZoneResult, find_zone, get_latest_semester


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
    coords = await geocoder.geocode(address, db)
    if not coords:
        raise ValueError(f"Address not found: {address}")

    if not semester:
        semester = await get_latest_semester(db)
        if not semester:
            raise ValueError("No data available in the database")

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
    zone_code: str,
    db: AsyncSession,
    limit: int = 20,
) -> list[dict]:
    """Fetch comparable transactions for a zone."""
    result = await db.execute(
        text("""
            SELECT transaction_date, declared_price, cadastral_category,
                   cadastral_vani, cadastral_mq, notes
            FROM omi.transactions
            WHERE link_zona = :link_zona
               OR omi_zone = :zone_code
            ORDER BY transaction_date DESC
            LIMIT :limit
        """),
        {"link_zona": link_zona, "zone_code": zone_code, "limit": limit},
    )
    return [dict(row._mapping) for row in result.all()]


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
    comparables = await get_comparables(zone.link_zona, zone.zone_code, db)

    # Compute estimate from prevalent quotation
    estimate = None
    prevalent = next((q for q in quotations if q.get("is_prevalent")), None)
    if prevalent is None and quotations:
        prevalent = quotations[0]

    if prevalent and surface_m2:
        p_min = float(prevalent["price_min"]) if prevalent["price_min"] else 0
        p_max = float(prevalent["price_max"]) if prevalent["price_max"] else 0
        if p_min > 0 and p_max > 0:
            avg = (p_min + p_max) / 2
            estimate = {
                "min": round(p_min * surface_m2, 2),
                "max": round(p_max * surface_m2, 2),
                "mid": round(avg * surface_m2, 2),
                "eur_per_m2_range": [p_min, p_max],
            }

    return {
        "address": address,
        "coordinates": {"lat": coords.lat, "lng": coords.lng},
        "zone": {
            "link_zona": zone.link_zona,
            "zone_code": zone.zone_code,
            "fascia": zone.fascia,
            "municipality": zone.municipality_name,
            "description": zone.zone_description,
            "distance_m": zone.distance_m,
        },
        "semester": semester,
        "quotations": quotations,
        "estimate": estimate,
        "comparables": comparables,
    }


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

    Returns a dict matching EnhancedValuationResponse.
    Raises ValueError if address or zone not found, or no quotation data.
    """
    coords, zone, semester = await geocode_and_find_zone(address, semester, db)

    quotations = await get_quotations(zone.link_zona, semester, property_type, db)
    comparables = await get_comparables(zone.link_zona, zone.zone_code, db)

    if not quotations:
        raise ValueError(
            f"No quotation data for zone {zone.link_zona} in semester {semester} "
            f"for property type {property_type}"
        )

    # Group quotations by conservation state
    quotations_by_state: dict[str, dict] = {}
    for q in quotations:
        state = q.get("conservation_state", "SCONOSCIUTO")
        if state and q.get("price_min") and q.get("price_max"):
            quotations_by_state[state] = {
                "price_min": float(q["price_min"]),
                "price_max": float(q["price_max"]),
                "is_prevalent": q.get("is_prevalent", False),
                "surface_type_sale": q.get("surface_type_sale"),
            }

    # Select the base OMI range for the user-chosen conservation state
    selected_state = property_details.get("conservation_state", "NORMALE")
    base = quotations_by_state.get(selected_state)

    if not base:
        # Fallback: use prevalent, or first available state
        prevalent_state = next(
            (s for s, v in quotations_by_state.items() if v.get("is_prevalent")),
            None,
        )
        if prevalent_state:
            base = quotations_by_state[prevalent_state]
            selected_state = prevalent_state
        else:
            first_state = next(iter(quotations_by_state))
            base = quotations_by_state[first_state]
            selected_state = first_state

    # Apply correction coefficients
    details_for_engine = {k: v for k, v in property_details.items() if k != "conservation_state"}
    adjusted = compute_adjusted_estimate(
        omi_price_min=base["price_min"],
        omi_price_max=base["price_max"],
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
        "zone": {
            "link_zona": zone.link_zona,
            "zone_code": zone.zone_code,
            "fascia": zone.fascia,
            "municipality": zone.municipality_name,
            "description": zone.zone_description,
            "distance_m": zone.distance_m,
        },
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
        "comparables": comparables,
    }
