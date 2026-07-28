"""
Track Header Widget for Hedit Pro Timeline (Track Controls: Mute, Solo, Lock, Target).
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal


class TrackHeaderWidget(QWidget):
    """Header widget displayed to the left of each timeline track lane."""

    mute_toggled = Signal(bool)
    solo_toggled = Signal(bool)
    lock_toggled = Signal(bool)

    def __init__(self, track_name: str, is_audio: bool = False, parent=None):
        super().__init__(parent)
        self.track_name = track_name
        self.is_audio = is_audio
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        # Track Label
        self.lbl_name = QLabel(self.track_name)
        self.lbl_name.setFixedWidth(28)
        self.lbl_name.setStyleSheet(
            "font-weight: bold; color: " + ("#81c784" if self.is_audio else "#64b5f6") + ";"
        )
        layout.addWidget(self.lbl_name)

        # Mute (M) Button
        self.btn_mute = QPushButton("M")
        self.btn_mute.setFixedSize(20, 20)
        self.btn_mute.setCheckable(True)
        self.btn_mute.setToolTip("Mute Track (M)")
        self.btn_mute.setStyleSheet("""
            QPushButton { background-color: #242424; color: #888888; border-radius: 2px; font-weight: bold; }
            QPushButton:checked { background-color: #d32f2f; color: #ffffff; }
        """)
        self.btn_mute.toggled.connect(self.mute_toggled.emit)
        layout.addWidget(self.btn_mute)

        # Solo (S) Button (Audio only) or Target (V)
        if self.is_audio:
            self.btn_solo = QPushButton("S")
            self.btn_solo.setFixedSize(20, 20)
            self.btn_solo.setCheckable(True)
            self.btn_solo.setToolTip("Solo Track (S)")
            self.btn_solo.setStyleSheet("""
                QPushButton { background-color: #242424; color: #888888; border-radius: 2px; font-weight: bold; }
                QPushButton:checked { background-color: #fbc02d; color: #000000; }
            """)
            self.btn_solo.toggled.connect(self.solo_toggled.emit)
            layout.addWidget(self.btn_solo)

        # Lock Button (🔒)
        self.btn_lock = QPushButton("🔒")
        self.btn_lock.setFixedSize(20, 20)
        self.btn_lock.setCheckable(True)
        self.btn_lock.setToolTip("Lock Track")
        self.btn_lock.setStyleSheet("""
            QPushButton { background-color: #242424; color: #888888; border-radius: 2px; font-size: 10px; }
            QPushButton:checked { background-color: #424242; color: #ff9800; }
        """)
        self.btn_lock.toggled.connect(self.lock_toggled.emit)
        layout.addWidget(self.btn_lock)

        layout.addStretch()
