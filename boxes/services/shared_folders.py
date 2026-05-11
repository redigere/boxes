from dataclasses import dataclass, asdict
import json

from boxes.constants import BOXES_CONFIG


@dataclass
class SharedFolder:
    host_path: str
    guest_path: str
    enabled: bool = True
    read_only: bool = False


class SharedFoldersManager:
    def __init__(self) -> None:
        self._config_path = BOXES_CONFIG / "shared_folders.json"
        self._folders: list[SharedFolder] = []
        self._load()

    def _load(self) -> None:
        if self._config_path.exists():
            data = json.loads(self._config_path.read_text())
            self._folders = [SharedFolder(**f) for f in data.get("folders", [])]

    def _save(self) -> None:
        BOXES_CONFIG.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(json.dumps(
            {"folders": [asdict(f) for f in self._folders]}, indent=2
        ))

    def add(self, host_path: str, guest_path: str, read_only: bool = False) -> None:
        self._folders.append(SharedFolder(host_path, guest_path, read_only=read_only))
        self._save()

    def remove(self, host_path: str) -> None:
        self._folders = [f for f in self._folders if f.host_path != host_path]
        self._save()

    def list(self) -> list[SharedFolder]:
        return list(self._folders)

    def toggle(self, host_path: str) -> None:
        for f in self._folders:
            if f.host_path == host_path:
                f.enabled = not f.enabled
                break
        self._save()
