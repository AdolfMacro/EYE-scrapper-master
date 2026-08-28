# ============================================================
# EYES MASTER — MAIN WINDOW
# ============================================================
#
# FILE:
#     gui/main_window.py
#
# STATUS:
#     CANONICAL / CORE
#
# ROLE:
#     Top-level visual shell of EYES MASTER.
#
# VISUAL DIRECTION:
#
#     DARK
#     INDUSTRIAL
#     DEEP PURPLE
#     AMBER
#     ORANGE
#     BURGUNDY
#     HIGH CONTRAST
#     READABLE TYPOGRAPHY
#
# RESPONSIBILITY:
#
#     - application shell
#     - global visual theme
#     - header
#     - system status
#     - MasterWindow hosting
#     - application shutdown
#
# DOES NOT OWN:
#
#     - scraper execution
#     - provider logic
#     - keyword processing
#     - database logic
#     - worker lifecycle
#     - multiprocessing logic
#     - scraper business rules
#
# ============================================================

from __future__ import annotations

import sys
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from master.process_manager import ProcessManager

from .master_window import MasterWindow


# ============================================================
# EYES MASTER — CANONICAL PALETTE
# ============================================================
#
# Palette reference:
#
#     #FED172  Amber
#     #F3742B  Orange
#     #B83A14  Deep Orange
#     #612E37  Burgundy
#     #231650  Purple
#
# ============================================================


# ------------------------------------------------------------
# PRIMARY PALETTE
# ------------------------------------------------------------

AMBER = "#FED172"
ORANGE = "#F3742B"
DEEP_ORANGE = "#B83A14"
BURGUNDY = "#612E37"
PURPLE = "#231650"


# ------------------------------------------------------------
# BACKGROUND
# ------------------------------------------------------------

BG_DEEP = "#120C22"
BG = "#18102A"


# ------------------------------------------------------------
# SURFACES
# ------------------------------------------------------------

SURFACE = "#211735"
SURFACE_2 = "#2A1D3E"
SURFACE_3 = "#34234A"

SURFACE_ACTIVE = "#38243F"


# ------------------------------------------------------------
# BORDERS
# ------------------------------------------------------------

BORDER = "#612E37"
BORDER_SOFT = "#4A2B38"

BORDER_ACTIVE = "#F3742B"
BORDER_AMBER = "#FED172"


# ------------------------------------------------------------
# STATUS
# ------------------------------------------------------------

GREEN = "#FED172"
WARNING = "#F3742B"
RED = "#B83A14"
BLUE = "#FED172"


# ------------------------------------------------------------
# TEXT
# ------------------------------------------------------------

TEXT = "#FFF4D6"
TEXT_SECONDARY = "#D8C7C0"
TEXT_MUTED = "#A98C8A"
TEXT_DARK = "#6F565F"


# ------------------------------------------------------------
# TERMINAL / EMPHASIS
# ------------------------------------------------------------

TERMINAL_AMBER = "#FED172"


# ============================================================
# MAIN WINDOW
# ============================================================


