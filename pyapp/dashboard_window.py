from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyapp.experiment_setup_window import ExperimentSetupWindow
from pyapp.slide_library_window import SlideLibraryWindow


class DashboardWindow(QMainWindow):
    def __init__(self, username: str, mode: str) -> None:
        super().__init__()
        self.username = username
        self.mode = mode

        self.researcher_button: QPushButton | None = None
        self.admin_button: QPushButton | None = None
        self.new_experiment_button: QPushButton | None = None
        self.slibrary_button: QPushButton | None = None
        self.experiment_setup_window: ExperimentSetupWindow | None = None
        self.slide_library_window: SlideLibraryWindow | None = None

        self._build_ui()
        if self.mode == "admin":
            self._set_admin_mode()
        else:
            self._set_researcher_mode()

    def _build_ui(self) -> None:
        self.setWindowTitle("SlideApp")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 700)

        central = QWidget(self)
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        left_panel = QWidget(self)
        left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(70, 30, 70, 70)
        left_layout.addStretch()

        self.new_experiment_button = QPushButton("⚗\nNew\nExperiment", self)
        self.new_experiment_button.setObjectName("newExperimentCard")
        self.new_experiment_button.setFixedSize(410, 470)
        left_layout_card = QHBoxLayout()
        left_layout_card.addStretch()
        left_layout_card.addWidget(self.new_experiment_button)
        left_layout_card.addStretch()
        left_layout.addLayout(left_layout_card)
        left_layout.addStretch()

        right_panel = QWidget(self)
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(70, 30, 70, 70)

        top_row = QHBoxLayout()
        top_row.addStretch()

        self.researcher_button = QPushButton("Researcher Mode", self)
        self.researcher_button.setCheckable(True)
        self.researcher_button.setObjectName("modePill")

        self.admin_button = QPushButton("Admin Mode", self)
        self.admin_button.setCheckable(True)
        self.admin_button.setObjectName("modePill")

        mode_group = QButtonGroup(self)
        mode_group.setExclusive(True)
        mode_group.addButton(self.researcher_button)
        mode_group.addButton(self.admin_button)

        top_row.addWidget(self.researcher_button)
        top_row.addSpacing(10)
        top_row.addWidget(self.admin_button)
        right_layout.addLayout(top_row)

        right_layout.addStretch()

        self.slibrary_button = QPushButton("📘\nThe\nSlibrary", self)
        self.slibrary_button.setObjectName("slibraryCard")
        self.slibrary_button.setFixedSize(410, 470)
        right_layout_card = QHBoxLayout()
        right_layout_card.addStretch()
        right_layout_card.addWidget(self.slibrary_button)
        right_layout_card.addStretch()
        right_layout.addLayout(right_layout_card)

        right_layout.addStretch()

        footer = QLabel(f"Signed in as: {self.username}", self)
        footer.setObjectName("footerLabel")
        footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_layout.addWidget(footer)

        root.addWidget(left_panel, 1)
        root.addWidget(right_panel, 1)

        self.setStyleSheet(
            "QMainWindow { background: #000000; }"
            "QWidget { font-family: 'Helvetica Neue'; }"
            "QWidget#leftPanel { background: #dcdcdc; }"
            "QWidget#rightPanel { background: #000000; }"
            "QPushButton#modePill {"
            "  background: #d9d9d9;"
            "  color: #111111;"
            "  border: none;"
            "  border-radius: 11px;"
            "  padding: 10px 18px;"
            "  font-size: 25px;"
            "  min-width: 190px;"
            "}"
            "QPushButton#newExperimentCard {"
            "  background: #000000;"
            "  color: #f2f2f2;"
            "  border: none;"
            "  border-radius: 40px;"
            "  font-size: 66px;"
            "  line-height: 1.18em;"
            "  padding: 24px;"
            "}"
            "QPushButton#slibraryCard {"
            "  background: #efefef;"
            "  color: #000000;"
            "  border: none;"
            "  border-radius: 40px;"
            "  font-size: 66px;"
            "  line-height: 1.18em;"
            "  padding: 24px;"
            "}"
            "QLabel#footerLabel {"
            "  color: #bcbcbc;"
            "  font-size: 18px;"
            "}"
        )

        self.researcher_button.clicked.connect(self._set_researcher_mode)
        self.admin_button.clicked.connect(self._set_admin_mode)
        if self.new_experiment_button is not None:
            self.new_experiment_button.clicked.connect(self._open_experiment_setup)
        if self.slibrary_button is not None:
            self.slibrary_button.clicked.connect(self._open_slide_library)

    def _set_researcher_mode(self) -> None:
        if self.researcher_button is None or self.admin_button is None:
            return
        self.mode = "researcher"
        self.researcher_button.setChecked(True)
        self.researcher_button.setStyleSheet(
            "QPushButton {"
            "  background: #84F28A;"
            "  color: #000000;"
            "  border: none;"
            "  border-radius: 11px;"
            "  padding: 10px 18px;"
            "  font-size: 25px;"
            "  min-width: 190px;"
            "}"
        )

    def _open_experiment_setup(self) -> None:
        self.experiment_setup_window = ExperimentSetupWindow(
            username=self.username,
            mode=self.mode,
        )
        self.experiment_setup_window.show()
        self.close()

    def _open_slide_library(self) -> None:
        self.slide_library_window = SlideLibraryWindow(username=self.username)
        self.slide_library_window.show()
        self.close()
        self.admin_button.setStyleSheet(
            "QPushButton {"
            "  background: #d9d9d9;"
            "  color: #111111;"
            "  border: none;"
            "  border-radius: 11px;"
            "  padding: 10px 18px;"
            "  font-size: 25px;"
            "  min-width: 190px;"
            "}"
        )

    def _set_admin_mode(self) -> None:
        if self.researcher_button is None or self.admin_button is None:
            return
        self.mode = "admin"
        self.admin_button.setChecked(True)
        self.admin_button.setStyleSheet(
            "QPushButton {"
            "  background: #F26565;"
            "  color: #000000;"
            "  border: none;"
            "  border-radius: 11px;"
            "  padding: 10px 18px;"
            "  font-size: 25px;"
            "  min-width: 190px;"
            "}"
        )
        self.researcher_button.setStyleSheet(
            "QPushButton {"
            "  background: #d9d9d9;"
            "  color: #111111;"
            "  border: none;"
            "  border-radius: 11px;"
            "  padding: 10px 18px;"
            "  font-size: 25px;"
            "  min-width: 190px;"
            "}"
        )
