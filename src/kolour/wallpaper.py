"""Read the current Plasma wallpaper from plasma-org.kde.plasma.desktop-appletsrc."""
from __future__ import annotations

import os
import re
from pathlib import Path

APPLETSRC = Path(os.path.expanduser("~/.config/plasma-org.kde.plasma.desktop-appletsrc"))

_SECTION_RE = re.compile(
    r"^\[Containments\]\[\d+\]\[Wallpaper\]\[org\.kde\.image\]\[General\]$"
)


def current(appletsrc: Path = APPLETSRC) -> Path | None:
    """First Image= path under any wallpaper section in the appletsrc file."""
    if not appletsrc.is_file():
        return None
    in_section = False
    try:
        for raw in appletsrc.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if line.startswith("["):
                in_section = bool(_SECTION_RE.match(line))
                continue
            if in_section and line.startswith("Image="):
                value = line.split("=", 1)[1].strip()
                if value.startswith("file://"):
                    value = value[len("file://"):]
                value = os.path.expanduser(value)
                p = Path(value)
                return p if p.exists() else p
    except OSError:
        return None
    return None
