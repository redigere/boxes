import argparse
import sys
from pathlib import Path

from boxes.core import BoxesCore


def _print_vm(vm: dict) -> None:
    state_color = {"Running": "32", "Paused": "33", "Off": "90", "Sleeping": "34", "Crashed": "91"}
    code = state_color.get(vm["state"], "0")
    print(
        f"  \033[{code}m{vm['state']:>8}\033[0m  {vm['name']:<30}  "
        f"{vm['memory_mb']:>5} MB  {vm['vcpus']} vCPU  {vm['disk_gb']:>3} GB  "
        f"{vm['os_type']:<12}"
    )


def cmd_list(args: argparse.Namespace, core: BoxesCore) -> None:
    vms = core.list_vms()
    if not vms:
        print("No virtual machines configured.")
        return
    print(f"Backend: {core.backend_name}  ({len(vms)} VM(s))")
    print("-" * 90)
    for vm in vms:
        _print_vm(vm)


def cmd_create(args: argparse.Namespace, core: BoxesCore) -> None:
    if core.find_vm(args.name):
        print(f"Error: VM '{args.name}' already exists.", file=sys.stderr)
        sys.exit(1)

    iso = args.iso
    if iso and not Path(iso).exists():
        print(f"Error: ISO file '{iso}' not found.", file=sys.stderr)
        sys.exit(1)

    if args.os:
        from boxes.models.media import InstallerMedia

        media = InstallerMedia(args.iso or "")
        detected = media.os_type
        os_type = args.os if args.os != "auto" else detected
    else:
        os_type = "generic"

    config = core.create_vm(
        name=args.name,
        memory_mb=args.memory,
        vcpus=args.vcpus,
        disk_gb=args.disk,
        iso_path=iso,
        os_type=os_type,
        graphics=args.graphics,
    )
    print(f"VM '{config.name}' created (UUID: {config.uuid})")


def cmd_start(args: argparse.Namespace, core: BoxesCore) -> None:
    ok, msg = core.start_vm(args.name)
    print(msg)
    if not ok:
        sys.exit(1)


def cmd_stop(args: argparse.Namespace, core: BoxesCore) -> None:
    ok, msg = core.stop_vm(args.name)
    print(msg)
    if not ok:
        sys.exit(1)


def cmd_pause(args: argparse.Namespace, core: BoxesCore) -> None:
    ok, msg = core.pause_vm(args.name)
    print(msg)
    if not ok:
        sys.exit(1)


def cmd_resume(args: argparse.Namespace, core: BoxesCore) -> None:
    ok, msg = core.resume_vm(args.name)
    print(msg)
    if not ok:
        sys.exit(1)


def cmd_delete(args: argparse.Namespace, core: BoxesCore) -> None:
    if not args.force:
        vm = core.find_vm(args.name)
        if vm is None:
            print(f"VM '{args.name}' not found.", file=sys.stderr)
            sys.exit(1)
        print(f"Are you sure you want to delete '{vm.name}'? [y/N] ", end="", flush=True)
        confirm = sys.stdin.readline().strip().lower()
        if confirm != "y":
            print("Canceled.")
            return
    ok, msg = core.delete_vm(args.name, keep_disks=args.keep_disks)
    print(msg)
    if not ok:
        sys.exit(1)


def cmd_download(args: argparse.Namespace, core: BoxesCore) -> None:
    from boxes.util import download_iso

    dest = download_iso(args.url, dest_dir=args.dir, filename=args.filename)
    if args.start:
        start_name = args.start
        vm = core.find_vm(start_name)
        if vm is None:
            print(f"Error: VM '{start_name}' not found.")
            return
        iso_path = dest
        vm.iso_path = iso_path
        vm.save()
        print(f"ISO attached to VM '{start_name}' at {iso_path}")


def cmd_diagnose(args: argparse.Namespace, core: BoxesCore) -> None:
    from boxes.diagnostics import get_root_cause

    rc = get_root_cause()
    print(rc.summary())


