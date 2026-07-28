"""
Effect Controls Inspector Panel for Hedit Pro (Motion, Opacity, Keyframe Stopwatches).
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox,
    QGroupBox, QFormLayout, QPushButton, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from core.effects import MotionEffect, AnimatableProperty
from gui.widgets.inspector.keyframe_graph import KeyframeGraphWidget


class EffectPropertyRow(QWidget):
    """Row widget combining Stopwatch button, Label, Spinbox value, and Keyframe Graph."""

    value_changed = Signal(float)
    keyframe_toggled = Signal(bool)

    def __init__(self, property_obj: AnimatableProperty, parent=None):
        super().__init__(parent)
        self.prop = property_obj
        self.current_frame = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(6)

        # Stopwatch Toggle Button (⏱)
        self.btn_stopwatch = QPushButton("⏱")
        self.btn_stopwatch.setFixedSize(24, 24)
        self.btn_stopwatch.setCheckable(True)
        self.btn_stopwatch.setToolTip("Toggle Keyframing")
        self.btn_stopwatch.setStyleSheet("""
            QPushButton { background-color: #262626; color: #888888; border-radius: 2px; }
            QPushButton:checked { background-color: #2680eb; color: #ffffff; }
        """)
        self.btn_stopwatch.toggled.connect(self._on_stopwatch_toggled)
        layout.addWidget(self.btn_stopwatch)

        # Label
        self.lbl_name = QLabel(self.prop.name)
        self.lbl_name.setFixedWidth(80)
        layout.addWidget(self.lbl_name)

        # Double SpinBox Value
        self.spinbox = QDoubleSpinBox()
        self.spinbox.setRange(self.prop.min_val, self.prop.max_val)
        self.spinbox.setValue(self.prop.default_value)
        self.spinbox.setFixedWidth(80)
        self.spinbox.valueChanged.connect(self._on_spinbox_changed)
        layout.addWidget(self.spinbox)

        # Keyframe Graph Widget
        self.graph = KeyframeGraphWidget()
        self.graph.set_property(self.prop, self.current_frame)
        layout.addWidget(self.graph, stretch=1)

    def set_frame(self, frame: int):
        self.current_frame = frame
        val = self.prop.get_value_at(frame)
        self.spinbox.blockSignals(True)
        self.spinbox.setValue(val)
        self.spinbox.blockSignals(False)

        # Check if keyframe exists at current frame
        has_kf = self.prop.has_keyframe_at(frame)
        self.btn_stopwatch.blockSignals(True)
        self.btn_stopwatch.setChecked(has_kf or len(self.prop.keyframes) > 0)
        self.btn_stopwatch.blockSignals(False)

        self.graph.set_property(self.prop, frame)

    def _on_spinbox_changed(self, value: float):
        if self.btn_stopwatch.isChecked():
            self.prop.set_keyframe(self.current_frame, value)
            self.graph.set_property(self.prop, self.current_frame)
        self.value_changed.emit(value)

    def _on_stopwatch_toggled(self, checked: bool):
        if checked:
            self.prop.set_keyframe(self.current_frame, self.spinbox.value())
        else:
            self.prop.keyframes.clear()
        self.graph.set_property(self.prop, self.current_frame)
        self.keyframe_toggled.emit(checked)


class EffectControlsWidget(QWidget):
    """Inspector Panel for clip properties: Position, Scale, Rotation, Opacity."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.motion = MotionEffect()
        self.current_frame = 0

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # Header Title
        title = QLabel("EFFECT CONTROLS")
        title.setFont(QFont("Inter", 10, QFont.Bold))
        title.setStyleSheet("color: #2680eb;")
        layout.addWidget(title)

        # Motion Controls Box
        motion_box = QGroupBox("Motion")
        motion_layout = QVBoxLayout(motion_box)
        motion_layout.setContentsMargins(4, 4, 4, 4)

        self.row_pos_x = EffectPropertyRow(self.motion.position_x)
        self.row_pos_y = EffectPropertyRow(self.motion.position_y)
        self.row_scale = EffectPropertyRow(self.motion.scale)
        self.row_scale.spinbox.setSuffix(" %")
        self.row_rotation = EffectPropertyRow(self.motion.rotation)
        self.row_rotation.spinbox.setSuffix(" °")

        for r in (self.row_pos_x, self.row_pos_y, self.row_scale, self.row_rotation):
            motion_layout.addWidget(r)

        layout.addWidget(motion_box)

        # Opacity Controls Box
        opacity_box = QGroupBox("Opacity")
        opacity_layout = QVBoxLayout(opacity_box)
        opacity_layout.setContentsMargins(4, 4, 4, 4)

        self.row_opacity = EffectPropertyRow(self.motion.opacity)
        self.row_opacity.spinbox.setSuffix(" %")
        opacity_layout.addWidget(self.row_opacity)

        layout.addWidget(opacity_box)
        layout.addStretch()

    def set_frame(self, frame: int):
        self.current_frame = frame
        for r in (self.row_pos_x, self.row_pos_y, self.row_scale, self.row_rotation, self.row_opacity):
            r.set_frame(frame)
