"""Geocoding service with Nominatim primary and Google fallback.

Includes a database cache for permanent storage of results.
"""

import asyncio
import logging
from dataclasses import dataclass

from geopy.geocoders import GoogleV3, Nominatim
from geopy.extra.rate_limiter import RateLimiter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class GeoResult:
    lat: float
    lng: float
    source: str


class ItalianGeocoder:
    def __init__(self):
        self.nominatim = Nominatim(user_agent="vendocasa_personal/1.0", timeout=10)
        self._geocode_nom = RateLimiter(self.nominatim.geocode, min_delay_seconds=1.0)
        self.google = (
            GoogleV3(api_key=settings.google_geocoding_api_key)
            if settings.google_geocoding_api_key
            else None
        )

    async def geocode(self, address: str, db: AsyncSession) -> GeoResult | None:
        """Geocode an address, checking cache first."""
        # 1. Check DB cache
        cached = await self._get_cached(address, db)
        if cached:
            return cached

        # 2. Try Nominatim (run sync geocoder in thread)
        result = await self._try_nominatim(address)
        if result:
            await self._save_cache(address, result, db)
            return result

        # 3. Fallback to Google
        if self.google:
            result = await self._try_google(address)
            if result:
                await self._save_cache(address, result, db)
                return result

        return None

    async def _get_cached(self, address: str, db: AsyncSession) -> GeoResult | None:
        result = await db.execute(
            text("SELECT lat, lng, source FROM omi.geocode_cache WHERE address = :addr"),
            {"addr": address},
        )
        row = result.first()
        if row:
            return GeoResult(lat=row.lat, lng=row.lng, source=row.source)
        return None

    async def _save_cache(self, address: str, result: GeoResult, db: AsyncSession):
        await db.execute(
            text("""
                INSERT INTO omi.geocode_cache (address, lat, lng, source)
                VALUES (:addr, :lat, :lng, :source)
                ON CONFLICT (address) DO NOTHING
            """),
            {"addr": address, "lat": result.lat, "lng": result.lng, "source": result.source},
        )
        await db.commit()

    async def _try_nominatim(self, address: str) -> GeoResult | None:
        try:
            loc = await asyncio.to_thread(
                self._geocode_nom, address, country_codes="it"
            )
            if loc:
                logger.info(f"Nominatim geocoded '{address}' -> ({loc.latitude}, {loc.longitude})")
                return GeoResult(lat=loc.latitude, lng=loc.longitude, source="nominatim")
        except Exception as e:
            logger.warning(f"Nominatim failed for '{address}': {e}")
        return None

    async def _try_google(self, address: str) -> GeoResult | None:
        try:
            loc = await asyncio.to_thread(
                self.google.geocode, address, region="it"
            )
            if loc:
                logger.info(f"Google geocoded '{address}' -> ({loc.latitude}, {loc.longitude})")
                return GeoResult(lat=loc.latitude, lng=loc.longitude, source="google")
        except Exception as e:
            logger.warning(f"Google failed for '{address}': {e}")
        return None


# Singleton
geocoder = ItalianGeocoder()