class MainWindow(QMainWindow):
    """
    Top-level visual shell for EYES MASTER.

    MainWindow owns only application-level UI concerns.

    The actual scraper management interface is delegated to
    MasterWindow.
    """

    # ========================================================
    # INIT
    # ========================================================

    def __init__(
        self,
        manager: ProcessManager,
        parent: Optional[QWidget] = None,
    ) -> None:

        super().__init__(parent)

        if manager is None:
            raise ValueError(
                "ProcessManager is required."
            )

        self.manager = manager

        # ----------------------------------------------------
        # WINDOW
        # ----------------------------------------------------

        self.setObjectName(
            "MainWindow"
        )

        self.setWindowTitle(
            "EYES // MASTER"
        )

        self.setMinimumSize(
            1200,
            760,
        )

        self.resize(
            1600,
            1000,
        )

        # ----------------------------------------------------
        # BUILD
        # ----------------------------------------------------

        self._build_ui()
        self._apply_style()

    # ========================================================
    # BUILD UI
    # ========================================================

    def _build_ui(self) -> None:
        """
        Build the application shell.
        """

        root = QWidget()

        root.setObjectName(
            "Root"
        )

        root.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        self.setCentralWidget(
            root
        )

        root_layout = QVBoxLayout(
            root
        )

        root_layout.setContentsMargins(
            22,
            20,
            22,
            20,
        )

        root_layout.setSpacing(
            16
        )

        # ====================================================
        # HEADER
        # ====================================================

        header = self._build_header()

        root_layout.addWidget(
            header
        )

        # ====================================================
        # MASTER CONTENT
        # ====================================================

        self.master_window = MasterWindow(
            manager=self.manager,
            parent=root,
        )

        self.master_window.setObjectName(
            "MasterContent"
        )

        self.master_window.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        root_layout.addWidget(
            self.master_window,
            1,
        )

    # ========================================================
    # HEADER
    # ========================================================

    def _build_header(self) -> QFrame:
        """
        Build the global EYES header.
        """

        header = QFrame()

        header.setObjectName(
            "Header"
        )

        header.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        header_layout = QHBoxLayout(
            header
        )

        header_layout.setContentsMargins(
            24,
            18,
            24,
            18,
        )

        header_layout.setSpacing(
            22
        )

        # ====================================================
        # BRAND
        # ====================================================

        brand_container = QVBoxLayout()

        brand_container.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        brand_container.setSpacing(
            3
        )

        brand = QLabel(
            "EYES"
        )

        brand.setObjectName(
            "Brand"
        )

        brand.setAlignment(
            Qt.AlignLeft
            | Qt.AlignVCenter
        )

        subtitle = QLabel(
            "// SCRAPER MASTER"
        )

        subtitle.setObjectName(
            "BrandSubtitle"
        )

        subtitle.setAlignment(
            Qt.AlignLeft
            | Qt.AlignVCenter
        )

        brand_container.addWidget(
            brand
        )

        brand_container.addWidget(
            subtitle
        )

        header_layout.addLayout(
            brand_container
        )

        # ====================================================
        # PIPELINE
        # ====================================================

        pipeline = QFrame()

        pipeline.setObjectName(
            "Pipeline"
        )

        pipeline.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        pipeline_layout = QHBoxLayout(
            pipeline
        )

        pipeline_layout.setContentsMargins(
            18,
            12,
            18,
            12,
        )

        pipeline_layout.setSpacing(
            11
        )

        pipeline_items = (
            ("01", "KEYWORDS"),
            ("02", "PROVIDER"),
            ("03", "LOCATION"),
            ("04", "SCRAPER"),
            ("05", "DATABASE"),
        )

        for index, (
            number,
            label,
        ) in enumerate(
            pipeline_items
        ):

            item = QLabel(
                f"{number}  {label}"
            )

            item.setObjectName(
                "PipelineItem"
            )

            item.setAlignment(
                Qt.AlignCenter
            )

            pipeline_layout.addWidget(
                item
            )

            if index < len(
                pipeline_items
            ) - 1:

                separator = QLabel(
                    ">"
                )

                separator.setObjectName(
                    "PipelineSeparator"
                )

                separator.setAlignment(
                    Qt.AlignCenter
                )

                pipeline_layout.addWidget(
                    separator
                )

        header_layout.addWidget(
            pipeline,
            1,
        )

        # ====================================================
        # SYSTEM STATUS
        # ====================================================

        self.status_frame = QFrame()

        self.status_frame.setObjectName(
            "StatusFrame"
        )

        self.status_frame.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Fixed,
        )

        status_layout = QHBoxLayout(
            self.status_frame
        )

        status_layout.setContentsMargins(
            16,
            11,
            16,
            11,
        )

        status_layout.setSpacing(
            10
        )

        self.system_indicator = QLabel(
            "●"
        )

        self.system_indicator.setObjectName(
            "SystemIndicator"
        )

        self.system_indicator.setAlignment(
            Qt.AlignCenter
        )

        self.system_label = QLabel(
            "SYSTEM READY"
        )

        self.system_label.setObjectName(
            "SystemStatus"
        )

        self.system_label.setAlignment(
            Qt.AlignCenter
        )

        status_layout.addWidget(
            self.system_indicator
        )

        status_layout.addWidget(
            self.system_label
        )

        header_layout.addWidget(
            self.status_frame
        )

        return header

    # ========================================================
    # SYSTEM STATUS
    # ========================================================

    def set_system_status(
        self,
        text: str,
        active: bool = False,
    ) -> None:
        """
        Update the global system status indicator.
        """

        text = str(
            text
        ).strip()

        if not text:
            text = "SYSTEM READY"

        self.system_label.setText(
            text.upper()
        )

        if active:

            self.system_indicator.setStyleSheet(
                f"""
                color: {WARNING};
                """
            )

            self.system_label.setStyleSheet(
                f"""
                color: {WARNING};
                """
            )

        else:

            self.system_indicator.setStyleSheet(
                f"""
                color: {GREEN};
                """
            )

            self.system_label.setStyleSheet(
                f"""
                color: {GREEN};
                """
            )

    # ========================================================
    # GLOBAL STYLE
    # ========================================================

    def _apply_style(self) -> None:
        """
        Apply the canonical EYES MASTER visual theme.

        The visual system is based exclusively on the
        EYES palette:

            AMBER
            ORANGE
            DEEP ORANGE
            BURGUNDY
            PURPLE
        """

        self.setStyleSheet(
            f"""
            /* =================================================
               GLOBAL
               ================================================= */

            QMainWindow#MainWindow {{
                background: {BG_DEEP};
            }}

            QWidget#Root {{
                background: {BG_DEEP};
            }}

            QWidget {{
                color: {TEXT};
                font-family: "DejaVu Sans";
                font-size: 15px;
            }}

            QLabel {{
                color: {TEXT};
                background: transparent;
                font-size: 15px;
            }}


            /* =================================================
               HEADER
               ================================================= */

            QFrame#Header {{
                background: {SURFACE};
                border: 2px solid {BORDER};
                border-radius: 14px;
            }}

            QFrame#Header:hover {{
                border-color: {ORANGE};
            }}


            /* =================================================
               BRAND
               ================================================= */

            QLabel#Brand {{
                color: {AMBER};
                font-family: "DejaVu Sans";
                font-size: 48px;
                font-weight: 900;
            }}

            QLabel#BrandSubtitle {{
                color: {ORANGE};
                font-family: "DejaVu Sans";
                font-size: 15px;
                font-weight: 900;
            }}


            /* =================================================
               PIPELINE
               ================================================= */

            QFrame#Pipeline {{
                background: {BG};
                border: 2px solid {BORDER};
                border-radius: 10px;
            }}

            QLabel#PipelineItem {{
                color: {TEXT_SECONDARY};
                font-family: "DejaVu Sans";
                font-size: 13px;
                font-weight: 900;
            }}

            QLabel#PipelineItem:hover {{
                color: {AMBER};
            }}

            QLabel#PipelineSeparator {{
                color: {ORANGE};
                font-size: 20px;
                font-weight: 900;
            }}


            /* =================================================
               SYSTEM STATUS
               ================================================= */

            QFrame#StatusFrame {{
                background: {SURFACE_2};
                border: 2px solid {BORDER};
                border-radius: 10px;
            }}

            QLabel#SystemIndicator {{
                color: {GREEN};
                font-size: 22px;
                font-weight: 900;
            }}

            QLabel#SystemStatus {{
                color: {GREEN};
                font-size: 13px;
                font-weight: 900;
            }}


            /* =================================================
               MASTER CONTENT
               ================================================= */

            QWidget#MasterContent {{
                background: transparent;
                border: none;
            }}


            /* =================================================
               BUTTONS
               ================================================= */

            QPushButton {{
                background: {SURFACE_2};
                color: {TEXT};
                border: 2px solid {BORDER};
                border-radius: 8px;
                min-height: 46px;
                padding: 8px 18px;
                font-size: 15px;
                font-weight: 900;
            }}

            QPushButton:hover {{
                background: {SURFACE_ACTIVE};
                border-color: {ORANGE};
                color: {AMBER};
            }}

            QPushButton:pressed {{
                background: {ORANGE};
                border-color: {ORANGE};
                color: {BG_DEEP};
            }}

            QPushButton:disabled {{
                background: {SURFACE};
                color: {TEXT_DARK};
                border-color: {BORDER_SOFT};
            }}


            /* =================================================
               INPUTS
               ================================================= */

            QLineEdit {{
                background: {BG};
                color: {TEXT};
                border: 2px solid {BORDER};
                border-radius: 8px;
                padding: 10px 14px;
                min-height: 42px;
                font-family: "DejaVu Sans";
                font-size: 18px;
                font-weight: 600;
                selection-background-color: {ORANGE};
                selection-color: {BG_DEEP};
            }}

            QLineEdit:hover {{
                border-color: {AMBER};
            }}

            QLineEdit:focus {{
                border-color: {ORANGE};
            }}

            QLineEdit:read-only {{
                background: {SURFACE_2};
                color: {TEXT_SECONDARY};
            }}


            /* =================================================
               TEXT EDIT
               ================================================= */

            QTextEdit,
            QPlainTextEdit {{
                background: {BG};
                color: {TEXT};
                border: 2px solid {BORDER};
                border-radius: 8px;
                padding: 11px;
                font-family: "DejaVu Sans";
                font-size: 17px;
                selection-background-color: {ORANGE};
                selection-color: {BG_DEEP};
            }}

            QTextEdit:hover,
            QPlainTextEdit:hover {{
                border-color: {AMBER};
            }}

            QTextEdit:focus,
            QPlainTextEdit:focus {{
                border-color: {ORANGE};
            }}


            /* =================================================
               COMBO BOX
               ================================================= */

            QComboBox {{
                background: {SURFACE_2};
                color: {TEXT};
                border: 2px solid {BORDER};
                border-radius: 8px;
                padding: 10px 14px;
                min-height: 42px;
                font-size: 18px;
                font-weight: 700;
            }}

            QComboBox:hover {{
                border-color: {AMBER};
            }}

            QComboBox:focus {{
                border-color: {ORANGE};
            }}

            QComboBox::drop-down {{
                border: none;
                width: 38px;
            }}

            QComboBox QAbstractItemView {{
                background: {SURFACE};
                color: {TEXT};
                border: 2px solid {BORDER};
                selection-background-color: {ORANGE};
                selection-color: {BG_DEEP};
                padding: 6px;
                font-size: 17px;
            }}


            /* =================================================
               SPIN BOX
               ================================================= */

            QSpinBox,
            QDoubleSpinBox {{
                background: {BG};
                color: {TEXT};
                border: 2px solid {BORDER};
                border-radius: 8px;
                padding: 8px 12px;
                min-height: 40px;
                font-size: 18px;
                font-weight: 700;
            }}

            QSpinBox:hover,
            QDoubleSpinBox:hover {{
                border-color: {AMBER};
            }}

            QSpinBox:focus,
            QDoubleSpinBox:focus {{
                border-color: {ORANGE};
            }}


            /* =================================================
               CHECKBOX
               ================================================= */

            QCheckBox {{
                color: {TEXT_SECONDARY};
                spacing: 10px;
                font-size: 17px;
            }}

            QCheckBox:hover {{
                color: {AMBER};
            }}

            QCheckBox::indicator {{
                width: 21px;
                height: 21px;
                border: 2px solid {BORDER};
                border-radius: 5px;
                background: {BG};
            }}

            QCheckBox::indicator:hover {{
                border-color: {AMBER};
            }}

            QCheckBox::indicator:checked {{
                background: {ORANGE};
                border-color: {ORANGE};
            }}


            /* =================================================
               RADIO
               ================================================= */

            QRadioButton {{
                color: {TEXT_SECONDARY};
                spacing: 10px;
                font-size: 17px;
            }}

            QRadioButton:hover {{
                color: {AMBER};
            }}

            QRadioButton::indicator {{
                width: 20px;
                height: 20px;
                border: 2px solid {BORDER};
                border-radius: 11px;
                background: {BG};
            }}

            QRadioButton::indicator:hover {{
                border-color: {AMBER};
            }}

            QRadioButton::indicator:checked {{
                background: {ORANGE};
                border: 5px solid {BG};
            }}


            /* =================================================
               GROUP BOX
               ================================================= */

            QGroupBox {{
                background: {SURFACE};
                color: {AMBER};
                border: 2px solid {BORDER};
                border-radius: 10px;
                margin-top: 18px;
                padding: 16px;
                font-size: 17px;
                font-weight: 900;
            }}

            QGroupBox:hover {{
                border-color: {ORANGE};
            }}

            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 9px;
                color: {AMBER};
                background: {SURFACE};
                font-size: 17px;
                font-weight: 900;
            }}


            /* =================================================
               CARDS
               ================================================= */

            QFrame#Card {{
                background: {SURFACE};
                border: 2px solid {BORDER};
                border-radius: 10px;
            }}

            QFrame#Card:hover {{
                border-color: {ORANGE};
            }}

            QFrame#ActiveCard {{
                background: {SURFACE_ACTIVE};
                border: 2px solid {ORANGE};
                border-radius: 10px;
            }}


            /* =================================================
               TABLES
               ================================================= */

            QTableWidget,
            QTableView {{
                background: {BG};
                alternate-background-color: {SURFACE};
                color: {TEXT};
                border: 2px solid {BORDER};
                border-radius: 9px;
                gridline-color: {SURFACE_3};
                selection-background-color: {ORANGE};
                selection-color: {BG_DEEP};
                font-size: 17px;
            }}

            QHeaderView::section {{
                background: {SURFACE_2};
                color: {AMBER};
                border: none;
                border-right: 1px solid {BORDER};
                border-bottom: 2px solid {BORDER};
                padding: 11px;
                font-size: 16px;
                font-weight: 900;
            }}


            /* =================================================
               LISTS
               ================================================= */

            QListWidget,
            QListView {{
                background: {BG};
                color: {TEXT};
                border: 2px solid {BORDER};
                border-radius: 9px;
                padding: 6px;
                outline: none;
                font-size: 17px;
            }}

            QListWidget::item,
            QListView::item {{
                padding: 10px;
                border-radius: 6px;
            }}

            QListWidget::item:hover,
            QListView::item:hover {{
                background: {SURFACE_3};
                color: {AMBER};
            }}

            QListWidget::item:selected,
            QListView::item:selected {{
                background: {ORANGE};
                color: {BG_DEEP};
            }}


            /* =================================================
               PROGRESS
               ================================================= */

            QProgressBar {{
                background: {BG};
                color: {TEXT};
                border: 2px solid {BORDER};
                border-radius: 7px;
                text-align: center;
                min-height: 26px;
                font-size: 16px;
                font-weight: 900;
            }}

            QProgressBar::chunk {{
                background: {ORANGE};
                border-radius: 5px;
            }}


            /* =================================================
               SCROLLBARS
               ================================================= */

            QScrollBar:vertical {{
                background: {BG};
                width: 13px;
                border: none;
                margin: 2px;
                border-radius: 7px;
            }}

            QScrollBar::handle:vertical {{
                background: {BORDER};
                min-height: 42px;
                border-radius: 7px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: {ORANGE};
            }}

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: transparent;
            }}

            QScrollBar:horizontal {{
                background: {BG};
                height: 13px;
                border: none;
                margin: 2px;
                border-radius: 7px;
            }}

            QScrollBar::handle:horizontal {{
                background: {BORDER};
                min-width: 42px;
                border-radius: 7px;
            }}

            QScrollBar::handle:horizontal:hover {{
                background: {ORANGE};
            }}

            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}

            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {{
                background: transparent;
            }}


            /* =================================================
               TOOLTIP
               ================================================= */

            QToolTip {{
                background: {SURFACE};
                color: {AMBER};
                border: 2px solid {ORANGE};
                padding: 8px;
                border-radius: 6px;
                font-size: 15px;
            }}


            /* =================================================
               MESSAGE BOX
               ================================================= */

            QMessageBox {{
                background: {SURFACE};
                color: {TEXT};
                font-size: 17px;
            }}

            QMessageBox QLabel {{
                color: {TEXT};
                font-size: 17px;
            }}

            QMessageBox QPushButton {{
                min-width: 110px;
                min-height: 44px;
                font-size: 16px;
            }}


            /* =================================================
               DIALOG
               ================================================= */

            QDialog {{
                background: {BG_DEEP};
                color: {TEXT};
                font-size: 17px;
            }}


            /* =================================================
               TABS
               ================================================= */

            QTabWidget::pane {{
                background: {SURFACE};
                border: 2px solid {BORDER};
                border-radius: 9px;
            }}

            QTabBar::tab {{
                background: {SURFACE_2};
                color: {TEXT_MUTED};
                border: 2px solid {BORDER};
                padding: 11px 19px;
                margin-right: 4px;
                border-top-left-radius: 7px;
                border-top-right-radius: 7px;
                font-size: 16px;
                font-weight: 900;
            }}

            QTabBar::tab:hover {{
                color: {AMBER};
                border-color: {ORANGE};
            }}

            QTabBar::tab:selected {{
                background: {ORANGE};
                color: {BG_DEEP};
                border-color: {ORANGE};
            }}


            /* =================================================
               STATUS BAR
               ================================================= */

            QStatusBar {{
                background: {BG};
                color: {TEXT_SECONDARY};
                border-top: 1px solid {BORDER};
                font-size: 15px;
            }}


            /* =================================================
               MENU
               ================================================= */

            QMenu {{
                background: {SURFACE};
                color: {TEXT};
                border: 2px solid {BORDER};
                padding: 6px;
                font-size: 16px;
            }}

            QMenu::item {{
                padding: 10px 24px;
            }}

            QMenu::item:selected {{
                background: {ORANGE};
                color: {BG_DEEP};
            }}


            /* =================================================
               TOOLBAR
               ================================================= */

            QToolBar {{
                background: {SURFACE};
                border: 1px solid {BORDER};
                spacing: 8px;
                padding: 7px;
            }}

            QToolBar QToolButton {{
                background: transparent;
                color: {TEXT};
                border: 1px solid transparent;
                padding: 8px 12px;
                font-size: 16px;
            }}

            QToolBar QToolButton:hover {{
                background: {SURFACE_2};
                color: {AMBER};
                border-color: {BORDER};
            }}
            """
        )

    # ========================================================
    # FULLSCREEN
    # ========================================================

    def enter_fullscreen(self) -> None:
        """
        Enter application fullscreen mode.
        """

        self.showFullScreen()

    # ========================================================

    def exit_fullscreen(self) -> None:
        """
        Exit application fullscreen mode.
        """

        self.showNormal()

    # ========================================================
    # CLOSE
    # ========================================================

    def closeEvent(
        self,
        event,
    ) -> None:
        """
        Perform application-level shutdown.

        ProcessManager remains the owner of process lifecycle.
        """

        # ----------------------------------------------------
        # Stop GUI refresh timer
        # ----------------------------------------------------

        try:

            timer = getattr(
                self.master_window,
                "refresh_timer",
                None,
            )

            if timer is not None:
                timer.stop()

        except Exception as exc:

            print(
                "[EYES] "
                f"Failed to stop GUI timer: {exc}"
            )

        # ----------------------------------------------------
        # Shutdown ProcessManager
        # ----------------------------------------------------

        try:

            shutdown = getattr(
                self.manager,
                "shutdown",
                None,
            )

            if callable(shutdown):

                shutdown(
                    timeout=10.0
                )

        except Exception as exc:

            print(
                "[EYES] "
                f"ProcessManager shutdown error: {exc}"
            )

        event.accept()


