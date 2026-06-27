"""Simple in-process sliding-window rate limiter (Phase 1).

In production this is replaced by a Redis token-bucket so limits are shared
across replicas (see SAD §10.3). The interface stays the same.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    def __init__(self, *, max_per_minute: int) -> None:
        self.max_per_minute = max_per_minute
        self._window = 60.0
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            cutoff = now - self._window
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= self.max_per_minute:
                retry_after = max(1, int(self._window - (now - q[0])))
                return False, retry_after
            q.append(now)
            return True, 0
