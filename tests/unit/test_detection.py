"""Unit tests for DetectionEngine."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ddo.backend.detection import DetectionEngine
from ddo.backend.packages import PackageManager


class TestDetectionEngine:
    def test_detect_returns_profile(self, pkg_manager: PackageManager) -> None:
        engine = DetectionEngine(pkg_manager)
        mock_result = MagicMock()
        mock_result.stdout = "amd64\n"
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            profile = engine.detect()
        assert profile.installed_package_names
        assert profile.architecture == "amd64"

    def test_detect_desktop_xfce(self, pkg_manager: PackageManager) -> None:
        from ddo.backend.apt import PackageInfo
        from tests.conftest import SAMPLE_PACKAGES

        extra = [PackageInfo("xfce4", "4.20", "all", 0, "x11")]
        all_pkgs = SAMPLE_PACKAGES + extra
        pkg_manager._cache = all_pkgs
        engine = DetectionEngine(pkg_manager)
        de = engine._detect_desktop({p.name for p in all_pkgs})
        assert de == "xfce"

    def test_detect_locale_from_env(self) -> None:
        import os

        with patch.dict(os.environ, {"LANG": "pt_BR.UTF-8"}):
            locale = DetectionEngine._detect_locale()
        assert locale == "pt_BR"

    def test_detect_laptop_not_chassis(self) -> None:
        with patch("pathlib.Path.exists", return_value=False):
            result = DetectionEngine._detect_laptop()
        assert result is False
