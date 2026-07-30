"""
test_docking.py — Baseline mínimo con hamburger menu ≡.

Sin temas, sin subclases. QDockWidget puro + PremiereDockTitleBar clonado de la app real.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDockWidget, QWidget, QLabel,
    QVBoxLayout, QStatusBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from gui.widgets.panel_header import PremiereDockTitleBar
from gui.widgets.timeline.canvas import TimelineCanvasWidget
from gui.widgets.media_pool.browser import MediaPoolWidget
from gui.widgets.monitors.source import SourceMonitorWidget
from gui.widgets.monitors.program import ProgramMonitorWidget
from gui.widgets.inspector.transform import EffectControlsWidget
from gui.widgets.color.wheels import LumetriColorWidget


def empty_panel(name: str) -> QWidget:
    w = QWidget()
    w.setMinimumSize(0, 0)
    w.setAttribute(Qt.WA_StyledBackground, True)
    w.setStyleSheet("QWidget { border: 1px solid #555; }")
    layout = QVBoxLayout(w)
    layout.setContentsMargins(4, 4, 4, 4)
    lbl = QLabel(name)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setFont(QFont("monospace", 10))
    lbl.setStyleSheet("color: #555; border: none;")
    layout.addWidget(lbl)
    return w


class BaselineWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qt Docking Baseline — 3 paneles")
        self.resize(1600, 950)

        self.setDockOptions(
            QMainWindow.AllowNestedDocks |
            QMainWindow.AllowTabbedDocks |
            QMainWindow.AnimatedDocks
        )

        # Esquinas inferiores → área bottom (full width horizontal)
        self.setCorner(Qt.BottomLeftCorner,  Qt.BottomDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.BottomDockWidgetArea)

        # Panel izquierdo — Media Pool real
        self.media_pool = MediaPoolWidget(project_name="sample movie name")
        self.dock_left = QDockWidget("Project: sample movie name", self)
        self.dock_left.setWidget(self.media_pool)
        self.dock_left.setMinimumSize(0, 0)
        self.dock_left.setTitleBarWidget(PremiereDockTitleBar(self.dock_left, "Project: sample movie name"))
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_left)

        # Effect Controls — a la derecha del Media Pool
        self.effect_controls = EffectControlsWidget()
        self.dock_effects = QDockWidget("Effect Controls", self)
        self.dock_effects.setWidget(self.effect_controls)
        self.dock_effects.setMinimumSize(0, 0)
        self.dock_effects.setTitleBarWidget(PremiereDockTitleBar(self.dock_effects, "Effect Controls"))
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_effects)
        self.splitDockWidget(self.dock_left, self.dock_effects, Qt.Horizontal)

        # Lumetri Color — tabulado junto a Effect Controls
        self.color_widget = LumetriColorWidget()
        self.dock_lumetri = QDockWidget("Lumetri Color", self)
        self.dock_lumetri.setWidget(self.color_widget)
        self.dock_lumetri.setMinimumSize(0, 0)
        self.tabifyDockWidget(self.dock_effects, self.dock_lumetri)
        self.dock_effects.raise_()

        # Panel derecho — Source Monitor (spliteado a la derecha de Effect Controls)
        self.source_monitor = SourceMonitorWidget()
        self.dock_right = QDockWidget("Source Monitor", self)
        self.dock_right.setWidget(self.source_monitor)
        self.dock_right.setMinimumSize(0, 0)
        self.dock_right.setTitleBarWidget(PremiereDockTitleBar(self.dock_right, "Source Monitor"))
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_right)
        self.splitDockWidget(self.dock_effects, self.dock_right, Qt.Horizontal)

        # Program Monitor — a la derecha del Source Monitor
        self.program_monitor = ProgramMonitorWidget()
        self.dock_program = QDockWidget("Program Monitor", self)
        self.dock_program.setWidget(self.program_monitor)
        self.dock_program.setMinimumSize(0, 0)
        self.dock_program.setTitleBarWidget(PremiereDockTitleBar(self.dock_program, "Program Monitor"))
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_program)
        self.splitDockWidget(self.dock_right, self.dock_program, Qt.Horizontal)

        # Panel inferior — TimelineCanvasWidget real (sin MLT engine)
        self.timeline_widget = TimelineCanvasWidget()
        self.dock_bottom = QDockWidget("Timeline: Main Sequence", self)
        self.dock_bottom.setWidget(self.timeline_widget)
        self.dock_bottom.setMinimumSize(0, 0)
        self.dock_bottom.setTitleBarWidget(PremiereDockTitleBar(self.dock_bottom, "Timeline: Main Sequence"))
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_bottom)

        # Central widget — mínimo 0px para no aparecer entre paneles (todos los
        # docks están en LeftDockWidgetArea), pero SIN fijar el máximo: Qt necesita
        # poder ajustar su altura como "slack" vertical al arrastrar el separador
        # entre el área superior y el dock inferior.
        dummy = QWidget()
        dummy.setMinimumSize(0, 0)
        self.setCentralWidget(dummy)

        sb = QStatusBar()
        self.setStatusBar(sb)
        sb.showMessage("Baseline: 3 paneles puros — Left + Right + Bottom full width")


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    window = BaselineWindow()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
