"""The `app` schema, and no client-role access to `app` or `omi`.

The database provider's data API serves exposed schemas to holders of the
public client key (`anon`) or of a user token (`authenticated`). Application
state and OMI data are reachable only through the backend, so these roles,
and PUBLIC, hold no privilege on either schema, nor on the tables, sequences
and functions in it, including Alembic's version table. Default privileges
extend this to tables and sequences created later. Functions created later
still get PostgreSQL's global default EXECUTE for PUBLIC; without USAGE on
the schema no client role can reach them, and the migration that creates a
function also revokes its EXECUTE explicitly.

The roles must exist. Supabase creates them; a plain PostgreSQL test database
creates them from backend/sql/client_roles.sql before migrating.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-25
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

CLIENT_ROLES = "PUBLIC, anon, authenticated"
PROTECTED_SCHEMAS = ("app", "omi")


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    for schema in PROTECTED_SCHEMAS:
        op.execute(f"REVOKE ALL ON SCHEMA {schema} FROM {CLIENT_ROLES}")
        op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA {schema} FROM {CLIENT_ROLES}")
        op.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA {schema} FROM {CLIENT_ROLES}")
        op.execute(f"REVOKE ALL ON ALL FUNCTIONS IN SCHEMA {schema} FROM {CLIENT_ROLES}")
        # New functions get EXECUTE for PUBLIC through a global default that a
        # per-schema rule cannot remove; they are protected by the schema-level
        # revoke above (no USAGE) and by explicit revokes where they are created.
        for kind in ("TABLES", "SEQUENCES"):
            op.execute(
                f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} "
                f"REVOKE ALL ON {kind} FROM {CLIENT_ROLES}"
            )


def downgrade() -> None:
    # Revoked privileges are not restored: the previous grants are unknown,
    # and restoring client access to these schemas would be unsafe. The `app`
    # schema stays because it holds Alembic's version table.
    pass
