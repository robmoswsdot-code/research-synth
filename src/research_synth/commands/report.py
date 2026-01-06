from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
import typer

from research_synth.log import console
from research_synth.paths import resolve_project_paths
from research_synth.config import load_config

def _render_markdown(concepts: list[dict], *, title: str) -> str:
    lines = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("This is a draft generated from analyzed source documents. Review and edit before publishing.")
    lines.append("")
    lines.append("---")
    lines.append("")

    by_category: dict[str, list[dict]] = {}
    for c in concepts:
        by_category.setdefault(c.get("category", "other"), []).append(c)

    order = ["finding", "risk", "recommendation", "assumption", "context", "other"]
    for cat in order:
        if cat not in by_category:
            continue
        lines.append(f"## {cat.title()}s")
        lines.append("")
        for c in by_category[cat]:
            lines.append(f"### {c.get('label','(untitled)')}")
            lines.append("")
            lines.append(c.get("summary", ""))
            lines.append("")
            lines.append("**Confidence:** " + c.get("confidence", "medium").title())
            lines.append("")
            ev = c.get("evidence", []) or []
            if ev:
                lines.append("**Evidence:**")
                for e in ev:
                    cid = e.get("chunk_id")
                    src = e.get("source_file")
                    loc = e.get("location")
                    q = e.get("quote")
                    ref = f"[{cid}] {src} — {loc}"
                    if q:
                        lines.append(f"- {ref}: \"{q}\"")
                    else:
                        lines.append(f"- {ref}")
                lines.append("")
        lines.append("")

    lines.append("---")
    lines.append("_Generated on " + datetime.now(timezone.utc).isoformat() + "Z_")
    return "\n".join(lines)

def report_command(
    project_root: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
    title: str = typer.Option("Draft Report", "--title", help="Report title"),
    input_file: str = typer.Option("analysis/concepts.json", "--input", help="Input concepts JSON"),
    out_file: str = typer.Option("outputs/draft_report.md", "--out", help="Output Markdown file"),
) -> None:
    """Generate a draft Markdown report from analysis/concepts.json."""
    paths = resolve_project_paths(project_root)
    cfg = load_config(paths.config_file)

    in_path = paths.root / input_file
    if not in_path.exists():
        console.print(f"[red]Missing input file: {in_path}[/red]")
        console.print("Run: research-synth analyze .")
        raise typer.Exit(code=1)

    data = json.loads(in_path.read_text(encoding="utf-8"))
    concepts = data.get("concepts", [])
    if not concepts:
        console.print("[yellow]No concepts found to report.[/yellow]")
        raise typer.Exit(code=1)

    paths.outputs_dir.mkdir(parents=True, exist_ok=True)
    out_path = paths.root / out_file

    md = _render_markdown(concepts, title=title or cfg.project_name or "Draft Report")
    out_path.write_text(md, encoding="utf-8")

    console.print("[bold green]Report generated[/bold green]")
    console.print(f"  Input: {in_path}")
    console.print(f"  Output: {out_path}")
