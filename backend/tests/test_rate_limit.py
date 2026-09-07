"""Tests for backend/app/services/rate_limit.py and its wiring into /api/chat."""

from __future__ import annotations

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


def test_get_client_ip_prefers_leftmost_x_forwarded_for():
    class FakeRequest:
        def __init__(self, headers, client_host="10.0.0.1"):
            self.headers = headers

            class _Client:
                host = client_host

            self.client = _Client()

    req = FakeRequest({"x-forwarded-for": "198.51.100.5, 10.0.0.2, 10.0.0.3"})
    assert get_client_ip(req) == "198.51.100.5"

    req_no_header = FakeRequest({})
    assert get_client_ip(req_no_header) == "10.0.0.1"
