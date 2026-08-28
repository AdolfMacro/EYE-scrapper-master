# ==========================================================
# EYES MASTER — SCRAPER ENGINE
# ==========================================================
#
# FILE:
#     scraper/engine.py
#
# STATUS:
#     CANONICAL / CORE
#
# ROLE:
#     Core scraper execution engine.
#
# RESPONSIBILITIES:
#     - Validate configuration
#     - Generate queries
#     - Execute provider searches
#     - Support normal pagination
#     - Support maximum-data pagination
#     - Extract Business objects
#     - Collect raw extraction results
#     - Track execution progress
#     - Support graceful stop
#     - Propagate fatal execution errors
#
# DOES NOT:
#     - Manage Database
#     - Persist records
#     - Deduplicate records
#     - Manage ProviderManager
#     - Manage multiprocessing
#     - Create threads
#
# IMPORTANT:
#
#     In MAXIMUM mode:
#
#         Engine does NOT truncate provider results.
#         Engine does NOT impose results_per_page.
#         Engine continues pagination until:
#
#             - provider returns no results
#             - provider returns fewer results
#               than the requested page size
#             - a page repeats the previous page
#             - maximum safety pages is reached
#             - maximum total results is reached
#             - user requests stop
#
#     This allows providers such as Balad to expose as much
#     available data as their API permits.
#
# ARCHITECTURE:
#
#     ScraperWorker
#          │
#          ▼
#     ScraperEngine
#          │
#          ├── QueryGenerator
#          ├── Provider
#          └── BusinessExtractor
#                    │
#                    ▼
#                Business[]
#                    │
#                    ▼
#               ScraperPipeline
#                    │
#                    ├── Validation
#                    ├── Deduplication
#                    └── Database
#
# CORE RULE:
#
#     Engine discovers and extracts.
#     Pipeline validates, deduplicates and persists.
#
# ==========================================================

from __future__ import annotations

import hashlib
import threading
import traceback

from typing import Any, Iterable

from scraper.extractor import BusinessExtractor
from scraper.query_generator import QueryGenerator


