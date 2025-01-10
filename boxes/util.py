import shutil
import subprocess
from pathlib import Path
from typing import Optional


def find_qemu_binary(arch: str = "x86_64") -> Optional[str]:
    binaries = {
        "x86_64": ["qemu-system-x86_64", "qemu-kvm"],
        "aarch64": ["qemu-system-aarch64"],
        "i386": ["qemu-system-i386"],
    }
    for binary in binaries.get(arch, []):
        path = shutil.which(binary)
        if path:
            return path
    return None


def detect_host_arch() -> str:
    try:
        result = subprocess.run(["uname", "-m"], capture_output=True, text=True)
        arch = result.stdout.strip()
        mapping = {"x86_64": "x86_64", "aarch64": "aarch64", "arm64": "aarch64",
                   "i386": "i386", "i686": "i386", "amd64": "x86_64"}
        return mapping.get(arch, "x86_64")
    except FileNotFoundError:
        return "x86_64"


def check_kvm_available() -> bool:
    return Path("/dev/kvm").exists()


def check_libvirt_available() -> bool:
    return shutil.which("virsh") is not None


def human_size(bytes_val: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} PB"


def truncate_text(text: str, max_len: int = 60) -> str:
    return text[:max_len - 3] + "..." if len(text) > max_len else text
