from __future__ import annotations

import json
import shutil
import tarfile
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from boxes.models.config import BoxConfig


class VMExporter:
	"""Exports a VM configuration and its disk images to a portable tarball."""

	def __init__(self) -> None:
		self._export_dir: Optional[Path] = None

	def export(self, config: BoxConfig, output_path: str) -> Optional[str]:
		"""Export a VM to a tarball.

		Args:
			config: The BoxConfig of the VM to export.
			output_path: Destination tarball path (e.g., /tmp/myvm.boxes.tar.gz).

		Returns:
			The path to the created tarball, or None on failure.
		"""
		dest = Path(output_path)
		if dest.suffix not in (".gz", ".tar", ".tgz"):
			dest = dest.with_suffix(".boxes.tar.gz")

		temp_dir = Path("/tmp") / f"boxes-export-{config.uuid}"
		boxes_dir = temp_dir / "boxes"
		boxes_dir.mkdir(parents=True, exist_ok=True)

		try:
			config_data = asdict(config)
			config_path = boxes_dir / "config.json"
			config_path.write_text(json.dumps(config_data, indent=2))

			disk_src = None
			if config.disk_path:
				disk_src = Path(config.disk_path)
				if disk_src.exists():
					shutil.copy2(disk_src, boxes_dir / f"{config.name}.qcow2")

			iso_src = None
			if config.iso_path:
				iso_src = Path(config.iso_path)
				if iso_src.exists():
					shutil.copy2(iso_src, boxes_dir / f"{config.name}.iso")

			with tarfile.open(str(dest), "w:gz") as tar:
				tar.add(str(boxes_dir), arcname="boxes")

			return str(dest)

		except (OSError, shutil.Error) as exc:
			raise IOError(f"Failed to export VM: {exc}") from exc
		finally:
			if temp_dir.exists():
				shutil.rmtree(str(temp_dir), ignore_errors=True)

	def export_all(self, output_dir: str) -> list[str]:
		"""Export all configured VMs to individual tarballs."""
		exported: list[str] = []
		dest_dir = Path(output_dir)
		dest_dir.mkdir(parents=True, exist_ok=True)
		for cfg in BoxConfig.list_all():
			out_path = str(dest_dir / f"{cfg.name}.boxes.tar.gz")
			result = self.export(cfg, out_path)
			if result:
				exported.append(result)
		return exported

	@staticmethod
	def estimate_size(config: BoxConfig) -> int:
		"""Estimate the exported tarball size in bytes."""
		total = 4096  
		if config.disk_path:
			disk = Path(config.disk_path)
			if disk.exists():
				total += disk.stat().st_size
		if config.iso_path:
			iso = Path(config.iso_path)
			if iso.exists():
				total += iso.stat().st_size
		return total
