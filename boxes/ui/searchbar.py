try:
    from PyQt6.QtCore import pyqtSignal
    from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton
except ImportError:
    class _DummySignal:
        def emit(self, *args, **kwargs):
            pass
        def connect(self, *args, **kwargs):
            pass
    def pyqtSignal(*args, **kwargs):  # noqa: E731
            return _DummySignal()
    QWidget = type("QWidget", (object,), {})
    QHBoxLayout = type("QHBoxLayout", (object,), {})
    QLineEdit = type("QLineEdit", (object,), {})
    QPushButton = type("QPushButton", (object,), {})


class Searchbar(QWidget):
	text_changed = pyqtSignal(str)
	search_submitted = pyqtSignal(str)

	def __init__(self, parent=None) -> None:
		super().__init__(parent)
		layout = QHBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)

		self.input = QLineEdit()
		self.input.setPlaceholderText("Search virtual machines...")
		self.input.setClearButtonEnabled(True)
		self.input.textChanged.connect(self.text_changed.emit)
		self.input.returnPressed.connect(lambda: self.search_submitted.emit(self.input.text()))
		layout.addWidget(self.input)

		self.close_btn = QPushButton("✕")
		self.close_btn.clicked.connect(self._close)
		layout.addWidget(self.close_btn)
		self.hide()

	@property
	def text(self) -> str:
		return self.input.text()

	@text.setter
	def text(self, value: str) -> None:
		self.input.setText(value)

	def showEvent(self, event) -> None:
		super().showEvent(event)
		self.input.setFocus()
		self.input.selectAll()

	def _close(self) -> None:
		self.input.clear()
		self.hide()
