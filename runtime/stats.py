from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, Optional


STATS_SCHEMA_VERSION = 1


def _utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


@dataclass
class ProviderStats:

    queries: int = 0
    requests: int = 0
    failed_requests: int = 0

    pages: int = 0

    raw_results: int = 0
    extracted: int = 0
    accepted: int = 0

    rejected: int = 0
    duplicates: int = 0
    saved: int = 0

    retries: int = 0
    errors: int = 0

    def snapshot(self) -> Dict[str, int]:

        return {
            "queries": self.queries,
            "requests": self.requests,
            "failed_requests": self.failed_requests,
            "pages": self.pages,
            "raw_results": self.raw_results,
            "extracted": self.extracted,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "duplicates": self.duplicates,
            "saved": self.saved,
            "retries": self.retries,
            "errors": self.errors,
        }


@dataclass
class ScraperStats:
    """
    Structured runtime statistics for one scraper execution.

    This object is an internal runtime service, but its snapshot()
    method is an external data contract.

    The snapshot is designed to be:

        - deterministic
        - JSON serializable
        - versioned
        - independent from internal Python objects
        - safe for external monitoring/analysis software
    """

    # ==========================================================
    # SCHEMA
    # ==========================================================

    schema_version: int = STATS_SCHEMA_VERSION

    # ==========================================================
    # LIFECYCLE
    # ==========================================================

    state: str = "created"

    started_at: Optional[str] = None
    finished_at: Optional[str] = None

    # ==========================================================
    # LOGICAL EXECUTION
    # ==========================================================

    logical_queries: int = 0
    completed_queries: int = 0

    # ==========================================================
    # PROVIDER EXECUTION
    # ==========================================================

    provider_queries: int = 0

    # ==========================================================
    # NETWORK
    # ==========================================================

    requests: int = 0
    failed_requests: int = 0
    retries: int = 0

    # ==========================================================
    # PAGINATION
    # ==========================================================

    pages: int = 0

    # ==========================================================
    # DATA LIFECYCLE
    # ==========================================================

    raw_results: int = 0
    extracted: int = 0
    accepted: int = 0

    rejected: int = 0
    duplicates: int = 0
    saved: int = 0

    # ==========================================================
    # ERRORS
    # ==========================================================

    errors: int = 0

    # ==========================================================
    # PROVIDERS
    # ==========================================================

    providers: Dict[str, ProviderStats] = field(
        default_factory=dict
    )

    # ==========================================================
    # INTERNAL LOCK
    # ==========================================================

    _lock: Lock = field(
        default_factory=Lock,
        repr=False,
        compare=False,
    )

    # ==========================================================
    # INTERNAL HELPERS
    # ==========================================================

    @staticmethod
    def _normalize_provider(
        provider: Optional[str],
    ) -> Optional[str]:

        if provider is None:
            return None

        value = str(
            provider
        ).strip().lower()

        return value or None

    def _provider(
        self,
        provider: Optional[str],
    ) -> Optional[ProviderStats]:

        provider = self._normalize_provider(
            provider
        )

        if provider is None:
            return None

        if provider not in self.providers:

            self.providers[provider] = (
                ProviderStats()
            )

        return self.providers[provider]

    # ==========================================================
    # QUERY
    # ==========================================================

    def query_started(
        self,
        count: int = 1,
    ) -> None:

        with self._lock:

            self.logical_queries += count

    def query_completed(
        self,
        count: int = 1,
    ) -> None:

        with self._lock:

            self.completed_queries += count

    # ==========================================================
    # PROVIDER QUERY
    # ==========================================================

    def provider_query_started(
        self,
        provider: Optional[str] = None,
        count: int = 1,
    ) -> None:

        with self._lock:

            self.provider_queries += count

            stats = self._provider(
                provider
            )

            if stats:

                stats.queries += count

    # ==========================================================
    # REQUEST
    # ==========================================================

    def request_started(
        self,
        provider: Optional[str] = None,
    ) -> None:

        with self._lock:

            self.requests += 1

            stats = self._provider(
                provider
            )

            if stats:

                stats.requests += 1

    def request_failed(
        self,
        provider: Optional[str] = None,
    ) -> None:

        with self._lock:

            self.failed_requests += 1

            stats = self._provider(
                provider
            )

            if stats:

                stats.failed_requests += 1

    # ==========================================================
    # RETRY
    # ==========================================================

    def retry(
        self,
        provider: Optional[str] = None,
    ) -> None:

        with self._lock:

            self.retries += 1

            stats = self._provider(
                provider
            )

            if stats:

                stats.retries += 1

    # ==========================================================
    # PAGE
    # ==========================================================

    def page_processed(
        self,
        provider: Optional[str] = None,
        count: int = 1,
    ) -> None:

        with self._lock:

            self.pages += count

            stats = self._provider(
                provider
            )

            if stats:

                stats.pages += count

    # ==========================================================
    # RAW RESULTS
    # ==========================================================

    def raw_result(
        self,
        count: int = 1,
        provider: Optional[str] = None,
    ) -> None:

        with self._lock:

            self.raw_results += count

            stats = self._provider(
                provider
            )

            if stats:

                stats.raw_results += count

    # ==========================================================
    # EXTRACTED
    # ==========================================================

    def extracted_result(
        self,
        count: int = 1,
        provider: Optional[str] = None,
    ) -> None:

        with self._lock:

            self.extracted += count

            stats = self._provider(
                provider
            )

            if stats:

                stats.extracted += count

    # ==========================================================
    # ACCEPTED
    # ==========================================================

    def accepted_result(
        self,
        count: int = 1,
        provider: Optional[str] = None,
    ) -> None:

        with self._lock:

            self.accepted += count

            stats = self._provider(
                provider
            )

            if stats:

                stats.accepted += count

    # ==========================================================
    # REJECTED
    # ==========================================================

    def rejected_result(
        self,
        count: int = 1,
        provider: Optional[str] = None,
    ) -> None:

        with self._lock:

            self.rejected += count

            stats = self._provider(
                provider
            )

            if stats:

                stats.rejected += count

    # ==========================================================
    # DUPLICATES
    # ==========================================================

    def duplicate(
        self,
        count: int = 1,
        provider: Optional[str] = None,
    ) -> None:

        with self._lock:

            self.duplicates += count

            stats = self._provider(
                provider
            )

            if stats:

                stats.duplicates += count

    # ==========================================================
    # SAVED
    # ==========================================================

    def saved_result(
        self,
        count: int = 1,
        provider: Optional[str] = None,
    ) -> None:

        with self._lock:

            self.saved += count

            stats = self._provider(
                provider
            )

            if stats:

                stats.saved += count

    # ==========================================================
    # ERRORS
    # ==========================================================

    def error(
        self,
        count: int = 1,
        provider: Optional[str] = None,
    ) -> None:

        with self._lock:

            self.errors += count

            stats = self._provider(
                provider
            )

            if stats:

                stats.errors += count

    # ==========================================================
    # LIFECYCLE — START
    # ==========================================================

    def start(self) -> None:

        with self._lock:

            self.state = "running"

            self.started_at = _utc_now()

            self.finished_at = None

    # ==========================================================
    # LIFECYCLE — COMPLETE
    # ==========================================================

    def complete(self) -> None:

        with self._lock:

            self.state = "completed"

            self.finished_at = _utc_now()

    # ==========================================================
    # LIFECYCLE — STOP
    # ==========================================================

    def stop(self) -> None:

        with self._lock:

            if self.state == "running":

                self.state = "stopped"

            self.finished_at = _utc_now()

    # ==========================================================
    # LIFECYCLE — FAILED
    # ==========================================================

    def fail(self) -> None:

        with self._lock:

            self.state = "failed"

            self.finished_at = _utc_now()

    # ==========================================================
    # COMPATIBILITY
    # ==========================================================

    @property
    def running(self) -> bool:

        return self.state == "running"

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(self) -> Dict[str, Any]:
        """
        Return the public runtime statistics contract.

        The returned dictionary contains only primitive,
        JSON-serializable values.
        """

        with self._lock:

            return {
                "schema_version": self.schema_version,

                "state": self.state,

                "started_at": self.started_at,
                "finished_at": self.finished_at,

                "logical_queries":
                    self.logical_queries,

                "completed_queries":
                    self.completed_queries,

                "provider_queries":
                    self.provider_queries,

                "requests":
                    self.requests,

                "failed_requests":
                    self.failed_requests,

                "retries":
                    self.retries,

                "pages":
                    self.pages,

                "raw_results":
                    self.raw_results,

                "extracted":
                    self.extracted,

                "accepted":
                    self.accepted,

                "rejected":
                    self.rejected,

                "duplicates":
                    self.duplicates,

                "saved":
                    self.saved,

                "errors":
                    self.errors,

                "providers": {
                    name: stats.snapshot()
                    for name, stats
                    in sorted(
                        self.providers.items()
                    )
                },
            }

    # ==========================================================
    # RESET
    # ==========================================================

    def reset(self) -> None:

        with self._lock:

            self.state = "created"

            self.started_at = None
            self.finished_at = None

            self.logical_queries = 0
            self.completed_queries = 0

            self.provider_queries = 0

            self.requests = 0
            self.failed_requests = 0
            self.retries = 0

            self.pages = 0

            self.raw_results = 0
            self.extracted = 0
            self.accepted = 0

            self.rejected = 0
            self.duplicates = 0
            self.saved = 0

            self.errors = 0

            self.providers.clear()