"""
Custom Monitor Scrubber Widget for Hedit Pro.
Draws dashed timeline track, shaded In/Out mark selection range, and cyan playhead indicator.
"""

from PySide6.QtWidgets import QWidget, QMenu
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtSvg import QSvgRenderer
import os

from gui.theme import COLOR_BG_DARK, COLOR_DIVIDER

MONITOR_ICONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Interface_elements/monitor"))


class MonitorScrubberWidget(QWidget):
    """Horizontal track slider showing dashed line, shaded In/Out range, and playhead arrow."""

    seek_requested = Signal(int)
    mark_in_changed = Signal(int)
    mark_out_changed = Signal(int)
    clear_marks_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(24)
        self.setMouseTracking(True)

        self.total_frames = 600
        self.current_frame = 0
        self.mark_in = 0
        self.mark_out = self.total_frames
        self.is_dragging = False
        self.drag_mode = None  # None, "in", "out", "playhead"

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Load SVG icon renderers
        self.renderer_mark_in = QSvgRenderer(os.path.join(MONITOR_ICONS_DIR, "monitor_icon_mark_in.svg"))
        self.renderer_mark_out = QSvgRenderer(os.path.join(MONITOR_ICONS_DIR, "monitor_icon_mark_out.svg"))
        self.renderer_playhead = QSvgRenderer(os.path.join(MONITOR_ICONS_DIR, "monitor_icon_playhead.svg"))

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #181818;
                color: #D4D4D4;
                border: 1px solid #2B2B2B;
                padding: 4px;
            }
            QMenu::item {
                padding: 4px 16px;
                font-size: 11px;
            }
            QMenu::item:selected {
                background-color: #282828;
                color: #00A8FF;
            }
        """)
        action_clear = menu.addAction("Clear In and Out")
        action_clear.triggered.connect(lambda: self.clear_marks_requested.emit())
        menu.exec(self.mapToGlobal(pos))

    def set_range(self, total_frames: int):
        self.total_frames = max(1, total_frames)
        self.update()

    def set_frame(self, current_frame: int):
        self.current_frame = max(0, min(current_frame, self.total_frames))
        self.update()

    def set_marks(self, mark_in: int, mark_out: int):
        self.mark_in = max(0, min(mark_in, self.total_frames))
        self.mark_out = max(self.mark_in, min(mark_out, self.total_frames))
        self.update()

    def _frame_from_pos(self, x: float) -> int:
        w = float(self.width())
        if w <= 0:
            return 0
        ratio = max(0.0, min(x / w, 1.0))
        return int(round(ratio * self.total_frames))

    def _get_hit_target(self, x: float) -> str:
        """Determines if mouse position hits Mark In handle, Mark Out handle, or track playhead."""
        w = float(self.width())
        if w <= 0 or self.total_frames <= 0:
            return "playhead"

        in_x = (float(self.mark_in) / float(self.total_frames)) * w
        out_x = (float(self.mark_out) / float(self.total_frames)) * w

        hit_margin = 8.0  # Tolerance margin around handles

        # Priority hit detection for In/Out handle grips
        if abs(x - in_x) <= hit_margin:
            return "in"
        if abs(x - out_x) <= hit_margin:
            return "out"

        return "playhead"

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            pos_x = event.position().x()
            self.drag_mode = self._get_hit_target(pos_x)
            frame = self._frame_from_pos(pos_x)

            if self.drag_mode == "in":
                new_in = max(0, min(frame, self.mark_out - 1))
                self.mark_in = new_in
                self.mark_in_changed.emit(new_in)
                self.seek_requested.emit(new_in)
            elif self.drag_mode == "out":
                new_out = max(self.mark_in + 1, min(frame, self.total_frames))
                self.mark_out = new_out
                self.mark_out_changed.emit(new_out)
                self.seek_requested.emit(new_out)
            else:
                self.seek_requested.emit(frame)

            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos_x = event.position().x()

        if not self.is_dragging:
            hit = self._get_hit_target(pos_x)
            if hit in ("in", "out"):
                self.setCursor(Qt.SizeHorCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        else:
            frame = self._frame_from_pos(pos_x)
            if self.drag_mode == "in":
                new_in = max(0, min(frame, self.mark_out - 1))
                if new_in != self.mark_in:
                    self.mark_in = new_in
                    self.mark_in_changed.emit(new_in)
                    self.seek_requested.emit(new_in)
                    self.update()
            elif self.drag_mode == "out":
                new_out = max(self.mark_in + 1, min(frame, self.total_frames))
                if new_out != self.mark_out:
                    self.mark_out = new_out
                    self.mark_out_changed.emit(new_out)
                    self.seek_requested.emit(new_out)
                    self.update()
            elif self.drag_mode == "playhead":
                self.seek_requested.emit(frame)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            self.drag_mode = None
            pos_x = event.position().x()
            hit = self._get_hit_target(pos_x)
            if hit in ("in", "out"):
                self.setCursor(Qt.SizeHorCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        delta = 1 if event.angleDelta().y() > 0 else -1
        new_frame = max(0, min(self.current_frame + delta, self.total_frames))
        self.seek_requested.emit(new_frame)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        track_y = h - 5.0

        # Background matching theme #1D1D1D
        painter.fillRect(self.rect(), QColor("#1D1D1D"))

        # 1. Dashed track line spanning full width near bottom
        dash_pen = QPen(QColor("#555555"), 1, Qt.DashLine)
        painter.setPen(dash_pen)
        painter.drawLine(QPointF(0, track_y), QPointF(w, track_y))

        # 2. In/Out Mark Shaded Region & Vector SVG Icons
        if self.total_frames > 0:
            in_x = (float(self.mark_in) / float(self.total_frames)) * w
            out_x = (float(self.mark_out) / float(self.total_frames)) * w

            # Shaded bar resting on top of dashed line, matching height and bounded inside brackets
            if out_x > in_x + 6.0:
                painter.fillRect(QRectF(in_x + 3.0, track_y - 14.0, out_x - in_x - 6.0, 14.0), QColor(60, 60, 60, 200))
            elif out_x > in_x:
                painter.fillRect(QRectF(in_x, track_y - 14.0, out_x - in_x, 14.0), QColor(60, 60, 60, 200))

            # Render Mark In SVG Icon ({) sitting on dashed line
            mark_in_rect = QRectF(in_x, track_y - 14.0, 6.0, 14.0)
            self.renderer_mark_in.render(painter, mark_in_rect)

            # Render Mark Out SVG Icon (}) sitting on dashed line
            mark_out_rect = QRectF(out_x - 6.0, track_y - 14.0, 6.0, 14.0)
            self.renderer_mark_out.render(painter, mark_out_rect)

        # 3. Cyan SVG Playhead Pointer sitting right on top of dashed track line
        if self.total_frames > 0:
            head_x = (float(self.current_frame) / float(self.total_frames)) * w

            # Render Playhead SVG Icon with pointed tip touching track_y
            playhead_rect = QRectF(head_x - 5.5, track_y - 16.0, 11.0, 16.0)
            self.renderer_playhead.render(painter, playhead_rect)
