from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QDialogButtonBox


class PreferencesDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setMinimumSize(450, 350)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        self._tabs = QTabWidget()
        from boxes.dialogs.resources_tab import ResourcesTab
        from boxes.dialogs.storage_tab import StorageTab
        from boxes.dialogs.network_tab import NetworkTab
        from boxes.dialogs.display_tab import DisplayTab

        self._resources_tab = ResourcesTab()
        self._storage_tab = StorageTab()
        self._network_tab = NetworkTab()
        self._display_tab = DisplayTab()

        self._tabs.addTab(self._resources_tab, "Resources")
        self._tabs.addTab(self._storage_tab, "Storage")
        self._tabs.addTab(self._network_tab, "Network")
        self._tabs.addTab(self._display_tab, "Display")
        layout.addWidget(self._tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def resources_tab(self):
        return self._resources_tab

    @property
    def storage_tab(self):
        return self._storage_tab

    @property
    def network_tab(self):
        return self._network_tab

    @property
    def display_tab(self):
        return self._display_tab
