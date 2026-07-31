"""
Video Viewport Frame Widget for Hedit Pro.
Draws decoded video pixmaps accurately centered and scaled within its bounds,
preventing Qt layout resize feedback loops.
"""

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QPainter, QPixmap, QColor, QFont, QCursor

NUMERIC_PRESETS = [10, 25, 50, 75, 100, 150, 200, 400]
ZOOM_MODES = ["Fit"] + [f"{p}%" for p in NUMERIC_PRESETS]


class VideoViewportWidget(QFrame):
    """High-performance canvas frame for displaying video frames in monitors with zoom and panning support."""

    zoom_changed = Signal(str)

    def __init__(self, placeholder_text: str = "DRAG MEDIA HERE", parent=None):
        super().__init__(parent)
        self.current_pixmap = None
        self.proxy_badge_mode: str | None = None

        self.original_size = (0, 0)
        self.zoom_mode: str = "Fit"
        self.zoom_factor: float = 1.0
        self.pan_offset = QPointF(0.0, 0.0)
        self.is_panning: bool = False
        self.last_mouse_pos = QPointF(0.0, 0.0)
        self.space_pressed: bool = False

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("background-color: #1D1D1D; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.placeholder_label = QLabel(placeholder_text)
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #444444; font-weight: bold; font-size: 12px;")
        layout.addWidget(self.placeholder_label)

    def set_original_size(self, width: int, height: int):
        """Set original canonical media resolution for zoom reference."""
        self.original_size = (max(0, width), max(0, height))
        self.update()

    def _get_ref_size(self) -> tuple[float, float]:
        """Returns reference dimensions (original_size if valid, else current_pixmap size)."""
        if self.original_size[0] > 0 and self.original_size[1] > 0:
            return float(self.original_size[0]), float(self.original_size[1])
        if self.current_pixmap and not self.current_pixmap.isNull():
            return float(self.current_pixmap.width()), float(self.current_pixmap.height())
        return 0.0, 0.0

    def set_pixmap(self, pixmap: QPixmap):
        """Update active video frame pixmap and trigger repaint."""
        self.current_pixmap = pixmap
        if pixmap and not pixmap.isNull():
            self.placeholder_label.hide()
        self.update()

    def set_proxy_badge(self, mode: str | None):
        """Update proxy status badge mode (None | 'on' | 'missing')."""
        self.proxy_badge_mode = mode
        self.update()

    def clear_video(self, placeholder_text: str = None):
        """Clear video frame and show placeholder."""
        self.current_pixmap = None
        if placeholder_text:
            self.placeholder_label.setText(placeholder_text)
        self.placeholder_label.show()
        self.update()

    def set_zoom(self, mode: str):
        """Set zoom preset mode (Fit, 10%, 25%, 50%, 75%, 100%, 150%, 200%, 400%)."""
        if mode not in ZOOM_MODES:
            return
        self.zoom_mode = mode
        if mode == "Fit":
            self.zoom_factor = 1.0
            self.pan_offset = QPointF(0.0, 0.0)
        else:
            val = float(mode.replace("%", "")) / 100.0
            self.zoom_factor = val
        self.update()

    def wheelEvent(self, event):
        """Ctrl + Wheel or Mouse Wheel over viewport changes zoom level based on dynamic Fit calculation."""
        delta = event.angleDelta().y()
        if delta == 0:
            return

        if self.zoom_mode == "Fit":
            ref_w, ref_h = self._get_ref_size()
            w, h = float(self.width()), float(self.height())
            if ref_w > 0 and ref_h > 0 and w > 0 and h > 0:
                fit_ratio = min(w / ref_w, h / ref_h)
                fit_pct = fit_ratio * 100.0
            else:
                fit_pct = 100.0

            if delta > 0:
                higher = [p for p in NUMERIC_PRESETS if p > fit_pct]
                target_pct = higher[0] if higher else 400
            else:
                lower = [p for p in NUMERIC_PRESETS if p < fit_pct]
                target_pct = lower[-1] if lower else 10

            next_mode = f"{target_pct}%"
        else:
            current_pct = int(self.zoom_mode.replace("%", "")) if "%" in self.zoom_mode else 100
            if current_pct in NUMERIC_PRESETS:
                idx = NUMERIC_PRESETS.index(current_pct)
            else:
                idx = 4  # default to 100%

            if delta > 0:
                next_idx = min(len(NUMERIC_PRESETS) - 1, idx + 1)
            else:
                next_idx = max(0, idx - 1)

            next_mode = f"{NUMERIC_PRESETS[next_idx]}%"

        self.set_zoom(next_mode)
        self.zoom_changed.emit(next_mode)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.set_zoom("Fit")
            self.zoom_changed.emit("Fit")
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and self.space_pressed):
            self.is_panning = True
            self.last_mouse_pos = event.position()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_panning:
            delta = event.position() - self.last_mouse_pos
            self.pan_offset += delta
            self.last_mouse_pos = event.position()
            self.update()
        else:
            if self.space_pressed:
                self.setCursor(Qt.OpenHandCursor)
            elif self.cursor().shape() in (Qt.OpenHandCursor, Qt.ClosedHandCursor):
                self.setCursor(Qt.ArrowCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_panning and (event.button() == Qt.MiddleButton or event.button() == Qt.LeftButton):
            self.is_panning = False
            if self.space_pressed:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.space_pressed = True
            self.setCursor(Qt.OpenHandCursor)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.space_pressed = False
            if not self.is_panning:
                self.setCursor(Qt.ArrowCursor)
        super().keyReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.current_pixmap and not self.current_pixmap.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)

            crect = self.rect()
            painter.setClipRect(crect)

            w, h = float(crect.width()), float(crect.height())
            cx, cy = float(crect.x()), float(crect.y())

            if w > 4 and h > 4:
                ref_w, ref_h = self._get_ref_size()
                pw, ph = float(self.current_pixmap.width()), float(self.current_pixmap.height())

                if self.zoom_mode == "Fit":
                    scaled = self.current_pixmap.scaled(
                        int(w), int(h), Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    draw_w, draw_h = float(scaled.width()), float(scaled.height())
                    draw_x = cx + (w - draw_w) / 2.0
                    draw_y = cy + (h - draw_h) / 2.0
                    painter.drawPixmap(int(draw_x), int(draw_y), scaled)
                else:
                    draw_w = ref_w * self.zoom_factor
                    draw_h = ref_h * self.zoom_factor
                    draw_x = cx + (w - draw_w) / 2.0 + self.pan_offset.x()
                    draw_y = cy + (h - draw_h) / 2.0 + self.pan_offset.y()
                    target_rect = QRectF(draw_x, draw_y, draw_w, draw_h)
                    source_rect = QRectF(0, 0, pw, ph)
                    painter.drawPixmap(target_rect, self.current_pixmap, source_rect)

                # ── PROXY badge (Fixed at top-right corner of inner viewport canvas) ──
                if self.proxy_badge_mode == "on":
                    badge_text = "PROXY"
                    font = QFont("Inter", 8, QFont.Bold)
                    painter.setFont(font)
                    fm = painter.fontMetrics()
                    bw = fm.horizontalAdvance(badge_text)
                    bh = fm.height()
                    pad = 4
                    badge_x = cx + w - bw - pad * 2 - 10
                    badge_y = cy + 10.0

                    # Gray background pill with 40% opacity (alpha 102)
                    painter.setBrush(QColor(128, 128, 128, 102))
                    painter.setPen(Qt.NoPen)
                    painter.drawRoundedRect(QRectF(badge_x - pad, badge_y, bw + pad * 2, bh + pad), 3, 3)

                    # PROXY text with 50% opacity (alpha 128)
                    painter.setPen(QColor(255, 255, 255, 128))
                    painter.drawText(badge_x, badge_y + fm.ascent() + 2, badge_text)

