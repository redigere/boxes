# Boxes — Type-0 Hypervisor Manager — ROADMAP

## Differentiator: Type-0 First, CLI Core, Full Module Tree

GNOME Boxes (virt-manager-based, type 2) relies on QEMU + libvirt for every
operation. **boxes** inverts the stack: primary backends are **type 0** (bare-metal
KVM ioctl, bare-metal Xen hypercall) — no emulator process, no libvirt daemon
required. QEMU/libvirt/QEMUProcess are only a fallback.

Every external dependency is wrapped in a Python module under `boxes/services/`
or `boxes/backends/`.

| Feature | GNOME Boxes | boxes (this project) |
|---------|-------------|----------------------|
| Primary backend | QEMU + libvirt (type 2/1) | KVM ioctl / Xen hypercall (type 0) |
| CLI core | No (GUI-only) | Yes — full CLI parity |
| ISO auto-download | Yes | Yes (boxes download) |
| SPICE display | Yes | Yes (services/spice/, services/vdagent/) |
| Shared clipboard | Yes (spice-vdagent) | Yes (services/spice/spice_clipboard.py) |
| Drag and drop files | Yes | Yes (services/spice/spice_file_transfer.py) |
| Shared folders | Yes (SPICE webdav) | Yes (services/shared/) |
| USB redirection | Yes | Yes (services/usb/) |
| Snapshots | Yes (libvirt) | Yes (services/snapshot/) |
| Express install | Yes (libosinfo) | Yes (services/osinfo/, services/install/) |
| UEFI / Secure Boot | Yes | Yes (services/firmware/) |
| 3D acceleration (virgl) | Yes | Yes (services/virgl/) |
| Auto-resize display | Yes | Yes (services/spice/spice_display.py) |
| Remote SSH backend | No (GNOME Connections split) | Yes (backends/ssh/) |
| VM export/import | Yes | Yes (services/export/) |
| Live migration | Yes | Yes (services/migration/) |
| Templates | Yes | Yes (services/template/) |
| Benchmarks | No | Yes (services/benchmark/) |
| Error reporting | No | Yes (services/error_reporting/) |
| Auth/credentials | Yes | Yes (services/auth/) |
| Container fallback (Podman) | No | Yes (services/container/) |

---

## Complete Module Dependency Tree

Every external system dependency is wrapped in a dedicated Python module.

### Backends (hardware/hypervisor abstraction)

| Module | Classes | Wraps |
|--------|---------|-------|
| backends/type0/kvm_device.py | KVMDevice | Linux KVM ioctl (/dev/kvm) |
| backends/type0/xen_device.py | XenDevice | Xen privcmd/evtchn/gnttab (/dev/xen/) |
| backends/type0/xen_backend.py | XenBackend | xl CLI tool (xen toolstack) |
| backends/type0/type0_backend.py | Type0Backend | KVM + Xen + qemu-img + Podman composite |
| backends/qemu/qemu_process.py | QEMUProcess | qemu-system-* binary, QMP socket |
| backends/qemu/qemu_backend.py | QEMUBackend | QEMU subprocess lifecycle |
| backends/libvirt_backend.py | LibvirtBackend | libvirt Python module + virsh |
| backends/ssh/ssh_backend.py | SSHBackend | ssh CLI to remote virsh |
| backends/ssh/ssh_config.py | SSHConfig | SSH connection parameters |
| backends/window/hyperv_backend.py | HyperVBackend | PowerShell Hyper-V module |
| backends/window/macos_backend.py | MacOSBackend | macOS Hypervisor.framework + QEMU |

### Core Services

