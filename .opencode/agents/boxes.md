---
description: >
  Boxes hypervisor manager. Type-0 first (KVM ioctl/Xen hypercall), QEMU/libvirt
  fallback. CLI (argparse) + optional PyQt6 GUI. Flatpak distribution. 1C1F strict.
  Root-cause diagnostics. Zero external runtime deps. TAB indentation only.
  Use ONLY when working on the boxes project.
mode: primary
permission:
  edit: allow
  bash:
    'git *': allow
    'pytest *': allow
    'ruff *': allow
    'pip install *': allow
    '*': ask
---

# Boxes agent

## Project identity

**boxes** is a bare-metal hypervisor manager with CLI (argparse) and optional
PyQt6 GUI, root-cause diagnostics, and strict 1C1F architecture. Primary
backends are type-0 (KVM ioctl, Xen hypercall); QEMU+libvirt are fallback.
Flatpak is the primary distribution method.

The config file is `.opencode/opencode.json`.

## Architecture and conventions (must follow)

These rules are enforced for all Python code produced:

- **TAB indentation only**. Zero space indentation permitted anywhere.
  Every `.py` file must use TABs exclusively.
- **Zero external runtime dependencies**. All code uses Python stdlib only.
  PyQt6 and podman-py are optional via `[gui]` and `[container]` extras
  in `pyproject.toml` and must never be imported at the top level of a
  stdlib-only module.
- **Zero comments allowed**. No `#` comments, no block comments, no
  inline comments. Code must be self-documenting.
- **Zero bullet or numbered lists in docstrings or comments**. Since
  comments are banned this is trivially satisfied.
- **All `.md` files must be written as Word-style documents**: prose
  paragraphs, tables, code blocks only. No markdown bullet lists,
  numbered lists, or decorative elements (emojis, trees, separators).
  Style reference: `ROADMAP.md`.
- **1C1F strict**: one class per file, no exceptions. File name = snake_case
  of class name (e.g. `MachineState` -> `machine_state.py`).
- **No placeholders, no bare pass**: every method must have a real
  implementation. Empty bodies are rejected.
- **Type-0 first**: prioritise `KVMDevice`/`XenDevice` over QEMU/libvirt.
  The `detect_backend()` helper in `core.py` tries type-0, then xen, then
  libvirt, then qemu, then hyperv, then macos.
- **CLI core must remain; GUI is optional**. The argparse CLI
  (`boxes list|create|start|stop|pause|resume|delete|download|diagnose|info`)
  is always functional. PyQt6 GUI (`boxes --desktop`) adds polish.
- **Flatpak is primary distribution**. Manifest at `io.boxes.Boxes.yml`
  uses GNOME Platform 47 runtime. Bundles boxes via pip with `[gui]` extra.
  No Podman dependency for running the app.
- **Synchronous download utility** (`boxes/util.py:download_file` +
  `download_iso`). No Qt dependency for downloads.
- **Root-cause diagnostics**: `DiagnosticRecord` in `diagnostic_record.py`,
  `RootCause` + `get_root_cause()` in `diagnostics.py`. Every operation
  captures context, error info, and suggested resolution. All public
  methods in `core.py`, `cli.py`, and backends use `rc.diagnose()`.
- **All cache patterns in `.gitignore`**: `*cache*`, `*Cache*`,
  `__pycache__/`, `.mypy_cache/`, `.ruff_cache/`.
- **CI runs with stdlib only**: no system Qt dependencies, no mypy, no
  `ruff format`. Tests must pass with only Python stdlib installed.
- **commit messages must be single-line**: one line only, no body.

## File layout

