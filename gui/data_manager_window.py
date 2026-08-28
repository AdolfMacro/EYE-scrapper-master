from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QFont, QColor
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from database.manager import DataManager


# ==========================================================
# OPTIONAL WEB ENGINE
# ==========================================================

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView

    WEB_ENGINE_AVAILABLE = True

except ImportError:
    QWebEngineView = None
    WEB_ENGINE_AVAILABLE = False


# ==========================================================
# STATISTICS GRAPH
# ==========================================================


class StatisticsGraph(QWidget):
    """
    Lightweight statistics graph.

    Uses QPainter only.
    No external chart dependency is required.

    Visual design
    -------------
    - EYES project color palette
    - Large readable typography
    - High contrast labels
    - Responsive bar layout
    """

    def __init__(
        self,
        parent=None,
    ) -> None:

        super().__init__(parent)

        self.values = {
            "Records": 0,
            "Phones": 0,
            "Coords": 0,
            "Addresses": 0,
        }

        self.setMinimumHeight(190)
        self.setMaximumHeight(225)

        self.setObjectName(
            "statistics_graph"
        )

    # ======================================================
    # UPDATE
    # ======================================================

    def set_values(
        self,
        records: int,
        phones: int,
        coordinates: int,
        addresses: int,
    ) -> None:

        self.values = {
            "Records": max(0, records),
            "Phones": max(0, phones),
            "Coords": max(0, coordinates),
            "Addresses": max(0, addresses),
        }

        self.update()

    # ======================================================
    # PAINT
    # ======================================================

    def paintEvent(
        self,
        event,
    ) -> None:

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing
        )

        rect = self.rect()

        # --------------------------------------------------
        # COLORS
        # --------------------------------------------------

        background = "#612E37"
        border = "#B83A14"

        accent = "#FED172"
        secondary = "#F3742B"

        white = "#FFFFFF"
        page_background = "#231650"

        # --------------------------------------------------
        # BACKGROUND
        # --------------------------------------------------

        painter.fillRect(
            rect,
            QBrush(
                self._color(
                    page_background
                )
            ),
        )

        # --------------------------------------------------
        # CARD
        # --------------------------------------------------

        card = QRectF(
            1,
            1,
            self.width() - 2,
            self.height() - 2,
        )

        painter.setBrush(
            QBrush(
                self._color(
                    background
                )
            )
        )

        painter.setPen(
            QPen(
                self._color(
                    border
                ),
                1,
            )
        )

        painter.drawRoundedRect(
            card,
            8,
            8,
        )

        # --------------------------------------------------
        # TITLE
        # --------------------------------------------------

        painter.setPen(
            QPen(
                self._color(
                    accent
                )
            )
        )

        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)

        painter.setFont(
            title_font
        )

        painter.drawText(
            14,
            25,
            "DATA DISTRIBUTION",
        )

        # --------------------------------------------------
        # GRAPH AREA
        # --------------------------------------------------

        graph_left = 18
        graph_right = self.width() - 18

        graph_top = 48
        graph_bottom = self.height() - 42

        graph_height = (
            graph_bottom - graph_top
        )

        values = list(
            self.values.values()
        )

        maximum = (
            max(values)
            if values
            else 0
        )

        # --------------------------------------------------
        # EMPTY STATE
        # --------------------------------------------------

        if maximum <= 0:

            painter.setPen(
                QPen(
                    self._color(
                        secondary
                    )
                )
            )

            empty_font = QFont()
            empty_font.setPointSize(10)
            empty_font.setBold(True)

            painter.setFont(
                empty_font
            )

            painter.drawText(
                graph_left,
                graph_top,
                graph_right - graph_left,
                graph_height,
                Qt.AlignCenter,
                "No statistics available",
            )

            painter.end()

            return

        # --------------------------------------------------
        # LABELS
        # --------------------------------------------------

        labels = list(
            self.values.keys()
        )

        bar_count = len(
            labels
        )

        available_width = (
            graph_right
            - graph_left
        )

        slot_width = (
            available_width
            / bar_count
        )

        bar_width = min(
            54,
            max(
                32,
                slot_width * 0.46,
            ),
        )

        # --------------------------------------------------
        # BAR COLORS
        # --------------------------------------------------

        colors = [
            "#FED172",
            "#F3742B",
            "#B83A14",
            "#FED172",
        ]

        # --------------------------------------------------
        # DRAW BARS
        # --------------------------------------------------

        for index, label in enumerate(
            labels
        ):

            value = self.values[
                label
            ]

            x = (
                graph_left
                + index * slot_width
                + (
                    slot_width
                    - bar_width
                )
                / 2
            )

            bar_height = (
                graph_height
                * value
                / maximum
            )

            if value > 0:

                bar_height = max(
                    4,
                    bar_height,
                )

            y = (
                graph_bottom
                - bar_height
            )

            # ------------------------------------------
            # BAR
            # ------------------------------------------

            painter.setBrush(
                QBrush(
                    self._color(
                        colors[index]
                    )
                )
            )

            painter.setPen(
                Qt.NoPen
            )

            painter.drawRoundedRect(
                QRectF(
                    x,
                    y,
                    bar_width,
                    max(
                        2,
                        bar_height,
                    ),
                ),
                5,
                5,
            )

            # ------------------------------------------
            # VALUE
            # ------------------------------------------

            painter.setPen(
                QPen(
                    self._color(
                        white
                    )
                )
            )

            value_font = QFont()
            value_font.setPointSize(10)
            value_font.setBold(True)

            painter.setFont(
                value_font
            )

            value_y = max(
                graph_top + 17,
                int(y - 7),
            )

            painter.drawText(
                int(x - 15),
                value_y,
                int(bar_width + 30),
                18,
                Qt.AlignCenter,
                f"{value:,}",
            )

            # ------------------------------------------
            # LABEL
            # ------------------------------------------

            label_font = QFont()
            label_font.setPointSize(9)
            label_font.setBold(True)

            painter.setFont(
                label_font
            )

            painter.setPen(
                QPen(
                    self._color(
                        accent
                    )
                )
            )

            painter.drawText(
                int(x - 25),
                graph_bottom + 20,
                int(bar_width + 50),
                20,
                Qt.AlignCenter,
                label,
            )

        painter.end()

    # ======================================================
    # COLOR
    # ======================================================

    @staticmethod
    def _color(
        value: str,
    ) -> QColor:

        return QColor(value)


