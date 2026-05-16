from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QStackedWidget,
    QStatusBar,
    QMessageBox,
)

from boxes import __app_name__
from boxes.models.collection import MachineCollection
from boxes.models.machine import Machine, MachineState
from boxes.ui.collection_view import CollectionView
from boxes.ui.display_view import DisplayWidget
from boxes.ui.topbar import Topbar
from boxes.ui.searchbar import Searchbar
from boxes.ui.toolbar import CollectionToolbar, DisplayToolbar
from boxes.ui.toast import ToastOverlay
from boxes.dialogs.new_vm import NewVMAssistant
from boxes.dialogs.preferences import PreferencesDialog
from boxes.dialogs.about import AboutDialog


class AppWindow(QMainWindow):
    def __init__(self, collection: MachineCollection, backend, parent=None) -> None:
        super().__init__(parent)
        self.collection = collection
        self.backend = backend
        self._current_machine: Optional[Machine] = None
        self._fullscreen = False

        self.setWindowTitle("Boxes")
        self.setMinimumSize(800, 600)
        self.resize(1100, 760)

        self.collection_view = CollectionView()
        self.display_stack = QStackedWidget()
        self.topbar = Topbar()
        self.searchbar = Searchbar()
        self.collection_toolbar = CollectionToolbar()
        self.display_toolbar = DisplayToolbar()
        self.status_bar = QStatusBar()
        self.toast_overlay = ToastOverlay(self)

        self._setup_actions()
        self._setup_ui()
        self._connect_signals()
        self._populate_collection()

    def _setup_actions(self) -> None:
        menu = self.menuBar()
        if menu is None:
            return
        file_menu = menu.addMenu("&File")
        if file_menu:
            act_new = QAction("New VM...", self)
            act_new.setShortcut(QKeySequence("Ctrl+N"))
            act_new.triggered.connect(self._on_new_vm)
            file_menu.addAction(act_new)
            file_menu.addSeparator()
            act_quit = QAction("Quit", self)
            act_quit.setShortcut(QKeySequence("Ctrl+Q"))
            act_quit.triggered.connect(self.close)
            file_menu.addAction(act_quit)

        vm_menu = menu.addMenu("&Virtual Machine")
        if vm_menu:
            vm_menu.addAction("Start", self._on_start)
            vm_menu.addAction("Shutdown", self._on_shutdown)
            vm_menu.addAction("Pause", self._on_pause)
            vm_menu.addAction("Resume", self._on_resume)
            vm_menu.addSeparator()
            vm_menu.addAction("Preferences...", self._on_preferences)
            vm_menu.addAction("Delete...", self._on_delete)

        view_menu = menu.addMenu("&View")
        if view_menu:
            view_menu.addAction("Icon View", lambda: self.collection_view.set_icon_mode())
            view_menu.addAction("List View", lambda: self.collection_view.set_list_mode())
            view_menu.addSeparator()
            act_fs = QAction("Fullscreen", self)
            act_fs.setShortcut(QKeySequence("F11"))
            act_fs.triggered.connect(self._toggle_fullscreen)
            view_menu.addAction(act_fs)

        help_menu = menu.addMenu("&Help")
        if help_menu:
            help_menu.addAction("About Boxes", self._on_about)

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.topbar)
        layout.addWidget(self.searchbar)
        layout.addWidget(self.collection_toolbar)
        layout.addWidget(self.collection_view)
        layout.addWidget(self.display_toolbar)
        layout.addWidget(self.display_stack)
        layout.addWidget(self.status_bar)

        self.display_toolbar.hide()
        self.display_stack.hide()
        self.status_bar.showMessage("Ready")

    def _connect_signals(self) -> None:
        self.collection_view.doubleClicked.connect(self._on_machine_activated)
        self.topbar.back_requested.connect(self._show_collection)
        self.topbar.power_toggled.connect(self._on_power_toggle)
        self.topbar.pause_toggled.connect(self._on_pause_toggle)
        self.topbar.settings_requested.connect(self._on_preferences)
        self.searchbar.text_changed.connect(self._filter_collection)
        self.collection_toolbar.createRequested.connect(self._on_new_vm)
        self.display_toolbar.backRequested.connect(self._show_collection)
        self.display_toolbar.fullscreenRequested.connect(self._on_fullscreen)
        self.display_toolbar.screenshotRequested.connect(self._on_screenshot)

    def _populate_collection(self) -> None:
        self.collection_view.setModel(self.collection)

    def _on_machine_activated(self, index) -> None:
        machine = self.collection.get(index.row())
        if machine is None:
            return
        self._current_machine = machine
        self._show_display(machine)

    def _show_display(self, machine: Machine) -> None:
        self.collection_view.hide()
        self.collection_toolbar.hide()
        self.searchbar.hide()

        self.display_stack.show()
        self.display_toolbar.show()
        self.topbar.show_machine_controls(machine)

        while self.display_stack.count():
            w = self.display_stack.widget(0)
            self.display_stack.removeWidget(w)
            if w is not None:
                w.deleteLater()

        display = DisplayWidget(machine, backend=self.backend)
        self.display_stack.addWidget(display)
        self.display_stack.setCurrentWidget(display)
        self.setWindowTitle(f"{machine.name} — {__app_name__}")

        self.status_bar.showMessage(f"{machine.name} — {machine.status_text}")

    def _show_collection(self) -> None:
        self._current_machine = None
        self.collection_view.show()
        self.collection_toolbar.show()

        self.display_stack.hide()
        self.display_toolbar.hide()
        self.topbar.collection_mode()
        self.setWindowTitle(__app_name__)
        self.status_bar.showMessage("Ready")

        if self._fullscreen:
            self._toggle_fullscreen()

    def _on_power_toggle(self) -> None:
        if not self._current_machine:
            return
        if self._current_machine.state == MachineState.RUNNING:
            self._on_shutdown()
        else:
            self._on_start()

    def _on_pause_toggle(self) -> None:
        if not self._current_machine:
            return
        if self._current_machine.state == MachineState.PAUSED:
            self._on_resume()
        else:
            self._on_pause()

    def _on_start(self) -> None:
        if not self._current_machine:
            return
        machine = self._current_machine
        machine.backend_id = machine.backend_id or machine.config.uuid
        if self.backend.start_machine(machine.backend_id):
            machine.state = MachineState.RUNNING
            self.status_bar.showMessage(f"{machine.name} started")
            self.topbar._update_power_button(machine)
        else:
            self.status_bar.showMessage(f"Failed to start {machine.name}")

    def _on_shutdown(self) -> None:
        if not self._current_machine:
            return
        machine = self._current_machine
        if machine.backend_id and self.backend.shutdown_machine(machine.backend_id):
            machine.state = MachineState.STOPPED
            self.status_bar.showMessage(f"{machine.name} stopped")
            self.topbar._update_power_button(machine)
        else:
            self.status_bar.showMessage(f"Failed to stop {machine.name}")

    def _on_pause(self) -> None:
        if not self._current_machine:
            return
        machine = self._current_machine
        if machine.backend_id and self.backend.pause_machine(machine.backend_id):
            machine.state = MachineState.PAUSED
            self.status_bar.showMessage(f"{machine.name} paused")
            self.topbar._update_power_button(machine)

    def _on_resume(self) -> None:
        if not self._current_machine:
            return
        machine = self._current_machine
        if machine.backend_id and self.backend.resume_machine(machine.backend_id):
            machine.state = MachineState.RUNNING
            self.status_bar.showMessage(f"{machine.name} resumed")
            self.topbar._update_power_button(machine)

    def _on_delete(self) -> None:
        if not self._current_machine:
            return
        machine = self._current_machine
        reply = QMessageBox.question(
            self,
            "Delete VM",
            f"Delete '{machine.name}' and all its storage?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if machine.backend_id:
                self.backend.delete_machine(machine.backend_id)
            machine.config.delete()
            self.collection.remove(machine)
            self._show_collection()
            self.status_bar.showMessage(f"{machine.name} deleted")

    def _on_new_vm(self) -> None:
        dlg = NewVMAssistant(self.collection, self.backend, self)
        dlg.exec()

    def _on_preferences(self) -> None:
        if not self._current_machine:
            return
        dlg = PreferencesDialog(self._current_machine, self)
        dlg.exec()

    def _on_about(self) -> None:
        dlg = AboutDialog(self)
        dlg.exec()

    def _filter_collection(self, text: str) -> None:
        for i in range(self.collection.rowCount()):
            idx = self.collection.index(i)
            name = self.collection.data(idx, Qt.ItemDataRole.DisplayRole) or ""
            visible = text.lower() in name.lower()
            self.collection_view.setRowHidden(i, not visible)

    def _switch_view(self, view: str) -> None:
        if view == "icon":
            self.collection_view.set_icon_mode()
        else:
            self.collection_view.set_list_mode()

    def _on_fullscreen(self) -> None:
        self._toggle_fullscreen()

    def _on_screenshot(self) -> None:
        if self._current_machine:
            self.status_bar.showMessage(f"Screenshot of {self._current_machine.name}")

    def _toggle_fullscreen(self, checked: Optional[bool] = None) -> None:
        if checked is not None:
            self._fullscreen = checked
        else:
            self._fullscreen = not self._fullscreen
        if self._fullscreen:
            self.showFullScreen()
        else:
            self.showNormal()

    def closeEvent(self, event) -> None:
        self.backend.disconnect()
        event.accept()
