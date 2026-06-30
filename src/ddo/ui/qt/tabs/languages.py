"""Languages management tab."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ddo.backend.languages import LanguageInfo, LanguageManager
from ddo.models.config import AppConfig
from ddo.utils.formatting import format_bytes


class LanguagesTab(QWidget):
    def __init__(
        self,
        lang_manager: LanguageManager,
        config: AppConfig,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._lang = lang_manager
        self._config = config
        self._build_ui()
        self._populate()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        hint = QLabel(
            "Languages marked [KEEP] will have their packages preserved. "
            "Uncheck a language to mark it for removal."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: language list
        self._list = QListWidget()
        self._list.itemSelectionChanged.connect(self._on_select)
        splitter.addWidget(self._list)

        # Right: detail panel
        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        self._detail_label = QLabel("Select a language to see details.")
        self._detail_label.setWordWrap(True)
        detail_layout.addWidget(self._detail_label)
        self._pkg_list = QListWidget()
        detail_layout.addWidget(self._pkg_list)
        splitter.addWidget(detail)
        splitter.setSizes([300, 400])
        layout.addWidget(splitter)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save Language Selection")
        save_btn.clicked.connect(self._save)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _populate(self) -> None:
        self._list.clear()
        for info in self._lang.detect_installed():
            item = QListWidgetItem(
                f"{'[KEEP] ' if info.code in self._config.kept_languages else ''}  "
                f"{info.name} ({info.code})  —  "
                f"{format_bytes(info.total_size_kb * 1024)}"
            )
            item.setData(Qt.ItemDataRole.UserRole, info)
            item.setCheckState(
                Qt.CheckState.Checked
                if info.code in self._config.kept_languages
                else Qt.CheckState.Unchecked
            )
            self._list.addItem(item)

    def _on_select(self) -> None:
        items = self._list.selectedItems()
        if not items:
            return
        info: LanguageInfo = items[0].data(Qt.ItemDataRole.UserRole)
        self._detail_label.setText(
            f"<b>{info.name}</b> ({info.code})<br>"
            f"Installed packages: {len(info.installed_packages)}<br>"
            f"Total size: {format_bytes(info.total_size_kb * 1024)}"
        )
        self._pkg_list.clear()
        for pkg in sorted(info.installed_packages):
            self._pkg_list.addItem(pkg)

    def _save(self) -> None:
        kept: list[str] = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                info: LanguageInfo = item.data(Qt.ItemDataRole.UserRole)
                kept.append(info.code)
        self._config.kept_languages = kept or ["en"]
        self._config.save()
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.information(self, "Saved", "Language selection saved.")
