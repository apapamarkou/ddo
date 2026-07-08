"""First-run wizard dialog."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

from ddo.backend.apt import AptManager
from ddo.backend.cleanup import CleanupEngine
from ddo.backend.languages import LanguageManager
from ddo.backend.packages import PackageManager
from ddo.models.config import AppConfig
from ddo.ui.qt.worker import BackendWorker
from ddo.utils.formatting import format_bytes, format_package_count


class FirstRunWizard(QWizard):
    """Multi-step first-run configuration wizard."""

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Debian Desktop Optimizer — First Run")
        self.setMinimumSize(700, 500)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        _candidates = [
            Path("/usr/share/ddo/icons/ddo-wizard-image.png"),
            Path(__file__).parent.parent.parent.parent.parent / "data/icons/ddo-wizard-image.png",
        ]
        self._watermark_source: QPixmap | None = None
        for _p in _candidates:
            if _p.exists():
                self._watermark_source = QPixmap(str(_p))
                break
        if self._watermark_source is not None:
            scaled = self._watermark_source.scaledToHeight(
                self.minimumHeight(), Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(QWizard.WizardPixmap.WatermarkPixmap, scaled)

        self._apt = AptManager()
        self._pkg = PackageManager(self._apt)
        db_path = Path(config.languages_db_path) if config.languages_db_path else None
        self._lang = LanguageManager(self._pkg, db_path=db_path)

        self.addPage(WelcomePage(self))
        self._lang_page = LanguageSelectionPage(self._lang, config, self)
        self.addPage(self._lang_page)
        self._options_page = CleanupOptionsPage(self)
        self.addPage(self._options_page)
        self._analysis_page = AnalysisPage(self._apt, self._pkg, self._lang, config, self)
        self.addPage(self._analysis_page)
        self._execute_page = ExecutePage(self._apt, self._pkg, self._lang, config, self)
        self.addPage(self._execute_page)

    def accept(self) -> None:
        self.config.kept_languages = self._lang_page.selected_languages()
        super().accept()


# ---------------------------------------------------------------------------
# Page 1 — Welcome
# ---------------------------------------------------------------------------


class WelcomePage(QWizardPage):
    def __init__(self, parent: QWizard) -> None:
        super().__init__(parent)
        self.setTitle("Welcome to Debian Desktop Optimizer")
        self.setSubTitle(
            "This wizard will help you remove unnecessary packages "
            "from your Debian desktop installation."
        )
        layout = QVBoxLayout()
        intro = QLabel(
            "The wizard will guide you through:\n\n"
            "  1. Selecting languages to keep\n"
            "  2. Choosing optional cleanup categories\n"
            "  3. Analysing your system\n"
            "  4. Executing the cleanup\n\n"
            "A rollback snapshot will be saved before any changes are made."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addStretch()
        self.setLayout(layout)


# ---------------------------------------------------------------------------
# Page 2 — Language Selection
# ---------------------------------------------------------------------------


class LanguageSelectionPage(QWizardPage):
    def __init__(
        self,
        lang_manager: LanguageManager,
        config: AppConfig,
        parent: QWizard,
    ) -> None:
        super().__init__(parent)
        self._lang_manager = lang_manager
        self._config = config
        self.setTitle("Language Selection")
        self.setSubTitle("Select the languages you want to KEEP on your system.")

        layout = QVBoxLayout()
        hint = QLabel(
            "All other language packages (translations, spellcheckers, fonts) "
            "will be candidates for removal."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(self._list)
        self.setLayout(layout)

    def initializePage(self) -> None:  # noqa: N802
        self._list.clear()
        current_code = self._lang_manager.current_language_code()
        for code, name in self._lang_manager.all_language_codes():
            item = QListWidgetItem(f"{name}  ({code})")
            item.setData(Qt.ItemDataRole.UserRole, code)
            self._list.addItem(item)
            if code in self._config.kept_languages or code == current_code or code == "en":
                item.setSelected(True)

    def selected_languages(self) -> list[str]:
        codes: list[str] = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item and item.isSelected():
                codes.append(item.data(Qt.ItemDataRole.UserRole))
        return codes or ["en"]


# ---------------------------------------------------------------------------
# Page 3 — Cleanup Options
# ---------------------------------------------------------------------------


class CleanupOptionsPage(QWizardPage):
    # (key, label, checked_by_default)
    _OPTION_LABELS: tuple[tuple[str, str, bool], ...] = (
        ("input_methods", "Remove Asian input methods", True),
        ("spellcheckers", "Remove unused spellcheckers", True),
        ("games", "Remove games", False),
        ("ocr_data", "Remove OCR data", False),
        ("speech", "Remove speech synthesis", False),
        ("accessibility", "Remove accessibility tools (screen readers)", False),
        ("printing", "Remove printing support", False),
        ("bluetooth", "Remove Bluetooth", False),
        ("modem", "Remove modem/mobile broadband support", False),
        ("server_packages", "Remove server packages", False),
        ("unused_docs", "Remove unused documentation", False),
        ("bloatware", "Remove bloatware (xterm, shotwell, mlterm)", False),
    )

    def __init__(self, parent: QWizard) -> None:
        super().__init__(parent)
        self.setTitle("Cleanup Options")
        self.setSubTitle("Choose what additional categories to remove.")

        layout = QVBoxLayout()
        self._checkboxes: dict[str, QCheckBox] = {}
        for key, label, default in self._OPTION_LABELS:
            cb = QCheckBox(label)
            cb.setChecked(default)
            self._checkboxes[key] = cb
            layout.addWidget(cb)

        layout.addStretch()

        self._view_details = QCheckBox("View details (show package list and apt output)")
        self._view_details.setChecked(False)
        layout.addWidget(self._view_details)

        self.setLayout(layout)

    def selected_categories(self) -> list[str]:
        return [k for k, cb in self._checkboxes.items() if cb.isChecked()]

    def view_details(self) -> bool:
        return self._view_details.isChecked()


# ---------------------------------------------------------------------------
# Page 4 — Analysis
# ---------------------------------------------------------------------------


class AnalysisPage(QWizardPage):
    def __init__(
        self,
        apt: AptManager,
        pkg: PackageManager,
        lang: LanguageManager,
        config: AppConfig,
        parent: QWizard,
    ) -> None:
        super().__init__(parent)
        self._apt = apt
        self._pkg = pkg
        self._lang = lang
        self._config = config
        self.setTitle("System Analysis")
        self.setSubTitle("Analysing your system. Please wait…")

        layout = QVBoxLayout()
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminate
        layout.addWidget(self._progress)
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        layout.addWidget(self._log)
        self.setLayout(layout)
        self._complete = False

    def initializePage(self) -> None:  # noqa: N802
        wizard = self.wizard()
        assert isinstance(wizard, FirstRunWizard)
        kept = wizard._lang_page.selected_languages()
        self._config.kept_languages = kept

        self._worker = BackendWorker(self._run_analysis)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _run_analysis(self) -> object:
        wizard = self.wizard()
        assert isinstance(wizard, FirstRunWizard)
        selected_keys = set(wizard._options_page.selected_categories())

        detected = self._lang.detect_installed()
        lang_pkgs_by_code = {i.code: i.installed_packages for i in detected}
        lang_to_remove: list[str] = []
        for info in detected:
            if info.code not in self._config.kept_languages:
                lang_to_remove.extend(info.installed_packages)

        engine = CleanupEngine(
            self._apt, self._pkg, progress_callback=lambda m: self._worker.progress.emit(m)
        )
        categories = engine.build_categories(self._config.kept_languages, lang_pkgs_by_code)
        for cat in categories:
            cat.enabled = cat.key in selected_keys
        plan = engine.analyze(categories, lang_to_remove, dry_run=True)
        return plan

    def _on_progress(self, msg: str) -> None:
        self._log.append(msg)

    def _on_done(self, result: object) -> None:
        from ddo.backend.cleanup import CleanupPlan

        assert isinstance(result, CleanupPlan)
        wizard = self.wizard()
        assert isinstance(wizard, FirstRunWizard)

        if wizard._options_page.view_details():
            for cat in result.categories:
                if cat.enabled and cat.packages_to_remove:
                    self._log.append(f"\n[{cat.label}]")
                    self._log.append("  " + ", ".join(cat.packages_to_remove))
            if result.language_packages_to_remove:
                self._log.append("\n[Language packages]")
                self._log.append("  " + ", ".join(result.language_packages_to_remove))

        self._log.append(
            f"\n✓ Analysis complete.\n"
            f"  Packages to remove: {format_package_count(result.total_packages)}\n"
            f"  Space freed: {format_bytes(result.total_size_bytes)}"
        )
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._complete = True
        self.completeChanged.emit()

    def _on_error(self, exc: Exception) -> None:
        self._log.append(f"⚠ Error: {exc}")
        self._progress.setRange(0, 1)
        self._progress.setValue(0)

    def isComplete(self) -> bool:  # noqa: N802
        return self._complete


# ---------------------------------------------------------------------------
# Page 5 — Execute
# ---------------------------------------------------------------------------


class ExecutePage(QWizardPage):
    def __init__(
        self,
        apt: AptManager,
        pkg: PackageManager,
        lang: LanguageManager,
        config: AppConfig,
        parent: QWizard,
    ) -> None:
        super().__init__(parent)
        self._apt = apt
        self._pkg = pkg
        self._lang = lang
        self._config = config
        self.setTitle("Cleanup")
        self.setSubTitle("Removing selected packages…")

        layout = QVBoxLayout()
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        layout.addWidget(self._progress)
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        layout.addWidget(self._log)
        self.setLayout(layout)
        self._complete = False
        self._view_details = False

    def initializePage(self) -> None:  # noqa: N802
        wizard = self.wizard()
        assert isinstance(wizard, FirstRunWizard)
        self._view_details = wizard._options_page.view_details()
        self._worker = BackendWorker(self._run_cleanup)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _run_cleanup(self) -> None:
        wizard = self.wizard()
        assert isinstance(wizard, FirstRunWizard)
        selected_keys = set(wizard._options_page.selected_categories())

        detected = self._lang.detect_installed()
        lang_pkgs_by_code = {i.code: i.installed_packages for i in detected}
        lang_to_remove: list[str] = []
        for info in detected:
            if info.code not in self._config.kept_languages:
                lang_to_remove.extend(info.installed_packages)

        from ddo.backend.restore import RestoreEngine

        restore = RestoreEngine(self._apt)

        engine = CleanupEngine(
            self._apt, self._pkg, progress_callback=lambda m: self._worker.progress.emit(m)
        )
        categories = engine.build_categories(self._config.kept_languages, lang_pkgs_by_code)
        for cat in categories:
            cat.enabled = cat.key in selected_keys

        all_pkgs = list(lang_to_remove)
        for cat in categories:
            if cat.enabled:
                all_pkgs.extend(cat.packages_to_remove)
        restore.save_rollback(all_pkgs, "First-run wizard cleanup")

        plan = engine.analyze(categories, lang_to_remove, dry_run=False)
        engine.execute(plan)

        if self._config.auto_update:
            self._worker.progress.emit("Updating package database…")
            self._apt.update()
            self._worker.progress.emit("Upgrading…")
            self._apt.upgrade()

    def _on_progress(self, msg: str) -> None:
        # Always show high-level messages; only show raw apt output if view_details
        if self._view_details or not msg.startswith("apt-get"):
            self._log.append(msg)

    def _on_done(self, _: object) -> None:
        self._log.append("\n✓ Cleanup complete!")
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._complete = True
        self.completeChanged.emit()

    def _on_error(self, exc: Exception) -> None:
        self._log.append(f"⚠ Error: {exc}")
        self._progress.setRange(0, 1)
        self._progress.setValue(0)

    def isComplete(self) -> bool:  # noqa: N802
        return self._complete
