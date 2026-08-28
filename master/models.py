# ============================================================
# EYES MASTER — SCRAPER MODELS
# ============================================================
#
# FILE:
#     master/models.py
#
# ROLE:
#     Core data model for one EYE scraper.
#
# RESPONSIBILITIES:
#     - Identity
#     - Provider configuration
#     - Scraper configuration
#     - Runtime process metadata
#     - Lifecycle state
#     - Lifecycle timestamps
#     - Serialization / restoration
#     - Validation
#     - Immutable-style snapshots/copies
#
# DOES NOT:
#     - Create processes
#     - Start processes
#     - Stop processes
#     - Execute providers
#     - Perform scraping
#     - Access Registry
#
# CONTRACT:
#
#     ScraperInfo
#         ↓
#     Persistent logical state
#
#     ScraperProcess
#         ↓
#     Runtime process state
#
#     ScraperRegistry
#         ↓
#     Persistence / coordination metadata
#
# ============================================================

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import time


# ============================================================
# STATUS
# ============================================================


class ScraperStatus(str, Enum):
    """
    Lifecycle states of a scraper.
    """

    CREATED = "CREATED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FINISHED = "FINISHED"
    CRASHED = "CRASHED"
    KILLED = "KILLED"


# ============================================================
# MODEL
# ============================================================


