"""Tests for backend/app/main.py: docs disabled by default, startup fail-fast."""

from __future__ import annotations

import os
import subprocess
import sys


def test_docs_disabled_by_default(client):
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_startup_fails_fast_without_anthropic_api_key():
    """A missing ANTHROPIC_API_KEY must fail at import time (process startup),
    not surface as a per-request 503 -- see app/main.py.
    """
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)

    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode != 0
    assert "ANTHROPIC_API_KEY is not set" in result.stderr
