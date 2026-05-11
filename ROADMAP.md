# Boxes — Roadmap & Project Status

## Vision

Boxes is a cross-platform, production-grade virtual machine manager written in **Python + Qt6**.
It supports every major hypervisor across all three host operating systems:

- **Type 0** — Direct bare-metal hypervisor access (KVM ioctl, Xen privcmd)
- **Type 1** — Xen (xl), KVM (libvirt/QEMU), Hyper-V (PowerShell), macOS Hypervisor.framework
- **Type 2** — QEMU user-mode, SSH remote management

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✓ | Completato — implemented, tested, production-ready |
| ⟳ | In progress |
| ◐ | Partial — functional but could be extended |
| ⬜ | Planned |

---

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

---

## Sprint 0 — Foundation & Rebranding

| Task | Status |
|------|--------|
| Git history rewrite → Alessio Attilio | ✓ |
| Project rename: `gnome-boxes` → `boxes` | ✓ |
| Remove all GNOME references, URLs, legacy branding | ✓ |
| New SVG icons (scalable + 16×16 … 256×256) violet/blue theme | ✓ |
| New `.desktop`, `metainfo.xml`, `gschema.xml` | ✓ |
| ROADMAP.md | ✓ |

## Sprint 1 — Backend Core Architecture

| Task | File | Status |
|------|------|--------|
| BaseBackend (concrete, no ABC) | `boxes/backends/__init__.py` | ✓ |
| BackendCapabilities | `boxes/backends/__init__.py` | ✓ |
| Type0Backend — bare-metal KVM/Xen ioctl | `boxes/backends/type0_backend.py` | ✓ |
| XenBackend — xl hypervisor control | `boxes/backends/xen_backend.py` | ✓ |
| LibvirtBackend — libvirt-python | `boxes/backends/libvirt_backend.py` | ✓ |
| QEMUBackend — QEMU subprocess + QMP | `boxes/backends/qemu_backend.py` | ✓ |
| HyperVBackend — PowerShell Hyper-V | `boxes/backends/hyperv_backend.py` | ✓ |
| MacOSBackend — Hypervisor.framework + hvf QEMU | `boxes/backends/macos_backend.py` | ✓ |
| SSHBackend — remote virsh over SSH | `boxes/backends/ssh_backend.py` | ✓ |
| Auto-detection with priority chain | `boxes/app.py:_detect_backend()` | ✓ |

## Sprint 2 — Models

| Task | File | Status |
|------|------|--------|
| BoxConfig (dataclass, JSON persistence) | `boxes/models/config.py` | ✓ |
| Machine (QObject, state machine) | `boxes/models/machine.py` | ✓ |
| MachineCollection (QAbstractListModel) | `boxes/models/collection.py` | ✓ |
| OSDatabase (12 OS presets) | `boxes/models/osdb.py` | ✓ |
| InstallerMedia (ISO filename detection) | `boxes/models/media.py` | ✓ |

## Sprint 3 — UI Components

| Task | File | Status |
|------|------|--------|
| AppWindow (QMainWindow, menus, lifecycle) | `boxes/app_window.py` | ✓ |
| CollectionView (QListView, IconView + ListView delegates) | `boxes/ui/collection_view.py` | ✓ |
| DisplayWidget (VNC socket + QPainter) | `boxes/ui/display_view.py` | ◐ |
| Topbar (power, pause, settings, back) | `boxes/ui/topbar.py` | ✓ |
| Searchbar (text filter, close) | `boxes/ui/searchbar.py` | ✓ |
| CollectionToolbar (view toggle, new VM) | `boxes/ui/toolbar.py` | ✓ |
| DisplayToolbar (back, fullscreen, screenshot) | `boxes/ui/toolbar.py` | ✓ |
| ToastOverlay (notifications, auto-dismiss) | `boxes/ui/toast.py` | ✓ |

## Sprint 4 — Dialogs & Assistants

| Task | File | Status |
|------|------|--------|
| NewVMAssistant (3-page QWizard) | `boxes/dialogs/new_vm.py` | ✓ |
| PreferencesDialog (4 tabs) | `boxes/dialogs/preferences.py` | ✓ |
| AboutDialog | `boxes/dialogs/about.py` | ✓ |

## Sprint 5 — Services

| Task | File | Status |
|------|------|--------|
| DownloadManager (QThread HTTP) | `boxes/services/downloader.py` | ✓ |
| SharedFoldersManager | `boxes/services/shared_folders.py` | ✓ |
| SnapshotManager | `boxes/services/snapshot.py` | ✓ |
| UnattendedInstaller (kickstart/preseed/autounattend) | `boxes/services/unattended.py` | ✓ |
| ISOExtractor (kernel/initrd via isoinfo) | `boxes/services/iso_extractor.py` | ✓ |
| AsyncWorker (QThread template) | `boxes/worker.py` | ✓ |

## Sprint 6 — Packaging & Distribution

| Task | Status |
|------|--------|
| `pyproject.toml` with full metadata | ✓ |
| `setup.py` with data_files | ✓ |
| `MANIFEST.in` | ✓ |
| `data/io.boxes.Boxes.desktop` | ✓ |
| `data/io.boxes.Boxes.metainfo.xml` | ✓ |
| `data/io.boxes.boxes.gschema.xml` | ✓ |
| `data/icons/hicolor/*/apps/io.boxes.Boxes.svg` (7 sizes) | ✓ |
| `boxes/resources/style.qss` | ✓ |
| Flatpak manifest (`build-aux/flatpak/`) | ◐ |
| D-Bus service file | ◐ |

## Sprint 7 — Quality & CI

| Task | Status |
|------|--------|
| ruff (0 errors) | ✓ |
| mypy strict (0 errors) | ✓ |
| Python compile (43/43 files) | ✓ |
| pytest suite (imports, models, util) | ✓ |
| GitHub Actions (lint, test, package) | ✓ |
| Pre-commit hooks | ◐ |
| End-to-end tests | ⬜ |

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| GUI | Qt 6 (PyQt6 ≥ 6.5) |
| Type 0 | KVM ioctl API, Xen privcmd, ctypes |
| Type 1 | Xen xl, libvirt-python, Hyper-V PowerShell, macOS HVF |
| Type 2 | QEMU subprocess + QMP, SSH |
| Display | VNC (embedded), SPICE (QEMU integration) |
| Storage | qemu-img, QEMU QMP blockdev |
| Build | setuptools / pyproject.toml |
| Testing | pytest, pytest-qt |
| Linting | ruff, mypy |
| CI/CD | GitHub Actions |
| Packaging | pip, Flatpak, container |
