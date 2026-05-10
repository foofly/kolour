"""Apply pipeline — uses dry-run mode so no real KDE/Konsole/GTK calls happen."""
from kolour import apply, registry


def test_dry_run_lists_actions(monkeypatch, tmp_path):
    # Redirect KDE scheme dir + Konsole/GTK targets so we don't actually touch the system.
    monkeypatch.setattr(apply, "KDE_SCHEMES_DIR", tmp_path / "schemes")
    monkeypatch.setattr(registry, "KDE_SCHEMES_DIR", tmp_path / "schemes")
    # current_scheme call should not block dry-run; force a "not current" answer
    monkeypatch.setattr(apply, "current_scheme", lambda: None)

    result = apply.apply_theme("Nord", dry_run=True, konsole=True, gtk=True)
    joined = " ".join(result.actions)

    assert result.name == "Nord"
    assert result.dry_run is True
    assert "plasma-apply-colorscheme Nord" in joined


def test_dry_run_skips_konsole_when_not_available(monkeypatch, tmp_path):
    monkeypatch.setattr(apply, "KDE_SCHEMES_DIR", tmp_path / "schemes")
    monkeypatch.setattr(registry, "KDE_SCHEMES_DIR", tmp_path / "schemes")
    monkeypatch.setattr(apply, "current_scheme", lambda: None)
    # Force the konsole module to report unavailable.
    from kolour import konsole as konsole_mod
    monkeypatch.setattr(konsole_mod, "available", lambda: False)

    result = apply.apply_theme("Dracula", dry_run=True, konsole=True, gtk=False)
    joined = " ".join(result.actions)
    assert "Konsole" not in joined and "konsolerc" not in joined
    assert "plasma-apply-colorscheme Dracula" in joined


def test_unknown_theme_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(apply, "KDE_SCHEMES_DIR", tmp_path / "schemes")
    monkeypatch.setattr(registry, "KDE_SCHEMES_DIR", tmp_path / "schemes")
    import pytest
    with pytest.raises(KeyError):
        apply.apply_theme("nonexistent-theme", dry_run=True)
