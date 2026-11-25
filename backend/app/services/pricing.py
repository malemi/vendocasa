"""Provider prices and the cost of a call, in integer micro-dollars.

Amounts are rounded up to the next micro-dollar, so recorded spending is never
below the provider's charge for the same usage. A model missing from the table
cannot be charged for, and paid calls refuse (see spending.reserve).

Prices are per million tokens, from the Claude API model catalog bundled with
Claude Code (cached 2026-11-03): claude-sonnet-5-5 costs $2 input, $2.50 for a
five-minute cache write, $0.10 for a cache read and $10 output. Changing a price
means changing PRICE_TABLE_VERSION, which the ledger records with every charge.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

PRICE_TABLE_VERSION = "2026-11-25"
MICRO_PER_USD = 1_000_000
_PER_MILLION = Decimal(1_000_000)


@dataclass(frozen=True)
class ModelPrices:
    """US dollars per million tokens."""

    input: Decimal
    cache_write: Decimal  # five-minute cache write, the highest input rate
    cache_read: Decimal
    output: Decimal


MODEL_PRICES: dict[str, ModelPrices] = {
    "claude-sonnet-5-5": ModelPrices(
        input=Decimal("2"),
        cache_write=Decimal("2.50"),
        cache_read=Decimal("0.10"),
        output=Decimal("10"),
    ),
}

# Google Geocoding API, one request. Conservative: it ignores any free monthly
# allowance. Confirm against Google's current price list before relying on it.
GOOGLE_GEOCODING_REQUEST_USD = Decimal("0.005")


class UnknownModelPrice(LookupError):
    pass


def usd_to_micro(amount: Decimal) -> int:
    """Convert dollars to micro-dollars, rounding up."""
    return math.ceil(amount * MICRO_PER_USD)


def prices_for(model: str) -> ModelPrices:
    try:
        return MODEL_PRICES[model]
    except KeyError as exc:
        raise UnknownModelPrice(model) from exc


def max_call_cost_micro(model: str, input_tokens: int, max_output_tokens: int) -> int:
    """The most a call can cost: every input token at the cache-write rate,
    plus the full output allowance (thinking counts toward it)."""
    p = prices_for(model)
    usd = (Decimal(input_tokens) * p.cache_write + Decimal(max_output_tokens) * p.output) / _PER_MILLION
    return usd_to_micro(usd)


def actual_call_cost_micro(model: str, usage: object) -> int:
    """The cost of a completed call from its `usage` (an SDK Usage object)."""
    p = prices_for(model)

    def tokens(field: str) -> Decimal:
        value = getattr(usage, field, None)
        return Decimal(value or 0)

    usd = (
        tokens("input_tokens") * p.input
        + tokens("cache_creation_input_tokens") * p.cache_write
        + tokens("cache_read_input_tokens") * p.cache_read
        + tokens("output_tokens") * p.output
    ) / _PER_MILLION
    return usd_to_micro(usd)


def google_geocoding_cost_micro() -> int:
    return usd_to_micro(GOOGLE_GEOCODING_REQUEST_USD)
