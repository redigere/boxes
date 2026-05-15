from __future__ import annotations
import sys
import os
import traceback
import subprocess
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DiagnosticRecord:
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    operation: str = ""
    component: str = ""
    success: bool = False
    error_type: str = ""
    error_message: str = ""
    traceback: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    resolution: str = ""


class RootCause:
    def __init__(self) -> None:
        self._records: list[DiagnosticRecord] = []
        self._capture_enabled = True

    def record(
        self,
        operation: str,
        component: str,
        success: bool,
        error: Optional[Exception] = None,
        context: Optional[dict[str, Any]] = None,
        resolution: str = "",
    ) -> DiagnosticRecord:
        rec = DiagnosticRecord(
            operation=operation,
            component=component,
            success=success,
            error_type=type(error).__name__ if error else "",
            error_message=str(error) if error else "",
            traceback="".join(traceback.format_exception(type(error), error, error.__traceback__))
            if error
            else "",
            context=context or {},
            resolution=resolution,
        )
        self._records.append(rec)
        return rec

    def diagnose(self, error: Exception, component: str, operation: str) -> DiagnosticRecord:
        ctx = self._gather_context(component)
        resolution = self._suggest_resolution(error, component)
        return self.record(
            operation=operation,
            component=component,
            success=False,
            error=error,
            context=ctx,
            resolution=resolution,
        )

    def _gather_context(self, component: str) -> dict[str, Any]:
        ctx: dict[str, Any] = {
            "python": sys.version,
            "platform": sys.platform,
            "cwd": os.getcwd(),
        }
        if component in ("kvm", "type0"):
            ctx["/dev/kvm"] = Path("/dev/kvm").exists()
        if component == "xen":
            ctx["/proc/xen"] = Path("/proc/xen").exists()
            ctx["xl"] = self._which("xl") or ""
        if component in ("qemu", "type0"):
            ctx["qemu-img"] = self._which("qemu-img") or ""
            for arch in ("x86_64", "aarch64"):
                ctx[f"qemu-system-{arch}"] = self._which(f"qemu-system-{arch}") or ""
        if component == "libvirt":
            ctx["virsh"] = self._which("virsh") or ""
        if component == "ssh":
            ctx["ssh"] = self._which("ssh") or ""
        if component == "display":
            ctx["DISPLAY"] = os.environ.get("DISPLAY", "")
            ctx["WAYLAND_DISPLAY"] = os.environ.get("WAYLAND_DISPLAY", "")
        return ctx

    def _suggest_resolution(self, error: Exception, component: str) -> str:
        msg = str(error).lower()
        if isinstance(error, FileNotFoundError):
            return f"Install missing {component} dependency"
        if isinstance(error, PermissionError):
            return f"Grant permissions for {component} access (try running with sudo or add user to appropriate group)"
        if "no such file" in msg or "not found" in msg:
            return f"Verify {component} binary path and installation"
        if "connection refused" in msg or "connect" in msg:
            return f"Ensure {component} service is running and accessible"
        if "timeout" in msg:
            return f"Increase timeout or check {component} responsiveness"
        if component == "libvirt" and "auth" in msg:
            return "Configure libvirt authentication (polkit or SASL)"
        if component == "kvm":
            return "Ensure KVM acceleration is available (kvm-ok, /dev/kvm permissions)"
        if component == "xen":
            return "Ensure Xen kernel and toolstack are installed and booted into Xen"
        return f"Check {component} configuration and logs"

    @staticmethod
    def _which(name: str) -> Optional[str]:
        return (
            subprocess.run(["which", name], capture_output=True, text=True).stdout.strip() or None
        )

    @property
    def records(self) -> list[DiagnosticRecord]:
        return list(self._records)

    @property
    def failures(self) -> list[DiagnosticRecord]:
        return [r for r in self._records if not r.success]

    def summary(self) -> str:
        total = len(self._records)
        failed = len(self.failures)
        if total == 0:
            return "No diagnostic records."
        lines = [f"Diagnostics: {total} total, {failed} failed"]
        for r in self.failures:
            lines.append(f"  [{r.component}] {r.operation}: {r.error_type} — {r.error_message}")
            if r.resolution:
                lines.append(f"    -> {r.resolution}")
        return "\n".join(lines)

    def clear(self) -> None:
        self._records.clear()


_root_cause = RootCause()


def get_root_cause() -> RootCause:
    return _root_cause
