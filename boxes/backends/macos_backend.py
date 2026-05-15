from typing import Optional
import subprocess

from boxes.backends import BaseBackend
from boxes.models.config import BoxConfig
from boxes.models.machine import MachineState
from boxes.constants import BOXES_IMAGES


class MacOSBackend(BaseBackend):
    def __init__(self) -> None:
        super().__init__()
        self.capabilities.snapshots = False
        self.capabilities.usb_redirection = False
        self.capabilities.shared_folders = False
        self.capabilities.networks = True
        self._connected = False
        self._vms: dict[str, dict] = {}

    def _run(self, cmd: list[str]) -> Optional[str]:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None

    def _check_hvf(self) -> bool:
        result = self._run(["sysctl", "-n", "kern.hv_support"])
        return result == "1"

    def _check_qemu_hvf(self) -> Optional[str]:
        for binary in ["qemu-system-x86_64", "qemu-system-aarch64"]:
            path = self._which(binary)
            if path:
                result = self._run([path, "-accel", "hvf", "-machine", "help"])
                if result is not None:
                    return path
        return None

    def connect(self) -> bool:
        if self._check_hvf():
            qemu = self._check_qemu_hvf()
            if qemu is not None:
                self._qemu_binary = qemu
                self._connected = True
                return True
        if self._which("qemu-system-x86_64"):
            self._qemu_binary = "qemu-system-x86_64"
            self._connected = True
            return True
        return False

    def disconnect(self) -> None:
        for vm_info in self._vms.values():
            proc = vm_info.get("proc")
            if proc is not None:
                try:
                    proc.terminate()
                except Exception:
                    pass
        self._vms.clear()
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def list_machines(self) -> list[dict]:
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
            "proc": None,
            "display_port": None,
        }
        return config.uuid

    def undefine_machine(self, backend_id: str) -> bool:
        self._vms.pop(backend_id, None)
        return True

    def _get_display_port(self) -> int:
        import socket as _socket

        with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    def start_machine(self, backend_id: str) -> bool:
        vm_info = self._vms.get(backend_id)
        if vm_info is None:
            return False
        config = vm_info["config"]
        binary = getattr(self, "_qemu_binary", "qemu-system-x86_64")
        display_port = self._get_display_port()
        cmd = [
            binary,
            "-name",
            config.name,
            "-machine",
            f"type={config.machine_type},accel=hvf:tcg",
            "-cpu",
            "host",
            "-m",
            str(config.memory_mb),
            "-smp",
            str(config.vcpus),
            "-drive",
            f"file={config.disk_path},format=qcow2,if=virtio",
            "-netdev",
            "vmnet-modeswitch,id=net0",
            "-device",
            "virtio-net-pci,netdev=net0",
            "-vnc",
            f"127.0.0.1:{display_port}",
            "-vga",
            "virtio",
            "-display",
            "default,show-cursor=on",
            "-usb",
            "-device",
            "usb-tablet",
            "-daemonize",
        ]
        if config.iso_path:
            cmd += ["-cdrom", config.iso_path]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            vm_info["proc"] = proc
            vm_info["display_port"] = display_port
            vm_info["state"] = MachineState.RUNNING
            return True
        except FileNotFoundError:
            return False

    def shutdown_machine(self, backend_id: str) -> bool:
        vm_info = self._vms.get(backend_id)
        if vm_info is None:
            return False
        proc = vm_info.get("proc")
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        vm_info["state"] = MachineState.STOPPED
        return True

    def pause_machine(self, backend_id: str) -> bool:
        vm_info = self._vms.get(backend_id)
        if vm_info is None:
            return False
        import signal as _signal

        proc = vm_info.get("proc")
        if proc is not None:
            try:
                proc.send_signal(_signal.SIGSTOP)
            except Exception:
                return False
        vm_info["state"] = MachineState.PAUSED
        return True

    def resume_machine(self, backend_id: str) -> bool:
        vm_info = self._vms.get(backend_id)
        if vm_info is None:
            return False
        import signal as _signal

        proc = vm_info.get("proc")
        if proc is not None:
            try:
                proc.send_signal(_signal.SIGCONT)
            except Exception:
                return False
        vm_info["state"] = MachineState.RUNNING
        return True

    def delete_machine(self, backend_id: str) -> bool:
        self.shutdown_machine(backend_id)
        self._vms.pop(backend_id, None)
        img_dir = BOXES_IMAGES / backend_id
        if img_dir.exists():
            import shutil

            shutil.rmtree(str(img_dir), ignore_errors=True)
        return True

    def get_state(self, backend_id: str) -> int:
        vm_info = self._vms.get(backend_id)
        if vm_info is None:
            return MachineState.STOPPED
        return vm_info["state"]

    def create_disk_image(self, path: str, size_gb: int) -> bool:
        try:
            result = subprocess.run(
                ["qemu-img", "create", "-f", "qcow2", path, f"{size_gb}G"], capture_output=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def get_display_address(self, backend_id: str) -> Optional[str]:
        return "127.0.0.1"

    def get_display_port(self, backend_id: str) -> Optional[int]:
        vm_info = self._vms.get(backend_id)
        if vm_info is None:
            return None
        return vm_info.get("display_port")

    @staticmethod
    def _which(name: str) -> Optional[str]:
        import shutil

        return shutil.which(name)
