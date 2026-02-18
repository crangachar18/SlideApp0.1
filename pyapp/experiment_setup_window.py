from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pyapp.tree_canvas_window import TreeCanvasWindow


class ExperimentSetupWindow(QMainWindow):
    def __init__(self, username: str, mode: str) -> None:
        super().__init__()
        self.username = username
        self.mode = mode

        self.experiment_type_combo: QComboBox | None = None
        self.ihc_panel: QWidget | None = None
        self.pcr_panel: QWidget | None = None

        self.num_groups_spin: QSpinBox | None = None
        self.groups_container: QVBoxLayout | None = None
        self.groups_scroll_area: QScrollArea | None = None
        self.group_slide_spins: list[QSpinBox] = []
        self.generate_tree_button: QPushButton | None = None
        self.serum_type_combo: QComboBox | None = None
        self.edu_combo: QComboBox | None = None
        self.antibody_mix_volume_spin: QDoubleSpinBox | None = None
        self.primary_inc_combo: QComboBox | None = None
        self.secondary_inc_combo: QComboBox | None = None
        self.secondary_volume_spin: QDoubleSpinBox | None = None
        self.tree_window: TreeCanvasWindow | None = None

        self._build_ui()
        self._refresh_experiment_type_ui()
        self._rebuild_group_inputs(0)

    def _build_ui(self) -> None:
        self.setWindowTitle("SlideApp - New Experiment")
        self.resize(1450, 900)
        self.setMinimumSize(1180, 760)

        central = QWidget(self)
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(46, 30, 46, 34)
        root.setSpacing(20)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        search_icon = QLabel("🔎", self)
        search_icon.setObjectName("searchIcon")

        self.experiment_type_combo = QComboBox(self)
        self.experiment_type_combo.setObjectName("experimentTypeCombo")
        self.experiment_type_combo.setEditable(True)
        self.experiment_type_combo.addItems([
            "Immunohistochemistry (IHC)",
            "Polymerase Chain Reaction (PCR)",
        ])

        top_row.addWidget(search_icon)
        top_row.addWidget(self.experiment_type_combo, 1)
        top_row.addStretch()
        root.addLayout(top_row)

        split_row = QHBoxLayout()
        split_row.setSpacing(24)

        left_frame = QFrame(self)
        left_frame.setObjectName("leftFrame")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(28, 24, 28, 24)
        left_layout.setSpacing(18)

        self.ihc_panel = self._build_ihc_panel()
        self.pcr_panel = self._build_pcr_panel()
        left_layout.addWidget(self.ihc_panel)
        left_layout.addWidget(self.pcr_panel)
        left_layout.addStretch()

        right_frame = QFrame(self)
        right_frame.setObjectName("rightFrame")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(28, 24, 28, 24)
        right_layout.setSpacing(16)

        group_count_row = QHBoxLayout()
        group_count_label = QLabel("Number of treatment groups\n(including control):", self)
        group_count_label.setObjectName("inputLabel")

        self.num_groups_spin = QSpinBox(self)
        self.num_groups_spin.setRange(0, 12)
        self.num_groups_spin.setValue(0)

        group_count_row.addWidget(group_count_label)
        group_count_row.addStretch()
        group_count_row.addWidget(self.num_groups_spin)
        right_layout.addLayout(group_count_row)

        groups_widget = QWidget(self)
        groups_widget.setObjectName("groupsCanvas")
        self.groups_container = QVBoxLayout(groups_widget)
        self.groups_container.setSpacing(10)
        self.groups_container.setContentsMargins(0, 0, 0, 0)

        self.groups_scroll_area = QScrollArea(self)
        self.groups_scroll_area.setWidgetResizable(True)
        self.groups_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.groups_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.groups_scroll_area.setWidget(groups_widget)
        self.groups_scroll_area.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.groups_scroll_area.setMinimumHeight(240)
        right_layout.addWidget(self.groups_scroll_area)

        self.generate_tree_button = QPushButton("🍃 Generate Tree", self)
        self.generate_tree_button.setObjectName("generateTreeButton")
        self.generate_tree_button.setVisible(False)
        self.generate_tree_button.setFixedHeight(90)
        self._apply_generate_tree_icon()
        right_layout.addWidget(self.generate_tree_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        split_row.addWidget(left_frame, 1)
        split_row.addWidget(right_frame, 1)
        root.addLayout(split_row, 1)

        footer = QLabel(f"Signed in as: {self.username} ({self.mode})", self)
        footer.setObjectName("footerLabel")
        footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        root.addWidget(footer)

        self.setStyleSheet(
            "QMainWindow { background: #0e0e0e; }"
            "QWidget { font-family: 'Helvetica Neue'; color: #efefef; }"
            "QLabel#searchIcon { font-size: 28px; }"
            "QComboBox#experimentTypeCombo {"
            "  min-height: 48px;"
            "  font-size: 22px;"
            "  padding: 8px 12px;"
            "  background: #f2f2f2;"
            "  color: #1b1b1b;"
            "  border-radius: 10px;"
            "}"
            "QFrame#leftFrame, QFrame#rightFrame {"
            "  background: #171717;"
            "  border-radius: 18px;"
            "}"
            "QLabel#sectionTitle { font-size: 44px; font-weight: 700; }"
            "QLabel#inputLabel { font-size: 24px; }"
            "QWidget#groupsCanvas { background: #171717; }"
            "QScrollArea { background: #171717; border: none; }"
            "QScrollArea > QWidget > QWidget { background: #171717; }"
            "QComboBox, QSpinBox, QDoubleSpinBox {"
            "  min-height: 42px;"
            "  min-width: 220px;"
            "  font-size: 22px;"
            "  padding: 4px 10px;"
            "  background: #f2f2f2;"
            "  color: #141414;"
            "  border: none;"
            "  border-radius: 8px;"
            "}"
            "QComboBox {"
            "  padding-right: 10px;"
            "}"
            "QComboBox::drop-down {"
            "  subcontrol-origin: padding;"
            "  subcontrol-position: top right;"
            "  right: -34px;"
            "  width: 28px;"
            "  border: none;"
            "  background: transparent;"
            "}"
            "QComboBox::down-arrow {"
            "  width: 14px;"
            "  height: 14px;"
            "}"
            "QAbstractSpinBox {"
            "  padding-right: 10px;"
            "}"
            "QAbstractSpinBox::up-button {"
            "  subcontrol-origin: padding;"
            "  subcontrol-position: top right;"
            "  right: -34px;"
            "  width: 28px;"
            "  border: none;"
            "  background: transparent;"
            "}"
            "QAbstractSpinBox::down-button {"
            "  subcontrol-origin: padding;"
            "  subcontrol-position: bottom right;"
            "  right: -34px;"
            "  width: 28px;"
            "  border: none;"
            "  background: transparent;"
            "}"
            "QAbstractSpinBox::up-arrow, QAbstractSpinBox::down-arrow {"
            "  width: 12px;"
            "  height: 12px;"
            "}"
            "QPushButton#generateTreeButton {"
            "  min-width: 460px;"
            "  background: transparent;"
            "  color: #efefef;"
            "  border: none;"
            "  font-size: 42px;"
            "  font-weight: 700;"
            "  padding: 0;"
            "}"
            "QLabel#footerLabel { color: #bfbfbf; font-size: 18px; }"
        )

        self.experiment_type_combo.currentTextChanged.connect(self._refresh_experiment_type_ui)
        self.num_groups_spin.valueChanged.connect(self._rebuild_group_inputs)
        self.generate_tree_button.clicked.connect(self._open_tree_canvas)

    def _is_ihc_selected(self) -> bool:
        if self.experiment_type_combo is None:
            return False
        return "ihc" in self.experiment_type_combo.currentText().lower() or "immunohistochemistry" in self.experiment_type_combo.currentText().lower()

    def _refresh_experiment_type_ui(self) -> None:
        ihc_selected = self._is_ihc_selected()

        if self.ihc_panel is not None:
            self.ihc_panel.setVisible(ihc_selected)
        if self.pcr_panel is not None:
            self.pcr_panel.setVisible(not ihc_selected)

        self._update_generate_tree_visibility()

    def _clear_groups_layout(self) -> None:
        if self.groups_container is None:
            return

        while self.groups_container.count():
            item = self.groups_container.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _rebuild_group_inputs(self, count: int) -> None:
        self.group_slide_spins.clear()
        self._clear_groups_layout()

        if self.groups_container is None:
            return

        for idx in range(count):
            row = QWidget(self)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)

            label = QLabel(f"Group {idx + 1} slide count", self)
            label.setObjectName("inputLabel")

            spin = QSpinBox(self)
            spin.setRange(0, 1000)
            spin.setValue(0)
            spin.valueChanged.connect(self._update_generate_tree_visibility)

            self.group_slide_spins.append(spin)
            row_layout.addWidget(label)
            row_layout.addStretch()
            row_layout.addWidget(spin)

            self.groups_container.addWidget(row)

        if self.groups_scroll_area is not None:
            if count > 8:
                self.groups_scroll_area.setVerticalScrollBarPolicy(
                    Qt.ScrollBarPolicy.ScrollBarAsNeeded
                )
            else:
                self.groups_scroll_area.setVerticalScrollBarPolicy(
                    Qt.ScrollBarPolicy.ScrollBarAlwaysOff
                )

        self._update_generate_tree_visibility()

    def _update_generate_tree_visibility(self) -> None:
        if self.generate_tree_button is None or self.num_groups_spin is None:
            return

        if not self._is_ihc_selected():
            self.generate_tree_button.setVisible(False)
            return

        group_count = self.num_groups_spin.value()
        if group_count <= 0:
            self.generate_tree_button.setVisible(False)
            return

        all_positive = all(spin.value() > 0 for spin in self.group_slide_spins)
        self.generate_tree_button.setVisible(all_positive)

    def _build_ihc_panel(self) -> QWidget:
        panel = QWidget(self)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(18)

        ihc_title = QLabel("IHC Presets", self)
        ihc_title.setObjectName("sectionTitle")
        panel_layout.addWidget(ihc_title)

        presets_grid = QGridLayout()
        presets_grid.setHorizontalSpacing(16)
        presets_grid.setVerticalSpacing(14)

        serum_label = QLabel("Serum Type", self)
        serum_label.setObjectName("inputLabel")
        self.serum_type_combo = QComboBox(self)
        self.serum_type_combo.addItems(["Goat", "Donkey", "Sheep"])

        serum_conc_label = QLabel("Serum Concentration", self)
        serum_conc_label.setObjectName("inputLabel")
        serum_conc_spin = QDoubleSpinBox(self)
        serum_conc_spin.setRange(0.0, 100.0)
        serum_conc_spin.setValue(5.0)
        serum_conc_spin.setSingleStep(0.1)
        serum_conc_spin.setDecimals(1)
        serum_conc_spin.setSuffix(" %")
        serum_conc_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)

        detergent_label = QLabel("Detergent Type", self)
        detergent_label.setObjectName("inputLabel")
        detergent_combo = QComboBox(self)
        detergent_combo.addItems(["Triton X-100", "Tween 20"])

        detergent_conc_label = QLabel("Detergent Concentration", self)
        detergent_conc_label.setObjectName("inputLabel")
        detergent_conc_spin = QDoubleSpinBox(self)
        detergent_conc_spin.setRange(0.0, 100.0)
        detergent_conc_spin.setValue(0.1)
        detergent_conc_spin.setSingleStep(0.1)
        detergent_conc_spin.setDecimals(1)
        detergent_conc_spin.setSuffix(" %")
        detergent_conc_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)

        primary_block_label = QLabel("Primary block length (minutes)", self)
        primary_block_label.setObjectName("inputLabel")
        primary_block_spin = QSpinBox(self)
        primary_block_spin.setRange(0, 1440)
        primary_block_spin.setValue(60)
        primary_block_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)

        primary_inc_label = QLabel("Primary incubation length", self)
        primary_inc_label.setObjectName("inputLabel")
        self.primary_inc_combo = QComboBox(self)
        self.primary_inc_combo.addItems(["1 hour at room temp", "Overnight at 4C"])
        self.primary_inc_combo.setCurrentIndex(1)

        edu_label = QLabel("EdU?", self)
        edu_label.setObjectName("inputLabel")
        self.edu_combo = QComboBox(self)
        self.edu_combo.addItems(["No", "Yes"])

        antibody_mix_volume_label = QLabel("Antibody mix volume per slide (uL)", self)
        antibody_mix_volume_label.setObjectName("inputLabel")
        self.antibody_mix_volume_spin = QDoubleSpinBox(self)
        self.antibody_mix_volume_spin.setRange(0.0, 5000.0)
        self.antibody_mix_volume_spin.setValue(300.0)
        self.antibody_mix_volume_spin.setSingleStep(5.0)
        self.antibody_mix_volume_spin.setDecimals(1)
        self.antibody_mix_volume_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)

        secondary_volume_label = QLabel("Secondary antibody volume (uL)", self)
        secondary_volume_label.setObjectName("inputLabel")
        self.secondary_volume_spin = QDoubleSpinBox(self)
        self.secondary_volume_spin.setRange(0.0, 5000.0)
        self.secondary_volume_spin.setValue(500.0)
        self.secondary_volume_spin.setSingleStep(10.0)
        self.secondary_volume_spin.setDecimals(1)
        self.secondary_volume_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)

        secondary_inc_label = QLabel("Secondary incubation length", self)
        secondary_inc_label.setObjectName("inputLabel")
        self.secondary_inc_combo = QComboBox(self)
        self.secondary_inc_combo.addItems(["Overnight at 4C", "1 hour at room temp"])
        self.secondary_inc_combo.setCurrentIndex(0)

        presets_grid.addWidget(serum_label, 0, 0)
        presets_grid.addWidget(self.serum_type_combo, 0, 1)
        presets_grid.addWidget(serum_conc_label, 1, 0)
        presets_grid.addWidget(serum_conc_spin, 1, 1)
        presets_grid.addWidget(detergent_label, 2, 0)
        presets_grid.addWidget(detergent_combo, 2, 1)
        presets_grid.addWidget(detergent_conc_label, 3, 0)
        presets_grid.addWidget(detergent_conc_spin, 3, 1)
        presets_grid.addWidget(primary_block_label, 4, 0)
        presets_grid.addWidget(primary_block_spin, 4, 1)
        presets_grid.addWidget(primary_inc_label, 5, 0)
        presets_grid.addWidget(self.primary_inc_combo, 5, 1)
        presets_grid.addWidget(edu_label, 6, 0)
        presets_grid.addWidget(self.edu_combo, 6, 1)
        presets_grid.addWidget(antibody_mix_volume_label, 7, 0)
        presets_grid.addWidget(self.antibody_mix_volume_spin, 7, 1)
        presets_grid.addWidget(secondary_volume_label, 8, 0)
        presets_grid.addWidget(self.secondary_volume_spin, 8, 1)
        presets_grid.addWidget(secondary_inc_label, 9, 0)
        presets_grid.addWidget(self.secondary_inc_combo, 9, 1)

        panel_layout.addLayout(presets_grid)
        panel_layout.addStretch()
        return panel

    def _build_pcr_panel(self) -> QWidget:
        panel = QWidget(self)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(16)

        title = QLabel("PCR Presets", self)
        title.setObjectName("sectionTitle")
        panel_layout.addWidget(title)

        note = QLabel("PCR presets will be configured here.", self)
        note.setObjectName("inputLabel")
        note.setWordWrap(True)
        panel_layout.addWidget(note)
        panel_layout.addStretch()
        return panel

    def _apply_generate_tree_icon(self) -> None:
        if self.generate_tree_button is None:
            return

        candidates = [
            Path(__file__).resolve().parent / "generate-tree.png",
            Path(__file__).resolve().parent / "generate_tree.png",
            Path(__file__).resolve().parents[1] / "assets" / "generate-tree.png",
            Path(__file__).resolve().parents[1] / "assets" / "generate_tree.png",
        ]
        icon_path = next((path for path in candidates if path.exists()), None)
        if icon_path is None:
            return

        self.generate_tree_button.setText("")
        self.generate_tree_button.setIcon(QIcon(str(icon_path)))
        self.generate_tree_button.setIconSize(QSize(420, 80))

    def _open_tree_canvas(self) -> None:
        if (
            self.num_groups_spin is None
            or self.serum_type_combo is None
            or self.edu_combo is None
            or self.antibody_mix_volume_spin is None
            or self.primary_inc_combo is None
            or self.secondary_volume_spin is None
            or self.secondary_inc_combo is None
            or self.experiment_type_combo is None
        ):
            return

        group_slide_counts = [spin.value() for spin in self.group_slide_spins]
        if not group_slide_counts:
            return

        self.tree_window = TreeCanvasWindow(
            username=self.username,
            mode=self.mode,
            serum_type=self.serum_type_combo.currentText(),
            group_slide_counts=group_slide_counts,
            edu_enabled=self.edu_combo.currentText().strip().lower() == "yes",
            antibody_mix_volume_ul=self.antibody_mix_volume_spin.value(),
            primary_incubation_method=self.primary_inc_combo.currentText().strip(),
            secondary_volume_ul=self.secondary_volume_spin.value(),
            secondary_incubation_method=self.secondary_inc_combo.currentText().strip(),
            experiment_name=self.experiment_type_combo.currentText(),
        )
        self.tree_window.show()
        self.close()
