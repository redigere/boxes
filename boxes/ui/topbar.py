from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel

from boxes.models.machine import Machine


class Topbar(QWidget):
    back_requested = pyqtSignal()
    power_toggled = pyqtSignal()
    pause_toggled = pyqtSignal()
    settings_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet("""
            Topbar { background: #1e293b; border-bottom: 1px solid #334155; min-height: 48px; }
            QLabel { color: #f1f5f9; font-size: 14px; }
            QPushButton { background: #334155; color: #e2e8f0; border: none;
                         border-radius: 6px; padding: 6px 16px; font-size: 13px; }
            QPushButton:hover { background: #475569; }
            QPushButton:pressed { background: #1e293b; }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)

        self.back_btn = QPushButton("← Back")
        self.back_btn.clicked.connect(self.back_requested.emit)
        self.back_btn.hide()
        layout.addWidget(self.back_btn)

        self.title = QLabel("Boxes")
        self.title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f1f5f9;")
        layout.addWidget(self.title)
        layout.addStretch()

        self.power_btn = QPushButton("▶ Start")
        self.power_btn.clicked.connect(self.power_toggled.emit)
        self.power_btn.hide()
        layout.addWidget(self.power_btn)

        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.clicked.connect(self.pause_toggled.emit)
        self.pause_btn.hide()
        layout.addWidget(self.pause_btn)

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        self.settings_btn.hide()
        layout.addWidget(self.settings_btn)

    def show_machine_controls(self, machine: Machine) -> None:
        self.title.setText(machine.name)
        self.back_btn.show()
        self.settings_btn.show()
        self.power_btn.show()
        self.pause_btn.show()
        self._update_power_button(machine)

    def _update_power_button(self, machine: Machine) -> None:
        if machine.is_running:
            self.power_btn.setText("⏹ Shutdown")
            self.pause_btn.setText("⏸ Pause")
        elif machine.is_paused:
            self.power_btn.setText("⏹ Shutdown")
            self.pause_btn.setText("▶ Resume")
        else:
            self.power_btn.setText("▶ Start")
            self.pause_btn.hide()

    def collection_mode(self) -> None:
        self.title.setText("Boxes")
        self.back_btn.hide()
        self.power_btn.hide()
        self.pause_btn.hide()
        self.settings_btn.hide()
