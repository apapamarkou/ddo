"""Integration tests — full backend pipeline with mocked apt."""

from __future__ import annotations

from pathlib import Path

from ddo.backend.apt import AptManager
from ddo.backend.cleanup import CleanupEngine
from ddo.backend.languages import LanguageManager
from ddo.backend.packages import PackageManager
from ddo.backend.restore import RestoreEngine
from ddo.models.config import AppConfig


class TestFullPipeline:
    """Full backend flow: detect → categorise → analyse → execute → restore."""

    def test_full_cleanup_pipeline(
        self,
        mock_apt: AptManager,
        pkg_manager: PackageManager,
        languages_db_path: Path,
        tmp_path: Path,
    ) -> None:
        config = AppConfig(kept_languages=["en"])

        # 1. Detect languages
        lang = LanguageManager(pkg_manager, db_path=languages_db_path)
        detected = lang.detect_installed()
        assert detected, "Must detect at least one language"
        lang_pkgs_by_code = {i.code: i.installed_packages for i in detected}

        # 2. Build language removal list
        lang_to_remove = [
            p
            for info in detected
            if info.code not in config.kept_languages
            for p in info.installed_packages
        ]

        # 3. Build cleanup plan
        engine = CleanupEngine(mock_apt, pkg_manager)
        categories = engine.build_categories(config.kept_languages, lang_pkgs_by_code)
        plan = engine.analyze(categories, lang_to_remove, dry_run=True)

        assert plan.total_packages >= 0
        assert plan.simulation is not None

        # 4. Save rollback
        restore = RestoreEngine(mock_apt, rollback_dir=tmp_path)
        all_pkgs = list(lang_to_remove)
        for cat in categories:
            all_pkgs.extend(cat.packages_to_remove)
        entry = restore.save_rollback(all_pkgs, "integration test")
        assert entry.packages

        # 5. Execute
        engine.execute(plan)
        mock_apt.purge.assert_called()

        # 6. Restore
        entries = restore.list_rollbacks()
        assert entries
        restore.restore(entries[0])
        mock_apt.install.assert_called()

    def test_kept_language_packages_not_removed(
        self,
        mock_apt: AptManager,
        pkg_manager: PackageManager,
        languages_db_path: Path,
    ) -> None:
        lang = LanguageManager(pkg_manager, db_path=languages_db_path)
        detected = lang.detect_installed()
        lang_pkgs_by_code = {i.code: i.installed_packages for i in detected}

        # Keep French
        engine = CleanupEngine(mock_apt, pkg_manager)
        categories = engine.build_categories(["en", "fr"], lang_pkgs_by_code)
        all_removal = [p for c in categories for p in c.packages_to_remove]

        french_pkgs = lang_pkgs_by_code.get("fr", [])
        for pkg in french_pkgs:
            assert pkg not in all_removal, f"French package {pkg} should be kept"
