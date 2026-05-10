"""Reusable colour-swatch widget."""
from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ..colors_io import Palette


class SwatchWidget(QWidget):
    """Paints a row of rounded chips for a palette dict."""

    KEYS_LARGE = (
        "window_bg", "view_bg", "button_bg",
        "window_fg", "selection_bg", "accent",
        "positive", "negative", "neutral",
    )
    KEYS_SMALL = ("window_bg", "view_bg", "selection_bg", "accent")

    def __init__(self, parent: QWidget | None = None, *, compact: bool = False) -> None:
        super().__init__(parent)
        self._palette: Palette = {}
        self._compact = compact
        self.setMinimumHeight(18 if compact else 56)

    def set_palette(self, palette: Palette) -> None:
        self._palette = palette
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(180 if self._compact else 360, 18 if self._compact else 56)

    def paintEvent(self, event) -> None:  # noqa: N802 — Qt API
        if not self._palette:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        keys = [k for k in (self.KEYS_SMALL if self._compact else self.KEYS_LARGE) if k in self._palette]
        if not keys:
            return
        n = len(keys)
        gap = 2 if self._compact else 6
        radius = 3 if self._compact else 6
        w = (self.width() - gap * (n - 1)) / n
        h = self.height()
        x = 0.0
        pen = QPen(QColor(0, 0, 0, 60))
        pen.setWidth(1)
        p.setPen(pen)
        for k in keys:
            r, g, b = self._palette[k]
            p.setBrush(QColor(r, g, b))
            p.drawRoundedRect(QRectF(x, 0, w, h), radius, radius)
            x += w + gap
        p.end()
