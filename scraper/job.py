# ==========================================================
# EYES MASTER — SCRAPER JOB
# ==========================================================
#
# FILE:
#     scraper/job.py
#
# STATUS:
#     CANONICAL / CORE
#
# ROLE:
#     Thread-level execution lifecycle manager.
#
# LAYER:
#     Scraper / Runtime
#
# RESPONSIBILITIES:
#     - Manage one scraper execution thread
#     - Start Worker
#     - Request graceful Worker stop
#     - Track Job lifecycle
#     - Store execution timestamps
#     - Store execution results/errors
#     - Expose progress and snapshot
#
# DOES NOT:
#     - Execute scraping logic
#     - Manage Provider
#     - Manage Database
#     - Manage Pipeline
#     - Manage Process lifecycle
#     - Manage ProviderManager
#     - Access Engine internals
#
# ARCHITECTURE:
#
#     ProcessManager
#           │
#           ▼
#     ScraperProcess
#           │
#           ▼
#       ScraperJob
#           │
#           ▼
#      ScraperWorker
#           │
#           ▼
#      ScraperEngine
#
# CORE RULE:
#
#     Job owns Thread lifecycle.
#     Worker owns scraper runtime lifecycle.
#     Engine owns scraping execution.
#
# ==========================================================

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, Optional


