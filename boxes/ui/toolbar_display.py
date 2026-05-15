from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QSlider
from PyQt6.QtCore import Qt, pyqtSignal


class DisplayToolbar(QWidget):
    backRequested = pyqtSignal()
    fullscreenRequested = pyqtSignal()
    screenshotRequested = pyqtSignal()
    zoomChanged = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._back_btn = QPushButton("Back")
        self._back_btn.clicked.connect(self.backRequested.emit)
        layout.addWidget(self._back_btn)

        layout.addStretch()

        self._name_label = QLabel()
        layout.addWidget(self._name_label)

        layout.addStretch()

        self._screenshot_btn = QPushButton("Screenshot")
        self._screenshot_btn.clicked.connect(self.screenshotRequested.emit)
        layout.addWidget(self._screenshot_btn)

        self._fullscreen_btn = QPushButton("Fullscreen")
        self._fullscreen_btn.clicked.connect(self.fullscreenRequested.emit)
        layout.addWidget(self._fullscreen_btn)

        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(25, 200)
        self._zoom_slider.setValue(100)
        self._zoom_slider.valueChanged.connect(self.zoomChanged.emit)
        layout.addWidget(self._zoom_slider)

    def set_machine_name(self, name: str) -> None:
        self._name_label.setText(name)

    def set_zoom(self, value: int) -> None:
        self._zoom_slider.setValue(value)

    @property
    def zoom(self) -> int:
        return self._zoom_slider.value()
