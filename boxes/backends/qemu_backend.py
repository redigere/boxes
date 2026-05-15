from typing import Optional
import subprocess
import time
from pathlib import Path

from boxes.backends import BaseBackend
from boxes.backends.qemu_process import QEMUProcess
from boxes.models.config import BoxConfig
from boxes.models.machine import MachineState
from boxes.constants import BOXES_IMAGES


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
