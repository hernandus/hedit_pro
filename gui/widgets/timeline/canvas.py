"""
Multi-Track Timeline Canvas Widget for Hedit Pro.
High-performance QGraphicsView timeline renderer supporting NLE tools (V, C, B, Y, U), magnetic snapping, and track headers.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsLineItem,
    QGraphicsTextItem, QFrame, QSplitter
)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QCursor

from core.timeline_model import SequenceModel, ClipItem
from gui.widgets.timeline.track_header import TrackHeaderWidget
from gui.utils.timecode import frames_to_timecode


class ClipGraphicsItem(QGraphicsRectItem):
    """Visual graphics item representing a single clip on the timeline."""

    def __init__(self, clip: ClipItem, pixels_per_frame: float = 2.0, parent=None):
        self.clip = clip
        self.pixels_per_frame = pixels_per_frame
        
        width = clip.duration * pixels_per_frame
        height = 44 # Height of clip block inside track lane

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
        self.setPen(QPen(QColor("#1a1a1a"), 1))

        # Clip Title Label inside block
        self.text_item = QGraphicsTextItem(clip.name, self)
        self.text_item.setDefaultTextColor(QColor("#ffffff"))
        self.text_item.setFont(QFont("Inter", 8, QFont.Bold))
        self.text_item.setPos(4, 4)

        self.update_position()

    def update_position(self):
        x = self.clip.start_frame * self.pixels_per_frame
        # Calculate Y according to track_index
        # Video tracks V3(0), V2(1), V1(2), then Audio A1(0), A2(1), A3(2)
        if not self.clip.is_audio:
            y = (self.clip.track_index * 48) + 2
        else:
            y = (3 * 48) + 8 + (self.clip.track_index * 48) + 2

        self.setPos(x, y)

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
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

        self.tool_buttons = {
            "V": self.btn_select_tool,
            "C": self.btn_razor_tool,
            "B": self.btn_ripple_tool
        }

        for tool_code, btn in self.tool_buttons.items():
            btn.setFixedHeight(24)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, t=tool_code: self.set_active_tool(t))
            header_layout.addWidget(btn)

        self.btn_select_tool.setChecked(True)

        # Magnetic Snapping Toggle (🧲)
        self.btn_snap = QPushButton("🧲 Snap")
        self.btn_snap.setFixedHeight(24)
        self.btn_snap.setCheckable(True)
        self.btn_snap.setChecked(True)
        self.btn_snap.toggled.connect(self.toggle_snapping)
        header_layout.addWidget(self.btn_snap)

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

        # Main Splitter: Track Headers (Left) | Canvas View (Right)
        splitter = QSplitter(Qt.Horizontal)
        
        # Track Headers Container
        headers_container = QWidget()
        headers_container.setFixedWidth(130)
        headers_container.setStyleSheet("background-color: #1a1a1a; border-right: 1px solid #2b2b2b;")
        headers_layout = QVBoxLayout(headers_container)
        headers_layout.setContentsMargins(0, 0, 0, 0)
        headers_layout.setSpacing(0)

        # Track Headers (V3, V2, V1, A1, A2, A3)
        for name, is_audio in [("V3", False), ("V2", False), ("V1", False), ("A1", True), ("A2", True), ("A3", True)]:
            h = TrackHeaderWidget(name, is_audio=is_audio)
            h.setFixedHeight(48)
            headers_layout.addWidget(h)
        headers_layout.addStretch()

        splitter.addWidget(headers_container)

        # Graphics Scene & View for Timeline Tracks
        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush(QBrush(QColor("#181818")))
        self.scene.setSceneRect(0, 0, 8000, 320)

        self.view = QGraphicsView(self.scene)
        self.view.setStyleSheet("border: none; background-color: #181818;")
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.mousePressEvent = self._on_view_mouse_press

        splitter.addWidget(self.view)
        splitter.setSizes([130, 1400])

        layout.addWidget(splitter)

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
        """Redraw track background lanes, clips, and playhead."""
        self.scene.clear()
        
        track_h = 48
        num_video = 3
        num_audio = 3

        # Video tracks (V3, V2, V1)
        for i in range(num_video):
            y = i * track_h
            bg = QGraphicsRectItem(0, y, 8000, track_h - 2)
            bg.setBrush(QBrush(QColor("#202020" if i % 2 == 0 else "#1c1c1c")))
            bg.setPen(QPen(QColor("#282828")))
            self.scene.addItem(bg)

        # Separator line
        sep_y = num_video * track_h
        sep_line = QGraphicsLineItem(0, sep_y + 3, 8000, sep_y + 3)
        sep_line.setPen(QPen(QColor("#2680eb"), 2))
        self.scene.addItem(sep_line)

        # Audio tracks (A1, A2, A3)
        for i in range(num_audio):
            y = sep_y + 8 + (i * track_h)
            bg = QGraphicsRectItem(0, y, 8000, track_h - 2)
            bg.setBrush(QBrush(QColor("#182026" if i % 2 == 0 else "#151c22")))
            bg.setPen(QPen(QColor("#222d36")))
            self.scene.addItem(bg)

        # Render Clip Items
        for t in self.model.video_tracks + self.model.audio_tracks:
            for clip in t.clips:
                item = ClipGraphicsItem(clip, pixels_per_frame=self.pixels_per_frame)
                self.scene.addItem(item)

        # Render Playhead
        px = self.model.playhead_frame * self.pixels_per_frame
        self.playhead = QGraphicsLineItem(px, 0, px, 300)
        self.playhead.setPen(QPen(QColor("#00ffcc"), 2))
        self.scene.addItem(self.playhead)

    def add_clip_to_timeline(self, clip_data: dict, track_index: int = 2):
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

        if self.active_tool == "C":
            # Razor Tool: Split clip under click
            track_idx = int(scene_pos.y() // 48)
            is_audio = track_idx >= 3
            real_track_idx = track_idx if not is_audio else (track_idx - 3)
            self.model.razor_clip_at(real_track_idx, click_frame, is_audio=is_audio)
            self.refresh_timeline()
        else:
            # Default Move Playhead
            self.model.playhead_frame = max(0, click_frame)
            self.playhead_moved.emit(self.model.playhead_frame)
            self.refresh_timeline()

        QGraphicsView.mousePressEvent(self.view, event)
