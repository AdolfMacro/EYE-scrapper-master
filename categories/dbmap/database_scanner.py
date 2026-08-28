# ==========================================================
# EYES DB MAP VIEWER — DATABASE SCANNER
# ==========================================================
#
# FILE:
#     dbmap/database_scanner.py
#
# STATUS:
#     CANONICAL / CORE
#
# ROLE:
#     Discover and identify SQLite database files inside
#     a user-selected directory.
#
# RESPONSIBILITIES
# ----------------------------------------------------------
# 1. Validate the requested directory
# 2. Discover SQLite database files
# 3. Support .db / .sqlite / .sqlite3
# 4. Verify SQLite file signatures
# 5. Inspect database tables
# 6. Return machine-readable database metadata
#
# DOES NOT:
# ----------------------------------------------------------
# ❌ Modify databases
# ❌ Insert records
# ❌ Delete records
# ❌ Modify tables
# ❌ Depend on EYES-master
# ❌ Depend on Business / School models
# ❌ Depend on PyQt
# ❌ Depend on OSM
# ❌ Render maps
#
# ARCHITECTURAL POSITION
# ----------------------------------------------------------
#
#                 User Directory
#                       │
#                       ▼
#              DatabaseScanner
#                       │
#             ┌─────────┴─────────┐
#             ▼                   ▼
#        SQLite files        Invalid files
#             │
#             ▼
#       DatabaseMetadata
#
# OUTPUT
# ----------------------------------------------------------
#
# Machine-readable metadata suitable for:
#
#     GUI
#     Database Inspector
#     Database Reader
#     Map Viewer
#
# ==========================================================

from __future__ import annotations

import os
import sqlite3

from dataclasses import (
    dataclass,
    field,
)
from pathlib import Path
from typing import (
    Iterable,
    Optional,
)


# ==========================================================
# DATABASE METADATA
# ==========================================================


@dataclass(frozen=True)
class DatabaseMetadata:
    """
    Immutable description of one discovered SQLite database.
    """

    path: str

    name: str

    size_bytes: int

    tables: tuple[str, ...] = field(
        default_factory=tuple
    )

    valid_sqlite: bool = False

    error: Optional[str] = None

    # ======================================================
    # PROPERTIES
    # ======================================================

    @property
    def table_count(self) -> int:
        """
        Return the number of discovered tables.
        """

        return len(
            self.tables
        )

    # ======================================================

    @property
    def is_readable(self) -> bool:
        """
        Return whether the database was successfully
        recognized and inspected.
        """

        return (
            self.valid_sqlite
            and self.error is None
        )

    # ======================================================

    def to_dict(self) -> dict:
        """
        Return machine-readable metadata.
        """

        return {
            "path": self.path,
            "name": self.name,
            "size_bytes": self.size_bytes,
            "tables": list(
                self.tables
            ),
            "table_count": self.table_count,
            "valid_sqlite": self.valid_sqlite,
            "is_readable": self.is_readable,
            "error": self.error,
        }


# ==========================================================
# DATABASE SCANNER
# ==========================================================


