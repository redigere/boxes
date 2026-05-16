from __future__ import annotations

import shutil
import subprocess
from typing import Optional


class LibosinfoWrapper:
    """Wrapper around libosinfo for OS detection and express install.

    Provides OS metadata (minimum resources, install script templates,
    ISO detection) using libosinfo database via `osinfo-query` CLI.
    Falls back to built-in OSDatabase when libosinfo is unavailable.
    """

    def __init__(self) -> None:
        self._osinfo_query: Optional[str] = None
        self._available: Optional[bool] = None

    @property
    def available(self) -> bool:
        """Check if libosinfo CLI tools are available."""
        if self._available is None:
            self._osinfo_query = shutil.which("osinfo-query")
            self._available = self._osinfo_query is not None
        return self._available

    def list_oses(self) -> list[dict]:
        """List all operating systems known to libosinfo."""
        if not self.available or not self._osinfo_query:
            return self._fallback_list()
        try:
            result = subprocess.run(
                [self._osinfo_query, "os"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode != 0:
                return self._fallback_list()
            oses: list[dict] = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip() or line.startswith("Short ID"):
                    continue
                parts = line.split("|")
                if len(parts) >= 2:
                    oses.append({
                        "id": parts[0].strip(),
                        "name": parts[1].strip(),
                        "short_id": parts[0].strip(),
                    })
            return oses
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return self._fallback_list()

    def get_os(self, os_id: str) -> Optional[dict]:
        """Get metadata for a specific OS."""
        if not self.available or not self._osinfo_query:
            return self._fallback_get(os_id)
        try:
            result = subprocess.run(
                [self._osinfo_query, "os", os_id],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) >= 2:
                    parts = lines[1].split("|")
                    if len(parts) >= 2:
                        return {
                            "id": os_id,
                            "name": parts[1].strip(),
                            "short_id": os_id,
                        }
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return self._fallback_get(os_id)

    def get_minimum_resources(self, os_id: str) -> dict:
        """Get minimum RAM and disk for a given OS."""
        from boxes.models.osdb import OSDatabase

        db = OSDatabase()
        entry = db.get(os_id)
        if entry:
            return {"ram_mb": entry.get("ram", 1024), "disk_gb": entry.get("disk", 10)}
        return {"ram_mb": 1024, "disk_gb": 10}

    def detect_os_from_iso(self, iso_path: str) -> Optional[str]:
        """Detect the OS from an ISO image using osinfo-detect."""
        detect = shutil.which("osinfo-detect")
        if detect is None:
            from boxes.models.media import InstallerMedia

            media = InstallerMedia(iso_path)
            return media.os_type if media.os_type != "generic" else None
        try:
            result = subprocess.run(
                [detect, iso_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split()[0]
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    @staticmethod
    def _fallback_list() -> list[dict]:
        """Fallback: return OS list from built-in OSDatabase."""
        from boxes.models.osdb import OSDatabase

        db = OSDatabase()
        return [{"id": oid, "name": info["name"], "short_id": oid} for oid, info in db._entries.items()]

    @staticmethod
    def _fallback_get(os_id: str) -> Optional[dict]:
        """Fallback: get OS info from built-in OSDatabase."""
        from boxes.models.osdb import OSDatabase

        db = OSDatabase()
        entry = db.get(os_id)
        if entry:
            return {"id": os_id, "name": entry["name"], "short_id": os_id}
        return None
