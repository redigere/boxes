from dataclasses import asdict
import json

from boxes.models.config import BoxConfig
from boxes.models.machine import Machine, MachineState
from boxes.models.osdb import OSDatabase
from boxes.models.media import InstallerMedia


class TestBoxConfig:
    def test_default_values(self) -> None:
        config = BoxConfig(name="test-vm")
        assert config.name == "test-vm"
        assert config.uuid is not None
        assert config.memory_mb == 2048
        assert config.vcpus == 2
        assert config.disk_size_gb == 20

    def test_asdict_roundtrip(self) -> None:
        config = BoxConfig(
            name="win10",
            memory_mb=4096,
            vcpus=4,
            disk_size_gb=80,
            os_type="windows",
            disk_path="/tmp/test.qcow2",
        )
        d = asdict(config)
        restored = BoxConfig(**d)
        assert restored.name == config.name
        assert restored.uuid == config.uuid
        assert restored.memory_mb == config.memory_mb
        assert restored.vcpus == config.vcpus
        assert restored.disk_size_gb == config.disk_size_gb
        assert restored.os_type == config.os_type
        assert restored.disk_path == config.disk_path

    def test_json_serialization(self) -> None:
        config = BoxConfig(name="serialize-test")
        d = asdict(config)
        assert d["name"] == "serialize-test"
        data = json.dumps(d)
        parsed = json.loads(data)
        assert parsed["name"] == "serialize-test"

    def test_save_and_load(self) -> None:
        from boxes.constants import BOXES_CONFIG
        BOXES_CONFIG.mkdir(parents=True, exist_ok=True)
        config = BoxConfig(name="save-test", memory_mb=1024)
        config.save()
        assert config.config_path.exists()
        loaded = BoxConfig.load(config.config_path)
        assert loaded.name == "save-test"
        assert loaded.memory_mb == 1024
        assert loaded.uuid == config.uuid
        config.delete()
        assert not config.config_path.exists()

    def test_list_all(self) -> None:
        configs = BoxConfig.list_all()
        assert isinstance(configs, list)


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

    def test_status_text(self) -> None:
        config = BoxConfig(name="status-test")
        machine = Machine(config)
        assert machine.status_text == "Off"
        machine.state = MachineState.RUNNING
        assert machine.status_text == "Running"

    def test_properties(self) -> None:
        config = BoxConfig(name="prop-test")
        machine = Machine(config)
        assert machine.name == "prop-test"
        assert machine.is_off
        assert not machine.is_running
        assert not machine.is_paused
        assert machine.backend_id is None


class TestOSDatabase:
    def test_presets_exist(self) -> None:
        db = OSDatabase()
        entries = db.list_all()
        assert len(entries) > 0

    def test_get(self) -> None:
        db = OSDatabase()
        entry = db.get("ubuntu")
        assert entry is not None
        assert entry["name"] == "Ubuntu Desktop"
        assert entry["ram"] == 2048
        assert entry["disk"] == 25

    def test_get_nonexistent(self) -> None:
        db = OSDatabase()
        entry = db.get("nonexistent-os")
        assert entry is None

    def test_suggest_known(self) -> None:
        db = OSDatabase()
        entry = db.suggest("fedora")
        assert entry["name"] == "Fedora Workstation"

    def test_suggest_unknown_falls_back_to_generic(self) -> None:
        db = OSDatabase()
        entry = db.suggest("made-up-os")
        assert entry["name"] == "Generic"

    def test_ids(self) -> None:
        db = OSDatabase()
        all_ids = db.ids()
        assert "fedora" in all_ids
        assert "ubuntu" in all_ids
        assert "windows" in all_ids


class TestInstallerMedia:
    def test_detect_ubuntu(self) -> None:
        media = InstallerMedia("ubuntu-24.04-desktop-amd64.iso")
        assert media.os_type == "ubuntu"

    def test_detect_windows(self) -> None:
        media = InstallerMedia("Win11_23H2_English_x64.iso")
        assert media.os_type == "windows"

    def test_detect_fedora(self) -> None:
        media = InstallerMedia("Fedora-40-1.14-x86_64.iso")
        assert media.os_type == "fedora"

    def test_detect_debian(self) -> None:
        media = InstallerMedia("debian-12.0.0-amd64-DVD-1.iso")
        assert media.os_type == "debian"

    def test_detect_unknown(self) -> None:
        media = InstallerMedia("random-file.iso")
        assert media.os_type == "generic"

    def test_label(self) -> None:
        media = InstallerMedia("/path/to/Fedora-40.iso")
        assert media.label == "Fedora-40.iso"

    def test_exists(self) -> None:
        media = InstallerMedia("/nonexistent/foo.iso")
        assert not media.exists
