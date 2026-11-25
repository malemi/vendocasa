"""Exact money arithmetic for valuations.

PostgreSQL NUMERIC columns arrive as Decimal; request values arrive as float.
Valuation arithmetic converts both to Decimal (floats through their string
form, so 0.1 stays 0.1), and rounds to cents only when producing output.
NUMERIC can also hold NaN, so every conversion rejects non-finite values.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")


def to_decimal(value: object) -> Decimal | None:
    """A finite Decimal, or None for missing, malformed or non-finite values."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def money(value: Decimal, places: Decimal = CENT) -> float:
    """Round half up to `places` and return a JSON-friendly float."""
    return float(value.quantize(places, rounding=ROUND_HALF_UP))


def usable_range(price_min: object, price_max: object) -> tuple[Decimal, Decimal] | None:
    """The (min, max) EUR/m2 range if it is usable: finite, positive and ordered."""
    low, high = to_decimal(price_min), to_decimal(price_max)
    if low is None or high is None or low <= 0 or high <= 0 or low > high:
        return None
    return low, high


def jsonable(value: object) -> object:
    if isinstance(value, Decimal):
        return float(value) if value.is_finite() else None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def jsonable_rows(rows: list[dict]) -> list[dict]:
    """Database rows with Decimal and date values made JSON-friendly."""
    return [{key: jsonable(value) for key, value in row.items()} for row in rows]
