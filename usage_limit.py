"""A process-global daily call cap, on top of Flask-Limiter's per-IP limit.

This exists so the shared demo API key can't be exhausted in one day by
either a single heavy user (handled by Flask-Limiter) or many different
visitors combined (handled here). In-memory and per-process by design —
see README's "Rate limiting" section for why that requires running a
single gunicorn worker.
"""

from __future__ import annotations

import threading
from datetime import date


class DailyLimiter:
    def __init__(self, max_per_day: int):
        self.max_per_day = max_per_day
        self._lock = threading.Lock()
        self._day = date.today()
        self._count = 0

    def _reset_if_new_day(self) -> None:
        today = date.today()
        if today != self._day:
            self._day = today
            self._count = 0

    def try_consume(self) -> bool:
        """Returns True and records a use if under the daily cap, else False."""
        with self._lock:
            self._reset_if_new_day()
            if self._count >= self.max_per_day:
                return False
            self._count += 1
            return True

    @property
    def remaining(self) -> int:
        with self._lock:
            self._reset_if_new_day()
            return max(0, self.max_per_day - self._count)
