from __future__ import annotations

import json
import shutil
import tarfile
from pathlib import Path
from typing import Optional

from boxes.models.config import BoxConfig


class VMImporter:
	"""Imports a VM from a boxes export tarball.

	Restores the VM configuration and disk images to their
	original locations.
	"""

	def __init__(self) -> None:
		self._last_config: Optional[BoxConfig] = None

	@property
	def last_imported_config(self) -> Optional[BoxConfig]:
		"""Return the config of the last successfully imported VM."""
		return self._last_config

	def import_vm(self, tarball_path: str) -> Optional[BoxConfig]:
		"""Import a VM from a boxes export tarball.

		Args:
			tarball_path: Path to the .boxes.tar.gz file.

		Returns:
			The imported BoxConfig, or None on failure.
		"""
		src = Path(tarball_path)
		if not src.exists():
			raise FileNotFoundError(f"Export file not found: {tarball_path}")

		temp_dir = Path("/tmp") / f"boxes-import-{src.stem}"
		try:
			with tarfile.open(str(src), "r:gz") as tar:
				tar.extractall(str(temp_dir))

			boxes_dir = temp_dir / "boxes"
			if not boxes_dir.exists():
				raise ValueError("Invalid export: missing 'boxes/' directory")

			config_path = boxes_dir / "config.json"
			if not config_path.exists():
				raise ValueError("Invalid export: missing config.json")

			config_data = json.loads(config_path.read_text())
			config = BoxConfig(**config_data)

			disk_dest = None
			if config.disk_path:
				disk_src = boxes_dir / f"{config.name}.qcow2"
				if disk_src.exists():
					disk_dest = Path(config.disk_path)
					disk_dest.parent.mkdir(parents=True, exist_ok=True)
					shutil.copy2(str(disk_src), str(disk_dest))

			if config.iso_path and not Path(config.iso_path).exists():
				iso_src = boxes_dir / f"{config.name}.iso"
				if iso_src.exists():
					iso_dest = Path(config.iso_path)
					iso_dest.parent.mkdir(parents=True, exist_ok=True)
					shutil.copy2(str(iso_src), str(iso_dest))

			config.save()
			self._last_config = config
			return config

		except (json.JSONDecodeError, OSError, tarfile.TarError) as exc:
			raise IOError(f"Failed to import VM: {exc}") from exc
		finally:
			if temp_dir.exists():
				shutil.rmtree(str(temp_dir), ignore_errors=True)
