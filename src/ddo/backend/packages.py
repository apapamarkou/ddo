"""Package filtering and grouping utilities."""

from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass, field

from ddo.backend.apt import AptManager, PackageInfo

logger = logging.getLogger(__name__)


@dataclass
class PackageGroup:
    """A named collection of packages sharing a logical purpose."""

    name: str
    description: str
    packages: list[str] = field(default_factory=list)
    total_size_kb: int = 0
    category: str = "misc"


class PackageManager:
    """Higher-level package querying built on top of AptManager."""

    def __init__(self, apt_manager: AptManager) -> None:
        self._apt = apt_manager
        self._cache: list[PackageInfo] | None = None

    def refresh(self) -> None:
        """Invalidate the internal package cache."""
        self._cache = None

    def all_installed(self) -> list[PackageInfo]:
        """Return cached list of all installed packages."""
        if self._cache is None:
            self._cache = self._apt.installed_packages()
        return self._cache

    def filter_by_pattern(self, pattern: str) -> list[PackageInfo]:
        """Return installed packages whose name matches a glob *pattern*."""
        return [pkg for pkg in self.all_installed() if fnmatch.fnmatch(pkg.name, pattern)]

    def filter_by_patterns(self, patterns: list[str]) -> list[str]:
        """Return unique package names matching any of the given glob patterns."""
        all_pkgs = {p.name for p in self.all_installed()}
        matched: set[str] = set()
        for pattern in patterns:
            for name in all_pkgs:
                if fnmatch.fnmatch(name, pattern):
                    matched.add(name)
        return sorted(matched)

    def group_by_prefix(self, prefix: str, category: str = "misc") -> PackageGroup:
        """Build a PackageGroup from all installed packages starting with *prefix*."""
        pkgs = self.filter_by_pattern(f"{prefix}*")
        names = [p.name for p in pkgs]
        total_kb = sum(p.installed_size_kb for p in pkgs)
        return PackageGroup(
            name=prefix,
            description=f"Packages matching {prefix}*",
            packages=names,
            total_size_kb=total_kb,
            category=category,
        )

    def calculate_group_size(self, packages: list[str]) -> int:
        """Return total installed-size in KB for a list of package names."""
        all_pkgs = {p.name: p for p in self.all_installed()}
        return sum(all_pkgs[n].installed_size_kb for n in packages if n in all_pkgs)

    def names_set(self) -> set[str]:
        """Return a set of all installed package names."""
        return {p.name for p in self.all_installed()}
