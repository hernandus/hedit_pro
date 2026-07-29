"""
Premiere Pro Style Panel Headers, Hamburger Context Menu (≡), and Title Truncation for Hedit Pro.
Supports single dock custom title bars, tabified QTabBar header option menus, and dynamic layout tracking.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QToolButton, QMenu, QDockWidget, QTabBar, QMainWindow
)
from PySide6.QtCore import Qt, QPoint, QObject, QEvent
from PySide6.QtGui import QAction, QFont


def truncate_title(title: str, max_chars: int = 30) -> str:
    """Truncates panel titles longer than max_chars with ellipsis (...)."""
    if not title:
        return ""
    if len(title) > max_chars:
        return title[:max_chars - 3] + "..."
    return title


def create_panel_context_menu(dock: QDockWidget, parent: QWidget = None) -> QMenu:
    """Creates Premiere Pro context menu for a panel with 'Close Panel' and 'Undock Panel' options."""
    menu = QMenu(parent or dock)

    # Action 1: Close Panel
    act_close = QAction("Close Panel", menu)
    act_close.triggered.connect(dock.close)
    menu.addAction(act_close)

    # Action 2: Undock Panel
    act_undock = QAction("Undock Panel", menu)
    act_undock.triggered.connect(lambda: dock.setFloating(True))
    menu.addAction(act_undock)

    return menu


class PremiereDockTitleBar(QWidget):
    """Custom title bar for single (un-tabified) QDockWidget instances with title and hamburger menu (≡)."""

    def __init__(self, dock: QDockWidget, title_text: str = None, parent=None):
        super().__init__(parent or dock)
        self.dock = dock
        self.raw_title = title_text or dock.windowTitle()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 6, 4)
        layout.setSpacing(4)

        display_text = truncate_title(self.raw_title, max_chars=30)
        self.lbl_title = QLabel(display_text)
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #A0A0A0;")
        self.lbl_title.setToolTip(self.raw_title)
        layout.addWidget(self.lbl_title)

        layout.addStretch()

        # Hamburger Menu Button (≡)
        self.btn_menu = QToolButton(self)
        self.btn_menu.setText("≡")
        self.btn_menu.setToolTip("Panel Options")
        self.btn_menu.setFixedSize(18, 18)
        self.btn_menu.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                color: #A0A0A0;
                font-weight: bold;
                font-size: 12px;
                padding: 0px;
            }
            QToolButton:hover {
                color: #FFFFFF;
                background-color: #333333;
                border-radius: 2px;
            }
        """)
        self.btn_menu.clicked.connect(self._show_menu)
        layout.addWidget(self.btn_menu)

    def set_title(self, text: str):
        self.raw_title = text
        self.lbl_title.setText(truncate_title(text, max_chars=30))
        self.lbl_title.setToolTip(text)

    def _show_menu(self):
        menu = create_panel_context_menu(self.dock, self)
        menu.exec(self.btn_menu.mapToGlobal(QPoint(0, self.btn_menu.height())))

    def contextMenuEvent(self, event):
        menu = create_panel_context_menu(self.dock, self)
        menu.exec(event.globalPos())


class PanelHeaderManager(QObject):
    """
    Monitors layout changes, dock drags, tab moves, and float state changes
    to keep hamburger buttons (≡), truncated titles, and custom title bars in sync dynamically.
    """

    def __init__(self, main_window: QMainWindow):
        super().__init__(main_window)
        self.main_window = main_window
        self._all_docks = [
            main_window.dock_media,
            main_window.dock_source,
            main_window.dock_program,
            main_window.dock_timeline,
            main_window.dock_effect_controls,
            main_window.dock_lumetri
        ]

        # Connect dock float / location change signals
        for dock in self._all_docks:
            dock.topLevelChanged.connect(self.refresh)
            dock.dockLocationChanged.connect(self.refresh)

        # Install event filter on main window to catch layout / child changes
        main_window.installEventFilter(self)

        # Initial refresh
        self.refresh()

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.ChildAdded, QEvent.ChildRemoved, QEvent.LayoutRequest):
            self.refresh()
        return super().eventFilter(obj, event)

    def refresh(self):
        try:
            if not self.main_window or not self.main_window.isVisible():
                return
        except RuntimeError:
            return

        dock_title_map = {}
        for dock in self._all_docks:
            raw = dock.windowTitle()
            dock_title_map[raw] = dock
            dock_title_map[truncate_title(raw, 30)] = dock

            # Update title bar widget based on standalone vs tabified state
            is_tabbed = len(self.main_window.tabifiedDockWidgets(dock)) > 0
            if is_tabbed:
                if type(dock.titleBarWidget()).__name__ != "QWidget":
                    empty_title = QWidget()
                    empty_title.setFixedHeight(0)
                    dock.setTitleBarWidget(empty_title)
            else:
                if type(dock.titleBarWidget()).__name__ != "PremiereDockTitleBar":
                    dock.setTitleBarWidget(PremiereDockTitleBar(dock, raw))

        # Scan all QTabBar instances
        for tb in self.main_window.findChildren(QTabBar):
            if tb.parentWidget() and not isinstance(tb.parentWidget(), QMainWindow):
                parent_name = type(tb.parentWidget()).__name__
                if "Dock" not in parent_name and "Main" not in parent_name:
                    continue

            tb.setContextMenuPolicy(Qt.CustomContextMenu)
            tb.setElideMode(Qt.ElideNone)

            def _make_context_handler(tabBar=tb):
                return lambda pos: self._on_tab_context_menu(tabBar, pos, dock_title_map)

            if not tb.property("context_connected"):
                tb.setProperty("context_connected", True)
                tb.customContextMenuRequested.connect(_make_context_handler(tb))

            for i in range(tb.count()):
                orig_text = tb.tabText(i)
                truncated = truncate_title(orig_text, 30)
                if orig_text != truncated:
                    tb.setTabText(i, truncated)
                tb.setTabToolTip(i, orig_text)

                # Ensure hamburger button is attached to each tab
                if not tb.tabButton(i, QTabBar.RightSide):
                    dock = dock_title_map.get(orig_text) or dock_title_map.get(truncated)
                    if dock:
                        btn = QToolButton(tb)
                        btn.setText("≡")
                        btn.setToolTip("Panel Options")
                        btn.setFixedSize(16, 16)
                        btn.setStyleSheet("""
                            QToolButton {
                                background: transparent;
                                border: none;
                                color: #A0A0A0;
                                font-weight: bold;
                                font-size: 11px;
                                padding: 0px;
                            }
                            QToolButton:hover {
                                color: #FFFFFF;
                                background-color: #333333;
                                border-radius: 2px;
                            }
                        """)
                        def _make_show_menu(d=dock, b=btn):
                            return lambda: create_panel_context_menu(d, b).exec(b.mapToGlobal(QPoint(0, b.height())))

                        btn.clicked.connect(_make_show_menu(dock, btn))
                        tb.setTabButton(i, QTabBar.RightSide, btn)

    def _on_tab_context_menu(self, tabBar, pos, dock_title_map):
        idx = tabBar.tabAt(pos)
        if idx >= 0:
            text = tabBar.tabText(idx)
            dock = dock_title_map.get(text)
            if dock:
                menu = create_panel_context_menu(dock, tabBar)
                menu.exec(tabBar.mapToGlobal(pos))


def setup_panel_headers(main_window: QMainWindow) -> PanelHeaderManager:
    """Configures dynamic PanelHeaderManager for MainWindow."""
    return PanelHeaderManager(main_window)
