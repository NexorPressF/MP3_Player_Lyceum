import sys

from PyQt6.QtWidgets import QApplication

from core.settings import AppSettings
from data.database import Database
from paths import data_dir
from windows.common import icon
from windows.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(icon("app_icon"))
    folder = data_dir()
    db = Database(folder / "player.db")
    settings = AppSettings(folder / "settings.ini")
    window = MainWindow(db, settings)
    window.show()
    code = app.exec()
    db.close()
    sys.exit(code)


if __name__ == "__main__":
    main()
