"""Monthly spending caps: per account and service-wide, in micro-dollars.

Before every paid provider call the caller reserves the call's maximum possible
cost. `reserve` locks the global month row and then the account month row (always
in that order, so concurrent reservations cannot deadlock), checks
`spent + reserved + amount` against both caps and the paid-call switch, and
records an open reservation, all in one transaction. A refusal happens before
any provider call.

After the call, `settle` moves the actual cost to `spent` and releases the rest.
An unknown outcome (crash, timeout, cancellation, provider error, missing usage)
settles the full reservation. Settlement is one conditional update from `open`
to `settled`, so a late live settlement and the stale-reservation sweep can never
both count the same reservation.

Months are calendar months in UTC. Caps come from configuration
(ACCOUNT_MONTHLY_CAP_USD, GLOBAL_MONTHLY_CAP_USD). Any database failure while
reserving refuses the call: the ledger never fails open.
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import settings
from app.services.pricing import PRICE_TABLE_VERSION, usd_to_micro

logger = logging.getLogger(__name__)

GLOBAL_SCOPE = "global"
PAID_CALLS_FLAG = "paid_calls_enabled"
STALE_AFTER = timedelta(minutes=15)

# The account a paid call is charged to, for services that cannot take it as an
# argument (the geocoder's Google fallback). Set by the route or agent loop.
charged_account: ContextVar[str | None] = ContextVar("charged_account", default=None)


class SpendRefused(Exception):
    """A paid call may not start. `code` is a refusal code (app/refusals.py)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Reservation:
    id: str
    account_id: str
    month: date
    amount_micro: int


def month_of(moment: datetime | None = None) -> date:
    moment = moment or datetime.now(UTC)
    return date(moment.year, moment.month, 1)


def account_cap_micro() -> int:
    return usd_to_micro(Decimal(str(settings.account_monthly_cap_usd)))


def global_cap_micro() -> int:
    return usd_to_micro(Decimal(str(settings.global_monthly_cap_usd)))


def _engine() -> AsyncEngine:
    from app.database import engine

    return engine


async def _lock_month_rows(conn, account_id: str, month: date) -> tuple[tuple[int, int], tuple[int, int]]:
    await conn.execute(
        text(
            "INSERT INTO app.spend_month (scope, month) VALUES (:g, :m), (:a, :m) "
            "ON CONFLICT DO NOTHING"
        ),
        {"g": GLOBAL_SCOPE, "a": account_id, "m": month},
    )
    rows = {}
    for scope in (GLOBAL_SCOPE, account_id):  # fixed order: global, then account
        row = (
            await conn.execute(
                text(
                    "SELECT spent_micro_usd, reserved_micro_usd FROM app.spend_month "
                    "WHERE scope = :s AND month = :m FOR UPDATE"
                ),
                {"s": scope, "m": month},
            )
        ).one()
        rows[scope] = (row[0], row[1])
    return rows[GLOBAL_SCOPE], rows[account_id]


async def _paid_calls_enabled(conn) -> bool:
    row = (
        await conn.execute(
            text("SELECT enabled FROM app.service_flag WHERE name = :n FOR SHARE"),
            {"n": PAID_CALLS_FLAG},
        )
    ).first()
    return bool(row and row[0])


async def reserve(account_id: str, kind: str, amount_micro: int, *, now: datetime | None = None) -> Reservation:
    """Reserve `amount_micro` for one paid call, or raise SpendRefused."""
    month = month_of(now)
    try:
        async with _engine().begin() as conn:
            if not await _paid_calls_enabled(conn):
                raise SpendRefused("paused")
            (g_spent, g_reserved), (a_spent, a_reserved) = await _lock_month_rows(conn, account_id, month)
            if g_spent + g_reserved + amount_micro > global_cap_micro():
                raise SpendRefused("global_limit")
            if a_spent + a_reserved + amount_micro > account_cap_micro():
                raise SpendRefused("account_limit")
            reservation_id = str(uuid.uuid4())
            await conn.execute(
                text(
                    "UPDATE app.spend_month SET reserved_micro_usd = reserved_micro_usd + :amt "
                    "WHERE month = :m AND scope IN (:g, :a)"
                ),
                {"amt": amount_micro, "m": month, "g": GLOBAL_SCOPE, "a": account_id},
            )
            await conn.execute(
                text(
                    "INSERT INTO app.spend_reservation "
                    "(id, account_id, month, kind, amount_micro_usd, state, price_table_version) "
                    "VALUES (:id, :a, :m, :k, :amt, 'open', :v)"
                ),
                {"id": reservation_id, "a": account_id, "m": month, "k": kind,
                 "amt": amount_micro, "v": PRICE_TABLE_VERSION},
            )
    except SpendRefused:
        raise
    except Exception as exc:  # the ledger is unavailable: refuse, never fail open
        logger.error("Spending reservation failed: %s", type(exc).__name__)
        raise SpendRefused("assistant_unavailable") from exc
    return Reservation(reservation_id, account_id, month, amount_micro)


