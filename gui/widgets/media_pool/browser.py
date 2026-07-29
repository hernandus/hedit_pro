"""
Media Pool / Project Panel Widget (Premiere Pro style asset browser).
"""

import os
import cv2
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTreeView, QHeaderView, QFileDialog, QMenu, QToolButton, QMessageBox,
    QAbstractItemView, QDockWidget
)
from PySide6.QtCore import Qt, Signal, QSize, QModelIndex, QPointF, QTimer
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon, QAction, QKeySequence, QShortcut, QColor, QPen, QPolygonF, QCursor

from gui.utils.timecode import frames_to_timecode
from gui.theme import (
    COLOR_BG_DARK, COLOR_BG_HOVER, COLOR_BG_SELECTED, COLOR_DIVIDER,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_TEXT_REGULAR, TREE_VIEW_QSS
)
from gui.widgets.media_pool.proxy_dialog import CreateProxyDialog

ICONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Interface_elements"))

VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.mov', '.avi', '.mxf', '.r3d', '.braw'}


def has_audio_stream(path: str) -> bool:
    """Checks via ffprobe whether a video media file contains audio streams."""
    if not path or not os.path.exists(path):
        return True  # Default to True for sample placeholder items if file doesn't exist
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'a',
            '-show_entries', 'stream=codec_type',
            '-of', 'csv=p=0',
            path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
        return bool(result.stdout.strip())
    except Exception:
        return True


def get_media_metadata(path: str):
    """Extracts (fps_str, video_res_str, audio_info_str, status_str) for a given media file path."""
    if not path or not os.path.exists(path):
        return ("25 fps", "1920x1080", "48000Hz 16Bit Stereo", "Online") if not path else ("", "", "", "Offline")

    status_str = "Online"
    fps_str = ""
    video_res_str = ""
    audio_info_str = ""

    ext = os.path.splitext(path)[1].lower()
    is_video = ext in ['.mp4', '.mkv', '.mov', '.avi']
    is_audio = ext in ['.mp3', '.wav', '.aac', '.flac', '.m4a']

    if is_video:
        try:
            cap = cv2.VideoCapture(path)
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
                fps_int = int(round(fps))
                fps_str = f"{fps_int} fps" if abs(fps - fps_int) < 0.05 else f"{fps:.2f} fps"
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                if w > 0 and h > 0:
                    video_res_str = f"{w}x{h}"
                cap.release()
        except Exception:
            fps_str = "25 fps"

    if is_video or is_audio:
        try:
            cmd = [
                'ffprobe', '-v', 'error',
                '-select_streams', 'a:0',
                '-show_entries', 'stream=sample_rate,channels,bits_per_raw_sample',
                '-of', 'csv=p=0',
                path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
            out = res.stdout.strip()
            if out:
                parts = [p.strip() for p in out.split(',') if p.strip()]
                if len(parts) >= 2:
                    sr = parts[0]
                    ch = int(parts[1]) if parts[1].isdigit() else 2
                    ch_str = "Stereo" if ch == 2 else ("Mono" if ch == 1 else f"{ch}Ch")
                    bit_str = f"{parts[2]}Bit " if (len(parts) >= 3 and parts[2].isdigit()) else "16Bit "
                    audio_info_str = f"{sr}Hz {bit_str}{ch_str}"
                elif len(parts) == 1:
                    audio_info_str = f"{parts[0]}Hz"
        except Exception:
            pass

    return fps_str, video_res_str, audio_info_str, status_str


class ProjectHeaderView(QHeaderView):
    """Custom header view positioning sort arrows immediately after text label."""

    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self.viewport().update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.viewport().update()

    def paintSection(self, painter, rect, logicalIndex):
        if not rect.isValid():
            return

        painter.save()

        mouse_pos = self.mapFromGlobal(QCursor.pos())
        is_hovered = rect.contains(mouse_pos)

        bg_color = QColor(COLOR_BG_HOVER) if is_hovered else QColor(COLOR_BG_DARK)
        painter.fillRect(rect, bg_color)

        border_pen = QPen(QColor(COLOR_DIVIDER), 1)
        painter.setPen(border_pen)
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())

        if is_hovered:
            painter.drawLine(rect.topLeft(), rect.bottomLeft())
            painter.drawLine(rect.topRight(), rect.bottomRight())

        model = self.model()
        text = str(model.headerData(logicalIndex, self.orientation(), Qt.DisplayRole) or "")

        font = self.font()
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QColor(COLOR_TEXT_PRIMARY if is_hovered else COLOR_TEXT_MUTED))

        fm = painter.fontMetrics()
        text_width = fm.horizontalAdvance(text)

        padding_left = 18 if logicalIndex == 0 else 8
        text_x = rect.x() + padding_left
        text_y = rect.y() + (rect.height() + fm.ascent() - fm.descent()) // 2

        painter.drawText(text_x, text_y, text)

        if self.isSortIndicatorShown() and self.sortIndicatorSection() == logicalIndex:
            arrow_size = 5
            arrow_x = text_x + text_width + 6
            arrow_center_y = rect.y() + rect.height() // 2

            painter.setBrush(QColor(COLOR_TEXT_PRIMARY if is_hovered else COLOR_TEXT_MUTED))
            painter.setPen(Qt.NoPen)

            poly = QPolygonF()
            if self.sortIndicatorOrder() == Qt.AscendingOrder:
                poly.append(QPointF(arrow_x, arrow_center_y + 2))
                poly.append(QPointF(arrow_x + arrow_size, arrow_center_y + 2))
                poly.append(QPointF(arrow_x + arrow_size / 2.0, arrow_center_y - 3))
            else:
                poly.append(QPointF(arrow_x, arrow_center_y - 2))
                poly.append(QPointF(arrow_x + arrow_size, arrow_center_y - 2))
                poly.append(QPointF(arrow_x + arrow_size / 2.0, arrow_center_y + 3))

            painter.drawPolygon(poly)

        painter.restore()


