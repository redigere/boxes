from __future__ import annotations

from typing import Optional
from pathlib import Path


class SharedFoldersManager:
    def __init__(self, base_dir: str = "") -> None:
        from boxes.services.shared_folder import SharedFolder

        self._folders: list[SharedFolder] = []
        self._base_dir = Path(base_dir) if base_dir else Path.cwd()

    def add(self, host_path: str, guest_path: str = "", readonly: bool = False) -> bool:
        from boxes.services.shared_folder import SharedFolder

        folder = SharedFolder(
            host_path=host_path,
            guest_path=guest_path or host_path,
            readonly=readonly,
        )
        self._folders.append(folder)
        return True

    def remove(self, host_path: str) -> bool:
        for i, f in enumerate(self._folders):
            if f.host_path == host_path:
                self._folders.pop(i)
                return True
        return False

    def list(self) -> list:
        return list(self._folders)

    def get(self, host_path: str) -> Optional:
        for f in self._folders:
            if f.host_path == host_path:
                return f
        return None

    def clear(self) -> None:
        self._folders.clear()

    @property
    def count(self) -> int:
        return len(self._folders)
