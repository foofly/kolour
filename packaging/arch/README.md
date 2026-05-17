# Arch packaging

A VCS-style PKGBUILD that pulls from `main` on GitHub. Builds and
installs as `kolour-git`, providing `kolour`.

## Local install

```sh
cd packaging/arch
makepkg -si
```

`makepkg` fetches the source, builds a `.pkg.tar.zst`, and `-i` hands it
to pacman to install — same uninstall path as any other Arch package:

```sh
sudo pacman -Rns kolour-git
```

(Run `kolour reset` first if you want kolour to undo its apply-time
changes; pacman alone only removes the package, not state under
`~/.config/`, `~/.local/share/konsole/`, etc.)

## AUR submission

Once there's a tagged release, this PKGBUILD is the starting point for
the `kolour-git` AUR entry:

```sh
git clone ssh://aur@aur.archlinux.org/kolour-git.git
cp PKGBUILD kolour-git/
cd kolour-git
makepkg --printsrcinfo > .SRCINFO
git add PKGBUILD .SRCINFO
git commit -m "initial import"
git push
```

A stable (non-`-git`) PKGBUILD would change `source=` to a tagged
tarball:

```bash
source=("kolour-$pkgver.tar.gz::$url/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('<run updpkgsums>')
```

and drop the `pkgver()` function.
