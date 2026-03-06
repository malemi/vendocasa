"""Geocoding service with smart retry for Italian addresses.

Tries Nominatim first, then Google as fallback.
If the original address fails, retries with variations:
  1. Original: "Via Sottocorno 17, Milano"
  2. Without civic number: "Via Sottocorno, Milano"
  3. Street keyword + city: "Sottocorno, Milano"
"""

import asyncio
import logging
import re
from dataclasses import dataclass

from geopy.geocoders import GoogleV3, Nominatim
from geopy.extra.rate_limiter import RateLimiter

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class GeoResult:
    lat: float
    lng: float
    source: str


# Regex to strip civic numbers: "Via Roma 17" -> "Via Roma", "Via Roma, 17/A" -> "Via Roma"
_CIVIC_RE = re.compile(r",?\s*\d+[/\w]*\s*(?=,|$)")
# Regex to strip Italian street prefixes: Via, Viale, Corso, Piazza, etc.
_PREFIX_RE = re.compile(
    r"^(via|viale|v\.le|corso|c\.so|piazza|p\.za|piazzale|p\.le|vicolo|"
    r"largo|lungarno|lungotevere|strada|stradone|borgata|borgo|contrada|"
    r"salita|discesa|traversa|rampa|galleria|passaggio)\s+",
    re.IGNORECASE,
)


def _address_variations(address: str) -> list[str]:
    """Generate progressively relaxed address variations.

    Given "Via Sottocorno 17, Milano" produces:
      1. "Via Sottocorno 17, Milano"       (original)
      2. "Via Sottocorno, Milano"           (no civic)
      3. "Sottocorno, Milano"              (no prefix, no civic)
    """
    variations = [address]

    # Strip civic number
    no_civic = _CIVIC_RE.sub("", address).strip().rstrip(",").strip()
    if no_civic != address:
        variations.append(no_civic)

    # Strip street prefix (from the no-civic version)
    base = no_civic if no_civic != address else address
    no_prefix = _PREFIX_RE.sub("", base).strip()
    if no_prefix != base:
        variations.append(no_prefix)

    return variations


class ItalianGeocoder:
    def __init__(self):
        self.nominatim = Nominatim(user_agent="vendocasa_personal/1.0", timeout=10)
        self._geocode_nom = RateLimiter(self.nominatim.geocode, min_delay_seconds=1.0)
        self.google = (
            GoogleV3(api_key=settings.google_geocoding_api_key)
            if settings.google_geocoding_api_key
            else None
        )

    async def geocode(self, address: str) -> GeoResult | None:
        """Geocode an address, trying variations if the original fails."""
        variations = _address_variations(address)

        for variant in variations:
            result = await self._try_nominatim(variant)
            if result:
                if variant != address:
                    logger.info("Original '%s' failed, resolved via variant '%s'", address, variant)
                return result

            if self.google:
                result = await self._try_google(variant)
                if result:
                    if variant != address:
                        logger.info("Original '%s' failed, resolved via variant '%s'", address, variant)
                    return result

        logger.warning("All geocoding attempts failed for '%s' (tried %d variations)", address, len(variations))
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
