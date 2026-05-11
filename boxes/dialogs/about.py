from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About Boxes")
        self.setFixedSize(400, 280)
        layout = QVBoxLayout(self)

        title = QLabel("<h1>Boxes</h1>")
        title.setObjectName("aboutTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        from boxes import __version__
        version = QLabel(f"<b>Version {__version__}</b>")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        desc = QLabel(
            "Virtualization made simple.<br><br>"
            "A cross-platform virtual machine manager<br>"
            "built with Python, Qt6, and QEMU/KVM.<br><br>"
            "Supports libvirt, direct QEMU, and remote SSH backends."
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        desc.setObjectName("aboutDesc")
        layout.addWidget(desc)

        layout.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)
