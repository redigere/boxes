class BackendCapabilities:
    def __init__(self) -> None:
        self.snapshots = False
        self.usb_redirection = False
        self.shared_folders = False
        self.live_migration = False
        self.storage_pools = False
        self.networks = False