# ==========================================================
# DATA MANAGER WINDOW
# ==========================================================


class DataManagerWindow(QDialog):
    """
    EYES-master Data Manager.

    Responsibilities
    ----------------
    - Discover scraper result databases
    - Open and inspect databases
    - Discover tables
    - Display records
    - Search records
    - Display database statistics
    - Display geographic records on a map
    - Display statistics graph
    - Refresh database/table data

    This window does NOT:
    - run scrapers
    - manage providers
    - start scraper processes
    - modify scraper configuration
    - merge databases automatically
    """

    # ==========================================================
    # PATH
    # ==========================================================

    DATABASE_DIRECTORY = (
        Path(__file__).resolve().parent.parent
        / "runtime"
        / "database"
    )

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(
        self,
        parent=None,
        data_manager: DataManager | None = None,
    ) -> None:

        super().__init__(parent)

        self.setWindowTitle(
            "EYES — DATA MANAGER"
        )

        self.setMinimumSize(
            1100,
            700,
        )

        self.resize(
            1350,
            850,
        )

        self.data_manager = (
            data_manager
            if data_manager is not None
            else DataManager()
        )

        self._current_rows: list[
            dict[str, Any]
        ] = []

        self._build_ui()

        self._load_databases()

    # ==========================================================
    # UI
    # ==========================================================

    def _build_ui(self) -> None:

        root = QVBoxLayout(
            self
        )

        root.setContentsMargins(
            22,
            22,
            22,
            22,
        )

        root.setSpacing(
            12
        )

        # ======================================================
        # HEADER
        # ======================================================

        header = QFrame()

        header_layout = QVBoxLayout(
            header
        )

        header_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        title = QLabel(
            "DATA MANAGER"
        )

        title.setObjectName(
            "title"
        )

        subtitle = QLabel(
            "Scraper runtime database "
            "inspection, statistics and geographic view"
        )

        subtitle.setObjectName(
            "subtitle"
        )

        header_layout.addWidget(
            title
        )

        header_layout.addWidget(
            subtitle
        )

        root.addWidget(
            header
        )

        # ======================================================
        # DATABASE BAR
        # ======================================================

        database_frame = QFrame()

        database_layout = QHBoxLayout(
            database_frame
        )

        database_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        database_layout.setSpacing(
            8
        )

        database_label = QLabel(
            "DATABASE"
        )

        database_label.setObjectName(
            "field_label"
        )

        self.database_combo = QComboBox()

        self.database_combo.setMinimumWidth(
            360
        )

        self.database_combo.currentIndexChanged.connect(
            self._database_changed
        )

        self.refresh_button = QPushButton(
            "⟳  REFRESH"
        )

        self.refresh_button.setObjectName(
            "secondary_button"
        )

        self.refresh_button.clicked.connect(
            self._load_databases
        )

        self.info_button = QPushButton(
            "ⓘ  INFO"
        )

        self.info_button.setObjectName(
            "secondary_button"
        )

        self.info_button.clicked.connect(
            self._show_database_info
        )

        database_layout.addWidget(
            database_label
        )

        database_layout.addWidget(
            self.database_combo,
            1,
        )

        database_layout.addWidget(
            self.refresh_button
        )

        database_layout.addWidget(
            self.info_button
        )

        root.addWidget(
            database_frame
        )

        # ======================================================
        # TABLE / SEARCH BAR
        # ======================================================

        table_frame = QFrame()

        table_layout = QHBoxLayout(
            table_frame
        )

        table_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        table_layout.setSpacing(
            8
        )

        table_label = QLabel(
            "TABLE"
        )

        table_label.setObjectName(
            "field_label"
        )

        self.table_combo = QComboBox()

        self.table_combo.setMinimumWidth(
            280
        )

        self.table_combo.currentIndexChanged.connect(
            self._table_changed
        )

        self.search_input = QLineEdit()

        self.search_input.setPlaceholderText(
            "Search records..."
        )

        self.search_input.returnPressed.connect(
            self._search
        )

        self.search_button = QPushButton(
            "⌕  SEARCH"
        )

        self.search_button.setObjectName(
            "primary_button"
        )

        self.search_button.clicked.connect(
            self._search
        )

        self.clear_button = QPushButton(
            "×  CLEAR"
        )

        self.clear_button.setObjectName(
            "secondary_button"
        )

        self.clear_button.clicked.connect(
            self._clear_search
        )

        table_layout.addWidget(
            table_label
        )

        table_layout.addWidget(
            self.table_combo
        )

        table_layout.addWidget(
            self.search_input,
            1,
        )

        table_layout.addWidget(
            self.search_button
        )

        table_layout.addWidget(
            self.clear_button
        )

        root.addWidget(
            table_frame
        )

        # ======================================================
        # STATISTICS
        # ======================================================

        statistics_layout = QHBoxLayout()

        statistics_layout.setSpacing(
            10
        )

        self.records_value = (
            self._create_stat_card(
                "RECORDS"
            )
        )

        self.phone_value = (
            self._create_stat_card(
                "PHONE NUMBERS"
            )
        )

        self.coordinate_value = (
            self._create_stat_card(
                "COORDINATES"
            )
        )

        self.address_value = (
            self._create_stat_card(
                "ADDRESSES"
            )
        )

        statistics_layout.addWidget(
            self.records_value[0],
            1,
        )

        statistics_layout.addWidget(
            self.phone_value[0],
            1,
        )

        statistics_layout.addWidget(
            self.coordinate_value[0],
            1,
        )

        statistics_layout.addWidget(
            self.address_value[0],
            1,
        )

        root.addLayout(
            statistics_layout
        )

        # ======================================================
        # STATUS
        # ======================================================

        self.status_label = QLabel(
            "No database selected."
        )

        self.status_label.setObjectName(
            "status"
        )

        root.addWidget(
            self.status_label
        )

        # ======================================================
        # CONTENT
        # ======================================================

        content_frame = QFrame()

        content_layout = QHBoxLayout(
            content_frame
        )

        content_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        content_layout.setSpacing(
            12
        )

        # ======================================================
        # RECORDS
        # ======================================================

        records_frame = QFrame()

        records_layout = QVBoxLayout(
            records_frame
        )

        records_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        records_layout.setSpacing(
            7
        )

        records_title = QLabel(
            "RECORDS"
        )

        records_title.setObjectName(
            "section_title"
        )

        self.records_table = QTableWidget()

        self.records_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        self.records_table.setSelectionBehavior(
            QTableWidget.SelectRows
        )

        self.records_table.setSelectionMode(
            QTableWidget.SingleSelection
        )

        self.records_table.setAlternatingRowColors(
            True
        )

        self.records_table.verticalHeader().setVisible(
            False
        )

        self.records_table.horizontalHeader().setStretchLastSection(
            True
        )

        records_layout.addWidget(
            records_title
        )

        records_layout.addWidget(
            self.records_table,
            1,
        )

        content_layout.addWidget(
            records_frame,
            3,
        )

        # ======================================================
        # RIGHT SIDE
        # ======================================================

        right_frame = QFrame()

        right_layout = QVBoxLayout(
            right_frame
        )

        right_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        right_layout.setSpacing(
            8
        )

        # ======================================================
        # MAP
        # ======================================================

        map_title = QLabel(
            "MAP VIEW"
        )

        map_title.setObjectName(
            "section_title"
        )

        right_layout.addWidget(
            map_title
        )

        if WEB_ENGINE_AVAILABLE:

            self.map_view = QWebEngineView()

            self.map_view.setMinimumWidth(
                350
            )

            self.map_view.setMinimumHeight(
                270
            )

            right_layout.addWidget(
                self.map_view,
                4,
            )

            self._set_empty_map()

        else:

            self.map_view = None

            map_unavailable = QLabel(
                "MAP VIEW\n\n"
                "QtWebEngine is not available."
            )

            map_unavailable.setAlignment(
                Qt.AlignCenter
            )

            map_unavailable.setObjectName(
                "map_unavailable"
            )

            right_layout.addWidget(
                map_unavailable,
                4,
            )

        # ======================================================
        # GRAPH
        # ======================================================

        graph_title = QLabel(
            "STATISTICS"
        )

        graph_title.setObjectName(
            "section_title"
        )

        right_layout.addWidget(
            graph_title
        )

        self.statistics_graph = (
            StatisticsGraph()
        )

        right_layout.addWidget(
            self.statistics_graph,
            2,
        )

        content_layout.addWidget(
            right_frame,
            2,
        )

        root.addWidget(
            content_frame,
            1,
        )

        # ======================================================
        # BOTTOM
        # ======================================================

        bottom = QHBoxLayout()

        self.count_label = QLabel(
            "Records: 0"
        )

        self.count_label.setObjectName(
            "bottom_count"
        )

        self.reload_button = QPushButton(
            "↻  RELOAD"
        )

        self.reload_button.setObjectName(
            "secondary_button"
        )

        self.reload_button.clicked.connect(
            self._reload_current_table
        )

        self.close_button = QPushButton(
            "CLOSE"
        )

        self.close_button.setObjectName(
            "close_button"
        )

        self.close_button.clicked.connect(
            self.close
        )

        bottom.addWidget(
            self.count_label
        )

        bottom.addStretch()

        bottom.addWidget(
            self.reload_button
        )

        bottom.addWidget(
            self.close_button
        )

        root.addLayout(
            bottom
        )

        # ======================================================
        # STYLE
        # ======================================================

        self.setStyleSheet(
            """
            QDialog {
                background: #231650;
                color: #FFFFFF;
            }

            QFrame {
                background: transparent;
            }

            QLabel {
                color: #FED172;
            }

            QLabel#title {
                color: #FED172;
                font-size: 28px;
                font-weight: 800;
                padding: 0;
            }

            QLabel#subtitle {
                color: #F3742B;
                font-size: 13px;
                padding-top: 2px;
            }

            QLabel#field_label {
                color: #FED172;
                font-size: 12px;
                font-weight: bold;
                min-width: 65px;
            }

            QLabel#section_title {
                color: #FED172;
                font-size: 14px;
                font-weight: bold;
                padding: 2px 0;
            }

            QLabel#status {
                color: #F3742B;
                font-size: 12px;
                padding: 3px 2px;
            }

            QLabel#bottom_count {
                color: #F3742B;
                font-size: 12px;
                font-weight: bold;
            }

            QLabel#map_unavailable {
                background: #612E37;
                border: 1px solid #B83A14;
                border-radius: 7px;
                color: #FED172;
                font-size: 13px;
            }

            QComboBox,
            QLineEdit {
                background: #612E37;
                color: #FFFFFF;
                border: 1px solid #B83A14;
                border-radius: 6px;
                padding: 9px 11px;
                min-height: 20px;
                font-size: 12px;
            }

            QComboBox:hover,
            QLineEdit:hover,
            QLineEdit:focus {
                border: 1px solid #FED172;
            }

            QComboBox QAbstractItemView {
                background: #612E37;
                color: #FFFFFF;
                selection-background-color: #B83A14;
                selection-color: #FED172;
                border: 1px solid #B83A14;
                font-size: 12px;
            }

            QPushButton {
                min-height: 20px;
                padding: 9px 16px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }

            QPushButton#primary_button {
                background: #B83A14;
                color: #FED172;
                border: 1px solid #F3742B;
            }

            QPushButton#primary_button:hover {
                background: #F3742B;
                color: #231650;
                border-color: #FED172;
            }

            QPushButton#primary_button:pressed {
                background: #FED172;
                color: #231650;
            }

            QPushButton#secondary_button {
                background: #612E37;
                color: #FED172;
                border: 1px solid #B83A14;
            }

            QPushButton#secondary_button:hover {
                background: #B83A14;
                color: #FFFFFF;
                border-color: #F3742B;
            }

            QPushButton#secondary_button:pressed {
                background: #F3742B;
                color: #231650;
            }

            QPushButton#close_button {
                background: #231650;
                color: #F3742B;
                border: 1px solid #B83A14;
            }

            QPushButton#close_button:hover {
                background: #B83A14;
                color: #FFFFFF;
            }

            QTableWidget {
                background: #231650;
                alternate-background-color: #612E37;
                color: #FFFFFF;
                gridline-color: #612E37;
                border: 1px solid #612E37;
                border-radius: 7px;
                selection-background-color: #B83A14;
                selection-color: #FED172;
                font-size: 11px;
            }

            QTableWidget::item {
                padding: 6px;
            }

            QHeaderView::section {
                background: #612E37;
                color: #FED172;
                padding: 8px;
                border: 0;
                border-bottom: 1px solid #B83A14;
                font-weight: bold;
                font-size: 11px;
            }

            QScrollBar:vertical {
                background: #231650;
                width: 10px;
                margin: 0;
            }

            QScrollBar::handle:vertical {
                background: #612E37;
                min-height: 25px;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical:hover {
                background: #B83A14;
            }

            QScrollBar:horizontal {
                background: #231650;
                height: 10px;
            }

            QScrollBar::handle:horizontal {
                background: #612E37;
                min-width: 25px;
                border-radius: 5px;
            }
            """
        )

    # ==========================================================
    # STAT CARD
    # ==========================================================

    def _create_stat_card(
        self,
        title: str,
    ) -> tuple[QFrame, QLabel]:

        frame = QFrame()

        frame.setObjectName(
            "stat_card"
        )

        layout = QVBoxLayout(
            frame
        )

        layout.setContentsMargins(
            14,
            10,
            14,
            10,
        )

        layout.setSpacing(
            3
        )

        title_label = QLabel(
            title
        )

        title_label.setObjectName(
            "stat_title"
        )

        value_label = QLabel(
            "0"
        )

        value_label.setObjectName(
            "stat_value"
        )

        value_label.setAlignment(
            Qt.AlignLeft
            | Qt.AlignVCenter
        )

        layout.addWidget(
            title_label
        )

        layout.addWidget(
            value_label
        )

        frame.setStyleSheet(
            """
            QFrame#stat_card {
                background: #612E37;
                border: 1px solid #B83A14;
                border-radius: 7px;
            }

            QLabel#stat_title {
                color: #FED172;
                font-size: 11px;
                font-weight: bold;
            }

            QLabel#stat_value {
                color: #FED172;
                font-size: 23px;
                font-weight: bold;
            }
            """
        )

        return (
            frame,
            value_label,
        )

    # ==========================================================
    # DATABASE DISCOVERY
    # ==========================================================

    def _load_databases(
        self,
    ) -> None:

        current = (
            self.database_combo.currentData()
        )

        self.database_combo.blockSignals(
            True
        )

        self.database_combo.clear()

        try:

            database_dir = (
                self.DATABASE_DIRECTORY
            )

            database_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            databases = []

            for path in sorted(
                database_dir.glob(
                    "*.db"
                )
            ):

                if path.is_file():

                    databases.append(
                        {
                            "name": path.name,
                            "path": str(
                                path
                            ),
                        }
                    )

            for item in databases:

                self.database_combo.addItem(
                    item["name"],
                    item["path"],
                )

            if current:

                index = (
                    self.database_combo.findData(
                        current
                    )
                )

                if index >= 0:

                    self.database_combo.setCurrentIndex(
                        index
                    )

            self.status_label.setText(
                f"Databases: {len(databases)}"
            )

        except Exception as exc:

            self.status_label.setText(
                "Database discovery failed: "
                f"{exc}"
            )

        finally:

            self.database_combo.blockSignals(
                False
            )

        if self.database_combo.count():

            self._database_changed(
                self.database_combo.currentIndex()
            )

        else:

            self._clear_database_view()

    # ==========================================================
    # DATABASE CHANGE
    # ==========================================================

    def _database_changed(
        self,
        index: int,
    ) -> None:

        if index < 0:
            return

        path = (
            self.database_combo.itemData(
                index
            )
        )

        if not path:
            return

        try:

            self.data_manager.open_database(
                Path(path)
            )

            self._load_tables()

            self.status_label.setText(
                f"Opened: {Path(path).name}"
            )

        except Exception as exc:

            self._clear_database_view()

            self.status_label.setText(
                "Unable to open database: "
                f"{exc}"
            )

    # ==========================================================
    # TABLE DISCOVERY
    # ==========================================================

    def _load_tables(
        self,
    ) -> None:

        self.table_combo.blockSignals(
            True
        )

        self.table_combo.clear()

        try:

            tables = (
                self.data_manager.list_tables()
            )

            for table in tables:

                self.table_combo.addItem(
                    table,
                    table,
                )

        except Exception as exc:

            self.status_label.setText(
                "Unable to read tables: "
                f"{exc}"
            )

        finally:

            self.table_combo.blockSignals(
                False
            )

        if self.table_combo.count():

            self.table_combo.setCurrentIndex(
                0
            )

            self._table_changed(
                0
            )

        else:

            self._clear_table_view()

    # ==========================================================
    # TABLE CHANGE
    # ==========================================================

    def _table_changed(
        self,
        index: int,
    ) -> None:

        if index < 0:
            return

        self._reload_current_table()

    # ==========================================================
    # LOAD RECORDS
    # ==========================================================

    def _reload_current_table(
        self,
    ) -> None:

        table = (
            self.table_combo.currentData()
        )

        if not table:
            return

        try:

            rows = (
                self.data_manager.fetch_rows(
                    table,
                    limit=500,
                )
            )

            self._populate_table(
                rows
            )

            self._update_statistics(
                rows
            )

            self._update_map(
                rows
            )

            self.status_label.setText(
                f"Table: {table}"
            )

        except Exception as exc:

            self.status_label.setText(
                "Unable to load records: "
                f"{exc}"
            )

            self._clear_table_view()

    # ==========================================================
    # SEARCH
    # ==========================================================

    def _search(
        self,
    ) -> None:

        table = (
            self.table_combo.currentData()
        )

        if not table:
            return

        text = (
            self.search_input
            .text()
            .strip()
        )

        try:

            rows = (
                self.data_manager.search_table(
                    table,
                    text,
                    limit=500,
                )
            )

            self._populate_table(
                rows
            )

            self._update_statistics(
                rows
            )

            self._update_map(
                rows
            )

            if text:

                self.status_label.setText(
                    f"Search: {text} | "
                    f"Results: {len(rows)}"
                )

            else:

                self.status_label.setText(
                    f"Table: {table}"
                )

        except Exception as exc:

            self.status_label.setText(
                "Search failed: "
                f"{exc}"
            )

    # ==========================================================
    # CLEAR SEARCH
    # ==========================================================

    def _clear_search(
        self,
    ) -> None:

        self.search_input.clear()

        self._reload_current_table()

    # ==========================================================
    # POPULATE TABLE
    # ==========================================================

    def _populate_table(
        self,
        rows: list[dict[str, Any]],
    ) -> None:

        self._current_rows = list(
            rows
        )

        self.records_table.clear()

        if not rows:

            self.records_table.setRowCount(
                0
            )

            self.records_table.setColumnCount(
                0
            )

            self.count_label.setText(
                "Records: 0"
            )

            return

        columns: list[str] = []

        for row in rows:

            for key in row.keys():

                key = str(key)

                if key not in columns:

                    columns.append(
                        key
                    )

        self.records_table.setColumnCount(
            len(columns)
        )

        self.records_table.setHorizontalHeaderLabels(
            columns
        )

        self.records_table.setRowCount(
            len(rows)
        )

        for row_index, row in enumerate(
            rows
        ):

            for column_index, column in enumerate(
                columns
            ):

                value = row.get(
                    column,
                    "",
                )

                if value is None:

                    value = ""

                item = QTableWidgetItem(
                    str(value)
                )

                item.setFlags(
                    item.flags()
                    & ~Qt.ItemIsEditable
                )

                self.records_table.setItem(
                    row_index,
                    column_index,
                    item,
                )

        self.records_table.resizeColumnsToContents()

        self.count_label.setText(
            f"Records: {len(rows):,}"
        )

    # ==========================================================
    # STATISTICS
    # ==========================================================

    def _update_statistics(
        self,
        rows: list[dict[str, Any]],
    ) -> None:

        record_count = len(
            rows
        )

        phone_count = 0

        coordinate_count = 0

        address_count = 0

        for row in rows:

            phone_count += (
                self._count_phone_values(
                    row
                )
            )

            if (
                self._extract_coordinates(
                    row
                )
                is not None
            ):

                coordinate_count += 1

            if self._has_value(
                row,
                (
                    "address",
                    "full_address",
                    "location",
                    "addr",
                ),
            ):

                address_count += 1

        self.records_value[1].setText(
            f"{record_count:,}"
        )

        self.phone_value[1].setText(
            f"{phone_count:,}"
        )

        self.coordinate_value[1].setText(
            f"{coordinate_count:,}"
        )

        self.address_value[1].setText(
            f"{address_count:,}"
        )

        self.statistics_graph.set_values(
            record_count,
            phone_count,
            coordinate_count,
            address_count,
        )

    # ==========================================================
    # PHONE COUNT
    # ==========================================================

    @staticmethod
    def _count_phone_values(
        row: dict[str, Any],
    ) -> int:

        phone_keys = {
            "phone",
            "phone_number",
            "phone_numbers",
            "telephone",
            "tel",
            "mobile",
            "mobile_number",
        }

        count = 0

        for key, value in row.items():

            normalized_key = (
                str(key)
                .lower()
                .strip()
            )

            if normalized_key not in phone_keys:
                continue

            if value is None:
                continue

            text = str(
                value
            ).strip()

            if not text:
                continue

            separators = (
                ",",
                ";",
                "|",
                "\n",
            )

            parts = [
                text
            ]

            for separator in separators:

                new_parts = []

                for part in parts:

                    new_parts.extend(
                        part.split(
                            separator
                        )
                    )

                parts = new_parts

            valid = [
                part.strip()
                for part in parts
                if part.strip()
            ]

            count += len(
                valid
            )

        return count

    # ==========================================================
    # VALUE DETECTION
    # ==========================================================

    @staticmethod
    def _has_value(
        row: dict[str, Any],
        keys: tuple[str, ...],
    ) -> bool:

        normalized = {
            str(key).lower().strip(): value
            for key, value in row.items()
        }

        for key in keys:

            value = normalized.get(
                key.lower()
            )

            if value is None:
                continue

            if str(value).strip():

                return True

        return False

    # ==========================================================
    # COORDINATE EXTRACTION
    # ==========================================================

    @staticmethod
    def _extract_coordinates(
        row: dict[str, Any],
    ) -> tuple[float, float] | None:

        normalized = {
            str(key).lower().strip(): value
            for key, value in row.items()
        }

        latitude = None

        longitude = None

        for key in (
            "latitude",
            "lat",
            "y",
        ):

            if key not in normalized:
                continue

            try:

                latitude = float(
                    normalized[key]
                )

                break

            except (
                TypeError,
                ValueError,
            ):

                continue

        for key in (
            "longitude",
            "lon",
            "lng",
            "long",
            "x",
        ):

            if key not in normalized:
                continue

            try:

                longitude = float(
                    normalized[key]
                )

                break

            except (
                TypeError,
                ValueError,
            ):

                continue

        if (
            latitude is None
            or longitude is None
        ):

            return None

        if not (
            -90 <= latitude <= 90
        ):

            return None

        if not (
            -180 <= longitude <= 180
        ):

            return None

        return (
            latitude,
            longitude,
        )

    # ==========================================================
    # MAP EMPTY
    # ==========================================================

    def _set_empty_map(
        self,
    ) -> None:

        if self.map_view is None:
            return

        html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">

