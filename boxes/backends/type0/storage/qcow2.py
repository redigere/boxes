from __future__ import annotations

import struct
import hashlib
from pathlib import Path
from typing import Optional


QCOW2_MAGIC = 0x514649FB
DEFAULT_CLUSTER_BITS = 16
DEFAULT_CLUSTER_SIZE = 1 << DEFAULT_CLUSTER_BITS
L2_ENTRY_SIZE = 8
L1_ENTRY_SIZE = 8
HEADER_SIZE = 72
HEADER_SIZE_V3 = 104


def _nb_sectors(size: int) -> int:
	return (size + 511) // 512


def _popcount(x: int) -> int:
	return x.bit_count()


def _sub_cluster_bits(cluster_bits: int) -> int:
	return max(4, cluster_bits - 6)


def _l2_bits(cluster_bits: int) -> int:
	return cluster_bits - 3


def _l2_size(cluster_bits: int) -> int:
	return 1 << _l2_bits(cluster_bits)


def _l1_size(size: int, cluster_bits: int) -> int:
	cluster_size = 1 << cluster_bits
	l2_entries = cluster_size // L2_ENTRY_SIZE
	return (size + cluster_size * l2_entries - 1) // (cluster_size * l2_entries)


def _refcount_order_default() -> int:
	return 4


def _refcount_bits(order: int) -> int:
	return 1 << order


def _refcount_entry_size(order: int) -> int:
	return (_refcount_bits(order) + 7) // 8


def _refcounts_per_cluster(cluster_bits: int, order: int) -> int:
	return (1 << cluster_bits) // _refcount_entry_size(order)


def _refcount_table_entries(cluster_bits: int) -> int:
	return (1 << cluster_bits) // 8


def _offset_cluster(offset: int) -> int:
	return offset & ~((1 << 9) - 1)


def _offset_normal(offset: int) -> int:
	return offset & 0x00FFFFFFFFFFFFFF


_OFFSET_MASK = 0x00FFFFFFFFFFFFFF
_CLUSTER_OFFSET_MASK = 0x00FFFFFFFFFFFFFF00
_L2_CLUSTER_OFFSET_MASK = 0x00FFFFFFFFFFFFFF00
_L1_TABLE_OFFSET_MASK = 0x00FFFFFFFFFFFFFF00


