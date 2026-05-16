from __future__ import annotations

import time
import subprocess
from typing import Optional, Callable


class BenchmarkRunner:
	"""Performance benchmark suite for VM operations.

	Measures boot time, IOPS, network throughput, and memory
	bandwidth for VM instances across all backends.
	"""

	def __init__(self) -> None:
		self._results: dict[str, dict] = {}
		self._on_progress: Optional[Callable[[str, int], None]] = None

	def set_progress_callback(self, callback: Optional[Callable[[str, int], None]]) -> None:
		self._on_progress = callback

	def measure_boot_time(self, backend_id: str, backend) -> Optional[float]:
		"""Measure VM boot time from start to responsive state."""
		start = time.monotonic()
		if not backend.start_machine(backend_id):
			return None
		timeout = 120
		poll_interval = 0.5
		elapsed = 0.0
		while elapsed < timeout:
			state = backend.get_state(backend_id)
			if state == 1:  
				return time.monotonic() - start
			time.sleep(poll_interval)
			elapsed += poll_interval
		return None

	def measure_disk_iops(
		self,
		backend_id: str,
		backend,
		ssh_cmd: Optional[list[str]] = None,
	) -> Optional[dict]:
		"""Measure disk IOPS using 'dd' or 'fio' in the guest."""
		if not ssh_cmd:
			return None
		results: dict = {}
		try:
			result = subprocess.run(
				ssh_cmd + [
					"dd", "if=/dev/zero", "of=/tmp/boxes-benchmark",
					"bs=1M", "count=256", "oflag=direct",
					"2>&1",
				],
				capture_output=True,
				text=True,
				timeout=60,
			)
			for line in result.stdout.split("\n"):
				if "MB/s" in line:
					parts = line.strip().split()
					for i, p in enumerate(parts):
						if "MB/s" in p:
							results["write_mbps"] = float(p.replace("MB/s", ""))
							break
			result = subprocess.run(
				ssh_cmd + [
					"dd", "if=/tmp/boxes-benchmark", "of=/dev/null",
					"bs=1M", "count=256", "iflag=direct",
					"2>&1",
				],
				capture_output=True,
				text=True,
				timeout=60,
			)
			for line in result.stdout.split("\n"):
				if "MB/s" in line:
					parts = line.strip().split()
					for i, p in enumerate(parts):
						if "MB/s" in p:
							results["read_mbps"] = float(p.replace("MB/s", ""))
							break
		except (subprocess.TimeoutExpired, FileNotFoundError):
			return None

	def measure_network_throughput(
		self,
		guest_ip: str,
		duration: int = 10,
	) -> Optional[dict]:
		"""Measure network throughput using iperf3 to the guest."""
		results: dict = {}
		try:
			result = subprocess.run(
				["iperf3", "-c", guest_ip, "-t", str(duration), "-J"],
				capture_output=True,
				text=True,
				timeout=duration + 10,
			)
			import json

			data = json.loads(result.stdout)
			if "end" in data and "sum_received" in data["end"]:
				results["mbps"] = data["end"]["sum_received"].get("bits_per_second", 0) / 1_000_000
		except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, ValueError):
			return None

	def measure_memory_bandwidth(self, ssh_cmd: Optional[list[str]] = None) -> Optional[dict]:
		"""Measure memory bandwidth using mbw in the guest."""
		if not ssh_cmd:
			return None
		try:
			result = subprocess.run(
				ssh_cmd + ["mbw", "256"],
				capture_output=True,
				text=True,
				timeout=30,
			)
			results: dict = {}
			for line in result.stdout.split("\n"):
				if "MEMCPY" in line:
					parts = line.strip().split()
					if len(parts) >= 2:
						try:
							results["memcpy_mib"] = float(parts[-1])
						except ValueError:
							continue
				elif "DUMB" in line:
					parts = line.strip().split()
					if len(parts) >= 2:
						try:
							results["dumb_mib"] = float(parts[-1])
						except ValueError:
							continue
			return results if results else None
		except (subprocess.TimeoutExpired, FileNotFoundError):
			return None

	def run_all(self, backend_id: str, backend) -> dict:
		"""Run all benchmarks and return results."""
		self._results = {}
		if self._on_progress:
			self._on_progress("boot_time", 25)
		boot = self.measure_boot_time(backend_id, backend)
		if boot is not None:
			self._results["boot_time_seconds"] = boot
		return self._results

	def get_results(self) -> dict:
		return dict(self._results)

	def clear(self) -> None:
		self._results.clear()
