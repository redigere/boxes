from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QButtonGroup, QSizePolicy


class CollectionToolbar(QWidget):
    view_changed = pyqtSignal(str)
    new_vm_clicked = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)

        self.title = QLabel("Virtual Machines")
        layout.addWidget(self.title)

        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        )
        layout.addWidget(spacer)

        self.icon_btn = QPushButton("Icons")
        self.icon_btn.setCheckable(True)
        self.icon_btn.setChecked(True)
        layout.addWidget(self.icon_btn)

        self.list_btn = QPushButton("List")
        self.list_btn.setCheckable(True)
        layout.addWidget(self.list_btn)

        group = QButtonGroup(self)
        group.addButton(self.icon_btn)
        group.addButton(self.list_btn)
        group.idClicked.connect(
            lambda btn: self.view_changed.emit("icon" if btn == self.icon_btn else "list")
        )

        self.new_btn = QPushButton("+ New VM")
        self.new_btn.setObjectName("newBtn")
        self.new_btn.clicked.connect(self.new_vm_clicked.emit)
        layout.addWidget(self.new_btn)


class DisplayToolbar(QWidget):
    back_clicked = pyqtSignal()
    fullscreen_clicked = pyqtSignal(bool)
    screenshot_clicked = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self.back_btn = QPushButton("← Back to Collection")
        self.back_btn.clicked.connect(self.back_clicked.emit)
        layout.addWidget(self.back_btn)
        layout.addStretch()

        self.fullscreen_btn = QPushButton("Fullscreen")
        self.fullscreen_btn.setCheckable(True)
        self.fullscreen_btn.clicked.connect(lambda c: self.fullscreen_clicked.emit(c))
        layout.addWidget(self.fullscreen_btn)

        self.screenshot_btn = QPushButton("Screenshot")
        self.screenshot_btn.clicked.connect(self.screenshot_clicked.emit)
        layout.addWidget(self.screenshot_btn)
