#!/usr/bin/env python3
"""Generate one VendoCasa project's secrets and environment files.

    deploy/make_secrets.py --rehearsal
    deploy/make_secrets.py --production --hostname vendocasa.example.org
    deploy/make_secrets.py --project vendocasa --owner-user-id <uuid>

Writes ~/.config/vendocasa/<project>/, mode 0700, with files of mode 0600:
- db.env, auth.env, backend.env, admin.env: each service's secrets;
- compose.env: the project's settings for deploy/compose.sh (no secret: the
  public client key is public);
- host-site.caddy: deploy/host-site.caddy rendered for the project;
- generated.env: the generated values, created once and kept on later runs;
- status.container.env and status.host.env (rehearsal only): the browser
  journeys' status files, inside the backend container and on the host.

The project is vendocasa-rehearsal (loopback rehearsal: mail goes to Mailpit,
and the provider key is a placeholder that is never sent) or vendocasa
(production: the operator's values come from ~/.config/vendocasa/secrets.env).
The two never share a generated value. The tool prints names and lengths,
never values. Python standard library only.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = Path.home() / ".config" / "vendocasa"
TEN_YEARS = 10 * 365 * 24 * 3600

PROJECTS = {
    "vendocasa-rehearsal": {
        "public_url": "http://127.0.0.1:8098",
        "site_address": "http://127.0.0.1:8098",
        "web_port": "8095",
        "admin_port": "8099",
        "mailpit_port": "8096",
        "edge_subnet": "172.31.95.0/24",
        "edge_gateway": "172.31.95.1",
    },
    "vendocasa": {
        "web_port": "8094",
        "edge_subnet": "172.31.94.0/24",
        "edge_gateway": "172.31.94.1",
    },
}
OPERATOR_KEYS = ("ANTHROPIC_API_KEY", "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "SMTP_SENDER")


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and not key.strip().startswith("#"):
                values[key.strip()] = unquote(value)
    return values


def write_private(path: Path, text: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(text)
    os.chmod(path, 0o600)


def write_env(path: Path, values: dict[str, str], quoted: bool = True) -> None:
    """Write KEY=value lines. Quoted: single quotes, which Compose takes literally,
    so a `$` or ` #` in an operator's password reaches the service unchanged.
    The status files stay unquoted for their own readers (serve.py, stack.ts)."""
    for key, value in values.items():
        if "\n" in value or "'" in value:
            raise SystemExit(f"make_secrets.py: {key} contains a newline or a single quote")
    lines = "".join(f"{k}='{v}'\n" if quoted else f"{k}={v}\n" for k, v in values.items())
    write_private(path, lines)
    print(f"{path.name}: " + ", ".join(f"{k}({len(v)})" for k, v in values.items()))


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def hs256_token(secret: str, claims: dict) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = b64url(json.dumps(claims, separators=(",", ":")).encode())
    signature = hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{b64url(signature)}"


def generated(directory: Path) -> dict[str, str]:
    path = directory / "generated.env"
    values = read_env(path)
    for key in ("POSTGRES_PASSWORD", "AUTH_DB_PASSWORD"):
        values.setdefault(key, secrets.token_urlsafe(32))
    values.setdefault("JWT_SECRET", secrets.token_urlsafe(48))
    issued = int(values.setdefault("KEYS_ISSUED_AT", str(int(time.time()))))
    values.setdefault("ANON_KEY", hs256_token(values["JWT_SECRET"], {
        "iss": "vendocasa", "role": "anon", "iat": issued, "exp": issued + TEN_YEARS}))
    values.setdefault("SERVICE_ROLE_KEY", hs256_token(values["JWT_SECRET"], {
        "iss": "vendocasa", "role": "service_role", "iat": issued, "exp": issued + TEN_YEARS}))
    write_env(path, values)
    return values


def render_host_site(site_address: str, upstream: str) -> str:
    template = (HERE / "host-site.caddy").read_text()
    lines = [line for line in template.splitlines() if not line.startswith("#")]
    text = "\n".join(lines).strip() + "\n"
    if text.count("SITE_ADDRESS") != 1 or text.count("UPSTREAM") != 1:
        raise SystemExit("make_secrets.py: host-site.caddy must name SITE_ADDRESS and UPSTREAM once each")
    return text.replace("SITE_ADDRESS", site_address).replace("UPSTREAM", upstream)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a VendoCasa project's secrets and environment files.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--rehearsal", action="store_true", help="the loopback rehearsal, vendocasa-rehearsal")
    mode.add_argument("--production", action="store_true", help="production, vendocasa")
    mode.add_argument("--project", choices=sorted(PROJECTS), help="update an existing project (with --owner-user-id)")
    parser.add_argument("--hostname", help="production's public hostname")
    parser.add_argument("--owner-user-id", help="record the owner's account ID in backend.env")
    args = parser.parse_args(argv)

    project = "vendocasa-rehearsal" if args.rehearsal else "vendocasa" if args.production else args.project
    directory = CONFIG / project
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(CONFIG, 0o700)
    os.chmod(directory, 0o700)

    if args.project:
        if not args.owner_user_id:
            parser.error("--project needs --owner-user-id")
        backend = read_env(directory / "backend.env")
        if not backend:
            raise SystemExit(f"make_secrets.py: {directory}/backend.env is missing; generate the project first")
        backend["OWNER_USER_ID"] = args.owner_user_id
        write_env(directory / "backend.env", backend)
        return 0

    settings = dict(PROJECTS[project])
    if args.production:
        if not args.hostname or "/" in args.hostname or ":" in args.hostname:
            parser.error("--production needs --hostname, a bare hostname")
        settings["public_url"] = f"https://{args.hostname}"
        settings["site_address"] = args.hostname
        operator = read_env(CONFIG / "secrets.env")
        missing = [k for k in OPERATOR_KEYS if not operator.get(k)]
        if missing:
            raise SystemExit(f"make_secrets.py: {CONFIG / 'secrets.env'} lacks {', '.join(missing)}")
    else:
        operator = {
            "ANTHROPIC_API_KEY": "rehearsal-key-never-sent",
            "SMTP_HOST": "mailpit", "SMTP_PORT": "1025",
            "SMTP_USER": "rehearsal", "SMTP_PASS": "rehearsal",
            "SMTP_SENDER": "noreply@vendocasa.test",
        }

    values = generated(directory)
    owner = read_env(directory / "backend.env").get("OWNER_USER_ID", "")
    public_url = settings["public_url"]

    write_env(directory / "db.env", {
        "POSTGRES_PASSWORD": values["POSTGRES_PASSWORD"],
        "AUTH_DB_PASSWORD": values["AUTH_DB_PASSWORD"],
    })
    write_env(directory / "auth.env", {
        "GOTRUE_DB_DATABASE_URL": f"postgres://supabase_auth_admin:{values['AUTH_DB_PASSWORD']}@db:5432/postgres",
        "GOTRUE_JWT_SECRET": values["JWT_SECRET"],
        "GOTRUE_SMTP_HOST": operator["SMTP_HOST"],
        "GOTRUE_SMTP_PORT": operator["SMTP_PORT"],
        "GOTRUE_SMTP_USER": operator["SMTP_USER"],
        "GOTRUE_SMTP_PASS": operator["SMTP_PASS"],
        "GOTRUE_SMTP_ADMIN_EMAIL": operator["SMTP_SENDER"],
    })
    write_env(directory / "backend.env", {
        "DATABASE_URL": f"postgresql+psycopg://postgres:{values['POSTGRES_PASSWORD']}@db:5432/postgres",
        "ANTHROPIC_API_KEY": operator["ANTHROPIC_API_KEY"],
        "SUPABASE_JWT_SECRET": values["JWT_SECRET"],
        "OWNER_USER_ID": owner,
    })
    write_env(directory / "admin.env", {
        "AUTH_ADMIN_URL": "http://auth:9999",
        "SERVICE_ROLE_KEY": values["SERVICE_ROLE_KEY"],
    })
    compose = {
        "VENDOCASA_SECRETS_DIR": str(directory),
        "PUBLIC_URL": public_url,
        "WEB_PORT": settings["web_port"],
        "EDGE_SUBNET": settings["edge_subnet"],
        "EDGE_GATEWAY": settings["edge_gateway"],
        "ANON_KEY": values["ANON_KEY"],
    }
    existing = read_env(directory / "compose.env")
    for key in ("BACKEND_TAG", "WEB_TAG"):  # written by deploy/build.sh
        if existing.get(key):
            compose[key] = existing[key]
    if args.rehearsal:
        compose["ADMIN_PORT"] = settings["admin_port"]
        compose["MAILPIT_PORT"] = settings["mailpit_port"]
    write_env(directory / "compose.env", compose)
    write_private(directory / "host-site.caddy",
                  render_host_site(settings["site_address"], f"127.0.0.1:{settings['web_port']}"))
    print("host-site.caddy: rendered")

    if args.rehearsal:
        common = {
            "ANON_KEY": values["ANON_KEY"],
            "SERVICE_ROLE_KEY": values["SERVICE_ROLE_KEY"],
            "JWT_ALGORITHM": "HS256",
            "JWT_SECRET": values["JWT_SECRET"],
        }
        write_env(directory / "status.container.env", {
            "DB_URL": f"postgresql://postgres:{values['POSTGRES_PASSWORD']}@db:5432/postgres",
            "API_URL": "http://web:8081",
            "ISSUER_BASE_URL": public_url,
            "MAILPIT_URL": "http://mailpit:8025",
            **common,
        }, quoted=False)
        write_env(directory / "status.host.env", {
            "API_URL": f"http://127.0.0.1:{settings['admin_port']}",
            "APP_URL": public_url,
            "MAILPIT_URL": f"http://127.0.0.1:{settings['mailpit_port']}",
            **common,
        }, quoted=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
