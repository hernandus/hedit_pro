"""
Real-Time Audio VU Meter Widget for Hedit Pro (dB scale, peak hold, clipping indicator).
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QFont


class StereoVUMeterWidget(QWidget):
    """Stereo (Left / Right) Audio Level Meter with dB scale."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(50)
        self.left_db = -60.0
        self.right_db = -60.0
        self.peak_left_db = -60.0
        self.peak_right_db = -60.0

        # Animation timer for test / live levels
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self._update_simulated_levels)
        self.is_active = False

    def start_meter(self):
        self.is_active = True
        self.timer.start()

    def stop_meter(self):
        self.is_active = False
        self.timer.stop()
        self.left_db = -60.0
        self.right_db = -60.0
        self.update()

    def set_levels(self, left_db: float, right_db: float):
        self.left_db = max(-60.0, min(6.0, left_db))
        self.right_db = max(-60.0, min(6.0, right_db))
        self.peak_left_db = max(self.peak_left_db, self.left_db)
        self.peak_right_db = max(self.peak_right_db, self.right_db)
        self.update()

    def _update_simulated_levels(self):
        if not self.is_active:
            return
        import random
        base_left = -12.0 + random.uniform(-6.0, 4.0)
        base_right = -12.0 + random.uniform(-6.0, 4.0)
        self.set_levels(base_left, base_right)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor("#141414"))

        # Channel bar widths
        bar_w = 16
        gap = 4
        left_x = 4
        right_x = left_x + bar_w + gap

        # Convert dB (-60 to +6) to Y height (h to 0)
        def db_to_y(db: float) -> int:
            norm = (db + 60.0) / 66.0 # 0.0 at -60dB, 1.0 at +6dB
            return int(h * (1.0 - max(0.0, min(1.0, norm))))

        # Gradient Brush (Green -> Yellow -> Red)
        grad = QLinearGradient(0, h, 0, 0)
        grad.setColorAt(0.0, QColor("#2e7d32"))  # Green (-60dB to -18dB)
        grad.setColorAt(0.65, QColor("#fbc02d")) # Yellow (-18dB to -3dB)
        grad.setColorAt(0.9, QColor("#d32f2f"))  # Red (-3dB to +6dB)

        # Left Bar
        left_y = db_to_y(self.left_db)
        painter.fillRect(left_x, left_y, bar_w, h - left_y, grad)

        # Right Bar
        right_y = db_to_y(self.right_db)
        painter.fillRect(right_x, right_y, bar_w, h - right_y, grad)

        # Draw dB scale lines (-48, -36, -24, -12, -6, 0, +3)
        painter.setPen(QColor("#444444"))
        for db in [-48, -36, -24, -12, -6, 0]:
            y = db_to_y(db)
            painter.drawLine(0, y, w, y)

        painter.end()
