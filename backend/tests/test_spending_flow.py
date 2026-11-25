"""Spending caps, bounds and quotas wired into the routes and the agent loop.

The ledger is the in-memory FakeLedger (tests/fakes.py); its transactional
behavior on PostgreSQL is in tests/integration/test_spend_ledger.py.
"""

from __future__ import annotations

import logging
import time
from types import SimpleNamespace

import pytest

from app.api import chat as chat_api
from app.config import settings
from app.database import get_db
from app.main import app
from app.refusals import REFUSAL_MESSAGES
from app.services import document_store, pricing, spending
from app.services.agent import run_agent_stream
from app.services.geocoder import ItalianGeocoder
from tests.auth_helpers import OWNER_ID, auth_headers
from tests.fakes import FakeResponse, FakeToolUseBlock, FakeUsage, make_fake_anthropic_factory, make_raising_anthropic_factory

MODEL = "claude-sonnet-5-5"
ACCOUNT = "33333333-3333-4333-8333-333333333333"
CHAT = {"messages": [{"role": "user", "content": "Valuta Via Roma 1, Milano"}]}


async def _collect(generator):
    return [chunk async for chunk in generator]


def _install(monkeypatch, responses):
    factory = make_fake_anthropic_factory(responses)
    monkeypatch.setattr("app.services.agent.AsyncAnthropic", factory)
    return factory


# --- The agent loop ---------------------------------------------------------

@pytest.mark.asyncio
async def test_each_round_is_reserved_at_its_maximum_and_settled_at_its_actual_cost(monkeypatch, ledger):
    usage = FakeUsage(input_tokens=800, output_tokens=150, cache_creation_input_tokens=200, cache_read_input_tokens=0)
    tool_round = FakeResponse(content=[FakeToolUseBlock(id="t1", name="not_a_real_tool", input={})], usage=usage)
    final = FakeResponse(content=[], usage=usage)
    factory = _install(monkeypatch, [tool_round, final])

    await _collect(run_agent_stream(CHAT["messages"], db=None, account_id=ACCOUNT))

    assert len(factory.instance.messages.calls) == 2
    assert len(factory.instance.messages.counted) == 2  # counted before every round
    expected_max = pricing.max_call_cost_micro(MODEL, 1_000, settings.agent_max_tokens)
    expected_actual = pricing.actual_call_cost_micro(MODEL, usage)
    assert ledger.settlements == [("r1", expected_actual), ("r2", expected_actual)]
    assert ledger.spent[ACCOUNT] == 2 * expected_actual
    assert ledger.reserved[ACCOUNT] == 0
    assert expected_actual < expected_max


@pytest.mark.asyncio
async def test_a_provider_error_settles_the_full_reservation(monkeypatch, ledger):
    monkeypatch.setattr("app.services.agent.AsyncAnthropic", make_raising_anthropic_factory(RuntimeError("boom")))
    events = await _collect(run_agent_stream(CHAT["messages"], db=None, account_id=ACCOUNT))
    assert ledger.settlements == [("r1", None)]
    assert ledger.spent[ACCOUNT] == pricing.max_call_cost_micro(MODEL, 1_000, settings.agent_max_tokens)
    assert any('"error": "assistant_unavailable"' in e for e in events)


class _OneDeltaStream:
    """A stream that emits one text delta, then would wait forever."""

    def __init__(self):
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        self.closed = True
        return False

    def __aiter__(self):
        async def events():
            yield SimpleNamespace(type="content_block_delta", delta=SimpleNamespace(text="Ciao"))
            raise AssertionError("the consumer should have stopped reading")

        return events()


@pytest.mark.asyncio
async def test_a_cancelled_stream_settles_the_full_reservation_and_closes(monkeypatch, ledger):
    factory = _install(monkeypatch, [FakeResponse(content=[])])
    stream = _OneDeltaStream()
    monkeypatch.setattr(factory.instance.messages, "stream", lambda **kwargs: stream)

    generator = run_agent_stream(CHAT["messages"], db=None, account_id=ACCOUNT)
    first = await generator.__anext__()
    assert first.startswith("event: text_delta")
    await generator.aclose()  # the client went away

    assert stream.closed
    assert ledger.settlements == [("r1", None)]


