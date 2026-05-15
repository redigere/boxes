from typing import Optional
from pathlib import Path


class DownloadManager:
    def __init__(self, downloads_dir: Optional[str] = None) -> None:
        self.downloads_dir = downloads_dir or str(Path.home() / "Downloads" / "boxes")

    def download(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        import urllib.parse

        Path(self.downloads_dir).mkdir(parents=True, exist_ok=True)
        if not filename:
            parsed = urllib.parse.urlparse(url)
            filename = Path(parsed.path).name or "download.iso"
        dest = str(Path(self.downloads_dir) / filename)
        worker = None
        try:
            from boxes.services.download_worker import DownloadWorker

            worker = DownloadWorker(url, dest)
            if worker.run():
                return dest
        except Exception:
            if worker:
                worker.cancel()
        return None

    def download_iso(self, url: str, distro: str = "linux") -> Optional[str]:
        from boxes.util import download_iso as util_iso

        return util_iso(url, distro)