@dataclass
class ScraperInfo:
    """
    Persistent logical model for one scraper.

    ScraperInfo contains metadata only.

    It does not own or control a real process.
    """

    # ========================================================
    # IDENTITY
    # ========================================================

    name: str

    # ========================================================
    # CONFIGURATION
    # ========================================================

    providers: list[str] = field(
        default_factory=list
    )

    target: Optional[str] = None

    config: dict[str, Any] = field(
        default_factory=dict
    )

    # ========================================================
    # RUNTIME FILES
    # ========================================================

    database: Optional[str] = None

    log_file: Optional[str] = None

    scraper_dir: Optional[str] = None

    # ========================================================
    # PROCESS METADATA
    # ========================================================

    pid: Optional[int] = None

    status: ScraperStatus = (
        ScraperStatus.CREATED
    )

    exit_code: Optional[int] = None

    error: Optional[str] = None

    # ========================================================
    # TIMESTAMPS
    # ========================================================

    created_at: float = field(
        default_factory=time.time
    )

    started_at: Optional[float] = None

    stopped_at: Optional[float] = None

    finished_at: Optional[float] = None

    updated_at: float = field(
        default_factory=time.time
    )

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __post_init__(self) -> None:

        # ----------------------------------------------------
        # NAME
        # ----------------------------------------------------

        self.name = str(
            self.name
        ).strip()

        # ----------------------------------------------------
        # PROVIDERS
        # ----------------------------------------------------

        if self.providers is None:

            self.providers = []

        self.providers = [
            str(provider).strip().lower()
            for provider in self.providers
            if str(provider).strip()
        ]

        # ----------------------------------------------------
        # CONFIG
        # ----------------------------------------------------

        if self.config is None:

            self.config = {}

        if not isinstance(
            self.config,
            dict,
        ):

            raise TypeError(
                "config must be a dictionary."
            )

        self.config = dict(
            self.config
        )

        # ----------------------------------------------------
        # OPTIONAL STRINGS
        # ----------------------------------------------------

        if self.target is not None:

            self.target = str(
                self.target
            ).strip()

            if not self.target:

                self.target = None

        if self.database is not None:

            self.database = str(
                self.database
            ).strip()

            if not self.database:

                self.database = None

        if self.log_file is not None:

            self.log_file = str(
                self.log_file
            ).strip()

            if not self.log_file:

                self.log_file = None

        if self.scraper_dir is not None:

            self.scraper_dir = str(
                self.scraper_dir
            ).strip()

            if not self.scraper_dir:

                self.scraper_dir = None

        # ----------------------------------------------------
        # PID
        # ----------------------------------------------------

        if self.pid is not None:

            try:

                self.pid = int(
                    self.pid
                )

            except (
                TypeError,
                ValueError,
            ):

                self.pid = None

        # ----------------------------------------------------
        # EXIT CODE
        # ----------------------------------------------------

        if self.exit_code is not None:

            try:

                self.exit_code = int(
                    self.exit_code
                )

            except (
                TypeError,
                ValueError,
            ):

                self.exit_code = None

        # ----------------------------------------------------
        # ERROR
        # ----------------------------------------------------

        if self.error is not None:

            self.error = str(
                self.error
            )

        # ----------------------------------------------------
        # TIMESTAMPS
        # ----------------------------------------------------

        self.created_at = (
            self._required_float(
                self.created_at,
                default=time.time(),
            )
        )

        self.started_at = (
            self._optional_float(
                self.started_at
            )
        )

        self.stopped_at = (
            self._optional_float(
                self.stopped_at
            )
        )

        self.finished_at = (
            self._optional_float(
                self.finished_at
            )
        )

        self.updated_at = (
            self._required_float(
                self.updated_at,
                default=time.time(),
            )
        )

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        self.status = (
            self.normalize_status(
                self.status
            )
        )

    # ========================================================
    # STATUS NORMALIZATION
    # ========================================================

    @staticmethod
    def normalize_status(
        status: ScraperStatus | str,
    ) -> ScraperStatus:
        """
        Normalize a lifecycle status.

        Accepts:

            ScraperStatus.RUNNING
            "RUNNING"
            "running"
            " Running "
        """

        if isinstance(
            status,
            ScraperStatus,
        ):

            return status

        if status is None:

            raise ValueError(
                "Scraper status cannot be None."
            )

        value = str(
            status
        ).strip().upper()

        try:

            return ScraperStatus(
                value
            )

        except ValueError as exc:

            raise ValueError(
                f"Invalid scraper status: {status!r}. "
                f"Expected one of: "
                f"{', '.join(item.value for item in ScraperStatus)}"
            ) from exc

    # ========================================================
    # SET STATUS
    # ========================================================

    def set_status(
        self,
        status: ScraperStatus | str,
        error: Optional[str] = None,
        exit_code: Optional[int] = None,
    ) -> None:
        """
        Update lifecycle state and related metadata.
        """

        normalized = (
            self.normalize_status(
                status
            )
        )

        now = time.time()

        self.status = normalized

        self.updated_at = now

        # ----------------------------------------------------
        # ERROR
        # ----------------------------------------------------

        if error is not None:

            self.error = str(
                error
            )

        # ----------------------------------------------------
        # EXIT CODE
        # ----------------------------------------------------

        if exit_code is not None:

            try:

                self.exit_code = int(
                    exit_code
                )

            except (
                TypeError,
                ValueError,
            ):

                raise ValueError(
                    "exit_code must be an integer."
                )

        # ----------------------------------------------------
        # START
        # ----------------------------------------------------

        if normalized == ScraperStatus.STARTING:

            if self.started_at is None:

                self.started_at = now

        elif normalized == ScraperStatus.RUNNING:

            if self.started_at is None:

                self.started_at = now

        # ----------------------------------------------------
        # STOP
        # ----------------------------------------------------

        elif normalized in {
            ScraperStatus.STOPPING,
            ScraperStatus.STOPPED,
            ScraperStatus.KILLED,
        }:

            if self.stopped_at is None:

                self.stopped_at = now

        # ----------------------------------------------------
        # FINISH / CRASH
        # ----------------------------------------------------

        elif normalized in {
            ScraperStatus.FINISHED,
            ScraperStatus.CRASHED,
        }:

            if self.finished_at is None:

                self.finished_at = now

        # ----------------------------------------------------
        # CRASH
        # ----------------------------------------------------

        if normalized == ScraperStatus.CRASHED:

            if error is None:

                if self.error is None:

                    self.error = (
                        "Scraper process crashed."
                    )

        # ----------------------------------------------------
        # CLEAR ERROR ON NORMAL START
        # ----------------------------------------------------

        if normalized in {
            ScraperStatus.STARTING,
            ScraperStatus.RUNNING,
        }:

            if error is None:

                self.error = None

    # ========================================================
    # STATE HELPERS
    # ========================================================

    @property
    def is_running(self) -> bool:

        return (
            self.status
            == ScraperStatus.RUNNING
        )

    @property
    def is_starting(self) -> bool:

        return (
            self.status
            == ScraperStatus.STARTING
        )

    @property
    def is_stopping(self) -> bool:

        return (
            self.status
            == ScraperStatus.STOPPING
        )

    @property
    def is_active(self) -> bool:
        """
        Logical lifecycle is still active.

        CREATED is intentionally included because
        the scraper exists but has not finished yet.
        """

        return self.status in {
            ScraperStatus.CREATED,
            ScraperStatus.STARTING,
            ScraperStatus.RUNNING,
            ScraperStatus.STOPPING,
        }

    @property
    def is_finished(self) -> bool:

        return self.status in {
            ScraperStatus.STOPPED,
            ScraperStatus.FINISHED,
            ScraperStatus.CRASHED,
            ScraperStatus.KILLED,
        }

    @property
    def has_failed(self) -> bool:

        return (
            self.status
            == ScraperStatus.CRASHED
        )

    @property
    def has_pid(self) -> bool:

        return self.pid is not None

    # ========================================================
    # CONFIGURATION SNAPSHOT
    # ========================================================

    def configuration(
        self,
    ) -> dict[str, Any]:
        """
        Return configuration only.

        Lifecycle/process metadata are excluded.
        """

        return {
            "name": self.name,

            "providers": list(
                self.providers
            ),

            "target": self.target,

            "config": dict(
                self.config
            ),

            "database": self.database,

            "log_file": self.log_file,

            "scraper_dir": self.scraper_dir,
        }

    # ========================================================
    # SERIALIZATION
    # ========================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Convert model into JSON-safe data.
        """

        return {
            "name": self.name,

            "providers": list(
                self.providers
            ),

            "target": self.target,

            "config": dict(
                self.config
            ),

            "database": self.database,

            "log_file": self.log_file,

            "scraper_dir": self.scraper_dir,

            "pid": self.pid,

            "status": self.status.value,

            "exit_code": self.exit_code,

            "error": self.error,

            "created_at": self.created_at,

            "started_at": self.started_at,

            "stopped_at": self.stopped_at,

            "finished_at": self.finished_at,

            "updated_at": self.updated_at,
        }

    # ========================================================
    # SNAPSHOT
    # ========================================================

    def snapshot(
        self,
    ) -> dict[str, Any]:

        return dict(
            self.to_dict()
        )

    # ========================================================
    # DESERIALIZATION
    # ========================================================

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "ScraperInfo":
        """
        Restore ScraperInfo from persisted JSON data.
        """

        if not isinstance(
            data,
            dict,
        ):

            raise TypeError(
                "ScraperInfo data must be a dictionary."
            )

        providers = data.get(
            "providers",
            [],
        )

        if providers is None:

            providers = []

        if isinstance(
            providers,
            str,
        ):

            providers = [
                providers
            ]

        elif not isinstance(
            providers,
            (list, tuple, set),
        ):

            raise TypeError(
                "providers must be a string "
                "or a collection of strings."
            )

        config = data.get(
            "config",
            {},
        )

        if config is None:

            config = {}

        if not isinstance(
            config,
            dict,
        ):

            raise TypeError(
                "config must be a dictionary."
            )

        return cls(

            name=data.get(
                "name",
                "",
            ),

            providers=list(
                providers
            ),

            target=data.get(
                "target"
            ),

            config=dict(
                config
            ),

            database=data.get(
                "database"
            ),

            log_file=data.get(
                "log_file"
            ),

            scraper_dir=data.get(
                "scraper_dir"
            ),

            pid=data.get(
                "pid"
            ),

            status=cls.normalize_status(
                data.get(
                    "status",
                    ScraperStatus.CREATED.value,
                )
            ),

            exit_code=data.get(
                "exit_code"
            ),

            error=data.get(
                "error"
            ),

            created_at=cls._required_float(
                data.get(
                    "created_at"
                ),
                default=time.time(),
            ),

            started_at=cls._optional_float(
                data.get(
                    "started_at"
                )
            ),

            stopped_at=cls._optional_float(
                data.get(
                    "stopped_at"
                )
            ),

            finished_at=cls._optional_float(
                data.get(
                    "finished_at"
                )
            ),

            updated_at=cls._required_float(
                data.get(
                    "updated_at"
                ),
                default=time.time(),
            ),
        )

    # ========================================================
    # COPY
    # ========================================================

    def copy(
        self,
    ) -> "ScraperInfo":
        """
        Return an independent model copy.
        """

        return ScraperInfo.from_dict(
            self.to_dict()
        )

    # ========================================================
    # VALIDATION
    # ========================================================

    def validate(self) -> None:
        """
        Validate the model contract.

        This method does not modify the object.
        """

        if not self.name:

            raise ValueError(
                "Scraper name cannot be empty."
            )

        if not isinstance(
            self.providers,
            list,
        ):

            raise TypeError(
                "providers must be a list."
            )

        if not self.providers:

            raise ValueError(
                "At least one provider is required."
            )

        for provider in self.providers:

            if not isinstance(
                provider,
                str,
            ):

                raise TypeError(
                    "Provider names must be strings."
                )

            if not provider.strip():

                raise ValueError(
                    "Provider names cannot be empty."
                )

        if not isinstance(
            self.config,
            dict,
        ):

            raise TypeError(
                "config must be a dictionary."
            )

        if self.pid is not None:

            if (
                not isinstance(
                    self.pid,
                    int,
                )
                or self.pid <= 0
            ):

                raise ValueError(
                    "pid must be a positive integer "
                    "or None."
                )

        if self.exit_code is not None:

            if not isinstance(
                self.exit_code,
                int,
            ):

                raise ValueError(
                    "exit_code must be an integer "
                    "or None."
                )

        self.normalize_status(
            self.status
        )

    # ========================================================
    # TIMESTAMP HELPERS
    # ========================================================

    @staticmethod
    def _optional_float(
        value: Any,
    ) -> Optional[float]:
        """
        Safely convert an optional timestamp.
        """

        if value is None:

            return None

        if value == "":

            return None

        try:

            return float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return None

    @staticmethod
    def _required_float(
        value: Any,
        default: float,
    ) -> float:
        """
        Convert timestamp to float.

        Invalid or missing values fall back
        to the supplied default.
        """

        if value is None:

            return float(
                default
            )

        if value == "":

            return float(
                default
            )

        try:

            return float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return float(
                default
            )

    # ========================================================
    # REPRESENTATION
    # ========================================================

    def __repr__(
        self,
    ) -> str:

        return (
            "<ScraperInfo "
            f"name={self.name!r} "
            f"status={self.status.value!r} "
            f"pid={self.pid!r} "
            f"providers={self.providers!r}>"
        )