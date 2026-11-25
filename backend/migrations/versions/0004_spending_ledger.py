"""Spending ledger: monthly totals, reservations and the paid-call switch.

See app/services/spending.py for the reservation and settlement rules.
Amounts are integer micro-dollars. Paid calls start switched off.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-25
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

CLIENT_ROLES = "PUBLIC, anon, authenticated"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE app.spend_month (
            scope               TEXT    NOT NULL,  -- an account ID, or 'global'
            month               DATE    NOT NULL,  -- first day of the calendar month, UTC
            spent_micro_usd     BIGINT  NOT NULL DEFAULT 0 CHECK (spent_micro_usd >= 0),
            reserved_micro_usd  BIGINT  NOT NULL DEFAULT 0 CHECK (reserved_micro_usd >= 0),
            PRIMARY KEY (scope, month)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE app.spend_reservation (
            id                   UUID        PRIMARY KEY,
            account_id           TEXT        NOT NULL,
            month                DATE        NOT NULL,
            kind                 TEXT        NOT NULL,  -- model, geocoding or external
            amount_micro_usd     BIGINT      NOT NULL CHECK (amount_micro_usd >= 0),
            settled_micro_usd    BIGINT      CHECK (settled_micro_usd >= 0),
            state                TEXT        NOT NULL CHECK (state IN ('open', 'settled')),
            price_table_version  TEXT        NOT NULL,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            settled_at           TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX spend_reservation_open_idx ON app.spend_reservation (created_at) "
        "WHERE state = 'open'"
    )
    op.execute("CREATE TABLE app.service_flag (name TEXT PRIMARY KEY, enabled BOOLEAN NOT NULL)")
    op.execute("INSERT INTO app.service_flag (name, enabled) VALUES ('paid_calls_enabled', false)")
    for table in ("spend_month", "spend_reservation", "service_flag"):
        op.execute(f"REVOKE ALL ON app.{table} FROM {CLIENT_ROLES}")


def downgrade() -> None:
    # The ledger records real spending; dropping it would lose the month's
    # totals and let the caps restart from zero. Refuse instead.
    raise RuntimeError("The spending ledger migration cannot be downgraded.")
