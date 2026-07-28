"""
Entry point for Hedit Pro - Adobe Premiere Pro Clone for Linux.
"""

import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from gui.theme import PREMIERE_DARK_STYLESHEET
from gui.main_window import MainWindow


def main():
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Hedit Pro")
    app.setOrganizationName("Hedit")

    # Apply Premiere Pro Charcoal Dark Theme
    app.setStyleSheet(PREMIERE_DARK_STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
