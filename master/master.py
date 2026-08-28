
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .process_manager import ProcessManager
from .scraper_registry import ScraperRegistry


class Master:
    """
    EYE Master Controller

    Master فقط مسئول orchestration است.

        GUI
          ↓
        Master
          ↓
        ProcessManager
          ↓
        ScraperProcess
          ↓
        ScraperWorker
          ↓
        Provider / ScraperEngine

    Master مستقیماً Process یا Provider اجرا نمی‌کند.
    """

    def __init__(
        self,
        runtime_dir: Optional[str | Path] = None,
    ) -> None:

        # ======================================================
        # PATHS
        # ======================================================

        self.base_dir = (
            Path(__file__)
            .resolve()
            .parent
            .parent
        )

        self.runtime_dir = Path(
            runtime_dir
            if runtime_dir is not None
            else self.base_dir / "runtime"
        ).resolve()

        self.runtime_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ======================================================
        # REGISTRY
        # ======================================================

        self.registry = ScraperRegistry(
            self.runtime_dir / "scrapers.json"
        )

        # ======================================================
        # PROCESS MANAGER
        # ======================================================

        self.process_manager = ProcessManager(
            registry=self.registry,
            runtime_dir=self.runtime_dir,
        )

    # ==========================================================
    # CREATE SCRAPER
    # ==========================================================

    def create_scraper(
        self,
        name: str,
        provider: str,
        database: str,
        config: Optional[dict[str, Any]] = None,
        log_file: Optional[str] = None,
        scraper_dir: Optional[str] = None,
    ):
        """
        ساخت یک Child Scraper.

        Master در اینجا فقط ورودی عمومی را
        به قرارداد ProcessManager تبدیل می‌کند.

        هر Child فعلاً یک Provider دارد.
        """

        name = str(name).strip()
        provider = str(provider).strip().lower()

        if not name:
            raise ValueError(
                "Scraper name is required."
            )

        if not provider:
            raise ValueError(
                "Provider is required."
            )

        if not database:
            raise ValueError(
                "Database is required."
            )

        return self.process_manager.create(
            name=name,
            providers=[provider],
            database=str(database),
            config=config,
            log_file=log_file,
            scraper_dir=scraper_dir,
        )

    # ==========================================================
    # START
    # ==========================================================

    def start_scraper(
        self,
        name: str,
    ):
        """
        Start یک Child Scraper.
        """

        return self.process_manager.start(
            str(name).strip()
        )

    # ==========================================================
    # STOP
    # ==========================================================

    def stop_scraper(
        self,
        name: str,
        timeout: float = 10.0,
    ):
        """
        Graceful stop برای یک Child.
        """

        return self.process_manager.stop(
            str(name).strip(),
            timeout=timeout,
        )

    # ==========================================================
    # KILL
    # ==========================================================

    def kill_scraper(
        self,
        name: str,
        timeout: float = 3.0,
    ):
        """
        Forced termination برای یک Child.
        """

        return self.process_manager.kill(
            str(name).strip(),
            timeout=timeout,
        )

    # ==========================================================
    # RESTART
    # ==========================================================

    def restart_scraper(
        self,
        name: str,
        timeout: float = 10.0,
    ):
        """
        Restart یک Child Scraper.
        """

        return self.process_manager.restart(
            str(name).strip(),
            timeout=timeout,
        )

    # ==========================================================
    # DELETE
    # ==========================================================

    def delete_scraper(
        self,
        name: str,
        force: bool = False,
    ) -> bool:
        """
        حذف Child Scraper.

        force=False:
            اگر Process فعال باشد، حذف انجام نمی‌شود.

        force=True:
            Process ابتدا terminate/kill می‌شود
            و سپس حذف انجام می‌شود.

        منطق واقعی حذف در ProcessManager است.
        """

        return self.process_manager.remove(
            str(name).strip(),
            force=force,
        )

    # ==========================================================
    # STATUS
    # ==========================================================

    def get_status(
        self,
        name: str,
    ) -> dict[str, Any]:
        """
        وضعیت کامل یک Scraper.

        اطلاعات persistent از Registry
        و وضعیت runtime از ProcessManager گرفته می‌شود.
        """

        name = str(name).strip()

        record = self.registry.get(name)

        if record is None:
            raise KeyError(
                f"Scraper '{name}' does not exist."
            )

        process = self.process_manager.get(name)

        result = dict(record)

        if process is None:
            result.update(
                {
                    "alive": False,
                    "started": False,
                    "terminated": False,
                }
            )

            return result

        snapshot = process.snapshot()

        result.update(
            {
                "alive": snapshot.get(
                    "alive",
                    process.is_alive(),
                ),
                "started": snapshot.get(
                    "started",
                    False,
                ),
                "terminated": snapshot.get(
                    "terminated",
                    False,
                ),
            }
        )

        return result

    # ==========================================================
    # LIST
    # ==========================================================

    def list_scrapers(
        self,
    ) -> list[dict[str, Any]]:
        """
        لیست تمام Scraperها.

        Registry منبع اطلاعات persistent است.
        ProcessManager وضعیت runtime را تکمیل می‌کند.
        """

        result: list[dict[str, Any]] = []

        for record in self.registry.all():

            name = record.get("name")

            if not name:
                continue

            item = dict(record)

            process = self.process_manager.get(
                name
            )

            if process is not None:

                item.update(
                    {
                        "alive": process.is_alive(),
                        "pid": process.pid,
                        "exit_code": process.exitcode,
                    }
                )

            else:

                item.update(
                    {
                        "alive": False,
                        "pid": record.get("pid"),
                        "exit_code": record.get(
                            "exit_code"
                        ),
                    }
                )

            result.append(item)

        return result

    # ==========================================================
    # RUNNING
    # ==========================================================

    def running_scrapers(
        self,
    ) -> list[dict[str, Any]]:
        """
        فقط Scraperهایی که واقعاً در Runtime
        در حال اجرا هستند.

        Registry به‌تنهایی منبع قابل اعتماد
        برای وضعیت زنده Process نیست.
        """

        result: list[dict[str, Any]] = []

        for item in self.list_scrapers():

            if item.get("alive") is True:
                result.append(item)

        return result

    # ==========================================================
    # ACTIVE
    # ==========================================================

    def active_scrapers(
        self,
    ) -> list[dict[str, Any]]:
        """
        Scraperهای فعال از دید Lifecycle.

        وضعیت‌های فعال:

            CREATED
            STARTING
            RUNNING
            STOPPING
        """

        active_states = {
            "CREATED",
            "STARTING",
            "RUNNING",
            "STOPPING",
        }

        result: list[dict[str, Any]] = []

        for item in self.list_scrapers():

            state = str(
                item.get("status")
                or item.get("state")
                or ""
            ).upper()

            if state in active_states:
                result.append(item)

        return result

    # ==========================================================
    # LOGS
    # ==========================================================

    def get_logs(
        self,
        name: str,
    ) -> list[str]:
        """
        دریافت Log فایل Child.

        اگر مسیر Log نسبی باشد،
        نسبت به runtime_dir تفسیر می‌شود.

        اگر مسیر absolute باشد،
        بدون تغییر استفاده می‌شود.
        """

        name = str(name).strip()

        record = self.registry.get(name)

        if record is None:
            raise KeyError(
                f"Scraper '{name}' does not exist."
            )

        log_file = record.get("log_file")

        if not log_file:
            return []

        path = Path(log_file)

        if not path.is_absolute():
            path = self.runtime_dir / path

        path = path.resolve()

        if not path.is_file():
            return []

        try:
            return path.read_text(
                encoding="utf-8"
            ).splitlines()

        except (OSError, UnicodeError):
            return []

    # ==========================================================
    # DATABASES
    # ==========================================================

    def databases(
        self,
    ):
        """
        دریافت Databaseهای ثبت‌شده برای Childها.
        """

        return self.registry.databases()

    # ==========================================================
    # STOP ALL
    # ==========================================================

    def stop_all(
        self,
        timeout: float = 10.0,
    ):
        """
        Graceful stop برای تمام Childها.
        """

        return self.process_manager.stop_all(
            timeout=timeout
        )

    # ==========================================================
    # KILL ALL
    # ==========================================================

    def kill_all(self):
        """
        Forced termination برای تمام Childها.
        """

        return self.process_manager.kill_all()

    # ==========================================================
    # EXISTS
    # ==========================================================

    def exists(
        self,
        name: str,
    ) -> bool:
        """
        بررسی وجود Scraper در Registry.
        """

        return self.registry.exists(
            str(name).strip()
        )

    # ==========================================================
    # GET PROCESS
    # ==========================================================

    def get_process(
        self,
        name: str,
    ):
        """
        دسترسی به Process runtime مربوط به یک Scraper.

        این متد برای موارد مدیریتی/GUI است.
        """

        return self.process_manager.get(
            str(name).strip()
        )

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def shutdown(
        self,
        timeout: float = 10.0,
    ) -> None:
        """
        خاموش کردن کامل Master.

        تمام lifecycle management
        به ProcessManager واگذار می‌شود.
        """

        self.process_manager.shutdown(
            timeout=timeout
        )

    # ==========================================================
    # CONTEXT MANAGER
    # ==========================================================

    def __enter__(self) -> Master:
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback_value,
    ) -> None:

        self.shutdown()