class ProjectTreeView(QTreeView):
    """Custom QTreeView that clears selection when clicking empty viewport space."""

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            self.clearSelection()
            self.setCurrentIndex(QModelIndex())
        super().mousePressEvent(event)


class MediaPoolWidget(QWidget):
    """
    Main Media Pool / Project Panel Widget containing hierarchy, asset details and controls.
    """

    media_double_clicked = Signal(str)
    media_imported = Signal(str)
    media_removed = Signal(str)

    def __init__(self, project_name="sample movie name", parent=None):
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
        self.header_view = ProjectHeaderView(Qt.Horizontal, self.tree_view)
        self.tree_view.setHeader(self.header_view)

        self.model = QStandardItemModel(0, 7)
        self.model.setHorizontalHeaderLabels(["Name", "Framerate", "Video", "Audio", "Status", "Path", "IsFolder"])

        self.tree_view.setModel(self.model)
        self.tree_view.setIconSize(QSize(16, 16))
        self.tree_view.setIndentation(14)

        # Configure columns & header sorting/resizing
        header = self.tree_view.header()
        header.setSectionsClickable(True)
        header.setStretchLastSection(True)

        # Set all visible columns to Interactive so users can drag borders left/right to resize
        for col_idx in range(5):
            header.setSectionResizeMode(col_idx, QHeaderView.Interactive)

        # Set initial default column widths
        header.resizeSection(0, 180)  # Name
        header.resizeSection(1, 75)   # Framerate
        header.resizeSection(2, 95)   # Video
        header.resizeSection(3, 140)  # Audio
        header.resizeSection(4, 75)   # Status

        header.setSortIndicatorShown(True)
        self.tree_view.setSortingEnabled(True)

        self.tree_view.setColumnHidden(5, True)  # Path
        self.tree_view.setColumnHidden(6, True)  # IsFolder

        self.tree_view.setStyleSheet(TREE_VIEW_QSS)

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

        # Context Menu setup on container and tree view
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self.tree_view)

        # Bottom toolbar with action icons on the right
        bottom_bar = QWidget()
        bottom_bar.setFixedHeight(28)
        bottom_bar.setStyleSheet("background-color: #1D1D1D; border-top: 1px solid #0E0E0E;")
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
        """Initial sample structure containing default bins."""
        self.create_bin("Audio")
        self.create_bin("Footage")

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
                is_folder_item = self.model.item(item.row(), 6)
                if is_folder_item and is_folder_item.text() == "True":
                    return item
                elif item.parent():
                    parent = item.parent()
                    parent_is_folder = parent.child(parent.row(), 6) if parent.parent() else self.model.item(parent.row(), 6)
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

        folder_video = QStandardItem("")
        folder_video.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        folder_audio = QStandardItem("")
        folder_audio.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        folder_status = QStandardItem("")
        folder_status.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        folder_path = QStandardItem("")
        folder_path.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        folder_is_bin = QStandardItem("True")
        folder_is_bin.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        row_items = [folder_item, folder_fps, folder_video, folder_audio, folder_status, folder_path, folder_is_bin]

        if parent_item:
            parent_item.appendRow(row_items)
            self.tree_view.expand(parent_item.index())
        else:
            self.model.appendRow(row_items)

        return folder_item

    def on_import_click(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Media into Project",
            "",
            "Media Files (*.mp4 *.mkv *.mov *.avi *.mp3 *.wav *.png *.jpg *.mxf *.braw *.r3d);;All Files (*)",
            options=QFileDialog.DontUseNativeDialog
        )
        if not file_paths:
            return
        parent_item = self.get_selected_folder_item()
        for path in file_paths:
            self.add_media_item(path, parent_item=parent_item)
            self.media_imported.emit(path)

    def on_import_folder_click(self):
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Import Folder into Project",
            "",
            options=QFileDialog.DontUseNativeDialog
        )
        if not folder_path or not os.path.exists(folder_path):
            return

        folder_name = os.path.basename(folder_path) or folder_path
        bin_item = self.create_bin(folder_name)

        for root, _, files in os.walk(folder_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in VIDEO_EXTENSIONS or ext in ['.mp3', '.wav', '.aac', '.flac', '.m4a', '.png', '.jpg']:
                    full_p = os.path.join(root, file)
                    self.add_media_item(full_p, parent_item=bin_item)
                    self.media_imported.emit(full_p)

    def add_media_item(self, path: str, parent_item=None):
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lower()

        fps_str, video_res_str, audio_info_str, status_str = get_media_metadata(path)

        is_video = ext in ['.mp4', '.mkv', '.mov', '.avi']
        is_audio = ext in ['.mp3', '.wav', '.aac', '.flac', '.m4a']
        has_audio = bool(audio_info_str) if is_video else False

        item_name = QStandardItem(name)
        if is_video:
            if has_audio:
                item_name.setIcon(self.icon_video_audio)
            else:
                item_name.setIcon(self.icon_video)
        elif is_audio:
            item_name.setIcon(self.icon_audio)
        else:
            item_name.setIcon(self.icon_video)
        item_name.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)

        item_fps = QStandardItem(fps_str)
        item_fps.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        item_video = QStandardItem(video_res_str)
        item_video.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        item_audio = QStandardItem(audio_info_str)
        item_audio.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        item_status = QStandardItem(status_str)
        item_status.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        item_path = QStandardItem(path)
        item_path.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        item_is_bin = QStandardItem("False")
        item_is_bin.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        row_items = [item_name, item_fps, item_video, item_audio, item_status, item_path, item_is_bin]

        if parent_item:
            parent_item.appendRow(row_items)
            self.tree_view.expand(parent_item.index())
        else:
            self.model.appendRow(row_items)

    def _on_item_double_clicked(self, index):
        if not index.isValid():
            self.on_import_click()
            return

        col5_path_idx = index.siblingAtColumn(5)
        col6_bin_idx = index.siblingAtColumn(6)

        is_bin_item = self.model.itemFromIndex(col6_bin_idx)
        path_item = self.model.itemFromIndex(col5_path_idx)

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
                path_item = parent_item.child(row, 5)
                if path_item and path_item.text():
                    self.media_removed.emit(path_item.text())
                parent_item.removeRow(row)
            else:
                path_item = self.model.item(row, 5)
                if path_item and path_item.text():
                    self.media_removed.emit(path_item.text())
                self.model.removeRow(row)

    def _get_selected_video_paths(self) -> list:
        """Returns file paths of all selected non-bin video items."""
        video_paths = []
        seen = set()
        for index in self.tree_view.selectedIndexes():
            if index.column() != 0:
                continue
            col6 = self.model.itemFromIndex(index.siblingAtColumn(6))
            col5 = self.model.itemFromIndex(index.siblingAtColumn(5))
            if col6 and col6.text() == "True":
                continue  # skip bins
            if col5 and col5.text():
                path = col5.text()
                ext  = os.path.splitext(path)[1].lower()
                if ext in VIDEO_EXTENSIONS and path not in seen:
                    seen.add(path)
                    video_paths.append(path)
        return video_paths

    def _on_create_proxy(self):
        """Opens the Create Proxy Media dialog for the selected video files."""
        video_paths = self._get_selected_video_paths()
        if not video_paths:
            return
        dlg = CreateProxyDialog(video_paths, parent=self)
        dlg.exec()

    def _show_context_menu(self, position):
        menu = QMenu(self)

        import_action = QAction("Import Media...", self)
        import_action.triggered.connect(lambda: QTimer.singleShot(0, self.on_import_click))
        menu.addAction(import_action)

        import_folder_action = QAction("Import Folder...", self)
        import_folder_action.triggered.connect(lambda: QTimer.singleShot(0, self.on_import_folder_click))
        menu.addAction(import_folder_action)

        new_bin_action = QAction("New Bin", self)
        new_bin_action.triggered.connect(lambda: QTimer.singleShot(0, lambda: self.create_bin()))
        menu.addAction(new_bin_action)

        if self.tree_view.selectedIndexes():
            # --- Proxy action (video files only) --------------------------
            video_paths = self._get_selected_video_paths()
            if video_paths:
                menu.addSeparator()
                n = len(video_paths)
                label = (
                    "Create Proxy Media…"
                    if n == 1
                    else f"Create Proxy Media…  ({n} files)"
                )
                proxy_action = QAction(label, self)
                proxy_action.triggered.connect(lambda: QTimer.singleShot(0, self._on_create_proxy))
                menu.addAction(proxy_action)

            # --- Standard item actions ------------------------------------
            menu.addSeparator()
            rename_action = QAction("Rename", self)
            rename_action.triggered.connect(lambda: QTimer.singleShot(0, self.rename_selected_item))
            menu.addAction(rename_action)

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: QTimer.singleShot(0, self.delete_selected_items))
            menu.addAction(delete_action)

        sender = self.sender()
        if sender == self.tree_view:
            global_pos = self.tree_view.viewport().mapToGlobal(position)
        else:
            global_pos = self.mapToGlobal(position)

        menu.exec(global_pos)



