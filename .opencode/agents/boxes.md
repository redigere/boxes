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

## Architecture & conventions (must follow)

- **1C1F strict**: one class per file, no exceptions. File name = snake_case
  of class name (e.g. `MachineState` → `machine_state.py`).
- **No placeholders, no bare `pass`**: every method must have a real
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

```
boxes/
├── __init__.py
├── __main__.py          # python -m boxes entry
├── app.py               # PyQt6 QApplication
├── app_window.py
├── cli.py               # Click commands
├── constants.py
├── core.py              # BoxesCore, detect_backend()
├── diagnostic_record.py # DiagnosticRecord
├── diagnostics.py       # RootCause, get_root_cause()
├── theme.py             # ThemeManager
├── theme_mode.py        # ThemeMode
├── util.py              # download_file, download_iso
├── backends/
│   ├── __init__.py      # re-exports BackendCapabilities, BaseBackend
│   ├── backend_capabilities.py
│   ├── base_backend.py
│   ├── type0_backend.py # Type0Backend
│   ├── kvm_device.py    # KVMDevice
│   ├── xen_device.py    # XenDevice
│   ├── qemu_backend.py  # QEMUBackend
│   ├── qemu_process.py  # QEMUProcess
│   ├── libvirt_backend.py
│   ├── ssh_backend.py   # SSHBackend
│   ├── ssh_config.py    # SSHConfig
│   ├── macos_backend.py
│   └── hyperv_backend.py
├── dialogs/
│   ├── __init__.py
│   ├── source_page.py
│   ├── config_page.py
│   ├── summary_page.py
│   ├── new_vm_assistant.py
│   ├── resources_tab.py
│   ├── storage_tab.py
│   ├── network_tab.py
│   ├── display_tab.py
│   └── preferences_dialog.py
├── models/
│   ├── __init__.py
│   ├── machine.py         # Machine (MachineState re-exported)
│   ├── machine_state.py   # MachineState
│   ├── collection.py
│   ├── config.py          # BoxConfig
│   ├── media.py           # InstallerMedia
│   └── osdb.py            # OSDatabase
├── services/
│   ├── __init__.py
│   ├── downloader.py      # DownloadManager (DownloadWorker re-exported)
│   ├── download_worker.py # DownloadWorker
│   ├── download_manager.py
│   ├── snapshot.py        # Snapshot
│   ├── snapshot_manager.py
│   ├── shared_folder.py
│   └── shared_folders_manager.py
└── ui/
    ├── __init__.py
    ├── collection_view.py  # CollectionView (delegates re-exported)
    ├── icon_view_delegate.py
    ├── list_view_delegate.py
    ├── toolbar.py          # re-exports both toolbars
    ├── toolbar_collection.py
    ├── toolbar_display.py
    ├── toast.py            # re-exports toast classes
    ├── toast_widget.py
    ├── toast_overlay.py
    ├── display_view.py
    └── topbar.py
```

## Testing

- **87 tests** spread across `tests/`:
  - `test_imports.py` — verifies every module imports clean
  - `test_models.py` — model unit tests
  - `test_integration.py` — integration tests (diagnostics, backends)
  - `test_e2e.py` — 35 E2E tests in 7 classes (networking, CLI, edge,
    downloads)
- Always run `python -m pytest tests/ -q` after changes.
- Conditional download E2E: set `BOXES_SKIP_DOWNLOAD=1` to skip large ISO
  downloads in CI. On `push-to-master`, full Alpine ISO (~300 MB) is tested.
- **ruff lint must pass**: `ruff check boxes/`.
- **87 tests must pass** before commit.

## CI & tooling

- `.github/workflows/ci.yml`: 4 jobs — lint (3.11/3.12/3.13), test, test-iso
  (master push only), package.
- `.pre-commit-config.yaml`: ruff (lint+format), mypy,
  trailing-whitespace, end-of-file-fixer, check-yaml/toml,
  detect-private-key.
- `.cspell.json`: virtualization word list.
- `ROADMAP.md`: 7 sprints, feature parity matrix with GNOME Boxes.

## Key decisions

1. **`detect_backend()`** stays in `core.py` as module-level helper — not split.
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
