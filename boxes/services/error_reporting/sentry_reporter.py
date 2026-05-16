from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from boxes.constants import BOXES_CONFIG


class SentryReporter:
	"""Error reporting integration.

	Collects diagnostics, captures crash contexts, and forwards
	them to a configurable error-reporting endpoint (Sentry,
	local files, or stdout).
	"""

	MODE_SENTRY = "sentry"
	MODE_FILE = "file"
	MODE_STDOUT = "stdout"
	MODE_DISABLED = "disabled"

	def __init__(self, mode: str = MODE_FILE) -> None:
		self.mode = mode
		self._dsn: str = ""
		self._environment: str = os.environ.get("BOXES_ENV", "production")
		self._release: str = ""
		self._reports_dir = BOXES_CONFIG / "error_reports"
		self._session_id: str = str(uuid.uuid4())[:8]

	def configure_sentry(self, dsn: str, release: str = "") -> None:
		"""Configure Sentry DSN for remote error reporting."""
		self.mode = self.MODE_SENTRY
		self._dsn = dsn
		self._release = release

	def configure_file_reports(self, dir_path: Optional[str] = None) -> None:
		"""Configure file-based error reporting."""
		self.mode = self.MODE_FILE
		if dir_path:
			self._reports_dir = Path(dir_path)
		self._reports_dir.mkdir(parents=True, exist_ok=True)

	def capture_exception(self, exc: Exception, context: Optional[dict] = None) -> Optional[str]:
		"""Capture an exception and report it.

		Returns a report ID on success, None if reporting is disabled.
		"""
		if self.mode == self.MODE_DISABLED:
			return None
		report_id = str(uuid.uuid4())
		report = {
			"report_id": report_id,
			"session_id": self._session_id,
			"timestamp": datetime.now().isoformat(),
			"environment": self._environment,
			"release": self._release,
			"error_type": type(exc).__name__,
			"error_message": str(exc),
			"context": context or {},
		}
		if self.mode == self.MODE_FILE:
			self._write_report(report_id, report)
		elif self.mode == self.MODE_STDOUT:
			print(f"[ERROR] {json.dumps(report, indent=2)}")
		elif self.mode == self.MODE_SENTRY:
			self._send_to_sentry(report)
		return report_id

	def _write_report(self, report_id: str, report: dict) -> None:
		"""Write an error report to the local filesystem."""
		self._reports_dir.mkdir(parents=True, exist_ok=True)
		report_path = self._reports_dir / f"{report_id}.json"
		report_path.write_text(json.dumps(report, indent=2))

	def _send_to_sentry(self, report: dict) -> None:
		"""Send an error report to Sentry (placeholder)."""
		if not self._dsn:
			self._write_report(report["report_id"], report)
			return
		try:
			import urllib.request
			import json as _json

			data = _json.dumps(report).encode()
			req = urllib.request.Request(
				self._dsn,
				data=data,
				headers={"Content-Type": "application/json"},
			)
			urllib.request.urlopen(req, timeout=10)
		except (OSError, ImportError):
			self._write_report(report["report_id"], report)

	def list_reports(self) -> list[dict]:
		"""List all local error reports."""
		if not self._reports_dir.exists():
			return []
		reports = []
		for f in sorted(self._reports_dir.iterdir()):
			if f.suffix == ".json":
				try:
					reports.append(json.loads(f.read_text()))
				except (json.JSONDecodeError, OSError):
					continue
		return reports

	def clear_reports(self) -> int:
		"""Delete all local error reports. Returns count deleted."""
		count = 0
		if self._reports_dir.exists():
			for f in self._reports_dir.iterdir():
				if f.suffix == ".json":
					try:
						f.unlink()
						count += 1
					except OSError:
						continue
		return count

	@staticmethod
	def from_config() -> SentryReporter:
		"""Load reporter config from boxes config file."""
		config_path = BOXES_CONFIG / "error_reporting.json"
		reporter = SentryReporter(mode=SentryReporter.MODE_FILE)
		if config_path.exists():
			try:
				data = json.loads(config_path.read_text())
				reporter.mode = data.get("mode", SentryReporter.MODE_FILE)
				reporter._dsn = data.get("dsn", "")
				reporter._release = data.get("release", "")
				reporter._environment = data.get("environment", "production")
			except (json.JSONDecodeError, OSError):
				reporter.mode = SentryReporter.MODE_FILE
		return reporter
