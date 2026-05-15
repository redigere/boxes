from PyQt6.QtWidgets import QWizardPage, QVBoxLayout, QFormLayout, QSpinBox


class ConfigPage(QWizardPage):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setTitle("Configuration")
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
        self._disk_spin = QSpinBox()
        self._disk_spin.setRange(4, 2048)
        self._disk_spin.setValue(32)
        self._disk_spin.setSuffix(" GB")
        form.addRow("Disk:", self._disk_spin)
        layout.addLayout(form)
        layout.addStretch()

    @property
    def ram_mb(self) -> int:
        return self._ram_spin.value()

    @property
    def cpus(self) -> int:
        return self._cpus_spin.value()

    @property
    def disk_gb(self) -> int:
        return self._disk_spin.value()
