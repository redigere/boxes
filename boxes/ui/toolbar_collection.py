from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal


class CollectionToolbar(QWidget):
    createRequested = pyqtSignal()
    deleteRequested = pyqtSignal()
    refreshRequested = pyqtSignal()
    searchRequested = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._create_btn = QPushButton("New")
        self._create_btn.clicked.connect(self.createRequested.emit)
        layout.addWidget(self._create_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.clicked.connect(self.deleteRequested.emit)
        layout.addWidget(self._delete_btn)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self.refreshRequested.emit)
        layout.addWidget(self._refresh_btn)

        layout.addStretch()

        self._title_label = QLabel("Virtual Machines")
        layout.addWidget(self._title_label)

        layout.addStretch()

        self._search_input = QWidget()
        layout.addWidget(self._search_input)

    def set_title(self, title: str) -> None:
        self._title_label.setText(title)

    @property
    def create_button(self) -> QPushButton:
        return self._create_btn
