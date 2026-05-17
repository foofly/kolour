"""A row of true-colour cells, one per palette entry."""
from __future__ import annotations

from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

from ..colors_io import Palette, rgb_to_hex

_KEY_ORDER: tuple[str, ...] = (
    "window_bg", "view_bg", "button_bg", "selection_bg",
    "window_fg", "view_fg", "button_fg", "selection_fg",
    "accent", "positive", "negative", "neutral",
)


class Swatch(Widget):
    DEFAULT_CSS = """
    Swatch {
        height: 1;
        width: auto;
    }
    """

    palette: reactive[Palette] = reactive({}, layout=True)

    def render(self) -> Text:
        if not self.palette:
            return Text("(no palette)", style="dim")
        text = Text()
        for key in _KEY_ORDER:
            rgb = self.palette.get(key)
            if rgb is None:
                continue
            text.append("      ", style=f"on {rgb_to_hex(rgb)}")
            text.append(" ")
        return text
