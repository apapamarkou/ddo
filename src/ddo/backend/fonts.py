"""Font detection and grouping.

Groups installed font packages by script/region so the user can
selectively remove fonts they do not need.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import cast

from ddo.backend.packages import PackageManager

logger = logging.getLogger(__name__)

# Mapping of logical font group → glob patterns
_FONT_GROUPS: dict[str, dict[str, object]] = {
    "cjk": {
        "label": "CJK (Chinese, Japanese, Korean) Fonts",
        "patterns": [
            "fonts-noto-cjk",
            "fonts-noto-cjk-extra",
            "fonts-ipafont*",
            "fonts-nanum",
            "fonts-vlgothic",
        ],
    },
    "arabic": {
        "label": "Arabic & Persian Fonts",
        "patterns": [
            "fonts-hosny-*",
            "fonts-kacst*",
            "fonts-sil-scheherazade",
            "fonts-sahel-variable",
            "fonts-vazirmatn-variable",
            "fonts-unikurdweb",
            "fonts-farsiweb",
        ],
    },
    "indic": {
        "label": "Indic Script Fonts",
        "patterns": [
            "fonts-beng",
            "fonts-beng-extra",
            "fonts-deva*",
            "fonts-gargi",
            "fonts-gujr*",
            "fonts-guru*",
            "fonts-kalapi",
            "fonts-lohit-*",
            "fonts-mlym",
            "fonts-nakula",
            "fonts-sahadeva",
            "fonts-samyak-*",
            "fonts-sarai",
            "fonts-smc*",
            "fonts-telu*",
            "fonts-teluguvijayam",
            "fonts-yrsa-rasa",
        ],
    },
    "thai": {
        "label": "Thai Fonts",
        "patterns": [
            "fonts-arundina",
            "fonts-thai-tlwg",
            "fonts-tlwg-*",
            "xfonts-thai*",
        ],
    },
    "georgian": {
        "label": "Georgian Fonts",
        "patterns": ["fonts-bpg-georgian"],
    },
    "khmer": {
        "label": "Khmer Fonts",
        "patterns": ["fonts-khmeros"],
    },
    "hebrew": {
        "label": "Hebrew Fonts",
        "patterns": ["culmus", "fonts-culmus"],
    },
    "ethiopic": {
        "label": "Ethiopic/Amharic Fonts",
        "patterns": ["fonts-sil-abyssinica", "fonts-sil-andika", "fonts-sil-annapurna"],
    },
    "uyghur": {
        "label": "Uyghur Fonts",
        "patterns": ["fonts-ukij-uyghur"],
    },
    "noto_extra": {
        "label": "Noto Extra Fonts (large)",
        "patterns": ["fonts-noto-extra", "fonts-noto-ui-extra", "fonts-noto-unhinted"],
    },
}


@dataclass
class FontGroup:
    """A group of font packages sharing a script or region."""

    key: str
    label: str
    packages: list[str] = field(default_factory=list)
    total_size_kb: int = 0


class FontManager:
    """Detect and categorise installed font packages."""

    def __init__(self, pkg_manager: PackageManager) -> None:
        self._pkg = pkg_manager

    def detect_groups(self) -> list[FontGroup]:
        """Return a FontGroup for each script that has installed packages."""
        groups: list[FontGroup] = []
        for key, meta in _FONT_GROUPS.items():
            patterns: list[str] = cast(list[str], meta["patterns"])
            matched = self._pkg.filter_by_patterns(patterns)
            if matched:
                total_kb = self._pkg.calculate_group_size(matched)
                groups.append(
                    FontGroup(
                        key=key,
                        label=str(meta["label"]),
                        packages=matched,
                        total_size_kb=total_kb,
                    )
                )
        return groups

    def all_font_packages(self) -> list[str]:
        """Return all installed packages whose name starts with ``fonts-``."""
        return [p.name for p in self._pkg.filter_by_pattern("fonts-*")]
