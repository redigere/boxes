from __future__ import annotations

import socket
import struct
from typing import Optional


class SPICEChannel:
    """Low-level SPICE protocol channel implementation.

    Handles the SPICE main channel handshake, authentication, and
    capability negotiation.
    """

    SPICE_MAGIC = b"REDQ"
    SPICE_VERSION_MAJOR = 2
    SPICE_VERSION_MINOR = 4

    def __init__(self, host: str = "127.0.0.1", port: int = 5900) -> None:
        self.host = host
        self.port = port
        self._sock: Optional[socket.socket] = None
        self._connected = False
        self._capabilities: set[int] = set()

    def connect(self) -> bool:
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(5.0)
            self._sock.connect((self.host, self.port))
            self._handshake()
            self._connected = True
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def _handshake(self) -> None:
        if not self._sock:
            return
        magic = self._sock.recv(4)
        if magic != self.SPICE_MAGIC:
            return
        _major = self._sock.recv(2)
        _minor = self._sock.recv(2)
        self._sock.send(struct.pack("!HH", self.SPICE_VERSION_MAJOR, self.SPICE_VERSION_MINOR))

    def disconnect(self) -> None:
        self._connected = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    @property
    def connected(self) -> bool:
        return self._connected

    def send(self, data: bytes) -> int:
        if not self._sock or not self._connected:
            raise ConnectionError("SPICE channel not connected")
        return self._sock.send(data)

    def recv(self, bufsize: int = 4096) -> bytes:
        if not self._sock or not self._connected:
            raise ConnectionError("SPICE channel not connected")
        return self._sock.recv(bufsize)
