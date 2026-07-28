"""
Interactive Color Wheels (Lift, Gamma, Gain) for Lumetri Color Grading in Hedit Pro.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QDoubleSpinBox,
    QPushButton, QFileDialog, QTabWidget, QFormLayout
)
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QConicalGradient

from core.color import ColorGradingModel
from gui.widgets.color.curves import RGBToneCurveWidget


class ColorWheelWidget(QWidget):
    """Single 2D Color Wheel (Lift / Gamma / Gain)."""

    color_changed = Signal(float, float, float) # R, G, B offsets

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.setFixedSize(120, 140)
        self.r_offset = 0.0
        self.g_offset = 0.0
        self.b_offset = 0.0
        self.handle_pos = QPointF(0.0, 0.0) # -1.0 to 1.0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        radius = 45
        center = QPointF(w / 2.0, (h - 20) / 2.0 + 15)

        # Title Label
        painter.setPen(QColor("#cccccc"))
        painter.setFont(self.font())
        painter.drawText(0, 12, w, 15, Qt.AlignCenter, self.title)

        # Draw Color Wheel Gradient Circle
        grad = QConicalGradient(center, 0)
        grad.setColorAt(0.0, QColor("#ff0000"))
        grad.setColorAt(0.16, QColor("#ffff00"))
        grad.setColorAt(0.33, QColor("#00ff00"))
        grad.setColorAt(0.5, QColor("#00ffff"))
        grad.setColorAt(0.66, QColor("#0000ff"))
        grad.setColorAt(0.83, QColor("#ff00ff"))
        grad.setColorAt(1.0, QColor("#ff0000"))

        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.drawEllipse(center, radius, radius)

        # Inner Neutral Circle
        painter.setBrush(QBrush(QColor(30, 30, 30, 180)))
        painter.drawEllipse(center, radius * 0.25, radius * 0.25)

        # Handle Knob (2D Color Offset)
        kx = center.x() + (self.handle_pos.x() * radius * 0.8)
        ky = center.y() + (self.handle_pos.y() * radius * 0.8)

        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.setPen(QPen(QColor("#000000"), 1.5))
        painter.drawEllipse(QPointF(kx, ky), 4.0, 4.0)

        painter.end()

    def mousePressEvent(self, event):
        self._update_handle(event.pos())

    def mouseMoveEvent(self, event):
        self._update_handle(event.pos())

    def _update_handle(self, pos: QPointF):
        w = self.width()
        h = self.height()
        radius = 45.0
        center = QPointF(w / 2.0, (h - 20) / 2.0 + 15)

        dx = (pos.x() - center.x()) / (radius * 0.8)
        dy = (pos.y() - center.y()) / (radius * 0.8)

        dist = (dx * dx + dy * dy) ** 0.5
        if dist > 1.0:
            dx /= dist
            dy /= dist

        self.handle_pos = QPointF(dx, dy)
        self.r_offset = dx
        self.b_offset = dy
        self.g_offset = -0.5 * (dx + dy)
        self.update()
        self.color_changed.emit(self.r_offset, self.g_offset, self.b_offset)


class LumetriColorWidget(QWidget):
    """Full Lumetri Color Grading Panel for Hedit Pro."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = ColorGradingModel()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        tabs = QTabWidget()

        # Tab 1: Basic Correction
        tab_basic = QWidget()
        basic_layout = QFormLayout(tab_basic)

        self.temp = QDoubleSpinBox()
        self.temp.setRange(-100, 100)
        basic_layout.addRow("Temperature:", self.temp)

        self.tint = QDoubleSpinBox()
        self.tint.setRange(-100, 100)
        basic_layout.addRow("Tint:", self.tint)

        self.exposure = QDoubleSpinBox()
        self.exposure.setRange(-5.0, 5.0)
        self.exposure.setSingleStep(0.1)
        basic_layout.addRow("Exposure:", self.exposure)

        self.contrast = QDoubleSpinBox()
        self.contrast.setRange(-100, 100)
        basic_layout.addRow("Contrast:", self.contrast)

        self.highlights = QDoubleSpinBox()
        self.highlights.setRange(-100, 100)
        basic_layout.addRow("Highlights:", self.highlights)

        self.shadows = QDoubleSpinBox()
        self.shadows.setRange(-100, 100)
        basic_layout.addRow("Shadows:", self.shadows)

        tabs.addTab(tab_basic, "Basic")

        # Tab 2: Color Wheels (Lift / Gamma / Gain)
        tab_wheels = QWidget()
        wheels_layout = QHBoxLayout(tab_wheels)
        wheels_layout.setContentsMargins(4, 4, 4, 4)

        self.wheel_lift = ColorWheelWidget("Lift (Shadows)")
        self.wheel_gamma = ColorWheelWidget("Gamma (Mids)")
        self.wheel_gain = ColorWheelWidget("Gain (Highlights)")

        wheels_layout.addWidget(self.wheel_lift)
        wheels_layout.addWidget(self.wheel_gamma)
        wheels_layout.addWidget(self.wheel_gain)

        tabs.addTab(tab_wheels, "Color Wheels")

        # Tab 3: RGB Curves
        tab_curves = QWidget()
        curves_layout = QVBoxLayout(tab_curves)
        curves_layout.setContentsMargins(4, 4, 4, 4)

        # Channel Selector Buttons
        chan_bar = QHBoxLayout()
        for ch in ["RGB", "R", "G", "B"]:
            btn = QPushButton(ch)
            btn.setFixedWidth(40)
            btn.clicked.connect(lambda checked, c=ch: self.curve_widget.set_channel(c))
            chan_bar.addWidget(btn)
        chan_bar.addStretch()

        curves_layout.addLayout(chan_bar)
        self.curve_widget = RGBToneCurveWidget()
        curves_layout.addWidget(self.curve_widget)

        tabs.addTab(tab_curves, "Curves")

        # Tab 4: 3D LUT
        tab_lut = QWidget()
        lut_layout = QVBoxLayout(tab_lut)
        
        self.btn_load_lut = QPushButton("🎨 Load 3D LUT (.cube)")
        self.btn_load_lut.clicked.connect(self.on_load_lut)
        self.lut_label = QLabel("No 3D LUT Applied")
        self.lut_label.setStyleSheet("color: #777777;")

        lut_layout.addWidget(self.btn_load_lut)
        lut_layout.addWidget(self.lut_label)
        lut_layout.addStretch()

        tabs.addTab(tab_lut, "Creative LUT")

        layout.addWidget(tabs)

    def on_load_lut(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select 3D LUT File", "", "LUT Files (*.cube *.3dl);;All Files (*)")
        if path:
            import os
            self.model.lut_path = path
            self.lut_label.setText(os.path.basename(path))
            self.lut_label.setStyleSheet("color: #00ffcc; font-weight: bold;")
