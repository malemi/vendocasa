"""Database URLs (backend/app/db_url.py), and the scripts that use them.

The command-line scripts run outside Alembic. Each database entry point must get
as far as connecting; against an unreachable server that is a connection error.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import OperationalError

from app.db_url import async_database_url, sync_database_url

UNREACHABLE = "postgresql://nobody:wrong@127.0.0.1:1/none"


@pytest.mark.parametrize("url", [
    "postgres://u:p@h:5432/d",
    "postgresql://u:p@h:5432/d",
    "postgresql+psycopg://u:p@h:5432/d",
    "postgresql+psycopg_async://u:p@h:5432/d",
])
def test_every_supported_form_maps_to_both_drivers(url):
    assert sync_database_url(url) == "postgresql+psycopg://u:p@h:5432/d"
    assert async_database_url(url) == "postgresql+psycopg_async://u:p@h:5432/d"


def _entry_points():
    from scripts import import_omi, record_external_spend, refresh_disposable_domains, validate_semesters

    return {
        "import_omi.reset_schema": lambda: import_omi.reset_schema(UNREACHABLE),
        "validate_semesters.validate": lambda: validate_semesters.validate(UNREACHABLE),
        "record_external_spend.record": lambda: record_external_spend.record(
            UNREACHABLE, Decimal("0.01"), date(2026, 11, 1), "test"),
        "refresh_disposable_domains.replace_table": lambda: refresh_disposable_domains.replace_table(
            UNREACHABLE, ["example.com"]),
    }


@pytest.mark.parametrize("name", sorted(_entry_points()))
def test_each_script_reaches_the_database_outside_alembic(name):
    with pytest.raises(OperationalError):
        _entry_points()[name]()