| Module | Classes | Wraps |
|--------|---------|-------|
| services/container/podman_manager.py | PodmanManager | podman CLI (QEMU in container) |
| services/spice/spice_channel.py | SPICEChannel | SPICE TCP protocol (port 5900) |
| services/spice/spice_display.py | SPICEDisplay | SPICE framebuffer/compression |
| services/spice/spice_input.py | SPICEInput | SPICE keyboard/mouse input |
| services/spice/spice_clipboard.py | SPICEClipboard | SPICE clipboard sync |
| services/spice/spice_file_transfer.py | SPICEFileTransfer | SPICE drag-and-drop files |
| services/spice/spice_vdagent.py | SPICEVDAgent | spice-vdagent install/detect |
| services/vnc/vnc_client.py | VNCClient | VNC/RFB client protocol |
| services/vnc/vnc_server.py | VNCServer | Minimal VNC server |
| services/usb/usb_device.py | USBDevice | lsusb, /sys/bus/usb/ |
| services/usb/usb_redirection.py | USBRedirection | SPICE usbredir, libvirt hostdev |
| services/template/template_manager.py | TemplateManager, VMTemplate | JSON template storage |
| services/export/vm_exporter.py | VMExporter | tar.gz export |
| services/export/vm_importer.py | VMImporter | tar.gz import |
| services/migration/migration_manager.py | MigrationManager | xl migrate, QMP migrate |
| services/virgl/virgl_renderer.py | VirglRenderer | libvirglrenderer.so, QEMU GL |
| services/benchmark/benchmark_runner.py | BenchmarkRunner | dd, iperf3, mbw |
| services/error_reporting/sentry_reporter.py | SentryReporter | Sentry SDK, file fallback |
| services/auth/auth_manager.py | AuthManager | SASL, SSH keys, credential store |
| services/firmware/firmware_manager.py | FirmwareManager | OVMF/SeaBIOS blob detection |
| services/firmware/ovmf_manager.py | OVMFManager | UEFI/Secure Boot/SBAT |
| services/osinfo/libosinfo_wrapper.py | LibosinfoWrapper | osinfo-query, osinfo-detect |
| services/vdagent/vdagent_manager.py | VDAgentManager | SPICE vdagentd socket |
| services/install/unattended.py | UnattendedInstaller | Kickstart/preseed/autounattend |
| services/install/iso_extractor.py | ISOExtractor | isoinfo for kernel/initrd |
| services/download/download_worker.py | DownloadWorker | urllib threaded download |
| services/download/downloader.py | DownloadManager | GUI download management |
| services/snapshot/snapshot.py | Snapshot | Snapshot dataclass |
| services/snapshot/snapshot_manager.py | SnapshotManager | Snapshot index + overlay chains |
| services/shared/shared_folder.py | SharedFolder | Folder dataclass |
| services/shared/shared_folders_manager.py | SharedFoldersManager | JSON folder config |
| worker.py | AsyncWorker | PyQt6 QThread worker |

### Models

| Module | Classes | Purpose |
|--------|---------|---------|
| models/machine_state.py | MachineState | VM state enum (STOPPED=0..CRASHED=4) |
| models/machine.py | Machine | QObject VM with signals |
| models/config.py | BoxConfig | JSON-persisted VM configuration |
| models/collection.py | MachineCollection | QAbstractListModel for GUI |
| models/media.py | InstallerMedia | ISO file OS detection |
| models/osdb.py | OSDatabase | Built-in OS presets |

### Diagnostic Infrastructure

| Module | Classes | Purpose |
|--------|---------|---------|
| diagnostic_record.py | DiagnosticRecord | Dataclass for one diagnostic event |
| diagnostics.py | RootCause, get_root_cause() | Root cause analysis chain |
| services/error_reporting/sentry_reporter.py | SentryReporter | Error report persistence |

---

## Sprint 1 — Type-0 VM Lifecycle (COMPLETE)

Goal: Type-0 backend (KVM + Xen) can create, run, stop, pause, resume VMs
natively without QEMU or libvirt.

| # | Task | Status | Module |
|---|------|--------|--------|
| 1.1 | KVMDevice: ioctl interface | Done | backends/type0/kvm_device.py |
| 1.2 | KVMDevice: memory regions + virtio | Done | backends/type0/kvm_device.py |
| 1.3 | KVMDevice: SMP vCPU threads | Done | backends/type0/kvm_device.py |
| 1.4 | KVMDevice: IRQFD/IOEVENTFD | Done | backends/type0/kvm_device.py |
| 1.5 | XenDevice: privcmd hypercall | Done | backends/type0/xen_device.py |
| 1.6 | XenDevice: evtchn + gnttab | Done | backends/type0/xen_device.py |
| 1.7 | Type0Backend: boot firmware | Done | backends/type0/type0_backend.py |
| 1.8 | Type0Backend: virtio-block mmap | Done | backends/type0/type0_backend.py |
| 1.9 | CLI: boxes run | Done | cli.py |
| 1.10 | CLI: boxes console | Done | cli.py |

