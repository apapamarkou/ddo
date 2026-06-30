"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ddo.backend.apt import AptManager, PackageInfo, SimulationResult
from ddo.backend.packages import PackageManager
from ddo.models.config import AppConfig

# ---------------------------------------------------------------------------
# Sample package list (subset of the real installed-packages.txt)
# ---------------------------------------------------------------------------

SAMPLE_PACKAGES = [
    PackageInfo("firefox-esr-l10n-de", "140.0", "all", 512, "web"),
    PackageInfo("firefox-esr-l10n-fr", "140.0", "all", 512, "web"),
    PackageInfo("firefox-esr-l10n-ja", "140.0", "all", 512, "web"),
    PackageInfo("firefox-esr-l10n-en-gb", "140.0", "all", 256, "web"),
    PackageInfo("libreoffice-l10n-de", "25.0", "all", 2048, "office"),
    PackageInfo("libreoffice-l10n-fr", "25.0", "all", 2048, "office"),
    PackageInfo("libreoffice-l10n-ja", "25.0", "all", 2048, "office"),
    PackageInfo("aspell-de", "20161207", "all", 1024, "text"),
    PackageInfo("aspell-fr", "0.50", "all", 512, "text"),
    PackageInfo("hunspell-de-de", "20161207", "all", 1024, "text"),
    PackageInfo("fonts-noto-cjk", "20240730", "all", 102400, "fonts"),
    PackageInfo("fonts-vlgothic", "20220612", "all", 8192, "fonts"),
    PackageInfo("anthy-common", "0.4", "all", 4096, "utils"),
    PackageInfo("mozc-data", "2.29", "all", 8192, "utils"),
    PackageInfo("task-japanese-desktop", "3.81", "all", 0, "tasks"),
    PackageInfo("task-german-desktop", "3.81", "all", 0, "tasks"),
    PackageInfo("task-french-desktop", "3.81", "all", 0, "tasks"),
    PackageInfo("fcitx5", "5.1.12", "amd64", 2048, "utils"),
    PackageInfo("fcitx5-chinese-addons", "5.1.8", "all", 4096, "utils"),
    PackageInfo("gnome-chess", "43.0", "amd64", 2048, "games"),
    PackageInfo("gnome-sudoku", "43.0", "amd64", 1024, "games"),
    PackageInfo("cups", "2.4.10", "amd64", 8192, "net"),
    PackageInfo("cups-daemon", "2.4.10", "amd64", 4096, "net"),
    PackageInfo("espeak-ng-data", "1.52.0", "all", 16384, "sound"),
    PackageInfo("speech-dispatcher", "0.12.0", "amd64", 2048, "sound"),
    PackageInfo("apt", "3.0.3", "amd64", 4096, "admin"),
    PackageInfo("base-files", "13.8", "amd64", 512, "admin"),
    PackageInfo("dpkg", "1.22.22", "amd64", 8192, "admin"),
    PackageInfo("libc6", "2.41", "amd64", 16384, "libs"),
    PackageInfo("bash", "5.2.37", "amd64", 2048, "shells"),
]


@pytest.fixture
def mock_apt() -> AptManager:
    """Return a fully mocked AptManager that never calls real apt."""
    apt = MagicMock(spec=AptManager)
    apt.installed_packages.return_value = SAMPLE_PACKAGES
    apt.package_size.return_value = 1024

    sim = SimulationResult(
        to_remove=["firefox-esr-l10n-de", "aspell-de"],
        to_install=[],
        space_freed_bytes=2 * 1024 * 1024,
        is_safe=True,
    )
    apt.simulate.return_value = sim
    apt.purge.return_value = None
    apt.install.return_value = None
    apt.update.return_value = None
    apt.upgrade.return_value = None
    apt.autoremove.return_value = None
    apt.autoclean.return_value = None
    return apt


@pytest.fixture
def pkg_manager(mock_apt: AptManager) -> PackageManager:
    """Return a PackageManager backed by the mock apt."""
    return PackageManager(mock_apt)


@pytest.fixture
def default_config(tmp_path: Path) -> AppConfig:
    """Return an AppConfig with 'en' as the only kept language."""
    cfg = AppConfig(kept_languages=["en"])
    cfg._path = tmp_path / "config.yaml"
    return cfg


@pytest.fixture
def languages_db_path() -> Path:
    """Return the real bundled languages.yaml path."""
    p = Path(__file__).parent.parent / "data" / "languages" / "languages.yaml"
    assert p.exists(), f"languages.yaml not found at {p}"
    return p
