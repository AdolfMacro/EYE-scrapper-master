from __future__ import annotations

from typing import Any, Optional


class ScraperProcessAdapter:
    """
    Adapter ساده برای اجرای Worker در لایه Scraper.

    نکته:
        multiprocessing توسط master.ScraperProcess مدیریت می‌شود.
        این کلاس فقط configuration و Worker را به هم متصل می‌کند.

    Architecture:

        Master
          |
          +-- ScraperProcess
                |
                +-- ScraperWorker
                      |
                      +-- ScraperProcessAdapter
                            |
                            +-- Worker
    """

    def __init__(
        self,
        name: str,
        providers: list[str] | str,
        database: str,
        config: Optional[dict[str, Any]] = None,
        log_file: Optional[str] = None,
        scraper_dir: Optional[str] = None,
    ):

        self.name = name
        self.providers = providers
        self.database = database
        self.config = dict(config or {})
        self.log_file = log_file
        self.scraper_dir = scraper_dir

        self.worker = None

    # ==========================================================
    # BUILD WORKER
    # ==========================================================

    def build_worker(self):

        from scraper.worker import ScraperWorker

        self.worker = ScraperWorker(
            name=self.name,
            providers=self.providers,
            database=self.database,
            config=self.config,
            log_file=self.log_file,
            scraper_dir=self.scraper_dir,
        )

        return self.worker

    # ==========================================================
    # RUN
    # ==========================================================

    def run(self):

        if self.worker is None:
            self.build_worker()

        return self.worker.run()

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(self) -> dict[str, Any]:

        if self.worker is None:
            return {
                "name": self.name,
                "providers": self.providers,
                "database": self.database,
                "running": False,
                "initialized": False,
            }

        return self.worker.snapshot()

    # ==========================================================
    # LOG
    # ==========================================================

    def log(self, message: Any) -> None:

        if self.worker is None:
            self.build_worker()

        self.worker.log(message)

    # ==========================================================
    # REPRESENTATION
    # ==========================================================

    def __repr__(self) -> str:

        return (
            f"<ScraperProcessAdapter "
            f"name={self.name!r} "
            f"providers={self.providers!r}>"
        )