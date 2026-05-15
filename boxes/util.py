import shutil
import subprocess
import os
import sys
import urllib.request
from pathlib import Path
from typing import Optional, Callable


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
        mapping = {
            "x86_64": "x86_64",
            "aarch64": "aarch64",
            "arm64": "aarch64",
            "i386": "i386",
            "i686": "i386",
            "amd64": "x86_64",
        }
        return mapping.get(arch, "x86_64")
    except FileNotFoundError:
        return "x86_64"


def check_kvm_available() -> bool:
    return Path("/dev/kvm").exists()


def check_xen_available() -> bool:
    if Path("/proc/xen").exists():
        return True
    if Path("/dev/xen/privcmd").exists():
        return True
    xl = shutil.which("xl")
    if xl:
        try:
            result = subprocess.run([xl, "info"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    return False


def check_libvirt_available() -> bool:
    return shutil.which("virsh") is not None


def check_hyperv_available() -> bool:
    if sys.platform not in ("win32", "cygwin"):
        return False
    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "Get-Command Get-VM -ErrorAction SilentlyContinue",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0 and "Get-VM" in (result.stdout or "")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_macos_hvf_available() -> bool:
    if sys.platform != "darwin":
        return False
    try:
        result = subprocess.run(
            ["sysctl", "-n", "kern.hv_support"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip() == "1":
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    try:
        import ctypes

        lib = ctypes.CDLL("/System/Library/Frameworks/Hypervisor.framework/Hypervisor")
        return lib is not None
    except (OSError, AttributeError):
        return False


def check_type0_available() -> bool:
    if check_kvm_available():
        try:
            fd = os.open("/dev/kvm", os.O_RDWR)
            os.close(fd)
            return True
        except (OSError, PermissionError):
            pass
    if check_xen_available():
        return True
    return False


def download_file(
    url: str,
    dest: str,
    on_progress: Optional[Callable[[int, int], None]] = None,
    chunk_size: int = 8192,
) -> str:
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Boxes/1.0"})
    response = urllib.request.urlopen(req, timeout=120)
    total = int(response.headers.get("Content-Length", 0))
    downloaded = 0
    with open(dest, "wb") as f:
        while data := response.read(chunk_size):
            f.write(data)
            downloaded += len(data)
            if on_progress and total > 0:
                on_progress(downloaded, total)
    return dest


def download_iso(
    url: str,
    dest_dir: Optional[str] = None,
    filename: Optional[str] = None,
) -> str:
    if filename is None:
        filename = url.rsplit("/", 1)[-1]
    if dest_dir is None:
        from boxes.constants import BOXES_ISO

        dest_dir = str(BOXES_ISO)
    dest = str(Path(dest_dir) / filename)
    print(f"Downloading {url} -> {dest} ...")
    download_file(
        url,
        dest,
        on_progress=lambda d, t: print(
            f"\r  {d // 1024 // 1024}MB / {t // 1024 // 1024}MB", end=""
        ),
    )
    print(f"\nDownloaded to {dest}")
    return dest


def human_size(bytes_val: int) -> str:
    val = float(bytes_val)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if val < 1024:
            return f"{val:.1f} {unit}"
        val /= 1024
    return f"{val:.1f} PB"


def truncate_text(text: str, max_len: int = 60) -> str:
    return text[: max_len - 3] + "..." if len(text) > max_len else text
