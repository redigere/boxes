from typing import Optional
import subprocess
import os
import shutil

from boxes.backends import BaseBackend
from boxes.models.config import BoxConfig
from boxes.models.machine import MachineState


class XenBackend(BaseBackend):
	def __init__(self) -> None:
		super().__init__()
		self.capabilities.snapshots = True
		self.capabilities.live_migration = True
		self.capabilities.storage_pools = True
		self.capabilities.networks = True
		self._xl_path: Optional[str] = None
		self._xen_version: Optional[str] = None

	def connect(self) -> bool:
		self._xl_path = shutil.which("xl")
		if self._xl_path is None:
			self._xl_path = shutil.which("xm")
		if self._xl_path is None:
			self._connected = False
			return False
		if not os.path.exists("/proc/xen"):
			self._connected = False
			return False
		try:
			result = subprocess.run(
				[self._xl_path, "info"], capture_output=True, text=True, timeout=5
			)
			if result.returncode != 0:
				self._connected = False
				return False
			for line in result.stdout.split("\n"):
				if "xen_version" in line or "xen_major" in line:
					self._xen_version = line.split(":")[-1].strip()
					break
			self._connected = True
			return True
		except (subprocess.TimeoutExpired, FileNotFoundError):
			self._connected = False
			return False

	def disconnect(self) -> None:
		self._connected = False

	def _run_xl(self, cmd: str) -> Optional[str]:
		if self._xl_path is None:
			return None
		try:
			result = subprocess.run(
				[self._xl_path] + cmd.split(), capture_output=True, text=True, timeout=30
			)
			if result.returncode == 0:
				return result.stdout.strip()
			return None
		except (subprocess.TimeoutExpired, FileNotFoundError):
			return None

	def list_machines(self) -> list[dict]:
		out = self._run_xl("list -l")
		if out is None:
			return []
		results = []
		import json as _json

		try:
			entries = _json.loads(out) if out.startswith("[") else [_json.loads(out)]
			for entry in entries if isinstance(entries, list) else [entries]:
				domid = entry.get("domid", -1)
				results.append(
					{
						"name": entry.get("name", "unknown"),
						"uuid": entry.get("uuid", ""),
						"state": 1 if domid >= 0 else 0,
						"max_mem": entry.get("memory", {}).get("current", 0),
						"vcpus": len(entry.get("vcpus", [])),
						"id": domid,
						"active": domid >= 0,
					}
				)
		except (_json.JSONDecodeError, ValueError):
			return results
		return results

	def define_machine(self, config: BoxConfig) -> Optional[str]:
		cfg = self._build_xen_config(config)
		cfg_path = f"/etc/xen/{config.name}.cfg"
		try:
			with open(cfg_path, "w") as f:
				f.write(cfg)
			return config.uuid
		except PermissionError:
			return None

	def undefine_machine(self, backend_id: str) -> bool:
		result = self._run_xl(f"destroy {backend_id}")
		return result is not None

	def start_machine(self, backend_id: str) -> bool:
		result = self._run_xl(f"create {backend_id}")
		return result is not None

	def shutdown_machine(self, backend_id: str) -> bool:
		result = self._run_xl(f"shutdown {backend_id}")
		return result is not None

	def pause_machine(self, backend_id: str) -> bool:
		result = self._run_xl(f"pause {backend_id}")
		return result is not None

	def resume_machine(self, backend_id: str) -> bool:
		result = self._run_xl(f"unpause {backend_id}")
		return result is not None

	def delete_machine(self, backend_id: str, keep_disks: bool = False) -> bool:
		self._run_xl(f"destroy {backend_id}")
		self._run_xl(f"delete {backend_id}")
		return True

	def get_state(self, backend_id: str) -> int:
		out = self._run_xl(f"list {backend_id}")
		if out is None:
			return MachineState.STOPPED
		parts = out.strip().split("\n")
		if len(parts) < 2:
			return MachineState.STOPPED
		fields = parts[1].split()
		if len(fields) < 5:
			return MachineState.STOPPED
		state_char = fields[4] if len(fields) > 4 else ""
		if "r" in state_char:
			return MachineState.RUNNING
		if "p" in state_char:
			return MachineState.PAUSED
		if "b" in state_char or "s" in state_char:
			return MachineState.SLEEPING
		return MachineState.STOPPED

	def create_disk_image(self, path: str, size_gb: int) -> bool:
		result = subprocess.run(
			["qemu-img", "create", "-f", "qcow2", path, f"{size_gb}G"], capture_output=True
		)
		return result.returncode == 0

	def get_display_address(self, backend_id: str) -> Optional[str]:
		return "127.0.0.1"

	def get_display_port(self, backend_id: str) -> Optional[int]:
		out = self._run_xl(f"list -l {backend_id}")
		if out is None:
			return None
		import re as _re

		match = _re.search(r"vncdisplay.*?(\d+)", out)
		if match:
			return 5900 + int(match.group(1))
		match = _re.search(r"display.*?(\d+)", out)
		if match:
			return int(match.group(1))
		return None

	def _build_xen_config(self, config: BoxConfig) -> str:
		return f"""# Xen config for {config.name}
name = "{config.name}"
uuid = "{config.uuid}"
memory = {config.memory_mb}
maxmem = {config.memory_mb}
vcpus = {config.vcpus}
maxvcpus = {config.vcpus}
builder = "hvm"
kernel = "/usr/lib/xen/boot/hvmloader"
boot = "d"
seabios = 1

disk = [
	'{config.disk_path or ""},qcow2,xvda,rw',
	'{config.iso_path or ""},raw,xvdb:cdrom,r'
]
vif = ['bridge=xenbr0']
vnc = 1
vnclisten = "127.0.0.1"
serial = "pty"
on_poweroff = "destroy"
on_reboot = "restart"
on_crash = "restart"
"""
