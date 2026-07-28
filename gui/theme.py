"""
Premiere Pro Charcoal Dark Theme QSS Styling for PySide6.
Colors inspired by Adobe Premiere Pro UI guidelines.
"""

PREMIERE_DARK_STYLESHEET = """
/* Base Palette & Global Settings */
QWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
    font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
    font-size: 12px;
    selection-background-color: #2680eb;
    selection-color: #ffffff;
    border: none;
}

QMainWindow {
    background-color: #141414;
}

QMainWindow::separator {
    background-color: #2b2b2b;
    width: 4px;
    height: 4px;
}

QMainWindow::separator:hover {
    background-color: #2680eb;
}

/* Dock Widgets & Panels */
QDockWidget {
    titlebar-close-icon: url(close.png);
    titlebar-normal-icon: url(float.png);
    border: 1px solid #2b2b2b;
    background-color: #1e1e1e;
}

QDockWidget::title {
    background-color: #282828;
    padding: 6px 10px;
    font-weight: bold;
    font-size: 11px;
    color: #a0a0a0;
    border-bottom: 1px solid #2b2b2b;
}

QDockWidget::title:focus {
    color: #2680eb;
}

/* Tab Bar inside Docked Panels */
QTabWidget::pane {
    border: 1px solid #2b2b2b;
    background-color: #1e1e1e;
}

QTabBar::tab {
    background-color: #222222;
    color: #888888;
    padding: 6px 14px;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    margin-right: 2px;
    font-weight: 500;
    border: 1px solid #2b2b2b;
    border-bottom: none;
}

QTabBar::tab:selected {
    background-color: #1e1e1e;
    color: #2680eb;
    border-top: 2px solid #2680eb;
}

QTabBar::tab:hover:!selected {
    background-color: #2a2a2a;
    color: #cccccc;
}

/* Toolbars */
QToolBar {
    background-color: #242424;
    border-bottom: 1px solid #2b2b2b;
    spacing: 4px;
    padding: 4px;
}

QToolButton {
    background-color: transparent;
    color: #cccccc;
    border-radius: 3px;
    padding: 5px 8px;
    font-size: 11px;
}

QToolButton:hover {
    background-color: #333333;
    color: #ffffff;
}

QToolButton:pressed, QToolButton:checked {
    background-color: #2680eb;
    color: #ffffff;
}

/* Buttons */
QPushButton {
    background-color: #2a2a2a;
    color: #e0e0e0;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #383838;
    border-color: #2680eb;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #2680eb;
    border-color: #1a60b0;
    color: #ffffff;
}

QPushButton:disabled {
    background-color: #1c1c1c;
    color: #555555;
    border-color: #282828;
}

/* Menu Bar & Context Menus */
QMenuBar {
    background-color: #181818;
    color: #cccccc;
    border-bottom: 1px solid #2b2b2b;
    padding: 2px;
}

QMenuBar::item {
    background-color: transparent;
    padding: 4px 10px;
    border-radius: 3px;
}

QMenuBar::item:selected {
    background-color: #2680eb;
    color: #ffffff;
}

QMenu {
    background-color: #242424;
    color: #e0e0e0;
    border: 1px solid #383838;
    padding: 4px 0px;
}

QMenu::item {
    padding: 6px 24px 6px 12px;
}

QMenu::item:selected {
    background-color: #2680eb;
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background-color: #333333;
    margin: 4px 8px;
}

/* Status Bar */
QStatusBar {
    background-color: #181818;
    color: #888888;
    border-top: 1px solid #2b2b2b;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #181818;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #333333;
    min-height: 20px;
    border-radius: 4px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4f4f4f;
}

QScrollBar:horizontal {
    background-color: #181818;
    height: 10px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background-color: #333333;
    min-width: 20px;
    border-radius: 4px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #4f4f4f;
}

QScrollBar::add-line, QScrollBar::sub-line {
    width: 0px;
    height: 0px;
}

/* Input Controls */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #181818;
    color: #e0e0e0;
    border: 1px solid #333333;
    border-radius: 3px;
    padding: 4px 8px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #2680eb;
}

/* Tree & List Views (Project Panel) */
QTreeView, QListView, QTableView {
    background-color: #1a1a1a;
    color: #d0d0d0;
    border: 1px solid #282828;
    alternate-background-color: #1e1e1e;
}

QTreeView::item, QListView::item {
    padding: 4px;
}

QTreeView::item:selected, QListView::item:selected {
    background-color: #2680eb;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #242424;
    color: #999999;
    padding: 4px 8px;
    border: none;
    border-right: 1px solid #2d2d2d;
    border-bottom: 1px solid #2d2d2d;
    font-weight: bold;
}
"""
