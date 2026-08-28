
from __future__ import annotations

import time
from typing import Any, Callable, Optional


class RetryPolicy:
    """
    Generic retry policy with exponential backoff.

    The policy executes a callable and retries it when an exception
    occurs. It does not swallow the final exception.
    """

    def __init__(
        self,
        attempts: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        on_retry: Optional[
            Callable[[int, Exception, float], None]
        ] = None,
    ):
        self.attempts = max(
            1,
            int(attempts),
        )

        self.delay = max(
            0.0,
            float(delay),
        )

        self.backoff = max(
            1.0,
            float(backoff),
        )

        self.on_retry = on_retry

    def execute(
        self,
        function: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Any:

        last_error: Optional[Exception] = None
        delay = self.delay

        for attempt in range(
            1,
            self.attempts + 1,
        ):
            try:
                return function(
                    *args,
                    **kwargs,
                )

            except Exception as exc:
                last_error = exc

                if attempt >= self.attempts:
                    break

                if self.on_retry is not None:
                    self.on_retry(
                        attempt,
                        exc,
                        delay,
                    )

                if delay > 0:
                    time.sleep(delay)

                delay *= self.backoff

        if last_error is not None:
            raise last_error

        raise RuntimeError(
            "RetryPolicy execution failed without an exception."
        )
