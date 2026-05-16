import sys
from pathlib import Path
from typing import Optional

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon
    _HAS_PYQT6 = True
except ImportError:
    _HAS_PYQT6 = False
    QApplication = type("QApplication", (object,), {})
    QIcon = type("QIcon", (object,), {})

from boxes import __version__, __app_id__, __app_name__
from boxes.app_window import AppWindow
from boxes.theme import ThemeManager
from boxes.core import detect_backend
from boxes.models.collection import MachineCollection
from boxes.models.machine import MachineState
from boxes.constants import BOXES_DATA, BOXES_CONFIG, BOXES_CACHE


class App(QApplication):
	def __init__(self, argv: list[str]) -> None:
		super().__init__(argv)
		self.setApplicationName(__app_name__)
		self.setApplicationVersion(__version__)
		self.setOrganizationDomain("boxes.io")
		self.setDesktopFileName(__app_id__)
		self.setWindowIcon(QIcon.fromTheme(__app_id__))

		for d in [BOXES_DATA, BOXES_CONFIG, BOXES_CACHE]:
			d.mkdir(parents=True, exist_ok=True)

		self.theme = ThemeManager(self)
		self.collection = MachineCollection()
		self.backend = detect_backend()
		self.main_window: Optional[AppWindow] = None

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


def gui_main() -> int:
	if not _HAS_PYQT6:
		raise ImportError(
			"PyQt6 is required for the GUI. "
			"Install it with: pip install boxes[gui]"
		)
	app = App(sys.argv)
	app.new_window()
	app.collection.load_all()
	for machine in app.collection:
		config = machine.config
		if config.disk_path and not Path(config.disk_path).exists():
			machine.state = MachineState.STOPPED
	return app.exec()


def main() -> int:
	from boxes.cli import main as cli_main

	return cli_main()
