"""
Effect Controls Inspector Panel for Hedit Pro (Motion, Opacity, Audio, Keyframes).
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox,
    QGroupBox, QFormLayout, QCheckBox, QPushButton
)
from PySide6.QtCore import Qt


class EffectControlsWidget(QWidget):
    """Inspector Panel for clip properties: Position, Scale, Rotation, Opacity."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # Motion Controls Box
        motion_box = QGroupBox("Motion")
        motion_layout = QFormLayout(motion_box)

        self.pos_x = QDoubleSpinBox()
        self.pos_x.setRange(-9999, 9999)
        self.pos_x.setValue(960.0)

        self.pos_y = QDoubleSpinBox()
        self.pos_y.setRange(-9999, 9999)
        self.pos_y.setValue(540.0)

        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("X:"))
        pos_layout.addWidget(self.pos_x)
        pos_layout.addWidget(QLabel("Y:"))
        pos_layout.addWidget(self.pos_y)

        motion_layout.addRow("Position:", pos_layout)

        self.scale = QDoubleSpinBox()
        self.scale.setRange(0.0, 1000.0)
        self.scale.setValue(100.0)
        self.scale.setSuffix(" %")
        motion_layout.addRow("Scale:", self.scale)

        self.rotation = QDoubleSpinBox()
        self.rotation.setRange(-360.0, 360.0)
        self.rotation.setSuffix(" °")
        motion_layout.addRow("Rotation:", self.rotation)

        layout.addWidget(motion_box)

        # Opacity Controls Box
        opacity_box = QGroupBox("Opacity")
        opacity_layout = QFormLayout(opacity_box)

        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(0.0, 100.0)
        self.opacity.setValue(100.0)
        self.opacity.setSuffix(" %")
        opacity_layout.addRow("Opacity:", self.opacity)

        layout.addWidget(opacity_box)
        layout.addStretch()
