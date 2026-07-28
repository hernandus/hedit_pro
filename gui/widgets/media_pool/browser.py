"""
Media Pool / Project Panel Widget (Premiere Pro style asset browser).
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeView, QHeaderView, QFileDialog, QToolBar
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem


class MediaPoolWidget(QWidget):
    """Project Panel for managing imported media files, bins, and assets."""

    media_imported = Signal(str)

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
        self.model = QStandardItemModel(0, 4)
        self.model.setHorizontalHeaderLabels(["Name", "Type", "Duration", "FPS"])

        self.tree_view.setModel(self.model)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree_view.setAlternatingRowColors(True)

        layout.addWidget(self.tree_view)

    def on_import_click(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Import Media into Project", "", "Video/Audio Files (*.mp4 *.mkv *.mov *.avi *.mp3 *.wav *.png *.jpg);;All Files (*)"
        )
        for path in file_paths:
            self.add_media_item(path)
            self.media_imported.emit(path)

    def add_media_item(self, path: str):
        import os
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lower()
        
        item_name = QStandardItem(name)
        item_type = QStandardItem("Video" if ext in ['.mp4', '.mkv', '.mov', '.avi'] else "Audio/Image")
        item_dur = QStandardItem("00:00:10:00")
        item_fps = QStandardItem("60.00")

        self.model.appendRow([item_name, item_type, item_dur, item_fps])
