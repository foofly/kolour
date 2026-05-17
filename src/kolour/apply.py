"""Orchestrates a colour-scheme swap across KDE, Konsole, GTK, and state."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from . import gtk as gtk_mod
from . import konsole as konsole_mod
from . import lookandfeel as lnf_mod
from . import registry, state

KDE_SCHEMES_DIR = registry.KDE_SCHEMES_DIR


@dataclass
class ApplyResult:
    name: str
    accent: str | None
    actions: list[str] = field(default_factory=list)
    dry_run: bool = False
    skipped: bool = False  # True when already current


def current_scheme() -> str | None:
    try:
        out = subprocess.run(
            ["kreadconfig6", "--file", "kdeglobals", "--group", "General", "--key", "ColorScheme"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return out or None
    except (FileNotFoundError, subprocess.CalledProcessError):
        s = state.read()
        return s.get("current")


def _ensure_linked(theme: registry.Theme, *, dry_run: bool) -> str | None:
    """Make the bundled .colors discoverable to KDE by placing it in
    ~/.local/share/color-schemes/. System-installed schemes (under /usr/share)
    need no linking — KDE finds them."""
    if not theme.colors_path or str(theme.colors_path).startswith("/usr/share"):
        return None
    target = KDE_SCHEMES_DIR / theme.colors_path.name
    if target.exists() or target.is_symlink():
        return None
    if dry_run:
        return f"would symlink {theme.colors_path} → {target}"
    KDE_SCHEMES_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(theme.colors_path, target)
    except OSError:
        shutil.copyfile(theme.colors_path, target)
    return f"linked scheme into {KDE_SCHEMES_DIR}"


def preview_theme(name: str, *, accent: str | None = None) -> ApplyResult:
    """Visual-only swap: plasma-apply-colorscheme + accent + refresh.

    No Konsole/GTK/Look-and-Feel changes, no state.toml write. Designed to be
    paired with another `preview_theme(prev_name, prev_accent)` call to undo.
    """
    theme = registry.resolve(name)
    result = ApplyResult(name=theme.name, accent=accent)
    linked = _ensure_linked(theme, dry_run=False)
    if linked:
        result.actions.append(linked)

    scheme_cmd = ["plasma-apply-colorscheme", theme.name]
    accent_cmd = ["plasma-apply-colorscheme", "--accent-color", accent] if accent else None
    try:
        subprocess.run(scheme_cmd, check=True, capture_output=True, text=True)
        if accent_cmd:
            subprocess.run(accent_cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise RuntimeError("plasma-apply-colorscheme not found on PATH") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"plasma-apply-colorscheme failed: {e.stderr.strip() or e.stdout.strip() or e}"
        ) from e
    result.actions.append(f"previewed {theme.name}")
    result.actions.extend(_refresh_kde())
    return result


def _refresh_kde() -> list[str]:
    """Best-effort signals to nudge running KDE processes to reload colours."""
    actions: list[str] = []
    # KGlobalSettings palette change (apps with Qt/KDE listeners).
    palette_changed = [
        "dbus-send", "--session", "--type=signal",
        "/KGlobalSettings", "org.kde.KGlobalSettings.notifyChange",
        "int32:0", "int32:0",
    ]
    # KWin reconfigure picks up new window decoration colours.
    kwin_reconfigure = [
        "dbus-send", "--session", "--type=method_call",
        "--dest=org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure",
    ]
    for label, cmd in (("KGlobalSettings palette change", palette_changed),
                       ("KWin reconfigure", kwin_reconfigure)):
        try:
            subprocess.run(cmd, check=False, capture_output=True, timeout=3)
            actions.append(f"notified {label}")
        except (FileNotFoundError, subprocess.SubprocessError):
            pass
    return actions


def apply_theme(
    name: str,
    *,
    accent: str | None = None,
    konsole: bool = True,
    gtk: bool = True,
    lookandfeel: bool = True,
    dry_run: bool = False,
) -> ApplyResult:
    theme = registry.resolve(name)
    result = ApplyResult(name=theme.name, accent=accent, dry_run=dry_run)

    linked = _ensure_linked(theme, dry_run=dry_run)
    if linked:
        result.actions.append(linked)

    if not dry_run and current_scheme() == theme.name and not accent:
        result.skipped = True
        result.actions.append(f"{theme.name} is already current")
        return result

    # plasma-apply-colorscheme treats <name> and --accent-color as mutually
    # exclusive — it only honours one per invocation. Run them separately.
    scheme_cmd = ["plasma-apply-colorscheme", theme.name]
    accent_cmd = ["plasma-apply-colorscheme", "--accent-color", accent] if accent else None
    if dry_run:
        result.actions.append("would run: " + " ".join(scheme_cmd))
        if accent_cmd:
            result.actions.append("would run: " + " ".join(accent_cmd))
    else:
        try:
            subprocess.run(scheme_cmd, check=True, capture_output=True, text=True)
            if accent_cmd:
                subprocess.run(accent_cmd, check=True, capture_output=True, text=True)
            result.actions.append(f"applied {theme.name}" + (f" (accent {accent})" if accent else ""))
        except FileNotFoundError as e:
            raise RuntimeError("plasma-apply-colorscheme not found on PATH") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"plasma-apply-colorscheme failed: {e.stderr.strip() or e.stdout.strip() or e}"
            ) from e

    if konsole:
        result.actions.extend(konsole_mod.apply(theme, dry_run=dry_run))
    if gtk:
        result.actions.extend(gtk_mod.apply(theme, dry_run=dry_run))

    # Look-and-Feel handling. A non-neutral L&F (Ant-Dark, Sweet, etc.) bundles
    # its own Plasma theme and visually overrides the colour scheme — switching
    # it to a Breeze variant lets the colour scheme actually drive the look.
    active_lnf = lnf_mod.current_package()
    if lookandfeel and not lnf_mod.is_neutral(active_lnf):
        target = lnf_mod.pick_for(theme.colors_path)
        result.actions.append(lnf_mod.apply_package(target, dry_run=dry_run))
    elif not lookandfeel and not lnf_mod.is_neutral(active_lnf):
        result.actions.append(
            f"NOTE: kept Look-and-Feel {active_lnf!r}; it may visually override the colour scheme"
        )

    if not dry_run:
        result.actions.extend(_refresh_kde())
        state.write(current=theme.name, accent=accent)

    return result
