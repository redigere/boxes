from __future__ import annotations

import json
import getpass
from pathlib import Path
from typing import Optional

from boxes.constants import BOXES_CONFIG


class AuthManager:
    """Handles authentication and credential management.

    Manages libvirt SASL credentials, SSH keys, SPICE
    password authentication, and API tokens.
    """

    def __init__(self) -> None:
        self._credentials_path = BOXES_CONFIG / "credentials.json"
        self._credentials: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self._credentials_path.exists():
            try:
                data = json.loads(self._credentials_path.read_text())
                self._credentials = data.get("credentials", {})
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self) -> None:
        BOXES_CONFIG.mkdir(parents=True, exist_ok=True)
        self._credentials_path.write_text(
            json.dumps({"credentials": self._credentials}, indent=2)
        )

    def set_credential(self, key: str, username: str, password: str) -> None:
        """Store a credential (in plaintext — use keyring for production)."""
        self._credentials[key] = {
            "username": username,
            "password": password,
        }
        self._save()

    def get_credential(self, key: str) -> Optional[dict]:
        """Retrieve a stored credential."""
        return self._credentials.get(key)

    def delete_credential(self, key: str) -> bool:
        """Delete a stored credential."""
        if key in self._credentials:
            del self._credentials[key]
            self._save()
            return True
        return False

    def list_credentials(self) -> dict[str, dict]:
        """List all stored credential keys."""
        return dict(self._credentials)

    @staticmethod
    def prompt_for_password(prompt: str = "Password: ") -> str:
        """Prompt the user for a password (secure input)."""
        return getpass.getpass(prompt)

    @staticmethod
    def check_libvirt_auth() -> bool:
        """Check if libvirt SASL authentication is configured."""
        sasl_paths = [
            "/etc/sasl2/libvirt.conf",
            "/etc/sasl2/libvirt-qemu.conf",
        ]
        for p in sasl_paths:
            if Path(p).exists():
                return True
        return False

    @staticmethod
    def check_ssh_key() -> bool:
        """Check if an SSH key exists for remote connections."""
        ssh_dir = Path.home() / ".ssh"
        if not ssh_dir.exists():
            return False
        for key_file in ["id_rsa", "id_ed25519", "id_ecdsa"]:
            if (ssh_dir / key_file).exists():
                return True
        return False

    def clear_all(self) -> None:
        """Clear all stored credentials."""
        self._credentials.clear()
        self._save()
