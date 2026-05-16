from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional


class OVMFManager:
    """Manages OVMF (UEFI) firmware for VM boot.

    Handles detection, installation, and Secure Boot (SBAT)
    key enrollment for UEFI-based VMs.
    """

    OVMF_PACKAGES_APT = ["ovmf", "edk2-ovmf"]
    OVMF_PACKAGES_DNF = ["edk2-ovmf", "edk2-aarch64"]
    OVMF_PACKAGES_PACMAN = ["edk2-ovmf"]

    def __init__(self) -> None:
        self._code_path: Optional[str] = None
        self._vars_path: Optional[str] = None
        self._sbat_supported: bool = False
        self._secure_boot_enabled: bool = False

    @property
    def code_path(self) -> Optional[str]:
        return self._code_path

    @property
    def vars_path(self) -> Optional[str]:
        return self._vars_path

    @property
    def secure_boot_supported(self) -> bool:
        return self._sbat_supported

    @property
    def secure_boot_enabled(self) -> bool:
        return self._secure_boot_enabled

    def detect(self) -> bool:
        """Detect OVMF firmware on the system."""
        search_paths = [
            "/usr/share/edk2/ovmf/OVMF_CODE.fd",
            "/usr/share/ovmf/OVMF_CODE.fd",
            "/usr/share/qemu/ovmf-x86_64.bin",
            "/usr/share/edk2-ovmf/x64/OVMF_CODE.fd",
            "/usr/share/edk2/ovmf/OVMF_VARS.fd",
            "/usr/share/ovmf/OVMF_VARS.fd",
            "/usr/share/edk2-ovmf/x64/OVMF_VARS.fd",
        ]
        code_found = False
        for p in search_paths:
            path = Path(p)
            if not path.exists():
                continue
            if "CODE" in p or "ovmf-x86_64" in p:
                if self._code_path is None:
                    self._code_path = str(path)
                    code_found = True
            elif "VARS" in p:
                if self._vars_path is None:
                    self._vars_path = str(path)
        self._sbat_supported = self._check_sbat()
        return code_found

    def _check_sbat(self) -> bool:
        """Check if OVMF supports SBAT (Secure Boot Advanced Targeting)."""
        if self._code_path:
            try:
                result = subprocess.run(
                    ["strings", self._code_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                return "sbat" in result.stdout.lower()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        return False

    def install(self) -> bool:
        """Install OVMF packages via system package manager."""
        if self.detect():
            return True
        pkg_manager = None
        if shutil.which("apt"):
            pkg_manager = ["apt", "install", "-y"] + self.OVMF_PACKAGES_APT
        elif shutil.which("dnf"):
            pkg_manager = ["dnf", "install", "-y"] + self.OVMF_PACKAGES_DNF
        elif shutil.which("pacman"):
            pkg_manager = ["pacman", "-S", "--noconfirm"] + self.OVMF_PACKAGES_PACMAN
        if pkg_manager is None:
            return False
        try:
            result = subprocess.run(pkg_manager, capture_output=True, timeout=120)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def enable_secure_boot(self) -> bool:
        """Enable Secure Boot (requires OVMF with SBAT support)."""
        if not self._sbat_supported:
            return False
        self._secure_boot_enabled = True
        return True

    def disable_secure_boot(self) -> None:
        """Disable Secure Boot."""
        self._secure_boot_enabled = False

    def get_qemu_args(self) -> list[str]:
        """Return QEMU command-line arguments for OVMF firmware."""
        args: list[str] = []
        if self._code_path:
            args += ["-bios", self._code_path]
        return args

    def get_qemu_uefi_args(self) -> list[str]:
        """Return QEMU args for UEFI boot with optional Secure Boot."""
        args: list[str] = []
        if self._code_path:
            args += ["-drive", f"if=pflash,format=raw,readonly=on,file={self._code_path}"]
        if self._vars_path:
            args += ["-drive", f"if=pflash,format=raw,file={self._vars_path}"]
        if self._secure_boot_enabled:
            args += [
                "-machine", "smm=on",
                "-global", "driver=cfi.pflash01,property=secure,value=on",
            ]
        return args
