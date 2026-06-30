"""Unit tests for LanguageManager."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from ddo.backend.languages import LanguageManager
from ddo.backend.packages import PackageManager


class TestLanguageManager:
    def test_load_db_from_real_file(
        self, pkg_manager: PackageManager, languages_db_path: Path
    ) -> None:
        lang = LanguageManager(pkg_manager, db_path=languages_db_path)
        assert len(lang._db) > 10, "Expected many language definitions"

    def test_detect_installed_returns_languages(
        self, pkg_manager: PackageManager, languages_db_path: Path
    ) -> None:
        lang = LanguageManager(pkg_manager, db_path=languages_db_path)
        detected = lang.detect_installed()
        # Our SAMPLE_PACKAGES includes de, fr, ja packages
        codes = [d.code for d in detected]
        assert "de" in codes
        assert "fr" in codes
        assert "ja" in codes

    def test_detect_installed_excludes_empty_languages(
        self, pkg_manager: PackageManager, languages_db_path: Path
    ) -> None:
        lang = LanguageManager(pkg_manager, db_path=languages_db_path)
        detected = lang.detect_installed()
        # All detected languages must have at least one package
        assert all(d.installed_packages for d in detected)

    def test_packages_for_language(
        self, pkg_manager: PackageManager, languages_db_path: Path
    ) -> None:
        lang = LanguageManager(pkg_manager, db_path=languages_db_path)
        pkgs = lang.packages_for_language("de")
        assert "firefox-esr-l10n-de" in pkgs

    def test_packages_for_unknown_language(
        self, pkg_manager: PackageManager, languages_db_path: Path
    ) -> None:
        lang = LanguageManager(pkg_manager, db_path=languages_db_path)
        assert lang.packages_for_language("zz") == []

    def test_current_language_code_from_env(
        self, pkg_manager: PackageManager, languages_db_path: Path
    ) -> None:
        lang = LanguageManager(pkg_manager, db_path=languages_db_path)
        with patch.dict(os.environ, {"LANG": "fr_FR.UTF-8"}, clear=False):
            code = lang.current_language_code()
        assert code == "fr"

    def test_current_language_code_fallback(
        self, pkg_manager: PackageManager, languages_db_path: Path
    ) -> None:
        lang = LanguageManager(pkg_manager, db_path=languages_db_path)
        with patch.dict(os.environ, {"LANG": "xx_XX.UTF-8"}, clear=False):
            code = lang.current_language_code()
        assert code == "en"

    def test_all_language_codes_sorted_by_name(
        self, pkg_manager: PackageManager, languages_db_path: Path
    ) -> None:
        lang = LanguageManager(pkg_manager, db_path=languages_db_path)
        codes = lang.all_language_codes()
        names = [n for _, n in codes]
        assert names == sorted(names)

    def test_missing_db_raises(self, pkg_manager: PackageManager) -> None:
        from ddo.backend.exceptions import LanguageDetectionError

        with pytest.raises(LanguageDetectionError):
            LanguageManager(pkg_manager, db_path=Path("/nonexistent/path.yaml"))
