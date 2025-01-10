from typing import Optional, Callable
from PyQt6.QtCore import QThread, pyqtSignal


class AsyncWorker(QThread):
    result_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, target: Callable, args: tuple = (), kwargs: dict = None) -> None:
        super().__init__()
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def run(self) -> None:
        try:
            result = self._target(*self._args, **self._kwargs)
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))
