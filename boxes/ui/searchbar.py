from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton


class Searchbar(QWidget):
    text_changed = pyqtSignal(str)
    search_submitted = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet("""
            Searchbar { background: #1e293b; border-bottom: 1px solid #334155; padding: 4px 12px; }
            QLineEdit { background: #334155; color: #e2e8f0; border: 1px solid #475569;
                        border-radius: 8px; padding: 6px 12px; font-size: 13px; }
            QLineEdit:focus { border-color: #6366f1; }
            QPushButton { background: transparent; color: #94a3b8; border: none;
                         font-size: 16px; padding: 4px 8px; }
            QPushButton:hover { color: #e2e8f0; }
        """)
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
