from pathlib import Path
import os
import sys

APP_NAME = "Boxes"
APP_ID = "io.boxes.Boxes"
APP_VERSION = "1.0.0"

XDG_DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
XDG_CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
XDG_CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))

BOXES_DATA = XDG_DATA / "boxes"
BOXES_CONFIG = XDG_CONFIG / "boxes"
BOXES_CACHE = XDG_CACHE / "boxes"
BOXES_SOURCES = BOXES_CONFIG / "sources"
BOXES_IMAGES = BOXES_DATA / "images"
BOXES_ISO = BOXES_DATA / "isos"

DEFAULT_RAM_MB = 2048
DEFAULT_VCPUS = 2
DEFAULT_DISK_GB = 20
MIN_RAM_MB = 256
MAX_RAM_MB = 524288
MIN_VCPUS = 1
MAX_VCPUS = 256
MIN_DISK_GB = 1
MAX_DISK_GB = 16384

QEMU_BINARIES = {
	"x86_64": "qemu-system-x86_64",
	"aarch64": "qemu-system-aarch64",
	"i386": "qemu-system-i386",
	"arm": "qemu-system-arm",
	"riscv64": "qemu-system-riscv64",
}

BACKEND_PRIORITY = [
	"type0",
	"xen",
	"libvirt",
	"qemu",
	"hyperv",
	"macos",
	"ssh",
]

PLATFORM = sys.platform
IS_LINUX = PLATFORM == "linux"
IS_WINDOWS = PLATFORM in ("win32", "cygwin")
IS_MACOS = PLATFORM == "darwin"
