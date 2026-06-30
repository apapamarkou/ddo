"""Updates tab."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ddo.backend.apt import AptManager
from ddo.ui.qt.worker import BackendWorker


class UpdatesTab(QWidget):
    def __init__(self, apt: AptManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._apt = apt
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Keep your system up-to-date."))

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        layout.addWidget(self._log)

        btn_layout = QHBoxLayout()
        update_btn = QPushButton("Update & Upgrade")
        update_btn.clicked.connect(self._run_update)
        autoremove_btn = QPushButton("Autoremove")
        autoremove_btn.clicked.connect(self._run_autoremove)
        btn_layout.addStretch()
        btn_layout.addWidget(autoremove_btn)
        btn_layout.addWidget(update_btn)
        layout.addLayout(btn_layout)

    def _run_update(self) -> None:
        self._start("Updating…", self._do_update)

    def _run_autoremove(self) -> None:
        self._start("Autoremove…", self._do_autoremove)

    def _start(self, label: str, fn: object) -> None:
        self._progress.setRange(0, 0)
        self._progress.setVisible(True)
        self._log.clear()
        self._worker = BackendWorker(fn)  # type: ignore[arg-type]
        self._worker.progress.connect(lambda m: self._log.append(m))
        self._worker.finished.connect(
            lambda _: (
                self._progress.setRange(0, 1),
                self._progress.setValue(1),
                self._log.append("✓ Done."),
            )
        )
        self._worker.error.connect(lambda e: self._log.append(f"⚠ {e}"))
        self._worker.start()

    def _do_update(self) -> None:
        self._worker.progress.emit("apt update…")
        self._apt.update()
        self._worker.progress.emit("apt upgrade…")
        self._apt.upgrade()

    def _do_autoremove(self) -> None:
        self._worker.progress.emit("apt autoremove…")
        self._apt.autoremove()
        self._worker.progress.emit("apt autoclean…")
        self._apt.autoclean()
