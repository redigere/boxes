from boxes.services.download.downloader import DownloadManager as DownloadManager
from boxes.services.download.download_worker import DownloadWorker as DownloadWorker
from boxes.services.snapshot.snapshot import Snapshot as Snapshot
from boxes.services.snapshot.snapshot_manager import SnapshotManager as SnapshotManager
from boxes.services.shared.shared_folder import SharedFolder as SharedFolder
from boxes.services.shared.shared_folders_manager import SharedFoldersManager as SharedFoldersManager
from boxes.services.install.iso_extractor import ISOExtractor as ISOExtractor
from boxes.services.install.unattended import UnattendedInstaller as UnattendedInstaller
from boxes.services.container import PodmanManager as PodmanManager
from boxes.services.spice import (
    SPICEChannel as SPICEChannel,
    SPICEDisplay as SPICEDisplay,
    SPICEInput as SPICEInput,
    SPICEClipboard as SPICEClipboard,
    SPICEFileTransfer as SPICEFileTransfer,
    SPICEVDAgent as SPICEVDAgent,
)
from boxes.services.vnc import VNCClient as VNCClient, VNCServer as VNCServer
from boxes.services.usb import USBDevice as USBDevice, USBRedirection as USBRedirection
from boxes.services.template import TemplateManager as TemplateManager
from boxes.services.export import VMExporter as VMExporter, VMImporter as VMImporter
from boxes.services.migration import MigrationManager as MigrationManager
from boxes.services.virgl import VirglRenderer as VirglRenderer
from boxes.services.benchmark import BenchmarkRunner as BenchmarkRunner
from boxes.services.error_reporting import SentryReporter as SentryReporter
from boxes.services.auth import AuthManager as AuthManager
from boxes.services.firmware import FirmwareManager as FirmwareManager, OVMFManager as OVMFManager
from boxes.services.osinfo import LibosinfoWrapper as LibosinfoWrapper
from boxes.services.vdagent import VDAgentManager as VDAgentManager

__all__ = [
    "DownloadManager", "DownloadWorker",
    "Snapshot", "SnapshotManager",
    "SharedFolder", "SharedFoldersManager",
    "ISOExtractor", "UnattendedInstaller",
    "PodmanManager",
    "SPICEChannel", "SPICEDisplay", "SPICEInput",
    "SPICEClipboard", "SPICEFileTransfer", "SPICEVDAgent",
    "VNCClient", "VNCServer",
    "USBDevice", "USBRedirection",
    "TemplateManager",
    "VMExporter", "VMImporter",
    "MigrationManager",
    "VirglRenderer",
    "BenchmarkRunner",
    "SentryReporter",
    "AuthManager",
    "FirmwareManager", "OVMFManager",
    "LibosinfoWrapper",
    "VDAgentManager",
]