def cmd_info(args: argparse.Namespace, core: BoxesCore) -> None:
    if args.name:
        vm = core.vm_info(args.name)
        if vm is None:
            print(f"VM '{args.name}' not found.", file=sys.stderr)
            sys.exit(1)
        print(f"Name:       {vm['name']}")
        print(f"UUID:       {vm['uuid']}")
        print(f"State:      {vm['state']}")
        print(f"Backend:    {vm['backend']}")
        print(f"Memory:     {vm['memory_mb']} MB")
        print(f"vCPUs:      {vm['vcpus']}")
        print(f"Disk:       {vm['disk_gb']} GB @ {vm['disk']}")
        print(f"OS Type:    {vm['os_type']}")
        print(f"Arch:       {vm['arch']}")
        print(f"ISO:        {vm['iso']}")
        print(f"Graphics:   {vm['graphics']}")
        if vm.get("display_address") and vm.get("display_port"):
            print(f"Display:    {vm['display_address']}:{vm['display_port']}")
        print(f"CPU Model:  {vm['cpu_model']}")
        print(f"Firmware:   {vm['firmware']}")
        print(f"Network:    {vm['network']}")
        print(f"Autostart:  {vm['autostart']}")
    else:
        bi = core.backend_info()
        print(f"Backend:    {bi['backend']}")
        print(f"Connected:  {bi['connected']}")
        print("Capabilities:")
        for cap in [
            "snapshots",
            "usb_redirection",
            "shared_folders",
            "live_migration",
            "storage_pools",
            "networks",
        ]:
            print(f"  {cap}: {bi[cap]}")
        vms = core.list_vms()
        if vms:
            print(f"\nVMs ({len(vms)}):")
            for vm in vms:
                print(f"  {vm['name']:<30} {vm['state']:>8}  {vm['os_type']}")
        else:
            print("\nNo VMs configured.")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="boxes",
        description="Cross-platform virtual machine manager",
    )
    parser.add_argument("--desktop", action="store_true", help="Launch GUI mode")

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List all VMs")

    p_create = sub.add_parser("create", help="Create a new VM")
    p_create.add_argument("--name", required=True)
    p_create.add_argument("--memory", type=int, default=2048)
    p_create.add_argument("--vcpus", type=int, default=2)
    p_create.add_argument("--disk", type=int, default=20)
    p_create.add_argument("--iso")
    p_create.add_argument("--os", default="auto", help="OS type or 'auto' to detect from ISO")
    p_create.add_argument("--graphics", default="spice", choices=["spice", "vnc"])

    for cmd_name in ("start", "stop", "pause", "resume"):
        p = sub.add_parser(cmd_name, help=f"{cmd_name.capitalize()} a VM")
        p.add_argument("name")

    p_delete = sub.add_parser("delete", help="Delete a VM")
    p_delete.add_argument("name")
    p_delete.add_argument("-f", "--force", action="store_true", help="Skip confirmation")
    p_delete.add_argument(
        "--keep-disks",
        action="store_true",
        default=False,
        help="Preserve disk images on disk (do not delete them)",
    )

    p_dl = sub.add_parser("download", help="Download an ISO image")
    p_dl.add_argument("--url", required=True, help="URL to ISO image")
    p_dl.add_argument("--filename", help="Save as filename (default: from URL)")
    p_dl.add_argument("--dir", help="Destination directory (default: ~/Downloads/boxes)")
    p_dl.add_argument("--start", help="Attach ISO to existing VM by name after download")

    sub.add_parser("diagnose", help="Show diagnostic info and root cause analysis")

    p_info = sub.add_parser("info", help="Show VM or backend info")
    p_info.add_argument("name", nargs="?")

    args = parser.parse_args()

    if args.desktop:
        from boxes.app import gui_main

        return gui_main()

    core = BoxesCore()

    if args.command == "list":
        cmd_list(args, core)
    elif args.command == "create":
        cmd_create(args, core)
    elif args.command == "start":
        cmd_start(args, core)
    elif args.command == "stop":
        cmd_stop(args, core)
    elif args.command == "pause":
        cmd_pause(args, core)
    elif args.command == "resume":
        cmd_resume(args, core)
    elif args.command == "delete":
        cmd_delete(args, core)
    elif args.command == "download":
        cmd_download(args, core)
        return 0
    elif args.command == "diagnose":
        cmd_diagnose(args, core)
    elif args.command == "info":
        cmd_info(args, core)
    else:
        parser.print_help()

    return 0
