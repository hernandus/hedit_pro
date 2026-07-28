"""
Program Monitor Widget for Hedit Pro.
Active sequence preview, resolution scaling, shuttle playback, and timecode synchronization.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSlider, QComboBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from gui.utils.timecode import frames_to_timecode


class ProgramMonitorWidget(QWidget):
    """Program Monitor for sequence playback, resolution preview, and shuttle navigation."""

    position_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fps = 60.0
        self.current_frame = 0
        self.total_sequence_frames = 1800 # Default 30 sec sequence
        self.is_playing = False
        self.playback_speed = 1.0 # 1.0 = normal, 2.0 = 2x, -1.0 = reverse (J-K-L shuttle)
        self.loop_enabled = False

        # Playback timer
        self.play_timer = QTimer(self)
        self.play_timer.setInterval(int(1000 / self.fps))
        self.play_timer.timeout.connect(self._on_timer_tick)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Sequence Title Header
        self.title_label = QLabel("SEQUENCE: Main Sequence (1920x1080 @ 60.00 fps)")
        self.title_label.setStyleSheet("color: #00ffcc; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.title_label)

        # Video Viewport Frame
        self.viewport = QFrame()
        self.viewport.setStyleSheet("background-color: #000000; border: 1px solid #282828;")
        self.viewport_layout = QVBoxLayout(self.viewport)

        self.placeholder_label = QLabel("PROGRAM MONITOR (SEQUENCE OUTPUT)")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #00ffcc; font-weight: bold; font-size: 13px;")
        self.viewport_layout.addWidget(self.placeholder_label)

        layout.addWidget(self.viewport, stretch=1)

        # Playhead Seek Slider
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, self.total_sequence_frames)
        self.seek_slider.setValue(0)
        self.seek_slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 6px; background: #222222; border-radius: 3px; }
            QSlider::sub-page:horizontal { background: #00ffcc; border-radius: 3px; }
            QSlider::handle:horizontal { background: #ffffff; width: 12px; margin-top: -3px; margin-bottom: -3px; border-radius: 6px; }
        """)
        self.seek_slider.valueChanged.connect(self._on_slider_moved)
        layout.addWidget(self.seek_slider)

        # Transport Bar
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(2, 2, 2, 2)
        controls_layout.setSpacing(4)

        # Resolution dropdown (Full, 1/2, 1/4)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Full", "1/2 Res", "1/4 Res"])
        self.quality_combo.setFixedWidth(85)
        controls_layout.addWidget(self.quality_combo)

        # Timecode display
        self.tc_label = QLabel("00:00:00:00")
        self.tc_label.setFont(QFont("Monospace", 11, QFont.Bold))
        self.tc_label.setStyleSheet("color: #00ffcc; background-color: #121212; padding: 4px 8px; border-radius: 3px;")
        controls_layout.addWidget(self.tc_label)

        # Transport buttons
        self.btn_shuttle_rev = QPushButton("J Rev")
        self.btn_shuttle_rev.setToolTip("Reverse Play (J)")
        self.btn_shuttle_rev.clicked.connect(self.shuttle_reverse)

        self.btn_shuttle_stop = QPushButton("K Stop")
        self.btn_shuttle_stop.setToolTip("Pause / Stop (K)")
        self.btn_shuttle_stop.clicked.connect(self.shuttle_stop)

        self.btn_shuttle_fwd = QPushButton("L Play")
        self.btn_shuttle_fwd.setToolTip("Forward Play (L)")
        self.btn_shuttle_fwd.clicked.connect(self.shuttle_forward)

        self.btn_loop = QPushButton("🔁")
        self.btn_loop.setToolTip("Toggle Loop Playback")
        self.btn_loop.setCheckable(True)
        self.btn_loop.toggled.connect(self.toggle_loop)

        for btn in (self.btn_shuttle_rev, self.btn_shuttle_stop, self.btn_shuttle_fwd, self.btn_loop):
            btn.setFixedHeight(24)
            controls_layout.addWidget(btn)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

    def shuttle_reverse(self):
        """J key: reverse playback or increase reverse speed."""
        if self.playback_speed > 0:
            self.playback_speed = -1.0
        else:
            self.playback_speed = max(-4.0, self.playback_speed * 2.0)
        self.start_playback()

    def shuttle_stop(self):
        """K key: stop playback."""
        self.playback_speed = 1.0
        self.stop_playback()

    def shuttle_forward(self):
        """L key: forward playback or increase forward speed."""
        if self.playback_speed < 0 or not self.is_playing:
            self.playback_speed = 1.0
        else:
            self.playback_speed = min(4.0, self.playback_speed * 2.0)
        self.start_playback()

    def start_playback(self):
        self.is_playing = True
        interval = max(5, int(1000 / (self.fps * abs(self.playback_speed))))
        self.play_timer.setInterval(interval)
        self.play_timer.start()

    def stop_playback(self):
        self.is_playing = False
        self.play_timer.stop()

    def toggle_loop(self, checked: bool):
        self.loop_enabled = checked

    def seek_to_frame(self, frame: int):
        self.current_frame = max(0, min(self.total_sequence_frames, frame))
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(self.current_frame)
        self.seek_slider.blockSignals(False)
        self.tc_label.setText(frames_to_timecode(self.current_frame, self.fps))
        self.position_changed.emit(self.current_frame)

    def _on_slider_moved(self, value: int):
        self.current_frame = value
        self.tc_label.setText(frames_to_timecode(self.current_frame, self.fps))
        self.position_changed.emit(self.current_frame)

    def _on_timer_tick(self):
        step = 1 if self.playback_speed > 0 else -1
        next_frame = self.current_frame + step

        if next_frame >= self.total_sequence_frames:
            if self.loop_enabled:
                self.seek_to_frame(0)
            else:
                self.shuttle_stop()
        elif next_frame < 0:
            if self.loop_enabled:
                self.seek_to_frame(self.total_sequence_frames)
            else:
                self.shuttle_stop()
        else:
            self.seek_to_frame(next_frame)
