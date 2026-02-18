import sys

from PySide6.QtWidgets import QApplication

from pyapp.dashboard_window import DashboardWindow
from pyapp.database import init_auth_db
from pyapp.home_window import HomeWindow


def main() -> int:
    init_auth_db()

    app = QApplication(sys.argv)
    login_window = HomeWindow()
    windows: dict[str, object] = {"login": login_window}

    def on_login_success(username: str, mode: str) -> None:
        dashboard = DashboardWindow(username=username, mode=mode)
        windows["dashboard"] = dashboard
        dashboard.show()
        login_window.close()

    login_window.login_success.connect(on_login_success)
    login_window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
