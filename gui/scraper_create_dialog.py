# ============================================================
# EYES MASTER — NEW SCRAPER DIALOG
# ============================================================
#
# FILE:
#     gui/new_scraper_dialog.py
#
# STATUS:
#     CANONICAL / CORE
#
# ROLE:
#     Collect and validate configuration required to create
#     a new scraper.
#
# RESPONSIBILITIES:
#
#     - scraper identity
#     - target
#     - database path
#     - scraper directory
#     - keywords
#     - search configuration
#     - Neshan geographic context
#     - provider selection
#     - validation
#     - structured configuration output
#
# DOES NOT OWN:
#
#     - scraper execution
#     - provider implementation
#     - provider discovery logic
#     - database creation
#     - process lifecycle
#     - worker lifecycle
#
# IMPORTANT:
#
#     The query itself is NEVER modified for Neshan.
#
#     If Neshan is selected, optional geographic context is
#     supplied separately:
#
#         province
#         city
#
#     Example:
#
#         query:
#             پاساژ رشت سایت
#
#         province:
#             گیلان
#
#         city:
#             رشت
#
#     The provider receives these as separate configuration
#     values and remains responsible for constructing its own
#     API request.
#
# UI CONTRACT:
#
#     Provider selection MUST remain the final configuration
#     section.
#
# KEYWORD CONTRACT:
#
#     - Every keyword remains directly visible.
#     - No "N more" summary.
#     - No internal keyword scrollbar.
#     - Main dialog scroll area handles large keyword sets.
#
# ============================================================

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from providers.manager import ProviderManager


# ============================================================
# EYES MASTER PALETTE
# ============================================================

BG = "#17101f"

SURFACE = "#21152a"
SURFACE_2 = "#281a31"
SURFACE_3 = "#301f38"

BORDER = "#4a3045"
BORDER_ACTIVE = "#F3742B"

TEXT = "#FFF7E6"
TEXT_SECONDARY = "#D8C7C0"
TEXT_MUTED = "#9C858D"

AMBER = "#FED172"
ORANGE = "#F3742B"
DEEP_ORANGE = "#B83A14"
BURGUNDY = "#612E37"
PURPLE = "#231650"

GREEN = "#72D6A3"
RED = "#E56B5D"


# ============================================================
# DEFAULTS
# ============================================================

DEFAULT_KEYWORD = "مدرسه"

DEFAULT_MAX_QUERIES = 20
DEFAULT_PAGES_PER_QUERY = 1
DEFAULT_RESULTS_PER_PAGE = 100
DEFAULT_DELAY = 0
DEFAULT_TIMEOUT = 30


# ============================================================
# PROVIDER IDENTIFIERS
# ============================================================

NESHAN_PROVIDER_KEY = "neshan"


# ============================================================
# NEW SCRAPER DIALOG
# ============================================================

