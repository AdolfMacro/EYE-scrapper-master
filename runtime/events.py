from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class ScraperEvent:

    event: str

    job_id: str

    timestamp: str

    data: dict[str, Any]


def make_event(
    event: str,
    job_id: str,
    **data: Any,
) -> ScraperEvent:

    return ScraperEvent(
        event=event,
        job_id=job_id,
        timestamp=datetime.now(
            timezone.utc
        ).isoformat(),
        data=data,
    )