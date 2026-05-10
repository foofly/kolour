# kolour

Quick KDE Plasma colour-scheme switcher with curated palettes, a PySide6 GUI, dark/light auto-follow, and Material You support.

![Main window](docs/screenshots/main-window.png)

## Themes shipped

- **Nord**
- **Catppuccin** — Latte, Frappe, Macchiato, Mocha
- **Everforest** — Dark, Light
- **Sweet**
- **Dracula**
- **Gruvbox** — Dark, Light
- **Tokyo Night** — Night, Storm
- **Material You** — generated from your current wallpaper via [matugen](https://github.com/InioX/matugen)

## Install

```sh
make install-gui   # CLI + PySide6 GUI + symlinks bundled schemes
# or, CLI only:
make install
```

The Makefile uninstalls any existing pipx package before reinstalling so source-only edits are picked up reliably; `make link-schemes` then symlinks each `.colors` file into `~/.local/share/color-schemes/` so KDE finds them.

## Use

```sh
kolour list                    # show themes; current marked with a green dot
kolour current                 # print the active scheme name
kolour apply Nord              # full swap: scheme + Konsole + GTK + matching Look-and-Feel
kolour apply Catppuccin-Mocha --accent "#f5c2e7"
kolour apply Sweet --no-lookandfeel    # keep your current Look-and-Feel
kolour gui                     # PySide6 picker — list, swatches, accent picker, preview/apply/revert
kolour matugen                 # generate Material You from current Plasma wallpaper
kolour matugen --wallpaper /path/to/img.jpg --mode light
kolour status                  # current scheme, accent, konsole/matugen availability
```

Global flags: `--no-konsole`, `--no-gtk`, `--no-lookandfeel`, `--dry-run`, `-v`.

## Dark / light auto-follow

Pair a dark + light theme and switch them on a schedule.

```sh
kolour auto pair --dark Catppuccin-Mocha --light Catppuccin-Latte
kolour auto run                # apply the right one for the current time
kolour auto toggle             # flip to the opposite member of the pair
kolour auto status             # show config and which would apply now
kolour auto enable             # install + start a systemd user timer
kolour auto disable            # stop and remove the timer
kolour auto enable --light-after 07:00 --dark-after 19:30
```

`kolour auto enable` writes a `kolour-auto.timer` + `kolour-auto.service` under `~/.config/systemd/user/` and starts the timer. The timer fires at the configured times; the service runs `kolour auto run`.

You can also bind `kolour auto toggle` to a global KDE shortcut (System Settings → Shortcuts → Custom Shortcuts) for a one-key flip.

## Material You

Requires `matugen` on `$PATH`. Install via your package manager or `cargo install matugen`. `kolour matugen` reads your current Plasma wallpaper, derives a palette, writes `~/.local/share/color-schemes/MaterialYou.colors`, and applies it via the standard pipeline.

## Konsole + GTK

Konsole gets a matching `.colorscheme` file and a managed `Kolour.profile` set as the default profile. **Existing Konsole windows must be reopened to pick up the new colours** — KDE limitation.

GTK 3 / GTK 4 get a managed `kolour.css` imported from `~/.config/gtk-{3,4}.0/colors.css` so any of your existing GTK customisation is preserved. Removed cleanly on uninstall.

Disable per-call: `kolour apply Nord --no-konsole --no-gtk`.

## Bind a global shortcut

System Settings → Shortcuts → Custom Shortcuts → New → Global → Command/URL: `kolour gui` (or `kolour auto toggle`).

## Troubleshooting

### Applying a theme doesn't visibly change the desktop

KDE Look-and-Feel packages (anything other than `org.kde.breeze.desktop` / `org.kde.breezedark.desktop` / `org.fedoraproject.fedora.desktop`) bundle their own Plasma styles that paint over the active colour scheme. By default `kolour apply` switches the L&F to a Breeze variant matching the new scheme's brightness — that's what makes the swap visible system-wide.

If you've passed `--no-lookandfeel` (or scripted around the default), the colour scheme is still applied to `~/.config/kdeglobals` but your themed L&F overrides it visually. Confirm with:

```sh
kreadconfig6 --file kdeglobals --group General --key ColorScheme   # → your scheme
kreadconfig6 --file kdeglobals --group KDE --key LookAndFeelPackage # → if non-Breeze, that's why
```

To restore your original L&F afterwards:

```sh
plasma-apply-lookandfeel --apply <pkg>   # e.g. Ant-Dark
```

### The pipx-installed `kolour` binary still has stale code after I edit a file

`pipx install --force` skips reinstalling source files when the package version is unchanged. `make install` and `make install-gui` work around this by uninstalling first. If you call pipx directly:

```sh
pipx uninstall kolour && pipx install '.[gui]'
```

### `kolour gui` fails with `ImportError: PySide6`

Install with the GUI extra:

```sh
pipx install '.[gui]'
```

### `kolour matugen` says matugen isn't on PATH

Install via your distro's package or `cargo install matugen`, then re-run.

### Logging from the GUI

Set `KOLOUR_LOG=DEBUG` (or `INFO` / `WARNING`) before launching to control verbosity:

```sh
KOLOUR_LOG=DEBUG kolour gui 2>~/kolour.log
```

## Flatpak (experimental)

A Flatpak manifest lives under `flatpak/`. kolour is unusual for a Flatpak: it's a system-administration tool, so every host call (KDE binaries, D-Bus, systemd) escapes the sandbox via `flatpak-spawn --host`. The Flatpak gives you distribution and a desktop entry, not security isolation.

Build + install locally:

```sh
make flatpak-install     # needs flatpak-builder; pulls org.kde.{Platform,Sdk}//6.10
make flatpak-run         # launches the GUI
```

Caveats:
- `matugen` must be installed on the host (the sandbox can't bundle it usefully — it'd run inside the sandbox without access to the host's wallpaper file).
- The bundled `.colors` files are copied into `~/.local/share/color-schemes/` on first apply (instead of symlinked) so they remain reachable when the Flatpak is uninstalled or upgraded.
- Flathub submission would need a real icon (the bundled SVG is a placeholder), screenshots, AppStream validation, and a maintained release tag — out of scope for the initial drop.

## Theme attribution

Each `src/kolour/themes/<theme>/LICENSE` cites the upstream palette source. kolour's own code is MIT.

## Adding a theme

Palettes are YAML; the generator does the rest.

1. Add `tools/palettes/<Name>.yaml` (copy any existing one as a starting point — see `tools/palettes/Nord.yaml`).
2. `make gen-themes` regenerates `.colors`, the matching Konsole `.colorscheme`, and the GTK CSS for every YAML.
3. `make link-schemes` symlinks the new `.colors` into `~/.local/share/color-schemes/`.
4. `make install-gui` (or `pipx uninstall kolour && pipx install '.[gui]'`) so the package picks up the new file.

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
│   ├── gui/              PySide6 main window, tree model, swatch widget
│   ├── themes/           bundled .colors files (one dir per family)
│   ├── konsole/          matching Konsole .colorscheme files
│   ├── gtk/              matching GTK colour overrides
│   └── matugen-templates/   matugen Tera template → KDE .colors
├── tools/
│   ├── generate-colors.py    YAML palette → .colors / .colorscheme / .css
│   └── palettes/             one YAML per bundled theme
└── tests/                pytest suite + stdlib-only smoke.py
```
