from typing import Optional
from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt
from PyQt6.QtGui import QIcon

from boxes.models.machine import Machine
from boxes.models.config import BoxConfig


class MachineCollection(QAbstractListModel):
    def __init__(self) -> None:
        super().__init__()
        self._machines: list[Machine] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._machines)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        m = self._machines[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return m.name
        if role == Qt.ItemDataRole.DecorationRole:
            return QIcon.fromTheme("computer")
        if role == Qt.ItemDataRole.UserRole:
            return m
        if role == Qt.ItemDataRole.ToolTipRole:
            return f"{m.name} — {m.status_text}"
        if role == Qt.ItemDataRole.StatusTipRole:
            return m.status_text
        return None

    def add(self, machine: Machine) -> None:
        self.beginInsertRows(QModelIndex(), len(self._machines), len(self._machines))
        self._machines.append(machine)
        self.endInsertRows()

    def remove(self, machine: Machine) -> None:
        idx = self._machines.index(machine)
        self.beginRemoveRows(QModelIndex(), idx, idx)
        self._machines.remove(machine)
        self.endRemoveRows()

    def get(self, row: int) -> Optional[Machine]:
        if 0 <= row < len(self._machines):
            return self._machines[row]
        return None

    def find_by_uuid(self, uuid: str) -> Optional[Machine]:
        for m in self._machines:
            if m.config.uuid == uuid:
                return m
        return None

    def find_by_name(self, name: str) -> Optional[Machine]:
        for m in self._machines:
            if m.name == name:
                return m
        return None

    def load_all(self) -> None:
        for config in BoxConfig.list_all():
            self.add(Machine(config))

    def __iter__(self):
        return iter(self._machines)

    def __len__(self):
        return len(self._machines)
