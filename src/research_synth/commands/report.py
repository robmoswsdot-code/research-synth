from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from datetime import datetime
import typer

from research_synth.log import console
from research_synth.paths import resolve_project_paths
from research_synth.config import load_config

def _load_tokenizer_flag(root: Path) -> dict | None:
    p = root / "chunks" / "extracted_text.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("tokenizer")
    except Exception:
        return None

def _load_manual_refs(manual_path: Path, concepts: list[dict]) -> list[str]:
    texts = []
    for c in concepts:
        texts.append((c.get('label','') + ' ' + c.get('summary','')).lower())
    needle = ' '.join(texts)
    out = []
    for f in manual_path.rglob('*'):
        if f.suffix.lower() not in {'.txt','.md'}:
            continue
        try:
            mt = f.read_text(encoding='utf-8', errors='ignore').lower()
        except Exception:
            continue
        score = 0
        for kw in set(needle.split()):
            if len(kw) < 5:
                continue
            if kw in mt:
                score += 1
        if score >= 8:
            out.append(f"{f.name} (keyword hits: {score})")
    out.sort()
    return out

def _render_markdown(concepts: list[dict], *, title: str, tokenizer_note: str | None = None, fiscal_summary: dict | None = None, technical_refs: list[str] | None = None) -> str:
    lines = []
    lines.append(f"# {title}")
    lines.append("")
    if tokenizer_note:
        lines.append("> **LOW-FIDELITY WARNING:** " + tokenizer_note)
        lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("This is a draft generated from analyzed source documents. Review and edit before publishing.")
    lines.append("")
    lines.append("---")
    lines.append("")

    if fiscal_summary and fiscal_summary.get('rows'):
        lines.append("## Fiscal Summary")
        lines.append("")
        lines.append("| Site | Authorized | Spent | Remaining |")
        lines.append("|---|---:|---:|---:|")
        for row in fiscal_summary['rows']:
            lines.append(f"| {row.get('site','')} | {row.get('authorized',0):,.0f} | {row.get('spent',0):,.0f} | {row.get('remaining',0):,.0f} |")
        lines.append("")
        lines.append("---")
        lines.append("")

    by_route: dict[str, list[dict]] = {}
    for c in concepts:
        route = c.get('route') or 'Unassigned'
        by_route.setdefault(route, []).append(c)

    routes_sorted = sorted(by_route.keys(), key=lambda x: (x=='Unassigned', x))

    order = ["finding", "risk", "recommendation", "assumption", "context", "other"]
    for route in routes_sorted:
        lines.append(f"## {route}")
        lines.append("")
        by_category: dict[str, list[dict]] = {}
        for c in by_route[route]:
            by_category.setdefault(c.get('category','other'), []).append(c)
        for cat in order:
            if cat not in by_category:
                continue
            lines.append(f"### {cat.title()}s")
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

    if technical_refs:
        lines.append("## Technical Reference")
        lines.append("")
        lines.append("> Assistive index only. Verify citations in the official WSDOT manual text.")
        lines.append("")
        for t in technical_refs:
            lines.append(f"- {t}")
        lines.append("")
    lines.append("---")
    lines.append("_Generated on " + datetime.utcnow().isoformat() + "Z_")
    return "\n".join(lines)

def report_command(
    project_root: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
    title: str = typer.Option("Draft Report", "--title", help="Report title"),
    input_file: str = typer.Option("analysis/concepts.json", "--input", help="Input concepts JSON"),
    out_file: str = typer.Option("outputs/draft_report.md", "--out", help="Output Markdown file"),
    source_manual: Optional[Path] = typer.Option(None, "--source-manual", help="Folder containing WSDOT manual text (.md/.txt) for assistive cross-references."),
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
    fiscal_summary = data.get('fiscal_summary')
    tok = _load_tokenizer_flag(paths.root)
    tokenizer_note = None
    if tok and tok.get('fidelity') == 'low':
        tokenizer_note = f"Tokenizer={tok.get('name')} ({tok.get('detail')}). Token counts may be inaccurate; review chunking boundaries."
    technical_refs = _load_manual_refs(source_manual, concepts) if source_manual else None
    if not concepts:
        console.print("[yellow]No concepts found to report.[/yellow]")
        raise typer.Exit(code=1)

    paths.outputs_dir.mkdir(parents=True, exist_ok=True)
    out_path = paths.root / out_file

    md = _render_markdown(concepts, title=title or cfg.project_name or "Draft Report", tokenizer_note=tokenizer_note, fiscal_summary=fiscal_summary, technical_refs=technical_refs)
    out_path.write_text(md, encoding="utf-8")

    # Generate report metadata document
    from datetime import datetime
    metadata_content = f"""# Report Generation Metadata

**Generated:** {datetime.utcnow().isoformat()}Z
**Project:** {cfg.project_name}

## Report Details

| Property | Value |
|----------|-------|
| Input File | {in_path.name} |
| Output File | {out_file} |
| Title | {title or cfg.project_name or "Draft Report"} |
| Concepts Included | {len(concepts)} |

## Files Generated

- **Report:** {out_path}
- **Metadata:** {out_path.parent / 'report_metadata.md'}

"""
    
    metadata_path = out_path.parent / "report_metadata.md"
    metadata_path.write_text(metadata_content, encoding="utf-8")

    console.print("[bold green]Report generated[/bold green]")
    console.print(f"  Input: {in_path}")
    console.print(f"  Report: {out_path}")
    console.print(f"  Metadata: {metadata_path}")
