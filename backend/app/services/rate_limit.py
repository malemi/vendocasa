"""Rate limiting for the chat and upload endpoints.

Both endpoints require a verified account (backend/app/auth.py), and chat
calls a paid Anthropic model. This module enforces three independent ceilings:

  - requests per minute, per identity
  - requests per day, per identity
  - Anthropic model calls per day, service-wide (a circuit breaker)

An "identity" is the pair (account ID, client IP). Both are checked
independently and a request is blocked if either exceeds its ceiling. The
account limit is primary; the IP limit is a backstop that also slows one
person who switches between several accounts from the same address, since
the IP-keyed counters are untouched by a different account.

Storage sits behind the `RateLimitStore` interface. `InMemoryRateLimitStore`
is correct for a single worker process. Railway runs this backend as a
single uvicorn worker (see `backend/Dockerfile` -- no `--workers` flag), so
in-process storage is consistent for the whole deployment today. Swapping
in a shared store (e.g. Redis) later means implementing `RateLimitStore`
and changing the `rate_limiter` construction below -- no call site changes.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from threading import Lock

from fastapi import Request

from app.config import settings

_MINUTE = 60
_DAY = 24 * 60 * 60

_GLOBAL_MODEL_CALLS_KEY = "global:model_calls:day"


@dataclass(frozen=True)
class RateLimitDecision:
    """The result of a rate-limit check."""

    allowed: bool
    retry_after_seconds: int = 0
    reason: str = ""


class RateLimitStore(ABC):
    """Fixed-window counters keyed by an arbitrary string bucket."""

    @abstractmethod
    def hit(self, key: str, window_seconds: int, limit: int) -> tuple[bool, int]:
        """Record one hit against `key` and report whether it stayed within `limit`.

        Returns (allowed, retry_after_seconds). `retry_after_seconds` is 0 when
        allowed, otherwise the number of seconds until the current window resets.
        """

    @abstractmethod
    def peek(self, key: str, window_seconds: int, limit: int) -> bool:
        """Report whether `key` is currently within `limit`, without recording a hit."""


class InMemoryRateLimitStore(RateLimitStore):
    """Fixed-window counters held in process memory.

    Correct for a single worker process (the current deployment). Not
    shared across replicas or process restarts -- acceptable for a
    single-worker deployment, a real gap the moment a second worker or
    replica is added. Thread-safe via a single lock; contention is not a
    concern at this traffic volume.
    """

    # Sweep expired windows every this many `hit` calls. Many identities
    # (accounts and client addresses) are otherwise a slow memory leak: nothing ever deletes an entry once its window has passed.
    _SWEEP_EVERY = 500

    def __init__(self) -> None:
        self._lock = Lock()
        # key -> (window_start_epoch_seconds, count, window_seconds)
        # window_seconds is stored per-entry so a sweep can tell whether any
        # given key has expired without the caller having to pass it in.
        self._windows: dict[str, tuple[float, int, int]] = {}
        self._hits_since_sweep = 0

    def _sweep_expired_locked(self, now: float) -> None:
        expired = [
            key
            for key, (window_start, _count, window_seconds) in self._windows.items()
            if now - window_start >= window_seconds
        ]
        for key in expired:
            del self._windows[key]

    def hit(self, key: str, window_seconds: int, limit: int) -> tuple[bool, int]:
        now = time.time()
        with self._lock:
            self._hits_since_sweep += 1
            if self._hits_since_sweep >= self._SWEEP_EVERY:
                self._sweep_expired_locked(now)
                self._hits_since_sweep = 0

            window_start, count, _ = self._windows.get(key, (now, 0, window_seconds))
            elapsed = now - window_start
            if elapsed >= window_seconds:
                window_start, count, elapsed = now, 0, 0.0
            count += 1
            self._windows[key] = (window_start, count, window_seconds)
            if count > limit:
                retry_after = max(1, int(window_seconds - elapsed))
                return False, retry_after
            return True, 0

    def peek(self, key: str, window_seconds: int, limit: int) -> bool:
        now = time.time()
        with self._lock:
            window_start, count, _ = self._windows.get(key, (now, 0, window_seconds))
            if now - window_start >= window_seconds:
                return True
            return count < limit


class RateLimiter:
    """Applies the three ceilings using a `RateLimitStore`."""

    def __init__(self, store: RateLimitStore) -> None:
        self._store = store

    def check_identity(self, account_id: str, ip: str) -> RateLimitDecision:
        """Enforce per-minute and per-day ceilings, keyed on both account and IP.

        Checking both independently -- rather than combining them into one
        key -- means a client that switches to another account from the same
        address is still constrained by the IP-keyed counters, which do not
        reset.
        """
        checks = [
            (f"acct:{account_id}:minute", _MINUTE, settings.rate_limit_per_minute, "per-minute"),
            (f"ip:{ip}:minute", _MINUTE, settings.rate_limit_per_minute, "per-minute"),
            (f"acct:{account_id}:day", _DAY, settings.rate_limit_per_day, "per-day"),
            (f"ip:{ip}:day", _DAY, settings.rate_limit_per_day, "per-day"),
        ]
        for key, window, limit, label in checks:
            allowed, retry_after = self._store.hit(key, window, limit)
            if not allowed:
                return RateLimitDecision(False, retry_after, f"{label} limit exceeded")
        return RateLimitDecision(True)

    def check_route(self, account_id: str) -> RateLimitDecision:
        """Per-minute ceiling for routes that cost no provider money."""
        allowed, retry_after = self._store.hit(
            f"acct:{account_id}:route:minute", _MINUTE, settings.route_requests_per_minute
        )
        if not allowed:
            return RateLimitDecision(False, retry_after, "per-minute route limit exceeded")
        return RateLimitDecision(True)

    def peek_global_model_calls(self) -> RateLimitDecision:
        """Check the global daily model-call ceiling without consuming it.

        Used as a door-level gate: if the service has already exhausted its
        daily budget, reject new chat requests before they start streaming.
        """
        allowed = self._store.peek(
            _GLOBAL_MODEL_CALLS_KEY, _DAY, settings.rate_limit_global_daily_model_calls
        )
        if not allowed:
            return RateLimitDecision(False, reason="global daily model-call ceiling reached")
        return RateLimitDecision(True)

    def record_model_call(self) -> RateLimitDecision:
        """Record one actual Anthropic API call against the global daily ceiling."""
        allowed, retry_after = self._store.hit(
            _GLOBAL_MODEL_CALLS_KEY, _DAY, settings.rate_limit_global_daily_model_calls
        )
        if not allowed:
            return RateLimitDecision(False, retry_after, "global daily model-call ceiling reached")
        return RateLimitDecision(True)


def get_client_ip(request: Request) -> str:
    """Return the client address from a value the caller cannot forge.

    Invariant: we only trust values the caller cannot have written under an
    appending proxy. `X-Forwarded-For` is a comma-separated list the caller
    can prepend arbitrary entries to; an appending proxy (Railway's Envoy
    edge included) puts the hop it actually observed at the END of the
    header and leaves everything to its left as whatever the client sent.
    Trusting the LEFTMOST entry lets any caller pick its own rate-limit
    identity by sending a fake leftmost address and no cookie.

    `X-Envoy-External-Address` is deliberately NOT in this chain: its safety
    depends on an unproven assumption that only a trusted edge can set it,
    and a forged one alone reopens the bypass whenever XFF is absent from a
    request that reaches this process directly. The rightmost XFF hop needs
    no such assumption -- under any appending proxy it is written by the
    last hop, not the caller -- and Vendocasa has no CDN in front of
    Railway, so there is no multi-proxy scenario where it would degrade to
    a shared proxy IP.

    Preference order:
      1. The RIGHTMOST `X-Forwarded-For` entry -- the last hop appended by
         a trusted proxy, correct regardless of how many hops preceded it.
      2. `request.client.host` -- no proxy in front (local development, or
         a request that reached this process directly).
    """
    # getlist, not get: with duplicate X-Forwarded-For header LINES, get()
    # returns only the first line -- which is the caller's under an appending
    # proxy. Joining all lines keeps the rightmost hop rightmost.
    forwarded = ",".join(request.headers.getlist("x-forwarded-for"))
    if forwarded:
        hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
        if hops:
            return hops[-1]

    return request.client.host if request.client else "unknown"


# Process-wide singleton. Swap the store implementation here to move to a
# shared backend later -- call sites only ever use `rate_limiter`.
rate_limiter = RateLimiter(InMemoryRateLimitStore())
