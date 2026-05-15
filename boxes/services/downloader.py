from typing import Optional, Callable

from boxes.services.download_worker import DownloadWorker


class DownloadManager:
    def __init__(self) -> None:
        self._active: list[DownloadWorker] = []

    def download(
        self,
        url: str,
        dest: str,
        on_progress: Optional[Callable] = None,
        on_done: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ) -> DownloadWorker:
        worker = DownloadWorker(url, dest)
        if on_progress:
            worker.progress.connect(on_progress)
        if on_done:
            worker.finished.connect(on_done)
        if on_error:
            worker.error_signal.connect(on_error)
        self._active.append(worker)
        worker.finished.connect(
            lambda: self._active.remove(worker) if worker in self._active else None
        )
        worker.start()
        return worker

    def cancel_all(self) -> None:
        for w in self._active:
            w.cancel()
            w.wait()
        self._active.clear()
