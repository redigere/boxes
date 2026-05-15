import platform
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication

from boxes.theme_mode import ThemeMode


_LIGHT: dict[str, str] = {
    "bg": "#f6f5f4",
    "surface": "#ffffff",
    "surface_alt": "#f6f5f4",
    "border": "#deddda",
    "border_focus": "#2ec27e",
    "text": "#1a1a1a",
    "text_secondary": "#5e5c64",
    "text_muted": "#9a9a9a",
    "text_inverse": "#ffffff",
    "accent": "#2ec27e",
    "accent_hover": "#26a16b",
    "accent_muted": "#e8f8f1",
    "scrollbar_bg": "#f6f5f4",
    "scrollbar_fg": "#c0bfbc",
    "scrollbar_hover": "#9a9a9a",
    "scrollbar_active": "#5e5c64",
    "success": "#2ec27e",
    "warning": "#ff7800",
    "error": "#e63d3d",
    "info": "#3584e4",
    "tooltip_bg": "#333333",
    "tooltip_fg": "#ffffff",
    "disabled_bg": "#f6f5f4",
    "disabled_fg": "#9a9a9a",
    "disabled_border": "#deddda",
    "highlight": "#e8f8f1",
}

_DARK: dict[str, str] = {
    "bg": "#1e1e1e",
    "surface": "#333333",
    "surface_alt": "#1e1e1e",
    "border": "#5e5c64",
    "border_focus": "#2ec27e",
    "text": "#ffffff",
    "text_secondary": "#deddda",
    "text_muted": "#9a9a9a",
    "text_inverse": "#ffffff",
    "accent": "#2ec27e",
    "accent_hover": "#57d99a",
    "accent_muted": "#1a3b2e",
    "scrollbar_bg": "#1e1e1e",
    "scrollbar_fg": "#5e5c64",
    "scrollbar_hover": "#9a9a9a",
    "scrollbar_active": "#c0bfbc",
    "success": "#2ec27e",
    "warning": "#ff7800",
    "error": "#e63d3d",
    "info": "#3584e4",
    "tooltip_bg": "#333333",
    "tooltip_fg": "#ffffff",
    "disabled_bg": "#1e1e1e",
    "disabled_fg": "#5e5c64",
    "disabled_border": "#333333",
    "highlight": "#1a3b2e",
}


_STYLE_TEMPLATE_PATH = Path(__file__).parent / "resources" / "style.qss"


class ThemeManager(QObject):
    _instance: Optional["ThemeManager"] = None

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self._app = app
        self._mode = self._detect_mode()
        self._colors: dict[str, str] = dict(self._get_palette())
        self._platform = platform.system().lower()

        self.apply()

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_theme)
        self._poll_timer.start(5000)

        if hasattr(app, "paletteChanged"):
            app.paletteChanged.connect(self._on_palette_changed)

        ThemeManager._instance = self

    @classmethod
    def instance(cls) -> Optional["ThemeManager"]:
        return cls._instance

    @classmethod
    def color(cls, name: str, default: str = "") -> str:
        inst = cls._instance
        if inst is not None:
            return inst._colors.get(name, default)
        return default

    @property
    def mode(self) -> ThemeMode:
        return self._mode

    @property
    def colors(self) -> dict[str, str]:
        return dict(self._colors)

    def _detect_mode(self) -> ThemeMode:
        hints = self._app.styleHints()
        if hints is not None and hasattr(hints, "colorScheme"):
            try:
                scheme = hints.colorScheme()
                if scheme is not None and "dark" in str(scheme).lower():
                    return ThemeMode.DARK
            except Exception:
                pass

        palette = self._app.palette()
        if palette is not None:
            window_color = palette.color(QPalette.ColorRole.Window)
            if window_color is not None and window_color.lightness() < 128:
                return ThemeMode.DARK

        return ThemeMode.LIGHT

    def _get_palette(self) -> dict[str, str]:
        return _DARK if self._mode == ThemeMode.DARK else _LIGHT

    def _generate_qss(self) -> str:
        qss = _STYLE_TEMPLATE_PATH.read_text(encoding="utf-8")
        for key, val in self._colors.items():
            qss = qss.replace(f"@{key}@", val)
        return qss

    def apply(self) -> None:
        stylesheet = self._generate_qss()
        self._app.setStyleSheet(stylesheet)

    def _poll_theme(self) -> None:
        new = self._detect_mode()
        if new != self._mode:
            self._mode = new
            self._colors = dict(self._get_palette())
            self.apply()

    def _on_palette_changed(self, _palette: QPalette) -> None:
        new = self._detect_mode()
        if new != self._mode:
            self._mode = new
            self._colors = dict(self._get_palette())
            self.apply()
