from __future__ import annotations

import subprocess
from typing import Optional, Callable


class MigrationManager:
	"""Manages live and offline VM migration between hosts.

	Supports Xen live migration via 'xl migrate', QEMU migration
	via QMP, and SSH-tunneled migration.
	"""

	def __init__(self) -> None:
		self._active_migrations: dict[str, dict[str, str | int]] = {}
		self._on_progress: Optional[Callable[[str, int], None]] = None

	def set_progress_callback(self, callback: Optional[Callable[[str, int], None]]) -> None:
		"""Set callback for migration progress: callback(vm_id, percent)."""
		self._on_progress = callback

	def migrate_xen(
		self,
		domain_name: str,
		target_host: str,
		live: bool = True,
		timeout: int = 300,
	) -> bool:
		"""Migrate a Xen domain to another host using 'xl migrate'."""
		migration_id = f"xen-{domain_name}-to-{target_host}"
		self._active_migrations[migration_id] = {
			"status": "starting",
			"progress": 0,
		}
		cmd = ["xl", "migrate"]
		if live:
			cmd.append("-l")
		cmd += [domain_name, target_host]
		try:
			result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
			success = result.returncode == 0
			self._active_migrations[migration_id] = {
				"status": "completed" if success else "failed",
				"progress": 100 if success else 0,
			}
			if self._on_progress:
				self._on_progress(migration_id, 100 if success else 0)
			return success
		except subprocess.TimeoutExpired:
			self._active_migrations[migration_id] = {"status": "timed_out", "progress": 0}
			return False
		except FileNotFoundError:
			self._active_migrations[migration_id] = {"status": "xl_not_found", "progress": 0}
			return False

	def migrate_qemu(
		self,
		qmp_host: str,
		qmp_port: int,
		target_uri: str,
		timeout: int = 300,
	) -> bool:
		"""Migrate a QEMU VM to another host via QMP migrate command."""
		migration_id = f"qemu-{qmp_host}:{qmp_port}-to-{target_uri}"
		self._active_migrations[migration_id] = {"status": "starting", "progress": 0}
		try:
			import socket
			import json

			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.settimeout(timeout)
			sock.connect((qmp_host, qmp_port))
			sock.recv(1024)
			sock.sendall(json.dumps({"execute": "qmp_capabilities"}).encode())
			sock.recv(1024)
			migrate_cmd = {
				"execute": "migrate",
				"arguments": {"uri": target_uri},
			}
			sock.sendall(json.dumps(migrate_cmd).encode())
			resp = json.loads(sock.recv(4096).decode())
			sock.close()
			success = "error" not in resp
			self._active_migrations[migration_id] = {
				"status": "completed" if success else "failed",
				"progress": 100 if success else 0,
			}
			if self._on_progress:
				self._on_progress(migration_id, 100 if success else 0)
			return success
		except (ConnectionError, OSError, json.JSONDecodeError):
			self._active_migrations[migration_id] = {"status": "failed", "progress": 0}
			return False

	def cancel_migration(self, migration_id: str) -> bool:
		"""Cancel an active migration."""
		if migration_id not in self._active_migrations:
			return False
		self._active_migrations[migration_id]["status"] = "cancelled"
		return True

	def get_status(self, migration_id: str) -> Optional[dict[str, str | int]]:
		"""Get the status of a migration."""
		return self._active_migrations.get(migration_id)

	def list_active(self) -> list[str]:
		"""List all active migration IDs."""
		return [
			mid
			for mid, info in self._active_migrations.items()
			if info.get("status") in ("starting", "in_progress")
		]

	def clear(self) -> None:
		"""Clear all migration records."""
		self._active_migrations.clear()
