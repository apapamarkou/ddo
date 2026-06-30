"""About tab."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ddo import __version__


class AboutTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(f"<h2>Debian Desktop Optimizer</h2><p>Version {__version__}</p>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        desc = QLabel(
            "<p>Remove unnecessary language packs, fonts, input methods,<br>"
            "and optional components from fresh Debian installations.</p>"
            "<p>License: <b>GPL-3.0-only</b></p>"
            "<p><a href='https://github.com/debian-desktop-optimizer/ddo'>"
            "github.com/debian-desktop-optimizer/ddo</a></p>"
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setOpenExternalLinks(True)
        layout.addWidget(desc)
