"""
Program Monitor Widget for Hedit Pro.
Active sequence preview, resolution scaling, shuttle playback, and timecode synchronization.
"""

import os
import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSlider, QComboBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QUrl
from PySide6.QtGui import QFont, QImage, QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from gui.utils.timecode import frames_to_timecode
from gui.widgets.monitors.viewport import VideoViewportWidget


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

        self.sequence_model = None
        self.caps = {}
        self.current_audio_path = None

        # Synchronized Audio Output Engine
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(1.0)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)

        # Playback timer (Microsecond precise timer)
        self.play_timer = QTimer(self)
        self.play_timer.setTimerType(Qt.PreciseTimer)
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

        # Video Viewport Frame Canvas
        self.viewport = VideoViewportWidget(placeholder_text="PROGRAM MONITOR (SEQUENCE OUTPUT)")
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

    def set_sequence_model(self, sequence_model):
        self.sequence_model = sequence_model

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

        if self.current_audio_path and self.playback_speed == 1.0:
            self.player.play()

        self.play_timer.start()

    def stop_playback(self):
        self.is_playing = False
        self.player.pause()
        self.play_timer.stop()

    def toggle_loop(self, checked: bool):
        self.loop_enabled = checked

    def render_sequence_frame(self, frame_num: int, force_seek: bool = False):
        """Render active timeline sequence video frame at specified sequence frame index."""
        if not self.sequence_model:
            return

        active_clip = None
        # Check video tracks from top (V3, V2, V1)
        for track in self.sequence_model.video_tracks:
            clip = track.get_clip_at(frame_num)
            if clip:
                active_clip = clip
                break

        if active_clip and os.path.exists(active_clip.file_path):
            file_path = active_clip.file_path
            if self.current_audio_path != file_path:
                self.current_audio_path = file_path
                self.player.setSource(QUrl.fromLocalFile(file_path))

            if file_path not in self.caps:
                cap = cv2.VideoCapture(file_path)
                if cap.isOpened():
                    self.caps[file_path] = cap
            
            cap = self.caps.get(file_path)
            if cap and cap.isOpened():
                clip_frame = (frame_num - active_clip.start_frame) + active_clip.mark_in
                curr_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                if force_seek or curr_pos != clip_frame:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, clip_frame)
                    if self.is_playing and self.playback_speed == 1.0:
                        pos_ms = int((clip_frame / active_clip.fps) * 1000)
                        self.player.setPosition(pos_ms)
                
                ret, frame = cap.read()
                if ret and frame is not None:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_frame.shape
                    qimg = QImage(rgb_frame.data, w, h, w * ch, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(qimg)
                    self.viewport.set_pixmap(pixmap)
                    return

        # Gap or no clip
        self.player.pause()
        self.viewport.clear_video("PROGRAM MONITOR (EMPTY TIMELINE GAP)")

    def seek_to_frame(self, frame: int):
        self.current_frame = max(0, min(self.total_sequence_frames, frame))
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(self.current_frame)
        self.seek_slider.blockSignals(False)
        self.tc_label.setText(frames_to_timecode(self.current_frame, self.fps))
        self.render_sequence_frame(self.current_frame, force_seek=True)
        self.position_changed.emit(self.current_frame)

    def _on_slider_moved(self, value: int):
        if not self.is_playing:
            self.seek_to_frame(value)

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
            self.current_frame = next_frame
            self.seek_slider.blockSignals(True)
            self.seek_slider.setValue(self.current_frame)
            self.seek_slider.blockSignals(False)
            self.tc_label.setText(frames_to_timecode(self.current_frame, self.fps))
            self.render_sequence_frame(self.current_frame, force_seek=(self.playback_speed != 1.0))
            self.position_changed.emit(self.current_frame)

    def closeEvent(self, event):
        for cap in self.caps.values():
            if cap:
                cap.release()
        self.caps.clear()
        self.player.stop()
        super().closeEvent(event)




