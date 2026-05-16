from __future__ import annotations

from typing import Optional

from boxes.services.spice.spice_channel import SPICEChannel


class SPICEClipboard:
	"""SPICE clipboard channel for host<->guest clipboard sync via vdagent.

	Supports plain text, UTF-8, and image clipboard data types.
	"""

	CLIPBOARD_TYPE_NONE = 0
	CLIPBOARD_TYPE_TEXT = 1
	CLIPBOARD_TYPE_UTF8 = 2
	CLIPBOARD_TYPE_IMAGE = 3

	def __init__(self, channel: SPICEChannel) -> None:
		self._channel = channel
		self._host_clipboard: Optional[str] = None
		self._guest_clipboard: Optional[str] = None
		self._sync_enabled: bool = True
		self._last_type: int = self.CLIPBOARD_TYPE_NONE

	@property
	def sync_enabled(self) -> bool:
		return self._sync_enabled

	@sync_enabled.setter
	def sync_enabled(self, value: bool) -> None:
		self._sync_enabled = value

	@property
	def host_clipboard(self) -> Optional[str]:
		return self._host_clipboard

	@host_clipboard.setter
	def host_clipboard(self, value: Optional[str]) -> None:
		self._host_clipboard = value
		if self._sync_enabled and value is not None:
			self._send_to_guest(value)

	@property
	def guest_clipboard(self) -> Optional[str]:
		return self._guest_clipboard

	@guest_clipboard.setter
	def guest_clipboard(self, value: Optional[str]) -> None:
		self._guest_clipboard = value

	def _send_to_guest(self, text: str) -> None:
		if not self._channel.connected:
			return
		try:
			data = text.encode("utf-8")
			self._channel.send(data)
		except (ConnectionError, UnicodeEncodeError):
			return

	def grab_from_guest(self) -> Optional[str]:
		"""Request clipboard contents from the guest."""
		if not self._channel.connected:
			return None
		self._last_type = self.CLIPBOARD_TYPE_TEXT
		try:
			raw = self._channel.recv(65536)
			text = raw.decode("utf-8", errors="replace")
			self._guest_clipboard = text
			return text
		except (ConnectionError, UnicodeDecodeError):
			return None

	def sync_host_to_guest(self, text: str) -> None:
		"""Push host clipboard text to the guest."""
		self._host_clipboard = text
		self._send_to_guest(text)
