from __future__ import annotations

from pathlib import Path
from typing import Optional


class FirmwareManager:
	"""Firmware detection and selection for VM boot.

	Detects available firmware blobs (SeaBIOS, OVMF, UEFI,
	UEFI+CSM) and provides paths for QEMU/KVM VM creation.
	"""

	FIRMWARE_SEARCH_PATHS = [
		"/usr/share/seabios/bios.bin",
		"/usr/share/qemu/bios.bin",
		"/usr/share/edk2/ovmf/OVMF_CODE.fd",
		"/usr/share/ovmf/OVMF_CODE.fd",
		"/usr/share/qemu/ovmf-x86_64.bin",
		"/usr/share/edk2/ovmf/OVMF_VARS.fd",
		"/usr/share/ovmf/OVMF_VARS.fd",
		"/run/host/usr/share/seabios/bios.bin",
		"/run/host/usr/share/qemu/bios.bin",
		"/run/host/usr/share/edk2/ovmf/OVMF_CODE.fd",
		"/run/host/usr/share/edk2/ovmf/OVMF_VARS.fd",
		"/usr/share/edk2-ovmf/x64/OVMF_CODE.fd",
		"/usr/share/edk2-ovmf/x64/OVMF_VARS.fd",
	]

	def __init__(self) -> None:
		self._firmware_cache: dict[str, Optional[str]] = {}

	def detect_all(self) -> dict[str, Optional[str]]:
		"""Detect all available firmware types."""
		result: dict[str, Optional[str]] = {
			"bios": None,
			"uefi": None,
			"uefi_vars": None,
		}
		for path_str in self.FIRMWARE_SEARCH_PATHS:
			p = Path(path_str)
			if not p.exists():
				continue
			name = p.name
			if "bios" in name:
				if result["bios"] is None:
					result["bios"] = str(p)
			elif "OVMF_CODE" in name or "OVMF" in name:
				if result["uefi"] is None:
					result["uefi"] = str(p)
			elif "OVMF_VARS" in name:
				if result["uefi_vars"] is None:
					result["uefi_vars"] = str(p)
		if result["bios"] is None:
			result["bios"] = self._find_seabios()
		if result["uefi"] is None:
			result["uefi"] = self._find_uefi()
		self._firmware_cache = result
		return result

	def get_firmware_path(self, firmware_type: str = "bios") -> Optional[str]:
		"""Get the path for a specific firmware type."""
		if firmware_type not in self._firmware_cache:
			self.detect_all()
		return self._firmware_cache.get(firmware_type)

	@staticmethod
	def _find_seabios() -> Optional[str]:
		"""Find SeaBIOS firmware blob."""
		paths = ["/usr/share/seabios/bios.bin", "/usr/share/qemu/bios.bin"]
		for p in paths:
			if Path(p).exists():
				return p
		return None

	@staticmethod
	def _find_uefi() -> Optional[str]:
		"""Find UEFI (OVMF) firmware blob."""
		paths = [
			"/usr/share/edk2/ovmf/OVMF_CODE.fd",
			"/usr/share/ovmf/OVMF_CODE.fd",
			"/usr/share/qemu/ovmf-x86_64.bin",
			"/usr/share/edk2-ovmf/x64/OVMF_CODE.fd",
		]
		for p in paths:
			if Path(p).exists():
				return p
		return None

	def is_uefi_available(self) -> bool:
		"""Check if UEFI firmware is available."""
		return self.get_firmware_path("uefi") is not None

	def is_bios_available(self) -> bool:
		"""Check if legacy BIOS firmware is available."""
		return self.get_firmware_path("bios") is not None
