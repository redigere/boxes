from PyQt6.QtWidgets import QWizard


class NewVMAssistant(QWizard):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Virtual Machine")
        self.setMinimumSize(500, 400)
        self._setup_pages()

    def _setup_pages(self) -> None:
        from boxes.dialogs.source_page import SourcePage
        from boxes.dialogs.config_page import ConfigPage
        from boxes.dialogs.summary_page import SummaryPage

        self.source_page = SourcePage()
        self.config_page = ConfigPage()
        self.summary_page = SummaryPage()

        self.addPage(self.source_page)
        self.addPage(self.config_page)
        self.addPage(self.summary_page)

    def get_config(self) -> dict:
        return {
            "iso_url": self.source_page.iso_url,
            "ram_mb": self.config_page.ram_mb,
            "cpus": self.config_page.cpus,
            "disk_gb": self.config_page.disk_gb,
        }
