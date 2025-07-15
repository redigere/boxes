from pathlib import Path
from typing import Optional, Callable
from urllib.request import urlopen, Request
from urllib.error import URLError
from PyQt6.QtCore import QThread, pyqtSignal


class DownloadWorker(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, url: str, dest: str, user_agent: str = "Boxes/1.0") -> None:
        super().__init__()
        self.url = url
        self.dest = dest
        self.user_agent = user_agent
        self._cancelled = False

    def run(self) -> None:
        try:
            req = Request(self.url, headers={"User-Agent": self.user_agent})
            response = urlopen(req, timeout=30)
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk = 8192
            dest_path = Path(self.dest)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.dest, "wb") as f:
                while data := response.read(chunk):
                    if self._cancelled:
                        return
                    f.write(data)
                    downloaded += len(data)
                    if total > 0:
                        self.progress.emit(downloaded, total)
            self.finished.emit(self.dest)
        except URLError as e:
            self.error_signal.emit(str(e))

    def cancel(self) -> None:
        self._cancelled = True


class DownloadManager:
    def __init__(self) -> None:
        self._active: list[DownloadWorker] = []

    def download(self, url: str, dest: str,
                 on_progress: Optional[Callable] = None,
                 on_done: Optional[Callable] = None,
                 on_error: Optional[Callable] = None) -> DownloadWorker:
        worker = DownloadWorker(url, dest)
        if on_progress:
            worker.progress.connect(on_progress)
        if on_done:
            worker.finished.connect(on_done)
        if on_error:
            worker.error_signal.connect(on_error)
        self._active.append(worker)
        worker.finished.connect(lambda: self._active.remove(worker) if worker in self._active else None)
        worker.start()
        return worker

    def cancel_all(self) -> None:
        for w in self._active:
            w.cancel()
            w.wait()
        self._active.clear()
