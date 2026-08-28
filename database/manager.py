"""
EYES-master / database/manager.py

Central Data Manager for EYES.

Responsibilities
----------------
- Manage SQLite databases inside data/
- Open and switch between databases safely
- Discover databases and text files
- Inspect tables and columns
- Read/search arbitrary SQLite tables
- Manage the canonical schools.db database
- CRUD operations for schools
- Detect missing school fields
- Provide database/table statistics
- Provide compatibility methods for older project code
- Provide safe SQLite access for worker/background threads

Architecture
------------
database/database.py
    Canonical persistence layer.

database/manager.py
    Data Manager / Data Access Layer.

GUI
    Uses this class for database discovery, inspection,
    searching and school-data management.

Important
---------
This class does NOT contain:
- scraper logic
- provider logic
- GUI logic
- process management
"""

from __future__ import annotations

import sqlite3
import threading

from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


class DataManager:
    """
    Central SQLite data manager for EYES.

    Default database:

        data/schools.db

    Other databases in data/ can be opened and inspected without
    automatically modifying their schema.

    The canonical `schools` table is created ONLY inside schools.db.
    """

    # ==========================================================
    # CONSTANTS
    # ==========================================================

    SCHOOL_DATABASE_NAME = "schools.db"

    SCHOOL_TABLE = "schools"

    SUPPORTED_MISSING_FIELDS = {
        "phone",
        "website",
        "address",
        "province",
        "city",
    }

    SCHOOL_FIELDS = {
        "name",
        "category",
        "keyword",
        "province",
        "city",
        "address",
        "phone",
        "website",
        "latitude",
        "longitude",
        "distance_km",
        "source",
        "source_id",
        "osm_type",
        "osm_id",
    }

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(
        self,
        path: str | Path = "data/schools.db",
        data_dir: str | Path | None = None,
    ) -> None:

        self.lock = threading.RLock()

        # ------------------------------------------------------
        # Resolve data directory
        # ------------------------------------------------------

        if data_dir is None:

            path_obj = Path(path)

            if path_obj.is_absolute():

                data_dir = path_obj.parent

            else:

                # Normal project usage:
                #
                # data/schools.db
                #
                # => data/

                parent = path_obj.parent

                if str(parent) == ".":
                    data_dir = Path("data")
                else:
                    data_dir = parent

        self.data_dir = Path(data_dir).expanduser()

        self.data_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ------------------------------------------------------
        # Connection state
        # ------------------------------------------------------

        self.connection: sqlite3.Connection | None = None

        self.current_database: Path | None = None

        self.current_table: str | None = None

        self.path: str = ""

        # ------------------------------------------------------
        # Open default database
        # ------------------------------------------------------

        self.open_database(path)

        # ------------------------------------------------------
        # Canonical school schema
        # ------------------------------------------------------

        if self.is_school_database():
            self.create_tables()

    # ==========================================================
    # PATH RESOLUTION
    # ==========================================================

    def _resolve_database_path(
        self,
        database: str | Path,
    ) -> Path:
        """
        Resolve a database path without accidentally creating:

            data/data/file.db
        """

        path = Path(database).expanduser()

        if path.is_absolute():
            return path

        # If caller explicitly supplied something like:
        #
        # data/results.db
        #
        # preserve it as-is.

        if path.parts and path.parts[0] == self.data_dir.name:
            return path

        # Otherwise treat a relative filename as belonging to data/.

        if len(path.parts) == 1:
            return self.data_dir / path

        return path

    # ==========================================================
    # CONNECTION
    # ==========================================================

    @staticmethod
    def _connect(
        database: str | Path,
    ) -> sqlite3.Connection:
        """
        Create a SQLite connection.

        check_same_thread=False is intentional because the manager
        may be used by GUI + worker infrastructure.

        Access is still serialized by self.lock.
        """

        connection = sqlite3.connect(
            str(database),
            timeout=30,
            check_same_thread=False,
        )

        connection.row_factory = sqlite3.Row

        # Improve behavior under concurrent SQLite access.

        connection.execute(
            "PRAGMA busy_timeout = 30000"
        )

        return connection

    # ==========================================================
    # OPEN DATABASE
    # ==========================================================

    def open_database(
        self,
        database: str | Path,
    ) -> sqlite3.Connection:
        """
        Open and activate a SQLite database.

        Does NOT automatically create the schools schema unless
        the selected database is schools.db.
        """

        with self.lock:

            path = self._resolve_database_path(database)

            if path.suffix.lower() != ".db":

                raise ValueError(
                    "Only SQLite .db files are supported."
                )

            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            # --------------------------------------------------
            # Close previous connection
            # --------------------------------------------------

            self._close_connection_only()

            # --------------------------------------------------
            # Connect
            # --------------------------------------------------

            self.connection = self._connect(path)

            self.current_database = path

            self.path = str(path)

            self.current_table = None

            # --------------------------------------------------
            # Only create canonical schema in schools.db
            # --------------------------------------------------

            if self.is_school_database():
                self.create_tables()

            return self.connection

    # ==========================================================
    # CONNECT ALIAS
    # ==========================================================

    def connect(
        self,
        database: str | Path,
    ) -> sqlite3.Connection:
        """
        Backwards-compatible alias for open_database().
        """

        return self.open_database(database)

    # ==========================================================
    # CURRENT DATABASE
    # ==========================================================

    def current_database_name(self) -> str | None:

        if self.current_database is None:
            return None

        return self.current_database.name

    # ==========================================================

    def get_main_database(self) -> Path:

        if self.current_database is None:
            raise RuntimeError(
                "No database is currently open."
            )

        return self.current_database

    # ==========================================================
    # DATABASE TYPE
    # ==========================================================

    def is_school_database(self) -> bool:

        if self.current_database is None:
            return False

        return (
            self.current_database.name.lower()
            == self.SCHOOL_DATABASE_NAME
        )

    # ==========================================================
    # DATABASE EXISTENCE
    # ==========================================================

    def database_exists(
        self,
        database: str | Path,
    ) -> bool:

        path = self._resolve_database_path(database)

        return path.is_file()

    # ==========================================================
    # DATABASE VALIDATION
    # ==========================================================

    def validate_database(
        self,
        database: str | Path,
    ) -> bool:
        """
        Validate that a file is a readable SQLite database.

        If the database contains `records`, it is considered compatible
        with the legacy generic DataManager API.

        A schools database is also valid.
        """

        path = self._resolve_database_path(database)

        if not path.is_file():
            return False

        try:

            with self._connect(path) as connection:

                connection.execute(
                    "SELECT name FROM sqlite_master LIMIT 1"
                ).fetchone()

                return True

        except sqlite3.Error:
            return False

    # ==========================================================
    # DATABASE SIZE
    # ==========================================================

    def database_size(
        self,
        database: str | Path | None = None,
    ) -> int:

        if database is None:

            if self.current_database is None:
                return 0

            path = self.current_database

        else:

            path = self._resolve_database_path(database)

        try:
            return path.stat().st_size
        except OSError:
            return 0

    # ==========================================================
    # DATABASE DISCOVERY
    # ==========================================================

    def list_databases(self) -> list[dict[str, Any]]:

        if not self.data_dir.exists():
            return []

        result = []

        for path in sorted(
            self.data_dir.glob("*.db"),
            key=lambda item: item.name.lower(),
        ):

            try:
                size = path.stat().st_size
            except OSError:
                size = 0

            result.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "size": size,
                    "valid": self.validate_database(path),
                }
            )

        return result

    # ==========================================================

    def database_names(self) -> list[str]:

        return [
            item["name"]
            for item in self.list_databases()
        ]

    # ==========================================================
    # DATA FILE DISCOVERY
    # ==========================================================

    def list_text_files(self) -> list[dict[str, Any]]:

        if not self.data_dir.exists():
            return []

        result = []

        for path in sorted(
            self.data_dir.glob("*.txt"),
            key=lambda item: item.name.lower(),
        ):

            try:
                size = path.stat().st_size
            except OSError:
                size = 0

            result.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "type": "text",
                    "size": size,
                }
            )

        return result

    # ==========================================================

    def list_data_files(self) -> list[dict[str, Any]]:

        result = []

        result.extend(
            {
                **item,
                "type": "database",
            }
            for item in self.list_databases()
        )

        result.extend(
            self.list_text_files()
        )

        return result

    # ==========================================================
    # CREATE CANONICAL SCHOOL TABLE
    # ==========================================================

    def create_tables(self) -> None:
        """
        Create the canonical schools schema.

        IMPORTANT:
        Never inject this schema into arbitrary databases.
        """

        with self.lock:

            self._require_connection()

            if not self.is_school_database():
                return

            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schools (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    name TEXT NOT NULL,

                    category TEXT DEFAULT '',

                    keyword TEXT DEFAULT '',

                    province TEXT DEFAULT '',

                    city TEXT DEFAULT '',

                    address TEXT DEFAULT '',

                    phone TEXT DEFAULT '',

                    website TEXT DEFAULT '',

                    latitude REAL,

                    longitude REAL,

                    distance_km REAL DEFAULT 0,

                    source TEXT DEFAULT '',

                    source_id TEXT DEFAULT '',

                    osm_type TEXT DEFAULT '',

                    osm_id INTEGER,

                    created_at TEXT NOT NULL,

                    updated_at TEXT NOT NULL,

                    UNIQUE(name, city, address)
                )
                """
            )

            self.connection.commit()

    # ==========================================================
    # ENSURE SCHOOL TABLE
    # ==========================================================

    def _ensure_schools_table(self) -> None:

        self._require_connection()

        if not self.is_school_database():

            raise RuntimeError(
                "School operations are only available "
                "on schools.db."
            )

        self.create_tables()

    # ==========================================================
    # TABLE DISCOVERY
    # ==========================================================

    def list_tables(
        self,
        database: str | Path | None = None,
    ) -> list[str]:

        with self.lock:

            if database is not None:
                self.open_database(database)

            self._require_connection()

            rows = self.connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()

            return [
                row["name"]
                for row in rows
            ]

    # ==========================================================

    def get_database_tables(self) -> list[str]:

        if self.connection is None:
            return []

        return self.list_tables()

    # ==========================================================
    # TABLE VALIDATION
    # ==========================================================

    def _validate_table(
        self,
        table: str,
    ) -> None:

        if not isinstance(table, str):
            raise TypeError(
                "Table name must be a string."
            )

        table = table.strip()

        if not table:
            raise ValueError(
                "Table name cannot be empty."
            )

        if table not in self.list_tables():

            raise ValueError(
                f"Unknown table: {table}"
            )

    # ==========================================================
    # TABLE INFO
    # ==========================================================

    def table_info(
        self,
        table: str,
    ) -> list[dict[str, Any]]:

        with self.lock:

            self._require_connection()

            self._validate_table(table)

            rows = self.connection.execute(
                f'PRAGMA table_info("{table}")'
            ).fetchall()

            return [
                dict(row)
                for row in rows
            ]

    # ==========================================================
    # COLUMNS
    # ==========================================================

    def columns(
        self,
        table: str,
    ) -> list[str]:

        return [
            item["name"]
            for item in self.table_info(table)
        ]

    # ==========================================================
    # COUNT TABLE
    # ==========================================================

    def count(
        self,
        table: str = "schools",
    ) -> int:

        with self.lock:

            self._require_connection()

            self._validate_table(table)

            row = self.connection.execute(
                f'''
                SELECT COUNT(*) AS total
                FROM "{table}"
                '''
            ).fetchone()

            return int(
                row["total"]
            )

    # ==========================================================
    # COUNT CURRENT DATABASE RECORDS
    # ==========================================================

    def count_database_records(
        self,
        database: str | Path,
    ) -> int:

        path = self._resolve_database_path(database)

        if not path.is_file():
            return 0

        try:

            with self._connect(path) as connection:

                tables = connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    AND name NOT LIKE 'sqlite_%'
                    """
                ).fetchall()

                total = 0

                for row in tables:

                    table = row["name"]

                    result = connection.execute(
                        f'''
                        SELECT COUNT(*)
                        FROM "{table}"
                        '''
                    ).fetchone()

                    total += int(result[0])

                return total

        except sqlite3.Error:
            return 0

    # ==========================================================
    # MAIN RECORD COUNT
    # ==========================================================

    def count_main_records(self) -> int:

        if self.current_database is None:
            return 0

        return self.count_database_records(
            self.current_database
        )

    # ==========================================================
    # DATABASE STATISTICS
    # ==========================================================

    def database_statistics(
        self,
        database: str | Path | None = None,
    ) -> dict[str, Any]:

        with self.lock:

            if database is not None:
                self.open_database(database)

            self._require_connection()

            tables = self.list_tables()

            table_data = []

            total_records = 0

            for table in tables:

                try:
                    records = self.count(table)
                except Exception:
                    records = 0

                total_records += records

                table_data.append(
                    {
                        "name": table,
                        "records": records,
                    }
                )

            return {
                "database": (
                    self.current_database.name
                    if self.current_database
                    else ""
                ),
                "path": self.path,
                "tables": len(tables),
                "records": total_records,
                "table_data": table_data,
                "size": self.database_size(),
            }

    # ==========================================================

    def table_statistics(self) -> list[dict[str, Any]]:

        return [
            {
                "name": table,
                "records": self.count(table),
            }
            for table in self.list_tables()
        ]

    # ==========================================================
    # DATABASE INFO
    # ==========================================================

    def database_info(
        self,
        database: str | Path | None = None,
    ) -> dict[str, Any]:

        with self.lock:

            if database is not None:
                self.open_database(database)

            if self.connection is None:
                return {}

            result = {
                "database": (
                    self.current_database.name
                    if self.current_database
                    else ""
                ),
                "path": self.path,
                "size": self.database_size(),
                "tables": [],
            }

            for table in self.list_tables():

                result["tables"].append(
                    {
                        "name": table,
                        "columns": self.columns(table),
                        "records": self.count(table),
                    }
                )

            return result

    # ==========================================================
    # INSPECT DATABASE
    # ==========================================================

    def inspect_database(
        self,
        database: str | Path,
    ) -> dict[str, int]:

        path = self._resolve_database_path(database)

        if not path.is_file():

            raise FileNotFoundError(
                f"Database not found: {path}"
            )

        result: dict[str, int] = {}

        try:

            with self._connect(path) as connection:

                tables = connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                    """
                ).fetchall()

                for row in tables:

                    table = row["name"]

                    count = connection.execute(
                        f'''
                        SELECT COUNT(*)
                        FROM "{table}"
                        '''
                    ).fetchone()[0]

                    result[table] = int(count)

        except sqlite3.Error as exc:

            raise RuntimeError(
                f"Unable to inspect database: {exc}"
            ) from exc

        return result

    # ==========================================================
    # FETCH ROWS
    # ==========================================================

    def fetch_rows(
        self,
        table: str,
        limit: int = 500,
        offset: int = 0,
    ) -> list[dict[str, Any]]:

        with self.lock:

            self._require_connection()

            self._validate_table(table)

            limit = max(
                1,
                int(limit),
            )

            offset = max(
                0,
                int(offset),
            )

            rows = self.connection.execute(
                f'''
                SELECT *
                FROM "{table}"
                LIMIT ?
                OFFSET ?
                ''',
                (
                    limit,
                    offset,
                ),
            ).fetchall()

            self.current_table = table

            return [
                dict(row)
                for row in rows
            ]

    # ==========================================================
    # SEARCH TABLE
    # ==========================================================

    def search_table(
        self,
        table: str,
        text: str = "",
        limit: int = 500,
    ) -> list[dict[str, Any]]:

        with self.lock:

            self._require_connection()

            self._validate_table(table)

            text = str(
                text or ""
            ).strip()

            limit = max(
                1,
                int(limit),
            )

            columns = self.columns(table)

            if not columns:
                return []

            if not text:

                return self.fetch_rows(
                    table,
                    limit=limit,
                )

            conditions = [
                f'CAST("{column}" AS TEXT) LIKE ?'
                for column in columns
            ]

            parameters = [
                f"%{text}%"
                for _ in columns
            ]

            parameters.append(limit)

            query = f'''
                SELECT *
                FROM "{table}"
                WHERE {" OR ".join(conditions)}
                LIMIT ?
            '''

            rows = self.connection.execute(
                query,
                parameters,
            ).fetchall()

            self.current_table = table

            return [
                dict(row)
                for row in rows
            ]

    # ==========================================================
    # GENERIC GET ALL
    # ==========================================================

    def get_all(
        self,
        table: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:

        if table is None:
            table = self.current_table

        if table is None:

            tables = self.list_tables()

            if not tables:
                return []

            table = tables[0]

        return self.fetch_rows(
            table,
            limit=limit,
        )

    # ==========================================================
    # GENERIC SEARCH
    # ==========================================================

    def search(
        self,
        text: str,
        table: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:

        if table is None:
            table = self.current_table

        if table is None:

            tables = self.list_tables()

            if not tables:
                return []

            table = tables[0]

        return self.search_table(
            table,
            text,
            limit,
        )

    # ==========================================================
    # INSERT SCHOOL
    # ==========================================================

    def insert_school(
        self,
        school: Any,
    ) -> int:

        data = self._to_dict(school)

        name = str(
            data.get("name", "")
            or ""
        ).strip()

        if not name:

            raise ValueError(
                "School name cannot be empty."
            )

        now = datetime.now().isoformat()

        query = """
            INSERT INTO schools (

                name,
                category,
                keyword,
                province,
                city,
                address,
                phone,
                website,
                latitude,
                longitude,
                distance_km,
                source,
                source_id,
                osm_type,
                osm_id,
                created_at,
                updated_at

            )

            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?
            )

            ON CONFLICT(name, city, address)

            DO UPDATE SET

                category =
                    CASE
                        WHEN excluded.category != ''
                        THEN excluded.category
                        ELSE schools.category
                    END,

                keyword =
                    CASE
                        WHEN excluded.keyword != ''
                        THEN excluded.keyword
                        ELSE schools.keyword
                    END,

                province =
                    CASE
                        WHEN excluded.province != ''
                        THEN excluded.province
                        ELSE schools.province
                    END,

                phone =
                    CASE
                        WHEN excluded.phone != ''
                        THEN excluded.phone
                        ELSE schools.phone
                    END,

                website =
                    CASE
                        WHEN excluded.website != ''
                        THEN excluded.website
                        ELSE schools.website
                    END,

                address =
                    CASE
                        WHEN excluded.address != ''
                        THEN excluded.address
                        ELSE schools.address
                    END,

                latitude =
                    CASE
                        WHEN excluded.latitude IS NOT NULL
                        THEN excluded.latitude
                        ELSE schools.latitude
                    END,

                longitude =
                    CASE
                        WHEN excluded.longitude IS NOT NULL
                        THEN excluded.longitude
                        ELSE schools.longitude
                    END,

                distance_km =
                    CASE
                        WHEN excluded.distance_km IS NOT NULL
                        THEN excluded.distance_km
                        ELSE schools.distance_km
                    END,

                source =
                    CASE
                        WHEN excluded.source != ''
                        THEN excluded.source
                        ELSE schools.source
                    END,

                source_id =
                    CASE
                        WHEN excluded.source_id != ''
                        THEN excluded.source_id
                        ELSE schools.source_id
                    END,

                osm_type =
                    CASE
                        WHEN excluded.osm_type != ''
                        THEN excluded.osm_type
                        ELSE schools.osm_type
                    END,

                osm_id =
                    CASE
                        WHEN excluded.osm_id IS NOT NULL
                        THEN excluded.osm_id
                        ELSE schools.osm_id
                    END,

                updated_at = excluded.updated_at
        """

        values = (
            name,
            data.get("category", ""),
            data.get("keyword", ""),
            data.get("province", ""),
            data.get("city", ""),
            data.get("address", ""),
            data.get("phone", ""),
            data.get("website", ""),
            self._float(data.get("latitude")),
            self._float(data.get("longitude")),
            self._float(data.get("distance_km")),
            data.get("source", ""),
            data.get("source_id", ""),
            data.get("osm_type", ""),
            self._int(data.get("osm_id")),
            data.get("created_at") or now,
            now,
        )

        with self.lock:

            self._ensure_schools_table()

            cursor = self.connection.execute(
                query,
                values,
            )

            self.connection.commit()

            # SQLite lastrowid may be zero for an UPSERT.
            if cursor.lastrowid:
                return int(cursor.lastrowid)

            row = self.connection.execute(
                """
                SELECT id
                FROM schools
                WHERE name = ?
                AND city = ?
                AND address = ?
                LIMIT 1
                """,
                (
                    name,
                    data.get("city", ""),
                    data.get("address", ""),
                ),
            ).fetchone()

            return (
                int(row["id"])
                if row
                else 0
            )

    # ==========================================================
    # GET SCHOOL
    # ==========================================================

    def get_school(
        self,
        school_id: int,
    ) -> dict[str, Any] | None:

        with self.lock:

            self._ensure_schools_table()

            row = self.connection.execute(
                """
                SELECT *
                FROM schools
                WHERE id = ?
                """,
                (school_id,),
            ).fetchone()

            return (
                dict(row)
                if row
                else None
            )

    # ==========================================================
    # GET ALL SCHOOLS
    # ==========================================================

    def get_all_schools(
        self,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:

        with self.lock:

            self._ensure_schools_table()

            if limit is None:

                rows = self.connection.execute(
                    """
                    SELECT *
                    FROM schools
                    ORDER BY id DESC
                    """
                ).fetchall()

            else:

                limit = max(
                    1,
                    int(limit),
                )

                rows = self.connection.execute(
                    """
                    SELECT *
                    FROM schools
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

            return [
                dict(row)
                for row in rows
            ]

    # ==========================================================
    # SEARCH SCHOOLS
    # ==========================================================

    def search_schools(
        self,
        text: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:

        text = str(
            text or ""
        ).strip()

        if not text:

            return self.get_all_schools(
                limit=limit
            )

        pattern = f"%{text}%"

        with self.lock:

            self._ensure_schools_table()

            query = """
                SELECT *
                FROM schools

                WHERE name LIKE ?
                OR category LIKE ?
                OR keyword LIKE ?
                OR province LIKE ?
                OR city LIKE ?
                OR phone LIKE ?
                OR website LIKE ?
                OR address LIKE ?
                OR source LIKE ?

                ORDER BY id DESC
            """

            parameters = (
                pattern,
                pattern,
                pattern,
                pattern,
                pattern,
                pattern,
                pattern,
                pattern,
                pattern,
            )

            if limit is not None:

                query += " LIMIT ?"

                parameters = (
                    *parameters,
                    max(1, int(limit)),
                )

            rows = self.connection.execute(
                query,
                parameters,
            ).fetchall()

            return [
                dict(row)
                for row in rows
            ]

    # ==========================================================
    # UPDATE SCHOOL
    # ==========================================================

    def update_school(
        self,
        school_id: int,
        **fields: Any,
    ) -> bool:

        fields = {
            key: value
            for key, value in fields.items()
            if key in self.SCHOOL_FIELDS
        }

        if not fields:
            return False

        # Normalize numeric fields.

        if "latitude" in fields:
            fields["latitude"] = self._float(
                fields["latitude"]
            )

        if "longitude" in fields:
            fields["longitude"] = self._float(
                fields["longitude"]
            )

        if "distance_km" in fields:
            fields["distance_km"] = self._float(
                fields["distance_km"]
            )

        if "osm_id" in fields:
            fields["osm_id"] = self._int(
                fields["osm_id"]
            )

        fields["updated_at"] = (
            datetime.now().isoformat()
        )

        assignments = ", ".join(
            f'"{key}" = ?'
            for key in fields
        )

        values = list(
            fields.values()
        )

        values.append(
            school_id
        )

        with self.lock:

            self._ensure_schools_table()

            cursor = self.connection.execute(
                f"""
                UPDATE schools
                SET {assignments}
                WHERE id = ?
                """,
                values,
            )

            self.connection.commit()

            return cursor.rowcount > 0

    # ==========================================================
    # DELETE SCHOOL
    # ==========================================================

    def delete_school(
        self,
        school_id: int,
    ) -> bool:

        with self.lock:

            self._ensure_schools_table()

            cursor = self.connection.execute(
                """
                DELETE FROM schools
                WHERE id = ?
                """,
                (school_id,),
            )

            self.connection.commit()

            return cursor.rowcount > 0

    # ==========================================================
    # SCHOOL COUNT
    # ==========================================================

    def school_count(self) -> int:

        with self.lock:

            self._ensure_schools_table()

            row = self.connection.execute(
                """
                SELECT COUNT(*)
                FROM schools
                """
            ).fetchone()

            return int(row[0])

    # ==========================================================
    # LEGACY COUNT
    # ==========================================================

    def count_schools(self) -> int:
        return self.school_count()

    # ==========================================================
    # MISSING FIELD
    # ==========================================================

    def missing_field(
        self,
        field: str,
        table: str = "schools",
    ) -> list[dict[str, Any]]:

        if field not in self.SUPPORTED_MISSING_FIELDS:

            raise ValueError(
                f"Unsupported field: {field}"
            )

        with self.lock:

            self._require_connection()

            self._validate_table(table)

            rows = self.connection.execute(
                f'''
                SELECT *
                FROM "{table}"
                WHERE
                    "{field}" IS NULL
                    OR TRIM(
                        CAST("{field}" AS TEXT)
                    ) = ''
                ORDER BY id DESC
                '''
            ).fetchall()

            return [
                dict(row)
                for row in rows
            ]

    # ==========================================================
    # LEGACY MISSING METHODS
    # ==========================================================

    def missing_phone(self):
        return self.missing_field("phone")

    # ==========================================================

    def missing_website(self):
        return self.missing_field("website")

    # ==========================================================

    def missing_address(self):
        return self.missing_field("address")

    # ==========================================================
    # MULTIPLE MISSING FIELDS
    # ==========================================================

    def missing_fields(
        self,
        fields: Iterable[str],
        table: str = "schools",
    ) -> list[dict[str, Any]]:

        normalized = [
            str(field).strip()
            for field in fields
            if str(field).strip()
        ]

        for field in normalized:

            if field not in self.SUPPORTED_MISSING_FIELDS:

                raise ValueError(
                    f"Unsupported field: {field}"
                )

        if not normalized:

            return self.fetch_rows(table)

        with self.lock:

            self._require_connection()

            self._validate_table(table)

            conditions = []

            for field in normalized:

                conditions.append(
                    f"""
                    (
                        "{field}" IS NULL
                        OR TRIM(
                            CAST("{field}" AS TEXT)
                        ) = ''
                    )
                    """
                )

            query = f"""
                SELECT *
                FROM "{table}"
                WHERE {" OR ".join(conditions)}
                ORDER BY id DESC
            """

            rows = self.connection.execute(
                query
            ).fetchall()

            return [
                dict(row)
                for row in rows
            ]

    # ==========================================================
    # STATISTICS
    # ==========================================================

    def statistics(self) -> dict[str, int]:

        with self.lock:

            self._ensure_schools_table()

            total = self.school_count()

            phone = self.connection.execute(
                """
                SELECT COUNT(*)
                FROM schools
                WHERE TRIM(
                    COALESCE(phone, '')
                ) != ''
                """
            ).fetchone()[0]

            website = self.connection.execute(
                """
                SELECT COUNT(*)
                FROM schools
                WHERE TRIM(
                    COALESCE(website, '')
                ) != ''
                """
            ).fetchone()[0]

            address = self.connection.execute(
                """
                SELECT COUNT(*)
                FROM schools
                WHERE TRIM(
                    COALESCE(address, '')
                ) != ''
                """
            ).fetchone()[0]

            return {
                "total": int(total),

                "with_phone": int(phone),
                "without_phone": int(total - phone),

                "with_website": int(website),
                "without_website": int(total - website),

                "with_address": int(address),
                "without_address": int(total - address),
            }

    # ==========================================================
    # TEXT FILE READ
    # ==========================================================

    def read_text_file(
        self,
        filename: str | Path,
    ) -> str:

        path = Path(filename).expanduser()

        if not path.is_absolute():

            if len(path.parts) == 1:
                path = self.data_dir / path

        if not path.is_file():

            raise FileNotFoundError(
                f"File not found: {path}"
            )

        return path.read_text(
            encoding="utf-8"
        )

    # ==========================================================
    # TEXT FILE WRITE
    # ==========================================================

    def write_text_file(
        self,
        filename: str | Path,
        content: str,
    ) -> Path:

        path = Path(filename).expanduser()

        if not path.is_absolute():

            if len(path.parts) == 1:
                path = self.data_dir / path

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            str(content),
            encoding="utf-8",
        )

        return path

    # ==========================================================
    # GENERIC RECORDS API
    # ==========================================================

    def _has_table(
        self,
        table: str,
    ) -> bool:

        if self.connection is None:
            return False

        return table in self.list_tables()

    # ==========================================================

    def validate_records_database(
        self,
        database: str | Path,
    ) -> bool:

        path = self._resolve_database_path(database)

        if not path.is_file():
            return False

        try:

            with self._connect(path) as connection:

                row = connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    AND name = 'records'
                    """
                ).fetchone()

                return row is not None

        except sqlite3.Error:
            return False

    # ==========================================================
    # MERGE GENERIC RECORD DATABASE
    # ==========================================================

    def merge_database(
        self,
        child_database: str | Path,
        main_database: str | Path | None = None,
    ) -> dict[str, Any]:
        """
        Merge a generic `records` database into another `records`
        database.

        This operation is explicit.

        No automatic database merge is performed.
        """

        child = self._resolve_database_path(
            child_database
        )

        if main_database is None:

            main = self._resolve_database_path(
                self.SCHOOL_DATABASE_NAME
            )

        else:

            main = self._resolve_database_path(
                main_database
            )

        if not child.is_file():

            raise FileNotFoundError(
                f"Child database not found: {child}"
            )

        if child.resolve() == main.resolve():

            raise ValueError(
                "Main database cannot be merged into itself."
            )

        if not self.validate_records_database(child):

            raise ValueError(
                "Selected child database does not contain "
                "a compatible records table."
            )

        main.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        stats = {
            "source": str(child),
            "destination": str(main),
            "read": 0,
            "merged": 0,
            "duplicates": 0,
            "failed": 0,
        }

        # ------------------------------------------------------
        # Ensure destination records schema
        # ------------------------------------------------------

        try:

            with self._connect(main) as main_conn:

                main_conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS records (

                        id INTEGER PRIMARY KEY AUTOINCREMENT,

                        data TEXT,

                        source TEXT,

                        scraper TEXT,

                        created_at TIMESTAMP
                            DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                main_conn.commit()

        except sqlite3.Error as exc:

            raise RuntimeError(
                f"Unable to prepare main database: {exc}"
            ) from exc

        # ------------------------------------------------------
        # Read child
        # ------------------------------------------------------

        try:

            with self._connect(child) as source_conn:

                rows = source_conn.execute(
                    """
                    SELECT
                        data,
                        source,
                        scraper,
                        created_at
                    FROM records
                    """
                ).fetchall()

        except sqlite3.Error as exc:

            raise RuntimeError(
                f"Unable to read child database: {exc}"
            ) from exc

        stats["read"] = len(rows)

        # ------------------------------------------------------
        # Merge
        # ------------------------------------------------------

        try:

            with self._connect(main) as main_conn:

                for row in rows:

                    data = row["data"]
                    source = row["source"]
                    scraper = row["scraper"]
                    created_at = row["created_at"]

                    duplicate = main_conn.execute(
                        """
                        SELECT id
                        FROM records
                        WHERE data = ?
                        AND COALESCE(source, '') =
                            COALESCE(?, '')
                        AND COALESCE(scraper, '') =
                            COALESCE(?, '')
                        LIMIT 1
                        """,
                        (
                            data,
                            source,
                            scraper,
                        ),
                    ).fetchone()

                    if duplicate:

                        stats["duplicates"] += 1
                        continue

                    try:

                        main_conn.execute(
                            """
                            INSERT INTO records (
                                data,
                                source,
                                scraper,
                                created_at
                            )
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                data,
                                source,
                                scraper,
                                created_at,
                            ),
                        )

                        stats["merged"] += 1

                    except sqlite3.Error:

                        stats["failed"] += 1

                main_conn.commit()

        except sqlite3.Error as exc:

            raise RuntimeError(
                f"Unable to merge database: {exc}"
            ) from exc

        return stats

    # ==========================================================
    # DATABASE SUMMARY
    # ==========================================================

    def get_database_info(
        self,
        database: str | Path,
    ) -> dict[str, Any]:

        path = self._resolve_database_path(
            database
        )

        return {
            "path": str(path),
            "name": path.name,
            "exists": path.is_file(),
            "valid": self.validate_database(path),
            "records": self.count_database_records(path),
            "size": (
                path.stat().st_size
                if path.is_file()
                else 0
            ),
        }

    # ==========================================================
    # INTERNAL: REQUIRE CONNECTION
    # ==========================================================

    def _require_connection(self) -> None:

        if self.connection is None:

            raise RuntimeError(
                "No database is currently open."
            )

    # ==========================================================
    # INTERNAL: CLOSE CONNECTION
    # ==========================================================

    def _close_connection_only(self) -> None:

        if self.connection is None:
            return

        try:
            self.connection.close()
        except Exception:
            pass

        self.connection = None

    # ==========================================================
    # INTERNAL: TO DICT
    # ==========================================================

    @staticmethod
    def _to_dict(
        school: Any,
    ) -> dict[str, Any]:

        if hasattr(
            school,
            "to_dict",
        ):

            data = school.to_dict()

        elif isinstance(
            school,
            dict,
        ):

            data = dict(school)

        else:

            raise TypeError(
                "School must be a dict or provide to_dict()."
            )

        # Backwards compatibility:
        #
        # title -> name

        if (
            "title" in data
            and "name" not in data
        ):

            data["name"] = data["title"]

        return data

    # ==========================================================
    # INTERNAL: FLOAT
    # ==========================================================

    @staticmethod
    def _float(
        value: Any,
    ) -> float | None:

        if value in (
            None,
            "",
        ):
            return None

        try:
            return float(value)
        except (
            TypeError,
            ValueError,
        ):
            return None

    # ==========================================================
    # INTERNAL: INT
    # ==========================================================

    @staticmethod
    def _int(
        value: Any,
    ) -> int | None:

        if value in (
            None,
            "",
        ):
            return None

        try:
            return int(value)
        except (
            TypeError,
            ValueError,
        ):
            return None

    # ==========================================================
    # CLOSE
    # ==========================================================

    def close(self) -> None:

        with self.lock:

            self._close_connection_only()

            self.current_database = None

            self.current_table = None

            self.path = ""

    # ==========================================================
    # CONTEXT MANAGER
    # ==========================================================

    def __enter__(self) -> "DataManager":

        return self

    # ==========================================================

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:

        self.close()

    # ==========================================================
    # DESTRUCTOR
    # ==========================================================

    def __del__(self) -> None:

        try:
            self.close()
        except Exception:
            pass