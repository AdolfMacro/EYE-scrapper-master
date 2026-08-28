import sys

from PyQt5.QtCore import (
    Qt,
    QThread,
    QTimer,
    pyqtSignal,
)

from PyQt5.QtGui import (
    QPainter,
    QPen,
    QBrush,
    QFont,
)

from PyQt5.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config.search import SearchConfig
from scraper.controller import ScraperController
from database.manager import DataManager


# ==========================================================
# COLORS
# ==========================================================

BG = "#111114"
PANEL = "#1B1B1F"
PANEL_LIGHT = "#242429"

SECONDARY = "#55555C"

CRIMSON_DARK = "#72182A"
CRIMSON = "#950740"
CRIMSON_BRIGHT = "#C3073F"

WHITE = "#F5F5F7"
MUTED = "#9999A1"

BLACK = "#0B0B0D"


# ==========================================================
# EYE WIDGET
# ==========================================================

class EyeIndicator(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.angle = 0
        self.running = False

        self.timer = QTimer(self)

        self.timer.timeout.connect(
            self.rotate
        )

        self.setFixedSize(
            42,
            42
        )

    # ------------------------------------------------------

    def start(self):

        self.running = True

        self.timer.start(
            40
        )

        self.update()

    # ------------------------------------------------------

    def stop(self):

        self.running = False

        self.timer.stop()

        self.angle = 0

        self.update()

    # ------------------------------------------------------

    def rotate(self):

        self.angle += 8

        if self.angle >= 360:

            self.angle = 0

        self.update()

    # ------------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing
        )

        center = self.rect().center()

        painter.translate(
            center
        )

        painter.rotate(
            self.angle
        )

        # Outer eye

        pen = QPen(
            CRIMSON_BRIGHT,
            2
        )

        painter.setPen(
            pen
        )

        painter.setBrush(
            Qt.NoBrush
        )

        painter.drawEllipse(
            -15,
            -9,
            30,
            18
        )

        # Iris

        painter.setPen(
            Qt.NoPen
        )

        painter.setBrush(
            QBrush(
                CRIMSON_BRIGHT
            )
        )

        painter.drawEllipse(
            -5,
            -5,
            10,
            10
        )

        # Center

        painter.setBrush(
            QBrush(
                BLACK
            )
        )

        painter.drawEllipse(
            -2,
            -2,
            4,
            4
        )

        painter.end()


# ==========================================================
# SCRAPER CONFIG DIALOG
# ==========================================================

class ScraperConfigDialog(QDialog):

    def __init__(
        self,
        parent=None
    ):

        super().__init__(
            parent
        )

        self.setWindowTitle(
            "START SCRAPING"
        )

        self.setModal(
            True
        )

        self.resize(
            560,
            540
        )

        self.build_ui()

    # ======================================================
    # UI
    # ======================================================

    def build_ui(self):

        layout = QVBoxLayout()

        layout.setContentsMargins(
            40,
            35,
            40,
            35
        )

        layout.setSpacing(
            24
        )

        self.setLayout(
            layout
        )

        # --------------------------------------------------
        # TITLE
        # --------------------------------------------------

        title = QLabel(
            "START SCRAPING"
        )

        title.setObjectName(
            "dialogTitle"
        )

        layout.addWidget(
            title
        )

        subtitle = QLabel(
            "Configure the discovery process."
        )

        subtitle.setObjectName(
            "dialogSubtitle"
        )

        layout.addWidget(
            subtitle
        )

        # --------------------------------------------------
        # FORM
        # --------------------------------------------------

        form = QFormLayout()

        form.setSpacing(
            18
        )

        form.setLabelAlignment(
            Qt.AlignLeft
        )

        self.keyword = QLineEdit()

        self.keyword.setText(
            "مدرسه"
        )

        self.province = QLineEdit()

        self.city = QLineEdit()

        self.radius = QLineEdit()

        self.radius.setText(
            "5"
        )

        self.provider = QComboBox()

        self.provider.addItems(
            [
                "google",
                "duckduckgo",
                "osm",
            ]
        )

        form.addRow(
            "KEYWORD",
            self.keyword
        )

        form.addRow(
            "PROVINCE",
            self.province
        )

        form.addRow(
            "CITY",
            self.city
        )

        form.addRow(
            "RADIUS KM",
            self.radius
        )

        form.addRow(
            "PROVIDER",
            self.provider
        )

        layout.addLayout(
            form
        )

        layout.addStretch()

        # --------------------------------------------------
        # BUTTONS
        # --------------------------------------------------

        buttons = QHBoxLayout()

        buttons.setSpacing(
            15
        )

        cancel = QPushButton(
            "CANCEL"
        )

        cancel.setObjectName(
            "secondaryButton"
        )

        cancel.clicked.connect(
            self.reject
        )

        start = QPushButton(
            "START SCRAPING"
        )

        start.setObjectName(
            "primaryButton"
        )

        start.clicked.connect(
            self.accept
        )

        buttons.addWidget(
            cancel
        )

        buttons.addWidget(
            start
        )

        layout.addLayout(
            buttons
        )

    # ======================================================
    # CONFIG
    # ======================================================

    def get_config(self):

        try:

            radius = float(
                self.radius.text().strip()
            )

        except ValueError:

            radius = 5.0

        return SearchConfig(

            keyword=(
                self.keyword.text().strip()
                or
                "مدرسه"
            ),

            province=(
                self.province.text().strip()
            ),

            city=(
                self.city.text().strip()
            ),

            radius=radius,

            provider=(
                self.provider.currentText()
            ),
        )


