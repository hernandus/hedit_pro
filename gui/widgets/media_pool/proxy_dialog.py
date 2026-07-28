"""
Create Proxy Media Dialog for Hedit Pro.
Premiere Pro / DaVinci Resolve inspired proxy generation workflow.
"""

import os
from typing import List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QProgressBar, QGroupBox, QFormLayout,
    QListWidget, QListWidgetItem, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QIcon

from core.proxy import (
    PROXY_CODECS, PROXY_DIMENSIONS,
    ProxyWorkerThread, get_proxy_output_path,
)


# ---------------------------------------------------------------------------
# Stylesheet helpers
# ---------------------------------------------------------------------------

_ACCENT      = "#2680eb"
_ACCENT_DARK = "#1a6bc4"
_BG_PANEL    = "#1e1e1e"
_BG_INPUT    = "#2a2a2a"
_BG_LIST     = "#161616"
_BORDER      = "#3a3a3a"
_TEXT_DIM    = "#888888"
_TEXT_MAIN   = "#d4d4d4"
_GREEN       = "#23c55e"
_RED         = "#e05252"
_YELLOW      = "#e8a838"

_GROUPBOX_QSS = f"""
QGroupBox {{
    font-size: 10px;
    font-weight: 600;
    color: {_TEXT_DIM};
    border: 1px solid {_BORDER};
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 6px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {_TEXT_DIM};
    letter-spacing: 1px;
    text-transform: uppercase;
}}
"""

_COMBO_QSS = f"""
QComboBox {{
    background: {_BG_INPUT};
    color: {_TEXT_MAIN};
    border: 1px solid {_BORDER};
    border-radius: 3px;
    padding: 4px 8px;
    font-size: 11px;
    min-height: 22px;
}}
QComboBox:hover {{ border-color: {_ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {_BG_INPUT};
    color: {_TEXT_MAIN};
    border: 1px solid {_BORDER};
    selection-background-color: {_ACCENT};
}}
"""

_BTN_QSS = f"""
QPushButton {{
    background: {_BG_INPUT};
    color: {_TEXT_MAIN};
    border: 1px solid {_BORDER};
    border-radius: 3px;
    padding: 5px 14px;
    font-size: 11px;
}}
QPushButton:hover {{ background: #383838; border-color: #606060; }}
QPushButton:pressed {{ background: #2a2a2a; }}
QPushButton:disabled {{ color: #555; border-color: #333; }}
"""

_BTN_PRIMARY_QSS = f"""
QPushButton {{
    background: {_ACCENT};
    color: #ffffff;
    border: none;
    border-radius: 3px;
    padding: 5px 18px;
    font-size: 11px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {_ACCENT_DARK}; }}
QPushButton:pressed {{ background: #1259a8; }}
QPushButton:disabled {{ background: #2a3a50; color: #567; }}
"""

_PROGRESS_QSS = f"""
QProgressBar {{
    height: 6px;
    border-radius: 3px;
    background: #2a2a2a;
    border: none;
    text-align: center;
}}
QProgressBar::chunk {{
    border-radius: 3px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {_ACCENT}, stop:1 #5ba8ff);
}}
"""

_PROGRESS_OVERALL_QSS = f"""
QProgressBar {{
    height: 4px;
    border-radius: 2px;
    background: #242424;
    border: none;
}}
QProgressBar::chunk {{
    border-radius: 2px;
    background: {_GREEN};
}}
"""


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

