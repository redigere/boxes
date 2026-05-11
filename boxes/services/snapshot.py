from typing import Optional
from dataclasses import dataclass, asdict
import json

from boxes.constants import BOXES_DATA


@dataclass
class Snapshot:
    name: str
    timestamp: str
    description: str = ""
    disk_path: Optional[str] = None


class SnapshotManager:
    def __init__(self, machine_uuid: str) -> None:
        self.machine_uuid = machine_uuid
        self._snapshots_dir = BOXES_DATA / "snapshots" / machine_uuid
        self._snapshots: list[Snapshot] = []
        self._load()

    def _load(self) -> None:
        index = self._snapshots_dir / "index.json"
        if index.exists():
            data = json.loads(index.read_text())
            self._snapshots = [Snapshot(**s) for s in data.get("snapshots", [])]

    def _save(self) -> None:
        self._snapshots_dir.mkdir(parents=True, exist_ok=True)
        index = self._snapshots_dir / "index.json"
        index.write_text(json.dumps(
            {"snapshots": [asdict(s) for s in self._snapshots]}, indent=2
        ))

    def create(self, name: str, description: str = "") -> Snapshot:
        from datetime import datetime
        snap = Snapshot(name=name, timestamp=datetime.now().isoformat(), description=description)
        self._snapshots.append(snap)
        self._save()
        return snap

    def list(self) -> list[Snapshot]:
        return list(self._snapshots)

    def delete(self, name: str) -> bool:
        initial = len(self._snapshots)
        self._snapshots = [s for s in self._snapshots if s.name != name]
        if len(self._snapshots) != initial:
            self._save()
            return True
        return False

    def restore(self, name: str) -> bool:
        for snap in self._snapshots:
            if snap.name == name:
                return True
        return False
