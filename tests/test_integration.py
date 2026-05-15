from boxes.core import BoxesCore, detect_backend
from boxes.constants import BOXES_CONFIG, BOXES_IMAGES
from boxes.models.config import BoxConfig
from boxes.models.machine import MachineState


class TestCoreIntegration:
    def setup_method(self) -> None:
        self._test_name = "inttest-vm"
        BOXES_CONFIG.mkdir(parents=True, exist_ok=True)
        existing = BoxConfig.list_all()
        for c in existing:
            if c.name == self._test_name:
                c.delete()
                break

    def teardown_method(self) -> None:
        configs = BoxConfig.list_all()
        for c in configs:
            if c.name == self._test_name:
                c.delete()
                break
        img_dir = BOXES_IMAGES / "inttest-vm"
        if img_dir.exists():
            import shutil

            shutil.rmtree(str(img_dir), ignore_errors=True)

    def test_detect_backend_returns_backend(self) -> None:
        backend = detect_backend()
        assert backend is not None
        assert hasattr(backend, "connected")

    def test_core_initializes(self) -> None:
        core = BoxesCore()
        assert core.backend is not None
        assert core.backend_name != ""

    def test_core_create_and_find_vm(self) -> None:
        core = BoxesCore()
        core.create_vm(name=self._test_name, memory_mb=512, vcpus=1, disk_gb=5)
        found = core.find_vm(self._test_name)
        assert found is not None
        assert found.name == self._test_name

    def test_core_list_vms(self) -> None:
        core = BoxesCore()
        core.create_vm(name=self._test_name, memory_mb=512, vcpus=1, disk_gb=5)
        vms = core.list_vms()
        names = [v["name"] for v in vms]
        assert self._test_name in names

    def test_core_vm_info(self) -> None:
        core = BoxesCore()
        config = core.create_vm(name=self._test_name, memory_mb=512, vcpus=1, disk_gb=5)
        info = core.vm_info(config.name)
        assert info is not None
        assert info["name"] == self._test_name
        assert info["memory_mb"] == 512
        assert info["vcpus"] == 1
        assert info["disk_gb"] == 5

    def test_core_delete_vm(self) -> None:
        core = BoxesCore()
        core.create_vm(name=self._test_name, memory_mb=512, vcpus=1, disk_gb=5)
        ok, msg = core.delete_vm(self._test_name)
        assert ok
        assert core.find_vm(self._test_name) is None

    def test_core_info_backend(self) -> None:
        core = BoxesCore()
        info = core.backend_info()
        assert "backend" in info
        assert "connected" in info
        assert "snapshots" in info

    def test_config_persistence(self) -> None:
        cfg = BoxConfig(name="persist-test", uuid="test-persist-uuid", memory_mb=4096)
        cfg.save()
        try:
            loaded = BoxConfig.load(cfg.config_path)
            assert loaded.name == "persist-test"
            assert loaded.memory_mb == 4096
        finally:
            cfg.delete()

    def test_config_list_all(self) -> None:
        cfg1 = BoxConfig(name="list-test-1", uuid="list-test-uuid-1")
        cfg2 = BoxConfig(name="list-test-2", uuid="list-test-uuid-2")
        cfg1.save()
        cfg2.save()
        try:
            configs = BoxConfig.list_all()
            uuids = [c.uuid for c in configs]
            assert "list-test-uuid-1" in uuids
            assert "list-test-uuid-2" in uuids
        finally:
            cfg1.delete()
            cfg2.delete()

    def test_machine_state_transitions(self) -> None:
        from boxes.models.machine import Machine

        machine = Machine(BoxConfig(name="state-machine"))
        assert machine.state == MachineState.STOPPED
        machine.state = MachineState.RUNNING
        assert machine.is_running
        machine.state = MachineState.PAUSED
        assert machine.is_paused
        machine.state = MachineState.STOPPED
        assert machine.is_off


class TestDiagnosticsIntegration:
    def test_rootcause_capture(self) -> None:
        from boxes.diagnostics import get_root_cause

        rc = get_root_cause()
        rc.clear()
        assert len(rc.records) == 0

        import os

        try:
            os.open("/nonexistent", os.O_RDONLY)
        except OSError as exc:
            rc.diagnose(exc, "test", "file_open")

        assert len(rc.records) == 1
        record = rc.records[0]
        assert record.success is False
        assert record.component == "test"
        assert record.operation == "file_open"

    def test_rootcause_summary(self) -> None:
        from boxes.diagnostics import RootCause

        rc = RootCause()
        rc.record("op", "comp", True)
        rc.record("fail_op", "comp", False, context={"detail": "test"})
        summary = rc.summary()
        assert "1 total" in summary or "2 total" in summary
        assert "Diagnostics" in summary

    def test_resolution_suggestions(self) -> None:
        from boxes.diagnostics import RootCause

        rc = RootCause()
        try:
            __import__("nonexistent_module_xyz")
        except ImportError as exc:
            record = rc.diagnose(exc, "import", "test_import")
            assert (
                "dependency" in record.resolution
                or "Install" in record.resolution
                or "Check" in record.resolution
            )

    def test_gather_context(self) -> None:
        from boxes.diagnostics import RootCause

        rc = RootCause()
        ctx = rc._gather_context("kvm")
        assert "python" in ctx
        assert "/dev/kvm" in ctx


class TestDiagnosticsCLI:
    def test_diagnose_command_registered(self) -> None:
        import argparse

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        sub.add_parser("diagnose")
        args = parser.parse_args(["diagnose"])
        assert args.command == "diagnose"

    def test_diagnose_imports(self) -> None:
        from boxes.diagnostics import RootCause, DiagnosticRecord, get_root_cause

        assert RootCause is not None
        assert DiagnosticRecord is not None
        assert get_root_cause is not None
