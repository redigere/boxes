from PyQt6.QtCore import Qt, QSize, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QFontMetrics
from PyQt6.QtWidgets import QStyledItemDelegate, QListView, QStyle, QAbstractItemView

from boxes.models.machine import Machine, MachineState


class IconViewDelegate(QStyledItemDelegate):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.icon_size = 96

    def paint(self, painter, option, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        machine = index.data(Qt.ItemDataRole.UserRole)
        name = index.data(Qt.ItemDataRole.DisplayRole) or "VM"
        rect = option.rect

        bg = QColor("#f8f9fa")
        if option.state & QStyle.StateFlag.State_Selected:
            bg = QColor("#e2e8f0")
        elif option.state & QStyle.StateFlag.State_MouseOver:
            bg = QColor("#eef2f6")
        painter.fillRect(rect, bg)

        cx = rect.x() + rect.width() // 2
        icon_r = QRect(cx - 48, rect.y() + 12, 96, 96)
        painter.setBrush(QBrush(QColor("#7c3aed")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(icon_r, 20, 20)
        painter.setPen(QPen(QColor("white"), 1))
        f = QFont("sans-serif", 28, QFont.Weight.Bold)
        painter.setFont(f)
        painter.drawText(icon_r, Qt.AlignmentFlag.AlignCenter, name[:2].upper())

        f = QFont("sans-serif", 11)
        painter.setFont(f)
        painter.setPen(QPen(QColor("#1f2937"), 1))
        text_r = QRect(rect.x(), icon_r.bottom() + 8, rect.width(), 20)
        painter.drawText(text_r, Qt.AlignmentFlag.AlignCenter, name)

        if machine:
            painter.setPen(QPen(QColor(MachineState.COLORS.get(machine.state, "#9aa0a6")), 1))
            f.setPointSize(9)
            painter.setFont(f)
            status_r = QRect(rect.x(), text_r.bottom(), rect.width(), 16)
            painter.drawText(status_r, Qt.AlignmentFlag.AlignCenter, machine.status_text)

        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(QPen(QColor("#6366f1"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)
        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        return QSize(140, 160)


class ListViewDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        machine = index.data(Qt.ItemDataRole.UserRole)
        name = index.data(Qt.ItemDataRole.DisplayRole) or "VM"
        rect = option.rect

        bg = QColor("white")
        if option.state & QStyle.StateFlag.State_Selected:
            bg = QColor("#e2e8f0")
        elif option.state & QStyle.StateFlag.State_MouseOver:
            bg = QColor("#f8fafc")
        painter.fillRect(rect, bg)

        icon_r = QRect(rect.x() + 8, rect.y() + 6, 36, 36)
        painter.setBrush(QBrush(QColor("#7c3aed")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(icon_r, 8, 8)
        painter.setPen(QPen(QColor("white"), 1))
        f = QFont("sans-serif", 12, QFont.Weight.Bold)
        painter.setFont(f)
        painter.drawText(icon_r, Qt.AlignmentFlag.AlignCenter, name[:2].upper())

        f = QFont("sans-serif", 12)
        painter.setFont(f)
        painter.setPen(QPen(QColor("#1f2937"), 1))
        painter.drawText(QRect(rect.x() + 52, rect.y() + 6, 260, 20),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)

        if machine:
            painter.setPen(QPen(QColor(MachineState.COLORS.get(machine.state, "#9aa0a6")), 1))
            f.setPointSize(10)
            painter.setFont(f)
            painter.drawText(QRect(rect.x() + 52, rect.y() + 26, 260, 16),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             machine.status_text)

            info = f"{machine.config.memory_mb} MB  |  {machine.config.vcpus} vCPU"
            painter.setPen(QPen(QColor("#64748b"), 1))
            painter.drawText(QRect(rect.right() - 240, rect.y(), 220, 48),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, info)

        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(QPen(QColor("#6366f1"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 4, 4)
        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        return QSize(0, 48)


class CollectionView(QListView):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setUniformItemSizes(True)
        self.setSpacing(4)
        self.setIconMode()

    def set_icon_mode(self) -> None:
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setIconSize(QSize(96, 96))
        self.setGridSize(QSize(140, 170))
        self.setWrapping(True)
        self.setWordWrap(True)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setItemDelegate(IconViewDelegate(self))

    def set_list_mode(self) -> None:
        self.setViewMode(QListView.ViewMode.ListMode)
        self.setGridSize(QSize())
        self.setWrapping(False)
        self.setWordWrap(False)
        self.setItemDelegate(ListViewDelegate(self))
