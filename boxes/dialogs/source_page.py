from PyQt6.QtWidgets import QWizardPage, QVBoxLayout, QLineEdit, QFormLayout


class SourcePage(QWizardPage):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setTitle("Source")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://example.com/os.iso")
        form.addRow("ISO URL:", self._url_input)
        layout.addLayout(form)
        layout.addStretch()

    @property
    def iso_url(self) -> str:
        return self._url_input.text().strip()