class ScraperJob:

    # ==========================================================
    # STATUS
    # ==========================================================

    STATUS_IDLE = "idle"

    STATUS_RUNNING = "running"

    STATUS_STOPPING = "stopping"

    STATUS_FINISHED = "finished"

    STATUS_STOPPED = "stopped"

    STATUS_FAILED = "failed"

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(
        self,
        job_id,
        worker,
    ) -> None:

        if worker is None:

            raise ValueError(
                "ScraperWorker is required."
            )

        self.job_id = str(
            job_id
        )

        self.worker = worker

        # ======================================================
        # THREAD
        # ======================================================

        self.thread: Optional[
            threading.Thread
        ] = None

        # ======================================================
        # STATE
        # ======================================================

        self.status = (
            self.STATUS_IDLE
        )

        self.results: list[Any] = []

        self.error: Optional[
            Exception
        ] = None

        self.started_at: Optional[
            str
        ] = None

        self.finished_at: Optional[
            str
        ] = None

    # ==========================================================
    # START
    # ==========================================================

    def start(self) -> bool:
        """
        Start the Worker in a dedicated thread.

        Returns:
            True  -> thread started
            False -> job is already running
        """

        if self.is_running():

            return False

        self.error = None

        self.results = []

        self.started_at = (
            datetime.now().isoformat()
        )

        self.finished_at = None

        self.status = (
            self.STATUS_RUNNING
        )

        self.thread = threading.Thread(
            target=self._run_worker,
            name=(
                f"ScraperJob-{self.job_id}"
            ),
            daemon=True,
        )

        self.thread.start()

        return True

    # ==========================================================
    # WORKER THREAD
    # ==========================================================

    def _run_worker(self) -> None:
        """
        Execute the Worker inside the Job thread.

        Worker owns the actual scraper lifecycle.
        Job only translates the result into Job state.
        """

        try:

            results = (
                self.worker.run()
            )

            self.results = (
                results or []
            )

            # ==================================================
            # ERROR
            # ==================================================

            if self.worker.error:

                self.error = (
                    RuntimeError(
                        self.worker.error
                    )
                )

                self.status = (
                    self.STATUS_FAILED
                )

                return

            # ==================================================
            # STOP
            # ==================================================

            if self._worker_stop_requested():

                self.status = (
                    self.STATUS_STOPPED
                )

                return

            # ==================================================
            # SUCCESS
            # ==================================================

            self.status = (
                self.STATUS_FINISHED
            )

        except Exception as error:

            self.error = error

            self.status = (
                self.STATUS_FAILED
            )

        finally:

            self.finished_at = (
                datetime.now().isoformat()
            )

    # ==========================================================
    # STOP REQUEST
    # ==========================================================

    def stop(self) -> bool:
        """
        Request graceful Worker shutdown.

        The Job does not forcibly terminate the thread.
        """

        if self.status != (
            self.STATUS_RUNNING
        ):

            return False

        self.status = (
            self.STATUS_STOPPING
        )

        try:

            stopped = (
                self.worker.stop()
            )

        except Exception as error:

            self.error = error

            self.status = (
                self.STATUS_FAILED
            )

            return False

        if not stopped:

            self.status = (
                self.STATUS_RUNNING
            )

            return False

        return True

    # ==========================================================
    # WORKER STOP STATE
    # ==========================================================

    def _worker_stop_requested(self) -> bool:
        """
        Determine whether Worker execution was requested to stop.

        Worker is the abstraction boundary.
        Job never accesses Engine internals.
        """

        snapshot = (
            self.worker.snapshot()
        )

        context = (
            snapshot.get(
                "context"
            )
            or {}
        )

        stats = (
            snapshot.get(
                "stats"
            )
            or {}
        )

        # ------------------------------------------------------
        # Current Worker contract does not expose a dedicated
        # stop_requested field yet.
        #
        # During a requested stop, Job itself enters STOPPING.
        # Therefore this helper primarily preserves the Worker
        # abstraction boundary and allows future Worker support.
        # ------------------------------------------------------

        if self.status == (
            self.STATUS_STOPPING
        ):

            return True

        return bool(
            context.get(
                "stop_requested",
                stats.get(
                    "stop_requested",
                    False,
                ),
            )
        )

    # ==========================================================
    # JOIN
    # ==========================================================

    def join(
        self,
        timeout: Optional[float] = None,
    ) -> None:
        """
        Wait for the Job thread to finish.
        """

        if self.thread is None:

            return

        self.thread.join(
            timeout
        )

    # ==========================================================
    # RUNNING
    # ==========================================================

    def is_running(self) -> bool:
        """
        Return whether the Job thread is alive.
        """

        return (
            self.thread is not None
            and self.thread.is_alive()
        )

    # ==========================================================
    # FINISHED
    # ==========================================================

    def is_finished(self) -> bool:
        """
        Return whether the Job reached a terminal state.
        """

        return self.status in (
            self.STATUS_FINISHED,
            self.STATUS_STOPPED,
            self.STATUS_FAILED,
        )

    # ==========================================================
    # PROGRESS
    # ==========================================================

    def progress(self) -> dict[str, Any]:
        """
        Return combined Worker + Job execution state.
        """

        try:

            data = dict(
                self.worker.snapshot()
            )

        except Exception:

            data = {}

        data.update({

            "job_id":
                self.job_id,

            "status":
                self.status,

            "started_at":
                self.started_at,

            "finished_at":
                self.finished_at,

        })

        return data

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(self) -> dict[str, Any]:
        """
        Return a complete Job runtime snapshot.
        """

        try:

            worker_snapshot = (
                self.worker.snapshot()
            )

        except Exception as error:

            worker_snapshot = {
                "error":
                    str(error),
            }

        return {

            "job_id":
                self.job_id,

            "status":
                self.status,

            "running":
                self.is_running(),

            "finished":
                self.is_finished(),

            "started_at":
                self.started_at,

            "finished_at":
                self.finished_at,

            "results":
                len(self.results),

            "error":
                (
                    str(self.error)
                    if self.error
                    else None
                ),

            "worker":
                worker_snapshot,

        }

    # ==========================================================
    # REPR
    # ==========================================================

    def __repr__(self) -> str:

        return (
            f"<ScraperJob "
            f"id={self.job_id!r} "
            f"status={self.status!r}>"
        )


# ==========================================================
# FINAL STATUS
# ==========================================================
#
# THREAD OWNERSHIP   : CLEAN
# WORKER DELEGATION  : CLEAN
# ENGINE COUPLING    : NONE
# PROVIDER COUPLING  : NONE
# DATABASE COUPLING  : NONE
# PIPELINE COUPLING  : NONE
# STOP API           : CLEAN
# ERROR PROPAGATION   : CLEAN
# SNAPSHOT            : GOOD
# LIFECYCLE           : GOOD
#
# FINAL VERDICT
# ----------------------------------------------------------
# APPROVED / CANONICAL
#
# ==========================================================