from typing import Optional
import subprocess
import os
import signal


class QEMUProcess:
    def __init__(self, binary: str = "qemu-system-x86_64") -> None:
        self.binary = binary
        self._process: Optional[subprocess.Popen] = None
        self._monitor_sock: Optional[str] = None

    def probe(self) -> bool:
        try:
            subprocess.run([self.binary, "--version"], capture_output=True, timeout=5)
            return True
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return False

    def launch(
        self,
        args: list[str],
        monitor_sock: Optional[str] = None,
    ) -> Optional[subprocess.Popen]:
        self._monitor_sock = monitor_sock
        qemu_args = [self.binary, "-display", "none", "-daemonize"]
        if monitor_sock:
            qemu_args.extend(["-qmp", f"unix:{monitor_sock},server,nowait"])
        qemu_args.extend(args)
        try:
            self._process = subprocess.Popen(
                qemu_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return self._process
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return None

    def stop(self) -> bool:
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=10)
                return True
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=5)
                return True
            except OSError:
                pass
            finally:
                self._process = None
        return True

    def force_stop(self) -> bool:
        if self._process:
            try:
                os.kill(self._process.pid, signal.SIGKILL)
                self._process.wait(timeout=5)
                return True
            except OSError:
                pass
            finally:
                self._process = None
        return False

    @property
    def running(self) -> bool:
        if self._process is None:
            return False
        return self._process.poll() is None

    @property
    def pid(self) -> Optional[int]:
        return self._process.pid if self._process else None
