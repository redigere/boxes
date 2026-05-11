# Boxes — Roadmap & Project Status

## Legend

| Symbol | Meaning |
|--------|---------|
| ✓ | Production-ready |
| ⟳ | In progress |
| ◐ | Partial |
| ⬜ | Planned |

## Backend Support Matrix

| Backend | Type | Linux | macOS | Windows | Status |
|---------|------|-------|-------|---------|--------|
| Type0Backend | 0 (bare-metal KVM) | ✓ | ⬜ | ⬜ | ✓ |
| Type0Backend | 0 (bare-metal Xen) | ✓ | ⬜ | ⬜ | ✓ |
| XenBackend | 1 | ✓ | ⬜ | ⬜ | ✓ |
| LibvirtBackend | 1 | ✓ | ✓ | ⬜ | ✓ |
| QEMUBackend | 2 | ✓ | ✓ | ✓ | ✓ |
| HyperVBackend | 1 | ⬜ | ⬜ | ✓ | ✓ |
| MacOSBackend | 1 | ⬜ | ✓ | ⬜ | ✓ |
| SSHBackend | remote | ✓ | ✓ | ✓ | ✓ |

## Architecture

```
boxes/
├── core.py           # Core logic (no Qt): backend, VM lifecycle, config
├── cli.py            # CLI entry: argparse subcommands
├── app.py            # GUI entry: QApplication + ThemeManager + Window
├── __main__.py       # Dispatcher → CLI or --desktop
├── theme.py          # Cross-platform Qt theme (auto light/dark)
├── backends/         # 7 backends, type0 → type2
├── models/           # BoxConfig, MachineState, OSDatabase, InstallerMedia
├── ui/               # Qt6 widgets (collection, display, toolbar, toast)
├── dialogs/          # New VM wizard, preferences, about
├── services/         # Download, snapshots, unattended install, ISO
└── resources/        # QSS template, icons
```

## Current Status

| Area | Status |
|------|--------|
| All 7 backends | ✓ |
| Backend auto-detection | ✓ |
| CLI (list, create, start, stop, pause, resume, delete, info) | ✓ |
| GUI (--desktop) | ✓ |
| Dual theme (light/dark auto-detect) | ✓ |
| VM creation wizard | ✓ |
| VNC/SPICE display | ◐ |
| Tests (36/36) | ✓ |
| ruff + mypy (0 errors) | ✓ |
| GitHub Actions CI | ✓ |

## Next Steps

- End-to-end integration tests
- Pre-commit hooks
- PyPI distribution
- SSH remote backend management
