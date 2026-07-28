"""
Log Console Inspector Dialog for Hedit Pro (Live log viewer).
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QFileDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from core.logger import LATEST_LOG_FILE, SESSION_LOG_FILE


class LogViewerDialog(QDialog):
    """Live Log Inspector Window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System Log Console - Hedit Pro")
        self.resize(750, 480)

        self.init_ui()
        self.load_logs()

        # Auto refresh timer
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.load_logs)
        self.timer.start()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header
        header = QHBoxLayout()
        lbl = QLabel(f"Active Session Log: {SESSION_LOG_FILE}")
        lbl.setStyleSheet("color: #00ffcc; font-size: 11px; font-weight: bold;")
        header.addWidget(lbl)
        header.addStretch()

        layout.addLayout(header)

        # Text Console
        self.text_console = QTextEdit()
        self.text_console.setReadOnly(True)
        self.text_console.setFont(QFont("Monospace", 9))
        self.text_console.setStyleSheet("""
            QTextEdit { background-color: #0c0c0c; color: #00ffcc; border: 1px solid #282828; }
        """)
        layout.addWidget(self.text_console)

        # Buttons
        btn_bar = QHBoxLayout()
        btn_save = QPushButton("💾 Save Log As...")
        btn_save.clicked.connect(self.on_save_log)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)

        btn_bar.addWidget(btn_save)
        btn_bar.addStretch()
        btn_bar.addWidget(btn_close)

        layout.addLayout(btn_bar)

    def load_logs(self):
        if os.path.exists(SESSION_LOG_FILE):
            try:
                with open(SESSION_LOG_FILE, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    self.text_console.setText("".join(lines[-500:])) # Show last 500 lines
                    self.text_console.moveCursor(self.text_console.textCursor().End)
            except Exception:
                pass

    def on_save_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Log File", "hedit_pro_session.log", "Log Files (*.log);;All Files (*)")
        if path and os.path.exists(SESSION_LOG_FILE):
            import shutil
            shutil.copy(SESSION_LOG_FILE, path)
