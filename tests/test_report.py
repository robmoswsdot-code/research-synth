from __future__ import annotations

from pathlib import Path
import json
from typer.testing import CliRunner
from research_synth.cli import app

runner = CliRunner()

def test_report_from_concepts(tmp_path: Path) -> None:
    assert runner.invoke(app, ["init", str(tmp_path), "--name", "Test Project"]).exit_code == 0

    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir(exist_ok=True)
    (analysis_dir / "concepts.json").write_text(
        json.dumps({
            "concepts": [
                {
                    "label": "Cost risk",
                    "category": "risk",
                    "summary": "Costs may increase due to scope changes.",
                    "confidence": "medium",
                    "evidence": [
                        {
                            "chunk_id": "abc123",
                            "source_file": "sources/a.txt",
                            "location": "TXT",
                            "quote": "Costs may increase"
                        }
                    ]
                }
            ]
        }),
        encoding="utf-8",
    )

    res = runner.invoke(app, ["report", str(tmp_path), "--title", "My Report"])
    assert res.exit_code == 0

    out = tmp_path / "outputs" / "draft_report.md"
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "# My Report" in text
    assert "Cost risk" in text


def test_report_includes_low_fidelity_warning(tmp_path: Path) -> None:
    assert runner.invoke(app, ["init", str(tmp_path), "--name", "Test Project"]).exit_code == 0

    (tmp_path / "chunks").mkdir(exist_ok=True)
    (tmp_path / "chunks" / "extracted_text.json").write_text(
        json.dumps({"tokenizer": {"name": "whitespace", "fidelity": "low", "detail": "missing"}}),
        encoding="utf-8",
    )

    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir(exist_ok=True)
    (analysis_dir / "concepts.json").write_text(
        json.dumps({
            "concepts": [
                {
                    "label": "Test",
                    "category": "finding",
                    "summary": "S",
                    "confidence": "low",
                    "evidence": [{"chunk_id":"c1","source_file":"sources/a.txt","location":"TXT","quote":None}],
                    "route": "SR 410"
                }
            ]
        }),
        encoding="utf-8",
    )

    res = runner.invoke(app, ["report", str(tmp_path), "--title", "My Report"])
    assert res.exit_code == 0
    out = tmp_path / "outputs" / "draft_report.md"
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "LOW-FIDELITY WARNING" in text