### Acceptance — ALL PASS
- boxes create --name foo --memory 512 --vcpus 1 --disk 5 + boxes start foo boots under pure KVM ioctl (no QEMU process)
- boxes stop foo, boxes pause foo, boxes resume foo all succeed
- Xen PV domain create/destroy works via privcmd

---

## Sprint 2 — SPICE Display and Input (COMPLETE)

Goal: Full SPICE protocol support for display, input, clipboard, and
drag-and-drop — matching GNOME Boxes experience.

| # | Task | Status | Module |
|---|------|--------|--------|
| 2.1 | SPICE protocol handshake | Done | services/spice/spice_channel.py |
| 2.2 | SPICE: image compression (quic/lz/glz) | Done | services/spice/spice_display.py |
| 2.3 | SPICE: input channel (keyboard + mouse) | Done | services/spice/spice_input.py |
| 2.4 | SPICE: cursor channel | Done | services/spice/spice_input.py |
| 2.5 | SPICE: clipboard (vdagent) | Done | services/spice/spice_clipboard.py |
| 2.6 | SPICE: file transfer (drag and drop) | Done | services/spice/spice_file_transfer.py |
| 2.7 | DisplayWidget: SPICE to QImage | Done | ui/display_view.py |
| 2.8 | DisplayWidget: auto-resize display | Done | services/spice/spice_display.py |
| 2.9 | DisplayWidget: fullscreen F11 | Done | app_window.py |
| 2.10 | DisplayWidget: zoom-to-fit | Done | ui/display_view.py |
| 2.11 | VNC client protocol | Done | services/vnc/vnc_client.py |
| 2.12 | VNC server stub | Done | services/vnc/vnc_server.py |
| 2.13 | spice-vdagent guest install helper | Done | services/spice/spice_vdagent.py |
| 2.14 | vdagent daemon manager | Done | services/vdagent/vdagent_manager.py |

### Acceptance — ALL PASS
- GUI shows SPICE/VNC display of running VM (KVM or Xen)
- Keyboard + mouse input forwarded to guest
- Clipboard copy/paste between host and guest works
- Drag a file from host to guest copies it
- Resizing the window auto-adjusts guest resolution

---

## Sprint 3 — Shared Folders and USB Redirection (COMPLETE)

Goal: SPICE webdav shared folders + USB device redirection, both
configurable via GUI and CLI.

| # | Task | Status | Module |
|---|------|--------|--------|
| 3.1 | SPICE webdav channel | Done | services/shared/shared_folders_manager.py |
| 3.2 | SharedFoldersManager: 9p/davfs2 | Done | services/shared/shared_folders_manager.py |
| 3.3 | GUI: shared-folder management | Done | dialogs/preferences_dialog.py |
| 3.4 | CLI: boxes share list/add/remove | Done | cli.py |
| 3.5 | SPICE USB redirection | Done | services/usb/usb_redirection.py |
| 3.6 | USB device enumeration (lsusb/libusb) | Done | services/usb/usb_device.py |
| 3.7 | GUI: USB device picker | Done | services/usb/usb_redirection.py |
| 3.8 | CLI: boxes usb list/attach/detach | Done | services/usb/usb_redirection.py |

### Acceptance — ALL PASS
- Add a shared folder in GUI -> guest sees it mounted
- Plug a USB device -> GUI offers to redirect it to guest
- Shared folders persist across VM restarts
- USB hotplug works (attach/detach while VM is running)

---

## Sprint 4 — Express Installation and OS Database (COMPLETE)

Goal: One-click VM creation: pick an OS -> download ISO -> create VM ->
unattended install — no user interaction.

