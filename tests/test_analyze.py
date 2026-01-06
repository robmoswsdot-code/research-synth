from __future__ import annotations

import json
from pathlib import Path
from typer.testing import CliRunner
from research_synth.cli import app

runner = CliRunner()

def test_analyze_pipeline_txt(tmp_path: Path) -> None:
    res = runner.invoke(app, ["init", str(tmp_path), "--name", "Test Project"])
    assert res.exit_code == 0

    src_dir = tmp_path / "sources"
    (src_dir / "a.txt").write_text(
        "Cost risk is increasing due to incomplete scope definition. "
        "Schedule impacts are possible if permits are delayed. "
        "Recommendation: finalize scope and coordinate early with stakeholders.",
        encoding="utf-8",
    )

    res2 = runner.invoke(app, ["ingest", str(tmp_path), "--max-tokens", "80", "--overlap", "10"])
    assert res2.exit_code == 0

    res3 = runner.invoke(app, ["analyze", str(tmp_path), "--max-concepts", "10", "--mode", "heuristic"])
    assert res3.exit_code == 0

    out = tmp_path / "analysis" / "concepts.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["concept_count"] >= 1
    assert "concepts" in data and len(data["concepts"]) >= 1
