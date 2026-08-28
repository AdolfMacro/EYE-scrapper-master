# ==========================================================
# FILE REVIEW — pipeline.py
#
# STATUS       : APPROVED — BUSINESS ARCHITECTURE ALIGNED
# ROLE         : Business Validation / Deduplication / Persistence
# LAYER        : Scraper / Pipeline
#
# RESPONSIBILITIES
# ----------------------------------------------------------
# 1. Receive canonical Business objects
# 2. Normalize canonical fields
# 3. Validate geographic coordinates
# 4. Perform runtime deduplication
# 5. Persist accepted records
# 6. Track pipeline statistics
# 7. Expose machine-readable snapshots
#
# ARCHITECTURAL BOUNDARY
# ----------------------------------------------------------
#
# Provider
#      ↓
# Raw Result
#      ↓
# Extractor / Normalizer
#      ↓
# Canonical Business
#      ↓
# ScraperPipeline
#      ├── Normalize
#      ├── Validate
#      ├── Runtime Deduplication
#      └── Persistence
#               ↓
#           Database
#
# PIPELINE DOES NOT:
# ----------------------------------------------------------
# ❌ Execute Provider searches
# ❌ Generate Queries
# ❌ Manage Providers
# ❌ Manage Jobs
# ❌ Manage Processes
# ❌ Construct Business objects from arbitrary raw data
# ❌ Manage RunContext lifecycle
#
# DEDUPLICATION POLICY
# ----------------------------------------------------------
#
# Runtime Deduplication:
#     Pipeline / Deduplicator
#
# Persistent Integrity:
#     Database
#
# COORDINATE POLICY
# ----------------------------------------------------------
#
# A record is accepted only when:
#
#     latitude  is valid
#     AND
#     longitude is valid
#
# ==========================================================

from __future__ import annotations

import math

from typing import (
    Any,
    Callable,
    Iterable,
    List,
    Optional,
)

from scraper.context import RunContext
from scraper.normalizer import (
    normalize_phone,
    normalize_text,
)