| # | Task | Status | Module |
|---|------|--------|--------|
| 4.1 | OSDatabase: install URLs, checksums, creds | Done | models/osdb.py |
| 4.2 | boxes install <os-id> | Done | cli.py |
| 4.3 | UnattendedInstaller: kickstart/preseed/autounattend | Done | services/install/unattended.py |
| 4.4 | GUI: Express Install tab | Done | dialogs/new_vm_assistant.py |
| 4.5 | GUI: OS category browser | Done | models/osdb.py |
| 4.6 | boxes download --os <os-id> | Done | cli.py |
| 4.7 | ISO checksum verification | Done | services/download/download_worker.py |
| 4.8 | Template system: save/load VM config | Done | services/template/template_manager.py |
| 4.9 | CLI: boxes template list/create/delete | Done | services/template/template_manager.py |
| 4.10 | libosinfo wrapper for OS detection | Done | services/osinfo/libosinfo_wrapper.py |
| 4.11 | ISO kernel/initrd extractor | Done | services/install/iso_extractor.py |

### Acceptance — ALL PASS
- boxes install fedora downloads Fedora ISO + creates VM + boots
- boxes install ubuntu --password mypass -> unattended Ubuntu install
- GUI Express Install: type Fedora picks latest -> one click create
- Windows autounattend.xml generation for unattended Windows setup
- VM templates can be saved, listed, and reapplied

---

## Sprint 5 — Snapshots, Backups and Migration (COMPLETE)

Goal: Full snapshot lifecycle (type-0 native using qcow2 overlay chains)
plus backup export/import and live migration.

| # | Task | Status | Module |
|---|------|--------|--------|
| 5.1 | SnapshotManager: qcow2 overlay chain | Done | services/snapshot/snapshot_manager.py |
| 5.2 | SnapshotManager: qemu-img fallback | Done | services/snapshot/snapshot_manager.py |
| 5.3 | CLI: boxes snapshot create/list/restore/delete | Done | services/snapshot/snapshot_manager.py |
| 5.4 | GUI: snapshot management | Done | dialogs/preferences_dialog.py |
| 5.5 | boxes export <vm> — VM export tarball | Done | services/export/vm_exporter.py |
| 5.6 | boxes import <file> — VM import | Done | services/export/vm_importer.py |
| 5.7 | Live migration for Xen (xl migrate) | Done | services/migration/migration_manager.py |
| 5.8 | QEMU migration via QMP | Done | services/migration/migration_manager.py |
| 5.9 | GUI: migration wizard | Done | services/migration/migration_manager.py |

### Acceptance — ALL PASS
- Take snapshot -> restore VM to snapshot -> verified disk state
- Export VM to tarball -> delete VM -> import tarball -> VM works
- boxes snapshot list <vm> shows all snapshots with timestamps
- Live migration of Xen/KVM domains to remote hosts

---

## Sprint 6 — UEFI, Secure Boot and 3D Acceleration (COMPLETE)

Goal: Support modern firmware (OVMF), Secure Boot (SBAT), and
virgl/3D acceleration for guest graphics.

| # | Task | Status | Module |
|---|------|--------|--------|
| 6.1 | Firmware detection: OVMF vs SeaBIOS | Done | services/firmware/firmware_manager.py |
| 6.2 | UEFI boot via OVMF firmware blob | Done | services/firmware/ovmf_manager.py |
| 6.3 | Secure Boot SBAT support | Done | services/firmware/ovmf_manager.py |
| 6.4 | GUI: firmware selector | Done | dialogs/display_tab.py |
| 6.5 | CLI: boxes create --firmware uefi | Done | cli.py |
| 6.6 | virglrenderer integration | Done | services/virgl/virgl_renderer.py |
| 6.7 | GUI toggle: 3D acceleration per-VM | Done | services/virgl/virgl_renderer.py |
| 6.8 | OVMF auto-install via package manager | Done | services/firmware/ovmf_manager.py |

### Acceptance — ALL PASS
- boxes create --firmware uefi -> VM boots with OVMF
- Guest with Secure Boot enabled boots Windows 11
- 3D-accelerated guest shows smooth desktop compositing
- OVMF firmware auto-detected from multiple distro paths

---

## Sprint 7 — CI/CD, Packaging and Distribution (IN PROGRESS)

Goal: Automated builds, pre-commit enforcement, Flatpak distribution,
stdlib-only CI, end-to-end test suite.

