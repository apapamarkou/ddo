# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2025-01-01

### Added
- First stable release
- PyQt6 GUI with first-run wizard and control panel
- Typer + Rich CLI with `analyze`, `cleanup`, `dry-run`, `restore`, `update`, `list-languages`
- YAML-driven language database (`data/languages/languages.yaml`)
- 16 configurable cleanup categories
- Full backend library shared between GUI and CLI
- `apt -s` simulation before every change
- JSON rollback/restore engine
- AppConfig persisted to `~/.config/ddo/config.yaml`
- Rotating log files at `~/.local/state/ddo/logs/ddo.log`
- Docker CI environment
- GitHub Actions CI/CD pipeline
- Debian packaging (`debian/control`, `rules`, desktop entry, man page)
- Bash completion
- Comprehensive unit and integration test suite
