"""The `app` schema, and no client-role access to `app` or `omi`.

The database provider's data API serves exposed schemas to holders of the
public client key (`anon`) or of a user token (`authenticated`). Application
state and OMI data are reachable only through the backend, so these roles,
and PUBLIC, hold no privilege on either schema, nor on the tables, sequences
and functions in it, including Alembic's version table. Objects created
later are protected the same way: no client role has USAGE on either schema,
and each migration that creates an object revokes client privileges on it
explicitly. The per-schema default-privilege revokes below only undo earlier
per-schema grants; they cannot remove a global default, such as PostgreSQL's
EXECUTE for PUBLIC on new functions.

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
