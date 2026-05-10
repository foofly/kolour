#!/usr/bin/env python3
"""Dev-only generator: YAML palette → .colors + .colorscheme + .css.

Reads tools/palettes/*.yaml and writes:
  themes/<family>/<name>.colors
  konsole/<name>.colorscheme
  gtk/<name>.css

Run: python3 tools/generate-colors.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install --user PyYAML")

ROOT = Path(__file__).resolve().parent.parent
PALETTES_DIR = ROOT / "tools" / "palettes"
PKG_DIR = ROOT / "src" / "kolour"
THEMES_DIR = PKG_DIR / "themes"
KONSOLE_DIR = PKG_DIR / "konsole"
GTK_DIR = PKG_DIR / "gtk"


def hex_to_rgb(s: str) -> tuple[int, int, int]:
    s = s.lstrip("#")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def rgb(value: str) -> str:
    r, g, b = hex_to_rgb(value)
    return f"{r},{g},{b}"


# Static effect blocks lifted verbatim from /usr/share/color-schemes/BreezeDark.colors —
# these tune disabled/inactive state and are scheme-agnostic.
EFFECTS = dedent(
    """
    [ColorEffects:Disabled]
    Color=56,56,56
    ColorAmount=0
    ColorEffect=0
    ContrastAmount=0.65
    ContrastEffect=1
    IntensityAmount=0.1
    IntensityEffect=2

    [ColorEffects:Inactive]
    ChangeSelectionColor=true
    Color=112,111,110
    ColorAmount=0.025
    ColorEffect=2
    ContrastAmount=0.1
    ContrastEffect=2
    Enable=false
    IntensityAmount=0
    IntensityEffect=0
    """
).strip()


def build_colors_file(name: str, p: dict) -> str:
    """Produce a complete KDE .colors file from a flat palette dict."""
    bg = p["bg"]
    bg_alt = p.get("bg_alt", bg)
    view_bg = p.get("view_bg", bg)
    view_alt = p.get("view_alt", bg_alt)
    button_bg = p.get("button_bg", bg_alt)
    button_alt = p.get("button_alt", bg_alt)
    tooltip_bg = p.get("tooltip_bg", bg_alt)
    tooltip_fg = p.get("tooltip_fg", p["fg"])
    fg = p["fg"]
    fg_dim = p.get("fg_dim", fg)
    accent = p["accent"]
    selection_bg = p.get("selection_bg", accent)
    selection_fg = p.get("selection_fg", bg)
    link = p.get("link", accent)
    visited = p.get("visited", p.get("link", accent))
    positive = p["positive"]
    neutral = p["neutral"]
    negative = p["negative"]

    def block(section: str, *, bg_n: str, bg_a: str, fg_n: str = fg) -> str:
        return dedent(f"""
        [{section}]
        BackgroundAlternate={rgb(bg_a)}
        BackgroundNormal={rgb(bg_n)}
        DecorationFocus={rgb(accent)}
        DecorationHover={rgb(accent)}
        ForegroundActive={rgb(accent)}
        ForegroundInactive={rgb(fg_dim)}
        ForegroundLink={rgb(link)}
        ForegroundNegative={rgb(negative)}
        ForegroundNeutral={rgb(neutral)}
        ForegroundNormal={rgb(fg_n)}
        ForegroundPositive={rgb(positive)}
        ForegroundVisited={rgb(visited)}
        """).strip()

    parts = [
        f"[General]\nName={name}\nshadeSortColumn=true\naccentColor={rgb(accent)}",
        EFFECTS,
        block("Colors:Button", bg_n=button_bg, bg_a=button_alt),
        block("Colors:Complementary", bg_n=bg, bg_a=bg_alt),
        block("Colors:Header", bg_n=bg_alt, bg_a=bg),
        block(
            "Colors:Selection",
            bg_n=selection_bg,
            bg_a=selection_bg,
            fg_n=selection_fg,
        ),
        block("Colors:Tooltip", bg_n=tooltip_bg, bg_a=bg_alt, fg_n=tooltip_fg),
        block("Colors:View", bg_n=view_bg, bg_a=view_alt),
        block("Colors:Window", bg_n=bg, bg_a=bg_alt),
        f"[WM]\nactiveBackground={rgb(bg_alt)}\nactiveBlend={rgb(bg)}\nactiveForeground={rgb(fg)}\ninactiveBackground={rgb(bg)}\ninactiveBlend={rgb(bg_alt)}\ninactiveForeground={rgb(fg_dim)}",
    ]
    return "\n\n".join(parts) + "\n"


def build_konsole_file(name: str, p: dict) -> str:
    """Konsole .colorscheme — uses 16-colour ANSI palette if provided."""
    ansi = p.get("ansi", {})
    # Sensible defaults from theme base colours.
    defaults = {
        0: p.get("bg", "#000000"),
        1: p.get("negative", "#cd0000"),
        2: p.get("positive", "#00cd00"),
        3: p.get("neutral", "#cdcd00"),
        4: p.get("accent", "#0000ee"),
        5: p.get("visited", "#cd00cd"),
        6: p.get("link", "#00cdcd"),
        7: p.get("fg", "#e5e5e5"),
        8: p.get("fg_dim", "#7f7f7f"),
        9: p.get("negative", "#ff0000"),
        10: p.get("positive", "#00ff00"),
        11: p.get("neutral", "#ffff00"),
        12: p.get("accent", "#5c5cff"),
        13: p.get("visited", "#ff00ff"),
        14: p.get("link", "#00ffff"),
        15: p.get("fg", "#ffffff"),
    }
    palette16 = {i: ansi.get(str(i), defaults[i]) for i in range(16)}

    sections = [
        f"[Background]\nColor={rgb(p['bg'])}",
        f"[BackgroundFaint]\nColor={rgb(p.get('bg_alt', p['bg']))}",
        f"[BackgroundIntense]\nColor={rgb(p['bg'])}",
        f"[Foreground]\nColor={rgb(p['fg'])}",
        f"[ForegroundFaint]\nColor={rgb(p.get('fg_dim', p['fg']))}",
        f"[ForegroundIntense]\nColor={rgb(p['fg'])}",
    ]
    for i in range(8):
        sections.append(f"[Color{i}]\nColor={rgb(palette16[i])}")
        sections.append(f"[Color{i}Faint]\nColor={rgb(palette16[i])}")
        sections.append(f"[Color{i}Intense]\nColor={rgb(palette16[i + 8])}")
    sections.append(f"[General]\nDescription={name}\nOpacity=1\nWallpaper=")
    return "\n\n".join(sections) + "\n"


def build_gtk_css(name: str, p: dict) -> str:
    """A minimal GTK colour override — defines named colours used by gtk-3/4 themes."""
    bg = p["bg"]
    bg_alt = p.get("bg_alt", bg)
    fg = p["fg"]
    fg_dim = p.get("fg_dim", fg)
    accent = p["accent"]
    sel_bg = p.get("selection_bg", accent)
    sel_fg = p.get("selection_fg", bg)
    return dedent(f"""
    /* kolour: {name} */
    @define-color theme_bg_color {bg};
    @define-color theme_base_color {p.get('view_bg', bg)};
    @define-color theme_fg_color {fg};
    @define-color theme_text_color {fg};
    @define-color theme_selected_bg_color {sel_bg};
    @define-color theme_selected_fg_color {sel_fg};
    @define-color theme_unfocused_bg_color {bg_alt};
    @define-color theme_unfocused_fg_color {fg_dim};
    @define-color insensitive_bg_color {bg_alt};
    @define-color insensitive_fg_color {fg_dim};
    @define-color borders {bg_alt};
    @define-color accent_color {accent};
    @define-color accent_bg_color {accent};
    @define-color accent_fg_color {sel_fg};
    @define-color destructive_color {p['negative']};
    @define-color success_color {p['positive']};
    @define-color warning_color {p['neutral']};
    @define-color error_color {p['negative']};
    """).lstrip()


def main() -> int:
    THEMES_DIR.mkdir(parents=True, exist_ok=True)
    KONSOLE_DIR.mkdir(parents=True, exist_ok=True)
    GTK_DIR.mkdir(parents=True, exist_ok=True)

    palettes = sorted(PALETTES_DIR.glob("*.yaml"))
    if not palettes:
        sys.exit(f"no palettes found in {PALETTES_DIR}")
    for path in palettes:
        spec = yaml.safe_load(path.read_text())
        name = spec["name"]
        family = spec.get("family", name.split("-")[0])
        out_dir = THEMES_DIR / family
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{name}.colors").write_text(build_colors_file(name, spec["colors"]))
        (KONSOLE_DIR / f"{name}.colorscheme").write_text(build_konsole_file(name, spec["colors"]))
        (GTK_DIR / f"{name}.css").write_text(build_gtk_css(name, spec["colors"]))
        print(f"  generated {name}")
    print(f"wrote {len(palettes)} themes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
