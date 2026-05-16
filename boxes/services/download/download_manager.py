from __future__ import annotations

from pathlib import Path
from typing import Optional


class DownloadManager:
	def __init__(self, downloads_dir: Optional[str] = None) -> None:
		self.downloads_dir = downloads_dir or str(Path.home() / "Downloads" / "boxes")

	def download(self, url: str, filename: Optional[str] = None) -> Optional[str]:
		from boxes.util import download_file

		Path(self.downloads_dir).mkdir(parents=True, exist_ok=True)
		if not filename:
			from urllib.parse import urlparse

			parsed = urlparse(url)
			filename = Path(parsed.path).name or "download.iso"
		dest = str(Path(self.downloads_dir) / filename)
		try:
			return download_file(url, dest)
		except Exception:
			return None

	def download_iso(self, url: str, distro: str = "linux") -> Optional[str]:
		from boxes.util import download_iso as util_iso

		return util_iso(url, distro)
