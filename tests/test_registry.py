import pytest

from kolour import registry


def test_all_returns_bundled_themes():
    themes = registry.all()
    names = {t.name for t in themes}
    expected = {
        "Nord",
        "Catppuccin-Latte", "Catppuccin-Frappe", "Catppuccin-Macchiato", "Catppuccin-Mocha",
        "Everforest-Dark", "Everforest-Light",
        "Sweet", "Dracula",
        "Gruvbox-Dark", "Gruvbox-Light",
        "TokyoNight", "TokyoNight-Storm",
    }
    assert expected.issubset(names), f"missing: {expected - names}"


@pytest.mark.parametrize(
    "query, expected",
    [
        ("Nord", "Nord"),
        ("nord", "Nord"),
        ("NORD", "Nord"),
        ("Catppuccin-Mocha", "Catppuccin-Mocha"),
        ("catppuccin-mocha", "Catppuccin-Mocha"),
        ("catppuccin/mocha", "Catppuccin-Mocha"),
        ("tokyonight", "TokyoNight"),
        ("tokyo night", "TokyoNight"),
        ("gruvbox-dark", "Gruvbox-Dark"),
    ],
)
def test_resolve_variants(query, expected):
    assert registry.resolve(query).name == expected


def test_resolve_unknown_raises():
    with pytest.raises(KeyError):
        registry.resolve("definitely-not-a-theme")


def test_each_theme_has_konsole_and_gtk():
    """Every bundled theme should ship matching konsole + gtk artefacts."""
    for t in registry.all():
        assert t.konsole_path is not None, f"{t.name} missing Konsole .colorscheme"
        assert t.gtk_path is not None, f"{t.name} missing GTK .css"