async def settle(reservation: Reservation | str, actual_micro: int | None) -> bool:
    """Settle an open reservation at `actual_micro`, or at its full amount when
    the actual cost is unknown (None). Returns False if it was already settled.
    """
    reservation_id = reservation.id if isinstance(reservation, Reservation) else reservation
    async with _engine().begin() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT account_id, month, amount_micro_usd FROM app.spend_reservation "
                    "WHERE id = :id AND state = 'open' FOR UPDATE"
                ),
                {"id": reservation_id},
            )
        ).first()
        if row is None:
            return False
        account_id, month, amount = row[0], row[1], row[2]
        charged = amount if actual_micro is None else actual_micro
        # Lock the month rows in the same order as reserve() before updating them.
        await _lock_month_rows(conn, account_id, month)
        await conn.execute(
            text(
                "UPDATE app.spend_reservation SET state = 'settled', settled_micro_usd = :c, "
                "settled_at = now() WHERE id = :id"
            ),
            {"c": charged, "id": reservation_id},
        )
        await conn.execute(
            text(
                "UPDATE app.spend_month SET spent_micro_usd = spent_micro_usd + :c, "
                "reserved_micro_usd = reserved_micro_usd - :amt "
                "WHERE month = :m AND scope IN (:g, :a)"
            ),
            {"c": charged, "amt": amount, "m": month, "g": GLOBAL_SCOPE, "a": account_id},
        )
        if charged > amount:
            # The reservation was not an upper bound: the price table or the
            # token count is wrong. Stop paid calls until a person checks it.
            logger.error(
                "Reservation %s settled at %d micro-USD above its %d reservation; "
                "turning paid calls off.", reservation_id, charged, amount,
            )
            await conn.execute(
                text("UPDATE app.service_flag SET enabled = false WHERE name = :n"),
                {"n": PAID_CALLS_FLAG},
            )
    return True


async def sweep_stale(*, older_than: timedelta = STALE_AFTER, now: datetime | None = None) -> int:
    """Settle, at their full amount, reservations open for longer than `older_than`."""
    cutoff = (now or datetime.now(UTC)) - older_than
    async with _engine().connect() as conn:
        ids = [
            row[0]
            for row in await conn.execute(
                text("SELECT id FROM app.spend_reservation WHERE state = 'open' AND created_at < :c"),
                {"c": cutoff},
            )
        ]
    settled = 0
    for reservation_id in ids:
        if await settle(str(reservation_id), None):
            settled += 1
    if settled:
        logger.warning("Settled %d stale reservations at their full amount", settled)
    return settled


async def precheck(account_id: str) -> None:
    """Refuse early, before a chat stream opens, when nothing could be reserved."""
    month = month_of()
    try:
        async with _engine().connect() as conn:
            if not await _paid_calls_enabled(conn):
                raise SpendRefused("paused")
            rows = {
                row[0]: row[1] + row[2]
                for row in await conn.execute(
                    text(
                        "SELECT scope, spent_micro_usd, reserved_micro_usd FROM app.spend_month "
                        "WHERE month = :m AND scope IN (:g, :a)"
                    ),
                    {"m": month, "g": GLOBAL_SCOPE, "a": account_id},
                )
            }
    except SpendRefused:
        raise
    except Exception as exc:
        logger.error("Spending precheck failed: %s", type(exc).__name__)
        raise SpendRefused("assistant_unavailable") from exc
    if rows.get(GLOBAL_SCOPE, 0) >= global_cap_micro():
        raise SpendRefused("global_limit")
    if rows.get(account_id, 0) >= account_cap_micro():
        raise SpendRefused("account_limit")


async def set_paid_calls(enabled: bool) -> None:
    async with _engine().begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO app.service_flag (name, enabled) VALUES (:n, :e) "
                "ON CONFLICT (name) DO UPDATE SET enabled = EXCLUDED.enabled"
            ),
            {"n": PAID_CALLS_FLAG, "e": enabled},
        )


async def month_report(month: date | None = None) -> dict:
    """The month's global and per-account spending, for the owner."""
    month = month or month_of()
    async with _engine().connect() as conn:
        enabled = await _paid_calls_enabled(conn)
        rows = (
            await conn.execute(
                text(
                    "SELECT scope, spent_micro_usd, reserved_micro_usd FROM app.spend_month "
                    "WHERE month = :m ORDER BY spent_micro_usd DESC"
                ),
                {"m": month},
            )
        ).all()

    def usd(micro: int) -> float:
        return round(micro / 1_000_000, 6)

    global_row = next((r for r in rows if r[0] == GLOBAL_SCOPE), None)
    return {
        "month": month.isoformat(),
        "paid_calls_enabled": enabled,
        "caps_usd": {"account": settings.account_monthly_cap_usd, "global": settings.global_monthly_cap_usd},
        "global": {"spent_usd": usd(global_row[1]) if global_row else 0.0,
                   "reserved_usd": usd(global_row[2]) if global_row else 0.0},
        "accounts": [
            {"account_id": r[0], "spent_usd": usd(r[1]), "reserved_usd": usd(r[2])}
            for r in rows if r[0] != GLOBAL_SCOPE
        ],
    }
