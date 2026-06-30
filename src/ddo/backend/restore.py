"""Restore previously removed packages.

Reads the rollback log written by CleanupEngine and reinstalls packages.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import cast

from ddo.backend.apt import AptManager
from ddo.backend.exceptions import RollbackError

logger = logging.getLogger(__name__)

_ROLLBACK_DIR = Path.home() / ".local" / "state" / "ddo" / "rollback"


@dataclass
class RollbackEntry:
    """A single rollback checkpoint."""

    timestamp: str
    packages: list[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "packages": self.packages,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> RollbackEntry:
        return cls(
            timestamp=str(data.get("timestamp", "")),
            packages=cast(list[str], data.get("packages") or []),
            description=str(data.get("description", "")),
        )


class RestoreEngine:
    """Record removed packages and restore them on demand."""

    def __init__(
        self,
        apt_manager: AptManager,
        rollback_dir: Path | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ) -> None:
        self._apt = apt_manager
        self._dir = rollback_dir or _ROLLBACK_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._cb = progress_callback or (lambda _: None)

    def save_rollback(self, packages: list[str], description: str = "") -> RollbackEntry:
        """Persist a rollback checkpoint before removal."""
        entry = RollbackEntry(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            packages=packages,
            description=description,
        )
        path = self._dir / f"{entry.timestamp.replace(':', '-')}.json"
        path.write_text(json.dumps(entry.to_dict(), indent=2), encoding="utf-8")
        logger.info("Saved rollback: %s (%d packages)", path.name, len(packages))
        return entry

    def list_rollbacks(self) -> list[RollbackEntry]:
        """Return all saved rollback entries, newest first."""
        entries: list[RollbackEntry] = []
        for p in sorted(self._dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                entries.append(RollbackEntry.from_dict(data))
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning("Skipping malformed rollback file %s: %s", p, exc)
        return entries

    def restore(self, entry: RollbackEntry, *, dry_run: bool = False) -> None:
        """Reinstall packages from a rollback entry.

        Parameters
        ----------
        entry:
            The checkpoint to restore.
        dry_run:
            If True, only print what would be installed.
        """
        if not entry.packages:
            raise RollbackError("Rollback entry has no packages to restore.")

        if dry_run:
            self._cb(
                f"DRY RUN: would reinstall {len(entry.packages)} packages "
                f"from {entry.timestamp}"
            )
            return

        self._cb(f"Restoring {len(entry.packages)} packages from {entry.timestamp}…")
        self._apt.install(entry.packages)
        logger.info(
            "Restored %d package(s) from rollback %s",
            len(entry.packages),
            entry.timestamp,
        )

    def restore_language_packages(self, packages: list[str], *, dry_run: bool = False) -> None:
        """Convenience: install a specific list of language packages."""
        if not packages:
            return
        if dry_run:
            self._cb(f"DRY RUN: would install {len(packages)} language package(s)")
            return
        self._cb(f"Installing {len(packages)} language package(s)…")
        self._apt.install(packages)
