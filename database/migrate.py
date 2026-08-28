"""
EYES-master / database/migrate.py

ابزار مستقل مهاجرت داده‌های مدارس بین دیتابیس‌های پروژه.

مسئولیت‌ها:
    - خواندن رکوردهای مدارس از دیتابیس مبدا
    - ایجاد یک دیتابیس مقصد مستقل برای تست Migration
    - انتقال داده‌ها به ساختار مدیریت‌شده توسط DataManager
    - ثبت تعداد رکوردهای پردازش‌شده و ناموفق
    - نمایش آمار و نتیجه نهایی مهاجرت
    - انجام بررسی اولیه برای اطمینان از صحت Migration

جریان عملیات:
    data/schools.db
        ↓
    خواندن رکوردهای schools
        ↓
    تبدیل داده به ساختار School-compatible
        ↓
    DataManager.insert_school()
        ↓
    data/eye_migration_test.db

نکته:
    این فایل ابزار Migration و تست آن است و مسئول
    منطق اصلی ذخیره‌سازی نیست.
    مدیریت ساختار و عملیات دیتابیس توسط
    database.manager.DataManager انجام می‌شود.

ساختار مرتبط:
    EYES-master/
    ├── data/
    │   ├── schools.db
    │   └── eye_migration_test.db
    └── database/
        ├── manager.py
        └── migrate.py
"""

import shutil
import sqlite3
from pathlib import Path

from database.manager import DataManager


SOURCE = Path("data/schools.db")
TARGET = Path("data/eye_migration_test.db")


def main():

    if not SOURCE.exists():
        raise FileNotFoundError(
            f"Source database not found: {SOURCE}"
        )

    # --------------------------------------------------
    # Fresh test database
    # --------------------------------------------------

    if TARGET.exists():
        TARGET.unlink()

    print("=" * 60)
    print("EYE SCRAPPER DATABASE MIGRATION")
    print("=" * 60)

    # --------------------------------------------------
    # Read source
    # --------------------------------------------------

    source_db = sqlite3.connect(SOURCE)
    source_db.row_factory = sqlite3.Row

    source_count = source_db.execute(
        "SELECT COUNT(*) FROM schools"
    ).fetchone()[0]

    print(f"[SOURCE] {SOURCE}")
    print(f"[SOURCE RECORDS] {source_count}")

    # --------------------------------------------------
    # Destination
    # --------------------------------------------------

    manager = DataManager(str(TARGET))

    inserted = 0
    failed = 0

    # --------------------------------------------------
    # Migration
    # --------------------------------------------------

    rows = source_db.execute(
        """
        SELECT
            name,
            city,
            phone,
            website,
            address,
            latitude,
            longitude,
            source,
            osm_type,
            osm_id,
            created_at,
            updated_at
        FROM schools
        """
    )

    for index, row in enumerate(rows, start=1):

        try:

            school = {
                "name": row["name"] or "",
                "category": "",
                "keyword": "",
                "province": "",
                "city": row["city"] or "",
                "address": row["address"] or "",
                "phone": row["phone"] or "",
                "website": row["website"] or "",
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "source": row["source"] or "",
                "osm_type": row["osm_type"] or "",
                "osm_id": row["osm_id"],
                "created_at": row["created_at"],
            }

            manager.insert_school(school)
            inserted += 1

        except Exception as error:

            failed += 1

            print(
                f"[FAILED] #{index} "
                f"{row['name']!r}: {error}"
            )

    # --------------------------------------------------
    # Results
    # --------------------------------------------------

    destination_count = manager.count()

    print()
    print("=" * 60)
    print("MIGRATION RESULT")
    print("=" * 60)

    print(f"SOURCE RECORDS      : {source_count}")
    print(f"PROCESSED           : {inserted}")
    print(f"FAILED              : {failed}")
    print(f"DESTINATION RECORDS : {destination_count}")

    print()
    print("STATISTICS:")
    print(manager.statistics())

    # --------------------------------------------------
    # Safety check
    # --------------------------------------------------

    if failed == 0 and destination_count <= source_count:
        print()
        print("[OK] Migration completed.")
    else:
        print()
        print("[WARNING] Review migration result.")

    manager.close()
    source_db.close()


if __name__ == "__main__":
    main()
