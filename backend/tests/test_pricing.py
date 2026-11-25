"""Cost arithmetic (backend/app/services/pricing.py)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import pricing

MODEL = "claude-sonnet-5-5"


def test_maximum_cost_prices_all_input_at_the_cache_write_rate():
    # 10,000 input tokens at $2.50/M = $0.025; 4,096 output at $10/M = $0.04096.
    assert pricing.max_call_cost_micro(MODEL, 10_000, 4_096) == 25_000 + 40_960


def test_actual_cost_sums_each_usage_category_at_its_rate():
    usage = SimpleNamespace(input_tokens=1_000, cache_creation_input_tokens=9_000,
                            cache_read_input_tokens=50_000, output_tokens=700)
    # 1,000*$2 + 9,000*$2.50 + 50,000*$0.10 + 700*$10, per million tokens.
    assert pricing.actual_call_cost_micro(MODEL, usage) == 2_000 + 22_500 + 5_000 + 7_000


def test_missing_usage_fields_count_as_zero():
    assert pricing.actual_call_cost_micro(MODEL, SimpleNamespace(input_tokens=10, output_tokens=None)) == 20


def test_amounts_round_up_to_the_next_micro_dollar():
    # 1 input token costs $0.000002 = 2 micro; 1 cache-read token costs $0.0000001,
    # which rounds up to 1 micro rather than down to 0.
    assert pricing.actual_call_cost_micro(MODEL, SimpleNamespace(cache_read_input_tokens=1)) == 1


def test_actual_cost_never_exceeds_the_maximum_for_the_same_call():
    for cached in (0, 4_000, 9_000):
        usage = SimpleNamespace(input_tokens=9_000 - cached, cache_creation_input_tokens=cached,
                                cache_read_input_tokens=0, output_tokens=4_096)
        assert pricing.actual_call_cost_micro(MODEL, usage) <= pricing.max_call_cost_micro(MODEL, 9_000, 4_096)


def test_an_unknown_model_cannot_be_priced():
    with pytest.raises(pricing.UnknownModelPrice):
        pricing.max_call_cost_micro("claude-sonnet-4-20250514", 10, 10)


def test_google_geocoding_request_price():
    assert pricing.google_geocoding_cost_micro() == 5_000
