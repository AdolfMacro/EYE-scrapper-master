from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ScraperCard(QFrame):
    """
    EYES MASTER scraper representation.

    This widget is intentionally dumb.

    It:
        - displays scraper state
        - exposes action signals
        - updates itself from data

    It does NOT:
        - access ProcessManager
        - access Registry
        - create processes
        - manipulate multiprocessing
    """

    start_requested = pyqtSignal(str)
    stop_requested = pyqtSignal(str)
    restart_requested = pyqtSignal(str)
    kill_requested = pyqtSignal(str)
    details_requested = pyqtSignal(str)

    COLORS = {
        "amber": "#FED172",
        "orange": "#F3742B",
        "deep_orange": "#B83A14",
        "burgundy": "#612E37",
        "purple": "#231650",

        "background": "#1B1230",
        "surface": "#24183A",
        "surface_hover": "#2B1C40",

        "border": "#432A43",
        "border_hover": "#F3742B",

        "text": "#FFF7E6",
        "secondary": "#D8C7C0",
        "muted": "#9C858D",
    }

    STATUS = {
        "CREATED": ("#9C858D", "#30223D"),
        "STARTING": ("#FED172", "#46361F"),
        "RUNNING": ("#FED172", "#40351E"),
        "STOPPING": ("#F3742B", "#43271F"),
        "STOPPED": ("#9C858D", "#30223D"),
        "FINISHED": ("#D8C7C0", "#30263D"),
        "CRASHED": ("#B83A14", "#43201E"),
        "KILLED": ("#B83A14", "#43201E"),
    }

    def __init__(
        self,
        name: str,
        providers: Optional[list[str]] = None,
        status: str = "CREATED",
        pid: Optional[int] = None,
        target: Optional[str] = None,
        database: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:

        super().__init__(parent)

        self.name = str(name).strip()
        self.providers = [
            str(item).strip()
            for item in (providers or [])
            if str(item).strip()
        ]

        self.status = str(
            status
        ).strip().upper()

        self.pid = pid
        self.target = target
        self.database = database

        self._build_ui()
        self._apply_style()
        self.update_state(
            self.status,
            self.pid,
        )

    # ==========================================================
    # UI
    # ==========================================================

    def _build_ui(self) -> None:

        self.setObjectName("ScraperCard")
        self.setMinimumHeight(128)
        self.setMaximumHeight(150)

        root = QHBoxLayout(self)

        root.setContentsMargins(
            18,
            15,
            18,
            15,
        )

        root.setSpacing(16)

        # ------------------------------------------------------
        # STATUS
        # ------------------------------------------------------

        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("StatusDot")
        self.status_dot.setFixedWidth(20)
        self.status_dot.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        root.addWidget(
            self.status_dot
        )

        # ------------------------------------------------------
        # INFO
        # ------------------------------------------------------

        info = QVBoxLayout()
        info.setSpacing(7)

        self.name_label = QLabel(
            self.name
        )

        self.name_label.setObjectName(
            "ScraperName"
        )

        self.name_label.setFont(
            QFont(
                "DejaVu Sans",
                15,
                QFont.Bold,
            )
        )

        info.addWidget(
            self.name_label
        )

        meta = QHBoxLayout()
        meta.setSpacing(10)

        self.status_label = QLabel()
        self.status_label.setObjectName(
            "StatusLabel"
        )

        self.pid_label = QLabel()
        self.pid_label.setObjectName(
            "MetaLabel"
        )

        self.target_label = QLabel()
        self.target_label.setObjectName(
            "MetaLabel"
        )

        meta.addWidget(
            self.status_label
        )

        meta.addWidget(
            self.pid_label
        )

        meta.addWidget(
            self.target_label
        )

        meta.addStretch()

        info.addLayout(meta)

        provider_text = (
            ", ".join(self.providers)
            if self.providers
            else "none"
        )

        self.providers_label = QLabel(
            f"PROVIDERS  {provider_text}"
        )

        self.providers_label.setObjectName(
            "ProvidersLabel"
        )

        info.addWidget(
            self.providers_label
        )

        root.addLayout(
            info,
            1,
        )

        # ------------------------------------------------------
        # ACTIONS
        # ------------------------------------------------------

        actions = QHBoxLayout()
        actions.setSpacing(6)

        self.start_button = self._button(
            "START",
            "StartButton",
        )

        self.stop_button = self._button(
            "STOP",
            "StopButton",
        )

        self.restart_button = self._button(
            "RESTART",
            "RestartButton",
        )

        self.kill_button = self._button(
            "KILL",
            "KillButton",
        )

        self.details_button = self._button(
            "DETAILS",
            "DetailsButton",
        )

        for button in (
            self.start_button,
            self.stop_button,
            self.restart_button,
            self.kill_button,
            self.details_button,
        ):
            actions.addWidget(button)

        root.addLayout(actions)

        self.start_button.clicked.connect(
            lambda: self.start_requested.emit(self.name)
        )

        self.stop_button.clicked.connect(
            lambda: self.stop_requested.emit(self.name)
        )

        self.restart_button.clicked.connect(
            lambda: self.restart_requested.emit(self.name)
        )

        self.kill_button.clicked.connect(
            lambda: self.kill_requested.emit(self.name)
        )

        self.details_button.clicked.connect(
            lambda: self.details_requested.emit(self.name)
        )

    # ==========================================================
    # BUTTON
    # ==========================================================

    def _button(
        self,
        text: str,
        object_name: str,
    ) -> QPushButton:

        button = QPushButton(text)

        button.setObjectName(
            object_name
        )

        button.setCursor(
            Qt.PointingHandCursor
        )

        button.setFixedHeight(36)
        button.setMinimumWidth(76)
        button.setMaximumWidth(105)

        button.setFocusPolicy(
            Qt.NoFocus
        )

        return button

    # ==========================================================
    # STATE
    # ==========================================================

    def update_state(
        self,
        status: str,
        pid: Optional[int] = None,
    ) -> None:

        self.status = str(
            status
        ).strip().upper()

        self.pid = pid

        self.status_label.setText(
            self.status
        )

        self.pid_label.setText(
            f"PID {pid}"
            if pid is not None
            else "PID —"
        )

        if self.target:
            self.target_label.setText(
                f"TARGET {self.target}"
            )
        else:
            self.target_label.clear()

        self._update_status_style()
        self._update_actions()

    # ==========================================================
    # STATUS STYLE
    # ==========================================================

    def _update_status_style(self) -> None:

        foreground, background = (
            self.STATUS.get(
                self.status,
                (
                    self.COLORS["secondary"],
                    self.COLORS["surface"],
                ),
            )
        )

        self.status_dot.setStyleSheet(
            f"""
            QLabel#StatusDot {{
                color: {foreground};
                font-size: 13px;
            }}
            """
        )

        self.status_label.setStyleSheet(
            f"""
            QLabel#StatusLabel {{
                color: {foreground};
                background: {background};
                border: 1px solid {foreground};
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: 900;
            }}
            """
        )

    # ==========================================================
    # ACTIONS STATE
    # ==========================================================

    def _update_actions(self) -> None:

        status = self.status

        active = status in {
            "STARTING",
            "RUNNING",
            "STOPPING",
        }

        self.start_button.setEnabled(
            status in {
                "CREATED",
                "STOPPED",
                "FINISHED",
                "CRASHED",
                "KILLED",
            }
        )

        self.stop_button.setEnabled(
            status == "RUNNING"
        )

        self.restart_button.setEnabled(
            status not in {
                "STARTING",
                "STOPPING",
            }
        )

        self.kill_button.setEnabled(
            active
        )

        self.details_button.setEnabled(
            True
        )

    # ==========================================================
    # DATA
    # ==========================================================

    def update_data(
        self,
        *,
        name: Optional[str] = None,
        providers: Optional[list[str]] = None,
        target: Optional[str] = None,
        database: Optional[str] = None,
    ) -> None:

        if name is not None:

            self.name = str(
                name
            ).strip()

            self.name_label.setText(
                self.name
            )

        if providers is not None:

            self.providers = [
                str(item).strip()
                for item in providers
                if str(item).strip()
            ]

            provider_text = (
                ", ".join(self.providers)
                if self.providers
                else "none"
            )

            self.providers_label.setText(
                f"PROVIDERS  {provider_text}"
            )

        if target is not None:

            self.target = (
                str(target).strip()
                if target
                else None
            )

        if database is not None:
            self.database = database

        self.update_state(
            self.status,
            self.pid,
        )

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(self) -> dict:

        return {
            "name": self.name,
            "providers": list(self.providers),
            "status": self.status,
            "pid": self.pid,
            "target": self.target,
            "database": self.database,
        }

    # ==========================================================
    # STYLE
    # ==========================================================

    def _apply_style(self) -> None:

        self.setStyleSheet(
            f"""
            QFrame#ScraperCard {{
                background: {self.COLORS["surface"]};
                border: 1px solid {self.COLORS["border"]};
                border-radius: 12px;
            }}

            QFrame#ScraperCard:hover {{
                background: {self.COLORS["surface_hover"]};
                border-color: {self.COLORS["orange"]};
            }}

            QLabel#ScraperName {{
                color: {self.COLORS["text"]};
                background: transparent;
                font-size: 15px;
                font-weight: 900;
            }}

            QLabel#MetaLabel {{
                color: {self.COLORS["muted"]};
                background: transparent;
                font-size: 10px;
                font-weight: 700;
            }}

            QLabel#ProvidersLabel {{
                color: {self.COLORS["amber"]};
                background: transparent;
                font-size: 10px;
                font-weight: 800;
            }}

            QPushButton {{
                min-height: 34px;
                border-radius: 7px;
                padding: 6px 10px;
                font-size: 9px;
                font-weight: 900;
                background: #30213F;
                color: {self.COLORS["secondary"]};
                border: 1px solid #513348;
            }}

            QPushButton:hover {{
                background: #3A2644;
                color: {self.COLORS["text"]};
                border-color: {self.COLORS["orange"]};
            }}

            QPushButton:pressed {{
                background: {self.COLORS["deep_orange"]};
                color: white;
            }}

            QPushButton:disabled {{
                background: #251B32;
                color: #685761;
                border-color: #34253A;
            }}

            QPushButton#StartButton {{
                color: {self.COLORS["amber"]};
                border-color: #806338;
                background: #30263A;
            }}

            QPushButton#StopButton {{
                color: {self.COLORS["orange"]};
                border-color: #714032;
                background: #322039;
            }}

            QPushButton#RestartButton {{
                color: #D8C7C0;
                border-color: #574052;
                background: #30233D;
            }}

            QPushButton#KillButton {{
                color: #F3742B;
                border-color: #71372D;
                background: #341F36;
            }}

            QPushButton#DetailsButton {{
                color: #C5B4B2;
                border-color: #51404D;
                background: #30243D;
            }}
            """
        )