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
        self.show_proxy_badge = False
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

                # Draw 'PROXIES ON' badge in top-right corner of video frame
                if self.show_proxy_badge:
                    painter.setPen(QColor("#00A8FF"))
                    font = QFont("Inter", 9, QFont.Bold)
                    painter.setFont(font)
                    badge_text = "PROXIES ON"
                    fm = painter.fontMetrics()
                    bw = fm.horizontalAdvance(badge_text)
                    badge_x = x + scaled.width() - bw - 10
                    badge_y = y + fm.ascent() + 8
                    if badge_x > x:
                        painter.drawText(badge_x, badge_y, badge_text)
