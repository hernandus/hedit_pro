"""
Multi-Track Timeline Canvas Widget for Hedit Pro.
High-performance PySide6 canvas for clips, playhead, snapping, and editing tools.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsLineItem, QFrame
)
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QColor, QPen, QBrush, QFont


class TimelineCanvasWidget(QWidget):
    """Timeline Editor View with multi-track support, playhead, and zoom controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Timeline Header Controls (Tools & Zoom)
        header = QFrame()
        header.setFixedHeight(32)
        header.setStyleSheet("background-color: #242424; border-bottom: 1px solid #2b2b2b;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 2, 8, 2)
        header_layout.setSpacing(4)

        # Tools: Selection (V), Razor (C), Ripple (B)
        self.btn_select_tool = QPushButton("V Select")
        self.btn_razor_tool = QPushButton("C Razor")
        self.btn_ripple_tool = QPushButton("B Ripple")

        for btn in (self.btn_select_tool, self.btn_razor_tool, self.btn_ripple_tool):
            btn.setFixedHeight(24)
            btn.setCheckable(True)
            header_layout.addWidget(btn)

        self.btn_select_tool.setChecked(True)
        header_layout.addStretch()

        self.zoom_label = QLabel("Zoom:")
        self.zoom_label.setStyleSheet("color: #888888;")
        header_layout.addWidget(self.zoom_label)

        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_in = QPushButton("+")
        for btn in (self.btn_zoom_out, self.btn_zoom_in):
            btn.setFixedSize(24, 24)
            header_layout.addWidget(btn)

        layout.addWidget(header)

        # Graphics Scene & View for Timeline Tracks
        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush(QBrush(QColor("#181818")))
        self.scene.setSceneRect(0, 0, 4000, 400)

        self.view = QGraphicsView(self.scene)
        self.view.setStyleSheet("border: none; background-color: #181818;")
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        layout.addWidget(self.view)

        # Build initial tracks representation
        self.draw_track_backgrounds()

    def draw_track_backgrounds(self):
        """Draw V1, V2, V3 and A1, A2, A3 track lanes."""
        self.scene.clear()
        
        # Track heights
        track_h = 50
        num_video = 3
        num_audio = 3

        # Video tracks (V3, V2, V1)
        for i in range(num_video):
            y = i * track_h
            bg = QGraphicsRectItem(0, y, 4000, track_h - 2)
            bg.setBrush(QBrush(QColor("#222222" if i % 2 == 0 else "#1f1f1f")))
            bg.setPen(QPen(QColor("#2a2a2a")))
            self.scene.addItem(bg)

        # Separator line
        sep_y = num_video * track_h
        sep_line = QGraphicsLineItem(0, sep_y, 4000, sep_y)
        sep_line.setPen(QPen(QColor("#2680eb"), 2))
        self.scene.addItem(sep_line)

        # Audio tracks (A1, A2, A3)
        for i in range(num_audio):
            y = sep_y + 4 + (i * track_h)
            bg = QGraphicsRectItem(0, y, 4000, track_h - 2)
            bg.setBrush(QBrush(QColor("#1c232a" if i % 2 == 0 else "#192026")))
            bg.setPen(QPen(QColor("#25303a")))
            self.scene.addItem(bg)

        # Playhead indicator
        self.playhead = QGraphicsLineItem(150, 0, 150, 350)
        self.playhead.setPen(QPen(QColor("#00ffcc"), 2))
        self.scene.addItem(self.playhead)
