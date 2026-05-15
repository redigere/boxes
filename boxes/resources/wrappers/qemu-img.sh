#!/bin/sh
exec flatpak-spawn --host podman exec boxes-qemu qemu-img "$@"
