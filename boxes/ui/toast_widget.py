from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont


class ToastWidget(QWidget):
    def __init__(self, message: str, duration: int = 3000, parent=None) -> None:
        super().__init__(parent)
        self._message = message
        self._duration = duration
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFixedHeight(40)
        self.setStyleSheet(
            "background-color: #323232; border-radius: 4px; padding: 8px;"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        self._label = QLabel(self._message)
        self._label.setStyleSheet("color: #ffffff;")
        self._label.setFont(QFont("Sans", 11))
        layout.addWidget(self._label)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

    def show_with_animation(self) -> None:
        self.show()
        self.raise_()
        if self._duration > 0:
            QTimer.singleShot(self._duration, self._fade_out)

    def _fade_out(self) -> None:
        self.hide()

    def set_message(self, message: str) -> None:
        self._label.setText(message)
