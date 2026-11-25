"""Seed the local Supabase stack for the browser journeys.

Imports one synthetic semester (tests/omi_fixtures.py) through the real
importer, replaces three synthetic sales in zone MI00000001, where the test
addresses fall, and makes sure the owner's account exists. The owner is
created already confirmed through the identity service's admin API, as M7
creates the real one. Running the seed again changes nothing.
"""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

from app.db_url import sync_database_url
from scripts.import_omi import discover_and_import_all
from tests.omi_fixtures import make_archive

OWNER_EMAIL = "owner@vendocasa.test"
SEED_NOTE = "e2e synthetic sale"
SALES = [
    (date(2024, 3, 15), 210_000, "A/2", 4.5, 85),
    (date(2024, 6, 2), 189_000, "A/3", 4.0, 78),
    (date(2024, 9, 20), 232_500, "A/2", 5.0, 92),
]


def admin_headers(status: dict[str, str]) -> dict[str, str]:
    key = status["SERVICE_ROLE_KEY"]
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def ensure_confirmed_user(status: dict[str, str], email: str) -> str:
    """The ID of a confirmed account for `email`, created if missing."""
    api = status["API_URL"]
    response = httpx.post(f"{api}/auth/v1/admin/users", headers=admin_headers(status),
                          json={"email": email, "email_confirm": True}, timeout=10)
    if response.status_code == 200:
        return response.json()["id"]
    if response.status_code != 422:
        response.raise_for_status()
    page = 1
    while True:
        listing = httpx.get(f"{api}/auth/v1/admin/users", headers=admin_headers(status),
                            params={"page": page, "per_page": 200}, timeout=10)
        listing.raise_for_status()
        users = listing.json().get("users", [])
        for user in users:
            if user.get("email") == email:
                return user["id"]
        if not users:
            raise RuntimeError(f"{email} exists but is not in the user listing")
        page += 1


def seed(status: dict[str, str]) -> dict[str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        make_archive(Path(tmp))
        failures = discover_and_import_all(tmp, status["DB_URL"])
    if failures:
        raise RuntimeError(f"{failures} synthetic semesters failed to import")

    engine = create_engine(sync_database_url(status["DB_URL"]))
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM omi.transactions WHERE notes = :n"), {"n": SEED_NOTE})
            conn.execute(
                text(
                    "INSERT INTO omi.transactions (transaction_date, transaction_type, declared_price, "
                    "municipality, omi_zone, link_zona, cadastral_category, cadastral_vani, cadastral_mq, notes) "
                    "VALUES (:d, 'compravendita', :p, 'MILANO', 'B01', 'MI00000001', :c, :v, :mq, :n)"
                ),
                [{"d": d, "p": p, "c": c, "v": v, "mq": mq, "n": SEED_NOTE} for d, p, c, v, mq in SALES],
            )
    finally:
        engine.dispose()
    return {"owner_user_id": ensure_confirmed_user(status, OWNER_EMAIL)}
