"""Disposable email domains and the identity service's before-user-created hook.

`app.disposable_email_domains` is loaded from backend/data/disposable_domains.txt.
`app.before_user_created(event)` refuses a sign-up whose email domain, or any
parent domain, is listed. Supabase Auth calls it as a Postgres-function hook,
as the role `supabase_auth_admin`; no client role may execute it. The backend
refuses the same domains independently (app/services/disposable_domains.py).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-25
"""

from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

DOMAINS_FILE = Path(__file__).resolve().parents[2] / "data" / "disposable_domains.txt"
REFUSAL_MESSAGE = "Questo indirizzo email non è accettato. Usa un indirizzo personale."
assert "'" not in REFUSAL_MESSAGE  # embedded in a SQL string literal below


def read_vendored_domains(path: Path = DOMAINS_FILE) -> list[str]:
    domains = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip().lower()
        if line and not line.startswith("#"):
            domains.append(line)
    return sorted(set(domains))


def upgrade() -> None:
    op.execute("CREATE TABLE IF NOT EXISTS app.disposable_email_domains (domain TEXT PRIMARY KEY)")
    op.execute("REVOKE ALL ON app.disposable_email_domains FROM PUBLIC, anon, authenticated")

    # The table is new in this migration, so it is empty here; the refresh
    # script (scripts/refresh_disposable_domains.py) replaces its contents later.
    table = sa.table("disposable_email_domains", sa.column("domain", sa.Text), schema="app")
    op.bulk_insert(table, [{"domain": d} for d in read_vendored_domains()])

    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION app.before_user_created(event jsonb)
        RETURNS jsonb
        LANGUAGE plpgsql
        STABLE
        SET search_path = ''
        AS $$
        DECLARE
            v_email text := lower(coalesce(event->'user'->>'email', event->>'email', ''));
            v_domain text := split_part(v_email, '@', 2);
        BEGIN
            WHILE v_domain <> '' LOOP
                IF EXISTS (
                    SELECT 1 FROM app.disposable_email_domains d WHERE d.domain = v_domain
                ) THEN
                    RETURN jsonb_build_object(
                        'error',
                        jsonb_build_object('http_code', 403, 'message', '{REFUSAL_MESSAGE}')
                    );
                END IF;
                IF position('.' in v_domain) = 0 THEN
                    EXIT;
                END IF;
                v_domain := substr(v_domain, position('.' in v_domain) + 1);
            END LOOP;
            RETURN '{{}}'::jsonb;
        END
        $$
        """
    )
    op.execute("REVOKE ALL ON FUNCTION app.before_user_created(jsonb) FROM PUBLIC, anon, authenticated")
    op.execute("GRANT USAGE ON SCHEMA app TO supabase_auth_admin")
    op.execute("GRANT EXECUTE ON FUNCTION app.before_user_created(jsonb) TO supabase_auth_admin")
    op.execute("GRANT SELECT ON app.disposable_email_domains TO supabase_auth_admin")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS app.before_user_created(jsonb)")
    op.execute("DROP TABLE IF EXISTS app.disposable_email_domains")
