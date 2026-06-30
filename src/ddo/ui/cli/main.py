"""CLI entry point for Debian Desktop Optimizer.

Commands:
    ddo analyze        - Analyse the system without making changes
    ddo cleanup        - Run the full cleanup wizard
    ddo dry-run        - Preview cleanup without removing anything
    ddo restore        - Reinstall packages from a rollback checkpoint
    ddo update         - Update and upgrade the system
    ddo list-languages - List detected language packages
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ddo.backend.apt import AptManager
from ddo.backend.cleanup import CleanupEngine, CleanupPlan
from ddo.backend.languages import LanguageManager
from ddo.backend.packages import PackageManager
from ddo.backend.restore import RestoreEngine
from ddo.models.config import AppConfig
from ddo.utils.formatting import format_bytes, format_package_count
from ddo.utils.logging_setup import setup_logging

app = typer.Typer(
    name="ddo",
    help="Debian Desktop Optimizer - Remove bloat, keep what matters.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()
err_console = Console(stderr=True, style="bold red")


def _build_stack(config: AppConfig) -> tuple[AptManager, PackageManager, LanguageManager]:
    """Construct the backend object graph."""
    progress_messages: list[str] = []

    def _cb(msg: str) -> None:
        progress_messages.append(msg)

    apt = AptManager(progress_callback=_cb)
    pkg = PackageManager(apt)
    db_path = Path(config.languages_db_path) if config.languages_db_path else None
    lang = LanguageManager(pkg, db_path=db_path)
    return apt, pkg, lang


# ---------------------------------------------------------------------------
# analyze command
# ---------------------------------------------------------------------------


@app.command()
def analyze(
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Path to config.yaml"),
    ] = None,
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Analyse the system and display what could be removed."""
    config = AppConfig.load(config_path)
    setup_logging(debug=config.debug, verbose=verbose)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        task = progress.add_task("Scanning installed packages...", total=None)
        apt, pkg, lang = _build_stack(config)
        progress.update(task, description="Detecting languages...")
        detected = lang.detect_installed()
        progress.update(task, description="Building cleanup plan...")
        engine = CleanupEngine(apt, pkg)
        lang_pkgs_by_code = {info.code: info.installed_packages for info in detected}
        categories = engine.build_categories(config.kept_languages, lang_pkgs_by_code)
        progress.update(task, description="Running simulation...")
        plan = engine.analyze(categories, language_packages=[], dry_run=True)
        progress.remove_task(task)

    console.print(
        Panel(
            f"[bold]Packages to remove:[/bold] {format_package_count(plan.total_packages)}\n"
            f"[bold]Space freed:[/bold]  {format_bytes(plan.total_size_bytes)}",
            title="[green]Analysis Complete[/green]",
            expand=False,
        )
    )

    table = Table(title="Removable Package Categories", box=box.ROUNDED, show_lines=True)
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Packages", justify="right", style="magenta")
    table.add_column("Size", justify="right", style="green")
    table.add_column("Description")

    for cat in plan.categories:
        if cat.packages_to_remove:
            table.add_row(
                cat.label,
                str(len(cat.packages_to_remove)),
                format_bytes(cat.total_size_kb * 1024),
                cat.description,
            )
    console.print(table)

    if plan.warnings:
        console.print("\n[yellow]Warnings:[/yellow]")
        for w in plan.warnings:
            console.print(f"  !  {w}")


# ---------------------------------------------------------------------------
# list-languages command
# ---------------------------------------------------------------------------