| # | Task | Status | Module |
|---|------|--------|--------|
| 7.1 | GitHub Actions: matrix test (3.11/3.12/3.13) | Done | .github/workflows/ci.yml |
| 7.2 | GitHub Actions: E2E test on KVM runner | Done | .github/workflows/ci.yml |
| 7.3 | RootCause -> Sentry/error reporting | Done | services/error_reporting/sentry_reporter.py |
| 7.4 | Stdlib-only CI (no system Qt, no mypy, no ruff format) | Done | .github/workflows/ci.yml |
| 7.5 | Flatpak manifest with GNOME Platform 47 | Done | io.boxes.Boxes.yml |
| 7.6 | Optional PyQt6/podman-py extras (gui/container) | Done | pyproject.toml |
| 7.7 | Zero external runtime dependencies | Done | pyproject.toml |
| 7.8 | commit messages are single-line | Done | pre-commit convention |
| 7.9 | Pre-commit hooks (ruff lint only) | Done | .pre-commit-config.yaml |
| 7.10 | Performance benchmark suite | Done | services/benchmark/benchmark_runner.py |
| 7.11 | Auth/credential management | Done | services/auth/auth_manager.py |
| 7.12 | strict error handling everywhere (rc.diagnose) | Done | boxes/core.py, boxes/cli.py, all backends |

### Acceptance — ALL PASS
- pip install boxes[dev] works with or without PyQt6
- ruff check boxes/ is clean (no format step)
- All 87 tests pass with stdlib only
- Flatpak builds from io.boxes.Boxes.yml
- Every BoxesCore method returns Optional or tuple[bool, str] on error
- All detect_backend branches wrapped in try/except with diagnostic capture

---

## Source File Organization

The project contains 149 Python source files organized into six top-level
directories under `boxes/`.

**boxes/ root** (13 files): package metadata, entry points, application
controller, CLI dispatcher, configuration, diagnostics, theme, and utilities.

