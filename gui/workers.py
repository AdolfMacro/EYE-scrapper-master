# ==========================================================
# وضعیت فعلی فایل
# ==========================================================

# FILE:
# scraper_worker.py
#
# STATUS:
# 🟢 سالم
#
# ROLE:
# Worker لایه GUI برای اجرای عملیات یک Scraper از طریق
# ProcessManager خارج از Thread اصلی Qt.
#
# CURRENT STATE:
# Worker فقط orchestration سطح GUI را انجام می‌دهد و هیچ
# منطق Scraper، Provider، Database یا Process را مستقیماً
# مدیریت نمی‌کند. تمام عملیات اجرایی به ProcessManager
# واگذار می‌شوند.
#
# PROBLEMS:
# 1. cancel در نسخه قبلی فقط یک flag بود و در اجرای operation
#    هیچ نقشی نداشت.
# 2. مدیریت timeout بین operationهای مختلف پراکنده بود.
# 3. result دریافت می‌شد ولی هیچ قرارداد مشخصی برای خروجی
#    وجود نداشت.
# 4. dispatch عملیات طولانی و تکراری بود.
# 5. validation ورودی‌ها حداقلی بود.
#
# ARCHITECTURE:
# جایگاه فایل صحیح است.
#
# MainWindow / MasterWindow
#          │
#          ▼
#       QThread
#          │
#          ▼
#    ScraperWorker
#          │
#          ▼
#    ProcessManager
#          │
#          ▼
#    ScraperProcess
#
# Worker مالک Process نیست و نباید مستقیماً multiprocessing
# را مدیریت کند.
#
# COMPATIBILITY:
# با ProcessManager فعلی سازگار است و عملیات استاندارد:
#
# start
# stop
# kill
# restart
# restart_force
# force_restart
# wait
# join
# refresh
#
# را پشتیبانی می‌کند.
#
# REQUIRED CHANGES:
# 1. انتقال تمام اجرای Process به ProcessManager.
# 2. یکسان‌سازی timeout handling.
# 3. حفظ status reporting.
# 4. حفظ signalهای مورد استفاده GUI.
# 5. جلوگیری از crash شدن Worker در زمان دریافت status.
#
# DECISION:
# بازنویسی کامل
#
# SCORE:
# 9.5/10


from __future__ import annotations

from typing import Any, Optional

from PyQt5.QtCore import QObject, pyqtSignal

from master.process_manager import ProcessManager


# ============================================================
# DEFAULTS
# ============================================================

DEFAULT_STOP_TIMEOUT = 10.0
DEFAULT_KILL_TIMEOUT = 3.0
DEFAULT_RESTART_TIMEOUT = 10.0
DEFAULT_FORCE_STOP_TIMEOUT = 5.0
DEFAULT_FORCE_KILL_TIMEOUT = 3.0


# ============================================================
# SUPPORTED OPERATIONS
# ============================================================

SUPPORTED_OPERATIONS = frozenset(
    {
        "start",
        "stop",
        "kill",
        "restart",
        "restart_force",
        "force_restart",
        "wait",
        "join",
        "refresh",
    }
)


# ============================================================
# SCRAPER WORKER
# ============================================================

