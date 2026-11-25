"""Access tokens shaped like Supabase's, signed with the test secret (see conftest.py)."""

from __future__ import annotations

import time
import uuid

import jwt

from app.auth import token_issuer
from app.config import settings

OWNER_ID = "00000000-0000-4000-8000-00000000000a"


def make_token(sub: str | None = None, email: str | None = None, **overrides) -> str:
    """Mint an access token shaped like Supabase's, signed with the test secret."""
    now = int(time.time())
    sub = sub or str(uuid.uuid4())
    claims = {
        "sub": sub,
        "email": email if email is not None else f"user-{sub[:8]}@example.com",
        "aud": "authenticated",
        "iss": token_issuer(),
        "role": "authenticated",
        "is_anonymous": False,
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, settings.supabase_jwt_secret, algorithm="HS256")


def auth_headers(sub: str | None = None, email: str | None = None, **overrides) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(sub, email, **overrides)}"}
