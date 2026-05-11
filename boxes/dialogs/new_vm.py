from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QSpinBox, QPushButton,
                             QFileDialog, QComboBox, QFormLayout, QCheckBox)

from boxes.models.config import BoxConfig
from boxes.models.osdb import OSDatabase
from boxes.models.machine import Machine
from boxes.constants import BOXES_IMAGES


class SourcePage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Installation Source")
        self.setSubTitle("Select an ISO file or use a downloaded operating system.")
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.iso_edit = QLineEdit()
        self.iso_edit.setPlaceholderText("/path/to/operating-system.iso")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.iso_edit)
        row.addWidget(browse_btn)
        form.addRow("ISO Image:", row)
        layout.addLayout(form)
        self.registerField("iso*", self.iso_edit)

        self.detect_btn = QPushButton("Detect from ISO")
        self.detect_btn.clicked.connect(self._detect)
        layout.addWidget(self.detect_btn)

        layout.addStretch()

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select ISO", "", "ISO Files (*.iso)")
        if path:
            self.iso_edit.setText(path)

    def _detect(self) -> None:
        from boxes.models.media import InstallerMedia
        media = InstallerMedia(self.iso_edit.text())
        wizard = self.wizard()
        if wizard is not None and hasattr(wizard, 'os_combo'):
            idx = wizard.os_combo.findText(media.os_type.title(), Qt.MatchFlag.MatchContains)
            if idx >= 0:
                wizard.os_combo.setCurrentIndex(idx)


class ConfigPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Virtual Machine Configuration")
        self.setSubTitle("Allocate memory, CPU, and storage for your VM.")
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("My Virtual Machine")
        form.addRow("Name:", self.name_edit)
        self.registerField("name*", self.name_edit)

        self.memory_spin = QSpinBox()
        self.memory_spin.setRange(256, 524288)
        self.memory_spin.setValue(2048)
        self.memory_spin.setSingleStep(256)
        self.memory_spin.setSuffix(" MB")
        form.addRow("Memory:", self.memory_spin)
        self.registerField("memory", self.memory_spin)

        self.vcpus_spin = QSpinBox()
        self.vcpus_spin.setRange(1, 256)
        self.vcpus_spin.setValue(2)
        form.addRow("vCPUs:", self.vcpus_spin)
        self.registerField("vcpus", self.vcpus_spin)

        self.disk_spin = QSpinBox()
        self.disk_spin.setRange(1, 16384)
        self.disk_spin.setValue(20)
        self.disk_spin.setSuffix(" GB")
        form.addRow("Disk Size:", self.disk_spin)
        self.registerField("disk", self.disk_spin)

        self.os_combo = QComboBox()
        os_db = OSDatabase()
        for os_id in os_db.ids():
            info = os_db.get(os_id)
            self.os_combo.addItem(info["name"] if info else os_id, os_id)
        form.addRow("OS Type:", self.os_combo)
        self.registerField("os_type", self.os_combo)

        self.graphics_combo = QComboBox()
        self.graphics_combo.addItems(["spice", "vnc"])
        form.addRow("Graphics:", self.graphics_combo)

        self.autostart_cb = QCheckBox("Start VM automatically on boot")
        layout.addWidget(self.autostart_cb)
        layout.addLayout(form)
        layout.addStretch()

    def initializePage(self) -> None:
        iso = self.field("iso")
        if iso:
            from boxes.models.media import InstallerMedia
            media = InstallerMedia(str(iso))
            os_db = OSDatabase()
            info = os_db.suggest(media.os_type)
            idx = self.os_combo.findText(info["name"], Qt.MatchFlag.MatchContains)
            if idx >= 0:
                self.os_combo.setCurrentIndex(idx)
            self.memory_spin.setValue(info["ram"])
            self.disk_spin.setValue(info["disk"])


class SummaryPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Summary")
        self.setSubTitle("Review your virtual machine configuration.")
        layout = QVBoxLayout(self)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("font-size: 13px; padding: 16px; background: #f8fafc; border-radius: 8px;")
        layout.addWidget(self.summary)
        layout.addStretch()

    def initializePage(self) -> None:
        self.summary.setText(
            f"<b>Name:</b> {self.field('name')}<br>"
            f"<b>ISO:</b> {self.field('iso')}<br>"
            f"<b>Memory:</b> {self.field('memory')} MB<br>"
            f"<b>vCPUs:</b> {self.field('vcpus')}<br>"
            f"<b>Disk:</b> {self.field('disk')} GB<br>"
            f"<b>OS:</b> {self.field('os_type')}"
        )


class NewVMAssistant(QWizard):
    def __init__(self, collection, backend, parent=None) -> None:
        super().__init__(parent)
        self.collection = collection
        self.backend = backend
        self.setWindowTitle("Create New Virtual Machine")
        self.setMinimumSize(640, 520)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        self.source_page = SourcePage()
        self.config_page = ConfigPage()
        self.summary_page = SummaryPage()

        self.addPage(self.source_page)
        self.addPage(self.config_page)
        self.addPage(self.summary_page)

        self.accepted.connect(self._create)

    def _create(self) -> None:
        name = self.field("name")
        iso = self.field("iso")
        memory = int(self.field("memory"))
        vcpus = int(self.field("vcpus"))
        disk = int(self.field("disk"))
        os_type = self.field("os_type")

        config = BoxConfig(
            name=name,
            memory_mb=memory,
            vcpus=vcpus,
            disk_size_gb=disk,
            iso_path=iso,
            os_type=os_type,
        )
        config.save()

        disk_path = str(BOXES_IMAGES / config.uuid / f"{name}.qcow2")
        config.disk_path = disk_path
        config.save()

        self.backend.create_disk_image(disk_path, disk)
        backend_id = self.backend.define_machine(config)
        machine = Machine(config)
        if backend_id:
            machine.backend_id = backend_id
        self.collection.add(machine)
