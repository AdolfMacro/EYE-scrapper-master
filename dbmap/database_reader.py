from __future__ import annotations

import sqlite3

from pathlib import Path
from typing import Any, Optional


class DatabaseReader:
    """
    Read-only SQLite database reader for Data Manager.

    This class NEVER modifies the source database.

    Responsibilities:
        - Open SQLite databases read-only
        - Discover tables
        - Discover columns
        - Read records
        - Search records
        - Extract map records
        - Generate statistics
    """

    SEARCHABLE_COLUMNS = frozenset(
        {
            "name",
            "title",
            "business_name",
            "school_name",
            "category",
            "keyword",
            "province",
            "city",
            "address",
            "neighborhood",
            "street",
            "phone",
            "website",
            "source",
        }
    )

    BUSINESS_TABLE_CANDIDATES = (
        "businesses",
        "schools",
        "results",
        "data",
    )

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
    # IDENTIFIER
    # ======================================================

    @staticmethod
    def _quote_identifier(
        identifier: str,
    ) -> str:

        return (
            '"'
            + str(identifier).replace(
                '"',
                '""',
            )
            + '"'
        )

    # ======================================================
    # SQLITE URI
    # ======================================================

    def _readonly_uri(self) -> str:

        return (
            "file:"
            + str(self.path)
            + "?mode=ro"
        )

    # ======================================================
    # OPEN
    # ======================================================

    def open(self) -> None:

        self.close()

        if not self.path.exists():

            raise FileNotFoundError(
                self.path
            )

        if not self.path.is_file():

            raise IsADirectoryError(
                self.path
            )

        self.connection = sqlite3.connect(
            self._readonly_uri(),
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
    # REQUIRE
    # ======================================================

    def _require_connection(
        self,
    ) -> sqlite3.Connection:

        if self.connection is None:

            raise RuntimeError(
                "Database is not open."
            )

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
            row["name"]
            for row in cursor.fetchall()
        ]

    # ======================================================
    # COLUMNS
    # ======================================================

    def columns(
        self,
        table: str,
    ) -> list[str]:

        connection = (
            self._require_connection()
        )

        quoted_table = (
            self._quote_identifier(table)
        )

        cursor = connection.execute(
            f"PRAGMA table_info({quoted_table})"
        )

        return [
            row["name"]
            for row in cursor.fetchall()
        ]

    # ======================================================
    # BUSINESS TABLE
    # ======================================================

    def business_table(
        self,
    ) -> Optional[str]:

        tables = set(
            self.tables()
        )

        for table in (
            self.BUSINESS_TABLE_CANDIDATES
        ):

            if table in tables:
                return table

        return None

    # ======================================================
    # COUNT
    # ======================================================

    def count(
        self,
        table: Optional[str] = None,
    ) -> int:

        connection = (
            self._require_connection()
        )

        table = (
            table
            or self.business_table()
        )

        if not table:
            return 0

        quoted_table = (
            self._quote_identifier(table)
        )

        cursor = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM {quoted_table}
            """
        )

        return int(
            cursor.fetchone()[0]
        )

    # ======================================================
    # RECORDS
    # ======================================================

    def records(
        self,
        table: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        where: Optional[str] = None,
        params: tuple[Any, ...] = (),
    ) -> list[dict[str, Any]]:

        connection = (
            self._require_connection()
        )

        table = (
            table
            or self.business_table()
        )

        if not table:
            return []

        quoted_table = (
            self._quote_identifier(table)
        )

        query = (
            f"SELECT * FROM {quoted_table}"
        )

        if where:
            query += f" WHERE {where}"

        query += " ORDER BY rowid DESC"

        values = list(params)

        if limit is not None:

            safe_limit = max(
                1,
                int(limit),
            )

            safe_offset = max(
                0,
                int(offset),
            )

            query += (
                " LIMIT ? OFFSET ?"
            )

            values.extend(
                [
                    safe_limit,
                    safe_offset,
                ]
            )

        cursor = connection.execute(
            query,
            tuple(values),
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    # ======================================================
    # MAP DATA
    # ======================================================

    def map_records(
        self,
        table: Optional[str] = None,
    ) -> list[dict[str, Any]]:

        rows = self.records(
            table=table
        )

        result = []

        for row in rows:

            latitude = row.get(
                "latitude"
            )

            longitude = row.get(
                "longitude"
            )

            try:

                if isinstance(
                    latitude,
                    bool,
                ) or isinstance(
                    longitude,
                    bool,
                ):
                    continue

                latitude = float(
                    latitude
                )

                longitude = float(
                    longitude
                )

            except (
                TypeError,
                ValueError,
            ):

                continue

            if not (
                -90.0 <= latitude <= 90.0
            ):
                continue

            if not (
                -180.0 <= longitude <= 180.0
            ):
                continue

            row["latitude"] = latitude
            row["longitude"] = longitude

            result.append(row)

        return result

    # ======================================================
    # SEARCH
    # ======================================================

    def search(
        self,
        text: str,
        table: Optional[str] = None,
    ) -> list[dict[str, Any]]:

        connection = (
            self._require_connection()
        )

        text = str(text).strip()

        if not text:
            return self.records(
                table
            )

        table = (
            table
            or self.business_table()
        )

        if not table:
            return []

        columns = self.columns(
            table
        )

        searchable = [
            column
            for column in columns
            if column.casefold()
            in {
                name.casefold()
                for name in self.SEARCHABLE_COLUMNS
            }
        ]

        if not searchable:
            return []

        quoted_table = (
            self._quote_identifier(table)
        )

        conditions = [
            (
                f"{self._quote_identifier(column)} "
                "LIKE ?"
            )
            for column in searchable
        ]

        query = f"""
            SELECT *
            FROM {quoted_table}
            WHERE {" OR ".join(conditions)}
            ORDER BY rowid DESC
        """

        pattern = f"%{text}%"

        cursor = connection.execute(
            query,
            tuple(
                pattern
                for _ in searchable
            ),
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    # ======================================================
    # STATISTICS
    # ======================================================

    def statistics(
        self,
        table: Optional[str] = None,
    ) -> dict[str, Any]:

        table = (
            table
            or self.business_table()
        )

        if not table:
            return {}

        rows = self.records(
            table
        )

        total = len(rows)

        coordinates = 0
        phones = 0
        websites = 0

        cities: set[str] = set()
        sources: set[str] = set()
        categories: set[str] = set()

        for row in rows:

            try:

                lat = float(
                    row.get("latitude")
                )

                lon = float(
                    row.get("longitude")
                )

                if (
                    -90.0 <= lat <= 90.0
                    and
                    -180.0 <= lon <= 180.0
                ):

                    coordinates += 1

            except (
                TypeError,
                ValueError,
            ):

                pass

            if str(
                row.get("phone") or ""
            ).strip():

                phones += 1

            if str(
                row.get("website") or ""
            ).strip():

                websites += 1

            city = str(
                row.get("city") or ""
            ).strip()

            source = str(
                row.get("source") or ""
            ).strip()

            category = str(
                row.get("category") or ""
            ).strip()

            if city:
                cities.add(city)

            if source:
                sources.add(source)

            if category:
                categories.add(category)

        return {
            "total": total,
            "with_coordinates": coordinates,
            "without_coordinates": (
                total - coordinates
            ),
            "with_phone": phones,
            "without_phone": (
                total - phones
            ),
            "with_website": websites,
            "without_website": (
                total - websites
            ),
            "cities": len(cities),
            "sources": len(sources),
            "categories": len(categories),
        }

    # ======================================================
    # CONTEXT
    # ======================================================

    def __enter__(
        self,
    ) -> "DatabaseReader":

        self.open()

        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:

        self.close()


__all__ = [
    "DatabaseReader",
]