class CreateProxyDialog(QDialog):
    """
    Dialog for configuring and monitoring proxy media creation.

    Workflow:
      1. User picks codec + dimensions → clicks "Create Proxies"
      2. ProxyWorkerThread encodes the queue one file at a time
      3. Per-file and overall progress bars update in real time
      4. On completion, the dialog shows a summary and allows closing
    """

    def __init__(self, file_paths: List[str], parent=None):
        super().__init__(parent)
        self.file_paths  = file_paths
        self.worker: ProxyWorkerThread = None
        self._total      = len(file_paths)
        self._done_count = 0
        self._fail_count = 0

        self.setWindowTitle("Create Proxy Media")
        self.setFixedWidth(510)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(f"background-color: {_BG_PANEL}; color: {_TEXT_MAIN};")

        self._build_ui()
        self._update_output_label()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ── Title ──────────────────────────────────────────────────────
        title = QLabel("CREATE PROXY MEDIA")
        title.setFont(QFont("Inter", 11, QFont.Bold))
        title.setStyleSheet(f"color: {_ACCENT}; letter-spacing: 1px;")
        root.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {_BORDER};")
        root.addWidget(sep)

        # ── Source Files ───────────────────────────────────────────────
        files_box = QGroupBox(f"Source Files  —  {self._total} file(s) selected")
        files_box.setStyleSheet(_GROUPBOX_QSS)
        files_layout = QVBoxLayout(files_box)
        files_layout.setContentsMargins(8, 6, 8, 8)

        self.list_widget = QListWidget()
        self.list_widget.setMaximumHeight(100)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background: {_BG_LIST};
                color: {_TEXT_MAIN};
                border: 1px solid {_BORDER};
                border-radius: 3px;
                font-size: 11px;
                padding: 2px 4px;
            }}
            QListWidget::item {{ padding: 2px 0; }}
            QListWidget::item:selected {{ background: #2a3d5a; color: #fff; }}
        """)
        self.list_widget.setSelectionMode(QListWidget.NoSelection)

        for path in self.file_paths:
            item = QListWidgetItem(f"  {os.path.basename(path)}")
            item.setForeground(QColor(_TEXT_MAIN))
            self.list_widget.addItem(item)

        files_layout.addWidget(self.list_widget)
        root.addWidget(files_box)

        # ── Transcode Settings ─────────────────────────────────────────
        settings_box = QGroupBox("Transcode Settings")
        settings_box.setStyleSheet(_GROUPBOX_QSS)
        form = QFormLayout(settings_box)
        form.setContentsMargins(10, 8, 10, 10)
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        lbl_codec = QLabel("Codec:")
        lbl_codec.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px;")

        self.codec_combo = QComboBox()
        self.codec_combo.setStyleSheet(_COMBO_QSS)
        for name, info in PROXY_CODECS.items():
            self.codec_combo.addItem(name)
        self.codec_combo.currentTextChanged.connect(self._on_codec_changed)
        form.addRow(lbl_codec, self.codec_combo)

        lbl_dim = QLabel("Dimensions:")
        lbl_dim.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px;")

        self.dim_combo = QComboBox()
        self.dim_combo.setStyleSheet(_COMBO_QSS)
        for label in PROXY_DIMENSIONS.keys():
            self.dim_combo.addItem(label)
        self.dim_combo.currentTextChanged.connect(self._update_output_label)
        form.addRow(lbl_dim, self.dim_combo)

        lbl_out_title = QLabel("Output folder:")
        lbl_out_title.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 11px;")

        self.lbl_output = QLabel()
        self.lbl_output.setStyleSheet(f"color: {_YELLOW}; font-size: 10px; font-family: monospace;")
        self.lbl_output.setWordWrap(True)
        form.addRow(lbl_out_title, self.lbl_output)

        self.lbl_codec_desc = QLabel()
        self.lbl_codec_desc.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 10px; font-style: italic;")
        self.lbl_codec_desc.setWordWrap(True)
        self._on_codec_changed(self.codec_combo.currentText())
        form.addRow("", self.lbl_codec_desc)

        root.addWidget(settings_box)

        # ── Progress ───────────────────────────────────────────────────
        self.progress_box = QGroupBox("Progress")
        self.progress_box.setStyleSheet(_GROUPBOX_QSS)
        prog_layout = QVBoxLayout(self.progress_box)
        prog_layout.setContentsMargins(10, 8, 10, 10)
        prog_layout.setSpacing(6)

        # Current file label
        self.lbl_current_file = QLabel("Waiting…")
        self.lbl_current_file.setStyleSheet(f"color: {_TEXT_MAIN}; font-size: 11px;")
        prog_layout.addWidget(self.lbl_current_file)

        # Per-file progress
        self.file_progress_bar = QProgressBar()
        self.file_progress_bar.setRange(0, 100)
        self.file_progress_bar.setValue(0)
        self.file_progress_bar.setTextVisible(False)
        self.file_progress_bar.setStyleSheet(_PROGRESS_QSS)
        prog_layout.addWidget(self.file_progress_bar)

        # FPS + percent row
        fps_row = QHBoxLayout()
        self.lbl_file_pct = QLabel("0%")
        self.lbl_file_pct.setStyleSheet(f"color: {_ACCENT}; font-size: 11px; font-weight: 600;")
        self.lbl_fps = QLabel("")
        self.lbl_fps.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 10px;")
        fps_row.addWidget(self.lbl_file_pct)
        fps_row.addStretch()
        fps_row.addWidget(self.lbl_fps)
        prog_layout.addLayout(fps_row)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet(f"color: {_BORDER};")
        prog_layout.addWidget(sep2)

        # Overall progress
        self.lbl_overall = QLabel(f"Overall: 0 / {self._total}")
        self.lbl_overall.setStyleSheet(f"color: {_TEXT_DIM}; font-size: 10px;")
        prog_layout.addWidget(self.lbl_overall)

        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setRange(0, self._total)
        self.overall_progress_bar.setValue(0)
        self.overall_progress_bar.setTextVisible(False)
        self.overall_progress_bar.setStyleSheet(_PROGRESS_OVERALL_QSS)
        prog_layout.addWidget(self.overall_progress_bar)

        root.addWidget(self.progress_box)

        # ── Buttons ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet(_BTN_QSS)
        self.btn_cancel.setFixedHeight(28)
        self.btn_cancel.clicked.connect(self._on_cancel)

        self.btn_create = QPushButton("Create Proxies")
        self.btn_create.setStyleSheet(_BTN_PRIMARY_QSS)
        self.btn_create.setFixedHeight(28)
        self.btn_create.clicked.connect(self._on_create)

        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_create)
        root.addLayout(btn_row)

        self.adjustSize()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _current_longest_side(self) -> int:
        label = self.dim_combo.currentText()
        return PROXY_DIMENSIONS.get(label, 1280)

    def _on_codec_changed(self, codec_name: str):
        desc = PROXY_CODECS.get(codec_name, {}).get("description", "")
        self.lbl_codec_desc.setText(desc)
        self._update_output_label()

    def _update_output_label(self):
        if not self.file_paths:
            return
        longest = self._current_longest_side()
        codec   = self.codec_combo.currentText()
        sample_out = get_proxy_output_path(self.file_paths[0], longest, codec)
        folder = os.path.dirname(sample_out)
        self.lbl_output.setText(folder)

    def _set_controls_enabled(self, enabled: bool):
        self.codec_combo.setEnabled(enabled)
        self.dim_combo.setEnabled(enabled)
        self.btn_create.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Slots — buttons
    # ------------------------------------------------------------------

    def _on_create(self):
        codec_name   = self.codec_combo.currentText()
        longest_side = self._current_longest_side()

        self._set_controls_enabled(False)
        self.btn_cancel.setText("Stop")
        self.lbl_current_file.setText("Starting…")

        self.worker = ProxyWorkerThread(self.file_paths, codec_name, longest_side, parent=self)
        self.worker.queue_started.connect(self._on_queue_started)
        self.worker.file_started.connect(self._on_file_started)
        self.worker.file_progress.connect(self._on_file_progress)
        self.worker.file_completed.connect(self._on_file_completed)
        self.worker.file_failed.connect(self._on_file_failed)
        self.worker.queue_completed.connect(self._on_queue_completed)
        self.worker.start()

    def _on_cancel(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.btn_cancel.setEnabled(False)
            self.lbl_current_file.setText("Stopping…")
        else:
            self.reject()

    # ------------------------------------------------------------------
    # Slots — worker signals
    # ------------------------------------------------------------------

    def _on_queue_started(self, total: int):
        self.overall_progress_bar.setRange(0, total)
        self.lbl_overall.setText(f"Overall: 0 / {total}")

    def _on_file_started(self, idx: int, filename: str):
        self.lbl_current_file.setText(f"Encoding ({idx}/{self._total}):  {filename}")
        self.file_progress_bar.setValue(0)
        self.lbl_file_pct.setText("0%")
        self.lbl_fps.setText("")

        # Highlight active item in list
        self.list_widget.item(idx - 1).setForeground(QColor("#5ba8ff"))

    def _on_file_progress(self, idx: int, percent: int, fps: float):
        self.file_progress_bar.setValue(percent)
        self.lbl_file_pct.setText(f"{percent}%")
        if fps > 0:
            self.lbl_fps.setText(f"{fps:.1f} fps")

    def _on_file_completed(self, idx: int, source: str, output: str):
        self._done_count += 1
        self.overall_progress_bar.setValue(self._done_count + self._fail_count)
        self.lbl_overall.setText(
            f"Overall: {self._done_count + self._fail_count} / {self._total}  "
            f"({self._done_count} ok, {self._fail_count} failed)"
        )
        # Mark item green
        item = self.list_widget.item(idx - 1)
        item.setText(f"  ✓  {os.path.basename(source)}")
        item.setForeground(QColor(_GREEN))

    def _on_file_failed(self, idx: int, source: str, error: str):
        self._fail_count += 1
        self.overall_progress_bar.setValue(self._done_count + self._fail_count)
        self.lbl_overall.setText(
            f"Overall: {self._done_count + self._fail_count} / {self._total}  "
            f"({self._done_count} ok, {self._fail_count} failed)"
        )
        item = self.list_widget.item(idx - 1)
        item.setText(f"  ✗  {os.path.basename(source)}")
        item.setForeground(QColor(_RED))

    def _on_queue_completed(self, completed: int, failed: int):
        self.lbl_fps.setText("")
        self.btn_cancel.setText("Close")
        self.btn_cancel.setEnabled(True)

        if failed == 0:
            self.lbl_current_file.setText(
                f"✓  Done — {completed} proxy file(s) created successfully."
            )
            self.lbl_current_file.setStyleSheet(f"color: {_GREEN}; font-size: 11px; font-weight: 600;")
        elif completed == 0:
            self.lbl_current_file.setText("✗  All encodes failed. Check logs for details.")
            self.lbl_current_file.setStyleSheet(f"color: {_RED}; font-size: 11px; font-weight: 600;")
        else:
            self.lbl_current_file.setText(
                f"⚠  Completed with errors — {completed} ok, {failed} failed."
            )
            self.lbl_current_file.setStyleSheet(f"color: {_YELLOW}; font-size: 11px; font-weight: 600;")

        self.file_progress_bar.setValue(100 if failed == 0 else self.file_progress_bar.value())
