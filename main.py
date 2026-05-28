import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase, QFont, QIcon

from config import Config
from ui.main_window import MainWindow
from utils import app_dir

_FONTS_DIR = app_dir() / "project" / "fonts"


def _load_fonts():
    for f in _FONTS_DIR.glob("*.otf"):
        QFontDatabase.addApplicationFont(str(f))
    for f in _FONTS_DIR.glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(f))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ANDRE")
    app.setOrganizationName("GoldenPixel")

    _load_fonts()
    app.setFont(QFont("terminal grotesque"))

    icon_path = app_dir() / "ANDRE.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # High-DPI handled automatically by Qt6

    config = Config()
    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
