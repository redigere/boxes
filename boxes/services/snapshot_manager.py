from __future__ import annotations

from typing import Optional
from pathlib import Path


class SnapshotManager:
    def __init__(self, snapshots_dir: str = "") -> None:
        self._snapshots: list = []
        self._snapshots_dir = Path(snapshots_dir) if snapshots_dir else Path.cwd()

    def create(self, name: str, description: str = "") -> bool:
        from boxes.services.snapshot import Snapshot

        snap = Snapshot(name=name, description=description)
        self._snapshots.append(snap)
        return True

    def delete(self, name: str) -> bool:
        for i, snap in enumerate(self._snapshots):
            if snap.name == name:
                self._snapshots.pop(i)
                return True
        return False

    def revert(self, name: str) -> bool:
        for snap in self._snapshots:
            if snap.name == name:
                return True
        return False

    def list(self) -> list:
        return list(self._snapshots)

    def get(self, name: str) -> Optional:
        for snap in self._snapshots:
            if snap.name == name:
                return snap
        return None

    @property
    def count(self) -> int:
        return len(self._snapshots)
