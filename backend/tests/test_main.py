"""Tests for backend/app/main.py: docs disabled by default, startup fail-fast."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = str(Path(__file__).resolve().parents[1])


def test_docs_disabled_by_default(client):
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_startup_fails_fast_without_anthropic_api_key():
    """A missing ANTHROPIC_API_KEY must fail at import time (process startup),
    not surface as a per-request 503 -- see app/main.py.

    Isolated from a local `.env`: pydantic-settings falls through to a
    `backend/.env` file when the OS environment doesn't define the key
    (env vars only take precedence over the dotenv file when they're
    actually *set*), so popping the OS var alone would pass or fail
    depending on whether the developer's tree happens to have one. Running
    the subprocess from an empty directory means the `.env` lookup --
    resolved relative to cwd -- can never find one, regardless of the tree.
    """
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    env["PYTHONPATH"] = BACKEND_DIR

    with tempfile.TemporaryDirectory() as empty_cwd:
        result = subprocess.run(
            [sys.executable, "-c", "import app.main"],
            env=env,
            cwd=empty_cwd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    assert result.returncode != 0
    assert "ANTHROPIC_API_KEY is not set" in result.stderr


def test_startup_refuses_a_non_canonical_anthropic_base_url():
    """A configured base URL other than the Anthropic API host would send the
    API key elsewhere, so the process refuses to start (app/main.py).
    """
    env = os.environ.copy()
    env["ANTHROPIC_API_KEY"] = "test-key-for-pytest"
    env["ANTHROPIC_BASE_URL"] = "https://collector.example.net"
    env["PYTHONPATH"] = BACKEND_DIR

    with tempfile.TemporaryDirectory() as empty_cwd:
        result = subprocess.run(
            [sys.executable, "-c", "import app.main"],
            env=env,
            cwd=empty_cwd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    assert result.returncode != 0
    assert "ANTHROPIC_BASE_URL must be https://api.anthropic.com" in result.stderr