# ============================================================
# START GUI
# ============================================================

def start_gui(
    manager: ProcessManager,
):
    """
    Start the EYES MASTER graphical interface.

    Parameters
    ----------
    manager:
        Existing ProcessManager instance.

    Returns
    -------
    int | MainWindow
        QApplication exit code when this function owns the
        QApplication, otherwise the created MainWindow.
    """

    if manager is None:
        raise ValueError(
            "ProcessManager is required."
        )

    # --------------------------------------------------------
    # QApplication
    # --------------------------------------------------------

    app = QApplication.instance()

    owns_app = app is None

    if owns_app:

        app = QApplication(
            sys.argv
        )

    # --------------------------------------------------------
    # Application metadata
    # --------------------------------------------------------

    app.setApplicationName(
        "EYES Master"
    )

    app.setApplicationDisplayName(
        "EYES // SCRAPER MASTER"
    )

    app.setOrganizationName(
        "EYES"
    )

    app.setOrganizationDomain(
        "eyes"
    )

    # --------------------------------------------------------
    # Global font
    # --------------------------------------------------------

    app.setFont(
        QFont(
            "DejaVu Sans",
            15,
        )
    )

    # --------------------------------------------------------
    # Main window
    # --------------------------------------------------------

    window = MainWindow(
        manager=manager
    )

    # --------------------------------------------------------
    # Fullscreen
    # --------------------------------------------------------

    window.showFullScreen()

    # --------------------------------------------------------
    # Event loop
    # --------------------------------------------------------

    if owns_app:
        return app.exec_()

    return window


# ============================================================
# DIRECT EXECUTION PROTECTION
# ============================================================

if __name__ == "__main__":

    raise RuntimeError(
        "main_window.py must be started through "
        "the EYES application entry point."
    )