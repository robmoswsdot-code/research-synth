from __future__ import annotations

import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Optional
from datetime import datetime
import typer

from research_synth.log import console
from research_synth.paths import resolve_project_paths
from research_synth.config import load_config
from research_synth.models import ExtractedConcept, EvidenceRef

# Optional stdlib HTTP OpenAI client (no dependency) for enterprise stability.
from research_synth.openai_http import responses_create

STOPWORDS = {
    "the","and","or","to","of","in","a","an","for","on","by","with","as","at","from","is","are","was","were",
    "be","been","being","this","that","these","those","it","its","we","you","they","them","our","their",
    "will","shall","may","might","can","could","would","should","not","no","yes","if","then","than","but",
    "into","over","under","between","within","without","during","before","after","above","below","up","down",
}

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")
SENT_SPLIT_RE = re.compile(r"(?<=[\.!\?])\s+")

def _top_keywords(text: str, k: int = 4) -> list[str]:
    words = [w.lower() for w in WORD_RE.findall(text or "")]
    words = [w for w in words if w not in STOPWORDS]
    if not words:
        return []
    counts = Counter(words)
    return [w for w, _ in counts.most_common(k)]

def _first_sentences(text: str, n: int = 2) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    parts = SENT_SPLIT_RE.split(t)
    parts = [p.strip() for p in parts if p.strip()]
    return " ".join(parts[:n]).strip()

def _heuristic_concepts(chunks: list[dict], *, category: str) -> list[ExtractedConcept]:
    candidates: list[ExtractedConcept] = []
    for ch in chunks:
        text = (ch.get("text", "") or "").strip()
        if not text:
            continue

        keywords = _top_keywords(text, k=4)
        label = " / ".join(keywords[:3]) if keywords else "general"
        summary = _first_sentences(text, n=2) or (text[:240] + ("…" if len(text) > 240 else ""))

        evidence = EvidenceRef(
            chunk_id=ch["chunk_id"],
            source_file=ch["source_file"],
            location=ch["location"],
            quote=_first_sentences(text, n=1)[:240] if text else None,
        )
        concept_id = ch["chunk_id"]  # v0.1 stable id (chunk-tied)

        candidates.append(
            ExtractedConcept(
                concept_id=concept_id,
                label=label,
                category=category,
                summary=summary,
                confidence="low",
                evidence=[evidence],
            )
        )

    merged: dict[str, ExtractedConcept] = {}
    for c in candidates:
        if c.label not in merged:
            merged[c.label] = c
        else:
            merged[c.label].evidence.extend(c.evidence)

    concepts = list(merged.values())
    concepts.sort(key=lambda c: (-len(c.evidence), c.label))
    return concepts

def _concepts_schema() -> dict:
    # JSON Schema for Structured Outputs (Responses API text.format json_schema).
    # We keep it intentionally small and aligned with models.ExtractedConcept.
    return {
        "type": "object",
        "properties": {
            "concepts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "label": {"type": "string"},
                        "category": {
                            "type": "string",
                            "enum": ["finding", "risk", "recommendation", "context", "assumption"],
                        },
                        "summary": {"type": "string"},
                        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                        "evidence": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "chunk_id": {"type": "string"},
                                    "source_file": {"type": "string"},
                                    "location": {"type": "string"},
                                    "quote": {"type": ["string", "null"]},
                                },
                                "required": ["chunk_id", "source_file", "location"],
                            },
                        },
                    },
                    "required": ["label", "category", "summary", "confidence", "evidence"],
                },
            }
        },
        "required": ["concepts"],
        "additionalProperties": False,
    }

def _build_openai_prompt(batch: list[dict], *, default_category: str, max_concepts: int) -> list[dict]:
    # Provide chunk metadata so the model can cite it.
    lines = []
    for ch in batch:
        lines.append(f"CHUNK {ch['chunk_id']} | {ch['source_file']} | {ch['location']}\n{ch.get('text','').strip()}\n")

    system = (
        "You are a research synthesis assistant. "
        "Extract distinct concepts from the provided chunks. "
        "Each concept MUST include: label, category, summary, confidence, and evidence. "
        "Evidence MUST reference one or more chunk_id values from the input. "
        "Prefer fewer, higher-signal concepts over many repetitive ones."
    )

    user = (
        f"Return up to {max_concepts} concepts. "
        f"If unsure of category, use '{default_category}'. "
        "Only use chunk_ids that appear in the input.\n\n"
        + "\n".join(lines)
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]

