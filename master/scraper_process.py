# ==========================================================
# FILE REVIEW — scraper_process.py
#
# STATUS       : APPROVED
# ROLE         : Child Process Wrapper
# LAYER        : Master / Runtime Execution Boundary
#
# RESPONSIBILITIES
# ----------------------------------------------------------
# 1. Build multiprocessing.Process
# 2. Prepare child configuration
# 3. Execute ScraperWorker inside child
# 4. Start / Stop / Kill
# 5. Join / Wait
# 6. Expose PID / Exit Code
# 7. Provide stable runtime snapshot
# 8. Prepare runtime directories
# 9. Record unexpected child errors
#
# PROVIDER CONTRACT
# ----------------------------------------------------------
# Exactly ONE provider per scraper.
#
# KEYWORD CONTRACT
# ----------------------------------------------------------
# Exactly ONE required keyword must exist in config.
#
# RESTART CONTRACT
# ----------------------------------------------------------
# ScraperProcess instances are never reused after
# the underlying multiprocessing.Process has started.
#
# ProcessManager creates a completely new ScraperProcess
# for every restart.
# ==========================================================

from __future__ import annotations

import multiprocessing as mp
import os
import signal
from pathlib import Path
from typing import Any, Optional

from scraper.worker import ScraperWorker


class ScraperProcess:
    """
    Runtime wrapper around exactly one child process.

    ScraperProcess owns one multiprocessing.Process instance.

    It does NOT:
        - manage ScraperRegistry
        - manage ProcessManager
        - execute providers directly
        - perform scraping logic
        - manage other processes
        - perform database migrations
    """

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

    def __init__(
        self,
        name: str,
        providers: list[str],
        database: str,
        config: Optional[dict[str, Any]] = None,
        log_file: Optional[str] = None,
        scraper_dir: Optional[str] = None,
    ) -> None:

        # ------------------------------------------------------
        # NAME
        # ------------------------------------------------------

        name = str(
            name
        ).strip()

        if not name:
            raise ValueError(
                "Scraper name is required."
            )

        self.name = name

        # ------------------------------------------------------
        # PROVIDER
        # ------------------------------------------------------

        normalized_providers = [
            str(provider).strip().lower()
            for provider in (providers or [])
            if str(provider).strip()
        ]

        if len(normalized_providers) != 1:
            raise ValueError(
                "Each scraper process must use "
                "exactly one provider."
            )

        self.providers = normalized_providers

        # ------------------------------------------------------
        # CONFIG
        # ------------------------------------------------------

        self.config = dict(
            config or {}
        )

        keyword = str(
            self.config.get(
                "keyword",
                "",
            )
        ).strip()

        if not keyword:
            raise ValueError(
                "Scraper keyword is required."
            )

        self.config["keyword"] = keyword

        # ------------------------------------------------------
        # DATABASE
        # ------------------------------------------------------

        if database is None:
            raise ValueError(
                "Database path is required."
            )

        self.database = str(
            Path(database).expanduser()
        )

        # ------------------------------------------------------
        # LOG
        # ------------------------------------------------------

        self.log_file = (
            str(
                Path(
                    log_file
                ).expanduser()
            )
            if log_file
            else None
        )

        # ------------------------------------------------------
        # SCRAPER DIRECTORY
        # ------------------------------------------------------

        self.scraper_dir = (
            str(
                Path(
                    scraper_dir
                ).expanduser()
            )
            if scraper_dir
            else None
        )

        # ------------------------------------------------------
        # PROCESS
        # ------------------------------------------------------

        self.process: Optional[
            mp.Process
        ] = None

        self._prepare_directories()

    # ==========================================================
    # DIRECTORIES
    # ==========================================================

    def _prepare_directories(
        self,
    ) -> None:
        """
        Prepare all runtime directories required
        by this scraper.
        """

        database_path = Path(
            self.database
        )

        database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if self.log_file:

            Path(
                self.log_file
            ).parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        if self.scraper_dir:

            Path(
                self.scraper_dir
            ).mkdir(
                parents=True,
                exist_ok=True,
            )

    # ==========================================================
    # START
    # ==========================================================

    def start(
        self,
    ) -> None:
        """
        Create and start the underlying child process.

        A ScraperProcess cannot reuse a previously-started
        multiprocessing.Process.
        """

        if self.process is not None:

            if self.process.is_alive():

                raise RuntimeError(
                    f"Scraper '{self.name}' "
                    "is already running."
                )

            if self.process.pid is not None:

                raise RuntimeError(
                    f"Scraper '{self.name}' "
                    "process has already been started "
                    "and cannot be reused."
                )

        self.process = mp.Process(
            target=self._bootstrap,
            name=f"EYE-{self.name}",
            daemon=False,
        )

        self.process.start()

    # ==========================================================
    # CHILD BOOTSTRAP
    # ==========================================================

    def _bootstrap(
        self,
    ) -> None:
        """
        Child-process entry point.

        Only scraper-specific configuration crosses
        the Master/Child boundary.
        """

        pid = os.getpid()

        try:

            self._setup_child_process()

            worker = ScraperWorker(
                name=self.name,
                providers=list(
                    self.providers
                ),
                database=self.database,
                config=dict(
                    self.config
                ),
                log_file=self.log_file,
                scraper_dir=self.scraper_dir,
            )

            worker.run()

        except KeyboardInterrupt:

            raise

        except SystemExit:

            raise

        except Exception as exc:

            self._write_child_error(
                pid=pid,
                error=exc,
            )

            raise

    # ==========================================================
    # CHILD SETUP
    # ==========================================================

    def _setup_child_process(
        self,
    ) -> None:
        """
        Defensive child-side directory initialization.

        Scraping logic remains inside ScraperWorker.
        """

        if self.scraper_dir:

            Path(
                self.scraper_dir
            ).mkdir(
                parents=True,
                exist_ok=True,
            )

        if self.log_file:

            Path(
                self.log_file
            ).parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        Path(
            self.database
        ).parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ==========================================================
    # STOP
    # ==========================================================

    def stop(
        self,
    ) -> None:
        """
        Request graceful process termination.

        multiprocessing.Process.terminate()
        sends SIGTERM on Unix.
        """

        if self.process is None:
            return

        if not self.process.is_alive():
            return

        self.process.terminate()

    # ==========================================================
    # KILL
    # ==========================================================

    def kill(
        self,
    ) -> None:
        """
        Immediately terminate the child process.
        """

        if self.process is None:
            return

        if not self.process.is_alive():
            return

        try:

            self.process.kill()

        except AttributeError:

            pid = self.pid

            if pid is None:
                return

            os.kill(
                pid,
                signal.SIGKILL,
            )

    # ==========================================================
    # JOIN
    # ==========================================================

    def join(
        self,
        timeout: Optional[float] = None,
    ) -> None:

        if self.process is None:
            return

        self.process.join(
            timeout=timeout
        )

    # ==========================================================
    # WAIT
    # ==========================================================

    def wait(
        self,
        timeout: Optional[float] = None,
    ) -> Optional[int]:
        """
        Wait for termination and return exit code.
        """

        if self.process is None:
            return None

        self.process.join(
            timeout=timeout
        )

        return self.process.exitcode

    # ==========================================================
    # IS ALIVE
    # ==========================================================

    def is_alive(
        self,
    ) -> bool:

        if self.process is None:
            return False

        return self.process.is_alive()

    # ==========================================================
    # PID
    # ==========================================================

    @property
    def pid(
        self,
    ) -> Optional[int]:

        if self.process is None:
            return None

        return self.process.pid

    # ==========================================================
    # EXIT CODE
    # ==========================================================

    @property
    def exitcode(
        self,
    ) -> Optional[int]:

        if self.process is None:
            return None

        return self.process.exitcode

    # ==========================================================
    # STARTED
    # ==========================================================

    @property
    def started(
        self,
    ) -> bool:

        return self.process is not None

    # ==========================================================
    # TERMINATED
    # ==========================================================

    @property
    def terminated(
        self,
    ) -> bool:

        if self.process is None:
            return False

        return (
            not self.process.is_alive()
            and self.process.exitcode is not None
        )

    # ==========================================================
    # RAW PROCESS
    # ==========================================================

    @property
    def raw_process(
        self,
    ) -> Optional[mp.Process]:

        return self.process

    # ==========================================================
    # CONFIGURATION
    # ==========================================================

    def configuration(
        self,
    ) -> dict[str, Any]:
        """
        Return stable serializable configuration.
        """

        return {
            "name": self.name,

            "providers": list(
                self.providers
            ),

            "database": self.database,

            "config": dict(
                self.config
            ),

            "log_file": self.log_file,

            "scraper_dir": self.scraper_dir,
        }

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(
        self,
    ) -> dict[str, Any]:
        """
        Return stable runtime snapshot.

        This contains runtime/process information only.
        Registry lifecycle state belongs to ScraperRegistry.
        """

        return {
            "name": self.name,

            "pid": self.pid,

            "alive": self.is_alive(),

            "started": self.started,

            "terminated": self.terminated,

            "exit_code": self.exitcode,

            "providers": list(
                self.providers
            ),

            "database": self.database,

            "log_file": self.log_file,

            "scraper_dir": self.scraper_dir,

            "config": dict(
                self.config
            ),
        }

    # ==========================================================
    # CHILD ERROR
    # ==========================================================

    def _write_child_error(
        self,
        pid: int,
        error: Exception,
    ) -> None:
        """
        Write unexpected child exception to the
        scraper-specific log.

        Logging failure must never hide the original
        child exception.
        """

        if not self.log_file:
            return

        try:

            path = Path(
                self.log_file
            )

            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with path.open(
                "a",
                encoding="utf-8",
            ) as file:

                file.write(
                    "\n"
                    "[CHILD PROCESS ERROR]\n"
                )

                file.write(
                    f"PID: {pid}\n"
                )

                file.write(
                    f"SCRAPER: {self.name}\n"
                )

                file.write(
                    "PROVIDER: "
                    f"{self.providers[0]}\n"
                )

                file.write(
                    f"ERROR: {error}\n"
                )

        except OSError:
            pass

    # ==========================================================
    # REPRESENTATION
    # ==========================================================

    def __repr__(
        self,
    ) -> str:

        return (
            f"<ScraperProcess "
            f"name={self.name!r} "
            f"pid={self.pid!r} "
            f"alive={self.is_alive()}>"
        )