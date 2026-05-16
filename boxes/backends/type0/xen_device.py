from typing import Optional
import os
import ctypes
from pathlib import Path


XEN_DEV_PRIVCMD = "/dev/xen/privcmd"
XEN_DEV_EVTCHN = "/dev/xen/evtchn"
XEN_DEV_GNTTAB = "/dev/xen/gnttab"


class XenDevice:
	def __init__(self) -> None:
		self._privcmd_fd: Optional[int] = None
		self._xc: Optional[ctypes.CDLL] = None

	def probe(self) -> bool:
		if Path(XEN_DEV_PRIVCMD).exists():
			return True
		for lib in ("libxenctrl.so.4.17", "libxenctrl.so.4.16", "libxenctrl.so"):
			try:
				ctypes.CDLL(lib)
				return True
			except OSError:
				continue
		return False

	def open(self) -> bool:
		try:
			self._privcmd_fd = os.open(XEN_DEV_PRIVCMD, os.O_RDWR | os.O_CLOEXEC)
			return True
		except (OSError, FileNotFoundError, PermissionError):
			self._privcmd_fd = None
		for lib in ("libxenctrl.so.4.17", "libxenctrl.so.4.16", "libxenctrl.so"):
			try:
				self._xc = ctypes.CDLL(lib)
				return True
			except OSError:
				continue
		return False

	def close(self) -> None:
		if self._privcmd_fd is not None:
			try:
				os.close(self._privcmd_fd)
			except OSError:
				self._privcmd_fd = None
			self._privcmd_fd = None
		self._xc = None

	@property
	def is_open(self) -> bool:
		return self._privcmd_fd is not None or self._xc is not None
