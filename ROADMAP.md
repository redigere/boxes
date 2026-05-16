# Boxes — Type-0 Hypervisor Manager — ROADMAP

Project life history. Tracks completed milestones (Sprint 1-7),
infrastructure work, current state, and planned development (Sprint 8-12).
Updated as the project evolves.

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

## Sprint 7 — CI/CD, Packaging and Distribution (COMPLETE)

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

---

## New Proposals and Future Work

Beyond the core 7 sprints and infrastructure, the following are proposed
for future development. Each proposal is now tracked as a concrete sprint
with detailed task breakdown in Sprint 8-12 above.

### P1 — Type-0 Native Storage Backend (Sprint 8)
| Capability | Target |
|------------|--------|
| Native qcow2 overlay chains | No qemu-img call for disk create/snapshot |
| Zero-copy virtio-blk | KVM_SET_USER_MEMORY_REGION + VHOST_USER |
| Native NVMe emulation | Submission/completion queues, DMA for type-0 |

### P1 — Web UI / REST API (Sprint 9)
| Capability | Target |
|------------|--------|
| REST API | Lightweight HTTP server for VM CRUD |
| Display streaming | WebSocket SPICE to HTML5 canvas, noVNC fallback |
| Management interface | Mobile-responsive single-page web UI |

### P2 — ARM / RISC-V Type-0 (Sprint 10)
| Capability | Target |
|------------|--------|
| aarch64 GICv3 | Interrupt controller, ITS, redistributors |
| riscv64 AIA | Advanced Interrupt Architecture support |
| Multi-arch firmware | UEFI for aarch64, OpenSBI for riscv64 |

### P2 — GPU Passthrough VFIO (Sprint 10)
| Capability | Target |
|------------|--------|
| IOMMU group isolation | Device binding/unbinding from host driver |
| CLI | boxes vfio list/bind/unbind |
| GUI | GPU passthrough device picker |

### P2 — Distro-Integrated Packaging (Sprint 11)
| Channel | Artifact |
|---------|---------|
| Flathub | Flatpak auto-build workflow |
| Fedora COPR | SRPM with boxes.spec |
| Ubuntu PPA | debian/ build scripts |
| Arch AUR | PKGBUILD |
| Windows | MSI installer (WiX, Hyper-V backend) |
| macOS | DMG (Hypervisor.framework backend) |

### P3 — Advanced Networking (Sprint 11)
| Capability | Target |
|------------|--------|
| Virtual NAT network | dnsmasq DHCP/DNS, tap interface |
| Bridged network | Linux bridge + tap |
| VPN tunnel | WireGuard for remote VM access |

### P3 — VM Templates Marketplace (Sprint 12)
| Capability | Target |
|------------|--------|
| Online repository | Community-created VM configs |
| CLI | boxes template search/download/publish |
| Hosting | GitHub-hosted template index with CI |

### P3 — libguestfs Integration (Sprint 12)
| Capability | Target |
|------------|--------|
| Guest filesystem | Native qcow2 mount, read, write (no libguestfs) |
| CLI | boxes guestfish ls/cat/inject |
| Express install | In-guest file injection for customization |

---

## Sprint 8 — Type-0 Native Storage Backend (PLANNED)

Goal: Remove qemu-img dependency by implementing qcow2/vhdx natively in
Python (stdlib-only). Add zero-copy virtio-blk and NVMe emulation for
type-0 VMs.

| # | Task | Status | Module |
|---|------|--------|--------|
| 8.1 | Native qcow2 format parser/writer (header, clusters, refcounts) | Planned | backends/type0/storage/qcow2.py |
| 8.2 | Native qcow2 overlay chain (snapshot without qemu-img) | Planned | backends/type0/storage/qcow2.py |
| 8.3 | Native VHDX parser/writer for Hyper-V backend | Planned | backends/type0/storage/vhdx.py |
| 8.4 | Zero-copy virtio-blk via KVM_SET_USER_MEMORY_REGION | Planned | backends/type0/kvm_device.py |
| 8.5 | VHOST_USER backend for virtio-blk (shared memory) | Planned | backends/type0/vhost.py |
| 8.6 | Native NVMe emulation (submission/completion queues, DMA) | Planned | backends/type0/storage/nvme.py |
| 8.7 | Disk format auto-detection (qcow2/raw/vhdx) | Planned | backends/type0/storage/disk.py |
| 8.8 | Remove qemu-img from critical path; keep as optional fallback | Planned | all backends |

### Acceptance
- `boxes create --disk 10` creates qcow2 without calling qemu-img
- Snapshot create/restore uses native qcow2 overlay chain
- NVMe emulation yields better IOPS than virtio-blk on type-0
- All existing backends fall back to qemu-img when native unavailable

---

## Sprint 9 — Web UI / REST API (PLANNED)

Goal: Provide a lightweight web management interface with real-time
display streaming — no desktop environment required.

