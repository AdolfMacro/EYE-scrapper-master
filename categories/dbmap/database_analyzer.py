# ==========================================================
# EYES DB MAP / DATA MANAGER
# DATABASE ANALYZER
# ==========================================================
#
# FILE:
#     dbmap/database_analyzer.py
#
# STATUS:
#     CANONICAL / CORE
#
# ROLE:
#     Read-only SQLite database analysis engine.
#
# RESPONSIBILITIES
# ----------------------------------------------------------
# - Database schema inspection
# - Table discovery
# - Column discovery
# - Type analysis
# - Row statistics
# - NULL / empty detection
# - Unique value analysis
# - Duplicate analysis
# - Coordinate detection
# - Coordinate validation
# - Semantic column detection
# - Data quality analysis
#
# DOES NOT:
# ----------------------------------------------------------
# ❌ Modify databases
# ❌ Insert records
# ❌ Delete records
# ❌ Update records
# ❌ Depend on PyQt
# ❌ Depend on OSM
# ❌ Depend on EYES-master
#
# ==========================================================

from __future__ import annotations

import math
import sqlite3

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


# ==========================================================
# COLUMN PROFILE
# ==========================================================


@dataclass(frozen=True)
class ColumnProfile:

    name: str

    declared_type: str

    nullable: bool

    primary_key: bool

    row_count: int

    null_count: int

    empty_count: int

    unique_count: int

    duplicate_count: int

    numeric_count: int

    text_count: int

    sample_values: tuple[Any, ...] = ()

    @property
    def non_empty_count(self) -> int:

        return max(
            0,
            self.row_count
            - self.null_count
            - self.empty_count,
        )

    @property
    def completeness(self) -> float:

        if self.row_count <= 0:
            return 0.0

        return (
            self.non_empty_count
            / self.row_count
        ) * 100.0

    def to_dict(self) -> dict:

        return {
            "name": self.name,
            "declared_type": self.declared_type,
            "nullable": self.nullable,
            "primary_key": self.primary_key,
            "row_count": self.row_count,
            "null_count": self.null_count,
            "empty_count": self.empty_count,
            "unique_count": self.unique_count,
            "duplicate_count": self.duplicate_count,
            "numeric_count": self.numeric_count,
            "text_count": self.text_count,
            "non_empty_count": self.non_empty_count,
            "completeness": self.completeness,
            "sample_values": list(
                self.sample_values
            ),
        }


# ==========================================================
# COORDINATE PROFILE
# ==========================================================


@dataclass(frozen=True)
class CoordinateProfile:

    latitude_column: Optional[str]

    longitude_column: Optional[str]

    total_rows: int

    valid_rows: int

    invalid_rows: int

    missing_rows: int

    @property
    def available(self) -> bool:

        return bool(
            self.latitude_column
            and self.longitude_column
        )

    @property
    def coverage(self) -> float:

        if self.total_rows <= 0:
            return 0.0

        return (
            self.valid_rows
            / self.total_rows
        ) * 100.0

    def to_dict(self) -> dict:

        return {
            "latitude_column":
                self.latitude_column,

            "longitude_column":
                self.longitude_column,

            "total_rows":
                self.total_rows,

            "valid_rows":
                self.valid_rows,

            "invalid_rows":
                self.invalid_rows,

            "missing_rows":
                self.missing_rows,

            "available":
                self.available,

            "coverage":
                self.coverage,
        }


# ==========================================================
# TABLE PROFILE
# ==========================================================


@dataclass(frozen=True)
class TableProfile:

    name: str

    row_count: int

    columns: tuple[ColumnProfile, ...]

    coordinate: CoordinateProfile

    detected_fields: dict[str, Optional[str]]

    duplicate_rows: int

    @property
    def column_count(self) -> int:

        return len(
            self.columns
        )

    def to_dict(self) -> dict:

        return {
            "name": self.name,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": [
                column.to_dict()
                for column in self.columns
            ],
            "coordinate":
                self.coordinate.to_dict(),

            "detected_fields":
                dict(
                    self.detected_fields
                ),

            "duplicate_rows":
                self.duplicate_rows,
        }