@pytest.mark.asyncio
async def test_the_account_cap_stops_a_conversation_mid_stream(monkeypatch, ledger):
    per_round = pricing.max_call_cost_micro(MODEL, 1_000, settings.agent_max_tokens)
    ledger.account_cap = per_round + 1  # room for one round only
    tool_round = FakeResponse(content=[FakeToolUseBlock(id="t1", name="not_a_real_tool", input={})],
                              usage=FakeUsage(input_tokens=1_000, output_tokens=settings.agent_max_tokens))
    factory = _install(monkeypatch, [tool_round])

    events = await _collect(run_agent_stream(CHAT["messages"], db=None, account_id=ACCOUNT))

    assert len(factory.instance.messages.calls) == 1
    errors = [e for e in events if e.startswith("event: error")]
    assert len(errors) == 1 and '"error": "account_limit"' in errors[0]
    assert events[-1].startswith("event: done")


@pytest.mark.asyncio
async def test_a_model_refusal_is_shown_in_italian(monkeypatch, ledger):
    _install(monkeypatch, [FakeResponse(content=[], stop_reason="refusal")])
    events = await _collect(run_agent_stream(CHAT["messages"], db=None, account_id=ACCOUNT))
    assert any('"error": "model_refusal"' in e for e in events)
    assert REFUSAL_MESSAGES["model_refusal"] in "".join(events)


@pytest.mark.asyncio
async def test_the_client_has_no_retries_a_timeout_and_cache_breakpoints(monkeypatch, ledger):
    factory = _install(monkeypatch, [FakeResponse(content=[])])
    await _collect(run_agent_stream(CHAT["messages"], db=None, account_id=ACCOUNT))
    assert factory.instance.init_kwargs["max_retries"] == 0
    assert factory.instance.init_kwargs["timeout"] == settings.agent_call_timeout_seconds
    call = factory.instance.messages.calls[0]
    assert call["system"][-1]["cache_control"] == {"type": "ephemeral"}
    assert call["cache_control"] == {"type": "ephemeral"}


# --- The chat route -------------------------------------------------------------

@pytest.mark.parametrize(
    ("setup", "status", "code"),
    [
        (lambda l: setattr(l, "account_cap", 0), 429, "account_limit"),
        (lambda l: setattr(l, "global_cap", 0), 503, "global_limit"),
        (lambda l: setattr(l, "enabled", False), 503, "paused"),
    ],
)
def test_chat_refuses_before_streaming_when_nothing_can_be_reserved(client, fake_anthropic, ledger, setup, status, code):
    factory = fake_anthropic()
    setup(ledger)
    response = client.post("/api/chat", json=CHAT, headers=auth_headers(ACCOUNT))
    assert response.status_code == status
    assert response.json()["detail"] == {"error": code, "message": REFUSAL_MESSAGES[code]}
    assert factory.instance.messages.calls == []


def test_a_second_concurrent_chat_is_refused(client, fake_anthropic):
    fake_anthropic()
    chat_api._active_streams[ACCOUNT] = time.monotonic()  # a stream in progress
    refused = client.post("/api/chat", json=CHAT, headers=auth_headers(ACCOUNT))
    assert refused.status_code == 429
    assert refused.json()["detail"]["error"] == "concurrent"
    # Another account is unaffected, and finished streams release their slot.
    other = "44444444-4444-4444-8444-444444444444"
    assert client.post("/api/chat", json=CHAT, headers=auth_headers(other)).status_code == 200
    assert client.post("/api/chat", json=CHAT, headers=auth_headers(other)).status_code == 200
    assert other not in chat_api._active_streams


def test_a_stale_stream_entry_does_not_lock_the_account(client, fake_anthropic):
    fake_anthropic()
    chat_api._active_streams[ACCOUNT] = time.monotonic() - chat_api._MAX_STREAM_SECONDS - 1
    assert client.post("/api/chat", json=CHAT, headers=auth_headers(ACCOUNT)).status_code == 200


