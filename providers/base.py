# ==========================================================
# EYES MASTER — PROVIDER ABSTRACTION
# ==========================================================
#
# FILE:
#     providers/base.py
#
# STATUS:
#     CANONICAL / CORE
#
# ROLE:
#     Abstract contract for every EYES search provider.
#
# CORE RULE:
#
#     Provider:
#         Query -> Search -> Raw/Normalized Results
#
#     Provider does NOT:
#         - generate queries
#         - manage cities
#         - manage keywords
#         - create jobs
#         - manage database
#         - create Business objects
#         - persist data
#         - control GUI
#
# ARCHITECTURE:
#
#     Keyword + City
#             │
#             ▼
#      QueryGenerator
#             │
#             ▼
#         SearchJob
#             │
#             ▼
#      SearchProvider
#             │
#             ▼
#       Search Results
#             │
#             ▼
#         Extractor
#             │
#             ▼
#          Business
#             │
#             ▼
#         Database
#
# ==========================================================

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class SearchProvider(ABC):
    """
    Canonical abstract base class for EYES providers.

    Every concrete provider must implement search().

    The Provider abstraction is deliberately independent
    from Business and Database.
    """

    # ======================================================
    # IDENTITY
    # ======================================================

    name: str = "unknown"

    version: str = "1.0"

    # ======================================================
    # INIT
    # ======================================================

    def __init__(
        self,
        timeout: int = 15,
    ) -> None:
        """
        Initialize the Provider.

        Provider-specific configuration belongs to the
        concrete Provider implementation.
        """

        self.timeout = max(
            1,
            int(timeout),
        )

    # ======================================================
    # SEARCH
    # ======================================================

    @abstractmethod
    def search(
        self,
        query: str,
        page: int = 1,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Execute a search request.

        Args:
            query:
                Fully constructed search query.

            page:
                Requested result page.

            **kwargs:
                Provider-specific options.

        Returns:
            list[dict[str, Any]]

        Provider-specific response structures should be
        converted into the common Search Result format.
        """

        raise NotImplementedError

    # ======================================================
    # RESULT NORMALIZATION
    # ======================================================

    def normalize_result(
        self,
        result: Any,
    ) -> Optional[dict[str, Any]]:
        """
        Normalize one provider result.

        This is NOT Business normalization.

        It only creates a common intermediate search-result
        representation consumed by the extraction layer.
        """

        if not isinstance(
            result,
            dict,
        ):
            return None

        return {

            # --------------------------------------------------
            # SEARCH RESULT IDENTITY
            # --------------------------------------------------

            "title": self._string(
                result.get("title")
            ),

            "name": self._string(
                result.get("name")
            ),

            # --------------------------------------------------
            # LOCATION
            # --------------------------------------------------

            "province": self._string(
                result.get("province")
            ),

            "city": self._string(
                result.get("city")
            ),

            "address": self._string(
                result.get("address")
            ),

            "neighborhood": self._string(
                result.get("neighborhood")
            ),

            "street": self._string(
                result.get("street")
            ),

            # --------------------------------------------------
            # CONTACT
            # --------------------------------------------------

            "phone": self._string(
                result.get("phone")
            ),

            "website": self._string(
                result.get("website")
            ),

            # --------------------------------------------------
            # GEOLOCATION
            # --------------------------------------------------

            "latitude": self._float(
                result.get("latitude")
            ),

            "longitude": self._float(
                result.get("longitude")
            ),

            "distance_km": self._float(
                result.get("distance_km")
            ),

            # --------------------------------------------------
            # SOURCE
            # --------------------------------------------------

            "url": self._string(
                result.get("url")
            ),

            "source_url": self._string(
                result.get("source_url")
            ),

            "source_id": self._string_or_none(
                result.get("source_id")
            ),

            "source": self.provider_name(),

            # --------------------------------------------------
            # SEARCH CONTEXT
            # --------------------------------------------------

            "snippet": self._string(
                result.get("snippet")
            ),

        }

    # ======================================================
    # NORMALIZE MANY
    # ======================================================

    def normalize_results(
        self,
        results: Any,
    ) -> list[dict[str, Any]]:
        """
        Normalize multiple search results.

        Invalid results are ignored.
        """

        if not isinstance(
            results,
            (list, tuple),
        ):
            return []

        normalized = []

        for result in results:

            item = self.normalize_result(
                result
            )

            if item is None:
                continue

            normalized.append(
                item
            )

        return normalized

    # ======================================================
    # PROVIDER INFO
    # ======================================================

    def info(
        self,
    ) -> dict[str, Any]:
        """
        Return generic Provider metadata.

        ProviderManager may expose this information to
        higher layers without knowing implementation details.
        """

        return {

            "name": self.provider_name(),

            "version": self.version,

            "timeout": self.timeout,

            "class": self.__class__.__name__,

        }

    # ======================================================
    # HEALTH CHECK
    # ======================================================

    def health_check(
        self,
    ) -> bool:
        """
        Perform a lightweight Provider health check.

        Concrete providers may override this method.

        Default:
            Provider is considered available.
        """

        return True

    # ======================================================
    # PROVIDER NAME
    # ======================================================

    def provider_name(
        self,
    ) -> str:
        """
        Return the canonical Provider identifier.
        """

        return self._string(
            self.name
        ).casefold()

    # ======================================================
    # TEXT NORMALIZATION
    # ======================================================

    @staticmethod
    def _string(
        value: Any,
    ) -> str:
        """
        Convert arbitrary input into normalized text.
        """

        if value is None:

            return ""

        return " ".join(
            str(value)
            .strip()
            .split()
        )

    # ======================================================
    # OPTIONAL TEXT
    # ======================================================

    @classmethod
    def _string_or_none(
        cls,
        value: Any,
    ) -> Optional[str]:
        """
        Convert arbitrary input into optional text.

        Empty values become None.
        """

        value = cls._string(
            value
        )

        return value or None

    # ======================================================
    # FLOAT
    # ======================================================

    @staticmethod
    def _float(
        value: Any,
    ) -> Optional[float]:
        """
        Convert input into a finite float.

        Invalid values become None.
        """

        if value in (
            None,
            "",
        ):
            return None

        try:

            result = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return None

        if result != result:
            return None

        if result in (
            float("inf"),
            float("-inf"),
        ):
            return None

        return result

    # ======================================================
    # INTEGER
    # ======================================================

    @staticmethod
    def _int(
        value: Any,
    ) -> Optional[int]:
        """
        Convert input into an integer.

        Invalid values become None.
        """

        if value in (
            None,
            "",
        ):
            return None

        try:

            return int(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return None

    # ======================================================
    # REPRESENTATION
    # ======================================================

    def __repr__(
        self,
    ) -> str:
        """
        Developer-friendly representation.
        """

        return (
            f"{self.__class__.__name__}("
            f"name={self.provider_name()!r}, "
            f"version={self.version!r}, "
            f"timeout={self.timeout!r}"
            ")"
        )