from pathlib import Path

from kolour import wallpaper

FIXTURES = Path(__file__).parent / "fixtures"


def test_current_parses_fixture():
    p = wallpaper.current(FIXTURES / "appletsrc.example")
    assert p == Path("/home/example/Pictures/wall.jpg")


def test_missing_file_returns_none(tmp_path):
    assert wallpaper.current(tmp_path / "does-not-exist") is None


def test_no_section_returns_none(tmp_path):
    f = tmp_path / "appletsrc"
    f.write_text("[General]\nFoo=bar\n", encoding="utf-8")
    assert wallpaper.current(f) is None