# --- Google geocoding -------------------------------------------------------------

class _FakeGoogle:
    def __init__(self, found=True):
        self.calls = 0
        self.found = found

    def geocode(self, address, region=None):
        self.calls += 1
        return SimpleNamespace(latitude=45.46, longitude=9.19) if self.found else None


def _google_only_geocoder(fake):
    geocoder = ItalianGeocoder.__new__(ItalianGeocoder)
    geocoder.google = fake
    return geocoder


@pytest.mark.asyncio
async def test_each_google_request_is_reserved_and_settled_at_its_price(ledger):
    fake = _FakeGoogle(found=False)
    token = spending.charged_account.set(ACCOUNT)
    try:
        assert await _google_only_geocoder(fake)._try_google("Via Inesistente 1") is None
    finally:
        spending.charged_account.reset(token)
    price = pricing.google_geocoding_cost_micro()
    assert fake.calls == 1
    assert ledger.kinds == ["geocoding"]
    assert ledger.settlements == [("r1", price)]  # billed even without a result
    assert ledger.spent[ACCOUNT] == price


@pytest.mark.asyncio
async def test_google_is_skipped_without_an_account_or_when_refused(ledger):
    fake = _FakeGoogle()
    assert await _google_only_geocoder(fake)._try_google("Via Roma 1") is None  # no account
    ledger.enabled = False
    token = spending.charged_account.set(ACCOUNT)
    try:
        assert await _google_only_geocoder(fake)._try_google("Via Roma 1") is None  # switch off
    finally:
        spending.charged_account.reset(token)
    assert fake.calls == 0
    assert ledger.settlements == []


# --- Quotas, uploads and bounded results --------------------------------------------

class _FakeResult:
    def all(self):
        return []

    def first(self):
        return None


class _RecordingSession:
    def __init__(self):
        self.params = []

    async def execute(self, statement, params=None):
        self.params.append(params or {})
        return _FakeResult()


@pytest.fixture
def recording_db(client):
    session = _RecordingSession()

    async def _get_db():
        yield session

    app.dependency_overrides[get_db] = _get_db
    return session


def test_routes_without_provider_cost_have_a_per_account_quota(client, recording_db, monkeypatch):
    monkeypatch.setattr(settings, "route_requests_per_minute", 2)
    statuses = [client.get("/api/transactions", headers=auth_headers(ACCOUNT)).status_code for _ in range(3)]
    assert statuses == [200, 200, 429]
    # The quota is per account.
    assert client.get("/api/transactions", headers=auth_headers()).status_code == 200


