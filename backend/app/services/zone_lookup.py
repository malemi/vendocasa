"""PostGIS spatial queries for OMI zone lookup."""

import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class ZoneResult:
    link_zona: str
    zone_code: str
    fascia: str
    municipality_name: str
    zone_description: str
    distance_m: float | None = None


async def find_zone(
    lat: float, lng: float, semester: str, db: AsyncSession
) -> ZoneResult | None:
    """Find the OMI zone containing a point, with fallback to nearest within 200m."""

    # Exact match: point inside polygon
    result = await db.execute(
        text("""
            SELECT z.link_zona, z.zone_code, z.fascia, z.municipality_name,
                   z.zone_description
            FROM omi.zones z
            WHERE ST_Intersects(z.geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
              AND z.semester = :semester
            LIMIT 1
        """),
        {"lng": lng, "lat": lat, "semester": semester},
    )
    row = result.first()
    if row:
        return ZoneResult(
            link_zona=row.link_zona,
            zone_code=row.zone_code,
            fascia=row.fascia,
            municipality_name=row.municipality_name,
            zone_description=row.zone_description,
        )

    # Fallback: nearest zone within 200m
    result = await db.execute(
        text("""
            SELECT z.link_zona, z.zone_code, z.fascia, z.municipality_name,
                   z.zone_description,
                   ST_Distance(
                       z.geom::geography,
                       ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
                   ) as dist_m
            FROM omi.zones z
            WHERE z.semester = :semester
              AND ST_DWithin(
                  z.geom::geography,
                  ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                  200
              )
            ORDER BY dist_m
            LIMIT 1
        """),
        {"lng": lng, "lat": lat, "semester": semester},
    )
    row = result.first()
    if row:
        logger.info(
            f"No exact zone match for ({lat}, {lng}), using nearest at {row.dist_m:.0f}m"
        )
        return ZoneResult(
            link_zona=row.link_zona,
            zone_code=row.zone_code,
            fascia=row.fascia,
            municipality_name=row.municipality_name,
            zone_description=row.zone_description,
            distance_m=row.dist_m,
        )

    return None


async def get_latest_semester(db: AsyncSession) -> str | None:
    """Return the most recent semester available in the database."""
    result = await db.execute(
        text("SELECT DISTINCT semester FROM omi.zones ORDER BY semester DESC LIMIT 1")
    )
    row = result.first()
    return row[0] if row else None


async def get_all_semesters(db: AsyncSession) -> list[str]:
    """Return all available semesters, most recent first."""
    result = await db.execute(
        text("SELECT DISTINCT semester FROM omi.zones ORDER BY semester DESC")
    )
    return [row[0] for row in result]
