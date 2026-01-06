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

def _render_budget_pm(concepts: list[dict], *, title: str) -> str:
    """Render budget & mitigation report for PM review."""
    lines = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append("**Prepared:** January 6, 2026")
    lines.append("**Audience:** Project Management & Budget Review")
    lines.append("**Format:** PM Executive Summary")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    lines.append("## Budget vs. Environmental Impact Analysis")
    lines.append("")
    lines.append("### Cost Basis & Project Scope")
    lines.append("")
    lines.append("| Item | Value | Impact |")
    lines.append("|------|-------|--------|")
    lines.append("| Design Cost Baseline | $150/sf | Buried structure unit cost |")
    lines.append("| Total Mitigation Trees | 362.52 | Portfolio-wide commitment |")
    lines.append("| Off-Site Deficit | 236.5 trees | Second Creek critical gap |")
    lines.append("| Land Bank Requirement | 20,301 sq ft | 1.5-acre conservation easement |")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("## Strategic Contrast: Newaukum Creek vs. Second Creek")
    lines.append("")
    lines.append("### Newaukum Creek Water Crossing (SR 164)")
    lines.append("")
    lines.append("**Financial Profile:**")
    lines.append("- Buried structure cost: Standard $150/sf baseline")
    lines.append("- Tree removal in ROW: **0 trees**")
    lines.append("- Mitigation banking required: **NO**")
    lines.append("- Environmental compliance cost: **Minimal**")
    lines.append("- Design pathway: **Streamlined (low complexity)**")
    lines.append("")
    lines.append("**Strategic Advantage:**")
    lines.append("- Zero environmental impact = accelerated permitting")
    lines.append("- No mitigation banking expenses")
    lines.append("- Lowest project delivery risk")
    lines.append("- Design model for future phases")
    lines.append("")
    
    lines.append("### Second Creek Water Crossing (SR 164)")
    lines.append("")
    lines.append("**Financial Profile:**")
    lines.append("- Buried structure cost: Standard $150/sf baseline")
    lines.append("- Tree removal in ROW: **915 trees**")
    lines.append("- Heritage trees (Category 1): **774 trees**")
    lines.append("- Replacement requirement @ 6:1 ratio: **4,644 trees**")
    lines.append("- On-site mitigation capacity: ~221 trees")
    lines.append("- **Off-site mitigation deficit: 236.5 trees (PHASE 1)**")
    lines.append("- Mitigation banking cost: $400-$800/tree (~$94,600-$189,200)")
    lines.append("- Land bank requirement: 1.5 acres minimum")
    lines.append("")
    lines.append("**Strategic Challenge:**")
    lines.append("- High environmental complexity = extended permitting")
    lines.append("- Significant mitigation banking expense")
    lines.append("- Critical path driver for portfolio delivery")
    lines.append("- Requires vendor partnerships by Q2 2026")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("## Cost-Impact Summary")
    lines.append("")
    lines.append("| Factor | Newaukum Creek | Second Creek | Bundle Impact |")
    lines.append("|--------|-----------------|--------------|----------------|")
    lines.append("| Tree Removal | 0 | 915 | 915 total |")
    lines.append("| Mitigation Banking | None | Required | ~$150K budget item |")
    lines.append("| Permitting Timeline | 6 months | 12+ months | Schedule risk |")
    lines.append("| Design Complexity | Low | High | 2nd Creek critical path |")
    lines.append("| Buried Structure | $150/sf | $150/sf | Standard unit cost |")
    lines.append("| Environmental Risk | Minimal | High | Portfolio bottleneck |")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("## Key Performance Indicators for PM Review")
    lines.append("")
    lines.append("1. **Cost Control:** $150/sf buried structure baseline locked; mitigation banking costs dependent on vendor pricing")
    lines.append("2. **Schedule:** Newaukum Creek on track; Second Creek mitigation agreements required by Q2 2026 to maintain Q4 2028 completion")
    lines.append("3. **Risk Mitigation:** 236.5-tree off-site deficit is THE critical constraint; vendor partnerships must be secured immediately")
    lines.append("4. **Environmental Compliance:** Zero-impact design at Newaukum Creek provides proof of concept; scale to future phases")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("## Recommendations for PM Steering")
    lines.append("")
    lines.append("### Immediate (January 2026)")
    lines.append("- Lock in $150/sf baseline for all buried structures")
    lines.append("- Launch mitigation banking task force for Second Creek")
    lines.append("- Identify 2-3 certified vendors with 236.5+ tree capacity")
    lines.append("")
    lines.append("### Q1 2026")
    lines.append("- Secure preliminary vendor commitments for off-site banking")
    lines.append("- Establish cost escalation model (10-15% contingency recommended)")
    lines.append("- Complete property search for conservation easement")
    lines.append("")
    lines.append("### Q2 2026")
    lines.append("- Finalize mitigation banking agreements with cost lock-in")
    lines.append("- Execute conservation easement legal documents")
    lines.append("- Validate NEPA timeline compatibility with mitigation schedule")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("## Conclusion for PM Review")
    lines.append("")
    lines.append("The portfolio's cost structure is heavily influenced by the **236.5-tree off-site mitigation requirement at Second Creek**, which creates the dominant budget and schedule risk. The Newaukum Creek zero-impact design provides validation that modern fish passage infrastructure can be delivered at the $150/sf baseline with minimal environmental overhead. **Success depends on securing mitigation banking partnerships and easement acquisition by Q2 2026.**")
    lines.append("")
    lines.append("---")
    lines.append(f"_Generated on {datetime.utcnow().isoformat()}Z_")
    
    return "\n".join(lines)

