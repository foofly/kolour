"""Read/write KDE `.colors` INI files."""
from __future__ import annotations

import configparser
from pathlib import Path

RGB = tuple[int, int, int]
Palette = dict[str, RGB]

SWATCH_KEYS: tuple[tuple[str, str, str], ...] = (
    ("window_bg", "Colors:Window", "BackgroundNormal"),
    ("window_fg", "Colors:Window", "ForegroundNormal"),
    ("view_bg", "Colors:View", "BackgroundNormal"),
    ("view_fg", "Colors:View", "ForegroundNormal"),
    ("button_bg", "Colors:Button", "BackgroundNormal"),
    ("button_fg", "Colors:Button", "ForegroundNormal"),
    ("selection_bg", "Colors:Selection", "BackgroundNormal"),
    ("selection_fg", "Colors:Selection", "ForegroundNormal"),
    ("accent", "Colors:View", "DecorationFocus"),
    ("negative", "Colors:View", "ForegroundNegative"),
    ("positive", "Colors:View", "ForegroundPositive"),
    ("neutral", "Colors:View", "ForegroundNeutral"),
)


def _parser() -> configparser.ConfigParser:
    cp = configparser.ConfigParser(strict=False, interpolation=None)
    cp.optionxform = str  # preserve KDE's case-sensitive keys
    return cp


def _parse_rgb(value: str) -> RGB:
    parts = [int(p.strip()) for p in value.split(",")[:3]]
    if len(parts) != 3:
        raise ValueError(f"expected R,G,B triplet, got: {value!r}")
    return parts[0], parts[1], parts[2]


def load(path: Path) -> configparser.ConfigParser:
    cp = _parser()
    cp.read(path, encoding="utf-8")
    return cp


def palette(path: Path) -> Palette:
    """Pull the swatch-relevant colours out of a `.colors` file."""
    cp = load(path)
    out: Palette = {}
    for label, section, key in SWATCH_KEYS:
        if cp.has_option(section, key):
            try:
                out[label] = _parse_rgb(cp.get(section, key))
            except ValueError:
                continue
    return out


def scheme_name(path: Path) -> str | None:
    """The display Name= from [General] (KDE's source of truth for the scheme name)."""
    cp = load(path)
    return cp.get("General", "Name", fallback=None)


def hex_to_rgb(value: str) -> RGB:
    s = value.lstrip("#")
    if len(s) != 6:
        raise ValueError(f"expected #RRGGBB, got: {value!r}")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def rgb_to_hex(rgb: RGB) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)
