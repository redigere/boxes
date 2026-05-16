from typing import Optional

try:
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal
    from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QImage, QKeyEvent, QMouseEvent
    from PyQt6.QtWidgets import QWidget, QSizePolicy
except ImportError:
    Qt = type("Qt", (object,), {})
    QTimer = type("QTimer", (object,), {})
    class _DummySignal:
        def emit(self, *args, **kwargs):
            pass
        def connect(self, *args, **kwargs):
            pass
    def pyqtSignal(*args, **kwargs):  # noqa: E731
            return _DummySignal()
    QPainter = type("QPainter", (object,), {})
    QColor = type("QColor", (object,), {})
    QFont = type("QFont", (object,), {})
    QPen = type("QPen", (object,), {})
    QImage = type("QImage", (object,), {})
    QKeyEvent = type("QKeyEvent", (object,), {})
    QMouseEvent = type("QMouseEvent", (object,), {})
    QWidget = type("QWidget", (object,), {})
    QSizePolicy = type("QSizePolicy", (object,), {})
import time

from boxes.models.machine import Machine
from boxes.services.vnc import VNCClient
from boxes.services.spice import SPICEChannel, SPICEDisplay, SPICEInput


class DisplayWidget(QWidget):
	"""VM display widget that connects to VNC or SPICE server.

	Integrates with VNCClient and SPICEDisplay/SPICEInput services
	for remote framebuffer rendering and input forwarding.
	"""

	fps_updated = pyqtSignal(int)

	def __init__(self, machine: Machine, backend=None, parent=None) -> None:
		super().__init__(parent)
		self.machine = machine
		self.backend = backend
		self.setMinimumSize(640, 480)
		self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
		self.setObjectName("displayWidget")
		self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
		self.setMouseTracking(True)

		self._frame: QImage = QImage(640, 480, QImage.Format.Format_RGB32)
		self._frame.fill(QColor("#1e293b").rgb())
		self._connected = False
		self._connection_error: Optional[str] = None

		
		self._vnc_client: Optional[VNCClient] = None
		self._spice_channel: Optional[SPICEChannel] = None
		self._spice_display: Optional[SPICEDisplay] = None
		self._spice_input: Optional[SPICEInput] = None

		
		self._timer = QTimer(self)
		self._timer.timeout.connect(self._poll_display)
		self._fps = 0
		self._frame_count = 0
		self._last_fps_time = 0.0

		
		QTimer.singleShot(0, self._auto_connect)

	def _auto_connect(self) -> None:
		"""Automatically connect to the VM display server."""
		if self._connected:
			return

		graphics = self.machine.config.graphics
		backend_id = self.machine.backend_id or self.machine.config.uuid

		display_host = "127.0.0.1"
		display_port: Optional[int] = None

		if self.backend is not None:
			addr = self.backend.get_display_address(backend_id)
			if addr:
				display_host = addr
			display_port = self.backend.get_display_port(backend_id)

		if graphics == "vnc":
			port = display_port or 5900
			self._connect_vnc(display_host, port)
		elif graphics == "spice":
			port = display_port or 5900
			self._connect_spice(display_host, port)

	def _connect_vnc(self, host: str, port: int) -> None:
		"""Connect to a VNC server using VNCClient service."""
		password = ""
		client = VNCClient(host=host, port=port, password=password)
		if client.connect():
			self._vnc_client = client
			self._connected = True
			self._connection_error = None

			
			def on_fb_update(data: bytes, x: int, y: int, w: int, h: int) -> None:
				pix_fmt = client._pixel_format
				bpp = pix_fmt["bpp"] if pix_fmt else 32
				if bpp == 32:
					img = QImage(data, w, h, w * 4, QImage.Format.Format_RGB32)
				elif bpp == 16:
					img = QImage(data, w, h, w * 2, QImage.Format.Format_RGB16)
				else:
					return
				painter = QPainter(self._frame)
				painter.drawImage(x, y, img)
				painter.end()

			client.set_framebuffer_callback(on_fb_update)
			client.request_update(incremental=False)
			self._timer.start(33)  
			self._resize_frame(client.width, client.height)
		else:
			self._connected = False
			self._connection_error = f"VNC connection to {host}:{port} failed"

	def _connect_spice(self, host: str, port: int) -> None:
		"""Connect to a SPICE server using SPICEChannel + SPICEDisplay service."""
		channel = SPICEChannel(host=host, port=port)
		if channel.connect():
			self._spice_channel = channel
			self._spice_display = SPICEDisplay(channel)
			self._spice_display.init_display(self.width(), self.height())
			self._spice_input = SPICEInput(channel)
			self._connected = True
			self._connection_error = None
			self._timer.start(33)
		else:
			self._connected = False
			self._connection_error = f"SPICE connection to {host}:{port} failed"

	def _resize_frame(self, w: int, h: int) -> None:
		"""Resize the internal framebuffer QImage."""
		if w != self._frame.width() or h != self._frame.height():
			new_frame = QImage(w, h, QImage.Format.Format_RGB32)
			new_frame.fill(QColor("#1e293b").rgb())
			self._frame = new_frame

	def _poll_display(self) -> None:
		"""Poll for framebuffer updates from the connected server."""
		if not self._connected:
			return

		if self._vnc_client is not None:
			try:
				self._vnc_client.read_message()
				self._frame_count += 1
			except Exception:
				self._disconnect()

		elif self._spice_channel is not None and self._spice_channel.connected:
			try:
				data = self._spice_channel.recv(65536)
				if data and self._spice_display is not None:
					self._spice_display.handle_draw(data)
					fb = self._spice_display.to_qimage_data()
					if fb:
						frame = QImage(
							fb, self._spice_display.width, self._spice_display.height,
							QImage.Format.Format_RGB32,
						)
						self._frame = frame
					self._frame_count += 1
			except (ConnectionError, TimeoutError):
				return
			except Exception:
				self._disconnect()

		
		now = time.monotonic()
		elapsed = now - self._last_fps_time
		if elapsed >= 1.0:
			self._fps = int(self._frame_count / elapsed)
			self._frame_count = 0
			self._last_fps_time = now
			self.fps_updated.emit(self._fps)

		self.update()

	
	
	

	def keyPressEvent(self, event: Optional[QKeyEvent]) -> None:
		if event is None:
			return
		key = self._qt_key_to_keysym(event.key())
		if self._vnc_client is not None:
			self._vnc_client.send_key_event(key, pressed=True)
		elif self._spice_input is not None:
			self._spice_input.send_key_down(key)
		event.accept()

	def keyReleaseEvent(self, event: Optional[QKeyEvent]) -> None:
		if event is None:
			return
		key = self._qt_key_to_keysym(event.key())
		if self._vnc_client is not None:
			self._vnc_client.send_key_event(key, pressed=False)
		elif self._spice_input is not None:
			self._spice_input.send_key_up(key)
		event.accept()

	def mouseMoveEvent(self, event: Optional[QMouseEvent]) -> None:
		if event is None:
			return
		x = int(event.position().x() * self._frame.width() / max(self.width(), 1))
		y = int(event.position().y() * self._frame.height() / max(self.height(), 1))
		if self._vnc_client is not None:
			self._vnc_client.send_pointer_event(x, y, self._mouse_buttons)
		elif self._spice_input is not None:
			self._spice_input.send_mouse_motion(x, y)

	def mousePressEvent(self, event: Optional[QMouseEvent]) -> None:
		if event is None:
			return
		self._mouse_buttons = self._qt_button_to_vnc_mask(event)
		self.mouseMoveEvent(event)

	def mouseReleaseEvent(self, event: Optional[QMouseEvent]) -> None:
		if event is None:
			return
		self._mouse_buttons = self._qt_button_to_vnc_mask(event)
		self.mouseMoveEvent(event)

	_mouse_buttons: int = 0

	@staticmethod
	def _qt_button_to_vnc_mask(event: QMouseEvent) -> int:
		mask = 0
		buttons = event.buttons()
		if buttons & Qt.MouseButton.LeftButton:
			mask |= 1
		if buttons & Qt.MouseButton.MiddleButton:
			mask |= 2
		if buttons & Qt.MouseButton.RightButton:
			mask |= 4
		return mask

	@staticmethod
	def _qt_key_to_keysym(qt_key: int) -> int:
		"""Convert a Qt key code to an X11 keysym.

		This is a simplified mapping covering standard keys.
		The full mapping would be generated from keysymdef.h.
		"""
		
		if Qt.Key.Key_A <= qt_key <= Qt.Key.Key_Z:
			return qt_key - Qt.Key.Key_A + 0x61
		
		if Qt.Key.Key_0 <= qt_key <= Qt.Key.Key_9:
			return qt_key - Qt.Key.Key_0 + 0x30
		
		if Qt.Key.Key_F1 <= qt_key <= Qt.Key.Key_F35:
			return qt_key - Qt.Key.Key_F1 + 0xFFBE
		
		mapping = {
			Qt.Key.Key_Return: 0xFF0D,
			Qt.Key.Key_Enter: 0xFF8D,
			Qt.Key.Key_Escape: 0xFF1B,
			Qt.Key.Key_Backspace: 0xFF08,
			Qt.Key.Key_Tab: 0xFF09,
			Qt.Key.Key_Space: 0x0020,
			Qt.Key.Key_Delete: 0xFFFF,
			Qt.Key.Key_Home: 0xFF50,
			Qt.Key.Key_End: 0xFF57,
			Qt.Key.Key_Left: 0xFF51,
			Qt.Key.Key_Up: 0xFF52,
			Qt.Key.Key_Right: 0xFF53,
			Qt.Key.Key_Down: 0xFF54,
			Qt.Key.Key_PageUp: 0xFF55,
			Qt.Key.Key_PageDown: 0xFF56,
			Qt.Key.Key_Shift: 0xFFE1,
			Qt.Key.Key_Control: 0xFFE3,
			Qt.Key.Key_Alt: 0xFFE9,
			Qt.Key.Key_Meta: 0xFFE7,
			Qt.Key.Key_CapsLock: 0xFFE5,
			Qt.Key.Key_NumLock: 0xFF7F,
			Qt.Key.Key_ScrollLock: 0xFF14,
		}
		return mapping.get(qt_key, qt_key)

	
	
	

	def paintEvent(self, event) -> None:
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
		scaled = self._frame.scaled(
			self.size(),
			Qt.AspectRatioMode.KeepAspectRatio,
			Qt.TransformationMode.SmoothTransformation,
		)
		x = (self.width() - scaled.width()) // 2
		y = (self.height() - scaled.height()) // 2
		painter.drawImage(x, y, scaled)

		if not self._connected:
			painter.setPen(QPen(QColor("#64748b"), 1))
			f = QFont("sans-serif", 18)
			painter.setFont(f)
			msg = self._connection_error or "VM Display"
			painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, msg)
		elif self._fps > 0:
			painter.setPen(QPen(QColor("#94a3b8"), 1))
			f = QFont("monospace", 10)
			painter.setFont(f)
			painter.drawText(8, self.height() - 8, f"{self._fps} FPS")

	def _disconnect(self) -> None:
		self._timer.stop()
		if self._vnc_client is not None:
			self._vnc_client.disconnect()
			self._vnc_client = None
		if self._spice_channel is not None:
			self._spice_channel.disconnect()
			self._spice_channel = None
			self._spice_display = None
			self._spice_input = None
		self._connected = False

	def disconnect(self) -> None:
		self._disconnect()