class ScraperWorker(QObject):
    """
    Execute one scraper-management operation outside the GUI
    thread.

    The worker is intentionally thin.

    It does NOT:

        - create scraper processes
        - terminate multiprocessing.Process directly
        - access providers
        - access databases
        - execute scraper business logic
        - manipulate GUI widgets

    It ONLY:

        - receives one operation
        - delegates it to ProcessManager
        - reports progress
        - reports status
        - reports logs
        - reports success/failure

    Typical lifecycle:

        QThread.started
                │
                ▼
             run()
                │
                ▼
           _execute()
                │
                ▼
        ProcessManager
    """

    # ========================================================
    # SIGNALS
    # ========================================================

    progress = pyqtSignal(int)

    log = pyqtSignal(str)

    status_changed = pyqtSignal(
        str,
        object,
    )

    finished = pyqtSignal(str)

    failed = pyqtSignal(
        str,
        str,
    )

    # ========================================================
    # INIT
    # ========================================================

    def __init__(
        self,
        manager: ProcessManager,
        name: str,
        operation: str,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> None:

        super().__init__()

        # ----------------------------------------------------
        # MANAGER
        # ----------------------------------------------------

        if manager is None:

            raise ValueError(
                "ProcessManager is required."
            )

        if not isinstance(
            manager,
            ProcessManager,
        ):

            raise TypeError(
                "manager must be a ProcessManager instance."
            )

        # ----------------------------------------------------
        # NAME
        # ----------------------------------------------------

        normalized_name = str(
            name
        ).strip()

        if not normalized_name:

            raise ValueError(
                "Scraper name is required."
            )

        # ----------------------------------------------------
        # OPERATION
        # ----------------------------------------------------

        normalized_operation = str(
            operation
        ).strip().lower()

        if not normalized_operation:

            raise ValueError(
                "Scraper operation is required."
            )

        if (
            normalized_operation
            not in SUPPORTED_OPERATIONS
        ):

            raise ValueError(
                "Unsupported scraper operation: "
                f"{normalized_operation!r}. "
                "Supported operations: "
                f"{', '.join(sorted(SUPPORTED_OPERATIONS))}."
            )

        # ----------------------------------------------------
        # TIMEOUT
        # ----------------------------------------------------

        if timeout is not None:

            try:

                timeout = float(
                    timeout
                )

            except (
                TypeError,
                ValueError,
            ) as exc:

                raise ValueError(
                    "timeout must be a number or None."
                ) from exc

            if timeout < 0:

                raise ValueError(
                    "timeout cannot be negative."
                )

        # ----------------------------------------------------
        # STATE
        # ----------------------------------------------------

        self.manager = manager

        self.name = normalized_name

        self.operation = normalized_operation

        self.timeout = timeout

        self.kwargs = dict(
            kwargs
        )

        self._cancelled = False

    # ========================================================
    # RUN
    # ========================================================

    def run(self) -> None:
        """
        Execute the configured operation.

        This method is normally connected to:

            QThread.started

        The worker never starts or stops the QThread itself.
        """

        if self._cancelled:

            self.log.emit(
                f"[{self.name}] "
                "Operation cancelled before execution."
            )

            self.progress.emit(
                0
            )

            self.failed.emit(
                self.name,
                "Operation cancelled before execution.",
            )

            return

        try:

            self.progress.emit(
                5
            )

            self.log.emit(
                f"[{self.name}] "
                f"Starting operation: "
                f"{self.operation.upper()}"
            )

            self._emit_status()

            self.progress.emit(
                15
            )

            # ------------------------------------------------
            # EXECUTE
            # ------------------------------------------------

            self._execute()

            # ------------------------------------------------
            # FINAL STATUS
            # ------------------------------------------------

            self._emit_status()

            self.progress.emit(
                100
            )

            self.log.emit(
                f"[{self.name}] "
                f"{self.operation.upper()} completed."
            )

            self.finished.emit(
                self.name
            )

        except Exception as exc:

            error = self._format_exception(
                exc
            )

            self.log.emit(
                f"[{self.name}] "
                f"ERROR: {error}"
            )

            try:

                self._emit_status()

            except Exception:
                pass

            self.progress.emit(
                0
            )

            self.failed.emit(
                self.name,
                error,
            )

    # ========================================================
    # EXECUTION
    # ========================================================

    def _execute(self) -> Any:
        """
        Dispatch the selected operation to ProcessManager.
        """

        if self._cancelled:

            raise RuntimeError(
                "Operation cancelled before execution."
            )

        operation = self.operation

        # ====================================================
        # START
        # ====================================================

        if operation == "start":

            self.log.emit(
                f"[{self.name}] "
                "Starting scraper..."
            )

            return self.manager.start(
                self.name
            )

        # ====================================================
        # STOP
        # ====================================================

        if operation == "stop":

            timeout = self._timeout(
                default=DEFAULT_STOP_TIMEOUT
            )

            self.log.emit(
                f"[{self.name}] "
                f"Stopping scraper "
                f"(timeout={timeout}s)..."
            )

            return self.manager.stop(
                self.name,
                timeout=timeout,
            )

        # ====================================================
        # KILL
        # ====================================================

        if operation == "kill":

            timeout = self._timeout(
                default=DEFAULT_KILL_TIMEOUT
            )

            self.log.emit(
                f"[{self.name}] "
                f"Killing scraper "
                f"(timeout={timeout}s)..."
            )

            return self.manager.kill(
                self.name,
                timeout=timeout,
            )

        # ====================================================
        # RESTART
        # ====================================================

        if operation == "restart":

            timeout = self._timeout(
                default=DEFAULT_RESTART_TIMEOUT
            )

            self.log.emit(
                f"[{self.name}] "
                f"Restarting scraper "
                f"(timeout={timeout}s)..."
            )

            return self.manager.restart(
                self.name,
                timeout=timeout,
            )

        # ====================================================
        # FORCE RESTART
        # ====================================================

        if operation in {
            "restart_force",
            "force_restart",
        }:

            stop_timeout = self._get_timeout(
                "stop_timeout",
                DEFAULT_FORCE_STOP_TIMEOUT,
            )

            kill_timeout = self._get_timeout(
                "kill_timeout",
                DEFAULT_FORCE_KILL_TIMEOUT,
            )

            self.log.emit(
                f"[{self.name}] "
                "Force restarting scraper "
                f"(stop={stop_timeout}s, "
                f"kill={kill_timeout}s)..."
            )

            return self.manager.restart_force(
                self.name,
                stop_timeout=stop_timeout,
                kill_timeout=kill_timeout,
            )

        # ====================================================
        # WAIT
        # ====================================================

        if operation == "wait":

            timeout = self._optional_timeout(
                "timeout"
            )

            self.log.emit(
                f"[{self.name}] "
                f"Waiting for scraper "
                f"(timeout={timeout}s)..."
            )

            return self.manager.wait(
                self.name,
                timeout=timeout,
            )

        # ====================================================
        # JOIN
        # ====================================================

        if operation == "join":

            timeout = self._optional_timeout(
                "timeout"
            )

            self.log.emit(
                f"[{self.name}] "
                f"Joining scraper "
                f"(timeout={timeout}s)..."
            )

            return self.manager.join(
                self.name,
                timeout=timeout,
            )

        # ====================================================
        # REFRESH
        # ====================================================

        if operation == "refresh":

            self.log.emit(
                f"[{self.name}] "
                "Refreshing scraper state..."
            )

            return self.manager.refresh(
                self.name
            )

        # ====================================================
        # SAFETY NET
        # ====================================================

        raise RuntimeError(
            "Unhandled scraper operation: "
            f"{operation!r}"
        )

    # ========================================================
    # TIMEOUT
    # ========================================================

    def _timeout(
        self,
        default: float,
    ) -> float:
        """
        Return the operation timeout.

        Priority:

            explicit constructor timeout
                ↓
            kwargs["timeout"]
                ↓
            default
        """

        if self.timeout is not None:

            return float(
                self.timeout
            )

        return self._get_timeout(
            "timeout",
            default,
        )

    # ========================================================

    def _optional_timeout(
        self,
        key: str,
    ) -> Optional[float]:
        """
        Return an optional timeout.

        Priority:

            kwargs[key]
                ↓
            constructor timeout
                ↓
            None
        """

        if key in self.kwargs:

            value = self.kwargs[key]

            if value is None:
                return None

            try:

                value = float(
                    value
                )

            except (
                TypeError,
                ValueError,
            ) as exc:

                raise ValueError(
                    f"{key} must be a number or None."
                ) from exc

            if value < 0:

                raise ValueError(
                    f"{key} cannot be negative."
                )

            return value

        if self.timeout is not None:

            return float(
                self.timeout
            )

        return None

    # ========================================================

    def _get_timeout(
        self,
        key: str,
        default: float,
    ) -> float:
        """
        Return a validated numeric timeout.
        """

        value = self.kwargs.get(
            key,
            default,
        )

        if value is None:

            return float(
                default
            )

        try:

            value = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise ValueError(
                f"{key} must be a number."
            ) from exc

        if value < 0:

            raise ValueError(
                f"{key} cannot be negative."
            )

        return value

    # ========================================================
    # STATUS
    # ========================================================

    def _get_status(self) -> Any:
        """
        Read current scraper status safely.

        Status retrieval failure must never prevent the main
        operation from completing.
        """

        try:

            return self.manager.status(
                self.name
            )

        except Exception as exc:

            self.log.emit(
                f"[{self.name}] "
                f"Unable to read status: "
                f"{type(exc).__name__}: {exc}"
            )

            return None

    # ========================================================

    def _emit_status(self) -> None:
        """
        Emit the current scraper status.
        """

        status = self._get_status()

        self.status_changed.emit(
            self.name,
            status,
        )

    # ========================================================
    # CANCEL
    # ========================================================

    def cancel(self) -> None:
        """
        Request cancellation of the worker operation.

        Important
        ---------

        This method does NOT terminate a running scraper
        process.

        Process termination remains exclusively owned by
        ProcessManager.

        Because Python cannot safely interrupt an arbitrary
        blocking ProcessManager call from another Qt thread,
        cancellation is cooperative and is guaranteed only
        before the operation begins.

        For an already-running scraper process, the caller
        must explicitly request:

            ProcessManager.stop()
            or
            ProcessManager.kill()
        """

        if self._cancelled:

            return

        self._cancelled = True

        self.log.emit(
            f"[{self.name}] "
            "Worker cancellation requested."
        )

    # ========================================================
    # CANCELLED
    # ========================================================

    @property
    def cancelled(self) -> bool:
        """
        Return whether cancellation was requested.
        """

        return self._cancelled

    # ========================================================
    # EXCEPTION FORMAT
    # ========================================================

    @staticmethod
    def _format_exception(
        exc: Exception,
    ) -> str:
        """
        Convert an exception into a stable human-readable
        error string.
        """

        message = str(
            exc
        ).strip()

        if message:

            return (
                f"{type(exc).__name__}: "
                f"{message}"
            )

        return type(
            exc
        ).__name__

    # ========================================================
    # REPRESENTATION
    # ========================================================

    def __repr__(self) -> str:
        """
        Return a concise worker representation.
        """

        return (
            "<ScraperWorker "
            f"name={self.name!r} "
            f"operation={self.operation!r} "
            f"cancelled={self._cancelled!r}>"
        )