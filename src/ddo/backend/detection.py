"""System detection engine.

Probes the running system and returns a SystemProfile dataclass
containing everything the cleanup engine needs to know.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ddo.backend.packages import PackageManager

logger = logging.getLogger(__name__)


@dataclass
class SystemProfile:
    """Snapshot of the detected system state."""

    desktop_environment: str = "unknown"
    installed_package_names: list[str] = field(default_factory=list)
    current_locale: str = "en_US"
    enabled_locales: list[str] = field(default_factory=list)
    keyboard_layouts: list[str] = field(default_factory=list)
    has_printer: bool = False
    has_bluetooth: bool = False
    has_modem: bool = False
    is_laptop: bool = False
    debian_version: str = "unknown"
    architecture: str = "amd64"


class DetectionEngine:
    """Probe the local system to build a SystemProfile."""

    def __init__(self, pkg_manager: PackageManager) -> None:
        self._pkg = pkg_manager

    def detect(self) -> SystemProfile:
        """Run all probes and return a complete SystemProfile."""
        profile = SystemProfile()
        profile.installed_package_names = [p.name for p in self._pkg.all_installed()]
        profile.desktop_environment = self._detect_desktop(set(profile.installed_package_names))
        profile.current_locale = self._detect_locale()
        profile.enabled_locales = self._detect_enabled_locales()
        profile.keyboard_layouts = self._detect_keyboards()
        profile.has_printer = self._has_packages(
            {"cups", "cups-daemon"}, set(profile.installed_package_names)
        )
        profile.has_bluetooth = self._has_packages(
            {"bluez", "bluetooth"}, set(profile.installed_package_names)
        )
        profile.has_modem = self._has_packages(
            {"modemmanager", "ppp"}, set(profile.installed_package_names)
        )
        profile.is_laptop = self._detect_laptop()
        profile.debian_version = self._detect_debian_version()
        profile.architecture = self._detect_architecture()
        return profile

    # ------------------------------------------------------------------
    # Individual probes
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_desktop(installed: set[str]) -> str:
        checks = [
            ({"xfce4", "xfwm4"}, "xfce"),
            ({"gnome-shell"}, "gnome"),
            ({"kde-plasma-desktop", "plasma-desktop"}, "kde"),
            ({"mate-desktop", "marco"}, "mate"),
            ({"cinnamon"}, "cinnamon"),
            ({"lxde", "openbox"}, "lxde"),
            ({"lxqt"}, "lxqt"),
            ({"budgie-desktop"}, "budgie"),
        ]
        for pkgs, de_name in checks:
            if pkgs & installed:
                return de_name
        return "unknown"

    @staticmethod
    def _detect_locale() -> str:
        lang = os.environ.get("LANG") or os.environ.get("LANGUAGE") or ""
        if lang:
            return lang.split(".")[0]
        try:
            result = subprocess.run(
                ["localectl", "status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.splitlines():
                if "LANG=" in line:
                    match = re.search(r"LANG=(\S+)", line)
                    if match:
                        return match.group(1).split(".")[0]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return "en_US"

    @staticmethod
    def _detect_enabled_locales() -> list[str]:
        path = Path("/etc/locale.gen")
        if not path.exists():
            return []
        locales: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                locales.append(line.split()[0])
        return locales

    @staticmethod
    def _detect_keyboards() -> list[str]:
        try:
            result = subprocess.run(
                ["localectl", "status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.splitlines():
                if "X11 Layout" in line or "VC Keymap" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        return [k.strip() for k in parts[1].split(",")]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return []

    @staticmethod
    def _has_packages(candidates: set[str], installed: set[str]) -> bool:
        return bool(candidates & installed)

    @staticmethod
    def _detect_laptop() -> bool:
        chassis_path = Path("/sys/class/dmi/id/chassis_type")
        if chassis_path.exists():
            try:
                chassis = int(chassis_path.read_text().strip())
                # 8=Portable, 9=Laptop, 10=Notebook, 14=Sub Notebook
                return chassis in {8, 9, 10, 14}
            except ValueError:
                pass
        return False

    @staticmethod
    def _detect_debian_version() -> str:
        path = Path("/etc/debian_version")
        if path.exists():
            return path.read_text().strip()
        return "unknown"

    @staticmethod
    def _detect_architecture() -> str:
        try:
            result = subprocess.run(
                ["dpkg", "--print-architecture"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return "amd64"