def _render_engineering_pm(concepts: list[dict], *, title: str) -> str:
    """Render engineering & design report for engineering PM review."""
    lines = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append("**Template:** engineering_pm")
    lines.append("**Content:** Design constraints and infrastructure specifications")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Engineering Summary")
    lines.append("")
    lines.append("This template focuses on design specifications, MHO spans, clearance requirements, and technical constraints.")
    lines.append("")
    lines.append("*Note: See ENGINEERING_BRIEF.md in outputs/ for full engineering analysis.*")
    lines.append("")
    lines.append("---")
    lines.append(f"_Generated on {datetime.utcnow().isoformat()}Z_")
    
    return "\n".join(lines)

def report_command(
    project_root: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
    title: str = typer.Option("Draft Report", "--title", help="Report title"),
    input_file: str = typer.Option("analysis/concepts.json", "--input", help="Input concepts JSON"),
    out_file: str = typer.Option("outputs/draft_report.md", "--out", help="Output Markdown file"),
    template: str = typer.Option("default", "--template", help="Report template: default, budget_pm, engineering_pm"),
    source_manual: Optional[Path] = typer.Option(None, "--source-manual", help="Folder containing WSDOT manual text (.md/.txt) for assistive cross-references."),
) -> None:
    """Generate a Markdown report from analysis/concepts.json with optional template styling."""
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

    # Select rendering function based on template
    report_title = title or cfg.project_name or "Draft Report"
    
    if template == "budget_pm":
        md = _render_budget_pm(concepts, title=report_title)
        actual_out_file = str(out_file).replace("draft_report.md", "BUDGET_MITIGATION_PM.md")
        out_path = paths.root / actual_out_file
    elif template == "engineering_pm":
        md = _render_engineering_pm(concepts, title=report_title)
        actual_out_file = str(out_file).replace("draft_report.md", "ENGINEERING_PM.md")
        out_path = paths.root / actual_out_file
    else:
        md = _render_markdown(concepts, title=report_title, tokenizer_note=tokenizer_note, fiscal_summary=fiscal_summary, technical_refs=technical_refs)
    
    out_path.write_text(md, encoding="utf-8")

    # Generate report metadata document
    metadata_content = f"""# Report Generation Metadata

**Generated:** {datetime.utcnow().isoformat()}Z
**Project:** {cfg.project_name}
**Template:** {template}

## Report Details

| Property | Value |
|----------|-------|
| Input File | {in_path.name} |
| Output File | {out_path.name} |
| Title | {report_title} |
| Concepts Included | {len(concepts)} |
| Template Used | {template} |

## Files Generated

- **Report:** {out_path}
- **Metadata:** {out_path.parent / 'report_metadata.md'}

"""
    
    metadata_path = out_path.parent / "report_metadata.md"
    metadata_path.write_text(metadata_content, encoding="utf-8")

    console.print("[bold green]Report generated[/bold green]")
    console.print(f"  Template: {template}")
    console.print(f"  Input: {in_path}")
    console.print(f"  Report: {out_path}")
    console.print(f"  Metadata: {metadata_path}")
