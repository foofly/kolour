import pytest

from kolour import colors_io, registry


def test_palette_extraction():
    nord = registry.resolve("Nord")
    pal = colors_io.palette(nord.colors_path)
    assert "window_bg" in pal
    assert "accent" in pal
    assert pal["accent"] == (136, 192, 208)  # Nord frost ice (#88c0d0)


def test_hex_round_trip():
    assert colors_io.hex_to_rgb("#88c0d0") == (136, 192, 208)
    assert colors_io.rgb_to_hex((136, 192, 208)) == "#88c0d0"


def test_invalid_hex_raises():
    with pytest.raises(ValueError):
        colors_io.hex_to_rgb("nope")


def test_scheme_name_matches_filename():
    for theme in registry.all():
        name = colors_io.scheme_name(theme.colors_path)
        assert name == theme.name, f"{theme.colors_path} has Name={name!r}"
