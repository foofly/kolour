"""Qt tree model + delegate for the theme list, grouped by family."""
from __future__ import annotations

from collections import defaultdict

from PySide6.QtCore import QModelIndex, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from .. import colors_io, registry

THEME_ROLE = Qt.UserRole + 1
KIND_ROLE = Qt.UserRole + 2  # "family" or "theme"


class ThemeModel(QStandardItemModel):
    """Tree of families → themes. Single-member families render flat at the top level."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._palettes: dict[str, colors_io.Palette] = {}
        self._current: str | None = None
        self._all_themes: list[registry.Theme] = []
        self.refresh()

    # --- public API ----------------------------------------------------

    def refresh(self) -> None:
        self.clear()
        self.setHorizontalHeaderLabels(["Theme"])
        self._all_themes = registry.all()
        self._palettes = {t.name: colors_io.palette(t.colors_path) for t in self._all_themes}

        # Group by family (default family = theme name when missing).
        by_family: dict[str, list[registry.Theme]] = defaultdict(list)
        for t in self._all_themes:
            by_family[t.family or t.name].append(t)

        root = self.invisibleRootItem()
        for family in sorted(by_family.keys(), key=str.lower):
            themes = sorted(by_family[family], key=lambda t: t.name.lower())
            if len(themes) == 1:
                root.appendRow(self._theme_item(themes[0], label_override=themes[0].name))
            else:
                family_item = QStandardItem(family)
                family_item.setData("family", KIND_ROLE)
                family_item.setEditable(False)
                family_item.setSelectable(False)
                bold = family_item.font()
                bold.setBold(True)
                family_item.setFont(bold)
                for t in themes:
                    flavour = t.name.removeprefix(family + "-") if t.name.startswith(family + "-") else t.name
                    family_item.appendRow(self._theme_item(t, label_override=flavour))
                root.appendRow(family_item)

    def set_current(self, name: str | None) -> None:
        if name == self._current:
            return
        old = self._current
        self._current = name
        for theme_name in (old, name):
            if not theme_name:
                continue
            idx = self.index_for_theme_name(theme_name)
            if idx is not None:
                self.dataChanged.emit(idx, idx, [Qt.DisplayRole])

    def palette_for(self, name: str) -> colors_io.Palette:
        return self._palettes.get(name, {})

    def index_for_theme_name(self, name: str) -> QModelIndex | None:
        """Walk the tree to find the index for a given theme name."""
        root = self.invisibleRootItem()
        for r in range(root.rowCount()):
            top = root.child(r, 0)
            t = top.data(THEME_ROLE)
            if isinstance(t, registry.Theme) and t.name == name:
                return top.index()
            for c in range(top.rowCount()):
                child = top.child(c, 0)
                ct = child.data(THEME_ROLE)
                if isinstance(ct, registry.Theme) and ct.name == name:
                    return child.index()
        return None

    def theme_for_index(self, index: QModelIndex) -> registry.Theme | None:
        if not index.isValid():
            return None
        item = self.itemFromIndex(index)
        if item is None:
            return None
        data = item.data(THEME_ROLE)
        return data if isinstance(data, registry.Theme) else None

    def all_themes(self) -> list[registry.Theme]:
        return list(self._all_themes)

    # --- internals -----------------------------------------------------

    def _theme_item(self, theme: registry.Theme, *, label_override: str) -> QStandardItem:
        item = QStandardItem(label_override.replace("-", " "))
        item.setData(theme, THEME_ROLE)
        item.setData("theme", KIND_ROLE)
        item.setEditable(False)
        return item


class ThemeDelegate(QStyledItemDelegate):
    """Paints theme leaves with a current-marker dot. Family rows use defaults."""

    def __init__(self, model: ThemeModel, parent=None) -> None:
        super().__init__(parent)
        self._model = model

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        kind = index.data(KIND_ROLE)
        if kind == "family":
            return QSize(220, 26)
        return QSize(220, 26)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        kind = index.data(KIND_ROLE)
        if kind != "theme":
            super().paint(painter, option, index)
            return

        painter.save()
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())

        theme = self._model.theme_for_index(index)
        rect = option.rect.adjusted(4, 4, -8, -4)
        marker_w = 14
        if theme and theme.name == self._model._current:
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor(120, 200, 120))
            painter.setPen(Qt.NoPen)
            cy = rect.center().y()
            painter.drawEllipse(rect.left(), cy - 4, 8, 8)
            painter.restore()

        text_rect = option.rect.adjusted(rect.left() - option.rect.left() + marker_w, 0, -8, 0)
        label = index.data(Qt.DisplayRole) or ""
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, label)
        painter.restore()