# ==========================================================
# SCRAPER WORKER
# ==========================================================

class ScraperWorker(QThread):

    log_signal = pyqtSignal(str)

    progress_signal = pyqtSignal(dict)

    finished_signal = pyqtSignal(list)

    error_signal = pyqtSignal(str)

    # ------------------------------------------------------

    def __init__(
        self,
        config,
        parent=None
    ):

        super().__init__(
            parent
        )

        self.config = config

        self.controller = None

        self._stop_requested = False

    # ======================================================
    # RUN
    # ======================================================

    def run(self):

        try:

            self._stop_requested = False

            # IMPORTANT:
            # ScraperController is created INSIDE QThread.
            # This prevents thread affinity problems.

            self.controller = ScraperController(

                logger=self.thread_log,

                progress=self.thread_progress,
            )

            if self._stop_requested:

                return

            self.controller.start(
                self.config
            )

            engine = getattr(
                self.controller,
                "engine",
                None
            )

            if engine is None:

                self.finished_signal.emit(
                    []
                )

                return

            while getattr(
                engine,
                "running",
                False
            ):

                if self._stop_requested:

                    break

                self.msleep(
                    100
                )

            if self._stop_requested:

                return

            results = getattr(
                engine,
                "results",
                []
            )

            if results is None:

                results = []

            self.finished_signal.emit(
                results
            )

        except Exception as error:

            if not self._stop_requested:

                self.error_signal.emit(
                    str(error)
                )

    # ======================================================
    # LOG
    # ======================================================

    def thread_log(
        self,
        text
    ):

        self.log_signal.emit(
            str(text)
        )

    # ======================================================
    # PROGRESS
    # ======================================================

    def thread_progress(
        self,
        data
    ):

        if isinstance(
            data,
            dict
        ):

            self.progress_signal.emit(
                data
            )

    # ======================================================
    # STOP
    # ======================================================

    def stop_scraper(self):

        self._stop_requested = True

        try:

            if self.controller:

                self.controller.stop()

        except Exception:

            pass


# ==========================================================
# SCRAPER WINDOW
# ==========================================================

