from typing import Optional

try:
    from PyQt6.QtWidgets import QStyledItemDelegate, QStyle
    from PyQt6.QtCore import QModelIndex, QSize
    from PyQt6.QtGui import QPainter
except ImportError:
    QStyledItemDelegate = type("QStyledItemDelegate", (object,), {})
    QStyle = type("QStyle", (object,), {})
    QModelIndex = type("QModelIndex", (object,), {})
    QSize = type("QSize", (object,), {})
    QPainter = type("QPainter", (object,), {})


class ListViewDelegate(QStyledItemDelegate):
	def __init__(self, parent=None) -> None:
		super().__init__(parent)

	def paint(self, painter: Optional[QPainter], option, index: QModelIndex) -> None:
		if painter is None:
			return
		painter.save()
		palette = option.palette
		if option.state & QStyle.StateFlag.State_Selected:
			painter.fillRect(option.rect, palette.highlight())
		else:
			painter.fillRect(option.rect, palette.base())
		painter.restore()

	def sizeHint(self, option, index: QModelIndex) -> QSize:
		return QSize(0, 48)
