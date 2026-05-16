import subprocess
from pathlib import Path
from typing import Optional


class ISOExtractor:
	def __init__(self) -> None:
		self._output_dir: Optional[Path] = None

	def set_output_dir(self, path: str) -> None:
		self._output_dir = Path(path)
		self._output_dir.mkdir(parents=True, exist_ok=True)

	def extract_kernel(self, iso_path: str) -> Optional[tuple[str, str]]:
		iso = Path(iso_path)
		if not iso.exists():
			return None
		out = self._output_dir or Path("/tmp/boxes-extract")
		out.mkdir(parents=True, exist_ok=True)
		kernel = None
		initrd = None
		candidates = {
			"kernel": [
				"isolinux/vmlinuz",
				"images/pxeboot/vmlinuz",
				"casper/vmlinuz",
				"live/vmlinuz",
			],
			"initrd": [
				"isolinux/initrd.img",
				"images/pxeboot/initrd.img",
				"casper/initrd",
				"live/initrd.img",
			],
		}
		for kind, paths in candidates.items():
			for p in paths:
				dest = out / Path(p).name
				if self._extract(iso_path, p, str(dest)):
					if kind == "kernel":
						kernel = str(dest)
					else:
						initrd = str(dest)
					break
		if kernel and initrd:
			return (kernel, initrd)
		return None

	def _extract(self, iso: str, src: str, dest: str) -> bool:
		try:
			result = subprocess.run(
				["isoinfo", "-R", "-x", f"/{src}", "-i", iso], capture_output=True, timeout=30
			)
			if result.returncode == 0 and result.stdout:
				Path(dest).write_bytes(result.stdout)
				return True
		except (FileNotFoundError, subprocess.TimeoutExpired):
			return False
		return False
