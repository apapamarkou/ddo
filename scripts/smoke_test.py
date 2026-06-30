#!/usr/bin/env python3
"""Smoke-test: import every backend module and print a summary.

Run without root — no packages are modified.

Usage:
    python3 scripts/smoke_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from the repo root without installing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ddo.backend.apt import AptManager
from ddo.backend.cleanup import CleanupEngine
from ddo.backend.detection import DetectionEngine
from ddo.backend.fonts import FontManager
from ddo.backend.inputmethods import InputMethodManager
from ddo.backend.languages import LanguageManager
from ddo.backend.packages import PackageManager
from ddo.backend.services import ServiceManager
from ddo.models.config import AppConfig
from ddo.utils.formatting import format_bytes


def main() -> None:
    print("=== Debian Desktop Optimizer — Smoke Test ===\n")

    config = AppConfig.load()
    print(f"Config loaded. Kept languages: {config.kept_languages}")

    apt = AptManager()
    pkg = PackageManager(apt)

    print("\n[1] Installed packages …")
    packages = pkg.all_installed()
    print(f"    Found {len(packages)} installed packages")

    db_path = Path(__file__).parent.parent / "data" / "languages" / "languages.yaml"
    lang = LanguageManager(pkg, db_path=db_path)

    print("\n[2] Language detection …")
    detected = lang.detect_installed()
    for info in detected[:5]:
        print(f"    {info.name} ({info.code}): {len(info.installed_packages)} pkgs, "
              f"{format_bytes(info.total_size_kb * 1024)}")
    if len(detected) > 5:
        print(f"    … and {len(detected) - 5} more")

    print("\n[3] Font groups …")
    fonts = FontManager(pkg)
    for group in fonts.detect_groups()[:3]:
        print(f"    {group.label}: {len(group.packages)} pkgs")

    print("\n[4] Input methods …")
    im = InputMethodManager(pkg)
    for group in im.detect_groups():
        print(f"    {group.label}: {len(group.packages)} pkgs")

    print("\n[5] System detection …")
    detector = DetectionEngine(pkg)
    profile = detector.detect()
    print(f"    Desktop: {profile.desktop_environment}")
    print(f"    Debian:  {profile.debian_version}")
    print(f"    Locale:  {profile.current_locale}")
    print(f"    Arch:    {profile.architecture}")

    print("\n[6] Cleanup analysis (dry-run, no changes) …")
    engine = CleanupEngine(apt, pkg)
    lang_pkgs_by_code = {i.code: i.installed_packages for i in detected}
    lang_to_remove = [
        p for i in detected
        if i.code not in config.kept_languages
        for p in i.installed_packages
    ]
    categories = engine.build_categories(config.kept_languages, lang_pkgs_by_code)
    plan = engine.analyze(categories, lang_to_remove, dry_run=False)
    print(f"    Categories: {len(plan.categories)}")
    print(f"    Packages to remove: {plan.total_packages}")
    print(f"    Estimated space: {format_bytes(plan.total_size_bytes)}")

    print("\n=== Smoke test passed ===")


if __name__ == "__main__":
    main()