| # | Task | Status | Module |
|---|------|--------|--------|
| 9.1 | REST API: VM CRUD endpoints (create, start, stop, delete) | Planned | boxes/services/api/server.py |
| 9.2 | REST API: snapshot listing and management | Planned | boxes/services/api/server.py |
| 9.3 | REST API: USB hotplug and shared folder management | Planned | boxes/services/api/server.py |
| 9.4 | WebSocket: VM state change push notifications | Planned | boxes/services/api/ws.py |
| 9.5 | WebSocket: SPICE display streaming to HTML5 canvas | Planned | boxes/services/api/ws.py |
| 9.6 | noVNC fallback for VNC-backed VMs | Planned | boxes/services/api/novnc.py |
| 9.7 | Static single-page web UI (htmx + vanilla JS, no framework) | Planned | boxes/services/api/static/ |
| 9.8 | CLI: `boxes serve` starts web server | Planned | cli.py |
| 9.9 | Auth: API token authentication | Planned | services/auth/auth_manager.py |

### Acceptance
- `boxes serve --port 8080` serves a responsive VM dashboard
- Create, start, stop, delete VM works from browser
- VM display renders in browser at ≥30 FPS on LAN
- API is usable by third-party tools (curl, Ansible, etc.)

---

## Sprint 10 — ARM / RISC-V Type-0 + GPU Passthrough (PLANNED)

Goal: Extend type-0 backend to aarch64 and riscv64 architectures. Add
VFIO GPU passthrough for high-performance graphics in VMs.

| # | Task | Status | Module |
|---|------|--------|--------|
| 10.1 | KVMDevice: aarch64 GICv3 interrupt controller (ITS, redistributors) | Planned | backends/type0/kvm_device.py |
| 10.2 | KVMDevice: aarch64 PSCI firmware interface | Planned | backends/type0/kvm_device.py |
| 10.3 | KVMDevice: riscv64 AIA (Advanced Interrupt Architecture) | Planned | backends/type0/kvm_device.py |
| 10.4 | KVMDevice: riscv64 SBI extension support | Planned | backends/type0/kvm_device.py |
| 10.5 | Multi-arch firmware detection (UEFI aarch64, OpenSBI riscv64) | Planned | services/firmware/firmware_manager.py |
| 10.6 | VFIO: IOMMU group detection and isolation | Planned | backends/type0/vfio.py |
| 10.7 | VFIO: device binding/unbinding from host driver | Planned | backends/type0/vfio.py |
| 10.8 | CLI: `boxes vfio list/bind/unbind` | Planned | cli.py |
| 10.9 | GUI: GPU passthrough device picker | Planned | dialogs/preferences_dialog.py |

### Acceptance
- `boxes create --arch aarch64` boots on Apple M1/M2 (macOS HVF) or KVM host
- `boxes create --arch riscv64` boots on QEMU riscv64 or KVM host
- `boxes vfio bind 0000:01:00.0` isolates GPU for passthrough
- Guest with VFIO GPU shows native graphics performance

---

## Sprint 11 — Distro-Integrated Packaging + Advanced Networking (PLANNED)

Goal: Distribute boxes through all major package channels. Build virtual
network infrastructure comparable to libvirt's default NAT network.

| # | Task | Status | Module |
|---|------|--------|--------|
| 11.1 | Flatpak auto-build workflow on Flathub | Planned | .github/workflows/flathub.yml |
| 11.2 | Fedora COPR build SRPM generator | Planned | packaging/fedora/boxes.spec |
| 11.3 | Ubuntu PPA build scripts | Planned | packaging/ubuntu/debian/ |
| 11.4 | Arch AUR PKGBUILD | Planned | packaging/arch/PKGBUILD |
| 11.5 | Windows MSI installer (WiX toolset, Hyper-V backend) | Planned | packaging/windows/ |
| 11.6 | macOS DMG (Hypervisor.framework backend) | Planned | packaging/macos/ |
| 11.7 | Virtual NAT network with dnsmasq DHCP/DNS | Planned | services/network/nat_network.py |
| 11.8 | Bridged network interface creation (tap + bridge) | Planned | services/network/bridge_network.py |
| 11.9 | CLI: `boxes network create/list/remove` | Planned | cli.py |
| 11.10 | WireGuard VPN tunnel for remote VM access | Planned | services/network/wireguard.py |

### Acceptance
- `pip install boxes` (stdlib-only) on all platforms
- `flatpak install io.boxes.Boxes` works from Flathub
- `boxes network create --nat mynet` provides DHCP to VMs
- WireGuard tunnel allows VM access from remote hosts
- Windows MSI installs and runs Hyper-V backend

---

## Sprint 12 — VM Templates Marketplace + libguestfs (PLANNED)

Goal: Community-driven VM template sharing. Guest filesystem
manipulation without booting the VM.

