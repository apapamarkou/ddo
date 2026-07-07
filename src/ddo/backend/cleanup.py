"""Cleanup categories and analysis engine.

Defines all removable package categories and provides the logic to
analyse, preview, and execute cleanup operations.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import cast

from ddo.backend.apt import AptManager, SimulationResult
from ddo.backend.exceptions import DangerousOperationError
from ddo.backend.packages import PackageManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default cleanup category definitions
# These define what can be removed.  No package names are hardcoded here;
# everything is expressed via glob patterns loaded from YAML or defined in
# the category registry below.
# ---------------------------------------------------------------------------

_CATEGORY_REGISTRY: dict[str, dict[str, object]] = {
    "bloatware": {
        "label": "Bloatware",
        "description": "Unwanted applications bundled with the default desktop install.",
        "patterns": [
            "xterm",
            "uxterm",
            "xbiff",
            "shotwell",
            "mlterm",
            "mlterm-common",
            "mlterm-tiny",
        ],
    },
    "games": {
        "label": "Games",
        "description": "Desktop games installed with GNOME/KDE/XFCE.",
        "patterns": [
            "gnome-2048",
            "five-or-more",
            "four-in-a-row",
            "gnome-chess",
            "gnome-klotski",
            "gnome-mahjongg",
            "gnome-mines",
            "gnome-nibbles",
            "gnome-robots",
            "gnome-sudoku",
            "gnome-taquin",
            "gnome-tetravex",
            "hitori",
            "lightsoff",
            "quadrapassel",
            "swell-foop",
            "tali",
        ],
    },
    "input_methods": {
        "label": "Input Methods",
        "description": "Asian and other complex input method frameworks.",
        "patterns": [
            "fcitx",
            "fcitx-bin",
            "fcitx-config-common",
            "fcitx-config-gtk",
            "fcitx-frontend-gtk2",
            "fcitx-frontend-gtk3",
            "fcitx-frontend-qt5",
            "fcitx-module-dbus",
            "fcitx-module-kimpanel",
            "fcitx-module-lua",
            "fcitx-module-x11",
            "fcitx-ui-classic",
            "fcitx5",
            "fcitx5-config-qt",
            "fcitx5-frontend-gtk3",
            "fcitx5-frontend-gtk4",
            "fcitx5-frontend-qt5",
            "fcitx5-module-dbus",
            "fcitx5-module-ibus",
            "fcitx5-module-kimpanel",
            "fcitx5-module-lua",
            "fcitx5-module-quickphrase",
            "fcitx5-module-wayland",
            "fcitx5-module-x11",
            "im-config",
            "mozc-server",
            "mozc-utils-gui",
            "uim",
            "uim-data",
            "uim-fep",
            "uim-gtk2.0",
            "uim-gtk2.0-immodule",
            "uim-gtk3",
            "uim-gtk3-immodule",
            "uim-mozc",
            "uim-plugins",
            "uim-qt5",
            "uim-qt5-immodule",
            "uim-xim",
            "anthy",
            "anthy-common",
            "kasumi",
            "ibus-hangul",
            "m17n-db",
            "mlterm",
            "mlterm-common",
            "mlterm-tiny",
        ],
    },
    "spellcheckers": {
        "label": "Spell Checkers",
        "description": "Language-specific spelling dictionaries.",
        "patterns": [
            "aspell-*",
            "hunspell-*",
            "myspell-*",
            "hyphen-*",
            "mythes-*",
            "ibrazilian",
            "ibulgarian",
            "icatalan",
            "idanish",
            "idutch",
            "ifrench-gut",
            "ihungarian",
            "iitalian",
            "ilithuanian",
            "inorwegian",
            "ipolish",
            "iportuguese",
            "irussian",
            "ispanish",
            "iswiss",
            "wbrazilian",
            "wbulgarian",
            "wcatalan",
            "wdanish",
            "wdutch",
            "wfrench",
            "witalian",
            "wngerman",
            "wnorwegian",
            "wpolish",
            "wportuguese",
            "wspanish",
            "wswedish",
        ],
    },
    "ocr_data": {
        "label": "OCR Data",
        "description": "Tesseract/Cuneiform OCR language data files.",
        "patterns": [
            "tesseract-ocr-*",
            "cuneiform*",
        ],
    },
    "speech": {
        "label": "Speech Synthesis",
        "description": "Text-to-speech engines and voice data.",
        "patterns": [
            "espeak-ng-data",
            "speech-dispatcher",
            "speech-dispatcher-audio-plugins",
            "speech-dispatcher-espeak-ng",
            "pocketsphinx",
            "festival",
            "festvox-kallpc16k",
        ],
    },
    "accessibility": {
        "label": "Accessibility (screen readers, Braille)",
        "description": "Screen readers and Braille display drivers.",
        "patterns": [
            "orca",
            "brltty",
            "xbrlapi",
            "florence",
        ],
    },
    "printing": {
        "label": "Printing Support",
        "description": "CUPS printing system and related tools.",
        "patterns": [
            "cups",
            "cups-browsed",
            "cups-bsd",
            "cups-client",
            "cups-common",
            "cups-core-drivers",
            "cups-daemon",
            "cups-filters",
            "cups-filters-core-drivers",
            "cups-ppdc",
            "cups-server-common",
            "system-config-printer",
            "system-config-printer-common",
            "system-config-printer-udev",
            "printer-driver-gutenprint",
            "foomatic-db",
            "foomatic-db-compressed-ppds",
            "hplip",
        ],
    },
    "bluetooth": {
        "label": "Bluetooth",
        "description": "Bluetooth stack and utilities.",
        "patterns": [
            "bluez",
            "bluetooth",
            "blueman",
        ],
    },
    "modem": {
        "label": "Modem / Mobile Broadband",
        "description": "ModemManager, PPP, and modem firmware.",
        "patterns": [
            "modemmanager",
            "ppp",
            "pppoe",
        ],
    },
    "server_packages": {
        "label": "Server Packages",
        "description": "Server daemons and infrastructure not needed on a desktop.",
        "patterns": [
            "apache2*",
            "nginx*",
            "postfix*",
            "sendmail*",
            "exim4*",
            "proftpd*",
            "vsftpd*",
            "samba",
            "samba-*",
        ],
    },
    "unused_docs": {
        "label": "Unused Documentation",
        "description": "Extra documentation packages.",
        "patterns": [
            "python3-doc",
            "linux-doc",
            "xorg-docs",
        ],
    },
}


@dataclass
class CleanupCategory:
    """A single cleanup category with its resolved package list."""

    key: str
    label: str
    description: str
    packages_to_remove: list[str] = field(default_factory=list)
    total_size_kb: int = 0
    enabled: bool = True


@dataclass
class CleanupPlan:
    """The result of analysing the system before cleanup."""

    categories: list[CleanupCategory] = field(default_factory=list)
    language_packages_to_remove: list[str] = field(default_factory=list)
    simulation: SimulationResult | None = None
    total_packages: int = 0
    total_size_bytes: int = 0
    warnings: list[str] = field(default_factory=list)


class CleanupEngine:
    """Analyse the system and execute cleanup operations.

    Parameters
    ----------
    apt_manager:
        The low-level apt abstraction.
    pkg_manager:
        Higher-level package query layer.
    progress_callback:
        Optional callable receiving progress messages.
    """

    def __init__(
        self,
        apt_manager: AptManager,
        pkg_manager: PackageManager,
        progress_callback: Callable[[str], None] | None = None,
    ) -> None:
        self._apt = apt_manager
        self._pkg = pkg_manager
        self._cb = progress_callback or (lambda _: None)

    def build_categories(
        self,
        kept_languages: list[str],
        language_packages_by_code: dict[str, list[str]],
    ) -> list[CleanupCategory]:
        """Build CleanupCategory objects from the registry.

        Parameters
        ----------
        kept_languages:
            Language codes that the user wants to KEEP.
        language_packages_by_code:
            Mapping from language code to list of associated packages.
        """
        # Collect all packages that must be protected (user's languages)
        protected: set[str] = set()
        for code in kept_languages:
            protected.update(language_packages_by_code.get(code, []))

        categories: list[CleanupCategory] = []
        for key, meta in _CATEGORY_REGISTRY.items():
            patterns: list[str] = cast(list[str], meta["patterns"])
            matched = self._pkg.filter_by_patterns(patterns)
            # Remove any packages the user wants to keep
            matched = [p for p in matched if p not in protected]
            if matched:
                total_kb = self._pkg.calculate_group_size(matched)
                categories.append(
                    CleanupCategory(
                        key=key,
                        label=str(meta["label"]),
                        description=str(meta["description"]),
                        packages_to_remove=matched,
                        total_size_kb=total_kb,
                        enabled=True,
                    )
                )
        return categories

    def analyze(
        self,
        categories: list[CleanupCategory],
        language_packages: list[str],
        *,
        dry_run: bool = True,
    ) -> CleanupPlan:
        """Analyse what would be removed and return a CleanupPlan.

        Parameters
        ----------
        categories:
            Category list as produced by ``build_categories``.
        language_packages:
            Extra language packages to remove.
        dry_run:
            If True, run ``apt -s`` simulation (safe).
        """
        plan = CleanupPlan()
        plan.categories = categories
        plan.language_packages_to_remove = language_packages

        all_to_remove: list[str] = list(language_packages)
        for cat in categories:
            if cat.enabled:
                all_to_remove.extend(cat.packages_to_remove)

        # Deduplicate while preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for p in all_to_remove:
            if p not in seen:
                seen.add(p)
                deduped.append(p)

        plan.total_packages = len(deduped)

        if dry_run and deduped:
            self._cb("Running apt simulation…")
            try:
                sim = self._apt.simulate(deduped)
                plan.simulation = sim
                plan.total_size_bytes = sim.space_freed_bytes
                plan.warnings.extend(sim.warnings)
            except Exception as exc:
                plan.warnings.append(f"Simulation error: {exc}")
        else:
            total_kb = sum(cat.total_size_kb for cat in categories)
            total_kb += self._pkg.calculate_group_size(language_packages)
            plan.total_size_bytes = total_kb * 1024

        return plan

    def execute(
        self,
        plan: CleanupPlan,
        *,
        dry_run: bool = False,
    ) -> None:
        """Execute the cleanup plan.

        Parameters
        ----------
        plan:
            The CleanupPlan from ``analyze()``.
        dry_run:
            If True, only simulate — do not actually remove anything.
        """
        if plan.simulation and not plan.simulation.is_safe:
            raise DangerousOperationError(
                "Aborting: simulation detected unsafe operations. "
                f"Dangerous packages: {plan.simulation.dangerous_packages}"
            )

        all_to_remove: list[str] = list(plan.language_packages_to_remove)
        for cat in plan.categories:
            if cat.enabled:
                all_to_remove.extend(cat.packages_to_remove)

        if not all_to_remove:
            logger.info("Nothing to remove")
            return

        if dry_run:
            self._cb(f"DRY RUN: would remove {len(all_to_remove)} packages")
            return

        self._cb(f"Removing {len(all_to_remove)} packages…")
        self._apt.purge(all_to_remove)

        self._cb("Running autoclean…")
        self._apt.autoclean()

        self._cb("Done.")
        logger.info("Cleanup complete: removed %d package(s)", len(all_to_remove))
