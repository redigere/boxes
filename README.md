# Boxes

A cross-platform virtual machine manager built with Python and Qt6.
Supports Type 0 (bare-metal KVM and Xen ioctl), Type 1 (Xen, libvirt,
Hyper-V, macOS HVF), and Type 2 (direct QEMU, SSH remote) hypervisors
across Linux, macOS, and Windows.

## Features

Create, start, stop, pause, resume, and delete virtual machines.
Multiple backend support with automatic detection in priority order:
Type0Backend using direct KVM ioctl API and Xen privcmd (bare-metal, no
libvirt needed), XenBackend via the xl hypervisor tool, LibvirtBackend
for QEMU and KVM via libvirt-python, QEMUBackend as direct QEMU
subprocess with QMP control, HyperVBackend for Windows Hyper-V via
PowerShell, MacOSBackend for macOS Hypervisor.framework with HVF
acceleration, and SSHBackend for remote VM management via virsh over
SSH. VNC display with embedded client and SPICE integration. VM
creation wizard with OS detection. Resource configuration for memory,
vCPUs, and disk. ISO download manager. Unattended OS installation
supporting kickstart, preseed, and autounattend. Snapshot management.
Shared folders. Cross-platform support for Linux, macOS, and Windows.

## Runtime Dependencies

Python 3.11 or later. PyQt6 6.5 or later for the GUI. qemu-img for
disk image creation. Platform-specific dependencies include Linux with
libvirt-python (optional) and access to /dev/kvm or /proc/xen, macOS
with built-in Hypervisor.framework and QEMU with hvf, and Windows with
Hyper-V module via PowerShell.

## Quick Start

```
pip install -e .
boxes
```

For the GUI interface, run:

```
boxes --desktop
```

## Development

```
pip install -e ".[dev]"
ruff check boxes/
pytest tests/
```

## Architecture

The project is organized into six top-level directories under boxes/.
The root contains package metadata, entry points, application controller,
CLI dispatcher, configuration, diagnostics, theme, and utilities.

The backends directory holds seven backend implementations across four
subdirectories. Type0Backend with KVMDevice and XenDevice provides
bare-metal hypervisor access. QEMUBackend with QEMUProcess handles
emulated VMs. LibvirtBackend manages libvirt-controlled domains.
SSHBackend enables remote host access. HyperVBackend and MacOSBackend
provide platform-native virtualization for Windows and macOS.

The models directory contains the MachineState enum, Machine QObject,
MachineCollection list model, BoxConfig dataclass, InstallerMedia for
ISO detection, and OSDatabase for OS presets.

The services directory contains twenty-five subdirectory modules
covering download management, snapshots, shared folders, install
helpers, container management, the SPICE protocol stack (channel,
display, input, clipboard, file transfer, vdagent), VNC client and
server, USB redirection, VM templates, export and import, live
migration, virgl 3D acceleration, benchmarking, error reporting, auth
management, firmware detection, OS information, and vdagent management.

The dialogs directory provides the NewVMAssistant wizard with source,
config, and summary pages, configuration tabs for resources, storage,
network, and display, plus preferences and about dialogs.

The ui directory implements the CollectionView with icon and list view
delegates, DisplayView for VNC and SPICE rendering, collection and
display toolbars, ToastWidget with ToastOverlay, Topbar, and Searchbar.

## Backend Detection Priority

The detect_backend function in core.py iterates through backends in a
fixed priority order. It first tries type0 when /dev/kvm or
/dev/xen/privcmd is available. It then tries Xen via the xl command.
Next it attempts libvirt when virsh and libvirt-python are present. On
Windows it tries Hyper-V via PowerShell. On macOS it checks the
kern.hv_support sysctl. It falls back to direct QEMU when any
qemu-system binary is found. SSH backend requires manual configuration
for remote hosts.

## License

LGPL-2.1+
