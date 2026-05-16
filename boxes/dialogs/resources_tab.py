try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSpinBox, QFormLayout
except ImportError:
    QWidget = type("QWidget", (object,), {})
    QVBoxLayout = type("QVBoxLayout", (object,), {})
    QSpinBox = type("QSpinBox", (object,), {})
    QFormLayout = type("QFormLayout", (object,), {})


class ResourcesTab(QWidget):
	def __init__(self, parent=None) -> None:
		super().__init__(parent)
		self._setup_ui()

	def _setup_ui(self) -> None:
		layout = QVBoxLayout(self)
		form = QFormLayout()
		self._ram_spin = QSpinBox()
		self._ram_spin.setRange(512, 65536)
		self._ram_spin.setValue(2048)
		self._ram_spin.setSuffix(" MB")
		form.addRow("RAM:", self._ram_spin)
		self._cpus_spin = QSpinBox()
		self._cpus_spin.setRange(1, 64)
		self._cpus_spin.setValue(2)
		form.addRow("CPUs:", self._cpus_spin)
		layout.addLayout(form)
		layout.addStretch()

	@property
	def ram_mb(self) -> int:
		return self._ram_spin.value()

	@ram_mb.setter
	def ram_mb(self, value: int) -> None:
		self._ram_spin.setValue(value)

	@property
	def cpus(self) -> int:
		return self._cpus_spin.value()

	@cpus.setter
	def cpus(self, value: int) -> None:
		self._cpus_spin.setValue(value)
