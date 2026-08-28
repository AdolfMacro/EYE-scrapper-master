# ==========================================================
# FILE REVIEW — process_manager.py
#
# STATUS       : APPROVED
# ROLE         : Master-level Process Lifecycle Manager
# LAYER        : Master / Runtime Orchestration
#
# RESPONSIBILITIES
# ----------------------------------------------------------
# 1. Create / Start / Stop / Kill
# 2. Restart / Force Restart
# 3. Join / Wait
# 4. Process lifecycle monitoring
# 5. Registry synchronization
# 6. Runtime path management
# 7. Stable runtime snapshots
# 8. Process removal / shutdown
#
# PROVIDER CONTRACT
# ----------------------------------------------------------
# Each child scraper MUST use exactly one provider.
#
# KEYWORD CONTRACT
# ----------------------------------------------------------
# Keyword is mandatory and MUST exist in scraper config.
#
# IMPORTANT
# ----------------------------------------------------------
# multiprocessing.Process instances are never reused after
# termination. Restart always creates a new ScraperProcess.
# ==========================================================

from __future__ import annotations

import os
import signal
import threading
import time
from pathlib import Path
from typing import Any, Optional

from .models import ScraperInfo, ScraperStatus
from .scraper_process import ScraperProcess
from .scraper_registry import ScraperRegistry


