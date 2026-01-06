from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
import typer

from research_synth.log import console
from research_synth.paths import resolve_project_paths
from research_synth.config import load_config
from research_synth.hashing import sha256_file, sha256_text
from research_synth.cache import open_cache
from research_synth.extractors import extract_file
from research_synth.chunking import chunk_text
from research_synth.models import SourceChunk

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".txt", ".md", ".xlsx", ".xlsm", ".xls"}

def _iter_source_files(project_root: Path, source_dirs: list[str]) -> list[Path]:
    files: list[Path] = []
    for d in source_dirs:
        p = (project_root / d).resolve()
        if not p.exists():
            continue
        for f in p.rglob("*"):
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
                # Deterministic ID: sha of filehash + location + index + chunk hash
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
        "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
        "source_dirs": cfg.source_dirs,
        "file_count": len(source_files),
        "chunk_count": len(all_chunks),
        "chunks": [c.model_dump() for c in all_chunks],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

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
    console.print(f"  Output: {out_path}")
