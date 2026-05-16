from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional

from boxes.constants import BOXES_IMAGES, QEMU_BINARIES
from boxes.models.config import BoxConfig


class QEMUProcess:
	def __init__(self, config: BoxConfig) -> None:
		self.config = config
		self.process: Optional[subprocess.Popen[bytes]] = None
		self.monitor_port: Optional[int] = None
		self.display_port: Optional[int] = None
		self.qmp_socket: Optional[str] = None

	def build_command(self) -> list[str]:
		binary = QEMU_BINARIES.get(self.config.arch, "qemu-system-x86_64")
		cmd = [binary]
		cmd += ["-name", self.config.name]
		cmd += ["-machine", f"{self.config.machine_type},accel=kvm:hax:whpx:tcg"]
		cmd += ["-cpu", self.config.cpu_model]
		cmd += ["-m", str(self.config.memory_mb)]
		cmd += ["-smp", str(self.config.vcpus)]
		cmd += [
			"-drive",
			f"file={self.config.disk_path},format=qcow2,if=virtio,aio=native,cache=unsafe",
		]
		if self.config.iso_path and Path(self.config.iso_path).exists():
			cmd += ["-cdrom", self.config.iso_path]
		cmd += ["-netdev", "user,id=net0"]
		cmd += ["-device", "virtio-net-pci,netdev=net0"]
		if self.config.graphics == "spice":
			self.display_port = self._find_free_port()
			cmd += ["-spice", f"port={self.display_port},disable-ticketing=on"]
			cmd += ["-vga", "qxl"]
		else:
			self.display_port = self._find_free_port()
			cmd += ["-vnc", f"127.0.0.1:{self.display_port}"]
			cmd += ["-vga", "virtio"]
		cmd += ["-usb"]
		cmd += ["-device", "usb-tablet"]
		cmd += ["-device", "virtio-balloon"]
		self.monitor_port = self._find_free_port()
		cmd += ["-qmp", f"tcp:127.0.0.1:{self.monitor_port},server,nowait"]
		cmd += ["-daemonize"]
		return cmd

	def start(self) -> bool:
		cmd = self.build_command()
		disks_dir = BOXES_IMAGES / self.config.uuid
		disks_dir.mkdir(parents=True, exist_ok=True)
		try:
			self.process = subprocess.Popen(
				cmd,
				stdout=subprocess.DEVNULL,
				stderr=subprocess.DEVNULL,
				cwd=str(disks_dir),
			)
			if self.process.pid and self.process.pid > 0:
				return True
			return False
		except FileNotFoundError:
			return False

	def stop(self) -> bool:
		if self.process and self.process.pid:
			try:
				os.kill(self.process.pid, signal.SIGTERM)
				time.sleep(2)
				if self.process.poll() is None:
					os.kill(self.process.pid, signal.SIGKILL)
				return True
			except Exception:
				return False
		return False

	def send_qmp(self, cmd: dict[str, object]) -> Optional[dict[str, object]]:
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.settimeout(5)
			s.connect(("127.0.0.1", self.monitor_port))
			s.recv(1024)
			s.sendall(json.dumps({"execute": "qmp_capabilities"}).encode())
			s.recv(1024)
			s.sendall(json.dumps(cmd).encode())
			resp = s.recv(65536).decode()
			s.close()
			resp_data = json.loads(resp)
			assert isinstance(resp_data, dict)
			return resp_data
		except Exception:
			return None

	def query_status(self) -> Optional[str]:
		if self.process is None:
			return None
		ret = self.process.poll()
		if ret is not None:
			return "stopped"
		resp = self.send_qmp({"execute": "query-status"})
		if resp and "return" in resp:
			return_val = resp["return"]
			assert isinstance(return_val, dict)
			return str(return_val.get("status", "running")).lower()
		return "running"

	def _find_free_port(self) -> int:
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
			s.bind(("", 0))
			port = s.getsockname()[1]
			assert isinstance(port, int)
			return port