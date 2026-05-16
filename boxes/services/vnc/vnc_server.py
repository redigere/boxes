from __future__ import annotations

import socket
import struct
import threading
from typing import Optional, Callable


class VNCServer:
	"""Minimal VNC server that can serve a VM display.

	Useful for backends that export a VNC framebuffer but don't
	include a built-in VNC server.
	"""

	def __init__(self, host: str = "127.0.0.1", port: int = 5900) -> None:
		self.host = host
		self.port = port
		self._server_sock: Optional[socket.socket] = None
		self._clients: list[socket.socket] = []
		self._running = False
		self._thread: Optional[threading.Thread] = None
		self._framebuffer: bytearray = bytearray(640 * 480 * 4)
		self._width: int = 640
		self._height: int = 480
		self._on_client_connect: Optional[Callable[[str], None]] = None
		self._on_client_disconnect: Optional[Callable[[str], None]] = None

	@property
	def running(self) -> bool:
		return self._running

	@property
	def client_count(self) -> int:
		return len(self._clients)

	def set_framebuffer(self, data: bytes, width: int, height: int) -> None:
		"""Update the framebuffer and notify all connected clients."""
		self._width = width
		self._height = height
		expected = width * height * 4
		if len(data) < expected:
			data = data.ljust(expected, b"\x00")
		self._framebuffer = bytearray(data[:expected])
		self._broadcast_framebuffer()

	def start(self) -> bool:
		try:
			self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self._server_sock.bind((self.host, self.port))
			self._server_sock.listen(5)
			self._server_sock.settimeout(1.0)
			self._running = True
			self._thread = threading.Thread(target=self._accept_loop, daemon=True)
			self._thread.start()
			return True
		except OSError:
			return False

	def _accept_loop(self) -> None:
		while self._running:
			try:
				client, addr = self._server_sock.accept()
				self._clients.append(client)
				if self._on_client_connect:
					self._on_client_connect(f"{addr[0]}:{addr[1]}")
			except socket.timeout:
				continue
			except OSError:
				break
		self._cleanup_clients()

	def _broadcast_framebuffer(self) -> None:
		disconnected = []
		for client in self._clients:
			try:
				fb_header = struct.pack("!BxH", 0, 1)
				rect_header = struct.pack("!HHHHi", 0, 0, self._width, self._height, 0)
				client.send(fb_header + rect_header + bytes(self._framebuffer))
			except OSError:
				disconnected.append(client)
		for client in disconnected:
			self._clients.remove(client)
			addr = "unknown"
			try:
				addr = str(client.getpeername())
			except OSError:
				addr = "unknown"
			if self._on_client_disconnect:
				self._on_client_disconnect(addr)

	def _cleanup_clients(self) -> None:
		for client in self._clients:
			try:
				client.close()
			except OSError:
				continue
		self._clients.clear()

	def stop(self) -> None:
		self._running = False
		if self._thread:
			self._thread.join(timeout=2.0)
		if self._server_sock:
			try:
				self._server_sock.close()
			except OSError:
				self._server_sock = None
			self._server_sock = None
		self._cleanup_clients()
