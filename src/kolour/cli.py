"""kolour command-line interface."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import apply as apply_mod
from . import auto as auto_mod
from . import gtk as gtk_mod
from . import host
from . import konsole as konsole_mod
from . import matugen as matugen_mod
from . import registry, state


def _print_actions(actions: list[str], verbose: bool) -> None:
    if not actions:
        return
    if verbose:
        for a in actions:
            print(f"  · {a}")
    else:
        last = actions[-1]
        if last:
            print(f"· {last}")


def cmd_list(args: argparse.Namespace) -> int:
    current = apply_mod.current_scheme()
    bundled = registry.all()
    bundled_names = {t.name for t in bundled}
    if bundled:
        print("Bundled themes:")
        for t in bundled:
            mark = "*" if t.name == current else " "
            family = f"  ({t.family})" if t.family else ""
            print(f"  {mark} {t.name}{family}")
    extras = [n for n in registry.system_schemes() if n not in bundled_names]
    if extras:
        print("\nOther installed schemes:")
        for n in extras:
            mark = "*" if n == current else " "
            print(f"  {mark} {n}")
    return 0


def cmd_current(args: argparse.Namespace) -> int:
    name = apply_mod.current_scheme()
    if name:
        print(name)
        return 0
    print("(no scheme set)", file=sys.stderr)
    return 1


def cmd_apply(args: argparse.Namespace) -> int:
    try:
        result = apply_mod.apply_theme(
            args.name,
            accent=args.accent,
            konsole=not args.no_konsole,
            gtk=not args.no_gtk,
            lookandfeel=args.lookandfeel,
            dry_run=args.dry_run,
        )
    except KeyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    _print_actions(result.actions, args.verbose)
    if not args.verbose and not result.skipped:
        print(f"applied {result.name}" + (f" (accent {result.accent})" if result.accent else ""))
    return 0


def cmd_gui(args: argparse.Namespace) -> int:
    try:
        from .gui.app import run
    except ImportError as e:
        print(
            "PySide6 not installed. Install with:\n"
            "  pipx install 'kolour[gui]'\n"
            "or:\n"
            "  pip install --user PySide6\n"
            f"(import error: {e})",
            file=sys.stderr,
        )
        return 1
    return run()


def cmd_install(args: argparse.Namespace) -> int:
    src = Path(args.path).expanduser()
    if not src.is_file() or src.suffix != ".colors":
        print(f"error: not a .colors file: {src}", file=sys.stderr)
        return 2
    user_dir = Path.home() / ".config" / "kolour" / "themes"
    user_dir.mkdir(parents=True, exist_ok=True)
    dest = user_dir / src.name
    shutil.copyfile(src, dest)
    # also link into KDE's scheme dir so it's pickable
    kde_link = registry.KDE_SCHEMES_DIR / src.name
    registry.KDE_SCHEMES_DIR.mkdir(parents=True, exist_ok=True)
    if kde_link.exists() or kde_link.is_symlink():
        kde_link.unlink()
    try:
        kde_link.symlink_to(dest)
    except OSError:
        shutil.copyfile(dest, kde_link)
    print(f"installed {dest.stem}")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    user_dir = Path.home() / ".config" / "kolour" / "themes"
    target = user_dir / f"{args.name}.colors"
    link = registry.KDE_SCHEMES_DIR / f"{args.name}.colors"
    removed = False
    for p in (link, target):
        if p.exists() or p.is_symlink():
            p.unlink()
            removed = True
    if not removed:
        print(f"error: no user-installed theme {args.name!r}", file=sys.stderr)
        return 2
    print(f"removed {args.name}")
    return 0


def cmd_matugen(args: argparse.Namespace) -> int:
    try:
        wp = Path(args.wallpaper).expanduser() if args.wallpaper else None
        result = matugen_mod.generate_and_apply(
            wallpaper_path=wp,
            mode=args.mode,
            dry_run=args.dry_run,
        )
    except matugen_mod.MatugenMissing as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except matugen_mod.WallpaperMissing as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    _print_actions(result.actions, args.verbose)
    return 0


def cmd_auto(args: argparse.Namespace) -> int:
    op = args.op
    if op == "pair":
        if not args.dark or not args.light:
            print("error: both --dark and --light are required", file=sys.stderr)
            return 2
        cfg = auto_mod.set_pair(
            dark=args.dark, light=args.light,
            light_after=args.light_after, dark_after=args.dark_after,
        )
        print(f"paired: dark={cfg['dark']} light={cfg['light']} "
              f"(light from {cfg['light_after']}, dark from {cfg['dark_after']})")
        return 0
    if op == "run":
        try:
            result = auto_mod.run(force=args.force, dry_run=args.dry_run)
        except auto_mod.AutoNotConfigured as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        except (KeyError, RuntimeError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        _print_actions(result.actions, args.verbose)
        return 0
    if op == "toggle":
        try:
            result = auto_mod.toggle(dry_run=args.dry_run)
        except auto_mod.AutoNotConfigured as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        _print_actions(result.actions, args.verbose)
        if not args.verbose:
            print(f"applied {result.name}")
        return 0
    if op == "status":
        cfg = auto_mod.get()
        if not cfg:
            print("auto: not configured")
            return 0
        print(f"dark         : {cfg.get('dark', '(unset)')}")
        print(f"light        : {cfg.get('light', '(unset)')}")
        print(f"light_after  : {cfg.get('light_after', auto_mod.DEFAULT_LIGHT_AFTER)}")
        print(f"dark_after   : {cfg.get('dark_after', auto_mod.DEFAULT_DARK_AFTER)}")
        try:
            mode = auto_mod.desired_mode_now()
            print(f"now → {mode} ({cfg.get(mode, '?')})")
        except auto_mod.AutoNotConfigured:
            pass
        print(f"systemd timer: {auto_mod.timer_status()}")
        return 0
    if op == "clear":
        auto_mod.clear()
        print("auto: cleared")
        return 0
    if op == "enable":
        try:
            actions = auto_mod.install_timer(
                light_after=args.light_after, dark_after=args.dark_after,
            )
        except auto_mod.AutoNotConfigured as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        _print_actions(actions, args.verbose)
        if not args.verbose:
            print("auto timer enabled")
        return 0
    if op == "disable":
        actions = auto_mod.disable_timer()
        _print_actions(actions, args.verbose)
        if not args.verbose:
            print("auto timer disabled")
        return 0
    print(f"error: unknown auto op {op!r}", file=sys.stderr)
    return 2


def cmd_reload_konsole(args: argparse.Namespace) -> int:
    actions = konsole_mod.reload_running_sessions()
    if not actions:
        print("no running Konsole sessions found")
        return 0
    _print_actions(actions, args.verbose)
    if not args.verbose:
        print(actions[-1])
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    s = state.read()
    print(f"current scheme : {apply_mod.current_scheme() or '(unset)'}")
    print(f"saved accent   : {s.get('accent', '(none)')}")
    konsole_ok = host.which("konsole") is not None
    matugen_ok = host.which("matugen") is not None
    print(f"konsole        : {'available' if konsole_ok else 'not installed'}")
    print(f"matugen        : {'available' if matugen_ok else 'not installed'}")
    print(f"bundled themes : {len(registry.all())}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="kolour",
        description="Quick KDE Plasma colour-scheme switcher.",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("reload-konsole",
                   help="force running Konsole sessions to re-read the kolour profile").set_defaults(func=cmd_reload_konsole)
    sub.add_parser("list", help="list available themes").set_defaults(func=cmd_list)
    sub.add_parser("current", help="print the active scheme").set_defaults(func=cmd_current)
    sub.add_parser("status", help="show kolour state").set_defaults(func=cmd_status)
    sub.add_parser("gui", help="launch the PySide6 picker").set_defaults(func=cmd_gui)

    apply_p = sub.add_parser("apply", help="apply a theme")
    apply_p.add_argument("name")
    apply_p.add_argument("--accent", help="override accent colour, e.g. '#f5c2e7'")
    apply_p.add_argument("--no-konsole", action="store_true")
    apply_p.add_argument("--no-gtk", action="store_true")
    apply_p.add_argument(
        "--no-lookandfeel", dest="lookandfeel", action="store_false",
        help="keep the current Look-and-Feel package (default: swap to Breeze when active L&F overrides colour schemes)",
    )
    apply_p.set_defaults(lookandfeel=True)
    apply_p.add_argument("--dry-run", action="store_true")
    apply_p.set_defaults(func=cmd_apply)

    install_p = sub.add_parser("install", help="install a third-party .colors file")
    install_p.add_argument("path")
    install_p.set_defaults(func=cmd_install)

    uninstall_p = sub.add_parser("uninstall", help="remove a user-installed scheme")
    uninstall_p.add_argument("name")
    uninstall_p.set_defaults(func=cmd_uninstall)

    matu_p = sub.add_parser("matugen", help="generate Material You from current wallpaper")
    matu_p.add_argument("--wallpaper", help="path to image; defaults to current Plasma wallpaper")
    matu_p.add_argument("--mode", choices=("dark", "light"), default="dark")
    matu_p.add_argument("--dry-run", action="store_true")
    matu_p.set_defaults(func=cmd_matugen)

    auto_p = sub.add_parser("auto", help="dark/light auto-follow")
    auto_sub = auto_p.add_subparsers(dest="op", required=True)

    pair_p = auto_sub.add_parser("pair", help="set the dark/light theme pair")
    pair_p.add_argument("--dark", required=True)
    pair_p.add_argument("--light", required=True)
    pair_p.add_argument("--light-after", help=f"HH:MM (default {auto_mod.DEFAULT_LIGHT_AFTER})")
    pair_p.add_argument("--dark-after", help=f"HH:MM (default {auto_mod.DEFAULT_DARK_AFTER})")

    run_p = auto_sub.add_parser("run", help="apply the right theme for the current time")
    run_p.add_argument("--force", choices=("dark", "light"), help="ignore time-of-day")
    run_p.add_argument("--dry-run", action="store_true")

    toggle_p = auto_sub.add_parser("toggle", help="flip between paired dark/light themes")
    toggle_p.add_argument("--dry-run", action="store_true")

    auto_sub.add_parser("status", help="show auto configuration")
    auto_sub.add_parser("clear", help="remove auto configuration")

    enable_p = auto_sub.add_parser("enable", help="install + enable a systemd user timer")
    enable_p.add_argument("--light-after", help="HH:MM")
    enable_p.add_argument("--dark-after", help="HH:MM")

    auto_sub.add_parser("disable", help="disable + remove the systemd user timer")
    auto_p.set_defaults(func=cmd_auto)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
