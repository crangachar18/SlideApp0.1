from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Signal, Qt
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

from pyapp.antibody_rules import (
    PrimaryAntibody,
    is_valid_antibody_selection,
    load_primaries,
)
from pyapp.master_mix_window import MasterMixDefinition, MasterMixWindow
from pyapp.secondary_tree_canvas_window import SecondaryTreeCanvasWindow


@dataclass(frozen=True)
class SlideRow:
    group_index: int
    slide_index: int


class SlideTreeView(QGraphicsView):
    slide_right_clicked = Signal(int, int)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.RightButton:
            item = self.itemAt(event.pos())
            if item is not None:
                key = item.data(0)
                if isinstance(key, str) and key.startswith("slide:"):
                    _, g_raw, s_raw = key.split(":")
                    self.slide_right_clicked.emit(int(g_raw), int(s_raw))
                    event.accept()
                    return
        super().mousePressEvent(event)


class TreeCanvasWindow(QMainWindow):
    def __init__(
        self,
        username: str,
        mode: str,
        serum_type: str,
        group_slide_counts: list[int],
        edu_enabled: bool,
        antibody_mix_volume_ul: float,
        primary_incubation_method: str,
        secondary_volume_ul: float,
        secondary_incubation_method: str,
        experiment_name: str = "Immunohistochemistry",
    ) -> None:
        super().__init__()
        self.username = username
        self.mode = mode
        self.serum_type = serum_type
        self.group_slide_counts = group_slide_counts
        self.edu_enabled = edu_enabled
        self.antibody_mix_volume_ul = antibody_mix_volume_ul
        self.primary_incubation_method = primary_incubation_method
        self.secondary_volume_ul = secondary_volume_ul
        self.secondary_incubation_method = secondary_incubation_method
        self.experiment_name = experiment_name

        self.antibodies = self._load_antibodies()
        self.by_name = {ab.name: ab for ab in self.antibodies}

        self.scene: QGraphicsScene | None = None
        self.tree_view: SlideTreeView | None = None
        self.table: QTableWidget | None = None
        self.status_label: QLabel | None = None
        self.slide_rows: list[SlideRow] = []
        self.antibody_column_indices: list[int] = []
        self.row_index_by_slide: dict[tuple[int, int], int] = {}
        self.slide_rect_by_key: dict[tuple[int, int], QGraphicsRectItem] = {}
        self.group_apply_button: QPushButton | None = None
        self.set_concentrations_button: QPushButton | None = None
        self.group_selected_rows: list[int] = []
        self.master_mix_window: MasterMixWindow | None = None
        self.secondary_tree_window: SecondaryTreeCanvasWindow | None = None

        self._build_ui()
        self._draw_tree()
        self._populate_table()

    def _load_antibodies(self) -> list[PrimaryAntibody]:
        root = Path(__file__).resolve().parent
        candidates = [
            root / "primaries.csv",
            root / "primaries - Sheet1.csv",
        ]
        for c in candidates:
            if c.exists():
                return load_primaries(c)
        return []

    def _build_ui(self) -> None:
        self.setWindowTitle("SlideApp - Tree Canvas")
        self.resize(1520, 920)
        self.setMinimumSize(1240, 760)

        central = QWidget(self)
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(10)

        header = QLabel(f"{self.experiment_name} / Tree Canvas", self)
        header.setObjectName("headerLabel")
        root.addWidget(header)

        meta = QLabel(
            f"Serum: {self.serum_type.title()}   |   Antibody mix volume per slide: {self.antibody_mix_volume_ul:.1f} uL",
            self,
        )
        meta.setObjectName("metaLabel")
        root.addWidget(meta)

        split = QHBoxLayout()
        split.setSpacing(18)

        view = SlideTreeView(self)
        self.tree_view = view
        self.scene = QGraphicsScene(self)
        view.setScene(self.scene)
        view.setObjectName("treeView")
        left = QVBoxLayout()
        left.setSpacing(8)

        left_actions = QHBoxLayout()
        left_actions.addStretch()
        self.group_apply_button = QPushButton("Group", self)
        self.group_apply_button.setVisible(False)
        self.group_apply_button.clicked.connect(self._apply_group_from_first_selected)
        left_actions.addWidget(self.group_apply_button)
        left.addLayout(left_actions)
        left.addWidget(view, 1)
        split.addLayout(left, 1)

        right = QVBoxLayout()
        right.setSpacing(10)

        self.table = QTableWidget(self)
        self.table.setObjectName("slideTable")
        antibody_count = 2 if self.edu_enabled else 3
        ab_headers = [f"AB{i}" for i in range(1, antibody_count + 1)]
        self.antibody_column_indices = list(range(1, 1 + antibody_count))
        self.table.setColumnCount(2 + antibody_count)
        self.table.setHorizontalHeaderLabels(["ID", *ab_headers, "MM"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        right.addWidget(self.table, 1)

        actions = QHBoxLayout()
        assign_button = QPushButton("Assign Master Mixes", self)
        assign_button.clicked.connect(self._assign_master_mix_ids)
        actions.addWidget(assign_button)
        actions.addStretch()
        self.set_concentrations_button = QPushButton("Set Master Mix Concentrations", self)
        self.set_concentrations_button.clicked.connect(self._open_master_mix_window)
        actions.addWidget(self.set_concentrations_button)
        right.addLayout(actions)

        self.status_label = QLabel("", self)
        self.status_label.setObjectName("statusLabel")
        right.addWidget(self.status_label)

        split.addLayout(right, 1)
        root.addLayout(split, 1)

        self.setStyleSheet(
            "QMainWindow { background: #dcdcdc; }"
            "QLabel#headerLabel { font-family: 'Helvetica Neue'; font-size: 48px; font-weight: 700; color: #111111; }"
            "QLabel#metaLabel { font-family: 'Helvetica Neue'; font-size: 20px; color: #202020; }"
            "QGraphicsView#treeView { background: #dcdcdc; border: none; }"
            "QTableWidget#slideTable { background: #f2f2f2; color: #111111; font-size: 18px; gridline-color: #c6c6c6; }"
            "QHeaderView::section { background: #e7e7e7; color: #111111; font-size: 22px; padding: 6px; border: none; }"
            "QPushButton { background: #111111; color: #f5f5f5; border: none; border-radius: 10px; padding: 10px 14px; font-size: 18px; }"
            "QPushButton:disabled { background: #777777; color: #d8d8d8; }"
            "QLabel#statusLabel { color: #8b0000; font-size: 16px; min-height: 24px; }"
        )

        if self.tree_view is not None:
            self.tree_view.slide_right_clicked.connect(self._handle_slide_right_click)

    def _draw_tree(self) -> None:
        if self.scene is None:
            return

        self.scene.clear()
        self.slide_rect_by_key.clear()

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
                slide_key = (g_idx, s_idx)
                s_box.setData(0, f"slide:{g_idx}:{s_idx}")
                self.slide_rect_by_key[slide_key] = s_box
                self.scene.addItem(s_box)
                s_text = QGraphicsSimpleTextItem(f"Slide {g_idx + 1}-{s_idx + 1}")
                s_text.setPos(slide_x + 24, y + 13)
                s_text.setData(0, f"slide:{g_idx}:{s_idx}")
                self.scene.addItem(s_text)

                self.scene.addLine(group_x + 180, group_y + 28, slide_x, y + 23, pen)

            # Advance the next group start to avoid vertical overlap with this group's slides.
            slide_block_height = max(56, (slide_count - 1) * slide_gap + 46)
            group_top += slide_block_height + group_block_padding

        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-30, -30, 40, 40))

    def _populate_table(self) -> None:
        if self.table is None:
            return

        self.slide_rows = []
        self.row_index_by_slide.clear()
        for g_idx, count in enumerate(self.group_slide_counts):
            for s_idx in range(count):
                self.slide_rows.append(SlideRow(group_index=g_idx, slide_index=s_idx))

        self.table.setRowCount(len(self.slide_rows))

        options = ["None", *[ab.name for ab in self.antibodies]]

        for row_idx, slide in enumerate(self.slide_rows):
            self.row_index_by_slide[(slide.group_index, slide.slide_index)] = row_idx
            slide_id = f"G{slide.group_index + 1}-S{slide.slide_index + 1}"
            self.table.setItem(row_idx, 0, QTableWidgetItem(slide_id))

            for col in self.antibody_column_indices:
                combo = QComboBox(self)
                combo.addItems(options)
                combo.currentIndexChanged.connect(lambda _i, r=row_idx: self._validate_row(r))
                self.table.setCellWidget(row_idx, col, combo)

            mm_item = QTableWidgetItem("")
            self.table.setItem(row_idx, self.table.columnCount() - 1, mm_item)

        self.table.resizeColumnsToContents()

    def _row_has_any_antibody(self, row: int) -> bool:
        if self.table is None:
            return False
        for col in self.antibody_column_indices:
            combo = self.table.cellWidget(row, col)
            if isinstance(combo, QComboBox) and combo.currentText().strip() not in {"", "None"}:
                return True
        return False

    def _set_slide_selected_visual(self, key: tuple[int, int], selected: bool) -> None:
        rect = self.slide_rect_by_key.get(key)
        if rect is None:
            return
        if selected:
            rect.setBrush(QBrush(QColor("#6ca6ff")))
        else:
            rect.setBrush(QBrush(QColor("#c8c8c8")))

    def _handle_slide_right_click(self, group_idx: int, slide_idx: int) -> None:
        if self.status_label is None:
            return
        key = (group_idx, slide_idx)
        row = self.row_index_by_slide.get(key)
        if row is None:
            return
        if row in self.group_selected_rows:
            self.group_selected_rows.remove(row)
            self._set_slide_selected_visual(key, selected=False)
            if self.group_apply_button is not None:
                self.group_apply_button.setVisible(len(self.group_selected_rows) > 0)
                self.group_apply_button.setEnabled(len(self.group_selected_rows) >= 2)
            self.status_label.setText("")
            return
        # First selected slide must define a source antibody set.
        if not self.group_selected_rows and not self._row_has_any_antibody(row):
            self.status_label.setText("Set at least one antibody on a slide before grouping.")
            return
        if row not in self.group_selected_rows:
            self.group_selected_rows.append(row)
            self._set_slide_selected_visual(key, selected=True)
        if self.group_apply_button is not None:
            self.group_apply_button.setVisible(True)
            self.group_apply_button.setEnabled(len(self.group_selected_rows) >= 2)
        self.status_label.setText("")

    def _selected_antibodies_for_row(self, row: int) -> list[PrimaryAntibody]:
        if self.table is None:
            return []

        selected: list[PrimaryAntibody] = []
        for col in self.antibody_column_indices:
            combo = self.table.cellWidget(row, col)
            if not isinstance(combo, QComboBox):
                continue
            name = combo.currentText().strip()
            if not name or name == "None":
                continue
            ab = self.by_name.get(name)
            if ab is not None:
                selected.append(ab)
        return selected

    def _validate_row(self, row: int) -> None:
        if self.table is None or self.status_label is None:
            return

        selected = self._selected_antibodies_for_row(row)
        ok = is_valid_antibody_selection(selected, self.serum_type)

        for col in self.antibody_column_indices:
            widget = self.table.cellWidget(row, col)
            if isinstance(widget, QComboBox):
                widget.setStyleSheet("background: #f2f2f2;" if ok else "background: #ffd8d8;")

        if not ok:
            self.status_label.setText(
                "Invalid antibody combination: duplicate host animals are blocked (except mouse with allowed subtype rules), and serum-matching host is blocked."
            )
        else:
            self.status_label.setText("")

    def _apply_group_from_first_selected(self) -> None:
        if self.table is None or len(self.group_selected_rows) < 2:
            return

        source_row = self.group_selected_rows[0]
        source_values: list[str] = []
        for col in self.antibody_column_indices:
            combo = self.table.cellWidget(source_row, col)
            value = combo.currentText().strip() if isinstance(combo, QComboBox) else "None"
            source_values.append(value)

        if all(v in {"", "None"} for v in source_values):
            return

        for row in self.group_selected_rows[1:]:
            for idx, col in enumerate(self.antibody_column_indices):
                combo = self.table.cellWidget(row, col)
                if isinstance(combo, QComboBox):
                    combo.setCurrentText(source_values[idx])

        mm_col = self.table.columnCount() - 1
        for row in self.group_selected_rows:
            mm_item = self.table.item(row, mm_col)
            if mm_item is None:
                mm_item = QTableWidgetItem("")
                self.table.setItem(row, mm_col, mm_item)
            # User can assign manually later or via Assign Master Mixes button.
            mm_item.setText("")

        for row in self.group_selected_rows:
            slide = self.slide_rows[row]
            self._set_slide_selected_visual((slide.group_index, slide.slide_index), selected=False)
        self.group_selected_rows.clear()
        if self.group_apply_button is not None:
            self.group_apply_button.setVisible(False)

    def _assign_master_mix_ids(self) -> None:
        if self.table is None:
            return

        mix_map: dict[tuple[str, ...], str] = {}
        next_idx = 1

        for row in range(self.table.rowCount()):
            raw_values: list[str] = []
            for col in self.antibody_column_indices:
                combo = self.table.cellWidget(row, col)
                value = combo.currentText().strip() if isinstance(combo, QComboBox) else "None"
                raw_values.append(value)

            selected = sorted([v for v in raw_values if v != "None"])
            canonical_values = [*selected]
            while len(canonical_values) < len(self.antibody_column_indices):
                canonical_values.append("None")

            # Realign row ordering so equivalent antibody sets look identical in AB columns.
            for idx, col in enumerate(self.antibody_column_indices):
                combo = self.table.cellWidget(row, col)
                if isinstance(combo, QComboBox):
                    combo.setCurrentText(canonical_values[idx])

            key = tuple(canonical_values)
            if all(v == "None" for v in key):
                mm_col = self.table.columnCount() - 1
                mm_item = self.table.item(row, mm_col)
                if mm_item is None:
                    mm_item = QTableWidgetItem("")
                    self.table.setItem(row, mm_col, mm_item)
                mm_item.setText("")
                continue
            if key not in mix_map:
                mix_map[key] = f"MM{next_idx}"
                next_idx += 1

            mm_col = self.table.columnCount() - 1
            mm_item = self.table.item(row, mm_col)
            if mm_item is None:
                mm_item = QTableWidgetItem("")
                self.table.setItem(row, mm_col, mm_item)
            mm_item.setText(mix_map[key])

    def _collect_master_mix_definitions(self) -> list[MasterMixDefinition]:
        if self.table is None:
            return []

        mm_groups: dict[str, dict[str, object]] = {}
        mm_col = self.table.columnCount() - 1

        for row in range(self.table.rowCount()):
            mm_item = self.table.item(row, mm_col)
            mm_id = mm_item.text().strip() if mm_item is not None else ""
            if not mm_id:
                continue

            if mm_id not in mm_groups:
                mm_groups[mm_id] = {"slides": 0, "antibodies": set()}

            mm_groups[mm_id]["slides"] = int(mm_groups[mm_id]["slides"]) + 1
            ab_set = mm_groups[mm_id]["antibodies"]
            if isinstance(ab_set, set):
                for col in self.antibody_column_indices:
                    combo = self.table.cellWidget(row, col)
                    name = combo.currentText().strip() if isinstance(combo, QComboBox) else ""
                    if name and name != "None":
                        ab_set.add(name)

        mixes: list[MasterMixDefinition] = []
        for mm_id in sorted(mm_groups.keys()):
            slide_count = int(mm_groups[mm_id]["slides"])
            ab_names = sorted(list(mm_groups[mm_id]["antibodies"]))  # deterministic order
            mixes.append(MasterMixDefinition(mix_id=mm_id, slide_count=slide_count, antibodies=ab_names))

        return mixes

    def _open_master_mix_window(self) -> None:
        if self.status_label is None:
            return

        mixes = self._collect_master_mix_definitions()
        if not mixes:
            self.status_label.setText("Assign master mixes first, then set concentrations.")
            return

        default_concentrations: dict[str, float] = {}
        for ab in self.antibodies:
            if ab.concentration is not None:
                default_concentrations[ab.name] = ab.concentration

        self.master_mix_window = MasterMixWindow(
            mixes=mixes,
            default_concentrations=default_concentrations,
            total_slide_count=len(self.slide_rows),
            primary_volume_ul=self.antibody_mix_volume_ul,
            primary_incubation_method=self.primary_incubation_method,
            on_set_secondaries=self._open_secondary_tree_canvas,
            parent=self,
        )
        self.master_mix_window.show()

    def _collect_primary_per_slide(self) -> dict[tuple[int, int], list[str]]:
        if self.table is None:
            return {}

        out: dict[tuple[int, int], list[str]] = {}
        for row, slide in enumerate(self.slide_rows):
            names: list[str] = []
            for col in self.antibody_column_indices:
                combo = self.table.cellWidget(row, col)
                if isinstance(combo, QComboBox):
                    name = combo.currentText().strip()
                    if name and name != "None":
                        names.append(name)
            out[(slide.group_index, slide.slide_index)] = names
        return out

    def _collect_primary_mm_per_slide(self) -> dict[tuple[int, int], str]:
        if self.table is None:
            return {}

        out: dict[tuple[int, int], str] = {}
        mm_col = self.table.columnCount() - 1
        for row, slide in enumerate(self.slide_rows):
            item = self.table.item(row, mm_col)
            out[(slide.group_index, slide.slide_index)] = item.text().strip() if item is not None else ""
        return out

    def _open_secondary_tree_canvas(self) -> None:
        self.secondary_tree_window = SecondaryTreeCanvasWindow(
            username=self.username,
            mode=self.mode,
            group_slide_counts=self.group_slide_counts,
            edu_enabled=self.edu_enabled,
            primary_per_slide=self._collect_primary_per_slide(),
            primary_mm_per_slide=self._collect_primary_mm_per_slide(),
            primary_by_name=self.by_name,
            secondary_volume_ul=self.secondary_volume_ul,
            secondary_incubation_method=self.secondary_incubation_method,
            experiment_name=self.experiment_name,
            parent=self,
        )
        self.secondary_tree_window.show()
