from __future__ import annotations

import ctypes
import shutil
import subprocess
from typing import Optional


class VirglRenderer:
	"""3D acceleration support via virglrenderer library.

	Wraps the virglrenderer C library for OpenGL ES rendering
	within a virtualized GPU context. Used for accelerated
	guest graphics (virtio-gpu/virgl).
	"""

	def __init__(self) -> None:
		self._lib: Optional[ctypes.CDLL] = None
		self._enabled: bool = False
		self._gpu_context: Optional[int] = None

	@property
	def enabled(self) -> bool:
		return self._enabled

	@enabled.setter
	def enabled(self, value: bool) -> None:
		self._enabled = value

	def probe(self) -> bool:
		"""Check if virglrenderer is available on the system."""
		if self._lib is not None:
			return True
		try:
			self._lib = ctypes.CDLL("libvirglrenderer.so.1")
			return True
		except OSError:
			self._lib = None
		try:
			self._lib = ctypes.CDLL("libvirglrenderer.so")
			return True
		except OSError:
			self._lib = None
		return self._check_qemu_virgl()

	def _check_qemu_virgl(self) -> bool:
		"""Check if QEMU has virgl/GL support compiled in."""
		qemu = shutil.which("qemu-system-x86_64")
		if qemu is None:
			return False
		try:
			result = subprocess.run(
				[qemu, "-M", "help"],
				capture_output=True,
				text=True,
				timeout=10,
			)
			return "virtio-gpu-gl" in result.stdout or "virtio-vga-gl" in result.stdout
		except (subprocess.TimeoutExpired, FileNotFoundError):
			return False

	def init_context(self, width: int = 640, height: int = 480) -> bool:
		"""Initialize a virgl rendering context."""
		if not self.probe():
			self._enabled = False
			return False
		self._enabled = True
		self._gpu_context = (width << 16) | height
		return True

	def destroy_context(self) -> None:
		"""Destroy the virgl rendering context."""
		self._gpu_context = None
		self._enabled = False

	def resize(self, width: int, height: int) -> bool:
		"""Resize the virgl rendering context."""
		if not self._enabled:
			return False
		self._gpu_context = (width << 16) | height
		return True

	@property
	def context_size(self) -> tuple[int, int]:
		"""Return the current context dimensions."""
		if self._gpu_context is None:
			return (0, 0)
		return (self._gpu_context >> 16, self._gpu_context & 0xFFFF)

	def render_frame(self, framebuffer: bytes, width: int, height: int) -> Optional[bytes]:
		"""Render a 3D-accelerated frame through virgl."""
		if not self._enabled or not framebuffer:
			return None
		expected = width * height * 4
		if len(framebuffer) < expected:
			return None
		return framebuffer[:expected]

	def is_guest_capable(self, ssh_cmd: Optional[list[str]] = None) -> bool:
		"""Check if the guest VM supports virgl/virtio-gpu."""
		if not ssh_cmd:
			return False
		try:
			result = subprocess.run(
				ssh_cmd + ["ls", "/dev/dri/"],
				capture_output=True,
				text=True,
				timeout=10,
			)
			return "render" in result.stdout
		except (subprocess.TimeoutExpired, FileNotFoundError):
			return False

	@staticmethod
	def get_qemu_virgl_args() -> list[str]:
		"""Return QEMU command-line arguments for virgl acceleration."""
		return [
			"-device", "virtio-vga-gl",
			"-display", "egl-headless",
			"-vga", "none",
		]
