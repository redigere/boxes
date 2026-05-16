from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional
import json
import uuid as uuid_mod

from boxes.constants import BOXES_CONFIG


@dataclass
class BoxConfig:
	name: str
	uuid: str = field(default_factory=lambda: str(uuid_mod.uuid4()))
	memory_mb: int = 2048
	vcpus: int = 2
	disk_size_gb: int = 20
	disk_path: Optional[str] = None
	iso_path: Optional[str] = None
	os_type: str = "generic"
	graphics: str = "spice"
	autostart: bool = False
	network: str = "default"
	arch: str = "x86_64"
	machine_type: str = "pc-q35-9.2"
	cpu_model: str = "host"
	firmware: str = "bios"

	@property
	def config_path(self) -> Path:
		return BOXES_CONFIG / f"{self.uuid}.json"

	def save(self) -> None:
		BOXES_CONFIG.mkdir(parents=True, exist_ok=True)
		self.config_path.write_text(json.dumps(asdict(self), indent=2))

	def delete(self) -> None:
		if self.config_path.exists():
			self.config_path.unlink()

	@classmethod
	def load(cls, path: Path) -> "BoxConfig":
		return cls(**json.loads(path.read_text()))

	@classmethod
	def list_all(cls) -> list["BoxConfig"]:
		if not BOXES_CONFIG.exists():
			return []
		return [cls.load(f) for f in sorted(BOXES_CONFIG.iterdir()) if f.suffix == ".json"]
