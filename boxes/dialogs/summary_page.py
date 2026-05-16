try:
    from PyQt6.QtWidgets import QWizardPage, QVBoxLayout, QLabel
except ImportError:
    QWizardPage = type("QWizardPage", (object,), {})
    QVBoxLayout = type("QVBoxLayout", (object,), {})
    QLabel = type("QLabel", (object,), {})


class SummaryPage(QWizardPage):
	def __init__(self, parent=None) -> None:
		super().__init__(parent)
		self.setTitle("Summary")
		self._summary_label = QLabel()
		self._setup_ui()

	def _setup_ui(self) -> None:
		layout = QVBoxLayout(self)
		self._summary_label.setWordWrap(True)
		layout.addWidget(self._summary_label)
		layout.addStretch()

	def set_summary(self, text: str) -> None:
		self._summary_label.setText(text)

	def initializePage(self) -> None:
		wizard = self.wizard()
		if wizard:
			src = getattr(wizard, "source_page", None)
			cfg = getattr(wizard, "config_page", None)
			lines = []
			if src:
				lines.append(f"ISO URL: {src.iso_url}")
			if cfg:
				lines.append(f"RAM: {cfg.ram_mb} MB")
				lines.append(f"CPUs: {cfg.cpus}")
				lines.append(f"Disk: {cfg.disk_gb} GB")
			self._summary_label.setText("\n".join(lines))