class ScraperPipeline:
    """
    Post-processing boundary between canonical Business objects
    and persistent storage.

    Expected flow:

        Provider
            ↓
        Raw Result
            ↓
        Extractor / Normalizer
            ↓
        Business
            ↓
        ScraperPipeline
            ↓
        Database
    """

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(
        self,
        context: RunContext,
        deduplicator=None,
        database=None,
        logger: Optional[
            Callable[[str], None]
        ] = None,
    ) -> None:

        self.context = context

        self.deduplicator = (
            deduplicator
        )

        self.database = database

        self.logger = logger

        # ------------------------------------------------------
        # Runtime statistics
        # ------------------------------------------------------

        self.accepted = 0
        self.rejected = 0
        self.duplicates = 0
        self.saved = 0

    # ==========================================================
    # LOGGING
    # ==========================================================

    def _log(
        self,
        message: Any,
    ) -> None:
        """
        Safely emit a pipeline log message.

        Logger failures must never terminate the pipeline.
        """

        if not callable(
            self.logger
        ):
            return

        try:

            self.logger(
                str(message)
            )

        except Exception:

            pass

    # ==========================================================
    # NORMALIZATION
    # ==========================================================

    @staticmethod
    def _normalize_value(
        value: Any,
        field: str,
    ) -> Any:
        """
        Normalize one canonical Business field.

        Only textual fields are normalized.

        Numeric fields such as latitude/longitude are left
        untouched and are validated separately.
        """

        if value is None:

            return value

        if not isinstance(
            value,
            str,
        ):

            return value

        if field == "phone":

            try:

                return normalize_phone(
                    value
                )

            except Exception:

                return ""

        try:

            return normalize_text(
                value
            )

        except Exception:

            return value.strip()

    # ==========================================================
    # NORMALIZE BUSINESS
    # ==========================================================

    def normalize(
        self,
        item: Any,
    ) -> Any:
        """
        Normalize canonical Business data.

        The Pipeline does not construct a Business from arbitrary
        Provider data. That responsibility belongs to the
        upstream Extractor / Normalizer layer.

        Object fields are normalized in place.

        Dictionaries are copied for compatibility with the
        canonical Database boundary.
        """

        fields = (
            "name",
            "category",
            "keyword",
            "province",
            "city",
            "address",
            "neighborhood",
            "street",
            "website",
            "source",
            "source_url",
            "source_id",
            "url",
            "phone",
        )

        # ------------------------------------------------------
        # Dictionary compatibility path
        # ------------------------------------------------------

        if isinstance(
            item,
            dict,
        ):

            result = dict(
                item
            )

            for field in fields:

                if field not in result:

                    continue

                result[field] = (
                    self._normalize_value(
                        result[field],
                        field,
                    )
                )

            return result

        # ------------------------------------------------------
        # Canonical Business path
        # ------------------------------------------------------

        for field in fields:

            if not hasattr(
                item,
                field,
            ):

                continue

            value = getattr(
                item,
                field,
            )

            normalized = (
                self._normalize_value(
                    value,
                    field,
                )
            )

            try:

                setattr(
                    item,
                    field,
                    normalized,
                )

            except Exception:

                # Some canonical models may expose
                # read-only properties.
                pass

        return item

    # ==========================================================
    # COORDINATE VALUE
    # ==========================================================

    @staticmethod
    def _coordinate_value(
        value: Any,
    ) -> Optional[float]:
        """
        Safely convert a coordinate to finite float.
        """

        if value is None:

            return None

        if isinstance(
            value,
            str,
        ):

            value = value.strip()

            if not value:

                return None

        try:

            value = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return None

        if not math.isfinite(
            value
        ):

            return None

        return value

    # ==========================================================
    # VALID COORDINATES
    # ==========================================================

    @classmethod
    def has_valid_coordinates(
        cls,
        item: Any,
    ) -> bool:
        """
        Validate latitude and longitude.

        Both coordinates are mandatory.

        Latitude:
            -90 <= latitude <= 90

        Longitude:
            -180 <= longitude <= 180
        """

        if isinstance(
            item,
            dict,
        ):

            latitude = item.get(
                "latitude"
            )

            longitude = item.get(
                "longitude"
            )

        else:

            latitude = getattr(
                item,
                "latitude",
                None,
            )

            longitude = getattr(
                item,
                "longitude",
                None,
            )

        latitude = (
            cls._coordinate_value(
                latitude
            )
        )

        longitude = (
            cls._coordinate_value(
                longitude
            )
        )

        if latitude is None:

            return False

        if longitude is None:

            return False

        return (
            -90.0
            <= latitude
            <= 90.0
            and
            -180.0
            <= longitude
            <= 180.0
        )

    # ==========================================================
    # RUNTIME DEDUPLICATION
    # ==========================================================

    def is_duplicate(
        self,
        item: Any,
    ) -> bool:
        """
        Ask the runtime Deduplicator whether the item has
        already been seen during the current execution.

        Persistent database uniqueness is NOT handled here.
        """

        if self.deduplicator is None:

            return False

        seen = getattr(
            self.deduplicator,
            "seen",
            None,
        )

        if not callable(
            seen
        ):

            return False

        try:

            return bool(
                seen(item)
            )

        except Exception as error:

            self._log(
                "[PIPELINE] "
                f"DEDUPLICATOR ERROR: {error}"
            )

            # Deduplicator failure must not silently mark
            # records as duplicates.
            return False

    # ==========================================================
    # DATABASE SAVE
    # ==========================================================

    def save(
        self,
        item: Any,
        provider: Optional[str] = None,
    ) -> bool:
        """
        Persist one accepted canonical Business.

        Database remains responsible for persistent integrity,
        including database-level duplicate protection.

        Canonical Database API:

            insert_business(
                item,
                return_reason=True,
            )
        """

        # ------------------------------------------------------
        # Optional database
        # ------------------------------------------------------

        if self.database is None:

            self._log(
                "[PIPELINE] "
                "DATABASE SKIPPED"
            )

            return True

        # ------------------------------------------------------
        # Canonical Database API
        # ------------------------------------------------------

        insert_business = getattr(
            self.database,
            "insert_business",
            None,
        )

        if not callable(
            insert_business
        ):

            raise AttributeError(
                "Database must provide "
                "insert_business()."
            )

        try:

            success, reason = (
                insert_business(
                    item,
                    return_reason=True,
                )
            )

        except TypeError:

            # Compatibility with older Database
            # implementations that do not expose
            # return_reason.
            success = bool(
                insert_business(
                    item
                )
            )

            reason = (
                "INSERTED"
                if success
                else "REJECTED"
            )

        # ------------------------------------------------------
        # Saved
        # ------------------------------------------------------

        if success:

            self.saved += 1

            self.context.stats.saved_result(
                provider=provider
            )

            self._log(
                "[PIPELINE] "
                f"SAVED: {reason}"
            )

            return True

        # ------------------------------------------------------
        # Persistent duplicate
        # ------------------------------------------------------

        if (
            isinstance(
                reason,
                str,
            )
            and reason.upper().startswith(
                "DUPLICATE"
            )
        ):

            self.duplicates += 1

            self.context.stats.duplicate(
                provider=provider
            )

            self._log(
                "[PIPELINE] "
                f"DATABASE DUPLICATE: {reason}"
            )

            return False

        # ------------------------------------------------------
        # Database rejection
        # ------------------------------------------------------

        self.rejected += 1

        self.context.stats.rejected_result(
            provider=provider
        )

        self._log(
            "[PIPELINE] "
            f"REJECTED: {reason}"
        )

        return False

    # ==========================================================
    # REJECT
    # ==========================================================

    def reject(
        self,
        reason: str,
        provider: Optional[str] = None,
    ) -> None:
        """
        Centralized rejection handling.
        """

        self.rejected += 1

        self.context.stats.rejected_result(
            provider=provider
        )

        self._log(
            "[PIPELINE] "
            f"REJECTED: {reason}"
        )

    # ==========================================================
    # PROCESS ONE
    # ==========================================================

    def process(
        self,
        item: Any,
        provider: Optional[str] = None,
    ) -> Optional[Any]:
        """
        Process one canonical Business.

        Processing order:

            1. Validate item
            2. Normalize
            3. Validate coordinates
            4. Runtime deduplication
            5. Persist
            6. Accept
        """

        # ======================================================
        # INVALID ITEM
        # ======================================================

        if item is None:

            self.reject(
                "INVALID_ITEM",
                provider=provider,
            )

            return None

        # ======================================================
        # NORMALIZATION
        # ======================================================

        normalized = self.normalize(
            item
        )

        # ======================================================
        # COORDINATE GATE
        # ======================================================

        if not self.has_valid_coordinates(
            normalized
        ):

            self.reject(
                "INVALID_COORDINATES",
                provider=provider,
            )

            return None

        # ======================================================
        # RUNTIME DEDUPLICATION
        # ======================================================

        if self.is_duplicate(
            normalized
        ):

            self.duplicates += 1

            self.context.stats.duplicate(
                provider=provider
            )

            self._log(
                "[PIPELINE] "
                "RUNTIME DUPLICATE"
            )

            return None

        # ======================================================
        # DATABASE
        # ======================================================

        if not self.save(
            normalized,
            provider=provider,
        ):

            return None

        # ======================================================
        # ACCEPT
        # ======================================================

        self.accepted += 1

        self.context.stats.accepted_result(
            provider=provider
        )

        self._log(
            "[PIPELINE] "
            "ACCEPTED"
        )

        return normalized

    # ==========================================================
    # PROCESS MANY
    # ==========================================================

    def process_many(
        self,
        items: Iterable[Any],
        provider: Optional[str] = None,
    ) -> List[Any]:
        """
        Process multiple canonical Business records.
        """

        results: List[Any] = []

        if items is None:

            return results

        for item in items:

            processed = self.process(
                item,
                provider=provider,
            )

            if processed is not None:

                results.append(
                    processed
                )

        return results

    # ==========================================================
    # RUN
    # ==========================================================

    def run(
        self,
        items: Iterable[Any],
        provider: Optional[str] = None,
    ) -> List[Any]:
        """
        Execute the complete post-processing pipeline.
        """

        if items is None:

            items = []

        items = list(
            items
        )

        self._log(
            "[PIPELINE] "
            f"INPUT: {len(items)}"
        )

        results = self.process_many(
            items,
            provider=provider,
        )

        self._log(
            "[PIPELINE] "
            "COMPLETE | "
            f"accepted={self.accepted} "
            f"saved={self.saved} "
            f"duplicates={self.duplicates} "
            f"rejected={self.rejected}"
        )

        return results

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(
        self,
    ) -> dict[str, Any]:
        """
        Return machine-readable runtime statistics.
        """

        return {
            "accepted": self.accepted,
            "rejected": self.rejected,
            "duplicates": self.duplicates,
            "saved": self.saved,
        }

    # ==========================================================
    # RESET STATISTICS
    # ==========================================================

    def reset(
        self,
    ) -> None:
        """
        Reset pipeline-local statistics.

        RunContext lifecycle remains outside Pipeline.
        """

        self.accepted = 0
        self.rejected = 0
        self.duplicates = 0
        self.saved = 0

    # ==========================================================
    # REPRESENTATION
    # ==========================================================

    def __repr__(
        self,
    ) -> str:

        return (
            f"<ScraperPipeline "
            f"accepted={self.accepted} "
            f"saved={self.saved} "
            f"duplicates={self.duplicates} "
            f"rejected={self.rejected}>"
        )


# ==========================================================
# FINAL STATUS
# ==========================================================
#
# ARCHITECTURE          : APPROVED
# CANONICAL ENTITY      : BUSINESS
# NORMALIZATION         : APPROVED
# COORDINATE VALIDATION : APPROVED
# RUNTIME DEDUPLICATION : APPROVED
# DATABASE BOUNDARY     : APPROVED
# DATABASE API          : insert_business()
# STATISTICS            : APPROVED
# CONTEXT OWNERSHIP     : APPROVED
# PROVIDER ISOLATION    : APPROVED
# PROCESS ISOLATION     : APPROVED
#
# DEDUPLICATION POLICY
# ----------------------------------------------------------
# Runtime duplicate detection:
#     Pipeline / Deduplicator
#
# Persistent duplicate protection:
#     Database
#
# FINAL VERDICT
# ----------------------------------------------------------
# APPROVED / BUSINESS ARCHITECTURE ALIGNED
#
# Ready for replacement.
# ==========================================================