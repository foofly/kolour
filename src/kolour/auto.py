"""Dark/light auto-follow: pair two themes and switch by time of day."""
from __future__ import annotations

import datetime as _dt
import os
import shutil
import subprocess
from pathlib import Path
from typing import Literal

from . import apply as apply_mod
from . import state

DEFAULT_LIGHT_AFTER = "06:00"
DEFAULT_DARK_AFTER = "18:00"

SYSTEMD_USER_DIR = Path(os.path.expanduser("~/.config/systemd/user"))
SERVICE_NAME = "kolour-auto.service"
TIMER_NAME = "kolour-auto.timer"


class AutoNotConfigured(RuntimeError):
    pass


def get() -> dict:
    return dict(state.read().get("auto", {}))


def set_pair(*, dark: str, light: str,
             light_after: str | None = None, dark_after: str | None = None) -> dict:
    return state.update_auto(
        dark=dark, light=light,
        light_after=light_after or DEFAULT_LIGHT_AFTER,
        dark_after=dark_after or DEFAULT_DARK_AFTER,
    )


def clear() -> None:
    state.clear_auto()
    if (SYSTEMD_USER_DIR / TIMER_NAME).exists():
        try:
            disable_timer()
        except Exception:  # noqa: BLE001
            pass


def desired_mode_now(now: _dt.time | None = None) -> Literal["dark", "light"]:
    cfg = get()
    if not cfg or "dark" not in cfg or "light" not in cfg:
        raise AutoNotConfigured("auto pairing not configured; run `kolour auto pair --dark X --light Y`")
    light_after = _parse_time(cfg.get("light_after", DEFAULT_LIGHT_AFTER))
    dark_after = _parse_time(cfg.get("dark_after", DEFAULT_DARK_AFTER))
    t = now or _dt.datetime.now().time()
    # Light from light_after up to dark_after, otherwise dark. This handles the
    # usual 06:00 light → 18:00 dark cycle. If user inverts (e.g. light_after later
    # than dark_after) we still pick the band closest to "now is in light range".
    if dark_after >= light_after:
        return "light" if light_after <= t < dark_after else "dark"
    # inverted (rare)
    return "dark" if dark_after <= t < light_after else "light"


def run(*, force: Literal["dark", "light", None] = None,
        dry_run: bool = False) -> apply_mod.ApplyResult:
    cfg = get()
    if not cfg or "dark" not in cfg or "light" not in cfg:
        raise AutoNotConfigured("auto pairing not configured; run `kolour auto pair --dark X --light Y`")
    mode = force or desired_mode_now()
    target = cfg["dark"] if mode == "dark" else cfg["light"]
    return apply_mod.apply_theme(target, dry_run=dry_run)


def toggle(*, dry_run: bool = False) -> apply_mod.ApplyResult:
    """Flip to the opposite member of the pair regardless of time."""
    cfg = get()
    if not cfg or "dark" not in cfg or "light" not in cfg:
        raise AutoNotConfigured("auto pairing not configured; run `kolour auto pair --dark X --light Y`")
    current = apply_mod.current_scheme()
    if current == cfg["dark"]:
        target = cfg["light"]
    elif current == cfg["light"]:
        target = cfg["dark"]
    else:
        target = cfg["dark"] if desired_mode_now() == "dark" else cfg["light"]
    return apply_mod.apply_theme(target, dry_run=dry_run)


# --- systemd user timer ---------------------------------------------------

def _kolour_binary() -> str:
    return shutil.which("kolour") or "kolour"


def install_timer(*, light_after: str | None = None, dark_after: str | None = None) -> list[str]:
    cfg = set_pair(
        dark=get().get("dark") or "",
        light=get().get("light") or "",
        light_after=light_after,
        dark_after=dark_after,
    ) if (light_after or dark_after) else get()
    if "dark" not in cfg or "light" not in cfg:
        raise AutoNotConfigured("set a pair first: kolour auto pair --dark X --light Y")
    SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)
    service = (
        "[Unit]\n"
        "Description=kolour auto-follow apply\n\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"ExecStart={_kolour_binary()} auto run\n"
    )
    timer = (
        "[Unit]\n"
        "Description=kolour auto-follow schedule\n\n"
        "[Timer]\n"
        f"OnCalendar=*-*-* {cfg.get('light_after', DEFAULT_LIGHT_AFTER)}:00\n"
        f"OnCalendar=*-*-* {cfg.get('dark_after', DEFAULT_DARK_AFTER)}:00\n"
        "Persistent=true\n\n"
        "[Install]\n"
        "WantedBy=timers.target\n"
    )
    (SYSTEMD_USER_DIR / SERVICE_NAME).write_text(service, encoding="utf-8")
    (SYSTEMD_USER_DIR / TIMER_NAME).write_text(timer, encoding="utf-8")
    actions = [f"wrote {SERVICE_NAME}", f"wrote {TIMER_NAME}"]
    actions.extend(_systemctl(["daemon-reload"]))
    actions.extend(_systemctl(["enable", "--now", TIMER_NAME]))
    return actions


def disable_timer() -> list[str]:
    actions: list[str] = []
    actions.extend(_systemctl(["disable", "--now", TIMER_NAME]))
    for f in (SYSTEMD_USER_DIR / SERVICE_NAME, SYSTEMD_USER_DIR / TIMER_NAME):
        if f.exists():
            f.unlink()
            actions.append(f"removed {f.name}")
    actions.extend(_systemctl(["daemon-reload"]))
    return actions


def timer_status() -> str:
    try:
        out = subprocess.run(
            ["systemctl", "--user", "is-active", TIMER_NAME],
            capture_output=True, text=True, check=False,
        )
        return out.stdout.strip() or "unknown"
    except FileNotFoundError:
        return "systemctl not found"


def _systemctl(args: list[str]) -> list[str]:
    try:
        subprocess.run(["systemctl", "--user", *args], check=True, capture_output=True)
        return [f"systemctl --user {' '.join(args)}"]
    except FileNotFoundError:
        return ["WARN: systemctl not on PATH"]
    except subprocess.CalledProcessError as e:
        return [f"WARN: systemctl --user {' '.join(args)} failed: {e.stderr.decode().strip()}"]


def _parse_time(s: str) -> _dt.time:
    h, m = s.split(":", 1)
    return _dt.time(hour=int(h), minute=int(m))
