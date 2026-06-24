"""
Simple in-memory rate limiter — for brute-force protection.

Not production-grade (does not work across multiple processes, resets on
server restart). Provides a basic protection layer.
For production, a Redis-based solution is preferred.
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Optional


# Configuration
_MAX_ATTEMPTS = 5       # Maximum failed attempts within the window
_WINDOW_SECONDS = 300   # 5-minute window
_LOCK_SECONDS = 60      # Lockout duration (seconds)


class RateLimiter:
    """Thread-safe in-memory rate limiter."""

    def __init__(
        self,
        max_attempts: int = _MAX_ATTEMPTS,
        window: int = _WINDOW_SECONDS,
        lockout: int = _LOCK_SECONDS,
    ) -> None:
        self._max_attempts = max_attempts
        self._window = window
        self._lockout = lockout
        # {key: [(timestamp, is_failure), ...]}
        self._records: dict[str, list[tuple[int, bool]]] = defaultdict(list)
        self._locks: dict[str, int] = {}  # {key: lock_expiry_time}
        self._lock = Lock()

    def kontrol_et(self, key: str) -> tuple[bool, Optional[int]]:
        """
        Check whether to allow the request.

        Args:
            key: Identifier such as IP address or email

        Returns:
            (allowed, remaining_seconds) — remaining_seconds > 0 when locked
        """
        now = int(time.time())
        with self._lock:
            # Lock check
            lock_expiry = self._locks.get(key, 0)
            if now < lock_expiry:
                return False, lock_expiry - now

            # Clear old records
            window_start = now - self._window
            self._records[key] = [
                (ts, failed)
                for ts, failed in self._records[key]
                if ts > window_start
            ]
            return True, None

    def basarisiz_kaydet(self, key: str) -> None:
        """Record a failed attempt, lock if threshold reached."""
        now = int(time.time())
        with self._lock:
            self._records[key].append((now, True))
            failures = sum(1 for _, failed in self._records[key] if failed)
            if failures >= self._max_attempts:
                self._locks[key] = now + self._lockout

    def basarili_kaydet(self, key: str) -> None:
        """Reset records on successful login."""
        with self._lock:
            self._records[key] = []
            self._locks.pop(key, None)


# Global limiter instance — for the login endpoint
login_limiter = RateLimiter()
