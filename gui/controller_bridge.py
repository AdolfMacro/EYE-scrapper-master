# ==========================================================
# وضعیت فعلی فایل
# ==========================================================
#
# FILE:
# gui/controller_bridge.py
#
# STATUS:
# 🟢 سالم — نسخه اصلاح‌شده و Canonical
#
# ROLE:
# تنها مرز ارتباطی GUI با Master Layer.
#
# CURRENT STATE:
# GUIController تمام عملیات lifecycle، status، snapshot،
# registry و action availability را به ProcessManager واگذار
# می‌کند و GUI را از جزئیات داخلی Master جدا نگه می‌دارد.
#
# PROBLEMS FIXED:
# 1. حذف منطق تکراری و ناسازگار create_scraper.
# 2. پشتیبانی همزمان از API جدید و legacy.
# 3. enforce شدن قرارداد One Child Scraper = One Provider.
# 4. نرمال‌سازی پایدار keyword / keywords.
# 5. جلوگیری از mutation ناخواسته config.
# 6. نرمال‌سازی timeout ها.
# 7. fallback امن برای join / wait / get / require.
# 8. snapshot ها همیشه خروجی dict می‌دهند.
# 9. available_actions منطق lifecycle را به شکل پایدار
#    به GUI ارائه می‌کند.
# 10. registry همیشه از manager فعال resolve می‌شود.
#
# ARCHITECTURE:
# GUI
#   ↓
# GUIController
#   ↓
# ProcessManager
#   ├── ScraperProcess
#   ├── ScraperWorker
#   └── ScraperRegistry
#
# COMPATIBILITY:
# Compatible with:
# - create_scraper(data)
# - create_scraper(name=..., provider=...)
# - create_scraper(name=..., providers=[...])
# - create_scraper("name", ["google"])
# - keyword
# - keywords
#
# REQUIRED CHANGES:
# No external change required if ProcessManager exposes the
# canonical methods used below.
#
# DECISION:
# نگه‌داری — Canonical GUI Boundary
#
# SCORE:
# 9.5/10
#
# ==========================================================

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from master.models import (
    ScraperInfo,
    ScraperStatus,
)
from master.process_manager import ProcessManager
from master.scraper_registry import ScraperRegistry


