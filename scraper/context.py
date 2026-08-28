from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from runtime.stats import ScraperStats


class RunContext:
    """
    Runtime context for exactly one scraper execution.

    Responsibilities
    ----------------
    - Own run identity
    - Own runtime metadata
    - Own ScraperStats
    - Control run lifecycle
    - Provide stable serializable snapshots

    This class does NOT:
        - Execute scraping
        - Manage providers
        - Manage databases
        - Perform deduplication
        - Manage processes

    Architecture
    ------------

        ScraperWorker
              │
              ▼
        RunContext
          ├── identity
          ├── metadata
          ├── lifecycle
          └── ScraperStats
                    │
                    ▼
             External Monitor
    """

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(
        self,
        job_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:

        self.job_id = (
            str(job_id).strip()
            if job_id
            else uuid4().hex
        )

        if not self.job_id:

            raise ValueError(
                "Job ID cannot be empty."
            )

        self.metadata: dict[str, Any] = (
            dict(metadata)
            if metadata
            else {}
        )

        self.stats = ScraperStats()

    # ==========================================================
    # LIFECYCLE
    # ==========================================================

    def start(self) -> None:
        """
        Start this run.

        A context represents exactly one run and therefore
        cannot be started more than once.
        """

        if self.stats.state != "created":

            raise RuntimeError(
                f"Run '{self.job_id}' "
                f"cannot start from state "
                f"'{self.stats.state}'."
            )

        self.stats.start()

    def complete(self) -> None:
        """
        Mark the run as successfully completed.
        """

        if self.stats.state != "running":

            raise RuntimeError(
                f"Run '{self.job_id}' "
                f"cannot complete from state "
                f"'{self.stats.state}'."
            )

        self.stats.complete()

    def stop(self) -> None:
        """
        Mark the run as intentionally stopped.

        This is idempotent for an already stopped run.
        """

        state = self.stats.state

        if state == "stopped":

            return

        if state != "running":

            raise RuntimeError(
                f"Run '{self.job_id}' "
                f"cannot stop from state "
                f"'{state}'."
            )

        self.stats.stop()

    def fail(self) -> None:
        """
        Mark the run as failed.

        Failure is a terminal lifecycle state.
        """

        if self.stats.state != "running":

            raise RuntimeError(
                f"Run '{self.job_id}' "
                f"cannot fail from state "
                f"'{self.stats.state}'."
            )

        self.stats.fail()

    # ==========================================================
    # METADATA
    # ==========================================================

    def set_metadata(
        self,
        key: str,
        value: Any,
    ) -> None:

        key = str(
            key
        ).strip()

        if not key:

            raise ValueError(
                "Metadata key cannot be empty."
            )

        self.metadata[key] = value

    def get_metadata(
        self,
        key: str,
        default: Any = None,
    ) -> Any:

        return self.metadata.get(
            key,
            default,
        )

    # ==========================================================
    # STATUS
    # ==========================================================

    @property
    def state(self) -> str:

        return self.stats.state

    @property
    def running(self) -> bool:

        return self.stats.running

    @property
    def finished(self) -> bool:

        return self.stats.state in {
            "completed",
            "stopped",
            "failed",
        }

    @property
    def started_at(self) -> Optional[str]:

        return self.stats.started_at

    @property
    def finished_at(self) -> Optional[str]:

        return self.stats.finished_at

    @property
    def stopped(self) -> bool:

        return self.stats.state == "stopped"

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(self) -> dict[str, Any]:
        """
        Return the public runtime snapshot.

        The returned structure contains only serializable data
        and can safely be consumed by external monitoring software.
        """

        stats = self.stats.snapshot()

        return {
            "schema_version": 1,

            "job_id": self.job_id,

            "state": self.state,

            "started_at": self.started_at,

            "finished_at": self.finished_at,

            "running": self.running,

            "finished": self.finished,

            "stopped": self.stopped,

            "metadata": dict(
                self.metadata
            ),

            "stats": stats,
        }

    # ==========================================================
    # REPRESENTATION
    # ==========================================================

    def __repr__(self) -> str:

        return (
            f"<RunContext "
            f"job_id={self.job_id!r} "
            f"state={self.state!r}>"
        )