from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DiagnosticRecord:
	timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
	operation: str = ""
	component: str = ""
	success: bool = False
	error_type: str = ""
	error_message: str = ""
	traceback: str = ""
	context: dict[str, str | bool] = field(default_factory=dict)
	resolution: str = ""
