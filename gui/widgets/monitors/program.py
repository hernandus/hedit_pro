"""
Program Monitor Widget for Hedit Pro.
Active sequence preview, resolution scaling, shuttle playback, timecode synchronization, and timeline tools.
Matches Source Monitor design pixel for pixel with Fit/Full dropdowns, bounded control group, cyan timecode, and vector SVG scrubber.
"""

import os
import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QToolButton
)
from PySide6.QtCore import Qt, Signal, QTimer, QUrl, QSize
from PySide6.QtGui import QFont, QColor, QImage, QPixmap, QIcon
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from gui.utils.timecode import frames_to_timecode
from gui.widgets.monitors.viewport import VideoViewportWidget
from gui.widgets.monitors.scrubber import MonitorScrubberWidget
from gui.theme import COLOR_BG_DARK, COLOR_DIVIDER, COLOR_BG_HOVER
from core.logger import get_logger

logger = get_logger()

MONITOR_ICONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Interface_elements/monitor"))


class ProgramMonitorWidget(QWidget):
    """Program Monitor for sequence playback, resolution preview, shuttle navigation, and timeline editing."""

    position_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fps = 60.0
        self.current_frame = 0
        self.total_sequence_frames = 1800  # Default 30 sec sequence
        self.mark_in = 0
        self.mark_out = self.total_sequence_frames
        self.is_playing = False
        self.playback_speed = 1.0  # 1.0 = normal, 2.0 = 2x, -1.0 = reverse (J-K-L shuttle)
        self.loop_enabled = False
        self.has_mark_in = False
        self.has_mark_out = False

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

        self._init_icons()
        self.init_ui()

    def _init_icons(self):
        self.icon_mark_in = QIcon(os.path.join(MONITOR_ICONS_DIR, "monitor_icon_mark_in.svg"))
        self.icon_mark_out = QIcon(os.path.join(MONITOR_ICONS_DIR, "monitor_icon_mark_out.svg"))
        self.icon_play = QIcon(os.path.join(MONITOR_ICONS_DIR, "monitor_icon_play.svg"))
        self.icon_stop = QIcon(os.path.join(MONITOR_ICONS_DIR, "monitor_icon_stop.svg"))
        self.icon_play_loop_disabled = QIcon(os.path.join(MONITOR_ICONS_DIR, "monitor_icon_play_loop_disabled.svg"))
        self.icon_play_loop_enabled = QIcon(os.path.join(MONITOR_ICONS_DIR, "monitor_icon_play_loop_enabled.svg"))
        self.icon_insert = QIcon(os.path.join(MONITOR_ICONS_DIR, "monitor_icon_insert.svg"))
        self.icon_overwrite = QIcon(os.path.join(MONITOR_ICONS_DIR, "monitor_icon_overwrite.svg"))

    def init_ui(self):
        self.setStyleSheet(f"background-color: {COLOR_BG_DARK}; color: #D4D4D4;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        # 1. Sequence Title Header (Top Left: "Program: Sequence 01")
        self.title_label = QLabel("Program: Sequence 01")
        self.title_label.setStyleSheet("color: #A0A0A0; font-size: 11px; font-weight: normal;")
        main_layout.addWidget(self.title_label)

        # 2. Video Viewport Frame Canvas
        self.viewport = VideoViewportWidget(placeholder_text="PROGRAM MONITOR (SEQUENCE OUTPUT)")
        main_layout.addWidget(self.viewport, stretch=1)

        # 3. Controls Layout Row (Fit dropdown | Bounded Controls Group | Cyan TC | Full dropdown)
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 4, 0, 4)
        controls_layout.setSpacing(8)

        arrow_icon_path = os.path.join(MONITOR_ICONS_DIR, "monitor_icon_arrow_down.svg").replace("\\", "/")
        combo_qss = f"""
            QComboBox {{
                background-color: #181818;
                color: #A0A0A0;
                border: 1px solid #2B2B2B;
                border-radius: 3px;
                padding-left: 4px;
                padding-right: 12px;
                font-size: 11px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 10px;
                border: none;
                margin-right: 2px;
            }}
            QComboBox::down-arrow {{
                image: url('{arrow_icon_path}');
                width: 8px;
                height: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #181818;
                color: #D4D4D4;
                selection-background-color: #2F2F2F;
            }}
        """

        # Left: Fit Dropdown
        self.combo_fit = QComboBox()
        self.combo_fit.addItems(["Fit", "25%", "50%", "75%", "100%", "150%", "200%"])
        self.combo_fit.setFixedSize(62, 24)
        self.combo_fit.setStyleSheet(combo_qss)
        controls_layout.addWidget(self.combo_fit)

        controls_layout.addStretch(1)

        # Center: Bounded Action Group Frame ({ 00:00:30:00 } ▶ 📥 📤)
        center_frame = QFrame()
        center_frame.setStyleSheet("""
            QFrame {
                background-color: #181818;
                border: 1px solid #2B2B2B;
                border-radius: 3px;
            }
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 2px;
                padding: 0px;
            }
            QToolButton:hover {
                background-color: #282828;
            }
            QToolButton:pressed {
                background-color: #333333;
            }
        """)
        center_layout = QHBoxLayout(center_frame)
        center_layout.setContentsMargins(6, 2, 6, 2)
        center_layout.setSpacing(6)

        # Mark In
        self.btn_mark_in = QToolButton()
        self.btn_mark_in.setIcon(self.icon_mark_in)
        self.btn_mark_in.setFixedSize(20, 20)
        self.btn_mark_in.setIconSize(QSize(15, 15))
        self.btn_mark_in.setToolTip("Mark In (I)")
        self.btn_mark_in.clicked.connect(self.set_mark_in)
        center_layout.addWidget(self.btn_mark_in)

        # Duration / Range Timecode Readout inside center box
        self.range_tc_label = QLabel("00:00:00:00")
        self.range_tc_label.setFont(QFont("Monospace", 9))
        self.range_tc_label.setStyleSheet("color: #A0A0A0; padding: 0 4px; border: none; background: transparent;")
        center_layout.addWidget(self.range_tc_label)

        # Mark Out
        self.btn_mark_out = QToolButton()
        self.btn_mark_out.setIcon(self.icon_mark_out)
        self.btn_mark_out.setFixedSize(20, 20)
        self.btn_mark_out.setIconSize(QSize(15, 15))
        self.btn_mark_out.setToolTip("Mark Out (O)")
        self.btn_mark_out.clicked.connect(self.set_mark_out)
        center_layout.addWidget(self.btn_mark_out)

        # Play / Pause
        self.btn_play = QToolButton()
        self.btn_play.setIcon(self.icon_play)
        self.btn_play.setFixedSize(20, 20)
        self.btn_play.setIconSize(QSize(15, 15))
        self.btn_play.setToolTip("Play/Pause (Space)")
        self.btn_play.clicked.connect(self.toggle_play_state)
        center_layout.addWidget(self.btn_play)

        # Loop Playback (right of Play)
        self.btn_loop = QToolButton()
        self.btn_loop.setIcon(self.icon_play_loop_disabled)
        self.btn_loop.setFixedSize(20, 20)
        self.btn_loop.setIconSize(QSize(15, 15))
        self.btn_loop.setToolTip("Loop Playback (OFF)")
        self.btn_loop.clicked.connect(self.toggle_loop)
        center_layout.addWidget(self.btn_loop)

        # Spacing between Play and Insert
        center_layout.addSpacing(12)

        # Insert
        self.btn_insert = QToolButton()
        self.btn_insert.setIcon(self.icon_insert)
        self.btn_insert.setFixedSize(20, 20)
        self.btn_insert.setIconSize(QSize(20, 20))
        self.btn_insert.setToolTip("Insert clip to timeline (,) ")
        center_layout.addWidget(self.btn_insert)

        # Equal Spacing between Insert and Overwrite
        center_layout.addSpacing(12)

        # Overwrite
        self.btn_overwrite = QToolButton()
        self.btn_overwrite.setIcon(self.icon_overwrite)
        self.btn_overwrite.setFixedSize(20, 20)
        self.btn_overwrite.setIconSize(QSize(20, 20))
        self.btn_overwrite.setToolTip("Overwrite clip to timeline (.) ")
        center_layout.addWidget(self.btn_overwrite)

        controls_layout.addWidget(center_frame)

        # Spacing between action frame and current timecode
        controls_layout.addSpacing(16)

        # Cyan Main Current Timecode Readout
        self.tc_label = QLabel("00:00:00:00")
        self.tc_label.setFont(QFont("Monospace", 10, QFont.Bold))
        self.tc_label.setStyleSheet("color: #00A8FF; background: transparent; padding: 2px 4px;")
        controls_layout.addWidget(self.tc_label)

        controls_layout.addStretch(1)

        # Right: Proxies Toggle Button (Fixed-width borderless text container)
        self.btn_proxy = QPushButton("PROXIES ON")
        self.btn_proxy.setCheckable(True)
        self.btn_proxy.setChecked(True)
        self.btn_proxy.setCursor(Qt.PointingHandCursor)
        self.btn_proxy.setFixedSize(80, 24)
        self._update_proxy_btn_style()
        self.btn_proxy.toggled.connect(self._on_proxy_toggled)
        controls_layout.addWidget(self.btn_proxy)

        controls_layout.addSpacing(4)

        # Right: Full Dropdown
        self.combo_full = QComboBox()
        self.combo_full.addItems(["Full", "1/2", "1/4", "1/8"])
        self.combo_full.setFixedSize(56, 24)
        self.combo_full.setStyleSheet(combo_qss)
        controls_layout.addWidget(self.combo_full)

        main_layout.addLayout(controls_layout)

        # 4. Scrubber Track (Dashed line + In/Out shaded range + Cyan playhead)
        self.scrubber = MonitorScrubberWidget()
        self.scrubber.seek_requested.connect(self.seek_to_frame)
        self.scrubber.set_range(self.total_sequence_frames)
        self.scrubber.set_marks(self.mark_in, self.mark_out)
        main_layout.addWidget(self.scrubber)

        self._update_range_display()

    def _on_proxy_toggled(self, checked: bool):
        """Toggle PROXIES ON / PROXIES OFF state."""
        self.btn_proxy.setText("PROXIES ON" if checked else "PROXIES OFF")
        self._update_proxy_btn_style()
        logger.info(f"[PROGRAM MONITOR] Proxy mode set to: {'ON' if checked else 'OFF'}")

    def _update_proxy_btn_style(self):
        """Set typography style and colors for proxy toggle text button."""
        color = "#00A8FF" if self.btn_proxy.isChecked() else "#4B4B4B"
        hover_color = "#33BAFF" if self.btn_proxy.isChecked() else "#666666"
        self.btn_proxy.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {color};
                font-size: 11px;
                font-weight: bold;
                text-align: left;
                padding: 0px 2px;
            }}
            QPushButton:hover {{
                color: {hover_color};
            }}
        """)

    def set_sequence_model(self, sequence_model):
        """Connect active timeline sequence model."""
        self.sequence_model = sequence_model

    def set_mark_in(self):
        """Set In mark at current playhead position."""
        self.mark_in = self.current_frame
        self.has_mark_in = True
        if self.mark_out < self.mark_in:
            self.mark_out = self.total_sequence_frames
            self.has_mark_out = False
        self.scrubber.set_marks(self.mark_in, self.mark_out)
        self._update_range_display()
        logger.info(f"[PROGRAM MONITOR] Set Mark In at frame {self.mark_in}")

    def set_mark_out(self):
        """Set Out mark at current playhead position."""
        self.mark_out = max(self.mark_in, self.current_frame)
        self.has_mark_out = True
        self.scrubber.set_marks(self.mark_in, self.mark_out)
        self._update_range_display()
        logger.info(f"[PROGRAM MONITOR] Set Mark Out at frame {self.mark_out}")

        # If loop is ON and both marks exist during active playback, immediately jump to mark_in and loop
        if self.is_playing and self.loop_enabled and self.has_mark_in and self.has_mark_out:
            self.seek_to_frame(self.mark_in)
            if self.playback_speed == 1.0 and self.current_audio_path:
                self.player.play()

    def _update_range_display(self):
        """Update center range duration timecode display."""
        duration_frames = max(0, self.mark_out - self.mark_in)
        tc_str = frames_to_timecode(duration_frames, self.fps)
        self.range_tc_label.setText(tc_str)

    def toggle_play_state(self):
        """Toggle play/pause state when play button is clicked."""
        if self.is_playing:
            self.shuttle_stop()
        else:
            self.shuttle_forward()

    def toggle_play(self):
        """Alias for toggle_play_state to fulfill PlaybackTarget protocol."""
        self.toggle_play_state()

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
        """Start or resume playback."""
        self.is_playing = True
        self.btn_play.setIcon(self.icon_stop)
        interval = max(5, int(1000 / (self.fps * abs(self.playback_speed))))
        self.play_timer.setInterval(interval)

        if self.current_audio_path and self.playback_speed == 1.0:
            self.player.play()

        self.play_timer.start()

    def stop_playback(self):
        """Stop or pause playback."""
        self.is_playing = False
        self.btn_play.setIcon(self.icon_play)
        self.player.pause()
        self.play_timer.stop()

    def toggle_loop(self, checked: bool = None):
        """Toggle loop playback mode."""
        if checked is None or (isinstance(checked, bool) and self.sender() is not None):
            self.loop_enabled = not self.loop_enabled
        else:
            self.loop_enabled = checked

        if self.loop_enabled:
            self.btn_loop.setIcon(self.icon_play_loop_enabled)
            self.btn_loop.setToolTip("Loop Playback (ON)")
        else:
            self.btn_loop.setIcon(self.icon_play_loop_disabled)
            self.btn_loop.setToolTip("Loop Playback (OFF)")

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
        """Seek playhead to specific frame index."""
        self.current_frame = max(0, min(self.total_sequence_frames, frame))
        self.scrubber.blockSignals(True)
        self.scrubber.set_frame(self.current_frame)
        self.scrubber.blockSignals(False)
        self.tc_label.setText(frames_to_timecode(self.current_frame, self.fps))
        self.render_sequence_frame(self.current_frame, force_seek=True)
        self.position_changed.emit(self.current_frame)

    def _on_timer_tick(self):
        """Advance playhead on each timer tick with conditional mark-based loop."""
        step = 1 if self.playback_speed > 0 else -1
        next_frame = self.current_frame + step

        has_in_out = self.has_mark_in and self.has_mark_out
        limit_out = self.mark_out if (self.loop_enabled and has_in_out) else self.total_sequence_frames
        limit_in = self.mark_in if (self.loop_enabled and has_in_out) else 0

        if next_frame >= limit_out:
            if self.loop_enabled and has_in_out:
                self.seek_to_frame(limit_in)
                if self.is_playing and self.playback_speed == 1.0 and self.current_audio_path:
                    self.player.play()
            else:
                self.shuttle_stop()
                self.seek_to_frame(limit_out)
        elif next_frame < limit_in:
            if self.loop_enabled and has_in_out:
                self.seek_to_frame(limit_out)
                if self.is_playing and self.playback_speed == 1.0 and self.current_audio_path:
                    self.player.play()
            else:
                self.shuttle_stop()
                self.seek_to_frame(limit_in)
        else:
            self.current_frame = next_frame
            self.scrubber.blockSignals(True)
            self.scrubber.set_frame(self.current_frame)
            self.scrubber.blockSignals(False)
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
