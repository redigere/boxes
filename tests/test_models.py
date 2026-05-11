import json
import tempfile
from pathlib import Path

from boxes.models.config import BoxConfig
from boxes.models.machine import Machine, MachineState
from boxes.models.osdb import OSDatabase
from boxes.models.media import InstallerMedia


class TestBoxConfig:
    def test_default_values(self) -> None:
        config = BoxConfig(name="test-vm")
        assert config.name == "test-vm"
        assert config.uuid is not None
        assert config.ram_mb == 2048
        assert config.vcpus == 2
        assert config.disk_gb == 20

    def test_to_dict_roundtrip(self) -> None:
        config = BoxConfig(
            name="win10",
            ram_mb=4096,
            vcpus=4,
            disk_gb=80,
            os_id="windows-10",
            disk_path="/tmp/test.qcow2",
        )
        d = config.to_dict()
        restored = BoxConfig.from_dict(d)
        assert restored.name == config.name
        assert restored.uuid == config.uuid
        assert restored.ram_mb == config.ram_mb
        assert restored.vcpus == config.vcpus
        assert restored.disk_gb == config.disk_gb
        assert restored.os_id == config.os_id
        assert restored.disk_path == config.disk_path

    def test_json_serialization(self) -> None:
        config = BoxConfig(name="serialize-test")
        data = config.to_json()
        assert isinstance(data, str)
        parsed = json.loads(data)
        assert parsed["name"] == "serialize-test"

    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            config = BoxConfig(name="save-test", ram_mb=1024)
            config.save(path)
            assert path.exists()
            loaded = BoxConfig.load(path)
            assert loaded.name == "save-test"
            assert loaded.ram_mb == 1024
            assert loaded.uuid == config.uuid

    def test_load_nonexistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nonexistent.json"
            loaded = BoxConfig.load(path)
            assert loaded is None


class TestMachine:
    def test_initial_state(self) -> None:
        config = BoxConfig(name="machine-test")
        machine = Machine(config)
        assert machine.config.name == "machine-test"
        assert machine.state == MachineState.STOPPED

    def test_state_transitions(self) -> None:
        config = BoxConfig(name="state-test")
        machine = Machine(config)
        assert machine.state == MachineState.STOPPED
        machine.state = MachineState.RUNNING
        assert machine.state == MachineState.RUNNING
        machine.state = MachineState.PAUSED
        assert machine.state == MachineState.PAUSED
        machine.state = MachineState.STOPPED
        assert machine.state == MachineState.STOPPED

    def test_string_representation(self) -> None:
        config = BoxConfig(name="rep-test")
        machine = Machine(config)
        s = str(machine)
        assert "rep-test" in s
        assert "STOPPED" in s or "stopped" in s


class TestOSDatabase:
    def test_presets_exist(self) -> None:
        db = OSDatabase()
        entries = db.get_all()
        assert len(entries) > 0

    def test_find_by_id(self) -> None:
        db = OSDatabase()
        entry = db.find_by_id("ubuntu-24-04")
        assert entry is not None
        assert entry.name == "Ubuntu 24.04 LTS"
        assert entry.min_ram_mb == 1024
        assert entry.min_disk_gb == 10

    def test_find_by_id_nonexistent(self) -> None:
        db = OSDatabase()
        entry = db.find_by_id("nonexistent-os")
        assert entry is None

    def test_search(self) -> None:
        db = OSDatabase()
        results = db.search("windows")
        assert len(results) > 0
        assert any("Windows" in r.name for r in results)

    def test_fedora_preset(self) -> None:
        db = OSDatabase()
        entry = db.find_by_id("fedora-40")
        assert entry is not None
        assert entry.name == "Fedora 40"
        assert entry.min_ram_mb == 1024

    def test_debian_preset(self) -> None:
        db = OSDatabase()
        entry = db.find_by_id("debian-12")
        assert entry is not None
        assert entry.name == "Debian 12"
        assert entry.min_ram_mb == 512


class TestInstallerMedia:
    def test_detect_ubuntu(self) -> None:
        result = InstallerMedia.detect("ubuntu-24.04-desktop-amd64.iso")
        assert result is not None
        assert "ubuntu" in result.os_id

    def test_detect_windows(self) -> None:
        result = InstallerMedia.detect("Win11_23H2_English_x64.iso")
        assert result is not None
        assert "windows" in result.os_id

    def test_detect_fedora(self) -> None:
        result = InstallerMedia.detect("Fedora-40-1.14-x86_64.iso")
        assert result is not None
        assert "fedora" in result.os_id

    def test_detect_debian(self) -> None:
        result = InstallerMedia.detect("debian-12.0.0-amd64-DVD-1.iso")
        assert result is not None
        assert "debian" in result.os_id

    def test_detect_unknown(self) -> None:
        result = InstallerMedia.detect("random-file.iso")
        assert result is None
