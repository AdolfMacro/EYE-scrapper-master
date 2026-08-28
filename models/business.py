# ==========================================================
# EYES MASTER — BUSINESS MODEL
# ==========================================================
#
# FILE:
#     models/business.py
#
# STATUS:
#     CANONICAL / CORE
#
# ROLE:
#     Canonical domain model for every entity discovered
#     by EYES.
#
# ARCHITECTURE:
#
#     Provider
#         │
#         ▼
#     Extractor
#         │
#         ▼
#     Business
#         │
#         ├── normalization
#         ├── validation
#         ├── identity
#         └── serialization
#         │
#         ▼
#     Database
#
# IMPORTANT:
#
#     Business is a DOMAIN MODEL.
#
#     It must NOT:
#         - access SQLite
#         - perform database queries
#         - know about providers
#         - control scraping
#         - manage workers
#         - contain GUI logic
#
# CORE PERSISTENCE RULE:
#
#     A Business is persistable only when:
#
#         name
#         latitude
#         longitude
#
#     are valid.
#
# ==========================================================

from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
)
from math import isfinite
from typing import Any, Optional


@dataclass
class Business:
    """
    Canonical domain model for an EYES business/entity.

    The model is intentionally provider-independent.

    Examples:

        school
        restaurant
        hotel
        pharmacy
        company
        shop
        office
        hospital
        service
        etc.

    Provider-specific information should remain outside
    this model unless it represents canonical entity data.
    """

    # ======================================================
    # IDENTITY
    # ======================================================

    name: str = ""

    # ======================================================
    # CLASSIFICATION
    # ======================================================

    category: str = ""

    keyword: str = ""

    # ======================================================
    # LOCATION
    # ======================================================

    province: str = ""

    city: str = ""

    address: str = ""

    neighborhood: str = ""

    street: str = ""

    # ======================================================
    # CONTACT
    # ======================================================

    phone: str = ""

    website: str = ""

    # ======================================================
    # SOURCE
    # ======================================================

    url: str = ""

    source_url: str = ""

    source: str = ""

    source_id: Optional[str] = None

    # ======================================================
    # GEOLOCATION
    # ======================================================

    latitude: Optional[float] = None

    longitude: Optional[float] = None

    distance_km: Optional[float] = None

    # ======================================================
    # NORMALIZATION
    # ======================================================

    def __post_init__(self) -> None:
        """
        Normalize incoming values immediately after object
        construction.

        The model performs only local normalization.

        Database-specific normalization belongs to the
        database layer.
        """

        # --------------------------------------------------
        # TEXT
        # --------------------------------------------------

        self.name = self.clean_text(
            self.name
        )

        self.category = self.clean_text(
            self.category
        )

        self.keyword = self.clean_text(
            self.keyword
        )

        self.province = self.clean_text(
            self.province
        )

        self.city = self.clean_text(
            self.city
        )

        self.address = self.clean_text(
            self.address
        )

        self.neighborhood = self.clean_text(
            self.neighborhood
        )

        self.street = self.clean_text(
            self.street
        )

        self.phone = self.clean_text(
            self.phone
        )

        self.website = self.clean_text(
            self.website
        )

        self.url = self.clean_text(
            self.url
        )

        self.source_url = self.clean_text(
            self.source_url
        )

        self.source = self.clean_text(
            self.source
        )

        # --------------------------------------------------
        # SOURCE ID
        # --------------------------------------------------

        if self.source_id is not None:

            self.source_id = (
                self.clean_text(
                    self.source_id
                )
                or None
            )

        # --------------------------------------------------
        # NUMERIC VALUES
        # --------------------------------------------------

        self.latitude = self.to_float(
            self.latitude
        )

        self.longitude = self.to_float(
            self.longitude
        )

        self.distance_km = self.to_float(
            self.distance_km
        )

    # ======================================================
    # TEXT
    # ======================================================

    @staticmethod
    def clean_text(
        value: Any,
    ) -> str:
        """
        Convert arbitrary input into normalized text.

        Examples:

            None
                -> ""

            "  Tehran   "
                -> "Tehran"

            "A   B   C"
                -> "A B C"
        """

        if value is None:

            return ""

        return " ".join(
            str(value)
            .strip()
            .split()
        )

    # ======================================================
    # FLOAT
    # ======================================================

    @staticmethod
    def to_float(
        value: Any,
    ) -> Optional[float]:
        """
        Convert a value into a finite float.

        Invalid numeric values become None.

        Examples:

            "35.7219"
                -> 35.7219

            ""
                -> None

            "invalid"
                -> None

            NaN
                -> None

            Infinity
                -> None
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

        if not isfinite(
            result
        ):

            return None

        return result

    # ======================================================
    # COORDINATES
    # ======================================================

    def has_coordinates(self) -> bool:
        """
        Return True when both geographic coordinates are
        present and within valid geographic ranges.

        Latitude:

            -90 <= latitude <= 90

        Longitude:

            -180 <= longitude <= 180
        """

        if (
            self.latitude is None
            or self.longitude is None
        ):

            return False

        if not (
            -90.0
            <= self.latitude
            <= 90.0
        ):

            return False

        if not (
            -180.0
            <= self.longitude
            <= 180.0
        ):

            return False

        return True

    # ======================================================
    # PERSISTENCE
    # ======================================================

    def is_persistable(self) -> bool:
        """
        Return True when this Business satisfies the
        canonical persistence requirements.

        Required:

            1. name
            2. valid latitude
            3. valid longitude
        """

        if not self.name:

            return False

        return self.has_coordinates()

    # ======================================================
    # VALIDATION
    # ======================================================

    def validation_errors(self) -> list[str]:
        """
        Return all domain validation errors.

        This method does not raise exceptions.

        Example:

            [
                "NAME_REQUIRED",
                "COORDINATES_REQUIRED"
            ]
        """

        errors: list[str] = []

        # --------------------------------------------------
        # NAME
        # --------------------------------------------------

        if not self.name:

            errors.append(
                "NAME_REQUIRED"
            )

        # --------------------------------------------------
        # COORDINATES
        # --------------------------------------------------

        if (
            self.latitude is None
            or self.longitude is None
        ):

            errors.append(
                "COORDINATES_REQUIRED"
            )

        elif not self.has_coordinates():

            errors.append(
                "INVALID_COORDINATES"
            )

        return errors

    # ======================================================
    # IDENTITY
    # ======================================================

    def key(self) -> str:
        """
        Generate a stable domain identity key.

        Priority:

            1. source + source_id
            2. canonical business identity

        Important:

            This key is NOT the database duplicate detector.

            Database-level duplicate detection belongs to
            database/database.py.
        """

        # --------------------------------------------------
        # PROVIDER IDENTITY
        # --------------------------------------------------

        if (
            self.source
            and self.source_id
        ):

            return (
                f"{self.source}:"
                f"{self.source_id}"
            ).casefold()

        # --------------------------------------------------
        # CANONICAL FALLBACK
        # --------------------------------------------------

        parts = (
            self.name,
            self.city,
            self.province,
            self.address,
        )

        normalized: list[str] = []

        for value in parts:

            value = self.clean_text(
                value
            )

            if value:

                normalized.append(
                    value.casefold()
                )

        return "|".join(
            normalized
        )

    # ======================================================
    # SERIALIZATION
    # ======================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Convert the Business into a plain dictionary.

        Suitable for:

            JSON
            SQLite adapters
            APIs
            logging
            debugging
        """

        return asdict(
            self
        )

    # ======================================================
    # DESERIALIZATION
    # ======================================================

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "Business":
        """
        Construct a Business from a dictionary.

        Supports the old `title` field for backward
        compatibility with legacy EYES data.
        """

        if not isinstance(
            data,
            dict,
        ):

            raise TypeError(
                "Business data must be a dictionary."
            )

        normalized = dict(
            data
        )

        # --------------------------------------------------
        # LEGACY TITLE → NAME
        # --------------------------------------------------

        if (
            not normalized.get("name")
            and normalized.get("title")
        ):

            normalized["name"] = (
                normalized["title"]
            )

        return cls(
            name=normalized.get(
                "name",
                "",
            ),

            category=normalized.get(
                "category",
                "",
            ),

            keyword=normalized.get(
                "keyword",
                "",
            ),

            province=normalized.get(
                "province",
                "",
            ),

            city=normalized.get(
                "city",
                "",
            ),

            address=normalized.get(
                "address",
                "",
            ),

            neighborhood=normalized.get(
                "neighborhood",
                "",
            ),

            street=normalized.get(
                "street",
                "",
            ),

            phone=normalized.get(
                "phone",
                "",
            ),

            website=normalized.get(
                "website",
                "",
            ),

            url=normalized.get(
                "url",
                "",
            ),

            source_url=normalized.get(
                "source_url",
                "",
            ),

            source=normalized.get(
                "source",
                "",
            ),

            source_id=normalized.get(
                "source_id"
            ),

            latitude=normalized.get(
                "latitude"
            ),

            longitude=normalized.get(
                "longitude"
            ),

            distance_km=normalized.get(
                "distance_km"
            ),
        )

    # ======================================================
    # COPY
    # ======================================================

    def copy(
        self,
    ) -> "Business":
        """
        Return an independent Business instance.
        """

        return type(self).from_dict(
            self.to_dict()
        )

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
            "Business("
            f"name={self.name!r}, "
            f"category={self.category!r}, "
            f"city={self.city!r}, "
            f"province={self.province!r}, "
            f"latitude={self.latitude!r}, "
            f"longitude={self.longitude!r}, "
            f"source={self.source!r}"
            ")"
        )