"""Candidate B: small fixed-window rate limiter (best effort, per function instance).

Serverless instances do not share memory, so this is a guard against a runaway client
loop hitting one warm instance, not a global quota. The table is bounded.
"""

from __future__ import annotations

import math
import threading
import time
from typing import Callable, Dict, Optional, Tuple

MAX_KEYS = 4096
WINDOW_S = 60.0


class FixedWindowLimiter:
    def __init__(self, per_window: int, window_s: float = WINDOW_S,
                 clock: Callable[[], float] = time.monotonic):
        self.per_window = per_window
        self.window_s = window_s
        self._clock = clock
        self._lock = threading.Lock()
        self._hits: Dict[str, Tuple[float, int]] = {}

    def check(self, key: str) -> Optional[int]:
        """Record a hit. Returns None if allowed, else seconds until the window resets."""
        now = self._clock()
        with self._lock:
            start, n = self._hits.get(key, (now, 0))
            if now - start >= self.window_s:
                start, n = now, 0
            if n >= self.per_window:
                return max(1, math.ceil(self.window_s - (now - start)))
            if len(self._hits) >= MAX_KEYS and key not in self._hits:
                cutoff = now - self.window_s
                self._hits = {k: v for k, v in self._hits.items() if v[0] >= cutoff}
                if len(self._hits) >= MAX_KEYS:
                    self._hits.clear()
            self._hits[key] = (start, n + 1)
            return None
