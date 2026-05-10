"""kolour main GUI window."""
from __future__ import annotations

import logging
import shutil

log = logging.getLogger("kolour.gui")

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QColor, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QColorDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTreeView,
    QVBoxLayout,
    QMainWindow,
    QWidget,
)

from .. import apply as apply_mod
from .. import matugen as matugen_mod
from ..colors_io import rgb_to_hex
from .swatch import SwatchWidget
from .theme_model import ThemeDelegate, ThemeModel


class _ApplyWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, name: str, accent: str | None, *, preview: bool = False) -> None:
        super().__init__()
        self._name = name
        self._accent = accent
        self._preview = preview

    def run(self) -> None:
        try:
            if self._preview:
                result = apply_mod.preview_theme(self._name, accent=self._accent)
            else:
                result = apply_mod.apply_theme(self._name, accent=self._accent)
        except Exception as e:  # noqa: BLE001 — surface to UI
            self.failed.emit(str(e))
            return
        self.finished.emit(result)


class _MatugenWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def run(self) -> None:
        try:
            result = matugen_mod.generate_and_apply()
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))
            return
        self.finished.emit(result)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("kolour")
        self.resize(820, 520)

        self._model = ThemeModel(self)
        self._model.set_current(apply_mod.current_scheme())
        self._accent_override: str | None = None
        self._preview_prev: tuple[str, str | None] | None = None
        self._thread: QThread | None = None
        self._worker: QObject | None = None

        self._build_ui()
        self._wire_shortcuts()
        self._select_current_or_first()

    # --- UI construction ----------------------------------------------------

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Horizontal, self)

        # Left: theme tree, grouped by family
        self._list = QTreeView()
        self._list.setModel(self._model)
        self._delegate = ThemeDelegate(self._model, self._list)
        self._list.setItemDelegate(self._delegate)
        self._list.setHeaderHidden(True)
        self._list.setRootIsDecorated(True)
        self._list.setIndentation(14)
        self._list.expandAll()
        self._list.selectionModel().currentChanged.connect(self._on_selection_changed)
        self._list.doubleClicked.connect(lambda _i: self._on_apply())
        splitter.addWidget(self._list)

        # Right: detail panel
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(16, 16, 16, 16)
        rl.setSpacing(12)

        self._title = QLabel("—")
        title_font = self._title.font()
        title_font.setPointSize(title_font.pointSize() + 4)
        title_font.setBold(True)
        self._title.setFont(title_font)
        rl.addWidget(self._title)

        self._family_label = QLabel("")
        self._family_label.setStyleSheet("color: gray;")
        rl.addWidget(self._family_label)

        self._swatch = SwatchWidget(compact=False)
        rl.addWidget(self._swatch)

        # Accent row
        accent_row = QHBoxLayout()
        accent_row.addWidget(QLabel("Accent:"))
        self._accent_btn = QPushButton("Default")
        self._accent_btn.clicked.connect(self._pick_accent)
        accent_row.addWidget(self._accent_btn)
        self._accent_reset = QPushButton("Reset")
        self._accent_reset.clicked.connect(self._reset_accent)
        accent_row.addWidget(self._accent_reset)
        accent_row.addStretch(1)
        rl.addLayout(accent_row)

        # Preview banner
        self._banner = QFrame()
        self._banner.setStyleSheet(
            "background: palette(highlight); color: palette(highlighted-text); padding: 6px; border-radius: 4px;"
        )
        bl = QHBoxLayout(self._banner)
        bl.setContentsMargins(8, 4, 8, 4)
        self._banner_label = QLabel("Previewing —")
        bl.addWidget(self._banner_label)
        bl.addStretch(1)
        self._banner_apply = QPushButton("Keep")
        self._banner_apply.clicked.connect(self._on_keep_preview)
        bl.addWidget(self._banner_apply)
        self._banner_revert = QPushButton("Revert")
        self._banner_revert.clicked.connect(self._on_revert_preview)
        bl.addWidget(self._banner_revert)
        self._banner.hide()
        rl.addWidget(self._banner)

        rl.addStretch(1)

        # Action buttons
        btn_row = QHBoxLayout()
        self._preview_btn = QPushButton("Preview")
        self._preview_btn.clicked.connect(self._on_preview)
        btn_row.addWidget(self._preview_btn)

        self._apply_btn = QPushButton("Apply")
        self._apply_btn.setDefault(True)
        self._apply_btn.clicked.connect(self._on_apply)
        btn_row.addWidget(self._apply_btn)

        self._matu_btn = QPushButton("Material You")
        self._matu_btn.clicked.connect(self._on_matugen)
        if not matugen_mod.available():
            self._matu_btn.setEnabled(False)
            self._matu_btn.setToolTip(
                "matugen not found on PATH. Install with: cargo install matugen"
            )
        btn_row.addWidget(self._matu_btn)
        btn_row.addStretch(1)
        rl.addLayout(btn_row)

        splitter.addWidget(right)
        splitter.setSizes([300, 520])
        self.setCentralWidget(splitter)

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage(f"Current: {apply_mod.current_scheme() or 'unset'}")

    def _wire_shortcuts(self) -> None:
        QShortcut(QKeySequence("Return"), self, activated=self._on_apply)
        QShortcut(QKeySequence("Enter"), self, activated=self._on_apply)
        QShortcut(QKeySequence("Escape"), self, activated=self._escape)

    def _select_current_or_first(self) -> None:
        current = apply_mod.current_scheme()
        if current:
            idx = self._model.index_for_theme_name(current)
            if idx is not None and idx.isValid():
                self._list.setCurrentIndex(idx)
                self._list.scrollTo(idx)
                return
        themes = self._model.all_themes()
        if themes:
            first = self._model.index_for_theme_name(themes[0].name)
            if first is not None:
                self._list.setCurrentIndex(first)

    # --- handlers -----------------------------------------------------------

    def _selected_theme(self):
        return self._model.theme_for_index(self._list.currentIndex())

    def _on_selection_changed(self, current, _previous) -> None:
        theme = self._model.theme_for_index(current)
        if theme is None:
            return
        self._title.setText(theme.label)
        self._family_label.setText(theme.family or "")
        self._swatch.set_palette(self._model.palette_for(theme.name))

    def _pick_accent(self) -> None:
        initial = QColor(self._accent_override) if self._accent_override else QColor(Qt.blue)
        c = QColorDialog.getColor(initial, self, "Pick accent colour")
        if c.isValid():
            self._accent_override = rgb_to_hex((c.red(), c.green(), c.blue()))
            self._accent_btn.setText(self._accent_override)

    def _reset_accent(self) -> None:
        self._accent_override = None
        self._accent_btn.setText("Default")

    def _busy(self, on: bool) -> None:
        for b in (self._preview_btn, self._apply_btn, self._matu_btn, self._list):
            b.setEnabled(not on)

    def _start_apply(self, name: str, accent: str | None, *, on_done, preview: bool = False) -> None:
        self._busy(True)
        self._status.showMessage(f"{'Previewing' if preview else 'Applying'} {name}…")
        self._thread = QThread(self)
        self._worker = _ApplyWorker(name, accent, preview=preview)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(lambda result: on_done(result, None))
        self._worker.failed.connect(lambda err: on_done(None, err))
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _cleanup_thread(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None

    def _after_apply(self, name: str, accent: str | None, result, error: str | None) -> None:
        self._busy(False)
        if error:
            self._status.showMessage(f"Failed: {error}", 5000)
            QMessageBox.warning(self, "kolour", error)
            return
        self._model.set_current(name)
        self._status.showMessage(f"Current: {name}" + (f" (accent {accent})" if accent else ""))

    def _on_apply(self) -> None:
        theme = self._selected_theme()
        if theme is None:
            return
        # If we were previewing, an Apply just commits the preview.
        self._preview_prev = None
        self._banner.hide()
        accent = self._accent_override
        self._start_apply(
            theme.name, accent,
            on_done=lambda r, err: self._after_apply(theme.name, accent, r, err),
        )

    def _on_preview(self) -> None:
        theme = self._selected_theme()
        if theme is None:
            return
        from .. import state as state_mod
        # Stash committed (name, accent) so Revert can put it back. Don't
        # overwrite if a preview is already active — the original committed
        # scheme is what we want to revert to, not the previously-previewed one.
        if self._preview_prev is None:
            prev_state = state_mod.read()
            prev_name = apply_mod.current_scheme()
            if prev_name:
                self._preview_prev = (prev_name, prev_state.get("accent"))
        accent = self._accent_override
        self._start_apply(
            theme.name, accent,
            preview=True,
            on_done=lambda r, err: self._after_preview(theme.name, accent, r, err),
        )

    def _after_preview(self, name: str, accent: str | None, result, error: str | None) -> None:
        self._busy(False)
        if error:
            self._status.showMessage(f"Failed: {error}", 5000)
            QMessageBox.warning(self, "kolour", error)
            return
        # Don't move the model's current marker — preview hasn't been committed.
        self._status.showMessage(f"Previewing {name}" + (f" (accent {accent})" if accent else ""))
        if self._preview_prev:
            self._banner_label.setText(
                f"Previewing {name} — Apply to keep, Revert to {self._preview_prev[0]}"
            )
            self._banner.show()

    def _on_keep_preview(self) -> None:
        # Commit the preview by running the full apply pipeline.
        theme = self._selected_theme()
        if theme is None:
            return
        self._preview_prev = None
        self._banner.hide()
        accent = self._accent_override
        self._start_apply(
            theme.name, accent,
            on_done=lambda r, err: self._after_apply(theme.name, accent, r, err),
        )

    def _on_revert_preview(self) -> None:
        if not self._preview_prev:
            self._banner.hide()
            return
        prev_name, prev_accent = self._preview_prev
        self._preview_prev = None
        self._banner.hide()
        # Visual-only revert — never persist; the prev scheme was already the
        # committed one, so its state.toml + L&F + Konsole/GTK are still right.
        self._start_apply(
            prev_name, prev_accent,
            preview=True,
            on_done=lambda r, err: self._after_revert(prev_name, prev_accent, r, err),
        )

    def _after_revert(self, name: str, accent: str | None, result, error: str | None) -> None:
        self._busy(False)
        if error:
            self._status.showMessage(f"Failed: {error}", 5000)
            QMessageBox.warning(self, "kolour", error)
            return
        self._status.showMessage(f"Current: {name}" + (f" (accent {accent})" if accent else ""))

    def _escape(self) -> None:
        if self._preview_prev:
            self._on_revert_preview()
        else:
            self.close()

    def closeEvent(self, event) -> None:  # noqa: N802 — Qt API
        # If we exit mid-preview, revert visually so the user doesn't end up on
        # an uncommitted scheme. Done synchronously — single ~200ms call.
        if self._preview_prev:
            prev_name, prev_accent = self._preview_prev
            self._preview_prev = None
            # Wait for any in-flight worker to finish first so we don't race it.
            if self._thread is not None:
                self._thread.quit()
                self._thread.wait(2000)
            log.info("reverting preview to %s on close", prev_name)
            try:
                apply_mod.preview_theme(prev_name, accent=prev_accent)
            except Exception as e:  # noqa: BLE001 — closing anyway
                log.warning("revert on close failed: %s", e)
        super().closeEvent(event)

    def _on_matugen(self) -> None:
        if not matugen_mod.available():
            QMessageBox.warning(
                self, "kolour",
                "matugen not found on PATH.\nInstall with: cargo install matugen",
            )
            return
        self._busy(True)
        self._status.showMessage("Generating Material You from current wallpaper…")
        self._thread = QThread(self)
        self._worker = _MatugenWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._after_matugen_ok)
        self._worker.failed.connect(self._after_matugen_err)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _after_matugen_ok(self, result) -> None:
        self._busy(False)
        self._model.refresh()
        self._list.expandAll()
        self._model.set_current("MaterialYou")
        idx = self._model.index_for_theme_name("MaterialYou")
        if idx is not None:
            self._list.setCurrentIndex(idx)
            self._list.scrollTo(idx)
        self._status.showMessage("Applied Material You")

    def _after_matugen_err(self, err: str) -> None:
        self._busy(False)
        self._status.showMessage(f"Material You failed: {err}", 8000)
        QMessageBox.warning(self, "kolour", err)