def _openai_concepts(
    chunks: list[dict],
    *,
    model: str,
    default_category: str,
    max_concepts: int,
    batch_size: int,
) -> list[ExtractedConcept]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Set it in your environment to use --mode openai.")

    schema = _concepts_schema()
    text_format = {"type": "json_schema", "strict": True, "schema": schema}

    # Batch to avoid huge single requests. Merge by label afterwards.
    all_concepts: list[ExtractedConcept] = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        input_items = _build_openai_prompt(batch, default_category=default_category, max_concepts=max_concepts)

        resp = responses_create(
            api_key=api_key,
            model=model,
            input_items=input_items,
            text_format=text_format,
            timeout_s=180,
        )

        text = resp.extract_text()
        if not text:
            continue

        data = json.loads(text)
        for idx, c in enumerate(data.get("concepts", [])):
            # Assign deterministic concept_id: batch index + label hash-ish fallback to idx
            label = (c.get("label") or "concept").strip()
            concept_id = f"{i}-{idx}-{abs(hash(label)) % 10_000_000}"
            evs = []
            for e in c.get("evidence", []) or []:
                evs.append(
                    EvidenceRef(
                        chunk_id=e.get("chunk_id", ""),
                        source_file=e.get("source_file", ""),
                        location=e.get("location", ""),
                        quote=e.get("quote"),
                    )
                )
            all_concepts.append(
                ExtractedConcept(
                    concept_id=concept_id,
                    label=label,
                    category=c.get("category", default_category),
                    summary=(c.get("summary") or "").strip(),
                    confidence=c.get("confidence", "medium"),
                    evidence=evs,
                )
            )

    # Merge by label deterministically
    merged: dict[str, ExtractedConcept] = {}
    for c in all_concepts:
        if c.label not in merged:
            merged[c.label] = c
        else:
            merged[c.label].evidence.extend(c.evidence)

    concepts = list(merged.values())
    concepts.sort(key=lambda c: (-len(c.evidence), c.label))
    return concepts

def _load_budget_summary(budget_file: Path) -> dict | None:
    try:
        import pandas as pd  # type: ignore
    except ModuleNotFoundError:
        raise RuntimeError("Excel support not installed. Run: pip install -e '.[excel]'")
    if budget_file.suffix.lower() == ".csv":
        df = pd.read_csv(budget_file)
    else:
        df = pd.read_excel(budget_file)
    cols = {c.lower(): c for c in df.columns}
    needed = ["site", "authorized", "spent"]
    if any(n not in cols for n in needed):
        return None
    rows = []
    for _, row in df.iterrows():
        site = str(row[cols["site"]]).strip()
        authorized = float(row[cols["authorized"]]) if str(row[cols["authorized"]]).strip() else 0.0
        spent = float(row[cols["spent"]]) if str(row[cols["spent"]]).strip() else 0.0
        remaining = authorized - spent
        rows.append({"site": site, "authorized": authorized, "spent": spent, "remaining": remaining})
    return {"rows": rows}

