from __future__ import annotations
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QPixmap

from boxes.models.config import BoxConfig
from boxes.models.machine_state import MachineState


class Machine(QObject):
    state_changed = pyqtSignal(int, int)
    error_occurred = pyqtSignal(str)

    def __init__(self, config: BoxConfig) -> None:
        super().__init__()
        self.config = config
        self._state = MachineState.STOPPED
        self._progress = 0.0
        self._screenshot: Optional[QPixmap] = None
        self.backend_id: Optional[str] = None

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def state(self) -> int:
        return self._state

    @state.setter
    def state(self, value: int) -> None:
        old = self._state
        if old != value:
            self._state = value
            self.state_changed.emit(old, value)

    @property
    def status_text(self) -> str:
        return MachineState.NAMES.get(self._state, "Unknown")

    @property
    def status_color(self) -> str:
        return MachineState.COLORS.get(self._state, "#9aa0a6")

    @property
    def is_running(self) -> bool:
        return self._state == MachineState.RUNNING

    @property
    def is_paused(self) -> bool:
        return self._state == MachineState.PAUSED

    @property
    def is_off(self) -> bool:
        return self._state == MachineState.STOPPED

    @property
    def progress(self) -> float:
        return self._progress

    @progress.setter
    def progress(self, value: float) -> None:
        self._progress = max(0.0, min(1.0, value))