class Qcow2Image:
	def __init__(self, path: str | Path) -> None:
		self._path = Path(path)
		self._file: Optional[None] = None
		self._fd: int = -1
		self.magic: int = 0
		self.version: int = 0
		self.backing_file_offset: int = 0
		self.backing_file_size: int = 0
		self.cluster_bits: int = DEFAULT_CLUSTER_BITS
		self.size: int = 0
		self.crypt_method: int = 0
		self.l1_size: int = 0
		self.l1_table_offset: int = 0
		self.refcount_table_offset: int = 0
		self.refcount_table_clusters: int = 0
		self.nb_snapshots: int = 0
		self.snapshots_offset: int = 0
		self.incompatible_features: int = 0
		self.compatible_features: int = 0
		self.autoclear_features: int = 0
		self.refcount_order: int = 4
		self.header_length: int = HEADER_SIZE_V3

	@property
	def cluster_size(self) -> int:
		return 1 << self.cluster_bits

	@property
	def l2_entries(self) -> int:
		return self.cluster_size // L2_ENTRY_SIZE

	@property
	def l1_entries(self) -> int:
		return _l1_size(self.size, self.cluster_bits)

	@classmethod
	def create(
		cls,
		path: str | Path,
		size_gb: int,
		cluster_bits: int = DEFAULT_CLUSTER_BITS,
		prealloc: bool = False,
	) -> Qcow2Image:
		size = size_gb * 1024 * 1024 * 1024
		cluster_size = 1 << cluster_bits
		l2_entries = cluster_size // L2_ENTRY_SIZE
		l1_entries = (size + cluster_size * l2_entries - 1) // (cluster_size * l2_entries)
		l1_clusters = (l1_entries * L1_ENTRY_SIZE + cluster_size - 1) // cluster_size
		l1_offset = cluster_size
		refcount_order = 4
		refcount_entry_bytes = _refcount_entry_size(refcount_order)
		refcounts_per_cluster = cluster_size // refcount_entry_bytes

		total_normal_clusters = l1_clusters + 1
		refcount_table_entries = cluster_size // 8
		refcount_table_needed = (total_normal_clusters + refcounts_per_cluster - 1) // refcounts_per_cluster
		refcount_table_clusters = (refcount_table_needed + refcount_table_entries - 1) // refcount_table_entries
		refcount_table_offset = l1_offset + l1_clusters * cluster_size

		refcount_blocks_needed = (total_normal_clusters + refcounts_per_cluster - 1) // refcounts_per_cluster
		refcount_block_clusters = refcount_blocks_needed
		refcount_block_offset = refcount_table_offset + refcount_table_clusters * cluster_size

		total_clusters = (refcount_block_offset + refcount_block_clusters * cluster_size + cluster_size - 1) // cluster_size

		file_size = total_clusters * cluster_size if prealloc else max(size, cluster_size * (total_clusters + 1))

		buf = bytearray()
		buf += struct.pack(
			">IIQQIIQQIIQQIIQQII",
			QCOW2_MAGIC,
			3,
			0,
			0,
			cluster_bits,
			size,
			0,
			l1_entries,
			l1_offset,
			refcount_table_offset,
			refcount_table_clusters,
			0,
			0,
			0,
			0,
			0,
			0,
			refcount_order,
			HEADER_SIZE_V3,
		)
		buf += b"\x00" * (HEADER_SIZE_V3 - 72)

		img = cls(path)
		p = Path(path)
		if prealloc:
			with p.open("wb") as f:
				f.truncate(file_size)
				f.seek(0)
				f.write(buf)
		else:
			p.write_bytes(buf)
			with p.open("ab") as f:
				f.truncate(file_size)

		img = cls.open(path)
		img._write_l1_table(0, l1_entries)
		img._write_refcount_table(
			refcount_table_offset, refcount_table_clusters, refcount_block_offset, refcount_order
		)
		img._write_refcount_blocks(
			refcount_block_offset, refcount_blocks_needed, cluster_bits, refcount_order
		)
		img._set_refcounts(
			refcount_block_offset,
			refcount_block_clusters,
			refcount_table_offset,
			refcount_table_clusters,
			l1_offset,
			l1_clusters,
			cluster_bits,
			refcount_order,
		)
		img._path = p
		return img

	@classmethod
	def open(cls, path: str | Path) -> Qcow2Image:
		img = cls(path)
		img._fd = -1
		data = Path(path).read_bytes()[:HEADER_SIZE_V3]
		(
			img.magic,
			img.version,
			img.backing_file_offset,
			img.backing_file_size,
			img.cluster_bits,
			img.size,
			img.crypt_method,
			img.l1_size,
			img.l1_table_offset,
			img.refcount_table_offset,
			img.refcount_table_clusters,
			img.nb_snapshots,
			img.snapshots_offset,
			img.incompatible_features,
			img.compatible_features,
			img.autoclear_features,
			img.refcount_order,
			img.header_length,
		) = struct.unpack(">IIQQIIQQIIQQIIQQII", data[:72] if img.version < 3 else data)
		return img

	def _write_l1_table(self, offset: int, entries: int) -> None:
		entry_count = max(entries, self.l1_entries)
		buf = b"\x00" * (entry_count * L1_ENTRY_SIZE)
		with self._path.open("r+b") as f:
			f.seek(offset)
			f.write(buf)

	def _write_refcount_table(
		self, table_offset: int, table_clusters: int, block_offset: int, order: int
	) -> None:
		buf = bytearray()
		cluster_size = self.cluster_size
		entries_per_cluster = cluster_size // 8
		entries_per_block = cluster_size // _refcount_entry_size(order)
		block_idx = 0
		for _ in range(table_clusters):
			cluster_buf = bytearray(cluster_size)
			for j in range(entries_per_cluster):
				if block_idx * entries_per_block + j * entries_per_block < 0:
					continue
				off = block_offset + block_idx * cluster_size
				struct.pack_into(">Q", cluster_buf, j * 8, off)
				block_idx += 1
			buf.extend(cluster_buf)
		with self._path.open("r+b") as f:
			f.seek(table_offset)
			f.write(buf)

	def _write_refcount_blocks(
		self, block_offset: int, block_count: int, cluster_bits: int, order: int
	) -> None:
		buf = bytearray()
		cluster_size = 1 << cluster_bits
		for _ in range(block_count):
			buf.extend(b"\x00" * cluster_size)
		with self._path.open("r+b") as f:
			f.seek(block_offset)
			f.write(buf)

	def _set_refcounts(
		self,
		block_offset: int,
		block_clusters: int,
		table_offset: int,
		table_clusters: int,
		l1_offset: int,
		l1_clusters: int,
		cluster_bits: int,
		order: int,
	) -> None:
		pass

	def _cluster_offset(self, cluster_index: int) -> int:
		return cluster_index << self.cluster_bits

	def _l2_table_for_cluster(self, cluster_index: int) -> tuple[int, int]:
		entries_per_l2 = self.l2_entries
		l2_idx = cluster_index // entries_per_l2
		l2_offset_entry = self._read_l1_entry(l2_idx)
		l2_offset = l2_offset_entry & _L2_CLUSTER_OFFSET_MASK
		l2_slot = cluster_index % entries_per_l2
		return l2_offset, l2_slot

	def _read_l1_entry(self, idx: int) -> int:
		offset = self.l1_table_offset + idx * L1_ENTRY_SIZE
		with self._path.open("rb") as f:
			f.seek(offset)
			return int(struct.unpack(">Q", f.read(8))[0])

	def _read_l2_entry(self, offset: int, slot: int) -> int:
		with self._path.open("rb") as f:
			f.seek(offset + slot * L2_ENTRY_SIZE)
			return int(struct.unpack(">Q", f.read(8))[0])

	def read_at(self, offset: int, size: int) -> bytes:
		result = bytearray()
		cluster_size = self.cluster_size
		cluster_bits = self.cluster_bits
		end = offset + size
		pos = offset
		while pos < end:
			cluster_idx = pos >> cluster_bits
			l2_offset, l2_slot = self._l2_table_for_cluster(cluster_idx)
			if l2_offset == 0:
				result.extend(b"\x00" * min(end - pos, cluster_size - (pos & (cluster_size - 1))))
				pos += cluster_size - (pos & (cluster_size - 1))
				continue
			l2_entry = self._read_l2_entry(l2_offset, l2_slot)
			data_cluster_offset = l2_entry & _CLUSTER_OFFSET_MASK
			if data_cluster_offset == 0:
				result.extend(b"\x00" * min(end - pos, cluster_size - (pos & (cluster_size - 1))))
				pos += cluster_size - (pos & (cluster_size - 1))
				continue
			cluster_start = pos & ~(cluster_size - 1)
			cluster_pos = pos - cluster_start
			read_size = min(end - pos, cluster_size - cluster_pos)
			with self._path.open("rb") as f:
				f.seek(data_cluster_offset + cluster_pos)
				result.extend(f.read(read_size))
			pos += read_size
		return bytes(result)

	def write_at(self, offset: int, data: bytes) -> None:
		cluster_size = self.cluster_size
		cluster_bits = self.cluster_bits
		pos = offset
		data_len = len(data)
		end = offset + data_len
		with self._path.open("r+b") as f:
			while pos < end:
				cluster_idx = pos >> cluster_bits
				l2_offset_entry = self._read_l1_entry(
					cluster_idx // self.l2_entries
				)
				l2_offset = l2_offset_entry & _L2_CLUSTER_OFFSET_MASK
				l2_slot = cluster_idx % self.l2_entries
				l2_entry = self._read_l2_entry(l2_offset, l2_slot) if l2_offset else 0
				data_cluster_offset = l2_entry & _CLUSTER_OFFSET_MASK
				if data_cluster_offset == 0:
					data_cluster_offset = self._alloc_cluster()
					self._write_l2_entry(l2_offset, l2_slot, data_cluster_offset)
				cluster_start = pos & ~(cluster_size - 1)
				cluster_pos = pos - cluster_start
				write_size = min(end - pos, cluster_size - cluster_pos)
				f.seek(data_cluster_offset + cluster_pos)
				f.write(data[:write_size])
				data = data[write_size:]
				pos += write_size

	def _alloc_cluster(self) -> int:
		with self._path.open("ab") as f:
			pos = f.tell()
			f.write(b"\x00" * self.cluster_size)
		return pos - self.cluster_size

	def _write_l2_entry(self, l2_offset: int, slot: int, cluster_offset: int) -> None:
		with self._path.open("r+b") as f:
			f.seek(l2_offset + slot * L2_ENTRY_SIZE)
			f.write(struct.pack(">Q", cluster_offset | 1 << 0))

	def _update_refcount(self, cluster_offset: int, delta: int) -> None:
		pass

	def checksum(self) -> str:
		return hashlib.sha256(self._path.read_bytes()).hexdigest()

	def close(self) -> None:
		pass
