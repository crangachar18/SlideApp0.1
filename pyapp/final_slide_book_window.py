from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyapp.database import (
    get_user_storage_locations,
    remember_user_storage_location,
    save_experiment_payload,
)


@dataclass(frozen=True)
class SlideBookRow:
    slide_id: str
    primary_set: str
    primary_mm: str
    secondary_set: str
    secondary_mm: str


class FinalSlideBookWindow(QMainWindow):
    def __init__(self, username: str, rows: list[SlideBookRow], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.username = username
        self.rows = rows
        self.table: QTableWidget | None = None
        self.done_button: QPushButton | None = None
        self.status_label: QLabel | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle("SlideApp - Final Slide Book")
        self.resize(1460, 900)
        self.setMinimumSize(1120, 720)

        central = QWidget(self)
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        title = QLabel("Final Slide Book", self)
        title.setObjectName("title")
        root.addWidget(title)

        subtitle = QLabel("Review slide identities and add storage/planned-use notes.", self)
        subtitle.setObjectName("subtitle")
        root.addWidget(subtitle)

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
        self.table.setRowCount(len(self.rows))
        storage_suggestions = get_user_storage_locations(self.username)
        if not storage_suggestions:
            storage_suggestions = ["cold room-bottom drawer"]

        for row_idx, r in enumerate(self.rows):
            self.table.setItem(row_idx, 0, QTableWidgetItem(r.slide_id))
            self.table.setItem(row_idx, 1, QTableWidgetItem(r.primary_set))
            self.table.setItem(row_idx, 2, QTableWidgetItem(r.primary_mm))
            self.table.setItem(row_idx, 3, QTableWidgetItem(r.secondary_set))
            self.table.setItem(row_idx, 4, QTableWidgetItem(r.secondary_mm))
            storage_combo = QComboBox(self)
            storage_combo.setEditable(True)
            storage_combo.addItems(storage_suggestions)
            self.table.setCellWidget(row_idx, 5, storage_combo)
            self.table.setCellWidget(row_idx, 6, QLineEdit(self))

        self.table.resizeColumnsToContents()
        root.addWidget(self.table, 1)

        self.status_label = QLabel("", self)
        self.status_label.setObjectName("statusLabel")
        root.addWidget(self.status_label)

        self.done_button = QPushButton("Done", self)
        self.done_button.clicked.connect(self._handle_done)
        root.addWidget(self.done_button)

        self.setStyleSheet(
            "QMainWindow { background: #efefef; }"
            "QLabel#title { font-size: 36px; font-weight: 700; color: #111111; }"
            "QLabel#subtitle { font-size: 18px; color: #333333; }"
            "QTableWidget { background: #ffffff; color: #111111; font-size: 15px; }"
            "QHeaderView::section { background: #e7e7e7; color: #111111; font-size: 16px; padding: 6px; border: none; }"
            "QLineEdit { min-height: 32px; padding: 3px 6px; }"
            "QComboBox { min-height: 32px; padding: 3px 6px; }"
            "QLabel#statusLabel { color: #333333; font-size: 14px; min-height: 24px; }"
            "QPushButton { background: #111111; color: #f5f5f5; border: none; border-radius: 10px; padding: 10px 14px; font-size: 18px; }"
        )

    def _handle_done(self) -> None:
        if self.table is None or self.done_button is None:
            return

        slides: list[dict[str, str]] = []
        for row in range(self.table.rowCount()):
            slide_id_item = self.table.item(row, 0)
            primary_set_item = self.table.item(row, 1)
            primary_mm_item = self.table.item(row, 2)
            secondary_set_item = self.table.item(row, 3)
            secondary_mm_item = self.table.item(row, 4)

            storage_widget = self.table.cellWidget(row, 5)
            storage = ""
            if isinstance(storage_widget, QComboBox):
                storage = storage_widget.currentText().strip()
                if storage:
                    remember_user_storage_location(self.username, storage)

            planned_widget = self.table.cellWidget(row, 6)
            planned_use = planned_widget.text().strip() if isinstance(planned_widget, QLineEdit) else ""

            slides.append(
                {
                    "slide_id": slide_id_item.text().strip() if slide_id_item else "",
                    "primary_set": primary_set_item.text().strip() if primary_set_item else "",
                    "primary_mm": primary_mm_item.text().strip() if primary_mm_item else "",
                    "secondary_set": secondary_set_item.text().strip() if secondary_set_item else "",
                    "secondary_mm": secondary_mm_item.text().strip() if secondary_mm_item else "",
                    "storage_location": storage,
                    "planned_use": planned_use,
                }
            )

        payload = {
            "username": self.username,
            "stage": "final_slide_book",
            "slides": slides,
        }
        run_id, json_path = save_experiment_payload(self.username, payload)

        QMessageBox.information(
            self,
            "Experiment Saved",
            f"Saved experiment run {run_id[:8]}.\nJSON: {json_path}",
        )
        self.close()
