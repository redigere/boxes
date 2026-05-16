from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from boxes.backends.backend_capabilities import BackendCapabilities
from boxes.models.config import BoxConfig


class BaseBackend(ABC):
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

	@abstractmethod
	def list_machines(self) -> list[dict[str, str | int | bool | None]]:
		...

	@abstractmethod
	def define_machine(self, config: BoxConfig) -> Optional[str]:
		...

	@abstractmethod
	def undefine_machine(self, backend_id: str) -> bool:
		...

	@abstractmethod
	def start_machine(self, backend_id: str) -> bool:
		...

	@abstractmethod
	def shutdown_machine(self, backend_id: str) -> bool:
		...

	@abstractmethod
	def pause_machine(self, backend_id: str) -> bool:
		...

	@abstractmethod
	def resume_machine(self, backend_id: str) -> bool:
		...

	@abstractmethod
	def delete_machine(self, backend_id: str, keep_disks: bool = False) -> bool:
		...

	@abstractmethod
	def get_state(self, backend_id: str) -> int:
		...

	@abstractmethod
	def create_disk_image(self, path: str, size_gb: int) -> bool:
		...

	@abstractmethod
	def get_display_address(self, backend_id: str) -> Optional[str]:
		...

	@abstractmethod
	def get_display_port(self, backend_id: str) -> Optional[int]:
		...
