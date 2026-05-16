from typing import Optional

from boxes.backends import BaseBackend
from boxes.constants import BOXES_CONFIG, BOXES_IMAGES, BACKEND_PRIORITY
from boxes.models.config import BoxConfig
from boxes.models.machine import MachineState
from boxes.diagnostics import get_root_cause
from boxes.util import (
	check_type0_available,
	check_xen_available,
	check_libvirt_available,
	check_hyperv_available,
	check_macos_hvf_available,
	find_qemu_binary,
)


rc = get_root_cause()


def detect_backend() -> BaseBackend:
	for backend_name in BACKEND_PRIORITY:
		if backend_name == "type0" and check_type0_available():
			try:
				from boxes.backends.type0.type0_backend import Type0Backend

				bk: BaseBackend = Type0Backend()
				if bk.connect():
					return bk
			except Exception as exc:
				rc.diagnose(exc, "type0", "connect")
		if backend_name == "xen" and check_xen_available():
			try:
				from boxes.backends.type0.xen_backend import XenBackend

				bk = XenBackend()
				if bk.connect():
					return bk
			except Exception as exc:
				rc.diagnose(exc, "xen", "connect")
		if backend_name == "libvirt" and check_libvirt_available():
			try:
				from boxes.backends.libvirt_backend import LibvirtBackend

				bk = LibvirtBackend()
				if bk.connect():
					return bk
			except Exception as exc:
				rc.diagnose(exc, "libvirt", "connect")
		if backend_name == "hyperv" and check_hyperv_available():
			try:
				from boxes.backends.window.hyperv_backend import HyperVBackend

				bk = HyperVBackend()
				if bk.connect():
					return bk
			except Exception as exc:
				rc.diagnose(exc, "hyperv", "connect")
		if backend_name == "macos" and check_macos_hvf_available():
			try:
				from boxes.backends.window.macos_backend import MacOSBackend

				bk = MacOSBackend()
				if bk.connect():
					return bk
			except Exception as exc:
				rc.diagnose(exc, "macos", "connect")
		if backend_name == "qemu" and find_qemu_binary():
			try:
				from boxes.backends.qemu.qemu_backend import QEMUBackend

				return QEMUBackend()
			except Exception as exc:
				rc.diagnose(exc, "qemu", "connect")
	try:
		from boxes.backends.qemu.qemu_backend import QEMUBackend

		return QEMUBackend()
	except Exception as exc:
		rc.diagnose(exc, "qemu", "create")
		raise


