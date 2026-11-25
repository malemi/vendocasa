"""Spending ledger on real PostgreSQL (backend/app/services/spending.py).

Runs only when TEST_DATABASE_URL points at a disposable PostgreSQL database,
for example `postgresql+psycopg://postgres:postgres@localhost:55432/vendocasa_test`.
The fixture creates the client roles, stamps Alembic at 0003 and applies the
ledger migration 0004 itself, so PostGIS is not needed for these tests.
"""

from __future__ import annotations

import asyncio
import multiprocessing
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.services import spending

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set")

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _sync_url(url: str) -> str:
    return url.replace("+psycopg_async://", "+psycopg://")


def _async_url(url: str) -> str:
    return url.replace("+psycopg://", "+psycopg_async://")


@pytest.fixture(scope="module")
def ledger_db():
    from alembic import command
    from alembic.config import Config

    engine = create_engine(_sync_url(TEST_DATABASE_URL))
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS app CASCADE"))
        conn.execute(text((BACKEND_DIR / "sql" / "client_roles.sql").read_text()))
        conn.execute(text("CREATE SCHEMA app"))
    engine.dispose()

    original = settings.database_url
    settings.database_url = TEST_DATABASE_URL
    try:
        cfg = Config(str(BACKEND_DIR / "alembic.ini"))
        command.stamp(cfg, "0003")
        command.upgrade(cfg, "0004")
    finally:
        settings.database_url = original
    yield TEST_DATABASE_URL


@pytest.fixture
def ledger(ledger_db, monkeypatch):
    """Point the spending service at the test database with small caps."""
    engine = create_async_engine(_async_url(ledger_db))
    monkeypatch.setattr(spending, "_engine", lambda: engine)
    monkeypatch.setattr(settings, "account_monthly_cap_usd", 1.0)
    monkeypatch.setattr(settings, "global_monthly_cap_usd", 100.0)
    sync = create_engine(_sync_url(ledger_db))
    with sync.begin() as conn:
        conn.execute(text("DELETE FROM app.spend_reservation"))
        conn.execute(text("DELETE FROM app.spend_month"))
        conn.execute(text("UPDATE app.service_flag SET enabled = true WHERE name = 'paid_calls_enabled'"))
    yield sync
    asyncio.get_event_loop_policy()  # keep the loop alive until disposal below
    sync.dispose()


def _month_row(sync, scope):
    with sync.connect() as conn:
        row = conn.execute(
            text("SELECT spent_micro_usd, reserved_micro_usd FROM app.spend_month "
                 "WHERE scope = :s AND month = :m"),
            {"s": scope, "m": spending.month_of()},
        ).first()
    return tuple(row) if row else (0, 0)


@pytest.mark.asyncio
async def test_settlement_charges_actual_cost_and_releases_the_rest(ledger):
    reservation = await spending.reserve("acct-a", "model", 300_000)
    assert _month_row(ledger, "acct-a") == (0, 300_000)
    assert await spending.settle(reservation, 120_000)
    assert _month_row(ledger, "acct-a") == (120_000, 0)
    assert _month_row(ledger, "global") == (120_000, 0)
    assert not await spending.settle(reservation, 1)  # already settled: no change
    assert _month_row(ledger, "acct-a") == (120_000, 0)


@pytest.mark.asyncio
async def test_unknown_outcome_settles_the_full_reservation(ledger):
    reservation = await spending.reserve("acct-b", "model", 250_000)
    await spending.settle(reservation, None)
    assert _month_row(ledger, "acct-b") == (250_000, 0)


@pytest.mark.asyncio
async def test_the_account_cap_refuses_before_any_call(ledger):
    await spending.settle(await spending.reserve("acct-c", "model", 900_000), None)
    with pytest.raises(spending.SpendRefused) as info:
        await spending.reserve("acct-c", "model", 100_001)
    assert info.value.code == "account_limit"
    await spending.reserve("acct-c", "model", 100_000)  # exactly up to the cap is allowed


@pytest.mark.asyncio
async def test_the_global_cap_refuses_every_account(ledger, monkeypatch):
    monkeypatch.setattr(settings, "global_monthly_cap_usd", 0.5)
    await spending.settle(await spending.reserve("acct-d", "model", 400_000), None)
    with pytest.raises(spending.SpendRefused) as info:
        await spending.reserve("acct-e", "model", 200_000)
    assert info.value.code == "global_limit"


@pytest.mark.asyncio
async def test_the_switch_refuses_paid_calls(ledger):
    await spending.set_paid_calls(False)
    with pytest.raises(spending.SpendRefused) as info:
        await spending.reserve("acct-f", "model", 1)
    assert info.value.code == "paused"
    await spending.set_paid_calls(True)
    await spending.reserve("acct-f", "model", 1)


