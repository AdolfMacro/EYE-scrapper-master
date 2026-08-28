# ==========================================================
# FILE REVIEW — worker.py
#
# STATUS       : APPROVED
# ROLE         : Child Scraper Runtime Worker
# LAYER        : Scraper / Runtime Execution
#
# RESPONSIBILITIES
# ----------------------------------------------------------
# 1. Manage one child scraper runtime
# 2. Validate exactly one provider
# 3. Normalize scraper keywords
# 4. Build single-keyword SearchConfig instances
# 5. Create ScraperEngine instances
# 6. Create and own one ScraperPipeline
# 7. Execute keywords sequentially
# 8. Forward raw results to the pipeline
# 9. Maintain runtime state
# 10. Maintain health state
# 11. Maintain RunContext
# 12. Expose stable runtime snapshots
# 13. Handle graceful stop requests
# 14. Record runtime errors
#
# DOES NOT
# ----------------------------------------------------------
# - Manage multiprocessing
# - Manage ProcessManager
# - Manage ScraperRegistry
# - Create threads
# - Generate provider-specific queries
# - Write directly to the database
#
# PROVIDER CONTRACT
# ----------------------------------------------------------
# Exactly ONE provider belongs to each child scraper.
#
# KEYWORD CONTRACT
# ----------------------------------------------------------
# One scraper may contain multiple keywords.
#
# SearchConfig remains SINGLE-keyword.
#
# Therefore:
#
#     Worker
#        │
#        ├── Provider
#        │
#        └── Keywords
#              │
#              ├── SearchConfig(keyword #1)
#              ├── SearchConfig(keyword #2)
#              ├── SearchConfig(keyword #3)
#              └── ...
#
# Each keyword gets its own ScraperEngine.
#
# One ScraperPipeline is shared across the complete run.
#
# RUNTIME CONTRACT
# ----------------------------------------------------------
# Worker owns scraper execution state only.
#
# Process lifecycle belongs to:
#
#     ProcessManager
#         ↓
#     ScraperProcess
#
# ==========================================================

from __future__ import annotations

import traceback
from pathlib import Path
from typing import Any, Optional

from database.database import Database
from providers.manager import ProviderManager
from runtime.health import ProviderHealth

from scraper.context import RunContext
from scraper.deduplicator import DeduplicationService
from scraper.engine import ScraperEngine
from scraper.pipeline import ScraperPipeline