<style>

html,
body {
    width: 100%;
    height: 100%;
    margin: 0;
    background: #231650;
    color: #FED172;
    font-family: Arial, sans-serif;
}

body {
    display: flex;
    align-items: center;
    justify-content: center;
}

.container {
    text-align: center;
}

.title {
    font-size: 20px;
    font-weight: bold;
}

.subtitle {
    margin-top: 8px;
    color: #F3742B;
    font-size: 12px;
}

</style>
</head>

<body>

<div class="container">

    <div class="title">
        MAP VIEW
    </div>

    <div class="subtitle">
        No geographic records available
    </div>

</div>

</body>
</html>
"""

        self.map_view.setHtml(
            html
        )

    # ==========================================================
    # MAP UPDATE
    # ==========================================================

    def _update_map(
        self,
        rows: list[dict[str, Any]],
    ) -> None:

        if self.map_view is None:
            return

        points = []

        for row in rows:

            coordinates = (
                self._extract_coordinates(
                    row
                )
            )

            if coordinates is None:
                continue

            latitude, longitude = (
                coordinates
            )

            name = (
                self._get_first_value(
                    row,
                    (
                        "name",
                        "school_name",
                        "title",
                    ),
                )
            )

            address = (
                self._get_first_value(
                    row,
                    (
                        "address",
                        "full_address",
                        "location",
                        "addr",
                    ),
                )
            )

            phone = (
                self._get_first_value(
                    row,
                    (
                        "phone",
                        "phone_number",
                        "telephone",
                        "tel",
                        "mobile",
                    ),
                )
            )

            points.append(
                {
                    "lat": latitude,
                    "lon": longitude,
                    "name": name,
                    "phone": phone,
                    "address": address,
                }
            )

        if not points:

            self._set_empty_map()

            return

        points_json = json.dumps(
            points,
            ensure_ascii=False,
        )

        html = f"""
