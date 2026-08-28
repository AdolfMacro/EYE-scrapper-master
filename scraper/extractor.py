# ==========================================================
# EYES MASTER — EXTRACTOR / NORMALIZER
# ==========================================================
#
# FILE:
#     scraper/extractor.py
#
# STATUS:
#     CANONICAL / CORE
#
# ROLE:
#     Provider Result → Canonical Business Mapper
#
# ARCHITECTURE:
#
#     Provider
#         │
#         ▼
#     Raw Result
#         │
#         ▼
#     BusinessExtractor
#         │
#         ▼
#     Business
#         │
#         ▼
#     Database
#
# RESPONSIBILITIES
# ----------------------------------------------------------
# 1. دریافت Raw Result از Provider
# 2. استخراج نام Canonical
# 3. استخراج Classification
# 4. استخراج Location
# 5. استخراج Contact
# 6. استخراج Source Metadata
# 7. استخراج Geolocation
# 8. ساخت Canonical Business
# 9. حذف ورودی‌های نامعتبر
# 10. تبدیل مجموعه Raw Results به Business[]
#
# DOES NOT
# ----------------------------------------------------------
# ❌ Database
# ❌ Deduplication
# ❌ ProviderManager
# ❌ Query generation
# ❌ Keyword generation
# ❌ City management
# ❌ Job management
# ❌ Pipeline orchestration
# ❌ Runtime management
# ❌ Process management
# ❌ GUI
#
# CORE RULE
# ----------------------------------------------------------
#
#     Provider
#         ↓
#     Raw Dictionary
#         ↓
#     BusinessExtractor
#         ↓
#     Business
#         ↓
#     Database
#
# IMPORTANT
# ----------------------------------------------------------
#
# EYES is NOT school-specific.
#
# The canonical entity is Business.
#
# Examples:
#
#     restaurant
#     hotel
#     school
#     pharmacy
#     company
#     shop
#     hospital
#     office
#     service
#
# ==========================================================

from __future__ import annotations

from typing import Any, Iterable, Optional

from models.business import Business

from tools.phone import (
    extract_phone,
    normalize_phone,
)


