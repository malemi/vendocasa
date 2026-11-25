"""Request quotas as route dependencies (backend/app/services/rate_limit.py)."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from app.auth import Account, current_account
from app.refusals import refusal
from app.services.rate_limit import get_client_ip, rate_limiter


def _refuse(retry_after: int) -> HTTPException:
    return HTTPException(status_code=429, detail=refusal("rate_limited"),
                         headers={"Retry-After": str(retry_after)})


def route_quota(account: Account = Depends(current_account)) -> None:
    """60 requests per minute per account (ROUTE_REQUESTS_PER_MINUTE)."""
    decision = rate_limiter.check_route(account.id)
    if not decision.allowed:
        raise _refuse(decision.retry_after_seconds)


def identity_quota(request: Request, account: Account = Depends(current_account)) -> None:
    """The chat-level per-account and per-IP limits, for routes that reach
    paid or rate-limited third-party services (the geocoders)."""
    decision = rate_limiter.check_identity(account.id, get_client_ip(request))
    if not decision.allowed:
        raise _refuse(decision.retry_after_seconds)
