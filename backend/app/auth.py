"""Account authentication for every API route except the health check.

The frontend signs users in with Supabase Auth (email sign-in links) and sends
the session's access token as `Authorization: Bearer <token>`. `AuthMiddleware`
verifies that token before the request body is read, so an unauthenticated
request never reaches body parsing or a route handler. Route handlers read the
verified account through the `current_account` and `require_owner` dependencies.

The accepted signing algorithm comes from configuration, never from the token
header. With asymmetric keys the verifier uses the project's JWKS and refetches
an unknown key ID at most once per JWKS_MIN_REFETCH_SECONDS.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass

import httpx
import jwt
from fastapi import Depends, HTTPException, Request
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import settings
from app.refusals import refusal
from app.services.disposable_domains import is_disposable

logger = logging.getLogger(__name__)

PUBLIC_API_PATHS = frozenset({"/api/health"})
AUDIENCE = "authenticated"
JWKS_MIN_REFETCH_SECONDS = 60
JWKS_RETRY_AFTER_FAILURE_SECONDS = 5
JWKS_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class Account:
    """A verified account: the token subject and its confirmed email."""

    id: str
    email: str

    @property
    def is_owner(self) -> bool:
        return bool(settings.owner_user_id) and self.id == settings.owner_user_id


class AuthFailure(Exception):
    def __init__(self, code: str, status_code: int = 401) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def token_issuer() -> str:
    return f"{settings.supabase_url.rstrip('/')}/auth/v1"


class JwksCache:
    """Signing keys from the identity service's JWKS endpoint, by key ID.

    A token is called invalid only after a SUCCESSFUL fetch shows its key ID is
    not the project's. While fetching fails, requests get `auth_unavailable`
    (503) and the fetch is retried at most every JWKS_RETRY_AFTER_FAILURE_SECONDS;
    a valid session is never refused as invalid because the key server was down.
    """

    def __init__(self) -> None:
        self._keys: dict[str, object] = {}
        self._fetched_at: float | None = None
        self._failed_at: float | None = None
        self._lock = asyncio.Lock()

    def clear(self) -> None:
        self._keys = {}
        self._fetched_at = None
        self._failed_at = None

    async def key_for(self, kid: str) -> object:
        if kid in self._keys:
            return self._keys[kid]
        async with self._lock:
            if kid in self._keys:
                return self._keys[kid]
            now = time.monotonic()
            if self._fetched_at is not None and now - self._fetched_at < JWKS_MIN_REFETCH_SECONDS:
                raise AuthFailure("invalid_token")  # fresh keys, and this ID is not among them
            if self._failed_at is not None and now - self._failed_at < JWKS_RETRY_AFTER_FAILURE_SECONDS:
                raise AuthFailure("auth_unavailable", 503)
            await self._refresh()
            if kid not in self._keys:
                raise AuthFailure("invalid_token")
            return self._keys[kid]

    async def _refresh(self) -> None:
        url = f"{token_issuer()}/.well-known/jwks.json"
        try:
            async with httpx.AsyncClient(timeout=JWKS_TIMEOUT_SECONDS) as client:
                response = await client.get(url)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            self._failed_at = time.monotonic()
            logger.error("JWKS fetch from %s failed: %s", url, type(exc).__name__)
            raise AuthFailure("auth_unavailable", 503) from exc
        keys: dict[str, object] = {}
        for jwk in payload.get("keys", []):
            kid = jwk.get("kid")
            if not kid or jwk.get("alg", settings.supabase_jwt_algorithm) != settings.supabase_jwt_algorithm:
                continue
            try:
                keys[kid] = jwt.PyJWK(jwk).key
            except jwt.PyJWTError:
                logger.warning("Ignoring unusable JWKS key %s", kid)
        self._keys = keys
        self._fetched_at = time.monotonic()
        self._failed_at = None


jwks_cache = JwksCache()


async def verify_token(token: str) -> Account:
    """Verify an access token and return its account, or raise AuthFailure."""
    algorithm = settings.supabase_jwt_algorithm
    if not settings.supabase_url:
        raise AuthFailure("auth_unavailable", 503)
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise AuthFailure("invalid_token") from exc

    if algorithm == "HS256":
        if not settings.supabase_jwt_secret:
            raise AuthFailure("auth_unavailable", 503)
        key: object = settings.supabase_jwt_secret
    else:
        kid = header.get("kid")
        if not kid:
            raise AuthFailure("invalid_token")
        key = await jwks_cache.key_for(kid)

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            audience=AUDIENCE,
            issuer=token_issuer(),
            options={"require": ["exp", "sub", "aud", "iss"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthFailure("session_expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthFailure("invalid_token") from exc

    if claims.get("is_anonymous") or claims.get("role") != "authenticated":
        raise AuthFailure("invalid_token")
    email = str(claims.get("email") or "").strip().lower()
    if "@" not in email:
        raise AuthFailure("invalid_token")
    try:
        disposable = await is_disposable(email)
    except Exception as exc:  # the domain list is unavailable: fail closed
        logger.error("Disposable-domain list unavailable: %s", type(exc).__name__)
        raise AuthFailure("auth_unavailable", 503) from exc
    if disposable:
        raise AuthFailure("disposable_email", 403)
    return Account(id=str(claims["sub"]), email=email)


async def _send_refusal(send: Send, failure: AuthFailure) -> None:
    body = json.dumps({"detail": refusal(failure.code)}, ensure_ascii=False).encode()
    headers = [
        (b"content-type", b"application/json; charset=utf-8"),
        (b"content-length", str(len(body)).encode()),
    ]
    if failure.status_code == 401:
        headers.append((b"www-authenticate", b"Bearer"))
    await send({"type": "http.response.start", "status": failure.status_code, "headers": headers})
    await send({"type": "http.response.body", "body": body})


class AuthMiddleware:
    """Verify the bearer token of every /api/ request except PUBLIC_API_PATHS.

    Runs before the route reads the body. CORS preflight requests are answered
    by the outer CORS middleware and never reach this one.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        if (
            scope["type"] != "http"
            or not path.startswith("/api/")
            or path in PUBLIC_API_PATHS
            or scope.get("method") == "OPTIONS"
        ):
            await self.app(scope, receive, send)
            return

        scheme, _, token = Headers(scope=scope).get("authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            await _send_refusal(send, AuthFailure("not_authenticated"))
            return
        try:
            account = await verify_token(token.strip())
        except AuthFailure as failure:
            await _send_refusal(send, failure)
            return

        scope.setdefault("state", {})["account"] = account
        await self.app(scope, receive, send)


def current_account(request: Request) -> Account:
    """The verified account of this request (set by AuthMiddleware)."""
    account = getattr(request.state, "account", None)
    if not isinstance(account, Account):
        raise HTTPException(status_code=401, detail=refusal("not_authenticated"))
    return account


def require_owner(account: Account = Depends(current_account)) -> Account:
    """Allow only the service owner (OWNER_USER_ID)."""
    if not account.is_owner:
        raise HTTPException(status_code=403, detail=refusal("owner_only"))
    return account
