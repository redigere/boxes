# Boxes — Type-0 Hypervisor Manager

## Differentiator: Type-0 First, CLI Core

GNOME Boxes (`virt-manager`-based, type 2) relies on QEMU + libvirt for every operation.
**boxes** inverts the stack: primary backends are **type 0** (bare-metal KVM ioctl,
bare-metal Xen hypercall) — no emulator process, no libvirt daemon required.
QEMU/libvirt/QEMUProcess are only a fallback.

| Feature | GNOME Boxes | boxes (this project) |
|---------|-------------|----------------------|
| Primary backend | QEMU + libvirt (type 2/1) | KVM ioctl / Xen hypercall (**type 0**) |
| CLI core | No (GUI-only) | **Yes** — full CLI parity |
| ISO auto-download | ✓ | ✓ (`boxes download`) |
| SPICE display | ✓ | ◐ (basic VNC/SPICE stub) |
| Shared clipboard | ✓ (spice-vdagent) | ⬜ |
| Drag & drop files | ✓ | ⬜ |
| Shared folders | ✓ (SPICE webdav) | ◐ (manager exists, no backend wiring) |
| USB redirection | ✓ | ⬜ |
| Snapshots | ✓ (libvirt) | ◐ (manager exists, no type-0 wiring) |
| Express install | ✓ (libosinfo) | ◐ (OSDatabase exists, no unattended wiring) |
| UEFI / Secure Boot | ✓ | ◐ (config field exists) |
| 3D acceleration (virgl) | ✓ | ⬜ |
| Auto-resize display | ✓ | ⬜ |
| Remote SSH backend | ⬜ (GNOME Connections split) | ✓ |

---

## Sprint 1 — Type-0 VM Lifecycle (core complete)

**Goal**: Type-0 backend (KVM + Xen) can create, run, stop, pause, resume VMs
natively without QEMU or libvirt.

| # | Task | Priority |
|---|------|----------|
| 1.1 | KVMDevice: load ELF/PIE kernel + initrd via `KVM_SET_USER_MEMORY_REGION` + `KVM_SET_SREGS` | P0 |
| 1.2 | KVMDevice: PCI device tree (virtio-blk, virtio-net, virtio-console) | P0 |
| 1.3 | KVMDevice: SMP support (>1 vCPU via `KVM_CREATE_VCPU` × N) | P0 |
| 1.4 | KVMDevice: `KVM_IRQFD` + `KVM_IOEVENTFD` for virtio notifications | P0 |
| 1.5 | XenDevice: `privcmd` hypercall interface for domain creation/destruction | P0 |
| 1.6 | XenDevice: `evtchn` event channel + `gnttab` grant-table for PV drivers | P1 |
| 1.7 | Type0Backend: `_start_kvm_direct` → load firmware + boot VM | P0 |
| 1.8 | Type0Backend: `_start_kvm_direct` → attach virtio-block via mmap | P0 |
| 1.9 | CLI: `boxes run <name>` — run VM in foreground with console output | P1 |
| 1.10 | CLI: `boxes console <name>` — attach to VM serial/console | P1 |

### Acceptance criteria
- `boxes create --name foo --memory 512 --vcpus 1 --disk 5` + `boxes start foo`
  boots a Linux kernel under **pure KVM ioctl** (no QEMU process)
- `boxes stop foo`, `boxes pause foo`, `boxes resume foo` all succeed
- Xen PV domain create/destroy works via `privcmd`

---

## Sprint 2 — SPICE Display & Input (core + GUI)

**Goal**: Full SPICE protocol support for display, input, clipboard, and
drag-and-drop — matching GNOME Boxes experience.

