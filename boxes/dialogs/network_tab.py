try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QFormLayout
except ImportError:
    QWidget = type("QWidget", (object,), {})
    QVBoxLayout = type("QVBoxLayout", (object,), {})
    QComboBox = type("QComboBox", (object,), {})
    QFormLayout = type("QFormLayout", (object,), {})


class NetworkTab(QWidget):
	def __init__(self, parent=None) -> None:
		super().__init__(parent)
		self._setup_ui()

	def _setup_ui(self) -> None:
		layout = QVBoxLayout(self)
		form = QFormLayout()
		self._network_type = QComboBox()
		self._network_type.addItems(["NAT", "Bridged", "Host-Only", "Isolated"])
		form.addRow("Network:", self._network_type)
		layout.addLayout(form)
		layout.addStretch()

	@property
	def network_type(self) -> str:
		return self._network_type.currentText()

	@network_type.setter
	def network_type(self, value: str) -> None:
		idx = self._network_type.findText(value)
		if idx >= 0:
			self._network_type.setCurrentIndex(idx)
