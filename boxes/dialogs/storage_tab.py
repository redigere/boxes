from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSpinBox, QFormLayout, QComboBox


class StorageTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._disk_spin = QSpinBox()
        self._disk_spin.setRange(4, 2048)
        self._disk_spin.setValue(32)
        self._disk_spin.setSuffix(" GB")
        form.addRow("Disk Size:", self._disk_spin)
        self._disk_type = QComboBox()
        self._disk_type.addItems(["qcow2", "raw", "vdi"])
        form.addRow("Disk Type:", self._disk_type)
        layout.addLayout(form)
        layout.addStretch()

    @property
    def disk_gb(self) -> int:
        return self._disk_spin.value()

    @disk_gb.setter
    def disk_gb(self, value: int) -> None:
        self._disk_spin.setValue(value)

    @property
    def disk_format(self) -> str:
        return self._disk_type.currentText()
