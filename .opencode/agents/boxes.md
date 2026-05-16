---
description: >
  Boxes hypervisor manager. Type-0 first (KVM ioctl/Xen hypercall), QEMU/libvirt
  fallback. PyQt6 GUI + Click CLI parity. 1C1F strict. Root-cause diagnostics.
  Alpine ISO download E2E. Use ONLY when the user is working on the boxes project.
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

**boxes** is a bare-metal hypervisor manager featuring CLI/GUI parity,
root-cause diagnostics, and a strict 1C1F (one class per file) architecture.
Primary backends are type-0 (KVM ioctl, Xen hypercall); QEMU+libvirt are
fallback.

The config file is `.opencode/opencode.json`.

## Architecture and conventions (must follow)

- **1C1F strict**: one class per file, no exceptions. File name = snake_case
  of class name (e.g. `MachineState` -> `machine_state.py`).
- **No placeholders, no bare pass**: every method must have a real
  implementation. Empty bodies are rejected.
- **Type-0 first**: prioritise `KVMDevice`/`XenDevice` over QEMU/libvirt.
  The `detect_backend()` helper in `core.py` tries type-0, then qemu, then
  libvirt, then ssh.
- **CLI core must remain; GUI must match/exceed GNOME Boxes UX**.
  The Click CLI (`boxes list|start|stop|diagnose|download`) is always
  functional. PyQt6 GUI adds polish where appropriate.
- **Synchronous download utility** (`boxes/util.py:download_file` +
  `download_iso`). No Qt dependency for downloads.
- **Root-cause diagnostics**: `DiagnosticRecord` in `diagnostic_record.py`,
  `RootCause` + `get_root_cause()` in `diagnostics.py`. Every operation
  captures context, error info, and suggested resolution.

## File layout

**boxes/** root files:
- `__init__.py` - package metadata
- `__main__.py` - `python -m boxes` entry
- `app.py` - PyQt6 QApplication
- `app_window.py` - QMainWindow
- `cli.py` - Click commands
- `constants.py` - XDG paths, defaults
- `core.py` - BoxesCore, detect_backend()
- `diagnostic_record.py` - DiagnosticRecord
- `diagnostics.py` - RootCause, get_root_cause()
- `theme.py` - ThemeManager
- `theme_mode.py` - ThemeMode
- `util.py` - download_file, download_iso
- `worker.py` - AsyncWorker (QThread)

**backends/** (hardware abstraction):
- `__init__.py` - exports BaseBackend, BackendCapabilities
- `base_backend.py` - abstract base class
- `backend_capabilities.py` - capability flags
- `type0/` - KVMDevice, XenDevice, XenBackend, Type0Backend
- `qemu/` - QEMUBackend, QEMUProcess
- `libvirt_backend.py` - LibvirtBackend
- `ssh/` - SSHBackend, SSHConfig
- `windows/` - HyperVBackend, MacOSBackend
- Plus compat re-export stubs at flat level

**models/**:
- `machine.py` - Machine (QObject)
- `machine_state.py` - MachineState enum
- `collection.py` - MachineCollection (QAbstractListModel)
- `config.py` - BoxConfig dataclass
- `media.py` - InstallerMedia
- `osdb.py` - OSDatabase

**services/** (87+ files, 25+ subdirectory modules):
- `download/` - DownloadManager, DownloadWorker
- `snapshot/` - Snapshot, SnapshotManager
- `shared/` - SharedFolder, SharedFoldersManager
- `install/` - UnattendedInstaller, ISOExtractor
- `container/` - PodmanManager
- `spice/` - SPICEChannel, SPICEDisplay, SPICEInput, SPICEClipboard, SPICEFileTransfer, SPICEVDAgent
- `vnc/` - VNCClient, VNCServer
- `usb/` - USBDevice, USBRedirection
- `template/` - TemplateManager, VMTemplate
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
- NewVMAssistant (QWizard), SourcePage, ConfigPage, SummaryPage
- ResourcesTab, StorageTab, NetworkTab, DisplayTab
- PreferencesDialog, AboutDialog

**ui/**:
- CollectionView, IconViewDelegate, ListViewDelegate
- DisplayWidget (VNC/SPICE rendering)
- CollectionToolbar, DisplayToolbar
- ToastWidget, ToastOverlay
- Topbar, Searchbar

## Testing

- **87 tests** spread across `tests/`:
  - `test_imports.py` - module import verification
  - `test_models.py` - model unit tests
  - `test_integration.py` - core integration, diagnostics
  - `test_e2e.py` - 39 E2E tests in 7 classes
- Always run `python -m pytest tests/ -q` after changes.
- Conditional download E2E: set `BOXES_SKIP_DOWNLOAD=1` to skip large ISO
  downloads in CI. On `push-to-master`, full Alpine ISO (~300 MB) is tested.
- **ruff lint must pass**: `ruff check boxes/`.

## CI and tooling

- `.github/workflows/ci.yml`: 4 jobs - lint (3.11/3.12/3.13), test, test-iso
  (master push only), package.
- `.pre-commit-config.yaml`: ruff (lint+format), mypy,
  trailing-whitespace, end-of-file-fixer, check-yaml/toml,
  detect-private-key.
- `.cspell.json`: virtualization word list.
- `ROADMAP.md`: 7 sprints, feature parity matrix with GNOME Boxes.

## Key decisions

1. **`detect_backend()`** stays in `core.py` as module-level helper - not split.
2. **Backward-compat stubs**: when 1C1F splits a class out of a file, the
   original file becomes a re-export stub (`from X import Y as Y`), so
   existing `from old_module import Y` imports continue to work.
3. **`BaseBackend`** defines the interface. All 7 backends
   (type0, qemu, libvirt, xen, ssh, macos, hyperv) subclass it.
4. **`MachineState`** is used across 14+ files (all backends, core, models,
   ui, tests). Always import from `machine_state.py` in new code;
   backward compat via `machine.py` allows `from boxes.models.machine import
   MachineState`.
5. **Alpine ISO URL** for testing:
   `https://dl-cdn.alpinelinux.org/alpine/v3.21/releases/x86_64/alpine-standard-3.21.3-x86_64.iso`
6. **`boxes download`** subcommand uses sync `download_file()` from
   `boxes/util.py`. The Qt-dependent `DownloadWorker` (QThread) is in
   `download_worker.py` and used only when a GUI is present.
7. **Sprint 1 next**: type-0 VM lifecycle on bare metal (start/shutdown/pause
   via KVM ioctl or `xl` commands without QEMU).
