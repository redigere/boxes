def test_import_boxes() -> None:
	import boxes

	assert boxes.__version__ == "1.0.0"
	assert boxes.__app_id__ == "io.boxes.Boxes"
	assert boxes.__app_name__ == "Boxes"


def test_import_models() -> None:
	from boxes.models.machine import MachineState

	assert MachineState.STOPPED == 0
	assert MachineState.RUNNING == 1
	assert MachineState.PAUSED == 2
	assert MachineState.SLEEPING == 3
	assert MachineState.CRASHED == 4


def test_import_backends() -> None:
	from boxes.backends import BaseBackend

	assert BaseBackend is not None


def test_import_ui() -> None:
	from boxes.ui.collection_view import CollectionView

	assert CollectionView is not None


def test_import_dialogs() -> None:
	from boxes.dialogs.new_vm import NewVMAssistant

	assert NewVMAssistant is not None


def test_import_services() -> None:
	from boxes.services.downloader import DownloadWorker

	assert DownloadWorker is not None


def test_import_constants() -> None:
	from boxes.constants import (
		APP_NAME,
		APP_ID,
		APP_VERSION,
	)

	assert APP_NAME == "Boxes"
	assert APP_ID == "io.boxes.Boxes"
	assert APP_VERSION == "1.0.0"


def test_import_util() -> None:
	from boxes.util import (
		find_qemu_binary,
	)

	assert find_qemu_binary is not None
