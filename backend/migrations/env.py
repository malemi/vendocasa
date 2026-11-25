"""Alembic environment for the VendoCasa database.

Migrations run synchronously through psycopg against DATABASE_URL, the same
setting the application uses. Alembic's version table lives in the `app`
schema, which the database provider's client-facing data API does not expose.
"""

from alembic import context
from sqlalchemy import create_engine, text

from app.config import settings
from app.db_url import sync_database_url

VERSION_TABLE_SCHEMA = "app"


def run_migrations_offline() -> None:
    context.configure(
        url=sync_database_url(settings.database_url),
        literal_binds=True,
        version_table_schema=VERSION_TABLE_SCHEMA,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(sync_database_url(settings.database_url))
    with engine.connect() as connection:
        # The version table needs its schema before the first migration runs.
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {VERSION_TABLE_SCHEMA}"))
        connection.commit()
        context.configure(
            connection=connection,
            version_table_schema=VERSION_TABLE_SCHEMA,
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
