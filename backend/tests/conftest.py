"""Shared pytest fixtures.

Sets a dummy ANTHROPIC_API_KEY before anything imports app.config, since
Settings() is instantiated at module-import time and app.main now raises
at import time if the key is missing (see app/main.py).
"""

from __future__ import annotations

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-for-pytest")
# Identity configuration for tests: HS256 tokens signed with a test secret,
# issued by a fictitious project URL. Real deployments use the project's JWKS.
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_JWT_ALGORITHM", "HS256")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret-for-pytest-only-0123456789abcdef")
os.environ.setdefault("OWNER_USER_ID", "00000000-0000-4000-8000-00000000000a")

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.services import disposable_domains
from app.services.rate_limit import rate_limiter
from tests.fakes import FakeResponse, make_fake_anthropic_factory

TEST_DISPOSABLE_DOMAINS = {"mailinator.com", "yopmail.com"}


@pytest.fixture(autouse=True)
def _disposable_domains():
    """Tests use a fixed domain set instead of the database table."""
    disposable_domains.set_domains_for_tests(TEST_DISPOSABLE_DOMAINS)
    yield
    disposable_domains.set_domains_for_tests(TEST_DISPOSABLE_DOMAINS)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Every test starts with a clean rate-limit store.

    The limiter is a process-wide singleton (backend/app/services/rate_limit.py),
    so without this, state from one test would leak into the next.
    """
    rate_limiter._store._windows.clear()
    yield
    rate_limiter._store._windows.clear()


@pytest.fixture
def client():
    """A TestClient with the DB dependency stubbed out.

    None of the behavior under test (rate limiting, request validation, the
    tool-calling loop cap) touches the database, so the dependency is
    overridden rather than requiring a real Postgres instance in CI.
    """

    async def _fake_get_db():
        yield None

    app.dependency_overrides[get_db] = _fake_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def fake_anthropic(monkeypatch):
    """Replace AsyncAnthropic in agent.py with a no-network fake.

    Defaults to a single response that ends the turn immediately (no tool
    calls). Tests that need multi-round behavior can call
    `fake_anthropic(responses=[...])` before making a request.
    """

    def _install(responses=None):
        factory = make_fake_anthropic_factory(responses or [FakeResponse(content=[])])
        monkeypatch.setattr("app.services.agent.AsyncAnthropic", factory)
        return factory

    return _install
