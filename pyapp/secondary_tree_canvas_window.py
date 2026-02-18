from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyapp.antibody_rules import PrimaryAntibody
from pyapp.secondary_rules import (
    SecondaryAntibody,
    load_secondaries,
    secondary_is_compatible,
    suggest_secondary_by_channel,
)
from pyapp.secondary_master_mix_window import SecondaryMasterMixWindow, SecondaryMixEntry
from pyapp.final_slide_book_window import FinalSlideBookWindow, SlideBookRow


@dataclass(frozen=True)
class SlideRow:
    group_index: int
    slide_index: int


class SecondaryTreeCanvasWindow(QMainWindow):
    def __init__(
        self,
        username: str,
        mode: str,
        group_slide_counts: list[int],
        edu_enabled: bool,
        primary_per_slide: dict[tuple[int, int], list[str]],
        primary_mm_per_slide: dict[tuple[int, int], str],
        primary_by_name: dict[str, PrimaryAntibody],
        secondary_volume_ul: float,
        secondary_incubation_method: str,
        experiment_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.username = username
        self.mode = mode
        self.group_slide_counts = group_slide_counts
        self.edu_enabled = edu_enabled
        self.primary_per_slide = primary_per_slide
        self.primary_mm_per_slide = primary_mm_per_slide
        self.primary_by_name = primary_by_name
        self.secondary_volume_ul = secondary_volume_ul
        self.secondary_incubation_method = secondary_incubation_method
        self.experiment_name = experiment_name

        self.secondaries = self._load_secondaries()
        self.secondary_by_name = {s.name: s for s in self.secondaries}

        self.scene: QGraphicsScene | None = None
        self.table: QTableWidget | None = None
        self.status_label: QLabel | None = None
        self.set_secondary_mixes_button: QPushButton | None = None
        self.slide_rows: list[SlideRow] = []
        self.secondary_mix_window: SecondaryMasterMixWindow | None = None
        self.final_slide_book_window: FinalSlideBookWindow | None = None
        self.secondary_mm_per_slide: dict[tuple[int, int], str] = {}

        self.channel_columns = ["A488", "Cy3", "A647"]

        self._build_ui()
        self._draw_tree()
        self._populate_table()

    def _load_secondaries(self) -> list[SecondaryAntibody]:
        root = Path(__file__).resolve().parent
        candidates = [
            root / "secondaries.csv",
            root / "secondaries - Sheet1.csv",
        ]
        for c in candidates:
            if c.exists():
                return load_secondaries(c)
        return []

    def _build_ui(self) -> None:
        self.setWindowTitle("SlideApp - Secondary Tree Canvas")
        self.resize(1520, 920)
        self.setMinimumSize(1240, 760)

        central = QWidget(self)
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(10)

        header = QLabel(f"{self.experiment_name} / Secondary Tree Canvas", self)
        header.setObjectName("headerLabel")
        root.addWidget(header)

        split = QHBoxLayout()
        split.setSpacing(18)

        view = QGraphicsView(self)
        self.scene = QGraphicsScene(self)
        view.setScene(self.scene)
        view.setObjectName("treeView")
        split.addWidget(view, 1)

        right = QVBoxLayout()
        right.setSpacing(10)

        self.table = QTableWidget(self)
        self.table.setObjectName("slideTable")
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "A488", "Cy3", "A647"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setAlternatingRowColors(True)
        right.addWidget(self.table, 1)

        actions = QHBoxLayout()
        magic = QPushButton("🪄 Auto Compatible", self)
        magic.clicked.connect(self._auto_fill_secondaries)
        actions.addWidget(magic)
        actions.addStretch()
        self.set_secondary_mixes_button = QPushButton("Set Secondary Master Mixes", self)
        self.set_secondary_mixes_button.setEnabled(False)
        self.set_secondary_mixes_button.clicked.connect(self._set_secondary_master_mixes)
        actions.addWidget(self.set_secondary_mixes_button)
        right.addLayout(actions)

        self.status_label = QLabel("", self)
        self.status_label.setObjectName("statusLabel")
        right.addWidget(self.status_label)

        split.addLayout(right, 1)
        root.addLayout(split, 1)

        self.setStyleSheet(
            "QMainWindow { background: #dcdcdc; }"
            "QLabel#headerLabel { font-family: 'Helvetica Neue'; font-size: 42px; font-weight: 700; color: #111111; }"
            "QGraphicsView#treeView { background: #dcdcdc; border: none; }"
            "QTableWidget#slideTable { background: #f2f2f2; color: #111111; font-size: 18px; gridline-color: #c6c6c6; }"
            "QHeaderView::section { background: #e7e7e7; color: #111111; font-size: 22px; padding: 6px; border: none; }"
            "QPushButton { background: #111111; color: #f5f5f5; border: none; border-radius: 10px; padding: 10px 14px; font-size: 18px; }"
            "QLabel#statusLabel { color: #8b0000; font-size: 16px; min-height: 24px; }"
        )

    def _draw_tree(self) -> None:
        if self.scene is None:
            return

        self.scene.clear()
        brush = QBrush(QColor("#c8c8c8"))
        pen = QPen(QColor("#2f2f2f"))

        ex_x, ex_y = 40, 280
        ex_w, ex_h = 150, 56
        ex_box = QGraphicsRectItem(ex_x, ex_y, ex_w, ex_h)
        ex_box.setPen(pen)
        ex_box.setBrush(brush)
        self.scene.addItem(ex_box)
        ex_text = QGraphicsSimpleTextItem("Experiment")
        ex_text.setPos(ex_x + 24, ex_y + 18)
        self.scene.addItem(ex_text)

        group_x = 300
        slide_x = 550
        slide_gap = 70
        group_top = 70
        group_block_padding = 36

        for g_idx, slide_count in enumerate(self.group_slide_counts):
            group_y = group_top
            g_box = QGraphicsRectItem(group_x, group_y, 180, 56)
            g_box.setPen(pen)
            g_box.setBrush(brush)
            self.scene.addItem(g_box)
            g_text = QGraphicsSimpleTextItem(f"Group {g_idx + 1}")
            g_text.setPos(group_x + 46, group_y + 18)
            self.scene.addItem(g_text)

            self.scene.addLine(ex_x + ex_w, ex_y + ex_h / 2, group_x, group_y + 28, pen)

            for s_idx in range(slide_count):
                y = group_y + (s_idx * slide_gap)
                s_box = QGraphicsRectItem(slide_x, y, 170, 46)
                s_box.setPen(pen)
                s_box.setBrush(brush)
                self.scene.addItem(s_box)
                s_text = QGraphicsSimpleTextItem(f"Slide {g_idx + 1}-{s_idx + 1}")
                s_text.setPos(slide_x + 24, y + 13)
                self.scene.addItem(s_text)
                self.scene.addLine(group_x + 180, group_y + 28, slide_x, y + 23, pen)

            slide_block_height = max(56, (slide_count - 1) * slide_gap + 46)
            group_top += slide_block_height + group_block_padding

        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-30, -30, 40, 40))

    def _populate_table(self) -> None:
        if self.table is None:
            return

        self.slide_rows.clear()
        for g_idx, count in enumerate(self.group_slide_counts):
            for s_idx in range(count):
                self.slide_rows.append(SlideRow(group_index=g_idx, slide_index=s_idx))

        self.table.setRowCount(len(self.slide_rows))
        options = ["None", *[s.name for s in self.secondaries]]

        for row_idx, slide in enumerate(self.slide_rows):
            slide_id = f"G{slide.group_index + 1}-S{slide.slide_index + 1}"
            self.table.setItem(row_idx, 0, QTableWidgetItem(slide_id))

            for col_idx, col_name in enumerate(self.channel_columns, start=1):
                if self.edu_enabled and col_name.upper() == "A647":
                    item = QTableWidgetItem("EdU")
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row_idx, col_idx, item)
                    continue

                combo = QComboBox(self)
                combo.addItems(options)
                combo.currentIndexChanged.connect(lambda _i, r=row_idx: self._validate_row(r))
                combo.currentIndexChanged.connect(self._update_set_button_state)
                self.table.setCellWidget(row_idx, col_idx, combo)

        self.table.resizeColumnsToContents()
        self._update_set_button_state()

    def _get_primary_set_for_row(self, row: int) -> list[PrimaryAntibody]:
        slide = self.slide_rows[row]
        names = self.primary_per_slide.get((slide.group_index, slide.slide_index), [])
        out: list[PrimaryAntibody] = []
        for n in names:
            p = self.primary_by_name.get(n)
            if p is not None:
                out.append(p)
        return out

    def _get_selected_secondary_for_channel(self, row: int, channel: str) -> SecondaryAntibody | None:
        if self.table is None:
            return None
        col = {"A488": 1, "CY3": 2, "A647": 3}[channel.upper()]
        combo = self.table.cellWidget(row, col)
        if not isinstance(combo, QComboBox):
            return None
        name = combo.currentText().strip()
        if not name or name == "None":
            return None
        for sec in self.secondaries:
            if sec.name == name:
                return sec
        return None

    def _validate_row(self, row: int) -> None:
        if self.table is None or self.status_label is None:
            return

        primary_set = self._get_primary_set_for_row(row)
        selected: list[SecondaryAntibody] = []
        ok = True

        for channel in ["A488", "Cy3", "A647"]:
            sec = self._get_selected_secondary_for_channel(row, channel)
            if sec is None:
                continue
            if not secondary_is_compatible(sec, selected, primary_set):
                ok = False
            selected.append(sec)

        for channel in ["A488", "Cy3", "A647"]:
            col = {"A488": 1, "CY3": 2, "A647": 3}[channel.upper()]
            widget = self.table.cellWidget(row, col)
            if isinstance(widget, QComboBox):
                widget.setStyleSheet("background: #f2f2f2;" if ok else "background: #ffd8d8;")

        if not ok:
            self.status_label.setText(
                "Invalid secondary set: host incompatibility or duplicate anti-target detected."
            )
        else:
            self.status_label.setText("")
        self._update_set_button_state()

    def _auto_fill_secondaries(self) -> None:
        if self.table is None:
            return

        for row in range(self.table.rowCount()):
            primary_set = self._get_primary_set_for_row(row)
            channels = ["A488", "Cy3"] if self.edu_enabled else ["A488", "Cy3", "A647"]
            suggestion = suggest_secondary_by_channel(channels, self.secondaries, primary_set)

            for channel in channels:
                col = {"A488": 1, "CY3": 2, "A647": 3}[channel.upper()]
                combo = self.table.cellWidget(row, col)
                if isinstance(combo, QComboBox):
                    combo.setCurrentText(suggestion.get(channel, "None"))

            self._validate_row(row)
        self._update_set_button_state()

    def _all_required_secondaries_selected(self) -> bool:
        if self.table is None:
            return False

        required_channels = ["A488", "Cy3"] if self.edu_enabled else ["A488", "Cy3", "A647"]
        for row in range(self.table.rowCount()):
            for channel in required_channels:
                col = {"A488": 1, "CY3": 2, "A647": 3}[channel.upper()]
                combo = self.table.cellWidget(row, col)
                if not isinstance(combo, QComboBox):
                    return False
                if combo.currentText().strip() in {"", "None"}:
                    return False
        return True

    def _row_is_valid(self, row: int) -> bool:
        if self.table is None:
            return False
        primary_set = self._get_primary_set_for_row(row)
        selected: list[SecondaryAntibody] = []
        for channel in ["A488", "Cy3", "A647"]:
            sec = self._get_selected_secondary_for_channel(row, channel)
            if sec is None:
                continue
            if not secondary_is_compatible(sec, selected, primary_set):
                return False
            selected.append(sec)
        return True

    def _update_set_button_state(self) -> None:
        if self.set_secondary_mixes_button is None or self.table is None:
            return
        all_selected = self._all_required_secondaries_selected()
        all_valid = all(self._row_is_valid(row) for row in range(self.table.rowCount()))
        self.set_secondary_mixes_button.setEnabled(all_selected and all_valid)

    def _set_secondary_master_mixes(self) -> None:
        if self.table is None or self.status_label is None:
            return

        required_channels = ["A488", "Cy3"] if self.edu_enabled else ["A488", "Cy3", "A647"]
        grouped: dict[tuple[str, ...], int] = {}
        mix_entries: list[SecondaryMixEntry] = []

        for row in range(self.table.rowCount()):
            key: list[str] = []
            for channel in required_channels:
                col = {"A488": 1, "CY3": 2, "A647": 3}[channel.upper()]
                combo = self.table.cellWidget(row, col)
                value = combo.currentText().strip() if isinstance(combo, QComboBox) else "None"
                key.append(value)
            grouped[tuple(key)] = grouped.get(tuple(key), 0) + 1

        for idx, key in enumerate(sorted(grouped.keys()), start=1):
            mix_id = f"SMM{idx}"
            channel_to_secondary: dict[str, str] = {}
            channel_to_fraction: dict[str, str] = {}
            for pos, channel in enumerate(required_channels):
                sec_name = key[pos]
                if not sec_name or sec_name == "None":
                    continue
                channel_to_secondary[channel] = sec_name
                sec_obj = self.secondary_by_name.get(sec_name)
                channel_to_fraction[channel] = sec_obj.concentration_text if sec_obj is not None else ""
            mix_entries.append(
                SecondaryMixEntry(
                    mix_id=mix_id,
                    slide_count=grouped[key],
                    channel_to_secondary=channel_to_secondary,
                    channel_to_fraction=channel_to_fraction,
                )
            )
            for row in range(self.table.rowCount()):
                row_key: list[str] = []
                for channel in required_channels:
                    col = {"A488": 1, "CY3": 2, "A647": 3}[channel.upper()]
                    combo = self.table.cellWidget(row, col)
                    row_key.append(combo.currentText().strip() if isinstance(combo, QComboBox) else "None")
                if tuple(row_key) == key:
                    slide = self.slide_rows[row]
                    self.secondary_mm_per_slide[(slide.group_index, slide.slide_index)] = mix_id

        self.secondary_mix_window = SecondaryMasterMixWindow(
            mixes=mix_entries,
            total_slide_count=len(self.slide_rows),
            secondary_volume_ul=self.secondary_volume_ul,
            secondary_incubation_method=self.secondary_incubation_method,
            edu_enabled=self.edu_enabled,
            on_continue=self._open_final_slide_book,
            parent=self,
        )
        self.secondary_mix_window.show()

        self.status_label.setText(
            f"Secondary master mixes set: {len(grouped)} groups across {self.table.rowCount()} slides."
        )

    def _open_final_slide_book(self) -> None:
        if self.table is None:
            return

        rows: list[SlideBookRow] = []
        for row_idx, slide in enumerate(self.slide_rows):
            key = (slide.group_index, slide.slide_index)
            slide_id = f"G{slide.group_index + 1}-S{slide.slide_index + 1}"
            primary_names = self.primary_per_slide.get(key, [])
            primary_set = ", ".join(primary_names) if primary_names else "-"
            primary_mm = self.primary_mm_per_slide.get(key, "")

            secondary_names: list[str] = []
            for channel in ["A488", "Cy3", "A647"]:
                col = {"A488": 1, "CY3": 2, "A647": 3}[channel.upper()]
                item = self.table.item(row_idx, col)
                if item is not None and item.text().strip():
                    secondary_names.append(f"{channel}:{item.text().strip()}")
                    continue
                combo = self.table.cellWidget(row_idx, col)
                if isinstance(combo, QComboBox):
                    val = combo.currentText().strip()
                    if val and val != "None":
                        secondary_names.append(f"{channel}:{val}")
            secondary_set = ", ".join(secondary_names) if secondary_names else "-"
            secondary_mm = self.secondary_mm_per_slide.get(key, "")

            rows.append(
                SlideBookRow(
                    slide_id=slide_id,
                    primary_set=primary_set,
                    primary_mm=primary_mm,
                    secondary_set=secondary_set,
                    secondary_mm=secondary_mm,
                )
            )

        self.final_slide_book_window = FinalSlideBookWindow(
            username=self.username,
            rows=rows,
            parent=self,
        )
        self.final_slide_book_window.show()
