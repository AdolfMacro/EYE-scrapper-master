from __future__ import annotations

from typing import List, Optional

from .models import ScraperInfo, ScraperStatus
from .scraper_registry import ScraperRegistry
from .process_manager import ProcessManager


class MasterController:
    """
    High-level controller for EYE Master.

    Responsibilities:

        - Create scraper definitions
        - Start scrapers
        - Stop scrapers
        - Remove scrapers
        - Restart scrapers
        - Query scraper state
        - Refresh runtime state

    Architecture:

        MasterController
              |
              +-- ScraperRegistry
              |
              +-- ProcessManager
                        |
                        +-- ScraperProcess

    MasterController does NOT:
        - execute scraping logic
        - execute providers
        - directly manage multiprocessing.Process
        - access scraper databases
    """

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

    def __init__(
        self,
        registry: Optional[ScraperRegistry] = None,
        process_manager: Optional[ProcessManager] = None,
    ) -> None:

        # ------------------------------------------------------
        # REGISTRY
        # ------------------------------------------------------

        self.registry = (
            registry
            if registry is not None
            else ScraperRegistry()
        )

        # ------------------------------------------------------
        # PROCESS MANAGER
        # ------------------------------------------------------
        #
        # IMPORTANT:
        # ProcessManager MUST use the exact same registry
        # instance as MasterController.
        #

        self.process_manager = (
            process_manager
            if process_manager is not None
            else ProcessManager(
                registry=self.registry
            )
        )

        # ------------------------------------------------------
        # SAFETY
        # ------------------------------------------------------

        if (
            self.process_manager.registry
            is not self.registry
        ):
            raise ValueError(
                "ProcessManager must use the same "
                "ScraperRegistry instance as MasterController."
            )

    # ==========================================================
    # CREATE
    # ==========================================================

    def create_scraper(
        self,
        name: str,
        provider: str,
        target: str,
        keyword: str,
    ) -> ScraperInfo:
        """
        Create a new scraper.

        Contract:

            exactly one provider
            exactly one required keyword
        """

        name = str(name).strip()
        provider = str(provider).strip().lower()
        target = str(target).strip()
        keyword = str(keyword).strip()

        # ------------------------------------------------------
        # VALIDATION
        # ------------------------------------------------------

        if not name:
            raise ValueError(
                "Scraper name cannot be empty."
            )

        if not provider:
            raise ValueError(
                "Provider cannot be empty."
            )

        if not keyword:
            raise ValueError(
                "Scraper keyword cannot be empty."
            )

        if self.registry.exists(name):
            raise ValueError(
                f"Scraper already exists: {name}"
            )

        # ------------------------------------------------------
        # CONFIG
        # ------------------------------------------------------

        config = {
            "keyword": keyword,
        }

        if target:
            config["target"] = target

        # ------------------------------------------------------
        # PROCESS MANAGER
        # ------------------------------------------------------
        #
        # ProcessManager.create() is responsible for:
        #
        #   - filesystem paths
        #   - ScraperProcess construction
        #   - registry registration
        #   - runtime process object
        #

        self.process_manager.create(
            name=name,
            providers=[provider],
            target=target or None,
            config=config,
        )

        # ------------------------------------------------------
        # RETURN PERSISTED MODEL
        # ------------------------------------------------------

        scraper = self.registry.get(name)

        if scraper is None:
            raise RuntimeError(
                f"Scraper '{name}' was created but "
                "could not be retrieved from registry."
            )

        return scraper

    # ==========================================================
    # CREATE FROM INFO
    # ==========================================================

    def create_from_info(
        self,
        scraper: ScraperInfo,
    ) -> ScraperInfo:
        """
        Create a runtime scraper from an existing ScraperInfo.

        The information is persisted through ProcessManager.
        """

        if not isinstance(
            scraper,
            ScraperInfo,
        ):
            raise TypeError(
                "scraper must be a ScraperInfo instance."
            )

        if self.registry.exists(
            scraper.name
        ):
            raise ValueError(
                f"Scraper already exists: "
                f"{scraper.name}"
            )

        self.process_manager.create_from_info(
            scraper
        )

        restored = self.registry.get(
            scraper.name
        )

        if restored is None:
            raise RuntimeError(
                f"Scraper '{scraper.name}' was created "
                "but could not be restored."
            )

        return restored

    # ==========================================================
    # START
    # ==========================================================

    def start_scraper(
        self,
        name: str,
    ) -> ScraperInfo:

        scraper = self._require_scraper(
            name
        )

        if scraper.status == (
            ScraperStatus.RUNNING
        ):
            return scraper

        try:

            self.process_manager.start(
                scraper.name
            )

        except Exception as exc:

            # ProcessManager already synchronizes
            # registry state on start failure.

            refreshed = self.registry.get(
                scraper.name
            )

            if refreshed is not None:
                return refreshed

            raise RuntimeError(
                f"Failed to start scraper "
                f"'{scraper.name}': {exc}"
            ) from exc

        result = self.registry.get(
            scraper.name
        )

        if result is None:
            raise RuntimeError(
                f"Scraper '{scraper.name}' disappeared "
                "from registry after start."
            )

        return result

    # ==========================================================
    # STOP
    # ==========================================================

    def stop_scraper(
        self,
        name: str,
        timeout: float = 10.0,
    ) -> ScraperInfo:

        scraper = self._require_scraper(
            name
        )

        if scraper.status not in {
            ScraperStatus.RUNNING,
            ScraperStatus.STARTING,
            ScraperStatus.STOPPING,
        }:
            return scraper

        stopped = self.process_manager.stop(
            scraper.name,
            timeout=timeout,
        )

        if not stopped:
            raise RuntimeError(
                f"Could not stop scraper "
                f"'{scraper.name}'."
            )

        result = self.registry.get(
            scraper.name
        )

        if result is None:
            raise RuntimeError(
                f"Scraper '{scraper.name}' disappeared "
                "from registry after stop."
            )

        return result

    # ==========================================================
    # KILL
    # ==========================================================

    def kill_scraper(
        self,
        name: str,
        timeout: float = 3.0,
    ) -> ScraperInfo:

        scraper = self._require_scraper(
            name
        )

        self.process_manager.kill(
            scraper.name,
            timeout=timeout,
        )

        result = self.registry.get(
            scraper.name
        )

        if result is None:
            raise RuntimeError(
                f"Scraper '{scraper.name}' disappeared "
                "from registry after kill."
            )

        return result

    # ==========================================================
    # RESTART
    # ==========================================================

    def restart_scraper(
        self,
        name: str,
        timeout: float = 10.0,
    ) -> ScraperInfo:

        scraper = self._require_scraper(
            name
        )

        self.process_manager.restart(
            scraper.name,
            timeout=timeout,
        )

        result = self.registry.get(
            scraper.name
        )

        if result is None:
            raise RuntimeError(
                f"Scraper '{scraper.name}' disappeared "
                "from registry after restart."
            )

        return result

    # ==========================================================
    # FORCE RESTART
    # ==========================================================

    def force_restart_scraper(
        self,
        name: str,
        stop_timeout: float = 5.0,
        kill_timeout: float = 3.0,
    ) -> ScraperInfo:

        scraper = self._require_scraper(
            name
        )

        self.process_manager.restart_force(
            scraper.name,
            stop_timeout=stop_timeout,
            kill_timeout=kill_timeout,
        )

        result = self.registry.get(
            scraper.name
        )

        if result is None:
            raise RuntimeError(
                f"Scraper '{scraper.name}' disappeared "
                "from registry after force restart."
            )

        return result

    # ==========================================================
    # REMOVE
    # ==========================================================

    def remove_scraper(
        self,
        name: str,
    ) -> None:

        scraper = self._require_scraper(
            name
        )

        # ------------------------------------------------------
        # PROCESS MANAGER owns process removal.
        # It also removes the registry record.
        # ------------------------------------------------------

        self.process_manager.remove(
            scraper.name,
            force=True,
        )

    # ==========================================================
    # GET
    # ==========================================================

    def get_scraper(
        self,
        name: str,
    ) -> Optional[ScraperInfo]:

        return self.registry.get(
            name
        )

    # ==========================================================
    # LIST
    # ==========================================================

    def list_scrapers(
        self,
    ) -> List[ScraperInfo]:

        return self.registry.all()

    # ==========================================================
    # RUNNING
    # ==========================================================

    def running_scrapers(
        self,
    ) -> List[ScraperInfo]:

        return self.registry.running()

    # ==========================================================
    # ACTIVE
    # ==========================================================

    def active_scrapers(
        self,
    ) -> List[ScraperInfo]:

        return self.registry.active()

    # ==========================================================
    # CRASHED
    # ==========================================================

    def crashed_scrapers(
        self,
    ) -> List[ScraperInfo]:

        return self.registry.crashed()

    # ==========================================================
    # FINISHED
    # ==========================================================

    def finished_scrapers(
        self,
    ) -> List[ScraperInfo]:

        return self.registry.finished()

    # ==========================================================
    # REFRESH
    # ==========================================================

    def refresh_status(
        self,
        name: Optional[str] = None,
    ) -> None:
        """
        Synchronize runtime process state with registry.
        """

        self.process_manager.refresh(
            name
        )

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(
        self,
        name: str,
    ) -> dict:
        """
        Return stable structured runtime snapshot.
        """

        self._require_scraper(
            name
        )

        return self.process_manager.snapshot(
            name
        )

    # ==========================================================
    # SNAPSHOTS
    # ==========================================================

    def snapshots(
        self,
    ) -> list[dict]:

        return self.process_manager.snapshots()

    # ==========================================================
    # STATUS
    # ==========================================================

    def status(
        self,
        name: str,
    ) -> ScraperStatus:

        self._require_scraper(
            name
        )

        return self.process_manager.status(
            name
        )

    # ==========================================================
    # COUNT
    # ==========================================================

    def count(
        self,
    ) -> int:

        return self.registry.count()

    # ==========================================================
    # SHUTDOWN
    # ==========================================================

    def shutdown(
        self,
        timeout: float = 10.0,
    ) -> None:
        """
        Shutdown all runtime scraper processes.

        Registry metadata is preserved.
        """

        self.process_manager.shutdown(
            timeout=timeout
        )

    # ==========================================================
    # REMOVE ALL
    # ==========================================================

    def remove_all(
        self,
        force: bool = False,
        timeout: float = 10.0,
    ) -> None:

        self.process_manager.remove_all(
            force=force,
            timeout=timeout,
        )

    # ==========================================================
    # INTERNAL
    # ==========================================================

    def _require_scraper(
        self,
        name: str,
    ) -> ScraperInfo:

        name = str(
            name
        ).strip()

        if not name:
            raise ValueError(
                "Scraper name cannot be empty."
            )

        scraper = self.registry.get(
            name
        )

        if scraper is None:
            raise KeyError(
                f"Scraper '{name}' does not exist."
            )

        return scraper

    # ==========================================================
    # REPRESENTATION
    # ==========================================================

    def __repr__(
        self,
    ) -> str:

        return (
            f"<MasterController "
            f"scrapers={self.count()}>"
        )