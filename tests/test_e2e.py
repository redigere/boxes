import os
import subprocess
import sys
from pathlib import Path

import pytest

from boxes.constants import BOXES_CONFIG, BOXES_IMAGES, BOXES_ISO
from boxes.core import BoxesCore, detect_backend
from boxes.models.config import BoxConfig
from boxes.models.media import InstallerMedia
from boxes.util import download_iso


ALPINE_URL = (
    "https://dl-cdn.alpinelinux.org/alpine/v3.21/releases/x86_64/alpine-standard-3.21.3-x86_64.iso"
)
ALPINE_FILENAME = "alpine-standard-3.21.3-x86_64.iso"
E2E_PREFIX = "boxes-e2e-"


def _cleanup_vms(pattern: str = E2E_PREFIX) -> None:
    for c in BoxConfig.list_all():
        if c.name.startswith(pattern):
            c.delete()
    for d in BOXES_IMAGES.iterdir():
        if d.is_dir() and d.name.startswith(pattern):
            import shutil

            shutil.rmtree(str(d), ignore_errors=True)


class TestE2EVMFromNetwork:
    @classmethod
    def setup_class(cls) -> None:
        BOXES_CONFIG.mkdir(parents=True, exist_ok=True)
        BOXES_IMAGES.mkdir(parents=True, exist_ok=True)
        _cleanup_vms()

    @classmethod
    def teardown_class(cls) -> None:
        _cleanup_vms()

    def test_detect_backend_available(self) -> None:
        backend = detect_backend()
        assert backend is not None, "No backend detected — cannot run E2E tests"
        assert hasattr(backend, "connected")

    def test_create_vm_network_boot(self) -> None:
        core = BoxesCore()
        name = f"{E2E_PREFIX}netboot"
        vm = core.find_vm(name)
        if vm:
            core.delete_vm(name)

        config = core.create_vm(
            name=name,
            memory_mb=512,
            vcpus=1,
            disk_gb=5,
            os_type="generic",
        )
        assert config is not None
        assert config.name == name
        assert config.iso_path is None
        assert config.disk_path is not None
        assert Path(config.disk_path).parent.exists()

        found = core.find_vm(name)
        assert found is not None

        config_path = config.config_path
        assert config_path.exists()
        loaded = BoxConfig.load(config_path)
        assert loaded.name == name
        assert loaded.iso_path is None

        info = core.vm_info(name)
        assert info is not None
        assert info["name"] == name
        assert info["iso"] == ""

    def test_create_vm_network_boot_twice_fails(self) -> None:
        core = BoxesCore()
        name = f"{E2E_PREFIX}netboot-dup"
        existing = core.find_vm(name)
        if existing:
            core.delete_vm(name)

        core.create_vm(name=name, memory_mb=512, vcpus=1, disk_gb=5)
        config = BoxConfig.list_all()
        matching = [c for c in config if c.name == name]
        assert len(matching) == 1

        core2 = BoxesCore()
        assert core2.find_vm(name) is not None

    def test_list_includes_network_vm(self) -> None:
        _cleanup_vms()
        core = BoxesCore()
        name = f"{E2E_PREFIX}netboot-list"
        core.create_vm(name=name, memory_mb=512, vcpus=1, disk_gb=5)
        vms = core.list_vms()
        names = [v["name"] for v in vms]
        assert name in names

    def test_start_network_vm(self) -> None:
        core = BoxesCore()
        name = f"{E2E_PREFIX}netboot-start"
        existing = core.find_vm(name)
        if existing:
            core.delete_vm(name)
        core.create_vm(name=name, memory_mb=512, vcpus=1, disk_gb=5)
        ok, msg = core.start_vm(name)
        if core.backend.connected:
            assert ok, msg
        else:
            assert not ok

    def test_start_stop_cycle(self) -> None:
        core = BoxesCore()
        name = f"{E2E_PREFIX}netboot-cycle"
        existing = core.find_vm(name)
        if existing:
            core.delete_vm(name)
        core.create_vm(name=name, memory_mb=512, vcpus=1, disk_gb=5)

        if core.backend.connected:
            ok_start, _ = core.start_vm(name)
            assert ok_start
            ok_stop, _ = core.stop_vm(name)
            assert ok_stop