@pytest.mark.asyncio
async def test_a_store_failure_refuses_and_never_fails_open(ledger, monkeypatch):
    broken = create_async_engine("postgresql+psycopg_async://nobody:wrong@127.0.0.1:1/none")
    monkeypatch.setattr(spending, "_engine", lambda: broken)
    with pytest.raises(spending.SpendRefused) as info:
        await spending.reserve("acct-g", "model", 1)
    assert info.value.code == "assistant_unavailable"


@pytest.mark.asyncio
async def test_a_new_month_starts_at_zero(ledger):
    november = datetime(2026, 11, 30, 23, 59, tzinfo=UTC)
    december = datetime(2026, 12, 1, 0, 1, tzinfo=UTC)
    await spending.settle(await spending.reserve("acct-h", "model", 1_000_000, now=november), None)
    with pytest.raises(spending.SpendRefused):
        await spending.reserve("acct-h", "model", 1, now=november)
    await spending.reserve("acct-h", "model", 1_000_000, now=december)


@pytest.mark.asyncio
async def test_an_overrun_turns_paid_calls_off(ledger):
    reservation = await spending.reserve("acct-i", "model", 10_000)
    await spending.settle(reservation, 10_001)
    with pytest.raises(spending.SpendRefused) as info:
        await spending.reserve("acct-i", "model", 1)
    assert info.value.code == "paused"


@pytest.mark.asyncio
async def test_a_failed_switch_off_after_an_overrun_keeps_the_settlement(ledger, monkeypatch, caplog):
    async def unavailable_switch(enabled):
        raise RuntimeError("flag store unavailable")

    reservation = await spending.reserve("acct-j", "model", 10_000)
    monkeypatch.setattr(spending, "set_paid_calls", unavailable_switch)
    with caplog.at_level("ERROR", logger=spending.logger.name):
        assert await spending.settle(reservation, 10_001)
    assert _month_row(ledger, "acct-j") == (10_001, 0)
    assert "Turning paid calls off after the overrun" in caplog.text


# --- Across processes ---------------------------------------------------------

def _reserve_in_child(url, account, amount, attempts, barrier, results):
    os.environ["DATABASE_URL"] = url
    from app.services import spending as child_spending

    engine = create_async_engine(_async_url(url))
    child_spending._engine = lambda: engine

    async def run():
        granted = 0
        barrier.wait()
        for _ in range(attempts):
            try:
                await child_spending.reserve(account, "model", amount)
                granted += 1
            except child_spending.SpendRefused:
                pass
        await engine.dispose()
        return granted

    results.put(asyncio.run(run()))


def _race(url, account, amount, attempts=40):
    ctx = multiprocessing.get_context("spawn")
    barrier, results = ctx.Barrier(2), ctx.Queue()
    workers = [ctx.Process(target=_reserve_in_child, args=(url, account, amount, attempts, barrier, results))
               for _ in range(2)]
    for w in workers:
        w.start()
    for w in workers:
        w.join(timeout=60)
        assert w.exitcode == 0
    return results.get() + results.get()


def test_two_processes_never_overbook_an_account(ledger, ledger_db):
    # A $1 cap and $0.03 reservations admit at most 33, however the races fall.
    granted = _race(ledger_db, f"race-{uuid.uuid4()}", 30_000)
    assert granted == 33


def test_two_processes_never_overbook_the_global_cap(ledger, ledger_db, monkeypatch):
    with ledger.begin() as conn:
        conn.execute(text("INSERT INTO app.spend_month (scope, month, spent_micro_usd) "
                          "VALUES ('global', :m, :s)"), {"m": spending.month_of(), "s": 99_700_000})
    # $0.30 of global room and $0.03 reservations from fresh accounts: at most 10.
    ctx_account = f"race-global-{uuid.uuid4()}"
    granted = _race(ledger_db, ctx_account, 30_000)
    spent, reserved = _month_row(ledger, "global")
    assert granted == 10
    assert spent + reserved <= 100_000_000


def _reserve_then_die(url, account):
    os.environ["DATABASE_URL"] = url
    from app.services import spending as child_spending

    engine = create_async_engine(_async_url(url))
    child_spending._engine = lambda: engine
    asyncio.run(child_spending.reserve(account, "model", 70_000))
    os._exit(1)  # crash before settling


@pytest.mark.asyncio
async def test_a_crash_after_reserving_is_settled_in_full_by_the_sweep(ledger, ledger_db):
    account = f"crash-{uuid.uuid4()}"
    process = multiprocessing.get_context("spawn").Process(target=_reserve_then_die, args=(ledger_db, account))
    process.start()
    process.join(timeout=60)
    assert process.exitcode == 1
    assert _month_row(ledger, account) == (0, 70_000)

    later = datetime.now(UTC) + timedelta(minutes=16)
    assert await spending.sweep_stale(now=later) >= 1
    assert _month_row(ledger, account) == (70_000, 0)
