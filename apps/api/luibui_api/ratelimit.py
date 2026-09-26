"""In-process sliding-window limiter. One API process per container, so memory is enough for now;
with several processes this moves to PostgreSQL."""

import threading
import time
from collections import deque


class RateLimiter:
    def __init__(self, max_events: int, window_seconds: float) -> None:
        self.max_events = max_events
        self.window = window_seconds
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> deque[float]:
        events = self._events.setdefault(key, deque())
        while events and events[0] <= now - self.window:
            events.popleft()
        return events

    def blocked(self, *keys: str) -> bool:
        now = time.monotonic()
        with self._lock:
            return any(len(self._recent(k, now)) >= self.max_events for k in keys)

    def hit(self, *keys: str) -> None:
        now = time.monotonic()
        with self._lock:
            for key in keys:
                self._recent(key, now).append(now)
            if len(self._events) > 100_000:  # bound memory under a flood of distinct keys
                self._events = {k: v for k, v in self._events.items() if self._recent(k, now)}

    def reset(self, *keys: str) -> None:
        with self._lock:
            for key in keys:
                self._events.pop(key, None)
