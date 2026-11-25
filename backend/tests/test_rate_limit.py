"""Tests for backend/app/services/rate_limit.py and its wiring into /api/chat."""

from __future__ import annotations

import time

from starlette.datastructures import Headers

from app.config import settings
from app.refusals import REFUSAL_MESSAGES
from app.services.rate_limit import InMemoryRateLimitStore, RateLimiter, get_client_ip
from tests.auth_helpers import auth_headers

ACCOUNT = "22222222-2222-4222-8222-222222222222"

CHAT_BODY = {"messages": [{"role": "user", "content": "Ciao, valuta Via Roma 1 Milano"}]}


def test_per_minute_limit_returns_429(client, fake_anthropic, monkeypatch):
    fake_anthropic()
    monkeypatch.setattr(settings, "rate_limit_per_minute", 2)
    monkeypatch.setattr(settings, "rate_limit_per_day", 1000)
    monkeypatch.setattr(settings, "rate_limit_global_daily_model_calls", 1000)

    for _ in range(2):
        response = client.post("/api/chat", json=CHAT_BODY, headers=auth_headers(ACCOUNT))
        assert response.status_code != 429

    response = client.post("/api/chat", json=CHAT_BODY, headers=auth_headers(ACCOUNT))
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert response.json()["detail"]["error"] == "rate_limited"


def test_per_day_limit_returns_429(client, fake_anthropic, monkeypatch):
    fake_anthropic()
    # Minute ceiling kept high so only the daily ceiling can trigger.
    monkeypatch.setattr(settings, "rate_limit_per_minute", 1000)
    monkeypatch.setattr(settings, "rate_limit_per_day", 2)
    monkeypatch.setattr(settings, "rate_limit_global_daily_model_calls", 1000)

    for _ in range(2):
        response = client.post("/api/chat", json=CHAT_BODY, headers=auth_headers(ACCOUNT))
        assert response.status_code != 429

    response = client.post("/api/chat", json=CHAT_BODY, headers=auth_headers(ACCOUNT))
    assert response.status_code == 429
    assert response.json()["detail"]["error"] == "rate_limited"


