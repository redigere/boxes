from __future__ import annotations

try:
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QDialogButtonBox, QWidget, QSpinBox, QFormLayout, QComboBox, QLineEdit
except ImportError:
    QDialog = type("QDialog", (object,), {})
    QVBoxLayout = type("QVBoxLayout", (object,), {})
    QTabWidget = type("QTabWidget", (object,), {})
    QDialogButtonBox = type("QDialogButtonBox", (object,), {})
    QWidget = type("QWidget", (object,), {})
    QSpinBox = type("QSpinBox", (object,), {})
    QFormLayout = type("QFormLayout", (object,), {})
    QComboBox = type("QComboBox", (object,), {})
    QLineEdit = type("QLineEdit", (object,), {})

from boxes.models.machine import Machine
from boxes.models.config import BoxConfig


class ResourcesTab(QWidget):
	def __init__(self, config: BoxConfig) -> None:
		super().__init__()
		self.config = config
		layout = QFormLayout(self)
		layout.setSpacing(16)

		self.memory_spin = QSpinBox()
		self.memory_spin.setRange(256, 524288)
		self.memory_spin.setValue(config.memory_mb)
		self.memory_spin.setSingleStep(256)
		self.memory_spin.setSuffix(" MB")
		self.memory_spin.valueChanged.connect(lambda v: setattr(config, "memory_mb", v))
		layout.addRow("Memory:", self.memory_spin)

		self.vcpu_spin = QSpinBox()
		self.vcpu_spin.setRange(1, 256)
		self.vcpu_spin.setValue(config.vcpus)
		self.vcpu_spin.valueChanged.connect(lambda v: setattr(config, "vcpus", v))
		layout.addRow("vCPUs:", self.vcpu_spin)

		self.cpu_combo = QComboBox()
		self.cpu_combo.addItems(["host", "host-passthrough", "qemu64", "qemu32", "kvm64"])
		self.cpu_combo.setCurrentText(config.cpu_model)
		self.cpu_combo.currentTextChanged.connect(lambda v: setattr(config, "cpu_model", v))
		layout.addRow("CPU Model:", self.cpu_combo)

	def save(self) -> None:
		self.config.memory_mb = self.memory_spin.value()
		self.config.vcpus = self.vcpu_spin.value()
		self.config.cpu_model = self.cpu_combo.currentText()
		self.config.save()


class StorageTab(QWidget):
	def __init__(self, config: BoxConfig) -> None:
		super().__init__()
		self.config = config
		layout = QFormLayout(self)

		self.disk_spin = QSpinBox()
		self.disk_spin.setRange(1, 16384)
		self.disk_spin.setValue(config.disk_size_gb)
		self.disk_spin.setSuffix(" GB")
		layout.addRow("Disk Size:", self.disk_spin)

		self.disk_path = QLineEdit(config.disk_path or "")
		layout.addRow("Disk Path:", self.disk_path)

		self.iso_path = QLineEdit(config.iso_path or "")
		layout.addRow("ISO Path:", self.iso_path)

	def save(self) -> None:
		self.config.disk_size_gb = self.disk_spin.value()
		self.config.disk_path = self.disk_path.text() or None
		self.config.iso_path = self.iso_path.text() or None
		self.config.save()


class NetworkTab(QWidget):
	def __init__(self, config: BoxConfig) -> None:
		super().__init__()
		self.config = config
		layout = QFormLayout(self)

		self.network_combo = QComboBox()
		self.network_combo.addItems(["default", "nat", "bridge", "isolated", "user"])
		self.network_combo.setCurrentText(config.network)
		layout.addRow("Network:", self.network_combo)

	def save(self) -> None:
		self.config.network = self.network_combo.currentText()
		self.config.save()


class DisplayTab(QWidget):
	def __init__(self, config: BoxConfig) -> None:
		super().__init__()
		self.config = config
		layout = QFormLayout(self)

		self.graphics_combo = QComboBox()
		self.graphics_combo.addItems(["spice", "vnc"])
		self.graphics_combo.setCurrentText(config.graphics)
		layout.addRow("Graphics:", self.graphics_combo)

		self.firmware_combo = QComboBox()
		self.firmware_combo.addItems(["bios", "uefi", "uefi-with-csm"])
		self.firmware_combo.setCurrentText(config.firmware)
		layout.addRow("Firmware:", self.firmware_combo)

	def save(self) -> None:
		self.config.graphics = self.graphics_combo.currentText()
		self.config.firmware = self.firmware_combo.currentText()
		self.config.save()


class PreferencesDialog(QDialog):
	def __init__(self, machine: Machine, parent=None) -> None:
		super().__init__(parent)
		self.machine = machine
		self.config = machine.config
		self.setWindowTitle(f"{machine.name} — Preferences")
		self.setMinimumSize(560, 420)

		layout = QVBoxLayout(self)
		tabs = QTabWidget()
		layout.addWidget(tabs)

		self.resources = ResourcesTab(self.config)
		self.storage = StorageTab(self.config)
		self.network = NetworkTab(self.config)
		self.display = DisplayTab(self.config)

		tabs.addTab(self.resources, "Resources")
		tabs.addTab(self.storage, "Storage")
		tabs.addTab(self.network, "Network")
		tabs.addTab(self.display, "Display")

		buttons = QDialogButtonBox(
			QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
		)

		def _on_accept() -> None:
			self.resources.save()
			self.storage.save()
			self.network.save()
			self.display.save()
			self.accept()

		buttons.accepted.connect(_on_accept)
		buttons.rejected.connect(self.reject)
		layout.addWidget(buttons)
