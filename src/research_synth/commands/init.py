from __future__ import annotations

import typer
from pathlib import Path
from datetime import datetime

from research_synth.log import console
from research_synth.paths import resolve_project_paths
from research_synth.config import write_default_config

def init_command(
    project_root: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
    name: str = typer.Option("Untitled Research Project", "--name", help="Project name stored in research.yml"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing config if present"),
) -> None:
    paths = resolve_project_paths(project_root)

    if paths.config_file.exists() and not force:
        raise typer.BadParameter(f"{paths.config_file} already exists. Use --force to overwrite.")

    paths.sources_dir.mkdir(parents=True, exist_ok=True)
    paths.outputs_dir.mkdir(parents=True, exist_ok=True)
    paths.chunks_dir.mkdir(parents=True, exist_ok=True)
    paths.analysis_dir.mkdir(parents=True, exist_ok=True)
    paths.cache_dir.mkdir(parents=True, exist_ok=True)

    write_default_config(paths.config_file, project_name=name)

    # Generate initialization report
    md_content = f"""# Project Initialization Report

**Project Name:** {name}
**Initialized:** {datetime.utcnow().isoformat()}Z

## Project Structure

| Directory | Path |
|-----------|------|
| Root | {paths.root} |
| Sources | {paths.sources_dir} |
| Chunks | {paths.chunks_dir} |
| Analysis | {paths.analysis_dir} |
| Outputs | {paths.outputs_dir} |
| Cache | {paths.cache_dir} |

## Configuration

- **Config File:** {paths.config_file}
- **Project Name:** {name}

## Next Steps

1. Place source documents in `sources/` directory
   - Supported formats: .docx, .md, .pdf, .txt, .xlsx, .xlsm, .xls

2. Run ingest to extract and chunk documents:
   ```
   research-synth ingest .
   ```

3. Run analyze to extract concepts:
   ```
   research-synth analyze .
   ```

4. Generate a report:
   ```
   research-synth report .
   ```

"""
    
    md_path = paths.root / "init_report.md"
    md_path.write_text(md_content, encoding="utf-8")

    console.print("[bold green]Initialized research project[/bold green]")
    console.print(f"  Root: {paths.root}")
    console.print(f"  Config: {paths.config_file}")
    console.print(f"  Sources: {paths.sources_dir}")
    console.print(f"  Outputs: {paths.outputs_dir}")
    console.print(f"  Chunks: {paths.chunks_dir}")
    console.print(f"  Analysis: {paths.analysis_dir}")
    console.print(f"  Cache: {paths.cache_dir}")
    console.print(f"  Init Report: {md_path}")
