# kolour

A small KDE Plasma colour-scheme switcher: a curated palette set, a Textual
TUI for browsing, a no-nonsense CLI for scripting, dark/light auto-follow on
a systemd timer, and on-demand Material You generation from your current
wallpaper.

One apply call sets the Plasma colour scheme, the Konsole profile, the GTK
3/4 overrides, and (where needed) the Plasma Look-and-Feel — so the swap is
visible everywhere, not just in KDE apps.

## Requirements

- **KDE Plasma 6** — kolour drives Plasma via its host binaries:
  `plasma-apply-colorscheme`, `plasma-apply-lookandfeel`, `kreadconfig6`,
  `kwriteconfig6`. They ship with Plasma 6.
- **Python 3.11+**.
- **Optional:** [matugen](https://github.com/InioX/matugen) on `$PATH` for
  Material You generation; Konsole for terminal colour propagation.

## Themes shipped

- **Nord**
- **Catppuccin** — Latte, Frappé, Macchiato, Mocha
- **Everforest** — Dark, Light
- **Sweet**
- **Dracula**
- **Gruvbox** — Dark, Light
- **Tokyo Night** — Night, Storm
- **Material You** — generated from your current wallpaper via [matugen](https://github.com/InioX/matugen)

Each `src/kolour/themes/<family>/LICENSE` cites its upstream palette source.
kolour's own code is MIT.

## Install

```sh
make install-tui   # CLI + Textual TUI + symlinks bundled schemes
# or, CLI only:
make install
```

The Makefile uninstalls any existing pipx package before reinstalling so
source-only edits are picked up reliably; `make link-schemes` then symlinks
each `.colors` file into `~/.local/share/color-schemes/` so KDE finds them.

## Uninstall

```sh
make uninstall            # full clean: invokes `kolour reset` then removes the package
# Or, step by step:
kolour reset              # undo system changes; keep ~/.config/kolour/themes/
kolour reset --purge      # also remove ~/.config/kolour/ entirely
kolour reset --dry-run    # preview without touching anything
```

`kolour reset` undoes everything kolour added at apply-time: the auto-follow
systemd timer, the `KolourA`/`KolourB` Konsole profiles plus copied
`.colorscheme` files, the managed GTK `kolour.css` + import line, the
bundled-scheme symlinks under `~/.local/share/color-schemes/`, and
`~/.config/kolour/state.toml`. User-installed themes (via `kolour install`)
are preserved unless you pass `--purge`.

## The TUI

```sh
kolour tui
```

A two-pane Textual app: a family-grouped theme tree on the left, a details
panel on the right with the theme's name, family, and a live true-colour
swatch of its 12 key colours. The currently-applied scheme is marked with
`●` in the tree.

| Key | Action |
| --- | --- |
| `↑` / `↓` | Move through themes |
| `→` / `←` | Expand / collapse a family |
| `enter` or `a` | Apply the highlighted theme |
| `r` | Re-scan available themes |
| `q` or `esc` | Quit |

Day-one scope is browse-and-apply. Preview-then-keep, accent overrides, and
on-the-fly Material You stay on the CLI (see below).

## CLI

```sh
kolour list                                       # show themes; current marked with '*'
kolour current                                    # print the active scheme name
kolour apply Nord                                 # full swap: scheme + Konsole + GTK + matching L&F
kolour apply Catppuccin-Mocha --accent "#f5c2e7"  # apply with a custom accent
kolour apply Sweet --no-lookandfeel               # keep your current L&F
kolour matugen                                    # Material You from current Plasma wallpaper
kolour matugen --wallpaper /path/to/img.jpg --mode light
kolour status                                     # current scheme, accent, tool availability
kolour reload-konsole                             # force running Konsole sessions to re-read the profile
kolour install /path/to/scheme.colors             # add a third-party .colors file
kolour uninstall <Name>                           # remove a user-installed scheme
```

Global flags: `--no-konsole`, `--no-gtk`, `--no-lookandfeel`, `--dry-run`,
`-v`. Theme names are case- and separator-insensitive (`catppuccin/mocha`,
`Catppuccin-Mocha`, and `catppuccinmocha` all resolve to the same theme).

## Dark / light auto-follow

Pair a dark + light theme and switch between them on a schedule.

```sh
kolour auto pair --dark Catppuccin-Mocha --light Catppuccin-Latte
kolour auto run        # apply the right one for the current time
kolour auto toggle     # flip to the opposite member of the pair
kolour auto status     # show config and which would apply now
kolour auto enable     # install + start a systemd user timer
kolour auto disable    # stop and remove the timer
kolour auto enable --light-after 07:00 --dark-after 19:30
```

`kolour auto enable` writes `kolour-auto.timer` + `kolour-auto.service`
under `~/.config/systemd/user/` and starts the timer. The timer fires at
the configured times; the service runs `kolour auto run`.

Bind `kolour auto toggle` to a global KDE shortcut (System Settings →
Shortcuts → Custom Shortcuts → New → Global) for a one-key dark/light flip.

## Material You

Requires [matugen](https://github.com/InioX/matugen) on `$PATH` (`cargo
install matugen` or your package manager). `kolour matugen` reads your
current Plasma wallpaper, derives a palette, writes
`~/.local/share/color-schemes/MaterialYou.colors`, and applies it through
the standard pipeline.

## Konsole + GTK

- **Konsole** — a matching `.colorscheme` is copied into
  `~/.local/share/konsole/` and one of two managed profiles
  (`KolourA.profile` / `KolourB.profile`) is set as the default. The two
  names rotate on each apply because Konsole caches profile metadata by
  name and won't re-read a profile of the same name. Running sessions are
  then nudged via D-Bus; if that doesn't take, `kolour reload-konsole`
  forces it, and reopening a window is always a safe fallback.
- **GTK 3 / GTK 4** — a managed `kolour.css` is dropped under
  `~/.config/gtk-{3,4}.0/` and `@import`-ed from your existing
  `colors.css`, so any GTK customisation you already had is preserved.
  Cleanly removed on uninstall.

Disable per-call with `kolour apply Nord --no-konsole --no-gtk`.

## Troubleshooting

### Applying a theme doesn't visibly change the desktop

KDE Look-and-Feel packages (anything other than
`org.kde.breeze.desktop` / `org.kde.breezedark.desktop` /
`org.fedoraproject.fedora.desktop`) bundle their own Plasma styles that
paint over the active colour scheme. By default `kolour apply` switches
the L&F to a Breeze variant matching the new scheme's brightness — that's
what makes the swap visible system-wide.

If you've passed `--no-lookandfeel` (or scripted around the default), the
colour scheme is still applied to `~/.config/kdeglobals` but your themed
L&F overrides it visually. Confirm with:

```sh
kreadconfig6 --file kdeglobals --group General --key ColorScheme    # → your scheme
kreadconfig6 --file kdeglobals --group KDE     --key LookAndFeelPackage  # → if non-Breeze, that's why
```

Restore your original L&F afterwards with
`plasma-apply-lookandfeel --apply <pkg>` (e.g. `Ant-Dark`).

### Stale code after editing a source file

`pipx install --force` skips reinstalling source files when the package
version is unchanged. `make install` and `make install-tui` work around
this by uninstalling first. If you call pipx directly:

```sh
pipx uninstall kolour && pipx install '.[tui]'
```

### `kolour tui` fails with `ImportError: textual`

You installed the bare CLI extra. Reinstall with the TUI extra:

```sh
pipx install '.[tui]'
```

### `kolour matugen` says matugen isn't on PATH

Install it (`cargo install matugen`, or your distro's package), then
re-run.

## Adding a theme

Palettes live in YAML; a generator handles the rest.

1. Add `tools/palettes/<Name>.yaml` (copy `tools/palettes/Nord.yaml` as a
   starting point).
2. `make gen-themes` — regenerates `.colors`, the matching Konsole
   `.colorscheme`, and the GTK CSS for every YAML.
3. `make link-schemes` — symlinks the new `.colors` into
   `~/.local/share/color-schemes/`.
4. `make install-tui` — picks up the new file in the installed package.

## Project layout

```
kolour/
├── src/kolour/
│   ├── apply.py          orchestrates KDE / Konsole / GTK / L&F / state
│   ├── auto.py           dark/light pairing + systemd timer
│   ├── cli.py            argparse subcommands
│   ├── colors_io.py      .colors file parsing
│   ├── konsole.py        Konsole .colorscheme + default profile
│   ├── gtk.py            managed gtk-3/4 colors.css import
│   ├── lookandfeel.py    Plasma L&F detection + neutral-Breeze swap
│   ├── matugen.py        Material You generation via matugen
│   ├── registry.py       theme discovery + name resolution
│   ├── state.py          ~/.config/kolour/state.toml
│   ├── wallpaper.py      Plasma wallpaper detection
│   ├── tui/              Textual app + swatch widget
│   ├── themes/           bundled .colors files (one dir per family)
│   ├── konsole/          matching Konsole .colorscheme files
│   ├── gtk/              matching GTK colour overrides
│   └── matugen-templates/   matugen Tera template → KDE .colors
├── tools/
│   ├── generate-colors.py    YAML palette → .colors / .colorscheme / .css
│   └── palettes/             one YAML per bundled theme
└── tests/                pytest suite + stdlib-only smoke.py
```
