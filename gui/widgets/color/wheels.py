"""
Lumetri-style Color Grading Panel Widget for Hedit Pro.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGroupBox, QDoubleSpinBox,
    QPushButton, QFileDialog, QLabel
)


class LumetriColorWidget(QWidget):
    """Color Grading Panel for Exposure, Contrast, Temperature, LUT loading."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # Basic Correction Box
        basic_box = QGroupBox("Basic Correction")
        form = QFormLayout(basic_box)

        self.temp = QDoubleSpinBox()
        self.temp.setRange(-100, 100)
        form.addRow("Temperature:", self.temp)

        self.exposure = QDoubleSpinBox()
        self.exposure.setRange(-5.0, 5.0)
        self.exposure.setSingleStep(0.1)
        form.addRow("Exposure:", self.exposure)

        self.contrast = QDoubleSpinBox()
        self.contrast.setRange(-100, 100)
        form.addRow("Contrast:", self.contrast)

        self.highlights = QDoubleSpinBox()
        self.highlights.setRange(-100, 100)
        form.addRow("Highlights:", self.highlights)

        self.shadows = QDoubleSpinBox()
        self.shadows.setRange(-100, 100)
        form.addRow("Shadows:", self.shadows)

        layout.addWidget(basic_box)

        # Creative / LUT Box
        lut_box = QGroupBox("Creative LUT")
        lut_layout = QVBoxLayout(lut_box)
        
        self.btn_load_lut = QPushButton("🎨 Load 3D LUT (.cube)")
        self.btn_load_lut.clicked.connect(self.on_load_lut)
        self.lut_label = QLabel("No LUT Applied")
        self.lut_label.setStyleSheet("color: #777777;")

        lut_layout.addWidget(self.btn_load_lut)
        lut_layout.addWidget(self.lut_label)

        layout.addWidget(lut_box)
        layout.addStretch()

    def on_load_lut(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select 3D LUT File", "", "LUT Files (*.cube *.3dl);;All Files (*)")
        if path:
            import os
            self.lut_label.setText(os.path.basename(path))
            self.lut_label.setStyleSheet("color: #2680eb; font-weight: bold;")