class ScraperEngine:

    # ==========================================================
    # SAFETY LIMITS
    # ==========================================================

    # Very high safety ceiling.
    #
    # This is NOT the intended data limit.
    #
    # It only prevents a broken provider/API from creating an
    # infinite pagination loop.
    #
    DEFAULT_MAX_PAGES_PER_QUERY = 10000

    # Maximum number of identical consecutive pages allowed.
    DEFAULT_MAX_REPEATED_PAGES = 1

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(
        self,
        config,
        provider=None,
        logger=None,
        progress_callback=None,
    ) -> None:

        self.config = config

        self.provider = provider

        self.logger = logger

        self.progress_callback = (
            progress_callback
        )

        self.running = False

        self._stop_event = (
            threading.Event()
        )

        self.results: list[Any] = []

        self.queries_processed = 0

        self.pages_processed = 0

        self.results_processed = 0

        # ------------------------------------------------------
        # Runtime statistics
        # ------------------------------------------------------

        self.raw_results_processed = 0

        self.empty_pages = 0

        self.repeated_pages = 0

        self.query_results: dict[
            str,
            int,
        ] = {}

        self.query_pages: dict[
            str,
            int,
        ] = {}

    # ==========================================================
    # LOGGING
    # ==========================================================

    def log(
        self,
        message: Any,
    ) -> None:

        message = str(
            message
        )

        print(
            message,
            flush=True,
        )

        if not callable(
            self.logger
        ):

            return

        try:

            self.logger(
                message
            )

        except Exception:

            pass

    # ==========================================================
    # PROGRESS
    # ==========================================================

    def update_progress(
        self,
    ) -> None:

        if not callable(
            self.progress_callback
        ):

            return

        try:

            self.progress_callback(
                self.progress()
            )

        except Exception:

            pass

    # ==========================================================
    # RESET
    # ==========================================================

    def reset(
        self,
    ) -> None:

        self._stop_event.clear()

        self.results.clear()

        self.queries_processed = 0

        self.pages_processed = 0

        self.results_processed = 0

        self.raw_results_processed = 0

        self.empty_pages = 0

        self.repeated_pages = 0

        self.query_results.clear()

        self.query_pages.clear()

    # ==========================================================
    # STOP
    # ==========================================================

    def stop(
        self,
    ) -> None:

        if not self.running:

            return

        self.log(
            "[STOP] Stop requested"
        )

        self._stop_event.set()

    # ==========================================================
    # STOP STATE
    # ==========================================================

    def stop_requested(
        self,
    ) -> bool:

        return self._stop_event.is_set()

    # ==========================================================
    # PROVIDER
    # ==========================================================

    def _require_provider(
        self,
    ):

        if self.provider is None:

            raise RuntimeError(
                "Provider is missing."
            )

        search = getattr(
            self.provider,
            "search",
            None,
        )

        if not callable(
            search
        ):

            raise RuntimeError(
                "Provider must implement "
                "search(query, page=...)."
            )

        return self.provider

    # ==========================================================
    # PROVIDER NAME
    # ==========================================================

    def provider_name(
        self,
    ) -> str:

        if self.provider is None:

            return ""

        name = getattr(
            self.provider,
            "name",
            None,
        )

        if name:

            return str(
                name
            ).strip().casefold()

        info = getattr(
            self.provider,
            "info",
            None,
        )

        if callable(
            info
        ):

            try:

                data = info()

                if isinstance(
                    data,
                    dict,
                ):

                    name = data.get(
                        "name"
                    )

                    if name:

                        return str(
                            name
                        ).strip().casefold()

            except Exception:

                pass

        return ""

    # ==========================================================
    # INTEGER HELPERS
    # ==========================================================

    @staticmethod
    def _positive_int(
        value,
        default: int,
    ) -> int:

        try:

            value = int(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return default

        return max(
            1,
            value,
        )

    @staticmethod
    def _non_negative_int(
        value,
        default: int = 0,
    ) -> int:

        try:

            value = int(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return default

        return max(
            0,
            value,
        )

    # ==========================================================
    # BOOLEAN HELPER
    # ==========================================================

    @staticmethod
    def _bool(
        value: Any,
        default: bool = False,
    ) -> bool:

        if value is None:

            return default

        if isinstance(
            value,
            bool,
        ):

            return value

        if isinstance(
            value,
            (int, float),
        ):

            return bool(
                value
            )

        text = str(
            value
        ).strip().casefold()

        if text in {
            "1",
            "true",
            "yes",
            "y",
            "on",
            "all",
            "maximum",
            "max",
            "unlimited",
        }:

            return True

        if text in {
            "0",
            "false",
            "no",
            "n",
            "off",
            "normal",
            "limited",
        }:

            return False

        return default

    # ==========================================================
    # DELAY
    # ==========================================================

    def _delay(
        self,
    ) -> float:

        try:

            value = float(
                getattr(
                    self.config,
                    "delay",
                    0,
                )
                or 0
            )

        except (
            TypeError,
            ValueError,
        ):

            return 0.0

        return max(
            0.0,
            value,
        )

    # ==========================================================
    # MAXIMUM MODE
    # ==========================================================

    def maximum_mode(
        self,
    ) -> bool:
        """
        Determine whether the scraper should attempt to collect
        the maximum amount of provider data.

        Supported configuration names:

            maximum_data
            max_data
            fetch_all
            all_results
            unlimited
            maximum_mode

        Also supports:

            data_mode = "maximum"
            data_mode = "max"
            data_mode = "all"
            data_mode = "unlimited"
        """

        names = (
            "maximum_data",
            "max_data",
            "fetch_all",
            "all_results",
            "unlimited",
            "maximum_mode",
        )

        for name in names:

            if hasattr(
                self.config,
                name,
            ):

                value = getattr(
                    self.config,
                    name,
                )

                if self._bool(
                    value,
                    False,
                ):

                    return True

        data_mode = getattr(
            self.config,
            "data_mode",
            None,
        )

        if data_mode is not None:

            mode = str(
                data_mode
            ).strip().casefold()

            if mode in {
                "maximum",
                "max",
                "all",
                "all_results",
                "unlimited",
                "maximum_data",
            }:

                return True

        return False

    # ==========================================================
    # MAXIMUM RESULT LIMIT
    # ==========================================================

    def maximum_results(
        self,
    ) -> int:
        """
        Return an optional global maximum result count.

        Zero means unlimited.

        Important:
            This is a safety/configuration ceiling.
            It is NOT 500.
        """

        for name in (
            "max_total_results",
            "maximum_results",
            "max_results_total",
            "total_results_limit",
        ):

            if not hasattr(
                self.config,
                name,
            ):

                continue

            value = getattr(
                self.config,
                name,
            )

            limit = self._non_negative_int(
                value,
                default=0,
            )

            if limit > 0:

                return limit

        return 0

    # ==========================================================
    # MAXIMUM PAGE LIMIT
    # ==========================================================

    def maximum_pages_per_query(
        self,
    ) -> int:
        """
        Safety ceiling for automatic pagination.

        This prevents an infinite loop caused by a broken API.

        It is deliberately very high.
        """

        for name in (
            "max_pages_per_query",
            "maximum_pages_per_query",
            "pagination_safety_limit",
        ):

            if not hasattr(
                self.config,
                name,
            ):

                continue

            value = self._positive_int(
                getattr(
                    self.config,
                    name,
                ),
                default=self.DEFAULT_MAX_PAGES_PER_QUERY,
            )

            return value

        return self.DEFAULT_MAX_PAGES_PER_QUERY

    # ==========================================================
    # NORMAL MODE PAGE LIMIT
    # ==========================================================

    def normal_pages_per_query(
        self,
    ) -> int:

        return self._positive_int(
            getattr(
                self.config,
                "pages_per_query",
                1,
            ),
            default=1,
        )

    # ==========================================================
    # FETCH
    # ==========================================================

    def fetch_page(
        self,
        query: str,
        page: int,
    ) -> Any:

        provider = (
            self._require_provider()
        )

        self.log(
            f"[PROVIDER] "
            f"{self.provider_name()} "
            f"page={page}"
        )

        return provider.search(
            query,
            page=page,
        )

    # ==========================================================
    # NORMALIZE RAW RESULTS
    # ==========================================================

    @staticmethod
    def _normalize_raw_results(
        raw: Any,
    ) -> list[Any]:

        if raw is None:

            return []

        if isinstance(
            raw,
            list,
        ):

            return raw

        if isinstance(
            raw,
            tuple,
        ):

            return list(
                raw
            )

        if isinstance(
            raw,
            (str, bytes),
        ):

            return [raw]

        try:

            return list(
                raw
            )

        except TypeError:

            return [raw]

    # ==========================================================
    # RESULT IDENTITY
    # ==========================================================

    @classmethod
    def _item_identity(
        cls,
        item: Any,
    ) -> str:
        """
        Build a stable identity for one raw result.

        Used only to detect repeated provider pages.

        This is NOT database deduplication.
        """

        if isinstance(
            item,
            dict,
        ):

            for key in (
                "source_id",
                "id",
                "poi_id",
                "place_id",
                "business_id",
                "url",
            ):

                value = item.get(
                    key
                )

                if value not in (
                    None,
                    "",
                ):

                    return (
                        f"{key}:"
                        f"{str(value).strip().casefold()}"
                    )

            parts = []

            for key in (
                "name",
                "title",
                "address",
                "city",
                "latitude",
                "longitude",
            ):

                value = item.get(
                    key
                )

                if value not in (
                    None,
                    "",
                ):

                    parts.append(
                        str(
                            value
                        ).strip().casefold()
                    )

            if parts:

                payload = "|".join(
                    parts
                )

                return (
                    "hash:"
                    + hashlib.sha1(
                        payload.encode(
                            "utf-8",
                            errors="ignore",
                        )
                    ).hexdigest()
                )

        payload = str(
            item
        ).strip().casefold()

        return (
            "hash:"
            + hashlib.sha1(
                payload.encode(
                    "utf-8",
                    errors="ignore",
                )
            ).hexdigest()
        )

    # ==========================================================
    # PAGE IDENTITY
    # ==========================================================

    @classmethod
    def _page_identity(
        cls,
        items: Iterable[Any],
    ) -> str:

        identities = [
            cls._item_identity(
                item
            )
            for item in items
        ]

        payload = "\n".join(
            identities
        )

        return hashlib.sha1(
            payload.encode(
                "utf-8",
                errors="ignore",
            )
        ).hexdigest()

    # ==========================================================
    # PAGE SIZE
    # ==========================================================

    def provider_page_size(
        self,
    ) -> int:
        """
        Determine expected provider page size.

        This is used only as a signal for automatic pagination.

        It does NOT truncate results.
        """

        for name in (
            "results_per_page",
            "page_size",
            "limit",
        ):

            if not hasattr(
                self.config,
                name,
            ):

                continue

            value = self._positive_int(
                getattr(
                    self.config,
                    name,
                ),
                default=0,
            )

            if value > 0:

                return value

        # Balad commonly exposes batches around this size.
        #
        # This is only a pagination heuristic.
        return 100

    # ==========================================================
    # PROCESS PAGE
    # ==========================================================

    def process_page(
        self,
        query: str,
        page: int,
        extractor: BusinessExtractor,
    ) -> list[Any]:

        if self.stop_requested():

            return []

        raw = self.fetch_page(
            query=query,
            page=page,
        )

        raw = (
            self._normalize_raw_results(
                raw
            )
        )

        self.raw_results_processed += len(
            raw
        )

        self.log(
            f"[RAW RESULTS] "
            f"query={query!r} "
            f"page={page} "
            f"count={len(raw)}"
        )

        # ------------------------------------------------------
        # IMPORTANT
        #
        # We intentionally DO NOT do:
        #
        #     raw = raw[:results_per_page]
        #
        # because the provider is allowed to return more data
        # than the old artificial configuration limit.
        # ------------------------------------------------------

        businesses = (
            extractor.extract_many(
                raw,
                source=self.provider_name(),
            )
        )

        businesses = list(
            businesses or []
        )

        self.log(
            f"[BUSINESSES] "
            f"query={query!r} "
            f"page={page} "
            f"count={len(businesses)}"
        )

        self.results.extend(
            businesses
        )

        self.results_processed = (
            len(self.results)
        )

        self.pages_processed += 1

        self.query_pages[query] = (
            self.query_pages.get(
                query,
                0,
            )
            + 1
        )

        self.query_results[query] = (
            self.query_results.get(
                query,
                0,
            )
            + len(businesses)
        )

        self.update_progress()

        return businesses

    # ==========================================================
    # PROCESS QUERY
    # ==========================================================

    def process_query(
        self,
        query: str,
        extractor: BusinessExtractor,
    ) -> list[Any]:

        extracted_results: list[Any] = []

        if self.stop_requested():

            return extracted_results

        self.log(
            f"[SEARCH] {query}"
        )

        maximum_mode = (
            self.maximum_mode()
        )

        # ------------------------------------------------------
        # NORMAL MODE
        # ------------------------------------------------------

        if not maximum_mode:

            pages_per_query = (
                self.normal_pages_per_query()
            )

            self.log(
                f"[PAGINATION] "
                f"mode=NORMAL "
                f"pages={pages_per_query}"
            )

            for page in range(
                1,
                pages_per_query + 1,
            ):

                if self.stop_requested():

                    break

                try:

                    businesses = (
                        self.process_page(
                            query=query,
                            page=page,
                            extractor=extractor,
                        )
                    )

                except Exception as error:

                    self.log(
                        f"[ERROR] "
                        f"query={query!r} "
                        f"page={page} "
                        f"error={error}"
                    )

                    traceback.print_exc()

                    raise

                extracted_results.extend(
                    businesses
                )

                if self._reached_total_limit():

                    self.log(
                        "[LIMIT] "
                        "Maximum total result limit reached"
                    )

                    break

                self._wait_between_pages()

            return extracted_results

        # ------------------------------------------------------
        # MAXIMUM MODE
        # ------------------------------------------------------

        maximum_pages = (
            self.maximum_pages_per_query()
        )

        expected_page_size = (
            self.provider_page_size()
        )

        total_limit = (
            self.maximum_results()
        )

        self.log(
            "[PAGINATION] "
            "mode=MAXIMUM "
            f"safety_pages={maximum_pages} "
            f"expected_page_size="
            f"{expected_page_size} "
            f"total_limit="
            f"{total_limit or 'UNLIMITED'}"
        )

        previous_page_signature = None

        repeated_pages = 0

        for page in range(
            1,
            maximum_pages + 1,
        ):

            if self.stop_requested():

                break

            # --------------------------------------------------
            # GLOBAL LIMIT
            # --------------------------------------------------

            if self._reached_total_limit():

                self.log(
                    "[LIMIT] "
                    "Maximum total result limit reached"
                )

                break

            # --------------------------------------------------
            # FETCH
            # --------------------------------------------------

            try:

                raw = self.fetch_page(
                    query=query,
                    page=page,
                )

            except Exception as error:

                self.log(
                    f"[ERROR] "
                    f"query={query!r} "
                    f"page={page} "
                    f"error={error}"
                )

                traceback.print_exc()

                raise

            raw = (
                self._normalize_raw_results(
                    raw
                )
            )

            raw_count = len(
                raw
            )

            self.raw_results_processed += (
                raw_count
            )

            self.log(
                f"[RAW RESULTS] "
                f"query={query!r} "
                f"page={page} "
                f"count={raw_count}"
            )

            # --------------------------------------------------
            # EMPTY PAGE
            # --------------------------------------------------

            if raw_count == 0:

                self.empty_pages += 1

                self.log(
                    f"[PAGINATION END] "
                    f"query={query!r} "
                    f"page={page} "
                    f"reason=empty_page"
                )

                break

            # --------------------------------------------------
            # REPEATED PAGE
            # --------------------------------------------------

            page_signature = (
                self._page_identity(
                    raw
                )
            )

            if (
                previous_page_signature
                == page_signature
            ):

                repeated_pages += 1

                self.repeated_pages += 1

                self.log(
                    f"[PAGINATION END] "
                    f"query={query!r} "
                    f"page={page} "
                    f"reason=repeated_page"
                )

                if (
                    repeated_pages
                    >= self.DEFAULT_MAX_REPEATED_PAGES
                ):

                    break

            else:

                repeated_pages = 0

            previous_page_signature = (
                page_signature
            )

            # --------------------------------------------------
            # EXTRACTION
            # --------------------------------------------------

            businesses = (
                extractor.extract_many(
                    raw,
                    source=self.provider_name(),
                )
            )

            businesses = list(
                businesses or []
            )

            self.log(
                f"[BUSINESSES] "
                f"query={query!r} "
                f"page={page} "
                f"count={len(businesses)}"
            )

            self.results.extend(
                businesses
            )

            self.results_processed = (
                len(self.results)
            )

            self.pages_processed += 1

            self.query_pages[query] = (
                self.query_pages.get(
                    query,
                    0,
                )
                + 1
            )

            self.query_results[query] = (
                self.query_results.get(
                    query,
                    0,
                )
                + len(businesses)
            )

            extracted_results.extend(
                businesses
            )

            self.update_progress()

            # --------------------------------------------------
            # GLOBAL LIMIT
            # --------------------------------------------------

            if self._reached_total_limit():

                self.log(
                    "[LIMIT] "
                    "Maximum total result limit reached"
                )

                break

            # --------------------------------------------------
            # SHORT PAGE
            #
            # A provider returning fewer records than its
            # normal page size is generally indicating that
            # pagination has reached its end.
            #
            # We still process that page completely first.
            # --------------------------------------------------

            if (
                expected_page_size > 0
                and raw_count < expected_page_size
            ):

                self.log(
                    f"[PAGINATION END] "
                    f"query={query!r} "
                    f"page={page} "
                    f"reason=short_page "
                    f"count={raw_count} "
                    f"expected={expected_page_size}"
                )

                break

            # --------------------------------------------------
            # DELAY
            # --------------------------------------------------

            self._wait_between_pages()

        else:

            self.log(
                f"[PAGINATION SAFETY STOP] "
                f"query={query!r} "
                f"maximum_pages={maximum_pages}"
            )

        return extracted_results

    # ==========================================================
    # TOTAL LIMIT
    # ==========================================================

    def _reached_total_limit(
        self,
    ) -> bool:

        limit = (
            self.maximum_results()
        )

        if limit <= 0:

            return False

        return (
            len(self.results)
            >= limit
        )

    # ==========================================================
    # PAGE DELAY
    # ==========================================================

    def _wait_between_pages(
        self,
    ) -> None:

        delay = self._delay()

        if (
            delay <= 0
            or self.stop_requested()
        ):

            return

        self._stop_event.wait(
            delay
        )

    # ==========================================================
    # QUERY GENERATION
    # ==========================================================

    def build_queries(
        self,
    ) -> list[str]:

        generator = QueryGenerator(
            self.config
        )

        queries = (
            generator.generate()
        )

        return list(
            queries or []
        )

    # ==========================================================
    # EXTRACTOR
    # ==========================================================

    def build_extractor(
        self,
    ) -> BusinessExtractor:

        return BusinessExtractor(

            keyword=getattr(
                self.config,
                "keyword",
                "",
            ),

            city=getattr(
                self.config,
                "city",
                "",
            ),

            province=getattr(
                self.config,
                "province",
                "",
            ),
        )

    # ==========================================================
    # CONFIG VALIDATION
    # ==========================================================

    def validate_config(
        self,
    ) -> None:

        if self.config is None:

            raise RuntimeError(
                "Configuration is missing."
            )

        validate = getattr(
            self.config,
            "validate",
            None,
        )

        if not callable(
            validate
        ):

            raise RuntimeError(
                "Configuration must provide "
                "validate()."
            )

        validate()

    # ==========================================================
    # RUN
    # ==========================================================

    def run(
        self,
    ) -> list[Any]:

        if self.running:

            raise RuntimeError(
                "ScraperEngine is already running."
            )

        self.reset()

        self.running = True

        self.log(
            "[START] Scraper started"
        )

        try:

            # --------------------------------------------------
            # CONFIG
            # --------------------------------------------------

            self.validate_config()

            # --------------------------------------------------
            # PROVIDER
            # --------------------------------------------------

            self._require_provider()

            provider_name = (
                self.provider_name()
            )

            if not provider_name:

                raise RuntimeError(
                    "Provider name is missing."
                )

            self.log(
                f"[PROVIDER READY] "
                f"{provider_name}"
            )

            # --------------------------------------------------
            # MODE
            # --------------------------------------------------

            if self.maximum_mode():

                self.log(
                    "[DATA MODE] "
                    "MAXIMUM / ALL AVAILABLE"
                )

            else:

                self.log(
                    "[DATA MODE] "
                    "NORMAL / CONFIGURED PAGES"
                )

            # --------------------------------------------------
            # QUERIES
            # --------------------------------------------------

            queries = (
                self.build_queries()
            )

            self.log(
                f"[QUERY COUNT] "
                f"{len(queries)}"
            )

            if not queries:

                self.log(
                    "[WARNING] "
                    "No queries generated."
                )

            # --------------------------------------------------
            # EXTRACTOR
            # --------------------------------------------------

            extractor = (
                self.build_extractor()
            )

            # --------------------------------------------------
            # EXECUTION
            # --------------------------------------------------

            total_queries = len(
                queries
            )

            for query_index, query in enumerate(
                queries,
                start=1,
            ):

                if self.stop_requested():

                    break

                if self._reached_total_limit():

                    self.log(
                        "[LIMIT] "
                        "Global maximum result limit reached"
                    )

                    break

                query = str(
                    query
                ).strip()

                if not query:

                    continue

                self.log(
                    f"[QUERY "
                    f"{query_index}/"
                    f"{total_queries}] "
                    f"{query}"
                )

                self.process_query(
                    query=query,
                    extractor=extractor,
                )

                self.queries_processed += 1

                self.update_progress()

            # --------------------------------------------------
            # COMPLETION
            # --------------------------------------------------

            if self.stop_requested():

                self.log(
                    "[STOPPED] "
                    "Scraper stopped by user"
                )

            elif self._reached_total_limit():

                self.log(
                    "[COMPLETE] "
                    "Maximum configured result limit reached"
                )

            else:

                self.log(
                    "[COMPLETE] "
                    "All queries processed"
                )

        except Exception as error:

            self.log(
                f"[FATAL] {error}"
            )

            traceback.print_exc()

            raise

        finally:

            self.running = False

            self.log(
                "[FINISHED] "
                "Scraper execution finished | "
                f"queries="
                f"{self.queries_processed} | "
                f"pages="
                f"{self.pages_processed} | "
                f"raw="
                f"{self.raw_results_processed} | "
                f"results="
                f"{len(self.results)} | "
                f"empty_pages="
                f"{self.empty_pages} | "
                f"repeated_pages="
                f"{self.repeated_pages}"
            )

            self.update_progress()

        return list(
            self.results
        )

    # ==========================================================
    # PROGRESS
    # ==========================================================

    def progress(
        self,
    ) -> dict[str, Any]:

        maximum_limit = (
            self.maximum_results()
        )

        return {

            "running":
                self.running,

            "queries":
                self.queries_processed,

            "pages":
                self.pages_processed,

            "raw_results":
                self.raw_results_processed,

            "results":
                self.results_processed,

            "total":
                len(self.results),

            "stop_requested":
                self.stop_requested(),

            "provider":
                self.provider_name(),

            "data_mode":
                (
                    "maximum"
                    if self.maximum_mode()
                    else "normal"
                ),

            "maximum_results":
                maximum_limit,

            "maximum_pages_per_query":
                self.maximum_pages_per_query(),

            "empty_pages":
                self.empty_pages,

            "repeated_pages":
                self.repeated_pages,

            "query_pages":
                dict(
                    self.query_pages
                ),

            "query_results":
                dict(
                    self.query_results
                ),
        }

    # ==========================================================
    # REPR
    # ==========================================================

    def __repr__(
        self,
    ) -> str:

        return (
            f"<ScraperEngine "
            f"provider="
            f"{self.provider_name()!r} "
            f"running="
            f"{self.running} "
            f"mode="
            f"{'maximum' if self.maximum_mode() else 'normal'}>"
        )


# ==========================================================
# FINAL STATUS
# ==========================================================
#
# ARCHITECTURE        : CANONICAL
# DATABASE COUPLING   : NONE
# PIPELINE COUPLING   : NONE
# PROVIDER BRANCHING  : NONE
# QUERY OWNERSHIP     : QueryGenerator
# EXTRACTION OWNERSHIP: BusinessExtractor
# THREAD OWNERSHIP    : ScraperJob
# PROCESS OWNERSHIP   : ScraperProcess
# DATABASE OWNERSHIP  : ScraperPipeline
#
# PAGINATION          : HARDENED
# MAXIMUM DATA MODE   : SUPPORTED
# ARTIFICIAL TRUNCATE : REMOVED
# PAGE LOOP PROTECTION: ENABLED
# REPEATED PAGE STOP  : ENABLED
# EMPTY PAGE STOP     : ENABLED
# SHORT PAGE STOP     : ENABLED
# GLOBAL LIMIT        : OPTIONAL
# STOP API            : PUBLIC
# ERROR PROPAGATION   : HARDENED
# CONFIG VALIDATION   : HARDENED
# PROGRESS API        : STABLE
#
# FINAL VERDICT:
#     APPROVED / CANONICAL
#
# ==========================================================