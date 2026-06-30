"""Unit tests for formatting helpers, FontManager, InputMethodManager, and ServiceManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ddo.backend.fonts import FontManager
from ddo.backend.inputmethods import InputMethodManager
from ddo.backend.packages import PackageManager
from ddo.utils.formatting import format_bytes, format_package_count

# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


class TestFormatBytes:
    def test_bytes(self) -> None:
        assert format_bytes(512) == "512 B"

    def test_kibibytes(self) -> None:
        assert "KiB" in format_bytes(2048)

    def test_mebibytes(self) -> None:
        assert "MiB" in format_bytes(5 * 1024 * 1024)

    def test_gibibytes(self) -> None:
        assert "GiB" in format_bytes(3 * 1024**3)

    def test_zero(self) -> None:
        assert format_bytes(0) == "0 B"


class TestFormatPackageCount:
    def test_singular(self) -> None:
        assert format_package_count(1) == "1 package"

    def test_plural(self) -> None:
        assert format_package_count(5) == "5 packages"

    def test_zero(self) -> None:
        assert format_package_count(0) == "0 packages"


# ---------------------------------------------------------------------------
# FontManager
# ---------------------------------------------------------------------------


class TestFontManager:
    def test_detect_groups_returns_list(self, pkg_manager: PackageManager) -> None:
        fm = FontManager(pkg_manager)
        groups = fm.detect_groups()
        assert isinstance(groups, list)

    def test_detect_groups_finds_cjk(self, pkg_manager: PackageManager) -> None:
        fm = FontManager(pkg_manager)
        groups = fm.detect_groups()
        keys = [g.key for g in groups]
        # SAMPLE_PACKAGES includes fonts-noto-cjk and fonts-vlgothic
        assert "cjk" in keys

    def test_group_has_packages(self, pkg_manager: PackageManager) -> None:
        fm = FontManager(pkg_manager)
        groups = fm.detect_groups()
        for group in groups:
            assert group.packages, f"Group {group.key!r} has no packages"

    def test_all_font_packages(self, pkg_manager: PackageManager) -> None:
        fm = FontManager(pkg_manager)
        pkgs = fm.all_font_packages()
        assert isinstance(pkgs, list)
        # SAMPLE_PACKAGES has fonts-noto-cjk and fonts-vlgothic
        assert "fonts-noto-cjk" in pkgs


# ---------------------------------------------------------------------------
# InputMethodManager
# ---------------------------------------------------------------------------


class TestInputMethodManager:
    def test_detect_groups_returns_list(self, pkg_manager: PackageManager) -> None:
        im = InputMethodManager(pkg_manager)
        groups = im.detect_groups()
        assert isinstance(groups, list)

    def test_detects_fcitx5(self, pkg_manager: PackageManager) -> None:
        im = InputMethodManager(pkg_manager)
        groups = im.detect_groups()
        keys = [g.key for g in groups]
        # SAMPLE_PACKAGES includes fcitx5 and fcitx5-chinese-addons
        assert "fcitx5" in keys

    def test_detects_mozc(self, pkg_manager: PackageManager) -> None:
        im = InputMethodManager(pkg_manager)
        groups = im.detect_groups()
        keys = [g.key for g in groups]
        # SAMPLE_PACKAGES includes mozc-data
        assert "mozc" in keys

    def test_group_has_packages(self, pkg_manager: PackageManager) -> None:
        im = InputMethodManager(pkg_manager)
        for group in im.detect_groups():
            assert group.packages, f"Group {group.key!r} is empty"


# ---------------------------------------------------------------------------
# ServiceManager (no systemd available in test env — mock subprocess)
# ---------------------------------------------------------------------------


class TestServiceManager:
    def test_list_optional_services(self) -> None:
        from ddo.backend.services import ServiceManager

        svc = ServiceManager()
        mock_result = MagicMock()
        mock_result.returncode = 1  # all services inactive/disabled in CI
        with patch("subprocess.run", return_value=mock_result):
            services = svc.list_optional_services()
        assert len(services) > 0
        names = [s.name for s in services]
        assert "bluetooth" in names
        assert "cups" in names

    def test_disable_protected_raises(self) -> None:
        from ddo.backend.services import ServiceManager

        svc = ServiceManager()
        with pytest.raises(ValueError, match="protected"):
            svc.disable("systemd-journald")

    def test_active_service_detected(self) -> None:
        from ddo.backend.services import ServiceManager

        svc = ServiceManager()
        active_result = MagicMock()
        active_result.returncode = 0
        with patch("subprocess.run", return_value=active_result):
            services = svc.list_optional_services()
        assert all(s.active for s in services)
