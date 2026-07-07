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
        self.refresh()

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
        refresh_btn.clicked.connect(self.refresh)
        btn_layout.addStretch()
        btn_layout.addWidget(refresh_btn)
        layout.addLayout(btn_layout)

    def refresh(self) -> None:
        path = get_log_path()
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                lines = content.splitlines()[-500:]
                self._text.setPlainText("\n".join(lines))
                sb = self._text.verticalScrollBar()
                sb.setValue(sb.maximum())
            except OSError as exc:
                self._text.setPlainText(f"Cannot read log: {exc}")
        else:
            self._text.setPlainText("No log file found yet.")
