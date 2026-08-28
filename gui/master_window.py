from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QPushButton,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from master.models import ScraperStatus
from master.process_manager import ProcessManager

from .controller import GUIController
from .data_manager_window import DataManagerWindow


# ============================================================
# EYE MASTER // HACKER PALETTE
# ============================================================

BG = "#120B18"

SURFACE = "#1B1023"
SURFACE_2 = "#23142D"
SURFACE_3 = "#2C1936"

BORDER = "#612E37"
BORDER_SOFT = "#432632"

TEXT = "#FFF7E6"
TEXT_SECONDARY = "#D8C7C0"
TEXT_MUTED = "#9C858D"

AMBER = "#FED172"
ORANGE = "#F3742B"
DEEP_ORANGE = "#B83A14"

BURGUNDY = "#612E37"
PURPLE = "#231650"

GREEN = "#72D6A3"
BLUE = "#7EB6E6"
RED = "#E56B5D"


# ============================================================
# DEFAULTS
# ============================================================

DEFAULT_PROVIDERS = (
    "google",
    "duckduckgo",
    "balad",
    "osm",
)

DEFAULT_KEYWORD_FILE = (
    "categories/business_keywords.txt"
)

DEFAULT_DATABASE_DIR = (
    Path("runtime") / "database"
)

DEFAULT_REFRESH_INTERVAL = 1000

KEYWORD_PREVIEW_LIMIT = 100


# ============================================================
# STATUS COLORS
# ============================================================

STATUS_COLORS = {
    ScraperStatus.CREATED: TEXT_MUTED,
    ScraperStatus.STARTING: AMBER,
    ScraperStatus.RUNNING: GREEN,
    ScraperStatus.STOPPING: AMBER,
    ScraperStatus.STOPPED: TEXT_MUTED,
    ScraperStatus.FINISHED: BLUE,
    ScraperStatus.CRASHED: RED,
    ScraperStatus.KILLED: RED,
}


# ============================================================
# NEW SCRAPER DIALOG
# ============================================================

