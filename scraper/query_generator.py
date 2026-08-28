# ==========================================================
# EYES MASTER — QUERY GENERATOR
# ==========================================================
#
# FILE:
#     scraper/query_generator.py
#
# STATUS:
#     CANONICAL / CORE
#
# ROLE:
#     Deterministic Search Query Generator
#
# RESPONSIBILITIES
# ----------------------------------------------------------
# 1. دریافت SearchConfig
# 2. پشتیبانی از keyword و keywords
# 3. ساخت Queryهای deterministic
# 4. ترکیب Keyword و Location
# 5. ساخت Search Variations
# 6. ساخت Radius Queries
# 7. حذف Queryهای تکراری
# 8. حفظ ترتیب اولویت
# 9. اعمال max_queries
#
# MAP SEARCH STRATEGY
# ----------------------------------------------------------
# این Generator برای Providerهای جستجوی مکانی نیز بهینه شده
# است؛ بنابراین Queryها باید تا حد ممکن semantic و location-aware
# باشند.
#
# اولویت اصلی:
#
#     1. Keyword + City + Province
#     2. Keyword + City
#     3. Keyword در City
#     4. Keyword نزدیک City
#     5. Keyword اطراف City
#     6. Keyword + Province
#     7. Radius Queries
#
# Queryهایی مانند:
#
#     "شماره تماس"
#     "تلفن"
#     "سایت"
#     "اطلاعات تماس"
#
# عمداً برای Map Search تولید نمی‌شوند؛ زیرا این اطلاعات باید
# از رکورد Business/Place توسط Provider یا Extractor استخراج شود.
#
# KEYWORD CONTRACT
# ----------------------------------------------------------
#
# Canonical:
#
#     keywords -> list[str]
#
# Backward compatibility:
#
#     keyword -> str
#
# اگر هر دو وجود داشته باشند:
#
#     keywords اولویت دارد.
#
# اگر keywords وجود نداشته باشد:
#
#     keyword به‌عنوان یک keyword منفرد استفاده می‌شود.
#
# QueryGenerator خودش keyword را به‌صورت پیش‌فرض
# جعل نمی‌کند و keyword خالی را معتبر نمی‌داند.
#
# DOES NOT
# ----------------------------------------------------------
# ❌ Provider
# ❌ ProviderManager
# ❌ Database
# ❌ Business Model
# ❌ Business Extraction
# ❌ Deduplication of Businesses
# ❌ Job Execution
# ❌ Network Requests
# ❌ GUI
# ❌ Process Management
#
# CORE RULE
# ----------------------------------------------------------
#
#     Same Config
#         +
#     Same Generator
#         =
#     Same Query Order
#
# ==========================================================

from __future__ import annotations

from typing import Any

from config.search import SearchConfig