class ScraperWindow(QWidget):

    back_signal = pyqtSignal()

    def __init__(
        self,
        config,
        parent=None
    ):

        super().__init__(
            parent
        )

        self.config = config

        self.worker = None

        self.running = False

        self.eye = None

        self.build_ui()

    # ======================================================
    # UI
    # ======================================================

    def build_ui(self):

        layout = QVBoxLayout()

        layout.setContentsMargins(
            55,
            45,
            55,
            45
        )

        layout.setSpacing(
            25
        )

        self.setLayout(
            layout
        )

        # --------------------------------------------------
        # HEADER
        # --------------------------------------------------

        header = QHBoxLayout()

        self.eye = EyeIndicator()

        header.addWidget(
            self.eye
        )

        title = QLabel(
            "EYE SCRAPPER"
        )

        title.setObjectName(
            "pageTitle"
        )

        header.addWidget(
            title
        )

        header.addStretch()

        self.status = QLabel(
            "READY"
        )

        self.status.setObjectName(
            "status"
        )

        header.addWidget(
            self.status
        )

        layout.addLayout(
            header
        )

        # --------------------------------------------------
        # DESCRIPTION
        # --------------------------------------------------

        description = QLabel(
            self.config.describe()
        )

        description.setObjectName(
            "description"
        )

        description.setWordWrap(
            True
        )

        layout.addWidget(
            description
        )

        # --------------------------------------------------
        # PROGRESS
        # --------------------------------------------------

        self.progress = QProgressBar()

        self.progress.setRange(
            0,
            0
        )

        self.progress.setValue(
            0
        )

        layout.addWidget(
            self.progress
        )

        # --------------------------------------------------
        # STATISTICS
        # --------------------------------------------------

        stats = QHBoxLayout()

        self.query_label = self.stat_card(
            "QUERIES",
            "0"
        )

        self.page_label = self.stat_card(
            "PAGES",
            "0"
        )

        self.result_label = self.stat_card(
            "RESULTS",
            "0"
        )

        stats.addWidget(
            self.query_label
        )

        stats.addWidget(
            self.page_label
        )

        stats.addWidget(
            self.result_label
        )

        layout.addLayout(
            stats
        )

        # --------------------------------------------------
        # LOG
        # --------------------------------------------------

        log_title = QLabel(
            "ACTIVITY"
        )

        log_title.setObjectName(
            "sectionTitle"
        )

        layout.addWidget(
            log_title
        )

        self.log = QTextEdit()

        self.log.setReadOnly(
            True
        )

        layout.addWidget(
            self.log
        )

        # --------------------------------------------------
        # BUTTONS
        # --------------------------------------------------

        buttons = QHBoxLayout()

        back_button = QPushButton(
            "BACK"
        )

        back_button.setObjectName(
            "secondaryButton"
        )

        back_button.clicked.connect(
            self.back
        )

        self.stop_button = QPushButton(
            "STOP SCRAPING"
        )

        self.stop_button.setObjectName(
            "dangerButton"
        )

        self.stop_button.clicked.connect(
            self.stop
        )

        buttons.addWidget(
            back_button
        )

        buttons.addStretch()

        buttons.addWidget(
            self.stop_button
        )

        layout.addLayout(
            buttons
        )

        self.start()

    # ======================================================
    # STAT CARD
    # ======================================================

    def stat_card(
        self,
        title,
        value
    ):

        frame = QFrame()

        frame.setObjectName(
            "statCard"
        )

        layout = QVBoxLayout()

        layout.setContentsMargins(
            18,
            15,
            18,
            15
        )

        frame.setLayout(
            layout
        )

        title_label = QLabel(
            title
        )

        title_label.setObjectName(
            "statTitle"
        )

        value_label = QLabel(
            value
        )

        value_label.setObjectName(
            "statValue"
        )

        layout.addWidget(
            title_label
        )

        layout.addWidget(
            value_label
        )

        return frame

    # ======================================================
    # START
    # ======================================================

    def start(self):

        if self.running:

            return

        self.running = True

        self.status.setText(
            "RUNNING"
        )

        self.eye.start()

        self.stop_button.setEnabled(
            True
        )

        self.progress.setRange(
            0,
            0
        )

        self.worker = ScraperWorker(
            self.config
        )

        self.worker.log_signal.connect(
            self.add_log
        )

        self.worker.progress_signal.connect(
            self.update_progress
        )

        self.worker.finished_signal.connect(
            self.finished
        )

        self.worker.error_signal.connect(
            self.error
        )

        self.worker.finished.connect(
            self.worker_finished
        )

        self.worker.start()

    # ======================================================
    # LOG
    # ======================================================

    def add_log(
        self,
        text
    ):

        self.log.append(
            str(text)
        )

    # ======================================================
    # PROGRESS
    # ======================================================

    def update_progress(
        self,
        data
    ):

        queries = data.get(
            "queries",
            0
        )

        pages = data.get(
            "pages",
            0
        )

        results = data.get(
            "results",
            0
        )

        query_value = self.query_label.findChild(
            QLabel,
            "statValue"
        )

        page_value = self.page_label.findChild(
            QLabel,
            "statValue"
        )

        result_value = self.result_label.findChild(
            QLabel,
            "statValue"
        )

        if query_value:

            query_value.setText(
                str(queries)
            )

        if page_value:

            page_value.setText(
                str(pages)
            )

        if result_value:

            result_value.setText(
                str(results)
            )

    # ======================================================
    # FINISHED
    # ======================================================

    def finished(
        self,
        results
    ):

        self.running = False

        self.status.setText(
            "FINISHED"
        )

        self.eye.stop()

        self.stop_button.setEnabled(
            False
        )

        self.progress.setRange(
            0,
            1
        )

        self.progress.setValue(
            1
        )

        self.add_log(
            f"[DONE] {len(results)} results"
        )

    # ======================================================
    # WORKER FINISHED
    # ======================================================

    def worker_finished(self):

        worker = self.worker

        if worker:

            worker.deleteLater()

    # ======================================================
    # ERROR
    # ======================================================

    def error(
        self,
        message
    ):

        self.running = False

        self.status.setText(
            "FAILED"
        )

        self.eye.stop()

        self.stop_button.setEnabled(
            False
        )

        self.progress.setRange(
            0,
            1
        )

        self.progress.setValue(
            0
        )

        self.add_log(
            f"[FATAL] {message}"
        )

        QMessageBox.critical(
            self,
            "SCRAPER ERROR",
            message
        )

    # ======================================================
    # STOP
    # ======================================================

    def stop(self):

        if not self.worker:

            return

        if not self.running:

            return

        self.status.setText(
            "STOPPING"
        )

        self.stop_button.setEnabled(
            False
        )

        self.eye.stop()

        self.worker.stop_scraper()

    # ======================================================
    # BACK
    # ======================================================

    def back(self):

        if self.running:

            answer = QMessageBox.question(
                self,
                "SCRAPER RUNNING",
                "The scraper is still running.\n\n"
                "Stop it and return?"
            )

            if answer != QMessageBox.Yes:

                return

            self.stop()

            if self.worker:

                self.worker.wait(
                    2000
                )

        self.back_signal.emit()

    # ======================================================
    # CLOSE
    # ======================================================

    def closeEvent(
        self,
        event
    ):

        if self.running:

            self.stop()

            if self.worker:

                self.worker.wait(
                    2000
                )

        event.accept()


