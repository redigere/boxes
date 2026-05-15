from typing import Optional
import subprocess
import socket
import os
import signal
import time
from pathlib import Path

from boxes.backends import BaseBackend
from boxes.models.config import BoxConfig
from boxes.models.machine import MachineState
from boxes.constants import QEMU_BINARIES, BOXES_IMAGES


class QEMUProcess:
    def __init__(self, config: BoxConfig) -> None:
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.monitor_port: Optional[int] = None
        self.display_port: Optional[int] = None
        self.qmp_socket: Optional[str] = None

    def build_command(self) -> list[str]:
        binary = QEMU_BINARIES.get(self.config.arch, "qemu-system-x86_64")
        cmd = [binary]
        cmd += ["-name", self.config.name]
        cmd += ["-machine", f"{self.config.machine_type},accel=kvm:hax:whpx:tcg"]
        cmd += ["-cpu", self.config.cpu_model]
        cmd += ["-m", str(self.config.memory_mb)]
        cmd += ["-smp", str(self.config.vcpus)]
        cmd += [
            "-drive",
            f"file={self.config.disk_path},format=qcow2,if=virtio,aio=native,cache=unsafe",
        ]
        if self.config.iso_path and Path(self.config.iso_path).exists():
            cmd += ["-cdrom", self.config.iso_path]
        cmd += ["-netdev", "user,id=net0"]
        cmd += ["-device", "virtio-net-pci,netdev=net0"]
        if self.config.graphics == "spice":
            self.display_port = self._find_free_port()
            cmd += ["-spice", f"port={self.display_port},disable-ticketing=on"]
            cmd += ["-vga", "qxl"]
        else:
            self.display_port = self._find_free_port()
            cmd += ["-vnc", f"127.0.0.1:{self.display_port}"]
            cmd += ["-vga", "virtio"]
        cmd += ["-usb"]
        cmd += ["-device", "usb-tablet"]
        cmd += ["-device", "virtio-balloon"]
        self.monitor_port = self._find_free_port()
        cmd += ["-qmp", f"tcp:127.0.0.1:{self.monitor_port},server,nowait"]
        cmd += ["-daemonize"]
        return cmd

    def start(self) -> bool:
        cmd = self.build_command()
        disks_dir = BOXES_IMAGES / self.config.uuid
        disks_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(disks_dir)
            )
            if self.process.pid and self.process.pid > 0:
                return True
            return False
        except FileNotFoundError:
            return False

    def stop(self) -> bool:
        if self.process and self.process.pid:
            try:
                os.kill(self.process.pid, signal.SIGTERM)
                time.sleep(2)
                if self.process.poll() is None:
                    os.kill(self.process.pid, signal.SIGKILL)
                return True
            except Exception:
                return False
        return False

    def send_qmp(self, cmd: dict) -> Optional[dict]:
        import json

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect(("127.0.0.1", self.monitor_port))
            s.recv(1024)
            s.sendall(json.dumps({"execute": "qmp_capabilities"}).encode())
            s.recv(1024)
            s.sendall(json.dumps(cmd).encode())
            resp = s.recv(65536).decode()
            s.close()
            return json.loads(resp)
        except Exception:
            return None

    def query_status(self) -> Optional[str]:
        if self.process is None:
            return None
        ret = self.process.poll()
        if ret is not None:
            return "stopped"
        resp = self.send_qmp({"execute": "query-status"})
        if resp and "return" in resp:
            return resp["return"].get("status", "running").lower()
        return "running"

    def _find_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            return s.getsockname()[1]


class QEMUBackend(BaseBackend):
    def __init__(self) -> None:
        super().__init__()
        self.capabilities.snapshots = True
        self.capabilities.shared_folders = True
        self._processes: dict[str, QEMUProcess] = {}
        self._connected = True

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        for proc in self._processes.values():
            proc.stop()
        self._processes.clear()
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def list_machines(self) -> list[dict]:
        results = []
        for uuid, proc in self._processes.items():
            status = proc.query_status()
            results.append(
                {
                    "name": proc.config.name,
                    "uuid": uuid,
                    "state": 1 if status == "running" else 0,
                    "active": status == "running",
                }
            )
        return results

    def define_machine(self, config: BoxConfig) -> Optional[str]:
        proc = QEMUProcess(config)
        self._processes[config.uuid] = proc
        return config.uuid

    def undefine_machine(self, backend_id: str) -> bool:
        if backend_id in self._processes:
            proc = self._processes[backend_id]
            proc.stop()
            del self._processes[backend_id]
            return True
        return False

    def start_machine(self, backend_id: str) -> bool:
        proc = self._processes.get(backend_id)
        if proc is None:
            return False
        return proc.start()

    def shutdown_machine(self, backend_id: str) -> bool:
        proc = self._processes.get(backend_id)
        if proc is None:
            return False
        resp = proc.send_qmp({"execute": "system_powerdown"})
        if resp and "error" not in resp:
            time.sleep(1)
            if proc.query_status() == "stopped":
                return True
        return proc.stop()

    def pause_machine(self, backend_id: str) -> bool:
        proc = self._processes.get(backend_id)
        if proc is None:
            return False
        resp = proc.send_qmp({"execute": "stop"})
        return resp is not None and "error" not in resp

    def resume_machine(self, backend_id: str) -> bool:
        proc = self._processes.get(backend_id)
        if proc is None:
            return False
        resp = proc.send_qmp({"execute": "cont"})
        return resp is not None and "error" not in resp

    def delete_machine(self, backend_id: str) -> bool:
        self.undefine_machine(backend_id)
        img_dir = BOXES_IMAGES / backend_id
        if img_dir.exists():
            import shutil

            shutil.rmtree(str(img_dir), ignore_errors=True)
        return True

    def get_state(self, backend_id: str) -> int:
        proc = self._processes.get(backend_id)
        if proc is None:
            return MachineState.STOPPED
        status = proc.query_status()
        if status is None:
            return MachineState.STOPPED
        if status == "running":
            return MachineState.RUNNING
        if status == "paused":
            return MachineState.PAUSED
        if status == "shutdown" or status == "stopped":
            return MachineState.STOPPED
        return MachineState.STOPPED

    def create_disk_image(self, path: str, size_gb: int) -> bool:
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                ["qemu-img", "create", "-f", "qcow2", path, f"{size_gb}G"], capture_output=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def get_display_address(self, backend_id: str) -> Optional[str]:
        proc = self._processes.get(backend_id)
        if proc is None or proc.display_port is None:
            return None
        return "127.0.0.1"

    def get_display_port(self, backend_id: str) -> Optional[int]:
        proc = self._processes.get(backend_id)
        if proc is None:
            return None
        return proc.display_port

    def reboot_machine(self, backend_id: str) -> bool:
        proc = self._processes.get(backend_id)
        if proc is None:
            return False
        resp = proc.send_qmp({"execute": "system_reset"})
        return resp is not None and "error" not in resp
