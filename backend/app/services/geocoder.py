"""Geocoding service for Italian addresses.

Uses Photon (Elasticsearch-based, fuzzy matching) as primary geocoder,
with Nominatim and Google as fallbacks.
"""

import asyncio
import logging
from dataclasses import dataclass

from geopy.geocoders import GoogleV3, Nominatim, Photon
from geopy.extra.rate_limiter import RateLimiter

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class GeoResult:
    lat: float
    lng: float
    source: str


def _address_variations(address: str) -> list[str]:
    """Generate address variations for fallback attempts.

    Photon handles fuzzy matching natively, so we only need minimal
    variations — the original and one with ", Italy" to help disambiguation.
    """
    variations = [address]

    if "italy" not in address.lower() and "italia" not in address.lower():
        variations.append(f"{address}, Italy")

    return variations


class ItalianGeocoder:
    def __init__(self):
        self.photon = Photon(user_agent="vendocasa_personal/1.0", timeout=10)
        self._geocode_photon = RateLimiter(self.photon.geocode, min_delay_seconds=0.5)

        self.nominatim = Nominatim(user_agent="vendocasa_personal/1.0", timeout=10)
        self._geocode_nom = RateLimiter(self.nominatim.geocode, min_delay_seconds=1.0)

        self.google = (
            GoogleV3(api_key=settings.google_geocoding_api_key)
            if settings.google_geocoding_api_key
            else None
        )

    async def geocode(self, address: str) -> GeoResult | None:
        """Geocode an address using Photon (primary), Nominatim and Google (fallbacks)."""
        variations = _address_variations(address)

        # 1. Try Photon (fuzzy Elasticsearch-based, handles Italian addresses well)
        for variant in variations:
            result = await self._try_photon(variant)
            if result:
                if variant != address:
                    logger.info("Photon resolved '%s' via variant '%s'", address, variant)
                return result

        # 2. Fallback to Nominatim
        for variant in variations:
            result = await self._try_nominatim(variant)
            if result:
                logger.info("Nominatim fallback resolved '%s' (variant: '%s')", address, variant)
                return result

        # 3. Fallback to Google (if configured)
        if self.google:
            for variant in variations:
                result = await self._try_google(variant)
                if result:
                    logger.info("Google fallback resolved '%s' (variant: '%s')", address, variant)
                    return result

        logger.warning("All geocoding attempts failed for '%s'", address)
        return None

    async def _try_photon(self, address: str) -> GeoResult | None:
        try:
            loc = await asyncio.to_thread(
                self._geocode_photon, address
            )
            if loc:
                logger.info("Photon geocoded '%s' -> (%s, %s)", address, loc.latitude, loc.longitude)
                return GeoResult(lat=loc.latitude, lng=loc.longitude, source="photon")
        except Exception as e:
            logger.warning("Photon failed for '%s': %s", address, e)
        return None

    async def _try_nominatim(self, address: str) -> GeoResult | None:
        try:
            loc = await asyncio.to_thread(
                self._geocode_nom, address, country_codes="it"
            )
            if loc:
                logger.info("Nominatim geocoded '%s' -> (%s, %s)", address, loc.latitude, loc.longitude)
                return GeoResult(lat=loc.latitude, lng=loc.longitude, source="nominatim")
        except Exception as e:
            logger.warning("Nominatim failed for '%s': %s", address, e)
        return None

    async def _try_google(self, address: str) -> GeoResult | None:
        try:
            loc = await asyncio.to_thread(
                self.google.geocode, address, region="it"
            )
            if loc:
                logger.info("Google geocoded '%s' -> (%s, %s)", address, loc.latitude, loc.longitude)
                return GeoResult(lat=loc.latitude, lng=loc.longitude, source="google")
        except Exception as e:
            logger.warning("Google failed for '%s': %s", address, e)
        return None


# Singleton
geocoder = ItalianGeocoder()
