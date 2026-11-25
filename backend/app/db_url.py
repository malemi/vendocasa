"""SQLAlchemy URLs for the configured PostgreSQL database.

DATABASE_URL may use either form that hosting providers hand out
(`postgres://`, `postgresql://`) or name a psycopg driver explicitly. The
application's engine uses the asynchronous psycopg driver; migrations and the
command-line scripts use the synchronous one. This module has no side effects,
so scripts can import it outside an Alembic run.
"""

from __future__ import annotations

SYNC_SCHEME = "postgresql+psycopg://"
ASYNC_SCHEME = "postgresql+psycopg_async://"


def sync_database_url(url: str) -> str:
    """The URL with SQLAlchemy's synchronous psycopg driver."""
    for scheme in ("postgres://", "postgresql://", ASYNC_SCHEME):
        if url.startswith(scheme):
            return SYNC_SCHEME + url[len(scheme):]
    return url


def async_database_url(url: str) -> str:
    """The URL with SQLAlchemy's asynchronous psycopg driver."""
    sync = sync_database_url(url)
    if sync.startswith(SYNC_SCHEME):
        return ASYNC_SCHEME + sync[len(SYNC_SCHEME):]
    return sync
