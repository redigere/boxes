from typing import Optional

from boxes.backends import BaseBackend
from boxes.constants import BOXES_CONFIG, BOXES_IMAGES, BACKEND_PRIORITY
from boxes.models.config import BoxConfig
from boxes.models.machine import MachineState
from boxes.util import (
    check_type0_available,
    check_xen_available,
    check_libvirt_available,
    check_hyperv_available,
    check_macos_hvf_available,
    find_qemu_binary,
)


def detect_backend() -> BaseBackend:
    for backend_name in BACKEND_PRIORITY:
        if backend_name == "type0" and check_type0_available():
            from boxes.backends.type0_backend import Type0Backend
            bk: BaseBackend = Type0Backend()
            if bk.connect():
                return bk
        if backend_name == "xen" and check_xen_available():
            from boxes.backends.xen_backend import XenBackend
            bk = XenBackend()
            if bk.connect():
                return bk
        if backend_name == "libvirt" and check_libvirt_available():
            try:
                from boxes.backends.libvirt_backend import LibvirtBackend
                bk = LibvirtBackend()
                if bk.connect():
                    return bk
            except Exception:
                pass
        if backend_name == "hyperv" and check_hyperv_available():
            from boxes.backends.hyperv_backend import HyperVBackend
            bk = HyperVBackend()
            if bk.connect():
                return bk
        if backend_name == "macos" and check_macos_hvf_available():
            from boxes.backends.macos_backend import MacOSBackend
            bk = MacOSBackend()
            if bk.connect():
                return bk
        if backend_name == "qemu" and find_qemu_binary():
            from boxes.backends.qemu_backend import QEMUBackend
            return QEMUBackend()
    from boxes.backends.qemu_backend import QEMUBackend
    return QEMUBackend()


class BoxesCore:
    def __init__(self) -> None:
        BOXES_CONFIG.mkdir(parents=True, exist_ok=True)
        BOXES_IMAGES.mkdir(parents=True, exist_ok=True)
        self.backend = detect_backend()
        self.backend_name = self._backend_name()

    def _backend_name(self) -> str:
        name = type(self.backend).__name__
        return name.replace("Backend", "")

    def list_vms(self) -> list[dict]:
        results: list[dict] = []
        for config in BoxConfig.list_all():
            backend_id = config.uuid
            state = MachineState.STOPPED
            if self.backend.connected:
                state = self.backend.get_state(backend_id)
            results.append({
                "uuid": config.uuid,
                "name": config.name,
                "state": MachineState.NAMES.get(state, "Unknown"),
                "state_code": state,
                "memory_mb": config.memory_mb,
                "vcpus": config.vcpus,
                "disk_gb": config.disk_size_gb,
                "os_type": config.os_type,
                "iso": config.iso_path or "",
                "disk": config.disk_path or "",
                "graphics": config.graphics,
                "arch": config.arch,
            })
        return results

    def find_vm(self, name: str) -> Optional[BoxConfig]:
        for c in BoxConfig.list_all():
            if c.name == name or c.uuid == name:
                return c
        return None

    def create_vm(
        self,
        name: str,
        memory_mb: int = 2048,
        vcpus: int = 2,
        disk_gb: int = 20,
        iso_path: Optional[str] = None,
        os_type: str = "generic",
        graphics: str = "spice",
        arch: str = "x86_64",
    ) -> BoxConfig:
        config = BoxConfig(
            name=name,
            memory_mb=memory_mb,
            vcpus=vcpus,
            disk_size_gb=disk_gb,
            iso_path=iso_path,
            os_type=os_type,
            graphics=graphics,
            arch=arch,
        )

        disk_path = str(BOXES_IMAGES / config.uuid / f"{name}.qcow2")
        config.disk_path = disk_path

        config.save()

        self.backend.create_disk_image(disk_path, disk_gb)
        backend_id = self.backend.define_machine(config)
        if backend_id:
            config.uuid = backend_id
            config.save()

        return config

    def start_vm(self, name: str) -> tuple[bool, str]:
        config = self.find_vm(name)
        if config is None:
            return False, f"VM '{name}' not found"
        backend_id = config.uuid
        if self.backend.start_machine(backend_id):
            return True, f"VM '{config.name}' started"
        return False, f"Failed to start VM '{config.name}'"

    def stop_vm(self, name: str) -> tuple[bool, str]:
        config = self.find_vm(name)
        if config is None:
            return False, f"VM '{name}' not found"
        if self.backend.shutdown_machine(config.uuid):
            return True, f"VM '{config.name}' stopped"
        return False, f"Failed to stop VM '{config.name}'"

    def pause_vm(self, name: str) -> tuple[bool, str]:
        config = self.find_vm(name)
        if config is None:
            return False, f"VM '{name}' not found"
        if self.backend.pause_machine(config.uuid):
            return True, f"VM '{config.name}' paused"
        return False, f"Failed to pause VM '{config.name}'"

    def resume_vm(self, name: str) -> tuple[bool, str]:
        config = self.find_vm(name)
        if config is None:
            return False, f"VM '{name}' not found"
        if self.backend.resume_machine(config.uuid):
            return True, f"VM '{config.name}' resumed"
        return False, f"Failed to resume VM '{config.name}'"

    def delete_vm(self, name: str) -> tuple[bool, str]:
        config = self.find_vm(name)
        if config is None:
            return False, f"VM '{name}' not found"
        self.backend.delete_machine(config.uuid)
        config.delete()
        return True, f"VM '{config.name}' deleted"

    def vm_info(self, name: str) -> Optional[dict]:
        config = self.find_vm(name)
        if config is None:
            return None
        state = self.backend.get_state(config.uuid)
        return {
            "uuid": config.uuid,
            "name": config.name,
            "state": MachineState.NAMES.get(state, "Unknown"),
            "memory_mb": config.memory_mb,
            "vcpus": config.vcpus,
            "disk_gb": config.disk_size_gb,
            "os_type": config.os_type,
            "iso": config.iso_path or "",
            "disk": config.disk_path or "",
            "graphics": config.graphics,
            "arch": config.arch,
            "cpu_model": config.cpu_model,
            "firmware": config.firmware,
            "network": config.network,
            "autostart": config.autostart,
            "backend": self.backend_name,
        }

    def backend_info(self) -> dict:
        caps = self.backend.capabilities
        return {
            "backend": self.backend_name,
            "connected": self.backend.connected,
            "snapshots": caps.snapshots,
            "usb_redirection": caps.usb_redirection,
            "shared_folders": caps.shared_folders,
            "live_migration": caps.live_migration,
            "storage_pools": caps.storage_pools,
            "networks": caps.networks,
        }
