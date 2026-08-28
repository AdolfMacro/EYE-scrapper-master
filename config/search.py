from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class SearchConfig:
    """
    Canonical generic search configuration.

    Supports both:

        keywords = ["مدرسه", "دبیرستان"]

    and legacy:

        keyword = "مدرسه"

    Canonical internal representation:

        keywords -> list[str]

    The first keyword is exposed through the legacy
    `keyword` property for backward compatibility.

    This class is completely domain-independent.

    Examples:

        keywords = ["رستوران"]
        keywords = ["بیمارستان", "درمانگاه"]
        keywords = ["فروشگاه", "سوپرمارکت"]
        keywords = ["شرکت نرم افزاری"]
        keywords = ["مدرسه", "دبیرستان"]

    All of them are valid generic search configurations.
    """

    # ==========================================================
    # SEARCH TARGET
    # ==========================================================

    keywords: list[str] = field(
        default_factory=list
    )

    # ==========================================================
    # LOCATION
    # ==========================================================

    province: str = ""

    city: str = ""

    radius: float = 0.0

    # ==========================================================
    # PROVIDER
    # ==========================================================

    provider: str = "google"

    # ==========================================================
    # SEARCH LIMITS
    # ==========================================================

    max_queries: int = 20

    pages_per_query: int = 1

    results_per_page: int = 100

    # ==========================================================
    # NETWORK
    # ==========================================================

    delay: float = 1.0

    timeout: int = 15

    # ==========================================================
    # LEGACY KEYWORD COMPATIBILITY
    # ==========================================================

    @property
    def keyword(self) -> str:
        """
        Return the first configured keyword.

        This property exists for backward compatibility with
        older components that still expect:

            config.keyword

        Canonical multi-keyword access should use:

            config.keywords
        """

        if not self.keywords:
            return ""

        return self.keywords[0]

    @keyword.setter
    def keyword(
        self,
        value: str,
    ) -> None:
        """
        Set the legacy single keyword.

        Assigning:

            config.keyword = "مدرسه"

        replaces the current keyword collection with:

            ["مدرسه"]
        """

        self.keywords = self._normalize_keywords(
            [value]
        )

    # ==========================================================
    # KEYWORD NORMALIZATION
    # ==========================================================

    @staticmethod
    def _normalize_keywords(
        values: Iterable[str] | None,
    ) -> list[str]:
        """
        Normalize, clean and deduplicate keywords.

        Rules:

            - None is ignored
            - non-string values are rejected
            - surrounding whitespace is removed
            - internal whitespace is normalized
            - empty values are ignored
            - duplicates are removed case-insensitively
            - original order is preserved
        """

        if values is None:
            return []

        result: list[str] = []

        seen: set[str] = set()

        for value in values:

            if not isinstance(
                value,
                str,
            ):
                raise ValueError(
                    "Each keyword must be a string."
                )

            keyword = " ".join(
                value.strip().split()
            )

            if not keyword:
                continue

            normalized = keyword.casefold()

            if normalized in seen:
                continue

            seen.add(
                normalized
            )

            result.append(
                keyword
            )

        return result

    # ==========================================================
    # POST INIT
    # ==========================================================

    def __post_init__(self) -> None:
        """
        Normalize configuration immediately after construction.

        This guarantees that SearchConfig exposes a stable
        internal keyword representation.
        """

        self.keywords = self._normalize_keywords(
            self.keywords
        )

        self.province = self._normalize_text(
            self.province
        )

        self.city = self._normalize_text(
            self.city
        )

        self.provider = self._normalize_text(
            self.provider
        )

    # ==========================================================
    # TEXT NORMALIZATION
    # ==========================================================

    @staticmethod
    def _normalize_text(
        value,
    ) -> str:
        """
        Normalize a generic textual configuration value.
        """

        if value is None:
            return ""

        if not isinstance(
            value,
            str,
        ):
            return str(value).strip()

        return " ".join(
            value.strip().split()
        )

    # ==========================================================
    # KEYWORD ACCESS
    # ==========================================================

    def get_keywords(self) -> list[str]:
        """
        Return a defensive copy of configured keywords.

        The returned list can be modified by the caller
        without changing SearchConfig directly.
        """

        return list(
            self.keywords
        )

    # ==========================================================
    # VALIDATION
    # ==========================================================

    def validate(self) -> bool:
        """
        Validate the complete search configuration.

        Raises:
            ValueError:
                If any configuration value is invalid.
        """

        # ------------------------------------------------------
        # KEYWORDS
        # ------------------------------------------------------

        if not isinstance(
            self.keywords,
            list,
        ):
            raise ValueError(
                "keywords must be a list."
            )

        self.keywords = self._normalize_keywords(
            self.keywords
        )

        if not self.keywords:

            raise ValueError(
                "Scraper keyword is required."
            )

        # ------------------------------------------------------
        # LOCATION
        # ------------------------------------------------------

        if not isinstance(
            self.province,
            str,
        ):
            raise ValueError(
                "province must be a string."
            )

        if not isinstance(
            self.city,
            str,
        ):
            raise ValueError(
                "city must be a string."
            )

        # ------------------------------------------------------
        # RADIUS
        # ------------------------------------------------------

        try:

            radius = float(
                self.radius
            )

        except (
            TypeError,
            ValueError,
        ):

            raise ValueError(
                "radius must be a number."
            )

        if radius < 0:

            raise ValueError(
                "radius cannot be negative."
            )

        self.radius = radius

        # ------------------------------------------------------
        # PROVIDER
        # ------------------------------------------------------

        if not isinstance(
            self.provider,
            str,
        ):
            raise ValueError(
                "provider must be a string."
            )

        self.provider = (
            self.provider.strip().lower()
        )

        if not self.provider:

            raise ValueError(
                "provider cannot be empty."
            )

        # ------------------------------------------------------
        # MAX QUERIES
        # ------------------------------------------------------

        try:

            self.max_queries = int(
                self.max_queries
            )

        except (
            TypeError,
            ValueError,
        ):

            raise ValueError(
                "max_queries must be an integer."
            )

        if self.max_queries < 1:

            raise ValueError(
                "max_queries must be greater than zero."
            )

        # ------------------------------------------------------
        # PAGES
        # ------------------------------------------------------

        try:

            self.pages_per_query = int(
                self.pages_per_query
            )

        except (
            TypeError,
            ValueError,
        ):

            raise ValueError(
                "pages_per_query must be an integer."
            )

        if self.pages_per_query < 1:

            raise ValueError(
                "pages_per_query must be greater than zero."
            )

        # ------------------------------------------------------
        # RESULTS
        # ------------------------------------------------------

        try:

            self.results_per_page = int(
                self.results_per_page
            )

        except (
            TypeError,
            ValueError,
        ):

            raise ValueError(
                "results_per_page must be an integer."
            )

        if self.results_per_page < 1:

            raise ValueError(
                "results_per_page must be greater than zero."
            )

        # ------------------------------------------------------
        # DELAY
        # ------------------------------------------------------

        try:

            self.delay = float(
                self.delay
            )

        except (
            TypeError,
            ValueError,
        ):

            raise ValueError(
                "delay must be a number."
            )

        if self.delay < 0:

            raise ValueError(
                "delay cannot be negative."
            )

        # ------------------------------------------------------
        # TIMEOUT
        # ------------------------------------------------------

        try:

            self.timeout = int(
                self.timeout
            )

        except (
            TypeError,
            ValueError,
        ):

            raise ValueError(
                "timeout must be an integer."
            )

        if self.timeout < 1:

            raise ValueError(
                "timeout must be greater than zero."
            )

        return True

    # ==========================================================
    # LOCATION
    # ==========================================================

    def location(self) -> str:
        """
        Return normalized human-readable location.

        Example:

            city = "Tabriz"
            province = "East Azerbaijan"

        returns:

            "Tabriz, East Azerbaijan"
        """

        parts: list[str] = []

        city = self.city.strip()

        province = self.province.strip()

        if city:

            parts.append(
                city
            )

        if province:

            parts.append(
                province
            )

        return ", ".join(
            parts
        )

    # ==========================================================
    # DESCRIPTION
    # ==========================================================

    def describe(self) -> str:
        """
        Return a human-readable description of this
        search configuration.
        """

        if self.keywords:

            if len(self.keywords) == 1:

                result = self.keywords[0]

            else:

                result = (
                    ", ".join(
                        self.keywords
                    )
                )

        else:

            result = ""

        location = self.location()

        if location:

            result += (
                f" - {location}"
            )

        if self.radius > 0:

            result += (
                f" - radius: "
                f"{self.radius:g} km"
            )

        return result

    # ==========================================================
    # DICT
    # ==========================================================

    def to_dict(self) -> dict:
        """
        Return a stable serializable representation.

        Both `keywords` and legacy `keyword` are exposed so
        external consumers and older components can continue
        reading the configuration.
        """

        return {

            "keywords":
                list(self.keywords),

            "keyword":
                self.keyword,

            "province":
                self.province,

            "city":
                self.city,

            "radius":
                self.radius,

            "provider":
                self.provider,

            "max_queries":
                self.max_queries,

            "pages_per_query":
                self.pages_per_query,

            "results_per_page":
                self.results_per_page,

            "delay":
                self.delay,

            "timeout":
                self.timeout,
        }

    # ==========================================================
    # REPRESENTATION
    # ==========================================================

    def __repr__(self) -> str:
        """
        Developer-friendly representation.
        """

        return (
            "SearchConfig("
            f"keywords={self.keywords!r}, "
            f"province={self.province!r}, "
            f"city={self.city!r}, "
            f"radius={self.radius!r}, "
            f"provider={self.provider!r}, "
            f"max_queries={self.max_queries!r}, "
            f"pages_per_query={self.pages_per_query!r}, "
            f"results_per_page={self.results_per_page!r}, "
            f"delay={self.delay!r}, "
            f"timeout={self.timeout!r}"
            ")"
        )