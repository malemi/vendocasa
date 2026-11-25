"""Record provider spending made outside the application in the ledger.

Real-provider runs before reopening, such as the cost measurement, spend from
the same provider account. Recording them keeps the month's global total, and
so the $100 cap, true. The spend is charged to the scope `external` and to
`global`, as an already-settled reservation of kind `external`.

Usage (from backend/, with DATABASE_URL set or in .env):
    python -m scripts.record_external_spend --usd 0.42 --month 2026-11 --note "M3 cost measurement"
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, text

EXTERNAL_SCOPE = "external"


def parse_month(value: str) -> date:
    year, month = value.split("-")
    return date(int(year), int(month), 1)


def record(database_url: str, usd: Decimal, month: date, note: str) -> None:
    from app.services.pricing import PRICE_TABLE_VERSION, usd_to_micro
    from migrations.env import sync_database_url

    micro = usd_to_micro(usd)
    engine = create_engine(sync_database_url(database_url))
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO app.spend_month (scope, month) VALUES ('global', :m), (:e, :m) "
                "ON CONFLICT DO NOTHING"
            ),
            {"m": month, "e": EXTERNAL_SCOPE},
        )
        conn.execute(
            text(
                "INSERT INTO app.spend_reservation (id, account_id, month, kind, amount_micro_usd, "
                "settled_micro_usd, state, price_table_version, settled_at) "
                "VALUES (:id, :e, :m, 'external', :amt, :amt, 'settled', :v, now())"
            ),
            {"id": str(uuid.uuid4()), "e": EXTERNAL_SCOPE, "m": month, "amt": micro,
             "v": f"{PRICE_TABLE_VERSION}; {note}"[:200]},
        )
        conn.execute(
            text(
                "UPDATE app.spend_month SET spent_micro_usd = spent_micro_usd + :amt "
                "WHERE month = :m AND scope IN ('global', :e)"
            ),
            {"amt": micro, "m": month, "e": EXTERNAL_SCOPE},
        )
    engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--usd", required=True, type=Decimal, help="amount in US dollars, e.g. 0.42")
    parser.add_argument("--month", required=True, type=parse_month, help="calendar month, YYYY-MM")
    parser.add_argument("--note", required=True, help="what the spend was for")
    args = parser.parse_args()
    if args.usd <= 0:
        parser.error("--usd must be positive")

    from app.config import settings

    record(settings.database_url, args.usd, args.month, args.note)
    print(f"Recorded ${args.usd} for {args.month:%Y-%m} under '{EXTERNAL_SCOPE}' and 'global'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
