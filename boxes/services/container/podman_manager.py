from __future__ import annotations

import os
import shutil
import subprocess
from typing import Optional

from boxes.constants import BOXES_IMAGES


class PodmanManager:
	CONTAINER = "boxes-qemu"
	IMAGE = "fedora:41"
	QEMU_PACKAGES = "qemu-system-x86 qemu-img qemu-user-static"

	def __init__(self) -> None:
		self._in_flatpak = bool(os.environ.get("FLATPAK_ID"))
		self._wrapper_dir = BOXES_IMAGES / ".wrappers"

	def _podman_cmd(self) -> list[str]:
		if self._in_flatpak:
			return ["flatpak-spawn", "--host", "podman"]
		return ["podman"]

	def _run(
		self, args: list[str], timeout: int = 60, text: bool = True
	) -> Optional[subprocess.CompletedProcess[str]]:
		try:
			return subprocess.run(
				self._podman_cmd() + args,
				capture_output=True,
				timeout=timeout,
				text=text,
			)
		except (FileNotFoundError, subprocess.TimeoutExpired):
			return None

	@property
	def available(self) -> bool:
		result = self._run(["version"], timeout=10)
		return result is not None and result.returncode == 0

	def container_exists(self) -> bool:
		result = self._run(
			["container", "exists", self.CONTAINER], timeout=10
		)
		return result is not None and result.returncode == 0

	def container_running(self) -> bool:
		result = self._run(
			["ps", "--filter", f"name={self.CONTAINER}", "--format", "{{.Names}}"],
			timeout=10,
		)
		if result is None or result.returncode != 0:
			return False
		return self.CONTAINER in result.stdout.strip()

	def ensure_image(self) -> bool:
		result = self._run(
			["image", "exists", self.IMAGE], timeout=10
		)
		if result is not None and result.returncode == 0:
			return True
		pull = self._run(["pull", self.IMAGE], timeout=300)
		return pull is not None and pull.returncode == 0

	def ensure_container(self) -> bool:
		if self.container_exists():
			if not self.container_running():
				start = self._run(["start", self.CONTAINER], timeout=30)
				return start is not None and start.returncode == 0
			return True
		if not self.ensure_image():
			return False
		create = self._run(
			[
				"create",
				"--name", self.CONTAINER,
				"--network", "host",
				"--privileged",
				"-v", f"{BOXES_IMAGES}:/data:Z",
				self.IMAGE,
				"sleep", "infinity",
			],
			timeout=30,
		)
		if create is None or create.returncode != 0:
			return False
		start = self._run(["start", self.CONTAINER], timeout=30)
		return start is not None and start.returncode == 0

	def install_qemu(self) -> bool:
		if not self.container_running():
			if not self.ensure_container():
				return False
		install = self._run(
			["exec", self.CONTAINER, "dnf", "install", "-y", self.QEMU_PACKAGES],
			timeout=300,
		)
		return install is not None and install.returncode == 0

	def exec(self, cmd: list[str], timeout: int = 30) -> Optional[subprocess.CompletedProcess[str]]:
		if not self.container_running():
			return None
		return self._run(["exec", self.CONTAINER] + cmd, timeout=timeout)

	def exec_detached(self, cmd: list[str]) -> Optional[str]:
		if not self.container_running():
			return None
		result = self._run(
			["exec", "-d", self.CONTAINER] + cmd, timeout=15
		)
		if result is not None and result.returncode == 0:
			return result.stdout.strip()
		return None

	def find_qemu_pid(self, uuid_prefix: str) -> Optional[int]:
		result = self._run(
			["exec", self.CONTAINER, "sh", "-c",
				f"pgrep -f 'qemu.*{uuid_prefix}'"],
			timeout=10,
		)
		if result is not None and result.returncode == 0 and result.stdout.strip():
			try:
				return int(result.stdout.strip().split("\n")[0])
			except ValueError:
				return None
		return None

	def _wrapper_content(self, binary: str) -> str:
		if self._in_flatpak:
			return (
				"#!/bin/sh\n"
				f"exec flatpak-spawn --host podman exec -d {self.CONTAINER} {binary} \"$@\"\n"
			)
		return (
			"#!/bin/sh\n"
			f"exec podman exec -d {self.CONTAINER} {binary} \"$@\"\n"
		)

	def _ensure_wrapper(self, name: str) -> Optional[str]:
		binary = {
			"qemu-system-x86_64": "qemu-system-x86_64",
			"qemu-img": "qemu-img",
		}.get(name)
		if binary is None:
			return None
		wrapper_path = self._wrapper_dir / name
		if wrapper_path.exists():
			return str(wrapper_path)
		self._wrapper_dir.mkdir(parents=True, exist_ok=True)
		try:
			wrapper_path.write_text(self._wrapper_content(binary))
			wrapper_path.chmod(0o755)
			return str(wrapper_path)
		except OSError:
			return None

	def ensure_wrappers(self) -> dict[str, Optional[str]]:
		return {
			"qemu-system-x86_64": self._ensure_wrapper("qemu-system-x86_64"),
			"qemu-img": self._ensure_wrapper("qemu-img"),
		}

	def get_qemu_path(self) -> Optional[str]:
		qemu = shutil.which("qemu-system-x86_64")
		if qemu:
			return qemu
		wrappers = self.ensure_wrappers()
		path = wrappers.get("qemu-system-x86_64")
		if path:
			return path
		container_qemu = self.exec(["sh", "-c", "which qemu-system-x86_64"], timeout=10)
		if container_qemu is not None and container_qemu.returncode == 0:
			return container_qemu.stdout.strip()
		if self.install_qemu():
			return self._ensure_wrapper("qemu-system-x86_64")
		return None

	def get_qemu_img_path(self) -> Optional[str]:
		qemu_img = shutil.which("qemu-img")
		if qemu_img:
			return qemu_img
		wrappers = self.ensure_wrappers()
		path = wrappers.get("qemu-img")
		if path:
			return path
		return None
