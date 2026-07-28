"""
Video Viewport Frame Widget for Hedit Pro.
Draws decoded video pixmaps accurately centered and scaled within its bounds,
preventing Qt layout resize feedback loops.
"""

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap, QColor, QFont


class VideoViewportWidget(QFrame):
    """High-performance canvas frame for displaying video frames in monitors."""

    def __init__(self, placeholder_text: str = "DRAG MEDIA HERE", parent=None):
        super().__init__(parent)
        self.current_pixmap = None
        # proxy_badge_mode: None  → hidden
        #                   "on"      → "● PROXY" cyan  (proxy active)
        #                   "missing" → "NO PROXY" gray  (proxies ON but file absent)
        self.proxy_badge_mode: str | None = None
        self.setStyleSheet("background-color: #000000; border: 1px solid #282828;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.placeholder_label = QLabel(placeholder_text)
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #444444; font-weight: bold; font-size: 12px;")
        layout.addWidget(self.placeholder_label)

    def set_pixmap(self, pixmap: QPixmap):
        """Update active video frame pixmap and trigger repaint."""
        self.current_pixmap = pixmap
        if pixmap and not pixmap.isNull():
            self.placeholder_label.hide()
        self.update()

    def set_proxy_badge(self, mode: str | None):
        """
        Update the proxy status badge overlay.
        mode: None → hidden | "on" → proxy active | "missing" → proxies ON but no proxy file
        """
        self.proxy_badge_mode = mode
        self.update()

    def clear_video(self, placeholder_text: str = None):
        """Clear video frame and show placeholder."""
        self.current_pixmap = None
        if placeholder_text:
            self.placeholder_label.setText(placeholder_text)
        self.placeholder_label.show()
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.current_pixmap and not self.current_pixmap.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)

            w, h = self.width(), self.height()
            if w > 4 and h > 4:
                scaled = self.current_pixmap.scaled(
                    w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                x = (w - scaled.width()) // 2
                y = (h - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)

                # ── Proxy badge (top-right corner of video frame) ──────────
                if self.proxy_badge_mode == "on":
                    badge_text = "● PROXY"
                    badge_color = QColor("#00A8FF")
                elif self.proxy_badge_mode == "missing":
                    badge_text = "NO PROXY"
                    badge_color = QColor("#555555")
                else:
                    badge_text = None

                if badge_text:
                    font = QFont("Inter", 8, QFont.Bold)
                    painter.setFont(font)
                    fm = painter.fontMetrics()
                    bw = fm.horizontalAdvance(badge_text)
                    bh = fm.height()
                    pad = 4
                    badge_x = x + scaled.width() - bw - pad * 2 - 4
                    badge_y = y + 6

                    # Background pill
                    painter.setBrush(QColor(0, 0, 0, 160))
                    painter.setPen(Qt.NoPen)
                    painter.drawRoundedRect(badge_x - pad, badge_y, bw + pad * 2, bh + pad, 3, 3)

                    # Text
                    painter.setPen(badge_color)
                    painter.drawText(badge_x, badge_y + fm.ascent() + 2, badge_text)