# ==========================================================
# DATABASE ANALYZER
# ==========================================================


class DatabaseAnalyzer:
    """
    Read-only SQLite database analyzer.

    The analyzer opens databases exclusively in read-only mode.
    """

    FIELD_ALIASES = {

        "name": (
            "name",
            "title",
            "business_name",
            "school_name",
            "company_name",
            "place_name",
        ),

        "latitude": (
            "latitude",
            "lat",
            "lat_deg",
            "geo_lat",
            "location_lat",
            "y",
        ),

        "longitude": (
            "longitude",
            "longitude_deg",
            "lon",
            "lng",
            "long",
            "geo_lon",
            "location_lon",
            "x",
        ),

        "phone": (
            "phone",
            "telephone",
            "tel",
            "mobile",
            "mobile_phone",
        ),

        "address": (
            "address",
            "full_address",
            "location",
            "street_address",
        ),

        "city": (
            "city",
            "town",
            "municipality",
        ),

        "province": (
            "province",
            "state",
            "region",
        ),

        "category": (
            "category",
            "type",
            "business_type",
            "place_type",
        ),

        "website": (
            "website",
            "site",
            "web",
            "homepage",
        ),

        "source": (
            "source",
            "provider",
            "origin",
        ),

        "source_id": (
            "source_id",
            "provider_id",
            "external_id",
        ),
    }

    # ======================================================
    # INIT
    # ======================================================

    def __init__(
        self,
        path: str | Path,
    ) -> None:

        self.path = (
            Path(path)
            .expanduser()
            .resolve()
        )

        self.connection: Optional[
            sqlite3.Connection
        ] = None

    # ======================================================
    # OPEN
    # ======================================================

    def open(self) -> None:

        if self.connection is not None:
            return

        if not self.path.exists():

            raise FileNotFoundError(
                self.path
            )

        uri = (
            "file:"
            + str(self.path)
            + "?mode=ro"
        )

        self.connection = sqlite3.connect(
            uri,
            uri=True,
            timeout=10,
        )

        self.connection.row_factory = (
            sqlite3.Row
        )

    # ======================================================
    # CLOSE
    # ======================================================

    def close(self) -> None:

        if self.connection is None:
            return

        try:

            self.connection.close()

        finally:

            self.connection = None

    # ======================================================
    # CONTEXT
    # ======================================================

    def __enter__(
        self,
    ) -> "DatabaseAnalyzer":

        self.open()

        return self

    # ======================================================

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:

        self.close()

    # ======================================================
    # REQUIRE
    # ======================================================

    def _require_connection(
        self,
    ) -> sqlite3.Connection:

        if self.connection is None:

            self.open()

        return self.connection

    # ======================================================
    # TABLES
    # ======================================================

    def tables(self) -> list[str]:

        connection = (
            self._require_connection()
        )

        cursor = connection.execute(
            """
            SELECT name
            FROM sqlite_master

            WHERE type = 'table'

            AND name NOT LIKE 'sqlite_%'

            ORDER BY name
            """
        )

        return [
            row[0]
            for row in cursor.fetchall()
        ]

    # ======================================================
    # COLUMNS
    # ======================================================

    def columns(
        self,
        table: str,
    ) -> list[dict]:

        connection = (
            self._require_connection()
        )

        cursor = connection.execute(
            f'PRAGMA table_info("{table}")'
        )

        return [
            {
                "cid": row["cid"],
                "name": row["name"],
                "type": row["type"],
                "notnull": bool(
                    row["notnull"]
                ),
                "default": row["dflt_value"],
                "primary_key": bool(
                    row["pk"]
                ),
            }
            for row in cursor.fetchall()
        ]

    # ======================================================
    # ROW COUNT
    # ======================================================

    def row_count(
        self,
        table: str,
    ) -> int:

        connection = (
            self._require_connection()
        )

        cursor = connection.execute(
            f'''
            SELECT COUNT(*)
            FROM "{table}"
            '''
        )

        return int(
            cursor.fetchone()[0]
        )

    # ======================================================
    # FIELD MATCHING
    # ======================================================

    @classmethod
    def detect_fields(
        cls,
        column_names: list[str],
    ) -> dict[str, Optional[str]]:

        normalized = {}

        for column in column_names:

            key = (
                str(column)
                .strip()
                .casefold()
            )

            normalized[key] = column

        result = {}

        for field, aliases in (
            cls.FIELD_ALIASES.items()
        ):

            found = None

            for alias in aliases:

                alias_key = (
                    alias.casefold()
                )

                if alias_key in normalized:

                    found = normalized[
                        alias_key
                    ]

                    break

            result[field] = found

        return result

    # ======================================================
    # FLOAT
    # ======================================================

    @staticmethod
    def coordinate(
        value: Any,
    ) -> Optional[float]:

        if value is None:
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

        if not math.isfinite(
            result
        ):

            return None

        return result

    # ======================================================
    # VALID COORDINATE
    # ======================================================

    @classmethod
    def valid_coordinate(
        cls,
        latitude: Any,
        longitude: Any,
    ) -> bool:

        lat = cls.coordinate(
            latitude
        )

        lon = cls.coordinate(
            longitude
        )

        if lat is None or lon is None:
            return False

        return (
            -90 <= lat <= 90
            and
            -180 <= lon <= 180
        )

    # ======================================================
    # COLUMN PROFILE
    # ======================================================

    def analyze_column(
        self,
        table: str,
        column: dict,
        row_count: int,
    ) -> ColumnProfile:

        connection = (
            self._require_connection()
        )

        name = column["name"]

        quoted = (
            f'"{name}"'
        )

        null_count = connection.execute(
            f'''
            SELECT COUNT(*)
            FROM "{table}"
            WHERE {quoted} IS NULL
            '''
        ).fetchone()[0]

        empty_count = connection.execute(
            f'''
            SELECT COUNT(*)
            FROM "{table}"
            WHERE
                {quoted} IS NOT NULL
                AND
                typeof({quoted}) = 'text'
                AND
                trim({quoted}) = ''
            '''
        ).fetchone()[0]

        unique_count = connection.execute(
            f'''
            SELECT COUNT(DISTINCT {quoted})
            FROM "{table}"
            WHERE {quoted} IS NOT NULL
            '''
        ).fetchone()[0]

        duplicate_count = max(
            0,
            (
                row_count
                - int(unique_count)
                - int(null_count)
            ),
        )

        numeric_count = connection.execute(
            f'''
            SELECT COUNT(*)
            FROM "{table}"
            WHERE
                {quoted} IS NOT NULL
                AND
                typeof({quoted})
                IN ('integer', 'real')
            '''
        ).fetchone()[0]

        text_count = connection.execute(
            f'''
            SELECT COUNT(*)
            FROM "{table}"
            WHERE
                {quoted} IS NOT NULL
                AND
                typeof({quoted}) = 'text'
            '''
        ).fetchone()[0]

        cursor = connection.execute(
            f'''
            SELECT {quoted}
            FROM "{table}"
            WHERE {quoted} IS NOT NULL
            LIMIT 5
            '''
        )

        samples = tuple(
            row[0]
            for row in cursor.fetchall()
        )

        return ColumnProfile(
            name=name,
            declared_type=(
                column["type"] or ""
            ),
            nullable=not column[
                "notnull"
            ],
            primary_key=bool(
                column["primary_key"]
            ),
            row_count=row_count,
            null_count=int(
                null_count
            ),
            empty_count=int(
                empty_count
            ),
            unique_count=int(
                unique_count
            ),
            duplicate_count=int(
                duplicate_count
            ),
            numeric_count=int(
                numeric_count
            ),
            text_count=int(
                text_count
            ),
            sample_values=samples,
        )

    # ======================================================
    # COORDINATE ANALYSIS
    # ======================================================

    def analyze_coordinates(
        self,
        table: str,
        detected: dict[str, Optional[str]],
        total_rows: int,
    ) -> CoordinateProfile:

        latitude = detected.get(
            "latitude"
        )

        longitude = detected.get(
            "longitude"
        )

        if not latitude or not longitude:

            return CoordinateProfile(
                latitude_column=latitude,
                longitude_column=longitude,
                total_rows=total_rows,
                valid_rows=0,
                invalid_rows=0,
                missing_rows=total_rows,
            )

        connection = (
            self._require_connection()
        )

        cursor = connection.execute(
            f'''
            SELECT
                "{latitude}",
                "{longitude}"
            FROM "{table}"
            '''
        )

        valid = 0
        invalid = 0
        missing = 0

        for row in cursor.fetchall():

            lat = self.coordinate(
                row[0]
            )

            lon = self.coordinate(
                row[1]
            )

            if lat is None or lon is None:

                missing += 1

                continue

            if (
                -90 <= lat <= 90
                and
                -180 <= lon <= 180
            ):

                valid += 1

            else:

                invalid += 1

        return CoordinateProfile(
            latitude_column=latitude,
            longitude_column=longitude,
            total_rows=total_rows,
            valid_rows=valid,
            invalid_rows=invalid,
            missing_rows=missing,
        )

    # ======================================================
    # DUPLICATE ROWS
    # ======================================================

    def duplicate_rows(
        self,
        table: str,
    ) -> int:

        connection = (
            self._require_connection()
        )

        columns = self.columns(
            table
        )

        if not columns:
            return 0

        names = [
            column["name"]
            for column in columns
        ]

        expressions = ", ".join(
            f'"{name}"'
            for name in names
        )

        query = f'''
            SELECT
                COUNT(*) - COUNT(
                    DISTINCT
                    {expressions}
                )
            FROM "{table}"
        '''

        try:

            result = connection.execute(
                query
            ).fetchone()[0]

            return max(
                0,
                int(result or 0),
            )

        except sqlite3.Error:

            return 0

    # ======================================================
    # TABLE ANALYSIS
    # ======================================================

    def analyze_table(
        self,
        table: str,
    ) -> TableProfile:

        row_count = self.row_count(
            table
        )

        column_info = self.columns(
            table
        )

        column_names = [
            column["name"]
            for column in column_info
        ]

        detected = (
            self.detect_fields(
                column_names
            )
        )

        profiles = tuple(
            self.analyze_column(
                table,
                column,
                row_count,
            )
            for column in column_info
        )

        coordinates = (
            self.analyze_coordinates(
                table,
                detected,
                row_count,
            )
        )

        duplicates = (
            self.duplicate_rows(
                table
            )
        )

        return TableProfile(
            name=table,
            row_count=row_count,
            columns=profiles,
            coordinate=coordinates,
            detected_fields=detected,
            duplicate_rows=duplicates,
        )

    # ======================================================
    # DATABASE ANALYSIS
    # ======================================================

    def analyze(
        self,
    ) -> list[TableProfile]:

        return [
            self.analyze_table(
                table
            )
            for table in self.tables()
        ]

    # ======================================================
    # BEST MAP TABLE
    # ======================================================

    def best_map_table(
        self,
    ) -> Optional[TableProfile]:
        """
        Select the most suitable table for map display.

        Priority:
            1. latitude + longitude
            2. valid coordinate coverage
            3. row count
        """

        profiles = self.analyze()

        candidates = [
            profile
            for profile in profiles
            if profile.coordinate.available
        ]

        if not candidates:
            return None

        candidates.sort(
            key=lambda profile: (
                profile.coordinate.valid_rows,
                profile.row_count,
            ),
            reverse=True,
        )

        return candidates[0]

    # ======================================================
    # SUMMARY
    # ======================================================

    def summary(
        self,
    ) -> dict:

        profiles = self.analyze()

        total_rows = sum(
            profile.row_count
            for profile in profiles
        )

        coordinate_rows = sum(
            profile.coordinate.valid_rows
            for profile in profiles
        )

        return {
            "database":
                str(self.path),

            "tables":
                len(profiles),

            "total_rows":
                total_rows,

            "coordinate_rows":
                coordinate_rows,

            "map_available":
                any(
                    profile.coordinate.available
                    for profile in profiles
                ),

            "table_names": [
                profile.name
                for profile in profiles
            ],
        }


# ==========================================================
# EXPORTS
# ==========================================================

__all__ = [
    "ColumnProfile",
    "CoordinateProfile",
    "TableProfile",
    "DatabaseAnalyzer",
]