class BoxesCore:
	def __init__(self) -> None:
		BOXES_CONFIG.mkdir(parents=True, exist_ok=True)
		BOXES_IMAGES.mkdir(parents=True, exist_ok=True)
		rc.record("detect_backend", "core", True)
		self.backend = detect_backend()
		self.backend_name = self._backend_name()

	def _backend_name(self) -> str:
		name = type(self.backend).__name__
		return name.replace("Backend", "")

	def list_vms(self) -> list[dict]:
		results: list[dict] = []
		try:
			configs = BoxConfig.list_all()
		except Exception as exc:
			rc.diagnose(exc, "core", "list_vms:list_all")
			return results
		for config in configs:
			backend_id = config.uuid
			state = MachineState.STOPPED
			if self.backend.connected:
				try:
					state = self.backend.get_state(backend_id)
				except Exception as exc:
					rc.diagnose(exc, self.backend_name, f"list_vms:get_state:{config.name}")
			results.append(
				{
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
				}
			)
		return results

	def find_vm(self, name: str) -> Optional[BoxConfig]:
		try:
			for c in BoxConfig.list_all():
				if c.name == name or c.uuid == name:
					return c
		except Exception as exc:
			rc.diagnose(exc, "core", f"find_vm:{name}")
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
	) -> Optional[BoxConfig]:
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
		try:
			disk_dir = BOXES_IMAGES / config.uuid
			disk_dir.mkdir(parents=True, exist_ok=True)
			disk_path = str(disk_dir / f"{name}.qcow2")
			config.disk_path = disk_path
			config.save()
			self.backend.create_disk_image(disk_path, disk_gb)
			backend_id = self.backend.define_machine(config)
			if backend_id:
				config.uuid = backend_id
				config.save()
			rc.record("create_vm", "core", True, context={"name": name})
			return config
		except Exception as exc:
			rc.diagnose(exc, self.backend_name, f"create_vm:{name}")
			return None

	def start_vm(self, name: str) -> tuple[bool, str]:
		config = self.find_vm(name)
		if config is None:
			return False, f"VM '{name}' not found"
		backend_id = config.uuid
		try:
			if self.backend.start_machine(backend_id):
				rc.record("start_vm", "core", True, context={"name": name})
				return True, f"VM '{config.name}' started"
			rc.record(
				"start_vm",
				"core",
				False,
				context={"name": name},
				resolution="Check backend connectivity and VM configuration",
			)
			return False, f"Failed to start VM '{config.name}'"
		except Exception as exc:
			rc.diagnose(exc, self.backend_name, f"start_vm:{name}")
			return False, f"Failed to start VM '{config.name}': {exc}"

	def stop_vm(self, name: str) -> tuple[bool, str]:
		config = self.find_vm(name)
		if config is None:
			return False, f"VM '{name}' not found"
		try:
			if self.backend.shutdown_machine(config.uuid):
				rc.record("stop_vm", "core", True, context={"name": name})
				return True, f"VM '{config.name}' stopped"
			return False, f"Failed to stop VM '{config.name}'"
		except Exception as exc:
			rc.diagnose(exc, self.backend_name, f"stop_vm:{name}")
			return False, f"Failed to stop VM '{config.name}': {exc}"

	def pause_vm(self, name: str) -> tuple[bool, str]:
		config = self.find_vm(name)
		if config is None:
			return False, f"VM '{name}' not found"
		try:
			if self.backend.pause_machine(config.uuid):
				rc.record("pause_vm", "core", True, context={"name": name})
				return True, f"VM '{config.name}' paused"
			return False, f"Failed to pause VM '{config.name}'"
		except Exception as exc:
			rc.diagnose(exc, self.backend_name, f"pause_vm:{name}")
			return False, f"Failed to pause VM '{config.name}': {exc}"

	def resume_vm(self, name: str) -> tuple[bool, str]:
		config = self.find_vm(name)
		if config is None:
			return False, f"VM '{name}' not found"
		try:
			if self.backend.resume_machine(config.uuid):
				rc.record("resume_vm", "core", True, context={"name": name})
				return True, f"VM '{config.name}' resumed"
			return False, f"Failed to resume VM '{config.name}'"
		except Exception as exc:
			rc.diagnose(exc, self.backend_name, f"resume_vm:{name}")
			return False, f"Failed to resume VM '{config.name}': {exc}"

	def delete_vm(self, name: str, keep_disks: bool = False) -> tuple[bool, str]:
		config = self.find_vm(name)
		if config is None:
			return False, f"VM '{name}' not found"
		try:
			self.backend.delete_machine(config.uuid, keep_disks=keep_disks)
			if not keep_disks:
				config.delete()
			rc.record("delete_vm", "core", True, context={"name": name, "keep_disks": keep_disks})
			msg = f"VM '{config.name}' deleted"
			if keep_disks:
				msg += " (disks preserved)"
			return True, msg
		except Exception as exc:
			rc.diagnose(exc, self.backend_name, f"delete_vm:{name}")
			return False, f"Failed to delete VM '{config.name}': {exc}"

	def vm_info(self, name: str) -> Optional[dict]:
		config = self.find_vm(name)
		if config is None:
			return None
		try:
			state = self.backend.get_state(config.uuid)
		except Exception as exc:
			rc.diagnose(exc, self.backend_name, f"vm_info:get_state:{name}")
			state = MachineState.UNKNOWN
		try:
			display_addr = self.backend.get_display_address(config.uuid)
		except Exception as exc:
			rc.diagnose(exc, self.backend_name, f"vm_info:display_addr:{name}")
			display_addr = ""
		try:
			display_port = self.backend.get_display_port(config.uuid)
		except Exception as exc:
			rc.diagnose(exc, self.backend_name, f"vm_info:display_port:{name}")
			display_port = 0
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
			"display_address": display_addr,
			"display_port": display_port,
		}

	def backend_info(self) -> dict:
		try:
			caps = self.backend.capabilities
			connected = self.backend.connected
		except Exception as exc:
			rc.diagnose(exc, self.backend_name, "backend_info")
			caps = None
			connected = False
		return {
			"backend": self.backend_name,
			"connected": connected,
			"snapshots": caps.snapshots if caps else False,
			"usb_redirection": caps.usb_redirection if caps else False,
			"shared_folders": caps.shared_folders if caps else False,
			"live_migration": caps.live_migration if caps else False,
			"storage_pools": caps.storage_pools if caps else False,
			"networks": caps.networks if caps else False,
		}
