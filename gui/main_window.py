"""
Primary Dockable MainWindow for Hedit Pro.
Arranges panels in Premiere Pro workspace layout using QDockWidgets and QTabWidget.
Connects signals across Media Pool, Source Monitor, Program Monitor, and Timeline.
"""

from PySide6.QtWidgets import (
    QMainWindow, QDockWidget, QTabWidget, QStatusBar, QMenuBar,
    QMenu, QLabel, QWidget
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QKeySequence, QAction, QShortcut

from core.engine import MLTEngine
from gui.widgets.monitors.source import SourceMonitorWidget
from gui.widgets.monitors.program import ProgramMonitorWidget
from gui.widgets.timeline.canvas import TimelineCanvasWidget
from gui.widgets.media_pool.browser import MediaPoolWidget
from gui.widgets.inspector.transform import EffectControlsWidget
from gui.widgets.color.wheels import LumetriColorWidget


class MainWindow(QMainWindow):
    """Premiere Pro inspired Main Workspace Window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hedit Pro - Adobe Premiere Pro Clone [Linux NLE]")
        self.resize(1600, 950)

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

        # Help Menu
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("About Hedit Pro")

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
        self.dock_media = QDockWidget("Project: Untitled", self)
        self.media_pool = MediaPoolWidget()
        self.dock_media.setWidget(self.media_pool)

        # 2. Source Monitor & Effect Controls Tabbed Dock (Top Left)
        self.dock_top_left = QDockWidget("Source & Inspector", self)
        self.top_left_tabs = QTabWidget()
        self.source_monitor = SourceMonitorWidget()
        self.effect_controls = EffectControlsWidget()
        self.top_left_tabs.addTab(self.source_monitor, "Source Monitor")
        self.top_left_tabs.addTab(self.effect_controls, "Effect Controls")
        self.dock_top_left.setWidget(self.top_left_tabs)

        # 3. Program Monitor & Lumetri Color Tabbed Dock (Top Right)
        self.dock_top_right = QDockWidget("Program & Color", self)
        self.top_right_tabs = QTabWidget()
        self.program_monitor = ProgramMonitorWidget()
        self.color_widget = LumetriColorWidget()
        self.top_right_tabs.addTab(self.program_monitor, "Program Monitor")
        self.top_right_tabs.addTab(self.color_widget, "Lumetri Color")
        self.dock_top_right.setWidget(self.top_right_tabs)

        # 4. Timeline Dock (Bottom Right)
        self.dock_timeline = QDockWidget("Timeline: Main Sequence", self)
        self.timeline_widget = TimelineCanvasWidget()
        self.dock_timeline.setWidget(self.timeline_widget)

        # Arrange Docks in Premiere Layout
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_top_left)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_top_right)
        
        self.splitDockWidget(self.dock_top_left, self.dock_media, Qt.Vertical)
        self.splitDockWidget(self.dock_top_right, self.dock_timeline, Qt.Vertical)

        # Adjust initial relative sizes
        self.resizeDocks([self.dock_top_left, self.dock_top_right], [450, 450], Qt.Vertical)

    def connect_signals(self):
        # Double click media in Project Panel -> Load into Source Monitor
        self.media_pool.media_double_clicked.connect(self._on_media_double_clicked)
        # Insert / Overwrite from Source Monitor -> Add to Timeline Sequence
        self.source_monitor.insert_to_timeline.connect(self._on_insert_clip_to_timeline)
        self.source_monitor.overwrite_to_timeline.connect(self._on_overwrite_clip_to_timeline)

    def setup_shortcuts(self):
        # Spacebar: Play/Pause Program Monitor
        self.shortcut_space = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.shortcut_space.activated.connect(self.program_monitor.shuttle_forward if not self.program_monitor.is_playing else self.program_monitor.shuttle_stop)

        # J-K-L Shuttle Navigation
        QShortcut(QKeySequence("j"), self).activated.connect(self.program_monitor.shuttle_reverse)
        QShortcut(QKeySequence("k"), self).activated.connect(self.program_monitor.shuttle_stop)
        QShortcut(QKeySequence("l"), self).activated.connect(self.program_monitor.shuttle_forward)

        # In (I) & Out (O) Marks for Source Monitor
        QShortcut(QKeySequence("i"), self).activated.connect(self.source_monitor.set_mark_in)
        QShortcut(QKeySequence("o"), self).activated.connect(self.source_monitor.set_mark_out)

    def _on_media_double_clicked(self, file_path: str):
        self.source_monitor.load_clip(file_path)
        self.top_left_tabs.setCurrentWidget(self.source_monitor)
        self.lbl_status.setText(f"Loaded clip into Source Monitor: {file_path}")

    def _on_insert_clip_to_timeline(self, clip_data: dict):
        self.lbl_status.setText(f"Inserted '{clip_data['name']}' into Timeline (In: {clip_data['mark_in']}, Out: {clip_data['mark_out']})")

    def _on_overwrite_clip_to_timeline(self, clip_data: dict):
        self.lbl_status.setText(f"Overwrote '{clip_data['name']}' into Timeline (In: {clip_data['mark_in']}, Out: {clip_data['mark_out']})")

    def on_import_media_action(self):
        self.media_pool.on_import_click()
