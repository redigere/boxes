from PyQt6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QFormLayout


class DisplayTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._graphics = QComboBox()
        self._graphics.addItems(["QXL", "VirtIO", "VGA", "VMVGA"])
        form.addRow("Graphics:", self._graphics)
        layout.addLayout(form)
        layout.addStretch()

    @property
    def graphics_type(self) -> str:
        return self._graphics.currentText()

    @graphics_type.setter
    def graphics_type(self, value: str) -> None:
        idx = self._graphics.findText(value)
        if idx >= 0:
            self._graphics.setCurrentIndex(idx)
