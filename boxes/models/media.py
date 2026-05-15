from pathlib import Path


class InstallerMedia:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.label = self.path.name
        self.os_type = self._detect_os()

    def _detect_os(self) -> str:
        name = self.path.stem.lower()
        for keyword, os_id in [
            ("fedora", "fedora"),
            ("ubuntu", "ubuntu"),
            ("debian", "debian"),
            ("centos", "centos"),
            ("rhel", "rhel"),
            ("arch", "arch"),
            ("opensuse", "opensuse"),
            ("windows", "windows"),
            ("win", "windows"),
            ("alma", "almalinux"),
            ("rocky", "rockylinux"),
            ("freebsd", "freebsd"),
        ]:
            if keyword in name:
                return os_id
        return "generic"

    @property
    def exists(self) -> bool:
        return self.path.exists()

    @property
    def size_mb(self) -> int:
        return self.path.stat().st_size // (1024 * 1024) if self.exists else 0
