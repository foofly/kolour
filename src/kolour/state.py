"""Persisted state under ~/.config/kolour/."""
from __future__ import annotations

import os
import time
import tomllib
from pathlib import Path

CONFIG_DIR = Path(os.path.expanduser("~/.config/kolour"))
STATE_FILE = CONFIG_DIR / "state.toml"


def read() -> dict:
    if not STATE_FILE.is_file():
        return {}
    try:
        with STATE_FILE.open("rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def write(*, current: str, accent: str | None) -> None:
    """Update the apply-related keys, preserving everything else (e.g. [auto])."""
    s = read()
    s["current"] = current
    s["applied_at"] = int(time.time())
    if accent is not None:
        s["accent"] = accent
    elif "accent" in s:
        del s["accent"]
    _save(s)


def update_auto(*, dark: str | None = None, light: str | None = None,
                light_after: str | None = None, dark_after: str | None = None) -> dict:
    s = read()
    auto = dict(s.get("auto", {}))
    if dark is not None:
        auto["dark"] = dark
    if light is not None:
        auto["light"] = light
    if light_after is not None:
        auto["light_after"] = light_after
    if dark_after is not None:
        auto["dark_after"] = dark_after
    s["auto"] = auto
    _save(s)
    return auto


def clear_auto() -> None:
    s = read()
    if "auto" in s:
        del s["auto"]
        _save(s)


def _save(state: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    # Top-level keys first, then sections.
    for k, v in state.items():
        if isinstance(v, dict):
            continue
        lines.append(_format_kv(k, v))
    for k, v in state.items():
        if not isinstance(v, dict):
            continue
        lines.append(f"\n[{k}]")
        for sk, sv in v.items():
            lines.append(_format_kv(sk, sv))
    STATE_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format_kv(key: str, value) -> str:
    if isinstance(value, bool):
        return f"{key} = {'true' if value else 'false'}"
    if isinstance(value, (int, float)):
        return f"{key} = {value}"
    return f'{key} = "{value}"'