def analyze_command(
    project_root: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
    max_concepts: int = typer.Option(50, "--max-concepts", help="Maximum number of concepts to output (after merge)."),
    category: str = typer.Option("finding", "--category", help="Default category to assign."),
    mode: str = typer.Option("heuristic", "--mode", help="heuristic (offline) or openai (LLM)."),
    model: str = typer.Option("gpt-4o-mini", "--model", help="Model name for --mode openai."),
    batch_size: int = typer.Option(12, "--batch-size", help="Chunks per OpenAI request (openai mode)."),
    budget_file: Optional[Path] = typer.Option(None, "--budget-file", help="Optional budget spreadsheet (xlsx/csv) for fiscal summary (requires excel extra)."),
) -> None:
    """Generate concepts from ingested chunks.

    - heuristic: fully offline, deterministic, lower quality.
    - openai: uses OpenAI Responses API with Structured Outputs for higher quality.
    """
    paths = resolve_project_paths(project_root)
    cfg = load_config(paths.config_file)

    in_path = paths.chunks_dir / "extracted_text.json"
    if not in_path.exists():
        console.print("[red]Missing chunks/extracted_text.json[/red]")
        console.print("Run: research-synth ingest .")
        raise typer.Exit(code=1)

    paths.analysis_dir.mkdir(parents=True, exist_ok=True)

    payload = json.loads(in_path.read_text(encoding="utf-8"))
    chunks = payload.get("chunks", [])

    if not chunks:
        console.print("[yellow]No chunks found to analyze.[/yellow]")
        raise typer.Exit(code=1)

    mode_norm = (mode or "").strip().lower()
    if mode_norm not in {"heuristic", "openai"}:
        raise typer.BadParameter("--mode must be 'heuristic' or 'openai'")

    if mode_norm == "heuristic":
        concepts = _heuristic_concepts(chunks, category=category)
    else:
        concepts = _openai_concepts(
            chunks,
            model=model,
            default_category=category,
            max_concepts=max_concepts,
            batch_size=batch_size,
        )

    concepts = concepts[:max_concepts]

    out_path = paths.analysis_dir / "concepts.json"
    out_payload = {
        "project": cfg.project_name,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "input": str(in_path.relative_to(paths.root)),
        "mode": mode_norm,
        "model": model if mode_norm == "openai" else None,
        "fiscal_summary": _load_budget_summary(budget_file) if budget_file is not None else None,
        "concept_count": len(concepts),
        "concepts": [c.model_dump() for c in concepts],
    }
    out_path.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Generate markdown summary
    md_content = f"""# Analysis Report

**Project:** {cfg.project_name}
**Generated:** {datetime.utcnow().isoformat()}Z

## Summary

| Metric | Value |
|--------|-------|
| Mode | {mode_norm} |
| Model | {model if mode_norm == "openai" else "Heuristic"} |
| Concepts Extracted | {len(concepts)} |
| Input File | {in_path.name} |

## Analysis Mode

"""
    if mode_norm == "openai":
        md_content += f"**Provider:** OpenAI Responses API (Structured Outputs)\n**Model:** {model}\n\n"
    else:
        md_content += "**Method:** Heuristic (keyword-based)\n\n"
    
    md_content += "## Extracted Concepts\n\n"
    for i, concept in enumerate(concepts[:20], 1):
        md_content += f"### {i}. {concept.label}\n\n"
        md_content += f"**Category:** {concept.category}\n"
        md_content += f"**Confidence:** {concept.confidence}\n"
        md_content += f"**Summary:** {concept.summary}\n\n"
        if concept.evidence:
            md_content += f"**Evidence:** {len(concept.evidence)} reference(s)\n"
            for ev in concept.evidence[:3]:
                md_content += f"- {ev.source_file}: {ev.quote or '(no quote)'}\n"
            if len(concept.evidence) > 3:
                md_content += f"- ... and {len(concept.evidence) - 3} more\n"
            md_content += "\n"
    
    if len(concepts) > 20:
        md_content += f"\n... and {len(concepts) - 20} more concepts\n"
    
    md_content += f"\n## Output Files\n\n"
    md_content += f"- **JSON:** {out_path}\n"
    md_content += f"- **Markdown:** {out_path.parent / 'analysis_report.md'}\n"
    
    md_path = out_path.parent / "analysis_report.md"
    md_path.write_text(md_content, encoding="utf-8")

    console.print("[bold green]Analyze complete[/bold green]")
    console.print(f"  Mode: {mode_norm}")
    if mode_norm == "openai":
        console.print("  Provider: OpenAI Responses API (Structured Outputs)")
        console.print(f"  Model: {model}")
    console.print(f"  Input: {in_path}")
    console.print(f"  Concepts: {len(concepts)}")
    console.print(f"  JSON Output: {out_path}")
    console.print(f"  Markdown Report: {md_path}")
