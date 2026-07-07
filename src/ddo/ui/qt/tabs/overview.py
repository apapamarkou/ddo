"""Overview tab — system summary."""

from __future__ import annotations

import shutil

from PyQt6.QtWidgets import (
    QGroupBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ddo.backend.apt import AptManager
from ddo.backend.cleanup import CleanupEngine
from ddo.backend.detection import DetectionEngine
from ddo.backend.languages import LanguageManager
from ddo.backend.packages import PackageManager
from ddo.models.config import AppConfig
from ddo.ui.qt.worker import BackendWorker
from ddo.utils.formatting import format_bytes


class OverviewTab(QWidget):
    def __init__(
        self,
        apt: AptManager,
        pkg: PackageManager,
        config: AppConfig,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._apt = apt
        self._pkg = pkg
        self._config = config
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        sys_box = QGroupBox("System Information")
        sys_layout = QVBoxLayout()
        self._sys_label = QLabel("Scanning…")
        self._sys_label.setWordWrap(True)
        sys_layout.addWidget(self._sys_label)
        sys_box.setLayout(sys_layout)
        layout.addWidget(sys_box)

        disk_box = QGroupBox("Disk Usage")
        disk_layout = QVBoxLayout()
        self._disk_label = QLabel("Scanning…")
        disk_layout.addWidget(self._disk_label)
        disk_box.setLayout(disk_layout)
        layout.addWidget(disk_box)

        cleanup_box = QGroupBox("Cleanup Potential")
        cleanup_layout = QVBoxLayout()
        self._cleanup_label = QLabel("Scanning…")
        cleanup_layout.addWidget(self._cleanup_label)
        cleanup_box.setLayout(cleanup_layout)
        layout.addWidget(cleanup_box)

        layout.addStretch()

    def _refresh(self) -> None:
        self._worker = BackendWorker(self._do_scan)
        self._worker.finished.connect(self._on_scan_done)
        self._worker.error.connect(lambda e: self._sys_label.setText(f"Error: {e}"))
        self._worker.start()

    def _do_scan(self) -> object:
        from pathlib import Path

        profile = DetectionEngine(self._pkg).detect()
        disk = shutil.disk_usage("/")

        db_path = Path(self._config.languages_db_path) if self._config.languages_db_path else None
        lang = LanguageManager(self._pkg, db_path=db_path)
        detected = lang.detect_installed()
        lang_pkgs_by_code = {i.code: i.installed_packages for i in detected}
        engine = CleanupEngine(self._apt, self._pkg)
        categories = engine.build_categories(self._config.kept_languages, lang_pkgs_by_code)
        removable = sum(len(c.packages_to_remove) for c in categories)

        return profile, disk, removable

    def _on_scan_done(self, result: object) -> None:
        from ddo.backend.detection import SystemProfile

        profile, disk, removable = result  # type: ignore[misc]
        assert isinstance(profile, SystemProfile)

        self._sys_label.setText(
            f"<b>Desktop:</b> {profile.desktop_environment.upper()}&nbsp;&nbsp;"
            f"<b>Debian:</b> {profile.debian_version}&nbsp;&nbsp;"
            f"<b>Arch:</b> {profile.architecture}&nbsp;&nbsp;"
            f"<b>Locale:</b> {profile.current_locale}&nbsp;&nbsp;"
            f"<b>Packages:</b> {len(profile.installed_package_names)}"
        )
        self._disk_label.setText(
            f"<b>Total:</b> {format_bytes(disk.total)}&nbsp;&nbsp;"
            f"<b>Used:</b> {format_bytes(disk.used)}&nbsp;&nbsp;"
            f"<b>Free:</b> {format_bytes(disk.free)}"
        )
        self._cleanup_label.setText(f"<b>Removable packages:</b> {removable}")
