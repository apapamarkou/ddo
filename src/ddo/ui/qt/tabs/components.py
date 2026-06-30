"""Components tab — manage individual cleanup categories."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ddo.backend.apt import AptManager
from ddo.backend.cleanup import CleanupCategory, CleanupEngine
from ddo.backend.languages import LanguageManager
from ddo.backend.packages import PackageManager
from ddo.models.config import AppConfig
from ddo.ui.qt.worker import BackendWorker
from ddo.utils.formatting import format_bytes


class ComponentsTab(QWidget):
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
        self._categories: list[CleanupCategory] = []
        self._build_ui()
        self._load_categories()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        hint = QLabel("Check categories you want to remove, then click 'Apply Selected'.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._cat_list = QListWidget()
        self._cat_list.itemSelectionChanged.connect(self._on_select)
        splitter.addWidget(self._cat_list)

        detail = QWidget()
        dl = QVBoxLayout(detail)
        self._detail = QLabel("Select a category.")
        self._detail.setWordWrap(True)
        dl.addWidget(self._detail)
        self._pkg_list = QListWidget()
        dl.addWidget(self._pkg_list)
        splitter.addWidget(detail)
        splitter.setSizes([300, 400])
        layout.addWidget(splitter)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(120)
        layout.addWidget(self._log)

        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("Apply Selected")
        apply_btn.clicked.connect(self._apply)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load_categories)
        btn_layout.addStretch()
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(apply_btn)
        layout.addLayout(btn_layout)

    def _load_categories(self) -> None:
        self._cat_list.clear()
        self._worker = BackendWorker(self._do_load)
        self._worker.finished.connect(self._on_loaded)
        self._worker.error.connect(lambda e: self._log.append(f"Error: {e}"))
        self._worker.start()

    def _do_load(self) -> object:
        from pathlib import Path

        db_path = Path(self._config.languages_db_path) if self._config.languages_db_path else None
        lang = LanguageManager(self._pkg, db_path=db_path)
        detected = lang.detect_installed()
        lang_pkgs_by_code = {i.code: i.installed_packages for i in detected}
        engine = CleanupEngine(self._apt, self._pkg)
        return engine.build_categories(self._config.kept_languages, lang_pkgs_by_code)

    def _on_loaded(self, result: object) -> None:
        assert isinstance(result, list)
        self._categories = result  # type: ignore[assignment]
        self._cat_list.clear()
        for cat in self._categories:
            item = QListWidgetItem(
                f"{cat.label}  ({len(cat.packages_to_remove)} pkgs, "
                f"{format_bytes(cat.total_size_kb * 1024)})"
            )
            item.setData(Qt.ItemDataRole.UserRole, cat)
            item.setCheckState(Qt.CheckState.Checked if cat.enabled else Qt.CheckState.Unchecked)
            self._cat_list.addItem(item)

    def _on_select(self) -> None:
        items = self._cat_list.selectedItems()
        if not items:
            return
        cat: CleanupCategory = items[0].data(Qt.ItemDataRole.UserRole)
        self._detail.setText(f"<b>{cat.label}</b><br>{cat.description}")
        self._pkg_list.clear()
        for p in sorted(cat.packages_to_remove):
            self._pkg_list.addItem(p)

    def _apply(self) -> None:
        from PyQt6.QtWidgets import QMessageBox

        # Update enabled state from checkboxes
        for i in range(self._cat_list.count()):
            item = self._cat_list.item(i)
            if item:
                cat: CleanupCategory = item.data(Qt.ItemDataRole.UserRole)
                cat.enabled = item.checkState() == Qt.CheckState.Checked

        enabled_cats = [c for c in self._categories if c.enabled]
        pkgs = [p for c in enabled_cats for p in c.packages_to_remove]
        if not pkgs:
            QMessageBox.information(self, "Nothing selected", "No packages to remove.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm",
            f"Remove {len(pkgs)} packages from {len(enabled_cats)} categories?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._progress.setRange(0, 0)
        self._progress.setVisible(True)
        self._log.clear()

        self._worker2 = BackendWorker(self._do_apply, enabled_cats)
        self._worker2.progress.connect(lambda m: self._log.append(m))
        self._worker2.finished.connect(
            lambda _: (
                self._progress.setRange(0, 1),
                self._progress.setValue(1),
                self._log.append("✓ Done!"),
                self._load_categories(),
            )
        )
        self._worker2.error.connect(lambda e: self._log.append(f"⚠ {e}"))
        self._worker2.start()

    def _do_apply(self, categories: list[CleanupCategory]) -> None:
        from ddo.backend.cleanup import CleanupPlan
        from ddo.backend.restore import RestoreEngine

        pkgs = [p for c in categories for p in c.packages_to_remove]
        RestoreEngine(self._apt).save_rollback(pkgs, "Components tab removal")

        engine = CleanupEngine(
            self._apt, self._pkg, progress_callback=lambda m: self._worker2.progress.emit(m)
        )
        plan = CleanupPlan(categories=categories)
        engine.execute(plan)