class BusinessExtractor:
    """
    Convert provider raw dictionaries into canonical
    Business models.

    This class represents the normalization boundary
    between Providers and the canonical EYES data model.

    Provider-specific structures are intentionally isolated
    here and are converted into the generic Business model.

    The extractor does not know about:

        Database
        ProviderManager
        ScraperEngine
        SearchJob
        GUI
        Process management

    It only performs:

        Raw Result
            ↓
        Canonical Business
    """

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(
        self,
        keyword: str = "",
        province: str = "",
        city: str = "",
    ) -> None:

        self.keyword = self.clean_text(
            keyword
        )

        self.province = self.clean_text(
            province
        )

        self.city = self.clean_text(
            city
        )

    # ==========================================================
    # TEXT
    # ==========================================================

    @staticmethod
    def clean_text(
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
    # NAME
    # ==========================================================

    def extract_name(
        self,
        item: dict[str, Any],
    ) -> str:
        """
        Extract canonical Business name.

        Priority:

            1. name
            2. title
            3. keyword fallback
        """

        name = self.clean_text(
            item.get("name")
        )

        if name:
            return name

        title = self.clean_text(
            item.get("title")
        )

        if title:

            if "," in title:

                first_part = (
                    title.split(
                        ",",
                        1,
                    )[0]
                )

                first_part = self.clean_text(
                    first_part
                )

                if first_part:
                    return first_part

            return title

        return self.keyword

    # ==========================================================
    # CATEGORY
    # ==========================================================

    def extract_category(
        self,
        item: dict[str, Any],
    ) -> str:
        """
        Extract canonical business category.

        Provider-specific semantic fields are accepted
        only as input to the canonical category field.
        """

        category = self.clean_text(
            item.get("category")
        )

        if category:
            return category

        semantic_type = self.clean_text(
            item.get("semantic_type")
        )

        if semantic_type:
            return semantic_type

        return self.keyword

    # ==========================================================
    # KEYWORD
    # ==========================================================

    def extract_keyword(
        self,
        item: dict[str, Any],
    ) -> str:
        """
        Extract search keyword associated with the result.
        """

        return self.clean_text(
            item.get("keyword")
            or self.keyword
        )

    # ==========================================================
    # PROVINCE
    # ==========================================================

    def extract_province(
        self,
        item: dict[str, Any],
    ) -> str:
        """
        Extract province.
        """

        return self.clean_text(
            item.get("province")
            or self.province
        )

    # ==========================================================
    # CITY
    # ==========================================================

    def extract_city(
        self,
        item: dict[str, Any],
    ) -> str:
        """
        Extract city.
        """

        return self.clean_text(
            item.get("city")
            or self.city
        )

    # ==========================================================
    # ADDRESS
    # ==========================================================

    def extract_address(
        self,
        item: dict[str, Any],
    ) -> str:
        """
        Extract canonical address.

        Fallbacks:

            address
            snippet
            description
        """

        address = self.clean_text(
            item.get("address")
        )

        if address:
            return address

        snippet = self.clean_text(
            item.get("snippet")
        )

        if snippet:
            return snippet

        description = self.clean_text(
            item.get("description")
        )

        return description

    # ==========================================================
    # NEIGHBORHOOD
    # ==========================================================

    def extract_neighborhood(
        self,
        item: dict[str, Any],
    ) -> str:
        """
        Extract neighborhood.
        """

        return self.clean_text(
            item.get("neighborhood")
        )

    # ==========================================================
    # STREET
    # ==========================================================

    def extract_street(
        self,
        item: dict[str, Any],
    ) -> str:
        """
        Extract street.
        """

        return self.clean_text(
            item.get("street")
        )

    # ==========================================================
    # PHONE
    # ==========================================================

    def extract_phone(
        self,
        item: dict[str, Any],
    ) -> str:
        """
        Extract and normalize Business phone number.

        Provider supplied phone numbers have priority.

        If unavailable, common textual fields are searched
        for a phone number.
        """

        provider_phone = self.clean_text(
            item.get("phone")
        )

        if provider_phone:

            try:

                normalized = normalize_phone(
                    provider_phone
                )

            except Exception:

                normalized = ""

            if normalized:
                return normalized

        fields = (
            item.get("phone", ""),
            item.get("title", ""),
            item.get("name", ""),
            item.get("address", ""),
            item.get("neighborhood", ""),
            item.get("street", ""),
            item.get("snippet", ""),
            item.get("description", ""),
        )

        combined = " ".join(
            self.clean_text(value)
            for value in fields
            if value is not None
        )

        if not combined:
            return ""

        try:

            phone = extract_phone(
                combined
            )

        except Exception:

            return ""

        if not phone:
            return ""

        try:

            return (
                normalize_phone(
                    phone
                )
                or ""
            )

        except Exception:

            return self.clean_text(
                phone
            )

    # ==========================================================
    # WEBSITE
    # ==========================================================

    def extract_website(
        self,
        item: dict[str, Any],
    ) -> str:
        """
        Extract Business website.
        """

        return self.clean_text(
            item.get("website")
        )

    # ==========================================================
    # SOURCE
    # ==========================================================

    def extract_source(
        self,
        item: dict[str, Any],
        source: str = "",
    ) -> str:
        """
        Extract Provider source identifier.
        """

        return self.clean_text(
            item.get("source")
            or source
        )

    # ==========================================================
    # SOURCE ID
    # ==========================================================

    def extract_source_id(
        self,
        item: dict[str, Any],
    ) -> Optional[str]:
        """
        Extract Provider-specific source identity.
        """

        value = item.get(
            "source_id"
        )

        if value is None:
            return None

        value = self.clean_text(
            value
        )

        return value or None

    # ==========================================================
    # URL
    # ==========================================================

    def extract_url(
        self,
        item: dict[str, Any],
    ) -> str:
        """
        Extract result URL.
        """

        return self.clean_text(
            item.get("url")
        )

    # ==========================================================
    # SOURCE URL
    # ==========================================================

    def extract_source_url(
        self,
        item: dict[str, Any],
    ) -> str:
        """
        Extract original Provider source URL.
        """

        return self.clean_text(
            item.get("source_url")
        )

    # ==========================================================
    # FLOAT
    # ==========================================================

    @staticmethod
    def to_float(
        value: Any,
    ) -> Optional[float]:
        """
        Safely convert a value into a finite float.
        """

        if value is None:
            return None

        if value == "":
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

    # ==========================================================
    # LATITUDE
    # ==========================================================

    def extract_latitude(
        self,
        item: dict[str, Any],
    ) -> Optional[float]:
        """
        Extract latitude.
        """

        return self.to_float(
            item.get("latitude")
        )

    # ==========================================================
    # LONGITUDE
    # ==========================================================

    def extract_longitude(
        self,
        item: dict[str, Any],
    ) -> Optional[float]:
        """
        Extract longitude.
        """

        return self.to_float(
            item.get("longitude")
        )

    # ==========================================================
    # DISTANCE
    # ==========================================================

    def extract_distance(
        self,
        item: dict[str, Any],
    ) -> Optional[float]:
        """
        Extract distance from search origin.
        """

        return self.to_float(
            item.get("distance_km")
        )

    # ==========================================================
    # MAIN EXTRACTION
    # ==========================================================

    def extract(
        self,
        item: Any,
        source: str = "",
    ) -> Optional[Business]:
        """
        Convert one Provider result into a Business.

        Invalid/non-dictionary results are ignored.

        The extractor validates the canonical identity
        at the model boundary.

        Database persistence validation remains the
        responsibility of Database.
        """

        if not isinstance(
            item,
            dict,
        ):
            return None

        name = self.extract_name(
            item
        )

        if not name:
            return None

        return Business(

            # --------------------------------------------------
            # IDENTITY
            # --------------------------------------------------

            name=name,

            # --------------------------------------------------
            # CLASSIFICATION
            # --------------------------------------------------

            category=self.extract_category(
                item
            ),

            keyword=self.extract_keyword(
                item
            ),

            # --------------------------------------------------
            # LOCATION
            # --------------------------------------------------

            province=self.extract_province(
                item
            ),

            city=self.extract_city(
                item
            ),

            address=self.extract_address(
                item
            ),

            neighborhood=self.extract_neighborhood(
                item
            ),

            street=self.extract_street(
                item
            ),

            # --------------------------------------------------
            # CONTACT
            # --------------------------------------------------

            phone=self.extract_phone(
                item
            ),

            website=self.extract_website(
                item
            ),

            # --------------------------------------------------
            # SOURCE
            # --------------------------------------------------

            url=self.extract_url(
                item
            ),

            source_url=self.extract_source_url(
                item
            ),

            source=self.extract_source(
                item,
                source,
            ),

            source_id=self.extract_source_id(
                item
            ),

            # --------------------------------------------------
            # GEOLOCATION
            # --------------------------------------------------

            latitude=self.extract_latitude(
                item
            ),

            longitude=self.extract_longitude(
                item
            ),

            distance_km=self.extract_distance(
                item
            ),
        )

    # ==========================================================
    # MANY
    # ==========================================================

    def extract_many(
        self,
        items: Iterable[Any],
        source: str = "",
    ) -> list[Business]:
        """
        Convert multiple Provider results into
        canonical Business objects.

        Invalid results are silently skipped.
        """

        results: list[Business] = []

        if items is None:
            return results

        for item in items:

            business = self.extract(
                item,
                source=source,
            )

            if business is not None:

                results.append(
                    business
                )

        return results

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
            f"<BusinessExtractor "
            f"keyword={self.keyword!r} "
            f"city={self.city!r} "
            f"province={self.province!r}>"
        )