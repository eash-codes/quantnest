"""In-process rate limiting.

A fixed-window counter guarding the authentication endpoints, which are
otherwise brute-forceable. Deliberately small: no dependency, no Redis, and
it does the job for a single instance.

**Scope caveat.** State lives in this process, so N replicas allow N times the
configured limit. The class is written against the same shape a Redis
implementation would use (``INCR`` + ``EXPIRE``), so swapping it out later
touches only this file.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

#: Attempts permitted per window, per key.
LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "10"))
#: Window length in seconds.
LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", "300"))
#: Registration is costlier (bcrypt) and rarer, so it gets a tighter budget.
REGISTER_MAX_ATTEMPTS = int(os.getenv("REGISTER_MAX_ATTEMPTS", "5"))
REGISTER_WINDOW_SECONDS = int(os.getenv("REGISTER_WINDOW_SECONDS", "3600"))

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").strip().lower() not in {
    "0",
    "false",
    "no",
}


@dataclass(frozen=True)
class RateLimitResult:
    """Outcome of a single rate-limit check."""

    allowed: bool
    remaining: int
    retry_after: int
    limit: int


class FixedWindowRateLimiter:
    """Counts hits per key within a fixed time window.

    Fixed-window is chosen over a sliding log for its constant memory per key.
    Its known weakness is burstiness at a window boundary (up to 2× the limit
    across two adjacent windows), which is an acceptable trade for guarding a
    login form.
    """

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self._max = max_attempts
        self._window = window_seconds
        self._lock = threading.Lock()
        # key -> (window_started_at, count)
        self._hits: Dict[str, Tuple[float, int]] = {}

    def check(self, key: str, *, cost: int = 1) -> RateLimitResult:
        """Record a hit and report whether it is allowed."""
        now = time.monotonic()

        with self._lock:
            started, count = self._hits.get(key, (now, 0))

            # Window elapsed: start a fresh one.
            if now - started >= self._window:
                started, count = now, 0

            count += cost
            self._hits[key] = (started, count)

            # Opportunistic cleanup so the dict cannot grow without bound.
            if len(self._hits) > 10_000:
                self._evict_stale(now)

        remaining = max(0, self._max - count)
        retry_after = max(1, int(self._window - (now - started)))

        return RateLimitResult(
            allowed=count <= self._max,
            remaining=remaining,
            retry_after=retry_after,
            limit=self._max,
        )

    def reset(self, key: str) -> None:
        """Clear a key's counter, e.g. after a successful login."""
        with self._lock:
            self._hits.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()

    def _evict_stale(self, now: float) -> None:
        stale = [k for k, (started, _) in self._hits.items() if now - started >= self._window]
        for key in stale:
            del self._hits[key]


_login_limiter: Optional[FixedWindowRateLimiter] = None
_register_limiter: Optional[FixedWindowRateLimiter] = None


def get_login_limiter() -> FixedWindowRateLimiter:
    global _login_limiter
    if _login_limiter is None:
        _login_limiter = FixedWindowRateLimiter(LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_SECONDS)
    return _login_limiter


def get_register_limiter() -> FixedWindowRateLimiter:
    global _register_limiter
    if _register_limiter is None:
        _register_limiter = FixedWindowRateLimiter(
            REGISTER_MAX_ATTEMPTS, REGISTER_WINDOW_SECONDS
        )
    return _register_limiter


def reset_limiters() -> None:
    """Clear all counters. Used by tests."""
    for limiter in (_login_limiter, _register_limiter):
        if limiter is not None:
            limiter.clear()


def client_key(request, scope: str) -> str:
    """Build a per-client key.

    Prefers the left-most ``X-Forwarded-For`` entry so a reverse proxy does not
    collapse every user onto one key. That header is client-controlled, so this
    is only trustworthy behind a proxy that overwrites it.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"

    return f"{scope}:{ip}"
