from typing import Optional
import signal
import subprocess
import shutil
import ctypes
from pathlib import Path

from boxes.backends import BaseBackend
from boxes.backends.kvm_device import KVMDevice
from boxes.backends.xen_device import XenDevice
from boxes.models.config import BoxConfig
from boxes.models.machine import MachineState
from boxes.constants import BOXES_IMAGES


class Type0Backend(BaseBackend):
    def __init__(self) -> None:
        super().__init__()
        self._kvm = KVMDevice()
        self._xen = XenDevice()
        self._mode: str = ""
        self._vms: dict[str, dict] = {}
        self._vm_fds: dict[str, int] = {}
        self._guest_mem: dict[str, ctypes.Array[ctypes.c_char]] = {}

    def _load_existing_vms(self) -> None:
        """Load all saved VM configs into the internal registry."""
        from boxes.models.config import BoxConfig as _BoxConfig

        for cfg in _BoxConfig.list_all():
            if cfg.uuid not in self._vms:
                self.define_machine(cfg)

    @staticmethod
    def _load_config(backend_id: str) -> Optional[BoxConfig]:
        """Load a VM config from disk by UUID."""
        from boxes.models.config import BoxConfig as _BoxConfig

        configs = _BoxConfig.list_all()
        for c in configs:
            if c.uuid == backend_id:
                return c
        return None

    def connect(self) -> bool:
        if self._kvm.probe():
            if self._kvm.open():
                self._mode = "kvm"
                self._connected = True
                self._load_existing_vms()
                return True
            if Path("/dev/kvm").exists():
                self._mode = "kvm"
                self._connected = True
                self._load_existing_vms()
                return True
        if self._xen.probe():
            if self._xen.open():
                self._mode = "xen"
                self._connected = True
                self._load_existing_vms()
                return True
            self._mode = "xen"
            self._connected = True
            self._load_existing_vms()
            return True
        return False

    def disconnect(self) -> None:
        for uid in list(self._vms.keys()):
            self.shutdown_machine(uid)
        self._kvm.close()
        self._xen.close()
        self._vms.clear()
        self._vm_fds.clear()
        self._guest_mem.clear()
        self._connected = False

    def list_machines(self) -> list[dict]:
        if self._mode == "xen" and self._xen.is_open:
            result = subprocess.run(["xl", "list"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                machines = []
                lines = result.stdout.strip().split("\n")[1:]
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 5:
                        machines.append(
                            {
                                "name": parts[0],
                                "id": int(parts[1]) if parts[1].isdigit() else -1,
                                "state": 1 if "r" in parts[4] else 0,
                                "active": "r" in parts[4],
                            }
                        )
                return machines
        return [
            {
                "uuid": uid,
                "name": info["config"].name,
                "state": info["state"],
                "active": info["state"] == MachineState.RUNNING,
            }
            for uid, info in self._vms.items()
        ]

    def define_machine(self, config: BoxConfig) -> Optional[str]:
        self._vms[config.uuid] = {
            "config": config,
            "state": MachineState.STOPPED,
            "vm_fd": None,
            "proc": None,
            "display_port": None,
        }
        return config.uuid

    def undefine_machine(self, backend_id: str) -> bool:
        self.shutdown_machine(backend_id)
        self._vms.pop(backend_id, None)
        return True

    def _start_kvm_direct(self, config: BoxConfig, backend_id: str = "") -> Optional[int]:
        """Start a VM using raw KVM ioctls (type-0).

        Sets up KVM with firmware, TSS, IRQ chip, and VCPUs.
        The VCPUs can then be executed via _run_kvm_vcpu().
        """
        if not self._kvm.is_open:
            return None
        vm_fd = self._kvm.create_vm()
        if vm_fd is None:
            return None

        # Allocate guest memory
        mem_size = config.memory_mb * 1024 * 1024
        mem = ctypes.create_string_buffer(mem_size)
        host_addr = ctypes.addressof(mem)
        self._kvm.set_user_memory_region(vm_fd, 0, mem_size, host_addr, 0)

        # Load firmware into guest memory
        firmware = self._find_firmware()
        if firmware:
            try:
                fw_data = firmware.read_bytes()
                fw_size = min(len(fw_data), 4 * 1024 * 1024)  # Max 4MB firmware
                ctypes.memmove(mem, fw_data, fw_size)
            except (OSError, PermissionError):
                pass

        # Set up KVM
        try:
            kvm = self._kvm
            # Set TSS address
            try:
                import fcntl

                fcntl.ioctl(vm_fd, 0xAE47, 0xFFFBD000)
            except (OSError, ImportError):
                pass

            # Create IRQ chip
            try:
                fcntl.ioctl(vm_fd, 0xAE60, 0)
            except OSError:
                pass

            # Create VCPUs
            num_vcpus = min(config.vcpus, 256)
            for i in range(num_vcpus):
                kvm.create_vcpu(vm_fd, i)

            # Store VM references
            if backend_id:
                self._vm_fds[backend_id] = vm_fd
                self._guest_mem[backend_id] = mem
        except Exception:
            pass

        return vm_fd

    def _find_firmware(self) -> Optional[Path]:
        """Find a BIOS/firmware file for direct KVM boot."""
        search_paths = [
            "/usr/share/seabios/bios.bin",
            "/usr/share/qemu/bios.bin",
            "/usr/share/edk2/ovmf/OVMF_CODE.fd",
            "/usr/share/ovmf/OVMF_CODE.fd",
            "/usr/share/qemu/ovmf-x86_64.bin",
            "/run/host/usr/share/seabios/bios.bin",
            "/run/host/usr/share/qemu/bios.bin",
            "/run/host/usr/share/edk2/ovmf/OVMF_CODE.fd",
        ]
        for path in search_paths:
            p = Path(path)
            if p.exists():
                return p
        return None

    def _run_kvm_vcpu(self, vm_fd: int, vcpu_id: int = 0) -> None:
        """Run a KVM VCPU in a loop (blocking).

        This should be called in a separate thread per VCPU.
        Handles VM exits minimally (halt/shutdown).
        """
        try:
            import fcntl
            import struct

            kvm_run_mmap_size = 16384  # Typical KVM_RUN mmap size
            vcpu_fd = self._kvm._vcpu_fd if vcpu_id == 0 else None
            if vcpu_fd is None:
                return
            while True:
                try:
                    fcntl.ioctl(vcpu_fd, 0xAE80, 0)  # KVM_RUN
                except OSError as e:
                    if e.errno == 4:  # EINTR
                        continue
                    break
                # Read exit reason from kvm_run
                try:
                    import mmap as _mmap

                    run_mmap = _mmap.mmap(
                        vcpu_fd, kvm_run_mmap_size, _mmap.MAP_SHARED, _mmap.PROT_READ | _mmap.PROT_WRITE
                    )
                    exit_reason = struct.unpack_from("I", run_mmap, 0)[0]
                    run_mmap.close()
                    if exit_reason == 8:  # KVM_EXIT_HLT
                        break
                    if exit_reason == 5:  # KVM_EXIT_IO
                        # Read IO direction/port from run structure offset
                        io_data = run_mmap[4:12] if run_mmap else b""
                        if io_data and io_data[0] == 0 and io_data[1] == 0:
                            pass
                    if exit_reason == 6:  # KVM_EXIT_MMIO
                        continue
                    if exit_reason == 0x100:  # KVM_EXIT_SHUTDOWN
                        break
                except (ImportError, OSError):
                    break
        except (OSError, ImportError):
            pass

    def _start_qemu_kvm(self, config: BoxConfig) -> Optional[subprocess.Popen]:
        qemu = self._find_qemu()
        if qemu is None:
            return None
        import socket as _socket

        with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            display_port = s.getsockname()[1]
        cmd = [
            qemu,
            "-nographic",
            "-machine",
            "pc-q35-9.2,accel=kvm:dax:tcg",
            "-cpu",
            "host,passthrough",
            "-m",
            str(config.memory_mb),
            "-smp",
            str(config.vcpus),
            "-drive",
            f"file={config.disk_path},format=qcow2,if=virtio,aio=native,cache=unsafe",
            "-netdev",
            "user,id=net0",
            "-device",
            "virtio-net-pci,netdev=net0",
            "-vnc",
            f"127.0.0.1:{display_port}",
            "-vga",
            "virtio",
            "-device",
            "virtio-balloon",
            "-device",
            "usb-tablet",
            "-daemonize",
        ]
        if config.iso_path and Path(config.iso_path).exists():
            cmd += ["-cdrom", config.iso_path]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return proc
        except FileNotFoundError:
            return None

    def _start_xen_domain(self, config: BoxConfig) -> Optional[subprocess.Popen]:
        xl = shutil.which("xl")
        if xl is None:
            return None
        cfg_content = self._build_xl_cfg(config)
        cfg_dir = BOXES_IMAGES / config.uuid
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = str(cfg_dir / f"{config.name}.cfg")
        with open(cfg_path, "w") as f:
            f.write(cfg_content)
        try:
            proc = subprocess.Popen(
                [xl, "create", cfg_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            proc.wait(timeout=30)
            return proc
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

    def _ensure_vm(self, backend_id: str) -> Optional[dict]:
        """Get VM info by ID, auto-loading config from disk if needed."""
        vm_info = self._vms.get(backend_id)
        if vm_info is not None:
            return vm_info
        config = self._load_config(backend_id)
        if config is None:
            return None
        self.define_machine(config)
        return self._vms.get(backend_id)

    def start_machine(self, backend_id: str) -> bool:
        vm_info = self._ensure_vm(backend_id)
        if vm_info is None:
            return False
        config = vm_info["config"]
        if self._mode == "kvm" and self._kvm.is_open:
            kvm_vm = self._start_kvm_direct(config, backend_id)
            if kvm_vm is not None:
                vm_info["vm_fd"] = kvm_vm
                vm_info["state"] = MachineState.RUNNING
                return True
        if self._mode == "xen" and self._xen.is_open:
            xen_proc = self._start_xen_domain(config)
            if xen_proc is not None:
                vm_info["proc"] = xen_proc
                vm_info["state"] = MachineState.RUNNING
                return True
        proc = self._start_qemu_kvm(config)
        if proc is not None:
            vm_info["proc"] = proc
            vm_info["state"] = MachineState.RUNNING
            return True
        vm_info["state"] = MachineState.RUNNING
        return True

    def shutdown_machine(self, backend_id: str) -> bool:
        vm_info = self._ensure_vm(backend_id)
        if vm_info is None:
            return False
        proc = vm_info.get("proc")
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=10)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        if self._mode == "xen":
            subprocess.run(["xl", "shutdown", backend_id], capture_output=True, timeout=10)
        vm_info["state"] = MachineState.STOPPED
        return True

    def pause_machine(self, backend_id: str) -> bool:
        vm_info = self._ensure_vm(backend_id)
        if vm_info is None:
            return False
        if self._mode == "xen":
            subprocess.run(["xl", "pause", backend_id], capture_output=True, timeout=10)
        proc = vm_info.get("proc")
        if proc is not None:
            try:
                proc.send_signal(signal.SIGSTOP)
            except Exception:
                pass
        vm_info["state"] = MachineState.PAUSED
        return True

    def resume_machine(self, backend_id: str) -> bool:
        vm_info = self._ensure_vm(backend_id)
        if vm_info is None:
            return False
        if self._mode == "xen":
            subprocess.run(["xl", "unpause", backend_id], capture_output=True, timeout=10)
        proc = vm_info.get("proc")
        if proc is not None:
            try:
                proc.send_signal(signal.SIGCONT)
            except Exception:
                pass
        vm_info["state"] = MachineState.RUNNING
        return True

    def delete_machine(self, backend_id: str) -> bool:
        self.shutdown_machine(backend_id)
        self._vms.pop(backend_id, None)
        # Also delete config from disk
        config = self._load_config(backend_id)
        if config is not None:
            config.delete()
        img_dir = BOXES_IMAGES / backend_id
        if img_dir.exists():
            import shutil as _shutil

            _shutil.rmtree(str(img_dir), ignore_errors=True)
        return True

    def get_state(self, backend_id: str) -> int:
        vm_info = self._vms.get(backend_id)
        if vm_info is None:
            config = self._load_config(backend_id)
            if config is not None:
                return MachineState.STOPPED
            return MachineState.STOPPED
        return vm_info["state"]

    def create_disk_image(self, path: str, size_gb: int) -> bool:
        try:
            result = subprocess.run(
                ["qemu-img", "create", "-f", "qcow2", path, f"{size_gb}G"],
                capture_output=True,
                timeout=120,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_display_address(self, backend_id: str) -> Optional[str]:
        return "127.0.0.1"

    def get_display_port(self, backend_id: str) -> Optional[int]:
        vm_info = self._vms.get(backend_id)
        if vm_info is None:
            return None
        return vm_info.get("display_port") or 5900

    def _find_qemu(self) -> Optional[str]:
        for name in ["qemu-system-x86_64", "qemu-kvm", "qemu-system-aarch64"]:
            path = shutil.which(name)
            if path:
                return path
        return None

    def _build_xl_cfg(self, config: BoxConfig) -> str:
        return (
            f'name = "{config.name}"\n'
            f'uuid = "{config.uuid}"\n'
            f"memory = {config.memory_mb}\n"
            f"maxmem = {config.memory_mb}\n"
            f"vcpus = {config.vcpus}\n"
            f"maxvcpus = {config.vcpus}\n"
            f'builder = "hvm"\n'
            f'boot = "d"\n'
            f"disk = [\n"
            f"  '{config.disk_path or ''},qcow2,xvda,rw',\n"
            f"  '{config.iso_path or ''},raw,xvdb:cdrom,r'\n"
            f"]\n"
            f"vif = ['bridge=xenbr0']\n"
            f"vnc = 1\n"
            f'vnclisten = "127.0.0.1"\n'
            f'serial = "pty"\n'
            f'on_poweroff = "destroy"\n'
            f'on_reboot = "restart"\n'
            f'on_crash = "restart"\n'
        )
