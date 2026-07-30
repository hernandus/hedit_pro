"""
Multi-Track Timeline Canvas Widget for Hedit Pro.
High-performance QGraphicsView timeline renderer supporting NLE tools (V, C, B, Y, U), magnetic snapping, audio waveforms, and track headers.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsLineItem,
    QGraphicsTextItem, QFrame, QSplitter, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QPolygonF, QPainterPath

from PySide6.QtCore import QSize

from core.timeline_model import SequenceModel, ClipItem
from core.cache import CacheManager
from gui.widgets.timeline.track_header import TrackHeaderWidget
from gui.utils.timecode import frames_to_timecode


class CompactGraphicsView(QGraphicsView):
    """QGraphicsView with a compact sizeHint so it never forces parent dock to a large minimum height."""
    def sizeHint(self):
        return QSize(200, 40)
    def minimumSizeHint(self):
        return QSize(100, 40)


class CompactScrollArea(QScrollArea):
    """QScrollArea with a compact sizeHint so it never forces parent dock to a large minimum height."""
    def sizeHint(self):
        return QSize(140, 40)
    def minimumSizeHint(self):
        return QSize(140, 40)
    def wheelEvent(self, event):
        # Redirect mouse wheel event to vertical scrollbar even when hidden
        delta = event.angleDelta().y()
        if delta != 0:
            val = self.verticalScrollBar().value()
            self.verticalScrollBar().setValue(val - (delta // 2))
            event.accept()
        else:
            super().wheelEvent(event)


class ClipGraphicsItem(QGraphicsRectItem):
    """Visual graphics item representing a single clip on the timeline with waveform rendering."""

    def __init__(self, clip: ClipItem, pixels_per_frame: float = 2.0, num_video_tracks: int = 5, parent=None):
        self.clip = clip
        self.pixels_per_frame = pixels_per_frame
        self.num_video_tracks = num_video_tracks

        width = clip.duration * pixels_per_frame
        height = 26 # Height of clip block inside 26px track lane

        super().__init__(0, 0, width, height, parent)

        # Flags & Style
        self.setFlags(
            QGraphicsRectItem.ItemIsSelectable |
            QGraphicsRectItem.ItemIsMovable |
            QGraphicsRectItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

        base_color = QColor(clip.color)
        self.setBrush(QBrush(base_color))
        self.setPen(QPen(QColor("#141414"), 1))

        # Clip Title Label inside block
        self.text_item = QGraphicsTextItem(clip.name, self)
        self.text_item.setDefaultTextColor(QColor("#ffffff"))
        self.text_item.setFont(QFont("Inter", 8, QFont.Bold))
        self.text_item.setPos(4, 2)

        self.update_position()

    def update_position(self):
        x = self.clip.start_frame * self.pixels_per_frame
        if not self.clip.is_audio:
            # 27px pitch per video track (1px top line + 26px lane)
            y = (self.clip.track_index * 27) + 1
        else:
            # Separator after video tracks + 4px gap + 27px pitch per audio track
            sep_y = self.num_video_tracks * 27
            y = sep_y + 4 + (self.clip.track_index * 27)

        self.setPos(x, y)

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)

        w = self.rect().width()
        h = self.rect().height()

        # Small White Marker Tick on Top-Left Edge (Premiere Pro clip style)
        if not self.clip.is_audio:
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.setPen(Qt.NoPen)
            painter.drawRect(0, 0, 3, 5)

        # Render Audio Peak Waveform if audio clip
        if self.clip.is_audio:
            cache_mgr = CacheManager()
            peaks = cache_mgr.get_audio_peaks(self.clip.file_path)
            mid_y = h / 2.0

            painter.setPen(QPen(QColor("#a5d6a7"), 1))
            num_peaks = len(peaks)
            if num_peaks > 0:
                dx = w / float(num_peaks)
                for i in range(num_peaks - 1):
                    x1 = i * dx
                    x2 = (i + 1) * dx
                    amp1 = peaks[i] * (h / 2.5)
                    amp2 = peaks[i + 1] * (h / 2.5)
                    painter.drawLine(x1, mid_y - amp1, x2, mid_y - amp2)
                    painter.drawLine(x1, mid_y + amp1, x2, mid_y + amp2)

        if self.isSelected():
            painter.setPen(QPen(QColor("#00ffcc"), 2))
            painter.drawRect(self.rect())


class TimelineCanvasWidget(QWidget):
    """Timeline Editor View with multi-track support, playhead, and zoom controls."""

    playhead_moved = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = SequenceModel()
        self.pixels_per_frame = 2.0 # Zoom level
        self.active_tool = "V" # "V" = Select, "C" = Razor, "B" = Ripple
        self.snapping_enabled = True
        self.tool_buttons = {}

        self.init_ui()

    def init_ui(self):
        self.setMinimumHeight(40)
        from PySide6.QtWidgets import QLayout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setSizeConstraint(QLayout.SetNoConstraint)

        # Timeline Header Controls (Timecode readout, Tools & Zoom)
        header = QFrame()
        header.setMaximumHeight(32)
        header.setMinimumHeight(0)
        header.setStyleSheet("background-color: #242424; border-bottom: 1px solid #2b2b2b;")
        header_layout = QHBoxLayout(header)
        header_layout.setSizeConstraint(QLayout.SetNoConstraint)
        header_layout.setContentsMargins(8, 2, 8, 2)
        header_layout.setSpacing(4)

        # Timecode Readout Display (00:00:47:20 cyan readout matching reference PNG)
        self.timecode_display = QLabel("00:00:00:00")
        self.timecode_display.setFixedWidth(130)
        self.timecode_display.setFont(QFont("Monospace", 11, QFont.Bold))
        self.timecode_display.setStyleSheet("color: #00aaff; font-weight: bold; background: transparent;")
        header_layout.addWidget(self.timecode_display)

        header_layout.addStretch()

        # Zoom Controls
        self.zoom_label = QLabel("Zoom:")
        self.zoom_label.setStyleSheet("color: #888888;")
        header_layout.addWidget(self.zoom_label)

        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        self.btn_zoom_in.clicked.connect(self.zoom_in)

        for btn in (self.btn_zoom_out, self.btn_zoom_in):
            btn.setFixedSize(24, 24)
            header_layout.addWidget(btn)

        layout.addWidget(header)

        # Main Layout: Track Headers (Left, Fixed 140px) | Canvas View (Right, Expanding)
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Track Headers Container (Dynamic height based on sequence track count)
        self.headers_container = QWidget()
        self.headers_container.setFixedWidth(140)
        self.headers_container.setStyleSheet("background-color: #1a1a1a;")
        self.headers_layout = QVBoxLayout(self.headers_container)
        self.headers_layout.setContentsMargins(0, 0, 0, 0)
        self.headers_layout.setSpacing(0)

        # Build track headers for Video (V5, V4, V3, V2, V1)
        self.track_headers = []
        for i, track in enumerate(self.model.video_tracks):
            # Set default target state: V1 active, V2-V5 inactive matching reference PNG
            is_target = (track.name == "V1")
            h = TrackHeaderWidget(track.name, is_audio=False, is_target=is_target, track_index=i)
            h.setFixedHeight(27)
            self.headers_layout.addWidget(h)
            self.track_headers.append(h)

        # 4px Separator gap between Video and Audio headers (matches canvas sep_y blue line)
        self.sep_gap = QFrame()
        self.sep_gap.setFixedHeight(4)
        self.sep_gap.setStyleSheet("background-color: #2680eb; border: none;")
        self.headers_layout.addWidget(self.sep_gap)

        # Build track headers for Audio (A1, A2, A3)
        for i, track in enumerate(self.model.audio_tracks):
            # Set default target state: A1, A2 active, A3 inactive
            is_target = (track.name in ("A1", "A2"))
            h = TrackHeaderWidget(track.name, is_audio=True, is_target=is_target, track_index=i)
            h.setFixedHeight(27)
            self.headers_layout.addWidget(h)
            self.track_headers.append(h)

        self.headers_scroll = CompactScrollArea()
        self.headers_scroll.setFixedWidth(140)
        self.headers_scroll.setMinimumHeight(40)
        self.headers_scroll.setWidgetResizable(False)
        self.headers_scroll.setFrameShape(QFrame.NoFrame)
        self.headers_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.headers_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.headers_scroll.setStyleSheet("background-color: #1a1a1a; border-right: 1px solid #2b2b2b; border-top: none; border-bottom: none; border-left: none; padding: 0px; margin: 0px;")
        self.headers_scroll.setWidget(self.headers_container)

        content_layout.addWidget(self.headers_scroll)

        # Graphics Scene & View for Timeline Tracks
        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush(QBrush(QColor("#181818")))

        self.view = CompactGraphicsView(self.scene)
        self.view.setMinimumHeight(40)
        self.view.setFrameShape(QFrame.NoFrame)
        self.view.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.view.setStyleSheet("border: none; background-color: #181818;")
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.mousePressEvent = self._on_view_mouse_press

        # Bi-directional sync of vertical scrolling between graphics view and track headers
        self.view.verticalScrollBar().valueChanged.connect(self.headers_scroll.verticalScrollBar().setValue)
        self.headers_scroll.verticalScrollBar().valueChanged.connect(self.view.verticalScrollBar().setValue)

        content_layout.addWidget(self.view, stretch=1)

        layout.addLayout(content_layout)

        # Draw initial background & demo clips
        self.refresh_timeline()

    def set_active_tool(self, tool_code: str):
        self.active_tool = tool_code
        for code, btn in self.tool_buttons.items():
            btn.setChecked(code == tool_code)

    def toggle_snapping(self, enabled: bool):
        self.snapping_enabled = enabled

    def zoom_in(self):
        self.pixels_per_frame = min(10.0, self.pixels_per_frame * 1.25)
        self.refresh_timeline()

    def zoom_out(self):
        self.pixels_per_frame = max(0.5, self.pixels_per_frame / 1.25)
        self.refresh_timeline()

    def refresh_timeline(self):
        """Redraw track background lanes, clips, playhead, and update dynamic sequence bounds."""
        num_video = len(self.model.video_tracks)
        num_audio = len(self.model.audio_tracks)
        track_pitch = 27
        lane_h = 26
        total_h = (num_video * track_pitch) + 4 + (num_audio * track_pitch)

        # Update dynamic header container size
        if hasattr(self, 'headers_container') and self.headers_container:
            self.headers_container.setFixedSize(140, total_h)

        self.scene.clear()
        self.scene.setSceneRect(0, 0, 8000, total_h)

        # Video tracks (V5, V4, V3, V2, V1)
        for i in range(num_video):
            y_line = i * track_pitch
            # Top 1px line
            top_line = QGraphicsLineItem(0, y_line, 8000, y_line)
            top_line.setPen(QPen(QColor("#282828"), 1))
            self.scene.addItem(top_line)

            # 26px Lane background
            bg = QGraphicsRectItem(0, y_line + 1, 8000, lane_h)
            bg.setBrush(QBrush(QColor("#202020" if i % 2 == 0 else "#1c1c1c")))
            bg.setPen(Qt.NoPen)
            self.scene.addItem(bg)

        # Separator line between Video & Audio sections (4px solid blue rect matching left sep_gap)
        sep_y = num_video * track_pitch
        sep_bg = QGraphicsRectItem(0, sep_y, 8000, 4)
        sep_bg.setBrush(QBrush(QColor("#2680eb")))
        sep_bg.setPen(Qt.NoPen)
        self.scene.addItem(sep_bg)

        # Audio tracks (A1, A2, A3)
        for i in range(num_audio):
            y_lane = sep_y + 4 + (i * track_pitch)
            # 26px Lane background
            bg = QGraphicsRectItem(0, y_lane, 8000, lane_h)
            bg.setBrush(QBrush(QColor("#182026" if i % 2 == 0 else "#151c22")))
            bg.setPen(Qt.NoPen)
            self.scene.addItem(bg)

            # Bottom 1px line
            bottom_line = QGraphicsLineItem(0, y_lane + lane_h, 8000, y_lane + lane_h)
            bottom_line.setPen(QPen(QColor("#222d36"), 1))
            self.scene.addItem(bottom_line)

        # Render Clip Items
        for t in self.model.video_tracks + self.model.audio_tracks:
            for clip in t.clips:
                item = ClipGraphicsItem(clip, pixels_per_frame=self.pixels_per_frame, num_video_tracks=num_video)
                self.scene.addItem(item)

        # Update Timecode Display
        tc_str = frames_to_timecode(self.model.playhead_frame, fps=self.model.fps)
        if hasattr(self, 'timecode_display'):
            self.timecode_display.setText(tc_str)

        # Render Playhead (height strictly bounded to tracks total_h)
        px = self.model.playhead_frame * self.pixels_per_frame
        self.playhead = QGraphicsLineItem(px, 0, px, total_h)
        self.playhead.setPen(QPen(QColor("#00ffcc"), 2))
        self.scene.addItem(self.playhead)

    def minimumSizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(200, 40)

    def sizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(800, 80)

    def add_clip_to_timeline(self, clip_data: dict, track_index: int = 4):
        """Add clip from Source Monitor or Project Panel to timeline sequence."""
        file_path = clip_data.get("path", "")
        mark_in = clip_data.get("mark_in", 0)
        mark_out = clip_data.get("mark_out", 600)

        # Target position is playhead_frame
        start_frame = self.model.playhead_frame
        if self.snapping_enabled:
            start_frame = self.model.snap_frame(start_frame)

        self.model.add_clip_to_track(
            file_path=file_path,
            start_frame=start_frame,
            mark_in=mark_in,
            mark_out=mark_out,
            track_index=track_index
        )
        self.refresh_timeline()

    def _on_view_mouse_press(self, event):
        scene_pos = self.view.mapToScene(event.pos())
        click_frame = int(scene_pos.x() / self.pixels_per_frame)

        if self.snapping_enabled:
            click_frame = self.model.snap_frame(click_frame)

        num_video = len(self.model.video_tracks)
        sep_y = num_video * 27

        if self.active_tool == "C":
            if scene_pos.y() < sep_y:
                track_idx = int(scene_pos.y() // 27)
                is_audio = False
                real_track_idx = min(track_idx, num_video - 1)
            else:
                track_idx = int((scene_pos.y() - sep_y - 4) // 27)
                is_audio = True
                real_track_idx = min(track_idx, len(self.model.audio_tracks) - 1)

            if real_track_idx >= 0:
                self.model.razor_clip_at(real_track_idx, click_frame, is_audio=is_audio)
                self.refresh_timeline()
        else:
            self.model.playhead_frame = max(0, click_frame)
            self.playhead_moved.emit(self.model.playhead_frame)
            self.refresh_timeline()

        QGraphicsView.mousePressEvent(self.view, event)