class DatabaseScanner:
    """
    Discover SQLite databases inside a directory.

    The scanner is intentionally read-only.

    Supported extensions:

        .db
        .sqlite
        .sqlite3
    """

    SUPPORTED_EXTENSIONS = frozenset(
        {
            ".db",
            ".sqlite",
            ".sqlite3",
        }
    )

    SQLITE_HEADER = (
        b"SQLite format 3\x00"
    )

    # ======================================================
    # INIT
    # ======================================================

    def __init__(
        self,
        recursive: bool = False,
    ) -> None:

        self.recursive = bool(
            recursive
        )

    # ======================================================
    # DIRECTORY VALIDATION
    # ======================================================

    @staticmethod
    def validate_directory(
        directory: str | os.PathLike,
    ) -> Path:
        """
        Validate and normalize a directory path.
        """

        path = Path(
            directory
        ).expanduser().resolve()

        if not path.exists():

            raise FileNotFoundError(
                f"Directory does not exist: "
                f"{path}"
            )

        if not path.is_dir():

            raise NotADirectoryError(
                f"Path is not a directory: "
                f"{path}"
            )

        return path

    # ======================================================
    # DISCOVER FILES
    # ======================================================

    def discover_files(
        self,
        directory: str | os.PathLike,
    ) -> list[Path]:
        """
        Discover candidate database files.

        Only files with supported SQLite extensions are
        returned.

        Results are sorted deterministically by path.
        """

        root = self.validate_directory(
            directory
        )

        if self.recursive:

            candidates = (
                path
                for path in root.rglob("*")
                if path.is_file()
            )

        else:

            candidates = (
                path
                for path in root.iterdir()
                if path.is_file()
            )

        files = []

        for path in candidates:

            if (
                path.suffix.lower()
                not in self.SUPPORTED_EXTENSIONS
            ):
                continue

            files.append(
                path
            )

        return sorted(
            files,
            key=lambda item: str(
                item
            ).casefold(),
        )

    # ======================================================
    # SQLITE SIGNATURE
    # ======================================================

    @classmethod
    def has_sqlite_signature(
        cls,
        path: Path,
    ) -> bool:
        """
        Check the SQLite file header.

        SQLite databases normally begin with:

            SQLite format 3\\x00
        """

        try:

            with path.open(
                "rb"
            ) as file:

                header = file.read(
                    len(
                        cls.SQLITE_HEADER
                    )
                )

        except (
            OSError,
            IOError,
        ):

            return False

        return (
            header
            == cls.SQLITE_HEADER
        )

    # ==========================================================
    # SQLITE VALIDATION
    # ==========================================================

    @staticmethod
    def validate_sqlite(
        path: Path,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that a file can be opened as SQLite.

        The connection is opened in read-only mode.

        No database modification is performed.
        """

        uri = (
            "file:"
            + str(
                path
            )
            + "?mode=ro"
        )

        connection = None

        try:

            connection = sqlite3.connect(
                uri,
                uri=True,
                timeout=5,
            )

            connection.execute(
                "PRAGMA schema_version"
            )

            return (
                True,
                None,
            )

        except sqlite3.Error as error:

            return (
                False,
                str(error),
            )

        finally:

            if connection is not None:

                try:

                    connection.close()

                except sqlite3.Error:

                    pass

    # ==========================================================
    # TABLE DISCOVERY
    # ==========================================================

    @staticmethod
    def discover_tables(
        path: Path,
    ) -> tuple[str, ...]:
        """
        Return user-defined SQLite tables.

        SQLite internal tables such as sqlite_sequence are
        excluded.
        """

        uri = (
            "file:"
            + str(
                path
            )
            + "?mode=ro"
        )

        connection = None

        try:

            connection = sqlite3.connect(
                uri,
                uri=True,
                timeout=5,
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

            return tuple(
                row[0]
                for row in cursor.fetchall()
            )

        finally:

            if connection is not None:

                connection.close()

    # ==========================================================
    # INSPECT ONE
    # ==========================================================

    def inspect(
        self,
        path: str | os.PathLike,
    ) -> DatabaseMetadata:
        """
        Inspect one database candidate.

        This method never modifies the database.
        """

        database_path = (
            Path(
                path
            )
            .expanduser()
            .resolve()
        )

        name = (
            database_path.name
        )

        try:

            size_bytes = (
                database_path.stat()
                .st_size
            )

        except OSError:

            size_bytes = 0

        # ------------------------------------------------------
        # File existence
        # ------------------------------------------------------

        if not database_path.exists():

            return DatabaseMetadata(
                path=str(
                    database_path
                ),
                name=name,
                size_bytes=size_bytes,
                valid_sqlite=False,
                error="FILE_NOT_FOUND",
            )

        if not database_path.is_file():

            return DatabaseMetadata(
                path=str(
                    database_path
                ),
                name=name,
                size_bytes=size_bytes,
                valid_sqlite=False,
                error="NOT_A_FILE",
            )

        # ------------------------------------------------------
        # SQLite signature
        # ------------------------------------------------------

        if not self.has_sqlite_signature(
            database_path
        ):

            return DatabaseMetadata(
                path=str(
                    database_path
                ),
                name=name,
                size_bytes=size_bytes,
                valid_sqlite=False,
                error="INVALID_SQLITE_SIGNATURE",
            )

        # ------------------------------------------------------
        # SQLite validation
        # ------------------------------------------------------

        valid, error = (
            self.validate_sqlite(
                database_path
            )
        )

        if not valid:

            return DatabaseMetadata(
                path=str(
                    database_path
                ),
                name=name,
                size_bytes=size_bytes,
                valid_sqlite=False,
                error=error
                or "INVALID_SQLITE_DATABASE",
            )

        # ------------------------------------------------------
        # Table discovery
        # ------------------------------------------------------

        try:

            tables = (
                self.discover_tables(
                    database_path
                )
            )

        except sqlite3.Error as error:

            return DatabaseMetadata(
                path=str(
                    database_path
                ),
                name=name,
                size_bytes=size_bytes,
                valid_sqlite=False,
                error=str(error),
            )

        return DatabaseMetadata(
            path=str(
                database_path
            ),
            name=name,
            size_bytes=size_bytes,
            tables=tables,
            valid_sqlite=True,
            error=None,
        )

    # ==========================================================
    # SCAN DIRECTORY
    # ==========================================================

    def scan(
        self,
        directory: str | os.PathLike,
    ) -> list[DatabaseMetadata]:
        """
        Discover and inspect all supported databases
        inside a directory.
        """

        files = self.discover_files(
            directory
        )

        results = []

        for path in files:

            results.append(
                self.inspect(
                    path
                )
            )

        return results

    # ==========================================================
    # VALID DATABASES
    # ==========================================================

    def scan_valid(
        self,
        directory: str | os.PathLike,
    ) -> list[DatabaseMetadata]:
        """
        Return only valid SQLite databases.
        """

        return [
            database
            for database in self.scan(
                directory
            )
            if database.valid_sqlite
        ]

    # ==========================================================
    # DATABASE ITERATOR
    # ==========================================================

    def iter_databases(
        self,
        directory: str | os.PathLike,
    ) -> Iterable[DatabaseMetadata]:
        """
        Lazily inspect databases one by one.
        """

        for path in self.discover_files(
            directory
        ):

            yield self.inspect(
                path
            )

    # ==========================================================
    # REPRESENTATION
    # ==========================================================

    def __repr__(
        self,
    ) -> str:

        return (
            "<DatabaseScanner "
            f"recursive={self.recursive}>"
        )


# ==========================================================
# MODULE EXPORTS
# ==========================================================

__all__ = [
    "DatabaseMetadata",
    "DatabaseScanner",
]