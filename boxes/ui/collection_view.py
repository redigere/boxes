from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QListView, QAbstractItemView

from boxes.ui.icon_view_delegate import IconViewDelegate
from boxes.ui.list_view_delegate import ListViewDelegate


class CollectionView(QListView):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setUniformItemSizes(True)
        self.setSpacing(4)
        self.set_icon_mode()

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
