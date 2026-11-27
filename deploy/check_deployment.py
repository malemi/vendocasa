#!/usr/bin/env python3
"""Access, exposure and client-identity checks of a VendoCasa deployment.

    deploy/check_deployment.py --project vendocasa-rehearsal --base-url http://127.0.0.1:8098 \
        --account-domain vendocasa.test [--email-rate]
    deploy/check_deployment.py --project vendocasa --base-url https://<hostname> \
        --account-domain <a domain the operator controls>

Requests go to --base-url, the first proxy: the rehearsal's stand-in, or the
host Caddy through the public hostname. Each request is bound to a chosen
local source address (127.0.0.2, .3, .4): over loopback the server reaches its
own public address from them, so the first proxy sees distinct clients.

Checks, all under the production request limits:
1. every registered /api route except /api/health refuses without a token;
2. Supabase's other API prefixes and Auth's admin API answer 404;
3. Auth's public settings: email only, no autoconfirm, no anonymous sign-in;
4. a direct sign-up (/signup and /otp) with a listed disposable domain is
   refused, and no account appears;
5. the one-time code behind a generated link has 10 digits;
6. backend client identity: two accounts send three uploads each from
   127.0.0.2, every request with a different forged X-Forwarded-For. The sixth
   is refused; an upload from 127.0.0.3 by a third account is accepted;
7. Auth client identity: 31 verifications with invalid codes from 127.0.0.2,
   each with a forged header; the last are refused with 429, and one from
   127.0.0.3 is not;
8. with --email-rate (rehearsal only, after an Auth restart): sign-in requests
   for 21 new addresses from 127.0.0.4 send 20 emails, and the 21st is refused.

Accounts are created and deleted through backend/scripts/auth_admin.py in a
one-off backend container; the service key reaches it through the
environment, and session tokens are never printed. Exit status 1 when any
check fails. Python standard library only.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import secrets
import ssl
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = Path.home() / ".config" / "vendocasa"
TINY_PDF = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"
UNSERVED = ["/rest/v1/", "/rest/v1/zones", "/graphql/v1", "/storage/v1/object/x", "/realtime/v1/websocket",
            "/functions/v1/x", "/pg/query", "/auth/v1/admin", "/auth/v1/admin/users"]

failures: list[str] = []


def report(ok: bool, name: str, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'} {name}{': ' + detail if detail else ''}", flush=True)
    if not ok:
        failures.append(name)


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            values[key.strip()] = value
    return values


class Target:
    def __init__(self, base_url: str) -> None:
        parsed = urllib.parse.urlsplit(base_url)
        self.scheme = parsed.scheme
        self.host = parsed.hostname or ""
        self.port = parsed.port or (443 if parsed.scheme == "https" else 80)

    def request(self, method: str, path: str, *, source: str = "127.0.0.2", headers: dict | None = None,
                body: bytes | None = None) -> tuple[int, dict, bytes]:
        if self.scheme == "https":
            conn: http.client.HTTPConnection = http.client.HTTPSConnection(
                self.host, self.port, timeout=30, source_address=(source, 0), context=ssl.create_default_context())
        else:
            conn = http.client.HTTPConnection(self.host, self.port, timeout=30, source_address=(source, 0))
        try:
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            return response.status, {k.lower(): v for k, v in response.getheaders()}, response.read()
        finally:
            conn.close()

    def json(self, method: str, path: str, payload: dict, **kwargs) -> tuple[int, bytes]:
        status, _, data = self.request(method, path, body=json.dumps(payload).encode(),
                                       headers={"content-type": "application/json", **kwargs.pop("headers", {})},
                                       **kwargs)
        return status, data


class Admin:
    """auth_admin.py in a one-off backend container of the project."""

    def __init__(self, project: str) -> None:
        self.project = project
        self.env = {**os.environ, **read_env(CONFIG / project / "admin.env")}

    def run(self, *args: str) -> str:
        command = [str(HERE / "compose.sh"), self.project, "run", "--rm", "--no-deps", "-T",
                   "-e", "AUTH_ADMIN_URL", "-e", "SERVICE_ROLE_KEY", "backend",
                   "python", "-m", "scripts.auth_admin", *args]
        result = subprocess.run(command, env=self.env, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"auth_admin {args[0]} failed: {result.stderr.strip()[-400:]}")
        return result.stdout.strip().splitlines()[-1]

    def routes(self) -> list[tuple[str, str]]:
        # The generated OpenAPI schema lists every route however routers are
        # nested, as backend/tests/test_access.py reads it; app.routes holds
        # included routers, not their routes.
        code = ("from app.main import app\n"
                "for path, operations in app.openapi()['paths'].items():\n"
                "    for method in sorted(operations):\n"
                "        print(method.upper(), path)\n")
        command = [str(HERE / "compose.sh"), self.project, "run", "--rm", "--no-deps", "-T", "backend",
                   "python", "-c", code]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"route listing failed: {result.stderr.strip()[-400:]}")
        pairs = []
        for line in result.stdout.splitlines():
            method, _, path = line.partition(" ")
            if method in {"GET", "POST", "PUT", "PATCH", "DELETE"} and path.startswith("/api"):
                pairs.append((method, path))
        return pairs


def concrete(path: str) -> str:
    out = []
    for part in path.split("/"):
        out.append("1" if part.startswith("{") and part.endswith("}") else part)
    return "/".join(out)


def multipart_pdf() -> tuple[bytes, str]:
    boundary = "vendocasa" + secrets.token_hex(8)
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"check.pdf\"\r\n"
            f"Content-Type: application/pdf\r\n\r\n").encode() + TINY_PDF + f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


def check_anonymous(target: Target, admin: Admin) -> None:
    routes = admin.routes()
    report(len(routes) > 10, "route list", f"{len(routes)} method-and-path pairs")
    status, _, _ = target.request("GET", "/api/health")
    report(status == 200, "health is public", str(status))
    refused = []
    for method, path in routes:
        if path == "/api/health":
            continue
        body = b"{}" if method in {"POST", "PUT", "PATCH"} else None
        status, headers, _ = target.request(method, concrete(path), body=body,
                                            headers={"content-type": "application/json"} if body else {})
        if status != 401 or "bearer" not in headers.get("www-authenticate", "").lower():
            refused.append(f"{method} {path} -> {status}")
    report(not refused, "every protected route refuses without a token",
           "; ".join(refused) if refused else f"{len(routes) - 1} routes answered 401")


def check_unserved(target: Target) -> None:
    wrong = []
    for path in UNSERVED:
        status, _, _ = target.request("GET", path)
        if status != 404:
            wrong.append(f"{path} -> {status}")
    report(not wrong, "no Data API, storage, functions or admin API", "; ".join(wrong) or f"{len(UNSERVED)} paths 404")


def check_settings(target: Target) -> None:
    status, _, data = target.request("GET", "/auth/v1/settings")
    try:
        settings = json.loads(data)
    except ValueError:
        report(False, "auth settings", f"HTTP {status}, not JSON")
        return
    external = settings.get("external", {})
    enabled = sorted(name for name, on in external.items() if on)
    ok = (status == 200 and enabled == ["email"] and settings.get("disable_signup") is False
          and settings.get("mailer_autoconfirm") is False)
    report(ok, "auth settings: email only, signup open, confirmation required",
           f"enabled={enabled} disable_signup={settings.get('disable_signup')} "
           f"mailer_autoconfirm={settings.get('mailer_autoconfirm')}")


def check_disposable(target: Target, admin: Admin) -> None:
    domains = [line.strip() for line in (HERE.parent / "backend/data/disposable_domains.txt").read_text().splitlines()
               if line.strip() and not line.startswith("#")]
    domain = domains[len(domains) // 2]
    email = f"check-{secrets.token_hex(4)}@{domain}"
    otp_status, otp_body = target.json("POST", "/auth/v1/otp", {"email": email, "create_user": True}, source="127.0.0.4")
    signup_status, _ = target.json("POST", "/auth/v1/signup",
                                             {"email": email, "password": secrets.token_urlsafe(18)}, source="127.0.0.4")
    exists = admin.run("exists", "--email", email)
    ok = otp_status >= 400 and signup_status >= 400 and exists == "absent"
    report(ok, f"disposable domain refused ({domain})",
           f"otp={otp_status} signup={signup_status} account={exists}; "
           f"{otp_body[:120].decode(errors='replace')}")


def check_code_length(admin: Admin, email: str) -> None:
    line = admin.run("otp-length", "--email", email)
    report(line == "length=10 digits=True", "one-time code length", line)


def check_backend_identity(target: Target, admin: Admin, domain: str) -> None:
    tag = secrets.token_hex(3)
    emails = [f"identity-{tag}-{name}@{domain}" for name in ("a", "b", "c")]
    try:
        for email in emails:
            admin.run("create-user", "--email", email)
        tokens = [admin.run("session", "--email", email) for email in emails]
        statuses = []
        for i in range(6):
            body, content_type = multipart_pdf()
            status, _, _ = target.request("POST", "/api/documents/upload", source="127.0.0.2", body=body, headers={
                "authorization": f"Bearer {tokens[i % 2]}", "content-type": content_type,
                "x-forwarded-for": f"203.0.113.{10 + i}"})
            statuses.append(status)
        body, content_type = multipart_pdf()
        other, _, _ = target.request("POST", "/api/documents/upload", source="127.0.0.3", body=body, headers={
            "authorization": f"Bearer {tokens[2]}", "content-type": content_type})
        ok = statuses[:5] == [200] * 5 and statuses[5] == 429 and other == 200
        report(ok, "backend keys on the real client address",
               f"127.0.0.2 with forged headers: {statuses}; 127.0.0.3: {other}")
    finally:
        for email in emails:
            try:
                admin.run("delete-user", "--email", email)
            except RuntimeError as exc:
                report(False, f"delete {email}", str(exc))


def check_auth_identity(target: Target) -> None:
    statuses = []
    for i in range(31):
        status, _ = target.json("POST", "/auth/v1/verify", {"type": "magiclink", "token_hash": secrets.token_hex(28)},
                                source="127.0.0.2", headers={"x-forwarded-for": f"198.51.100.{10 + i}"})
        statuses.append(status)
    other, _ = target.json("POST", "/auth/v1/verify", {"type": "magiclink", "token_hash": secrets.token_hex(28)},
                           source="127.0.0.3")
    limited = [i for i, s in enumerate(statuses) if s == 429]
    ok = bool(limited) and statuses[-1] == 429 and all(s != 429 for s in statuses[:limited[0]]) and other != 429
    report(ok, "Auth limits verifications per real client address",
           f"127.0.0.2: first 429 at request {limited[0] + 1 if limited else None} of 31, last={statuses[-1]}; "
           f"127.0.0.3: {other}")


def check_email_rate(target: Target, domain: str) -> None:
    tag = secrets.token_hex(3)
    statuses = []
    for i in range(21):
        status, _ = target.json("POST", "/auth/v1/otp", {"email": f"rate-{tag}-{i}@{domain}", "create_user": True},
                                source="127.0.0.4")
        statuses.append(status)
    ok = statuses[:20] == [200] * 20 and statuses[20] == 429
    report(ok, "email rate: 20 an hour", f"statuses={statuses}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a VendoCasa deployment.")
    parser.add_argument("--project", required=True, choices=["vendocasa", "vendocasa-rehearsal"])
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--account-domain", required=True,
                        help="the domain of the test accounts; in production, one the operator controls")
    parser.add_argument("--code-email", help="an existing account whose generated link is read for the code length")
    parser.add_argument("--email-rate", action="store_true", help="rehearsal only, after an Auth restart")
    args = parser.parse_args(argv)
    if args.email_rate and args.project != "vendocasa-rehearsal":
        parser.error("--email-rate sends real emails; it runs only in the rehearsal")

    target = Target(args.base_url)
    admin = Admin(args.project)
    started = time.time()
    check_anonymous(target, admin)
    check_unserved(target)
    check_settings(target)
    check_disposable(target, admin)
    if args.code_email:
        check_code_length(admin, args.code_email)
    check_backend_identity(target, admin, args.account_domain)
    check_auth_identity(target)
    if args.email_rate:
        check_email_rate(target, args.account_domain)
    print(f"{len(failures)} failed, in {time.time() - started:.0f} s", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