class ScraperWorker:
    """
    Runtime worker for one child scraper.

    ScraperWorker executes scraper logic inside the child
    process created by ScraperProcess.

    It owns:

        provider
        configuration
        keywords
        RunContext
        database manager
        deduplication service
        pipeline
        engine
        health state

    It does NOT own multiprocessing lifecycle.
    """

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

    def __init__(
        self,
        name: str,
        providers: list[str] | str,
        database: str,
        config: Optional[dict[str, Any]] = None,
        log_file: Optional[str] = None,
        scraper_dir: Optional[str] = None,
    ) -> None:

        # ------------------------------------------------------
        # NAME
        # ------------------------------------------------------

        name = str(name).strip()

        if not name:
            raise ValueError(
                "Scraper name is required."
            )

        self.name = name

        # ------------------------------------------------------
        # PROVIDER
        # ------------------------------------------------------

        if isinstance(providers, str):

            provider_name = (
                providers.strip().lower()
            )

        elif isinstance(
            providers,
            (list, tuple),
        ):

            if len(providers) != 1:
                raise ValueError(
                    "Each child scraper must use "
                    "exactly one provider."
                )

            provider_name = str(
                providers[0]
            ).strip().lower()

        else:

            raise TypeError(
                "Provider must be a string or "
                "a list containing one provider."
            )

        if not provider_name:
            raise ValueError(
                "Provider name is required."
            )

        self.provider_name = provider_name

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
        # CONFIG
        # ------------------------------------------------------

        self.config = dict(
            config or {}
        )

        # ------------------------------------------------------
        # LOG
        # ------------------------------------------------------

        self.log_file = (
            str(
                Path(log_file).expanduser()
            )
            if log_file
            else None
        )

        # ------------------------------------------------------
        # SCRAPER DIRECTORY
        # ------------------------------------------------------

        self.scraper_dir = (
            str(
                Path(scraper_dir).expanduser()
            )
            if scraper_dir
            else None
        )

        # ======================================================
        # RUNTIME STATE
        # ======================================================

        self.running = False

        self.error: Optional[str] = None

        self.results: list[Any] = []

        self.context: Optional[
            RunContext
        ] = None

        self.engine: Optional[
            ScraperEngine
        ] = None

        self.pipeline: Optional[
            ScraperPipeline
        ] = None

        self.database_manager: Optional[
            Database
        ] = None

        # ------------------------------------------------------
        # SERVICES
        # ------------------------------------------------------

        self.provider_manager = (
            ProviderManager()
        )

        self.health = ProviderHealth(
            provider=self.provider_name
        )

        self.deduplicator = (
            DeduplicationService()
        )

        # ------------------------------------------------------
        # STOP STATE
        # ------------------------------------------------------

        self._stop_requested = False

        # ======================================================
        # KEYWORD STATE
        # ======================================================

        self.keywords: list[str] = []

        self.current_keyword: Optional[
            str
        ] = None

        self.keyword_index = 0

        self.keyword_count = 0

        # ======================================================
        # DIRECTORIES
        # ======================================================

        self._prepare_directories()

    # ==========================================================
    # DIRECTORIES
    # ==========================================================

    def _prepare_directories(
        self,
    ) -> None:
        """
        Prepare worker runtime directories.
        """

        Path(
            self.database
        ).parent.mkdir(
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
    # LOG
    # ==========================================================

    def log(
        self,
        message: Any,
    ) -> None:
        """
        Emit a worker runtime message.
        """

        line = (
            f"[{self.name}] {message}"
        )

        print(
            line,
            flush=True,
        )

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
                    line + "\n"
                )

        except OSError:
            pass

    # ==========================================================
    # PROVIDER
    # ==========================================================

    def get_provider(self):
        """
        Load the single configured provider.
        """

        self.log(
            f"[PROVIDER] Loading: "
            f"{self.provider_name}"
        )

        provider = (
            self.provider_manager.get(
                self.provider_name
            )
        )

        if provider is None:
            raise RuntimeError(
                f"Provider '{self.provider_name}' "
                "could not be loaded."
            )

        self.log(
            f"[PROVIDER] Ready: "
            f"{self.provider_name}"
        )

        return provider

    # ==========================================================
    # CONFIG VALUE
    # ==========================================================

    def _config_value(
        self,
        *names: str,
        default: Any = None,
    ) -> Any:
        """
        Resolve configuration values from supported
        direct and nested configuration structures.
        """

        # ------------------------------------------------------
        # DIRECT
        # ------------------------------------------------------

        for name in names:

            if name not in self.config:
                continue

            value = self.config.get(name)

            if value is None:
                continue

            if isinstance(value, str):

                value = value.strip()

                if not value:
                    continue

            return value

        # ------------------------------------------------------
        # NESTED
        # ------------------------------------------------------

        for section_name in (
            "search",
            "search_config",
            "config",
        ):

            section = self.config.get(
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

                value = section.get(name)

                if value is None:
                    continue

                if isinstance(value, str):

                    value = value.strip()

                    if not value:
                        continue

                return value

        return default

    # ==========================================================
    # NORMALIZE KEYWORDS
    # ==========================================================

    @staticmethod
    def _normalize_keywords(
        value: Any,
    ) -> list[str]:
        """
        Normalize a keyword value into a stable list.

        Supported:

            "کافه"

            [
                "کافه",
                "رستوران"
            ]

            tuple
            set

        Empty values are removed.

        Duplicates are removed while preserving order.
        """

        if value is None:
            return []

        # ------------------------------------------------------
        # STRING
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
        # COLLECTION
        # ------------------------------------------------------

        if isinstance(
            value,
            (list, tuple, set),
        ):

            normalized: list[str] = []

            seen: set[str] = set()

            for item in value:

                if item is None:
                    continue

                item = str(item).strip()

                if not item:
                    continue

                key = item.casefold()

                if key in seen:
                    continue

                seen.add(key)

                normalized.append(item)

            return normalized

        raise TypeError(
            "Keywords must be a string, "
            "list, tuple, or set."
        )

    # ==========================================================
    # GET KEYWORDS
    # ==========================================================

    def _get_keywords(
        self,
    ) -> list[str]:
        """
        Resolve the complete scraper keyword list.

        Priority:

            1. keywords
            2. search_keywords
            3. keyword
            4. search_keyword
        """

        value = self._config_value(
            "keywords",
            "search_keywords",
            default=None,
        )

        if value is not None:

            keywords = (
                self._normalize_keywords(
                    value
                )
            )

            if keywords:
                return keywords

        value = self._config_value(
            "keyword",
            "search_keyword",
            default=None,
        )

        keywords = (
            self._normalize_keywords(
                value
            )
        )

        if not keywords:

            raise ValueError(
                f"Scraper '{self.name}' "
                "has no keyword configured."
            )

        return keywords

    # ==========================================================
    # SINGLE KEYWORD
    # ==========================================================

    def _get_keyword(
        self,
    ) -> str:
        """
        Return the first configured keyword.

        Kept for compatibility with existing callers.
        """

        keywords = self._get_keywords()

        return keywords[0]

    # ==========================================================
    # BUILD SEARCH CONFIG
    # ==========================================================

    def build_config(
        self,
        keyword: Optional[str] = None,
    ):
        """
        Build one SearchConfig for exactly one keyword.
        """

        from config.search import SearchConfig

        data = dict(
            self.config
        )

        if keyword is None:
            keyword = self._get_keyword()

        keyword = str(
            keyword
        ).strip()

        if not keyword:
            raise ValueError(
                f"Scraper '{self.name}' "
                "contains an empty keyword."
            )

        # ------------------------------------------------------
        # REMOVE WORKER-LEVEL FIELDS
        # ------------------------------------------------------

        for key in (
            "keyword",
            "keywords",
            "search_keyword",
            "search_keywords",
            "database",
            "database_file",
        ):

            data.pop(
                key,
                None,
            )

        # ------------------------------------------------------
        # FLATTEN SEARCH SECTIONS
        # ------------------------------------------------------

        for section_name in (
            "search",
            "search_config",
        ):

            section = data.pop(
                section_name,
                None,
            )

            if not isinstance(
                section,
                dict,
            ):
                continue

            for key, value in section.items():

                if key in {
                    "keyword",
                    "keywords",
                    "search_keyword",
                    "search_keywords",
                }:
                    continue

                if key not in data:
                    data[key] = value

        # ------------------------------------------------------
        # FINAL KEYWORD
        # ------------------------------------------------------

        data["keyword"] = keyword

        # ------------------------------------------------------
        # BUILD
        # ------------------------------------------------------

        try:

            config = SearchConfig(
                **data
            )

        except TypeError:

            config = SearchConfig()

            for key, value in data.items():

                if hasattr(
                    config,
                    key,
                ):

                    setattr(
                        config,
                        key,
                        value,
                    )

        # ------------------------------------------------------
        # VALIDATE
        # ------------------------------------------------------

        final_keyword = getattr(
            config,
            "keyword",
            None,
        )

        if final_keyword is None:

            raise ValueError(
                f"SearchConfig for scraper "
                f"'{self.name}' does not contain "
                "keyword."
            )

        final_keyword = str(
            final_keyword
        ).strip()

        if not final_keyword:

            raise ValueError(
                f"SearchConfig for scraper "
                f"'{self.name}' contains an empty "
                "keyword."
            )

        config.keyword = (
            final_keyword
        )

        return config

    # ==========================================================
    # DATABASE
    # ==========================================================

    def build_database(
        self,
    ) -> Database:
        """
        Lazily create the worker database manager.
        """

        if self.database_manager is not None:
            return self.database_manager

        self.log(
            f"[DATABASE] Opening: "
            f"{self.database}"
        )

        self.database_manager = Database(
            self.database
        )

        self.log(
            "[DATABASE] Ready"
        )

        return self.database_manager

    # ==========================================================
    # ENGINE
    # ==========================================================

    def build_engine(
        self,
        keyword: Optional[str] = None,
    ) -> ScraperEngine:
        """
        Build a ScraperEngine for one keyword.
        """

        provider = self.get_provider()

        config = self.build_config(
            keyword=keyword
        )

        return ScraperEngine(
            config=config,
            provider=provider,
            logger=self.log,
        )

    # ==========================================================
    # PIPELINE
    # ==========================================================

    def build_pipeline(
        self,
    ) -> ScraperPipeline:
        """
        Build the single pipeline shared by the run.
        """

        if self.context is None:

            raise RuntimeError(
                "RunContext must exist before "
                "building the pipeline."
            )

        database = (
            self.build_database()
        )

        return ScraperPipeline(
            context=self.context,
            deduplicator=self.deduplicator,
            database=database,
            logger=self.log,
        )

    # ==========================================================
    # RUN
    # ==========================================================

    def run(self):
        """
        Execute the complete scraper job.

        Keywords are processed sequentially.

        Each keyword receives:

            SearchConfig
                ↓
            ScraperEngine
                ↓
            ScraperPipeline

        The pipeline itself is shared across the complete run.
        """

        if self.running:

            raise RuntimeError(
                f"Scraper '{self.name}' "
                "is already running."
            )

        self.running = True

        self.error = None

        self.results = []

        self.engine = None

        self.pipeline = None

        self._stop_requested = False

        self.keywords = []

        self.current_keyword = None

        self.keyword_index = 0

        self.keyword_count = 0

        # ======================================================
        # CONTEXT
        # ======================================================

        self.context = RunContext(
            metadata={
                "scraper": self.name,
                "provider": self.provider_name,
                "database": self.database,
            }
        )

        self.deduplicator.clear()

        self.context.start()

        self.log(
            "[WORKER] Starting"
        )

        self.log(
            f"[JOB] {self.context.job_id}"
        )

        self.log(
            f"[DATABASE] {self.database}"
        )

        self.log(
            f"[PROVIDER] {self.provider_name}"
        )

        try:

            # ==================================================
            # LOAD KEYWORDS
            # ==================================================

            self.keywords = (
                self._get_keywords()
            )

            self.keyword_count = len(
                self.keywords
            )

            self.log(
                f"[KEYWORDS] Loaded: "
                f"{self.keyword_count}"
            )

            # ==================================================
            # EXECUTE KEYWORDS
            # ==================================================

            for index, keyword in enumerate(
                self.keywords,
                start=1,
            ):

                self.keyword_index = index

                self.current_keyword = (
                    keyword
                )

                # ----------------------------------------------
                # STOP
                # ----------------------------------------------

                if self._stop_requested:

                    self.log(
                        "[WORKER] Stop requested "
                        "before next keyword."
                    )

                    break

                # ----------------------------------------------
                # KEYWORD
                # ----------------------------------------------

                self.log(
                    f"[KEYWORD] "
                    f"{index}/{self.keyword_count} "
                    f"| {keyword}"
                )

                # ----------------------------------------------
                # CONFIG
                # ----------------------------------------------

                config = (
                    self.build_config(
                        keyword=keyword
                    )
                )

                # ----------------------------------------------
                # PIPELINE
                # ----------------------------------------------

                if self.pipeline is None:

                    self.pipeline = (
                        self.build_pipeline()
                    )

                # ----------------------------------------------
                # PROVIDER
                # ----------------------------------------------

                provider = (
                    self.get_provider()
                )

                # ----------------------------------------------
                # ENGINE
                # ----------------------------------------------

                self.engine = ScraperEngine(
                    config=config,
                    provider=provider,
                    logger=self.log,
                )

                # ----------------------------------------------
                # EXECUTE
                # ----------------------------------------------

                raw_results = (
                    self.engine.run()
                    or []
                )

                self.log(
                    f"[KEYWORD RESULT] "
                    f"{keyword} | "
                    f"raw={len(raw_results)}"
                )

                # ----------------------------------------------
                # PIPELINE
                # ----------------------------------------------

                processed_results = (
                    self.pipeline.run(
                        raw_results,
                        provider=self.provider_name,
                    )
                    or []
                )

                self.results.extend(
                    processed_results
                )

                self.log(
                    f"[KEYWORD FINISHED] "
                    f"{keyword} | "
                    f"accepted="
                    f"{len(processed_results)}"
                )

                # ----------------------------------------------
                # RELEASE ENGINE
                # ----------------------------------------------

                self.engine = None

            # ==================================================
            # FINAL STATE
            # ==================================================

            if self._stop_requested:

                self.log(
                    "[WORKER] Stopped"
                )

            else:

                self.health.success()

                self.log(
                    "[WORKER] Finished | "
                    f"keywords="
                    f"{self.keyword_count} "
                    f"results="
                    f"{len(self.results)} "
                    f"saved="
                    f"{self.pipeline.saved if self.pipeline else 0} "
                    f"duplicates="
                    f"{self.pipeline.duplicates if self.pipeline else 0}"
                )

            return self.results

        except Exception as exc:

            self.error = str(exc)

            try:

                self.health.failure(
                    exc
                )

            except Exception:
                pass

            if self.context is not None:

                try:

                    self.context.stats.error(
                        provider=self.provider_name
                    )

                except Exception:
                    pass

            self.log(
                f"[WORKER ERROR] {exc}"
            )

            traceback.print_exc()

            raise

        finally:

            self.engine = None

            self.current_keyword = None

            if self.context is not None:

                try:
                    self.context.stop()
                except Exception:
                    pass

            self.running = False

            self.log(
                "[WORKER] Exit"
            )

    # ==========================================================
    # STOP
    # ==========================================================

    def stop(
        self,
    ) -> bool:
        """
        Request graceful worker shutdown.
        """

        if not self.running:
            return False

        self._stop_requested = True

        if self.engine is None:

            self.log(
                "[WORKER] Stop requested "
                "before active engine."
            )

            return True

        try:

            self.engine.stop()

        except Exception as exc:

            self.log(
                f"[STOP ERROR] {exc}"
            )

            return False

        self.log(
            "[WORKER] Stop requested"
        )

        return True

    # ==========================================================
    # CLOSE
    # ==========================================================

    def close(
        self,
    ) -> None:
        """
        Release worker-owned runtime resources.
        """

        if self.running:
            self.stop()

        self.engine = None

        if self.database_manager is not None:

            try:

                self.database_manager.close()

            finally:

                self.database_manager = None

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(
        self,
    ) -> dict[str, Any]:
        """
        Return a stable, serializable worker snapshot.
        """

        return {
            "name": self.name,

            "provider": self.provider_name,

            "database": self.database,

            "running": self.running,

            "stop_requested": (
                self._stop_requested
            ),

            "keywords": list(
                self.keywords
            ),

            "keyword_count": (
                self.keyword_count
            ),

            "keyword_index": (
                self.keyword_index
            ),

            "current_keyword": (
                self.current_keyword
            ),

            "job_id": (
                self.context.job_id
                if self.context
                else None
            ),

            "results": len(
                self.results
            ),

            "error": self.error,

            "keyword": (
                self.current_keyword
                if self.current_keyword
                else (
                    getattr(
                        self.context,
                        "metadata",
                        {},
                    ).get("keyword")
                    if self.context
                    else None
                )
            ),

            "stats": (
                self.context.stats.snapshot()
                if self.context
                else None
            ),

            "health": (
                self.health.snapshot()
            ),

            "pipeline": (
                self.pipeline.snapshot()
                if self.pipeline
                else None
            ),

            "deduplicator": (
                self.deduplicator.snapshot()
            ),

            "context": (
                self.context.snapshot()
                if self.context
                else None
            ),

            "log_file": self.log_file,

            "scraper_dir": self.scraper_dir,
        }

    # ==========================================================
    # REPRESENTATION
    # ==========================================================

    def __repr__(
        self,
    ) -> str:

        return (
            f"<ScraperWorker "
            f"name={self.name!r} "
            f"provider={self.provider_name!r} "
            f"keywords={len(self.keywords)}>"
        )