def test_global_ceiling_returns_503(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_per_minute", 1000)
    monkeypatch.setattr(settings, "rate_limit_per_day", 1000)
    monkeypatch.setattr(settings, "rate_limit_global_daily_model_calls", 0)

    response = client.post("/api/chat", json=CHAT_BODY, headers=auth_headers(ACCOUNT))
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "daily_limit"
    assert response.json()["detail"]["message"] == REFUSAL_MESSAGES["daily_limit"]


def test_ip_limit_survives_switching_accounts():
    """Switching accounts must not reset the budget: the IP-keyed counter is
    independent of the account-keyed one, and a different account on the
    same IP is still blocked once the IP's own ceiling is hit.
    """
    limiter = RateLimiter(InMemoryRateLimitStore())  # fresh, isolated store
    limit_backup = settings.rate_limit_per_minute
    settings.rate_limit_per_minute = 2
    try:
        same_ip = "203.0.113.9"
        decisions = [limiter.check_identity(f"account-{i}", same_ip) for i in range(3)]
    finally:
        settings.rate_limit_per_minute = limit_backup

    assert [d.allowed for d in decisions] == [True, True, False]
    assert decisions[-1].retry_after_seconds > 0


def test_store_sweeps_expired_windows(monkeypatch):
    """Many identities (accounts and client addresses) grow
    the store forever unless expired windows are swept -- verify `hit`
    actually purges them instead of leaking memory indefinitely.
    """
    store = InMemoryRateLimitStore()
    monkeypatch.setattr(InMemoryRateLimitStore, "_SWEEP_EVERY", 2)

    long_expired = time.time() - 1_000_000
    store._windows["stale-1"] = (long_expired, 5, 60)
    store._windows["stale-2"] = (long_expired, 5, 60)
    assert len(store._windows) == 2

    # _SWEEP_EVERY=2: the second hit below triggers a sweep.
    store.hit("fresh-1", 60, 100)
    store.hit("fresh-2", 60, 100)

    assert "stale-1" not in store._windows
    assert "stale-2" not in store._windows


class FakeRequest:
    def __init__(self, headers, client_host="10.0.0.1"):
        # Real Starlette Headers, so the fake carries the same API the code
        # uses (get AND getlist) and duplicate header lines behave as on the
        # wire. Accepts the tests' plain dicts unchanged.
        self.headers = Headers(headers=headers)

        class _Client:
            host = client_host

        self.client = _Client()


def test_get_client_ip_ignores_x_envoy_external_address_entirely():
    """X-Envoy-External-Address is not in the trust chain: its safety would
    rest on an unproven assumption about Railway's edge, and a forged one
    alone reopens the bypass whenever XFF is absent. The rightmost XFF hop
    wins even when an Envoy header is also present.
    """
    req = FakeRequest({
        "x-envoy-external-address": "198.51.100.9",
        "x-forwarded-for": "1.2.3.4, 10.0.0.2, 203.0.113.55",
    })
    assert get_client_ip(req) == "203.0.113.55"


def test_get_client_ip_ignores_envoy_header_when_xff_absent():
    """With no X-Forwarded-For, a forged Envoy header must not be trusted
    either -- fall back to request.client.host, not the header value.
    """
    req = FakeRequest({"x-envoy-external-address": "198.51.100.9"}, client_host="10.0.0.1")
    assert get_client_ip(req) == "10.0.0.1"


def test_get_client_ip_ignores_caller_supplied_leftmost_hop():
    """The leftmost X-Forwarded-For entry is whatever the caller typed --
    it must never be trusted. Only the rightmost (proxy-appended) entry is.
    """
    req = FakeRequest({"x-forwarded-for": "9.9.9.9, 10.0.0.2, 203.0.113.7"})
    assert get_client_ip(req) == "203.0.113.7"

    # A caller sending a completely different fake leftmost value each time
    # must still resolve to the same (real, rightmost) address.
    req2 = FakeRequest({"x-forwarded-for": "1.1.1.1, 10.0.0.2, 203.0.113.7"})
    assert get_client_ip(req2) == get_client_ip(req) == "203.0.113.7"


def test_get_client_ip_falls_back_to_request_client_host():
    req = FakeRequest({})
    assert get_client_ip(req) == "10.0.0.1"


def test_rotating_leftmost_xff_with_fresh_accounts_still_gets_limited(client, fake_anthropic, monkeypatch):
    """Reproduces the exploit from the integration review: a caller with a
    fresh account for every request that rotates the leftmost
    X-Forwarded-For entry must still be blocked, because the IP identity
    comes from the rightmost (proxy-appended) hop, which the caller does not
    control.
    """
    fake_anthropic()
    monkeypatch.setattr(settings, "rate_limit_per_minute", 5)
    monkeypatch.setattr(settings, "rate_limit_per_day", 1000)
    monkeypatch.setattr(settings, "rate_limit_global_daily_model_calls", 1000)

    real_rightmost_ip = "203.0.113.42"
    statuses = []
    for i in range(6):
        response = client.post(
            "/api/chat",
            json=CHAT_BODY,
            headers={**auth_headers(), "x-forwarded-for": f"10.10.10.{i}, {real_rightmost_ip}"},
        )
        statuses.append(response.status_code)

    assert statuses[:5] == [200] * 5
    assert statuses[5] == 429


def test_forged_envoy_header_with_xff_present_still_gets_limited(client, fake_anthropic, monkeypatch):
    """A forged, rotated X-Envoy-External-Address must not override the
    rightmost XFF hop -- the header carries no trust at all, with or
    without XFF alongside it.
    """
    fake_anthropic()
    monkeypatch.setattr(settings, "rate_limit_per_minute", 5)
    monkeypatch.setattr(settings, "rate_limit_per_day", 1000)
    monkeypatch.setattr(settings, "rate_limit_global_daily_model_calls", 1000)

    real_rightmost_ip = "203.0.113.99"
    statuses = []
    for i in range(6):
        response = client.post(
            "/api/chat",
            json=CHAT_BODY,
            headers={
                **auth_headers(),
                "x-forwarded-for": f"10.10.10.{i}, {real_rightmost_ip}",
                "x-envoy-external-address": f"198.51.100.{i}",  # rotated, forged
            },
        )
        statuses.append(response.status_code)

    assert statuses[:5] == [200] * 5
    assert statuses[5] == 429


def test_forged_envoy_header_without_xff_does_not_bypass(client, fake_anthropic, monkeypatch):
    """With XFF absent, a rotated forged Envoy header must not mint a new
    identity per request either: the header is never trusted, so every
    request falls back to request.client.host (constant for TestClient).
    """
    fake_anthropic()
    monkeypatch.setattr(settings, "rate_limit_per_minute", 5)
    monkeypatch.setattr(settings, "rate_limit_per_day", 1000)
    monkeypatch.setattr(settings, "rate_limit_global_daily_model_calls", 1000)

    statuses = []
    for i in range(6):
        response = client.post(
            "/api/chat",
            json=CHAT_BODY,
            headers={**auth_headers(), "x-envoy-external-address": f"198.51.100.{i}"},  # rotated, forged, no XFF
        )
        statuses.append(response.status_code)

    assert statuses[:5] == [200] * 5
    assert statuses[5] == 429
