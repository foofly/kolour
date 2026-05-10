"""Subprocess wrapper that escapes a Flatpak sandbox via flatpak-spawn --host.

kolour's whole job is calling host KDE binaries (plasma-apply-colorscheme,
kreadconfig6, dbus-send, systemctl --user, etc.) — none of which exist inside
a typical Flatpak runtime. When packaged as a Flatpak we route every host
command through `flatpak-spawn --host`. Outside Flatpak this module is a thin
passthrough to subprocess.
"""
from __future__ import annotations

import os
import shutil
import subprocess

IN_FLATPAK = os.path.exists("/.flatpak-info") or "FLATPAK_ID" in os.environ


def host_cmd(args: list[str]) -> list[str]:
    if IN_FLATPAK:
        return ["flatpak-spawn", "--host", *args]
    return list(args)


def run(args: list[str], **kwargs):
    """subprocess.run replacement that targets the host when sandboxed."""
    return subprocess.run(host_cmd(args), **kwargs)


def which(name: str) -> str | None:
    """Resolve a binary on the host (if sandboxed) or in the local env."""
    if not IN_FLATPAK:
        return shutil.which(name)
    try:
        result = subprocess.run(
            host_cmd(["which", name]),
            capture_output=True, text=True, check=False, timeout=2,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    path = result.stdout.strip()
    return path if result.returncode == 0 and path else None
