import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon

from boxes import __version__, __app_id__, __app_name__
from boxes.app_window import AppWindow
from boxes.models.collection import MachineCollection
from boxes.models.config import BoxConfig
from boxes.models.machine import Machine
from boxes.backends.libvirt_backend import LibvirtBackend
from boxes.backends.qemu_backend import QEMUBackend
from boxes.backends.ssh_backend import SSHBackend
from boxes.constants import BOXES_IMAGES, BOXES_CONFIG, BOXES_DATA, BOXES_CACHE
from boxes.util import check_libvirt_available, find_qemu_binary


class App(QApplication):
    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self.setApplicationName(__app_name__)
        self.setApplicationVersion(__version__)
        self.setOrganizationDomain("boxes.io")
        self.setDesktopFileName(__app_id__)
        self.setWindowIcon(QIcon.fromTheme(__app_id__))

        for d in [BOXES_DATA, BOXES_CONFIG, BOXES_CACHE, BOXES_IMAGES]:
            d.mkdir(parents=True, exist_ok=True)

        self.collection = MachineCollection()
        self.backend = self._detect_backend()
        self.main_window: Optional[AppWindow] = None

    def _detect_backend(self) -> object:
        if check_libvirt_available():
            try:
                bk = LibvirtBackend()
                if bk.connect():
                    return bk
            except Exception:
                pass
        if find_qemu_binary():
            return QEMUBackend()
        return QEMUBackend()

    def new_window(self) -> AppWindow:
        win = AppWindow(self.collection, self.backend)
        self.main_window = win
        win.show()
        return win

    def activate(self) -> None:
        if self.main_window:
            self.main_window.raise_()
            self.main_window.activateWindow()
        else:
            self.new_window()


def main() -> int:
    from PyQt6.QtCore import Qt
    app = App(sys.argv)
    win = app.new_window()
    app.collection.load_all()
    for machine in app.collection:
        config = machine.config
        if config.disk_path and not Path(config.disk_path).exists():
            machine.state = MachineState.STOPPED
    return app.exec()