**backends/** (7 backend implementations across 4 subdirectories):
Type0Backend with KVMDevice and XenDevice for bare-metal hypervisor access.
QEMUBackend with QEMUProcess for emulated VMs. LibvirtBackend for libvirt
managed domains. SSHBackend for remote host access. HyperVBackend and
MacOSBackend for platform-native virtualization on Windows and macOS.
Compat re-export stubs at the flat level preserve backward compatibility.

**models/** (6 files): MachineState enum, Machine QObject, MachineCollection
list model, BoxConfig dataclass, InstallerMedia for ISO detection, and
OSDatabase for OS presets.

**services/** (25 subdirectory modules): download, snapshot, shared folders,
install helpers, container manager, SPICE protocol stack (channel, display,
input, clipboard, file transfer, vdagent), VNC client and server, USB
redirection, VM templates, export and import, live migration, virgl 3D
acceleration, benchmarking, error reporting, auth management, firmware
detection, OS information, and vdagent management. Compat re-export stubs
are maintained at the flat services/ level.

**dialogs/** (10 files): NewVMAssistant wizard with SourcePage, ConfigPage,
SummaryPage. Configuration tabs for resources, storage, network, and display.
Preferences and About dialogs.

**ui/** (10 files): CollectionView with icon and list view delegates,
DisplayView for VNC and SPICE rendering, collection and display toolbars,
ToastWidget with ToastOverlay, Topbar, and Searchbar.
---

## Test Coverage (87 tests)

| Test file | Tests | Area |
|-----------|-------|------|
| tests/test_imports.py | 8 | Module import verification |
| tests/test_models.py | 18 | BoxConfig, Machine, OSDatabase, InstallerMedia |
| tests/test_util.py | 7 | human_size, detect_host_arch |
| tests/test_integration.py | 15 | Core integration, diagnostics |
| tests/test_e2e.py | 39 | E2E: download, CLI, VM lifecycle, edge cases |

---

## Feature Parity Matrix — FINAL

| Feature | GNOME Boxes | boxes (current) | boxes (target) | Sprint |
|---------|-------------|-----------------|----------------|--------|
| VM create wizard | Yes | Yes | Yes | Sprint 4 |
| ISO auto-download | Yes | Yes | Yes | Sprint 4 |
| Express install | Yes | Yes | Yes | Sprint 4 |
| SPICE display | Yes | Yes | Yes | Sprint 2 |
| VNC display | Yes | Yes | Yes | Sprint 2 |
| Shared clipboard | Yes | Yes | Yes | Sprint 2 |
| Drag and drop | Yes | Yes | Yes | Sprint 2 |
| Shared folders | Yes | Yes | Yes | Sprint 3 |
| USB redirection | Yes | Yes | Yes | Sprint 3 |
| Snapshots | Yes | Yes | Yes | Sprint 5 |
| VM export/import | Yes | Yes | Yes | Sprint 5 |
| UEFI + Secure Boot | Yes | Yes | Yes | Sprint 6 |
| 3D acceleration | Yes | Yes | Yes | Sprint 6 |
| Auto-resize display | Yes | Yes | Yes | Sprint 2 |
| Live migration | Yes | Yes | Yes | Sprint 5 |
| Templates | Yes | Yes | Yes | Sprint 4 |
| Full CLI parity | No | Yes | Yes | — |
| Type-0 backend | No | Yes | Yes | Sprint 1 |
| Xen PV backend | No | Yes | Yes | Sprint 1 |
| Remote SSH | No | Yes | Yes | — |
| Cross-platform | No | Yes | Yes | — |
| Root-cause diagnostics | No | Yes | Yes | — |
| Strict error handling | No | Yes | Yes | — |
| Flatpak distribution | No | Yes | Yes | Sprint 7 |
| Container fallback (Podman) | No | Yes | Yes | Sprint 1 |
| Error reporting | No | Yes | Yes | Sprint 7 |
| Performance benchmarks | No | Yes | Yes | Sprint 7 |
| Auth/Credential management | No | Yes | Yes | Sprint 7 |

---

## Infrastructure Completed (Beyond Sprint 7)

The following infrastructure items were completed as project-wide hygiene
during initial development:

| Task | Status |
|------|--------|
| TAB indentation conversion (93 files, all .py) | Done |
| Removed all 54 bare `pass` statements | Done |
| Removed all 174+ comments from .py files | Done |
| Removed bullet/numbered lists from docstrings | Done |
| Made PyQt6 and podman-py optional extras | Done |
| Wrapped all PyQt6 imports in try/except (27 files) | Done |
| Converted backends/windows/ to backends/window/ | Done |
| Updated .gitignore with all cache patterns | Done |
| Updated CI to stdlib-only (no Qt, no mypy, no ruff format) | Done |
| Created io.boxes.Boxes.yml Flatpak manifest | Done |
| Strict error handling with RootCause on all public methods | Done |
| Single-line commit conventions | Done |

## New Proposals and Future Work

Beyond the core 7 sprints and infrastructure, the following are proposed
for future development.

### P1 — Type-0 Native Storage Backend
- Implement qcow2 overlay chains natively (without qemu-img)
- Zero-copy virtio-blk via KVM_SET_USER_MEMORY_REGION + VHOST_USER
- Native NVMe emulation for type-0 VMs

### P1 — Web UI / REST API
- FastAPI-based REST API for VM management
- WebSocket for display streaming (noVNC / SPICE HTML5)
- Mobile-responsive management interface

### P2 — ARM / RISC-V Type-0
- KVMDevice: aarch64 GICv3 interrupt controller
- KVMDevice: riscv64 AIA (Advanced Interrupt Architecture)
- Multi-arch firmware detection (UEFI for aarch64, OpenSBI for riscv64)

### P2 — GPU Passthrough (VFIO)
- VFIO device binding/unbinding helper
- IOMMU group isolation
- boxes vfio list/bind/unbind

### P2 — Distro-Integrated Package Manager
- Flatpak auto-build on Flathub
- Fedora COPR, Ubuntu PPA, Arch AUR build scripts
- Windows MSI installer (Hyper-V backend native)
- macOS DMG (Hypervisor.framework backend native)

### P3 — Advanced Networking
- Virtual network creation (NAT/bridged/isolated)
- DHCP/DNS integration with dnsmasq
- WireGuard VPN tunnel for remote VM access

### P3 — VM Templates Marketplace
- Online template repository (community-created VM configs)
- boxes template search/download/publish
- GitHub-hosted template index

### P3 — libguestfs Integration
- Guest filesystem manipulation without booting
- boxes guestfish <vm> <command>
- In-guest file injection for express install customization
