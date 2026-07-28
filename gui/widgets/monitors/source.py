"""
Source Monitor Widget for Hedit Pro.
Supports clip preview, seek slider, In/Out range marking, timecode display, and Insert/Overwrite to Timeline.
Matches Premiere Pro mockup design with Fit/Full dropdowns, cyan timecode, and custom scrubber track.
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
from core.proxy import find_proxy_for_source

logger = get_logger()

MONITOR_ICONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Interface_elements/monitor"))


class SourceMonitorWidget(QWidget):
    """Source Monitor for loading raw media clips, setting In/Out marks, and auditioning."""

    insert_to_timeline = Signal(dict)    # Emits clip metadata + in/out range
    overwrite_to_timeline = Signal(dict) # Emits clip metadata + in/out range

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fps = 60.0
        self.current_frame = 0
        self.total_frames = 600  # Default 10 seconds at 60fps
        self.mark_in = 0
        self.mark_out = self.total_frames
        self.is_playing = False
        self.clip_data = None

        # Proxy state ─────────────────────────────────────────────────────────
        self.original_path: str | None = None   # path as imported by the user
        self.proxy_path: str | None = None       # detected proxy file (may be None)
        self.proxies_enabled: bool = True        # mirrors btn_proxy.isChecked()

        self.cap = None

        # Synchronized Audio Output Engine
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(1.0)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)

        # Playback timer
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
        self.icon_insert = QIcon(os.path.join(MONITOR_ICONS_DIR, "monitor_icon_insert.svg"))
        self.icon_overwrite = QIcon(os.path.join(MONITOR_ICONS_DIR, "monitor_icon_overwrite.svg"))

    def init_ui(self):
        self.setStyleSheet(f"background-color: {COLOR_BG_DARK}; color: #D4D4D4;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        # 1. Clip Title Header (Top Left: "Source: <clip_name>")
        self.title_label = QLabel("Source: No Clip Loaded")
        self.title_label.setStyleSheet("color: #A0A0A0; font-size: 11px; font-weight: normal;")
        main_layout.addWidget(self.title_label)

        # 2. Video Viewport Frame Canvas (with 'PROXIES ON' overlay badge)
        self.viewport = VideoViewportWidget(placeholder_text="DRAG MEDIA HERE OR DOUBLE CLICK IN PROJECT PANEL")
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

        # Center: Bounded Action Group Frame ({ 00:02:34:15 } ▶ 📥 📤)
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
        self.btn_play.clicked.connect(self.toggle_play)
        center_layout.addWidget(self.btn_play)

        # Spacing between Play and Insert
        center_layout.addSpacing(12)

        # Insert
        self.btn_insert = QToolButton()
        self.btn_insert.setIcon(self.icon_insert)
        self.btn_insert.setFixedSize(20, 20)
        self.btn_insert.setIconSize(QSize(20, 20))
        self.btn_insert.setToolTip("Insert clip to timeline (,) ")
        self.btn_insert.clicked.connect(self.do_insert)
        center_layout.addWidget(self.btn_insert)

        # Equal Spacing between Insert and Overwrite
        center_layout.addSpacing(12)

        # Overwrite
        self.btn_overwrite = QToolButton()
        self.btn_overwrite.setIcon(self.icon_overwrite)
        self.btn_overwrite.setFixedSize(20, 20)
        self.btn_overwrite.setIconSize(QSize(20, 20))
        self.btn_overwrite.setToolTip("Overwrite clip to timeline (.) ")
        self.btn_overwrite.clicked.connect(self.do_overwrite)
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
        main_layout.addWidget(self.scrubber)

    # ── Proxy toggle logic ────────────────────────────────────────────────────

    def _get_active_path(self) -> str | None:
        """
        Returns the path that should currently be decoded:
        - proxy file if proxies are enabled AND a proxy exists on disk
        - original file otherwise
        """
        if (
            self.proxies_enabled
            and self.proxy_path
            and os.path.exists(self.proxy_path)
        ):
            return self.proxy_path
        return self.original_path

    def _update_proxy_badge(self):
        """Syncs the viewport proxy badge to reflect current proxy state."""
        if not self.original_path:
            self.viewport.set_proxy_badge(None)
        elif self.proxies_enabled:
            if self.proxy_path and os.path.exists(self.proxy_path):
                self.viewport.set_proxy_badge("on")
            else:
                self.viewport.set_proxy_badge("missing")
        else:
            self.viewport.set_proxy_badge(None)

    def _switch_source(self, new_path: str):
        """
        Hot-swap the decode source (cv2 + QMediaPlayer) to *new_path*
        without resetting marks or current playhead position.
        """
        was_playing = self.is_playing
        if was_playing:
            self.play_timer.stop()
            self.player.pause()

        if self.cap:
            self.cap.release()
            self.cap = None

        self.cap = cv2.VideoCapture(new_path)
        self.player.setSource(QUrl.fromLocalFile(new_path))

        # Restore frame position in new source
        self.seek_to_frame(self.current_frame)

        if was_playing:
            pos_ms = int((self.current_frame / self.fps) * 1000)
            self.player.setPosition(pos_ms)
            self.player.play()
            self.play_timer.start()

        logger.info(f"[SOURCE MONITOR] Switched decode source → {new_path}")

    def _on_proxy_toggled(self, checked: bool):
        """Toggle PROXIES ON / PROXIES OFF — switches decode source live."""
        self.proxies_enabled = checked
        self.btn_proxy.setText("PROXIES ON" if checked else "PROXIES OFF")
        self._update_proxy_btn_style()

        if self.original_path:
            active = self._get_active_path()
            self._switch_source(active)
            self._update_proxy_badge()

        logger.info(f"[SOURCE MONITOR] Proxy mode → {'ON' if checked else 'OFF'} "
                    f"(proxy {'found' if self.proxy_path else 'not found'})")

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

    def load_clip(self, file_path: str, duration_frames: int = 600, fps: float = 60.0):
        """Load a media clip into the Source Monitor."""
        if self.cap:
            self.cap.release()
            self.cap = None

        # ── Proxy detection ───────────────────────────────────────────────────
        self.original_path = file_path
        self.proxy_path = find_proxy_for_source(file_path)
        if self.proxy_path:
            logger.info(f"[SOURCE MONITOR] Proxy found: {self.proxy_path}")
        else:
            logger.debug(f"[SOURCE MONITOR] No proxy found for: {file_path}")

        active_path = self._get_active_path()  # proxy or original per toggle state

        detected_fps = fps
        detected_frames = duration_frames

        if os.path.exists(file_path):  # always probe original for metadata
            probe = cv2.VideoCapture(file_path)
            if probe.isOpened():
                c_fps = probe.get(cv2.CAP_PROP_FPS)
                if c_fps and c_fps > 0:
                    detected_fps = float(c_fps)
                c_frames = int(probe.get(cv2.CAP_PROP_FRAME_COUNT))
                if c_frames and c_frames > 0:
                    detected_frames = c_frames
                logger.info(f"[SOURCE MONITOR] {detected_frames} frames @ {detected_fps:.2f} FPS")
            probe.release()

        # Open decode source (may be proxy)
        self.cap = cv2.VideoCapture(active_path)
        self.player.setSource(QUrl.fromLocalFile(active_path))
        self.player.setPosition(0)

        self.fps = detected_fps
        self.total_frames = detected_frames
        self.clip_data = {
            "path": file_path,          # always the original path for timeline
            "name": os.path.basename(file_path),
            "duration": self.total_frames,
            "fps": self.fps
        }
        self.current_frame = 0
        self.mark_in = 0
        self.mark_out = self.total_frames

        self.play_timer.setInterval(max(5, int(1000 / self.fps)))
        self.title_label.setText(f"Source: {self.clip_data['name']}")

        self.scrubber.set_range(self.total_frames)
        self.scrubber.set_marks(self.mark_in, self.mark_out)
        self.seek_to_frame(0)
        self.update_timecode_display()
        self._update_proxy_badge()

    def set_mark_in(self):
        self.mark_in = self.current_frame
        if self.mark_out <= self.mark_in:
            self.mark_out = self.total_frames
        self.scrubber.set_marks(self.mark_in, self.mark_out)
        self.update_timecode_display()

    def set_mark_out(self):
        self.mark_out = self.current_frame
        if self.mark_in >= self.mark_out:
            self.mark_in = 0
        self.scrubber.set_marks(self.mark_in, self.mark_out)
        self.update_timecode_display()

    def toggle_play(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.btn_play.setIcon(self.icon_stop)
            if self.cap and self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            pos_ms = int((self.current_frame / self.fps) * 1000)
            self.player.setPosition(pos_ms)
            self.player.play()
            self.play_timer.start()
        else:
            self.btn_play.setIcon(self.icon_play)
            self.player.pause()
            self.play_timer.stop()

    def step_back(self):
        self.seek_to_frame(max(0, self.current_frame - 1))

    def step_forward(self):
        self.seek_to_frame(min(self.total_frames, self.current_frame + 1))

    def seek_to_frame(self, frame: int):
        """Perform exact position seek for user scrubbing / step buttons."""
        self.current_frame = frame
        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ret, mat_frame = self.cap.read()
            if ret and mat_frame is not None:
                rgb_frame = cv2.cvtColor(mat_frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                qimg = QImage(rgb_frame.data, w, h, w * ch, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)
                self.viewport.set_pixmap(pixmap)

        pos_ms = int((frame / self.fps) * 1000)
        self.player.setPosition(pos_ms)

        self.scrubber.set_frame(frame)
        self.update_timecode_display()

    def _on_timer_tick(self):
        """Ultra-fast sequential frame playback with synced audio output."""
        if not self.cap or not self.cap.isOpened():
            return

        if self.current_frame >= self.total_frames or self.current_frame >= self.mark_out:
            self.seek_to_frame(self.mark_in)
            return

        ret, mat_frame = self.cap.read()
        if ret and mat_frame is not None:
            rgb_frame = cv2.cvtColor(mat_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            qimg = QImage(rgb_frame.data, w, h, w * ch, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            self.viewport.set_pixmap(pixmap)

            self.current_frame += 1
            self.scrubber.set_frame(self.current_frame)
            self.update_timecode_display()
        else:
            self.seek_to_frame(self.mark_in)

    def update_timecode_display(self):
        tc = frames_to_timecode(self.current_frame, self.fps)
        range_tc = frames_to_timecode(max(0, self.mark_out - self.mark_in), self.fps)
        self.tc_label.setText(tc)
        self.range_tc_label.setText(range_tc)

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

    def closeEvent(self, event):
        if self.cap:
            self.cap.release()
            self.cap = None
        self.player.stop()
        super().closeEvent(event)
