"""Unit tests for AptManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ddo.backend.apt import AptManager
from ddo.backend.exceptions import (
    DangerousOperationError,
)


class TestAptManagerInstalled:
    def test_installed_packages_parses_output(self) -> None:
        raw = "apt\t3.0.3\tamd64\t4096\tadmin\tii \n"
        apt = AptManager()
        with patch.object(apt, "_run") as mock_run:
            mock_run.return_value = MagicMock(stdout=raw, returncode=0)
            pkgs = apt.installed_packages()
        assert len(pkgs) == 1
        assert pkgs[0].name == "apt"
        assert pkgs[0].installed_size_kb == 4096

    def test_skips_non_installed_packages(self) -> None:
        raw = "foo\t1.0\tamd64\t100\tmisc\tun \n"
        apt = AptManager()
        with patch.object(apt, "_run") as mock_run:
            mock_run.return_value = MagicMock(stdout=raw, returncode=0)
            pkgs = apt.installed_packages()
        assert pkgs == []

    def test_package_size_returns_int(self) -> None:
        apt = AptManager()
        with patch.object(apt, "_run") as mock_run:
            mock_run.return_value = MagicMock(stdout="2048\n", returncode=0)
            size = apt.package_size("foo")
        assert size == 2048

    def test_package_size_returns_zero_on_failure(self) -> None:
        apt = AptManager()
        with patch.object(apt, "_run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=1)
            size = apt.package_size("nonexistent")
        assert size == 0


class TestPackageManager:
    def test_packages_by_section_filters_correctly(self) -> None:
        from ddo.backend.apt import PackageInfo
        from ddo.backend.packages import PackageManager

        apt = AptManager()
        pkgs = [
            PackageInfo(
                name="gnome-chess",
                version="1",
                architecture="amd64",
                installed_size_kb=100,
                section="games",
            ),
            PackageInfo(
                name="bash",
                version="5",
                architecture="amd64",
                installed_size_kb=200,
                section="shells",
            ),
            PackageInfo(
                name="supertux",
                version="2",
                architecture="amd64",
                installed_size_kb=150,
                section="games",
            ),
        ]
        pkg = PackageManager(apt)
        with patch.object(pkg, "all_installed", return_value=pkgs):
            result = pkg.packages_by_section("games")
        assert result == ["gnome-chess", "supertux"]
        assert "bash" not in result


class TestAptManagerPermissions:
    def test_update_uses_pkexec_when_not_root(self) -> None:
        apt = AptManager()
        with patch("os.geteuid", return_value=1000), patch.object(apt, "_run") as mock_run:
            apt.update()
            cmd = mock_run.call_args[0][0]
            assert cmd[0] == "pkexec"

    def test_purge_uses_pkexec_when_not_root(self) -> None:
        from ddo.backend.apt import SimulationResult

        apt = AptManager()
        safe_sim = SimulationResult(to_remove=["foo"], dangerous_packages=[], space_freed_bytes=0)
        with (
            patch("os.geteuid", return_value=1000),
            patch.object(apt, "simulate", return_value=safe_sim),
            patch.object(apt, "_run") as mock_run,
        ):
            apt.purge(["foo"])
            cmd = mock_run.call_args[0][0]
            assert cmd[0] == "pkexec"


class TestAptManagerSafety:
    def test_purge_refuses_critical_packages(self) -> None:
        apt = AptManager()
        with patch("os.geteuid", return_value=0), pytest.raises(DangerousOperationError):
            apt.purge(["apt", "libc6"], force=False)

    def test_purge_critical_with_force_skips_validation(self) -> None:
        apt = AptManager()
        with patch("os.geteuid", return_value=0), patch.object(apt, "_run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            # force=True bypasses critical package check
            apt.purge(["apt"], force=True)
            mock_run.assert_called()


class TestSimulation:
    def test_simulate_parses_removals(self) -> None:
        apt = AptManager()
        output = "Remv firefox-esr-l10n-de [140.0]\nRemv aspell-de [20.0]\n"
        with patch.object(apt, "_run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, stderr="", returncode=0)
            with patch.object(apt, "package_size", return_value=1024):
                result = apt.simulate(["firefox-esr-l10n-de", "aspell-de"])
        assert "firefox-esr-l10n-de" in result.to_remove
        assert "aspell-de" in result.to_remove
        assert result.is_safe is True

    def test_simulate_flags_critical_removals(self) -> None:
        apt = AptManager()
        output = "Remv apt [3.0]\nRemv base-files [13.0]\n"
        with patch.object(apt, "_run") as mock_run:
            mock_run.return_value = MagicMock(stdout=output, stderr="", returncode=0)
            with patch.object(apt, "package_size", return_value=0):
                result = apt.simulate(["apt", "base-files"])
        assert result.is_safe is False
        assert len(result.dangerous_packages) > 0

    def test_simulate_empty_list_returns_empty_result(self) -> None:
        apt = AptManager()
        result = apt.simulate([])
        assert result.to_remove == []
        assert result.space_freed_bytes == 0
