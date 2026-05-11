from typing import Optional
import subprocess

from boxes.backends import BaseBackend
from boxes.models.config import BoxConfig
from boxes.models.machine import MachineState


class HyperVBackend(BaseBackend):
    def __init__(self) -> None:
        super().__init__()
        self.capabilities.snapshots = True
        self.capabilities.networks = True
        self.capabilities.usb_redirection = False
        self._connected = False
        self._vms: dict[str, dict] = {}

    def _ps(self, command: str) -> Optional[str]:
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", command],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def connect(self) -> bool:
        result = self._ps("Get-Module -ListAvailable Hyper-V | Select-Object -ExpandProperty Name")
        if result and "Hyper-V" in result:
            self._connected = True
            return True
        result = self._ps("Get-Command Get-VM -ErrorAction SilentlyContinue")
        self._connected = result is not None and "Get-VM" in result
        return self._connected

    def disconnect(self) -> None:
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def list_machines(self) -> list[dict]:
        out = self._ps("Get-VM | Select-Object Name,Id,State,MemoryStartup,CPUUsage | ConvertTo-Json")
        if out is None or out == "":
            return []
        results = []
        import json
        try:
            data = json.loads(out)
            if isinstance(data, dict):
                data = [data]
            for vm in data:
                state_str = vm.get("State", "Off")
                results.append({
                    "name": vm.get("Name", ""),
                    "uuid": vm.get("Id", ""),
                    "state": 1 if state_str == "Running" else 0,
                    "memory": vm.get("MemoryStartup", 0),
                    "active": state_str == "Running",
                })
        except (json.JSONDecodeError, TypeError):
            pass
        return results

    def define_machine(self, config: BoxConfig) -> Optional[str]:
        self._vms[config.uuid] = {
            "config": config,
            "state": MachineState.STOPPED,
        }
        ps_cmd = (
            f"New-VM -Name '{config.name}' -MemoryStartupBytes {config.memory_mb}MB "
            f"-Generation 2 "
            f"-BootDevice VHD"
        )
        if config.iso_path:
            ps_cmd += f"; Add-VMDvdDrive -VMName '{config.name}' -Path '{config.iso_path}'"
        self._ps(ps_cmd)
        if config.vcpus > 1:
            self._ps(f"Set-VM -Name '{config.name}' -ProcessorCount {config.vcpus}")
        return config.uuid

    def undefine_machine(self, backend_id: str) -> bool:
        self._vms.pop(backend_id, None)
        return True

    def start_machine(self, backend_id: str) -> bool:
        vm_info = self._vms.get(backend_id)
        if vm_info is None:
            return False
        name = vm_info["config"].name
        result = self._ps(f"Start-VM -Name '{name}'")
        if result is not None:
            vm_info["state"] = MachineState.RUNNING
            return True
        return False

    def shutdown_machine(self, backend_id: str) -> bool:
        vm_info = self._vms.get(backend_id)
        if vm_info is None:
            return False
        name = vm_info["config"].name
        result = self._ps(f"Stop-VM -Name '{name}' -Force")
        if result is not None:
            vm_info["state"] = MachineState.STOPPED
            return True
        return False

    def pause_machine(self, backend_id: str) -> bool:
        vm_info = self._vms.get(backend_id)
        if vm_info is None:
            return False
        name = vm_info["config"].name
        result = self._ps(f"Suspend-VM -Name '{name}'")
        if result is not None:
            vm_info["state"] = MachineState.PAUSED
            return True
        return False

    def resume_machine(self, backend_id: str) -> bool:
        vm_info = self._vms.get(backend_id)
        if vm_info is None:
            return False
        name = vm_info["config"].name
        result = self._ps(f"Resume-VM -Name '{name}'")
        if result is not None:
            vm_info["state"] = MachineState.RUNNING
            return True
        return False

    def delete_machine(self, backend_id: str) -> bool:
        vm_info = self._vms.get(backend_id)
        if vm_info is not None:
            name = vm_info["config"].name
            self._ps(f"Stop-VM -Name '{name}' -TurnOff -ErrorAction SilentlyContinue")
            self._ps(f"Remove-VM -Name '{name}' -Force")
            self._vms.pop(backend_id, None)
        return True

    def get_state(self, backend_id: str) -> int:
        vm_info = self._vms.get(backend_id)
        if vm_info is None:
            return MachineState.STOPPED
        return vm_info["state"]

    def create_disk_image(self, path: str, size_gb: int) -> bool:
        vhdx_path = path.replace(".qcow2", ".vhdx")
        result = self._ps(
            f"New-VHD -Path '{vhdx_path}' -SizeBytes {size_gb * 1024**3} -Dynamic"
        )
        return result is not None

    def get_display_address(self, backend_id: str) -> Optional[str]:
        return "127.0.0.1"

    def get_display_port(self, backend_id: str) -> Optional[int]:
        return 5900
