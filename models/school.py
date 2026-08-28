from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional


@dataclass
class School:
    """
    Canonical school data model.

    This model represents normalized school/entity data
    extracted from different providers.

    Provider-specific metadata should remain outside this
    model unless it is part of the canonical school record.
    """

    # ==========================================================
    # IDENTITY
    # ==========================================================

    name: str = ""

    # ==========================================================
    # CLASSIFICATION
    # ==========================================================

    category: str = ""

    keyword: str = ""

    # ==========================================================
    # LOCATION
    # ==========================================================

    province: str = ""

    city: str = ""

    address: str = ""

    neighborhood: str = ""

    street: str = ""

    # ==========================================================
    # CONTACT
    # ==========================================================

    phone: str = ""

    website: str = ""

    # ==========================================================
    # SOURCE
    # ==========================================================

    url: str = ""

    source_url: str = ""

    source: str = ""

    source_id: Optional[str] = None

    # ==========================================================
    # GEOLOCATION
    # ==========================================================

    latitude: Optional[float] = None

    longitude: Optional[float] = None

    distance_km: Optional[float] = None

    # ==========================================================
    # NORMALIZATION
    # ==========================================================

    def __post_init__(self) -> None:

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

        if self.source_id is not None:

            self.source_id = str(
                self.source_id
            ).strip()

        self.latitude = self.to_float(
            self.latitude
        )

        self.longitude = self.to_float(
            self.longitude
        )

        self.distance_km = self.to_float(
            self.distance_km
        )

    # ==========================================================
    # TEXT
    # ==========================================================

    @staticmethod
    def clean_text(
        value: Any,
    ) -> str:

        if value is None:
            return ""

        return " ".join(
            str(value).strip().split()
        )

    # ==========================================================
    # FLOAT
    # ==========================================================

    @staticmethod
    def to_float(
        value: Any,
    ) -> Optional[float]:

        if value is None:
            return None

        if value == "":
            return None

        try:

            return float(value)

        except (
            TypeError,
            ValueError,
        ):

            return None
        # ==========================================================
    # IDENTITY KEY
    # ==========================================================

    def key(self) -> str:
        """
        Return a stable identity key for persistence
        and duplicate detection.

        Provider-specific identity is preferred when
        source_id is available. Otherwise, a canonical
        fallback is generated from normalized fields.
        """

        if self.source_id:

            return (
                f"{self.source}:"
                f"{self.source_id}"
            ).casefold()

        parts = [
            self.name,
            self.city,
            self.province,
            self.address,
            self.source,
        ]

        normalized = [
            self.clean_text(
                value
            ).casefold()
            for value in parts
            if self.clean_text(value)
        ]

        return "|".join(
            normalized
        )
    # ==========================================================
    # SERIALIZATION
    # ==========================================================

    def to_dict(self) -> dict[str, Any]:

        return asdict(self)

    # ==========================================================
    # DESERIALIZATION
    # ==========================================================

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "School":

        if not isinstance(
            data,
            dict,
        ):

            raise TypeError(
                "School data must be a dictionary."
            )

        return cls(
            name=data.get(
                "name",
                "",
            ),

            category=data.get(
                "category",
                "",
            ),

            keyword=data.get(
                "keyword",
                "",
            ),

            province=data.get(
                "province",
                "",
            ),

            city=data.get(
                "city",
                "",
            ),

            address=data.get(
                "address",
                "",
            ),

            neighborhood=data.get(
                "neighborhood",
                "",
            ),

            street=data.get(
                "street",
                "",
            ),

            phone=data.get(
                "phone",
                "",
            ),

            website=data.get(
                "website",
                "",
            ),

            url=data.get(
                "url",
                "",
            ),

            source_url=data.get(
                "source_url",
                "",
            ),

            source=data.get(
                "source",
                "",
            ),

            source_id=data.get(
                "source_id"
            ),

            latitude=data.get(
                "latitude"
            ),

            longitude=data.get(
                "longitude"
            ),

            distance_km=data.get(
                "distance_km"
            ),
        )

    # ==========================================================
    # COPY
    # ==========================================================

    def copy(self) -> "School":

        return School.from_dict(
            self.to_dict()
        )

    # ==========================================================
    # REPRESENTATION
    # ==========================================================

    def __repr__(self) -> str:

        return (
            "School("
            f"name={self.name!r}, "
            f"city={self.city!r}, "
            f"province={self.province!r}, "
            f"source={self.source!r}"
            ")"
        )
