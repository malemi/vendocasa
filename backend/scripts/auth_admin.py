"""Accounts through the identity service's admin API, for deployment work.

Runs inside the backend image as a one-off container on the server deployment
(deploy/compose.yaml), where Auth's admin API is reachable only on the
project's networks:

    docker compose run --rm --env-file <admin.env> backend \
        python -m scripts.auth_admin create-user --email owner@example.com

Environment:
- AUTH_ADMIN_URL: the Auth server's own address, for example http://auth:9999.
  A gateway address ending in /auth/v1 works too.
- SERVICE_ROLE_KEY: a token with role service_role. It is never printed.

Commands:
- create-user: an already confirmed account; prints its ID. An existing
  account for the address is reused, and its ID printed.
- delete-user: deletes the account for the address, if it exists.
- exists: prints "present" or "absent".
- session: prints an access token for an existing account. It generates a
  sign-in link and verifies it, so no email is sent. The token is a
  credential for one hour: the caller keeps it out of logs.
- otp-length: prints the length of the one-time code behind a generated
  link, and whether it is all digits. The code itself is never printed.
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx

TIMEOUT_SECONDS = 15


class AdminError(Exception):
    pass


def _base() -> str:
    url = os.environ.get("AUTH_ADMIN_URL", "").rstrip("/")
    if not url:
        raise AdminError("AUTH_ADMIN_URL is not set")
    return url


def _headers() -> dict[str, str]:
    key = os.environ.get("SERVICE_ROLE_KEY", "")
    if not key:
        raise AdminError("SERVICE_ROLE_KEY is not set")
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def _check(response: httpx.Response, what: str) -> dict:
    if response.status_code >= 400:
        # The body is Auth's error message; it carries no credential.
        raise AdminError(f"{what}: HTTP {response.status_code}: {response.text[:300]}")
    return response.json() if response.content else {}


def find_user_id(client: httpx.Client, email: str) -> str | None:
    page = 1
    while True:
        listing = _check(
            client.get(f"{_base()}/admin/users", headers=_headers(), params={"page": page, "per_page": 200}),
            "list users",
        )
        users = listing.get("users", [])
        for user in users:
            if (user.get("email") or "").lower() == email.lower():
                return user["id"]
        if not users:
            return None
        page += 1


def create_user(client: httpx.Client, email: str) -> str:
    response = client.post(
        f"{_base()}/admin/users", headers=_headers(), json={"email": email, "email_confirm": True}
    )
    if response.status_code == 422:
        existing = find_user_id(client, email)
        if existing:
            return existing
    return _check(response, f"create {email}")["id"]


def delete_user(client: httpx.Client, email: str) -> bool:
    user_id = find_user_id(client, email)
    if user_id is None:
        return False
    _check(client.delete(f"{_base()}/admin/users/{user_id}", headers=_headers()), f"delete {email}")
    return True


def generated_link(client: httpx.Client, email: str) -> dict:
    return _check(
        client.post(f"{_base()}/admin/generate_link", headers=_headers(), json={"type": "magiclink", "email": email}),
        f"generate a link for {email}",
    )


def session_token(client: httpx.Client, email: str) -> str:
    link = generated_link(client, email)
    verified = _check(
        client.post(f"{_base()}/verify", json={"type": "magiclink", "token_hash": link["hashed_token"]}),
        f"verify the link for {email}",
    )
    token = verified.get("access_token")
    if not token:
        raise AdminError(f"verify for {email} returned no access token")
    return token


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["create-user", "delete-user", "exists", "session", "otp-length"])
    parser.add_argument("--email", required=True)
    args = parser.parse_args(argv)

    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            if args.command == "create-user":
                print(create_user(client, args.email))
            elif args.command == "delete-user":
                print("deleted" if delete_user(client, args.email) else "absent")
            elif args.command == "exists":
                print("present" if find_user_id(client, args.email) else "absent")
            elif args.command == "session":
                print(session_token(client, args.email))
            else:
                code = generated_link(client, args.email).get("email_otp") or ""
                print(f"length={len(code)} digits={code.isdigit()}")
    except (AdminError, httpx.HTTPError) as exc:
        print(f"auth_admin: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
