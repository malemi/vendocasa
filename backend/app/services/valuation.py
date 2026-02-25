"""Valuation service: combines geocoding, zone lookup, and quotation retrieval."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.geocoder import GeoResult, geocoder
from app.services.zone_lookup import ZoneResult, find_zone, get_latest_semester


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
    # 1. Geocode
    coords = await geocoder.geocode(address, db)
    if not coords:
        raise ValueError(f"Address not found: {address}")

    # 2. Determine semester
    if not semester:
        semester = await get_latest_semester(db)
        if not semester:
            raise ValueError("No data available in the database")

    # 3. Find zone
    zone = await find_zone(coords.lat, coords.lng, semester, db)
    if not zone:
        raise ValueError(f"No OMI zone found for coordinates ({coords.lat}, {coords.lng})")

    # 4. Get quotations
    quot_result = await db.execute(
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
        {"link_zona": zone.link_zona, "semester": semester, "ptype": property_type},
    )
    quotations = [dict(row._mapping) for row in quot_result.all()]

    # 5. Get comparables
    comp_result = await db.execute(
        text("""
            SELECT transaction_date, declared_price, cadastral_category,
                   cadastral_vani, cadastral_mq, notes
            FROM omi.transactions
            WHERE link_zona = :link_zona
               OR omi_zone = :zone_code
            ORDER BY transaction_date DESC
            LIMIT 20
        """),
        {"link_zona": zone.link_zona, "zone_code": zone.zone_code},
    )
    comparables = [dict(row._mapping) for row in comp_result.all()]

    # 6. Compute estimate from prevalent quotation
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
