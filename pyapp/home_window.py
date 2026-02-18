from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyapp.database import verify_credentials


class HomeWindow(QMainWindow):
    login_success = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.researcher_button: QPushButton | None = None
        self.admin_button: QPushButton | None = None
        self.user_edit: QLineEdit | None = None
        self.password_edit: QLineEdit | None = None
        self.begin_button: QPushButton | None = None
        self.status_label: QLabel | None = None

        self._build_ui()
        self._apply_styles()
        self._set_researcher_mode()

    def _build_ui(self) -> None:
        self.setWindowTitle("SlideApp")
        self.resize(980, 680)
        self.setMinimumSize(840, 560)

        central = QWidget(self)
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(70, 30, 70, 40)
        root.setSpacing(0)

        top_row = QHBoxLayout()
        top_row.addStretch()

        self.researcher_button = QPushButton("Researcher Mode", self)
        self.researcher_button.setCheckable(True)

        self.admin_button = QPushButton("Admin Mode", self)
        self.admin_button.setCheckable(True)

        mode_group = QButtonGroup(self)
        mode_group.setExclusive(True)
        mode_group.addButton(self.researcher_button)
        mode_group.addButton(self.admin_button)

        top_row.addWidget(self.researcher_button)
        top_row.addSpacing(10)
        top_row.addWidget(self.admin_button)
        root.addLayout(top_row)

        root.addSpacing(86)

        title = QLabel("Emerson Lab", self)
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title.setObjectName("titleLabel")
        root.addWidget(title)

        root.addSpacing(44)

        form_wrap = QWidget(self)
        form_wrap.setMaximumWidth(760)
        form = QVBoxLayout(form_wrap)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(18)

        user_row = QHBoxLayout()
        user_row.setSpacing(14)
        user_label = QLabel("User:", self)
        user_label.setObjectName("fieldLabel")

        self.user_edit = QLineEdit(self)
        self.user_edit.setObjectName("fieldInput")
        self.user_edit.setMinimumWidth(420)
        self.user_edit.setPlaceholderText("")

        user_row.addWidget(user_label)
        user_row.addWidget(self.user_edit, 1)
        form.addLayout(user_row)

        password_row = QHBoxLayout()
        password_row.setSpacing(14)
        password_label = QLabel("Password:", self)
        password_label.setObjectName("fieldLabel")

        self.password_edit = QLineEdit(self)
        self.password_edit.setObjectName("fieldInput")
        self.password_edit.setMinimumWidth(420)
        self.password_edit.setPlaceholderText("")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        show_password_checkbox = QCheckBox("Show", self)
        show_password_checkbox.setObjectName("showPasswordCheck")
        show_password_checkbox.toggled.connect(
            lambda checked: self.password_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )

        password_row.addWidget(password_label)
        password_row.addWidget(self.password_edit, 1)
        password_row.addWidget(show_password_checkbox)
        form.addLayout(password_row)

        self.status_label = QLabel("", self)
        self.status_label.setObjectName("statusLabel")
        form.addWidget(self.status_label)

        form_center_row = QHBoxLayout()
        form_center_row.addStretch()
        form_center_row.addWidget(form_wrap)
        form_center_row.addStretch()
        root.addLayout(form_center_row)

        root.addSpacing(64)

        self.begin_button = QPushButton("Begin", self)
        self.begin_button.setObjectName("beginButton")
        self.begin_button.setFixedSize(280, 110)

        begin_row = QHBoxLayout()
        begin_row.addStretch()
        begin_row.addWidget(self.begin_button)
        begin_row.addStretch()
        root.addLayout(begin_row)

        root.addStretch()

        self.researcher_button.clicked.connect(self._set_researcher_mode)
        self.admin_button.clicked.connect(self._set_admin_mode)
        self.begin_button.clicked.connect(self._handle_begin_clicked)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            "QMainWindow { background: #000000; }"
            "QWidget { color: #f2f2f2; font-family: 'Helvetica Neue'; }"
            "QLabel#titleLabel { font-size: 78px; font-weight: 300; letter-spacing: 1px; }"
            "QLabel#fieldLabel { font-size: 42px; font-weight: 400; }"
            "QLineEdit#fieldInput {"
            "  background: transparent;"
            "  border: none;"
            "  color: #ffffff;"
            "  font-size: 42px;"
            "  font-weight: 400;"
            "  padding: 0;"
            "}"
            "QPushButton {"
            "  background: #d9d9d9;"
            "  color: #111111;"
            "  border: none;"
            "  border-radius: 11px;"
            "  padding: 10px 18px;"
            "  font-size: 25px;"
            "}"
            "QPushButton:hover { background: #ececec; }"
            "QPushButton:pressed { background: #bbbbbb; }"
            "QPushButton#beginButton {"
            "  background: #84F28A;"
            "  color: #000000;"
            "  border-radius: 48px;"
            "  font-size: 64px;"
            "  font-weight: 500;"
            "  padding: 0;"
            "}"
            "QPushButton#beginButton:hover { background: #95f69a; }"
            "QPushButton#beginButton:pressed { background: #76e87d; }"
            "QLabel#statusLabel { color: #ff9a9a; font-size: 20px; min-height: 24px; }"
            "QCheckBox#showPasswordCheck { color: #d4d4d4; font-size: 22px; }"
        )

    def _set_researcher_mode(self) -> None:
        if self.researcher_button is None or self.admin_button is None:
            return

        self.researcher_button.setChecked(True)
        self.researcher_button.setStyleSheet(
            "QPushButton {"
            "  background: #84F28A;"
            "  color: #000000;"
            "  border: none;"
            "  border-radius: 11px;"
            "  padding: 10px 18px;"
            "  font-size: 25px;"
            "}"
        )

        self.admin_button.setStyleSheet(
            "QPushButton {"
            "  background: #d9d9d9;"
            "  color: #111111;"
            "  border: none;"
            "  border-radius: 11px;"
            "  padding: 10px 18px;"
            "  font-size: 25px;"
            "}"
        )

    def _set_admin_mode(self) -> None:
        if self.researcher_button is None or self.admin_button is None:
            return

        self.admin_button.setChecked(True)
        self.admin_button.setStyleSheet(
            "QPushButton {"
            "  background: #F26565;"
            "  color: #000000;"
            "  border: none;"
            "  border-radius: 11px;"
            "  padding: 10px 18px;"
            "  font-size: 25px;"
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
            "}"
        )

    def _handle_begin_clicked(self) -> None:
        if (
            self.user_edit is None
            or self.password_edit is None
            or self.status_label is None
        ):
            return

        username = self.user_edit.text().strip()
        password = self.password_edit.text()
        if not username or not password:
            self.status_label.setText("Enter username and password.")
            return

        role = verify_credentials(username, password)
        if role is None:
            self.status_label.setText("Invalid credentials.")
            return

        if self.admin_button is not None and self.admin_button.isChecked() and role != "admin":
            self.status_label.setText("Admin mode requires an admin account.")
            return

        mode = "admin" if self.admin_button is not None and self.admin_button.isChecked() else "researcher"
        self.status_label.setText("")
        self.login_success.emit(username, mode)
