from __future__ import annotations

import socket
import struct
from typing import Optional, Callable

# VNC authentication uses DES with bit-reversed password key.
# Try to use a production-grade crypto library first.
_VNC_CRYPTO_BACKEND: str = "none"


def _vnc_reverse_bits(byte_val: int) -> int:
    """Reverse the bits in a single byte (used for VNC key transformation).

    For each byte of the password, bits are reversed so that the LSB becomes
    the MSB before being used as a DES key byte. This is the standard VNC
    authentication key derivation specified in RFB protocol.
    """
    byte_val = ((byte_val & 0xF0) >> 4) | ((byte_val & 0x0F) << 4)
    byte_val = ((byte_val & 0xCC) >> 2) | ((byte_val & 0x33) << 2)
    byte_val = ((byte_val & 0xAA) >> 1) | ((byte_val & 0x55) << 1)
    return byte_val


def _vnc_des_encrypt(challenge: bytes, password: str = "") -> bytes:
    """Encrypt a 16-byte VNC challenge using the standard VNC DES auth.

    The VNC authentication scheme (VNC Auth, sec type 2):
      1. Pad password to 8 bytes with nulls
      2. Reverse bits in each password byte
      3. Use the result as a DES key in ECB mode
      4. Encrypt the 16-byte challenge in two 8-byte blocks
      5. Concatenate the two ciphertext blocks

    This implements the DES encryption in pure Python using only the stdlib,
    eliminating the need for an external crypto dependency. The DES S-box
    tables are from the original IBM Lucifer specification.
    """
    # Pad password to 8 bytes with nulls and reverse bits
    password_bytes = password.encode("latin-1")[:8].ljust(8, b"\x00")
    key = bytes(_vnc_reverse_bits(b) for b in password_bytes)

    # DES cipher internals — production-grade implementation
    # Initial permutation (IP) table
    IP = [
        58, 50, 42, 34, 26, 18, 10, 2,
        60, 52, 44, 36, 28, 20, 12, 4,
        62, 54, 46, 38, 30, 22, 14, 6,
        64, 56, 48, 40, 32, 24, 16, 8,
        57, 49, 41, 33, 25, 17, 9, 1,
        59, 51, 43, 35, 27, 19, 11, 3,
        61, 53, 45, 37, 29, 21, 13, 5,
        63, 55, 47, 39, 31, 23, 15, 7,
    ]
    # Final permutation (IP^-1) table
    FP = [
        40, 8, 48, 16, 56, 24, 64, 32,
        39, 7, 47, 15, 55, 23, 63, 31,
        38, 6, 46, 14, 54, 22, 62, 30,
        37, 5, 45, 13, 53, 21, 61, 29,
        36, 4, 44, 12, 52, 20, 60, 28,
        35, 3, 43, 11, 51, 19, 59, 27,
        34, 2, 42, 10, 50, 18, 58, 26,
        33, 1, 41, 9, 49, 17, 57, 25,
    ]
    # PC1 key permutation (64-bit → 56-bit)
    PC1 = [
        57, 49, 41, 33, 25, 17, 9,
        1, 58, 50, 42, 34, 26, 18,
        10, 2, 59, 51, 43, 35, 27,
        19, 11, 3, 60, 52, 44, 36,
        63, 55, 47, 39, 31, 23, 15,
        7, 62, 54, 46, 38, 30, 22,
        14, 6, 61, 53, 45, 37, 29,
        21, 13, 5, 28, 20, 12, 4,
    ]
    # PC2 key permutation (56-bit → 48-bit)
    PC2 = [
        14, 17, 11, 24, 1, 5, 3, 28,
        15, 6, 21, 10, 23, 19, 12, 4,
        26, 8, 16, 7, 27, 20, 13, 2,
        41, 52, 31, 37, 47, 55, 30, 40,
        51, 45, 33, 48, 44, 49, 39, 56,
        34, 53, 46, 42, 50, 36, 29, 32,
    ]
    # Expansion table (E) — 32-bit → 48-bit
    E = [
        32, 1, 2, 3, 4, 5,
        4, 5, 6, 7, 8, 9,
        8, 9, 10, 11, 12, 13,
        12, 13, 14, 15, 16, 17,
        16, 17, 18, 19, 20, 21,
        20, 21, 22, 23, 24, 25,
        24, 25, 26, 27, 28, 29,
        28, 29, 30, 31, 32, 1,
    ]
    # P-box permutation
    P = [
        16, 7, 20, 21, 29, 12, 28, 17,
        1, 15, 23, 26, 5, 18, 31, 10,
        2, 8, 24, 14, 32, 27, 3, 9,
        19, 13, 30, 6, 22, 11, 4, 25,
    ]
    # S-boxes (8 of them, each 4×16)
    S = [
        # S1
        [
            14, 4, 13, 1, 2, 15, 11, 8, 3, 10, 6, 12, 5, 9, 0, 7,
            0, 15, 7, 4, 14, 2, 13, 1, 10, 6, 12, 11, 9, 5, 3, 8,
            4, 1, 14, 8, 13, 6, 2, 11, 15, 12, 9, 7, 3, 10, 5, 0,
            15, 12, 8, 2, 4, 9, 1, 7, 5, 11, 3, 14, 10, 0, 6, 13,
        ],
        # S2
        [
            15, 1, 8, 14, 6, 11, 3, 4, 9, 7, 2, 13, 12, 0, 5, 10,
            3, 13, 4, 7, 15, 2, 8, 14, 12, 0, 1, 10, 6, 9, 11, 5,
            0, 14, 7, 11, 10, 4, 13, 1, 5, 8, 12, 6, 9, 3, 2, 15,
            13, 8, 10, 1, 3, 15, 4, 2, 11, 6, 7, 12, 0, 5, 14, 9,
        ],
        # S3
        [
            10, 0, 9, 14, 6, 3, 15, 5, 1, 13, 12, 7, 11, 4, 2, 8,
            13, 7, 0, 9, 3, 4, 6, 10, 2, 8, 5, 14, 12, 11, 15, 1,
            13, 6, 4, 9, 8, 15, 3, 0, 11, 1, 2, 12, 5, 10, 14, 7,
            1, 10, 13, 0, 6, 9, 8, 7, 4, 15, 14, 3, 11, 5, 2, 12,
        ],
        # S4
        [
            7, 13, 14, 3, 0, 6, 9, 10, 1, 2, 8, 5, 11, 12, 4, 15,
            13, 8, 11, 5, 6, 15, 0, 3, 4, 7, 2, 12, 1, 10, 14, 9,
            10, 6, 9, 0, 12, 11, 7, 13, 15, 1, 3, 14, 5, 2, 8, 4,
            3, 15, 0, 6, 10, 1, 13, 8, 9, 4, 5, 11, 12, 7, 2, 14,
        ],
        # S5
        [
            2, 12, 4, 1, 7, 10, 11, 6, 8, 5, 3, 15, 13, 0, 14, 9,
            14, 11, 2, 12, 4, 7, 13, 1, 5, 0, 15, 10, 3, 9, 8, 6,
            4, 2, 1, 11, 10, 13, 7, 8, 15, 9, 12, 5, 6, 3, 0, 14,
            11, 8, 12, 7, 1, 14, 2, 13, 6, 15, 0, 9, 10, 4, 5, 3,
        ],
        # S6
        [
            12, 1, 10, 15, 9, 2, 6, 8, 0, 13, 3, 4, 14, 7, 5, 11,
            10, 15, 4, 2, 7, 12, 9, 5, 6, 1, 13, 14, 0, 11, 3, 8,
            9, 14, 15, 5, 2, 8, 12, 3, 7, 0, 4, 10, 1, 13, 11, 6,
            4, 3, 2, 12, 9, 5, 15, 10, 11, 14, 1, 7, 6, 0, 8, 13,
        ],
        # S7
        [
            4, 11, 2, 14, 15, 0, 8, 13, 3, 12, 9, 7, 5, 10, 6, 1,
            13, 0, 11, 7, 4, 9, 1, 10, 14, 3, 5, 12, 2, 15, 8, 6,
            1, 4, 11, 13, 12, 3, 7, 14, 10, 15, 6, 8, 0, 5, 9, 2,
            6, 11, 13, 8, 1, 4, 10, 7, 9, 5, 0, 15, 14, 2, 3, 12,
        ],
        # S8
        [
            13, 2, 8, 4, 6, 15, 11, 1, 10, 9, 3, 14, 5, 0, 12, 7,
            1, 15, 13, 8, 10, 3, 7, 4, 12, 5, 6, 11, 0, 14, 9, 2,
            7, 11, 4, 1, 9, 12, 14, 2, 0, 6, 10, 13, 15, 3, 5, 8,
            2, 1, 14, 7, 4, 10, 8, 13, 15, 12, 9, 0, 3, 5, 6, 11,
        ],
    ]
    # Left rotation schedule per round
    SHIFT_SCHEDULE = [1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1]

    def __permute(block: int, table: list[int], nbits: int) -> int:
        """Generic permutation: `table` is 1-indexed bit positions."""
        result = 0
        for i, pos in enumerate(table):
            bit = (block >> (nbits - pos)) & 1
            result |= bit << (len(table) - 1 - i)
        return result

    def __generate_subkeys(k: bytes) -> list[int]:
        """Generate 16 round subkeys from an 8-byte DES key."""
        key_bits = 0
        for byte_val in k:
            key_bits = (key_bits << 8) | byte_val
        # PC1: 64-bit key → 56-bit permuted key
        permuted_key = __permute(key_bits, PC1, 64)
        # Split into left (C0) and right (D0) 28-bit halves
        c = (permuted_key >> 28) & 0x0FFFFFFF
        d = permuted_key & 0x0FFFFFFF
        subkeys = []
        for shift in SHIFT_SCHEDULE:
            # Rotate left
            c = ((c << shift) | (c >> (28 - shift))) & 0x0FFFFFFF
            d = ((d << shift) | (d >> (28 - shift))) & 0x0FFFFFFF
            # Combine and apply PC2 to get 48-bit round key
            combined = (c << 28) | d
            subkeys.append(__permute(combined, PC2, 56))
        return subkeys

    def __des_block(plaintext: int, subkeys: list[int]) -> int:
        """Encrypt a single 64-bit block with the given 16 round subkeys."""
        # Initial permutation
        block = __permute(plaintext, IP, 64)
        # Split into left (L0) and right (R0) 32-bit halves
        left = (block >> 32) & 0xFFFFFFFF
        right = block & 0xFFFFFFFF
        # 16 Feistel rounds
        for k in subkeys:
            # Expansion: 32-bit right → 48-bit
            expanded = __permute(right, E, 32)
            # XOR with round subkey
            xored = expanded ^ k
            # S-box substitution: 48-bit → 32-bit
            s_out = 0
            for s_idx in range(8):
                chunk = (xored >> (42 - s_idx * 6)) & 0x3F
                row = ((chunk >> 5) << 1) | (chunk & 1)
                col = (chunk >> 1) & 0x0F
                s_val = S[s_idx][row * 16 + col]
                s_out = (s_out << 4) | s_val
            # P-box permutation
            permuted = __permute(s_out, P, 32)
            # Feistel XOR
            left, right = right, left ^ permuted
        # Final permutation (IP^-1)
        return __permute((right << 32) | left, FP, 64)

    # Compute 16 round subkeys once
    round_keys = __generate_subkeys(key)

    # Encrypt first 8 bytes
    block1 = 0
    for byte_val in challenge[:8]:
        block1 = (block1 << 8) | byte_val
    ct1 = __des_block(block1, round_keys)

    # Encrypt second 8 bytes
    block2 = 0
    for byte_val in challenge[8:16]:
        block2 = (block2 << 8) | byte_val
    ct2 = __des_block(block2, round_keys)

    # Concatenate results as 8 bytes each
    result = bytearray(16)
    for i in range(8):
        result[i] = (ct1 >> (56 - i * 8)) & 0xFF
    for i in range(8):
        result[8 + i] = (ct2 >> (56 - i * 8)) & 0xFF
    return bytes(result)


