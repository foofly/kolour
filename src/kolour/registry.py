"""Theme discovery and name resolution."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent
USER_THEMES_DIR = Path(os.path.expanduser("~/.config/kolour/themes"))
KDE_SCHEMES_DIR = Path(os.path.expanduser("~/.local/share/color-schemes"))


@dataclass(frozen=True)
class Theme:
    name: str               # the canonical scheme name (matches [General] Name= and the .colors basename)
    colors_path: Path       # the .colors file
    konsole_path: Path | None = None
    gtk_path: Path | None = None
    family: str | None = None  # e.g. "Catppuccin"

    @property
    def label(self) -> str:
        return self.name.replace("-", " ")


def _bundled_themes_dir() -> Path:
    return PKG_ROOT / "themes"


def _bundled_konsole_dir() -> Path:
    return PKG_ROOT / "konsole"


def _bundled_gtk_dir() -> Path:
    return PKG_ROOT / "gtk"


def _make_theme(colors_path: Path, family: str | None) -> Theme:
    name = colors_path.stem
    konsole = _bundled_konsole_dir() / f"{name}.colorscheme"
    gtk = _bundled_gtk_dir() / f"{name}.css"
    return Theme(
        name=name,
        colors_path=colors_path,
        konsole_path=konsole if konsole.is_file() else None,
        gtk_path=gtk if gtk.is_file() else None,
        family=family,
    )


def all() -> list[Theme]:  # noqa: A001 — the public name is intentional
    """All themes kolour knows about: bundled first, then user dir."""
    themes: dict[str, Theme] = {}
    bundled = _bundled_themes_dir()
    if bundled.is_dir():
        for sub in sorted(bundled.iterdir()):
            if not sub.is_dir():
                continue
            for colors in sorted(sub.glob("*.colors")):
                t = _make_theme(colors, family=sub.name)
                themes[t.name] = t
    if USER_THEMES_DIR.is_dir():
        for colors in sorted(USER_THEMES_DIR.glob("*.colors")):
            t = _make_theme(colors, family=None)
            themes.setdefault(t.name, t)  # bundled wins on conflict
    return list(themes.values())


def system_schemes() -> list[str]:
    """Schemes already in ~/.local/share/color-schemes (incl. system/Breeze copies)."""
    out: list[str] = []
    for d in (KDE_SCHEMES_DIR, Path("/usr/share/color-schemes")):
        if d.is_dir():
            out.extend(sorted(p.stem for p in d.glob("*.colors")))
    # de-dup while preserving order
    seen: set[str] = set()
    return [n for n in out if not (n in seen or seen.add(n))]


def resolve(name: str) -> Theme:
    """Find a bundled/user theme by name. Case- and separator-insensitive.
    Falls back to system-installed schemes (Breeze*, etc.) so any scheme KDE
    knows about is applicable."""
    norm = _normalise(name)
    for t in all():
        if _normalise(t.name) == norm:
            return t
        if t.family:
            for sep in ("/", "-", "_", " "):
                shorthand = f"{t.family}{sep}{t.colors_path.stem}"
                if _normalise(shorthand) == norm:
                    return t

    # Fallback: schemes already installed in the system's colour-scheme dirs.
    for sys_name in system_schemes():
        if _normalise(sys_name) == norm:
            colors_path = _find_system_colors(sys_name)
            return Theme(name=sys_name, colors_path=colors_path)

    raise KeyError(f"unknown theme: {name!r}")


def _find_system_colors(name: str) -> Path:
    for d in (KDE_SCHEMES_DIR, Path("/usr/share/color-schemes")):
        candidate = d / f"{name}.colors"
        if candidate.is_file():
            return candidate
    # last resort — return a path that won't exist so callers get a clear error
    return KDE_SCHEMES_DIR / f"{name}.colors"


def _normalise(s: str) -> str:
    return "".join(ch.lower() for ch in s if ch.isalnum())
