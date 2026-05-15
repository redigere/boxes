import hashlib
import os
from pathlib import Path


class DownloadWorker:
    def __init__(self, url: str, dest: str, expected_sha256: str = "") -> None:
        self.url = url
        self.dest = dest
        self.expected_sha256 = expected_sha256
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self, progress_callback=None) -> bool:
        import urllib.request
        import urllib.error

        self._cancelled = False
        temp = self.dest + ".part"
        try:
            req = urllib.request.Request(self.url, headers={"User-Agent": "boxes/1.0"})
            with urllib.request.urlopen(req, timeout=300) as response:
                total = int(response.headers.get("Content-Length", "0")) or None
                downloaded = 0
                chunk_size = 8192
                sha256 = hashlib.sha256()
                with open(temp, "wb") as f:
                    while True:
                        if self._cancelled:
                            self._cleanup(temp)
                            return False
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        sha256.update(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total:
                            progress_callback(downloaded / total * 100)
                        elif progress_callback:
                            progress_callback(downloaded)
                if self.expected_sha256:
                    actual = sha256.hexdigest()
                    if actual != self.expected_sha256:
                        self._cleanup(temp)
                        return False
            os.replace(temp, self.dest)
            return True
        except (urllib.error.URLError, OSError, ValueError):
            self._cleanup(temp)
            return False

    def _cleanup(self, path: str) -> None:
        try:
            p = Path(path)
            if p.exists():
                p.unlink()
        except OSError:
            pass
