from __future__ import annotations

import json
import os
import re
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone
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

def analyze_command(
    project_root: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
    max_concepts: int = typer.Option(50, "--max-concepts", help="Maximum number of concepts to output (after merge)."),
    category: str = typer.Option("finding", "--category", help="Default category to assign."),
    mode: str = typer.Option("heuristic", "--mode", help="heuristic (offline) or openai (LLM)."),
    model: str = typer.Option("gpt-4o-mini", "--model", help="Model name for --mode openai."),
    batch_size: int = typer.Option(12, "--batch-size", help="Chunks per OpenAI request (openai mode)."),
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
        "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
        "input": str(in_path.relative_to(paths.root)),
        "mode": mode_norm,
        "model": model if mode_norm == "openai" else None,
        "concept_count": len(concepts),
        "concepts": [c.model_dump() for c in concepts],
    }
    out_path.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    console.print("[bold green]Analyze complete[/bold green]")
    console.print(f"  Mode: {mode_norm}")
    if mode_norm == "openai":
        console.print("  Provider: OpenAI Responses API (Structured Outputs)")
        console.print(f"  Model: {model}")
    console.print(f"  Input: {in_path}")
    console.print(f"  Concepts: {len(concepts)}")
    console.print(f"  Output: {out_path}")
