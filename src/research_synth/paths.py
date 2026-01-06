from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    config_file: Path
    sources_dir: Path
    outputs_dir: Path
    chunks_dir: Path
    analysis_dir: Path
    cache_dir: Path

def resolve_project_paths(root: Path) -> ProjectPaths:
    root = root.resolve()
    return ProjectPaths(
        root=root,
        config_file=root / "research.yml",
        sources_dir=root / "sources",
        outputs_dir=root / "outputs",
        chunks_dir=root / "chunks",
        analysis_dir=root / "analysis",
        cache_dir=root / ".research_cache",
    )
