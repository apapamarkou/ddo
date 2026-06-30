"""Logs viewer tab."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ddo.utils.logging_setup import get_log_path


class LogsTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self._path_label = QLabel(f"Log file: {get_log_path()}")
        layout.addWidget(self._path_label)

        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        font = self._text.font()
        font.setFamily("monospace")
        self._text.setFont(font)
        layout.addWidget(self._text)

        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load)
        clear_btn = QPushButton("Clear View")
        clear_btn.clicked.connect(self._text.clear)
        btn_layout.addStretch()
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(refresh_btn)
        layout.addLayout(btn_layout)

    def _load(self) -> None:
        path = get_log_path()
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                # Show last 500 lines to keep the view manageable
                lines = content.splitlines()[-500:]
                self._text.setPlainText("\n".join(lines))
                # Scroll to bottom
                sb = self._text.verticalScrollBar()
                sb.setValue(sb.maximum())
            except OSError as exc:
                self._text.setPlainText(f"Cannot read log: {exc}")
        else:
            self._text.setPlainText("No log file found yet.")
