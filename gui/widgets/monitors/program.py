"""
Program Monitor Widget (Premiere Pro style active timeline sequence preview).
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class ProgramMonitorWidget(QWidget):
    """Program Monitor for rendering the active Timeline sequence."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Video Viewport Frame
        self.viewport = QFrame()
        self.viewport.setStyleSheet("background-color: #000000; border: 1px solid #282828;")
        self.viewport_layout = QVBoxLayout(self.viewport)

        self.placeholder_label = QLabel("PROGRAM MONITOR (SEQUENCE PREVIEW)")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #2680eb; font-weight: bold; font-size: 14px;")
        self.viewport_layout.addWidget(self.placeholder_label)

        layout.addWidget(self.viewport, stretch=1)

        # Transport & Quality Bar
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(2, 2, 2, 2)
        controls_layout.setSpacing(6)

        # Resolution dropdown (Full, 1/2, 1/4)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Full", "1/2 Resolution", "1/4 Resolution"])
        self.quality_combo.setFixedWidth(110)
        controls_layout.addWidget(self.quality_combo)

        # Timecode display
        self.tc_label = QLabel("00:00:00:00")
        self.tc_label.setFont(QFont("Monospace", 11, QFont.Bold))
        self.tc_label.setStyleSheet("color: #00ffcc; background-color: #121212; padding: 4px 8px; border-radius: 3px;")
        controls_layout.addWidget(self.tc_label)

        # Transport buttons
        self.btn_step_back = QPushButton("⏮ 1 Frame")
        self.btn_play = QPushButton("▶ Play")
        self.btn_step_forward = QPushButton("1 Frame ⏭")
        self.btn_loop = QPushButton("🔁 Loop")

        for btn in (self.btn_step_back, self.btn_play, self.btn_step_forward, self.btn_loop):
            btn.setFixedHeight(26)
            controls_layout.addWidget(btn)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)
