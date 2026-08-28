
import sqlite3
from pathlib import Path


class DataManager:
    """
    مدیریت دیتابیس اصلی و دیتابیس‌های Child Scraper.

    ساختار:
        data/
        ├── main.db
        └── scrapers/
            ├── scraper_a/
            │   └── scraper_a.db
            ├── scraper_b/
            │   └── scraper_b.db
            └── ...

    DataManager فقط زمانی دیتای یک Child Database را
    وارد Main Database می‌کند که کاربر آن را انتخاب
    کرده و عملیات Merge را اجرا کند.
    """

    def __init__(self, main_database="data/main.db"):
        self.main_database = Path(main_database)

        self.main_database.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self._ensure_main_database()

    # ==========================================================
    # CONNECTION
    # ==========================================================

    @staticmethod
    def _connect(database):
        """
        ایجاد اتصال SQLite.
        """

        return sqlite3.connect(
            str(database),
            timeout=30
        )

    # ==========================================================
    # MAIN DATABASE
    # ==========================================================

    def _ensure_main_database(self):
        """
        ایجاد ساختار Main Database در صورت نبودن.
        """

        with self._connect(self.main_database) as conn:

            conn.execute(
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

            conn.commit()

    # ==========================================================
    # DATABASE VALIDATION
    # ==========================================================

    def database_exists(self, database):
        """
        بررسی وجود دیتابیس.
        """

        return Path(database).is_file()

    def validate_database(self, database):
        """
        بررسی می‌کند دیتابیس انتخاب‌شده
        قابل استفاده برای Merge هست یا خیر.
        """

        database = Path(database)

        if not database.is_file():
            return False

        try:

            with self._connect(database) as conn:

                table = conn.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    AND name = 'records'
                    """
                ).fetchone()

                return table is not None

        except sqlite3.Error:
            return False

    # ==========================================================
    # DATABASE INFO
    # ==========================================================

    def inspect_database(self, database):
        """
        دریافت اطلاعات جداول و تعداد رکوردهای دیتابیس.
        """

        database = Path(database)

        if not database.is_file():
            raise FileNotFoundError(
                f"Database not found: {database}"
            )

        result = {}

        try:

            with self._connect(database) as conn:

                tables = conn.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                    """
                ).fetchall()

                for (table_name,) in tables:

                    count = conn.execute(
                        f'''
                        SELECT COUNT(*)
                        FROM "{table_name}"
                        '''
                    ).fetchone()[0]

                    result[table_name] = count

        except sqlite3.Error as exc:

            raise RuntimeError(
                f"Unable to inspect database: {exc}"
            ) from exc

        return result

    # ==========================================================
    # RECORD COUNT
    # ==========================================================

    def count_main_records(self):
        """
        تعداد رکوردهای Main Database.
        """

        return self.count_database_records(
            self.main_database
        )

    def count_database_records(self, database):
        """
        تعداد رکوردهای یک دیتابیس.
        """

        database = Path(database)

        if not database.is_file():
            return 0

        try:

            with self._connect(database) as conn:

                result = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM records
                    """
                ).fetchone()

                return result[0]

        except sqlite3.Error:
            return 0

    # ==========================================================
    # MERGE
    # ==========================================================

    def merge_database(self, child_database):
        """
        Merge فقط دیتابیس انتخاب‌شده توسط کاربر
        در Main Database.

        هیچ Merge خودکاری انجام نمی‌شود.
        """

        child_database = Path(child_database)

        if not child_database.is_file():
            raise FileNotFoundError(
                f"Child database not found: {child_database}"
            )

        if (
            child_database.resolve()
            == self.main_database.resolve()
        ):
            raise ValueError(
                "Main database cannot be merged into itself."
            )

        if not self.validate_database(child_database):
            raise ValueError(
                "Selected database has an invalid schema."
            )

        stats = {
            "source": str(child_database),
            "read": 0,
            "merged": 0,
            "duplicates": 0,
            "failed": 0,
        }

        # ------------------------------------------------------
        # Read Child Database
        # ------------------------------------------------------

        try:

            with self._connect(child_database) as source_conn:

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
        # Merge Into Main Database
        # ------------------------------------------------------

        try:

            with self._connect(self.main_database) as main_conn:

                for row in rows:

                    try:

                        data, source, scraper, created_at = row

                        # --------------------------------------
                        # Duplicate Detection
                        # --------------------------------------

                        duplicate = main_conn.execute(
                            """
                            SELECT id
                            FROM records
                            WHERE
                                data = ?
                                AND
                                COALESCE(source, '') =
                                COALESCE(?, '')
                                AND
                                COALESCE(scraper, '') =
                                COALESCE(?, '')
                            LIMIT 1
                            """,
                            (
                                data,
                                source,
                                scraper,
                            )
                        ).fetchone()

                        if duplicate:

                            stats["duplicates"] += 1
                            continue

                        # --------------------------------------
                        # Insert
                        # --------------------------------------

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
                            )
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
    # MAIN DATABASE PATH
    # ==========================================================

    def get_main_database(self):
        """
        مسیر Main Database.
        """

        return self.main_database

    # ==========================================================
    # SELECTED DATABASE INFO
    # ==========================================================

    def get_database_info(self, database):
        """
        اطلاعات خلاصه دیتابیس انتخاب‌شده.
        """

        database = Path(database)

        return {
            "path": str(database),
            "exists": database.is_file(),
            "valid": self.validate_database(database),
            "records": self.count_database_records(
                database
            ),
        }
