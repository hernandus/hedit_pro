"""
Export Media Dialog for Hedit Pro (Premiere Pro style render window).
Supports preset selection, target path browsing, resolution options, and real-time progress bar with ETA.
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QProgressBar, QFileDialog, QGroupBox, QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from core.export import EXPORT_PRESETS, ExportWorkerThread


class ExportDialog(QDialog):
    """Premiere Pro inspired Export Settings Modal Dialog."""

    def __init__(self, total_sequence_frames: int = 1800, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Media - Hedit Pro")
        self.setFixedSize(580, 420)
        self.total_frames = total_sequence_frames
        self.worker_thread: ExportWorkerThread = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Title
        title = QLabel("EXPORT SETTINGS")
        title.setFont(QFont("Inter", 11, QFont.Bold))
        title.setStyleSheet("color: #2680eb;")
        layout.addWidget(title)

        # File & Output Path Box
        file_box = QGroupBox("Output File")
        file_layout = QFormLayout(file_box)

        default_name = os.path.expanduser("~/Videos/HeditPro_Render.mp4")
        self.path_input = QLineEdit(default_name)
        
        btn_browse = QPushButton("Browse...")
        btn_browse.setFixedWidth(80)
        btn_browse.clicked.connect(self.on_browse)

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(btn_browse)

        file_layout.addRow("Save Location:", path_layout)
        layout.addWidget(file_box)

        # Format Presets Box
        preset_box = QGroupBox("Format & Quality Preset")
        preset_layout = QFormLayout(preset_box)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(EXPORT_PRESETS.keys()))
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        preset_layout.addRow("Preset:", self.preset_combo)

        self.lbl_details = QLabel("Video: 1920x1080 @ 60 FPS | Codec: H.264 | Audio: AAC 192 kbps")
        self.lbl_details.setStyleSheet("color: #00ffcc; font-size: 11px;")
        preset_layout.addRow("Summary:", self.lbl_details)

        layout.addWidget(preset_box)

        # Progress Bar & ETA Box
        progress_box = QGroupBox("Render Progress")
        progress_layout = QVBoxLayout(progress_box)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar { height: 18px; border-radius: 4px; text-align: center; background-color: #121212; }
            QProgressBar::chunk { background-color: #2680eb; border-radius: 4px; }
        """)

        self.lbl_eta = QLabel("Status: Ready to export")
        self.lbl_eta.setStyleSheet("color: #888888; font-size: 11px;")

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.lbl_eta)

        layout.addWidget(progress_box)

        # Bottom Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_export = QPushButton("🚀 Export Video")
        self.btn_export.setFixedHeight(30)
        self.btn_export.setStyleSheet("background-color: #2680eb; color: #ffffff; font-weight: bold; padding: 0 16px;")
        self.btn_export.clicked.connect(self.start_export)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_export)

        layout.addLayout(btn_layout)

    def on_preset_changed(self, preset_name: str):
        p = EXPORT_PRESETS.get(preset_name, EXPORT_PRESETS["H.264 MP4 (1080p 60fps)"])
        self.lbl_details.setText(f"Res: {p['res']} @ {p['fps']} FPS | Codec: {p['vcodec']} | Audio: {p['acodec']} {p['abitrate']}")

    def on_browse(self):
        preset_name = self.preset_combo.currentText()
        ext = "mp4" if "MP4" in preset_name or "YouTube" in preset_name else ("mov" if "ProRes" in preset_name else "wav")
        path, _ = QFileDialog.getSaveFileName(self, "Export Media Target", self.path_input.text(), f"Media File (*.{ext});;All Files (*)")
        if path:
            self.path_input.setText(path)

    def start_export(self):
        output_path = self.path_input.text()
        preset_name = self.preset_combo.currentText()

        self.btn_export.setEnabled(False)
        self.btn_cancel.setText("Cancel Render")

        self.worker_thread = ExportWorkerThread(output_path, preset_name, total_frames=self.total_frames)
        self.worker_thread.progress_changed.connect(self._on_progress_update)
        self.worker_thread.render_completed.connect(self._on_render_done)
        self.worker_thread.render_failed.connect(self._on_render_failed)
        self.worker_thread.start()

    def _on_progress_update(self, percent: int, eta_sec: float):
        self.progress_bar.setValue(percent)
        self.lbl_eta.setText(f"Rendering: {percent}% completed | Estimated Time Remaining: {int(eta_sec)}s")

    def _on_render_done(self, file_path: str):
        self.progress_bar.setValue(100)
        self.lbl_eta.setText(f"Status: Export completed successfully! Saved to {file_path}")
        self.btn_export.setEnabled(True)
        self.btn_cancel.setText("Close")
        QMessageBox.information(self, "Export Complete", f"Video render finished successfully!\nSaved to: {file_path}")

    def _on_render_failed(self, error_msg: str):
        self.lbl_eta.setText(f"Status: Export failed - {error_msg}")
        self.btn_export.setEnabled(True)
        self.btn_cancel.setText("Close")
