# ============================================================
# EYES MASTER — SCRAPER REGISTRY
# ============================================================
#
# FILE:
#     master/scraper_registry.py
#
# ROLE:
#     Persistent metadata registry for scraper instances.
#
# RESPONSIBILITIES:
#     - Register scraper
#     - Retrieve scraper metadata
#     - Update configuration/runtime metadata
#     - Manage logical lifecycle status
#     - Store PID / exit code / error
#     - Persist registry atomically
#     - Restore registry on startup
#     - Query scraper states
#
# DOES NOT:
#     - Create processes
#     - Start processes
#     - Stop processes
#     - Kill processes
#     - Execute providers
#     - Execute scraping
#     - Own ScraperProcess objects
#
# ARCHITECTURE:
#
#     ScraperRegistry
#            │
#            └── ScraperInfo
#
#     ProcessManager
#            │
#            ├── ScraperRegistry
#            └── ScraperProcess
#
# IMPORTANT:
#
#     Registry is the persistent logical source of truth.
#     Runtime process objects remain owned by ProcessManager.
#
# ============================================================

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Optional

from .models import (
    ScraperInfo,
    ScraperStatus,
)


class ScraperRegistry:
    """
    Persistent registry for EYES scrapers.

    The registry stores logical scraper metadata only.

    It never owns or controls multiprocessing.Process
    instances.
    """

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

    def __init__(
        self,
        registry_file: Optional[
            str | Path
        ] = None,
    ) -> None:

        self.base_dir = (
            Path(__file__)
            .resolve()
            .parent
            .parent
        )

        self.runtime_dir = (
            self.base_dir / "runtime"
        )

        self.runtime_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.registry_file = Path(
            registry_file
            if registry_file is not None
            else (
                self.runtime_dir
                / "scrapers.json"
            )
        ).expanduser()

        self._lock = threading.RLock()

        self.scrapers: dict[
            str,
            ScraperInfo,
        ] = {}

        self._load()

    # ==========================================================
    # NORMALIZATION
    # ==========================================================

    @staticmethod
    def _normalize_name(
        name: str,
    ) -> str:

        normalized = str(
            name
        ).strip()

        if not normalized:

            raise ValueError(
                "Scraper name cannot be empty."
            )

        return normalized

    @staticmethod
    def _normalize_providers(
        providers: Any,
    ) -> list[str]:

        if providers is None:

            return []

        if isinstance(
            providers,
            str,
        ):

            providers = [
                providers
            ]

        if not isinstance(
            providers,
            (list, tuple, set),
        ):

            raise TypeError(
                "providers must be a string "
                "or a collection of strings."
            )

        result: list[str] = []

        seen: set[str] = set()

        for provider in providers:

            value = str(
                provider
            ).strip().lower()

            if not value:
                continue

            if value in seen:
                continue

            seen.add(
                value
            )

            result.append(
                value
            )

        return result

    # ==========================================================
    # REGISTER
    # ==========================================================

    def register(
        self,
        scraper: Optional[
            ScraperInfo
        ] = None,
        *,
        name: Optional[str] = None,
        pid: Optional[int] = None,
        providers: Optional[
            list[str] | str
        ] = None,
        target: Optional[str] = None,
        database: Optional[str] = None,
        log_file: Optional[str] = None,
        scraper_dir: Optional[str] = None,
        config: Optional[
            dict[str, Any]
        ] = None,
    ) -> ScraperInfo:
        """
        Register a new scraper.

        Supports both:

            register(
                ScraperInfo(...)
            )

        and compatibility form:

            register(
                name="school",
                providers=["google"],
                ...
            )
        """

        with self._lock:

            # --------------------------------------------------
            # BUILD MODEL
            # --------------------------------------------------

            if scraper is None:

                if name is None:

                    raise ValueError(
                        "Scraper name is required."
                    )

                normalized_providers = (
                    self._normalize_providers(
                        providers
                    )
                )

                scraper = ScraperInfo(
                    name=name,
                    providers=normalized_providers,
                    target=target,
                    config=dict(
                        config or {}
                    ),
                    database=database,
                    log_file=log_file,
                    scraper_dir=scraper_dir,
                    pid=pid,
                )

            elif not isinstance(
                scraper,
                ScraperInfo,
            ):

                raise TypeError(
                    "scraper must be a "
                    "ScraperInfo instance."
                )

            # --------------------------------------------------
            # VALIDATE
            # --------------------------------------------------

            scraper.validate()

            scraper_name = (
                self._normalize_name(
                    scraper.name
                )
            )

            # --------------------------------------------------
            # DUPLICATE
            # --------------------------------------------------

            if scraper_name in self.scrapers:

                raise ValueError(
                    f"Scraper already exists: "
                    f"{scraper_name}"
                )

            # --------------------------------------------------
            # STORE COPY
            # --------------------------------------------------

            stored = scraper.copy()

            self.scrapers[
                scraper_name
            ] = stored

            self._save()

            return stored.copy()

    # ==========================================================
    # EXISTS
    # ==========================================================

    def exists(
        self,
        name: str,
    ) -> bool:

        name = self._normalize_name(
            name
        )

        with self._lock:

            return name in self.scrapers

    # ==========================================================
    # GET
    # ==========================================================

    def get(
        self,
        name: str,
    ) -> Optional[ScraperInfo]:

        name = self._normalize_name(
            name
        )

        with self._lock:

            scraper = self.scrapers.get(
                name
            )

            if scraper is None:

                return None

            return scraper.copy()

    # ==========================================================
    # REQUIRE
    # ==========================================================

    def require(
        self,
        name: str,
    ) -> ScraperInfo:

        scraper = self.get(
            name
        )

        if scraper is None:

            raise KeyError(
                f"Scraper '{name}' does not exist."
            )

        return scraper

    # ==========================================================
    # ALL
    # ==========================================================

    def all(
        self,
    ) -> list[ScraperInfo]:

        with self._lock:

            return [
                scraper.copy()
                for scraper
                in self.scrapers.values()
            ]

    # ==========================================================
    # UPDATE
    # ==========================================================

    def update(
        self,
        name: str,
        **fields: Any,
    ) -> ScraperInfo:
        """
        Update mutable scraper metadata.

        Identity and creation timestamp are immutable.
        """

        name = self._normalize_name(
            name
        )

        with self._lock:

            scraper = self.scrapers.get(
                name
            )

            if scraper is None:

                raise KeyError(
                    f"Scraper '{name}' does not exist."
                )

            protected = {
                "name",
                "created_at",
            }

            for key, value in fields.items():

                if key in protected:

                    continue

                if not hasattr(
                    scraper,
                    key,
                ):

                    continue

                if key == "providers":

                    value = (
                        self._normalize_providers(
                            value
                        )
                    )

                elif key == "config":

                    if not isinstance(
                        value,
                        dict,
                    ):

                        raise TypeError(
                            "config must be a dictionary."
                        )

                    value = dict(
                        value
                    )

                elif key == "status":

                    value = (
                        ScraperInfo.normalize_status(
                            value
                        )
                    )

                elif key in {
                    "database",
                    "log_file",
                    "scraper_dir",
                }:

                    if value is not None:

                        value = str(
                            value
                        )

                setattr(
                    scraper,
                    key,
                    value,
                )

            scraper.updated_at = (
                time.time()
            )

            # --------------------------------------------------
            # VALIDATE AFTER UPDATE
            # --------------------------------------------------

            scraper.validate()

            self._save()

            return scraper.copy()

    # ==========================================================
    # STATUS
    # ==========================================================

    def set_status(
        self,
        name: str,
        status: ScraperStatus | str,
        error: Optional[str] = None,
        exit_code: Optional[int] = None,
    ) -> ScraperInfo:

        name = self._normalize_name(
            name
        )

        with self._lock:

            scraper = self.scrapers.get(
                name
            )

            if scraper is None:

                raise KeyError(
                    f"Scraper '{name}' does not exist."
                )

            scraper.set_status(
                status=status,
                error=error,
                exit_code=exit_code,
            )

            self._save()

            return scraper.copy()

    # ==========================================================
    # PID
    # ==========================================================

    def set_pid(
        self,
        name: str,
        pid: Optional[int],
    ) -> ScraperInfo:

        if pid is not None:

            pid = int(
                pid
            )

            if pid <= 0:

                raise ValueError(
                    "PID must be greater than zero."
                )

        return self.update(
            name,
            pid=pid,
        )

    # ==========================================================
    # ERROR
    # ==========================================================

    def set_error(
        self,
        name: str,
        error: Optional[str],
    ) -> ScraperInfo:

        return self.update(
            name,
            error=(
                str(error)
                if error is not None
                else None
            ),
        )

    # ==========================================================
    # EXIT CODE
    # ==========================================================

    def set_exit_code(
        self,
        name: str,
        exit_code: Optional[int],
    ) -> ScraperInfo:

        if exit_code is not None:

            exit_code = int(
                exit_code
            )

        return self.update(
            name,
            exit_code=exit_code,
        )

    # ==========================================================
    # DATABASE
    # ==========================================================

    def set_database(
        self,
        name: str,
        database: Optional[str],
    ) -> ScraperInfo:

        return self.update(
            name,
            database=(
                str(database)
                if database is not None
                else None
            ),
        )

    # ==========================================================
    # LOG FILE
    # ==========================================================

    def set_log_file(
        self,
        name: str,
        log_file: Optional[str],
    ) -> ScraperInfo:

        return self.update(
            name,
            log_file=(
                str(log_file)
                if log_file is not None
                else None
            ),
        )

    # ==========================================================
    # SCRAPER DIRECTORY
    # ==========================================================

    def set_scraper_dir(
        self,
        name: str,
        scraper_dir: Optional[str],
    ) -> ScraperInfo:

        return self.update(
            name,
            scraper_dir=(
                str(scraper_dir)
                if scraper_dir is not None
                else None
            ),
        )

    # ==========================================================
    # CONFIGURATION
    # ==========================================================

    def set_config(
        self,
        name: str,
        config: dict[str, Any],
    ) -> ScraperInfo:

        if not isinstance(
            config,
            dict,
        ):

            raise TypeError(
                "config must be a dictionary."
            )

        return self.update(
            name,
            config=dict(
                config
            ),
        )

    # ==========================================================
    # PROVIDERS
    # ==========================================================

    def set_providers(
        self,
        name: str,
        providers: list[str] | str,
    ) -> ScraperInfo:

        normalized = (
            self._normalize_providers(
                providers
            )
        )

        return self.update(
            name,
            providers=normalized,
        )

    # ==========================================================
    # REMOVE
    # ==========================================================

    def remove(
        self,
        name: str,
    ) -> bool:

        name = self._normalize_name(
            name
        )

        with self._lock:

            if name not in self.scrapers:

                return False

            del self.scrapers[
                name
            ]

            self._save()

            return True

    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear(
        self,
    ) -> None:

        with self._lock:

            self.scrapers.clear()

            self._save()

    # ==========================================================
    # FIND BY PID
    # ==========================================================

    def find_by_pid(
        self,
        pid: int,
    ) -> Optional[ScraperInfo]:

        pid = int(
            pid
        )

        with self._lock:

            for scraper in (
                self.scrapers.values()
            ):

                if scraper.pid == pid:

                    return scraper.copy()

        return None

    # ==========================================================
    # FIND BY STATUS
    # ==========================================================

    def find_by_status(
        self,
        status: ScraperStatus | str,
    ) -> list[ScraperInfo]:

        normalized = (
            ScraperInfo.normalize_status(
                status
            )
        )

        with self._lock:

            return [
                scraper.copy()
                for scraper
                in self.scrapers.values()
                if scraper.status
                == normalized
            ]

    # ==========================================================
    # RUNNING
    # ==========================================================

    def running(
        self,
    ) -> list[ScraperInfo]:

        return self.find_by_status(
            ScraperStatus.RUNNING
        )

    # ==========================================================
    # STARTING
    # ==========================================================

    def starting(
        self,
    ) -> list[ScraperInfo]:

        return self.find_by_status(
            ScraperStatus.STARTING
        )

    # ==========================================================
    # STOPPING
    # ==========================================================

    def stopping(
        self,
    ) -> list[ScraperInfo]:

        return self.find_by_status(
            ScraperStatus.STOPPING
        )

    # ==========================================================
    # ACTIVE
    # ==========================================================

    def active(
        self,
    ) -> list[ScraperInfo]:

        with self._lock:

            return [
                scraper.copy()
                for scraper
                in self.scrapers.values()
                if scraper.is_active
            ]

    # ==========================================================
    # FINISHED
    # ==========================================================

    def finished(
        self,
    ) -> list[ScraperInfo]:

        with self._lock:

            return [
                scraper.copy()
                for scraper
                in self.scrapers.values()
                if scraper.is_finished
                and scraper.status
                != ScraperStatus.CRASHED
            ]

    # ==========================================================
    # CRASHED
    # ==========================================================

    def crashed(
        self,
    ) -> list[ScraperInfo]:

        return self.find_by_status(
            ScraperStatus.CRASHED
        )

    # ==========================================================
    # STOPPED
    # ==========================================================

    def stopped(
        self,
    ) -> list[ScraperInfo]:

        return self.find_by_status(
            ScraperStatus.STOPPED
        )

    # ==========================================================
    # KILLED
    # ==========================================================

    def killed(
        self,
    ) -> list[ScraperInfo]:

        return self.find_by_status(
            ScraperStatus.KILLED
        )

    # ==========================================================
    # DATABASES
    # ==========================================================

    def databases(
        self,
    ) -> list[dict[str, Any]]:

        with self._lock:

            return [
                {
                    "name": scraper.name,
                    "database": scraper.database,
                    "status": scraper.status.value,
                }
                for scraper
                in self.scrapers.values()
                if scraper.database
            ]

    # ==========================================================
    # COUNT
    # ==========================================================

    def count(
        self,
    ) -> int:

        with self._lock:

            return len(
                self.scrapers
            )

    # ==========================================================
    # SAVE
    # ==========================================================

    def _save(
        self,
    ) -> None:
        """
        Atomically persist registry.

        JSON is written to a temporary file first and then
        replaced over the real registry file.
        """

        self.registry_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_file = (
            self.registry_file.with_name(
                self.registry_file.name
                + ".tmp"
            )
        )

        data = {
            name: scraper.to_dict()
            for name, scraper
            in self.scrapers.items()
        }

        with temporary_file.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False,
            )

            file.write(
                "\n"
            )

            file.flush()

        temporary_file.replace(
            self.registry_file
        )

    # ==========================================================
    # LOAD
    # ==========================================================

    def _load(
        self,
    ) -> None:

        if not self.registry_file.exists():

            return

        try:

            with self.registry_file.open(
                "r",
                encoding="utf-8",
            ) as file:

                data = json.load(
                    file
                )

        except (
            json.JSONDecodeError,
            OSError,
            TypeError,
        ):

            self.scrapers = {}

            return

        if not isinstance(
            data,
            dict,
        ):

            self.scrapers = {}

            return

        restored: dict[
            str,
            ScraperInfo,
        ] = {}

        for name, raw in data.items():

            try:

                if not isinstance(
                    raw,
                    dict,
                ):

                    continue

                scraper = (
                    ScraperInfo.from_dict(
                        raw
                    )
                )

                # ------------------------------------------------
                # Registry key is always the model identity.
                # ------------------------------------------------

                if not scraper.name:

                    scraper.name = (
                        str(name).strip()
                    )

                scraper.validate()

                restored[
                    scraper.name
                ] = scraper

            except (
                TypeError,
                ValueError,
            ):

                continue

        self.scrapers = restored

    # ==========================================================
    # DUMP
    # ==========================================================

    def dump(
        self,
    ) -> dict[str, Any]:

        with self._lock:

            return {
                name: scraper.to_dict()
                for name, scraper
                in self.scrapers.items()
            }

    # ==========================================================
    # RELOAD
    # ==========================================================

    def reload(
        self,
    ) -> None:

        with self._lock:

            self.scrapers.clear()

            self._load()

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(
        self,
    ) -> dict[str, Any]:

        with self._lock:

            return {
                "registry_file":
                    str(
                        self.registry_file
                    ),

                "count":
                    len(
                        self.scrapers
                    ),

                "scrapers":
                    {
                        name:
                            scraper.snapshot()
                        for name, scraper
                        in self.scrapers.items()
                    },
            }

    # ==========================================================
    # ITERATION
    # ==========================================================

    def __len__(
        self,
    ) -> int:

        return self.count()

    def __contains__(
        self,
        name: str,
    ) -> bool:

        return self.exists(
            name
        )

    def __iter__(
        self,
    ):

        return iter(
            self.all()
        )

    # ==========================================================
    # REPRESENTATION
    # ==========================================================

    def __repr__(
        self,
    ) -> str:

        return (
            "<ScraperRegistry "
            f"count={self.count()} "
            f"file={str(self.registry_file)!r}>"
        )   