from typing import Optional
import os
import struct
import fcntl


KVM_API_VERSION = 12
KVM_GET_API_VERSION = 0xAE00
KVM_CREATE_VM = 0x4020AE01
KVM_CHECK_EXTENSION = 0xAE03
KVM_CREATE_VCPU = 0x4020AE41
KVM_SET_USER_MEMORY_REGION = 0x4020AE46
KVM_RUN = 0xAE80
KVM_GET_VCPU_MMAP_SIZE = 0xAE04
KVM_SET_TSS_ADDR = 0xAE47
KVM_CREATE_IRQCHIP = 0xAE60
KVM_CAP_MAX_VCPUS = 66
KVM_CAP_USER_MEMORY = 5


class KVMDevice:
    def __init__(self) -> None:
        self._kvm_fd: Optional[int] = None
        self._vm_fd: Optional[int] = None
        self._vcpu_fd: Optional[int] = None
        self._vcpu_mmap_size: int = 0

    def probe(self) -> bool:
        from pathlib import Path

        return Path("/dev/kvm").exists()

    def open(self) -> bool:
        try:
            fd = os.open("/dev/kvm", os.O_RDWR | os.O_CLOEXEC)
        except (OSError, PermissionError):
            return False
        try:
            version = fcntl.ioctl(fd, KVM_GET_API_VERSION, 0)
            if version != KVM_API_VERSION:
                os.close(fd)
                return False
            self._kvm_fd = fd
            return True
        except OSError:
            os.close(fd)
            return False

    def close(self) -> None:
        for fd in (self._vcpu_fd, self._vm_fd, self._kvm_fd):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
        self._kvm_fd = None
        self._vm_fd = None
        self._vcpu_fd = None

    @property
    def is_open(self) -> bool:
        return self._kvm_fd is not None

    def create_vm(self) -> Optional[int]:
        if self._kvm_fd is None:
            return None
        try:
            vm_fd = fcntl.ioctl(self._kvm_fd, KVM_CREATE_VM, 0)
            self._vm_fd = vm_fd
            return vm_fd
        except OSError:
            return None

    def create_vcpu(self, vm_fd: int, vcpu_id: int = 0) -> Optional[int]:
        try:
            vcpu_fd = fcntl.ioctl(vm_fd, KVM_CREATE_VCPU, vcpu_id)
            self._vcpu_fd = vcpu_fd
            if self._vcpu_mmap_size == 0 and self._kvm_fd is not None:
                self._vcpu_mmap_size = fcntl.ioctl(
                    self._kvm_fd, KVM_GET_VCPU_MMAP_SIZE, 0
                )
            return vcpu_fd
        except OSError:
            return None

    def set_user_memory_region(
        self,
        vm_fd: int,
        guest_paddr: int,
        mem_size: int,
        host_addr: int,
        slot: int = 0,
    ) -> bool:
        region = struct.pack("IIQII", slot, guest_paddr >> 16, host_addr, mem_size, 0)
        try:
            fcntl.ioctl(vm_fd, KVM_SET_USER_MEMORY_REGION, region)
            return True
        except OSError:
            return False

    def check_capability(self, cap: int) -> bool:
        if self._kvm_fd is None:
            return False
        try:
            return fcntl.ioctl(self._kvm_fd, KVM_CHECK_EXTENSION, cap) > 0
        except OSError:
            return False
