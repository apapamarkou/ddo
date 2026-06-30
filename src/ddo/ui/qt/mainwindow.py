"""Main application window with tab-based control panel."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QWidget,
)

from ddo.backend.apt import AptManager
from ddo.backend.languages import LanguageManager
from ddo.backend.packages import PackageManager
from ddo.models.config import AppConfig
from ddo.ui.qt.tabs.about import AboutTab
from ddo.ui.qt.tabs.components import ComponentsTab
from ddo.ui.qt.tabs.languages import LanguagesTab
from ddo.ui.qt.tabs.logs import LogsTab
from ddo.ui.qt.tabs.overview import OverviewTab
from ddo.ui.qt.tabs.updates import UpdatesTab


class MainWindow(QMainWindow):
    """Main window shown after the first-run wizard completes."""

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Debian Desktop Optimizer")
        self.setMinimumSize(900, 600)

        self._apt = AptManager()
        self._pkg = PackageManager(self._apt)
        db_path = Path(config.languages_db_path) if config.languages_db_path else None
        self._lang = LanguageManager(self._pkg, db_path=db_path)

        self._build_ui()
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

    def _build_ui(self) -> None:
        self._tabs = QTabWidget()

        self._overview_tab = OverviewTab(self._apt, self._pkg, self._lang, self.config, self)
        self._lang_tab = LanguagesTab(self._lang, self.config, self)
        self._components_tab = ComponentsTab(self._apt, self._pkg, self.config, self)
        self._updates_tab = UpdatesTab(self._apt, self)
        self._logs_tab = LogsTab(self)
        self._about_tab = AboutTab(self)

        self._tabs.addTab(self._overview_tab, "Overview")
        self._tabs.addTab(self._lang_tab, "Languages")
        self._tabs.addTab(self._components_tab, "Components")
        self._tabs.addTab(self._updates_tab, "Updates")
        self._tabs.addTab(self._logs_tab, "Logs")
        self._tabs.addTab(self._about_tab, "About")

        self.setCentralWidget(self._tabs)

    def show_status(self, msg: str) -> None:
        self._status_bar.showMessage(msg, 5000)
