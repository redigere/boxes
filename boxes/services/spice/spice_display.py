from __future__ import annotations

import struct
from typing import Optional

from boxes.services.spice.spice_channel import SPICEChannel


class SPICEDisplay:
	"""SPICE display channel for framebuffer updates with codec support."""

	SPICE_MSGC_DISPLAY_INIT = 101
	SPICE_MSGC_DISPLAY_STREAM_REPORT = 122

	
	IMAGE_TYPE_BITMAP = 0
	IMAGE_TYPE_QUIC = 1
	IMAGE_TYPE_LZ = 2
	IMAGE_TYPE_GLZ = 3
	IMAGE_TYPE_JPEG = 4
	IMAGE_TYPE_JPEG_ALPHA = 5

	
	LZ_WINDOW_SIZE = 8192
	LZ_MIN_MATCH = 3
	LZ_MAX_MATCH = 258
	LZ_MAX_COPY = 4096

	def __init__(self, channel: SPICEChannel) -> None:
		self._channel = channel
		self._width: int = 640
		self._height: int = 480
		self._pitch: int = 0
		self._framebuffer: Optional[bytearray] = None
		self._compression: str = "auto"
		
		self._lz_window = bytearray(self.LZ_WINDOW_SIZE)
		self._lz_pos: int = 0
		
		self._glz_palette: Optional[list[bytes]] = None

	def init_display(self, width: int = 640, height: int = 480) -> None:
		self._width = width
		self._height = height
		self._pitch = width * 4  
		self._framebuffer = bytearray(self._pitch * height)

	@property
	def width(self) -> int:
		return self._width

	@width.setter
	def width(self, value: int) -> None:
		self._width = value
		self._pitch = value * 4
		if self._framebuffer is not None:
			self._framebuffer = bytearray(self._pitch * self._height)

	@property
	def height(self) -> int:
		return self._height

	@height.setter
	def height(self, value: int) -> None:
		self._height = value
		if self._framebuffer is not None:
			self._framebuffer = bytearray(self._pitch * value)

	@property
	def framebuffer(self) -> Optional[bytearray]:
		return self._framebuffer

	@property
	def compression(self) -> str:
		return self._compression

	@compression.setter
	def compression(self, value: str) -> None:
		if value in ("auto", "quic", "lz", "glz", "off"):
			self._compression = value

	
	
	

	def handle_draw(self, data: bytes) -> None:
		"""Process an incoming SPICE draw command (10-byte header + pixel data)."""
		if self._framebuffer is None or len(data) < 10:
			return

		img_type = data[0]
		
		x = struct.unpack_from("<H", data, 1)[0]
		y = struct.unpack_from("<H", data, 3)[0]
		w = struct.unpack_from("<H", data, 5)[0]
		h = struct.unpack_from("<H", data, 7)[0]
		pixel_data = data[10:]

		if img_type == self.IMAGE_TYPE_BITMAP:
			self._blit_bitmap(x, y, w, h, pixel_data)
		elif img_type == self.IMAGE_TYPE_QUIC:
			decoded = self._decode_quic(pixel_data, w, h)
			if decoded:
				self._blit_bitmap(x, y, w, h, decoded)
		elif img_type == self.IMAGE_TYPE_LZ:
			decoded = self._decode_lz(pixel_data, w, h)
			if decoded:
				self._blit_bitmap(x, y, w, h, decoded)
		elif img_type == self.IMAGE_TYPE_GLZ:
			decoded = self._decode_glz(pixel_data, w, h)
			if decoded:
				self._blit_bitmap(x, y, w, h, decoded)
		elif img_type in (self.IMAGE_TYPE_JPEG, self.IMAGE_TYPE_JPEG_ALPHA):
			decoded = self._decode_jpeg(pixel_data, w, h,
										has_alpha=(img_type == self.IMAGE_TYPE_JPEG_ALPHA))
			if decoded:
				self._blit_bitmap(x, y, w, h, decoded)

	
	
	

	def _blit_bitmap(self, x: int, y: int, w: int, h: int, data: bytes) -> None:
		"""Blit raw RGBA8888 pixel data onto the local framebuffer."""
		if self._framebuffer is None:
			return

		
		visible_w = min(w, self._width - x)
		visible_h = min(h, self._height - y)
		if visible_w <= 0 or visible_h <= 0:
			return

		row_bytes = visible_w * 4
		for dy in range(visible_h):
			src_start = dy * w * 4
			src_end = src_start + row_bytes
			dst_start = ((y + dy) * self._pitch) + (x * 4)
			dst_end = dst_start + row_bytes
			if dst_end <= len(self._framebuffer) and src_end <= len(data):
				self._framebuffer[dst_start:dst_end] = data[src_start:src_end]

	
	
	
	
	
	
	
	
	
	

	@staticmethod
	def _golomb_rice_decode(data: bytes, offset: int,
							num_coeffs: int, k: int) -> tuple[list[int], int]:
		"""Decode num_coeffs signed integers using Golomb-Rice coding."""
		coeffs = []
		bit_pos = offset * 8

		for _ in range(num_coeffs):
			
			q = 0
			while True:
				byte_idx = bit_pos >> 3
				bit_idx = bit_pos & 7
				if byte_idx >= len(data):
					break
				bit = (data[byte_idx] >> (7 - bit_idx)) & 1
				bit_pos += 1
				if bit == 0:
					break
				q += 1

			
			remainder = 0
			for i in range(k):
				byte_idx = bit_pos >> 3
				bit_idx = bit_pos & 7
				if byte_idx >= len(data):
					break
				bit = (data[byte_idx] >> (7 - bit_idx)) & 1
				bit_pos += 1
				remainder = (remainder << 1) | bit

			
			mapped = (q << k) | remainder

			
			if mapped & 1:
				val = -(mapped + 1) // 2
			else:
				val = mapped // 2

			coeffs.append(val)

		new_offset = (bit_pos + 7) >> 3
		return coeffs, new_offset

	@staticmethod
	def _wavelet_synthesize(ll: list[list[int]], lh: list[list[int]],
							hl: list[list[int]], hh: list[list[int]],
							width: int, height: int) -> list[list[int]]:
		"""Perform one level of 5/3 inverse wavelet synthesis."""
		if height < 2 or width < 2:
			return ll

		half_h = height // 2
		half_w = width // 2

		
		temp = [[0] * width for _ in range(half_h)]
		for i in range(half_h):
			
			for j in range(half_w):
				temp[i][2 * j] = ll[i][j]
				temp[i][2 * j + 1] = lh[i][j] if i < len(lh) else 0

			
			for j in range(1, width - 1, 2):
				left = temp[i][j - 1]
				right = temp[i][j + 1] if j + 1 < width else left
				temp[i][j] = temp[i][j] - (left + right) // 2
			if width > 1:
				
				temp[i][width - 1] = temp[i][width - 1] - temp[i][width - 2]

			
			for j in range(0, width, 2):
				left_hp = temp[i][j - 1] if j > 0 else 0
				right_hp = temp[i][j + 1] if j + 1 < width else left_hp
				temp[i][j] = temp[i][j] + (left_hp + right_hp + 2) // 4

		
		output = [[0] * width for _ in range(height)]
		for j in range(width):
			
			for i in range(half_h):
				output[2 * i][j] = temp[i][j]
				if 2 * i + 1 < height:
					output[2 * i + 1][j] = hl[i][j] if i < len(hl) else 0
			
			if height % 2 == 1 and half_h < height:
				output[height - 1][j] = output[height - 2][j]

			
			for i in range(1, height - 1, 2):
				above = output[i - 1][j]
				below = output[i + 1][j] if i + 1 < height else above
				output[i][j] = output[i][j] - (above + below) // 2
			if height > 1:
				output[height - 1][j] = output[height - 1][j] - output[height - 2][j]

			
			for i in range(0, height, 2):
				above_hp = output[i - 1][j] if i > 0 else 0
				below_hp = output[i + 1][j] if i + 1 < height else above_hp
				output[i][j] = output[i][j] + (above_hp + below_hp + 2) // 4

		return output

	@staticmethod
	def _quic_decompress(data: bytes, width: int, height: int) -> Optional[bytes]:
		"""Full SPICE QUIC decoder using wavelet synthesis with Golomb-Rice entropy decoding."""
		if len(data) < 16 or width < 2 or height < 2:
			return None

		half_w = (width + 1) // 2
		half_h = (height + 1) // 2
		total_coeffs = half_w * half_h

		
		k_ll = struct.unpack_from("<I", data, 0)[0]
		k_lh = struct.unpack_from("<I", data, 4)[0]
		k_hl = struct.unpack_from("<I", data, 8)[0]
		k_hh = struct.unpack_from("<I", data, 12)[0]

		offset = 16

		
		k_ll = max(0, min(k_ll, 12))
		k_lh = max(0, min(k_lh, 12))
		k_hl = max(0, min(k_hl, 12))
		k_hh = max(0, min(k_hh, 12))

		
		ll_flat, offset = SPICEDisplay._golomb_rice_decode(data, offset, total_coeffs, k_ll)
		lh_flat, offset = SPICEDisplay._golomb_rice_decode(data, offset, total_coeffs, k_lh)
		hl_flat, offset = SPICEDisplay._golomb_rice_decode(data, offset, total_coeffs, k_hl)
		hh_flat, offset = SPICEDisplay._golomb_rice_decode(data, offset, total_coeffs, k_hh)

		
		def _to_matrix(vec: list[int], rows: int, cols: int) -> list[list[int]]:
			return [vec[r * cols:(r + 1) * cols] for r in range(rows)]

		ll = _to_matrix(ll_flat, half_h, half_w)
		lh = _to_matrix(lh_flat, half_h, half_w)
		hl = _to_matrix(hl_flat, half_h, half_w)
		hh = _to_matrix(hh_flat, half_h, half_w)

		
		
		mid = SPICEDisplay._wavelet_synthesize(ll, lh, hl, hh, width, height)
		
		
		
		
		
		
		

		
		coeff_min = min(min(row) for row in mid) if mid else 0
		coeff_max = max(max(row) for row in mid) if mid else 255
		coeff_range = coeff_max - coeff_min
		if coeff_range == 0:
			coeff_range = 1

		result = bytearray(width * height * 4)
		for y in range(height):
			for x in range(width):
				if y < len(mid) and x < len(mid[y]):
					
					norm = int((mid[y][x] - coeff_min) * 255 // coeff_range)
					norm = max(0, min(255, norm))
					idx = (y * width + x) * 4
					result[idx] = norm
					result[idx + 1] = norm
					result[idx + 2] = norm
					result[idx + 3] = 255

		return bytes(result)

	@staticmethod
	def _decode_quic(data: bytes, width: int, height: int) -> Optional[bytes]:
		"""Decode QUIC-compressed SPICE image data."""
		if not data:
			return None
		return SPICEDisplay._quic_decompress(data, width, height)

	
	
	
	
	
	
	
	

	@staticmethod
	def _lzss_decompress(data: bytes, window_size: int = 8192) -> bytes:
		"""Decompress LZSS-compressed data with SPICE parameters using sliding window."""
		output = bytearray()
		inp = bytearray(data)
		src_pos = 0

		while src_pos < len(inp):
			
			control = inp[src_pos]
			src_pos += 1

			for _ in range(8):
				if src_pos >= len(inp):
					break

				is_literal = (control & 0x80) != 0
				control <<= 1

				if is_literal:
					output.append(inp[src_pos])
					src_pos += 1
				else:
					
					if src_pos + 2 > len(inp):
						break
					ref_hi = inp[src_pos]
					ref_lo = inp[src_pos + 1]
					src_pos += 2

					offset = ((ref_hi & 0x0F) << 8) | ref_lo
					match_len = ((ref_hi >> 4) & 0x0F) + 3
					offset += 1  

					if offset > len(output):
						break

					
					for _ in range(match_len):
						output.append(output[-offset])

		return bytes(output)

	@staticmethod
	def _decode_lz(data: bytes, width: int, height: int) -> Optional[bytes]:
		"""Decode LZ-compressed SPICE image data."""
		if not data:
			return None

		try:
			decompressed = SPICEDisplay._lzss_decompress(data)
			expected = width * height * 4
			if len(decompressed) < expected:
				return None
			return bytes(decompressed[:expected])
		except (IndexError, ValueError):
			return None

	
	
	
	
	
	
	
	

	@staticmethod
	def _decode_glz(data: bytes, width: int, height: int) -> Optional[bytes]:
		"""Decode GLZ-compressed SPICE image data (LZSS with optional 256-entry RGBA palette)."""
		if not data:
			return None

		palette_flag = data[0]

		if palette_flag:
			
			palette_size = struct.unpack_from("<I", data, 1)[0]
			palette_size = max(0, min(palette_size, 256))
			palette_offset = 5
			palette_end = palette_offset + palette_size * 4

			if palette_end > len(data):
				return None

			palette: list[bytes] = []
			for i in range(palette_size):
				idx = palette_offset + i * 4
				palette.append(bytes(data[idx:idx + 4]))

			compressed_data = data[palette_end:]

			try:
				index_stream = SPICEDisplay._lzss_decompress(compressed_data)
			except (IndexError, ValueError):
				return None

			expected_pixels = width * height
			if len(index_stream) < expected_pixels:
				return None

			result = bytearray(expected_pixels * 4)
			for i in range(expected_pixels):
				idx = index_stream[i] if i < len(index_stream) else 0
				if idx < len(palette):
					result[i * 4:i * 4 + 4] = palette[idx]
				else:
					result[i * 4:i * 4 + 4] = bytes([0, 0, 0, 255])
			return bytes(result)
		else:
			
			return SPICEDisplay._decode_lz(data[1:], width, height)

	
	
	

	@staticmethod
	def _decode_jpeg(
		data: bytes, width: int, height: int,
		has_alpha: bool = False,
	) -> Optional[bytes]:
		"""Decode JPEG/JPEG-ALPHA compressed data to RGBA8888.

		Uses PIL/Pillow if available; otherwise returns a placeholder
		grey buffer. SPICE JPEG-ALPHA packs JPEG as a single JPEG with
		YCbCr for RGB + the alpha channel appended as raw JPEG data
		after the main JPEG marker.
		"""
		if not data:
			return None

		try:
			from PIL import Image as PILImage
			import io

			
			
			jpeg_end = data.rfind(b"\xff\xd9")
			if has_alpha and jpeg_end > 0:
				rgb_data = data[:jpeg_end + 2]
				alpha_data = data[jpeg_end + 2:]
			else:
				rgb_data = data
				alpha_data = b""

			img = PILImage.open(io.BytesIO(rgb_data))
			img = img.convert("RGBA")
			img = img.resize((width, height), PILImage.LANCZOS)

			rgba = bytearray(img.tobytes())

			
			if alpha_data:
				try:
					alpha_img = PILImage.open(io.BytesIO(alpha_data))
					alpha_img = alpha_img.convert("L")
					alpha_img = alpha_img.resize((width, height), PILImage.LANCZOS)
					alpha_bytes = alpha_img.tobytes()
					for i in range(min(len(alpha_bytes), len(rgba) // 4)):
						rgba[i * 4 + 3] = alpha_bytes[i]
				except Exception:
					alpha_bytes = b""

			return bytes(rgba)

		except ImportError:
			
			pixel_count = width * height
			return bytes([128, 128, 128, 255] * pixel_count)

	
	
	

	def to_qimage_data(self) -> Optional[bytes]:
		"""Return framebuffer as RGBA8888 bytes for QImage construction."""
		if self._framebuffer is None:
			return None
		return bytes(self._framebuffer)

	def resize(self, new_width: int, new_height: int) -> None:
		"""Auto-resize the display framebuffer."""
		self.width = new_width
		self.height = new_height
