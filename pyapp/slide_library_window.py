from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyapp.database import list_experiment_runs


class SlideLibraryWindow(QMainWindow):
    def __init__(self, username: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.username = username
        self.run_selector: QComboBox | None = None
        self.table: QTableWidget | None = None
        self.runs: list[dict[str, str]] = []
        self._build_ui()
        self._load_runs()

    def _build_ui(self) -> None:
        self.setWindowTitle("SlideApp - Slibrary")
        self.resize(1450, 900)
        self.setMinimumSize(1080, 700)

        central = QWidget(self)
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        title = QLabel("The Slibrary", self)
        title.setObjectName("title")
        root.addWidget(title)

        header = QHBoxLayout()
        header.addWidget(QLabel("Experiment Run:", self))
        self.run_selector = QComboBox(self)
        self.run_selector.currentIndexChanged.connect(self._on_run_changed)
        header.addWidget(self.run_selector, 1)
        root.addLayout(header)

        self.table = QTableWidget(self)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            [
                "Slide ID",
                "Primary Set",
                "Primary MM",
                "Secondary Set",
                "Secondary MM",
                "Storage Location",
                "Planned Use",
            ]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table, 1)

        self.setStyleSheet(
            "QMainWindow { background: #efefef; }"
            "QLabel#title { font-size: 38px; font-weight: 700; color: #111111; }"
            "QLabel { font-size: 18px; color: #1b1b1b; }"
            "QComboBox { min-height: 34px; font-size: 16px; padding: 4px 8px; }"
            "QTableWidget { background: #ffffff; color: #111111; font-size: 15px; }"
            "QHeaderView::section { background: #e7e7e7; color: #111111; font-size: 16px; padding: 6px; border: none; }"
        )

    def _load_runs(self) -> None:
        if self.run_selector is None:
            return

        self.runs = list_experiment_runs(self.username)
        self.run_selector.clear()

        if not self.runs:
            self.run_selector.addItem("No saved runs")
            self._populate_table([])
            return

        for run in self.runs:
            run_id = run["run_id"][:8]
            created = run["created_at"]
            self.run_selector.addItem(f"{created}  ({run_id})")

        self._on_run_changed(0)

    def _on_run_changed(self, index: int) -> None:
        if index < 0 or index >= len(self.runs):
            self._populate_table([])
            return

        payload_json = self.runs[index].get("payload_json", "{}")
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError:
            self._populate_table([])
            return

        slides = payload.get("slides", []) if isinstance(payload, dict) else []
        if not isinstance(slides, list):
            slides = []
        self._populate_table(slides)

    def _populate_table(self, slides: list[object]) -> None:
        if self.table is None:
            return

        self.table.setRowCount(len(slides))

        for row_idx, raw in enumerate(slides):
            slide = raw if isinstance(raw, dict) else {}
            values = [
                str(slide.get("slide_id", "")),
                str(slide.get("primary_set", "")),
                str(slide.get("primary_mm", "")),
                str(slide.get("secondary_set", "")),
                str(slide.get("secondary_mm", "")),
                str(slide.get("storage_location", "")),
                str(slide.get("planned_use", "")),
            ]
            for col_idx, value in enumerate(values):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(value))

        self.table.resizeColumnsToContents()
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
