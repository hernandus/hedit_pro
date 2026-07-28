"""
Source Monitor Widget for Hedit Pro.
Supports clip preview, seek slider, In/Out range marking, timecode display, and Insert/Overwrite to Timeline.
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSlider, QStyle
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor

from gui.utils.timecode import frames_to_timecode


class SourceMonitorWidget(QWidget):
    """Source Monitor for loading raw media clips, setting In/Out marks, and auditioning."""

    insert_to_timeline = Signal(dict)    # Emits clip metadata + in/out range
    overwrite_to_timeline = Signal(dict) # Emits clip metadata + in/out range

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fps = 60.0
        self.current_frame = 0
        self.total_frames = 600 # Default 10 seconds at 60fps
        self.mark_in = 0
        self.mark_out = self.total_frames
        self.is_playing = False
        self.clip_data = None

        # Playback timer
        self.play_timer = QTimer(self)
        self.play_timer.setInterval(int(1000 / self.fps))
        self.play_timer.timeout.connect(self._on_timer_tick)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Clip Title Header
        self.title_label = QLabel("No Clip Loaded")
        self.title_label.setStyleSheet("color: #888888; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.title_label)

        # Video Viewport Frame
        self.viewport = QFrame()
        self.viewport.setStyleSheet("background-color: #000000; border: 1px solid #282828;")
        self.viewport_layout = QVBoxLayout(self.viewport)
        
        self.placeholder_label = QLabel("DRAG MEDIA HERE OR DOUBLE CLICK IN PROJECT PANEL")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #444444; font-weight: bold; font-size: 12px;")
        self.viewport_layout.addWidget(self.placeholder_label)

        layout.addWidget(self.viewport, stretch=1)

        # Playhead Seek Slider
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, self.total_frames)
        self.seek_slider.setValue(0)
        self.seek_slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 6px; background: #222222; border-radius: 3px; }
            QSlider::sub-page:horizontal { background: #2680eb; border-radius: 3px; }
            QSlider::handle:horizontal { background: #00ffcc; width: 12px; margin-top: -3px; margin-bottom: -3px; border-radius: 6px; }
        """)
        self.seek_slider.valueChanged.connect(self._on_slider_moved)
        layout.addWidget(self.seek_slider)

        # Timecode & Controls Bar
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(2, 2, 2, 2)
        controls_layout.setSpacing(4)

        # Timecode display
        self.tc_label = QLabel("00:00:00:00")
        self.tc_label.setFont(QFont("Monospace", 10, QFont.Bold))
        self.tc_label.setStyleSheet("color: #2680eb; background-color: #121212; padding: 3px 6px; border-radius: 3px;")
        controls_layout.addWidget(self.tc_label)

        # Transport & Marking Buttons
        self.btn_mark_in = QPushButton("[ In")
        self.btn_mark_in.setToolTip("Mark In (I)")
        self.btn_mark_in.clicked.connect(self.set_mark_in)

        self.btn_mark_out = QPushButton("Out ]")
        self.btn_mark_out.setToolTip("Mark Out (O)")
        self.btn_mark_out.clicked.connect(self.set_mark_out)

        self.btn_step_back = QPushButton("⏮")
        self.btn_step_back.clicked.connect(self.step_back)

        self.btn_play = QPushButton("▶")
        self.btn_play.clicked.connect(self.toggle_play)

        self.btn_step_forward = QPushButton("⏭")
        self.btn_step_forward.clicked.connect(self.step_forward)

        self.btn_insert = QPushButton(", Insert")
        self.btn_insert.setToolTip("Insert clip to timeline (,) ")
        self.btn_insert.setStyleSheet("background-color: #1d3c6a; color: #7cb5ec;")
        self.btn_insert.clicked.connect(self.do_insert)

        self.btn_overwrite = QPushButton(". Overwrite")
        self.btn_overwrite.setToolTip("Overwrite clip to timeline (.) ")
        self.btn_overwrite.setStyleSheet("background-color: #4a2828; color: #f08080;")
        self.btn_overwrite.clicked.connect(self.do_overwrite)

        for btn in (self.btn_mark_in, self.btn_mark_out, self.btn_step_back, self.btn_play, self.btn_step_forward, self.btn_insert, self.btn_overwrite):
            btn.setFixedHeight(24)
            controls_layout.addWidget(btn)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

    def load_clip(self, file_path: str, duration_frames: int = 600, fps: float = 60.0):
        """Load a media clip into the Source Monitor."""
        self.clip_data = {
            "path": file_path,
            "name": os.path.basename(file_path),
            "duration": duration_frames,
            "fps": fps
        }
        self.fps = fps
        self.total_frames = duration_frames
        self.current_frame = 0
        self.mark_in = 0
        self.mark_out = self.total_frames

        self.title_label.setText(f"SOURCE: {self.clip_data['name']} ({frames_to_timecode(self.total_frames, self.fps)})")
        self.placeholder_label.setText(f"MEDIA PREVIEW: {self.clip_data['name']}")
        self.placeholder_label.setStyleSheet("color: #2680eb; font-weight: bold; font-size: 13px;")

        self.seek_slider.setRange(0, self.total_frames)
        self.seek_slider.setValue(0)
        self.update_timecode_display()

    def set_mark_in(self):
        self.mark_in = self.current_frame
        if self.mark_out <= self.mark_in:
            self.mark_out = self.total_frames
        self.update_timecode_display()

    def set_mark_out(self):
        self.mark_out = self.current_frame
        if self.mark_in >= self.mark_out:
            self.mark_in = 0
        self.update_timecode_display()

    def toggle_play(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.btn_play.setText("⏸")
            self.play_timer.start()
        else:
            self.btn_play.setText("▶")
            self.play_timer.stop()

    def step_back(self):
        self.seek_to_frame(max(0, self.current_frame - 1))

    def step_forward(self):
        self.seek_to_frame(min(self.total_frames, self.current_frame + 1))

    def seek_to_frame(self, frame: int):
        self.current_frame = frame
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(frame)
        self.seek_slider.blockSignals(False)
        self.update_timecode_display()

    def _on_slider_moved(self, value: int):
        self.current_frame = value
        self.update_timecode_display()

    def _on_timer_tick(self):
        if self.current_frame >= self.total_frames:
            self.seek_to_frame(self.mark_in)
        else:
            self.seek_to_frame(self.current_frame + 1)

    def update_timecode_display(self):
        tc = frames_to_timecode(self.current_frame, self.fps)
        in_tc = frames_to_timecode(self.mark_in, self.fps)
        out_tc = frames_to_timecode(self.mark_out, self.fps)
        self.tc_label.setText(f"{tc}  [In: {in_tc} | Out: {out_tc}]")

    def do_insert(self):
        if self.clip_data:
            payload = dict(self.clip_data)
            payload["mark_in"] = self.mark_in
            payload["mark_out"] = self.mark_out
            self.insert_to_timeline.emit(payload)

    def do_overwrite(self):
        if self.clip_data:
            payload = dict(self.clip_data)
            payload["mark_in"] = self.mark_in
            payload["mark_out"] = self.mark_out
            self.overwrite_to_timeline.emit(payload)
