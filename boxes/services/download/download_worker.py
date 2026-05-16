from __future__ import annotations

import hashlib
import os
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

try:
    from PyQt6.QtCore import QThread, pyqtSignal
except ImportError:
    QThread = type("QThread", (object,), {})
    class _DummySignal:
        def emit(self, *args, **kwargs):
            pass
        def connect(self, *args, **kwargs):
            pass
    def pyqtSignal(*args, **kwargs):  # noqa: E731
            return _DummySignal()


class DownloadWorker(QThread):
	progress = pyqtSignal(int, int)
	finished = pyqtSignal(str)
	error_signal = pyqtSignal(str)

	def __init__(
		self,
		url: str,
		dest: str,
		user_agent: str = "Boxes/1.0",
		expected_sha256: str = "",
	) -> None:
		super().__init__()
		self.url = url
		self.dest = dest
		self.user_agent = user_agent
		self.expected_sha256 = expected_sha256
		self._cancelled = False

	def run(self) -> None:
		try:
			req = Request(self.url, headers={"User-Agent": self.user_agent})
			response = urlopen(req, timeout=120)
			total = int(response.headers.get("Content-Length", 0))
			downloaded = 0
			chunk = 8192
			sha256 = hashlib.sha256()
			dest_path = Path(self.dest)
			dest_path.parent.mkdir(parents=True, exist_ok=True)
			temp = self.dest + ".part"
			with open(temp, "wb") as f:
				while data := response.read(chunk):
					if self._cancelled:
						self._cleanup(temp)
						return
					f.write(data)
					sha256.update(data)
					downloaded += len(data)
					if total > 0:
						self.progress.emit(downloaded, total)
			if self.expected_sha256:
				actual = sha256.hexdigest()
				if actual != self.expected_sha256:
					self._cleanup(temp)
					self.error_signal.emit(f"SHA256 mismatch: expected {self.expected_sha256}, got {actual}")
					return
			os.replace(temp, self.dest)
			self.finished.emit(self.dest)
		except URLError as e:
			self.error_signal.emit(str(e))
		except OSError as e:
			self.error_signal.emit(str(e))

	def cancel(self) -> None:
		self._cancelled = True

	@staticmethod
	def _cleanup(path: str) -> None:
		try:
			p = Path(path)
			if p.exists():
				p.unlink()
		except OSError:
			return
