from __future__ import annotations

import subprocess
from typing import Optional


class USBDevice:
	"""Represents a physical USB device on the host.

	Handles enumeration via lsusb / libusb and provides
	device descriptors for redirection.
	"""

	def __init__(
		self,
		vendor_id: str = "",
		product_id: str = "",
		bus: str = "",
		device: str = "",
		manufacturer: str = "",
		product: str = "",
	) -> None:
		self.vendor_id = vendor_id
		self.product_id = product_id
		self.bus = bus
		self.device = device
		self.manufacturer = manufacturer
		self.product = product
		self._attached: bool = False

	@property
	def attached(self) -> bool:
		return self._attached

	def attach(self) -> bool:
		"""Mark the device as attached/redirected."""
		self._attached = True
		return True

	def detach(self) -> bool:
		"""Mark the device as detached."""
		self._attached = False
		return True

	@property
	def usb_id(self) -> str:
		return f"{self.vendor_id}:{self.product_id}"

	@property
	def description(self) -> str:
		parts = [p for p in [self.manufacturer, self.product] if p]
		return " ".join(parts) if parts else f"USB Device ({self.usb_id})"

	def __repr__(self) -> str:
		return f"USBDevice({self.usb_id} {self.description})"


def enumerate_usb_devices() -> list[USBDevice]:
	"""Enumerate USB devices on the host using lsusb."""
	devices: list[USBDevice] = []
	lsusb = _find_lsusb()
	if not lsusb:
		return _fallback_enumerate()
	try:
		result = subprocess.run(
			[lsusb], capture_output=True, text=True, timeout=10
		)
		if result.returncode != 0:
			return _fallback_enumerate()
		for line in result.stdout.strip().split("\n"):
			if not line.strip():
				continue
			parts = line.split()
			if len(parts) < 6:
				continue
			try:
				bus = parts[1]
				device = parts[3].rstrip(":")
				vendor_product = parts[5]
				if ":" not in vendor_product:
					continue
				vendor_id, product_id = vendor_product.split(":", 1)
				desc = " ".join(parts[6:]) if len(parts) > 6 else ""
				manufacturer, product_name = _parse_description(desc)
				devices.append(
					USBDevice(
						vendor_id=vendor_id,
						product_id=product_id,
						bus=bus,
						device=device,
						manufacturer=manufacturer,
						product=product_name,
					)
				)
			except (IndexError, ValueError):
				continue
	except (subprocess.TimeoutExpired, FileNotFoundError):
		return devices


def _find_lsusb() -> Optional[str]:
	import shutil

	return shutil.which("lsusb")


def _fallback_enumerate() -> list[USBDevice]:
	"""Fallback USB enumeration via /sys/bus/usb/devices."""
	from pathlib import Path

	devices: list[USBDevice] = []
	usb_path = Path("/sys/bus/usb/devices")
	if not usb_path.exists():
		return devices
	for dev_dir in usb_path.iterdir():
		if not dev_dir.is_dir():
			continue
		vendor_file = dev_dir / "idVendor"
		product_file = dev_dir / "idProduct"
		if vendor_file.exists() and product_file.exists():
			try:
				vendor_id = vendor_file.read_text().strip()
				product_id = product_file.read_text().strip()
				manufacturer = (dev_dir / "manufacturer").read_text().strip()
				product = (dev_dir / "product").read_text().strip()
				devices.append(
					USBDevice(
						vendor_id=vendor_id,
						product_id=product_id,
						manufacturer=manufacturer,
						product=product,
						bus=dev_dir.name,
					)
				)
			except OSError:
				continue
	return devices


def _parse_description(desc: str) -> tuple[str, str]:
	"""Parse the lsusb description line into manufacturer and product."""
	if not desc:
		return ("", "")
	parts = desc.split(None, 1)
	if len(parts) == 1:
		return ("", parts[0])
	if parts[0].endswith("Inc.") or parts[0].endswith(" Ltd."):
		return (parts[0], parts[1] if len(parts) > 1 else "")
	return ("", desc)