# ==========================================================
# DATA MANAGER WINDOW
# ==========================================================

class DataManagerWindow(QWidget):

    back_signal = pyqtSignal()

    def __init__(
        self,
        parent=None
    ):

        super().__init__(
            parent
        )

        self.database = DataManager()

        self.build_ui()

        self.load_databases()

    # ======================================================
    # UI
    # ======================================================

    def build_ui(self):

        layout = QVBoxLayout()

        layout.setContentsMargins(
            45,
            40,
            45,
            40
        )

        layout.setSpacing(
            20
        )

        self.setLayout(
            layout
        )

        # --------------------------------------------------
        # HEADER
        # --------------------------------------------------

        header = QHBoxLayout()

        title = QLabel(
            "DATA MANAGER"
        )

        title.setObjectName(
            "pageTitle"
        )

        header.addWidget(
            title
        )

        header.addStretch()

        back = QPushButton(
            "BACK"
        )

        back.setObjectName(
            "secondaryButton"
        )

        back.clicked.connect(
            self.back
        )

        header.addWidget(
            back
        )

        layout.addLayout(
            header
        )

        # --------------------------------------------------
        # DATABASE SELECTOR
        # --------------------------------------------------

        database_layout = QHBoxLayout()

        database_label = QLabel(
            "DATABASE"
        )

        database_label.setObjectName(
            "sectionTitle"
        )

        self.database_combo = QComboBox()

        self.database_combo.currentIndexChanged.connect(
            self.database_changed
        )

        database_layout.addWidget(
            database_label
        )

        database_layout.addWidget(
            self.database_combo,
            1
        )

        layout.addLayout(
            database_layout
        )

        # --------------------------------------------------
        # DATABASE INFO
        # --------------------------------------------------

        self.database_info = QLabel(
            "NO DATABASE"
        )

        self.database_info.setObjectName(
            "description"
        )

        layout.addWidget(
            self.database_info
        )

        # --------------------------------------------------
        # STATISTICS
        # --------------------------------------------------

        stats = QHBoxLayout()

        self.total = self.stat(
            "RECORDS",
            "0"
        )

        self.tables = self.stat(
            "TABLES",
            "0"
        )

        self.current_table_stat = self.stat(
            "CURRENT TABLE",
            "-"
        )

        stats.addWidget(
            self.total
        )

        stats.addWidget(
            self.tables
        )

        stats.addWidget(
            self.current_table_stat
        )

        layout.addLayout(
            stats
        )

        # --------------------------------------------------
        # TABLE SELECTOR
        # --------------------------------------------------

        table_layout = QHBoxLayout()

        table_label = QLabel(
            "TABLE"
        )

        table_label.setObjectName(
            "sectionTitle"
        )

        self.table_combo = QComboBox()

        self.table_combo.currentIndexChanged.connect(
            self.table_changed
        )

        table_layout.addWidget(
            table_label
        )

        table_layout.addWidget(
            self.table_combo,
            1
        )

        layout.addLayout(
            table_layout
        )

        # --------------------------------------------------
        # SEARCH
        # --------------------------------------------------

        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()

        self.search_input.setPlaceholderText(
            "Search in current table..."
        )

        self.search_input.returnPressed.connect(
            self.search
        )

        search_button = QPushButton(
            "SEARCH"
        )

        search_button.setObjectName(
            "primaryButton"
        )

        search_button.clicked.connect(
            self.search
        )

        refresh_button = QPushButton(
            "REFRESH"
        )

        refresh_button.setObjectName(
            "secondaryButton"
        )

        refresh_button.clicked.connect(
            self.refresh_table
        )

        search_layout.addWidget(
            self.search_input
        )

        search_layout.addWidget(
            search_button
        )

        search_layout.addWidget(
            refresh_button
        )

        layout.addLayout(
            search_layout
        )

        # --------------------------------------------------
        # TABLE
        # --------------------------------------------------

        self.table = QTableWidget()

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

        self.table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        self.table.setAlternatingRowColors(
            True
        )

        self.table.verticalHeader().setVisible(
            False
        )

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Interactive
        )

        layout.addWidget(
            self.table
        )

    # ======================================================
    # STAT
    # ======================================================

    def stat(
        self,
        title,
        value
    ):

        frame = QFrame()

        frame.setObjectName(
            "statCard"
        )

        layout = QVBoxLayout()

        layout.setContentsMargins(
            18,
            15,
            18,
            15
        )

        frame.setLayout(
            layout
        )

        title_label = QLabel(
            title
        )

        title_label.setObjectName(
            "statTitle"
        )

        value_label = QLabel(
            value
        )

        value_label.setObjectName(
            "statValue"
        )

        layout.addWidget(
            title_label
        )

        layout.addWidget(
            value_label
        )

        return frame

    # ======================================================
    # LOAD DATABASES
    # ======================================================

    def load_databases(self):

        self.database_combo.blockSignals(
            True
        )

        self.database_combo.clear()

        databases = self.database.list_databases()

        for database in databases:

            self.database_combo.addItem(
                database["name"],
                database["path"]
            )

        self.database_combo.blockSignals(
            False
        )

        if databases:

            self.database_combo.setCurrentIndex(
                0
            )

            self.database_changed(
                0
            )

        else:

            self.database_info.setText(
                "NO SQLITE DATABASES FOUND IN DATA/"
            )

    # ======================================================
    # DATABASE CHANGED
    # ======================================================

    def database_changed(
        self,
        index
    ):

        if index < 0:

            return

        path = self.database_combo.itemData(
            index
        )

        if not path:

            return

        try:

            self.database.open_database(
                path
            )

            statistics = (
                self.database.database_statistics()
            )

            self.database_info.setText(
                f"DATABASE: "
                f"{statistics['database']}    •    "
                f"TABLES: "
                f"{statistics['tables']}    •    "
                f"RECORDS: "
                f"{statistics['records']}"
            )

            self.set_stat(
                self.total,
                statistics["records"]
            )

            self.set_stat(
                self.tables,
                statistics["tables"]
            )

            self.load_tables()

        except Exception as error:

            QMessageBox.critical(
                self,
                "DATABASE ERROR",
                str(error)
            )

    # ======================================================
    # LOAD TABLES
    # ======================================================

    def load_tables(self):

        self.table_combo.blockSignals(
            True
        )

        self.table_combo.clear()

        tables = self.database.list_tables()

        for table in tables:

            self.table_combo.addItem(
                table
            )

        self.table_combo.blockSignals(
            False
        )

        if tables:

            self.table_combo.setCurrentIndex(
                0
            )

            self.table_changed(
                0
            )

        else:

            self.clear_table()

    # ======================================================
    # TABLE CHANGED
    # ======================================================

    def table_changed(
        self,
        index
    ):

        if index < 0:

            return

        table = self.table_combo.itemText(
            index
        )

        if not table:

            return

        try:

            self.database.current_table = table

            count = self.database.count(
                table
            )

            self.set_stat(
                self.total,
                count
            )

            self.set_stat(
                self.current_table_stat,
                table
            )

            self.load_rows()

        except Exception as error:

            QMessageBox.critical(
                self,
                "TABLE ERROR",
                str(error)
            )

    # ======================================================
    # LOAD ROWS
    # ======================================================

    def load_rows(
        self,
        rows=None
    ):

        if not self.database.current_table:

            self.clear_table()

            return

        try:

            if rows is None:

                rows = self.database.fetch_rows(
                    self.database.current_table,
                    limit=1000
                )

            if not rows:

                self.table.clear()

                self.table.setRowCount(
                    0
                )

                self.table.setColumnCount(
                    0
                )

                return

            columns = list(
                rows[0].keys()
            )

            self.table.clear()

            self.table.setColumnCount(
                len(columns)
            )

            self.table.setHorizontalHeaderLabels(
                columns
            )

            self.table.setRowCount(
                len(rows)
            )

            for row_index, row in enumerate(rows):

                for column_index, column in enumerate(columns):

                    value = row.get(
                        column,
                        ""
                    )

                    item = QTableWidgetItem(
                        str(
                            value
                            if value is not None
                            else ""
                        )
                    )

                    self.table.setItem(
                        row_index,
                        column_index,
                        item
                    )

            self.table.resizeColumnsToContents()

        except Exception as error:

            QMessageBox.critical(
                self,
                "TABLE ERROR",
                str(error)
            )

    # ======================================================
    # SEARCH
    # ======================================================

    def search(self):

        if not self.database.current_table:

            return

        text = (
            self.search_input
            .text()
            .strip()
        )

        try:

            rows = self.database.search_table(
                self.database.current_table,
                text,
                limit=1000
            )

            self.load_rows(
                rows
            )

        except Exception as error:

            QMessageBox.critical(
                self,
                "SEARCH ERROR",
                str(error)
            )

    # ======================================================
    # REFRESH
    # ======================================================

    def refresh_table(self):

        if self.database.current_database:

            self.database_changed(
                self.database_combo.currentIndex()
            )

    # ======================================================
    # CLEAR
    # ======================================================

    def clear_table(self):

        self.table.clear()

        self.table.setRowCount(
            0
        )

        self.table.setColumnCount(
            0
        )

    # ======================================================
    # SET STAT
    # ======================================================

    @staticmethod
    def set_stat(
        frame,
        value
    ):

        label = frame.findChild(
            QLabel,
            "statValue"
        )

        if label:

            label.setText(
                str(value)
            )

    # ======================================================
    # BACK
    # ======================================================

    def back(self):

        self.back_signal.emit()

    # ======================================================
    # CLOSE
    # ======================================================

    def closeEvent(
        self,
        event
    ):

        self.database.close()

        event.accept()


