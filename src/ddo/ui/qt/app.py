"""PyQt6 GUI entry point for Debian Desktop Optimizer."""

from __future__ import annotations

import sys

from PyQt6.QtCore import QSharedMemory
from PyQt6.QtWidgets import QApplication, QMessageBox

from ddo.models.config import AppConfig
from ddo.ui.qt.mainwindow import MainWindow
from ddo.ui.qt.wizard import FirstRunWizard
from ddo.utils.logging_setup import setup_logging


def main() -> None:
    config = AppConfig.load()
    setup_logging(debug=config.debug)

    app = QApplication(sys.argv)
    app.setApplicationName("Debian Desktop Optimizer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("DDO")

    _lock = QSharedMemory("ddo-single-instance")
    if not _lock.create(1):
        # Segment exists — could be a live instance or a stale crash remnant.
        # Try to attach: if it succeeds, detach immediately (cleans up on Unix)
        # then retry create. If create still fails, a real instance is running.
        _stale = QSharedMemory("ddo-single-instance")
        if _stale.attach():
            _stale.detach()
        if not _lock.create(1):
            QMessageBox.warning(
                None, "Already Running", "Debian Desktop Optimizer is already running."
            )
            sys.exit(0)

    if AppConfig.is_first_run():
        wizard = FirstRunWizard(config)
        if wizard.exec():
            config = wizard.config
            config.save()
            AppConfig.mark_initialized()
        else:
            sys.exit(0)

    window = MainWindow(config)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
