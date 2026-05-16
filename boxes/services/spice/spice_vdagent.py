from __future__ import annotations

import shutil
import subprocess
from typing import Optional


class SPICEVDAgent:
	"""Manager for the SPICE vdagent guest integration.

	Handles detection, installation, and communication with
	spice-vdagent on the guest for clipboard, file transfer,
	and display auto-resize.
	"""

	VDAGENT_BINARY = "spice-vdagent"
	VDAGENT_SERVICE = "spice-vdagentd"

	def __init__(self) -> None:
		self._host_agent_available: Optional[bool] = None
		self._guest_agent_running: bool = False

	@property
	def host_agent_installed(self) -> bool:
		"""Check if spice-vdagent is installed on the host."""
		if self._host_agent_available is None:
			self._host_agent_available = shutil.which(self.VDAGENT_BINARY) is not None
		return self._host_agent_available

	@property
	def guest_agent_running(self) -> bool:
		return self._guest_agent_running

	@guest_agent_running.setter
	def guest_agent_running(self, value: bool) -> None:
		self._guest_agent_running = value

	def detect_in_guest(self, ssh_cmd: Optional[list[str]] = None) -> bool:
		"""Detect if spice-vdagent is running inside the guest."""
		if ssh_cmd:
			try:
				result = subprocess.run(
					ssh_cmd + ["pgrep", "-x", self.VDAGENT_BINARY],
					capture_output=True,
					timeout=10,
				)
				self._guest_agent_running = result.returncode == 0
				return self._guest_agent_running
			except (subprocess.TimeoutExpired, FileNotFoundError):
				return False
		return False

	def install_guest_agent(self, ssh_cmd: Optional[list[str]] = None) -> bool:
		"""Install spice-vdagent in the guest via SSH."""
		if not ssh_cmd:
			return False
		try:
			result = subprocess.run(
				ssh_cmd + ["which", self.VDAGENT_BINARY],
				capture_output=True,
				timeout=10,
			)
			if result.returncode == 0:
				self._guest_agent_running = True
				return True
			if shutil.which("apt"):
				install_cmd = ["apt", "install", "-y", "spice-vdagent"]
			elif shutil.which("dnf"):
				install_cmd = ["dnf", "install", "-y", "spice-vdagent"]
			elif shutil.which("yum"):
				install_cmd = ["yum", "install", "-y", "spice-vdagent"]
			elif shutil.which("pacman"):
				install_cmd = ["pacman", "-S", "--noconfirm", "spice-vdagent"]
			else:
				return False
			result = subprocess.run(
				ssh_cmd + install_cmd,
				capture_output=True,
				timeout=120,
			)
			self._guest_agent_running = result.returncode == 0
			return self._guest_agent_running
		except (subprocess.TimeoutExpired, FileNotFoundError):
			return False

	def start_guest_agent(self, ssh_cmd: Optional[list[str]] = None) -> bool:
		"""Start spice-vdagent in the guest."""
		if not ssh_cmd:
			return False
		try:
			result = subprocess.run(
				ssh_cmd + [self.VDAGENT_BINARY],
				capture_output=True,
				timeout=10,
			)
			self._guest_agent_running = result.returncode == 0
			return self._guest_agent_running
		except (subprocess.TimeoutExpired, FileNotFoundError):
			return False

	def restart_guest_service(self, ssh_cmd: Optional[list[str]] = None) -> bool:
		"""Restart the SPICE vdagent service in the guest."""
		if not ssh_cmd:
			return False
		try:
			result = subprocess.run(
				ssh_cmd + ["systemctl", "restart", self.VDAGENT_SERVICE],
				capture_output=True,
				timeout=15,
			)
			if result.returncode != 0:
				result = subprocess.run(
					ssh_cmd + ["systemctl", "start", self.VDAGENT_SERVICE],
					capture_output=True,
					timeout=15,
				)
			return result.returncode == 0
		except (subprocess.TimeoutExpired, FileNotFoundError):
			return False

	@staticmethod
	def install_host_support() -> bool:
		"""Install spice-vdagent on the host system."""
		if shutil.which("apt"):
			cmd = ["apt", "install", "-y", "spice-vdagent"]
		elif shutil.which("dnf"):
			cmd = ["dnf", "install", "-y", "spice-vdagent"]
		elif shutil.which("yum"):
			cmd = ["yum", "install", "-y", "spice-vdagent"]
		elif shutil.which("pacman"):
			cmd = ["pacman", "-S", "--noconfirm", "spice-vdagent"]
		else:
			return False
		try:
			result = subprocess.run(cmd, capture_output=True, timeout=120)
			return result.returncode == 0
		except (subprocess.TimeoutExpired, FileNotFoundError):
			return False
