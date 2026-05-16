from __future__ import annotations

import shutil
import subprocess
from typing import Optional


class VDAgentManager:
	"""Manages the SPICE vdagent for guest/host clipboard, file transfer, and display."""

	VDAGENT_BINARY = "spice-vdagent"
	VDAGENTD_SERVICE = "spice-vdagentd"
	VDAGENTD_SOCKET = "/var/run/spice-vdagentd/spice-vdagent-sock"

	def __init__(self) -> None:
		self._host_available: Optional[bool] = None
		self._guest_available: Optional[bool] = None
		self._active: bool = False

	@property
	def active(self) -> bool:
		return self._active

	def activate(self) -> bool:
		"""Activate the vdagent service."""
		self._active = True
		return True

	def deactivate(self) -> None:
		"""Deactivate the vdagent service."""
		self._active = False

	def is_host_supported(self) -> bool:
		"""Check if the host has vdagent support installed."""
		if self._host_available is None:
			self._host_available = shutil.which(self.VDAGENT_BINARY) is not None
		return self._host_available

	def is_guest_running(self, ssh_cmd: Optional[list[str]] = None) -> bool:
		"""Check if vdagent is running in the guest."""
		if not ssh_cmd:
			return False
		try:
			result = subprocess.run(
				ssh_cmd + ["pgrep", "-x", self.VDAGENT_BINARY],
				capture_output=True,
				timeout=10,
			)
			return result.returncode == 0
		except (subprocess.TimeoutExpired, FileNotFoundError):
			return False

	def start_in_guest(self, ssh_cmd: Optional[list[str]] = None) -> bool:
		"""Start the vdagent in the guest VM."""
		if not ssh_cmd:
			return False
		try:
			result = subprocess.run(
				ssh_cmd + [self.VDAGENT_BINARY],
				capture_output=True,
				timeout=15,
			)
			return result.returncode == 0
		except (subprocess.TimeoutExpired, FileNotFoundError):
			return False

	def install_in_guest(self, ssh_cmd: Optional[list[str]] = None) -> bool:
		"""Install spice-vdagent in the guest VM."""
		if not ssh_cmd:
			return False
		try:
			result = subprocess.run(
				ssh_cmd + ["which", self.VDAGENT_BINARY],
				capture_output=True,
				timeout=10,
			)
			if result.returncode == 0:
				return True
			for pkg_manager in (
				["apt", "install", "-y", "spice-vdagent"],
				["dnf", "install", "-y", "spice-vdagent"],
				["pacman", "-S", "--noconfirm", "spice-vdagent"],
				["zypper", "install", "-y", "spice-vdagent"],
			):
				result = subprocess.run(
					ssh_cmd + pkg_manager,
					capture_output=True,
					timeout=120,
				)
				if result.returncode == 0:
					return True
			return False
		except (subprocess.TimeoutExpired, FileNotFoundError):
			return False

	@property
	def socket_path(self) -> str:
		return self.VDAGENTD_SOCKET

	def inject_clipboard(self, text: str) -> bool:
		"""Inject clipboard text into the guest via vdagent socket."""
		if not self._active:
			return False
		try:
			import socket as _socket

			sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
			sock.settimeout(5)
			sock.connect(self.VDAGENTD_SOCKET)
			sock.sendall(text.encode("utf-8"))
			sock.close()
			return True
		except (ConnectionError, OSError):
			return False