@app.command(name="list-languages")
def list_languages(
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Path to config.yaml"),
    ] = None,
    show_packages: bool = typer.Option(False, "--packages", "-p", help="Show package names"),
) -> None:
    """List all detected language packages on this system."""
    config = AppConfig.load(config_path)
    setup_logging(debug=config.debug)

    with Progress(
        SpinnerColumn(), TextColumn("{task.description}"), transient=True, console=console
    ) as p:
        t = p.add_task("Scanning packages...", total=None)
        _apt, _pkg, lang = _build_stack(config)
        detected = lang.detect_installed()
        p.remove_task(t)

    table = Table(
        title="Installed Language Packages",
        box=box.ROUNDED,
        show_lines=show_packages,
    )
    table.add_column("Code", style="cyan", width=8)
    table.add_column("Language", style="bold")
    table.add_column("Packages", justify="right", style="magenta")
    table.add_column("Size", justify="right", style="green")
    table.add_column("Kept?", justify="center")
    if show_packages:
        table.add_column("Package Names", style="dim")

    for info in sorted(detected, key=lambda x: x.name):
        kept = "+" if info.code in config.kept_languages else ""
        row = [
            info.code,
            info.name,
            str(len(info.installed_packages)),
            format_bytes(info.total_size_kb * 1024),
            f"[green]{kept}[/green]" if kept else "",
        ]
        if show_packages:
            tail = "..." if len(info.installed_packages) > 5 else ""
            row.append(", ".join(info.installed_packages[:5]) + tail)
        table.add_row(*row)

    console.print(table)


# ---------------------------------------------------------------------------
# dry-run command
# ---------------------------------------------------------------------------


