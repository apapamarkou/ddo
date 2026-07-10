# Debian Desktop Optimizer v1.0.0

**First stable release.**

Debian Desktop Optimizer removes unnecessary language packs, fonts, input methods,
games, and optional desktop components from a freshly installed Debian system —
while keeping the languages you actually use, and never touching anything critical.

---

## Highlights

### First-run Wizard
A guided setup wizard launches on first run, detects your current locale, and walks
you through choosing which languages to keep and which optional components to remove.
Includes a classic watermark-style sidebar image and live analysis before any changes
are made.

### Control Panel
A tab-based GUI for ongoing management after the initial setup:

- **Overview** — system info at a glance: desktop environment, Debian version,
  architecture, locale, installed package count, disk usage, and how many packages
  can still be removed
- **Languages** — view and manage installed language packs; mark languages to keep
- **Components** — per-category removal of optional components; categories disappear
  once fully cleaned
- **Updates** — update & upgrade the system, or remove unused packages with a single click
- **Logs** — live log viewer, auto-refreshed when you switch to the tab
- **About** — version and project info

### Cleanup Categories
All categories are opt-in (unchecked by default):

| Category | Detection method |
|---|---|
| Games | Auto-detected via `dpkg Section: games` — catches everything, not just GNOME games |
| Input Methods | fcitx, fcitx5, uim, mozc, anthy, ibus-hangul, m17n-db |
| Spell Checkers | aspell, hunspell, myspell, hyphen, mythes dictionaries |
| OCR Data | tesseract-ocr-*, cuneiform |
| Speech Synthesis | espeak-ng-data, speech-dispatcher, festival |
| Accessibility | orca, brltty, xbrlapi, florence |
| Printing Support | CUPS stack, system-config-printer, hplip, foomatic |
| Bluetooth | bluez, bluetooth, blueman |
| Modem / Mobile Broadband | modemmanager, ppp, pppoe |
| Server Packages | apache2, nginx, postfix, exim4, samba, vsftpd, proftpd |
| Unused Documentation | python3-doc, linux-doc, xorg-docs |
| Bloatware | xterm, uxterm, xbiff, shotwell, mlterm |

### Safety
- `apt -s` simulation runs before every operation
- Critical system packages are protected by an explicit blocklist
- A JSON rollback snapshot is saved before every change
- `autoremove` runs after purge to clean up orphaned dependencies
- Privileged operations use `pkexec` — the app never requires running as root

### CLI
Full command-line interface for scripting and headless use:

```bash
ddo analyze          # show what would be removed
ddo dry-run          # simulate without removing
sudo ddo cleanup     # run cleanup
ddo list-languages   # list installed language packages
sudo ddo restore     # roll back the last operation
```

### Single Instance
Launching a second instance shows a warning and exits. Stale locks left by a
crashed session are automatically cleaned up.

---

## Installation

### From .deb (recommended)

Download `debian-desktop-optimizer_1.0.0-1_all.deb` from the assets below, then:

```bash
sudo apt install ./debian-desktop-optimizer_1.0.0-1_all.deb
```

### Requirements

- Debian 13 (Trixie) or later
- Python 3.13+
- PyQt6
- polkitd

### From source

```bash
git clone https://github.com/apapamarkou/ddo.git
cd ddo
pip install -e ".[dev]"
ddo-gui
```

---

## License

GPL-3.0-only — see [LICENSE](LICENSE).