| # | Task | Status | Module |
|---|------|--------|--------|
| 12.1 | Template index format (JSON schema, versioned) | Planned | services/template/template_index.py |
| 12.2 | `boxes template search <query>` — search online index | Planned | services/template/template_manager.py |
| 12.3 | `boxes template download <id>` — pull community template | Planned | services/template/template_manager.py |
| 12.4 | `boxes template publish` — push to community index | Planned | services/template/template_manager.py |
| 12.5 | Native qcow2 mount/read/write (no libguestfs) | Planned | services/guestfs/guestfs.py |
| 12.6 | `boxes guestfish <vm> ls <path>` — list files in VM disk | Planned | services/guestfs/guestfs.py |
| 12.7 | `boxes guestfish <vm> cat <path>` — read file from VM disk | Planned | services/guestfs/guestfs.py |
| 12.8 | `boxes guestfish <vm> inject <src> <dst>` — file injection | Planned | services/guestfs/guestfs.py |
| 12.9 | In-guest file injection for express install customization | Planned | services/install/unattended.py |

### Acceptance
- `boxes template search ubuntu` returns community Ubuntu templates
- `boxes template download ubuntu-24.04` creates a pre-configured VM
- `boxes guestfish myvm ls /etc/` lists files in an offline VM disk
- `boxes guestfish myvm inject cloud-init.iso /` enables cloud-init
- Template marketplace hosted on GitHub Pages with automated CI

---

## Dependency Strategy

### Python Packages (`pip install boxes`)

**Zero runtime dependencies.** The core package installs with only the
Python stdlib — no PyPI packages required. This makes `boxes` usable in
minimal environments (containers, embedded, air-gapped systems).

| Category | Package | Type | Required |
|----------|---------|------|----------|
| Core | (stdlib only) | — | Yes |
| GUI | PyQt6 >= 6.5 | Optional (`[gui]`) | No |
| Container | podman-py >= 5 | Optional (`[container]`) | No |
| Libvirt | libvirt-python >= 10 | Optional (`[libvirt]`) | No |
| Image decode | Pillow | Optional (SPICE JPEG fallback) | No |
| Dev | pytest, ruff, mypy, pre-commit | Dev only (`[dev]`) | No |

Layout:
```toml
[project]
dependencies = []       # stdlib only

[project.optional-dependencies]
gui = ["PyQt6>=6.5"]
container = ["podman-py>=5"]
libvirt = ["libvirt-python>=10"]
dev = ["boxes[gui,container]", "pytest>=7", "ruff>=0.1", "mypy>=1.0", "pre-commit>=3"]
```

### Flatpak Distribution (`io.boxes.Boxes`)

The Flatpak manifest uses **GNOME Platform** runtime which provides Qt,
SPICE protocol libraries, and other system dependencies. All external
CLI tools are resolved at build/run time from the Flatpak SDK or bundled
as Flatpak modules.

| System Dependency | Source | Required By |
|-------------------|--------|-------------|
| QEMU (qemu-system-*, qemu-img) | GNOME Platform runtime / bundled module | backends/qemu/, all disk ops |
| OVMF/UEFI firmware | Flatpak module (edk2-ovmf) | services/firmware/ |
| SPICE vdagentd | GNOME Platform runtime | services/vdagent/ |
| libosinfo (osinfo-query) | Flatpak module (libosinfo) | services/osinfo/ |
| Podman | Host (flatpak-spawn --host) | services/container/ |
| dnsmasq | Flatpak module | services/network/ (Sprint 11) |
| genisoimage/isoinfo | Flatpak module (cdrtools) | services/install/ |
| lsusb (usbutils) | GNOME Platform runtime | services/usb/ |
| WireGuard (wg) | Flatpak module / host | services/network/ (Sprint 11) |

The `io.boxes.Boxes.yml` manifest installs the package with `pip install
--prefix ... .[gui]` so the GUI is always available in Flatpak.
System-level CLI tools are not bundled as Python dependencies — they
remain external and are detected at runtime via `shutil.which()`, with
graceful fallback and diagnostic reporting.

### Runtime Detection Flow

```
shutil.which("qemu-img") -> found? yes -> use it
                          -> no  -> try native qcow2 (Sprint 8)
                                   -> unsupported? -> DiagnosticRecord + fallback
```

This design keeps the pip package zero-dependency while allowing
full functionality when system tools are present — either natively or
via Flatpak runtime. No command is ever hard-required; every external
tool has a fallback path (either alternative tool, Python-native
implementation, or a clear error message with install instructions).

---

## Feature Parity Matrix — EXTENDED

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
| Native qcow2 storage | No | No | Yes | Sprint 8 |
| NVMe emulation | No | No | Yes | Sprint 8 |
| Web UI / REST API | No | No | Yes | Sprint 9 |
| Browser display streaming | No | No | Yes | Sprint 9 |
| ARM type-0 support | No | No | Yes | Sprint 10 |
| RISC-V type-0 support | No | No | Yes | Sprint 10 |
| VFIO GPU passthrough | No | No | Yes | Sprint 10 |
| Distro packages (COPR/PPA/AUR) | No | No | Yes | Sprint 11 |
| Windows MSI / macOS DMG | No | No | Yes | Sprint 11 |
| Virtual NAT networking | Yes | No | Yes | Sprint 11 |
| WireGuard VPN tunnels | No | No | Yes | Sprint 11 |
| VM template marketplace | No | No | Yes | Sprint 12 |
| GuestFS (libguestfs equivalent) | No | No | Yes | Sprint 12 |
