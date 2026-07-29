"""
Entry point for Hedit Pro - Adobe Premiere Pro Clone for Linux.
Initializes centralized logging, Qt application, dark QSS theme, and main window.
"""

import sys
import os
import atexit

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from core.logger import HeditLogger, get_logger
from gui.theme import PREMIERE_DARK_STYLESHEET
from gui.style import HeditProStyle
from gui.main_window import MainWindow


def main():
    # 1. Initialize Centralized Application Logger
    HeditLogger.setup_logging()
    logger = get_logger()
    logger.info("[APP] Starting Hedit Pro application process...")

    # Register clean shutdown callback
    atexit.register(HeditLogger.shutdown)

    # 2. Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Hedit Pro")
    app.setOrganizationName("Hedit")

    # 3. Install custom style (wide dock separator grab zones)
    app.setStyle(HeditProStyle())

    # 4. Apply Premiere Pro Charcoal Dark Theme
    logger.info("[UI] Applying Premiere Pro Charcoal Dark QSS stylesheet.")
    app.setStyleSheet(PREMIERE_DARK_STYLESHEET)

    # 4. Instantiate & Show MainWindow
    window = MainWindow()
    window.show()

    logger.info("[APP] Event loop running.")
    ret_code = app.exec()

    logger.info(f"[APP] Application exited with code {ret_code}.")
    sys.exit(ret_code)


if __name__ == "__main__":
    main()
