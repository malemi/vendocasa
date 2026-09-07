"""Rate limiting for the public chat endpoint.

The chat endpoint is public, unauthenticated, and calls a paid Anthropic
model on every message. This module enforces three independent ceilings:

  - requests per minute, per identity
  - requests per day, per identity
  - Anthropic model calls per day, service-wide (a circuit breaker)

An "identity" is the pair (vendocasa_uid cookie, client IP). Both are
checked independently and a request is blocked if either exceeds its
ceiling -- this is what keeps deleting the cookie from resetting the
budget, since the IP-keyed counters are untouched by a new cookie value.

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

    def __init__(self) -> None:
        self._lock = Lock()
        # key -> (window_start_epoch_seconds, count)
        self._windows: dict[str, tuple[float, int]] = {}

    def hit(self, key: str, window_seconds: int, limit: int) -> tuple[bool, int]:
        now = time.time()
        with self._lock:
            window_start, count = self._windows.get(key, (now, 0))
            elapsed = now - window_start
            if elapsed >= window_seconds:
                window_start, count, elapsed = now, 0, 0.0
            count += 1
            self._windows[key] = (window_start, count)
            if count > limit:
                retry_after = max(1, int(window_seconds - elapsed))
                return False, retry_after
            return True, 0

    def peek(self, key: str, window_seconds: int, limit: int) -> bool:
        now = time.time()
        with self._lock:
            window_start, count = self._windows.get(key, (now, 0))
            if now - window_start >= window_seconds:
                return True
            return count < limit


class RateLimiter:
    """Applies the three ceilings using a `RateLimitStore`."""

    def __init__(self, store: RateLimitStore) -> None:
        self._store = store

    def check_identity(self, uid: str, ip: str) -> RateLimitDecision:
        """Enforce per-minute and per-day ceilings, keyed on both uid and IP.

        Checking both independently -- rather than combining them into one
        key -- means a client that clears its cookie to get a fresh uid is
        still constrained by the IP-keyed counters, which do not reset.
        """
        checks = [
            (f"uid:{uid}:minute", _MINUTE, settings.rate_limit_per_minute, "per-minute"),
            (f"ip:{ip}:minute", _MINUTE, settings.rate_limit_per_minute, "per-minute"),
            (f"uid:{uid}:day", _DAY, settings.rate_limit_per_day, "per-day"),
            (f"ip:{ip}:day", _DAY, settings.rate_limit_per_day, "per-day"),
        ]
        for key, window, limit, label in checks:
            allowed, retry_after = self._store.hit(key, window, limit)
            if not allowed:
                return RateLimitDecision(False, retry_after, f"{label} limit exceeded")
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
    """Return the client IP, preferring the leftmost X-Forwarded-For hop.

    Railway terminates TLS at a proxy, so `request.client.host` is the
    proxy's address, not the caller's. The leftmost X-Forwarded-For entry
    is the original client as seen by the first hop.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first_hop = forwarded.split(",")[0].strip()
        if first_hop:
            return first_hop
    return request.client.host if request.client else "unknown"


# Process-wide singleton. Swap the store implementation here to move to a
# shared backend later -- call sites only ever use `rate_limiter`.
rate_limiter = RateLimiter(InMemoryRateLimitStore())
