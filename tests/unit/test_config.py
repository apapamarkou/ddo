"""Unit tests for AppConfig."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ddo.models.config import AppConfig


class TestAppConfig:
    def test_default_config(self) -> None:
        cfg = AppConfig()
        assert cfg.kept_languages == ["en"]
        assert cfg.auto_update is True
        assert cfg.theme == "system"

    def test_save_and_load(self, tmp_path: Path) -> None:
        path = tmp_path / "config.yaml"
        cfg = AppConfig(kept_languages=["en", "fr", "de"], theme="dark")
        cfg.save(path)
        loaded = AppConfig.load(path)
        assert loaded.kept_languages == ["en", "fr", "de"]
        assert loaded.theme == "dark"

    def test_load_nonexistent_returns_defaults(self, tmp_path: Path) -> None:
        path = tmp_path / "missing.yaml"
        cfg = AppConfig.load(path)
        assert cfg.kept_languages == ["en"]

    def test_load_malformed_yaml_returns_defaults(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.yaml"
        path.write_text("{ invalid yaml: [", encoding="utf-8")
        cfg = AppConfig.load(path)
        assert cfg.kept_languages == ["en"]

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "nested" / "config.yaml"
        cfg = AppConfig(kept_languages=["es"])
        cfg.save(path)
        assert path.exists()
        loaded = yaml.safe_load(path.read_text())
        assert "es" in loaded["kept_languages"]

    def test_first_run_flag(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        flag = tmp_path / ".initialized"
        monkeypatch.setattr("ddo.models.config._FIRST_RUN_FLAG", flag)
        assert AppConfig.is_first_run() is True
        AppConfig.mark_initialized()
        assert AppConfig.is_first_run() is False
