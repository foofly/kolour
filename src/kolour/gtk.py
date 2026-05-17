"""GTK 3 / GTK 4 colour propagation via a managed @import in colors.css."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from .registry import Theme

GTK_DIRS = (
    Path(os.path.expanduser("~/.config/gtk-3.0")),
    Path(os.path.expanduser("~/.config/gtk-4.0")),
)
MANAGED_NAME = "kolour.css"
IMPORT_LINE = '@import url("kolour.css");'
MARKER = "/* kolour: managed import — do not edit this line */"


def apply(theme: Theme, *, dry_run: bool = False) -> list[str]:
    if theme.gtk_path is None or not theme.gtk_path.is_file():
        return []
    actions: list[str] = []
    for gtk_dir in GTK_DIRS:
        managed = gtk_dir / MANAGED_NAME
        colors_css = gtk_dir / "colors.css"
        if dry_run:
            actions.append(f"would write {managed} from {theme.gtk_path.name}")
            actions.append(f"would ensure {colors_css} imports kolour.css")
            continue
        gtk_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(theme.gtk_path, managed)
        _ensure_import(colors_css)
        actions.append(f"updated {managed}")
    return actions


def _ensure_import(colors_css: Path) -> None:
    line = f"{IMPORT_LINE} {MARKER}"
    existing = colors_css.read_text(encoding="utf-8") if colors_css.is_file() else ""
    if MARKER in existing:
        return
    new_content = line + "\n" + existing if existing else line + "\n"
    colors_css.write_text(new_content, encoding="utf-8")


def remove() -> list[str]:
    """Used by `kolour reset` to clean up managed files + import lines."""
    actions: list[str] = []
    for gtk_dir in GTK_DIRS:
        managed = gtk_dir / MANAGED_NAME
        colors_css = gtk_dir / "colors.css"
        if managed.is_file():
            managed.unlink()
            actions.append(f"removed {managed}")
        if colors_css.is_file():
            text = colors_css.read_text(encoding="utf-8")
            cleaned = "\n".join(
                ln for ln in text.splitlines() if MARKER not in ln
            ).strip()
            if cleaned:
                colors_css.write_text(cleaned + "\n", encoding="utf-8")
            else:
                colors_css.unlink()
            actions.append(f"cleaned import from {colors_css}")
    return actions