class NewScraperDialog(QDialog):
    """
    Dialog used to collect configuration for a new scraper.

    Provider-independent configuration is collected first.

    Provider-specific configuration is collected before the
    final provider selection section.

    Neshan geographic context:

        neshan_province
        neshan_city

    is optional and is only enabled when the selected provider
    is Neshan.

    Output contract
    ---------------

        {
            "name": str,
            "providers": [str],
            "keyword": str,
            "keywords": list[str],
            "target": str | None,
            "database": str,
            "scraper_dir": str | None,
            "config": {
                ...
                "neshan": {
                    "province": str | None,
                    "city": str | None
                }
            }
        }
    """

    # ========================================================
    # INIT
    # ========================================================

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:

        super().__init__(parent)

        self.setWindowTitle(
            "NEW SCRAPER"
        )

        self.setObjectName(
            "NewScraperDialog"
        )

        # ----------------------------------------------------
        # INTERNAL STATE
        # ----------------------------------------------------

        self._providers: list[str] = []

        self._database_auto = True

        self._last_generated_database = ""

        # ----------------------------------------------------
        # WINDOW
        # ----------------------------------------------------

        self._configure_window()

        # ----------------------------------------------------
        # UI
        # ----------------------------------------------------

        self._build_ui()

        self._set_default_values()

        self._load_providers()

        self._apply_style()

        # ----------------------------------------------------
        # Keyword sizing
        # ----------------------------------------------------

        self._update_keyword_editor_height()

        QTimer.singleShot(
            0,
            self._update_keyword_editor_height,
        )

        # ----------------------------------------------------
        # Neshan state
        # ----------------------------------------------------

        self._update_neshan_fields()

        self._update_create_state()

    # ========================================================
    # WINDOW CONFIGURATION
    # ========================================================

    def _configure_window(self) -> None:
        """
        Configure a large centered dialog.
        """

        screen = self.screen()

        if screen is None:

            parent_widget = self.parentWidget()

            if parent_widget is not None:
                screen = parent_widget.screen()

        if screen is None:

            self.resize(
                1000,
                800,
            )

            return

        available = (
            screen.availableGeometry()
        )

        width = min(
            max(
                900,
                int(
                    available.width() * 0.90
                ),
            ),
            available.width(),
        )

        height = min(
            max(
                700,
                int(
                    available.height() * 0.90
                ),
            ),
            available.height(),
        )

        self.resize(
            width,
            height,
        )

        self.setMinimumSize(
            min(
                900,
                available.width(),
            ),
            min(
                700,
                available.height(),
            ),
        )

        self.move(
            available.x()
            + (
                available.width()
                - width
            ) // 2,
            available.y()
            + (
                available.height()
                - height
            ) // 2,
        )

    # ========================================================
    # BUILD UI
    # ========================================================

    def _build_ui(self) -> None:
        """
        Build the complete scraper configuration form.

        Provider selection is deliberately the final
        configuration section.
        """

        outer = QVBoxLayout(
            self
        )

        outer.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        outer.setSpacing(
            0
        )

        # ====================================================
        # MAIN SCROLL AREA
        # ====================================================

        self.scroll_area = QScrollArea()

        self.scroll_area.setWidgetResizable(
            True
        )

        self.scroll_area.setFrameShape(
            QFrame.NoFrame
        )

        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        outer.addWidget(
            self.scroll_area,
            1,
        )

        # ====================================================
        # CONTENT
        # ====================================================

        content = QWidget()

        content.setObjectName(
            "DialogContent"
        )

        self.scroll_area.setWidget(
            content
        )

        root = QVBoxLayout(
            content
        )

        root.setContentsMargins(
            30,
            28,
            30,
            30,
        )

        root.setSpacing(
            20
        )

        # ====================================================
        # HEADER
        # ====================================================

        title = QLabel(
            "NEW SCRAPER"
        )

        title.setObjectName(
            "DialogTitle"
        )

        subtitle = QLabel(
            "CREATE A NEW SCRAPER PROCESS"
        )

        subtitle.setObjectName(
            "DialogSubtitle"
        )

        root.addWidget(
            title
        )

        root.addWidget(
            subtitle
        )

        # ====================================================
        # BASIC CONFIGURATION
        # ====================================================

        form_frame = QFrame()

        form_frame.setObjectName(
            "FormPanel"
        )

        form = QFormLayout(
            form_frame
        )

        form.setContentsMargins(
            20,
            20,
            20,
            20,
        )

        form.setHorizontalSpacing(
            22
        )

        form.setVerticalSpacing(
            17
        )

        # ====================================================
        # NAME
        # ====================================================

        self.name_edit = QLineEdit()

        self.name_edit.setObjectName(
            "NameEdit"
        )

        self.name_edit.setPlaceholderText(
            "e.g. iran_schools"
        )

        self.name_edit.setMinimumHeight(
            46
        )

        self.name_edit.textChanged.connect(
            self._name_changed
        )

        form.addRow(
            "NAME",
            self.name_edit,
        )

        # ====================================================
        # TARGET
        # ====================================================

        self.target_edit = QLineEdit()

        self.target_edit.setObjectName(
            "TargetEdit"
        )

        self.target_edit.setPlaceholderText(
            "Optional target"
        )

        self.target_edit.setMinimumHeight(
            46
        )

        self.target_edit.textChanged.connect(
            self._update_create_state
        )

        form.addRow(
            "TARGET",
            self.target_edit,
        )

        # ====================================================
        # DATABASE
        # ====================================================

        self.database_edit = QLineEdit()

        self.database_edit.setObjectName(
            "DatabaseEdit"
        )

        self.database_edit.setMinimumHeight(
            46
        )

        self.database_edit.textEdited.connect(
            self._database_manually_edited
        )

        form.addRow(
            "DATABASE",
            self.database_edit,
        )

        # ====================================================
        # SCRAPER DIRECTORY
        # ====================================================

        self.scraper_dir_edit = QLineEdit()

        self.scraper_dir_edit.setObjectName(
            "ScraperDirEdit"
        )

        self.scraper_dir_edit.setPlaceholderText(
            "Optional scraper directory"
        )

        self.scraper_dir_edit.setMinimumHeight(
            46
        )

        self.scraper_dir_edit.textChanged.connect(
            self._update_create_state
        )

        form.addRow(
            "SCRAPER DIR",
            self.scraper_dir_edit,
        )

        root.addWidget(
            form_frame
        )

        # ====================================================
        # CONFIGURATION TITLE
        # ====================================================

        config_label = QLabel(
            "CONFIGURATION"
        )

        config_label.setObjectName(
            "StandaloneLabel"
        )

        root.addWidget(
            config_label
        )

        # ====================================================
        # CONFIGURATION PANEL
        # ====================================================

        config_frame = QFrame()

        config_frame.setObjectName(
            "ConfigPanel"
        )

        config_layout = QVBoxLayout(
            config_frame
        )

        config_layout.setContentsMargins(
            18,
            16,
            18,
            16,
        )

        config_layout.setSpacing(
            13
        )

        # ====================================================
        # KEYWORDS
        # ====================================================

        keyword_header = QHBoxLayout()

        keyword_label = QLabel(
            "KEYWORDS"
        )

        keyword_label.setObjectName(
            "ConfigLabel"
        )

        keyword_header.addWidget(
            keyword_label
        )

        keyword_header.addStretch()

        keyword_hint = QLabel(
            "ONE KEYWORD PER LINE"
        )

        keyword_hint.setObjectName(
            "KeywordHint"
        )

        keyword_header.addWidget(
            keyword_hint
        )

        config_layout.addLayout(
            keyword_header
        )

        self.keyword_edit = QPlainTextEdit()

        self.keyword_edit.setObjectName(
            "KeywordEdit"
        )

        self.keyword_edit.setPlaceholderText(
            "ONE KEYWORD PER LINE"
        )

        self.keyword_edit.setMinimumHeight(
            48
        )

        self.keyword_edit.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.keyword_edit.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.keyword_edit.setLineWrapMode(
            QPlainTextEdit.NoWrap
        )

        self.keyword_edit.setTabChangesFocus(
            True
        )

        self.keyword_edit.setUndoRedoEnabled(
            True
        )

        self.keyword_edit.textChanged.connect(
            self._keyword_text_changed
        )

        config_layout.addWidget(
            self.keyword_edit
        )

        # ====================================================
        # MAX QUERIES
        # ====================================================

        max_queries_row = QHBoxLayout()

        max_queries_label = QLabel(
            "MAX QUERIES"
        )

        max_queries_label.setObjectName(
            "ConfigLabel"
        )

        self.max_queries_spin = QSpinBox()

        self.max_queries_spin.setObjectName(
            "MaxQueriesSpin"
        )

        self.max_queries_spin.setRange(
            1,
            1_000_000,
        )

        self.max_queries_spin.setMinimumHeight(
            42
        )

        max_queries_row.addWidget(
            max_queries_label
        )

        max_queries_row.addWidget(
            self.max_queries_spin
        )

        max_queries_row.addStretch()

        config_layout.addLayout(
            max_queries_row
        )

        # ====================================================
        # PAGES / QUERY
        # ====================================================

        pages_row = QHBoxLayout()

        pages_label = QLabel(
            "PAGES / QUERY"
        )

        pages_label.setObjectName(
            "ConfigLabel"
        )

        self.pages_per_query_spin = QSpinBox()

        self.pages_per_query_spin.setObjectName(
            "PagesPerQuerySpin"
        )

        self.pages_per_query_spin.setRange(
            1,
            1_000_000,
        )

        self.pages_per_query_spin.setMinimumHeight(
            42
        )

        pages_row.addWidget(
            pages_label
        )

        pages_row.addWidget(
            self.pages_per_query_spin
        )

        pages_row.addStretch()

        config_layout.addLayout(
            pages_row
        )

        # ====================================================
        # RESULTS / PAGE
        # ====================================================

        results_row = QHBoxLayout()

        results_label = QLabel(
            "RESULTS / PAGE"
        )

        results_label.setObjectName(
            "ConfigLabel"
        )

        self.results_per_page_spin = QSpinBox()

        self.results_per_page_spin.setObjectName(
            "ResultsPerPageSpin"
        )

        self.results_per_page_spin.setRange(
            1,
            1_000_000,
        )

        self.results_per_page_spin.setMinimumHeight(
            42
        )

        results_row.addWidget(
            results_label
        )

        results_row.addWidget(
            self.results_per_page_spin
        )

        results_row.addStretch()

        config_layout.addLayout(
            results_row
        )

        # ====================================================
        # DELAY
        # ====================================================

        delay_row = QHBoxLayout()

        delay_label = QLabel(
            "DELAY (SEC)"
        )

        delay_label.setObjectName(
            "ConfigLabel"
        )

        self.delay_spin = QSpinBox()

        self.delay_spin.setObjectName(
            "DelaySpin"
        )

        self.delay_spin.setRange(
            0,
            1_000_000,
        )

        self.delay_spin.setMinimumHeight(
            42
        )

        delay_row.addWidget(
            delay_label
        )

        delay_row.addWidget(
            self.delay_spin
        )

        delay_row.addStretch()

        config_layout.addLayout(
            delay_row
        )

        # ====================================================
        # TIMEOUT
        # ====================================================

        timeout_row = QHBoxLayout()

        timeout_label = QLabel(
            "TIMEOUT (SEC)"
        )

        timeout_label.setObjectName(
            "ConfigLabel"
        )

        self.timeout_spin = QSpinBox()

        self.timeout_spin.setObjectName(
            "TimeoutSpin"
        )

        self.timeout_spin.setRange(
            1,
            1_000_000,
        )

        self.timeout_spin.setMinimumHeight(
            42
        )

        timeout_row.addWidget(
            timeout_label
        )

        timeout_row.addWidget(
            self.timeout_spin
        )

        timeout_row.addStretch()

        config_layout.addLayout(
            timeout_row
        )

        root.addWidget(
            config_frame
        )

        # ====================================================
        # NESHAN GEOGRAPHIC CONTEXT
        #
        # IMPORTANT:
        #
        # This is provider-specific configuration, therefore
        # it is placed BEFORE provider selection.
        #
        # Nothing configuration-related is added after the
        # provider list.
        # ====================================================

        self.neshan_frame = QFrame()

        self.neshan_frame.setObjectName(
            "NeshanPanel"
        )

        neshan_layout = QVBoxLayout(
            self.neshan_frame
        )

        neshan_layout.setContentsMargins(
            18,
            16,
            18,
            16,
        )

        neshan_layout.setSpacing(
            12
        )

        # ====================================================
        # NESHAN HEADER
        # ====================================================

        neshan_header = QHBoxLayout()

        neshan_title = QLabel(
            "NESHAN LOCATION CONTEXT"
        )

        neshan_title.setObjectName(
            "NeshanTitle"
        )

        neshan_header.addWidget(
            neshan_title
        )

        neshan_header.addStretch()

        neshan_hint = QLabel(
            "OPTIONAL"
        )

        neshan_hint.setObjectName(
            "NeshanHint"
        )

        neshan_header.addWidget(
            neshan_hint
        )

        neshan_layout.addLayout(
            neshan_header
        )

        neshan_description = QLabel(
            "CITY AND PROVINCE ARE PASSED SEPARATELY "
            "TO NESHAN. THE ORIGINAL QUERY IS PRESERVED."
        )

        neshan_description.setObjectName(
            "NeshanDescription"
        )

        neshan_description.setWordWrap(
            True
        )

        neshan_layout.addWidget(
            neshan_description
        )

        # ====================================================
        # PROVINCE
        # ====================================================

        province_row = QHBoxLayout()

        province_label = QLabel(
            "PROVINCE"
        )

        province_label.setObjectName(
            "ConfigLabel"
        )

        self.neshan_province_edit = QLineEdit()

        self.neshan_province_edit.setObjectName(
            "NeshanProvinceEdit"
        )

        self.neshan_province_edit.setPlaceholderText(
            "e.g. گیلان"
        )

        self.neshan_province_edit.setMinimumHeight(
            42
        )

        self.neshan_province_edit.textChanged.connect(
            self._update_create_state
        )

        province_row.addWidget(
            province_label
        )

        province_row.addWidget(
            self.neshan_province_edit,
            1,
        )

        neshan_layout.addLayout(
            province_row
        )

        # ====================================================
        # CITY
        # ====================================================

        city_row = QHBoxLayout()

        city_label = QLabel(
            "CITY"
        )

        city_label.setObjectName(
            "ConfigLabel"
        )

        self.neshan_city_edit = QLineEdit()

        self.neshan_city_edit.setObjectName(
            "NeshanCityEdit"
        )

        self.neshan_city_edit.setPlaceholderText(
            "e.g. رشت"
        )

        self.neshan_city_edit.setMinimumHeight(
            42
        )

        self.neshan_city_edit.textChanged.connect(
            self._update_create_state
        )

        city_row.addWidget(
            city_label
        )

        city_row.addWidget(
            self.neshan_city_edit,
            1,
        )

        neshan_layout.addLayout(
            city_row
        )

        root.addWidget(
            self.neshan_frame
        )

        # ====================================================
        # PROVIDER SECTION
        #
        # THIS MUST REMAIN THE FINAL CONFIGURATION SECTION.
        # ====================================================

        provider_separator = QFrame()

        provider_separator.setFrameShape(
            QFrame.HLine
        )

        provider_separator.setObjectName(
            "ProviderSeparator"
        )

        root.addWidget(
            provider_separator
        )

        # ====================================================
        # PROVIDER HEADER
        # ====================================================

        provider_title_row = QHBoxLayout()

        provider_title = QLabel(
            "SEARCH PROVIDER"
        )

        provider_title.setObjectName(
            "ProviderTitle"
        )

        provider_title_row.addWidget(
            provider_title
        )

        provider_title_row.addStretch()

        self.provider_status = QLabel(
            "NO PROVIDER"
        )

        self.provider_status.setObjectName(
            "ProviderStatus"
        )

        provider_title_row.addWidget(
            self.provider_status
        )

        root.addLayout(
            provider_title_row
        )

        provider_hint = QLabel(
            "SELECT EXACTLY ONE PROVIDER"
        )

        provider_hint.setObjectName(
            "ProviderHint"
        )

        root.addWidget(
            provider_hint
        )

        # ====================================================
        # PROVIDER LIST
        # ====================================================

        self.providers_list = QListWidget()

        self.providers_list.setObjectName(
            "ProvidersList"
        )

        self.providers_list.setMinimumHeight(
            150
        )

        self.providers_list.setMaximumHeight(
            240
        )

        self.providers_list.setSelectionMode(
            QListWidget.SingleSelection
        )

        self.providers_list.setUniformItemSizes(
            True
        )

        self.providers_list.itemSelectionChanged.connect(
            self._provider_changed
        )

        root.addWidget(
            self.providers_list
        )

        # ====================================================
        # ACTION BUTTONS
        #
        # ONLY ACTIONS ARE ALLOWED AFTER PROVIDER SECTION.
        # ====================================================

        button_frame = QFrame()

        button_frame.setObjectName(
            "ButtonPanel"
        )

        button_layout = QHBoxLayout(
            button_frame
        )

        button_layout.setContentsMargins(
            0,
            8,
            0,
            0,
        )

        button_layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.Cancel
            | QDialogButtonBox.Ok
        )

        buttons.accepted.connect(
            self._validate
        )

        buttons.rejected.connect(
            self.reject
        )

        self.create_button = (
            buttons.button(
                QDialogButtonBox.Ok
            )
        )

        self.create_button.setText(
            "CREATE SCRAPER"
        )

        self.create_button.setObjectName(
            "CreateButton"
        )

        button_layout.addWidget(
            buttons
        )

        root.addWidget(
            button_frame
        )

    # ========================================================
    # DEFAULT VALUES
    # ========================================================

    def _set_default_values(self) -> None:
        """
        Apply default scraper configuration.
        """

        self.keyword_edit.setPlainText(
            DEFAULT_KEYWORD
        )

        self.max_queries_spin.setValue(
            DEFAULT_MAX_QUERIES
        )

        self.pages_per_query_spin.setValue(
            DEFAULT_PAGES_PER_QUERY
        )

        self.results_per_page_spin.setValue(
            DEFAULT_RESULTS_PER_PAGE
        )

        self.delay_spin.setValue(
            DEFAULT_DELAY
        )

        self.timeout_spin.setValue(
            DEFAULT_TIMEOUT
        )

        self._database_auto = True

        self._update_database_path()

        # ----------------------------------------------------
        # Neshan context starts empty.
        # ----------------------------------------------------

        self.neshan_province_edit.clear()

        self.neshan_city_edit.clear()

    # ========================================================
    # KEYWORD TEXT CHANGED
    # ========================================================

    def _keyword_text_changed(self) -> None:
        """
        React to keyword editor changes.
        """

        self._update_keyword_editor_height()

        self._update_create_state()

        QTimer.singleShot(
            0,
            self._update_keyword_editor_height,
        )

    # ========================================================
    # KEYWORD EDITOR HEIGHT
    # ========================================================

    def _update_keyword_editor_height(self) -> None:
        """
        Resize keyword editor to show all keyword lines.
        """

        if not hasattr(
            self,
            "keyword_edit",
        ):
            return

        document = (
            self.keyword_edit.document()
        )

        if document is None:
            return

        block_count = max(
            1,
            document.blockCount(),
        )

        font_metrics = (
            self.keyword_edit.fontMetrics()
        )

        line_height = max(
            18,
            font_metrics.lineSpacing(),
        )

        content_height = (
            block_count
            * line_height
        )

        frame_height = (
            self.keyword_edit.frameWidth()
            * 2
        )

        margins = (
            document.documentMargin()
        )

        padding = int(
            margins * 2
        ) + 18

        calculated_height = (
            content_height
            + frame_height
            + padding
        )

        calculated_height = max(
            48,
            calculated_height,
        )

        self.keyword_edit.setFixedHeight(
            calculated_height
        )

        content = (
            self.keyword_edit.parentWidget()
        )

        if content is not None:
            content.updateGeometry()

    # ========================================================
    # NAME CHANGED
    # ========================================================

    def _name_changed(
        self,
        _text: str,
    ) -> None:
        """
        Update database path while automatic database mode
        is active.
        """

        if self._database_auto:
            self._update_database_path()

        self._update_create_state()

    # ========================================================
    # DATABASE MANUAL EDIT
    # ========================================================

    def _database_manually_edited(
        self,
        text: str,
    ) -> None:
        """
        Disable automatic database generation when manually
        changed.
        """

        text = str(
            text
        ).strip()

        if text != self._last_generated_database:
            self._database_auto = False

        self._update_create_state()

    # ========================================================
    # DATABASE PATH
    # ========================================================

    def _update_database_path(self) -> None:
        """
        Generate default database path from scraper name.
        """

        name = (
            self.name_edit
            .text()
            .strip()
        )

        if not name:

            generated = (
                "runtime/databases/"
                "<scraper_name>.db"
            )

        else:

            generated = str(
                Path(
                    "runtime",
                    "databases",
                    f"{name}.db",
                )
            )

        self._last_generated_database = (
            generated
        )

        self.database_edit.blockSignals(
            True
        )

        self.database_edit.setText(
            generated
        )

        self.database_edit.blockSignals(
            False
        )

    # ========================================================
    # KEYWORD NORMALIZATION
    # ========================================================

    def _get_keywords(self) -> list[str]:
        """
        Return normalized, unique keywords.

        Empty lines are ignored.
        Surrounding whitespace is removed.
        Duplicate keywords are removed case-insensitively.
        Original order is preserved.
        """

        raw = (
            self.keyword_edit
            .toPlainText()
        )

        keywords: list[str] = []

        seen: set[str] = set()

        for line in raw.splitlines():

            keyword = line.strip()

            if not keyword:
                continue

            normalized = keyword.casefold()

            if normalized in seen:
                continue

            seen.add(
                normalized
            )

            keywords.append(
                keyword
            )

        return keywords

    # ========================================================
    # PROVIDER DISCOVERY
    # ========================================================

    def _load_providers(self) -> None:
        """
        Load providers from ProviderManager.

        ProviderManager remains the single source of truth.
        """

        self.providers_list.clear()

        self._providers.clear()

        try:

            manager = ProviderManager()

        except Exception as exc:

            self._set_provider_error(
                f"PROVIDER MANAGER ERROR: {exc}"
            )

            return

        names = self._extract_provider_names(
            manager
        )

        if not names:

            self._set_provider_error(
                "NO PROVIDERS AVAILABLE"
            )

            return

        self._providers = list(
            names
        )

        for name in self._providers:

            item = QListWidgetItem(
                name
            )

            item.setData(
                Qt.UserRole,
                name,
            )

            self.providers_list.addItem(
                item
            )

        self.provider_status.setText(
            f"{len(self._providers)} PROVIDERS"
        )

        if self.providers_list.count() > 0:

            self.providers_list.setCurrentRow(
                0
            )

    # ========================================================
    # PROVIDER NAME EXTRACTION
    # ========================================================

    @staticmethod
    def _extract_provider_names(
        manager: ProviderManager,
    ) -> list[str]:
        """
        Extract provider names exposed by ProviderManager.

        Supported interfaces:

            available_providers
            list_providers
            get_providers
            providers
        """

        candidates = (
            "available_providers",
            "list_providers",
            "get_providers",
            "providers",
        )

        for attribute_name in candidates:

            try:

                if not hasattr(
                    manager,
                    attribute_name,
                ):
                    continue

                source = getattr(
                    manager,
                    attribute_name,
                )

            except Exception:

                continue

            try:

                value = (
                    source()
                    if callable(source)
                    else source
                )

            except Exception:

                continue

            if value is None:
                continue

            if isinstance(
                value,
                dict,
            ):
                value = value.keys()

            try:

                values = list(
                    value
                )

            except (
                TypeError,
                ValueError,
            ):

                continue

            names: list[str] = []

            seen: set[str] = set()

            for item in values:

                if isinstance(
                    item,
                    str,
                ):

                    name = item.strip()

                else:

                    name = getattr(
                        item,
                        "name",
                        None,
                    )

                    if name is None:

                        name = getattr(
                            item,
                            "provider_name",
                            None,
                        )

                    if name is None:
                        continue

                    name = str(
                        name
                    ).strip()

                if not name:
                    continue

                key = name.casefold()

                if key in seen:
                    continue

                seen.add(
                    key
                )

                names.append(
                    name
                )

            if names:

                return sorted(
                    names,
                    key=str.casefold,
                )

        return []

    # ========================================================
    # PROVIDER ERROR
    # ========================================================

    def _set_provider_error(
        self,
        message: str,
    ) -> None:
        """
        Put provider selection into a safe empty state.
        """

        self._providers = []

        self.providers_list.clear()

        self.provider_status.setText(
            message
        )

        self._update_neshan_fields()

        self._update_create_state()

    # ========================================================
    # PROVIDER CHANGED
    # ========================================================

    def _provider_changed(self) -> None:
        """
        React to provider selection.

        Neshan-specific fields become enabled only when the
        selected provider is Neshan.
        """

        provider = (
            self._selected_provider()
        )

        if provider is None:

            self.provider_status.setText(
                "NO PROVIDER"
            )

        else:

            self.provider_status.setText(
                provider.upper()
            )

        self._update_neshan_fields()

        self._update_create_state()

    # ========================================================
    # NESHAN PROVIDER CHECK
    # ========================================================

    def _is_neshan_selected(self) -> bool:
        """
        Return True when the selected provider is Neshan.

        Matching is case-insensitive.
        """

        provider = (
            self._selected_provider()
        )

        if provider is None:
            return False

        return (
            provider.casefold()
            == NESHAN_PROVIDER_KEY
        )

    # ========================================================
    # NESHAN FIELDS STATE
    # ========================================================

    def _update_neshan_fields(self) -> None:
        """
        Enable and show Neshan geographic configuration only
        when Neshan is selected.

        The fields are optional.

        This dialog does NOT attempt to parse the query to
        determine geographic information.
        """

        if not hasattr(
            self,
            "neshan_frame",
        ):
            return

        enabled = (
            self._is_neshan_selected()
        )

        self.neshan_frame.setVisible(
            enabled
        )

        self.neshan_frame.setEnabled(
            enabled
        )

        if not enabled:

            # ------------------------------------------------
            # Keep user-entered Neshan values intact rather
            # than silently destroying them when changing
            # provider.
            #
            # They can therefore be reused if Neshan is
            # selected again.
            # ------------------------------------------------

            pass

    # ========================================================
    # SELECTED PROVIDER
    # ========================================================

    def _selected_provider(
        self,
    ) -> Optional[str]:
        """
        Return the selected provider.
        """

        items = (
            self.providers_list.selectedItems()
        )

        if len(items) != 1:
            return None

        value = items[0].data(
            Qt.UserRole
        )

        if value is None:
            value = items[0].text()

        value = str(
            value
        ).strip()

        if not value:
            return None

        if not any(
            value.casefold()
            == provider.casefold()
            for provider in self._providers
        ):
            return None

        return value

    # ========================================================
    # SCRAPER NAME VALIDATION
    # ========================================================

    def _is_valid_scraper_name(
        self,
        name: str,
    ) -> bool:
        """
        Validate scraper identity.
        """

        if not name:
            return False

        if name in {
            ".",
            "..",
        }:
            return False

        if "/" in name:
            return False

        if "\\" in name:
            return False

        if Path(name).name != name:
            return False

        if name.endswith(
            (
                ".",
                " ",
            )
        ):
            return False

        return True

    # ========================================================
    # FORM VALIDITY
    # ========================================================

    def _is_form_valid(self) -> bool:
        """
        Silent form validation.
        """

        name = (
            self.name_edit
            .text()
            .strip()
        )

        database = (
            self.database_edit
            .text()
            .strip()
        )

        keywords = (
            self._get_keywords()
        )

        provider = (
            self._selected_provider()
        )

        if not (
            self._is_valid_scraper_name(
                name
            )
            and database
            and keywords
            and provider
        ):
            return False

        # ----------------------------------------------------
        # Neshan geographic values are optional.
        #
        # Therefore they must NOT make the form invalid.
        # ----------------------------------------------------

        return True

    # ========================================================
    # CREATE BUTTON STATE
    # ========================================================

    def _update_create_state(
        self,
        *_args,
    ) -> None:
        """
        Enable Create only when minimum valid configuration
        exists.
        """

        if not hasattr(
            self,
            "create_button",
        ):
            return

        self.create_button.setEnabled(
            self._is_form_valid()
        )

    # ========================================================
    # VALIDATION
    # ========================================================

    def _validate(self) -> None:
        """
        Validate the complete configuration and accept.
        """

        name = (
            self.name_edit
            .text()
            .strip()
        )

        keywords = (
            self._get_keywords()
        )

        provider = (
            self._selected_provider()
        )

        database = (
            self.database_edit
            .text()
            .strip()
        )

        # ----------------------------------------------------
        # NAME
        # ----------------------------------------------------

        if not name:

            QMessageBox.warning(
                self,
                "Invalid scraper",
                "Scraper name cannot be empty.",
            )

            self.name_edit.setFocus()

            return

        if not self._is_valid_scraper_name(
            name
        ):

            QMessageBox.warning(
                self,
                "Invalid scraper name",
                (
                    "Scraper name must be a simple "
                    "filesystem-safe identifier and "
                    "cannot contain '/' or '\\'."
                ),
            )

            self.name_edit.setFocus()

            return

        # ----------------------------------------------------
        # KEYWORDS
        # ----------------------------------------------------

        if not keywords:

            QMessageBox.warning(
                self,
                "Invalid keywords",
                "At least one scraper keyword is required.",
            )

            self.keyword_edit.setFocus()

            return

        # ----------------------------------------------------
        # DATABASE
        # ----------------------------------------------------

        if not database:

            QMessageBox.warning(
                self,
                "Invalid database",
                "Database path cannot be empty.",
            )

            self.database_edit.setFocus()

            return

        # ----------------------------------------------------
        # PROVIDER
        # ----------------------------------------------------

        if not provider:

            QMessageBox.warning(
                self,
                "Invalid provider",
                "Please select exactly one search provider.",
            )

            self.providers_list.setFocus()

            return

        self.accept()

    # ========================================================
    # DATA
    # ========================================================

    def data(self) -> dict:
        """
        Return complete scraper configuration.

        Important:

            Neshan geographic information is kept separate
            from the actual query.

        Therefore:

            keyword/query:
                remains untouched

            neshan.province:
                separate field

            neshan.city:
                separate field
        """

        name = (
            self.name_edit
            .text()
            .strip()
        )

        if not self._is_valid_scraper_name(
            name
        ):
            raise ValueError(
                "Invalid scraper name."
            )

        database = (
            self.database_edit
            .text()
            .strip()
        )

        if not database:
            raise ValueError(
                "Database path cannot be empty."
            )

        keywords = (
            self._get_keywords()
        )

        if not keywords:
            raise ValueError(
                "At least one scraper keyword is required."
            )

        provider = (
            self._selected_provider()
        )

        if not provider:
            raise ValueError(
                "Exactly one provider is required."
            )

        keyword = keywords[0]

        target = (
            self.target_edit
            .text()
            .strip()
            or None
        )

        scraper_dir = (
            self.scraper_dir_edit
            .text()
            .strip()
            or None
        )

        # ====================================================
        # NESHAN LOCATION
        # ====================================================

        neshan_province = (
            self.neshan_province_edit
            .text()
            .strip()
            or None
        )

        neshan_city = (
            self.neshan_city_edit
            .text()
            .strip()
            or None
        )

        # ----------------------------------------------------
        # Only meaningful for Neshan.
        #
        # We still return the stable structure so downstream
        # code can rely on the schema.
        # ----------------------------------------------------

        neshan_config = {
            "province":
                neshan_province,

            "city":
                neshan_city,
        }

        # ====================================================
        # CONFIG
        # ====================================================

        config = {

            # ------------------------------------------------
            # PRIMARY KEYWORD
            # ------------------------------------------------

            "keyword":
                keyword,

            # ------------------------------------------------
            # ALL KEYWORDS
            # ------------------------------------------------

            "keywords":
                list(keywords),

            # ------------------------------------------------
            # SEARCH CONFIGURATION
            # ------------------------------------------------

            "max_queries":
                self.max_queries_spin.value(),

            "pages_per_query":
                self.pages_per_query_spin.value(),

            "results_per_page":
                self.results_per_page_spin.value(),

            "delay":
                self.delay_spin.value(),

            "timeout":
                self.timeout_spin.value(),

            # ------------------------------------------------
            # PROVIDER-SPECIFIC CONFIGURATION
            # ------------------------------------------------

            "neshan":
                neshan_config,
        }

        return {

            # ------------------------------------------------
            # IDENTITY
            # ------------------------------------------------

            "name":
                name,

            # ------------------------------------------------
            # PROVIDER
            # ------------------------------------------------

            "providers":
                [provider],

            # ------------------------------------------------
            # PRIMARY KEYWORD
            # ------------------------------------------------

            "keyword":
                keyword,

            # ------------------------------------------------
            # ALL KEYWORDS
            # ------------------------------------------------

            "keywords":
                list(keywords),

            # ------------------------------------------------
            # TARGET
            # ------------------------------------------------

            "target":
                target,

            # ------------------------------------------------
            # DATABASE
            # ------------------------------------------------

            "database":
                database,

            # ------------------------------------------------
            # SCRAPER DIRECTORY
            # ------------------------------------------------

            "scraper_dir":
                scraper_dir,

            # ------------------------------------------------
            # CONFIG
            # ------------------------------------------------

            "config":
                config,
        }

    # ========================================================
    # STYLE
    # ========================================================

    def _apply_style(self) -> None:
        """
        Apply EYES MASTER dark-purple / amber theme.
        """

        self.setStyleSheet(
            f"""

            /* =================================================
               DIALOG
               ================================================= */

            QDialog#NewScraperDialog {{
                background: {BG};
            }}

            QWidget#DialogContent {{
                background: {BG};
            }}


            /* =================================================
               HEADER
               ================================================= */

            QLabel#DialogTitle {{
                color: {AMBER};
                font-size: 27px;
                font-weight: 900;
                letter-spacing: 3px;
            }}

            QLabel#DialogSubtitle {{
                color: {TEXT_MUTED};
                font-size: 11px;
                font-weight: 900;
                letter-spacing: 2px;
            }}


            /* =================================================
               PANELS
               ================================================= */

            QFrame#FormPanel,
            QFrame#ConfigPanel,
            QFrame#NeshanPanel {{
                background: {SURFACE};
                border: 1px solid {BORDER};
                border-radius: 10px;
            }}


            QFrame#NeshanPanel {{
                border-color: {BURGUNDY};
            }}


            /* =================================================
               FORM LABELS
               ================================================= */

            QFormLayout QLabel {{
                color: {TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 900;
                letter-spacing: 0.8px;
            }}

            QLabel#StandaloneLabel {{
                color: {AMBER};
                font-size: 13px;
                font-weight: 900;
                letter-spacing: 1.5px;
            }}

            QLabel#ConfigLabel {{
                color: {TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 900;
                letter-spacing: 0.8px;
                min-width: 150px;
            }}

            QLabel#KeywordHint {{
                color: {TEXT_MUTED};
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 0.8px;
            }}


            /* =================================================
               TEXT INPUT
               ================================================= */

            QLineEdit,
            QPlainTextEdit {{
                background: {SURFACE_2};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 7px;
                padding: 9px 11px;
                min-height: 20px;
                font-size: 12px;
                selection-background-color: {PURPLE};
                selection-color: {TEXT};
            }}

            QLineEdit:hover,
            QPlainTextEdit:hover {{
                border-color: {BORDER_ACTIVE};
            }}

            QLineEdit:focus,
            QPlainTextEdit:focus {{
                border-color: {ORANGE};
                background: {SURFACE_3};
            }}

            QLineEdit#DatabaseEdit {{
                color: {AMBER};
                background: {SURFACE_3};
                font-family: "JetBrains Mono";
            }}

            QPlainTextEdit#KeywordEdit {{
                padding: 10px 12px;
                min-height: 48px;
            }}


            /* =================================================
               NESHAN
               ================================================= */

            QLabel#NeshanTitle {{
                color: {AMBER};
                font-size: 14px;
                font-weight: 900;
                letter-spacing: 1.3px;
            }}

            QLabel#NeshanHint {{
                color: {TEXT_MUTED};
                font-size: 10px;
                font-weight: 900;
                letter-spacing: 1px;
            }}

            QLabel#NeshanDescription {{
                color: {TEXT_MUTED};
                font-size: 10px;
                line-height: 1.4;
            }}

            QLineEdit#NeshanProvinceEdit,
            QLineEdit#NeshanCityEdit {{
                background: {SURFACE_3};
                color: {TEXT};
                border-color: {BURGUNDY};
            }}

            QLineEdit#NeshanProvinceEdit:focus,
            QLineEdit#NeshanCityEdit:focus {{
                border-color: {ORANGE};
            }}


            /* =================================================
               SPIN BOX
               ================================================= */

            QSpinBox {{
                background: {SURFACE_2};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 7px;
                padding: 8px 10px;
                min-width: 120px;
                min-height: 24px;
                font-size: 12px;
            }}

            QSpinBox:hover {{
                border-color: {BORDER_ACTIVE};
            }}

            QSpinBox:focus {{
                border-color: {ORANGE};
                background: {SURFACE_3};
            }}

            QSpinBox::up-button,
            QSpinBox::down-button {{
                background: {SURFACE_3};
                border: none;
                width: 22px;
            }}

            QSpinBox::up-button:hover,
            QSpinBox::down-button:hover {{
                background: {BURGUNDY};
            }}


            /* =================================================
               PROVIDER SEPARATOR
               ================================================= */

            QFrame#ProviderSeparator {{
                background: {BORDER};
                max-height: 1px;
                border: none;
            }}


            /* =================================================
               PROVIDER HEADER
               ================================================= */

            QLabel#ProviderTitle {{
                color: {AMBER};
                font-size: 15px;
                font-weight: 900;
                letter-spacing: 1.5px;
            }}

            QLabel#ProviderHint {{
                color: {TEXT_MUTED};
                font-size: 11px;
            }}

            QLabel#ProviderStatus {{
                color: {GREEN};
                font-size: 10px;
                font-weight: 900;
                letter-spacing: 1px;
            }}


            /* =================================================
               PROVIDER LIST
               ================================================= */

            QListWidget#ProvidersList {{
                background: {SURFACE_2};
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 7px;
                outline: none;
            }}

            QListWidget#ProvidersList::item {{
                background: transparent;
                color: {TEXT_SECONDARY};
                border-radius: 6px;
                padding: 12px 13px;
                margin: 2px 0px;
                font-size: 12px;
                font-weight: 800;
            }}

            QListWidget#ProvidersList::item:hover {{
                background: {SURFACE_3};
                color: {TEXT};
            }}

            QListWidget#ProvidersList::item:selected {{
                background: {PURPLE};
                color: {AMBER};
                border: 1px solid {ORANGE};
            }}


            /* =================================================
               BUTTONS
               ================================================= */

            QDialogButtonBox {{
                background: transparent;
            }}

            QPushButton {{
                background: {SURFACE_2};
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER};
                border-radius: 7px;
                padding: 11px 18px;
                min-width: 95px;
                min-height: 20px;
                font-size: 11px;
                font-weight: 900;
            }}

            QPushButton:hover {{
                color: {AMBER};
                border-color: {ORANGE};
                background: {SURFACE_3};
            }}

            QPushButton:pressed {{
                background: {BURGUNDY};
            }}

            QPushButton:disabled {{
                background: {SURFACE};
                color: {TEXT_MUTED};
                border-color: {BORDER};
            }}

            QPushButton#CreateButton {{
                background: {AMBER};
                color: {BG};
                border-color: {AMBER};
                min-width: 155px;
            }}

            QPushButton#CreateButton:hover {{
                background: {ORANGE};
                border-color: {ORANGE};
                color: {BG};
            }}

            QPushButton#CreateButton:pressed {{
                background: {DEEP_ORANGE};
                border-color: {DEEP_ORANGE};
                color: {TEXT};
            }}


            /* =================================================
               SCROLL AREA
               ================================================= */

            QScrollArea {{
                background: {BG};
                border: none;
            }}

            QScrollBar:vertical {{
                background: {SURFACE};
                width: 10px;
                border: none;
                margin: 2px;
            }}

            QScrollBar::handle:vertical {{
                background: {BORDER};
                border-radius: 5px;
                min-height: 35px;
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
                height: 0px;
            }}

            """
        )