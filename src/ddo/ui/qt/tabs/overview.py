"""Overview tab — system summary and quick actions."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ddo.backend.apt import AptManager
from ddo.backend.cleanup import CleanupEngine, CleanupPlan
from ddo.backend.detection import DetectionEngine
from ddo.backend.languages import LanguageManager
from ddo.backend.packages import PackageManager
from ddo.models.config import AppConfig
from ddo.ui.qt.worker import BackendWorker
from ddo.utils.formatting import format_bytes, format_package_count


class OverviewTab(QWidget):
    def __init__(
        self,
        apt: AptManager,
        pkg: PackageManager,
        lang: LanguageManager,
        config: AppConfig,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._apt = apt
        self._pkg = pkg
        self._lang = lang
        self._config = config
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # System info group
        info_box = QGroupBox("System Information")
        info_layout = QVBoxLayout()
        self._sys_label = QLabel("Scanning…")
        self._sys_label.setWordWrap(True)
        info_layout.addWidget(self._sys_label)
        info_box.setLayout(info_layout)
        layout.addWidget(info_box)

        # Quick actions
        action_box = QGroupBox("Quick Actions")
        action_layout = QHBoxLayout()
        self._analyze_btn = QPushButton("Analyse System")
        self._analyze_btn.clicked.connect(self._run_analysis)
        self._cleanup_btn = QPushButton("Run Cleanup")
        self._cleanup_btn.clicked.connect(self._run_cleanup)
        self._update_btn = QPushButton("Update System")
        self._update_btn.clicked.connect(self._run_update)
        action_layout.addWidget(self._analyze_btn)
        action_layout.addWidget(self._cleanup_btn)
        action_layout.addWidget(self._update_btn)
        action_box.setLayout(action_layout)
        layout.addWidget(action_box)

        # Progress & log
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        layout.addWidget(self._log)

    def _refresh(self) -> None:
        self._worker = BackendWorker(self._do_scan)
        self._worker.finished.connect(self._on_scan_done)
        self._worker.error.connect(lambda e: self._sys_label.setText(f"Error: {e}"))
        self._worker.start()

    def _do_scan(self) -> object:
        detector = DetectionEngine(self._pkg)
        return detector.detect()

    def _on_scan_done(self, result: object) -> None:
        from ddo.backend.detection import SystemProfile

        assert isinstance(result, SystemProfile)
        p = result
        self._sys_label.setText(
            f"Desktop: {p.desktop_environment.upper()}   |   "
            f"Debian: {p.debian_version}   |   "
            f"Arch: {p.architecture}   |   "
            f"Locale: {p.current_locale}   |   "
            f"Packages: {len(p.installed_package_names)}"
        )

    def _run_analysis(self) -> None:
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        self._log.clear()
        self._worker = BackendWorker(self._do_analysis)
        self._worker.progress.connect(lambda m: self._log.append(m))
        self._worker.finished.connect(self._on_analysis_done)
        self._worker.error.connect(lambda e: self._log.append(f"Error: {e}"))
        self._worker.start()

    def _do_analysis(self) -> object:
        detected = self._lang.detect_installed()
        lang_pkgs_by_code = {i.code: i.installed_packages for i in detected}
        lang_to_remove = [
            p
            for i in detected
            if i.code not in self._config.kept_languages
            for p in i.installed_packages
        ]
        engine = CleanupEngine(
            self._apt, self._pkg, progress_callback=lambda m: self._worker.progress.emit(m)
        )
        categories = engine.build_categories(self._config.kept_languages, lang_pkgs_by_code)
        return engine.analyze(categories, lang_to_remove, dry_run=True)

    def _on_analysis_done(self, result: object) -> None:
        assert isinstance(result, CleanupPlan)
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._log.append(
            f"\n✓ Analysis complete.\n"
            f"  Removable packages: {format_package_count(result.total_packages)}\n"
            f"  Estimated space freed: {format_bytes(result.total_size_bytes)}"
        )

    def _run_cleanup(self) -> None:
        from PyQt6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "Confirm Cleanup",
            "This will remove selected packages. A rollback snapshot will be saved.\n\nProceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._progress.setRange(0, 0)
        self._progress.setVisible(True)
        self._log.clear()

        self._worker = BackendWorker(self._do_cleanup)
        self._worker.progress.connect(lambda m: self._log.append(m))
        self._worker.finished.connect(
            lambda _: (
                self._progress.setRange(0, 1),
                self._progress.setValue(1),
                self._log.append("\n✓ Done!"),
            )
        )
        self._worker.error.connect(lambda e: self._log.append(f"⚠ Error: {e}"))
        self._worker.start()

    def _do_cleanup(self) -> None:
        from ddo.backend.restore import RestoreEngine

        detected = self._lang.detect_installed()
        lang_pkgs_by_code = {i.code: i.installed_packages for i in detected}
        lang_to_remove = [
            p
            for i in detected
            if i.code not in self._config.kept_languages
            for p in i.installed_packages
        ]
        engine = CleanupEngine(
            self._apt, self._pkg, progress_callback=lambda m: self._worker.progress.emit(m)
        )
        categories = engine.build_categories(self._config.kept_languages, lang_pkgs_by_code)
        plan = engine.analyze(categories, lang_to_remove, dry_run=False)

        all_pkgs = list(lang_to_remove) + [p for c in categories for p in c.packages_to_remove]
        RestoreEngine(self._apt).save_rollback(all_pkgs, "Manual cleanup")
        engine.execute(plan)

    def _run_update(self) -> None:
        self._progress.setRange(0, 0)
        self._progress.setVisible(True)
        self._log.clear()
        self._worker = BackendWorker(self._do_update)
        self._worker.progress.connect(lambda m: self._log.append(m))
        self._worker.finished.connect(
            lambda _: (
                self._progress.setRange(0, 1),
                self._progress.setValue(1),
                self._log.append("✓ System updated."),
            )
        )
        self._worker.error.connect(lambda e: self._log.append(f"⚠ {e}"))
        self._worker.start()

    def _do_update(self) -> None:
        self._worker.progress.emit("Updating package database…")
        self._apt.update()
        self._worker.progress.emit("Upgrading packages…")
        self._apt.upgrade()
        self._worker.progress.emit("Autoremove…")
        self._apt.autoremove()
