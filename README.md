# Boxes

A cross-platform virtual machine manager built with Python + Qt6.

Supports **Type 0** (bare-metal KVM/Xen ioctl), **Type 1** (Xen, libvirt, Hyper-V, macOS HVF),
and **Type 2** (direct QEMU, SSH remote) hypervisors across Linux, macOS, and Windows.

## Features

- Create, start, stop, pause, resume, and delete virtual machines
- Multiple backend support with automatic detection:
  - **Type0Backend** — Direct KVM ioctl API and Xen privcmd (bare-metal, no libvirt needed)
  - **XenBackend** — Xen hypervisor via `xl`
  - **LibvirtBackend** — QEMU/KVM via libvirt-python
  - **QEMUBackend** — Direct QEMU subprocess with QMP control
  - **HyperVBackend** — Windows Hyper-V via PowerShell
  - **MacOSBackend** — macOS Hypervisor.framework with HVF acceleration
  - **SSHBackend** — Remote VM management via virsh over SSH
- VNC display (embedded client), SPICE integration
- VM creation wizard with OS detection
- Resource configuration (memory, vCPUs, disk)
- ISO download manager
- Unattended OS installation (kickstart, preseed, autounattend)
- Snapshot management
- Shared folders
- Cross-platform (Linux, macOS, Windows)

## Runtime Dependencies

- Python 3.11+
- PyQt6 ≥ 6.5
- qemu-img (for disk image creation)
- Platform-specific:
  - **Linux**: libvirt-python (optional), /dev/kvm or /proc/xen
  - **macOS**: Hypervisor.framework (built-in), QEMU with hvf
  - **Windows**: Hyper-V module (PowerShell)

## Quick Start

```bash
pip install -e .
boxes
```

## Development

```bash
pip install -e ".[dev]"
ruff check boxes/
mypy boxes/
pytest tests/
```

## Architecture

```
boxes/
├── app.py                    # QApplication singleton + backend auto-detection
├── app_window.py             # QMainWindow with full VM lifecycle
├── backends/
│   ├── __init__.py           # BaseBackend (concrete), BackendCapabilities
│   ├── type0_backend.py      # Bare-metal KVM/Xen (ioctl/privcmd)
│   ├── xen_backend.py        # Xen xl hypervisor
│   ├── libvirt_backend.py    # libvirt-python (KVM/QEMU)
│   ├── qemu_backend.py       # Direct QEMU subprocess + QMP
│   ├── hyperv_backend.py     # Windows Hyper-V PowerShell
│   ├── macos_backend.py      # macOS Hypervisor.framework + hvf QEMU
│   └── ssh_backend.py        # Remote virsh over SSH
├── models/
│   ├── config.py             # BoxConfig dataclass
│   ├── machine.py            # Machine QObject with state enum
│   ├── collection.py         # MachineCollection QAbstractListModel
│   ├── osdb.py               # OSDatabase (12 presets)
│   └── media.py              # InstallerMedia (ISO detection)
├── ui/
│   ├── collection_view.py    # Icon + List view delegates
│   ├── display_view.py       # VNC display widget
│   ├── topbar.py             # VM state controls
│   ├── searchbar.py          # Text filter
│   ├── toolbar.py            # Collection + Display toolbars
│   └── toast.py              # Notification overlay
├── dialogs/
│   ├── new_vm.py             # VM creation wizard
│   ├── preferences.py        # 4-tab preferences
│   └── about.py              # About dialog
├── services/
│   ├── downloader.py         # HTTP download manager
│   ├── shared_folders.py     # Shared folders manager
│   ├── snapshot.py           # Snapshot manager
│   ├── unattended.py         # Unattended install generators
│   └── iso_extractor.py      # Kernel/initrd extraction
├── constants.py              # Paths, limits, QEMU binary names
├── util.py                   # Detection utilities
└── worker.py                 # QThread worker template
```

## Backend Detection Priority

1. Type0Backend — if `/dev/kvm` or `/dev/xen/privcmd` available
2. XenBackend — if `xl` command + `/proc/xen` available
3. LibvirtBackend — if `virsh` + libvirt-python available
4. HyperVBackend — if PowerShell `Get-VM` available (Windows)
5. MacOSBackend — if `kern.hv_support` = 1 (macOS)
6. QEMUBackend — if any qemu-system binary found
7. SSHBackend — manual configuration for remote hosts

## License

LGPL-2.1+