class ProcessManager:
    """
    Master-level runtime lifecycle manager.

    ProcessManager owns runtime process objects and coordinates
    their lifecycle with ScraperRegistry.

    It does NOT execute scraping logic.

    Architecture:

        Master
          |
          +-- ProcessManager
          |      |
          |      +-- ScraperProcess
          |             |
          |             +-- multiprocessing.Process
          |
          +-- ScraperRegistry

    Execution:

        ScraperProcess
            -> ScraperWorker
            -> ScraperEngine

    Contract:

        one ScraperProcess
            -> exactly one provider
            -> exactly one required keyword
    """

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

    def __init__(
        self,
        registry: ScraperRegistry,
        runtime_dir: Optional[str | Path] = None,
    ) -> None:

        if registry is None:
            raise ValueError(
                "ScraperRegistry is required."
            )

        self.registry = registry

        # ------------------------------------------------------
        # BASE PATH
        # ------------------------------------------------------

        self.base_dir = (
            Path(__file__)
            .resolve()
            .parent
            .parent
        )

        self.runtime_dir = Path(
            runtime_dir
            if runtime_dir is not None
            else self.base_dir / "runtime"
        ).expanduser()

        self.logs_dir = (
            self.runtime_dir / "logs"
        )

        self.scrapers_dir = (
            self.runtime_dir / "scrapers"
        )

        self.databases_dir = (
            self.runtime_dir / "databases"
        )

        for directory in (
            self.runtime_dir,
            self.logs_dir,
            self.scrapers_dir,
            self.databases_dir,
        ):
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

        # ------------------------------------------------------
        # RUNTIME STATE
        # ------------------------------------------------------

        self._lock = threading.RLock()

        self.processes: dict[
            str,
            ScraperProcess,
        ] = {}

        self._monitor_threads: dict[
            str,
            threading.Thread,
        ] = {}

        self._monitor_stop_events: dict[
            str,
            threading.Event,
        ] = {}

        # Generation prevents an old monitor from touching
        # a newly-created process after restart.
        self._monitor_generations: dict[
            str,
            int,
        ] = {}

    # ==========================================================
    # CREATE
    # ==========================================================

    def create(
        self,
        name: str,
        providers: list[str],
        database: Optional[str] = None,
        config: Optional[dict[str, Any]] = None,
        log_file: Optional[str] = None,
        scraper_dir: Optional[str] = None,
        target: Optional[str] = None,
    ) -> ScraperProcess:
        """
        Create a scraper process without starting it.

        Required:

            name
            exactly one provider
            config.keyword

        The process is registered in both runtime state and
        persistent registry state.
        """

        name = str(name).strip()

        if not name:
            raise ValueError(
                "Scraper name is required."
            )

        normalized_providers = [
            str(provider).strip().lower()
            for provider in (providers or [])
            if str(provider).strip()
        ]

        if len(normalized_providers) != 1:
            raise ValueError(
                "Each child scraper must use "
                "exactly one provider."
            )

        provider = normalized_providers[0]

        scraper_config = dict(config or {})

        keyword = str(
            scraper_config.get(
                "keyword",
                "",
            )
        ).strip()

        if not keyword:
            raise ValueError(
                "Scraper keyword is required."
            )

        scraper_config["keyword"] = keyword

        if target is not None:
            scraper_config.setdefault(
                "target",
                target,
            )

        with self._lock:

            if name in self.processes:
                raise ValueError(
                    f"Process already exists: {name}"
                )

            if self.registry.exists(name):
                raise ValueError(
                    f"Scraper already exists: {name}"
                )

            # --------------------------------------------------
            # DATABASE
            # --------------------------------------------------

            database_path = self._resolve_path(
                database,
                self.databases_dir / f"{name}.db",
            )

            database_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            # --------------------------------------------------
            # LOG
            # --------------------------------------------------

            log_path = self._resolve_path(
                log_file,
                self.logs_dir / f"{name}.log",
            )

            log_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            # --------------------------------------------------
            # SCRAPER DIRECTORY
            # --------------------------------------------------

            scraper_path = self._resolve_path(
                scraper_dir,
                self.scrapers_dir / name,
            )

            scraper_path.mkdir(
                parents=True,
                exist_ok=True,
            )

            # --------------------------------------------------
            # BUILD
            # --------------------------------------------------

            process = self._build_process(
                name=name,
                provider=provider,
                database=str(database_path),
                config=scraper_config,
                log_file=str(log_path),
                scraper_dir=str(scraper_path),
            )

            # --------------------------------------------------
            # REGISTER
            # --------------------------------------------------

            self.registry.register(
                name=name,
                providers=[provider],
                target=target,
                database=str(database_path),
                log_file=str(log_path),
                scraper_dir=str(scraper_path),
                config=dict(scraper_config),
            )

            self.processes[name] = process

            return process

    # ==========================================================
    # CREATE FROM INFO
    # ==========================================================

    def create_from_info(
        self,
        scraper: ScraperInfo,
    ) -> ScraperProcess:
        """
        Create a runtime process from a ScraperInfo record.
        """

        if not isinstance(scraper, ScraperInfo):
            raise TypeError(
                "scraper must be a ScraperInfo instance."
            )

        return self.create(
            name=scraper.name,
            providers=list(scraper.providers),
            database=scraper.database,
            config=dict(scraper.config),
            log_file=scraper.log_file,
            scraper_dir=scraper.scraper_dir,
            target=scraper.target,
        )

    # ==========================================================
    # START
    # ==========================================================

    def start(
        self,
        name: str,
    ) -> ScraperProcess:
        """
        Start a previously-created scraper process.
        """

        with self._lock:

            process = self._get_process(name)

            if process.is_alive():
                raise RuntimeError(
                    f"Scraper '{name}' is already running."
                )

            # A multiprocessing.Process that has already been
            # started cannot be started again.
            if self._process_has_started(process):
                raise RuntimeError(
                    f"Scraper '{name}' cannot be started again. "
                    "Create or rebuild a new process instance."
                )

            self._stop_monitor(name)

            self.registry.set_status(
                name,
                ScraperStatus.STARTING,
                error=None,
            )

            self.registry.set_pid(
                name,
                None,
            )

            try:
                process.start()

            except Exception as exc:

                self.registry.set_pid(
                    name,
                    None,
                )

                self.registry.set_status(
                    name,
                    ScraperStatus.CRASHED,
                    error=str(exc),
                )

                raise

            self.registry.set_pid(
                name,
                process.pid,
            )

            self.registry.set_status(
                name,
                ScraperStatus.RUNNING,
                error=None,
            )

            self._start_monitor(name)

            return process

    # ==========================================================
    # STOP
    # ==========================================================

    def stop(
        self,
        name: str,
        timeout: float = 10.0,
    ) -> bool:
        """
        Gracefully stop a running process.

        Does not automatically kill the process if timeout
        expires.
        """

        self._validate_timeout(timeout)

        with self._lock:

            process = self._get_process(name)

            if not process.is_alive():

                self._sync_dead_process(
                    name,
                    process,
                )

                return True

            self.registry.set_status(
                name,
                ScraperStatus.STOPPING,
            )

            try:
                process.stop()

            except Exception as exc:

                self.registry.set_error(
                    name,
                    str(exc),
                )

                return False

        if not self._wait_process(
            process,
            timeout,
        ):
            return False

        with self._lock:

            self._sync_dead_process(
                name,
                process,
                stopped=True,
            )

        return True

    # ==========================================================
    # KILL
    # ==========================================================

    def kill(
        self,
        name: str,
        timeout: float = 3.0,
    ) -> bool:
        """
        Forcefully terminate a running process.
        """

        self._validate_timeout(timeout)

        with self._lock:

            process = self._get_process(name)

            if not process.is_alive():

                self._sync_dead_process(
                    name,
                    process,
                )

                return True

            pid = process.pid

            try:

                process.kill()

            except (
                AttributeError,
                NotImplementedError,
            ):

                if pid is None:
                    raise RuntimeError(
                        f"Cannot kill scraper '{name}': "
                        "PID is unavailable."
                    )

                os.kill(
                    pid,
                    signal.SIGKILL,
                )

            except Exception as exc:

                self.registry.set_error(
                    name,
                    str(exc),
                )

                raise

        if not self._wait_process(
            process,
            timeout,
        ):
            return False

        with self._lock:

            self._sync_dead_process(
                name,
                process,
                killed=True,
            )

        return True

    # ==========================================================
    # RESTART
    # ==========================================================

    def restart(
        self,
        name: str,
        timeout: float = 10.0,
    ) -> ScraperProcess:
        """
        Gracefully restart a scraper.

        A completely new ScraperProcess is created.
        """

        self._validate_timeout(timeout)

        with self._lock:

            process = self._get_process(name)

            if process.is_alive():

                stopped = self.stop(
                    name,
                    timeout=timeout,
                )

                if not stopped:
                    raise RuntimeError(
                        f"Could not stop scraper "
                        f"'{name}' for restart."
                    )

            new_process = self._rebuild_process(name)

            self.processes[name] = new_process

            self.registry.set_pid(
                name,
                None,
            )

            self.registry.set_status(
                name,
                ScraperStatus.CREATED,
                error=None,
            )

            return self.start(name)

    # ==========================================================
    # FORCE RESTART
    # ==========================================================

    def restart_force(
        self,
        name: str,
        stop_timeout: float = 5.0,
        kill_timeout: float = 3.0,
    ) -> ScraperProcess:
        """
        Restart using:

            STOP
              ↓
            KILL if required
              ↓
            NEW PROCESS
              ↓
            START
        """

        self._validate_timeout(stop_timeout)
        self._validate_timeout(kill_timeout)

        with self._lock:

            process = self._get_process(name)

            if process.is_alive():

                stopped = self.stop(
                    name,
                    timeout=stop_timeout,
                )

                if not stopped:

                    killed = self.kill(
                        name,
                        timeout=kill_timeout,
                    )

                    if not killed:
                        raise RuntimeError(
                            f"Could not terminate "
                            f"scraper '{name}'."
                        )

            new_process = self._rebuild_process(name)

            self.processes[name] = new_process

            self.registry.set_pid(
                name,
                None,
            )

            self.registry.set_status(
                name,
                ScraperStatus.CREATED,
                error=None,
            )

            return self.start(name)

    # ==========================================================
    # JOIN
    # ==========================================================

    def join(
        self,
        name: str,
        timeout: Optional[float] = None,
    ) -> Optional[int]:
        """
        Wait for process termination and synchronize registry.
        """

        if timeout is not None:
            self._validate_timeout(timeout)

        with self._lock:
            process = self._get_process(name)

        process.join(timeout)

        with self._lock:

            if not process.is_alive():

                self._sync_dead_process(
                    name,
                    process,
                )

            return process.exitcode

    # ==========================================================
    # WAIT
    # ==========================================================

    def wait(
        self,
        name: str,
        timeout: Optional[float] = None,
    ) -> Optional[int]:
        """
        Alias for join().
        """

        return self.join(
            name,
            timeout,
        )

    # ==========================================================
    # STATUS
    # ==========================================================

    def status(
        self,
        name: str,
    ) -> ScraperStatus:
        """
        Return the persistent registry status.
        """

        record = self.registry.get(name)

        if record is None:
            raise KeyError(
                f"Scraper '{name}' does not exist."
            )

        if isinstance(record, ScraperInfo):
            return record.status

        if isinstance(record, dict):

            value = record.get("status")

            if isinstance(
                value,
                ScraperStatus,
            ):
                return value

            if value is None:
                raise ValueError(
                    f"Scraper '{name}' has no status."
                )

            try:
                return ScraperStatus(
                    str(value)
                    .strip()
                    .upper()
                )

            except ValueError as exc:
                raise ValueError(
                    f"Invalid scraper status: {value!r}"
                ) from exc

        raise TypeError(
            "ScraperRegistry.get() returned "
            f"unsupported type: {type(record).__name__}"
        )

    # ==========================================================
    # REFRESH
    # ==========================================================

    def refresh(
        self,
        name: Optional[str] = None,
    ) -> None:
        """
        Synchronize dead runtime processes with the registry.
        """

        with self._lock:

            if name is not None:

                process = self._get_process(name)

                if not process.is_alive():
                    self._sync_dead_process(
                        name,
                        process,
                    )

                return

            for scraper_name, process in list(
                self.processes.items()
            ):

                if not process.is_alive():

                    self._sync_dead_process(
                        scraper_name,
                        process,
                    )

    # ==========================================================
    # GET
    # ==========================================================

    def get(
        self,
        name: str,
    ) -> Optional[ScraperProcess]:

        with self._lock:
            return self.processes.get(name)

    # ==========================================================
    # REQUIRE
    # ==========================================================

    def require(
        self,
        name: str,
    ) -> ScraperProcess:

        process = self.get(name)

        if process is None:
            raise KeyError(
                f"Scraper process '{name}' does not exist."
            )

        return process

    # ==========================================================
    # RUNNING
    # ==========================================================

    def running(
        self,
    ) -> list[ScraperProcess]:

        with self._lock:

            return [
                process
                for process in self.processes.values()
                if process.is_alive()
            ]

    # ==========================================================
    # ALL
    # ==========================================================

    def all(
        self,
    ) -> list[ScraperProcess]:

        with self._lock:
            return list(
                self.processes.values()
            )

    # ==========================================================
    # COUNT
    # ==========================================================

    def count(
        self,
    ) -> int:

        with self._lock:
            return len(self.processes)

    # ==========================================================
    # EXISTS
    # ==========================================================

    def exists(
        self,
        name: str,
    ) -> bool:

        with self._lock:
            return name in self.processes

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(
        self,
        name: str,
    ) -> dict[str, Any]:
        """
        Return a stable process + registry snapshot.
        """

        with self._lock:

            process = self._get_process(name)

            record = self.registry.get(name)

            if isinstance(
                record,
                ScraperInfo,
            ):

                registry_snapshot = record.snapshot()

            elif isinstance(
                record,
                dict,
            ):

                registry_snapshot = dict(record)

            else:

                registry_snapshot = None

            process_snapshot = process.snapshot()

            return {
                "name": name,
                "process": process_snapshot,
                "registry": registry_snapshot,
            }

    # ==========================================================
    # SNAPSHOTS
    # ==========================================================

    def snapshots(
        self,
    ) -> list[dict[str, Any]]:

        with self._lock:
            names = list(
                self.processes.keys()
            )

        return [
            self.snapshot(name)
            for name in names
        ]

    # ==========================================================
    # REMOVE
    # ==========================================================

    def remove(
        self,
        name: str,
        force: bool = False,
        timeout: float = 10.0,
    ) -> bool:
        """
        Remove runtime process and persistent registry record.

        Running process:

            force=False -> reject

            force=True
                -> stop
                -> kill if required
                -> remove
        """

        self._validate_timeout(timeout)

        with self._lock:

            process = self._get_process(name)

            if process.is_alive():

                if not force:
                    raise RuntimeError(
                        f"Scraper '{name}' is still running."
                    )

                stopped = self.stop(
                    name,
                    timeout=timeout,
                )

                if not stopped:

                    killed = self.kill(
                        name,
                        timeout=3.0,
                    )

                    if not killed:
                        raise RuntimeError(
                            f"Could not terminate "
                            f"scraper '{name}'."
                        )

            self._stop_monitor(name)

            self.processes.pop(
                name,
                None,
            )

            self.registry.remove(name)

            return True

    # ==========================================================
    # REMOVE ALL
    # ==========================================================

    def remove_all(
        self,
        force: bool = False,
        timeout: float = 10.0,
    ) -> None:
        """
        Remove every managed scraper.
        """

        with self._lock:
            names = list(
                self.processes.keys()
            )

        for name in names:

            self.remove(
                name,
                force=force,
                timeout=timeout,
            )

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def shutdown(
        self,
        timeout: float = 10.0,
    ) -> None:
        """
        Stop all active processes.

        Registry records are intentionally preserved.
        """

        self._validate_timeout(timeout)

        with self._lock:
            names = list(
                self.processes.keys()
            )

        for name in names:

            try:

                process = self.get(name)

                if process is None:
                    continue

                if not process.is_alive():
                    self.refresh(name)
                    continue

                stopped = self.stop(
                    name,
                    timeout=timeout,
                )

                if not stopped:

                    self.kill(
                        name,
                        timeout=3.0,
                    )

            except Exception:

                # Shutdown continues with other processes.
                continue

        with self._lock:

            for name in list(
                self._monitor_stop_events.keys()
            ):
                self._stop_monitor(name)

    # ==========================================================
    # INTERNAL — BUILD PROCESS
    # ==========================================================

    def _build_process(
        self,
        name: str,
        provider: str,
        database: str,
        config: dict[str, Any],
        log_file: str,
        scraper_dir: str,
    ) -> ScraperProcess:
        """
        Build a completely new ScraperProcess.
        """

        return ScraperProcess(
            name=name,
            providers=[provider],
            database=database,
            config=dict(config),
            log_file=log_file,
            scraper_dir=scraper_dir,
        )

    # ==========================================================
    # INTERNAL — REBUILD
    # ==========================================================

    def _rebuild_process(
        self,
        name: str,
    ) -> ScraperProcess:
        """
        Rebuild a process from persistent registry state.
        """

        record = self.registry.get(name)

        if record is None:
            raise KeyError(
                f"Scraper '{name}' does not exist."
            )

        if not isinstance(
            record,
            ScraperInfo,
        ):
            raise TypeError(
                "ScraperRegistry.get() must return "
                "ScraperInfo."
            )

        if len(record.providers) != 1:
            raise ValueError(
                f"Scraper '{name}' must have "
                "exactly one provider."
            )

        provider = str(
            record.providers[0]
        ).strip().lower()

        if not provider:
            raise ValueError(
                f"Scraper '{name}' has an invalid provider."
            )

        config = dict(
            record.config
        )

        keyword = str(
            config.get(
                "keyword",
                "",
            )
        ).strip()

        if not keyword:
            raise ValueError(
                f"Scraper '{name}' has no keyword."
            )

        config["keyword"] = keyword

        if record.target is not None:
            config.setdefault(
                "target",
                record.target,
            )

        database = self._resolve_path(
            record.database,
            self.databases_dir / f"{name}.db",
        )

        log_file = self._resolve_path(
            record.log_file,
            self.logs_dir / f"{name}.log",
        )

        scraper_dir = self._resolve_path(
            record.scraper_dir,
            self.scrapers_dir / name,
        )

        database.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        log_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        scraper_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        return self._build_process(
            name=name,
            provider=provider,
            database=str(database),
            config=config,
            log_file=str(log_file),
            scraper_dir=str(scraper_dir),
        )

    # ==========================================================
    # INTERNAL — GET
    # ==========================================================

    def _get_process(
        self,
        name: str,
    ) -> ScraperProcess:

        process = self.processes.get(name)

        if process is None:
            raise KeyError(
                f"Scraper process '{name}' does not exist."
            )

        return process

    # ==========================================================
    # INTERNAL — START MONITOR
    # ==========================================================

    def _start_monitor(
        self,
        name: str,
    ) -> None:

        self._stop_monitor(name)

        generation = (
            self._monitor_generations.get(
                name,
                0,
            )
            + 1
        )

        self._monitor_generations[
            name
        ] = generation

        stop_event = threading.Event()

        self._monitor_stop_events[
            name
        ] = stop_event

        thread = threading.Thread(
            target=self._monitor_worker,
            args=(
                name,
                stop_event,
                generation,
            ),
            daemon=True,
            name=f"EYE-Monitor-{name}",
        )

        self._monitor_threads[
            name
        ] = thread

        thread.start()

    # ==========================================================
    # INTERNAL — STOP MONITOR
    # ==========================================================

    def _stop_monitor(
        self,
        name: str,
    ) -> None:

        event = self._monitor_stop_events.pop(
            name,
            None,
        )

        if event is not None:
            event.set()

        self._monitor_threads.pop(
            name,
            None,
        )

        self._monitor_generations[
            name
        ] = (
            self._monitor_generations.get(
                name,
                0,
            )
            + 1
        )

    # ==========================================================
    # INTERNAL — MONITOR WORKER
    # ==========================================================

    def _monitor_worker(
        self,
        name: str,
        stop_event: threading.Event,
        generation: int,
    ) -> None:
        """
        Observe only process lifecycle.

        No scraping logic is executed here.
        """

        while not stop_event.wait(0.5):

            with self._lock:

                if (
                    self._monitor_generations.get(
                        name
                    )
                    != generation
                ):
                    return

                process = self.processes.get(name)

                if process is None:
                    return

                if process.is_alive():
                    continue

                self._sync_dead_process(
                    name,
                    process,
                )

                return

    # ==========================================================
    # INTERNAL — SYNC DEAD PROCESS
    # ==========================================================

    def _sync_dead_process(
        self,
        name: str,
        process: ScraperProcess,
        stopped: bool = False,
        killed: bool = False,
    ) -> None:
        """
        Synchronize final runtime state with registry.

        Exit code semantics:

            0
                FINISHED

            SIGTERM
                STOPPED

            SIGKILL
                KILLED

            other negative / non-zero
                CRASHED
        """

        if process.is_alive():
            return

        exit_code = process.exitcode

        record = self.registry.get(name)

        if record is None:
            return

        current_status = self._record_status(record)

        # ------------------------------------------------------
        # FINAL STATUS
        # ------------------------------------------------------

        if killed:

            final_status = ScraperStatus.KILLED

        elif stopped:

            final_status = ScraperStatus.STOPPED

        elif exit_code == 0:

            final_status = ScraperStatus.FINISHED

        elif (
            isinstance(exit_code, int)
            and exit_code < 0
        ):

            if exit_code == -signal.SIGTERM:

                final_status = ScraperStatus.STOPPED

            elif exit_code == -signal.SIGKILL:

                final_status = ScraperStatus.KILLED

            else:

                final_status = ScraperStatus.CRASHED

        else:

            final_status = ScraperStatus.CRASHED

        # ------------------------------------------------------
        # REGISTRY
        # ------------------------------------------------------

        self.registry.set_pid(
            name,
            None,
        )

        self.registry.set_status(
            name,
            final_status,
            exit_code=exit_code,
        )

        # ------------------------------------------------------
        # MONITOR
        # ------------------------------------------------------

        active_statuses = {
            ScraperStatus.CREATED,
            ScraperStatus.STARTING,
            ScraperStatus.RUNNING,
            ScraperStatus.STOPPING,
        }

        if current_status in active_statuses:
            self._stop_monitor(name)

    # ==========================================================
    # INTERNAL — RECORD STATUS
    # ==========================================================

    @staticmethod
    def _record_status(
        record: Any,
    ) -> Optional[ScraperStatus]:

        if isinstance(
            record,
            ScraperInfo,
        ):
            return record.status

        if isinstance(
            record,
            dict,
        ):

            value = record.get("status")

            if isinstance(
                value,
                ScraperStatus,
            ):
                return value

            if value is None:
                return None

            try:

                return ScraperStatus(
                    str(value)
                    .strip()
                    .upper()
                )

            except ValueError:

                return None

        return None

    # ==========================================================
    # INTERNAL — WAIT PROCESS
    # ==========================================================

    @staticmethod
    def _wait_process(
        process: ScraperProcess,
        timeout: float,
    ) -> bool:
        """
        Wait for process termination without holding manager lock.
        """

        deadline = (
            time.monotonic()
            + timeout
        )

        while process.is_alive():

            remaining = (
                deadline
                - time.monotonic()
            )

            if remaining <= 0:
                return False

            time.sleep(
                min(
                    0.1,
                    remaining,
                )
            )

        return True

    # ==========================================================
    # INTERNAL — PROCESS STARTED
    # ==========================================================

    @staticmethod
    def _process_has_started(
        process: ScraperProcess,
    ) -> bool:
        """
        Detect whether the underlying multiprocessing.Process
        has already been started.

        ScraperProcess is expected to expose the underlying
        Process as `process`.
        """

        child = getattr(
            process,
            "process",
            None,
        )

        if child is None:
            return False

        return getattr(
            child,
            "pid",
            None,
        ) is not None

    # ==========================================================
    # INTERNAL — PATH
    # ==========================================================

    @staticmethod
    def _resolve_path(
        value: Optional[str],
        default: Path,
    ) -> Path:
        """
        Resolve an optional filesystem path.

        Explicit relative paths remain relative to the current
        application working directory, preserving the caller's
        configured path semantics.
        """

        if value is None:

            return default

        value = str(value).strip()

        if not value:

            return default

        return Path(
            value
        ).expanduser()

    # ==========================================================
    # INTERNAL — TIMEOUT
    # ==========================================================

    @staticmethod
    def _validate_timeout(
        timeout: float,
    ) -> None:

        if timeout < 0:
            raise ValueError(
                "timeout cannot be negative."
            )

    # ==========================================================
    # REPRESENTATION
    # ==========================================================

    def __repr__(
        self,
    ) -> str:

        return (
            f"<ProcessManager "
            f"processes={self.count()}>"
        )