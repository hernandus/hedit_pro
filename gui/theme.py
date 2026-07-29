"""
Premiere Pro Dark Theme Tokens & Global QSS Styling for Hedit Pro NLE.
Centralized color palette, design tokens, and reusable widget stylesheets.
"""

# ==============================================================================
# COLOR PALETTE TOKENS (Adobe Premiere Pro Dark Theme)
# ==============================================================================
COLOR_BG_DARK = "#1D1D1D"         # Main window, dock background & tree background
COLOR_BG_HOVER = "#242424"        # Item & button hover state background
COLOR_BG_SELECTED = "#2F2F2F"     # Selected item / focus background
COLOR_DIVIDER = "#0E0E0E"         # Fine horizontal divider lines
COLOR_TEXT_PRIMARY = "#FFFFFF"    # Bright text for active/selected items
COLOR_TEXT_REGULAR = "#D4D4D4"    # Regular text color
COLOR_TEXT_MUTED = "#A0A0A0"      # Dimmed header and label text

# ==============================================================================
# REUSABLE WIDGET QSS STYLESHEETS
# ==============================================================================

# Tree View & Media Pool Table Style
TREE_VIEW_QSS = f"""
    QTreeView {{
        background-color: {COLOR_BG_DARK};
        color: {COLOR_TEXT_REGULAR};
        border: none;
        font-size: 12px;
        outline: 0;
    }}
    QTreeView::branch {{
        background-color: {COLOR_BG_DARK};
        border-bottom: 1px solid {COLOR_DIVIDER};
    }}
    QTreeView::item {{
        height: 24px;
        padding: 2px 4px;
        border-bottom: 1px solid {COLOR_DIVIDER};
        border-right: none;
    }}
    QTreeView::item:selected {{
        background-color: {COLOR_BG_SELECTED};
        color: {COLOR_TEXT_PRIMARY};
    }}
    QTreeView::item:hover:!selected {{
        background-color: {COLOR_BG_HOVER};
    }}
"""

# Global Application Stylesheet for MainWindow, Docks, Dialogs & Controls
PREMIERE_DARK_STYLESHEET = f"""
/* Base Palette & Global Settings */
QWidget {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_REGULAR};
    font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
    font-size: 12px;
    selection-background-color: {COLOR_BG_SELECTED};
    selection-color: {COLOR_TEXT_PRIMARY};
    border: none;
}}

QMainWindow {{
    background-color: {COLOR_BG_DARK};
}}

/* Separator rendering is handled by HeditProStyle (gui/style.py) */

/* Dock Widgets & Panels */
QDockWidget {{
    border: 1px solid {COLOR_DIVIDER};
    background-color: {COLOR_BG_DARK};
}}

QDockWidget[active="true"] {{
    border: 2px solid #2680EB;
}}

QDockWidget::title {{
    background-color: {COLOR_BG_DARK};
    padding: 6px 10px;
    font-weight: bold;
    font-size: 11px;
    color: {COLOR_TEXT_MUTED};
    border-bottom: 1px solid {COLOR_DIVIDER};
}}

QDockWidget[active="true"]::title {{
    color: {COLOR_TEXT_PRIMARY};
    background-color: #242424;
    border-bottom: 2px solid #2680EB;
}}

/* Dock Tab Bar (Top Tabs like Premiere Pro) */
QTabBar {{
    background-color: {COLOR_BG_DARK};
    border: none;
    border-bottom: none;
}}

QTabBar::tab {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_MUTED};
    padding: 6px 6px;
    font-size: 11px;
    font-weight: bold;
    border: none;
    border-bottom: 2px solid transparent;
}}

QTabBar::tab:selected {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_PRIMARY};
    border-bottom: 2px solid #2680EB;
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLOR_BG_HOVER};
    color: {COLOR_TEXT_REGULAR};
}}

/* Scrollbars */
QScrollBar:vertical {{
    background-color: {COLOR_BG_DARK};
    width: 10px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background-color: #2b2b2b;
    min-height: 20px;
    border-radius: 3px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: #383838;
}}

QScrollBar:horizontal {{
    background-color: {COLOR_BG_DARK};
    height: 10px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background-color: #2b2b2b;
    min-width: 20px;
    border-radius: 3px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: #383838;
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0px;
    height: 0px;
}}

/* Context Menus */
QMenu {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_REGULAR};
    border: 1px solid {COLOR_DIVIDER};
    padding: 4px 0px;
}}

QMenu::item {{
    padding: 6px 24px 6px 12px;
}}

QMenu::item:selected {{
    background-color: {COLOR_BG_SELECTED};
    color: {COLOR_TEXT_PRIMARY};
}}

QMenu::separator {{
    height: 1px;
    background-color: {COLOR_DIVIDER};
    margin: 4px 8px;
}}
"""
