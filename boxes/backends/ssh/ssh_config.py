from dataclasses import dataclass


@dataclass
class SSHConfig:
    host: str
    port: int = 22
    username: str = "root"
    key_file: str = ""
    timeout: int = 10

    @property
    def host_string(self) -> str:
        if self.port != 22:
            return f"{self.host}:{self.port}"
        return self.host

    def to_ssh_args(self) -> list[str]:
        args = [
            "-p",
            str(self.port),
            "-o",
            f"ConnectTimeout={self.timeout}",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
        ]
        if self.key_file:
            args.extend(["-i", self.key_file])
        args.append(f"{self.username}@{self.host}")
        return args
