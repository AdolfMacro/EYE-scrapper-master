# ==========================================================
# EYES MASTER — DATABASE LAYER
# ==========================================================
#
# FILE:
#     database/database.py
#
# STATUS:
#     CANONICAL / CORE
#
# ROLE:
#     Canonical SQLite persistence layer for EYES.
#
# ARCHITECTURE:
#
#     Provider
#         │
#         ▼
#     Extractor / Normalizer
#         │
#         ▼
#     Business Model
#         │
#         ▼
#     Database
#         │
#         ├── businesses
#         ├── coordinate validation
#         ├── duplicate detection
#         ├── persistence
#         ├── queries
#         └── statistics
#
# CORE RULE:
#
#     A Business MUST have valid latitude and longitude
#     before it can enter the canonical database.
#
# IMPORTANT:
#
#     This file knows nothing about:
#
#         School
#         Provider
#         Scraper
#         Keyword generation
#         GUI
#         Worker orchestration
#
#     It is ONLY the canonical persistence layer.
#
# ==========================================================

from __future__ import annotations

import os
import re
import sqlite3
import threading

from datetime import datetime, timezone
from typing import Any, Optional

from models.business import Business


class Database:
    """
    Canonical SQLite persistence layer for EYES.

    The canonical entity stored by this class is Business.

    Persistence rule
    ----------------
    A Business is persisted only when:

        latitude is valid
        AND
        longitude is valid

    Responsibilities
    ----------------
    - SQLite connection management
    - Canonical schema creation
    - Business persistence
    - Coordinate validation
    - Duplicate detection
    - Query APIs
    - Statistics
    - Safe concurrent access
    """

    # ======================================================
    # CONSTANTS
    # ======================================================

    TABLE_NAME = "businesses"

    DEFAULT_PATH = "data/results.db"

    # ======================================================
    # INIT
    # ======================================================

    def __init__(
        self,
        path: str = DEFAULT_PATH,
    ) -> None:

        self.path = str(path)

        self.lock = threading.RLock()

        self.connection: Optional[
            sqlite3.Connection
        ] = None

        self._ensure_directory()

        self._connect()

        self.create_tables()

    # ======================================================
    # CONNECTION
    # ======================================================

    def _ensure_directory(self) -> None:
        """
        Ensure the database parent directory exists.
        """

        directory = os.path.dirname(
            self.path
        )

        if directory:

            os.makedirs(
                directory,
                exist_ok=True,
            )

    # ======================================================

    def _connect(self) -> None:
        """
        Create and configure the SQLite connection.
        """

        self.connection = sqlite3.connect(
            self.path,
            check_same_thread=False,
            timeout=30,
        )

        self.connection.row_factory = sqlite3.Row

        self.connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        self.connection.execute(
            "PRAGMA journal_mode = WAL"
        )

        self.connection.execute(
            "PRAGMA synchronous = NORMAL"
        )

        self.connection.execute(
            "PRAGMA busy_timeout = 30000"
        )

        self.connection.commit()

    # ======================================================
    # TIMESTAMP
    # ======================================================

    @staticmethod
    def now() -> str:
        """
        Return the current UTC timestamp.
        """

        return datetime.now(
            timezone.utc
        ).isoformat()

    # ======================================================
    # TABLE CREATION
    # ======================================================

    def create_tables(self) -> None:
        """
        Create the canonical businesses table.
        """

        query = """
        CREATE TABLE IF NOT EXISTS businesses (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            category TEXT DEFAULT '',

            keyword TEXT DEFAULT '',

            province TEXT DEFAULT '',

            city TEXT DEFAULT '',

            address TEXT DEFAULT '',

            neighborhood TEXT DEFAULT '',

            street TEXT DEFAULT '',

            phone TEXT DEFAULT '',

            website TEXT DEFAULT '',

            url TEXT DEFAULT '',

            source_url TEXT DEFAULT '',

            source TEXT DEFAULT '',

            source_id TEXT,

            latitude REAL NOT NULL,

            longitude REAL NOT NULL,

            distance_km REAL,

            created_at TEXT NOT NULL,

            updated_at TEXT NOT NULL

        )
        """

        self.execute(
            query
        )

        self._create_indexes()

    # ======================================================
    # INDEXES
    # ======================================================

    def _create_indexes(self) -> None:
        """
        Create indexes used by common queries and
        duplicate detection.
        """

        indexes = (

            """
            CREATE INDEX IF NOT EXISTS
            idx_businesses_source
            ON businesses(source)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_businesses_source_id
            ON businesses(source_id)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_businesses_name
            ON businesses(name)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_businesses_city
            ON businesses(city)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_businesses_province
            ON businesses(province)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_businesses_phone
            ON businesses(phone)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_businesses_coordinates
            ON businesses(latitude, longitude)
            """,

            """
            CREATE INDEX IF NOT EXISTS
            idx_businesses_name_city
            ON businesses(name, city)
            """,
        )

        for query in indexes:

            self.execute(
                query
            )

    # ======================================================
    # EXECUTE
    # ======================================================

    def execute(
        self,
        query: str,
        params: tuple = (),
    ):
        """
        Execute a SQL statement safely.

        This method is intended for schema and simple
        database operations.
        """

        with self.lock:

            self._require_connection()

            cursor = self.connection.cursor()

            try:

                cursor.execute(
                    query,
                    params,
                )

                self.connection.commit()

                return cursor

            except sqlite3.Error:

                self.connection.rollback()

                raise

    # ======================================================
    # CONNECTION VALIDATION
    # ======================================================

    def _require_connection(self) -> None:
        """
        Ensure the database connection is available.
        """

        if self.connection is None:

            raise RuntimeError(
                "Database connection is closed."
            )

    # ======================================================
    # TABLE HELPERS
    # ======================================================

    def table_exists(
        self,
        table_name: str,
    ) -> bool:
        """
        Check whether a SQLite table exists.
        """

        with self.lock:

            self._require_connection()

            cursor = self.connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                AND name = ?
                """,
                (
                    table_name,
                ),
            )

            return (
                cursor.fetchone()
                is not None
            )

    # ======================================================

    def table_columns(
        self,
        table_name: str,
    ) -> set[str]:
        """
        Return all columns belonging to a table.
        """

        with self.lock:

            self._require_connection()

            cursor = self.connection.execute(
                f'PRAGMA table_info("{table_name}")'
            )

            return {
                row["name"]
                for row in cursor.fetchall()
            }

    # ======================================================
    # TEXT NORMALIZATION
    # ======================================================

    @staticmethod
    def text_value(
        value: Any,
    ) -> str:
        """
        Convert arbitrary values into normalized text.
        """

        if value is None:

            return ""

        return " ".join(
            str(value)
            .strip()
            .split()
        )

    # ======================================================
    # LOOKUP NORMALIZATION
    # ======================================================

    @classmethod
    def normalize_lookup_text(
        cls,
        value: Any,
    ) -> str:
        """
        Normalize text used for identity and lookup.

        Includes Persian/Arabic character normalization.
        """

        text = cls.text_value(
            value
        )

        if not text:

            return ""

        replacements = {

            "ي": "ی",
            "ى": "ی",
            "ك": "ک",
            "ۀ": "ه",
            "ة": "ه",
            "ؤ": "و",
            "إ": "ا",
            "أ": "ا",
            "ٱ": "ا",
            "ـ": "",
        }

        for old, new in replacements.items():

            text = text.replace(
                old,
                new,
            )

        text = re.sub(
            r"[\u200c\u200d]",
            " ",
            text,
        )

        text = re.sub(
            r"[ًٌٍَُِّْـ]",
            "",
            text,
        )

        return " ".join(
            text.split()
        ).casefold()

    # ======================================================
    # FLOAT
    # ======================================================

    @staticmethod
    def float_value(
        value: Any,
    ) -> Optional[float]:
        """
        Convert a value to a finite float.

        Invalid values return None.
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

    # ======================================================
    # COORDINATE VALIDATION
    # ======================================================

    @classmethod
    def valid_coordinates(
        cls,
        latitude: Any,
        longitude: Any,
    ) -> bool:
        """
        Validate geographic coordinates.

        Latitude:
            -90 <= latitude <= 90

        Longitude:
            -180 <= longitude <= 180
        """

        lat = cls.float_value(
            latitude
        )

        lon = cls.float_value(
            longitude
        )

        if lat is None or lon is None:

            return False

        if not (
            -90.0 <= lat <= 90.0
        ):

            return False

        if not (
            -180.0 <= lon <= 180.0
        ):

            return False

        return True

    # ======================================================
    # BUSINESS CONVERSION
    # ======================================================

    @staticmethod
    def to_business(
        data: Any,
    ) -> Business:
        """
        Convert incoming data into the canonical
        Business model.
        """

        if isinstance(
            data,
            Business,
        ):

            return data.copy()

        if isinstance(
            data,
            dict,
        ):

            return Business.from_dict(
                dict(data)
            )

        raise TypeError(
            "Database expects a Business "
            "object or dictionary."
        )

    # ======================================================
    # DUPLICATE — SOURCE ID
    # ======================================================

    def find_by_source_id(
        self,
        source: str,
        source_id: str,
    ) -> Optional[dict]:
        """
        Find a business by provider identity.
        """

        source = self.text_value(
            source
        )

        source_id = self.text_value(
            source_id
        )

        if not source or not source_id:

            return None

        with self.lock:

            self._require_connection()

            cursor = self.connection.execute(
                """
                SELECT *
                FROM businesses

                WHERE lower(trim(source))
                    = lower(trim(?))

                AND lower(trim(source_id))
                    = lower(trim(?))

                LIMIT 1
                """,
                (
                    source,
                    source_id,
                ),
            )

            row = cursor.fetchone()

            if row is None:

                return None

            return dict(row)

    # ======================================================
    # DUPLICATE — PHONE
    # ======================================================

    def find_by_phone(
        self,
        phone: str,
    ) -> Optional[dict]:
        """
        Find a business by phone number.
        """

        phone = self.text_value(
            phone
        )

        if not phone:

            return None

        with self.lock:

            self._require_connection()

            cursor = self.connection.execute(
                """
                SELECT *
                FROM businesses

                WHERE phone = ?

                LIMIT 1
                """,
                (
                    phone,
                ),
            )

            row = cursor.fetchone()

            if row is None:

                return None

            return dict(row)

    # ======================================================
    # DUPLICATE — NAME + CITY
    # ======================================================

    def find_by_name_city(
        self,
        name: str,
        city: str,
    ) -> Optional[dict]:
        """
        Find a business using normalized name and city.
        """

        name_key = (
            self.normalize_lookup_text(
                name
            )
        )

        city_key = (
            self.normalize_lookup_text(
                city
            )
        )

        if not name_key:

            return None

        with self.lock:

            self._require_connection()

            cursor = self.connection.execute(
                """
                SELECT *
                FROM businesses
                """
            )

            for row in cursor.fetchall():

                existing_name = (
                    self.normalize_lookup_text(
                        row["name"]
                    )
                )

                existing_city = (
                    self.normalize_lookup_text(
                        row["city"]
                    )
                )

                if (
                    existing_name == name_key
                    and
                    existing_city == city_key
                ):

                    return dict(row)

        return None

    # ======================================================
    # DUPLICATE — COORDINATES
    # ======================================================

    def find_by_coordinates(
        self,
        latitude: Any,
        longitude: Any,
    ) -> Optional[dict]:
        """
        Find a business using exact coordinates.
        """

        lat = self.float_value(
            latitude
        )

        lon = self.float_value(
            longitude
        )

        if not self.valid_coordinates(
            lat,
            lon,
        ):

            return None

        with self.lock:

            self._require_connection()

            cursor = self.connection.execute(
                """
                SELECT *
                FROM businesses

                WHERE latitude = ?
                AND longitude = ?

                LIMIT 1
                """,
                (
                    lat,
                    lon,
                ),
            )

            row = cursor.fetchone()

            if row is None:

                return None

            return dict(row)

    # ======================================================
    # DUPLICATE DETECTION
    # ======================================================

    def find_duplicate(
        self,
        business: Business,
    ) -> tuple[
        Optional[dict],
        Optional[str],
    ]:
        """
        Detect an existing business.

        Priority:

            1. source + source_id
            2. coordinates
            3. phone
            4. normalized name + city
        """

        if (
            business.source
            and business.source_id
        ):

            existing = (
                self.find_by_source_id(
                    business.source,
                    business.source_id,
                )
            )

            if existing:

                return (
                    existing,
                    "DUPLICATE_SOURCE_ID",
                )

        existing = (
            self.find_by_coordinates(
                business.latitude,
                business.longitude,
            )
        )

        if existing:

            return (
                existing,
                "DUPLICATE_COORDINATES",
            )

        if business.phone:

            existing = (
                self.find_by_phone(
                    business.phone
                )
            )

            if existing:

                return (
                    existing,
                    "DUPLICATE_PHONE",
                )

        if business.name:

            existing = (
                self.find_by_name_city(
                    business.name,
                    business.city,
                )
            )

            if existing:

                return (
                    existing,
                    "DUPLICATE_NAME_CITY",
                )

        return (
            None,
            None,
        )

    # ======================================================
    # INSERT BUSINESS
    # ======================================================

    def insert_business(
        self,
        data: Any,
        return_reason: bool = False,
    ):
        """
        Persist a Business into the canonical database.

        HARD RULE:

            No valid coordinates
                =
            No database insertion.

        Possible results:

            INSERTED

            INVALID_DATA
            INVALID_NAME
            MISSING_COORDINATES
            INVALID_COORDINATES

            DUPLICATE_SOURCE_ID
            DUPLICATE_COORDINATES
            DUPLICATE_PHONE
            DUPLICATE_NAME_CITY

            INTEGRITY_ERROR
            SQLITE_ERROR
        """

        try:

            business = self.to_business(
                data
            )

        except (
            TypeError,
            ValueError,
        ):

            if return_reason:

                return (
                    False,
                    "INVALID_DATA",
                )

            return False

        if not business.name:

            if return_reason:

                return (
                    False,
                    "INVALID_NAME",
                )

            return False

        if (
            business.latitude is None
            or
            business.longitude is None
        ):

            if return_reason:

                return (
                    False,
                    "MISSING_COORDINATES",
                )

            return False

        if not self.valid_coordinates(
            business.latitude,
            business.longitude,
        ):

            if return_reason:

                return (
                    False,
                    "INVALID_COORDINATES",
                )

            return False

        with self.lock:

            self._require_connection()

            try:

                self.connection.execute(
                    "BEGIN IMMEDIATE"
                )

                existing, reason = (
                    self.find_duplicate(
                        business
                    )
                )

                if existing:

                    self.connection.rollback()

                    if return_reason:

                        return (
                            False,
                            reason,
                        )

                    return False

                created_at = (
                    getattr(
                        business,
                        "created_at",
                        None,
                    )
                    or
                    self.now()
                )

                updated_at = (
                    self.now()
                )

                query = """
                INSERT INTO businesses
                (
                    name,
                    category,
                    keyword,
                    province,
                    city,
                    address,
                    neighborhood,
                    street,
                    phone,
                    website,
                    url,
                    source_url,
                    source,
                    source_id,
                    latitude,
                    longitude,
                    distance_km,
                    created_at,
                    updated_at
                )

                VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?
                )
                """

                values = (

                    self.text_value(
                        business.name
                    ),

                    self.text_value(
                        business.category
                    ),

                    self.text_value(
                        business.keyword
                    ),

                    self.text_value(
                        business.province
                    ),

                    self.text_value(
                        business.city
                    ),

                    self.text_value(
                        business.address
                    ),

                    self.text_value(
                        business.neighborhood
                    ),

                    self.text_value(
                        business.street
                    ),

                    self.text_value(
                        business.phone
                    ),

                    self.text_value(
                        business.website
                    ),

                    self.text_value(
                        business.url
                    ),

                    self.text_value(
                        business.source_url
                    ),

                    self.text_value(
                        business.source
                    ),

                    (
                        self.text_value(
                            business.source_id
                        )
                        or None
                    ),

                    self.float_value(
                        business.latitude
                    ),

                    self.float_value(
                        business.longitude
                    ),

                    self.float_value(
                        business.distance_km
                    ),

                    self.text_value(
                        created_at
                    ),

                    updated_at,
                )

                cursor = (
                    self.connection.cursor()
                )

                cursor.execute(
                    query,
                    values,
                )

                self.connection.commit()

                if return_reason:

                    return (
                        True,
                        "INSERTED",
                    )

                return True

            except sqlite3.IntegrityError:

                self.connection.rollback()

                if return_reason:

                    return (
                        False,
                        "INTEGRITY_ERROR",
                    )

                return False

            except sqlite3.Error:

                self.connection.rollback()

                if return_reason:

                    return (
                        False,
                        "SQLITE_ERROR",
                    )

                return False

    # ======================================================
    # GET BY ID
    # ======================================================

    def get_by_id(
        self,
        business_id: int,
    ) -> Optional[dict]:
        """
        Return one business by database ID.
        """

        with self.lock:

            self._require_connection()

            cursor = self.connection.execute(
                """
                SELECT *
                FROM businesses
                WHERE id = ?
                LIMIT 1
                """,
                (
                    business_id,
                ),
            )

            row = cursor.fetchone()

            if row is None:

                return None

            return dict(row)

    # ======================================================
    # ALL
    # ======================================================

    def all(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[dict]:
        """
        Return canonical businesses.
        """

        with self.lock:

            self._require_connection()

            if limit is None:

                cursor = (
                    self.connection.execute(
                        """
                        SELECT *
                        FROM businesses
                        ORDER BY id DESC
                        """
                    )
                )

            else:

                cursor = (
                    self.connection.execute(
                        """
                        SELECT *
                        FROM businesses
                        ORDER BY id DESC
                        LIMIT ?
                        OFFSET ?
                        """,
                        (
                            max(
                                0,
                                int(limit),
                            ),
                            max(
                                0,
                                int(offset),
                            ),
                        ),
                    )
                )

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

    # ======================================================
    # COUNT
    # ======================================================

    def count(
        self,
        city: Optional[str] = None,
        source: Optional[str] = None,
    ) -> int:
        """
        Count businesses with optional filters.
        """

        with self.lock:

            self._require_connection()

            conditions = []

            params = []

            if city is not None:

                conditions.append(
                    """
                    lower(trim(city))
                    =
                    lower(trim(?))
                    """
                )

                params.append(
                    city
                )

            if source is not None:

                conditions.append(
                    """
                    lower(trim(source))
                    =
                    lower(trim(?))
                    """
                )

                params.append(
                    source
                )

            if conditions:

                query = f"""
                    SELECT COUNT(*)
                    FROM businesses
                    WHERE {" AND ".join(conditions)}
                """

            else:

                query = """
                    SELECT COUNT(*)
                    FROM businesses
                """

            cursor = (
                self.connection.execute(
                    query,
                    tuple(params),
                )
            )

            row = cursor.fetchone()

            return int(
                row[0]
            )

    # ======================================================
    # BY CITY
    # ======================================================

    def by_city(
        self,
        city: str,
    ) -> list[dict]:
        """
        Return businesses in a city.
        """

        with self.lock:

            self._require_connection()

            cursor = self.connection.execute(
                """
                SELECT *
                FROM businesses

                WHERE lower(trim(city))
                    = lower(trim(?))

                ORDER BY id DESC
                """,
                (
                    city,
                ),
            )

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

    # ======================================================
    # BY SOURCE
    # ======================================================

    def by_source(
        self,
        source: str,
    ) -> list[dict]:
        """
        Return businesses discovered by a provider.
        """

        with self.lock:

            self._require_connection()

            cursor = self.connection.execute(
                """
                SELECT *
                FROM businesses

                WHERE lower(trim(source))
                    = lower(trim(?))

                ORDER BY id DESC
                """,
                (
                    source,
                ),
            )

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

    # ======================================================
    # SEARCH
    # ======================================================

    def search(
        self,
        text: str,
        limit: int = 100,
    ) -> list[dict]:
        """
        Search across common business fields.
        """

        text = self.text_value(
            text
        )

        if not text:

            return []

        limit = max(
            1,
            int(limit),
        )

        pattern = f"%{text}%"

        with self.lock:

            self._require_connection()

            cursor = self.connection.execute(
                """
                SELECT *
                FROM businesses

                WHERE
                    name LIKE ?
                    OR category LIKE ?
                    OR keyword LIKE ?
                    OR province LIKE ?
                    OR city LIKE ?
                    OR address LIKE ?
                    OR neighborhood LIKE ?
                    OR street LIKE ?
                    OR phone LIKE ?
                    OR website LIKE ?

                ORDER BY id DESC

                LIMIT ?
                """,
                (
                    pattern,
                    pattern,
                    pattern,
                    pattern,
                    pattern,
                    pattern,
                    pattern,
                    pattern,
                    pattern,
                    pattern,
                    limit,
                ),
            )

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

    # ======================================================
    # WITH COORDINATES
    # ======================================================

    def with_coordinates(
        self,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """
        Return businesses with coordinates.
        """

        query = """
            SELECT *
            FROM businesses

            WHERE latitude IS NOT NULL
            AND longitude IS NOT NULL

            ORDER BY id DESC
        """

        params = ()

        if limit is not None:

            query += """
                LIMIT ?
            """

            params = (
                max(
                    1,
                    int(limit),
                ),
            )

        with self.lock:

            self._require_connection()

            cursor = (
                self.connection.execute(
                    query,
                    params,
                )
            )

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

    # ======================================================
    # MISSING COORDINATES
    # ======================================================

    def missing_coordinates(self) -> list[dict]:
        """
        Return records without coordinates.

        Under the canonical schema this should normally
        return an empty list.
        """

        with self.lock:

            self._require_connection()

            cursor = self.connection.execute(
                """
                SELECT *
                FROM businesses

                WHERE
                    latitude IS NULL
                    OR longitude IS NULL

                ORDER BY id DESC
                """
            )

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

    # ======================================================
    # STATISTICS
    # ======================================================

    def statistics(self) -> dict[str, Any]:
        """
        Return canonical database statistics.
        """

        with self.lock:

            self._require_connection()

            total = self.count()

            with_phone = (
                self.connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM businesses

                    WHERE phone IS NOT NULL
                    AND trim(phone) != ''
                    """
                )
                .fetchone()[0]
            )

            with_website = (
                self.connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM businesses

                    WHERE website IS NOT NULL
                    AND trim(website) != ''
                    """
                )
                .fetchone()[0]
            )

            with_coordinates = (
                self.connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM businesses

                    WHERE latitude IS NOT NULL
                    AND longitude IS NOT NULL
                    """
                )
                .fetchone()[0]
            )

            cities = (
                self.connection.execute(
                    """
                    SELECT COUNT(
                        DISTINCT city
                    )
                    FROM businesses

                    WHERE trim(city) != ''
                    """
                )
                .fetchone()[0]
            )

            sources = (
                self.connection.execute(
                    """
                    SELECT COUNT(
                        DISTINCT source
                    )
                    FROM businesses

                    WHERE trim(source) != ''
                    """
                )
                .fetchone()[0]
            )

            categories = (
                self.connection.execute(
                    """
                    SELECT COUNT(
                        DISTINCT category
                    )
                    FROM businesses

                    WHERE trim(category) != ''
                    """
                )
                .fetchone()[0]
            )

            return {

                "total": int(
                    total
                ),

                "with_phone": int(
                    with_phone
                ),

                "without_phone": (
                    int(total)
                    - int(with_phone)
                ),

                "with_website": int(
                    with_website
                ),

                "without_website": (
                    int(total)
                    - int(with_website)
                ),

                "with_coordinates": int(
                    with_coordinates
                ),

                "without_coordinates": (
                    int(total)
                    - int(with_coordinates)
                ),

                "cities": int(
                    cities
                ),

                "sources": int(
                    sources
                ),

                "categories": int(
                    categories
                ),
            }

    # ======================================================
    # DELETE
    # ======================================================

    def delete(
        self,
        business_id: int,
    ) -> bool:
        """
        Delete a business by ID.
        """

        with self.lock:

            self._require_connection()

            cursor = self.connection.execute(
                """
                DELETE FROM businesses
                WHERE id = ?
                """,
                (
                    business_id,
                ),
            )

            self.connection.commit()

            return (
                cursor.rowcount > 0
            )

    # ======================================================
    # CLEAR
    # ======================================================

    def clear(self) -> None:
        """
        Delete all canonical businesses.
        """

        with self.lock:

            self._require_connection()

            self.connection.execute(
                """
                DELETE FROM businesses
                """
            )

            self.connection.commit()

    # ======================================================
    # VACUUM
    # ======================================================

    def vacuum(self) -> None:
        """
        Reclaim unused SQLite space.
        """

        with self.lock:

            self._require_connection()

            self.connection.execute(
                "VACUUM"
            )

    # ======================================================
    # CONTEXT MANAGER
    # ======================================================

    def __enter__(self) -> "Database":

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
    # CLOSE
    # ======================================================

    def close(self) -> None:
        """
        Safely close the database connection.
        """

        with self.lock:

            if self.connection is None:

                return

            try:

                self.connection.close()

            except sqlite3.Error:

                pass

            finally:

                self.connection = None
