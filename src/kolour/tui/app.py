"""Main Textual application: browse themes and apply one."""
from __future__ import annotations

from collections import defaultdict

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Static, Tree
from textual.widgets.tree import TreeNode

from .. import apply as apply_mod
from .. import colors_io, registry
from .swatch import Swatch


class KolourApp(App):
    CSS = """
    Screen {
        layout: horizontal;
    }
    #tree-pane {
        width: 36;
        border-right: solid $primary;
    }
    Tree {
        padding: 1;
    }
    #detail-pane {
        padding: 1 2;
        width: 1fr;
    }
    #title {
        text-style: bold;
        padding-bottom: 1;
    }
    #family {
        color: $text-muted;
        padding-bottom: 1;
    }
    #swatch {
        margin-top: 1;
    }
    #status {
        dock: bottom;
        height: 1;
        background: $primary 30%;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("enter", "apply", "Apply"),
        Binding("a", "apply", "Apply", show=False),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
        Binding("escape", "quit", "Quit", show=False),
    ]

    current: reactive[str | None] = reactive(None)
    selected: reactive[registry.Theme | None] = reactive(None)
    busy: reactive[bool] = reactive(False)

    def __init__(self) -> None:
        super().__init__()
        self._leaves: list[tuple[TreeNode, registry.Theme, str]] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="tree-pane"):
            yield Tree("Themes", id="tree")
        with Vertical(id="detail-pane"):
            yield Static("—", id="title")
            yield Static("", id="family")
            yield Swatch(id="swatch")
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "kolour"
        self.current = apply_mod.current_scheme()
        self._populate_tree()
        self._update_status()

    # --- tree --------------------------------------------------------------

    def _populate_tree(self) -> None:
        tree: Tree = self.query_one("#tree", Tree)
        tree.clear()
        tree.show_root = False
        self._leaves = []

        themes = registry.all()
        by_family: dict[str, list[registry.Theme]] = defaultdict(list)
        for t in themes:
            by_family[t.family or t.name].append(t)

        current_node: TreeNode | None = None
        for family in sorted(by_family.keys(), key=str.lower):
            members = sorted(by_family[family], key=lambda t: t.name.lower())
            if len(members) == 1:
                t = members[0]
                variant = t.label
                node = tree.root.add_leaf(self._theme_label(t, variant), data=t)
                self._leaves.append((node, t, variant))
                if t.name == self.current:
                    current_node = node
            else:
                branch = tree.root.add(family, expand=True)
                for t in members:
                    if t.name.startswith(family + "-"):
                        variant = t.name[len(family) + 1:].replace("-", " ")
                    else:
                        variant = t.name.replace("-", " ")
                    node = branch.add_leaf(self._theme_label(t, variant), data=t)
                    self._leaves.append((node, t, variant))
                    if t.name == self.current:
                        current_node = node

        if current_node is not None:
            try:
                tree.select_node(current_node)
                tree.scroll_to_node(current_node)
            except Exception:
                pass

    def _theme_label(self, theme: registry.Theme, base: str) -> str:
        return f"{base} ●" if theme.name == self.current else base

    def _refresh_tree_labels(self) -> None:
        for node, theme, variant in self._leaves:
            node.set_label(self._theme_label(theme, variant))

    # --- events ------------------------------------------------------------

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        data = event.node.data
        self.selected = data if isinstance(data, registry.Theme) else None

    def watch_selected(self, theme: registry.Theme | None) -> None:
        if not self.is_mounted:
            return
        title = self.query_one("#title", Static)
        family = self.query_one("#family", Static)
        swatch = self.query_one("#swatch", Swatch)
        if theme is None:
            title.update("—")
            family.update("")
            swatch.palette = {}
            return
        title.update(theme.label)
        family.update(theme.family or "")
        try:
            swatch.palette = colors_io.palette(theme.colors_path)
        except OSError:
            swatch.palette = {}

    def watch_current(self, _new: str | None) -> None:
        if self.is_mounted:
            self._update_status()

    # --- actions -----------------------------------------------------------

    def action_apply(self) -> None:
        if self.busy or self.selected is None:
            return
        self._do_apply(self.selected)

    def action_refresh(self) -> None:
        self.current = apply_mod.current_scheme()
        self._populate_tree()

    @work(thread=True, exclusive=True)
    def _do_apply(self, theme: registry.Theme) -> None:
        self.call_from_thread(self._begin_apply, theme.name)
        try:
            apply_mod.apply_theme(theme.name)
        except Exception as e:  # noqa: BLE001 — surface to UI
            self.call_from_thread(self._after_apply, theme, str(e))
            return
        self.call_from_thread(self._after_apply, theme, None)

    def _begin_apply(self, name: str) -> None:
        self.busy = True
        self.query_one("#status", Static).update(f"Applying {name}…")

    def _after_apply(self, theme: registry.Theme, error: str | None) -> None:
        self.busy = False
        if error:
            self.query_one("#status", Static).update(f"Failed: {error}")
            return
        self.current = theme.name
        self._refresh_tree_labels()

    def _update_status(self) -> None:
        try:
            status = self.query_one("#status", Static)
        except Exception:
            return
        status.update(f"Current: {self.current or 'unset'}")
