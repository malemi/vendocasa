"""Run the real backend for the browser journeys (frontend/e2e/).

    SUPABASE_STATUS_ENV=/path/to/status.env .venv/bin/python -m tests.e2e.serve

The status file holds what `npx supabase@3.4.0 status -o env` prints for the
local stack (supabase/config.toml); its database must already be migrated
(`alembic upgrade head`). The server seeds the stack (tests/e2e/seed.py),
replaces the model provider and the public geocoders with
tests/e2e/substitute.py, and serves the API on 127.0.0.1:8000 with one
worker, as production does. Tokens are verified against the stack's JWKS.

Two settings differ from production, for the journeys only: request quotas
are higher, so a journey can fill a conversation to its 50-message limit, and
uploads expire after E2E_UPLOAD_TTL_SECONDS (default 4), so the re-upload
journey does not wait 30 minutes.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def load_status(path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in Path(path).read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep:
            values[key.strip()] = value.strip().strip('"')
    return values


def main() -> int:
    status = load_status(os.environ["SUPABASE_STATUS_ENV"])
    # Settings are read when app.config is first imported, so the environment
    # comes first.
    os.environ.update({
        "DATABASE_URL": status["DB_URL"],
        "SUPABASE_URL": status["API_URL"],
        "SUPABASE_JWT_ALGORITHM": "ES256",
        "SUPABASE_JWT_SECRET": "",
        "ANTHROPIC_API_KEY": "e2e-substitute-never-sent",
        "CORS_ORIGINS": "http://127.0.0.1:4173,http://localhost:4173",
        "RATE_LIMIT_PER_MINUTE": "200",
        "RATE_LIMIT_PER_DAY": "2000",
    })

    from tests.e2e.seed import seed

    seeded = seed(status)

    import uvicorn

    from app.config import settings
    from app.services import agent, document_store
    from app.services.geocoder import ItalianGeocoder
    from tests.e2e import substitute

    settings.owner_user_id = seeded["owner_user_id"]
    agent.AsyncAnthropic = substitute.SubstituteAnthropic
    ItalianGeocoder.geocode = substitute.geocode
    document_store.TTL_SECONDS = int(os.environ.get("E2E_UPLOAD_TTL_SECONDS", "4"))

    from app.main import app

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("E2E_API_PORT", "8000")), workers=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
