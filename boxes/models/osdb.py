from typing import Optional


class OSDatabase:
	def __init__(self) -> None:
		self._entries = self._build()

	def _build(self) -> dict[str, dict[str, str | int]]:
		return {
			"fedora": {"name": "Fedora Workstation", "ram": 2048, "disk": 15, "arch": "x86_64"},
			"ubuntu": {"name": "Ubuntu Desktop", "ram": 2048, "disk": 25, "arch": "x86_64"},
			"debian": {"name": "Debian", "ram": 1024, "disk": 10, "arch": "x86_64"},
			"centos": {"name": "CentOS Stream", "ram": 2048, "disk": 20, "arch": "x86_64"},
			"rhel": {"name": "Red Hat Enterprise Linux", "ram": 2048, "disk": 20, "arch": "x86_64"},
			"windows": {"name": "Microsoft Windows", "ram": 4096, "disk": 64, "arch": "x86_64"},
			"arch": {"name": "Arch Linux", "ram": 1024, "disk": 8, "arch": "x86_64"},
			"opensuse": {"name": "OpenSUSE", "ram": 2048, "disk": 20, "arch": "x86_64"},
			"almalinux": {"name": "AlmaLinux", "ram": 2048, "disk": 20, "arch": "x86_64"},
			"rockylinux": {"name": "Rocky Linux", "ram": 2048, "disk": 20, "arch": "x86_64"},
			"freebsd": {"name": "FreeBSD", "ram": 1024, "disk": 8, "arch": "x86_64"},
			"generic": {"name": "Generic", "ram": 1024, "disk": 10, "arch": "x86_64"},
		}

	def get(self, os_id: str) -> Optional[dict[str, str | int]]:
		return self._entries.get(os_id)

	def suggest(self, os_id: str) -> dict[str, str | int]:
		return self._entries.get(os_id, self._entries["generic"])

	def list_all(self) -> list[dict[str, str | int]]:
		return [v for v in self._entries.values()]

	def ids(self) -> list[str]:
		return list(self._entries.keys())
