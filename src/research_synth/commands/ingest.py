from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
import typer
import re
import importlib.util

from research_synth.log import console
from research_synth.paths import resolve_project_paths
from research_synth.config import load_config
from research_synth.hashing import sha256_file, sha256_text
from research_synth.cache import open_cache
from research_synth.extractors import extract_file

ROUTE_RE = re.compile(r"\bSR\s*0*(92|164|204|410|528)\b", re.IGNORECASE)

def _detect_route(text: str, path_str: str) -> str | None:
    m = ROUTE_RE.search(path_str) or ROUTE_RE.search(text or "")
    if not m:
        return None
    return f"SR {int(m.group(1))}"
from research_synth.chunking import chunk_text, chunk_text_with_meta
from research_synth.models import SourceChunk

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".txt", ".md", ".xlsx", ".xlsm", ".xls"}

# Use list_all_contents.py as source of truth for file discovery
from research_synth.list_all_contents import list_all_contents
def _iter_source_files(project_root: Path, source_dirs: list[str]) -> list[Path]:
    # Recursively check all documents listed by list_all_contents.py in the entire project folder
    all_items = list_all_contents(str(project_root))
    files: list[Path] = []
    for item in all_items:
        f = project_root / item
        if f.is_file() and f.suffix.lower() in SUPPORTED_SUFFIXES:
            files.append(f)
    # Deterministic ordering
    return sorted(files, key=lambda x: str(x).lower())

def ingest_command(
    project_root: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
    max_tokens: int = typer.Option(800, "--max-tokens", help="Max tokens per chunk"),
    overlap: int = typer.Option(100, "--overlap", help="Token overlap between chunks"),
    force: bool = typer.Option(False, "--force", help="Ignore cache and re-extract everything"),
) -> None:
    """Extract and chunk text from documents under sources/, writing chunks/extracted_text.json."""
    paths = resolve_project_paths(project_root)
    cfg = load_config(paths.config_file)

    paths.chunks_dir.mkdir(parents=True, exist_ok=True)
    paths.cache_dir.mkdir(parents=True, exist_ok=True)

    cache = open_cache(paths.cache_dir)

    source_files = _iter_source_files(paths.root, cfg.source_dirs)
    if not source_files:
        console.print("[yellow]No supported files found in configured source_dirs.[/yellow]")
        console.print(f"Configured source_dirs: {cfg.source_dirs}")
        console.print(f"Supported: {', '.join(sorted(SUPPORTED_SUFFIXES))}")
        raise typer.Exit(code=1)

    all_chunks: list[SourceChunk] = []
    extracted_docs = 0
    cached_docs = 0
    skipped_docs = 0
    skipped: list[str] = []

    for f in source_files:
        file_hash = sha256_file(f)
        cache_key = f"extract:{str(f)}:{file_hash}"
        if (not force) and (cache_key in cache):
            parts = cache[cache_key]
            cached_docs += 1
        else:
            try:
                parts = extract_file(f)
            except RuntimeError as e:
                skipped_docs += 1
                skipped.append(f"{str(f)} :: {e}")
                parts = []
            cache[cache_key] = parts
            extracted_docs += 1

        # parts: [(location, text)]
        for location, text in parts:
            for ch in chunk_text(text, max_tokens=max_tokens, overlap=overlap):
                # Deterministic ID: sha of filehash + location + index + chunk hash of text 
                cid = sha256_text(f"{file_hash}|{location}|{ch.index}|{sha256_text(ch.text)}")[:32]
                all_chunks.append(
                    SourceChunk(
                        chunk_id=cid,
                        source_file=str(f.relative_to(paths.root)),
                        location=location,
                        text=ch.text,
                        hash=file_hash,
                    )
                )

    out_path = paths.chunks_dir / "extracted_text.json"
    payload = {
        "project": cfg.project_name,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source_dirs": cfg.source_dirs,
        "file_count": len(source_files),
        "chunk_count": len(all_chunks),
        "chunks": [c.model_dump() for c in all_chunks],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Generate markdown summary
    md_content = f"""# Ingest Report

**Project:** {cfg.project_name}
**Generated:** {datetime.utcnow().isoformat()}Z

## Summary

| Metric | Value |
|--------|-------|
| Files Processed | {len(source_files)} |
| Chunks Created | {len(all_chunks)} |
| Extracted (New) | {extracted_docs} |
| Cached (Reused) | {cached_docs} |
| Skipped | {skipped_docs} |

## Source Directories

{chr(10).join(f"- {d}" for d in cfg.source_dirs)}

## Chunk Statistics

- **Max Tokens per Chunk:** {max_tokens}
- **Token Overlap:** {overlap}
- **Total Tokens (approx):** {sum(len(ch.text.split()) for ch in all_chunks) * 1.3:.0f}

## Output Files

- **JSON:** {out_path}
- **Markdown:** {out_path.parent / 'ingest_report.md'}
"""
    
    if skipped_docs:
        md_content += f"\n## Skipped Files ({skipped_docs})\n\n"
        for s in skipped[:10]:
            md_content += f"- {s}\n"
        if len(skipped) > 10:
            md_content += f"\n... and {len(skipped)-10} more\n"
    
    md_path = out_path.parent / "ingest_report.md"
    md_path.write_text(md_content, encoding="utf-8")

    console.print("[bold green]Ingest complete[/bold green]")
    console.print(f"  Files: {len(source_files)}")
    console.print(f"  Extracted (cache miss): {extracted_docs}")
    console.print(f"  Cached (cache hit): {cached_docs}")
    console.print(f"  Chunks: {len(all_chunks)}")
    if skipped_docs:
        console.print(f"  Skipped: {skipped_docs}")
        for s in skipped[:10]:
            console.print(f"    - {s}")
        if len(skipped) > 10:
            console.print(f"    ... and {len(skipped)-10} more")
    console.print(f"  JSON Output: {out_path}")
    console.print(f"  Markdown Report: {md_path}")
