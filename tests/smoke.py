#!/usr/bin/env python3
"""Stdlib-only smoke tests. Run: python3 tests/smoke.py"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from kolour import apply, auto, colors_io, matugen, registry, wallpaper  # noqa: E402

FAIL: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    status = "ok" if cond else "FAIL"
    print(f"  [{status}] {label}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAIL.append(label)


def section(name: str) -> None:
    print(f"\n== {name} ==")


def main() -> int:
    section("registry")
    themes = registry.all()
    check("at least 13 bundled themes", len(themes) >= 13, f"got {len(themes)}")
    expected = {
        "Nord", "Catppuccin-Latte", "Catppuccin-Frappe",
        "Catppuccin-Macchiato", "Catppuccin-Mocha",
        "Everforest-Dark", "Everforest-Light", "Sweet", "Dracula",
        "Gruvbox-Dark", "Gruvbox-Light", "TokyoNight", "TokyoNight-Storm",
    }
    names = {t.name for t in themes}
    missing = expected - names
    check("all expected themes present", not missing, f"missing {missing}")
    check("all themes have konsole + gtk artefacts",
          all(t.konsole_path and t.gtk_path for t in themes),
          "; ".join(t.name for t in themes if not (t.konsole_path and t.gtk_path)))

    for q, exp in [
        ("Nord", "Nord"), ("nord", "Nord"), ("NORD", "Nord"),
        ("catppuccin/mocha", "Catppuccin-Mocha"),
        ("tokyo night", "TokyoNight"),
        ("gruvbox-dark", "Gruvbox-Dark"),
    ]:
        check(f"resolve({q!r}) == {exp}", registry.resolve(q).name == exp)

    try:
        registry.resolve("definitely-not-a-theme")
        check("unknown theme raises KeyError", False)
    except KeyError:
        check("unknown theme raises KeyError", True)

    section("colors_io")
    nord_palette = colors_io.palette(registry.resolve("Nord").colors_path)
    check("Nord palette parses accent",
          nord_palette.get("accent") == (136, 192, 208),
          f"got {nord_palette.get('accent')}")
    check("hex_to_rgb round-trip",
          colors_io.rgb_to_hex(colors_io.hex_to_rgb("#88c0d0")) == "#88c0d0")
    for theme in themes:
        scheme_name = colors_io.scheme_name(theme.colors_path)
        check(f"{theme.name} Name= matches filename",
              scheme_name == theme.name,
              f"file says {scheme_name!r}")

    section("wallpaper")
    fixture = ROOT / "tests" / "fixtures" / "appletsrc.example"
    parsed = wallpaper.current(fixture)
    check("fixture appletsrc parses",
          parsed == Path("/home/example/Pictures/wall.jpg"),
          f"got {parsed}")
    check("missing file → None",
          wallpaper.current(ROOT / "no-such-file") is None)

    section("matugen")
    # Save originals so we can restore.
    saved_avail = matugen.available
    saved_template = matugen.TEMPLATE
    try:
        matugen.available = lambda: False
        try:
            matugen.generate_and_apply(wallpaper_path=Path("/tmp/x.png"))
            check("missing matugen raises", False)
        except matugen.MatugenMissing:
            check("missing matugen raises", True)

        matugen.available = lambda: True
        # Build a fake template so generate_and_apply gets past the file check.
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            wp = Path(td) / "wp.jpg"
            wp.write_bytes(b"\x89PNG")
            matugen.TEMPLATE = Path(td) / "kde.colors"
            matugen.TEMPLATE.write_text("tmpl")
            result = matugen.generate_and_apply(wallpaper_path=wp, dry_run=True)
            joined = " ".join(result.actions)
            check("dry-run plans matugen image",
                  "matugen image" in joined and "--mode dark" in joined,
                  joined)
    finally:
        matugen.available = saved_avail
        matugen.TEMPLATE = saved_template

    section("auto pairing")
    import datetime as _dt
    # Test desired_mode_now logic with synthetic config (no I/O).
    saved_get = auto.get
    auto.get = lambda: {"dark": "X", "light": "Y", "light_after": "06:00", "dark_after": "18:00"}
    try:
        check("06:00 → light", auto.desired_mode_now(_dt.time(6, 0)) == "light")
        check("12:00 → light", auto.desired_mode_now(_dt.time(12, 0)) == "light")
        check("17:59 → light", auto.desired_mode_now(_dt.time(17, 59)) == "light")
        check("18:00 → dark", auto.desired_mode_now(_dt.time(18, 0)) == "dark")
        check("23:00 → dark", auto.desired_mode_now(_dt.time(23, 0)) == "dark")
        check("05:00 → dark", auto.desired_mode_now(_dt.time(5, 0)) == "dark")
    finally:
        auto.get = saved_get

    section("apply (dry-run)")
    # Run dry-run; the only side effect possible is symlink creation,
    # which the dry-run path skips.
    result = apply.apply_theme("Nord", dry_run=True)
    joined = " ".join(result.actions)
    check("dry-run plans plasma-apply-colorscheme call",
          "plasma-apply-colorscheme Nord" in joined,
          f"actions: {result.actions}")
    check("dry-run does not write state",
          result.dry_run is True)

    print()
    if FAIL:
        print(f"{len(FAIL)} check(s) failed:")
        for f in FAIL:
            print(f"  - {f}")
        return 1
    print(f"all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
