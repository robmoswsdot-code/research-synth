from __future__ import annotations

from pathlib import Path
from typer.testing import CliRunner
from research_synth.cli import app

runner = CliRunner()

def test_init_creates_structure(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", str(tmp_path), "--name", "Test Project"])
    assert result.exit_code == 0
    assert (tmp_path / "research.yml").exists()
    assert (tmp_path / "sources").exists()
    assert (tmp_path / "outputs").exists()
    assert (tmp_path / "chunks").exists()
    assert (tmp_path / "analysis").exists()
    assert (tmp_path / ".research_cache").exists()
