"""
Media Pool / Project Panel Widget (Premiere Pro style asset browser).
"""

import os
import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeView, QHeaderView, QFileDialog, QToolBar
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem

from gui.utils.timecode import frames_to_timecode


class MediaPoolWidget(QWidget):
    """Project Panel for managing imported media files, bins, and assets."""

    media_imported = Signal(str)
    media_double_clicked = Signal(str) # Emits file path when double clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_import = QPushButton("+ Import Media")
        self.btn_import.setFixedHeight(26)
        self.btn_import.clicked.connect(self.on_import_click)

        self.btn_new_bin = QPushButton("📁 New Bin")
        self.btn_new_bin.setFixedHeight(26)

        toolbar.addWidget(self.btn_import)
        toolbar.addWidget(self.btn_new_bin)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        # Tree View for Media Assets
        self.tree_view = QTreeView()
        self.model = QStandardItemModel(0, 5)
        self.model.setHorizontalHeaderLabels(["Name", "Type", "Duration", "FPS", "Path"])

        self.tree_view.setModel(self.model)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree_view.setColumnHidden(4, True) # Hide full path column
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.doubleClicked.connect(self._on_item_double_clicked)

        layout.addWidget(self.tree_view)

    def on_import_click(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Import Media into Project", "", "Video/Audio Files (*.mp4 *.mkv *.mov *.avi *.mp3 *.wav *.png *.jpg);;All Files (*)"
        )
        for path in file_paths:
            self.add_media_item(path)
            self.media_imported.emit(path)

    def add_media_item(self, path: str):
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lower()
        
        dur_tc = "00:00:10:00"
        fps_str = "60.00"

        if ext in ['.mp4', '.mkv', '.mov', '.avi']:
            try:
                cap = cv2.VideoCapture(path)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS) or 60.0
                    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 600
                    dur_tc = frames_to_timecode(frames, fps)
                    fps_str = f"{fps:.2f}"
                    cap.release()
            except Exception:
                pass

        item_name = QStandardItem(name)
        item_type = QStandardItem("Video" if ext in ['.mp4', '.mkv', '.mov', '.avi'] else "Audio/Image")
        item_dur = QStandardItem(dur_tc)
        item_fps = QStandardItem(fps_str)
        item_path = QStandardItem(path)

        self.model.appendRow([item_name, item_type, item_dur, item_fps, item_path])

    def _on_item_double_clicked(self, index):
        row = index.row()
        path_item = self.model.item(row, 4)
        if path_item:
            self.media_double_clicked.emit(path_item.text())

