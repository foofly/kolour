"""Konsole colour-scheme propagation. No-op when Konsole is absent."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from . import host, state
from .registry import Theme

KONSOLE_DIR = Path(os.path.expanduser("~/.local/share/konsole"))
# Konsole caches profiles by name and won't re-read the file on setProfile to
# the same name. We rotate between two profile names so each apply produces a
# "new" profile from Konsole's perspective.
PROFILE_NAMES = ("KolourA", "KolourB")


def available() -> bool:
    return host.which("konsole") is not None or KONSOLE_DIR.exists()


def _next_profile_name() -> str:
    """Alternate between PROFILE_NAMES on successive applies."""
    last = state.read().get("konsole_profile")
    return PROFILE_NAMES[1] if last == PROFILE_NAMES[0] else PROFILE_NAMES[0]


def apply(theme: Theme, *, dry_run: bool = False) -> list[str]:
    """Returns a list of human-readable actions taken (or planned for dry-run)."""
    if not available():
        return []
    if theme.konsole_path is None or not theme.konsole_path.is_file():
        return []

    actions: list[str] = []
    target = KONSOLE_DIR / theme.konsole_path.name
    if dry_run:
        actions.append(f"would copy {theme.konsole_path} → {target}")
    else:
        KONSOLE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(theme.konsole_path, target)
        actions.append(f"copied {theme.konsole_path.name} to Konsole")

    profile_name = _next_profile_name()
    profile_path = KONSOLE_DIR / f"{profile_name}.profile"
    profile_lines = (
        "[General]\n"
        f"Name={profile_name}\n"
        "Parent=FALLBACK/\n"
        f"\n[Appearance]\nColorScheme={theme.konsole_path.stem}\n"
    )
    if dry_run:
        actions.append(f"would write {profile_path} with ColorScheme={theme.konsole_path.stem}")
    else:
        profile_path.write_text(profile_lines, encoding="utf-8")
        actions.append(f"wrote {profile_path.name}")

    cmd = [
        "kwriteconfig6",
        "--file", "konsolerc",
        "--group", "Desktop Entry",
        "--key", "DefaultProfile",
        profile_path.name,
    ]
    if dry_run:
        actions.append("would run: " + " ".join(cmd))
    else:
        try:
            host.run(cmd, check=True)
            actions.append(f"set Konsole DefaultProfile={profile_path.name}")
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            actions.append(f"WARN: could not set Konsole default profile: {e}")

    if dry_run:
        actions.append("would live-reload running Konsole sessions via D-Bus")
    else:
        actions.extend(reload_running_sessions(profile_name))
        # Persist which profile name we just used so next apply alternates.
        s = state.read()
        s["konsole_profile"] = profile_name
        state._save(s)
    return actions


def _running_konsole_services() -> list[str]:
    try:
        out = host.run(
            ["dbus-send", "--session", "--print-reply",
             "--dest=org.freedesktop.DBus", "/org/freedesktop/DBus",
             "org.freedesktop.DBus.ListNames"],
            capture_output=True, text=True, check=True, timeout=2,
        ).stdout
    except (FileNotFoundError, subprocess.SubprocessError):
        return []
    return re.findall(r'"(org\.kde\.konsole-\d+)"', out)


def _session_paths(service: str) -> list[str]:
    """Introspect /Sessions/ and return /Sessions/<n> for each child node."""
    try:
        out = host.run(
            ["dbus-send", "--session", "--print-reply",
             f"--dest={service}", "/Sessions",
             "org.freedesktop.DBus.Introspectable.Introspect"],
            capture_output=True, text=True, check=True, timeout=2,
        ).stdout
    except (FileNotFoundError, subprocess.SubprocessError):
        return []
    return [f"/Sessions/{n}" for n in re.findall(r'<node name="(\d+)"', out)]


def reload_running_sessions(profile_name: str | None = None) -> list[str]:
    """Switch every running Konsole session to the given profile (or whichever
    we last wrote, per state) so already-open windows pick up the new colours.
    Best-effort — failures on individual sessions don't abort the apply.
    """
    if profile_name is None:
        profile_name = state.read().get("konsole_profile") or PROFILE_NAMES[0]
    actions: list[str] = []
    services = _running_konsole_services()
    if not services:
        return actions
    reloaded = 0
    for svc in services:
        for sess in _session_paths(svc):
            try:
                host.run(
                    ["dbus-send", "--session", "--type=method_call",
                     f"--dest={svc}", sess,
                     "org.kde.konsole.Session.setProfile",
                     f"string:{profile_name}"],
                    check=False, capture_output=True, timeout=1,
                )
                reloaded += 1
            except subprocess.SubprocessError:
                pass
    if reloaded:
        actions.append(f"live-reloaded {reloaded} Konsole session(s) across {len(services)} window(s) → {profile_name}")
    return actions
