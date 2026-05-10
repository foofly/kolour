"""matugen integration tests — fully mocked, no external matugen needed."""
from pathlib import Path
from unittest.mock import patch

import pytest

from kolour import matugen


def test_missing_matugen_raises(monkeypatch):
    monkeypatch.setattr(matugen, "available", lambda: False)
    with pytest.raises(matugen.MatugenMissing):
        matugen.generate_and_apply(wallpaper_path=Path("/tmp/x.png"))


def test_missing_wallpaper_raises(monkeypatch):
    monkeypatch.setattr(matugen, "available", lambda: True)
    monkeypatch.setattr(matugen.wallpaper, "current", lambda: None)
    with pytest.raises(matugen.WallpaperMissing):
        matugen.generate_and_apply(wallpaper_path=None)


def test_dry_run_builds_correct_command(monkeypatch, tmp_path):
    fake_wp = tmp_path / "wp.jpg"
    fake_wp.write_bytes(b"\x89PNG")
    monkeypatch.setattr(matugen, "available", lambda: True)
    monkeypatch.setattr(matugen, "TEMPLATE", tmp_path / "kde.colors")
    (tmp_path / "kde.colors").write_text("template")  # exists check

    result = matugen.generate_and_apply(
        wallpaper_path=fake_wp, mode="dark", dry_run=True,
    )
    joined = " ".join(result.actions)
    assert "matugen image" in joined
    assert str(fake_wp) in joined
    assert "--mode dark" in joined
    assert result.dry_run is True


def test_subprocess_failure_propagates(monkeypatch, tmp_path):
    fake_wp = tmp_path / "wp.jpg"
    fake_wp.write_bytes(b"\x89PNG")
    monkeypatch.setattr(matugen, "available", lambda: True)
    monkeypatch.setattr(matugen, "TEMPLATE", tmp_path / "kde.colors")
    (tmp_path / "kde.colors").write_text("template")

    import subprocess
    def fail(*_a, **_kw):
        raise subprocess.CalledProcessError(1, ["matugen"], stderr="boom")
    monkeypatch.setattr(matugen.subprocess, "run", fail)

    with pytest.raises(RuntimeError, match="matugen failed"):
        matugen.generate_and_apply(wallpaper_path=fake_wp)
