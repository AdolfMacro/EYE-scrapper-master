# tools/map_view.py

from __future__ import annotations

import json
import math
import html

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
)

from PyQt5.QtWebEngineWidgets import QWebEngineView


# ==========================================================
# MAP WINDOW
# ==========================================================

class MapWindow(QDialog):
    """
    Display selected Data Manager rows on OpenStreetMap.

    Only rows containing valid latitude / longitude values
    are displayed.

    Expected row format:

        {
            "name": "School A",
            "city": "Tabriz",
            "latitude": 38.0962,
            "longitude": 46.2738,
            ...
        }
    """

    LATITUDE_FIELDS = (
        "latitude",
        "lat",
        "Latitude",
        "LATITUDE",
    )

    LONGITUDE_FIELDS = (
        "longitude",
        "lon",
        "lng",
        "long",
        "Longitude",
        "LONGITUDE",
    )

    def __init__(
        self,
        rows,
        parent=None,
    ):

        super().__init__(parent)

        self.rows = rows or []

        self.map_rows = []

        self.setWindowTitle(
            "EYE SCRAPPER — MAP VIEW"
        )

        self.resize(
            1200,
            800
        )

        self.setMinimumSize(
            900,
            600
        )

        self.build_ui()

        self.prepare_rows()

        self.load_map()

    # ======================================================
    # UI
    # ======================================================

    def build_ui(self):

        layout = QVBoxLayout()

        layout.setContentsMargins(
            12,
            12,
            12,
            12
        )

        layout.setSpacing(
            8
        )

        self.setLayout(
            layout
        )

        # --------------------------------------------------
        # HEADER
        # --------------------------------------------------

        header = QHBoxLayout()

        title = QLabel(
            "MAP VIEW"
        )

        title.setStyleSheet(
            """
            QLabel {
                font-size: 18px;
                font-weight: bold;
            }
            """
        )

        header.addWidget(
            title
        )

        header.addStretch()

        self.counter = QLabel(
            "LOCATIONS: 0"
        )

        self.counter.setStyleSheet(
            """
            QLabel {
                font-size: 13px;
                font-weight: bold;
            }
            """
        )

        header.addWidget(
            self.counter
        )

        refresh_button = QPushButton(
            "REFRESH"
        )

        refresh_button.clicked.connect(
            self.refresh_map
        )

        header.addWidget(
            refresh_button
        )

        close_button = QPushButton(
            "CLOSE"
        )

        close_button.clicked.connect(
            self.close
        )

        header.addWidget(
            close_button
        )

        layout.addLayout(
            header
        )

        # --------------------------------------------------
        # WEB VIEW
        # --------------------------------------------------

        self.web_view = QWebEngineView()

        layout.addWidget(
            self.web_view
        )

    # ======================================================
    # PREPARE ROWS
    # ======================================================

    def prepare_rows(self):

        self.map_rows = []

        for row in self.rows:

            if not isinstance(row, dict):
                continue

            latitude = self.get_field(
                row,
                self.LATITUDE_FIELDS
            )

            longitude = self.get_field(
                row,
                self.LONGITUDE_FIELDS
            )

            coordinates = self.parse_coordinates(
                latitude,
                longitude
            )

            if coordinates is None:
                continue

            lat, lon = coordinates

            marker = {
                "latitude": lat,
                "longitude": lon,
                "data": self.clean_row(
                    row
                )
            }

            self.map_rows.append(
                marker
            )

        self.counter.setText(
            f"LOCATIONS: {len(self.map_rows):,}"
        )

    # ======================================================
    # FIELD LOOKUP
    # ======================================================

    @staticmethod
    def get_field(
        row,
        candidates
    ):

        normalized = {
            str(key).strip().lower(): value
            for key, value in row.items()
        }

        for candidate in candidates:

            value = normalized.get(
                candidate.lower()
            )

            if value is not None:
                return value

        return None

    # ======================================================
    # COORDINATE PARSER
    # ======================================================

    @staticmethod
    def parse_coordinates(
        latitude,
        longitude
    ):

        try:

            if latitude is None:
                return None

            if longitude is None:
                return None

            lat_text = str(
                latitude
            ).strip()

            lon_text = str(
                longitude
            ).strip()

            if not lat_text or not lon_text:
                return None

            lat = float(
                lat_text
            )

            lon = float(
                lon_text
            )

            if not math.isfinite(lat):
                return None

            if not math.isfinite(lon):
                return None

            if not (
                -90 <= lat <= 90
            ):
                return None

            if not (
                -180 <= lon <= 180
            ):
                return None

            return lat, lon

        except (
            TypeError,
            ValueError
        ):

            return None

    # ======================================================
    # CLEAN DATA
    # ======================================================

    @staticmethod
    def clean_row(
        row
    ):

        result = {}

        for key, value in row.items():

            if value is None:
                continue

            text = str(
                value
            ).strip()

            if not text:
                continue

            result[str(key)] = text

        return result

    # ======================================================
    # MAP HTML
    # ======================================================

    def build_html(self):

        markers_json = json.dumps(
            self.map_rows,
            ensure_ascii=False
        )

        html_content = """
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>EYE MAP</title>

<link
    rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
/>

<style>

html,
body,
#map {
    width: 100%;
    height: 100%;
    margin: 0;
    padding: 0;
}

body {
    overflow: hidden;
    font-family: Arial, sans-serif;
}

.popup {
    min-width: 220px;
    max-width: 350px;
}

.popup-title {
    font-size: 15px;
    font-weight: bold;
    margin-bottom: 8px;
}

.popup-row {
    margin: 3px 0;
    word-break: break-word;
}

.popup-key {
    font-weight: bold;
}

.empty {
    position: absolute;
    z-index: 9999;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: white;
    padding: 20px 28px;
    border-radius: 8px;
    box-shadow: 0 3px 15px rgba(0,0,0,.25);
    font-family: Arial, sans-serif;
}

</style>

</head>

<body>

<div id="map"></div>

<script
    src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js">
</script>

<script>

const records = __MARKERS_JSON__;

let map;

function escapeHtml(value) {

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function buildPopup(data) {

    const keys = Object.keys(data);

    let popupHtml =
        '<div class="popup">';

    let title = null;

    const titleFields = [
        "name",
        "school_name",
        "title",
        "NAME",
        "School Name"
    ];

    for (const field of titleFields) {

        if (
            data[field] !== undefined &&
            data[field] !== null &&
            String(data[field]).trim() !== ""
        ) {

            title = data[field];

            break;
        }
    }

    if (title) {

        popupHtml +=
            '<div class="popup-title">' +
            escapeHtml(title) +
            '</div>';

    }

    for (const key of keys) {

        if (
            key === "latitude" ||
            key === "longitude"
        ) {
            continue;
        }

        const value = data[key];

        if (
            value === null ||
            value === undefined ||
            String(value).trim() === ""
        ) {
            continue;
        }

        popupHtml +=
            '<div class="popup-row">' +
            '<span class="popup-key">' +
            escapeHtml(key) +
            ':</span> ' +
            escapeHtml(value) +
            '</div>';
    }

    popupHtml += '</div>';

    return popupHtml;
}

function initMap() {

    map = L.map(
        "map",
        {
            zoomControl: true
        }
    );

    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            maxZoom: 19,
            attribution:
                '&copy; OpenStreetMap contributors'
        }
    ).addTo(map);

    if (!records.length) {

        map.setView(
            [32.0, 53.0],
            5
        );

        const message =
            document.createElement("div");

        message.className = "empty";

        message.innerText =
            "No records with valid coordinates.";

        document.body.appendChild(
            message
        );

        return;
    }

    const bounds = [];

    records.forEach(
        function(record) {

            const lat =
                record.latitude;

            const lon =
                record.longitude;

            const marker =
                L.marker(
                    [lat, lon]
                ).addTo(map);

            marker.bindPopup(
                buildPopup(
                    record.data
                )
            );

            bounds.push(
                [lat, lon]
            );
        }
    );

    if (bounds.length === 1) {

        map.setView(
            bounds[0],
            15
        );

    } else {

        map.fitBounds(
            bounds,
            {
                padding: [40, 40]
            }
        );
    }
}

initMap();

</script>

</body>

</html>
"""

        html_content = html_content.replace(
            "__MARKERS_JSON__",
            markers_json
        )

        return html_content

    # ======================================================
    # LOAD MAP
    # ======================================================

    def load_map(self):

        html_content = self.build_html()

        self.web_view.setHtml(
            html_content,
            QUrl(
                "https://localhost/"
            )
        )

    # ======================================================
    # REFRESH
    # ======================================================

    def refresh_map(self):

        self.prepare_rows()

        self.load_map()


# ==========================================================
# SIMPLE HELPER
# ==========================================================

def open_map(
    rows,
    parent=None
):

    window = MapWindow(
        rows,
        parent
    )

    window.exec_()


# ==========================================================
# TEST
# ==========================================================

if __name__ == "__main__":

    import sys

    from PyQt5.QtWidgets import QApplication

    app = QApplication(
        sys.argv
    )

    test_rows = [

        {
            "name": "School A",
            "city": "Tabriz",
            "latitude": 38.0962,
            "longitude": 46.2738,
            "phone": "04100000000",
        },

        {
            "name": "School B",
            "city": "Tehran",
            "latitude": 35.6892,
            "longitude": 51.3890,
            "phone": "02100000000",
        },

        {
            "name": "Without Coordinates",
            "city": "Unknown",
            "phone": "00000000000",
        },

    ]

    window = MapWindow(
        test_rows
    )

    window.show()

    sys.exit(
        app.exec_()
    )
