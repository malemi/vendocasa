"""Disposable email domains, loaded from `app.disposable_email_domains`.

The same table feeds the identity service's before-user-created hook, so the
hook and the backend refuse the same domains. The backend check holds even
if the hook is missing or misconfigured: an account whose email domain is
listed cannot use any API route.
"""

from __future__ import annotations

import asyncio
import time

from sqlalchemy import text

REFRESH_SECONDS = 3600

_domains: frozenset[str] | None = None
_loaded_at = 0.0
_lock = asyncio.Lock()


def email_domain_candidates(email: str) -> list[str]:
    """Return the email's domain and each parent domain, most specific first.

    `mail.tempmail.example` yields `mail.tempmail.example`, `tempmail.example`
    and `example`, so a listed domain also covers its subdomains.
    """
    domain = email.rsplit("@", 1)[-1].strip().lower().rstrip(".")
    parts = domain.split(".")
    return [".".join(parts[i:]) for i in range(len(parts)) if parts[i]]


async def _load_domains() -> frozenset[str]:
    from app.database import engine

    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT domain FROM app.disposable_email_domains"))
        return frozenset(row[0] for row in result)


async def disposable_domains() -> frozenset[str]:
    """Return the cached domain set, reloading it at most once per REFRESH_SECONDS."""
    global _domains, _loaded_at
    if _domains is not None and time.monotonic() - _loaded_at < REFRESH_SECONDS:
        return _domains
    async with _lock:
        if _domains is None or time.monotonic() - _loaded_at >= REFRESH_SECONDS:
            _domains = await _load_domains()
            _loaded_at = time.monotonic()
    return _domains


async def is_disposable(email: str) -> bool:
    domains = await disposable_domains()
    return any(candidate in domains for candidate in email_domain_candidates(email))


def set_domains_for_tests(domains: set[str] | None) -> None:
    """Replace the cached set (tests only); None forces a reload from the database."""
    global _domains, _loaded_at
    _domains = frozenset(domains) if domains is not None else None
    _loaded_at = time.monotonic() if domains is not None else 0.0
