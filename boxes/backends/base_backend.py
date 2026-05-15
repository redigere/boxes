from typing import Optional

from boxes.backends.backend_capabilities import BackendCapabilities
from boxes.models.config import BoxConfig
from boxes.models.machine_state import MachineState


class BaseBackend:
    def __init__(self) -> None:
        self.capabilities = BackendCapabilities()
        self._connected = False

    def connect(self) -> bool:
        return self._connected

    def disconnect(self) -> None:
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def list_machines(self) -> list[dict]:
        return []

    def define_machine(self, config: BoxConfig) -> Optional[str]:
        return config.uuid

    def undefine_machine(self, backend_id: str) -> bool:
        return True

    def start_machine(self, backend_id: str) -> bool:
        return False

    def shutdown_machine(self, backend_id: str) -> bool:
        return False

    def pause_machine(self, backend_id: str) -> bool:
        return False

    def resume_machine(self, backend_id: str) -> bool:
        return False

    def delete_machine(self, backend_id: str) -> bool:
        return True

    def get_state(self, backend_id: str) -> int:
        return MachineState.STOPPED

    def create_disk_image(self, path: str, size_gb: int) -> bool:
        return False

    def get_display_address(self, backend_id: str) -> Optional[str]:
        return "127.0.0.1"

    def get_display_port(self, backend_id: str) -> Optional[int]:
        return None
