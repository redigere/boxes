import platform
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication

from boxes.theme_mode import ThemeMode


_LIGHT: dict[str, str] = {
    "bg": "#f8fafc",
    "surface": "#ffffff",
    "surface_alt": "#f1f5f9",
    "border": "#e2e8f0",
    "border_focus": "#a5b4fc",
    "text": "#0f172a",
    "text_secondary": "#334155",
    "text_muted": "#64748b",
    "text_inverse": "#ffffff",
    "accent": "#6366f1",
    "accent_hover": "#4f46e5",
    "accent_muted": "#eef2ff",
    "scrollbar_bg": "#f1f5f9",
    "scrollbar_fg": "#cbd5e1",
    "scrollbar_hover": "#94a3b8",
    "scrollbar_active": "#64748b",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "info": "#3b82f6",
    "tooltip_bg": "#1e293b",
    "tooltip_fg": "#f1f5f9",
    "disabled_bg": "#f1f5f9",
    "disabled_fg": "#94a3b8",
    "disabled_border": "#e2e8f0",
    "highlight": "#eef2ff",
}

_DARK: dict[str, str] = {
    "bg": "#0f172a",
    "surface": "#1e293b",
    "surface_alt": "#0f172a",
    "border": "#334155",
    "border_focus": "#6366f1",
    "text": "#f1f5f9",
    "text_secondary": "#e2e8f0",
    "text_muted": "#94a3b8",
    "text_inverse": "#ffffff",
    "accent": "#6366f1",
    "accent_hover": "#818cf8",
    "accent_muted": "#312e81",
    "scrollbar_bg": "#0f172a",
    "scrollbar_fg": "#475569",
    "scrollbar_hover": "#64748b",
    "scrollbar_active": "#94a3b8",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "info": "#3b82f6",
    "tooltip_bg": "#1e293b",
    "tooltip_fg": "#f1f5f9",
    "disabled_bg": "#1e293b",
    "disabled_fg": "#475569",
    "disabled_border": "#334155",
    "highlight": "#1e1b4b",
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
