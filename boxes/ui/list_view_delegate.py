from PyQt6.QtWidgets import QStyledItemDelegate, QStyle
from PyQt6.QtCore import QModelIndex, QSize
from PyQt6.QtGui import QPainter


class ListViewDelegate(QStyledItemDelegate):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

    def paint(self, painter: QPainter, option, index: QModelIndex) -> None:
        painter.save()
        palette = option.palette
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, palette.highlight())
        else:
            painter.fillRect(option.rect, palette.base())
        painter.restore()

    def sizeHint(self, option, index: QModelIndex) -> QSize:
        return QSize(0, 48)
