"""
Keyframe Timeline & Curve Editor Widget for Hedit Pro.
Visualizes keyframe diamonds (◆), interpolation curves, and playhead position.
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPolygonF, QFont

from core.effects import AnimatableProperty


class KeyframeGraphWidget(QWidget):
    """Mini Keyframe Timeline Graph for Effect Controls properties."""

    keyframe_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.setMinimumWidth(150)
        self.property: AnimatableProperty = None
        self.current_frame = 0
        self.max_frames = 600

    def set_property(self, prop: AnimatableProperty, current_frame: int = 0, max_frames: int = 600):
        self.property = prop
        self.current_frame = current_frame
        self.max_frames = max_frames
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor("#191919"))
        painter.setPen(QColor("#2c2c2c"))
        painter.drawRect(0, 0, w - 1, h - 1)

        if not self.property:
            return

        # Frame to X helper
        def frame_to_x(f: int) -> float:
            return (f / float(self.max_frames)) * w

        # Draw keyframe connection curve line
        if len(self.property.keyframes) > 1:
            painter.setPen(QPen(QColor("#2680eb"), 1.5, Qt.DashLine))
            pts = []
            for k in self.property.keyframes:
                x = frame_to_x(k.frame)
                y = h / 2.0
                pts.append((x, y))

            for i in range(len(pts) - 1):
                painter.drawLine(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])

        # Draw Keyframe Diamonds (◆)
        for k in self.property.keyframes:
            kx = frame_to_x(k.frame)
            ky = h / 2.0
            
            # Draw diamond polygon
            d_size = 5.0
            diamond = QPolygonF([
                (kx, ky - d_size),
                (kx + d_size, ky),
                (kx, ky + d_size),
                (kx - d_size, ky)
            ])

            if k.frame == self.current_frame:
                painter.setBrush(QBrush(QColor("#00ffcc"))) # Highlighted cyan diamond
                painter.setPen(QPen(QColor("#ffffff"), 1.5))
            else:
                painter.setBrush(QBrush(QColor("#2680eb"))) # Premiere blue diamond
                painter.setPen(QPen(QColor("#104e92"), 1))

            painter.drawPolygon(diamond)

        # Draw playhead indicator line
        px = frame_to_x(self.current_frame)
        painter.setPen(QPen(QColor("#ff5252"), 1.5))
        painter.drawLine(px, 0, px, h)

        painter.end()
