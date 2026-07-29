"""
Custom QProxyStyle for Hedit Pro.
Overrides dock separator hit-test and rendering so the interactive grab zone
is wide (~8 px) while the visible line stays thin (1-2 px), matching the
behaviour of professional NLEs like Premiere Pro and DaVinci Resolve.
"""

from PySide6.QtWidgets import QProxyStyle, QStyle, QStyleOption
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QPen

from gui.theme import COLOR_BG_DARK, COLOR_DIVIDER, COLOR_BG_SELECTED

# Width of the actual interactive grab area (pixels).
SEPARATOR_EXTENT = 8

# Width of the visible line drawn in the center of the grab area (pixels).
SEPARATOR_LINE_WIDTH = 2


class HeditProStyle(QProxyStyle):
    """Application-wide style that provides a wide dock-separator grab zone
    while rendering only a thin visual indicator."""

    # ── Metrics ───────────────────────────────────────────────────────────
    def pixelMetric(self, metric, option=None, widget=None):
        if metric == QStyle.PM_DockWidgetSeparatorExtent:
            return SEPARATOR_EXTENT
        return super().pixelMetric(metric, option, widget)

    # ── Painting ──────────────────────────────────────────────────────────
    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QStyle.PE_IndicatorDockWidgetResizeHandle:
            self._draw_separator(option, painter)
            return
        super().drawPrimitive(element, option, painter, widget)

    def _draw_separator(self, option: QStyleOption, painter: QPainter):
        """Render the dock separator: full area filled with panel background,
        thin center line in divider color, highlighted on hover."""
        rect: QRect = option.rect
        is_hovered = bool(option.state & QStyle.State_MouseOver)
        is_horizontal = rect.width() > rect.height()

        # Fill entire grab zone with panel background so it blends in
        painter.fillRect(rect, QColor(COLOR_BG_DARK))

        # Draw the thin center line
        line_color = QColor(COLOR_DIVIDER)
        painter.setPen(Qt.NoPen)
        painter.setBrush(line_color)

        if is_horizontal:
            # Horizontal separator (divides top/bottom) → thin horizontal line
            center_y = rect.y() + (rect.height() - SEPARATOR_LINE_WIDTH) // 2
            painter.drawRect(rect.x(), center_y, rect.width(), SEPARATOR_LINE_WIDTH)
        else:
            # Vertical separator (divides left/right) → thin vertical line
            center_x = rect.x() + (rect.width() - SEPARATOR_LINE_WIDTH) // 2
            painter.drawRect(center_x, rect.y(), SEPARATOR_LINE_WIDTH, rect.height())
