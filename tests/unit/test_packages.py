"""Unit tests for PackageManager."""

from __future__ import annotations

from ddo.backend.packages import PackageManager


class TestPackageManager:
    def test_all_installed_returns_cached(self, pkg_manager: PackageManager) -> None:
        first = pkg_manager.all_installed()
        second = pkg_manager.all_installed()
        assert first is second  # same object — cached

    def test_refresh_invalidates_cache(self, pkg_manager: PackageManager) -> None:
        # Call count before refresh
        pkg_manager.all_installed()
        call_count_before = pkg_manager._apt.installed_packages.call_count  # type: ignore[attr-defined]
        pkg_manager.refresh()
        pkg_manager.all_installed()
        call_count_after = pkg_manager._apt.installed_packages.call_count  # type: ignore[attr-defined]
        assert call_count_after == call_count_before + 1

    def test_filter_by_pattern_glob(self, pkg_manager: PackageManager) -> None:
        matches = pkg_manager.filter_by_pattern("firefox-esr-l10n-*")
        names = [p.name for p in matches]
        assert "firefox-esr-l10n-de" in names
        assert "firefox-esr-l10n-fr" in names
        assert all("libreoffice" not in n for n in names)

    def test_filter_by_patterns_multiple(self, pkg_manager: PackageManager) -> None:
        names = pkg_manager.filter_by_patterns(["aspell-*", "hunspell-*"])
        assert "aspell-de" in names
        assert "aspell-fr" in names
        assert "hunspell-de-de" in names

    def test_filter_by_patterns_no_match(self, pkg_manager: PackageManager) -> None:
        names = pkg_manager.filter_by_patterns(["nonexistent-package-xyz-*"])
        assert names == []

    def test_calculate_group_size(self, pkg_manager: PackageManager) -> None:
        size = pkg_manager.calculate_group_size(["firefox-esr-l10n-de", "firefox-esr-l10n-fr"])
        # Each is 512 KB in SAMPLE_PACKAGES
        assert size == 1024

    def test_names_set(self, pkg_manager: PackageManager) -> None:
        names = pkg_manager.names_set()
        assert isinstance(names, set)
        assert "apt" in names
        assert "firefox-esr-l10n-de" in names
