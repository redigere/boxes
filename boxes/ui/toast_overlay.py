try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout
    from PyQt6.QtCore import Qt
except ImportError:
    QWidget = type("QWidget", (object,), {})
    QVBoxLayout = type("QVBoxLayout", (object,), {})
    Qt = type("Qt", (object,), {})


class ToastOverlay(QWidget):
	def __init__(self, parent=None) -> None:
		super().__init__(parent)
		self._toasts: list = []
		self._setup_ui()

	def _setup_ui(self) -> None:
		self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
		layout = QVBoxLayout(self)
		layout.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
		layout.setSpacing(8)
		self._layout = layout

	def show_toast(self, message: str, duration: int = 3000) -> None:
		from boxes.ui.toast_widget import ToastWidget

		toast = ToastWidget(message, duration)
		self._layout.addWidget(toast)
		self._toasts.append(toast)
		toast.show_with_animation()
		if duration > 0:
			from PyQt6.QtCore import QTimer

			QTimer.singleShot(duration + 500, lambda: self._remove_toast(toast))

	def _remove_toast(self, toast) -> None:
		if toast in self._toasts:
			self._toasts.remove(toast)
			self._layout.removeWidget(toast)
			toast.deleteLater()

	def clear_all(self) -> None:
		for toast in self._toasts[:]:
			self._remove_toast(toast)