class GUIController:
    """
    Canonical GUI-facing boundary for EYES Master.

    The GUI communicates with the Master layer through this class.

    GUIController does NOT perform:

        - scraping
        - provider execution
        - database operations
        - multiprocessing
        - worker execution
        - engine execution

    Architectural rule:

        One Child Scraper = One Provider
    """

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(
        self,
        process_manager: Optional[ProcessManager] = None,
        registry_path: Optional[str | Path] = None,
        runtime_dir: Optional[str | Path] = None,
    ) -> None:

        self.manager: ProcessManager
        self.registry: Optional[ScraperRegistry]
        self.runtime_dir: Optional[Path]
        self.registry_path: Optional[Path]

        # ------------------------------------------------------
        # Existing ProcessManager
        # ------------------------------------------------------

        if process_manager is not None:

            self.manager = process_manager

            self.registry = getattr(
                process_manager,
                "registry",
                None,
            )

            runtime = getattr(
                process_manager,
                "runtime_dir",
                None,
            )

            self.runtime_dir = (
                Path(runtime)
                if runtime is not None
                else None
            )

            registry_file = getattr(
                self.registry,
                "registry_file",
                None,
            )

            self.registry_path = (
                Path(registry_file)
                if registry_file is not None
                else None
            )

            return

        # ------------------------------------------------------
        # Project paths
        # ------------------------------------------------------

        self.base_dir = (
            Path(__file__)
            .resolve()
            .parent
            .parent
        )

        self.runtime_dir = Path(
            runtime_dir
            or self.base_dir / "runtime"
        ).expanduser()

        self.runtime_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.registry_path = Path(
            registry_path
            or self.runtime_dir / "scrapers.json"
        ).expanduser()

        self.registry_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ------------------------------------------------------
        # Registry
        # ------------------------------------------------------

        self.registry = ScraperRegistry(
            registry_file=self.registry_path
        )

        # ------------------------------------------------------
        # Process Manager
        # ------------------------------------------------------

        self.manager = ProcessManager(
            registry=self.registry,
            runtime_dir=self.runtime_dir,
        )

    # ==========================================================
    # INTERNAL — MANAGER
    # ==========================================================

    def _require_manager(self) -> ProcessManager:
        """
        Return the active ProcessManager.
        """

        if self.manager is None:

            raise RuntimeError(
                "GUIController is not connected "
                "to a ProcessManager."
            )

        return self.manager

    # ==========================================================
    # INTERNAL — NAME
    # ==========================================================

    @staticmethod
    def _require_name(
        name: Any,
    ) -> str:

        if not isinstance(
            name,
            str,
        ):

            raise TypeError(
                "Scraper name must be a string."
            )

        value = name.strip()

        if not value:

            raise ValueError(
                "Scraper name cannot be empty."
            )

        return value

    # ==========================================================
    # INTERNAL — PROVIDER
    # ==========================================================

    @staticmethod
    def _normalize_provider(
        provider: Any,
    ) -> str:

        if not isinstance(
            provider,
            str,
        ):

            raise TypeError(
                "Provider name must be a string."
            )

        value = provider.strip().lower()

        if not value:

            raise ValueError(
                "Provider name cannot be empty."
            )

        return value

    # ==========================================================
    # INTERNAL — PROVIDERS
    # ==========================================================

    @classmethod
    def _normalize_providers(
        cls,
        providers: Any = None,
        provider: Any = None,
    ) -> list[str]:
        """
        Normalize provider input.

        Supported:

            provider="google"

            providers="google"

            providers=["google"]

            providers=("google",)

        Exactly one provider is allowed.
        """

        # ------------------------------------------------------
        # Singular provider has priority.
        # ------------------------------------------------------

        if provider is not None:

            return [
                cls._normalize_provider(
                    provider
                )
            ]

        if providers is None:

            raise ValueError(
                "Exactly one provider is required."
            )

        # ------------------------------------------------------
        # Legacy string.
        # ------------------------------------------------------

        if isinstance(
            providers,
            str,
        ):

            return [
                cls._normalize_provider(
                    providers
                )
            ]

        # ------------------------------------------------------
        # Collection.
        # ------------------------------------------------------

        if not isinstance(
            providers,
            (list, tuple, set),
        ):

            raise TypeError(
                "Providers must be a string, "
                "list, tuple, or set."
            )

        normalized: list[str] = []

        for item in providers:

            if item is None:
                continue

            value = cls._normalize_provider(
                item
            )

            if value not in normalized:

                normalized.append(
                    value
                )

        if len(normalized) != 1:

            raise ValueError(
                "Each child scraper must use "
                "exactly one provider."
            )

        return normalized

    # ==========================================================
    # INTERNAL — CONFIG
    # ==========================================================

    @staticmethod
    def _normalize_config(
        config: Any,
    ) -> dict[str, Any]:

        if config is None:

            return {}

        if not isinstance(
            config,
            dict,
        ):

            raise TypeError(
                "Scraper config must be a dictionary."
            )

        return dict(
            config
        )

    # ==========================================================
    # INTERNAL — CONFIG VALUE
    # ==========================================================

    @staticmethod
    def _config_value(
        config: dict[str, Any],
        *names: str,
    ) -> Any:
        """
        Resolve configuration values.

        Priority:

            config[name]
                ↓
            config["search"][name]
                ↓
            config["search_config"][name]
        """

        for name in names:

            if name not in config:
                continue

            value = config[name]

            if value is None:
                continue

            if isinstance(
                value,
                str,
            ):

                value = value.strip()

                if not value:
                    continue

            return value

        for section_name in (
            "search",
            "search_config",
        ):

            section = config.get(
                section_name
            )

            if not isinstance(
                section,
                dict,
            ):
                continue

            for name in names:

                if name not in section:
                    continue

                value = section[name]

                if value is None:
                    continue

                if isinstance(
                    value,
                    str,
                ):

                    value = value.strip()

                    if not value:
                        continue

                return value

        return None

    # ==========================================================
    # INTERNAL — KEYWORDS
    # ==========================================================

    @staticmethod
    def _normalize_keywords(
        value: Any,
    ) -> list[str]:

        if value is None:
            return []

        # ------------------------------------------------------
        # Single keyword.
        # ------------------------------------------------------

        if isinstance(
            value,
            str,
        ):

            value = value.strip()

            return (
                [value]
                if value
                else []
            )

        # ------------------------------------------------------
        # Collection.
        # ------------------------------------------------------

        if not isinstance(
            value,
            (list, tuple, set),
        ):

            raise TypeError(
                "Keywords must be a string, "
                "list, tuple, or set."
            )

        result: list[str] = []

        seen: set[str] = set()

        for item in value:

            if item is None:
                continue

            item = str(
                item
            ).strip()

            if not item:
                continue

            key = item.casefold()

            if key in seen:
                continue

            seen.add(key)

            result.append(item)

        return result

    # ==========================================================
    # INTERNAL — VALIDATE CONFIG
    # ==========================================================

    @classmethod
    def _validate_config(
        cls,
        config: dict[str, Any],
    ) -> dict[str, Any]:

        normalized = dict(
            config
        )

        # ======================================================
        # MULTI KEYWORD
        # ======================================================

        multi_value = cls._config_value(
            normalized,
            "keywords",
            "search_keywords",
        )

        if multi_value is not None:

            keywords = cls._normalize_keywords(
                multi_value
            )

            if keywords:

                normalized["keywords"] = list(
                    keywords
                )

                normalized["keyword"] = (
                    keywords[0]
                )

                normalized.pop(
                    "search_keywords",
                    None,
                )

                return normalized

        # ======================================================
        # SINGLE KEYWORD
        # ======================================================

        single_value = cls._config_value(
            normalized,
            "keyword",
            "search_keyword",
        )

        keywords = cls._normalize_keywords(
            single_value
        )

        if not keywords:

            raise ValueError(
                "Scraper keyword is required."
            )

        normalized["keywords"] = list(
            keywords
        )

        normalized["keyword"] = (
            keywords[0]
        )

        normalized.pop(
            "search_keyword",
            None,
        )

        return normalized

    # ==========================================================
    # INTERNAL — TARGET
    # ==========================================================

    @staticmethod
    def _normalize_target(
        target: Any,
    ) -> Optional[str]:

        if target is None:
            return None

        value = str(
            target
        ).strip()

        return value or None

    # ==========================================================
    # INTERNAL — DATABASE
    # ==========================================================

    def _normalize_database(
        self,
        database: Any,
        name: str,
    ) -> str:

        runtime_dir = (
            self.runtime_dir
            or (
                self.base_dir / "runtime"
                if hasattr(self, "base_dir")
                else Path("runtime")
            )
        )

        default_path = (
            Path(runtime_dir)
            / "databases"
            / f"{name}.db"
        )

        if database is None:

            return str(
                default_path
            )

        value = str(
            database
        ).strip()

        return (
            value
            or str(default_path)
        )

    # ==========================================================
    # INTERNAL — CREATE ARGUMENTS
    # ==========================================================

    def _normalize_create_arguments(
        self,
        data: Any = None,
        *,
        name: Optional[str] = None,
        provider: Optional[str] = None,
        providers: Any = None,
        target: Optional[str] = None,
        database: Optional[str] = None,
        config: Optional[dict[str, Any]] = None,
        log_file: Optional[str] = None,
        scraper_dir: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Normalize all supported create_scraper forms.
        """

        # ------------------------------------------------------
        # Dictionary payload.
        # ------------------------------------------------------

        if data is not None:

            if isinstance(
                data,
                dict,
            ):

                payload = dict(
                    data
                )

                if name is not None:
                    payload["name"] = name

                if provider is not None:
                    payload["provider"] = provider

                if providers is not None:
                    payload["providers"] = providers

                if target is not None:
                    payload["target"] = target

                if database is not None:
                    payload["database"] = database

                if config is not None:
                    payload["config"] = config

                if log_file is not None:
                    payload["log_file"] = log_file

                if scraper_dir is not None:
                    payload["scraper_dir"] = scraper_dir

                name = payload.get(
                    "name",
                    payload.get(
                        "scraper_name"
                    ),
                )

                provider = payload.get(
                    "provider"
                )

                providers = payload.get(
                    "providers"
                )

                target = payload.get(
                    "target"
                )

                database = payload.get(
                    "database"
                )

                config = payload.get(
                    "config"
                )

                log_file = payload.get(
                    "log_file"
                )

                scraper_dir = payload.get(
                    "scraper_dir"
                )

                # Remaining fields become config.
                reserved = {
                    "name",
                    "scraper_name",
                    "provider",
                    "providers",
                    "target",
                    "database",
                    "config",
                    "log_file",
                    "scraper_dir",
                }

                extras = {
                    key: value
                    for key, value in payload.items()
                    if key not in reserved
                }

                if extras:

                    base_config = (
                        self._normalize_config(
                            config
                        )
                    )

                    merged_config = dict(
                        extras
                    )

                    merged_config.update(
                        base_config
                    )

                    config = merged_config

            else:

                if name is None:
                    name = data

        # ------------------------------------------------------
        # Name.
        # ------------------------------------------------------

        name = self._require_name(
            name
        )

        # ------------------------------------------------------
        # Provider.
        # ------------------------------------------------------

        normalized_providers = (
            self._normalize_providers(
                providers=providers,
                provider=provider,
            )
        )

        # ------------------------------------------------------
        # Config.
        # ------------------------------------------------------

        normalized_config = (
            self._normalize_config(
                config
            )
        )

        normalized_config = (
            self._validate_config(
                normalized_config
            )
        )

        # ------------------------------------------------------
        # Other fields.
        # ------------------------------------------------------

        target = self._normalize_target(
            target
        )

        database = self._normalize_database(
            database,
            name,
        )

        if log_file is not None:

            log_file = (
                str(log_file).strip()
                or None
            )

        if scraper_dir is not None:

            scraper_dir = (
                str(scraper_dir).strip()
                or None
            )

        return {
            "name": name,
            "providers": normalized_providers,
            "target": target,
            "database": database,
            "config": normalized_config,
            "log_file": log_file,
            "scraper_dir": scraper_dir,
        }

    # ==========================================================
    # CREATE
    # ==========================================================

    def create_scraper(
        self,
        name: Optional[
            str | dict[str, Any]
        ] = None,
        providers: Any = None,
        target: Optional[str] = None,
        database: Optional[str] = None,
        config: Optional[dict[str, Any]] = None,
        log_file: Optional[str] = None,
        scraper_dir: Optional[str] = None,
        provider: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Create a scraper without starting it.

        Supported:

            create_scraper({
                "name": "schools",
                "provider": "google",
                "keyword": "مدرسه",
            })

            create_scraper(
                name="schools",
                provider="google",
                config={...},
            )

            create_scraper(
                name="schools",
                providers=["google"],
                config={...},
            )

            create_scraper(
                "schools",
                ["google"],
            )

        Canonical architectural rule:

            One Child Scraper = One Provider
        """

        # ------------------------------------------------------
        # Merge arbitrary keyword arguments into config.
        # ------------------------------------------------------

        if kwargs:

            base_config = (
                self._normalize_config(
                    config
                )
            )

            merged_config = dict(
                kwargs
            )

            merged_config.update(
                base_config
            )

            config = merged_config

        # ------------------------------------------------------
        # Normalize everything before touching manager.
        # ------------------------------------------------------

        normalized = (
            self._normalize_create_arguments(
                data=name
                if isinstance(
                    name,
                    dict,
                )
                else None,
                name=(
                    None
                    if isinstance(
                        name,
                        dict,
                    )
                    else name
                ),
                provider=provider,
                providers=providers,
                target=target,
                database=database,
                config=config,
                log_file=log_file,
                scraper_dir=scraper_dir,
            )
        )

        # ------------------------------------------------------
        # ProcessManager is called ONLY after full validation.
        # ------------------------------------------------------

        return self._require_manager().create(
            name=normalized["name"],
            providers=normalized["providers"],
            target=normalized["target"],
            database=normalized["database"],
            config=normalized["config"],
            log_file=normalized["log_file"],
            scraper_dir=normalized["scraper_dir"],
        )

    # ==========================================================
    # START
    # ==========================================================

    def start(
        self,
        name: str,
    ) -> Any:

        return self._require_manager().start(
            self._require_name(name)
        )

    # ==========================================================
    # STOP
    # ==========================================================

    def stop(
        self,
        name: str,
        timeout: float = 10.0,
    ) -> bool:

        return bool(
            self._require_manager().stop(
                self._require_name(name),
                timeout=float(timeout),
            )
        )

    # ==========================================================
    # KILL
    # ==========================================================

    def kill(
        self,
        name: str,
        timeout: float = 3.0,
    ) -> bool:

        return bool(
            self._require_manager().kill(
                self._require_name(name),
                timeout=float(timeout),
            )
        )

    # ==========================================================
    # RESTART
    # ==========================================================

    def restart(
        self,
        name: str,
        timeout: float = 10.0,
    ) -> Any:

        return self._require_manager().restart(
            self._require_name(name),
            timeout=float(timeout),
        )

    # ==========================================================
    # FORCE RESTART
    # ==========================================================

    def restart_force(
        self,
        name: str,
        stop_timeout: float = 5.0,
        kill_timeout: float = 3.0,
    ) -> Any:

        return self._require_manager().restart_force(
            self._require_name(name),
            stop_timeout=float(stop_timeout),
            kill_timeout=float(kill_timeout),
        )

    # ==========================================================
    # JOIN
    # ==========================================================

    def join(
        self,
        name: str,
        timeout: Optional[float] = None,
    ) -> Optional[int]:

        manager = self._require_manager()
        name = self._require_name(name)

        method = getattr(
            manager,
            "join",
            None,
        )

        if callable(method):

            return method(
                name,
                timeout=timeout,
            )

        method = getattr(
            manager,
            "wait",
            None,
        )

        if callable(method):

            return method(
                name,
                timeout=timeout,
            )

        return None

    # ==========================================================
    # WAIT
    # ==========================================================

    def wait(
        self,
        name: str,
        timeout: Optional[float] = None,
    ) -> Optional[int]:

        return self.join(
            name,
            timeout=timeout,
        )

    # ==========================================================
    # GET PROCESS
    # ==========================================================

    def get_process(
        self,
        name: str,
    ) -> Any:

        manager = self._require_manager()

        method = getattr(
            manager,
            "get",
            None,
        )

        if not callable(method):
            return None

        return method(
            self._require_name(name)
        )

    # ==========================================================
    # REQUIRE PROCESS
    # ==========================================================

    def require_process(
        self,
        name: str,
    ) -> Any:

        name = self._require_name(
            name
        )

        manager = self._require_manager()

        method = getattr(
            manager,
            "require",
            None,
        )

        if callable(method):

            return method(name)

        process = self.get_process(
            name
        )

        if process is None:

            raise KeyError(
                f"Scraper not found: {name}"
            )

        return process

    # ==========================================================
    # STATUS
    # ==========================================================

    def status(
        self,
        name: str,
    ) -> ScraperStatus:

        return self._require_manager().status(
            self._require_name(name)
        )

    # ==========================================================
    # STATUS TEXT
    # ==========================================================

    def status_text(
        self,
        name: str,
    ) -> str:

        try:

            return self._status_value(
                self.status(name)
            )

        except Exception:

            return "UNKNOWN"

    # ==========================================================
    # STATUS ROLE
    # ==========================================================

    def status_role(
        self,
        name: str,
    ) -> str:

        status = self.status(
            name
        )

        mapping = {
            ScraperStatus.CREATED: "created",
            ScraperStatus.STARTING: "starting",
            ScraperStatus.RUNNING: "running",
            ScraperStatus.STOPPING: "stopping",
            ScraperStatus.STOPPED: "stopped",
            ScraperStatus.FINISHED: "finished",
            ScraperStatus.CRASHED: "crashed",
            ScraperStatus.KILLED: "killed",
        }

        return mapping.get(
            status,
            "unknown",
        )

    # ==========================================================
    # REFRESH
    # ==========================================================

    def refresh(
        self,
        name: Optional[str] = None,
    ) -> None:

        manager = self._require_manager()

        if name is not None:

            name = self._require_name(
                name
            )

        method = getattr(
            manager,
            "refresh",
            None,
        )

        if callable(method):

            method(name)

    # ==========================================================
    # COUNT
    # ==========================================================

    def count(self) -> int:

        method = getattr(
            self._require_manager(),
            "count",
            None,
        )

        if not callable(method):
            return 0

        try:

            return int(
                method()
            )

        except Exception:

            return 0

    # ==========================================================
    # EXISTS
    # ==========================================================

    def exists(
        self,
        name: str,
    ) -> bool:

        try:

            name = self._require_name(
                name
            )

        except (
            TypeError,
            ValueError,
        ):

            return False

        manager = self._require_manager()

        method = getattr(
            manager,
            "exists",
            None,
        )

        if callable(method):

            try:

                return bool(
                    method(name)
                )

            except Exception:

                return False

        return self.get_process(
            name
        ) is not None

    # ==========================================================
    # NAMES
    # ==========================================================

    def names(self) -> list[str]:

        manager = self._require_manager()

        method = getattr(
            manager,
            "names",
            None,
        )

        if callable(method):

            try:

                return [
                    str(name)
                    for name in method()
                ]

            except Exception:

                pass

        result: list[str] = []

        for process in self.all_processes():

            name = getattr(
                process,
                "name",
                None,
            )

            if name is None:
                continue

            value = str(
                name
            ).strip()

            if value:

                result.append(
                    value
                )

        return result

    # ==========================================================
    # ALL PROCESSES
    # ==========================================================

    def all_processes(self) -> list[Any]:

        manager = self._require_manager()

        method = getattr(
            manager,
            "all",
            None,
        )

        if not callable(method):
            return []

        try:

            return self._collection_values(
                method()
            )

        except Exception:

            return []

    # ==========================================================
    # RUNNING PROCESSES
    # ==========================================================

    def running_processes(self) -> list[Any]:

        manager = self._require_manager()

        method = getattr(
            manager,
            "running",
            None,
        )

        if not callable(method):
            return []

        try:

            return self._collection_values(
                method()
            )

        except Exception:

            return []

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(
        self,
        name: str,
    ) -> dict[str, Any]:

        result = self._require_manager().snapshot(
            self._require_name(name)
        )

        return self._snapshot_dict(
            result
        )

    # ==========================================================
    # SNAPSHOTS
    # ==========================================================

    def snapshots(
        self,
    ) -> list[dict[str, Any]]:

        manager = self._require_manager()

        method = getattr(
            manager,
            "snapshots",
            None,
        )

        if callable(method):

            try:

                return [
                    self._snapshot_dict(item)
                    for item in self._collection_values(
                        method()
                    )
                ]

            except Exception:

                pass

        result: list[dict[str, Any]] = []

        for name in self.names():

            try:

                result.append(
                    self.snapshot(name)
                )

            except Exception:

                continue

        return result

    # ==========================================================
    # SCRAPER INFO
    # ==========================================================

    def scraper_info(
        self,
        name: str,
    ) -> Optional[ScraperInfo]:

        registry = self._get_registry()

        if registry is None:
            return None

        method = getattr(
            registry,
            "get",
            None,
        )

        if not callable(method):
            return None

        try:

            return method(
                self._require_name(name)
            )

        except Exception:

            return None

    # ==========================================================
    # ALL SCRAPERS
    # ==========================================================

    def all_scrapers(
        self,
    ) -> list[ScraperInfo]:

        registry = self._get_registry()

        if registry is None:
            return []

        method = getattr(
            registry,
            "all",
            None,
        )

        if not callable(method):
            return []

        try:

            return list(
                method()
            )

        except Exception:

            return []

    # ==========================================================
    # REMOVE
    # ==========================================================

    def remove(
        self,
        name: str,
        force: bool = False,
        timeout: float = 10.0,
    ) -> bool:

        return bool(
            self._require_manager().remove(
                self._require_name(name),
                force=bool(force),
                timeout=float(timeout),
            )
        )

    # ==========================================================
    # REMOVE ALL
    # ==========================================================

    def remove_all(
        self,
        force: bool = False,
        timeout: float = 10.0,
    ) -> None:

        manager = self._require_manager()

        method = getattr(
            manager,
            "remove_all",
            None,
        )

        if callable(method):

            method(
                force=bool(force),
                timeout=float(timeout),
            )

            return

        for name in self.names():

            try:

                self.remove(
                    name,
                    force=force,
                    timeout=timeout,
                )

            except Exception:

                continue

    # ==========================================================
    # AVAILABLE ACTIONS
    # ==========================================================

    def available_actions(
        self,
        name: str,
    ) -> dict[str, bool]:

        name = self._require_name(
            name
        )

        defaults = self._disabled_actions()

        if not self.exists(name):
            return defaults

        manager = self._require_manager()

        # ------------------------------------------------------
        # Prefer manager-owned lifecycle policy.
        # ------------------------------------------------------

        method = getattr(
            manager,
            "available_actions",
            None,
        )

        if callable(method):

            try:

                return self._normalize_actions(
                    method(name)
                )

            except Exception:

                pass

        # ------------------------------------------------------
        # Defensive fallback.
        # ------------------------------------------------------

        try:

            status = self.status(
                name
            )

        except Exception:

            return defaults

        process = self.get_process(
            name
        )

        alive = False

        if process is not None:

            try:

                alive = bool(
                    process.is_alive()
                )

            except Exception:

                alive = False

        transitional = status in {
            ScraperStatus.STARTING,
            ScraperStatus.STOPPING,
        }

        finished = status in {
            ScraperStatus.STOPPED,
            ScraperStatus.FINISHED,
            ScraperStatus.CRASHED,
            ScraperStatus.KILLED,
        }

        return {
            "start":
                not alive
                and not transitional,

            "stop":
                alive
                and status != ScraperStatus.STOPPING,

            "kill":
                alive,

            "restart":
                not transitional
                and (
                    not alive
                    or finished
                    or status == ScraperStatus.CREATED
                ),

            "restart_force":
                not transitional,

            "remove":
                not alive
                and not transitional,
        }

    # ==========================================================
    # STATE HELPERS
    # ==========================================================

    def is_running(
        self,
        name: str,
    ) -> bool:

        try:

            return (
                self.status(name)
                == ScraperStatus.RUNNING
            )

        except Exception:

            return False

    # ----------------------------------------------------------

    def is_starting(
        self,
        name: str,
    ) -> bool:

        try:

            return (
                self.status(name)
                == ScraperStatus.STARTING
            )

        except Exception:

            return False

    # ----------------------------------------------------------

    def is_stopping(
        self,
        name: str,
    ) -> bool:

        try:

            return (
                self.status(name)
                == ScraperStatus.STOPPING
            )

        except Exception:

            return False

    # ----------------------------------------------------------

    def is_finished(
        self,
        name: str,
    ) -> bool:

        try:

            status = self.status(
                name
            )

        except Exception:

            return False

        return status in {
            ScraperStatus.STOPPED,
            ScraperStatus.FINISHED,
            ScraperStatus.CRASHED,
            ScraperStatus.KILLED,
        }

    # ----------------------------------------------------------

    def has_failed(
        self,
        name: str,
    ) -> bool:

        try:

            return (
                self.status(name)
                == ScraperStatus.CRASHED
            )

        except Exception:

            return False

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def shutdown(
        self,
        timeout: float = 10.0,
    ) -> None:

        manager = self._require_manager()

        method = getattr(
            manager,
            "shutdown",
            None,
        )

        if not callable(method):
            return

        try:

            method(
                timeout=float(timeout)
            )

        except TypeError:

            method()

    # ==========================================================
    # INTERNAL — REGISTRY
    # ==========================================================

    def _get_registry(
        self,
    ) -> Optional[ScraperRegistry]:

        manager = self._require_manager()

        registry = getattr(
            manager,
            "registry",
            None,
        )

        if registry is not None:

            self.registry = registry

        return self.registry

    # ==========================================================
    # INTERNAL — COLLECTION
    # ==========================================================

    @staticmethod
    def _collection_values(
        value: Any,
    ) -> list[Any]:

        if value is None:
            return []

        if isinstance(
            value,
            dict,
        ):

            return list(
                value.values()
            )

        if isinstance(
            value,
            (list, tuple, set),
        ):

            return list(value)

        try:

            return list(value)

        except TypeError:

            return []

    # ==========================================================
    # INTERNAL — SNAPSHOT
    # ==========================================================

    @staticmethod
    def _snapshot_dict(
        snapshot: Any,
    ) -> dict[str, Any]:

        if snapshot is None:
            return {}

        if isinstance(
            snapshot,
            dict,
        ):

            return dict(
                snapshot
            )

        method = getattr(
            snapshot,
            "to_dict",
            None,
        )

        if callable(method):

            try:

                result = method()

                if isinstance(
                    result,
                    dict,
                ):

                    return dict(
                        result
                    )

            except Exception:

                pass

        data = getattr(
            snapshot,
            "__dict__",
            None,
        )

        if isinstance(
            data,
            dict,
        ):

            return dict(
                data
            )

        return {
            "value": snapshot
        }

    # ==========================================================
    # INTERNAL — ACTIONS
    # ==========================================================

    @staticmethod
    def _disabled_actions() -> dict[str, bool]:

        return {
            "start": False,
            "stop": False,
            "kill": False,
            "restart": False,
            "restart_force": False,
            "remove": False,
        }

    # ----------------------------------------------------------

    @staticmethod
    def _normalize_actions(
        actions: Any,
    ) -> dict[str, bool]:

        defaults = (
            GUIController
            ._disabled_actions()
        )

        if not isinstance(
            actions,
            dict,
        ):

            return defaults

        for key in defaults:

            defaults[key] = bool(
                actions.get(
                    key,
                    False,
                )
            )

        return defaults

    # ==========================================================
    # INTERNAL — STATUS
    # ==========================================================

    @staticmethod
    def _status_value(
        status: Any,
    ) -> str:

        if isinstance(
            status,
            ScraperStatus,
        ):

            return str(
                status.value
            ).upper()

        value = getattr(
            status,
            "value",
            status,
        )

        return str(
            value
        ).upper()

    # ==========================================================
    # REPRESENTATION
    # ==========================================================

    def __repr__(
        self,
    ) -> str:

        try:

            count = self.count()

        except Exception:

            count = "?"

        return (
            "<GUIController "
            f"processes={count}>"
        )