class TestE2EVMFromISO:
    iso_path: str = ""

    @classmethod
    def setup_class(cls) -> None:
        BOXES_CONFIG.mkdir(parents=True, exist_ok=True)
        BOXES_IMAGES.mkdir(parents=True, exist_ok=True)
        BOXES_ISO.mkdir(parents=True, exist_ok=True)
        _cleanup_vms()

        dest = str(BOXES_ISO / ALPINE_FILENAME)
        if not Path(dest).exists():
            if os.environ.get("BOXES_SKIP_DOWNLOAD", "").lower() in ("1", "true", "yes"):
                pytest.skip("BOXES_SKIP_DOWNLOAD is set")
            cls.iso_path = download_iso(ALPINE_URL, filename=ALPINE_FILENAME)
        else:
            cls.iso_path = dest

    @classmethod
    def teardown_class(cls) -> None:
        _cleanup_vms()

    def test_iso_exists(self) -> None:
        assert Path(self.iso_path).exists()
        assert Path(self.iso_path).stat().st_size > 0

    def test_iso_detected(self) -> None:
        media = InstallerMedia(self.iso_path)
        assert media.exists
        assert media.size_mb > 0
        assert media.os_type == "generic"

    def test_detect_backend_available(self) -> None:
        backend = detect_backend()
        assert backend is not None

    def test_create_vm_from_iso(self) -> None:
        core = BoxesCore()
        name = f"{E2E_PREFIX}iso-vm"
        existing = core.find_vm(name)
        if existing:
            core.delete_vm(name)

        config = core.create_vm(
            name=name,
            memory_mb=512,
            vcpus=1,
            disk_gb=8,
            iso_path=self.iso_path,
            os_type="generic",
        )
        assert config is not None
        assert config.name == name
        assert config.iso_path == self.iso_path
        assert config.disk_path is not None
        assert Path(config.disk_path).parent.exists()

        loaded = BoxConfig.load(config.config_path)
        assert loaded.iso_path == self.iso_path
        assert loaded.disk_size_gb == 8

    def test_create_vm_from_iso_with_os_detection(self) -> None:
        core = BoxesCore()
        name = f"{E2E_PREFIX}iso-osdetect"
        existing = core.find_vm(name)
        if existing:
            core.delete_vm(name)

        media = InstallerMedia(self.iso_path)
        config = core.create_vm(
            name=name,
            memory_mb=1024,
            vcpus=2,
            disk_gb=10,
            iso_path=self.iso_path,
            os_type=media.os_type,
            graphics="vnc",
        )
        assert config.os_type == "generic"
        assert config.graphics == "vnc"
        assert config.memory_mb == 1024
        assert config.vcpus == 2

    def test_vm_info_from_iso(self) -> None:
        core = BoxesCore()
        name = f"{E2E_PREFIX}iso-info"
        existing = core.find_vm(name)
        if existing:
            core.delete_vm(name)
        core.create_vm(name=name, memory_mb=512, vcpus=1, disk_gb=5, iso_path=self.iso_path)

        info = core.vm_info(name)
        assert info is not None
        assert info["iso"] == self.iso_path
        assert info["name"] == name
        assert info["backend"] != ""

    def test_list_shows_iso_vm(self) -> None:
        _cleanup_vms()
        core = BoxesCore()
        name = f"{E2E_PREFIX}iso-list"
        core.create_vm(name=name, memory_mb=512, vcpus=1, disk_gb=5, iso_path=self.iso_path)
        vms = core.list_vms()
        names = [v["name"] for v in vms]
        assert name in names

    def test_delete_iso_vm(self) -> None:
        core = BoxesCore()
        name = f"{E2E_PREFIX}iso-delete"
        existing = core.find_vm(name)
        if existing:
            core.delete_vm(name)
        core.create_vm(name=name, memory_mb=512, vcpus=1, disk_gb=5, iso_path=self.iso_path)
        ok, msg = core.delete_vm(name)
        assert ok, msg
        assert core.find_vm(name) is None


class TestE2ECLICreate:
    def test_cli_create_network_vm(self) -> None:
        name = f"{E2E_PREFIX}cli-net"
        _cleanup_vms()
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "boxes",
                "create",
                "--name",
                name,
                "--memory",
                "512",
                "--vcpus",
                "1",
                "--disk",
                "5",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
        assert name in result.stdout
        core = BoxesCore()
        assert core.find_vm(name) is not None

    def test_cli_list(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "boxes", "list"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0

    def test_cli_info(self) -> None:
        name = f"{E2E_PREFIX}cli-info"
        _cleanup_vms()
        core = BoxesCore()
        core.create_vm(name=name, memory_mb=256, vcpus=1, disk_gb=3)
        result = subprocess.run(
            [sys.executable, "-m", "boxes", "info", name],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0
        assert name in result.stdout

    def test_cli_info_backend(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "boxes", "info"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0
        assert "Backend" in result.stdout

    def test_cli_diagnose(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "boxes", "diagnose"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0

    def test_cli_delete_force(self) -> None:
        name = f"{E2E_PREFIX}cli-del"
        _cleanup_vms()
        core = BoxesCore()
        core.create_vm(name=name, memory_mb=256, vcpus=1, disk_gb=3)
        result = subprocess.run(
            [sys.executable, "-m", "boxes", "delete", "--force", name],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0
        assert core.find_vm(name) is None
