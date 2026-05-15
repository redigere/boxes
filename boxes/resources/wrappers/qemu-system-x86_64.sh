#!/bin/sh
exec flatpak-spawn --host podman exec -d boxes-qemu qemu-system-x86_64 "$@"
