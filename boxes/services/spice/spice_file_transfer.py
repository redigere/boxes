from __future__ import annotations

from pathlib import Path
from typing import Optional, Callable, cast

from boxes.services.spice.spice_channel import SPICEChannel


class SPICEFileTransfer:
	"""SPICE file transfer channel for drag-and-drop files.

	Handles sending files from host to guest and receiving files
	from guest to host via the SPICE vdagent protocol.
	"""

	CHUNK_SIZE = 65536

	def __init__(self, channel: SPICEChannel) -> None:
		self._channel = channel
		self._active_transfers: dict[str, dict[str, str | int]] = {}

	def send_file(
		self,
		host_path: str,
		guest_path: str = "",
		on_progress: Optional[Callable[[int, int], None]] = None,
	) -> bool:
		"""Send a file from host to the SPICE guest."""
		if not self._channel.connected:
			return False
		src = Path(host_path)
		if not src.exists() or not src.is_file():
			return False
		dest = guest_path or src.name
		file_size = src.stat().st_size
		transfer_id = f"host-to-guest-{dest}"
		self._active_transfers[transfer_id] = {
			"path": dest,
			"total": file_size,
			"sent": 0,
		}
		try:
			metadata = f"FILENAME:{dest}\nSIZE:{file_size}\n".encode()
			self._channel.send(metadata)
			with open(src, "rb") as f:
				while chunk := f.read(self.CHUNK_SIZE):
					self._channel.send(chunk)
					sent = cast(int, self._active_transfers[transfer_id]["sent"]) + len(chunk)
					self._active_transfers[transfer_id]["sent"] = sent
					if on_progress:
						on_progress(sent, file_size)
			self._channel.send(b"DONE")
			return True
		except (ConnectionError, OSError):
			self._active_transfers.pop(transfer_id, None)
			return False

	def receive_file(
		self,
		dest_dir: str,
		filename: str = "",
		on_progress: Optional[Callable[[int, int], None]] = None,
	) -> Optional[str]:
		"""Receive a file from the SPICE guest."""
		if not self._channel.connected:
			return None
		dest = Path(dest_dir)
		dest.mkdir(parents=True, exist_ok=True)
		try:
			header = self._channel.recv(256)
			header_text = header.decode("utf-8", errors="replace")
			guest_filename = filename or "received_file"
			file_size = 0
			for line in header_text.split("\n"):
				if line.startswith("FILENAME:"):
					guest_filename = line.replace("FILENAME:", "").strip()
				elif line.startswith("SIZE:"):
					file_size = int(line.replace("SIZE:", "").strip())
			output_path = dest / guest_filename
			received = 0
			with open(output_path, "wb") as f:
				while True:
					data = self._channel.recv(self.CHUNK_SIZE)
					if not data or data == b"DONE":
						break
					f.write(data)
					received += len(data)
					if on_progress and file_size > 0:
						on_progress(received, file_size)
			return str(output_path)
		except (ConnectionError, OSError, ValueError):
			return None

	def cancel_transfer(self, transfer_id: str) -> bool:
		"""Cancel an active file transfer."""
		if transfer_id in self._active_transfers:
			self._active_transfers.pop(transfer_id, None)
			return True
		return False

	def active_count(self) -> int:
		"""Return the number of active file transfers."""
		return len(self._active_transfers)
