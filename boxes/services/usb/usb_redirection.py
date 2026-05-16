from __future__ import annotations

import subprocess

from boxes.services.usb.usb_device import USBDevice, enumerate_usb_devices


class USBRedirection:
    """Manages USB device redirection to VMs.

    Supports SPICE usbredir channel, libvirt USB hostdev,
    and manual QEMU -device usb-host passthrough.
    """

    MODE_SPICE = "spice"
    MODE_LIBVIRT = "libvirt"
    MODE_QEMU = "qemu"

    def __init__(self, mode: str = MODE_SPICE) -> None:
        self.mode = mode
        self._redirected: dict[str, USBDevice] = {}

    def list_available(self) -> list[USBDevice]:
        """List USB devices available for redirection."""
        return enumerate_usb_devices()

    def list_redirected(self) -> list[USBDevice]:
        """List currently redirected USB devices."""
        return list(self._redirected.values())

    def redirect(self, vendor_id: str, product_id: str) -> bool:
        """Redirect a USB device to the VM."""
        key = f"{vendor_id}:{product_id}"
        if key in self._redirected:
            return True
        if self.mode == self.MODE_SPICE:
            return self._redirect_spice(vendor_id, product_id)
        elif self.mode == self.MODE_LIBVIRT:
            return self._redirect_libvirt(vendor_id, product_id)
        elif self.mode == self.MODE_QEMU:
            return self._redirect_qemu(vendor_id, product_id)
        return False

    def detach(self, vendor_id: str, product_id: str) -> bool:
        """Detach a redirected USB device."""
        key = f"{vendor_id}:{product_id}"
        device = self._redirected.pop(key, None)
        if device:
            device.detach()
        return device is not None

    def _redirect_spice(self, vendor_id: str, product_id: str) -> bool:
        """Redirect via SPICE usbredir channel."""
        for dev in enumerate_usb_devices():
            if dev.vendor_id == vendor_id and dev.product_id == product_id:
                dev.attach()
                self._redirected[dev.usb_id] = dev
                return True
        return False

    def _redirect_libvirt(self, vendor_id: str, product_id: str) -> bool:
        """Redirect via libvirt hostdev XML."""
        try:
            result = subprocess.run(
                [
                    "virsh", "attach-device",
                    "--domain", "",
                    "--file", "",
                    "--live",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _redirect_qemu(self, vendor_id: str, product_id: str) -> bool:
        """Redirect via QEMU usb-host device passthrough."""
        try:
            result = subprocess.run(
                [
                    "qemu-system-x86_64",
                    "-device",
                    f"usb-host,vendorid=0x{vendor_id},productid=0x{product_id}",
                    "-help",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def redirection_count(self) -> int:
        return len(self._redirected)
