# Development Guide

## Prerequisites

- Debian 13+ or Ubuntu 24.04+
- Python 3.13+
- `python3-venv`, `python3-pip`

## Setup

```bash
git clone https://github.com/apapamarkou/ddo.git
cd ddo
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Running Tests

```bash
# All backend unit tests (no display needed)
pytest -m "not gui"

# With coverage
pytest --cov=ddo --cov-report=term-missing -m "not gui"

# Specific file
pytest tests/unit/test_apt.py -v
```

## Code Quality

```bash
# Lint
ruff check src/ tests/

# Format
black src/ tests/

# Type check
mypy src/ddo/backend/ src/ddo/models/ src/ddo/utils/
```

## Running the GUI Locally

```bash
# Ensure PyQt6 is installed
pip install PyQt6
ddo-gui
```

## Project Structure

```
src/ddo/
├── backend/           ← Pure Python, no UI
│   ├── apt.py
│   ├── cleanup.py
│   ├── detection.py
│   ├── exceptions.py
│   ├── fonts.py
│   ├── inputmethods.py
│   ├── languages.py
│   ├── packages.py
│   ├── restore.py
│   └── services.py
├── models/
│   └── config.py
├── ui/
│   ├── cli/main.py
│   └── qt/
│       ├── app.py
│       ├── mainwindow.py
│       ├── wizard.py
│       ├── worker.py
│       └── tabs/
└── utils/
    ├── formatting.py
    └── logging_setup.py

data/languages/languages.yaml    ← Language package database
tests/
├── conftest.py
├── unit/
└── integration/
```

## Adding a New Language

Edit `data/languages/languages.yaml` and add a new entry:

```yaml
xx:
  name: My Language
  patterns:
    - "firefox-esr-l10n-xx"
    - "libreoffice-l10n-xx"
    - "aspell-xx"
    - "task-my-language-desktop"
```

No Python changes required.

## Adding a New Cleanup Category

Edit `_CATEGORY_REGISTRY` in `src/ddo/backend/cleanup.py`:

```python
"my_category": {
    "label": "My Category",
    "description": "Packages I want to offer for removal.",
    "patterns": ["my-pkg-*", "another-pkg"],
},
```

## Conventional Commits

Use the following prefixes:

- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `test:` test additions/changes
- `refactor:` code restructuring
- `chore:` build/CI/dependency updates
