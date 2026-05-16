from __future__ import annotations

from typing import Optional, TYPE_CHECKING, cast
from boxes.backends import BaseBackend

if TYPE_CHECKING:
    import libvirt
from boxes.models.config import BoxConfig
from boxes.models.machine import MachineState


class LibvirtBackend(BaseBackend):
	def __init__(self, uri: str = "qemu:///session") -> None:
		super().__init__()
		self.uri = uri
		self.capabilities.snapshots = True
		self.capabilities.usb_redirection = True
		self.capabilities.shared_folders = True
		self.capabilities.storage_pools = True
		self.capabilities.networks = True
		self._conn: libvirt.libvirt | None = None

	def _import_libvirt(self) -> libvirt.libvirt:
		import libvirt as _lv
		return _lv

	def connect(self) -> bool:
		try:
			lv = self._import_libvirt()
			self._conn = lv.open(self.uri)
			return self._conn is not None
		except Exception:
			return False

	def disconnect(self) -> None:
		if self._conn:
			try:
				self._conn.close()
			except Exception:
				self._conn = None
			self._conn = None

	@property
	def connected(self) -> bool:
		return self._conn is not None

	def list_machines(self) -> list[dict[str, str | int | bool | None]]:
		if not self.connected or self._conn is None:
			return []
		results = []
		try:
			for domain_id in self._conn.listDomainsID():
				dom = self._conn.lookupByID(domain_id)
				state, max_mem, mem, vcpus, cpu_time = dom.info()
				results.append(
					{
						"name": dom.name(),
						"uuid": dom.UUIDString(),
						"state": state,
						"max_mem": max_mem,
						"vcpus": vcpus,
						"id": domain_id,
						"active": True,
					}
				)
			for name in self._conn.listDefinedDomains():
				dom = self._conn.lookupByName(name)
				results.append(
					{
						"name": dom.name(),
						"uuid": dom.UUIDString(),
						"state": 0,
						"max_mem": 0,
						"vcpus": 0,
						"id": -1,
						"active": False,
					}
				)
		except Exception:
			return results
		return results

	def define_machine(self, config: BoxConfig) -> Optional[str]:
		if not self.connected or self._conn is None:
			return None
		xml = self._build_domain_xml(config)
		try:
			dom = self._conn.defineXML(xml)
			return cast(str, dom.UUIDString())
		except Exception:
			return None

	def undefine_machine(self, backend_id: str) -> bool:
		if not self.connected or self._conn is None:
			return False
		try:
			dom = self._conn.lookupByUUIDString(backend_id)
			dom.undefine()
			return True
		except Exception:
			return False

	def start_machine(self, backend_id: str) -> bool:
		if not self.connected or self._conn is None:
			return False
		try:
			dom = self._conn.lookupByUUIDString(backend_id)
			dom.create()
			return True
		except Exception:
			return False

	def shutdown_machine(self, backend_id: str) -> bool:
		if not self.connected or self._conn is None:
			return False
		try:
			dom = self._conn.lookupByUUIDString(backend_id)
			dom.shutdown()
			return True
		except Exception:
			return False

	def pause_machine(self, backend_id: str) -> bool:
		if not self.connected or self._conn is None:
			return False
		try:
			dom = self._conn.lookupByUUIDString(backend_id)
			dom.suspend()
			return True
		except Exception:
			return False

	def resume_machine(self, backend_id: str) -> bool:
		if not self.connected or self._conn is None:
			return False
		try:
			dom = self._conn.lookupByUUIDString(backend_id)
			dom.resume()
			return True
		except Exception:
			return False

	def delete_machine(self, backend_id: str, keep_disks: bool = False) -> bool:
		if not self.connected or self._conn is None:
			return False
		try:
			dom = self._conn.lookupByUUIDString(backend_id)
			dom.undefine()
			try:
				pool = self._conn.storagePoolLookupByName("default")
				vol = pool.storageVolLookupByName(f"{dom.name()}.qcow2")
				vol.delete(0)
			except Exception:
				return True
			return True
		except Exception:
			return False

	def get_state(self, backend_id: str) -> int:
		if not self.connected or self._conn is None:
			return MachineState.STOPPED
		try:
			dom = self._conn.lookupByUUIDString(backend_id)
			state, _, _, _, _ = dom.info()
			mapping = {
				1: MachineState.RUNNING,
				2: MachineState.PAUSED,
				3: MachineState.SLEEPING,
				5: MachineState.SLEEPING,
				4: MachineState.CRASHED,
			}
			return mapping.get(state, MachineState.STOPPED)
		except Exception:
			return MachineState.STOPPED

	def create_disk_image(self, path: str, size_gb: int) -> bool:
		if not self.connected or self._conn is None:
			return False
		try:
			pool = self._conn.storagePoolLookupByName("default")
			if pool is None:
				return False
			xml = f"""
			<volume>
				<name>{path.split("/")[-1]}</name>
				<capacity unit='G'>{size_gb}</capacity>
				<allocation unit='G'>0</allocation>
				<target>
					<format type='qcow2'/>
					<path>{path}</path>
				</target>
			</volume>"""
			pool.createXML(xml)
			return True
		except Exception:
			return False

	def get_display_address(self, backend_id: str) -> Optional[str]:
		if not self.connected or self._conn is None:
			return None
		try:
			dom = self._conn.lookupByUUIDString(backend_id)
			xml = dom.XMLDesc()
			import re

			match = re.search(r"<graphics type='(\w+)'.*?port='(\d+)'.*?listen='([^']*)'", xml)
			if match:
				return match.group(3)
			match = re.search(r"<graphics type='(\w+)'.*?autoport='yes'", xml)
			if match:
				return "127.0.0.1"
			return None
		except Exception:
			return None

	def get_display_port(self, backend_id: str) -> Optional[int]:
		if not self.connected or self._conn is None:
			return None
		try:
			dom = self._conn.lookupByUUIDString(backend_id)
			xml = dom.XMLDesc()
			import re

			match = re.search(r"<graphics type='(\w+)'.*?port='(\d+)'", xml)
			if match:
				return int(match.group(2))
			return None
		except Exception:
			return None

	def _build_domain_xml(self, config: BoxConfig) -> str:
		return f"""<domain type='kvm'>
\t<name>{config.name}</name>
\t<uuid>{config.uuid}</uuid>
\t<memory unit='MiB'>{config.memory_mb}</memory>
\t<vcpu>{config.vcpus}</vcpu>
\t<os>
\t\t<type arch='{config.arch}' machine='{config.machine_type}'>hvm</type>
\t\t<boot dev='hd'/>
\t\t<boot dev='cdrom'/>
\t</os>
\t<features>
\t\t<acpi/><apic/><pae/>
\t</features>
\t<cpu mode='host-passthrough'/>
\t<clock offset='utc'/>
\t<on_poweroff>destroy</on_poweroff>
\t<on_reboot>restart</on_reboot>
\t<on_crash>restart</on_crash>
\t<devices>
\t\t<disk type='file' device='disk'>
\t\t\t<driver name='qemu' type='qcow2'/>
\t\t\t<source file='{config.disk_path or ""}'/>
\t\t\t<target dev='vda' bus='virtio'/>
\t\t</disk>
\t\t<disk type='file' device='cdrom'>
\t\t\t<driver name='qemu' type='raw'/>
\t\t\t<source file='{config.iso_path or ""}'/>
\t\t\t<target dev='sda' bus='sata'/>
\t\t\t<readonly/>
\t\t</disk>
\t\t<interface type='network'>
\t\t\t<source network='{config.network}'/>
\t\t\t<model type='virtio'/>
\t\t</interface>
\t\t<graphics type='{config.graphics}' port='-1' autoport='yes' listen='127.0.0.1'>
\t\t\t<gl enable='no'/>
\t\t</graphics>
\t\t<video>
\t\t\t<model type='qxl' ram='65536' vram='65536' heads='1'/>
\t\t</video>
\t\t<memballoon model='virtio'/>
\t</devices>
</domain>"""