def test_direct_valuations_use_the_chat_level_limits(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_per_minute", 1)

    async def _no_address(*args, **kwargs):
        raise ValueError("Indirizzo non trovato")

    monkeypatch.setattr("app.api.valuations.valuate_address", _no_address)
    first = client.get("/api/valuate", params={"address": "Via Roma 1"}, headers=auth_headers(ACCOUNT))
    second = client.get("/api/valuate", params={"address": "Via Roma 1"}, headers=auth_headers(ACCOUNT))
    assert first.status_code == 404
    assert second.status_code == 429


def test_transaction_pages_are_bounded(client, recording_db):
    assert client.get("/api/transactions", params={"limit": 101}, headers=auth_headers(ACCOUNT)).status_code == 422
    assert client.get("/api/transactions", params={"offset": -1}, headers=auth_headers(ACCOUNT)).status_code == 422
    client.get("/api/transactions", headers=auth_headers(ACCOUNT))
    assert recording_db.params[-1]["limit"] == 50 and recording_db.params[-1]["offset"] == 0


def test_zone_geojson_requires_a_bounding_box_and_is_capped(client, recording_db, monkeypatch):
    async def _latest(db):
        return "2024_S2"

    monkeypatch.setattr("app.api.zones.get_latest_semester", _latest)
    assert client.get("/api/zones/geojson", headers=auth_headers(ACCOUNT)).status_code == 422
    ok = client.get("/api/zones/geojson", params={"bbox": "9.1,45.4,9.2,45.5"}, headers=auth_headers(ACCOUNT))
    assert ok.status_code == 200
    assert recording_db.params[-1]["limit"] == 500


PDF = b"%PDF-1.4\n" + b"0" * 200


def _upload(client, account, content=PDF):
    return client.post("/api/documents/upload", files={"file": ("doc.pdf", content, "application/pdf")},
                       headers=auth_headers(account))


def test_an_oversized_file_is_refused_without_storing_it(client):
    response = _upload(client, ACCOUNT, b"%PDF-" + b"0" * (5 * 1024 * 1024))
    assert response.status_code == 413
    assert response.json()["detail"]["error"] == "too_large"
    assert not any(d.owner_id == ACCOUNT for d in document_store._store.values())


def test_stored_upload_bytes_are_capped_per_account_and_in_total(client, monkeypatch):
    document_store._store.clear()
    monkeypatch.setattr(document_store, "MAX_BYTES_PER_ACCOUNT", len(PDF) * 2)
    monkeypatch.setattr(document_store, "MAX_BYTES_TOTAL", len(PDF) * 3)
    assert _upload(client, ACCOUNT).status_code == 200
    assert _upload(client, ACCOUNT).status_code == 200
    third = _upload(client, ACCOUNT)
    assert third.status_code == 429 and third.json()["detail"]["error"] == "account_uploads_full"
    assert _upload(client, "55555555-5555-4555-8555-555555555555").status_code == 200
    full = _upload(client, "66666666-6666-4666-8666-666666666666")
    assert full.status_code == 503 and full.json()["detail"]["error"] == "uploads_full"
    document_store._store.clear()


def test_expired_uploads_are_swept(monkeypatch):
    document_store._store.clear()
    doc = document_store.store_document(ACCOUNT, "a.pdf", "application/pdf", PDF)
    doc.created_at = time.time() - document_store.TTL_SECONDS - 1
    assert document_store.cleanup_expired() == 1
    assert doc.doc_id not in document_store._store


# --- Owner routes ---------------------------------------------------------------------

def test_spending_and_the_switch_are_owner_only(client, monkeypatch):
    async def _report():
        return {"month": "2026-11-01"}

    switched = []

    async def _switch(enabled):
        switched.append(enabled)

    monkeypatch.setattr(spending, "month_report", _report)
    monkeypatch.setattr(spending, "set_paid_calls", _switch)
    assert client.get("/api/admin/spending", headers=auth_headers(ACCOUNT)).status_code == 403
    assert client.put("/api/admin/paid-calls", json={"enabled": False}, headers=auth_headers(ACCOUNT)).status_code == 403
    assert client.get("/api/admin/spending", headers=auth_headers(OWNER_ID)).json() == {"month": "2026-11-01"}
    assert client.put("/api/admin/paid-calls", json={"enabled": False}, headers=auth_headers(OWNER_ID)).json() == {
        "paid_calls_enabled": False
    }
    assert switched == [False]


# --- Secrets ----------------------------------------------------------------------------

def test_keys_tokens_and_document_bytes_stay_out_of_logs_and_responses(client, fake_anthropic, monkeypatch, caplog):
    secret_key = "sk-ant-MARKER-key-0123456789"
    monkeypatch.setattr(settings, "anthropic_api_key", secret_key)
    fake_anthropic()
    document_marker = b"MARKER-DOCUMENT-CONTENT"
    caplog.set_level(logging.DEBUG)

    headers = auth_headers(ACCOUNT)
    token = headers["Authorization"].removeprefix("Bearer ")
    upload = _upload(client, ACCOUNT, b"%PDF-1.4\n" + document_marker + b"0" * 200)
    body = {"messages": [{"role": "user", "content": "Guarda", "document_ids": [upload.json()["doc_id"]]}]}
    chat = client.post("/api/chat", json=body, headers=headers)

    logged = "\n".join(record.getMessage() for record in caplog.records)
    for text in (logged, upload.text, chat.text):
        assert secret_key not in text
        assert token not in text
        assert document_marker.decode() not in text