class NewScraperDialog(QDialog):
    """
    EYE Master scraper creation dialog.

    Responsibilities:
        - collect scraper configuration
        - load and select keywords
        - select exactly one provider
        - validate configuration
        - generate the runtime database path

    Database:
        runtime/database/<scraper_name>.db

    Keyword execution:
        The complete keyword file is passed to the backend.
        The selected keyword is kept as the initial active keyword.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:

        super().__init__(parent)

        self.setWindowTitle(
            "EYE // NEW SCRAPER"
        )

        self.setMinimumSize(
            820,
            800,
        )

        self.resize(
            900,
            900,
        )

        self._build_ui()
        self._apply_style()
        self._connect_signals()
        self._load_keyword_preview()

    # ========================================================
    # BUILD UI
    # ========================================================

    def _build_ui(self) -> None:

        outer = QVBoxLayout(self)

        outer.setContentsMargins(
            18,
            18,
            18,
            18,
        )

        outer.setSpacing(
            12,
        )

        # ====================================================
        # HEADER
        # ====================================================

        header = QFrame()
        header.setObjectName("DialogHeader")

        header_layout = QVBoxLayout(header)

        header_layout.setContentsMargins(
            22,
            18,
            22,
            18,
        )

        header_layout.setSpacing(5)

        title = QLabel(
            "EYE // NEW SCRAPER"
        )

        title.setObjectName(
            "DialogTitle"
        )

        subtitle = QLabel(
            "IDENTITY  →  KEYWORDS  →  LOCATION  →  "
            "EXECUTION  →  ADVANCED  →  PROVIDER"
        )

        subtitle.setObjectName(
            "DialogSubtitle"
        )

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)

        outer.addWidget(header)

        # ====================================================
        # SCROLL AREA
        # ====================================================

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)

        scroll.setFrameShape(
            QFrame.NoFrame
        )

        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        content = QWidget()

        content_layout = QVBoxLayout(content)

        content_layout.setContentsMargins(
            4,
            4,
            10,
            6,
        )

        content_layout.setSpacing(
            14,
        )

        scroll.setWidget(content)

        outer.addWidget(
            scroll,
            1,
        )

        # ====================================================
        # 01 // IDENTITY
        # ====================================================

        identity = self._create_section(
            "01 // SCRAPER IDENTITY",
            "SCRAPER PROCESS IDENTIFICATION",
        )

        identity_form = QFormLayout()

        identity_form.setHorizontalSpacing(22)
        identity_form.setVerticalSpacing(14)

        self.name_edit = QLineEdit()

        self.name_edit.setPlaceholderText(
            "e.g. tehran_businesses"
        )

        identity_form.addRow(
            "SCRAPER NAME",
            self.name_edit,
        )

        self.target_edit = QLineEdit()

        self.target_edit.setPlaceholderText(
            "Optional target identifier"
        )

        identity_form.addRow(
            "TARGET",
            self.target_edit,
        )

        identity.layout().addLayout(
            identity_form
        )

        content_layout.addWidget(identity)

        # ====================================================
        # 02 // KEYWORD MATRIX
        # ====================================================

        keyword_section = self._create_section(
            "02 // KEYWORD MATRIX",
            "SELECT A TEXT FILE CONTAINING ONE KEYWORD PER LINE",
        )

        keyword_layout = QVBoxLayout()

        keyword_layout.setSpacing(11)

        keyword_row = QHBoxLayout()

        self.keyword_file_edit = QLineEdit()

        self.keyword_file_edit.setText(
            DEFAULT_KEYWORD_FILE
        )

        self.keyword_file_edit.setReadOnly(True)

        self.keyword_file_edit.setPlaceholderText(
            "categories/business_keywords.txt"
        )

        browse_button = QPushButton(
            "BROWSE"
        )

        browse_button.setObjectName(
            "SecondaryButton"
        )

        keyword_row.addWidget(
            self.keyword_file_edit,
            1,
        )

        keyword_row.addWidget(
            browse_button
        )

        keyword_layout.addLayout(
            keyword_row
        )

        self.keyword_info = QLabel(
            "NO KEYWORDS LOADED"
        )

        self.keyword_info.setObjectName(
            "KeywordInfo"
        )

        keyword_layout.addWidget(
            self.keyword_info
        )

        active_keyword_row = QHBoxLayout()

        active_keyword_label = QLabel(
            "ACTIVE KEYWORD"
        )

        active_keyword_label.setObjectName(
            "ActiveKeywordLabel"
        )

        self.active_keyword_edit = QLineEdit()

        self.active_keyword_edit.setPlaceholderText(
            "Select a keyword below"
        )

        self.active_keyword_edit.setReadOnly(True)

        active_keyword_row.addWidget(
            active_keyword_label
        )

        active_keyword_row.addWidget(
            self.active_keyword_edit,
            1,
        )

        keyword_layout.addLayout(
            active_keyword_row
        )

        self.keyword_preview = QListWidget()

        self.keyword_preview.setObjectName(
            "KeywordPreview"
        )

        self.keyword_preview.setSelectionMode(
            QListWidget.SingleSelection
        )

        self.keyword_preview.setMinimumHeight(
            190
        )

        self.keyword_preview.setMaximumHeight(
            300
        )

        keyword_layout.addWidget(
            self.keyword_preview
        )

        keyword_hint = QLabel(
            "CLICK ANY KEYWORD TO MAKE IT THE ACTIVE KEYWORD"
        )

        keyword_hint.setObjectName(
            "KeywordHint"
        )

        keyword_layout.addWidget(
            keyword_hint
        )

        keyword_section.layout().addLayout(
            keyword_layout
        )

        content_layout.addWidget(
            keyword_section
        )

        # ====================================================
        # 03 // LOCATION
        # ====================================================

        location_section = self._create_section(
            "03 // TARGET LOCATION",
            "SEARCH LOCATION PARAMETERS",
        )

        location_form = QFormLayout()

        location_form.setHorizontalSpacing(22)
        location_form.setVerticalSpacing(14)

        self.province_edit = QLineEdit()

        self.province_edit.setPlaceholderText(
            "e.g. آذربایجان شرقی"
        )

        location_form.addRow(
            "PROVINCE",
            self.province_edit,
        )

        self.city_edit = QLineEdit()

        self.city_edit.setPlaceholderText(
            "e.g. تبریز"
        )

        location_form.addRow(
            "CITY",
            self.city_edit,
        )

        location_section.layout().addLayout(
            location_form
        )

        content_layout.addWidget(
            location_section
        )

        # ====================================================
        # 04 // EXECUTION
        # ====================================================

        execution_section = self._create_section(
            "04 // EXECUTION",
            "QUERY AND REQUEST PARAMETERS",
        )

        execution_form = QFormLayout()

        execution_form.setHorizontalSpacing(22)
        execution_form.setVerticalSpacing(13)

        self.max_queries_spin = self._create_integer_input(
            1,
            1_000_000,
            20,
        )

        execution_form.addRow(
            "MAX QUERIES",
            self.max_queries_spin,
        )

        self.pages_per_query_spin = self._create_integer_input(
            1,
            100_000,
            1,
        )

        execution_form.addRow(
            "PAGES / QUERY",
            self.pages_per_query_spin,
        )

        self.results_per_page_spin = self._create_integer_input(
            1,
            100_000,
            100,
        )

        execution_form.addRow(
            "RESULTS / PAGE",
            self.results_per_page_spin,
        )

        self.delay_spin = self._create_integer_input(
            0,
            86_400,
            0,
        )

        execution_form.addRow(
            "DELAY / REQUEST (SEC)",
            self.delay_spin,
        )

        self.timeout_spin = self._create_integer_input(
            1,
            86_400,
            30,
        )

        execution_form.addRow(
            "REQUEST TIMEOUT (SEC)",
            self.timeout_spin,
        )

        execution_section.layout().addLayout(
            execution_form
        )

        content_layout.addWidget(
            execution_section
        )

        # ====================================================
        # 05 // ADVANCED
        # ====================================================

        advanced_section = self._create_section(
            "05 // ADVANCED",
            "OPTIONAL BACKEND KEY=VALUE CONFIGURATION",
        )

        self.config_edit = QTextEdit()

        self.config_edit.setPlaceholderText(
            "Optional key=value configuration\n\n"
            "example:\n"
            "deduplicate=true\n"
            "retry_count=3"
        )

        self.config_edit.setMinimumHeight(
            120
        )

        self.config_edit.setMaximumHeight(
            180
        )

        advanced_section.layout().addWidget(
            self.config_edit
        )

        content_layout.addWidget(
            advanced_section
        )

        # ====================================================
        # 06 // PROVIDER
        #
        # PROVIDER MUST ALWAYS BE THE FINAL MAIN SECTION.
        # ====================================================

        provider_section = self._create_section(
            "06 // SEARCH PROVIDER",
            "ONE PROVIDER PER CHILD SCRAPER",
        )

        provider_layout = QVBoxLayout()

        provider_layout.setSpacing(9)

        self.providers_list = QListWidget()

        self.providers_list.setObjectName(
            "ProviderList"
        )

        self.providers_list.setSelectionMode(
            QListWidget.SingleSelection
        )

        self.providers_list.setMinimumHeight(
            210
        )

        self.providers_list.setMaximumHeight(
            300
        )

        self._populate_providers()

        provider_layout.addWidget(
            self.providers_list
        )

        self.provider_hint = QLabel(
            "SELECT EXACTLY ONE PROVIDER"
        )

        self.provider_hint.setObjectName(
            "ProviderHint"
        )

        provider_layout.addWidget(
            self.provider_hint
        )

        provider_section.layout().addLayout(
            provider_layout
        )

        content_layout.addWidget(
            provider_section
        )

        content_layout.addStretch(1)

        # ====================================================
        # DIALOG BUTTONS
        # ====================================================

        buttons = QDialogButtonBox(
            QDialogButtonBox.Cancel
            | QDialogButtonBox.Ok
        )

        self.create_button = buttons.button(
            QDialogButtonBox.Ok
        )

        self.create_button.setText(
            "CREATE // ARM SCRAPER"
        )

        self.create_button.setObjectName(
            "PrimaryButton"
        )

        outer.addWidget(buttons)

        self._buttons = buttons
        self._browse_button = browse_button

    # ========================================================
    # SIGNALS
    # ========================================================

    def _connect_signals(self) -> None:

        self._browse_button.clicked.connect(
            self._browse_keyword_file
        )

        self.keyword_preview.currentItemChanged.connect(
            self._on_keyword_selected
        )

        self.keyword_preview.itemClicked.connect(
            self._on_keyword_clicked
        )

        self._buttons.accepted.connect(
            self._validate
        )

        self._buttons.rejected.connect(
            self.reject
        )

    # ========================================================
    # SECTION FACTORY
    # ========================================================

    @staticmethod
    def _create_section(
        title: str,
        subtitle: str,
    ) -> QFrame:

        frame = QFrame()

        frame.setObjectName(
            "ConfigSection"
        )

        layout = QVBoxLayout(frame)

        layout.setContentsMargins(
            18,
            16,
            18,
            18,
        )

        layout.setSpacing(10)

        title_label = QLabel(title)

        title_label.setObjectName(
            "SectionTitle"
        )

        subtitle_label = QLabel(subtitle)

        subtitle_label.setObjectName(
            "SectionSubtitle"
        )

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        return frame

    # ========================================================
    # INTEGER INPUT
    # ========================================================

    @staticmethod
    def _create_integer_input(
        minimum: int,
        maximum: int,
        default: int,
    ) -> QSpinBox:

        widget = QSpinBox()

        widget.setRange(
            minimum,
            maximum,
        )

        widget.setValue(
            default
        )

        widget.setButtonSymbols(
            QSpinBox.PlusMinus
        )

        widget.setMinimumHeight(
            46
        )

        return widget

    # ========================================================
    # KEYWORD FILE
    # ========================================================

    def _browse_keyword_file(self) -> None:

        start_dir = Path(
            DEFAULT_KEYWORD_FILE
        ).parent

        if not start_dir.exists():
            start_dir = Path.cwd()

        path, _ = QFileDialog.getOpenFileName(
            self,
            "SELECT KEYWORD FILE",
            str(start_dir),
            "Text Files (*.txt);;All Files (*)",
        )

        if not path:
            return

        self.keyword_file_edit.setText(
            path
        )

        self._load_keyword_preview()

    # ========================================================
    # READ KEYWORDS
    # ========================================================

    def _read_keywords(self) -> list[str]:

        raw_path = (
            self.keyword_file_edit
            .text()
            .strip()
        )

        if not raw_path:
            return []

        path = Path(
            raw_path
        ).expanduser()

        if not path.is_file():
            return []

        keywords: list[str] = []

        try:

            with path.open(
                "r",
                encoding="utf-8-sig",
            ) as file:

                for line in file:

                    keyword = line.strip()

                    if not keyword:
                        continue

                    if keyword.startswith("#"):
                        continue

                    keywords.append(
                        keyword
                    )

        except (
            OSError,
            UnicodeError,
        ):

            return []

        return keywords

    # ========================================================
    # KEYWORD PREVIEW
    # ========================================================

    def _load_keyword_preview(self) -> None:

        self.keyword_preview.blockSignals(
            True
        )

        try:

            self.keyword_preview.clear()

            keywords = self._read_keywords()

            if not keywords:

                self.active_keyword_edit.clear()

                self.keyword_info.setText(
                    "⚠ NO VALID KEYWORDS FOUND"
                )

                self.keyword_info.setStyleSheet(
                    f"color: {RED};"
                )

                return

            self.keyword_info.setText(
                f"● {len(keywords)} KEYWORDS LOADED"
            )

            self.keyword_info.setStyleSheet(
                f"color: {GREEN};"
            )

            for index, keyword in enumerate(
                keywords[:KEYWORD_PREVIEW_LIMIT],
                start=1,
            ):

                item = QListWidgetItem(
                    f"{index:03d}  //  {keyword}"
                )

                item.setData(
                    Qt.UserRole,
                    keyword,
                )

                self.keyword_preview.addItem(
                    item
                )

            if len(keywords) > KEYWORD_PREVIEW_LIMIT:

                remaining = (
                    len(keywords)
                    - KEYWORD_PREVIEW_LIMIT
                )

                extra = QListWidgetItem(
                    f"... {remaining} MORE KEYWORDS"
                )

                extra.setFlags(
                    Qt.NoItemFlags
                )

                self.keyword_preview.addItem(
                    extra
                )

            if self.keyword_preview.count():

                self.keyword_preview.setCurrentRow(
                    0
                )

        finally:

            self.keyword_preview.blockSignals(
                False
            )

        self._sync_active_keyword()

    # ========================================================
    # KEYWORD SELECTION
    # ========================================================

    def _on_keyword_selected(
        self,
        current: Optional[QListWidgetItem],
        previous: Optional[QListWidgetItem],
    ) -> None:

        del previous

        self._set_active_keyword(
            current
        )

    # ========================================================
    # KEYWORD CLICK
    # ========================================================

    def _on_keyword_clicked(
        self,
        item: Optional[QListWidgetItem],
    ) -> None:

        self._set_active_keyword(
            item
        )

    # ========================================================
    # SET ACTIVE KEYWORD
    # ========================================================

    def _set_active_keyword(
        self,
        item: Optional[QListWidgetItem],
    ) -> None:

        if item is None:
            return

        keyword = item.data(
            Qt.UserRole
        )

        if keyword is None:
            return

        keyword = str(
            keyword
        ).strip()

        if not keyword:
            return

        self.active_keyword_edit.setText(
            keyword
        )

        self.keyword_info.setText(
            f"● ACTIVE // {keyword}"
        )

        self.keyword_info.setStyleSheet(
            f"color: {AMBER};"
        )

    # ========================================================
    # SYNC ACTIVE KEYWORD
    # ========================================================

    def _sync_active_keyword(self) -> None:

        item = (
            self.keyword_preview.currentItem()
        )

        if item is None:
            return

        self._set_active_keyword(
            item
        )

    # ========================================================
    # DATABASE PATH
    # ========================================================

    @classmethod
    def _database_path(
        cls,
        scraper_name: str,
    ) -> str:

        safe_name = cls._safe_filename(
            scraper_name
        )

        if not safe_name:
            safe_name = "scraper"

        return str(
            DEFAULT_DATABASE_DIR
            / f"{safe_name}.db"
        )

    # ========================================================
    # SAFE FILE NAME
    # ========================================================

    @staticmethod
    def _safe_filename(
        value: str,
    ) -> str:

        value = value.strip()

        allowed = (
            "abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "0123456789"
            "_-"
        )

        result = "".join(
            char
            for char in value
            if char in allowed
        )

        return result.strip(
            "._-"
        )

    # ========================================================
    # PROVIDERS
    # ========================================================

    def _populate_providers(self) -> None:

        providers: list[str] = []

        try:

            from providers.manager import ProviderManager

            manager = ProviderManager()

            candidates: Any = []

            # ------------------------------------------------
            # Supported provider manager APIs.
            # ------------------------------------------------

            for method_name in (
                "list_providers",
                "available_providers",
            ):

                method = getattr(
                    manager,
                    method_name,
                    None,
                )

                if callable(method):

                    result = method()

                    if result:
                        candidates = result
                        break

            if not candidates:

                registry = getattr(
                    manager,
                    "registry",
                    None,
                )

                if isinstance(
                    registry,
                    dict,
                ):

                    candidates = registry.keys()

                elif registry is not None:

                    list_method = getattr(
                        registry,
                        "list",
                        None,
                    )

                    if callable(list_method):

                        result = list_method()

                        if result:
                            candidates = result

            if not candidates:

                candidates_attr = getattr(
                    manager,
                    "providers",
                    None,
                )

                if callable(
                    candidates_attr
                ):

                    candidates_attr = (
                        candidates_attr()
                    )

                if candidates_attr:
                    candidates = candidates_attr

            for provider in candidates:

                name = self._provider_name(
                    provider
                )

                if name:
                    providers.append(
                        name
                    )

        except Exception:
            providers = []

        if not providers:

            providers = list(
                DEFAULT_PROVIDERS
            )

        providers = sorted(
            {
                provider.strip().lower()
                for provider in providers
                if provider
            },
            key=str.lower,
        )

        self.providers_list.clear()

        for provider in providers:

            item = QListWidgetItem(
                f"◉  {provider}"
            )

            item.setData(
                Qt.UserRole,
                provider,
            )

            self.providers_list.addItem(
                item
            )

        if self.providers_list.count():

            self.providers_list.setCurrentRow(
                0
            )

    # ========================================================
    # PROVIDER NAME
    # ========================================================

    @staticmethod
    def _provider_name(
        provider: Any,
    ) -> str:

        if isinstance(
            provider,
            str,
        ):
            return provider.strip()

        if isinstance(
            provider,
            dict,
        ):

            value = provider.get(
                "name"
            )

            if value is None:
                value = provider.get(
                    "id"
                )

            return (
                str(value).strip()
                if value is not None
                else ""
            )

        value = getattr(
            provider,
            "name",
            None,
        )

        if value is not None:
            return str(
                value
            ).strip()

        return ""

    # ========================================================
    # SELECTED PROVIDER
    # ========================================================

    def _selected_provider(self) -> str:

        item = (
            self.providers_list.currentItem()
        )

        if item is None:
            return ""

        value = item.data(
            Qt.UserRole
        )

        if value is None:
            return ""

        return str(
            value
        ).strip().lower()

    # ========================================================
    # VALIDATION
    # ========================================================

    def _validate(self) -> None:

        name = (
            self.name_edit
            .text()
            .strip()
        )

        if not name:

            self._warning(
                "INVALID SCRAPER",
                "Scraper name cannot be empty.",
            )

            self.name_edit.setFocus()

            return

        safe_name = self._safe_filename(
            name
        )

        if not safe_name:

            self._warning(
                "INVALID SCRAPER",
                "Scraper name must contain at least one ASCII "
                "letter, number, '_' or '-'.",
            )

            self.name_edit.setFocus()

            return

        keyword_file = (
            self.keyword_file_edit
            .text()
            .strip()
        )

        if not keyword_file:

            self._warning(
                "INVALID KEYWORD FILE",
                "Select a keyword file.",
            )

            return

        keyword_path = Path(
            keyword_file
        ).expanduser()

        if not keyword_path.is_file():

            self._warning(
                "KEYWORD FILE NOT FOUND",
                "The selected keyword file does not exist.",
            )

            return

        keywords = self._read_keywords()

        if not keywords:

            self._warning(
                "EMPTY KEYWORD FILE",
                "The selected keyword file contains no valid keywords.",
            )

            return

        keyword = (
            self.active_keyword_edit
            .text()
            .strip()
        )

        if not keyword:

            self._warning(
                "SCRAPER KEYWORD REQUIRED",
                "Select at least one keyword.",
            )

            self.keyword_preview.setFocus()

            return

        if keyword not in keywords:

            self._warning(
                "INVALID ACTIVE KEYWORD",
                "The selected active keyword is not present "
                "in the keyword file.",
            )

            self._load_keyword_preview()

            return

        province = (
            self.province_edit
            .text()
            .strip()
        )

        city = (
            self.city_edit
            .text()
            .strip()
        )

        if not province:

            self._warning(
                "INVALID LOCATION",
                "Province cannot be empty.",
            )

            self.province_edit.setFocus()

            return

        if not city:

            self._warning(
                "INVALID LOCATION",
                "City cannot be empty.",
            )

            self.city_edit.setFocus()

            return

        provider = self._selected_provider()

        if not provider:

            self._warning(
                "INVALID PROVIDER",
                "Select a search provider.",
            )

            self.providers_list.setFocus()

            return

        self.accept()

    # ========================================================
    # WARNING
    # ========================================================

    def _warning(
        self,
        title: str,
        message: str,
    ) -> None:

        QMessageBox.warning(
            self,
            title,
            message,
        )

    # ========================================================
    # ADVANCED CONFIG
    # ========================================================

    @staticmethod
    def _parse_advanced_config(
        text: str,
    ) -> dict[str, str]:

        config: dict[str, str] = {}

        protected_keys = {
            "name",
            "target",
            "keyword",
            "keywords",
            "keyword_file",
            "keyword_mode",
            "keyword_execution",
            "process_all_keywords",
            "stop_on_keyword_error",
            "keyword_count",
            "province",
            "city",
            "location",
            "max_queries",
            "pages_per_query",
            "results_per_page",
            "delay",
            "timeout",
            "provider",
            "search_provider",
            "database",
        }

        for line in text.splitlines():

            line = line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split(
                "=",
                1,
            )

            key = key.strip()
            value = value.strip()

            if not key:
                continue

            if key.lower() in protected_keys:
                continue

            config[key] = value

        return config

    # ========================================================
    # DATA
    # ========================================================

    def data(self) -> dict[str, Any]:

        provider = self._selected_provider()

        keywords = self._read_keywords()

        keyword = (
            self.active_keyword_edit
            .text()
            .strip()
        )

        if not keyword and keywords:
            keyword = keywords[0]

        keyword_file = (
            self.keyword_file_edit
            .text()
            .strip()
        )

        province = (
            self.province_edit
            .text()
            .strip()
        )

        city = (
            self.city_edit
            .text()
            .strip()
        )

        name = (
            self.name_edit
            .text()
            .strip()
        )

        database_path = (
            self._database_path(
                name
            )
        )

        config: dict[str, Any] = {

            # ------------------------------------------------
            # ACTIVE KEYWORD
            # ------------------------------------------------

            "keyword": keyword,

            # ------------------------------------------------
            # COMPLETE KEYWORD SET
            # ------------------------------------------------

            "keywords": list(
                keywords
            ),

            "keyword_file": keyword_file,
            "keyword_mode": "file",
            "keyword_execution": "sequential",
            "process_all_keywords": True,
            "stop_on_keyword_error": False,
            "keyword_count": len(keywords),

            # ------------------------------------------------
            # LOCATION
            # ------------------------------------------------

            "province": province,
            "city": city,

            "location": {
                "province": province,
                "city": city,
            },

            # ------------------------------------------------
            # EXECUTION
            # ------------------------------------------------

            "max_queries": (
                self.max_queries_spin.value()
            ),

            "pages_per_query": (
                self.pages_per_query_spin.value()
            ),

            "results_per_page": (
                self.results_per_page_spin.value()
            ),

            "delay": (
                self.delay_spin.value()
            ),

            "timeout": (
                self.timeout_spin.value()
            ),

            # ------------------------------------------------
            # PROVIDER
            # ------------------------------------------------

            "provider": provider,

            "search_provider": (
                [provider]
                if provider
                else []
            ),

            # ------------------------------------------------
            # DATABASE
            # ------------------------------------------------

            "database": database_path,
        }

        # ----------------------------------------------------
        # OPTIONAL ADVANCED CONFIG
        # ----------------------------------------------------

        advanced = self._parse_advanced_config(
            self.config_edit.toPlainText()
        )

        config.update(
            advanced
        )

        # ----------------------------------------------------
        # FORCE CORE VALUES
        # ----------------------------------------------------

        config["keyword"] = keyword
        config["keywords"] = list(
            keywords
        )

        config["keyword_file"] = keyword_file
        config["keyword_mode"] = "file"
        config["keyword_execution"] = "sequential"
        config["process_all_keywords"] = True
        config["stop_on_keyword_error"] = False
        config["keyword_count"] = len(keywords)

        config["province"] = province
        config["city"] = city

        config["location"] = {
            "province": province,
            "city": city,
        }

        config["max_queries"] = (
            self.max_queries_spin.value()
        )

        config["pages_per_query"] = (
            self.pages_per_query_spin.value()
        )

        config["results_per_page"] = (
            self.results_per_page_spin.value()
        )

        config["delay"] = (
            self.delay_spin.value()
        )

        config["timeout"] = (
            self.timeout_spin.value()
        )

        config["provider"] = provider

        config["search_provider"] = (
            [provider]
            if provider
            else []
        )

        config["database"] = database_path

        return {
            "name": name,

            "providers": (
                [provider]
                if provider
                else []
            ),

            "target": (
                self.target_edit
                .text()
                .strip()
                or None
            ),

            "database": database_path,

            "scraper_dir": None,

            "config": config,
        }

    # ========================================================
    # STYLE
    # ========================================================

    def _apply_style(self) -> None:

        self.setStyleSheet(
            f"""
            QDialog {{
                background: {BG};
                color: {TEXT};
                font-family: "JetBrains Mono", monospace;
            }}

            QFrame#DialogHeader {{
                background: {SURFACE};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}

            QLabel {{
                color: {TEXT};
                background: transparent;
            }}

            QLabel#DialogTitle {{
                color: {AMBER};
                font-size: 27px;
                font-weight: 900;
            }}

            QLabel#DialogSubtitle {{
                color: {TEXT_MUTED};
                font-size: 11px;
                font-weight: 900;
            }}

            QFrame#ConfigSection {{
                background: {SURFACE};
                border: 1px solid {BORDER_SOFT};
                border-radius: 11px;
            }}

            QLabel#SectionTitle {{
                color: {AMBER};
                font-size: 14px;
                font-weight: 900;
            }}

            QLabel#SectionSubtitle {{
                color: {TEXT_MUTED};
                font-size: 11px;
                font-weight: 700;
            }}

            QFormLayout QLabel {{
                color: {TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 900;
            }}

            QLabel#ActiveKeywordLabel {{
                color: {AMBER};
                font-size: 12px;
                font-weight: 900;
            }}

            QLabel#KeywordInfo {{
                color: {GREEN};
                font-family: "JetBrains Mono";
                font-size: 12px;
                font-weight: 900;
            }}

            QLabel#KeywordHint {{
                color: {TEXT_MUTED};
                font-family: "JetBrains Mono";
                font-size: 10px;
                font-weight: 900;
            }}

            QLabel#ProviderHint {{
                color: {TEXT_MUTED};
                font-family: "JetBrains Mono";
                font-size: 10px;
                font-weight: 900;
            }}

            QLineEdit,
            QTextEdit,
            QSpinBox {{
                background: {SURFACE_2};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 10px 13px;
                font-family: "JetBrains Mono";
                font-size: 14px;
                font-weight: 600;
                selection-background-color: {PURPLE};
                selection-color: {TEXT};
            }}

            QLineEdit {{
                min-height: 44px;
            }}

            QLineEdit:focus,
            QTextEdit:focus,
            QSpinBox:focus {{
                border: 2px solid {ORANGE};
                background: {SURFACE_3};
            }}

            QLineEdit:read-only {{
                background: {SURFACE_3};
                color: {TEXT_SECONDARY};
            }}

            QTextEdit {{
                padding: 12px;
            }}

            QSpinBox {{
                min-height: 44px;
                padding-right: 38px;
            }}

            QSpinBox::up-button,
            QSpinBox::down-button {{
                background: {SURFACE_3};
                border: none;
                width: 28px;
            }}

            QSpinBox::up-button:hover,
            QSpinBox::down-button:hover {{
                background: {BURGUNDY};
            }}

            QListWidget {{
                background: {SURFACE_2};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 6px;
                outline: none;
            }}

            QListWidget::item {{
                color: {TEXT_SECONDARY};
                padding: 10px 12px;
                min-height: 24px;
                border-radius: 6px;
                font-family: "JetBrains Mono";
                font-size: 13px;
                font-weight: 700;
            }}

            QListWidget::item:hover {{
                background: {SURFACE_3};
                color: {TEXT};
            }}

            QListWidget::item:selected {{
                background: {PURPLE};
                color: {AMBER};
                border: 1px solid {ORANGE};
                border-left: 4px solid {ORANGE};
            }}

            QListWidget#KeywordPreview {{
                min-height: 190px;
            }}

            QListWidget#KeywordPreview::item {{
                padding: 9px 12px;
                font-family: "JetBrains Mono";
                font-size: 13px;
            }}

            QListWidget#ProviderList {{
                min-height: 210px;
            }}

            QListWidget#ProviderList::item {{
                padding: 13px 14px;
                min-height: 28px;
                font-size: 14px;
            }}

            QPushButton {{
                background: {SURFACE_2};
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 11px 17px;
                min-height: 40px;
                font-family: "JetBrains Mono";
                font-size: 12px;
                font-weight: 900;
            }}

            QPushButton:hover {{
                color: {AMBER};
                border-color: {ORANGE};
                background: {SURFACE_3};
            }}

            QPushButton:pressed {{
                background: {DEEP_ORANGE};
                color: {TEXT};
            }}

            QPushButton:disabled {{
                color: {TEXT_MUTED};
                background: {SURFACE};
                border-color: {BORDER_SOFT};
            }}

            QPushButton#PrimaryButton {{
                background: {AMBER};
                color: {BG};
                border-color: {AMBER};
                min-height: 44px;
            }}

            QPushButton#PrimaryButton:hover {{
                background: {ORANGE};
                border-color: {ORANGE};
                color: {TEXT};
            }}

            QPushButton#SecondaryButton {{
                min-width: 110px;
                min-height: 44px;
            }}

            QScrollArea {{
                background: transparent;
                border: none;
            }}

            QScrollBar:vertical {{
                background: {SURFACE};
                width: 11px;
                border-radius: 5px;
            }}

            QScrollBar::handle:vertical {{
                background: {BORDER};
                min-height: 40px;
                border-radius: 5px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: {ORANGE};
            }}

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            """
        )


# ============================================================
# MASTER WINDOW
# ============================================================

class MasterWindow(QWidget):
    """
    EYE Master process dashboard.

    Responsibilities:
        - display scraper processes
        - display process status
        - create scraper configurations
        - start / stop / restart / kill
        - remove scraper
        - display runtime information
        - display configuration
        - display master event log

    Scraping logic remains outside the GUI.
    """

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

        self.controller = GUIController(
            process_manager=manager
        )

        self.current_scraper: Optional[str] = None

        self._database_manager_window: Optional[DataManagerWindow] = None

        self._building_list = False
        self._last_refresh_error = ""

        self._build_ui()
        self._apply_style()

        self.refresh_timer = QTimer(self)

        self.refresh_timer.setInterval(
            DEFAULT_REFRESH_INTERVAL
        )

        self.refresh_timer.timeout.connect(
            self.refresh
        )

        self.refresh_timer.start()

        self.refresh()

    # ========================================================
    # BUILD
    # ========================================================

    def _build_ui(self) -> None:

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            14,
            14,
            14,
            12,
        )

        layout.setSpacing(14)

        # ====================================================
        # HEADER
        # ====================================================

        header = QHBoxLayout()

        title_box = QVBoxLayout()

        title_box.setSpacing(3)

        title = QLabel(
            "EYE // MASTER"
        )

        title.setObjectName(
            "MasterTitle"
        )

        subtitle = QLabel(
            "SCRAPER ORCHESTRATION // BUSINESS INTELLIGENCE"
        )

        subtitle.setObjectName(
            "MasterSubtitle"
        )

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header.addLayout(title_box)
        header.addStretch()

        self.connection_label = QLabel(
            "● MASTER ONLINE"
        )

        self.connection_label.setObjectName(
            "Connection"
        )

        header.addWidget(
            self.connection_label
        )

        layout.addLayout(header)

        # ====================================================
        # STATS
        # ====================================================

        stats = QHBoxLayout()

        stats.setSpacing(10)

        self.total_value = self._create_stat(
            stats,
            "TOTAL",
            TEXT,
        )

        self.running_value = self._create_stat(
            stats,
            "RUNNING",
            GREEN,
        )

        self.starting_value = self._create_stat(
            stats,
            "STARTING",
            AMBER,
        )

        self.failed_value = self._create_stat(
            stats,
            "FAILED",
            RED,
        )

        self.finished_value = self._create_stat(
            stats,
            "FINISHED",
            BLUE,
        )

        layout.addLayout(stats)

        # ====================================================
        # MAIN SPLITTER
        # ====================================================

        splitter = QSplitter(
            Qt.Horizontal
        )

        splitter.setChildrenCollapsible(
            False
        )

        # ====================================================
        # LEFT PANEL
        # ====================================================

        left = QFrame()

        left.setObjectName(
            "Panel"
        )

        left_layout = QVBoxLayout(left)

        left_layout.setContentsMargins(
            16,
            16,
            16,
            16,
        )

        left_layout.setSpacing(10)

        left_title = QLabel(
            "SCRAPER PROCESSES"
        )

        left_title.setObjectName(
            "PanelTitle"
        )

        left_layout.addWidget(
            left_title
        )

        self.scraper_list = QListWidget()

        self.scraper_list.setObjectName(
            "ScraperList"
        )

        self.scraper_list.setSelectionMode(
            QListWidget.SingleSelection
        )

        self.scraper_list.currentItemChanged.connect(
            self._on_scraper_selected
        )

        left_layout.addWidget(
            self.scraper_list,
            1,
        )

        new_button = QPushButton(
            "+ NEW SCRAPER"
        )

        new_button.setObjectName(
            "PrimaryButton"
        )

        new_button.clicked.connect(
            self._create_scraper
        )

        left_layout.addWidget(
            new_button
        )

        actions_row_1 = QHBoxLayout()

        self.start_button = QPushButton(
            "START"
        )

        self.stop_button = QPushButton(
            "STOP"
        )

        actions_row_1.addWidget(
            self.start_button
        )

        actions_row_1.addWidget(
            self.stop_button
        )

        left_layout.addLayout(
            actions_row_1
        )

        actions_row_2 = QHBoxLayout()

        self.restart_button = QPushButton(
            "RESTART"
        )

        self.kill_button = QPushButton(
            "KILL"
        )

        actions_row_2.addWidget(
            self.restart_button
        )

        actions_row_2.addWidget(
            self.kill_button
        )

        left_layout.addLayout(
            actions_row_2
        )

        self.remove_button = QPushButton(
            "REMOVE"
        )

        self.remove_button.setObjectName(
            "DangerButton"
        )

        left_layout.addWidget(
            self.remove_button
        )

        self.start_button.clicked.connect(
            self._start_selected
        )

        self.stop_button.clicked.connect(
            self._stop_selected
        )

        self.restart_button.clicked.connect(
            self._restart_selected
        )

        self.kill_button.clicked.connect(
            self._kill_selected
        )

        self.remove_button.clicked.connect(
            self._remove_selected
        )

        splitter.addWidget(left)

        # ====================================================
        # RIGHT PANEL
        # ====================================================

        right = QFrame()

        right.setObjectName(
            "Panel"
        )

        right_layout = QVBoxLayout(right)

        right_layout.setContentsMargins(
            16,
            16,
            16,
            16,
        )

        right_layout.setSpacing(10)

        self.detail_title = QLabel(
            "NO SCRAPER SELECTED"
        )

        self.detail_title.setObjectName(
            "DetailTitle"
        )

        right_layout.addWidget(
            self.detail_title
        )

        self.detail_status = QLabel(
            "STATUS: —"
        )

        self.detail_status.setObjectName(
            "DetailStatus"
        )

        right_layout.addWidget(
            self.detail_status
        )

        detail_scroll = QScrollArea()

        detail_scroll.setWidgetResizable(
            True
        )

        detail_scroll.setFrameShape(
            QFrame.NoFrame
        )

        detail_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        detail_content = QWidget()

        detail_content_layout = QVBoxLayout(
            detail_content
        )

        detail_content_layout.setContentsMargins(
            0,
            0,
            6,
            0,
        )

        detail_content_layout.setSpacing(10)

        runtime_frame = self._create_info_frame(
            "RUNTIME"
        )

        runtime_layout = runtime_frame.layout()

        self.runtime_text = QTextEdit()

        self.runtime_text.setReadOnly(True)

        self.runtime_text.setMinimumHeight(
            170
        )

        runtime_layout.addWidget(
            self.runtime_text
        )

        detail_content_layout.addWidget(
            runtime_frame
        )

        config_frame = self._create_info_frame(
            "CONFIGURATION"
        )

        config_layout = config_frame.layout()

        self.config_text = QTextEdit()

        self.config_text.setReadOnly(True)

        self.config_text.setMinimumHeight(
            200
        )

        config_layout.addWidget(
            self.config_text
        )

        detail_content_layout.addWidget(
            config_frame
        )

        event_frame = self._create_info_frame(
            "MASTER EVENTS"
        )

        event_layout = event_frame.layout()

        self.event_text = QTextEdit()

        self.event_text.setReadOnly(True)

        self.event_text.setMinimumHeight(
            200
        )

        event_layout.addWidget(
            self.event_text
        )

        detail_content_layout.addWidget(
            event_frame
        )

        detail_content_layout.addStretch(1)

        detail_scroll.setWidget(
            detail_content
        )

        right_layout.addWidget(
            detail_scroll,
            1,
        )

        splitter.addWidget(right)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        splitter.setSizes(
            [360, 1000]
        )

        layout.addWidget(
            splitter,
            1,
        )

        # ====================================================
        # FOOTER
        # ====================================================

        footer = QHBoxLayout()

        self.footer_label = QLabel(
            "READY"
        )

        self.footer_label.setObjectName(
            "Footer"
        )

        footer.addWidget(
            self.footer_label
        )

        footer.addStretch()

        self.database_button = QPushButton(
            "DATA MANAGER"
        )

        self.database_button.setObjectName(
            "DatabaseButton"
        )

        self.database_button.setCursor(
            Qt.PointingHandCursor
        )

        self.database_button.clicked.connect(
            self._open_database_manager
        )

        footer.addWidget(
            self.database_button
        )

        refresh_button = QPushButton(
            "REFRESH"
        )

        refresh_button.clicked.connect(
            self.refresh
        )

        footer.addWidget(
            refresh_button
        )

        layout.addLayout(
            footer
        )

        self._refresh_button = refresh_button

        self._set_action_buttons_enabled(
            False
        )

    # ========================================================
    # STAT CARD
    # ========================================================

    @staticmethod
    def _create_stat(
        parent_layout: QHBoxLayout,
        label: str,
        value_color: str,
    ) -> QLabel:

        frame = QFrame()

        frame.setObjectName(
            "StatCard"
        )

        box = QVBoxLayout(frame)

        box.setContentsMargins(
            15,
            11,
            15,
            11,
        )

        box.setSpacing(3)

        value = QLabel("0")

        value.setObjectName(
            "StatValue"
        )

        value.setStyleSheet(
            f"color: {value_color};"
        )

        caption = QLabel(label)

        caption.setObjectName(
            "StatCaption"
        )

        box.addWidget(value)
        box.addWidget(caption)

        parent_layout.addWidget(
            frame,
            1,
        )

        return value

    # ========================================================
    # INFO FRAME
    # ========================================================

    @staticmethod
    def _create_info_frame(
        title: str,
    ) -> QFrame:

        frame = QFrame()

        frame.setObjectName(
            "InfoFrame"
        )

        layout = QVBoxLayout(frame)

        layout.setContentsMargins(
            13,
            11,
            13,
            13,
        )

        layout.setSpacing(8)

        label = QLabel(title)

        label.setObjectName(
            "InfoTitle"
        )

        layout.addWidget(label)

        return frame

    # ========================================================
    # REFRESH
    # ========================================================

    def refresh(self) -> None:

        if self._building_list:
            return

        try:

            self.controller.refresh()

            processes = self._get_processes()

            self._last_refresh_error = ""

            self.connection_label.setText(
                "● MASTER ONLINE"
            )

            self.connection_label.setStyleSheet(
                f"color: {GREEN};"
            )

            self._update_stats(
                processes
            )

            self._rebuild_scraper_list(
                processes
            )

            self._update_selected_details()

            self.footer_label.setText(
                f"{len(processes)} SCRAPER(S) // SYNCHRONIZED"
            )

        except Exception as exc:

            message = str(
                exc
            ).strip()

            if not message:
                message = "Unknown controller error."

            self._last_refresh_error = message

            self.connection_label.setText(
                "● MASTER ERROR"
            )

            self.connection_label.setStyleSheet(
                f"color: {RED};"
            )

            self.footer_label.setText(
                f"REFRESH ERROR // {message}"
            )

    # ========================================================
    # PROCESS DISCOVERY
    # ========================================================

    def _get_processes(self) -> list[Any]:

        result = self.controller.all_processes()

        if result is None:
            return []

        if isinstance(
            result,
            dict,
        ):

            return list(
                result.values()
            )

        try:
            return list(result)

        except TypeError:
            return []

    # ========================================================
    # PROCESS NAME
    # ========================================================

    @staticmethod
    def _process_name(
        process: Any,
    ) -> str:

        if isinstance(
            process,
            dict,
        ):

            for key in (
                "name",
                "scraper",
                "scraper_name",
                "id",
            ):

                value = process.get(key)

                if value is not None:
                    return str(value)

            return "UNKNOWN"

        for attribute in (
            "name",
            "scraper_name",
            "id",
        ):

            value = getattr(
                process,
                attribute,
                None,
            )

            if value is not None:
                return str(value)

        return "UNKNOWN"

    # ========================================================
    # STATUS
    # ========================================================

    def _process_status(
        self,
        name: str,
        process: Any = None,
    ) -> Any:

        try:

            status = self.controller.status(
                name
            )

            if status is not None:
                return status

        except Exception:
            pass

        if isinstance(
            process,
            dict,
        ):

            return process.get(
                "status"
            )

        return getattr(
            process,
            "status",
            None,
        )

    # ========================================================
    # NORMALIZE STATUS
    # ========================================================

    @staticmethod
    def _normalize_status(
        status: Any,
    ) -> Any:

        if status is None:
            return None

        if isinstance(
            status,
            ScraperStatus,
        ):
            return status

        raw = getattr(
            status,
            "value",
            status,
        )

        raw = str(
            raw
        ).strip().lower()

        for candidate in ScraperStatus:

            candidate_value = str(
                getattr(
                    candidate,
                    "value",
                    candidate,
                )
            ).strip().lower()

            if raw == candidate_value:
                return candidate

            if raw == str(
                candidate
            ).strip().lower():

                return candidate

        return status

    # ========================================================
    # STATUS TEXT
    # ========================================================

    @classmethod
    def _status_text(
        cls,
        status: Any,
    ) -> str:

        normalized = cls._normalize_status(
            status
        )

        if normalized is None:
            return "UNKNOWN"

        value = getattr(
            normalized,
            "value",
            normalized,
        )

        return str(
            value
        ).upper()

    # ========================================================
    # STATUS COLOR
    # ========================================================

    @classmethod
    def _status_color(
        cls,
        status: Any,
    ) -> str:

        normalized = cls._normalize_status(
            status
        )

        return STATUS_COLORS.get(
            normalized,
            TEXT_MUTED,
        )

    # ========================================================
    # STATS
    # ========================================================

    def _update_stats(
        self,
        processes: list[Any],
    ) -> None:

        counts = {
            "running": 0,
            "starting": 0,
            "failed": 0,
            "finished": 0,
        }

        for process in processes:

            name = self._process_name(
                process
            )

            status = self._normalize_status(
                self._process_status(
                    name,
                    process,
                )
            )

            if status == ScraperStatus.RUNNING:

                counts["running"] += 1

            elif status in {
                ScraperStatus.CREATED,
                ScraperStatus.STARTING,
                ScraperStatus.STOPPING,
            }:

                counts["starting"] += 1

            elif status in {
                ScraperStatus.CRASHED,
                ScraperStatus.KILLED,
            }:

                counts["failed"] += 1

            elif status == ScraperStatus.FINISHED:

                counts["finished"] += 1

        self.total_value.setText(
            str(len(processes))
        )

        self.running_value.setText(
            str(counts["running"])
        )

        self.starting_value.setText(
            str(counts["starting"])
        )

        self.failed_value.setText(
            str(counts["failed"])
        )

        self.finished_value.setText(
            str(counts["finished"])
        )

    # ========================================================
    # REBUILD LIST
    # ========================================================

    def _rebuild_scraper_list(
        self,
        processes: list[Any],
    ) -> None:

        selected_name = self.current_scraper

        self._building_list = True

        try:

            self.scraper_list.blockSignals(
                True
            )

            self.scraper_list.clear()

            names: list[str] = []

            for process in processes:

                name = self._process_name(
                    process
                )

                if not name:
                    continue

                names.append(
                    name
                )

            names = sorted(
                set(names),
                key=str.lower,
            )

            target_row = -1

            process_by_name = {
                self._process_name(process): process
                for process in processes
            }

            for index, name in enumerate(
                names
            ):

                process = process_by_name.get(
                    name
                )

                status = self._process_status(
                    name,
                    process,
                )

                item = QListWidgetItem()

                item.setData(
                    Qt.UserRole,
                    name,
                )

                item.setText(
                    f"●  {name}\n"
                    f"    {self._status_text(status)}"
                )

                item.setForeground(
                    QColor(
                        self._status_color(status)
                    )
                )

                self.scraper_list.addItem(
                    item
                )

                if (
                    selected_name
                    and name == selected_name
                ):

                    target_row = index

            if target_row >= 0:

                self.scraper_list.setCurrentRow(
                    target_row
                )

            elif self.scraper_list.count():

                self.scraper_list.setCurrentRow(
                    0
                )

            else:

                self.current_scraper = None

        finally:

            self.scraper_list.blockSignals(
                False
            )

            self._building_list = False

        self._on_scraper_selected(
            self.scraper_list.currentItem(),
            None,
        )

    # ========================================================
    # SELECTION
    # ========================================================

    def _on_scraper_selected(
        self,
        current: Optional[QListWidgetItem],
        previous: Optional[QListWidgetItem],
    ) -> None:

        del previous

        if current is None:

            self.current_scraper = None

            self.detail_title.setText(
                "NO SCRAPER SELECTED"
            )

            self.detail_status.setText(
                "STATUS: —"
            )

            self.runtime_text.clear()
            self.config_text.clear()
            self.event_text.clear()

            self._set_action_buttons_enabled(
                False
            )

            return

        name = current.data(
            Qt.UserRole
        )

        if not name:
            return

        self.current_scraper = str(
            name
        )

        self._update_selected_details()

    # ========================================================
    # DETAILS
    # ========================================================

    def _update_selected_details(self) -> None:

        name = self.current_scraper

        if not name:
            return

        self.detail_title.setText(
            name.upper()
        )

        try:

            status = self.controller.status(
                name
            )

        except Exception:

            status = None

        status_text = self._status_text(
            status
        )

        self.detail_status.setText(
            f"STATUS: {status_text}"
        )

        self.detail_status.setStyleSheet(
            f"color: {self._status_color(status)};"
            "font-weight: 900;"
        )

        self._load_runtime(
            name
        )

        self._load_config(
            name
        )

        self._load_events(
            name
        )

        self._update_action_buttons(
            name,
            status,
        )

    # ========================================================
    # RUNTIME
    # ========================================================

    def _load_runtime(
        self,
        name: str,
    ) -> None:

        try:

            snapshot = self.controller.snapshot(
                name
            )

            self.runtime_text.setPlainText(
                self._format_data(
                    snapshot
                )
            )

        except Exception as exc:

            self.runtime_text.setPlainText(
                f"SNAPSHOT ERROR\n\n{exc}"
            )

    # ========================================================
    # CONFIG
    # ========================================================

    def _load_config(
        self,
        name: str,
    ) -> None:

        try:

            info = self.controller.scraper_info(
                name
            )

            self.config_text.setPlainText(
                self._format_data(
                    info
                )
            )

        except Exception as exc:

            self.config_text.setPlainText(
                f"CONFIG ERROR\n\n{exc}"
            )

    # ========================================================
    # EVENTS
    # ========================================================

    def _load_events(
        self,
        name: str,
    ) -> None:

        try:

            snapshot = self.controller.snapshot(
                name
            )

            events = None

            if isinstance(
                snapshot,
                dict,
            ):

                events = snapshot.get(
                    "events"
                )

                if events is None:

                    runtime = snapshot.get(
                        "runtime"
                    )

                    if isinstance(
                        runtime,
                        dict,
                    ):

                        events = runtime.get(
                            "events"
                        )

            if events is None:

                self.event_text.setPlainText(
                    "NO EVENTS AVAILABLE"
                )

                return

            self.event_text.setPlainText(
                self._format_data(
                    events
                )
            )

        except Exception as exc:

            self.event_text.setPlainText(
                f"EVENT ERROR\n\n{exc}"
            )

    # ========================================================
    # FORMAT DATA
    # ========================================================

    @classmethod
    def _format_data(
        cls,
        value: Any,
        indent: int = 0,
    ) -> str:

        prefix = " " * indent

        if value is None:
            return f"{prefix}—"

        if isinstance(
            value,
            dict,
        ):

            if not value:
                return f"{prefix}{{}}"

            lines: list[str] = []

            for key in sorted(
                value.keys(),
                key=lambda item: str(item).lower(),
            ):

                item_value = value[key]

                if isinstance(
                    item_value,
                    (dict, list, tuple),
                ):

                    lines.append(
                        f"{prefix}{key}:"
                    )

                    lines.append(
                        cls._format_data(
                            item_value,
                            indent + 4,
                        )
                    )

                else:

                    lines.append(
                        f"{prefix}{key}: {item_value}"
                    )

            return "\n".join(
                lines
            )

        if isinstance(
            value,
            (list, tuple),
        ):

            if not value:
                return f"{prefix}[]"

            lines: list[str] = []

            for item in value:

                if isinstance(
                    item,
                    (dict, list, tuple),
                ):

                    lines.append(
                        f"{prefix}-"
                    )

                    lines.append(
                        cls._format_data(
                            item,
                            indent + 4,
                        )
                    )

                else:

                    lines.append(
                        f"{prefix}- {item}"
                    )

            return "\n".join(
                lines
            )

        return f"{prefix}{value}"

    # ========================================================
    # ACTION BUTTONS
    # ========================================================

    def _set_action_buttons_enabled(
        self,
        enabled: bool,
    ) -> None:

        for button in (
            self.start_button,
            self.stop_button,
            self.restart_button,
            self.kill_button,
            self.remove_button,
        ):

            button.setEnabled(
                enabled
            )

    # ========================================================
    # ACTION STATE
    # ========================================================

    def _update_action_buttons(
        self,
        name: str,
        status: Any,
    ) -> None:

        if not name:

            self._set_action_buttons_enabled(
                False
            )

            return

        actions: set[str] = set()

        try:

            result = (
                self.controller.available_actions(
                    name
                )
            )

            if result:

                if isinstance(
                    result,
                    dict,
                ):

                    actions = {
                        str(key).lower()
                        for key, enabled in result.items()
                        if enabled
                    }

                else:

                    actions = {
                        str(action).lower()
                        for action in result
                    }

        except Exception:

            actions = set()

        if not actions:

            normalized = self._normalize_status(
                status
            )

            actions = self._fallback_actions(
                normalized
            )

        self.start_button.setEnabled(
            "start" in actions
        )

        self.stop_button.setEnabled(
            "stop" in actions
        )

        self.restart_button.setEnabled(
            "restart" in actions
        )

        self.kill_button.setEnabled(
            "kill" in actions
        )

        self.remove_button.setEnabled(
            "remove" in actions
        )

    # ========================================================
    # FALLBACK ACTIONS
    # ========================================================

    @staticmethod
    def _fallback_actions(
        status: Any,
    ) -> set[str]:

        if status in {
            ScraperStatus.CREATED,
            ScraperStatus.STOPPED,
            ScraperStatus.FINISHED,
            ScraperStatus.CRASHED,
            ScraperStatus.KILLED,
        }:

            return {
                "start",
                "restart",
                "remove",
            }

        if status == ScraperStatus.STARTING:

            return {
                "stop",
                "kill",
            }

        if status == ScraperStatus.RUNNING:

            return {
                "stop",
                "restart",
                "kill",
            }

        if status == ScraperStatus.STOPPING:

            return {
                "kill",
            }

        return set()

    # ========================================================
    # DATA MANAGER
    # ========================================================

    def _open_database_manager(self) -> None:
        """Open the real project DataManagerWindow as a top-level window."""

        try:

            if self._database_manager_window is not None:

                try:
                    if self._database_manager_window.isVisible():
                        self._database_manager_window.raise_()
                        self._database_manager_window.activateWindow()
                        return
                except RuntimeError:
                    self._database_manager_window = None

            window = DataManagerWindow()

            window.setWindowFlag(
                Qt.Window,
                True,
            )

            window.setAttribute(
                Qt.WA_DeleteOnClose,
                True,
            )

            window.destroyed.connect(
                self._on_database_manager_destroyed
            )

            self._database_manager_window = window

            window.show()
            window.raise_()
            window.activateWindow()

            self.footer_label.setText(
                "DATA MANAGER // OPEN"
            )

        except Exception as exc:

            self._database_manager_window = None

            QMessageBox.critical(
                self,
                "DATA MANAGER ERROR",
                (
                    "Unable to open Data Manager.\n\n"
                    f"{type(exc).__name__}: {exc}"
                ),
            )

    def _on_database_manager_destroyed(
        self,
        *_args: Any,
    ) -> None:

        self._database_manager_window = None

    # ========================================================
    # CREATE SCRAPER
    # ========================================================

    def _create_scraper(self) -> None:

        dialog = NewScraperDialog(
            self
        )

        if dialog.exec_() != QDialog.Accepted:
            return

        data = dialog.data()

        name = data.get(
            "name"
        )

        if not name:
            return

        try:

            if self.controller.exists(
                name
            ):

                QMessageBox.warning(
                    self,
                    "SCRAPER EXISTS",
                    f"Scraper '{name}' already exists.",
                )

                return

            self.controller.create_scraper(
                data
            )

            self.current_scraper = name

            self.footer_label.setText(
                f"SCRAPER CREATED // {name}"
            )

            self.refresh()

        except Exception as exc:

            QMessageBox.critical(
                self,
                "CREATE FAILED",
                str(exc),
            )

    # ========================================================
    # SELECTED NAME
    # ========================================================

    def _selected_name(
        self,
    ) -> Optional[str]:

        item = (
            self.scraper_list.currentItem()
        )

        if item is None:
            return None

        value = item.data(
            Qt.UserRole
        )

        if value is None:
            return None

        return str(
            value
        )

    # ========================================================
    # START
    # ========================================================

    def _start_selected(self) -> None:

        name = self._selected_name()

        if not name:
            return

        self._run_action(
            "START",
            self.controller.start,
            name,
        )

    # ========================================================
    # STOP
    # ========================================================

    def _stop_selected(self) -> None:

        name = self._selected_name()

        if not name:
            return

        self._run_action(
            "STOP",
            self.controller.stop,
            name,
        )

    # ========================================================
    # RESTART
    # ========================================================

    def _restart_selected(self) -> None:

        name = self._selected_name()

        if not name:
            return

        self._run_action(
            "RESTART",
            self.controller.restart,
            name,
        )

    # ========================================================
    # KILL
    # ========================================================

    def _kill_selected(self) -> None:

        name = self._selected_name()

        if not name:
            return

        answer = QMessageBox.question(
            self,
            "KILL SCRAPER",
            f"Forcefully terminate '{name}'?",
            QMessageBox.Yes
            | QMessageBox.No,
            QMessageBox.No,
        )

        if answer != QMessageBox.Yes:
            return

        self._run_action(
            "KILL",
            self.controller.kill,
            name,
        )

    # ========================================================
    # REMOVE
    # ========================================================

    def _remove_selected(self) -> None:

        name = self._selected_name()

        if not name:
            return

        try:

            status = self.controller.status(
                name
            )

        except Exception:

            status = None

        normalized = self._normalize_status(
            status
        )

        if normalized in {
            ScraperStatus.STARTING,
            ScraperStatus.RUNNING,
            ScraperStatus.STOPPING,
        }:

            QMessageBox.warning(
                self,
                "SCRAPER ACTIVE",
                (
                    f"Scraper '{name}' is currently "
                    f"{self._status_text(status)}.\n\n"
                    "Stop or kill the scraper before removing it."
                ),
            )

            return

        answer = QMessageBox.question(
            self,
            "REMOVE SCRAPER",
            (
                f"Remove scraper '{name}' "
                "from the master registry?"
            ),
            QMessageBox.Yes
            | QMessageBox.No,
            QMessageBox.No,
        )

        if answer != QMessageBox.Yes:
            return

        try:

            self.controller.remove(
                name
            )

            self.current_scraper = None

            self.footer_label.setText(
                f"SCRAPER REMOVED // {name}"
            )

            self.refresh()

        except Exception as exc:

            QMessageBox.critical(
                self,
                "REMOVE FAILED",
                str(exc),
            )

    # ========================================================
    # ACTION EXECUTOR
    # ========================================================

    def _run_action(
        self,
        action_name: str,
        action: Any,
        name: str,
    ) -> None:

        try:

            action(
                name
            )

            self.footer_label.setText(
                f"{action_name} // {name}"
            )

            self.refresh()

        except Exception as exc:

            QMessageBox.critical(
                self,
                f"{action_name} FAILED",
                str(exc),
            )

            self.refresh()

    # ========================================================
    # STYLE
    # ========================================================

    def _apply_style(self) -> None:

        self.setStyleSheet(
            f"""
            QWidget {{
                background: {BG};
                color: {TEXT};
                font-family: "JetBrains Mono", monospace;
            }}

            QLabel {{
                background: transparent;
                color: {TEXT};
            }}

            QLabel#MasterTitle {{
                color: {AMBER};
                font-size: 30px;
                font-weight: 900;
            }}

            QLabel#MasterSubtitle {{
                color: {TEXT_MUTED};
                font-size: 11px;
                font-weight: 900;
            }}

            QLabel#Connection {{
                color: {GREEN};
                font-size: 12px;
                font-weight: 900;
            }}

            QFrame#StatCard {{
                background: {SURFACE};
                border: 1px solid {BORDER_SOFT};
                border-radius: 10px;
            }}

            QLabel#StatValue {{
                font-size: 24px;
                font-weight: 900;
            }}

            QLabel#StatCaption {{
                color: {TEXT_MUTED};
                font-size: 10px;
                font-weight: 900;
            }}

            QFrame#Panel {{
                background: {SURFACE};
                border: 1px solid {BORDER_SOFT};
                border-radius: 11px;
            }}

            QLabel#PanelTitle {{
                color: {AMBER};
                font-size: 13px;
                font-weight: 900;
            }}

            QLabel#DetailTitle {{
                color: {TEXT};
                font-size: 20px;
                font-weight: 900;
            }}

            QLabel#DetailStatus {{
                font-family: "JetBrains Mono";
                font-size: 12px;
                font-weight: 900;
            }}

            QFrame#InfoFrame {{
                background: {SURFACE_2};
                border: 1px solid {BORDER_SOFT};
                border-radius: 9px;
            }}

            QLabel#InfoTitle {{
                color: {AMBER};
                font-size: 11px;
                font-weight: 900;
            }}

            QTextEdit {{
                background: {BG};
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER_SOFT};
                border-radius: 7px;
                padding: 10px;
                font-family: "JetBrains Mono";
                font-size: 12px;
                selection-background-color: {PURPLE};
                selection-color: {TEXT};
            }}

            QListWidget {{
                background: {SURFACE_2};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 6px;
                outline: none;
            }}

            QListWidget::item {{
                color: {TEXT_SECONDARY};
                padding: 11px;
                min-height: 26px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 800;
            }}

            QListWidget::item:hover {{
                background: {SURFACE_3};
                color: {TEXT};
            }}

            QListWidget::item:selected {{
                background: {PURPLE};
                color: {AMBER};
                border-left: 4px solid {ORANGE};
            }}

            QPushButton {{
                background: {SURFACE_2};
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 10px 15px;
                min-height: 40px;
                font-size: 11px;
                font-weight: 900;
            }}

            QPushButton:hover {{
                color: {AMBER};
                border-color: {ORANGE};
                background: {SURFACE_3};
            }}

            QPushButton:pressed {{
                background: {DEEP_ORANGE};
                color: {TEXT};
            }}

            QPushButton:disabled {{
                color: {TEXT_MUTED};
                background: {SURFACE};
                border-color: {BORDER_SOFT};
            }}

            QPushButton#PrimaryButton {{
                background: {AMBER};
                color: {BG};
                border-color: {AMBER};
                min-height: 43px;
            }}

            QPushButton#PrimaryButton:hover {{
                background: {ORANGE};
                border-color: {ORANGE};
                color: {TEXT};
            }}

            QPushButton#DatabaseButton {{
                color: {AMBER};
                border-color: {BURGUNDY};
                min-width: 150px;
            }}

            QPushButton#DatabaseButton:hover {{
                color: {TEXT};
                background: {PURPLE};
                border-color: {ORANGE};
            }}

            QPushButton#DangerButton {{
                color: {RED};
            }}

            QPushButton#DangerButton:hover {{
                color: {TEXT};
                background: {RED};
                border-color: {RED};
            }}

            QScrollArea {{
                background: transparent;
                border: none;
            }}

            QSplitter::handle {{
                background: {BORDER_SOFT};
            }}

            QScrollBar:vertical {{
                background: {SURFACE};
                width: 11px;
                border-radius: 5px;
            }}

            QScrollBar::handle:vertical {{
                background: {BORDER};
                min-height: 40px;
                border-radius: 5px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: {ORANGE};
            }}

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}

            QScrollBar:horizontal {{
                background: {SURFACE};
                height: 11px;
                border-radius: 5px;
            }}

            QScrollBar::handle:horizontal {{
                background: {BORDER};
                min-width: 40px;
                border-radius: 5px;
            }}

            QLabel#Footer {{
                color: {TEXT_MUTED};
                font-family: "JetBrains Mono";
                font-size: 10px;
                font-weight: 900;
            }}
            """
        )