class QueryGenerator:
    """
    Generate deterministic search queries from SearchConfig.

    The generator is provider-independent but optimized for
    location-aware discovery, especially map-oriented
    providers such as Neshan, Google Maps and OSM-based
    search providers.

    Keyword compatibility:

        keywords -> canonical multi-keyword input
        keyword  -> backward-compatible single keyword input

    When both are present, ``keywords`` has priority.
    """

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(
        self,
        config: SearchConfig,
    ) -> None:

        if not isinstance(
            config,
            SearchConfig,
        ):
            raise TypeError(
                "QueryGenerator requires "
                "a SearchConfig instance."
            )

        self.config = config

        self._validate_keyword_contract()

    # ==========================================================
    # TEXT NORMALIZATION
    # ==========================================================

    @staticmethod
    def _clean(
        value: Any,
    ) -> str:
        """
        Normalize arbitrary values into clean text.
        """

        if value is None:
            return ""

        return " ".join(
            str(value)
            .strip()
            .split()
        )

    # ==========================================================
    # KEYWORD NORMALIZATION
    # ==========================================================

    @classmethod
    def _normalize_keywords(
        cls,
        value: Any,
    ) -> list[str]:
        """
        Normalize a keyword collection.

        Supported inputs:

            None
            str
            list
            tuple
            set
            other iterables

        Empty values are removed.

        Duplicate keywords are removed case-insensitively
        while preserving their first occurrence.
        """

        if value is None:
            return []

        if isinstance(
            value,
            str,
        ):
            values = [
                value
            ]

        else:

            try:

                values = list(
                    value
                )

            except TypeError:

                values = [
                    value
                ]

        result: list[str] = []

        seen: set[str] = set()

        for item in values:

            keyword = cls._clean(
                item
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
    # KEYWORD CONTRACT VALIDATION
    # ==========================================================

    def _validate_keyword_contract(
        self,
    ) -> None:
        """
        Validate that at least one keyword is available.

        ``keywords`` is the canonical field.

        ``keyword`` remains supported for compatibility with
        older SearchConfig implementations.
        """

        keywords = self._configured_keywords()

        if not keywords:

            raise ValueError(
                "Scraper keyword is required."
            )

    # ==========================================================
    # CONFIGURED KEYWORDS
    # ==========================================================

    def _configured_keywords(
        self,
    ) -> list[str]:
        """
        Return configured keywords.

        Priority:

            1. config.keywords
            2. config.keyword
        """

        configured_keywords = getattr(
            self.config,
            "keywords",
            None,
        )

        keywords = self._normalize_keywords(
            configured_keywords
        )

        if keywords:

            return keywords

        legacy_keyword = getattr(
            self.config,
            "keyword",
            None,
        )

        return self._normalize_keywords(
            legacy_keyword
        )

    # ==========================================================
    # KEYWORDS
    # ==========================================================

    def keywords(
        self,
    ) -> list[str]:
        """
        Return normalized configured keywords.
        """

        return list(
            self._configured_keywords()
        )

    # ==========================================================
    # KEYWORD
    # ==========================================================

    def keyword(
        self,
    ) -> str:
        """
        Return the first configured keyword.

        Backward compatibility method.
        """

        keywords = self.keywords()

        if not keywords:
            return ""

        return keywords[0]

    # ==========================================================
    # MAX QUERIES
    # ==========================================================

    def max_queries(
        self,
    ) -> int:
        """
        Return configured maximum query count.
        """

        try:

            value = int(
                getattr(
                    self.config,
                    "max_queries",
                    1,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            value = 1

        return max(
            1,
            value,
        )

    # ==========================================================
    # PROVINCE
    # ==========================================================

    def province(
        self,
    ) -> str:
        """
        Return normalized province.
        """

        return self._clean(
            getattr(
                self.config,
                "province",
                "",
            )
        )

    # ==========================================================
    # CITY
    # ==========================================================

    def city(
        self,
    ) -> str:
        """
        Return normalized city.
        """

        return self._clean(
            getattr(
                self.config,
                "city",
                "",
            )
        )

    # ==========================================================
    # RADIUS
    # ==========================================================

    def radius(
        self,
    ) -> float:
        """
        Return normalized search radius.

        Invalid or non-positive values become 0.
        """

        value = getattr(
            self.config,
            "radius",
            0,
        )

        try:

            value = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return 0.0

        if value <= 0:

            return 0.0

        return value

    # ==========================================================
    # LOCATION QUERIES
    # ==========================================================

    def location_queries(
        self,
    ) -> list[str]:
        """
        Generate high-priority location-aware queries.

        Designed primarily for map/place discovery.

        Priority per keyword:

            1. keyword + city + province
            2. keyword + city
            3. keyword در city
            4. keyword نزدیک city
            5. keyword اطراف city
            6. keyword + province
            7. keyword

        The most geographically specific query is placed first.
        """

        keywords = self.keywords()

        province = self.province()

        city = self.city()

        if not keywords:
            return []

        queries: list[str] = []

        for keyword in keywords:

            # --------------------------------------------------
            # CITY + PROVINCE
            # --------------------------------------------------

            if city and province:

                queries.append(
                    f"{keyword} {city} {province}"
                )

            # --------------------------------------------------
            # CITY
            # --------------------------------------------------

            if city:

                queries.append(
                    f"{keyword} {city}"
                )

                queries.append(
                    f"{keyword} در {city}"
                )

                queries.append(
                    f"{keyword} نزدیک {city}"
                )

                queries.append(
                    f"{keyword} اطراف {city}"
                )

            # --------------------------------------------------
            # PROVINCE
            # --------------------------------------------------

            if province:

                queries.append(
                    f"{keyword} {province}"
                )

            # --------------------------------------------------
            # BASE
            # --------------------------------------------------

            queries.append(
                keyword
            )

        return queries

    # ==========================================================
    # SEARCH VARIATIONS
    # ==========================================================

    def search_variations(
        self,
    ) -> list[str]:
        """
        Generate semantic variations suitable for place
        and business discovery.

        Unlike the previous implementation, this method does
        not generate contact-oriented queries such as:

            شماره تماس
            تلفن
            سایت
            اطلاعات تماس
            آدرس

        Those fields belong to the returned place/business
        record and should be extracted from provider results.

        Map-oriented semantic variations:

            در شهر
            نزدیک شهر
            اطراف شهر
            محدوده شهر
            مرکز شهر
        """

        keywords = self.keywords()

        province = self.province()

        city = self.city()

        if not keywords:
            return []

        queries: list[str] = []

        for keyword in keywords:

            if city:

                queries.extend(
                    (
                        f"{keyword} در {city}",

                        f"{keyword} نزدیک {city}",

                        f"{keyword} اطراف {city}",

                        f"{keyword} محدوده {city}",

                        f"{keyword} مرکز {city}",
                    )
                )

            if province:

                queries.extend(
                    (
                        f"{keyword} در {province}",

                        f"{keyword} اطراف {province}",
                    )
                )

        return queries

    # ==========================================================
    # RADIUS QUERIES
    # ==========================================================

    def radius_queries(
        self,
    ) -> list[str]:
        """
        Generate radius-aware semantic queries.

        Radius queries are intentionally placed after the
        direct city/location queries because map providers
        generally perform better when given the canonical
        place + city query first.

        Required:

            keyword
            city
            positive radius
        """

        keywords = self.keywords()

        city = self.city()

        radius = self.radius()

        if (
            not keywords
            or not city
            or radius <= 0
        ):
            return []

        radius_text = f"{radius:g}"

        queries: list[str] = []

        for keyword in keywords:

            queries.extend(
                (
                    (
                        f"{keyword} نزدیک "
                        f"{city} "
                        f"{radius_text} کیلومتر"
                    ),

                    (
                        f"{keyword} اطراف "
                        f"{city} "
                        f"{radius_text} کیلومتر"
                    ),

                    (
                        f"{keyword} در محدوده "
                        f"{city} "
                        f"{radius_text} کیلومتر"
                    ),

                    (
                        f"{keyword} در شعاع "
                        f"{radius_text} کیلومتری "
                        f"{city}"
                    ),
                )
            )

        return queries

    # ==========================================================
    # UNIQUE
    # ==========================================================

    @classmethod
    def unique(
        cls,
        queries,
    ) -> list[str]:
        """
        Remove duplicate queries while preserving order.

        Comparison is case-insensitive.
        """

        if not queries:
            return []

        result: list[str] = []

        seen: set[str] = set()

        for query in queries:

            query = cls._clean(
                query
            )

            if not query:
                continue

            normalized = query.casefold()

            if normalized in seen:
                continue

            seen.add(
                normalized
            )

            result.append(
                query
            )

        return result

    # ==========================================================
    # GENERATE
    # ==========================================================

    def generate(
        self,
    ) -> list[str]:
        """
        Generate the final deterministic query list.

        Priority:

            1. Location queries
            2. Search variations
            3. Radius queries

        Duplicates are removed before max_queries is applied.
        """

        queries: list[str] = []

        # ------------------------------------------------------
        # PRIORITY 1
        # ------------------------------------------------------

        queries.extend(
            self.location_queries()
        )

        # ------------------------------------------------------
        # PRIORITY 2
        # ------------------------------------------------------

        queries.extend(
            self.search_variations()
        )

        # ------------------------------------------------------
        # PRIORITY 3
        # ------------------------------------------------------

        queries.extend(
            self.radius_queries()
        )

        # ------------------------------------------------------
        # UNIQUE
        # ------------------------------------------------------

        queries = self.unique(
            queries
        )

        # ------------------------------------------------------
        # LIMIT
        # ------------------------------------------------------

        return queries[
            :self.max_queries()
        ]

    # ==========================================================
    # COUNT
    # ==========================================================

    def count(
        self,
    ) -> int:
        """
        Return number of generated queries.
        """

        return len(
            self.generate()
        )

    # ==========================================================
    # PREVIEW
    # ==========================================================

    def preview(
        self,
    ) -> list[str]:
        """
        Print and return generated queries.

        Developer convenience only.
        """

        queries = self.generate()

        print(
            "=" * 60
        )

        print(
            "EYES MASTER — QUERY GENERATOR"
        )

        print(
            "=" * 60
        )

        print(
            "Keywords          : "
            f"{self.keywords()}"
        )

        print(
            "Province          : "
            f"{self.province() or '-'}"
        )

        print(
            "City              : "
            f"{self.city() or '-'}"
        )

        print(
            "Radius            : "
            f"{self.radius():g}"
        )

        print(
            f"Generated queries : {len(queries)}"
        )

        print(
            "Configured maximum: "
            f"{self.max_queries()}"
        )

        print(
            "=" * 60
        )

        for index, query in enumerate(
            queries,
            start=1,
        ):

            print(
                f"[{index:02d}] {query}"
            )

        print(
            "=" * 60
        )

        return queries

    # ==========================================================
    # REPRESENTATION
    # ==========================================================

    def __repr__(
        self,
    ) -> str:
        """
        Developer-friendly representation.
        """

        return (
            "QueryGenerator("
            f"keywords={self.keywords()!r}, "
            f"province={self.province()!r}, "
            f"city={self.city()!r}, "
            f"radius={self.radius()!r}, "
            f"max_queries={self.max_queries()!r}"
            ")"
        )