"""Application configuration model.

Reads and writes ``~/.config/ddo/config.yaml``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path.home() / ".config" / "ddo" / "config.yaml"
_FIRST_RUN_FLAG = Path.home() / ".config" / "ddo" / ".initialized"


@dataclass
class AppConfig:
    """Runtime configuration for Debian Desktop Optimizer."""

    # Languages to keep (BCP-47 codes)
    kept_languages: list[str] = field(default_factory=lambda: ["en"])
    # Package names/globs to never remove
    ignored_packages: list[str] = field(default_factory=list)
    # Service names to never touch
    ignored_services: list[str] = field(default_factory=list)
    # Whether to run updates after cleanup
    auto_update: bool = True
    # "system" | "dark" | "light"
    theme: str = "system"
    # Path to an alternative languages.yaml
    languages_db_path: str = ""
    # Enable verbose/debug logging
    debug: bool = False
    # Path where config was loaded from
    _path: Path = field(default=_DEFAULT_CONFIG_PATH, repr=False, compare=False)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: Path | None = None) -> AppConfig:
        """Load config from *path* (default: ``~/.config/ddo/config.yaml``)."""
        config_path = path or _DEFAULT_CONFIG_PATH
        if not config_path.exists():
            logger.debug("Config file not found, using defaults: %s", config_path)
            instance = cls()
            instance._path = config_path
            return instance
        try:
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            logger.warning("Failed to parse config %s: %s — using defaults", config_path, exc)
            raw = {}

        instance = cls(
            kept_languages=list(raw.get("kept_languages", ["en"])),
            ignored_packages=list(raw.get("ignored_packages", [])),
            ignored_services=list(raw.get("ignored_services", [])),
            auto_update=bool(raw.get("auto_update", True)),
            theme=str(raw.get("theme", "system")),
            languages_db_path=str(raw.get("languages_db_path", "")),
            debug=bool(raw.get("debug", False)),
        )
        instance._path = config_path
        logger.debug("Loaded config from %s", config_path)
        return instance

    def save(self, path: Path | None = None) -> None:
        """Write config to *path* (default: path it was loaded from)."""
        save_path = path or self._path
        save_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "kept_languages": self.kept_languages,
            "ignored_packages": self.ignored_packages,
            "ignored_services": self.ignored_services,
            "auto_update": self.auto_update,
            "theme": self.theme,
            "languages_db_path": self.languages_db_path,
            "debug": self.debug,
        }
        save_path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
        logger.debug("Saved config to %s", save_path)

    # ------------------------------------------------------------------
    # First-run detection
    # ------------------------------------------------------------------

    @staticmethod
    def is_first_run() -> bool:
        """Return True if the application has never been run before."""
        return not _FIRST_RUN_FLAG.exists()

    @staticmethod
    def mark_initialized() -> None:
        """Create the flag file that marks a successful first run."""
        _FIRST_RUN_FLAG.parent.mkdir(parents=True, exist_ok=True)
        _FIRST_RUN_FLAG.touch()
        logger.info("Marked application as initialized")
