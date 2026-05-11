from typing import Optional
import subprocess
import re

from boxes.backends import BaseBackend
from boxes.models.config import BoxConfig
from boxes.models.machine import MachineState


class SSHBackend(BaseBackend):
    def __init__(self, host: str, port: int = 22, user: str = "root") -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.user = user
        self.capabilities.snapshots = True
        self._connected = False

    def _ssh(self, cmd: str) -> Optional[str]:
        try:
            result = subprocess.run(
                ["ssh", "-p", str(self.port), f"{self.user}@{self.host}", cmd],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def connect(self) -> bool:
        result = self._ssh("virsh list --all")
        self._connected = result is not None
        return self._connected

    def disconnect(self) -> None:
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def list_machines(self) -> list[dict]:
        out = self._ssh("virsh list --all --uuid --name --state")
        if out is None:
            return []
        results = []
        for line in out.split("\n"):
            parts = line.strip().split()
            if len(parts) >= 3:
                results.append({
                    "uuid": parts[0],
                    "name": parts[1],
                    "state": 1 if parts[2] == "running" else 0,
                    "active": parts[2] == "running",
                })
        return results

    def define_machine(self, config: BoxConfig) -> Optional[str]:
        return config.uuid

    def undefine_machine(self, backend_id: str) -> bool:
        dom = self._ssh(f"virsh dominfo {backend_id} 2>/dev/null && echo EXISTS")
        if dom is None:
            return True
        result = self._ssh(f"virsh undefine {backend_id}")
        return result is not None

    def start_machine(self, backend_id: str) -> bool:
        result = self._ssh(f"virsh start {backend_id}")
        return result is not None

    def shutdown_machine(self, backend_id: str) -> bool:
        result = self._ssh(f"virsh shutdown {backend_id}")
        return result is not None

    def pause_machine(self, backend_id: str) -> bool:
        result = self._ssh(f"virsh suspend {backend_id}")
        return result is not None

    def resume_machine(self, backend_id: str) -> bool:
        result = self._ssh(f"virsh resume {backend_id}")
        return result is not None

    def delete_machine(self, backend_id: str) -> bool:
        self._ssh(f"virsh destroy {backend_id} 2>/dev/null")
        result = self._ssh(f"virsh undefine {backend_id} --remove-all-storage")
        return result is not None

    def get_state(self, backend_id: str) -> int:
        state = self._ssh(f"virsh domstate {backend_id}")
        if state is None:
            return MachineState.STOPPED
        state = state.lower()
        if "running" in state:
            return MachineState.RUNNING
        if "paused" in state or "suspended" in state:
            return MachineState.PAUSED
        if "shut" in state:
            return MachineState.STOPPED
        return MachineState.STOPPED

    def create_disk_image(self, path: str, size_gb: int) -> bool:
        result = self._ssh(f"qemu-img create -f qcow2 {path} {size_gb}G")
        return result is not None

    def get_display_address(self, backend_id: str) -> Optional[str]:
        return self.host

    def get_display_port(self, backend_id: str) -> Optional[int]:
        xml = self._ssh(f"virsh dumpxml {backend_id}")
        if xml is None:
            return None
        match = re.search(r"port='(\d+)'", xml)
        if match:
            return int(match.group(1))
        return None
