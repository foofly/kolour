"""Material You theme generation via `matugen`."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from . import apply as apply_mod
from . import host, registry, wallpaper

TEMPLATE = registry.PKG_ROOT / "matugen-templates" / "kde.colors"
OUTPUT_NAME = "MaterialYou.colors"


class MatugenMissing(RuntimeError):
    pass


class WallpaperMissing(RuntimeError):
    pass


def available() -> bool:
    return host.which("matugen") is not None


def _write_matugen_config(output_path: Path) -> Path:
    """Build a tiny matugen config that registers our KDE template."""
    config = (
        '[config]\n'
        '\n'
        '[templates.kde]\n'
        f'input_path = "{TEMPLATE}"\n'
        f'output_path = "{output_path}"\n'
    )
    tmp = Path(tempfile.mkstemp(prefix="kolour-matugen-", suffix=".toml")[1])
    tmp.write_text(config, encoding="utf-8")
    return tmp


def generate_and_apply(
    *,
    wallpaper_path: Path | None = None,
    mode: str = "dark",
    dry_run: bool = False,
) -> apply_mod.ApplyResult:
    if not available():
        raise MatugenMissing(
            "matugen not found on PATH. Install with: cargo install matugen "
            "(or your distro's package)."
        )
    if wallpaper_path is None:
        wallpaper_path = wallpaper.current()
    if wallpaper_path is None or not Path(wallpaper_path).is_file():
        raise WallpaperMissing(
            "could not determine current wallpaper; pass --wallpaper PATH"
        )
    if not TEMPLATE.is_file():
        raise FileNotFoundError(f"matugen template missing at {TEMPLATE}")

    output = registry.KDE_SCHEMES_DIR / OUTPUT_NAME
    registry.KDE_SCHEMES_DIR.mkdir(parents=True, exist_ok=True)
    config_path = _write_matugen_config(output)
    cmd = [
        "matugen", "image", str(wallpaper_path),
        "--mode", mode,
        "--config", str(config_path),
        "--json", "hex",
    ]
    if dry_run:
        result = apply_mod.ApplyResult(name="MaterialYou", accent=None, dry_run=True)
        result.actions.append("would run: " + " ".join(cmd))
        result.actions.append(f"would apply MaterialYou (output: {output})")
        return result
    try:
        proc = host.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"matugen failed: {e.stderr.strip() or e.stdout.strip() or e}"
        ) from e
    finally:
        try:
            os.unlink(config_path)
        except OSError:
            pass

    # matugen prints colour roles as JSON; we don't need them here, but parse for sanity.
    try:
        json.loads(proc.stdout)
    except (ValueError, json.JSONDecodeError):
        pass

    if not output.is_file():
        raise RuntimeError(f"matugen ran but did not produce {output}")

    return apply_mod.apply_theme("MaterialYou")