| # | Task | Priority |
|---|------|----------|
| 2.1 | SPICE protocol handshake (main + display channel) | P0 |
| 2.2 | SPICE: lossy/lossless image compression (quic, lz, glz) | P0 |
| 2.3 | SPICE: input channel (keyboard + mouse) | P0 |
| 2.4 | SPICE: cursor channel | P1 |
| 2.5 | SPICE: clipboard (vdagent) — shared clipboard host↔guest | P1 |
| 2.6 | SPICE: file transfer (drag & drop via vdagent) | P2 |
| 2.7 | DisplayWidget: wire SPICE channel → `QImage` rendering | P0 |
| 2.8 | DisplayWidget: auto-resize guest display to window size | P1 |
| 2.9 | DisplayWidget: fullscreen with F11 | P0 |
| 2.10 | DisplayWidget: zoom-to-fit / scale display | P1 |
| 2.11 | `spice-vdagent` guest-side install helper in CLI | P2 |

### Acceptance criteria
- GUI shows SPICE display of running VM (KVM or Xen)
- Keyboard + mouse input forwarded to guest
- Clipboard copy/paste between host and guest works
- Drag a file from host → guest copies it
- Resizing the window auto-adjusts guest resolution

---

## Sprint 3 — Shared Folders & USB Redirection

**Goal**: SPICE webdav shared folders + USB device redirection, both
configurable via GUI and CLI.

| # | Task | Priority |
|---|------|----------|
| 3.1 | SPICE webdav channel implementation | P0 |
| 3.2 | SharedFoldersManager: mount webdav in guest via `davfs2` or 9p | P0 |
| 3.3 | GUI: shared-folder management in Preferences → Storage tab | P0 |
| 3.4 | CLI: `boxes share list/add/remove <vm> <host-path> <guest-path>` | P1 |
| 3.5 | SPICE USB redirection channel (`usbredir`) | P1 |
| 3.6 | USB device enumeration on host (`lsusb` / `libusb`) | P1 |
| 3.7 | GUI: USB device picker in VM display toolbar | P2 |
| 3.8 | CLI: `boxes usb list/attach/detach <vm> <device>` | P2 |

### Acceptance criteria
- Add a shared folder in GUI → guest sees it mounted
- Plug a USB device → GUI offers to redirect it to guest
- Shared folders persist across VM restarts
- USB hotplug works (attach/detach while VM is running)

---

## Sprint 4 — Express Installation & OS Database

**Goal**: One-click VM creation: pick an OS → download ISO → create VM →
unattended install — no user interaction.

| # | Task | Priority |
|---|------|----------|
| 4.1 | OSDatabase: enrich with install URLs, checksums, default credentials | P0 |
| 4.2 | `boxes install <os-id>` — single-command download + create + start | P0 |
| 4.3 | UnattendedInstaller: wire kickstart/preseed/autounattend into VM creation | P0 |
| 4.4 | GUI: Express Install tab in New VM wizard | P1 |
| 4.5 | GUI: OS category browser (Linux distros, Windows, BSD, Other) | P1 |
| 4.6 | `boxes download --os <os-id>` — download ISO by ID | P1 |
| 4.7 | ISO checksum verification after download | P2 |
| 4.8 | Template system: save VM config as reusable template | P2 |
| 4.9 | CLI: `boxes template list/create/delete` | P2 |

### Acceptance criteria
- `boxes install fedora` → downloads Fedora ISO + creates VM + boots
- `boxes install ubuntu --password mypass` → unattended Ubuntu install
- GUI Express Install: type "Fedora" → picks latest → one click create
- Windows autounattend.xml generation for unattended Windows setup

---

## Sprint 5 — Snapshots, Backups & Migration

**Goal**: Full snapshot lifecycle (type-0 native using qcow2 overlay chains)
plus backup export/import and live migration.

| # | Task | Priority |
|---|------|----------|
| 5.1 | SnapshotManager: qcow2 overlay chain (backing file) for type-0 | P0 |
| 5.2 | SnapshotManager: `qemu-img snapshot` fallback for QEMU backend | P1 |
| 5.3 | CLI: `boxes snapshot create/list/restore/delete <vm> <name>` | P0 |
| 5.4 | GUI: snapshot management in VM display toolbar | P1 |
| 5.5 | `boxes export <vm> --output boxes.tar.gz` — full VM export | P1 |
| 5.6 | `boxes import <file>` — import exported VM | P1 |
| 5.7 | Live migration for Xen ( `xl migrate` ) | P2 |
| 5.8 | GUI: migration wizard (migrate VM to another host) | P2 |

