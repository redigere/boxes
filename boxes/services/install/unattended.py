from pathlib import Path


class UnattendedInstaller:
    def __init__(self) -> None:
        self.template_dir = Path(__file__).parent.parent / "resources" / "templates"

    def generate_kickstart(self, name: str, password: str = "boxes") -> str:
        return (
            f"# Kickstart for {name}\n"
            "install\n"
            "text\n"
            "lang en_US.UTF-8\n"
            "keyboard us\n"
            f"rootpw --plaintext {password}\n"
            "timezone UTC\n"
            "bootloader --location=mbr\n"
            "clearpart --all --initlabel\n"
            "autopart\n"
            "reboot\n"
            "network --bootproto=dhcp\n"
            "%packages\n"
            "@core\n"
            "%end\n"
        )

    def generate_preseed(self, name: str, password: str = "boxes") -> str:
        return (
            f"d-i debian-installer/locale string en_US\n"
            f"d-i keyboard-configuration/xkb-keymap select us\n"
            f"d-i netcfg/choose_interface select auto\n"
            f"d-i netcfg/get_hostname string {name}\n"
            f"d-i passwd/root-password password {password}\n"
            f"d-i passwd/root-password-again password {password}\n"
            f"d-i clock-setup/utc boolean true\n"
            f"d-i partman-auto/method string regular\n"
            f"d-i partman-partitioning/confirm_write_new_label boolean true\n"
            f"d-i partman/confirm boolean true\n"
            f"d-i partman/confirm_nooverwrite boolean true\n"
            f"d-i grub-installer/only_debian boolean true\n"
            f"d-i finish-install/reboot_in_progress note\n"
        )

    def generate_autounattend(self, name: str) -> str:
        return (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<unattend xmlns="urn:schemas-microsoft-com:unattend">\n'
            '  <settings pass="windowsPE">\n'
            '    <component name="Microsoft-Windows-Setup" processorArchitecture="amd64">\n'
            "      <UserData>\n"
            "        <AcceptEula>true</AcceptEula>\n"
            f"        <FullName>{name}</FullName>\n"
            "        <Organization>Boxes</Organization>\n"
            "      </UserData>\n"
            "    </component>\n"
            "  </settings>\n"
            "</unattend>\n"
        )
