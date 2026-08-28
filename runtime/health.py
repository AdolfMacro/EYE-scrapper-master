from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class ProviderHealth:

    provider: str

    healthy: bool = False

    checked_at: str | None = None

    error: str | None = None

    def success(self) -> None:

        self.healthy = True
        self.error = None

        self.checked_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

    def failure(
        self,
        error: Exception | str,
    ) -> None:

        self.healthy = False
        self.error = str(error)

        self.checked_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

    def snapshot(self) -> dict:

        return {
            "provider": self.provider,
            "healthy": self.healthy,
            "checked_at": self.checked_at,
            "error": self.error,
        }