### Acceptance criteria
- Take snapshot → restore VM to snapshot → verified disk state
- Export VM to tarball → delete VM → import tarball → VM works
- `boxes snapshot list <vm>` shows all snapshots with timestamps

---

## Sprint 6 — UEFI, Secure Boot & 3D Acceleration

**Goal**: Support modern firmware (OVMF), Secure Boot (SBAT), and
virgl/3D acceleration for guest graphics.

| # | Task | Priority |
|---|------|----------|
| 6.1 | Firmware detection: OVMF (UEFI) vs SeaBIOS (legacy) | P0 |
| 6.2 | UEFI boot via OVMF firmware blob + `KVM_SET_SREGS` | P0 |
| 6.3 | Secure Boot SBAT support (enroll keys in guest) | P1 |
| 6.4 | GUI: firmware selector in Preferences → Display tab | P1 |
| 6.5 | CLI: `boxes create --firmware uefi` | P0 |
| 6.6 | virglrenderer integration for 3D acceleration | P2 |
| 6.7 | GUI toggle: enable 3D acceleration per-VM | P2 |

### Acceptance criteria
- `boxes create --firmware uefi` → VM boots with OVMF
- Guest with Secure Boot enabled boots Windows 11
- 3D-accelerated guest shows smooth desktop compositing

---

## Sprint 7 — CI/CD, Packaging & Distribution

**Goal**: Automated builds, pre-commit enforcement, PyPI + Flatpak + distro
packages, end-to-end test suite running on real KVM hardware.

| # | Task | Priority |
|---|------|----------|
| 7.1 | GitHub Actions: matrix test (Linux KVM, macOS HVF, Windows Hyper-V) | P0 |
| 7.2 | GitHub Actions: E2E test on self-hosted KVM runner | P1 |
| 7.3 | `boxes.diagnostics.RootCause` → Sentry/error reporting integration | P1 |
| 7.4 | PyPI publish workflow (trusted publishing) | P1 |
| 7.5 | Flatpak manifest (Flathub) | P2 |
| 7.6 | Distribution packages: Fedora COPR, Ubuntu PPA, Arch AUR | P2 |
| 7.7 | Pre-commit hooks enforced in CI | P0 |
| 7.8 | Performance benchmark suite (boot time, IOPS, network throughput) | P2 |

### Acceptance criteria
- Every PR runs full test suite + ruff + mypy
- `pip install boxes` works on Linux/macOS/Windows
- Flatpak published on Flathub
- CI includes at least one bare-metal KVM runner for type-0 tests

---

## All-time: Feature Parity Matrix

| Feature | GNOME Boxes | boxes (current) | boxes (target) |
|---------|-------------|-----------------|----------------|
| VM create wizard | ✓ | ✓ | ✓ |
| ISO auto-download | ✓ | ✓ | ✓ |
| Express install | ✓ | ◐ | Sprint 4 |
| SPICE display | ✓ | ◐ | Sprint 2 |
| VNC display | ✓ | ◐ | Sprint 2 |
| Shared clipboard | ✓ | ⬜ | Sprint 2 |
| Drag & drop | ✓ | ⬜ | Sprint 2 |
| Shared folders | ✓ | ◐ | Sprint 3 |
| USB redirection | ✓ | ⬜ | Sprint 3 |
| Snapshots | ✓ | ◐ | Sprint 5 |
| VM export/import | ✓ | ⬜ | Sprint 5 |
| UEFI + Secure Boot | ✓ | ◐ | Sprint 6 |
| 3D acceleration | ✓ | ⬜ | Sprint 6 |
| Auto-resize display | ✓ | ⬜ | Sprint 2 |
| Full CLI parity | ⬜ | ✓ | ✓ |
| Type-0 backend | ⬜ | ✓ | Sprint 1 |
| Xen PV backend | ⬜ | ✓ | Sprint 1 |
| Remote SSH | ⬜ | ✓ | ✓ |
| Cross-platform | ⬜ | ✓ | ✓ |
| Root-cause diagnostics | ⬜ | ✓ | ✓ |
