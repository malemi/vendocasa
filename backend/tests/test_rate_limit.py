"""Tests for backend/app/services/rate_limit.py and its wiring into /api/chat."""

from __future__ import annotations

import time

from app.config import settings
from app.services.rate_limit import InMemoryRateLimitStore, RateLimiter, get_client_ip

CHAT_BODY = {"messages": [{"role": "user", "content": "Ciao, valuta Via Roma 1 Milano"}]}


def test_per_minute_limit_returns_429(client, fake_anthropic, monkeypatch):
    fake_anthropic()
    monkeypatch.setattr(settings, "rate_limit_per_minute", 2)
    monkeypatch.setattr(settings, "rate_limit_per_day", 1000)
    monkeypatch.setattr(settings, "rate_limit_global_daily_model_calls", 1000)

    for _ in range(2):
        response = client.post("/api/chat", json=CHAT_BODY)
        assert response.status_code != 429

    response = client.post("/api/chat", json=CHAT_BODY)
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
        response = client.post("/api/chat", json=CHAT_BODY)
        assert response.status_code != 429

    response = client.post("/api/chat", json=CHAT_BODY)
    assert response.status_code == 429
    assert response.json()["detail"]["error"] == "rate_limited"


def test_global_ceiling_returns_503(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_per_minute", 1000)
    monkeypatch.setattr(settings, "rate_limit_per_day", 1000)
    monkeypatch.setattr(settings, "rate_limit_global_daily_model_calls", 0)

    response = client.post("/api/chat", json=CHAT_BODY)
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "service_unavailable"


def test_ip_fallback_survives_cookie_deletion():
    """Deleting the cookie must not reset the budget: the IP-keyed counter
    is independent of the uid-keyed one, and a fresh uid on the same IP is
    still blocked once the IP's own ceiling is hit.
    """
    limiter = RateLimiter(InMemoryRateLimitStore())  # fresh, isolated store
    limit_backup = settings.rate_limit_per_minute
    settings.rate_limit_per_minute = 2
    try:
        same_ip = "203.0.113.9"
        decisions = [limiter.check_identity(f"uid-{i}", same_ip) for i in range(3)]
    finally:
        settings.rate_limit_per_minute = limit_backup

    assert [d.allowed for d in decisions] == [True, True, False]
    assert decisions[-1].retry_after_seconds > 0


def test_store_sweeps_expired_windows(monkeypatch):
    """Attacker-chosen identities (a fresh uid per cookie-less request) grow
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
        self.headers = headers

        class _Client:
            host = client_host

        self.client = _Client()


def test_get_client_ip_prefers_envoy_header_over_forwarded_for():
    req = FakeRequest({
        "x-envoy-external-address": "198.51.100.9",
        "x-forwarded-for": "1.2.3.4, 10.0.0.2, 10.0.0.3",
    })
    assert get_client_ip(req) == "198.51.100.9"


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


def test_rotating_leftmost_xff_with_no_cookie_still_gets_limited(client, fake_anthropic, monkeypatch):
    """Reproduces the exploit from the integration review: a caller with no
    vendocasa_uid cookie (fresh uuid4 identity every request) that rotates
    the leftmost X-Forwarded-For entry must still be blocked, because the
    real identity comes from the rightmost (proxy-appended) hop, which the
    caller does not control.
    """
    fake_anthropic()
    monkeypatch.setattr(settings, "rate_limit_per_minute", 5)
    monkeypatch.setattr(settings, "rate_limit_per_day", 1000)
    monkeypatch.setattr(settings, "rate_limit_global_daily_model_calls", 1000)

    real_rightmost_ip = "203.0.113.42"
    statuses = []
    for i in range(6):
        client.cookies.clear()  # no vendocasa_uid cookie -> fresh uuid4 identity
        response = client.post(
            "/api/chat",
            json=CHAT_BODY,
            headers={"x-forwarded-for": f"10.10.10.{i}, {real_rightmost_ip}"},
        )
        statuses.append(response.status_code)

    assert statuses[:5] == [200] * 5
    assert statuses[5] == 429
