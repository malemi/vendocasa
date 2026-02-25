import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.zone_lookup import find_zone, get_latest_semester

router = APIRouter()


@router.get("/api/zones/geojson")
async def zones_geojson(
    bbox: str | None = Query(None, description="Bounding box: min_lng,min_lat,max_lng,max_lat"),
    semester: str | None = Query(None, description="Semester"),
    db: AsyncSession = Depends(get_db),
):
    """Return zone polygons as GeoJSON FeatureCollection for map display."""
    if not semester:
        semester = await get_latest_semester(db)
        if not semester:
            raise HTTPException(404, "No data available")

    # Build query with optional bbox filter
    params = {"semester": semester}
    bbox_clause = ""
    if bbox:
        parts = bbox.split(",")
        if len(parts) == 4:
            params["min_lng"] = float(parts[0])
            params["min_lat"] = float(parts[1])
            params["max_lng"] = float(parts[2])
            params["max_lat"] = float(parts[3])
            bbox_clause = """
                AND z.geom && ST_MakeEnvelope(:min_lng, :min_lat, :max_lng, :max_lat, 4326)
            """

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

    result = await db.execute(
        text("""
            SELECT property_type_code, property_type_desc, conservation_state,
                   is_prevalent, price_min, price_max, surface_type_sale,
                   rent_min, rent_max, surface_type_rent
            FROM omi.quotations
            WHERE link_zona = :link_zona AND semester = :semester
            ORDER BY property_type_code, is_prevalent DESC
        """),
        {"link_zona": link_zona, "semester": semester},
    )
    return [dict(row._mapping) for row in result.all()]
