"""
Source Monitor Widget (Premiere Pro style clip preview and In/Out trimmer).
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSlider
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont


class SourceMonitorWidget(QWidget):
    """Source Monitor for loading raw media clips, setting In/Out marks, and auditioning."""

    mark_in_changed = Signal(int)
    mark_out_changed = Signal(int)

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
        
        self.placeholder_label = QLabel("NO CLIP LOADED IN SOURCE MONITOR")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #555555; font-weight: bold; font-size: 13px;")
        self.viewport_layout.addWidget(self.placeholder_label)

        layout.addWidget(self.viewport, stretch=1)

        # Timecode & Controls Bar
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(2, 2, 2, 2)
        controls_layout.setSpacing(6)

        # Timecode display
        self.tc_label = QLabel("00:00:00:00")
        self.tc_label.setFont(QFont("Monospace", 11, QFont.Bold))
        self.tc_label.setStyleSheet("color: #2680eb; background-color: #121212; padding: 4px 8px; border-radius: 3px;")
        controls_layout.addWidget(self.tc_label)

        # Transport buttons
        self.btn_mark_in = QPushButton("Mark In {I}")
        self.btn_mark_out = QPushButton("Mark Out {O}")
        self.btn_play = QPushButton("▶ Play")
        self.btn_insert = QPushButton(",, Insert")
        self.btn_overwrite = QPushButton(". Overwrite")

        for btn in (self.btn_mark_in, self.btn_mark_out, self.btn_play, self.btn_insert, self.btn_overwrite):
            btn.setFixedHeight(26)
            controls_layout.addWidget(btn)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)
