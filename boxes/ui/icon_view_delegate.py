from typing import Optional

try:
    from PyQt6.QtWidgets import QStyledItemDelegate, QStyle
    from PyQt6.QtCore import QRect, Qt, QModelIndex, QSize, QPoint
    from PyQt6.QtGui import QPainter, QColor, QPolygon
except ImportError:
    QStyledItemDelegate = type("QStyledItemDelegate", (object,), {})
    QStyle = type("QStyle", (object,), {})
    QRect = type("QRect", (object,), {})
    Qt = type("Qt", (object,), {})
    QModelIndex = type("QModelIndex", (object,), {})
    QSize = type("QSize", (object,), {})
    QPoint = type("QPoint", (object,), {})
    QPainter = type("QPainter", (object,), {})
    QColor = type("QColor", (object,), {})
    QPolygon = type("QPolygon", (object,), {})


class IconViewDelegate(QStyledItemDelegate):
	def __init__(self, parent=None) -> None:
		super().__init__(parent)
		self.icon_size = 64

	def paint(self, painter: Optional[QPainter], option, index: QModelIndex) -> None:
		if painter is None:
			return
		painter.save()
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)
		rect = option.rect
		name = index.data(Qt.ItemDataRole.DisplayRole) or ""
		state = index.data(Qt.ItemDataRole.UserRole) or 0

		palette = option.palette
		if option.state & QStyle.StateFlag.State_Selected:
			painter.fillRect(rect, palette.highlight())
			text_color = palette.highlightedText().color()
		else:
			painter.fillRect(rect, palette.base())
			text_color = palette.text().color()

		icon_x = rect.x() + (rect.width() - self.icon_size) // 2
		icon_y = rect.y() + 8
		icon_rect = QRect(icon_x, icon_y, self.icon_size, self.icon_size)

		state_colors = {0: "#9aa0a6", 1: "#34a853", 2: "#fbbc04", 3: "#4285f4", 4: "#ea4335"}
		color = QColor(state_colors.get(state, "#9aa0a6"))
		painter.setBrush(color)
		painter.setPen(Qt.PenStyle.NoPen)
		painter.drawRoundedRect(icon_rect, 8, 8)

		if state == 1:
			c = icon_rect.center()
			triangle = QPolygon([
				c + QPoint(-6, -4),
				c + QPoint(-6, 4),
				c + QPoint(4, 0),
			])
			painter.setBrush(QColor("#ffffff"))
			painter.drawPolygon(triangle)

		text_rect = QRect(rect.x(), icon_y + self.icon_size + 4, rect.width(), rect.height() - self.icon_size - 12)
		painter.setPen(text_color)
		painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, name)

		painter.restore()

	def sizeHint(self, option, index: QModelIndex) -> QSize:
		return QSize(96, 96)
