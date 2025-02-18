from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QImage
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
import socket
import struct

from boxes.models.machine import Machine


class DisplayWidget(QWidget):
    def __init__(self, machine: Machine, parent=None) -> None:
        super().__init__(parent)
        self.machine = machine
        self.setMinimumSize(640, 480)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: #0f172a;")
        self._frame: QImage = QImage(640, 480, QImage.Format.Format_RGB32)
        self._frame.fill(QColor("#1e293b").rgb())
        self._vnc_sock: Optional[socket.socket] = None
        self._connected = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll_display)
        self._fps = 0
        self._frame_count = 0
        self._last_fps_time = 0.0

    def connect_vnc(self, host: str = "127.0.0.1", port: int = 5900) -> bool:
        try:
            self._vnc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._vnc_sock.settimeout(3)
            self._vnc_sock.connect((host, port))
            self._vnc_sock.settimeout(0.01)
            self._vnc_handshake()
            self._connected = True
            self._timer.start(33)
            return True
        except Exception:
            self._connected = False
            return False

    def _vnc_handshake(self) -> None:
        if not self._vnc_sock:
            return
        data = self._vnc_sock.recv(12)
        if len(data) >= 12 and data[:4] == b"RFB ":
            ver_major, ver_minor = data[4:7], data[7:11]
            self._vnc_sock.send(b"RFB 003.008\n")
            auth = self._vnc_sock.recv(4)
            self._vnc_sock.send(b"\x01" * 16)
            self._vnc_sock.recv(4)
            self._vnc_sock.send(struct.pack("!HH", 640, 480))
            self._vnc_sock.recv(4)

    def _poll_display(self) -> None:
        if not self._vnc_sock or not self._connected:
            return
        try:
            while True:
                data = self._vnc_sock.recv(4)
                if not data:
                    break
        except socket.timeout:
            pass
        except Exception:
            self._connected = False
            self._timer.stop()

    def connect_spice(self, port: int) -> None:
        self._fps_placeholder = QLabel(f"SPICE connected on port {port}")
        self._fps_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._fps_placeholder.setStyleSheet("color: #4ade80; font-size: 16px;")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        scaled = self._frame.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawImage(x, y, scaled)

        if not self._connected:
            painter.setPen(QPen(QColor("#64748b"), 1))
            f = QFont("sans-serif", 18)
            painter.setFont(f)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "VM Display")

    def disconnect(self) -> None:
        self._timer.stop()
        if self._vnc_sock:
            self._vnc_sock.close()
            self._vnc_sock = None
        self._connected = False
