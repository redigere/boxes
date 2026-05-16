from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Optional

from boxes.constants import BOXES_CONFIG


@dataclass
class VMTemplate:
	name: str
	memory_mb: int = 2048
	vcpus: int = 2
	disk_size_gb: int = 20
	os_type: str = "generic"
	graphics: str = "spice"
	arch: str = "x86_64"
	firmware: str = "bios"
	network: str = "default"
	machine_type: str = "pc-q35-9.2"
	cpu_model: str = "host"
	description: str = ""
	iso_url: str = ""
	tags: list[str] | None = None

	def __post_init__(self) -> None:
		if self.tags is None:
			self.tags = []


class TemplateManager:
	"""Manages VM configuration templates.

	Templates allow creating VMs with pre-defined settings
	without manually specifying every parameter each time.
	"""

	def __init__(self) -> None:
		self._templates_dir = BOXES_CONFIG / "templates"
		self._templates: dict[str, VMTemplate] = {}
		self._load()

	def _load(self) -> None:
		if not self._templates_dir.exists():
			self._templates_dir.mkdir(parents=True, exist_ok=True)
			return
		for tpl_file in sorted(self._templates_dir.iterdir()):
			if tpl_file.suffix == ".json":
				try:
					data = json.loads(tpl_file.read_text())
					tpl = VMTemplate(**data)
					self._templates[tpl.name] = tpl
				except (json.JSONDecodeError, OSError, TypeError):
					continue

	def _save(self, template: VMTemplate) -> None:
		self._templates_dir.mkdir(parents=True, exist_ok=True)
		tpl_path = self._templates_dir / f"{template.name}.json"
		tpl_path.write_text(json.dumps(asdict(template), indent=2))

	def create(self, template: VMTemplate) -> bool:
		"""Create a new template. Returns False if name already exists."""
		if template.name in self._templates:
			return False
		self._templates[template.name] = template
		self._save(template)
		return True

	def get(self, name: str) -> Optional[VMTemplate]:
		return self._templates.get(name)

	def delete(self, name: str) -> bool:
		tpl = self._templates.pop(name, None)
		if tpl is None:
			return False
		tpl_path = self._templates_dir / f"{name}.json"
		if tpl_path.exists():
			tpl_path.unlink()
		return True

	def list(self) -> list[VMTemplate]:
		return list(self._templates.values())

	def list_names(self) -> list[str]:
		return list(self._templates.keys())

	def count(self) -> int:
		return len(self._templates)

	def apply(self, name: str, overrides: Optional[dict] = None) -> Optional[VMTemplate]:
		"""Get a template with optional overrides applied."""
		tpl = self._templates.get(name)
		if tpl is None:
			return None
		if overrides:
			data = asdict(tpl)
			data.update(overrides)
			return VMTemplate(**data)
		return tpl