@app.command(name="dry-run")
def dry_run(
    config_path: Annotated[
        Path | None,
        typer.Option("--config"),
    ] = None,
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Preview cleanup - show what would be removed without changing anything."""
    config = AppConfig.load(config_path)
    setup_logging(debug=config.debug, verbose=verbose)

    console.print("[bold yellow]DRY RUN MODE - no packages will be removed[/bold yellow]\n")

    with Progress(
        SpinnerColumn(), TextColumn("{task.description}"), transient=True, console=console
    ) as p:
        t = p.add_task("Scanning...", total=None)
        apt, pkg, lang = _build_stack(config)
        detected = lang.detect_installed()
        lang_pkgs_by_code = {i.code: i.installed_packages for i in detected}

        lang_to_remove: list[str] = [
            pkg_name
            for info in detected
            if info.code not in config.kept_languages
            for pkg_name in info.installed_packages
        ]

        engine = CleanupEngine(apt, pkg)
        categories = engine.build_categories(config.kept_languages, lang_pkgs_by_code)
        plan = engine.analyze(categories, lang_to_remove, dry_run=True)
        p.remove_task(t)

    _print_plan_summary(plan)


# ---------------------------------------------------------------------------
# cleanup command
# ---------------------------------------------------------------------------


@app.command()
def cleanup(
    config_path: Annotated[
        Path | None,
        typer.Option("--config"),
    ] = None,
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    dry_run_flag: bool = typer.Option(False, "--dry-run", help="Simulate only"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Remove bloatware based on your configuration."""
    config = AppConfig.load(config_path)
    setup_logging(debug=config.debug, verbose=verbose)

    console.print(
        Panel(
            "[bold]Debian Desktop Optimizer[/bold]\n"
            "This will remove packages NOT required for your selected languages.\n\n"
            f"Languages to keep: [cyan]{', '.join(config.kept_languages)}[/cyan]",
            title="Cleanup",
            expand=False,
        )
    )

    with Progress(
        SpinnerColumn(), TextColumn("{task.description}"), transient=True, console=console
    ) as p:
        t = p.add_task("Scanning...", total=None)
        apt, pkg, lang = _build_stack(config)
        detected = lang.detect_installed()
        lang_pkgs_by_code = {i.code: i.installed_packages for i in detected}

        lang_to_remove: list[str] = [
            pkg_name
            for info in detected
            if info.code not in config.kept_languages
            for pkg_name in info.installed_packages
        ]

        engine = CleanupEngine(apt, pkg)
        categories = engine.build_categories(config.kept_languages, lang_pkgs_by_code)
        plan = engine.analyze(categories, lang_to_remove, dry_run=True)
        p.remove_task(t)

    _print_plan_summary(plan)

    if plan.warnings:
        for w in plan.warnings:
            console.print(f"[yellow]!  {w}[/yellow]")

    if dry_run_flag:
        console.print("\n[yellow]Dry-run mode - no changes made.[/yellow]")
        return

    if not yes:
        typer.confirm("\nProceed with cleanup?", abort=True)

    restore = RestoreEngine(apt)
    all_pkgs = lang_to_remove[:]
    for cat in plan.categories:
        if cat.enabled:
            all_pkgs.extend(cat.packages_to_remove)
    restore.save_rollback(all_pkgs, description="Pre-cleanup snapshot")

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("Removing packages...", total=None)
        messages: list[str] = []

        def cb(msg: str) -> None:
            messages.append(msg)
            p.update(t, description=msg[:60])

        engine2 = CleanupEngine(apt, pkg, progress_callback=cb)
        engine2.execute(plan)
        p.remove_task(t)

    console.print("\n[bold green]Cleanup complete![/bold green]")

    if config.auto_update:
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
            t = p.add_task("Updating package database...", total=None)
            apt.update()
            p.update(t, description="Upgrading...")
            apt.upgrade()
            p.remove_task(t)
        console.print("[green]System updated.[/green]")


# ---------------------------------------------------------------------------
# restore command
# ---------------------------------------------------------------------------


@app.command()
def restore(
    config_path: Annotated[
        Path | None,
        typer.Option("--config"),
    ] = None,
    index: int = typer.Option(0, "--index", "-i", help="Rollback index (0 = newest)"),
    dry_run_flag: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Restore packages from a previous rollback checkpoint."""
    config = AppConfig.load(config_path)
    setup_logging(debug=config.debug)

    apt, _, _ = _build_stack(config)
    restore_engine = RestoreEngine(apt)
    entries = restore_engine.list_rollbacks()

    if not entries:
        console.print("[yellow]No rollback checkpoints found.[/yellow]")
        raise typer.Exit(1)

    table = Table(title="Available Rollbacks", box=box.ROUNDED)
    table.add_column("#", width=4)
    table.add_column("Timestamp", style="cyan")
    table.add_column("Packages", justify="right")
    table.add_column("Description")
    for i, e in enumerate(entries):
        table.add_row(str(i), e.timestamp, str(len(e.packages)), e.description)
    console.print(table)

    if index >= len(entries):
        err_console.print(f"Index {index} out of range (0-{len(entries) - 1})")
        raise typer.Exit(1)

    entry = entries[index]
    console.print(
        f"\nWill restore [bold]{len(entry.packages)}[/bold] package(s) "
        f"from [cyan]{entry.timestamp}[/cyan]"
    )

    if not dry_run_flag:
        typer.confirm("Proceed?", abort=True)

    restore_engine.restore(entry, dry_run=dry_run_flag)
    if dry_run_flag:
        console.print("[yellow]Dry-run - no changes made.[/yellow]")
    else:
        console.print("[bold green]Restore complete![/bold green]")


# ---------------------------------------------------------------------------
# update command
# ---------------------------------------------------------------------------


@app.command()
def update(
    config_path: Annotated[
        Path | None,
        typer.Option("--config"),
    ] = None,
) -> None:
    """Update the package database and upgrade all packages."""
    config = AppConfig.load(config_path)
    setup_logging(debug=config.debug)

    apt, _, _ = _build_stack(config)

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("Updating package database...", total=None)
        apt.update()
        p.update(t, description="Upgrading packages...")
        apt.upgrade()
        p.update(t, description="Removing orphans...")
        apt.autoremove()
        p.update(t, description="Cleaning cache...")
        apt.autoclean()
        p.remove_task(t)

    console.print("[bold green]System is up-to-date.[/bold green]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _print_plan_summary(plan: CleanupPlan) -> None:
    console.print(
        Panel(
            f"[bold]Total packages to remove:[/bold] {format_package_count(plan.total_packages)}\n"
            f"[bold]Estimated space freed:[/bold]  {format_bytes(plan.total_size_bytes)}",
            title="Cleanup Preview",
            expand=False,
        )
    )

    table = Table(box=box.SIMPLE_HEAD, show_lines=False)
    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right", style="magenta")
    table.add_column("Size", justify="right", style="green")
    for cat in plan.categories:
        if cat.packages_to_remove:
            table.add_row(
                cat.label,
                str(len(cat.packages_to_remove)),
                format_bytes(cat.total_size_kb * 1024),
            )
    console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
