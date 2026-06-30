"""Unit tests for CleanupEngine."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from ddo.backend.cleanup import CleanupEngine
from ddo.backend.languages import LanguageManager
from ddo.backend.packages import PackageManager


class TestCleanupEngine:
    def test_build_categories_returns_list(
        self,
        mock_apt: object,
        pkg_manager: PackageManager,
        languages_db_path: Path,
    ) -> None:
        lang = LanguageManager(pkg_manager, db_path=languages_db_path)
        detected = lang.detect_installed()
        lang_pkgs_by_code = {i.code: i.installed_packages for i in detected}
        engine = CleanupEngine(mock_apt, pkg_manager)  # type: ignore[arg-type]
        categories = engine.build_categories(["en"], lang_pkgs_by_code)
        assert isinstance(categories, list)
        assert len(categories) > 0

    def test_build_categories_respects_kept_languages(
        self,
        mock_apt: object,
        pkg_manager: PackageManager,
        languages_db_path: Path,
    ) -> None:
        lang = LanguageManager(pkg_manager, db_path=languages_db_path)
        detected = lang.detect_installed()
        lang_pkgs_by_code = {i.code: i.installed_packages for i in detected}
        engine = CleanupEngine(mock_apt, pkg_manager)  # type: ignore[arg-type]

        # Keep German
        categories = engine.build_categories(["en", "de"], lang_pkgs_by_code)
        all_removal_pkgs = [p for c in categories for p in c.packages_to_remove]
        # German packages should NOT appear in the removal list
        german_pkgs = lang_pkgs_by_code.get("de", [])
        for german_pkg in german_pkgs:
            assert german_pkg not in all_removal_pkgs

    def test_analyze_dry_run(
        self,
        mock_apt: object,
        pkg_manager: PackageManager,
        languages_db_path: Path,
    ) -> None:
        lang = LanguageManager(pkg_manager, db_path=languages_db_path)
        detected = lang.detect_installed()
        lang_pkgs_by_code = {i.code: i.installed_packages for i in detected}
        engine = CleanupEngine(mock_apt, pkg_manager)  # type: ignore[arg-type]
        categories = engine.build_categories(["en"], lang_pkgs_by_code)
        plan = engine.analyze(categories, [], dry_run=True)
        assert plan.total_packages >= 0
        # Simulation should have been called
        mock_apt.simulate.assert_called()  # type: ignore[attr-defined]

    def test_execute_calls_purge(
        self,
        mock_apt: object,
        pkg_manager: PackageManager,
        languages_db_path: Path,
    ) -> None:
        from ddo.backend.cleanup import CleanupCategory, CleanupPlan

        plan = CleanupPlan(
            categories=[
                CleanupCategory(
                    key="games",
                    label="Games",
                    description="Games",
                    packages_to_remove=["gnome-chess", "gnome-sudoku"],
                    enabled=True,
                )
            ]
        )
        # Mark simulation as safe
        plan.simulation = MagicMock(is_safe=True, dangerous_packages=[])

        engine = CleanupEngine(mock_apt, pkg_manager)  # type: ignore[arg-type]
        engine.execute(plan)
        mock_apt.purge.assert_called()  # type: ignore[attr-defined]

    def test_execute_dry_run_does_not_call_purge(
        self,
        mock_apt: object,
        pkg_manager: PackageManager,
    ) -> None:
        from ddo.backend.cleanup import CleanupCategory, CleanupPlan

        plan = CleanupPlan(
            categories=[
                CleanupCategory(
                    key="games",
                    label="Games",
                    description="",
                    packages_to_remove=["gnome-chess"],
                    enabled=True,
                )
            ]
        )
        engine = CleanupEngine(mock_apt, pkg_manager)  # type: ignore[arg-type]
        engine.execute(plan, dry_run=True)
        mock_apt.purge.assert_not_called()  # type: ignore[attr-defined]