<!DOCTYPE html>
<html>

<head>

<meta charset="utf-8">

<meta
    name="viewport"
    content="width=device-width,
             initial-scale=1.0"
>

<link
    rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
/>

<script
    src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js">
</script>

<style>

html,
body,
#map {{
    width: 100%;
    height: 100%;
    margin: 0;
    padding: 0;
}}

body {{
    background: #231650;
}}

.leaflet-popup-content-wrapper,
.leaflet-popup-tip {{
    background: #231650;
    color: #FED172;
}}

.leaflet-popup-content {{
    font-family: Arial, sans-serif;
    font-size: 12px;
}}

.popup-title {{
    color: #FED172;
    font-weight: bold;
    font-size: 14px;
    margin-bottom: 5px;
}}

.popup-value {{
    color: #FFFFFF;
    margin-top: 3px;
}}

</style>

</head>

<body>

<div id="map"></div>

<script>

const points = {points_json};

const map = L.map(
    "map"
).setView(
    [
        points[0].lat,
        points[0].lon
    ],
    11
);

L.tileLayer(
    "https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png",
    {{
        maxZoom: 19,
        attribution:
            "&copy; OpenStreetMap contributors"
    }}
).addTo(
    map
);

const bounds = [];

points.forEach(
    function(point) {{

        const marker = L.marker(
            [
                point.lat,
                point.lon
            ]
        ).addTo(
            map
        );

        let html = "";

        if (point.name) {{

            html +=
                '<div class="popup-title">'
                + point.name
                + "</div>";

        }}

        if (point.address) {{

            html +=
                '<div class="popup-value">'
                + point.address
                + "</div>";

        }}

        if (point.phone) {{

            html +=
                '<div class="popup-value">'
                + point.phone
                + "</div>";

        }}

        marker.bindPopup(
            html || "Location"
        );

        bounds.push(
            [
                point.lat,
                point.lon
            ]
        );

    }}
);

