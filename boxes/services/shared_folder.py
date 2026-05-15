from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SharedFolder:
    host_path: str = ""
    guest_path: str = ""
    readonly: bool = False
    name: str = ""
    options: dict[str, str] = field(default_factory=dict)
