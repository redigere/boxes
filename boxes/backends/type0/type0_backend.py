from __future__ import annotations

import json
import signal
import subprocess
import shutil
import ctypes
import threading
from pathlib import Path
from typing import Optional, Any

from boxes.backends import BaseBackend
from boxes.backends.type0.kvm_device import KVMDevice
from boxes.backends.type0.xen_device import XenDevice
from boxes.models.config import BoxConfig
from boxes.models.machine import MachineState
from boxes.constants import BOXES_IMAGES, BOXES_CONFIG
from boxes.services.container import PodmanManager


class Type0Backend(BaseBackend):
    def __init__(self) -> None:
        super().__init__()
        self._kvm = KVMDevice()
        self._xen = XenDevice()
        self._podman = PodmanManager()
        self._mode: str = ""
        self._vms: dict[str, dict[str, Any]] = {}
        self._vm_fds: dict[str, int] = {}
        self._guest_mem: dict[str, Any] = {}
        self._vcpu_threads: dict[str, list[threading.Thread]] = {}
        self._stop_events: dict[str, threading.Event] = {}

    @property
    def _state_path(self) -> Path:
        return BOXES_CONFIG / "type0.state"

    def _save_state(self) -> None:
        data: dict[str, int] = {}
        for uid, info in self._vms.items():
            data[uid] = info.get("state", MachineState.STOPPED)
        BOXES_CONFIG.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps(data, indent=2))

    def _load_state(self) -> dict[str, int]:
        if not self._state_path.exists():
            return {}
        try:
            return json.loads(self._state_path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _load_existing_vms(self) -> None:
        from boxes.models.config import BoxConfig as _BoxConfig

        saved_states = self._load_state()
        for cfg in _BoxConfig.list_all():
            if cfg.uuid not in self._vms:
                self.define_machine(cfg)
                if cfg.uuid in saved_states and cfg.uuid in self._vms:
                    self._vms[cfg.uuid]["state"] = saved_states[cfg.uuid]

    def connect(self) -> bool:
        if self._kvm.probe():
            if self._kvm.open():
                self._mode = "kvm"
                self._connected = True
                self._load_existing_vms()
                self._podman.ensure_wrappers()
                return True
            if Path("/dev/kvm").exists():
                self._mode = "kvm"
                self._connected = True
                self._load_existing_vms()
                self._podman.ensure_wrappers()
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
        self._save_state()
        for uid in list(self._vms.keys()):
            self.shutdown_machine(uid)
        self._kvm.close()
        self._xen.close()
        self._vms.clear()
        self._vm_fds.clear()
        self._guest_mem.clear()
        self._vcpu_threads.clear()
        self._stop_events.clear()
        self._connected = False

    def list_machines(self) -> list[dict[str, Any]]:
        if self._mode == "xen" and self._xen.is_open:
            result = subprocess.run(
                ["xl", "list"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                machines: list[dict[str, Any]] = []
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
                "state": info.get("state", MachineState.STOPPED),
                "active": info.get("state") == MachineState.RUNNING,
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
        self._vm_fds.pop(backend_id, None)
        self._guest_mem.pop(backend_id, None)
        self._vcpu_threads.pop(backend_id, None)
        self._stop_events.pop(backend_id, None)
        return True

    @staticmethod
    def _load_config(backend_id: str) -> Optional[BoxConfig]:
        from boxes.models.config import BoxConfig as _BoxConfig

        for c in _BoxConfig.list_all():
            if c.uuid == backend_id:
                return c
        return None

    def _ensure_vm(self, backend_id: str) -> Optional[dict[str, Any]]:
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
        config: BoxConfig = vm_info["config"]

        result = self._start_qemu_kvm(config, backend_id)
        if result is not None:
            proc, display_port = result
            vm_info["proc"] = proc
            vm_info["display_port"] = display_port
            vm_info["state"] = MachineState.RUNNING
            self._save_state()
            return True

        if self._mode == "xen" and self._xen.is_open:
            xen_proc = self._start_xen_domain(config)
            if xen_proc is not None:
                vm_info["proc"] = xen_proc
                vm_info["state"] = MachineState.RUNNING
                self._save_state()
                return True

        if self._mode == "kvm" and self._kvm.is_open:
            kvm_vm = self._start_kvm_direct(config, backend_id)
            if kvm_vm is not None:
                vm_info["vm_fd"] = kvm_vm
                vm_info["state"] = MachineState.RUNNING
                self._save_state()
                return True

        vm_info["state"] = MachineState.RUNNING
        self._save_state()
        return False

    def shutdown_machine(self, backend_id: str) -> bool:
        vm_info = self._ensure_vm(backend_id)
        if vm_info is None:
            return False

        self._stop_vcpu_threads(backend_id)
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
        else:
            qemu_pid = self._find_qemu_in_container(backend_id)
            if qemu_pid is not None:
                self._podman.exec(["kill", str(qemu_pid)], timeout=10)

        if self._mode == "xen":
            subprocess.run(
                ["xl", "shutdown", backend_id],
                capture_output=True,
                timeout=10,
            )

        vm_info["state"] = MachineState.STOPPED
        self._save_state()
        return True

    def pause_machine(self, backend_id: str) -> bool:
        vm_info = self._ensure_vm(backend_id)
        if vm_info is None:
            return False
        if self._mode == "xen":
            subprocess.run(
                ["xl", "pause", backend_id], capture_output=True, timeout=10
            )
        proc = vm_info.get("proc")
        if proc is not None:
            try:
                proc.send_signal(signal.SIGSTOP)
            except Exception:
                pass
        vm_info["state"] = MachineState.PAUSED
        self._save_state()
        return True

    def resume_machine(self, backend_id: str) -> bool:
        vm_info = self._ensure_vm(backend_id)
        if vm_info is None:
            return False
        if self._mode == "xen":
            subprocess.run(
                ["xl", "unpause", backend_id], capture_output=True, timeout=10
            )
        proc = vm_info.get("proc")
        if proc is not None:
            try:
                proc.send_signal(signal.SIGCONT)
            except Exception:
                pass
        vm_info["state"] = MachineState.RUNNING
        self._save_state()
        return True

    def get_state(self, backend_id: str) -> int:
        vm_info = self._vms.get(backend_id)
        if vm_info is None:
            config = self._load_config(backend_id)
            if config is not None:
                return MachineState.STOPPED
            return MachineState.STOPPED
        return vm_info.get("state", MachineState.STOPPED)

    def delete_machine(self, backend_id: str, keep_disks: bool = False) -> bool:
        self.shutdown_machine(backend_id)
        self._vms.pop(backend_id, None)
        self._vm_fds.pop(backend_id, None)
        self._guest_mem.pop(backend_id, None)
        self._vcpu_threads.pop(backend_id, None)
        self._stop_events.pop(backend_id, None)

        config = self._load_config(backend_id)
        if config is not None:
            config.delete()

        if not keep_disks:
            img_dir = BOXES_IMAGES / backend_id
            if img_dir.exists():
                shutil.rmtree(str(img_dir), ignore_errors=True)

        self._save_state()
        return True

    def create_disk_image(self, path: str, size_gb: int) -> bool:
        qemu_img = shutil.which("qemu-img")
        if qemu_img is None:
            qemu_img = self._auto_install_qemu()
            if qemu_img is None:
                return False
        try:
            result = subprocess.run(
                [qemu_img, "create", "-f", "qcow2", path, f"{size_gb}G"],
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
        return vm_info.get("display_port")

    def _start_kvm_direct(
        self, config: BoxConfig, backend_id: str = ""
    ) -> Optional[int]:
        if not self._kvm.is_open:
            return None
        vm_fd = self._kvm.create_vm()
        if vm_fd is None:
            return None

        mem_size = config.memory_mb * 1024 * 1024
        mem = ctypes.create_string_buffer(mem_size)
        host_addr = ctypes.addressof(mem)
        self._kvm.set_user_memory_region(vm_fd, 0, mem_size, host_addr, 0)

        firmware = self._find_firmware()
        if firmware:
            try:
                fw_data = firmware.read_bytes()
                fw_size = min(len(fw_data), mem_size)
                ctypes.memmove(mem, fw_data, fw_size)
            except (OSError, PermissionError):
                pass

        try:
            try:
                import fcntl

                fcntl.ioctl(vm_fd, 0xAE47, 0xFFFBD000)
            except (OSError, ImportError):
                pass

            try:
                fcntl.ioctl(vm_fd, 0xAE60, 0)
            except OSError:
                pass

            num_vcpus = min(config.vcpus, 256)
            for i in range(num_vcpus):
                self._kvm.create_vcpu(vm_fd, i)

            if backend_id:
                self._vm_fds[backend_id] = vm_fd
                self._guest_mem[backend_id] = mem
                self._launch_vcpu_threads(backend_id, vm_fd, num_vcpus)
        except Exception:
            pass

        return vm_fd

    def _find_firmware(self) -> Optional[Path]:
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

    def _launch_vcpu_threads(
        self, backend_id: str, vm_fd: int, num_vcpus: int
    ) -> None:
        stop_event = threading.Event()
        self._stop_events[backend_id] = stop_event
        threads: list[threading.Thread] = []
        for i in range(num_vcpus):
            t = threading.Thread(
                target=self._run_kvm_vcpu,
                args=(backend_id, i, stop_event),
                daemon=True,
            )
            t.start()
            threads.append(t)
        self._vcpu_threads[backend_id] = threads

    def _stop_vcpu_threads(self, backend_id: str) -> None:
        stop_event = self._stop_events.pop(backend_id, None)
        if stop_event:
            stop_event.set()
        threads = self._vcpu_threads.pop(backend_id, [])
        for t in threads:
            t.join(timeout=2.0)

    def _run_kvm_vcpu(
        self, backend_id: str, vcpu_id: int, stop_event: threading.Event
    ) -> None:
        vm_fd = self._vm_fds.get(backend_id)
        if vm_fd is None:
            return
        try:
            import fcntl
            import struct

            vcpu_fd = fcntl.ioctl(vm_fd, 0x4020AE41, vcpu_id)
            kvm_run_mmap_size = 16384

            while not stop_event.is_set():
                try:
                    fcntl.ioctl(vcpu_fd, 0xAE80, 0)
                except OSError as e:
                    if e.errno == 4:
                        continue
                    if e.errno == 9:
                        break
                    break

                try:
                    import mmap

                    run_mmap = mmap.mmap(
                        vcpu_fd,
                        kvm_run_mmap_size,
                        mmap.MAP_SHARED,
                        mmap.PROT_READ | mmap.PROT_WRITE,
                    )
                    exit_reason = struct.unpack_from("I", run_mmap, 0)[0]
                    run_mmap.close()
                except Exception:
                    break

                if exit_reason == 8:
                    break
                elif exit_reason == 5:
                    continue
                elif exit_reason == 6:
                    continue
                elif exit_reason == 0x100:
                    break
                elif exit_reason == 0x200:
                    break
                elif exit_reason == 0x400:
                    break
                else:
                    continue
        except (OSError, ImportError):
            pass

    def _start_qemu_kvm(
        self, config: BoxConfig, backend_id: str = ""
    ) -> Optional[tuple[subprocess.Popen, int]]:
        qemu = self._find_qemu()
        if qemu is None:
            qemu = self._auto_install_qemu()
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
            "pc-q35-9.2,accel=kvm:tcg",
            "-cpu",
            "host",
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
            "std",
            "-device",
            "virtio-balloon",
            "-device",
            "piix3-usb-uhci",
            "-device",
            "usb-tablet",
        ]
        if config.iso_path and Path(config.iso_path).exists():
            cmd += ["-cdrom", config.iso_path]
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            if backend_id:
                vm_info = self._vms.get(backend_id)
                if vm_info is not None:
                    vm_info["display_port"] = display_port
            return (proc, display_port)
        except FileNotFoundError:
            return None

    def _find_qemu(self) -> Optional[str]:
        path = self._podman.get_qemu_path()
        if path:
            return path
        for name in [
            "qemu-system-x86_64",
            "qemu-kvm",
            "qemu-system-aarch64",
        ]:
            path = shutil.which(name)
            if path:
                return path
        return None

    def _find_qemu_in_container(self, backend_id: str) -> Optional[int]:
        if not backend_id:
            return None
        return self._podman.find_qemu_pid(backend_id[:8])

    def _auto_install_qemu(self) -> Optional[str]:
        local_qemu = BOXES_IMAGES / ".qemu" / "qemu-system-x86_64"
        local_qemu_img = BOXES_IMAGES / ".qemu" / "qemu-img"
        if local_qemu_img.exists() and local_qemu.exists():
            return str(local_qemu)

        if shutil.which("apt"):
            import subprocess as _sp

            try:
                _sp.run(
                    ["apt", "install", "-y", "qemu-system-x86", "qemu-utils"],
                    capture_output=True,
                    timeout=300,
                )
                path = shutil.which("qemu-system-x86_64")
                if path:
                    return path
            except Exception:
                pass
        elif shutil.which("dnf"):
            import subprocess as _sp

            try:
                _sp.run(
                    ["dnf", "install", "-y", "qemu-system-x86", "qemu-img"],
                    capture_output=True,
                    timeout=300,
                )
                path = shutil.which("qemu-system-x86_64")
                if path:
                    return path
            except Exception:
                pass

        qemu_dir = BOXES_IMAGES / ".qemu"
        qemu_dir.mkdir(parents=True, exist_ok=True)
        url = (
            "https://github.com/musescore/QEMU-static/releases/download/v9.2.0/"
            "qemu-system-x86_64"
        )
        url_img = (
            "https://github.com/musescore/QEMU-static/releases/download/v9.2.0/"
            "qemu-img"
        )
        try:
            from boxes.util import download_file

            for dest_url, dest_path in [
                (url, str(local_qemu)),
                (url_img, str(local_qemu_img)),
            ]:
                download_file(dest_url, dest_path)
            local_qemu.chmod(0o755)
            local_qemu_img.chmod(0o755)
            return str(local_qemu)
        except Exception:
            return None

    def _start_xen_domain(
        self, config: BoxConfig
    ) -> Optional[subprocess.Popen]:
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
                [xl, "create", cfg_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            proc.wait(timeout=30)
            return proc
        except (FileNotFoundError, subprocess.TimeoutExpired):
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