# ==========================================================
# MAIN WINDOW
# ==========================================================

class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.current_page = None

        self.build_window()

        self.show_home()

    # ======================================================
    # WINDOW
    # ======================================================

    def build_window(self):

        self.setWindowTitle(
            "EYE SCRAPPER"
        )

        self.resize(
            1280,
            850
        )

        self.setMinimumSize(
            1000,
            700
        )

        self.setStyleSheet(
            self.styles()
        )

    # ======================================================
    # HOME
    # ======================================================

    def show_home(self):

        self.clear_page()

        root = QWidget()

        self.setCentralWidget(
            root
        )

        layout = QVBoxLayout()

        layout.setContentsMargins(
            80,
            60,
            80,
            55
        )

        layout.setSpacing(
            28
        )

        root.setLayout(
            layout
        )

        # --------------------------------------------------
        # TOP
        # --------------------------------------------------

        top = QHBoxLayout()

        brand = QLabel(
            "EYE"
        )

        brand.setObjectName(
            "brand"
        )

        top.addWidget(
            brand
        )

        top.addStretch()

        version = QLabel(
            "SCRAPPER / 01"
        )

        version.setObjectName(
            "version"
        )

        top.addWidget(
            version
        )

        layout.addLayout(
            top
        )

        # --------------------------------------------------
        # HERO
        # --------------------------------------------------

        layout.addStretch(
            1
        )

        eye = QLabel(
            "◉"
        )

        eye.setAlignment(
            Qt.AlignCenter
        )

        eye.setObjectName(
            "heroEye"
        )

        layout.addWidget(
            eye
        )

        title = QLabel(
            "EYE SCRAPPER"
        )

        title.setAlignment(
            Qt.AlignCenter
        )

        title.setObjectName(
            "heroTitle"
        )

        layout.addWidget(
            title
        )

        subtitle = QLabel(
            "SCHOOL DATA DISCOVERY SYSTEM"
        )

        subtitle.setAlignment(
            Qt.AlignCenter
        )

        subtitle.setObjectName(
            "heroSubtitle"
        )

        layout.addWidget(
            subtitle
        )

        description = QLabel(
            "DISCOVER  •  EXTRACT  •  ORGANIZE"
        )

        description.setAlignment(
            Qt.AlignCenter
        )

        description.setObjectName(
            "heroDescription"
        )

        layout.addWidget(
            description
        )

        # --------------------------------------------------
        # BUTTONS
        # --------------------------------------------------

        buttons = QHBoxLayout()

        buttons.setSpacing(
            22
        )

        scraping = QPushButton(
            "START SCRAPING"
        )

        scraping.setObjectName(
            "heroButton"
        )

        scraping.clicked.connect(
            self.start_scraping
        )

        manager = QPushButton(
            "DATA MANAGER"
        )

        manager.setObjectName(
            "heroButton"
        )

        manager.clicked.connect(
            self.open_data_manager
        )

        buttons.addWidget(
            scraping
        )

        buttons.addWidget(
            manager
        )

        layout.addLayout(
            buttons
        )

        # --------------------------------------------------
        # FOOTER
        # --------------------------------------------------

        layout.addStretch(
            2
        )

        footer = QLabel(
            "EYE SCRAPPER  •  DATA DISCOVERY ENGINE  •  v1.0"
        )

        footer.setAlignment(
            Qt.AlignCenter
        )

        footer.setObjectName(
            "footer"
        )

        layout.addWidget(
            footer
        )

    # ======================================================
    # START SCRAPING
    # ======================================================

    def start_scraping(self):

        dialog = ScraperConfigDialog(
            self
        )

        if dialog.exec_() != QDialog.Accepted:

            return

        config = dialog.get_config()

        try:

            config.validate()

        except Exception as error:

            QMessageBox.warning(
                self,
                "INVALID CONFIGURATION",
                str(error)
            )

            return

        page = ScraperWindow(
            config,
            self
        )

        page.back_signal.connect(
            self.show_home
        )

        self.setCentralWidget(
            page
        )

        self.current_page = page

    # ======================================================
    # DATA MANAGER
    # ======================================================

    def open_data_manager(self):

        page = DataManagerWindow(
            self
        )

        page.back_signal.connect(
            self.show_home
        )

        self.setCentralWidget(
            page
        )

        self.current_page = page

    # ======================================================
    # CLEAR
    # ======================================================

    def clear_page(self):

        self.current_page = None

    # ======================================================
    # STYLES
    # ======================================================

    def styles(self):

        return f"""

        /* ================================================
           GLOBAL
           ================================================ */

        QWidget
        {{
            background: {BG};
            color: {WHITE};
            font-family: "DejaVu Sans";
            font-size: 14px;
        }}


        /* ================================================
           BRAND
           ================================================ */

        QLabel#brand
        {{
            color: {CRIMSON_BRIGHT};
            font-size: 30px;
            font-weight: 900;
            letter-spacing: 10px;
        }}


        QLabel#version
        {{
            color: {MUTED};
            font-size: 14px;
            font-weight: bold;
            letter-spacing: 4px;
        }}


        /* ================================================
           HERO
           ================================================ */

        QLabel#heroEye
        {{
            color: {CRIMSON_BRIGHT};
            font-size: 95px;
            font-weight: 900;
        }}


        QLabel#heroTitle
        {{
            color: {WHITE};
            font-size: 50px;
            font-weight: 900;
            letter-spacing: 9px;
        }}


        QLabel#heroSubtitle
        {{
            color: {SECONDARY};
            font-size: 16px;
            font-weight: bold;
            letter-spacing: 5px;
        }}


        QLabel#heroDescription
        {{
            color: {MUTED};
            font-size: 14px;
            letter-spacing: 5px;
        }}


        QLabel#footer
        {{
            color: {SECONDARY};
            font-size: 12px;
            letter-spacing: 3px;
        }}


        /* ================================================
           HERO BUTTON
           ================================================ */

        QPushButton#heroButton
        {{
            background: transparent;
            color: {WHITE};
            border: 2px solid {CRIMSON};
            min-height: 95px;
            font-size: 18px;
            font-weight: bold;
            letter-spacing: 3px;
            padding: 0 45px;
        }}


        QPushButton#heroButton:hover
        {{
            background: {CRIMSON};
            border: 2px solid {CRIMSON_BRIGHT};
        }}


        QPushButton#heroButton:pressed
        {{
            background: {CRIMSON_BRIGHT};
        }}


        /* ================================================
           PAGE TITLE
           ================================================ */

        QLabel#pageTitle
        {{
            color: {WHITE};
            font-size: 34px;
            font-weight: 900;
            letter-spacing: 5px;
        }}


        QLabel#status
        {{
            color: {CRIMSON_BRIGHT};
            font-size: 16px;
            font-weight: bold;
            letter-spacing: 4px;
        }}


        QLabel#description
        {{
            color: {MUTED};
            font-size: 15px;
        }}


        QLabel#sectionTitle
        {{
            color: {CRIMSON_BRIGHT};
            font-size: 15px;
            font-weight: bold;
            letter-spacing: 3px;
        }}


        /* ================================================
           STAT CARDS
           ================================================ */

        QFrame#statCard
        {{
            background: {PANEL};
            border-left: 4px solid {CRIMSON};
        }}


        QLabel#statTitle
        {{
            color: {MUTED};
            font-size: 13px;
            font-weight: bold;
            letter-spacing: 2px;
        }}


        QLabel#statValue
        {{
            color: {WHITE};
            font-size: 30px;
            font-weight: 900;
        }}


        /* ================================================
           PROGRESS
           ================================================ */

        QProgressBar
        {{
            background: {PANEL};
            border: none;
            height: 9px;
            text-align: center;
        }}


        QProgressBar::chunk
        {{
            background: {CRIMSON_BRIGHT};
        }}


        /* ================================================
           LOG
           ================================================ */

        QTextEdit
        {{
            background: {BLACK};
            color: {CRIMSON_BRIGHT};
            border: 1px solid {SECONDARY};
            padding: 15px;
            font-family: "DejaVu Sans Mono";
            font-size: 14px;
        }}


        /* ================================================
           INPUT
           ================================================ */

        QLineEdit,
        QComboBox
        {{
            background: {PANEL};
            color: {WHITE};
            border: 1px solid {SECONDARY};
            padding: 12px;
            min-height: 28px;
            font-size: 15px;
        }}


        QLineEdit:focus,
        QComboBox:focus
        {{
            border: 2px solid {CRIMSON_BRIGHT};
        }}


        /* ================================================
           BUTTONS
           ================================================ */

        QPushButton#primaryButton
        {{
            background: {CRIMSON};
            color: {WHITE};
            border: none;
            padding: 14px 25px;
            font-size: 14px;
            font-weight: bold;
            letter-spacing: 2px;
        }}


        QPushButton#primaryButton:hover
        {{
            background: {CRIMSON_BRIGHT};
        }}


        QPushButton#secondaryButton
        {{
            background: transparent;
            color: {MUTED};
            border: 1px solid {SECONDARY};
            padding: 14px 25px;
            font-size: 14px;
            font-weight: bold;
            letter-spacing: 2px;
        }}


        QPushButton#secondaryButton:hover
        {{
            color: {WHITE};
            border: 1px solid {WHITE};
        }}


        QPushButton#dangerButton
        {{
            background: {CRIMSON};
            color: {WHITE};
            border: none;
            padding: 14px 30px;
            font-size: 14px;
            font-weight: bold;
            letter-spacing: 2px;
        }}


        QPushButton#dangerButton:hover
        {{
            background: {CRIMSON_BRIGHT};
        }}


        /* ================================================
           DIALOG
           ================================================ */

        QDialog
        {{
            background: {BG};
        }}


        QLabel#dialogTitle
        {{
            color: {WHITE};
            font-size: 32px;
            font-weight: 900;
            letter-spacing: 4px;
        }}


        QLabel#dialogSubtitle
        {{
            color: {MUTED};
            font-size: 14px;
        }}


        QFormLayout QLabel
        {{
            color: {MUTED};
            font-size: 14px;
            font-weight: bold;
        }}


        /* ================================================
           TABLE
           ================================================ */

        QTableWidget
        {{
            background: {BLACK};
            color: {WHITE};
            border: 1px solid {SECONDARY};
            gridline-color: {SECONDARY};
            selection-background-color: {CRIMSON};
            selection-color: {WHITE};
            font-size: 14px;
            alternate-background-color: {PANEL};
        }}


        QTableWidget::item
        {{
            padding: 8px;
        }}


        QHeaderView::section
        {{
            background: {PANEL_LIGHT};
            color: {WHITE};
            border: none;
            border-bottom: 2px solid {CRIMSON};
            padding: 13px;
            font-size: 14px;
            font-weight: bold;
        }}


        /* ================================================
           SCROLLBAR
           ================================================ */

        QScrollBar:vertical
        {{
            background: {BG};
            width: 10px;
        }}


        QScrollBar::handle:vertical
        {{
            background: {SECONDARY};
            min-height: 35px;
        }}


        QScrollBar::handle:vertical:hover
        {{
            background: {CRIMSON};
        }}

        """


# ==========================================================
# APPLICATION ENTRY
# ==========================================================

def start_gui():

    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        "EYE SCRAPPER"
    )

    app.setStyle(
        "Fusion"
    )

    window = MainWindow()

    window.show()

    sys.exit(
        app.exec_()
    )


# ==========================================================
# DIRECT RUN
# ==========================================================

if __name__ == "__main__":

    start_gui()