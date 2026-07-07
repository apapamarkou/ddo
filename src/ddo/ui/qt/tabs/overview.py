"""Overview tab — system summary."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QGroupBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ddo.backend.detection import DetectionEngine
from ddo.backend.packages import PackageManager
from ddo.ui.qt.worker import BackendWorker


class OverviewTab(QWidget):
    def __init__(
        self,
        pkg: PackageManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._pkg = pkg
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        info_box = QGroupBox("System Information")
        info_layout = QVBoxLayout()
        self._sys_label = QLabel("Scanning…")
        self._sys_label.setWordWrap(True)
        info_layout.addWidget(self._sys_label)
        info_box.setLayout(info_layout)
        layout.addWidget(info_box)
        layout.addStretch()

    def _refresh(self) -> None:
        self._worker = BackendWorker(self._do_scan)
        self._worker.finished.connect(self._on_scan_done)
        self._worker.error.connect(lambda e: self._sys_label.setText(f"Error: {e}"))
        self._worker.start()

    def _do_scan(self) -> object:
        return DetectionEngine(self._pkg).detect()

    def _on_scan_done(self, result: object) -> None:
        from ddo.backend.detection import SystemProfile

        assert isinstance(result, SystemProfile)
        p = result
        self._sys_label.setText(
            f"<b>Desktop:</b> {p.desktop_environment.upper()}<br>"
            f"<b>Debian:</b> {p.debian_version}<br>"
            f"<b>Architecture:</b> {p.architecture}<br>"
            f"<b>Locale:</b> {p.current_locale}<br>"
            f"<b>Installed packages:</b> {len(p.installed_package_names)}"
        )
