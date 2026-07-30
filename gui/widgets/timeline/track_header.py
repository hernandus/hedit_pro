"""
Track Header Widget for Hedit Pro Timeline.
Renders track controls (Target toggle, Lock, Eye/Visibility, Mute, Solo) with SVG icons and Premiere Pro styling.
"""

import os
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon

ELEMENTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../Interface_elements")
)


class TrackHeaderWidget(QWidget):
    """Header widget displayed to the left of each timeline track lane."""

    mute_toggled = Signal(bool)
    solo_toggled = Signal(bool)
    lock_toggled = Signal(bool)
    eye_toggled = Signal(bool)
    target_toggled = Signal(bool)

    def __init__(self, track_name: str, is_audio: bool = False, is_target: bool = False, track_index: int = 0, parent=None):
        super().__init__(parent)
        self.track_name = track_name
        self.is_audio = is_audio
        self.default_target = is_target
        self.track_index = track_index

        # Enable QWidget stylesheet background and border rendering
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Load SVG Icons
        self.icon_lock_locked = QIcon(os.path.join(ELEMENTS_DIR, "icon_lock_locked.svg"))
        self.icon_lock_unlocked = QIcon(os.path.join(ELEMENTS_DIR, "icon_lock_unlocked.svg"))
        self.icon_eye_open = QIcon(os.path.join(ELEMENTS_DIR, "icon_eye_open.svg"))
        self.icon_eye_hidden = QIcon(os.path.join(ELEMENTS_DIR, "icon_eye_hidden.svg"))

        self.init_ui()

    def init_ui(self):
        self.setFixedHeight(27)

        # Border & background styling per track type (matching right canvas lanes)
        if self.is_audio:
            bg_color = "#182026" if self.track_index % 2 == 0 else "#151c22"
            self.setStyleSheet(f"""
                TrackHeaderWidget {{
                    background-color: {bg_color};
                    border-bottom: 1px solid #222d36;
                }}
            """)
        else:
            bg_color = "#202020" if self.track_index % 2 == 0 else "#1c1c1c"
            self.setStyleSheet(f"""
                TrackHeaderWidget {{
                    background-color: {bg_color};
                    border-top: 1px solid #282828;
                }}
            """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)

        # 1. Target Track Button ([ V1 ] / V2 / [ A1 ])
        self.btn_target = QPushButton(self.track_name)
        self.btn_target.setFixedSize(28, 20)
        self.btn_target.setCheckable(True)
        self.btn_target.setChecked(self.default_target)
        self.btn_target.setToolTip(f"Target Track ({self.track_name})")
        self._update_target_style(self.default_target)
        self.btn_target.toggled.connect(self._on_target_toggled)
        layout.addWidget(self.btn_target)

        # 2. Lock Button (🔒 SVG)
        self.btn_lock = QPushButton()
        self.btn_lock.setFixedSize(20, 20)
        self.btn_lock.setIconSize(QSize(13, 13))
        self.btn_lock.setCheckable(True)
        self.btn_lock.setIcon(self.icon_lock_unlocked)
        self.btn_lock.setToolTip("Lock Track")
        self.btn_lock.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 2px;
            }
            QPushButton:hover {
                background-color: #2a2a2a;
            }
            QPushButton:checked {
                background-color: #332815;
            }
        """)
        self.btn_lock.toggled.connect(self._on_lock_toggled)
        layout.addWidget(self.btn_lock)

        # 3. Controls right of lock: Eye icon for Video, Mute/Solo for Audio
        if not self.is_audio:
            # Eye / Visibility Button
            self.btn_eye = QPushButton()
            self.btn_eye.setFixedSize(20, 20)
            self.btn_eye.setIconSize(QSize(14, 14))
            self.btn_eye.setCheckable(True)
            self.btn_eye.setIcon(self.icon_eye_open)
            self.btn_eye.setToolTip("Toggle Track Output (Eye)")
            self.btn_eye.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 2px;
                }
                QPushButton:hover {
                    background-color: #2a2a2a;
                }
            """)
            self.btn_eye.toggled.connect(self._on_eye_toggled)
            layout.addWidget(self.btn_eye)
        else:
            # Mute Button (M)
            self.btn_mute = QPushButton("M")
            self.btn_mute.setFixedSize(18, 18)
            self.btn_mute.setCheckable(True)
            self.btn_mute.setToolTip("Mute Track (M)")
            self.btn_mute.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #777777;
                    border: none;
                    border-radius: 2px;
                    font-size: 10px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #282828;
                }
                QPushButton:checked {
                    background-color: #d32f2f;
                    color: #ffffff;
                }
            """)
            self.btn_mute.toggled.connect(self.mute_toggled.emit)
            layout.addWidget(self.btn_mute)

            # Solo Button (S)
            self.btn_solo = QPushButton("S")
            self.btn_solo.setFixedSize(18, 18)
            self.btn_solo.setCheckable(True)
            self.btn_solo.setToolTip("Solo Track (S)")
            self.btn_solo.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #777777;
                    border: none;
                    border-radius: 2px;
                    font-size: 10px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #282828;
                }
                QPushButton:checked {
                    background-color: #fbc02d;
                    color: #000000;
                }
            """)
            self.btn_solo.toggled.connect(self.solo_toggled.emit)
            layout.addWidget(self.btn_solo)

        layout.addStretch()

    def _update_target_style(self, checked: bool):
        if checked:
            self.btn_target.setStyleSheet("""
                QPushButton {
                    background-color: #1565c0;
                    color: #ffffff;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 11px;
                    border: none;
                }
            """)
        else:
            self.btn_target.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #777777;
                    border-radius: 3px;
                    font-size: 11px;
                    border: none;
                }
                QPushButton:hover {
                    color: #bbbbbb;
                    background-color: #282828;
                }
            """)

    def _on_target_toggled(self, checked: bool):
        self._update_target_style(checked)
        self.target_toggled.emit(checked)

    def _on_lock_toggled(self, checked: bool):
        self.btn_lock.setIcon(self.icon_lock_locked if checked else self.icon_lock_unlocked)
        self.lock_toggled.emit(checked)

    def _on_eye_toggled(self, checked: bool):
        self.btn_eye.setIcon(self.icon_eye_hidden if checked else self.icon_eye_open)
        self.eye_toggled.emit(checked)