if (bounds.length > 1) {{

    map.fitBounds(
        bounds,
        {{
            padding: [25, 25]
        }}
    );

}}

</script>

</body>

</html>
"""

        self.map_view.setHtml(
            html
        )

    # ==========================================================
    # VALUE HELPER
    # ==========================================================

    @staticmethod
    def _get_first_value(
        row: dict[str, Any],
        keys: tuple[str, ...],
    ) -> str:

        normalized = {
            str(key).lower().strip(): value
            for key, value in row.items()
        }

        for key in keys:

            value = normalized.get(
                key.lower()
            )

            if value is None:
                continue

            text = str(
                value
            ).strip()

            if text:

                return text

        return ""

    # ==========================================================
    # DATABASE INFO
    # ==========================================================

    def _show_database_info(
        self,
    ) -> None:

        path = (
            self.database_combo.currentData()
        )

        if not path:
            return

        try:

            info = (
                self.data_manager.database_info(
                    Path(path)
                )
            )

            lines = [
                "Database: "
                f"{info.get('database', '')}",
                "Path: "
                f"{info.get('path', '')}",
                "Size: "
                f"{info.get('size', 0):,} bytes",
                "",
                "Tables:",
            ]

            for table in info.get(
                "tables",
                [],
            ):

                lines.append(
                    f"  • {table['name']} "
                    f"({table['records']:,} records)"
                )

                columns = table.get(
                    "columns"
                )

                if columns:

                    lines.append(
                        "    Columns: "
                        + ", ".join(
                            columns
                        )
                    )

            QMessageBox.information(
                self,
                "Database Information",
                "\n".join(
                    lines
                ),
            )

        except Exception as exc:

            QMessageBox.critical(
                self,
                "Database Error",
                str(exc),
            )

    # ==========================================================
    # CLEAR DATABASE
    # ==========================================================

    def _clear_database_view(
        self,
    ) -> None:

        self.table_combo.clear()

        self._clear_table_view()

        self.status_label.setText(
            "No database selected."
        )

    # ==========================================================
    # CLEAR TABLE
    # ==========================================================

    def _clear_table_view(
        self,
    ) -> None:

        self._current_rows = []

        self.records_table.clear()

        self.records_table.setRowCount(
            0
        )

        self.records_table.setColumnCount(
            0
        )

        self.count_label.setText(
            "Records: 0"
        )

        self.records_value[1].setText(
            "0"
        )

        self.phone_value[1].setText(
            "0"
        )

        self.coordinate_value[1].setText(
            "0"
        )

        self.address_value[1].setText(
            "0"
        )

        self.statistics_graph.set_values(
            0,
            0,
            0,
            0,
        )

        self._set_empty_map()

    # ==========================================================
    # CLOSE
    # ==========================================================

    def closeEvent(
        self,
        event,
    ) -> None:

        try:

            self.data_manager.close()

        except Exception:

            pass

        event.accept()