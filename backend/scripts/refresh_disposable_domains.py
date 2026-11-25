"""Refresh the disposable email domain list.

Downloads the current blocklist, rewrites backend/data/disposable_domains.txt,
and replaces the contents of app.disposable_email_domains in one transaction.
The backend reloads its cached copy within an hour (app/services/disposable_domains.py).

Usage (from backend/, with DATABASE_URL set or in .env):
    python -m scripts.refresh_disposable_domains
    python -m scripts.refresh_disposable_domains --file-only   # skip the database
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

SOURCE_URL = (
    "https://raw.githubusercontent.com/disposable-email-domains/"
    "disposable-email-domains/main/disposable_email_blocklist.conf"
)
DOMAINS_FILE = Path(__file__).resolve().parents[1] / "data" / "disposable_domains.txt"
DOMAIN_PATTERN = re.compile(r"^[a-z0-9.-]+\.[a-z0-9-]+$")
MIN_EXPECTED_DOMAINS = 1000  # a much shorter download means a broken source, not a policy


def fetch_domains() -> list[str]:
    response = httpx.get(SOURCE_URL, timeout=30, follow_redirects=False)
    response.raise_for_status()
    domains = sorted({line.strip().lower() for line in response.text.splitlines() if line.strip()})
    invalid = [d for d in domains if not DOMAIN_PATTERN.match(d)]
    if invalid:
        raise ValueError(f"{len(invalid)} malformed entries, e.g. {invalid[:3]}")
    if len(domains) < MIN_EXPECTED_DOMAINS:
        raise ValueError(f"only {len(domains)} domains downloaded; refusing to replace the list")
    return domains


def write_file(domains: list[str]) -> None:
    header = [
        "# Disposable email domains refused at registration (backend/app/services/disposable_domains.py).",
        "# Source: https://github.com/disposable-email-domains/disposable-email-domains, "
        "file disposable_email_blocklist.conf",
        f"# License: CC0 1.0 Universal. Retrieved {datetime.date.today().isoformat()}. "
        "Refresh with: python -m scripts.refresh_disposable_domains",
    ]
    DOMAINS_FILE.write_text("\n".join(header + domains) + "\n", encoding="utf-8")


def replace_table(database_url: str, domains: list[str]) -> None:
    from app.db_url import sync_database_url

    engine = create_engine(sync_database_url(database_url))
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM app.disposable_email_domains"))
        conn.execute(
            text("INSERT INTO app.disposable_email_domains (domain) VALUES (:domain)"),
            [{"domain": d} for d in domains],
        )
    engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--file-only", action="store_true", help="update the file, not the database")
    args = parser.parse_args()

    domains = fetch_domains()
    write_file(domains)
    print(f"Wrote {len(domains)} domains to {DOMAINS_FILE}")
    if not args.file_only:
        from app.config import settings

        replace_table(settings.database_url, domains)
        print("Replaced app.disposable_email_domains")
    return 0


if __name__ == "__main__":
    sys.exit(main())