**boxes/** root files:
- `__init__.py` - package metadata
- `__main__.py` - `python -m boxes` entry
- `app.py` - PyQt6 QApplication, main() dispatcher (cli_main/gui_main)
- `app_window.py` - QMainWindow
- `cli.py` - argparse commands
- `constants.py` - XDG paths, defaults
- `core.py` - BoxesCore, detect_backend()
- `diagnostic_record.py` - DiagnosticRecord
- `diagnostics.py` - RootCause, get_root_cause()
- `theme.py` - ThemeManager
- `theme_mode.py` - ThemeMode
- `util.py` - download_file, download_iso, detect_host_arch, check_* helpers
- `worker.py` - AsyncWorker (QThread compat stub)

**backends/** (hardware abstraction):
- `__init__.py` - exports BaseBackend, BackendCapabilities
- `base_backend.py` - abstract base class
- `backend_capabilities.py` - capability flags
- `type0/` - KVMDevice, XenDevice, XenBackend, Type0Backend
- `qemu/` - QEMUBackend, QEMUProcess
- `libvirt_backend.py` - LibvirtBackend
- `ssh/` - SSHBackend, SSHConfig
- `window/` - HyperVBackend, MacOSBackend
- Plus compat re-export stubs at flat level

**models/**:
- `machine.py` - Machine (re-exports MachineState)
- `machine_state.py` - MachineState enum
- `collection.py` - MachineCollection (QAbstractListModel)
- `config.py` - BoxConfig dataclass
- `media.py` - InstallerMedia
- `osdb.py` - OSDatabase

**services/** (25+ subdirectory modules):
- `download/` - DownloadManager, DownloadWorker
- `snapshot/` - Snapshot, SnapshotManager
- `shared/` - SharedFolder, SharedFoldersManager
- `install/` - UnattendedInstaller, ISOExtractor
- `container/` - PodmanManager
- `spice/` - SPICEChannel, SPICEDisplay, SPICEInput, SPICEClipboard, SPICEFileTransfer, SPICEVDAgent
- `vnc/` - VNCClient, VNCServer
- `usb/` - USBDevice, USBRedirection
- `template/` - TemplateManager
- `export/` - VMExporter, VMImporter
- `migration/` - MigrationManager
- `virgl/` - VirglRenderer
- `benchmark/` - BenchmarkRunner
- `error_reporting/` - SentryReporter
- `auth/` - AuthManager
- `firmware/` - FirmwareManager, OVMFManager
- `osinfo/` - LibosinfoWrapper
- `vdagent/` - VDAgentManager
- Plus compat re-export stubs at flat level

**dialogs/**:
- NewVMAssistant, SourcePage, ConfigPage, SummaryPage
- ResourcesTab, StorageTab, NetworkTab, DisplayTab
- PreferencesDialog, AboutDialog

**ui/**:
- CollectionView, IconViewDelegate, ListViewDelegate
- DisplayView (VNC/SPICE rendering)
- CollectionToolbar, DisplayToolbar
- ToastWidget, ToastOverlay
- Topbar, Searchbar

## Testing

- **87 tests** spread across `tests/`:
  - `test_imports.py` (8) - module import verification
  - `test_models.py` (18) - model unit tests
  - `test_util.py` (7) - utility function tests
  - `test_integration.py` (15) - core integration, diagnostics
  - `test_e2e.py` (39) - E2E tests across 7 classes (networking, CLI, edge, downloads)
- Always run `python -m pytest tests/ -q` after changes.
- Conditional download E2E: set `BOXES_SKIP_DOWNLOAD=1` to skip large ISO
  downloads in CI. On `push-to-master`, full Alpine ISO (~300 MB) is tested.
- CI uses stdlib-only test runs. No Qt headless, no mypy, no `ruff format`.
  `ruff check` still runs for lint but `ruff format` is excluded.

## CI and tooling

- `.github/workflows/ci.yml`: test and package jobs with stdlib-only Python.
  No system Qt or mypy. Lint uses `ruff check` only (no format step).
- `.pre-commit-config.yaml`: ruff (lint only, no format), mypy disabled,
  trailing-whitespace, end-of-file-fixer, check-yaml/toml,
  detect-private-key.
- `.gitignore` includes `*cache*`, `*Cache*`, `strip_comments.py`.
- `.cspell.json`: virtualization word list.
- `ROADMAP.md`: project life history document. Tracks all completed work
  (Sprint 1-7), infrastructure milestones, feature parity, future sprints
  (Sprint 8-12), proposals (P1/P2/P3), and dependency strategy.
  Written as Word-style document (prose, tables, code blocks — no bullet
  lists, numbered lists, emojis, or decorative elements).

## Key decisions

1. **Flatpak is primary distribution method**. Manifest at
   `io.boxes.Boxes.yml` using GNOME Platform 47. Bundles boxes and its
   optional PyQt6 GUI dep inside the sandbox. QEMU/KVM accessed via host
   filesystem bridges (`--filesystem=/dev/kvm`, `--filesystem=home`).
   Distribution relies entirely on **pip** (Python package, `dependencies
   = []`, stdlib-only) + **Flatpak** (GNOME runtime for system deps).
   No external services, no SaaS, no package manager URLs in code.
2. **`detect_backend()`** stays in `core.py` as module-level helper - not split.
3. **Backward-compat stubs**: when 1C1F splits a class out of a file, the
   original file becomes a re-export stub (`from X import Y as Y`), so
   existing `from old_module import Y` imports continue to work.
4. **`BaseBackend`** defines the interface. All 7 backends
   (type0, qemu, libvirt, xen, ssh, macos, hyperv) subclass it.
5. **`MachineState`** is used across 14+ files (all backends, core, models,
   ui, tests). Always import from `machine_state.py` in new code;
   backward compat via `machine.py` allows `from boxes.models.machine import
   MachineState`.
6. **Alpine ISO URL** for testing:
   `https://dl-cdn.alpinelinux.org/alpine/v3.21/releases/x86_64/alpine-standard-3.21.3-x86_64.iso`
7. **`boxes download`** subcommand uses sync `download_file()` from
   `boxes/util.py`. The Qt-dependent `DownloadWorker` (QThread) is in
   `download_worker.py` and used only when a GUI is present.
8. **Strict error handling**: all `BoxesCore` public methods,
   `detect_backend()` branches, and CLI command handlers wrap operations
   in `try/except` with `get_root_cause().diagnose()`. No bare `except:`
   blocks survive. Methods return `Optional[T]` or `tuple[bool, str]`
   on failure instead of letting exceptions propagate.
9. **CLI uses argparse**, not Click. Entry point is
   `boxes.app:main` which dispatches to `cli_main()` or `gui_main()`.
   The `--desktop` flag launches the PyQt6 GUI.
10. **Zero runtime dependencies**: core and CLI work with Python stdlib
    only. PyQt6 (`[gui]`) and podman-py (`[container]`) are optional extras.
    All PyQt6 imports are guarded by `try/except ImportError`.
    No external service references (no SaaS, no API URLs, no package
    manager curl/wget in code). All system CLIs detected at runtime via
    `shutil.which()` with graceful fallback.
11. **Commit messages are single-line**: one line only, no body paragraph.
