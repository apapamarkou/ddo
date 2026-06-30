# Architecture

## Overview

Debian Desktop Optimizer is structured in three layers:

```
┌─────────────────────────────────────────────────────┐
│                    User Interface                   │
│                                                     │
│   ┌─────────────────┐   ┌─────────────────────────┐ │
│   │   PyQt6 GUI     │   │     Typer + Rich CLI     │ │
│   │  (src/ddo/ui/qt)│   │  (src/ddo/ui/cli)        │ │
│   └────────┬────────┘   └───────────┬─────────────┘ │
└────────────┼───────────────────────┼───────────────┘
             │                       │
             ▼                       ▼
┌─────────────────────────────────────────────────────┐
│                   Backend Library                   │
│                                                     │
│  detection  languages  fonts  inputmethods          │
│  cleanup    restore    services  packages           │
│                                                     │
│         All under src/ddo/backend/                  │
└─────────────────────────────┬───────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────┐
│              System Layer (apt / dpkg)              │
│                  src/ddo/backend/apt.py             │
└─────────────────────────────────────────────────────┘
```

## Key Principles

1. **No UI code in backend** — `src/ddo/backend/` has zero Qt or Typer imports.
2. **No apt calls in UI** — the GUI/CLI only calls backend public methods.
3. **No hardcoded package names** — all patterns are in `data/languages/languages.yaml`
   and `_CATEGORY_REGISTRY` inside `cleanup.py` (configurable).
4. **Safety first** — every mutating operation runs `apt -s` simulation first.
5. **Rollback always** — `RestoreEngine` saves a JSON snapshot before every removal.

## Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `apt.py` | Raw subprocess wrapper around apt-get/dpkg-query |
| `packages.py` | Higher-level package querying and glob filtering |
| `languages.py` | Load YAML DB, detect installed languages, map locale |
| `fonts.py` | Group font packages by script/region |
| `inputmethods.py` | Group input method packages by framework |
| `detection.py` | System probe — DE, locale, keyboards, Debian version |
| `cleanup.py` | Build categories, analyse plan, execute removal |
| `restore.py` | Save/load/apply rollback JSON checkpoints |
| `services.py` | Query and toggle systemd services |
| `models/config.py` | Load/save `~/.config/ddo/config.yaml` |

## Threading Model

All long-running backend operations in the GUI run in a `BackendWorker`
(`QThread` subclass). The UI thread only calls `worker.start()` and handles
`progress`, `finished`, and `error` signals.
