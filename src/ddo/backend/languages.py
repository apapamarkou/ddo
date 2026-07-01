"""Language detection and management.

Reads language definitions from the bundled YAML database and correlates
them with packages actually installed on the system.
"""

from __future__ import annotations

import locale
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ddo.backend.exceptions import LanguageDetectionError
from ddo.backend.packages import PackageManager

logger = logging.getLogger(__name__)

# Built-in path to the bundled language database.
_SYSTEM_DB = Path("/usr/share/ddo/languages/languages.yaml")
_SOURCE_DB = Path(__file__).parent.parent.parent.parent / "data" / "languages" / "languages.yaml"
_DEFAULT_DB: Path = _SYSTEM_DB if _SYSTEM_DB.exists() else _SOURCE_DB


@dataclass
class LanguageInfo:
    """Details about a single language as detected on the system."""

    code: str
    name: str
    installed_packages: list[str] = field(default_factory=list)
    total_size_kb: int = 0


class LanguageManager:
    """Detect and manage language-related packages.

    Parameters
    ----------
    pkg_manager:
        A ``PackageManager`` instance for querying installed packages.
    db_path:
        Optional path to an alternative ``languages.yaml``.
    """

    def __init__(
        self,
        pkg_manager: PackageManager,
        db_path: Path | None = None,
    ) -> None:
        self._pkg = pkg_manager
        self._db_path = db_path or _DEFAULT_DB
        self._db: dict[str, Any] = {}
        self._load_db()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _load_db(self) -> None:
        if not self._db_path.exists():
            raise LanguageDetectionError(f"Language database not found: {self._db_path}")
        with self._db_path.open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        self._db = raw.get("languages", {})
        logger.debug("Loaded %d language definitions", len(self._db))

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect_installed(self) -> list[LanguageInfo]:
        """Return LanguageInfo for every language that has at least one
        installed package on the current system.
        """
        installed_names = self._pkg.names_set()
        result: list[LanguageInfo] = []

        for code, meta in self._db.items():
            patterns: list[str] = meta.get("patterns", [])
            matched = self._pkg.filter_by_patterns(patterns)
            matched = [p for p in matched if p in installed_names]
            if matched:
                total_kb = self._pkg.calculate_group_size(matched)
                result.append(
                    LanguageInfo(
                        code=code,
                        name=meta.get("name", code),
                        installed_packages=matched,
                        total_size_kb=total_kb,
                    )
                )

        logger.debug("Detected %d installed languages", len(result))
        return sorted(result, key=lambda x: x.name)

    def packages_for_language(self, code: str) -> list[str]:
        """Return installed packages belonging to language *code*."""
        meta = self._db.get(code)
        if not meta:
            return []
        patterns: list[str] = meta.get("patterns", [])
        installed_names = self._pkg.names_set()
        matched = self._pkg.filter_by_patterns(patterns)
        return [p for p in matched if p in installed_names]

    # ------------------------------------------------------------------
    # Current system locale
    # ------------------------------------------------------------------

    @staticmethod
    def current_locale() -> str:
        """Return the current system locale code, e.g. ``en_US``."""
        lang = os.environ.get("LANG") or os.environ.get("LANGUAGE") or ""
        if lang:
            return lang.split(".")[0]
        try:
            loc = locale.getdefaultlocale()[0] or "en_US"
            return loc
        except ValueError:
            return "en_US"

    @staticmethod
    def enabled_locales() -> list[str]:
        """Return list of locales enabled in /etc/locale.gen."""
        path = Path("/etc/locale.gen")
        if not path.exists():
            return []
        locales: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                locales.append(line.split()[0])
        return locales

    def current_language_code(self) -> str:
        """Map the current system locale to a language code in our DB.

        Falls back to ``en`` if no match is found.
        """
        current = self.current_locale().lower()
        # Direct match (e.g. "zh_cn" → "zh-cn")
        normalised = current.replace("_", "-")
        if normalised in self._db:
            return normalised
        # Match just the primary subtag (e.g. "fr_FR" → "fr")
        primary = normalised.split("-")[0]
        if primary in self._db:
            return primary
        return "en"

    # ------------------------------------------------------------------
    # All language definitions (for display in UI)
    # ------------------------------------------------------------------

    def all_language_codes(self) -> list[tuple[str, str]]:
        """Return all (code, name) pairs from the database, sorted by name."""
        return sorted(
            ((code, meta.get("name", code)) for code, meta in self._db.items()),
            key=lambda x: x[1],
        )