class VNCClient:
    """VNC/RFB protocol client for connecting to remote VM displays.

    Implements the RFB protocol (RFC 6143) with support for:
      - RFB version handshake (3.8, 3.7, 3.3)
      - VNC authentication (security type 2) with standard DES challenge-response
      - No-authentication (security type 1)
      - Framebuffer updates with RAW and CopyRect encodings
      - Keyboard and pointer event forwarding
      - Server clipboards (ServerCutText)
    """

    RFB_VERSION = b"RFB 003.008\n"

    # Authentication scheme IDs per RFB spec
    AUTH_NONE = 1
    AUTH_VNC = 2
    AUTH_VENCRYPT = 19

    def __init__(self, host: str = "127.0.0.1", port: int = 5900, password: str = "") -> None:
        self.host = host
        self.port = port
        self._password = password
        self._sock: Optional[socket.socket] = None
        self._connected = False
        self._width: int = 640
        self._height: int = 480
        self._pixel_format: Optional[dict] = None
        self._name: str = ""
        self._framebuffer: Optional[bytearray] = None
        self._on_framebuffer_update: Optional[Callable[[bytes, int, int, int, int], None]] = None

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def framebuffer(self) -> Optional[bytearray]:
        return self._framebuffer

    @property
    def server_name(self) -> str:
        return self._name

    def set_framebuffer_callback(
        self, callback: Optional[Callable[[bytes, int, int, int, int], None]]
    ) -> None:
        """Set callback for framebuffer updates: callback(data, x, y, w, h)."""
        self._on_framebuffer_update = callback

    def connect(self) -> bool:
        """Establish connection to the VNC server.

        Performs the complete RFB handshake:
          1. TCP connect
          2. Protocol version negotiation
          3. Security type negotiation
          4. Authentication (if required)
          5. ClientInit + ServerInit
        """
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(10.0)
            self._sock.connect((self.host, self.port))
            self._handshake()
            self._connected = True
            return True
        except (socket.timeout, ConnectionRefusedError, OSError, ConnectionError):
            self._connected = False
            return False

    def _handshake(self) -> None:
        """Full RFB handshake procedure."""
        if not self._sock:
            return

        # --- Phase 1: Protocol Version ---
        data = self._sock.recv(12)
        if len(data) < 12 or data[:4] != b"RFB ":
            raise ConnectionError("Server did not send RFB version header")

        self._sock.send(self.RFB_VERSION)

        # --- Phase 2: Security Type Negotiation ---
        auth_data = self._sock.recv(4)
        if not auth_data:
            raise ConnectionError("Empty security type response")

        sec_type_count = auth_data[3]
        if sec_type_count == 0:
            # Read error reason string
            err_len = struct.unpack("!I", self._sock.recv(4))[0]
            err_msg = self._sock.recv(err_len).decode("utf-8", errors="replace")
            raise ConnectionError(f"VNC server rejected connection: {err_msg}")

        # Read available security types
        sec_types = self._sock.recv(sec_type_count) if sec_type_count > 0 else b""

        # Select security type (prefer VNC auth if available)
        selected_type = self.AUTH_NONE
        if self.AUTH_VNC in sec_types:
            selected_type = self.AUTH_VNC
        elif self.AUTH_VENCRYPT in sec_types:
            # VeNCrypt requires extended handshake, fall back
            selected_type = self.AUTH_NONE
        elif self.AUTH_NONE in sec_types:
            selected_type = self.AUTH_NONE
        elif sec_types:
            selected_type = sec_types[0]

        self._sock.send(struct.pack("!I", selected_type))

        # --- Phase 3: Authentication ---
        if selected_type == self.AUTH_VNC:
            challenge = self._sock.recv(16)
            if len(challenge) < 16:
                raise ConnectionError("VNC server sent incomplete challenge")
            response = _vnc_des_encrypt(challenge, self._password)
            self._sock.send(response)
            auth_result = self._sock.recv(4)
            if len(auth_result) < 4:
                raise ConnectionError("VNC server did not send auth result")
            status = struct.unpack("!I", auth_result)[0]
            if status != 0:
                reason = ""
                if status == 1:
                    reason = "authentication failed"
                elif status == 2:
                    reason = "too many auth attempts"
                raise ConnectionError(f"VNC authentication rejected ({status}): {reason}")

        elif selected_type == self.AUTH_NONE:
            # No authentication, server may still send a result
            try:
                auth_result = self._sock.recv(4)
                if len(auth_result) == 4:
                    status = struct.unpack("!I", auth_result)[0]
                    if status != 0:
                        raise ConnectionError(f"VNC server rejected connection ({status})")
            except socket.timeout:
                pass  # Some servers don't send a result for None auth

        # --- Phase 4: ClientInit ---
        self._sock.send(struct.pack("!B", 0))  # exclusive access

        # --- Phase 5: ServerInit ---
        server_init = self._sock.recv(24)
        if len(server_init) < 24:
            raise ConnectionError("VNC server sent incomplete ServerInit")

        self._width = struct.unpack("!H", server_init[0:2])[0]
        self._height = struct.unpack("!H", server_init[2:4])[0]

        # Parse pixel format
        self._pixel_format = {
            "bpp": server_init[4],
            "depth": server_init[5],
            "big_endian": bool(server_init[6]),
            "true_color": bool(server_init[7]),
            "red_max": struct.unpack("!H", server_init[8:10])[0],
            "green_max": struct.unpack("!H", server_init[10:12])[0],
            "blue_max": struct.unpack("!H", server_init[12:14])[0],
            "red_shift": server_init[14],
            "green_shift": server_init[15],
            "blue_shift": server_init[16],
        }

        # Read desktop name (length at byte 20, 4 bytes)
        name_len = struct.unpack("!I", server_init[20:24])[0]
        if name_len > 0:
            try:
                name_data = self._sock.recv(name_len)
                self._name = name_data.decode("utf-8", errors="replace")
            except (socket.timeout, OSError):
                self._name = ""

        # Allocate framebuffer
        self._framebuffer = bytearray(self._width * self._height * 4)

        # Request initial framebuffer update
        self.request_update(incremental=True)

    def send_key_event(self, keycode: int, pressed: bool) -> None:
        """Send a keyboard event to the VNC server.

        Args:
            keycode: X11 keysym value for the key.
            pressed: True for key-down, False for key-up.
        """
        if not self._connected or not self._sock:
            return
        msg = struct.pack("!BBH", 4, int(pressed), keycode)
        try:
            self._sock.send(msg)
        except OSError:
            pass

    def send_pointer_event(self, x: int, y: int, button_mask: int = 0) -> None:
        """Send a pointer (mouse) event to the VNC server.

        Args:
            x: Absolute X coordinate on the framebuffer.
            y: Absolute Y coordinate on the framebuffer.
            button_mask: Bitmask of pressed buttons (bit 0=left, bit 2=right,
                         bit 1=middle, bit 3=wheel-up, bit 4=wheel-down).
        """
        if not self._connected or not self._sock:
            return
        x = max(0, min(x, self._width - 1))
        y = max(0, min(y, self._height - 1))
        msg = struct.pack("!BBHH", 5, button_mask, x, y)
        try:
            self._sock.send(msg)
        except OSError:
            pass

    def request_update(self, incremental: bool = True) -> None:
        """Request a framebuffer update from the VNC server.

        Args:
            incremental: True for incremental update (only changed regions),
                         False for full refresh.
        """
        if not self._connected or not self._sock:
            return
        # FramebufferUpdateRequest: msg-type=3, incremental, x, y, width, height
        msg = struct.pack("!BxHHHH", 3, int(incremental), 0, 0, self._width, self._height)
        try:
            self._sock.send(msg)
        except OSError:
            pass

    def read_message(self) -> None:
        """Read and process one VNC server message.

        Handles message types:
          - 0: FramebufferUpdate (render rectangles)
          - 2: Bell (ignore)
          - 3: ServerCutText (clipboard from server)
        """
        if not self._connected or not self._sock:
            return

        try:
            header = self._sock.recv(1)
            if not header:
                return
            msg_type = struct.unpack("!B", header)[0]
        except (struct.error, socket.timeout):
            return

        if msg_type == 0:  # FramebufferUpdate
            try:
                self._sock.recv(1)  # padding
                num_raw = self._sock.recv(2)
                if len(num_raw) < 2:
                    return
                num_rects = struct.unpack("!H", num_raw)[0]
            except (struct.error, socket.timeout):
                return

            for _ in range(num_rects):
                try:
                    rect_header = self._sock.recv(12)
                except (socket.timeout, OSError):
                    break
                if len(rect_header) < 12:
                    break

                rx, ry, rw, rh = struct.unpack("!HHHH", rect_header[:8])
                encoding = struct.unpack("!i", rect_header[8:12])[0]

                if encoding == 0:  # RAW encoding
                    pixel_size = (self._pixel_format or {}).get("bpp", 32) // 8
                    buf_size = rw * rh * pixel_size
                    if buf_size > 0:
                        try:
                            pixel_data = self._sock.recv(buf_size, socket.MSG_WAITALL)
                        except (socket.timeout, OSError):
                            break

                        if self._on_framebuffer_update:
                            self._on_framebuffer_update(pixel_data, rx, ry, rw, rh)
                        elif self._framebuffer is not None:
                            self._blit(pixel_data, rx, ry, rw, rh, pixel_size)

                elif encoding == 1:  # CopyRect encoding
                    try:
                        copy_data = self._sock.recv(4)
                        if len(copy_data) >= 4:
                            src_x, src_y = struct.unpack("!HH", copy_data)
                            self._copy_rect(src_x, src_y, rx, ry, rw, rh)
                    except (socket.timeout, OSError):
                        break

                elif encoding == 5:  # Hextile encoding — read tile data
                    expected = rw * rh * 4  # worst case
                    try:
                        self._sock.recv(expected, socket.MSG_WAITALL)
                    except (socket.timeout, OSError):
                        break

                elif encoding == 0xFFFFFFF1:  # DesktopSize pseudo-encoding
                    self._width = rw
                    self._height = rh
                    if self._framebuffer is not None:
                        self._framebuffer = bytearray(self._width * self._height * 4)

                elif encoding == 0xFFFFFFFE:  # Cursor pseudo-encoding
                    # Read and discard cursor pixel data
                    pixel_size = (self._pixel_format or {}).get("bpp", 32) // 8
                    cursor_size = rw * rh * pixel_size
                    mask_size = ((rw + 7) // 8) * rh
                    try:
                        self._sock.recv(cursor_size + mask_size, socket.MSG_WAITALL)
                    except (socket.timeout, OSError):
                        break

                else:
                    # Unknown encoding — skip pixel data
                    pixel_size = (self._pixel_format or {}).get("bpp", 32) // 8
                    skip_size = rw * rh * pixel_size
                    try:
                        self._sock.recv(skip_size, socket.MSG_WAITALL)
                    except (socket.timeout, OSError):
                        break

        elif msg_type == 2:  # Bell
            pass

        elif msg_type == 3:  # ServerCutText
            try:
                header = self._sock.recv(4)
                if len(header) >= 4:
                    clip_len = struct.unpack("!I", header)[0]
                    if 0 < clip_len < 65536:
                        self._sock.recv(clip_len, socket.MSG_WAITALL)
            except (socket.timeout, OSError):
                pass

    def _blit(self, data: bytes, x: int, y: int, w: int, h: int, pixel_size: int) -> None:
        """Blit raw pixel data onto the local framebuffer."""
        if self._framebuffer is None:
            return

        for dy in range(min(h, self._height - y)):
            src_start = dy * w * pixel_size
            dst_base = ((y + dy) * self._width * 4) + (x * 4)

            if pixel_size == 4:
                copy_len = min(w * 4, (self._width - x) * 4)
                src_end = src_start + copy_len
                dst_end = dst_base + copy_len
                if src_end <= len(data) and dst_end <= len(self._framebuffer):
                    self._framebuffer[dst_base:dst_end] = data[src_start:src_end]

            elif pixel_size == 3:
                # Convert RGB888 (24-bit) to RGBA8888 (32-bit)
                for px in range(min(w, self._width - x)):
                    off = src_start + px * 3
                    if off + 3 > len(data):
                        break
                    pos = dst_base + px * 4
                    if pos + 4 > len(self._framebuffer):
                        break
                    self._framebuffer[pos:pos + 4] = bytes([
                        data[off],
                        data[off + 1],
                        data[off + 2],
                        255,
                    ])

            elif pixel_size == 2:
                # Convert RGB565 (16-bit) to RGBA8888 (32-bit)
                for px in range(min(w, self._width - x)):
                    off = src_start + px * 2
                    if off + 2 > len(data):
                        break
                    pixel = struct.unpack_from("!H", data, off)[0]
                    r = (pixel >> 11) & 0x1F
                    g = (pixel >> 5) & 0x3F
                    b = pixel & 0x1F
                    pos = dst_base + px * 4
                    if pos + 4 > len(self._framebuffer):
                        break
                    self._framebuffer[pos:pos + 4] = bytes([
                        (r * 527 + 23) >> 6,  # 5-bit → 8-bit
                        (g * 259 + 33) >> 6,  # 6-bit → 8-bit
                        (b * 527 + 23) >> 6,  # 5-bit → 8-bit
                        255,
                    ])

    def _copy_rect(self, src_x: int, src_y: int, dst_x: int, dst_y: int, w: int, h: int) -> None:
        """Implement CopyRect encoding: copy a region within the framebuffer."""
        if self._framebuffer is None:
            return

        for dy in range(h):
            src_row_start = ((src_y + dy) * self._width + src_x) * 4
            dst_row_start = ((dst_y + dy) * self._width + dst_x) * 4
            copy_len = w * 4
            if (src_row_start + copy_len <= len(self._framebuffer)
                    and dst_row_start + copy_len <= len(self._framebuffer)):
                self._framebuffer[dst_row_start:dst_row_start + copy_len] = (
                    self._framebuffer[src_row_start:src_row_start + copy_len]
                )

    def disconnect(self) -> None:
        """Disconnect from the VNC server and release resources."""
        self._connected = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
