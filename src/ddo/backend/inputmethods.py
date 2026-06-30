"""Input method detection and management."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import cast

from ddo.backend.packages import PackageManager

logger = logging.getLogger(__name__)

_INPUT_METHOD_GROUPS: dict[str, dict[str, object]] = {
    "fcitx4": {
        "label": "Fcitx 4 (legacy input method)",
        "patterns": ["fcitx", "fcitx-*", "libfcitx-*"],
    },
    "fcitx5": {
        "label": "Fcitx 5 (modern input method)",
        "patterns": ["fcitx5", "fcitx5-*", "libfcitx5*"],
    },
    "ibus": {
        "label": "IBus (input method bus)",
        "patterns": ["ibus", "ibus-*"],
    },
    "mozc": {
        "label": "Mozc (Japanese input)",
        "patterns": ["mozc-*", "ibus-mozc", "uim-mozc"],
    },
    "anthy": {
        "label": "Anthy (Japanese input)",
        "patterns": [
            "anthy",
            "anthy-common",
            "libanthydata",
            "libanthy1*",
            "libanthyinput0*",
            "kasumi",
        ],
    },
    "uim": {
        "label": "UIM (Universal Input Method)",
        "patterns": ["uim", "uim-*", "libuim*"],
    },
    "m17n": {
        "label": "M17N multilingual input",
        "patterns": ["m17n-db", "libm17n-*"],
    },
    "hangul": {
        "label": "Hangul (Korean input)",
        "patterns": ["ibus-hangul", "libhangul*"],
    },
    "thai_im": {
        "label": "Thai input method",
        "patterns": ["gtk-im-libthai", "gtk3-im-libthai"],
    },
}


@dataclass
class InputMethodGroup:
    """A group of input-method related packages."""

    key: str
    label: str
    packages: list[str] = field(default_factory=list)
    total_size_kb: int = 0


class InputMethodManager:
    """Detect installed input method packages."""

    def __init__(self, pkg_manager: PackageManager) -> None:
        self._pkg = pkg_manager

    def detect_groups(self) -> list[InputMethodGroup]:
        """Return groups for each IM framework that has installed packages."""
        groups: list[InputMethodGroup] = []
        for key, meta in _INPUT_METHOD_GROUPS.items():
            patterns: list[str] = cast(list[str], meta["patterns"])
            matched = self._pkg.filter_by_patterns(patterns)
            if matched:
                total_kb = self._pkg.calculate_group_size(matched)
                groups.append(
                    InputMethodGroup(
                        key=key,
                        label=str(meta["label"]),
                        packages=matched,
                        total_size_kb=total_kb,
                    )
                )
        return groups
