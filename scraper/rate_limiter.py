
from __future__ import annotations

import threading
import time


class RateLimiter:
    """
    Thread-safe request rate limiter.

    Ensures that consecutive calls to wait() are separated
    by at least the configured delay.
    """

    def __init__(
        self,
        delay: float = 0.0,
    ):
        self.delay = max(
            0.0,
            float(delay),
        )

        self._lock = threading.Lock()
        self._last_request = 0.0

    def wait(self) -> None:

        if self.delay <= 0:
            return

        with self._lock:

            now = time.monotonic()

            elapsed = (
                now -
                self._last_request
            )

            remaining = (
                self.delay -
                elapsed
            )

            if remaining > 0:
                time.sleep(
                    remaining
                )

            self._last_request = (
                time.monotonic()
            )

    def reset(self) -> None:

        with self._lock:
            self._last_request = 0.0

    def snapshot(self) -> dict:

        with self._lock:
            return {
                "delay": self.delay,
                "last_request": self._last_request,
            }
