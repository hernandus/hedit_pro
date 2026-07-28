"""
Media Pool / Project Panel Widget (Premiere Pro style asset browser).
"""

import os
import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTreeView, QHeaderView, QFileDialog, QMenu, QToolButton, QMessageBox,
    QAbstractItemView, QDockWidget
)
from PySide6.QtCore import Qt, Signal, QSize, QModelIndex
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon, QAction, QKeySequence, QShortcut

from gui.utils.timecode import frames_to_timecode

ICONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Interface_elements"))


class ProjectTreeView(QTreeView):
    """Custom QTreeView that clears selection when clicking empty viewport space."""

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            self.clearSelection()
            self.setCurrentIndex(QModelIndex())
        super().mousePressEvent(event)


class MediaPoolWidget(QWidget):
    """Project Panel for managing imported media files, bins, and assets."""

    media_imported = Signal(str)
    media_double_clicked = Signal(str)  # Emits file path when double clicked
    media_removed = Signal(str)         # Emits file path when item is deleted

    def __init__(self, parent=None, project_name="sample movie name"):
        super().__init__(parent)
        self.project_name = project_name
        self._init_icons()
        self.init_ui()

    def _init_icons(self):
        self.icon_folder = QIcon(os.path.join(ICONS_DIR, "icon_folder.svg"))
        self.icon_video_audio = QIcon(os.path.join(ICONS_DIR, "icon_video_audio.svg"))
        self.icon_video = QIcon(os.path.join(ICONS_DIR, "icon_video.svg"))
        self.icon_audio = QIcon(os.path.join(ICONS_DIR, "icon_audio.svg"))
        self.icon_add = QIcon(os.path.join(ICONS_DIR, "icon_add.svg"))

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tree View for Media Assets & Bins
        self.tree_view = ProjectTreeView()
        self.model = QStandardItemModel(0, 4)
        self.model.setHorizontalHeaderLabels(["Name", "Framerate", "Path", "IsFolder"])

        self.tree_view.setModel(self.model)
        self.tree_view.setIconSize(QSize(16, 16))

        # Configure columns
        header = self.tree_view.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree_view.setColumnHidden(2, True)  # Path
        self.tree_view.setColumnHidden(3, True)  # IsFolder

        # Style tree view to match reference PNG (#1d1d1d background, horizontal dividers #141414)
        self.tree_view.setStyleSheet("""
            QTreeView {
                background-color: #1d1d1d;
                color: #d4d4d4;
                border: none;
                font-size: 12px;
                outline: 0;
            }
            QTreeView::branch {
                background-color: #1d1d1d;
            }
            QTreeView::item {
                height: 24px;
                padding: 2px 4px;
                border-bottom: 1px solid #141414;
                border-right: none;
            }
            QTreeView::item:selected {
                background-color: #2680eb;
                color: #ffffff;
            }
            QTreeView::item:hover:!selected {
                background-color: #242424;
            }
            QHeaderView::section {
                background-color: #1d1d1d;
                color: #a0a0a0;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: normal;
                border: none;
                border-bottom: 1px solid #141414;
            }
        """)

        self.tree_view.setAlternatingRowColors(False)
        self.tree_view.setExpandsOnDoubleClick(True)
        self.tree_view.doubleClicked.connect(self._on_item_double_clicked)

        # Disable automatic inline edit triggers (only allowed via context menu > Rename)
        self.tree_view.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Enable Drag and Drop reordering and nesting into bins
        self.tree_view.setDragEnabled(True)
        self.tree_view.setAcceptDrops(True)
        self.tree_view.setDropIndicatorShown(True)
        self.tree_view.setDragDropMode(QTreeView.InternalMove)
        self.tree_view.setDefaultDropAction(Qt.MoveAction)

        # Delete / Backspace Keyboard Shortcuts for items
        self.shortcut_del = QShortcut(QKeySequence(Qt.Key_Delete), self.tree_view)
        self.shortcut_del.setContext(Qt.WidgetWithChildrenShortcut)
        self.shortcut_del.activated.connect(self.delete_selected_items)

        self.shortcut_back = QShortcut(QKeySequence(Qt.Key_Backspace), self.tree_view)
        self.shortcut_back.setContext(Qt.WidgetWithChildrenShortcut)
        self.shortcut_back.activated.connect(self.delete_selected_items)

        # Context Menu setup
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self.tree_view)

        # Bottom toolbar with action icons on the right
        bottom_bar = QWidget()
        bottom_bar.setFixedHeight(28)
        bottom_bar.setStyleSheet("background-color: #1d1d1d; border-top: 1px solid #141414;")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(6, 2, 8, 2)
        bottom_layout.setSpacing(6)
        bottom_layout.addStretch()

        # Icon Folder (New Bin) button
        self.btn_new_bin = QToolButton()
        self.btn_new_bin.setIcon(self.icon_folder)
        self.btn_new_bin.setIconSize(QSize(16, 16))
        self.btn_new_bin.setToolTip("New Bin")
        self.btn_new_bin.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                padding: 2px;
                border-radius: 2px;
            }
            QToolButton:hover {
                background: #333333;
            }
            QToolButton:pressed {
                background: #444444;
            }
        """)
        self.btn_new_bin.clicked.connect(self.create_bin)

        # Icon Add button (Placeholder for new sequence / item)
        self.btn_add = QToolButton()
        self.btn_add.setIcon(self.icon_add)
        self.btn_add.setIconSize(QSize(16, 16))
        self.btn_add.setToolTip("New Item")
        self.btn_add.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                padding: 2px;
                border-radius: 2px;
            }
            QToolButton:hover {
                background: #333333;
            }
            QToolButton:pressed {
                background: #444444;
            }
        """)

        bottom_layout.addWidget(self.btn_new_bin)
        bottom_layout.addWidget(self.btn_add)

        layout.addWidget(bottom_bar)

        # Populate initial sample structure matching reference PNG
        self._populate_sample_data()

    def _populate_sample_data(self):
        """Initial sample structure matching reference hedit-pro-menu-project.png."""
        self.create_bin("Audio")
        footage_item = self.create_bin("Footage")

        # Add sample clip items inside Footage
        for clip_name in ["C0159.MP4", "C0160.MP4", "C0161.MP4", "C0162.MP4"]:
            item_name = QStandardItem(clip_name)
            item_name.setIcon(self.icon_video_audio)
            item_name.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)

            item_fps = QStandardItem("25 fps")
            item_fps.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

            item_path = QStandardItem("")
            item_path.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

            item_is_bin = QStandardItem("False")
            item_is_bin.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

            footage_item.appendRow([item_name, item_fps, item_path, item_is_bin])

        self.tree_view.expand(footage_item.index())

    def set_project_name(self, name: str):
        self.project_name = name
        parent = self.parentWidget()
        while parent and not isinstance(parent, QDockWidget):
            parent = parent.parentWidget()
        if parent:
            parent.setWindowTitle(f"Project: {name}")

    def get_selected_folder_item(self):
        """Returns the currently selected folder QStandardItem or None (root)."""
        selected_indexes = self.tree_view.selectedIndexes()
        if selected_indexes:
            index = selected_indexes[0]
            item = self.model.itemFromIndex(index)
            if item:
                if item.column() != 0:
                    item = self.model.item(item.row(), 0)
                is_folder_item = self.model.item(item.row(), 3)
                if is_folder_item and is_folder_item.text() == "True":
                    return item
                elif item.parent():
                    parent = item.parent()
                    parent_is_folder = parent.child(parent.row(), 3) if parent.parent() else self.model.item(parent.row(), 3)
                    if parent_is_folder and parent_is_folder.text() == "True":
                        return parent
        return None

    def create_bin(self, name="New Bin"):
        parent_item = self.get_selected_folder_item()

        folder_item = QStandardItem(name)
        folder_item.setIcon(self.icon_folder)
        folder_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)

        folder_fps = QStandardItem("")
        folder_fps.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        folder_path = QStandardItem("")
        folder_path.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        folder_is_bin = QStandardItem("True")
        folder_is_bin.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        row_items = [folder_item, folder_fps, folder_path, folder_is_bin]

        if parent_item:
            parent_item.appendRow(row_items)
            self.tree_view.expand(parent_item.index())
        else:
            self.model.appendRow(row_items)

        return folder_item

    def on_import_click(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Import Media into Project", "", "Video/Audio Files (*.mp4 *.mkv *.mov *.avi *.mp3 *.wav *.png *.jpg);;All Files (*)"
        )
        parent_item = self.get_selected_folder_item()
        for path in file_paths:
            self.add_media_item(path, parent_item=parent_item)
            self.media_imported.emit(path)

    def add_media_item(self, path: str, parent_item=None):
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lower()

        fps_str = ""
        is_video = ext in ['.mp4', '.mkv', '.mov', '.avi']
        is_audio = ext in ['.mp3', '.wav', '.aac', '.flac', '.m4a']

        if is_video:
            try:
                cap = cv2.VideoCapture(path)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
                    fps_int = int(round(fps))
                    fps_str = f"{fps_int} fps" if abs(fps - fps_int) < 0.05 else f"{fps:.2f} fps"
                    cap.release()
            except Exception:
                fps_str = "25 fps"

        item_name = QStandardItem(name)
        if is_video:
            item_name.setIcon(self.icon_video_audio)
        elif is_audio:
            item_name.setIcon(self.icon_audio)
        else:
            item_name.setIcon(self.icon_video)
        item_name.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)

        item_fps = QStandardItem(fps_str)
        item_fps.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        item_path = QStandardItem(path)
        item_path.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        item_is_bin = QStandardItem("False")
        item_is_bin.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        row_items = [item_name, item_fps, item_path, item_is_bin]

        if parent_item:
            parent_item.appendRow(row_items)
            self.tree_view.expand(parent_item.index())
        else:
            self.model.appendRow(row_items)

    def _on_item_double_clicked(self, index):
        col2_path_idx = index.siblingAtColumn(2)
        col3_bin_idx = index.siblingAtColumn(3)

        is_bin_item = self.model.itemFromIndex(col3_bin_idx)
        path_item = self.model.itemFromIndex(col2_path_idx)

        # If it is not a bin, load the clip into Source Monitor
        if not (is_bin_item and is_bin_item.text() == "True"):
            if path_item and path_item.text():
                self.media_double_clicked.emit(path_item.text())

    def rename_selected_item(self):
        """Triggers inline text editing for the selected item (Column 0)."""
        selected_indexes = self.tree_view.selectedIndexes()
        if selected_indexes:
            idx = selected_indexes[0]
            col0_idx = idx.siblingAtColumn(0)
            self.tree_view.edit(col0_idx)

    def delete_selected_items(self):
        """Permanently removes selected items/bins from the model and UI."""
        selected_indexes = self.tree_view.selectedIndexes()
        if not selected_indexes:
            return

        # Unique row index targets in column 0
        rows_to_delete = []
        seen_rows = set()

        for index in selected_indexes:
            parent = index.parent()
            row = index.row()
            key = (parent, row)
            if key not in seen_rows:
                seen_rows.add(key)
                col0_index = index.siblingAtColumn(0)
                rows_to_delete.append(col0_index)

        # Sort in reverse order by row index to prevent shifting during deletion
        rows_to_delete.sort(key=lambda idx: idx.row(), reverse=True)

        count = len(rows_to_delete)
        msg = f"¿Estás seguro de que deseas eliminar {'este elemento' if count == 1 else f'estos {count} elementos'} del proyecto?"

        reply = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        for index in rows_to_delete:
            parent_index = index.parent()
            row = index.row()

            if parent_index.isValid():
                parent_item = self.model.itemFromIndex(parent_index)
                path_item = parent_item.child(row, 2)
                if path_item and path_item.text():
                    self.media_removed.emit(path_item.text())
                parent_item.removeRow(row)
            else:
                path_item = self.model.item(row, 2)
                if path_item and path_item.text():
                    self.media_removed.emit(path_item.text())
                self.model.removeRow(row)

    def _show_context_menu(self, position):
        menu = QMenu(self)
        import_action = QAction("Import Media...", self)
        import_action.triggered.connect(self.on_import_click)
        menu.addAction(import_action)

        # If items are selected, add Rename and Delete options to context menu
        if self.tree_view.selectedIndexes():
            menu.addSeparator()
            rename_action = QAction("Rename", self)
            rename_action.triggered.connect(self.rename_selected_item)
            menu.addAction(rename_action)

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(self.delete_selected_items)
            menu.addAction(delete_action)

        menu.exec(self.tree_view.viewport().mapToGlobal(position))



