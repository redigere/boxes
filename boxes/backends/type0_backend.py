from typing import Optional
import os
import signal
import struct
import fcntl
import ctypes
import subprocess
import shutil
from pathlib import Path

from boxes.backends import BaseBackend
from boxes.models.config import BoxConfig
from boxes.models.machine import MachineState
from boxes.constants import BOXES_IMAGES


KVM_API_VERSION = 12
KVM_GET_API_VERSION = 0xAE00
KVM_CREATE_VM = 0x4020AE01
KVM_CHECK_EXTENSION = 0xAE03
KVM_CREATE_VCPU = 0x4020AE41
KVM_SET_USER_MEMORY_REGION = 0x4020AE46
KVM_RUN = 0xAE80
KVM_GET_VCPU_MMAP_SIZE = 0xAE04
KVM_SET_TSS_ADDR = 0xAE47
KVM_CREATE_IRQCHIP = 0xAE60
KVM_CAP_MAX_VCPUS = 66
KVM_CAP_USER_MEMORY = 5

XEN_DEV_PRIVCMD = "/dev/xen/privcmd"
XEN_DEV_EVTCHN = "/dev/xen/evtchn"
XEN_DEV_GNTTAB = "/dev/xen/gnttab"


class KVMDevice:
    def __init__(self) -> None:
        self._kvm_fd: Optional[int] = None
        self._vm_fd: Optional[int] = None
        self._vcpu_fd: Optional[int] = None
        self._vcpu_mmap_size: int = 0

    def probe(self) -> bool:
        return Path("/dev/kvm").exists()

    def open(self) -> bool:
        try:
            fd = os.open("/dev/kvm", os.O_RDWR | os.O_CLOEXEC)
        except (OSError, PermissionError):
            return False
        try:
            version = fcntl.ioctl(fd, KVM_GET_API_VERSION, 0)
            if version != KVM_API_VERSION:
                os.close(fd)
                return False
            self._kvm_fd = fd
            return True
        except OSError:
            os.close(fd)
            return False

    def close(self) -> None:
        for fd in (self._vcpu_fd, self._vm_fd, self._kvm_fd):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
        self._kvm_fd = None
        self._vm_fd = None
        self._vcpu_fd = None

    @property
    def is_open(self) -> bool:
        return self._kvm_fd is not None

    def create_vm(self) -> Optional[int]:
        if self._kvm_fd is None:
            return None
        try:
            vm_fd = fcntl.ioctl(self._kvm_fd, KVM_CREATE_VM, 0)
            self._vm_fd = vm_fd
            return vm_fd
        except OSError:
            return None

    def create_vcpu(self, vm_fd: int, vcpu_id: int = 0) -> Optional[int]:
        try:
            vcpu_fd = fcntl.ioctl(vm_fd, KVM_CREATE_VCPU, vcpu_id)
            self._vcpu_fd = vcpu_fd
            if self._vcpu_mmap_size == 0 and self._kvm_fd is not None:
                self._vcpu_mmap_size = fcntl.ioctl(self._kvm_fd, KVM_GET_VCPU_MMAP_SIZE, 0)
            return vcpu_fd
        except OSError:
            return None

    def set_user_memory_region(
        self, vm_fd: int, guest_paddr: int, mem_size: int, host_addr: int, slot: int = 0
    ) -> bool:
        region = struct.pack("IIQII", slot, guest_paddr >> 16, host_addr, mem_size, 0)
        try:
            fcntl.ioctl(vm_fd, KVM_SET_USER_MEMORY_REGION, region)
            return True
        except OSError:
            return False

    def check_capability(self, cap: int) -> bool:
        if self._kvm_fd is None:
            return False
        try:
            return fcntl.ioctl(self._kvm_fd, KVM_CHECK_EXTENSION, cap) > 0
        except OSError:
            return False


class XenDevice:
    def __init__(self) -> None:
        self._privcmd_fd: Optional[int] = None
        self._xc: Optional[ctypes.CDLL] = None

    def probe(self) -> bool:
        if Path(XEN_DEV_PRIVCMD).exists():
            return True
        for lib in ("libxenctrl.so.4.17", "libxenctrl.so.4.16", "libxenctrl.so"):
            try:
                ctypes.CDLL(lib)
                return True
            except OSError:
                continue
        return False

    def open(self) -> bool:
        try:
            self._privcmd_fd = os.open(XEN_DEV_PRIVCMD, os.O_RDWR | os.O_CLOEXEC)
            return True
        except (OSError, FileNotFoundError, PermissionError):
            pass
        for lib in ("libxenctrl.so.4.17", "libxenctrl.so.4.16", "libxenctrl.so"):
            try:
                self._xc = ctypes.CDLL(lib)
                return True
            except OSError:
                continue
        return False

    def close(self) -> None:
        if self._privcmd_fd is not None:
            try:
                os.close(self._privcmd_fd)
            except OSError:
                pass
            self._privcmd_fd = None
        self._xc = None

    @property
    def is_open(self) -> bool:
        return self._privcmd_fd is not None or self._xc is not None


class Type0Backend(BaseBackend):
    def __init__(self) -> None:
        super().__init__()
        self._kvm = KVMDevice()
        self._xen = XenDevice()
        self._mode: str = ""
        self._vms: dict[str, dict] = {}

    def connect(self) -> bool:
        if self._kvm.probe():
            if self._kvm.open():
                self._mode = "kvm"
                self._connected = True
                return True
            if Path("/dev/kvm").exists():
                self._mode = "kvm"
                self._connected = True
                return True
        if self._xen.probe():
            if self._xen.open():
                self._mode = "xen"
                self._connected = True
                return True
            self._mode = "xen"
            self._connected = True
            return True
        return False

    def disconnect(self) -> None:
        for uid in list(self._vms.keys()):
            self.shutdown_machine(uid)
        self._kvm.close()
        self._xen.close()
        self._vms.clear()
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

    def _start_kvm_direct(self, config: BoxConfig) -> Optional[int]:
        if not self._kvm.is_open:
            return None
        vm_fd = self._kvm.create_vm()
        if vm_fd is None:
            return None
        mem_size = config.memory_mb * 1024 * 1024
        mem = ctypes.create_string_buffer(mem_size)
        self._kvm.set_user_memory_region(vm_fd, 0, mem_size, ctypes.addressof(mem), 0)
        return vm_fd

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

    def start_machine(self, backend_id: str) -> bool:
        vm_info = self._vms.get(backend_id)
        if vm_info is None:
            return False
        config = vm_info["config"]
        if self._mode == "kvm" and self._kvm.is_open:
            kvm_vm = self._start_kvm_direct(config)
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
        vm_info = self._vms.get(backend_id)
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
        vm_info = self._vms.get(backend_id)
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
        vm_info = self._vms.get(backend_id)
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
        img_dir = BOXES_IMAGES / backend_id
        if img_dir.exists():
            import shutil as _shutil

            _shutil.rmtree(str(img_dir), ignore_errors=True)
        return True

    def get_state(self, backend_id: str) -> int:
        vm_info = self._vms.get(backend_id)
        if vm_info is None:
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
