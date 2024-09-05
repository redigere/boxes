from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Callable

from boxes.models.machine import Machine
from boxes.models.config import BoxConfig


class BackendCapabilities:
    def __init__(self) -> None:
        self.snapshots = False
        self.usb_redirection = False
        self.shared_folders = False
        self.live_migration = False
        self.storage_pools = False
        self.networks = False


class BaseBackend(ABC):
    def __init__(self) -> None:
        self.capabilities = BackendCapabilities()

    @abstractmethod
    def connect(self) -> bool: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @property
    @abstractmethod
    def connected(self) -> bool: ...

    @abstractmethod
    def list_machines(self) -> list[dict]: ...

    @abstractmethod
    def define_machine(self, config: BoxConfig) -> Optional[str]: ...

    @abstractmethod
    def undefine_machine(self, backend_id: str) -> bool: ...

    @abstractmethod
    def start_machine(self, backend_id: str) -> bool: ...

    @abstractmethod
    def shutdown_machine(self, backend_id: str) -> bool: ...

    @abstractmethod
    def pause_machine(self, backend_id: str) -> bool: ...

    @abstractmethod
    def resume_machine(self, backend_id: str) -> bool: ...

    @abstractmethod
    def delete_machine(self, backend_id: str) -> bool: ...

    @abstractmethod
    def get_state(self, backend_id: str) -> int: ...

    @abstractmethod
    def create_disk_image(self, path: str, size_gb: int) -> bool: ...

    @abstractmethod
    def get_display_address(self, backend_id: str) -> Optional[str]: ...

    @abstractmethod
    def get_display_port(self, backend_id: str) -> Optional[int]: ...
