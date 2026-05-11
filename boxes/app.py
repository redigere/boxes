import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from boxes import __version__, __app_id__, __app_name__
from boxes.app_window import AppWindow
from boxes.backends import BaseBackend
from boxes.models.collection import MachineCollection
from boxes.models.machine import MachineState
from boxes.constants import BOXES_IMAGES, BOXES_CONFIG, BOXES_DATA, BOXES_CACHE
from boxes.constants import BACKEND_PRIORITY
from boxes.util import (
    check_type0_available,
    check_xen_available,
    check_libvirt_available,
    check_hyperv_available,
    check_macos_hvf_available,
    find_qemu_binary,
)


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

    def _detect_backend(self) -> BaseBackend:
        for backend_name in BACKEND_PRIORITY:
            if backend_name == "type0" and check_type0_available():
                from boxes.backends.type0_backend import Type0Backend
                bk: BaseBackend = Type0Backend()
                if bk.connect():
                    return bk
            if backend_name == "xen" and check_xen_available():
                from boxes.backends.xen_backend import XenBackend
                bk = XenBackend()
                if bk.connect():
                    return bk
            if backend_name == "libvirt" and check_libvirt_available():
                try:
                    from boxes.backends.libvirt_backend import LibvirtBackend
                    bk = LibvirtBackend()
                    if bk.connect():
                        return bk
                except Exception:
                    pass
            if backend_name == "hyperv" and check_hyperv_available():
                from boxes.backends.hyperv_backend import HyperVBackend
                bk = HyperVBackend()
                if bk.connect():
                    return bk
            if backend_name == "macos" and check_macos_hvf_available():
                from boxes.backends.macos_backend import MacOSBackend
                bk = MacOSBackend()
                if bk.connect():
                    return bk
            if backend_name == "qemu" and find_qemu_binary():
                from boxes.backends.qemu_backend import QEMUBackend
                return QEMUBackend()
        from boxes.backends.qemu_backend import QEMUBackend
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
    app = App(sys.argv)
    app.new_window()
    app.collection.load_all()
    for machine in app.collection:
        config = machine.config
        if config.disk_path and not Path(config.disk_path).exists():
            machine.state = MachineState.STOPPED
    return app.exec()
