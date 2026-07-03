"""Low-level apt/dpkg abstraction layer.

This module provides a single AptManager class that wraps all interactions
with apt and dpkg.  No UI code is permitted here.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field

from ddo.backend.exceptions import (
    AptError,
    AptSimulationError,
    DangerousOperationError,
    PermissionError,
)

logger = logging.getLogger(__name__)

# Packages that must never be removed under any circumstances.
_CRITICAL_PACKAGES: frozenset[str] = frozenset(
    {
        "apt",
        "base-files",
        "base-passwd",
        "bash",
        "coreutils",
        "dash",
        "debconf",
        "debian-archive-keyring",
        "dpkg",
        "e2fsprogs",
        "findutils",
        "gcc-14-base",
        "gcc-13-base",
        "gcc-12-base",
        "grep",
        "gzip",
        "init",
        "init-system-helpers",
        "libpam-modules",
        "libpam-runtime",
        "libc6",
        "libc-bin",
        "libgcc-s1",
        "libstdc++6",
        "libapt-pkg7.0",
        "libapt-pkg6.0",
        "login",
        "mount",
        "passwd",
        "perl-base",
        "sed",
        "sensible-utils",
        "systemd",
        "systemd-sysv",
        "tar",
        "util-linux",
    }
)


@dataclass
class SimulationResult:
    """Result of an ``apt -s`` (simulate) run."""

    to_remove: list[str] = field(default_factory=list)
    to_install: list[str] = field(default_factory=list)
    space_freed_bytes: int = 0
    warnings: list[str] = field(default_factory=list)
    raw_output: str = ""
    is_safe: bool = True
    dangerous_packages: list[str] = field(default_factory=list)


@dataclass
class PackageInfo:
    """Metadata about a single installed package."""

    name: str
    version: str
    architecture: str
    installed_size_kb: int = 0
    description: str = ""
    section: str = ""
    is_automatic: bool = False


class AptManager:
    """Single abstraction over apt and dpkg operations.

    All public methods that mutate the system require root privileges.
    Use ``simulate()`` first to preview changes safely.
    """

    def __init__(
        self,
        apt_binary: str = "apt-get",
        dpkg_query_binary: str = "dpkg-query",
        dpkg_binary: str = "dpkg",
        env: dict[str, str] | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ) -> None:
        self._apt = apt_binary
        self._dpkg_query = dpkg_query_binary
        self._dpkg = dpkg_binary
        self._env: dict[str, str] = {
            "DEBIAN_FRONTEND": "noninteractive",
            "LANG": "C",
            "LC_ALL": "C",
            **(env or {}),
            **os.environ,
        }
        self._progress_callback = progress_callback or (lambda _: None)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _run(
        self,
        cmd: list[str],
        *,
        check: bool = True,
        capture: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        logger.debug("Running: %s", " ".join(cmd))
        self._progress_callback(" ".join(cmd))
        result = subprocess.run(
            cmd,
            env=self._env,
            capture_output=capture,
            text=True,
        )
        if check and result.returncode != 0:
            raise AptError(
                f"Command failed ({result.returncode}): {' '.join(cmd)}\n"
                f"stderr: {result.stderr}",
                returncode=result.returncode,
            )
        return result

    @staticmethod
    def _check_root() -> None:
        """No-op: privilege is handled per-command via pkexec."""

    def _privileged(self, cmd: list[str]) -> list[str]:
        """Prefix *cmd* with pkexec when not already running as root."""
        if os.geteuid() == 0:
            return cmd
        return ["pkexec", "--disable-internal-agent"] + cmd

    def _validate_packages(self, packages: list[str]) -> None:
        dangerous = [p for p in packages if p in _CRITICAL_PACKAGES]
        if dangerous:
            raise DangerousOperationError(
                f"Refusing to remove critical system packages: {dangerous}"
            )

    # ------------------------------------------------------------------
    # Read-only operations (no root required)
    # ------------------------------------------------------------------

    def installed_packages(self) -> list[PackageInfo]:
        """Return a list of all currently installed packages."""
        result = self._run(
            [
                self._dpkg_query,
                "-W",
                "--showformat=${Package}\t${Version}\t${Architecture}\t"
                "${Installed-Size}\t${Section}\t${db:Status-Abbrev}\n",
            ]
        )
        packages: list[PackageInfo] = []
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) < 6:
                continue
            name, version, arch, size_str, section, status = parts[:6]
            # Only include packages that are actually installed (ii, hi, etc.)
            if not status.strip().startswith("i"):
                continue
            try:
                size_kb = int(size_str)
            except ValueError:
                size_kb = 0
            packages.append(
                PackageInfo(
                    name=name,
                    version=version,
                    architecture=arch,
                    installed_size_kb=size_kb,
                    section=section,
                )
            )
        logger.debug("Found %d installed packages", len(packages))
        return packages

    def package_size(self, package_name: str) -> int:
        """Return installed size in KB for a single package, or 0 if unknown."""
        result = self._run(
            [
                self._dpkg_query,
                "-W",
                "--showformat=${Installed-Size}",
                package_name,
            ],
            check=False,
        )
        if result.returncode != 0:
            return 0
        try:
            return int(result.stdout.strip())
        except ValueError:
            return 0

    def is_installed(self, package_name: str) -> bool:
        """Return True if the package is currently installed."""
        result = self._run(
            [self._dpkg_query, "-W", "--showformat=${db:Status-Abbrev}", package_name],
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip().startswith("i")

    def packages_matching(self, pattern: str) -> list[str]:
        """Return installed package names that match a glob *pattern*.

        Uses ``dpkg-query`` with the glob directly.
        """
        result = self._run(
            [
                self._dpkg_query,
                "-W",
                "--showformat=${Package}\t${db:Status-Abbrev}\n",
                pattern,
            ],
            check=False,
        )
        if result.returncode != 0:
            return []
        names: list[str] = []
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) == 2 and parts[1].strip().startswith("i"):
                names.append(parts[0])
        return names

    # ------------------------------------------------------------------
    # Simulation (safe, no root needed)
    # ------------------------------------------------------------------

    def simulate(self, packages: list[str]) -> SimulationResult:
        """Simulate removal of *packages* without making any changes.

        Returns a ``SimulationResult`` with packages that would be
        removed, installed (replacements), disk freed, and warnings.
        """
        if not packages:
            return SimulationResult()

        cmd = [self._apt, "-s", "purge", *packages]
        result = self._run(cmd, check=False)
        output = result.stdout + result.stderr

        sim = SimulationResult(raw_output=output)

        if result.returncode != 0:
            sim.is_safe = False
            sim.warnings.append(f"apt simulation returned code {result.returncode}")
            raise AptSimulationError(
                f"Simulation failed:\n{output}",
                returncode=result.returncode,
            )

        # Parse "Remv foo [1.0]" lines
        remv_re = re.compile(r"^Remv (\S+)", re.MULTILINE)
        inst_re = re.compile(r"^Inst (\S+)", re.MULTILINE)

        sim.to_remove = remv_re.findall(output)
        sim.to_install = inst_re.findall(output)

        # Detect dangerous packages in removal list
        sim.dangerous_packages = [p for p in sim.to_remove if p in _CRITICAL_PACKAGES]
        if sim.dangerous_packages:
            sim.is_safe = False
            sim.warnings.append(f"Would remove critical packages: {sim.dangerous_packages}")

        # Calculate freed space
        total_kb = sum(self.package_size(p) for p in sim.to_remove)
        sim.space_freed_bytes = total_kb * 1024

        return sim

    # ------------------------------------------------------------------
    # Mutating operations (root required)
    # ------------------------------------------------------------------

    def update(self) -> None:
        """Run ``apt-get update``."""
        self._run(self._privileged([self._apt, "-y", "update"]))
        logger.info("Package database updated")

    def upgrade(self) -> None:
        """Run ``apt-get upgrade``."""
        result = self._run(
            self._privileged([
                self._apt, "-y",
                "-o", "Dpkg::Options::=--force-confdef",
                "-o", "Dpkg::Options::=--force-confold",
                "upgrade",
            ]),
            check=False,
        )
        if result.returncode != 0:
            logger.warning("apt-get upgrade exited %d: %s", result.returncode, result.stderr)
        logger.info("System upgraded")

    def autoremove(self) -> None:
        """Run ``apt-get autoremove --purge``."""
        self._run(self._privileged([self._apt, "-y", "--purge", "autoremove"]))
        logger.info("Autoremove complete")

    def autoclean(self) -> None:
        """Run ``apt-get autoclean``."""
        self._run(self._privileged([self._apt, "-y", "autoclean"]))
        logger.info("Autoclean complete")

    def purge(self, packages: list[str], *, force: bool = False) -> None:
        """Purge *packages* after safety checks.

        Pass ``force=True`` only in tests/mock environments.
        """
        if not packages:
            return
        if not force:
            self._validate_packages(packages)
            sim = self.simulate(packages)
            if not sim.is_safe:
                raise DangerousOperationError(
                    f"Aborting purge — simulation detected unsafe removals: "
                    f"{sim.dangerous_packages}"
                )
        self._run(self._privileged(
            [self._apt, "-y", "--purge", "remove", "--no-auto-remove", *packages]
        ))
        logger.info("Purged %d package(s)", len(packages))

    def install(self, packages: list[str]) -> None:
        """Install *packages*."""
        if not packages:
            return
        self._run(self._privileged([self._apt, "-y", "install", *packages]))
        logger.info("Installed %d package(s)", len(packages))
