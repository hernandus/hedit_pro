"""
Primary Dockable MainWindow for Hedit Pro.
Arranges panels in Premiere Pro workspace layout using QDockWidgets and QTabWidget.
Connects signals across Media Pool, Source Monitor, Program Monitor, VU Meter, Effect Controls, Lumetri Color, and Timeline.
Includes System Log Viewer & Logger integration.
"""

from PySide6.QtWidgets import (
    QMainWindow, QDockWidget, QTabWidget, QStatusBar, QMenuBar,
    QMenu, QLabel, QWidget, QHBoxLayout, QApplication
)
from PySide6.QtCore import Qt, QSize, QEvent
from PySide6.QtGui import QIcon, QKeySequence, QAction, QShortcut

from core.engine import MLTEngine
from core.logger import get_logger
from gui.widgets.monitors.source import SourceMonitorWidget
from gui.widgets.monitors.program import ProgramMonitorWidget
from gui.widgets.monitors.vu_meter import StereoVUMeterWidget
from gui.widgets.timeline.canvas import TimelineCanvasWidget
from gui.widgets.media_pool.browser import MediaPoolWidget
from gui.widgets.inspector.transform import EffectControlsWidget
from gui.widgets.color.wheels import LumetriColorWidget
from gui.widgets.export_dialog import ExportDialog
from gui.widgets.log_viewer import LogViewerDialog

logger = get_logger()


