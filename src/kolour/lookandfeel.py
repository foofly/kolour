"""Detect & swap the active Plasma Look-and-Feel package.

L&F packages bundle their own Plasma desktop theme, splash, etc. Some L&Fs
(Breeze, Fedora) are colour-scheme-friendly — they defer to the active
ColorScheme. Others (Ant-Dark, Sweet, etc.) hard-code their look and override
colour-scheme changes visually.
"""
from __future__ import annotations

import configparser
import subprocess
from pathlib import Path

from . import colors_io, host

# L&F packages that respect the active colour scheme. Anything outside this
# set will visually override our scheme until it's switched.
NEUTRAL_PACKAGES = {
    "org.kde.breeze.desktop",
    "org.kde.breezedark.desktop",
    "org.kde.breezetwilight.desktop",
    "org.fedoraproject.fedora.desktop",
    "org.fedoraproject.fedoradark.desktop",
    "org.fedoraproject.fedoralight.desktop",
}

DARK_DEFAULT = "org.kde.breezedark.desktop"
LIGHT_DEFAULT = "org.kde.breeze.desktop"


def current_package() -> str | None:
    try:
        out = host.run(
            ["kreadconfig6", "--file", "kdeglobals", "--group", "KDE",
             "--key", "LookAndFeelPackage"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return out or None
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def is_neutral(pkg: str | None) -> bool:
    if not pkg:
        return True  # no L&F set ≡ Breeze defaults
    return pkg in NEUTRAL_PACKAGES


def is_dark_theme(colors_path: Path) -> bool:
    """Decide dark vs light from the Window background luminance."""
    try:
        cp = configparser.ConfigParser(strict=False, interpolation=None)
        cp.optionxform = str
        cp.read(colors_path, encoding="utf-8")
        bg = cp.get("Colors:Window", "BackgroundNormal", fallback=None)
        if not bg:
            return True
        r, g, b = (int(x) for x in bg.split(",")[:3])
    except (OSError, ValueError, configparser.Error):
        return True
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    return luma < 128


def pick_for(colors_path: Path) -> str:
    return DARK_DEFAULT if is_dark_theme(colors_path) else LIGHT_DEFAULT


def apply_package(pkg: str, *, dry_run: bool = False) -> str:
    cmd = ["plasma-apply-lookandfeel", "--apply", pkg]
    if dry_run:
        return "would run: " + " ".join(cmd)
    try:
        host.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise RuntimeError("plasma-apply-lookandfeel not found on PATH") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"plasma-apply-lookandfeel failed: {e.stderr.strip() or e.stdout.strip() or e}"
        ) from e
    return f"set Look-and-Feel to {pkg}"
