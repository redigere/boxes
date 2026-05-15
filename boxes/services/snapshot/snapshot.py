from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Snapshot:
    name: str
    description: str = ""
    timestamp: float = 0.0
    backend_id: str = ""
    state: int = 0
    disk_only: bool = False
    parent: str = ""
    children: list[str] | None = None

    def __post_init__(self) -> None:
        if self.children is None:
            self.children = []
