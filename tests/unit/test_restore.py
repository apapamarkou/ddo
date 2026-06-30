"""Unit tests for RestoreEngine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ddo.backend.restore import RestoreEngine, RollbackEntry


class TestRestoreEngine:
    def test_save_and_list_rollback(self, mock_apt: object, tmp_path: Path) -> None:
        engine = RestoreEngine(mock_apt, rollback_dir=tmp_path)  # type: ignore[arg-type]
        engine.save_rollback(["pkg-a", "pkg-b"], "test")
        entries = engine.list_rollbacks()
        assert len(entries) == 1
        assert entries[0].packages == ["pkg-a", "pkg-b"]
        assert entries[0].description == "test"

    def test_list_sorted_newest_first(self, mock_apt: object, tmp_path: Path) -> None:
        # Write two entries with explicitly distinct timestamps via fixed filenames
        old = tmp_path / "2024-01-01T10-00-00.json"
        new = tmp_path / "2024-06-01T10-00-00.json"
        old.write_text(
            json.dumps({"timestamp": "2024-01-01T10:00:00", "packages": ["a"], "description": ""}),
            encoding="utf-8",
        )
        new.write_text(
            json.dumps({"timestamp": "2024-06-01T10:00:00", "packages": ["b"], "description": ""}),
            encoding="utf-8",
        )
        engine = RestoreEngine(mock_apt, rollback_dir=tmp_path)  # type: ignore[arg-type]
        entries = engine.list_rollbacks()
        assert len(entries) == 2
        assert entries[0].timestamp >= entries[1].timestamp

    def test_restore_calls_install(self, mock_apt: object, tmp_path: Path) -> None:
        engine = RestoreEngine(mock_apt, rollback_dir=tmp_path)  # type: ignore[arg-type]
        entry = RollbackEntry(timestamp="2024-01-01T00:00:00", packages=["pkg-a"])
        engine.restore(entry)
        mock_apt.install.assert_called_with(["pkg-a"])  # type: ignore[attr-defined]

    def test_restore_dry_run_no_install(self, mock_apt: object, tmp_path: Path) -> None:
        engine = RestoreEngine(mock_apt, rollback_dir=tmp_path)  # type: ignore[arg-type]
        entry = RollbackEntry(timestamp="2024-01-01T00:00:00", packages=["pkg-a"])
        engine.restore(entry, dry_run=True)
        mock_apt.install.assert_not_called()  # type: ignore[attr-defined]

    def test_restore_empty_raises(self, mock_apt: object, tmp_path: Path) -> None:
        from ddo.backend.exceptions import RollbackError

        engine = RestoreEngine(mock_apt, rollback_dir=tmp_path)  # type: ignore[arg-type]
        entry = RollbackEntry(timestamp="2024-01-01T00:00:00", packages=[])
        with pytest.raises(RollbackError):
            engine.restore(entry)

    def test_skips_malformed_json(self, mock_apt: object, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{invalid", encoding="utf-8")
        engine = RestoreEngine(mock_apt, rollback_dir=tmp_path)  # type: ignore[arg-type]
        # Should not raise; malformed file is silently skipped
        entries = engine.list_rollbacks()
        assert len(entries) == 0
