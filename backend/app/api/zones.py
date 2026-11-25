import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.zone_lookup import find_zone, get_latest_semester, semester_is_complete

router = APIRouter()

GEOJSON_MAX_ZONES = 500
QUOTATIONS_MAX_ROWS = 200


@router.get("/api/zones/geojson")
# TODO: add response_model when a matching output schema is defined
async def zones_geojson(
    bbox: str = Query(..., description="Bounding box: min_lng,min_lat,max_lng,max_lat"),
    semester: str | None = Query(None, description="Semester"),
    db: AsyncSession = Depends(get_db),
):
    """Return zone polygons as GeoJSON FeatureCollection for map display."""
    if not semester:
        semester = await get_latest_semester(db)
        if not semester:
            raise HTTPException(404, "No data available")
    elif not await semester_is_complete(semester, db):
        raise HTTPException(404, f"Semester {semester} is not available")

    # A bounding box is required, and the response is capped at GEOJSON_MAX_ZONES
    # zones: the whole country in one response would be tens of megabytes.
    params = {"semester": semester, "limit": GEOJSON_MAX_ZONES}
    bbox_clause = ""
    if bbox:
        try:
            parts = bbox.split(",")
            if len(parts) != 4:
                raise ValueError("bbox must have 4 comma-separated values")
            min_lng, min_lat, max_lng, max_lat = [float(p) for p in parts]
            if not (min_lng < max_lng and min_lat < max_lat):
                raise ValueError("min values must be less than max values")
            params["min_lng"] = min_lng
            params["min_lat"] = min_lat
            params["max_lng"] = max_lng
            params["max_lat"] = max_lat
            bbox_clause = """
                AND z.geom && ST_MakeEnvelope(:min_lng, :min_lat, :max_lng, :max_lat, 4326)
            """
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid bbox parameter: {e}")

    result = await db.execute(
        text(f"""
            SELECT z.link_zona, z.zone_code, z.fascia, z.municipality_name,
                   z.zone_description,
                   ST_AsGeoJSON(z.geom) as geojson,
                   q.price_min as avg_price_min,
                   q.price_max as avg_price_max
            FROM omi.zones z
            LEFT JOIN LATERAL (
                SELECT price_min, price_max
                FROM omi.quotations
                WHERE link_zona = z.link_zona
                  AND semester = z.semester
                  AND property_type_code = 20
                  AND is_prevalent = true
                LIMIT 1
            ) q ON true
            WHERE z.semester = :semester
            {bbox_clause}
            ORDER BY z.link_zona
            LIMIT :limit
        """),
        params,
    )

    features = []
    for row in result.all():
        geom = json.loads(row.geojson)
        feature = {
            "type": "Feature",
            "geometry": geom,
            "properties": {
                "link_zona": row.link_zona,
                "zone_code": row.zone_code,
                "fascia": row.fascia,
                "municipality": row.municipality_name,
                "description": row.zone_description,
                "price_min": float(row.avg_price_min) if row.avg_price_min else None,
                "price_max": float(row.avg_price_max) if row.avg_price_max else None,
            },
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.get("/api/zones/by-coordinates")
# TODO: add response_model when a matching output schema is defined
async def zone_by_coordinates(
    lat: float = Query(...),
    lng: float = Query(...),
    semester: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Look up the OMI zone for a specific lat/lng point."""
    if not semester:
        semester = await get_latest_semester(db)
        if not semester:
            raise HTTPException(404, "No data available")
    elif not await semester_is_complete(semester, db):
        raise HTTPException(404, f"Semester {semester} is not available")

    zone = await find_zone(lat, lng, semester, db)
    if not zone:
        raise HTTPException(404, "No OMI zone found for this location")

    return {
        "link_zona": zone.link_zona,
        "zone_code": zone.zone_code,
        "fascia": zone.fascia,
        "municipality": zone.municipality_name,
        "description": zone.zone_description,
        "distance_m": zone.distance_m,
        "semester": semester,
    }


@router.get("/api/quotations")
# TODO: add response_model when a matching output schema is defined
async def get_quotations(
    link_zona: str = Query(...),
    semester: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get all quotations for a specific zone."""
    if not semester:
        semester = await get_latest_semester(db)
        if not semester:
            raise HTTPException(404, "No data available")
    elif not await semester_is_complete(semester, db):
        raise HTTPException(404, f"Semester {semester} is not available")

    result = await db.execute(
        text("""
            SELECT property_type_code, property_type_desc, conservation_state,
                   is_prevalent, price_min, price_max, surface_type_sale,
                   rent_min, rent_max, surface_type_rent
            FROM omi.quotations
            WHERE link_zona = :link_zona AND semester = :semester
            ORDER BY property_type_code, is_prevalent DESC
            LIMIT :limit
        """),
        {"link_zona": link_zona, "semester": semester, "limit": QUOTATIONS_MAX_ROWS},
    )
    return [dict(row._mapping) for row in result.all()]