class MainWindow(QMainWindow):
    """Premiere Pro inspired Main Workspace Window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hedit Pro - Adobe Premiere Pro Clone [Linux NLE]")
        self.resize(1600, 950)

        logger.info("[UI] Initializing MainWindow layout...")

        # Init MLT Engine
        self.engine = MLTEngine()

        # Enable Dock Nesting and Tabs
        self.setDockOptions(
            QMainWindow.AllowNestedDocks |
            QMainWindow.AllowTabbedDocks |
            QMainWindow.AnimatedDocks |
            QMainWindow.GroupedDragging
        )

        self.setup_menubar()
        self.setup_statusbar()
        self.setup_docks()
        self.connect_signals()
        self.setup_shortcuts()
        self.setup_focus_tracking()

        logger.info("[UI] MainWindow layout and docks initialized successfully.")

    def setup_menubar(self):
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")
        new_proj = file_menu.addAction("New Project...")
        open_proj = file_menu.addAction("Open Project...")
        file_menu.addSeparator()
        import_media = file_menu.addAction("Import Media...")
        import_media.triggered.connect(self.on_import_media_action)
        file_menu.addSeparator()
        export_video = file_menu.addAction("Export Media... (Ctrl+M)")
        export_video.triggered.connect(self.on_open_export_dialog)
        file_menu.addSeparator()
        exit_act = file_menu.addAction("Exit")
        exit_act.triggered.connect(self.close)

        # Edit Menu
        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction("Undo (Ctrl+Z)")
        edit_menu.addAction("Redo (Ctrl+Shift+Z)")

        # Sequence Menu
        seq_menu = menubar.addMenu("&Sequence")
        seq_menu.addAction("Sequence Settings...")

        # Window Menu
        window_menu = menubar.addMenu("&Window")
        window_menu.addAction("Reset Layout")
        view_log_act = window_menu.addAction("View System Log Console")
        view_log_act.triggered.connect(self.on_open_log_viewer)

        # Help Menu
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("About Hedit Pro")
        help_log_act = help_menu.addAction("View System Log...")
        help_log_act.triggered.connect(self.on_open_log_viewer)

    def setup_statusbar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        self.lbl_status = QLabel("Ready")
        self.lbl_engine = QLabel(f"Engine: {'MLT Active' if self.engine.is_available() else 'Fallback Preview Mode'}")
        self.lbl_engine.setStyleSheet("color: #00ffcc; font-weight: bold; margin-right: 12px;")

        self.statusbar.addWidget(self.lbl_status, stretch=1)
        self.statusbar.addPermanentWidget(self.lbl_engine)

    def setup_docks(self):
        # 1. Project Panel / Media Pool Dock (Bottom Left)
        self.media_pool = MediaPoolWidget(project_name="sample movie name")
        self.dock_media = QDockWidget(f"Project: {self.media_pool.project_name}", self)
        self.dock_media.setWidget(self.media_pool)

        # 2. Source Monitor Dock (Top Left)
        self.source_monitor = SourceMonitorWidget()
        self.dock_source = QDockWidget("Source Monitor", self)
        self.dock_source.setWidget(self.source_monitor)

        # 3. Effect Controls Dock (Decoupled Independent Window / Dock)
        self.effect_controls = EffectControlsWidget()
        self.dock_effect_controls = QDockWidget("Effect Controls", self)
        self.dock_effect_controls.setWidget(self.effect_controls)

        # 4. Program Monitor Dock (Top Right)
        self.dock_program = QDockWidget("Program Monitor", self)
        prog_container = QWidget()
        prog_layout = QHBoxLayout(prog_container)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        prog_layout.setSpacing(2)

        self.program_monitor = ProgramMonitorWidget()
        self.vu_meter = StereoVUMeterWidget()
        prog_layout.addWidget(self.program_monitor, stretch=1)
        prog_layout.addWidget(self.vu_meter)
        self.dock_program.setWidget(prog_container)

        # 5. Lumetri Color Dock (Decoupled Independent Window / Dock)
        self.color_widget = LumetriColorWidget()
        self.dock_lumetri = QDockWidget("Lumetri Color", self)
        self.dock_lumetri.setWidget(self.color_widget)

        # 6. Timeline Dock (Bottom Right)
        self.dock_timeline = QDockWidget("Timeline: Main Sequence", self)
        self.timeline_widget = TimelineCanvasWidget()
        self.dock_timeline.setWidget(self.timeline_widget)

        # Arrange Docks per User Layout (Top Row: Media Pool | Source Monitor | Program Monitor, Bottom Row: Timeline)
        self.setCorner(Qt.BottomLeftCorner, Qt.BottomDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.BottomDockWidgetArea)

        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_media)
        self.splitDockWidget(self.dock_media, self.dock_source, Qt.Horizontal)
        self.splitDockWidget(self.dock_source, self.dock_program, Qt.Horizontal)

        self.tabifyDockWidget(self.dock_source, self.dock_effect_controls)
        self.dock_source.raise_()

        self.tabifyDockWidget(self.dock_program, self.dock_lumetri)
        self.dock_program.raise_()

        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_timeline)

        # Adjust initial relative sizes
        self.resizeDocks([self.dock_media, self.dock_source, self.dock_program], [240, 520, 520], Qt.Horizontal)
        self.resizeDocks([self.dock_source, self.dock_timeline], [420, 260], Qt.Vertical)

    def setup_focus_tracking(self):
        self._active_dock = None

        # Enable WA_StyledBackground on all dock inner widgets so QSS border renders
        for dock in (self.dock_media, self.dock_source, self.dock_program,
                     self.dock_timeline, self.dock_effect_controls, self.dock_lumetri):
            w = dock.widget()
            if w:
                w.setAttribute(Qt.WA_StyledBackground, True)

        app = QApplication.instance()
        if app:
            app.focusChanged.connect(self._on_focus_changed)
            app.installEventFilter(self)
        self._set_active_dock(self.dock_timeline)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            curr = obj
            while curr and not isinstance(curr, QDockWidget):
                curr = curr.parentWidget() if hasattr(curr, 'parentWidget') else None
            if curr and isinstance(curr, QDockWidget):
                self._set_active_dock(curr)
        return super().eventFilter(obj, event)

    def _on_focus_changed(self, old_widget, new_widget):
        if not new_widget:
            return

        dock = new_widget
        while dock and not isinstance(dock, QDockWidget):
            dock = dock.parentWidget()

        if dock and isinstance(dock, QDockWidget):
            self._set_active_dock(dock)

    def _set_active_dock(self, dock: QDockWidget):
        if dock and dock != self._active_dock:
            if self._active_dock:
                self._active_dock.setProperty("active", False)
                self._active_dock.style().unpolish(self._active_dock)
                self._active_dock.style().polish(self._active_dock)
                w_old = self._active_dock.widget()
                if w_old:
                    w_old.setProperty("active", False)
                    w_old.style().unpolish(w_old)
                    w_old.style().polish(w_old)

            self._active_dock = dock
            self._active_dock.setProperty("active", True)
            self._active_dock.style().unpolish(self._active_dock)
            self._active_dock.style().polish(self._active_dock)
            w_new = self._active_dock.widget()
            if w_new:
                w_new.setProperty("active", True)
                w_new.style().unpolish(w_new)
                w_new.style().polish(w_new)

    def connect_signals(self):
        # Pass sequence model to Program Monitor for timeline preview rendering
        self.program_monitor.set_sequence_model(self.timeline_widget.model)

        # Double click media in Project Panel -> Load into Source Monitor
        self.media_pool.media_double_clicked.connect(self._on_media_double_clicked)
        # Insert / Overwrite from Source Monitor -> Add to Timeline Sequence
        self.source_monitor.insert_to_timeline.connect(self._on_insert_clip_to_timeline)
        self.source_monitor.overwrite_to_timeline.connect(self._on_overwrite_clip_to_timeline)

        # Sync Playhead between Program Monitor & Timeline Canvas & Effect Controls
        self.program_monitor.position_changed.connect(self._on_program_monitor_seek)
        self.timeline_widget.playhead_moved.connect(self.program_monitor.seek_to_frame)


    def setup_shortcuts(self):
        # Spacebar: Play/Pause Program Monitor
        self.shortcut_space = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.shortcut_space.activated.connect(self._toggle_program_play)

        # Export Media Shortcut: Ctrl+M
        self.shortcut_export = QShortcut(QKeySequence("Ctrl+M"), self)
        self.shortcut_export.activated.connect(self.on_open_export_dialog)

        # J-K-L Shuttle Navigation
        QShortcut(QKeySequence("j"), self).activated.connect(self._shuttle_j)
        QShortcut(QKeySequence("k"), self).activated.connect(self._shuttle_k)
        QShortcut(QKeySequence("l"), self).activated.connect(self._shuttle_l)

        # Tools Shortcuts: V, C, B
        QShortcut(QKeySequence("v"), self).activated.connect(lambda: self.timeline_widget.set_active_tool("V"))
        QShortcut(QKeySequence("c"), self).activated.connect(lambda: self.timeline_widget.set_active_tool("C"))
        QShortcut(QKeySequence("b"), self).activated.connect(lambda: self.timeline_widget.set_active_tool("B"))

        # In (I) & Out (O) Marks for Source Monitor
        QShortcut(QKeySequence("i"), self).activated.connect(self.source_monitor.set_mark_in)
        QShortcut(QKeySequence("o"), self).activated.connect(self.source_monitor.set_mark_out)

    def _toggle_program_play(self):
        if not self.program_monitor.is_playing:
            logger.info("[TRANSPORT] Playback started via Spacebar.")
            self.program_monitor.shuttle_forward()
            self.vu_meter.start_meter()
        else:
            logger.info("[TRANSPORT] Playback stopped via Spacebar.")
            self.program_monitor.shuttle_stop()
            self.vu_meter.stop_meter()

    def _shuttle_j(self):
        logger.info(f"[TRANSPORT] Shuttle Reverse (J) - Speed: {self.program_monitor.playback_speed}x.")
        self.program_monitor.shuttle_reverse()
        self.vu_meter.start_meter()

    def _shuttle_k(self):
        logger.info("[TRANSPORT] Shuttle Stop (K).")
        self.program_monitor.shuttle_stop()
        self.vu_meter.stop_meter()

    def _shuttle_l(self):
        logger.info(f"[TRANSPORT] Shuttle Forward (L) - Speed: {self.program_monitor.playback_speed}x.")
        self.program_monitor.shuttle_forward()
        self.vu_meter.start_meter()

    def _on_media_double_clicked(self, file_path: str):
        logger.info(f"[MEDIA] Loading media '{file_path}' into Source Monitor.")
        self.source_monitor.load_clip(file_path)
        self.dock_source.raise_()
        self.lbl_status.setText(f"Loaded clip into Source Monitor: {file_path}")

    def _on_insert_clip_to_timeline(self, clip_data: dict):
        logger.info(f"[TIMELINE] Insert command triggered for clip '{clip_data['name']}'.")
        self.timeline_widget.add_clip_to_timeline(clip_data, track_index=2) # Default V1
        self.lbl_status.setText(f"Added '{clip_data['name']}' to Timeline (In: {clip_data['mark_in']}, Out: {clip_data['mark_out']})")

    def _on_overwrite_clip_to_timeline(self, clip_data: dict):
        logger.info(f"[TIMELINE] Overwrite command triggered for clip '{clip_data['name']}'.")
        self.timeline_widget.add_clip_to_timeline(clip_data, track_index=2) # Default V1
        self.lbl_status.setText(f"Overwrote '{clip_data['name']}' on Timeline (In: {clip_data['mark_in']}, Out: {clip_data['mark_out']})")

    def _on_program_monitor_seek(self, frame: int):
        self.timeline_widget.model.playhead_frame = frame
        self.timeline_widget.refresh_timeline()
        self.effect_controls.set_frame(frame)

    def on_import_media_action(self):
        logger.info("[MEDIA] Import Media dialog opened.")
        self.media_pool.on_import_click()

    def on_open_export_dialog(self):
        logger.info("[EXPORT] Opening Export Media dialog (Ctrl+M).")
        dlg = ExportDialog(total_sequence_frames=1800, parent=self)
        dlg.exec()

    def on_open_log_viewer(self):
        logger.info("[LOG] Opening Log Console Inspector dialog.")
        dlg = LogViewerDialog(parent=self)
        dlg.exec()

    def closeEvent(self, event):
        logger.info("[APP] MainWindow closing. Performing clean shutdown sequence...")
        super().closeEvent(event)
