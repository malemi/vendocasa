"""Client roles, registration and the sign-in email rate on the local Supabase stack.

Runs only when SUPABASE_STATUS_ENV names the file that
`npx supabase@3.4.0 status -o env` printed for the stack in supabase/config.toml,
after `alembic upgrade head` against the stack's database. The module starts
the backend itself (tests/e2e/serve.py) on port 8001. The local stack exposes
the `app` and `omi` schemas, so each refusal below comes from privileges.

The email-rate case uses up the stack's hourly sign-in email allowance; run
the browser journeys (frontend/e2e/) first, or restart the auth container.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import tomllib
import uuid
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, text

from app.db_url import sync_database_url

STATUS_ENV = os.environ.get("SUPABASE_STATUS_ENV")
pytestmark = pytest.mark.skipif(not STATUS_ENV, reason="SUPABASE_STATUS_ENV is not set")

BACKEND_DIR = Path(__file__).resolve().parents[2]
CONFIG = tomllib.loads((BACKEND_DIR.parent / "supabase" / "config.toml").read_text())
EXPOSED_SCHEMAS = CONFIG["api"]["schemas"]
EMAIL_LIMIT = CONFIG["auth"]["rate_limit"]["email_sent"]
BACKEND_PORT = 8001
HOOK_REFUSAL = "Questo indirizzo email non è accettato"


@pytest.fixture(scope="module")
def stack() -> dict[str, str]:
    from tests.e2e.serve import load_status

    return load_status(STATUS_ENV)


@pytest.fixture(scope="module")
def db(stack):
    engine = create_engine(sync_database_url(stack["DB_URL"]))
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def backend(stack, tmp_path_factory):
    log = (tmp_path_factory.mktemp("backend") / "serve.log").open("w")
    env = {**os.environ, "SUPABASE_STATUS_ENV": STATUS_ENV, "E2E_API_PORT": str(BACKEND_PORT)}
    process = subprocess.Popen([sys.executable, "-m", "tests.e2e.serve"], cwd=BACKEND_DIR, env=env,
                               stdout=log, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{BACKEND_PORT}"
    try:
        for _ in range(120):
            try:
                if httpx.get(f"{url}/api/health", timeout=1).status_code == 200:
                    break
            except httpx.TransportError:
                pass
            if process.poll() is not None:
                raise RuntimeError(f"the backend exited with {process.returncode}; see {log.name}")
            time.sleep(0.5)
        else:
            raise RuntimeError(f"the backend did not become healthy; see {log.name}")
        yield url
    finally:
        process.terminate()
        process.wait(timeout=15)
        log.close()


def public(stack) -> dict[str, str]:
    return {"apikey": stack["ANON_KEY"], "Authorization": f"Bearer {stack['ANON_KEY']}"}


def admin(stack) -> dict[str, str]:
    return {"apikey": stack["SERVICE_ROLE_KEY"], "Authorization": f"Bearer {stack['SERVICE_ROLE_KEY']}"}


def confirmed_account_token(stack, email: str) -> str:
    """Create a confirmed account through the admin API and return a session token."""
    created = httpx.post(f"{stack['API_URL']}/auth/v1/admin/users", headers=admin(stack),
                         json={"email": email, "email_confirm": True})
    assert created.status_code == 200, created.text
    link = httpx.post(f"{stack['API_URL']}/auth/v1/admin/generate_link", headers=admin(stack),
                      json={"type": "magiclink", "email": email})
    assert link.status_code == 200, link.text
    verified = httpx.post(f"{stack['API_URL']}/auth/v1/verify", headers=public(stack),
                          json={"type": "magiclink", "token_hash": link.json()["hashed_token"]})
    assert verified.status_code == 200, verified.text
    return verified.json()["access_token"]


def migrated_objects(db) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, list[str]]]]:
    """Relations and functions in exposed schemas that the migration role owns.

    Objects that belong to an extension (PostGIS's functions and
    spatial_ref_sys) are excluded by rule; the migrations do not create them.
    """
    with db.connect() as conn:
        relations = conn.execute(text("""
            SELECT n.nspname, c.relname, a.attname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = 1
            WHERE n.nspname = ANY(:schemas) AND c.relkind IN ('r', 'v', 'm', 'p', 'f')
              AND c.relowner = (SELECT oid FROM pg_roles WHERE rolname = current_user)
              AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_class'::regclass
                              AND d.objid = c.oid AND d.deptype = 'e')
            ORDER BY 1, 2
        """), {"schemas": EXPOSED_SCHEMAS}).all()
        functions = conn.execute(text("""
            SELECT n.nspname, p.proname, coalesce(p.proargnames, '{}')
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = ANY(:schemas)
              AND p.proowner = (SELECT oid FROM pg_roles WHERE rolname = current_user)
              AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_proc'::regclass
                              AND d.objid = p.oid AND d.deptype = 'e')
            ORDER BY 1, 2
        """), {"schemas": EXPOSED_SCHEMAS}).all()
    return [tuple(r) for r in relations], [(r[0], r[1], list(r[2])) for r in functions]


def assert_privilege_refusal(response: httpx.Response, what: str) -> None:
    # 42501 is PostgreSQL's insufficient_privilege, so the request reached the
    # database through PostgREST and was refused there, not by the gateway.
    assert response.status_code in (401, 403), f"{what}: {response.status_code} {response.text[:200]}"
    assert response.json().get("code") == "42501", f"{what}: {response.text[:200]}"


def test_client_credentials_reach_no_migrated_object(stack, db):
    relations, functions = migrated_objects(db)
    names = {f"{schema}.{name}" for schema, name, _ in relations} | {f"{s}.{n}" for s, n, _ in functions}
    assert {"app.alembic_version", "app.spend_month", "app.spend_reservation", "app.service_flag",
            "app.disposable_email_domains", "omi.zones", "omi.quotations", "omi.transactions",
            "omi.semester_import", "app.before_user_created"} <= names

    user_token = confirmed_account_token(stack, f"roles-{uuid.uuid4().hex[:8]}@vendocasa.test")
    assert httpx.get(f"{stack['API_URL']}/auth/v1/user", headers={
        "apikey": stack["ANON_KEY"], "Authorization": f"Bearer {user_token}"}).status_code == 200
    credentials = {
        "public key": public(stack),
        "publishable key": {"apikey": stack["PUBLISHABLE_KEY"]},
        "user token": {"apikey": stack["ANON_KEY"], "Authorization": f"Bearer {user_token}"},
    }
    rest = f"{stack['API_URL']}/rest/v1"
    with httpx.Client(timeout=10) as client:
        for label, headers in credentials.items():
            for schema, name, column in relations:
                read = {**headers, "Accept-Profile": schema}
                write = {**headers, "Content-Profile": schema}
                what = f"{label} on {schema}.{name}"
                assert_privilege_refusal(client.get(f"{rest}/{name}", params={"select": "*"}, headers=read),
                                         f"{what} read")
                assert_privilege_refusal(client.post(f"{rest}/{name}", json={}, headers=write), f"{what} insert")
                assert_privilege_refusal(client.patch(f"{rest}/{name}", params={column: "is.null"},
                                                      json={column: None}, headers=write), f"{what} update")
                assert_privilege_refusal(client.delete(f"{rest}/{name}", params={column: "is.null"},
                                                       headers=write), f"{what} delete")
            for schema, name, args in functions:
                call = client.post(f"{rest}/rpc/{name}", json={a: None for a in args},
                                   headers={**headers, "Content-Profile": schema})
                assert_privilege_refusal(call, f"{label} executing {schema}.{name}")


def test_a_disposable_address_cannot_register(stack, db):
    emails = [f"otp-{uuid.uuid4().hex[:8]}@mailinator.com", f"signup-{uuid.uuid4().hex[:8]}@mailinator.com"]
    otp = httpx.post(f"{stack['API_URL']}/auth/v1/otp", headers=public(stack),
                     json={"email": emails[0], "create_user": True})
    signup = httpx.post(f"{stack['API_URL']}/auth/v1/signup", headers=public(stack),
                        json={"email": emails[1], "password": f"Pw-{uuid.uuid4().hex}"})
    for response in (otp, signup):
        assert response.status_code == 403, response.text
        assert HOOK_REFUSAL in response.json()["msg"]
    with db.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM auth.users WHERE email = ANY(:e)"),
                            {"e": emails}).scalar() == 0


def test_an_account_created_behind_the_hook_cannot_use_the_backend(stack, backend):
    # The admin API creates accounts without running the before-user-created hook.
    disposable = confirmed_account_token(stack, f"admin-{uuid.uuid4().hex[:8]}@mailinator.com")
    ordinary = confirmed_account_token(stack, f"ordinary-{uuid.uuid4().hex[:8]}@vendocasa.test")
    refused = httpx.get(f"{backend}/api/transactions", headers={"Authorization": f"Bearer {disposable}"})
    assert refused.status_code == 403
    assert refused.json()["detail"]["error"] == "disposable_email"
    accepted = httpx.get(f"{backend}/api/transactions", headers={"Authorization": f"Bearer {ordinary}"})
    assert accepted.status_code == 200


def test_sign_in_emails_stop_at_the_rate_limit(stack):
    tag = uuid.uuid4().hex[:8]
    addresses = [f"rate-{tag}-{i}@vendocasa.test" for i in range(EMAIL_LIMIT + 1)]
    accepted = 0
    refusal = None
    for address in addresses:
        response = httpx.post(f"{stack['API_URL']}/auth/v1/otp", headers=public(stack),
                              json={"email": address, "create_user": True})
        if response.status_code == 200:
            accepted += 1
            continue
        refusal = response
        break
    # Earlier sign-ins this hour may have used part of the allowance.
    assert refusal is not None, f"{accepted} sign-in emails accepted; the limit is {EMAIL_LIMIT}"
    assert accepted <= EMAIL_LIMIT
    assert refusal.status_code == 429
    assert refusal.json()["error_code"] == "over_email_send_rate_limit"
    delivered = httpx.get(f"{stack['MAILPIT_URL']}/api/v1/search", params={"query": f"rate-{tag}"}).json()
    assert delivered["messages_count"] == accepted
