# Packaging Guide

## Building the .deb package

### Prerequisites

```bash
sudo apt install devscripts debhelper dh-python python3-all python3-setuptools fakeroot lintian
```

### Build from source tree

```bash
cd packaging
dpkg-buildpackage -us -uc -b
# The .deb will appear one level up
ls ../*.deb
```

### Install locally

```bash
sudo apt install ./debian-desktop-optimizer_1.0.0-1_all.deb
```

### Lint the package

```bash
lintian ../debian-desktop-optimizer_1.0.0-1_all.deb
```

## Installed file layout

| Path | Contents |
|------|----------|
| `/usr/bin/ddo` | CLI entry point |
| `/usr/bin/ddo-gui` | GUI entry point |
| `/usr/share/applications/ddo.desktop` | Desktop entry |
| `/usr/share/man/man1/ddo.1.gz` | Man page |
| `/usr/share/ddo/languages/languages.yaml` | Language database |
| `/usr/share/bash-completion/completions/ddo` | Bash completion |

## Building a wheel

```bash
pip install build
python -m build
ls dist/
```
