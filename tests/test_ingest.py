from __future__ import annotations

import json
from pathlib import Path
from typer.testing import CliRunner
from research_synth.cli import app

runner = CliRunner()

def test_ingest_txt(tmp_path: Path) -> None:
    # init project
    res = runner.invoke(app, ["init", str(tmp_path), "--name", "Test Project"])
    assert res.exit_code == 0

    # add a text file
    src_dir = tmp_path / "sources"
    src_dir.mkdir(exist_ok=True)
    (src_dir / "a.txt").write_text("Hello world. This is a test document.", encoding="utf-8")

    # ingest
    res2 = runner.invoke(app, ["ingest", str(tmp_path), "--max-tokens", "50", "--overlap", "10"])
    assert res2.exit_code == 0

    out = tmp_path / "chunks" / "extracted_text.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["file_count"] == 1
    assert data["chunk_count"] >= 1
