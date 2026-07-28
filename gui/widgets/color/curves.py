"""
Interactive RGB Tone Curves Widget for Lumetri Color Grading in Hedit Pro.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath


class RGBToneCurveWidget(QWidget):
    """Interactive RGB Tone Curve Graph (Master, Red, Green, Blue)."""

    curve_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(180)
        self.setMinimumWidth(200)
        
        self.active_channel = "RGB" # "RGB", "R", "G", "B"
        
        # Control points per channel (stored in 0.0 to 1.0 coords)
        self.points = {
            "RGB": [QPointF(0.0, 0.0), QPointF(1.0, 1.0)],
            "R": [QPointF(0.0, 0.0), QPointF(1.0, 1.0)],
            "G": [QPointF(0.0, 0.0), QPointF(1.0, 1.0)],
            "B": [QPointF(0.0, 0.0), QPointF(1.0, 1.0)],
        }
        self.selected_point_idx = None

    def set_channel(self, channel: str):
        self.active_channel = channel
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Grid Background
        painter.fillRect(0, 0, w, h, QColor("#161616"))
        painter.setPen(QPen(QColor("#282828"), 1))
        
        for i in range(1, 4):
            x = (w / 4.0) * i
            y = (h / 4.0) * i
            painter.drawLine(x, 0, x, h)
            painter.drawLine(0, y, w, y)

        # Draw Diagonal Reference Line
        painter.setPen(QPen(QColor("#383838"), 1, Qt.DashLine))
        painter.drawLine(0, h, w, 0)

        # Channel Colors
        colors = {
            "RGB": QColor("#ffffff"),
            "R": QColor("#ff5252"),
            "G": QColor("#66bb6a"),
            "B": QColor("#42a5f5"),
        }
        curve_color = colors.get(self.active_channel, QColor("#ffffff"))

        pts = self.points[self.active_channel]

        # Construct Curve Path
        path = QPainterPath()
        start_pt = QPointF(pts[0].x() * w, (1.0 - pts[0].y()) * h)
        path.moveTo(start_pt)

        if len(pts) == 2:
            end_pt = QPointF(pts[1].x() * w, (1.0 - pts[1].y()) * h)
            path.lineTo(end_pt)
        else:
            for i in range(len(pts) - 1):
                p1 = QPointF(pts[i].x() * w, (1.0 - pts[i].y()) * h)
                p2 = QPointF(pts[i+1].x() * w, (1.0 - pts[i+1].y()) * h)
                ctrl1 = QPointF(p1.x() + (p2.x() - p1.x()) / 2.0, p1.y())
                ctrl2 = QPointF(p1.x() + (p2.x() - p1.x()) / 2.0, p2.y())
                path.cubicTo(ctrl1, ctrl2, p2)

        painter.setPen(QPen(curve_color, 2))
        painter.drawPath(path)

        # Draw Control Point Knobs
        for p in pts:
            px = p.x() * w
            py = (1.0 - p.y()) * h
            painter.setBrush(QBrush(curve_color))
            painter.setPen(QPen(QColor("#000000"), 1))
            painter.drawEllipse(QPointF(px, py), 5.0, 5.0)

        painter.end()

    def mousePressEvent(self, event):
        pos = event.pos()
        w = self.width()
        h = self.height()
        norm_x = max(0.0, min(1.0, pos.x() / float(w)))
        norm_y = max(0.0, min(1.0, 1.0 - (pos.y() / float(h))))

        pts = self.points[self.active_channel]
        # Check if clicking existing point
        for i, p in enumerate(pts):
            px = p.x() * w
            py = (1.0 - p.y()) * h
            if (pos - QPointF(px, py)).manhattanLength() < 10:
                self.selected_point_idx = i
                return

        # Add new point on curve
        new_pt = QPointF(norm_x, norm_y)
        pts.append(new_pt)
        pts.sort(key=lambda pt: pt.x())
        self.update()
        self.curve_changed.emit()

    def mouseMoveEvent(self, event):
        if self.selected_point_idx is not None:
            pos = event.pos()
            w = self.width()
            h = self.height()
            norm_x = max(0.0, min(1.0, pos.x() / float(w)))
            norm_y = max(0.0, min(1.0, 1.0 - (pos.y() / float(h))))

            pts = self.points[self.active_channel]
            pts[self.selected_point_idx] = QPointF(norm_x, norm_y)
            pts.sort(key=lambda pt: pt.x())
            self.update()
            self.curve_changed.emit()

    def mouseReleaseEvent(self, event):
        self.selected_point_idx = None
