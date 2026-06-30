# Debian Desktop Optimizer

[![CI](https://github.com/apapamarkou/ddo/actions/workflows/ci.yml/badge.svg)](https://github.com/apapamarkou/ddo/actions)
[![License: GPL-3.0-only](https://img.shields.io/badge/License-GPL--3.0--only-blue.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-brightgreen.svg)](https://python.org)

Remove unnecessary language packs, fonts, input methods, games, and optional
desktop components from a freshly installed Debian system — while keeping the
languages you actually use.

---

## Features

- **First-run wizard** — guided setup that detects your locale and lets you choose what to keep
- **Control panel** — tab-based GUI for ongoing management (Languages, Components, Updates, Logs)
- **Full CLI** — `ddo analyze`, `ddo cleanup`, `ddo dry-run`, `ddo restore`, `ddo update`, `ddo list-languages`
- **Shared backend** — GUI and CLI use exactly the same backend library
- **Safety first** — `apt -s` simulation before every change; critical packages protected
- **Rollback / restore** — JSON snapshot saved before every operation
- **YAML-driven languages** — no hardcoded package names in Python
- **Supports** Debian 13 (Trixie) and future releases

---

## Installation

### From .deb (recommended)

```bash
sudo apt install ./debian-desktop-optimizer_1.0.0-1_all.deb
```

### From source

```bash
git clone https://github.com/apapamarkou/ddo.git
cd ddo
pip install -e ".[dev]"
```

---

## Quick Start

### GUI

```bash
ddo-gui
```

### CLI

```bash
# See what would be removed
ddo analyze

# Preview without removing anything
ddo dry-run

# Run cleanup (keeps languages from ~/.config/ddo/config.yaml)
sudo ddo cleanup

# See installed language packages
ddo list-languages --packages

# Restore a previous snapshot
sudo ddo restore
```

---

## Configuration

`~/.config/ddo/config.yaml`

```yaml
kept_languages:
  - en
  - fr
auto_update: true
theme: system
ignored_packages: []
```

---

## Running with Docker

```bash
cd docker
docker compose run ddo-ci
```

---

## Development

See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for the full developer guide.

```bash
pip install -e ".[dev]"
pytest
ruff check src/ tests/
mypy src/ddo/backend/
```

---

## License

GPL-3.0-only — see [LICENSE](LICENSE).
