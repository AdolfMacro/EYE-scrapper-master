from providers.manager import ProviderManager
from database.database import Database
from scraper.engine import ScraperEngine


class ScraperController:

    def __init__(
        self,
        logger=None,
        progress=None
    ):

        self.logger = logger

        self.progress = progress

        self.provider_manager = (
            ProviderManager()
        )

        self.database = None

        self.engine = None

    # ======================================
    # START
    # ======================================

    def start(self, config):

        if self.engine:

            status = self.engine.progress()

            if status.get("running"):

                raise RuntimeError(
                    "Scraper is already running"
                )

        provider = (
            self.provider_manager.get(
                config.provider
            )
        )

        # Database is created inside the
        # worker thread by ScraperEngine.
        self.database = None

        self.engine = ScraperEngine(

            config=config,

            provider=provider,

            database=None,

            logger=self.logger,

            progress_callback=self.progress
        )

        return self.engine

    # ======================================
    # RUN
    # ======================================

    def run(self):

        if self.engine is None:

            raise RuntimeError(
                "Scraper has not been started"
            )

        return self.engine.run()

    # ======================================
    # RUN ASYNC
    # ======================================

    def run_async(
        self,
        callback=None
    ):

        if self.engine is None:

            raise RuntimeError(
                "Scraper has not been started"
            )

        return self.engine.run_async(
            callback or self.finished
        )

    # ======================================
    # STOP
    # ======================================

    def stop(self):

        if self.engine:

            self.engine.stop()

    # ======================================
    # FINISHED
    # ======================================

    def finished(self, results):

        if self.logger:

            self.logger(
                f"[DONE] {len(results)} results processed"
            )

    # ======================================
    # STATUS
    # ======================================

    def status(self):

        if self.engine:

            return self.engine.progress()

        return {

            "running": False,

            "queries": 0,

            "pages": 0,

            "results": 0,

            "total": 0
        }

    # ======================================
    # PROVIDERS
    # ======================================

    def providers(self):

        return self.provider_manager.list()