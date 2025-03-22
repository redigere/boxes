from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class ToastWidget(QWidget):
    dismissed = pyqtSignal()

    def __init__(self, message: str, action: str = "", duration_ms: int = 5000, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet("""
            ToastWidget { background: #1e293b; border-radius: 24px; padding: 0px; }
            QLabel { color: #f8fafc; font-size: 13px; padding: 8px 16px; }
            QPushButton { color: #818cf8; background: transparent; border: none;
                         font-weight: bold; font-size: 13px; padding: 8px 16px; }
            QPushButton:hover { color: #a5b4fc; }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 8, 6)

        self.label = QLabel(message)
        layout.addWidget(self.label)

        self.action_btn = QPushButton(action) if action else None
        if self.action_btn:
            layout.addWidget(self.action_btn)

        close = QPushButton("✕")
        close.setFixedSize(28, 28)
        close.clicked.connect(self.dismiss)
        layout.addWidget(close)

        if duration_ms > 0:
            QTimer.singleShot(duration_ms, self.dismiss)

    def on_action(self, callback) -> None:
        if self.action_btn:
            self.action_btn.clicked.connect(callback)
            self.action_btn.clicked.connect(self.dismiss)


class ToastOverlay(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        self._layout.setContentsMargins(0, 0, 0, 32)

    def show_message(self, message: str, action: str = "") -> ToastWidget:
        toast = ToastWidget(message, action, parent=self)
        self._layout.addWidget(toast)
        toast.dismissed.connect(lambda: self._remove(toast))
        return toast

    def _remove(self, toast: ToastWidget) -> None:
        self._layout.removeWidget(toast)
        toast.deleteLater()
