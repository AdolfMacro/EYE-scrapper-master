from __future__ import annotations

from typing import Any

from scraper.normalizer import (
    normalize_name,
    normalize_city,
    phone_digits,
)


class DeduplicationService:
    """
    In-memory deduplication service for a single scraper run.

    Responsibilities
    ----------------
    - Generate a stable identity key
    - Detect duplicates inside the current run
    - Track seen records
    - Reset runtime state

    This service does NOT:
        - Access the database
        - Perform persistent deduplication
        - Manage providers
        - Normalize complete School objects
        - Decide database uniqueness rules

    Architecture
    ------------
        ScraperEngine
              │
              ▼
        ScraperPipeline
              │
              ▼
        DeduplicationService
              │
              ▼
        Database

    Important
    ---------
    DeduplicationService is run-scoped.

    Database remains responsible for persistent
    duplicate protection across different runs.
    """

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(self) -> None:

        self._memory: set[str] = set()

    # ==========================================================
    # VALUE ACCESS
    # ==========================================================

    @staticmethod
    def _get(
        result: Any,
        field: str,
        default: Any = "",
    ) -> Any:

        if isinstance(result, dict):

            return result.get(
                field,
                default,
            )

        return getattr(
            result,
            field,
            default,
        )

    # ==========================================================
    # TEXT
    # ==========================================================

    @staticmethod
    def _text(
        value: Any,
    ) -> str:

        if value is None:
            return ""

        return str(
            value
        ).strip()

    # ==========================================================
    # SOURCE ID
    # ==========================================================

    def source_id_key(
        self,
        result: Any,
    ) -> str:

        source = self._text(
            self._get(
                result,
                "source",
            )
        )

        source_id = self._text(
            self._get(
                result,
                "source_id",
            )
        )

        if not source_id:
            return ""

        if source:

            return (
                "source_id:"
                f"{source.casefold()}:"
                f"{source_id.casefold()}"
            )

        return (
            "source_id:"
            f"{source_id.casefold()}"
        )

    # ==========================================================
    # PHONE KEY
    # ==========================================================

    def phone_key(
        self,
        result: Any,
    ) -> str:

        phone = phone_digits(
            self._get(
                result,
                "phone",
            )
        )

        if not phone:
            return ""

        return (
            "phone:"
            f"{phone}"
        )

    # ==========================================================
    # CANONICAL KEY
    # ==========================================================

    def canonical_key(
        self,
        result: Any,
    ) -> str:

        name = normalize_name(
            self._get(
                result,
                "name",
            )
        )

        city = normalize_city(
            self._get(
                result,
                "city",
            )
        )

        province = normalize_city(
            self._get(
                result,
                "province",
            )
        )

        address = normalize_name(
            self._get(
                result,
                "address",
            )
        )

        parts = [
            value
            for value in (
                name,
                city,
                province,
                address,
            )
            if value
        ]

        if not parts:
            return ""

        return (
            "canonical:"
            + "|".join(parts)
        )

    # ==========================================================
    # IDENTITY KEYS
    # ==========================================================

    def keys(
        self,
        result: Any,
    ) -> list[str]:

        keys: list[str] = []

        source_id = self.source_id_key(
            result
        )

        if source_id:

            keys.append(
                source_id
            )

        phone = self.phone_key(
            result
        )

        if phone:

            keys.append(
                phone
            )

        canonical = self.canonical_key(
            result
        )

        if canonical:

            keys.append(
                canonical
            )

        return keys

    # ==========================================================
    # KEY
    # ==========================================================

    def key(
        self,
        result: Any,
    ) -> str:

        keys = self.keys(
            result
        )

        if not keys:

            return ""

        # Primary identity key.
        #
        # source_id has the highest priority,
        # followed by phone and canonical identity.

        return keys[0]

    # ==========================================================
    # MEMORY
    # ==========================================================

    def seen(
        self,
        result: Any,
    ) -> bool:
        """
        Return True if the result was already seen.

        A result may be considered duplicate when ANY
        of its identity keys has already been observed.
        """

        keys = self.keys(
            result
        )

        if not keys:

            return False

        for key in keys:

            if key in self._memory:

                return True

        for key in keys:

            self._memory.add(
                key
            )

        return False

    # ==========================================================
    # FORGET
    # ==========================================================

    def clear(
        self,
    ) -> None:

        self._memory.clear()

    # ==========================================================
    # SIZE
    # ==========================================================

    def size(
        self,
    ) -> int:

        return len(
            self._memory
        )

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(
        self,
    ) -> dict[str, Any]:

        return {
            "memory_size": len(
                self._memory
            ),
        }

    # ==========================================================
    # REPRESENTATION
    # ==========================================================

    def __repr__(
        self,
    ) -> str:

        return (
            "<DeduplicationService "
            f"memory_size={self.size()}>"
        )